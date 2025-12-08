import requests
import os
import json
import sys
import time

SCRIPT_VERSION = "2.1 (Login Fix)"

# --- Configuration ---
# EG4 Portal URLs
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_GET_PLANT_LIST_URL = "https://monitor.eg4electronics.com/WManage/web/plant/getPlantList"
EG4_GET_REALTIME_DATA_URL = "https://monitor.eg4electronics.com/WManage/web/plant/getRealtimeData"

# Sensecraft API URL
SENSECRAFT_PUSH_DATA_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"

# Sensecraft Device ID (as provided in the example body structure)
SENSECRAFT_DEVICE_ID = 20221942

def log_message(level, message):
    """Prints a formatted log message."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level.upper()}] {message}")

def get_env_variable(name, required=True, sensitive=False):
    """Fetches an environment variable, checks for existence, and optionally masks output."""
    value = os.environ.get(name)
    if required and not value:
        log_message("ERROR", f"Missing required environment variable: {name}")
        sys.exit(1)
    if value and not sensitive:
        log_message("INFO", f"Loaded environment variable: {name}")
    elif value and sensitive:
        log_message("INFO", f"Loaded sensitive environment variable: {name} (masked)")
    return value

def main():
    log_message("INFO", f"Script Version: {SCRIPT_VERSION}")
    log_message("INFO", "Starting EG4 to Sensecraft Data Bridge...")

    # --- 1. Load Environment Variables ---
    eg4_user = get_env_variable('EG4_USER', required=True, sensitive=False)
    eg4_pass = get_env_variable('EG4_PASS', required=True, sensitive=True)
    eg4_station_id = get_env_variable('EG4_STATION_ID', required=False, sensitive=False)
    sensecraft_key = get_env_variable('SENSECRAFT_KEY', required=True, sensitive=True)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'X-Requested-With': 'XMLHttpRequest', # Often required by these portals for AJAX calls
        'Referer': 'https://monitor.eg4electronics.com/WManage/web/login', # Mimic browser
        'Origin': 'https://monitor.eg4electronics.com',
    })

    # --- 2. EG4 Portal Login ---
    log_message("INFO", f"Attempting to log in to EG4 portal: {EG4_LOGIN_URL}")
    login_payload = {
        'account': eg4_user,
        'password': eg4_pass,
        'isRem': 'false',
        'lang': 'en_US'
    }

    try:
        # First, a GET request to the login page might be needed to get initial cookies/CSRF tokens if any.
        # For simple POST logins, this might be skipped, but it's safer to attempt.
        # The portal typically handles session cookies automatically if allow_redirects=True.
        # Let's try direct POST first based on common patterns.
        login_response = session.post(EG4_LOGIN_URL, data=login_payload, allow_redirects=True, timeout=10)
        login_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Assuming the login endpoint returns JSON
        login_data = login_response.json()

        if login_data.get('code') == 0: # Common success code
            log_message("INFO", "Successfully logged in to EG4 portal.")
        else:
            log_message("ERROR", f"EG4 Login failed: {login_data.get('msg', 'Unknown error')} (Code: {login_data.get('code', 'N/A')})")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        log_message("ERROR", f"Network or HTTP error during EG4 login: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        log_message("ERROR", f"Failed to decode JSON from EG4 login response. Response content: {login_response.text[:200]}...")
        sys.exit(1)

    # --- 3. Determine EG4 Plant ID (Station ID) ---
    current_plant_id = eg4_station_id
    if not current_plant_id:
        log_message("INFO", "EG4_STATION_ID not provided. Attempting to fetch plant list and auto-select the first one.")
        try:
            # Need to update Referer for the plant list request
            session.headers.update({'Referer': 'https://monitor.eg4electronics.com/WManage/web/plant/overview'})
            plant_list_response = session.post(EG4_GET_PLANT_LIST_URL, data={'page': 1, 'limit': 10}, timeout=10)
            plant_list_response.raise_for_status()
            plant_list_data = plant_list_response.json()

            if plant_list_data.get('code') == 0 and 'data' in plant_list_data and 'list' in plant_list_data['data']:
                plants = plant_list_data['data']['list']
                if plants:
                    current_plant_id = plants[0].get('plantId')
                    plant_name = plants[0].get('name', 'N/A')
                    log_message("INFO", f"Auto-selected Plant ID: {current_plant_id} (Name: {plant_name})")
                else:
                    log_message("ERROR", "No plants found in the EG4 account.")
                    sys.exit(1)
            else:
                log_message("ERROR", f"Failed to fetch plant list from EG4: {plant_list_data.get('msg', 'Unknown error')} (Code: {plant_list_data.get('code', 'N/A')})")
                sys.exit(1)

        except requests.exceptions.RequestException as e:
            log_message("ERROR", f"Network or HTTP error during fetching EG4 plant list: {e}")
            sys.exit(1)
        except json.JSONDecodeError:
            log_message("ERROR", f"Failed to decode JSON from EG4 plant list response. Response content: {plant_list_response.text[:200]}...")
            sys.exit(1)
    else:
        log_message("INFO", f"Using provided EG4_STATION_ID: {current_plant_id}")

    if not current_plant_id:
        log_message("ERROR", "Could not determine EG4 Plant ID. Exiting.")
        sys.exit(1)

    # --- 4. Fetch Realtime Data from EG4 Portal ---
    log_message("INFO", f"Fetching realtime data for Plant ID: {current_plant_id}")
    realtime_data_payload = {'plantId': current_plant_id}
    try:
        session.headers.update({'Referer': 'https://monitor.eg4electronics.com/WManage/web/plant/overview'})
        realtime_response = session.post(EG4_GET_REALTIME_DATA_URL, data=realtime_data_payload, timeout=10)
        realtime_response.raise_for_status()
        realtime_data = realtime_response.json()

        if realtime_data.get('code') == 0 and 'data' in realtime_data:
            eg4_metrics = realtime_data['data']
            log_message("DEBUG", f"Raw EG4 Realtime Data: {eg4_metrics}")

            # --- Map EG4 data to Sensecraft format ---
            # These key names are best guesses based on common portal structures.
            # Actual names might differ. User may need to inspect `eg4_metrics` output.
            pv_power = eg4_metrics.get('currentPower', 0) # Often inverter output / PV power
            battery_soc = eg4_metrics.get('batterySoc', 0) # Battery State of Charge
            load_power = eg4_metrics.get('loadPower', 0)   # Home/Load consumption power

            # Ensure values are numeric, default to 0 if not found or invalid
            try:
                pv_power = float(pv_power)
                battery_soc = float(battery_soc)
                load_power = float(load_power)
            except (ValueError, TypeError) as e:
                log_message("WARNING", f"Could not convert one or more EG4 metrics to float (PV: {pv_power}, SOC: {battery_soc}, Load: {load_power}). Error: {e}. Defaulting to 0.")
                pv_power, battery_soc, load_power = 0.0, 0.0, 0.0

            log_message("INFO", f"EG4 Data - PV Power: {pv_power}W, Battery SOC: {battery_soc}%, Load Power: {load_power}W")

            # --- 5. Format and Push to Sensecraft API ---
            sensecraft_payload = {
                "device_id": SENSECRAFT_DEVICE_ID,
                "data": {
                    "pv_power": pv_power,
                    "battery_soc": battery_soc,
                    "load_power": load_power
                }
            }

            sensecraft_headers = {
                "api-key": sensecraft_key,
                "Content-Type": "application/json"
            }

            log_message("INFO", "Pushing data to Sensecraft API...")
            sensecraft_response = requests.post(
                SENSECRAFT_PUSH_DATA_URL,
                headers=sensecraft_headers,
                json=sensecraft_payload,
                timeout=10
            )
            sensecraft_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            sensecraft_result = sensecraft_response.json()
            if sensecraft_result.get('status') == 0: # Assuming 0 is success for Sensecraft
                log_message("INFO", "Successfully pushed data to Sensecraft API.")
            else:
                log_message("ERROR", f"Failed to push data to Sensecraft API: {sensecraft_result.get('msg', 'Unknown error')} (Status: {sensecraft_result.get('status', 'N/A')})")
                sys.exit(1)

        else:
            log_message("ERROR", f"Failed to fetch realtime data from EG4: {realtime_data.get('msg', 'Unknown error')} (Code: {realtime_data.get('code', 'N/A')})")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        log_message("ERROR", f"Network or HTTP error during EG4 data fetch or Sensecraft push: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        log_message("ERROR", f"Failed to decode JSON from EG4 realtime data or Sensecraft response. Response content: {realtime_response.text[:200]}...")
        sys.exit(1)
    except Exception as e:
        log_message("ERROR", f"An unexpected error occurred: {e}")
        sys.exit(1)

    log_message("INFO", "Script execution completed successfully.")

if __name__ == "__main__":
    main()
