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
    if tf in ["1", "3"]:                             return 30    # 30 dakika
    if tf in ["5"]:                                  return 60    # 1 saat
    if tf in ["15"]:                                 return 240   # 4 saat
    if tf in ["30"]:                                 return 1440  # 1 gun
    if tf in ["60","1H","240","4H","D","1D","W","1W"]: return 10080 # 1 hafta
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
VERI_DOSYASI     = os.getenv("VERI_DOSYASI", "/data/sinyaller.json")


def veri_kaydet():
    try:
        os.makedirs(os.path.dirname(VERI_DOSYASI), exist_ok=True)
        with gunluk_kilit:
            veri = gunluk_sinyaller[:]
        with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False)
    except Exception as e:
        print(f"[KAYIT] Hata: {e}")


def dosyadan_yukle():
    global gunluk_sinyaller
    try:
        if os.path.exists(VERI_DOSYASI):
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                veri = json.load(f)
            with gunluk_kilit:
                gunluk_sinyaller = veri
            print(f"[YUKLE] {len(veri)} sinyal yuklendi.")
    except Exception as e:
        print(f"[YUKLE] Hata: {e}")


def sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, tp4, tp5, sl, message_id):
    kayit = {
        "gun": gun_str(), "zaman": time.time(),
        "symbol": symbol, "sinyal": sinyal,
        "timeframe": timeframe, "price": price,
        "tp1": tp1, "tp2": tp2, "tp3": tp3, "tp4": tp4, "tp5": tp5, "sl": sl,
        "tp1_ok": None, "tp2_ok": None, "tp3_ok": None, "tp4_ok": None, "tp5_ok": None,
        "sl_ok": None,
        "message_id": message_id
    }
    with gunluk_kilit:
        gunluk_sinyaller.append(kayit)
    veri_kaydet()
    if TELEGRAM_LOG_ID:
        log_satir = LOG_MAGIC + json.dumps(kayit, ensure_ascii=False)
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, log_satir)


def tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok):
    with gunluk_kilit:
        for s in gunluk_sinyaller:
            if s["message_id"] == message_id:
                s["tp1_ok"] = tp1_ok
                s["tp2_ok"] = tp2_ok
                s["tp3_ok"] = tp3_ok
                s["tp4_ok"] = tp4_ok
                s["tp5_ok"] = tp5_ok
                s["sl_ok"]  = sl_ok
                break
    veri_kaydet()


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

def format_mesaj(symbol, price, timeframe, sinyal, tp1=None, tp2=None, tp3=None,
                 tp4=None, tp5=None, sl=None):
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
    tp_listesi = [tp1, tp2, tp3, tp4, tp5]
    tp_satirlari = [(i+1, tp) for i, tp in enumerate(tp_listesi) if tp and str(tp) != 'null']
    if tp_satirlari:
        msg += "\n"
        for num, tp in tp_satirlari:
            msg += f"🎯 TP{num}: {fmt_tp(tp)}\n"
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

def tp_kontrol_gonder(symbol, sinyal, timeframe, tp1, tp2, tp3, tp4, tp5, sl,
                      message_id, dakika, sinyal_ts, sinyal_fiyat=None):
    is_long  = any(x in sinyal.upper() for x in ["BUY", "LONG"])
    is_short = any(x in sinyal.upper() for x in ["SELL", "SHORT"])

    def tp_ulasti(tp_fiyat, yuksek, dusuk):
        if tp_fiyat is None or str(tp_fiyat) == 'null':
            return False
        try:
            tp = float(str(tp_fiyat).replace(",", "."))
            if is_long:  return yuksek >= tp
            if is_short: return dusuk  <= tp
        except:
            pass
        return False

    def sl_tetiklendi(sl_fiyat, yuksek, dusuk):
        if sl_fiyat is None or str(sl_fiyat) == 'null':
            return False
        try:
            s = float(str(sl_fiyat).replace(",", "."))
            if is_long:  return dusuk  <= s
            if is_short: return yuksek >= s
        except:
            pass
        return False

    def mesaj_olustur(tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok, erken=False):
        fiyat_str     = fmt_fiyat(sinyal_fiyat) if sinyal_fiyat else ""
        sinyal_etiket = sinyal_emoji(sinyal)
        baslik = "⚡ <b>Erken TP/SL Bildirimi</b>" if erken else "<b>TP ve SL Kontrol</b>"
        tf_map_g = {"1":"1DK","3":"3DK","5":"5DK","15":"15DK","30":"30DK",
                    "60":"1SA","1H":"1SA","240":"4SA","D":"1G","1D":"1G"}
        tf_goster_s = tf_map_g.get(str(timeframe), timeframe)
        msg = (
            f"{baslik}\n\n"
            f"⚡ {symbol} | ⏰ {tf_goster_s}"
            + (f" | 💰 {fiyat_str}" if fiyat_str else "")
            + f" | {sinyal_etiket}\n\n"
        )
        tp_kontroller = [
            (tp1, tp1_ok, "TP1"), (tp2, tp2_ok, "TP2"), (tp3, tp3_ok, "TP3"),
            (tp4, tp4_ok, "TP4"), (tp5, tp5_ok, "TP5"),
        ]
        for tp_val, tp_ok, tp_label in tp_kontroller:
            if tp_val and str(tp_val) != 'null':
                msg += f"🎯 {tp_label}: {fmt_tp(tp_val)} — {'✅ ULASILDI' if tp_ok else '❌ Ulasilmadi'}\n"
        if sl and str(sl) != 'null':
            msg += f"🚪 SL: {fmt_fiyat(sl)} — {'⛔ TETİKLENDİ' if sl_ok else '— Bekleniyor'}\n"
        return msg

    def bildirim_gonder(msg):
        resp = _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, msg, reply_to=message_id)
        if resp and resp.status_code == 200:
            print(f"[TP] {symbol} bildirim gonderildi.")
        if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
            _telegram_mesaj_gonder(TELEGRAM_LOG_ID, msg)

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
        tp4_ok = tp_ulasti(tp4, yuksek, dusuk)
        tp5_ok = tp_ulasti(tp5, yuksek, dusuk)
        sl_ok  = sl_tetiklendi(sl, yuksek, dusuk)

        if (any([tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok]) or sl_ok) and not erken_bildirim_gonderildi:
            msg = mesaj_olustur(tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok, erken=True)
            bildirim_gonder(msg)
            erken_bildirim_gonderildi = True

            if sl_ok:
                sl_mesaj = (
                    f"⛔ <b>SL TETİKLENDİ</b>\n\n"
                    f"⚡ {symbol} | {sinyal_emoji(sinyal)}\n"
                    f"🚪 SL Seviyesi: {fmt_fiyat(sl)}"
                )
                bildirim_gonder(sl_mesaj)

            tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok)
            return

    end_ts        = int(time.time())
    yuksek, dusuk = get_high_low_in_period(symbol, sinyal_ts, end_ts)
    if yuksek is None:
        guncel = get_mexc_price(symbol)
        yuksek = dusuk = guncel

    tp1_ok = tp_ulasti(tp1, yuksek, dusuk)
    tp2_ok = tp_ulasti(tp2, yuksek, dusuk)
    tp3_ok = tp_ulasti(tp3, yuksek, dusuk)
    tp4_ok = tp_ulasti(tp4, yuksek, dusuk)
    tp5_ok = tp_ulasti(tp5, yuksek, dusuk)
    sl_ok  = sl_tetiklendi(sl, yuksek, dusuk)

    if not erken_bildirim_gonderildi:
        msg = mesaj_olustur(tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok, erken=False)
        bildirim_gonder(msg)

    tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok)


# ==========================================
# SINYAL GÖNDER + TP PLANLA
# ==========================================

def send_telegram_and_schedule_tp(caption, symbol, timeframe, sinyal,
                                   tp1, tp2, tp3, tp4, tp5, sl,
                                   imageurl=None, price=None):
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
        sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, tp4, tp5, sl, message_id)

    tp_var = any(x and str(x) != 'null' for x in [tp1, tp2, tp3, tp4, tp5])
    if message_id and tp_var:
        sinyal_ts  = int(time.time())
        kontrol_dk = tp_sure(timeframe)
        t = threading.Thread(
            target=tp_kontrol_gonder,
            args=(symbol, sinyal, timeframe, tp1, tp2, tp3, tp4, tp5, sl,
                  message_id, kontrol_dk, sinyal_ts, price))
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
    tp_basarili   = 0
    sl_tetiklenen = 0
    devam_eden    = 0
    long_sayisi   = 0
    short_sayisi  = 0

    for s in kayitlar:
        sin = s["sinyal"].upper()
        if any(x in sin for x in ["BUY", "LONG"]):
            long_sayisi += 1
        else:
            short_sayisi += 1
        kontrol_yapildi = any(s.get(k) is not None for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"])
        if kontrol_yapildi:
            if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
                tp_basarili += 1
            elif s.get("sl_ok") is True:
                sl_tetiklenen += 1
            else:
                devam_eden += 1  # kontrol bitti, ne TP ne SL — Devam Eden (Nötr)
        else:
            devam_eden += 1  # kontrol süresi henüz dolmadı — Devam Eden

    kapanan     = tp_basarili + sl_tetiklenen
    toplam      = kapanan + devam_eden
    basari_oran = round(tp_basarili / toplam * 100, 1) if toplam > 0 else 0
    return {
        "toplam": toplam, "long": long_sayisi, "short": short_sayisi,
        "tp_basarili": tp_basarili, "sl_tetiklenen": sl_tetiklenen,
        "devam_eden": devam_eden, "kapanan": kapanan, "basari_oran": basari_oran
    }


def istatistik_mesaji():
    bugun = gun_str()
    b     = istatistik_hesapla(gun_filtre=bugun)
    t     = istatistik_hesapla()

    with gunluk_kilit:
        bugun_kayitlar = [s for s in gunluk_sinyaller if s["gun"] == bugun]

    # En başarılı sembol (bugün, min 3 sinyal)
    sym_stats = {}
    for s in bugun_kayitlar:
        sym = sembol_grup(s["symbol"])
        if sym not in sym_stats:
            sym_stats[sym] = {"toplam": 0, "basarili": 0}
        sym_stats[sym]["toplam"] += 1
        if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
            sym_stats[sym]["basarili"] += 1

    en_sym = max(
        ((sym, st["basarili"]/st["toplam"]*100) for sym, st in sym_stats.items() if st["toplam"] >= 3),
        key=lambda x: x[1], default=("", -1)
    )

    # En başarılı zaman dilimi (bugün, min 3 sinyal)
    tf_map_g = {"1":"1DK","3":"3DK","5":"5DK","15":"15DK","30":"30DK",
                "60":"1SA","1H":"1SA","240":"4SA","D":"1G","1D":"1G"}
    tf_stats = {}
    for s in bugun_kayitlar:
        tf = s.get("timeframe","?")
        if tf not in tf_stats:
            tf_stats[tf] = {"toplam": 0, "basarili": 0}
        tf_stats[tf]["toplam"] += 1
        if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
            tf_stats[tf]["basarili"] += 1

    en_tf = max(
        ((tf_map_g.get(tf,tf), st["basarili"]/st["toplam"]*100) for tf, st in tf_stats.items() if st["toplam"] >= 3),
        key=lambda x: x[1], default=("", -1)
    )

    mesaj = (
        f"📊 <b>BEN KÜL YUTMAM — İstatistik</b>\n\n"
        f"<b>— Bugün ({bugun}) —</b>\n"
        f"📨 Toplam Sinyal: <b>{b['toplam']}</b>  (🚀 {b['long']} Long | 📉 {b['short']} Short)\n"
        f"✅ TP Başarılı: <b>{b['tp_basarili']}</b>\n"
        f"⛔ SL Tetiklenen: <b>{b['sl_tetiklenen']}</b>\n"
        f"⏳ Devam Eden: <b>{b['devam_eden']}</b>\n"
        f"🏆 Başarı Oranı: <b>%{b['basari_oran']}</b> ({b['tp_basarili']}/{b['toplam']})\n"
    )
    if en_sym[0]:
        mesaj += f"🥇 En Başarılı Sembol: <b>{en_sym[0]}</b> (%{round(en_sym[1],1)})\n"
    if en_tf[0]:
        mesaj += f"⏱ En Başarılı Zaman Dilimi: <b>{en_tf[0]}</b> (%{round(en_tf[1],1)})\n"
    mesaj += (
        f"\n<b>— Tüm Zamanlar —</b>\n"
        f"📨 Toplam Sinyal: <b>{t['toplam']}</b>  (🚀 {t['long']} Long | 📉 {t['short']} Short)\n"
        f"✅ TP Başarılı: <b>{t['tp_basarili']}</b>\n"
        f"⛔ SL Tetiklenen: <b>{t['sl_tetiklenen']}</b>\n"
        f"🏆 Başarı Oranı: <b>%{t['basari_oran']}</b> ({t['tp_basarili']}/{t['toplam']})"
    )
    return mesaj


# ==========================================
# RAPOR
# ==========================================

def bar_str(oran, genislik=5):
    dolu = round(oran / 100 * genislik)
    bos  = genislik - dolu
    return "\u2588" * dolu + "\u2591" * bos


def sembol_grup(symbol: str) -> str:
    s = symbol.upper().replace("USDT.P","").replace("USDT","").replace(".P","")
    for ana in ["BTC","ETH","BNB","SOL","XRP","AVAX","DOGE","ADA","DOT","LINK",
                "MATIC","TRX","TON","HYPE","LTC","NEAR","HBAR","SUI","XMR","ZEC","XLM"]:
        if s.startswith(ana):
            return ana
    return "OTHERS"


def rapor_hesapla(gun: str):
    with gunluk_kilit:
        kayitlar = [s for s in gunluk_sinyaller if s["gun"] == gun]

    tf_siralama = ["1","5","15","60","240","D"]
    tf_goster   = {"1":"1DK","5":"5DK","15":"15DK","60":"1SA","240":"4SA","D":"1G"}

    matris = {}
    tf_set = set()
    for s in kayitlar:
        grup = sembol_grup(s["symbol"])
        tf   = s.get("timeframe","?")
        if tf in tf_goster:
            tf_set.add(tf)
        if grup not in matris:
            matris[grup] = {}
        if tf not in matris[grup]:
            matris[grup][tf] = {"toplam":0,"basarili":0,"devam":0}
        matris[grup][tf]["toplam"] += 1
        kontrol_yapildi = any(s.get(k) is not None for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"])
        if kontrol_yapildi:
            if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
                matris[grup][tf]["basarili"] += 1
            elif not s.get("sl_ok"):
                matris[grup][tf]["devam"] += 1  # ne TP ne SL — Devam Eden
        else:
            matris[grup][tf]["devam"] += 1  # henüz kontrol edilmedi

    tf_kullanilan = [tf for tf in tf_siralama if tf in tf_set]

    toplam_satir = {tf: {"toplam":0,"basarili":0,"devam":0} for tf in tf_kullanilan}
    for grup, tfler in matris.items():
        for tf, st in tfler.items():
            if tf in toplam_satir:
                toplam_satir[tf]["toplam"]   += st["toplam"]
                toplam_satir[tf]["basarili"] += st["basarili"]
                toplam_satir[tf]["devam"]    += st["devam"]

    return matris, toplam_satir, tf_kullanilan, tf_goster, kayitlar


def rapor_mesaji(gun: str) -> str:
    matris, toplam_satir, tf_kullanilan, tf_goster, kayitlar = rapor_hesapla(gun)

    if not kayitlar:
        return f"\U0001f4ed <b>{gun}</b> tarihine ait sinyal bulunamad\u0131."

    toplam_sinyal   = len(kayitlar)
    toplam_basarili = sum(1 for s in kayitlar
                         if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]))
    toplam_sl       = sum(1 for s in kayitlar if s.get("sl_ok") is True)
    kontrol_yapilan = sum(1 for s in kayitlar
                         if any(s.get(k) is not None for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]))
    genel_oran      = round(toplam_basarili / kontrol_yapilan * 100, 1) if kontrol_yapilan else 0

    msg  = f"\U0001f4ca <b>BEN K\xdcL YUTMAM &amp; PAR\u0130TE \xd7 T\u0130MEFRAME RAPORU</b>\n"
    msg += f"<b>{gun}</b>\n\n"
    msg += (f"Toplam Sinyal: <b>{toplam_sinyal}</b>   "
            f"TP Ba\u015far\u0131l\u0131: <b>{toplam_basarili}/{kontrol_yapilan}</b>   "
            f"Genel Ba\u015far\u0131: <b>%{genel_oran}</b>\n"
            f"SL: <b>{toplam_sl}</b>\n\n")

    if not tf_kullanilan:
        msg += "Hen\xfcz tamamlanm\u0131\u015f sinyal yok."
        return msg

    # Tablo — monospace
    col_w = 8
    tf_basliklar = "  ".join(f"{tf_goster[tf]:>{col_w}}" for tf in tf_kullanilan)
    msg += f"<code>{'Parite':<8}  {tf_basliklar}  {'TOPLAM':>{col_w}}\n"
    msg += "\u2500" * (10 + len(tf_kullanilan) * (col_w+2) + col_w + 2) + "\n"

    for grup in sorted(matris.keys(), key=lambda x: (x == "OTHERS", x)):
        tfler = matris[grup]
        satir_yuzde = f"{grup:<8}"
        satir_oran  = " " * 8
        satir_bar   = " " * 8
        g_top = g_bas = 0
        for tf in tf_kullanilan:
            st = tfler.get(tf, {"toplam":0,"basarili":0})
            g_top += st["toplam"]
            g_bas += st["basarili"]
            if st["toplam"] > 0:
                o = st["basarili"] / st["toplam"] * 100
                satir_yuzde += f"  %{o:>5.1f}"
                satir_oran  += f"  {st['basarili']}/{st['toplam']:<5}"
                satir_bar   += f"  {bar_str(o):<7}"
            else:
                satir_yuzde += f"  {'No':>{col_w}}"
                satir_oran  += f"  {'0/0':>{col_w}}"
                satir_bar   += f"  {'':>{col_w}}"
        if g_top > 0:
            go = g_bas / g_top * 100
            satir_yuzde += f"  %{go:>5.1f}"
            satir_oran  += f"  {g_bas}/{g_top}"
            satir_bar   += f"  {bar_str(go)}"
        msg += satir_yuzde + "\n" + satir_oran + "\n" + satir_bar + "\n\n"

    # TOPLAM satırı
    msg += "\u2500" * (10 + len(tf_kullanilan) * (col_w+2) + col_w + 2) + "\n"
    satir_t_y = f"{'TOPLAM':<8}"
    satir_t_o = " " * 8
    satir_t_b = " " * 8
    gt_top = gt_bas = 0
    for tf in tf_kullanilan:
        st = toplam_satir.get(tf, {"toplam":0,"basarili":0})
        gt_top += st["toplam"]
        gt_bas += st["basarili"]
        if st["toplam"] > 0:
            o = st["basarili"] / st["toplam"] * 100
            satir_t_y += f"  %{o:>5.1f}"
            satir_t_o += f"  {st['basarili']}/{st['toplam']:<5}"
            satir_t_b += f"  {bar_str(o):<7}"
        else:
            satir_t_y += f"  {'No':>{col_w}}"
            satir_t_o += f"  {'0/0':>{col_w}}"
            satir_t_b += f"  {'':>{col_w}}"
    if gt_top > 0:
        go = gt_bas / gt_top * 100
        satir_t_y += f"  %{go:>5.1f}"
        satir_t_o += f"  {gt_bas}/{gt_top}"
        satir_t_b += f"  {bar_str(go)}"
    msg += satir_t_y + "\n" + satir_t_o + "\n" + satir_t_b + "\n</code>"
    return msg


def rapor_gorsel(gun: str):
    """Raporu koyu tema PNG olarak üretir — 5 kart + devam eden hücrelerde."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        import io
    except ImportError:
        return None

    matris, toplam_satir, tf_kullanilan, tf_goster, kayitlar = rapor_hesapla(gun)
    if not kayitlar:
        return None

    # Koyu tema renkleri
    BG        = "#13151A"
    CARD_BG   = "#1C1F28"
    ROW_ODD   = "#1A1D24"
    ROW_EVEN  = "#16181F"
    TOTAL_BG  = "#22262F"
    HDR_COL   = "#6B6F7A"
    TEXT_W    = "#E8E8E6"
    BAR_TRACK = "#22262F"

    def bar_col(p):
        if p is None: return "#3A3F4A"
        if p >= 60:   return "#5DC98A"
        if p >= 35:   return "#E8A835"
        return "#E05C5C"

    def cell_bg(p, t):
        if t == 0: return ROW_ODD
        if p >= 60: return "#1A2E1E"
        if p >= 35: return "#2A2210"
        return "#2A1212"

    # İstatistik
    b = istatistik_hesapla(gun_filtre=gun)
    tp_basarili   = b["tp_basarili"]
    sl_tetiklenen = b["sl_tetiklenen"]
    devam_eden    = b["devam_eden"]
    toplam_sinyal = b["toplam"]
    genel_oran    = b["basari_oran"]

    semboller = sorted(matris.keys(), key=lambda x: (x == "OTHERS", x))
    n_sym = len(semboller) + 1
    n_tf  = len(tf_kullanilan) + 1

    col_w = 1.55
    row_h = 1.0   # devam satırı için biraz daha yüksek
    fig_w = 2.0 + n_tf * col_w
    fig_h = 3.8 + n_sym * row_h

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor(BG)

    # Başlık
    ax.text(fig_w/2, fig_h - 0.22, "BEN KÜL YUTMAM — Günlük Rapor",
            ha="center", va="top", fontsize=13, fontweight="bold", color=TEXT_W)
    ax.text(fig_w/2, fig_h - 0.52, gun,
            ha="center", va="top", fontsize=10, color=HDR_COL)

    # 5 Metrik kart
    metrics = [
        ("Toplam Sinyal", str(toplam_sinyal),  TEXT_W),
        ("TP Başarılı",   str(tp_basarili),    "#5DC98A"),
        ("SL Tetiklenen", str(sl_tetiklenen),  "#E05C5C"),
        ("Devam Eden",    str(devam_eden),      "#E8A835"),
        ("Genel Başarı",  f"%{genel_oran}",    "#5B9CF6"),
    ]
    m_w = fig_w / 5
    for i, (lbl, val, col) in enumerate(metrics):
        mx = i * m_w
        my = fig_h - 1.48
        ax.add_patch(FancyBboxPatch((mx + 0.06, my), m_w - 0.12, 0.70,
                                     boxstyle="round,pad=0.04", linewidth=0, facecolor=CARD_BG))
        ax.text(mx + m_w/2, my + 0.54, lbl, ha="center", va="center",
                fontsize=6.5, color=HDR_COL)
        ax.text(mx + m_w/2, my + 0.22, val, ha="center", va="center",
                fontsize=13, fontweight="bold", color=col)

    # Tablo
    t_top  = fig_h - 1.92
    t_left = 1.55

    # Başlıklar
    ax.text(0.78, t_top + 0.34, "Parite", ha="center", va="center",
            fontsize=8, fontweight="bold", color=HDR_COL)
    for j, tf in enumerate(tf_kullanilan):
        x = t_left + j * col_w + col_w/2
        ax.text(x, t_top + 0.34, tf_goster.get(tf, tf),
                ha="center", va="center", fontsize=8, fontweight="bold", color=HDR_COL)
    ax.text(t_left + len(tf_kullanilan) * col_w + col_w/2, t_top + 0.34,
            "Toplam", ha="center", va="center", fontsize=8, fontweight="bold", color=HDR_COL)
    ax.axhline(t_top + 0.06, xmin=0.02, xmax=0.98, color="#22262F", linewidth=0.8)

    all_rows = semboller + ["TOPLAM"]
    for i, sym in enumerate(all_rows):
        y = t_top - i * row_h
        is_total = (sym == "TOPLAM")
        row_bg = TOTAL_BG if is_total else (ROW_ODD if i % 2 == 0 else ROW_EVEN)

        ax.add_patch(FancyBboxPatch((0.03, y - row_h + 0.04), fig_w - 0.06, row_h - 0.06,
                                     boxstyle="round,pad=0.02", linewidth=0, facecolor=row_bg, zorder=0))

        ax.text(0.78, y - row_h/2, sym, ha="center", va="center",
                fontsize=9, fontweight="bold" if is_total else "normal",
                color=TEXT_W if is_total else "#C8C8C6")

        cols_data = []
        if is_total:
            for tf in tf_kullanilan:
                st = toplam_satir.get(tf, {"toplam":0,"basarili":0,"devam":0})
                cols_data.append(st)
            gt_b   = sum(c["basarili"]    for c in cols_data)
            gt_t   = sum(c["toplam"]      for c in cols_data)
            gt_dev = sum(c.get("devam",0) for c in cols_data)
            cols_data.append({"basarili": gt_b, "toplam": gt_t, "devam": gt_dev})
        else:
            tfler = matris.get(sym, {})
            for tf in tf_kullanilan:
                cols_data.append(tfler.get(tf, {"toplam":0,"basarili":0,"devam":0}))
            gb   = sum(c["basarili"]    for c in cols_data)
            gt   = sum(c["toplam"]      for c in cols_data)
            gdev = sum(c.get("devam",0) for c in cols_data)
            cols_data.append({"basarili": gb, "toplam": gt, "devam": gdev})

        for j, st in enumerate(cols_data):
            x = t_left + j * col_w + col_w/2
            b_v = st["basarili"]
            t_v = st["toplam"]
            dev = st.get("devam", 0)
            p   = round(b_v / t_v * 100) if t_v > 0 else None

            ax.add_patch(FancyBboxPatch((x - col_w/2 + 0.07, y - row_h + 0.09),
                                         col_w - 0.14, row_h - 0.16,
                                         boxstyle="round,pad=0.03", linewidth=0,
                                         facecolor=cell_bg(p if p is not None else 0, t_v), zorder=1))

            if t_v > 0:
                ax.text(x, y - 0.18, f"%{p}", ha="center", va="center",
                        fontsize=9, fontweight="bold", color=bar_col(p), zorder=2)
                ax.text(x, y - 0.44, f"{b_v}/{t_v}", ha="center", va="center",
                        fontsize=7.5, color=TEXT_W, zorder=2)
                if dev > 0:
                    ax.text(x, y - 0.66, f"+{dev} devam", ha="center", va="center",
                            fontsize=6.5, color="#E8A835", zorder=2)
                bw = col_w - 0.36
                bx = x - bw/2
                by = y - row_h + 0.13
                ax.add_patch(plt.Rectangle((bx, by), bw, 0.07, color=BAR_TRACK, zorder=2))
                ax.add_patch(plt.Rectangle((bx, by), bw * p/100, 0.07, color=bar_col(p), zorder=3))
            elif dev > 0:
                ax.text(x, y - row_h/2, f"+{dev} devam", ha="center", va="center",
                        fontsize=7, color="#E8A835", zorder=2)
            else:
                ax.text(x, y - row_h/2, "—", ha="center", va="center",
                        fontsize=9, color="#3A3F4A", zorder=2)

        if is_total:
            ax.axhline(y + 0.05, xmin=0.02, xmax=0.98, color="#333740", linewidth=0.8)

    ax.text(fig_w/2, 0.10, "Başarı: en az 1 TP vurulmuş  |  yeşil ≥%60  sarı ≥%35  kırmızı <%35  |  ~N nötr  +N devam",
            ha="center", va="bottom", fontsize=6.5, color="#3A3F4A")

    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()

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
    print(f"[OZET] Istatistik ve rapor gonderiliyor. gun={bugun}")

    # 1) İstatistik mesajı
    _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, istatistik_mesaji())

    # 2) Görsel rapor
    img = rapor_gorsel(bugun)
    if img:
        _telegram_foto_gonder(TELEGRAM_CHAT_ID, img, f"Günlük Rapor — {bugun}")
    else:
        _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, rapor_mesaji(bugun))

    print(f"[OZET] Gonderildi.")
    print(f"[OZET] Gonderildi. {b['toplam']} sinyal.")

    sinir = time.time() - 3 * 86400
    with gunluk_kilit:
        gunluk_sinyaller[:] = [s for s in gunluk_sinyaller if s["zaman"] > sinir]
    veri_kaydet()


# ==========================================
# PLAIN TEXT PARSER
# ==========================================

def parse_plain(raw: str):
    symbol, timeframe, sinyal, price = "BTCUSDT", "60", "", "?"
    tp1, tp2, tp3, tp4, tp5, sl = None, None, None, None, None, None
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
        elif line.startswith("TP4 "): tp4 = line[4:].strip()
        elif line.startswith("TP5 "): tp5 = line[4:].strip()
        elif line.lower().startswith("cikis:"):
            sl = line.split(":", 1)[1].strip()
        elif line.lower().startswith("giris:"):
            price = line.split(":", 1)[1].strip()
    return symbol, price, timeframe, sinyal if sinyal else "SINYAL", tp1, tp2, tp3, tp4, tp5, sl


# ==========================================
# WEBHOOK ENDPOINT
# ==========================================

@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True).strip()
    if not raw:
        return jsonify({"error": "Bos mesaj"}), 400
    print(f"[RAW] {raw[:500]}")

    # Telegram bot komutu mu?
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and ("message" in data or "channel_post" in data):
            msg     = data.get("message") or data.get("channel_post")
            text    = msg.get("text", "").strip().lower()
            chat_id = str(msg.get("chat", {}).get("id", ""))
            yetkili = [x for x in [TELEGRAM_CHAT_ID, TELEGRAM_LOG_ID] if x]
            if text.startswith("/istatistik"):
                if chat_id in yetkili:
                    _telegram_mesaj_gonder(chat_id, istatistik_mesaji())
                    print(f"[KOMUT] /istatistik islendi. chat_id={chat_id}")
                else:
                    print(f"[KOMUT] /istatistik yetkisiz. chat_id={chat_id} yetkili={yetkili}")
            elif text.startswith("/rapor"):
                if chat_id in yetkili:
                    gun = gun_str()
                    print(f"[KOMUT] /rapor basliyor. gun={gun} chat_id={chat_id}")
                    img = rapor_gorsel(gun)
                    if img:
                        _telegram_foto_gonder(chat_id, img, f"Günlük Rapor — {gun}")
                        print(f"[KOMUT] /rapor gorsel gonderildi.")
                    else:
                        _telegram_mesaj_gonder(chat_id, rapor_mesaji(gun))
                        print(f"[KOMUT] /rapor metin gonderildi.")
                else:
                    print(f"[KOMUT] /rapor yetkisiz. chat_id={chat_id} yetkili={yetkili}")
            elif text.startswith("/tarayici"):
                if chat_id in yetkili:
                    print(f"[KOMUT] /tarayici islendi. chat_id={chat_id}")
                    threading.Thread(target=_tarayici_gonder, daemon=True).start()
                else:
                    print(f"[KOMUT] /tarayici yetkisiz. chat_id={chat_id}")

            elif text.startswith("/balina"):
                if chat_id in yetkili:
                    print(f"[KOMUT] /balina islendi. chat_id={chat_id}")
                    def _balina_manuel(cid):
                        bulunan = False
                        for sym in WHALE_SYMBOLS:
                            deals = _whale_fetch(sym)
                            if not deals:
                                continue
                            for deal in deals[:50]:
                                fiyat  = float(deal.get("p", 0))
                                miktar = float(deal.get("v", 0))
                                tutar  = fiyat * miktar
                                if tutar >= WHALE_LIMIT_USD:
                                    ts_ms     = deal.get("time", 0)
                                    taraf     = deal.get("T", 1)
                                    yon       = "ALIM" if taraf == 1 else "SATIM"
                                    zaman_str = _whale_fmt_zaman(ts_ms)
                                    mesaj     = _whale_mesaj(sym, yon, tutar, miktar, fiyat, zaman_str)
                                    _telegram_mesaj_gonder(cid, mesaj)
                                    bulunan = True
                                    break
                            if bulunan:
                                break
                        if not bulunan:
                            _telegram_mesaj_gonder(cid,
                                "🐋 Balina izleme aktif.\n"
                                f"Limit: ${WHALE_LIMIT_USD:,.0f}\n"
                                "Son işlemlerde eşiği aşan hareket bulunamadı."
                            )
                    threading.Thread(target=_balina_manuel, args=(chat_id,), daemon=True).start()
                else:
                    print(f"[KOMUT] /balina yetkisiz. chat_id={chat_id}")
            else:
                print(f"[KOMUT] Bilinmeyen komut: {text[:50]}")
            return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[KOMUT-HATA] {e}")

    # Normal TradingView sinyali
    imageurl = None
    tp1 = tp2 = tp3 = tp4 = tp5 = sl = None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "symbol" in data:
            symbol    = data.get("symbol", data.get("ticker", "BTCUSDT"))
            timeframe = str(data.get("timeframe", "60"))
            sinyal    = data.get("signal", data.get("sinyal", "SINYAL"))
            price     = str(data.get("price", "?"))
            imageurl  = data.get("imageurl", None)
            # null string olarak gelebilir, temizle
            def _clean(v):
                if v is None or str(v) == 'null':
                    return None
                return str(v)
            tp1 = _clean(data.get("tp1"))
            tp2 = _clean(data.get("tp2"))
            tp3 = _clean(data.get("tp3"))
            tp4 = _clean(data.get("tp4"))
            tp5 = _clean(data.get("tp5"))
            sl  = _clean(data.get("sl", data.get("cikis")))
        else:
            raise ValueError
    except Exception:
        symbol, price, timeframe, sinyal, tp1, tp2, tp3, tp4, tp5, sl = parse_plain(raw)
        imageurl = None

    # Duplicate önleme (30 sn)
    simdi   = time.time()
    anahtar = f"{symbol}_{sinyal}_{timeframe}"
    if anahtar == son_sinyal["key"] and simdi - son_sinyal["zaman"] < 30:
        print(f"[DUPLICATE] {anahtar} atlandi.")
        return jsonify({"status": "duplicate"}), 200
    son_sinyal["key"]   = anahtar
    son_sinyal["zaman"] = simdi

    print(f"[SINYAL] {symbol} {sinyal} @ {price} ({timeframe}) | TP1={tp1} TP2={tp2} TP3={tp3} SL={sl}")
    mesaj = format_mesaj(symbol, price, timeframe, sinyal, tp1, tp2, tp3, tp4, tp5, sl)

    t = threading.Thread(
        target=send_telegram_and_schedule_tp,
        args=(mesaj, symbol, timeframe, sinyal, tp1, tp2, tp3, tp4, tp5, sl, imageurl, price))
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
# BALINA HAREKETLİLİĞİ — MEXC FUTURES
# ==========================================

WHALE_LIMIT_USD   = float(os.getenv("WHALE_LIMIT_USD", "1000000"))  # $1M
WHALE_SYMBOLS     = ["BTC_USDT", "ETH_USDT"]
WHALE_COOLDOWN    = 60   # aynı parite için minimum kaç saniye bekle
WHALE_POLL_SEC    = 3    # kaç saniyede bir kontrol et

_whale_last_ts    = {}   # son gönderilen işlem timestamp'i per symbol

def _whale_fmt_zaman(ts_ms):
    # MEXC bazen saniye bazen milisaniye döndürür
    # 1e10'dan büyükse milisaniye, değilse saniye
    ts = ts_ms / 1000 if ts_ms > 1e10 else ts_ms
    if ts <= 0:
        if TR_TZ:
            return datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M:%S")
        return datetime.utcnow().strftime("%d %b %Y %H:%M:%S UTC")
    try:
        if TR_TZ:
            dt = datetime.fromtimestamp(ts, tz=TR_TZ)
        else:
            dt = datetime.utcfromtimestamp(ts)
        return dt.strftime("%d %b %Y %H:%M:%S")
    except:
        if TR_TZ:
            return datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M:%S")
        return datetime.utcnow().strftime("%d %b %Y %H:%M:%S UTC")

def _whale_fmt_tutar(usd):
    if usd >= 1_000_000:
        return f"${usd/1_000_000:.2f}M"
    return f"${usd:,.0f}"

def _whale_fmt_fiyat(fiyat, symbol):
    if "BTC" in symbol:
        return f"{fiyat:,.2f} USDT"
    return f"{fiyat:,.4f} USDT"

def _whale_fmt_miktar(miktar, symbol):
    coin = symbol.split("_")[0]
    if miktar >= 1:
        return f"{miktar:,.2f} {coin}"
    return f"{miktar:.6f} {coin}"

def _whale_mesaj(symbol, yon, tutar_usd, miktar, fiyat, zaman_str):
    yon_emoji = "🟢" if yon == "ALIM" else "🔴"
    yon_str   = "BÜYÜK ALIM" if yon == "ALIM" else "BÜYÜK SATIM"
    sembol_goster = symbol.replace("_", "") + ".P"
    ayrac = "─" * 20
    satirlar = [
        "❗ " + KANAL_ADI + " ❗",
        "",
        "🐋 BTC ve ETH Balina Hareketliliği",
        ayrac,
        "⚡ " + sembol_goster,
        yon_emoji + " " + yon_str,
        "",
        "💰 Tutar   : " + _whale_fmt_tutar(tutar_usd),
        "📦 Miktar  : " + _whale_fmt_miktar(miktar, symbol),
        "📌 Fiyat   : " + _whale_fmt_fiyat(fiyat, symbol),
        "🕐 Zaman   : " + zaman_str,
        ayrac,
        "Siz de kulübe katılıp, alarmları kaçırmamak için lütfen iletişime geçin.",
        "İletişim: " + KANAL_TAG,
    ]
    return "\n".join(satirlar)

def _whale_fetch(symbol):
    """MEXC Futures son işlemlerini çek."""
    url = f"https://contract.mexc.com/api/v1/contract/deals/{symbol}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and data.get("data"):
                return data["data"]
    except Exception as e:
        print(f"[WHALE] Fetch hata ({symbol}): {e}")
    return []

def _whale_kontrol():
    """Her WHALE_POLL_SEC saniyede bir tüm sembolleri kontrol et."""
    # Başlangıçta mevcut son işlemleri kaydet — eski işlem bildirimi olmasın
    for sym in WHALE_SYMBOLS:
        deals = _whale_fetch(sym)
        if deals:
            _whale_last_ts[sym] = deals[0].get("time", 0)
    print(f"[WHALE] Izleme basladi. Limit: ${WHALE_LIMIT_USD:,.0f} | Semboller: {WHALE_SYMBOLS}")

    while True:
        try:
            for sym in WHALE_SYMBOLS:
                deals = _whale_fetch(sym)
                if not deals:
                    continue

                son_ts = _whale_last_ts.get(sym, 0)
                yeni_islemler = [d for d in deals if d.get("time", 0) > son_ts]

                if yeni_islemler:
                    _whale_last_ts[sym] = deals[0].get("time", 0)

                for deal in reversed(yeni_islemler):
                    fiyat   = float(deal.get("p", 0))
                    miktar  = float(deal.get("v", 0))
                    tutar   = fiyat * miktar
                    ts_ms   = deal.get("time", 0)
                    taraf   = deal.get("T", 1)  # 1=alım, 2=satım (MEXC)

                    if tutar < WHALE_LIMIT_USD:
                        continue

                    # Cooldown kontrolü
                    son_bildirim = _whale_last_ts.get(f"{sym}_bildirim", 0)
                    simdi_ms = time.time() * 1000
                    if (simdi_ms - son_bildirim) < WHALE_COOLDOWN * 1000:
                        continue

                    yon = "ALIM" if taraf == 1 else "SATIM"
                    zaman_str = _whale_fmt_zaman(ts_ms)
                    mesaj = _whale_mesaj(sym, yon, tutar, miktar, fiyat, zaman_str)

                    _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, mesaj)
                    _whale_last_ts[f"{sym}_bildirim"] = simdi_ms
                    print(f"[WHALE] {sym} {yon} ${tutar:,.0f} @ {fiyat}")

                    if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
                        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, mesaj)

        except Exception as e:
            print(f"[WHALE] Dongu hata: {e}")

        time.sleep(WHALE_POLL_SEC)


# ==========================================
# FUTURES TARAYICI — EN ÇOK YÜKSELEN/DÜŞEN
# ==========================================

TARAYICI_TOP_N = 5

def _tarayici_veri_cek():
    """MEXC Futures tüm paritelerin 24s ticker verisi."""
    try:
        r = requests.get("https://contract.mexc.com/api/v1/contract/ticker", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and data.get("data"):
                return data["data"]
    except Exception as e:
        print(f"[TARAYICI] Veri cekme hatasi: {e}")
    return []

def _tarayici_mesaj(yukselenler, dusenler, zaman_str):
    ayrac = "─" * 28

    def yuksel_satir(i, item):
        sym  = item["sym"][:10].ljust(10)
        pct  = f"+{item['pct']:.2f}%".rjust(9)
        fiyat = ("💰 $" + item["fiyat"]).ljust(18)
        return f"🟢 {i}. {sym} {pct}   {fiyat}"

    def dusen_satir(i, item):
        sym  = item["sym"][:10].ljust(10)
        pct  = f"-{abs(item['pct']):.2f}%".rjust(9)
        fiyat = ("💰 $" + item["fiyat"]).ljust(18)
        return f"🔴 {i}. {sym} {pct}   {fiyat}"

    baslik = "❗ " + KANAL_ADI + " ❗"
    alt_baslik = "📊 MEXC Futures — Saatlik Tarama"
    zaman_satir = "🕐 " + zaman_str

    yuksel_satirlar = [yuksel_satir(i, item) for i, item in enumerate(yukselenler, 1)]
    dusen_satirlar  = [dusen_satir(i, item)  for i, item in enumerate(dusenler, 1)]

    msg = (
        baslik + "\n\n"
        + alt_baslik + "\n"
        + zaman_satir + "\n"
        + ayrac + "\n\n"
        + "🚀 <b>En Çok Yükselenler</b>\n"
        + "<pre>" + "\n".join(yuksel_satirlar) + "</pre>\n"
        + ayrac + "\n\n"
        + "📉 <b>En Çok Düşenler</b>\n"
        + "<pre>" + "\n".join(dusen_satirlar) + "</pre>\n"
        + ayrac + "\n"
        + "Siz de kulübe katılıp, alarmları kaçırmamak için lütfen iletişime geçin.\n"
        + "İletişim: " + KANAL_TAG
    )
    return msg

def _tarayici_gonder():
    tickers = _tarayici_veri_cek()
    if not tickers:
        print("[TARAYICI] Veri alinamadi.")
        return

    liste = []
    for t in tickers:
        try:
            sym = t.get("symbol", "")
            if not sym.endswith("_USDT"):
                continue
            pct  = float(t.get("riseFallRate", 0)) * 100
            last = float(t.get("lastPrice", 0))
            if last <= 0:
                continue
            # Fiyat formatla
            if last >= 1000:
                fiyat_str = f"{last:,.1f}"
            elif last >= 1:
                fiyat_str = f"{last:,.3f}"
            else:
                fiyat_str = f"{last:.6f}"
            liste.append({
                "sym": sym.replace("_USDT", ""),
                "pct": pct,
                "fiyat": fiyat_str
            })
        except:
            continue

    if not liste:
        print("[TARAYICI] İşlenecek veri yok.")
        return

    yukselenler = sorted(liste, key=lambda x: x["pct"], reverse=True)[:TARAYICI_TOP_N]
    dusenler    = sorted(liste, key=lambda x: x["pct"])[:TARAYICI_TOP_N]

    if TR_TZ:
        zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
    else:
        zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

    mesaj = _tarayici_mesaj(yukselenler, dusenler, zaman_str)
    _telegram_mesaj_gonder(TELEGRAM_CHAT_ID, mesaj)
    print(f"[TARAYICI] Gonderildi. Top {TARAYICI_TOP_N} yukselenler/dusenler.")

    if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, mesaj)

def _tarayici_zamanlayici():
    """Her saat başında tarayıcı çalıştır."""
    import datetime as dt_mod

    print("[TARAYICI] Zamanlayici basladi.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()

            # Bir sonraki saat başını hesapla
            sonraki = simdi.replace(minute=0, second=0, microsecond=0) + dt_mod.timedelta(hours=1)
            bekle = (sonraki - simdi).total_seconds()
            print(f"[TARAYICI] Sonraki rapor: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(bekle)
            _tarayici_gonder()
            time.sleep(5)  # double-fire önleme
        except Exception as e:
            print(f"[TARAYICI] Zamanlayici hata: {e}")
            time.sleep(60)


# ==========================================
# BAŞLAT
# ==========================================

print(f"[BASLANGIC] Veri dosyasi: {VERI_DOSYASI}")
dosyadan_yukle()
threading.Thread(target=gunluk_ozet_gonder, daemon=True).start()
threading.Thread(target=_whale_kontrol, daemon=True).start()
threading.Thread(target=_tarayici_zamanlayici, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Sunucu baslatiliyor -> http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
