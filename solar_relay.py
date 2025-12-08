import requests
import os
from bs4 import BeautifulSoup
import sys
import json
import re
from datetime import datetime, timezone

# --- Script Version ---
print("Script Version: 4.2 (JSON/Regex Extraction)")

# --- 0. Configuration ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_OVERVIEW_URL = "https://monitor.eg4electronics.com/WManage/web/overview/global"

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

# --- 2. Fetch Overview Page ---
print("\nFetching overview page...")

int_solar = 0
int_load = 0
int_soc = 0

try:
    overview_response = session.get(EG4_OVERVIEW_URL, timeout=15)
    overview_response.raise_for_status()
    page_text = overview_response.text
    print(f"Page length: {len(page_text)} chars")

    # Method 1: Look for JSON data in script tags
    print("\nSearching for embedded JSON data...")

    # Common patterns for embedded data
    json_patterns = [
        r'var\s+plantData\s*=\s*(\[.*?\]);',
        r'var\s+data\s*=\s*(\[.*?\]);',
        r'"plants"\s*:\s*(\[.*?\])',
        r'"stations"\s*:\s*(\[.*?\])',
        r'\{"solarPower":\s*(\d+)',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, page_text, re.DOTALL)
        if match:
            print(f"Found pattern: {pattern[:30]}...")
            print(f"Match: {match.group(0)[:200]}...")

    # Method 2: Extract values directly using regex
    print("\nExtracting values with regex...")

    # Look for SolarPower value
    solar_patterns = [
        r'"solarPower"\s*:\s*(\d+)',
        r'"SolarPower"\s*:\s*(\d+)',
        r'solarPower["\s:]+(\d+)',
        r'>(\d+)\s*W<.*?SolarPower',
        r'SolarPower.*?>(\d+)',
    ]

    for pattern in solar_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            int_solar = int(match.group(1))
            print(f"Found SolarPower: {int_solar}W (pattern: {pattern[:30]})")
            break

    # Look for Load value
    load_patterns = [
        r'"load"\s*:\s*(\d+)',
        r'"Load"\s*:\s*(\d+)',
        r'load["\s:]+(\d+)',
    ]

    for pattern in load_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            int_load = int(match.group(1))
            print(f"Found Load: {int_load}W")
            break

    # Look for SOC value
    soc_patterns = [
        r'"soc"\s*:\s*(\d+)',
        r'"SOC"\s*:\s*(\d+)',
        r'soc["\s:]+(\d+)',
        r'>(\d+)\s*%<',
    ]

    for pattern in soc_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            int_soc = int(match.group(1))
            print(f"Found SOC: {int_soc}%")
            break

    # Method 3: If still no data, try to find any API endpoints and call them
    if int_solar == 0 and int_soc == 0:
        print("\nNo data found via regex. Looking for API calls...")

        # Look for AJAX URLs in the page
        api_patterns = [
            r'url\s*:\s*["\']([^"\']*overview[^"\']*)["\']',
            r'url\s*:\s*["\']([^"\']*plant[^"\']*)["\']',
            r'url\s*:\s*["\']([^"\']*station[^"\']*)["\']',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, page_text)
            for url in matches[:3]:
                print(f"Found potential API: {url}")

    # Print a snippet of the page for debugging
    print("\n--- Page snippet (first 2000 chars) ---")
    print(page_text[:2000])
    print("--- End snippet ---")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print(f"\nExtracted: Solar={int_solar}W, Load={int_load}W, SOC={int_soc}%")

# --- 3. Write data.json ---
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
