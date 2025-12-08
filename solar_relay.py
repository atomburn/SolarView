import os
import requests
import json
import sys
import time

# --- Configuration ---
# EG4 Portal URLs
# These are best-guess paths based on typical SPA backend APIs.
# You might need to adjust them by inspecting network traffic in your browser
# when interacting with the EG4 portal.
EG4_BASE_URL = "https://monitor.eg4electronics.com/WManage/web/"
EG4_LOGIN_ENDPOINT = "user/login"
EG4_PLANT_LIST_ENDPOINT = "plant/plantList"
EG4_PLANT_REALTIME_DATA_ENDPOINT = "plant/plantRealTimeData"

# Sensecraft API
SENSECRAFT_PUSH_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"
# As per the prompt's example, 'device_id' is hardcoded in the body.
SENSECRAFT_DEVICE_ID = 20221942 

# --- Environment Variable Loading ---
# Load sensitive information from environment variables
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID') # Optional: will auto-detect if not provided
SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')

# --- Main Script ---

def main():
    print("--- EG4 Data Bridge Script Started ---")

    # 1. Validate Environment Variables
    missing_env_vars = []
    if not EG4_USER:
        missing_env_vars.append('EG4_USER')
    if not EG4_PASS:
        missing_env_vars.append('EG4_PASS')
    if not SENSECRAFT_KEY:
        missing_env_vars.append('SENSECRAFT_KEY')

    if missing_env_vars:
        print(f"ERROR: The following required environment variables are not set: {', '.join(missing_env_vars)}")
        sys.exit(1)

    # Convert EG4_STATION_ID to int if it exists, otherwise keep as None
    eg4_station_id_int = None
    if EG4_STATION_ID:
        try:
            eg4_station_id_int = int(EG4_STATION_ID)
        except ValueError:
            print(f"ERROR: EG4_STATION_ID must be an integer if provided. Got: '{EG4_STATION_ID}'")
            sys.exit(1)

    session = requests.Session()
    eg4_auth_token = None

    try:
        # 2. Login to EG4 Portal
        print("Attempting to log in to EG4 portal...")
        login_url = f"{EG4_BASE_URL}{EG4_LOGIN_ENDPOINT}"
        login_payload = json.dumps({
            "userName": EG4_USER,
            "passWord": EG4_PASS
        })
        
        # EG4 login typically uses Content-Type: application/json
        headers_eg4_login = {'Content-Type': 'application/json'}

        login_response = session.post(login_url, data=login_payload, headers=headers_eg4_login, timeout=15)
        login_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        login_data = login_response.json()

        if login_data.get('code') == 0 and login_data.get('msg') == 'success':
            eg4_auth_token = login_data.get('obj', {}).get('token')
            if not eg4_auth_token:
                raise ValueError("EG4 login successful but no authentication token received.")
            print("Successfully logged in to EG4 portal.")
        else:
            raise ValueError(f"EG4 login failed: {login_data.get('msg', 'Unknown error')}. Response: {login_data}")

        # Set headers for subsequent authenticated EG4 API calls
        headers_eg4_auth = {'Content-Type': 'application/json', 'token': eg4_auth_token}

        # 3. Determine EG4 Station ID
        target_station_id = eg4_station_id_int
        if not target_station_id:
            print("EG4_STATION_ID not provided, fetching plant list to select the first one...")
            plant_list_url = f"{EG4_BASE_URL}{EG4_PLANT_LIST_ENDPOINT}"
            
            # EG4 plantList API usually requires a POST with a body for pagination
            plant_list_payload = json.dumps({"page": 1, "pageSize": 10}) 
            
            plant_list_response = session.post(plant_list_url, data=plant_list_payload, headers=headers_eg4_auth, timeout=15)
            plant_list_response.raise_for_status()
            plant_list_data = plant_list_response.json()

            if plant_list_data.get('code') == 0 and plant_list_data.get('obj', {}).get('list'):
                first_plant = plant_list_data['obj']['list'][0]
                target_station_id = first_plant.get('plantId')
                if not target_station_id:
                    raise ValueError("Could not find 'plantId' in the first plant from the list.")
                print(f"Selected first plant: '{first_plant.get('plantName', 'N/A')}' (ID: {target_station_id})")
            else:
                raise ValueError(f"Failed to fetch plant list or no plants found. Response: {plant_list_data.get('msg', 'Unknown error')}. Full response: {plant_list_data}")
        else:
            print(f"Using provided EG4_STATION_ID: {target_station_id}")
            
        if not target_station_id:
            raise ValueError("No EG4 Station ID could be determined. Exiting.")

        # 4. Fetch Latest Inverter Data
        print(f"Fetching real-time data for EG4 Station ID: {target_station_id}...")
        inverter_data_url = f"{EG4_BASE_URL}{EG4_PLANT_REALTIME_DATA_ENDPOINT}"
        inverter_payload = json.dumps({"plantId": target_station_id})

        inverter_response = session.post(inverter_data_url, data=inverter_payload, headers=headers_eg4_auth, timeout=15)
        inverter_response.raise_for_status()
        inverter_data = inverter_response.json()

        pv_power = None
        battery_soc = None
        load_power = None

        if inverter_data.get('code') == 0 and inverter_data.get('obj'):
            plant_realtime_info = inverter_data['obj']
            # Common field names for inverter data.
            # You might need to adjust these based on the actual EG4 API response:
            # 'pac' for PV AC power
            # 'soc' for battery State of Charge
            # 'pLoad' for instantaneous load power
            pv_power = plant_realtime_info.get('pac')
            battery_soc = plant_realtime_info.get('soc')
            load_power = plant_realtime_info.get('pLoad') 

            # Ensure all values are numeric, convert to float/int if they are not already.
            # Default to 0.0 if missing or conversion fails.
            try:
                pv_power = float(pv_power) if pv_power is not None else 0.0
                battery_soc = float(battery_soc) if battery_soc is not None else 0.0
                load_power = float(load_power) if load_power is not None else 0.0
            except (TypeError, ValueError) as e:
                print(f"WARNING: Could not convert EG4 data to numeric type: {e}")
                print(f"Raw EG4 values: PV={pv_power}, SOC={battery_soc}, Load={load_power}")
                # Fallback to 0.0 if conversion failed but original value exists (e.g. string "N/A")
                pv_power = 0.0
                battery_soc = 0.0
                load_power = 0.0

            print(f"EG4 Data Retrieved: PV Power={pv_power}W, Battery SOC={battery_soc}%, Load Power={load_power}W")
        else:
            raise ValueError(f"Failed to fetch inverter data. Response: {inverter_data.get('msg', 'Unknown error')}. Full response: {inverter_data}")

        if pv_power is None and battery_soc is None and load_power is None:
            raise ValueError("No valid inverter data could be extracted from EG4 response.")

        # 5. Push data to Sensecraft API
        print("Pushing data to Sensecraft API...")
        sensecraft_headers = {
            'api-key': SENSECRAFT_KEY,
            'Content-Type': 'application/json'
        }
        sensecraft_payload = {
            "device_id": SENSECRAFT_DEVICE_ID,
            "data": {
                "pv_power": pv_power,
                "battery_soc": battery_soc,
                "load_power": load_power
            }
        }

        sensecraft_response = requests.post(
            SENSECRAFT_PUSH_URL,
            headers=sensecraft_headers,
            json=sensecraft_payload,
            timeout=15
        )
        sensecraft_response.raise_for_status() # Raise HTTPError for bad responses

        print(f"Data successfully pushed to Sensecraft API. Response: {sensecraft_response.text}")
        print("--- EG4 Data Bridge Script Finished Successfully ---")
        sys.exit(0)

    except requests.exceptions.HTTPError as e:
        print(f"ERROR: An HTTP error occurred: {e}")
        if e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            try:
                print(f"Response body: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Response body (raw): {e.response.text}")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: A network connection error occurred: {e}")
        sys.exit(1)
    except requests.exceptions.Timeout as e:
        print(f"ERROR: The request timed out after 15 seconds: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: An unexpected request error occurred: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: Data processing or API logic error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unhandled exception occurred: {e}", exc_info=True) # exc_info for detailed traceback
        sys.exit(1)

if __name__ == "__main__":
    main()
