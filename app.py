from flask import Flask, render_template, jsonify
from flask_caching import Cache
import csv
import os
import requests
import dotenv
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
dotenv.load_dotenv()
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})
def load_symbols():
    try:
        with open('symbols.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader)
            return [row[0] for row in reader]
    except FileNotFoundError:
        print("symbols.csv not found, using default symbols")
        return list(symbol_to_instrument.keys())

nifty50_symbols = load_symbols()
symbol_to_instrument = {
    "ADANIENT": "NSE_EQ|INE423A01024",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "APOLLOHOSP": "NSE_EQ|INE437A01024",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
    "BAJFINANCE": "NSE_EQ|INE296A01032",  # Updated ISIN
    "BAJAJFINSV": "NSE_EQ|INE918I01026",  # Updated ISIN
    "BEL": "NSE_EQ|INE263A01024",         # New addition
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "CIPLA": "NSE_EQ|INE059A01026",
    "COALINDIA": "NSE_EQ|INE522F01014",
    "DRREDDY": "NSE_EQ|INE089A01031",     # Updated ISIN
    "EICHERMOT": "NSE_EQ|INE066A01021",   # Updated ISIN
    "ETERNAL": "NSE_EQ|INE758T01015",     # New addition
    "GRASIM": "NSE_EQ|INE047A01021",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "HDFCBANK": "NSE_EQ|INE040A01034",    # Updated ISIN
    "HDFCLIFE": "NSE_EQ|INE795G01014",
    "HEROMOTOCO": "NSE_EQ|INE158A01026",
    "HINDALCO": "NSE_EQ|INE038A01020",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "ITC": "NSE_EQ|INE154A01025",
    "INDUSINDBK": "NSE_EQ|INE095A01012",
    "INFY": "NSE_EQ|INE009A01021",
    "JSWSTEEL": "NSE_EQ|INE019A01038",
    "JIOFIN": "NSE_EQ|INE758E01017",      # New addition
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "LT": "NSE_EQ|INE018A01030",
    "M&M": "NSE_EQ|INE101A01026",
    "MARUTI": "NSE_EQ|INE585B01010",
    "NTPC": "NSE_EQ|INE733E01010",
    "NESTLEIND": "NSE_EQ|INE239A01024",   # Updated ISIN
    "ONGC": "NSE_EQ|INE213A01029",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "RELIANCE": "NSE_EQ|INE002A01018",
    "SBILIFE": "NSE_EQ|INE123W01016",
    "SHRIRAMFIN": "NSE_EQ|INE721A01047",  # Updated ISIN
    "SBIN": "NSE_EQ|INE062A01020",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "TCS": "NSE_EQ|INE467B01029",
    "TATACONSUM": "NSE_EQ|INE192A01025",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "TATASTEEL": "NSE_EQ|INE081A01020",   # Updated ISIN
    "TECHM": "NSE_EQ|INE669C01036",
    "TITAN": "NSE_EQ|INE280A01028",
    "TRENT": "NSE_EQ|INE849A01020",       # New addition
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "WIPRO": "NSE_EQ|INE075A01022"
}

market_caps = {}
try:
    with open('market_caps.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row['symbol']
            try:
                market_caps[symbol] = float(row['market_cap'])
            except (ValueError, KeyError):
                market_caps[symbol] = 0.0
except FileNotFoundError:
    logger.warning("market_caps.csv not found, using default values")
    for symbol in symbol_to_instrument.keys():
        market_caps[symbol] = 100000.0 

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

def get_stock_data(symbols):
    valid_symbols = [s.upper() for s in symbols if s.upper() in symbol_to_instrument]
    if not valid_symbols:
        logger.warning("No valid symbols found in symbol_to_instrument mapping")
        return []
    instrument_keys = [symbol_to_instrument[symbol] for symbol in valid_symbols]
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
            logger.error(f"Upstox API error: {response.status_code}")
            return []
        data = response.json()
        if "data" not in data:
            logger.warning("No 'data' key in response")
            return []
        result = []
        for api_key, details in data["data"].items():
            instrument_token = details.get("instrument_token")
            if not instrument_token:
                logger.warning(f"No instrument_token found for API key: {api_key}")
                continue
            symbol = None
            for sym, token in symbol_to_instrument.items():
                if token == instrument_token:
                    symbol = sym
                    break
            if not symbol:
                continue

            ohlc_data = details.get("ohlc", {})
            close = ohlc_data.get("close")
            open_price = ohlc_data.get("open")
            
            if close is None or open_price is None or open_price == 0:
                continue

            change_percent = ((close - open_price) / open_price) * 100
            market_cap = market_caps.get(symbol, 0)
            
            result.append({
                'name': f"{symbol}|{close:.2f}|{change_percent:.2f}%",
                'value': float(market_cap),
                'colorValue': float(change_percent),
                'image': f'/static/images/nifty50_icons/{symbol}.svg'
            })
            
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception in get_stock_data: {e}")
        return []
    except Exception as e:
        logger.error(f"General exception in get_stock_data: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
@cache.cached()
def get_data():
    results = get_stock_data(nifty50_symbols)
    if results:
        results.sort(key=lambda x: x['value'], reverse=True)
    return jsonify(results)

@app.route('/debug')
def debug():
    """Debug endpoint to check symbol mapping"""
    debug_info = {
        'loaded_symbols': nifty50_symbols,
        'symbol_to_instrument_keys': len(symbol_to_instrument),
        'market_caps_loaded': len(market_caps),
        'valid_symbols': [s for s in nifty50_symbols if s.upper() in symbol_to_instrument],
        'invalid_symbols': [s for s in nifty50_symbols if s.upper() not in symbol_to_instrument]
    }
    return jsonify(debug_info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
