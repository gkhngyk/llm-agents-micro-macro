ONAYLANDI — 2026-10-18 (kullanıcı)

> Bu belge onaylanmadan hiçbir ücretli çağrı yapılmaz. Her aşama (B1 duman, B2 ana koşu) kullanıcı o aşama için "BAŞLA" deyince başlar.

# Deney B ön kaydı (prereg_expB): Oyun içinden öğrenilen kural yeni bir oyunu önceden tahmin edebilir mi?

- **Tarih:** 2026-10-18 (ilk taslak). Veriden önce yazıldı.
- **Yazan:** Claude, kullanıcının isteğiyle. Bu bir iç yazılı plandır, kamuya açık bir kayıt değildir.
- **İlişkisi:** ana deney (`prereg_main.md`) ve Deney A (`prereg_expA.md`). Bu deney, keşifsel F.14 bulgusunu **ileriye dönük** olarak sınar.

## 0. Sonuç (önce bu)

1. **Arka plan (keşifsel, F.14):** ajanların tek başına (izole) verdiği cevaplardan simüle edilen gruplar gerçek gruplardan daha iyimserdi (H4). Kuralı **oyunun içinden** öğrenince (R3: kendi önceki katkı, ötekilerin önceki ortalaması, "biri 0 verdi mi", oyunun sonuna kalan tur) boşluk kapandı; Aşama 1'de çapraz doğrulamada ve Deney A'nın bağımsız koşusunda. Ama kural, sonuçlar görüldükten sonra tasarlandı.
2. **Bu deneyin sorusu:** Aşama 1'den öğrenilip **dondurulan** R3 kuralı, ajanların hiç oynamadığı bir oyunu, yani **15 turluk** oyunu, önceden tahmin edebilir mi?
3. **İkinci soru (ufuk):** ajanların oyun sonu davranışı açıklanan oyun uzunluğunu mu izliyor ("sona 2 tur kala" kuralı), yoksa eğitimdeki mutlak tur numaralarına mı bağlı ("9. ve 10. turda bırak")? İki varyant 15 turluk oyunda çok farklı tahminler verir; veri hangisinin doğru olduğunu söyler.
4. **Tasarım:** ana deneyle aynı istem; tek fark tur sayısı (10 → 15). 8 kart (4 minimal + 4 değer), 3 model. Kurallar ve tahminler **koşudan önce** dosyaya yazılıp sha256 ile kilitlenir.
5. **Maliyet (kaba tahmin, kesin değer B0 dry-run'ından):** Mistral dahil ~25–30 USD; Mistral'sız ~5 USD. Süre ~12–13 saat (3 paralel).
6. **Kullanıcı kararları (§11).**

## 1. Tasarım

### 1.1 Ana deneyle aynı olanlar

- Çerçeve `abstract_v4` (sha256 `c00db315…a9f4`), kural metni, karar sorusu, kural anlama soruları (anahtar 28 / −6), cevap biçimi A, koşul N, homojen 4 kişilik gruplar, bağış 20, MPCR 0,4 [prereg_main §2].
- Modeller, sağlayıcılar, istek ayarları (temperature ve reasoning_effort gönderilmez, max_tokens 16 000, deadline 900 s) [prereg_main §2.2].
- Durma ve sürdürme kuralları (prereg_main §10, F.8 `length` → sürdür, 429 → bekle ve sürdür).

### 1.2 Tek fark: tur sayısı 15

- Config'te `params.rounds = 15`. İstemlerde "The same 4 players stay together for all 15 rounds." ve "ROUND k of 15." yazar. Başka bir bayt değişmez (B0 testi: 15 turluk istem, 10 turluk Aşama 1 isteminden yalnız bu sayılarda ve geçmişin uzunluğunda ayrışır).
- Tur sayısı oyunun başında açıklanır (ana deneydeki gibi).

### 1.3 Kartlar ve grup sayısı

- **8 kart:** 4 minimal (`boston_minimal`, `copenhagen_minimal`, `athens_minimal`, `riyadh_minimal`) + 4 değer (`…_value`), `cards/main_cards_v1.json`'dan, metinler aynen.
- **Gerekçe:** DeepSeek minimal kartlarda tabana yakın oynadı (r2–9 ortalaması 0,2–1,4); "0'da kalır" tahmini kolay ve zayıf bir test olurdu. Değer kartları her modelde daha zengin dinamikler üretti (ör. DeepSeek Kopenhag ve Riyad değer hücreleri ~9 ve ~13).
- **G (hücre başına grup, varsayılan öneri):** DeepSeek 8, GPT 8, Mistral 6 → 64 + 64 + 48 = 176 grup.
- Grup arm'ı yalnız; izole kol yok (R0 için Aşama 1'in izole tepkisi kullanılır).

## 2. Dondurulan tahmin modelleri

Bütün kurallar **yalnız Aşama 1 verisinden** öğrenilir (`main_s1_20261014`, bütün geçerli satırlar; hücre = aynı model × aynı kart; geri çekilme için modelin 12 kartı) [F.14]. Öğrenilen sayım tabloları B0'da bir dosyaya yazılır, sha256'sı bu belgeye eklenir ve koşudan sonra değiştirilmez.

- **R3-kalan (birincil):** R3, tur dilimi **oyunun sonuna kalan tura göre**: karar turu t ≤ T − 2 → dilim 0; t = T − 1 → dilim 1; t = T → dilim 2. T = 10'da bu, Aşama 1'deki dilimlerle (2–8, 9, 10) aynıdır.
- **R3-mutlak (rakip):** tur dilimi **mutlak tur numarasına göre**, eğitimdeki gibi: t ≤ 8 → 0; t = 9 → 1; t ≥ 10 → 2. 15 turluk oyunda 9. turdan itibaren oyun sonu davranışı öngörür.
- **R1 (tur bilgisi yok)** ve **R0 (izole tepki, H4 simülasyonu)**: karşılaştırma.
- Simülasyon F.14'teki gibi: olasılıklı, her ajan her turda eğitimde aynı durumdaki gerçek kararlardan birini çeker; grup gözlenen 1. turundan başlar; S = 200.

### 2.1 Koşudan önce yazılan sayısal tahmin

B0'da, yeni gruplar henüz yokken, her model × kart için **koşulsuz** bir tahmin hesaplanır: 1. tur, Aşama 1'de aynı hücredeki grupların gözlenen 1. turlarından örneklenir; tur 1–15 ortalama katkı yörüngesi R3-kalan ve R3-mutlak ile (S = 2000) hesaplanıp tablo olarak bu belgeye **tarihli ek** olarak yazılır. Bu tablo koşudan sonra değiştirilmez.

## 3. Hipotezler (her yönüyle; birim = grup)

**Ölçü:** Δ = (gözlenen − simüle) grup ortalama katkısı; hücre içinde gruplar üzerinden ortalama; model başına 8 kartın ortalaması; **kart içinde tabakalı bootstrap** (gruplar), 10 000 tekrar, yüzdelik %95 CI, p prereg_main §7.3 tanımıyla.

### 3.1 B-H1 — Birincil: R3-kalan yeni oyunu tahmin ediyor mu?

- Pencere: tur 2–15. Model başına.
- **"Tahmin tuttu":** Δ'nın %95 CI'si [−2, 2] içinde (eşdeğerlik; çalışmanın pratik eşiği). Ek not: CI [−1, 1] içindeyse "sıkı eşdeğerlik".
- **"Tahmin sapıyor: gerçek daha düşük":** Δ < −2 ve p < 0,05.
- **"Tahmin sapıyor: gerçek daha yüksek":** Δ > 2 ve p < 0,05.
- **"Belirsiz":** diğer durumlar.
- Hücre (model × kart) düzeyinde aynı etiketler betimsel olarak (model içinde 8 kartlık Holm).

### 3.2 B-H2 — Ufuk: oyun sonu, açıklanan uzunluğu mu izliyor?

- Pencere: **tur 9–13** (R3-kalan burada oyun ortası, R3-mutlak oyun sonu öngörür). Model başına, iki varyant için ayrı Δ.
- **"Açıklanan ufku izliyor":** R3-kalan'ın Δ CI'si [−2, 2] içinde **ve** R3-mutlak'ın Δ'sı > 2 ve p < 0,05 (gerçek gruplar R3-mutlak'ın öngördüğü erken çöküşü yapmıyor).
- **"Mutlak tur numarasına bağlı":** R3-mutlak'ın Δ CI'si [−2, 2] içinde **ve** R3-kalan'ın Δ'sı < −2 ve p < 0,05.
- **"Ayırt edilemedi":** diğer durumlar.

### 3.3 B-H3 — Karşılaştırma (betimsel)

- Model başına yörünge RMSE'si (tur 2–15, hücre ortalama yörüngeleri): R3-kalan, R3-mutlak, R1, R0. Beklenti: R3-kalan en düşük. Farkların bootstrap CI'si verilir; etiket yok.
- Koşulsuz tahmin (§2.1) ile gözlenen yörünge arasındaki RMSE (betimsel).

### 3.4 Duyarlılık

prereg_main §7.5 ve F.8 ile aynı üç dışlama (kural anlaması tam olmayan, reasoning_capped / `length`, yeniden kullanılan cevap); etiket değişimleri raporlanır.

## 4. Analiz kodu

- `pgg_analysis_expB.py`: F.14 kodunun (`pgg_analysis_rules.py`) tur sayısı ve tur dilimi eşlemesiyle genelleştirilmiş hali; dondurulmuş tabloları okur (yeniden öğrenmez). Koşu tamamlanmadan çalışmayı reddeder.
- Testler (sentetik): T = 10'da R3-kalan ile R3-mutlak aynı sonucu verir; ufku izleyen sahte bir dünyada B-H2 "açıklanan ufku izliyor", mutlak tura bağlı bir dünyada "mutlak tur numarasına bağlı" verir; dondurulmuş tablonun sha256'sı değişirse betik durur.

## 5. Aşamalar

- **B0 (ücretsiz):** config (`configs/expB_main.json`, `configs/expB_smoke.json`); istem testi (§1.2); kural tablolarının dondurulması ve sha256; koşulsuz tahmin tablosu (§2.1) bu belgeye tarihli ek; analiz kodu ve testler; dry-run; kod kopyası.
- **B1 duman (ücretli, küçük):** 4 minimal kart × 3 model × 1 grup (12 grup). Amaç: 15 turluk istemde biçim, kural anlama ve muhakeme uzunluğu (uzun geçmişte `reasoning_capped` / `length` artıyor mu). Okuma; veri analize girmez.
- **B2 ana koşu (ücretli):** §1.3'teki G ile.

## 6. Durma kuralları ve bütçe

- Tavanlar B0 dry-run'ına göre prereg_main §13 Soru 2 kuralıyla (sert tavan ≥ toplam p95; alt tavan ≥ model p95; kapı = ortalama × 1,1).
- Geçersiz + parse_fail > %5 → o model durur.

## 7. Öngörülen sınırlılıklar

1. Kural yalnız bir önceki tura bakar; 15 turda daha uzun geçmişin etkisi (ör. birikmiş güven) kuralın dışında kalır. Tahmin tutmazsa bu, açıklamalardan biridir.
2. 11–15. turlarda istemdeki geçmiş, Aşama 1'de hiç görülmemiş uzunluktadır; muhakeme uzunluğu ve maliyet artabilir.
3. Model sürümleri Aşama 1'den bu yana değişmiş olabilir (sürüm logda; Deney A'da aynıydı).
4. "Tahmin tuttu" eşdeğerlik bandı (±2 puan) geniş bir banttır; dar bant (±1) ayrıca raporlanır.
5. Aynı kurallar, aynı modellerin aynı istemiyle öğrenildi; başka modellere ya da başka oyunlara genelleme bu deneyin konusu değildir.

## 8. Güç (kaba)

Deney A B kolunda R3 hücre CI yarı genişliği (12 / 8 / 12 grup): DeepSeek 0,24, Mistral 1,32, GPT 2,03. Model başına 8 kart üzerinden ortalamada (hücre başına 8 / 6 / 8 grup), yarı genişlik kabaca DeepSeek ~0,1, Mistral ~0,5, GPT ~0,9 beklenir. ±2 eşdeğerliği üç modelde de ulaşılabilir; ±1'e GPT'de sınırda.

## 9. Maliyet ve süre (kaba; kesin değer B0'da)

Grup başına 64 çağrı (4 kural anlama + 60 karar). Aşama 1'in çağrı başına maliyetleri, 15 turluk uzun geçmiş için ~%15 artırılarak:

| seçenek | grup | çağrı | maliyet | süre (3 paralel) |
|---|---:|---:|---:|---:|
| DeepSeek 8 + GPT 8 + Mistral 6 (öneri) | 176 | 11 264 | ~27 USD | ~12–13 saat |
| Mistral 4 | 160 | 10 240 | ~20 USD | ~10 saat |
| Mistral'sız | 128 | 8 192 | ~5 USD | ~7 saat |
| B1 duman (12 grup) | 12 | 768 | ~2 USD | ~1 saat |

## 10. Bu belgede yapılmayanlar

Kod yazılmadı, API çağrısı yapılmadı; kurallar henüz dondurulmadı, tahmin tablosu henüz hesaplanmadı (B0'da, koşudan önce).

## 11. Kullanıcı kararları (onayla birlikte)

1. **Kartlar:** 4 minimal + 4 değer (öneri) mi, yalnız 4 minimal mi?
2. **Mistral ve G:** öneri DeepSeek 8, GPT 8, Mistral 6 (~27 USD). Alternatif Mistral 4 (~20 USD) ya da Mistral'sız (~5 USD). Mistral, ufkun en çok önemli olduğu modeldi (F.14'te tur bilgisi olmadan +1,6 sapma).
3. **B1 duman testi** yapılsın mı (öneri: evet, yalnız minimal kartlarla, ~2 USD)?
4. **Eşikler:** B-H1 ve B-H2 için ±2 puan (çalışmanın eşiği) + ±1 ek not.
5. **Onay.**

## Onay ve kullanıcı kararları (2026-10-18)

- Kullanıcı: "onaylıyorum, önerilerinle devam et, B0'a geç". İlk satırdaki durum TASLAK → ONAYLANDI olarak değiştirildi; metnin geri kalanı aynen.
  1. **Kartlar:** 4 minimal + 4 değer.
  2. **G:** DeepSeek 8, GPT 8, Mistral 6 (Mistral dahil).
  3. **B1 duman testi:** evet; 4 minimal kart × 3 model × 1 grup.
  4. **Eşikler:** ±2 puan (birincil), ±1 ek not.
- Bütçe tavanları, dondurulan kural tablosunun sha256'sı ve koşulsuz tahmin tablosu B0'da, ücretli çağrıdan önce buraya yazılır.

### F-B.1 Dondurulan kurallar ve koşudan önce yazılan tahmin (2026-10-18, ücretli çağrıdan önce)

- **Dondurulan kural tablosu:** `data/expB/frozen_rules_v1.json`, sha256 `62b2bae7bcf6560f022181ff5b0813fec4747f2b8e3e13e5dd1301931fbd93d1`. Kaynak: `main_s1_20261014` sonuç dosyası (sha256 `3a8d22e9…f930`, F.10 ile aynı); karar sayıları DeepSeek 6 912, Mistral 4 320, GPT 6 912 (grup × 36); izole tepkiler (R0) ve Aşama 1'in 1. tur vektörleri dosyada.
- **Koşulsuz tahmin:** `data/expB/forecast_v1.json`, sha256 `ef76791f0c6e6051fa0a02807c8df0367957d5e2f700f027f9130afc884904de` (S = 2 000; 1. tur Aşama 1'in aynı hücresinden örneklendi). Hücre başına yörüngeler dosyada; aşağıda 8 kartın ortalaması (tur 1–15):

| model | varyant | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepseek | R3-kalan | 6,4 | 4,1 | 3,8 | 3,6 | 3,5 | 3,5 | 3,4 | 3,4 | 3,4 | 3,3 | 3,3 | 3,3 | 3,3 | 3,1 | 2,1 |
| deepseek | R3-mutlak | 6,4 | 4,1 | 3,8 | 3,6 | 3,5 | 3,4 | 3,4 | 3,4 | 3,1 | 2,1 | 1,2 | 0,8 | 0,5 | 0,4 | 0,3 |
| mistral | R3-kalan | 9,6 | 9,0 | 8,7 | 8,4 | 8,1 | 7,9 | 7,7 | 7,5 | 7,3 | 7,1 | 7,0 | 6,8 | 6,7 | 5,9 | 4,0 |
| mistral | R3-mutlak | 9,6 | 9,0 | 8,7 | 8,4 | 8,1 | 7,9 | 7,7 | 7,5 | 6,4 | 4,1 | 2,8 | 2,3 | 2,1 | 2,0 | 1,9 |
| gpt | R3-kalan | 9,8 | 9,1 | 9,1 | 9,0 | 9,0 | 9,0 | 9,0 | 9,0 | 8,9 | 8,9 | 8,9 | 8,9 | 8,9 | 8,8 | 3,8 |
| gpt | R3-mutlak | 9,8 | 9,1 | 9,1 | 9,0 | 9,0 | 9,0 | 9,0 | 9,0 | 8,9 | 3,8 | 2,0 | 1,2 | 0,9 | 0,6 | 0,5 |

- Okuma: R3-kalan oyun ortasını 13. tura kadar sürdürür, düşüşü 14–15. turlara koyar; R3-mutlak düşüşü 9–10. turlara koyar. B-H2 (tur 9–13) bu iki öngörüyü ayırır.
- **Bütçe tavanları** (B0 dry-run, §6 kuralı): **B1 duman** (`configs/expB_smoke.json`, 768 çağrı, ortalama 2,08 / p95 3,87 USD): sert 4; alt tavanlar DeepSeek 1 / Mistral 4 / GPT 0,1; kapı 3. **B2 ana** (`configs/expB_main.json`, 11 264 çağrı, ortalama 25,74 / p95 49,24 USD): sert 50; alt tavanlar DeepSeek 11 / Mistral 39 / GPT 2 (model p95: 10,02 / 38,20 / 1,02); kapı 29.
- **Kartlar:** B2 `cards/expB_cards_v1.json` (main_cards_v1'in 4 minimal + 4 değer kartı, aynı metinler); B1 `cards/expA_cards_v1.json` (4 minimal).

### F-B.2 B1 duman testi sonucu (2026-10-18) — değişiklik yok

- **Koşu:** `expB_smoke_20261018`, kod `dc70579` (temiz), 14:05–~15:05; 12/12 grup, 768 satır (sha256 `f5f2b76874fa1dd9c9be1811abb88fa0d81d2e91a9f5fb63bbf69a48e375f21b`), tek segment, `stop_reason` yok. Maliyet 1,9965 USD (DeepSeek 0,26 / Mistral 1,69 / GPT 0,04; tahmin 2,08). Superseded / truncated / discarded 0. Model sürümleri Aşama 1 ile aynı.
- **Tesisat:** geçersiz + parse_fail 0 (üç model), `length` 0; kural anlama 16/16 (üç model). DeepSeek `reasoning_capped` tur 1–10'da 16/160, tur 11–15'te 0/80: uzun geçmiş muhakemenin sınıra çarpmasını artırmıyor.
- **Okuma (yalnız istemin doğru okunması):** oyunu 10 turluk sanan kayıt yok. Sıkı bir kalıpla çıkan adaylar (DeepSeek 8, Mistral 18, GPT 9 / 240) okununca doğru ifadeler: 5. turda "10 tur kaldı" (15 turda doğru), literatürdeki "10 turluk oyun", GPT özetlerinde "10'luk geçmiş". Turlara göre katkı değerleri bu okumada **incelenmedi** (B-H2'nin sonucuna bakmamak için).
- **Karar:** tasarım kusuru yok; B2 aynı kod (`_kod_dc70579…`) ve `configs/expB_main.json` ile, kullanıcı "BAŞLA B2" deyince. B1 verisi analize girmez.

### F-B.3 B2 tamamlandı ve analiz çalıştırıldı (2026-10-19)

- **Koşu:** `expB_main_20261018`, kod `dc70579` (4 segment, `code_lock` "same"), 2026-10-18 15:30 → 2026-10-19 ~01:50; 176/176 grup, 11 264 satır (sha256 `2be90a5b2dae25eaff3d33248722810edd6f0bd924e8182350317b00a4c90a44`). Segment sonları: Mistral sağlayıcı kesintisi (HTTP 503 "unreachable_backend", 19:41; 10 dk beklenip sürdürüldü, §10.2 madde 8), bir 429, bir `length` (F.8). Superseded / truncated / discarded 0. Bütün karar satırları beklenen sağlayıcı ve model sürümünden (deepseek-v4.1-flash-20260910, mistral-large-4-0-20261006, gpt-6-luna-20260922); sürümü boş iki yanıt sağlayıcı adı dönmeyen ve reddedilip yeniden istenen yanıtlardır.
- **Maliyet:** özet 23,1165 USD; ham logdaki faturalanan `usage.cost` toplamı 23,0751 USD. Fark (≈0,04 USD), kesinti sırasındaki 9 sağlayıcı hata yanıtının (faturalanmayan, `upstream_inference_cost` 0,0204) ve sağlayıcı adı dönmeyen 2 yanıtın özette ihtiyatlı sayılmasından.
- **Tesisat:** geçersiz + parse_fail DeepSeek 4 + 0, Mistral 0, GPT 0 + 1; `length` GPT 1; kural anlama DeepSeek 256/256, Mistral 192/192, GPT 255/256.
- **Analiz:** `pgg_analysis_expB.py analyse` (kod `dc70579`, değiştirilmeden), dondurulmuş kural dosyası sha256 `62b2bae7…93d1` doğrulandı; `results/expB_main_20261018_analysis.json`, sha256 `08b58e0e57fa0f75ebb435fc73a1cd2206f7f2103df89e83a59310a4ff549095`. Gözlenen yörüngeler bağımsız kodla yeniden hesaplandı ve tuttu.
- **B-H1 (R3-kalan, tur 2–15):** DeepSeek Δ −0,06 [−0,60, +0,48] **"tahmin tuttu (sıkı eşdeğerlik)"**; Mistral +0,82 [+0,17, +1,52] **"tahmin tuttu"**; GPT +0,67 [−0,17, +1,46] **"tahmin tuttu"**. Hücre etiketleri: 24 hücrenin 23'ü "uyumlu", 1'i "yukarı" (GPT).
- **B-H2 (tur 9–13):** Mistral (R3-kalan +1,11 [+0,22, +1,98]; R3-mutlak +4,38 [+3,43, +5,34]) ve GPT (+0,73 [−0,25, +1,64]; +6,87 [+5,87, +7,87]) **"açıklanan ufku izliyor"**. DeepSeek **"ayırt edilemedi"**: R3-kalan uyuyor (−0,28 [−0,99, +0,41]), R3-mutlak'ın hatası aynı yönde ama eşiğin altında (+1,49 [+0,82, +2,18], p < 0,001), çünkü DeepSeek'in katkı düzeyi düşük.
- **B-H3 (RMSE, tur 2–15):** R3-kalan her modelde en düşük: DeepSeek 0,37 (R3-mutlak 1,35, R1 0,81, R0 1,83); Mistral 0,89 (3,13 / 2,82 / 2,29); GPT 0,77 (5,29 / 2,92 / 2,36). R3-kalan ile farkların CI'si, DeepSeek'te R1 dışında ([−0,39, +0,93]), 0'ı dışlıyor.
- **Koşudan önce yazılan koşulsuz tahmin (F-B.1) RMSE:** R3-kalan DeepSeek 0,53, Mistral 0,45, GPT 2,19; R3-mutlak 1,45 / 2,87 / 5,99. GPT'de koşulsuz tahminin hatası, 15 turluk oyunda 1. turun Aşama 1'den yüksek olmasından (gözlenen 12,1, tahmin 9,8); 1. turdan başlatılan koşullu tahmin uyuyor (0,77). Betimsel not (hipotez değil): ufuk uzayınca açılış katkısı GPT'de ve DeepSeek'te daha yüksek (7,4 / 6,4).
- **Duyarlılık:** üç dışlama (1, 40, 3 grup) hiçbir B-H1 / B-H2 etiketini değiştirmedi.
