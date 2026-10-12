# ONAYLANDI — 2026-10-04 (kullanıcı)

# Pilot ön kaydı (prereg_pilot): kamu malı oyunu, kimlik tanımı × izole/grup

Tarih: 2026-10-04 (taslak #30); kesinleştirme: 2026-10-05 (#31). Durum: **onaylandı; kararlar §12'de**. Bu belge iç yazılı plandır, kamusal kayıt değildir [CL "Write the plan before the data"]. Bu görevde kod çalıştırılmadı, API çağrısı yapılmadı, depoya yazılmadı.

Kaynak kısaltmaları: **CL** = depo `CLAUDE.md`; **BG** = depo `notes/BACKGROUND.md`; **K** = `kararlar.md`; **M** = `maliyet_analizi.md`; **S** = `gorev_soguk_test_sonuclari.md`; **R** = `rapor_acik_isler.md`; **G7b** = `gorev7b_herrmann2008_data_filtresi.md`; **#29** = developer görevinin sonucu (pgg_game.py, pgg_cost.py). "(tahmin)" = kaynağı olmayan çıkarım veya öneri.

> **Kaynak notu:** #29'u `git show orc/PublicGoods` ile okuyamadım (bu görevde kabuk aracı yok). Motor davranışı görev sonuç metninden alındı; dal içeriğiyle birebir doğrulanmadı. Koşudan önce developer görevi `pgg_game.py --dry-run` çıktısını bu belgedeki sayılarla (1 620 çağrı, §6) karşılaştıracak.

---

## 1. Sonuç (önce bu)

- **Kapsam:** 3 model × 2 kimlik (Boston, Riyadh) × 3 stil = 6 hücre/model, yalnızca N (cezasız), yalnızca homojen grup. Hücre başına 2 grup + izole çizelge (5 değer × 2 tekrar).
- **Hacim:** model başına 540, toplam **1 620 çağrı**.
- **Maliyet (tahmin):** beklenen **~0,41 USD** (geçersiz yanıt yeniden denemeleriyle ~0,43); makul en kötü durum ~0,86 USD. **Sert tavan 1,00 USD** (birikmiş `usage.cost`; aşılırsa koşu durur). Her çağrı `max_tokens` = 4000'e kadar çıksaydı teorik üst sınır ~3,05 USD olurdu; tavan bu durumda devreye girer (§6.4).
- **Kartlar:** 12 İngilizce kart yazıldı (4 şehir × 3 stil), pilota yalnızca Boston ve Riyadh kartları girer. Üç stil 24–25 kelime; kelime farkı ≤ %4. Kart metinleri §4 tablosunda ve `pilot_cards.json` içinde birebir aynıdır.
- **Amaç:** bilimsel sonuç değil, tasarım ve istem hatalarını bulmak. Hücre başına 2 grup istatistiksel test için çok az; pilot **betimsel** okunur (tahmin).
- **Pilot verisi ana analizden HARİÇ** tutulur [CL].

---

## 2. Sabit çerçeve

Tekrarlı kamu malı oyunu: 4 kişilik grup, 10 tur, 20 puan, MPCR 0.4; ceza oranı 1:3 çerçevede var ama **pilotta kullanılmaz** [BG §4; K "Sabit çerçeve"]. Çapa: Herrmann–Thöni–Gächter (2008) [BG §4]. Motor: `pgg_game.py` (ceza koşulu kodda mevcut, pilotta kapalı) [#29].

Pilotta olanlar: koşul **N**; grup türü **homojen** (4 ajanın hepsi aynı kart). Pilotta olmayanlar: P (ceza), karma tanımlı grup, insan verisiyle karşılaştırma.

**Dil:** kartlar dahil tüm istem İngilizce; şehir adları İngilizce (§12 karar 2).

---

## 3. Kimlikler (Karar 1 B)

**Kararlaştırılan şehir listesi:** Boston, Copenhagen, Athens, Riyadh (4 şehir; K Karar 1 B). **12 kart yazılır; pilota yalnızca Boston + Riyadh girer** (2 kimlik × 3 stil = 6 hücre). Copenhagen ve Athens kartları pilot sonrası için hazır tutulur, pilotta çağrı yapılmaz.

| Şehir | Hesaplanan P ortalaması (geçici) | Not | Pilotta |
|---|---|---|---|
| Boston | 17.98 | yüksek uç [R §1.1] | evet |
| Copenhagen | 17.75 | yüksek uç [R §1.1] | hayır |
| Athens | 5.70 | düşük uç; `data` belirsizliğinden etkilenen şehir [R §1.3] | hayır |
| Riyadh | 6.91 | düşük uç [R §1.1] | evet |

- Değerler **yayımlanmış değer değil, hesaptır**; `data` filtresi bilinmediği için geçicidir [R §0 madde 1, 3].
- Seçim ölçütü P koşulundaki hesaplanan ortalamadır; pilot N koşuludur. Yani şehirler pilot koşulu için değil, tam deneyin insan çapası için seçilmiştir (tahmin).
- **Athens için `data` filtresi belirsizliği (not kalır):** `data` değişkeni ne CSV'de ne `.dta`'da var, do dosyalarında tanımı yok; ne dışladığı belirlenemedi [G7b Özet; R §1.3]. Athens'te veri 72 denek, ikincil kaynaktaki 2010 Tablo 1'de 44 (fark 28, bölünmüş oturum); kimlikler birleştirilince sayı tutuyor [R §1.2; G7b §2]. Dışlama varyantlarında Athens P ortalaması −0.61 oynuyor (E_H5drop, E_H7) [R §1.3]. Boston, Copenhagen ve Riyadh bu belirsizlikten etkilenmiyor sayılır [R §4 Karar 4]. Athens sonuçları insan çapasına göre yorumlanırken ihtiyatla okunur; pilot insan verisiyle karşılaştırmaz.
- Pilota Riyadh'ın girmesinin gerekçesi: düşük uç ve `data` belirsizliğinden etkilenmeyen şehir (tahmin).
- Açık tasarım sorusu: kimlik "o şehrin öğrencisi" mi, "kültür" mü? Kaynakta cevap yok; kartlarda "öğrenci" sabit tutuldu (Herrmann örneklemi öğrenci havuzu) [K Karar 2; R §4 Karar 1 "Dikkat"].

---

## 4. Kartlar (Karar 2 B)

**4 şehir × 3 stil = 12 kart** [K Karar 2 B]. Stiller: minimal (yaş + meslek/öğrenci), değer yüklü, olgusal [CL "Vary the description"; BG §1]. **Sayısal eğilim puanı yoktur** [CL]. Değer yüklü ve olgusal kartlar K Karar 2 B şablonlarının İngilizce çevirisidir; çeviri benim, ilk çalışmanın kart metni değil [K Karar 2 Not]. Tüm kartlar ikinci tekil kişidedir ("You are ...").

### 4.1 Kuruluş

- **Eşit uzunluk:** her şehrin üç kartı ve stiller arası kartlar aynı kalıpla kurulur: "You are a [21-year-old] university student living in {City}." + ikinci cümle. Hedef: kelime sayısı farkı ±%10 içinde. Sonuç: tüm kartlar 24–25 kelime (§4.3).
- **Minimal kart** yalnızca yaş + meslek (öğrenci) içerir. Uzunluk farkı, ikinci bir cümleyle kapatılır: "Please read the rules carefully and take the time you need before you make a decision." Gerekçe: cümle kimlik, değer veya olgu içermez ve işbirliği/katkı hakkında bir şey söylemez. **Sınırlılık:** cümle yine de genel bir davranış talimatı gibi okunabilir (dikkatli okuma ve yavaş karar verme). Bu yüzden §9 kontrol listesine eklendi (madde 8); minimal hücrede farkın bu cümleden gelip gelmediği muhakeme metinlerinden bakılır. Bu bir tasarım seçimidir, doğrulanmış tarafsızlık iddiası değildir.
- **Olgusal kart** ("The city is a large urban area, and its economy is closely tied to market relations."): kaynağı olmayan genel bir iddiadır. Dört şehir için de **(tahmin)**: "büyük kent" ve "piyasa ilişkilerine yoğun bağlı ekonomi" tanımları bu çalışmanın hiçbir kaynağında doğrulanmadı; K Karar 2 de bunun yer tutucu olduğunu söylüyor. İfadede sayı ve şehre özgü olgu bilerek yok. Bu bir "(tahmin)" olarak kalır; kullanıcı onayı bu metni kapsıyor, ama olgusal doğruluk kanıtlanmış değildir. JSON metninde bu işaret yoktur.
- Aynı şablon dört şehirde kullanıldığı için şehirler arası fark yalnızca şehir adından gelir; şehre özgü içerik yok (sınırlılık).

### 4.2 Biçim: `--cards` girdisi

Kart dosyası `pilot_cards.json`: JSON listesi, her öğe `{"card_id", "city", "style", "text"}`. `card_id` biçimi `<şehir_küçük_harf>_<stil>`, stil değerleri `minimal`, `value`, `factual`. Sistem mesajı = kart metni [#29].

- #29'un `--cards` tanımı `{card_id, style, text}` listesidir. Dosyadaki ek `city` alanının motoru bozmaması **beklenir ama doğrulanmadı**; developer görevi kontrol edecek, uyuşmazlık çıkarsa biçimi o düzeltir (metinleri yalnızca bu belge belirler).
- `style` değerlerinin (`value`, `factual`, `minimal`) motorun beklediği etiketlerle aynı olup olmadığı doğrulanmadı (aynı kontrol).
- Dosya 12 kart içerir; pilot yalnızca `boston_*` ve `riyadh_*` kartlarını koşar. Motorun kart/şehir filtresi olup olmadığı bilinmiyor; yoksa developer görevi 6 kartlık bir alt liste ya da filtre kullanır, 12 kartın tamamı çalıştırılmaz.

### 4.3 Kart tablosu

Kelime sayısı: boşlukla ayrılmış simgeler (tireli "21-year-old" tek kelime). Karakter sayısı: boşluklar ve noktalama dahil. Sayımlar elle ve iki kez yapıldı (kod çalıştırılmadı).

| card_id | city | style | kelime | karakter | metin |
|---|---|---|---|---|---|
| boston_minimal | Boston | minimal | 25 | 145 | You are a 21-year-old university student living in Boston. Please read the rules carefully and take the time you need before you make a decision. |
| boston_value | Boston | value | 25 | 155 | You are a university student living in Boston. The environment you grew up in values contributing to the common good, reciprocity, and sharing with others. |
| boston_factual | Boston | factual | 24 | 131 | You are a university student living in Boston. The city is a large urban area, and its economy is closely tied to market relations. |
| copenhagen_minimal | Copenhagen | minimal | 25 | 149 | You are a 21-year-old university student living in Copenhagen. Please read the rules carefully and take the time you need before you make a decision. |
| copenhagen_value | Copenhagen | value | 25 | 159 | You are a university student living in Copenhagen. The environment you grew up in values contributing to the common good, reciprocity, and sharing with others. |
| copenhagen_factual | Copenhagen | factual | 24 | 135 | You are a university student living in Copenhagen. The city is a large urban area, and its economy is closely tied to market relations. |
| athens_minimal | Athens | minimal | 25 | 145 | You are a 21-year-old university student living in Athens. Please read the rules carefully and take the time you need before you make a decision. |
| athens_value | Athens | value | 25 | 155 | You are a university student living in Athens. The environment you grew up in values contributing to the common good, reciprocity, and sharing with others. |
| athens_factual | Athens | factual | 24 | 131 | You are a university student living in Athens. The city is a large urban area, and its economy is closely tied to market relations. |
| riyadh_minimal | Riyadh | minimal | 25 | 145 | You are a 21-year-old university student living in Riyadh. Please read the rules carefully and take the time you need before you make a decision. |
| riyadh_value | Riyadh | value | 25 | 155 | You are a university student living in Riyadh. The environment you grew up in values contributing to the common good, reciprocity, and sharing with others. |
| riyadh_factual | Riyadh | factual | 24 | 131 | You are a university student living in Riyadh. The city is a large urban area, and its economy is closely tied to market relations. |

### 4.4 Uzunluk denetimi

- **Kelime:** minimal 25, değer yüklü 25, olgusal 24 → en büyük fark 1 kelime (%4), her şehirde ve şehirler arasında aynı (şehir adları tek kelime). Hedef ±%10 sağlandı.
- **Karakter (bilgi amaçlı, hedef değil):** Boston/Athens/Riyadh'ta 145 / 155 / 131, Copenhagen'da 149 / 159 / 135. En kısa (olgusal) en uzundan (değer yüklü) 24 karakter (~%15) kısa. Karakter farkı kelime sayısıyla eşit düzeyde kontrol edilmedi; olgusal kartın daha kısa sözcükler kullandığı anlamına gelir. Biçim/uzunluk etkisi şüphesi §9'da okunur.
- Copenhagen kartları şehir adı yüzünden Boston/Athens/Riyadh kartlarından 4 karakter uzundur; pilotta Copenhagen yok.
- Kartlarda sayısal eğilim puanı yoktur.

---

## 5. İzole kol (Karar 3 C)

Karar 3 C: kısa çizelgeyle pilot, eğri doğrusal değilse tam yönteme geç [K Karar 3].

- **Çizelge:** "diğer üç oyuncunun ortalama katkısı" = **0, 5, 10, 15, 20**; her biri için modelin kendi katkısı (0–20 tam sayı) istenir [BG §4 kol (i); K Karar 3; #29].
- **Her değer ayrı çağrı** (5 çağrı); geçersiz değer tek başına yeniden istenir ve kendi satırında sayılır [#29]. Bedeli: kurallar 5 kez gönderilir, pilot maliyetinin ~%7–9'u (#29, tahmin).
- Hücre başına **2 tekrar** → 10 çağrı/hücre; 6 hücre → 60 çağrı/model [M §3; #29].
- Başkalarının ortalaması yalnızca "bu değer" olarak verilir, geçmiş yoktur (M'de izole girdisinde geçmiş = 0 token) [M §2].
- Çizelgenin tam strateji yöntemine (21 nokta) göre kaçırabileceği: doğrusal olmayan kıvrımlar (tahmin) [K Karar 3].
- Açık ek karar (pilot dışı): izole ajanın ceza tepkisi pilotta ölçülmez (P yok); tam deneyde ölçülüp ölçülmeyeceği ayrı karardır [K Karar 3 "Ek kararlar"].

---

## 6. Oyun, modeller, hacim ve maliyet

### 6.1 Oyun akışı (pilot)
- Grup: 4 ajan, hepsi aynı kartta (homojen), 10 tur, 20 puan/tur, MPCR 0.4, N koşulu [BG §4; #29].
- Çağrılar durumsuz; geçmiş her çağrıda istemde. Tur içi çağrılar yalnızca önceki turları görür (aynı turdaki diğer kararları görmez) [#29].
- Tüm çağrılar `llm_client.call_llm_valid` üzerinden; geçersiz yanıt yeniden istenir ve sayılır, asla kodlanmaz; seed `llm_client.stable_seed` (hash() yok), satıra yazılır; sıcaklık gönderilmez, log `"default"` [CL; #29; S §4].
- **`reasoning_effort` pilotta gönderilmez** (model varsayılanı). Log'da gönderilmediği açıkça yazılır; **reasoning token'ları ölçülür ve raporlanır** (`usage` içindeki reasoning alanı).
- **`max_tokens` = 4000** (oyun çağrıları). Reasoning token'ları bu sınırdan yer.
- Çıktı: `results/<run>.jsonl`, satır başına karar; alanlar: `n_invalid`, `n_parse_fail`, `model`, `session_id`, `reasoning_effort` (gönderilmedi), `finish_reason`, `usage`, varsa reasoning metni [#29].
- JSON'da karardan sonra kısa **`rationale`** alanı kalır (Gemini yerel reasoning metni vermediği için, pilot sonrası okuma amacıyla); yalnızca karar alanı doğrulanır [#29].
- **Eşzamanlı çağrı; batch yok** (§6.5).

### 6.2 Modeller
| Kısa ad | Model | Not |
|---|---|---|
| deepseek | `deepseek/deepseek-v4.1-flash` | sağlayıcı sabit değil; completion fiyatı ~13 kat değişebilir [S §3; M §6] |
| gpt | `openai/gpt-6-luna` | |
| gemini | `google/gemini-2.5-flash-lite` | soğuk testte reasoning 0 (tek ölçüm) [S §6] |

### 6.3 Tekrar sayısı ve çağrı sayısı
- Tekrar: **hücre başına 2 homojen grup** (N), izole çizelge **2 tekrar × 5 değer** [M §3; #29].
- Hücre = kart (kimlik × stil) = 6 (Boston ve Riyadh × 3 stil).

| Bileşen | Hesap | Çağrı/model |
|---|---|---|
| Grup (N) | 6 hücre × 2 grup × 4 ajan × 10 tur | 480 |
| İzole | 6 hücre × 2 tekrar × 5 değer | 60 |
| **Toplam / model** | | **540** |
| **Üç model** | 3 × 540 | **1 620** |

12 grup/model (6 × 2). Yeniden istenen çağrılar bu sayıya **ek** olarak gelir (§6.5 ve §8.1).

### 6.4 Maliyet (normal fiyat, USD, tahmin)

Fiyatlar M §1 tablosundan (USD / 1M token; girdi / çıktı): deepseek 0,14 / 0,42; gpt-6-luna 0,10 / 0,50; gemini-2.5-flash-lite 0,10 / 0,40. Reasoning completion fiyatından ücretlenir [M §1].

**(a) Temel tahmin (tahmin).** M'nin istem ve çıktı varsayımlarıyla (girdi 1 120 token/katkı çağrısı, 630 token/izole çağrısı; reasoning deepseek 400, gpt 200, gemini 0 token) [M §2]. `reasoning_effort` gönderilmemesi M'nin varsayımını değiştirmez; M zaten sabit düzey varsaymamıştı [M §2]. Çağrı birim maliyetleri M §4'ten (deepseek 0,00035 / 0,00027; gpt 0,00024 / 0,00018; gemini 0,000136 / 0,000079; katkı / izole):

| Model | Hesap | Maliyet | Çağrı |
|---|---|---|---|
| deepseek | 480 × 0,00035 + 60 × 0,00027 | 0,184 | 540 |
| gpt-6-luna | 480 × 0,00024 + 60 × 0,00018 | 0,126 | 540 |
| gemini-2.5-flash-lite | 480 × 0,000136 + 60 × 0,000079 | 0,070 | 540 |
| **Toplam** | | **0,380 (~0,38)** | **1 620** |

Bağımsız kontrol (girdi/çıktı fiyatlarından yeniden): her modelde girdi 480 × 1 120 + 60 × 630 = 575 400 token; girdi maliyeti deepseek 0,081, gpt 0,058, gemini 0,058 (toplam 0,196). Bu, M'nin birim maliyetleriyle tutarlıdır.

**(b) `rationale` ekleme (tahmin).** Karardan sonraki kısa gerekçe için çağrı başına +40 çıktı token varsayımı (kaynaksız; M'nin 60 token varsayımına dahil olup olmadığı belli değil). Ek: deepseek 540 × 40 × 0,42e-6 = 0,009; gpt 540 × 40 × 0,50e-6 = 0,011; gemini 540 × 40 × 0,40e-6 = 0,009; toplam **~+0,03**.
**(c) Geçersiz yanıt yeniden denemesi:** %5 → ~+0,02.

**Beklenen toplam: 0,38 + 0,03 = ~0,41 USD; yeniden denemelerle ~0,43 USD (tahmin).**

**(d) Duyarlılık (tahmin):**

| Senaryo | Ek | Toplam |
|---|---|---|
| DeepSeek+GPT reasoning ×0,5 (M pilot reasoning payı 0,14) | −0,07 | ~0,34 (rationale ve yeniden denemesiz) |
| DeepSeek+GPT reasoning ×3 | +0,28 | ~0,66 (aynı kapsam) |
| Gemini varsayılanında 200 reasoning token/çağrı | +0,043 (540 × 200 × 4e-7) | |
| Gemini varsayılanında 600 reasoning token/çağrı | +0,130 (540 × 600 × 4e-7) | |
| **Makul en kötü:** reasoning ×3 + Gemini 600 + rationale + %5 yeniden deneme | 0,66 + 0,13 + 0,03 + ~0,04 | **~0,86** |

**(e) `max_tokens` = 4000 ile teorik üst sınır (tahmin).** Her çağrının 4000 completion token'a kadar gitmesi mümkündür. Bu durumda tek çağrı maliyeti deepseek ~0,0018, gpt ~0,0021, gemini ~0,0017 USD olur. Hepsi 4000 token olursa model başına: deepseek 480 × 0,001837 + 60 × 0,001768 = 0,988; gpt 480 × 0,002112 + 60 × 0,002063 = 1,138; gemini 480 × 0,001712 + 60 × 0,001663 = 0,922; **toplam ~3,05 USD**. Bu gerçekçi bir tahmin değil, tavandır. **1,00 USD tavanı, tüm modellerde ortalama completion (reasoning dahil) çağrı başına ~1 130 token'ı geçerse devreye girer** (0,196 girdi + 540 × C × 1,32e-6 = 1,00 → C ≈ 1 128). M'nin temel varsayımı ortalama deepseek 460, gpt 260, gemini 60 token'dı; yani tavan temel varsayımın çok üstünde bir reasoning uzunluğunda işler. Beklenen ve makul en kötü toplam (0,41–0,86) tavanın altında, ama makul en kötü durumda marj dardır.

Bu tahminin dışında kalanlar:
1. **Fiyatlar ve token'lar tahmindir**; M tek kısa soğuk testten ve varsayılan istem uzunluklarından türetildi, "kesin bütçe sayılmamalı" [M Sonuç]. DeepSeek/GPT reasoning'i (400/200 token) kaynaksızdır [M §2].
2. DeepSeek sağlayıcı fiyatı sabit değil; completion fiyatı ~13 kat değişebilir [M §6 madde 3]. Bu, DeepSeek toplamını (a) değerinin çok üstüne çıkarabilir.
3. Eşzamanlı çağrılarda tavan kontrolü anında olmaz; uçuştaki çağrılar nedeniyle küçük bir aşma olabilir (tahmin). Developer eşzamanlılığı sınırlı tutmalı.

### 6.5 Yürütme
**Karar: pilot eşzamanlı koşar, batch yok** (§12 karar 11). #29 motoru `call_llm_valid` (eşzamanlı) kullanıyor [#29]. Batch beklemeye ilişkin kullanıcı kuralı (~15 dk, `logs/batches.jsonl`, "batch sonucu topla" görevi) pilot için geçerli değildir; batch yolu tam deney konusudur. Geçersiz yanıtlar aynı çağrı döngüsünde yeniden istenir ve sayılır (§8.1).

---

## 7. Hipotezler (her iki yönüyle)

Pilot **betimseldir**: hücre başına 2 grup (8 ajan yörüngesi) ve izole çizelgede hücre başına 2 tekrar var. Anlamlılık testi planlanmaz (tahmin); "destekler/desteklemez" ifadeleri gözlenen fark yönü ve büyüklüğü içindir. Eşik **e = 2 puan** onaylandı (§12).

**Tanımlar** (her model ve kimlik çifti/stil çifti için ayrı):
- `D_iso` = iki hücrenin (ör. iki stil, aynı kimlik) izole çizelgesinde 5 değer üzerinden ortalama katkı farkı.
- `D_grup(t)` = aynı iki hücrenin t. turdaki grup ortalama katkı farkı (hücre içindeki 2 grubun ortalaması).
- `g` = bir hücrenin iki grubunun aynı turdaki ortalamaları arasındaki fark (gürültü ölçüsü).
- Eşik `e` = 2 puan (20 puanlık ölçekte %10).
- Bir fark yalnızca |fark| > max(e, g) ise "var" sayılır (tahmin): iki grup arası dalgalanmayı aşmayan fark okunmaz.

### H1. Kimlik/stil izole ajanın davranışını değiştirir mi? (BG §4 sorusunun ilk yarısı)
- **H1a (fark var):** |D_iso| > max(e, g). Destekleyen gözlem: kartlar (stil veya şehir) arasında izole çizelge düzeyi veya eğimi ayrışıyor.
- **H1b (fark yok):** |D_iso| ≤ max(e, g) tüm kart çiftlerinde. Destekleyen gözlem: çizelgeler üst üste. Bu sonuç pilotu geçersiz kılmaz; "tanımın yazılışı sonucu belirler" [CL]; farkın olmaması modelin kartı yok saydığına da (muhakeme metninden bakılır, §9) gerçek etkisizliğe de işaret edebilir.

### H2. Grup etkileşimi farkı büyütür mü, söndürür mü, korur mu? (BG §4 ana soru)
H1a gözlendiyse, aynı kart çifti için:
- **Büyür:** D_grup(10) aynı işaretle ve |D_grup(10)| > |D_grup(1)| + e. Destek: farkın tur boyunca açılması.
- **Söner:** |D_grup(10)| < |D_grup(1)| − e (veya işaret değiştirir). Destek: yörüngelerin birbirine yaklaşması.
- **Korunur:** ||D_grup(10)| − |D_grup(1)|| ≤ e. Destek: yörüngeler paralel. **Düz yörüngeler de bu kategoriye girer; BG §4 bunu "geçerli ama mütevazı" sonuç sayıyor, tasarım bu sonucu da bilgilendirici kılmalı** (iki yönlü kural budur).
- H1b gözlendiyse H2 değerlendirilmez; yalnızca "grup içinde yeni fark doğdu mu" (|D_grup(10)| > max(e, g)) not edilir.

### H3. İzole çizelge, grup davranışını öngörüyor mu? (Flint ve ark. mantığı, BG §4 analiz fikri)
Öngörü: grubun t. turdaki gözlenen "diğerlerinin ortalaması" değerinde, aynı hücrenin izole çizelgesinin 5 noktası arasında doğrusal enterpolasyon (tahmin) ile beklenen katkı. İlk tur için öngörü yok (geçmiş yok); ilk tur ayrı raporlanır. Tur içi çağrılar yalnızca önceki turları gördüğü için, t. turun öngörüsü t−1 turundaki diğerleri ortalamasıyla yapılır (tahmin; #29'daki geçmiş biçimine dayanır).
- **Uyumlu:** 2–10. turlarda gözlenen ile öngörülen ortalama katkı arasındaki ortalama mutlak fark ≤ e. Destek: etkileşim izole politikaya bir şey eklemiyor.
- **Uyumsuz, yukarı:** gözlenen > öngörülen + e; etkileşim katkıyı artırıyor.
- **Uyumsuz, aşağı:** gözlenen < öngörülen − e; etkileşim katkıyı azaltıyor.
- İzole çizelge hücreler arasında ayrışmıyor (H1b) fakat grup ayrışıyorsa: izole ajan tanımı yansıtmıyor, etkileşim farkı yaratıyor demektir; ters durum (izole ayrışıyor, grup ayrışmıyor) etkileşimin farkı sildiği anlamına gelir (tahmin).

### H4. Modeller arası yön tutarlılığı
- **Tutarlı:** üç modelde aynı yönde (büyür/söner/korunur). **Tutarsız:** yön modele göre değişir. Gemini-2.5-flash-lite aynı kuşakta olmadığı için tutarsızlık model ailesinden mi kuşaktan mı bilinemez (§10). Pilotta yalnızca not edilir.

---

## 8. Karar kuralları

Eşik e = 2 puan ve geçersiz yanıt tavanı %5 kullanıcı tarafından onaylandı (§12). Diğer sayısal eşikler (ör. §8.3'teki 2e) kaynaklarda dayanak olmayan tahmindir.

### 8.1 Geçersiz yanıt tavanı
- Geçersiz yanıt: 25, `"abc"`, 12.0, `true`, eksik anahtar; yeniden istenir ve `n_invalid`'e yazılır. Bozuk JSON `n_parse_fail`'e yazılır. Hiçbir değer varsayılanla kodlanmaz [#29; CL]. `max_tokens`'a takılıp kesilen yanıt bozuk JSON olarak `n_parse_fail`'e düşer (tahmin).
- Motorda tavan aşılırsa `RunAborted` fırlar, `logs/raw_calls.jsonl`'a `pgg_run_aborted` olayı yazılır, CLI 1 döner [#29]. **Motorun varsayılan tavan değeri bu görevde okunamadı;** developer görevi pilot için %5'in uygulandığını doğrular, kodda yoksa ekler.
- **Pilot tavanı (onaylı): model başına geçersiz yanıt oranı %5.** Hesap: model başına kabul edilen 540 çağrının %5'i = 27 geçersiz yanıt. Aşılırsa o model durdurulur ve nedene göre (anlamsız değer / bozuk JSON / sağlayıcı hatası) raporlanır. Tek çağrı için yeniden deneme sınırı motordaki değerdir (okunamadı).

### 8.2 Durdurma ölçütleri
Aşağıdakilerden biri olursa pilot durur:
1. **Birikmiş maliyet 1,00 USD'ye ulaştı** (sert tavan; birikmiş `usage.cost` toplamı, yeniden denemeler dahil). Tavan tüm pilotu (3 model birlikte) kapsar; model başına ayrı pay tanımlanmadı. Durumda satırlar kaydedilir ve gerçek maliyet raporlanır.
2. Bir modelde geçersiz yanıt oranı %5'i aştı (§8.1) veya `RunAborted`.
3. `finish_reason` kesilme gösteriyor (ör. `length`): `max_tokens` = 4000 yetersiz demektir; ilk görüldüğünde durum raporlanır, düzeltilmeden devam edilmez (tahmin: tek bir `length` bile sayılır; geçersiz oran tavanı ayrıca geçerli).
4. İstekte `reasoning_effort` gönderildiği görülürse (karara aykırı) durdur. Yanıtta reasoning token alanı hiç dönmüyorsa durdurulmaz, ama raporda "ölçülemedi" olarak belirtilir.
5. Yanıttaki model (`model_snapshot`) istenenle farklı veya sağlayıcı değişiyor [S §4].
6. Sürekli API/sağlayıcı hatası.

Her durdurmada elde edilen satırlar kaydedilir; yarım kalan tur yalnızca ham logda kalır, `resume` yolu yok [#29].

### 8.3 Pilotun sonucu ne tetikler
| Sonuç | Tetiklenen |
|---|---|
| Geçersiz oran tavan altında, kesilme yok, reasoning metinleri tasarım hatası göstermiyor, yanıtlar ne taban (hep 0) ne tavan (hep 20) ne de tamamen sabit | **Tam deneye geçiş önerisi** (M'nin orta/tam ölçeği); kararı kullanıcı verir |
| Yanıtlar hep aynı değerde (taban/tavan/sabit), kart farkı yok ve metinler kartı yok sayıyor | **Tasarım revizyonu**: kart metni/istem; tarihli ek |
| Kart farkı var ama metinler farkın uzunluk/biçimden geldiğini gösteriyor | **Revizyon**: kart uzunluk/biçim eşitleme [R §2.3] |
| İzole çizelge 0–20 arasında doğrusaldan belirgin sapıyor (ör. 10 değerindeki katkı 0 ve 20 doğrusundan > 2e uzak, tahmin) | K Karar 3 C gereği **tam strateji yöntemine (21 nokta) geçiş** [K Karar 3; M §6 madde 6: ek ~1 USD tam deneyde] |
| Yalnızca bir model sorunlu (geçersiz, kesilme, reasoning) | O model için ayar (`max_tokens`, gerekirse `reasoning_effort` eklenmesi) revizyonu, diğerleri için karar ayrı |
| Hiçbir kart farkı yok ve metinler gerçek etkisizlik gösteriyor | Tam deney yine geçerli olabilir (H1b geçerli sonuç); kullanıcıya sorulur |

Pilot sonuçları insan verisine eşlenmez; Herrmann ortalamaları yayımlanmış değerlerle doğrulanmadığı için pilot sonrası insan karşılaştırması kararı tam deney planına bırakılır [R §0 madde 1].

---

## 9. Pilot sonrası muhakeme (reasoning) metinlerinin okunması

[CL: "After a pilot run, read the reasoning texts for design flaws"; BG §5 madde 4 notları: muhakeme metinlerini oku, oran değil.]

- **Amaç:** tasarım kusurunu bulmak. Metinlerden nedensel sonuç çıkarılmaz; metinler karardan sonraki gerekçe de olabilir (özellikle `rationale` alanı, #29) ve modelin gerçek karar sürecini yansıttığı varsayılmaz (tahmin).
- **Neyi okuyacağız (kontrol listesi, tahmin):**
  1. Model kartı (kimliği) gerekçede kullanıyor mu, yoksa kuralları mı hesaplıyor?
  2. Kuralları yanlış anlama (MPCR, kazanç, 10 tur bilgisi) var mı?
  3. Son turda "oyun biter" mantığı (son tur etkisi) görülüyor mu?
  4. Kart metnindeki sözcük kelimesi kelimesine yankılanıyor mu (ör. "reciprocity", "common good")? Bu, değer yüklü kartın talimat gibi okunduğunu gösterir.
  5. Sayısal eğilim puanına benzer ifade ya da biçim/uzunluk farkının gerekçe olarak anılması.
  6. İzole çizelgede model "diğerlerinin ortalaması" bilgisini doğru kullanıyor mu?
  7. Metinlerde istem/şablon artefaktı (JSON biçimi karışıklığı, kesik metin).
  8. Minimal kartta "read the rules carefully and take the time you need" cümlesi gerekçede anılıyor mu (§4.1)? Anılıyorsa minimal hücre farkı bu cümleden gelmiş olabilir.
  9. Olgusal kartta "large urban area / market relations" ifadesi gerekçede kullanılıyor mu?
  10. **Reasoning token sayıları** (`reasoning_effort` gönderilmediği için model varsayılanı): model başına ortalama ve dağılım raporlanır; `finish_reason` = `length` var mı.
- **Örnekleme (tahmin):** her modelin izole satırlarının tamamı (60/model) + her grubun 1., 5. ve 10. turlarının 4 ajan metni (12 grup × 3 tur × 4 = 144/model). Sorun bulunursa ilgili hücre tamamen okunur.
- **Gemini:** yerel reasoning metni yok (soğuk testte 0 token) [S §6]; okuma yalnızca `rationale` alanına dayanır. Varsayılanda bu değişebilir (bilinmiyor).
- **Çıktı:** kusurlar ve değişiklikler **tarihli ek (amendment)** olarak, gerekçesiyle bu dosyanın sonuna yazılır [CL]. Pilot sonrası revize edilen tasarımla koşan ana deney yeni bir `prereg_<ad>.md` ister (tahmin).
- Okuma bulguları sayısal sonuç değildir; sayılar raporlanırken sonuç dosyalarından yeniden doğrulanır [CL].

### Pilot verisinin ana analizden hariç tutulması
- Pilot satırları (`results/<pilot_run>.jsonl`) ana analize **girmez**; ana deneyde aynı kartlar yeniden koşulur [CL].
- Pilot koşusunun `run` adı ve seed'leri (`stable_seed("pgg", run, model, kart, stil, …)`) ana deneyden farklı tutulur [#29]; pilot oturumları ana deney oturumu olarak yeniden kullanılmaz.
- Pilot sonuçları yalnızca tasarım kararı için (§8.3) ve bu belgenin ekinde betimsel özet olarak kullanılır.

---

## 10. Sınırlılıklar

1. **Gemini farklı kuşakta:** `google/gemini-2.5-flash-lite`, DeepSeek-v4.1-flash ve GPT-6-luna ile aynı kuşakta değil (kullanıcı kararı, kaynaklarda ayrıca doğrulanmadı). Modeller arası farklar model ailesine mi kuşak/yetenek farkına mı bağlı, ayrıştırılamaz [M §6]. Reasoning davranışı da farklı: Gemini'de 0 (tek ölçüm), DeepSeek'te 29 token [S §2, §6].
2. **Herrmann şehir ortalamaları yayımlanmış değerlerle karşılaştırılamadı** (yayımlanmış sayısal ortalama yok, yalnızca Fig. 1; SOM okunamadı); `data` filtresinin tanımı bilinmiyor [R §0 madde 1, 3; G7b]. Şehir seçiminde kullanılan P ortalamaları (§3) geçicidir.
3. **Küçük örnek:** hücre başına 2 grup; betimsel; gürültü ile fark ayrılamayabilir.
4. **Tek ölçümlük maliyet/token tabanı:** soğuk test tek kısa istemdi, oyun istemini temsil etmez [S §5, §6; M §6]. `reasoning_effort` gönderilmediği için reasoning uzunluğu önceden bilinmiyor; maliyet tahmini bu yüzden geniş aralıklıdır (§6.4).
5. **Sağlayıcı sabit değil:** özellikle DeepSeek'te davranış ve fiyat sağlayıcıya bağlı olabilir [S §5].
6. **Kart zayıflıkları:** şehirler arası içerik aynı, yalnızca ad değişiyor; olgusal iddia doğrulanmadı (tahmin); minimal kartın uzunluk dolgusu davranış talimatı gibi okunabilir; karakter uzunluğu stiller arasında ~%15'e kadar farklı (§4.1, §4.4).
7. **Çizelge (5 nokta)** doğrusal olmayan kıvrımları kaçırabilir (K Karar 3).
8. **Motor varsayımları (#29):** ceza bilgisi görünürlüğü Herrmann talimatlarından doğrulanamadı (pilotta P yok, acil değil); satırlar tur bitince yazılıyor (resume yok); `--cards` biçimi ve `city` alanı doğrulanmadı (§4.2).
9. **SILICA/Flint SI'ları okunamadı;** "SILICA'da izole kol yok" ana metne dayanıyor [R §2, §6].
10. **Tek dil:** tüm istem İngilizce; sonuçlar başka dillere genellenemez.

---

## 11. Sıra (özet)

1. Kullanıcı onayı verildi (2026-10-04). 2. Kart dosyası (12 kart, eşitlenmiş uzunluk) hazır: `pilot_cards.json`. 3. Developer: `pgg_game.py --dry-run` ile 1 620 çağrı ve maliyetin §6 ile tuttuğunu doğrular; tutmazsa API çağrısı yapmadan durur ve raporlar. 4. Motor kontrolü: `reasoning_effort` gönderilmiyor, `max_tokens` = 4000, 1 USD tavan, %5 geçersiz tavanı (yoksa eklenir, mock testle doğrulanır). 5. Pilot koşusu (Boston + Riyadh, N, homojen, 3 model, eşzamanlı). 6. Muhakeme okuması, tarihli ek, karar (§8.3).

---

## 12. Karar verildi (kullanıcı, 2026-10-04)

| # | Konu | Karar |
|---|---|---|
| 1 | Şehirler | Boston, Copenhagen, Athens, Riyadh. 12 kart yazılır; **pilota yalnızca Boston + Riyadh girer** (2 kimlik × 3 stil = 6 hücre). Athens'in `data` belirsizliği notu kalır (§3). |
| 2 | Dil | Kartlar dahil tüm istem İngilizce; şehir adları İngilizce. |
| 3 | `reasoning_effort` | Pilotta **gönderilmez** (model varsayılanı). Reasoning token'ları ölçülür ve raporlanır. |
| 4 | `max_tokens` | **4000** (oyun çağrıları). |
| 5 | Tekrar | Hücre başına **2 homojen grup** (N) + izole çizelge **5 değer × 2 tekrar**. Model başına **540**, toplam **1 620** çağrı. |
| 6 | Bütçe | Pilot için **1,00 USD sert tavan** (birikmiş `usage.cost`'a göre; aşılırsa koşu durur). |
| 7 | `rationale` | Alan kalır. |
| 8 | Geçersiz yanıt tavanı | Model başına **%5**. |
| 9 | Eşik | **e = 2 puan**. |
| 10 | Kart biçimi | Üç stil: minimal (yaş + öğrenci + nötr cümle), değer yüklü, olgusal; eşit uzunluk; sayısal eğilim puanı yok (§4). |
| 11 | Yürütme | Çağrılar **eşzamanlı**; batch yok. |
| 12 | Modeller | `deepseek/deepseek-v4.1-flash`, `openai/gpt-6-luna`, `google/gemini-2.5-flash-lite`. |

Kararların uygulanması: entegrasyon dalı `orc/PublicGoods` (07b0358) üzerinde developer görevi (§11).

---

## 13. Taslaktan (#30) değişenler

Bu bölüm taslak durumunu kayda geçirir; başka bölümlerde tekrarlanmaz.
- Taslakta başlık "TASLAK — kullanıcı onayı bekliyor" idi; kart şablonları Türkçeydi (Boston taslağı elle sayımla 18 / 7 / 17 kelime, yani eşit değildi) ve kart tablosu yoktu. Şimdi İngilizce, eşit uzunlukta 12 kart (§4).
- Taslakta toplam maliyet tahmini ~0,38 USD, en kötü durum ~0,8 USD, tavan önerisi 1,00 USD idi; `reasoning_effort` ve `max_tokens` açık soruydu. Şimdi tavan karar olarak onaylı, tahmin `rationale` ve `max_tokens` = 4000 ile yeniden hesaplandı (§6.4).
- Taslakta çağrı sayısı (1 620) aynıydı ve değişmedi.
- Pilota girecek kimlikler (Boston + Riyadh) taslakta öneriydi; karar oldu.

---

## Kaynaklar
`kararlar.md`, `maliyet_analizi.md`, `gorev_soguk_test_sonuclari.md`, `rapor_acik_isler.md`, `gorev7b_herrmann2008_data_filtresi.md` (workspace); depo `CLAUDE.md` ("Write the plan before the data"), `notes/BACKGROUND.md` §4–5; #29 görev sonucu (dal `orc/PublicGoods`, 07b0358; dalda doğrulanmadı).

---

ONAYLANDI — 2026-10-05 (kullanıcı)

# Amendment 2026-10-05

Durum: **onaylandı (2026-10-05, kullanıcı; A6 soru 19).** Yukarıdaki onaylı metin (§1–§13 ve Kaynaklar) değiştirilmemiştir; bu ek, ilgili maddeleri aşağıda belirtilen yerlerde **geçersiz kılar**. Bu ek yazılırken kod çalıştırılmadı, API çağrısı yapılmadı, depoya yazılmadı.

Ek kaynak kısaltmaları: **#32** = ilk pilot koşusunun (pilot_20261005) görev sonucu; **PD** = `pilot_durdurma_raporu.md` (#33); **#34** = tesisat görevinin sonucu (dal `orc/PublicGoods`, ad24572); **#36** = `kart_tasarimi_v2.md`, `kart_linter.py`, `pilot_cards_v2.json`. Bu ekteki sayılar bu kaynaklardan alınmıştır; #32 sayılarını log dosyalarından doğrulayamadım, çünkü dosyalar kayıptır (PD). "(tahmin)" = kaynağı olmayan çıkarım.

## A1. pilot_20261005 neden durdu, verisi neden kayboldu

- **Durma nedeni:** §8.2 madde 3 tetiklendi. DeepSeek (`boston_minimal`, grup 001, 1. tur) 4000 token'ın tamamını reasoning'e harcadı, içerik boş geldi, `finish_reason = length`. Koşu **56 sn** (56,2) sonra durdu; birikmiş gerçek maliyet **0,0334 USD** (0,033421; 1 USD tavanının ~%3,3'ü). 1 USD tavanı (madde 1) ve %5 geçersiz tavanı (madde 2) devreye girmedi [#32; PD].
- **Ne kadar veri vardı:** 1 620 planlanan çağrının 193'ü yanıt aldı, 186 satır sonuç dosyasına yazıldı; Riyadh kartlarına sıra gelmedi [#32; PD]. Bu 186 satır hiçbir analize girmez.
- **Veri neden kayboldu:** koşu bir git worktree'sinde yapıldı; `results/` ve `logs/` git-ignore'daydı. Worktree birleştirmeden sonra silindi, dosyalar onunla gitti. `pilot_20261005*` dosyası hiçbir yerde bulunamadı; depodaki `logs/raw_calls.jsonl` bu koşuya ait değil [PD "Kaynaklar ve erişim durumu"]. Ücretli 193 çağrının ham kaydı bu yüzden yok.
- **Kaynaklar:** #32 sonucu; `pilot_durdurma_raporu.md`.

## A2. Tesisat değişiklikleri (#34)

Kod tarafı mock testlerle doğrulandı: `python -m unittest discover -s tests -v` → 124 test, OK (89 eski, 35 yeni) [#34]. Gerçek koşu yapılmadı; aşağıdaki davranışlar henüz gerçek API çağrısıyla sınanmadı.

### A2.1 Değişiklik listesi ve prereg'e etkisi

| # | Değişiklik (#34) | Geçersiz kıldığı / etkilediği prereg maddesi |
|---|---|---|
| a | **Kalıcı çıktı dizini.** Sonuç dosyası, özet ve `raw_calls.jsonl` `<runs_dir>/<run>/` altına yazılır. `runs_dir` sırası: `--runs-dir`, config `runs_dir`, `PGG_RUNS_DIR`, orc `workspace/runs`. Göreli yol, var olmayan dizin ya da git worktree'si içindeki yol verilirse koşu çağrı yapmadan durur. Koşu sonunda özette `files` bölümü (dosya adı + satır sayısı) yazılır. | §6.1 "Çıktı: `results/<run>.jsonl`" ve §9 "`results/<pilot_run>.jsonl`" yolları |
| b | **`max_tokens` = 16000** (4000'den), **istemci zaman aşımı 300 sn** (60 sn'den). | §6.1, §8.2 madde 3 metnindeki "4000", §11 madde 4, §12 karar 4 |
| c | **Sağlayıcı sabitleme.** Her modelde `provider.order = only = [slug]`, `allow_fallbacks: false`; her yanıt satırına `provider` ve `provider_quantization` loglanır. Yanıttaki sağlayıcı adı beklenenden farklıysa koşu `provider_mismatch` ile durur. Yanıtta ad hiç yoksa yalnızca `n_provider_unknown` sayılır, koşu durmaz (A6 soru 8). Nicemleme yalnızca istek tarafı olarak özete yazılır; belgelenmiş yanıt şemasında alan olmadığı için `provider_quantization` büyük olasılıkla `null` kalır [#34]. | §6.2 ("sağlayıcı sabit değil"), §8.2 madde 5, §10 madde 5 |
| d | **Sağlayıcı hata sınıfı.** `finish_reason == "error"` olan ya da 0 token ve 0 maliyetli (veya maliyet alanı olmayan) yanıt `error_kind = "provider"` sayılır, yeniden istenir, `n_provider_error` olarak ayrı sayılır; `n_parse_fail`'e ve %5 geçersiz tavanına **girmez**. | §8.1 (tavan hesabı), §8.2 madde 2 ve 6 |
| e | **Round-robin sıra.** Her tur her hücreyi (kart × model) bir kez içerir; art arda gelen her 6 birim 6 kartın hepsini kapsar. Sıra `stable_seed(ns, run, "order", …)` ile belirlenir; koşu başında `pgg_run_start` olayıyla loga, sonunda özetteki `unit_order` alanına yazılır. | §6.1 akış (sıra tanımsızdı); çağrı sayısı (1 620) değişmez |
| f | **Düzeltilmiş kazanç etiketi.** "Your earnings from the project" yalnızca 0,4 × toplam katkıdır; tur toplamı ayrı etiketle ("total earnings") gösterilir. Geçmiş satırlarında da aynı düzeltme. Ceza bütçesi hâlâ tur toplamına bağlı; yalnızca etiketi düzeltildi. | §6.1 istem içeriği (kazanç formülü) |
| g | **İzole kol ayarı `isolated_frame`** (`one_shot` / `repeated`); seçim kullanıcıda (A4). | §5 |
| — | Yer tutucu (sağlayıcı slug'ı, `isolated_frame`) seçilmemiş config ile gerçek koşu başlamaz [#34]. | — |

Eski (onaylı) sürümde `max_tokens = 4000` ve zaman aşımı 60 sn idi; ek, yalnızca bu satırlar yerine geçer.

### A2.2 Değişen istem metinleri (#34'ten aynen)

Örnek tur 1 katkıları 4, 7, 10, 13 (toplam 34): proje kazancı 0,4 × 34 = 13,6; oyuncu 1'in tur toplamı 20 − 4 + 13,6 = 29,6.

**Katkı istemi, yeni metin (tam):**
```
RULES
- A group has 4 players: you and 3 others. Players cannot communicate.
- The same 4 players stay together for all 10 rounds.
- In every round each player receives 20 points.
- Each player then decides how many of these points (a whole number from 0 to 20) to contribute to a group project. Points that are not contributed stay with the player.
- Every point contributed to the project yields 0.4 points for each of the 4 players. Your earnings from the project in a round are therefore:
  0.4 x (sum of all 4 players' contributions)
- Your total earnings in a round are the points you kept plus your earnings from the project:
  20 - (your contribution) + 0.4 x (sum of all 4 players' contributions)
- After each round you are told every player's contribution and your own earnings.

HISTORY OF PREVIOUS ROUNDS
Round 1
  Contributions: Player 1 (you): 4; Player 2: 7; Player 3: 10; Player 4: 13. Group total: 34.
  Your earnings from the project: 13.6. Your total earnings this round: 29.6.

ROUND 2 of 10. You are Player 1. All players decide at the same time, without seeing each other's choice for this round.
How many of your 20 points do you contribute to the group project? (a whole number from 0 to 20)
```

**Değişen satırlar (önce → sonra):**

Kurallar bloğu:
```
önce:   Your earnings from the project in a round are therefore:
          20 - (your contribution) + 0.4 x (sum of all 4 players' contributions)
sonra:  Your earnings from the project in a round are therefore:
          0.4 x (sum of all 4 players' contributions)
        - Your total earnings in a round are the points you kept plus your earnings from the project:
          20 - (your contribution) + 0.4 x (sum of all 4 players' contributions)
```
Geçmiş satırı:
```
önce:   Your earnings from the project: 29.6.
sonra:  Your earnings from the project: 13.6. Your total earnings this round: 29.6.
```

**Ceza adımı (P koşulu; pilotta kullanılmaz).** RULES bloğu yukarıdaki yeni bloğun aynısı; ceza kuralı satırı değişmedi. Değişen satırlar (sonra):
```
  Your earnings from the project: 13.6. Your total earnings this round: 29.6.
  Punishment points you assigned: Player 2: 3 (cost to you: 3).
  Punishment points you received: 0 (points lost: 0).
  Your earnings after punishment: 26.6.

ROUND 2 of 10, punishment step. You are Player 1.
This round: Contributions: Player 1 (you): 4; Player 2: 7; Player 3: 10; Player 4: 13. Group total: 34. Your earnings from the project this round: 13.6. Your total earnings this round (before punishment): 29.6.
You may now assign punishment points (0 to 10) to each other player. A point costs you 1 and reduces the receiving player's earnings by 3. Your total cost may not exceed your total earnings this round, so you can assign at most 29 points in total. All players decide at the same time.
```
Önceki metinde son iki cümlede "Your earnings from the project this round: 29.6" ve "…may not exceed your earnings from the project this round…" yazıyordu; ceza bütçesinin değeri değişmedi (29), yalnızca etiket düzeltildi [#34].

**İzole kol, mevcut ifade aynen:** `There is no history and no other round.` (A4'te ele alınır). Mevcut istemin QUESTION bölümü:
```
QUESTION
Consider one round. Suppose the other 3 players of your group each contribute, on average, 10 points. There is no history and no other round.
How many of your 20 points do you contribute to the group project? (a whole number from 0 to 20)
```
`one_shot` seçeneğinde bu bölüm aynı kalır; kurallar bloğunda yalnızca A2.1 (f) düzeltmesi (yukarıdaki iki satır) yapılır, ayrıca "The game is played in rounds; this question is about one round." satırı korunur.

### A2.3 Durdurma kuralları (§8.2) ve maliyete etkisi

Ek onaylanırsa §8.2 şöyle okunur (yalnızca değişenler):
1. **Madde 1 (1,00 USD sert tavan):** değişmez.
2. **Madde 2 / §8.1 (%5 geçersiz tavanı):** yalnızca anlamsız değer (`n_invalid`) ve bozuk JSON (`n_parse_fail`) sayılır. Sağlayıcı hataları (`n_provider_error`) tavana **sayılmaz**, ayrı raporlanır. Bu, ilk pilotta Gemini'nin `finish_reason = "error"`, 0 token, 0 USD ile gelen 3 yanıtının bozuk JSON sayılmasını önler [#32; PD].
3. **Madde 3 (`length`):** kural aynen durur; eşik artık `max_tokens` = 16000. Tek bir `length` yine durdurur.
4. **Madde 4:** değişmez (`reasoning_effort` yine gönderilmez).
5. **Madde 5:** artık sağlayıcı da denetlenir. Sabitlenen sağlayıcı adından farklı bir yanıt `provider_mismatch` ile durdurur. İlk pilotta sağlayıcı denetlenmiyor ve loglanmıyordu [PD]. Sağlayıcı adı hiç dönmezse durma yok, yalnızca sayım (A6 soru 8'e bağlı).
6. **Madde 6:** sağlayıcı hataları ayrı sınıf olarak sayılır; "sürekli hata" kararı bu sayıma dayanır.
7. **Yeni koşul:** `runs_dir` geçerli değilse koşu başlamaz (A2.1 a).

**Dry-run maliyeti (`--dry-run --config configs/pilot.json`) [#34]:**
```
deepseek  deepseek/deepseek-v4.1-flash        540 çağrı (contribute_N=480, isolated=60)  ~0.18 USD (tahmin)
gpt       openai/gpt-6-luna                   540 çağrı (contribute_N=480, isolated=60)  ~0.13 USD (tahmin)
gemini    google/gemini-2.5-flash-lite        540 çağrı (contribute_N=480, isolated=60)  ~0.07 USD (tahmin)
TOPLAM                                       1620 çağrı                              ~0.38 USD (tahmin)
Tavan (her çağrı max_tokens=16000 çıktıyı doldurursa; beklenen değil): deepseek ~3.71, gpt ~4.38, gemini ~3.51; toplam ~11.60 USD (tahmin)
```
- Çağrı sayısı değişmedi: 1 620. Beklenen maliyet 0,38 USD (tahmin); `maliyet_analizi.md` varsayımlarına dayanır, 16000 sınırı beklenen değeri değiştirmez. Teorik tavan 4000 sınırındaki ~3,05 USD'den **~11,60 USD'ye** çıktı (tahmin; her çağrı sınırı doldurursa, gerçekçi değil).
- **Gözlenen birim maliyetle yeniden tahmin:** ilk pilotun ölçülen birim maliyetleriyle (DeepSeek ~0,000795, GPT ~0,000108, Gemini ~0,000080 USD/çağrı) 540 çağrıya ölçeklenirse toplam **~0,53 USD** (tahmin; küçük örnek, girdi büyümesi eksik sayılmış, yani alt tahmin) [PD]. DeepSeek ~0,43 ile baskın.
- **1 USD tavanı hâlâ yeterli mi?** Evet, **koşullu**: 0,38 (dry-run) ve ~0,53 (gözlenen birim maliyet) her ikisi de 1 USD'nin altında (tahmin). 11,60 USD teorik tavan 1 USD'nin çok üstünde, ama bu durumda tavan koşuyu durdurur; round-robin sıra sayesinde durmuş koşu bile tüm kartlardan veri verir (A2.1 e). Koşullar:
  - Dry-run fiyatları sabitlenmemiş sağlayıcıya göredir. DeepSeek completion fiyatı seçilen sağlayıcıya göre değişir (#34 tablosunda 0,18 ile 2,4 USD / 1M çıktı arası). DeepSeek'in toplamının ~0,43 USD'si büyük ölçüde completion'dan geldiği için, completion fiyatı 0,42'nin kabaca 2,3 katını (~0,97 USD / 1M) aşarsa beklenen toplam 1 USD'ye yaklaşır (tahmin; kaba hesap: kalan iki modelin toplamı ~0,10 USD varsayılarak). Seçilecek sağlayıcının fiyatı bu eşiğin altında kalmalı (A6 soru 1).
  - 16000 sınırıyla ilk pilotta kesilen uzun çağrılar tamamlanır; bu, DeepSeek maliyetini 4000 sınırında ölçülene göre artırır. Etkinin büyüklüğü bilinmiyor (reasoning kuyruğu ölçülmedi; ölçülen en yüksek kabul edilen reasoning 3 049 token) [PD].
  - Pilot koşusundan önce sağlayıcı seçilip dry-run yeniden çalıştırılmalı; sağlayıcı fiyatı dry-run'a yansır [#34].

### A2.4 Veri kalıcılığı kuralı (kullanıcı onaylı)
Bundan sonra gerçek API çağrısı yapan her koşu ham logu (`raw_calls`), sonuç `jsonl` dosyasını ve özet dosyalarını worktree **dışındaki** kalıcı `runs/<run_adı>/` dizinine yazar. Görev bitmeden dosyaların orada var olduğu ve satır sayıları raporlanır; denetleyici bunu kontrol eder. Hesap kimliği içeren ham loglar commit'e girmez. Bu kural pilot koşusu görev açıklamasına açıkça yazılacaktır.

## A3. Yeni kartlar (ONAYLANDI — 2026-10-05, A6 soru 9–17)

Dosyalar: `kart_tasarimi_v2.md`, `pilot_cards_v2.json` (12 kart), `kart_linter.py` [#36]. §4'teki 12 kartın (`pilot_cards.json`) yerine geçmesi onaylandı (pilotta yalnızca Boston + Riyadh, `pilot_cards_v2.json`; A6 soru 14). Pilota girecek kimlikler değişmez (Boston + Riyadh, §12 karar 1); Copenhagen ve Athens kartları hazır, pilotta çağrı yok.

- **Değişikliğin gerekçesi [#36]:**
  1. Eski değer yüklü kartlar oyundaki hamleyi adlandırıyordu ("contributing", "reciprocity", "sharing", "common good").
  2. Eski olgusal kart ("economy closely tied to market relations") Henrich vd.'nin piyasa entegrasyonu değişkenidir, yani insan verisinin açıklayıcı değişkenini kartın içine koyuyordu; kaynaksızdı ve şehre özgü değildi.
  3. Eski minimal kartın dolgu cümlesi ("Please read the rules carefully…") genel bir davranış talimatı gibi okunabiliyordu (§4.1'in kendi sınırlılık notu).
  4. Kartlar dört şehirde aynı şablondu; şehre özgü içerik yoktu (§4.1, §10 madde 6).
- **Yeni tasarım:** her şehre özgü değer ve olgu cümleleri; olgusal kartlardaki her olgu kaynaklı (8 olgu; yalnızca Boston 1635 okul olgusu kaynak sayfadan doğrudan doğrulandı, kalanı ikincil kaynak, çoğu Wikipedia); doğrulanamayan olgu kullanılmadı. Piyasa, hukuk, güven, din olguları kartlarda yok. Minimal kart: "You are a 21-year-old university student living in {City}." Yaş üç stilde de "21-year-old".
- **Linter kuralı:** `kart_linter.py`, kart metnini küçük harfe çevirip 13 yasaklı kökü alt dizgi olarak arar: contribut, cooperat, reciproc, shar, common good, public good, collective, generos, fair, trust, group, project, invest. Yapı denetimi de yapar (4 alan dolu, card_id tekil). Yanlış pozitif riski var ("affairs", "sharp", "entrust"), yanlış negatif riski de ("give", "pool", "teamwork", "selfless" listede yok); politika: bastırma yok, kart yeniden yazılır [#36].
- **Sonuç:** `python3 kart_linter.py pilot_cards_v2.json` → **12/12 kart geçti**, çıkış kodu 0; kendi kendine test (`--selftest`) çıkış kodu 0. Karşılaştırma için eski `pilot_cards.json` → **8/12** (dört eski değer kartı `contribut`, `reciproc`, `shar`, `common good` köklerine birden takıldı) [#36]. Kelime/karakter: minimal 9 kelime (58–62 karakter), değer yüklü 21–24 (135–143), olgusal 26–29 (144–172).
- **Uzunluk:** v2 kartlar §4.4'teki "kelime farkı ≤ %4" eşitliğini **sağlamaz** (minimal 9, diğerleri 21–29 kelime). #36 seçenek (ii)'yi önerir: eşitlik gevşetilir, uzunluk loglanıp analizde ortak değişken olur; seçenek (i) (üç stile aynı nötr cümle, "You are about to take part in a short decision-making session.") eşitliği de sağlamaz (21 ile 33–41 kelime). `pilot_cards_v2.json` (ii)'ye göre yazıldı. Minimal ile diğer stiller arasındaki farkın uzunluktan mı içerikten mi geldiği ortak değişkenle kısmen bile ayrılamayabilir (tahmin) [#36]. Onaylanırsa §4.1, §4.4 ve §8.3 3. satır (uzunluk eşitleme) buna göre okunur.
- **Sınırlılıklar [#36]:** değer kartları ülke ölçeğinde ortalamalara dayanır; "you" ile yazılınca bireye atfedilmiş olur (stereotip riski). Riyadh değer kartında kaynak cümledeki "religious authority" bilerek çıkarıldı (kaynağı eksik aktarmak). Copenhagen için tek kaynaklı bir değer var.
- **İlk çalışma (BACKGROUND §1) ile ilişki [#36]:** üç stil fikri, sayısal puanın yokluğu ve yaş + meslek minimal tanımı devralındı; değer/olgusal içerik yeni, kaynaklı ve hamleyi/piyasa değişkenini adlandırmayan metinlerle değiştirildi; ilk çalışma kartlarıyla birebir kıyas yapılmamalı.

## A4. İzole kol: sınırlılık ve seçenekler

- **Mevcut ifade ve sınırlılığı:** izole istemde "There is no history and no other round." yazar ve kurallar "The game is played in rounds; this question is about one round." der. Bu çerçeve izole ajanı **tek seferlik** bir karara koyar; oysa grup kolundaki ajan, aynı 4 oyuncuyla 10 turluk bir oyunun içindedir. Yani izole ile grup arasındaki fark yalnızca "diğerlerinin davranışı bilgisi" değil, **oyunun zaman ufku** (tekrar var/yok) da olur. Bu iki etken ayrıştırılamaz (tahmin; yorum, #34 bunu doğrudan söylemiyor). Tek seferlik kararda katkı gölgesi (son-tur mantığı) ve itibar gerekçesi yokluğu izole katkıyı grup kolunun ilk turundan sistematik olarak farklı kılabilir (tahmin).
- **`one_shot` (mevcut):** QUESTION bölümü aynı; kurallarda yalnızca A2.1 (f) düzeltmesi.
- **`repeated` (yeni) [#34]:** 10 turluk oyunun "ilk ya da son olmayan" bir turu, başkalarının önceki tur ortalaması verilerek. Kurallar bloğu grup istemiyle aynı ("The same 4 players stay together for all 10 rounds." dahil); QUESTION:
```
QUESTION
Consider a round of this 10-round game that is neither the first nor the last round. In the previous round the other 3 players of your group contributed, on average, 10 points each.
How many of your 20 points do you contribute to the group project in this round? (a whole number from 0 to 20)
```
- **Hipotez/yoruma etkisi (tahmin):**
  - `one_shot` ile H1 (D_iso: kimlik/stil izole davranışı değiştirir mi) tek seferlik bir karar için ölçülür; H3 (izole çizelge grup davranışını öngörür mü) izole ile grup arasında ufuk farkını da içerir; uyumsuzluk "etkileşim katkı ekliyor" yerine "ufuk farkı" olarak da okunabilir.
  - `repeated` ile izole ve grup kolu aynı ufuk çerçevesini paylaşır; H3 ufuk farkından daha temiz ayrışır. Bedeli: izole kol artık "geçmişsiz" değildir (bir önceki tur ortalaması vardır), prereg §5'teki "geçmiş yoktur" ve BG §4'teki izole tanımından ayrılır. Ayrıca "neither the first nor the last" ifadesi, son-tur ve ilk-tur etkilerini bilerek dışarıda bırakır ama grup kolunun 1. ve 10. turlarıyla karşılaştırmayı daraltır.
  - Seçimden bağımsız: iki çerçeve arasında sonuçlar farklı çıkarsa bu pilotta yalnızca betimsel not edilir.
- **Seçim kullanıcıda.** Config'teki `isolated_frame` alanı seçilene kadar yer tutucudur ve gerçek koşu başlamaz (A6 soru 5, 6).

## A5. Yeni run adı ve seed namespace'i

- İlk pilotun `run` adı `pilot_20261005`, `seed_namespace` değeri `pgg-pilot` idi (config'te hâlâ aynı [#34]). Bu ek onaylanırsa pilot **yeni bir run adıyla ve yeni bir seed namespace'iyle** koşar; eski adlar yeniden kullanılmaz.
- **Öneri (tahmin):** run adı `pilot_v2_<tarih>` (`<tarih>` = koşu günü, YYYYMMDD; kesin tarih koşu günü belirlenir). Seed namespace'i `pgg-pilot-v2`. Run adı `stable_seed` girdisine de girdiği için (§9) seed'ler ek olarak ayrışır [prereg §9].
- Seed namespace'i ana deneyden **ve** ilk pilottan (`pgg-pilot`) ayrı olmalıdır. Ana deney için kullanılacak namespace bu belgede tanımlı değildir; seçilirken `pgg-pilot-v2` ile çakışmamalıdır.
- Çıktı dizini: `<runs_dir>/pilot_v2_<tarih>/` (A2.1 a). Aynı adla ikinci koşu yapılmaz.

## A6. Karar verildi (kullanıcı, 2026-10-05)

Açık sorular (#34 ve #36) kullanıcı tarafından cevaplandı (kaynak: ortak hafızadaki "KULLANICI KARARI (2026-10-05)" notu). Yer tutucu kilidi (A2.1) config'e bu değerler girilince kalkar; kilidin açılması için kalan koşullar notlarda.

| # | Soru | Karar | Not |
|---|---|---|---|
| 1 | DeepSeek sağlayıcı | `deepinfra` | #34 endpoints tablosunda bu tag yoksa API çağrısı yapmadan dur ve kullanıcıya sor; tahminle başka sağlayıcı seçilmez. Dry-run seçilen sağlayıcının fiyatıyla yeniden çalıştırılır; beklenen toplam 1 USD'yi aşıyorsa koşulmaz, raporlanır. |
| 2 | DeepSeek nicemleme | `fp8` | Tag fp8 değilse API çağrısı yapmadan dur ve kullanıcıya sor. |
| 3 | GPT sağlayıcı | `openai` | |
| 4 | Gemini sağlayıcı | `google-vertex` | |
| 5 | `isolated_frame` | `repeated` | A4'teki `repeated` çerçevesi. |
| 6 | "neither the first nor the last round" | Kalır | |
| 7 | `runs_dir` | `/Users/karbon/Desktop/Veri Bilimi/complexity-prj/orc/data/projects/PublicGoods/workspace/runs` | Dizini kullanıcı oluşturur; yoksa koşulmaz, raporlanır. |
| 8 | Sağlayıcı adı dönmezse | Durma yok | `n_provider_unknown` sayılır ve raporlanır. |
| 9 | Kart uzunluğu | Seçenek (ii) | Eşitlik gevşetilir; kart uzunluğu loglanır ve ortak değişken olur. |
| 10 | Yaş | Evet | Üç stilde de "21-year-old". |
| 11 | Riskli olgular | Ana kartlara girmez | |
| 12 | Riyadh değer kartı | Çıkarılmış hali kalır | "religious authority" çıkarılmış. |
| 13 | Olgu kaynakları | İkincil kaynaklar kabul (pilot için) | Ana deneyden önce birincil doğrulama görevi açılacak. |
| 14 | Kart metni onayı | Boston ve Riyadh onaylandı (`pilot_cards_v2.json`) | Copenhagen ve Athens pilot sonrası. |
| 15 | Değer çerçevesi | "Where you grew up, people …" kalır | |
| 16 | Copenhagen ikinci kaynak araştırması | Açılabilir | Pilotu BEKLETMEZ. |
| 17 | Linter | Kökler eklenir: give, pool, team, selfless | v2 kartlar yeniden linter'dan geçirilir; takılan olursa koşulmaz, raporlanır. |
| 18 | Run adı / seed | `pilot_v2_<koşu günü YYYYMMDD>`; seed namespace `pgg-pilot-v2` | A5 önerisi onaylandı. |
| 19 | Ek bütünü | Onaylandı | |

### Pilot v2 koşu parametreleri (özet)

- Kartlar: `pilot_cards_v2.json`, yalnızca Boston + Riyadh (6 hücre/model); koşul N, yalnızca homojen grup.
- Modeller: 3 (`deepseek/deepseek-v4.1-flash` @ deepinfra fp8, `openai/gpt-6-luna` @ openai, `google/gemini-2.5-flash-lite` @ google-vertex).
- `max_tokens` 16000; istemci zaman aşımı 300 sn; `reasoning_effort` gönderilmez; sıcaklık gönderilmez.
- Maliyet: 1 USD sert tavan (birikmiş `usage.cost`); geçersiz yanıt tavanı %5 (model başına).
- Sıra: round-robin (A2.1 e).
- Run adı `pilot_v2_<YYYYMMDD>`, seed namespace `pgg-pilot-v2`; `isolated_frame = repeated`.
- Veri kalıcılığı: tüm çıktılar (raw_calls, results jsonl, özet) `<runs_dir>/<run>/` altına; görev bitmeden dosyaların orada olduğu ve satır sayıları raporlanır; denetleyici kontrol eder (A2.4).
- Rapor yalnızca tesisat ve sayılar içerir; muhakeme okuması ayrı görev.

---

# Not — pilot_v2_20261005 teknik kesintiler ve sürdürme (2026-10-05)

Bu not yukarıdaki metni değiştirmez; yalnızca pilot v2 koşusunun teknik seyrini kayda geçirir. Bilimsel yorum içermez. Not yazılırken kod çalıştırılmadı, API çağrısı yapılmadı. Kaynaklar: **SY** = `pilot_v2_sayilar.md` (#44; saat 22:59 durumu); **#43** = `rapor_gorev43_pilot_v2_resume.md`; **SUM** = `runs/pilot_v2_20261005/pilot_v2_20261005_summary.json` (segment 3 kapandıktan sonra yazılmış son hali); **KOD** = `_kod_58ae381/pgg_game.py` "Resume" açıklaması (satır 135–162).

**Durum: koşu tamamlanmadı.** 72 birimin 70'i tamam, 2'si eksik: `deepseek|riyadh_minimal|minimal|N|group|1` ve `deepseek|riyadh_value|value|N|group|1` [SUM `units`; SY §0]. Toplam gerçek maliyet **0,545648 USD** (< 1 USD) [SUM `total_cost_usd`]. §8.2 durdurma kurallarından yalnızca madde 2'deki `RunAborted` bir kez (segment 1) oluştu; diğerleri tetiklenmedi (N3).

## N1. Segmentler ve kesintiler

| segment | başlangıç | stop_reason | süre (sn) | yanıt | gerçek maliyet (USD) | tamamlanan birim |
|---|---|---|---|---|---|---|
| 0 | 21:29:48 | `null` (dışarıdan kesildi) | 47,1 | 227 | 0,026592 | 4 |
| 1 | 21:55:26 | `run_aborted` ("Connection error"; 213 çağrı kaydının 90'ı yanıtsız) | 58,0 | 123 | 0,015243 | 2 |
| 2 | 21:57:51 | `interrupted` (görev oturumu sonu) | 1246,4 | 1379 | 0,500109 | 64 |
| 3 | 22:23:06 | `interrupted` | 2549,0 | 4 | 0,003704 | 0 |
| **toplam** | | | 3900,5 | 1733 | **0,545648** | **70** |

- Kaynak: başlangıç saatleri, yanıt sayıları (seg0–2) ve tamamlanan birimler SY §2–§3; stop_reason, süre, maliyet ve segment 3 yanıt sayısı SUM `segments`. Toplam süre ve toplam maliyet bu not için segment değerlerinden toplandı; toplam maliyet SUM `total_cost_usd` (0,5456476136) ile aynı, toplam yanıt (1733) SUM model başına `n_responses` toplamıyla (544 + 598 + 591) aynı.
- **Segment 3:** son yanıt SY'ye göre 22:24:51'de geldi; sonrasında süreç yanıt ya da hata kaydı üretmeden çalışmaya devam etti, 2549 sn sonra (hesap: ~23:05) `interrupted` ile kapandı. Bu segmentte hiçbir birim tamamlanmadı, sonuç dosyasına satır yazılmadı (SUM `n_rows` = 0). Takılmanın nedeni doğrulanmadı [SY §0].
- **Segment 4 yok:** bu not yazılırken başka bir sürdürme segmenti başlatılmamıştır.

**SY (22:59) ile SUM (segment 3 sonu) arasındaki fark.** SY, segment 3 sürerken alınmış bir ara durumdur; SUM sonraki son haldir. Fark yalnızca 22:59'dan sonra gelen 1 DeepSeek yanıtından kaynaklanır:

| ölçü | SY (22:59) | SUM (son) |
|---|---|---|
| segment 3 yanıt | 3 | 4 |
| segment 3 maliyet (USD) | 0,003594 | 0,003704 |
| DeepSeek `n_responses` / maliyet (USD) | 543 / 0,426495 | 544 / 0,426605 |
| toplam gerçek maliyet (USD) | 0,545538 | 0,545648 |
| `raw_calls.jsonl` satır | 1849 | 1857 |
| sonuç dosyası (`pilot_v2_20261005.jsonl`) satır | 1692 | 1692 |
| n_complete / n_remaining | 70 / 2 | 70 / 2 |

- Satır sayıları SUM `files` alanından; bu not için dosyalar yeniden sayıldı ve aynı çıktı (1692 ve 1857). `raw_calls.jsonl`'daki +8 satırın içeriği bu notta ayrıştırılmadı.

## N2. Sürdürme kuralı (`--resume`)

- **Run adı ve seed namespace değişmedi:** `pilot_v2_20261005`, `pgg-pilot-v2` [SUM `run`, `seed_namespace`]. Her segment aynı dizine (`runs/pilot_v2_20261005/`) yeni segment olarak yazar [KOD].
- **Birim düzeyinde atlama:** birim = bir grup oyunu ya da bir izole çizelge (ör. `gpt|boston_value|value|N|group|0`). Tamamlanmış birimler yeniden koşulmaz [KOD].
- **Yarım birimler baştan koşulur:** aynı seed'ler ve aynı oturum kimlikleriyle, birimin başından [KOD].
- **Append-only:** sonuç dosyası yalnızca ekleme için açılır, önceki baytlar değişmez; eski satırlar dosyada kalır [KOD]. Sonuç dosyası 1692 satırda sabit kaldı, ham loga yalnızca ekleme yapıldı [SY §8].
- **superseded_units geçersizdir.** SUM'daki kural aynen: `"a row counts only if its (unit, segment) holds the complete unit; rows without a segment are segment 0"`. Superseded birimler (6 birim, 152 satır):

| birim | segment | satır |
|---|---|---|
| gpt\|boston_minimal\|minimal\|N\|group\|0 | 0 | 28 |
| gemini\|riyadh_value\|value\|N\|group\|0 | 0 | 24 |
| gpt\|boston_factual\|factual\|N\|group\|0 | 1 | 28 |
| gemini\|boston_value\|value\|N\|group\|0 | 1 | 8 |
| deepseek\|riyadh_minimal\|minimal\|N\|group\|1 | 2 | 28 |
| deepseek\|riyadh_value\|value\|N\|group\|1 | 2 | 36 |

  Geçerli satır: 1692 − 152 = **1540** (deepseek 460, gpt 540, gemini 540) [SY §4, §7]; tamamlanınca beklenen 1620.
- **Bütçe segmentler arası birikir:** 1 USD tavanı ve %5 geçersiz tavanı önceki segmentlerin maliyet ve sayımlarıyla devam eder [KOD]; SUM'da `total_cost_usd` (birikmiş) ve `segment_cost_usd` ayrı tutulur.

## N3. Prereg §8.2 durdurma kuralları (A2.3 ile)

| kural | durum (SUM son hali) |
|---|---|
| 1. 1,00 USD sert tavan | Tetiklenmedi. Birikmiş 0,545648 USD; kalan 0,454352 USD. |
| 2. %5 geçersiz tavanı (model başına sınır 27; `n_invalid` + `n_parse_fail`) | Tetiklenmedi. Üç modelde de `n_invalid` = 0, `n_parse_fail` = 0. Sağlayıcı hataları tavana sayılmaz: gemini 17, gpt 1, deepseek 0 (toplam 18), hepsi yeniden istendi. |
| 2. `RunAborted` | **Bir kez oluştu:** segment 1, "Connection error", 90 yanıtsız deneme (deepseek 55, gpt 15, gemini 20) [#43; SY §3–§4]. `--resume` ile sürdürüldü (#43). Segment 0, 2 ve 3'te yok. |
| 3. `length` (kesilme; `max_tokens` = 16000) | Tetiklenmedi. `n_length` = 0 (üç model, tüm segmentler). |
| 4. `reasoning_effort` gönderildi mi | Hayır. Üç modelde `default`. |
| 5. `model_snapshot` / sağlayıcı farkı | Tetiklenmedi. Sağlayıcı adları: DeepInfra 544/544, OpenAI 598/598, Google 591/591; `n_provider_unknown` = 0; `stopped_models` boş. `model_snapshot` tüm yanıtlarda istenenle aynı [SY §4, 22:59 itibarıyla]. |
| 6. Sürekli API/sağlayıcı hatası | Tetiklenmedi. Segment 3'te 22:24:51'den sonra yanıt ya da hata kaydı olmadan geçen süre bu kural kapsamında bir durdurma üretmedi (N1). |
| Yeni koşul: `runs_dir` geçerli | Geçerli. |

## N4. Maliyet ve tamamlanma

- **Toplam gerçek maliyet: 0,545648 USD** (deepseek 0,426605; gpt 0,068090; gemini 0,050952) [SUM `per_model`]. 1 USD tavanının altında.
- **Tamamlanma: tamamlanmadı (70/72 birim).** Eksik iki birim DeepSeek Riyadh grup birimleridir (N2 tablosunun son iki satırı); #44 dry-run'ına göre kalan tahmin 80 DeepSeek çağrısı, ~0,028 USD [SY §1].
- Pilotun tamamlanması için yeni bir `--resume` segmenti gerekir (önce `--resume --dry-run`). Bu not o segmenti kapsamaz.

---

# Kapanış eki — pilot_v2_20261005 son durumu (2026-10-05)

Bu ek yukarıdaki metni (Amendment ve "Not — … teknik kesintiler ve sürdürme" dahil) değiştirmez; notun "tamamlanmadı" durumunu kapatır. Yalnızca tesisat ve sayılar içerir, bilimsel yorum yoktur. Ek yazılırken kod çalıştırılmadı, API çağrısı yapılmadı, depoya yazılmadı. Kaynaklar: **SY2** = `pilot_v2_sayilar.md` §10–§18 (#47; 23:47 durumu); **SUM4** = `runs/pilot_v2_20261005/pilot_v2_20261005_summary.json` (segment 4 sonrası son hali); **KOD2** = `_kod_d9aa70f/` (README "Hangs" maddesi, `llm_client.py`); **#47** = görev sonucu.

**Durum: pilot v2 tamamlandı.** 72/72 birim; geçerli satır **1620** (deepseek 540, gpt 540, gemini 540); toplam gerçek maliyet **0,636407 USD** (< 1 USD) [SUM4; SY2 §10]. §8.2 kurallarından yalnızca `RunAborted` bir kez (segment 1) oluştu; diğerleri ve yeni bekçi tetiklenmedi (K5).

## K1. Segment 3'ün takılması ve kapanışı

- Segment 3 22:23:06'da başladı, 4 DeepSeek yanıtı aldı; son yanıt 22:24:51'de geldi. Sonrasında yanıt ya da hata kaydı üretmeden çalıştı ve 2549,0 sn sonra `interrupted` ile kapandı: 0 birim, 0 satır, 0,003704 USD [SUM4 `segments`; N1].
- #47 başında `kill -0 92369` "no such process" döndü; süreç çalışmıyordu [SY2 §11].
- Takılmanın kesin nedeni doğrulanmadı.

## K2. Tesisat değişikliği: istek süre sınırı ve takılma bekçisi (commit d9aa70f, #46)

- **İstek süre sınırı** (`--request-deadline`, varsayılan 300 sn): her HTTP denemesine toplam (duvar saati) süre sınırı. 300 sn'lik istemci zaman aşımı yalnızca tek tek okumaları sınırlar. Süre aşılırsa deneme bırakılır, `error_kind` "transport" / `error_subkind` "deadline" olarak loglanır ve yeniden istenir. Süreden sonra gelen yanıt `late_response` olayı olarak loglanır, karar olarak kullanılmaz [KOD2].
- **Takılma bekçisi** (`--stall-timeout`, varsayılan 900 sn): ham loga bu süre boyunca hiç kayıt düşmezse koşu `stop_reason` "stalled" ile durur ve `--resume` ile sürdürülebilir [KOD2].
- Segment 4'teki değerler: `request_timeout_s` 300, `request_deadline_s` 300, `stall_timeout_s` 900 [SUM4].
- **Bu bir tesisat değişikliğidir; istemi, modeli, parametreleri ve kartları değiştirmez.** Dayanaklar:
  - KOD2'ye göre iki ayar operasyoneldir, `--resume`'da karşılaştırılmaz; her segmentin summary girdisi bunları ve kod sürümünü kaydeder.
  - `configs/pilot.json` sha256 `c123738c…`, 58ae381 kopyasıyla aynı; `diff` farkı yok [SY2 §11].
  - Kartlar: SUM4'teki 6 kartın `text_sha256` değerleri segment 1, 2 ve 3 summary yedeklerindekiyle aynı. `cards/pilot_cards_v2.json` iki kod kopyasında satır satır aynı (bu ek için okunarak karşılaştırıldı).
  - İstem: `pgg_game.py`'de istemi kuran metin satırları (desen aramasıyla 42 satır) iki kopyada aynı ve aynı sırada. Tam dosya `diff`'i yapılmadı.
  - SUM4: `max_tokens` 16000, `reasoning_effort` üç modelde `default`, `budget_usd` 1,0, `invalid_rate_cap` 0,05.
- #46'nın görev sonuç metni bu eke doğrudan kaynak olarak ulaşmadı; değişikliğin tanımı KOD2'den ve #47'den alındı.

## K3. Segmentler farklı kod commit'leriyle koşuldu

| segment | kod | kaynak |
|---|---|---|
| 0 | bu ekin kaynaklarında kayıtlı değil | — |
| 1–2 | 58ae381 (`_kod_58ae381/`) | `rapor_gorev43_pilot_v2_resume.md` |
| 3 | 58ae381 (`_kod_58ae381/`) | SY başlığı (#44) |
| 4 | d9aa70f (`_kod_d9aa70f/`) | #47; SUM4 `code_version.files_sha256` |

- Segment 0–3'ün summary girdilerinde `code_version` alanı yok. Segment 4'te var, ancak `git_commit` `null`: arşiv kopyasında `.git` yok, commit bilgisi elle kaydedildi [SY2 §11]. Segment 4 dosya özetleri: `pgg_game.py` bc6f5a60…, `llm_client.py` ac8b7e66…, `pgg_cost.py` b79c6809….

## K4. Segment 4 ve son sayılar

| segment | zaman | stop_reason | süre (sn) | yanıt | maliyet (USD) | satır | tamamlanan birim |
|---|---|---|---|---|---|---|---|
| 4 | 23:33:21–23:46:52 | `null` (normal bitiş; çıkış kodu 0) | 809,3 | 80 | 0,090760 | 80 | 2 |

- Tek `--resume` yetti. Segment 4 maliyeti, dry-run tahmininin (0,0280 USD) yaklaşık 3,2 katı [SY2 §13].

| ölçü | son değer |
|---|---|
| tamamlanan birim | **72/72** (segment 0–4: 4 + 2 + 64 + 0 + 2) |
| geçerli satır | **1620** (540 / 540 / 540). Sonuç dosyasında 1772 satır var; 152'si superseded (N2 tablosundaki 6 birim) ve geçersiz sayılır. |
| yanıt | 1813 (deepseek 624, gpt 598, gemini 591) |
| toplam süre (segment toplamı) | 4709,8 sn |
| toplam gerçek maliyet | **0,636407 USD** (deepseek 0,517364; gpt 0,068090; gemini 0,050952); tavanın %63,6'sı |
| ham log ile summary maliyeti | eşleşiyor [SY2 §18] |

- Bu ek için bağımsız kontrol:
  - maliyet: 0,0265920152 + 0,0152433264 + 0,5001085608 + 0,0037037112 + 0,090759648 = 0,6364072616;
  - yanıt: 227 + 123 + 1379 + 4 + 80 = 1813 = 624 + 598 + 591;
  - satır: 212 + 116 + 1364 + 0 + 80 = 1772, 1772 − 152 = 1620;
  - süre: 3900,5 + 809,3 = 4709,8.
- Dosyalar (`runs/pilot_v2_20261005/`, `wc -l`, 23:47) [SY2 §18]: `pilot_v2_20261005.jsonl` 1772; `raw_calls.jsonl` 1939; `pilot_v2_20261005_summary.json` 705; `summary.seg3.json` 625. Dosyalara yalnızca ekleme yapıldı (önek sha256 ile doğrulandı). `raw_calls.jsonl` commit'e girmez.

## K5. §8.2 durdurma kuralları (A2.3 ile): son durum

| kural | durum (SUM4) |
|---|---|
| 1. 1,00 USD sert tavan | Tetiklenmedi. Birikmiş 0,636407 USD; kalan 0,363593 USD. |
| 2. %5 geçersiz tavanı (model başına 27) | Tetiklenmedi. Üç modelde `n_invalid` = 0, `n_parse_fail` = 0. Sağlayıcı hatası 18 (gemini 17, gpt 1); tavana sayılmaz, hepsi yeniden istendi. |
| 2. `RunAborted` | Bir kez oluştu (segment 1; N3). Segment 4'te yok. |
| 3. `length` | Tetiklenmedi. `n_length` = 0. En yüksek reasoning token 12035 < 16000 [SY2 §16]. |
| 4. `reasoning_effort` | Gönderilmedi (`default`). |
| 5. `model_snapshot` / sağlayıcı farkı | Tetiklenmedi. DeepInfra 624, OpenAI 598, Google 591; `n_provider_unknown` = 0; `stopped_models` boş. |
| 6. Sürekli API/sağlayıcı hatası | Tetiklenmedi. Segment 4'te hata kaydı yok [SY2 §13]. |
| `runs_dir` geçerli | Geçerli. |
| Yeni: istek süre sınırı (yalnız segment 4'te etkin) | Tetiklenmedi. `error_subkind` "deadline" 0, `late_response` 0 [SY2 §15]. |
| Yeni: takılma bekçisi (yalnız segment 4'te etkin) | Tetiklenmedi. `stalled` = false [SUM4]. |

## K6. Bu ekin kapsamadığı

- §9 muhakeme okuması ve §8.3 kararı ayrı görevlerdir.
- Segment 3'ün takılma nedeni doğrulanmadı.
