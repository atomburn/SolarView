import requests
import os
import sys
import json
import re
from datetime import datetime, timezone

# --- Script Version ---
print("Script Version: 4.5 (Auto-discover Station ID)")

# --- 0. Configuration ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_BASE_URL = "https://monitor.eg4electronics.com/WManage"

EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')
EG4_STATION_ID = os.environ.get('EG4_STATION_ID')  # Can be numeric ID or serial number

if not EG4_USER or not EG4_PASS:
    print("ERROR: Missing EG4_USER or EG4_PASS")
    sys.exit(1)

print(f"Configured Station ID/Serial: {EG4_STATION_ID if EG4_STATION_ID else 'NOT SET (will auto-discover)'}")

# --- 1. Login ---
print("\nLogging in to EG4 portal...")
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

# --- 2. Get Plant List (to find station ID and data) ---
print("\n" + "="*50)
print("STEP 1: Getting plant list...")
print("="*50)

int_solar = 0
int_load = 0
int_soc = 0
numeric_station_id = None

plant_list_url = EG4_BASE_URL + "/web/overview/plant/list"

# Try POST first (common in WManage), then GET
for method in ["POST", "GET"]:
    try:
        print(f"\n{method} {plant_list_url}")
        if method == "POST":
            resp = session.post(plant_list_url, data={'page': 1, 'rows': 50}, timeout=10)
        else:
            resp = session.get(plant_list_url, timeout=10)

        print(f"  Status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")

                if isinstance(data, dict) and 'rows' in data and data['rows']:
                    print(f"  Found {len(data['rows'])} plant(s)")

                    # Print ALL plant info for debugging
                    for i, plant in enumerate(data['rows']):
                        print(f"\n  --- Plant {i+1} ---")
                        print(f"  Full data: {json.dumps(plant, indent=4)}")

                        # Extract the numeric station ID
                        plant_id = plant.get('id') or plant.get('stationId') or plant.get('plantId')
                        plant_sn = plant.get('sn') or plant.get('serialNumber') or plant.get('inverterSn')
                        plant_name = plant.get('name') or plant.get('stationName') or plant.get('plantName')

                        print(f"\n  Extracted: ID={plant_id}, SN={plant_sn}, Name={plant_name}")

                        # Use first plant's ID if we don't have one
                        if plant_id and not numeric_station_id:
                            numeric_station_id = str(plant_id)
                            print(f"  >>> Using Station ID: {numeric_station_id}")

                        # Try to get power values directly from plant list
                        solar = plant.get('solarPower') or plant.get('pac') or plant.get('pvPower') or plant.get('power') or 0
                        load = plant.get('load') or plant.get('loadPower') or plant.get('pload') or 0
                        soc = plant.get('soc') or plant.get('batterySoc') or plant.get('capacity') or 0

                        # Handle string values
                        try:
                            int_solar = int(float(solar)) if solar else 0
                            int_load = int(float(load)) if load else 0
                            int_soc = int(float(soc)) if soc else 0
                        except (ValueError, TypeError):
                            pass

                        if int_solar > 0 or int_soc > 0:
                            print(f"  >>> FOUND DATA: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")

                    if int_solar > 0 or int_soc > 0:
                        break  # Got data, stop trying methods

            except json.JSONDecodeError:
                print(f"  Response (not JSON): {resp.text[:300]}")

    except Exception as e:
        print(f"  Error: {e}")

# --- 3. Try inverter list endpoint (often has real-time data) ---
if int_solar == 0 and int_soc == 0:
    print("\n" + "="*50)
    print("STEP 2: Getting inverter list...")
    print("="*50)

    station_id_to_use = numeric_station_id or EG4_STATION_ID

    inverter_endpoints = [
        ("/web/monitor/inverter/list", "POST", {'page': 1, 'rows': 50}),
        ("/web/overview/inverter/list", "POST", {'page': 1, 'rows': 50}),
        (f"/web/overview/device/list?stationId={station_id_to_use}", "GET", None) if station_id_to_use else None,
        (f"/web/monitor/inverter/list?stationId={station_id_to_use}", "GET", None) if station_id_to_use else None,
    ]

    for endpoint_info in inverter_endpoints:
        if not endpoint_info:
            continue

        endpoint, method, post_data = endpoint_info
        url = EG4_BASE_URL + endpoint

        try:
            print(f"\n{method} {url}")
            if method == "POST" and post_data:
                # Add station ID to POST data if we have it
                if station_id_to_use:
                    post_data['stationId'] = station_id_to_use
                resp = session.post(url, data=post_data, timeout=10)
            else:
                resp = session.get(url, timeout=10)

            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"  Response: {json.dumps(data, indent=2)[:1000]}")

                    # Check for rows array
                    rows = data.get('rows', []) if isinstance(data, dict) else []
                    if rows:
                        inverter = rows[0]
                        print(f"\n  Inverter keys: {list(inverter.keys())}")

                        solar = inverter.get('solarPower') or inverter.get('pac') or inverter.get('ppv') or inverter.get('pvPower') or 0
                        load = inverter.get('load') or inverter.get('loadPower') or inverter.get('pload') or 0
                        soc = inverter.get('soc') or inverter.get('batterySoc') or inverter.get('capacity') or 0

                        try:
                            int_solar = int(float(solar)) if solar else 0
                            int_load = int(float(load)) if load else 0
                            int_soc = int(float(soc)) if soc else 0
                        except (ValueError, TypeError):
                            pass

                        if int_solar > 0 or int_soc > 0:
                            print(f"  >>> FOUND DATA: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")
                            break

                except json.JSONDecodeError:
                    print(f"  Not JSON: {resp.text[:200]}")

        except Exception as e:
            print(f"  Error: {e}")

# --- 4. Try real-time data endpoint ---
if int_solar == 0 and int_soc == 0:
    print("\n" + "="*50)
    print("STEP 3: Trying real-time data endpoints...")
    print("="*50)

    station_id_to_use = numeric_station_id or EG4_STATION_ID

    if station_id_to_use:
        realtime_endpoints = [
            f"/web/overview/energy/day?id={station_id_to_use}",
            f"/web/overview/plant/detail?id={station_id_to_use}",
            f"/api/station/overview?id={station_id_to_use}",
            f"/web/overview/battery/list?stationId={station_id_to_use}",
        ]

        for endpoint in realtime_endpoints:
            url = EG4_BASE_URL + endpoint
            try:
                print(f"\nGET {url}")
                resp = session.get(url, timeout=10)
                print(f"  Status: {resp.status_code}")

                if resp.status_code == 200:
                    print(f"  Response: {resp.text[:800]}")

                    try:
                        data = resp.json()

                        # Look for power data in various structures
                        if isinstance(data, dict):
                            # Direct fields
                            solar = data.get('solarPower') or data.get('pac') or 0
                            load = data.get('load') or data.get('loadPower') or 0
                            soc = data.get('soc') or data.get('batterySoc') or 0

                            # Nested in 'data' key
                            if 'data' in data and isinstance(data['data'], dict):
                                subdata = data['data']
                                solar = solar or subdata.get('solarPower') or subdata.get('pac') or 0
                                load = load or subdata.get('load') or subdata.get('loadPower') or 0
                                soc = soc or subdata.get('soc') or subdata.get('batterySoc') or 0

                            try:
                                int_solar = int(float(solar)) if solar else 0
                                int_load = int(float(load)) if load else 0
                                int_soc = int(float(soc)) if soc else 0
                            except (ValueError, TypeError):
                                pass

                            if int_solar > 0 or int_soc > 0:
                                print(f"  >>> FOUND DATA: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")
                                break

                    except json.JSONDecodeError:
                        pass

            except Exception as e:
                print(f"  Error: {e}")

# --- 5. Final Summary ---
print("\n" + "="*50)
print("FINAL RESULTS")
print("="*50)
print(f"Station ID used: {numeric_station_id or EG4_STATION_ID or 'None found'}")
print(f"Solar Power: {int_solar}W")
print(f"Load Power: {int_load}W")
print(f"Battery SOC: {int_soc}%")

# --- 6. Write data.json ---
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
