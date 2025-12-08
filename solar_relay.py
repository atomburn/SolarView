import requests
import os
from bs4 import BeautifulSoup
import sys

# --- Script Version ---
print("Script Version: 3.0 (BS4 Dependency Fix)")

# --- 0. Configuration and Environment Variables ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_OVERVIEW_URL = "https://monitor.eg4electronics.com/WManage/web/overview/global"

# SenseCraft API configuration
SENSECRAFT_DEVICE_ID = 20222838  # Integer format (Authorization: Bearer worked with this)
SENSECRAFT_API_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"

# Get credentials from environment variables
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
# EG4_STATION_ID is used to find the specific device row on the EG4 portal.
# If not provided, the script will attempt to find the first "Normal" or "Offline" device.
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
    login_response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

    # A successful login usually redirects or returns a specific page.
    # Check if we were redirected to the overview page or similar success indicator.
    # If the login fails, it often returns the login page itself with a 200 status.
    if "login" in login_response.url and "login" in login_response.text.lower():
        print("ERROR: EG4 Login failed. Check username and password.")
        sys.exit(1)
    
    print("Successfully logged in to EG4 portal.")

except requests.exceptions.RequestException as e:
    print(f"ERROR: EG4 Login request failed: {e}")
    sys.exit(1)

# --- 2. COMPREHENSIVE API TEST ---
print("\n" + "="*60)
print("COMPREHENSIVE SENSECRAFT API TEST")
print("="*60)
print(f"API URL: {SENSECRAFT_API_URL}")
print(f"Device ID: {SENSECRAFT_DEVICE_ID}")
print(f"API Key: {SENSECRAFT_KEY[:8]}...{SENSECRAFT_KEY[-4:]}")

# All header variations to try
header_options = [
    ("api-key", {"api-key": SENSECRAFT_KEY, "Content-Type": "application/json"}),
    ("X-API-KEY", {"X-API-KEY": SENSECRAFT_KEY, "Content-Type": "application/json"}),
    ("Authorization (plain)", {"Authorization": SENSECRAFT_KEY, "Content-Type": "application/json"}),
    ("Authorization Bearer", {"Authorization": f"Bearer {SENSECRAFT_KEY}", "Content-Type": "application/json"}),
]

# Payload
test_payload = {"device_id": SENSECRAFT_DEVICE_ID, "data": {"battery_soc": 50}}
print(f"Payload: {test_payload}")
print()

best_result = None
sensecraft_headers = None

for header_name, headers in header_options:
    print(f"[{header_name}]")
    try:
        resp = requests.post(SENSECRAFT_API_URL, json=test_payload, headers=headers, timeout=10)
        print(f"  HTTP: {resp.status_code} | Body: {resp.text[:100] if resp.text else '(empty)'}")

        # Track best result (200 is better than 500)
        if resp.status_code == 200:
            try:
                rj = resp.json()
                code = rj.get('code', 0)
                msg = rj.get('message', '')
                print(f"  JSON code: {code}, message: {msg}")
                if code == 0:
                    print(f"  *** SUCCESS! ***")
                    best_result = header_name
                    sensecraft_headers = headers
            except:
                print(f"  *** SUCCESS (no error code)! ***")
                best_result = header_name
                sensecraft_headers = headers
    except Exception as e:
        print(f"  Error: {e}")
    print()

if not sensecraft_headers:
    print("WARNING: No successful header found. Using api-key as default.")
    sensecraft_headers = {"api-key": SENSECRAFT_KEY, "Content-Type": "application/json"}
else:
    print(f"Best result with: {best_result}")

print("="*60)

# --- 3. DATA ACQUISITION (Table Scraping) ---
print("\nAcquiring data from EG4 overview page...")
int_solar = 0
int_load = 0
int_soc = 0

try:
    overview_response = session.get(EG4_OVERVIEW_URL, timeout=15)
    overview_response.raise_for_status()
    soup = BeautifulSoup(overview_response.text, 'html.parser')

    # Find the table containing the device data. Assume it's the main data table.
    # Common classes/IDs for such tables are 'table', 'gridTable', 'dataTable', etc.
    # We try a few common ones.
    table = soup.find('table', class_='table') 
    if not table:
        table = soup.find('table', id='gridTable')
    if not table: # Fallback to finding any table if specific classes/ids not found
        table = soup.find('table') 

    if not table:
        print("WARNING: Could not find any data table on the EG4 overview page. Defaulting to 0 values.")
    else:
        # Assuming the data rows are within a tbody
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:] # Skip header row if no tbody

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
        
        # If no specific STATION_ID was provided, or if it wasn't found,
        # try to find the first device marked "Normal" or "Offline".
        if not target_row:
            print("Searching for the first 'Normal' or 'Offline' device status.")
            for row in rows:
                cols = row.find_all('td')
                # Check text content of all columns in the row for status indicators
                row_text_content = ' '.join(td.text.strip() for td in cols)
                if "Normal" in row_text_content or "Offline" in row_text_content:
                    target_row = row
                    if cols and len(cols) > 0:
                        detected_device_id = cols[0].text.strip()
                        print(f"Detected and using device: {detected_device_id} (Status: {'Normal' if 'Normal' in row_text_content else 'Offline'})")
                    break
        
        if target_row:
            cols = target_row.find_all('td')
            # Ensure there are enough columns before accessing specific indices
            # Indices: SolarPower (2), Load (5), SOC (6) - this means we need at least 7 columns (0-6)
            if len(cols) > 6: 
                try:
                    # Column Index 2 (SolarPower)
                    solar_power_str = cols[2].text.strip().replace(' W', '')
                    int_solar = int(float(solar_power_str)) # Use float first to handle potential decimals
                except (ValueError, IndexError):
                    print(f"WARNING: Could not parse SolarPower from '{cols[2].text.strip() if len(cols)>2 else 'N/A'}'. Defaulting to 0.")
                    int_solar = 0

                try:
                    # Column Index 5 (Load)
                    load_str = cols[5].text.strip().replace(' W', '')
                    int_load = int(float(load_str))
                except (ValueError, IndexError):
                    print(f"WARNING: Could not parse Load from '{cols[5].text.strip() if len(cols)>5 else 'N/A'}'. Defaulting to 0.")
                    int_load = 0

                try:
                    # Column Index 6 (SOC)
                    soc_str = cols[6].text.strip().replace(' %', '')
                    int_soc = int(float(soc_str))
                except (ValueError, IndexError):
                    print(f"WARNING: Could not parse SOC from '{cols[6].text.strip() if len(cols)>6 else 'N/A'}'. Defaulting to 0.")
                    int_soc = 0
            else:
                print(f"WARNING: Target row found but not enough columns ({len(cols)}) to extract all data. Expected at least 7 for indices 2, 5, 6. Defaulting to 0 values.")
        else:
            print("WARNING: No target device row found based on STATION_ID or 'Normal'/'Offline' status. Defaulting to 0 values.")

except requests.exceptions.RequestException as e:
    print(f"ERROR: Failed to retrieve EG4 overview page: {e}. Defaulting to 0 values.")
except Exception as e:
    print(f"ERROR: An unexpected error occurred during data scraping: {e}. Defaulting to 0 values.")

print(f"Extracted Data: Solar Power: {int_solar}W, Load: {int_load}W, Battery SOC: {int_soc}%")

# --- 4. REAL DATA PUSH ---
print("\nPushing real data to Sensecraft API...")
print(f"URL: {SENSECRAFT_API_URL}")

# Payload with device_id and data
real_data_payload = {
    "device_id": SENSECRAFT_DEVICE_ID,
    "data": {
        "battery_soc": int_soc,
        "pv_power": int_solar,
        "load_power": int_load
    }
}
print(f"Payload: {real_data_payload}")

try:
    real_data_response = requests.post(SENSECRAFT_API_URL, json=real_data_payload, headers=sensecraft_headers, timeout=10)
    print(f"HTTP Status: {real_data_response.status_code}")
    print(f"Response: {real_data_response.text[:500] if real_data_response.text else '(empty)'}")
    real_data_response.raise_for_status()

    print(f"Real Data Push successful! Status Code: {real_data_response.status_code}")
except requests.exceptions.HTTPError as e:
    if e.response is not None and e.response.status_code == 500:
        print("Real Data Push failed. Ensure 'pv_power' and 'load_power' are also defined as Data Keys in your Sensecraft Dashboard.")
        print(f"Full 500 Error Response: {e.response.text}")
    else:
        print(f"ERROR: Real Data Push failed with HTTP error: {e}")
        if e.response is not None:
            print(f"Response: {e.response.status_code} - {e.response.text}")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR: Real Data Push request failed: {e}")
    sys.exit(1)

print("\nScript finished successfully.")
