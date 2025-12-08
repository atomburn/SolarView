import os
import requests
import json
import re
import sys

# --- Configuration ---
SCRIPT_VERSION = "2.3 (Endpoint Scanner)"

# EG4 Portal URLs
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_PLANT_LIST_URL = "https://monitor.eg4electronics.com/WManage/web/plant/plantList" # For auto-detection

# EG4 Data Fetch Endpoints (in order of preference)
EG4_DATA_ENDPOINTS = [
    {"name": "Power Flow", "url": "https://monitor.eg4electronics.com/WManage/web/plant/currPowerFlow"},
    {"name": "Inverter List", "url": "https://monitor.eg4electronics.com/WManage/web/device/inverter/list"},
    {"name": "Plant Overview", "url": "https://monitor.eg4electronics.com/WManage/web/plant/overview"},
    {"name": "Old Realtime", "url": "https://monitor.eg4electronics.com/WManage/web/plant/getRealtimeData"},
]

# Sensecraft API URL
SENSECRAFT_PUSH_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"

# Sensecraft Device ID (hardcoded as per prompt example)
SENSECRAFT_DEVICE_ID = 20221942

# Environment Variable Names
ENV_EG4_USER = 'EG4_USER'
ENV_EG4_PASS = 'EG4_PASS'
ENV_EG4_STATION_ID = 'EG4_STATION_ID'
ENV_SENSECRAFT_KEY = 'SENSECRAFT_KEY'

# --- Helper Functions ---

def load_config():
    """Loads configuration from environment variables."""
    config = {}
    
    config[ENV_EG4_USER] = os.environ.get(ENV_EG4_USER)
    config[ENV_EG4_PASS] = os.environ.get(ENV_EG4_PASS)
    config[ENV_SENSECRAFT_KEY] = os.environ.get(ENV_SENSECRAFT_KEY)
    config[ENV_EG4_STATION_ID] = os.environ.get(ENV_EG4_STATION_ID) # Optional/auto-detected
    
    missing_mandatory = []
    if not config[ENV_EG4_USER]:
        missing_mandatory.append(ENV_EG4_USER)
    if not config[ENV_EG4_PASS]:
        missing_mandatory.append(ENV_EG4_PASS)
    if not config[ENV_SENSECRAFT_KEY]:
        missing_mandatory.append(ENV_SENSECRAFT_KEY)
        
    if missing_mandatory:
        print(f"ERROR: Missing mandatory environment variables: {', '.join(missing_mandatory)}")
        sys.exit(1)
        
    if not config[ENV_EG4_STATION_ID]:
        print(f"WARNING: {ENV_EG4_STATION_ID} not set. Will attempt to auto-detect the first available station ID after login.")
    
    return config

def login_to_eg4(session, username, password):
    """
    Logs into the EG4 Electronics Monitoring Portal using requests.Session.
    Implements Login Fix V2.2 logic by checking for login form presence after request.
    """
    print(f"Attempting to log in to EG4 portal for user: {username}...")
    login_data = {
        'account': username,
        'password': password,
        'isRem': 'false',
        'lang': 'en_US'
    }
    login_headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = session.post(EG4_LOGIN_URL, data=login_data, headers=login_headers, allow_redirects=True, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        # Login Fix V2.2 logic: Check if we were redirected back to the login page
        # This typically indicates failed login credentials.
        # Look for typical login page elements (form with login-form class, or account input field)
        if "login-form" in response.text or f'name="account" value="{username}"' in response.text:
            print("ERROR: Login failed. Credentials might be incorrect or the server rejected the login.")
            return False
        
        print(f"Successfully logged in. Current URL: {response.url}")
        return True

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error during EG4 login: {e}")
        print(f"Response content: {e.response.text[:200]}...") # Print partial response for debugging
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error during EG4 login: {e}")
        return False
    except requests.exceptions.Timeout:
        print("Timeout error during EG4 login.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"An unexpected error occurred during EG4 login: {e}")
        return False

def auto_detect_station_id(session):
    """
    Attempts to auto-detect the first available station ID after login.
    """
    print("Attempting to auto-detect EG4 station ID...")
    try:
        response = session.post(EG4_PLANT_LIST_URL, json={'page': 1, 'rows': 10}, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and 'rows' in data and data['rows']:
            first_plant_id = data['rows'][0].get('plantId')
            if first_plant_id:
                print(f"Auto-detected EG4 station ID: {first_plant_id}")
                return first_plant_id
            else:
                print("Could not find 'plantId' in the first plant entry.")
        else:
            print("No plant list found or list is empty.")
            
    except requests.exceptions.RequestException as e:
        print(f"Error auto-detecting station ID: {e}")
    except json.JSONDecodeError:
        print("Error decoding JSON from plant list endpoint. Response might not be JSON.")
    
    return None

def fetch_data_with_fallback(session, station_id):
    """
    Fetches data from EG4 portal using a series of fallback endpoints.
    Returns a dictionary with 'pv_power', 'battery_soc', 'load_power' or None if all fail.
    """
    print(f"Fetching data for station ID: {station_id} using smart endpoint scanner...")
    
    # Initialize with None so we know what data was not found
    result_data = {
        "pv_power": None,
        "battery_soc": None,
        "load_power": None
    }

    for endpoint_info in EG4_DATA_ENDPOINTS:
        name = endpoint_info['name']
        url = endpoint_info['url']
        payload = {'plantId': station_id}
        
        print(f"  Trying endpoint: {name} ({url})...")
        
        try:
            # Adjust payload for 'inverter/list' as it needs paging info
            if name == "Inverter List":
                payload = {'page': 1, 'rows': 10, 'plantId': station_id} # Fetch up to 10 inverters
            
            response = session.post(url, json=payload, timeout=15)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            json_data = response.json()
            
            # --- Data Extraction Logic based on endpoint name ---
            current_pv_power = 0.0
            current_load_power = 0.0
            current_soc_sum = 0.0
            current_soc_count = 0

            # Helper to get float values safely
            def get_float_val(data_dict, *keys):
                for key in keys:
                    val = data_dict.get(key)
                    if val is not None:
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            pass # Not a float, try next key or return None
                return None

            if name == "Power Flow":
                data_root = json_data.get('data', json_data) # Check for 'data' key or use root
                pv_power = get_float_val(data_root, 'pvPower')
                soc = get_float_val(data_root, 'soc')
                load_power = get_float_val(data_root, 'loadPower')
                
                if all(v is not None for v in [pv_power, soc, load_power]):
                    result_data["pv_power"] = pv_power
                    result_data["battery_soc"] = soc
                    result_data["load_power"] = load_power
                    print(f"  Successfully fetched data from '{name}'.")
                    return result_data

            elif name == "Inverter List":
                if 'rows' in json_data and json_data['rows']:
                    for inverter in json_data['rows']:
                        current_pv_power += get_float_val(inverter, 'pvPower') or 0.0
                        current_load_power += get_float_val(inverter, 'loadPower') or 0.0
                        soc_val = get_float_val(inverter, 'soc')
                        if soc_val is not None:
                            current_soc_sum += soc_val
                            current_soc_count += 1
                    
                    if current_pv_power > 0 or current_load_power > 0 or current_soc_count > 0:
                        result_data["pv_power"] = current_pv_power
                        result_data["load_power"] = current_load_power
                        result_data["battery_soc"] = current_soc_sum / current_soc_count if current_soc_count > 0 else 0.0
                        print(f"  Successfully fetched and aggregated data from '{name}'.")
                        return result_data
                
            elif name == "Plant Overview":
                # This endpoint often provides summary data. Keys can vary.
                data_root = json_data.get('data', json_data)
                
                pv_power = get_float_val(data_root, 'pvPower', 'currPower', 'pvTotalPower')
                load_power = get_float_val(data_root, 'loadPower', 'currLoadPower', 'loadTotalPower')
                soc = get_float_val(data_root, 'soc', 'batterySoc', 'battery_soc')
                
                # Further nested checks if needed
                if pv_power is None and 'currPower' in data_root and isinstance(data_root['currPower'], dict):
                    pv_power = get_float_val(data_root['currPower'], 'pv')
                    load_power = get_float_val(data_root['currPower'], 'load')
                if soc is None and 'battery' in data_root and isinstance(data_root['battery'], dict):
                    soc = get_float_val(data_root['battery'], 'soc')
                
                if all(v is not None for v in [pv_power, soc, load_power]):
                    result_data["pv_power"] = pv_power
                    result_data["load_power"] = load_power
                    result_data["battery_soc"] = soc
                    print(f"  Successfully fetched data from '{name}'.")
                    return result_data

            elif name == "Old Realtime":
                # Assuming structure similar to Power Flow or Plant Overview
                data_root = json_data.get('data', json_data)
                pv_power = get_float_val(data_root, 'pvPower')
                soc = get_float_val(data_root, 'soc')
                load_power = get_float_val(data_root, 'loadPower')
                
                if all(v is not None for v in [pv_power, soc, load_power]):
                    result_data["pv_power"] = pv_power
                    result_data["battery_soc"] = soc
                    result_data["load_power"] = load_power
                    print(f"  Successfully fetched data from '{name}'.")
                    return result_data

            print(f"  Endpoint '{name}' received a 200 OK, but expected data keys (pvPower, soc, loadPower) were not found or incomplete.")

        except requests.exceptions.HTTPError as e:
            print(f"  Endpoint '{name}' failed with HTTP error: {e.response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"  Endpoint '{name}' failed with connection error: {e}")
        except requests.exceptions.Timeout:
            print(f"  Endpoint '{name}' failed due to timeout.")
        except json.JSONDecodeError:
            print(f"  Endpoint '{name}' returned non-JSON response or invalid JSON.")
        except Exception as e:
            print(f"  An unexpected error occurred with endpoint '{name}': {e}")
        
        # Continue to next endpoint if this one failed or didn't provide complete data
        
    print("ERROR: All EG4 data fetching endpoints failed or did not provide complete data.")
    return None # All attempts failed

def push_to_sensecraft(sensecraft_api_key, data_payload):
    """
    Pushes data to the Sensecraft API.
    """
    print("Pushing data to Sensecraft API...")
    
    headers = {
        'api-key': sensecraft_api_key,
        'Content-Type': 'application/json'
    }
    
    # Construct the body, ensuring values are floats or None as specified
    push_body = {
        "device_id": SENSECRAFT_DEVICE_ID,
        "data": {
            "pv_power": data_payload.get("pv_power"),
            "battery_soc": data_payload.get("battery_soc"),
            "load_power": data_payload.get("load_power")
        }
    }

    try:
        response = requests.post(SENSECRAFT_PUSH_URL, headers=headers, json=push_body, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        print("Data successfully pushed to Sensecraft API.")
        print(f"Sensecraft Response: {response.json()}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP error pushing to Sensecraft: {e}")
        print(f"Sensecraft Error Response: {e.response.text}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection error pushing to Sensecraft: {e}")
        return False
    except requests.exceptions.Timeout:
        print("ERROR: Timeout error pushing to Sensecraft.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: An unexpected error occurred pushing to Sensecraft: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Script Version: {SCRIPT_VERSION}")

    config = load_config()

    eg4_user = config[ENV_EG4_USER]
    eg4_pass = config[ENV_EG4_PASS]
    sensecraft_key = config[ENV_SENSECRAFT_KEY]
    eg4_station_id = config[ENV_EG4_STATION_ID]

    session = requests.Session()

    # 1. Login to EG4 Portal
    if not login_to_eg4(session, eg4_user, eg4_pass):
        print("Script failed at EG4 login.")
        sys.exit(1)

    # Resolve EG4 Station ID
    if not eg4_station_id:
        eg4_station_id = auto_detect_station_id(session)
        if not eg4_station_id:
            print("ERROR: Could not determine EG4 Station ID. Please set the EG4_STATION_ID environment variable or ensure auto-detection works.")
            sys.exit(1)
    else:
        print(f"Using provided EG4 Station ID: {eg4_station_id}")

    # 2. Fetch Data from EG4 Portal
    eg4_data = fetch_data_with_fallback(session, eg4_station_id)
    if not eg4_data:
        print("Script failed to fetch data from EG4 portal.")
        sys.exit(1)
    
    print(f"Fetched EG4 Data: {eg4_data}")

    # 3. Format and Push to Sensecraft API
    if not push_to_sensecraft(sensecraft_key, eg4_data):
        print("Script failed to push data to Sensecraft API.")
        sys.exit(1)

    print("Script completed successfully.")
