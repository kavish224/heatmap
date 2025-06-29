from flask import Flask, render_template, jsonify, request
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, cast, Date
import logging
import dotenv
import os
import csv
import json
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

dotenv.load_dotenv()
jwt_token = os.getenv("ANGEL_JWT_TOKEN")
db_url = os.getenv("DATABASE_URL")

if not jwt_token or not db_url:
    logger.critical("Missing essential environment variables. Exiting.")
    exit(1)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 60

db = SQLAlchemy(app)
cache = Cache(app)

class HistoricalData1D(db.Model):
    __tablename__ = 'HistoricalData1D'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String, nullable=False)
    closePrice = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime(timezone=True), nullable=False)

symbol_to_instrument = {
    "ADANIENT": "NSE_EQ|25", "ADANIPORTS": "NSE_EQ|15083", "APOLLOHOSP": "NSE_EQ|157",
    "ASIANPAINT": "NSE_EQ|236", "AXISBANK": "NSE_EQ|5900", "BAJAJ-AUTO": "NSE_EQ|16669",
    "BAJFINANCE": "NSE_EQ|317", "BAJAJFINSV": "NSE_EQ|16675", "BEL": "NSE_EQ|383",
    "BHARTIARTL": "NSE_EQ|10604", "CIPLA": "NSE_EQ|694", "COALINDIA": "NSE_EQ|20374",
    "DRREDDY": "NSE_EQ|881", "EICHERMOT": "NSE_EQ|910", "ETERNAL": "NSE_EQ|5097",
    "GRASIM": "NSE_EQ|1232", "HCLTECH": "NSE_EQ|7229", "HDFCBANK": "NSE_EQ|1333",
    "HDFCLIFE": "NSE_EQ|467", "HEROMOTOCO": "NSE_EQ|1348", "HINDALCO": "NSE_EQ|1363",
    "HINDUNILVR": "NSE_EQ|1394", "ICICIBANK": "NSE_EQ|4963", "ITC": "NSE_EQ|1660",
    "INDUSINDBK": "NSE_EQ|5258", "INFY": "NSE_EQ|1594", "JSWSTEEL": "NSE_EQ|11723",
    "JIOFIN": "NSE_EQ|18143", "KOTAKBANK": "NSE_EQ|1922", "LT": "NSE_EQ|11483",
    "M&M": "NSE_EQ|2031", "MARUTI": "NSE_EQ|10999", "NTPC": "NSE_EQ|11630",
    "NESTLEIND": "NSE_EQ|17963", "ONGC": "NSE_EQ|2475", "POWERGRID": "NSE_EQ|14977",
    "RELIANCE": "NSE_EQ|2885", "SBILIFE": "NSE_EQ|21808", "SHRIRAMFIN": "NSE_EQ|4306",
    "SBIN": "NSE_EQ|3045", "SUNPHARMA": "NSE_EQ|3351", "TCS": "NSE_EQ|11536",
    "TATACONSUM": "NSE_EQ|3432", "TATAMOTORS": "NSE_EQ|3456", "TATASTEEL": "NSE_EQ|3499",
    "TECHM": "NSE_EQ|13538", "TITAN": "NSE_EQ|3506", "TRENT": "NSE_EQ|1964",
    "ULTRACEMCO": "NSE_EQ|11532", "WIPRO": "NSE_EQ|3787"
}

def load_symbols():
    try:
        with open('symbols.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader)
            return [row[0].strip().upper() for row in reader]
    except FileNotFoundError:
        logger.warning("symbols.csv not found, falling back to hardcoded list.")
        return list(symbol_to_instrument.keys())

nifty50_symbols = load_symbols()

market_caps = {}
try:
    with open('market_caps.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                market_caps[row['symbol'].strip().upper()] = float(row['market_cap'])
            except (ValueError, KeyError):
                pass
except FileNotFoundError:
    logger.warning("market_caps.csv not found, using fallback values.")
    for s in symbol_to_instrument.keys():
        market_caps[s] = 100_000.0

def get_previous_close_map():
    """Returns map of {symbol: previous_close_price} for last trading day"""
    try:
        date_col = cast(HistoricalData1D.date, Date)
        dates = db.session.query(date_col.label("trading_date")).distinct().order_by(date_col.desc()).limit(2).all()
        if len(dates) < 2:
            return {}

        prev_date = dates[1].trading_date
        rows = db.session.query(HistoricalData1D.symbol, HistoricalData1D.closePrice).filter(
            cast(HistoricalData1D.date, Date) == prev_date
        ).all()
        return {r.symbol.upper(): r.closePrice for r in rows}
    except Exception as e:
        logger.error(f"Error fetching previous close: {e}")
        return {}

def get_stock_data(symbols):
    """Fetch live stock data and compute % change and heatmap value"""
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': os.getenv("LOCAL_IP", "127.0.0.1"),
        'X-ClientPublicIP': os.getenv("PUBLIC_IP", "127.0.0.1"),
        'X-MACAddress': os.getenv("MAC_ADDRESS", "00:00:00:00:00:00"),
        'X-PrivateKey': os.getenv("ANGEL_API_KEY", "")
    }

    token_map = {k: v.split("|")[1] for k, v in symbol_to_instrument.items()}
    valid_symbols = [s for s in symbols if s in token_map]
    previous_closes = get_previous_close_map()

    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
    payload = {
        "mode": "OHLC",
        "exchangeTokens": {"NSE": [token_map[s] for s in valid_symbols]}
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=5)
        data = res.json()
        if not data.get("status"):
            raise ValueError(data.get("message"))

        result = []
        for item in data["data"]["fetched"]:
            symbol = item["tradingSymbol"].replace("-EQ", "")
            ltp = item.get("ltp")
            prev = previous_closes.get(symbol)
            if ltp is None or prev is None or prev == 0:
                continue

            change = ((ltp - prev) / prev) * 100
            result.append({
                'name': f"{symbol}|{ltp:.2f}|{change:.2f}%",
                'value': market_caps.get(symbol, 0),
                'colorValue': change,
                'image': f'/static/images/nifty50_icons/{symbol}.svg'
            })

        return sorted(result, key=lambda x: x['value'], reverse=True)
    except Exception as e:
        logger.error(f"get_stock_data failed: {e}")
        return []

@app.route('/')
def index():
    logger.info("Accessed index route '/'")
    return render_template('index.html')

@app.route('/get_data')
@cache.cached()
def get_data():
    """Endpoint for heatmap data"""
    logger.info("Accessed '/get_data' route - attempting to fetch stock data")

    data = get_stock_data(nifty50_symbols)
    count = len(data)

    if count == 0:
        logger.warning("No stock data returned.")
    else:
        top_gainers = sorted(data, key=lambda x: x['colorValue'], reverse=True)[:3]
        top_losers = sorted(data, key=lambda x: x['colorValue'])[:3]
        logger.info(f"{count} stocks returned. Top gainers: {[s['name'] for s in top_gainers]}")
        logger.info(f"Top losers: {[s['name'] for s in top_losers]}")

    return jsonify(data)

@app.route('/debug')
def debug():
    """Return internal debug information"""
    logger.info("Accessed '/debug' route for internal state inspection")
    info = {
        'symbols_loaded': len(nifty50_symbols),
        'market_caps_loaded': len(market_caps),
        'valid_symbols': [s for s in nifty50_symbols if s in symbol_to_instrument],
        'invalid_symbols': [s for s in nifty50_symbols if s not in symbol_to_instrument]
    }
    logger.debug(f"Debug info: {json.dumps(info)}")
    return jsonify(info)

if __name__ == '__main__':
    logger.info("Starting Flask app on port %s", os.getenv("PORT", 5005))
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5005)), debug=False)
