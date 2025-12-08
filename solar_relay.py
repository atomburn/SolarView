import os
import requests
from bs4 import BeautifulSoup
import sys
import json

# --- Configuration and Environment Variables ---
SCRIPT_VERSION = "2.9 (Single Variable Sanity Check)"

EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_OVERVIEW_URL = "https://monitor.eg4electronics.com/WManage/web/overview/global"
SENSECRAFT_API_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"

print(f"Script Version: {SCRIPT_VERSION}")

# Load sensitive data from environment variables
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID')
SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')

# Check for required environment variables
missing_critical_vars = []
if not EG4_USER:
    missing_critical_vars.append('EG4_USER')
if not EG4_PASS:
    missing_critical_vars.append('EG4_PASS')
if not SENSECRAFT_KEY:
    missing_critical_vars.append('SENSECRAFT_KEY')

if missing_critical_vars:
    print(f"ERROR: Missing critical environment variables: {', '.join(missing_critical_vars)}")
    print("Please set EG4_USER, EG4_PASS, and SENSECRAFT_KEY before running the script.")
    sys.exit(1)

# EG4_STATION_ID is used for data push to Sensecraft.
# If it's not set, we'll use the default ID provided in the prompt's example for Sensecraft.
if not EG4_STATION_ID:
    print("WARNING: EG4_STATION_ID environment variable is not set. Data push to Sensecraft will use the default device_id '20221942' from the prompt's example.")
    EG4_STATION_ID = "20221942" # Default value as per prompt's example for Sensecraft device_id

# --- Step 1: Login to EG4 Monitoring Portal ---
session = requests.Session()
login_data = {
    'account': EG4_USER,
    'password': EG4_PASS,
    'isRem': 'false',
    'lang': 'en_US'
}
login_headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print("Attempting to log in to EG4 portal...")
try:
    response = session.post(EG4_LOGIN_URL, data=login_data, headers=login_headers, timeout=10)
    response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

    # Check for successful login. The EG4 portal usually redirects to /WManage/web/overview/global on success.
    # We can check the final URL after redirects or for a 200 OK.
    if "overview/global" in response.url or response.status_code == 200:
        print("Successfully logged in to EG4 portal.")
    else:
        print(f"Login failed. Status code: {response.status_code}. Response: {response.text[:200]}...")
        sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR during EG4 login: {e}")
    sys.exit(1)

# --- Step 2: Sanity Check (Version 2.9 - Single Variable Test) ---
print("Sending Sanity Check (battery_soc only)...")
sensecraft_headers = {
    'api-key': SENSECRAFT_KEY,
    'Content-Type': 'application/json'
}
sanity_payload = {
    "device_id": EG4_STATION_ID,
    "data": {
        "battery_soc": 50
    }
}

try:
    sanity_response = requests.post(
        SENSECRAFT_API_URL,
        headers=sensecraft_headers,
        json=sanity_payload,
        timeout=10
    )
    if sanity_response.status_code == 200:
        print("Sanity Check Passed.")
    else:
        print(f"Sanity Check Failed. Error {sanity_response.status_code}. Response: {sanity_response.text}")
        sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR during Sanity Check request: {e}")
    sys.exit(1)

# --- Step 3: Data Acquisition (Table Scraping) ---
print("Attempting to acquire data from EG4 overview page...")
int_solar = 0
int_load = 0
int_soc = 0

try:
    overview_response = session.get(EG4_OVERVIEW_URL, timeout=10)
    overview_response.raise_for_status()
    soup = BeautifulSoup(overview_response.text, 'html.parser')

    # Find the main table. Adjust selector if necessary (e.g., table with a specific class or ID).
    table = soup.find('table') 

    if not table:
        raise ValueError("Could not find any table on the EG4 overview page.")

    # Find all table rows. Skip header rows if present.
    rows = table.find_all('tr')

    found_data_row = False
    for row in rows:
        cells = row.find_all('td')
        # A data row is expected to have multiple columns and a status like "Normal" or "Offline"
        if len(cells) > 6 and (
            "Normal" in cells[1].get_text(strip=True) or
            "Offline" in cells[1].get_text(strip=True)
        ):
            # This is likely a data row containing the inverter's status
            try:
                # SolarPower (Column Index 2)
                solar_text = cells[2].get_text(strip=True).replace(' W', '')
                int_solar = int(float(solar_text)) # Convert to float first to handle potential decimals

                # Load (Column Index 5)
                load_text = cells[5].get_text(strip=True).replace(' W', '')
                int_load = int(float(load_text))

                # SOC (Column Index 6)
                soc_text = cells[6].get_text(strip=True).replace(' %', '')
                int_soc = int(float(soc_text))

                found_data_row = True
                break # Found and parsed the first relevant data row, exit loop

            except (IndexError, ValueError) as e:
                print(f"WARNING: Error parsing data from a potential data row ({row.get_text(strip=True)[:100]}...): {e}. Defaulting values to 0 for this row.")
                # If parsing fails for a specific row, continue to the next one, or use defaults.
                # For this script, we'll break and use the defaults if parsing *our chosen* row fails.
                int_solar = 0
                int_load = 0
                int_soc = 0
                break # Stop after first identified data row, even if parsing failed partially

    if found_data_row:
        print(f"Data acquired: SolarPower={int_solar}W, Load={int_load}W, SOC={int_soc}%")
    else:
        print("WARNING: No data row with 'Normal' or 'Offline' status found on the EG4 overview page. Defaulting all values to 0.")

except requests.exceptions.RequestException as e:
    print(f"ERROR during EG4 data acquisition request: {e}. Defaulting all values to 0.")
except ValueError as e:
    print(f"ERROR during data acquisition (HTML parsing): {e}. Defaulting all values to 0.")
except Exception as e:
    print(f"An unexpected error occurred during data acquisition: {e}. Defaulting all values to 0.")

# --- Step 4: Real Data Push ---
print("Attempting to push real data to Sensecraft HMI API...")

real_data_payload = {
    "device_id": EG4_STATION_ID,
    "data": {
        "battery_soc": int_soc,
        "pv_power": int_solar,
        "load_power": int_load
    }
}

try:
    push_response = requests.post(
        SENSECRAFT_API_URL,
        headers=sensecraft_headers,
        json=real_data_payload,
        timeout=10
    )
    push_response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

    print("Real Data Push successful.")
    # print(f"Sensecraft response: {push_response.text}") # Uncomment for debugging

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 500:
        print(f"Real Data Push failed with 500 error. Ensure 'pv_power' and 'load_power' are also defined as Data Keys in your Sensecraft Dashboard. Details: {e.response.text}")
    else:
        print(f"Real Data Push failed with HTTP Error {e.response.status_code}: {e.response.text}")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR during Real Data Push request: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during Real Data Push: {e}")
    sys.exit(1)

print("Script finished successfully.")
