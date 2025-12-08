import os
import requests
import json
import sys

# --- Configuration ---
# Base URL for the EG4 Electronics Monitoring Portal
EG4_BASE_URL = "https://monitor.eg4electronics.com"
# Specific paths for login, plant list, and real-time data
EG4_LOGIN_PATH = "/WManage/web/login"
EG4_PLANT_LIST_PATH = "/PlantList/getPlantList"
EG4_REALTIME_DATA_PATH = "/PlantData/getRealtimeData"

# Sensecraft API endpoint and device ID
SENSECRAFT_API_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"
SENSECRAFT_DEVICE_ID = 20221942 # Hardcoded as per user requirement

# --- Load Environment Variables ---
# EG4 credentials
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID') # Optional: if not set, script will auto-detect

# Sensecraft API key
SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')

def check_env_vars():
    """
    Checks for mandatory environment variables and prints a warning/error message.
    Exits the script if critical variables are missing.
    """
    missing_vars = []
    if not EG4_USER:
        missing_vars.append('EG4_USER')
    if not EG4_PASS:
        missing_vars.append('EG4_PASS')
    if not SENSECRAFT_KEY:
        missing_vars.append('SENSECRAFT_KEY')

    if missing_vars:
        print(f"ERROR: The following critical environment variables are missing: {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set them before running the script.", file=sys.stderr)
        sys.exit(1)
    
    if not EG4_STATION_ID:
        print("WARNING: EG4_STATION_ID not provided. The script will attempt to auto-detect the first available plant.", file=sys.stderr)

def eg4_login(session: requests.Session) -> bool:
    """
    Attempts to log in to the EG4 Electronics Monitoring Portal.
    Maintains session state (cookies).
    Returns True if login is successful (indicated by a redirect to /web/home), False otherwise.
    """
    login_url = f"{EG4_BASE_URL}{EG4_LOGIN_PATH}"
    print(f"Attempting to log in to EG4 portal at {login_url}...")

    login_data = {
        'account': EG4_USER,
        'password': EG4_PASS,
        'isRem': 'false', # "Remember me" checkbox
        'lang': 'en_US'  # Language setting
    }

    try:
        # A POST request to the login endpoint.
        # allow_redirects=False lets us check for the 302 redirect specifically.
        response = session.post(login_url, data=login_data, allow_redirects=False, timeout=10)

        # Successful login typically results in a 302 redirect to '/web/home'
        if response.status_code == 302 and response.headers.get('Location') == '/web/home':
            print("Successfully logged in to EG4 portal.")
            # Follow the redirect to properly initialize the session for subsequent requests
            session.get(f"{EG4_BASE_URL}/web/home", timeout=10) 
            return True
        elif response.status_code == 200:
            # If status 200, it often means login failed and the page was re-rendered.
            if "Incorrect username or password" in response.text:
                print("EG4 Login failed: Incorrect username or password.", file=sys.stderr)
            else:
                print(f"EG4 Login failed: Received status code 200, but not redirected. "
                      f"Response might indicate a login failure. Excerpt: {response.text[:200]}...", file=sys.stderr)
        else:
            print(f"EG4 Login failed: Unexpected HTTP status code {response.status_code}. "
                  f"Response: {response.text[:200]}...", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"Network error during EG4 login: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred during EG4 login: {e}", file=sys.stderr)
        return False

def get_eg4_station_id(session: requests.Session) -> str | None:
    """
    Retrieves the EG4 station (plant) ID.
    If EG4_STATION_ID environment variable is set, it uses that.
    Otherwise, it fetches the list of plants associated with the user and returns the ID
    of the first one found.
    Returns the station ID as a string, or None on failure.
    """
    if EG4_STATION_ID:
        print(f"Using provided EG4_STATION_ID: {EG4_STATION_ID}")
        return EG4_STATION_ID
    
    print("EG4_STATION_ID not provided. Attempting to fetch plant list to auto-detect...")
    plant_list_url = f"{EG4_BASE_URL}{EG4_PLANT_LIST_PATH}"

    try:
        response = session.get(plant_list_url, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        plant_data = response.json()
        
        if not plant_data or not isinstance(plant_data, list):
            print("No plants found or unexpected response format for EG4 plant list.", file=sys.stderr)
            return None
        
        # Select the first plant from the list
        first_plant = plant_data[0]
        first_plant_id = str(first_plant.get('id'))
        first_plant_name = first_plant.get('plantName', 'N/A')

        if not first_plant_id:
            print("Could not extract ID from the first plant in the list.", file=sys.stderr)
            return None

        print(f"Automatically selected first plant found: ID='{first_plant_id}', Name='{first_plant_name}'")
        return first_plant_id
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching EG4 plant list: {e}", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from EG4 plant list response. Response: {response.text[:200]}", file=sys.stderr)
    except IndexError:
        print("No plants found in the list after parsing JSON.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred while getting EG4 station ID: {e}", file=sys.stderr)
    return None

def get_eg4_inverter_data(session: requests.Session, station_id: str) -> dict | None:
    """
    Fetches real-time inverter data for a given EG4 station ID.
    Returns a dictionary with 'pv_power', 'battery_soc', 'load_power' or None on failure.
    """
    data_url = f"{EG4_BASE_URL}{EG4_REALTIME_DATA_PATH}"
    print(f"Fetching real-time data for EG4 station ID: {station_id}...")
    
    # The EG4 portal uses a POST request with 'plantId' in form data for this endpoint.
    payload = {'plantId': station_id}

    try:
        response = session.post(data_url, data=payload, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        raw_data = response.json()
        
        # Extracting required fields based on observed EG4 API response structure
        # realTimePower is a nested object
        pv_power = raw_data.get('realTimePower', {}).get('pvPower')
        load_power = raw_data.get('realTimePower', {}).get('loadPower')
        # SOC is often directly at the top level
        battery_soc = raw_data.get('soc') 
        
        # Basic validation that we got values
        if pv_power is None or load_power is None or battery_soc is None:
            print(f"EG4 Data extraction failed: One or more data fields (PV Power, Load Power, Battery SOC) were missing or null. "
                  f"PV Power: {pv_power}, Load Power: {load_power}, Battery SOC: {battery_soc}", file=sys.stderr)
            print(f"Raw response excerpt: {json.dumps(raw_data, indent=2)[:500]}", file=sys.stderr)
            return None

        # Convert extracted values to float, handling potential type errors
        try:
            pv_power = float(pv_power)
            load_power = float(load_power)
            battery_soc = float(battery_soc)
        except (ValueError, TypeError) as e:
            print(f"EG4 Data conversion error: Could not convert extracted values to numbers. "
                  f"Error: {e}. Data: PV='{pv_power}', Load='{load_power}', SOC='{battery_soc}'", file=sys.stderr)
            return None

        print(f"EG4 Data retrieved: PV Power={pv_power}W, Load Power={load_power}W, Battery SOC={battery_soc}%")
        
        return {
            "pv_power": pv_power,
            "battery_soc": battery_soc,
            "load_power": load_power
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching EG4 inverter data: {e}", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from EG4 inverter data response. Response: {response.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred while getting EG4 inverter data: {e}", file=sys.stderr)
    return None

def push_to_sensecraft(data: dict) -> bool:
    """
    Pushes the formatted inverter data to the Sensecraft API.
    Returns True on successful push, False otherwise.
    """
    print("Attempting to push data to Sensecraft API...")

    if not SENSECRAFT_KEY:
        print("Sensecraft API key (SENSECRAFT_KEY) is not set. Cannot push data.", file=sys.stderr)
        return False

    headers = {
        'api-key': SENSECRAFT_KEY,
        'Content-Type': 'application/json'
    }

    payload = {
        "device_id": SENSECRAFT_DEVICE_ID,
        "data": data
    }

    try:
        response = requests.post(SENSECRAFT_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        print("Data successfully pushed to Sensecraft API.")
        print(f"Sensecraft response ({response.status_code}): {response.text}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Network error pushing data to Sensecraft API: {e}", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Sensecraft response. Response: {response.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred while pushing data to Sensecraft: {e}", file=sys.stderr)
    return False

def main():
    """
    Main function to orchestrate the data fetching and pushing process.
    """
    check_env_vars()

    # Use a requests.Session to persist cookies across requests (important for login)
    session = requests.Session()
    
    try:
        # Step 1: Login to EG4 portal
        if not eg4_login(session):
            print("Critical error: EG4 login failed. Exiting.", file=sys.stderr)
            sys.exit(1)
        
        # Step 2: Get the station ID (either from env var or auto-detected)
        station_id = get_eg4_station_id(session)
        if not station_id:
            print("Critical error: Failed to determine EG4 station ID. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        # Step 3: Fetch inverter data from EG4 portal
        inverter_data = get_eg4_inverter_data(session, station_id)
        if not inverter_data:
            print("Critical error: Failed to retrieve EG4 inverter data. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        # Step 4: Push the data to Sensecraft API
        if not push_to_sensecraft(inverter_data):
            print("Critical error: Failed to push data to Sensecraft API. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        print("Script completed successfully: EG4 data relayed to Sensecraft.")

    except Exception as e:
        print(f"An unhandled critical error occurred during script execution: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Close the session to release resources
        session.close()

if __name__ == "__main__":
    main()
