# CLEANED BALINA SCHEDULER PATCH
# Bu dosya mevcut bot-chatgpt.py içine uygulanmış temiz versiyondur.

# ==========================================
# 🐋 GLOBAL BALINA MANUEL FONKSİYONU
# ==========================================

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

                ts_ms = deal.get("time", 0)
                taraf = deal.get("T", 1)

                yon = "ALIM" if taraf == 1 else "SATIM"

                zaman_str = _whale_fmt_zaman(ts_ms)

                mesaj = _whale_mesaj(
                    sym,
                    yon,
                    tutar,
                    miktar,
                    fiyat,
                    zaman_str
                )

                # 📸 Grafik screenshot
                img = get_screenshot_chartimg(
                    sym.replace("_", ""),
                    "5"
                )

                if img:
                    _telegram_foto_gonder(cid, img, mesaj)
                else:
                    _telegram_mesaj_gonder(cid, mesaj)

                bulunan = True
                break

        if bulunan:
            break

    if not bulunan:
        _telegram_mesaj_gonder(
            cid,
            "🐋 Balina izleme aktif.\n"
            f"Limit: ${WHALE_LIMIT_USD:,.0f}\n"
            "Son işlemlerde eşiği aşan hareket bulunamadı."
        )


# ==========================================
# 🐋 /BALINA KOMUTU
# ==========================================

# ESKİ nested _balina_manuel kodunu sil.
# SADECE ŞUNU BIRAK:

"""
elif text.startswith("/balina"):

    threading.Thread(
        target=_balina_manuel,
        args=(chat_id,),
        daemon=True
    ).start()
"""


# ==========================================
# 🐋 AUTO SCHEDULER
# ==========================================

def balina_scheduler():
    while True:
        try:
            now = datetime.now(TR_TZ) if TR_TZ else datetime.utcnow()

            # Her saat :30
            if now.minute == 30:

                print(f"[BALINA AUTO] {now.strftime('%H:%M')}")

                threading.Thread(
                    target=_balina_manuel,
                    args=(TELEGRAM_CHAT_ID,),
                    daemon=True
                ).start()

                time.sleep(60)

            time.sleep(5)

        except Exception as e:
            print(f"[BALINA HATA] {e}")
            time.sleep(10)


# ==========================================
# 🚀 THREAD BAŞLAT
# ==========================================

t_balina = threading.Thread(target=balina_scheduler)
t_balina.daemon = True
t_balina.start()

print("[BALINA] Auto scheduler aktif.")


# ==========================================
# ✅ WHALE SYMBOLS
# ==========================================

WHALE_SYMBOLS = ["BTC_USDT", "ETH_USDT"]


# ==========================================
# ❌ SİLİNECEK KISIM
# ==========================================

# BUNLARI DOSYADAN TAMAMEN SİL:

"""
def start_balina_scheduler():
    t = threading.Thread(target=balina_scheduler)
"""

# ve:
"""
start_balina_scheduler()
"""
