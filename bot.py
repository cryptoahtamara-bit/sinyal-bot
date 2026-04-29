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

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHARTIMG_KEY     = os.getenv("CHARTIMG_KEY", "")
KANAL_ADI        = os.getenv("KANAL_ADI", "BEN KÜL YUTMAM")
KANAL_TAG        = os.getenv("KANAL_TAG", "@dayiscalper")
def tp_sure(timeframe: str) -> int:
    """Timeframe'e göre TP kontrol süresi (dakika)"""
    tf = str(timeframe)
    if tf in ["1", "3"]:       return 15
    if tf in ["5"]:            return 30
    if tf in ["15"]:           return 60
    if tf in ["30"]:           return 120
    if tf in ["60", "1H"]:     return 240
    if tf in ["120"]:          return 480
    if tf in ["240"]:          return 1440
    if tf in ["D", "1D"]:      return 4320
    if tf in ["W", "1W"]:      return 10080
    return 15

son_sinyal = {"key": "", "zaman": 0}

# Günlük sinyal kaydı
gunluk_sinyaller = []
gunluk_kilit = threading.Lock()

def gun_str(ts=None):
    """TR saati ile gün string'i: 2024-04-30"""
    if TR_TZ:
        dt = datetime.fromtimestamp(ts or time.time(), tz=TR_TZ)
    else:
        dt = datetime.utcfromtimestamp(ts or time.time())
    return dt.strftime("%Y-%m-%d")

def sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, message_id):
    """Sinyali günlük kayda ekle"""
    with gunluk_kilit:
        gunluk_sinyaller.append({
            "gun": gun_str(),
            "zaman": time.time(),
            "symbol": symbol,
            "sinyal": sinyal,
            "timeframe": timeframe,
            "price": price,
            "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "tp1_ok": None, "tp2_ok": None, "tp3_ok": None,
            "message_id": message_id
        })

def tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok):
    """TP sonuçlarını güncelle"""
    with gunluk_kilit:
        for s in gunluk_sinyaller:
            if s["message_id"] == message_id:
                s["tp1_ok"] = tp1_ok
                s["tp2_ok"] = tp2_ok
                s["tp3_ok"] = tp3_ok
                break

def gunluk_ozet_gonder():
    """Her gün 12:00 ve 23:59 TR saatinde özet gönder"""
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()

            # Sonraki hedef saati bul (12:00 veya 23:59)
            hedefler = [
                simdi.replace(hour=12, minute=0, second=0, microsecond=0),
                simdi.replace(hour=23, minute=59, second=0, microsecond=0),
            ]
            # Henüz geçmemiş en yakın hedefi seç
            gelecek = [h for h in hedefler if h > simdi]
            if gelecek:
                hedef = min(gelecek)
            else:
                # İkisi de geçtiyse yarın 12:00
                import datetime as dt_mod
                yarin = simdi + dt_mod.timedelta(days=1)
                hedef = yarin.replace(hour=12, minute=0, second=0, microsecond=0)

            bekle = (hedef - simdi).total_seconds()
            print(f"[OZET] Sonraki özet: {hedef.strftime('%H:%M')} TR ({int(bekle//60)} dk sonra)")
            time.sleep(bekle)
            _ozet_gonder()
            time.sleep(70)  # Aynı dakikada tekrar tetiklenmesin
        except Exception as e:
            print(f"[OZET] Hata: {e}")
            time.sleep(60)

def _ozet_gonder():
    """Günlük özet tablosunu oluştur ve gönder"""
    bugun = gun_str()
    with gunluk_kilit:
        bugun_sinyaller = [s for s in gunluk_sinyaller if s["gun"] == bugun]
    
    if not bugun_sinyaller:
        print("[OZET] Bugün sinyal yok, özet gönderilmedi.")
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
        sin = s["sinyal"]
        
        # TP durumu
        tp_kontrol = s["tp1_ok"] is not None or s["tp2_ok"] is not None or s["tp3_ok"] is not None
        if tp_kontrol:
            tp_kontrol_yapilan += 1
            tp_gerceklesen = sum([
                1 for x in [s["tp1_ok"], s["tp2_ok"], s["tp3_ok"]]
                if x is True
            ])
            tp_toplam = sum([
                1 for x in [s["tp1"], s["tp2"], s["tp3"]]
                if x is not None
            ])
            if tp_gerceklesen > 0:
                tp_olan += 1
            tp_durum = f"{tp_gerceklesen}/{tp_toplam} TP"
        else:
            tp_durum = "⏳ Bekleniyor"
        
        satirlar.append(f"{saat} | {sym} | {sin[:8]} | {tp_durum}")

    basari = round((tp_olan / tp_kontrol_yapilan * 100), 1) if tp_kontrol_yapilan > 0 else 0

    mesaj = f"\U0001f4c5 <b>Gunluk Ozet - {bugun}</b>\n\n"
    mesaj += f"\U0001f4ca Toplam Sinyal: <b>{toplam}</b>\n"
    mesaj += f"\u2705 TP Basarili: <b>{tp_olan}</b> / {tp_kontrol_yapilan}\n"
    mesaj += f"\U0001f3af Basari Orani: <b>%{basari}</b>\n\n"
    mesaj += "<code>"
    mesaj += "Saat | Sembol | Sinyal   | Sonuc\n"
    mesaj += "-" * 38 + "\n"
    mesaj += "\n".join(satirlar)
    mesaj += "</code>"

    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        resp = requests.post(
            f"{base}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "HTML"},
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"[OZET] Günlük özet gönderildi. {toplam} sinyal.")
        else:
            print(f"[OZET] Hata: {resp.status_code}")
    except Exception as e:
        print(f"[OZET] Gönderim hatası: {e}")

    # Eski kayıtları temizle (3 günden eski)
    sinir = time.time() - 3 * 86400
    with gunluk_kilit:
        gunluk_sinyaller[:] = [s for s in gunluk_sinyaller if s["zaman"] > sinir]

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

def get_sym(symbol: str) -> str:
    return symbol.upper().replace(".P", "").replace("USDT.P", "USDT")

def get_mexc_price(symbol: str) -> float:
    """MEXC API'den güncel fiyat çek"""
    sym = get_sym(symbol)
    if not sym.endswith("USDT"):
        sym = sym + "USDT"
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={sym}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json()["price"])
    except:
        pass
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json()["price"])
    except:
        pass
    return None

def get_high_low_in_period(symbol: str, start_ts: int, end_ts: int):
    """Belirli zaman aralığındaki en yüksek ve en düşük fiyatı çek (1m mumlar)"""
    sym = get_sym(symbol)
    if not sym.endswith("USDT"):
        sym = sym + "USDT"
    
    en_yuksek = None
    en_dusuk = None
    
    # MEXC kline API
    try:
        url = "https://api.mexc.com/api/v3/klines"
        params = {
            "symbol": sym,
            "interval": "1m",
            "startTime": start_ts * 1000,
            "endTime": end_ts * 1000,
            "limit": 20
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            klines = r.json()
            if klines:
                highs = [float(k[2]) for k in klines]
                lows  = [float(k[3]) for k in klines]
                en_yuksek = max(highs)
                en_dusuk  = min(lows)
                print(f"[TP] MEXC kline OK: high={en_yuksek} low={en_dusuk}")
                return en_yuksek, en_dusuk
    except Exception as e:
        print(f"[TP] MEXC kline hata: {e}")
    
    # Binance kline API
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": sym,
            "interval": "1m",
            "startTime": start_ts * 1000,
            "endTime": end_ts * 1000,
            "limit": 20
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            klines = r.json()
            if klines:
                highs = [float(k[2]) for k in klines]
                lows  = [float(k[3]) for k in klines]
                en_yuksek = max(highs)
                en_dusuk  = min(lows)
                print(f"[TP] Binance kline OK: high={en_yuksek} low={en_dusuk}")
                return en_yuksek, en_dusuk
    except Exception as e:
        print(f"[TP] Binance kline hata: {e}")
    
    return None, None

def tp_kontrol_gonder(symbol, sinyal, tp1, tp2, tp3, message_id, dakika, sinyal_ts):
    """dakika sonra TP kontrolü yap — periyot içi high/low ile karşılaştır"""
    time.sleep(dakika * 60)

    end_ts = int(time.time())
    en_yuksek, en_dusuk = get_high_low_in_period(symbol, sinyal_ts, end_ts)

    if en_yuksek is None and en_dusuk is None:
        print(f"[TP] {symbol} kline verisi alınamadı, anlık fiyata düşülüyor")
        guncel = get_mexc_price(symbol)
        en_yuksek = guncel
        en_dusuk = guncel

    is_long  = any(x in sinyal.upper() for x in ["BUY", "LONG"])
    is_short = any(x in sinyal.upper() for x in ["SELL", "SHORT"])

    def tp_ulasti(tp_fiyat):
        if tp_fiyat is None:
            return False
        try:
            tp = float(tp_fiyat)
            if is_long  and en_yuksek is not None: return en_yuksek >= tp
            if is_short and en_dusuk  is not None: return en_dusuk  <= tp
        except:
            pass
        return False

    tp1_ok = tp_ulasti(tp1)
    tp2_ok = tp_ulasti(tp2)
    tp3_ok = tp_ulasti(tp3)

    mesaj = (
        f"📊 <b>TP Kontrol</b>\n\n"
        f"⚡ {symbol}\n\n"
    )
    if tp1:
        mesaj += f"🎯 TP1: {tp1} — {chr(9989)+' ULAŞILDI' if tp1_ok else chr(10060)+' Ulaşılmadı'}\n"
    if tp2:
        mesaj += f"🎯 TP2: {tp2} — {chr(9989)+' ULAŞILDI' if tp2_ok else chr(10060)+' Ulaşılmadı'}\n"
    if tp3:
        mesaj += f"🎯 TP3: {tp3} — {chr(9989)+' ULAŞILDI' if tp3_ok else chr(10060)+' Ulaşılmadı'}\n"

    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        resp = requests.post(
            f"{base}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": mesaj,
                "parse_mode": "HTML",
                "reply_to_message_id": message_id
            },
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"[TP] {symbol} TP kontrol gönderildi.")
        else:
            print(f"[TP] Hata: {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"[TP] Gönderim hatası: {e}")
    
    # Günlük kayda TP sonuçlarını işle
    tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok)

def send_telegram_and_schedule_tp(caption, symbol, timeframe, sinyal, tp1, tp2, tp3, imageurl=None, price=None):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    img_data = None
    if imageurl:
        img_data = get_screenshot_tv(imageurl)
    if not img_data:
        print(f"[IMG] chart-img'e düşüldü...")
        img_data = get_screenshot_chartimg(symbol, timeframe)

    message_id = None
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
            message_id = resp.json().get("result", {}).get("message_id")
            print(f"[OK] {symbol} gönderildi. message_id={message_id}")
        else:
            print(f"[HATA] {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"[HATA] send_telegram: {e}")
        return

    # Günlük kayda ekle
    if message_id:
        sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, message_id)

    # TP'ler varsa kontrol et
    if message_id and any([tp1, tp2, tp3]):
        sinyal_ts = int(time.time())
        kontrol_dk = tp_sure(timeframe)
        t = threading.Thread(
            target=tp_kontrol_gonder,
            args=(symbol, sinyal, tp1, tp2, tp3, message_id, kontrol_dk, sinyal_ts)
        )
        t.daemon = True
        t.start()
        print(f"[TP] {symbol} için {kontrol_dk} dk sonra kontrol planlandı.")

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
    tp1 = tp2 = tp3 = None
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
        imageurl = None

    # Duplicate önleme
    simdi = time.time()
    anahtar = f"{symbol}_{sinyal}_{timeframe}"
    if anahtar == son_sinyal["key"] and simdi - son_sinyal["zaman"] < 10:
        print(f"[DUPLICATE] {anahtar} atlandı.")
        return jsonify({"status": "duplicate"}), 200
    son_sinyal["key"] = anahtar
    son_sinyal["zaman"] = simdi

    print(f"[SINYAL] {symbol} {sinyal} @ {price} ({timeframe})")
    mesaj = format_mesaj(symbol, price, timeframe, sinyal, tp1, tp2, tp3)

    t = threading.Thread(
        target=send_telegram_and_schedule_tp,
        args=(mesaj, symbol, timeframe, sinyal, tp1, tp2, tp3, imageurl, price)
    )
    t.daemon = True
    t.start()

    return jsonify({"status": "ok"}), 200

@app.route("/health")
def health():
    return jsonify({"status": "running", "time": time.strftime("%Y-%m-%d %H:%M UTC")})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Günlük özet thread'i başlat
    ozet_thread = threading.Thread(target=gunluk_ozet_gonder, daemon=True)
    ozet_thread.start()
    print(f"Sunucu başlatılıyor → http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
