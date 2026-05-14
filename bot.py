import os
import time
import hmac
import json
import hashlib
import requests
from flask import Flask, request, jsonify

# =========================================================
# CONFIG
# =========================================================

MEXC_API_KEY = os.getenv("MEXC_API_KEY", "")
MEXC_SECRET_KEY = os.getenv("MEXC_SECRET_KEY", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

MEXC_BASE_URL = "https://contract.mexc.com"

TRADE_MARGIN_USDT = float(os.getenv("MEXC_MARGIN_USDT", "0.25"))
DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", "100"))

app = Flask(__name__)

contract_cache = {}

# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(message):
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("[TELEGRAM] Token/chat id eksik")
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        requests.post(url, json=payload, timeout=10)

    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# =========================================================
# MEXC HELPERS
# =========================================================

def mexc_format_symbol(symbol: str):
    symbol = symbol.upper()

    symbol = symbol.replace(".P", "")
    symbol = symbol.replace("/", "")

    if symbol.endswith("USDT") and "_USDT" not in symbol:
        symbol = symbol.replace("USDT", "_USDT")

    return symbol

def get_contract_detail(symbol):
    global contract_cache

    if symbol in contract_cache:
        return contract_cache[symbol]

    url = f"{MEXC_BASE_URL}/api/v1/contract/detail"

    r = requests.get(url, timeout=10)
    data = r.json()

    if not data.get("success"):
        raise Exception(f"Contract detail alınamadı: {data}")

    for item in data.get("data", []):
        if item["symbol"] == symbol:
            contract_cache[symbol] = item
            return item

    raise Exception(f"Contract bulunamadı: {symbol}")

def get_max_leverage(symbol):
    detail = get_contract_detail(symbol)

    try:
        return int(detail.get("maxLeverage", 20))
    except:
        return 20

def calculate_contract_volume(symbol, price, leverage):
    detail = get_contract_detail(symbol)

    contract_size = float(detail.get("contractSize", 0.0001))
    min_vol = float(detail.get("minVol", 1))
    vol_scale = int(detail.get("volScale", 0))

    margin = TRADE_MARGIN_USDT

    notional = margin * leverage

    raw_contracts = notional / (price * contract_size)

    volume = round(raw_contracts, vol_scale)

    if volume < min_vol:
        volume = min_vol

    return volume

# =========================================================
# SIGNATURE
# =========================================================

def mexc_signature(secret_key, payload):
    return hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

# =========================================================
# ORDER
# =========================================================

def create_order(symbol, signal, entry_price):

    sym = mexc_format_symbol(symbol)

    leverage = DEFAULT_LEVERAGE

    volume = calculate_contract_volume(
        sym,
        float(entry_price),
        leverage
    )

    if signal.upper() in ["LONG", "STRONG BUY"]:
        side = 1
    else:
        side = 2

    endpoint = "/api/v1/private/order/submit"

    order_body = {
        "symbol": sym,
        "price": 0,
        "vol": volume,
        "side": side,
        "type": 5,
        "openType": 2,
        "leverage": leverage
    }

    req_time = str(int(time.time() * 1000))

    body_str = json.dumps(order_body, separators=(",", ":"))

    sign_payload = MEXC_API_KEY + req_time + body_str

    sign = mexc_signature(
        MEXC_SECRET_KEY,
        sign_payload
    )

    headers = {
        "ApiKey": MEXC_API_KEY,
        "Request-Time": req_time,
        "Signature": sign,
        "Content-Type": "application/json"
    }

    url = MEXC_BASE_URL + endpoint

    print(f"[MEXC] ORDER => {order_body}")

    r = requests.post(
        url,
        headers=headers,
        data=body_str,
        timeout=15
    )

    print(f"[MEXC] STATUS => {r.status_code}")
    print(f"[MEXC] RAW RESPONSE => {r.text}")

    try:
        result = r.json()
    except:
        result = {
            "success": False,
            "status_code": r.status_code,
            "raw_response": r.text
        }

    print(f"[MEXC] RESPONSE => {result}")

    return result

# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:
        data = request.json

        print(f"[WEBHOOK] {data}")

        symbol = data.get("symbol")
        signal = data.get("signal")
        price = float(data.get("price", 0))

        if not symbol or not signal:
            return jsonify({
                "success": False,
                "message": "Eksik veri"
            })

        result = create_order(
            symbol,
            signal,
            price
        )

        send_telegram(
            f"""🚀 MEXC Futures İşlem

Sembol: {symbol}
Sinyal: {signal}
Fiyat: {price}

Sonuç:
{result}
"""
        )

        return jsonify(result)

    except Exception as e:

        print(f"[ERROR] {e}")

        send_telegram(
            f"❌ BOT ERROR\n\n{e}"
        )

        return jsonify({
            "success": False,
            "error": str(e)
        })

# =========================================================
# ROOT
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return "MEXC Futures Bot Aktif"

# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    port = int(os.getenv("PORT", 8080))

    print("[BOT] MEXC Futures Bot Başlatıldı")

    app.run(
        host="0.0.0.0",
        port=port
    )
