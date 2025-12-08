import os
import sys
import requests
import json
import re

# --- Configuration ---
EG4_BASE_URL = "https://monitor.eg4electronics.com"
EG4_LOGIN_PATH = "/WManage/web/login"
EG4_DATA_PATH = "/WManage/api/device/getData" # This path often requires specific parameters

SENSECRAFT_API_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"
SENSECRAFT_DEVICE_ID = 20221942 # As specified by the user

# --- Environment Variable Names ---
ENV_EG4_USER = 'EG4_USER'
ENV_EG4_PASS = 'EG4_PASS'
ENV_EG4_STATION_ID = 'EG4_STATION_ID' # This is crucial for EG4 data fetching
ENV_SENSECRAFT_KEY = 'SENSECRAFT_KEY'

def load_env_vars():
    """Loads environment variables and performs basic validation."""
    config = {}
    missing_vars = []

    config['eg4_user'] = os.environ.get(ENV_EG4_USER)
    config['eg4_pass'] = os.environ.get(ENV_EG4_PASS)
    config['eg4_station_id'] = os.environ.get(ENV_EG4_STATION_ID)
    config['sensecraft_key'] = os.environ.get(ENV_SENSECRAFT_KEY)

    for key, value in config.items():
        if value is None:
            missing_vars.append(key.upper())

    if missing_vars:
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set them before running the script.", file=sys.stderr)
        sys.exit(1)
    return config

def get_csrf_token(session, url):
    """
    Fetches the login page to extract the CSRF token.
    EG4 uses CSRF protection on its login form.
    """
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        match = re.search(r'<input type="hidden" name="_csrf" value="([^"]+)">', response.text)
        if match:
            return match.group(1)
        else:
            print("Error: CSRF token not found on EG4 login page.", file=sys.stderr)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching EG4 login page for CSRF token: {e}", file=sys.stderr)
        return None

def main():
    """Main function to perform data bridging."""
    config = load_env_vars()

    eg4_user = config['eg4_user']
    eg4_pass = config['eg4_pass']
    eg4_station_id = config['eg4_station_id']
    sensecraft_key = config['sensecraft_key']

    eg4_login_url = f"{EG4_BASE_URL}{EG4_LOGIN_PATH}"
    eg4_data_url = f"{EG4_BASE_URL}{EG4_DATA_PATH}"

    eg4_data = {
        "pv_power": None,
        "battery_soc": None,
        "load_power": None,
    }

    # --- Step 1: Login to EG4 Portal and fetch data ---
    with requests.Session() as session:
        print("Attempting to log in to EG4 portal...")
        
        # 1. Get CSRF token
        csrf_token = get_csrf_token(session, eg4_login_url)
        if not csrf_token:
            sys.exit(1)
        print("CSRF token obtained.")

        # 2. Perform Login POST request
        login_payload = {
            "username": eg4_user,
            "password": eg4_pass,
            "_csrf": csrf_token # Include the CSRF token
        }
        login_headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            login_response = session.post(eg4_login_url, data=login_payload, headers=login_headers, timeout=15, allow_redirects=False)
            
            # EG4 login typically redirects on success. Check for redirect or success status.
            if login_response.status_code == 302: # Redirect indicates successful login
                print("Successfully logged in to EG4 portal (redirect detected).")
            elif login_response.status_code == 200: # Could be direct success or an error page
                 if "Sign In" in login_response.text or "Incorrect username or password" in login_response.text:
                    print(f"Error: EG4 login failed. Status: {login_response.status_code}, Response: {login_response.text}", file=sys.stderr)
                    sys.exit(1)
                 else:
                     print("Successfully logged in to EG4 portal (direct success page).")
            else:
                print(f"Error: EG4 login failed with status code {login_response.status_code}", file=sys.stderr)
                sys.exit(1)

        except requests.exceptions.RequestException as e:
            print(f"Error during EG4 login: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"Attempting to fetch data from EG4 station ID: {eg4_station_id}...")
        data_payload = json.dumps({"stationId": eg4_station_id})
        data_headers = {
            "Content-Type": "application/json"
        }

        try:
            data_response = session.post(eg4_data_url, data=data_payload, headers=data_headers, timeout=15)
            data_response.raise_for_status()
            eg4_raw_data = data_response.json()
            
            # Check EG4 API response structure
            if eg4_raw_data.get('code') == 0 and 'obj' in eg4_raw_data:
                obj_data = eg4_raw_data['obj']
                eg4_data["pv_power"] = obj_data.get('pvPower')
                eg4_data["battery_soc"] = obj_data.get('batterySoc')
                eg4_data["load_power"] = obj_data.get('loadPower')
                
                print("Successfully fetched data from EG4:")
                print(f"  PV Power: {eg4_data['pv_power']}W")
                print(f"  Battery SOC: {eg4_data['battery_soc']}%")
                print(f"  Load Power: {eg4_data['load_power']}W")

                if any(v is None for v in eg4_data.values()):
                    print("Warning: Some expected data fields were missing from EG4 response.", file=sys.stderr)
                    print(f"Full EG4 response for debugging: {json.dumps(eg4_raw_data, indent=2)}", file=sys.stderr)

            else:
                print(f"Error: EG4 data API returned an error or unexpected structure: {eg4_raw_data.get('msg', 'Unknown error')}", file=sys.stderr)
                print(f"Full EG4 response for debugging: {json.dumps(eg4_raw_data, indent=2)}", file=sys.stderr)
                sys.exit(1)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from EG4: {e}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error decoding EG4 data response as JSON: {e}", file=sys.stderr)
            print(f"Raw response: {data_response.text}", file=sys.stderr)
            sys.exit(1)
        except KeyError as e:
            print(f"Error: Missing expected key in EG4 response data: {e}", file=sys.stderr)
            print(f"Full EG4 response for debugging: {json.dumps(eg4_raw_data, indent=2)}", file=sys.stderr)
            sys.exit(1)
    
    # --- Step 2: Format and push data to Sensecraft API ---
    print("Preparing data for Sensecraft API...")
    sensecraft_payload = {
        "device_id": SENSECRAFT_DEVICE_ID,
        "data": {
            "pv_power": eg4_data["pv_power"] if eg4_data["pv_power"] is not None else 0, # Send 0 if None
            "battery_soc": eg4_data["battery_soc"] if eg4_data["battery_soc"] is not None else 0,
            "load_power": eg4_data["load_power"] if eg4_data["load_power"] is not None else 0
        }
    }

    sensecraft_headers = {
        "api-key": sensecraft_key,
        "Content-Type": "application/json"
    }

    print("Pushing data to Sensecraft API...")
    try:
        sensecraft_response = requests.post(
            SENSECRAFT_API_URL,
            headers=sensecraft_headers,
            json=sensecraft_payload,
            timeout=10
        )
        sensecraft_response.raise_for_status()
        
        print("Successfully pushed data to Sensecraft API.")
        print(f"Sensecraft Response: {sensecraft_response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error pushing data to Sensecraft API: {e}", file=sys.stderr)
        if hasattr(sensecraft_response, 'text'):
            print(f"Sensecraft Error Response: {sensecraft_response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during Sensecraft push: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()