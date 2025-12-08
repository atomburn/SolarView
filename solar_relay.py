import requests
import os
import re
import json
import time

print("Script Version: 2.4 (HTML Scraper)")

# --- 1. Load Environment Variables ---
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID') # Optional, will use default if not set
SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')

# Check for essential environment variables
missing_env_vars = []
if not EG4_USER:
    missing_env_vars.append('EG4_USER')
if not EG4_PASS:
    missing_env_vars.append('EG4_PASS')
if not SENSECRAFT_KEY:
    missing_env_vars.append('SENSECRAFT_KEY')

if missing_env_vars:
    print(f"Error: The following environment variables are missing: {', '.join(missing_env_vars)}")
    print("Please set them before running the script.")
    exit(1)

# --- 2. EG4 Monitoring Portal Login ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_DASHBOARD_URL = "https://monitor.eg4electronics.com/WManage/web/monitor/inverter"
EG4_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}
EG4_LOGIN_DATA = {
    'account': EG4_USER,
    'password': EG4_PASS,
    'isRem': 'false',
    'lang': 'en_US'
}

session = requests.Session()
print("Attempting to log in to EG4 portal...")
try:
    login_response = session.post(EG4_LOGIN_URL, data=EG4_LOGIN_DATA, headers=EG4_HEADERS, allow_redirects=True, timeout=15)
    login_response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

    # Check if login was successful by looking for a redirect or content on a presumed dashboard page
    # A successful login typically redirects to the dashboard or a similar management page.
    # The prompt implies 'Login Fix V2.2 logic' for HTML response.
    # We'll check if the dashboard URL is in the history or if the response URL matches.
    if EG4_DASHBOARD_URL not in login_response.url and "登录" in login_response.text: # "登录" means login in Chinese, might indicate login failure
        print("Login failed: Initial login POST did not redirect to dashboard or content suggests failure.")
        print(f"Response URL: {login_response.url}")
        print(f"Response Status: {login_response.status_code}")
        print(f"Response Body (first 500 chars):\n{login_response.text[:500]}")
        exit(1)
    
    print(f"Successfully logged in to EG4 portal. Current URL: {login_response.url}")

except requests.exceptions.RequestException as e:
    print(f"Error during EG4 login: {e}")
    exit(1)

# --- 3. DATA SCRAPING (Version 2.4 - HTML Screen Scraper) ---
print("Fetching dashboard page for data scraping...")
try:
    dashboard_response = session.get(EG4_DASHBOARD_URL, timeout=15)
    dashboard_response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
    dashboard_html = dashboard_response.text
    print(f"Successfully fetched dashboard page. Current URL: {dashboard_response.url}")

    # Regex patterns (flexible with whitespace and non-digit characters between label and value)
    # Using \D* to match any non-digit character zero or more times
    # Using [\d.]+ to match numbers that might have a decimal point
    # Using \s* to match any whitespace character zero or more times
    soc_regex = r"SOC\D*?(\d+)\s*%"
    pv_regex = r"SolarPower\D*?([\d.]+)\s*W"
    load_regex = r"Load\D*?([\d.]+)\s*W"
    charge_power_regex = r"ChargePower\D*?([\d.]+)\s*W"
    discharge_power_regex = r"DischargePower\D*?([\d.]+)\s*W"

    scraped_data = {}

    # Extract SOC
    match = re.search(soc_regex, dashboard_html)
    if match:
        scraped_data['battery_soc'] = int(float(match.group(1))) # Convert to float first to handle potential decimals, then int
        print(f"Scraped SOC: {scraped_data['battery_soc']}%")
    else:
        scraped_data['battery_soc'] = None
        print("Warning: SOC not found.")

    # Extract SolarPower (PV)
    match = re.search(pv_regex, dashboard_html)
    if match:
        scraped_data['pv_power'] = int(float(match.group(1)))
        print(f"Scraped SolarPower (PV): {scraped_data['pv_power']}W")
    else:
        scraped_data['pv_power'] = None
        print("Warning: SolarPower (PV) not found.")

    # Extract Load
    match = re.search(load_regex, dashboard_html)
    if match:
        scraped_data['load_power'] = int(float(match.group(1)))
        print(f"Scraped Load: {scraped_data['load_power']}W")
    else:
        scraped_data['load_power'] = None
        print("Warning: Load not found.")

    # Extract ChargePower
    charge_power = 0
    match = re.search(charge_power_regex, dashboard_html)
    if match:
        charge_power = float(match.group(1))
        print(f"Scraped ChargePower: {charge_power}W")
    else:
        print("Warning: ChargePower not found, assuming 0W.")

    # Extract DischargePower
    discharge_power = 0
    match = re.search(discharge_power_regex, dashboard_html)
    if match:
        discharge_power = float(match.group(1))
        print(f"Scraped DischargePower: {discharge_power}W")
    else:
        print("Warning: DischargePower not found, assuming 0W.")

    # Calculate Net Battery Power (for internal logging/understanding, not pushed to Sensecraft directly)
    net_battery_power = charge_power - discharge_power
    print(f"Calculated Net Battery Power: {net_battery_power}W (Charge - Discharge)")

    # Debugging: if any critical data is missing, print HTML snippet
    if scraped_data['battery_soc'] is None or scraped_data['pv_power'] is None or scraped_data['load_power'] is None:
        print("\n--- WARNING: Missing critical data. Printing first 500 characters of HTML for debugging ---")
        print(dashboard_html[:1000]) # Print a bit more than 500 for better context
        print("--------------------------------------------------------------------------------------------------\n")

except requests.exceptions.RequestException as e:
    print(f"Error fetching EG4 dashboard or during data scraping: {e}")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred during data scraping: {e}")
    print("\n--- Printing first 500 characters of HTML for debugging ---")
    print(dashboard_html[:1000])
    print("--------------------------------------------------------------------------------------------------\n")
    exit(1)


# --- 4. Format and PUSH to Sensecraft API ---
SENSECRAFT_ENDPOINT = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"
SENSECRAFT_HEADERS = {
    'api-key': SENSECRAFT_KEY,
    'Content-Type': 'application/json'
}

# Use EG4_STATION_ID from env, fallback to example if not set
device_id_to_use = int(EG4_STATION_ID) if EG4_STATION_ID else 20221942
if not EG4_STATION_ID:
    print(f"Warning: EG4_STATION_ID not set. Using default device_id: {device_id_to_use}")

# Filter out None values and ensure required fields are present and of correct type
# Sensecraft expects integers, so we cast float to int if needed.
push_data_payload = {
    "device_id": device_id_to_use,
    "data": {}
}

if scraped_data['pv_power'] is not None:
    push_data_payload["data"]["pv_power"] = int(scraped_data['pv_power'])
else:
    print("Warning: 'pv_power' is missing or could not be parsed. Not sending this field to Sensecraft.")

if scraped_data['battery_soc'] is not None:
    push_data_payload["data"]["battery_soc"] = int(scraped_data['battery_soc'])
else:
    print("Warning: 'battery_soc' is missing or could not be parsed. Not sending this field to Sensecraft.")

if scraped_data['load_power'] is not None:
    push_data_payload["data"]["load_power"] = int(scraped_data['load_power'])
else:
    print("Warning: 'load_power' is missing or could not be parsed. Not sending this field to Sensecraft.")

if not push_data_payload["data"]:
    print("Error: No valid data to push to Sensecraft API. Exiting.")
    exit(1)

print("\nPushing data to Sensecraft API...")
print(f"Payload: {json.dumps(push_data_payload, indent=2)}")

try:
    sensecraft_response = requests.post(SENSECRAFT_ENDPOINT, headers=SENSECRAFT_HEADERS, json=push_data_payload, timeout=15)
    sensecraft_response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

    print("Successfully pushed data to Sensecraft API.")
    print(f"Sensecraft Response Status: {sensecraft_response.status_code}")
    print(f"Sensecraft Response Body: {sensecraft_response.text}")

except requests.exceptions.RequestException as e:
    print(f"Error pushing data to Sensecraft API: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Sensecraft Response Status: {e.response.status_code}")
        print(f"Sensecraft Response Body: {e.response.text}")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred during Sensecraft API push: {e}")
    exit(1)

print("\nScript execution completed successfully.")
