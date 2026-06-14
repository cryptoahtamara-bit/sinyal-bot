import os, time, json, re, threading, requests, base64, io, hmac, hashlib, traceback
try:
    import websocket as _ws_lib  # websocket-client
    HAS_WS = True
except ImportError:
    HAS_WS = False
# bot_v528 — 14 Haziran 2026
# Degisiklikler (v517 -> v518):
#   1. sinyal_kaydet: sinyal_tipi, fg_deger, fg_kategori, funding_rate,
#      oi_yonu, piyasa_yonu, hacim_durumu, seans alanları eklendi
#   2. _tp_kosul_rapor_hesapla: 7 bölümlü TP koşul analiz fonksiyonu
#   3. _tp_kosul_rapor_gorsel: Pillow ile görsel üretimi
#   4. _tp_kosul_rapor_zamanlayici: Her saatin :30'unda TOPIC_RAPOR'a gönderir
# bot_v517 — 13 Haziran 2026
# Degisiklikler (v516 -> v517):
#   1. BUG FIX: /liq Direnc gosteriminde ayni deger iki kez yaziliyordu
#      Neden: son 20 mumun high listesinde ayni seviye tekrar edince
#      direnc_adaylar[0] == direnc_adaylar[1] olabiliyordu
#      Duzeltme: destek ve direnc adaylari unique hale getirildi (set + round)
#      Gosterimde de direnc[0]==direnc[1] kontrolu eklendi
# bot_v516 — 11 Haziran 2026
# Degisiklikler (v515 -> v516):
#   1. GUNCELLEME: "olta ver" — metin tablo yerine gorsel (PNG) gonderir
#      _olta_ver_tablo() tamamen yeniden yazildi
#      Pillow ile karanlik temali tablo gorseli uretilir
#      LONG (yesil baslik) ve SHORT (kirmizi baslik) icin ayri 2 PNG
#      Coin adi + mevcut fiyat kolon basliginda (ortalanmis, beyaz)
#      TF etiketleri grup ortasinda dikey ortalanmis (cyan)
#      GiRiS=sari, SL=kirmizi, TP=yesil
#      Footer: fiyat giris bolgesindeki coinler icin tek cumle ozet
#      Gorsel _telegram_topic_foto_gonder ile TOPIC_OLTA'ya gonderilir
# bot_v515 — 11 Haziran 2026
# Degisiklikler (v514 -> v515):
#   1. YENI KOMUT: "olta ver" — TOPIC_OLTA'ya yazilinca tetiklenir
#      BTC, ETH, XRP, SOL icin tum TF'leri paralel ceker
#      LONG ve SHORT icin ayri 2 tablo mesaji gonderir
#      Tablo formati: TF x VERi satirlari (Giris/SL/TP1/TP2), 4 coin kolonu
#      Monospace <pre> blokunda, hizali
#      Fonksiyon: _olta_ver_gonder()
# bot_v513 — 11 Haziran 2026
# Degisiklikler (v512 -> v513):
#   1. Eşik coin bazında: BTC %25, ETH %45
#      Gerçek grid verisiyle test edildi — ETH long $1,574–$1,641 (harita: $1,574–$1,621) ✅
#   2. DEBUG logları kaldırıldı
# bot_v512 — 11 Haziran 2026
# Degisiklikler (v511 -> v512):
#   1. DEBUG: grid_long/short_1d değerleri Railway log'a yazdırılıyor
#      ETH long alt sınırı sorununu kök nedeninden çözmek için
# bot_v511 — 11 Haziran 2026
# Degisiklikler (v510 -> v511):
#   1. _grid_minmax eşiği %15 → %25 — dağınık bantlar kesiliyor
#      ETH long alt sınırı daraltıldı
# bot_v510 — 11 Haziran 2026
# Degisiklikler (v509 -> v510):
#   1. KÖK NEDEN DÜZELTİLDİ: likidasyon bölgesi hesabı tamamen yeniden yazıldı
#      _bolge_hesapla_dis (band_usd kümeleme) kaldırıldı
#      Yerine _grid_minmax: normalize sonrası grid.sum(axis=1) — haritayla birebir aynı veri
#      Eşiğin (%15) üzerindeki tüm bantların min/max'ı → geniş bölge doğru çıkıyor
# bot_v509 — 10 Haziran 2026
# Degisiklikler (v508 -> v509):
#   1. BUG FIX: _bolge_hesapla artık kendi try bloğu içinde tanımlı
#      n_pb, price_min, price_max parametre olarak geçiliyor
#      band_long/short_usd.max() > 0 kontrolü eklendi
# bot_v508 — 10 Haziran 2026
# Degisiklikler (v507 -> v508):
#   1. BUG FIX: _bolge_hesapla çağrısı try bloğu dışına alındı
#      _bant_etiketleri exception verince liq_long/short_zone None kalıyordu
#      Artık band_long/short_usd başlangıçta None, sonra try bloğu dışında hesaplanıyor
# bot_v507 — 10 Haziran 2026
# Degisiklikler (v506 -> v507):
#   1. MİMARİ DÜZELTMESİ: Likidasyon bölgeleri artık _bant_etiketleri ile aynı mantıktan geliyor
#      Haritadaki etiketler ile metin tamamen aynı hesaplamadan besleniyor
#      Grid okuma / connected component kaldırıldı — doğrudan band_arr gruplaması kullanılıyor
# bot_v506 — 10 Haziran 2026
# Degisiklikler (v505 -> v506):
#   1. IYILESTIRME: Grid bölge eşiği %25 → %50 artırıldı
#      Sadece en yoğun bantlar bölgeye dahil oluyor, üst/alt sınır daralıyor
# bot_v505 — 10 Haziran 2026
# Degisiklikler (v504 -> v505):
#   1. BUG FIX: _liq_veri_cek return dict'inde liq_long/short_baskisi None olarak set edildi
#      v504'te değişken kaldırılmıştı ama return dict'i güncellenmemişti
# bot_v504 — 10 Haziran 2026
# Degisiklikler (v503 -> v504):
#   1. MİMARİ DEĞİŞİKLİK: Likidasyon bölgeleri artık ısı haritası grid'inden okunuyor
#      _liq_heatmap_gercek → görsel + grid_long/grid_short 1D dizilerini döndürür
#      _liq_yorum → grid'den connected component ile en yoğun bölgeyi okur
#      _liq_veri_cek → ayrı likidasyon hesabı tamamen kaldırıldı
#      Metin ile harita artık birebir aynı veriden besleniyor
# bot_v503 — 10 Haziran 2026
# Degisiklikler (v502 -> v503):
#   1. BUG FIX: _grid_bolge — connected component yaklaşımı
#      Eşik üstündeki komşu bantlar birleştiriliyor, en yüksek hacimli sürekli bölge seçiliyor
#      Haritadaki geniş yoğunluk bölgesini doğru yansıtması bekleniyor
# bot_v502 — 10 Haziran 2026
# Degisiklikler (v501 -> v502):
#   1. BUG FIX: _grid_bolge — kümeleme algoritması kaldırıldı
#      Top 6 yoğun bandın doğrudan min-max aralığı döndürülüyor
#      Isı haritasının görsel olarak gösterdiği bölgeyle birebir uyuşma için
# bot_v501 — 10 Haziran 2026
# Degisiklikler (v500 -> v501):
#   1. BUG FIX: _grid_bolge — bant seçimi yakınlık ağırlıklı skora göre yapılıyor
#      Fiyat merkezine yakın bantlar daha yüksek skor alıyor
#      top_n=8→10, eşik %2.5→%3.0 — ETH Long geniş aralık için iyileştirme
# bot_v500 — 10 Haziran 2026
# Degisiklikler (v499 -> v500):
#   1. BUG FIX: Küme eşiği %4 → %2.5 — BTC short $63.6K yerine $61.8K-$62.4K bandı
# bot_v499 — 10 Haziran 2026
# Degisiklikler (v498 -> v499):
#   1. BUG FIX: _grid_bolge — min-max yerine fiyata yakın yoğun küme seçiliyor
#      top_n=8 içinde %4 aralıkta birbirine yakın bantlar kümeleniyor
#      BTC short $63.6K yerine $61.8K-$62.4K bandını göstermesi bekleniyor
# bot_v498 — 10 Haziran 2026
# Degisiklikler (v497 -> v498):
#   1. BUG FIX: Likidasyon bölgesi — ısı haritasıyla tamamen aynı grid mantığına geçildi
#      15m kline + tüm kaldıraç seviyeleri (5x-100x) + grid → en yoğun 5 bant
#      Artık metin ile harita aynı kaynaktan besleniyor
# bot_v497 — 10 Haziran 2026
# Degisiklikler (v496 -> v497):
#   1. BUG FIX: Likidasyon bölgesi — kline kaynağı 1h/24 → 4h/30 muma geçildi
#      Son 5 günlük giriş fiyat aralığı daha gerçekçi likidasyon seviyeleri veriyor
#   2. IYILESTIRME: Küme algoritması fiyata yakınlığı da ağırlıklandırıyor
#      Haritadaki yoğun bölgelerle örtüşme artırıldı
# bot_v496 — 10 Haziran 2026
# Degisiklikler (v495 -> v496):
#   1. BUG FIX: Likidasyon bölgesi — 10x kaldıraç çıkarıldı, sadece 25x/50x/100x
#      10x BTC için ~$55K, ETH için ~$1,456 veriyor (haritada yok)
#      25x minimum ile BTC ~$59.7K-$60.3K, ETH ~$1,585-$1,601 → haritayla örtüşüyor
# bot_v495 — 10 Haziran 2026
# Degisiklikler (v494 -> v495):
#   1. IYILESTIRME: RSI eşiği 30→35'e indirildi, 35-42 arası "satım bölgesine yakın" eklendi
#   2. BUG FIX: CVD birikim — kümülatif CVD negatif olsa bile fiyat↓ CVD↑ birikim sayılıyor
#      Kısa vadeli birikim ile uzun vadeli satış baskısı ayrı yorumlanıyor
#   3. IYILESTIRME: Ne Yapmalıyım — breadth=0 + skor<25 durumunda çöküş modu uyarısı
# bot_v494 — 10 Haziran 2026
# Degisiklikler (v493 -> v494):
#   1. BUG FIX: Likidasyon bölgesi — kaldıraç bazlı hesaplamaya geçildi
#      Isı haritasıyla aynı mantık: giriş * (1 ± 1/kaldıraç)
#      25x/50x/100x ağırlıklı, en yakın küme seçiliyor
#      BTC Long ~$60K, Short ~$62K bandını yakalıyor (haritayla uyumlu)
# bot_v493 — 10 Haziran 2026
# Degisiklikler (v492 -> v493):
#   1. BUG FIX: Likidasyon bölgesi hesabı — tek bant yerine top 5 yoğun bant alınıyor
#      n_bant 20→30, top_n=5 band cluster → gerçekçi geniş aralık
#      BTC Long $59-60K, Short $62-64K bandını yakalamak için
#   2. IYILESTIRME: /liq'ten likidasyon grafiği kaldırıldı
#      Artık sadece ısı haritası + yorum metin geliyor
# bot_v492 — 10 Haziran 2026
# Degisiklikler (v491 -> v492):
#   1. IYILESTIRME: /liq yorum mesajı sadeleştirildi
#      Kaldırılanlar: Funding, OI, yön yorumu (güçlü yükseliş/düşüş sinyali),
#                     Ne Yapmalıyım bölümü, Toplam OI satırı
#      Kalanlar: 4H Momentum, Likidasyon bölgeleri, Destek/Direnç, Risk değerlendirmesi
# bot_v491 — 10 Haziran 2026
# Degisiklikler (v490 -> v491):
#   1. IYILESTIRME: RSI "aşırı alım bölgesine yakın" uyarısı sadece puan>=0
#      (yani market yönü yukarı veya yatay) olduğunda gösteriliyor
#      Aşağı yönlü piyasada 65-70 RSI önemli bir sinyal değil, mesaj kaldırıldı
# bot_v490 — 10 Haziran 2026
# Degisiklikler (v489 -> v490):
#   1. BUG FIX: Breakout benzerliği — F&G ve Breadth ağırlığı 16→26 artırıldı
#      extreme_fear + dar breadth durumunda yükseliş senaryosu öne çıkmıyor
#   2. IYILESTIRME: BREAKOUT_ENVANTER'e "2022 Bear Dip Birikim" senaryosu eklendi
#      (extreme_fear + dar breadth + dengeli funding → mevcut duruma daha uygun)
#   3. IYILESTIRME: CVD bölümüne uyumlu_asagi listesi eklendi
#      fiyat ↓ CVD ↓ → "gerçek satış baskısı" olarak gösteriliyor
#   4. IYILESTIRME: RSI mesajına 65-70 arası "alım bölgesine yakın" uyarısı eklendi
# bot_v489 — 10 Haziran 2026
# Degisiklikler (v488 -> v489):
#   1. BUG FIX: CVD birikim/pump listesi — CVD değeri de yönü desteklemiyorsa listeye girmiyor
#      Birikim: uyumsuz_asagi VE cvd_val > 0 (gerçek alım baskısı var)
#      Sahte pump: uyumsuz_yukari VE cvd_val < 0 (satış gizleniyor)
#      Böylece BTC CVD -6764 iken BTC birikim listesine girmiyor
#   2. IYILESTIRME: Market Yönü breadth ağırlığı artırıldı (en güçlü sinyal)
#      8+ breadth → +3, 6+ → +2, 4+ → +1
#      BTC CVD < -3000 ise -1 puan eklendi
#   3. IYILESTIRME: Ne Yapmalıyım CVD önerisi — gerçek birikim yoksa çıkmıyor
#      CVD değeri negatifse "birikim var" mesajı artık gösterilmiyor
# bot_v488 — 10 Haziran 2026
# Degisiklikler (v487 -> v488):
#   1. BUG FIX: CVD — BTC birikim listesinden çıkarıldı, zaten ayrı satırda gösteriliyor
#   2. IYILESTIRME: Sayısal değerler kaldırıldı — funding %, HAC.Ç x, piyasa skoru sayısı
#      Yalnızca yorum kalıyor; sayılar tabloda zaten var
#   3. BUG FIX: "Sert kırılım" uyarısı sadece puan>=4 veya <=-4 durumunda çıkıyor
#   4. IYILESTIRME: Likidasyon eşiği $0.1M → $1M olarak güncellendi
# bot_v487 — 10 Haziran 2026
# Degisiklikler (v486 -> v487):
#   1. IYILESTIRME: Piyasa Skoru yorumu sadece durum belirtiyor, öneri içermiyor
#      Öneriler yalnızca "Ne Yapmalıyım?" bölümünde yer alıyor
# bot_v486 — 10 Haziran 2026
# Degisiklikler (v485 -> v486):
#   1. IYILESTIRME: "Teknik Skor" → "Piyasa Skoru" olarak yeniden adlandırıldı, skor değeri parantez içinde gösteriliyor
#   2. YENİ: "Ne Yapmalıyım?" bölümü eklendi — madde madde, genel strateji + coin bazlı öneriler
#      - Market yönü + piyasa skoru → genel strateji
#      - CVD birikim + RSI teyidi → dip alma adayları
#      - Aşırı alım/satım coinleri için uyarı
#      - Funding, HAC.Ç, breakout benzerliği uyarıları
# bot_v485 — 10 Haziran 2026
# Degisiklikler (v483 -> v485):
#   1. IYILESTIRME: _analiz_ozet_telegram tamamen yeniden yazıldı
#      - Tanımlama yok (CVD nedir, RSI nedir vb.)
#      - Uzun açıklama yok
#      - Tabloda zaten olan veri tekrarı yok
#      - Kısa ve öz: her satır max 1 cümle, sadece dikkat çeken coinler/değerler
#      - Tüm fonksiyon try/except ile sarıldı, hata olursa Telegram'a hata mesajı gelir
# bot_v483 — 10 Haziran 2026
# Degisiklikler (v482 -> v483):
#   1. BUG FIX: Likidasyon bölgesi — grid/kaldıraç yöntemi kaldırıldı
#      1h kline hacim bazlı yöntem eklendi (heatmap ile aynı kaynak/mantık)
#   2. IYILESTIRME: Market Yönü — skor/breadth tutarsızlığında daha nüanslı mesaj
#   3. IYILESTIRME: Breakout Benzerliği — çelişkili liste kaldırıldı, tek en iyi eşleşme
#   4. IYILESTIRME: /analiz görselinden olta paneli kaldırıldı (ayrı /olta komutu var)
#   5. IYILESTIRME: Ozet metin yeniden yazıldı — kısa/öz, tanım yok, tekrar yok
#   6. BUG FIX: Ozet metinde "F&G" → "F&amp;G" — HTML parse hatası düzeltildi
#      (Telegram HTML modunda & kaçırılmazsa mesaj sessizce reddediliyor)
# bot_v482 — 9 Haziran 2026
# bot_v482 — 9 Haziran 2026
# Degisiklikler (v481 -> v482):
#   1. BUG FIX: RSI asiri alim esigi >= 70 → > 70 (tam 70 asiri alim sayilmiyordu)
#      AVAX(70) gibi durumlar artik asiri alim olarak isaretlenmeyecek
#   2. IYILESTIRME: Market Yönü YUKARI aciklamasi duzeltildi
#      "Tüm göstergeler" → "Çoğunluk göstergeler" (daha dogru ifade)
#   3. IYILESTIRME: /analiz ETH long likidasyon bolge hesaplamasi
#      Kaldıraç agirliklarinda 25x daha fazla, 100x daha az agirlik verildi
# bot_v481 — 9 Haziran 2026
# Degisiklikler (v480 -> v481):
#   1. BUG FIX: Likidasyon bölgesi hesaplama yöntemi degistirildi
#      Agirlikli ortalama yöntemi kaldırıldı — uzak seviyelere kayıyordu
#      Grid bazlı hesaplama eklendi — heatmap ile aynı mantık, grafik yok
#      Fiyat etrafı ±6% pencere, 100 bin, en yogun 3 ardisik bin seçilir
#      Kaldıraç listesi: 25x/50x/100x (10x çıkarıldı — yine uzak düşüyordu)
# bot_v480 — 9 Haziran 2026
# Degisiklikler (v479 -> v480):
#   1. BUG FIX: Likidasyon bölgesi çok geniş çıkıyordu ($49,995 — $76,092 gibi)
#      5x kaldıraç hesaplamadan çıkarıldı (fiyatı çok uzağa itiyordu)
#      Artık sadece 10x/25x/50x/100x kullanılıyor
#      Bant genişliği %1.5 -> %0.8'e indirildi — daha dar ve gerçekçi bölge
# bot_v479 — 9 Haziran 2026
# Degisiklikler (v478 -> v479):
#   1. BUG FIX: Likidasyon bölgesi WS proxy engelinden dolayi 0 event aliyordu
#      wss://fstream.binance.com/ws/!forceOrder@arr Railway proxy'de bloklu
#   2. YENİ: _liq_veri_cek icinde kaldıraç bazlı likidasyon bolgesi hesaplama
#      15dk klines verisiyle 5x/10x/25x/50x/100x kaldıraç seviyeleri hesaplanıyor
#      En yogun long/short bolgesi agirlikli ortalama ile bulunuyor
#      liq_long_baskisi ve liq_short_baskisi artik veri dict'inde doluyor
#      WS verisine bagimlilik kaldirildi — proxy sorununu bypass eder
# bot_v478 — 9 Haziran 2026
# Degisiklikler (v477 -> v478):
#   1. YENİ: Likidasyon WS verisi diske kaydediliyor — /data/liq_ws_data.json
#      _liq_ws_kaydet()  — her 5 dakikada diske yaz
#      _liq_ws_yukle()   — startup'ta diskten yukle (restart sonrasi veri kaybolmuyor)
#      _liq_ws_temizle() — 3 gunde bir 2 gunluk veri sil, 1 gunluk veri kalsin
#      _liq_ws_bakim_zamanlayici() — daemon thread ile yonetim
#   2. YENİ: _liq_ws_bolge_hesapla() — gercek WS verisinden likidasyon bolgesi hesapla
#      fiyat etrafinda +/-8% aralikta en yogun long/short seviyeleri
#      /liq yorumunda liq_long_baskisi ve liq_short_baskisi artik gercek veriyle doluyor
# bot_v477 — 8 Haziran 2026
# Degisiklikler (v476 -> v477):
#   1. BUG FIX: /liq Likidasyon Bölgesi yanlış hesaplanıyordu
#      Destek/direnc fiyata gore filtrelendi — fiyat altindaki low=destek, ustundeki high=direnc
#      Likidasyon bölgesi fallback: 24h high/low yerine destek/direnc seviyeleri kullaniliyor
#   2. BUG FIX: Direnc sirasi terstti (,711 / ,706 yerine ,706 / ,711 olmali)
#      direnc[0]=en yakin, direnc[-1]=en uzak olacak sekilde sirala duzeltildi
# bot_v476 — 8 Haziran 2026
# Degisiklikler (v475 -> v476):
#   1. BUG FIX: Long/Short Oran yorumu — "Balina ve KY farklı yönde" hatası
#      abs(bal_long - ky_long) < 5 karsilastirmasi yanlis sonuc veriyordu
#      Duzeltme: her ikisinin de long/short agirlikli olup olmadigi kontrol edilir
#      bal_long > bal_short ve ky_long > ky_short esit ise ayni yon, degil ise farkli
# bot_v475 — 8 Haziran 2026
# Degisiklikler (v474 -> v475):
#   1. BUG FIX: /skor — "Olta verileli: son 24 saat" sorunu duzeltildi
#      Olta mesaji direkt parse edildiginde cache ts aktarilmiyordu
#      _olta_skor_kontrol() artik cache_ts parametresi aliyor
#      /skor handler once cache ts cekip fonksiyona geciriyor
# bot_v474 — 8 Haziran 2026
# Degisiklikler (v473 -> v474):
#   1. Kayıp sinyal verisi offset olarak Tüm Zamanlar'a eklendi
#      05 Haziran 2026 00:30 itibarıyla: 4982 sinyal, 2185 TP, 34 SL
#      2338 Long, 2644 Short — Bu değerler gun_filtre=None istatistiğine eklenir
# bot_v464 — 6 Haziran 2026
# Degisiklikler (v463 -> v464):
#   1. BUG FIX: _liq_gonder() — ETH verisi proxy timeout alınca 1 retry
#      BTC gelip ETH gelmeme sorunu giderildi
# bot_v463 — 6 Haziran 2026
# Degisiklikler (v462 -> v463):
#   1. KULYUTMAZ 780 coin taraması kaldırıldı (proxy tüketimi engellendi)
#      _kulyutmaz_alarm_kontrol() ve _kulyutmaz_alarm_zamanlayici() devre dışı
#      TOPIC_YUKSELENLER artık sadece saatlik tarayıcı raporu alıyor
#   2. Binance fallback proxy kaldırıldı — MEXC Futures başarısız olunca
#      direkt MEXC Spot'a düşüyor, Binance proxy denemesi yapılmıyor
# bot_v462 — 5 Haziran 2026
# Degisiklikler (v461 -> v462):
#   1. BUG FIX: Atomic write - once gecici dosyaya yaz, sonra rename
#      Yazma sirasinda bot kesilse bile eski dosya korunur
#      os.replace() atomik islem — dosya asla yarim kalmaz
# bot_v461 — 5 Haziran 2026
# Degisiklikler (v460 -> v461):
#   1. BUG FIX: f_collectTPs Pine Script ile birebir eslesme
#      Pine: for i = 1 to tpLookback → son bar haric, geriye doğru 21 bar
#      Python: range(son_i-1, son_i-1-TP_LOOKBACK, -1) ile ayni indeks mantigi
#   2. BOT VERSIYON v460 korundu (zaten dogru)
# bot_v460 — 5 Haziran 2026
# Degisiklikler (v459 -> v460):
#   1. BUG FIX: CVWAP hesabı yanlıştı
#      vwaplength=1 → ta.vwap degil ta.ema(ta.vwap,1)=ta.vwap
#      Gercek VWAP: kümülatif(tipik_fiyat * hacim) / kümülatif(hacim)
#      Bu sayede STRONG BUY/SELL vs LONG/SHORT doğru ayrışacak
#   2. BOT VERSIYON string güncellendi
# bot_v459 — 5 Haziran 2026
# Degisiklikler (v458 -> v459):
#   1. BUG FIX: Eski sinyal gonderiliyordu
#      Sinyal sadece son 1 mumda olusmussa gecerli sayilir
#      long_sinyal_i >= n-2 veya short_sinyal_i >= n-2 sarti eklendi
#   2. DEBUG logu korundu
# bot_v458 — 5 Haziran 2026
# Degisiklikler (v457 -> v458):
#   1. DEBUG: Sinyal detay logu eklendi
#      closes[-1], sari/mor/beyaz hat, ema200, is_long degerlerini logla
# bot_v457 — 5 Haziran 2026
# Degisiklikler (v456 -> v457):
#   1. DEBUG: Tarama sonu ozet logu eklendi
#      Kac sembol tarandı, kac sinyal bulundu, sinyal tipleri
# bot_v456 — 5 Haziran 2026
# Degisiklikler (v455 -> v456):
#   1. BUG FIX: _ema fonksiyon ismi catismasi
#      Satir 4765'te baska bir _ema fonksiyonu var ve tek float donduruyordu
#      Python'da sonraki tanim oncekini eziyor — atr_beyaz float oluyordu
#      Kululyutmaz fonksiyonlari _kulyutmaz_ema/_kulyutmaz_atr/_kulyutmaz_cci olarak yeniden adlandirildi
# bot_v455 — 4 Haziran 2026
# Degisiklikler (v454 -> v455):
#   1. BUG FIX: _kulyutmaz_sinyal_hesapla çağrısında parametre sırası yanlıştı
#      _skor_klines_cek: closes, volumes, highs, lows döndürüyor
#      Çağrı closes, highs, lows, volumes olmalıydı ama volumes highs'a gidiyordu
#      Düzeltildi: closes, volumes, highs, lows → doğru parametrelere atandı
# bot_v454 — 4 Haziran 2026
# Degisiklikler (v453 -> v454):
#   1. BUG FIX: MEXC veri bozuk gelince closes her karakter float oluyor
#      closes[0] fiyat araligi kontrolu eklendi (0.000001 - 10_000_000)
#      Bu aralık dışı veri bozuk sayılır, coin atlanır
# bot_v453 — 4 Haziran 2026
# Degisiklikler (v452 -> v453):
#   1. DEBUG: closes/highs/lows/volumes tip ve içerik logu eklendi
#      _kulyutmaz_sinyal_hesapla çağrısından önce veri doğrulama logu
# bot_v452 — 4 Haziran 2026
# Degisiklikler (v451 -> v452):
#   1. BUG FIX: _ema() içinde result[i-1]=None olduğunda None*(1-k) hatası
#      EMA hesabında önceki değer None ise SMA ile yeniden başlatılıyor
#      Bu sayede atr_beyaz/atr_sari/atr14 listeleri doğru float döner
# bot_v451 — 4 Haziran 2026
# Degisiklikler (v450 -> v451):
#   1. DEBUG: Hata mesajına traceback eklendi — tam satır tespiti için
# bot_v450 — 4 Haziran 2026
# Degisiklikler (v449 -> v450):
#   1. BUG FIX: 'float' object is not subscriptable hatası (devam)
#      _skor_klines_cek (None,None,None,None) döndüğünde tuple kontrolü geçiyordu
#      closes/highs/lows/volumes None kontrolü eklendi
# bot_v449 — 4 Haziran 2026
# Degisiklikler (v448 -> v449):
#   1. BUG FIX: 'float' object is not subscriptable hatası
#      _skor_klines_cek beklenmedik dönüş tipinde patlıyordu
#      isinstance(sonuc, tuple) + len(sonuc)==4 kontrolü eklendi
# bot_v448 — 4 Haziran 2026
# Degisiklikler (v447 -> v448):
#   1. TOPIC_YUKSELENLER: %2 degisim alarmi kaldirildi
#      Yerine KÜLYUTMAZ V.4.3 indikatör mantigi eklendi
#      _kulyutmaz_sinyal_hesapla(): Beyaz/Sari/Mor hat + EMA200 + CVWAP
#      _kulyutmaz_alarm_kontrol(): Tüm MEXC coinleri 5dk mumlarla tarar
#      _kulyutmaz_alarm_zamanlayici(): 5 dakikada bir çalışır
#      Sinyal tipleri: LONG / STRONG BUY / SHORT / STRONG SELL
#      TP: Son 21 mumun hacim bazlı high/low seviyeleri (5 adet)
#      SL: %2 sabit (LONG için aşağı, SHORT için yukarı)
#   2. TOPIC_ALARM ve tüm diğer mantıklara dokunulmadı
# bot_v446 — 4 Haziran 2026
# Degisiklikler (v445 -> v446):
#   1. BREAKOUT_ENVANTER: fear_greed ve breadth alanlari eklendi
#      - Düşüş olayları: extreme_fear + dar breadth
#      - Yükseliş olayları: normal/acgozluluk + geniş breadth
#   2. _fg_kategori() ve _breadth_kategori() yardımcı fonksiyonları eklendi
#   3. _breakout_benzerlik_hesapla() 4 -> 6 kritere yükseltildi
#      Kriterler: Funding, OI yönü, CVD, Likidasyon, F&G, Breadth
#      5+ kriter eşleşmesi = KRİTİK uyarı
#   4. /analiz çıktısında F&G kategorisi ve Breadth özet satırına eklendi
# bot_v445 — 4 Haziran 2026
# Degisiklikler (v444 -> v445):
#   1. BREAKOUT_ENVANTER listesi eklendi (TOPIC_OLTA'nin hemen altina)
#      8 gerçek BTC olayı: 4 çöküş + 4 yükseliş
#      Her olay: tarih, yön, hareket_pct, süre_gün, piyasa koşulları
#   2. _breakout_benzerlik_hesapla() fonksiyonu eklendi
#      Funding, OI yönü, CVD uyum, Likidasyon tarafı üzerinden 100 üzeri skor
#   3. _analiz_ozet_telegram() en altına yeni bölüm eklendi
#      /analiz komutunda otomatik çalışır, en benzer 3 olay listelenir
#      Yükseliş/düşüş ağırlığına göre genel yorum eklenir
# bot_v444 — 4 Haziran 2026
# Degisiklikler (v443 -> v444):
#   1. Fibonacci lookback değerleri güncellendi
#      Her TF kendi zaman dilimine özgü swing hesaplıyor
#      5m=6(30dk) 15m=12(3s) 1h=24(1g) 4h=14(2.3g) 1d=30(1ay)
#      Tüm TF'lerin aynı girişi vermesi sorunu çözüldü
# bot_v443 — 3 Haziran 2026
# Degisiklikler (v442 -> v443):
#   1. BUG FIX: "Olta verileli: 0 dk önce" hatası
#      Cache loop herhangi bir sym'in ts'sini alıyordu
#      XRP all yeni verilince BTC /skor da XRP'nin ts'sini alıyordu
#      Düzeltildi: sym'e göre doğru cache aranıyor
# bot_v442 — 3 Haziran 2026
# Degisiklikler (v441 -> v442):
#   1. Giriş fiyata yakın (%0.5 içinde) ise ◉ işareti eklendi
#      Olta mesajının altına "◉ Fiyat giriş bölgesinde" notu düşülür
#      Fibonacci hesabına dokunulmadı — seviye doğru, sadece bilgi notu
# bot_v441 — 3 Haziran 2026
# Degisiklikler (v440 -> v441):
#   1. BUG FIX: Giriş fiyatı anlık fiyatla aynı çıkıyor (XRP dar band)
#      Long giriş min %0.3 altında, short giriş min %0.3 üstünde garantisi
# bot_v440 — 3 Haziran 2026
# Degisiklikler (v439 -> v440):
#   1. BUG FIX: /skor since_ts ile çok az mum çekiyordu (2-4 mum)
#      Minimum limit garantisi eklendi: 5m=10, 15m=6, 1h/4h/1d=3
# bot_v439 — 3 Haziran 2026
# Degisiklikler (v438 -> v439):
#   1. BUG FIX: 1s olta verisi gelmiyor
#      _trend_fetch_klines MEXC futures çağrısında proxy eksikti
#      Proxy eklendi — Min60 proxy üzerinden çalışacak
#   2. 4s/Gün aynı giriş sorunu için TF limit'leri güncellendi
# bot_v438 — 3 Haziran 2026
# Degisiklikler (v437 -> v438):
#   1. BUG FIX: "name isaret is not defined" hatası
#      v426'da Açık durumu ⏳'e sadeleştirilmişti ama eski satır silinmemişti
# bot_v437 — 3 Haziran 2026
# Degisiklikler (v436 -> v437):
#   1. BUG FIX: "Olta verileli: son 24 saat" sorunu
#      ts cache'de tutuluyordu ama parsed dict'e aktarılmıyordu
#      Cache fallback'te ts parsed'a ekleniyor, since_ts doğru alınıyor
# bot_v436 — 3 Haziran 2026
# Degisiklikler (v435 -> v436):
#   1. /skor zaman damgası: olta verildiği andan itibaren kontrol
#      "Son 24 saatlik mumlar" yerine "Olta verileli: 45 dk önce" gösterilir
#      Sadece olta verildikten sonraki mumlar kontrol edilir
#      Önceki fiyat hareketleri false positive vermez
#      Cache'e ts (Unix timestamp) kaydediliyor, deploy sonrası da korunuyor
# bot_v435 — 3 Haziran 2026
# Degisiklikler (v434 -> v435):
#   1. BUG FIX: BTC (eski olta) parse=FAIL ana neden bulundu
#      parse_blok fonksiyonu giris/sl/tp1 hesaplıyor ama "return []" ile bitiyordu
#      Sonuç hiç dönmüyordu → cache her zaman boş görünüyordu
#      Düzeltildi: giris+sl+tp1 doluysa dict listesi döner
# bot_v434 — 3 Haziran 2026
# Degisiklikler (v433 -> v434):
#   1. BUG FIX: BTC (eski olta) /skor cache deploy sonrasi bos kaliyordu
#      Cache artik /data/son_olta_cache.json dosyasina yaziliyor
#      Startup'ta diskten yukleniyor — deploy sonrasi kaybolmuyor
# bot_v433 — 3 Haziran 2026
# Degisiklikler (v432 -> v433):
#   1. Olta tablosundan Skor sütunu kaldırıldı
#      Skor sadece /skor komutuyla gösterilir
#   2. BUG FIX: BTC (eski olta) /skor hâlâ çalışmıyordu
#      _olta_skor_kontrol parse başarısız olunca hata mesajı döndürüyordu
#      Cache fallback sadece None gelince devreye giriyordu
#      Düzeltildi: parse başarısız → None dön, hata mesajı üst katta verilir
# bot_v432 — 3 Haziran 2026
# Degisiklikler (v431 -> v432):
#   1. BUG FIX: BTC (eski olta) /skor cache'den parse edilemiyordu
#      Cache'e HTML yerine temiz metin + parse edilmiş dict kaydediliyor
#      _olta_skor_kontrol_parsed: cache'deki parsed dict'i doğrudan işler
#   2. BUG FIX: 1s "veri alınamadı" — Proxy 402 hatası
#      Tüm proxy yolları başarısız olunca 15m mumlardan 1h hesaplanıyor
#      4x15m = 1h mantığıyla fallback çalışıyor
# bot_v431 — 3 Haziran 2026
# Degisiklikler (v430 -> v431):
#   1. BUG FIX: BTC TUM /skor yanlış yön gösteriyordu
#      Alıntılanan mesaj başlığından LONG/SHORT yönü belirleniyor
#      SHORT mesajı alıntılandıysa SHORT cache, LONG ise LONG cache kullanılıyor
#   2. BUG FIX: Cache thread içinde global tanımı eksikti
#      _olta_gonder ve _skor_gonder'e global _son_olta_cache eklendi
# bot_v430 — 3 Haziran 2026
# Degisiklikler (v429 -> v430):
#   1. BUG FIX: Eski olta (BTC) /skor ile parse edilemiyordu
#      Sebep: Telegram bot mesajı alıntılanınca reply_text kısalıyor
#      Çözüm: Her olta sorgusu sonucu _son_olta_cache[TOPIC_OLTA]'ya kaydediliyor
#      /skor parse başarısız olursa otomatik cache kullanılıyor
# bot_v429 — 3 Haziran 2026
# Degisiklikler (v428 -> v429):
#   1. BUG FIX: /skor 1s "veri alınamadı" daha iyi debug
#      MEXC futures HTTP hata kodu ve mesajı loglanıyor
#      success:false durumu yakalanıp sonraki interval deneniyor
# bot_v428 — 3 Haziran 2026
# Degisiklikler (v427 -> v428):
#   1. /skor satır formatı: TF + giriş fiyatı birlikte
#      "5dk - 1981  ✅ TP1"  |  "Gün - 1952  ✅ TP1 TP2"
# bot_v427 — 3 Haziran 2026
# Degisiklikler (v426 -> v427):
#   1. BUG FIX: "name pct is not defined" hatası
#      Eski satırlar silinmemişti, pct hesabı gereksiz kalmıştı
#      Temizlendi: sadece ✅ TP1 | ✅ TP1 TP2 | ⏳ | ❌
# bot_v426 — 3 Haziran 2026
# Degisiklikler (v425 -> v426):
#   1. /skor TP etiketi eklendi
#      ✅ TP1 — sadece TP1 geldi
#      ✅ TP1 TP2 — her ikisi de geldi
#      ⏳ — bekleniyor/açık
#      ❌ — SL geldi
# bot_v425 — 3 Haziran 2026
# Degisiklikler (v424 -> v425):
#   1. /skor 3 durum: ✅ TP hit | ⏳ Bekleniyor/Açık | ❌ SL hit
# bot_v424 — 3 Haziran 2026
# Degisiklikler (v423 -> v424):
#   1. /skor sonuç sadeleştirildi
#      TP1/TP2 Hit, SL Hit, Açık, Bekleniyor yerine sadece:
#      ✅ — TP1 veya TP2'ye ulaştı
#      ❌ — SL hit, bekleniyor veya açık pozisyon
# bot_v423 — 3 Haziran 2026
# Degisiklikler (v422 -> v423):
#   1. BUG FIX: /skor 1s "veri alınamadı" hatası
#      MEXC futures 1h için "Min60" yanı sıra "Hour1","60m" de deneniyor
#      Binance spot ve futures ikisi de fallback olarak eklendi
#   2. /skor satır etiketi: TF kodu yerine giriş fiyatı gösteriliyor
#      "5dk" yerine "69890", "15dk" yerine "68954" gibi
# bot_v422 — 2 Haziran 2026
# Degisiklikler (v421 -> v422):
#   1. BUG FIX: ETH /skor "-%99.9 uzakta" hatası
#      Kök neden: q() fonksiyonu ETH 1906'yı "1.906" formatında yazıyor
#      parse_sayi "1.906" → 1.906 (ondalık) okuyordu, 1906 olmalıydı
#      YENİ KURAL: nokta ayırıcı + 3 haneli ondalık → her zaman binlik
#      1.906→1906, 69.890→69890 ✅  |  69.89→69.89, 1.5→1.5 ✅
# bot_v421 — 2 Haziran 2026
# Degisiklikler (v420 -> v421):
#   1. BUG FIX: /skor sonuç gönderilmiyordu
#      Logda: "[TREND] Tum kaynaklar basarisiz" → Binance Railway'de bloklu
#      _trend_fetch_klines (len>=50 şartlı) yerine _skor_klines_cek eklendi
#      MEXC futures → MEXC spot → Binance sırası, min 3 mum şartı
#   2. /skor handler'a detaylı log eklendi
#      Parse sonucu, sonuç uzunluğu ve boş sonuç durumu loglanıyor
# bot_v420 — 2 Haziran 2026
# Degisiklikler (v419 -> v420):
#   1. BUG FIX: /skor — "-%99.9 uzakta" hatası
#      Nokta binlik ayırıcı yanlış parse ediliyordu
#      "69.890" → 69.890 yerine artık doğru 69890 okunuyor
#      Kural: tam kısım 2+ hane ve ondalık 3 hane → binlik nokta
#   2. BUG FIX: /skor — 1s/4s/Gün "veri yok" hatası
#      limit_map 24/6/2 mum çekiyordu ama _trend_fetch_klines >=50 şartı var
#      Düzeltildi: 1h=72, 4h=52, 1d=52 mum çekiliyor
#   3. BUG FIX: /skor — "Olta mesajı okunamadı" hatası
#      Telegram HTML mesajlarında reply_text boş geliyordu
#      HTML tag'leri temizlenerek düz metin alınıyor artık
# bot_v419 — 2 Haziran 2026
# Degisiklikler (v418 -> v419):
#   1. BUG FIX: /skor — BTC (eski olta) mesajı parse edilemiyordu
#      Eski format (LONG OLTA / SHORT OLTA blokları) artık destekleniyor
#      Her iki yön için ayrı sonuç gösteriliyor
#   2. BUG FIX: TP1 etiketindeki "1" rakamı sayı olarak alınıyordu
#      tp1=1.0 olunca -%99.9 uzakta hatası çıkıyordu
#      Kolon sonrasındaki sayılar kullanılıyor artık
#   3. BUG FIX: ETH gibi küçük fiyatlar yanlış parse ediliyordu
#      "1,950" → 1950 yerine artık doğru 1.950 okunuyor
#      Kural: tam kısım 1 rakam → ondalık virgül, 2+ rakam → binlik
# bot_v418 — 2 Haziran 2026
# Degisiklikler (v417 -> v418):
#   1. YENI: /skor komutu — olta mesajini alintilayip /skor yaz
#      Bot mesajdaki TF/Giris/SL/TP1/TP2 seviyelerini parse eder
#      Son 24 saatlik mumlarla her TF'i kontrol eder:
#      ⭐ TP2 Hit | ✅ TP1 Hit | ❌ SL Hit | ⏳ Bekliyor | 📍 Açık pozisyon
#      Yüzde bazlı kazanç/kayıp ve fiyata uzaklık gösterilir
# bot_v417 — 2 Haziran 2026
# Degisiklikler (v416 -> v417):
#   1. YENI: Fibonacci olta güven skoru — her TF satırına eklendi
#      Kriterler: R:R oranı, giriş Fib seviyesine yakınlık,
#                 fiyata uzaklık (ulaşılabilirlik), TP2 Fib desteği
#      ⭐ 80+  ✅ 60+  ⚠️ 40+  ❌ <40
#      Örnek: "5dk  69.890 69.699 70.334 70.506  ⭐85"
# bot_v416 — 2 Haziran 2026
# Degisiklikler (v415 -> v416):
#   1. BUG FIX: _olta_sorgula fonksiyon tanimi eksikti — "name not defined" hatasi
#   2. BUG FIX: Short/Long TP seviyeleri farkli TF'lerde ayni cikiyordu
#      Kisa lookback (5m=20 15m=30 1h=40 4h=30 1d=20) — her TF kendi swing'ini alir
#      TP: once Fib seviyesi, yoksa TF'e ozgu yuzde adimi
#      5dk=%1.2/%2.2 | 15dk=%1.8/%3.2 | 1s=%3/%5.5 | 4s=%5.5/%9.5 | Gun=%10/%17
#      Kisa TF kucuk hedef, uzun TF buyuk hedef — her satir farkli ve anlamli
# bot_v415 — 2 Haziran 2026
# Degisiklikler (v414 -> v415):
#   0. BUG FIX: _olta_sorgula fonksiyon tanimi eksikti (def satiri silindi)
#      "BTC" yazinca "name not defined" hatasi veriyordu — duzeltildi
#   6. BUG FIX: Short/Long TP seviyeleri farkli TF'lerde ayni cikiyordu
#      Kisa lookback (5m=20 15m=30 1h=40 4h=30 1d=20) ile TF bağımsız swing
#      TP: once Fib seviyesi, yoksa TF'e ozgu yuzde: 5m=%1.2/%2.2 ... 1d=%10/%17
#      Boylece kisa TF kucuk, uzun TF buyuk hedefler verir
#      "BTC" yazinca "name not defined" hatasi veriyordu — duzeltildi
#   1. TOPIC_OLTA iki mod:
#      "BTC"     → eski 15dk EMA/destek tabanlı olta (tek mesaj, v409 sistemi)
#      "BTC TUM" → Fibonacci multi-TF olta (5dk/15dk/1s/4s/Gun, Long+Short 2 mesaj)
#   2. BUG FIX: _olta_fib_hesapla long/short yön hatası
#      Long girisi MUTLAKA fiyatin ALTINDA, Short girisi MUTLAKA USTUNDE
#   3. BUG FIX: Farkli TF'lerde ayni veri cikiyordu
#      Her TF farkli lookback: 5m=30 15m=50 1h=60 4h=45 1d=30
#      Minimum range kontrolu eklendi (rng < fiyat*0.002 ise None)
#   4. BUG FIX: SL seviyesi girisle esit veya yanlis tarafta olabiliyordu
#      Minimum mesafe garanti: SL = rng*0.015 uzakliktan sonraki Fib
#   5. Format: Telegram monospace uyumlu 33 karakter — TP2 alta kaymiyor
#      BTC ve ETH icin ayni genislik (6 char/sutun)
# bot_v414 — 1 Haziran 2026
# Degisiklikler (v413 -> v414):
#   1. BUG FIX: Deploy sonrasi AUTO_TRADE ve PNL_RAPOR durumu sifirlaniyor
#      Onceki: AUTO_TRADE env variable'dan, PNL_RAPOR hardcode True okunuyordu
#      Simdi: /data/bot_durum.json dosyasina kaydedilir, deploy sonrasi korunur
#      Dosya yoksa guvenli default: AUTO_TRADE=False, PNL_RAPOR=False
#      /trade_ac, /trade_kapat, /pnl_ac, /pnl_kapat komutlari durum dosyasini gunceller
# bot_v413 — 1 Haziran 2026
# Degisiklikler (v412 -> v413):
#   1. BUG FIX: Whitelist bypass hatasi duzeltildi (XRP/DOT yetkisiz islem olayi)
#      Onceki: aktif_pozisyonlar dict'i + API ikisi kontrol ediliyordu
#              Baslangicta yuklenen eski HEDGE kayitlari whitelist'i atliyordu
#      Simdi: SADECE API'den gelen gercek acik pozisyon ters yondeyse hedge muafiyeti
#             aktif_pozisyonlar dict'i whitelist bypass icin kullanilmiyor
# bot_v412 — 1 Haziran 2026
# Degisiklikler (v411 -> v412):
#   1. TOPIC_OLTA: Multi-TF Fibonacci olta tablosu (5dk/15dk/1s/4s/Gun)
#      Kullanici parite yazinca Long icin ayri, Short icin ayri 2 mesaj gelir
#      Her TF icin Fibonacci seviyeleri: %38.2/%50/%61.8/%78.6/%100/%127.2/%161.8
#      Giris/Stop/TP1/TP2 — mobil uyumlu <pre> tablo formatinda
# Degisiklikler (v410 -> v411):
#   1. PNL_RAPOR_ENABLED flag eklendi — 15 dakikalık otomatik PNL raporunu açıp kapatır
#   2. /pnl_kapat komutu — sadece MEXC_NOTIFY_CHAT_ID kanalından çalışır, raporu durdurur
#   3. /pnl_ac komutu — sadece MEXC_NOTIFY_CHAT_ID kanalından çalışır, raporu başlatır
# bot_v410 — 31 Mayis 2026
# Degisiklikler (v409 -> v410):
#   1. mexc_update_tpsl — avg_price alindiginda TP karlilik kontrolu eklendi
#      TP avg_price'a gore karsit yonde veya esitse guncelleme yapilmaz,
#      mevcut stop order'a dokunulmaz, bildirim gonderilmez (False dondurilir)
# bot_v409 — 31 Mayis 2025
# Degisiklikler (v408 -> v409):
#   1. Unrealized PNL % — toplam USDT / kullanilan marjin (onceki: profitRatio toplami yanlistı)
# bot_v408 — 31 Mayis 2025
# Degisiklikler (v407 -> v408):
#   1. Senaryo 2a/2 — if/elif zincirine donusturuldu, cift mesaj sorunu giderildi
#      (Onceki: if+if ayri bloklar, her ikisi de tetikleniyordu)
# bot_v407 — 31 Mayis 2025
# Degisiklikler (v406 -> v407):
#   1. PNL raporu zamanlayicisi — 15 dakikada bir (onceki: her saatin :15'inde)
# bot_v406 — 31 Mayis 2025
# Degisiklikler (v405 -> v406):
#   1. PNL raporu zamanlayicisi — her saatin :15'inde (onceki: 05:59/11:59/17:59/23:59)
#   2. Gece sifirlama 00:15'e tasindi (onceki: 23:59 sonrasi)
# bot_v405 — 31 Mayis 2025
# Degisiklikler (v404 -> v405):
#   1. Unrealized PNL — open_positions profitRatio*im toplami (% + USDT)
#   2. _wl_hedge — aktif_pozisyonlar dict'i de kontrol ediliyor (sadece API degil)
#   3. Senaryo 3/D — mevcut pozisyon kontrolunden SONRA TP1 gecildi kontrolu
#   4. Senaryo 2 — acik HEDGE varsa yeni hedge acma, revize et
# bot_v404 — 31 Mayis 2025
# Degisiklikler (v402 -> v404):
#   1. Senaryo 4 — tp1_karlilik_kontrol'e hedge_fallback=True eklendi (TP5 gecemezse TP1-TP4'e duser)
#   2. Senaryo 4 — zarar kontrolunde anlık mp yerine pozisyon giris fiyati (mark_price) kullanılıyor
#   3. Senaryo E — pozisyon kaydına mark_price eklendi (Senaryo 4 zarar kontrolu icin)
#   4. tp1_karlilik_kontrol yeniden yazildi — sira TP1→TP2→TP3→TP4→TP5 (en yakin karli TP secilir, TP5 son care)
#   5. Senaryo 3/D — TP1 zaten gecilmisse artık mexc_notify bildirimi gidiyor
#   6. TOPIC_ALARM — tum bildirimlere ayrac eklendi
#   7. TELEGRAM_KANAL_ID — foto ve metin caption'larina ayrac eklendi
# Degisiklikler (v172 -> v173):
#   1. Proxy geri eklendi — SADECE private API istekleri icin (IPRoyal)
#   2. Public istekler (mark price, ticker, contract detail) direkt gidiyor
# Degisiklikler (v171 -> v172):
#   1. MEXC blogu detayli loglama — her adim izleniyor
#   2. mexc_place_order icinde tam traceback basiliyor
#   3. MEXC webhook exception handler traceback ile guclendirildi
#   4. /myip endpoint eklendi
# Degisiklikler (v164 -> v171):
#   1. MEXC_PROXY kaldirildi — Railway'den direkt MEXC baglantisi
#   2. mexc_sign() duzeltildi — GET istekleri icin body="" bos string kullaniliyor
#   3. mexc_headers(body_dict=None) GET cagrisi icin varsayilan None eklendi
#   4. mexc_place_order() olü kod blogu temizlendi
#   5. mexc_update_tpsl() ve mexc_pozisyon_sorgula() mexc_headers() ile eslesti
#   6. _gunluk_pnl_gonder() mexc_headers() kullanacak sekilde duzeltildi
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
TELEGRAM_KANAL_ID = os.getenv("TELEGRAM_KANAL_ID", "")  # Eski alarm kanalı
TELEGRAM_LOG_ID  = os.getenv("TELEGRAM_LOG_ID", "")
CHARTIMG_KEY     = os.getenv("CHARTIMG_KEY", "")
KANAL_ADI        = os.getenv("KANAL_ADI", "BEN KÜL YUTMAM")
KANAL_TAG        = os.getenv("KANAL_TAG", "@dayiscalper")

# ==========================================
# TELEGRAM GRUP + TOPIC AYARLARI
# ==========================================
TELEGRAM_GRUP_ID  = os.getenv("TELEGRAM_GRUP_ID", "")
TOPIC_ALARM       = int(os.getenv("TOPIC_ALARM",   "2"))
TOPIC_ANALIZ      = int(os.getenv("TOPIC_ANALIZ",  "3"))
TOPIC_YUKSELENLER = int(os.getenv("TOPIC_YUKSELENLER", "5"))
TOPIC_RAPOR       = int(os.getenv("TOPIC_RAPOR",   "6"))
TOPIC_HABER       = int(os.getenv("TOPIC_HABER",   "287")) # 📰 Haberler & Analiz
TOPIC_BALINA      = int(os.getenv("TOPIC_BALINA",  "393")) # 🐋 Balina Cüzdan Takibi
TOPIC_OLTA        = int(os.getenv("TOPIC_OLTA",    "0"))   # 🎣 Parite Olta Sorgulama

# ==========================================
# GEÇMİŞ BREAKOUT ENVANTERİ
# ==========================================
# Her olay: ad, tarih, yon (yukari/asagi), hareket_pct, sure_gun,
#           kosullar: funding_min, funding_max, oi_yon (+/-), cvd_uyum (uyumlu/uyumsuz_yukari/uyumsuz_asagi), lik_taraf (long/short/dengeli)
BREAKOUT_ENVANTER = [
    {
        "ad": "FTX Çöküşü",
        "tarih": "Kas 2022",
        "yon": "asagi",
        "hareket_pct": -28,
        "sure_gun": 3,
        "kosullar": {
            "funding_min": 0.03,
            "funding_max": 0.06,
            "oi_yon": "+",
            "cvd_uyum": "uyumsuz_yukari",
            "lik_taraf": "long",
            "fear_greed": "extreme_fear",
            "breadth": "dar",
        }
    },
    {
        "ad": "LUNA Çöküşü",
        "tarih": "May 2022",
        "yon": "asagi",
        "hareket_pct": -35,
        "sure_gun": 5,
        "kosullar": {
            "funding_min": 0.02,
            "funding_max": 0.05,
            "oi_yon": "+",
            "cvd_uyum": "uyumsuz_yukari",
            "lik_taraf": "long",
            "fear_greed": "extreme_fear",
            "breadth": "dar",
        }
    },
    {
        "ad": "Covid Paniği",
        "tarih": "Mar 2020",
        "yon": "asagi",
        "hareket_pct": -50,
        "sure_gun": 4,
        "kosullar": {
            "funding_min": -0.02,
            "funding_max": 0.01,
            "oi_yon": "-",
            "cvd_uyum": "uyumsuz_asagi",
            "lik_taraf": "long",
            "fear_greed": "extreme_fear",
            "breadth": "dar",
        }
    },
    {
        "ad": "China Mining Yasağı",
        "tarih": "May 2021",
        "yon": "asagi",
        "hareket_pct": -30,
        "sure_gun": 7,
        "kosullar": {
            "funding_min": 0.02,
            "funding_max": 0.08,
            "oi_yon": "+",
            "cvd_uyum": "uyumsuz_yukari",
            "lik_taraf": "long",
            "fear_greed": "extreme_fear",
            "breadth": "dar",
        }
    },
    {
        "ad": "2022 Bear Dip Birikim",
        "tarih": "Haz 2022",
        "yon": "asagi",
        "hareket_pct": -38,
        "sure_gun": 10,
        "kosullar": {
            "funding_min": -0.01,
            "funding_max": 0.01,
            "oi_yon": "-",
            "cvd_uyum": "uyumlu",
            "lik_taraf": "long",
            "fear_greed": "extreme_fear",
            "breadth": "dar",
        }
    },
    {
        "ad": "ETF Onayı Öncesi Rallisi",
        "tarih": "Eki 2023",
        "yon": "yukari",
        "hareket_pct": 40,
        "sure_gun": 10,
        "kosullar": {
            "funding_min": -0.02,
            "funding_max": 0.01,
            "oi_yon": "+",
            "cvd_uyum": "uyumlu",
            "lik_taraf": "short",
            "fear_greed": "normal",
            "breadth": "genis",
        }
    },
    {
        "ad": "Kurumsal Alım Rallisi",
        "tarih": "Şub 2021",
        "yon": "yukari",
        "hareket_pct": 60,
        "sure_gun": 14,
        "kosullar": {
            "funding_min": 0.01,
            "funding_max": 0.04,
            "oi_yon": "+",
            "cvd_uyum": "uyumlu",
            "lik_taraf": "short",
            "fear_greed": "acgozluluk",
            "breadth": "genis",
        }
    },
    {
        "ad": "Short Squeeze Rallisi",
        "tarih": "Oca 2023",
        "yon": "yukari",
        "hareket_pct": 25,
        "sure_gun": 5,
        "kosullar": {
            "funding_min": -0.03,
            "funding_max": -0.01,
            "oi_yon": "-",
            "cvd_uyum": "uyumlu",
            "lik_taraf": "short",
            "fear_greed": "korku",
            "breadth": "orta",
        }
    },
    {
        "ad": "Halving Öncesi Rallisi",
        "tarih": "Nis 2024",
        "yon": "yukari",
        "hareket_pct": 35,
        "sure_gun": 12,
        "kosullar": {
            "funding_min": 0.01,
            "funding_max": 0.05,
            "oi_yon": "+",
            "cvd_uyum": "uyumlu",
            "lik_taraf": "dengeli",
            "fear_greed": "acgozluluk",
            "breadth": "genis",
        }
    },
]


# Fear & Greed → kategori dönüşümü
def _fg_kategori(fg_deger):
    """Fear & Greed sayısal değerini kategoriye çevirir."""
    if fg_deger is None:
        return None
    if fg_deger <= 25:
        return "extreme_fear"
    elif fg_deger <= 45:
        return "korku"
    elif fg_deger <= 55:
        return "normal"
    elif fg_deger <= 75:
        return "acgozluluk"
    else:
        return "extreme_greed"

# Breadth → kategori dönüşümü
def _breadth_kategori(ema_ustunde_sayi, toplam_coin=10):
    """EMA üstündeki coin sayısını breadth kategorisine çevirir."""
    oran = ema_ustunde_sayi / max(toplam_coin, 1)
    if oran <= 0.3:
        return "dar"
    elif oran <= 0.6:
        return "orta"
    else:
        return "genis"

def _breakout_benzerlik_hesapla(btc_fund, oi_delta_pct, cvd_uyum_str, lik_taraf_str,
                                 fg_deger=None, breadth_sayi=None, toplam_coin=10):
    """
    Mevcut piyasa koşullarını BREAKOUT_ENVANTER ile karşılaştırır.
    6 kriter, her biri ~16-17 puan → toplam 100 üzerinden skor.
    5-6 kriter tutuyorsa KRİTİK UYARI verilir.

    Kriterler:
      1) Funding aralığı  (~17p)
      2) OI yönü          (~17p)
      3) CVD uyum         (~17p)
      4) Likidasyon tarafı (~17p)
      5) Fear & Greed     (~16p)
      6) Breadth          (~16p)
    """
    # Puan ağırlıkları — F&G ve Breadth artırıldı (toplam 100)
    W_FUND   = 12
    W_OI     = 12
    W_CVD    = 12
    W_LIK    = 12
    W_FG     = 26   # F&G en kritik — extreme_fear yükseliş senaryosuyla eşleşmemeli
    W_BREAD  = 26   # Breadth en kritik — dar breadth yükseliş senaryosuyla eşleşmemeli

    mevcut_fg     = _fg_kategori(fg_deger)
    mevcut_breadth = _breadth_kategori(breadth_sayi if breadth_sayi is not None else 0, toplam_coin)
    mevcut_oi_yon  = "+" if oi_delta_pct >= 0 else "-"

    sonuclar = []
    for olay in BREAKOUT_ENVANTER:
        k = olay["kosullar"]
        puan = 0
        eslesme_sayisi = 0  # kaç kriter tam eşleşti

        # 1) Funding aralığı uyumu
        if k["funding_min"] <= btc_fund <= k["funding_max"]:
            puan += W_FUND
            eslesme_sayisi += 1
        else:
            dist = min(abs(btc_fund - k["funding_min"]), abs(btc_fund - k["funding_max"]))
            kismi = max(0, W_FUND - int(dist * 340))  # 0.05 fark ≈ 17p kayıp
            puan += kismi
            if kismi >= W_FUND * 0.7:
                eslesme_sayisi += 0.5  # kısmi eşleşme

        # 2) OI yönü uyumu
        if mevcut_oi_yon == k["oi_yon"]:
            puan += W_OI
            eslesme_sayisi += 1

        # 3) CVD uyum uyumu
        if cvd_uyum_str == k["cvd_uyum"]:
            puan += W_CVD
            eslesme_sayisi += 1

        # 4) Likidasyon tarafı uyumu
        if lik_taraf_str == k["lik_taraf"]:
            puan += W_LIK
            eslesme_sayisi += 1
        elif k["lik_taraf"] == "dengeli":
            puan += W_LIK // 2
            eslesme_sayisi += 0.5

        # 5) Fear & Greed uyumu
        if mevcut_fg and mevcut_fg == k.get("fear_greed"):
            puan += W_FG
            eslesme_sayisi += 1
        elif mevcut_fg and k.get("fear_greed"):
            # Komşu kategoriler için kısmi puan
            fg_sirasi = ["extreme_fear", "korku", "normal", "acgozluluk", "extreme_greed"]
            try:
                fark = abs(fg_sirasi.index(mevcut_fg) - fg_sirasi.index(k["fear_greed"]))
                if fark == 1:
                    puan += W_FG // 2
                    eslesme_sayisi += 0.5
            except ValueError:
                pass

        # 6) Breadth uyumu
        if mevcut_breadth == k.get("breadth"):
            puan += W_BREAD
            eslesme_sayisi += 1
        elif k.get("breadth") == "orta":
            puan += W_BREAD // 2  # "orta" her iki yöne yakın
            eslesme_sayisi += 0.5

        sonuclar.append((puan, eslesme_sayisi, olay))

    # Puana göre sırala, en yüksek 3'ü döndür
    sonuclar.sort(key=lambda x: (-x[0], -x[1]))
    return sonuclar[:3]

# ==========================================
# FİLİGRAN
# ==========================================

# Watermark doğrudan gömülü — ayrı dosya gerekmez
_WATERMARK_B64 = "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"

def _watermark_yukle():
    print("[FILIGRAN] Watermark gomulu olarak yuklendi.")


def filigran_ekle(img_bytes, alpha=0.35, boyut_oran=0.45):
    """PNG bytes üzerine merkeze şeffaf Zenginler Kulübü filigranı ekle."""
    if not _WATERMARK_B64:
        return img_bytes
    try:
        from PIL import Image
        ana  = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        w, h = ana.size
        wm   = Image.open(io.BytesIO(base64.b64decode(_WATERMARK_B64))).convert("RGBA")

        # Boyutlandır
        wm_w = int(w * boyut_oran)
        wm_h = int(wm_w * wm.size[1] / wm.size[0])
        wm   = wm.resize((wm_w, wm_h), Image.LANCZOS)

        # Şeffaflık uygula
        r2, g2, b2, a2 = wm.split()
        a2 = a2.point(lambda x: int(x * alpha))
        wm.putalpha(a2)

        # Ortaya yerleştir
        overlay = Image.new("RGBA", ana.size, (0, 0, 0, 0))
        overlay.paste(wm, ((w - wm_w) // 2, (h - wm_h) // 2))
        result = Image.alpha_composite(ana, overlay).convert("RGB")

        buf = io.BytesIO()
        result.save(buf, "PNG", dpi=(150, 150))
        return buf.getvalue()
    except Exception as e:
        print(f"[FILIGRAN] Hata: {e}")
        return img_bytes

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

# ── PNL Kayıt Sistemi ──
# {gun: [{symbol, sinyal, giris, cikis, tp_label, pnl_usdt, pnl_pct, zaman, message_id}]}
_pnl_kayitlar      = {}   # gün bazlı kümülatif işlem kayıtları
_pnl_kilit         = threading.Lock()
_pnl_baslangic_bak = {}   # {gun: bakiye} — gün başı bakiyesi (% hesabı için)
VERI_DOSYASI     = os.getenv("VERI_DOSYASI", "/data/sinyaller.json")
POZISYON_DOSYASI = os.getenv("POZISYON_DOSYASI", "/data/pozisyonlar.json")

# ==========================================
# MEXC FUTURES AYARLARI
# ==========================================
MEXC_API_KEY       = os.getenv("MEXC_API_KEY", "")
MEXC_API_SECRET    = os.getenv("MEXC_API_SECRET", "")
# MEXC bildirimleri MEXC_NOTIFY_CHAT_ID'ye gidiyor (topic degil, direkt kanal/grup)
# Sabit hedef: -1003990949543 — env ile override edilebilir
MEXC_NOTIFY_CHAT_ID  = os.getenv("MEXC_NOTIFY_CHAT_ID", "-1003990949543")
MEXC_MAX_MARGIN_PCT  = float(os.getenv("MEXC_MAX_MARGIN_PCT", "20"))  # Maksimum margin ratio %
MEXC_MARGIN_USDT        = float(os.getenv("MEXC_MARGIN_USDT", "0.25"))
HEDGE_MARGIN_MULTIPLIER = 2.0  # Hedge marjin çarpanı — hedge_margin_max = MEXC_MARGIN_USDT × bu değer
MEXC_LEVERAGE      = int(os.getenv("MEXC_LEVERAGE", "0"))   # 0 = sınırsız (max kullan), >0 = üst limit
MEXC_BASE_URL      = "https://futures.mexc.com"
MEXC_BASE_URL_ALT  = "https://contract.mexc.com"
MEXC_WEB_KEY       = os.getenv("MEXC_WEB_KEY", "")  # Tarayici session key (WEB...)
# AUTO_TRADE ve PNL_RAPOR durumu /data/bot_durum.json'dan okunur
# Deploy sonrasi sifirlanmaz — /trade_ac veya /pnl_ac komutu gerekir
# Dosya yoksa GUVENLI DEFAULT: her ikisi de KAPALI
AUTO_TRADE_ENABLED = False
PNL_RAPOR_ENABLED  = False

# Proxy ayarlari
_proxy_user = os.getenv("IPROYAL_USER", "")
_proxy_pass = os.getenv("IPROYAL_PASS", "")
_proxy_host = "geo.iproyal.com"
_proxy_port = "12321"

# Binance icin IPRoyal proxy (Railway Binance'e erisemiyor)
if _proxy_user and _proxy_pass:
    BINANCE_PROXY = {
        "http":  f"http://{_proxy_user}:{_proxy_pass}@{_proxy_host}:{_proxy_port}",
        "https": f"http://{_proxy_user}:{_proxy_pass}@{_proxy_host}:{_proxy_port}",
    }
    print(f"[PROXY] Binance proxy aktif: {_proxy_host}:{_proxy_port}")
else:
    BINANCE_PROXY = None
    print(f"[PROXY] Binance proxy devre disi")

# MEXC — proxy YOK, direkt Railway IP + browser headers ile WAF bypass
MEXC_PRIVATE_PROXY = None
print(f"[PROXY] MEXC_PRIVATE_PROXY aktif: False (WAF bypass modu)")
print(f"[PROXY] User uzunlugu: {len(_proxy_user)} Pass uzunlugu: {len(_proxy_pass)}")

# Aktif pozisyon takibi
# Son olta sorgu cache — /skor icin
_son_olta_cache = {}  # {topic_id: parsed_olta_dict}
_OLTA_CACHE_DOSYASI = "/data/son_olta_cache.json"


def _olta_cache_kaydet():
    """Cache'i diske yaz — deploy sonrasi korunsun."""
    try:
        import json as _json
        # Dict key'leri int olabilir, str'e cevir
        kayit = {}
        for k, v in _son_olta_cache.items():
            kayit[str(k)] = v
        with open(_OLTA_CACHE_DOSYASI, "w", encoding="utf-8") as f:
            _json.dump(kayit, f, ensure_ascii=False)
        print(f"[OLTA] Cache diske kaydedildi: {len(kayit)} topic")
    except Exception as e:
        print(f"[OLTA] Cache kayit hatasi: {e}")


def _olta_cache_yukle():
    """Startup'ta cache'i diskten yukle."""
    global _son_olta_cache
    try:
        import json as _json, os as _os
        if _os.path.exists(_OLTA_CACHE_DOSYASI):
            with open(_OLTA_CACHE_DOSYASI, "r", encoding="utf-8") as f:
                kayit = _json.load(f)
            # Key'leri int'e cevir (TOPIC_OLTA int)
            _son_olta_cache = {}
            for k, v in kayit.items():
                try:
                    _son_olta_cache[int(k)] = v
                except Exception:
                    _son_olta_cache[k] = v
            for k, v in _son_olta_cache.items():
                ts_val = v.get("ts")
                fmt_val = v.get("format", "?")
                print(f"[OLTA] Cache topic={k} format={fmt_val} ts={ts_val}")
            print(f"[OLTA] Cache diskten yuklendi: {len(_son_olta_cache)} topic")
        else:
            print("[OLTA] Cache dosyasi yok — bos baslatildi")
    except Exception as e:
        print(f"[OLTA] Cache yukle hatasi: {e}")

aktif_pozisyonlar = {}
pozisyon_kilit    = threading.Lock()

# Saatlik koin başarı sıralaması — top 3 her zaman işlem açabilir
top3_whitelist    = []  # ["BTC", "ETH", "LINK"] gibi
top3_kilit        = threading.Lock()

# Whitelist eşik yüzdesi — bu değeri istediğiniz gibi değiştirebilirsiniz
TRADE_WHITELIST_MIN_PERCENT = 70.0




# ==========================================
# MEXC FUTURES FONKSİYONLARI
# ==========================================

def pozisyon_kaydet():
    try:
        os.makedirs(os.path.dirname(POZISYON_DOSYASI), exist_ok=True)
        with pozisyon_kilit:
            veri = dict(aktif_pozisyonlar)
        with open(POZISYON_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False)
        print(f"[POZISYON] {len(veri)} pozisyon kaydedildi.")
    except Exception as e:
        print(f"[POZISYON KAYIT] Hata: {e}")


def pozisyon_yukle():
    global aktif_pozisyonlar
    try:
        if os.path.exists(POZISYON_DOSYASI):
            with open(POZISYON_DOSYASI, "r", encoding="utf-8") as f:
                veri = json.load(f)
            with pozisyon_kilit:
                aktif_pozisyonlar.update(veri)
            print(f"[POZISYON] {len(veri)} pozisyon yuklendi: {list(veri.keys())}")
        else:
            print("[POZISYON] Pozisyon dosyasi yok, bos baslatildi.")
    except Exception as e:
        print(f"[POZISYON YUKLE] Hata: {e}")


BOT_DURUM_DOSYASI = "/data/bot_durum.json"

def bot_durum_kaydet():
    """AUTO_TRADE ve PNL_RAPOR durumunu /data/bot_durum.json'a yazar."""
    try:
        os.makedirs(os.path.dirname(BOT_DURUM_DOSYASI), exist_ok=True)
        durum = {
            "auto_trade": AUTO_TRADE_ENABLED,
            "pnl_rapor":  PNL_RAPOR_ENABLED,
        }
        with open(BOT_DURUM_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False)
        print(f"[DURUM] Kaydedildi: auto_trade={AUTO_TRADE_ENABLED} pnl_rapor={PNL_RAPOR_ENABLED}")
    except Exception as e:
        print(f"[DURUM] Kayit hatasi: {e}")


def bot_durum_yukle():
    """Deploy sonrasi AUTO_TRADE ve PNL_RAPOR durumunu geri yukler.
    Dosya yoksa guvenli default: her ikisi de False (kapali)."""
    global AUTO_TRADE_ENABLED, PNL_RAPOR_ENABLED
    try:
        if os.path.exists(BOT_DURUM_DOSYASI):
            with open(BOT_DURUM_DOSYASI, "r", encoding="utf-8") as f:
                durum = json.load(f)
            AUTO_TRADE_ENABLED = bool(durum.get("auto_trade", False))
            PNL_RAPOR_ENABLED  = bool(durum.get("pnl_rapor",  False))
            print(f"[DURUM] Yuklendi: auto_trade={AUTO_TRADE_ENABLED} pnl_rapor={PNL_RAPOR_ENABLED}")
        else:
            # Ilk calistirma — guvenli default
            AUTO_TRADE_ENABLED = False
            PNL_RAPOR_ENABLED  = False
            print("[DURUM] Durum dosyasi yok — guvenli default: auto_trade=False pnl_rapor=False")
    except Exception as e:
        print(f"[DURUM] Yukle hatasi: {e} — guvenli default kullaniliyor")
        AUTO_TRADE_ENABLED = False
        PNL_RAPOR_ENABLED  = False


def mexc_format_symbol(symbol):
    sym = symbol.upper().replace(".P", "")
    if sym.endswith("USDT") and "_" not in sym:
        return sym[:-4] + "_USDT"
    return sym


def mexc_get_contract_info(symbol):
    """Mark price, max leverage ve vol precision'i tek API cagrisinda al"""
    sym = mexc_format_symbol(symbol)
    try:
        r = requests.get(f"{MEXC_BASE_URL}/api/v1/contract/detail",
                         params={"symbol": sym}, timeout=10)
        print(f"[MEXC] mark_price status:{r.status_code} raw:{r.text[:300]}")
        d = r.json()
        if d.get("success"):
            data = d["data"]
            mp = 0
            for field in ["fairPrice", "lastPrice", "indexPrice", "markPrice", "price"]:
                val = data.get(field)
                if val and float(val) > 0:
                    mp = float(val)
                    break
            lev = int(data.get("maxLeverage", 20))
            vol_decimals = int(data.get("volDecimalPlaces", 4))
            contract_size = float(data.get("contractSize", 1))
            max_vol = float(data.get("maxVol", 0))  # Maksimum kontrat adedi
            print(f"[MEXC] Contract fields: fairPrice={data.get('fairPrice')} lastPrice={data.get('lastPrice')} maxLev={lev} volDec={vol_decimals} maxVol={max_vol} RAW_KEYS={list(data.keys())[:15]}")
            if mp > 0:
                return mp, lev, vol_decimals, contract_size, max_vol
            else:
                # mp gelmedi ama diger alanlar dogru — fallback mp al, lev/size koru
                mp_fallback = get_mexc_price(symbol)
                print(f"[MEXC] mp fallback kullanildi: {mp_fallback}, lev={lev}, contract_size={contract_size}")
                return mp_fallback, lev, vol_decimals, contract_size, max_vol
    except Exception as e:
        print(f"[MEXC] Contract info hatasi: {e}")
    mp_fallback = get_mexc_price(symbol)
    return mp_fallback, 20, 4, 1, 0


def mexc_get_mark_price(symbol):
    sym = mexc_format_symbol(symbol)
    try:
        r = requests.get(f"{MEXC_BASE_URL}/api/v1/contract/detail",
                         params={"symbol": sym}, timeout=10)
        print(f"[MEXC] mark_price status:{r.status_code} raw:{r.text[:300]}")
        d = r.json()
        if d.get("success"):
            p = float(d["data"].get("fairPrice", 0))
            if p > 0:
                return p
    except Exception as e:
        print(f"[MEXC] Mark price hatasi: {e}")
    return get_mexc_price(symbol)


def mexc_get_max_leverage(symbol):
    sym = mexc_format_symbol(symbol)
    try:
        r = requests.get(f"{MEXC_BASE_URL}/api/v1/contract/detail",
                         params={"symbol": sym}, timeout=10)
        d = r.json()
        if d.get("success"):
            return int(d["data"].get("maxLeverage", 20))
    except Exception as e:
        print(f"[MEXC] Leverage sorgu hatasi: {e}")
    return 20


def mexc_sign(body_dict, ts):
    # GET icin: bos string
    # POST icin: JSON body string (MEXC dokumantasyonu)
    if body_dict:
        body_str = json.dumps(body_dict, separators=(",", ":"), ensure_ascii=False,
                              sort_keys=True)
    else:
        body_str = ""
    sign_str = MEXC_API_KEY + ts + body_str
    return hmac.new(
        MEXC_API_SECRET.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def mexc_headers(body_dict=None):
    ts = str(int(time.time() * 1000))
    return {"ApiKey": MEXC_API_KEY, "Request-Time": ts,
            "Signature": mexc_sign(body_dict, ts),
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://futures.mexc.com",
            "Referer": "https://futures.mexc.com/exchange/BTC_USDT"}, ts


def mexc_private_get(url, params=None, timeout=10):
    """Private GET — query string parametrelerini imzaya dahil et"""
    ts = str(int(time.time() * 1000))
    # MEXC GET imzasi: ApiKey + ts + sorted query string
    if params:
        sorted_params = dict(sorted(params.items()))
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params.items())
    else:
        param_str = ""
    sign_str = MEXC_API_KEY + ts + param_str
    sig = hmac.new(
        MEXC_API_SECRET.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    hdrs = {
        "ApiKey": MEXC_API_KEY,
        "Request-Time": ts,
        "Signature": sig,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://futures.mexc.com",
        "Referer": "https://futures.mexc.com/exchange/BTC_USDT",
    }
    return requests.get(url, headers=hdrs, params=params,
                        timeout=timeout, proxies=MEXC_PRIVATE_PROXY)


def mexc_private_post(url, body, timeout=15):
    """Private POST - json=sorted_body + browser headers ile WAF bypass
    IP whitelist bos, imza compact JSON formatinda
    """
    ts = str(int(time.time() * 1000))
    sorted_body = dict(sorted(body.items()))
    body_json = json.dumps(sorted_body, separators=(",", ":"), ensure_ascii=False)
    sign_str = MEXC_API_KEY + ts + body_json
    sig = hmac.new(MEXC_API_SECRET.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256).hexdigest()
    print(f"[MEXC IMZA] body_json: {body_json[:100]}")
    print(f"[MEXC IMZA] sig: {sig[:20]}...")
    hdrs = {
        "ApiKey": MEXC_API_KEY,
        "Request-Time": ts,
        "Signature": sig,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://futures.mexc.com",
        "Referer": "https://futures.mexc.com/exchange/BTC_USDT",
    }
    # data=body_json: imza ile ayni string gonderilir (bosluksuz compact JSON)
    r = requests.post(url, headers=hdrs, data=body_json, timeout=timeout)
    print(f"[MEXC POST] Status: {r.status_code} Body: {r.text[:150]}")
    return r


def mexc_notify(symbol, sinyal, vol=0, leverage=0, margin=0,
                order_id="", tp1=None, sl=None, mark_price=None,
                hata_msg=None, bilgi_msg=None):
    yon   = "LONG" if any(x in sinyal.upper() for x in ["BUY","LONG"]) else "SHORT"
    emoji = "🟢" if yon == "LONG" else "🔴"
    if bilgi_msg:
        metin = emoji + " <b>" + symbol + "</b> | " + yon + "\n\n" + str(bilgi_msg)
    elif hata_msg:
        metin = "\u26a0\ufe0f <b>MEXC Islem ACILAMADI</b>\n\n" + emoji + " " + symbol + " | " + yon + "\nHata: " + str(hata_msg)
    else:
        parts = [f"✅ <b>MEXC Islem ACILDI</b>", "",
                 f"{emoji} {symbol} | {yon}",
                 f"Giris (Mark Price): {mark_price}",
                 f"Lot: {vol} | Kaldirac: {leverage}x | Marjin: ${margin} USDT"]
        if tp1:
            parts.append(f"TP1: {tp1} (Mark Price)")
        if sl:
            parts.append(f"SL: {sl} (Mark Price)")
        parts.append(f"Order ID: <code>{order_id}</code>")
        metin = "\n".join(parts)
    try:
        r = _mexc_topic_mesaj_gonder(metin)
        if r and r.status_code == 200:
            mid = r.json().get("result", {}).get("message_id")
            print(f"[MEXC BILDIRIM] message_id={mid}")
            return mid
    except Exception as e:
        print(f"[MEXC BILDIRIM] Hata: {e}")
    return None


def mexc_margin_ratio_kontrol():
    """Hesap margin ratio'sunu kontrol et. %20 üzerindeyse True döner (işlem açma)."""
    try:
        r = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/account/assets")
        res = r.json()
        if not res.get("success"):
            return False  # Veri gelmezse bloklama
        assets = res.get("data", [])
        if isinstance(assets, list):
            for asset in assets:
                if asset.get("currency") == "USDT":
                    equity = float(asset.get("equity", 0))
                    position_margin = float(asset.get("positionMargin", 0))
                    if equity > 0:
                        ratio = position_margin / equity * 100
                        print(f"[MEXC] Margin ratio: %{ratio:.1f} (pozisyon={position_margin:.4f} equity={equity:.4f})")
                        if ratio > MEXC_MAX_MARGIN_PCT:
                            print(f"[MEXC] Margin ratio %{MEXC_MAX_MARGIN_PCT:.0f} üzerinde, yeni işlem açılmıyor!")
                            return True
        return False
    except Exception as e:
        print(f"[MEXC] Margin ratio kontrol hatasi: {e}")
        return False  # Hata durumunda bloklama


# Minimum karlı mesafe eşiği — giriş fiyatı ile TP1 arasındaki fark bu oranın
# altındaysa TP1 atlanır, TP2 kullanılır (fee kaybını önlemek için).
# MEXC Futures taker fee ≈ %0.06 açma + %0.06 kapama = %0.12 toplam.
# Güvenlik payıyla %0.15 eşik kullanıyoruz.
MIN_KARLI_MESAFE_PCT = 0.002    # %0.20 — genel eşik

# Coin bazlı özel eşikler — genel eşikten farklı davranması gereken coinler
COIN_KARLI_MESAFE_PCT = {
    "DOTUSDT": 0.004,   # %0.40 — DOT küçük fiyat, fee+slippage oranı yüksek
}


def tp1_karlilik_kontrol(mark_price, tp1, tp2, is_long, tp3=None, tp4=None, tp5=None, symbol=None, hedge_fallback=False):
    """
    Giriş fiyatı (mark_price) ile TP'ler arasındaki mesafeyi sırayla kontrol eder.
    Sıra: TP1 → TP2 → TP3 → TP4 → TP5 (en yakın kârlı TP seçilir)
    TP5 son çare — TP1-TP4 hiçbiri fee eşiğini geçemezse denenir.
    Hiçbiri geçemiyorsa (None, notu) döner → işlem AÇILMAZ.
    hedge_fallback parametresi artık kullanılmıyor (geriye dönük uyumluluk için bırakıldı).

    Dönen: (kullanilacak_tp_veya_None, atlama_notu_veya_None)
    """
    if not mark_price:
        return tp1, None
    try:
        mp_f = float(str(mark_price).replace(",", "."))
        if mp_f <= 0:
            return tp1, None
    except Exception as e:
        print(f"[FEE] mark_price parse hatasi: {e}")
        return tp1, None

    # Coin bazlı eşik — yoksa genel eşik
    sym_key = str(symbol).replace(".P", "").upper() if symbol else ""
    esik = COIN_KARLI_MESAFE_PCT.get(sym_key, MIN_KARLI_MESAFE_PCT)

    # TP1→TP2→TP3→TP4→TP5 sırasıyla en yakın kârlı TP'yi seç
    tp_listesi = [(tp1, "TP1"), (tp2, "TP2"), (tp3, "TP3"), (tp4, "TP4"), (tp5, "TP5")]

    for tp_val, tp_label in tp_listesi:
        if not tp_val or str(tp_val) in ("null", "None", ""):
            continue
        try:
            tp_f = float(str(tp_val).replace(",", "."))
            # Yön kontrolü: LONG için TP > mark_price, SHORT için TP < mark_price
            if is_long and tp_f <= mp_f:
                print(f"[FEE] {tp_label} yön hatası: LONG TP ({tp_f}) <= giriş ({mp_f}) — atlandı")
                continue
            if not is_long and tp_f >= mp_f:
                print(f"[FEE] {tp_label} yön hatası: SHORT TP ({tp_f}) >= giriş ({mp_f}) — atlandı")
                continue
            mesafe_pct = abs(tp_f - mp_f) / mp_f
            print(f"[FEE] {tp_label} mesafe: %{mesafe_pct*100:.3f} (esik: %{esik*100:.2f})")
            if mesafe_pct >= esik:
                if tp_label != "TP1":
                    notu = f"TP1 yetersiz, {tp_label} ({tp_val}) kullanildi"
                    print(f"[FEE] {notu}")
                    return tp_val, notu
                else:
                    return tp_val, None
        except Exception as e:
            print(f"[FEE] {tp_label} parse hatasi: {e}")
            continue

    # Hiçbir TP eşiği geçemedi
    notu = f"Tüm TP'ler çok yakın veya yanlış yönde (mark={mark_price}), işlem açılmıyor"
    print(f"[FEE] {notu}")
    return None, notu


def tp_uzak_sec(mark_price, tp1, tp2, is_long, tp3=None, tp4=None, tp5=None, symbol=None):
    """
    HEDGE işlemler için en UZAK karlı TP'yi seçer.
    Sıra: TP5 → TP4 → TP3 → TP2 → TP1
    Yön kontrolü yapılır, fallback yok — hiçbiri geçemezse None döner.
    """
    if not mark_price:
        return tp1, None
    try:
        mp_f = float(str(mark_price).replace(",", "."))
        if mp_f <= 0:
            return tp1, None
    except:
        return tp1, None

    sym_key = str(symbol).replace(".P", "").upper() if symbol else ""
    # Hedge için eşik yarıya indirilir — RECOVERY pozisyonlarda TP'ler çok yakın olabilir
    esik = COIN_KARLI_MESAFE_PCT.get(sym_key, MIN_KARLI_MESAFE_PCT) * 0.5
    print(f"[HEDGE_TP] esik={esik*100:.4f}% (hedge için {MIN_KARLI_MESAFE_PCT*100:.3f}%'nin yarısı)")

    # En uzaktan en yakına doğru dene
    tp_sirasi = [(tp5, "TP5"), (tp4, "TP4"), (tp3, "TP3"), (tp2, "TP2"), (tp1, "TP1")]

    for tp_val, tp_label in tp_sirasi:
        if not tp_val or str(tp_val) in ("null", "None", ""):
            continue
        try:
            tp_f = float(str(tp_val).replace(",", "."))
            # Yön kontrolü
            if is_long and tp_f <= mp_f:
                print(f"[HEDGE_TP] {tp_label} yön hatası: LONG TP ({tp_f}) <= giriş ({mp_f}) — atlandı")
                continue
            if not is_long and tp_f >= mp_f:
                print(f"[HEDGE_TP] {tp_label} yön hatası: SHORT TP ({tp_f}) >= giriş ({mp_f}) — atlandı")
                continue
            mesafe_pct = abs(tp_f - mp_f) / mp_f
            print(f"[HEDGE_TP] {tp_label} mesafe: %{mesafe_pct*100:.3f} (esik: %{esik*100:.2f})")
            if mesafe_pct >= esik:
                notu = f"HEDGE — en uzak {tp_label} ({tp_val}) kullanıldı"
                print(f"[HEDGE_TP] {notu}")
                return tp_val, notu
        except Exception as e:
            print(f"[HEDGE_TP] {tp_label} parse hatasi: {e}")
            continue

    notu = f"HEDGE — tüm TP'ler yetersiz (mark={mark_price}), işlem açılmıyor"
    print(f"[HEDGE_TP] {notu}")
    return None, notu


def mexc_place_order(symbol, sinyal, tp1=None, sl=None, hedge=False, margin_override=None):
    if not AUTO_TRADE_ENABLED:
        return None
    if not MEXC_API_KEY or not MEXC_API_SECRET:
        return {"success": False, "msg": "MEXC API anahtari tanimli degil"}

    # Margin ratio kontrolü — %20 üzerindeyse yeni işlem açma (HEDGE muaf)
    if not hedge and mexc_margin_ratio_kontrol():
        return {"success": False, "msg": f"Margin ratio %{MEXC_MAX_MARGIN_PCT:.0f} uzerinde, islem atlandı"}

    sym = mexc_format_symbol(symbol)
    is_long = any(x in sinyal.upper() for x in ["BUY", "LONG"])
    # MEXC futures: side=1 long ac, side=3 short ac
    side = 1 if is_long else 3

    mp, lev, vol_decimals, contract_size, max_vol = mexc_get_contract_info(symbol)
    print(f"[MEXC] Mark Price ham: {mp}")
    # Kaldıraç sınırla: env MEXC_LEVERAGE > 0 ise üst limit uygula
    if MEXC_LEVERAGE > 0 and lev > MEXC_LEVERAGE:
        print(f"[MEXC] Leverage {lev} → {MEXC_LEVERAGE} (MEXC_LEVERAGE limiti)")
        lev = MEXC_LEVERAGE
    print(f"[MEXC] Leverage: {lev} | Vol Decimals: {vol_decimals} | Contract Size: {contract_size} | Max Vol: {max_vol}")

    if not mp:
        return {"success": False, "msg": "Mark Price alinamadi"}
    try:
        mp = float(str(mp).replace(",", "."))
    except:
        return {"success": False, "msg": f"Gecersiz Mark Price: {mp}"}

    # Vol hesabi — margin_override varsa onu kullan (hedge 2x marjin), yoksa global
    _efektif_margin = margin_override if margin_override and margin_override > 0 else MEXC_MARGIN_USDT
    notional = _efektif_margin * lev
    vol_raw = notional / (mp * contract_size) if contract_size > 0 else notional / mp
    vol = max(1, int(vol_raw))

    # Max vol limitini kontrol et
    if max_vol > 0 and vol > max_vol:
        vol = max(1, int(max_vol))
        print(f"[MEXC] Vol max limite indirildi: {vol}")

    print(f"[MEXC] Vol hesabi: notional={notional} mp={mp} vol_raw={vol_raw:.4f} -> vol={vol}")

    body = {"symbol": sym, "price": 0, "vol": vol, "side": side, "type": 5, "openType": 2, "leverage": lev}
    # NOT: TP/SL order body'sine eklenmiyor — MEXC 5003 hatası veriyor
    # TP/SL emir açıldıktan sonra mexc_update_tpsl ile ayrıca set ediliyor

    for deneme in range(2):  # max 2 deneme
        try:
            r = mexc_private_post(f"{MEXC_BASE_URL}/api/v1/private/order/create", body)
            print(f"[MEXC] Status: {r.status_code}")
            print(f"[MEXC] Raw: {r.text}")
            if not r.text.strip():
                print(f"[MEXC] Bos yanit, deneme {deneme+1}/2")
                time.sleep(1)
                continue
            res = r.json()
            print(f"[MEXC] Emir yaniti: {res}")
            if res.get("success"):
                tpsl_oim = 0.0
                if tp1 or sl:
                    import time as _time
                    _time.sleep(2)
                    tpsl_sonuc = mexc_update_tpsl(symbol, is_long, tp1, sl)
                    tpsl_ok  = tpsl_sonuc[0] if isinstance(tpsl_sonuc, tuple) else tpsl_sonuc
                    tpsl_oim = tpsl_sonuc[1] if isinstance(tpsl_sonuc, tuple) else 0.0
                    print(f"[MEXC] TP/SL set: {'OK' if tpsl_ok else 'BASARISIZ'} oim={tpsl_oim:.4f}")
                # oim 0 gelirse open_positions'tan çek (gerçek im değeri)
                if tpsl_oim <= 0:
                    try:
                        _r_chk = mexc_private_get(
                            f"{MEXC_BASE_URL}/api/v1/private/position/open_positions",
                            params={"symbol": sym})
                        _poz_list = _r_chk.json().get("data", [])
                        _tip = 1 if is_long else 2
                        for _p in _poz_list:
                            if _p.get("positionType") == _tip:
                                tpsl_oim = float(_p.get("im") or _p.get("oim") or 0)
                                # leverage de buradan al — daha güvenilir
                                _lev_real = int(_p.get("leverage") or lev)
                                if _lev_real > 0:
                                    lev = _lev_real
                                print(f"[MEXC] open_positions'tan oim={tpsl_oim:.4f} lev={lev}")
                                break
                    except Exception as _oe:
                        print(f"[MEXC] oim fallback hata: {_oe}")
                return {"success": True, "order_id": str(res.get("data", "")),
                        "vol": vol, "leverage": lev, "mark_price": mp,
                        "oim": tpsl_oim, "contract_size": contract_size}
            return {"success": False, "msg": res.get("message", str(res))}
        except Exception as e:
            print(f"[MEXC] Emir hatasi (deneme {deneme+1}/2): {e}")
            if deneme < 1:
                time.sleep(1)
    return {"success": False, "msg": "2 denemede de basarisiz"}


def mexc_update_tpsl(symbol, is_long, tp1, sl):
    """
    Position TP/SL — önce mevcut stop order'ları iptal et, sonra yenisini koy.
    trend=2: Last Price
    """
    sym = mexc_format_symbol(symbol)
    try:
        # 1) Açık pozisyonu bul
        r = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/position/open_positions",
                             params={"symbol": sym})
        raw = r.json()
        print(f"[MEXC TPSL] open_positions: {raw}")
        pozlar = raw.get("data", [])
        hedef  = None
        for p in pozlar:
            if is_long and p.get("positionType") == 1:
                hedef = p; break
            elif not is_long and p.get("positionType") == 2:
                hedef = p; break
        if not hedef:
            print(f"[MEXC TPSL] Pozisyon bulunamadi — is_long={is_long}, aktif_pozisyonlar'dan temizleniyor")
            # MEXC'te pozisyon yok — bot kaydını da temizle
            sym_key_tpsl = sym.replace("_USDT", "USDT")
            with pozisyon_kilit:
                for _k in [sym_key_tpsl, sym_key_tpsl + "_HEDGE"]:
                    poz = aktif_pozisyonlar.get(_k)
                    if poz and poz.get("is_long") == is_long:
                        aktif_pozisyonlar.pop(_k, None)
                        print(f"[MEXC TPSL] {_k} aktif_pozisyonlar'dan silindi")
            pozisyon_kaydet()
            return False

        pid       = hedef.get("positionId") or hedef.get("id")
        oim       = float(hedef.get("oim") or hedef.get("im") or 0)
        avg_price = float(hedef.get("holdAvgPrice") or hedef.get("openAvgPrice") or 0)
        print(f"[MEXC TPSL] pid={pid} oim={oim:.4f} avg_price={avg_price}")

        # TP karlilik kontrolu — avg_price'a gore TP dogru yonde ve karli mi?
        # Karli degil ise stop order'a dokunma, guncelleme yapma.
        if tp1 and avg_price > 0:
            try:
                tp1_f = float(str(tp1).replace(",", "."))
                if is_long and tp1_f <= avg_price:
                    print(f"[MEXC TPSL] TP karli degil: LONG TP ({tp1_f}) <= avg_price ({avg_price}) — guncelleme atlandı")
                    return False, 0.0
                elif not is_long and tp1_f >= avg_price:
                    print(f"[MEXC TPSL] TP karli degil: SHORT TP ({tp1_f}) >= avg_price ({avg_price}) — guncelleme atlandı")
                    return False, 0.0
            except Exception as e:
                print(f"[MEXC TPSL] TP karlilik parse hatasi: {e}")

        # 2) Mevcut stop order'ları iptal et — sadece bu pozisyon için (positionId bazlı)
        try:
            # Önce positionId bazlı iptal dene (hedge durumunda diğer pozisyonu etkilemez)
            r_cancel = mexc_private_post(
                f"{MEXC_BASE_URL}/api/v1/private/stoporder/cancel_all",
                {"symbol": sym, "positionId": pid}
            )
            print(f"[MEXC TPSL] mevcut stop order iptali (pid={pid}): {r_cancel.text[:100]}")
        except Exception as e:
            print(f"[MEXC TPSL] stop order iptal hatasi (devam): {e}")
        import time as _t; _t.sleep(0.5)

        # 2) Position TP/SL endpoint — resmi dokümantasyon
        # trend: 1=Fair Price, 2=Last Price, 3=Index Price
        body = {
            "symbol":     sym,
            "positionId": pid,
        }
        if tp1:
            body["takeProfitPrice"] = float(str(tp1).replace(",", "."))
            body["takeProfitType"]  = 2   # Last Price
        if sl:
            body["stopLossPrice"] = float(str(sl).replace(",", "."))
            body["stopLossType"]  = 2   # Last Price

        print(f"[MEXC TPSL] position/stop_loss_plan body: {body}")
        r2 = mexc_private_post(
            f"{MEXC_BASE_URL}/api/v1/private/position/stop_loss_plan", body)
        print(f"[MEXC TPSL] stop_loss_plan yanit: {r2.text[:300]}")

        result = r2.json()
        if result.get("success"):
            print("[MEXC TPSL] Position TP/SL OK")
            return True, oim

        # Fallback: stoporder/place ile dene (eski yöntem)
        print(f"[MEXC TPSL] stop_loss_plan basarisiz ({result.get('message')}), stoporder/place deneniyor...")
        vol = int(float(hedef.get("holdVol", 1)))
        body2 = {
            "symbol":       sym,
            "positionId":   pid,
            "vol":          vol,          # tam pozisyon hacmi
            "executeCycle": 87600,        # GTC
            "trend":        2,            # Last Price
            "triggerType":  1,
            "openType":     2,            # isolated margin
        }
        if tp1:
            body2["takeProfitPrice"] = float(str(tp1).replace(",", "."))
            body2["profitTrend"]     = 2  # Last Price
        if sl:
            body2["stopLossPrice"] = float(str(sl).replace(",", "."))
            body2["lossTrend"]     = 2    # Last Price
        print(f"[MEXC TPSL] stoporder/place body: {body2}")
        r3 = mexc_private_post(f"{MEXC_BASE_URL}/api/v1/private/stoporder/place", body2)
        print(f"[MEXC TPSL] stoporder/place yanit: {r3.text[:300]}")
        ok = r3.json().get("success", False)
        print(f"[MEXC TPSL] Sonuc: {'OK' if ok else 'BASARISIZ'}")
        return ok, oim

    except Exception as e:
        print(f"[MEXC TPSL] Hata: {e}")
        return False, 0.0


def mexc_pozisyon_kapat(symbol, is_long):
    """Mevcut pozisyonu market fiyatından kapat."""
    sym = mexc_format_symbol(symbol)
    try:
        # Mevcut pozisyonu bul
        r = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/position/open_positions",
                             params={"symbol": sym})
        pozlar = r.json().get("data", [])
        hedef = None
        for p in pozlar:
            if is_long and p.get("positionType") == 1:
                hedef = p; break
            elif not is_long and p.get("positionType") == 2:
                hedef = p; break
        if not hedef:
            print(f"[MEXC KAPAT] {symbol} pozisyon bulunamadi")
            return False
        vol = int(float(hedef.get("vol", 1)))
        # One-way mode: LONG kapat = side=2 (sell), SHORT kapat = side=1 (buy)
        side = 2 if is_long else 1
        body = {"symbol": sym, "price": 0, "vol": vol, "side": side,
                "type": 5, "openType": 2}
        r2 = mexc_private_post(f"{MEXC_BASE_URL}/api/v1/private/order/create", body)
        res = r2.json()
        print(f"[MEXC KAPAT] {symbol} kapat yanit: {res}")
        return res.get("success", False)
    except Exception as e:
        print(f"[MEXC KAPAT] {symbol} hata: {e}")
        return False



def mexc_pozisyon_sorgula(symbol, is_long):
    sym = mexc_format_symbol(symbol)
    try:
        r = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/position/open_positions",
                             params={"symbol": sym})
        data = r.json().get("data", [])
        print(f"[POZISYON] {sym} is_long={is_long} pozisyon sayisi={len(data)} data={str(data)[:200]}")
        for p in data:
            if is_long and p.get("positionType") == 1: return True
            if not is_long and p.get("positionType") == 2: return True
        return False
    except Exception as e:
        print(f"[POZISYON] {sym} sorgu hatasi: {e}")
        return False


def mexc_pozisyon_detay(symbol, is_long):
    """MEXC'ten açık pozisyonun detaylarını çek — marjin, vol, unrealized PnL."""
    sym = mexc_format_symbol(symbol)
    try:
        r = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/position/open_positions",
                             params={"symbol": sym})
        data = r.json().get("data", [])
        tip  = 1 if is_long else 2
        for p in data:
            if p.get("positionType") == tip:
                return {
                    "im":      float(p.get("im",      0) or 0),   # başlangıç marjini (USDT)
                    "vol":     float(p.get("vol",     0) or 0),
                    "holdVol": float(p.get("holdVol", 0) or 0),
                    "avgPrice":float(p.get("openAvgPrice", 0) or 0),
                }
        return None
    except Exception as e:
        print(f"[POZISYON_DETAY] {sym} hata: {e}")
        return None


def pozisyon_al(sym_key, is_long):
    with pozisyon_kilit:
        mevcut = aktif_pozisyonlar.get(sym_key)
    if mevcut:
        symbol = sym_key.replace("_HEDGE", "")
        if mexc_pozisyon_sorgula(symbol, mevcut["is_long"]):
            return mevcut
        with pozisyon_kilit:
            aktif_pozisyonlar.pop(sym_key, None)
        pozisyon_kaydet()
        return None
    symbol = sym_key.replace("_HEDGE", "")
    if mexc_pozisyon_sorgula(symbol, is_long):
        poz = {"is_long": is_long, "timeframe": "?", "sinyal": "RECOVERY",
               "order_id": "", "vol": 0, "tp1": None, "sl": None}
        with pozisyon_kilit:
            aktif_pozisyonlar[sym_key] = poz
        pozisyon_kaydet()
        return poz
    return None


def _gunluk_pnl_gonder(hedef_chat_id=None):
    """PNL gonder — hedef_chat_id None ise MEXC_NOTIFY_CHAT_ID kullanilir."""
    def _hata_gonder(msg):
        _mexc_topic_mesaj_gonder(f"MEXC PNL hatasi: {msg}")

    if not MEXC_API_KEY or not MEXC_API_SECRET:
        _hata_gonder("MEXC API anahtari tanimli degil.")
        return
    # 3 deneme yap
    res = None
    for deneme in range(3):
        try:
            r = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/account/assets")
            res = r.json()
            if not res.get("success"):
                msg = res.get('message', '')
                if "Network error" in msg and deneme < 2:
                    print(f"[PNL] Network error, {deneme+1}. deneme tekrar...")
                    time.sleep(2)
                    continue
                _hata_gonder(f"MEXC bakiye sorgu hatasi: {msg}")
                return
            break
        except Exception as e:
            if deneme < 2:
                time.sleep(2)
                continue
            _hata_gonder(f"PNL sorgu hatasi: {str(e)[:100]}")
            return
    if not res or not res.get("success"):
        return
    try:
        assets = res.get("data", {})
        usdt   = None
        for a in (assets if isinstance(assets, list) else [assets]):
            if a.get("currency") == "USDT":
                usdt = a; break
        if not usdt:
            _telegram_mesaj_gonder(hedef_chat_id, "USDT bakiyesi bulunamadi.")
            return
        bakiye     = float(usdt.get("equity", 0))
        kullanilan = float(usdt.get("positionMargin", 0))
        realized   = float(usdt.get("realised", 0))
        # Unrealized PNL — open_positions'tan profitRatio * im toplamı (MEXC UI ile aynı)
        unrealized = 0.0
        unrealized_pct = 0.0
        try:
            _r_pos = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/position/open_positions")
            _pos_data = _r_pos.json().get("data", [])
            if isinstance(_pos_data, list) and _pos_data:
                for _p in _pos_data:
                    _im  = float(_p.get("im", 0) or 0)
                    _pct = float(_p.get("profitRatio", 0) or 0)
                    unrealized += _pct * _im
                print(f"[PNL DEBUG] unrealized={unrealized:.4f} USDT ({len(_pos_data)} poz)")
            else:
                print(f"[PNL DEBUG] open_positions bos — unrealized=0")
        except Exception as _pe:
            print(f"[PNL DEBUG] open_positions unrealized hata: {_pe}")
        # % = toplam unrealized / toplam kullanılan marjin
        unrealized_pct = (unrealized / kullanilan * 100) if kullanilan > 0 else 0.0
        print(f"[PNL DEBUG] unrealized_pct={unrealized_pct:.2f}%")
        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
        # Gorsel olustur
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.gridspec import GridSpec

            fig = plt.figure(figsize=(10, 4), facecolor="#0d1117")
            gs  = GridSpec(1, 4, figure=fig, wspace=0.3)

            def kart(ax, baslik, deger, renk, alt="USDT"):
                ax.set_facecolor("#161b22")
                ax.set_xticks([]); ax.set_yticks([])
                for s in ax.spines.values(): s.set_edgecolor("#30363d")
                ax.text(0.5, 0.7, baslik, transform=ax.transAxes,
                        ha="center", fontsize=9, color="#8b949e")
                # deger string veya float olabilir
                if isinstance(deger, str):
                    isaretli = deger
                elif "PNL" in baslik:
                    isaretli = (f"{deger:+.4f}" if abs(deger) < 0.01 else f"{deger:+.2f}")
                else:
                    isaretli = f"{deger:.2f}"
                ax.text(0.5, 0.35, isaretli, transform=ax.transAxes,
                        ha="center", fontsize=13, color=renk)
                ax.text(0.5, 0.1, alt, transform=ax.transAxes,
                        ha="center", fontsize=8, color="#484f58")

            kart(fig.add_subplot(gs[0,0]), "Toplam Bakiye", bakiye,    "#e6edf3")
            kart(fig.add_subplot(gs[0,1]), "Kullanilan",    kullanilan, "#e6edf3")
            # Gerçekleşen PNL: % sol, USDT sağ
            gun_bugun = gun_str()
            with _pnl_kilit:
                gun_kayitlar = [k for k in _pnl_kayitlar.get(gun_bugun, []) if k.get("mexc_acildi", True)]
            kum_pnl_usdt = sum(k["pnl_usdt"] for k in gun_kayitlar)
            kum_pnl_pct  = sum(k["pnl_pct"]  for k in gun_kayitlar)

            ax_pnl = fig.add_subplot(gs[0,2])
            ax_pnl.set_facecolor("#161b22")
            ax_pnl.set_xticks([]); ax_pnl.set_yticks([])
            for sp in ax_pnl.spines.values(): sp.set_edgecolor("#30363d")
            ax_pnl.text(0.5, 0.78, "Gerceklesen PNL", transform=ax_pnl.transAxes,
                        ha="center", fontsize=9, color="#8b949e")
            renk_pnl = "#26a69a" if kum_pnl_usdt >= 0 else "#ef5350"
            def fmt_usdt2(v):
                return f"{v:+.2f}" if abs(v) >= 0.01 else f"{v:+.4f}"
            ax_pnl.text(0.5, 0.45, f"{kum_pnl_pct:+.2f}%", transform=ax_pnl.transAxes,
                        ha="center", fontsize=13, color=renk_pnl)
            ax_pnl.text(0.5, 0.25, f"{fmt_usdt2(kum_pnl_usdt)} USDT", transform=ax_pnl.transAxes,
                        ha="center", fontsize=11, color=renk_pnl)
            ax_pnl.text(0.5, 0.1, f"{len(gun_kayitlar)} işlem", transform=ax_pnl.transAxes,
                        ha="center", fontsize=8, color="#484f58")
            # Açık poz PNL kartı — % üstte, USDT altta
            ax_unreal = fig.add_subplot(gs[0,3])
            ax_unreal.set_facecolor("#161b22")
            ax_unreal.set_xticks([]); ax_unreal.set_yticks([])
            for sp in ax_unreal.spines.values(): sp.set_edgecolor("#30363d")
            ax_unreal.text(0.5, 0.78, "Acik Poz. PNL", transform=ax_unreal.transAxes,
                           ha="center", fontsize=9, color="#8b949e")
            _uc = "#26a69a" if unrealized >= 0 else "#ef5350"
            if unrealized != 0:
                ax_unreal.text(0.5, 0.48, f"{unrealized_pct:+.2f}%", transform=ax_unreal.transAxes,
                               ha="center", fontsize=13, color=_uc)
                ax_unreal.text(0.5, 0.25, f"{fmt_usdt2(unrealized)} USDT", transform=ax_unreal.transAxes,
                               ha="center", fontsize=10, color=_uc)
            else:
                ax_unreal.text(0.5, 0.38, "—", transform=ax_unreal.transAxes,
                               ha="center", fontsize=13, color="#8b949e")
            ax_unreal.text(0.5, 0.1, "USDT", transform=ax_unreal.transAxes,
                           ha="center", fontsize=8, color="#484f58")

            fig.suptitle(f"MEXC Futures PNL — {zaman_str}",
                         color="#e6edf3", fontsize=11, fontweight="bold")
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                        facecolor="#0d1117", edgecolor="none", pad_inches=0.1)
            plt.close(fig)
            buf.seek(0)
            img_bytes = buf.read()
        except Exception as e:
            print(f"[PNL GORSEL] Hata: {e}")
            img_bytes = None

        # Kümülatif PNL verileri
        gun_bugun2 = gun_str()
        with _pnl_kilit:
            gun_kayitlar2 = list(_pnl_kayitlar.get(gun_bugun2, []))
        kum_pct2  = sum(k["pnl_pct"]  for k in gun_kayitlar2)
        kum_usdt2 = sum(k["pnl_usdt"] for k in gun_kayitlar2)
        tp_sayi   = sum(1 for k in gun_kayitlar2 if k.get("tp_label","").startswith("TP"))
        sl_sayi   = sum(1 for k in gun_kayitlar2 if k.get("tp_label") == "SL")

        caption = (
            f"📊 <b>PNL — {zaman_str}</b>\n\n"
            f"💰 Bakiye: <b>{bakiye:.2f} USDT</b>\n"
            f"📦 Kullanılan: <b>{kullanilan:.2f} USDT</b>\n"
            f"📈 Açık Poz. PNL: <b>{unrealized_pct:+.2f}%</b> | <b>{unrealized:+.4f} USDT</b>\n\n"
        )
        if gun_kayitlar2:
            caption += f"🏆 <b>Günlük Bot PNL ({len(gun_kayitlar2)} işlem)</b>\n"
            caption += f"{'✅' if kum_pct2 >= 0 else '❌'} Kümülatif: <b>{kum_pct2:+.2f}%</b> / <b>{kum_usdt2:+.4f} USDT</b>\n"
            caption += f"✅ TP: {tp_sayi}  ❌ SL: {sl_sayi}\n\n"
            # İşlem detayları (son 5)
            for k in gun_kayitlar2[-5:]:
                ikon = "✅" if k.get("tp_label","").startswith("TP") else "❌"
                sym  = k["symbol"].replace("USDT","")
                sinyal = "LONG" if any(x in k.get("sinyal","").upper() for x in ["BUY","LONG"]) else "SHORT"
                caption += (
                    f"{ikon} {sym} {sinyal} {k.get('tp_label','?')} "
                    f"<b>{k['pnl_pct']:+.2f}%</b> / {k['pnl_usdt']:+.4f}$\n"
                )
        else:
            caption += "⚪ Bugün henüz tamamlanan bot işlemi yok."
        

        base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        if img_bytes:
            if MEXC_NOTIFY_CHAT_ID:
                requests.post(f"{base}/sendPhoto",
                              data={"chat_id": MEXC_NOTIFY_CHAT_ID,
                                    "caption": caption,
                                    "parse_mode": "HTML"},
                              files={"photo": ("pnl.png", img_bytes, "image/png")},
                              timeout=30)
            else:
                print("[PNL] MEXC_NOTIFY_CHAT_ID tanimli degil, PNL gonderilmedi.")
        else:
            _mexc_topic_mesaj_gonder(caption)

    except Exception as e:
        print(f"[PNL] Hata: {e}")
        _mexc_topic_mesaj_gonder(f"PNL sorgu hatasi: {str(e)[:100]}")


def _gunluk_pnl_gonder_topic():
    """PNL'yi MEXC_NOTIFY_CHAT_ID'ye gonder — wrapper fonksiyon."""
    _gunluk_pnl_gonder(None)

def veri_kaydet():
    try:
        os.makedirs(os.path.dirname(VERI_DOSYASI), exist_ok=True)
        with gunluk_kilit:
            veri = gunluk_sinyaller[:]
        # Atomic write: once gecici dosyaya yaz, sonra rename
        # Yazma sirasinda bot kesilse bile eski dosya korunur
        tmp_dosya = VERI_DOSYASI + ".tmp"
        with open(tmp_dosya, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False)
        os.replace(tmp_dosya, VERI_DOSYASI)
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

            # Bekleyen TP kontrollerini yeniden başlat
            simdi = time.time()
            yeniden_baslatilanlar = 0
            for s in veri:
                # Eski kayıtlarda mexc_acildi yoksa order_id'ye göre belirle
                if "mexc_acildi" not in s:
                    order_id = s.get("order_id", "")
                    s["mexc_acildi"] = bool(order_id and str(order_id) not in ("", "None", "null", "{}"))
                # Bildirim zaten gönderilmişse atla (yeni alan)
                if s.get("bildirim_gonderildi"):
                    continue
                # TP sonuçları zaten yazılmışsa (True veya False) — bildirim gönderilmiş demektir
                # None = henüz kontrol edilmedi, True/False = sonuçlanmış
                sonuclanmis = all(
                    s.get(k) is not None
                    for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]
                    if s.get("tp"+k[-1])  # sadece tanımlı TP'leri kontrol et
                ) and any(s.get(k) is not None for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok","sl_ok"])
                if sonuclanmis:
                    continue
                # message_id ve TP değerleri olmalı
                if not s.get("message_id"):
                    continue
                tp_var = any(s.get(k) and str(s.get(k)) != "null" for k in ["tp1","tp2","tp3","tp4","tp5"])
                if not tp_var:
                    continue
                # Kontrol süresi dolmamış olmalı
                sinyal_ts  = s.get("zaman", 0)
                if sinyal_ts == 0:
                    continue  # Zaman bilgisi yoksa atla
                kontrol_dk = tp_sure(s.get("timeframe", "1"))
                bitis_ts   = sinyal_ts + kontrol_dk * 60
                if simdi >= bitis_ts:
                    continue  # Süre dolmuş, atla
                # Kalan süreyi hesapla
                kalan_dk = max(1, int((bitis_ts - simdi) / 60))
                t = threading.Thread(
                    target=tp_kontrol_gonder,
                    args=(s["symbol"], s["sinyal"], s.get("timeframe","1"),
                          s.get("tp1"), s.get("tp2"), s.get("tp3"), s.get("tp4"), s.get("tp5"),
                          s.get("sl"), s["message_id"], kalan_dk, int(sinyal_ts), s.get("price")))
                t.daemon = True
                t.start()
                yeniden_baslatilanlar += 1
            if yeniden_baslatilanlar > 0:
                print(f"[YUKLE] {yeniden_baslatilanlar} bekleyen TP kontrolu yeniden baslatildi.")
    except Exception as e:
        print(f"[YUKLE] Hata: {e}")


def _sinyal_tipi_belirle(sinyal_str):
    """Sinyal string'inden tip belirle: Strong Buy / Long / Strong Sell / Short"""
    s = sinyal_str.upper()
    if "STRONG" in s and ("BUY" in s or "LONG" in s):
        return "Strong Buy"
    elif "STRONG" in s and ("SELL" in s or "SHORT" in s):
        return "Strong Sell"
    elif "BUY" in s or "LONG" in s:
        return "Long"
    else:
        return "Short"

def _seans_belirle():
    """Mevcut saate göre seans belirle (UTC)"""
    try:
        saat = datetime.utcnow().hour
        if 0 <= saat < 8:
            return "Asya"
        elif 8 <= saat < 13:
            return "Londra"
        else:
            return "New York"
    except Exception:
        return None

def _hacim_durumu_belirle(symbol):
    """Son hacmi 20 bar ortalamasıyla karşılaştır"""
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": symbol, "interval": "1m", "limit": 21},
            timeout=6, proxies=BINANCE_PROXY
        )
        if r.status_code == 200:
            data = r.json()
            if len(data) >= 21:
                volumes = [float(k[5]) for k in data[:-1]]
                ort = sum(volumes) / len(volumes)
                son = float(data[-1][5])
                if son >= ort * 1.2:
                    return "Ortalama Üstü"
                elif son <= ort * 0.8:
                    return "Ortalama Altı"
                else:
                    return "Normal"
    except Exception:
        pass
    return None

def _piyasa_yonu_hizli():
    """BTC fiyat değişimiyle hızlı piyasa yönü tahmini (son 1 saatlik kline)"""
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": "BTCUSDT", "interval": "1h", "limit": 3},
            timeout=6, proxies=BINANCE_PROXY
        )
        if r.status_code == 200:
            data = r.json()
            if len(data) >= 2:
                acilis = float(data[-2][1])
                kapanis = float(data[-2][4])
                pct = (kapanis - acilis) / acilis * 100
                if pct >= 0.3:
                    return "Yükseliş"
                elif pct <= -0.3:
                    return "Düşüş"
                else:
                    return "Yatay"
    except Exception:
        pass
    return None

def sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, tp4, tp5, sl, message_id):
    # Piyasa koşullarını /analiz cache'inden oku — gereksiz API çağrısı yok
    _global = _son_analiz_veriler.get("_GLOBAL", {}) if _son_analiz_veriler else {}
    fg_deger     = _global.get("fg_deger")
    fg_sinif     = None  # cache'de kategori yok, deger'den türetilir
    funding      = _global.get("btc_fund")
    funding_yon  = ("Pozitif" if (funding or 0) > 0 else
                    "Negatif" if (funding or 0) < 0 else "Nötr") if funding is not None else None
    # OI yönü: coin bazlı cache'den BTC OI delta'sına bak
    try:
        btc_oi = _son_analiz_veriler.get("BTCUSDT", {}).get("oi_delta")
        oi_yonu = ("Artıyor" if btc_oi and btc_oi.get("delta_pct", 0) > 0 else
                   "Azalıyor" if btc_oi and btc_oi.get("delta_pct", 0) < 0 else None)
    except Exception:
        oi_yonu = None
    piyasa_yonu  = _global.get("piyasa_yonu")
    hacim_durumu = _hacim_durumu_belirle(symbol)
    seans        = _seans_belirle()
    sinyal_tipi  = _sinyal_tipi_belirle(sinyal)

    kayit = {
        "gun": gun_str(), "zaman": time.time(),
        "symbol": symbol, "sinyal": sinyal,
        "timeframe": timeframe, "price": price,
        "tp1": tp1, "tp2": tp2, "tp3": tp3, "tp4": tp4, "tp5": tp5, "sl": sl,
        "tp1_ok": None, "tp2_ok": None, "tp3_ok": None, "tp4_ok": None, "tp5_ok": None,
        "sl_ok": None,
        "message_id": message_id,
        "mexc_acildi": False,
        "istatistik_sayildi": True,
        # --- Yeni piyasa koşulu alanları ---
        "sinyal_tipi":   sinyal_tipi,
        "fg_deger":      fg_deger,
        "fg_kategori":   fg_sinif,
        "funding_rate":  round(funding, 4) if funding is not None else None,
        "funding_yonu":  funding_yon,
        "oi_yonu":       oi_yonu,
        "piyasa_yonu":   piyasa_yonu,
        "hacim_durumu":  hacim_durumu,
        "seans":         seans,
    }
    with gunluk_kilit:
        gunluk_sinyaller.append(kayit)
    veri_kaydet()
    if TELEGRAM_LOG_ID:
        log_satir = LOG_MAGIC + json.dumps(kayit, ensure_ascii=False)
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, log_satir)


def _pnl_islem_kaydet(sinyal_kayit, tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok):
    """TP/SL sonucundan PNL hesapla ve günlük kayda ekle."""
    try:
        giris = sinyal_kayit.get("price")
        if not giris:
            return
        giris = float(str(giris).replace(",", "."))
        if giris <= 0:
            return

        sinyal   = sinyal_kayit.get("sinyal", "").upper()
        is_long  = any(x in sinyal for x in ["BUY", "LONG"])
        symbol   = sinyal_kayit.get("symbol", "")
        gun      = sinyal_kayit.get("gun", gun_str())

        # Hangi seviye tetiklendi ve çıkış fiyatı ne?
        tp_map = [
            (tp5_ok, sinyal_kayit.get("tp5"), "TP5"),
            (tp4_ok, sinyal_kayit.get("tp4"), "TP4"),
            (tp3_ok, sinyal_kayit.get("tp3"), "TP3"),
            (tp2_ok, sinyal_kayit.get("tp2"), "TP2"),
            (tp1_ok, sinyal_kayit.get("tp1"), "TP1"),
        ]
        cikis     = None
        tp_label  = None
        for ok, fiyat, label in tp_map:
            if ok and fiyat and str(fiyat) != "null":
                try:
                    cikis    = float(str(fiyat).replace(",", "."))
                    tp_label = label
                    break
                except Exception:
                    continue

        if sl_ok and sinyal_kayit.get("sl"):
            try:
                cikis    = float(str(sinyal_kayit["sl"]).replace(",", "."))
                tp_label = "SL"
            except Exception:
                pass

        if not cikis:
            return

        # Kaldıraçlı PNL hesabı (MEXC UI ile aynı formül)
        # PNL% = (çıkış - giriş) / giriş × kaldıraç × 100
        # mexc_leverage kaydedilmişse kullan (500x gibi), yoksa vol/oim/price'tan hesapla
        leverage = float(sinyal_kayit.get("mexc_leverage") or 0)
        if leverage <= 0:
            # Kaldıracı vol × contract_size × price / oim'den hesapla
            _vol_l  = float(sinyal_kayit.get("vol") or 0)
            _cs_l   = float(sinyal_kayit.get("contract_size") or 1.0)
            _oim_l  = float(sinyal_kayit.get("mexc_oim") or 0)
            if _vol_l > 0 and _oim_l > 0 and giris > 0:
                leverage = round(_vol_l * _cs_l * giris / _oim_l)
                print(f"[PNL] leverage hesaplandi: {leverage}x (vol={_vol_l} cs={_cs_l} giris={giris} oim={_oim_l})")
            else:
                # Son çare: MEXC open_positions'tan gerçek leverage'ı çek
                try:
                    _sym_pnl = symbol.replace("USDT.P","").replace("USDT","")
                    _r_pnl = mexc_private_get(
                        f"{MEXC_BASE_URL}/api/v1/private/position/open_positions")
                    _plist = _r_pnl.json().get("data", [])
                    for _p in (_plist if isinstance(_plist, list) else []):
                        _psym = str(_p.get("symbol","")).replace("_USDT","")
                        if _psym == _sym_pnl:
                            leverage = int(_p.get("leverage") or 1)
                            print(f"[PNL] leverage MEXC API'den alindi: {leverage}x ({symbol})")
                            break
                    if leverage <= 0:
                        leverage = 1
                        print(f"[PNL] leverage API'den de alinamadi, 1x kullanildi")
                except Exception as _le:
                    leverage = 1
                    print(f"[PNL] leverage API hata: {_le}, 1x kullanildi")
        if is_long:
            pnl_pct = (cikis - giris) / giris * leverage * 100
        else:
            pnl_pct = (giris - cikis) / giris * leverage * 100

        # USDT PNL — oim (MEXC im alanı, fee dahil gerçek margin) kullan
        # oim yoksa notional/leverage ile hesapla
        oim = float(sinyal_kayit.get("mexc_oim") or 0)
        if oim <= 0:
            vol_k    = float(sinyal_kayit.get("vol") or 0)
            cs_k     = float(sinyal_kayit.get("contract_size") or 1.0)
            notional = vol_k * cs_k * giris if vol_k > 0 else 0
            oim      = notional / leverage if (notional > 0 and leverage > 0) else 0
        if oim <= 0:
            # oim bulunamadı — MEXC_MARGIN_USDT global ayarını kullan (doğru değer)
            oim = MEXC_MARGIN_USDT
        pnl_usdt = round(pnl_pct / 100 * oim, 4)

        kayit = {
            "symbol":      symbol,
            "sinyal":      sinyal_kayit.get("sinyal", ""),
            "giris":       giris,
            "cikis":       cikis,
            "tp_label":    tp_label,
            "pnl_usdt":    round(pnl_usdt, 4),
            "pnl_pct":     round(pnl_pct,  2),
            "zaman":       time.time(),
            "message_id":  sinyal_kayit.get("message_id"),
            "mexc_acildi": sinyal_kayit.get("mexc_acildi", False),
        }
        with _pnl_kilit:
            if gun not in _pnl_kayitlar:
                _pnl_kayitlar[gun] = []
            # Revize durumu: aynı symbol için önceki kayıt varsa güncelle
            guncellendi = False
            for mevcut in _pnl_kayitlar[gun]:
                if mevcut["symbol"] == symbol:
                    mevcut.update(kayit)
                    guncellendi = True
                    print(f"[PNL KAYIT] {symbol} revize güncellendi: {tp_label} pnl={pnl_pct:+.2f}%")
                    break
            if not guncellendi:
                _pnl_kayitlar[gun].append(kayit)
                print(f"[PNL KAYIT] {symbol} yeni kayit: {tp_label} pnl={pnl_pct:+.2f}%")
    except Exception as e:
        print(f"[PNL KAYIT] Hata: {e}")


def tp_sonuc_guncelle(message_id, tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok):
    sinyal_ref = None
    with gunluk_kilit:
        for s in gunluk_sinyaller:
            if s["message_id"] == message_id:
                s["tp1_ok"] = tp1_ok
                s["tp2_ok"] = tp2_ok
                s["tp3_ok"] = tp3_ok
                s["tp4_ok"] = tp4_ok
                s["tp5_ok"] = tp5_ok
                s["sl_ok"]  = sl_ok
                s["bildirim_gonderildi"] = True
                # Hangi seviye tetiklendi — PNL mesajı için
                if sl_ok:       s["tetiklenen"] = "SL"
                elif tp5_ok:    s["tetiklenen"] = "TP5"
                elif tp4_ok:    s["tetiklenen"] = "TP4"
                elif tp3_ok:    s["tetiklenen"] = "TP3"
                elif tp2_ok:    s["tetiklenen"] = "TP2"
                elif tp1_ok:    s["tetiklenen"] = "TP1"
                sinyal_ref = dict(s)
                break
    veri_kaydet()
    # PNL kaydet — sadece botun açtığı işlemler için (mexc_acildi=True)
    if sinyal_ref and sinyal_ref.get("mexc_acildi"):
        _pnl_islem_kaydet(sinyal_ref, tp1_ok, tp2_ok, tp3_ok, tp4_ok, tp5_ok, sl_ok)
    elif sinyal_ref:
        print(f"[PNL] {sinyal_ref.get('symbol')} mexc_acildi=False — PNL kaydedilmedi")


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


def _telegram_topic_mesaj_gonder(topic_id, metin, parse_mode="HTML", reply_to=None):
    """Grubun belirtilen topic'ine metin gönder."""
    if not TELEGRAM_GRUP_ID:
        return None
    base    = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    payload = {
        "chat_id": TELEGRAM_GRUP_ID,
        "message_thread_id": topic_id,
        "text": metin,
        "parse_mode": parse_mode
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        r = requests.post(f"{base}/sendMessage", json=payload, timeout=15)
        if r.status_code != 200:
            print(f"[GRUP] Topic mesaj hatasi: {r.status_code} topic={topic_id}")
        return r
    except Exception as e:
        print(f"[GRUP] Topic mesaj hatasi: {e}")
        return None


def _mexc_topic_mesaj_gonder(metin, parse_mode="HTML"):
    """MEXC islem bildirimlerini MEXC_NOTIFY_CHAT_ID'ye gonder."""
    if not MEXC_NOTIFY_CHAT_ID:
        print("[MEXC NOTIFY] MEXC_NOTIFY_CHAT_ID tanimli degil, mesaj gonderilmedi.")
        return None
    return _telegram_mesaj_gonder(str(MEXC_NOTIFY_CHAT_ID), metin, parse_mode=parse_mode)


def _mexc_topic_foto_gonder(img_data, caption, parse_mode="HTML"):
    """MEXC islem fotografini MEXC_NOTIFY_CHAT_ID'ye gonder."""
    if not MEXC_NOTIFY_CHAT_ID:
        print("[MEXC NOTIFY] MEXC_NOTIFY_CHAT_ID tanimli degil, foto gonderilmedi.")
        return None
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        r = requests.post(f"{base}/sendPhoto",
            data={"chat_id": MEXC_NOTIFY_CHAT_ID,
                  "caption": caption, "parse_mode": parse_mode},
            files={"photo": ("chart.png", img_data, "image/png")}, timeout=30)
        return r
    except Exception as e:
        print(f"[MEXC NOTIFY] Foto gonderme hatasi: {e}")
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


def _telegram_topic_foto_gonder(topic_id, img_data, caption, parse_mode="HTML"):
    """Grubun belirtilen topic'ine fotoğraf gönder."""
    if not TELEGRAM_GRUP_ID:
        return None
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        r = requests.post(f"{base}/sendPhoto",
            data={"chat_id": TELEGRAM_GRUP_ID, "message_thread_id": topic_id,
                  "caption": caption, "parse_mode": parse_mode},
            files={"photo": ("chart.png", img_data, "image/png")}, timeout=30)
        if r.status_code != 200:
            print(f"[GRUP] Topic foto hatasi: {r.status_code} topic={topic_id}")
        return r
    except Exception as e:
        print(f"[GRUP] Topic foto hatasi: {e}")
        return None


def _telegram_foto_gonder_filigranli(chat_id, img_data, caption, parse_mode="HTML"):
    """Filigran ekleyerek fotoğraf gönder — sadece kendi ürettiğimiz raporlar için."""
    return _telegram_foto_gonder(chat_id, filigran_ekle(img_data, alpha=0.1125, boyut_oran=0.56), caption, parse_mode)


def _topic_foto_gonder_filigranli(topic_id, img_data, caption, parse_mode="HTML"):
    """Grubun topic'ine filigranla fotoğraf gönder."""
    return _telegram_topic_foto_gonder(topic_id, filigran_ekle(img_data, alpha=0.1125, boyut_oran=0.56), caption, parse_mode)


# ==========================================
# CHART SCREENSHOT
# ==========================================

def get_screenshot_chartimg(symbol: str, timeframe: str):
    if not CHARTIMG_KEY:
        return None
    # Dominans sembolleri için chart çekme
    if any(x in symbol.upper() for x in [".D", "DOMINAN"]):
        return None
    tf_map = {
        "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
        "60": "1h", "1H": "1h", "120": "2h", "240": "4h",
        "D": "1D", "1D": "1D", "W": "1W", "M": "1M"
    }
    tf  = tf_map.get(str(timeframe), "1h")
    sym = symbol.upper().replace(".P", "").replace("USDT.P", "USDT")

    # Dominans sembolleri — CRYPTOCAP prefix
    dominans = ["USDT.D", "BTC.D", "ETH.D", "OTHERS.D", "USDC.D"]
    if sym in dominans:
        sym = f"CRYPTOCAP:{sym}"
    # Borsa zaten belirtilmişse dokunma
    elif any(x in sym for x in [":", "BINANCE", "BYBIT", "MEXC", "CRYPTOCAP"]):
        pass
    else:
        sym = f"MEXC:{sym}.P"

    url     = "https://api.chart-img.com/v1/tradingview/advanced-chart"
    params  = {"symbol": sym, "interval": tf, "theme": "dark", "width": 800, "height": 500}
    headers = {"x-api-key": CHARTIMG_KEY}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.content
        print(f"[SCREENSHOT] chart-img hata: {r.status_code} sym={sym}")
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
            proxies = None
            r = requests.get(api_url, timeout=10, proxies=proxies)
            if r.status_code == 200:
                return float(r.json()["price"])
        except:
            pass
    return None


def get_high_low_in_period(symbol: str, start_ts: int, end_ts: int):
    sym = get_sym(symbol)
    if not sym.endswith("USDT"):
        sym += "USDT"

    # Önce MEXC Futures, sonra Binance Futures, son çare spot
    apis = [
        ("https://contract.mexc.com/api/v1/contract/kline/" + sym,
         {"interval": "Min1", "start": start_ts, "end": end_ts}, "mexc_futures"),
        ("https://fapi.binance.com/fapi/v1/klines",
         {"symbol": sym, "interval": "1m", "startTime": start_ts * 1000,
          "endTime": end_ts * 1000, "limit": 1500}, "binance_futures"),
        ("https://api.binance.com/api/v3/klines",
         {"symbol": sym, "interval": "1m", "startTime": start_ts * 1000,
          "endTime": end_ts * 1000, "limit": 1500}, "binance_spot"),
    ]

    for api_url, params, kaynak in apis:
        try:
            proxies = None
            r = requests.get(api_url, params=params, timeout=10, proxies=proxies)
            if r.status_code == 200:
                data = r.json()
                # MEXC Futures farklı format
                if kaynak == "mexc_futures":
                    if data.get("success") and data.get("data"):
                        klines = data["data"]
                        highs = [float(k[3]) for k in klines if len(k) > 3]
                        lows  = [float(k[4]) for k in klines if len(k) > 4]
                        if highs and lows:
                            print(f"[TP] High/Low kaynak: MEXC Futures")
                            return max(highs), min(lows)
                else:
                    klines = data
                    if klines:
                        print(f"[TP] High/Low kaynak: {kaynak}")
                        return max(float(k[2]) for k in klines), min(float(k[3]) for k in klines)
        except Exception as e:
            print(f"[TP] kline hata ({kaynak}): {e}")
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
        baslik = "⚡ <b>Erken TP/SL Bildirimi</b>" if erken else "⏱ <b>Zamana Bağlı TP/SL Bildirimi</b>"
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
        # mexc_acildi kontrolü — sadece botun açtığı işlemler için bildirim
        mexc_acildi = False
        mexc_msg_id = None
        with gunluk_kilit:
            for s in gunluk_sinyaller:
                if s.get("message_id") == message_id:
                    mexc_acildi = s.get("mexc_acildi", False)
                    mexc_msg_id = s.get("mexc_msg_id")
                    break

        # 1) TOPIC_ALARM — tüm sinyaller için (bot açsın açmasın üyeler görmeli)
        _telegram_topic_mesaj_gonder(TOPIC_ALARM, msg + "\n\n─────────────────────────────", reply_to=message_id)
        print(f"[TP] {symbol} TOPIC_ALARM bildirimi gonderildi. mexc_acildi={mexc_acildi}")

        # 2) MEXC_NOTIFY — sadece botun açtığı işlemler için kapanış bildirimi
        if mexc_acildi and MEXC_NOTIFY_CHAT_ID:
            # MEXC_NOTIFY için PNL hesaplamalı zengin kapanış mesajı
            try:
                sinyal_kayit = None
                with gunluk_kilit:
                    for s in gunluk_sinyaller:
                        if s.get("message_id") == message_id:
                            sinyal_kayit = dict(s)
                            break

                if sinyal_kayit:
                    giris    = float(str(sinyal_kayit.get("price") or 0).replace(",","."))
                    leverage = float(sinyal_kayit.get("mexc_leverage") or 0)
                    if leverage <= 0:
                        _vol_t = float(sinyal_kayit.get("vol") or 0)
                        _cs_t  = float(sinyal_kayit.get("contract_size") or 1.0)
                        _oim_t = float(sinyal_kayit.get("mexc_oim") or 0)
                        _pr_t  = giris
                        if _vol_t > 0 and _oim_t > 0 and _pr_t > 0:
                            leverage = round(_vol_t * _cs_t * _pr_t / _oim_t)
                        else:
                            leverage = 1
                    # Çıkış fiyatı — sinyal kaydındaki tetiklenen seviyeden al (msg parse değil)
                    tp_label = sinyal_kayit.get("tetiklenen", "?")
                    tp_val_map = {
                        "TP1": sinyal_kayit.get("tp1"), "TP2": sinyal_kayit.get("tp2"),
                        "TP3": sinyal_kayit.get("tp3"), "TP4": sinyal_kayit.get("tp4"),
                        "TP5": sinyal_kayit.get("tp5"), "SL":  sinyal_kayit.get("sl"),
                    }
                    cikis = 0.0
                    try:
                        val = tp_val_map.get(tp_label)
                        if val:
                            cikis = float(str(val).replace(",","."))
                    except Exception:
                        pass

                    if giris > 0 and cikis > 0:
                        is_long_k = any(x in sinyal_kayit.get("sinyal","").upper() for x in ["BUY","LONG"])
                        if is_long_k:
                            pnl_pct = (cikis - giris) / giris * leverage * 100
                        else:
                            pnl_pct = (giris - cikis) / giris * leverage * 100
                        oim_c = float(sinyal_kayit.get("mexc_oim") or 0)
                        if oim_c <= 0:
                            vol_c    = float(sinyal_kayit.get("vol") or 0)
                            cs_c     = float(sinyal_kayit.get("contract_size") or 1.0)
                            notional_c = vol_c * cs_c * giris if vol_c > 0 else 0
                            oim_c    = notional_c / leverage if (notional_c > 0 and leverage > 0) else 0
                        if oim_c <= 0:
                            oim_c = MEXC_MARGIN_USDT
                        pnl_usd = pnl_pct / 100 * oim_c
                        ikon    = "✅" if pnl_pct >= 0 else "❌"
                        yon     = "LONG" if is_long_k else "SHORT"

                        # Fiyat format
                        def fp(f):
                            if f >= 1000: return f"{f:,.1f}"
                            if f >= 1:    return f"{f:.4f}"
                            return f"{f:.7f}"

                        mexc_msg = (
                            f"{ikon} <b>{symbol.replace('USDT.P','').replace('USDT','')} {yon} — {tp_label}</b>\n\n"
                            f"📍 Giriş: <b>{fp(giris)}</b>\n"
                            f"🎯 Çıkış: <b>{fp(cikis)}</b>\n"
                            f"📊 PNL: <b>{pnl_pct:+.2f}%</b> / <b>{pnl_usd:+.4f} USDT</b>\n"
                            f"⚡ Kaldıraç: {leverage:.0f}x"
                        )
                    else:
                        mexc_msg = msg  # fallback
                else:
                    mexc_msg = msg
            except Exception as e:
                print(f"[TP] MEXC mesaj hesap hatasi: {e}")
                mexc_msg = msg

            _telegram_mesaj_gonder(MEXC_NOTIFY_CHAT_ID, mexc_msg,
                                   reply_to=mexc_msg_id, parse_mode="HTML")
            print(f"[TP] {symbol} MEXC_NOTIFY kapanış bildirimi gonderildi.")

        if TELEGRAM_LOG_ID:
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
    # Gruba gönder — 🔔 İndikatör Alarmları topic'i
    if img_data:
        resp = _telegram_topic_foto_gonder(TOPIC_ALARM, img_data, caption + "\n\n─────────────────────────────")
    else:
        resp = _telegram_topic_mesaj_gonder(TOPIC_ALARM, caption + "\n\n─────────────────────────────")

    # Eski kanala da gönder
    if TELEGRAM_KANAL_ID:
        if img_data:
            _telegram_foto_gonder(TELEGRAM_KANAL_ID, img_data, caption + "\n\n─────────────────────────────")
        else:
            _telegram_mesaj_gonder(TELEGRAM_KANAL_ID, caption + "\n\n─────────────────────────────")

    if resp and resp.status_code == 200:
        message_id = resp.json().get("result", {}).get("message_id")
        print(f"[OK] {symbol} gonderildi. message_id={message_id}")
    else:
        print(f"[HATA] {resp.status_code if resp else 'baglanti yok'}")

    if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, caption)

    # message_id olmasa bile istatistiğe kaydet
    kayit_id = message_id if message_id else int(time.time() * 1000)
    sinyal_kaydet(symbol, sinyal, timeframe, price, tp1, tp2, tp3, tp4, tp5, sl, kayit_id)

    tp_var = any(x and str(x) != 'null' for x in [tp1, tp2, tp3, tp4, tp5])
    if tp_var:
        sinyal_ts  = int(time.time())
        kontrol_dk = tp_sure(timeframe)
        t = threading.Thread(
            target=tp_kontrol_gonder,
            args=(symbol, sinyal, timeframe, tp1, tp2, tp3, tp4, tp5, sl,
                  kayit_id, kontrol_dk, sinyal_ts, price))
        t.daemon = True
        t.start()
        print(f"[TP] {symbol} icin {kontrol_dk} dk sonra kontrol planlanadi.")


# ==========================================
# İSTATİSTİK
# ==========================================

def koin_sirala_bugun(snapshot=None):
    """Bugünün verisiyle koin bazında başarı sıralaması hesapla.
    rapor_hesapla ile aynı mantık:
    - basarili: en az 1 TP true
    - devam: kontrol yapilmadi VEYA kontrol yapildi ama ne TP ne SL
    - sl: sl_ok=True ve hicbir TP true degil
    Oran = basarili / (basarili + sl + devam)
    """
    bugun = gun_str()
    if snapshot is not None:
        kayitlar = [s for s in snapshot if s.get("gun") == bugun]
    else:
        with gunluk_kilit:
            kayitlar = [s for s in gunluk_sinyaller if s.get("gun") == bugun]

    TF_GECERLI = {"1","5","15","60","240","D"}
    koin_istat = {}
    for s in kayitlar:
        sym = sembol_grup(s.get("symbol", ""))
        if not sym or sym == "OTHERS":
            continue
        tf = str(s.get("timeframe", "?"))
        if tf not in TF_GECERLI:
            continue
        # rapor_hesapla ile aynı mantık — tüm sinyaller sayılır, MEXC filtresi yok
        if sym not in koin_istat:
            koin_istat[sym] = {"tp": 0, "sl": 0, "devam": 0, "long": 0, "short": 0}
        sin = s.get("sinyal", "").upper()
        if any(x in sin for x in ["BUY", "LONG"]):
            koin_istat[sym]["long"] += 1
        else:
            koin_istat[sym]["short"] += 1
        # rapor_hesapla ile aynı mantık
        kontrol_yapildi = any(s.get(k) is not None for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"])
        if kontrol_yapildi:
            if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
                koin_istat[sym]["tp"] += 1
            elif not s.get("sl_ok"):
                koin_istat[sym]["devam"] += 1  # kontrol yapildi, ne TP ne SL
            else:
                koin_istat[sym]["sl"] += 1
        else:
            koin_istat[sym]["devam"] += 1  # henuz kontrol edilmedi

    sonuc = []
    for sym, v in koin_istat.items():
        # rapor_hesapla ile ayni: toplam = tp + devam (SL dahil degil, gorsel ile ayni)
        toplam = v["tp"] + v["sl"] + v["devam"]
        basarili = v["tp"]
        oran = round(basarili / toplam * 100, 1) if toplam > 0 else 0
        yon = "LONG" if v["long"] >= v["short"] else "SHORT"
        sonuc.append({"sym": sym, "oran": oran, "toplam": toplam, "tp": v["tp"], "yon": yon})

    sonuc.sort(key=lambda x: (-x["oran"], -x["tp"]))
    return sonuc


def top3_guncelle(snapshot=None):
    """Bugün %50+ başarı oranı olan tüm koinleri whitelist'e al.
    Tüm TF'lerde sadece bu koinlerden işlem açılır.
    Başarı verisi yoksa (güne yeni başlandıysa) whitelist boş → tüm koinler serbest.
    """
    global top3_whitelist
    sirala = koin_sirala_bugun(snapshot)
    if not sirala:
        with top3_kilit:
            top3_whitelist = []
        print(f"[WHITELIST] Veri yok — işlem açılmayacak (%{TRADE_WHITELIST_MIN_PERCENT}+ yok)")
        return []

    # TRADE_WHITELIST_MIN_PERCENT ve üzeri başarı oranına sahip tüm koinler
    elli_plus = [item["sym"] for item in sirala if item["oran"] >= TRADE_WHITELIST_MIN_PERCENT]

    with top3_kilit:
        top3_whitelist = elli_plus
    print(f"[WHITELIST] %{TRADE_WHITELIST_MIN_PERCENT}+ güncellendi: {top3_whitelist}")
    return elli_plus


def koin_sirala_metni(snapshot=None):
    """Saatlik rapora eklenecek koin sıralama metni."""
    sirala = koin_sirala_bugun(snapshot)
    if not sirala:
        return ""
    top3 = top3_guncelle(snapshot)
    satirlar = ["", "📊 <b>Koin Başarı Sıralaması (Bugün)</b>"]
    for i, item in enumerate(sirala[:10], 1):
        # TRADE_WHITELIST_MIN_PERCENT+ ise aktif işlem alınıyor
        aktif = item["oran"] >= TRADE_WHITELIST_MIN_PERCENT
        yildiz = "✅" if aktif else "  "
        yon_emoji = "🟢" if item["yon"] == "LONG" else "🔴"
        satirlar.append(
            f"{yildiz}{i}. <b>{item['sym']}</b> — %{item['oran']} "
            f"({item['tp']}/{item['toplam']}) {yon_emoji}{item['yon']}"
        )
    aktif_liste = [item["sym"] for item in sirala if item["oran"] >= TRADE_WHITELIST_MIN_PERCENT]
    if aktif_liste:
        satirlar.append(f"\n✅ <b>Aktif (%{TRADE_WHITELIST_MIN_PERCENT}+):</b> {', '.join(aktif_liste)}")
    else:
        satirlar.append("\n⚪ <b>Aktif:</b> Tüm koinler (henüz yeterli veri yok)")
    satirlar.append("\n<code>/sirala</code>")
    return "\n".join(satirlar)


def istatistik_hesapla(gun_filtre=None, snapshot=None):
    if snapshot is not None:
        kayitlar = [s for s in snapshot if gun_filtre is None or s["gun"] == gun_filtre]
    else:
        with gunluk_kilit:
            kayitlar = [s for s in gunluk_sinyaller
                        if gun_filtre is None or s["gun"] == gun_filtre]
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

    # Tüm Zamanlar için kayıp veri offset (05 Haziran 2026 00:30 itibarıyla)
    # Bot yeniden başladığında kaybolan 4982 sinyal burada telafi ediliyor
    if gun_filtre is None:
        OFFSET_TOPLAM       = 4982
        OFFSET_LONG         = 2338
        OFFSET_SHORT        = 2644
        OFFSET_TP_BASARILI  = 2185
        OFFSET_SL_TETIK     = 34
        toplam       += OFFSET_TOPLAM
        long_sayisi  += OFFSET_LONG
        short_sayisi += OFFSET_SHORT
        tp_basarili  += OFFSET_TP_BASARILI
        sl_tetiklenen += OFFSET_SL_TETIK
        kapanan      += OFFSET_TP_BASARILI + OFFSET_SL_TETIK

    basari_oran = round(tp_basarili / toplam * 100, 1) if toplam > 0 else 0
    return {
        "toplam": toplam, "long": long_sayisi, "short": short_sayisi,
        "tp_basarili": tp_basarili, "sl_tetiklenen": sl_tetiklenen,
        "devam_eden": devam_eden, "kapanan": kapanan, "basari_oran": basari_oran
    }


def istatistik_mesaji(snapshot=None):
    bugun = gun_str()
    b     = istatistik_hesapla(gun_filtre=bugun, snapshot=snapshot)
    t     = istatistik_hesapla(snapshot=snapshot)

    if snapshot is not None:
        bugun_kayitlar = [s for s in snapshot if s["gun"] == bugun]
        tum_kayitlar   = snapshot
    else:
        with gunluk_kilit:
            bugun_kayitlar = [s for s in gunluk_sinyaller if s["gun"] == bugun]
            tum_kayitlar   = list(gunluk_sinyaller)

    # En başarılı sembol — rapor görseli ile aynı timeframe'ler
    RAPOR_TF = {"1","5","15","60","240","D"}  # Görsel raporda gösterilen TF'ler
    sym_stats = {}
    for s in bugun_kayitlar:
        tf = str(s.get("timeframe","?"))
        if tf not in RAPOR_TF:
            continue  # Görsel raporda gösterilmeyen TF'leri atla
        sym = sembol_grup(s["symbol"])
        if sym not in sym_stats:
            sym_stats[sym] = {"toplam": 0, "basarili": 0}
        sym_stats[sym]["toplam"] += 1
        tp_ok = any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"])
        if tp_ok:
            sym_stats[sym]["basarili"] += 1

    # Debug log
    for sym, st in sorted(sym_stats.items(), key=lambda x: x[1]["toplam"], reverse=True):
        print(f"[ISTATISTIK] {sym}: {st['basarili']}/{st['toplam']} = %{round(st['basarili']/st['toplam']*100,1) if st['toplam']>0 else 0}")

    en_sym = max(
        ((sym, round(st["basarili"]/st["toplam"]*100, 1))
         for sym, st in sym_stats.items() if st["toplam"] >= 3),
        key=lambda x: x[1], default=("", -1)
    )

    # En başarılı zaman dilimi — sadece görsel rapordaki TF'ler
    tf_map_g = {"1":"1DK","5":"5DK","15":"15DK","60":"1SA","240":"4SA","D":"1G"}
    tf_stats = {}
    for s in bugun_kayitlar:
        tf = str(s.get("timeframe","?"))
        if tf not in tf_map_g:
            continue  # Görsel raporda gösterilmeyen TF'leri atla
        tf_goster = tf_map_g[tf]
        if tf_goster not in tf_stats:
            tf_stats[tf_goster] = {"toplam": 0, "basarili": 0}
        tf_stats[tf_goster]["toplam"] += 1
        if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
            tf_stats[tf_goster]["basarili"] += 1

    en_tf = max(
        ((tf, round(st["basarili"]/st["toplam"]*100, 1))
         for tf, st in tf_stats.items() if st["toplam"] >= 3),
        key=lambda x: x[1], default=("", -1)
    )

    # Tüm zamanlar en başarılı sembol (min 5 sinyal)
    if snapshot is not None:
        tum_kayitlar = snapshot
    else:
        with gunluk_kilit:
            tum_kayitlar = list(gunluk_sinyaller)

    sym_stats_t = {}
    for s in tum_kayitlar:
        sym = sembol_grup(s["symbol"])
        if sym not in sym_stats_t:
            sym_stats_t[sym] = {"toplam": 0, "basarili": 0}
        sym_stats_t[sym]["toplam"] += 1
        if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
            sym_stats_t[sym]["basarili"] += 1

    en_sym_t = max(
        ((sym, st["basarili"]/st["toplam"]*100) for sym, st in sym_stats_t.items() if st["toplam"] >= 5),
        key=lambda x: x[1], default=("", -1)
    )

    # Tüm zamanlar en başarılı zaman dilimi (min 5 sinyal)
    tf_stats_t = {}
    for s in tum_kayitlar:
        tf = s.get("timeframe","?")
        if tf not in tf_stats_t:
            tf_stats_t[tf] = {"toplam": 0, "basarili": 0}
        tf_stats_t[tf]["toplam"] += 1
        if any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"]):
            tf_stats_t[tf]["basarili"] += 1

    en_tf_t = max(
        ((tf_map_g.get(tf,tf), st["basarili"]/st["toplam"]*100) for tf, st in tf_stats_t.items() if st["toplam"] >= 5),
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
        f"🏆 Başarı Oranı: <b>%{t['basari_oran']}</b> ({t['tp_basarili']}/{t['toplam']})\n"
    )
    if en_sym_t[0]:
        mesaj += f"🥇 En Başarılı Sembol: <b>{en_sym_t[0]}</b> (%{round(en_sym_t[1],1)})\n"
    if en_tf_t[0]:
        mesaj += f"⏱ En Başarılı Zaman Dilimi: <b>{en_tf_t[0]}</b> (%{round(en_tf_t[1],1)})\n"
    mesaj += "\n<code>/istatistik</code>"
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


def rapor_hesapla(gun: str, snapshot=None):
    if snapshot is not None:
        kayitlar = [s for s in snapshot if s["gun"] == gun]
    else:
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
    msg += "\n<code>/rapor</code>"
    return msg


def rapor_gorsel(gun: str, snapshot=None):
    """Raporu koyu tema PNG olarak üretir — 5 kart + devam eden hücrelerde."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        import io
    except ImportError:
        return None

    matris, toplam_satir, tf_kullanilan, tf_goster, kayitlar = rapor_hesapla(gun, snapshot=snapshot)
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
    row_h = 1.25
    fig_w = max(10.0, 2.0 + n_tf * col_w)  # minimum 10 birim genişlik
    fig_h = 4.6 + n_sym * row_h

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor(BG)

    # Başlık
    ax.text(fig_w/2, fig_h - 0.25, "BEN KÜL YUTMAM — Günlük Rapor",
            ha="center", va="top", fontsize=16, fontweight="bold", color=TEXT_W)
    ax.text(fig_w/2, fig_h - 0.62, gun,
            ha="center", va="top", fontsize=12.5, color=HDR_COL)

    # 5 Metrik kart
    metrics = [
        ("Toplam Sinyal", str(toplam_sinyal),  TEXT_W),
        ("TP Başarılı",   str(tp_basarili),    "#5DC98A"),
        ("SL Tetiklenen", str(sl_tetiklenen),  "#E05C5C"),
        ("Devam Eden",    str(devam_eden),      "#E8A835"),
        ("Genel Başarı",  f"%{genel_oran}",    "#5B9CF6"),
    ]
    m_w = fig_w / 5
    kart_h = 0.90
    for i, (lbl, val, col) in enumerate(metrics):
        mx = i * m_w
        my = fig_h - 1.88
        ax.add_patch(FancyBboxPatch((mx + 0.06, my), m_w - 0.12, kart_h,
                                     boxstyle="round,pad=0.04", linewidth=0, facecolor=CARD_BG))
        ax.text(mx + m_w/2, my + kart_h - 0.18, lbl, ha="center", va="center",
                fontsize=8, color=HDR_COL)
        ax.text(mx + m_w/2, my + 0.30, val, ha="center", va="center",
                fontsize=16, fontweight="bold", color=col)

    # Tablo
    t_top  = fig_h - 2.36
    t_left = 1.55

    # Başlıklar
    ax.text(0.78, t_top + 0.34, "Parite", ha="center", va="center",
            fontsize=10, fontweight="bold", color=HDR_COL)
    for j, tf in enumerate(tf_kullanilan):
        x = t_left + j * col_w + col_w/2
        ax.text(x, t_top + 0.34, tf_goster.get(tf, tf),
                ha="center", va="center", fontsize=10, fontweight="bold", color=HDR_COL)
    ax.text(t_left + len(tf_kullanilan) * col_w + col_w/2, t_top + 0.34,
            "Toplam", ha="center", va="center", fontsize=10, fontweight="bold", color=HDR_COL)
    ax.axhline(t_top + 0.06, xmin=0.02, xmax=0.98, color="#22262F", linewidth=0.8)

    all_rows = semboller + ["TOPLAM"]
    for i, sym in enumerate(all_rows):
        y = t_top - i * row_h
        is_total = (sym == "TOPLAM")
        row_bg = TOTAL_BG if is_total else (ROW_ODD if i % 2 == 0 else ROW_EVEN)

        ax.add_patch(FancyBboxPatch((0.03, y - row_h + 0.04), fig_w - 0.06, row_h - 0.06,
                                     boxstyle="round,pad=0.02", linewidth=0, facecolor=row_bg, zorder=0))

        ax.text(0.78, y - row_h/2, sym, ha="center", va="center",
                fontsize=11, fontweight="bold" if is_total else "normal",
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
                                         col_w - 0.14, row_h - 0.14,
                                         boxstyle="round,pad=0.03", linewidth=0,
                                         facecolor=cell_bg(p if p is not None else 0, t_v), zorder=1))

            if t_v > 0:
                ax.text(x, y - 0.22, f"%{p}", ha="center", va="center",
                        fontsize=11, fontweight="bold", color=bar_col(p), zorder=2)
                ax.text(x, y - 0.55, f"{b_v}/{t_v}", ha="center", va="center",
                        fontsize=9.5, color=TEXT_W, zorder=2)
                if dev > 0:
                    ax.text(x, y - 0.84, f"+{dev} devam", ha="center", va="center",
                            fontsize=8, color="#E8A835", zorder=2)
                bw = col_w - 0.36
                bx = x - bw/2
                by = y - row_h + 0.13
                ax.add_patch(plt.Rectangle((bx, by), bw, 0.07, color=BAR_TRACK, zorder=2))
                ax.add_patch(plt.Rectangle((bx, by), bw * p/100, 0.07, color=bar_col(p), zorder=3))
            elif dev > 0:
                ax.text(x, y - row_h/2, f"+{dev} devam", ha="center", va="center",
                        fontsize=8.5, color="#E8A835", zorder=2)
            else:
                ax.text(x, y - row_h/2, "—", ha="center", va="center",
                        fontsize=11, color="#3A3F4A", zorder=2)

        if is_total:
            ax.axhline(y + 0.05, xmin=0.02, xmax=0.98, color="#333740", linewidth=0.8)

    ax.text(fig_w/2, 0.10, "Başarı: en az 1 TP vurulmuş  |  yeşil ≥%60  sarı ≥%35  kırmızı <%35  |  ~N nötr  +N devam",
            ha="center", va="bottom", fontsize=8, color="#3A3F4A")

    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150,
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# ==========================================
# GÜNLÜK ÖZET
# ==========================================

def gunluk_ozet_gonder():
    import datetime as dt_mod
    OZET_SAATLERI = [(5, 45), (11, 45), (17, 45), (23, 45)]

    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()

            # Sonraki hedef saati bul
            hedefler = [
                simdi.replace(hour=h, minute=m, second=0, microsecond=0)
                for h, m in OZET_SAATLERI
            ]
            gelecek = [h for h in hedefler if h > simdi]

            if gelecek:
                hedef = min(gelecek)
            else:
                # Bugün tüm saatler geçti, yarın 05:59
                yarin = simdi + dt_mod.timedelta(days=1)
                hedef = yarin.replace(hour=5, minute=45, second=0, microsecond=0)

            bekle = (hedef - simdi).total_seconds()
            print(f"[OZET] Sonraki ozet: {hedef.strftime('%H:%M')} TR ({int(bekle//60)} dk sonra)")
            time.sleep(bekle)
            _ozet_gonder()
            time.sleep(70)  # double-fire önleme
        except Exception as e:
            print(f"[OZET] Hata: {e}")
            time.sleep(60)


def _ozet_gonder():
    bugun = gun_str()
    print(f"[OZET] Istatistik ve rapor gonderiliyor. gun={bugun}")

    # 1) İstatistik mesajı — sadece gruba
    _telegram_topic_mesaj_gonder(TOPIC_RAPOR, istatistik_mesaji())

    # 2) Görsel rapor — sadece gruba
    img = rapor_gorsel(bugun)
    if img:
        _topic_foto_gonder_filigranli(TOPIC_RAPOR, img, f"Günlük Rapor — {bugun}\n/rapor")
    else:
        _telegram_topic_mesaj_gonder(TOPIC_RAPOR, rapor_mesaji(bugun))

    b = istatistik_hesapla(gun_filtre=bugun)
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
    global AUTO_TRADE_ENABLED, PNL_RAPOR_ENABLED
    raw = request.get_data(as_text=True).strip()
    if not raw:
        return jsonify({"error": "Bos mesaj"}), 400
    print(f"[RAW] {raw[:500]}")

    # Telegram bot komutu mu?
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and ("message" in data or "channel_post" in data):
            msg           = data.get("message") or data.get("channel_post")
            text          = msg.get("text", "").strip().lower()
            chat_id       = str(msg.get("chat", {}).get("id", ""))
            thread_id     = msg.get("message_thread_id")  # Hangi topic'ten geldi
            reply_msg     = msg.get("reply_to_message")   # Alıntılanan mesaj
            # Telegram HTML mesajlarında metin "text" alanında gelir, entities ayrıdır
            # HTML tag'leri kaldırarak düz metni al
            if reply_msg:
                reply_text = reply_msg.get("text", "") or reply_msg.get("caption", "")
                # <b>, <pre>, <code> gibi HTML tag'lerini temizle
                import re as _re
                reply_text = _re.sub(r"<[^>]+>", " ", reply_text).strip()
            else:
                reply_text = ""
            yetkili       = [x for x in [TELEGRAM_CHAT_ID, TELEGRAM_LOG_ID, TELEGRAM_GRUP_ID, MEXC_NOTIFY_CHAT_ID] if x]

            if text.startswith("/istatistik"):
                if chat_id in yetkili and thread_id == TOPIC_RAPOR:
                    _telegram_topic_mesaj_gonder(TOPIC_RAPOR, istatistik_mesaji())
                    print(f"[KOMUT] /istatistik islendi.")

            elif text.startswith("/sirala"):
                if chat_id in yetkili and thread_id == TOPIC_RAPOR:
                    koin_metni = koin_sirala_metni()
                    if koin_metni:
                        _telegram_topic_mesaj_gonder(TOPIC_RAPOR, koin_metni)
                    else:
                        _telegram_topic_mesaj_gonder(TOPIC_RAPOR, "⚪ Henüz yeterli veri yok — istatistik birikmedi.")
                    print(f"[KOMUT] /sirala islendi.")

            elif text.startswith("/rapor"):
                if chat_id in yetkili and thread_id == TOPIC_RAPOR:
                    gun = gun_str()
                    print(f"[KOMUT] /rapor basliyor. gun={gun}")
                    img = rapor_gorsel(gun)
                    if img:
                        _topic_foto_gonder_filigranli(TOPIC_RAPOR, img, f"Günlük Rapor — {gun}\n/rapor")
                        print(f"[KOMUT] /rapor gorsel gonderildi.")
                    else:
                        _telegram_topic_mesaj_gonder(TOPIC_RAPOR, rapor_mesaji(gun))

            elif text.startswith("/tp_rapor"):
                if chat_id in yetkili and thread_id == TOPIC_RAPOR:
                    print(f"[KOMUT] /tp_rapor basliyor.")
                    def _tp_rapor_gonder():
                        try:
                            with gunluk_kilit:
                                snapshot = list(gunluk_sinyaller)
                            veri      = _tp_kosul_rapor_hesapla(snapshot=snapshot)
                            gorseller = _tp_kosul_rapor_gorsel(veri=veri)
                            if gorseller:
                                for img, caption in gorseller:
                                    _topic_foto_gonder_filigranli(TOPIC_RAPOR, img, caption)
                                    time.sleep(2)
                                maddeler = _tp_kosul_yorum_uret(veri)
                                if maddeler:
                                    yorum_txt = "📊 <b>Otomatik Yorum</b>\n\n" + "\n".join(f"• {m}" for m in maddeler)
                                    _telegram_topic_mesaj_gonder(TOPIC_RAPOR, yorum_txt)
                            else:
                                _telegram_topic_mesaj_gonder(TOPIC_RAPOR, "⚠️ TP Koşul Raporu: Yeterli veri yok.")
                        except Exception as e:
                            print(f"[TP_RAPOR] Hata: {e}")
                            _telegram_topic_mesaj_gonder(TOPIC_RAPOR, f"⚠️ TP Raporu hatası: {e}")
                    threading.Thread(target=_tp_rapor_gonder, daemon=True).start()

            elif text.startswith("/tarayici"):
                if chat_id in yetkili and thread_id == TOPIC_YUKSELENLER:
                    print(f"[KOMUT] /tarayici islendi.")
                    threading.Thread(target=_tarayici_gonder, daemon=True).start()

            elif text.startswith("/ls"):
                if chat_id in yetkili and thread_id == TOPIC_ANALIZ:
                    print(f"[KOMUT] /ls islendi.")
                    threading.Thread(target=lambda: _ls_gonder(), daemon=True).start()

            elif TOPIC_OLTA and thread_id == TOPIC_OLTA and chat_id in yetkili:
                # /skor — alıntılanan olta mesajını kontrol et
                if text.startswith("/skor") and reply_text:
                    print(f"[OLTA] /skor komutu — alıntı parse ediliyor")
                    def _skor_gonder(rt):
                        global _son_olta_cache
                        try:
                            print(f"[SKOR] Parse basliyor, reply_text uzunlugu: {len(rt)}")
                            # Önce cache ts'sini al — parse başarılı olsa bile kullanılacak
                            cache = _son_olta_cache.get(TOPIC_OLTA)
                            cache_ts = cache.get("ts") if cache else None
                            sonuc = _olta_skor_kontrol(rt, cache_ts=cache_ts)
                            # Parse basarisizsa cache'e bak
                            if not sonuc:
                                cache = _son_olta_cache.get(TOPIC_OLTA)
                                if cache:
                                    print("[SKOR] reply_text yetersiz, cache kullaniliyor")
                                    fmt = cache.get("format", "")
                                    cache_ts = cache.get("ts")
                                    if fmt == "tablo":
                                        import re as _re
                                        rt_upper = rt.upper()
                                        if "SHORT" in rt_upper:
                                            p = _olta_skor_parse(cache.get("short_msg", ""))
                                            if p and cache_ts: p["ts"] = cache_ts
                                            sonuc = _olta_skor_kontrol_parsed(p) if p else None
                                        elif "LONG" in rt_upper:
                                            p = _olta_skor_parse(cache.get("long_msg", ""))
                                            if p and cache_ts: p["ts"] = cache_ts
                                            sonuc = _olta_skor_kontrol_parsed(p) if p else None
                                        else:
                                            pl = _olta_skor_parse(cache.get("long_msg",  ""))
                                            ps = _olta_skor_parse(cache.get("short_msg", ""))
                                            if pl and cache_ts: pl["ts"] = cache_ts
                                            if ps and cache_ts: ps["ts"] = cache_ts
                                            sl = _olta_skor_kontrol_parsed(pl) if pl else None
                                            ss = _olta_skor_kontrol_parsed(ps) if ps else None
                                            if sl: _telegram_topic_mesaj_gonder(TOPIC_OLTA, sl)
                                            if ss:
                                                time.sleep(0.3)
                                                _telegram_topic_mesaj_gonder(TOPIC_OLTA, ss)
                                            return
                                    elif fmt == "eski":
                                        parsed = cache.get("parsed")
                                        if parsed and cache_ts: parsed["ts"] = cache_ts
                                        if parsed:
                                            sonuc = _olta_skor_kontrol_parsed(parsed)
                                        else:
                                            sonuc = _olta_skor_kontrol(cache.get("metin", ""))
                                else:
                                    print("[SKOR] Cache de bos!")
                            if sonuc:
                                print(f"[SKOR] Sonuc gonderiliyor ({len(sonuc)} karakter)")
                                _telegram_topic_mesaj_gonder(TOPIC_OLTA, sonuc)
                            else:
                                _telegram_topic_mesaj_gonder(TOPIC_OLTA,
                                    "⚠️ Olta mesajı okunamadı.\nBTC veya BTC TUM yazıp tekrar deneyin.")
                        except Exception as e:
                            print(f"[SKOR] Hata: {traceback.format_exc()}")
                            _telegram_topic_mesaj_gonder(TOPIC_OLTA, f"⚠️ Hata: {e}")
                    threading.Thread(target=_skor_gonder, args=(reply_text,), daemon=True).start()

                # "olta ver" → BTC/ETH/SOL/XRP tum TF tablo
                elif text.lower().strip() == "olta ver":
                    print(f"[OLTA] 'olta ver' komutu alindi")
                    def _olta_ver_gonder():
                        try:
                            _telegram_topic_mesaj_gonder(TOPIC_OLTA, "⏳ Tüm coinler hesaplanıyor...")
                            long_bytes, short_bytes = _olta_ver_tablo()
                            _telegram_topic_foto_gonder(TOPIC_OLTA, long_bytes, "")
                            time.sleep(0.5)
                            _telegram_topic_foto_gonder(TOPIC_OLTA, short_bytes, "")
                        except Exception as e:
                            print(f"[OLTA-VER] Hata: {traceback.format_exc()}")
                            _telegram_topic_mesaj_gonder(TOPIC_OLTA, f"⚠️ Hata: {e}")
                    threading.Thread(target=_olta_ver_gonder, daemon=True).start()

                # Kullanıcı olta topic'ine parite yazdı
                # "BTC"     → eski 15dk EMA olta (tek mesaj)
                # "BTC TUM" → Fibonacci multi-TF olta (long + short 2 mesaj)
                elif not text.startswith("/"):
                    symbol_raw = msg.get("text", "").strip()
                    if symbol_raw:
                        print(f"[OLTA] Sorgu: {symbol_raw}")
                        parcalar = symbol_raw.upper().split()
                        tum_mod  = len(parcalar) >= 2 and parcalar[-1] in ("TUM", "TÜM", "ALL")
                        sym_part = parcalar[0]
                        def _olta_gonder(sym, tum):
                            global _son_olta_cache
                            try:
                                if tum:
                                    long_msg, short_msg = _olta_mtf_sorgula(sym)
                                    _telegram_topic_mesaj_gonder(TOPIC_OLTA, long_msg)
                                    time.sleep(0.5)
                                    _telegram_topic_mesaj_gonder(TOPIC_OLTA, short_msg)
                                    import re as _re, time as _time
                                    _son_olta_cache[TOPIC_OLTA] = {
                                        "long_msg":  _re.sub(r"<[^>]+>", " ", long_msg).strip(),
                                        "short_msg": _re.sub(r"<[^>]+>", " ", short_msg).strip(),
                                        "format": "tablo",
                                        "ts": int(_time.time())
                                    }
                                    print(f"[OLTA] Cache kaydedildi: {sym} tablo format")
                                    _olta_cache_kaydet()
                                else:
                                    cevap = _olta_sorgula(sym)
                                    _telegram_topic_mesaj_gonder(TOPIC_OLTA, cevap)
                                    # Cache: parse edilmis dict olarak sakla (HTML sorununu onler)
                                    import re as _re
                                    cevap_temiz = _re.sub(r"<[^>]+>", " ", cevap).strip()
                                    parsed = _olta_skor_parse(cevap_temiz)
                                    import time as _time
                                    _son_olta_cache[TOPIC_OLTA] = {
                                        "parsed": parsed,
                                        "metin":  cevap_temiz,
                                        "format": "eski",
                                        "ts": int(_time.time())
                                    }
                                    print(f"[OLTA] Cache kaydedildi: {sym} eski format, parse={'OK' if parsed else 'FAIL'}")
                                    _olta_cache_kaydet()
                            except Exception as e:
                                print(f"[OLTA] Hata: {traceback.format_exc()}")
                                _telegram_topic_mesaj_gonder(TOPIC_OLTA, f"⚠️ Hata: {e}")
                        threading.Thread(target=_olta_gonder, args=(sym_part, tum_mod,), daemon=True).start()

            elif text.startswith("/trendyonu") or text.startswith("/trend"):
                if chat_id in yetkili and thread_id == TOPIC_ANALIZ:
                    print(f"[KOMUT] /trendyonu islendi.")
                    threading.Thread(target=lambda: _trend_gonder(), daemon=True).start()

            elif text.startswith("/hl_test"):
                if chat_id in yetkili and thread_id == TOPIC_BALINA:
                    def _hl_test():
                        satirlar = ["🧪 Hyperliquid API Testi:\n"]
                        adresler = [
                            "0x08c14b32c8a48894e4b933090ebcc9ce33b21135",
                            "0x3ee505ba316879d246a8fd2b3d7ee63b51b44fab",
                        ]
                        for adres in adresler:
                            try:
                                r = requests.post(
                                    "https://api.hyperliquid.xyz/info",
                                    json={"type": "clearinghouseState", "user": adres},
                                    headers={"Content-Type": "application/json"},
                                    timeout=8
                                )
                                if r.status_code == 200:
                                    data = r.json()
                                    pozisyonlar = data.get("assetPositions", [])
                                    satirlar.append(f"✅ {adres[:10]}... → {len(pozisyonlar)} pozisyon")
                                    for p in pozisyonlar[:3]:
                                        pos = p.get("position", {})
                                        satirlar.append(f"   {pos.get('coin')} {pos.get('szi')} @ {pos.get('entryPx')}")
                                else:
                                    satirlar.append(f"❌ {adres[:10]}...: HTTP {r.status_code}")
                            except Exception as e:
                                satirlar.append(f"❌ {adres[:10]}...: {str(e)[:60]}")
                        _telegram_topic_mesaj_gonder(TOPIC_BALINA, "\n".join(satirlar))
                    threading.Thread(target=_hl_test, daemon=True).start()

            elif text.startswith("/hl_durum"):
                if chat_id in yetkili and thread_id == TOPIC_BALINA:
                    print(f"[KOMUT] /hl_durum islendi.")
                    def _hl_durum_gonder():
                        if TR_TZ:
                            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
                        else:
                            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
                        ayrac = "-" * 32
                        print(f"[HL_DURUM] Basliyor. {len(HL_CUZDANLAR)} cuzdan.")
                        for adres, isim in HL_CUZDANLAR.items():
                            try:
                                print(f"[HL_DURUM] {isim} sorgulanıyor...")
                                pozlar = _hl_pozisyon_cek(adres)
                                print(f"[HL_DURUM] {isim}: {len(pozlar) if pozlar else 0} pozisyon")
                                if not pozlar:
                                    continue
                                sirali = sorted(
                                    [(c, p) for c, p in pozlar.items()
                                     if abs(p["szi"]) * p["entryPx"] >= HL_MIN_USD],
                                    key=lambda x: abs(x[1]["szi"]) * x[1]["entryPx"],
                                    reverse=True
                                )
                                print(f"[HL_DURUM] {isim}: sirali={len(sirali)} HL_MIN_USD={HL_MIN_USD}")
                                if not sirali:
                                    continue

                                long_satirlar  = []
                                short_satirlar = []

                                for coin, p in sirali:
                                    szi      = p["szi"]
                                    entry_px = p["entryPx"]
                                    pnl      = p["unrealizedPnl"]
                                    usd      = abs(szi) * entry_px
                                    if usd >= 1e6:
                                        usd_str = f"${usd/1e6:.1f}M"
                                    else:
                                        usd_str = f"${usd/1e3:.0f}K"
                                    if entry_px >= 1000:
                                        px_str = f"${entry_px:,.0f}"
                                    elif entry_px >= 1:
                                        px_str = f"${entry_px:.2f}"
                                    else:
                                        px_str = f"${entry_px:.4f}"
                                    pnl_str = (f"+${pnl/1e3:.1f}K" if pnl >= 0 else f"-${abs(pnl)/1e3:.1f}K")
                                    coin_p  = coin[:7].ljust(7)
                                    usd_p   = usd_str.rjust(6)
                                    px_p    = px_str.rjust(10)
                                    pnl_p   = pnl_str.rjust(9)
                                    satir   = f"{coin_p} {usd_p} {px_p} {pnl_p}"
                                    if szi > 0:
                                        long_satirlar.append(satir)
                                    else:
                                        short_satirlar.append(satir)

                                baslik_satir = f"{'COİN':<7} {'BOYUT':>6} {'GİRİŞ':>10} {'PnL':>9}"
                                ayrac2 = "-" * len(baslik_satir)

                                msg  = f"❗ <b>BEN KÜL YUTMAM</b> ❗\n\n"
                                msg += f"🐋 <b>{isim} — Hyperliquid</b>\n"
                                msg += f"🕐 {zaman_str}\n\n"

                                if long_satirlar:
                                    msg += "🚀 <b>Long Pozisyonlar</b>\n"
                                    msg += "<pre>"
                                    msg += baslik_satir + "\n"
                                    msg += ayrac2 + "\n"
                                    msg += "\n".join(long_satirlar)
                                    msg += "</pre>\n\n"

                                if short_satirlar:
                                    msg += "📉 <b>Short Pozisyonlar</b>\n"
                                    msg += "<pre>"
                                    msg += baslik_satir + "\n"
                                    msg += ayrac2 + "\n"
                                    msg += "\n".join(short_satirlar)
                                    msg += "</pre>\n\n"

                                msg += f"İletişim: {KANAL_TAG}\n"
                                msg += ayrac
                                print(f"[HL_DURUM] {isim} mesaj gonderiliyor. GRUP_ID={TELEGRAM_GRUP_ID} TOPIC={TOPIC_BALINA}")
                                r = _telegram_topic_mesaj_gonder(TOPIC_BALINA, msg)
                                print(f"[HL_DURUM] {isim} sonuc: {r.status_code if r else 'None'}")
                                time.sleep(1)
                            except Exception as e:
                                print(f"[HL_DURUM] {isim} hata: {e}")
                    threading.Thread(target=_hl_durum_gonder, daemon=True).start()

            elif text.startswith("/liq"):
                if chat_id in yetkili and thread_id == TOPIC_ANALIZ:
                    print(f"[KOMUT] /liq islendi.")
                    threading.Thread(target=_liq_gonder, daemon=True).start()

            elif text.startswith("/marketyonu"):
                if chat_id in yetkili and thread_id == TOPIC_ANALIZ:
                    print(f"[KOMUT] /marketyonu islendi.")
                    threading.Thread(target=_marketyonu_gonder, daemon=True).start()

            elif text.startswith("/analiz"):
                if chat_id in yetkili and thread_id == TOPIC_ANALIZ:
                    print(f"[KOMUT] /analiz islendi.")
                    threading.Thread(target=_analiz_gonder, daemon=True).start()

            elif text.startswith("/liq_test"):
                if chat_id in yetkili and thread_id == TOPIC_ANALIZ:
                    print(f"[KOMUT] /liq_test islendi.")
                    def _liq_test():
                        endpoints = [
                            ("BTC Funding Rate", "https://fapi.binance.com/fapi/v1/fundingRate",
                             {"symbol": "BTCUSDT", "limit": 3}),
                            ("BTC 24h Ticker", "https://fapi.binance.com/fapi/v1/ticker/24hr",
                             {"symbol": "BTCUSDT"}),
                            ("BTC Klines 1h", "https://fapi.binance.com/fapi/v1/klines",
                             {"symbol": "BTCUSDT", "interval": "1h", "limit": 24}),
                            ("BTC OI History", "https://fapi.binance.com/futures/data/openInterestHist",
                             {"symbol": "BTCUSDT", "period": "1h", "limit": 24}),
                        ]
                        for isim, url, params in endpoints:
                            try:
                                r = requests.get(url, params=params, timeout=8)
                                mesaj = f"<b>{isim}</b>: {r.status_code}\n<pre>{r.text[:200]}</pre>"
                            except Exception as e:
                                mesaj = f"<b>{isim}</b> hata: {str(e)[:100]}"
                            _telegram_topic_mesaj_gonder(TOPIC_ANALIZ, mesaj)
                            time.sleep(1)
                    threading.Thread(target=_liq_test, daemon=True).start()

            elif text.startswith("/haber"):
                if chat_id in yetkili and thread_id == TOPIC_HABER:
                    print(f"[KOMUT] /haber islendi.")
                    threading.Thread(target=_haber_kontrol, daemon=True).start()

            elif text.startswith("/trade_ac"):
                if chat_id in yetkili:
                    AUTO_TRADE_ENABLED = True
                    bot_durum_kaydet()
                    _mexc_topic_mesaj_gonder(
                        "✅ <b>Otomatik islem ACILDI</b>\nBir sonraki sinyalden itibaren MEXC emirleri acilacak.")
                    print("[KOMUT] AUTO_TRADE_ENABLED = True")

            elif text.startswith("/trade_kapat"):
                if chat_id in yetkili:
                    AUTO_TRADE_ENABLED = False
                    bot_durum_kaydet()
                    _mexc_topic_mesaj_gonder(
                        "🛑 <b>Otomatik islem KAPATILDI</b>\nMEXC emirleri durduruldu.")
                    print("[KOMUT] AUTO_TRADE_ENABLED = False")

            elif text.startswith("/pnl_kapat"):
                if str(chat_id) == str(MEXC_NOTIFY_CHAT_ID):
                    PNL_RAPOR_ENABLED = False
                    bot_durum_kaydet()
                    _telegram_mesaj_gonder(str(MEXC_NOTIFY_CHAT_ID),
                        "🛑 <b>PNL raporu KAPATILDI</b>\n15 dakikalık otomatik raporlar durduruldu.\n/pnl_ac ile tekrar açabilirsiniz.")
                    print("[KOMUT] PNL_RAPOR_ENABLED = False")

            elif text.startswith("/pnl_ac"):
                if str(chat_id) == str(MEXC_NOTIFY_CHAT_ID):
                    PNL_RAPOR_ENABLED = True
                    bot_durum_kaydet()
                    _telegram_mesaj_gonder(str(MEXC_NOTIFY_CHAT_ID),
                        "✅ <b>PNL raporu AÇILDI</b>\n15 dakikalık otomatik raporlar devam ediyor.")
                    print("[KOMUT] PNL_RAPOR_ENABLED = True")

            elif text.startswith("/gunluk_pnl") or text.startswith("/gunluk_PNL"):
                if chat_id in yetkili:
                    threading.Thread(target=_gunluk_pnl_gonder_topic,
                                     daemon=True).start()
                    print("[KOMUT] /gunluk_PNL islendi.")

            elif text.startswith("/rapor"):
                pass  # Yukarıda ele alındı

            else:
                if text.startswith("/"):
                    print(f"[KOMUT] Bilinmeyen komut veya yanlis topic: {text}")

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


    # ==========================================
    # MEXC FUTURES ORDER — A/B/C/D SENARYOLAR
    # ==========================================
    if AUTO_TRADE_ENABLED:
        try:
            print(f"[MEXC] AUTO_TRADE aktif — sinyal isleniyor: {symbol} {sinyal}")
            s_upper  = sinyal.upper()
            is_trade = any(x in s_upper for x in ["BUY","SELL","LONG","SHORT"])
            print(f"[MEXC] is_trade={is_trade} s_upper={s_upper}")
            if is_trade:
                is_long    = any(x in s_upper for x in ["BUY","LONG"])
                sym_key    = symbol.upper().replace(".P","")
                is_futures = str(symbol).upper().endswith(".P")
                print(f"[MEXC] is_long={is_long} sym_key={sym_key} is_futures={is_futures}")
                TF_SIR     = {"1":1,"3":2,"5":3,"15":4,"30":5,
                              "60":6,"1H":6,"240":7,"4H":7,"D":8,"1D":8}
                tf_yeni    = TF_SIR.get(str(timeframe), 0)
                print(f"[MEXC] tf_yeni={tf_yeni} timeframe={timeframe}")
                mp         = mexc_get_mark_price(symbol)
                print(f"[MEXC] mark_price={mp}")

                # SENARYO D: TP1 zaten gecildi mi? (%0.1 tolerans — tam esitlikte emir acilsin)
                tp1_gecildi = False
                if tp1 and mp:
                    try:
                        tp1_f = float(str(tp1).replace(",","."))
                        tolerans = tp1_f * 0.0002  # %0.02 — daha dar tolerans
                        if is_long and mp > tp1_f + tolerans:     tp1_gecildi = True
                        elif not is_long and mp < tp1_f - tolerans: tp1_gecildi = True
                    except: pass

                print(f"[MEXC] tp1_gecildi={tp1_gecildi} tp1={tp1} mp={mp}")

                # Hedge muafiyeti: SADECE API'den gelen GERÇEK açık pozisyona bak
                # aktif_pozisyonlar dict'i whitelist bypass için KULLANILMAZ
                # Yalnızca TERS yön aktif pozisyon varsa whitelist atlanır
                _api_long  = pozisyon_al(sym_key, True)   # API'den long pozisyon
                _api_short = pozisyon_al(sym_key, False)  # API'den short pozisyon
                # Ters yön var mı? LONG sinyali geldi → aktif SHORT var mı? (veya tersi)
                _wl_hedge = (
                    (is_long  and bool(_api_short)) or   # LONG sinyal + aktif SHORT → hedge
                    (not is_long and bool(_api_long))     # SHORT sinyal + aktif LONG → hedge
                )
                print(f"[MEXC] wl_hedge={_wl_hedge} api_long={bool(_api_long)} api_short={bool(_api_short)}")

                if not is_futures:
                    print("[MEXC] " + symbol + " futures degil, atlandi.")
                elif not top3_whitelist and not _wl_hedge:
                    print(f"[MEXC] {timeframe}dk sinyal, {sym_key} atlandı — whitelist bos (%{TRADE_WHITELIST_MIN_PERCENT}+ yok)")
                elif sym_key.replace("USDT","") not in top3_whitelist and not _wl_hedge:
                    print(f"[MEXC] {timeframe}dk sinyal, {sym_key} %{TRADE_WHITELIST_MIN_PERCENT}+ whitelist'te degil — islem atlandı. Whitelist: {top3_whitelist}")
                else:
                    # Mevcut pozisyonu bul — önce API, sonra dict
                    mevcut = pozisyon_al(sym_key, is_long)
                    # Hedge pozisyonu da kontrol et — aynı yön hedge varsa revize edilebilir
                    # API'den doğrula: dict'te kayıt olsa bile gerçek pozisyon yoksa kullanma
                    hedge_mevcut = None
                    with pozisyon_kilit:
                        hedge_mevcut = aktif_pozisyonlar.get(sym_key + "_HEDGE")
                    if not mevcut and hedge_mevcut and hedge_mevcut.get("is_long") == is_long:
                        _api_hedge_dogrula = pozisyon_al(sym_key, is_long)
                        if _api_hedge_dogrula:
                            mevcut = hedge_mevcut
                            mevcut["_is_hedge_pos"] = True
                            print(f"[MEXC] Hedge pozisyonu bulundu (API doğrulandı) — revize edilecek: {sym_key}_HEDGE")
                        else:
                            print(f"[MEXC] Hedge dict kaydı var ama API'de pozisyon yok — {sym_key}_HEDGE atlandı, temizleniyor")
                            with pozisyon_kilit:
                                aktif_pozisyonlar.pop(sym_key + "_HEDGE", None)
                            pozisyon_kaydet()
                    print(f"[MEXC] mevcut_pozisyon={mevcut}")

                    # SENARYO 3/D: Mevcut yoksa TP1 geçildi mi kontrolü
                    if not mevcut and tp1_gecildi:
                        print(f"[MEXC] SENARYO 3 — TP1 gecildi, islem atlandı")
                        mexc_notify(symbol, sinyal,
                            bilgi_msg=f"⛔ İşlem Açılmadı\nTP1 zaten geçilmiş\nTP1: {tp1} | Mark: {mp}")
                    elif mevcut:
                        mevcut_long = mevcut["is_long"]
                        tf_mevcut   = TF_SIR.get(str(mevcut.get("timeframe","1")), 0)

                        # Açık HEDGE kontrolü — her durumda önceden yap
                        _acik_hedge = None
                        with pozisyon_kilit:
                            _acik_hedge = aktif_pozisyonlar.get(sym_key + "_HEDGE")

                        if mevcut_long != is_long and _acik_hedge and _acik_hedge.get("is_long") == is_long:
                            # SENARYO 2a: Ters yön ama zaten açık HEDGE var — +0.2 USDT ekle, daha uzak TP/SL seç
                            tp1_mevcut_h = _acik_hedge.get("tp1")
                            sl_mevcut_h  = _acik_hedge.get("sl")
                            try:
                                tp1_mevcut_h_f = float(str(tp1_mevcut_h).replace(",", ".")) if tp1_mevcut_h else None
                            except:
                                tp1_mevcut_h_f = None
                            try:
                                sl_mevcut_h_f = float(str(sl_mevcut_h).replace(",", ".")) if sl_mevcut_h else None
                            except:
                                sl_mevcut_h_f = None

                            # Daha uzak TP seç
                            tp_adaylar_2a = []
                            for _tp in [tp1, tp2, tp3, tp4, tp5]:
                                try:
                                    _f = float(str(_tp).replace(",", ".")) if _tp and str(_tp) not in ("None", "null", "") else None
                                    if _f: tp_adaylar_2a.append(_f)
                                except: pass

                            tp_sec_2a = None
                            if tp_adaylar_2a and tp1_mevcut_h_f:
                                if is_long:
                                    _uzak = max(tp_adaylar_2a)
                                    if _uzak > tp1_mevcut_h_f:
                                        tp_sec_2a = _uzak
                                else:
                                    _uzak = min(tp_adaylar_2a)
                                    if _uzak < tp1_mevcut_h_f:
                                        tp_sec_2a = _uzak
                            elif tp_adaylar_2a:
                                tp_sec_2a = max(tp_adaylar_2a) if is_long else min(tp_adaylar_2a)

                            # Daha uzak SL seç
                            sl_sec_2a = None
                            try:
                                sl_yeni_2a_f = float(str(sl).replace(",", ".")) if sl and str(sl) not in ("None", "null", "") else None
                            except:
                                sl_yeni_2a_f = None
                            if sl_yeni_2a_f and sl_mevcut_h_f:
                                if is_long and sl_yeni_2a_f < sl_mevcut_h_f:
                                    sl_sec_2a = sl_yeni_2a_f
                                elif not is_long and sl_yeni_2a_f > sl_mevcut_h_f:
                                    sl_sec_2a = sl_yeni_2a_f
                            if sl_sec_2a is None:
                                sl_sec_2a = sl_mevcut_h_f or sl_yeni_2a_f

                            tp_kullan_2a = tp_sec_2a if tp_sec_2a else tp1_mevcut_h_f
                            sl_kullan_2a = sl_sec_2a

                            guc_margin_2a = MEXC_MARGIN_USDT
                            print(f"[MEXC] SENARYO 2a GUC — HEDGE güçlendiriliyor: +{MEXC_MARGIN_USDT} USDT, TP={tp_kullan_2a}, SL={sl_kullan_2a}")
                            sonuc_2a = mexc_place_order(symbol, sinyal, tp_kullan_2a, sl_kullan_2a,
                                                        hedge=True, margin_override=guc_margin_2a)
                            if sonuc_2a and sonuc_2a["success"]:
                                with pozisyon_kilit:
                                    if sym_key + "_HEDGE" in aktif_pozisyonlar:
                                        aktif_pozisyonlar[sym_key + "_HEDGE"].update({
                                            "timeframe": timeframe, "sinyal": sinyal,
                                            "tp1": tp_kullan_2a, "sl": sl_kullan_2a
                                        })
                                pozisyon_kaydet()
                                mexc_notify(symbol, sinyal,
                                    bilgi_msg=(
                                        f"💪 Pozisyon Güçlendirildi (Hedge)\n"
                                        f"Marjin: +{MEXC_MARGIN_USDT} USDT eklendi\n"
                                        f"TP: {tp1_mevcut_h_f} → {tp_kullan_2a}\n"
                                        f"SL: {sl_mevcut_h_f} → {sl_kullan_2a}"))
                            elif sonuc_2a:
                                mexc_notify(symbol, sinyal, hata_msg=sonuc_2a.get("msg", "Hata"))

                        elif mevcut_long != is_long and not (_acik_hedge and _acik_hedge.get("is_long") == is_long):
                            # SENARYO 2: Ters yon — HEDGE
                            # Hedge için EN UZAK TP kullanılır (TP5→TP4→TP3→TP2→TP1), fallback yok
                            tp1_hedge, fee_notu_hedge = tp_uzak_sec(
                                mp, tp1, tp2, is_long, tp3, tp4, tp5, symbol=symbol)
                            if tp1_hedge is None:
                                print(f"[MEXC] SENARYO 2 HEDGE — tüm TP'ler yetersiz, işlem atlandı")
                                mexc_notify(symbol, sinyal,
                                    bilgi_msg=f"⛔ HEDGE açılmadı\n{fee_notu_hedge}")
                            else:
                                # Hedge marjini: önceki pozisyonun GERÇEK marjininin 2 katı
                                # 1) Bot kaydından bak (bot açtıysa mexc_oim var)
                                # 2) Yoksa MEXC API'den gerçek marjini çek (manuel işlem)
                                # 3) İkisi de yoksa global ayar * 2
                                onceki_margin = MEXC_MARGIN_USDT
                                manuel_acilis = mevcut.get("sinyal") == "RECOVERY"
                                try:
                                    onceki_oim = float(mevcut.get("mexc_oim", 0) or 0)
                                    if onceki_oim > 0:
                                        # Bot tarafından açılmış — kayıtlı marjin güvenilir
                                        onceki_margin = onceki_oim
                                        print(f"[HEDGE] Bot kaydından marjin: {onceki_margin} USDT")
                                    else:
                                        # Manuel açılmış veya RECOVERY — MEXC'ten gerçek marjini çek
                                        detay = mexc_pozisyon_detay(symbol, mevcut_long)
                                        if detay and detay["im"] > 0:
                                            onceki_margin = detay["im"]
                                            print(f"[HEDGE] MEXC API'den marjin: {onceki_margin} USDT (manuel pozisyon)")
                                        else:
                                            print(f"[HEDGE] Marjin alınamadı — global ayar kullanılıyor: {MEXC_MARGIN_USDT} USDT")
                                    hedge_margin_ham = round(onceki_margin * 2, 4)
                                    # Üst sınır: global MEXC_MARGIN_USDT'nin 2 katını aşamasın
                                    hedge_margin_max = round(MEXC_MARGIN_USDT * HEDGE_MARGIN_MULTIPLIER, 4)
                                    hedge_margin = min(hedge_margin_ham, hedge_margin_max)
                                    if hedge_margin < hedge_margin_ham:
                                        print(f"[HEDGE] Marjin üst sınıra indirildi: {hedge_margin_ham} → {hedge_margin} USDT (max={hedge_margin_max})")
                                except Exception as _me:
                                    hedge_margin = round(MEXC_MARGIN_USDT * 2, 4)
                                    print(f"[HEDGE] Marjin hesap hatası: {_me}, fallback={hedge_margin}")

                                manuel_notu = "\n⚠️ Manuel pozisyon tespit edildi — API'den marjin alındı" if manuel_acilis else ""
                                print(f"[HEDGE] Önceki marjin: {onceki_margin} → Hedge marjin: {hedge_margin} (max={round(MEXC_MARGIN_USDT*HEDGE_MARGIN_MULTIPLIER,4)}) {'(manuel)' if manuel_acilis else '(bot)'}") 
                                sonuc = mexc_place_order(symbol, sinyal, tp1_hedge, sl,
                                                         hedge=True, margin_override=hedge_margin)
                                if sonuc and sonuc["success"]:
                                    with pozisyon_kilit:
                                        aktif_pozisyonlar[sym_key+"_HEDGE"] = {
                                            "is_long": is_long, "timeframe": timeframe,
                                            "sinyal": sinyal, "order_id": sonuc["order_id"],
                                            "vol": sonuc["vol"], "tp1": tp1_hedge, "sl": sl,
                                            "hedge_margin": hedge_margin}
                                    pozisyon_kaydet()
                                    yon_m = "LONG" if mevcut_long else "SHORT"
                                    yon_y = "LONG" if is_long else "SHORT"
                                    fee_ek = f"\n⚠️ {fee_notu_hedge}" if fee_notu_hedge else ""
                                    mexc_notify(symbol, sinyal,
                                        bilgi_msg=(
                                            f"🔀 HEDGE Açıldı\n"
                                            f"{yon_m} açık kaldı | {yon_y} hedge açıldı\n"
                                            f"TP: {tp1_hedge} | SL: {sl}\n"
                                            f"Marjin: {hedge_margin} USDT (2×){manuel_notu}\n"
                                            f"Order: {sonuc['order_id']}{fee_ek}"))
                                elif sonuc:
                                    mexc_notify(symbol, sinyal, hata_msg=sonuc.get("msg", "Hata"))

                        else:
                            # SENARYO 1+4: Aynı yön — +0.2 USDT marjin ekle, daha uzak TP/SL seç
                            _poz_key = (sym_key + "_HEDGE") if mevcut.get("_is_hedge_pos") else sym_key
                            hedge_notu = " (Hedge)" if mevcut.get("_is_hedge_pos") else ""

                            # Mevcut TP ve SL
                            tp1_mevcut_str = mevcut.get("tp1")
                            sl_mevcut_str  = mevcut.get("sl")
                            try:
                                tp1_mevcut_f = float(str(tp1_mevcut_str).replace(",", ".")) if tp1_mevcut_str else None
                            except:
                                tp1_mevcut_f = None
                            try:
                                sl_mevcut_f = float(str(sl_mevcut_str).replace(",", ".")) if sl_mevcut_str else None
                            except:
                                sl_mevcut_f = None

                            # Daha uzak TP seç — LONG için büyük, SHORT için küçük
                            tp_adaylar = []
                            for _tp in [tp1, tp2, tp3, tp4, tp5]:
                                try:
                                    _f = float(str(_tp).replace(",", ".")) if _tp and str(_tp) not in ("None", "null", "") else None
                                    if _f: tp_adaylar.append(_f)
                                except: pass

                            tp_sec = None
                            if tp_adaylar and tp1_mevcut_f:
                                if is_long:
                                    _uzak = max(tp_adaylar)
                                    if _uzak > tp1_mevcut_f:
                                        tp_sec = _uzak
                                else:
                                    _uzak = min(tp_adaylar)
                                    if _uzak < tp1_mevcut_f:
                                        tp_sec = _uzak
                            elif tp_adaylar:
                                tp_sec = max(tp_adaylar) if is_long else min(tp_adaylar)

                            # Daha uzak SL seç — LONG için küçük, SHORT için büyük
                            sl_sec = None
                            try:
                                sl_yeni_f = float(str(sl).replace(",", ".")) if sl and str(sl) not in ("None", "null", "") else None
                            except:
                                sl_yeni_f = None

                            if sl_yeni_f and sl_mevcut_f:
                                if is_long and sl_yeni_f < sl_mevcut_f:
                                    sl_sec = sl_yeni_f
                                elif not is_long and sl_yeni_f > sl_mevcut_f:
                                    sl_sec = sl_yeni_f
                            if sl_sec is None:
                                sl_sec = sl_mevcut_f or sl_yeni_f

                            tp_kullan  = tp_sec if tp_sec else tp1_mevcut_f
                            sl_kullan  = sl_sec

                            # HEDGE VAR: +MEXC_MARGIN_USDT ekle, yeni emir aç
                            # HEDGE YOK: sadece TP/SL güncelle, marjin ekleme
                            if _wl_hedge:
                                guc_margin = round(MEXC_MARGIN_USDT + MEXC_MARGIN_USDT, 4)
                                print(f"[MEXC] SENARYO GUC (hedge var) — +{MEXC_MARGIN_USDT} USDT → {guc_margin} USDT, TP={tp_kullan}, SL={sl_kullan}")
                                sonuc_guc = mexc_place_order(symbol, sinyal, tp_kullan, sl_kullan,
                                                             hedge=True, margin_override=MEXC_MARGIN_USDT)
                                if sonuc_guc and sonuc_guc["success"]:
                                    with pozisyon_kilit:
                                        if _poz_key in aktif_pozisyonlar:
                                            aktif_pozisyonlar[_poz_key].update({
                                                "timeframe": timeframe, "sinyal": sinyal,
                                                "tp1": tp_kullan, "sl": sl_kullan
                                            })
                                        else:
                                            print(f"[MEXC] {_poz_key} güncelleme atlandı — pozisyon temizlenmiş")
                                    pozisyon_kaydet()
                                    mexc_notify(symbol, sinyal,
                                        bilgi_msg=(
                                            f"💪 Pozisyon Güçlendirildi{hedge_notu}\n"
                                            f"Marjin: {tp1_mevcut_f and round(float(mevcut.get('mexc_oim') or MEXC_MARGIN_USDT),4)} → +{MEXC_MARGIN_USDT} USDT\n"
                                            f"TP: {tp1_mevcut_f} → {tp_kullan}\n"
                                            f"SL: {sl_mevcut_f} → {sl_kullan}"))
                                elif sonuc_guc:
                                    mexc_notify(symbol, sinyal, hata_msg=sonuc_guc.get("msg", "Hata"))
                            else:
                                # Hedge yok — sadece TP/SL güncelle
                                print(f"[MEXC] SENARYO GUC (hedge yok) — sadece TP/SL güncelleniyor: TP={tp_kullan}, SL={sl_kullan}")
                                tpsl_ok = mexc_update_tpsl(symbol, is_long, tp_kullan, sl_kullan)
                                if tpsl_ok:
                                    with pozisyon_kilit:
                                        if _poz_key in aktif_pozisyonlar:
                                            aktif_pozisyonlar[_poz_key].update({
                                                "timeframe": timeframe, "sinyal": sinyal,
                                                "tp1": tp_kullan, "sl": sl_kullan
                                            })
                                    pozisyon_kaydet()
                                    mexc_notify(symbol, sinyal,
                                        bilgi_msg=(
                                            f"💪 Pozisyon Güçlendirildi{hedge_notu}\n"
                                            f"TP: {tp1_mevcut_f} → {tp_kullan}\n"
                                            f"SL: {sl_mevcut_f} → {sl_kullan}"))
                                else:
                                    mexc_notify(symbol, sinyal,
                                        bilgi_msg=f"🛡️ TP/SL güncellenmedi — API hatası")
                    else:
                        # Normal islem — SENARYO E: Yeni pozisyon
                        # Margin ratio son kontrolü — hedge işlemler muaf, sadece normal işlemler için
                        # API gecikmesi nedeniyle place_order içindeki kontrol geçebiliyor
                        _is_hedge_senaryo = bool(aktif_pozisyonlar.get(sym_key + "_HEDGE"))
                        if not _is_hedge_senaryo and mexc_margin_ratio_kontrol():
                            print(f"[MEXC] SENARYO E iptal — margin ratio esik ustunde: {symbol}")
                        else:
                            print(f"[MEXC] SENARYO E — Yeni pozisyon aciliyor: {symbol} {sinyal}")
                            # Karlılık kontrolü: eşiği geçen ilk TP'yi seç
                            tp1_yeni, fee_notu = tp1_karlilik_kontrol(
                                mp, tp1, tp2, is_long, tp3, tp4, tp5, symbol=symbol)
                            if tp1_yeni is None:
                                # Hiçbir TP yeterli değil — işlemi açma
                                print(f"[MEXC] SENARYO E — tüm TP'ler yetersiz, işlem atlandı")
                                mexc_notify(symbol, sinyal,
                                    bilgi_msg=f"⛔ İşlem açılmadı\n{fee_notu}")
                            else:
                                sonuc = mexc_place_order(symbol, sinyal, tp1_yeni, sl)
                            print(f"[MEXC] place_order sonuc: {sonuc}")
                            if sonuc and sonuc["success"]:
                                with pozisyon_kilit:
                                    aktif_pozisyonlar[sym_key] = {
                                        "is_long": is_long, "timeframe": timeframe,
                                        "sinyal": sinyal, "order_id": sonuc["order_id"],
                                        "vol": sonuc["vol"], "tp1": tp1_yeni, "sl": sl,
                                        "mark_price": sonuc.get("mark_price")}
                                pozisyon_kaydet()
                                mexc_msg_id = mexc_notify(symbol, sinyal,
                                            vol=sonuc["vol"], leverage=sonuc["leverage"],
                                            margin=MEXC_MARGIN_USDT,
                                            order_id=sonuc["order_id"],
                                            tp1=tp1_yeni, sl=sl,
                                            mark_price=sonuc.get("mark_price"),
                                            bilgi_msg=(f"⚠️ {fee_notu}" if fee_notu else None))
                                # mexc_msg_id ve mexc_acildi'yi sinyal kaydına ekle
                                # En son eklenen bu symbol kaydını bul (message_id ile)
                                with gunluk_kilit:
                                    for s in reversed(gunluk_sinyaller):
                                        if s.get("symbol") == symbol and not s.get("mexc_acildi"):
                                            s["mexc_msg_id"]    = mexc_msg_id
                                            s["mexc_acildi"]    = True
                                            s["mexc_leverage"]  = sonuc.get("leverage", 1)
                                            s["mexc_oim"]       = sonuc.get("oim", 0)
                                            s["vol"]            = sonuc.get("vol", 0)
                                            s["contract_size"]  = sonuc.get("contract_size", 1.0)
                                            print(f"[MEXC] mexc_acildi=True set edildi: {symbol} lev={sonuc.get('leverage',1)} oim={sonuc.get('oim',0):.4f}")
                                            break
                            elif sonuc:
                                mexc_notify(symbol, sinyal, hata_msg=sonuc.get("msg", "Hata"))
        except Exception as e:
            print("[MEXC WEBHOOK HATA] " + str(e))
            print("[MEXC WEBHOOK HATA] " + traceback.format_exc())

    t = threading.Thread(
        target=send_telegram_and_schedule_tp,
        args=(mesaj, symbol, timeframe, sinyal, tp1, tp2, tp3, tp4, tp5, sl, imageurl, price))
    t.daemon = True
    t.start()

    return jsonify({"status": "ok"}), 200


@app.route("/external_veri", methods=["POST"])
def external_veri():
    """GitHub Actions'dan gelen L/S ve LIQ verisini işle, grafik çiz, Telegram'a gönder."""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"ok": False, "msg": "Veri yok"}), 400

        secret = data.get("secret", "")
        if secret != os.getenv("EXTERNAL_VERI_SECRET", ""):
            return jsonify({"ok": False, "msg": "Yetkisiz"}), 403

        tip = data.get("tip")  # "ls" veya "liq"

        if tip == "ls":
            btc_ls = data.get("btc_ls", {"genel": [], "balina": []})
            eth_ls = data.get("eth_ls", {"genel": [], "balina": []})
            if TR_TZ:
                zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
            else:
                zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
            img = _ls_gorsel(btc_ls, eth_ls, zaman_str)
            if img:
                _topic_foto_gonder_filigranli(TOPIC_ANALIZ, img, f"📈 Long/Short Oran — 1S — {zaman_str}\n/ls")
                print(f"[LS] Gorsel gonderildi (external).")
            yorum = _ls_yorum(btc_ls, eth_ls)
            _telegram_topic_mesaj_gonder(TOPIC_ANALIZ, yorum)
            print(f"[LS] Tamamlandi (external).")
            return jsonify({"ok": True, "tip": "ls"})

        elif tip == "liq":
            for sym in ["BTCUSDT", "ETHUSDT"]:
                veri = data.get(sym)
                if not veri:
                    continue
                sym_kisa = sym.replace("USDT", "")
                if TR_TZ:
                    zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
                else:
                    zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
                heatmap_sonuc = _liq_heatmap_gercek(sym, saat=6)
                if heatmap_sonuc:
                    _topic_foto_gonder_filigranli(TOPIC_ANALIZ, heatmap_sonuc["img"],
                        f"🌡 {sym_kisa} Likidasyon Isı Haritası — {zaman_str}\n/liq")
                    time.sleep(1)
                    veri["liq_grid"] = heatmap_sonuc
                yorum = _liq_yorum(veri)
                _telegram_topic_mesaj_gonder(TOPIC_ANALIZ, yorum)
                print(f"[LIQ] {sym} gonderildi (external).")
                time.sleep(3)
            return jsonify({"ok": True, "tip": "liq"})

        return jsonify({"ok": False, "msg": "Bilinmeyen tip"}), 400

    except Exception as e:
        print(f"[EXTERNAL] Hata: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500



def health():
    ist = istatistik_hesapla()
    return jsonify({
        "status": "running",
        "version": BOT_VERSIYON,
        "time": time.strftime("%Y-%m-%d %H:%M UTC"),
        "toplam_sinyal": ist["toplam"],
        "basari_oran": f"%{ist['basari_oran']}"
    })


@app.route("/mexc_test")
def mexc_test():
    """MEXC baglanti ve imza tanisi — Railway loglarinda gormek icin"""
    sonuc = {"version": BOT_VERSIYON, "proxy": bool(MEXC_PRIVATE_PROXY)}
    # 0. Proxy testi — proxy uzerinden dis IP kontrolu
    if MEXC_PRIVATE_PROXY:
        try:
            r0 = requests.get("https://api.ipify.org?format=json",
                              timeout=10, proxies=MEXC_PRIVATE_PROXY)
            sonuc["proxy_ip"] = r0.json().get("ip", r0.text.strip())
        except Exception as e:
            sonuc["proxy_ip"] = f"HATA: {str(e)}"
    # 1. Public endpoint — imza yok, proxy yok
    try:
        r = requests.get("https://contract.mexc.com/api/v1/contract/ping", timeout=8)
        sonuc["public_ping"] = {"status": r.status_code, "body": r.text[:200]}
    except Exception as e:
        sonuc["public_ping"] = {"error": str(e)}
    # 2. Private endpoint — proxy ile
    if MEXC_API_KEY and MEXC_API_SECRET:
        try:
            r2 = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/account/assets")
            body = r2.json()
            sonuc["private_assets"] = {
                "status": r2.status_code,
                "success": body.get("success"),
                "message": body.get("message", ""),
            }
        except Exception as e:
            sonuc["private_assets"] = {"error": str(e)}
    else:
        sonuc["private_assets"] = {"error": "API key tanimli degil"}

    # 4. Imza debug — farkli kombinasyonlar
    if MEXC_API_KEY and MEXC_API_SECRET:
        ts_dbg = str(int(time.time() * 1000))
        test_body = {"symbol": "XRP_USDT", "vol": 1, "side": 1, "type": 5, "openType": 2, "leverage": 20}
        sorted_body = dict(sorted(test_body.items()))

        # Kombinasyon A: imza={}, json={}, params=body (v199 yontemi — 9999 vermisti)
        try:
            sign_a = MEXC_API_KEY + ts_dbg + "{}"
            sig_a = hmac.new(MEXC_API_SECRET.encode(), sign_a.encode(), hashlib.sha256).hexdigest()
            hdrs_a = {"ApiKey": MEXC_API_KEY, "Request-Time": ts_dbg, "Signature": sig_a,
                      "Content-Type": "application/json",
                      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                      "Origin": "https://futures.mexc.com", "Referer": "https://futures.mexc.com/exchange/BTC_USDT"}
            r_a = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                                headers=hdrs_a, json={}, params=sorted_body, timeout=8)
            sonuc["A_bos_json_params"] = {"status": r_a.status_code, "body": r_a.text[:150]}
        except Exception as e:
            sonuc["A_bos_json_params"] = {"error": str(e)[:50]}

        # Kombinasyon B: imza=body_json, json={}, params=body
        try:
            body_json = json.dumps(sorted_body, separators=(",",":"), sort_keys=True)
            sign_b = MEXC_API_KEY + ts_dbg + body_json
            sig_b = hmac.new(MEXC_API_SECRET.encode(), sign_b.encode(), hashlib.sha256).hexdigest()
            hdrs_b = {"ApiKey": MEXC_API_KEY, "Request-Time": ts_dbg, "Signature": sig_b,
                      "Content-Type": "application/json",
                      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                      "Origin": "https://futures.mexc.com", "Referer": "https://futures.mexc.com/exchange/BTC_USDT"}
            r_b = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                                headers=hdrs_b, json={}, params=sorted_body, timeout=8)
            sonuc["B_bodyjson_imza_params"] = {"status": r_b.status_code, "body": r_b.text[:150]}
        except Exception as e:
            sonuc["B_bodyjson_imza_params"] = {"error": str(e)[:50]}

        # Kombinasyon C: imza=body_json, json=body (normal yol — WAF gormemis gibi)
        try:
            r_c = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                                headers=hdrs_b, json=sorted_body, timeout=8)
            sonuc["C_bodyjson_imza_json"] = {"status": r_c.status_code, "body": r_c.text[:150]}
        except Exception as e:
            sonuc["C_bodyjson_imza_json"] = {"error": str(e)[:50]}
    # 3. POST domain testi — kucuk bir yanlis body ile 403 mi yoksa baska hata mi aliyor
    for domain in ["contract.mexc.com", "futures.mexc.com"]:
        try:
            test_url = f"https://{domain}/api/v1/private/order/create"
            hdrs_t, _ = mexc_headers({})
            r_t = requests.post(test_url, headers=hdrs_t, json={}, timeout=8)
            sonuc[f"post_test_{domain.split('.')[0]}"] = {
                "status": r_t.status_code,
                "body": r_t.text[:100]
            }
        except Exception as e:
            sonuc[f"post_test_{domain.split('.')[0]}"] = {"error": str(e)}
    # GET ile order submit dene
    if MEXC_API_KEY and MEXC_API_SECRET:
        try:
            ts = str(int(time.time() * 1000))
            test_body = {"symbol": "BTC_USDT", "vol": 1, "side": 1, "type": 5, "openType": 2, "leverage": 20, "price": 0}
            sorted_body = dict(sorted(test_body.items()))
            param_str = "&".join([f"{k}={v}" for k, v in sorted_body.items()])
            sign_str = MEXC_API_KEY + ts + param_str
            sig = hmac.new(MEXC_API_SECRET.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256).hexdigest()
            hdrs_g = {
                "ApiKey": MEXC_API_KEY, "Request-Time": ts, "Signature": sig,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Origin": "https://futures.mexc.com",
                "Referer": "https://futures.mexc.com/exchange/BTC_USDT",
            }
            r_get = requests.get(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                                 headers=hdrs_g, params=sorted_body, timeout=8)
            sonuc["get_order_submit"] = {"status": r_get.status_code, "body": r_get.text[:200]}
        except Exception as e:
            sonuc["get_order_submit"] = {"error": str(e)[:100]}

    print(f"[MEXC_TEST] {sonuc}")
    return jsonify(sonuc)


@app.route("/webkey_test")
def webkey_test():
    """MEXC WEB-key ile POST testi — farkli header kombinasyonlari"""
    if not MEXC_WEB_KEY:
        return jsonify({"error": "MEXC_WEB_KEY tanimli degil"})
    sonuc = {"web_key_uzunluk": len(MEXC_WEB_KEY), "web_key_bas": MEXC_WEB_KEY[:6]}

    # Test 1: Tarayici benzeri User-Agent ile POST
    try:
        hdrs1 = {
            "Content-Type": "application/json",
            "x-mxc-nonce": str(int(time.time() * 1000)),
            "Authorization": MEXC_WEB_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://futures.mexc.com",
            "Referer": "https://futures.mexc.com/exchange/BTC_USDT",
        }
        r1 = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                           headers=hdrs1, json={}, timeout=10)
        sonuc["post_browser_headers"] = {"status": r1.status_code, "body": r1.text[:200]}
    except Exception as e:
        sonuc["post_browser_headers"] = {"error": str(e)}

    # Test 2: futures.mexc.com domain + tarayici header
    try:
        hdrs2 = {
            "Content-Type": "application/json",
            "x-mxc-nonce": str(int(time.time() * 1000)),
            "Authorization": MEXC_WEB_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://futures.mexc.com",
            "Referer": "https://futures.mexc.com/exchange/BTC_USDT",
        }
        r2 = requests.post(f"{MEXC_BASE_URL_ALT}/api/v1/private/order/create",
                           headers=hdrs2, json={}, timeout=10)
        sonuc["post_futures_domain"] = {"status": r2.status_code, "body": r2.text[:200]}
    except Exception as e:
        sonuc["post_futures_domain"] = {"error": str(e)}

    # Test 3: Normal API key + tarayici header
    if MEXC_API_KEY and MEXC_API_SECRET:
        try:
            hdrs3, _ = mexc_headers({})
            hdrs3["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            hdrs3["Origin"] = "https://futures.mexc.com"
            hdrs3["Referer"] = "https://futures.mexc.com/exchange/BTC_USDT"
            r3 = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                               headers=hdrs3, json={}, timeout=10)
            sonuc["post_apikey_browser"] = {"status": r3.status_code, "body": r3.text[:200]}
        except Exception as e:
            sonuc["post_apikey_browser"] = {"error": str(e)}

    # Test 4: Minimum body ile imza denemeleri
    if MEXC_API_KEY and MEXC_API_SECRET:
        ts = str(int(time.time() * 1000))

        def make_hdrs(sig):
            return {
                "ApiKey": MEXC_API_KEY,
                "Request-Time": ts,
                "Signature": sig,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Origin": "https://futures.mexc.com",
                "Referer": "https://futures.mexc.com/exchange/BTC_USDT",
            }

        # Minimum parametreler — sadece zorunlu alanlar
        min_body = {"symbol": "BTC_USDT", "vol": 1, "side": 1, "type": 5, "openType": 2, "leverage": 20}

        # Format A: sorted query string imzasi
        sorted_params = dict(sorted(min_body.items()))
        param_str = "&".join([f"{k}={v}" for k, v in sorted_params.items()])
        sig_a = hmac.new(MEXC_API_SECRET.encode(), (MEXC_API_KEY + ts + param_str).encode(), hashlib.sha256).hexdigest()
        try:
            r = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                              headers=make_hdrs(sig_a), json={}, params=sorted_params, timeout=8)
            sonuc["min_sorted_qs"] = {"status": r.status_code, "body": r.text[:200]}
        except Exception as e:
            sonuc["min_sorted_qs"] = {"error": str(e)[:50]}

        # Format B: JSON imzasi + query string gonder
        body_json = json.dumps(min_body, separators=(",",":"), ensure_ascii=False)
        sig_b = hmac.new(MEXC_API_SECRET.encode(), (MEXC_API_KEY + ts + body_json).encode(), hashlib.sha256).hexdigest()
        try:
            r = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                              headers=make_hdrs(sig_b), json={}, params=min_body, timeout=8)
            sonuc["min_json_sign_qs_body"] = {"status": r.status_code, "body": r.text[:200]}
        except Exception as e:
            sonuc["min_json_sign_qs_body"] = {"error": str(e)[:50]}

        # Format C: JSON imzasi + JSON body (normal yol ama browser headers ile)
        sig_c = hmac.new(MEXC_API_SECRET.encode(), (MEXC_API_KEY + ts + body_json).encode(), hashlib.sha256).hexdigest()
        try:
            r = requests.post(f"{MEXC_BASE_URL}/api/v1/private/order/create",
                              headers=make_hdrs(sig_c), json=min_body, timeout=8)
            sonuc["min_json_sign_json_body"] = {"status": r.status_code, "body": r.text[:200]}
        except Exception as e:
            sonuc["min_json_sign_json_body"] = {"error": str(e)[:50]}

    print(f"[WEBKEY_TEST] {sonuc}")
    return jsonify(sonuc)


@app.route("/exchange_test")
def exchange_test():
    """Binance ve Bybit POST erisim testi — WAF kontrolu"""
    sonuc = {}
    testler = [
        ("binance_futures_post", "POST", "https://fapi.binance.com/fapi/v1/order"),
        ("binance_futures_get",  "GET",  "https://fapi.binance.com/fapi/v1/ping"),
        ("bybit_post",           "POST", "https://api.bybit.com/v5/order/create"),
        ("bybit_get",            "GET",  "https://api.bybit.com/v5/market/time"),
    ]
    for isim, metod, url in testler:
        try:
            if metod == "POST":
                r = requests.post(url, json={}, timeout=8,
                                  headers={"Content-Type": "application/json"})
            else:
                r = requests.get(url, timeout=8)
            sonuc[isim] = {"status": r.status_code, "body": r.text[:120]}
        except Exception as e:
            sonuc[isim] = {"error": str(e)}
    print(f"[EXCHANGE_TEST] {sonuc}")
    return jsonify(sonuc)
    """Railway sunucusunun dis IP adresini dondur"""
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=8)
        ip = r.json().get("ip", r.text.strip())
    except Exception as e:
        ip = f"Alinamadi: {e}"
    print(f"[MYIP] Railway IP: {ip}")
    return jsonify({"railway_ip": ip})



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
        + zaman_satir + "\n\n"
        + "🚀 <b>En Çok Yükselenler</b>\n"
        + "<pre>" + "\n".join(yuksel_satirlar) + "</pre>\n\n"
        + "📉 <b>En Çok Düşenler</b>\n"
        + "<pre>" + "\n".join(dusen_satirlar) + "</pre>\n\n"
        + "Siz de kulübe katılıp, alarmları kaçırmamak için lütfen iletişime geçin.\n"
        + "İletişim: " + KANAL_TAG + "\n"
        + ayrac + "\n"
        + "<code>/tarayici</code>"
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
    _telegram_topic_mesaj_gonder(TOPIC_YUKSELENLER, mesaj)
    print(f"[TARAYICI] Gonderildi. Top {TARAYICI_TOP_N} yukselenler/dusenler.")

    if TELEGRAM_LOG_ID and TELEGRAM_LOG_ID != TELEGRAM_CHAT_ID:
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, mesaj)


# ==========================================
# KÜLYUTMAZ V.4.3 SİNYAL TARAMA SİSTEMİ (TOPIC_YUKSELENLER)
# ==========================================
# Pine Script parametreleri (koddan birebir alındı):
#   beyaz_h=10, beyaz_m=3.0, sari_p=7
#   vwaplength=1, ema200_length=200, slPercent=2.0
#   tpLookback=21, tpCount=5
# ==========================================

_kulyutmaz_kilit = threading.Lock()

def _fiyat_formatla(f):
    """Fiyatı uygun formatta string'e çevirir."""
    if f >= 1000:   return f"{f:,.1f}"
    elif f >= 1:    return f"{f:.4f}"
    elif f >= 0.01: return f"{f:.6f}"
    else:           return f"{f:.8f}"

def _kulyutmaz_ema(dizi, periyot):
    """Basit EMA hesabı — liste döner. None değerler atlanır, prev=None ise SMA ile yeniden başlar."""
    k = 2.0 / (periyot + 1)
    result = [None] * len(dizi)
    for i, v in enumerate(dizi):
        if v is None:
            result[i] = None
            continue
        if i < periyot - 1:
            result[i] = None
        elif i == periyot - 1:
            dilim = [x for x in dizi[i - periyot + 1: i + 1] if x is not None]
            result[i] = sum(dilim) / len(dilim) if dilim else None
        else:
            prev = result[i - 1]
            if prev is None:
                dilim = [x for x in dizi[max(0, i - periyot + 1): i + 1] if x is not None]
                result[i] = sum(dilim) / len(dilim) if dilim else None
            else:
                result[i] = v * k + prev * (1 - k)
    return result

def _kulyutmaz_atr(highs, lows, closes, periyot):
    """ATR hesabı — liste döner (True Range = max(H-L, |H-Cprev|, |L-Cprev|))."""
    n = len(closes)
    tr_list = []
    for i in range(n):
        if i == 0:
            tr_list.append(highs[i] - lows[i])
        else:
            tr_list.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i]  - closes[i - 1])
            ))
    # ATR = EMA(TR, periyot)
    return _kulyutmaz_ema(tr_list, periyot)

def _kulyutmaz_cci(highs, lows, closes, periyot=21):
    """CCI hesabı — liste döner."""
    n = len(closes)
    result = [None] * n
    for i in range(periyot - 1, n):
        tp_slice = [(highs[j] + lows[j] + closes[j]) / 3 for j in range(i - periyot + 1, i + 1)]
        mean = sum(tp_slice) / periyot
        md   = sum(abs(x - mean) for x in tp_slice) / periyot
        result[i] = (tp_slice[-1] - mean) / (0.015 * md) if md != 0 else 0
    return result

def _kulyutmaz_sinyal_hesapla(closes, highs, lows, volumes):
    """
    KÜLYUTMAZ V.4.3 sinyal mantığını Python'da hesaplar.
    Parametreler Pine Script kodundan birebir alındı.

    Döndürür: (sinyal_tipi, tp_listesi, sl) veya (None, None, None)
    sinyal_tipi: 'STRONG BUY' | 'LONG' | 'STRONG SELL' | 'SHORT'
    """
    # Parametreler (Pine Script varsayılanları)
    BEYAZ_H    = 10     # beyaz_h
    BEYAZ_M    = 3.0    # beyaz_m
    SARI_P     = 7      # sari_p
    VWAP_LEN   = 1      # vwaplength (EMA of VWAP)
    EMA200_LEN = 200    # ema200_length
    SL_PCT     = 2.0    # slPercent
    TP_LOOKBACK = 21    # tpLookback
    TP_COUNT    = 5     # tpCount

    n = len(closes)
    if n < EMA200_LEN + 5:
        return None, None, None

    # --- EMA 200 ---
    ema200_list = _kulyutmaz_ema(closes, EMA200_LEN)

    # --- ATR hesapları ---
    atr_beyaz = _kulyutmaz_atr(highs, lows, closes, BEYAZ_H)
    atr_sari  = _kulyutmaz_atr(highs, lows, closes, SARI_P)
    atr14     = _kulyutmaz_atr(highs, lows, closes, 14)

    # --- CCI ---
    cci_list = _kulyutmaz_cci(highs, lows, closes, 21)

    # --- CVWAP: Gerçek VWAP (kümülatif tipik fiyat * hacim / kümülatif hacim) ---
    # Pine'da ta.vwap gün başından itibaren sıfırlanır
    # Biz 250 mum üzerinden kümülatif hesaplıyoruz
    cvwap_list = [None] * n
    cum_tv = 0.0  # kümülatif tipik_fiyat * hacim
    cum_v  = 0.0  # kümülatif hacim
    for i in range(n):
        tp = (highs[i] + lows[i] + closes[i]) / 3.0
        v  = volumes[i] if volumes[i] else 0.0
        cum_tv += tp * v
        cum_v  += v
        cvwap_list[i] = cum_tv / cum_v if cum_v > 0 else closes[i]

    # --- Beyaz hat (ATR+CCI trailing) ---
    beyaz_hat = [None] * n
    for i in range(n):
        if atr_beyaz[i] is None or cci_list[i] is None:
            beyaz_hat[i] = None
            continue
        up_b = (highs[i] + lows[i]) / 2 - atr_beyaz[i] * BEYAZ_M
        dn_b = (highs[i] + lows[i]) / 2 + atr_beyaz[i] * BEYAZ_M
        if i == 0 or beyaz_hat[i - 1] is None:
            beyaz_hat[i] = up_b if cci_list[i] >= 0 else dn_b
        else:
            if cci_list[i] >= 0:
                beyaz_hat[i] = max(up_b, beyaz_hat[i - 1])
            else:
                beyaz_hat[i] = min(dn_b, beyaz_hat[i - 1])

    # --- Sarı hat (ATR trailing, sari_p=7) ---
    sari_hat = [None] * n
    for i in range(n):
        if atr_sari[i] is None:
            sari_hat[i] = None
            continue
        if i == 0 or sari_hat[i - 1] is None:
            sari_hat[i] = closes[i]
            continue
        prev = sari_hat[i - 1]
        if closes[i] > prev + atr_sari[i] * 1:
            sari_hat[i] = closes[i] - atr_sari[i] * 1
        elif closes[i] < prev - atr_sari[i] * 1:
            sari_hat[i] = closes[i] + atr_sari[i] * 1
        else:
            sari_hat[i] = prev

    # --- Mor hat (ATR 14, thr=ATR*2.0) ---
    mor_hat = [None] * n
    for i in range(n):
        if atr14[i] is None:
            mor_hat[i] = None
            continue
        thr = atr14[i] * 2.0
        if i == 0 or mor_hat[i - 1] is None:
            mor_hat[i] = closes[i]
            continue
        prev = mor_hat[i - 1]
        if closes[i] > prev + thr:
            mor_hat[i] = closes[i] - thr
        elif closes[i] < prev - thr:
            mor_hat[i] = closes[i] + thr
        else:
            mor_hat[i] = prev

    # --- Sinyal tespiti (son bar) ---
    # Pine'da: ikisi_ustte = sari > beyaz AND mor > beyaz
    # Sinyal sadece ilk kez geçişte tetiklenir (long_bolgesinde / short_bolgesinde)
    long_bolgesinde  = False
    short_bolgesinde = False
    long_sinyal_i    = -1
    short_sinyal_i   = -1

    for i in range(n):
        if beyaz_hat[i] is None or sari_hat[i] is None or mor_hat[i] is None:
            continue
        ikisi_ustte = sari_hat[i] > beyaz_hat[i] and mor_hat[i] > beyaz_hat[i]
        ikisi_altta = sari_hat[i] < beyaz_hat[i] and mor_hat[i] < beyaz_hat[i]

        if ikisi_ustte and not long_bolgesinde:
            long_sinyal_i    = i
            long_bolgesinde  = True
            short_bolgesinde = False
        elif ikisi_altta and not short_bolgesinde:
            short_sinyal_i   = i
            short_bolgesinde = True
            long_bolgesinde  = False
        elif not ikisi_ustte and not ikisi_altta:
            pass  # geçiş bölgesi, durum korunur

    # Son bar sinyal üretiyor mu? Sadece son 1 mumda oluşmuş sinyaller geçerli
    son_i = n - 1
    long_taze  = (long_sinyal_i  >= son_i - 1)  # son 1 mumda
    short_taze = (short_sinyal_i >= son_i - 1)  # son 1 mumda

    if not long_taze and not short_taze:
        return None, None, None

    # İkisi de tazeyse daha yenisini al
    if long_taze and short_taze:
        is_long = (long_sinyal_i >= short_sinyal_i)
    elif long_taze:
        is_long = True
    else:
        is_long = False

    # DEBUG: sinyal detay logu
    _s = lambda v: f"{v:.6f}" if v is not None else "None"
    print(f"[KY_DEBUG] is_long={is_long} close={_s(closes[son_i])} "
          f"beyaz={_s(beyaz_hat[son_i])} sari={_s(sari_hat[son_i])} "
          f"mor={_s(mor_hat[son_i])} ema200={_s(ema200_list[son_i])}")

    # --- EMA200 filtresi ---
    ema200_son = ema200_list[son_i]
    if ema200_son is None:
        return None, None, None
    if is_long  and closes[son_i] <= ema200_son:
        return None, None, None
    if not is_long and closes[son_i] >= ema200_son:
        return None, None, None

    # --- Sinyal tipi: STRONG BUY / LONG / STRONG SELL / SHORT ---
    cvwap_son = cvwap_list[son_i]
    if is_long:
        sinyal_tipi = "STRONG BUY"  if closes[son_i] > cvwap_son else "LONG"
    else:
        sinyal_tipi = "STRONG SELL" if closes[son_i] < cvwap_son else "SHORT"

    entry = closes[son_i]

    # --- SL: %2 sabit ---
    sl = entry * (1 - SL_PCT / 100) if is_long else entry * (1 + SL_PCT / 100)

    # --- TP: Hacim bazlı (f_collectTPs — Pine Script birebir) ---
    # Pine: for i = 1 to tpLookback → i=1 son bardan bir öncesi, i=21 en eski
    # Python eşdeğeri: son_i-1 den son_i-TP_LOOKBACK'e kadar geriye
    atr14_son = atr14[son_i] if atr14[son_i] else entry * 0.005

    c_prices = []
    c_vols   = []
    for offset_i in range(1, TP_LOOKBACK + 1):
        idx = son_i - offset_i
        if idx < 0:
            break
        if is_long:
            p_lvl = highs[idx]
            if p_lvl > entry:
                c_prices.append(p_lvl)
                c_vols.append(volumes[idx])
        else:
            p_lvl = lows[idx]
            if p_lvl < entry:
                c_prices.append(p_lvl)
                c_vols.append(volumes[idx])

    # Hacme göre büyükten küçüğe sırala, TP_COUNT kadar al
    tp_listesi = []
    if c_prices:
        siralı = sorted(zip(c_vols, c_prices), reverse=True)
        for v, p in siralı:
            if len(tp_listesi) >= TP_COUNT:
                break
            tp_listesi.append(p)

    # Yeterli seviye yoksa ATR ile tamamla (Pine birebir)
    needed = TP_COUNT - len(tp_listesi)
    if needed > 0 and atr14_son > 0:
        if tp_listesi:
            farthest = max(tp_listesi) if is_long else min(tp_listesi)
            dist_far = abs(farthest - entry)
            start_k  = int(dist_far / (atr14_son * 1.5)) + 1
        else:
            start_k = 1
        for k in range(start_k, start_k + needed):
            atr_offset = atr14_son * k * 1.5
            extra_tp   = entry + atr_offset if is_long else entry - atr_offset
            tp_listesi.append(extra_tp)

    # Sırala (LONG: artan, SHORT: azalan) — Pine: array.sort ascending/descending
    tp_listesi = sorted(tp_listesi, reverse=not is_long)[:TP_COUNT]

    return sinyal_tipi, tp_listesi, sl


def _kulyutmaz_alarm_kontrol():
    """v463: DEVRE DISI — proxy tasarrufu icin kaldirıldı."""
    return  # noqa
    try:
        tickers = _tarayici_veri_cek()
        if not tickers:
            print("[KULYUTMAZ] Ticker verisi alinamadi.")
            return

        semboller = []
        for t in tickers:
            sym = t.get("symbol", "")
            if sym.endswith("_USDT"):
                semboller.append(sym)

        print(f"[KULYUTMAZ] {len(semboller)} sembol taranacak.")
        _tarama_sinyal_sayac = {"STRONG BUY": 0, "LONG": 0, "STRONG SELL": 0, "SHORT": 0}
        _tarama_atlanan = 0

        for sym in semboller:
            try:
                with _kulyutmaz_kilit:
                    pass  # kilit sadece flood önleme için

                # 5dk 250 mum çek (EMA200 için yeterli geçmiş)
                sonuc = _skor_klines_cek(sym.replace("_USDT", "USDT"), "5m", 250)
                if not sonuc or not isinstance(sonuc, tuple) or len(sonuc) != 4:
                    continue
                # _skor_klines_cek döndürme sırası: closes, volumes, highs, lows
                closes, volumes, highs, lows = sonuc
                if not closes or not highs or not lows or not volumes:
                    continue
                if not (0.000001 <= closes[0] <= 10_000_000):
                    continue
                if len(closes) < 210:
                    continue

                sinyal_tipi, tp_listesi, sl = _kulyutmaz_sinyal_hesapla(
                    closes, highs, lows, volumes
                )
                if sinyal_tipi is None:
                    _tarama_atlanan += 1
                    continue

                kisa    = sym.replace("_USDT", "")
                entry   = closes[-1]

                # Sinyal ikonu
                if sinyal_tipi == "STRONG BUY":
                    ikon = "🚀"
                elif sinyal_tipi == "LONG":
                    ikon = "📈"
                elif sinyal_tipi == "STRONG SELL":
                    ikon = "💀"
                else:
                    ikon = "📉"

                # Mesaj formatı (TOPIC_ALARM formatıyla aynı)
                cizgi = "―" * 22
                mesaj_satirlar = [
                    f"⚡ <b>{kisa}/USDT</b>",
                    f"{ikon} <b>{sinyal_tipi}</b>",
                    f"🕐 5 DK",
                    f"",
                    f"💰 Giriş (Entry): <code>{_fiyat_formatla(entry)}</code>",
                    f"🪤 Çıkış (SL): <code>{_fiyat_formatla(sl)}</code>",
                ]
                if tp_listesi:
                    mesaj_satirlar.append("")
                    for idx, tp in enumerate(tp_listesi, 1):
                        mesaj_satirlar.append(f"🎯 TP{idx}: <code>{_fiyat_formatla(tp)}</code>")
                mesaj_satirlar.append(cizgi)

                mesaj = "\n".join(mesaj_satirlar)
                _telegram_topic_mesaj_gonder(TOPIC_YUKSELENLER, mesaj)
                _tarama_sinyal_sayac[sinyal_tipi] = _tarama_sinyal_sayac.get(sinyal_tipi, 0) + 1
                print(f"[KULYUTMAZ] {kisa} → {sinyal_tipi} gonderildi.")
                time.sleep(2)  # flood önleme

            except Exception as e:
                print(f"[KULYUTMAZ] {sym} hata: {e}\n{traceback.format_exc()}")

        toplam_sinyal = sum(_tarama_sinyal_sayac.values())
        print(f"[KULYUTMAZ] Tarama tamamlandi. {len(semboller)} tarandı | {toplam_sinyal} sinyal | Atlaanan: {_tarama_atlanan} | {_tarama_sinyal_sayac}")

    except Exception as e:
        print(f"[KULYUTMAZ] Genel hata: {e}")


def _kulyutmaz_alarm_zamanlayici():
    """Her 5 dakikada bir mum kapanışında KÜLYUTMAZ taraması yapar."""
    print("[KULYUTMAZ] Zamanlayici basladi. Her 5 dakikada bir tarama yapilacak.")
    # Bir sonraki 5dk kapanışını bekle
    import datetime as dt_mod
    while True:
        try:
            simdi    = datetime.now(tz=TR_TZ) if TR_TZ else datetime.utcnow()
            gecen_dk = simdi.minute % 5
            bekle_sn = (5 - gecen_dk) * 60 - simdi.second + 3  # +3sn mum kapanış toleransı
            if bekle_sn <= 3:
                bekle_sn += 300
            print(f"[KULYUTMAZ] Sonraki tarama {int(bekle_sn//60)}dk {int(bekle_sn%60)}sn sonra.")
            time.sleep(bekle_sn)
            _kulyutmaz_alarm_kontrol()
        except Exception as e:
            print(f"[KULYUTMAZ] Zamanlayici hata: {e}")
            time.sleep(60)

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
# TREND ANALİZİ MODÜLİ
# ==========================================

TREND_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"
]
TREND_INTERVAL   = "15m"   # mum aralığı
TREND_EMA_FAST   = 20
TREND_EMA_SLOW   = 50
TREND_EMA_MAJOR  = 200
TREND_RSI_PERIOD = 14


def _ema(values, period):
    """Basit EMA hesaplama."""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def _rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _trend_fetch_klines(symbol, interval="15m", limit=220):
    """
    Kline verisi çek.
    Öncelik: MEXC Futures → MEXC Spot → Binance Futures → Binance Spot
    MEXC sembol formatı: BTCUSDT → BTC_USDT (futures), BTCUSDT (spot)
    """
    # MEXC interval map
    mexc_interval_map = {
        "1m":"Min1","3m":"Min3","5m":"Min5","15m":"Min15","30m":"Min30",
        "1h":"Min60","4h":"Hour4","1d":"Day1"
    }
    mexc_iv = mexc_interval_map.get(interval, "Min15")

    # 1. MEXC Futures  (BTC_USDT formatı)
    mexc_sym = symbol.replace("USDT", "_USDT") if not "_" in symbol else symbol
    try:
        r = requests.get(
            f"https://contract.mexc.com/api/v1/contract/kline/{mexc_sym}",
            params={"interval": mexc_iv, "limit": limit},
            timeout=6,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and data.get("data"):
                d = data["data"]
                # MEXC futures kline format: time,open,close,high,low,vol,...
                closes  = [float(x) for x in d.get("close",  [])]
                volumes = [float(x) for x in d.get("vol",    [])]
                highs   = [float(x) for x in d.get("high",   [])]
                lows    = [float(x) for x in d.get("low",    [])]
                if len(closes) >= 50:
                    return closes, volumes, highs, lows
    except Exception as e:
        print(f"[TREND] MEXC futures kline hata ({symbol}): {e}")

    # 2. MEXC Spot
    try:
        r = requests.get(
            "https://api.mexc.com/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=6,
            
        )
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                closes  = [float(k[4]) for k in data]
                volumes = [float(k[5]) for k in data]
                highs   = [float(k[2]) for k in data]
                lows    = [float(k[3]) for k in data]
                if len(closes) >= 50:
                    return closes, volumes, highs, lows
    except Exception as e:
        print(f"[TREND] MEXC spot kline hata ({symbol}): {e}")

    # 3. Binance Futures (Railway'de bloklu olabilir, kısa timeout)
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            closes  = [float(k[4]) for k in data]
            volumes = [float(k[5]) for k in data]
            highs   = [float(k[2]) for k in data]
            lows    = [float(k[3]) for k in data]
            return closes, volumes, highs, lows
    except Exception as e:
        print(f"[TREND] Binance futures kline hata ({symbol}): {e}")

    # 4. Binance Spot
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            closes  = [float(k[4]) for k in data]
            volumes = [float(k[5]) for k in data]
            highs   = [float(k[2]) for k in data]
            lows    = [float(k[3]) for k in data]
            return closes, volumes, highs, lows
    except Exception as e:
        print(f"[TREND] Binance spot kline hata ({symbol}): {e}")

    print(f"[TREND] Tum kaynaklar basarisiz: {symbol}")
    return None, None, None, None


def _trend_fear_greed():
    """Alternative.me'den Fear & Greed Index çek."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        if r.status_code == 200:
            d = r.json().get("data", [{}])[0]
            deger      = int(d.get("value", 0))
            sinifland  = d.get("value_classification", "")
            return deger, sinifland
    except Exception as e:
        print(f"[TREND] fear&greed hata: {e}")
    return None, None


def _trend_fg_emoji(deger):
    """Fear & Greed değerine göre emoji ve Türkçe etiket döndür."""
    if deger is None:    return "❓", "Bilinmiyor"
    if deger <= 24:      return "😱", "Aşırı Korku"
    if deger <= 44:      return "😨", "Korku"
    if deger <= 54:      return "😐", "Nötr"
    if deger <= 74:      return "😏", "Açgözlülük"
    return "🤑", "Aşırı Açgözlülük"


def _trend_fg_renk(deger):
    if deger is None: return "#9E9E9E"
    if deger <= 24:   return "#F44336"
    if deger <= 44:   return "#FF9800"
    if deger <= 54:   return "#9E9E9E"
    if deger <= 74:   return "#8BC34A"
    return "#4CAF50"


# ==========================================
# ==========================================
# BALİNA POZİSYON TAKİBİ (OI BAZLI)
# ==========================================

WHALE_OI_DEGISIM_PCT = float(os.getenv("WHALE_OI_DEGISIM_PCT", "0.5"))  # Min %0.5 OI değişimi (hassasiyet artırıldı)
WHALE_OI_MIN_USD     = float(os.getenv("WHALE_OI_MIN_USD", "500000"))   # Min $500K (hassasiyet artırıldı)
WHALE_OI_INTERVAL    = int(os.getenv("WHALE_OI_INTERVAL", "5"))         # Dakika

OI_SEMBOLLER = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"
]

_oi_onceki = {}


def _oi_cek(symbol):
    try:
        r1 = requests.get("https://fapi.binance.com/fapi/v1/openInterest",
                          params={"symbol": symbol}, timeout=6, proxies=BINANCE_PROXY)
        r2 = requests.get("https://fapi.binance.com/fapi/v1/ticker/price",
                          params={"symbol": symbol}, timeout=6, proxies=BINANCE_PROXY)
        if r1.status_code == 200 and r2.status_code == 200:
            return float(r1.json()["openInterest"]), float(r2.json()["price"])
    except Exception as e:
        print(f"[OI] {symbol} cekme hatasi: {e}")
    return None, None


def _oi_yon_yorum(oi_pct, fiyat_pct):
    if oi_pct > 0 and fiyat_pct > 0:
        return "🟢 LONG AÇILDI", "OI arttı + Fiyat yükseldi"
    elif oi_pct > 0 and fiyat_pct < 0:
        return "🔴 SHORT AÇILDI", "OI arttı + Fiyat düştü"
    elif oi_pct < 0 and fiyat_pct > 0:
        return "⚠️ SHORT KAPATILDI", "OI azaldı + Fiyat yükseldi"
    else:
        return "⚠️ LONG KAPATILDI", "OI azaldı + Fiyat düştü"


def _oi_kontrol():
    global _oi_onceki
    for symbol in OI_SEMBOLLER:
        try:
            oi, fiyat = _oi_cek(symbol)
            if oi is None:
                continue
            simdi = time.time()
            if symbol not in _oi_onceki:
                _oi_onceki[symbol] = {"oi": oi, "fiyat": fiyat, "zaman": simdi}
                continue
            onceki         = _oi_onceki[symbol]
            oi_fark_pct    = (oi - onceki["oi"]) / onceki["oi"] * 100 if onceki["oi"] > 0 else 0
            fiyat_fark_pct = (fiyat - onceki["fiyat"]) / onceki["fiyat"] * 100 if onceki["fiyat"] > 0 else 0
            oi_fark_usd    = abs(oi - onceki["oi"]) * fiyat

            if abs(oi_fark_pct) >= WHALE_OI_DEGISIM_PCT and oi_fark_usd >= WHALE_OI_MIN_USD:
                yon, aciklama = _oi_yon_yorum(oi_fark_pct, fiyat_fark_pct)
                if TR_TZ:
                    zaman_str = datetime.now(tz=TR_TZ).strftime("%H:%M")
                else:
                    zaman_str = datetime.utcnow().strftime("%H:%M UTC")
                if oi_fark_usd >= 1e9:
                    usd_str = f"${oi_fark_usd/1e9:.2f}B"
                elif oi_fark_usd >= 1e6:
                    usd_str = f"${oi_fark_usd/1e6:.1f}M"
                else:
                    usd_str = f"${oi_fark_usd:,.0f}"
                sym_kisa = symbol.replace("USDT", "")
                mesaj = (
                    f"🐋 <b>BÜYÜK POZİSYON HAREKETİ</b>\n\n"
                    f"📊 <b>{sym_kisa}/USDT</b> — Binance Futures\n"
                    f"💰 Fiyat: ${fiyat:,.2f}\n"
                    f"📈 OI Değişimi: {oi_fark_pct:+.2f}% ({usd_str})\n"
                    f"{yon}\n"
                    f"   └ {aciklama}\n\n"
                    f"⏱ {zaman_str}\n"
                    f"{'━' * 16}"
                )
                mesaj += "\n<code>/balina</code>"
                _telegram_topic_mesaj_gonder(TOPIC_BALINA, mesaj)
                print(f"[OI] BİLDİRİM: {symbol} {yon} {oi_fark_pct:+.1f}% {usd_str}")
            _oi_onceki[symbol] = {"oi": oi, "fiyat": fiyat, "zaman": simdi}
        except Exception as e:
            print(f"[OI] {symbol} kontrol hatasi: {e}")


def _oi_zamanlayici():
    """Her WHALE_OI_INTERVAL dakikada bir OI kontrol et."""
    print(f"[OI] Zamanlayici basladi. Interval: {WHALE_OI_INTERVAL} dakika.")
    time.sleep(60)
    oi, fiyat = _oi_cek("BTCUSDT")
    if oi:
        print(f"[OI] Endpoint ACIK. BTC OI={oi:.0f} Fiyat={fiyat:.1f}")
    else:
        print(f"[OI] Endpoint KAPALI veya hata!")
    while True:
        try:
            _oi_kontrol()
            time.sleep(WHALE_OI_INTERVAL * 60)
        except Exception as e:
            print(f"[OI] Zamanlayici hata: {e}")
            time.sleep(60)


def _liq_veri_cek(symbol):
    """BTC/ETH için funding rate, OI geçmişi, kline ve ticker çek."""
    try:
        sym = symbol

        # 1) Funding Rate
        r1 = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                          params={"symbol": sym, "limit": 1}, timeout=6, proxies=BINANCE_PROXY)
        funding = float(r1.json()[0]["fundingRate"]) * 100 if r1.status_code == 200 else 0

        # 2) 24h Ticker
        r2 = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr",
                          params={"symbol": sym}, timeout=6, proxies=BINANCE_PROXY)
        ticker   = r2.json() if r2.status_code == 200 else {}
        fiyat    = float(ticker.get("lastPrice", 0))
        high_24h = float(ticker.get("highPrice", 0))
        low_24h  = float(ticker.get("lowPrice", 0))
        degisim  = float(ticker.get("priceChangePercent", 0))

        # 3) Anlık OI (openInterestHist bölgede bloklu olabileceğinden anlık kullanıyoruz)
        r3 = requests.get("https://fapi.binance.com/fapi/v1/openInterest",
                          params={"symbol": sym}, timeout=6, proxies=BINANCE_PROXY)
        oi_list = []
        if r3.status_code == 200:
            oi_anlik = float(r3.json().get("openInterest", 0))
            oi_fiyat = fiyat if fiyat > 0 else 1
            oi_toplam = oi_anlik * oi_fiyat
        else:
            oi_toplam = 0
        oi_degisim = 0  # history yok, degisim hesaplanamıyor

        # 4) Klines 1h (24 adet) — destek/direnç için
        r4 = requests.get("https://fapi.binance.com/fapi/v1/klines",
                          params={"symbol": sym, "interval": "1h", "limit": 24}, timeout=6, proxies=BINANCE_PROXY)
        klines = r4.json() if r4.status_code == 200 else []

        # 4b) Klines 4h (30 adet) — likidasyon bölgesi için (geniş giriş fiyat aralığı)
        r4b = requests.get("https://fapi.binance.com/fapi/v1/klines",
                           params={"symbol": sym, "interval": "4h", "limit": 30}, timeout=6, proxies=BINANCE_PROXY)
        klines_liq = r4b.json() if r4b.status_code == 200 else klines

        # 5) Klines 4h (24 adet) — momentum için
        r5 = requests.get("https://fapi.binance.com/fapi/v1/klines",
                          params={"symbol": sym, "interval": "4h", "limit": 24}, timeout=6, proxies=BINANCE_PROXY)
        klines_4h = r5.json() if r5.status_code == 200 else []

        # 6) Destek/Direnç — 1h pivot noktaları
        destek    = None
        direnc    = None
        if len(klines) >= 20:
            highs = [float(k[2]) for k in klines[-20:]]
            lows  = [float(k[3]) for k in klines[-20:]]
            fiyat_ref = fiyat if fiyat and fiyat > 0 else float(klines[-1][4])
            # Fiyatin altindaki low'lar = destek (en yakin once — buyukten kucuge)
            # Unique: ayni seviye tekrar edince iki farkli deger gibi gorunmesin
            destek_adaylar = sorted(set(round(l, 2) for l in lows if l < fiyat_ref), reverse=True)
            destek = destek_adaylar[:3] if destek_adaylar else sorted(set(round(l, 2) for l in lows))[:3]
            # Fiyatin ustundeki high'lar = direnc (en yakin once — kucukten buyuge)
            direnc_adaylar = sorted(set(round(h, 2) for h in highs if h > fiyat_ref))
            direnc = direnc_adaylar[:3] if direnc_adaylar else sorted(set(round(h, 2) for h in highs))[-3:]

        # 7) 4H Momentum — son 6 x 4h mumun hacim ve yön analizi
        momentum_4h = None
        if len(klines_4h) >= 6:
            son_6 = klines_4h[-6:]
            alinlar  = sum(float(k[5]) for k in son_6 if float(k[4]) > float(k[1]))  # kapanış > açılış
            satilanlar = sum(float(k[5]) for k in son_6 if float(k[4]) <= float(k[1]))
            toplam_hacim = alinlar + satilanlar
            if toplam_hacim > 0:
                alis_pct = alinlar / toplam_hacim * 100
            else:
                alis_pct = 50
            # Son 4h mum değişimi
            ilk_4h_acilis = float(son_6[0][1])
            son_4h_kapanis = float(son_6[-1][4])
            momentum_pct = (son_4h_kapanis - ilk_4h_acilis) / ilk_4h_acilis * 100 if ilk_4h_acilis > 0 else 0
            momentum_4h = {
                "alis_pct": alis_pct,
                "satis_pct": 100 - alis_pct,
                "momentum_pct": momentum_pct,
                "toplam_hacim": toplam_hacim,
            }

        # Likidasyon bölgeleri: ısı haritası grid'inden okunur (_liq_yorum'da)

        return {
            "symbol": sym,
            "fiyat": fiyat,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "degisim": degisim,
            "funding": funding,
            "oi_toplam": oi_toplam,
            "oi_degisim": oi_degisim,
            "oi_list": [],
            "klines": klines,
            "klines_4h": klines_4h,
            "destek": destek,
            "direnc": direnc,
            "momentum_4h": momentum_4h,
            "liq_long_baskisi": None,
            "liq_short_baskisi": None,
        }
    except Exception as e:
        print(f"[LIQ] {symbol} veri hatasi: {e}")
        return None


def _liq_ws_kaydet():
    """_liq_ws_data'yi diske kaydet — restart sonrasi korunsin."""
    try:
        with _liq_ws_kilit:
            kayit = {sym: list(evler) for sym, evler in _liq_ws_data.items()}
        with open(LIQ_WS_DOSYASI, "w", encoding="utf-8") as f:
            import json as _j
            _j.dump(kayit, f)
        toplam = sum(len(v) for v in kayit.values())
        print(f"[LIQ_WS] Diske kaydedildi: {toplam} event")
    except Exception as e:
        print(f"[LIQ_WS] Kayit hatasi: {e}")


def _liq_ws_yukle():
    """Startup'ta liq_ws_data'yi diskten yukle, 2 gunden eski verileri at."""
    global _liq_ws_data
    try:
        import json as _j, os as _os
        if not _os.path.exists(LIQ_WS_DOSYASI):
            print("[LIQ_WS] Kayitli veri yok — bos baslatildi")
            return
        with open(LIQ_WS_DOSYASI, "r", encoding="utf-8") as f:
            kayit = _j.load(f)
        sinir = (time.time() - LIQ_WS_SAKLA_SURE) * 1000  # 1 gun oncesi
        with _liq_ws_kilit:
            for sym in ["BTCUSDT", "ETHUSDT"]:
                evler = kayit.get(sym, [])
                temiz = [tuple(e) for e in evler if e[0] >= sinir]
                _liq_ws_data[sym] = temiz
                print(f"[LIQ_WS] {sym} yuklendi: {len(temiz)} event")
        print("[LIQ_WS] Disk verisi yuklendi")
    except Exception as e:
        print(f"[LIQ_WS] Yukleme hatasi: {e}")


def _liq_ws_temizle():
    """2 gunden eski eventlari sil — 1 gunluk veri kalsin."""
    try:
        sinir = (time.time() - LIQ_WS_SAKLA_SURE) * 1000
        with _liq_ws_kilit:
            for sym in list(_liq_ws_data.keys()):
                onceki = len(_liq_ws_data[sym])
                _liq_ws_data[sym] = [e for e in _liq_ws_data[sym] if e[0] >= sinir]
                silindi = onceki - len(_liq_ws_data[sym])
                print(f"[LIQ_WS] {sym} temizlendi: {silindi} eski event silindi, {len(_liq_ws_data[sym])} kaldi")
        _liq_ws_kaydet()
    except Exception as e:
        print(f"[LIQ_WS] Temizlik hatasi: {e}")


def _liq_ws_bakim_zamanlayici():
    """Her 5 dakikada diske kaydet, 3 gunde bir 2 gunluk veri sil."""
    son_temizlik = time.time()
    while True:
        try:
            time.sleep(300)  # 5 dakika
            _liq_ws_kaydet()
            # 3 gunde bir temizlik
            if time.time() - son_temizlik >= LIQ_WS_TEMIZLE_SURE:
                print("[LIQ_WS] 3 gunluk temizlik basladi")
                _liq_ws_temizle()
                son_temizlik = time.time()
        except Exception as e:
            print(f"[LIQ_WS] Bakim zamanlayici hata: {e}")
            time.sleep(60)


def _liq_ws_bolge_hesapla(sym, fiyat, n_bin=50):
    """
    _liq_ws_data'dan long/short likidasyon yogun bolgelerini hesapla.
    Fiyat etrafinda +/-8% aralikta en yogun seviyeleri dondurur.
    Donus: (long_alt, long_ust, short_alt, short_ust) veya None
    """
    try:
        with _liq_ws_kilit:
            events = list(_liq_ws_data.get(sym, []))
        if len(events) < 10:
            return None
        price_min = fiyat * 0.92
        price_max = fiyat * 1.08
        long_bins  = [0.0] * n_bin
        short_bins = [0.0] * n_bin
        for ts_ms, price, usd, side in events:
            if not (price_min < price < price_max):
                continue
            idx = int((price - price_min) / (price_max - price_min) * n_bin)
            idx = max(0, min(n_bin - 1, idx))
            if side == "LONG":
                long_bins[idx]  += usd
            else:
                short_bins[idx] += usd
        def en_yogun_bolge(bins, fiyat_alt_mi):
            """En yogun ardisik 3 bin'i bul, alt/ust fiyat dondur."""
            if max(bins) == 0:
                return None, None
            # Kayar pencere ile en yogun 3 bin
            en_iyi_idx = 0
            en_iyi_toplam = 0
            for i in range(len(bins) - 2):
                t = bins[i] + bins[i+1] + bins[i+2]
                if t > en_iyi_toplam:
                    en_iyi_toplam = t
                    en_iyi_idx = i
            alt = price_min + (en_iyi_idx)     / n_bin * (price_max - price_min)
            ust = price_min + (en_iyi_idx + 3) / n_bin * (price_max - price_min)
            return round(alt, 2), round(ust, 2)

        long_alt,  long_ust  = en_yogun_bolge(long_bins,  True)
        short_alt, short_ust = en_yogun_bolge(short_bins, False)
        if long_alt is None or short_alt is None:
            return None
        return (long_alt, long_ust, short_alt, short_ust)
    except Exception as e:
        print(f"[LIQ_WS] Bolge hesaplama hatasi: {e}")
        return None


def _liq_ws_baslat():
    """Binance forceOrder WebSocket'i dinle — BTC ve ETH likidasyonlarını biriktir."""
    if not HAS_WS:
        print("[LIQ_WS] websocket-client kurulu değil, atlanıyor.")
        return

    def on_message(ws, message):
        try:
            data = json.loads(message)
            # Tüm market akışı: {"e":"forceOrder","E":...,"o":{...}}
            o = data.get("o") or data
            sym_raw = o.get("s", "")
            # Sadece BTC ve ETH
            sym = None
            if "BTC" in sym_raw: sym = "BTCUSDT"
            elif "ETH" in sym_raw: sym = "ETHUSDT"
            if not sym:
                return

            price  = float(o.get("ap") or o.get("p") or 0)
            qty    = float(o.get("z") or o.get("q") or 0)
            usd    = price * qty
            side   = "LONG" if o.get("S") == "SELL" else "SHORT"
            ts_ms  = int(o.get("T") or time.time() * 1000)

            if price <= 0 or usd <= 0:
                return

            with _liq_ws_kilit:
                _liq_ws_data[sym].append((ts_ms, price, usd, side))
                # 6 saat ötesini temizle
                sinir = (time.time() - LIQ_WS_SURE) * 1000
                _liq_ws_data[sym] = [e for e in _liq_ws_data[sym] if e[0] >= sinir]

        except Exception as e:
            print(f"[LIQ_WS] Mesaj hatası: {e}")

    def on_error(ws, error):
        print(f"[LIQ_WS] Hata: {error}")

    def on_close(ws, *args):
        print("[LIQ_WS] Bağlantı kapandı, 10sn sonra yeniden bağlanılıyor.")

    def on_open(ws):
        print("[LIQ_WS] Bağlandı — BTC+ETH likidasyon dinleniyor.")

    def _calistir():
        while True:
            try:
                ws = _ws_lib.WebSocketApp(
                    "wss://fstream.binance.com/ws/!forceOrder@arr",
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open,
                )
                ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                print(f"[LIQ_WS] Bağlantı hatası: {e}")
            time.sleep(10)

    t = threading.Thread(target=_calistir, daemon=True, name="liq_ws")
    t.start()
    print("[LIQ_WS] WebSocket thread başlatıldı.")


def _liq_heatmap_gercek(symbol, saat=6):
    """
    Kaldıraç bazlı likidasyon ısı haritası.
    Mantık: Her 5dk mumun giriş fiyatına 10x/25x/50x/100x kaldıraç uygula
    → likidasyon fiyatlarını hesapla → o seviyelerde yoğunluk oluştur.
    X=zaman, Y=fiyat, sarı=yoğun likidasyon bölgesi.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        import numpy as np
        from scipy.ndimage import gaussian_filter
        import io

        sym = symbol

        # 1) OHLCV çek — 15dk mumlar daha temiz seviyeler verir
        r = requests.get("https://fapi.binance.com/fapi/v1/klines",
                         params={"symbol": sym, "interval": "15m",
                                 "limit": int(saat * 4) + 10}, timeout=8,
                         proxies=BINANCE_PROXY)
        klines = r.json() if r.status_code == 200 else []
        if not klines or len(klines) < 5:
            return None

        fiyat      = float(klines[-1][4])
        timestamps = [int(k[0]) for k in klines]
        opens      = [float(k[1]) for k in klines]
        closes     = [float(k[4]) for k in klines]
        highs      = [float(k[2]) for k in klines]
        lows       = [float(k[3]) for k in klines]
        volumes    = [float(k[5]) * float(k[4]) for k in klines]  # USD hacmi

        # 2) Y ekseni — fiyatın ±6% (kaldıraç likidasyon seviyeleri burada)
        price_center = fiyat
        price_range  = fiyat * 0.06
        price_min    = min(min(lows), fiyat - price_range) * 0.999
        price_max    = max(max(highs), fiyat + price_range) * 1.001

        n_tb = len(klines)
        n_pb = 120  # daha ince bant = net seviyeler

        # Long ve Short için ayrı grid
        grid_long  = np.zeros((n_pb, n_tb))
        grid_short = np.zeros((n_pb, n_tb))

        # 3) Her mum için kaldıraç bazlı likidasyon seviyeleri hesapla
        # Long likidasyon  = giriş * (1 - 1/kaldıraç)  → fiyatın ALTINDA  → kırmızı
        # Short likidasyon = giriş * (1 + 1/kaldıraç)  → fiyatın ÜSTÜNDE  → yeşil
        kaldıraçlar = [
            (10,  0.30),
            (25,  0.25),
            (50,  0.20),
            (100, 0.15),
            (5,   0.10),
        ]

        for i, k in enumerate(klines):
            t_bin   = i
            k_open  = float(k[1])
            k_close = float(k[4])
            k_high  = float(k[2])
            k_low   = float(k[3])
            k_usd   = float(k[5]) * k_close
            yukari  = k_close > k_open

            for lev, agirlik in kaldıraçlar:
                long_lik  = k_open * (1 - 1 / lev)
                short_lik = k_open * (1 + 1 / lev)
                long_w    = k_usd * agirlik * (1.3 if not yukari else 0.7)
                short_w   = k_usd * agirlik * (1.3 if yukari else 0.7)

                if price_min < long_lik < price_max:
                    p_bin = int((long_lik - price_min) / (price_max - price_min) * n_pb)
                    p_bin = max(0, min(n_pb - 1, p_bin))
                    grid_long[p_bin, t_bin] += long_w

                if price_min < short_lik < price_max:
                    p_bin = int((short_lik - price_min) / (price_max - price_min) * n_pb)
                    p_bin = max(0, min(n_pb - 1, p_bin))
                    grid_short[p_bin, t_bin] += short_w

            if k_usd > np.mean(volumes) * 1.5:
                for lev, _ in kaldıraçlar:
                    for entry in [k_open, k_close, k_high, k_low]:
                        long_lik2  = entry * (1 - 1/lev)
                        short_lik2 = entry * (1 + 1/lev)
                        if price_min < long_lik2 < price_max:
                            p_bin = int((long_lik2 - price_min) / (price_max - price_min) * n_pb)
                            p_bin = max(0, min(n_pb - 1, p_bin))
                            grid_long[p_bin, t_bin] += k_usd * 0.05
                        if price_min < short_lik2 < price_max:
                            p_bin = int((short_lik2 - price_min) / (price_max - price_min) * n_pb)
                            p_bin = max(0, min(n_pb - 1, p_bin))
                            grid_short[p_bin, t_bin] += k_usd * 0.05

        # 4) Gerçek WebSocket verisi varsa üstüne ekle
        with _liq_ws_kilit:
            events = list(_liq_ws_data.get(sym, []))

        t_start = timestamps[0]
        t_end   = timestamps[-1] + 15 * 60 * 1000
        if len(events) >= 5:
            for ts_ms, price, usd, side in events:
                if not (t_start <= ts_ms <= t_end):
                    continue
                t_bin = int((ts_ms - t_start) / (t_end - t_start) * n_tb)
                t_bin = max(0, min(n_tb - 1, t_bin))
                if price_min < price < price_max:
                    p_bin = int((price - price_min) / (price_max - price_min) * n_pb)
                    p_bin = max(0, min(n_pb - 1, p_bin))
                    if side == "SELL":  # SELL = long likidasyon
                        grid_long[p_bin, t_bin]  += usd * 3
                    else:
                        grid_short[p_bin, t_bin] += usd * 3

        # 5) Yumuşat ve normalize — her grid bağımsız
        # sigma=[fiyat_ekseni, zaman_ekseni]
        # Zaman ekseninde yayılma küçük → sağa kayma önlenir
        # Fiyat ekseninde biraz daha yumuşat → güzel görünüm
        grid_long  = gaussian_filter(grid_long,  sigma=[1.2, 0.3])
        grid_short = gaussian_filter(grid_short, sigma=[1.2, 0.3])

        if grid_long.max()  > 0:
            grid_long  = grid_long  / grid_long.max()
            grid_long  = np.power(grid_long,  0.4)
        if grid_short.max() > 0:
            grid_short = grid_short / grid_short.max()
            grid_short = np.power(grid_short, 0.4)

        # ── Grafik ──
        fig, ax = plt.subplots(figsize=(12, 5.5))
        fig.patch.set_facecolor("#050A14")
        ax.set_facecolor("#050A14")

        # Long likidasyon — kırmızı tonda (Reds_r: yoğun kırmızı)
        cmap_long  = mcolors.LinearSegmentedColormap.from_list(
            "long_lik", ["#050A14", "#7B0000", "#FF1744", "#FF6D00", "#FFD600"], N=256)
        # Short likidasyon — yeşil tonda
        cmap_short = mcolors.LinearSegmentedColormap.from_list(
            "short_lik", ["#050A14", "#003300", "#00C853", "#B2FF59", "#FFFFFF"], N=256)

        # Alpha maskesi: sıfır değerleri transparan
        alpha_long  = np.where(grid_long  > 0.05, grid_long  * 0.90, 0)
        alpha_short = np.where(grid_short > 0.05, grid_short * 0.90, 0)

        rgba_long  = cmap_long(grid_long)
        rgba_short = cmap_short(grid_short)
        rgba_long[...,  3] = alpha_long
        rgba_short[..., 3] = alpha_short

        ax.imshow(rgba_long,  aspect="auto", origin="lower",
                  extent=[0, n_tb, price_min, price_max],
                  interpolation="nearest", zorder=2)
        ax.imshow(rgba_short, aspect="auto", origin="lower",
                  extent=[0, n_tb, price_min, price_max],
                  interpolation="nearest", zorder=3)

        # Fiyat çizgisi
        price_x = np.linspace(0, n_tb, len(closes))
        ax.plot(price_x, closes, color="#FFFFFF", linewidth=1.0, alpha=0.9, zorder=5)

        # Anlık fiyat
        if fiyat >= 1000:
            fiyat_label = f"${fiyat:,.0f}"
        elif fiyat >= 1:
            fiyat_label = f"${fiyat:.2f}"
        else:
            fiyat_label = f"${fiyat:.5f}"

        ax.axhline(y=fiyat, color="#5B9CF6", linewidth=0.6,
                   linestyle="--", alpha=0.5, zorder=4)
        ax.annotate(fiyat_label, xy=(n_tb * 0.98, fiyat),
                    color="#5B9CF6", fontsize=8, fontweight="bold",
                    ha="right", va="bottom")

        # Kaldıraç seviye etiketleri (sağ tarafta)
        for lev, _ in [(10, ""), (25, ""), (50, ""), (100, "")]:
            long_lik  = fiyat * (1 - 1/lev)
            short_lik = fiyat * (1 + 1/lev)
            if price_min < long_lik < price_max:
                ax.axhline(y=long_lik, color="#F44336", linewidth=0.4,
                           linestyle=":", alpha=0.4, zorder=3)
                ax.annotate(f"{lev}x LONG", xy=(n_tb, long_lik),
                            xytext=(3, 0), textcoords="offset points",
                            color="#F44336", fontsize=5.5, va="center")
            if price_min < short_lik < price_max:
                ax.axhline(y=short_lik, color="#4CAF50", linewidth=0.4,
                           linestyle=":", alpha=0.4, zorder=3)
                ax.annotate(f"{lev}x SHORT", xy=(n_tb, short_lik),
                            xytext=(3, 0), textcoords="offset points",
                            color="#4CAF50", fontsize=5.5, va="center")

        # Y ekseni
        y_ticks = np.linspace(price_min * 1.002, price_max * 0.998, 10)
        ax.set_yticks(y_ticks)
        if fiyat >= 1000:
            ax.set_yticklabels([f"${t:,.0f}" for t in y_ticks], fontsize=6.5, color="#9CA3AF")
        elif fiyat >= 1:
            ax.set_yticklabels([f"${t:.2f}" for t in y_ticks], fontsize=6.5, color="#9CA3AF")
        else:
            ax.set_yticklabels([f"${t:.5f}" for t in y_ticks], fontsize=6.5, color="#9CA3AF")

        # X ekseni
        n_tick = min(7, n_tb)
        x_pos  = np.linspace(0, n_tb, n_tick)
        x_lbl  = []
        for i in range(n_tick):
            idx = int(i * (len(klines) - 1) / (n_tick - 1))
            ts  = timestamps[idx]
            if TR_TZ:
                dt = datetime.fromtimestamp(ts / 1000, tz=TR_TZ)
            else:
                dt = datetime.utcfromtimestamp(ts / 1000)
            x_lbl.append(dt.strftime("%H:%M"))
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_lbl, fontsize=7, color="#9CA3AF")

        ax.yaxis.grid(True, color="#1F2937", linewidth=0.3, alpha=0.4)
        ax.xaxis.grid(True, color="#1F2937", linewidth=0.3, alpha=0.4)
        for spine in ax.spines.values():
            spine.set_edgecolor("#1F2937")

        # ── Dolar birikim etiketleri — her yoğun bandın ortasında fiyat + tutar ──
        band_long_usd  = None
        band_short_usd = None
        liq_long_zone  = None
        liq_short_zone = None
        try:
            # Long ve Short için ayrı birikim hesapla
            band_long_usd  = np.zeros(n_pb)
            band_short_usd = np.zeros(n_pb)
            for i_k, k in enumerate(klines):
                k_usd = float(k[5]) * float(k[4])
                for lev, agirlik in kaldıraçlar:
                    for entry in [float(k[1]), float(k[4])]:
                        long_lik3  = entry * (1 - 1/lev)
                        short_lik3 = entry * (1 + 1/lev)
                        if price_min < long_lik3 < price_max:
                            p_bin = int((long_lik3 - price_min) / (price_max - price_min) * n_pb)
                            p_bin = max(0, min(n_pb - 1, p_bin))
                            band_long_usd[p_bin] += k_usd * agirlik
                        if price_min < short_lik3 < price_max:
                            p_bin = int((short_lik3 - price_min) / (price_max - price_min) * n_pb)
                            p_bin = max(0, min(n_pb - 1, p_bin))
                            band_short_usd[p_bin] += k_usd * agirlik
            for ts_ms, ev_price, ev_usd, ev_side in events:
                if price_min < ev_price < price_max:
                    p_bin = int((ev_price - price_min) / (price_max - price_min) * n_pb)
                    p_bin = max(0, min(n_pb - 1, p_bin))
                    if ev_side == "SELL":
                        band_long_usd[p_bin]  += ev_usd
                    else:
                        band_short_usd[p_bin] += ev_usd

            # Grid'den her fiyat bandının en yoğun zaman noktasını bul
            # long/short grid'leri daha önce hesaplandı — normalize öncesi değerleri kullan
            def _bant_etiketleri(band_arr, grid_2d, renk_baz, yon_str):
                """
                Yoğun bantları grupla.
                Etiket pozisyonu: bandın grafik üzerindeki en parlak (yoğun) t noktası.
                Üst üste binmeyi önlemek için y ekseninde min mesafe kontrolü.
                """
                esik = band_arr.max() * 0.30
                if esik <= 0:
                    return
                i_e = 0
                etiketler = []
                while i_e < n_pb:
                    if band_arr[i_e] >= esik:
                        j_e = i_e
                        while j_e < n_pb and band_arr[j_e] >= esik:
                            j_e += 1
                        merkez_bin   = (i_e + j_e) // 2
                        toplam_usd   = band_arr[i_e:j_e].sum()
                        merkez_fiyat = price_min + (merkez_bin / n_pb) * (price_max - price_min)

                        # Bu fiyat bandının en yoğun zaman noktasını bul
                        band_slice = grid_2d[i_e:j_e, :]  # (p_bins, t_bins)
                        if band_slice.size > 0:
                            t_toplam = band_slice.sum(axis=0)  # her t için toplam yoğunluk
                            # En yoğun %30'luk zaman diliminin ortasını al
                            t_esik = t_toplam.max() * 0.5
                            yogun_t = np.where(t_toplam >= t_esik)[0]
                            if len(yogun_t) > 0:
                                # Ortadaki noktayı al, kenarlara yapışmasın
                                t_merkez = int(np.median(yogun_t))
                                t_merkez = max(int(n_tb * 0.05), min(int(n_tb * 0.75), t_merkez))
                            else:
                                t_merkez = int(n_tb * 0.15)
                        else:
                            t_merkez = int(n_tb * 0.15)

                        etiketler.append((merkez_fiyat, toplam_usd, t_merkez))
                        i_e = j_e
                    else:
                        i_e += 1

                # En yoğun 6 etiketi al, USD'ye göre sırala
                etiketler = sorted(etiketler, key=lambda x: -x[1])[:6]

                # Üst üste binme önleme — y ekseninde min_gap kadar mesafe zorla
                min_gap = (price_max - price_min) * 0.04  # fiyat aralığının %4'ü
                etiketler = sorted(etiketler, key=lambda x: x[0])  # fiyata göre sırala
                temizlendi = []
                for ep_fiyat, ep_usd, ep_t in etiketler:
                    # Önceki etiketle çakışıyor mu?
                    cakisiyor = any(abs(ep_fiyat - y) < min_gap for y, _, _ in temizlendi)
                    if not cakisiyor:
                        temizlendi.append((ep_fiyat, ep_usd, ep_t))

                for ep_fiyat, ep_usd, ep_t in temizlendi:
                    # Dolar formatı
                    if ep_usd >= 1e9:
                        usd_str = f"${ep_usd/1e9:.1f}B"
                    elif ep_usd >= 1e6:
                        usd_str = f"${ep_usd/1e6:.0f}M"
                    else:
                        usd_str = f"${ep_usd/1e3:.0f}K"
                    # Fiyat formatı — binlik ayraç, USD miktarından net ayrılmış
                    if ep_fiyat >= 1000:
                        fiyat_str = f"${ep_fiyat:,.0f}"
                    elif ep_fiyat >= 1:
                        fiyat_str = f"${ep_fiyat:.2f}"
                    else:
                        fiyat_str = f"${ep_fiyat:.5f}"
                    # Format: "$76,867 · $347M LONG"
                    etiket = f"{fiyat_str} · {usd_str} {yon_str}"
                    yakin = abs(ep_fiyat - fiyat) / fiyat < 0.015
                    renk  = "#FFD700" if yakin else renk_baz
                    ax.annotate(
                        etiket,
                        xy=(ep_t, ep_fiyat),
                        color=renk, fontsize=6.5, fontweight="bold",
                        va="center", ha="left",
                        bbox=dict(boxstyle="round,pad=0.25", facecolor="#050A14",
                                  alpha=0.85, edgecolor=renk_baz, linewidth=0.5),
                        zorder=10
                    )

            _bant_etiketleri(band_long_usd,  grid_long,  "#FF6B6B", "LONG")
            _bant_etiketleri(band_short_usd, grid_short, "#69FF69", "SHORT")

        except Exception as _e:
            print(f"[LIQ] Dolar etiket hatasi: {_e}")

        # Likidasyon bölgesi — band_arr'dan hesapla (etiket hatasından bağımsız)
        try:
            # Direkt grid_long / grid_short 1D üzerinden min-max bölge hesabı
            # Harita ile birebir aynı veri — eşiğin üzerindeki tüm bantların min/max'ı
            # Eşik coin bazında: BTC %25 (geniş dağılım), ETH %45 (yoğun küme)
            _esik_pct = 0.45 if "ETH" in sym else 0.25
            def _grid_minmax(grid_1d, fiyat_ref, taraf, n_pb_, price_min_, price_max_, esik_pct=_esik_pct):
                if grid_1d is None or grid_1d.max() <= 0:
                    return None
                esik = grid_1d.max() * esik_pct  # coin bazında eşik
                bant_w = (price_max_ - price_min_) / n_pb_
                aktif = []
                for idx in range(n_pb_):
                    if grid_1d[idx] < esik:
                        continue
                    fiyat_alt = price_min_ + idx * bant_w
                    fiyat_ust = fiyat_alt + bant_w
                    merkez    = (fiyat_alt + fiyat_ust) / 2
                    if taraf == "long"  and merkez >= fiyat_ref: continue
                    if taraf == "short" and merkez <= fiyat_ref: continue
                    aktif.append((fiyat_alt, fiyat_ust))
                if not aktif:
                    return None
                alt = round(min(a for a, _ in aktif), 2)
                ust = round(max(u for _, u in aktif), 2)
                return (alt, ust)

            # grid_long_1d / grid_short_1d normalize öncesi ham değerler henüz yok;
            # normalize sonrası grid sum(axis=1) kullanıyoruz — haritayla aynı veri
            grid_long_1d_tmp  = grid_long.sum(axis=1)
            grid_short_1d_tmp = grid_short.sum(axis=1)

            liq_long_zone  = _grid_minmax(grid_long_1d_tmp,  fiyat, "long",  n_pb, price_min, price_max)
            liq_short_zone = _grid_minmax(grid_short_1d_tmp, fiyat, "short", n_pb, price_min, price_max)
        except Exception as _e2:
            print(f"[LIQ] Bolge hesaplama hatasi: {_e2}")
            liq_long_zone  = None
            liq_short_zone = None

        sym_kisa  = sym.replace("USDT", "")
        ws_notu   = f"{len(events)} gercek likidasyon" if len(events) >= 5 else "Kaldirac tahmini"
        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        ax.set_title(
            f"BEN KUL YUTMAM  |  {sym_kisa}/USDT  Likidasyon Isı Haritası\n"
            f"Binance Futures · {zaman_str} · Son {saat}s · {ws_notu}",
            color="#E8E8E6", fontsize=8, pad=6, loc="left"
        )

        # Sağ üst köşe — açıklama
        ax.text(0.995, 0.98,
                "Sari = yogun likidasyon  |  Kirmizi = LONG lik.  |  Yesil = SHORT lik.",
                transform=ax.transAxes, color="#6B7280", fontsize=5.5,
                ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#0A0E1A", alpha=0.7))

        plt.tight_layout(pad=0.6)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor="#050A14", edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        # Grid satır toplamları — metin için likidasyon bölgesi hesabında kullanılır
        grid_long_1d  = grid_long.sum(axis=1)   # her fiyat bandındaki toplam long yoğunluk
        grid_short_1d = grid_short.sum(axis=1)  # her fiyat bandındaki toplam short yoğunluk

        return {
            "img":            buf.read(),
            "grid_long":      grid_long_1d,
            "grid_short":     grid_short_1d,
            "price_min":      price_min,
            "price_max":      price_max,
            "n_pb":           n_pb,
            "fiyat":          fiyat,
            "liq_long_zone":  liq_long_zone,
            "liq_short_zone": liq_short_zone,
        }

    except Exception as e:
        print(f"[LIQ_WS] Heatmap hatasi: {e}")
        import traceback; traceback.print_exc()
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy.ndimage import gaussian_filter
        import io

        sym = symbol  # BTCUSDT / ETHUSDT
        with _liq_ws_kilit:
            events = list(_liq_ws_data.get(sym, []))

        # Mevcut fiyat ve OHLCV çek
        r = requests.get("https://fapi.binance.com/fapi/v1/klines",
                         params={"symbol": sym, "interval": "5m",
                                 "limit": int(saat * 12)}, timeout=8,
                         proxies=BINANCE_PROXY)
        klines = r.json() if r.status_code == 200 else []

        if not klines:
            return None

        fiyat     = float(klines[-1][4])
        timestamps = [int(k[0]) for k in klines]
        closes     = [float(k[4]) for k in klines]
        highs      = [float(k[2]) for k in klines]
        lows       = [float(k[3]) for k in klines]

        price_min = min(lows) * 0.998
        price_max = max(highs) * 1.002
        t_start   = timestamps[0]
        t_end     = timestamps[-1] + 5 * 60 * 1000

        n_tb = min(len(klines), 100)
        n_pb = 80

        price_edges = np.linspace(price_min, price_max, n_pb + 1)
        grid        = np.zeros((n_pb, n_tb))

        if len(events) >= 10:
            # Gerçek veri var
            for ts_ms, price, usd, side in events:
                if not (t_start <= ts_ms <= t_end):
                    continue
                t_bin = int((ts_ms - t_start) / (t_end - t_start) * n_tb)
                t_bin = max(0, min(n_tb - 1, t_bin))
                p_bin = int((price - price_min) / (price_max - price_min) * n_pb)
                p_bin = max(0, min(n_pb - 1, p_bin))
                grid[p_bin, t_bin] += usd
            print(f"[LIQ_WS] {sym} gerçek veri kullanıldı: {len(events)} olay")
        else:
            # Yeterli gerçek veri yok — klines'tan tahmin
            print(f"[LIQ_WS] {sym} yeterli veri yok ({len(events)} olay), tahmin modu.")
            for i, k in enumerate(klines):
                t_bin  = int(i / len(klines) * n_tb)
                k_high = float(k[2]); k_low = float(k[3])
                k_vol  = float(k[5]); k_open = float(k[1]); k_close = float(k[4])
                yukari = k_close > k_open

                # Short likidasyon — mum yukarı gidince yukarıdaki short'lar ezilir
                if yukari and k_vol > 0:
                    target = k_high + (k_high - k_low) * 0.3
                    p_bin  = int((target - price_min) / (price_max - price_min) * n_pb)
                    p_bin  = max(0, min(n_pb - 1, p_bin))
                    grid[p_bin, t_bin] += k_vol * float(k[4]) * 0.3

                # Long likidasyon — mum aşağı gidince aşağıdaki long'lar ezilir
                if not yukari and k_vol > 0:
                    target = k_low - (k_high - k_low) * 0.3
                    p_bin  = int((target - price_min) / (price_max - price_min) * n_pb)
                    p_bin  = max(0, min(n_pb - 1, p_bin))
                    grid[p_bin, t_bin] += k_vol * float(k[4]) * 0.3

        # Yumuşat ve normalize
        grid = gaussian_filter(grid, sigma=[1.5, 1.0])
        if grid.max() > 0:
            grid = np.log1p(grid)
            grid /= grid.max()

        # ── Grafik ──
        fig, ax = plt.subplots(figsize=(12, 5))
        fig.patch.set_facecolor("#050A14")
        ax.set_facecolor("#050A14")

        ax.imshow(grid, aspect="auto", origin="lower",
                  extent=[0, n_tb, price_min, price_max],
                  cmap="inferno", interpolation="bilinear",
                  alpha=0.92, vmin=0, vmax=1)

        # Fiyat çizgisi
        price_x = np.linspace(0, n_tb, len(closes))
        ax.plot(price_x, closes, color="#FFFFFF", linewidth=1.2, alpha=0.85, zorder=5)
        ax.scatter([n_tb], [fiyat], color="#5B9CF6", s=40, zorder=6)
        if fiyat >= 1000:
            fiyat_label = f"${fiyat:,.0f}"
        else:
            fiyat_label = f"${fiyat:.3f}"
        ax.annotate(fiyat_label, xy=(n_tb, fiyat),
                    xytext=(-65, 4), textcoords="offset points",
                    color="#5B9CF6", fontsize=8, fontweight="bold")

        # Y ekseni
        y_ticks = np.linspace(price_min * 1.001, price_max * 0.999, 8)
        ax.set_yticks(y_ticks)
        if fiyat >= 1000:
            ax.set_yticklabels([f"${t:,.0f}" for t in y_ticks], fontsize=7, color="#9CA3AF")
        else:
            ax.set_yticklabels([f"${t:.4f}" for t in y_ticks], fontsize=7, color="#9CA3AF")

        # X ekseni — saat etiketleri
        x_pos = np.linspace(0, n_tb, 7)
        x_lbl = []
        for i in range(7):
            idx = int(i * (len(klines) - 1) / 6)
            ts  = timestamps[idx]
            dt  = datetime.utcfromtimestamp(ts / 1000)
            if TR_TZ:
                from datetime import timezone
                dt = datetime.fromtimestamp(ts / 1000, tz=TR_TZ)
            x_lbl.append(dt.strftime("%H:%M"))
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_lbl, fontsize=7, color="#9CA3AF")

        ax.yaxis.grid(True, color="#1F2937", linewidth=0.4, alpha=0.5)
        ax.xaxis.grid(True, color="#1F2937", linewidth=0.4, alpha=0.5)
        for spine in ax.spines.values():
            spine.set_edgecolor("#1F2937")

        sym_kisa = sym.replace("USDT", "")
        veri_notu = f"Gercek veri: {len(events)} likidasyon" if len(events) >= 10 else "Tahmin modu"
        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        ax.set_title(
            f"BEN KUL YUTMAM  |  {sym_kisa}/USDT — Likidas yon Isi Haritasi\n"
            f"Binance Futures  ·  {zaman_str}  ·  Son {saat}s  ·  {veri_notu}",
            color="#E8E8E6", fontsize=8, pad=8, loc="left"
        )

        ax.text(0.995, 0.97,
                "Sari/turuncu = yogun likidasyon bolgesi",
                transform=ax.transAxes, color="#9CA3AF", fontsize=6,
                ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#111827", alpha=0.6))

        plt.tight_layout(pad=0.8)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor="#050A14", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        print(f"[LIQ_WS] Heatmap hatasi: {e}")
        import traceback; traceback.print_exc()
        return None


def _liq_gorsel(veri):
    """Likidisyon baskı haritası PNG üret."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np
        import io

        sym      = veri["symbol"]
        fiyat    = veri["fiyat"]
        high_24h = veri["high_24h"]
        low_24h  = veri["low_24h"]
        funding  = veri["funding"]
        oi_toplam = veri["oi_toplam"]
        oi_degisim = veri["oi_degisim"]
        degisim  = veri["degisim"]
        klines   = veri["klines"]

        # Fiyat bantlarını oluştur
        aralik   = high_24h - low_24h
        if aralik <= 0:
            aralik = fiyat * 0.02
        adim     = aralik / 10
        bantlar  = [low_24h + i * adim for i in range(11)]

        # Her bant için tahmini baskı hesapla
        # Kline volume'u fiyat seviyesine dağıt
        long_baskisi  = []
        short_baskisi = []
        for b in bantlar:
            long_agirlik  = max(0, (b - low_24h) / aralik) if aralik > 0 else 0
            short_agirlik = max(0, (high_24h - b) / aralik) if aralik > 0 else 0
            try:
                vol = sum(float(k[5]) for k in klines if float(k[3]) <= b <= float(k[2])) if klines else 1
            except:
                vol = 1
            long_baskisi.append(long_agirlik * vol * (1 - funding * 5) if funding < 0 else long_agirlik * vol)
            short_baskisi.append(short_agirlik * vol * (1 + funding * 5) if funding > 0 else short_agirlik * vol)

        # Normalize
        max_val = max(max(long_baskisi + short_baskisi), 1)
        long_baskisi  = [v / max_val for v in long_baskisi]
        short_baskisi = [v / max_val for v in short_baskisi]

        # Grafik
        fig, ax = plt.subplots(figsize=(7, 4))
        fig.patch.set_facecolor("#0A0E1A")
        ax.set_facecolor("#0A0E1A")

        bant_etiketleri = [f"${b:,.0f}" for b in bantlar]
        x = np.arange(len(bantlar))
        w = 0.38

        bars_l = ax.bar(x - w/2, long_baskisi,  w, color="#F44336", alpha=0.85, label="Long Baskısı",  zorder=3)
        bars_s = ax.bar(x + w/2, short_baskisi, w, color="#4CAF50", alpha=0.85, label="Short Baskısı", zorder=3)

        # Güncel fiyat çizgisi
        if low_24h <= fiyat <= high_24h:
            fiyat_idx = (fiyat - low_24h) / adim
            ax.axvline(x=fiyat_idx - 0.5, color="#5B9CF6", linewidth=1.5,
                       linestyle="--", zorder=4, label=f"Fiyat ${fiyat:,.0f}")

        # Stil
        ax.set_xticks(x)
        ax.set_xticklabels(bant_etiketleri, fontsize=7, color="#9CA3AF", rotation=30, ha="right")
        ax.set_yticks([])
        ax.tick_params(colors="#9CA3AF")
        for spine in ax.spines.values():
            spine.set_edgecolor("#1F2937")
        ax.yaxis.grid(True, color="#1F2937", linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)

        sym_kisa = sym.replace("USDT", "")
        emoji    = "₿" if "BTC" in sym else "Ξ"
        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        ax.set_title(f"{emoji} {sym_kisa}/USDT — Likidasyon Grafiği\n"
                     f"Binance Futures  ·  {zaman_str}",
                     color="#E8E8E6", fontsize=9, pad=8)

        legend = ax.legend(fontsize=7, facecolor="#111827", edgecolor="#1F2937",
                           labelcolor="#9CA3AF", loc="upper right")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                    facecolor="#0A0E1A", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[LIQ] Gorsel hatasi: {e}")
        return None


def _liq_heatmap(veri):
    """Likidasyon yoğunluk ısı haritası — fiyat ekseninde tahmini long/short birikim gösterimi."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        import numpy as np
        import io

        sym      = veri["symbol"]
        fiyat    = veri["fiyat"]
        high_24h = veri["high_24h"]
        low_24h  = veri["low_24h"]
        funding  = veri["funding"]
        klines   = veri["klines"]

        aralik = high_24h - low_24h
        if aralik <= 0:
            aralik = fiyat * 0.02

        # 20 bant oluştur
        n_bant   = 20
        adim     = aralik / n_bant
        bantlar  = [low_24h + i * adim for i in range(n_bant + 1)]
        merkez   = [(bantlar[i] + bantlar[i+1]) / 2 for i in range(n_bant)]

        # Her bant için hacim birikimi hesapla
        long_yogunluk  = np.zeros(n_bant)
        short_yogunluk = np.zeros(n_bant)

        for k in klines:
            try:
                k_ac  = float(k[1])
                k_kap = float(k[4])
                k_yuk = float(k[2])
                k_dus = float(k[3])
                k_vol = float(k[5])
                yukari = k_kap > k_ac

                for i, m in enumerate(merkez):
                    if k_dus <= m <= k_yuk:
                        agirlik = 1 - abs(m - (k_ac + k_kap) / 2) / (aralik + 1e-9)
                        agirlik = max(0, agirlik)
                        if yukari:
                            short_yogunluk[i] += k_vol * agirlik  # yukarı mum → short likidasyon riski
                        else:
                            long_yogunluk[i]  += k_vol * agirlik  # aşağı mum → long likidasyon riski
            except:
                continue

        # Funding etkisi
        if funding > 0.005:
            long_yogunluk  *= (1 + funding * 10)
        elif funding < -0.005:
            short_yogunluk *= (1 - funding * 10)

        # Normalize 0-1
        max_l = max(long_yogunluk.max(), 1e-9)
        max_s = max(short_yogunluk.max(), 1e-9)
        long_yogunluk  = long_yogunluk  / max_l
        short_yogunluk = short_yogunluk / max_s

        # ── Grafik ──
        fig, ax = plt.subplots(figsize=(2.5, 6))
        fig.patch.set_facecolor("#0A0E1A")
        ax.set_facecolor("#0A0E1A")

        bar_h = adim * 0.85

        for i, m in enumerate(merkez):
            # Long likidasyon (kırmızı — solda)
            lv = long_yogunluk[i]
            if lv > 0.05:
                r = plt.Rectangle((-lv, m - bar_h/2), lv, bar_h,
                                   color="#F44336", alpha=min(0.3 + lv * 0.7, 0.95))
                ax.add_patch(r)

            # Short likidasyon (yeşil — sağda)
            sv = short_yogunluk[i]
            if sv > 0.05:
                r = plt.Rectangle((0, m - bar_h/2), sv, bar_h,
                                   color="#4CAF50", alpha=min(0.3 + sv * 0.7, 0.95))
                ax.add_patch(r)

        # Fiyat çizgisi
        ax.axhline(y=fiyat, color="#5B9CF6", linewidth=1.5, linestyle="--", zorder=5)

        # Eksen
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(low_24h - adim, high_24h + adim)
        ax.set_xticks([])
        ax.axvline(x=0, color="#374151", linewidth=0.8)

        # Y ekseni fiyat etiketleri
        tick_adim = aralik / 5
        ticks = [low_24h + i * tick_adim for i in range(6)]
        if fiyat not in ticks:
            ticks.append(fiyat)
        ticks = sorted(set(ticks))
        ax.set_yticks(ticks)
        if fiyat >= 1000:
            ax.set_yticklabels([f"${t:,.0f}" for t in ticks], fontsize=7, color="#9CA3AF")
        else:
            ax.set_yticklabels([f"${t:.3f}" for t in ticks], fontsize=7, color="#9CA3AF")

        # Güncel fiyat etiketi
        if fiyat >= 1000:
            fiyat_label = f"${fiyat:,.0f}"
        else:
            fiyat_label = f"${fiyat:.3f}"
        ax.annotate(fiyat_label, xy=(0, fiyat), xytext=(0.05, fiyat),
                    color="#5B9CF6", fontsize=7, fontweight="bold",
                    va="center")

        for spine in ax.spines.values():
            spine.set_edgecolor("#1F2937")

        # Sol/Sağ etiket
        ax.text(-0.55, high_24h + adim * 0.6, "LONG\nLİK.", color="#F44336",
                fontsize=7, ha="center", fontweight="bold")
        ax.text(0.55, high_24h + adim * 0.6, "SHORT\nLİK.", color="#4CAF50",
                fontsize=7, ha="center", fontweight="bold")

        sym_kisa = sym.replace("USDT", "")
        emoji    = "₿" if "BTC" in sym else "Ξ"
        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        ax.set_title(f"{emoji} {sym_kisa}/USDT — Likidasyon Isı Haritası\n"
                     f"Binance Futures  ·  {zaman_str}",
                     color="#E8E8E6", fontsize=8, pad=6)

        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                    facecolor="#0A0E1A", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[LIQ] Heatmap hatasi: {e}")
        return None


def _liq_yorum(veri):
    """Likidasyon baskı yorumu — bölgeler ısı haritası grid'inden okunur."""
    fiyat     = veri["fiyat"]
    high_24h  = veri["high_24h"]
    low_24h   = veri["low_24h"]
    destek    = veri.get("destek")
    direnc    = veri.get("direnc")
    mom       = veri.get("momentum_4h")
    grid_data = veri.get("liq_grid")
    sym_kisa  = veri["symbol"].replace("USDT", "")
    emoji     = "₿" if "BTC" in veri["symbol"] else "Ξ"

    def fmt(p):
        return f"${p:,.0f}" if p >= 100 else f"${p:,.3f}" if p < 1 else f"${p:,.2f}"

    satirlar = [f"📊 <b>{emoji} {sym_kisa} Likidisyon Baskı Yorumu</b>\n"]

    # ── 4H Momentum ──
    if mom:
        m_pct = mom["momentum_pct"]
        a_pct = mom["alis_pct"]
        if m_pct > 1.5 and a_pct > 55:
            satirlar.append(f"🚀 4H Momentum: <b>+{m_pct:.1f}%</b> — Alıcı ağırlıklı (%{a_pct:.0f})")
        elif m_pct < -1.5 and a_pct < 45:
            satirlar.append(f"🔻 4H Momentum: <b>{m_pct:.1f}%</b> — Satıcı ağırlıklı (%{100-a_pct:.0f})")
        elif a_pct > 60:
            satirlar.append(f"📊 4H Momentum: <b>{m_pct:+.1f}%</b> — Alıcı baskısı güçlü (%{a_pct:.0f})")
        elif a_pct < 40:
            satirlar.append(f"📊 4H Momentum: <b>{m_pct:+.1f}%</b> — Satıcı baskısı güçlü (%{100-a_pct:.0f})")
        else:
            satirlar.append(f"📊 4H Momentum: <b>{m_pct:+.1f}%</b> — Dengeli")

    # ── Likidasyon bölgeleri — grid'den oku ──
    satirlar.append("")
    liq_long_alt = liq_long_ust = liq_short_alt = liq_short_ust = None

    if grid_data:
        liq_long_zone  = grid_data.get("liq_long_zone")
        liq_short_zone = grid_data.get("liq_short_zone")
        if liq_long_zone:
            liq_long_alt, liq_long_ust = liq_long_zone
        if liq_short_zone:
            liq_short_alt, liq_short_ust = liq_short_zone

    if liq_long_alt and liq_long_ust:
        satirlar.append(f"🔴 <b>Long Likidasyon Bölgesi:</b> {fmt(liq_long_alt)} — {fmt(liq_long_ust)}")
    if liq_short_alt and liq_short_ust:
        satirlar.append(f"🟢 <b>Short Likidasyon Bölgesi:</b> {fmt(liq_short_alt)} — {fmt(liq_short_ust)}")

    if destek:
        d1 = fmt(destek[0])
        d2 = fmt(destek[1]) if len(destek) > 1 and destek[1] != destek[0] else None
        satirlar.append(f"🛡 <b>Destek:</b> {d1}" + (f" / {d2}" if d2 else ""))
    if direnc:
        r1 = fmt(direnc[0])
        r2 = fmt(direnc[1]) if len(direnc) > 1 and direnc[1] != direnc[0] else None
        satirlar.append(f"🎯 <b>Direnç:</b> {r1}" + (f" / {r2}" if r2 else ""))

    # ── Risk değerlendirmesi ──
    if destek and direnc and fiyat:
        satirlar.append("")
        satirlar.append("📍 <b>Risk Değerlendirmesi</b>")

        if liq_long_alt and liq_long_ust:
            uzaklik_long = abs(fiyat - liq_long_ust) / fiyat * 100
            if uzaklik_long < 1.5:
                satirlar.append(f"⚠️ Fiyat long likidasyon bölgesine çok yakın (%{uzaklik_long:.1f}) — Sert düşüş olabilir")

        if liq_short_alt and liq_short_ust:
            uzaklik_short = abs(fiyat - liq_short_alt) / fiyat * 100
            if uzaklik_short < 1.5:
                satirlar.append(f"⚠️ Fiyat short likidasyon bölgesine çok yakın (%{uzaklik_short:.1f}) — Sert yükseliş olabilir")

        aralik_pct = abs(direnc[-1] - destek[-1]) / fiyat * 100
        if aralik_pct < 2:
            satirlar.append(f"📌 Destek-direnç arası dar (%{aralik_pct:.1f}) — Kırılım bekleniyor")

    return "\n".join(satirlar)


def _liq_gonder():
    """BTC ve ETH için likidasyon baskı haritası + yorum → TOPIC_PIYASA. Her :30'da çalışır."""
    print("[LIQ] Zamanlayici tetiklendi — veri çekiliyor.")
    hedef = TOPIC_ANALIZ
    if TR_TZ:
        zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
    else:
        zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
    for sym in ["BTCUSDT", "ETHUSDT"]:
        try:
            veri = _liq_veri_cek(sym)
            if not veri:
                # 1 kez retry — proxy timeout olabilir
                print(f"[LIQ] {sym} veri alinamadi, 5sn sonra retry...")
                time.sleep(5)
                veri = _liq_veri_cek(sym)
            if not veri:
                print(f"[LIQ] {sym} retry sonrasi da alinamadi, atlaniyor.")
                continue
            sym_kisa = sym.replace("USDT", "")
            # Sadece ısı haritası — grafik kaldırıldı
            heatmap_sonuc = _liq_heatmap_gercek(sym, saat=6)
            if heatmap_sonuc:
                _topic_foto_gonder_filigranli(
                    hedef, heatmap_sonuc["img"],
                    f"🌡 {sym_kisa} Likidasyon Isı Haritası — {zaman_str}\n/liq"
                )
                time.sleep(1)
                veri["liq_grid"] = heatmap_sonuc
            yorum_raw = _liq_yorum(veri)
            _telegram_topic_mesaj_gonder(hedef, yorum_raw + "\n\n<code>/liq</code>")
            print(f"[LIQ] {sym} → TOPIC_PIYASA gonderildi.")
            time.sleep(3)
        except Exception as e:
            print(f"[LIQ] {sym} hata: {e}")


def _liq_zamanlayici():
    """Her saat :45'te likidasyon haritası + yorum → TOPIC_PIYASA."""
    import datetime as dt_mod
    print("[LIQ] Zamanlayici basladi. Her saat :45'te TOPIC_PIYASA'ya gonderilecek.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()
            # Sonraki :45
            dk = simdi.minute
            if dk < 45:
                sonraki = simdi.replace(minute=45, second=0, microsecond=0)
            else:
                sonraki = (simdi.replace(minute=45, second=0, microsecond=0)
                           + dt_mod.timedelta(hours=1))
            bekle = (sonraki - simdi).total_seconds()
            print(f"[LIQ] Sonraki rapor: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(max(bekle, 1))
            _liq_gonder()
            time.sleep(10)  # double-fire önleme
        except Exception as e:
            print(f"[LIQ] Zamanlayici hata: {e}")
            time.sleep(60)



    print(f"[OI] Zamanlayici basladi. Interval: {WHALE_OI_INTERVAL} dakika.")
    time.sleep(60)
    oi, fiyat = _oi_cek("BTCUSDT")
    if oi:
        print(f"[OI] Endpoint ACIK. BTC OI={oi:.0f} Fiyat={fiyat:.1f}")
    else:
        print(f"[OI] Endpoint KAPALI veya hata!")
    while True:
        try:
            _oi_kontrol()
            time.sleep(WHALE_OI_INTERVAL * 60)
        except Exception as e:
            print(f"[OI] Zamanlayici hata: {e}")
            time.sleep(60)


# ==========================================
# HYPERLİQUID BALINA CÜZDAN TAKİBİ
# ==========================================

HL_CUZDANLAR = {
    "0x08c14b32c8a48894e4b933090ebcc9ce33b21135": "Balina 1",
    "0x3ee505ba316879d246a8fd2b3d7ee63b51b44fab": "Balina 2",
    "0x2cd991f48ba31536a96b772536a1daaaedf150ae": "Balina 3",
    "0xcc221419e754b43b2b5a9482909d8892ef70c838": "Balina 4",
    "0x41f9ae0b64a0ec4adc788ee5c82d4b824f839017": "Balina 5",
    "0x7fdafde5cfb5465924316eced2d3715494c517d1": "Balina 6",
    "0x06cecfbac34101ae41c88ebc2450f8602b3d164b": "Balina 7",
    "0x5559da6ec434c5723d0ce9c4da7f29e3f8a3d43b": "Balina 8",
    "0xa87a233e8a7d8951ff790a2e39738086cb5f71b7": "Balina 9",
    "0x99967871e6c4f9a5185abc57edede9e9540191f6": "Balina 10",
    "0x5f94a51948d2376ad34a6fadfa2544e651b74b96": "Balina 11",
    "0xdd7a372377fc633f74ab6e20963803d52f448830": "Balina 12",
    "0xdbd1bac81ad581c7198c9d155ca468f32a0c29dd": "Balina 13",
    "0x72988778525f0ce15c5ac1804ac460606a987d6c": "Balina 14",
    "0xfdf891f2b214a4c9374d26595ec6d4080262e381": "Balina 15",
    "0xe639710e64d7094f7f82ab495915559c2f612953": "Balina 16",
    "0x179c17d04be626561b0355a248d6055a80456aa5": "Balina 17",
    "0x8cc94dc843e1ea7a19805e0cca43001123512b6a": "Balina 18",
    "0x782e432267376f377585fc78092d998f8442ab83": "Balina 19",
    "0x5b5d51203a0f9079f8aeb098a6523a13f298c060": "Balina 20",
    "0x393d0b87ed38fc779fd9611144ae649ba6082109": "Balina 21",
    "0x488d2a9b70cc18ef66057a48ab3d59da1c59fe08": "Balina 22",
    "0x4eb8d907136189a34c9b087950211b6a566f7819": "Balina 23",
    "0xeadc152ac1014ace57c6b353f89adf5faffe9d55": "Balina 24",
    "0x4ec8fe22a531a96c8a846aaf5cbef73202649a80": "Balina 25",
    "0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00": "Balina 26",
}

HL_MIN_USD     = float(os.getenv("HL_MIN_USD", "50000"))    # Min $50K pozisyon (hassasiyet artırıldı)
HL_INTERVAL    = int(os.getenv("HL_INTERVAL",  "5"))        # Dakika
_hl_onceki     = {}  # {adres: {coin: {szi, entryPx, unrealizedPnl}}}


def _hl_pozisyon_cek(adres):
    """Hyperliquid'dan cüzdanın açık pozisyonlarını çek."""
    try:
        r = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "clearinghouseState", "user": adres},
            headers={"Content-Type": "application/json"},
            timeout=8
        )
        if r.status_code == 200:
            data = r.json()
            pozlar = {}
            for p in data.get("assetPositions", []):
                pos  = p.get("position", {})
                coin = pos.get("coin", "")
                szi  = float(pos.get("szi", 0))
                if szi == 0:
                    continue
                entry_px   = float(pos.get("entryPx") or 0)
                unrealized = float(pos.get("unrealizedPnl") or 0)
                pozlar[coin] = {
                    "szi":           szi,
                    "entryPx":       entry_px,
                    "unrealizedPnl": unrealized,
                }
            return pozlar
    except Exception as e:
        print(f"[HL] {adres[:10]} cekme hatasi: {e}")
    return None


def _hl_gorsel(isim, adres, pozlar, zaman_str):
    """Hyperliquid pozisyonları için PNG tablo üret."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import io

        # Sadece HL_MIN_USD üzeri, USD'ye göre sırala
        sirali = sorted(
            [(c, p) for c, p in pozlar.items() if abs(p["szi"]) * p["entryPx"] >= HL_MIN_USD],
            key=lambda x: abs(x[1]["szi"]) * x[1]["entryPx"],
            reverse=True
        )
        if not sirali:
            return None

        satirlar = []
        for coin, p in sirali:
            szi      = p["szi"]
            entry_px = p["entryPx"]
            pnl      = p["unrealizedPnl"]
            usd      = abs(szi) * entry_px
            yon      = "LONG" if szi > 0 else "SHORT"
            if usd >= 1e6:
                usd_str = f"${usd/1e6:.1f}M"
            else:
                usd_str = f"${usd/1e3:.0f}K"
            if entry_px >= 1000:
                px_str = f"${entry_px:,.0f}"
            elif entry_px >= 1:
                px_str = f"${entry_px:.2f}"
            else:
                px_str = f"${entry_px:.4f}"
            pnl_str = f"+${pnl/1e3:.1f}K" if pnl >= 0 else f"-${abs(pnl)/1e3:.1f}K"
            satirlar.append([coin, yon, usd_str, px_str, pnl_str, pnl >= 0])

        n     = len(satirlar)
        yuk   = max(1.8 + n * 0.42, 3.0)
        fig, ax = plt.subplots(figsize=(7, yuk))
        fig.patch.set_facecolor("#0A0E1A")
        ax.set_facecolor("#0A0E1A")
        ax.axis("off")

        # Başlık
        fig.text(0.5, 0.97, f"🐋  {isim}  —  Hyperliquid Pozisyonlar",
                 ha="center", va="top", fontsize=11, fontweight="bold",
                 color="#E8E8E6", fontfamily="monospace")
        fig.text(0.5, 0.91, f"{adres[:24]}...   |   {zaman_str}",
                 ha="center", va="top", fontsize=8, color="#6B7280",
                 fontfamily="monospace")

        # Tablo verisi
        tablo_veri = [[s[0], s[1], s[2], s[3], s[4]] for s in satirlar]
        kolon_adlari = ["COİN", "YÖN", "BOYUT", "GİRİŞ", "PnL"]

        tablo = ax.table(
            cellText=tablo_veri,
            colLabels=kolon_adlari,
            cellLoc="center",
            loc="center",
            bbox=[0, 0, 1, 0.85]
        )
        tablo.auto_set_font_size(False)
        tablo.set_fontsize(9)

        # Stil
        for (row, col), cell in tablo.get_celld().items():
            cell.set_facecolor("#0A0E1A")
            cell.set_edgecolor("#1F2937")
            cell.set_linewidth(0.5)

            if row == 0:
                cell.set_facecolor("#111827")
                cell.set_text_props(color="#9CA3AF", fontweight="bold", fontsize=8)
            else:
                s = satirlar[row - 1]
                yon_val = s[1]
                pnl_pos = s[5]

                if col == 0:
                    cell.set_text_props(color="#E8E8E6")
                elif col == 1:
                    color = "#4CAF50" if yon_val == "LONG" else "#F44336"
                    cell.set_text_props(color=color)
                elif col == 2:
                    cell.set_text_props(color="#C9A84C")
                elif col == 3:
                    cell.set_text_props(color="#9CA3AF")
                elif col == 4:
                    color = "#4CAF50" if pnl_pos else "#F44336"
                    cell.set_text_props(color=color)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                    facecolor="#0A0E1A", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[HL] Gorsel hata: {e}")
        return None
    """Hyperliquid'dan cüzdanın açık pozisyonlarını çek."""
    try:
        r = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "clearinghouseState", "user": adres},
            headers={"Content-Type": "application/json"},
            timeout=8
        )
        if r.status_code == 200:
            data = r.json()
            pozlar = {}
            for p in data.get("assetPositions", []):
                pos  = p.get("position", {})
                coin = pos.get("coin", "")
                szi  = float(pos.get("szi", 0))
                if szi == 0:
                    continue
                entry_px    = float(pos.get("entryPx") or 0)
                unrealized  = float(pos.get("unrealizedPnl") or 0)
                pozlar[coin] = {
                    "szi":          szi,
                    "entryPx":      entry_px,
                    "unrealizedPnl": unrealized,
                }
            return pozlar
    except Exception as e:
        print(f"[HL] {adres[:10]} cekme hatasi: {e}")
    return None


def _hl_mesaj_olustur(isim, adres, coin, olay, szi, entry_px, pnl=None, onceki_szi=None):
    """Hyperliquid pozisyon değişikliği bildirimi — kompakt grid format."""
    yon      = "LONG" if szi > 0 else "SHORT"
    szi_abs  = abs(szi)
    usd      = szi_abs * entry_px

    if usd >= 1e9:
        usd_str = f"${usd/1e9:.2f}B"
    elif usd >= 1e6:
        usd_str = f"${usd/1e6:.1f}M"
    else:
        usd_str = f"${usd/1e3:.0f}K"

    if entry_px >= 1000:
        px_str = f"${entry_px:,.0f}"
    elif entry_px >= 1:
        px_str = f"${entry_px:.2f}"
    else:
        px_str = f"${entry_px:.4f}"

    if olay == "ACILDI":
        olay_str = "Yeni Pozisyon"
    elif olay == "KAPATILDI":
        olay_str = "Pozisyon Kapandı"
    else:
        olay_str = "Pozisyon Değişti"

    if TR_TZ:
        zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
    else:
        zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

    yon_emoji = "🟢" if szi > 0 else "🔴"

    ayrac = "━" * 16
    mesaj = (
        f"🐋 <b>{isim} — {olay_str}</b>\n"
        f"<code>{adres[:20]}...</code> · {zaman_str}\n\n"
        f"{yon_emoji} <b>{coin}/USDC</b> · {yon}\n"
        f"💰 <b>{usd_str}</b>   📌 {px_str}"
    )

    if onceki_szi is not None and olay == "DEGISTI":
        degisim_pct = (szi - onceki_szi) / abs(onceki_szi) * 100 if onceki_szi != 0 else 0
        mesaj += f"\n📊 {abs(onceki_szi):,.2f} → {szi_abs:,.2f} {coin} ({degisim_pct:+.0f}%)"

    if pnl is not None and olay != "ACILDI":
        pnl_emoji = "✅" if pnl >= 0 else "❌"
        if abs(pnl) >= 1e3:
            pnl_str = f"+${pnl/1e3:.1f}K" if pnl >= 0 else f"-${abs(pnl)/1e3:.1f}K"
        else:
            pnl_str = f"+${pnl:.0f}" if pnl >= 0 else f"-${abs(pnl):.0f}"
        mesaj += f"\n{pnl_emoji} PnL: {pnl_str}"

    mesaj += f"\n{ayrac}"
    mesaj += "\n<code>/balina</code>"
    return mesaj


def _hl_kontrol():
    """Tüm cüzdanları kontrol et, değişiklikleri bildir."""
    global _hl_onceki

    for adres, isim in HL_CUZDANLAR.items():
        try:
            yeni_pozlar = _hl_pozisyon_cek(adres)
            if yeni_pozlar is None:
                continue

            onceki_pozlar = _hl_onceki.get(adres, {})

            # İlk çalışma — sadece kaydet, bildirim gönderme
            if adres not in _hl_onceki:
                _hl_onceki[adres] = yeni_pozlar
                print(f"[HL] {isim}: {len(yeni_pozlar)} pozisyon kaydedildi.")
                continue

            # Yeni açılan pozisyonlar
            for coin, yeni in yeni_pozlar.items():
                usd = abs(yeni["szi"]) * yeni["entryPx"]
                if usd < HL_MIN_USD:
                    continue

                if coin not in onceki_pozlar:
                    mesaj = _hl_mesaj_olustur(isim, adres, coin, "ACILDI",
                                               yeni["szi"], yeni["entryPx"])
                    _telegram_topic_mesaj_gonder(TOPIC_BALINA, mesaj)
                    print(f"[HL] {isim} YENİ: {coin} {yeni['szi']} @ {yeni['entryPx']}")

                else:
                    # Boyut önemli ölçüde değiştiyse (%20+)
                    onceki = onceki_pozlar[coin]
                    if onceki["szi"] != 0:
                        degisim_pct = abs(yeni["szi"] - onceki["szi"]) / abs(onceki["szi"]) * 100
                        if degisim_pct >= 20:
                            mesaj = _hl_mesaj_olustur(isim, adres, coin, "DEGISTI",
                                                       yeni["szi"], yeni["entryPx"],
                                                       yeni["unrealizedPnl"], onceki["szi"])
                            _telegram_topic_mesaj_gonder(TOPIC_BALINA, mesaj)
                            print(f"[HL] {isim} DEĞİŞTİ: {coin} {onceki['szi']}→{yeni['szi']}")

            # Kapatılan pozisyonlar
            for coin, onceki in onceki_pozlar.items():
                if coin not in yeni_pozlar:
                    usd = abs(onceki["szi"]) * onceki["entryPx"]
                    if usd < HL_MIN_USD:
                        continue
                    mesaj = _hl_mesaj_olustur(isim, adres, coin, "KAPATILDI",
                                               onceki["szi"], onceki["entryPx"],
                                               onceki["unrealizedPnl"])
                    _telegram_topic_mesaj_gonder(TOPIC_BALINA, mesaj)
                    print(f"[HL] {isim} KAPANDI: {coin}")

            _hl_onceki[adres] = yeni_pozlar

        except Exception as e:
            print(f"[HL] {isim} kontrol hatasi: {e}")


def _hl_zamanlayici():
    """Her HL_INTERVAL dakikada bir cüzdanları kontrol et."""
    print(f"[HL] Zamanlayici basladi. {len(HL_CUZDANLAR)} cüzdan izleniyor. Interval: {HL_INTERVAL} dk.")
    time.sleep(30)  # Başlangıçta bekle
    while True:
        try:
            _hl_kontrol()
            time.sleep(HL_INTERVAL * 60)
        except Exception as e:
            print(f"[HL] Zamanlayici hata: {e}")
            time.sleep(60)


# ==========================================
# HABER SİSTEMİ
# ==========================================

HABER_GONDERILENLER = set()
HABER_GONDERILENLER_DOSYA = "/data/haber_gonderilenler.json"
HABER_TARAMA_SURESI = int(os.getenv("HABER_TARAMA_SURESI", "15"))

HABER_COINLER = ["bitcoin", "btc", "ethereum", "eth"]

RSS_KAYNAKLAR = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
]


def _haber_gonderilenler_yukle():
    global HABER_GONDERILENLER
    try:
        with open(HABER_GONDERILENLER_DOSYA, "r") as f:
            HABER_GONDERILENLER = set(json.load(f))
        print(f"[HABER] {len(HABER_GONDERILENLER)} haber ID yuklendi.")
    except FileNotFoundError:
        print("[HABER] Gecmis haber dosyasi yok, sifirdan basliyor.")
        HABER_GONDERILENLER = set()
    except Exception as e:
        print(f"[HABER] Yukle hatasi: {e}")
        HABER_GONDERILENLER = set()


def _haber_gonderilenler_kaydet():
    try:
        with open(HABER_GONDERILENLER_DOSYA, "w") as f:
            json.dump(list(HABER_GONDERILENLER)[-500:], f)
    except Exception as e:
        print(f"[HABER] Kayit hatasi: {e}")


def _haber_rss_cek(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        haberler = []
        for item in root.findall(".//item")[:20]:
            baslik = item.findtext("title", "").strip()
            link   = item.findtext("link",  "").strip()
            desc   = item.findtext("description", "").strip()
            if baslik and link:
                haberler.append({"baslik": baslik, "link": link, "desc": desc})
        return haberler
    except Exception as e:
        print(f"[HABER] RSS cekme hatasi: {e}")
        return []


def _haber_onemli_mi(baslik, desc=""):
    baslik_lower = baslik.lower()
    coin_var = any(c in baslik_lower for c in HABER_COINLER)
    if not coin_var:
        return False
    yuksek_etki = [
        # Negatif
        "hack", "hacked", "exploit", "stolen", "theft",
        "crash", "crashes", "ban", "banned", "bans",
        "sec sues", "lawsuit", "bankrupt", "bankruptcy",
        "fraud", "scam", "collapse", "collapses",
        "rejected", "rejects", "plunges", "plunge",
        "liquidation", "liquidated", "attack", "breach",
        "prison", "arrested", "criminal", "money laundering",
        "crashed near zero", "crashes near zero",
        "dump", "sell-off", "bearish", "warning", "risk",
        "loses", "drops", "falls", "decline", "tumbles",
        "fears", "concern", "uncertainty", "volatility",
        "probe", "investigation", "charges", "penalty", "fine",
        "restrict", "restriction", "crackdown", "regulate",
        # Pozitif
        "etf approved", "etf approval", "sec approves",
        "all-time high", "ath", "record high",
        "blackrock", "fidelity", "spot etf",
        "legal tender", "country adopts",
        "rate cut", "halving",
        "strategic reserve", "government buys",
        "mass adoption", "retreats below", "outflows",
        "liquidating", "reserve campaign",
        "rally", "surge", "soars", "gains", "rises",
        "bullish", "breakout", "milestone", "record",
        "partnership", "integration", "launch", "upgrade",
        "institutional", "investment", "fund", "billion",
        "fed", "federal reserve", "interest rate", "inflation", "cpi",
        "trump", "congress", "senate", "legislation", "regulation",
    ]
    return any(k in baslik_lower for k in yuksek_etki)


def _haber_cevir(metin):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "tr", "dt": "t", "q": metin}
        r = requests.get(url, params=params, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return "".join([x[0] for x in data[0] if x[0]]).strip()
    except Exception as e:
        print(f"[HABER] Ceviri hatasi: {e}")
    return metin


def _haber_etki_analiz(baslik, desc=""):
    metin = baslik.lower()
    pozitif = [
        "etf approved", "etf approval", "sec approves", "all-time high", "ath",
        "record high", "blackrock", "fidelity", "spot etf", "legal tender",
        "country adopts", "rate cut", "halving", "strategic reserve",
        "government buys", "mass adoption", "rally", "surge", "bullish"
    ]
    negatif = [
        "hack", "hacked", "exploit", "stolen", "theft", "crash", "crashes",
        "ban", "banned", "bans", "sec sues", "lawsuit", "bankrupt", "bankruptcy",
        "fraud", "scam", "collapse", "rejected", "plunges", "plunge",
        "liquidation", "liquidated", "attack", "breach", "prison", "arrested",
        "criminal", "money laundering", "retreats below", "outflows"
    ]
    poz = [k for k in pozitif if k in metin]
    neg = [k for k in negatif if k in metin]
    if neg and not poz:
        etki = "Negatif"
    elif poz and not neg:
        etki = "Pozitif"
    else:
        etki = "Karışık"

    coin_map = {
        "bitcoin": "BTC", "btc": "BTC",
        "ethereum": "ETH", "eth": "ETH",
    }
    coinler = list(dict.fromkeys([v for k, v in coin_map.items() if k in metin]))

    baslik_tr = _haber_cevir(baslik)
    ozet_tr = ""
    if desc:
        try:
            import re
            temiz = re.sub(r"<[^>]+>", "", desc).strip()[:300]
            if temiz:
                ozet_tr = _haber_cevir(temiz)
        except:
            pass

    return {"baslik_tr": baslik_tr, "ozet_tr": ozet_tr, "etki": etki, "etkilenen_coinler": coinler}


def _haber_mesaj_olustur(baslik, link, kaynak, analiz):
    if analiz:
        etki      = analiz.get("etki", "Karışık")
        baslik_tr = analiz.get("baslik_tr", baslik)
        ozet_tr   = analiz.get("ozet_tr", "")
        coinler   = ", ".join(analiz.get("etkilenen_coinler", []))
        emoji     = "🟢" if etki == "Pozitif" else "🔴" if etki == "Negatif" else "🟡"
        msg  = f"📰 <b>ÖNEMLİ HABER</b>\n\n"
        msg += f"📌 <b>{baslik_tr}</b>\n\n"
        if ozet_tr:
            msg += f"📝 {ozet_tr}\n\n"
        msg += f"{emoji} <b>Piyasa Etkisi:</b> {etki}\n"
        if coinler:
            msg += f"⚡ <b>Etkilenen:</b> {coinler}\n"
        msg += f"\n<i>Kaynak: {kaynak}</i>"
    else:
        msg = f"📰 <b>ÖNEMLİ HABER</b>\n\n📌 <b>{baslik}</b>\n\n<i>Kaynak: {kaynak}</i>"
    msg += "\n\n<code>/haber</code>"
    return msg


def _haber_kontrol():
    global HABER_GONDERILENLER
    yeni = 0
    for kaynak_adi, rss_url in RSS_KAYNAKLAR:
        haberler = _haber_rss_cek(rss_url)
        for haber in haberler:
            haber_id = haber["link"]
            if haber_id in HABER_GONDERILENLER:
                continue
            if not _haber_onemli_mi(haber["baslik"], haber.get("desc", "")):
                continue
            print(f"[HABER] Onemli haber: {haber['baslik'][:60]}...")
            analiz = _haber_etki_analiz(haber["baslik"], haber.get("desc", ""))
            mesaj  = _haber_mesaj_olustur(haber["baslik"], haber["link"], kaynak_adi, analiz)
            _telegram_topic_mesaj_gonder(TOPIC_HABER, mesaj)
            HABER_GONDERILENLER.add(haber_id)
            _haber_gonderilenler_kaydet()
            yeni += 1
            time.sleep(2)
    if len(HABER_GONDERILENLER) > 500:
        HABER_GONDERILENLER = set(list(HABER_GONDERILENLER)[-250:])
        _haber_gonderilenler_kaydet()
    print(f"[HABER] Kontrol tamamlandi. {yeni} yeni haber gonderildi.")


def _haber_zamanlayici():
    """Her HABER_TARAMA_SURESI dakikada bir haberleri kontrol et."""
    print(f"[HABER] Zamanlayici basladi. Tarama suresi: {HABER_TARAMA_SURESI} dakika.")
    time.sleep(30)
    while True:
        try:
            _haber_kontrol()
            time.sleep(HABER_TARAMA_SURESI * 60)
        except Exception as e:
            print(f"[HABER] Zamanlayici hata: {e}")
            time.sleep(60)


def _tp_kosul_rapor_hesapla(snapshot=None):
    """Tüm sinyal kayıtlarından TP koşul analizi üret."""
    with gunluk_kilit:
        kayitlar = list(snapshot if snapshot is not None else gunluk_sinyaller)

    def tp_mi(s):
        return any(s.get(k) is True for k in ["tp1_ok","tp2_ok","tp3_ok","tp4_ok","tp5_ok"])

    def satir(kayitlar_sub):
        tp      = sum(1 for s in kayitlar_sub if tp_mi(s))
        sl      = sum(1 for s in kayitlar_sub if s.get("sl_ok") is True and not tp_mi(s))
        devam   = sum(1 for s in kayitlar_sub if not tp_mi(s) and s.get("sl_ok") is not True)
        top     = len(kayitlar_sub)
        oran    = f"%{round(tp/top*100,1)}" if top > 0 else "—"
        return top, tp, devam, sl, oran

    # 1. Sinyal tipi
    tipler = ["Strong Buy", "Long", "Strong Sell", "Short"]
    sinyal_tipi_sonuc = {}
    for t in tipler:
        sub = [s for s in kayitlar if s.get("sinyal_tipi") == t]
        sinyal_tipi_sonuc[t] = satir(sub)

    # 2. Piyasa koşulları
    kosullar = {
        "Piyasa — Yükseliş":      [s for s in kayitlar if s.get("piyasa_yonu") == "Yükseliş"],
        "Piyasa — Düşüş":         [s for s in kayitlar if s.get("piyasa_yonu") == "Düşüş"],
        "Piyasa — Yatay":          [s for s in kayitlar if s.get("piyasa_yonu") == "Yatay"],
        "F&G — Aşırı Korku":      [s for s in kayitlar if (s.get("fg_deger") or 100) <= 24],
        "F&G — Korku":             [s for s in kayitlar if 25 <= (s.get("fg_deger") or -1) <= 44],
        "F&G — Nötr":              [s for s in kayitlar if 45 <= (s.get("fg_deger") or -1) <= 55],
        "F&G — Açgözlülük":       [s for s in kayitlar if 56 <= (s.get("fg_deger") or -1) <= 75],
        "F&G — Aşırı Açgözlülük": [s for s in kayitlar if (s.get("fg_deger") or -1) >= 76],
        "Funding — Pozitif":       [s for s in kayitlar if s.get("funding_yonu") == "Pozitif"],
        "Funding — Negatif":       [s for s in kayitlar if s.get("funding_yonu") == "Negatif"],
        "Hacim — Ortalama Üstü":  [s for s in kayitlar if s.get("hacim_durumu") == "Ortalama Üstü"],
        "Hacim — Ortalama Altı":  [s for s in kayitlar if s.get("hacim_durumu") == "Ortalama Altı"],

    }
    kosul_sonuc = {k: satir(v) for k, v in kosullar.items()}

    # 3. TP seviyesi dağılımı
    tp_seviye = {}
    for lbl, key in [("TP1","tp1_ok"),("TP2","tp2_ok"),("TP3+",None)]:
        if key:
            say = sum(1 for s in kayitlar if s.get(key) is True)
        else:
            say = sum(1 for s in kayitlar if any(s.get(f"tp{i}_ok") is True for i in [3,4,5]))
        tp_seviye[lbl] = say
    toplam_tp = sum(1 for s in kayitlar if tp_mi(s))
    for lbl in tp_seviye:
        pct = f"%{round(tp_seviye[lbl]/toplam_tp*100,1)}" if toplam_tp > 0 else "—"
        tp_seviye[lbl] = (tp_seviye[lbl], pct)
    en_cok = max(tp_seviye, key=lambda x: tp_seviye[x][0]) if toplam_tp > 0 else "—"

    # 4. Coin bazlı
    semboller = list({s.get("symbol","").replace("USDT","") for s in kayitlar if s.get("symbol")})
    coin_sonuc = {}
    for sym in sorted(semboller):
        sub = [s for s in kayitlar if s.get("symbol","").replace("USDT","") == sym]
        coin_sonuc[sym] = satir(sub)

    # 5. TF bazlı
    tf_map = {"1":"1DK","3":"3DK","5":"5DK","15":"15DK","60":"1SA","240":"4SA","1440":"1G","D":"1G"}
    tf_sonuc = {}
    for tf_key, tf_lbl in [("1","1DK"),("5","5DK"),("15","15DK"),("60","1SA"),("240","4SA"),("1440","1G")]:
        sub = [s for s in kayitlar if str(s.get("timeframe","")) == tf_key]
        if sub:
            tf_sonuc[tf_lbl] = satir(sub)

    # 6. Kombinasyonlar
    from itertools import product as iterproduct
    kombinasyonlar = {}
    # Sinyal tipi + piyasa yönü
    for tip, yon in iterproduct(tipler, ["Yükseliş","Düşüş","Yatay"]):
        sub = [s for s in kayitlar if s.get("sinyal_tipi")==tip and s.get("piyasa_yonu")==yon]
        if sub:
            kombinasyonlar[f"{tip} + {yon}"] = satir(sub)

    # Coin + TF
    for sym in sorted(semboller):
        for tf_lbl in tf_sonuc:
            tf_key = [k for k,v in tf_map.items() if v==tf_lbl]
            sub = [s for s in kayitlar
                   if s.get("symbol","").replace("USDT","")==sym
                   and str(s.get("timeframe","")) in tf_key]
            if sub:
                kombinasyonlar[f"{sym} + {tf_lbl}"] = satir(sub)

    # 7. Öneri: min 20 sinyal, en yüksek TP oranlı kombinasyonlar
    MIN_SINYAL = 20
    oneriler = [
        (k, v) for k, v in kombinasyonlar.items()
        if v[0] >= MIN_SINYAL
    ]
    oneriler.sort(key=lambda x: x[1][1], reverse=True)
    oneriler = oneriler[:5]

    return {
        "sinyal_tipi": sinyal_tipi_sonuc,
        "kosul": kosul_sonuc,
        "tp_seviye": tp_seviye,
        "en_cok_tp": en_cok,
        "coin": coin_sonuc,
        "tf": tf_sonuc,
        "kombinasyon": kombinasyonlar,
        "oneri": oneriler,
        "toplam": len(kayitlar),
        "toplam_tp": toplam_tp,
    }


def _tp_kosul_yorum_uret(veri):
    """Veriden otomatik madde madde Türkçe yorum üret."""
    MIN_GENEL = 5    # Sinyal tipi, coin, TF için
    MIN_KOMB  = 20   # Kombinasyon önerisi için
    maddeler = []

    def oran_val(v):
        try:
            return float(str(v[3]).replace("%","")) if "%" in str(v[3]) else -1
        except Exception:
            return -1

    # 1. Sinyal tipi
    tip_veri = {k: v for k, v in veri["sinyal_tipi"].items() if v[0] >= MIN_GENEL and oran_val(v) >= 0}
    if tip_veri:
        en_iyi = max(tip_veri.items(), key=lambda x: oran_val(x[1]))
        en_kotu = min(tip_veri.items(), key=lambda x: oran_val(x[1]))
        maddeler.append(f"🏆 En başarılı sinyal tipi: <b>{en_iyi[0]}</b> → <b>{en_iyi[1][3]}</b> TP ({en_iyi[1][0]} sinyal)")
        if en_kotu[0] != en_iyi[0]:
            maddeler.append(f"📉 En düşük sinyal tipi: <b>{en_kotu[0]}</b> → <b>{en_kotu[1][3]}</b> TP ({en_kotu[1][0]} sinyal)")
    else:
        maddeler.append("⏳ Sinyal tipi: Veri birikmesi devam ediyor")

    # 2. Piyasa koşulları — seans hariç, gerçek piyasa verisi olanlar
    kosul_veri = {k: v for k, v in veri["kosul"].items()
                  if v[0] >= MIN_GENEL and oran_val(v) >= 0 and not any(x in k for x in ["Seans"])}
    if kosul_veri:
        en_iyi_k = max(kosul_veri.items(), key=lambda x: oran_val(x[1]))
        en_kotu_k = min(kosul_veri.items(), key=lambda x: oran_val(x[1]))
        maddeler.append(f"✅ En başarılı piyasa koşulu: <b>{en_iyi_k[0]}</b> → <b>{en_iyi_k[1][3]}</b> TP ({en_iyi_k[1][0]} sinyal)")
        if en_kotu_k[0] != en_iyi_k[0]:
            maddeler.append(f"❌ En düşük piyasa koşulu: <b>{en_kotu_k[0]}</b> → <b>{en_kotu_k[1][3]}</b> TP ({en_kotu_k[1][0]} sinyal)")
    else:
        maddeler.append("⏳ Piyasa koşulları (F&G, Funding, Hacim): Veri birikmesi devam ediyor")

    # 3. Coin
    coin_veri = {k: v for k, v in veri["coin"].items() if v[0] >= MIN_GENEL and oran_val(v) >= 0}
    if coin_veri:
        en_iyi_c = max(coin_veri.items(), key=lambda x: oran_val(x[1]))
        en_kotu_c = min(coin_veri.items(), key=lambda x: oran_val(x[1]))
        maddeler.append(f"🥇 En başarılı coin: <b>{en_iyi_c[0]}</b> → <b>{en_iyi_c[1][3]}</b> TP ({en_iyi_c[1][0]} sinyal)")
        maddeler.append(f"🔴 En düşük performanslı coin: <b>{en_kotu_c[0]}</b> → <b>{en_kotu_c[1][3]}</b> TP ({en_kotu_c[1][0]} sinyal)")

    # 5. Zaman dilimi
    tf_veri = {k: v for k, v in veri["tf"].items() if v[0] >= MIN_GENEL and oran_val(v) >= 0}
    if tf_veri:
        en_iyi_tf = max(tf_veri.items(), key=lambda x: oran_val(x[1]))
        maddeler.append(f"⏱ En güvenilir zaman dilimi: <b>{en_iyi_tf[0]}</b> → <b>{en_iyi_tf[1][3]}</b> TP ({en_iyi_tf[1][0]} sinyal)")
        for tf, tv in tf_veri.items():
            if oran_val(tv) < 25:
                maddeler.append(f"⚠️ Dikkat: <b>{tf}</b> → <b>{tv[3]}</b> TP — düşük performans, dikkatli olunmalı")

    # 6. Kombinasyon — min 20 sinyal
    komb_veri = {k: v for k, v in veri["kombinasyon"].items() if v[0] >= MIN_KOMB and oran_val(v) >= 0}
    if komb_veri:
        en_iyi_komb = max(komb_veri.items(), key=lambda x: oran_val(x[1]))
        maddeler.append(f"💡 En güvenilir kombinasyon: <b>{en_iyi_komb[0]}</b> → <b>{en_iyi_komb[1][3]}</b> TP ({en_iyi_komb[1][0]} sinyal)")
    else:
        maddeler.append("⏳ Kombinasyon önerisi: Min. 20 sinyal bekleniyor")

    return maddeler


def _tp_kosul_rapor_gorsel(veri=None, snapshot=None):
    """TP koşul raporunu 4 ayrı PNG olarak üretir — liste döner."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        from datetime import datetime as dt_cls
        import io
        import textwrap
    except ImportError:
        return []

    if veri is None:
        veri = _tp_kosul_rapor_hesapla(snapshot=snapshot)

    BG       = "#13151A"
    ROW_ODD  = "#1A1D24"
    ROW_EVEN = "#16181F"
    TEXT_W   = "#E8E8E6"
    TEXT_G   = "#6B6F7A"
    GREEN    = "#4CAF50"
    RED      = "#F44336"
    AMBER    = "#FFC107"
    BLUE     = "#4A90D9"
    GREEN2   = "#2E9E4F"
    AMBER2   = "#D4A017"
    PURPLE   = "#9C7FE0"
    TEAL     = "#26C6A0"
    CORAL    = "#E07060"
    PINK     = "#D46B8A"
    YORUM_BG = "#1E1A2E"
    YORUM_C  = "#C8B8F0"

    simdi = dt_cls.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    ozet  = f"Toplam: {veri['toplam']} sinyal  |  TP: {veri['toplam_tp']}  |  {simdi}"
    yorum_maddeler = _tp_kosul_yorum_uret(veri)

    def oran_renk(oran_str):
        try:
            val = float(str(oran_str).replace("%",""))
            if val >= 50: return GREEN
            elif val >= 35: return AMBER
            else: return RED
        except Exception:
            return TEXT_G

    def toplam_satir_yap(satirlar, sutunlar):
        """Tablonun alt toplamını hesapla — Toplam/TP/Devam/SL/Oran yapısına göre."""
        try:
            n = len(sutunlar)
            toplam_sayilar = [0] * n
            for satir in satirlar:
                for ci in range(1, n):
                    try:
                        v = str(satir[ci]).replace("%","")
                        if v.lstrip("-").replace(".","").isdigit():
                            toplam_sayilar[ci] += float(v)
                    except Exception:
                        pass
            t_row = ["Toplam"]
            for ci in range(1, n):
                if ci == n-1:  # Oran sütunu — TP/Toplam
                    try:
                        tp_idx  = sutunlar.index("TP")     if "TP"     in sutunlar else 2
                        top_idx = sutunlar.index("Toplam") if "Toplam" in sutunlar else 1
                        tp_t  = toplam_sayilar[tp_idx]
                        top_t = toplam_sayilar[top_idx]
                        oran  = f"%{round(tp_t/top_t*100,1)}" if top_t > 0 else "—"
                        t_row.append(oran)
                    except Exception:
                        t_row.append("—")
                else:
                    v = toplam_sayilar[ci]
                    vi = int(v) if v == int(v) else round(v, 1)
                    t_row.append(str(vi) if vi > 0 else "—")
            return tuple(t_row)
        except Exception:
            return None

    def gorsel_yap(basliklar_renkler_satirlar_sutunlar, baslik_ana, alt_yazi="",
                   toplam_satirlari=None, yorum_metni=None):
        SATIR_H   = 0.46
        TOPLAM_H  = 0.50
        FONT_SATIR  = 13
        FONT_SUTUN  = 11
        FONT_BASLIK = 13
        SOL = 0.15
        SAG = 13.85
        GENISLIK = SAG - SOL

        # Toplam yükseklik
        n_satirlar = sum(len(s) + 2.5 for _,_,s,_ in basliklar_renkler_satirlar_sutunlar)
        # Toplam satır ekleri
        n_toplam = len(toplam_satirlari) if toplam_satirlari else 0
        # Yorum yüksekliği
        yorum_satirlari = textwrap.wrap(yorum_metni, width=110) if yorum_metni else []
        yorum_h = len(yorum_satirlari) * 0.38 + 0.6 if yorum_satirlari else 0

        fig_h = max(4.0, 2.8 + n_satirlar * SATIR_H + n_toplam * TOPLAM_H + yorum_h)

        fig, ax = plt.subplots(figsize=(14, fig_h))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ax.set_xlim(0, 14)
        ax.set_ylim(0, fig_h)
        ax.axis("off")

        ax.text(7, fig_h - 0.45, baslik_ana, ha="center", fontsize=18,
                fontweight="bold", color=TEXT_W)
        ax.text(7, fig_h - 0.90, ozet, ha="center", fontsize=11, color=TEXT_G)
        if alt_yazi:
            ax.text(7, fig_h - 1.20, alt_yazi, ha="center", fontsize=10, color=TEXT_G)

        y = fig_h - 1.55

        tablo_idx = 0
        for (bolum_baslik, renk, satirlar, sutunlar) in basliklar_renkler_satirlar_sutunlar:
            ax.add_patch(FancyBboxPatch((SOL, y - 0.38), GENISLIK, 0.40,
                                        boxstyle="round,pad=0.02", linewidth=0,
                                        facecolor=renk+"44", zorder=1))
            ax.text(SOL + 0.2, y - 0.17, bolum_baslik, va="center",
                    fontsize=FONT_BASLIK, fontweight="bold", color=renk)
            y -= 0.38

            col_w = GENISLIK / len(sutunlar)
            y -= 0.32
            for ci, sut in enumerate(sutunlar):
                ax.text(SOL + ci*col_w + (col_w*0.08 if ci==0 else col_w/2),
                        y, sut, va="center",
                        ha="left" if ci==0 else "center",
                        fontsize=FONT_SUTUN, color=TEXT_G, fontweight="bold")
            y -= 0.10

            for ri, satir in enumerate(satirlar):
                bg = ROW_ODD if ri % 2 == 0 else ROW_EVEN
                ax.add_patch(FancyBboxPatch((SOL, y - SATIR_H + 0.05), GENISLIK, SATIR_H - 0.07,
                                            boxstyle="round,pad=0.01", linewidth=0,
                                            facecolor=bg, zorder=0))
                for ci, hucre in enumerate(satir):
                    renk_h = TEXT_W
                    if ci > 0 and isinstance(hucre, str) and "%" in hucre:
                        renk_h = oran_renk(hucre)
                    is_oran = (ci == len(satir) - 1)
                    ax.text(SOL + ci*col_w + (col_w*0.08 if ci==0 else col_w/2),
                            y - SATIR_H/2, str(hucre), va="center",
                            ha="left" if ci==0 else "center",
                            fontsize=FONT_SATIR, color=renk_h,
                            fontweight="bold" if is_oran else "normal")
                y -= SATIR_H

            # Toplam satırı
            if toplam_satirlari and tablo_idx < len(toplam_satirlari) and toplam_satirlari[tablo_idx]:
                t_row = toplam_satirlari[tablo_idx]
                ax.add_patch(FancyBboxPatch((SOL, y - TOPLAM_H + 0.05), GENISLIK, TOPLAM_H - 0.07,
                                            boxstyle="round,pad=0.01", linewidth=0,
                                            facecolor=renk+"22", zorder=0))
                for ci, hucre in enumerate(t_row):
                    renk_h = TEXT_W
                    if ci > 0 and isinstance(hucre, str) and "%" in hucre:
                        renk_h = oran_renk(hucre)
                    ax.text(SOL + ci*col_w + (col_w*0.08 if ci==0 else col_w/2),
                            y - TOPLAM_H/2, str(hucre), va="center",
                            ha="left" if ci==0 else "center",
                            fontsize=13, color=renk_h, fontweight="bold")
                y -= TOPLAM_H

            tablo_idx += 1
            y -= 0.30

        # Yorum bölümü
        if yorum_satirlari:
            yorum_blok_h = len(yorum_satirlari) * 0.38 + 0.4
            ax.add_patch(FancyBboxPatch((SOL, y - yorum_blok_h), GENISLIK, yorum_blok_h,
                                        boxstyle="round,pad=0.04", linewidth=0,
                                        facecolor=YORUM_BG, zorder=0))
            ax.text(SOL + 0.2, y - 0.25, "Otomatik Yorum", va="center",
                    fontsize=12, fontweight="bold", color=YORUM_C)
            for i, satir in enumerate(yorum_satirlari):
                ax.text(SOL + 0.2, y - 0.55 - i*0.38, satir, va="center",
                        fontsize=11, color=TEXT_W)

        plt.tight_layout(pad=0.3)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, facecolor=BG, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf

    gorseller = []

    # ── GÖRSEL 1: Sinyal Tipi ──
    satirlar1 = sorted([(t,)+v for t,v in veri["sinyal_tipi"].items()],
                       key=lambda x: float(str(x[4]).replace("%","")) if "%" in str(x[4]) else -1,
                       reverse=True)
    t1 = toplam_satir_yap(satirlar1, ["Sinyal Tipi","Toplam","TP","Devam","SL","Oran"])
    g1 = gorsel_yap(
        [("1. Sinyal Tipi — Karşılaştırma", BLUE, satirlar1,
          ["Sinyal Tipi","Toplam","TP","Devam","SL","Oran"])],
        "TP Koşul Raporu — 1/4",
        toplam_satirlari=[t1]
    )
    gorseller.append((g1, "TP Koşul Raporu 1/4 — Sinyal Tipi"))

    # ── GÖRSEL 2: Piyasa Koşulları ──
    satirlar2 = sorted([(t,)+v for t,v in veri["kosul"].items()],
                       key=lambda x: float(str(x[4]).replace("%","")) if "%" in str(x[4]) else -1,
                       reverse=True)
    g2 = gorsel_yap(
        [("2. Piyasa Koşulları — Karşılaştırma", GREEN2, satirlar2,
          ["Koşul","Toplam","TP","Devam","SL","Oran"])],
        "TP Koşul Raporu — 2/4",
        toplam_satirlari=[None]
    )
    gorseller.append((g2, "TP Koşul Raporu 2/4 — Piyasa Koşulları"))

    # ── GÖRSEL 3: TP Seviyesi + Coin + TF ──
    satirlar3 = [(lbl, v[0], v[1], "", "") for lbl,v in veri["tp_seviye"].items()]
    satirlar3.append(("En çok ulaşılan", veri["en_cok_tp"], "", "", ""))
    satirlar4 = sorted([(t,)+v for t,v in veri["coin"].items()],
                       key=lambda x: float(str(x[4]).replace("%","")) if "%" in str(x[4]) else -1,
                       reverse=True)
    satirlar5 = [(t,)+v for t,v in veri["tf"].items()]
    t4 = toplam_satir_yap(satirlar4, ["Coin","Toplam","TP","Devam","SL","Oran"])
    t5 = toplam_satir_yap(satirlar5, ["TF","Toplam","TP","Devam","SL","Oran"])
    g3 = gorsel_yap(
        [
            ("3. TP Seviyesi — Dağılımı", AMBER2, satirlar3,
             ["Seviye","Toplam TP","Oran","",""]),
            ("4. Coin Bazlı — Karşılaştırma", PURPLE, satirlar4,
             ["Coin","Toplam","TP","Devam","SL","Oran"]),
            ("5. Zaman Dilimi — Karşılaştırma", TEAL, satirlar5,
             ["TF","Toplam","TP","Devam","SL","Oran"]),
        ],
        "TP Koşul Raporu — 3/4",
        toplam_satirlari=[None, t4, t5]
    )
    gorseller.append((g3, "TP Koşul Raporu 3/4 — TP Seviyesi + Coin + TF"))

    # ── GÖRSEL 4: Kombinasyonlar + Öneri ──
    komb_sirali = sorted(veri["kombinasyon"].items(), key=lambda x: x[1][1], reverse=True)[:15]
    satirlar6 = [(k,)+v for k,v in komb_sirali]
    t6 = toplam_satir_yap(satirlar6, ["Kombinasyon","Toplam","TP","Devam","SL","Oran"])
    if veri["oneri"]:
        satirlar7 = [(k,)+v for k,v in veri["oneri"]]
    else:
        satirlar7 = [("Veri birikmesi bekleniyor (min. 5 sinyal)", "—", "—", "—", "—")]
    t7 = toplam_satir_yap(satirlar7, ["Kombinasyon","Toplam","TP","Devam","SL","Oran"])
    g4 = gorsel_yap(
        [
            ("6. En Kârlı Kombinasyonlar", CORAL, satirlar6,
             ["Kombinasyon","Toplam","TP","Devam","SL","Oran"]),
            ("7. Öneri Mekanizması — En Güvenilir Koşullar", PINK, satirlar7,
             ["Kombinasyon","Toplam","TP","Devam","SL","Oran"]),
        ],
        "TP Koşul Raporu — 4/4",
        alt_yazi="Devam = TP/SL bekleniyor  |  Öneri: min. 20 sinyal  |  %50+ Önerilen  |  %35- Kaçınılan",
        toplam_satirlari=[t6, t7]
    )
    gorseller.append((g4, "TP Koşul Raporu 4/4 — Kombinasyonlar + Öneri"))

    return gorseller



def _tp_kosul_rapor_zamanlayici():
    """Her saatin :30'unda TP koşul raporunu TOPIC_RAPOR'a gönder."""
    import datetime as dt_mod
    print("[TP_KOSUL] Zamanlayici basladi.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()
            dk = simdi.minute
            if dk < 30:
                sonraki = simdi.replace(minute=30, second=0, microsecond=0)
            else:
                sonraki = (simdi.replace(minute=0, second=0, microsecond=0)
                           + dt_mod.timedelta(hours=1))
            bekle = (sonraki - simdi).total_seconds()
            print(f"[TP_KOSUL] Sonraki: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(bekle)
            with gunluk_kilit:
                snapshot = list(gunluk_sinyaller)
            veri      = _tp_kosul_rapor_hesapla(snapshot=snapshot)
            gorseller = _tp_kosul_rapor_gorsel(veri=veri)
            if gorseller:
                for img, caption in gorseller:
                    _topic_foto_gonder_filigranli(TOPIC_RAPOR, img, caption)
                    time.sleep(2)
                # Yorum metni en sona
                maddeler = _tp_kosul_yorum_uret(veri)
                if maddeler:
                    yorum_txt = "📊 <b>Otomatik Yorum</b>\n\n" + "\n".join(f"• {m}" for m in maddeler)
                    _telegram_topic_mesaj_gonder(TOPIC_RAPOR, yorum_txt)
            else:
                _telegram_topic_mesaj_gonder(TOPIC_RAPOR, "⚠️ TP Koşul Raporu: Yeterli veri yok.")
            time.sleep(10)
        except Exception as e:
            print(f"[TP_KOSUL] Hata: {e}")
            time.sleep(60)


def _istatistik_zamanlayici():
    """Her 30 dakikada bir istatistik + günlük rapor görseli gönder."""
    import datetime as dt_mod
    print("[ISTATISTIK] Zamanlayici basladi.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()
            # Bir sonraki :00 veya :30'a hesapla
            dk = simdi.minute
            if dk < 30:
                sonraki = simdi.replace(minute=30, second=0, microsecond=0)
            else:
                sonraki = (simdi.replace(minute=0, second=0, microsecond=0)
                           + dt_mod.timedelta(hours=1))
            bekle = (sonraki - simdi).total_seconds()
            print(f"[ISTATISTIK] Sonraki: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(bekle)
            bugun = gun_str()
            # Aynı anda snapshot al — ikisi de aynı veriyi kullansın
            with gunluk_kilit:
                snapshot = list(gunluk_sinyaller)
            # 1) İstatistik metni
            _telegram_topic_mesaj_gonder(TOPIC_RAPOR, istatistik_mesaji(snapshot=snapshot))
            # 2) Koin başarı sıralaması + top3 güncelle
            koin_metni = koin_sirala_metni(snapshot=snapshot)
            if koin_metni:
                _telegram_topic_mesaj_gonder(TOPIC_RAPOR, koin_metni)
            # 3) Günlük rapor görseli
            img = rapor_gorsel(bugun, snapshot=snapshot)
            if img:
                _topic_foto_gonder_filigranli(TOPIC_RAPOR, img, f"Günlük Rapor — {bugun}\n/rapor")
            time.sleep(10)
        except Exception as e:
            print(f"[ISTATISTIK] Hata: {e}")
            time.sleep(60)


def _trend_btc_dominans():
    """BTC dominansını MEXC ticker'dan hesapla."""
    try:
        r = requests.get("https://contract.mexc.com/api/v1/contract/ticker", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and data.get("data"):
                tickers      = data["data"]
                usdt_tickers = [t for t in tickers if str(t.get("symbol","")).endswith("_USDT")]
                toplam_hacim = sum(float(t.get("amount24", 0) or 0) for t in usdt_tickers)
                if toplam_hacim > 0:
                    btc_hacim = next((float(t.get("amount24",0) or 0) for t in usdt_tickers if t.get("symbol") == "BTC_USDT"), 0)
                    eth_hacim = next((float(t.get("amount24",0) or 0) for t in usdt_tickers if t.get("symbol") == "ETH_USDT"), 0)
                    btc_dom   = round(btc_hacim / toplam_hacim * 100, 2)
                    eth_dom   = round(eth_hacim / toplam_hacim * 100, 2)
                    return btc_dom, eth_dom, toplam_hacim, 0
    except Exception as e:
        print(f"[TREND] dominans hata: {e}")
    return None, None, None, None


def _ls_veri_cek(symbol="BTCUSDT", limit=24):
    """
    Binance Futures'tan Long/Short oranı çek.
    Genel hesap oranı + Top Trader oranı (balina vs KY ayrımı)
    Her biri: [{longAccount, shortAccount, longShortRatio, timestamp}, ...]
    """
    sonuc = {"genel": [], "balina": []}
    try:
        # Genel L/S — tüm hesaplar (KY ağırlıklı)
        r = requests.get(
            "https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
            params={"symbol": symbol, "period": "1h", "limit": limit},
            timeout=8, proxies=BINANCE_PROXY
        )
        if r.status_code == 200:
            sonuc["genel"] = r.json()
    except Exception as e:
        print(f"[LS] genel hata: {e}")

    try:
        # Top Trader L/S — büyük hesaplar (balina)
        r = requests.get(
            "https://fapi.binance.com/futures/data/topLongShortAccountRatio",
            params={"symbol": symbol, "period": "1h", "limit": limit},
            timeout=8, proxies=BINANCE_PROXY
        )
        if r.status_code == 200:
            sonuc["balina"] = r.json()
    except Exception as e:
        print(f"[LS] balina hata: {e}")

    return sonuc


def _ls_gorsel(btc_ls, eth_ls, zaman_str):
    """
    Hyblock tarzı L/S grafik görseli üret.
    Üst: bar chart (net fark)
    Alt: çizgi grafik (balina % / KY %)
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        from matplotlib.patches import FancyBboxPatch
        import io
        import numpy as np
    except ImportError:
        return None

    BG      = "#0A0E1A"
    CARD_BG = "#111827"
    BORDER  = "#1E2D4A"
    TEXT_W  = "#FFFFFF"
    HDR_COL = "#E8E8E6"

    fig = plt.figure(figsize=(14, 8), facecolor=BG)
    fig.patch.set_facecolor(BG)

    # 2 satır, 2 sütun (BTC sol, ETH sağ)
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.3,
                           top=0.92, bottom=0.06, left=0.05, right=0.97)

    fig.text(0.5, 0.96, "BEN KÜL YUTMAM — Long/Short Oran Analizi",
             ha="center", va="top", fontsize=14, fontweight="bold", color=TEXT_W)
    fig.text(0.5, 0.93, f"{zaman_str}  |  Binance Futures  |  1 Saatlik  |  Son 24 Saat",
             ha="center", va="top", fontsize=9, color=HDR_COL)

    for col_idx, (sym, ls_data) in enumerate([("BTC", btc_ls), ("ETH", eth_ls)]):
        genel  = ls_data.get("genel",  [])
        balina = ls_data.get("balina", [])

        if not genel:
            continue

        # Binance API en yeni veriyi sona koyar (timestamp artan sıra)
        # Tersine çevirme YAPMA — zaten kronolojik sırada
        genel  = list(genel)   # eski → yeni (soldan sağa doğru zaman)
        balina = list(balina) if balina else []

        timestamps   = [d["timestamp"] for d in genel]
        long_genel   = [float(d["longAccount"])  * 100 for d in genel]
        short_genel  = [float(d["shortAccount"]) * 100 for d in genel]
        net_fark     = [l - s for l, s in zip(long_genel, short_genel)]

        # Balina uzunluğunu genel ile eşitle
        long_balina  = [float(d["longAccount"])  * 100 for d in balina] if balina else []
        short_balina = [float(d["shortAccount"]) * 100 for d in balina] if balina else []
        # Boyut farkını düzelt
        if long_balina and len(long_balina) != len(long_genel):
            min_len = min(len(long_genel), len(long_balina))
            long_genel   = long_genel[-min_len:]
            short_genel  = short_genel[-min_len:]
            net_fark     = net_fark[-min_len:]
            timestamps   = timestamps[-min_len:]
            long_balina  = long_balina[-min_len:]
            short_balina = short_balina[-min_len:]

        n = len(timestamps)
        x = list(range(n))

        # X ekseni etiketleri — timestamp'ten gerçek saat
        import datetime as dt_ls
        def ts_to_hm(ts_ms):
            try:
                _dt = datetime.fromtimestamp(ts_ms / 1000, tz=TR_TZ) if TR_TZ else dt_ls.datetime.utcfromtimestamp(ts_ms / 1000)
                return _dt.strftime("%H:%M")
            except:
                return ""

        # ── Üst: Bar chart (net fark) ──
        ax_bar = fig.add_subplot(gs[0, col_idx])
        ax_bar.set_facecolor(CARD_BG)
        ax_bar.spines[:].set_color(BORDER)
        ax_bar.tick_params(colors=HDR_COL, labelsize=7)

        colors_bar = ["#4CAF50" if v >= 0 else "#F44336" for v in net_fark]
        ax_bar.bar(x, net_fark, color=colors_bar, width=0.8)
        ax_bar.axhline(0, color=HDR_COL, linewidth=0.5, alpha=0.5)

        son_fark = net_fark[-1] if net_fark else 0
        fark_col = "#4CAF50" if son_fark >= 0 else "#F44336"
        ax_bar.set_title(f"{sym} — Net L/S Fark: {son_fark:+.2f}",
                         color=TEXT_W, fontsize=10, fontweight="bold", pad=4)
        ax_bar.set_xticks([])
        ax_bar.yaxis.label.set_color(HDR_COL)
        # Son bar üstüne değer etiketi
        ax_bar.annotate(f"{son_fark:+.3f}", xy=(x[-1], son_fark),
                        xytext=(5, 5), textcoords="offset points",
                        color=fark_col, fontsize=8, fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor=CARD_BG, edgecolor=fark_col))

        # ── Alt: Çizgi grafik (Balina vs KY) ──
        ax_line = fig.add_subplot(gs[1:, col_idx])
        ax_line.set_facecolor(CARD_BG)
        ax_line.spines[:].set_color(BORDER)
        ax_line.tick_params(colors=HDR_COL, labelsize=7)

        # KY (genel hesap)
        ax_line.plot(x, long_genel,  color="#4CAF50", linewidth=1.5,
                     label=f"KY Long %{long_genel[-1]:.2f}")
        ax_line.plot(x, short_genel, color="#F44336", linewidth=1.5,
                     label=f"KY Short %{short_genel[-1]:.2f}")

        # Balina (top trader) — kesikli
        if long_balina:
            ax_line.plot(x, long_balina,  color="#81C784", linewidth=1.2, linestyle="--",
                         label=f"Balina Long %{long_balina[-1]:.2f}")
            ax_line.plot(x, short_balina, color="#E57373", linewidth=1.2, linestyle="--",
                         label=f"Balina Short %{short_balina[-1]:.2f}")

        ax_line.axhline(50, color=HDR_COL, linewidth=0.4, alpha=0.4, linestyle=":")

        # Y ekseni dinamik — veri aralığına göre ayarla
        tum_degerler = long_genel + short_genel + (long_balina or []) + (short_balina or [])
        y_min = max(0,  min(tum_degerler) - 3)
        y_max = min(100, max(tum_degerler) + 3)
        ax_line.set_ylim(y_min, y_max)

        # Son değer etiketleri — satırların birbirine yapışmaması için offset
        long_son  = long_genel[-1]
        short_son = short_genel[-1]
        uzaklik   = abs(long_son - short_son)
        y_ofset   = 1.5 if uzaklik < 3 else 0

        ax_line.annotate(f"%{long_son:.2f}", xy=(x[-1], long_son),
                         xytext=(4, y_ofset), textcoords="offset points",
                         color="#4CAF50", fontsize=8, fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.2", facecolor=CARD_BG, edgecolor="#4CAF50"))
        ax_line.annotate(f"%{short_son:.2f}", xy=(x[-1], short_son),
                         xytext=(4, -y_ofset), textcoords="offset points",
                         color="#F44336", fontsize=8, fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.2", facecolor=CARD_BG, edgecolor="#F44336"))

        # X ekseni — her 4 saatte bir gerçek saat etiketi
        tick_idx = list(range(0, n, max(1, n // 6)))
        if (n - 1) not in tick_idx:
            tick_idx.append(n - 1)
        tick_lbl = [ts_to_hm(timestamps[ti]) for ti in tick_idx]
        ax_line.set_xticks(tick_idx)
        ax_line.set_xticklabels(tick_lbl, rotation=0, ha="center", fontsize=7, color=HDR_COL)

        legend = ax_line.legend(loc="lower left", fontsize=7,
                                facecolor=CARD_BG, edgecolor=BORDER,
                                labelcolor=HDR_COL)

    # Sağ taraftaki etiketlerin kırpılmaması için sağ boşluk ayarı
    plt.subplots_adjust(right=0.93)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150,
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _ls_yorum(btc_ls, eth_ls):
    """BTC ve ETH L/S verilerinden otomatik yorum üret."""
    satirlar = ["📊 <b>Long/Short Oran Yorumu</b>\n"]

    for sym, ls_data in [("BTC", btc_ls), ("ETH", eth_ls)]:
        genel  = ls_data.get("genel",  [])
        balina = ls_data.get("balina", [])
        if not genel:
            continue

        ky_long    = float(genel[-1]["longAccount"])  * 100
        ky_short   = float(genel[-1]["shortAccount"]) * 100
        net_fark   = ky_long - ky_short

        bal_long  = float(balina[-1]["longAccount"])  * 100 if balina else None
        bal_short = float(balina[-1]["shortAccount"]) * 100 if balina else None

        satirlar.append(f"<b>{'₿' if sym=='BTC' else 'Ξ'} {sym}USDT</b>")
        satirlar.append(f"KY Long: <b>%{ky_long:.1f}</b>  |  KY Short: <b>%{ky_short:.1f}</b>")

        if bal_long:
            satirlar.append(f"Balina Long: <b>%{bal_long:.1f}</b>  |  Balina Short: <b>%{bal_short:.1f}</b>")

        # Trend değişimi — son 6 saat (önce hesapla, yorumda kullan)
        degisim = 0
        if len(genel) >= 6:
            eski_long = float(genel[-6]["longAccount"]) * 100
            degisim   = ky_long - eski_long

        # Balina vs KY çelişkisi — en önemli sinyal
        if bal_long and bal_short:
            bal_net = bal_long - bal_short
            ky_net  = ky_long  - ky_short

            if bal_short > 55 and ky_long > 60:
                satirlar.append("⚠️ <b>Dikkat:</b> Balina SHORT, KY LONG — Düşüş baskısı olabilir")
            elif bal_long > 55 and ky_short > 55:
                satirlar.append("⚠️ <b>Dikkat:</b> Balina LONG, KY SHORT — Squeeze potansiyeli yüksek")
            bal_yon_long = bal_long > bal_short
            ky_yon_long  = ky_long  > ky_short
            if bal_yon_long == ky_yon_long:
                satirlar.append("✅ Balina ve KY aynı yönde — Trend teyit ediliyor")
            else:
                satirlar.append("🔶 Balina ve KY farklı yönde — Dikkatli ol")

        # Ana yorum: mutlak oran + değişim yönü birlikte değerlendir
        if degisim > 2 and ky_long > 55:
            yorum = "🟢 Long oranı artıyor — Yükseliş baskısı güçleniyor"
        elif degisim < -2 and ky_long > 55:
            yorum = "🔴 Long oranı azalıyor — Pozisyon kapama var, dikkat"
        elif degisim < -2 and ky_short > 50:
            yorum = "🔴 Short baskısı artıyor — Düşüş eğilimi güçleniyor"
        elif degisim > 2 and ky_short > 50:
            yorum = "🟡 Long artıyor ama short ağırlıklı — Squeeze riski"
        elif ky_short > 65:
            yorum = "🔴 KY ağırlıklı SHORT — Short sıkışması riski var"
        elif ky_long > 70:
            yorum = "🟡 KY çok fazla LONG — Aşırı pozisyonlanma, dikkatli ol"
        elif ky_long > 60:
            yorum = "🟢 KY ağırlıklı LONG — Yükseliş beklentisi var"
        else:
            yorum = "⚪ Dengeli pozisyonlanma — Yön belirsiz"
        satirlar.append(yorum)

        # Değişim notu
        if abs(degisim) > 2:
            yon = "↑ artıyor" if degisim > 0 else "↓ azalıyor"
            satirlar.append(f"📉 Son 6s Long oranı {yon} ({degisim:+.1f}%)")

        satirlar.append("")

    satirlar.append(f"<i>Kaynak: Binance Futures  |  1 Saatlik</i>")
    return "\n".join(satirlar)


def _ls_gonder(chat_id=None):
    """L/S grafiği + yorum gönder. (v282 — direkt Binance'den çeker)"""
    print("[LS] Zamanlayici tetiklendi — Binance'den L/S verisi çekiliyor.")
    try:
        from datetime import datetime as _dt
        # Binance L/S endpoint
        btc_ls = {"genel": [], "balina": []}
        eth_ls = {"genel": [], "balina": []}

        for sym, hedef in [("BTCUSDT", btc_ls), ("ETHUSDT", eth_ls)]:
            # Genel Long/Short oranı
            try:
                r_genel = requests.get(
                    "https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
                    params={"symbol": sym, "period": "1h", "limit": 24},
                    timeout=8, proxies=BINANCE_PROXY
                )
                if r_genel.status_code == 200:
                    hedef["genel"] = r_genel.json()
            except Exception as e:
                print(f"[LS] {sym} genel L/S hata: {e}")

            # Balina (Büyük hesaplar) L/S oranı
            try:
                r_balina = requests.get(
                    "https://fapi.binance.com/futures/data/topLongShortAccountRatio",
                    params={"symbol": sym, "period": "1h", "limit": 24},
                    timeout=8, proxies=BINANCE_PROXY
                )
                if r_balina.status_code == 200:
                    hedef["balina"] = r_balina.json()
            except Exception as e:
                print(f"[LS] {sym} balina L/S hata: {e}")

        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        img = _ls_gorsel(btc_ls, eth_ls, zaman_str)
        if img:
            _topic_foto_gonder_filigranli(TOPIC_ANALIZ, img, f"📈 Long/Short Oran — 1S — {zaman_str}\n/ls")
            print("[LS] Gorsel gonderildi.")

        yorum = _ls_yorum(btc_ls, eth_ls)
        _telegram_topic_mesaj_gonder(TOPIC_ANALIZ, yorum + "\n\n<code>/ls</code>")
        print("[LS] Tamamlandi.")
    except Exception as e:
        print(f"[LS] _ls_gonder hata: {e}")


def _ls_zamanlayici():
    """Her saatin :15'inde L/S raporu gönder. (v281 — 15dk döngü :15)"""
    import datetime as dt_mod
    print("[LS] Zamanlayici basladi. Her saat :15'de tetiklenecek.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()

            if simdi.minute < 15:
                sonraki = simdi.replace(minute=15, second=0, microsecond=0)
            else:
                sonraki = (simdi.replace(minute=15, second=0, microsecond=0)
                           + dt_mod.timedelta(hours=1))

            bekle = (sonraki - simdi).total_seconds()
            print(f"[LS] Sonraki rapor: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(max(bekle, 1))
            _ls_gonder()
            time.sleep(10)  # double-fire önleme
        except Exception as e:
            print(f"[LS] Zamanlayici hata: {e}")
            time.sleep(60)
    """BTC dominansını MEXC ticker'dan hesapla — CoinGecko Railway'de bloklu."""
    try:
        r = requests.get(
            "https://contract.mexc.com/api/v1/contract/ticker",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and data.get("data"):
                tickers = data["data"]
                # USDT pariteleri filtrele
                usdt_tickers = [t for t in tickers if str(t.get("symbol","")).endswith("_USDT")]
                # Toplam hacim hesapla
                toplam_hacim = sum(float(t.get("amount24", 0) or 0) for t in usdt_tickers)
                if toplam_hacim > 0:
                    btc_hacim  = next((float(t.get("amount24",0) or 0) for t in usdt_tickers if t.get("symbol") == "BTC_USDT"), 0)
                    eth_hacim  = next((float(t.get("amount24",0) or 0) for t in usdt_tickers if t.get("symbol") == "ETH_USDT"), 0)
                    btc_dom    = round(btc_hacim / toplam_hacim * 100, 2)
                    eth_dom    = round(eth_hacim / toplam_hacim * 100, 2)
                    return btc_dom, eth_dom, toplam_hacim, 0
    except Exception as e:
        print(f"[TREND] dominans hata: {e}")
    return None, None, None, None


def _trend_skor_hesapla(symbol):
    """
    Bir sembol için 0-100 arası trend skoru hesapla.
    EMA hizalaması (40p) + RSI (25p) + Momentum (20p) + Hacim (15p)
    """
    closes, volumes, highs, lows = _trend_fetch_klines(symbol, TREND_INTERVAL, 220)
    if not closes or len(closes) < TREND_EMA_MAJOR + 5:
        return None

    ema20  = _ema(closes, TREND_EMA_FAST)
    ema50  = _ema(closes, TREND_EMA_SLOW)
    ema200 = _ema(closes, TREND_EMA_MAJOR)
    rsi    = _rsi(closes, TREND_RSI_PERIOD)
    fiyat  = closes[-1]

    if None in (ema20, ema50, ema200, rsi):
        return None

    skor = 0

    # ── EMA Hizalaması (40 puan) ──
    # Tam bull: fiyat > ema20 > ema50 > ema200
    ema_skor = 0
    if fiyat > ema200: ema_skor += 10
    if fiyat > ema50:  ema_skor += 10
    if fiyat > ema20:  ema_skor += 10
    if ema20 > ema50:  ema_skor += 5
    if ema50 > ema200: ema_skor += 5
    skor += ema_skor

    # ── RSI (25 puan) ──
    # 70+ = 25p, 60-70 = 20p, 50-60 = 15p, 40-50 = 10p, 30-40 = 5p, <30 = 0p
    if rsi >= 70:   skor += 25
    elif rsi >= 60: skor += 20
    elif rsi >= 50: skor += 15
    elif rsi >= 40: skor += 10
    elif rsi >= 30: skor += 5

    # ── Momentum: Son 10 barlık değişim (20 puan) ──
    if len(closes) >= 11:
        momentum_pct = (closes[-1] - closes[-11]) / closes[-11] * 100
        if momentum_pct > 3:    skor += 20
        elif momentum_pct > 1:  skor += 15
        elif momentum_pct > 0:  skor += 10
        elif momentum_pct > -1: skor += 5
        # negatif momentum = 0p

    # ── Hacim Oranı: Son bar hacmi / 20 bar ortalaması (15 puan) ──
    if len(volumes) >= 21:
        avg_vol = sum(volumes[-21:-1]) / 20
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
        # Yüksek hacimli hareket trendi teyit eder
        # Yükseliş trendinde yüksek hacim = güçlü; düşüş trendinde düşük hacim = zayıf satış
        if fiyat > ema20:  # yükseliş bağlamında
            if vol_ratio > 1.5:   skor += 15
            elif vol_ratio > 1.0: skor += 10
            else:                 skor += 5
        else:  # düşüş bağlamında yüksek hacim kötü
            if vol_ratio > 1.5:   skor += 0
            elif vol_ratio > 1.0: skor += 3
            else:                 skor += 8

    # 24s değişim
    degisim_24h = None
    if len(closes) >= 97:  # 15dk * 96 = 24s
        degisim_24h = round((closes[-1] - closes[-97]) / closes[-97] * 100, 2)

    return {
        "symbol":      symbol.replace("USDT", ""),
        "fiyat":       fiyat,
        "skor":        min(skor, 100),
        "ema20":       round(ema20, 4),
        "ema50":       round(ema50, 4),
        "ema200":      round(ema200, 4),
        "rsi":         rsi,
        "degisim_24h": degisim_24h,
        "vol_ratio":   round(vol_ratio if len(volumes) >= 21 else 1.0, 2),
    }


def _trend_etiket(skor):
    if skor >= 75: return "🟢 GÜÇLÜ YÜKSELİŞ"
    if skor >= 55: return "🟡 YÜKSELİŞ"
    if skor >= 40: return "⚪ NÖTR"
    if skor >= 25: return "🟠 DÜŞÜŞ"
    return "🔴 GÜÇLÜ DÜŞÜŞ"


def _trend_etiket_kisa(skor):
    if skor >= 75: return "🟢 GÜÇLÜ ↑"
    if skor >= 55: return "🟡 YÜKSELİŞ"
    if skor >= 40: return "⚪ NÖTR"
    if skor >= 25: return "🟠 DÜŞÜŞ"
    return "🔴 GÜÇLÜ ↓"


def _trend_bar_renk(skor):
    if skor >= 75: return "#4CAF50"
    if skor >= 55: return "#8BC34A"
    if skor >= 40: return "#9E9E9E"
    if skor >= 25: return "#FF9800"
    return "#F44336"


def _trend_gorsel(sonuclar, btc_dom, eth_dom, total_mcap, mcap_change, fg_deger, fg_sinif, zaman_str):
    """Trend raporunu Tema1 (Lacivert/Altın) PNG olarak üret."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        import io
    except ImportError:
        return None

    # ── Tema 1 Renk Paleti ──────────────────────────────
    BG       = "#0A0E1A"   # arka plan — derin lacivert
    CARD_BG  = "#111827"   # kart zemin
    BORDER   = "#1E2D4A"   # kart kenarlık
    HDR_COL  = "#E8E8E6"   # başlık/etiket — beyaz
    TEXT_W   = "#FFFFFF"   # coin isimleri — tam beyaz
    TEXT_M   = "#FFFFFF"   # coin isimleri
    ALTIN    = "#C9A84C"   # altın vurgu
    TRACK    = "#1E2D4A"   # bar arka plan

    n     = len(sonuclar)
    fig_w = 9.0
    # Yükseklik: başlık(1.0) + metrik kartlar(0.9) + F&G(0.9) + tablo başlık(0.5) + n satır(0.65 her biri) + alt(0.4)
    fig_h = 1.0 + 0.9 + (0.9 if fg_deger is not None else 0) + 0.5 + n * 0.65 + 0.4

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor(BG)

    y = fig_h - 0.18

    # ── Başlık ──────────────────────────────────────────
    ax.text(fig_w / 2, y, "BEN KÜL YUTMAM — Piyasa Trend Raporu",
            ha="center", va="top", fontsize=16, fontweight="bold", color=TEXT_W)
    y -= 0.32
    ax.text(fig_w / 2, y, zaman_str,
            ha="center", va="top", fontsize=10.5, color=HDR_COL)
    y -= 0.12
    ax.axhline(y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.8)

    # ── 3 Metrik Kart: Piyasa Trend | F&G | BTC Dom ─────
    y -= 0.08
    ort_skor   = round(sum(s["skor"] for s in sonuclar) / len(sonuclar))
    ort_etiket = _trend_etiket(ort_skor)
    ort_renk   = _trend_bar_renk(ort_skor)

    fg_emoji, fg_etiket = _trend_fg_emoji(fg_deger) if fg_deger is not None else ("❓", "—")
    fg_renk = _trend_fg_renk(fg_deger) if fg_deger is not None else HDR_COL
    fg_str  = f"{fg_emoji} {fg_deger}  {fg_etiket}" if fg_deger is not None else "—"
    btc_dom_str = f"%{btc_dom}" if btc_dom else "—"
    kart_bilgi = [
        ("PİYASA TREND",  ort_etiket,   ort_renk),
        ("KORKU / AÇGÖZLÜLÜK",  fg_str,        fg_renk),
        ("BTC DOM",       btc_dom_str,   ALTIN),
    ]
    kart_w = fig_w / 3
    kart_h = 0.85  # daha yüksek kart — büyük font için
    for i, (lbl, val, col) in enumerate(kart_bilgi):
        kx = i * kart_w
        ax.add_patch(FancyBboxPatch(
            (kx + 0.12, y - kart_h + 0.06), kart_w - 0.24, kart_h - 0.10,
            boxstyle="round,pad=0.05", linewidth=0.8,
            edgecolor=BORDER, facecolor=CARD_BG))
        ax.text(kx + kart_w / 2, y - 0.16, lbl,
                ha="center", va="top", fontsize=16.5, color=HDR_COL)
        ax.text(kx + kart_w / 2, y - 0.52, val,
                ha="center", va="top", fontsize=21.5, color=col)
    y -= kart_h + 0.10

    # ── Fear & Greed Bar ────────────────────────────────
    if fg_deger is not None:
        bar_x = 0.20
        bar_w_total = fig_w - 0.40
        bar_h_fg    = 0.13

        ax.add_patch(FancyBboxPatch(
            (0.10, y - 0.72), fig_w - 0.20, 0.68,
            boxstyle="round,pad=0.04", linewidth=0.8,
            edgecolor=BORDER, facecolor=CARD_BG))

        ax.text(0.20, y - 0.10,
                "KORKU / AÇGÖZLÜLÜK ENDEKSİ",
                ha="left", va="center", fontsize=9.5,
                color=HDR_COL, fontweight="bold", zorder=3)
        ax.text(fig_w - 0.20, y - 0.10,
                f"{fg_emoji} {fg_deger}/100 — {fg_etiket}",
                ha="right", va="center", fontsize=11,
                color=fg_renk, fontweight="bold", zorder=3)

        # Bölge renk doldurma (gradient görünümü)
        bolge_renkler = [
            (0.00, 0.25, "#F44336"),
            (0.25, 0.45, "#FF9800"),
            (0.45, 0.55, "#9E9E9E"),
            (0.55, 0.75, "#8BC34A"),
            (0.75, 1.00, "#4CAF50"),
        ]
        track_y = y - 0.42
        ax.add_patch(plt.Rectangle((bar_x, track_y), bar_w_total, bar_h_fg,
                                   color=TRACK, zorder=1))
        for b_start, b_end, b_col in bolge_renkler:
            w_seg = bar_w_total * (b_end - b_start)
            alpha = 0.3
            ax.add_patch(plt.Rectangle(
                (bar_x + bar_w_total * b_start, track_y), w_seg, bar_h_fg,
                color=b_col, alpha=alpha, zorder=2))
        # Dolgu
        ax.add_patch(plt.Rectangle(
            (bar_x, track_y), bar_w_total * fg_deger / 100, bar_h_fg,
            color=fg_renk, alpha=0.9, zorder=3))
        # İbre
        igx = bar_x + bar_w_total * fg_deger / 100
        ax.plot([igx, igx], [track_y - 0.03, track_y + bar_h_fg + 0.03],
                color=TEXT_W, linewidth=1.5, zorder=4)

        # Bölge etiketleri
        bolge_lbls = [
            (0.125, "Aşırı Korku", "#F44336"),
            (0.350, "Korku",       "#FF9800"),
            (0.500, "Nötr",        "#9E9E9E"),
            (0.650, "Açgözlülük",  "#8BC34A"),
            (0.875, "Aşırı A.",    "#4CAF50"),
        ]
        for pct, lbl, col in bolge_lbls:
            ax.text(bar_x + bar_w_total * pct, track_y - 0.08,
                    lbl, ha="center", va="top", fontsize=8, color=col, zorder=4)

        y -= 0.80

    # ── Tablo Başlık ────────────────────────────────────
    ax.axhline(y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.8)
    y -= 0.08

    # Sütun x pozisyonları: Sembol | Trend Etiketi | Bar | 24h%
    C_SYM   = 0.20
    C_LABEL = 1.60
    C_BAR   = 3.80
    C_24H   = 8.30

    hdrs = [(C_SYM, "COİN"), (C_LABEL, "TREND DURUMU"),
            (C_BAR, "GÜÇ"), (C_24H, "24S%")]
    for hx, hdr in hdrs:
        ax.text(hx, y, hdr, ha="left", va="top",
                fontsize=8.5, color=HDR_COL)
    y -= 0.10
    ax.axhline(y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.6)

    # ── Coin Satırları ──────────────────────────────────
    satirlar = sorted(sonuclar, key=lambda x: x["skor"], reverse=True)
    row_h = 0.65

    for i, s in enumerate(satirlar):
        ry     = y - 0.08 - i * row_h
        row_bg = "#111827" if i % 2 == 0 else "#0D1120"
        renk   = _trend_bar_renk(s["skor"])
        etiket = _trend_etiket_kisa(s["skor"])

        ax.add_patch(FancyBboxPatch(
            (0.08, ry - row_h + 0.12), fig_w - 0.16, row_h - 0.10,
            boxstyle="round,pad=0.03", linewidth=0,
            facecolor=row_bg, zorder=0))

        mid_y = ry - row_h / 2 + 0.06

        # Coin ismi
        ax.text(C_SYM, mid_y, s["symbol"],
                ha="left", va="center", fontsize=12.5,
                fontweight="bold", color=TEXT_M, zorder=1)

        # Trend etiketi
        ax.text(C_LABEL, mid_y, etiket,
                ha="left", va="center", fontsize=11,
                fontweight="bold", color=renk, zorder=1)

        # Progress bar
        bar_x2    = C_BAR
        bar_w2    = 4.20
        bar_h2    = 0.14
        bar_y2    = mid_y - bar_h2 / 2
        ax.add_patch(plt.Rectangle((bar_x2, bar_y2), bar_w2, bar_h2,
                                   color=TRACK, zorder=1))
        ax.add_patch(plt.Rectangle((bar_x2, bar_y2),
                                   bar_w2 * s["skor"] / 100, bar_h2,
                                   color=renk, zorder=2))
        ax.text(bar_x2 + bar_w2 + 0.12, mid_y,
                str(s["skor"]), ha="left", va="center",
                fontsize=10, color=renk, fontweight="bold", zorder=2)

        # 24h değişim
        if s.get("degisim_24h") is not None:
            d     = s["degisim_24h"]
            d_col = "#4CAF50" if d >= 0 else "#F44336"
            d_str = f"+{d:.1f}%" if d >= 0 else f"{d:.1f}%"
            ax.text(C_24H, mid_y, d_str,
                    ha="right", va="center", fontsize=10.5,
                    fontweight="bold", color=d_col, zorder=1)

    # ── Alt Bilgi ───────────────────────────────────────
    bottom_y = y - 0.08 - n * row_h - 0.06
    ax.axhline(bottom_y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.6)

    en_guclu = satirlar[0]["symbol"]
    en_zayif = satirlar[-1]["symbol"]
    ax.text(0.20, bottom_y - 0.10,
            f"🏆 {en_guclu}   ⚠️ {en_zayif}",
            ha="left", va="top", fontsize=9.5, color=HDR_COL)
    ax.text(fig_w - 0.20, bottom_y - 0.10,
            f"@dayiscalper  |  EMA+RSI+Hacim  |  Binance 15dk",
            ha="right", va="top", fontsize=8.5, color=HDR_COL)

    plt.tight_layout(pad=0.2)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _trend_metin(sonuclar, btc_dom, eth_dom, total_mcap, mcap_change, fg_deger, fg_sinif, zaman_str):
    """Görsel sonrası gönderilecek kısa metin özeti."""
    ort_skor   = round(sum(s["skor"] for s in sonuclar) / len(sonuclar))
    ort_etiket = _trend_etiket(ort_skor)
    en_guclu   = max(sonuclar, key=lambda x: x["skor"])
    en_zayif   = min(sonuclar, key=lambda x: x["skor"])

    msg = (
        f"📊 <b>Piyasa Trend Özeti</b>\n"
        f"🕐 {zaman_str}\n\n"
        f"🌐 Genel Skor: <b>{ort_skor}/100</b>  {ort_etiket}\n"
    )

    # Fear & Greed
    if fg_deger is not None:
        fg_emoji, fg_etiket = _trend_fg_emoji(fg_deger)
        fg_renk_html = {
            "Aşırı Korku": "🔴", "Korku": "🟠",
            "Nötr": "⚪", "Açgözlülük": "🟡", "Aşırı Açgözlülük": "🟢"
        }.get(fg_etiket, "⚪")
        msg += f"{fg_emoji} Korku/Açgözlülük: <b>{fg_deger}/100</b>  {fg_renk_html} {fg_etiket}\n"

    if btc_dom:
        mcap_str = f"${total_mcap/1e9:.1f}B" if total_mcap else "—"
        mcap_ch  = f"{'+'if mcap_change>=0 else ''}{mcap_change}%" if mcap_change else ""
        mcap_col = "📈" if mcap_change and mcap_change >= 0 else "📉"
        msg += (
            f"\n<b>— Dominans (MEXC Hacim) —</b>\n"
            f"₿ BTC Dom: <b>{btc_dom}%</b>\n"
            f"Ξ ETH Dom: <b>{eth_dom}%</b>\n"
        )

    msg += "\n<b>— Coin Sıralaması —</b>\n"
    for i, s in enumerate(sorted(sonuclar, key=lambda x: x["skor"], reverse=True), 1):
        d = s.get("degisim_24h")
        d_str = f" ({'+' if d>=0 else ''}{d:.1f}%)" if d is not None else ""
        msg += f"{i}. <b>{s['symbol']}</b> — {_trend_etiket_kisa(s['skor'])} ({s['skor']}/100){d_str}\n"

    msg += (
        f"\n🏆 En Güçlü: <b>{en_guclu['symbol']}</b> ({en_guclu['skor']}/100)\n"
        f"⚠️ En Zayıf: <b>{en_zayif['symbol']}</b> ({en_zayif['skor']}/100)\n"
        f"\nİletişim: {KANAL_TAG}"
    )
    return msg


def _trend_gonder(chat_id=None):
    """Trend analizini hesapla, görsel + metin + L/S grafik olarak Telegram'a gönder."""
    hedef = chat_id or TELEGRAM_CHAT_ID
    print(f"[TREND] Analiz basliyor...")

    sonuclar = []
    for sym in TREND_SYMBOLS:
        try:
            s = _trend_skor_hesapla(sym)
            if s:
                sonuclar.append(s)
                print(f"[TREND] {sym}: skor={s['skor']} rsi={s['rsi']}")
        except Exception as e:
            print(f"[TREND] {sym} hata: {e}")

    if not sonuclar:
        _telegram_mesaj_gonder(hedef, "⚠️ Trend analizi için veri alınamadı.")
        return

    btc_dom, eth_dom, total_mcap, mcap_change = _trend_btc_dominans()
    fg_deger, fg_sinif = _trend_fear_greed()
    print(f"[TREND] Fear&Greed: {fg_deger} ({fg_sinif})")

    if TR_TZ:
        zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
    else:
        zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

    # Trend görseli + metin — Genişletilmiş Analiz zaten TOPIC_ANALIZ'de olduğu için buraya gönderilmiyor
    print("[TREND] Gorsel/metin TOPIC_ANALIZ'e gönderilmiyor (Genişletilmiş Analiz kapsıyor).")

    if TELEGRAM_LOG_ID:
        metin = _trend_metin(sonuclar, btc_dom, eth_dom, total_mcap, mcap_change, fg_deger, fg_sinif, zaman_str)
        _telegram_mesaj_gonder(TELEGRAM_LOG_ID, metin)

    print(f"[TREND] Tamamlandi. {len(sonuclar)} coin analiz edildi.")


def _trend_zamanlayici():
    """Her saatin :30'unda trend raporu gönder. (v281 — 15dk döngü :30)"""
    import datetime as dt_mod
    print("[TREND] Zamanlayici basladi. Her saat :30'da tetiklenecek.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()

            if simdi.minute < 30:
                sonraki = simdi.replace(minute=30, second=0, microsecond=0)
            else:
                sonraki = (simdi.replace(minute=30, second=0, microsecond=0)
                           + dt_mod.timedelta(hours=1))

            bekle = (sonraki - simdi).total_seconds()
            print(f"[TREND] Sonraki rapor: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(max(bekle, 1))
            _trend_gonder()
            time.sleep(10)  # double-fire önleme
        except Exception as e:
            print(f"[TREND] Zamanlayici hata: {e}")
            time.sleep(60)


# ==========================================
# MARKET YÖNÜ — OI + Funding + Spot/Futures Hacim
# ==========================================

# ==========================================
# GENİŞLETİLMİŞ PİYASA ANALİZİ — YARDIMCI FONKSİYONLAR
# ==========================================

def _cvd_hesapla(symbol, interval="1h", limit=24):
    """
    Kümülatif Hacim Deltası (CVD) hesapla.
    Binance kline sütun 9 = takerBuyBaseAssetVolume
    CVD = sum(takerBuy) - sum(takerSell)
    Dönen: {"cvd": float, "son_delta": float, "uyum": str}
    """
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=6, proxies=BINANCE_PROXY
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None

        cvd_kumulatif = 0.0
        fiyatlar = []
        for k in data:
            hacim     = float(k[5])
            taker_buy = float(k[9])   # takerBuyBaseAssetVolume
            taker_sell = hacim - taker_buy
            delta = taker_buy - taker_sell
            cvd_kumulatif += delta
            fiyatlar.append(float(k[4]))  # kapanış

        # Son delta (son mum)
        son_k = data[-1]
        son_hacim = float(son_k[5])
        son_buy   = float(son_k[9])
        son_delta = son_buy - (son_hacim - son_buy)

        # Fiyat yönü vs CVD yönü — uyumsuzluk tespiti
        # Son limit/2 mumla ilk limit/2 mumu karşılaştır
        yarim = max(limit // 2, 1)
        fiyat_erken = sum(fiyatlar[:yarim]) / yarim
        fiyat_son   = sum(fiyatlar[yarim:]) / max(len(fiyatlar[yarim:]), 1)
        fiyat_degisim = fiyat_son - fiyat_erken

        cvd_erken = 0.0
        cvd_son   = 0.0
        for i, k in enumerate(data):
            h = float(k[5])
            b = float(k[9])
            d = b - (h - b)
            if i < yarim:
                cvd_erken += d
            else:
                cvd_son   += d
        cvd_degisim = cvd_son - cvd_erken

        if fiyat_degisim > 0 and cvd_degisim > 0:
            uyum = "uyum"    # ikisi de yukarı
        elif fiyat_degisim < 0 and cvd_degisim < 0:
            uyum = "uyum"    # ikisi de aşağı
        elif fiyat_degisim > 0 and cvd_degisim < 0:
            uyum = "uyumsuz_yukari"   # fiyat ↑ CVD ↓ — satış gizleniyor
        elif fiyat_degisim < 0 and cvd_degisim > 0:
            uyum = "uyumsuz_asagi"    # fiyat ↓ CVD ↑ — birikim var
        else:
            uyum = "duz"

        return {
            "cvd":       round(cvd_kumulatif, 2),
            "son_delta": round(son_delta, 2),
            "uyum":      uyum,
        }
    except Exception as e:
        print(f"[CVD] {symbol} hata: {e}")
        return None


def _taker_oran_cek(symbol, interval="30m", limit=4):
    """
    Taker Buy/Sell oranı — Binance Futures takerlongshortRatio.
    Dönen: {"taker_buy_pct": float, "sinyal": str}
    """
    try:
        r = requests.get(
            "https://fapi.binance.com/futures/data/takerlongshortRatio",
            params={"symbol": symbol, "period": interval, "limit": limit},
            timeout=6, proxies=BINANCE_PROXY
        )
        if r.status_code != 200 or not r.json():
            return None
        data = r.json()
        son  = data[-1]
        buy_sell_ratio = float(son.get("buySellRatio", 1.0))
        # buySellRatio = takerBuyVol / takerSellVol
        buy_pct = round(buy_sell_ratio / (1 + buy_sell_ratio) * 100, 1)

        if buy_pct >= 58:
            sinyal = "guclu_alis"
        elif buy_pct >= 53:
            sinyal = "alis"
        elif buy_pct <= 42:
            sinyal = "guclu_satis"
        elif buy_pct <= 47:
            sinyal = "satis"
        else:
            sinyal = "denge"

        return {"taker_buy_pct": buy_pct, "sinyal": sinyal}
    except Exception as e:
        print(f"[TAKER] {symbol} hata: {e}")
        return None


def _likidasyon_cek(symbol, limit=50):
    """
    Likidasyon tahmini: OI değişimi + fiyat hareketi + 5m kline hacim bazlı.
    forceOrders endpoint Railway proxy'de bloklu — bu yaklaşım mevcut verilerle çalışır.
    Dönen: {"long_usd": float, "short_usd": float, "toplam_usd": float, "agirlik": str}
    """
    try:
        # 5 dakikalık kline (son 6 = 30dk)
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": symbol, "interval": "5m", "limit": 7},
            timeout=6, proxies=BINANCE_PROXY
        )
        if r.status_code != 200:
            return None
        klines = r.json()
        if len(klines) < 2:
            return None

        # Son 30dk fiyat değişimi ve taker hacmi
        fiyat_ilk  = float(klines[0][1])   # open
        fiyat_son  = float(klines[-1][4])   # close
        fiyat_pct  = (fiyat_son - fiyat_ilk) / fiyat_ilk * 100 if fiyat_ilk > 0 else 0

        # Taker buy/sell hacmi (kline[9]=takerBuyBase, [5]=volume)
        taker_buy  = sum(float(k[9]) for k in klines[:-1])
        taker_tot  = sum(float(k[5]) for k in klines[:-1])
        taker_sell = taker_tot - taker_buy
        taker_buy_pct = taker_buy / taker_tot * 100 if taker_tot > 0 else 50

        # OI değişimi
        r2 = requests.get(
            "https://fapi.binance.com/fapi/v1/openInterest",
            params={"symbol": symbol}, timeout=5, proxies=BINANCE_PROXY
        )
        oi_usdt = 0
        if r2.status_code == 200:
            oi_coin = float(r2.json().get("openInterest", 0))
            oi_usdt = oi_coin * fiyat_son

        # Tahmin mantığı:
        # Fiyat sert düştü + OI düştü = long likidasyon yaşandı
        # Fiyat sert yükseldi + OI düştü = short likidasyon yaşandı
        # Tahmin büyüklüğü: OI * |fiyat değişimi| / 100 * katsayı
        tahmin_base = oi_usdt * abs(fiyat_pct) / 100 * 0.15  # %15 oranında etkilendiği varsayımı

        if fiyat_pct <= -1.5:
            # Düşüş = long likidasyon baskın
            long_usd  = tahmin_base * 0.75
            short_usd = tahmin_base * 0.25
        elif fiyat_pct >= 1.5:
            # Yükseliş + OI düşüşü = short likidasyon baskın
            long_usd  = tahmin_base * 0.25
            short_usd = tahmin_base * 0.75
        elif taker_buy_pct <= 40:
            # Satış baskısı — long likidasyon
            long_usd  = tahmin_base * 0.65
            short_usd = tahmin_base * 0.35
        elif taker_buy_pct >= 60:
            # Alım baskısı — short likidasyon
            long_usd  = tahmin_base * 0.35
            short_usd = tahmin_base * 0.65
        else:
            long_usd  = tahmin_base * 0.5
            short_usd = tahmin_base * 0.5

        # M$ cinsine çevir
        long_usd  /= 1_000_000
        short_usd /= 1_000_000
        toplam = long_usd + short_usd

        if toplam == 0:
            agirlik = "yok"
        elif long_usd > short_usd * 2:
            agirlik = "long_baskin"   # longlar ezildi → düşüş baskısı
        elif short_usd > long_usd * 2:
            agirlik = "short_baskin"  # shortlar ezildi → yükseliş baskısı
        else:
            agirlik = "dengeli"

        return {
            "long_usd":  round(long_usd / 1e6, 2),
            "short_usd": round(short_usd / 1e6, 2),
            "toplam_usd": round(toplam / 1e6, 2),
            "agirlik":   agirlik,
        }
    except Exception as e:
        print(f"[LIK] {symbol} hata: {e}")
        return None


def _oi_delta_cek(symbol):
    """
    OI değişimini hafızadan hesapla — global dict'te önceki değer saklanıyor.
    Dönen: {"oi_usdt": float, "delta_pct": float, "delta_usdt": float, "yorum": str}
    """
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/openInterest",
            params={"symbol": symbol},
            timeout=6, proxies=BINANCE_PROXY
        )
        r2 = requests.get(
            "https://fapi.binance.com/fapi/v1/ticker/price",
            params={"symbol": symbol},
            timeout=6, proxies=BINANCE_PROXY
        )
        if r.status_code != 200 or r2.status_code != 200:
            return None

        oi_coin  = float(r.json().get("openInterest", 0))
        fiyat    = float(r2.json().get("price", 0))
        oi_usdt  = oi_coin * fiyat

        onceki   = _analiz_oi_onceki.get(symbol)
        _analiz_oi_onceki[symbol] = {"oi": oi_usdt, "zaman": time.time()}

        if onceki is None or onceki["oi"] == 0:
            return {"oi_usdt": oi_usdt, "delta_pct": 0, "delta_usdt": 0, "yorum": "ilk_okuma"}

        delta_usdt = oi_usdt - onceki["oi"]
        delta_pct  = delta_usdt / onceki["oi"] * 100

        if delta_pct > 1.5:
            yorum = "artis"
        elif delta_pct < -1.5:
            yorum = "azalis"
        else:
            yorum = "sakin"

        return {
            "oi_usdt":    round(oi_usdt / 1e9, 2),
            "delta_pct":  round(delta_pct, 2),
            "delta_usdt": round(delta_usdt / 1e6, 1),
            "yorum":      yorum,
        }
    except Exception as e:
        print(f"[OI_DELTA] {symbol} hata: {e}")
        return None


# OI hafıza — zamanlayıcılar arasında paylaşılır
_analiz_oi_onceki = {}
_son_analiz_veriler = {}   # _analiz_gonder sonrası cache — olta sorgusunda kullanılır

# ── Likidasyon WebSocket veri deposu ──
# {symbol: [(timestamp_ms, price, usd_value, side), ...]}  — son 6 saat tutulur
_liq_ws_data  = {"BTCUSDT": [], "ETHUSDT": []}
_liq_ws_kilit = threading.Lock()
LIQ_WS_SURE   = 6 * 3600       # 6 saat — bellek icindeki pencere
LIQ_WS_DOSYASI = "/data/liq_ws_data.json"
LIQ_WS_TEMIZLE_SURE  = 3 * 24 * 3600  # 3 gunde bir temizlik
LIQ_WS_SAKLA_SURE    = 1 * 24 * 3600  # 1 gunluk veri kalsin (2 gun silindi)


def _marketyonu_veri_cek():
    """BTC ve ETH için OI, funding rate, spot hacim, futures hacim çek."""
    sonuc = {}
    for sym, spot_sym in [("BTCUSDT", "BTCUSDT"), ("ETHUSDT", "ETHUSDT")]:
        try:
            veri = {}

            # 1) Funding Rate
            try:
                r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                                  params={"symbol": sym, "limit": 3}, timeout=6, proxies=BINANCE_PROXY)
                if r.status_code == 200 and r.json():
                    veri["funding"] = float(r.json()[0]["fundingRate"]) * 100
                    veri["funding_gecmis"] = [float(x["fundingRate"]) * 100 for x in r.json()]
                else:
                    veri["funding"] = 0
                    veri["funding_gecmis"] = []
            except Exception as e:
                veri["funding"] = 0
                veri["funding_gecmis"] = []
                print(f"[MARKETYONU] {sym} funding hata: {e}")

            # 2) Open Interest (anlık)
            try:
                r = requests.get("https://fapi.binance.com/fapi/v1/openInterest",
                                  params={"symbol": sym}, timeout=6, proxies=BINANCE_PROXY)
                veri["oi"] = float(r.json().get("openInterest", 0)) if r.status_code == 200 else 0
            except Exception as e:
                veri["oi"] = 0
                print(f"[MARKETYONU] {sym} OI hata: {e}")

            # 3) Futures 24h Ticker (hacim + fiyat)
            try:
                r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr",
                                  params={"symbol": sym}, timeout=6, proxies=BINANCE_PROXY)
                if r.status_code == 200:
                    t = r.json()
                    veri["futures_hacim_usdt"] = float(t.get("quoteVolume", 0))
                    veri["futures_hacim_coin"] = float(t.get("volume", 0))
                    veri["fiyat"] = float(t.get("lastPrice", 0))
                    veri["degisim_pct"] = float(t.get("priceChangePercent", 0))
                else:
                    veri["futures_hacim_usdt"] = 0
                    veri["fiyat"] = 0
                    veri["degisim_pct"] = 0
            except Exception as e:
                veri["futures_hacim_usdt"] = 0
                veri["fiyat"] = 0
                veri["degisim_pct"] = 0
                print(f"[MARKETYONU] {sym} futures ticker hata: {e}")

            # 4) Spot 24h Ticker (hacim)
            try:
                r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                                  params={"symbol": spot_sym}, timeout=6)
                if r.status_code == 200:
                    t = r.json()
                    veri["spot_hacim_usdt"] = float(t.get("quoteVolume", 0))
                    veri["spot_hacim_coin"] = float(t.get("volume", 0))
                else:
                    veri["spot_hacim_usdt"] = 0
            except Exception as e:
                veri["spot_hacim_usdt"] = 0
                print(f"[MARKETYONU] {sym} spot ticker hata: {e}")

            sonuc[sym] = veri
        except Exception as e:
            print(f"[MARKETYONU] {sym} genel hata: {e}")
    return sonuc


def _marketyonu_yorum(veri_map):
    """OI + Funding + Spot/Futures hacim verilerinden market yönü yorumu üret."""
    if TR_TZ:
        zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
    else:
        zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

    satirlar = [f"📡 <b>Market Yönü Analizi</b> — {zaman_str}\n"]

    for sym in ["BTCUSDT", "ETHUSDT"]:
        veri = veri_map.get(sym)
        if not veri:
            continue

        sym_kisa = sym.replace("USDT", "")
        emoji = "₿" if sym_kisa == "BTC" else "Ξ"
        fiyat = veri.get("fiyat", 0)
        degisim = veri.get("degisim_pct", 0)
        funding = veri.get("funding", 0)
        oi = veri.get("oi", 0) * fiyat  # USDT cinsinden OI
        fut_hacim = veri.get("futures_hacim_usdt", 0)
        spot_hacim = veri.get("spot_hacim_usdt", 0)

        def _hacim_fmt(v):
            if v >= 1e9: return f"${v/1e9:.2f}B"
            if v >= 1e6: return f"${v/1e6:.1f}M"
            return f"${v:,.0f}"

        def _oi_fmt(v):
            if v >= 1e9: return f"${v/1e9:.2f}B"
            if v >= 1e6: return f"${v/1e6:.1f}M"
            return f"${v:,.0f}"

        degisim_emoji = "🟢" if degisim > 0 else ("🔴" if degisim < 0 else "⚪")
        satirlar.append(f"<b>{emoji} {sym_kisa}USDT</b>  {degisim_emoji} {degisim:+.2f}%  |  ${fiyat:,.2f}")

        # OI yorumu
        if oi > 0:
            satirlar.append(f"📊 OI: <b>{_oi_fmt(oi)}</b>")

        # Funding yorumu
        if funding > 0.01:
            fund_yorum = f"💚 Funding: <b>+{funding:.4f}%</b> — Long ağırlıklı, short squeeze riski"
        elif funding < -0.01:
            fund_yorum = f"❤️ Funding: <b>{funding:.4f}%</b> — Short ağırlıklı, long squeeze riski"
        else:
            fund_yorum = f"⚪ Funding: <b>{funding:.4f}%</b> — Dengeli"
        satirlar.append(fund_yorum)

        # Spot vs Futures hacim analizi — fake/gerçek tespiti
        if spot_hacim > 0 and fut_hacim > 0:
            oran = fut_hacim / spot_hacim if spot_hacim > 0 else 0
            satirlar.append(f"📦 Spot: <b>{_hacim_fmt(spot_hacim)}</b>  |  Futures: <b>{_hacim_fmt(fut_hacim)}</b>")
            if oran > 5:
                hacim_yorum = (f"⚠️ <b>Futures/Spot oranı: {oran:.1f}x</b> — Futures baskın, "
                               f"kaldıraçlı spekülasyon yüksek; hareket <b>SAHTE</b> olabilir")
            elif oran > 2:
                hacim_yorum = (f"🟡 <b>Futures/Spot oranı: {oran:.1f}x</b> — Kaldıraç var, "
                               f"trend yönünde dikkatli ol")
            else:
                hacim_yorum = (f"✅ <b>Futures/Spot oranı: {oran:.1f}x</b> — Spot destekli hareket, "
                               f"<b>GERÇEK</b> talep/arz görünümü")
            satirlar.append(hacim_yorum)
        elif fut_hacim > 0:
            satirlar.append(f"📦 Futures: <b>{_hacim_fmt(fut_hacim)}</b>")

        # Özet sinyal
        sinyaller = []
        if funding > 0.03:
            sinyaller.append("aşırı long yığılması")
        elif funding < -0.03:
            sinyaller.append("aşırı short yığılması")
        if degisim > 3 and spot_hacim > 0 and fut_hacim / max(spot_hacim, 1) < 2:
            sinyaller.append("spot destekli yükseliş")
        elif degisim < -3 and spot_hacim > 0 and fut_hacim / max(spot_hacim, 1) < 2:
            sinyaller.append("spot destekli düşüş")
        if sinyaller:
            satirlar.append(f"🔍 Özet: {', '.join(sinyaller)}")

        satirlar.append("")

    satirlar.append(f"<i>Kaynak: Binance Spot + Futures  |  {zaman_str}</i>")
    return "\n".join(satirlar)


def _marketyonu_gonder():
    """OI + Funding Rate + Spot/Futures hacim analizi — Genişletilmiş Analiz kapsıyor, TOPIC_ANALIZ'e gönderilmiyor."""
    print("[MARKETYONU] Zamanlayici tetiklendi — veri çekiliyor (log icin).")
    try:
        veri_map = _marketyonu_veri_cek()
        if not veri_map:
            print("[MARKETYONU] Veri alinamadi.")
            return
        if TELEGRAM_LOG_ID:
            yorum = _marketyonu_yorum(veri_map)
            _telegram_mesaj_gonder(TELEGRAM_LOG_ID, yorum)
        print("[MARKETYONU] Tamamlandi (TOPIC_ANALIZ'e gonderilmedi — Genişletilmiş Analiz kapsıyor).")
    except Exception as e:
        print(f"[MARKETYONU] Hata: {e}")


def _marketyonu_zamanlayici():
    """Her saatin :45'inde market yönü raporu gönder. (v281 — 15dk döngü :45)"""
    import datetime as dt_mod
    print("[MARKETYONU] Zamanlayici basladi. Her saat :45'de tetiklenecek.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()

            if simdi.minute < 45:
                sonraki = simdi.replace(minute=45, second=0, microsecond=0)
            else:
                sonraki = (simdi.replace(minute=45, second=0, microsecond=0)
                           + dt_mod.timedelta(hours=1))

            bekle = (sonraki - simdi).total_seconds()
            print(f"[MARKETYONU] Sonraki rapor: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(max(bekle, 1))
            _marketyonu_gonder()
            time.sleep(10)  # double-fire önleme
        except Exception as e:
            print(f"[MARKETYONU] Zamanlayici hata: {e}")
            time.sleep(60)


# ==========================================
# GENİŞLETİLMİŞ PİYASA ANALİZİ — /analiz
# ==========================================

def _analiz_veri_topla():
    """
    Tüm coinler için paralel veri çekimi.
    Her coin: trend skoru, funding, OI delta, CVD, taker, likidasyon, spot/futures hacim.
    BTC/ETH/SOL için ek: destek/direnç, olta seviyeleri.
    """
    import concurrent.futures

    ANALIZ_SEMBOLLER = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"
    ]

    sonuclar = {}

    def _tek_coin(sym):
        veri = {}
        try:
            # 1) Trend skoru (EMA + RSI + momentum + hacim)
            t = _trend_skor_hesapla(sym)
            if t:
                veri.update(t)

            # 2) Funding rate
            try:
                rf = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                                   params={"symbol": sym, "limit": 3}, timeout=5, proxies=BINANCE_PROXY)
                if rf.status_code == 200 and rf.json():
                    rates = [float(x["fundingRate"]) * 100 for x in rf.json()]
                    veri["funding"]     = rates[0]
                    veri["funding_kum"] = round(sum(rates), 4)  # 3 periyot kümülatif
                else:
                    veri["funding"] = 0; veri["funding_kum"] = 0
            except:
                veri["funding"] = 0; veri["funding_kum"] = 0

            # 3) OI delta
            oi_d = _oi_delta_cek(sym)
            veri["oi_delta"] = oi_d

            # 4) CVD (1h, son 24 mum)
            cvd = _cvd_hesapla(sym, interval="1h", limit=24)
            veri["cvd"] = cvd

            # 5) Taker oranı (30m, son 4)
            taker = _taker_oran_cek(sym, interval="30m", limit=4)
            veri["taker"] = taker

            # 6) Son 30dk likidasyon
            lik = _likidasyon_cek(sym, limit=50)
            veri["likidasyonlar"] = lik

            # 7) Futures/Spot hacim oranı
            # fapi proxy üzerinden futures hacmi çek
            # Spot: api.binance.com proxy'de bloklu olabilir → MEXC spot fallback
            try:
                rf2 = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr",
                                    params={"symbol": sym}, timeout=5, proxies=BINANCE_PROXY)
                fut_h = float(rf2.json().get("quoteVolume", 0)) if rf2.status_code == 200 else 0

                # Spot hacim: önce Binance spot, bloklu ise MEXC spot
                spt_h = 0
                try:
                    rs2 = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                                        params={"symbol": sym}, timeout=5, proxies=BINANCE_PROXY)
                    if rs2.status_code == 200:
                        spt_h = float(rs2.json().get("quoteVolume", 0))
                except Exception:
                    pass

                if spt_h == 0:
                    # MEXC spot fallback
                    try:
                        mexc_sym = sym.replace("USDT", "_USDT")
                        rm = requests.get("https://contract.mexc.com/api/v1/contract/ticker",
                                          params={"symbol": mexc_sym}, timeout=5)
                        if rm.status_code == 200:
                            td = rm.json().get("data", [{}])
                            if isinstance(td, list) and td:
                                spt_h = float(td[0].get("amount24", 0))
                            elif isinstance(td, dict):
                                spt_h = float(td.get("amount24", 0))
                    except Exception:
                        pass

                veri["fut_hacim"]  = fut_h
                veri["spt_hacim"]  = spt_h
                veri["hac_carpan"] = round(fut_h / spt_h, 1) if spt_h > 0 else 0
            except Exception:
                veri["fut_hacim"] = 0; veri["spt_hacim"] = 0; veri["hac_carpan"] = 0

            # 8) BTC/ETH/SOL için destek/direnç (liq veri)
            if sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
                lv = _liq_veri_cek(sym)
                if lv:
                    veri["destek"]  = lv.get("destek")
                    veri["direnc"]  = lv.get("direnc")
                    veri["high_24h"] = lv.get("high_24h", 0)
                    veri["low_24h"]  = lv.get("low_24h", 0)
                    veri["momentum_4h"] = lv.get("momentum_4h")

        except Exception as e:
            print(f"[ANALIZ] {sym} veri hatasi: {e}")
        return sym, veri

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_tek_coin, s): s for s in ANALIZ_SEMBOLLER}
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=55):
                try:
                    sym, veri = fut.result()
                    sonuclar[sym] = veri
                except Exception as e:
                    print(f"[ANALIZ] Paralel hata: {e}")
        except concurrent.futures.TimeoutError:
            print("[ANALIZ] Timeout — tamamlanan coin'lerle devam ediliyor")
            for fut, sym in futures.items():
                if fut.done() and sym not in sonuclar:
                    try:
                        s, v = fut.result()
                        sonuclar[s] = v
                    except Exception:
                        pass

    # Market breadth — EMA20 üstünde kaç coin
    breadth = sum(1 for s, v in sonuclar.items()
                  if v.get("fiyat", 0) > v.get("ema20", float("inf")))
    sonuclar["_breadth"] = breadth

    return sonuclar



def _olta_fib_hesapla(closes, highs, lows, fiyat, interval):
    """
    TF bazli Fibonacci olta seviyeleri.
    Her TF farkli kisa vadeli swing kullanir — buyuk swing ortusunu engeller.
    Giris/SL Fib bazli, TP TF'e ozgu yuzde adimlarla — tekrar engellenir.
    """
    if not closes or len(closes) < 30:
        return None

    # Kisa vadeli swing: her TF sadece SON N mumu bakar
    # Boylece 1h/4h/1d birbirinden farkli swing alir
    lb_map = {"5m": 6, "15m": 12, "1h": 24, "4h": 14, "1d": 30}
    lb = min(lb_map.get(interval, 30), len(highs) - 1)
    swing_high = max(highs[-lb:])
    swing_low  = min(lows[-lb:])
    rng = swing_high - swing_low
    if rng <= 0 or rng < fiyat * 0.001:
        return None

    # Fib seviyeleri
    fib_236 = swing_low  + rng * 0.236
    fib_382 = swing_low  + rng * 0.382
    fib_500 = swing_low  + rng * 0.500
    fib_618 = swing_low  + rng * 0.618
    fib_786 = swing_low  + rng * 0.786
    fib_100 = swing_high
    fib_1272 = swing_high + rng * 0.272
    fib_1618 = swing_high + rng * 0.618

    dec = 6 if fiyat < 0.01 else (5 if fiyat < 0.1 else (4 if fiyat < 1 else (2 if fiyat < 10 else (1 if fiyat < 100 else 0))))
    def rd(v): return round(v, dec)

    # TF'e ozgu TP yuzdeleri — kisa TF kucuk hedef, uzun TF buyuk hedef
    tp_pct = {
        "5m":  (0.012, 0.022),
        "15m": (0.018, 0.032),
        "1h":  (0.030, 0.055),
        "4h":  (0.055, 0.095),
        "1d":  (0.100, 0.170),
    }
    tp1_pct, tp2_pct = tp_pct.get(interval, (0.018, 0.032))

    # ── LONG ──
    l_giris_adaylar = sorted(
        [f for f in [fib_618, fib_500, fib_382, fib_236] if f < fiyat],
        reverse=True
    )
    long_giris = rd(l_giris_adaylar[0]) if l_giris_adaylar else rd(fiyat * 0.985)
    # Minimum mesafe: long giriş fiyattan en az %0.3 aşağıda olmalı
    if long_giris >= fiyat * 0.997:
        long_giris = rd(fiyat * 0.994)

    l_sl_adaylar = sorted(
        [f for f in [fib_786, fib_618, fib_500, fib_382, fib_236, swing_low]
         if f < long_giris - rng * 0.01],
        reverse=True
    )
    long_sl = rd(l_sl_adaylar[0]) if l_sl_adaylar else rd(long_giris * (1 - tp1_pct))
    if long_sl >= long_giris:
        long_sl = rd(long_giris * 0.985)

    # TP: once Fib seviyesi dene, yoksa TF yuzde kullan
    l_tp_fib = sorted([f for f in [fib_786, fib_100, fib_1272, fib_1618] if f > fiyat * (1 + tp1_pct * 0.5)])
    if len(l_tp_fib) >= 2:
        long_tp1 = rd(l_tp_fib[0])
        long_tp2 = rd(l_tp_fib[1]) if l_tp_fib[1] > l_tp_fib[0] * (1 + tp1_pct * 0.3) else rd(fiyat * (1 + tp2_pct))
    elif len(l_tp_fib) == 1:
        long_tp1 = rd(l_tp_fib[0])
        long_tp2 = rd(fiyat * (1 + tp2_pct))
    else:
        long_tp1 = rd(fiyat * (1 + tp1_pct))
        long_tp2 = rd(fiyat * (1 + tp2_pct))
    if long_tp1 == long_tp2 or long_tp2 <= long_tp1:
        long_tp2 = rd(long_tp1 * (1 + tp1_pct))

    # ── SHORT ──
    s_giris_adaylar = sorted(
        [f for f in [fib_618, fib_786, fib_100] if f > fiyat]
    )
    short_giris = rd(s_giris_adaylar[0]) if s_giris_adaylar else rd(fiyat * (1 + tp1_pct))
    # Minimum mesafe: short giriş fiyattan en az %0.3 yukarıda olmalı
    if short_giris <= fiyat * 1.003:
        short_giris = rd(fiyat * 1.006)

    s_sl_adaylar = sorted(
        [f for f in [fib_786, fib_100, fib_1272, fib_1618]
         if f > short_giris + rng * 0.01]
    )
    short_sl = rd(s_sl_adaylar[0]) if s_sl_adaylar else rd(short_giris * (1 + tp1_pct * 0.5))
    if short_sl <= short_giris:
        short_sl = rd(short_giris * 1.015)

    # TP: once Fib seviyesi dene, yoksa TF yuzde kullan
    s_tp_fib = sorted(
        [f for f in [fib_618, fib_500, fib_382, fib_236, swing_low]
         if f < fiyat * (1 - tp1_pct * 0.5)],
        reverse=True
    )
    if len(s_tp_fib) >= 2:
        short_tp1 = rd(s_tp_fib[0])
        short_tp2 = rd(s_tp_fib[1]) if s_tp_fib[0] - s_tp_fib[1] > fiyat * tp1_pct * 0.3 else rd(fiyat * (1 - tp2_pct))
    elif len(s_tp_fib) == 1:
        short_tp1 = rd(s_tp_fib[0])
        short_tp2 = rd(fiyat * (1 - tp2_pct))
    else:
        short_tp1 = rd(fiyat * (1 - tp1_pct))
        short_tp2 = rd(fiyat * (1 - tp2_pct))
    if short_tp1 == short_tp2 or short_tp2 >= short_tp1:
        short_tp2 = rd(short_tp1 * (1 - tp1_pct))

    # ── GÜVEN SKORU hesapla ──
    def _skor(giris, sl, tp1, tp2, yon):
        puan = 0
        notlar = []

        # 1) Risk/Ödül oranı
        risk = abs(giris - sl)
        odul = abs(tp1 - giris)
        rr = odul / risk if risk > 0 else 0
        if rr >= 3.0:
            puan += 40; notlar.append(f"R:R 1:{rr:.1f}")
        elif rr >= 2.0:
            puan += 30; notlar.append(f"R:R 1:{rr:.1f}")
        elif rr >= 1.5:
            puan += 15; notlar.append(f"R:R 1:{rr:.1f}")
        else:
            notlar.append(f"R:R 1:{rr:.1f} zayif")

        # 2) Giriş güçlü Fib seviyesinde mi? (%61.8 veya %50)
        giris_tol = rng * 0.015
        if abs(giris - fib_618) < giris_tol or abs(giris - fib_500) < giris_tol:
            puan += 25; notlar.append("Fib %61.8/%50 girisi")
        elif abs(giris - fib_382) < giris_tol or abs(giris - fib_786) < giris_tol:
            puan += 15; notlar.append("Fib %38.2/%78.6 girisi")
        else:
            puan += 5

        # 3) Giriş fiyata ne kadar yakın? (ulaşılabilirlik)
        uzaklik_pct = abs(giris - fiyat) / fiyat * 100
        if uzaklik_pct <= 1.0:
            puan += 20; notlar.append(f"%{uzaklik_pct:.1f} uzakta")
        elif uzaklik_pct <= 2.5:
            puan += 12; notlar.append(f"%{uzaklik_pct:.1f} uzakta")
        elif uzaklik_pct <= 5.0:
            puan += 5
        # 5'ten uzak = puan yok

        # 4) TP2 de Fib seviyesine yakın mı?
        tp2_fib_ok = any(abs(tp2 - f) < rng * 0.02
                         for f in [fib_100, fib_1272, fib_1618, fib_382, fib_236])
        if tp2_fib_ok:
            puan += 15; notlar.append("TP2 Fib destekli")

        return min(puan, 100), rr, notlar

    long_skor,  long_rr,  long_notlar  = _skor(long_giris,  long_sl,  long_tp1,  long_tp2,  "long")
    short_skor, short_rr, short_notlar = _skor(short_giris, short_sl, short_tp1, short_tp2, "short")

    def _emoji(skor):
        if skor >= 80: return "⭐"
        if skor >= 60: return "✅"
        if skor >= 40: return "⚠️"
        return "❌"

    return {
        "long_giris":  long_giris,  "long_sl":   long_sl,
        "long_tp1":    long_tp1,    "long_tp2":  long_tp2,
        "short_giris": short_giris, "short_sl":  short_sl,
        "short_tp1":   short_tp1,   "short_tp2": short_tp2,
        "swing_high":  rd(swing_high), "swing_low": rd(swing_low),
        "long_skor":   long_skor,   "long_rr":   round(long_rr, 1),
        "long_emoji":  _emoji(long_skor),
        "short_skor":  short_skor,  "short_rr":  round(short_rr, 1),
        "short_emoji": _emoji(short_skor),
    }



def _skor_klines_cek(symbol, interval, limit, since_ts=None):
    """
    /skor icin hafif kline cekici.
    MEXC futures → MEXC spot → Binance spot (proxy)
    len>=50 sarti YOK. Min 3 mum yeterli.
    since_ts: Unix timestamp — bu andan itibaren mumlar getirilir.
              None ise son 24 saat kullanilir.
    """
    # MEXC futures interval adlari — 1h icin alternatifleri de dene
    mexc_iv_map = {
        "5m":  ["Min5"],
        "15m": ["Min15"],
        "1h":  ["Min60", "Hour1", "60m"],
        "4h":  ["Hour4", "Min240"],
        "1d":  ["Day1"],
    }
    mexc_ivs  = mexc_iv_map.get(interval, ["Min15"])
    mexc_sym  = symbol.replace("USDT", "_USDT") if "_" not in symbol else symbol

    # 1) MEXC Futures — her interval adini dene
    for mexc_iv in mexc_ivs:
        try:
            r = requests.get(
                f"https://contract.mexc.com/api/v1/contract/kline/{mexc_sym}",
                params={"interval": mexc_iv, "limit": limit},
                timeout=5
            )
            if r.status_code == 200:
                js = r.json()
                # MEXC bazi durumlarda success:false doner — kontrol et
                if not js.get("success", True):
                    print(f"[SKOR] MEXC futures {mexc_iv} basarisiz: {js.get('message','')}")
                    continue
                d = js.get("data", {})
                closes  = [float(x) for x in d.get("close", [])]
                highs   = [float(x) for x in d.get("high",  [])]
                lows    = [float(x) for x in d.get("low",   [])]
                volumes = [float(x) for x in d.get("vol",   [])]
                if len(closes) >= 3:
                    print(f"[SKOR] MEXC futures OK: {symbol} {interval}({mexc_iv}) {len(closes)} mum")
                    return closes, volumes, highs, lows
            else:
                print(f"[SKOR] MEXC futures HTTP {r.status_code} ({symbol} {mexc_iv}): {r.text[:80]}")
        except Exception as e:
            print(f"[SKOR] MEXC futures hata ({symbol} {mexc_iv}): {e}")

    # 2) MEXC Spot — standart interval adi
    try:
        spot_params = {"symbol": symbol, "interval": interval, "limit": limit}
        if since_ts:
            spot_params["startTime"] = since_ts * 1000  # ms
        r = requests.get(
            "https://api.mexc.com/api/v3/klines",
            params=spot_params,
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                closes  = [float(k[4]) for k in data]
                highs   = [float(k[2]) for k in data]
                lows    = [float(k[3]) for k in data]
                volumes = [float(k[5]) for k in data]
                if len(closes) >= 3:
                    print(f"[SKOR] MEXC spot OK: {symbol} {interval} {len(closes)} mum")
                    return closes, volumes, highs, lows
    except Exception as e:
        print(f"[SKOR] MEXC spot hata ({symbol} {interval}): {e}")

    # 3) Binance fallback kaldirildi (v463) — proxy tasarrufu
    # MEXC Spot yeterli, Binance proxy gerektiriyor ve Railway'de calismiyor

    # 1h icin ozel fallback: 15m mumlardan hesapla
    if interval == "1h":
        print(f"[SKOR] 1h fallback: 15m mumlardan hesaplaniyor")
        try:
            r = requests.get(
                "https://api.mexc.com/api/v3/klines",
                params={"symbol": symbol, "interval": "15m", "limit": min(limit * 4, 400)},
                timeout=5
            )
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and len(data) >= 4:
                    # Her 4 x 15m mumu 1 x 1h muma donustur
                    closes=[]; highs=[]; lows=[]; volumes=[]
                    for i in range(0, len(data)-3, 4):
                        chunk = data[i:i+4]
                        closes.append(float(chunk[-1][4]))
                        highs.append(max(float(c[2]) for c in chunk))
                        lows.append(min(float(c[3]) for c in chunk))
                        volumes.append(sum(float(c[5]) for c in chunk))
                    if len(closes) >= 3:
                        print(f"[SKOR] 15m→1h fallback OK: {symbol} {len(closes)} mum")
                        return closes, volumes, highs, lows
        except Exception as e:
            print(f"[SKOR] 15m→1h fallback hata: {e}")

    print(f"[SKOR] Tum kaynaklar basarisiz: {symbol} {interval}")
    return None, None, None, None


def _olta_skor_parse(metin):
    """
    Olta mesajini parse eder. Iki format desteklenir:
    FORMAT A (BTC TUM — tablo): pre icinde TF satirlari
      "5dk   69.890 69.699 70.334 70.506  ⭐85"
    FORMAT B (BTC — eski olta): LONG OLTA / SHORT OLTA bloklari
      "🟢 LONG OLTA\n  Giris: 69,490 – 69,908\n  Stop: 68,863\n  TP1: 71,016"
    """
    import re

    # Sembol bul — her iki formatta da var
    sym = None
    m_sym = re.search(r'([A-Z]{2,10}USDT)', metin)
    if m_sym:
        sym = m_sym.group(1).upper()
    if not sym:
        return None

    def parse_sayi(s):
        """
        Turk/TR fiyat formatlarini dogru parse eder.
        Olta tablosu q() fonksiyonu ile uretilir: noktali binlik (69.890, 1.906)
        Eski olta virgullu (69,890) veya (1,982) kullanir.

        Kural — NOKTA ayirici:
          Hem tam hem ondalik kisim 3 hane olunca (X.XXX) → BINLIK
          Ornek: 1.906 → 1906, 69.890 → 69890, 70.334 → 70334
          Gercek ondalik: 69.89 (2 hane) → 69.89

        Kural — VIRGUL ayirici:
          Ondalik 3 hane, tam 2+ hane → BINLIK: 69,890 → 69890
          Ondalik 3 hane, tam 1 hane  → ONDALIK: 1,982 → 1.982
        """
        s = s.replace(" ", "")
        if "." in s and "," not in s:
            parca = s.split(".")
            if len(parca) == 2 and len(parca[1]) == 3:
                # Her durumda 3 haneli ondalik → binlik nokta
                # 1.906→1906, 69.890→69890, 70.334→70334
                return float(s.replace(".", ""))
            return float(s)  # 69.89, 2.5 gibi gercek ondalik
        if "," in s and "." not in s:
            parca = s.split(",")
            if len(parca) == 2 and len(parca[1]) == 3 and len(parca[0]) >= 2:
                return float(s.replace(",", ""))  # 69,890 → 69890
            return float(s.replace(",", "."))     # 1,982 → 1.982
        return float(s.replace(",", ""))
    tf_iv_map = {"5dk": "5m", "15dk": "15m", "1s": "1h", "4s": "4h",
                 "gun": "1d", "gün": "1d"}

    # ── FORMAT A: Tablo (BTC TUM) ──
    satirlar_a = []
    for line in metin.split("\n"):
        line = line.strip()
        parcalar = line.split()
        if not parcalar:
            continue
        tf_raw = parcalar[0].lower()
        if tf_raw not in tf_iv_map:
            continue
        sayilar = re.findall(r"\d+[.,]\d+|\d{4,}", line)
        try:
            sayilar = [parse_sayi(s) for s in sayilar]
        except Exception:
            continue
        if len(sayilar) < 3:
            continue
        satirlar_a.append({
            "tf":    parcalar[0],
            "iv":    tf_iv_map[tf_raw],
            "giris": sayilar[0],
            "sl":    sayilar[1],
            "tp1":   sayilar[2],
            "tp2":   sayilar[3] if len(sayilar) > 3 else None,
        })

    if satirlar_a:
        # Yon: basliga bak
        yon = "short" if "SHORT" in metin.upper().split("\n")[0] else "long"
        return {"sym": sym, "yon": yon, "satirlar": satirlar_a, "format": "tablo"}

    # ── FORMAT B: Eski olta (BTC) ──
    # Her yon icin ayri parse, ikisini de dondur
    def parse_blok(blok_metin, yon):
        giris = sl = tp1 = tp2 = None
        for line in blok_metin.split("\n"):
            line = line.strip()
            lu = line.upper()
            ll = line.lower()
            # Kolon sonrasindaki sayilari cek — TP1/TP2 etiketindeki rakamlari atla
            kolon_sonrasi = line.split(":", 1)[-1] if ":" in line else line
            sayilar_ham = re.findall(r"\d[\d.,]*\d|\d{2,}", kolon_sonrasi)
            sayilar = []
            for s in sayilar_ham:
                try: sayilar.append(parse_sayi(s))
                except Exception: pass
            if not sayilar:
                continue
            if "giri" in ll:
                # "Giris: 1,950 - 1,962" → orta noktayi al
                if len(sayilar) >= 2:
                    giris = (sayilar[0] + sayilar[1]) / 2
                else:
                    giris = sayilar[0]
            elif "stop" in ll and not sl:
                sl = sayilar[0]
            elif lu.strip().startswith("TP1") and not tp1:
                tp1 = sayilar[0]
            elif lu.strip().startswith("TP2") and not tp2:
                tp2 = sayilar[0]
            elif lu.strip().startswith("TP:") and not tp1:
                tp1 = sayilar[0]
        if giris and sl and tp1:
            return [{"tf": "15dk", "iv": "15m", "giris": giris,
                     "sl": sl, "tp1": tp1, "tp2": tp2}]
        return []

    # LONG blogu bul
    long_satirlar = []; short_satirlar = []
    m_long  = re.search(r"LONG OLTA(.+?)(?=SHORT OLTA|$)", metin, re.DOTALL | re.IGNORECASE)
    m_short = re.search(r"SHORT OLTA(.+?)$", metin, re.DOTALL | re.IGNORECASE)
    if m_long:
        long_satirlar  = parse_blok(m_long.group(1),  "long")
    if m_short:
        short_satirlar = parse_blok(m_short.group(1), "short")

    if long_satirlar or short_satirlar:
        # Her iki yon icin ayri sonuc: once long dondur, short icin {"yon":"short"} ile tekrar cagrilabilir
        # Basitlik icin: long + short birlesik, yon="her ikisi"
        return {
            "sym": sym,
            "yon": "long",
            "satirlar": long_satirlar,
            "yon2": "short",
            "satirlar2": short_satirlar,
            "format": "eski"
        }

    return None


def _olta_skor_kontrol_parsed(parsed):
    """
    Parse edilmis olta dict'ini dogrudan alarak skor kontrolu yapar.
    Cache'den gelen parsed dict icin kullanilir.
    """
    if not parsed:
        return None
    # Her iki yonu de kontrol et
    fiyat_str = ""
    sym = parsed.get("sym", "")
    fiyat = mexc_get_mark_price(sym) if sym else None
    if not fiyat:
        return "⚠️ {} fiyati alinamadi.".format(sym)

    dec = 6 if fiyat < 0.01 else (5 if fiyat < 0.1 else (4 if fiyat < 1 else (2 if fiyat < 10 else (1 if fiyat < 100 else 0))))
    def p(v): return "{:,.{}f}".format(v, dec)

    baslik = ("📊 <b>" + sym + " — Skor Kontrolu</b>\n"
              "💰 Anlik Fiyat: <b>" + p(fiyat) + "</b>\n"
              "🕐 Son 24 saatlik mumlar\n")

    # Her iki yonu isleme
    parcalar = []
    for yon_key, satilar_key in [("yon", "satirlar"), ("yon2", "satirlar2")]:
        yon = parsed.get(yon_key)
        satirlar = parsed.get(satilar_key, [])
        if yon and satirlar:
            from functools import partial
            blok = _blok_kontrol_fn(sym, fiyat, dec, satirlar, yon)
            parcalar += blok
            parcalar += [""]

    if not parcalar:
        return None
    return baslik + "\n" + "\n".join(parcalar)


def _blok_kontrol_fn(sym, fiyat, dec, satirlar, yon):
    """Skor blok kontrolu — _olta_skor_kontrol icindeki _blok_kontrol'un bagimsiz versiyonu."""
    def p(v): return "{:,.{}f}".format(v, dec)
    yon_etiket = "🟢 <b>LONG</b>" if yon == "long" else "🔴 <b>SHORT</b>"
    cikti = [yon_etiket]
    limit_map = {"5m": 288, "15m": 96, "1h": 72, "4h": 52, "1d": 52}
    tf_label = {"5m":"5dk ","15m":"15dk","1h":"1s  ","4h":"4s  ","1d":"Gun "}
    for s in satirlar:
        tf = s.get("tf",""); iv = s.get("iv","15m")
        giris = s.get("giris",0); sl = s.get("sl",0)
        tp1 = s.get("tp1",0); tp2 = s.get("tp2")
        lbl = tf_label.get(iv, tf)
        etiket = "{} - {}".format(lbl, int(giris))
        limit = limit_map.get(iv, 96)
        closes, volumes, highs, lows = _skor_klines_cek(sym, iv, limit)
        if not closes:
            cikti.append("  {} ⚠️ veri alinamadi".format(etiket))
            continue
        min_low = min(lows); max_high = max(highs)
        giris_ulasildi = (min_low <= giris) if yon == "long" else (max_high >= giris)
        if not giris_ulasildi:
            cikti.append("  {} ⏳".format(etiket))
            continue
        if yon == "long":
            tp1_hit = max_high >= tp1
            tp2_hit = bool(tp2) and max_high >= tp2
            sl_hit  = min_low <= sl
        else:
            tp1_hit = min_low <= tp1
            tp2_hit = bool(tp2) and min_low <= tp2
            sl_hit  = max_high >= sl
        if sl_hit and not tp1_hit:
            cikti.append("  {} ❌".format(etiket))
        elif tp2_hit:
            cikti.append("  {} ✅ TP1 TP2".format(etiket))
        elif tp1_hit:
            cikti.append("  {} ✅ TP1".format(etiket))
        else:
            cikti.append("  {} ⏳".format(etiket))
    return cikti


def _olta_skor_kontrol(metin, cache_ts=None):
    """
    Alintilanan olta mesajini parse edip son 24 saatlik mumlarla kontrol eder.
    Iki format: eski (BTC) ve tablo (BTC TUM).
    cache_ts: Olta verilisinin Unix timestamp - zaman damgasi icin.
    """
    parsed = _olta_skor_parse(metin)
    if not parsed:
        return None  # Cache fallback icin None don
    if cache_ts:
        parsed["ts"] = cache_ts

    sym = parsed["sym"]
    fmt = parsed.get("format", "tablo")

    fiyat = mexc_get_mark_price(sym)
    if not fiyat:
        return "⚠️ {} fiyatı alınamadı.".format(sym)

    dec = 6 if fiyat < 0.01 else (5 if fiyat < 0.1 else (4 if fiyat < 1 else (2 if fiyat < 10 else (1 if fiyat < 100 else 0))))
    def p(v): return "{:,.{}f}".format(v, dec)

    def _blok_kontrol(satirlar, yon, since_ts=None):
        yon_etiket = "🟢 <b>LONG</b>" if yon == "long" else "🔴 <b>SHORT</b>"
        cikti = [yon_etiket]
        import time as _t
        if since_ts:
            gecen_sn = max(int(_t.time()) - since_ts, 300)
            # Minimum limit: her TF icin en az 3 mum garantile
            # since_ts cok yakinsa bile yeterli veri gelsin
            limit_map = {
                "5m":  max(min(int(gecen_sn/300)+2,  500), 10),
                "15m": max(min(int(gecen_sn/900)+2,  200), 6),
                "1h":  max(min(int(gecen_sn/3600)+2, 100), 3),
                "4h":  max(min(int(gecen_sn/14400)+2, 60), 3),
                "1d":  max(min(int(gecen_sn/86400)+2, 30), 3),
            }
        else:
            limit_map = {"5m": 288, "15m": 96, "1h": 72, "4h": 52, "1d": 52}
        for s in satirlar:
            tf = s["tf"]; iv = s["iv"]
            giris = s["giris"]; sl = s["sl"]
            tp1 = s["tp1"]; tp2 = s["tp2"]
            tf_label = {"5m":"5dk ","15m":"15dk","1h":"1s  ","4h":"4s  ","1d":"Gün "}.get(iv, iv)
            etiket = "{} - {}".format(tf_label, int(giris))
            limit = limit_map.get(iv, 96)
            closes, volumes, highs, lows = _skor_klines_cek(sym, iv, limit)
            if not closes:
                cikti.append("  {} \u26a0\ufe0f veri alınamadı".format(etiket))
                continue
            min_low = min(lows); max_high = max(highs)
            giris_ulasildi = (min_low <= giris) if yon == "long" else (max_high >= giris)
            if not giris_ulasildi:
                uzaklik = abs(fiyat - giris) / fiyat * 100
                cikti.append("  {} \u23f3".format(etiket))  # Bekleniyor
                continue
            if yon == "long":
                tp1_hit = max_high >= tp1
                tp2_hit = bool(tp2) and max_high >= tp2
                sl_hit  = min_low <= sl
            else:
                tp1_hit = min_low <= tp1
                tp2_hit = bool(tp2) and min_low <= tp2
                sl_hit  = max_high >= sl
            if sl_hit and not tp1_hit:
                cikti.append("  {} \u274c".format(etiket))
            elif tp2_hit:
                cikti.append("  {} \u2705 TP1 TP2".format(etiket))
            elif tp1_hit:
                cikti.append("  {} \u2705 TP1".format(etiket))
            else:
                cikti.append("  {} \u23f3".format(etiket))
        return cikti

    # since_ts: olta verildiği andan itibaren mumları getir
    # ts cache'de tutuluyor, parsed dict'te değil — cache'den al
    since_ts = parsed.get("ts")
    if not since_ts:
        # Cache'den sym'e göre doğru ts'yi bul
        for topic_id, cache_data in _son_olta_cache.items():
            if cache_data.get("ts"):
                # Dogru sym'in cache'i mi kontrol et
                cache_sym = None
                for msg_key in ["long_msg", "short_msg", "metin"]:
                    msg_val = cache_data.get(msg_key, "")
                    if sym and sym in msg_val:
                        cache_sym = sym
                        break
                if cache_sym:
                    since_ts = cache_data["ts"]
                    break
    if since_ts:
        gecen_sn = int(time.time()) - since_ts
        if gecen_sn < 3600:
            zaman_str = f"{gecen_sn // 60} dk \u00f6nce"
        else:
            h = gecen_sn // 3600; m = (gecen_sn % 3600) // 60
            zaman_str = f"{h}s {m}dk \u00f6nce"
    else:
        zaman_str = "son 24 saat"

    baslik = ("\U0001f4ca <b>" + sym + " \u2014 Skor Kontrolü</b>\n"
              "\U0001f4b0 Anlık Fiyat: <b>" + p(fiyat) + "</b>\n"
              "\U0001f550 Olta verileli: " + zaman_str + "\n")

    if fmt == "tablo":
        yon = parsed["yon"]
        cikti = _blok_kontrol(parsed["satirlar"], yon, since_ts=since_ts)
        return baslik + "\n" + "\n".join(cikti)
    else:
        parcalar = []
        if parsed.get("satirlar"):
            parcalar += _blok_kontrol(parsed["satirlar"], parsed["yon"], since_ts=since_ts)
        if parsed.get("satirlar2"):
            parcalar += [""]
            parcalar += _blok_kontrol(parsed["satirlar2"], parsed["yon2"], since_ts=since_ts)
        return baslik + "\n" + "\n".join(parcalar)

def _olta_mtf_sorgula(symbol_raw):
    """
    Multi-timeframe Fibonacci olta: 5dk/15dk/1s/4s/Gun
    Kullanici "BTC TUM" yazinca cagrilir.
    Long icin ayri, Short icin ayri 2 mesaj doner.
    """
    import concurrent.futures
    sym = symbol_raw.strip().upper()
    if not sym.endswith("USDT"):
        sym = sym + "USDT"

    fiyat = mexc_get_mark_price(sym)
    if not fiyat or fiyat <= 0:
        err = "\u26a0\ufe0f <b>{}</b> icin fiyat alinamadi.".format(sym)
        return err, err

    dec = 6 if fiyat < 0.01 else (5 if fiyat < 0.1 else (4 if fiyat < 1 else (2 if fiyat < 10 else (1 if fiyat < 100 else 0))))

    def p(v):
        return "{:,.{}f}".format(v, dec)

    TF_LIST = [
        ("5dk",  "5m",  200),
        ("15dk", "15m", 220),
        ("1s",   "1h",  100),
        ("4s",   "4h",  80),
        ("Gun",  "1d",  60),
    ]

    results = {}

    def _cek(label, interval, limit):
        try:
            closes, volumes, highs, lows = _trend_fetch_klines(sym, interval=interval, limit=limit)
            r = _olta_fib_hesapla(closes, highs, lows, fiyat, interval)
            return label, r
        except Exception as e:
            print("[OLTA-MTF] {} {} hata: {}".format(sym, label, e))
            return label, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(_cek, lbl, iv, lim) for lbl, iv, lim in TF_LIST]
        for fut in concurrent.futures.as_completed(futures):
            lbl, r = fut.result()
            results[lbl] = r

    # Hizalama: BTC icin 6 char, diger fiyatlar icin 7 char
    # Toplam: 4 + 1 + 6 + 1 + 6 + 1 + 6 + 1 + 6 = 32 (BTC) veya 4+1+7+1+7+1+7+1+7=36 (ETH)
    # Ikisi de Telegram monospace'de tek satirda sigacak sekilde
    if dec == 0:
        # BTC gibi tam sayi — 6 karakter (max 6 rakam)
        def q(v): return "{:>6,.0f}".format(v).replace(",", ".")
        w = 6
    else:
        # ETH, SOL, XRP gibi ondalikli — 6 karakter (3 tam + . + 2 ondalik)
        def q(v): return "{:>6,.{}f}".format(v, min(dec, 3)).replace(",", ".")
        w = 6

    fmt      = "{{:<5}} {{:>{}}} {{:>{}}} {{:>{}}} {{:>{}}}".format(w, w, w, w)
    baslik   = fmt.format("TF", "Giris", "Stop", "TP1", "TP2")
    ayrac    = "-" * len(baslik)

    def satir(lbl, r, side):
        if not r:
            return fmt.format(lbl, "-", "-", "-", "-")
        if side == "long":
            yakin = abs(r["long_giris"] - fiyat) / fiyat < 0.005
            isaret = " ◉" if yakin else ""
            return fmt.format(lbl, q(r["long_giris"]), q(r["long_sl"]),
                              q(r["long_tp1"]), q(r["long_tp2"])) + isaret
        else:
            yakin = abs(r["short_giris"] - fiyat) / fiyat < 0.005
            isaret = " ◉" if yakin else ""
            return fmt.format(lbl, q(r["short_giris"]), q(r["short_sl"]),
                              q(r["short_tp1"]), q(r["short_tp2"])) + isaret

    long_satirlar  = [satir(lbl, results.get(lbl), "long")  for lbl, _, _ in TF_LIST]
    short_satirlar = [satir(lbl, results.get(lbl), "short") for lbl, _, _ in TF_LIST]

    cikti_aciklama = "\n◉ Fiyat giriş bölgesinde" if any("◉" in s for s in long_satirlar) else ""
    long_msg  = ("\U0001f7e2 <b>" + sym + " \u2014 LONG OLTALAR</b>\n"
                 "\U0001f4b0 Anlik Fiyat: <b>" + p(fiyat) + "</b>\n"
                 "<pre>" + baslik + "\n" + ayrac + "\n"
                 + "\n".join(long_satirlar) + "</pre>"
                 + cikti_aciklama)

    cikti_aciklama_s = "\n◉ Fiyat giriş bölgesinde" if any("◉" in s for s in short_satirlar) else ""
    short_msg = ("\U0001f534 <b>" + sym + " \u2014 SHORT OLTALAR</b>\n"
                 "\U0001f4b0 Anlik Fiyat: <b>" + p(fiyat) + "</b>\n"
                 "<pre>" + baslik + "\n" + ayrac + "\n"
                 + "\n".join(short_satirlar) + "</pre>"
                 + cikti_aciklama_s)

    return long_msg, short_msg


def _olta_ver_tablo():
    """
    BTC, ETH, SOL, XRP icin tum TF'leri paralel ceker.
    LONG ve SHORT icin Pillow ile gorsel PNG uretir, bytes olarak doner.
    """
    import concurrent.futures, io
    from PIL import Image, ImageDraw, ImageFont

    COINS   = ["BTC", "ETH", "SOL", "XRP"]
    TF_LIST = [("5DK","5m",200),("15DK","15m",220),("1SA","1h",100),("4SA","4h",80),("GUN","1d",60)]

    fiyatlar     = {}
    tum_sonuclar = {}

    def _cek(coin, lbl, iv, lim):
        sym = coin + "USDT"
        try:
            f = mexc_get_mark_price(sym)
            if not f or f <= 0:
                return coin, lbl, None, None
            closes, volumes, highs, lows = _trend_fetch_klines(sym, interval=iv, limit=lim)
            r = _olta_fib_hesapla(closes, highs, lows, f, iv)
            return coin, lbl, f, r
        except Exception as e:
            print(f"[OLTA-VER] {coin} {lbl} hata: {e}")
            return coin, lbl, None, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futs = [ex.submit(_cek, c, lbl, iv, lim) for c in COINS for lbl, iv, lim in TF_LIST]
        for fut in concurrent.futures.as_completed(futs):
            coin, lbl, f, r = fut.result()
            if f and coin not in fiyatlar:
                fiyatlar[coin] = f
            tum_sonuclar.setdefault(coin, {})[lbl] = r

    # Zaman
    try:
        import pytz as _pytz
        _TR = _pytz.timezone("Europe/Istanbul")
        from datetime import datetime as _dt
        zaman = _dt.now(tz=_TR).strftime("%d %b %Y  %H:%M")
    except Exception:
        from datetime import datetime as _dt
        zaman = _dt.utcnow().strftime("%d %b %Y  %H:%M UTC")

    def fmt_val(coin, val):
        if val is None: return "---"
        f = fiyatlar.get(coin, 1)
        dec = 0 if f>=100 else (1 if f>=10 else (2 if f>=1 else (4 if f>=0.1 else 6)))
        try:
            return "{:,.{}f}".format(val, dec).replace(",", ".")
        except Exception:
            return "---"

    def yakin_mi(coin, val, esik=0.008):
        f = fiyatlar.get(coin)
        if not f: return False
        return abs(val - f) / f < esik

    def footer_ozet(side):
        coinler = []
        for lbl, _, _ in TF_LIST:
            for c in COINS:
                r = tum_sonuclar.get(c, {}).get(lbl)
                giris = r.get("long_giris" if side=="long" else "short_giris") if r else None
                if giris and yakin_mi(c, giris) and c not in coinler:
                    coinler.append(c)
        if not coinler:
            return None
        if len(coinler) == 1:
            return f"\u25cf {coinler[0]} i\u00e7in verilen baz\u0131 olta yerlerinde fiyat giri\u015f b\u00f6lgesinde."
        else:
            return f"\u25cf {', '.join(coinler[:-1])} ve {coinler[-1]} i\u00e7in verilen baz\u0131 olta yerlerinde fiyat giri\u015f b\u00f6lgesinde."

    # ── Gorsel uret ──────────────────────────────────────────────────
    FONT_PATH      = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
    FONT_BOLD_PATH = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"

    BG=(15,17,22); PANEL_BG=(22,26,35); BORDER=(40,46,60)
    HEADER_BG=(28,34,48); AYRAC_COL=(45,52,68)
    COL_WHITE=(255,255,255); COL_GRAY=(110,118,135); COL_GOLD=(255,198,80)
    COL_GREEN=(72,199,142); COL_RED=(255,90,90); COL_CYAN=(100,210,220)
    COL_ORANGE=(255,155,50)

    def _ciz(side):
        FONT_SZ=17; BOLD_SZ=18; TITLE_SZ=22
        PAD_X=36; PAD_Y=30; ROW_H=27; TF_GAP=12; HDR_H=52

        try:
            font      = ImageFont.truetype(FONT_PATH,      FONT_SZ)
            font_bold = ImageFont.truetype(FONT_BOLD_PATH, BOLD_SZ)
            font_tf   = ImageFont.truetype(FONT_BOLD_PATH, FONT_SZ)
            font_title= ImageFont.truetype(FONT_BOLD_PATH, TITLE_SZ)
            font_note = ImageFont.truetype(FONT_PATH,      15)
            font_small= ImageFont.truetype(FONT_PATH,      13)
        except Exception:
            font=font_bold=font_tf=font_title=font_note=font_small=ImageFont.load_default()

        tmp=Image.new("RGB",(1,1)); td=ImageDraw.Draw(tmp)

        TF_W=68; VERI_W=58; COIN_W=100; GAP=12
        cols=["TF","VERİ"]+COINS
        col_x={}; col_w={}; x=0
        for c in cols:
            col_x[c]=x
            col_w[c]=TF_W if c=="TF" else VERI_W if c=="VERİ" else COIN_W
            x+=col_w[c]+GAP
        total_w=int(x-GAP)

        ozet=footer_ozet(side)
        FOOTER_H=58
        TITLE_H=PAD_Y+38+24+14
        TABLE_H=HDR_H+8+4*len(TF_LIST)*ROW_H+(len(TF_LIST)-1)*TF_GAP+18
        IMG_W=int(total_w+PAD_X*2)
        IMG_H=TITLE_H+TABLE_H+FOOTER_H

        img=Image.new("RGB",(IMG_W,IMG_H),BG)
        d=ImageDraw.Draw(img)

        title_col=COL_GREEN if side=="long" else COL_RED
        title_txt="LONG OLTALAR — Tüm Coinler" if side=="long" else "SHORT OLTALAR — Tüm Coinler"

        d.rectangle([(0,0),(5,IMG_H)],fill=title_col)
        ty=PAD_Y

        tw=td.textlength(title_txt,font=font_title)
        d.text(((IMG_W-tw)/2,ty),title_txt,font=font_title,fill=title_col)
        ty+=38

        zw=td.textlength(zaman,font=font_note)
        d.text(((IMG_W-zw)/2,ty),zaman,font=font_note,fill=COL_ORANGE)
        ty+=24

        d.rectangle([(PAD_X,ty),(PAD_X+total_w,ty+1)],fill=BORDER)
        ty+=14

        d.rectangle([(PAD_X-6,ty-4),(PAD_X+total_w+6,ty+HDR_H+4)],fill=HEADER_BG)
        for c in cols:
            cx=PAD_X+col_x[c]; cw=col_w[c]
            if c in ("TF","VERİ"):
                lw=td.textlength(c,font=font_bold)
                d.text((cx+(cw-lw)/2,ty+(HDR_H-BOLD_SZ)//2),c,font=font_bold,fill=COL_WHITE)
            else:
                lw=td.textlength(c,font=font_bold)
                d.text((cx+(cw-lw)/2,ty+4),c,font=font_bold,fill=COL_WHITE)
                fstr=fmt_val(c,fiyatlar.get(c))
                fstr_p=f"({fstr})" if fstr!="---" else ""
                if fstr_p:
                    fw=td.textlength(fstr_p,font=font_small)
                    d.text((cx+(cw-fw)/2,ty+28),fstr_p,font=font_small,fill=COL_WHITE)
        ty+=HDR_H+4

        d.rectangle([(PAD_X,ty),(PAD_X+total_w,ty+1)],fill=AYRAC_COL)
        ty+=8

        VERI_LABELS=["GİRİŞ","SL","TP1","TP2"]
        KEYS_LONG  =["long_giris","long_sl","long_tp1","long_tp2"]
        KEYS_SHORT =["short_giris","short_sl","short_tp1","short_tp2"]

        for tf_i,(lbl,_,_) in enumerate(TF_LIST):
            gb=ty
            for vi,vd in enumerate(VERI_LABELS):
                row_bg=(24,29,40) if vi%2==0 else PANEL_BG
                d.rectangle([(PAD_X-6,ty-2),(PAD_X+total_w+6,ty+ROW_H-2)],fill=row_bg)
                vcol=COL_GOLD if vd=="GİRİŞ" else COL_RED if vd=="SL" else COL_GREEN

                vc=PAD_X+col_x["VERİ"]; vcw=col_w["VERİ"]
                vlw=td.textlength(vd,font=font)
                d.text((vc+(vcw-vlw)/2,ty+4),vd,font=font,fill=vcol)

                key=KEYS_LONG[vi] if side=="long" else KEYS_SHORT[vi]
                for c in COINS:
                    r=tum_sonuclar.get(c,{}).get(lbl)
                    val=r.get(key) if r else None
                    cx=PAD_X+col_x[c]; cw=col_w[c]
                    s=fmt_val(c,val)
                    sw=td.textlength(s,font=font)
                    d.text((cx+(cw-sw)/2,ty+4),s,font=font,fill=vcol)
                    if vd=="GİRİŞ" and val and yakin_mi(c,val):
                        d.text((cx+(cw+sw)/2+3,ty+4),"●",font=font,fill=COL_GOLD)
                ty+=ROW_H

            tf_lw=td.textlength(lbl,font=font_tf)
            tf_ty=gb+(4*ROW_H-FONT_SZ)//2
            d.text((PAD_X+col_x["TF"]+(TF_W-tf_lw)/2,tf_ty),lbl,font=font_tf,fill=COL_CYAN)

            if tf_i<len(TF_LIST)-1:
                d.rectangle([(PAD_X,ty+3),(PAD_X+total_w,ty+4)],fill=(32,38,52))
                ty+=TF_GAP

        ty+=18
        d.rectangle([(PAD_X,ty),(PAD_X+total_w,ty+1)],fill=BORDER)
        ty+=12

        txt=ozet if ozet else "● Fiyat giriş bölgesinde olan coin yok"
        col=COL_GOLD if ozet else COL_GRAY
        kelimeler=txt.split(); satirlar=[]; mevcut=""
        for k in kelimeler:
            test=(mevcut+" "+k).strip()
            if td.textlength(test,font=font_note)<=total_w: mevcut=test
            else:
                if mevcut: satirlar.append(mevcut)
                mevcut=k
        if mevcut: satirlar.append(mevcut)
        for s in satirlar:
            sw=td.textlength(s,font=font_note)
            d.text(((IMG_W-sw)/2,ty),s,font=font_note,fill=col)
            ty+=20

        buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
        return buf.read()

    long_bytes  = _ciz("long")
    short_bytes = _ciz("short")
    return long_bytes, short_bytes



def _olta_sorgula(symbol_raw):
    """
    Kullanıcı bir parite yazdığında çağrılır.
    Anlık fiyat + long/short olta seviyelerini hesaplayıp metin döner.

    Öncelik:
    1. _son_analiz_veriler cache'i varsa → _analiz_olta_seviyeleri (analiz görseli ile aynı veri)
    2. Cache yoksa → 15dk OHLCV'den EMA + swing high/low hesapla
    """
    # Sembol normalize: btc → BTCUSDT, btcusdt → BTCUSDT
    sym = symbol_raw.strip().upper()
    if not sym.endswith("USDT"):
        sym = sym + "USDT"

    # 1) Anlık fiyat
    fiyat = mexc_get_mark_price(sym)
    if not fiyat or fiyat <= 0:
        return f"⚠️ <b>{sym}</b> için fiyat alınamadı."

    dec = 6 if fiyat < 0.1 else (4 if fiyat < 1 else (2 if fiyat < 10 else (1 if fiyat < 100 else 0)))

    def p(val):
        return f"{val:,.{dec}f}"

    # 2) Cache'den veri al
    global _son_analiz_veriler
    veri_cache = _son_analiz_veriler.get(sym) if _son_analiz_veriler else None

    if veri_cache:
        # ── Cache var: destek/direnç/EMA cache'den, fiyat anlık ──
        print(f"[OLTA] {sym} cache verisi kullanılıyor (anlık fiyat: {fiyat}).")
        # Fiyatı güncelle — olta seviyeleri anlık fiyata göre hesaplansın
        veri_guncel = dict(veri_cache)
        veri_guncel["fiyat"] = fiyat
        olta = _analiz_olta_seviyeleri(sym, veri_guncel)

        # 24s high/low cache'den
        high_24h = veri_cache.get("high_24h", fiyat * 1.02)
        low_24h  = veri_cache.get("low_24h",  fiyat * 0.98)
        ema20    = veri_cache.get("ema20", 0)
        ema50    = veri_cache.get("ema50", 0)
        destek   = veri_cache.get("destek") or []
        direnc   = veri_cache.get("direnc") or []

    else:
        # ── Cache yok: OHLCV'den hesapla ──
        print(f"[OLTA] {sym} cache yok, OHLCV hesaplanıyor.")
        try:
            closes, volumes, highs, lows = _trend_fetch_klines(sym, interval="15m", limit=220)
        except Exception as e:
            return f"⚠️ <b>{sym}</b> için OHLCV verisi alınamadı: {e}"

        if not closes or len(closes) < 50:
            return f"⚠️ <b>{sym}</b> için yeterli veri yok."

        def ema(data, period):
            k = 2 / (period + 1)
            e = data[0]
            for v in data[1:]:
                e = v * k + e * (1 - k)
            return e

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        high_24h = max(highs[-96:]) if len(highs) >= 96 else max(highs)
        low_24h  = min(lows[-96:])  if len(lows)  >= 96 else min(lows)

        # Swing high/low → destek/direnç
        rh = highs[-50:]; rl = lows[-50:]
        direnc_raw = [rh[i] for i in range(2, len(rh)-2)
                      if rh[i] > rh[i-1] and rh[i] > rh[i+1]
                      and rh[i] > rh[i-2] and rh[i] > rh[i+2]]
        destek_raw = [rl[i] for i in range(2, len(rl)-2)
                      if rl[i] < rl[i-1] and rl[i] < rl[i+1]
                      and rl[i] < rl[i-2] and rl[i] < rl[i+2]]

        direnc = sorted([d for d in direnc_raw if d > fiyat])[:3]
        destek = sorted([d for d in destek_raw if d < fiyat], reverse=True)[:3]

        # Sahte veri dict oluştur → _analiz_olta_seviyeleri'ne ver
        veri_fake = {
            "fiyat": fiyat, "ema20": ema20, "ema50": ema50,
            "destek": destek, "direnc": direnc,
            "high_24h": high_24h, "low_24h": low_24h,
            "skor": 50, "funding": 0,
        }
        olta = _analiz_olta_seviyeleri(sym, veri_fake)

    # 3) Mesaj formatı
    mesaj = (
        f"🎣 <b>{sym}</b>\n"
        f"💰 Anlık Fiyat: <b>{p(fiyat)}</b>\n"
        f"📊 24s: ↑{p(high_24h)} ↓{p(low_24h)}\n"
        f"📈 EMA20: {p(ema20)}  EMA50: {p(ema50)}\n"
        f"\n"
        f"🟢 <b>LONG OLTA</b>\n"
        f"  Giriş: {p(olta['long_giris_alt'])} – {p(olta['long_giris_ust'])}\n"
        f"  Stop:  {p(olta['long_stop'])}\n"
        f"  TP1:   {p(olta['long_tp1'])}\n"
        f"  TP2:   {p(olta['long_tp2'])}\n"
        f"\n"
        f"🔴 <b>SHORT OLTA</b>\n"
        f"  Giriş: {p(olta['short_giris'])}\n"
        f"  Stop:  {p(olta['short_stop'])}\n"
        f"  TP:    {p(olta['short_tp'])}\n"
    )

    destek_goster = [d for d in (destek if isinstance(destek, list) else []) if d < fiyat][:3]
    direnc_goster = [r for r in (direnc if isinstance(direnc, list) else []) if r > fiyat][:3]
    if destek_goster:
        mesaj += f"\n🛡 Destek: {' / '.join(p(d) for d in destek_goster)}"
    if direnc_goster:
        mesaj += f"\n🧱 Direnç: {' / '.join(p(r) for r in direnc_goster)}"
    if olta.get("senaryo_notu"):
        mesaj += f"\n💡 {olta['senaryo_notu']}"

    return mesaj


def _analiz_olta_seviyeleri(sym, veri):
    """
    BTC/ETH/SOL için long/short olta seviyeleri hesapla.
    Dönen dict: long_giris, long_stop, long_tp1, long_tp2,
                short_giris, short_stop, short_tp, senaryo_notu
    """
    fiyat   = veri.get("fiyat", 0)
    ema20   = veri.get("ema20", 0)
    ema50   = veri.get("ema50", 0)
    destek  = veri.get("destek")   # [d1, d2, d3]
    direnc  = veri.get("direnc")   # [r1, r2, r3]
    skor    = veri.get("skor", 50)
    cvd     = veri.get("cvd")
    taker   = veri.get("taker")
    lik     = veri.get("likidasyonlar")
    high_24h = veri.get("high_24h", fiyat * 1.02)
    low_24h  = veri.get("low_24h",  fiyat * 0.98)
    fund    = veri.get("funding", 0)

    dec = 6 if fiyat < 0.01 else (5 if fiyat < 0.1 else (4 if fiyat < 1 else (2 if fiyat < 10 else (1 if fiyat < 100 else 0))))

    # ── Long Giriş ──
    # Mutlaka fiyatın ALTINDA bir seviye — destek veya EMA20 (hangisi alttaysa)
    long_candidates = []
    if ema20 and ema20 < fiyat * 1.001:  # %0.1 tolerans — fiyata çok yakın EMA20 de geçerli
        long_candidates.append(ema20)
    if destek:
        for d in destek:
            if d and d < fiyat:
                long_candidates.append(d)

    if long_candidates:
        # Fiyata en yakın ama altındaki seviye
        long_ref = max(long_candidates)
    else:
        # Fallback: fiyatın %1.5 altı
        long_ref = fiyat * 0.985

    long_giris_ust = round(long_ref * 1.003, dec)
    long_giris_alt = round(long_ref * 0.997, dec)
    long_stop      = round(long_ref * 0.988, dec)

    # Giriş aralığı fiyatın üstüne taşmışsa aşağı çek
    if long_giris_ust >= fiyat:
        long_giris_ust = round(fiyat * 0.999, dec)
    if long_giris_alt >= long_giris_ust:
        long_giris_alt = round(long_giris_ust * 0.994, dec)
    if long_stop >= long_giris_alt:
        long_stop = round(long_giris_alt * 0.988, dec)

    # TP1 = fiyatın üzerindeki en yakın direnç, TP2 = ondan uzak olan
    direnc_ust = [r for r in (direnc or []) if r and r > fiyat]
    direnc_ust.sort()
    if len(direnc_ust) >= 2:
        long_tp1 = round(direnc_ust[0], dec)
        long_tp2 = round(direnc_ust[1], dec)
    elif len(direnc_ust) == 1:
        long_tp1 = round(direnc_ust[0], dec)
        long_tp2 = round(fiyat * 1.025, dec)
    else:
        long_tp1 = round(fiyat * 1.015, dec)
        long_tp2 = round(fiyat * 1.030, dec)

    # TP1 ve TP2 aynıysa (yuvarlama nedeniyle) TP2'yi %1.5 daha yukarı koy
    if long_tp1 == long_tp2:
        long_tp2 = round(long_tp1 * 1.015, dec)

    # TP1 fiyata çok yakınsa veya altındaysa fallback — en az %0.8 yukarı
    if long_tp1 <= fiyat * 1.003:
        long_tp1 = round(fiyat * 1.012, dec)
    if long_tp2 <= long_tp1 * 1.003:
        long_tp2 = round(long_tp1 * 1.020, dec)

    # ── Short Giriş ──
    # Mutlaka fiyatın ÜSTÜNDE bir direnç seviyesi — en az %0.5 uzak
    direnc_ust_short = [r for r in (direnc or []) if r and r > fiyat * 1.003]
    direnc_ust_short.sort()
    if direnc_ust_short:
        short_ref = direnc_ust_short[0]
    else:
        short_ref = high_24h if high_24h > fiyat * 1.005 else fiyat * 1.015

    short_giris = round(short_ref * 0.999, dec)
    short_stop  = round(short_ref * 1.012, dec)

    # Short TP = fiyatın altındaki en yakın destek — en az %0.5 uzak
    destek_alt = [d for d in (destek or []) if d and d < fiyat * 0.997]
    destek_alt.sort(reverse=True)
    if destek_alt:
        short_tp = round(destek_alt[0], dec)
    else:
        short_tp = round(fiyat * 0.975, dec)

    # Short TP fiyata çok yakınsa veya üstündeyse fallback
    if short_tp >= fiyat * 0.997:
        short_tp = round(fiyat * 0.975, dec)

    # ── Senaryo notu ──
    notlar = []

    # CVD uyumsuzluğu
    if cvd:
        if cvd["uyum"] == "uyumsuz_yukari":
            notlar.append("CVD uyumsuz — fiyat ↑ CVD ↓, long dikkatli")
        elif cvd["uyum"] == "uyumsuz_asagi":
            notlar.append("CVD uyumsuz — fiyat ↓ CVD ↑, birikim var")

    # Funding aşırı pozitif → long girişte dikkat
    if fund > 0.03:
        notlar.append("Funding yüksek, long maliyetli")
    elif fund < -0.03:
        notlar.append("Funding negatif, short maliyetli")

    # Likidasyon ağırlığı
    if lik:
        if lik["agirlik"] == "short_baskin":
            notlar.append(f"Son 30dk {lik['short_usd']}M short ezildi — güç sinyali")
        elif lik["agirlik"] == "long_baskin":
            notlar.append(f"Son 30dk {lik['long_usd']}M long ezildi — dikkat")

    # Taker
    if taker:
        if taker["sinyal"] == "guclu_alis":
            notlar.append(f"Taker %{taker['taker_buy_pct']} alıcı — güçlü akış")
        elif taker["sinyal"] == "guclu_satis":
            notlar.append(f"Taker %{taker['taker_buy_pct']} alıcı — satıcı baskısı")

    senaryo_notu = " · ".join(notlar) if notlar else ""

    return {
        "long_giris_alt": long_giris_alt,
        "long_giris_ust": long_giris_ust,
        "long_stop":      long_stop,
        "long_tp1":       long_tp1,
        "long_tp2":       long_tp2,
        "short_giris":    short_giris,
        "short_stop":     short_stop,
        "short_tp":       short_tp,
        "senaryo_notu":   senaryo_notu,
    }


def _analiz_gorsel(veriler, zaman_str):
    """
    Genişletilmiş Piyasa Analizi görseli üret — matplotlib.
    Üst: 4 metrik kart + breadth + CVD kart
    Orta: 10 coin tablo (11 sütun)
    Alt: BTC / ETH / SOL olta paneli
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch
        import numpy as np
        import io

        # Matplotlib math parser'ı kapat — $ işareti LaTeX olarak parse edilmesin
        import matplotlib as mpl
        mpl.rcParams["text.usetex"] = False
        mpl.rcParams["mathtext.default"] = "regular"
        plt.rcParams["text.usetex"] = False

        BG      = "#0A0E1A"
        CARD    = "#111827"
        CARD2   = "#0D1120"
        BORDER  = "#1E2D4A"
        WHITE   = "#FFFFFF"
        GRAY    = "#9CA3AF"
        DGRAY   = "#6B7280"
        GREEN   = "#4CAF50"
        LGREEN  = "#8BC34A"
        ORANGE  = "#FF9800"
        RED     = "#F44336"
        GOLD    = "#C9A84C"

        def renk_skor(s):
            if s >= 75: return GREEN
            if s >= 55: return LGREEN
            if s >= 40: return GRAY
            if s >= 25: return ORANGE
            return RED

        def renk_pct(v):
            if v is None: return GRAY
            return GREEN if v > 0 else (RED if v < 0 else GRAY)

        def fmt_fiyat(f):
            if f is None: return "—"
            try:
                f = float(f)
            except (TypeError, ValueError):
                return str(f) if f else "—"
            if f >= 10000: return f"USD {f:,.0f}"
            if f >= 100:   return f"USD {f:,.0f}"
            if f >= 1:     return f"USD {f:.3f}"
            return f"USD {f:.5f}"

        def fmt_para(v):
            if v is None: return "—"
            if abs(v) >= 1000: return f"USD {v/1000:.1f}B"
            return f"USD {v:.1f}M"

        SEMBOLLER = [
            "BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
            "DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT"
        ]

        # Figür boyutu — olta paneli kaldırıldı
        fig_w = 11.13
        fig_h = 10.0
        matplotlib.rcParams['text.usetex'] = False
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        ax.set_xlim(0, fig_w); ax.set_ylim(0, fig_h)
        ax.axis("off")
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)

        y = fig_h - 0.15

        # ── BAŞLIK ──
        ax.text(fig_w / 2, y, "BEN KÜL YUTMAM",
                ha="center", va="top", fontsize=12, color=WHITE, fontweight="bold")
        y -= 0.28
        ax.text(fig_w / 2, y, "GENİŞLETİLMİŞ PİYASA ANALİZİ",
                ha="center", va="top", fontsize=18, color=WHITE, fontweight="bold")
        y -= 0.32
        ax.text(fig_w / 2, y, f"{zaman_str}  ·  Binance Futures + Spot  ·  @dayiscalper",
                ha="center", va="top", fontsize=10, color=GRAY, fontweight="bold")
        y -= 0.16
        ax.axhline(y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.8)
        y -= 0.14

        # ── ÜST METRİK KARTLAR (6 adet) ──
        # Piyasa skoru, F&G, BTC Dom, Breadth, BTC CVD, BTC Funding
        coin_verileri = {s: veriler.get(s, {}) for s in SEMBOLLER}
        skorlar = [v.get("skor", 0) for v in coin_verileri.values() if v.get("skor") is not None]
        ort_skor = round(sum(skorlar) / len(skorlar)) if skorlar else 0

        fg_deger, fg_sinif = _trend_fear_greed()
        btc_dom, _, _, _   = _trend_btc_dominans()
        breadth            = veriler.get("_breadth", 0)
        btc_cvd            = veriler.get("BTCUSDT", {}).get("cvd")
        btc_fund           = veriler.get("BTCUSDT", {}).get("funding", 0)

        def _fg_renk(v):
            if v is None: return GRAY
            if v >= 75: return GREEN
            if v >= 55: return LGREEN
            if v >= 45: return ORANGE
            if v >= 25: return ORANGE
            return RED

        kartlar = [
            ("PİYASA SKORU", str(ort_skor), renk_skor(ort_skor),
             "GÜÇLÜ YÜK." if ort_skor>=75 else ("YÜKSELİŞ" if ort_skor>=55 else
             ("NÖTR" if ort_skor>=40 else ("DÜŞÜŞ" if ort_skor>=25 else "GÜÇLÜ DÜŞ.")))),
            ("FEAR & GREED", str(fg_deger) if fg_deger else "—", _fg_renk(fg_deger),
             fg_sinif if fg_sinif else "—"),
            ("BTC DOM", f"%{btc_dom}" if btc_dom else "—", GOLD,
             "alt sezon yok" if btc_dom and btc_dom > 58 else ("dikkat" if btc_dom else "—")),
            ("MARKET BREADTH", f"{breadth}/10", GREEN if breadth >= 7 else (ORANGE if breadth >= 4 else RED),
             "EMA20 üstü"),
            ("BTC CVD (1H)", (f"+{btc_cvd['cvd']:.0f}" if btc_cvd and btc_cvd['cvd'] >= 0
                              else (f"{btc_cvd['cvd']:.0f}" if btc_cvd else "—")),
             (GREEN if btc_cvd and btc_cvd["uyum"] == "uyum" and btc_cvd["cvd"] >= 0
              else (ORANGE if btc_cvd and "uyumsuz" in btc_cvd["uyum"] else GRAY)),
             (btc_cvd["uyum"].replace("_", " ") if btc_cvd else "—")),
            ("BTC FUNDING", f"{btc_fund:+.4f}%" if btc_fund != 0 else "0.0000%",
             GREEN if btc_fund > 0.01 else (RED if btc_fund < -0.01 else GRAY),
             "long yığılması" if btc_fund > 0.01 else
             ("short yığılması" if btc_fund < -0.01 else "dengeli")),
        ]

        kart_w = fig_w / 6
        kart_h = 0.90
        for i, (lbl, val, col, sub) in enumerate(kartlar):
            kx = i * kart_w
            ax.add_patch(FancyBboxPatch(
                (kx + 0.08, y - kart_h + 0.06), kart_w - 0.16, kart_h - 0.08,
                boxstyle="round,pad=0.04", linewidth=0.6,
                edgecolor=BORDER, facecolor=CARD))
            ax.text(kx + kart_w/2, y - 0.16, lbl,
                    ha="center", va="top", fontsize=8, color=WHITE, fontweight="bold")
            ax.text(kx + kart_w/2, y - 0.50, val,
                    ha="center", va="top", fontsize=15, color=col, fontweight="bold")
            ax.text(kx + kart_w/2, y - 0.78, sub,
                    ha="center", va="top", fontsize=8, color=col, fontweight="bold")
        y -= kart_h + 0.16

        ax.axhline(y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.6)
        y -= 0.12

        # ── TABLO BAŞLIK ──
        # Sütun x pozisyonları — fig_w=7.42 için
        COL = {
            "coin":   0.18,
            "fiyat":  2.10,
            "d24":    3.20,
            "skor":   4.20,
            "rsi":    5.05,
            "fund":   5.95,
            "oi":     6.85,
            "taker":  7.80,
            "cvd":    8.85,
            "hac":   10.20,
        }
        col_defs = [
            (COL["coin"],  "COİN",   "left"),
            (COL["fiyat"], "FİYAT",  "right"),
            (COL["d24"],   "24S%",   "right"),
            (COL["skor"],  "SKOR",   "right"),
            (COL["rsi"],   "RSI",    "right"),
            (COL["fund"],  "FUND.",  "right"),
            (COL["oi"],    "OI Δ",   "right"),
            (COL["taker"], "TAKER",  "right"),
            (COL["cvd"],   "CVD",    "right"),
            (COL["hac"],   "HAC.Ç",  "right"),
        ]
        for cx, lbl, ha in col_defs:
            ax.text(cx, y, lbl, ha=ha, va="top", fontsize=10, color=WHITE, fontweight="bold")
        y -= 0.16
        ax.axhline(y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.5)

        row_h = 0.70
        for i, sym in enumerate(SEMBOLLER):
            ry     = y - 0.06 - i * row_h
            veri   = coin_verileri.get(sym, {})
            bg_col = CARD if i % 2 == 0 else CARD2
            ax.add_patch(FancyBboxPatch(
                (0.08, ry - row_h + 0.10), fig_w - 0.16, row_h - 0.08,
                boxstyle="round,pad=0.02", linewidth=0, facecolor=bg_col))

            my = ry - row_h / 2 + 0.04

            sym_kisa = sym.replace("USDT", "")
            sym_renk = GOLD if sym == "BTCUSDT" else WHITE
            ax.text(COL["coin"], my, sym_kisa, ha="left", va="center",
                    fontsize=12, color=sym_renk, fontweight="bold")

            # Fiyat
            ax.text(COL["fiyat"], my, fmt_fiyat(veri.get("fiyat")), ha="right", va="center",
                    fontsize=10, color=GRAY)

            # 24s%
            d24 = veri.get("degisim_24h")
            ax.text(COL["d24"], my, f"{d24:+.1f}%" if d24 is not None else "—",
                    ha="right", va="center", fontsize=10, color=renk_pct(d24))

            # Skor — kutu yok, sadece renkli kalın metin
            skor = veri.get("skor")
            if skor is not None:
                s_col = renk_skor(skor)
                ax.text(COL["skor"] - 0.04, my, str(skor), ha="center", va="center",
                        fontsize=11, color=s_col)

            # RSI
            rsi = veri.get("rsi")
            r_col = ORANGE if rsi and rsi >= 70 else (ORANGE if rsi and rsi <= 30 else GRAY)
            ax.text(COL["rsi"], my, f"{rsi:.1f}" if rsi else "—",
                    ha="right", va="center", fontsize=10, color=r_col, fontweight="bold")

            # Funding
            fund = veri.get("funding", 0)
            ax.text(COL["fund"], my, f"{fund:+.4f}" if fund != 0 else "0",
                    ha="right", va="center", fontsize=9.5,
                    color=GREEN if fund > 0.01 else (RED if fund < -0.01 else GRAY))

            # OI delta
            oi_d = veri.get("oi_delta")
            if oi_d:
                dp = oi_d["delta_pct"]
                ax.text(COL["oi"], my, f"{dp:+.1f}%", ha="right", va="center",
                        fontsize=10, color=renk_pct(dp))
            else:
                ax.text(COL["oi"], my, "—", ha="right", va="center", fontsize=10, color=GRAY, fontweight="bold")

            # Taker
            taker = veri.get("taker")
            if taker:
                bp = taker["taker_buy_pct"]
                t_col = GREEN if bp >= 55 else (RED if bp <= 45 else GRAY)
                ax.text(COL["taker"], my, f"{bp:.0f}%B", ha="right", va="center",
                        fontsize=10, color=t_col, fontweight="bold")
            else:
                ax.text(COL["taker"], my, "—", ha="right", va="center", fontsize=10, color=GRAY, fontweight="bold")

            # CVD
            cvd = veri.get("cvd")
            if cvd:
                c_uyum = cvd["uyum"]
                if c_uyum == "uyum" and cvd["cvd"] >= 0:
                    cvd_str, c_col = "↑ uyum", GREEN
                elif c_uyum == "uyum" and cvd["cvd"] < 0:
                    cvd_str, c_col = "↓ uyum", RED
                elif c_uyum == "uyumsuz_yukari":
                    cvd_str, c_col = "↓ UYM⚠", ORANGE
                elif c_uyum == "uyumsuz_asagi":
                    cvd_str, c_col = "↑ UYM⚠", ORANGE
                else:
                    cvd_str, c_col = "→ düz", GRAY
                ax.text(COL["cvd"], my, cvd_str, ha="right", va="center",
                        fontsize=10, color=c_col, fontweight="bold")
            else:
                ax.text(COL["cvd"], my, "—", ha="right", va="center", fontsize=10, color=GRAY, fontweight="bold")

            # Hacim çarpanı — kısa format
            hc = veri.get("hac_carpan", 0)
            if hc and hc > 0:
                hc_col = ORANGE if hc > 5 else (LGREEN if hc > 2 else GRAY)
                hc_str = f"{hc:.1f}x" + ("⚠" if hc > 5 else "")
                ax.text(COL["hac"], my, hc_str, ha="right", va="center",
                        fontsize=9.5, color=hc_col, fontweight="bold")
            else:
                ax.text(COL["hac"], my, "—", ha="right", va="center", fontsize=9.5, color=DGRAY, fontweight="bold")

        y -= len(SEMBOLLER) * row_h + 0.16

        # ── ALT BİLGİ ──
        ax.axhline(y, xmin=0.01, xmax=0.99, color=BORDER, linewidth=0.5)
        legend_items = [
            ("■", GREEN,  "75+ Güçlü Yük."),
            ("■", LGREEN, "55+ Yükseliş"),
            ("■", GRAY,   "40+ Nötr"),
            ("■", ORANGE, "25+ Düşüş"),
            ("■", RED,    "Güçlü Düş."),
        ]
        lx = 0.12
        for sym2, col, lbl in legend_items:
            ax.text(lx, y - 0.14, sym2, ha="left", va="top", fontsize=7.5, color=col, fontweight="bold")
            ax.text(lx + 0.15, y - 0.14, lbl, ha="left", va="top", fontsize=7.5, color=WHITE, fontweight="bold")
            lx += 1.38
        # Sağ açıklamalar — 2 satıra böl
        ax.text(fig_w - 0.10, y - 0.10,
                "HAC.Ç=Fut/Spot  ·  UYM⚠=Uyumsuz",
                ha="right", va="top", fontsize=7, color=GRAY, fontweight="bold")
        ax.text(fig_w - 0.10, y - 0.26,
                "OI Δ=Açık Pozisyon Değişimi",
                ha="right", va="top", fontsize=7, color=GRAY, fontweight="bold")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=200,
                    facecolor=BG, edgecolor="none",
                    bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        import traceback as _tb
        print(f"[ANALIZ] Gorsel hatasi: {type(e).__name__}: {e}")
        _tb.print_exc()
        return None


def _analiz_ozet_metin(coin_verileri, veriler):
    """
    BTC/ETH/SOL için piyasa diliyle özet + olta seviyeleri metni üret.
    Telegram HTML formatında döner (görsel altında mesaj olarak da gönderilir).
    """
    SEMBOLLER = [
        "BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
        "DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT"
    ]

    def fmt(f):
        if f is None: return "—"
        if f >= 10000: return f"${f:,.0f}"
        if f >= 100:   return f"${f:,.0f}"
        if f >= 1:     return f"${f:.3f}"
        return f"${f:.5f}"

    satirlar = []

    # Genel durum
    skorlar = [v.get("skor", 0) for v in coin_verileri.values() if v.get("skor") is not None]
    ort_skor = round(sum(skorlar) / len(skorlar)) if skorlar else 0
    breadth  = veriler.get("_breadth", 0)

    if ort_skor >= 70 and breadth >= 7:
        genel = "Piyasa genelinde güçlü yükseliş baskısı hâkim, 10 coinden {b}'si EMA20 üstünde.".format(b=breadth)
    elif ort_skor >= 55:
        genel = "Piyasa yükseliş eğiliminde, {b}/10 coin EMA20 üstünde.".format(b=breadth)
    elif ort_skor >= 40:
        genel = "Piyasa yön arıyor, {b}/10 coin EMA20 üstünde.".format(b=breadth)
    else:
        genel = "Piyasada satış baskısı var, sadece {b}/10 coin EMA20 üstünde.".format(b=breadth)
    satirlar.append(genel)

    # BTC / ETH / SOL detay
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        v     = coin_verileri.get(sym, {})
        olta  = _analiz_olta_seviyeleri(sym, v)
        kisa  = sym.replace("USDT", "")
        fiyat = v.get("fiyat", 0)
        skor  = v.get("skor", 0)
        cvd   = v.get("cvd")
        taker = v.get("taker")
        lik   = v.get("likidasyonlar")
        fund  = v.get("funding", 0)
        d24   = v.get("degisim_24h", 0) or 0

        # Güç özeti
        if skor >= 70:
            guc = "sinyaller uyumlu"
        elif skor >= 55:
            guc = "yükseliş eğilimli"
        elif skor >= 40:
            guc = "nötr seyirde"
        else:
            guc = "zayıf"

        # CVD yorumu
        cvd_yorum = ""
        if cvd:
            if cvd["uyum"] == "uyumsuz_yukari":
                cvd_yorum = "CVD uyumsuz (fiyat ↑ CVD ↓ — satış gizleniyor)"
            elif cvd["uyum"] == "uyumsuz_asagi":
                cvd_yorum = "CVD uyumsuz (fiyat ↓ CVD ↑ — birikim sinyali)"

        # Likidasyon yorumu
        lik_yorum = ""
        if lik and lik["toplam_usd"] >= 1.0:
            if lik["agirlik"] == "short_baskin":
                lik_yorum = f"son 30dk ${lik['short_usd']}M short ezildi"
            elif lik["agirlik"] == "long_baskin":
                lik_yorum = f"son 30dk ${lik['long_usd']}M long ezildi — dikkat"

        # Cümle birleştir
        detaylar = [x for x in [cvd_yorum, lik_yorum] if x]
        detay_str = (" — " + ", ".join(detaylar)) if detaylar else ""

        # Olta cümlesi
        olta_str = (
            f"Long olta {fmt(olta['long_giris_alt'])}–{fmt(olta['long_giris_ust'])} "
            f"(stop {fmt(olta['long_stop'])}, TP {fmt(olta['long_tp1'])}/{fmt(olta['long_tp2'])}), "
            f"short olta {fmt(olta['short_giris'])} red "
            f"(stop {fmt(olta['short_stop'])}, TP {fmt(olta['short_tp'])})."
        )

        d24_str = f"{d24:+.1f}%" if d24 else ""
        coin_satirı = (
            f"{kisa} {d24_str} — {guc}{detay_str}. {olta_str}"
        )
        satirlar.append(coin_satirı)

    # Tek düz metin (görsel içinde textwrap ile bölünür)
    return "  ".join(satirlar)


def _analiz_ozet_telegram(coin_verileri, veriler, zaman_str):
    """Telegram HTML — kısa, öz, tanımsız, tekrarsız."""
    try:
        satirlar = [f"📡 <b>Piyasa Özeti</b> — {zaman_str}\n"]

        breadth   = veriler.get("_breadth", 0)
        btc_veri  = coin_verileri.get("BTCUSDT", {})
        btc_fund  = btc_veri.get("funding", 0) or 0
        btc_cvd_d = btc_veri.get("cvd")

        skorlar  = [v.get("skor", 0) for v in coin_verileri.values() if v.get("skor") is not None]
        ort_skor = round(sum(skorlar) / len(skorlar)) if skorlar else 0

        # CVD sınıflandırma — kısa vadeli yön tespiti (uyum) + uzun vadeli seviye (cvd_val)
        uyumsuz_yukari, uyumsuz_asagi, uyumlu_asagi = [], [], []
        for sym, v in coin_verileri.items():
            cvd = v.get("cvd")
            if not cvd: continue
            kisa    = sym.replace("USDT", "")
            uyum    = cvd.get("uyum", "")
            cvd_val = cvd.get("cvd", 0)
            # Birikim: fiyat ↓ CVD ↑ (kısa vadeli alım var) — CVD kümülatif negatif olsa da geçerli
            if uyum == "uyumsuz_asagi":
                uyumsuz_asagi.append((kisa, cvd_val))
            # Sahte pump: fiyat ↑ CVD ↓ VE CVD kümülatif negatif
            elif uyum == "uyumsuz_yukari" and cvd_val < 0:
                uyumsuz_yukari.append(kisa)
            # Gerçek satış: fiyat ↓ CVD ↓ VE CVD kümülatif negatif
            elif uyum in ("uyum", "duz") and cvd_val < -500:
                uyumlu_asagi.append(kisa)

        # Likidasyon
        toplam_lik = long_lik = short_lik = 0.0
        for v in coin_verileri.values():
            lik = v.get("likidasyonlar")
            if lik:
                toplam_lik += lik.get("toplam_usd", 0)
                long_lik   += lik.get("long_usd", 0)
                short_lik  += lik.get("short_usd", 0)

        # Taker
        taker_long_c  = sum(1 for v in coin_verileri.values()
                            if v.get("taker") and v["taker"].get("taker_buy_pct", 50) >= 55)
        taker_short_c = sum(1 for v in coin_verileri.values()
                            if v.get("taker") and v["taker"].get("taker_buy_pct", 50) <= 45)
        taker_toplam  = sum(1 for v in coin_verileri.values() if v.get("taker"))

        # ── MARKET YÖNÜ PUANI ──
        puan = 0
        if ort_skor >= 65:    puan += 2
        elif ort_skor >= 50:  puan += 1
        elif ort_skor < 40:   puan -= 2
        # Breadth en güçlü sinyal — ağırlık artırıldı
        if breadth >= 8:      puan += 3
        elif breadth >= 6:    puan += 2
        elif breadth >= 4:    puan += 1
        elif breadth <= 2:    puan -= 3
        elif breadth <= 4:    puan -= 2
        if taker_long_c >= 6:    puan += 2
        elif taker_short_c >= 6: puan -= 2
        if short_lik > long_lik * 2 and toplam_lik >= 1.0: puan += 1
        elif long_lik > short_lik * 2 and toplam_lik >= 1.0: puan -= 1
        if len(uyumsuz_yukari) >= 4: puan -= 1
        if len(uyumsuz_asagi) >= 3:  puan += 1  # tuple listesi, len doğru çalışır
        if btc_fund > 0.02:   puan -= 1
        elif btc_fund < -0.01: puan += 1
        # BTC CVD negatifse (gerçek satış baskısı) puan düş
        if btc_cvd_d and btc_cvd_d.get("cvd", 0) < -3000: puan -= 1

        if puan >= 4:    yon_ikon, yon_metin = "📈", "Yukarı Yönlü"
        elif puan >= 2:  yon_ikon, yon_metin = "🟡", "Hafif Yukarı Yönlü"
        elif puan <= -4: yon_ikon, yon_metin = "📉", "Aşağı Yönlü"
        elif puan <= -2: yon_ikon, yon_metin = "🟠", "Hafif Aşağı Yönlü"
        else:            yon_ikon, yon_metin = "↔️", "Yatay / Belirsiz"

        # ── 1) CVD ──
        if uyumsuz_asagi or uyumsuz_yukari or uyumlu_asagi or btc_cvd_d:
            parcalar = []
            # BTC'yi ayrı yorumla — CVD satırında gösteriliyor
            birikim_listesi = [c for c,_ in uyumsuz_asagi if c != "BTC"]
            btc_birikim     = any(c == "BTC" for c,_ in uyumsuz_asagi)
            pump_listesi    = [c for c in uyumsuz_yukari if c != "BTC"]
            satis_listesi   = [c for c in uyumlu_asagi if c != "BTC"]

            if birikim_listesi:
                # Kümülatif CVD negatif olanlar için farklı mesaj
                neg_cvd = [c for c,v in uyumsuz_asagi if c != "BTC" and v < 0]
                pos_cvd = [c for c,v in uyumsuz_asagi if c != "BTC" and v >= 0]
                if pos_cvd:
                    parcalar.append(f"<b>{', '.join(pos_cvd)}</b> düşüş suni olabilir, dip alma fırsatı")
                if neg_cvd:
                    parcalar.append(f"<b>{', '.join(neg_cvd)}</b> kısa vadeli alım var ancak baskı sürüyor")
            if satis_listesi:
                parcalar.append(f"<b>{', '.join(satis_listesi)}</b> gerçek satış baskısı altında")
            if pump_listesi:
                parcalar.append(f"<b>{', '.join(pump_listesi)}</b> pump suni olabilir, dikkatli ol")
            if btc_cvd_d:
                cvd_val = btc_cvd_d.get("cvd", 0)
                if btc_birikim and cvd_val < 0:
                    parcalar.append("BTC kısa vadeli alım sinyali var ancak kümülatif satış baskısı sürüyor")
                elif cvd_val > 1000:
                    parcalar.append("BTC güçlü alım baskısı, yükseliş destekli")
                elif cvd_val > 0:
                    parcalar.append("BTC hafif alıcı üstünlüğü")
                elif cvd_val < -1000:
                    parcalar.append("BTC ağır satış baskısı, düşüş destekli")
                else:
                    parcalar.append("BTC hafif satıcı üstünlüğü")
            if parcalar:
                satirlar.append("💡 <b>CVD:</b> " + ". ".join(parcalar) + ".")

        # ── 2) LİKİDASYON ──
        if toplam_lik >= 1.0:
            if long_lik > short_lik * 2:
                lik_yorum = "ağırlıklı long tasfiyesi, satış baskısı artabilir"
            elif short_lik > long_lik * 2:
                lik_yorum = "ağırlıklı short tasfiyesi, yükseliş ivmesi var"
            else:
                lik_yorum = "dengeli tasfiye"
            satirlar.append(f"💥 <b>Likidasyon:</b> Son 30dk'da likidasyon mevcut — {lik_yorum}.")
        else:
            satirlar.append("💥 <b>Likidasyon:</b> Son 30dk'da kayda değer likidasyon yok.")

        # ── 3) FUNDING ──
        if abs(btc_fund) >= 0.02:
            fund_yorum = "Long kalabalık, düzeltme riski." if btc_fund > 0 else "Short kalabalık, squeeze riski."
        elif abs(btc_fund) >= 0.005:
            fund_yorum = "Long baskın." if btc_fund > 0 else "Short baskın."
        else:
            fund_yorum = "Eşit maliyette."
        satirlar.append(f"💰 <b>BTC Funding:</b> {fund_yorum}")

        # ── 4) RSI ──
        asiri_alim   = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                        if v.get("rsi") and v["rsi"] > 70]
        alim_yakin   = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                        if v.get("rsi") and 65 < v["rsi"] <= 70]
        asiri_satim  = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                        if v.get("rsi") and v["rsi"] <= 35]
        satim_yakin  = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                        if v.get("rsi") and 35 < v["rsi"] <= 42]
        if asiri_alim and asiri_satim:
            str_aa = ", ".join([n for n,_ in sorted(asiri_alim, key=lambda x:-x[1])])
            str_as = ", ".join([n for n,_ in sorted(asiri_satim, key=lambda x:x[1])])
            satirlar.append(f"📊 <b>RSI:</b> Aşırı alım: <b>{str_aa}</b> — Aşırı satım: <b>{str_as}</b>.")
        elif asiri_alim:
            str_aa = ", ".join([n for n,_ in sorted(asiri_alim, key=lambda x:-x[1])])
            satirlar.append(f"📊 <b>RSI:</b> <b>{str_aa}</b> aşırı alım bölgesinde.")
        elif asiri_satim:
            str_as = ", ".join([n for n,_ in sorted(asiri_satim, key=lambda x:x[1])])
            satirlar.append(f"📊 <b>RSI:</b> <b>{str_as}</b> aşırı satım bölgesinde, dönüş fırsatı izlenebilir.")
        elif satim_yakin:
            str_sy = ", ".join([n for n,_ in sorted(satim_yakin, key=lambda x:x[1])])
            satirlar.append(f"📊 <b>RSI:</b> <b>{str_sy}</b> aşırı satım bölgesine yakın.")
        elif alim_yakin and puan >= 0:
            str_ay = ", ".join([n for n,_ in sorted(alim_yakin, key=lambda x:-x[1])])
            satirlar.append(f"📊 <b>RSI:</b> <b>{str_ay}</b> aşırı alım bölgesine yakın, dikkatli ol.")
        else:
            satirlar.append("📊 <b>RSI:</b> Aşırı alım/satım yok, trendi takip etmeye elverişli ortam.")

        # ── 5) OI (Açık Pozisyon) ──
        oi_artan  = [(s.replace("USDT",""), v["oi_delta"]["delta_pct"]) for s,v in coin_verileri.items()
                     if v.get("oi_delta") and v["oi_delta"]["delta_pct"] > 0.3]
        oi_azalan = [(s.replace("USDT",""), v["oi_delta"]["delta_pct"]) for s,v in coin_verileri.items()
                     if v.get("oi_delta") and v["oi_delta"]["delta_pct"] < -0.3]
        oi_artan.sort(key=lambda x: -x[1])
        oi_azalan.sort(key=lambda x: x[1])
        if oi_artan:
            str_art = ", ".join([n for n,_ in oi_artan[:4]])
            satirlar.append(f"📈 <b>Artan Pozisyon:</b> <b>{str_art}</b> için pozisyonlar açılıyor, piyasa büyüyor.")
        if oi_azalan:
            str_az = ", ".join([n for n,_ in oi_azalan[:4]])
            satirlar.append(f"📉 <b>Azalan Pozisyon:</b> <b>{str_az}</b> için pozisyonlar kapanıyor.")

        # ── 6) HAC.Ç ──
        hac_yuksek = [(s.replace("USDT",""), v.get("hac_carpan", 0)) for s,v in coin_verileri.items()
                      if v.get("hac_carpan") and v["hac_carpan"] >= 5]
        hac_yuksek.sort(key=lambda x: -x[1])
        if hac_yuksek:
            str_hac = ", ".join([n for n,_ in hac_yuksek[:4]])
            satirlar.append(f"⚡ <b>HAC.Ç:</b> <b>{str_hac}</b> için spekülatif hareket futures piyasasından geliyor.")

        # ── 7) PİYASA SKORU ──
        if ort_skor >= 70 and breadth >= 7:
            skor_yorum = "Güçlü yükseliş sinyali."
        elif ort_skor >= 55:
            skor_yorum = "Yükseliş eğilimli."
        elif ort_skor >= 40:
            skor_yorum = "Karışık sinyaller, net yön yok."
        elif ort_skor >= 25:
            skor_yorum = "Satış baskısı hakim."
        else:
            skor_yorum = "Düşüş baskısı güçlü."
        satirlar.append(f"🏆 <b>Piyasa Skoru:</b> {skor_yorum}")

        # ── 8) MARKET YÖNÜ ──
        if puan >= 4 or puan <= -4:
            yon_ek = " Yakın zamanda sert kırılım olabilir."
        else:
            yon_ek = ""
        satirlar.append(f"🧭 <b>Market Yönü:</b> {yon_ikon} <b>{yon_metin}</b>.{yon_ek}")

        # ── 9) BREAKOUT BENZERLİĞİ ──
        benzer_olay_bilgi = None
        try:
            cvd_uyum_str = ("uyumsuz_yukari" if len(uyumsuz_yukari) >= len(uyumsuz_asagi) and uyumsuz_yukari
                            else "uyumsuz_asagi" if uyumsuz_asagi else "uyumlu")
            lik_taraf = ("long" if long_lik > short_lik * 1.5 else
                         "short" if short_lik > long_lik * 1.5 else "dengeli")
            btc_oi_d = btc_veri.get("oi_delta")
            oi_delta = btc_oi_d["delta_pct"] if btc_oi_d else 0.0
            fg_deger = None
            try: fg_deger, _ = _trend_fear_greed()
            except Exception: pass

            benzer = _breakout_benzerlik_hesapla(
                btc_fund, oi_delta, cvd_uyum_str, lik_taraf,
                fg_deger=fg_deger, breadth_sayi=breadth, toplam_coin=len(coin_verileri)
            )
            if benzer:
                puan_b, eslesme, olay = benzer[0]
                yon_b   = "Piyasa Çöküşü" if olay["yon"] == "asagi" else "Piyasa Yükselişi"
                ikon_b  = "📉" if olay["yon"] == "asagi" else "📈"
                kritik  = " 🚨 Yakın zamanda sert hareket olabilir!" if eslesme >= 5 else ""
                asagi_s = sum(1 for _,_,o in benzer if o["yon"] == "asagi")
                yukari_s = sum(1 for _,_,o in benzer if o["yon"] == "yukari")
                if asagi_s > yukari_s:
                    senaryo_yorum = " ⚠️ Benzer senaryolar düşüşle kapandı."
                elif yukari_s > asagi_s:
                    senaryo_yorum = " 📈 Benzer senaryolar yükselişle kapandı."
                else:
                    senaryo_yorum = " ↔️ Benzer senaryolar karışık yönlü."
                satirlar.append(
                    f"\n⚡ <b>Geçmiş {yon_b} Benzerliği (%{puan_b}):</b> {ikon_b} {olay['ad']} "
                    f"({olay['tarih']}) — {olay['hareket_pct']:+d}% ({olay['sure_gun']}g)."
                    f"{senaryo_yorum}{kritik}"
                )
                benzer_olay_bilgi = (olay["yon"], eslesme)
        except Exception as e:
            print(f"[ANALIZ] Breakout benzerlik hatasi: {e}")

        # ── 10) NE YAPMALIYIM? ──
        satirlar.append("\n🎯 <b>Ne Yapmalıyım?</b>")
        oneriler = []

        # Genel strateji
        if puan <= -4:
            # Aşırı düşüş durumu — breadth ve skor da kontrol et
            if breadth == 0 and ort_skor < 25:
                oneriler.append("🚨 Piyasa çöküş modunda. Tüm açık longları kapat, yeni pozisyon açma. Nakit en güvenli seçenek.")
            elif breadth <= 2:
                oneriler.append("⛔ Çok güçlü düşüş baskısı. Yeni long kesinlikle açma, mevcut longları kapat veya stop'ları çok sıkıştır.")
            else:
                oneriler.append("⛔ Yeni long pozisyon açma. Mevcut longları gözden geçir, stop'ları sıkıştır.")
        elif puan <= -2:
            oneriler.append("⚠️ Long pozisyonlarda temkinli ol. Yüksek kaldıraçtan kaçın, stop'ları dar tut.")
        elif puan >= 4:
            oneriler.append("✅ Trend yukarı yönlü. Yüksek skorlu coinlerde long fırsatları değerlendirilebilir.")
        elif puan >= 2:
            oneriler.append("🟡 Yükseliş eğilimi var ancak teyit bekleniyor. Küçük pozisyonlarla gir, acele etme.")
        else:
            oneriler.append("⏸️ Net yön yok. Breakout veya net sinyal bekle, pozisyon açma.")

        # CVD bazlı coin önerileri
        if uyumsuz_asagi and puan >= 0:
            dip_adaylar = []
            dip_bekle   = []
            for coin, cvd_v in uyumsuz_asagi[:4]:
                if coin == "BTC": continue
                sym  = coin + "USDT"
                v    = coin_verileri.get(sym, {})
                rsi  = v.get("rsi", 50)
                skor = v.get("skor", 0)
                if rsi <= 35 and skor >= 45 and cvd_v > 0:
                    dip_adaylar.append(coin)
                elif cvd_v > 0:
                    dip_bekle.append(coin)
            if dip_adaylar:
                oneriler.append(f"💡 Dip alma adayları: <b>{', '.join(dip_adaylar)}</b> — CVD birikim + RSI teyidi var. Stop'lu gir.")
            elif dip_bekle:
                oneriler.append(f"💡 <b>{', '.join(dip_bekle)}</b> CVD birikim sinyali veriyor, RSI teyidi bekleniyor.")

        if uyumsuz_yukari and puan <= 0:
            oneriler.append(f"⚠️ <b>{', '.join(uyumsuz_yukari[:3])}</b> pump suni görünüyor — long riskli, short fırsatı olabilir.")

        # RSI bazlı
        asiri_satim_coins = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                             if v.get("rsi") and v["rsi"] <= 28]
        if asiri_satim_coins and puan >= -2:
            str_as2 = ", ".join([f"<b>{n}</b>({r:.0f})" for n,r in sorted(asiri_satim_coins, key=lambda x:x[1])[:3]])
            oneriler.append(f"🟢 {str_as2} aşırı satım bölgesinde — dipten dönüş için takibe al.")

        asiri_alim_coins = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                            if v.get("rsi") and v["rsi"] >= 75]
        if asiri_alim_coins:
            str_aa2 = ", ".join([f"<b>{n}</b>({r:.0f})" for n,r in sorted(asiri_alim_coins, key=lambda x:-x[1])[:3]])
            oneriler.append(f"🔴 {str_aa2} aşırı alım bölgesinde — mevcut pozisyonda stop sıkıştır, yeni long açma.")

        # Funding uyarısı
        if btc_fund > 0.02:
            oneriler.append("💸 Funding yüksek — long maliyeti artıyor, kısa vadeli longlardan çık.")
        elif btc_fund < -0.01:
            oneriler.append("💸 Negatif funding — short pozisyon taşıma maliyeti yüksek, shortları yönet.")

        # HAC.Ç uyarısı
        if hac_yuksek and len(hac_yuksek) >= 3:
            oneriler.append(f"⚡ Yüksek HAC.Ç nedeniyle ani ters hareket riski var — geniş stop kullan veya pozisyon küçük tut.")

        # Breakout benzerliği uyarısı
        if benzer_olay_bilgi:
            yon_b2, eslesme_b2 = benzer_olay_bilgi
            if eslesme_b2 >= 5:
                if yon_b2 == "asagi":
                    oneriler.append("🚨 Geçmiş benzerlik kritik eşikte — tüm açık longları gözden geçir, stop'suz pozisyon taşıma.")
                else:
                    oneriler.append("🚨 Geçmiş benzerlik kritik eşikte — kırılım yukarı olursa hızlı hareket edebilir, hazırlıklı ol.")

        for o in oneriler:
            satirlar.append(f"  • {o}")

        satirlar.append(f"\n<i>{zaman_str}  ·  Binance Futures + Spot</i>")
        return "\n".join(satirlar)

    except Exception as e:
        print(f"[ANALIZ] ozet_telegram hata: {e}")
        traceback.print_exc()
        return f"📡 <b>Piyasa Özeti</b> — {zaman_str}\n\n⚠️ Özet üretilemedi: {e}"

        breadth  = veriler.get("_breadth", 0)
        btc_veri = coin_verileri.get("BTCUSDT", {})
        btc_fund = btc_veri.get("funding", 0) or 0
        btc_cvd_d = btc_veri.get("cvd")

        skorlar  = [v.get("skor", 0) for v in coin_verileri.values() if v.get("skor") is not None]
        ort_skor = round(sum(skorlar) / len(skorlar)) if skorlar else 0

        # CVD uyumsuzlukları
        uyumsuz_yukari, uyumsuz_asagi = [], []
        for sym, v in coin_verileri.items():
            cvd = v.get("cvd")
            if not cvd: continue
            kisa = sym.replace("USDT", "")
            uyum = cvd.get("uyum", "")
            if uyum == "uyumsuz_yukari": uyumsuz_yukari.append(kisa)
            elif uyum == "uyumsuz_asagi": uyumsuz_asagi.append(kisa)

        # Likidasyon
        toplam_lik = long_lik = short_lik = 0.0
        for v in coin_verileri.values():
            lik = v.get("likidasyonlar")
            if lik:
                toplam_lik += lik.get("toplam_usd", 0)
                long_lik   += lik.get("long_usd", 0)
                short_lik  += lik.get("short_usd", 0)

        # Taker
        taker_long_c  = sum(1 for v in coin_verileri.values()
                            if v.get("taker") and v["taker"].get("taker_buy_pct", 50) >= 55)
        taker_short_c = sum(1 for v in coin_verileri.values()
                            if v.get("taker") and v["taker"].get("taker_buy_pct", 50) <= 45)
        taker_toplam  = sum(1 for v in coin_verileri.values() if v.get("taker"))

        # ── MARKET YÖNÜ PUANI ──
        puan = 0
        if ort_skor >= 65:   puan += 2
        elif ort_skor >= 50: puan += 1
        elif ort_skor < 40:  puan -= 2
        if breadth >= 7:     puan += 2
        elif breadth >= 5:   puan += 1
        elif breadth <= 3:   puan -= 2
        if taker_long_c >= 6:   puan += 2
        elif taker_short_c >= 6: puan -= 2
        if short_lik > long_lik * 2 and toplam_lik >= 1.0: puan += 1
        elif long_lik > short_lik * 2 and toplam_lik >= 1.0: puan -= 1
        if len(uyumsuz_yukari) >= 4: puan -= 1
        if len(uyumsuz_asagi) >= 3:  puan += 1
        if btc_fund > 0.02: puan -= 1
        elif btc_fund < -0.01: puan += 1

        if puan >= 4:    yon_ikon, yon_metin = "📈", "YUKARI"
        elif puan >= 2:  yon_ikon, yon_metin = "🟡", "HAFIF YUKARI"
        elif puan <= -4: yon_ikon, yon_metin = "📉", "AŞAĞI"
        elif puan <= -2: yon_ikon, yon_metin = "🟠", "HAFIF AŞAĞI"
        else:            yon_ikon, yon_metin = "↔️", "YATAY"

        # Global piyasa verilerini cache'e yaz — sinyal_kaydet tarafından okunur
        try:
            _fg_d, _ = _trend_fear_greed()
        except Exception:
            _fg_d = None
        _piyasa_yonu_cache = (
            "Yükseliş" if "YUKARI" in yon_metin else
            "Düşüş"   if "AŞAĞI"  in yon_metin else
            "Yatay"
        )
        _son_analiz_veriler["_GLOBAL"] = {
            "fg_deger":    _fg_d,
            "btc_fund":    btc_fund,
            "ort_skor":    ort_skor,
            "piyasa_yonu": _piyasa_yonu_cache,
            "zaman":       time.time(),
        }

        # ── ÇIKTI ──

        # 1) Yön + özet
        satirlar.append(f"{yon_ikon} <b>{yon_metin}</b> (Puan: {puan:+d})")

        # 2) CVD — sadece uyumsuzluk varsa
        if uyumsuz_asagi:
            satirlar.append(f"💡 Birikim: <b>{', '.join(uyumsuz_asagi)}</b>")
        if uyumsuz_yukari:
            satirlar.append(f"⚠️ Sahte pump riski: <b>{', '.join(uyumsuz_yukari)}</b>")
        if btc_cvd_d:
            cvd_val = btc_cvd_d.get("cvd", 0)
            if abs(cvd_val) >= 500:
                cvd_yorum = "alım baskısı" if cvd_val > 0 else "satış baskısı"
                satirlar.append(f"📊 BTC CVD: <b>{cvd_val:+,.0f}</b> — {cvd_yorum}")

        # 3) Likidasyon — sadece anlamlıysa
        if toplam_lik >= 0.5:
            if long_lik > short_lik * 2:
                satirlar.append(f"📉 Lik: {toplam_lik:.1f}M$ — long ezildi")
            elif short_lik > long_lik * 2:
                satirlar.append(f"📈 Lik: {toplam_lik:.1f}M$ — short squeeze")
            else:
                satirlar.append(f"↔️ Lik: {toplam_lik:.1f}M$ — dengeli")

        # 4) Funding — sadece dikkat çekiciyse
        if abs(btc_fund) >= 0.005:
            yorum = "long kalabalık ⚠️" if btc_fund > 0.02 else ("short kalabalık ⚠️" if btc_fund < -0.01 else ("long baskın" if btc_fund > 0 else "short baskın"))
            satirlar.append(f"💰 Funding: <b>{btc_fund:+.4f}%</b> — {yorum}")

        # 5) Dikkat çeken coinler — RSI uçları
        asiri_alim  = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                       if v.get("rsi") and v["rsi"] > 70]
        asiri_satim = [(s.replace("USDT",""), v["rsi"]) for s,v in coin_verileri.items()
                       if v.get("rsi") and v["rsi"] <= 30]
        if asiri_alim:
            str_aa = ", ".join([f"{n}({r:.0f})" for n,r in sorted(asiri_alim, key=lambda x:-x[1])])
            satirlar.append(f"🔴 RSI alım bölgesi: <b>{str_aa}</b>")
        if asiri_satim:
            str_as = ", ".join([f"{n}({r:.0f})" for n,r in sorted(asiri_satim, key=lambda x:x[1])])
            satirlar.append(f"🟢 RSI satım bölgesi: <b>{str_as}</b>")

        # 6) Breakout benzerliği
        try:
            cvd_uyum_str = ("uyumsuz_yukari" if len(uyumsuz_yukari) >= len(uyumsuz_asagi) and uyumsuz_yukari
                            else "uyumsuz_asagi" if uyumsuz_asagi else "uyumlu")
            lik_taraf = ("long" if long_lik > short_lik * 1.5 else
                         "short" if short_lik > long_lik * 1.5 else "dengeli")
            btc_oi_d = btc_veri.get("oi_delta")
            oi_delta = btc_oi_d["delta_pct"] if btc_oi_d else 0.0

            fg_deger = None
            try: fg_deger, _ = _trend_fear_greed()
            except Exception: pass

            benzer = _breakout_benzerlik_hesapla(
                btc_fund, oi_delta, cvd_uyum_str, lik_taraf,
                fg_deger=fg_deger, breadth_sayi=breadth, toplam_coin=len(coin_verileri)
            )
            if benzer:
                puan_b, eslesme, olay = benzer[0]
                ikon_b = "🚨📉" if eslesme >= 5 and olay["yon"] == "asagi" else \
                         "🚨📈" if eslesme >= 5 else \
                         "📉" if olay["yon"] == "asagi" else "📈"
                satirlar.append(
                    f"\n⚡ Geçmişe benzerlik <b>%{puan_b}</b>: {ikon_b} {olay['ad']} "
                    f"({olay['tarih']}) — {olay['hareket_pct']:+d}% ({olay['sure_gun']}g)"
                )
                asagi_s = sum(1 for _,_,o in benzer if o["yon"] == "asagi")
                yukari_s = sum(1 for _,_,o in benzer if o["yon"] == "yukari")
                if asagi_s > yukari_s:   satirlar.append("  ⚠️ Benzer senaryolar düşüşle kapandı.")
                elif yukari_s > asagi_s: satirlar.append("  📈 Benzer senaryolar yükselişle kapandı.")
        except Exception as e:
            print(f"[ANALIZ] Breakout benzerlik hatasi: {e}")

        satirlar.append(f"\n<i>{zaman_str}  ·  Binance Futures + Spot</i>")
        return "\n".join(satirlar)

    except Exception as e:
        print(f"[ANALIZ] ozet_telegram hata: {e}")
        traceback.print_exc()
        return f"📡 <b>Piyasa Özeti</b> — {zaman_str}\n\n⚠️ Özet üretilemedi: {e}"


def _analiz_gonder(chat_id=None):
    """Genişletilmiş Piyasa Analizi görselini + özet metnini TOPIC_PIYASA'ya gönder (saat başı)."""
    print("[ANALIZ] Basliyor — veri toplanıyor...")
    try:
        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        veriler = _analiz_veri_topla()
        if not veriler:
            print("[ANALIZ] Veri alinamadi.")
            return

        # Cache'e kaydet — olta sorgusunda kullanılır
        global _son_analiz_veriler
        _son_analiz_veriler = veriler

        SEMBOLLER = [
            "BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
            "DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT"
        ]
        coin_verileri = {s: veriler.get(s, {}) for s in SEMBOLLER}

        # Görsel üret
        img = _analiz_gorsel(veriler, zaman_str)
        if img:
            _topic_foto_gonder_filigranli(
                TOPIC_ANALIZ, img,
                f"📊 Genişletilmiş Piyasa Analizi — {zaman_str}\n/analiz"
            )
            print(f"[ANALIZ] Gorsel gonderildi. Boyut: {len(img)} bytes")
        else:
            print(f"[ANALIZ] Gorsel uretilmedi — veri sayisi: {len(veriler)}")

        # Özet metin
        ozet_msg = _analiz_ozet_telegram(coin_verileri, veriler, zaman_str)
        _telegram_topic_mesaj_gonder(TOPIC_ANALIZ, ozet_msg + "\n\n<code>/analiz</code>")
        print("[ANALIZ] Tamamlandi.")

    except Exception as e:
        print(f"[ANALIZ] Hata: {e}")
        traceback.print_exc()


def _analiz_zamanlayici():
    """Her saat başında (:00) Genişletilmiş Piyasa Analizi → TOPIC_PIYASA."""
    import datetime as dt_mod
    print("[ANALIZ] Zamanlayici basladi. Her saat :00'da TOPIC_PIYASA'ya gonderilecek.")
    while True:
        try:
            if TR_TZ:
                simdi = datetime.now(tz=TR_TZ)
            else:
                simdi = datetime.utcnow()

            sonraki = (simdi.replace(minute=0, second=0, microsecond=0)
                       + dt_mod.timedelta(hours=1))
            bekle = (sonraki - simdi).total_seconds()
            print(f"[ANALIZ] Sonraki rapor: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(max(bekle, 1))
            _analiz_gonder()
            time.sleep(15)  # double-fire önleme
        except Exception as e:
            print(f"[ANALIZ] Zamanlayici hata: {e}")
            time.sleep(60)


# ==========================================
# BAŞLAT
# ==========================================

BOT_VERSIYON = "v528"
print(f"[BASLANGIC] ========== BOT VERSIYON: {BOT_VERSIYON} ==========")
print(f"[BASLANGIC] Veri dosyasi: {VERI_DOSYASI}")
dosyadan_yukle()
pozisyon_yukle()
bot_durum_yukle()  # AUTO_TRADE ve PNL_RAPOR durumunu geri yukle
_olta_cache_yukle()    # Son olta cache'ini diskten yukle
_liq_ws_yukle()        # Likidasyon WS verisini diskten yukle
print(f"[BASLANGIC] AUTO_TRADE_ENABLED: {AUTO_TRADE_ENABLED} | PNL_RAPOR_ENABLED: {PNL_RAPOR_ENABLED}")
_watermark_yukle()
_haber_gonderilenler_yukle()
# Başlangıçta top3 hesapla — deploy sonrası boş kalmasın
top3_guncelle()
print(f"[BASLANGIC] Top3 whitelist: {top3_whitelist}")
threading.Thread(target=_tarayici_zamanlayici, daemon=True).start()
# v463: KULYUTMAZ tarama kaldirildi — proxy tasarrufu
# threading.Thread(target=_kulyutmaz_alarm_zamanlayici, daemon=True).start()
print("[KULYUTMAZ] Sinyal tarama zamanlayicisi basladi.")
threading.Thread(target=_trend_zamanlayici, daemon=True).start()
threading.Thread(target=_ls_zamanlayici, daemon=True).start()
threading.Thread(target=_marketyonu_zamanlayici, daemon=True).start()
threading.Thread(target=_analiz_zamanlayici, daemon=True).start()
# Bot başlarken analizi bir kez çalıştır — _GLOBAL cache hemen dolsun
# Böylece ilk sinyalden itibaren piyasa koşulları kaydedilir
threading.Thread(target=_analiz_gonder, daemon=True).start()
threading.Thread(target=_haber_zamanlayici, daemon=True).start()
threading.Thread(target=_oi_zamanlayici, daemon=True).start()
threading.Thread(target=_istatistik_zamanlayici, daemon=True).start()
threading.Thread(target=_tp_kosul_rapor_zamanlayici, daemon=True).start()
threading.Thread(target=_hl_zamanlayici, daemon=True).start()
threading.Thread(target=_liq_zamanlayici, daemon=True).start()
_liq_ws_baslat()  # Likidasyon WebSocket toplayici
threading.Thread(target=_liq_ws_bakim_zamanlayici, daemon=True).start()  # 5dk kaydet, 3gunde temizle



# ==========================================
# PNL RAPOR SİSTEMİ (05:59 / 11:59 / 17:59 / 23:59)
# ==========================================

def _pnl_rapor_gorsel(gun, bakiye, kullanilan, unrealized, unrealized_pct=0.0):
    """PNL raporu için görsel üret — kümülatif günlük verilerle."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec

        with _pnl_kilit:
            gun_kayitlar = [k for k in _pnl_kayitlar.get(gun, []) if k.get("mexc_acildi", True)]

        kum_pnl_usdt = sum(k["pnl_usdt"] for k in gun_kayitlar)
        # Kümülatif % = toplam USDT kazanç / toplam kullanılan marjin
        # Her işlemin pnl_pct'sini toplamamak gerekir (farklı marjinler)
        # Metin raporu ile tutarlı olması için aynı yöntemi kullan
        kum_pnl_pct  = sum(k["pnl_pct"] for k in gun_kayitlar)  # toplam işlem bazlı %

        if TR_TZ:
            zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
        else:
            zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

        fig = plt.figure(figsize=(10, 4), facecolor="#0d1117")
        gs  = GridSpec(1, 4, figure=fig, wspace=0.3)

        def kart(ax, baslik, deger, renk, alt="USDT"):
            ax.set_facecolor("#161b22")
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values(): sp.set_edgecolor("#30363d")
            ax.text(0.5, 0.78, baslik, transform=ax.transAxes,
                    ha="center", fontsize=9, color="#8b949e")
            # deger string veya float
            if isinstance(deger, str):
                deger_str = deger
            elif "PNL" in baslik:
                deger_str = (f"{deger:+.4f}" if abs(deger) < 0.01 else f"{deger:+.2f}")
            else:
                deger_str = f"{deger:.2f}"
            ax.text(0.5, 0.38, deger_str, transform=ax.transAxes,
                    ha="center", fontsize=13, color=renk)
            ax.text(0.5, 0.1, alt, transform=ax.transAxes,
                    ha="center", fontsize=8, color="#484f58")

        kart(fig.add_subplot(gs[0,0]), "Toplam Bakiye",
             f"{bakiye:.2f}", "#e6edf3")
        kart(fig.add_subplot(gs[0,1]), "Kullanilan",
             f"{kullanilan:.2f}", "#e6edf3")

        # PNL kart — % ve USDT yan yana
        ax_pnl = fig.add_subplot(gs[0,2])
        ax_pnl.set_facecolor("#161b22")
        ax_pnl.set_xticks([]); ax_pnl.set_yticks([])
        for sp in ax_pnl.spines.values(): sp.set_edgecolor("#30363d")
        ax_pnl.text(0.5, 0.78, "Gerceklesen PNL", transform=ax_pnl.transAxes,
                    ha="center", fontsize=9, color="#8b949e")
        renk_pnl = "#26a69a" if kum_pnl_usdt >= 0 else "#ef5350"
        # USDT formatı: büyükse .2f, küçükse .4f (0.0042 gibi değerler görünsün)
        def fmt_usdt(v):
            return f"{v:+.2f}" if abs(v) >= 0.01 else f"{v:+.4f}"

        ax_pnl.text(0.5, 0.45, f"{kum_pnl_pct:+.2f}%", transform=ax_pnl.transAxes,
                    ha="center", fontsize=13, color=renk_pnl)
        ax_pnl.text(0.5, 0.25, f"{fmt_usdt(kum_pnl_usdt)} USDT", transform=ax_pnl.transAxes,
                    ha="center", fontsize=11, color=renk_pnl)
        ax_pnl.text(0.5, 0.1, f"{len(gun_kayitlar)} işlem", transform=ax_pnl.transAxes,
                    ha="center", fontsize=8, color="#484f58")

        # Açık poz PNL kartı — % üstte, USDT altta
        ax_unreal2 = fig.add_subplot(gs[0,3])
        ax_unreal2.set_facecolor("#161b22")
        ax_unreal2.set_xticks([]); ax_unreal2.set_yticks([])
        for sp in ax_unreal2.spines.values(): sp.set_edgecolor("#30363d")
        ax_unreal2.text(0.5, 0.78, "Acik Poz. PNL", transform=ax_unreal2.transAxes,
                        ha="center", fontsize=9, color="#8b949e")
        _uc2 = "#26a69a" if unrealized >= 0 else "#ef5350"
        if unrealized != 0:
            ax_unreal2.text(0.5, 0.48, f"{unrealized_pct:+.2f}%", transform=ax_unreal2.transAxes,
                            ha="center", fontsize=13, color=_uc2)
            ax_unreal2.text(0.5, 0.25, f"{fmt_usdt(unrealized)} USDT", transform=ax_unreal2.transAxes,
                            ha="center", fontsize=10, color=_uc2)
        else:
            ax_unreal2.text(0.5, 0.38, "—", transform=ax_unreal2.transAxes,
                            ha="center", fontsize=13, color="#8b949e")
        ax_unreal2.text(0.5, 0.1, "USDT", transform=ax_unreal2.transAxes,
                        ha="center", fontsize=8, color="#484f58")

        fig.suptitle(f"MEXC Futures PNL — {zaman_str}",
                     color="#e6edf3", fontsize=11, fontweight="bold")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[PNL RAPOR GORSEL] Hata: {e}")
        return None


def _pnl_rapor_metin(gun, donem_bas, donem_bitis):
    """Kümülatif günlük PNL raporu metni."""
    with _pnl_kilit:
        gun_kayitlar = [k for k in _pnl_kayitlar.get(gun, []) if k.get("mexc_acildi", True)]

    if TR_TZ:
        zaman_str = datetime.now(tz=TR_TZ).strftime("%d %b %Y %H:%M")
    else:
        zaman_str = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

    # Dönem filtresi
    donem_kayitlar = [k for k in gun_kayitlar
                      if donem_bas <= k["zaman"] <= donem_bitis]

    kum_usdt = sum(k["pnl_usdt"] for k in gun_kayitlar)
    kum_pct  = sum(k["pnl_pct"]  for k in gun_kayitlar)
    tp_sayisi = sum(1 for k in gun_kayitlar if k["tp_label"] and "TP" in k["tp_label"])
    sl_sayisi = sum(1 for k in gun_kayitlar if k["tp_label"] == "SL")

    satirlar = [
        f"📊 <b>PNL Raporu</b> — {zaman_str}",
        f"<i>Günün başından bu yana kümülatif</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if not gun_kayitlar:
        satirlar.append("Henüz tamamlanan işlem yok.")
    else:
        # İşlem detayları — sadece botun açtığı işlemler
        for k in gun_kayitlar:
            if not k.get("mexc_acildi", True):
                continue
            sinyal  = k["sinyal"].upper()
            is_long = any(x in sinyal for x in ["BUY", "LONG"])
            yon     = "LONG" if is_long else "SHORT"
            tp_lbl  = k["tp_label"] or "?"
            ikon    = "✅" if tp_lbl != "SL" else "❌"
            renk_ok = "+" if k["pnl_usdt"] >= 0 else ""

            if k["giris"] >= 100:
                giris_str = f"{k['giris']:,.1f}"
                cikis_str = f"{k['cikis']:,.1f}"
            elif k["giris"] >= 1:
                giris_str = f"{k['giris']:.4f}"
                cikis_str = f"{k['cikis']:.4f}"
            else:
                giris_str = f"{k['giris']:.6f}"
                cikis_str = f"{k['cikis']:.6f}"

            satirlar.append(
                f"{ikon} <b>{k['symbol']}</b> — {yon} — {tp_lbl}\n"
                f"   Giriş: <code>{giris_str}</code> → <code>{cikis_str}</code>\n"
                f"   <b>{renk_ok}{k['pnl_usdt']:.4f} USDT</b>  |  "
                f"<b>{k['pnl_pct']:+.2f}%</b>"
            )

        # Özet
        satirlar += [
            "━━━━━━━━━━━━━━━━━━━━━━━",
            f"📈 Toplam: <b>{len(gun_kayitlar)} işlem</b>  "
            f"|  ✅ {tp_sayisi} TP  |  ❌ {sl_sayisi} SL",
            f"💰 Net PNL: <b>{kum_usdt:+.4f} USDT</b>  |  <b>{kum_pct:+.2f}%</b>",
        ]

    return "\n".join(satirlar)


def _pnl_rapor_gonder():
    """Dönemsel PNL raporu — görsel + işlem detayları metin olarak gönder."""
    if not PNL_RAPOR_ENABLED:
        print("[PNL RAPOR] Devre disi — /pnl_ac komutuyla aktif edilebilir.")
        return
    if not MEXC_API_KEY or not MEXC_API_SECRET:
        return

    try:
        # MEXC'ten güncel bakiye çek
        r = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/account/assets")
        res = r.json()
        if not res.get("success"):
            print(f"[PNL RAPOR] Bakiye sorgu hatasi: {res.get('message')}")
            return

        assets     = res.get("data", {})
        usdt       = None
        for a in (assets if isinstance(assets, list) else [assets]):
            if a.get("currency") == "USDT":
                usdt = a; break
        if not usdt:
            return

        bakiye     = float(usdt.get("equity",          0))
        kullanilan = float(usdt.get("positionMargin",   0))
        # Unrealized PNL — open_positions'tan profitRatio * im toplamı
        unrealized = 0.0
        unrealized_pct = 0.0
        try:
            _r_pos2 = mexc_private_get(f"{MEXC_BASE_URL}/api/v1/private/position/open_positions")
            _pos_data2 = _r_pos2.json().get("data", [])
            if isinstance(_pos_data2, list) and _pos_data2:
                for _p2 in _pos_data2:
                    _im2  = float(_p2.get("im", 0) or 0)
                    _pct2 = float(_p2.get("profitRatio", 0) or 0)
                    unrealized += _pct2 * _im2
                print(f"[PNL RAPOR] unrealized={unrealized:.4f} USDT ({len(_pos_data2)} poz)")
            else:
                print(f"[PNL RAPOR] open_positions bos")
        except Exception as _pe2:
            print(f"[PNL RAPOR] unrealized hata: {_pe2}")
        unrealized_pct = (unrealized / kullanilan * 100) if kullanilan > 0 else 0.0
        print(f"[PNL RAPOR] unrealized_pct={unrealized_pct:.2f}%")

        gun = gun_str()

        # Gün başı bakiyesi kaydet (ilk raporda)
        with _pnl_kilit:
            if gun not in _pnl_baslangic_bak:
                _pnl_baslangic_bak[gun] = bakiye

        donem_bitis = time.time()
        donem_bas   = donem_bitis - 86400  # 24 saat

        # Görsel
        img = _pnl_rapor_gorsel(gun, bakiye, kullanilan, unrealized, unrealized_pct)
        # Metin
        metin = _pnl_rapor_metin(gun, donem_bas, donem_bitis)

        base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        if img and MEXC_NOTIFY_CHAT_ID:
            requests.post(
                f"{base}/sendPhoto",
                data={"chat_id": MEXC_NOTIFY_CHAT_ID,
                      "caption": metin,
                      "parse_mode": "HTML"},
                files={"photo": ("pnl_rapor.png", img, "image/png")},
                timeout=30
            )
        elif MEXC_NOTIFY_CHAT_ID:
            requests.post(
                f"{base}/sendMessage",
                json={"chat_id": MEXC_NOTIFY_CHAT_ID,
                      "text": metin, "parse_mode": "HTML"},
                timeout=15
            )
        print(f"[PNL RAPOR] Gonderildi — {gun} {len(_pnl_kayitlar.get(gun, []))} islem")

    except Exception as e:
        print(f"[PNL RAPOR] Hata: {e}")


def _pnl_rapor_zamanlayici():
    """15 dakikada bir PNL raporu gönderir.
    Gece 00:00-00:15 arasında günlük kayıtlar sıfırlanır.
    """
    import datetime as dt_mod
    ARALIK_DK = 15  # Kaç dakikada bir
    print(f"[PNL RAPOR] Zamanlayici basladi. Her {ARALIK_DK} dakikada bir rapor gonderilecek.")
    while True:
        try:
            simdi = datetime.now(tz=TR_TZ) if TR_TZ else datetime.utcnow()

            # Sonraki 15 dakika dilimini hesapla (00, 15, 30, 45)
            import datetime as dt_mod
            gecen_dk = simdi.minute % ARALIK_DK
            bekle_dk = ARALIK_DK - gecen_dk
            sonraki = (simdi.replace(second=0, microsecond=0)
                       + dt_mod.timedelta(minutes=bekle_dk))

            bekle = (sonraki - simdi).total_seconds()
            print(f"[PNL RAPOR] Sonraki rapor: {sonraki.strftime('%H:%M')} ({int(bekle//60)} dk sonra)")
            time.sleep(max(bekle, 10))

            _pnl_rapor_gonder()

            # Gece 00:00-00:15 arasında günlük kayıtları sıfırla
            simdi_yeni = datetime.now(tz=TR_TZ) if TR_TZ else datetime.utcnow()
            if simdi_yeni.hour == 0 and simdi_yeni.minute < ARALIK_DK:
                with _pnl_kilit:
                    _pnl_kayitlar.clear()
                    _pnl_baslangic_bak.clear()
                print("[PNL RAPOR] Gece 00:00 — PNL kayitlari sifirlandi.")

            time.sleep(65)  # double-fire önleme

        except Exception as e:
            print(f"[PNL RAPOR ZAMANLAYICI] Hata: {e}")
            time.sleep(60)

def _pnl_zamanlayici():
    """Saatlik PNL devre dışı — 05:59/11:59/17:59/23:59 rapor sistemi kullanılıyor."""
    print("[PNL] Saatlik zamanlayici devre disi (4 gunluk rapor sistemi aktif).")

threading.Thread(target=_pnl_zamanlayici, daemon=True).start()
print("[PNL] Saatlik PNL zamanlayicisi basladi.")
threading.Thread(target=_pnl_rapor_zamanlayici, daemon=True).start()
print("[PNL RAPOR] 15 dakikada bir rapor zamanlayicisi basladi.")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Sunucu baslatiliyor -> http://0.0.0.0:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
