# ==========================================
# FINAL SAFE BALINA PATCH
# Railway + Gunicorn Compatible
# ==========================================

# ------------------------------------------------
# ✅ 1) GLOBAL BALINA FONKSİYONU
# ------------------------------------------------
# Bunu def _whale_mesaj(...) ALTINA EKLE

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

                try:
                    _telegram_mesaj_gonder(cid, mesaj)

                except Exception as e:
                    print(f"[BALINA TELEGRAM HATA] {e}")

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


# ------------------------------------------------
# ✅ 2) /BALINA KOMUTU
# ------------------------------------------------
# Webhook içindeki /balina kısmı SADECE bu olacak:

"""
elif text.startswith("/balina"):

    threading.Thread(
        target=_balina_manuel,
        args=(chat_id,),
        daemon=True
    ).start()
"""


# ------------------------------------------------
# ✅ 3) AUTO SCHEDULER
# ------------------------------------------------
# Bunu threading kullanılan çalışan bölümün üstüne ekle

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


# ------------------------------------------------
# ✅ 4) THREAD START
# ------------------------------------------------
# Bunu mevcut çalışan thread startlarının ALTINA EKLE

"""
threading.Thread(
    target=balina_scheduler,
    daemon=True
).start()
"""

print("[BALINA] Auto scheduler aktif.")


# ------------------------------------------------
# ✅ 5) WHALE SYMBOLS
# ------------------------------------------------

WHALE_SYMBOLS = ["BTC_USDT", "ETH_USDT"]


# ------------------------------------------------
# ❌ SİLİNECEK TÜM KODLAR
# ------------------------------------------------

# Bunların hepsini dosyadan kaldır:

"""
def start_balina_scheduler():
"""

"""
start_balina_scheduler()
"""

"""
t_balina = threading.Thread(...)
"""

# Ayrıca nested yapı TAMAMEN kaldırılacak:

"""
elif text.startswith("/balina"):

    def _balina_manuel(cid):
"""

# ------------------------------------------------
# ✅ DOĞRU LOG
# ------------------------------------------------

"""
[BALINA] Auto scheduler aktif.
"""

"""
[BALINA AUTO] 01:30
"""
