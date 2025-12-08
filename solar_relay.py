import os
import requests
import re
import json

# Script Version
print("Script Version: 2.6 (Sanity Check + Deep Scraper)")

# --- Configuration ---
# EG4 Portal URLs
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_INVERTER_DATA_URL = "https://monitor.eg4electronics.com/WManage/web/monitor/inverter"

# Sensecraft API URL
SENSECRAFT_API_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"

# --- Load Environment Variables ---
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID')
SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')

# Check for required environment variables
missing_vars = []
if not EG4_USER:
    missing_vars.append('EG4_USER')
if not EG4_PASS:
    missing_vars.append('EG4_PASS')
if not SENSECRAFT_KEY:
    missing_vars.append('SENSECRAFT_KEY')

if missing_vars:
    print(f"ERROR: The following environment variables are not set: {', '.join(missing_vars)}")
    exit(1)

if not EG4_STATION_ID:
    print("WARNING: EG4_STATION_ID environment variable not set. Using default '20221942' for Sensecraft device_id.")
    EG4_STATION_ID = "20221942" # Default device_id if not provided

print(f"Using Sensecraft Device ID: {EG4_STATION_ID}")

# --- Initialize Session ---
session = requests.Session()
eg4_login_success = False

# --- 1. Login to EG4 Electronics Monitoring Portal ---
print("\n--- EG4 Login ---")
login_data = {
    'account': EG4_USER,
    'password': EG4_PASS,
    'isRem': 'false',
    'lang': 'en_US'
}
login_headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

try:
    login_response = session.post(EG4_LOGIN_URL, data=login_data, headers=login_headers, timeout=10, allow_redirects=True)
    login_response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

    # Check for successful login.
    # A common indicator is a redirect away from the login page, or specific success text.
    if login_response.url != EG4_LOGIN_URL or "login-success" in login_response.text.lower() or "登录成功" in login_response.text:
        print("EG4 Login successful.")
        eg4_login_success = True
    else:
        print(f"EG4 Login failed. Response status: {login_response.status_code}")
        print(f"Response content snippet: {login_response.text[:500]}...")
except requests.exceptions.RequestException as e:
    print(f"EG4 Login failed due to network or HTTP error: {e}")
except Exception as e:
    print(f"An unexpected error occurred during EG4 Login: {e}")

if not eg4_login_success:
    print("Cannot proceed without successful EG4 login.")
    exit(1)

# --- 2. SANITY CHECK (Sensecraft API Connection Verification) ---
print("\n--- SANITY CHECK ---")
sanity_check_passed = False
sensecraft_headers = {
    'api-key': SENSECRAFT_KEY,
    'Content-Type': 'application/json'
}
test_payload = {
    "device_id": EG4_STATION_ID,
    "data": { "battery_soc": 50, "pv_power": 100, "load_power": 100 }
}

try:
    sanity_response = requests.post(SENSECRAFT_API_URL, headers=sensecraft_headers, json=test_payload, timeout=10)
    
    if sanity_response.status_code == 200:
        print("SUCCESS: Sensecraft connection verified.")
        sanity_check_passed = True
    else:
        print(f"FAILURE: Sensecraft returned error. Status code: {sanity_response.status_code}")
        print(f"Error details: {sanity_response.text}")
except requests.exceptions.RequestException as e:
    print(f"FAILURE: Sensecraft connection failed due to network or HTTP error: {e}")
except Exception as e:
    print(f"An unexpected error occurred during Sensecraft sanity check: {e}")

# --- 3. DATA ACQUISITION from EG4 Monitoring Portal ---
print("\n--- EG4 Data Acquisition ---")
scraped_pv_power = 0
scraped_battery_soc = 0
scraped_load_power = 0

if eg4_login_success: # Ensure login was successful before attempting to get data
    try:
        inverter_data_response = session.get(EG4_INVERTER_DATA_URL, timeout=15)
        inverter_data_response.raise_for_status()
        html_content = inverter_data_response.text

        # Regex strategy: Look for 'var cache_inv_datas = { ... };' or similar JS object
        # The prompt mentioned 'cache_inv_datas' (plural) but it could also be singular 'cache_inv_data'
        js_data_match = re.search(r'var\s+cache_inv_datas?\s*=\s*(\{.*?\});', html_content, re.DOTALL)

        if js_data_match:
            json_str = js_data_match.group(1)
            try:
                # Attempt to parse the captured string as JSON
                inv_data = json.loads(json_str)

                # Assuming common keys like curPvPower, curBatSoc, curLoadPower within the JS object
                scraped_pv_power = int(inv_data.get('curPvPower', 0))
                scraped_battery_soc = int(inv_data.get('curBatSoc', 0))
                scraped_load_power = int(inv_data.get('curLoadPower', 0))
                print("Data extracted from JavaScript object (cache_inv_data/datas).")

            except json.JSONDecodeError as e:
                print(f"WARNING: Failed to parse JS object as JSON ({e}). Attempting individual regex within the captured string.")
                # Fallback to individual regex within the captured string if json.loads fails
                pv_match = re.search(r'"curPvPower"\s*:\s*"(\d+)"', json_str)
                soc_match = re.search(r'"curBatSoc"\s*:\s*"(\d+)"', json_str)
                load_match = re.search(r'"curLoadPower"\s*:\s*"(\d+)"', json_str)

                scraped_pv_power = int(pv_match.group(1)) if pv_match else 0
                scraped_battery_soc = int(soc_match.group(1)) if soc_match else 0
                scraped_load_power = int(load_match.group(1)) if load_match else 0
                
                if any([scraped_pv_power, scraped_battery_soc, scraped_load_power]):
                    print("Data extracted using individual regex within JS object string.")
                else:
                    print("WARNING: Could not extract data using individual regex within the JS object string. Values will be 0.")
        else:
            print("WARNING: 'cache_inv_data/datas' JS object not found. Attempting direct regex search for common keys in HTML.")
            
            # Fallback to searching the entire HTML content for the known keys
            pv_match = re.search(r'"curPvPower"\s*:\s*"(\d+)"', html_content)
            soc_match = re.search(r'"curBatSoc"\s*:\s*"(\d+)"', html_content)
            load_match = re.search(r'"curLoadPower"\s*:\s*"(\d+)"', html_content)
            
            scraped_pv_power = int(pv_match.group(1)) if pv_match else 0
            scraped_battery_soc = int(soc_match.group(1)) if soc_match else 0
            scraped_load_power = int(load_match.group(1)) if load_match else 0
            
            if not any([scraped_pv_power, scraped_battery_soc, scraped_load_power]):
                 print("WARNING: Specific EG4 data keys (curPvPower, curBatSoc, curLoadPower) not found in HTML. Values will be 0.")
            else:
                 print("Data extracted using direct regex search for common JS variable keys in HTML.")
        
        # Ensure all values are integers (redundant but safe)
        scraped_pv_power = int(scraped_pv_power)
        scraped_battery_soc = int(scraped_battery_soc)
        scraped_load_power = int(scraped_load_power)

        print(f"Scraped Data: PV Power={scraped_pv_power}W, Battery SOC={scraped_battery_soc}%, Load Power={scraped_load_power}W")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to retrieve EG4 inverter data due to network or HTTP error: {e}")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during EG4 data acquisition: {e}")
else:
    print("Skipping EG4 data acquisition as login was not successful.")


# --- 4. REAL DATA PUSH to Sensecraft ---
print("\n--- Sensecraft Real Data Push ---")
if sanity_check_passed:
    # Only push if at least one meaningful piece of data was scraped
    if any([scraped_pv_power, scraped_battery_soc, scraped_load_power]): 
        real_data_payload = {
            "device_id": EG4_STATION_ID,
            "data": {
                "pv_power": scraped_pv_power,
                "battery_soc": scraped_battery_soc,
                "load_power": scraped_load_power
            }
        }

        try:
            push_response = requests.post(SENSECRAFT_API_URL, headers=sensecraft_headers, json=real_data_payload, timeout=10)
            
            if push_response.status_code == 200:
                print("SUCCESS: Real EG4 data pushed to Sensecraft.")
            else:
                print(f"FAILURE: Sensecraft returned error for real data push. Status code: {push_response.status_code}")
                print(f"Error details: {push_response.text}")
        except requests.exceptions.RequestException as e:
            print(f"FAILURE: Sensecraft real data push failed due to network or HTTP error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during Sensecraft real data push: {e}")
    else:
        print("Skipping real data push to Sensecraft: No meaningful data was scraped from EG4 portal (all values are 0).")
else:
    print("Skipping real data push to Sensecraft: Sanity check failed.")

print("\n--- Script Finished ---")
