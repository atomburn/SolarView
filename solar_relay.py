import requests
import os
import sys
import json
import re
from datetime import datetime, timezone

# --- Script Version ---
print("Script Version: 4.4 (Station-Specific API Calls)")

# --- 0. Configuration ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_BASE_URL = "https://monitor.eg4electronics.com/WManage"

EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID')

if not EG4_USER or not EG4_PASS:
    print("ERROR: Missing EG4_USER or EG4_PASS")
    sys.exit(1)

print(f"Station ID: {EG4_STATION_ID if EG4_STATION_ID else 'NOT SET'}")

# --- 1. Login ---
print("Logging in to EG4 portal...")
session = requests.Session()

try:
    login_response = session.post(EG4_LOGIN_URL, data={
        'account': EG4_USER,
        'password': EG4_PASS,
        'isRem': 'false',
        'lang': 'en_US'
    }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
    login_response.raise_for_status()
    print("Login successful.")
except Exception as e:
    print(f"Login failed: {e}")
    sys.exit(1)

# --- 2. Try Various API Endpoints ---
print("\nTrying various EG4 API endpoints...")

int_solar = 0
int_load = 0
int_soc = 0

# First, get plant list to find station ID if not provided
print("\n--- Getting plant list ---")
plant_list_url = EG4_BASE_URL + "/web/overview/plant/list"
try:
    # Try POST with pagination params (common in EasyGrid/WManage systems)
    resp = session.post(plant_list_url, data={'page': 1, 'rows': 50}, timeout=10)
    print(f"POST {plant_list_url}")
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.text[:500]}")

    if resp.status_code == 200:
        data = resp.json()
        if 'rows' in data and data['rows']:
            plant = data['rows'][0]
            print(f"\n  Plant info: {json.dumps(plant, indent=2)[:800]}")

            # Extract station ID from plant data
            found_station_id = plant.get('stationId') or plant.get('id') or plant.get('plantId')
            if found_station_id:
                print(f"\n  Found Station ID: {found_station_id}")
                if not EG4_STATION_ID:
                    EG4_STATION_ID = str(found_station_id)

            # Try to extract power values from plant overview
            int_solar = int(float(plant.get('solarPower', plant.get('pac', 0)) or 0))
            int_load = int(float(plant.get('load', plant.get('loadPower', 0)) or 0))
            int_soc = int(float(plant.get('soc', plant.get('batterySoc', 0)) or 0))

            if int_solar > 0 or int_soc > 0:
                print(f"  *** FOUND DATA in plant list: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")

except Exception as e:
    print(f"  Error: {e}")

# If we have a station ID, try station-specific endpoints
if EG4_STATION_ID and (int_solar == 0 and int_soc == 0):
    print(f"\n--- Trying station-specific endpoints for ID: {EG4_STATION_ID} ---")

    station_endpoints = [
        (f"/web/overview/energy/day?id={EG4_STATION_ID}", "GET"),
        (f"/web/overview/device/list?id={EG4_STATION_ID}", "GET"),
        (f"/web/monitor/inverter/list", "POST", {'stationId': EG4_STATION_ID, 'page': 1, 'rows': 50}),
        (f"/web/overview/plant/energy/day?stationId={EG4_STATION_ID}", "GET"),
        (f"/api/station/detail?id={EG4_STATION_ID}", "GET"),
        (f"/web/overview/battery/list?stationId={EG4_STATION_ID}", "GET"),
    ]

    for endpoint_info in station_endpoints:
        if len(endpoint_info) == 2:
            endpoint, method = endpoint_info
            post_data = None
        else:
            endpoint, method, post_data = endpoint_info

        url = EG4_BASE_URL + endpoint
        print(f"\n{method} {url}")

        try:
            if method == "POST":
                resp = session.post(url, data=post_data, timeout=10)
            else:
                resp = session.get(url, timeout=10)

            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                content = resp.text[:800]
                print(f"  Response: {content}")

                try:
                    data = resp.json()

                    # Check for 'rows' array (inverter/device list)
                    if isinstance(data, dict) and 'rows' in data and data['rows']:
                        row = data['rows'][0]
                        print(f"  First row keys: {list(row.keys())}")

                        # Common field names for power values
                        solar = row.get('solarPower') or row.get('pac') or row.get('pvPower') or row.get('ppv') or 0
                        load = row.get('load') or row.get('loadPower') or row.get('pload') or 0
                        soc = row.get('soc') or row.get('batterySoc') or row.get('capacity') or 0

                        int_solar = int(float(solar))
                        int_load = int(float(load))
                        int_soc = int(float(soc))

                        if int_solar > 0 or int_soc > 0:
                            print(f"  *** FOUND DATA: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")
                            break

                    # Check for direct 'data' object
                    elif isinstance(data, dict) and 'data' in data:
                        subdata = data['data']
                        print(f"  Data keys: {list(subdata.keys()) if isinstance(subdata, dict) else 'array'}")

                        if isinstance(subdata, dict):
                            solar = subdata.get('solarPower') or subdata.get('pac') or 0
                            load = subdata.get('load') or subdata.get('loadPower') or 0
                            soc = subdata.get('soc') or subdata.get('batterySoc') or 0

                            int_solar = int(float(solar))
                            int_load = int(float(load))
                            int_soc = int(float(soc))

                            if int_solar > 0 or int_soc > 0:
                                print(f"  *** FOUND DATA: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")
                                break

                except json.JSONDecodeError:
                    print("  Not JSON")

        except Exception as e:
            print(f"  Error: {e}")

# --- 3. If still no data, search the overview page for embedded JSON/AJAX URLs ---
if int_solar == 0 and int_soc == 0:
    print("\n\n--- Fetching overview page to find embedded data ---")

    overview_response = session.get(EG4_BASE_URL + "/web/overview/global", timeout=15)
    page_text = overview_response.text

    # Look for datagrid/AJAX URLs in JavaScript
    url_pattern = r"url\s*:\s*['\"]([^'\"]+)['\"]"
    matches = re.findall(url_pattern, page_text)

    print(f"Found {len(matches)} potential URLs in page:")
    for url in matches[:15]:
        print(f"  - {url}")

    # Also look for embedded JSON data
    json_pattern = r'"solarPower"\s*:\s*(\d+)'
    solar_matches = re.findall(json_pattern, page_text)
    if solar_matches:
        print(f"\nFound solarPower values in page: {solar_matches}")
        int_solar = int(solar_matches[0])

    soc_pattern = r'"soc"\s*:\s*(\d+)'
    soc_matches = re.findall(soc_pattern, page_text)
    if soc_matches:
        print(f"Found soc values in page: {soc_matches}")
        int_soc = int(soc_matches[0])

print(f"\n\n{'='*50}")
print(f"Final Extracted: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")
print(f"{'='*50}")

# --- 4. Write data.json ---
data = {
    "battery_soc": int_soc,
    "pv_power": int_solar,
    "load_power": int_load,
    "last_updated": datetime.now(timezone.utc).isoformat()
}

with open('data.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nWrote data.json: {json.dumps(data)}")
print("Done!")
