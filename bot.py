import os, time, json, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHARTIMG_KEY     = os.getenv("CHARTIMG_KEY", "")
KANAL_ADI        = os.getenv("KANAL_ADI", "BEN KÜL YUTMAM")
KANAL_TAG        = os.getenv("KANAL_TAG", "@dayiscalper")

# ─── chart-img.com ile screenshot ─────────────────────────────
def get_screenshot(symbol: str, timeframe: str):
    if not CHARTIMG_KEY:
        return None

    tf_map = {
        "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
        "60": "1h", "1H": "1h", "120": "2h", "240": "4h",
        "D": "1D", "1D": "1D", "W": "1W", "M": "1M"
    }
    tf = tf_map.get(str(timeframe), "1h")

    sym = symbol.upper().replace(".P", "").replace("USDT.P", "USDT")
    if not any(x in sym for x in [":", "BINANCE", "BYBIT"]):
        sym = f"BINANCE:{sym}"

    url = "https://api.chart-img.com/v1/tradingview/advanced-chart"
    params = {
        "symbol":   sym,
        "interval": tf,
        "theme":    "dark",
        "width":    800,
        "height":   500,
    }
    headers = {"x-api-key": CHARTIMG_KEY}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.content
        print(f"[SCREENSHOT] chart-img hatası: {r.status_code} — {r.text}")
        return None
    except Exception as e:
        print(f"[SCREENSHOT] İstek hatası: {e}")
        return None

# ─── Sinyal emojisi ────────────────────────────────────────────
def sinyal_emoji(sinyal: str) -> str:
    s = sinyal.upper().replace(" ", "_").replace("-", "_")
    if "STRONG_BUY" in s or "STRONG BUY" in s:
        return "🔥 STRONG BUY"
    if "STRONG_SELL" in s or "STRONG SELL" in s:
        return "💀 STRONG SELL"
    if "LONG" in s or "BUY" in s:
        return "🚀 LONG"
    if "SHORT" in s or "SELL" in s:
        return "📉 SHORT"
    return sinyal

# ─── Telegram Gönderici ────────────────────────────────────────
def send_telegram(caption: str, symbol: str, timeframe: str) -> bool:
    base     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    img_data = get_screenshot(symbol, timeframe)

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
        print(f"[OK] {symbol} sinyali gönderildi.")
        return True
    else:
        print(f"[HATA] Telegram: {resp.status_code} — {resp.text}")
        return False

# ─── Mesaj formatla ────────────────────────────────────────────
def format_mesaj(symbol, price, timeframe, sinyal):
    tf_map = {
        "1": "1 DK", "3": "3 DK", "5": "5 DK", "15": "15 DK",
        "30": "30 DK", "60": "1 SAAT", "1H": "1 SAAT",
        "120": "2 SAAT", "240": "4 SAAT", "D": "1 GÜN", "1D": "1 GÜN",
        "W": "1 HAFTA", "1W": "1 HAFTA"
    }
    tf_goster = tf_map.get(str(timeframe), timeframe)

    return (
        f"❗ {KANAL_ADI} ❗\n\n"
        f"⚡ {symbol}\n"
        f"💰 {price}\n"
        f"⏰ {tf_goster}\n"
        f"{sinyal_emoji(sinyal)}\n\n"
        f"Sizde kulübe katılıp, alarmları kaçırmamak isterseniz lütfen iletişime geçin. {KANAL_TAG}"
    )

# ─── Webhook ──────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True).strip()
    print(f"[WEBHOOK] Ham veri: {raw[:200]}")

    symbol    = "BTCUSDT"
    timeframe = "60"
    sinyal    = "SINYAL"
    price     = "?"

    # --- 1) JSON FORMAT dene ---
    parsed_json = None
    try:
        parsed_json = json.loads(raw)
    except Exception:
        # Content-Type json ama body düz metin olabilir
        pass

    if parsed_json and isinstance(parsed_json, dict):
        symbol    = parsed_json.get("symbol", parsed_json.get("ticker", symbol))
        timeframe = str(parsed_json.get("timeframe", parsed_json.get("tf", timeframe)))
        sinyal    = parsed_json.get("signal", parsed_json.get("sinyal", sinyal))
        price     = str(parsed_json.get("price", parsed_json.get("fiyat", price)))
        print(f"[WEBHOOK] JSON sinyal: {symbol} {sinyal} @ {price}")
        mesaj = format_mesaj(symbol, price, timeframe, sinyal)

    # --- 2) PLAIN TEXT FORMAT (Pine Script alert() mesajı) ---
    else:
        if not raw:
            return jsonify({"error": "Boş mesaj"}), 400

        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        print(f"[WEBHOOK] Plain text satırlar: {lines}")

        for line in lines:
            # Sembol: büyük harf + USDT içeren satır
            if line.isupper() and len(line) > 3 and any(c.isalpha() for c in line) and "USDT" in line:
                symbol = line
            # Fiyat: sadece rakam ve nokta
            elif line.replace(".", "").replace(",", "").isdigit():
                price = line
            # Timeframe
            elif any(x in line for x in ["DK", "SAAT", "GUN", "HAFTA"]):
                tf_raw = line.upper()
                if "1 DK" in tf_raw:     timeframe = "1"
                elif "3 DK" in tf_raw:   timeframe = "3"
                elif "5 DK" in tf_raw:   timeframe = "5"
                elif "15 DK" in tf_raw:  timeframe = "15"
                elif "30 DK" in tf_raw:  timeframe = "30"
                elif "1 SAAT" in tf_raw: timeframe = "60"
                elif "2 SAAT" in tf_raw: timeframe = "120"
                elif "4 SAAT" in tf_raw: timeframe = "240"
                elif "1 GUN" in tf_raw:  timeframe = "D"
                elif "1 HAFTA" in tf_raw: timeframe = "W"
            # Sinyal tipi
            elif any(x in line.upper() for x in ["STRONG BUY", "STRONG SELL", "LONG", "SHORT", "BUY", "SELL"]):
                sinyal = line

        print(f"[WEBHOOK] Plain text parse: {symbol} {sinyal} @ {price} ({timeframe})")
        mesaj = format_mesaj(symbol, price, timeframe, sinyal)

    ok = send_telegram(mesaj, symbol, timeframe)
    return jsonify({"status": "ok" if ok else "error"}), 200 if ok else 500

# ─── Sağlık kontrolü ──────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "running", "time": time.strftime("%Y-%m-%d %H:%M UTC")})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Sunucu başlatılıyor → http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
