import os
import requests
import json
import sys

SCRIPT_VERSION = "2.2 (JSON Fix)"

def main():
    print(f"Script Version: {SCRIPT_VERSION}")
    print("--- EG4 to Sensecraft Data Bridge ---")

    # --- 1. Load Environment Variables ---
    eg4_user = os.environ.get('EG4_USER')
    eg4_pass = os.environ.get('EG4_PASS')
    eg4_station_id = os.environ.get('EG4_STATION_ID')
    sensecraft_key = os.environ.get('SENSECRAFT_KEY')

    if not eg4_user:
        print("ERROR: Environment variable 'EG4_USER' is not set.")
        sys.exit(1)
    if not eg4_pass:
        print("ERROR: Environment variable 'EG4_PASS' is not set.")
        sys.exit(1)
    if not sensecraft_key:
        print("ERROR: Environment variable 'SENSECRAFT_KEY' is not set.")
        sys.exit(1)

    if not eg4_station_id:
        print("WARNING: 'EG4_STATION_ID' is not set. Attempting to auto-detect the first plant ID.")
    else:
        print(f"Using EG4 Station ID: {eg4_station_id}")

    # --- 2. EG4 Portal Login ---
    session = requests.Session()
    login_url = "https://monitor.eg4electronics.com/WManage/web/login"
    login_data = {
        'account': eg4_user,
        'password': eg4_pass,
        'isRem': 'false',
        'lang': 'en_US'
    }
    login_headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    print("Attempting to log in to EG4 portal...")
    try:
        login_response = session.post(login_url, data=login_data, headers=login_headers, timeout=10)

        if login_response.status_code == 200 and 'JSESSIONID' in session.cookies:
            print("Successfully logged in to EG4 portal.")
        else:
            print(f"ERROR: EG4 Login failed. Status code: {login_response.status_code}")
            print(f"Response snippet: {login_response.text[:500]}...") # Show part of the response for debugging
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: An error occurred during EG4 login: {e}")
        sys.exit(1)

    # --- 3. Determine EG4 Station ID (if not provided) ---
    actual_station_id = eg4_station_id
    if not actual_station_id:
        get_plant_list_url = "https://monitor.eg4electronics.com/WManage/web/plant/getPlantList"
        print("Attempting to fetch plant list to determine Station ID...")
        try:
            plant_list_response = session.get(get_plant_list_url, timeout=10)
            plant_list_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            plant_list_json = plant_list_response.json()

            if plant_list_json.get('code') == 0 and plant_list_json.get('obj'):
                plants = plant_list_json['obj']
                if plants:
                    actual_station_id = plants[0].get('plantId')
                    print(f"Auto-detected EG4 Station ID: {actual_station_id}")
                else:
                    print("ERROR: No plants found in EG4 portal. Cannot determine Station ID.")
                    sys.exit(1)
            else:
                print(f"ERROR: Failed to fetch EG4 plant list. Response: {plant_list_json}")
                sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"ERROR: An error occurred while fetching EG4 plant list: {e}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"ERROR: Failed to decode JSON from EG4 plant list response. Response content: {plant_list_response.text}")
            sys.exit(1)

    if not actual_station_id:
        print("ERROR: Could not determine EG4 Station ID. Exiting.")
        sys.exit(1)

    # --- 4. Fetch EG4 Realtime Data ---
    get_realtime_data_url = "https://monitor.eg4electronics.com/WManage/web/plant/getRealtimeData"
    realtime_data_payload = {'plantId': actual_station_id}

    print(f"Attempting to fetch realtime data for Station ID: {actual_station_id}...")
    try:
        realtime_response = session.post(get_realtime_data_url, data=realtime_data_payload, timeout=10)
        realtime_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        realtime_json = realtime_response.json()

        if realtime_json.get('code') == 0 and realtime_json.get('obj'):
            eg4_data = realtime_json['obj']
            print("Successfully fetched EG4 realtime data.")

            # Extract relevant fields. Adjust keys if they differ from common names.
            pv_power = eg4_data.get('pvPower', 0)
            battery_soc = eg4_data.get('soc', 0) # Assuming 'soc' for State of Charge
            load_power = eg4_data.get('loadPower', 0)

            print(f"  PV Power: {pv_power}W")
            print(f"  Battery SOC: {battery_soc}%")
            print(f"  Load Power: {load_power}W")

        else:
            print(f"ERROR: Failed to fetch EG4 realtime data. Response: {realtime_json}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: An error occurred while fetching EG4 realtime data: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"ERROR: Failed to decode JSON from EG4 realtime data response. Response content: {realtime_response.text}")
        sys.exit(1)
    except KeyError as e:
        print(f"ERROR: Missing expected key in EG4 realtime data: {e}. Full response obj: {eg4_data}")
        sys.exit(1)


    # --- 5. Push Data to Sensecraft API ---
    sensecraft_endpoint = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"
    sensecraft_device_id = 20221942 # Hardcoded as per requirement

    sensecraft_headers = {
        'api-key': sensecraft_key,
        'Content-Type': 'application/json'
    }

    sensecraft_payload = {
        "device_id": sensecraft_device_id,
        "data": {
            "pv_power": pv_power,
            "battery_soc": battery_soc,
            "load_power": load_power
        }
    }

    print(f"Attempting to push data to Sensecraft API for device ID: {sensecraft_device_id}...")
    try:
        push_response = requests.post(
            sensecraft_endpoint,
            headers=sensecraft_headers,
            json=sensecraft_payload,
            timeout=10
        )
        push_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        print(f"Successfully pushed data to Sensecraft API. Status: {push_response.status_code}")
        print(f"Sensecraft Response: {push_response.text}")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: An error occurred while pushing data to Sensecraft API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Sensecraft Error Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        sys.exit(1)

    print("\n--- Script finished successfully ---")

if __name__ == "__main__":
    main()
