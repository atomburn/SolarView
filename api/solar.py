from http.server import BaseHTTPRequestHandler
import requests
import os
import json
from datetime import datetime, timezone

def get_solar_data():
    """Fetch live data from EG4 API"""

    EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
    EG4_BASE_URL = "https://monitor.eg4electronics.com/WManage"

    EG4_USER = os.environ.get('EG4_USER')
    EG4_PASS = os.environ.get('EG4_PASS')

    if not EG4_USER or not EG4_PASS:
        return {"error": "Missing credentials", "battery_soc": 0, "pv_power": 0, "load_power": 0}

    # Create session and login
    session = requests.Session()

    try:
        login_response = session.post(EG4_LOGIN_URL, data={
            'account': EG4_USER,
            'password': EG4_PASS,
            'isRem': 'false',
            'lang': 'en_US'
        }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
        login_response.raise_for_status()
    except Exception as e:
        return {"error": f"Login failed: {str(e)}", "battery_soc": 0, "pv_power": 0, "load_power": 0}

    # Fetch plant data
    try:
        api_url = EG4_BASE_URL + "/api/plantOverview/list/viewer"
        resp = session.post(api_url, data={'page': 1, 'rows': 50}, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            rows = data.get('rows', [])

            if rows:
                plant = rows[0]

                # Extract values
                int_solar = int(plant.get('ppv', 0) or 0)
                int_load = int(plant.get('pConsumption', 0) or 0)

                # Parse SOC string "73 %" -> 73
                soc_str = plant.get('soc', '0')
                try:
                    int_soc = int(soc_str.replace('%', '').strip())
                except (ValueError, AttributeError):
                    int_soc = 0

                return {
                    "battery_soc": int_soc,
                    "pv_power": int_solar,
                    "load_power": int_load,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }

    except Exception as e:
        return {"error": f"API failed: {str(e)}", "battery_soc": 0, "pv_power": 0, "load_power": 0}

    return {"error": "No data", "battery_soc": 0, "pv_power": 0, "load_power": 0}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Get fresh data from EG4
        data = get_solar_data()

        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # Allow SenseCraft to access
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()

        self.wfile.write(json.dumps(data).encode())
