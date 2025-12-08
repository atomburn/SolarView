import requests
import os
import sys
import json
from datetime import datetime, timezone

# --- Script Version ---
print("Script Version: 5.0 (Using discovered API endpoint)")

# --- 0. Configuration ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_BASE_URL = "https://monitor.eg4electronics.com/WManage"

EG4_USER = os.environ.get('EG4_USER')
EG4_PASS = os.environ.get('EG4_PASS')

if not EG4_USER or not EG4_PASS:
    print("ERROR: Missing EG4_USER or EG4_PASS")
    sys.exit(1)

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

int_solar = 0
int_load = 0
int_soc = 0

# --- 2. Call the discovered API endpoint ---
print("\n" + "="*50)
print("Fetching plant overview data...")
print("="*50)

# The discovered endpoint from the portal JavaScript
api_url = EG4_BASE_URL + "/api/plantOverview/list/viewer"

# Try both POST (with pagination) and GET
for method in ["POST", "GET"]:
    print(f"\n{method} {api_url}")
    try:
        if method == "POST":
            resp = session.post(api_url, data={'page': 1, 'rows': 50}, timeout=10)
        else:
            resp = session.get(api_url, timeout=10)

        print(f"  Status: {resp.status_code}")

        if resp.status_code == 200:
            print(f"  Response: {resp.text[:2000]}")

            try:
                data = resp.json()
                print(f"\n  JSON structure: {list(data.keys()) if isinstance(data, dict) else 'array'}")

                # Check for rows array (common in EasyUI datagrid)
                rows = []
                if isinstance(data, dict):
                    rows = data.get('rows', data.get('data', data.get('list', [])))
                elif isinstance(data, list):
                    rows = data

                if rows:
                    print(f"  Found {len(rows)} plant(s)")

                    # Print full first row for debugging
                    plant = rows[0]
                    print(f"\n  --- Full plant data ---")
                    print(json.dumps(plant, indent=2))
                    print("  --- End plant data ---")

                    # Try to extract values - check all possible field names
                    # Solar/PV power
                    solar = (plant.get('solarPower') or plant.get('pac') or
                            plant.get('pvPower') or plant.get('ppv') or
                            plant.get('power') or plant.get('currentPower') or 0)

                    # Load power
                    load = (plant.get('load') or plant.get('loadPower') or
                           plant.get('pload') or plant.get('consumption') or 0)

                    # Battery SOC
                    soc = (plant.get('soc') or plant.get('batterySoc') or
                          plant.get('capacity') or plant.get('batteryCapacity') or 0)

                    # Handle string values
                    try:
                        int_solar = int(float(solar)) if solar else 0
                        int_load = int(float(load)) if load else 0
                        int_soc = int(float(soc)) if soc else 0
                    except (ValueError, TypeError):
                        pass

                    print(f"\n  Extracted: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")

                    if int_solar > 0 or int_soc > 0:
                        break  # Got data!

            except json.JSONDecodeError:
                print("  Not JSON response")

    except Exception as e:
        print(f"  Error: {e}")

# --- 3. If no data yet, try the inverter endpoint ---
if int_solar == 0 and int_soc == 0:
    print("\n" + "="*50)
    print("Trying inverter monitoring endpoint...")
    print("="*50)

    inverter_url = EG4_BASE_URL + "/web/monitor/inverter"

    for method in ["POST", "GET"]:
        print(f"\n{method} {inverter_url}")
        try:
            if method == "POST":
                resp = session.post(inverter_url, data={'page': 1, 'rows': 50}, timeout=10)
            else:
                resp = session.get(inverter_url, timeout=10)

            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                content = resp.text[:2000]
                print(f"  Response: {content}")

                # Try to parse as JSON
                try:
                    data = resp.json()
                    rows = data.get('rows', []) if isinstance(data, dict) else []
                    if rows:
                        inverter = rows[0]
                        print(f"\n  Inverter data: {json.dumps(inverter, indent=2)}")

                        solar = inverter.get('solarPower') or inverter.get('pac') or inverter.get('ppv') or 0
                        load = inverter.get('load') or inverter.get('loadPower') or 0
                        soc = inverter.get('soc') or inverter.get('batterySoc') or 0

                        try:
                            int_solar = int(float(solar)) if solar else 0
                            int_load = int(float(load)) if load else 0
                            int_soc = int(float(soc)) if soc else 0
                        except:
                            pass

                        if int_solar > 0 or int_soc > 0:
                            break
                except:
                    pass

        except Exception as e:
            print(f"  Error: {e}")

# --- 4. Final Summary ---
print("\n" + "="*50)
print("FINAL RESULTS")
print("="*50)
print(f"Solar Power: {int_solar}W")
print(f"Load Power: {int_load}W")
print(f"Battery SOC: {int_soc}%")

# --- 5. Write data.json ---
output_data = {
    "battery_soc": int_soc,
    "pv_power": int_solar,
    "load_power": int_load,
    "last_updated": datetime.now(timezone.utc).isoformat()
}

with open('data.json', 'w') as f:
    json.dump(output_data, f, indent=2)

print(f"\nWrote data.json: {json.dumps(output_data)}")
print("Done!")
