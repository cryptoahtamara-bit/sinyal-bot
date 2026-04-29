import os, time, json, re, threading, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHARTIMG_KEY     = os.getenv("CHARTIMG_KEY", "")
KANAL_ADI        = os.getenv("KANAL_ADI", "BEN KÜL YUTMAM")
KANAL_TAG        = os.getenv("KANAL_TAG", "@dayiscalper")

son_sinyal = {"key": "", "zaman": 0}

def get_screenshot_chartimg(symbol: str, timeframe: str):
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
    params = {"symbol": sym, "interval": tf, "theme": "dark", "width": 800, "height": 500}
    headers = {"x-api-key": CHARTIMG_KEY}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.content
        print(f"[SCREENSHOT] chart-img hata: {r.status_code}")
        return None
    except Exception as e:
        print(f"[SCREENSHOT] Timeout: {e}")
        return None

def get_screenshot_tv(imageurl: str):
    """TradingView {{imageurl}} — indikatörlü grafik"""
    try:
        r = requests.get(imageurl, timeout=15)
        if r.status_code == 200:
            return r.content
        print(f"[TV_IMG] Hata: {r.status_code}")
        return None
    except Exception as e:
        print(f"[TV_IMG] Timeout: {e}")
        return None

def sinyal_emoji(sinyal: str) -> str:
    s = sinyal.upper()
    if "STRONG" in s and ("BUY" in s or "LONG" in s):  return "🔥 STRONG BUY"
    if "STRONG" in s and ("SELL" in s or "SHORT" in s): return "💀 STRONG SELL"
    if "LONG" in s or "BUY" in s:                        return "🚀 LONG"
    if "SHORT" in s or "SELL" in s:                      return "📉 SHORT"
    return sinyal

def format_mesaj(symbol, price, timeframe, sinyal, tp1=None, tp2=None, tp3=None):
    tf_map = {
        "1": "1 DK", "3": "3 DK", "5": "5 DK", "15": "15 DK",
        "30": "30 DK", "60": "1 SAAT", "1H": "1 SAAT",
        "120": "2 SAAT", "240": "4 SAAT",
        "D": "1 GÜN", "1D": "1 GÜN", "W": "1 HAFTA"
    }
    tf_goster = tf_map.get(str(timeframe), timeframe)
    return (
        f"❗ {KANAL_ADI} ❗\n\n"
        f"⚡ {symbol}\n"
        f"💰 {price}\n"
        f"⏰ {tf_goster}\n"
        f"{sinyal_emoji(sinyal)}\n"
        + (f"🎯 TP1: {tp1}\n" if tp1 else "")
        + (f"🎯 TP2: {tp2}\n" if tp2 else "")
        + (f"🎯 TP3: {tp3}\n" if tp3 else "")
        + f"\nSiz de kulübe katılıp, alarmları kaçırmamak için lütfen iletişime geçin. \nİletişim: {KANAL_TAG}"
    )

def send_telegram(caption: str, symbol: str, timeframe: str, imageurl: str = None):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

    # Önce TradingView'in kendi görselini dene (indikatörlü)
    img_data = None
    if imageurl:
        print(f"[IMG] TradingView görüntüsü alınıyor...")
        img_data = get_screenshot_tv(imageurl)

    # TradingView görseli yoksa chart-img'e düş
    if not img_data:
        print(f"[IMG] chart-img'e düşüldü...")
        img_data = get_screenshot_chartimg(symbol, timeframe)

    try:
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
            print(f"[OK] {symbol} gönderildi.")
        else:
            print(f"[HATA] {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"[HATA] send_telegram: {e}")

def parse_plain(raw: str):
    symbol, timeframe, sinyal, price = "BTCUSDT", "60", "", "?"
    tp1, tp2, tp3 = None, None, None
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    for line in lines:
        u = line.upper()
        if re.match(r'^[A-Z0-9.]{3,15}$', line) and any(
            x in u for x in ["USDT","BTC","ETH","BNB","SOL","XRP","DOGE","ADA","DOT","AVAX"]
        ):
            symbol = line
            continue
        if re.match(r'^\d+[\.,]?\d*$', line):
            price = line
            continue
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
        if "STRONG BUY" in u or "STRONG_BUY" in u:    sinyal = "STRONG BUY"
        elif "STRONG SELL" in u or "STRONG_SELL" in u: sinyal = "STRONG SELL"
        elif u == "LONG":  sinyal = "LONG"
        elif u == "SHORT": sinyal = "SHORT"
        if line.startswith("TP1 "):
            tp1 = line[4:].strip()
        elif line.startswith("TP2 "):
            tp2 = line[4:].strip()
        elif line.startswith("TP3 "):
            tp3 = line[4:].strip()
    return symbol, price, timeframe, sinyal if sinyal else "SINYAL", tp1, tp2, tp3

@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True).strip()
    if not raw:
        return jsonify({"error": "Boş mesaj"}), 400

    imageurl = None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            symbol    = data.get("symbol", data.get("ticker", "BTCUSDT"))
            timeframe = str(data.get("timeframe", "60"))
            sinyal    = data.get("signal", data.get("sinyal", "SINYAL"))
            price     = str(data.get("price", "?"))
            imageurl  = data.get("imageurl", None)
            tp1 = data.get("tp1", None)
            tp2 = data.get("tp2", None)
            tp3 = data.get("tp3", None)
        else:
            raise ValueError
    except Exception:
        symbol, price, timeframe, sinyal, tp1, tp2, tp3 = parse_plain(raw)

    # Duplicate önleme
    simdi = time.time()
    anahtar = f"{symbol}_{sinyal}_{timeframe}"
    if anahtar == son_sinyal["key"] and simdi - son_sinyal["zaman"] < 10:
        print(f"[DUPLICATE] {anahtar} atlandı.")
        return jsonify({"status": "duplicate"}), 200
    son_sinyal["key"] = anahtar
    son_sinyal["zaman"] = simdi

    print(f"[SINYAL] {symbol} {sinyal} @ {price} ({timeframe}) imageurl={imageurl}")
    mesaj = format_mesaj(symbol, price, timeframe, sinyal, tp1, tp2, tp3)

    t = threading.Thread(target=send_telegram, args=(mesaj, symbol, timeframe, imageurl))
    t.daemon = True
    t.start()

    return jsonify({"status": "ok"}), 200

@app.route("/health")
def health():
    return jsonify({"status": "running", "time": time.strftime("%Y-%m-%d %H:%M UTC")})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Sunucu başlatılıyor → http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
