ONAYLANDI — 2026-10-19 (kullanıcı; §10 seçenek (a), tam seri)

> Bu belge onaylanmadan hiçbir ücretli çağrı yapılmaz. Her aşama (C1 duman, C2 ana koşu) kullanıcı o aşama için "BAŞLA" deyince başlar.

# Deney C ön kaydı (prereg_expC): Grup büyüdükçe ne olur? Dört kişilik gruplardan öğrenilen kuralın ölçek tahmini

- **Tarih:** 2026-10-19. Veriden önce yazıldı.
- **Yazan:** Claude, kullanıcının isteğiyle ("iddialı olsun, bilime bir şey katsın"; büyüklük serisi önerisine "olur"). Bu bir iç yazılı plandır, kamuya açık bir kayıt değildir.
- **Taslak geçmişi:** ilk taslak (yalnız 8 kişilik gruplar) commit `5f64f3d`'dedir. Onaylanmadan ve hiçbir veri toplanmadan bu ikinci taslakla değiştirildi. Gerekçe: o taslağın kendi ön bakışına göre 8 kişide etki ılımlı kalıyordu; tek boyutlu bir test ölçek sorusunu cevaplamaz.
- **İlişkisi:** ana deney (`prereg_main.md`), Deney B (`prereg_expB.md`, dondurulmuş kural), dinamik analizler (`prereg_dyn.md`).

## 0. Sonuç (önce bu)

1. **Soru:** 4 kişilik gruplardan öğrenilip dondurulan R3 kuralı, grup büyüdükçe (4 → 8 → 16 → 32) toplu davranışın nasıl değişeceğini **önceden** tahmin edebilir mi?
2. **Kuralın tahmini (ön bakış, §2):** iki model ters yönde ölçekleniyor.
   - **Mistral:** grup büyüdükçe işbirliği çöküyor. 8. turda çöküş bölgesindeki grup payı 4 / 8 / 16 / 32 kişide 0,39 / 0,58 / 0,77 / 0,88.
   - **GPT:** büyüdükçe çökmüyor, hafifçe daha dayanıklı: 0,23 / 0,19 / 0,16 / 0,15.
   - **Neden:** Mistral'ın kuralında "ötekilerden biri 0 verdi" güçlü bir tetikleyici; kalabalıkta biri neredeyse her zaman 0 verir. GPT ötekilerin ortalamasına bakıyor; kalabalıkta ortalama daha az oynar.
   - **İzole cevap kuralı (R0) ölçek etkisi öngörmüyor:** Mistral 0,30 / 0,30 / 0,32 / 0,29.
3. **Neden önemli:** doğrulanırsa, bireysel kuraldan **topluluğun ölçeklenmesini** önceden söyleyen bir yasa olur. Bu, "4 kişilik grup küçük bir sistem" itirazının cevabıdır. Ters yönlü iki tahmin aynı anda tutarsa tesadüfle açıklanamaz. Tutmazsa da bilgi verir: tek bir 0'a tepki grup büyüklüğüyle değişiyor demektir, yani küçük grupta ölçülen kural büyük topluluğa taşınamaz. İki sonuç da önceden yazıldığı için raporlanır.
4. **Tasarım (önerilen):**
   - GPT: 4, 8, 16 ve 32 kişilik gruplar, her büyüklükte 48 grup;
   - Mistral: 4, 8 ve 16 kişilik gruplar, her büyüklükte 24 grup;
   - 4 minimal kart, 10 tur. 4 kişilik gruplar eşzamanlı kontroldür.
   - İstem ana deneyle aynıdır; yalnız oyuncu sayısı ve kural anlama sorusundaki örnek değişir.
5. **Maliyet (kaba; kesin değer C0 dry-run'ından):** ≈ 64 USD (Mistral ≈ 57, GPT ≈ 6). Duman (C1) ≈ 3 USD. Daha ucuz seçenekler §10'da.
6. **Kullanıcı kararları:** §10.

## 1. Soru ve gerekçe

- **Önceki testler:** Deney B kuralı daha uzun bir oyuna (10 → 15 tur) taşıdı ve tuttu (prereg_expB F-B.3). Dinamik analizler (prereg_dyn D.2) kuralın grup düzeyindeki yapıyı da ürettiğini gösterdi: çöküş tuzağı, yapışkan işbirliği, DeepSeek ve Mistral'da tek bedavacıda devrilme.
- **Kural büyüklükten bağımsız özelliklerle tanımlı:** kendi önceki katkı, ötekilerin ortalaması, "ötekilerden biri 0 verdi mi", kalan tur. Bu yüzden her n için doğrudan bir tahmin üretir. Büyüklüğe en duyarlı özellik "ötekilerden biri 0 verdi mi"dir: n − 1 ötekinden en az birinin 0 vermesi n büyüdükçe daha olası.
- **İki yön önceden yazılıyor:**
  - (a) ajanlar n kişide de 4 kişideki gibi "tek bir 0"a tepki verir → kural tutar: Mistral'da çöküş artar, GPT'de artmaz;
  - (b) ajanlar büyük grupta tek bir 0'a hoşgörülü olur ("31 kişiden biri") → kural Mistral'da çöküşü fazla öngörür. Bu durumda tetikleyici büyüklüğe taşınmıyor demektir.
- **Başka iki seçenek de yazılıyor:**
  - (c) her iki modelde de büyüklükle genel bir düşüş olur (sorumluluğun dağılması gibi). Bu durumda GPT'nin tahmini tutmaz.
  - (d) hiçbir modelde değişim olmaz. Bu R0'ın tahminidir.
- **İnsan bağlamı (yalnız bağlam, sınanmıyor):** sabit MPCR'de grup büyüklüğü insanların katkısını düşürmedi (Isaac, Walker & Williams, 1994; DOI 10.1016/0047-2727(94)90068-X Crossref'te doğrulandı; içerik yazıya geçmeden makalenin metninden kontrol edilecek).

## 2. Ön bakış (resmi tahmin değil; resmi tahmin C0'da dondurulur)

- **Yöntem:**
  - dondurulmuş R3 tabloları (`data/expB/frozen_rules_v1.json`, sha256 `62b2bae7bcf6560f022181ff5b0813fec4747f2b8e3e13e5dd1301931fbd93d1`) kullanıldı;
  - kalan tur dilimleri, 10 tur;
  - her ajanın 1. turu, hücrenin Aşama 1'deki 1. tur kararlarından bağımsız çekildi (büyüklüğün 1. turu değiştirmediği varsayımıyla);
  - hücre ve n başına S = 3 000 grup;
  - durum hesabında ötekilerin ortalaması n − 1 kişi üzerinden, "ötekilerden biri 0" n − 1 kişi üzerinden alındı;
  - R0 hücrenin izole f'i ile, aynı başlangıçlardan hesaplandı.
- **Kod:** oturumun scratchpad'inde, sabit seed'le. Hiçbir gözlem verisi kullanılmadı (C koşusu yok). Resmi tahmin C0'da depodaki bir betikle yeniden üretilir ve sha256 ile kilitlenir.

**Minimal kartların ortalaması, 8. turda çöküş bölgesindeki grup payı (ortalama katkı, tur 2–10):**

| model | n = 4 | n = 8 | n = 16 | n = 32 |
|---|---|---|---|---|
| Mistral, kural | 0,39 (6,46) | 0,58 (5,20) | 0,77 (3,76) | 0,88 (2,83) |
| Mistral, R0 | 0,30 (7,96) | 0,30 (7,81) | 0,32 (7,67) | 0,29 (7,63) |
| GPT, kural | 0,23 (7,24) | 0,19 (6,78) | 0,16 (6,52) | 0,15 (6,46) |
| GPT, R0 | 0,07 (8,81) | 0,01 (8,80) | 0,00 (8,81) | 0,00 (8,82) |
| DeepSeek, kural | 0,95 (0,77) | 0,99 (0,43) | 0,99 (0,58) | 1,00 (0,77) |

- **Kartlar:**
  - Mistral'da dört kartta da kural, büyüdükçe çöküş payını artırıyor (Boston 0,52 → 0,92, Kopenhag 0,24 → 0,53, Atina 0,42 → 0,87, Riyad 0,37 → 0,78; n = 4 → 16).
  - GPT'de üç kartta pay düşüyor (ör. Atina 0,22 → 0,00), Riyad'da 0,39 → 0,58'e çıkıp orada kalıyor.
- **DeepSeek** minimal kartlarda zaten tabanda; bu deneyde bilgi vermez, tasarıma alınmadı.
- **GPT'de kural ve R0 aynı yönde** (artış yok). GPT, kuralı R0'dan ayırt etmez; (c) seçeneğini (genel ölçek düşüşü) sınar. Kuralı R0'dan ayıran test Mistral'dır.

## 3. Tasarım

### 3.1 Ana deneyle aynı olanlar

- Çerçeve `abstract_v4` (kural metni, karar sorusu, geçmiş gösterimi), cevap biçimi A, koşul N, homojen gruplar, bağış 20, MPCR 0,4, 10 tur [prereg_main §2].
- Modeller, sağlayıcılar ve istek ayarları: Mistral → mistral, GPT → openai. `temperature` ve `reasoning_effort` gönderilmez; `max_tokens` 16 000 [prereg_main §2.2].
- Durma ve sürdürme kuralları (prereg_main §10; F.8 `length` → sürdür; 429 / 5xx → bekle ve sürdür).

### 3.2 Farklar

1. **Grup büyüklüğü** `params.group_size` ∈ {4, 8, 16, 32}. İstemdeki oyuncu sayıları ("A group has n players: you and n − 1 others" vb.) ve geçmiş satırının uzunluğu çerçevedeki `{n}` yer tutucularından gelir. Karar istemlerinin metni değişmez.
2. **Kural anlama sorusu q1.** Motor q1'deki örnek listesinin n − 1 öteki içermesini şart koşuyor. Bu yüzden her n > 4 için bir çerçeve kopyası hazırlanır (`abstract_v4_n8`, `_n16`, `_n32`); yalnız q1 değişir.
   - Örnek liste, ana deneydeki örnekten (4, 12, 16) başlayan sabit bir desenin (4, 12, 16, 0, 8, 20, 2) tekrarıyla n − 1 sayıya tamamlanır.
   - Anahtar motor tarafından hesaplanır (20 − 8 + 0,4 × (8 + toplam)).
   - q2 aynı (anahtar −6).
   - **4 kişilik kontrol `abstract_v4`'ü bayt bayt aynen kullanır.**
   - C0 testi: her n için `_nN` çerçevesinin karar istemleri, `abstract_v4`'ün aynı n'deki istemleriyle bayt bayt aynıdır; fark yalnız q1 satırındadır.
3. **Kartlar:** 4 minimal kart (`cards/expA_cards_v1.json` ile aynı metinler).
4. **Modeller, büyüklükler, G:**

| model | n | kart başına grup | grup | ajan | yanıt (n × 11 × grup) |
|---|---|---|---|---|---|
| GPT | 4 | 12 | 48 | 192 | 2 112 |
| GPT | 8 | 12 | 48 | 384 | 4 224 |
| GPT | 16 | 12 | 48 | 768 | 8 448 |
| GPT | 32 | 12 | 48 | 1 536 | 16 896 |
| Mistral | 4 | 6 | 24 | 96 | 1 056 |
| Mistral | 8 | 6 | 24 | 192 | 2 112 |
| Mistral | 16 | 6 | 24 | 384 | 4 224 |

   İzole kol yok; R0 için Aşama 1 hücrelerinin izole f'i kullanılır.
5. **Mistral n = 32 yok:** maliyet (≈ 87 USD tek başına). n = 16'da kuralın tahmini zaten 0,77.

## 4. Tahminlerin dondurulması (C0, ücretli çağrıdan önce)

- **Betik** `pgg_analysis_expC.py forecast`:
  - dondurulmuş R3 (sha256 kontrolüyle) ve hücrelerin izole f'i;
  - genel n için durum hesabı.

  n = 4'te durumların Aşama 1 / Deney B koduyla birebir aynı çıktığı test edilir.
- **Koşulsuz tahmin:** model × kart × n için, kural (R3, kalan tur dilimleri) ve R0 ile:
  - ortalama yörünge;
  - 8. turda çöküş payı;
  - n = 4'e göre fark.

  1. tur §2'deki gibi çekilir. S = 4 000, seed `stable_seed("pgg-expC-forecast", model, kart, n)`.
- **Çıktı:** `data/expC/forecast_v1.json`. Dosyanın sha256'ı ilk ücretli çağrıdan önce bu dosyaya ek olarak yazılır ve commit edilir.
- **Koşullu tahmin** (hipotezlerin asıl karşılaştırması): koşudan sonra, her gerçek grubun gözlenen 1. turundan, aynı kural ve aynı seed kuralıyla hesaplanır (grup başına S = 500). Kural ve kod C0'da dondurulur. Böylece 1. turun büyüklükle değişmesi tahmini bozmaz.

## 5. Hipotezler ve karar kuralları

**Ortak tanımlar:**
- m_t, n ajanın t. turdaki ortalama katkısıdır.
- Çöküş bölgesi m₈ ≤ 2,5, yani 8. tur (orta oyunun sonu; prereg_dyn ile aynı).
- Bootstrap gruplar üzerinden yapılır (10 000 tekrar), kart içinde tabakalı; yüzdelik %95 CI.
- Etiketler model başınadır; düzeltme yok.

**C-H1 — ölçek yönü (birincil).**
- **Ölçü:** Δ = (8. turda çöküş payı, en büyük n) − (aynı model, eşzamanlı n = 4). En büyük n: Mistral 16, GPT 32.
- **Etiketler:**
  - CI 0'ın üstünde → "artış";
  - CI 0'ın altında → "azalış";
  - CI ±0,10 içinde → "değişim yok";
  - diğer → "belirsiz".
- **Okuma** (kuralın koşullu Δ tahmini de raporlanır):
  - **Mistral:** kural "artış" öngörüyor (koşulsuz +0,39), R0 "değişim yok" (+0,02). "Artış" → kural lehine. "Değişim yok" ya da "azalış" → kural aleyhine, (b) ya da (d).
  - **GPT:** kural artış öngörmüyor (koşulsuz −0,08). "Artış" → kural aleyhine, (c). "Değişim yok" ya da "azalış" → kuralla uyumlu (R0 ile de).
  - **"Ters yönlü ölçek doğrulandı"** yalnız iki koşul birlikte sağlanırsa yazılır: Mistral "artış" ve GPT "artış" değil.
- **Güç notu:** Mistral'da kart başına 6 grupla CI yarı genişliği ≈ 0,25. +0,39'luk bir artış saptanabilir, ama "değişim yok" (±0,10) etiketi pratikte çıkamaz. GPT'de 48 + 48 grupla CI yarı genişliği ≈ 0,15.

**C-H2 — aktarım (birincil), model × n (n ≥ 8; n = 4 kontrol olarak ayrıca).**
- **Ölçü:** model × n hücresinde, kartlar üzerinden ortalama alınarak (gözlenen − kuralın koşullu tahmini) ortalama katkı, tur 2–10.
- **Etiketler** (Deney B'nin B-H1 kuralı):
  - CI ±2 içinde → "tahmin tuttu"; ±1 içinde → "(sıkı eşdeğerlik)";
  - |tahmin| > 2 ve p < 0,05 → "tahmin sapıyor: gerçek daha düşük / yüksek";
  - diğer → "belirsiz".
- **Kaç test:** 5 (Mistral 8, 16; GPT 8, 16, 32). Model içinde Holm, sapma etiketleri için.

**C-H3 — makro aktarım (ikincil).**
- **Ölçü:** model × n'de 8. turda çöküş payı, gözlenen − kuralın koşullu tahmini (grup başına olasılık).
- **Etiketler:**
  - fark ve CI ±0,15 içinde → "yeniden üretiyor";
  - CI tümüyle dışında → "sapıyor (gerçek daha yüksek / düşük)";
  - diğer → "belirsiz".
- Mistral'da 24 grupla "yeniden üretiyor" etiketi zor çıkar (CI ≈ ±0,17); bu yüzden ikincil.

**C-H4 — eğri (betimsel).**
- Her model için çöküş payı ve ortalama katkı log₂ n'ye karşı: gözlenen, kural (koşullu ve koşulsuz) ve R0. Eğim bootstrap CI ile verilir. Etiket yok.

**Mekanizma (betimsel, etiketsiz).**
- **Koşul:** ajan bir önceki turda ≥ 10 vermiş ve ötekilerin ortalaması ≥ 5.
- **Ölçü:** ötekilerden biri 0 verdiyse ajanın 0 verme payı, vermediyse 0 verme payı. Her n'de ve 4 kişide (eşzamanlı kontrol ve Aşama 1) raporlanır.
- **Yorum:** (a) ve (b) arasındaki ayrımın doğrudan ölçüsüdür. "Tek 0" tepkisi n ile azalıyorsa, kuralın sabit tablosu bunu bilemez.

**R0:** koşullu tahmini ve gözlenenle farkı her hipotezde raporlanır (etiketsiz).

**Duyarlılık:**
- kural anlama sorularının ikisini de doğru cevaplayan ajanların grupları (etiket değişirse raporlanır);
- `reasoning_capped` ya da `length` içeren gruplar çıkarılarak;
- Mistral C-H1'de eşzamanlı kontrol yerine tarihsel 4 kişilik gruplarla (Aşama 1 ve Deney A B kolu, aynı kartlar).

## 6. Analiz

- **Betik** `pgg_analysis_expC.py`: `forecast` ve `analyse` alt komutları; eksik koşuda çalışmayı reddeder. Grup dizileri genel n'ye uyarlanır.
- **Sentetik testler:** cevabı bilinen dünyalar.
  - n = 4'te durum hesabı Aşama 1 koduyla aynı.
  - "Tek 0 herkesi düşürür" dünyasında n büyüdükçe çöküş artar → C-H1 "artış".
  - "Yalnız ortalamaya bakar" dünyasında n'nin etkisi yok → C-H1 "değişim yok" (büyük G ile).
  - "Büyük grupta 0'a hoşgörü" dünyasında C-H3 "sapıyor (gerçek daha düşük)".
  - Kural anlama anahtarları her n için doğru.
  - İstem farkı yalnız q1'de.
- API çağrısı yok. Sonuç `results/expC_main_<tarih>_analysis.json`; sha256 bu dosyaya yazılır.

## 7. Aşamalar ve maliyet

| aşama | ne | maliyet |
|---|---|---|
| C0 | `_nN` çerçeveleri, config'ler, `forecast` ve dondurma, analiz betiği ve testleri, dry-run maliyet hesabı, n = 32 istem uzunluğu kontrolü | ücretsiz |
| C1 | duman: her model × n için 1 grup (kart sırayla); muhakemeler tasarım kusuru için okunur (özellikle n = 16 / 32'de geçmiş satırının okunması ve q1) | ≈ 3 USD |
| C2 | ana koşu | ≈ 64 USD |

- **Kaba hesap:**
  - yanıt başı ortalama maliyet: Mistral ~6,4, GPT ~0,14 USD / 1 000 yanıt (önceki deneylerden);
  - istem uzunluğu çarpanı n = 8 / 16 / 32 için × 1,15 / 1,3 / 1,6 (tahmin; kesin değer dry-run'dan).
- **Model başına:**
  - GPT: 0,3 + 0,7 + 1,5 + 3,8 ≈ 6,3 USD;
  - Mistral: 6,8 + 15,5 + 35,1 ≈ 57,4 USD.
- **Kesin tavanlar:** C0 dry-run'ından, önceki deneylerdeki kuralla (p95 üst sınır; beklenen maliyet × 1,1 kapı).
- **Süre:** Mistral 7 392, GPT 31 680 yanıt; tahminen 1–2 gün (3 paralel birim, izleyiciyle).

## 8. Durdurma ve sürdürme

prereg_main §10 ve F.8 aynen uygulanır. İzleyici (`watch_s1b.py` mantığı) şu durumlarda otomatik sürdürür:
- `length` sonrası;
- 429 (300 s bekle, ikinci 429'dan sonra 3 paralel);
- parse hatası (30 s);
- 5xx (600 s).

Başka bir durmada kullanıcıya bildirir. Büyük gruplarda bir turdaki n çağrı aynı anda gidebilir; Mistral'da hız sınırı riski C1'de ölçülür.

## 9. Sınırlılıklar

- 32 kişi de büyük bir nüfus değil. Bu deney kuralın büyüklüğe **taşınmasını** ve ölçek yönünü sınar, büyük nüfuslarda ortaya çıkışı değil.
- **İstem uzunluğu büyüklükle birlikte artar** (geçmiş satırında n sayı). Büyüklük etkisi ile uzun istem etkisi bu tasarımda ayrılamaz.
- **q1'deki liste n ile uzar;** soru zorlaşır. Kural anlama dışlama ölçütü değildir, yalnız duyarlılıktır.
- **MPCR 0,4 sabit;** grubun bir puandan toplam getirisi n × 0,4 (4 kişide 1,6; 32 kişide 12,8). Bu, insan deneylerindeki standart "sabit MPCR" karşılaştırmasıdır.
- **Kural büyük gruplarda 4 kişide az görülen durumlara gider.** Ör. "biri 0 verdi" iken ötekilerin ortalaması yüksek: 4 kişide (0, 10, 10, 10)'da görüldü, 32 kişide çok sık. Geri çekilme oranları raporlanır.
- **Homojen gruplar, tek sağlayıcı, ağ yok.** Mistral'da G küçük (C-H1 güç notu).

## 10. Kullanıcı kararları

1. **Kapsam (önerilen: tam seri, ≈ 64 USD).** Seçenekler:
   - (a) tam seri, önerilen: GPT 4 / 8 / 16 / 32, Mistral 4 / 8 / 16 → ≈ 64 USD;
   - (b) Mistral n = 8 olmadan (GPT tam, Mistral 4 / 16) → ≈ 48 USD; eğri Mistral'da iki noktaya iner;
   - (c) Mistral kart başına 10 grup (daha güçlü C-H1 ve C-H3) → ≈ 102 USD;
   - (d) yalnız GPT serisi → ≈ 6 USD. Kural ile R0'ı ayırt etmez; yalnız "genel ölçek düşüşü" (c) seçeneğini sınar.
2. **Duman (C1):** her model × n için 1 grup, ≈ 3 USD (önerilen).
3. **Onay:** onaylanırsa C0'a geçilir (ücretsiz). C1 ve C2 için ayrıca "BAŞLA".

**Kayıt (2026-10-19, kullanıcı):** "onaylıyorum, a seçeneği, C0'a geç". Kapsam (a): GPT n = 4 / 8 / 16 / 32 (kart başına 12 grup), Mistral n = 4 / 8 / 16 (kart başına 6 grup); C1 duman önerildiği gibi. C1 ve C2 yine ayrı "BAŞLA" ister.

## Değişiklik günlüğü

- 2026-10-19: ilk taslak (yalnız n = 8; commit `5f64f3d`).
- 2026-10-19: onay (kullanıcı, seçenek (a)); metin değişmedi, yalnız üst satır ve §10 kaydı.
- 2026-10-19: ikinci taslak. Büyüklük serisine çevrildi (GPT 4 / 8 / 16 / 32, Mistral 4 / 8 / 16; eşzamanlı 4 kişilik kontrol). Hipotezler ölçek yönü (C-H1), aktarım (C-H2), makro aktarım (C-H3) ve eğri (C-H4) olarak yeniden yazıldı. Onaydan ve veriden önce.

## Ek F-C.1 — C0: dondurulan tahmin, çerçeveler, config'ler ve bütçe tavanları (2026-10-19, ücretli çağrıdan önce)

- **Kod:** commit `cf8850c`: `pgg_analysis_expC.py`, çerçeveler, config'ler ve 13 test; tam paket 617 test geçti. Testlerin kapsadığı yerler:
  - n = 4'te durum hesabı Aşama 1 koduyla aynı;
  - R0, Deney B koduyla aynı;
  - sentetik dünyalar: "tek 0 tetikler", "büyük grupta hoşgörü", "değişim yok";
  - her n'de karar istemleri `abstract_v4` ile bayt bayt aynı;
  - 8 kişilik bir grubun motorda sahte API ile uçtan uca oynanması.
- **Çerçeveler** (yalnız q1 farklı; q1 örneği n − 1 öteki listeler; desen 4, 12, 16, 0, 8, 20, 2 tekrarlanır):

  | çerçeve | sha256 | öteki sayısı | anahtar (q1 / q2) | not |
  |---|---|---|---|---|
  | `abstract_v4_n8` | `9de2ef2c5439d99e70314c65ef675f2e1950ee7650e973d1c0f06bd3af7b8968` | 7 | 40 / −6 | |
  | `abstract_v4_n16` | `4af2135903a53c94e03fd31136a07637b57b38053b70fa9b9a4ce84fcc4a4c6b` | 15 | 68 / −6 | son değer 4 → 8 |
  | `abstract_v4_n32` | `c6ac2b296044d2bf494631bad70e322121bf856a9ece203c5274ab6e70a48aa3` | 31 | 128 / −6 | son değer 16 → 18 |

  - Son değer, cevabın tam sayı olması için yükseltildi (0,4 × toplam tam sayı olmalı; motor bunu şart koşuyor). Bu, §3.2'deki "desen tekrarı" kuralının uygulama ayrıntısıdır.
  - 4 kişilik kontrol `abstract_v4`'ü (sha256 `c00db315…a9f4`) aynen kullanır.
- **Koşulsuz tahmin (dondurulan):** `data/expC/forecast_v1.json`, sha256 `00d88e05fed5dcede000a5d2a9e56287383e752787ba2554562f2e21099be9df`. Hesap: S = 4 000, seed `stable_seed("pgg-expC-forecast", model, kart, n)`, dondurulmuş R3 (sha256 `62b2bae7…d93d1`).

  **Minimal kartların ortalaması, 8. turda çöküş bölgesindeki grup payı (ortalama katkı, tur 2–10):**

  | model | kural | n = 4 | n = 8 | n = 16 | n = 32 |
  |---|---|---|---|---|---|
  | Mistral | R3 | 0,373 (6,54) | 0,570 (5,25) | 0,772 (3,83) | — |
  | Mistral | R0 | 0,297 (7,97) | 0,298 (7,82) | 0,311 (7,70) | — |
  | GPT | R3 | 0,228 (7,25) | 0,188 (6,84) | 0,158 (6,50) | 0,146 (6,46) |
  | GPT | R0 | 0,063 (8,82) | 0,013 (8,84) | 0,000 (8,84) | 0,000 (8,82) |

  - **C-H1 karşılaştırma noktaları (koşulsuz, n büyük − n = 4):** Mistral R3 +0,399, R0 +0,014; GPT R3 −0,083, R0 −0,063.
  - **Kartlar, R3, n = 4 → en büyük n:**
    - Mistral: Boston 0,51 → 0,91, Kopenhag 0,23 → 0,54, Atina 0,41 → 0,86, Riyad 0,34 → 0,78;
    - GPT: Boston 0,17 → 0,00, Kopenhag 0,14 → 0,00, Atina 0,21 → 0,00, Riyad 0,40 → 0,58.
- **Config'ler ve bütçe tavanları** (C0 dry-run, önceki deneylerin kuralıyla):
  - sert tavan = toplam p95 üst sınırın yukarı yuvarlanması;
  - model alt tavanı ≥ model p95 (1 USD altı 0,1'e yuvarlanır);
  - kapı = ortalama × 1,1, yukarı yuvarlanır.

  | config | çağrı | ortalama / p95 (USD) | sert tavan | alt tavanlar | kapı |
  |---|---|---|---|---|---|
  | `expC_n4_main` | 3 168 | 7,82 / 13,29 | 14 | Mistral 13, GPT 0,5 | 9 |
  | `expC_n8_main` | 6 336 | 15,79 / 26,78 | 27 | Mistral 26, GPT 2 | 18 |
  | `expC_n16_main` | 12 672 | 32,20 / 54,40 | 55 | Mistral 53, GPT 3 | 36 |
  | `expC_n32_main` | 16 896 | 3,21 / 5,03 | 6 | GPT 6 | 4 |
  | **C2 toplam** | 39 072 | **59,02 / 99,50** | 102 | | |
  | `expC_n4_smoke` (Boston) | 88 | 0,32 / 0,54 | 1 | Mistral 0,6, GPT 0,1 | 1 |
  | `expC_n8_smoke` (Kopenhag) | 176 | 0,65 / 1,09 | 2 | Mistral 2, GPT 0,1 | 1 |
  | `expC_n16_smoke` (Atina) | 352 | 1,31 / 2,22 | 3 | Mistral 3, GPT 0,1 | 2 |
  | `expC_n32_smoke` (Riyad) | 352 | 0,07 / 0,10 | 1 | GPT 0,2 | 1 |
  | **C1 toplam** | 968 | **2,35 / 3,97** | 7 | | |

  - Dry-run'ın istem ölçeği tahmini (karakter oranı): n = 4 / 8 / 16 / 32 için × 0,95 / 1,06 / 1,31 / 1,79.
  - Planın kaba hesabı ≈ 64 USD idi; dry-run ortalaması 59 USD.
- **Koşular:** her büyüklük ayrı bir koşudur. Koşu adları `expC_n{n}_{smoke|main}_<tarih>`, seed ad alanları `pgg-expC-n{n}` ve `pgg-expC-n{n}-smoke`. Aşama: C2 için `stage` "1" (kod sürümü kilidi), C1 için "0b".
- **Sıradaki adım:** C1 duman testi, kullanıcı "BAŞLA C1" deyince. C1 verisi analize girmez; muhakemeler okunur (bkz. §7).

- **Düzeltme (2026-10-19):** F-C.1 tablosunda C1 toplam p95 3,96 USD olmalı (0,5438 + 1,0948 + 2,2212 + 0,1047); 3,97 yazıldı (yuvarlama). Tavanlar etkilenmez.

## Ek F-C.2 — Plan ve tahmin Zenodo'da herkese açık (2026-10-19)

- **Kayıt:** https://doi.org/10.5281/zenodo.23483296 ("Pre-registered forecast: how cooperation among LLM agents changes with group size (Experiment C)"). Kullanıcı yükledi, CC BY 4.0. Oluşturulma zamanı 2026-10-19 20:04:55 UTC (23:04 Türkiye saati).
- **Dosya:** `expC_prereg_f258798.zip`, md5 `b77109baf7940a5ecef15056b97b399c`. Yereldeki paketle aynı. Paket commit `f2587985ed2dd8cc6c8288a88cd34b22a525e020`'den `scripts/build_zenodo_expC.py` ile kuruldu.
- **İçerik:**
  - bu planın F-C.1 dahil hali;
  - dondurulmuş kural tabloları (sha256 `62b2bae7…d93d1`);
  - dondurulmuş tahmin (sha256 `00d88e05…be9df`);
  - kod, çerçeveler, config'ler ve İngilizce README.

  Paketi açıp tek başına sınadım: bütün sha256'lar tuttu ve tahmin paketteki koddan birebir yeniden üretildi.
- **Yükleme anındaki durum:** C1 duman koşuları 19:51 UTC'de başlamıştı ve sürüyordu. Hiçbir C2 (ana koşu) verisi yoktu, C2 başlatılmamıştı. README'deki "A smoke test … ran on 2026-10-19" ifadesi yükleme anında "sürüyordu" anlamındadır. C1 verisi plana göre analize girmez.
- **Değişiklik kuralı:** C1 okuması bir tasarım değişikliği gerektirirse değişiklik bu dosyaya tarihli ek olarak yazılır ve Zenodo'ya C2'den önce yeni bir sürüm olarak yüklenir. Dondurulmuş tahmin değişmez.

## Ek F-C.3 — C1 duman testi sonucu (2026-10-19): tasarım değişikliği yok, GPT bütçe tavanları yükseltildi

- **Koşular:** `expC_n{4,8,16,32}_smoke_20261019`, kod `53a27d7` (temiz kopya `_kod_53a27d7…`); 19:51 UTC'de birlikte başladı. Grup sayıları ve kartlar:
  - n = 4: 2 grup, Boston;
  - n = 8: 2 grup, Kopenhag;
  - n = 16: 2 grup, Atina;
  - n = 32: 1 grup, Riyad (yalnız GPT).

  Hepsi tamam, tek segment, `stop_reason` yok, otomatik sürdürme gerekmedi. Satırlar 88 / 176 / 352 / 352. Sonuç dosyalarının sha256'ları:

  | n | sha256 |
  |---|---|
  | 4 | `c3fba5d41461ffd9fcbb9fa846db499496085e2116611e671fba13bfe4c09caa` |
  | 8 | `cd0f11368a28acc1c35db6549603029f427853a7e183cadd653c18dbb9004b1b` |
  | 16 | `c1b3e82a4d5970af31ee4d1c6f32851332b2c5c2b728fe58bb9406cc3f8499c8` |
  | 32 | `a871277a8e2553a85c966d3af661cce89f4bc4c317a15b1b391bb68a0fa2692e` |

- **Tesisat:**
  - geçersiz ve parse_fail 0; `length` 0; `reasoning_capped` 0;
  - superseded / truncated / discarded 0;
  - model sürümleri önceki deneylerle aynı (GPT `-20260922`, Mistral `-20261006`);
  - n = 32'de sağlayıcı adı olmayan 3 yanıt kuralına göre yeniden istendi.
- **Kural anlama** (doğru / toplam):
  - Mistral: 4/4, 8/8, 16/16;
  - GPT: 4/4, 8/8, 16/16, 31/32. Tek hata n = 32'de q2'de bir aritmetik kayma: "−10 + 0,4 × 10 = 3".
- **Okuma** (yalnız istemin okunması):
  - n ≥ 8'de grubu 4 kişilik sanan kayıt yok. Mistral'ın muhakemelerinde grup büyüklüğü 8 kişide 206, 16 kişide 453 kez doğru anılıyor.
  - Diğer sayılar ("5 players", "13 players" vb.) alt kümeler ("5 kişi 0 verdi") ya da GPT özetlerinin gevşek ifadeleri.
  - Mistral'ın uzun geçmişte saydığı "0 veren sayısı" 16 kişide örneklenen 8 iddianın 8'inde doğru.
  - Bir kayıtta önce 1 eksik sayıp ("4 kişi 0 verdi"; doğrusu 5) aynı muhakemede listeyi yeniden okuyarak düzeltiyor.
  - GPT 32 kişide grup toplamını doğru okuyor (96). Bir özette katkı veren sayısı 1 fazla (9; doğrusu 8).
  - Sonuç: büyük gruplarda ara sıra sayım kayması var, ama geçmiş okunuyor ve kendi kendine düzeltiliyor. Bu bir tasarım kusuru değil; büyük grubun bilişsel yükünün parçası. Sınırlılık olarak raporlanır.
- **Dürüstlük notu:** okuma sırasında iki duman grubunun bazı katkıları görüldü:
  - n = 32 GPT grubunda 4–5. turlardan itibaren herkes 0 veriyor;
  - n = 16 Mistral grubunun 9. turunda 5 kişi 0, 11 kişi 10 veriyor.

  Duman verisi plana göre analize girmez ve tasarımda hiçbir şey değiştirilmedi; bu bilgi hiçbir karara girmedi.
- **Maliyet:** toplam 2,25 USD (tahmin 2,35). Gerçek / dry-run oranı:

  | model | n = 4 | n = 8 | n = 16 | n = 32 |
  |---|---|---|---|---|
  | Mistral | 0,95 | 0,89 | 0,94 | — |
  | GPT | 0,94 | 1,27 | 1,39 | 1,78 (sayılan; faturalanan 1,42) |

  GPT'nin istem başına maliyeti büyüklükle dry-run'ın varsaydığından hızlı artıyor.
- **Karar:**
  1. **Tasarım değişikliği yok;** dondurulmuş tahmin, hipotezler ve istemler aynen kalır. Zenodo'ya yeni sürüm gerekmez.
  2. **GPT bütçe tavanları yükseltildi.** Yalnız koşunun erken durmasını önlemek için; analizi etkilemez.
     - `expC_n16_main`: GPT alt tavanı 3 → 4 (p95 × 1,39 = 3,03);
     - `expC_n32_main`: sert tavan ve GPT alt tavanı 6 → 9 (p95 × 1,78 = 8,95).

     Diğer tavanlar ve kapılar aynı. C2'nin beklenen toplamı ≈ 58 USD (Mistral ≈ 49,7, GPT ≈ 8,7); sert tavanların toplamı 105 USD.
- **Sıradaki adım:** C2 bu değişiklikten sonraki commit'in kod kopyasıyla, kullanıcı "BAŞLA C2" deyince. Dört koşu (n = 4, 8, 16, 32) aynı anda başlar; izleyici F.8 / 429 / parse / 5xx kurallarıyla sürdürür.

## Ek F-C.4 — C2 öncesi tasarım (güç) analizi ve veri yolu kontrolü (2026-10-19, yalnız sentetik veri)

- **Amaç:** ücretli C2'den önce, önerilen grup sayılarıyla (Mistral kart başına 6, GPT 12) testlerin ne sıklıkla doğru etiketi vereceğini görmek. Hiçbir C2 verisi yok; duman verisi kullanılmadı.
- **Yöntem** (`scripts/power_expC.py`; seed 20261019):
  - **"Kural doğru" dünyası:** gruplar dondurulmuş R3 ile, 1. tur hücrenin Aşama 1 havuzundan çekilerek üretildi.
  - **"R0 doğru" dünyası:** aynı başlangıçlardan izole kural.
  - C-H1 için 300 tekrar, analiz kodunun kendi bootstrap ve etiket fonksiyonlarıyla (bootstrap 2 000).
  - C-H2 ve C-H3 için (Mistral, n = 16) 40 tekrar; koşullu tahmin S = 100, bootstrap 1 000.
- **Sonuç:**

  | test | dünya | etiket dağılımı |
  |---|---|---|
  | C-H1 Mistral (4 → 16) | kural doğru | "artış" 0,87, "belirsiz" 0,13 (ortalama Δ +0,40) |
  | C-H1 Mistral | R0 doğru | "artış" 0,03 (yanlış alarm), "belirsiz" 0,87, "değişim yok" 0,08, "azalış" 0,02 |
  | C-H1 GPT (4 → 32) | kural doğru | "artış" 0,00, "belirsiz" 0,80, "azalış" 0,20 |
  | C-H1 GPT | R0 doğru | "artış" 0,00, "azalış" 0,38, "değişim yok" 0,16, "belirsiz" 0,46 |
  | C-H2 Mistral n = 16 | kural doğru | 40/40 "tahmin tuttu" (28'i sıkı eşdeğerlik) |
  | C-H3 Mistral n = 16 | kural doğru | 7/40 "yeniden üretiyor", 33/40 "belirsiz" |

  - "Ters yönlü ölçek doğrulandı" etiketi kural doğruysa ≈ 0,87 olasılıkla çıkar, R0 doğruysa ≈ 0,03 olasılıkla.
  - C-H3, Mistral'da beklendiği gibi güçsüz (§5 güç notu). İkincil olduğu için tasarım değiştirilmedi.
  - GPT'de "artış yok" kuralla da R0 ile de neredeyse kesin. Bu kol yalnız (c) seçeneğini, yani genel bir ölçek düşüşünü sınar (§2).
- **Karar:** grup sayıları yeterli; tasarım değişmez.
- **Veri yolu kontrolü:** analiz kodunun okuyucusu (`pa.load_run` + `UnitsN`) dört duman koşusunun gerçek dosyalarında denendi. Yalnız biçime bakıldı: grup dizileri (1, 10, n), tamamlanmamış grup 0, kural anlama bayrakları okunuyor. Katkılar hesaplanmadı.
- **Not (yorum için):** `comp_full` duyarlılığı, bir grubu ajanlarından biri bile kural anlama sorusunda hata yaparsa dışarıda bırakır. Ajan başına küçük bir hata oranı bile büyük gruplarda çok sayıda grubu düşürür; ör. ajan başına %3 hatada 32 kişilik bir grubun hepsinin doğru olma olasılığı ≈ 0,38. Bu yüzden bu duyarlılık n ile karışır ve büyük n'de bilgi değeri düşüktür. Plan değişmez; raporda bu not verilir.
