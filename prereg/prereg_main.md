ONAYLANDI — 2026-10-11 (kullanıcı)

> config'lerde prereg_approved=true ayrı developer görevinde yapılır; ücretli koşu yok

> **Onayın dayanağı (EMİR 6 "Uygulama" koşulu):** #95'te tam test takımı geçti (505 test) [T95]; #96'da tam test takımı geçti (528 test, `gorev96_tests.txt`: "Ran 528 tests … OK") [T96]; dry-run kapıları 0a (A ve B), 0b (A ve B) ve Aşama 1 (A ve B) için "GEÇER" [C3D]. Kullanıcı kararları §13'te. Dört config'te (`configs/main.json`, `main_s0a_example.json`, `main_s0a_schema.json`, `main_s0b.json`) **`"prereg_approved": false`** hâlâ duruyor (her dosyada satır 3) [CFG6]; `true` yapılması ayrı bir developer görevidir. **Her aşama (0a, 0b, Aşama 1) ancak kullanıcı o aşama için "BAŞLA" dedikten sonra başlar** [EM6 Bölüm 3]; koşular kullanıcının Terminal'inden `scripts/runctl.py` ile başlar (P8, §10.4).

# Ana deney ön kaydı (prereg_main): EMİR 5 ve EMİR 6, Aşama 0a, 0b ve 1

- **Tarih:** 2026-10-10, görev #94 (ilk taslak). **Güncelleme:** 2026-10-11, görev #98 (EMİR 6; ayrıntı: değişiklik günlüğü). Veriden önce yazıldı [CL "Write the plan before the data"].
- **Belgenin niteliği:** iç yazılı plan; kamusal kayıt değildir [CL].
- **Bu belgeyi yazan görevlerde yapılmayanlar:** kod çalıştırılmadı, API çağrısı yapılmadı; depoya, `runs/` altına ve `raw_calls.jsonl`'a yazılmadı; `prereg_minipilot.md` değiştirilmedi.
- **Öncelik:** EMİR 6 metni esastır; önceki emirlerle çeliştiği her noktada EMİR 6, onunla çelişmeyen her noktada EMİR 5 geçerlidir [EM6 giriş; EM5 giriş].
- **Pilot verisi ana analize girmez.** Pilot v2 (`pilot_v2_20261005`), mini-pilot (`minipilot_20261008`), M1 tesisat ölçümü, Aşama 0a ve Aşama 0b verisi ana analize (P4–P5) **girmez** [CL "exclude pilot data"; EM5 Bölüm 3]. Pilot verisi yalnız iki yerde kullanılır: maliyet kalibrasyonu (mini-pilot; P7) ve güç hesabı (pilot v2 + mini-pilot; P7 §9.3). İkisi de tasarım girdisidir, hipotez testi değildir.

**Kaynak kısaltmaları**

| kısaltma | kaynak |
|---|---|
| **EM6** | EMİR 6 metni (2026-10-11), Bölüm 1 (C1–C3), Bölüm 2 (P-a–P-c), Bölüm 3 (Soru 1–3, Uygulama); üst yönetici ve kullanıcı |
| **EM5** | EMİR 5 metni (Hedef 30), Bölüm 1 (M1–M4), Bölüm 2 (K1–K6), Bölüm 3 (P1–P9); üst yönetici, 2026-10-10 |
| **T95** | Görev #95 sonuç raporu (C1 kod sürümü kilidi, C2 biçime duyarlı tahmin; 505 test; orc commit `86cae1f`) |
| **T96** | Görev #96 sonuç raporu (C3 yeni 0a, model başına G, bütçeler; 528 test; orc commit `782dc31`) |
| **C3D** | `gorev_emir6_c3_dryrun.md` (#96; dry-run tabloları, sha256'lar, 0a render örneği) |
| **GUC2** | `main_prereg_girdi/guc_v2/guc_v2.md` ve aynı klasördeki CSV'ler (#97; güç hesabı) |
| **CFG6** | depo `configs/main.json`, `main_s0a_example.json`, `main_s0a_schema.json`, `main_s0b.json`, #95/#96 sonrası (görev #98'de okundu) |
| **T90** | Görev #90 sonuç raporu (Bölüm 1: M1–M4; testler; commit `d8eafc9`) |
| **T91 / S6** | Görev #91 sonuç raporu ve `gorev_d2_s6_dogrulama.md` |
| **T92** | Görev #92 sonuç raporu ve `main_prereg_girdi/README.md` (CSV'lerden üretilmiş) |
| **T93** | Görev #93 sonuç raporu (commit `69ef290`) |
| **DRY5** | `main_dryrun_tablosu.md` (#93; sha256 `fff34aa7…a801`) |
| **KD** | `main_kartlar/cikti/dogrula.md` (#93) |
| **CFG5** | depo config'leri, #93 sürümü. **Not:** CFG5'e verilen satır numaraları #93 sürümüne aittir; #95 `stage`, #96 `groups_per_cell_by_model` ve `params.rounds` eklediği için güncel dosyalarda satırlar kaydı. Güncel değerler için CFG6 |
| **FR4** | depo `frames/abstract_v4.json` (#93; bu görevde okundu) |
| **CARD** | depo `cards/main_cards_v1.json` (#93; bu görevde okundu) |
| **PMP** | `prereg_minipilot.md` (§n; teknik not T1–T3; okuma eki) |
| **MPA** | `minipilot_analiz/minipilot_analiz.md` (#78) |
| **MUH5** | `minipilot_muhakeme_okuma.md` (#89; K1–K12) |
| **D2** | `gorev_d2_kurum_uygulama.md` (#69; S1–S8) |
| **CT** | depo `notes/cevap_talimati_tasarim.md` |
| **UK** | depo `notes/uzun_omurlu_kosu.md` |
| **BG** | depo `notes/BACKGROUND.md` |
| **CL** | depo `CLAUDE.md` |
| **G8** | `gorev8_silica_flint.md` (#8) |

**(tahmin)** = kaynağı olmayan çıkarım ya da benim hesabım. **(hesap)** = kaynaktaki sayılardan bu belgede yapılan aritmetik. **KULLANICI KARARI** = emir metninde karşılığı olmayan, burada varsayılanı önerilen nokta; bu varsayılanlar 2026-10-11'de onaylandı (§13 soru 3).

---

## 0. Sonuç (önce bu)

1. **Ne ölçülüyor:** Aynı kimlik kartının (4 şehir × 3 stil) izole bir ajanda ve 10 turluk homojen grupta katkıyı nasıl değiştirdiği; grup etkileşiminin farkı büyütüp büyütmediği, söndürüp söndürmediği; izole tepki fonksiyonunun grup davranışını öngörüp öngörmediği (BG §4; EM5 P4).
2. **Aşamalar:** 0a cevap biçimi testi (biçim başına 360, toplam 720 çağrı; 3 turluk kısa grup oyunu dahil) → 0b duman testi (1800 çağrı) → 1 ana koşu (DeepSeek 16, GPT 16, Mistral 10 grup/hücre; 23 040 çağrı). 0a ve 0b analiz verisi değildir [EM6 C3; T96; C3D].
3. **Hipotezler H1–H5**, her biri bütün yönleriyle (P4). Karar kuralı: "var" için hem |D| > 2 hem de %95 CI'nin 0'ı dışlaması; model içinde Holm (P5).
4. **Bütçe (tahmin; #96 dry-run):** Aşama 1 ortalama A 46,8940 / B 47,0614 USD; sert tavan 91, alt tavanlar DeepSeek 22 / Mistral 68 / GPT 3, kapı 52 USD. 0b: 10 / 2-8-0,5 / 5,5. 0a (koşu başına): 1,6 / 0,3-1,3-0,1 / 1,0. Bütün kapılar geçiyor [C3D].
5. **Güç (GUC2):** havuzlanmış hücre içi SD DeepSeek 0,887, GPT 2,507; Mistral için SD bilinmiyor. G = 16'da DeepSeek ve GPT'de 10 ve 5 puanlık fark ≥ 0,999 oranında yakalanıyor; Mistral için en kötü durumda (SD = 9, G = 10) oran 10 puanda 0,730, 5 puanda 0,293 (§9.3).
6. **Kullanıcı kararları verildi (§13):** G, bütçe ve onay. Belge onaylandı; config'lerde `prereg_approved` hâlâ false, ücretli koşu yok.
7. **Açık noktalar:** D2 S6'nın "iki belgeyi birebir okuma" koşulu karşılanmadı (§8.4); 0a izole sorusunun "round 2 of 3" olması #96'nın geliştirici seçimi, emirde yok (§3.1); #96 dry-run tabloları commit'ten önce üretildi, commit sonrası bir kez yeniden üretilmesi öneriliyor (§12.3); Mistral'ın Aşama 1 alt tavanı p95'in yalnız 0,37 USD üstünde (§9.4); #90 değişen dosyaların sha256'larını raporlamadı (§12.2).

---

## 1. Amaç ve kapsam

### 1.1 Araştırma sorusu

Kimlik tanımı izole bir ajanın davranışını değiştirdiğinde, on turluk grup etkileşimi bu farkı büyütür mü, söndürür mü, korur mu [BG §4]? İzole tepki fonksiyonundan "etkileşim hiçbir şey katmasaydı" grubun ne yapacağı simüle edilir ve gözlenen grupla karşılaştırılır (Flint ve ark. mantığı) [BG §4; G8 §2].

### 1.2 Bu belgenin kapsadığı aşamalar

| aşama | amaç | analiz verisi mi | bölüm |
|---|---|---|---|
| 0a | cevap biçimi seçimi (A / B) | hayır | P1 (§3) |
| 0b | son istemlerle duman testi; tasarım kusuru arama | hayır | P2 (§4) |
| 1 | ana koşu: N koşulu, homojen gruplar, 12 kart × 3 model; grup kolu + izole kol | **evet** | P3 (§5), P4–P5 (§6–§7) |

### 1.3 Aşama 2 — yalnız taslak başlıklar (bu belgede karar yok)

Aşama 2, Aşama 1 analizinden sonra **ayrı bir prereg ekiyle** yazılır [EM5 K4]. Başlıklar:

1. P koşulu (ceza adımı, 1:3; Herrmann tasarımı) — çerçeve metni ve sürdürme testleri.
2. Karma gruplar (farklı kartlı ajanlar aynı grupta) — bileşim ve hücre tanımı.
3. Hipotezler (her iki yönüyle): ceza katkıyı değiştirir mi; antisosyal ceza; karma grupta yakınsama.
4. İnsan çapası: Herrmann P koşulu şehir ortalamaları ve antisosyal ceza payları.
5. "punishment" terim çakışması riski (mini-pilotta N koşulunda katkı düşüşüne "punishment" denmesi) [MUH5 K10].
6. Bütçe, G ve durdurma kuralları.

---

## 2. Tasarım (K1–K6)

### 2.1 K1 — Çerçeve: abstract_v4; hikâye kolu yok

- **Hikâye kolu ana deneyde yok.** Gerekçe: mini-pilotta tanıma azalmadı. E2a (i) "experiment" hariç, etiket alanında DeepSeek abstract_v3 **537/540**, DeepSeek story **533/540**; Mistral abstract_v3 **342/342** [EM5 K1; MPA §3.2; PMP okuma eki madde 1]. Ele veren, ödeme kuralının kendisidir [EM5 K1].
- **abstract_v4 = abstract_v3 + sistem mesajında karttan önce "The following describes you:" satırı** [EM5 K1; FR4 satır 7]. Gerekçe: yalnız karttan oluşan sistem mesajı DeepSeek'te "prompt injection" gibi okundu [EM5 K1; MUH5 K2: "MP-1456: 'Maybe it's a prompt injection?'"; MUH5 satır 205: MP-904].
- Sistem mesajı (aynen): `"system": "The following describes you:\n{card}"` [FR4 satır 7].
- "experiment" ve "participant" hiçbir istemde geçmiyor: 252 istem tarandı (3 cevap biçimi × 12 kart × 7 istem türü); kullanıcı mesajı, cevap talimatı ve response_format abstract_v3 ile 252/252 bayt bayt aynı [T93].
- `"kind": "abstract"` → çerçeve linter'ından muaf (bilerek game/contribute diyor) [FR4 satır 6; PMP §9.5].
- **sha256:** `frames/abstract_v4.json` = `c00db315d9c3141b78b04de5ece650e4b922db907cb90ae124666c439633a9f4` [T93; CFG5 `main.json` satır 46].
- **Tanıma (E2a) hipotez değildir.** Satır başına kaydedilen **betimsel ortak değişkendir** [EM5 K1]: her karar satırı için (i) paradigma/literatür ("experiment" dahil ve hariç) ve (ii) oyun teorisi eşleşmesi (0/1), mini-pilottaki sözlük ve sayım kuralıyla (PMP §5.0–§5.1; MPA `analiz.py` → `e2a_counts`, `match_terms`) yazılır. Hiçbir karar kuralına girmez.
- Kart uzunluğu (kelime, karakter) da satır başına ortak değişken olarak kaydedilir [prereg_pilot A6 soru 9; KD §6].

### 2.2 K2 — Modeller ve sağlayıcılar

| kısa ad | model | sağlayıcı (OpenRouter) | kaynak |
|---|---|---|---|
| deepseek | `deepseek/deepseek-v4.1-flash` | `deepinfra/fp8` (DeepInfra, fp8) | EM5 K2; CFG5 `main.json` satır 14, 56–62 |
| mistral | `mistralai/mistral-large-4-0` | `mistral` | EM5 K2; CFG5 satır 15, 63–66 |
| gpt | `openai/gpt-6-luna` | `openai` | EM5 K2; CFG5 satır 16, 67–70 |

- **Gönderilmeyenler:** `temperature` ve `reasoning_effort`; logda "default" yazılır [EM5 K2; CFG5 `_notes`].
- **max_tokens = 16000** [EM5 K2; CFG5 satır 52].
- `allow_fallbacks: false`, `require_parameters: true` (üç modelde) [CFG5 `_notes`]; `check_snapshot: true`, `snapshot_version_models: ["mistral"]` [CFG5 satır 84–87]; `reasoning_cap_rule: {"mistral": "max_reasoning_completion"}` [CFG5 satır 88–90]; `workers` 4, `parallel_units` 3 [CFG5 satır 91–92].
- `request_deadline_s` 900, `stall_timeout_s` 1800 [CFG5 satır 53–54].

### 2.3 K3 — Kartlar (12 kart)

- **Dosya:** `cards/main_cards_v1.json`, sha256 `bb2be483d1cb860df43d46675a0b798acc240f5d022ee36a5e5d272a12d7f1dc`; config'te `cards_sha256` ile kilitli [T93; KD §1; CFG5 satır 6].
- **Stiller:** minimal = v3 ile bayt bayt aynı; değer = v2 ile bayt bayt aynı; olgusal = D2 C1 mahkeme süresi kartı [EM5 K3; KD §2–§3].
- **Linter sonucu:** 12 kartın hiçbiri kart_linter (17 kök), cerceve_linter (16 kök), kimlik listesi (zorunlu 7), C3 sözlüğü (A 26 / B 10 / C 4) ve E2a sözlüğüne takılmadı; "GENEL SONUÇ: TÜM ZORUNLU KONTROLLER GEÇTİ" [KD §4]. Yalnız uyarı (çıkış kodunu etkilemez): `boston_value`'da şart sözlüğü "authorit" [KD §5].

**Tam metinler, kelime ve karakter sayıları** [CARD; KD §4]:

| card_id | stil | metin (aynen) | kelime | karakter |
|---|---|---|---|---|
| boston_minimal | minimal | You are a 21-year-old university student living in Boston. | 9 | 58 |
| boston_value | değer | You are a 21-year-old university student living in Boston. Where you grew up, people prize personal liberty and speaking up against authority. | 22 | 142 |
| boston_factual | olgusal | You are a 21-year-old university student living in Boston. In your country, a lawsuit over an unpaid bill takes about 444 days. | 22 | 127 |
| copenhagen_minimal | minimal | You are a 21-year-old university student living in Copenhagen. | 9 | 62 |
| copenhagen_value | değer | You are a 21-year-old university student living in Copenhagen. Where you grew up, people expect equal standing and decide for themselves. | 21 | 137 |
| copenhagen_factual | olgusal | You are a 21-year-old university student living in Copenhagen. In your country, a lawsuit over an unpaid bill takes about 485 days. | 22 | 131 |
| athens_minimal | minimal | You are a 21-year-old university student living in Athens. | 9 | 58 |
| athens_value | değer | You are a 21-year-old university student living in Athens. Where you grew up, people respect their elders and take pride in their ancient past. | 24 | 143 |
| athens_factual | olgusal | You are a 21-year-old university student living in Athens. In your country, a lawsuit over an unpaid bill takes about 1,711 days. | 22 | 129 |
| riyadh_minimal | minimal | You are a 21-year-old university student living in Riyadh. | 9 | 58 |
| riyadh_value | değer | You are a 21-year-old university student living in Riyadh. Where you grew up, people strongly respect family elders and tribal leaders. | 21 | 135 |
| riyadh_factual | olgusal | You are a 21-year-old university student living in Riyadh. In your country, a lawsuit over an unpaid bill takes about 575 days. | 22 | 127 |

Sağlama (bu görevde elle): `boston_minimal` 9 kelime / 58 karakter; ek cümle "In your country, … 444 days." 13 kelime / 68 karakter; 58 + 1 + 68 = 127 → KD ile aynı.

**Olgusal kart: D2 C1 mahkeme süresi.** Kaynak: Doing Business 2020, Enforcing Contracts, "Time (days)": ABD 444, Danimarka 485, Yunanistan 1,711, Suudi Arabistan 575 [D2 §2]. Tam sayı; "In your country" [EM5 K3].

**D2 kararları (S1–S8)** [EM5 K3]:

| soru (D2 §5.2) | karar | uygulama / kaynak |
|---|---|---|
| S1 DB2020 Enforcing Contracts "Time (days)" kabul mü | **Evet** | CARD |
| S2 aday cümle | **C1** ("a lawsuit over an unpaid bill takes about N days") | CARD; D2 §4 |
| S3 "In your country," | **Evet** | CARD (dört kartta da) |
| S4 Boston'da ABD birleşik değeri | **Evet (444)** | CARD; 444 = NYC (370) ve LA (555) birleşimi [D2 §2; S6 §4 yan bulgu 2] |
| S5 tam / yuvarlak | **Tam sayılar** ("1,711" binlik ayraçlı) | CARD |
| S6 inceleme PDF'i + WilmerHale birebir okunsun | **Evet**; PDF metne çevrilemiyorsa raporlanır | Sonuç §8.4: iki belge metne çevrilemedi; hüküm GIA raporu ve DB verisine dayanıyor [S6] |
| S7 B-READY 2026 yeniden kontrol | **Hayır (şimdilik)** | — |
| S8 nötr prosedür kartının yerine mi | **"Yerine"**: nötr prosedür kartı ana deneyde **yok**; rolü (uzunluk kontrolü) mini-pilotta karşılandı | EM5 K3 |

**Uzunluk (bilgi; eşitlik gevşetildi, prereg_pilot A6/9):** olgusal ↔ değer kartı karakter farkı Boston −%10,6, Copenhagen −%4,4, Athens −%9,8, Riyadh −%5,9 [KD §6].

### 2.4 K4 — Aşama 1'in hücreleri

- Koşul N; homojen gruplar (gruptaki 4 ajan aynı kartı taşır); 12 kart × 3 model = **36 hücre**; kollar: grup (4 ajan × 10 tur) ve izole [EM5 K4; CFG5 satır 7–24].
- **Hücre başına grup sayısı G model başına farklıdır: DeepSeek 16, GPT 16, Mistral 10** (kullanıcı kararı, §13 soru 1) [EM6 Soru 1; T96]. Config: `"groups_per_cell": 10` ve `"groups_per_cell_by_model": {"deepseek": 16, "mistral": 10, "gpt": 16}` [CFG6 `main.json` satır 26–31]. İkisi de config kaydına girer; `--resume` başka bir G ile başlatılırsa reddedilir (mock testli) [T96].

### 2.5 K5 — İzole kol

- **5 nokta (0, 5, 10, 15, 20) × 4 tekrar**, sabit tur: `isolated_frame: "fixed_round"`, `isolated_round_no: 5` [EM5 K5; CFG5 satır 26–35].
- Soru metni (aynen): "This is round {round_no} of {rounds}. In the previous round the other {n_others} players of your group contributed, on average, {others_mean} points each." → "round 5 of 10" [FR4 satır 48].
- Gerekçe: mini-pilottaki doğrusallık işaretleri tekrarlar arası tutarsızlıktan geliyordu; sorun çözünürlük değil, varyans [EM5 K5]. Bu yüzden nokta sayısı değil tekrar sayısı artırıldı (mini-pilotta 2 tekrar [PMP §2.1]).
- Model başına izole çağrı: 12 kart × 4 tekrar × 5 nokta = **240** [DRY5: her G'de izole 240].

### 2.6 K6 — Kural anlama

- İki soru kalır; cevap anahtarı **q1 = 28, q2 = −6**; q2'nin nötr son cümlesi: "Give the change as a whole number (it can be positive, zero or negative)." [EM5 K6; FR4 satır 56–62].
- Anahtar (sağlama, bu görevde elle): q1 = 20 − 8 + 0,4 × (8 + 4 + 12 + 16) = 12 + 16 = 28; q2 = 10 × (0,4 − 1) = −6 (mpcr 0,4, bağış 20 [BG §4]).
- Grup kolunda her ajana 1. turdan önce bir kez; izole kolda her çizelgeden önce bir kez [PMP §6.1].
- **Dışlama yok; yalnız duyarlılık** (P5 §7.5) [EM5 K6].
- Kural anlama çağrısı koşuyu durdurmaz; `max_invalid` tükenirse `comp_missing: true` yazılır; geçersizleri %5 tavanına sayılmaz [PMP §6.1, §9.3].

---

## 3. P1 — Aşama 0a: Cevap biçimi testi (ücretli, küçük; analiz verisi değil)

### 3.1 Tasarım (EMİR 6 C3)

- **Neden yeniden tasarlandı:** mini-pilotta Mistral'ın 28 geçersiz yanıtının 27'si grup turundaydı, 1'i izole, 0'ı kural anlama [PMP T1; EM6 C3]. Yeni 0a geçmişli grup istemlerini de dener.
- **A = `example_object`** (şema metni yerine örnek cevap nesnesi); **B = `json_schema_strict`** (response_format json_schema, strict) [EM5 M4; T90 M4]. İki biçimde de `rationale` zorunlu [T90 M4]. Her biçim ayrı bir koşudur (`main_s0a_example.json`, `main_s0a_schema.json`) [CFG6].
- Çerçeve abstract_v4; kartlar Boston ve Riyadh × 3 stil = 6 kart [EM6 C3; T96].
- **Her biçim için model başına çağrılar** [EM6 C3; T96; C3D]:

| kol | tasarım | çağrı |
|---|---|---|
| grup (katkı) | 6 kart × 1 grup × 4 ajan × 3 tur | 72 |
| izole | 6 kart × X = 10 × 2 tekrar | 12 |
| kural anlama | grup kolunda her ajana 1 (24) + her izole çizelgeye 1 (12) | 36 |
| **model toplamı** | | **120** |

Biçim başına 3 model × 120 = **360**; iki biçim **720** çağrı [C3D]. (Kural anlama ayrıştırması 24 + 12 = 36 §2.6 kuralıyla yapılmış hesaptır; toplam 36 C3D'den.)

- **Tur sayısı:** `params.rounds = 3` yalnız iki 0a config'inde; motorun varsayılanı 10 tur olarak kaldı [T96; CFG6 `main_s0a_*.json` satır 20–22].
- **İzole sorunun turu:** `isolated_round_no: 2` → "This is round 2 of 3" [T96; CFG6 satır 33]. **GELİŞTİRİCİ SEÇİMİ (#96):** emirde bu konuda bir şey yazmıyor; 3 turluk oyunda 5. tur olmadığı için #96 seçti ve kullanıcının onayına bağladı [T96].
- **Geçersiz sınırları:** `invalid_rate_cap` kapalı (`null`; ölçümün amacı geçersizleri saymak), `max_invalid` 8 [EM6 C3; CFG6 satır 72, 84]. #96'nın okuması: bir çağrıda üst üste 9 geçersiz cevaptan sonra vazgeçilir, yani 8 kez yeniden istenir [T96].
- **"Biçim başarısız":** bir çağrı geçerli cevap alamazsa (8 geçersizle RunAborted) **yalnız o model durur** ve `format_failed` olarak kayda geçer; bu, o model × biçim için "biçim başarısız" sayılır. Diğer modeller oynamaya devam eder; `--resume` ile de o model durmuş kalır. Sağlayıcı uyuşmazlığı biçim hatası sayılmaz. 0b ve Aşama 1'de eski davranış (koşu durur) aynen sürer. Hepsi mock testli [EM6 C3; T96].
- **Özetteki `format_test` alanı** model başına `n_invalid`, `n_parse_fail`, `n_comp_invalid`, `n_comp_parse_fail`, `invalid_parse_rate`, `decision_invalid_parse_rate` (kural anlama hariç), `run_aborted`, `format_failed` verir [T96; depo `pgg_game.py` `format_test_summary`]. **A/B seçimini kod yapmaz;** seçim §3.2 kuralıyla yapılır ve ekte gerekçelendirilir.
- Run adları ve seed namespace'leri: `main_s0a_example_<YYYYMMDD>` / `pgg-main-s0a-example`; `main_s0a_schema_<YYYYMMDD>` / `pgg-main-s0a-schema` [CFG5 `main_s0a_*.json` satır 4, 66; namespace CFG6 satır 71].
- **Sınırlılık — 0a bir biçim testidir:** 0a istemlerinde "ROUND 3 of 3. You are Player 1…", "for all 3 rounds" ve "This is round 2 of 3" yazıyor; Aşama 1 istemleri 10 turludur [EM6 C3; C3D render örneği; `gorev96_0a_render_ornegi.txt`]. 0a'daki katkı değerleri davranış verisi olarak yorumlanmaz; yalnız geçersiz ve parse_fail sayımı için kullanılır.

### 3.2 Önceden yazılmış seçim kuralı (aynen)

> **Varsayılan A. A'nın herhangi bir modelde geçersiz + parse_fail oranı > %2 ve B'ninki daha düşükse (ya da A RunAborted verdiyse ve B vermediyse) B seçilir. Sağlayıcı B'yi desteklemezse A kalır.** [EM6 C3; EM5 P1]

Uygulama tanımları (**KULLANICI KARARI**, 2026-10-11'de onaylandı, §13 soru 3):
- **Oran:** model × biçim başına (`n_invalid` + `n_parse_fail` + `n_comp_invalid` + `n_comp_parse_fail`) / o model × biçimde alınan yanıt sayısı (yeniden istenenler dahil). Kural anlama geçersizleri de sayılır, çünkü iki çağrı türü de cevap biçimini sınar. Kodun `invalid_parse_rate` alanı bu formülle hesaplanır [depo `pgg_game.py` `format_test_summary`].
- **Eşik (hesap):** model başına 120 çağrı tamamlanırsa 2 kötü yanıt 2/122 = %1,64, 3 kötü yanıt 3/123 = %2,44 eder; yani pratikte A'da bir modelde **3 ya da daha fazla** geçersiz/parse_fail yanıt kuralı tetikler.
- **"B'ninki daha düşük":** aynı modelde B'nin oranı A'nınkinden kesin küçük.
- **"A RunAborted verdiyse":** o modelde A koşusunun özetinde `format_failed: true` (geçersiz ya da ayrıştırılamayan cevaplarla durma; EM6 C3'teki "8 geçersizle RunAborted = biçim başarısız" tanımı). Başka bir nedenle duran model (ör. sağlayıcı uyuşmazlığı, alt tavan) ekte ayrıca raporlanır; otomatik karar verilmez (yorum).
- **"Sağlayıcı B'yi desteklemezse":** B koşusunda o modelin isteği desteklenmeme nedeniyle `http` hatasıyla reddedilirse (require_parameters true iken desteklemeyen uç noktaya istek gitmez [CT §3]). 2026-10-09 uç nokta listesine göre üç uç noktada `structured_outputs` var; uygulama derecesi doğrulanmadı [CT §3].
- **Seçim tek biçimdir:** Aşama 1'de üç model aynı `answer_format`'ı kullanır (config'te tek alan [CFG6 `main.json` satır 57]; model başına ayrı biçimin desteklenmediği tahmin).

### 3.3 Tahmini maliyet, tavanlar ve kapı (dry-run, #96)

**Biçim A (`main_s0a_example.json`)** — oyun: 4 ajan × 3 tur; izole `fixed_round` tur 2; nokta [10] × 2 tekrar; kural anlama açık [C3D]:

| model | kol | çağrı | ortalama (USD) | p95 üst sınır (USD) |
|---|---|---|---|---|
| deepseek | grup (katkı) | 72 | 0,0482 | 0,1848 |
| deepseek | izole | 12 | 0,0274 | 0,0598 |
| deepseek | kural anlama | 36 | 0,0055 | 0,0067 |
| **deepseek** | **toplam** | **120** | **0,0811** | **0,2513** |
| mistral | grup (katkı) | 72 | 0,5200 | 0,8995 |
| mistral | izole | 12 | 0,0950 | 0,1550 |
| mistral | kural anlama | 36 | 0,1721 | 0,2366 |
| **mistral** | **toplam** | **120** | **0,7870** | **1,2910** |
| gpt | grup (katkı) | 72 | 0,0090 | 0,0156 |
| gpt | izole | 12 | 0,0013 | 0,0016 |
| gpt | kural anlama | 36 | 0,0038 | 0,0041 |
| **gpt** | **toplam** | **120** | **0,0141** | **0,0213** |
| **TOPLAM** | | **360** | **0,8822** | **1,5636** |

**Biçim B (`main_s0a_schema.json`)** — aynı tasarım [C3D]:

| model | kol | çağrı | ortalama (USD) | p95 üst sınır (USD) |
|---|---|---|---|---|
| deepseek | grup (katkı) | 72 | 0,0484 | 0,1850 |
| deepseek | izole | 12 | 0,0274 | 0,0598 |
| deepseek | kural anlama | 36 | 0,0056 | 0,0068 |
| **deepseek** | **toplam** | **120** | **0,0813** | **0,2516** |
| mistral | grup (katkı) | 72 | 0,5215 | 0,9016 |
| mistral | izole | 12 | 0,0952 | 0,1552 |
| mistral | kural anlama | 36 | 0,1732 | 0,2377 |
| **mistral** | **toplam** | **120** | **0,7899** | **1,2946** |
| gpt | grup (katkı) | 72 | 0,0092 | 0,0159 |
| gpt | izole | 12 | 0,0013 | 0,0017 |
| gpt | kural anlama | 36 | 0,0039 | 0,0042 |
| **gpt** | **toplam** | **120** | **0,0145** | **0,0217** |
| **TOPLAM** | | **360** | **0,8858** | **1,5679** |

*Not (#95 C2): kalibrasyon schema_text ile ölçüldü; A/B farkı istem uzunluğundan ölçeklendi.* Tutarlar tahmindir; p95 üst sınırı çağrı türü başına p95 token × çağrı sayısıdır (toplamın p95'i değil) [C3D].

**Tavanlar ve kapı (koşu başına; A ve B'de aynı)** [T96; CFG6 `main_s0a_*.json` satır 73–79]:

| | değer (USD) | kural | dayanak |
|---|---|---|---|
| sert tavan `budget_usd` | 1,6 | ≥ toplam p95 | B 1,5679 |
| alt tavanlar DeepSeek / Mistral / GPT | 0,3 / 1,3 / 0,1 | ≥ model p95 | B 0,2516 / 1,2946 / 0,0217 |
| kapı `expected_cost_gate_usd` | 1,0 | ortalama × 1,1 (yukarı) | B 0,8858 × 1,1 = 0,9744 |

- **Kapı:** A 0,8822 ve B 0,8858 < 1,0 → **iki koşuda da GEÇER** [C3D].
- İki 0a koşusu birlikte: ortalama 0,8822 + 0,8858 = 1,7680 USD; p95 üst sınır 1,5636 + 1,5679 = 3,1315 USD (hesap).
- **Risk (tahmin):** Mistral'ın alt tavanı p95'in yalnız 0,0054 USD üstünde (hesap). 0a'da `invalid_rate_cap` kapalı ve çağrı başına 8 yeniden istek mümkün olduğu için, Mistral çok geçersiz verirse yeniden istekler tahmini aşabilir ve Mistral biçim ölçümü bitmeden alt tavanla durabilir. Bu durumda duruş "biçim başarısız" değil "alt tavan" olarak kaydedilir ve ekte raporlanır.

### 3.4 Sonucun kaydı

0a, kullanıcı 0a için "BAŞLA" dedikten sonra başlar (§10.4). Sonuç bu belgeye **tarihli ek** olarak yazılır: model × biçim oranları (`format_test`), `format_failed` / `run_aborted` durumları, uygulanan kural, seçilen biçim ve `configs/main.json` / `main_s0b.json`'a yazılacak `answer_format` değeri [EM5 P1; EM6 Bölüm 3]. Seçim 0b'den önce yapılır. 0a satırları hiçbir analize girmez.

---

## 4. P2 — Aşama 0b: Duman testi (son istemlerle; analiz verisi değil)

### 4.1 Kapsam

- **12 kart × 3 model × 1 grup (10 tur) + izole 1 tekrar (5 nokta) + kural anlama** [EM5 P2; CFG5 `main_s0b.json`].
- Model başına 600 çağrı (grup 480, izole 60, kural anlama 60); toplam **1800** [DRY5 Aşama 0b; C3D].
- `answer_format`: 0a'nın seçtiği biçim (şu an yer tutucu) [CFG6 `main_s0b.json` satır 52].
- Run adı `main_s0b_<YYYYMMDD>`, seed namespace `pgg-main-s0b` [CFG5 satır 4; CFG6 satır 74].
- Tahmini maliyet (#96): A ortalama **4,8518** / p95 üst sınır **8,9394**; B **4,8681** / **8,9603 USD**. Tavanlar (kullanıcı kararı, §13 soru 2): sert 10, alt tavanlar DeepSeek 2 / Mistral 8 / GPT 0,5, kapı 5,5 USD; kural sağlanıyor, kapı A ve B'de **GEÇER** [T96; C3D; CFG6 satır 76–82]. Model × kol tabloları §4.4'te.
- Copenhagen ve Athens kartları ilk kez burada koşulur (pilot v2 ve mini-pilot yalnız Boston + Riyadh [PMP §2.1]).

### 4.2 Okuma planı (muhakeme metinleri)

Amaç: son istemlerde tasarım kusuru aramak [EM5 P2; CL "After a pilot run, read the reasoning texts for design flaws"]. Sayım değil okuma; nedensel yorum yok.

- **Rationale:** 1800 satırın hepsi okunur.
- **Reasoning (DeepSeek ve Mistral):** model başına her kartta grup 1., 5. ve 10. turdan bir ajan (agent 1) + izole X = 10 + bir kural anlama = 12 × 5 = 60 kayıt (öneri). GPT'de reasoning dönen her kayıt (metin özet olduğu için) [PMP §3].
- **Bakılacaklar** (mini-pilot okumasının listesinden [MUH5 K1–K12]):
  1. "The following describes you:" satırından sonra kartın hâlâ "prompt injection / flavor text" diye okunup okunmadığı (K2).
  2. Olgusal kartın (mahkeme süresi) nasıl okunduğu: "irrelevant", ceza / yaptırım çağrışımı, Athens 1,711'in "kurallar işlemiyor" diye okunması [D2 §5.1 risk 1, 6].
  3. Kural yanlışları ve kural anlama cevaplarının gerekçeleri.
  4. Cevap biçimi artefaktları (şema geri yazma, şema tartışması) [MUH5 §9-7].
  5. İzole sorunun süren bir oyun gibi okunması [PMP okuma eki "Öneriler"].
  6. Değer kartında kimlik anılması; Copenhagen ve Athens değer kartlarının okunuşu.
  7. Tesisat iddiaları (MUH5 K12: sistem mesajı iddiası, "ChatGPT" öz-atfı).
- **Tesisat sayıları** (yalnız sayı): model başına geçersiz + parse_fail oranı (seçilen biçimde), `n_reasoning_capped`, `n_length`, `n_reuse_invalid`, maliyet / dry-run oranı, süre dağılımı.

### 4.3 Tarihli ek kuralı

- Okuma bir tasarım kusuru gösterirse değişiklik **Aşama 1'den önce**, gerekçesiyle, **tarihli ek** olarak bu belgeye yazılır [EM5 P2; CL].
- Değişiklik çerçeve ya da kart dosyasına dokunuyorsa: yeni sha256, linter, istem birebir aynılık testi ve yeni dry-run; config kilidi güncellenir. Değişen istemlerle 0b'nin yeniden koşulup koşulmayacağı ekte kullanıcıya sorulur.
- Seçilen biçimde 0b'de herhangi bir modelin karar çağrısı geçersiz oranı ≥ %5 ise (Aşama 1'in durma tavanı, §10) bu ayrıca raporlanır; otomatik değişiklik yok.
- **0b verisi ana analize girmez** [EM5 P2]. Değişiklik olmasa da "değişiklik yok" diye tarihli ek yazılır.

### 4.4 Dry-run tabloları (#96)

**Biçim A (`main_s0b.json`, `--answer-format example_object`)** — oyun: 4 ajan × 10 tur; izole `fixed_round` tur 5; noktalar [0, 5, 10, 15, 20] × 1 tekrar; kural anlama açık [C3D]:

| model | kol | çağrı | ortalama (USD) | p95 üst sınır (USD) |
|---|---|---|---|---|
| deepseek | grup (katkı) | 480 | 0,3275 | 1,2401 |
| deepseek | izole | 60 | 0,1370 | 0,2990 |
| deepseek | kural anlama | 60 | 0,0091 | 0,0112 |
| **deepseek** | **toplam** | **600** | **0,4737** | **1,5503** |
| mistral | grup (katkı) | 480 | 3,5350 | 6,0895 |
| mistral | izole | 60 | 0,4749 | 0,7749 |
| mistral | kural anlama | 60 | 0,2868 | 0,3943 |
| **mistral** | **toplam** | **600** | **4,2967** | **7,2587** |
| gpt | grup (katkı) | 480 | 0,0685 | 0,1155 |
| gpt | izole | 60 | 0,0066 | 0,0081 |
| gpt | kural anlama | 60 | 0,0063 | 0,0068 |
| **gpt** | **toplam** | **600** | **0,0814** | **0,1304** |
| **TOPLAM** | | **1800** | **4,8518** | **8,9394** |

**Biçim B (`main_s0b.json`, `--answer-format json_schema_strict`)** [C3D]:

| model | kol | çağrı | ortalama (USD) | p95 üst sınır (USD) |
|---|---|---|---|---|
| deepseek | grup (katkı) | 480 | 0,3284 | 1,2413 |
| deepseek | izole | 60 | 0,1371 | 0,2991 |
| deepseek | kural anlama | 60 | 0,0093 | 0,0114 |
| **deepseek** | **toplam** | **600** | **0,4748** | **1,5518** |
| mistral | grup (katkı) | 480 | 3,5454 | 6,1036 |
| mistral | izole | 60 | 0,4761 | 0,7761 |
| mistral | kural anlama | 60 | 0,2887 | 0,3962 |
| **mistral** | **toplam** | **600** | **4,3102** | **7,2759** |
| gpt | grup (katkı) | 480 | 0,0698 | 0,1172 |
| gpt | izole | 60 | 0,0067 | 0,0083 |
| gpt | kural anlama | 60 | 0,0066 | 0,0070 |
| **gpt** | **toplam** | **600** | **0,0831** | **0,1325** |
| **TOPLAM** | | **1800** | **4,8681** | **8,9603** |

*Not (#95 C2): kalibrasyon schema_text ile ölçüldü; A/B farkı istem uzunluğundan ölçeklendi.*

- Kapı 5,5: A 4,8518, B 4,8681 → **GEÇER**; kural değeri (ortalama × 1,1) A 5,3369, B 5,3549 [C3D].
- Sert tavan 10 ≥ toplam p95 (B 8,9603); alt tavanlar 2 / 8 / 0,5 ≥ model p95 (B 1,5518 / 7,2759 / 0,1325) [C3D]. Kuralın verdiği en küçük değerler (9 / 2-7,5-0,5 / 5,5) yerine kullanıcının değerleri (10 / 2-8-0,5 / 5,5) geçerlidir [C3D "Bütçe kuralının kontrolü"; EM6 Soru 2].

---

## 5. P3 — Aşama 1: Ana koşu

- Tasarım: K1–K6 (§2) [EM5 P3].
- **Run adı:** `main_s1_<koşu günü YYYYMMDD>` (config şablonu `main_s1_{run_date}`) [T93; CFG5 `main.json` satır 4]. `--resume` yalnız açık adla çalışır [UK §6 adım 4].
- **Seed namespace:** `pgg-main-s1` [T93; CFG6 `main.json` satır 79]. 0a ve 0b'nin namespace'lerinden ayrıdır.
- **Config aşaması:** `"stage": "1"`; bu aşamada `--allow-code-change` reddedilir (§10.3) [T95; CFG6 satır 4].
- **Çağrı sayısı (model başına):** grup 480 × G, izole 240, kural anlama 48 × G + 48 [DRY5]. G = 16 (DeepSeek, GPT): 7680 + 240 + 816 = 8736; G = 10 (Mistral): 4800 + 240 + 528 = 5568; toplam 8736 + 5568 + 8736 = **23 040** [C3D; sağlama hesap].
- `cost_calibration`: `configs/cost_calibration_minipilot.json`, sha256 `d26eb410…c8` (yalnız fiyat tahmini; isteği değiştirmez) [T93; CFG6 satır 88–91].
- Çıktılar `runs_dir/<run>/` altına (worktree dışı): `runs_dir` = `/Users/karbon/Desktop/Veri Bilimi/complexity-prj/orc/data/projects/PublicGoods/workspace/runs` [CFG6 satır 78] (P8 §10.4).
- Aynı run adıyla ikinci yeni koşu yapılmaz; kesintide yalnız `--resume` [PMP §2.3].

---

## 6. P4 — Hipotezler (her yönüyle; birim = grup)

### 6.0 Ortak tanımlar

- **Birim:** grup (oturum). Homojen grupta 4 ajan aynı kartı taşır [EM5 P4].
- **Hücre:** model × kart. Hücre başına G grup.
- **Grup ölçüleri:** m10 = 10 tur × 4 ajan katkısının ortalaması; r(t) = t. turdaki 4 katkının ortalaması (t = 1, 9, 10) [T92 Bölüm 1 tanımları].
- **Hücre değeri:** hücredeki G grubun ölçüsünün ortalaması.
- **D (şehir çifti farkı):** D = hücre(A) − hücre(B), aynı model ve aynı stil.
- **Şehir çiftleri ve "insan yönü":** çift A − B, Herrmann N→P tur 1–10 ortalamasında **A > B** olacak biçimde yazılır; bu yüzden "insan yönü" = D > 0. Değerler T92'den (N→P, filtre yok) [T92 Bölüm 2]:

| çift (A − B) | Herrmann tur 1–10: A | B | insan farkı A − B (çıkarma) |
|---|---|---|---|
| Copenhagen − Athens | 11.534 | 6.357 | 5.177 |
| Copenhagen − Riyadh | 11.534 | 7.629 | 3.905 |
| Boston − Athens | 9.327 | 6.357 | 2.970 |
| Copenhagen − Boston | 11.534 | 9.327 | 2.207 |
| **Boston − Riyadh** | 9.327 | 7.629 | 1.698 |
| Riyadh − Athens | 7.629 | 6.357 | 1.272 |

Sıra (tur 1–10): Copenhagen > Boston > Riyadh > Athens; `data` filtresi hipotezleriyle (H5drop, H7) değişmiyor [T92 "Dört öncelikli şehrin sırası"]. EMİR 5'teki örnek çift (Boston − Riyadh) listede kalın.

- **"Var" kuralı:** |D| > 2 **ve** %95 CI 0'ı dışlıyor (Holm ailesi içinde düzeltilmiş p < 0,05; P5 §7.3). Aksi halde "fark yok".

### 6.1 H1 — Değer kartı yönü

- **Ölçü:** D_val = hücre(A_value) − hücre(B_value), m10 üzerinden; model başına; 6 şehir çiftinin her biri (§6.0 tablo). EMİR 5'in örneği: D_val = Boston_değer − Riyadh_değer [EM5 P4 H1].
- **Yönler (her çift, her model):**
  - **İnsan yönü:** D_val > 2 ve CI 0'ı dışlıyor (A > B, Herrmann'daki gibi).
  - **Ters yön:** D_val < −2 ve CI 0'ı dışlıyor (B > A).
  - **Fark yok:** yukarıdakilerin hiçbiri.
- Ek alt not (etiket değil): "fark yok" satırlarında %95 CI tamamen [−2, 2] içindeyse "eşdeğerlik sağlandı", değilse "ayırt edilemedi".
- Betimsel eşlik eden ölçüler (karar yok): D_val'in izole karşılığı D_iso (5 nokta ortalaması); minimal kart için D_min (karşılaştırma ölçütü).
- Bağlam (karar değil): mini-pilotta Boston − Riyadh değer çiftinde DeepSeek ve Mistral ters yöndeydi (ör. DeepSeek abstract_v3 D_grup(1) = −16,25; Mistral D_grup(10) = −20,00) [MPA §5.4]. Bu veri ana analize girmez.

### 6.2 H2 — Olgusal (mahkeme süresi) kart yönü

- **Ölçü:** D_fac = hücre(A_factual) − hücre(B_factual), m10; aynı 6 çift; model başına [EM5 P4 H2].
- **Yönler:**
  - **Herrmann'daki yönü verir:** D_fac > 2 ve CI 0'ı dışlıyor.
  - **Ters yön:** D_fac < −2 ve CI 0'ı dışlıyor.
  - **Fark yok:** diğer durumlar (eşdeğerlik alt notu H1'deki gibi).
- **Betimsel ek etiket (hipotez değil):** kartın kendi olgusunun yönü, yani "kısa mahkeme süresi → yüksek katkı". Süreler: ABD 444, Danimarka 485, Suudi Arabistan 575, Yunanistan 1,711 gün [D2 §2]. Altı çiftin beşinde süre yönü Herrmann yönüyle aynıdır; yalnız **Copenhagen − Boston**'da ayrışır (Boston'un süresi daha kısa, Herrmann'da Copenhagen yüksek) (bu görevde yapılan sıra karşılaştırması) [D2 §5.1 risk 2]. "Herrmann yönü" ile "olgunun yönü" yalnız bu çiftte ayrıştırılabilir.

### 6.3 H3 — Etkileşim: fark büyür / söner / korunur

- **Ölçü:** D(t) = hücre(A, r(t)) − hücre(B, r(t)); t = 1, 9, 10. **Δ = |D(10)| − |D(1)|** ve bootstrap CI'si; ayrıca Δ9 = |D(9)| − |D(1)| [EM5 P4 H3, P5].
- **Kapsam:** H1'in 6 değer çifti ve H2'nin 6 olgusal çifti; **model başına ayrı** (DeepSeek, Mistral, GPT). Minimal kartın 6 çifti betimsel olarak verilir.
- **Yönler:**
  - **Büyür:** Δ > 2 ve Δ'nın CI'si 0'ı dışlıyor, **ve** D(10) ile D(1) aynı işarette.
  - **Söner:** Δ < −2 ve Δ'nın CI'si 0'ı dışlıyor; **ya da** işaret değişti (D(1) ve D(10) ikisi de "var" ve zıt işaretli; bu durum "söner (işaret döndü)" diye ayrıca adlandırılır).
  - **Korunur:** büyür ve söner koşullarının hiçbiri sağlanmıyor. Alt not: Δ'nın CI'si [−2, 2] içindeyse "korunur — eşdeğerlik sağlandı", değilse "korunur — ayırt edilemedi".
- **D(9):** aynı sınıflama Δ9 ile; 9 ile 10 ayrışırsa "son tur etkisi" notu [PMP §5.3].
- **Ek not:** |D(1)| ≤ 2 ve D(10) "var" ise "grup içinde doğan fark" [PMP §5.3].
- Model başına D(1), D(9), D(10) değerleri ve CI'leri tabloda ayrı ayrı verilir.

### 6.4 H4 — İzole tepki fonksiyonu grup davranışını öngörür mü (Flint mantığı)

- **Fikir:** izole çizelgeden etkileşimsiz bir grup yörüngesi simüle edilir; gözlenen grup yörüngesiyle karşılaştırılır [EM5 P4 H4; BG §4; G8 §2 "Kritik nokta"].
- **Simülasyon algoritması (önceden sabit):**
  1. **Tepki fonksiyonu f (model × kart):** her izole nokta x ∈ {0, 5, 10, 15, 20} için f(x) = 4 tekrarın katkı ortalaması. Noktalar arası **doğrusal enterpolasyon** (başkalarının ortalaması hep [0, 20] içinde kalır). — **KULLANICI KARARI** (varsayılan: doğrusal enterpolasyon; alternatif: en yakın nokta).
  2. **Başlangıç:** her gözlenen grup g için ajanların **gözlenen 1. tur katkıları** c_i(1). Simülasyon gözlenen gruba eşlenir. — **KULLANICI KARARI** (varsayılan: gözlenen 1. tur; alternatif: hücrenin 1. tur ortalaması).
  3. **Güncelleme (ajan düzeyi, belirlenimci):** t = 2…10 için c_i(t) = f( (Σ_{j≠i} c_j(t−1)) / 3 ). Yuvarlama yok. — **KULLANICI KARARI** (varsayılan: belirlenimci, yuvarlamasız; alternatif: tekrarlardan örnekleme ile olasılıklı simülasyon).
  4. Sonuç: her g için simüle edilmiş tur 2–10 grup ortalaması S_g.
- **Uyum ölçütü:** O_g = gözlenen tur 2–10 grup ortalaması; Δ4 = hücre içinde (O_g − S_g)'nin G grup üzerinden ortalaması. Bootstrap'te hem gruplar hem (f'nin belirsizliği için) her noktadaki 4 izole tekrar iadeli yeniden örneklenir. — **KULLANICI KARARI** (varsayılan: iki düzeyli yeniden örnekleme; alternatif: yalnız gruplar).
- **Yönler (model × kart, 36 hücre):**
  - **Yukarı:** Δ4 > 2 ve CI 0'ı dışlıyor (grup, etkileşimsiz tahminden yüksek katkı veriyor).
  - **Aşağı:** Δ4 < −2 ve CI 0'ı dışlıyor.
  - **Uyumlu:** diğer durumlar; alt not CI ⊂ [−2, 2] ise "uyumlu — eşdeğerlik sağlandı", değilse "uyumlu — ayırt edilemedi".
- İkincil (betimsel): yalnız tur 10 için aynı karşılaştırma.
- **Bilinen sınır:** f "round 5 of 10" bağlamında ölçülür ama tur 2–10'a uygulanır; son tur etkisini yakalamaz (tahmin). Flint'te izole politika bellek-koşullu ve logit'ten çıkarılıyor; bizde yalnız "önceki turdaki başkalarının ortalaması"na koşullu ve örneklemeyle tahmin ediliyor [G8 §2–§3].

### 6.5 H5 — Model tutarlılığı

- **Ölçü:** H1'in 6 çifti ve H3'ün 12 çifti (6 değer + 6 olgusal) için üç modelin etiketleri [EM5 P4 H5].
- **Yönler (her çift):**
  - **Aynı:** üç model aynı etiketi alıyor (H1: insan yönü / ters yön / fark yok; H3: büyür / söner / korunur).
  - **Farklı:** en az bir model farklı etiket alıyor.
  - Bir model durmuş ya da hücre eksikse (ör. alt tavan, geçersiz tavanı) o çift için **"belirlenemedi"** yazılır; iki modelle "aynı" denmez.
- Özet: H1 ve H3 için "aynı" çift sayısı / toplam çift. Test yok; H1 ve H3 etiketlerinden türetilir.

---

## 7. P5 — İstatistik planı (önceden sabit)

### 7.1 Birim ve tahmin

- Analiz birimi **grup ortalaması** (izole kolda çizelge) [EM5 P5].
- Hücre farkları (D, Δ, Δ4) için **grup düzeyinde bootstrap**: her bootstrap tekrarında her hücrenin G grubu iadeli yeniden örneklenir (iki hücre bağımsız); **10 000 tekrar**; yüzdelik %95 CI [EM5 P5].
- **Sabit seed:** `llm_client.stable_seed("pgg-main-s1-analysis", hipotez, model, çift)` (crc32) [CL "Seeds"; depo `llm_client.py` satır 238–241]. Seed dizgisi öneridir.

### 7.2 "Var" kararı

Hem pratik eşik **|D| > 2** hem de **%95 CI'nin 0'ı dışlaması** [EM5 P5]. Eşik 2 puan, mini-pilottaki e = 2 ile aynıdır [PMP §5.2].

### 7.3 Çoklu karşılaştırma: model içinde Holm

- **Bootstrap p değeri:** p = min(1, 2 × min(P*(D* ≤ 0), P*(D* ≥ 0))).
- **Holm, model içinde, hipotez başına bir aile** (varsayılan; **KULLANICI KARARI**, alternatif: model başına H1–H4 tek aile, 36 test):

| aile (her model için ayrı) | test sayısı |
|---|---|
| H1: 6 değer çifti, D_val (m10) | 6 |
| H2: 6 olgusal çifti, D_fac (m10) | 6 |
| H3: 12 çift (6 değer + 6 olgusal), Δ = \|D(10)\| − \|D(1)\| | 12 |
| H4: 12 kart, Δ4 | 12 |
| H5 | test yok (türetilir) |

- "CI 0'ı dışlıyor" koşulu aile içinde **Holm-düzeltilmiş p < 0,05** olarak uygulanır. Raporda düzeltmesiz %95 CI ve düzeltilmiş p birlikte verilir.
- İkincil ve betimsel ölçüler (D(9), Δ9, D_iso, minimal çiftler, tur 10 H4) düzeltilmez ve "betimsel" diye işaretlenir.

### 7.4 H3 ölçüsü

Δ = |D(10)| − |D(1)|; her bootstrap tekrarında |D*(10)| − |D*(1)| hesaplanır; CI bu dağılımdan [EM5 P5].

### 7.5 Duyarlılık analizleri (karar değiştirmez; ana etiketin yanında verilir)

1. **Yalnız kural anlaması tam birimler:** grup biriminde dört ajanın ikişer sorusu doğru; izole çizelgede iki soru doğru [EM5 P5; PMP §6.4].
2. **reasoning_capped hariç:** reasoning_capped satırı içeren grup birimleri çıkarılır (grup ortalaması tek satır çıkarınca bozulduğu için birim düzeyinde); izole kolda yalnız o nokta çıkarılır (tanım önerisi) [EM5 P5].
3. **Yeniden kullanılan cevap içeren birimler hariç:** #90 mekanizmasıyla önceki segmentten yeniden kullanılmış en az bir cevabı olan birimler çıkarılır [EM5 P5; T90 M1].

Her duyarlılık analizinde çıkarılan birim sayısı model × hücre başına raporlanır. Etiket ana analizden farklıysa ikisi de yazılır; ana etiket değişmez.

### 7.6 Analiz kodu

Analiz betiği Aşama 1 verisi açılmadan yazılır ve sentetik veriyle test edilir (öneri). 0a / 0b verisi yalnız betiğin çalıştığını sınamak için kullanılabilir; sayıları sonuç olarak raporlanmaz.

---

## 8. P6 — İnsan verisi çapası (Herrmann, Thöni & Gächter 2008)

### 8.1 Alt küme tanımı

- **Önerilen: N koşulunda N→P sırasındaki oturumlar** [EM5 P6]. Yayımlanmış veride `secseq == 0` (README rtf:88–90); do dosyasındaki `np` ile eşdeğerliği gözlem düzeyinde kontrol edildi [T92 Bölüm 2 (b)].
- Sayımlar: N koşulu 1076 katılımcı, 269 grup; bunların **920**'si N→P sırasında; gruplar 4 kişi [T92].
- **Not (tutarsızlık):** BG §6 "900 subjects are in plain N→P sessions" diyor; T92 920 sayıyor. Fark 20; Chengdu'nun iki kimliğe bölünmüş oturumunun (20 denek) birleştirilmiş kimlikle N→P sayılmasından gelebilir (tahmin; BG §6 ve T92 "Denek anahtarı").
- Tüm N ile N→P yalnız üç şehirde ayrışır (Minsk +0.967, Samara +0.976, St. Gallen −0.464; tur 1–10) [T92 "Varyantlar arası fark özeti"]; dört öncelikli şehirde fark yok.

### 8.2 Şehir ortalamaları (N→P; `data` filtresinin üç işlemselleştirmesi)

| şehir | filtre | tur 1 | tur 1–10 | tur 10 | grup / katılımcı |
|---|---|---|---|---|---|
| Boston | yok / H5drop / H7 | 12.964 | 9.327 | 2.946 | 14 / 56 |
| Copenhagen | yok / H5drop / H7 | 14.103 | 11.534 | 5.294 | 17 / 68 |
| Athens | yok, H7 | 8.136 | 6.357 | 5.364 | 11 / 44 |
| Athens | **H5drop** | 7.125 | 6.325 | 7.688 | 4 / 16 |
| Riyadh | yok / H5drop / H7 | 7.958 | 7.629 | 5.875 | 12 / 48 |

Kaynak: T92 `p6_herrmann_N_sehir.csv` (README tabloları). H5drop = bölünmüş oturumlar çıkarılır; H7 = yalnız 10 dönemi tam kayıtlar [T92].

**Sıra (yüksekten düşüğe)** [T92]:
- Tur 1: Copenhagen > Boston > Athens > Riyadh (filtre yok, H7); H5drop'ta Athens ve Riyadh yer değiştirir.
- Tur 1–10: Copenhagen > Boston > Riyadh > Athens (üç filtrede aynı).
- Tur 10: Riyadh > Athens > Copenhagen > Boston (filtre yok, H7); H5drop'ta Athens birinci.

### 8.3 Karşılaştırmanın niteliği

- **Yalnız yön ve sıra düzeyinde, betimsel** [EM5 P6]. Model katkılarının sayısal düzeyi insan değerleriyle karşılaştırılmaz; test yapılmaz.
- Kullanım: (a) H1/H2'deki "insan yönü" işaretinin tanımı (§6.0); (b) her model ve stil için dört şehrin m10 sırasının Herrmann tur 1–10 sırasıyla yan yana verilmesi. Sıra uyumu için bir özet (ör. Spearman) yalnız betimsel verilebilir (öneri).

### 8.4 Sınırlılıklar

1. **`data` filtresi belirsizliği:** do dosyaları `data` değişkenini filtre olarak kullanıyor (ör. SOM.do:305 `keep if data`), ama bu değişken **yayımlanmış CSV'de de .dta'da da yok**; .dta'nın 22 değişkeni CSV'nin 22 sütunuyla aynı [T92 (c); `p6_meta.json`: `dta_data_degiskeni = false`; BG §6]. "Filtre uygulanmış" hal doğrudan hesaplanamaz; iki hipotezle işlemselleştirildi (H5drop, H7).
2. **Athens:** H5drop ile katılımcı 44 → 16, grup 11 → 4; tur 1 −1.011, tur 1–10 −0.032, tur 10 +2.324 [T92 "Athens"]. Tur 1 ve tur 10 sıraları filtreye duyarlı; tur 1–10 sırası değil. Bu yüzden H1/H2 çiftleri tur 1–10 üzerinden tanımlandı (§6.0).
3. **Küçük insan farkları:** Boston − Riyadh (1.698) ve Riyadh − Athens (1.272) farkları, bizim "var" eşiğimizin (|D| > 2) altında (§6.0). Bu çiftlerde "insan yönü" yalnız işaret anlamındadır.
4. **D2 S6 sonucu (Suudi verisi):**
   - **Hüküm: Suudi Enforcing Contracts süresi (575 gün) usulsüzlükten etkilenmemiş görünüyor; güvenilirlik orta-yüksek** [S6 §5].
   - Dayanak: Dünya Bankası GIA doğrulama raporu (8 Aralık 2020), Ek 1, s. 9: Suudi Arabistan için düzeltilen göstergeler yalnız "Legal Rights (Getting Credit) / Strength of Legal Rights Index" (madde 4) ve "Paying Taxes / Time (hours)" (madde 5); "contract" yalnız Azerbaycan için geçiyor (madde 2) [S6 §3]. DB API verisi (lastupdated 2021-08-18) 2015–2019 her yıl 575; DB arşiv profili DB2020 için 575 [S6 §4].
   - **PDF metne çevrilemedi:** Aralık 2020 inceleme PDF'i (21 sayfa) ve WilmerHale raporu (şifreli) metne çevrilemedi; S6'nın "iki belgeyi birebir okuma" koşulu **karşılanmadı** [S6 §0–§2]. Kapatmak için öneri: poppler kurulu ortamda `pdftotext -layout` (WilmerHale için önce `qpdf --decrypt`) [S6 §6].
   - Yan bulgu: arşivin Suudi genel skoru (62 / 71.6) düzeltilmemiş değer; 575'i etkilemez [S6 §4].
5. **Boston 444 Boston'a ait değil:** ABD değeri NYC (370) ve LA (555) birleşimi; "In your country" bunu karşılıyor [D2 §2; S6 §4 yan bulgu 2].
6. **Yıl farkı:** DB2020 verisi Mayıs 2019'da toplandı [D2 §2]; Herrmann oturumlarının yılı bu görevde doğrulanmadı; kart 2026'da kullanılıyor [D2 §5.1 risk 4].
7. Herrmann'ın şehir ortalamaları 2008 makalesinin şekilleriyle henüz eşleştirilmedi (PDF 403) [BG §6].

---

## 9. P7 — Grup sayısı ve bütçe (kullanıcı kararları 2026-10-11, §13)

### 9.1 Kalibrasyon

- Dry-run, mini-pilotun gerçek token dağılımıyla kalibre edildi: `configs/cost_calibration_minipilot.json` (model × çağrı türü ortalama ve p95 token) [T93; DRY5].
- Mini-pilotun gerçekleşen kapsamıyla tahmin 3,8403, gerçek 4,0843 USD (oran 0,9403); Mistral'da oran 1,0006 [DRY5].
- **Mistral eksik veriyle kalibre:** 600 planlı satırın 380'i [DRY5; PMP T1].
- **p95 üst sınırı:** tek tek çağrı p95'lerinin toplamı; toplamın p95'i değil, çok temkinli [DRY5].
- **Cevap biçimi (#95 C2):** istem uzunluğu tek fonksiyonla (`_prompt_chars`) cevap talimatıyla birlikte, llm_client'ın gönderdiği haliyle ölçülür; dry-run, Aşama 1 kapısı ve `deadline_estimate` aynı fonksiyonu kullanır. Kalibrasyon schema_text ile ölçüldü; A/B farkı istem uzunluğundan ölçeklendi. B'nin `response_format` içinde gönderdiği şema istem uzunluğuna katılmadı (sağlayıcının nasıl saydığı bilinmiyor) [T95].

### 9.2 Aşama 1 dry-run (G: DeepSeek 16, GPT 16, Mistral 10; #96)

**Biçim A (`--answer-format example_object`)** — oyun: 4 ajan × 10 tur; izole `fixed_round` tur 5; noktalar [0, 5, 10, 15, 20] × 4 tekrar; kural anlama açık [C3D]:

| model | G | kol | çağrı | ortalama (USD) | p95 üst sınır (USD) |
|---|---|---|---|---|---|
| deepseek | 16 | grup (katkı) | 7680 | 5,2404 | 19,8413 |
| deepseek | 16 | izole | 240 | 0,5481 | 1,1961 |
| deepseek | 16 | kural anlama | 816 | 0,1239 | 0,1526 |
| **deepseek** | 16 | **toplam** | **8736** | **5,9124** | **21,1899** |
| mistral | 10 | grup (katkı) | 4800 | 35,3501 | 60,8953 |
| mistral | 10 | izole | 240 | 1,8997 | 3,0994 |
| mistral | 10 | kural anlama | 528 | 2,5237 | 3,4700 |
| **mistral** | 10 | **toplam** | **5568** | **39,7735** | **67,4647** |
| gpt | 16 | grup (katkı) | 7680 | 1,0956 | 1,8477 |
| gpt | 16 | izole | 240 | 0,0263 | 0,0326 |
| gpt | 16 | kural anlama | 816 | 0,0863 | 0,0921 |
| **gpt** | 16 | **toplam** | **8736** | **1,2082** | **1,9724** |
| **TOPLAM** | | | **23040** | **46,8940** | **90,6270** |

**Biçim B (`--answer-format json_schema_strict`)** [C3D]:

| model | G | kol | çağrı | ortalama (USD) | p95 üst sınır (USD) |
|---|---|---|---|---|---|
| deepseek | 16 | grup (katkı) | 7680 | 5,2552 | 19,8612 |
| deepseek | 16 | izole | 240 | 0,5485 | 1,1965 |
| deepseek | 16 | kural anlama | 816 | 0,1262 | 0,1548 |
| **deepseek** | 16 | **toplam** | **8736** | **5,9298** | **21,2125** |
| mistral | 10 | grup (katkı) | 4800 | 35,4543 | 61,0365 |
| mistral | 10 | izole | 240 | 1,9044 | 3,1042 |
| mistral | 10 | kural anlama | 528 | 2,5402 | 3,4868 |
| **mistral** | 10 | **toplam** | **5568** | **39,8989** | **67,6275** |
| gpt | 16 | grup (katkı) | 7680 | 1,1164 | 1,8759 |
| gpt | 16 | izole | 240 | 0,0269 | 0,0332 |
| gpt | 16 | kural anlama | 816 | 0,0894 | 0,0953 |
| **gpt** | 16 | **toplam** | **8736** | **1,2327** | **2,0043** |
| **TOPLAM** | | | **23040** | **47,0614** | **90,8443** |

*Not (#95 C2): kalibrasyon schema_text ile ölçüldü; A/B farkı istem uzunluğundan ölçeklendi.*

- Kapı 52: A 46,8940, B 47,0614 → **GEÇER** [C3D].
- Mistral payı (ortalama, hesap): A 39,7735 / 46,8940 = %84,8; B 39,8989 / 47,0614 = %84,8.
- **Tüm aşamalar, ortalama (hesap):** iki 0a koşusu 1,7680 + 0b + Aşama 1 = A ile 1,7680 + 4,8518 + 46,8940 = **53,5138**; B ile 1,7680 + 4,8681 + 47,0614 = **53,6975 USD**.

### 9.3 Güç hesabı: hücre içi grup arası SD ve CI genişliği (#97)

**Kaynak ve yöntem** [GUC2 §1–§2, §4]:
- SD, grup başına 10 tur ortalaması (m10) üzerinden, **iki pilotun** geçerli satırlarından hesaplandı: pilot v2'den 1620 geçerli satır (6 superseded birim, 152 satır hariç); mini-pilottan DeepSeek 1200, GPT 1200, Mistral 380 satır. Yalnız grup kolu katkı satırları; yalnız 10 turu tam gruplar (92 grubun 91'i). 48 hücrenin 43'ünde en az 2 tam grup olduğu için SD hesaplanabildi. Hücre = pilot × model × çerçeve × kart.
- **Havuzlanmış SD** = √(hücre varyanslarının ortalaması); her hücrede 2 grup olduğu için df ağırlıklı havuzla aynı.
- **Analitik %95 CI yarı genişliği** = 1,96 × SD × √(2/G) (iki bağımsız hücre, eşit varyans, normal yaklaşım).
- **Bootstrap:** her (senaryo, yöntem, G) için 1000 sentetik veri kümesi × grup düzeyinde 10 000 tekrar; sabit seed (taban 20261011). "0'ı dışlama oranı" = CI'nin 0'ı dışladığı kümelerin oranı. Değerler [0, 20] aralığına kırpılmadı. Script iki kez çalıştırıldı; 8 çıktı dosyasının sha256'sı aynı [GUC2; #97 sonucu].

**Model başına SD ve üst yöneticinin ön hesabıyla karşılaştırma** [GUC2 §2–§3]:

| model | SD hesaplanan hücre | grup | havuzlanmış SD | en büyük hücre SD'si | SD = 0 hücre | ön hesap | tutuyor mu | Aşama 1 G |
|---|---|---|---|---|---|---|---|---|
| DeepSeek | 18 | 36 | **0,887** | 2,652 | 7 | 0,89 (18 hücre) | evet | 16 |
| GPT | 18 | 36 | **2,507** | 6,541 | 5 | 2,51 (18 hücre) | evet | 16 |
| Gemini (yalnız referans; ana deneyde yok) | 6 | 12 | **3,349** | 6,205 | 0 | 3,35 (6 hücre) | evet | – |
| Mistral | 1 (2 tam gruplu tek hücre, df 1) | 2 | **bilinmiyor** | – | – | bilinmiyor | – | 10 |

- **Mistral:** mini-pilotta yalnız bir hücrede iki tam grup var; bu tek hücrenin değeri güvenilir bir SD tahmini değildir ve güç hesabında kullanılmaz [GUC2 §2 "tek hücre, güvenilmez"; EM6 P-b]. Mistral için en kötü durum senaryosu (SD = 9) esas alınır.
- Hücre SD'lerinin ortalaması, medyanı ve kapsam kırılımları (pilot v2 / mini-pilot / çerçeve) GUC2 §2'de.

**Senaryolar: yarı genişlik ve 0'ı dışlama oranı (normal sapmalı simülasyon)** [GUC2 §4.1]:

| senaryo | SD | analitik yarı genişlik G = 10 / G = 16 | bootstrap yarı genişlik medyanı G = 10 / G = 16 | fark 10: 0'ı dışlama G = 10 / G = 16 | fark 5: 0'ı dışlama G = 10 / G = 16 |
|---|---|---|---|---|---|
| DeepSeek havuzlanmış | 0,887 | 0,778 / 0,615 | 0,733 / 0,585 | 1,000 / 1,000 | 1,000 / 1,000 |
| DeepSeek en büyük hücre | 2,652 | 2,324 / 1,838 | 2,191 / 1,758 | 1,000 / 1,000 | 0,985 / 1,000 |
| GPT havuzlanmış | 2,507 | 2,198 / 1,737 | 2,045 / 1,668 | 1,000 / 1,000 | 0,986 / 0,999 |
| GPT en büyük hücre | 6,541 | 5,733 / 4,533 | 5,327 / 4,346 | 0,926 / 0,992 | 0,474 / 0,608 |
| Gemini havuzlanmış (referans) | 3,349 | 2,935 / 2,321 | 2,690 / 2,228 | 1,000 / 1,000 | 0,931 / 0,989 |
| **En kötü durum, normal** | 9 | 7,889 / 6,237 | 7,404 / 5,963 | **0,730 / 0,887** | **0,293 / 0,385** |
| **En kötü durum, iki modlu (±9)** | 9 | 7,889 / 6,237 | 7,200 / 5,625 | **0,736 / 0,891** | **0,257 / 0,402** |

- Bu satırların hepsinde "CI 0'ı dışlıyor **ve** |D̂| > 2" oranı, yalnız "CI 0'ı dışlıyor" oranıyla aynı [GUC2 §4.1].
- Gözlenen artıklardan yeniden örnekleme (havuzlanmış senaryolar): DeepSeek fark 10 ve 5'te iki G'de 1,000; GPT G = 10'da 1,000 / 0,991, G = 16'da 1,000 / 0,999 [GUC2 §4.1].
- **Gerçek fark 0 iken** (referans; CI'nin 0'ı dışlama oranı, G = 10 / G = 16): DeepSeek havuzlanmış 0,070 / 0,073; GPT havuzlanmış 0,089 / 0,051; en kötü durum normal 0,070 / 0,077; iki modlu 0,042 / 0,040 [GUC2 §4.2].

**Seçilen G'ye göre okuma (sayılar yukarıdaki tablodan):**
- **DeepSeek (G = 16):** havuzlanmış SD ile 10 ve 5 puanlık fark 1,000 oranında; en büyük hücre SD'siyle de 1,000 / 1,000.
- **GPT (G = 16):** havuzlanmış SD ile 1,000 / 0,999; en büyük hücre SD'siyle 0,992 / 0,608.
- **Mistral (G = 10):** SD bilinmiyor; en kötü durumda (SD = 9) yarı genişlik 7,889, 0'ı dışlama oranı 10 puanda 0,730 (iki modlu 0,736), 5 puanda 0,293 (iki modlu 0,257).

**Sınırlar:**
- Simülasyon iki hücre farkı (H1/H2 tipi D) içindir; H3'ün Δ = |D(10)| − |D(1)| ölçüsü ve H4'ün Δ4'ü ayrıca simüle edilmedi.
- Simülasyondaki CI düzeltmesiz %95 CI'dir; §7.3'teki Holm düzeltmesi uygulanınca oranlar daha düşük olur (tahmin).
- Gerçek fark 0 iken oranlar bazı senaryolarda 0,05'in üstünde (ör. GPT havuzlanmış G = 10'da 0,089) [GUC2 §4.2]; küçük G'de yüzdelik bootstrap CI'sinin dar kalmasından kaynaklanıyor olabilir (tahmin).
- SD'ler Boston/Riyadh kartlarından, abstract_v3 / story / pilot v2 çerçevelerinden geldi; abstract_v4, Copenhagen/Athens kartları ve yeni olgusal kart için varyans bilinmiyor (tahmin). DeepSeek'te 18 hücrenin 7'sinde, GPT'de 5'inde SD = 0 [GUC2 §2].

### 9.4 Tavanlar ve kapı (seçilen G: 16 / 16 / 10)

| aşama | sert tavan | alt tavanlar DeepSeek / Mistral / GPT | kapı | ortalama A / B | kapı kararı |
|---|---|---|---|---|---|
| 0a (koşu başına; A ve B aynı) | 1,6 | 0,3 / 1,3 / 0,1 | 1,0 | 0,8822 / 0,8858 | geçer |
| 0b (kullanıcının değerleri) | 10 | 2 / 8 / 0,5 | 5,5 | 4,8518 / 4,8681 | geçer |
| Aşama 1 | 91 | 22 / 68 / 3 | 52 | 46,8940 / 47,0614 | geçer |

Kaynak: T96; C3D; CFG6. Kural: sert tavan ≥ toplam p95; alt tavan ≥ model p95; kapı = ortalama × 1,1; A ile B'den büyüğü alınıp yukarı yuvarlandı (0a: 0,1 USD; Aşama 1: 1 USD adım) [EM6 Soru 2; T96].

Sağlama (hesap, B değerleriyle): Aşama 1 — 47,0614 × 1,1 = 51,77 → 52; toplam p95 90,8443 → 91; DeepSeek 21,2125 → 22; Mistral 67,6275 → 68; GPT 2,0043 → 3 ✓. 0a — 0,8858 × 1,1 = 0,9744 → 1,0; 1,5679 → 1,6 ✓. 0b — 4,8681 × 1,1 = 5,3549 ≤ 5,5; 8,9603 ≤ 10 ✓.

- **Mistral'ın Aşama 1 alt tavanı dar:** 68 USD, B p95'inin (67,6275) yalnız 0,37 USD üstünde [T96].
- **Kapı aşılırsa koşu yapılmaz, raporlanır; hiçbir kol ya da model çıkarılmaz** [PMP §8.1].
- Uçuştaki çağrılar tavanı biraz aşabilir; mini-pilotta en kötü durum ≈ 0,41 USD hesaplanmıştı (tahmin) [PMP §8.3].

### 9.5 Mistral: şema geri yazma sorunu ve E3 uygunluğu için 0a'nın rolü

- Mini-pilotta Mistral'ın **28 geçersiz** yanıtı: 25'i istemdeki JSON şemasını aynen geri yazma, 3'ü şema içinde cevap; 28 > 27 (0,05 × 540) olduğu için `invalid_rate_cap` ile durdu; 600 planlı satırın 380'i var [PMP T1; MUH5 madde 5].
- Aşama 1'de Mistral'ın karar çağrısı geçersiz sınırı (G = 10): 0,05 × (480 × 10 + 240) = 252 (hesap). Mini-pilottaki oran sürerse Mistral'ın Aşama 1'de durması olasıdır (tahmin).
- **0a'nın rolü:** şema metni yerine örnek nesne (A) ya da zorlanan şema (B) bu sorunu gideriyor mu, ilk kez 0a gösterir [EM5 M4, P1; CT]. Yeni 0a grup turlarını da içerdiği için Mistral'ın geçersizlerinin çoğunun çıktığı istem türü de sınanır; ancak 0a 3 turludur (§3.1 sınırlılık).
- **E3 uygunluğu:** mini-pilotta Mistral'da U1–U3'ün hiçbiri gerçekleşmedi, ama değerlendirme eksik veriyle (380/600) betimseldi [MPA §0]. Seçilen biçimde Mistral'ın 0a/0b geçersiz oranı ≥ %5 ise "Aşama 1'de geçersiz tavanıyla durma riski" diye raporlanır. **Otomatik çıkarma yapılmaz; karar kullanıcınındır** [PMP §7].

---

## 10. P8 — Durdurma ve sürdürme kuralları

### 10.1 Başlamama koşulları (çağrı yapılmadan)

Mini-pilottaki gibi [PMP §9.2], bu belgenin değerleriyle:
- `prereg_approved` true değil (şu an false [CFG6 satır 3]).
- Kullanıcı o aşama için "BAŞLA" demedi (§10.4) [EM6 Bölüm 3].
- Kalibre dry-run ortalaması kapıyı aşıyor (0a 1,0; 0b 5,5; Aşama 1 52) [CFG6].
- Çerçeve, kart ya da `cost_calibration` sha256'sı config'tekiyle tutmuyor [T93].
- Yer tutucu alan var: şu an yalnız `answer_format` `main.json` ve `main_s0b.json`'da yer tutucu (0a ile seçilir) [CFG6 `main.json` satır 57, `main_s0b.json` satır 52]. G, `budget_usd`, `model_budget_usd`, `expected_cost_gate_usd` artık dolu (§9.4).
- `runs_dir` geçersiz (mutlak değil, yok ya da worktree içinde); kod kirli ya da sürümü bilinmiyor (`git_commit` / `CODE_VERSION.json`) [PMP §9.1 A5].
- `--allow-code-change` config'e yazılmışsa ya da `stage` "1" olan (veya `stage`'i olmayan) bir config'le verilmişse koşu başlamaz (yeni koşu dahil) [T95].

### 10.2 Durma koşulları

1. Birikmiş maliyet sert tavana ulaştı (0a 1,6; 0b 10; Aşama 1 91).
2. Bir modelin maliyeti alt tavanına ulaştı → yalnız o model durur, `model_stops` yazılır.
3. **0b ve Aşama 1:** bir modelde `n_invalid` + `n_parse_fail` > %5 × karar çağrısı (`invalid_rate_cap` 0,05) → yalnız o model durur; kural anlama geçersizleri sayılmaz [PMP §9.3; CFG6 `main.json` satır 92, `main_s0b.json` satır 87]. **0a'da bu sınır kapalıdır** (`invalid_rate_cap: null`); 0a'da bir çağrı `max_invalid` (8) sonrasında geçerli cevap alamazsa yalnız o model `format_failed` ile durur, diğerleri sürer (§3.1) [EM6 C3; T96].
4. İlk `finish_reason = length` (`stop_on_length` true) [CFG6 `main.json` satır 93]; `reasoning_capped` bu kural değildir.
5. İstekte `reasoning_effort` gönderildiği görülürse.
6. Sağlayıcı uyuşmazlığı deneme sınırını tüketti (0a'da da biçim hatası sayılmaz [T96]).
7. Mistral'da `model_version_changed` [CFG5 satır 84–87].
8. `RunAborted` ya da `stalled` → `--resume` (0a'da `format_failed` model `--resume`'da da durmuş kalır [T96]).

### 10.3 Sürdürme: kod sürümü kilidi ve yeniden kullanım (#90, #95)

- **Kod sürümü kilidi (EMİR 6 C1):** bir koşunun her segmenti ilk segmentinin kodunu çalıştırır. `--resume` ilk segmentin `git_commit`'inden farklı bir commit'le başlatılırsa **reddedilir** — önceki segmentten yeniden kullanılacak cevap olsun olmasın. Ret kilit dosyasından, herhangi bir yazmadan ve çağrıdan önce olur [EM6 C1; T95].
- **İstisna `--allow-code-change`:** yalnız komut satırından verilir (config'e yazılırsa koşu reddedilir) ve **yalnız analiz verisi olmayan koşularda** geçerlidir: config `"stage": "0a"` ya da `"0b"`. **Aşama 1'de (`"stage": "1"`) bayrak reddedilir** [EM6 C1; T95; CFG6 satır 4]. `stage` config kaydına girer; sürdürmede aşama değiştirilerek bayrak hakkı elde edilemez [T95].
- **İki sürüme yayılan birimler:** bayrakla devam edilince bu birimlerin yeni satırlarında `"code_change_span": true` ve `"code_commits": [A, B]`; özette `code_change_span_units` (birim, segmentler, commit'ler, satır sayısı), `n_code_change_span_units`, `n_code_change_span_rows`. Her segment kaydında `code_lock` alanı kararı tutar: same / allowed / refused / not_recorded [T95]. Önceki segmentteki satırlara işaret konamaz (dosya yalnız eklemeli); bunlar özetteki listeden tanınır [T95].
- İlk segmenti kod sürümü kaydetmemiş eski koşularda (A5 öncesi) kilit denetlenemez ("not_recorded"); `git_commit: null` kaydedilmiş segment reddedilir. Yeni kod her segmentte commit kaydettiği için 0a/0b/1'de bu bir boşluk değildir [T95].
- **İstek hash'iyle yeniden kullanım:** gönderilen istek gövdesinin `session_id` dışındaki her alanı (model, mesajlar ve eklenen cevap talimatı, max_tokens, response_format, provider gövdesi) kanonik JSON + sha256 ile hash'lenir; `answer_format` da hash'e girer [T90 M1, M4]. Yeniden kullanım yalnız aynı `git_commit`'li segmentten olur; `--discard-reuse-on-code-change` farklı commit'li cevapları `code_changed` olarak atar ve yeniden sorar [T90 M1]. Kod kilidinden sonra bu durum yalnız `--allow-code-change` ile sürdürülen bir 0a/0b koşusunda doğabilir (#95'te bu seçeneğin testi `stage` 0a/0b + bayrakla denetler hale getirildi) [T95]. Sürdürme aynı `_kod_<sha>` kopyasıyla yapılır [T90 "Riskler"; UK §6 adım 4].
- **Yeniden kullanılan cevap `is_valid`'den yeniden geçer;** geçmezse `reuse_invalid` olarak atılır, `n_reuse_invalid` ile sayılır ve yeniden sorulur [T90 M1].
- **Kilit her zaman bırakılır;** `status.json` yazılamasa bile; koşunun asıl hatası gizlenmez [T90 M3].
- **Model başına G:** `--resume` başka bir G (ya da `groups_per_cell_by_model`) ile başlatılırsa reddedilir [T96].
- Testler: 448 (#90) → 474 (#93) → 505 (#95) → 528 (#96), hepsi OK (§12.1).

### 10.4 Ücretli koşunun başlatılması

- **"BAŞLA" kuralı:** her aşama (0a, 0b, Aşama 1) ancak kullanıcı **o aşama için** "BAŞLA" dedikten sonra başlar. Her aşamadan sonra sonuç raporu yazılır; gerekiyorsa bu belgeye tarihli ek eklenir (0a: §3.4; 0b: §4.3) [EM6 Bölüm 3].
- Ücretli koşular **kullanıcının kendi Terminal'inden** `scripts/runctl.py start` ile başlatılır; **caffeinate varsayılan açık** (`--no-caffeinate` kapatır) [EM5 M3; T90 M3; UK §4, §6]. Sürdürmede bayrak runctl üzerinden geçirilir: `runctl.py start --resume ... -- --allow-code-change` (yalnız 0a/0b) [depo README].
- Adımlar (README "A paid run, step by step"; UK §6): kodu `_kod_<sha>` kopyasına sabitleme → anahtarı yalnız o terminale verme → dry-run ve kapı → `start --run <açık ad> --runs-dir …` → `status` ile izleme → gerekirse `stop` (orc sandbox'ından `stop_request.json`) → bitince dosyalar ve satır sayıları [UK §6].
- Orc koşuyu yalnız dosyalardan izler; gerçek koşuyu başlatmaz [UK §4].
- caffeinate'in varsayılan açık olması yalnız mock testle doğrulandı; gerçek Terminal'de denenmedi [T90 "Riskler"]. Kapak kapanınca Mac yine uyur [UK §7].
- **Veri kalıcılığı (kullanıcı onaylı kural):** her ücretli koşu ham logu (`raw_calls.jsonl`), sonuç `.jsonl`'u ve özet dosyalarını worktree dışındaki `runs_dir/<run>/` altına yazar; görev bitmeden dosyaların orada olduğu ve satır sayıları raporlanır, denetleyici kontrol eder; hesap kimliği içeren ham loglar commit'e girmez [PMP §9.4; kullanıcı notu].

### 10.5 Okunan yanıtların yeniden kullanımı ve sınırlılığı

- Kesinti olursa, önceki segmentte kabul edilmiş ve isteği bayt bayt aynı olan cevaplar yeniden sorulmaz, yeniden kullanılır (`<run>.accepted.jsonl`) [T90 M1–M2].
- Bu, mini-pilottaki "yeniden çekme" seçim etkisini azaltır: orada 100 kabul edilmiş yanıt atıldı ve **94 karar noktası** yeniden çekildi; 35 noktada atılan ve kabul edilen cevap farklıydı [PMP T2].
- **Sınırlılık:** yeniden kullanılan cevap önceki segmentten gelir (zaman farkı); uçuşta kesilip hiç dönmeyen çağrılar yine yeniden sorulur, yani uzun düşünen çağrılarda seçim etkisi tamamen kalkmaz (tahmin) [PMP T2 "Sınırlılık: uzun düşünen çağrılar"]. Duyarlılık analizi 3 (§7.5) yeniden kullanılmış cevap içeren birimleri çıkarır.

---

## 11. Sınırlılıklar

1. **Yeniden çekme seçim etkisi:** mini-pilotta 94 nokta (atılmadan yeniden istenen 7 ile 101) [PMP T2]; Aşama 1'de runctl ve yeniden kullanım bunu azaltır ama uçuşta kesilen çağrılar için sürer (§10.5).
2. **Modeller arası farklar:**
   - GPT'nin reasoning metni özet; mini-pilotta abstract_v3 karar satırlarının 191/540'ında boş [MPA §3.2]. E2a GPT'de yalnız rationale ile karşılaştırılabilir [PMP Ç2].
   - Aşama 1 maliyetinin ~%85'i Mistral'dan (§9.2); Mistral'ın tahmini eksik veriyle kalibre [DRY5].
   - Mistral'ın şema sorunu (§9.5) ve olası durması.
   - G modeller arasında farklı (DeepSeek ve GPT 16, Mistral 10); Mistral'ın CI'leri daha geniştir ve H5'te modeller farklı güçle karşılaştırılır (tahmin).
   - Sürüm denetimi yalnız Mistral'da durdurucu; DeepSeek ve GPT'de sürüm yalnız loglanır [CFG5 satır 84–87].
3. **Tanıma çok yüksek:** DeepSeek ve Mistral paradigmayı neredeyse her satırda adlandırıyor (537/540, 342/342) [MPA §3.2]. Sonuçlar "public goods oyununu tanıyan ajanların" davranışıdır; tanıma ortak değişken olarak kaydedilir, düzeltilmez.
4. **Sıcaklık gönderilmiyor:** modelin varsayılanı kullanılır; değeri bilinmiyor ve modeller arasında farklı olabilir (tahmin).
5. **İzole soru** sabit "round 5 of 10" bağlamındadır; H4 bu fonksiyonu bütün turlara uygular (§6.4). Mini-pilotta izole soru süren bir oyun gibi okundu [PMP okuma eki].
6. **Herrmann çapası:** `data` filtresi, Athens, küçük insan farkları, yıl farkı (§8.4).
7. **Olgusal kart:** DB süre sırası bir çiftte (Copenhagen − Boston) Herrmann sırasından farklı [D2 §5.1 risk 2]; Athens 1,711 diğerlerinin ~3–4 katı [D2 §5.1 risk 1]; Boston değeri ABD birleşik; S6 birebir okuma eksik; "lawsuit" ceza / yaptırım çağrıştırabilir [D2 §5.1 risk 6].
8. **Kart uzunluğu:** olgusal kart değer kartından en çok %10,6 kısa (Boston) [KD §6]; uzunluk ortak değişken.
9. **SD tahmini** 2 gruplu hücrelerden (pilot v2 + mini-pilot); Mistral için SD bilinmiyor; abstract_v4 ve yeni kartlar için varyans ölçülmedi (§9.3).
10. **0a bir biçim testidir:** istemler "ROUND k of 3" diyor, Aşama 1 istemleri 10 turlu; 0a'nın geçersiz oranı Aşama 1'inkini tam temsil etmeyebilir (tahmin). Bu yüzden 0b'de seçilen biçimin geçersiz oranı ayrıca raporlanır (§3.1, §4.3).
11. **p95 üst sınırı** çok temkinli; tavanlar bu yüzden yüksek önerildi [DRY5]. B'de `response_format` şeması istem uzunluğuna katılmadı (§9.1).
12. Yalnız homojen gruplar ve N koşulu; karma gruplar ve P, Aşama 2'de (§1.3).

---

## 12. Teslim özeti

### 12.1 Testler ve commit'ler

| görev | test sonucu | commit (orc/PublicGoods) | not |
|---|---|---|---|
| #90 (Bölüm 1, M1–M4) | **448 test, OK** (önce 421; 27 yeni: `tests/test_emir5_bolum1.py` 25, `tests/test_runctl.py` 2); yeni test dosyası 3 kez daha OK | `d8eafc9` | `tests/fixtures/request_hashes_811fdcc.json` değişmeden geçiyor; çıktı `workspace/gorev90_tests.txt` |
| #93 (Bölüm 2 dosyaları, P testleri, kalibrasyon, dry-run) | **474 test, OK** (122 sn); ilk koşuda `test_pgg_a2_a3` içinde bir zamanlama testi yük altında (270 sn) düştü, modül tek başına 3/3 ve tam takım yeniden 474/474 geçti | `69ef290` | log `workspace/gorev93_tests.txt` |
| #95 (EMİR 6 C1 + C2) | **505 test, OK** (474 + 31 yeni: `tests/test_emir6_c1_c2.py`); 5 mevcut test yeni kurala göre değiştirildi | `86cae1f` | ara koşularda `test_body_cut_at_the_deadline_logs_content_and_cost` yük altında düştü; temiz HEAD'de de düştüğü için mevcut zamanlama testi; yük düşünce tam takım geçti [T95] |
| #96 (EMİR 6 C3 + Soru 1–2) | **528 test, OK** (132 sn) | `782dc31` | çıktı `workspace/gorev96_tests.txt`; yeni `tests/test_emir6_c3.py` |

### 12.2 Güncel dosyaların sha256'ları

| dosya | sha256 | kaynak |
|---|---|---|
| `frames/abstract_v4.json` | `c00db315d9c3141b78b04de5ece650e4b922db907cb90ae124666c439633a9f4` | T93; C3D (değişmedi) |
| `cards/main_cards_v1.json` | `bb2be483d1cb860df43d46675a0b798acc240f5d022ee36a5e5d272a12d7f1dc` | T93; C3D (değişmedi) |
| `configs/main.json` | `290024c0bb96eef2c271632cba4b08c095a2b5a6f6295efb26c01542342d8f4e` | C3D (#96) |
| `configs/main_s0a_example.json` | `e159d1f0bce0238d378adac9487e6b90a67a3718f7330f30625345eb12292d6e` | C3D (#96) |
| `configs/main_s0a_schema.json` | `c7307f06ea412c25620c3950c18b1a0b2988a989fc974e109818d4ee07fd00a9` | C3D (#96) |
| `configs/main_s0b.json` | `74f0ca6463f56f6215b7b13716884e204253f00ac57a931571d774f0ad8c94b2` | C3D (#96) |
| `configs/cost_calibration_minipilot.json` | `d26eb4107aa7ae0ec828bffb912dc5e59d23933347cdf3a8f737858b5ec040c8` | T93; config'teki kilit değeri CFG6 `main.json` satır 90 |
| `workspace/main_dryrun_tablosu.md` (DRY5; kaynak olarak) | `fff34aa77f99c444952ef1eee220e324dcb97726cdbfe17a393c3c396c18a801` | T93 |

**#90'ın değiştirdiği dosyalar** (`llm_client.py`, `pgg_game.py`, `scripts/runctl.py`, `README.md`, iki not, testler) için #90 raporunda sha256 **verilmedi**; #95 ve #96'nın değiştirdiği `pgg_game.py`, `README.md` ve test dosyaları için de verilmedi; burada uydurulmadı. Kod sürümü orc commit'leriyle tanımlıdır (`d8eafc9`, `86cae1f`, `782dc31`).

**Tarihli not — 2026-10-11, EMİR 8 (görev #103): config sha256'ları.** Yukarıdaki tablo silinmedi; tablodaki dört config değeri #96'nındır ve artık güncel değildir. Ara değerler #99'un `prereg_approved=true` değişikliğinden sonraki hâldir (commit `daa8f62`, Aşama 0a'nın koştuğu kod) [T99 §3; T102 §1]. Güncel değerler #101'in `answer_format = "example_object"` değişikliğinden sonraki hâldir (commit `d585830e377a380b48e640f2e92572ee4643903e`) [T101; T102 §1, §3]. Kısaltmalar (dosya sonundaki ekte de): T99 = `gorev99_rapor.md`; T101 = görev #101 sonuç raporu; T102 = `gorev_0b_hazirlik.md`.

| dosya | §12.2 tablosu (#96) | #99 sonrası (`daa8f62`) | **güncel** (#101 sonrası, `d585830`) |
|---|---|---|---|
| `configs/main.json` | `290024c0bb96eef2c271632cba4b08c095a2b5a6f6295efb26c01542342d8f4e` | `a3395a8e9503bf3df090a660a039dd26569d4ec1730e8c406221a3c1996a225c` | **`4b2d9f5639b094242f97eecc99c77ba370f42ebe18ecc6a5e9004073fe34704f`** |
| `configs/main_s0a_example.json` | `e159d1f0bce0238d378adac9487e6b90a67a3718f7330f30625345eb12292d6e` | `76e5d785858ea8bdba62e4589820a4196a0b2f6e64dbb3f98d1d21f6e1c8fa6d` | `76e5d785858ea8bdba62e4589820a4196a0b2f6e64dbb3f98d1d21f6e1c8fa6d` (#101'de değişmedi) |
| `configs/main_s0a_schema.json` | `c7307f06ea412c25620c3950c18b1a0b2988a989fc974e109818d4ee07fd00a9` | `a5a29d6716e2c5241f1e81fbde097ebe044a3fd029679dc321490104178c10b8` | `a5a29d6716e2c5241f1e81fbde097ebe044a3fd029679dc321490104178c10b8` (#101'de değişmedi) |
| `configs/main_s0b.json` | `74f0ca6463f56f6215b7b13716884e204253f00ac57a931571d774f0ad8c94b2` | `d6231b57e9f7fa0899ce2d603e6375c6685f9f9b35bdad7ae59fd6b4c231b34a` | **`505b90af52aec92de5fa0bbb29e3a12f567218284131b9324d2dafb84ad853fc`** |
| `frames/abstract_v4.json` | `c00db315d9c3141b78b04de5ece650e4b922db907cb90ae124666c439633a9f4` | aynı | aynı (değişmedi) |
| `cards/main_cards_v1.json` | `bb2be483d1cb860df43d46675a0b798acc240f5d022ee36a5e5d272a12d7f1dc` | aynı | aynı (değişmedi) |
| `configs/cost_calibration_minipilot.json` | `d26eb4107aa7ae0ec828bffb912dc5e59d23933347cdf3a8f737858b5ec040c8` | aynı | aynı (değişmedi) |

- `daa8f62` → `d585830` arasında yalnız 5 dosya değişti: `configs/main.json`, `configs/main_s0b.json` ve üç test dosyası; iki 0a config'i, çerçeve, kart ve motor kodu aynı kaldı [T102 §2]. İki config'te de yalnız `answer_format` satırı değişti [T101].
- Yeni commit'in kod kopyası: `workspace/_kod_d585830e377a380b48e640f2e92572ee4643903e/`. `CODE_VERSION.json` 51 dosyanın sha256'sını içeriyor (34'ü `.py`); kopyadaki dosyalar damgayla aynı [T102 §2]. Testler: 528 test, OK [T101; `gorev101_tests.txt`: "Ran 528 tests … OK"].
- 0a sonucunun kaydı dosya sonundaki "Ek — Aşama 0a sonucu (2026-10-11)" bölümünde.

### 12.3 Dry-run özeti (#96)

| aşama | çağrı | ortalama A / B | p95 üst sınır A / B | sert tavan | alt tavanlar (DS / Mistral / GPT) | kapı | karar |
|---|---|---|---|---|---|---|---|
| 0a (A ve B ayrı koşu) | 360 + 360 | 0,8822 / 0,8858 | 1,5636 / 1,5679 | koşu başına 1,6 | 0,3 / 1,3 / 0,1 | 1,0 | geçer |
| 0b | 1800 | 4,8518 / 4,8681 | 8,9394 / 8,9603 | 10 | 2 / 8 / 0,5 | 5,5 | geçer |
| 1 (G 16 / 16 / 10) | 23 040 | 46,8940 / 47,0614 | 90,6270 / 90,8443 | 91 | 22 / 68 / 3 | 52 | geçer |

Tutarlar USD, tahmin [C3D]. Model × kol ayrıntısı §3.3, §4.4 ve §9.2'de. *Not (#95 C2): kalibrasyon schema_text ile ölçüldü; A/B farkı istem uzunluğundan ölçeklendi.*

**Not:** #96 tabloları commit'ten önce, çalışma ağacından üretildi; sayılar commit'e değil config, kalibrasyon, çerçeve ve kartlara bağlıdır. "Temiz kodla" şartını tam karşılamak için commit sonrası aynı betiğin (`python gorev96_dryrun_tablo.py <kod_dizini>`) bir kez yeniden çalıştırılması önerildi [T96].

---

## 13. P9 — Kullanıcı kararları (2026-10-11; EMİR 6 Bölüm 3)

> Onay verildi; `prereg_approved` config'lerde `false` kalır ve ayrı developer görevinde `true` yapılır. **Ücretli koşu başlamaz;** her aşama kullanıcı o aşama için "BAŞLA" deyince başlar (§10.4).

1. **Soru 1 — G: DeepSeek 16, GPT 16, Mistral 10.** EMİR 6'nın koşulu: motor model başına `groups_per_cell`'i destekliyorsa (ya da küçük bir değişiklikle destekleyebiliyorsa; mock testli) 16 / 16 / 10, desteklemiyorsa üç model 10. #96 bu desteği küçük bir değişiklikle ve mock testlerle ekledi (`groups_per_cell_by_model`, `--groups-per-cell-by-model`); bu yüzden **16 / 16 / 10** hali seçildi [EM6 Soru 1; T96; CFG6 `main.json` satır 26–31].
   - Gerekçe (kullanıcı): "DeepSeek ve GPT'yi 16'ya çıkarmak ~3 USD ekler ve güç artar; maliyetin ~%89'u Mistral'dan geliyor" [EM6 Soru 1].
   - Güncel dry-run'la sağlama (hesap): üç model G = 10'da Aşama 1 ortalaması A 44,44, B 44,60 USD [T95]; 16 / 16 / 10'da A 46,8940, B 47,0614 USD [C3D] → fark yaklaşık 2,45 USD. 16 / 16 / 10'da Mistral payı %84,8 (§9.2).
2. **Soru 2 — Bütçe** (kural: sert tavan ≥ toplam p95; alt tavan ≥ model p95; kapı = ortalama × 1,1) [EM6 Soru 2; T96]:
   - **Aşama 1 (16 / 16 / 10):** sert tavan **91**, alt tavanlar DeepSeek **22** / Mistral **68** / GPT **3**, kapı **52** USD.
   - **0b:** **10 / 2-8-0,5 / 5,5** USD (kullanıcının değerleri; kural sağlanıyor).
   - **0a (koşu başına, A ve B):** sert tavan **1,6**, alt tavanlar **0,3 / 1,3 / 0,1**, kapı **1,0** USD.
   - Dayanak ve sağlama §9.4.
3. **Soru 3 — Onay: ONAYLANDI.** Kullanıcı bu belgeyi, "KULLANICI KARARI" diye işaretli varsayılanlarla ve EMİR 6'daki değişikliklerle birlikte onayladı [EM6 Soru 3]. Onaylanan varsayılanlar:
   - 0a oran tanımı (§3.2);
   - H4 simülasyon ayrıntıları: doğrusal enterpolasyon, gözlenen 1. tur başlangıcı, belirlenimci güncelleme, iki düzeyli bootstrap (§6.4);
   - Holm ailesi: hipotez başına (§7.3).
   - **Onay kapsamı dışında kalmış olabilecek nokta:** 0a izole sorusunun "round 2 of 3" olması (`isolated_round_no` 2) emir metninde yok; #96'nın geliştirici seçimi (§3.1). Kullanıcıya ayrıca bildirildi.

---

## Değişiklik günlüğü

- 2026-10-10, görev #94: ilk taslak. API çağrısı yok; kod çalıştırılmadı.
- **2026-10-11 — EMİR 6** (görev #98; kaynaklar #95, #96, #97; API çağrısı yok, kod çalıştırılmadı):
  - **Başlık:** "TASLAK — KULLANICI ONAYI BEKLİYOR" → "ONAYLANDI — 2026-10-11 (kullanıcı)"; altına "config'lerde prereg_approved=true ayrı developer görevinde yapılır; ücretli koşu yok" notu ve onayın dayanağı (#95 505 test OK, #96 528 test OK, 0a/0b/Aşama 1 dry-run kapıları A ve B'de geçer).
  - **Giriş:** EMİR 6 önceliği; güncelleme tarihi; pilot verisinin kullanım yerleri (güç hesabı pilot v2 + mini-pilot); kaynak tablosuna EM6, T95, T96, C3D, GUC2, CFG6; CFG5 satır numaralarının #93 sürümüne ait olduğu notu.
  - **§0 Sonuç:** aşama çağrı sayıları (0a 720, Aşama 1 23 040), bütçe, güç özeti, verilen kararlar ve açık noktalar güncellendi.
  - **§2.4:** G model başına (16 / 16 / 10) ve `groups_per_cell_by_model`.
  - **§3 (P-a):** Aşama 0a yeniden yazıldı: biçim başına model başına 6 kart × 1 grup × 3 tur + kart başına izole X = 10 × 2 + kural anlama (120 çağrı; biçim başına 360); `params.rounds` 3 yalnız 0a'da; `isolated_round_no` 2 (#96 geliştirici seçimi); `invalid_rate_cap` kapalı, `max_invalid` 8; 8 geçersizle RunAborted = o model × biçim için "biçim başarısız" (`format_failed`), diğer modeller sürer; `format_test` özeti; seçim kuralı EMİR 6 metniyle (RunAborted koşulu eklendi); eşik açıklaması 120 çağrıya göre yeniden hesaplandı (pratikte ≥ 3 kötü yanıt); "ROUND k of 3" sınırlılığı; 0a dry-run tabloları (A, B), tavanlar 1,6 / 0,3-1,3-0,1 / 1,0 ve kapı kararı #96'dan. Kaldırılanlar: eski 24 çağrılık tasarım, "1. tur katkı için motor modu yok" notu, 144 / 216 çağrılık eski maliyetler (0,3693 / 0,5510 USD) ve eski tavanlar (1 / 0,5-0,5-0,5 / 0,5), `invalid_rate_cap` 0,05 riski (#96'da kapatıldı: `null`).
  - **§4.1 ve yeni §4.4:** 0b maliyetleri #96'nın A/B değerleriyle (eski tek değer 4,8609 / 8,9510 çıkarıldı); 0b dry-run tabloları ve C2 notu.
  - **§5:** `stage` "1"; Aşama 1 çağrı sayısı 23 040 (16 / 16 / 10).
  - **§9 (P-b):** §9.1'e C2 maddesi; §9.2 Aşama 1 tablosu #96'nın 16 / 16 / 10 A/B tablolarıyla değiştirildi (eski G = 6 / 10 / 16 tablosu çıkarıldı); §9.3 güç hesabı #97'ye göre baştan yazıldı; §9.4 tavanlar seçilen G'ye göre (eski G = 6 / 10 / 16 tavan tablosu çıkarıldı); §9.5 Mistral sınırı yalnız G = 10.
  - **§9.3'ten 0,149 ve 0,177 çıkarıldı. Neden:** bu değerler eski taslakta (T92) yalnız mini-pilotun abstract_v3 hücrelerinden hesaplanmıştı ve gerçek dışıdır (EMİR 6 P-b). #97 aynı alt kümede DeepSeek için 0,149 (GPT için 4,211) buldu; iki pilotun bütün hücreleriyle havuzlanmış SD DeepSeek 0,887, GPT 2,507. Mistral'ın 0,177'si 2 tam gruplu tek bir hücreden (boston_value, df 1) geliyor; güvenilir değil, Mistral için SD "bilinmiyor" sayıldı. Eski tablodaki yarı genişlikler ve eski bootstrap oranları (GPT SD × %200 senaryosu) da çıkarıldı. Yeni bölümde ön hesapla karşılaştırma (0,89 / 2,51 / 3,35 / bilinmiyor, tutuyor), en kötü durum SD = 9 (normal ve iki modlu), G = 10 ve 16, 10 ve 5 puanlık farkta yarı genişlik ve 0'ı dışlama oranı var.
  - **§10 (P8):** başlık "Durdurma ve sürdürme kuralları"; C1 kod sürümü kilidi ve `--allow-code-change` istisnası (yalnız 0a/0b; Aşama 1'de ret; `code_change_span` işaretleri) §10.3'e; başlamama koşullarına "BAŞLA" ve bayrak ret koşulları; kapı ve tavan değerleri güncellendi; 0a'da `invalid_rate_cap` kapalı ve `format_failed` davranışı; `--discard-reuse-on-code-change`'in kilitten sonraki yeri; §10.4'e "BAŞLA" kuralı ve aşama sonu raporu.
  - **§11:** Mistral maliyet payı (~%85), farklı G'nin H5'e etkisi, SD kaynağı ve 0a "ROUND k of 3" maddeleri güncellendi; eski "0a 1. tur katkı içermiyor" maddesi çıkarıldı.
  - **§12:** #95 ve #96 test/commit satırları; config sha256'ları #96 değerleriyle değiştirildi (#93'ün config sha256'ları — `main` 8e98b0f6…, `s0a_example` 219d8031…, `s0a_schema` a10b4fe2…, `s0b` 34573568… — ve #96'da değişen `tests/test_emir5_bolum2.py`'nin #93 sha256'sı 2765e465… artık güncel değil); dry-run özeti #96'dan; tabloların commit öncesi üretildiği notu.
  - **§13 (P-c):** üç soru kullanıcı kararlarıyla dolduruldu (G 16 / 16 / 10; bütçe; onay ve onaylanan varsayılanlar); eski soru metni ve eski seçenekler (G 6 / 10 / 16; 85 / 14-68-2 / 49 önerisi) çıkarıldı.
  - **Değişmeyen bölümler:** §1, §2.1–§2.3, §2.5–§2.6, §4.2–§4.3, §6, §7, §8, §10.5 metni aynen korundu (kontrol yöntemi: `rapor_emir6_prereg.md`).
- **2026-10-11 — EMİR 8** (görev #103; kaynaklar #100, #101, #102; API çağrısı yok, kod çalıştırılmadı): `configs/main.json` ve `configs/main_s0b.json`'da `answer_format` = `"example_object"` (#101, commit `d585830`); başka config alanı değişmedi (`daa8f62` → `d585830` arasında config olarak yalnız bu iki dosya değişti, her birinde yalnız `answer_format` satırı) [T101; T102 §1–§2]. §12.2'ye tarihli sha256 notu eklendi (eski tablo silinmedi); dosyanın sonuna "Ek — Aşama 0a sonucu (2026-10-11)" eklendi. Önceki metin değiştirilmedi (kontrol yöntemi: `rapor_emir8.md` §3).

---

## Ek — Aşama 0a sonucu (2026-10-11)

- **Tarih ve görev:** 2026-10-11, görev #103 (EMİR 8). Bu ek yazılırken API çağrısı yapılmadı, kod çalıştırılmadı; depoya ve `runs/` altına yazılmadı.
- **Kaynaklar:** **S0A** = `gorev_0a_sonuc.md` (#100; §1–§9 `s0a_sonuc.py` çıktısı, koşu dosyalarından yeniden üretim); **T99** = `gorev99_rapor.md` (#99); **T101** = görev #101 sonuç raporu (config değişikliği, testler, dry-run'lar, sha256'lar); **T102** = `gorev_0b_hazirlik.md` (#102); **EM8** = EMİR 8 metni (2026-10-11; üst yönetici ve kullanıcı).
- Bu ek §3.4'ün öngördüğü kayıttır. **0a katkı değerleri yorumlanmaz** (§3.1 sınırlılık); 0a satırları hiçbir analize girmez.

### E.1 Sonuç (önce bu)

- **Seçilen biçim: A = `example_object`.** Üç modelde de §3.2 oranı 0/120 = %0,00 (eşik %2); hiçbir modelde `format_failed` yok [S0A §7, §9].
- **B (`main_s0a_schema`) koşulmadı; gerekçe: kural A'yı B'den bağımsız olarak seçiyor** (E.4) [S0A §10; EM8].
- `configs/main.json` ve `configs/main_s0b.json`'da `answer_format = "example_object"` (commit `d585830`); güncel sha256'lar §12.2'deki tarihli notta [T101; T102 §1–§3].

### E.2 Koşu

| alan | değer | kaynak |
|---|---|---|
| koşu dizini | `workspace/runs/main_s0a_example_20261011/` | S0A başlık |
| başlatma | kullanıcının kendi Terminal'inden (biçim A) | EM8 |
| config / biçim | `configs/main_s0a_example.json`; `answer_format` = `example_object` | S0A §9 |
| kod | `_kod_daa8f62b4952208771eede83956f6da04cb1a11f/`; tek segment, `git_commit` `daa8f62b4952208771eede83956f6da04cb1a11f`, `git_dirty` False | S0A başlık, §5 |
| birim | 54/54 (model başına 18) | S0A §2 |
| sonuç satırı | 360 (model başına 120: grup turu 72, izole 12, kural anlama 36) | S0A §2 |
| maliyet | 0,844827202 ≈ **0,8448 USD** (DeepSeek 0,1138 / Mistral 0,7159 / GPT 0,0152); ham log, sonuç satırları, özet ve `status.json` aynı toplamı veriyor; sert tavan 1,6 | S0A §6 |
| stop_reason | yok (özette ve `status.json`'da `None`); durum `ended` / `completed` | S0A §2, §4 |
| RunAborted / `format_failed` | yok (üç modelde) | S0A §4 |

### E.3 Model başına geçersiz ve parse_fail oranları

| model | birim / satır | n_invalid | n_parse_fail | n_comp_invalid | n_comp_parse_fail | pay / alınan yanıt | §3.2 oranı | > %2 ? | `format_failed` | `reasoning_capped` |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | 18 / 120 | 0 | 0 | 0 | 0 | 0 / 120 | %0,00 | hayır | hayır | 1 |
| mistral | 18 / 120 | 0 | 0 | 0 | 0 | 0 / 120 | %0,00 | hayır | hayır | 0 |
| gpt | 18 / 120 | 0 | 0 | 0 | 0 | 0 / 120 | %0,00 | hayır | hayır | 0 |

Kaynak: S0A §3 (dört sayaç sonuç satırlarından yeniden sayıldı; özetteki değerlerle aynı), §4 (`format_failed`), §7 (payda = ham logdaki çağrı kaydı sayısı; özetteki `n_responses` 120 ile aynı).

- **Ön sayımla karşılaştırma:** üst yöneticinin ön sayımındaki 25 kalemin (birim, satır, maliyet, stop_reason; model başına dört sayaç, oran, geçerli yanıt ve `reasoning_capped`) hepsi yeniden üretilen sayılarla tuttu; **ön sayımla tutmayan sayı yok** [S0A §8]. Ön sayımda Mistral ve GPT için `reasoning_capped` açıkça yazılmamıştı; karşılaştırmada 0 okundu [S0A §12].
- **DeepSeek'teki `reasoning_capped` satırı:** 1 satır (sonuç satırlarında, ham logda ve özette 1); Mistral ve GPT'de 0 [S0A §3]. `reasoning_capped`, §3.2 oranının dört sayacından biri değildir ve durma kuralı değildir (§10.2 madde 4). DeepSeek'in 120 çağrısının hepsinde `finish_reason` = `stop`, `n_length` = 0 [S0A §3].
- **Diğer sayaçlar:** `n_length`, `n_transport`, `n_deadline`, `n_provider_mismatch`, `n_provider_missing`, `n_discarded` ve `comp_missing` üç modelde 0; ham logda `invalid_payload` kaydı yok [S0A §3].

### E.4 Seçim kuralı (§3.2, aynen) ve mekanik uygulama

> **Varsayılan A. A'nın herhangi bir modelde geçersiz + parse_fail oranı > %2 ve B'ninki daha düşükse (ya da A RunAborted verdiyse ve B vermediyse) B seçilir. Sağlayıcı B'yi desteklemezse A kalır.** [EM6 C3; EM5 P1]

Uygulama tanımları §3.2'dedir (oran formülü; "A RunAborted verdiyse" = o modelde `format_failed: true`). Kuralın B'yi seçtiği yalnız iki dal vardır; ikisi de bir A koşuluyla bir B koşulunun birlikte sağlanmasını ister [S0A §10]:

| dal | A tarafındaki koşul | A'daki değer | A koşulu sağlanıyor mu | B tarafındaki koşul |
|---|---|---|---|---|
| (i) | herhangi bir modelde A oranı > %2 | DeepSeek, Mistral, GPT: 0/120 = %0,00 (E.3) | hayır | "B'ninki daha düşük" |
| (ii) | A RunAborted (`format_failed: true`) | üç modelde `format_failed` ve `run_aborted` False; ham logda `pgg_run_aborted` / `pgg_model_stopped` = 0 [S0A §4] | hayır | "B vermediyse" |

- İki dalda da A koşulu sağlanmıyor; bu yüzden B'nin sonucu ne olursa olsun B dalı tetiklenmez ve kuralın ilk cümlesi geçerlidir: "Varsayılan A." Üçüncü cümle ("Sağlayıcı B'yi desteklemezse A kalır") yalnız A'yı korur [S0A §10].
- **Seçilen biçim: A = `example_object`.**
- **B (`main_s0a_schema`) koşulmadı; gerekçe: kural A'yı B'den bağımsız olarak seçiyor.** B koşusunun hiçbir olası sonucu kararı değiştiremez; `runs/` altında `main_s0a_schema_*` dizini yok [S0A §10; T102 §6]. Bu yüzden "B'ninki daha düşük" ve "Sağlayıcı B'yi desteklemezse" koşulları için veri yoktur; karar için de gerekmez.

### E.5 Sınırlılık: 0a'da grup oyunu 3 turdu

- 0a config'lerinde `params.rounds = 3`, izole soru `isolated_round_no: 2` (§3.1). İstemlerde "ROUND k of 3" (ör. "ROUND 3 of 3. You are Player 1. …"), izole soruda "This is round 2 of 3" yazıyor [§3.1; #96 render örneği `gorev96_0a_render_ornegi.txt` satır 21 ve 37]. 0b ve Aşama 1 istemleri 10 turludur (izole "round 5 of 10", §2.5).
- 0a'daki %0,00 oranı 10 turluk istemlerdeki oranı tam temsil etmeyebilir (§11 madde 10, tahmin). Seçilen biçimin geçersiz oranı 0b'de ayrıca raporlanır (§4.2–§4.3).
- "round 2 of 3" #96'nın geliştirici seçimidir; emir metninde yok (§3.1; §13 soru 3 son madde).

### E.6 Veri kalıcılığı: 0a dosyaları

Dosyalar worktree dışında, `workspace/runs/main_s0a_example_20261011/` altında (`runs_dir`, §5) [S0A §1, §12]:

| dosya | bayt | satır |
|---|---:|---:|
| `console.log` | 1793 | 7 |
| `launcher.jsonl` | 1255 | 1 |
| `main_s0a_example_20261011.accepted.jsonl` | 2957296 | 360 |
| `main_s0a_example_20261011.jsonl` | 3178041 | 360 |
| `main_s0a_example_20261011_summary.json` | 37103 | 1049 |
| `raw_calls.jsonl` | 1488850 | 722 |
| `status.json` | 1928 | 49 |

- Satır sayıları S0A §1'den. Görev #103'te içerik rapora alınmadan yalnız satır sayımıyla (Grep) yeniden sayıldı; 7 dosyada da aynı. `.seg` / `.partial` / `.lock` / `stop_request` dosyası yok [S0A §1]. Dosyaların sha256'ları S0A §11'de.
- **Ham log (`raw_calls.jsonl`) commit'e girmez** (veri kalıcılığı kuralı, §10.4); kopyalanmadı [S0A §12].

### E.7 Sonraki adım ve bu ekle eskiyen ifadeler

- **0b hazırlığı (API yok):** commit `d585830` kopyasından 0b dry-run'ı: 1800 çağrı, ortalama 4,8518 / p95 üst sınır 8,9394 USD (tahmin), kapı 5,5 → GEÇER; kod "temiz", çerçeve ve kart kilitleri "beklenenle aynı", `answer_format=example_object` [T102 §4]. Böylece §12.3 Not'undaki "commit sonrası yeniden üretim" önerisi A biçimi için karşılandı: 0b ve Aşama 1 değerleri (Aşama 1: 23 040 çağrı, 46,8940 / 90,6270 USD, kapı 52 → GEÇER) temiz koddan #96'nın A değerleriyle aynı çıktı [T101; T102 §4–§5].
- **0b başlatılmadı;** kullanıcı 0b için "BAŞLA" diyene kadar başlamaz (§10.4).
- **Önceki metinde eskiyen ifadeler (metin değiştirilmedi, burada not edilir):** başlıktaki onay dayanağı notu, §0 madde 6 ve §10.1 config'lerde `prereg_approved` için "false" diyor; #99'dan beri `true` [T99 başlık ve §1; T102 §4: "Ön kayıt: onaylı (prereg_approved=true)"]. §4.1 ve §10.1 `answer_format`'ı yer tutucu diye anıyor; artık `example_object` [T101]. §12.2 tablosunun config satırlarının güncel değerleri oradaki tarihli notta.

---

## Ek — Aşama 0b sonucu (2026-10-13)

- **Tarih ve yapan:** 2026-10-13; Claude (orc yöneticisi artık kullanılmıyor), kullanıcı onayıyla. Kaynak: `workspace/runs/main_s0b_20261012/` (sonuç dosyası sha256 `fa6a9cf1…9c30`, özet `640764ba…0d6b`, ham log `7bd3fab5…d8bc`).
- **0b verisi hiçbir analize girmez** (§4.3). Aşağıdaki sayılar yalnız tesisat ve okuma içindir; kartlar arası karşılaştırma yapılmadı.

### F.1 Koşu

- Kullanıcı "BAŞLA 0b" dedi (2026-10-12); koşu `_kod_d585830…` kopyasından, `runctl` ile başladı (22:49) ve 2026-10-13 00:58'de bitti (7 772 s).
- 72/72 birim, 1 800 satır (model başına grup 480, izole 60, kural anlama 60). `stop_reason` yok, model durması yok. Kod `d585830`, `git_dirty` false; `answer_format` example_object.
- Maliyet 4,3656 USD (DeepSeek 0,4893 / Mistral 3,7973 / GPT 0,0790); dry-run oranı 0,90 (Mistral 0,88, DeepSeek 1,03, GPT 0,97).

### F.2 Tesisat sayıları (§4.2)

| model | geçersiz + parse_fail (karar) | kural anlama tam doğru | reasoning_capped | n_length | n_reuse_invalid | süre medyan / p95 / maks (s) |
|---|---|---|---|---|---|---|
| deepseek | 1 / 541 (%0,18) | 60/60 | 8 | 0 | 0 | 15,1 / 181,0 / 507,9 |
| mistral | 0 / 540 | 60/60 | 0 | 0 | 0 | 45,7 / 113,6 / 236,7 |
| gpt | 0 / 540 | 60/60 | 0 | 0 | 0 | 3,0 / 5,5 / 11,8 |

- Hiçbir model %5 tavanına yaklaşmadı (§4.3). DeepSeek'in tek geçersiz yanıtı: muhakeme metni JSON anahtarı olarak yazılmış; yeniden istendi ve sayıldı.
- DeepSeek'te 9 kez HTTP 429 (sağlayıcı hız sınırı); ücretsiz, yeniden denendi; özetteki `n_transport` bunları saymıyor. Mistral'da 2 ücretsiz bağlantı hatası.
- GPT'nin 6 gerekçesinin sonunda artık karakter (`}` ya da `】【。}`); karar alanını etkilemiyor.

### F.3 Okuma (§4.2)

**Yöntem:** 1 800 gerekçenin hepsi; DeepSeek ve Mistral'da §4.2 örneklemi (kart başına grup 1/5/10. tur ajan 1, izole X = 10, ajan 1 kural anlama: model başına 60) ve DeepSeek'in 8 `reasoning_capped` kaydı; GPT'de muhakeme dönen 472 kaydın hepsi. Okuma, Claude alt ajanlarıyla yapıldı; aktarılan 12 alıntı ham dosyada birebir doğrulandı. Ayrıca 1 800 kaydın tamamında anahtar kelime sayımı yapıldı.

**Mekanik kusur bulunmadı:** kural anlama 180/180; şema geri yazma yok (Mistral dahil); oyuncu numarası karışıklığı yok; gerekçe ile sayı arasında çelişki yok; geçmiş doğru okunuyor (tek tük tur sayımı kaymaları).

**Gözlemler (kusur değil; sınırlılık ve ortak değişken olarak kayıt):**
1. **Mistral'a sağlayıcı tarafından eklenen sistem metni.** Mistral muhakemelerinde istemde olmayan "Always respond with valid JSON. Ensure the output is strictly formatted as JSON, with no additional text, explanations, or markdown formatting." cümlesi 68/600 kayıtta, "You are Mistral Large 4" 10/600 kayıtta alıntılanıyor (0a'da 19/120, mini-pilotta 59/380). Kodumuzda yok (`_kod_d585830…` tarandı). Büyük olasılıkla sağlayıcı ekliyor (JSON modu). Bütün Mistral hücrelerinde aynı; kartlar arası karşılaştırmayı bozmaz. Mistral için "sistem mesajı yalnız giriş satırı + kart" varsayımı geçerli değildir; yöntem bölümüne yazılır.
2. **İzole kol büyük ölçüde eşleme:** katkı = X olan cevaplar GPT 60/60, DeepSeek 58/60, Mistral 45/60. H4 okunurken bu dikkate alınır; soru değiştirilmez.
3. **Olgusal kart:** DeepSeek muhakemesinde sık sık "tuhaf / alakasız" bulunuyor; "prompt injection" olgusal kartta 10/200 (mini-pilotta, farklı bir kartla — nüfus sayımı cümlesi — 34/200; karşılaştırma kaba). Mistral süreyi her şehirde "yavaş yargı / zayıf yaptırım" diye okuyor (444 gün dahil); GPT gerekçelerinde kart hiç geçmiyor. "In your country" ile şehir adı arasında 1–2 kayıtta sürtünme ("Boston is not a country").
4. **Değer kartlarının oyuna bağlanma kolaylığı eşit değil:** Kopenhag "equal standing" doğrudan "eşit katkı" olarak okunuyor; Boston "against authority" ancak zorlamayla oyuna bağlanıyor; Atina'da "elders" düşüyor, kartta olmayan "polis / civic duty" ekleniyor; Riyad'da onur/utanç ekleniyor. Minimal kartlar da yalnız şehir adından kültür klişesi üretiyor. Değer stilinin şehir karşılaştırmaları yorumlanırken sınırlılık.
5. **Literatür tanıma:** Herrmann / Gächter / Thöni adı DeepSeek'te 13, Mistral'da 7 muhakemede (DeepSeek bir kayıtta şehir setini Herrmann, Thöni & Gächter 2008'e bağlıyor). Bu adlar E2a sözlüğünde zaten var; Aşama 1'de sayılır.
6. **Talep / değerlendirme farkındalığı:** "kullanıcı test ediyor" Mistral 131/600, DeepSeek 32/600; "benchmark / evaluat" DeepSeek 150/600, GPT özetlerinde 118/472. Amaç cümlesi (kazancını en çoğa çıkar) istemde yok; modeller bunu sık soruyor (bilinçli tasarım, değiştirilmedi).
7. "Group project" ifadesi Mistral'da 23/600 muhakemede ders ödevi / not çağrışımı yapıyor; bütün kartlarda aynı.

### F.4 Karar: değişiklik yok

- Okuyucuların 6'sı "değişiklik gerektiren kusur yok" dedi; ikisi ifade düzeyinde öneri getirdi ("In your country" yerine ülke adı, amaç cümlesi, izole soruda kendi önceki katkı). Bunlar uygulanmadı: kilitli manipülasyonu değiştirir, 0b'nin yeniden koşulmasını gerektirir ve yeni talep etkisi getirir; bulunan sürtünmeler seyrek ve bütün hücrelerde ortak.
- Çerçeve ve kart dosyaları değişmedi (sha256 `c00db315…`, `bb2be483…`).

### F.5 Model seçimi: Mistral Large 4 kalır

- Kullanıcı Aşama 1'in Mistral maliyetini (0b fiyatlarıyla ~35 USD, toplamın ~%80'i) sordu. OpenRouter'da Avrupalı üretici yalnız Mistral.
- **Mistral Small 4 (`mistralai/mistral-small-2603`) denemesi (2026-10-13, analiz verisi değil):** 0b'de Mistral Large 4'e giden 16 istemin aynısı, aynı ayarlarla (temperature ve reasoning_effort gönderilmedi, max_tokens 16000, sağlayıcı Mistral'a sabit, example_object). Sonuç: 12/16 yanıt; 4 çağrı dört denemede de HTTP 429; dönen yanıtların hiçbirinde muhakeme yok (reasoning_tokens 0); kural anlamanın 3/3'ü yanlış (q1 22 / 23 / 23, q2 −2 / 2 / −2), oysa aynı yanıtların gerekçesi 28 ve −6'yı doğru hesaplıyor. Maliyet 0,0014 USD. Log Claude'un geçici dizininde; depoya girmedi.
- Karar (kullanıcı, 2026-10-13): **Mistral Large 4 ile devam.** G 16 / 16 / 10 değişmez.

### F.6 Aşama 1 öncesi

- `configs/main.json` `_notes` alanında üç eskimiş cümle güncellendi (yalnız açıklama; davranış değişmez): answer_format seçimi, prereg onayı, bütçe gerekçesindeki "henüz seçilmedi". Yeni sha256 `ab402a4c2e878b6b41c184d731e84ac8192946b2a6319b603603ac75a2089700`. 528 test OK.
- Tahmin (0b oranlarıyla): Aşama 1 ~43 USD (dry-run 46,89; sert tavan 91); süre ~24–25 saat (0b birim süreleri × Aşama 1 birim sayısı / 3 paralel birim).
- Aşama 1, kullanıcı "BAŞLA 1" diyene kadar başlamaz (§10.4).

### F.7 Aşama 1 başlatma kararı (2026-10-14, kullanıcı)

- Kullanıcı "BAŞLA 1, 6 paralel, ilk parça 3 saat" dedi.
- **İşletme ayarı (tasarım değişikliği değil):** `parallel_units` config'te 3; Aşama 1, komut satırından `--parallel-units 6` ile koşar (segment kaydına girer; `--resume`'de segmentler arasında farklı olabilir). Gerekçe: süre ~24 saatten ~12 saate iner. İstemler, seed'ler ve birim sırası paralellikten bağımsızdır; risk yalnız sağlayıcı hız sınırı (HTTP 429 dört denemede de dönerse koşu durur ve `--resume` ile sürer).
- **Parçalı koşu:** ilk parça ~3 saat sonra `runctl stop` ile güvenli durdurulur; kalan parçalar aynı kod kopyası (`_kod_d68be55…`) ve aynı run adıyla `--resume` ile sürer. Parçalar arası ara 1–2 günü geçmez (Mistral sürüm kilidi).
- OpenRouter API anahtarı 2026-10-14'te kullanıcı tarafından yenilendi (yeni anahtar, kullanım 0).

### F.8 `finish_reason = length` sonrası sürdürme kuralı (2026-10-14, kullanıcı onayı)

- **Olay:** `main_s1_20261014` segment 0, 11:59'da başladı; 12:06'da DeepSeek'in bir çağrısı (copenhagen_factual grubu, tur 4, ajan 3) 14 673 muhakeme token'ıyla `max_tokens` 16 000'e ulaştı (`finish_reason = length`, cevap yok) ve koşu §10.2 madde 4 gereği durdu. O ana kadar 7/648 birim, 444 satır, 0,8755 USD.
- **Sıklık:** DeepSeek'in bugüne kadarki ~2 000 yanıtında (mini-pilot 1 275, 0b 601, bu segment 152) tek `length` bu; Aşama 1'de (~8 700 DeepSeek çağrısı) birkaç tekrar beklenir. Mistral ve GPT'de görülmedi.
- **§10.2 madde 4'e eklenen kural (önceki metin değişmez):** `finish_reason_length` ile duran Aşama 1 koşusu, aynı `_kod_<sha>` kopyası ve aynı run adıyla `--resume` ile sürdürülür; cevapsız kalan çağrı yeniden sorulur (geçersiz yanıtın yeniden istenmesiyle aynı mantık). Config ve `max_tokens` değişmez. Sürdürme izleyici betikle otomatik yapılır; başka bir durma nedeni kullanıcıya bildirilir.
- **§7.5 madde 2'ye eklenen:** en az bir `length` olayı yaşanan grup birimleri (izole kolda yalnız o nokta) "reasoning_capped hariç" duyarlılık analizinde de çıkarılır; model başına `n_length` raporlanır.
- Bu kural, Aşama 1'in 7 birimi dışında hiçbir veri görülmeden yazıldı; o 7 birimin satırları okunmadı ve analiz edilmedi.

### F.9 Analiz betiği ve veriden önce sabitlenen uygulama ayrıntıları (2026-10-16)

- **Betik:** `pgg_analysis.py` (depo kökü), testleri `tests/test_pgg_analysis.py` (25 test; sentetik veriyle bilinen etkiler: insan yönü / ters yön / fark yok ve eşdeğerlik, büyür / söner / işaret döndü / korunur, yukarı / aşağı / uyumlu, Holm, seed, duyarlılık dışlamaları, eksik hücre → belirlenemedi; ayrıca 0b koşusu üzerinde yalnız "çalışıyor mu" denemesi, sayıları raporlanmaz). Yazıldığı anda Aşama 1 koşusu 221/648 birimdeydi; Aşama 1 satırlarının hiçbir sonuç değeri okunmadı ya da hesaplanmadı. Betik, koşu tamamlanmadan çalışmayı reddeder ("ara analiz planda yok"); bu koruma gerçek koşuda denendi (221/648'de reddetti, dosya yazmadı).
- Betik §6–§7'yi aynen uygular (birim grup, 10 000 bootstrap, yüzdelik CI, §7.3 p tanımı, hipotez başına Holm, `stable_seed("pgg-main-s1-analysis", hipotez, model, çift)`, geçerli satırlar `pgg_game.Engine.valid_rows` ile). Prereg'in açık bıraktığı ve **veriden önce** şöyle sabitlenen noktalar:
  1. **H3 işaret dönmesi:** D(1) ve D(10)'un "var" olması |D| > 2 ve düzeltmesiz %95 CI'nin 0'ı dışlamasıyla belirlenir (bu ikisi bir Holm ailesi değildir).
  2. **H3 "büyür" ve D(1) = 0:** "aynı işaret" koşulunda D(1) tam 0 ise ters dönecek işaret yoktur; aynı işaret sayılır (ör. bütün gruplar 1. turda aynı katkıyı veren bir modelde). Bu durumda "grup içinde doğan fark" notu da düşülür.
  3. **Yalnız tamamlanmış birimler sayılır:** 10 tur × 4 ajanı tam grup; 5 noktası tam izole çizelge. Planlanandan az birimli hücre eldekilerle analiz edilir ve "eksik" işaretlenir; H5 o hücreyi kullanan her çift için "belirlenemedi" yazar.
  4. **H4 iki düzeyli bootstrap:** ikinci düzeyde her izole noktadaki cevaplar o noktada, noktalar arasında bağımsız olarak iadeli yeniden örneklenir.
  5. **Duyarlılık 2 (F.8 ile):** reasoning_capped satırı ya da `length` olayı olan grup birimleri çıkarılır; izole kolda yalnız o nokta. Duyarlılık 3: önceki segmentten yeniden kullanılmış cevabı olan birim (izole kolda çizelge) çıkarılır.
  6. Betimsel ölçüler (düzeltmesiz): D(9) / Δ9 ve "son tur etkisi" notu, minimal çiftler (D_min ve H3), stil başına D_iso (çizelge düzeyinde bootstrap), dört şehrin m10 sırası ile Herrmann tur 1–10 sırası ve Spearman ρ, E2a tanıma sayımları (mini-pilot sözlükleri ve etiket alanı kuralı aynen), kural anlama oranları.
- **İşletme notu (2026-10-16):** 2. parça 11:36'da başladı ve 26 saniye sonra DeepSeek sağlayıcısının (DeepInfra) "upstream rate-limited" 429 hatasıyla üç çağrının dört denemesi de tükenince `run_aborted` ile durdu (§10.2 madde 8 → `--resume`). İzleyici bu durumda 5 dakika bekleyip sürdürür; ikinci 429 durmasından sonra paralel birim sayısını 6'dan 3'e indirir; altıncıdan sonra durur ve bildirir. Tasarım değişmez.

### F.10 Aşama 1 tamamlandı (2026-10-17) — tesisat kaydı

- **Koşu:** `main_s1_20261014`, 2026-10-14 11:59 → 2026-10-17 05:5x; 28 segment (0–27), hepsi commit `d68be55` (`code_lock` 27 kez "same"); 648/648 birim, 23 040 satır, `stop_reason` yok, model durması yok. Sonuç dosyası sha256 `3a8d22e9b579406ae0e4b755c5ac4f5f14c7692aab4e42de4f89faca4f7ff930`, özet `b1ae8c0012658a3a0d0ef6f6efeea42bb8f4bc5811ca5e2047fb3948e358cdc5`, ham log `20ef027ff3ab72a8e4633c5c469146701d6339aed13910b45bbf716708ffd5c0` (47 138 satır).
- **Segment sonları:** `finish_reason_length` 10, `run_aborted` 16 (DeepSeek sağlayıcısı DeepInfra'nın "upstream rate-limited" HTTP 429'u; biri 429 + `length` birleşimi), `interrupted` 1 (1. parça sonu), son segment normal bitiş. Hepsi §10.2 madde 8 ve F.8'e göre aynı kod ve run adıyla sürdürüldü. Paralel birim: segment 0–12'de 6, 13'ten sonra 3.
- **Bütünlük:** superseded 0, truncated 0, discarded 0, reuse_invalid 0, orphaned 0; yeniden kullanılan cevap 87 (segment geçişlerinde yoldaki çağrılar). Model sürümleri değişmedi: deepseek-v4.1-flash-20260910, mistral-large-4-0-20261006, gpt-6-luna-20260922.
- **Maliyet:** 45,343 USD (özet = ham log); DeepSeek 8,46 / Mistral 35,69 / GPT 1,20. Sert tavan 91, alt tavanlar aşılmadı.
- **Model başına:** geçersiz + parse_fail (karar) DeepSeek 13 + 19 (%0,37), Mistral 0, GPT 0; `n_length` DeepSeek 16; `reasoning_capped` DeepSeek 236, Mistral 1; kural anlama tam doğru DeepSeek 816/816, Mistral 528/528, GPT 811/816.
- **İşletme notu:** iki kez (16 Ekim 17:07–17:59 ve 23:10–23:54) koşu durmuşken Mac boşta uykuya geçti ve sürdürme gecikti; izleyici bundan sonra `caffeinate -i` altında çalıştırıldı. Veriye etkisi yok.
- Analiz, koşu tamamlandıktan sonra `pgg_analysis.py` (commit `5276e46`) ile, değiştirilmeden çalıştırıldı.

### F.11 Analiz çalıştırıldı (2026-10-17)

- `pgg_analysis.py` (commit `5276e46`, değiştirilmeden) koşu tamamlandıktan sonra bir kez çalıştırıldı: `results/main_s1_20261014_analysis.json`, sha256 `c44002b97984af181cf19ddbebbddec82051d298c614a0f0ac6b39fec8ae4a24` (results/ git dışında). 504 grup, 144 izole çizelge, eksik birim ve eksik hücre yok; 10 000 bootstrap.
- Üç hücre farkı betikten bağımsız olarak ham satırlardan yeniden hesaplandı ve tuttu (DeepSeek değer Boston − Riyad −12,92; Mistral olgusal Kopenhag − Atina 5,74; GPT değer Kopenhag − Boston 2,38).
- **Duyarlılık notu:** "reasoning_capped / length hariç" analizinde DeepSeek'in 192 grup biriminden 88'i çıkıyor; `athens_value` hücresi 16 → 0 grup (o hücreyi kullanan testler "belirlenemedi"). Bu duyarlılık analizi DeepSeek için bilgi vermez; sınırlılık olarak raporlanır. Kural anlama duyarlılığında 0, yeniden kullanılan cevap duyarlılığında 1 etiket değişti.

### F.12 Keşifsel analiz: H4'te son tur etkisini ayırmak (2026-10-17, hesaplanmadan önce yazıldı)

- **Durum:** **keşifsel (exploratory), önceden kayıtlı değil.** H4'ün ana sonuçları (F.11) görüldükten sonra yazıldı. H4'ün ana etiketlerini değiştirmez; raporda "keşifsel" diye ayrı verilir.
- **Gerekçe:** izole tepki fonksiyonu f "round 5 of 10" bağlamında ölçüldü, simülasyon tur 2–10'a uygulanıyor ve son tur etkisini içermiyor (§6.4 "Bilinen sınır"). Ana analizde Δ4 36 hücrenin 32'sinde negatif (13 "aşağı", 0 "yukarı"). Bu düşüşün ne kadarının son turlardan geldiği bilinmiyor.
- **Ölçü:** simülasyon §6.4 ile aynı (doğrusal enterpolasyon, gözlenen 1. tur başlangıcı, belirlenimci güncelleme, tur 2–10 simüle edilir); yalnız karşılaştırma penceresi değişir: Δ4[a–b] = hücre içinde (O_g[a–b] − S_g[a–b])'nin grup ortalaması; O ve S, a…b turlarının 4 ajan ortalaması.
  - **Birincil keşifsel pencere: tur 2–8.**
  - İkincil (betimsel): tur 2–9 ve tur 2–5 (f'nin ölçüldüğü tura kadar).
- **İstatistik:** §7.1–§7.3 ile aynı: iki düzeyli bootstrap (gruplar ve her izole noktadaki cevaplar), 10 000 tekrar, yüzdelik %95 CI, §7.3 p tanımı, birincil pencerede model başına 12 kartlık Holm ailesi, etiketler yukarı / aşağı / uyumlu (+ eşdeğerlik alt notu). Seed: `stable_seed("pgg-main-s1-analysis", "H4x", model, kart, pencere)`. İkincil pencerelerde düzeltme yok.
- **Rapor:** model başına etiket sayıları ve ortalama Δ4, pencere 2–10 (ana) ile 2–8 yan yana; ayrıca 2–9 ve 2–5. Okuma kuralı yalnız betimsel: 2–8'de de düşüş sürüyorsa fazla çöküş son turlarla sınırlı değildir; 2–8'de kaybolursa ana H4 sonucu büyük ölçüde son tur etkisidir. Eşik konmadı.
- **Uygulama:** ayrı betik `pgg_analysis_explore.py` (ana betik `pgg_analysis.py` değiştirilmez); pencere 2–10 ile ana H4 nokta tahminini birebir yeniden üretmesi test edilir. Yalnız ana analiz birimleri (duyarlılık türevi yok). API çağrısı yok.
- **Sonuç (2026-10-17, keşifsel):** `results/main_s1_20261014_explore_h4.json`, sha256 `29990a814852fdfd560f9dec12ae3c63359e826b64f224283c5daaaacec0ab80`. Pencere 2–10 ana H4 tahminlerini birebir verdi (en büyük fark 0,0). Bir hücre (GPT boston_factual, 2–8: −2,05) bağımsız kodla yeniden hesaplandı ve tuttu. Holm'lu pencerelerde "aşağı" sayısı (2–10 → 2–8): DeepSeek 3 → 3, Mistral 7 → 5, GPT 3 → 0; "yukarı" hiçbir pencerede yok; negatif nokta tahmini 32 → 30 / 36. Ortalama Δ4 (2–10 → 2–8): DeepSeek −1,64 → −1,53, Mistral −1,53 → −0,80, GPT −2,17 → −1,43. 2–9 ve 2–5 pencereleri düzeltmesizdir; etiket sayıları Holm'lu pencerelerle karşılaştırılmaz.

### F.13 Aşama 1 muhakeme okuması: plan (2026-10-17, okumadan önce yazıldı)

- **Durum:** keşifsel ve nitel; hiçbir etiketi değiştirmez. Sonuçlar (F.11, F.12) görüldükten sonra, yorum için yapılır. Sayım değil okuma; nedensel iddia yok.
- **Sorular:**
  1. **Boston değer** (DeepSeek 0,15, Mistral 0,20; GPT 8,91): "personal liberty / speaking up against authority" katkı kararına nasıl bağlanıyor? GPT neden etkilenmiyor?
  2. **Riyad değer** (DeepSeek 13,06, Mistral 14,65): "respect family elders and tribal leaders" katkıya nasıl bağlanıyor?
  3. **Kopenhag değer** (DeepSeek 9,26 / minimal 1,62): "equal standing" nasıl okunuyor?
  4. **Mistral Atina olgusal** (1,59; diğer olgusal hücreler 5,5–7,8): 1 711 gün nasıl okunuyor?
  5. **GPT'de grup içinde doğan farklar** (değer: Kopenhag − Atina D(1) 1,09 → D(10) 6,88; Kopenhag − Boston 2,19 → 7,73): sonraki turlarda kart mı anılıyor, yoksa farkı geçmiş (gruptaki ilk katkılar) mi büyütüyor?
  6. **DeepSeek'in erken çöküşü** (H4 "aşağı": copenhagen_minimal, copenhagen_factual, athens_factual; 2–8'de de): gruplar izole tepkinin öngördüğünden neden hızlı düşüyor?
- **Örneklem:** her soru için ilgili hücrelerden önceden seçilen grup ve turlar (kural: hücrenin ilk 4 grubu, grup_id sırasıyla; turlar 1, 2, 5, 10; ajan 1; soru 5'te 5. ve 10. tur, soru 6'da tur 2–4), gerekçe + muhakeme. Ek olarak bütün satırlarda kart sözcüklerinin anılma sayımı (betimsel): liberty / authority, elder / tribal, equal standing, ancient, lawsuit / court / days.
- **Okuma yardımı:** alt ajanlar (Claude); aktarılan alıntılar ham dosyada doğrulanır.
- **Okuma sonucu (2026-10-17, keşifsel, nitel):** 7 okuma dosyası (A1a/A1b/A1c DeepSeek değer, A2a–A2c DeepSeek tur 2–4, B1–B3 Mistral, C1 GPT); A1a ve A1c alt ajanda güvenlik filtresine takıldığı için Claude tarafından kart pasajları ve son kararlar okunarak yapıldı. Alt ajanların aktardığı 34 alıntının 34'ü ham dosyada doğrulandı (2'si tırnak işareti farkıyla).
  1. **Boston değer:** DeepSeek'te kart anılıyor ama karar her seferinde ödeme hesabıyla 0 (minimal Boston da ~0,6; kart aşağı itmiyor). Mistral'da kart karar gerekçesi: "özgürlük = puanlarımı tutmak", "grup projesi = otorite / zorla kolektivizm" (16/16 notta); eşlemenin zorlama olduğunu ~8/16 kendisi söylüyor; 400 kararın 6'sı > 0.
  2. **Riyad değer** (iki model): önce "0 baskın" hesabı, sonra kart işbirliğini seçtiriyor; köprü kolektivizm / onur-utanç; Mistral kartta olmayan Arapça kavramlar (13/16) ve kaynaksız "Suudiler daha çok katkı verir" iddiaları (6/16) ekliyor; son turda dördü de işbirliğini sürdürüyor. Kart deneycinin ipucu olarak okunuyor (DeepSeek: "The persona is given for a reason"; "If I choose 0, I might fail the cultural manipulation check").
  3. **Kopenhag değer:** "equal standing" → "herkes aynı miktarı" kuralı (DeepSeek tur ortalaması 10,5 → 8,9; minimal Kopenhag 5,5 → 0,6). GPT'de son turda 57/64 karar ≥ 10 (diğer kartlarda 2–21/64, Riyad değer 51/64); "equal/fair" gerekçede tur 1–9 %36, tur 10 %73. GPT'nin değer çiftlerindeki "büyür" ve "grup içinde doğan fark" tamamen 10. turdan geliyor (Kopenhag − Atina D(9) 1,97, D(10) 6,88).
  4. **Mistral Atina olgusal:** 1 711 gün "kurumlar işlemiyor / güven yok" ve kartta olmayan Yunan klişeleri (12/16); 444 gün Boston'da 4/4 "süs metni". Fark çöküşün zamanında: tur ortalaması Atina 6,1 → tur 6'da 0; Boston 9. tura kadar ~9.
  5. **DeepSeek ve Mistral erken çöküşü (H4 "aşağı"):** misilleme değil; "bir bedavacı varken işbirliği kazandırmaz" ve işbirlikçileri sömürme hesabı. Betimsel kontrol (tur 2–9, ötekilerin önceki ortalaması ≥ 5): ötekilerde 0 veren varken ajan 0 veriyor DeepSeek %75, Mistral %64, GPT %25; 0 veren yokken %4 / %4 / %1. İzole soru yalnız ortalama gösterdiği için bu kanal simülasyonda yok.
  6. **Ortak:** talep / test farkındalığı yaygın (kart "araştırmacının ipucu"); bütün katkıların %96'sı tam 0, 10 ya da 20 (0: %46,5, 10: %45,0, 20: %4,4), yani simülasyonun sürekli değerleriyle karşılaştırmada kesiklilik bir sınırlılık.

### F.14 Keşifsel analiz: mikro kuralı grup verisinden öğrenmek (2026-10-18, hesaplanmadan önce yazıldı)

- **Durum:** keşifsel, önceden kayıtlı değil; H4 (F.11), F.12, F.13 ve Deney A (prereg_expA F-A.4) sonuçları görüldükten sonra yazıldı. Hiçbir ana etiketi değiştirmez.
- **Soru:** H4'teki boşluk (gruplar izole kuraldan simüle edilen yörüngeden daha düşük) (a) etkileşimin kendisinden mi, yoksa (b) kuralın yanlış bağlamda (izole, "round 5 of 10") ölçülmesinden mi geliyor? Kural **grup verisinden** öğrenilip simülasyon tekrarlanırsa boşluk kapanıyor mu?
- **Kural modelleri** (hepsi model × kart hücresi içinde, ampirik koşullu dağılım; simülasyon olasılıklı: her ajan, her turda, eğitim verisinde aynı durumdaki gerçek kararlardan birini çeker; böylece 0 / 10 / 20 kesikliliği korunur):
  - **R0:** H4'ün kendisi (izole f, doğrusal enterpolasyon, belirlenimci). Karşılaştırma tabanı.
  - **R1:** durum = (kendi önceki katkı dilimi, ötekilerin önceki ortalaması dilimi).
  - **R2:** R1 + "ötekilerden biri önceki turda 0 verdi mi".
  - **R3:** R2 + tur dilimi (2–8, 9, 10; son tur etkisi).
  - Dilimler: kendi önceki katkı {0, 1–9, 10, 11–19, 20}; ötekilerin ortalaması {0, (0, 5), [5, 10), 10, (10, 15), [15, 20]}.
  - **Seyrek durum için geri çekilme sırası:** hücre içi tam durum → aynı modelin bütün kartları, tam durum → hücre içi, en ince özellik düşürülmüş (R3'te tur, R2'de sıfır göstergesi, R1'de kendi dilimi) → … → hücre içi bütün kararlar. Geri çekilme oranları raporlanır.
- **Değerlendirme 1 — Aşama 1, bir-grup-dışarıda çapraz doğrulama:** her hücrede her grup sırayla dışarıda bırakılır; kural kalan gruplardan öğrenilir; dışarıdaki grup gözlenen 1. turundan başlatılıp S = 200 kez simüle edilir; S_g = simülasyonların ortalaması. Ölçü Δ_R = hücre içinde (O_g − S_g) ortalaması (H4 ile aynı tanım), pencere tur 2–10 (birincil, H4 ile karşılaştırılabilir) ve tur 2–8. Ayrıca tur başına grup ortalaması yörüngelerinin RMSE'si.
- **Değerlendirme 2 — bağımsız veri:** kurallar Aşama 1'in minimal hücrelerinin bütün gruplarından öğrenilir; Deney A'nın **B kolu** (aynı istem, yeni koşu; DeepSeek 48, Mistral 32, GPT 48 grup) gözlenen 1. turdan simüle edilir. R0 için Aşama 1'in minimal hücrelerinin izole f'i kullanılır.
- **İstatistik:** hücre etiketleri H4 kuralıyla (|Δ| > 2 ve bootstrap p < 0,05, model içinde 12 kartlık Holm; "aşağı / yukarı / uyumlu" + eşdeğerlik notu); bootstrap gruplar üzerinden (10 000), simülasyon belirsizliği S = 200 ile ortalanır. Seed `stable_seed("pgg-main-s1-rules", model, kart, kural, grup)`. Değerlendirme 2'de hücre başına aynı etiket kuralı (4 kart, Holm 4'lü), düzeltmesiz CI de verilir.
- **Okuma kuralı (yalnız betimsel, önceden yazıldı):**
  - R2 ya da R3 ile "aşağı" hücre sayısı belirgin azalır ve ortalama |Δ_R| R0'ın yarısının altına inerse: **"boşluk büyük ölçüde kuralın ölçüldüğü bağlamdan"** (yöntem dersi: LLM ajanları tek soruyla ayarlamak toplu dinamiği yanlış tahmin ettirir).
  - R3 ile de "aşağı" hücreler ve |Δ_R| R0 düzeyinde kalırsa: **"tek turluk durumla açıklanamayan bir grup etkisi"** (daha uzun geçmişe bağlılık ya da başka bir etkileşim; indirgenemezlik iddiası için gerekli ama yeterli değil).
  - Arada kalırsa: "kısmen".
- **Bilinen sınırlar:** kurallar yalnız bir önceki tura bakar (daha uzun bellek yok); homojen gruplar; durum dilimleri sonradan seçilmedi ama veriden önce de denenmedi; Değerlendirme 1 aynı koşunun gruplarıyla yapılır (bağımsızlık Değerlendirme 2'de).
- **Uygulama:** `pgg_analysis_rules.py` ve sentetik testleri; API çağrısı yok.
- **Sonuç (2026-10-18, keşifsel):** `results/rules_analysis.json`, sha256 `c74d48a183d8c4e4a5fc7e4b40432d44dd18dc5c301cf2ad1d60d4426d14fdc4` (kod `f112f39`). R0'ın ortalama Δ'sı H4'le aynı (DeepSeek −1,64, Mistral −1,53, GPT −2,17); R0'ın etiket sayıları H4'ten fazla (aşağı 4 / 9 / 7; H4'te 3 / 7 / 3), çünkü burada bootstrap yalnız gruplar üzerinden (izole f'in belirsizliği yok).
  - **Değerlendirme 1 (Aşama 1, bir-grup-dışarıda), tur 2–10:** R3 (kendi önceki katkı + ötekilerin ortalaması + "biri 0 verdi" + tur dilimi) bütün modellerde boşluğu kapatıyor: ortalama Δ DeepSeek −0,02, Mistral +0,12, GPT −0,03; 36 hücrenin 36'sı "uyumlu"; yörünge RMSE R0 → R3: 2,01 → 0,41, 3,76 → 0,58, 3,04 → 0,44. R1 / R2 (tur bilgisi yok) DeepSeek'te boşluğu kapatıyor (ort. Δ +0,43 / +0,31), Mistral'da (+1,58 / +1,57; 4 "yukarı") ve GPT'de (+0,61 / +0,71) simülasyonu gerçeğin üstüne taşıyor. "Biri 0 verdi" göstergesi (R1 → R2) toplamda neredeyse hiçbir şey değiştirmiyor.
  - **Değerlendirme 2 (bağımsız veri, Deney A B kolu, 128 grup):** R3 ortalama Δ DeepSeek −0,20, Mistral +0,55, GPT −0,10; 12 hücrenin 12'si "uyumlu"; RMSE R0 → R3: 2,10 → 0,41, 4,34 → 0,76, 2,83 → 0,67.
  - **Geri çekilme (R3, Aşama 1):** kararların ~%50–55'i hücre içi tam durumdan, ~%27–30'u modelin bütün kartlarından tam durumdan; geri kalanı daha kaba durumlardan.
  - **Okuma kuralına göre (önceden yazılmış):** R3 ile "aşağı" hücre sayısı 0'a, ortalama |Δ| R0'ın yarısının çok altına iniyor → **"boşluk büyük ölçüde kuralın ölçüldüğü bağlamdan"**. Tek turluk bellekli, oyun ufkunu bilen bir durum kuralı, grup yörüngelerini hem çapraz doğrulamada hem bağımsız yeni koşuda yeniden üretiyor. Eksik parça modele göre: DeepSeek'te izole cevabın kendisi (bağlam içinde ajan izole cevabından çok daha az katkı veriyor), Mistral ve GPT'de tur / ufuk bilgisi.
