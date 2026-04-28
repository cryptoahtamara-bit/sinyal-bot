import os, time, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TV_CHART_ID      = "rtSnoL8D"

# ─── TradingView Snapshot ──────────────────────────────────────
def get_screenshot() -> bytes | None:
    try:
        # Snapshot URL'sini al
        snapshot_url = f"https://www.tradingview.com/x/{TV_CHART_ID}/"
        r = requests.get(snapshot_url, timeout=15)
        if r.status_code == 200:
            # Direkt PNG döner
            if b'PNG' in r.content[:8] or r.headers.get('content-type','').startswith('image'):
                return r.content
            # JSON içinde URL döner
            try:
                data = r.json()
                img_url = data.get("url") or data.get("image")
                if img_url:
                    r2 = requests.get(img_url, timeout=15)
                    if r2.status_code == 200:
                        return r2.content
            except Exception:
                pass
        print(f"[SCREENSHOT] Snapshot hatası: {r.status_code}")
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

    emoji   = "🟢" if "BUY" in side or "LONG" in side else "🔴"
    side_tr = "STRONG AL 🚀🔥" if side == "STRONG_BUY" else \
              "AL 🚀"          if side == "LONG"        else \
              "STRONG SAT 💀🔥" if side == "STRONG_SELL" else "SAT 💀"

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
        f"🕐 Zaman: <code>{time.strftime('%Y-%m-%d %H:%M UTC')}</code>"
    )

    base     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    img_data = get_screenshot()

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
