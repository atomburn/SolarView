import requests
import os
import re
import time
import sys

# --- Script Version ---
SCRIPT_VERSION = "2.7 (Global Overview Table Scraper)"
print(f"Script Version: {SCRIPT_VERSION}\n")

# --- Configuration (URLs) ---
EG4_LOGIN_URL = "https://monitor.eg4electronics.com/WManage/web/login"
EG4_OVERVIEW_URL = "https://monitor.eg4electronics.com/WManage/web/overview/global"
SENSECRAFT_PUSH_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"

# --- Helper Function for cleaning and extracting numbers ---
def clean_and_extract_number(html_text):
    """
    Cleans HTML tags from text and extracts the first integer found.
    Returns 0 if no integer is found.
    """
    cleaned_text = re.sub(r'<[^>]+>', '', html_text).strip()
    match = re.search(r'(\d+)', cleaned_text)
    if match:
        return int(match.group(1))
    return 0

# --- 1. Login to EG4 Electronics Monitoring Portal ---
def login_eg4(session, username, password):
    """
    Logs into the EG4 portal and returns the requests.Session object.
    """
    print("Attempting to log in to EG4 portal...")
    login_data = {
        'account': username,
        'password': password,
        'isRem': 'false',
        'lang': 'en_US'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = session.post(EG4_LOGIN_URL, data=login_data, headers=headers, allow_redirects=False, timeout=10)
        
        if response.status_code == 302 and '/WManage/web/overview/global' in response.headers.get('Location', ''):
            print("Successfully logged in to EG4 portal.")
            return True
        elif response.status_code == 200 and 'login_error' in response.text: # Check for common login error indicators
            print(f"Login failed: Incorrect username or password. Response status: {response.status_code}")
            return False
        else:
            print(f"Login attempt returned unexpected status code: {response.status_code}")
            print("Response content (partial):", response.text[:500]) # Print first 500 chars for debugging
            return False
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during EG4 login: {e}")
        return False

# --- 2. SANITY CHECK (Sensecraft API) ---
def check_sensecraft_api(api_key, device_id):
    """
    Verifies Sensecraft API connection by pushing a test battery_soc.
    """
    print("\nPerforming Sensecraft API sanity check...")
    payload = {
        "device_id": device_id,
        "data": {"battery_soc": 50}
    }
    headers = {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(SENSECRAFT_PUSH_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print("Sensecraft API sanity check successful (200 OK).")
            return True
        elif response.status_code == 500:
            print(f"Sensecraft API sanity check received 500 error: {response.text}")
            print("Ensure 'battery_soc' is defined as a widget in your Sensecraft Dashboard.")
            return False
        else:
            print(f"Sensecraft API sanity check failed with status code {response.status_code}.")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during Sensecraft API sanity check: {e}")
        return False

# --- 3. DATA ACQUISITION (Table Scraping V2.7) ---
def scrape_eg4_overview(session, target_station_name=None):
    """
    Scrapes the EG4 global overview page for power and SOC data.
    """
    print("\nAcquiring data from EG4 overview page...")
    data = {
        "pv_power": 0,
        "battery_soc": 0,
        "load_power": 0,
        "charge_power": 0,
        "discharge_power": 0,
        "net_battery_watts": 0
    }

    try:
        response = session.get(EG4_OVERVIEW_URL, timeout=15)
        response.raise_for_status() # Raise an exception for HTTP errors

        html_content = response.text
        
        # Regex to find all table rows
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html_content, re.DOTALL)

        if not rows:
            print("Warning: No table rows found on the EG4 overview page.")
            return data

        # Skip header row (assuming first row is header)
        data_rows = rows[1:] 

        target_row_cells = None
        for row_content in data_rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row_content, re.DOTALL)
            if len(cells) > 1: # Ensure it's a data row
                status = re.sub(r'<[^>]+>', '', cells[1]).strip() # Status is at index 1
                name = re.sub(r'<[^>]+>', '', cells[0]).strip() # Name is at index 0

                if (status == "Normal" or status == "Offline"):
                    if target_station_name:
                        if name == target_station_name:
                            target_row_cells = cells
                            print(f"Found target station '{name}' with status '{status}'.")
                            break
                    else:
                        target_row_cells = cells
                        print(f"Found first station '{name}' with status '{status}'.")
                        break
        
        if not target_row_cells:
            print("Warning: Could not find any station with 'Normal' or 'Offline' status.")
            print("Ensure the station is visible on the EG4 overview page.")
            return data

        # Extract values based on indices
        # Columns: [Name, Status, SolarPower, ChargePower, DischargePower, Load, SOC, ...]
        try:
            data["pv_power"] = clean_and_extract_number(target_row_cells[2]) # SolarPower
            data["charge_power"] = clean_and_extract_number(target_row_cells[3])
            data["discharge_power"] = clean_and_extract_number(target_row_cells[4])
            data["load_power"] = clean_and_extract_number(target_row_cells[5])
            data["battery_soc"] = clean_and_extract_number(target_row_cells[6])
            
            data["net_battery_watts"] = data["charge_power"] - data["discharge_power"]

            print(f"Scraped Data: PV Power={data['pv_power']}W, Charge Power={data['charge_power']}W, "
                  f"Discharge Power={data['discharge_power']}W, Load Power={data['load_power']}W, "
                  f"SOC={data['battery_soc']}%, Net Battery Watts={data['net_battery_watts']}W")

        except IndexError as e:
            print(f"Error parsing table cells: {e}. Check table structure or column indices.")
            print("Falling back to default 0s for all values.")
            data = {k: 0 for k in data} # Reset all to 0
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching EG4 overview page: {e}")
        print("Falling back to default 0s for all values.")
        data = {k: 0 for k in data} # Reset all to 0
    
    return data

# --- 4. REAL DATA PUSH (Sensecraft) ---
def push_data_to_sensecraft(api_key, device_id, pv_power, battery_soc, load_power):
    """
    Pushes extracted data to the Sensecraft API.
    """
    print("\nPushing data to Sensecraft...")
    payload = {
        "device_id": device_id,
        "data": {
            "pv_power": pv_power,
            "battery_soc": battery_soc,
            "load_power": load_power
        }
    }
    headers = {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(SENSECRAFT_PUSH_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        print("Data successfully pushed to Sensecraft.")
        print(f"Sensecraft Response: {response.status_code} - {response.text}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while pushing data to Sensecraft: {e}")
        print(f"Payload sent: {payload}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Sensecraft Error Response: {e.response.status_code} - {e.response.text}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    # --- Load Environment Variables ---
    EG4_USER = os.environ.get('EG4_USER')
    EG4_PASS = os.environ.get('EG4_PASS')
    EG4_STATION_ID = os.environ.get('EG4_STATION_ID') # Sensecraft device_id
    EG4_STATION_NAME = os.environ.get('EG4_STATION_NAME') # Optional: to target a specific station by name
    SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')

    # --- Check for missing critical environment variables ---
    missing_vars = []
    if not EG4_USER:
        missing_vars.append('EG4_USER')
    if not EG4_PASS:
        missing_vars.append('EG4_PASS')
    if not SENSECRAFT_KEY:
        missing_vars.append('SENSECRAFT_KEY')
    if not EG4_STATION_ID:
        missing_vars.append('EG4_STATION_ID') # Treat as critical for Sensecraft push

    if missing_vars:
        print("\nERROR: The following required environment variables are not set:")
        for var in missing_vars:
            print(f"- {var}")
        print("Please set these variables before running the script.")
        sys.exit(1)

    print(f"EG4_STATION_ID for Sensecraft: {EG4_STATION_ID}")
    if EG4_STATION_NAME:
        print(f"Targeting EG4 Station by Name: {EG4_STATION_NAME}")
    else:
        print("No EG4_STATION_NAME specified. Will scrape data from the first 'Normal' or 'Offline' station found.")


    # --- Step 1: Sensecraft API Sanity Check ---
    if not check_sensecraft_api(SENSECRAFT_KEY, EG4_STATION_ID):
        print("\nSanity check failed. Aborting script.")
        sys.exit(1)

    # --- Initialize requests session ---
    eg4_session = requests.Session()

    # --- Step 2: Login to EG4 Portal ---
    if not login_eg4(eg4_session, EG4_USER, EG4_PASS):
        print("\nEG4 login failed. Aborting script.")
        sys.exit(1)
    
    # After successful login, make a GET request to the overview page
    # The session should automatically handle the redirect if allow_redirects was True
    # or follow the 302 redirect manually if allow_redirects=False was used in post
    # and then subsequent requests will use the session cookies.
    # We already have a valid session from login.

    # --- Step 3: Scrape Data ---
    scraped_data = scrape_eg4_overview(eg4_session, EG4_STATION_NAME)

    if scraped_data["pv_power"] == 0 and \
       scraped_data["battery_soc"] == 0 and \
       scraped_data["load_power"] == 0:
        print("\nWarning: All scraped data values are zero or scraping failed significantly. Check EG4 portal accessibility or table structure.")
        # Decide if you want to push zeros or abort. For now, we'll proceed to push zeros.

    # --- Step 4: Push Data to Sensecraft ---
    push_data_to_sensecraft(
        SENSECRAFT_KEY,
        EG4_STATION_ID,
        scraped_data["pv_power"],
        scraped_data["battery_soc"],
        scraped_data["load_power"]
    )

    print("\nScript execution finished.")
