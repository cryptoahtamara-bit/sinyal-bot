import os, time, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHARTIMG_KEY     = os.getenv("CHARTIMG_KEY", "")

# ─── chart-img.com ile screenshot ─────────────────────────────
def get_screenshot(symbol: str, timeframe: str) -> bytes | None:
    if not CHARTIMG_KEY:
        return None

    tf_map = {
        "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
        "60": "1h", "120": "2h", "240": "4h", "D": "1D", "W": "1W", "M": "1M"
    }
    tf = tf_map.get(str(timeframe), "1h")

    url = "https://api.chart-img.com/v1/tradingview/advanced-chart"
    params = {
        "symbol": f"BINANCE:{symbol}",
        "interval": tf,
        "theme": "dark",
        "studies": "RSI",
        "width": 800,
        "height": 500,
    }
    headers = {"x-api-key": CHARTIMG_KEY}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.content
        else:
            print(f"[SCREENSHOT] chart-img hatası: {r.status_code} — {r.text}")
            return None
    except Exception as e:
        print(f"[SCREENSHOT] İstek hatası: {e}")
        return None

# ─── Telegram Gönderici ────────────────────────────────────────
def send_telegram(signal: dict) -> bool:
    sym  = signal.get("symbol", "?")
    tf   = signal.get("timeframe", "?")
    side = signal.get("signal", "?")
    px   = signal.get("price", 0)
    sl   = signal.get("sl", 0)
    tp   = signal.get("tp", 0)
    rsi  = signal.get("rsi", 0)
    atr  = signal.get("atr", 0)

    emoji   = "🟢" if side == "LONG" else "🔴"
    side_tr = "AL  ▲" if side == "LONG" else "SAT ▼"

    caption = (
        f"{emoji} <b>{sym} — {side_tr}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Sembol    : <code>{sym}</code>\n"
        f"⏱ Zaman     : <code>{tf}</code>\n"
        f"💲 Fiyat     : <code>{px}</code>\n"
        f"🛑 Stop Loss : <code>{sl}</code>\n"
        f"🎯 Take Prof : <code>{tp}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 RSI  : <code>{rsi}</code>\n"
        f"📉 ATR  : <code>{atr}</code>\n"
        f"🕐 Zaman: <code>{time.strftime('%Y-%m-%d %H:%M UTC')}</code>"
    )

    base     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    img_data = get_screenshot(sym, tf)

    if img_data:
        resp = requests.post(
            f"{base}/sendPhoto",
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("chart.png", img_data, "image/png")},
            timeout=30,
        )
    else:
        resp = requests.post(
            f"{base}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"},
            timeout=15,
        )

    if resp.status_code == 200:
        print(f"[OK] {sym} {side} sinyali gönderildi.")
        return True
    else:
        print(f"[HATA] Telegram: {resp.status_code} — {resp.text}")
        return False

# ─── Webhook ──────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON bekleniyor"}), 400

    print(f"[WEBHOOK] Gelen sinyal: {data}")

    required = ["symbol", "signal", "price"]
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Eksik alanlar: {missing}"}), 400

    ok = send_telegram(data)
    return jsonify({"status": "ok" if ok else "error"}), 200 if ok else 500

# ─── Sağlık kontrolü ──────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "running", "time": time.strftime("%Y-%m-%d %H:%M UTC")})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Sunucu başlatılıyor → http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
