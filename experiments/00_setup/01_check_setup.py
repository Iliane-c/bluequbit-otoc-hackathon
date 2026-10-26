"""First check of the environment: is the BlueQubit token set and does the SDK connect?

Originally: test_setup.py
"""

import os

import bluequbit
from dotenv import load_dotenv

load_dotenv()


def main():
    api_token = os.getenv("BLUEQUBIT_API_TOKEN")
    if not api_token or api_token == "your_bluequbit_api_token_here":
        print("Error: BLUEQUBIT_API_TOKEN is missing or not configured in .env")
        return

    try:
        bluequbit.init()
        print("Success: BlueQubit API connection initialized.")
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    main()
