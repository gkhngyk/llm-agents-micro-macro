TASLAK — kullanıcı onayı bekliyor (2026-10-19)

> Bu belge onaylanmadan hiçbir ücretli çağrı yapılmaz. Her aşama (C1 duman, C2 ana koşu) kullanıcı o aşama için "BAŞLA" deyince başlar.

# Deney C ön kaydı (prereg_expC): Dört kişilik gruplardan öğrenilen kural, sekiz kişilik grupları önceden tahmin edebilir mi?

- **Tarih:** 2026-10-19 (ilk taslak). Veriden önce yazıldı.
- **Yazan:** Claude, kullanıcının isteğiyle ("önerini yapalım"). Bu bir iç yazılı plandır, kamuya açık bir kayıt değildir.
- **İlişkisi:** ana deney (`prereg_main.md`), Deney B (`prereg_expB.md`, dondurulmuş kural), dinamik analizler (`prereg_dyn.md`). Bu deney, kuralı ilk kez **başka bir sistem boyutunda** ileriye dönük sınar.

## 0. Sonuç (önce bu)

1. **Soru:** 4 kişilik gruplardan öğrenilip dondurulan R3 kuralı, ajanların hiç oynamadığı **8 kişilik** grupların dinamiğini önceden tahmin edebilir mi? Kural grup büyüklüğüne bağlı bir **ölçek etkisi** öngörüyor mu, gerçekte bu etki çıkıyor mu?
2. **Neden önemli:** karmaşıklık bilimi okurunun ilk itirazı "4 kişilik grup küçük bir sistem" olur. Kural büyüklükten bağımsız özelliklerle tanımlı (kendi önceki katkı, ötekilerin ortalaması, "ötekilerden biri 0 verdi mi", kalan tur). Bu yüzden 8 kişilik gruplar için doğrudan bir tahmin üretir. İzole cevap kuralı (R0) ise yalnız ortalamaya baktığı için büyüklükten neredeyse etkilenmez.
3. **Ön bakış (§2, resmi tahmin değil):** kural yalnız **ılımlı** bir ölçek etkisi öngörüyor ve bu etki yalnız **Mistral'ın minimal kartlarında** belirgin:
   - 8. turda çöküş bölgesindeki grup payı 0,38 → 0,59;
   - ortalama katkı (tur 2–10) 6,51 → 5,17.

   GPT'de etki yok, DeepSeek'in minimal kartları zaten tabanda. R0 hiçbir modelde fark öngörmüyor. Bu deney "büyük bir ölçek etkisi" göstermek için değil, **kuralın yeni bir grup büyüklüğüne taşınıp taşınmadığını** sınamak için.
4. **Tasarım (önerilen):** Mistral ve GPT; 4 minimal kart; 8 kişilik homojen gruplar; 10 tur (eğitimle aynı; yalnız grup büyüklüğü değişir); kart başına 10 grup (model başına 40 grup). İstem ana deneyle aynı; yalnız oyuncu sayısı ve kural anlama sorusu 8 kişiye göre.
5. **Maliyet (kaba, kesin değer C0 dry-run'ından):** önerilen tasarım ~26 USD; bunun ~25,8 USD'si Mistral. Eşzamanlı 4 kişilik kontrol eklenirse ~38 USD; yalnız GPT ~1 USD. Duman koşusu (C1) ~3 USD.
6. **Kullanıcı kararları:** §10.

## 1. Soru ve gerekçe

- Deney B kuralı **daha uzun bir oyuna** (10 → 15 tur) taşıdı ve tuttu (prereg_expB F-B.3). Dinamik analizler (prereg_dyn D.2), kuralın grup düzeyindeki yapıyı da ürettiğini gösterdi: çöküş tuzağı, yapışkan işbirliği, DeepSeek ve Mistral'da tek bedavacıda devrilme.
- Kuralın "ötekilerden biri 0 verdi mi" özelliği büyüklüğe duyarlı. 8 kişilik grupta 7 ötekinden en az birinin 0 vermesi daha olası. Ajanlar "tek bir 0" karşısında 4 kişilik gruptaki gibi davranırsa, büyük gruplar daha sık çöker.
- **İki yön önceden yazılıyor:**
  - (a) ajanlar 4 kişilik gruptaki gibi tepki verir → kural tutar, Mistral'da çöküş artar;
  - (b) ajanlar büyük grupta tek bir 0'a daha hoşgörülü olur ("7 kişiden biri") → kural çöküşü fazla öngörür. Bu durumda "0 tetikleyicisi" büyüklüğe taşınmıyor demektir.
- **İnsan bağlamı (yalnız bağlam, sınanmıyor):** insan deneylerinde grup büyüklüğü, sabit MPCR'de, katkıyı düşürmedi (Isaac, Walker & Williams, 1994; DOI 10.1016/0047-2727(94)90068-X, Crossref'te doğrulandı). İçerik, yazıya geçmeden önce makalenin metninden ayrıca kontrol edilecek.

## 2. Ön bakış (önizleme; resmi tahmin C0'da dondurulur)

- **Yöntem:**
  - dondurulmuş R3 tabloları (`data/expB/frozen_rules_v1.json`, sha256 `62b2bae7…d93d1`);
  - 1. tur katkıları her hücrenin Aşama 1'deki 1. tur kararlarından bağımsız çekilir (büyüklüğün 1. turu değiştirmediği varsayımıyla);
  - 10 tur, kalan tur dilimleri; hücre başına S = 4 000 grup.

  Durum, 8 kişide "7 ötekinin ortalaması" ve "7 ötekinden biri 0 verdi mi"dir. R0, hücrenin izole f'i ile, aynı başlangıçlardan.
- **Kod:** oturumun scratchpad'inde, sabit seed'le. Resmi tahmin C0'da depodaki bir betikle yeniden üretilir ve sha256 ile kilitlenir.

**Minimal kartlar, 4 → 8 kişi:**

| model | kart | kural ortalama (tur 2–10) | kural: 8. turda çöküş payı | 1. turda en az bir 0 | R0 ortalama | R0: 8. turda çöküş payı |
|---|---|---|---|---|---|---|
| Mistral | Boston | 5,68 → 4,08 | 0,51 → 0,76 | 0,10 → 0,19 | 9,31 → 8,82 | 0,10 → 0,19 |
| Mistral | Kopenhag | 7,20 → 6,17 | 0,24 → 0,37 | 0,09 → 0,19 | 3,14 → 3,13 | 1,00 → 1,00 |
| Mistral | Atina | 6,18 → 4,67 | 0,40 → 0,64 | 0,10 → 0,19 | 9,37 → 9,14 | 0,10 → 0,02 |
| Mistral | Riyad | 6,98 → 5,77 | 0,35 → 0,57 | 0,00 → 0,00 | 10,04 → 10,04 | 0,00 → 0,00 |
| GPT | Boston | 7,83 → 7,37 | 0,17 → 0,12 | 0,73 → 0,93 | 9,53 → 9,49 | 0,03 → 0,00 |
| GPT | Kopenhag | 7,57 → 7,32 | 0,15 → 0,10 | 0,71 → 0,92 | 8,34 → 8,44 | 0,05 → 0,00 |
| GPT | Atina | 7,33 → 7,86 | 0,22 → 0,04 | 0,80 → 0,95 | 9,19 → 9,29 | 0,06 → 0,01 |
| GPT | Riyad | 5,95 → 4,76 | 0,41 → 0,52 | 0,92 → 0,99 | 8,02 → 8,15 | 0,13 → 0,04 |

- **Kart ortalamaları:**
  - Mistral, kural: ortalama 6,51 → 5,17; çöküş payı 0,375 → 0,585. R0: çöküş payı 0,30 → 0,30.
  - GPT, kural: ortalama 7,17 → 6,83; çöküş payı 0,24 → 0,20.
- **DeepSeek (minimal):** kuralda çöküş payı 0,88–0,97 → 0,96–1,00, yani taban. Değer kartlarında (Kopenhag, Riyad) ortalama farkı < 0,7 puan. DeepSeek bu deneyde bilgi vermez; önerilen tasarıma alınmadı.
- **Not:** Mistral Riyad minimal'de 1. turda hiç 0 yok, yine de kural çöküş payını 0,35 → 0,57 artırıyor. Ölçek etkisi yalnız 1. turdaki 0'lardan değil, sonraki turlarda herhangi bir ajanın 0'a düşmesinin 8 kişide daha olası olmasından da geliyor.

## 3. Tasarım

### 3.1 Ana deneyle aynı olanlar

- Çerçeve `abstract_v4` (kural metni, karar sorusu, geçmiş gösterimi), cevap biçimi A, koşul N, homojen gruplar, bağış 20, MPCR 0,4, 10 tur [prereg_main §2].
- Modeller, sağlayıcılar ve istek ayarları: Mistral → mistral, GPT → openai; `temperature` ve `reasoning_effort` gönderilmez; `max_tokens` 16 000 [prereg_main §2.2].
- Durma ve sürdürme kuralları (prereg_main §10; F.8 `length` → sürdür; 429 / 5xx → bekle ve sürdür).

### 3.2 Farklar

1. **Grup büyüklüğü 8** (`params.group_size = 8`). İstemde "A group has 8 players: you and 7 others", "… for each of the 8 players" ve 8 oyunculu geçmiş satırı yazar. Bunlar çerçevedeki `{n}` yer tutucularından gelir; metin değişmez.
2. **Kural anlama sorusu** 7 öteki için yeniden yazılır. Çerçeve `abstract_v4_n8` = `abstract_v4` + yalnız q1 değişir:
   - q1: "the other 7 players contribute 4, 12, 16, 0, 8, 20 and 2 points" (kendi katkı 8);
   - anahtar: 20 − 8 + 0,4 × 70 = **40**;
   - q2 aynı (anahtar −6).

   Motor bugünkü çerçeveyle 8 kişide q1'i reddediyor ("3 others, the group has 7"); bu doğru davranış. C0 testi: `abstract_v4_n8`'in karar istemleri 8 kişide `abstract_v4`'ünkilerle bayt bayt aynıdır; fark yalnız q1 satırında.
3. **Kartlar:** 4 minimal kart (`cards/expA_cards_v1.json` ile aynı metinler).
4. **Modeller ve G:** Mistral ve GPT, kart başına 10 grup (model başına 40 grup, 320 ajan). İzole kol yok; R0 için Aşama 1 hücrelerinin izole f'i kullanılır.

## 4. Tahminlerin dondurulması (C0, ücretli çağrıdan önce)

- **Betik** `pgg_analysis_expC.py forecast`:
  - dondurulmuş R3 (sha256 kontrolüyle) ve hücrelerin izole f'i;
  - grup büyüklüğü n için genel durum hesabı: ötekilerin ortalaması n − 1 kişi üzerinden, "ötekilerden biri 0".

  n = 4'te durumların Aşama 1 / Deney B koduyla birebir aynı çıktığı test edilir.
- **Koşulsuz tahmin:** model × kart için n = 4 ve n = 8'de ortalama yörünge, 8. turda çöküş payı ve aradaki fark; kural (R3, kalan tur dilimleri) ve R0. 1. tur, hücrenin Aşama 1'deki 1. tur kararlarından bağımsız çekilir. S = 4 000, seed `stable_seed("pgg-expC-forecast", model, kart, n)`.
- **Çıktı:** `data/expC/forecast_v1.json`. Dosyanın sha256'ı, ilk ücretli çağrıdan önce bu dosyaya ek olarak yazılır ve commit edilir.
- **Koşullu tahmin** (hipotezlerin asıl karşılaştırması): koşudan sonra, her gerçek grubun gözlenen 1. turundan, aynı kural ve aynı seed kuralıyla hesaplanır. Kural ve kod C0'da dondurulur.

## 5. Hipotezler ve karar kuralları

**Ortak tanımlar:**
- m_t, 8 ajanın t. turdaki ortalama katkısıdır.
- Çöküş bölgesi m ≤ 2,5 (prereg_dyn ile aynı).
- Bootstrap gruplar üzerinden yapılır (10 000 tekrar), kart içinde tabakalı; yüzdelik %95 CI.
- Etiketler model başınadır, düzeltme yok (her hipotezde model başına tek test).

**C-H1 (aktarım, birincil)**
- **Ölçü:** model başına, kartlar üzerinden ortalama alınarak (gözlenen − kuralın koşullu tahmini) ortalama katkı, tur 2–10.
- **Etiketler** (Deney B'nin B-H1 kuralı):
  - CI ±2 içinde → "tahmin tuttu"; ±1 içinde → "(sıkı eşdeğerlik)";
  - |tahmin| > 2 ve p < 0,05 → "tahmin sapıyor: gerçek daha düşük / yüksek";
  - diğer → "belirsiz".

**C-H2 (makro aktarım, birincil)**
- **Ölçü:** 8. turda çöküş bölgesindeki grup payı; gözlenen − kuralın koşullu tahmini (grup başına olasılık).
- **Etiketler:**
  - fark ve CI ±0,15 içinde → "yeniden üretiyor";
  - CI tümüyle dışında → "sapıyor (gerçek daha yüksek / düşük)";
  - diğer → "belirsiz".
- R0'ın koşullu tahmini ve gözlenenle farkı da raporlanır (etiketsiz).

**C-H3 (ölçek etkisi, ikincil; iki yön)**
- **Ölçü:** 8. turda çöküş payı, 8 kişilik gruplar (C2) − 4 kişilik gruplar. 4 kişilik gruplar: aynı model, aynı 4 minimal kart; Aşama 1 ve Deney A B kolu, Mistral 72, GPT 112 grup; tarihsel kontrol. Kart içinde tabakalı bootstrap.
- **Karşılaştırma noktaları** (C0'da dondurulur): kuralın koşulsuz tahmini (ön bakışta Mistral +0,21, GPT −0,04) ve R0'ınki (≈ 0).
- **Etiketler:**
  - CI 0'ı dışlıyor, kuralın yönünde ve kuralın tahminini içeriyor → "kuralın öngördüğü ölçek etkisi";
  - CI ±0,10 içinde → "ölçek etkisi yok";
  - CI 0'ı kuralın tersi yönde dışlıyor → "ters yön";
  - diğer → "belirsiz".
- **GPT:** kural etki öngörmüyor. "Ölçek etkisi yok" sonucu kuralla da R0 ile de uyumludur, ayırt edici değildir; böyle raporlanır.
- **Sınırlılık:** kontrol tarihsel; tarih / koşu farkı karışabilir. Deney A'nın B kolu Aşama 1'i 12 hücrenin 11'inde yeniden üretti (prereg_expA F-A.4); tek istisna tam da bu deneyin bir hücresi: Mistral riyadh_minimal (Aşama 1'de 7,69, B kolunda 5,38). C-H3 bu hücre çıkarılarak da raporlanır. Kullanıcı eşzamanlı kontrolü seçerse (§10) C-H3 onunla yapılır, tarihsel kontrol duyarlılık olarak raporlanır.

**Mekanizma (betimsel, etiketsiz):** ajan bir önceki turda ≥ 10 vermiş ve ötekilerin ortalaması ≥ 5 iken iki durum karşılaştırılır: ötekilerden biri 0 verdiyse 0 verme payı, vermediyse 0 verme payı. Değerler 8 kişide ve 4 kişide (Aşama 1, aynı kartlar) raporlanır. Bu, "0 tetikleyicisi büyüklüğe taşınıyor mu" sorusunun doğrudan ölçüsüdür.

## 6. Analiz

- **Betik** `pgg_analysis_expC.py`: `forecast` ve `analyse` alt komutları; eksik koşuda çalışmayı reddeder. Grup dizileri `UnitsT` ile genel n'ye uyarlanır.
- **Sentetik testler:** cevabı bilinen dünyalar.
  - n = 4'te durum hesabı Aşama 1 koduyla aynı.
  - "Tek 0 herkesi düşürür" dünyasında 8 kişide çöküş artar.
  - "Büyük grupta 0'a hoşgörü" dünyasında C-H2 "sapıyor (gerçek daha düşük)" etiketi çıkar.
  - Kural anlama anahtarı 40 / −6.
  - İstem farkı yalnız q1.
- API çağrısı yok; sonuç `results/expC_main_<tarih>_analysis.json`, sha256 bu dosyaya yazılır.

## 7. Aşamalar ve maliyet

| aşama | ne | maliyet |
|---|---|---|
| C0 | çerçeve `abstract_v4_n8`, kart dosyası, config'ler, `forecast` ve dondurma, analiz betiği ve testler, dry-run maliyet hesabı | ücretsiz |
| C1 | duman: model × kart başına 1 grup (Mistral 4, GPT 4 grup); muhakemeler tasarım kusuru için okunur | ~3 USD |
| C2 | ana koşu | §0 madde 5 |

- **Kaba hesap:** model başına yanıt başı ortalama maliyet (Aşama 1, Deney A ve B'den): Mistral ~6,4, GPT ~0,14, DeepSeek ~1,0 USD / 1 000 yanıt. 8 kişilik istem daha uzun olduğu için ×1,15. Grup başına yanıt 88 (8 ajan × 11).
- **Önerilen tasarım:** Mistral 40 grup ≈ 25,8 USD; GPT ≈ 0,6 USD; toplam **≈ 26 USD**.
- **Eşzamanlı 4 kişilik kontrol** (kart başına 10 grup): + ≈ 11,4 USD (Mistral 11,2), toplam **≈ 38 USD**.
- **DeepSeek eklenirse** (bilgi vermez, §2): + ≈ 4 USD.
- **Kesin tavanlar:** C0 dry-run'ından, önceki deneylerdeki kuralla (p95 üst sınır ve beklenen maliyet × 1,1 kapı).
- **Süre:** Mistral 3 520 yanıt; Deney B'deki hıza göre ~10–12 saat (3 paralel).

## 8. Durdurma ve sürdürme

prereg_main §10 ve F.8 aynen uygulanır. İzleyici (`watch_s1b.py` mantığı) şu durumlarda otomatik sürdürür:
- `length` sonrası;
- 429 (300 s bekle, ikinci 429'dan sonra 3 paralel);
- parse hatası (30 s);
- 5xx (600 s).

Başka bir durmada kullanıcıya bildirir.

## 9. Sınırlılıklar

- 8 kişi hâlâ küçük bir sistem. Bu deney kuralın büyüklüğe **taşınmasını** sınar, büyük nüfuslarda ortaya çıkışı değil.
- Ön bakışa göre beklenen etki ılımlı ve yalnız Mistral'da belirgin. 40 grupla C-H2'nin ±0,15 bandı sınanabilir; C-H3'te 0,21'lik bir fark CI genişliğine yakın.
- Ön bakıştaki koşulsuz tahmin, 1. turun büyüklükten etkilenmediğini varsayar. Asıl testler (C-H1, C-H2) gözlenen 1. turdan başladığı için bu varsayıma dayanmaz.
- Tarihsel kontrol (C-H3) tarih ve koşu farkını dışlayamaz.
- Homojen gruplar, tek sağlayıcı, ağ yok; MPCR 0,4 sabit tutulduğu için 8 kişide grubun toplam getirisi (3,2) 4 kişidekinden (1,6) yüksek. Bu, insan deneylerindeki standart "sabit MPCR" karşılaştırmasıdır.

## 10. Kullanıcı kararları

1. **Modeller:** önerilen Mistral + GPT (~26 USD). Alternatif: yalnız GPT (~1 USD; ölçek etkisi beklenmediği için zayıf test) ya da DeepSeek de dahil (+~4 USD; bilgi vermez).
2. **Eşzamanlı 4 kişilik kontrol:** önerilen hayır (tarihsel kontrol, ~26 USD). Evet: ~38 USD; C-H3 daha temiz olur.
3. **G:** kart başına 10 grup (model başına 40). Daha az grup C-H2'nin gücünü düşürür.
4. **Onay:** onaylanırsa C0'a geçilir (ücretsiz). C1 ve C2 için ayrıca "BAŞLA".

## Değişiklik günlüğü

- 2026-10-19: ilk taslak (veriden önce).
