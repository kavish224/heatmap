import time
import random
from flask import Flask, render_template, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import csv
import requests

app = Flask(__name__)

def load_symbols():
    with open('symbols.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header
        return [row[0] for row in reader]

nifty50_symbols = load_symbols()


symbol_to_instrument = {
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "BAJAJFINSV": "NSE_EQ|INE918I01018",
    "BPCL": "NSE_EQ|INE029A01011",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "INFRATEL": "NSE_EQ|INE121J01017",
    "CIPLA": "NSE_EQ|INE059A01026",
    "COALINDIA": "NSE_EQ|INE522F01014",
    "DRREDDY": "NSE_EQ|INE089A01023",
    "EICHERMOT": "NSE_EQ|INE066A01013",
    "GAIL": "NSE_EQ|INE129A01019",
    "GRASIM": "NSE_EQ|INE047A01021",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "HDFCBANK": "NSE_EQ|INE040A01026",
    "HEROMOTOCO": "NSE_EQ|INE158A01026",
    "HINDALCO": "NSE_EQ|INE038A01020",
    "HINDPETRO": "NSE_EQ|INE094A01015",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "HDFC": "NSE_EQ|INE001A01036",
    "ITC": "NSE_EQ|INE154A01025",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "IBULHSGFIN": "NSE_EQ|INE148I01020",
    "IOC": "NSE_EQ|INE242A01010",
    "INDUSINDBK": "NSE_EQ|INE095A01012",
    "INFY": "NSE_EQ|INE009A01021",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "LT": "NSE_EQ|INE018A01030",
    "LUPIN": "NSE_EQ|INE326A01037",
    "M&M": "NSE_EQ|INE101A01026",
    "MARUTI": "NSE_EQ|INE585B01010",
    "NTPC": "NSE_EQ|INE733E01010",
    "ONGC": "NSE_EQ|INE213A01029",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "RELIANCE": "NSE_EQ|INE002A01018",
    "SBIN": "NSE_EQ|INE062A01020",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "TCS": "NSE_EQ|INE467B01029",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "TATASTEEL": "NSE_EQ|INE081A01012",
    "TECHM": "NSE_EQ|INE669C01036",
    "TITAN": "NSE_EQ|INE280A01028",
    "UPL": "NSE_EQ|INE628A01036",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "VEDL": "NSE_EQ|INE205A01025",
    "WIPRO": "NSE_EQ|INE075A01022",
    "YESBANK": "NSE_EQ|INE528G01027",
    "ZEEL": "NSE_EQ|INE256A01028"
}

market_caps = {}
with open('market_caps.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        symbol = row['symbol']
        try:
            market_caps[symbol] = float(row['market_cap'])
        except:
            market_caps[symbol] = 0.0

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIyS0FEWTIiLCJqdGkiOiI2ODVkNzYyYzEwMjRkODE0MjRjOTE0NzAiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc1MDk1NTU2NCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzUwOTc1MjAwfQ.-EEDSsRx3jkocDEXy-oIdxAPo90W2pQhkrQ1aXdzGXw"

def get_stock_data(symbols):
    instrument_keys = [symbol_to_instrument[s] for s in symbols if s in symbol_to_instrument]

    url = 'https://api.upstox.com/v2/market-quote/ohlc'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }
    params = {
        'instrument_key': ",".join(instrument_keys),
        'interval': '1d'
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Upstox API error: {response.status_code}")
            return []
        data = response.json()
        result = []

        for key, details in data["data"].items():
            instrument_token = details.get("instrument_token")
            symbol = next((sym for sym, k in symbol_to_instrument.items() if k == instrument_token), None)
            if not symbol:
                continue

            ohlc_data = details.get("ohlc", {})
            close = ohlc_data.get("close")
            prev_close = ohlc_data.get("open")
            
            if close is None or prev_close is None or prev_close == 0:
                continue

            change_percent = ((close - prev_close) / prev_close) * 100
            market_cap = market_caps.get(symbol, 0)
            result.append({
                'name': f"{symbol}|{close:.2f}|{change_percent:.2f}%",
                'value': float(market_cap),
                'colorValue': float(change_percent),
                'image': f'/static/images/nifty50_icons/{symbol}.svg'
            })
        print(result)
        return result

    except Exception as e:
        print(f"Exception in get_stock_data: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    results = get_stock_data(nifty50_symbols)
    print(results)
    results.sort(key=lambda x: x['value'], reverse=True)
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
