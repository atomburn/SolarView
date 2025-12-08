name: Solar Sync

on:
  schedule:
    # Runs every 5 minutes
    - cron: '*/5 * * * *'
  workflow_dispatch: # Allows manual triggering from the GitHub UI

jobs:
  run-solar-relay:
    runs-on: ubuntu-latest
    env:
      EG4_USER: ${{ secrets.EG4_USER }}
      EG4_PASS: ${{ secrets.EG4_PASS }}
      SENSECRAFT_KEY: ${{ secrets.SENSECRAFT_KEY }}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.9
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run solar_relay.py
        run: python solar_relay.py
