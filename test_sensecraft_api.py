#!/usr/bin/env python3
"""
Minimal SenseCraft API Test Script
Purpose: Send fake battery_soc data to verify API connectivity

Usage:
  export SENSECRAFT_KEY="your-api-key-here"
  python test_sensecraft_api.py

  Or with inline key:
  SENSECRAFT_KEY="your-api-key-here" python test_sensecraft_api.py
"""

import requests
import os
import sys

# --- Configuration ---
SENSECRAFT_API_URL = "https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data"
SENSECRAFT_DEVICE_ID = "20221942"  # Your device ID from the existing script

# Get API key from environment
SENSECRAFT_KEY = os.environ.get('SENSECRAFT_KEY')

if not SENSECRAFT_KEY:
    print("ERROR: SENSECRAFT_KEY environment variable not set")
    print("\nUsage:")
    print('  export SENSECRAFT_KEY="your-api-key-here"')
    print('  python test_sensecraft_api.py')
    sys.exit(1)

print("=" * 50)
print("SenseCraft API Test - battery_soc")
print("=" * 50)
print(f"API URL: {SENSECRAFT_API_URL}")
print(f"Device ID: {SENSECRAFT_DEVICE_ID}")
print(f"API Key: {SENSECRAFT_KEY[:8]}...{SENSECRAFT_KEY[-4:]}" if len(SENSECRAFT_KEY) > 12 else "***")
print()

# --- Test Payload: Just battery_soc ---
test_soc_value = 75  # Fake value - change this to any 0-100 value

payload = {
    "device_id": SENSECRAFT_DEVICE_ID,
    "data": {
        "battery_soc": test_soc_value
    }
}

headers = {
    "api-key": SENSECRAFT_KEY,
    "Content-Type": "application/json"
}

print(f"Sending test payload: battery_soc = {test_soc_value}%")
print(f"Full payload: {payload}")
print()

try:
    response = requests.post(
        SENSECRAFT_API_URL,
        json=payload,
        headers=headers,
        timeout=15
    )

    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    print()

    if response.status_code == 200:
        print("SUCCESS! Data sent to SenseCraft API.")
        print("Check your link display - battery_soc should show 75%")
    elif response.status_code == 401:
        print("FAILED: Invalid API key (401 Unauthorized)")
    elif response.status_code == 404:
        print("FAILED: Device not found (404). Check SENSECRAFT_DEVICE_ID")
    elif response.status_code == 500:
        print("FAILED: Server error (500). The 'battery_soc' data key may not be defined in your SenseCraft dashboard")
    else:
        print(f"FAILED: Unexpected response code {response.status_code}")

    response.raise_for_status()

except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")
    sys.exit(1)
except requests.exceptions.ConnectionError:
    print("Connection Error: Could not reach SenseCraft API")
    sys.exit(1)
except requests.exceptions.Timeout:
    print("Timeout: Request took too long")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"Request Error: {e}")
    sys.exit(1)

print("\nTest complete!")
