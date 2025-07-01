import os
import sys
import logging
import requests
import pyotp
import dotenv
import psycopg2
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

dotenv.load_dotenv()
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
LOCAL_IP = os.getenv("LOCAL_IP", "127.0.0.1")
PUBLIC_IP = os.getenv("PUBLIC_IP", "127.0.0.1")
MAC_ADDRESS = os.getenv("MAC_ADDRESS", "00:11:22:33:44:55")
name = os.getenv("DB_NAME")
dbuser = os.getenv("DB_USER")
passw = os.getenv("DB_PASSWORD")
hst = os.getenv("DB_HOST")
prt = os.getenv("DB_PORT")

def update_jwt_in_db(token):
    conn = psycopg2.connect(
        dbname=name,
        user=dbuser,
        password=passw,
        host=hst,
        port=prt
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO "SystemToken" (key, value, updated_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
    """, ("ANGEL_JWT_TOKEN", token, datetime.now(timezone.utc)))
    conn.commit()
    cur.close()
    conn.close()
    logging.info("JWT token saved in database.")

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
        'X-PrivateKey': API_KEY,
        'User-Agent': 'Mozilla/5.0'
    }

    payload = {
        "clientcode": CLIENT_CODE,
        "password": PASSWORD,
        "totp": totp,
        "state": "flask-app"
    }

    url = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"

    try:
        logging.info("📡 Sending login request to Angel One...")
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=20,
        )
        logging.info(f"🌐 Response status: {response.status_code}")

    except requests.RequestException as e:
        logging.error(f"HTTP request failed: {e}")
        sys.exit(1)

    if response.status_code == 200:
        try:
            data = response.json()["data"]
            jwt_token = data["jwtToken"]
            update_jwt_in_db(jwt_token)
            logging.info("Login successful. JWT token updated.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Failed to parse login response: {e}")
            sys.exit(1)
    else:
        logging.error(f"Login failed: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    login()
