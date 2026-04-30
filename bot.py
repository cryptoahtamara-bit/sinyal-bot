import os, time, json, re, threading, requests
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
try:
    import pytz
    TR_TZ = pytz.timezone("Europe/Istanbul")
except:
    TR_TZ = None

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_LOG_ID   = os.getenv("TELEGRAM_LOG_ID", "")   # Madde 12: TP log kanalı
CHARTIMG_KEY      = os.getenv("CHARTIMG_KEY", "")
KANAL_ADI         = os.getenv("KANAL_ADI", "BEN KÜL YUTMAM")
KANAL_TAG         = os.getenv("KANAL_TAG", "@dayiscalper")

def tp_sure(timeframe: str) -> int:
    tf = str(timeframe)
    if tf in ["1", "3"]:        return 30
    if tf in ["5"]:             return 60
    if tf in ["15"]:            return 240
    if tf in ["30"]:            return 1440
    if tf in ["60", "1H"]:      return 10080
    if tf in ["240", "4H"]:     return 20160
    if tf in ["D", "1D"]:       return 43200
    if tf in ["W", "1W"]:       return 172800
    return 30

son_sinyal = {"key": "", "zaman": 0}
gunluk_sinyaller = []
gunluk_kilit = threading.Lock()

def gun_str(ts=None):
    if TR_TZ:
        dt = datetime.fromtimestamp(ts or time.time(), tz=TR_TZ)
    else:
        dt = datetime.utcfromtimestamp(ts or time.time())
    return dt.strftime("%Y-%m-%d")

def sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, message_id):
    with gunluk_kilit:
        gunluk_sinyaller.append({
            "gun": gun_str(), "zaman": time.time(),
            "symbol": symbol, "sinyal": sinyal,
            "timeframe": timeframe, "price": price,
            "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "tp1_ok": None, "tp2_ok": None, "tp3_ok": None,
            "message_id": message_id
        })

def tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok):
    with gunluk_kilit:
        for s in gunluk_sinyaller:
            if s["message_id"] == message_id:
                s["tp1_ok"] = tp1_ok
                s["tp2_ok"] = tp2_ok
                s["tp3_ok"] = tp3_ok
                break

def gunluk_ozet_gonder():
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()
            hedefler = [
                simdi.replace(hour=12, minute=0, second=0, microsecond=0),
                simdi.replace(hour=23, minute=59, second=0, microsecond=0),
            ]
            gelecek = [h for h in hedefler if h > simdi]
            if gelecek:
                hedef = min(gelecek)
            else:
                import datetime as dt_mod
                yarin = simdi + dt_mod.timedelta(days=1)
                hedef = yarin.replace(hour=12, minute=0, second=0, microsecond=0)
            bekle = (hedef - simdi).total_seconds()
            print(f"[OZET] Sonraki ozet: {hedef.strftime('%H:%M')} TR ({int(bekle//60)} dk sonra)")
            time.sleep(bekle)
            _ozet_gonder()
            time.sleep(70)
        except Exception as e:
            print(f"[OZET] Hata: {e}")
            time.sleep(60)

def _ozet_gonder():
    bugun = gun_str()
    with gunluk_kilit:
        bugun_sinyaller = [s for s in gunluk_sinyaller if s["gun"] == bugun]
    if not bugun_sinyaller:
        print("[OZET] Bugun sinyal yok.")
        return
    toplam = len(bugun_sinyaller)
    tp_olan = 0
    tp_kontrol_yapilan = 0
    satirlar = []
    for s in bugun_sinyaller:
        if TR_TZ:
            dt = datetime.fromtimestamp(s["zaman"], tz=TR_TZ)
        else:
            dt = datetime.utcfromtimestamp(s["zaman"])
        saat = dt.strftime("%H:%M")
        sym = s["symbol"].replace("USDT.P","").replace("USDT","")
        tp_kontrol = s["tp1_ok"] is not None or s["tp2_ok"] is not None or s["tp3_ok"] is not None
        if tp_kontrol:
            tp_kontrol_yapilan += 1
            tp_gerceklesen = sum([1 for x in [s["tp1_ok"], s["tp2_ok"], s["tp3_ok"]] if x is True])
            tp_toplam = sum([1 for x in [s["tp1"], s["tp2"], s["tp3"]] if x is not None])
            if tp_gerceklesen > 0:
                tp_olan += 1
            tp_durum = f"{tp_gerceklesen}/{tp_toplam} TP"
        else:
            tp_durum = "bekleniyor"
        satirlar.append(f"{saat} | {sym} | {s['sinyal'][:8]} | {tp_durum}")
    basari = round((tp_olan / tp_kontrol_yapilan * 100), 1) if tp_kontrol_yapilan > 0 else 0
    mesaj = f"<b>Gunluk Ozet - {bugun}</b>\n\nToplam Sinyal: <b>{toplam}</b>\nTP Basarili: <b>{tp_olan}</b> / {tp_kontrol_yapilan}\nBasari Orani: <b>%{basari}</b>\n\n<code>Saat | Sembol   | Sinyal   | Sonuc\n" + "-"*38 + "\n" + "\n".join(satirlar) + "</code>"
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        resp = requests.post(f"{base}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "HTML"}, timeout=15)
        if resp.status_code == 200:
            print(f"[OZET] Gonderildi. {toplam} sinyal.")
        else:
            print(f"[OZET] Hata: {resp.status_code}")
    except Exception as e:
        print(f"[OZET] Hata: {e}")
    sinir = time.time() - 3 * 86400
    with gunluk_kilit:
        gunluk_sinyaller[:] = [s for s in gunluk_sinyaller if s["zaman"] > sinir]

# Madde 4: Dinamik fiyat formatı (50 altı 4 hane, 1 altı 6 hane, 50 üstü 2 hane)
def fmt_fiyat(val):
    if val is None:
        return None
    try:
        f = float(str(val).replace(",", "."))
        if f >= 50:
            return f"{f:.2f}"
        elif f >= 1:
            return f"{f:.4f}"
        else:
            return f"{f:.6f}"
    except:
        return str(val)

fmt_tp = fmt_fiyat

# Madde 7: MEXC chart
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
    try:
        r = requests.get(imageurl, timeout=15)
        if r.status_code == 200:
            return r.content
        return None
    except:
        return None

# Madde 8: Sinyal emoji
def sinyal_emoji(sinyal: str) -> str:
    s = sinyal.upper()
    if "STRONG" in s and ("BUY" in s or "LONG" in s):   return "🔥 STRONG BUY"
    if "STRONG" in s and ("SELL" in s or "SHORT" in s):  return "💀 STRONG SELL"
    if "LONG" in s or "BUY" in s:                         return "🚀 LONG"
    if "SHORT" in s or "SELL" in s:                       return "📉 SHORT"
    return sinyal

# Madde 8: Mesaj formatı
def format_mesaj(symbol, price, timeframe, sinyal, tp1=None, tp2=None, tp3=None, sl=None):
    tf_map = {
        "1": "1 DK", "3": "3 DK", "5": "5 DK", "15": "15 DK",
        "30": "30 DK", "60": "1 SAAT", "1H": "1 SAAT",
        "120": "2 SAAT", "240": "4 SAAT",
        "D": "1 GUN", "1D": "1 GUN", "W": "1 HAFTA"
    }
    tf_goster = tf_map.get(str(timeframe), timeframe)
    price_fmt = fmt_fiyat(price)
    sl_fmt    = fmt_fiyat(sl)
    tp1_fmt   = fmt_tp(tp1)
    tp2_fmt   = fmt_tp(tp2)
    tp3_fmt   = fmt_tp(tp3)
    msg = (
        f"❗ {KANAL_ADI} ❗\n\n"
        f"⚡ {symbol}\n"
        f"{sinyal_emoji(sinyal)}\n"
        f"⏰ {tf_goster}\n"
        f"\n💰 Giris: {price_fmt}\n"
    )
    if sl_fmt:
        msg += f"🚪 Cikis: {sl_fmt}\n"
    if tp1_fmt:
        msg += f"\n🎯 TP1: {tp1_fmt}\n"
    if tp2_fmt:
        msg += f"🎯 TP2: {tp2_fmt}\n"
    if tp3_fmt:
        msg += f"🎯 TP3: {tp3_fmt}\n"
    msg += f"\nSiz de kulube katilip, alarmlari kacirmamak icin lutfen iletisime gecin.\nIletisim: {KANAL_TAG}"
    return msg

def get_sym(symbol: str) -> str:
    return symbol.upper().replace(".P", "").replace("USDT.P", "USDT")

def get_mexc_price(symbol: str) -> float:
    sym = get_sym(symbol)
    if not sym.endswith("USDT"):
        sym = sym + "USDT"
    for api_url in [
        f"https://api.mexc.com/api/v3/ticker/price?symbol={sym}",
        f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
    ]:
        try:
            r = requests.get(api_url, timeout=10)
            if r.status_code == 200:
                return float(r.json()["price"])
        except:
            pass
    return None

def get_high_low_in_period(symbol: str, start_ts: int, end_ts: int):
    sym = get_sym(symbol)
    if not sym.endswith("USDT"):
        sym = sym + "USDT"
    for api_url in [
        "https://api.mexc.com/api/v3/klines",
        "https://api.binance.com/api/v3/klines"
    ]:
        try:
            params = {
                "symbol": sym, "interval": "1m",
                "startTime": start_ts * 1000,
                "endTime": end_ts * 1000,
                "limit": 1500
            }
            r = requests.get(api_url, params=params, timeout=10)
            if r.status_code == 200:
                klines = r.json()
                if klines:
                    highs = [float(k[2]) for k in klines]
                    lows  = [float(k[3]) for k in klines]
                    return max(highs), min(lows)
        except Exception as e:
            print(f"[TP] kline hata ({api_url}): {e}")
    return None, None

# Madde 5 + 12: TP kontrol
def tp_kontrol_gonder(symbol, sinyal, tp1, tp2, tp3, message_id, dakika, sinyal_ts, sinyal_fiyat=None):
    time.sleep(dakika * 60)
    end_ts = int(time.time())
    en_yuksek, en_dusuk = get_high_low_in_period(symbol, sinyal_ts, end_ts)
    if en_yuksek is None and en_dusuk is None:
        guncel = get_mexc_price(symbol)
        en_yuksek = guncel
        en_dusuk = guncel

    is_long  = any(x in sinyal.upper() for x in ["BUY", "LONG"])
    is_short = any(x in sinyal.upper() for x in ["SELL", "SHORT"])

    def tp_ulasti(tp_fiyat):
        if tp_fiyat is None:
            return False
        try:
            tp = float(str(tp_fiyat).replace(",", "."))
            if is_long  and en_yuksek is not None: return en_yuksek >= tp
            if is_short and en_dusuk  is not None: return en_dusuk  <= tp
        except:
            pass
        return False

    tp1_ok = tp_ulasti(tp1)
    tp2_ok = tp_ulasti(tp2)
    tp3_ok = tp_ulasti(tp3)

    # Madde 5: fiyat ve sinyal adı
    fiyat_str = fmt_fiyat(sinyal_fiyat) if sinyal_fiyat else ""
    sinyal_etiket = sinyal_emoji(sinyal)

    mesaj = (
        f"<b>TP Kontrol</b>\n\n"
        f"⚡ {symbol}"
        + (f" | 💰 {fiyat_str}" if fiyat_str else "")
        + f" | {sinyal_etiket}\n\n"
    )
    if tp1:
        mesaj += f"🎯 TP1: {fmt_tp(tp1)} — {'✅ ULASILDI' if tp1_ok else '❌ Ulasilmadi'}\n"
    if tp2:
        mesaj += f"🎯 TP2: {fmt_tp(tp2)} — {'✅ ULASILDI' if tp2_ok else '❌ Ulasilmadi'}\n"
    if tp3:
        mesaj += f"🎯 TP3: {fmt_tp(tp3)} — {'✅ ULASILDI' if tp3_ok else '❌ Ulasilmadi'}\n"

    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

    # Ana kanala gönder
    try:
        resp = requests.post(f"{base}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "HTML",
                  "reply_to_message_id": message_id}, timeout=15)
        if resp.status_code == 200:
            print(f"[TP] {symbol} TP kontrol gonderildi.")
        else:
            print(f"[TP] Hata: {resp.status_code}")
    except Exception as e:
        print(f"[TP] Hata: {e}")

    # Madde 12: Log kanalına gönder
    if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
        try:
            requests.post(f"{base}/sendMessage",
                json={"chat_id": TELEGRAM_LOG_ID, "text": mesaj, "parse_mode": "HTML"}, timeout=15)
            print(f"[LOG] {symbol} log kanalina gonderildi.")
        except Exception as e:
            print(f"[LOG] Hata: {e}")

    tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok)

def send_telegram_and_schedule_tp(caption, symbol, timeframe, sinyal, tp1, tp2, tp3, imageurl=None, price=None):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    img_data = None
    if imageurl:
        img_data = get_screenshot_tv(imageurl)
    if not img_data:
        img_data = get_screenshot_chartimg(symbol, timeframe)

    message_id = None
    try:
        if img_data:
            resp = requests.post(f"{base}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("chart.png", img_data, "image/png")}, timeout=30)
        else:
            resp = requests.post(f"{base}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}, timeout=15)
        if resp.status_code == 200:
            message_id = resp.json().get("result", {}).get("message_id")
            print(f"[OK] {symbol} gonderildi. message_id={message_id}")
        else:
            print(f"[HATA] {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"[HATA] send_telegram: {e}")
        return

    # Madde 12: Sinyali log kanalına da kaydet
    if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
        try:
            requests.post(f"{base}/sendMessage",
                json={"chat_id": TELEGRAM_LOG_ID, "text": caption, "parse_mode": "HTML"}, timeout=15)
        except:
            pass

    if message_id:
        sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, message_id)

    if message_id and any([tp1, tp2, tp3]):
        sinyal_ts = int(time.time())
        kontrol_dk = tp_sure(timeframe)
        t = threading.Thread(
            target=tp_kontrol_gonder,
            args=(symbol, sinyal, tp1, tp2, tp3, message_id, kontrol_dk, sinyal_ts, price))
        t.daemon = True
        t.start()
        print(f"[TP] {symbol} icin {kontrol_dk} dk sonra kontrol planlanadi.")

def parse_plain(raw: str):
    symbol, timeframe, sinyal, price = "BTCUSDT", "60", "", "?"
    tp1, tp2, tp3, sl = None, None, None, None
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
        elif line.startswith("Cikis: ") or line.startswith("Cikis:"):
            sl = line.split(": ", 1)[1].strip() if ": " in line else line[7:].strip()
        elif line.startswith("Giris: ") or line.startswith("Giris:"):
            price = line.split(": ", 1)[1].strip() if ": " in line else line[7:].strip()
    return symbol, price, timeframe, sinyal if sinyal else "SINYAL", tp1, tp2, tp3, sl

@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True).strip()
    if not raw:
        return jsonify({"error": "Bos mesaj"}), 400

    imageurl = None
    tp1 = tp2 = tp3 = sl = None
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
            sl  = data.get("sl", data.get("cikis", None))
        else:
            raise ValueError
    except Exception:
        symbol, price, timeframe, sinyal, tp1, tp2, tp3, sl = parse_plain(raw)
        imageurl = None

    # Duplicate önleme (10 sn)
    simdi = time.time()
    anahtar = f"{symbol}_{sinyal}_{timeframe}"
    if anahtar == son_sinyal["key"] and simdi - son_sinyal["zaman"] < 10:
        print(f"[DUPLICATE] {anahtar} atlandi.")
        return jsonify({"status": "duplicate"}), 200
    son_sinyal["key"] = anahtar
    son_sinyal["zaman"] = simdi

    print(f"[SINYAL] {symbol} {sinyal} @ {price} ({timeframe})")
    mesaj = format_mesaj(symbol, price, timeframe, sinyal, tp1, tp2, tp3, sl)

    t = threading.Thread(
        target=send_telegram_and_schedule_tp,
        args=(mesaj, symbol, timeframe, sinyal, tp1, tp2, tp3, imageurl, price))
    t.daemon = True
    t.start()

    return jsonify({"status": "ok"}), 200

@app.route("/health")
def health():
    return jsonify({"status": "running", "time": time.strftime("%Y-%m-%d %H:%M UTC")})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    ozet_thread = threading.Thread(target=gunluk_ozet_gonder, daemon=True)
    ozet_thread.start()
    print(f"Sunucu baslatiliyor -> http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
