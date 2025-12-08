import requests
import os
import sys
import json
import re
from datetime import datetime, timezone

# --- Script Version ---
print("Script Version: 4.6 (Explore Portal Structure)")

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
print("\nLogging in to EG4 portal...")
session = requests.Session()

try:
    login_response = session.post(EG4_LOGIN_URL, data={
        'account': EG4_USER,
        'password': EG4_PASS,
        'isRem': 'false',
        'lang': 'en_US'
    }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)

    print(f"Login response status: {login_response.status_code}")
    print(f"Login response (first 500 chars): {login_response.text[:500]}")
    print(f"Session cookies: {dict(session.cookies)}")

except Exception as e:
    print(f"Login failed: {e}")
    sys.exit(1)

int_solar = 0
int_load = 0
int_soc = 0

# --- 2. Explore the portal after login ---
print("\n" + "="*50)
print("STEP 1: Fetching main pages to find API endpoints...")
print("="*50)

# Try various main pages to find what URLs exist
main_pages = [
    "/web/overview/global",
    "/web/index",
    "/index",
    "/web/home",
    "/home",
    "/",
]

found_urls = set()

for page in main_pages:
    url = EG4_BASE_URL + page
    print(f"\nGET {url}")
    try:
        resp = session.get(url, timeout=10)
        print(f"  Status: {resp.status_code}")

        if resp.status_code == 200:
            page_text = resp.text
            print(f"  Page length: {len(page_text)} chars")

            # Look for URLs in the page
            url_patterns = [
                r'url\s*[=:]\s*["\']([^"\']+)["\']',
                r'href\s*=\s*["\']([^"\']*(?:api|data|list|overview|monitor|inverter|plant|station)[^"\']*)["\']',
                r'src\s*=\s*["\']([^"\']*\.js)["\']',
                r'["\']/(WManage/)?([^"\']*(?:list|data|overview|monitor)[^"\']*)["\']',
            ]

            for pattern in url_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = ''.join(match)
                    if match and len(match) > 3 and not match.endswith(('.css', '.png', '.jpg', '.ico')):
                        found_urls.add(match)

            # Print page snippet
            print(f"\n  --- Page content (first 1500 chars) ---")
            print(page_text[:1500])
            print("  --- End snippet ---")

            # Also look for embedded JSON data
            json_data_pattern = r'(?:var\s+\w+\s*=\s*|data\s*:\s*)(\{[^}]+\}|\[[^\]]+\])'
            json_matches = re.findall(json_data_pattern, page_text)
            if json_matches:
                print(f"\n  Found {len(json_matches)} potential JSON blocks")
                for jm in json_matches[:3]:
                    print(f"    {jm[:200]}")

            break  # Found a working page

    except Exception as e:
        print(f"  Error: {e}")

print(f"\n\nFound {len(found_urls)} potential API URLs:")
for url in sorted(found_urls)[:30]:
    print(f"  - {url}")

# --- 3. Try discovered URLs ---
print("\n" + "="*50)
print("STEP 2: Trying discovered API URLs...")
print("="*50)

# Also try some common patterns based on WManage/SEMS portals
common_apis = [
    "/web/station/list",
    "/web/device/list",
    "/web/inverter/list",
    "/api/v1/plant/list",
    "/api/v1/station/list",
    "/api/v1/device/list",
    "/api/plant/list",
    "/api/station/list",
    "/api/inverter/list",
    "/web/plant/list",
    "/plant/list",
    "/station/list",
    "/inverter/list",
    "/overview/list",
]

for endpoint in common_apis:
    url = EG4_BASE_URL + endpoint
    try:
        # Try both GET and POST
        for method in ["GET", "POST"]:
            if method == "GET":
                resp = session.get(url, timeout=5)
            else:
                resp = session.post(url, data={'page': 1, 'rows': 50}, timeout=5)

            if resp.status_code == 200:
                print(f"\n{method} {url}")
                print(f"  Status: {resp.status_code}")
                print(f"  Response: {resp.text[:500]}")

                try:
                    data = resp.json()
                    print(f"  JSON keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")

                    # Try to extract data
                    if isinstance(data, dict):
                        rows = data.get('rows', data.get('data', data.get('list', [])))
                        if rows and isinstance(rows, list) and rows:
                            print(f"  Found {len(rows)} items")
                            print(f"  First item: {json.dumps(rows[0], indent=2)[:500]}")
                except:
                    pass

                break  # Found working endpoint

    except Exception as e:
        pass  # Silently skip errors for quick scan

# --- 4. Final Summary ---
print("\n" + "="*50)
print("FINAL RESULTS")
print("="*50)
print(f"Solar Power: {int_solar}W")
print(f"Load Power: {int_load}W")
print(f"Battery SOC: {int_soc}%")

# --- 5. Write data.json ---
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
