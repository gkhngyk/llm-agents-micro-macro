# Dinamik analizler (prereg_dyn): tuzaklar, devrilme noktası, yol bağımlılığı

- **Tarih:** 2026-10-19. **Hesaplanmadan önce yazıldı** ve hesaplamadan önce commit edildi.
- **Yazan:** Claude, kullanıcının isteğiyle ("complexity science'a katkı yapmalıyız, başla, dinamik analizleri yap"). İç yazılı plandır, kamuya açık bir kayıt değildir.
- **Durum:** **keşifsel.** Önceden kayıtlı hiçbir etiketi (prereg_main, prereg_expA, prereg_expB) değiştirmez. Ücretli çağrı yok; yalnız mevcut veriler.

## 0. Sonuç (önce bu)

1. **Soru (karmaşıklık bilimi):** oyunun içinden öğrenilen mikro kural (R3) grup düzeyinde hangi makro yapıyı üretiyor? (a) Emici ya da yapışkan durumlar (çöküş tuzağı, işbirliği kilidi) var mı? (b) Kaç bedavacı bir grubu çöküşe devirir (devrilme noktası)? (c) Aynı başlangıçtan farklı sonlara gidiliyor mu (yol bağımlılığı, iki uçlu sonlar)?
2. **Karşılaştırmalar:** aynı soruları (i) izole cevaplardan kurulan kural R0, (ii) gözlenen LLM grupları (örneklem içi ve örneklem dışı), (iii) aynı oyunu oynayan insan grupları (Herrmann, Thöni & Gächter, 2008) için cevaplıyoruz.
3. **Neden önemli:** R3'ün ortalama yörüngeleri tuttuğunu biliyoruz (F.14, prereg_expB F-B.3). Bu plan, kuralın ortalamanın ötesinde **makro yapıyı** da (çekiciler, eşikler, dağılımın şekli) doğru üretip üretmediğini ve izole kuralın bu yapıyı nitel olarak yanlış öngörüp öngörmediğini sınar.

## 1. Yazıldığında görülmüş olanlar (dürüstlük kaydı)

- **Görüldü:** Aşama 1, Deney A ve Deney B'nin bütün önceden kayıtlı sonuçları; hücre ortalama yörüngeleri; H4, F.12, F.14; B-H1–B-H3. F.13'teki betimsel sayımlar: katkıların %96'sı tam 0, 10 ya da 20; ötekilerden biri 0 verdiyse ajanın 0 verme oranı (DeepSeek %75, Mistral %64, GPT %25; kimse 0 vermediyse %4 / %4 / %1). İnsan verisinin dönem ortalamaları (N deneyi, havuz: 10,82 → 4,41) ve şehir ortalamaları.
- **Görülmedi:** bu plandaki ölçülerin hiçbiri. Uç durumların payları, kalıcılık olasılıkları, devrilme eşikleri, yaşam süreleri ve son durum dağılımları görülmedi; insan verisinin grup düzeyindeki dinamikleri de görülmedi.

## 2. Veri

| ad | kaynak | grup | tur | kart | rolü |
|---|---|---|---|---|---|
| S1 | Aşama 1, `main_s1_20261014` | 504 | 10 | 12 | kuralın öğrenildiği veri → **örneklem içi** (uyum, doğrulama değil) |
| AB | Deney A, B kolu (`abstract_v4`), `expA_main_20261017` | 128 | 10 | 4 minimal | **örneklem dışı** (aynı istem, yeni koşu) |
| EB | Deney B, `expB_main_20261018` | 176 | 15 | 4 minimal + 4 değer | **örneklem dışı**, orta oyun 12 tur (eğitimde 7) |
| H | Herrmann, Thöni & Gächter (2008), N deneyi, yalnız N'nin önce oynandığı oturumlar (`secseq` 0) | 230 | 10 | 16 şehir, havuz | **insan referansı**, betimsel |

H aynı oyundur: 4 kişilik sabit gruplar, 20 jeton, MPCR 0,4, 10 dönem, ceza yok. Veri `data/herrmann2008/raw/HerrmannThoeniGaechterDATA.csv` (CC0, sha256 `data/herrmann2008/SHA256SUMS`); her (oturum, grup) bir grup.

## 3. Kurallar

- **LLM, R3:** dondurulmuş tablolar `data/expB/frozen_rules_v1.json` (sha256 `62b2bae7bcf6560f022181ff5b0813fec4747f2b8e3e13e5dd1301931fbd93d1`), değişmeden; yükleme sha256 kontrolüyle.
- **Orta oyun kuralı:** bütün dinamik simülasyonlarda tur dilimi 0 (eğitimde tur 2–8; EB'de R3-kalan ile tur 2–13). Son tur etkisi bilinçli olarak dışarıda: soru, oyunun sonu yaklaşmadan grubun nereye gittiği.
- **İki düzey:**
  - (a) **Model kuralı:** modelin 12 kartının havuz tablosu (dondurulmuş `model_tables`; hücre tablosu yerine de aynı tablo). **Başlık sonuçları bununla.**
  - (b) **Hücre kuralı:** model × kart, F.14 geri çekilmesiyle. Hücreler arası medyan ve en küçük–en büyük raporlanır; 4 minimal kart ayrıca.
- **R0:** hücrenin izole f'i (`iso_f`, 0/5/10/15/20 noktaları, doğrusal enterpolasyon, belirlenimci). Model düzeyi = 12 hücrenin f ortalaması.
- **İnsan kuralı H-R3:** aynı R3 durum tanımı ve dilimleri, H'nin bütün gruplarından tek havuz tablo (dönem 2–10; dilim 2–8 / 9 / 10). Örneklem içi; yalnız referans.

## 4. Tanımlar

- m_t: 4 ajanın t. turdaki ortalama katkısı.
- **Çöküş bölgesi** m_t ≤ 2,5; **işbirliği bölgesi** m_t ≥ 7,5; arası **ara bölge**. Duyarlılık (yalnız D3a): 1 / 9.
- **Simetrik durumlar:** Z = (0,0,0,0), C10 = (10,10,10,10), C20 = (20,20,20,20), tam değerler.
- **Orta oyun sonu E:** S1, AB ve H için 8; EB için 13.
- **Çöküş anı** τ: m_t ≤ 2,5 olan ilk tur (t ≥ 1). **Hayatta kalma** S(t): τ > t olan grupların payı.

## 5. Analizler

### D1 Tuzaklar ve yaşam süreleri

- **D1a Kalıcılık:** simetrik durum s için kuraldaki "bir tur sonra aynen tekrar" olasılığı p_s = π_s⁴. π_s, ajanın o durumda aynı katkıyı verme olasılığıdır:
  - Z: P(0 | kendi 0, ötekiler 0, biri 0 verdi, dilim 0);
  - C10: P(10 | kendi 10, ötekiler 10, kimse 0 vermedi, 0);
  - C20: P(20 | kendi 20, ötekiler [15, 20], kimse 0 vermedi, 0).
  - Beklenen kalış süresi 1 / (1 − p_s). Olasılığın hangi geri çekilme düzeyinden ve kaç karardan geldiği raporlanır.
  - Gözlenen karşılığı: orta oyun geçişlerinde (t → t+1, t+1 ≤ E) s durumundaki grupların bir sonraki turda s'de kalma payı (S1, AB, EB, H).
- **D1b İşbirliğinin yaşam süresi:** kuralla C10'dan başlayıp orta oyun kuralıyla en çok 100 tur simülasyon (S = 2 000). Ölçü, ilk çöküş anına kadar geçen tur sayısı: medyan, ortalama (100'de kesik) ve kesilen pay. Model kuralları ve hücre kuralları için C10'dan; model kuralları için ayrıca C20'den.
- **D1c Gözlenen hayatta kalma ve geri dönüş:**
  - Her veri kümesinde S(t), t = 1…E: gözlenen değer ile her grubun gözlenen 1. turundan kuralla (hücre kuralı, S = 500) ve R0 ile simüle edilen değer.
  - E'de gözlenen − kural farkı, grup bootstrap CI ile.
  - **Geri dönüş:** τ ≤ E − 1 olan gruplardan sonraki bir turda (≤ E) m ≥ 7,5'e çıkanların payı. Ayrıca çöküş bölgesinden çıkanların (m > 2,5) payı. Gözlenen ve kural simülasyonu.

### D2 Devrilme noktası

- **Başlangıç:** 1. turda k ajan 0, 4 − k ajan 10 verir (k = 0…4). Orta oyun kuralıyla tur 2–13 simüle edilir (12 tur, EB'nin orta oyunu; S = 2 000).
  - Çıktılar: P(çöküş bölgesi), P(işbirliği bölgesi) ve ortalama m; 13. turda ve 8. turda.
- **Devrilme noktası** k*: 13. turda P(çöküş) ≥ 0,5 olan en küçük k. Hiçbir k'de değilse "yok".
- **R0 karşılığı:** aynı başlangıçlardan belirlenimci, k*_R0 aynı tanımla.
  - Ayrıca R0'ın **simetrik sabit noktaları**: x ↦ f(x) için f(x) = x çözümleri (parçalı doğrusal f). Kararlılık ölçütü, kesişimdeki eğimin mutlak değerinin 1'den küçük olması. Kararlı sabit nokta sayısı ve konumları raporlanır (model düzeyi ve hücreler).
- **Gözlenen kontrol:** gruplar 1. turdaki 0 sayısına göre ayrılır (k1 = 0…4). E'de çöküş bölgesinde olanların payı; gözlenen değer ile aynı grupların 1. turundan kural ve R0 öngörüsü. En az 5 gruplu k1 sınıfları raporlanır. H için gözlenen değer ve H-R3.

### D3 İki uçlu sonlar ve yol bağımlılığı

- **D3a Son durum dağılımı:** E'de çöküş / ara / işbirliği payları; gözlenen, kural (gözlenen 1. turdan) ve R0. Model × veri kümesi.
  - Hücre içinde: iki uçta da en az %10 ve en az 2 grup bulunan hücre sayısı ("hücre içi iki uçlu").
- **D3b Aynı başlangıç, farklı son:**
  - 1. turdaki sıralanmış katkı vektörü aynı olan grup kümeleri (veri kümesi × model içinde, en az 8 grup). Her kümede E'de çöküş ve işbirliği payları.
  - Kuralla: her gözlenen grubun 1. turundan P(çöküş, E). 0,2 < P < 0,8 olan grupların payı ("başlangıçta karar verilmemiş" pay).

## 6. İstatistik

- Paylar için %95 CI: grup bootstrap (10 000), kart içinde tabakalı; H'de şehir içinde tabakalı.
- Gözlenen − öngörülen farkları için her grubun öngörülen olasılığı (simülasyondan) sabit alınır; bootstrap gruplar üzerinden.
- Çoklu karşılaştırma düzeltmesi yok (keşifsel, betimsel). Seed `stable_seed("pgg-dyn", …)`.

## 7. Okuma kuralları (önceden yazıldı, betimsel)

1. **Tuzak:** model kuralında p_Z ≥ 0,9 ve örneklem dışı verilerde (AB, EB) çöküşten işbirliği bölgesine geri dönüş payı < %10 → "çöküş emici (tuzak)".
2. **İşbirliği:**
   - model kuralında p_C10 ≥ 0,8 ve D1b medyan yaşam süresi ≥ 12 tur → "yarı kararlı işbirliği (kilitlenme)";
   - medyan < 4 tur → "kırılgan işbirliği";
   - arası "orta".
3. **İki çekici (bistability):** 1 ve 2'deki kural koşulları (p_Z ≥ 0,9 ve p_C10 ≥ 0,8) birlikte sağlanır; ayrıca AB'de ve EB'de ayrı ayrı gözlenen D3a'da ara bölge payı < %20 ve iki uçta en az %10 bulunur.
4. **Devrilme:** k* = 1 → "tek bedavacı grubu deviriyor"; k* = 2 → "iki bedavacı"; vb.
5. **R0 ile nitel uyum:** iki koşul birlikte sağlanmalıdır:
   - R0'ın kararlı sabit nokta sayısı, kuralın yapışkan simetrik durum sayısına (p ≥ 0,8 olan Z / C10 / C20) eşittir;
   - k*_R0 = k*.

   Sağlanmazsa: "izole kural makro yapıyı nitel olarak yanlış öngörüyor".
6. **Örneklem dışı uyum (AB, EB):** D2'nin k1 sınıflarında, D3a paylarında ve S(E)'de:
   - |gözlenen − kural| ≤ 0,15 ve CI ±0,15 içinde → "kural makro yapıyı yeniden üretiyor";
   - CI tamamen ±0,15 dışında → "sapıyor";
   - diğer durumlar → "belirsiz".
7. **İnsan:** yalnız betimsel karşılaştırma (aynı ölçüler); eşik yok. İnsan–LLM farkı nedensel yorumlanmaz.

## 8. Bilinen sınırlar

- Model kuralı kartları havuzlar; kartlar farklı çekicilere gidebilir (hücre düzeyi raporlanır).
- D1b'deki 100 turluk yaşam süresi gözlenen ufkun (en çok 12 orta oyun turu) çok ötesine bir dışdeğerlemedir. Kuralın bir özelliği olarak raporlanır, LLM'lerin 100 turluk davranışına dair bir iddia değildir.
- Eşikler (2,5 / 7,5; 0,9 / 0,8; 0,15; 0,2–0,8) veriden önce yazıldı ama denenmedi.
- İnsan katkıları 0–20 arası tam sayılara yayılıyor; tam simetrik durumlar (Z, C10) insanlarda seyrek olabilir.
- Kural yalnız bir tur geriye bakar; çok turlu bellek (ör. itibar) yakalanamaz.
- 4 kişilik homojen gruplar; ağ ve büyük nüfus yok.

## 9. Uygulama

- Betik `pgg_analysis_dynamics.py`, testler `tests/test_pgg_analysis_dynamics.py`. Sentetik dünyalar:
  - Z emici ve C10 kalıcı bir dünya;
  - tek bir 0'ın grubu devirdiği bir dünya;
  - R0 sabit noktaları bilinen f'ler;
  - yükleme sha256 kontrolü.
- Sonuç `results/dynamics_analysis.json`. Dosyanın sha256'ı bu dosyaya ek olarak yazılır. API çağrısı yok.

## Değişiklik günlüğü

- 2026-10-19: ilk sürüm, hesaplamadan önce.

## Ek D.1 — Bootstrap düzeltmesi, D2 k1 sınıfları (2026-10-19, ilk çalıştırmadan sonra)

- **Ne görüldü:** ilk çalıştırma (`results/dynamics_analysis_v0_stratified_k1.json`, sha256 `9b28e672be4e9f3e44640f2e4dd9afc02eb1a35a7faac77f23e2c029d5082852`, kod `2fd471c`), k1 sınıflarında sıfır genişlikte CI'ler verdi. Örnekler: insan k1 = 2, 16 grup, gözlenen 0,62 [0,62, 0,62]; GPT AB k1 = 3, 5 grup, fark −0,14 [−0,15, −0,14].
- **Neden:** §6'daki kart (şehir) içinde tabakalı bootstrap, k1 sınıfı içinde tabakaların çoğunu 1–3 gruba indiriyor. Tek gruplu bir tabaka yeniden örneklemede hep aynı değeri verir. Böyle bir CI belirsizliği yok sayar; bu bir yöntem hatasıdır.
- **Değişiklik:** yalnız D2 k1 sınıflarında bootstrap tabakasız yapılır (sınıf içindeki gruplar üzerinden). Bütün veri kümesi düzeyindeki paylarda (D1c S(E), D3a) tabakalama aynen kalır; orada her kartta 6–16, her şehirde 8–24 grup var. Bu değişiklik CI'leri genişletir; yani tutucu yöndedir. Sonuçlar bu düzeltmeyle yeniden hesaplanır ve ilk dosyanın etiketleri ayrıca raporlanır.
- **İlk çalıştırmadan görülen ama değiştirilmeyen bir sınır durumu:** Mistral'ın model düzeyindeki R0'ı, k = 0 başlangıcından 13. turda m = 2,497'ye iniyor. Bu, çöküş eşiğinin (2,5) 0,003 altında kalıyor; bu yüzden k*_R0 = 0. Eşik değiştirilmedi. Raporda bu sınır durumu açıkça yazılır: R0'ın tek kararlı sabit noktası x ≈ 2,08'dir, okuma kuralı 5'in ilk koşulu bu k* sınır durumundan bağımsızdır.

## Ek D.2 — Sonuç (2026-10-19, keşifsel)

- **Dosya:** `results/dynamics_analysis.json`, sha256 `d51730d1acafce9cc962c682ab9f063a69fea3531e2e70f667ccf8e1ac46a715` (kod `4494b87`, D.1 düzeltmesiyle).
  - D.1, ilk dosyaya göre yalnız k1 sınıflarının CI'lerini ve 4 k1 etiketini değiştirdi (DeepSeek EB k1 = 0, GPT AB k1 = 3, GPT EB k1 = 1: "yeniden üretiyor" → "belirsiz"; insan k1 = 2: "sapıyor" → "belirsiz"). Geri kalan her şey birebir aynı.
- **Bağımsız kontroller:** ayrı kodla yeniden hesaplananlar:
  - π_Z, π_C10, p_Z, p_C10 (dondurulmuş sayımlardan);
  - insan son durum payları, Z kalıcılığı ve k1 sınıfları (ham CSV'den);
  - model kuralıyla D2, 6 başlangıç (kendi simülatörüyle, S = 4 000).

  Hepsi tuttu (simülasyon farkları ≤ 0,014).

### Okuma kuralları (§7), model başına

| | DeepSeek | Mistral | GPT |
|---|---|---|---|
| 1 Tuzak | çöküş emici | çöküş emici | çöküş emici |
| 2 İşbirliği | kilitlenme | kilitlenme | kilitlenme |
| 3 İki çekici | değil (AB'de işbirliği payı 0,02) | **iki çekici** | değil (EB'de çöküş payı 0,08) |
| 4 Devrilme k* | **1** | **1** | 3 |
| 5 R0 ile nitel uyum | yanlış öngörüyor | yanlış öngörüyor | yanlış öngörüyor |

### D1 Tuzaklar ve yaşam süreleri (model kuralı; parantezde gözlenen)

- **p_Z:** DeepSeek 0,95, Mistral 0,92, GPT 1,00. Gözlenen Z kalma payı S1 / AB / EB'de 0,93–1,00. İnsanlarda gözlenen 0,41 (22 geçiş); H-R3'te 0,32.
- **p_C10:** 0,96 / 0,95 / 1,00. Gözlenen 0,92–1,00. İnsanlarda C10 neredeyse hiç yok (1 geçiş); H-R3'te 0,00.
- **İşbirliği yaşam süresi** (C10'dan ilk çöküşe kadar, medyan): DeepSeek 25 tur, Mistral 15 tur, GPT > 100 tur (%99'u kesik). İnsan kuralında 13 tur.
- **Çöküşten işbirliğine geri dönüş** (gözlenen): AB / EB'de DeepSeek 0,02 / 0,06, Mistral 0 / 0, GPT 0,08 / 0. Çöküş grubu sayıları 47 / 50, 10 / 15, 13 / 5. İnsanlarda 0,19 (59 grup); insan gruplarının 0,61'i çöküş bölgesinden çıkıyor.
- **Hayatta kalma S(E):**
  - kural örneklem dışında DeepSeek ve GPT'de "yeniden üretiyor";
  - Mistral AB "belirsiz" (+0,08);
  - Mistral EB'de gözlenen kuraldan yüksek (+0,12 [0,04, 0,21], "belirsiz"): 15 turluk oyunda Mistral'ın işbirliği kuralın öngördüğünden daha uzun sürdü.

### D2 Devrilme noktası

**Model kuralı, 13. turda P(çöküş), k = 0 / 1 / 2 / 3 / 4:**

| | k = 0 | k = 1 | k = 2 | k = 3 | k = 4 |
|---|---|---|---|---|---|
| DeepSeek | 0,28 | 0,96 | 0,98 | 0,98 | 0,99 |
| Mistral | 0,42 | 0,98 | 0,98 | 0,98 | 0,99 |
| GPT | 0,00 | 0,04 | 0,30 | 0,81 | 1,00 |
| İnsan kuralı | 0,19 | 0,23 | 0,22 | 0,25 | 0,27 |

İnsan kuralında devrilme yok.

**Hücre kurallarında k\*:**
- DeepSeek: 8 hücrede 1, 3 hücrede 0, 1 hücrede yok;
- Mistral: 6 hücrede 1, 5 hücrede 0, 1 hücrede 2;
- GPT: 4 hücrede 2, 7 hücrede 3, 1 hücrede 4.

**R0 (model düzeyi f):**
- DeepSeek: kararlı sabit nokta 0, kararsız 15. k*_R0 = 0; tümü 10'dan başlayan grup 13. turda m = 0,58.
- Mistral: tek kararlı sabit nokta ≈ 2,08. k*_R0 = 0, sınır durumu (m₁₃ = 2,497; D.1).
- GPT: kararlı sabit nokta yok. 0 zayıf kararsız (eğim 1,06); 15–20 arası nötr süreklilik. k*_R0 = 4: grup yalnız dördü de 0'la başlarsa çöküyor.

R0'ın kararlı sabit nokta sayısı (1 / 1 / 0), kuralın yapışkan simetrik durum sayısından (2 / 2 / 3) farklı.

**Gözlenen kontrol** (E'de çöküş payı; gözlenen / kural / R0):
- DeepSeek k1 = 1: S1 0,82 / 0,83 / 0,36; AB 1,00 / 0,93 / 0,88; EB 0,94 / 0,84 / 0,47.
- Mistral k1 = 1: S1 1,00 / 0,94 / 0,56; AB 1,00 / 1,00 / 0,40. EB'de bu sınıfta 4 grup var, raporlanmadı.
- GPT k1 = 2: S1 0,44 / 0,29 / 0,00; AB 0,33 / 0,40 / 0,00; EB 0,09 / 0,38 / 0,00.
- GPT k1 = 3: S1 0,57 / 0,69 / 0,50; AB 0,80 / 0,94 / 0,80.
- **İnsan** k1 = 0 / 1 / 2 (151 / 63 / 16 grup): gözlenen 0,11 / 0,40 / 0,62; H-R3 0,16 / 0,23 / 0,25.

  İnsanlarda ilk turdaki 0'lar sonu kademeli olarak kötüleştiriyor, ama tek turluk havuz kural bunu yeniden üretmiyor (k1 = 1: +0,17 [0,06, 0,29]; k1 = 2: +0,38 [0,12, 0,63]; ikisi de "belirsiz").

### D3 İki uçlu sonlar ve yol bağımlılığı

**Ara bölge payı (E'de; gözlenen / kural / R0):**

| | S1 | AB | EB |
|---|---|---|---|
| DeepSeek | 0,01 / 0,02 / 0,16 | 0,02 / 0,02 / 0,15 | 0,02 / 0,03 / 0,11 |
| Mistral | 0,01 / 0,02 / 0,02 | 0,00 / 0,02 / 0,03 | 0,02 / 0,01 / 0,00 |
| GPT | 0,04 / 0,05 / 0,19 | 0,02 / 0,04 / 0,23 | 0,03 / 0,02 / 0,17 |

İnsanlarda gözlenen 0,30, H-R3 0,33.

- **Örneklem dışında (AB, EB) çöküş / ara / işbirliği payları:**
  - DeepSeek ve GPT'de 12 karşılaştırmanın 12'si "yeniden üretiyor";
  - Mistral'da ara bölge "yeniden üretiyor"; çöküş ve işbirliği "belirsiz": kural çöküşü fazla öngörüyor (AB 0,42 vs 0,34; EB 0,43 vs 0,29).
- **Aynı başlangıç, farklı son** (gözlenen; E'de çöküş / işbirliği):
  - Mistral S1'de tümü 10'la başlayan 65 grup: 0,22 / 0,77 (kural çöküş 0,28); AB'de 25 grup: 0,16 / 0,84; EB'de 23 grup: 0,22 / 0,78.
  - GPT S1'de (0, 0, 10, 20) ile başlayan 16 grup: 0,56 / 0,31.
- **"Başlangıçta karar verilmemiş" pay** (kural, 0,2 < P(çöküş) < 0,8):
  - DeepSeek 0,02–0,09; Mistral 0,35–0,59; GPT 0,14–0,22; insan (H-R3) 0,40.
- **Hücre içi iki uçlu hücreler:**
  - S1: DeepSeek 3 / 12, Mistral 7 / 12, GPT 8 / 12;
  - insan şehirleri 10 / 16.

### Okuma (betimsel, keşifsel)

1. Bağlam içinde öğrenilen tek turluk kural, ortalama yörüngelerin ötesinde makro yapıyı da üretiyor: emici bir çöküş durumu, yapışkan bir işbirliği durumu ve iki uçlu son durum dağılımı. DeepSeek ve Mistral'da ayrıca tek bedavacıda keskin bir devrilme eşiği var. Örneklem dışı verilerde bu yapı büyük ölçüde tutuyor; istisna Mistral'ın 15 turluk oyunu: işbirliği öngörülenden uzun sürdü.
2. İzole cevaplardan kurulan kural (R0) üç modelde de nitel olarak farklı bir sistem öngörüyor:
   - DeepSeek ve Mistral'da tek çekici ve kademeli düşüş;
   - GPT'de çöküşsüz bir yükseliş;
   - bedavacılara zayıf duyarlılık ve fazla sayıda ara son.
3. İnsan grupları aynı oyunda başka bir rejimde:
   - çöküş emici değil, geri dönüş var;
   - sonlar iki uçlu değil, %30'u arada;
   - ilk turdaki bedavacıların etkisi kademeli.

   İnsan dinamiği tek turluk havuz kuralla yalnız kısmen yakalanıyor. Bir olası açıklama kişiler arası kalıcı farklar (heterojenlik) ama bu sınanmadı. LLM grupları homojen ajanlardan oluşuyor ve tek turluk kural onlar için yetiyor.

## Ek D.3 — Yuvarlama düzeltmesi (2026-10-20)

- İnsan grupları, k1 = 2: gözlenen çöküş payı tam 10/16 = 0,625. Makalede yarımı yukarı yuvarlamayla **0,63** yazılır; D.2'de 0,62 yazılmıştı. Etiket değişmez.
