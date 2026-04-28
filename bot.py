"""
TradingView → Telegram Sinyal Botu
------------------------------------
Kurulum:
  pip install flask requests python-dotenv

Çalıştırma:
  python bot.py

Gerekli .env değişkenleri:
  TELEGRAM_TOKEN   = 7xxxxxxxxx:AAF...
  TELEGRAM_CHAT_ID = -100xxxxxxxxx   (kanal = -100..., grup = -...)
  TV_CHART_URL     = https://www.tradingview.com/chart/CHART_ID/
  SECRET_KEY       = güvenlik için rastgele bir string
"""

import os, time, requests
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TV_CHART_URL     = os.getenv("TV_CHART_URL", "")
SECRET_KEY       = os.getenv("SECRET_KEY", "")

# ─── TradingView Screenshot URL ────────────────────────────────
def get_screenshot_url(symbol: str, timeframe: str) -> str | None:
    """
    TradingView'in herkese açık chart_image endpoint'ini kullanır.
    Chart URL'niz varsa oradan snapshot alır, yoksa genel bir sembol linki döner.
    """
    # Kendi chart'ınızın snapshot URL'si (chart ID'yi .env'e koyun)
    if TV_CHART_URL:
        snapshot_api = f"https://www.tradingview.com/x/snapshot/{TV_CHART_URL.rstrip('/').split('/')[-1]}/"
        try:
            r = requests.get(snapshot_api, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("url")  # PNG URL döner
        except Exception as e:
            print(f"[SCREENSHOT] Snapshot hatası: {e}")

    # Fallback: sembol bazlı mini chart PNG (public endpoint)
    tf_map = {"1": "1", "5": "5", "15": "15", "60": "1H", "240": "4H", "D": "1D", "W": "1W"}
    tv_tf  = tf_map.get(str(timeframe), timeframe)
    return f"https://www.tradingview.com/x/snapshot/{symbol}_{tv_tf}/"

# ─── Telegram Gönderici ────────────────────────────────────────
def send_telegram(signal: dict) -> bool:
    sym  = signal.get("symbol", "?")
    tf   = signal.get("timeframe", "?")
    side = signal.get("signal", "?")       # LONG / SHORT
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

    # 1) Screenshot URL al
    img_url = get_screenshot_url(sym, tf)
    base    = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

    if img_url:
        # Fotoğraf + caption gönder
        resp = requests.post(
            f"{base}/sendPhoto",
            json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "photo":      img_url,
                "caption":    caption,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
    else:
        # Sadece metin gönder
        resp = requests.post(
            f"{base}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       caption,
                "parse_mode": "HTML",
            },
            timeout=15,
        )

    if resp.status_code == 200:
        print(f"[OK] {sym} {side} sinyali Telegram'a gönderildi.")
        return True
    else:
        print(f"[HATA] Telegram yanıtı: {resp.status_code} — {resp.text}")
        return False

# ─── Webhook Endpoint ──────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    # İsteğe bağlı güvenlik kontrolü
    if SECRET_KEY:
        token = request.headers.get("X-Secret-Key", "")
        if token != SECRET_KEY:
            abort(403)

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON bekleniyor"}), 400

    print(f"[WEBHOOK] Gelen sinyal: {data}")

    # Gerekli alan kontrolü
    required = ["symbol", "signal", "price"]
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Eksik alanlar: {missing}"}), 400

    ok = send_telegram(data)
    return jsonify({"status": "ok" if ok else "error"}), 200 if ok else 500

# ─── Sağlık kontrolü ───────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "running", "time": time.strftime("%Y-%m-%d %H:%M UTC")})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Sunucu başlatılıyor → http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
