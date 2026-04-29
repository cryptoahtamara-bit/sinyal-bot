import os, time, json, re, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHARTIMG_KEY     = os.getenv("CHARTIMG_KEY", "")
KANAL_ADI        = os.getenv("KANAL_ADI", "BEN KÜL YUTMAM")
KANAL_TAG        = os.getenv("KANAL_TAG", "@dayiscalper")

# Son gönderilen sinyali takip et (duplicate önleme)
son_sinyal = {"key": "", "zaman": 0}

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
    if not any(x in sym for x in [":", "BINANCE", "BYBIT", "MEXC"]):
        sym = f"MEXC:{sym}"

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
    s = sinyal.upper()
    if "STRONG" in s and ("BUY" in s or "LONG" in s):
        return "🔥 STRONG BUY"
    if "STRONG" in s and ("SELL" in s or "SHORT" in s):
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
        "120": "2 SAAT", "240": "4 SAAT",
        "D": "1 GÜN", "1D": "1 GÜN",
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

# ─── Plain text parse ─────────────────────────────────────────
def parse_plain(raw: str):
    symbol    = "BTCUSDT"
    timeframe = "60"
    sinyal    = ""
    price     = "?"

    lines = [l.strip() for l in raw.split("\n") if l.strip()]

    for line in lines:
        u = line.upper()

        # Sembol
        if re.match(r'^[A-Z0-9]{3,12}$', line.replace(".P", "")) and any(
            x in line.upper() for x in ["USDT","BTC","ETH","BNB","SOL","XRP","DOGE","ADA","DOT","AVAX"]
        ):
            symbol = line
            continue

        # Fiyat
        if re.match(r'^\d+[\.,]?\d*$', line):
            price = line
            continue

        # Timeframe
        if "1 DK" in u:      timeframe = "1"
        elif "3 DK" in u:    timeframe = "3"
        elif "5 DK" in u:    timeframe = "5"
        elif "15 DK" in u:   timeframe = "15"
        elif "30 DK" in u:   timeframe = "30"
        elif "1 SAAT" in u:  timeframe = "60"
        elif "2 SAAT" in u:  timeframe = "120"
        elif "4 SAAT" in u:  timeframe = "240"
        elif "1 GUN" in u:   timeframe = "D"
        elif "1 HAFTA" in u: timeframe = "W"

        # Sinyal
        if "STRONG BUY" in u or "STRONG_BUY" in u:
            sinyal = "STRONG BUY"
        elif "STRONG SELL" in u or "STRONG_SELL" in u:
            sinyal = "STRONG SELL"
        elif u == "LONG":
            sinyal = "LONG"
        elif u == "SHORT":
            sinyal = "SHORT"

    return symbol, price, timeframe, sinyal if sinyal else "SINYAL"

# ─── Webhook ──────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True).strip()

    if not raw:
        return jsonify({"error": "Boş mesaj"}), 400

    # JSON dene
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            symbol    = data.get("symbol", data.get("ticker", "BTCUSDT"))
            timeframe = str(data.get("timeframe", data.get("tf", "60")))
            sinyal    = data.get("signal", data.get("sinyal", "SINYAL"))
            price     = str(data.get("price", data.get("fiyat", "?")))
    except Exception:
        symbol, price, timeframe, sinyal = parse_plain(raw)

    # Duplicate önleme — aynı sembol+sinyal 10 saniye içinde tekrar gelirse atla
    simdi = time.time()
    anahtar = f"{symbol}_{sinyal}_{timeframe}"
    if anahtar == son_sinyal["key"] and simdi - son_sinyal["zaman"] < 10:
        print(f"[DUPLICATE] {anahtar} atlandı.")
        return jsonify({"status": "duplicate"}), 200
    son_sinyal["key"] = anahtar
    son_sinyal["zaman"] = simdi

    print(f"[SINYAL] {symbol} {sinyal} @ {price} ({timeframe})")
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
