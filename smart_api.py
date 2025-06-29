import requests
import os
import pyotp
import dotenv
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Load .env
dotenv_path = Path(__file__).parent / ".env"
dotenv.load_dotenv(dotenv_path)

# Environment variables
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

LOCAL_IP = os.getenv("LOCAL_IP", "127.0.0.1")
PUBLIC_IP = os.getenv("PUBLIC_IP", "127.0.0.1")
MAC_ADDRESS = os.getenv("MAC_ADDRESS", "00:11:22:33:44:55")

# Safely update .env file
def update_env_variable(key, value):
    lines = []
    key_found = False

    if dotenv_path.exists():
        with open(dotenv_path, "r") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    key_found = True
                else:
                    lines.append(line)

    if not key_found:
        lines.append(f"{key}={value}\n")

    # Write to temporary file first
    temp_path = dotenv_path.with_suffix(".env.tmp")
    with open(temp_path, "w") as f:
        f.writelines(lines)

    temp_path.replace(dotenv_path)
    logging.info(f"Updated {key} in .env")

# Login to Angel One and save JWT token
def login():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
    except Exception as e:
        logging.error(f"Failed to generate TOTP: {e}")
        sys.exit(1)

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': LOCAL_IP,
        'X-ClientPublicIP': PUBLIC_IP,
        'X-MACAddress': MAC_ADDRESS,
        'X-PrivateKey': API_KEY
    }

    payload = {
        "clientcode": CLIENT_CODE,
        "password": PASSWORD,
        "totp": totp,
        "state": "flask-app"
    }

    url = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"

    try:
        response = requests.post(url, headers=headers, json=payload)
    except requests.RequestException as e:
        logging.error(f"HTTP request failed: {e}")
        sys.exit(1)

    if response.status_code == 200:
        try:
            data = response.json()["data"]
            jwt_token = data["jwtToken"]
            update_env_variable("ANGEL_JWT_TOKEN", jwt_token)
            logging.info("✅ Login successful. JWT token updated.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Failed to parse login response: {e}")
            sys.exit(1)
    else:
        logging.error(f"❌ Login failed: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    login()
