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
TELEGRAM_LOG_ID  = os.getenv("TELEGRAM_LOG_ID", "")
CHARTIMG_KEY     = os.getenv("CHARTIMG_KEY", "")
KANAL_ADI        = os.getenv("KANAL_ADI", "BEN KÜL YUTMAM")
KANAL_TAG        = os.getenv("KANAL_TAG", "@dayiscalper")

# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================

def tp_sure(timeframe: str) -> int:
    tf = str(timeframe)
    if tf in ["1", "3"]:       return 30
    if tf in ["5"]:            return 60
    if tf in ["15"]:           return 240
    if tf in ["30"]:           return 1440
    if tf in ["60", "1H"]:     return 10080
    if tf in ["240", "4H"]:    return 20160
    if tf in ["D", "1D"]:      return 43200
    if tf in ["W", "1W"]:      return 172800
    return 30

def gun_str(ts=None):
    if TR_TZ:
        dt = datetime.fromtimestamp(ts or time.time(), tz=TR_TZ)
    else:
        dt = datetime.utcfromtimestamp(ts or time.time())
    return dt.strftime("%Y-%m-%d")

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

def sinyal_emoji(sinyal: str) -> str:
    s = sinyal.upper()
    if "STRONG" in s and ("BUY" in s or "LONG" in s):  return "🔥 STRONG BUY"
    if "STRONG" in s and ("SELL" in s or "SHORT" in s): return "💀 STRONG SELL"
    if "LONG" in s or "BUY" in s:                        return "🚀 LONG"
    if "SHORT" in s or "SELL" in s:                      return "📉 SHORT"
    return sinyal

def get_sym(symbol: str) -> str:
    return symbol.upper().replace(".P", "").replace("USDT.P", "USDT")

# ==========================================
# VERİ DEPOSU
# ==========================================

son_sinyal       = {"key": "", "zaman": 0}
gunluk_sinyaller = []
gunluk_kilit     = threading.Lock()
LOG_MAGIC        = "#SINYAL_LOG#"


def sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, sl, message_id):
    kayit = {
        "gun": gun_str(), "zaman": time.time(),
        "symbol": symbol, "sinyal": sinyal,
        "timeframe": timeframe, "price": price,
        "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl,
        "tp1_ok": None, "tp2_ok": None, "tp3_ok": None,
        "sl_ok": None,
        "message_id": message_id
    }
    with gunluk_kilit:
        gunluk_sinyaller.append(kayit)
    if TELEGRAM_LOG_ID:
        log_satir = LOG_MAGIC + json.dumps(kayit, ensure_ascii=False)
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, log_satir)

def sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, sl, message_id):
    kayit = {
        "gun": gun_str(), "zaman": time.time(),
        "symbol": symbol, "sinyal": sinyal,
        "timeframe": timeframe, "price": price,
        "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl,
        "tp1_ok": None, "tp2_ok": None, "tp3_ok": None,
        "sl_ok": None,
        "message_id": message_id
    }
    with gunluk_kilit:
        gunluk_sinyaller.append(kayit)

    dosyaya_kaydet()  # ← BU SATIRI EKLEYİN

    if TELEGRAM_LOG_ID:
        log_satir = LOG_MAGIC + json.dumps(kayit, ensure_ascii=False)
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, log_satir)

def tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok, sl_ok):
    with gunluk_kilit:
        for s in gunluk_sinyaller:
            if s["message_id"] == message_id:
                s["tp1_ok"] = tp1_ok
                s["tp2_ok"] = tp2_ok
                s["tp3_ok"] = tp3_ok
                s["sl_ok"]  = sl_ok
                break


# ==========================================
# TELEGRAM GÖNDERİCİLER
# ==========================================

def _telegram_mesaj_gonder(chat_id, metin, reply_to=None, parse_mode="HTML"):
    base    = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    payload = {"chat_id": chat_id, "text": metin, "parse_mode": parse_mode}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        r = requests.post(f"{base}/sendMessage", json=payload, timeout=15)
        return r
    except Exception as e:
        print(f"[TELEGRAM] Mesaj gonderme hatasi: {e}")
        return None


def _telegram_foto_gonder(chat_id, img_data, caption, parse_mode="HTML"):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        r = requests.post(f"{base}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption, "parse_mode": parse_mode},
            files={"photo": ("chart.png", img_data, "image/png")}, timeout=30)
        return r
    except Exception as e:
        print(f"[TELEGRAM] Foto gonderme hatasi: {e}")
        return None


# ==========================================
# CHART SCREENSHOT
# ==========================================

def get_screenshot_chartimg(symbol: str, timeframe: str):
    if not CHARTIMG_KEY:
        return None
    tf_map = {
        "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
        "60": "1h", "1H": "1h", "120": "2h", "240": "4h",
        "D": "1D", "1D": "1D", "W": "1W", "M": "1M"
    }
    tf  = tf_map.get(str(timeframe), "1h")
    sym = symbol.upper().replace(".P", "").replace("USDT.P", "USDT")
    if not any(x in sym for x in [":", "BINANCE", "BYBIT", "MEXC"]):
        sym = f"MEXC:{sym}"
    url     = "https://api.chart-img.com/v1/tradingview/advanced-chart"
    params  = {"symbol": sym, "interval": tf, "theme": "dark", "width": 800, "height": 500}
    headers = {"x-api-key": CHARTIMG_KEY}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.content
        print(f"[SCREENSHOT] chart-img hata: {r.status_code}")
    except Exception as e:
        print(f"[SCREENSHOT] Timeout: {e}")
    return None


def get_screenshot_tv(imageurl: str):
    try:
        r = requests.get(imageurl, timeout=15)
        if r.status_code == 200:
            return r.content
    except:
        pass
    return None


# ==========================================
# MESAJ FORMATI
# ==========================================

def format_mesaj(symbol, price, timeframe, sinyal, tp1=None, tp2=None, tp3=None, sl=None):
    tf_map = {
        "1": "1 DK", "3": "3 DK", "5": "5 DK", "15": "15 DK",
        "30": "30 DK", "60": "1 SAAT", "1H": "1 SAAT",
        "120": "2 SAAT", "240": "4 SAAT",
        "D": "1 GUN", "1D": "1 GUN", "W": "1 HAFTA"
    }
    tf_goster = tf_map.get(str(timeframe), timeframe)
    msg = (
        f"❗ {KANAL_ADI} ❗\n\n"
        f"⚡ {symbol}\n"
        f"{sinyal_emoji(sinyal)}\n"
        f"⏰ {tf_goster}\n"
        f"\n💰 Giris (Entry): {fmt_fiyat(price)}\n"
    )
    if sl:
        msg += f"🚪 Cikis (SL): {fmt_fiyat(sl)}\n"
    if tp1:
        msg += f"\n🎯 TP1: {fmt_tp(tp1)}\n"
    if tp2:
        msg += f"🎯 TP2: {fmt_tp(tp2)}\n"
    if tp3:
        msg += f"🎯 TP3: {fmt_tp(tp3)}\n"
    msg += f"\nSiz de kulube katilip, alarmlari kacirmamak icin lutfen iletisime gecin.\nIletisim: {KANAL_TAG}"
    return msg


# ==========================================
# FİYAT VERİSİ
# ==========================================

def get_mexc_price(symbol: str) -> float:
    sym = get_sym(symbol)
    if not sym.endswith("USDT"):
        sym += "USDT"
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
        sym += "USDT"
    for api_url in ["https://api.mexc.com/api/v3/klines", "https://api.binance.com/api/v3/klines"]:
        try:
            params = {
                "symbol": sym, "interval": "1m",
                "startTime": start_ts * 1000,
                "endTime":   end_ts   * 1000,
                "limit": 1500
            }
            r = requests.get(api_url, params=params, timeout=10)
            if r.status_code == 200:
                klines = r.json()
                if klines:
                    return max(float(k[2]) for k in klines), min(float(k[3]) for k in klines)
        except Exception as e:
            print(f"[TP] kline hata ({api_url}): {e}")
    return None, None


# ==========================================
# TP + SL KONTROL
# ==========================================

def tp_kontrol_gonder(symbol, sinyal, tp1, tp2, tp3, sl, message_id, dakika, sinyal_ts, sinyal_fiyat=None):
    is_long  = any(x in sinyal.upper() for x in ["BUY", "LONG"])
    is_short = any(x in sinyal.upper() for x in ["SELL", "SHORT"])

    def tp_ulasti(tp_fiyat, yuksek, dusuk):
        if tp_fiyat is None: return False
        try:
            tp = float(str(tp_fiyat).replace(",", "."))
            if is_long:  return yuksek >= tp
            if is_short: return dusuk  <= tp
        except: pass
        return False

    def sl_tetiklendi(sl_fiyat, yuksek, dusuk):
        if sl_fiyat is None: return False
        try:
            s = float(str(sl_fiyat).replace(",", "."))
            if is_long:  return dusuk  <= s
            if is_short: return yuksek >= s
        except: pass
        return False

    def mesaj_olustur(tp1_ok, tp2_ok, tp3_ok, sl_ok, erken=False):
        fiyat_str     = fmt_fiyat(sinyal_fiyat) if sinyal_fiyat else ""
        sinyal_etiket = sinyal_emoji(sinyal)
        baslik = "⚡ <b>Erken TP/SL Bildirimi</b>" if erken else "<b>TP ve SL Kontrol</b>"
        msg = (
            f"{baslik}\n\n"
            f"⚡ {symbol}"
            + (f" | 💰 {fiyat_str}" if fiyat_str else "")
            + f" | {sinyal_etiket}\n\n"
        )
        if tp1: msg += f"🎯 TP1: {fmt_tp(tp1)} — {'✅ ULASILDI' if tp1_ok else '❌ Ulasilmadi'}\n"
        if tp2: msg += f"🎯 TP2: {fmt_tp(tp2)} — {'✅ ULASILDI' if tp2_ok else '❌ Ulasilmadi'}\n"
        if tp3: msg += f"🎯 TP3: {fmt_tp(tp3)} — {'✅ ULASILDI' if tp3_ok else '❌ Ulasilmadi'}\n"
        if sl:  msg += f"🚪 SL:  {fmt_fiyat(sl)} — {'⛔ TETİKLENDİ' if sl_ok else '— Bekleniyor'}\n"
        return msg

    def bildirim_gonder(msg):
        resp = _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, msg, reply_to=message_id)
        if resp and resp.status_code == 200:
            print(f"[TP] {symbol} bildirim gonderildi.")
        if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
            _telegram_mesaj_gonder(TELEGRAM_LOG_ID, msg)

    # Her dakika kontrol et, TP veya SL tetiklenirse hemen bildir
    kontrol_araligi           = 60
    toplam_sure               = dakika * 60
    gecen_sure                = 0
    erken_bildirim_gonderildi = False

    while gecen_sure < toplam_sure:
        time.sleep(kontrol_araligi)
        gecen_sure += kontrol_araligi

        end_ts        = int(time.time())
        yuksek, dusuk = get_high_low_in_period(symbol, sinyal_ts, end_ts)
        if yuksek is None:
            continue

        tp1_ok = tp_ulasti(tp1, yuksek, dusuk)
        tp2_ok = tp_ulasti(tp2, yuksek, dusuk)
        tp3_ok = tp_ulasti(tp3, yuksek, dusuk)
        sl_ok  = sl_tetiklendi(sl, yuksek, dusuk)

        if (any([tp1_ok, tp2_ok, tp3_ok]) or sl_ok) and not erken_bildirim_gonderildi:
            msg = mesaj_olustur(tp1_ok, tp2_ok, tp3_ok, sl_ok, erken=True)
            bildirim_gonder(msg)
            erken_bildirim_gonderildi = True

            if sl_ok:
                sl_mesaj = (
                    f"⛔ <b>SL TETİKLENDİ</b>\n\n"
                    f"⚡ {symbol} | {sinyal_emoji(sinyal)}\n"
                    f"🚪 SL Seviyesi: {fmt_fiyat(sl)}"
                )
                bildirim_gonder(sl_mesaj)

            tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok, sl_ok)
            return

    # Süre doldu, final kontrol
    end_ts        = int(time.time())
    yuksek, dusuk = get_high_low_in_period(symbol, sinyal_ts, end_ts)
    if yuksek is None:
        guncel = get_mexc_price(symbol)
        yuksek = dusuk = guncel

    tp1_ok = tp_ulasti(tp1, yuksek, dusuk)
    tp2_ok = tp_ulasti(tp2, yuksek, dusuk)
    tp3_ok = tp_ulasti(tp3, yuksek, dusuk)
    sl_ok  = sl_tetiklendi(sl, yuksek, dusuk)

    if not erken_bildirim_gonderildi:
        msg = mesaj_olustur(tp1_ok, tp2_ok, tp3_ok, sl_ok, erken=False)
        bildirim_gonder(msg)

    tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok, sl_ok)


# ==========================================
# SINYAL GÖNDER + TP PLANLA
# ==========================================

def send_telegram_and_schedule_tp(caption, symbol, timeframe, sinyal, tp1, tp2, tp3, sl, imageurl=None, price=None):
    img_data = None
    if imageurl:
        img_data = get_screenshot_tv(imageurl)
    if not img_data:
        img_data = get_screenshot_chartimg(symbol, timeframe)

    message_id = None
    if img_data:
        resp = _telegram_foto_gonder(TELEGRAM_CHAT_ID, img_data, caption)
    else:
        resp = _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, caption)

    if resp and resp.status_code == 200:
        message_id = resp.json().get("result", {}).get("message_id")
        print(f"[OK] {symbol} gonderildi. message_id={message_id}")
    else:
        print(f"[HATA] {resp.status_code if resp else 'baglanti yok'}")
        return

    if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, caption)

    if message_id:
        sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, sl, message_id)

    if message_id and any([tp1, tp2, tp3]):
        sinyal_ts  = int(time.time())
        kontrol_dk = tp_sure(timeframe)
        t = threading.Thread(
            target=tp_kontrol_gonder,
            args=(symbol, sinyal, tp1, tp2, tp3, sl, message_id, kontrol_dk, sinyal_ts, price))
        t.daemon = True
        t.start()
        print(f"[TP] {symbol} icin {kontrol_dk} dk sonra kontrol planlanadi.")


# ==========================================
# İSTATİSTİK
# ==========================================

def istatistik_hesapla(gun_filtre=None):
    with gunluk_kilit:
        kayitlar = [
            s for s in gunluk_sinyaller
            if gun_filtre is None or s["gun"] == gun_filtre
        ]
    toplam             = len(kayitlar)
    tp_kontrol_yapilan = 0
    tp_basarili        = 0
    sl_tetiklenen      = 0
    long_sayisi        = 0
    short_sayisi       = 0

    for s in kayitlar:
        sin = s["sinyal"].upper()
        if any(x in sin for x in ["BUY", "LONG"]):
            long_sayisi += 1
        else:
            short_sayisi += 1
        kontrol_yapildi = any(s[k] is not None for k in ["tp1_ok", "tp2_ok", "tp3_ok"])
        if kontrol_yapildi:
            tp_kontrol_yapilan += 1
            if any(s[k] is True for k in ["tp1_ok", "tp2_ok", "tp3_ok"]):
                tp_basarili += 1
            if s.get("sl_ok") is True:
                sl_tetiklenen += 1

    basari_oran = round(tp_basarili / tp_kontrol_yapilan * 100, 1) if tp_kontrol_yapilan > 0 else 0
    return {
        "toplam": toplam, "long": long_sayisi, "short": short_sayisi,
        "tp_kontrol": tp_kontrol_yapilan, "tp_basarili": tp_basarili,
        "sl_tetiklenen": sl_tetiklenen, "basari_oran": basari_oran
    }


def istatistik_mesaji():
    bugun = gun_str()
    b     = istatistik_hesapla(gun_filtre=bugun)
    t     = istatistik_hesapla()
    mesaj = (
        f"📊 <b>İSTATİSTİK</b>\n\n"
        f"<b>— Bugün ({bugun}) —</b>\n"
        f"📨 Toplam Sinyal: <b>{b['toplam']}</b>  (🚀 {b['long']} Long | 📉 {b['short']} Short)\n"
        f"✅ TP Başarılı: <b>{b['tp_basarili']}</b> / {b['tp_kontrol']}\n"
        f"⛔ SL Tetiklenen: <b>{b['sl_tetiklenen']}</b>\n"
        f"🏆 Başarı Oranı: <b>%{b['basari_oran']}</b>\n\n"
        f"<b>— Tüm Zamanlar —</b>\n"
        f"📨 Toplam Sinyal: <b>{t['toplam']}</b>  (🚀 {t['long']} Long | 📉 {t['short']} Short)\n"
        f"✅ TP Başarılı: <b>{t['tp_basarili']}</b> / {t['tp_kontrol']}\n"
        f"⛔ SL Tetiklenen: <b>{t['sl_tetiklenen']}</b>\n"
        f"🏆 Başarı Oranı: <b>%{t['basari_oran']}</b>"
    )
    return mesaj


# ==========================================
# GÜNLÜK ÖZET
# ==========================================

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

    b        = istatistik_hesapla(gun_filtre=bugun)
    satirlar = []
    for s in bugun_sinyaller:
        if TR_TZ:
            dt = datetime.fromtimestamp(s["zaman"], tz=TR_TZ)
        else:
            dt = datetime.utcfromtimestamp(s["zaman"])
        saat    = dt.strftime("%H:%M")
        sym     = s["symbol"].replace("USDT.P", "").replace("USDT", "")
        kontrol = any(s[k] is not None for k in ["tp1_ok", "tp2_ok", "tp3_ok"])
        if kontrol:
            tp_g     = sum(1 for k in ["tp1_ok","tp2_ok","tp3_ok"] if s[k] is True)
            tp_t     = sum(1 for k in ["tp1","tp2","tp3"] if s[k] is not None)
            sl_d     = "⛔SL" if s.get("sl_ok") else ""
            tp_durum = f"{tp_g}/{tp_t}TP {sl_d}".strip()
        else:
            tp_durum = "bekl."
        satirlar.append(f"{saat} | {sym[:6]:<6} | {s['sinyal'][:8]:<8} | {tp_durum}")

    mesaj = (
        f"<b>Gunluk Ozet — {bugun}</b>\n\n"
        f"📨 Sinyal: <b>{b['toplam']}</b>  (🚀{b['long']} / 📉{b['short']})\n"
        f"✅ TP: <b>{b['tp_basarili']}</b>/{b['tp_kontrol']}  "
        f"⛔ SL: <b>{b['sl_tetiklenen']}</b>\n"
        f"🏆 Basari: <b>%{b['basari_oran']}</b>\n\n"
        f"<code>Saat  | Sembol | Sinyal   | Sonuc\n"
        + "-" * 38 + "\n"
        + "\n".join(satirlar)
        + "</code>"
    )
    _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, mesaj)
    print(f"[OZET] Gonderildi. {b['toplam']} sinyal.")

    sinir = time.time() - 3 * 86400
    with gunluk_kilit:
        gunluk_sinyaller[:] = [s for s in gunluk_sinyaller if s["zaman"] > sinir]


# ==========================================
# PLAIN TEXT PARSER
# ==========================================

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
        if line.startswith("TP1 "):   tp1 = line[4:].strip()
        elif line.startswith("TP2 "): tp2 = line[4:].strip()
        elif line.startswith("TP3 "): tp3 = line[4:].strip()
        elif line.lower().startswith("cikis:"):
            sl = line.split(":", 1)[1].strip()
        elif line.lower().startswith("Giris (Entry):"):
            price = line.split(":", 1)[1].strip()
    return symbol, price, timeframe, sinyal if sinyal else "SINYAL", tp1, tp2, tp3, sl


# ==========================================
# WEBHOOK ENDPOINT
# ==========================================

@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True).strip()
    if not raw:
        return jsonify({"error": "Bos mesaj"}), 400

    # Telegram bot komutu mu?
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "message" in data:
            msg     = data["message"]
            text    = msg.get("text", "").strip().lower()
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if text.startswith("/istatistik"):
                yetkili = [x for x in [TELEGRAM_CHAT_ID, TELEGRAM_LOG_ID] if x]
                if chat_id in yetkili:
                    _telegram_mesaj_gonder(chat_id, istatistik_mesaji())
                    print(f"[KOMUT] /istatistik islendi. chat_id={chat_id}")
            return jsonify({"status": "ok"}), 200
    except:
        pass

    # Normal TradingView sinyali
    imageurl = None
    tp1 = tp2 = tp3 = sl = None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "symbol" in data:
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

    # Duplicate önleme (30 sn)
    simdi   = time.time()
    anahtar = f"{symbol}_{sinyal}_{timeframe}"
    if anahtar == son_sinyal["key"] and simdi - son_sinyal["zaman"] < 30:
        print(f"[DUPLICATE] {anahtar} atlandi.")
        return jsonify({"status": "duplicate"}), 200
    son_sinyal["key"]   = anahtar
    son_sinyal["zaman"] = simdi

    print(f"[SINYAL] {symbol} {sinyal} @ {price} ({timeframe})")
    mesaj = format_mesaj(symbol, price, timeframe, sinyal, tp1, tp2, tp3, sl)

    t = threading.Thread(
        target=send_telegram_and_schedule_tp,
        args=(mesaj, symbol, timeframe, sinyal, tp1, tp2, tp3, sl, imageurl, price))
    t.daemon = True
    t.start()

    return jsonify({"status": "ok"}), 200


@app.route("/health")
def health():
    ist = istatistik_hesapla()
    return jsonify({
        "status": "running",
        "time": time.strftime("%Y-%m-%d %H:%M UTC"),
        "toplam_sinyal": ist["toplam"],
        "basari_oran": f"%{ist['basari_oran']}"
    })


# ==========================================
# BAŞLAT
# ==========================================
# Gunicorn ile çalışırken de başlangıç işlemlerini yap
# ==========================================
# BAŞLAT
# ==========================================
VERI_DOSYASI = os.getenv("VERI_DOSYASI", "/data/sinyaller.json")

def dosyadan_yukle():
    global gunluk_sinyaller
    try:
        if not os.path.exists(VERI_DOSYASI):
            print("[DOSYA] Veri dosyasi bulunamadi, temiz baslaniyor.")
            return
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            veriler = json.load(f)
        sinir = time.time() - 30 * 86400
        veriler = [s for s in veriler if s.get("zaman", 0) > sinir]
        with gunluk_kilit:
            gunluk_sinyaller = veriler
        print(f"[DOSYA] {len(veriler)} sinyal yuklendi.")
    except Exception as e:
        print(f"[DOSYA] Okuma hatasi: {e}")

def dosyaya_kaydet():
    try:
        os.makedirs(os.path.dirname(VERI_DOSYASI), exist_ok=True)
        with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(gunluk_sinyaller, f, ensure_ascii=False, indent=2)
        print(f"[DOSYA] {len(gunluk_sinyaller)} sinyal kaydedildi.")
    except Exception as e:
        print(f"[DOSYA] Yazma hatasi: {e}")

print(f"[BASLANGIC] Veri dosyasi: {VERI_DOSYASI}")
dosyadan_yukle()
threading.Thread(target=gunluk_ozet_gonder, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Sunucu baslatiliyor -> http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
