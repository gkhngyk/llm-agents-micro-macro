ONAYLANDI — 2026-10-17 (kullanıcı)

> Bu belge onaylanmadan hiçbir ücretli çağrı yapılmaz. Her aşama (A1 duman testi, A2 ana koşu) kullanıcı o aşama için "BAŞLA" deyince başlar.

# Deney A ön kaydı (prereg_expA): Bedavacının görünürlüğü grup çöküşünü hızlandırıyor mu?

- **Tarih:** 2026-10-17 (ilk taslak). Veriden önce yazıldı.
- **Yazan:** Claude, kullanıcının isteğiyle. Bu bir iç yazılı plandır, kamuya açık bir kayıt değildir.
- **İlişkisi:** ana deneyin (`prereg_main.md`, Aşama 1, `main_s1_20261014`) devamı. Ana deneyin verisi bu deneyin hipotez testine **girmez**; yalnız güç hesabında ve betimsel bir tekrar karşılaştırmasında kullanılır (§7.4).

## 0. Sonuç (önce bu)

1. **Soru:** LLM ajan grupları, ötekilerin katkılarını tek tek gördüklerinde, yalnız ortalamayı gördüklerine göre daha hızlı mı çöküyor?
2. **Neden şimdi:** Ana deneyde gruplar, tek başına (izole) sorulan cevaplardan simüle edilen yörüngeden daha düşük katkı verdi (önceden kayıtlı H4: 36 hücrenin 13'ünde "aşağı", hiçbirinde "yukarı"; F.11). Keşifsel okuma ve sayım (F.12, F.13) bir mekanizma önerdi: izole soru yalnız ötekilerin **ortalamasını** gösteriyordu; grupta ise ajan **tek tek** katkıları görüyor ve bir oyuncu 0 verince işbirliğini bırakıyor. Kendisi önceki turda ≥ 10 vermiş ve ötekilerin ortalaması ≥ 5 olan kararlarda, ötekilerden biri 0 vermişse ajan 0 veriyor: DeepSeek %65, Mistral %61, GPT %15; kimse 0 vermemişse %2 / %3 / %0. Bu bir ilişki; nedensel değil.
3. **Tasarım:** iki kol, tek fark geri bildirimin biçimi. **Bireysel kol (B):** ana deneydeki istem, aynen. **Toplam kol (T):** geçmişte ötekilerin katkıları tek tek değil, yalnız ortalama ve grup toplamı olarak gösterilir. Kartlar: 4 minimal kart. Modeller, sağlayıcılar, ayarlar ana deneyle aynı.
4. **Birincil hipotez (A-H1):** 2–9. tur grup ortalama katkısında T − B farkı (model başına). İki yön de önceden yazıldı.
5. **Mekanizma hipotezi (A-H2):** aynı gerçek durumda (biri 0 vermiş, ötekilerin ortalaması ≥ 5, ajan önceki turda ≥ 10) ajanın 0 verme olasılığı T'de B'den düşük mü?
6. **Maliyet (tahmin):** DeepSeek + GPT, G = 12: ~4,7 USD; Mistral eklenirse (G = 8) ~22,7 USD. Duman testi ayrıca ~0,4 USD (Mistral'la ~2,7 USD). Ayrıntı §9.
7. **Kullanıcı kararları (§11):** Mistral dahil mi, G, paralellik.

## 1. Tasarım

### 1.1 Sabit tutulanlar (ana deneyle aynı)

- Oyun: 4 oyuncu, 10 tur, tur başına 20 puan, MPCR 0,4, koşul N (ceza yok), homojen gruplar [prereg_main §2.4].
- Çerçeve: `abstract_v4` (sistem mesajı "The following describes you:\n{card}"); kural metni, karar sorusu, kural anlama soruları (anahtar 28 / −6) ve cevap biçimi A (`example_object`) aynen [prereg_main §2.1, §2.6, E.4].
- Modeller ve sağlayıcılar: `deepseek/deepseek-v4.1-flash` → DeepInfra fp8; `mistralai/mistral-large-4-0` → Mistral; `openai/gpt-6-luna` → OpenAI. `temperature` ve `reasoning_effort` gönderilmez; `max_tokens` 16 000; `request_deadline_s` 900 [prereg_main §2.2].
- Durma ve sürdürme kuralları: prereg_main §10 ve F.8 (`finish_reason = length` → sürdür), F.9 işletme notu (429 → bekle, sürdür).
- İzole kol **yok** (bu deneyin sorusu grup kolunda).

### 1.2 Kartlar

Yalnız 4 minimal kart (`cards/main_cards_v1.json`, sha256 `bb2be483…f1dc`): `boston_minimal`, `copenhagen_minimal`, `athens_minimal`, `riyadh_minimal`. **Gerekçe:** değer ve olgusal kartların kendi etkileri (ana deney H1, H2) bu deneyin sorusunu karıştırmasın; minimal kartlarda şehir çiftleri arasında fark yoktu (ana deney D_min, üç modelde de en büyük |D| 2,22, hiçbiri "var" değil). Kart burada katman (strata) olarak kullanılır, hipotez değildir.

### 1.3 Manipülasyon: iki çerçeve dosyası

Toplam kol için yeni bir çerçeve dosyası `frames/abstract_v4_agg.json` yazılır. `abstract_v4`'ten **yalnız iki yerde** ayrılır; başka her bayt aynıdır (testle denetlenir, §8).

**(a) Kural metninin son maddesi**

- B (aynen, ana deney): `- After each round you are told every player's contribution and your own earnings.`
- T: `- After each round you are told your own contribution, the average contribution of the other 3 players, and your own earnings.`

**(b) Geçmişteki her turun katkı satırı** (örnek: ajan Oyuncu 2, tur 1'de katkılar 20 / 15 / 10 / 20)

- B (aynen, ana deney):
  ```
  Round 1
    Contributions: Player 1: 20; Player 2 (you): 15; Player 3: 10; Player 4: 20. Group total: 65.
    Your earnings from the project: 26. Your total earnings this round: 31.
  ```
- T:
  ```
  Round 1
    Your contribution: 15. The other 3 players contributed, on average, 16.67 points each. Group total: 65.
    Your earnings from the project: 26. Your total earnings this round: 31.
  ```
- Ortalamanın yazımı: iki ondalık basamak, sondaki sıfırlar atılır (16.67; 10; 13.33; 6.5). Grup toplamı iki kolda da gösterilir; T'de ötekilerin toplamı ortalamadan zaten çıkarılabilir, yani T yalnız **dağılımı** gizler.
- Karar sorusundaki "You are Player k" iki kolda aynen kalır (istemler yalnız (a) ve (b)'de ayrışsın diye).

### 1.4 Hücreler ve grup sayısı

- Hücre = model × kart × kol. Grup sayısı G hücre başına (kullanıcı kararı, §11). Varsayılan öneri: DeepSeek 12, GPT 12, Mistral 8 (dahil edilirse).
- Birim sırası: ana deneydeki gibi `stable_seed` ile karıştırılmış, hücreler arasında dönüşümlü (bir koşu erken dursa da her hücreden veri olur). İki kol aynı koşuda, iç içe koşar.
- Seed namespace: `pgg-expA`. Run adı: `expA_main_<YYYYMMDD>` (duman testi `expA_smoke_<YYYYMMDD>`).

## 2. Ölçüler

- **r2–9 (grup):** 2.–9. turlarda 4 ajanın katkılarının ortalaması. 1. tur dışarıda: o turda geçmiş yoktur, iki kolun istemi aynıdır. 10. tur dışarıda: son tur etkisi (ana deney F.12) manipülasyondan bağımsız bir düşüş ekler.
- **Olay kararı (A-H2 için):** t = 2…9, ajan i; koşul: ajanın t−1'deki katkısı ≥ 10, ötekilerin t−1 ortalaması ≥ 5, ötekilerden en az biri t−1'de 0 verdi. Bu durum her iki kolda da **gerçek katkılardan** hesaplanır (T'de ajan bunu görmez). Sonuç: ajanın t'deki katkısı 0 mı.
- **Kontrol kararı:** aynı koşul, ama ötekilerden hiçbiri 0 vermedi.

## 3. Hipotezler (her yönüyle; birim = grup)

### 3.1 A-H1 — Birincil: görünürlük ve çöküş

- **Ölçü:** ΔA = (1/4) Σ_kart [hücre(T, kart) − hücre(B, kart)], r2–9 üzerinden; model başına.
- **Yönler:**
  - **"Görünürlük çöküşü hızlandırır":** ΔA > 2 ve %95 CI 0'ı dışlıyor (T daha yüksek: ötekileri tek tek görmek işbirliğini düşürüyor).
  - **"Görünürlük işbirliğini destekler":** ΔA < −2 ve CI 0'ı dışlıyor.
  - **"Fark yok":** diğer durumlar; alt not: CI ⊂ [−2, 2] ise "eşdeğerlik sağlandı", değilse "ayırt edilemedi".
- Eşik 2 puan ana deneyle aynıdır [prereg_main §7.2].

### 3.2 A-H2 — Mekanizma: görünen bedavacı

- **Ölçü:** Δp = p_T − p_B; p = olay kararlarında 0 verme oranı. Grup düzeyinde: her grubun olay kararlarındaki oran; olay kararı olmayan grup bu testte yer almaz.
- **Yönler:**
  - **"Mekanizma destekleniyor":** Δp < −0,10 ve CI 0'ı dışlıyor (bedavacı görünmeyince ajan daha az bırakıyor).
  - **"Ters":** Δp > 0,10 ve CI 0'ı dışlıyor.
  - **"Fark yok":** diğer durumlar (eşdeğerlik alt notu: CI ⊂ [−0,10, 0,10]).
- **Kontrol (betimsel):** kontrol kararlarında aynı fark; beklenti ~0. Kontrolde de büyük fark çıkarsa A-H2 "bedavacı" yerine genel bir kol farkına işaret eder; raporda yazılır.
- **Bilinen sınır:** olay kararlarının sıklığı kolun kendi dinamiğine bağlıdır (T'de gruplar daha işbirlikçiyse olay daha az olabilir). Karşılaştırma aynı koşuldaki kararlar arasında yapılır, ama seçilim tamamen giderilemez.

### 3.3 Denge kontrolü (etiket değil)

- 1. tur grup ortalamasında T − B (iki kolda istem aynı): |fark| ≤ 2 beklenir. Daha büyükse raporda işaretlenir (rastlantı ya da tasarım sorunu).

### 3.4 Betimsel

- Kol × tur ortalama katkı eğrileri (1–10); 10. tur ayrıca.
- B kolunun ana deneyin minimal hücreleriyle karşılaştırması (aynı istem; tekrar kontrolü; §7.4).
- Kural anlama oranları; E2a tanıma sayımları (ana deneydeki sözlük ve kurallar).

## 4. İstatistik planı

- Birim grup; hücre farkları için **kart içinde tabakalı bootstrap**: her tekrarda her (kart × kol) hücresinin grupları iadeli yeniden örneklenir; 10 000 tekrar; yüzdelik %95 CI; p = min(1, 2 min(P*(x ≤ 0), P*(x ≥ 0))) [prereg_main §7.1, §7.3].
- Seed: `stable_seed("pgg-expA-analysis", hipotez, model)`.
- **Çoklu karşılaştırma:** A-H1 ve A-H2 model başına birer test; ana deneyle tutarlı olarak model içinde aile başına düzeltme gerekmez (her ailede tek test). Modeller arası düzeltme yapılmaz; üç modelin etiketleri ayrı ayrı verilir ve "en az bir modelde" gibi birleşik bir iddia kurulmaz.
- **Duyarlılık** (karar değiştirmez): (1) yalnız kural anlaması tam gruplar; (2) reasoning_capped satırı ya da `length` olayı olan gruplar hariç; (3) yeniden kullanılan cevabı olan gruplar hariç [prereg_main §7.5, F.8].
- **Analiz kodu:** `pgg_analysis_expA.py`, veri açılmadan yazılır ve sentetik veriyle test edilir; koşu tamamlanmadan çalışmayı reddeder [prereg_main §7.6, F.9].

## 5. Aşamalar

- **A0 (ücretsiz):** `frames/abstract_v4_agg.json` ve motorda iki yeni geçmiş alanı (`own_contribution`, `others_mean`); testler (§8); config'ler (`configs/expA_smoke.json`, `configs/expA_main.json`); dry-run (maliyet, süre); kod kopyası `_kod_<sha>`.
- **A1 duman testi (ücretli, küçük):** hücre başına 1 grup (model başına 8 grup). Okuma: T kolunda geri bildirim doğru anlaşılıyor mu (ortalamayı toplam sanma, eksik bilgi şikâyeti, "biri bedavacılık yapıyor olmalı" çıkarımı); cevap biçimi; kural anlama. Tasarım kusuru çıkarsa tarihli ek ve gerekirse A1 tekrarı. A1 verisi analize girmez.
- **A2 ana koşu (ücretli):** G hücre başına; parçalı koşabilir (ana deneydeki gibi).

## 6. Durma kuralları

- Sert tavan ve model alt tavanları dry-run'a göre konur (kural: sert tavan ≥ toplam p95; alt tavan ≥ model p95; kapı = ortalama × 1,1) [prereg_main §13 Soru 2].
- Geçersiz + parse_fail > %5 → o model durur [prereg_main §10.2].
- `length` → aynı kodla sürdür (F.8); 429 `run_aborted` → bekle ve sürdür.

## 7. Öngörülen sınırlılıklar

1. **Bilgi farkı yalnız dağılımda:** T ortalamayı ve toplamı gösterir; "kim 0 verdi" bilgisini gizler. Ama T'de ajan yine de ortalama düşükse "biri bedavacılık yapıyor" çıkarımını yapabilir; bu A-H2'nin etkisini azaltır.
2. **Kural metni de değişiyor:** (a) maddesi iki kolda farklıdır; etki bilgi biçiminden mi yoksa kuralın yazılışından mı geliyor ayrıştırılamaz (ikisi aynı manipülasyonun parçası).
3. **Ondalıklı ortalama:** T'de ondalıklı sayı görünür (16.67), B'de yalnız tam sayılar. Bu, ana deneydeki 0 / 10 / 20 odak değerleri eğilimini değiştirebilir (betimsel olarak raporlanır).
4. **Taban etkisi:** DeepSeek'in minimal kartlarda r2–9 ortalaması 0,2–1,4 (ana deney). B kolu tabana yakın kalırsa yalnız T > B yönü gözlenebilir.
5. **Talep / test farkındalığı:** ana deneydeki gibi yaygın olabilir (F.13); iki kolda eşit varsayılır, okumada izlenir.
6. **Ana deneyden zaman farkı:** model sürümleri değişmiş olabilir; B kolu ana deneyle betimsel olarak karşılaştırılır (§7.4), sürüm logda kaydedilir.

### 7.4 Ana deneyle tekrar karşılaştırması (betimsel)

B kolunun istemleri ana deneyin minimal hücreleriyle bayt bayt aynıdır. B'nin r2–9 hücre ortalamaları ana deneyin aynı hücreleriyle yan yana verilir; büyük fark (> 2) model sürümü ya da zaman etkisine işaret eder ve raporda tartışılır. Hipotez testi değildir.

## 8. Testler (A0, ücretli koşudan önce)

1. B istemleri (sistem, kullanıcı, cevap talimatı) ana deneyin `abstract_v4` minimal hücre istemleriyle bayt bayt aynı (gerçek bir geçmişle render edilerek).
2. T istemi B'den yalnız §1.3 (a) ve (b)'de ayrışıyor; başka her satır aynı.
3. Ortalama yazımı (16.67 / 10 / 13.33 / 6.5 / 0) ve grup toplamı doğru.
4. Kural anlama istemleri iki kolda aynı.
5. Analiz betiği sentetik veride bilinen etkileri doğru etiketliyor (A-H1 iki yön ve fark yok; A-H2 olay kararlarının seçimi; tabakalı bootstrap; seed).
6. Tam test takımı OK.

## 9. Güç ve bütçe (tahmin; ana deney verisinden)

**Gruptan gruba SD (r2–9, ana deney minimal hücreleri, havuzlanmış):** DeepSeek 2,42; Mistral 3,30; GPT 4,48. T kolunun SD'si bilinmiyor; aynı varsayıldı.

**ΔA'nın %95 CI yarı genişliği** ≈ 1,96 × SD × √(2 / (4G)) (4 kart havuzlanır):

| model | G = 8 | G = 12 | G = 16 |
|---|---:|---:|---:|
| DeepSeek | 1,19 | 0,97 | 0,84 |
| Mistral | 1,62 | 1,32 | 1,14 |
| GPT | 2,20 | 1,79 | 1,55 |

Okuma: G = 12'de DeepSeek ve GPT'de 4 puanlık bir fark rahat "var" olur; 3 puanlık farkta GPT sınırda. Fark yoksa DeepSeek'te eşdeğerlik (CI ⊂ [−2, 2]) G = 12'de beklenebilir.

**Maliyet** (grup başına 44 çağrı: 4 kural anlama + 40 karar; ana deneyin gerçekleşen çağrı başına maliyetleri: DeepSeek 0,00097, Mistral 0,00641, GPT 0,00014 USD):

| seçenek | grup sayısı | çağrı | tahmini maliyet | süre (3 paralel) |
|---|---|---:|---:|---:|
| DeepSeek + GPT, G = 12 | 96 + 96 | 8 448 | ~4,7 USD | ~7 saat |
| + Mistral, G = 8 | + 64 | + 2 816 | + ~18,1 → ~22,7 USD | ~12 saat |
| A1 duman testi (DeepSeek + GPT) | 8 + 8 | 704 | ~0,4 USD | ~1 saat |
| A1 duman testi + Mistral | + 8 | + 352 | + ~2,3 USD | — |

Kesin değerler A0 dry-run'ından gelir; tavanlar onlara göre konur.

## 10. Bu belgede yapılmayanlar

- Kod yazılmadı, API çağrısı yapılmadı.
- Ana deneyin sonuçları ve keşifsel bulguları (F.11–F.13) değiştirilmedi.

## 11. Kullanıcı kararları (onayla birlikte)

1. **Mistral dahil mi?** Mekanizmanın en güçlü görüldüğü iki modelden biri (%61 / %3), ama maliyetin ~%80'i. Öneri: dahil, G = 8 (toplam ~22,7 USD). Bütçe öncelikliyse DeepSeek + GPT (~4,7 USD).
2. **G:** öneri DeepSeek 12, GPT 12, Mistral 8.
3. **Paralellik:** öneri 3 (ana deneyde 6 paralelde DeepSeek sağlayıcısı sık 429 verdi).
4. **Eşikler:** A-H1 için 2 puan (ana deneyle aynı), A-H2 için 10 yüzde puanı. Onay ya da değişiklik.
5. **Onay:** bu taslak, yukarıdaki varsayılanlarla.

## Onay ve kullanıcı kararları (2026-10-17)

- Kullanıcı: "onaylıyorum, mistral dahil, A0'a geç". Belge §11'deki varsayılanlarla onaylandı (ilk satırdaki durum TASLAK → ONAYLANDI olarak değiştirildi; metnin geri kalanı aynen).
  1. **Mistral dahil.**
  2. **G:** DeepSeek 12, GPT 12, Mistral 8 (hücre = model × kart × kol).
  3. **Paralellik:** 3.
  4. **Eşikler:** A-H1 2 puan; A-H2 10 yüzde puanı.
- Bütçe tavanları A0 dry-run'ından sonra §6 kuralıyla konur ve buraya yazılır. A1 ve A2, kullanıcı o aşama için "BAŞLA" deyince başlar.

## Tarihli düzeltmeler

### F-A.1 (2026-10-17, A0 sırasında, veriden önce)

- §8 madde 4 "Kural anlama istemleri iki kolda aynı" yanlıştı: kural anlama istemi kural metnini tekrarlar, bu yüzden iki kol **yalnız §1.3 (a) maddesinde** ayrışır (soru metinleri ve cevap anahtarı aynı). Test buna göre yazıldı (`tests/test_expA_prompts.py`). Tasarım değişmedi.

### F-A.2 (2026-10-17, A0 sırasında, veriden önce) — analiz betiği ve uygulama ayrıntıları

- Betik `pgg_analysis_expA.py`, testleri `tests/test_pgg_analysis_expA.py` (9 test, sentetik veri: iki yön ve fark yok; 1. ve 10. turun A-H1'e girmemesi; denge bayrağı; görünen bedavacı senaryosunda A-H2 "mekanizma destekleniyor"; olay tanımı; olay yoksa "belirlenemedi"; duyarlılık dışlaması; seed). İstem testleri `tests/test_expA_prompts.py` (8 test; B kolu Aşama 1'de gönderilen 60 istemle bayt bayt aynı).
- **Sabitlenen ayrıntılar:**
  1. "CI 0'ı dışlıyor" koşulu, ana deneyle tutarlı olarak bootstrap p < 0,05 ile uygulanır (model ve hipotez başına tek test, düzeltme yok).
  2. **A-H2:** kart başına olay sayısı az olacağı için en az bir olay kararı olan gruplar kol içinde 4 kart üzerinden **havuzlanır**; bootstrap bu grupları kol içinde iadeli yeniden örnekler (kart tabakası yok). Bir kolda olaylı grup yoksa etiket "belirlenemedi".
  3. Denge kontrolü (1. tur T − B) A-H1 ile aynı tabakalı bootstrap'le hesaplanır; |fark| > 2 ise bayrak.
  4. Duyarlılık analizlerinde A-H1 ve A-H2 etiketleri yeniden hesaplanır; değişen etiketler listelenir.
  5. Ana deneyle tekrar karşılaştırması (`--stage1-run`): B kolunun kart başına r2–9 ortalaması ile Aşama 1 minimal hücreleri; |fark| > 2 bayrak.
- Bütçe tavanları (A0 dry-run, §6 kuralı; tahmin pgg_cost mini-pilot kalibrasyonu):
  - **A1 duman** (`configs/expA_smoke.json`, 1 056 çağrı, ortalama 2,79 / p95 5,19 USD): sert tavan 6; alt tavanlar DeepSeek 1 / Mistral 5 / GPT 0,1 (model p95: 0,83 / 4,27 / 0,08); kapı 4.
  - **A2 ana** (`configs/expA_main.json`, 11 264 çağrı, ortalama 23,37 / p95 45,16 USD): sert tavan 46; alt tavanlar DeepSeek 11 / Mistral 35 / GPT 1 (model p95: 10,00 / 34,19 / 0,97); kapı 26.
