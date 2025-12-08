import requests
import os
from bs4 import BeautifulSoup
import sys
import json
from datetime import datetime, timezone

# --- Script Version ---
print("Script Version: 4.1 (Debug Mode)")

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

try:
    login_response = session.post(EG4_LOGIN_URL, data=login_data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
    login_response.raise_for_status()
    print(f"Login response URL: {login_response.url}")
    print("Successfully logged in to EG4 portal.")
except requests.exceptions.RequestException as e:
    print(f"ERROR: EG4 Login request failed: {e}")
    sys.exit(1)

# --- 2. DATA ACQUISITION (Debug Mode) ---
print("\n" + "="*60)
print("DEBUG: Fetching overview page...")
print("="*60)

int_solar = 0
int_load = 0
int_soc = 0

try:
    overview_response = session.get(EG4_OVERVIEW_URL, timeout=15)
    overview_response.raise_for_status()
    print(f"Overview URL: {overview_response.url}")
    print(f"Response length: {len(overview_response.text)} chars")

    soup = BeautifulSoup(overview_response.text, 'html.parser')

    # Find ALL tables
    all_tables = soup.find_all('table')
    print(f"\nFound {len(all_tables)} table(s) on page")

    for i, table in enumerate(all_tables):
        print(f"\n--- TABLE {i} ---")
        table_class = table.get('class', 'no-class')
        table_id = table.get('id', 'no-id')
        print(f"Class: {table_class}, ID: {table_id}")

        # Get headers
        headers = table.find_all('th')
        if headers:
            header_text = [th.text.strip() for th in headers]
            print(f"Headers: {header_text}")

        # Get rows
        rows = table.find_all('tr')
        print(f"Rows: {len(rows)}")

        for j, row in enumerate(rows[:5]):  # First 5 rows only
            cols = row.find_all(['td', 'th'])
            col_text = [c.text.strip()[:20] for c in cols]  # First 20 chars each
            print(f"  Row {j}: {col_text}")

    # Also check for div-based data (some sites use divs instead of tables)
    print("\n--- Checking for data divs ---")
    data_divs = soup.find_all('div', class_=lambda x: x and ('data' in x.lower() or 'value' in x.lower() or 'card' in x.lower()))
    print(f"Found {len(data_divs)} potential data divs")

    # Look for specific values in the page text
    page_text = overview_response.text
    if 'SolarPower' in page_text or 'solarPower' in page_text:
        print("\n'SolarPower' found in page!")
    if 'SOC' in page_text:
        print("'SOC' found in page!")
    if 'Normal' in page_text:
        print("'Normal' status found in page!")
    if 'Cinnamon' in page_text:
        print("'Cinnamon' found in page!")

    # Try to find the actual data table and extract values
    for table in all_tables:
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')

        for row in rows:
            cols = row.find_all('td')
            row_text = ' '.join(td.text.strip() for td in cols)

            if 'Normal' in row_text or 'Cinnamon' in row_text:
                print(f"\n*** FOUND TARGET ROW ***")
                print(f"Row has {len(cols)} columns:")
                for idx, col in enumerate(cols):
                    print(f"  [{idx}]: '{col.text.strip()}'")

                # Try to extract based on what we see
                # Looking at screenshot: Name, Status, SolarPower, ChargePower, DischargePower, Load, SOC
                if len(cols) >= 7:
                    try:
                        # Station Overview: col[2]=SolarPower, col[5]=Load, col[6]=SOC
                        solar_str = cols[2].text.strip().replace('W', '').replace(' ', '')
                        load_str = cols[5].text.strip().replace('W', '').replace(' ', '')
                        soc_str = cols[6].text.strip().replace('%', '').replace(' ', '')

                        int_solar = int(float(solar_str)) if solar_str else 0
                        int_load = int(float(load_str)) if load_str else 0
                        int_soc = int(float(soc_str)) if soc_str else 0
                        print(f"Parsed: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")
                    except Exception as e:
                        print(f"Parse error: {e}")
                break

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("="*60)
print(f"\nExtracted Data: Solar Power: {int_solar}W, Load: {int_load}W, Battery SOC: {int_soc}%")

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

print("\nScript finished!")
