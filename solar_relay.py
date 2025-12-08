import requests
import os
from bs4 import BeautifulSoup
import sys
import json
from datetime import datetime, timezone

# --- Script Version ---
print("Script Version: 4.0 (JSON File Output for SenseCraft Pull)")

# --- 0. Configuration and Environment Variables ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_OVERVIEW_URL = "https://monitor.eg4electronics.com/WManage/web/overview/global"

# Get credentials from environment variables
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID')

# Check for required environment variables
missing_vars = []
if not EG4_USER:
    missing_vars.append('EG4_USER')
if not EG4_PASS:
    missing_vars.append('EG4_PASS')

if missing_vars:
    print(f"ERROR: Missing environment variables: {', '.join(missing_vars)}")
    print("Please set them before running the script.")
    sys.exit(1)

# --- 1. Login to EG4 Electronics Monitoring Portal ---
print("Attempting to log in to EG4 portal...")
session = requests.Session()
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
    login_response = session.post(EG4_LOGIN_URL, data=login_data, headers=login_headers, timeout=10)
    login_response.raise_for_status()

    if "login" in login_response.url and "login" in login_response.text.lower():
        print("ERROR: EG4 Login failed. Check username and password.")
        sys.exit(1)

    print("Successfully logged in to EG4 portal.")

except requests.exceptions.RequestException as e:
    print(f"ERROR: EG4 Login request failed: {e}")
    sys.exit(1)

# --- 2. DATA ACQUISITION (Table Scraping) ---
print("\nAcquiring data from EG4 overview page...")
int_solar = 0
int_load = 0
int_soc = 0

try:
    overview_response = session.get(EG4_OVERVIEW_URL, timeout=15)
    overview_response.raise_for_status()
    soup = BeautifulSoup(overview_response.text, 'html.parser')

    table = soup.find('table', class_='table')
    if not table:
        table = soup.find('table', id='gridTable')
    if not table:
        table = soup.find('table')

    if not table:
        print("WARNING: Could not find any data table on the EG4 overview page. Defaulting to 0 values.")
    else:
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]

        target_row = None

        if EG4_STATION_ID:
            print(f"Looking for device_id: {EG4_STATION_ID}")
            for row in rows:
                cols = row.find_all('td')
                if cols and len(cols) > 0 and cols[0].text.strip() == EG4_STATION_ID:
                    target_row = row
                    break
            if not target_row:
                print(f"WARNING: Device ID '{EG4_STATION_ID}' not found in the table.")

        if not target_row:
            print("Searching for the first 'Normal' or 'Offline' device status.")
            for row in rows:
                cols = row.find_all('td')
                row_text_content = ' '.join(td.text.strip() for td in cols)
                if "Normal" in row_text_content or "Offline" in row_text_content:
                    target_row = row
                    if cols and len(cols) > 0:
                        detected_device_id = cols[0].text.strip()
                        print(f"Detected and using device: {detected_device_id} (Status: {'Normal' if 'Normal' in row_text_content else 'Offline'})")
                    break

        if target_row:
            cols = target_row.find_all('td')
            if len(cols) > 6:
                try:
                    solar_power_str = cols[2].text.strip().replace(' W', '')
                    int_solar = int(float(solar_power_str))
                except (ValueError, IndexError):
                    print(f"WARNING: Could not parse SolarPower. Defaulting to 0.")
                    int_solar = 0

                try:
                    load_str = cols[5].text.strip().replace(' W', '')
                    int_load = int(float(load_str))
                except (ValueError, IndexError):
                    print(f"WARNING: Could not parse Load. Defaulting to 0.")
                    int_load = 0

                try:
                    soc_str = cols[6].text.strip().replace(' %', '')
                    int_soc = int(float(soc_str))
                except (ValueError, IndexError):
                    print(f"WARNING: Could not parse SOC. Defaulting to 0.")
                    int_soc = 0
            else:
                print(f"WARNING: Not enough columns. Defaulting to 0 values.")
        else:
            print("WARNING: No target device row found. Defaulting to 0 values.")

except requests.exceptions.RequestException as e:
    print(f"ERROR: Failed to retrieve EG4 overview page: {e}. Defaulting to 0 values.")
except Exception as e:
    print(f"ERROR: An unexpected error occurred during data scraping: {e}. Defaulting to 0 values.")

print(f"Extracted Data: Solar Power: {int_solar}W, Load: {int_load}W, Battery SOC: {int_soc}%")

# --- 3. WRITE TO data.json ---
print("\nWriting data to data.json...")

data = {
    "battery_soc": int_soc,
    "pv_power": int_solar,
    "load_power": int_load,
    "last_updated": datetime.now(timezone.utc).isoformat()
}

try:
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Successfully wrote data.json:")
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"ERROR: Failed to write data.json: {e}")
    sys.exit(1)

print("\nScript finished successfully!")
print("SenseCraft will pull data from: https://github.com/atomburn/SolarView/raw/main/data.json")
