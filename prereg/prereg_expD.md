ONAYLANDI — 2026-10-20 (kullanıcı; 64 kişi, Mistral yok)

> Bu belge onaylanmadan hiçbir ücretli çağrı yapılmaz. Ücretli aşama (D2) kullanıcı "BAŞLA D2" deyince başlar. **Bu, çalışmanın son deneyidir;** sonucu ne olursa olsun ardından makale tamamlanır ve yayımlanır.

# Deney D ön kaydı (prereg_expD): "Kaç kişi 0 verdi" bilgisini içeren düzeltilmiş kural, hiç denenmemiş bir grup büyüklüğünü önceden tahmin edebilir mi?

- **Tarih:** 2026-10-20. Veriden önce yazıldı.
- **Yazan:** Claude, kullanıcının isteğiyle ("D'yi de planla … hata yapmayalım … yavaş yavaş bitirelim"). İç yazılı plandır.
- **İlişkisi:** Deney C (`prereg_expC.md`). Dondurulmuş kural R3, GPT'de büyük grupları öngöremedi (F-C.7). Keşifsel tanıya göre (F-C.9) ajanlar "biri 0 verdi mi"ye değil, kaç kişinin ya da ötekilerin ne kadarının 0 verdiğine tepki veriyor. Bu deney o açıklamayı ileriye dönük sınar.

## 0. Sonuç (önce bu)

1. **Soru:** 0 verenlerin **sayısını ya da payını** da gören düzeltilmiş kural (R4), mevcut verilerden öğrenilip dondurulduğunda, hiç oynanmamış bir grup büyüklüğünü tahmin edebilir mi? Eski kuraldan (R3) daha iyi mi?
2. **Karar kapısı (D0, ücretsiz):** önce mevcut veride "bir büyüklüğü dışarıda bırak" sınaması yapılır. R4, R3'ten belirgin daha iyi değilse **D koşulmaz** ve doğrudan makaleye geçilir.
3. **Tasarım (önerilen):** yalnız GPT, **64 kişilik** gruplar, 48 grup (kart başına 12), 4 minimal kart, 10 tur. Ana deneyle aynı istem; yalnız oyuncu sayısı değişir.
   - Neden GPT: kuralın başarısız olduğu model bu.
   - Neden 64: tahmin edilen sistem, eğitimdeki en büyük gruptan (32) **büyük** olsun; yani gerçek bir dışdeğerleme.
4. **Maliyet (kaba; kesin değer D0 dry-run'ından):** ≈ 12–16 USD, birkaç saat. Daha ucuz seçenek: 24 kişi, ≈ 3 USD (§9).
5. **Duman koşusu yok.** Gerekçe: istem şablonu 8 / 16 / 32 kişide sınandı (C1, C2); yalnız q1 listesi uzar. Yerine **erken kontrol** yapılır: ana koşunun ilk ~4 grubu bitince tesisat okunur; sorun varsa koşu durdurulur.

## 1. Kurallar

- **Durum öğeleri:**
  - kendi önceki katkı dilimi (0, 1–9, 10, 11–19, 20);
  - ötekilerin ortalaması dilimi (0, (0, 5), [5, 10), 10, (10, 15), [15, 20]);
  - "ötekilerden biri 0 verdi";
  - kalan tur dilimi (≥ 2, sondan bir önceki, son).
- **R3-donmuş:** Deney B / C'nin dondurulmuş kuralı (sha256 `62b2bae7…d93d1`); yalnız 4 kişilik verilerden.
- **R3-tümü:** R3 ile aynı durum tanımı, **bütün mevcut verilerden** öğrenilir. Kontrol kuralıdır: iyileşme "daha çok veri"den mi, "yeni bilgi"den mi, onu ayırır.
- **R4-sayı:** R3 durumu + ötekiler arasında 0 verenlerin **sayısı** (0, 1, 2, 3+).
- **R4-pay:** R3 durumu + ötekiler arasında 0 verenlerin **payı** (0, (0, 0,2], (0,2, 0,4], > 0,4).
- **Eğitim verisi** (bütün R3-tümü / R4 kuralları için, model × kart hücresi ve model havuzu, F.14 geri çekilmesi):
  - Aşama 1 ve Deney A B kolu, 4 minimal kart, 4 kişi;
  - Deney C, n = 4 / 8 / 16 / 32.
- **R4 geri çekilme sırası:** tam durum → kalan tur dilimi düşer → 0 sayısı / payı düşer (R3 durumu) → R3'ün kendi sırası.

## 2. D0 — dışarıda bırakılan büyüklükle seçim ve karar kapısı (ücretsiz, mevcut veri)

- **Dışarıda bırakılan büyüklükler:** GPT için 8, 16, 32; Mistral için 8, 16. Her biri sırayla dışarıda bırakılır; kurallar kalan veriden öğrenilir. Dışarıdaki büyüklüğün grupları gözlenen 1. turlarından simüle edilir (S = 500).
- **Ölçüler:**
  - 8. turda çöküş payı hatası |gözlenen − tahmin|;
  - yörünge RMSE (tur 2–10).
- **Seçim:** R4-sayı ile R4-pay'dan, (model, dışarıdaki büyüklük) çiftleri üzerinden ortalama |çöküş hatası| daha küçük olan seçilir. Fark < 0,01 ise RMSE'ye bakılır. Seçilen kurala "R4" denir.
- **Karar kapısı:** R4'ün ortalama |çöküş hatası|, R3-tümü'nünkinden **en az 0,05 küçük** olmalı; ayrıca GPT'nin üç dışarıdaki büyüklüğünün en az ikisinde R3-tümü'nden küçük olmalı. Değilse D koşulmaz; sonuç "yeni bilgi büyüklüğe aktarımı düzeltmedi" diye raporlanır ve makaleye geçilir.
- **Kapı geçilirse dondurulacaklar:**
  - R4 ve R3-tümü bütün mevcut veriden öğrenilir ve dosyaya yazılır (`data/expD/rules_v1.json`, sha256);
  - 64 kişi için koşulsuz tahmin dondurulur (`data/expD/forecast_v1.json`, sha256). 1. tur, hücrenin Deney C'deki bütün 1. tur kararlarından ajan ajan çekilir.
  - Plan ve tahmin D2'den önce Zenodo'ya yeni sürüm olarak yüklenir (kullanıcı).

## 3. D2 — ana koşu

- **Çerçeve:** `abstract_v4_n64`. `abstract_v4` ile aynı; yalnız q1 örneği 63 ötekini listeler (C'deki desen kuralı). Karar istemlerinin `abstract_v4` ile bayt bayt aynı olduğu test edilir.
- **Gruplar:** 4 minimal kart × 12 grup = 48 grup; GPT (openai, sürüm `-20260922` beklenir).
- **Değişmeyenler:** istek ayarları, durdurma / sürdürme kuralları ve izleyici, C2 ile aynı.

## 4. Hipotezler (GPT, n = 64; tahminler gözlenen 1. turdan koşullu)

- **D-H1 — düzeltilmiş kural yeni büyüklüğü tahmin ediyor mu (birincil):**
  - (a) 8. turda çöküş payı, gözlenen − R4. Etiket ±0,15 bandı: "yeniden üretiyor" / "sapıyor (gerçek daha yüksek / düşük)" / "belirsiz".
  - (b) ortalama katkı tur 2–10, gözlenen − R4. Etiket ±2 bandı (B-H1 kuralı): "tahmin tuttu" / "sapıyor" / "belirsiz".
- **D-H2 — R4, R3-tümü'nden daha mı iyi (birincil):**
  - Ölçü: çöküş payında E = |gözlenen − R3-tümü| − |gözlenen − R4|; grup bootstrap CI, kart içinde tabakalı.
  - Etiketler: CI > 0 → "R4 daha iyi"; CI < 0 → "R3-tümü daha iyi"; diğer → "ayırt edilemedi".
- **İkincil (etiketsiz):** aynı karşılaştırma ortalama katkı için; R3-donmuş ve R0 da raporlanır.
- **Mekanizma (betimsel):** F-C.9 T2 ve T3 ölçüleri n = 64'te.
- **Okuma:**
  - D-H1(a) "yeniden üretiyor" ve D-H2 "R4 daha iyi" → keşifsel açıklama ileriye dönük doğrulandı.
  - D-H2 "ayırt edilemedi" ya da R4 sapıyor → açıklama yetmedi.

  İki sonuç da raporlanır.
- **Güç:** 48 grupla çöküş payının CI yarı genişliği ≈ 0,13 (C2 GPT'ye göre); D0'da sentetik veriyle yeniden hesaplanır.

## 5. Analiz ve kod

- **Betik:** `pgg_analysis_expD.py`; alt komutlar:
  - `select`: D0, dışarıda bırakılan büyüklükle seçim ve karar kapısı;
  - `freeze`: kuralların ve koşulsuz tahminin dondurulması;
  - `analyse`: eksik koşuyu ve sha256'sı farklı dosyayı reddeder.
- **Testler** (sentetik dünyalar, cevabı bilinen):
  - sayıya tepki veren dünyada R4-sayı'nın R3'ü yenmesi;
  - R4 durumunun n = 4'te R3'e indirgenmesi;
  - 64 kişilik istemin yalnız q1'de farklı olması;
  - etiketler.
- API çağrısı yok.

## 6. Aşamalar

| aşama | ne | maliyet |
|---|---|---|
| D0 | seçim ve karar kapısı; kod, testler, çerçeve, config, dry-run, dondurma, Zenodo paketi | ücretsiz |
| D2 | ana koşu (kapı geçilirse ve kullanıcı "BAŞLA D2" derse); ilk ~4 grupta erken tesisat kontrolü | ≈ 12–16 USD |
| Analiz | `analyse` bir kez; sonuç ve keşifsel okuma | ücretsiz |

## 7. Sınırlılıklar

- **Tek model (GPT).** Mistral'da R4 yalnız D0'daki dışarıda bırakma sınamasıyla değerlendirilir; ileriye dönük test edilmez.
- **R4'ün yeni öğesi C verisi görüldükten sonra seçildi** (F-C.9). D, bu keşifsel açıklamanın ilk ileriye dönük testidir.
- **64 kişide istem uzun:** geçmiş satırında 64 sayı ve q1'de 63 sayı var. Büyüklük ile istem uzunluğu ayrılamaz (C'deki gibi).
- **Sabit MPCR 0,4:** grubun toplam getirisi n ile büyür (64 kişide 25,6).

## 8. Bitiş planı (kullanıcının isteğiyle)

- D0 → (kapı) → D2 → analiz → makale (taslak 5: Çalışma 4 sonuçları, tanı, Deney D) → son kontrol (sayılar ve kaynaklar) → Zenodo'da açık yayın (makale, veri, kod, kırpılmış ham kayıtlar).
- **Bu plan kapsamında yeni bir deney eklenmez.** Yeni sorular makalede "gelecek çalışma" olarak yazılır.

## 9. Kullanıcı kararları

1. **Grup büyüklüğü:**
   - (a) önerilen: 64 kişi, ≈ 12–16 USD, gerçek dışdeğerleme;
   - (b) 24 kişi, ≈ 3 USD, ama 16 ile 32 arasında kalır (iç değerleme).
2. **Mistral'ı D2'ye eklemek:** önerilen hayır. 12 kişide 24 grup ≈ 22 USD; ±0,15 bandına yetmez; çalışmayı uzatır.
3. **Onay:** onaylanırsa D0'a geçilir (ücretsiz). D2 için ayrıca "BAŞLA D2".

**Kayıt (2026-10-20, kullanıcı):** "onaylıyorum, 64, Mistral yok, D0'a geç". Seçenek (a) 64 kişi; Mistral D2'ye eklenmez.

## Değişiklik günlüğü

- 2026-10-20: ilk taslak (veriden önce).
- 2026-10-20: onay (kullanıcı); metin değişmedi, yalnız üst satır ve §9 kaydı.

## Ek F-D.1 — Bir test tanımının düzeltilmesi (2026-10-20, kod yazılmadan önce)

- **Yanlış olan:** §5'teki "R4 durumunun n = 4'te R3'e indirgenmesi" testi yanlış tanımlanmış. 4 kişide de 0 sayısı 0–3 değerini alır; R4-sayı, 2 ya da 3 kişinin 0 verdiği durumları R3'ten ayırır. Yani R4, 4 kişide de R3'e indirgenmez.
- **Doğru test:** R4'ün yeni öğesi "biri 0 verdi" göstergesiyle tutarlıdır: 0 sayısı (ya da payı) > 0 ⇔ gösterge 1. Geri çekilmede yeni öğe düşünce durum R3 durumunun aynısı olur.

## Ek F-D.2 — D0 sonucu: karar kapısı geçilmedi, D2 koşulmaz (2026-10-20)

- **Kod ve dosya:** kod `f429709`; 628 test geçti. Sentetik "sayıya tepki veren dünya"da R4-sayı, R3'ü yeniyor. `results/expD_select.json`, sha256 `053d1566487d66d861465554deee82c1ea9233535497824215bd9a9118028318` (S = 500).
- **Dışarıda bırakılan büyüklük:** 8. turda çöküş payı hatası |gözlenen − tahmin|; parantez içinde yörünge RMSE.

  | model, dışarıdaki n | gözlenen | R3-donmuş | R3-tümü | R4-sayı | R4-pay |
  |---|---|---|---|---|---|
  | GPT 8 | 0,562 | 0,346 (2,14) | 0,179 (1,47) | 0,140 (1,26) | 0,179 (1,26) |
  | GPT 16 | 0,479 | 0,345 (1,56) | **0,095** (0,33) | 0,216 (1,80) | 0,137 (1,23) |
  | GPT 32 | 0,688 | 0,524 (2,19) | 0,390 (0,96) | **0,112** (1,12) | 0,142 (0,85) |
  | Mistral 8 | 0,208 | 0,401 (2,52) | 0,314 (1,96) | 0,275 (1,70) | 0,295 (1,76) |
  | Mistral 16 | 0,792 | 0,057 (1,68) | 0,031 (1,32) | 0,039 (1,42) | 0,023 (0,89) |

- **Seçim (§2):** ortalama |hata| R4-sayı 0,156, R4-pay 0,155; fark < 0,01. Bu yüzden RMSE'ye bakıldı (1,46 ve 1,20) ve **R4-pay** seçildi.
- **Karar kapısı:**
  - R4-pay'in ortalama |hatası| 0,155, R3-tümü'nünki 0,202. İyileşme **0,047**; gereken **0,05**. İlk koşul **sağlanmadı** (0,003 farkla).
  - GPT'de üç büyüklüğün ikisinde R3-tümü'nden iyi; ikinci koşul sağlandı.
  - Kapı iki koşulu birlikte istiyor; **kapı geçilmedi.** Plan gereği dondurma ve D2 yok. 64 kişilik çerçeve ve config depoda kalır, kullanılmaz.
- **Dürüstlük notu:** fark eşiğin çok yakınında. Eşik veriden önce yazıldı ve değiştirilmez. "Neredeyse geçti" gerekçesiyle D koşulmaz.
- **Okuma (keşifsel, betimsel):**
  1. **Asıl iyileşme yeni bilgiden değil, karışık büyüklükteki veriden.** Kuralı yalnız 4 kişilik verilerden değil, farklı büyüklüklerden öğrenmek, saklanan büyüklüğün hatasını GPT'de yaklaşık yarıya indiriyor: ortalama 0,405 → 0,221.
  2. **"0 veren sayısı / payı" bilgisi** en büyük grubun (32) dışdeğerlemesinde belirgin yardım ediyor (0,390 → 0,112 / 0,142). Ara büyüklüklerde ediyor ya da etmiyor; 16 kişide kötüleştiriyor. F-C.9 açıklaması yalnız kısmen destekleniyor.
  3. **Mistral 8 kişilik gruplar** hiçbir kuralla iyi tahmin edilmiyor (en iyi hata 0,275). F-C.7'deki aykırılık sürüyor.
- **Sonuç:** Deney D burada biter. Bitiş planına (§8) göre sıradaki adım makale.

## Ek F-D.3 — Yuvarlama düzeltmesi (2026-10-20)

- F-D.2 tablosunda GPT 8: gözlenen tam 27/48 = 0,5625 → **0,563** (0,562 yazılmıştı); R3-tümü'nün hatası tam 0,1795 → **0,180** (0,179 yazılmıştı). Ortalamalar ve karar kapısı etkilenmez.
