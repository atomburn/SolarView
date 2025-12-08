import requests
import os
import re
import json
import time

print("Script Version: 2.5 (Strict Scraper + Safe Defaults)")

# --- 1. Load Environment Variables ---
# EG4 Login Credentials
EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')

# EG4 Station ID (Optional for HTML scraping, but required for API fallback)
EG4_STATION_ID = os.environ.get('EG4_STATION_ID')

# Sensecraft API Key and Device ID
SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')
SENSECRAFT_DEVICE_ID = os.environ.get('SENSECRAFT_DEVICE_ID', "20221942") # Default as per example if not set

# --- 2. Configuration & Validation ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_INVERTER_URL = "https://monitor.eg4electronics.com/WManage/web/monitor/inverter"
EG4_POWER_FLOW_API_URL = "https://monitor.eg4electronics.com/WManage/app/monitor/getPowerFlow"
SENSECRAFT_PUSH_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"

# Check for missing required environment variables
missing_env_vars = []
if not EG4_USER:
    missing_env_vars.append("EG4_USER")
if not EG4_PASS:
    missing_env_vars.append("EG4_PASS")
if not SENSECRAFT_KEY:
    missing_env_vars.append("SENSECRAFT_KEY")

if missing_env_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_env_vars)}")
    print("Please set these variables before running the script.")
    exit(1)

if not EG4_STATION_ID:
    print("WARNING: EG4_STATION_ID environment variable is not set. The script will attempt to detect it from the HTML, but this might not always be reliable. If detection fails, the mobile app API fallback might not work.")

# --- 3. EG4 Login ---
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

print(f"Attempting to log in to EG4 portal as {EG4_USER}...")
try:
    response = session.post(EG4_LOGIN_URL, data=login_data, headers=login_headers, timeout=10)
    response.raise_for_status() # Raise an exception for HTTP errors (e.g., 4xx or 5xx)
    
    # Check for successful login. The EG4 portal typically redirects to a dashboard URL.
    # If the current URL still contains "login", it's likely a failure.
    if "login" in response.url.lower():
        print("ERROR: Login failed. Please check your EG4_USER and EG4_PASS environment variables.")
        if "Incorrect account name or password" in response.text:
            print("  Reason: Incorrect account name or password detected in response.")
        exit(1)
    
    print("EG4 login successful.")
except requests.exceptions.RequestException as e:
    print(f"ERROR during EG4 login: {e}")
    exit(1)

# Initialize data points to 0
pv_power = 0
battery_soc = 0
load_power = 0
charge_power = 0
discharge_power = 0
station_id = EG4_STATION_ID # Use the environment variable, or None if not set

# --- 4. Data Acquisition (Version 2.5) ---

html_scraped_successfully = False

# Strategy A: Strict HTML Scraping (Primary)
print("Attempting Strict HTML Scraping (Strategy A)...")
try:
    response = session.get(EG4_INVERTER_URL, headers=login_headers, timeout=10) # Reuse login_headers for User-Agent
    response.raise_for_status()
    html_content = response.text

    # Try to find station_id from HTML if not provided by env var
    if not station_id:
        print("Attempting to detect EG4_STATION_ID from HTML...")
        match_station_id = re.search(r"plantId\s*=\s*'(\d+)'", html_content)
        if match_station_id:
            station_id = match_station_id.group(1)
            print(f"Detected EG4_STATION_ID: {station_id}")
        else:
            print("WARNING: Could not detect EG4_STATION_ID from HTML. Mobile app API fallback might fail without it.")
            
    # Regex patterns: MUST include the colon. Capture numeric values (integers or floats).
    # Using re.IGNORECASE for the label part to be robust, but colon is strict.
    # The first capturing group `()` will contain the value.
    patterns = {
        "SolarPower": r"SolarPower:\s*([\d.]+)",
        "SOC": r"SOC:\s*(\d+)", # SOC is typically an integer percentage
        "Load": r"Load:\s*([\d.]+)",
        "ChargePower": r"ChargePower:\s*([\d.]+)",
        "DischargePower": r"DischargePower:\s*([\d.]+)"
    }

    found_values = {}
    for label, pattern_str in patterns.items():
        match = re.search(pattern_str, html_content, re.IGNORECASE)
        if match:
            value_str = match.group(1)
            # Convert to float first, then int if no decimal, to handle both types
            try:
                numeric_value = float(value_str)
                found_values[label] = int(numeric_value) if numeric_value.is_integer() else numeric_value
            except ValueError:
                found_values[label] = 0 # Default to 0 if conversion fails
            print(f"  HTML Scraped - {label}: {found_values[label]}")
        else:
            found_values[label] = 0 # Default to 0 if not found
            print(f"  HTML Scraped - {label}: Not found, defaulting to 0.")

    # Assign scraped values, ensuring they are not None and default to 0
    pv_power = int(found_values.get("SolarPower", 0))
    battery_soc = int(found_values.get("SOC", 0))
    load_power = int(found_values.get("Load", 0))
    charge_power = int(found_values.get("ChargePower", 0))
    discharge_power = int(found_values.get("DischargePower", 0))

    # Determine if HTML scraping was "successful enough" to skip API fallback
    # Check if at least one critical value (pv, soc, load) is non-zero
    if pv_power > 0 or battery_soc > 0 or load_power > 0:
        html_scraped_successfully = True
        print("Strategy A (HTML Scraping) successful for critical values.")
    else:
        print("Strategy A (HTML Scraping) did not find sufficient critical data. Attempting fallback.")

except requests.exceptions.RequestException as e:
    print(f"ERROR during HTML page retrieval (Strategy A): {e}")
    print("Falling back to Mobile App API (Strategy B).")
except Exception as e:
    print(f"ERROR during HTML parsing (Strategy A): {e}")
    print("Falling back to Mobile App API (Strategy B).")

# Strategy B: Mobile App API (Fallback)
if not html_scraped_successfully:
    print("Attempting Mobile App API (Strategy B) as fallback...")
    if not station_id:
        print("ERROR: Cannot use Mobile App API fallback. EG4_STATION_ID is missing and could not be detected.")
    else:
        try:
            api_data = {'plantId': station_id}
            # The app API often expects JSON content type
            api_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36'
            }
            response = session.post(EG4_POWER_FLOW_API_URL, json=api_data, headers=api_headers, timeout=10)
            response.raise_for_status()
            api_response_json = response.json()

            if api_response_json.get('result') == 1 and api_response_json.get('data'):
                data = api_response_json['data']
                pv_power = int(data.get('pvPower', 0))
                battery_soc = int(data.get('soc', 0))
                load_power = int(data.get('loadPower', 0))
                charge_power = int(data.get('chargePower', 0))
                discharge_power = int(data.get('dischargePower', 0))
                print("Strategy B (Mobile App API) successful.")
            else:
                print(f"ERROR: Mobile App API returned an error or no data: {api_response_json.get('msg', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            print(f"ERROR during Mobile App API call (Strategy B): {e}")
        except json.JSONDecodeError as e:
            print(f"ERROR decoding JSON from Mobile App API (Strategy B): {e}")
        except Exception as e:
            print(f"An unexpected error occurred during Mobile App API call (Strategy B): {e}")

# --- 5. Data Cleanup & Push ---

# Ensure all values are non-negative integers
pv_power = int(max(0, pv_power))
load_power = int(max(0, load_power))

# Battery SOC must be between 0-100
battery_soc = int(max(0, min(100, battery_soc)))

print("\n--- Final Data Collected ---")
print(f"PV Power: {pv_power}W")
print(f"Load Power: {load_power}W")
print(f"Battery SOC: {battery_soc}%")
print(f"Charge Power: {charge_power}W")
print(f"Discharge Power: {discharge_power}W")
print(f"Net Battery Watts: {charge_power - discharge_power}W (Charge - Discharge)") # For debug/info

# Construct Sensecraft payload
sensecraft_payload = {
    "device_id": str(SENSECRAFT_DEVICE_ID), # Ensure device_id is a string
    "data": {
        "pv_power": pv_power,
        "battery_soc": battery_soc,
        "load_power": load_power
    }
}

sensecraft_headers = {
    'api-key': SENSECRAFT_KEY,
    'Content-Type': 'application/json'
}

print(f"\nPushing data to Sensecraft for device_id: {SENSECRAFT_DEVICE_ID}...")
try:
    response = requests.post(SENSECRAFT_PUSH_URL, json=sensecraft_payload, headers=sensecraft_headers, timeout=10)
    response.raise_for_status() # Raise an exception for HTTP errors (e.g., 4xx or 5xx)
    print("Data successfully pushed to Sensecraft.")
    print("Sensecraft Response:", response.json())
except requests.exceptions.RequestException as e:
    print(f"ERROR pushing data to Sensecraft: {e}")
    if e.response:
        print("Sensecraft Error Response:", e.response.text)
except Exception as e:
    print(f"An unexpected error occurred during Sensecraft push: {e}")

print("\nScript finished.")
