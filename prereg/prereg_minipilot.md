ONAYLANDI — 2026-10-07 (kullanıcı)

> configs/minipilot.json'da prereg_approved=true ayrı bir developer göreviyle yapılır; koşu, kullanıcı 'BAŞLA' dedikten sonra ayrı görevle başlar.

# Mini-pilot ön kaydı (prereg_minipilot): EMİR 3 sonrası onaylı sürüm

- **Tarih:** 2026-10-07.
  - İlk taslak görev #63'te yazıldı.
  - Görev #66'da Görev E'ye göre yeniden düzenlendi.
  - Görev #72'de EMİR 2'ye göre güncellendi: Ç1–Ç8 kapatıldı, §13 karar tablosu oldu, M1 (§14) ve kalibre dry-run (§15) eklendi.
  - Bu sürüm görev #74'te EMİR 3'e göre güncellendi: çerçeve ataması, bütçe tavanları, kod düzeltmeleri (3a–3f), son dry-run (§15) ve kullanıcı onayı (§17). Değişiklikler sondaki değişiklik günlüğünde.
- **Durum:** kullanıcı tarafından onaylandı (2026-10-07) [EM3 Bölüm 5].
  - `configs/minipilot.json` içinde hâlâ **`"prereg_approved": false`** [CFG satır 3]. Bu değer true yapılmadan gerçek koşu (ve `--resume`) başlamaz; kod bunu reddediyor [DOC "Pre-registration lock"; T67 "Dry-run ve gerçek koşunun reddi"].
  - `prereg_approved` ayrı bir developer göreviyle true yapılır. Koşu, kullanıcı "BAŞLA" dedikten sonra ayrı bir görevle yapılır [EM3 Bölüm 5].
- **Belgenin niteliği:** iç yazılı plandır, kamusal kayıt değildir. Mini-pilotun ilk oyun çağrısından önce yazıldı [CL "Write the plan before the data"].
- **Bu görevde (#74) yapılmayanlar:** kod çalıştırılmadı, API çağrısı yapılmadı, depoya ve `runs/` altına yazılmadı.
- **Öncelik kuralı:** EMİR 3 en son talimattır. Önceki emirlerle (EMİR 2, Görev C, Görev E) çeliştiği her noktada EMİR 3 geçerlidir [EM3 giriş].

**Kaynak kısaltmaları**

| kısaltma | kaynak |
|---|---|
| **EM3** | EMİR 3 metni (güncel sürüm, Bölüm 1–6), üst yönetici ve kullanıcı, 2026-10-07. "EM3 3a" = Bölüm 3 madde 3a |
| **EM2** | EMİR 2 metni (Bölüm 1–4), üst yönetici, 2026-10-07. "EM2 m.n" = Bölüm 1 madde n |
| **T67, T68, T69, T70, T71** | Görev #67, #68, #69, #70, #71 sonuç raporları |
| **T73** | Görev #73 sonuç raporu (EMİR 3 Bölüm 1–3; testler, dry-run, sha256, linter) |
| **DRY** | `gorev73_dryrun.txt` (#73'ün son kalibre dry-run çıktısı) |
| **TO** | `gorev_tesisat_olcum.md` (#70, M1) |
| **D2** | `gorev_d2_kurum_uygulama.md` (#69) |
| **GE** | GÖREV E metni (E1–E6) ve görev #66 açıklaması |
| **GC** | GÖREV C (değiştirildi) metni, C1–C5. Workspace'te dosya olarak yok; #63 taslağındaki aktarımlarıyla kullanıldı |
| **CL** | depo `CLAUDE.md` |
| **CFG** | depo `configs/minipilot.json` (salt okunur). #73 sonrası hali 2026-10-07'de görev #74'te okundu; satır numaraları bu hale göredir |
| **REPO** | depo `pgg_game.py`, `frames/abstract_v2.json`, `frames/abstract_v3.json`, `frames/story_A.json`, `frames/SCHEMA.md`, `cerceve_linter.py`, `configs/cost_calibration_minipilot_m1.json`, `README.md` |
| **DOC** | depo `pgg_game.py` modül docstring'i |
| **KV3** | `kart_tasarimi_v3.md` (#65) |
| **KC3** | `pilot_cards_v3.json` (#65) |
| **KO** | `gorev_kurum_olgulari.md` (#64) |
| **HT / HR / DR** | `hikaye_taslaklari.md`, `hikaye_render_ornekleri.md`, `dryrun_c2/dryrun_{A,B}_{Sa,Sb}.txt` (#62) |
| **PV** | `pilot_v2_degerlendirme.md` (K1–K8, E1–E8, S1–S14) |
| **MUH** | `pilot_v2_muhakeme_okuma.md` |
| **BET** | `pilot_v2_betimsel.md` |
| **PR** | `prereg_pilot.md` (§n; ekler A1–A6, N, K) |
| **MT** | `gorev_mistral_tesisat.md` (#59) |
| **H11** | `gorev11_herrmann_degerler.md` |

**(tahmin)** = kaynağı olmayan çıkarım ya da varsayıma dayalı sayı. **(doğrulanamadı)** = verilen ama bu görevde kaynağından doğrulanamayan bilgi.

---

## 0. Sonuç (önce bu)

1. **Durum:** Bütün karar soruları (Ç1–Ç8, §13'teki 19 madde) EMİR 2 ve EMİR 3 ile kapandı. Kullanıcı belgeyi 2026-10-07'de onayladı (§17). Config'te `prereg_approved: false` [CFG satır 3]; true yapılması ayrı bir developer görevidir.
2. **Amaç:** Bilimsel sonuç üretmek değil. Mini-pilot dört şeyi sınar:
   - hikâye çerçevesinin deney ve literatür tanımasını azaltıp azaltmadığı (E2a);
   - nötr prosedür kartının ve değer kartının yönü (E2b);
   - farkın turlar boyunca seyri (E2c);
   - her modelin ana deneye uygunluğu (E3).
   Veri ana analize girmez.
3. **Son tasarım** [CFG satır 5–19; EM3 Bölüm 1; T73]:
   - Boston + Riyadh × 3 stil (minimal, değer v2, nötr prosedür kartı v3) = 6 kart. Yalnız N koşulu, homojen gruplar, hücre başına 2 grup, izole 5 nokta × 2 tekrar.
   - Çerçeveler: **abstract_v3 × deepseek, mistral, gpt** ve **story_A (kavanoz) × deepseek, gpt**.
   - Mistral yalnız abstract_v3 kolunda koşar; ana deneye uygunluğu (E3) ana deneyin çerçevesinde ölçülür. Çerçeve karşılaştırması yalnız DeepSeek ve GPT içinde yapılır (sınırlılık, §0.1 Ç3).
   - 5 kol × 600 = **3000** çağrı; yeniden istekler hariç (§2.4).
4. **Bütçe** [EM3 Bölüm 2; CFG satır 53–55]:
   - Sert tavan 10 USD, beklenti kapısı 4,5 USD (ortalamaya göre).
   - Model alt tavanları: Mistral 5, DeepSeek 5, GPT 0,5 USD.
   - Son kalibre dry-run'ın beklenen toplamı **~4,0440 USD (tahmin)**; kapıdan geçiyor [T73; DRY].
   - **Sınırlılıklar:**
     - Toplam p95 üst sınırı ~9,4348 USD (tahmin); 10 USD tavanın altında. Model p95'leri de kendi alt tavanlarının altında (§15).
     - Kapı kararı, Mistral'ın 2.–10. turlarda daha az düşüneceği varsayımına dayanır. Kullanıcı bu varsayımı onayladı (§15.4, §17).
     - Dry-run, değişiklikler commit edilmeden önce alındığı için "kod kirli" uyarısı verdi. Koşu görevi temiz kodla dry-run'ı tekrarlar (§9.2).
5. **M1 tesisat ölçümü** (§14): 20/20 çağrı başarılı, toplam 0,103482 USD. Mistral'ın reasoning metni 18/18 çağrıda döndü; en uzun çağrı 173,8 sn sürdü. **Bu veri hiçbir analize girmez.**

### 0.1 Kapatılan kararlar (Ç1–Ç8)

**Ç1. Çerçeve: Taslak A (kavanoz). KAPANDI** [EM2 m.1]
- **Dosya:** `frames/story_A.json`, kaynağı workspace `frames_story_A.json` (#62). Depoya #67'de kopyalandı.
- **Kilit:** sha256 `d8face90d927cb4d21ee23e53ace2458937f0e029996f88334441d3ab9190d7d`, `frame_files.story` içinde [CFG satır 25–28; T73]. Özet tutmazsa koşu da dry-run da çağrı yapmadan durur [T67].
- **Balıkçı hikâyesi yok.** Önceki taslaktaki `<CERCEVE_KULLANICI_KARARI>` yer tutucusu kaldırıldı.
- **C2 yasağı geçerli:** balıkçılık, otlak, orman gibi ortak kaynak ya da tükenme imgesi yok. `cerceve_linter.py`'nin yasaklı kök denetimi koşu başında çalışır (§4.1).

**Ç2. Hikâye kolu: DeepSeek ve GPT. KAPANDI** [EM2 m.2; EM3 Bölüm 1]
- `frames.story` = `["deepseek", "gpt"]` [CFG satır 18]. Atamanın gerekçesi Ç3'te.
- **GPT'de E2a sayımı yalnız `rationale` (Q) üzerinden yapılır.** Gerekçe: GPT'nin reasoning metni pilot v2'de 43/204 örneklem kaydında hiç dönmedi, dönen metin de büyük olasılıkla bir özet [MUH §3.2, §5.3; PV E8 (c)]. Reasoning özeti ayrıca betimsel sayılır; hipotez etiketine girmez.

**Ç3. abstract_v3 kolu üç modelde. KAPANDI** [EM2 m.3; EM3 Bölüm 1]
- **Atama:** abstract_v3 × deepseek, mistral, gpt; story_A × deepseek, gpt. `frames.abstract_v3` = `["deepseek", "mistral", "gpt"]` [CFG satır 16–19; T73].
- **Gerekçe** [EM3 Bölüm 1]:
  - Ana deney soyut çerçeveyle yapılacak. Mistral'ın ana deneye uygunluğu (E3) ancak o çerçevede ölçülebilir.
  - EMİR 2 madde 4'teki geri çekilme sırası ("kapı aşılırsa önce Mistral'ın abstract_v3 kolu çıkar") yanlış kolu seçiyordu. Bu kural, veri görülmeden düzeltildi ve **kaldırıldı**. Geçerli kural: kapı aşılırsa koşu yapılmaz, raporlanır; hiçbir kol çıkarılmaz (Ç4, §8.1).
- **Sonuçları:**
  - Aynı koşu içindeki temiz çerçeve karşılaştırması (abstract_v3 ↔ story_A; aynı kart, aynı sistem mesajı) **yalnız DeepSeek ve GPT içinde** yapılır.
  - **Sınırlılık:** Mistral bu karşılaştırmaya girmez; yalnız abstract_v3 kolunda koşar.
  - EM2 m.11'deki "uygunlukta esas kol abstract_v3" kuralı üç modele de uygulanır; Mistral'ın tek kolu da abstract_v3'tür (§7).
- **Pilot v2 ile karşılaştırmanın sınırlılığı (geçerli):** abstract_v2 (pilot v2) ile hikâye arasındaki fark yalnız çerçeve değildir. Karşılaştırma **karışıktır (confounded)**:
  1. **Kart:** v2 olgusal kart (tarih/iklim) yerine v3 nötr prosedür kartı geldi. Minimal ve değer kartları bayt bayt aynı [KV3 (v) §1].
  2. **Sistem mesajı:** abstract_v2'de "You are a participant in a decision-making experiment. The following describes you:" + kart vardı; yeni çerçevelerde yalnız kart var [REPO `frames/abstract_v2.json` satır 6; `abstract_v3.json` ve `story_A.json` `"system": "{card}"`].
  3. **İzole soru:** `repeated` ("neither the first nor the last round") yerine `fixed_round` ("This is round 5 of 10.") geldi [PR A4; GC C1].
  4. **Kural anlama çağrıları** eklendi. Oyun istemine taşınmazlar, ama ajan başına ek bir çağrıdır.
  5. **Sözcük kopyalama:** "experiment" abstract_v2 sistem mesajında geçiyor (Ç8).
  6. **Zaman:** farklı gün ve sağlayıcı durumu.
  - Bu yüzden pilot v2'ye karşı verilen E2a etiketi çerçevenin değil, **paketin** (çerçeve + kart + sistem mesajı + izole soru) etkisi olarak okunur.

**Ç4. Bütçe: 10 USD tavan, 4,5 USD kapı, model alt tavanları. KAPANDI** [EM2 m.4; EM3 Bölüm 2]
- **Toplam:** sert tavan 10 USD, beklenti kapısı 4,5 USD (ortalamaya göre) [CFG satır 53, 55].
- **Model alt tavanları:** Mistral 5, DeepSeek 5, GPT 0,5 USD. Aşılırsa **yalnız o model durur** ve raporlanır [CFG satır 54; T68 K3a].
- **Gerekçe** [EM3 Bölüm 2]: p95 değerleri eski tavanların üstündeydi. Koşunun dengesiz yarım kalmasını önlemek için tavanlar p95'i karşılayacak düzeye çıkarıldı. Beklenen harcama değişmez.
- **Kapı aşılırsa:** koşu yapılmaz, raporlanır; kol çıkarılmaz [EM3 Bölüm 1; CFG `_notes`; T73]. EMİR 2'deki Mistral abstract_v3 geri çekilmesi kaldırıldı (gerekçe Ç3).
- **Uygulama:** son dry-run'ın ortalama beklentisi ~4,0440 USD (tahmin), kapının altında [T73; DRY] (§15).

**Ç5. Kartlar: v3 olgusal kartlar olduğu gibi, stil adı "nötr prosedür kartı". KAPANDI** [EM2 m.5]
- **Kullanım:** v3 olgusal kartlar (`boston_factual`, `riyadh_factual`) mini-pilotta **olduğu gibi** kullanılır. Kart dosyası ve sha256 değişmez (§2.1).
- **Prereg'deki stil adı:** **"nötr prosedür kartı"**. Kartların `card_id`'leri ve dosyadaki stil etiketi (`factual`) değişmez.
  - Gerekçe: bu kartlar kuralların uygulanmasını anlatmıyor [KV3 (vi); EM2 m.5].
- **Rolü:** değer kartıyla aynı uzunlukta, **içeriksiz bir kontrol**.
- **E2b(b1)** buna göre yeniden yazıldı: beklenen sonuç minimal kartla aynı; etiketler betimsel (§5.2).
- **Kart soruları** [KV3 (vii)]:
  - **S1** (T3 / T2): kartlar olduğu gibi kullanıldığı için mini-pilotta T3 ile yazılmış KC3 kartları geçerli.
  - **S2** (Boston küçük dava cümlesi): mevcut metin kalır ("the yearly resident census is answered online or by mail").
  - **S5** (Riyad formülasyonu): mevcut metin kalır ("a power of attorney is issued online without a notary").
  - **S7 = Evet:** v3 nötr prosedür kartı ile minimal kart arasındaki fark ayrı başlıkla raporlanır (§11.2).
  - **S3, S4 ve S6:** Athens ve Copenhagen ile birincil doğrulama ana deneye ertelenir; mini-pilotu bekletmez (EM2 m.19).
- **Eski #63 §11 soruları:** hepsi EMİR 2 ile kapandı. Eşlemeleri:
  - soru 1 → m.1;
  - soru 2 → m.12;
  - soru 3 → E3 (§7);
  - soru 6 → m.16;
  - soru 7 → m.17;
  - soru 8 → m.9;
  - soru 9 → m.10;
  - soru 10 → m.13;
  - soru 11 → m.14;
  - soru 12 → m.15;
  - soru 14 → m.19;
  - soru 4, 5 ve 13 E ile kapanmıştı.

**Ç6. E3'te fark tanımı: max(e, g). KAPANDI** [EM2 m.6]
- Bir kart çiftinde fark, |D| > max(e, g) ise "var" sayılır (e = 2; g = iki grup arası fark, BET §5 tanımı) [PR §7].
- Pilot v2 GPT örneği:
  - `boston_minimal − boston_factual` D_grup(1) = 2,50, g ile aynı büyüklükte.
  - max(e, g) ile bu çift "fark yok" sayılır.
  - Önceki taslağın hesabına göre pilot v2 GPT bu tanımla U1'i tetiklerdi [BET §5.2; #66 Ç6].

**Ç7. Karşılaştırma ölçütü: pilot v2 aynı kural ve aynı kodla yeniden sayılır. KAPANDI** [EM2 m.7]
- **Yeniden sayım:** §5.0 sayım kuralı ve §5.1 sözlüğü, mini-pilot analizinde kullanılacak **aynı kodla** pilot v2 DeepSeek'in 540 geçerli karar satırına uygulanır.
  - Kaynak: `runs/pilot_v2_20261005/…jsonl`, BET §0 filtresi. API çağrısı yok.
- **Üst yöneticinin ön sayımı** (DeepSeek, 540 geçerli satır, §5.1 sözlüğü, R ∪ Q) [EM2 m.7]:
  - (i) paradigma/literatür: **528/540**. "public good" tek başına 528; "experiment" hariç tutulsa da 528.
  - (ii) oyun teorisi: **387/540**.
  - Bu sayılar bu görevde yeniden sayılmadı.
- **103/374** başka bir sözlükle yapılmış eski bir sayımdır. **Kullanılmaz.**
- **Analiz görevinin işi:** iki sayıyı kendi koduyla yeniden üretir. Tutmazsa farkı raporlar.
  - Tutmama durumunda hangi değerin esas alınacağı EM2'de belirtilmedi. Analiz görevi etiket vermeden önce bunu kullanıcıya sorar.
- **Eşikler:** (i) ≤ 176, (ii) ≤ 129 eşleşen yanıt (528 / 3 = 176; 387 / 3 = 129) (§5.1).

**Ç8. "experiment": dahil ve hariç iki biçimde. KAPANDI** [EM2 m.8]
- (i) sayımı iki biçimde raporlanır: "experiment" dahil ve hariç.
- **Hipotez etiketi "experiment" HARİÇ hal üzerinden verilir.** Gerekçe: pilot v2'de bu sözcük istemde (abstract_v2 sistem mesajında) geçiyordu.
- Ön sayıma göre pilot v2'de iki hal de 528, eşik iki halde de ≤ 176.

### 0.2 Bölüm–madde eşleme tabloları

**GE (Görev E):**

| GE maddesi | içerik | karşılandığı bölüm |
|---|---|---|
| E1 | Boston + Riyadh; minimal / değer / nötr prosedür kartı; N; homojen; 2 grup + 5 nokta × 2 tekrar; 3 model; çerçeve; run adı, seed; ana analize girmez; çağrı sayısı | §2, §3, §4; Ç1–Ç3 |
| E2a | tanıma: iki sayım, sabit sözlükler, kurallar, ölçüt, eşik | §5.0, §5.1; Ç7, Ç8 |
| E2b | kart yönü: nötr prosedür kartı ve değer kartı | §5.2 |
| E2c | etkileşim; D_grup(1), D_grup(9), D_grup(10) | §5.3 |
| E3 | uygunluk kuralı (3 ölçüt) | §7; Ç6 |
| E4 | durdurma, Görev A ekleri, bütçe (EMİR 3 ile 10 / 4,5 USD), maliyet tahmini, veri kalıcılığı | §8, §9; Ç4 |
| E5 | okuma: §9 listesi, tanıma, kural anlama, kimlik anılma; örneklem; tarihli ek | §11 |
| E6 | onaydan önce koşu yok | başlık; §9.2; §17 |

**EMİR 2:**

| EMİR 2 | içerik | bölüm |
|---|---|---|
| Bölüm 1, m.1–19 | prereg kararları | §0.1, §13 (karar tablosu) |
| Bölüm 2, K1–K5 | kod düzeltmeleri (T67, T68) | §4, §6, §8, §9, §13.1 |
| Bölüm 3, M1 | Mistral ön ölçümü ve tesisat çağrıları (T70) | §14 |
| Bölüm 3, M2 | kalibre dry-run, kapı kararı, sınırlılıklar (T71; EMİR 3 ile T73'ün dry-run'ı geçerli) | §15 |
| Bölüm 4, D2 ve NOT | ana deney için açık işler (T69) | §16 |

**EMİR 3:**

| EMİR 3 | içerik | bölüm |
|---|---|---|
| Bölüm 1 | çerçeve ataması; geri çekilme kuralı; sınırlılık | §0.1 Ç2–Ç4, §2.2, §2.4, §5.1, §7, §8, §13, §15 |
| Bölüm 2 | bütçe tavanları | §0.1 Ç4, §8, §9.3, §10, §15 |
| Bölüm 3, 3a–3f | kod düzeltmeleri (T73) | §4, §6, §7 U3, §9.2, §9.3, §9.5, §10, §11.1, §13.2 |
| Bölüm 4 | son kontroller (testler, dry-run, sha256, linter) | §13.2, §15 |
| Bölüm 5 | kullanıcı onayı ve üç uygulama kararı | başlık, §17 |
| Bölüm 6 | bekleyenler | §16 |

---

## 1. Amaç ve pilot v2'den farklar

> Pilot v2 ve #63 taslağıyla karşılaştırma yalnız bu bölümde yapılır.

**Neden mini-pilot:**
- PR §8.3'ün "tam deneye geçiş" satırı pilot v2'de karşılanmadı. DeepSeek grup yörüngelerinin 24/48'i hep 0, GPT yörüngelerinin 41/48'i tek değerdi [PV §0 madde 2; BET §4.2].
- Muhakeme metinlerinde tasarım kusuru işaretleri de vardı:
  - değer kartı davranış ipucu gibi okundu (K1);
  - deney ve literatür tanındı (K2) [PV §3].

**Pilot v2'den farklar**

| konu | pilot v2 | mini-pilot (bu belge) | kaynak |
|---|---|---|---|
| Çerçeve | abstract_v2 | abstract_v3 × deepseek, mistral, gpt; story_A (kavanoz) × deepseek, gpt | EM2 m.1–3; EM3 Bölüm 1; CFG satır 16–19 |
| Sistem mesajı | "You are a participant in a decision-making experiment. The following describes you:" + kart | yalnız kart | REPO abstract_v2/v3, story_A |
| İzole soru | `repeated` | `fixed_round`, "round 5 of 10" | GC C1; CFG `isolated_round_no` |
| Olgusal kart | v2 (tarih/iklim) | v3, prereg adı "nötr prosedür kartı" | KV3; KC3; EM2 m.5 |
| Modeller | deepseek, gpt, gemini | deepseek, mistral, gpt | CFG `models` |
| Kural anlama | yok | iki soru; satırlar `step = "comprehension"` | GC C4; T67 K2 |
| Bütçe | 1 USD tavan | 10 USD tavan, 4,5 USD kapı, model alt tavanları | EM3 Bölüm 2 |
| Sağlayıcı adı dönmeyen yanıt | kabul edilir, `n_provider_unknown` | sabitlenmiş modelde yeniden istenir ve sayılır | T68 K4 |
| Hipotezler | H1–H4 | E2a tanıma, E2b kart yönü, E2c etkileşim + E3 uygunluk | GE |

**#63 taslağından farklar (özet):**
- Çerçeve A (kavanoz) seçildi; B (sepet) depoya alınmadı [T67].
- abstract_v3 kolu üç modelde; hikâye kolu DeepSeek ve GPT'de (EMİR 3).
- H-tanıma ve H-oyun teorisi E2a'nın iki sayımına dönüştü. Karşılaştırma pilot v2'yle, yeniden sayılan değerlerle yapılıyor.
- E3 uygunluk kuralı eklendi.
- Bütçe 10 / 4,5 USD (EMİR 3); model alt tavanları eklendi.
- Kartlar `pilot_cards_v2.json` yerine `pilot_cards_v3.json`.

---

## 2. Kapsam ve tasarım (E1)

### 2.1 Kartlar ve hücreler

- **Kart dosyası:** `cards/pilot_cards_v3.json`, sha256 `a4f50d0f36296c4f38450a78210703c81aeabec1af4f72830c91a00266d7a9aa` [KV3 (v); T67 K1: depodaki kopya aynı özeti veriyor; CFG satır 5–6]. Config'te `cards_sha256` ile kilitli; tutmazsa koşu da dry-run da başlamaz (EM3 3e; §9.5). Yalnız Boston ve Riyadh kartları kullanılır (6 kart):

| card_id | stil (prereg adı) | metin | kaynak |
|---|---|---|---|
| boston_minimal | minimal | You are a 21-year-old university student living in Boston. | KC3 (v2 ile aynı) |
| boston_value | değer (v2) | … Where you grew up, people prize personal liberty and speaking up against authority. | KC3 (v2 ile aynı) |
| boston_factual | nötr prosedür kartı (v3) | … Where you live, the yearly resident census is answered online or by mail. | KC3; KV3 (ii) K1a–K1b |
| riyadh_minimal | minimal | You are a 21-year-old university student living in Riyadh. | KC3 |
| riyadh_value | değer (v2) | … Where you grew up, people strongly respect family elders and tribal leaders. | KC3 |
| riyadh_factual | nötr prosedür kartı (v3) | … Where you live, a power of attorney is issued online without a notary. | KC3; KV3 (ii) K4a–K4b |

- **Koşul:** yalnız N, ceza adımı yok [GC C2; GE E1; CFG satır 9].
- **Grup türü:** homojen; gruptaki 4 ajan aynı kartı taşır.
- **Kollar:** grup (4 ajan × 10 tur) ve izole.
- **Hücre:** kart × model × çerçeve.
  - Grup kolunda hücre başına 2 grup.
  - İzole kolda hücre başına 2 tekrar ve 5 nokta: `[0, 5, 10, 15, 20]`. `fixed_round`, `isolated_round_no` = 5 [CFG satır 11–15].

### 2.2 Modeller ve çerçeveler

```
"frames": {
  "abstract_v3": ["deepseek", "mistral", "gpt"],
  "story": ["deepseek", "gpt"]
}
```
[CFG satır 16–19]
- Bu atama EMİR 3 Bölüm 1'in atamasıdır: abstract_v3 üç modelde, story_A DeepSeek ve GPT'de.
- Mistral yalnız abstract_v3 kolunda koşar. Çerçeve karşılaştırması (abstract_v3 / story) yalnız DeepSeek ve GPT içinde yapılır; Mistral bu karşılaştırmaya girmez (sınırlılık, §0.1 Ç3).
- **Çağrılar:** deepseek 1200, gpt 1200, mistral 600; toplam 3000 (§2.4). #73 dry-run'ı aynı sayıları veriyor; fark yok [DRY].

### 2.3 Run adı, seed ve ana analizden hariç tutma

- **Run adı:** `minipilot_<YYYYMMDD>` [EM2 m.13].
  - Config'te şablon `minipilot_{run_date}` olarak duruyor. Yeni koşu başlarken koşu günüyle çözülür ve özete `run_template` olarak yazılır.
  - `--resume` yalnız açık adla çalışır: `--run minipilot_YYYYMMDD` [CFG satır 4; T67].
- **Seed namespace:** `pgg-minipilot` [EM2 m.13; CFG satır 51]. M1'in namespace'i `pgg-tesisat-olcum` bundan ayrıdır [TO].
- Aynı run adıyla ikinci yeni koşu yapılmaz. Kesinti olursa yalnız `--resume` kullanılır.
- **Pilot verisi ana analize girmez.** Ana deneyde kartlar yeniden koşulur [PR §9 "Pilot verisinin ana analizden hariç tutulması"; GE E1].

### 2.4 Çağrı sayısı (planlanan; yeniden istekler hariç)

Model × çerçeve kolu başına:
- **Grup katkı çağrısı:** 6 kart × 2 grup × 4 ajan × 10 tur = **480**.
- **İzole çağrı:** 6 kart × 2 tekrar × 5 nokta = **60**.
- **Kural anlama çağrısı:** **60**.
  - Grup kolu: 6 × 2 × 4 = 48 (ajan başına 1, 1. turdan önce).
  - İzole kol: 6 × 2 = 12 (çizelge başına 1).
- **Kol başına toplam:** 480 + 60 + 60 = **600** [DRY: her kol "600 çağrı (contribute_N=480, isolated=60, comprehension=60)"].

| model | kollar | çağrı |
|---|---|---|
| deepseek | abstract_v3, story | 1200 |
| gpt | abstract_v3, story | 1200 |
| mistral | abstract_v3 | 600 |
| **toplam** | **5 kol** | **3000** (kural anlama 300 dahil) |

- Sağlama: 1200 + 1200 + 600 = 3000. #73 dry-run'ı "TOPLAM 3000 çağrı" ve model başına 1200 / 600 / 1200 diyor; EMİR 3'teki sayılarla aynı, fark yok [DRY; T73].
- Bu sayılara yeniden istenen yanıtlar dahil değildir; onlar ayrıca sayılır (§9). Örnekler: geçersiz yanıt, sağlayıcı uyuşmazlığı, sağlayıcı adı dönmeyen yanıt, `discarded`, süre aşımı.

---

## 3. Modeller ve sağlayıcılar

| kısa ad | model | sağlayıcı (OpenRouter tag → beklenen ad) | M1'de görülen tarihli sürüm (`model_version`) | kaynak |
|---|---|---|---|---|
| deepseek | `deepseek/deepseek-v4.1-flash` | `deepinfra/fp8` → DeepInfra, nicemleme fp8 | `deepseek/deepseek-v4.1-flash-20260910` | CFG satır 36–40; PR A6 soru 1–2; TO §2 |
| mistral | `mistralai/mistral-large-4-0` | `mistral` → Mistral | `mistralai/mistral-large-4-0-20261006` | CFG satır 41–44; MT; TO §1 |
| gpt | `openai/gpt-6-luna` | `openai` → OpenAI | `openai/gpt-6-luna-20260922` | CFG satır 45–48; PR A6 soru 3; TO §2 |

**Gönderilen ve gönderilmeyen parametreler** [CFG `_notes`; MT; TO §0]:
- **Gönderilenler:** `allow_fallbacks: false`, `require_parameters: true`, `max_tokens` 16000, `response_format` `json_object`. DeepSeek'e ayrıca `quantizations: [fp8]`.
- **M1 sonucu:** `require_parameters: true` açıkken üç modelin isteği de ilk denemede kabul edildi [TO §2].
- **Gönderilmeyenler:** `temperature` ve `reasoning_effort`. Logda "default" yazılır.
- **fp8 doğrulanamıyor:** DeepSeek yanıtında nicemleme alanı dönmüyor. fp8 yalnız istekte sabitleniyor [TO §2].

**Reasoning metni erişimi (E2a için önemli):**
- **DeepSeek:** uzun ham muhakeme döndürüyor; pilot v2 ortalaması 1748,8 token [PV §4.3].
- **GPT:** metin büyük olasılıkla özet; pilot v2 örnekleminde 43/204 kayıtta hiç yok [MUH §3.2]. E2a GPT'de yalnız rationale ile yapılır (Ç2).
- **Mistral:**
  - M1'de, abstract_v3 oyun istemleriyle, **18/18 çağrıda reasoning metni döndü** (6 049–15 260 karakter) [TO §1].
  - Mini-pilotta Mistral yalnız abstract_v3'te koşar; M1 ölçümü aynı çerçeveden.
  - Metin dönmeyen satırlarda Mistral'ın E2a sayımı yalnız rationale'e dayanır (§5.0).

**Sürüm logu ve denetimi** [EM2 m.15; T68 madde 15]:
- Her satıra ve ham log kaydına `model_version` yazılır. Değer, `openrouter_metadata` içindeki, yanıtı veren uç noktanın tarihli model adıdır.
- `check_snapshot: true` ve `snapshot_version_models: ["mistral"]` [CFG satır 58–59]:
  - Mistral'ın tarihli sürümü istenen modele uymalı.
  - Koşu boyunca ilk görülen sürüm değişmemeli; değişirse koşu `model_version_changed` ile durur.
  - Sürüm dönmezse koşu durmaz, `n_model_version_unknown` sayılır.

**Yürütme:** eşzamanlı çağrılar, `workers` 4, `parallel_units` 3 [CFG satır 61–62]. Config'te batch alanı yok; batch bekleme kuralı bu koşuya uygulanmaz.

---

## 4. Çerçeve

### 4.1 Hikâye çerçevesi: Taslak A (kavanoz)

- **Dosya:** depo `frames/story_A.json`; `"name": "story_A_jar"`, `"kind": "story"` [REPO].
- **sha256:** `d8face90d927cb4d21ee23e53ace2458937f0e029996f88334441d3ab9190d7d`, `frame_files.story` içinde kilitli [CFG satır 25–28; T73].
- **Kurgu** [REPO `story_A.json` `rules`]:
  - Bir telefon uygulaması her gün her kullanıcının bakiyesine 20 kredi ekler; krediler ücretsizdir.
  - 4 kullanıcı, eklenen kredilerden ne kadarını ortak "jar"a koyacağına karar verir.
  - Gün sonunda kavanoz {multiplier} katına çıkar ve sabit kural gereği 4 kişiye eşit bölünür.
  - Kazanma ya da emek söylemi yok.
  - Sistem mesajı yalnız kart (`"system": "{card}"`).
- **Önceki sha256'lar:** #62'deki sha256 (`9fec03ee…7db9`, Ek A) ve #67'deki kilit bu dosyanınkiyle aynı değildir. #67, dosyaya `kind` alanını ekledi ve q2'nin son cümlesini değiştirdi; #73 q2'yi EM3 3b'ye göre yeniden değiştirdi [T67 K1–K2; T73]. Geçerli kilit yukarıdaki özettir; eski → yeni özetler değişiklik günlüğünde.
- **Koşu başı denetimleri** [T67 K1; EM2 K1; EM3 3d]:
  - Özet tutmazsa koşu da dry-run da çağrı yapmadan durur.
  - `cerceve_linter.py`'nin yasaklı kök denetimi `RunConfig._validate_frames` içinde çalışır. Denetim dosyadaki metinleri ve modele gidecek render edilmiş istemleri tarar. Kök bulunursa koşu da dry-run da başlamaz.
  - EMİR 3 3d ile linter **her çerçevede varsayılan olarak** çalışır; yalnız dosyasında açıkça `"kind": "abstract"` yazan çerçeve muaftır. `kind` alanı zorunludur (§9.5).
  - Yasaklı kökler (16) [REPO `cerceve_linter.py` satır 50–52]: game, experiment, participant, player, contribut, public good, group project, cooperat, free rid, commons, tragedy, punish, token, payoff, nash, equilibrium.
  - #73'ün son dry-run'ında story_A: "GEÇTİ (kind story; yasaklı kök yok)" [DRY].
  - "Kirli kod" denetimi `frames/*.json`, `configs/*.json` ve `cards/*.json` dosyalarını da kapsar.
- **C2 yasağı:** balıkçılık, otlak, orman gibi ortak kaynak ya da tükenme imgesi yok [HT §2 madde 5; EM2 m.1].
- **Kural anlama soruları:** aynı yer tutucularla gelir; cevap anahtarı 28 / −6 (§6.2–6.3).
- **Ceza adımı:** dosyada P koşulu için bir ceza adımı ("reductions") var. Mini-pilot yalnız N koşulunu koştuğu için bu adım istemlere girmez. Ana deneyden önce yeniden yazılacak (§16).
- **Değişmezlik:** veri görüldükten sonra çerçeve değiştirilmez. Motor her satıra `frame_sha256` yazar; dosya değişirse `--resume`'u reddeder [DOC; README].

### 4.2 abstract_v3 (deepseek, mistral, gpt)

- **Dosya:** `frames/abstract_v3.json`, `"kind": "abstract"`. sha256 `09b4d67b7b6640e33c0c265bec3324b2572293e61ac5d58bac798757ecb93e5a` [CFG satır 21–24; T73].
- **Sistem mesajı:** yalnız kart.
- **Kurallar:** A2.1 (f) ile aynı.
- **İzole soru:** `fixed_round`, "This is round 5 of 10. In the previous round the other 3 players of your group contributed, on average, {X} points each." [REPO `frames/abstract_v3.json`; #63 §3.1; TO §0].
- **Linter:** abstract_v3 bilerek "game/contribute" içerir. Dosyada açıkça `"kind": "abstract"` yazdığı için yasaklı kök denetiminden muaftır. #73'ün son dry-run'ında sonuç: "MUAF (kind "abstract" declared in the file)" [DRY; T73].

---

## 5. Hipotezler (E2; her iki yönüyle)

Mini-pilot **betimseldir**. Anlamlılık testi yapılmaz. "Azalır / azalmaz", "var / yok" gibi ifadeler önceden yazılmış mekanik etiketlerdir.

### 5.0 Ortak sayım kuralları (E2a)

- **Metin alanları ayrı ayrı sayılır:**
  - (R) yanıtın `reasoning` metni;
  - (Q) `rationale` alanı.
  - Ayrıca iki metinden birinde eşleşme olan yanıtlar (R ∪ Q) raporlanır.
- **Hipotez etiketi hangi alanla verilir:**
  - **DeepSeek:** (R ∪ Q).
  - **GPT:** (Q) (Ç2).
  - **Mistral:** reasoning metni dönen satırlarda (R ∪ Q), dönmeyenlerde (Q). Metin dönmeyen satır sayısı raporlanır. M1'de metin 18/18 döndü [TO §1].
  - **Karşılaştırma ölçütü:** pilot v2 değeri aynı alan tanımıyla (DeepSeek, R ∪ Q) hesaplanır (Ç7).
- **Birim:** yanıt (karar satırı). İlgili alanda sözlükten **en az bir** eşleşme varsa yanıt "eşleşen" sayılır; aynı yanıttaki birden fazla eşleşme 1 sayılır.
  - **Karar satırları:** grup katkı satırları (tur 1–10) ve izole satırlar; kol başına 480 + 60 = 540.
  - **Kural anlama satırları** sonuç dosyasında `step = "comprehension"` ile ayrılır. **Analiz bu adıma göre süzer:** bu satırlar karar satırı sayılmaz, ayrı raporlanır, hipoteze girmez [EM2 K2; T67 K2].
- **Oran:** eşleşen yanıt / geçerli karar satırı, model × çerçeve başına.
- **Büyük/küçük harf ve kök kuralı:**
  - Metin küçük harfe çevrilir; tire ve alt çizgi boşluk sayılır.
  - Eşleşme alt dizgi aramasıyla yapılır, sözcük sınırı aranmaz. Bu, `cerceve_linter.py` ile aynı mantıktır [HT §4; KV3 (v)].
  - Böylece sözlük maddesi bir kök gibi çalışır: `public good` "public goods" ile, `experiment` "experimental" ve "experiments" ile, `nash` "Nash's" ile eşleşir.
  - **Yazım varyantları** (aşağıdaki tablo) kabul edildi [EM2 m.10].
- **Olumsuzlama da sayılır:** "this is not a public goods game" bir eşleşmedir; adı anmak tanımanın işaretidir (tanım seçimi).
- **İstem kontrolü:** koşudan önce sözlükler her çerçevenin render edilmiş istemlerine (sistem, kullanıcı, şema) uygulanır; istemde geçen terim raporlanır.
  - story_A'nın istemleri yasaklı kök denetiminden temiz geçiyor. Bu kökler experiment, public good, commons, nash ve equilibrium'u da içeriyor [§4.1].
  - abstract_v3 bu denetime tabi değil. İstem kontrolü analiz görevinde ayrıca yapılır.
- **Elle denetim:** her eşleşme bağlamıyla (±100 karakter) dışa aktarılır. Yalnız açık teknik yanlış pozitifler, gerekçesiyle ve listelenerek çıkarılabilir; örnek: `commons` ⊂ "commonsense". Sözlük veri görüldükten sonra genişletilmez.

### 5.1 E2a: Tanıma (iki ayrı sayım)

**Sözlükler (GE'de sabitlendi; varyantlar EM2 m.10 ile kabul):**

| sayım | GE terimi | eşleşme kökü (normalleştirilmiş metinde) | yazım varyantı |
|---|---|---|---|
| (i) paradigma/literatür | public good | `public good` | — |
| | commons | `commons` | — |
| | Fehr | `fehr` | — |
| | Gächter | `gächter` | `gachter`, `gaechter` |
| | Herrmann | `herrmann` | — |
| | Ostrom | `ostrom` | — |
| | experiment | `experiment` | — (Ç8: dahil ve hariç) |
| (ii) oyun teorisi | Nash | `nash` | — |
| | subgame | `subgame` | `sub game` ("sub-game" normalleşince bu biçimi alır) |
| | backward induction | `backward induction` | `backwards induction` |
| | equilibrium | `equilibri` (equilibrium, equilibria) | — |

- (i) ve (ii) **ayrı ayrı** raporlanır; kesişmezler.
- (i) iki biçimde verilir: "experiment" dahil ve hariç. **Etiket hariç hal üzerinden verilir** (Ç8).
- **Geniş sözlükler** (#63 taslağındakiler: prisoner, free rid, dominant strateg vb.) **ikincil sayım** olarak ayrı raporlanır. Hipoteze girmezler [EM2 m.10].

**Karşılaştırma ölçütü (Ç7):**
- Pilot v2 DeepSeek (abstract_v2), 540 geçerli satır, R ∪ Q; üst yöneticinin ön sayımı [EM2 m.7]:
  - (i) **528/540** (= %97,78). "experiment" hariç de 528.
  - (ii) **387/540** (= %71,67).
- Analiz görevi bu iki sayıyı mini-pilotla aynı kodla yeniden üretir. Tutmazsa raporlar (Ç7).
- Mini-pilotta DeepSeek'in hikâye kolunda da 540 karar satırı vardır (§2.4); payda aynıdır.

**Hipotez** (DeepSeek, hikâye kolu; her sayım için ayrı; 1/3 eşiği iki sayımda da [EM2 m.9]):
- **Azalır:** eşleşen_hikâye ≤ (1/3) × eşleşen_pilotv2.
  - (i), "experiment" hariç: **≤ 176**/540 (528 / 3 = 176; oran ≤ %32,59).
  - (ii): **≤ 129**/540 (387 / 3 = 129; oran ≤ %23,89).
- **Azalmaz:** eşik aşılırsa. Bu durumda hikâye tanımayı yeterince azaltmıyor demektir. Model yapıyı (çarpan ve eşit bölüşüm) yine paradigmaya bağlıyor olabilir (HT §8'in yazdığı risk).
- **(ii) için beklenti: "azalmaz"** [EM2 m.9]. Ödeme yapısı gizlenmiyor (PV K3: #480, #969).
- **Ek not (etiket değil):** eşleşen_hikâye > eşleşen_pilotv2 ise ayrıca "arttı" diye yazılır.
- **Okuma sınırı:** pilot v2'ye karşı etiket paketin etkisidir (Ç3 sınırlılığı).
- **Aynı koşu içinde çerçeve karşılaştırması:** DeepSeek ve GPT'de story_A ile abstract_v3, aynı 1/3 kuralıyla ayrıca etiketlenir.
  - Kart ve sistem mesajı iki kolda aynıdır; karşılaştırma bu açıdan karışık değildir.
  - GPT'de alan (Q)'dur.
  - Mistral bu karşılaştırmaya girmez; yalnız abstract_v3 kolunda koşar (Ç3, sınırlılık) [EM3 Bölüm 1].
- **Mistral:** E2a sayımları ((i) ve (ii)) **yalnız abstract_v3 kolundan** yapılır ve **betimseldir**; hipotez etiketi verilmez [EM3 Bölüm 1]. Mistral'ın pilot v2 verisi yok.
- **GPT'nin pilot v2 karşılaştırması:** GPT'nin metin alanı karşılaştırılamaz; oranları betimsel raporlanır.
- **1/3 ölçütünün kökeni:** GC C3'e göre ilk çalışmanın manipülasyon kontrolü ölçütüdür. İlk çalışmanın deposu kaynaklarda yok; orijinal tanımı (doğrulanamadı).

### 5.2 E2b: Kart yönü

**Tanımlar** (model × çerçeve başına):
- D_fac = `boston_factual` − `riyadh_factual` (nötr prosedür kartı, v3).
- D_val = `boston_value` − `riyadh_value` (değer, v2).
- D_min = `boston_minimal` − `riyadh_minimal` (minimal; b1'in karşılaştırma ölçütü).
- Her biri dört ölçüde verilir: D_iso (izole 5 nokta ortalaması), D_grup(1), D_grup(9) ve D_grup(10). Ölçüler PR §7 tanımlarıyla hesaplanır.

**Etiket (e = 2; GE):**
- D > 2: **insan yönü** (Boston > Riyadh).
- D < −2: **ters yön**.
- |D| ≤ 2: **fark yok**.
- g (iki grup arası fark, BET §5 tanımı) her satırın yanında raporlanır. max(e, g) ile verilen etiket ikinci sütunda yer alır (Ç6 ile tutarlı).
- Etiketler **betimseldir** [EM2 m.5].
- **"İnsan yönü" adı neden:** Herrmann verisinden hesaplanan şehir ortalamalarında Boston N'de 9,33, Riyadh 7,63 [H11 satır 24, 33]. Bunlar yayımlanmış değil, hesaplanmış değerlerdir. Mini-pilot insan verisiyle karşılaştırma yapmaz; yalnız işaretin adı buradan gelir.

**Hipotezler:**
- **(b1) Nötr prosedür kartı.**
  - Bu kart kuralların uygulanmasını anlatmaz. Değer kartıyla aynı uzunlukta, içeriksiz bir kontroldür [EM2 m.5; KV3 (vi)].
  - **Beklenen sonuç: minimal kartla aynı.** Operasyonel olarak iki betimsel denetim yapılır:
    1. D_fac'ın etiketi D_min'in etiketiyle aynı mı?
    2. Her şehirde `factual − minimal` stil çifti farkı "fark yok" mu (|D| ≤ 2)? Bu fark S7 gereği ayrı başlıkla raporlanır (§11.2).
  - Sapma olursa "nötr prosedür kartı minimal karttan ayrıştı" diye betimsel not edilir; bir kart etkisi iddiası kurulmaz.
  - Pilot v2'deki olgusal kart farkı farklı bir kart metnine aittir ve karşılaştırılmaz.
- **(b2) Değer kartının ters yönü tekrarlanır mı?**
  - **Tekrarlanır:** D_val < −2.
  - **Tekrarlanmaz:** D_val ≥ −2. Bu, "fark yok" ya da "insan yönü" olarak ayrıca adlandırılır.
- **Pilot v2 referansı** (DeepSeek, abstract_v2; betimsel) [BET §5.1, §2.1]:
  - D_iso = −3,50, D_grup(1) = −13,75, D_grup(10) = −20,00.
  - D_grup(9) = 0,00 − 20,00 = **−20,00** (BET §2.1 t9 hücre ortalamalarından, #66'da hesaplandı).
  - Gemini: D_grup(10) = −9,38. GPT: dört ölçünün hiçbirinde |D| > 2 yok [BET §5.2–§5.3].
  - Değer kartı metni değişmediği için (b2) karşılaştırması yalnız kart açısından eşleşiktir. Çerçeve ve sistem mesajı farkı sürer (Ç3).

### 5.3 E2c: Etkileşim (betimsel)

- **Kapsam:** §5.2'deki iki şehir çifti (D_fac, D_val). Ayrıca §11.2'de tüm 9 kart çifti için bilgi amaçlı verilir.
- **Etiketler** PR §7 H2'den, e = 2:
  - **Büyür:** D_grup(10) D_grup(1) ile aynı işarette ve |D_grup(10)| > |D_grup(1)| + 2.
  - **Söner:** |D_grup(10)| < |D_grup(1)| − 2 ya da işaret değişti.
  - **Korunur:** ||D_grup(10)| − |D_grup(1)|| ≤ 2. Düz yörüngeler de bu etikete girer.
- **D_grup(9):** aynı sınıflama D_grup(9) ile ayrıca verilir (PV E6). 9 ile 10 ayrışırsa bu, son tur etkisi notuyla raporlanır.
- **H1b koşulu yok:** D_iso farkı olmasa da etiket verilir. Etiket betimseldir.
  - |D_grup(1)| ≤ 2 ve |D_grup(10)| > 2 ise "grup içinde doğan fark" diye ayrıca not edilir.

---

## 6. Kural anlama kontrolü

### 6.1 Nasıl sorulur [README "Rule comprehension"; #61; REPO `frames/SCHEMA.md` satır 133; T68 madde 17]

- **Grup kolu:** her ajana 1. turdan önce ayrı bir çağrıyla bir kez sorulur. Satır `round: 1`, **`step: "comprehension"`** olarak yazılır.
- **İzole kol:** her izole çizelgeden önce bir kez sorulur.
- **İstem:** sistem mesajı kart; kullanıcı mesajı kurallar + kural anlama bloğu. Geçmiş yok.
- **Şema:** `{"q1": int, "q2": int, "rationale": str}`.
- **Ayrıştırıcı:** "+3" biçimini ve Unicode eksi işaretli "−3" biçimini de geçerli kabul eder [T67 K2]. Bu normalleştirme ve degraded logu EMİR 3 sonrası da korunur [EM3 3b; T73].
- **Geçersiz yanıt:** yalnız şemaya uymayan yanıt geçersizdir ve yeniden istenir. **Yanlış cevap geçerli satırdır.** `comp_q1_correct` ve `comp_q2_correct` alanlarına yazılır, oyun sürer.
- **Kural anlama çağrısı koşuyu durdurmaz** [EM3 3c; T73 3c]:
  - `max_invalid` (3) tükenirse kural anlama satırı **`comp_missing: true`** olarak yazılır, `pgg_comprehension_missing` olayı loglanır ve oyun devam eder.
  - Kural anlama geçersizleri model başına **ayrı raporlanır** (`n_comp_invalid`, `n_comp_parse_fail`, `n_comp_missing`) ve karar çağrılarının **%5 geçersiz tavanına sayılmaz** (§9.3).
  - Maliyetleri bütçeye girer.
- **Bağımsızlık:** çağrılar durumsuzdur; kural anlama yanıtı oyun istemine girmez [PR §6.1].
- **Analizde süzme:** analiz görevi kural anlama satırlarını `step == "comprehension"` ile ayırır. Bu satırlar karar satırı sayılmaz (E2a, E2b, E2c, U1); U2 ve U3'te kullanılır (§7) [EM2 K2].
- **Sürdürme:** kural anlama sırasında kesilen birim baştan başlar. Sürdürmede gönderilen istekler kesintisiz koşudakilerle bayt bayt aynıdır; bu, abstract_v3 ve story_A için testli [T68 K5].

### 6.2 Soruların metni

q2'nin son cümlesi EMİR 3 3b'ye göre değişti: "Give the change as a whole number (it can be positive, zero or negative)." Üç çerçevede de geçerlidir (abstract_v3 ve story_A; abstract_v2'de kural anlama yok). "+3 / -3" örneği kaldırıldı [EM3 3b; T73 3b; REPO `frames/abstract_v3.json` ve `frames/story_A.json` satır 61].

- **abstract_v3** [REPO `frames/abstract_v3.json` satır 52–62]:
```
RULE CHECK
Before you make any decision, answer two questions about the rules above. Your answers do not change anyone's earnings.
1. Suppose that in a round you contribute {own} points and the other {n_others} players contribute {other_1}, {other_2} and {other_3} points. What are your total earnings in that round?
2. Suppose that the contributions of the other players stay the same. If you contribute {delta} more points to the group project, by how much do your own total earnings in that round change? Give the change as a whole number (it can be positive, zero or negative).
Answer each question with a whole number.
```
- **story_A** [REPO `frames/story_A.json` satır 52–63]:
```
CHECK OF THE JAR'S RULES
Before you choose anything, answer the questions below about the jar's rules. Your answers do not change anybody's balance.
1. Suppose that on a day you put {own} credits into the jar and the other {n_others} users put in {other_1}, {other_2} and {other_3} credits. How many credits do you end that day with?
2. Suppose that the other users put the same amounts into the jar. If you put {delta} more credits into the jar, by how much does what you end that day with change? Give the change as a whole number (it can be positive, zero or negative).
Answer each question with a whole number.
```
- **Yer tutucu değerleri** (iki çerçevede aynı) [REPO `answer`]:
  - own = 8;
  - others = 4, 12, 16;
  - delta = 10.
- **Şema ve denetim:** şema tam sayı kalır; işaretli sayı normalleştirmesi ve degraded logu korunur. #73'ün testine göre motorun ürettiği bütün istemler (her tur, ceza adımı, izole soru, şema) eski dosyalarla (533aca8) q2 cümlesi dışında birebir aynıdır [T73 3b].
- q2 değişince iki çerçevenin sha256'sı değişti; config'teki kilitler yeniden yazıldı (§4; değişiklik günlüğü).

### 6.3 Cevap anahtarı (motor hesaplar)

- q1 = 20 − 8 + 0,4 × (8 + 4 + 12 + 16) = 12 + 16 = **28**.
- q2 = 10 × (0,4 − 1) = **−6**.
- Elle yeniden hesaplandı.

### 6.4 Yanlış cevaplar

- **Satır ve birim dışlama yok; yalnız duyarlılık analizi yapılır** [EM2 m.12]. Bir grup ajanını atmak diğer üç ajanın geçmişini bozar.
- E3, yanlış oranını model düzeyinde uygunluk ölçütü yapar (U2, §7).
- **Duyarlılık:** E2b ve hücre ortalamaları bir kez de yalnız "anlama-tam" birimlerle verilir:
  - grup birimi için dört ajanın ikişer sorusu da doğru;
  - izole çizelge için çizelgenin iki sorusu da doğru.

---

## 7. Modelin ana deneye uygunluk kuralı (E3)

Aşağıdakilerden **biri** gerçekleşirse model için **"ana deney setinden çıkarılması önerilir"** diye raporlanır. **Otomatik çıkarma yapılmaz;** karar kullanıcınındır. Ölçütler model × çerçeve kolu başına hesaplanır.

- **Esas kol** [EM2 m.11; EM3 Bölüm 1]:
  - **Uygunlukta esas kol abstract_v3'tür.** Üç modelde de abstract_v3 kolu esastır.
  - DeepSeek ve GPT'de story kolu bilgi amaçlı raporlanır.
  - **Mistral'ın E3 uygunluğu abstract_v3 kolundan değerlendirilir** (Mistral'ın tek kolu; §17 (b)).

| # | ölçüt (GE, aynen) | ölçülebilir tanım | 600 çağrılık kolda sayısal sınır |
|---|---|---|---|
| U1 | Yörüngelerin ≥ %80'i tek değerde **ve** hiçbir kart çiftinde fark yok | **Yörünge:** grup kolunda bir ajanın 10 turluk katkı dizisi; kol başına 6 × 2 × 4 = 48 yörünge. **Tek değer:** 10 turun hepsinde aynı katkı (BET §4 tanımı; hep 0 ve hep 20 dahil). **Kart çifti:** 6 kartın 9 çifti (her şehirde 3 stil çifti ve her stilde 1 şehir çifti; BET §5 düzeni). **Fark:** D_iso, D_grup(1), D_grup(9) ve D_grup(10) ölçülerinden herhangi birinde \|D\| > **max(e, g)**, e = 2 (Ç6). U1 = (tek değer yörünge / 48 ≥ 0,80) **VE** (9 çiftin hiçbirinde fark yok) | 0,80 × 48 = 38,4, yani **≥ 39/48** tek değer yörünge |
| U2 | Kural anlama kontrolünde yanlış oranı > %20 | **Birim:** geçerli kural anlama satırı (`step = "comprehension"`). **Yanlış:** q1 **ya da** q2 anahtara uymuyor [EM2 m.11]. Oran = yanlış satır / geçerli kural anlama satırı. `comp_missing` satırları geçerli satır değildir; paydaya girmez, ayrı sayılır (§6.1) | 0,20 × 60 = 12, yani **≥ 13/60** yanlış |
| U3 | `reasoning_capped` oranı > %5 | **reasoning_capped:** reasoning_tokens ≥ max_tokens − 4096 = 11 904 (A2; README). **Mistral'da** max(reasoning_tokens, completion_tokens) ≥ 11 904 (EM3 3a; §9.5). **Payda: karar + kural anlama satırları** [EM2 m.11]. Oran = `n_reasoning_capped` / geçerli satır | 0,05 × 600 = 30, yani **≥ 31/600** |

- **Pilot v2 örneği** (yalnız açıklama, karar değil):
  - GPT'de tek değer oranı 41/48 = %85,4 [BET §4.2]; U1'in ilk yarısını karşılar.
  - İkinci yarı max(e, g) tanımıyla karşılanır: `boston_minimal − boston_factual` D_grup(1) = 2,50 "fark yok" sayılır [BET §5.2; Ç6].
  - DeepSeek'te pilot v2'de 11 904 eşiğine ulaşan 10 yanıt vardı [README A2; #63 §8.1]. 10/540 = %1,85 < %5.
- **M1 bilgisi** (analiz verisi değil): Mistral'ın 18 çağrısında en yüksek reasoning değeri 3 895, en yüksek completion değeri 4 113 token; max kuralıyla da 11 904 eşiğinin çok altında [TO §1.1].

---

## 8. Bütçe (EMİR 2 madde 4; EMİR 3 Bölüm 2)

### 8.1 Kurallar

- **Sert tavan 10 USD** [CFG satır 53; EM3 Bölüm 2]:
  - Ölçü birikmiş `usage.cost`.
  - Dahil olanlar: yeniden istenen yanıtlar, sağlayıcısı uyuşmayan ya da sağlayıcı adı dönmeyen yanıtlar, `discarded` yanıtlar, kural anlama geçersizleri ve süre aşımları (aşağıda).
  - Tavana ulaşılınca yeni çağrı gönderilmez [DOC; README].
- **Model alt tavanları: Mistral 5, DeepSeek 5, GPT 0,5 USD** [CFG satır 54; T68 K3a; EM3 Bölüm 2]:
  - Bir modelin birikmiş maliyeti kendi tavanına ulaşınca **yalnız o model durur**, öbürleri sürer.
  - Özette model başına `model_stops` yazılır: neden, an, segment, maliyet, tavan, yanıt sayısı.
  - Sürdürmede tavan önceki segmentleri de sayar. Tavanı aşmış model sürdürmede hiç çağrılmaz (`at_resume: true`).
  - Alt tavanların toplamı 10,5 USD'dir (bilgi) [DRY].
- **Gerekçe** [EM3 Bölüm 2]: p95 değerleri eski tavanların üstündeydi. Koşunun dengesiz yarım kalmasını önlemek için tavanlar p95'i karşılayacak düzeye çıkarıldı. Beklenen harcama değişmez.
- **Beklenti kapısı 4,5 USD** [CFG satır 55]:
  - Gerçek koşudan ve `--resume`'dan önce kalibre dry-run'ın **ortalama** beklentisine bakılır. Beklenti 4,5 USD'yi aşarsa **koşu yapılmaz**.
  - p95 bilgi amaçlıdır [README "Expected-cost gate"; T68 K3c].
- **Kapı aşılırsa** [EM3 Bölüm 1; T73]:
  - Koşu yapılmaz, raporlanır. **Hiçbir kol çıkarılmaz.** Kod da kapı mesajında "kol çıkarılmaz, raporlanır" diyor; bunu bir test denetliyor [T73].
  - EMİR 2'deki Mistral abstract_v3 geri çekilmesi kaldırıldı. Gerekçe: yanlış kolu seçiyordu; veri görülmeden düzeltildi (§0.1 Ç3).
- **Süre aşımı muhasebesi** [EM2 K3; T68 K3b]:
  - Süre aşımında maliyeti bilinmeyen çağrı, bütçeye "istem + 16 000 çıktı token'ı" liste fiyatıyla eklenir; istem token'ı karakter / 3 ile tahmin edilir (tahmin).
  - Bu tahmin hem toplam tavana hem modelin alt tavanına sayılır.
  - Ham logda `pgg_deadline_cost_estimated` olayı, satırda `"cost_estimated": true` yazılır; özette `n_deadline_cost_estimated` ve tutar ayrı durur.
  - Terk edilen çağrının yanıtı sonradan gelirse tahmin geri alınır ve gerçek maliyet yazılır.
  - Mistral'da bu tahmin çağrı başına yaklaşık 0,034 USD [T68 risk 2].

### 8.2 Bu tasarım için beklenen maliyet

Son kalibre dry-run'ın çıktısı ve kapı kararı §15'tedir. Özet [T73; DRY]:

| model | kollar | ortalama (USD, tahmin) | p95 üst sınır (USD, tahmin) | alt tavan (USD) |
|---|---|---|---|---|
| deepseek | abstract_v3 + story | ~1,1309 | ~4,5092 | 5 |
| mistral | abstract_v3 | ~2,7601 | ~4,6881 | 5 |
| gpt | abstract_v3 + story | ~0,1530 | ~0,2376 | 0,5 |
| **toplam** | 5 kol, 3000 çağrı | **~4,0440** | **~9,4348** | tavan 10, kapı 4,5 |

- **Sağlama** (görev #74'te yapıldı):
  - Toplam ortalama: 0,5635 + 2,7601 + 0,0734 + 0,5674 + 0,0796 = 4,0440.
  - Toplam p95: 2,2519 + 4,6881 + 0,1145 + 2,2573 + 0,1231 = 9,4349 (dry-run 9,4348; yuvarlama).
  - DeepSeek: ortalama 0,5635 + 0,5674 = 1,1309; p95 2,2519 + 2,2573 = 4,5092.
  - GPT: ortalama 0,0734 + 0,0796 = 0,1530; p95 0,1145 + 0,1231 = 0,2376.
- **Tavan senaryosu** (her çağrı 16 000 çıktı token'ını doldurursa; beklenen değil): ~38,15 USD (tahmin) [DRY].

### 8.3 Mistral tahmininin dayanağı ve uçuştaki çağrılar

- **Kalibrasyon** [T71 §1; T73; REPO `configs/cost_calibration_minipilot_m1.json`]:
  - Mistral girdisi alt sınır değil. M1 ölçümünden kalibre edildi.
  - Ölçüm 12 adet 1. tur katkı çağrısı ve 6 izole (X = 10) çağrıdan geliyor; yalnız abstract_v3 çerçevesinde. Mini-pilotta Mistral aynı çerçevede koşar.
  - Maliyet completion token'larından hesaplandı, çünkü ücret onlar üzerinden kesiliyor ve M1'de 18 yanıtın 11'inde reasoning sayısı completion'dan büyük döndü [TO §1.2].
- **Varsayımlar (tahmin):**
  - **2.–10. turlar ve diğer X değerleri:** M1 değeri, pilot v2'deki DeepSeek ve GPT oranlarının büyüğüyle çarpıldı. Katkıda ortalama oranı 0,6134 ve p95 oranı 0,8300; izolede 1,0304 ve 1,2230 [T71]. #73'e göre bu varsayım değişmedi [T73].
  - **Kural anlama:** Mistral token'ları ölçülmedi; contribute_N ölçümünden oranla tahmin edildi [DRY].
  - **Ödenmiş-geçersiz payı:** pilot v2 havuzundan 0,181866.
- **Uçuştaki çağrılar tavanı aşabilir** [DOC "budget_usd"; T68 risk 3]. Bu, alt tavanlar için de geçerlidir.
  - En kötü durum: `parallel_units` 3 × `workers` 4 = 12 Mistral çağrısının hepsi 16 000 token doldurur.
  - Hesap: 12 × (1200 × 0,68e-6 + 16 000 × 2,09e-6) = 12 × 0,034256 ≈ **0,41 USD** aşım (tahmin; girdi 1200 token varsayıldı; fiyatlar 0,68 / 2,09 USD/1M [T71 §1]).

---

## 9. Durdurma ve tesisat kuralları (E4)

### 9.1 Pilot v2 kuralları, Görev A ekleri (A1–A5) ve EMİR 2 değişiklikleri

Kaynak: README; DOC; PR §8.2 + A2.3; #63 §8.1; T67; T68.

| # | kural | prereg'e etkisi |
|---|---|---|
| A1 | **Tur düzeyinde sürdürme.** Kabul edilip satıra dönüşmeyen yanıt `pgg_discarded` ve `"discarded": true` ile loglanır, `n_discarded` sayılır, maliyette kalır. Kilit dosyası (`<run>.lock`) ikinci süreci engeller; kesik son satır `<run>.partial.jsonl` dosyasına gider | PR N2'deki "yarım birim baştan koşulur" kuralının yerine geçer. Kural anlama sırasında kesilen birim baştan başlar (T68 K5) |
| A2 | **`reasoning_capped`:** reasoning_tokens ≥ 11 904 ise satır işaretlenir, **tutulur, atılmaz ve yeniden istenmez.** `n_reasoning_capped` olarak sayılır. **EMİR 3 3a:** Mistral'da ölçü max(reasoning_tokens, completion_tokens) ≥ 11 904 (§9.5) | `length` kuralını tetiklemez; E3 U3'e girer |
| A3 | `request_deadline_s` **900**, `stall_timeout_s` **1800** [CFG satır 33–34]. Satıra `elapsed_s`, `n_transport`, `n_deadline` yazılır. **EMİR 2 K3:** maliyeti bilinmeyen süre aşımı bütçeye max_tokens fiyatıyla eklenir (§8.1) | "stalled" durumunda `--resume` ile sürer. `n_deadline` model başına raporlanır (§11.1, §15.5) |
| A4 | **Sağlayıcı uyuşmazlığında yeniden iste ve say** (`provider_mismatch: true`, `n_provider_mismatch`; maliyet bütçeye girer; çağrı başına 4 deneme). `require_parameters: true`. **EMİR 2 K4:** sabitlenmiş modelde **sağlayıcı adı dönmeyen yanıt** da uyuşmazlık gibi yeniden istenir ve sayılır (`n_provider_mismatch` içinde, alt sayaç `n_provider_missing`) [T68 K4] | **PR §8.2 madde 5'i değiştirir: "dur" yerine "yeniden iste ve say".** Deneme sınırı tükenirse `provider_mismatch_limit` ile durur. PR A6 soru 8'deki "durma yok, `n_provider_unknown` say" kuralı artık yalnız sabitlenmemiş modellerde geçerli. Mini-pilotun üç modeli de sabitlenmiş |
| A5 | **`git_commit` zorunlu;** git dışı kopyada `CODE_VERSION.json` gerekir. **Kirli ya da bilinmeyen kodla gerçek koşu ve `--resume` başlamaz** | Yeni başlatma koşulu. `_kod_8616997/` kopyasından koşu başlamaz [DR uyarısı]. Kirli kod denetimi `frames/*.json`, `configs/*.json`, `cards/*.json` dosyalarını da kapsar (T67 K1) |

### 9.2 Başlamama koşulları (çağrı yapılmadan)

- `prereg_approved` true değil (E6) [CFG satır 3: şu an false; true yapılması ayrı developer görevi].
- Kalibre dry-run'ın ortalama beklentisi > 4,5 USD. Bu durumda koşu yapılmaz, raporlanır; kol çıkarılmaz (§8.1).
- Bir çerçevenin ya da `frame_files` girdisinin sha256'sı config'tekiyle tutmuyor (T67 K1).
- Kart dosyasının sha256'sı `cards_sha256` ile tutmuyor (EM3 3e; T73).
- Bir çerçeve dosyasında `kind` alanı yok (EM3 3d). Tek istisna dondurulmuş `abstract_v2`: yalnız `frames` alanı olmayan config'lerde varsayılan çerçeve olarak, sha256'sıyla tanınarak muaf; `frames` altında adıyla anılırsa koşu başlamaz [T73].
- `"kind": "abstract"` olmayan bir çerçevede, dosyada ya da render edilmiş istemde yasaklı kök var (T67 K1; EM3 3d).
- `runs_dir` geçersiz: mutlak değil, yok ya da worktree içinde.
- Kod kirli ya da sürümü bilinmiyor (A5).
  - #73'ün son dry-run'ı "kod kirli" uyarısı verdi, çünkü değişiklikler o an commit'lenmemişti; sonradan dala eklendi (3be3620) [T73; DRY].
  - Koşu görevi temiz kodla dry-run'ı tekrarlar ve kapıyı o çıktıyla yeniden denetler.
- `--resume`'da çerçeve sha256'sı ya da config farklı.

### 9.3 Durma koşulları

1. Birikmiş maliyet **10 USD**'ye ulaştı.
2. Bir modelin birikmiş maliyeti **alt tavanına** ulaştı: Mistral 5, DeepSeek 5, GPT 0,5 USD. Yalnız o model durur, `model_stops` yazılır.
3. Bir modelde `n_invalid` + `n_parse_fail` sınırı aştı (`invalid_rate_cap` 0,05; yalnız o model durur). Sağlayıcı hataları ve uyuşmazlıklar bu sayıma girmez [PR A2.3 madde 2].
   - %5 tavanı **yalnız karar çağrılarından** hesaplanır; kural anlama geçersizleri bu tavana sayılmaz, ayrı raporlanır (EM3 3c; §6.1) [T73].
   - Sınır: DeepSeek ve GPT 0,05 × 1080 = 54, Mistral 0,05 × 540 = 27 yanıt (karar çağrıları: kol başına 540) [T73].
4. İlk `finish_reason = length` (`stop_on_length`). `reasoning_capped` bu kural değildir.
5. İstekte `reasoning_effort` gönderildiği görülürse [PR §8.2 madde 4].
6. Sağlayıcı uyuşmazlığı (sağlayıcı adı dönmeyen yanıt dahil) deneme sınırını tüketti (A4).
7. `check_snapshot` farkı: Mistral'da `model_version_changed` (§3). Mistral'ın sürümü dönmezse durulmaz, `n_model_version_unknown` sayılır.
8. `RunAborted` ya da `stalled`. `stalled` durumunda `--resume` kullanılır.

Kural anlama çağrısında `max_invalid`'in tükenmesi bir durma koşulu değildir; satır `comp_missing` yazılır ve oyun sürer (§6.1).

### 9.4 Veri kalıcılığı (kullanıcı onaylı kural; koşu görevinin açıklamasına aynen yazılır)

- Gerçek API çağrısı yapan her koşu ham logu (`raw_calls.jsonl`), `results/*.jsonl` ve özet dosyalarını worktree **dışındaki** kalıcı `runs_dir/<run>/` dizinine yazar.
  - `runs_dir` = `/Users/karbon/Desktop/Veri Bilimi/complexity-prj/orc/data/projects/PublicGoods/workspace/runs` [CFG].
  - Dosyalar: `<run>.jsonl`, `<run>_summary.json`, `raw_calls.jsonl`, varsa `.seg<k>.json` ve `.partial.jsonl`.
- **Görev bitmeden** dosyaların bu dizinde var olduğu ve satır sayıları (`wc -l`) raporlanır; denetleyici kontrol eder.
- **Hesap kimliği içeren ham loglar commit'e girmez.**

### 9.5 EMİR 3 tesisat düzeltmeleri (3a, 3d, 3e) [EM3 Bölüm 3; T73]

- **3a Mistral token sayımı:**
  - M1'de 18 yanıtın 11'inde `reasoning_tokens` > `completion_tokens` döndü (§14.1).
  - Mistral için `reasoning_capped` = max(reasoning_tokens, completion_tokens) ≥ max_tokens − 4096 (= 11 904). Config'te `reasoning_cap_rule: {"mistral": "max_reasoning_completion"}` [CFG satır 60]. Diğer modellerde reasoning_tokens ≥ 11 904 kuralı aynen geçerli.
  - İki sayı (reasoning ve completion) satırda, özette ve ham logda ayrı yazılır; tesisat raporunda ayrı verilir (§11.1).
  - Maliyet completion üzerinden hesaplanır.
- **3d Çerçeve linter'ı varsayılan açık:**
  - `kind` alanı her çerçeve dosyasında zorunludur (istisna §9.2'de).
  - Linter her koşu başında her çerçevede çalışır. Yalnız dosyasında açıkça `"kind": "abstract"` yazan çerçeve muaftır.
  - Her çerçevenin denetim sonucu (geçti / muaf, nedeniyle) özete ve her segment kaydına (`frame_audit`) yazılır.
  - Son dry-run: abstract_v3 **MUAF** (dosyada `"kind": "abstract"`); story_A **GEÇTİ** (yasaklı kök yok) [DRY; T73].
- **3e Kart kilidi:**
  - Kart dosyası çerçeveler gibi config'te sha256 ile kilitlidir: `cards_sha256` = `a4f50d0f…a9aa` [CFG satır 6].
  - Tutmazsa gerçek koşu da dry-run da başlamaz. Son dry-run: "kilitli, beklenenle aynı" [DRY].
- **3f `_notes`:** config'teki `_notes` EMİR 3 tasarımına göre yeniden yazıldı; çelişen eski cümleler çıkarıldı (§10) [T73].
- **Mistral tarihli sürümü dönmeyen yanıt:** değişiklik yok. Yalnız sayılır (`n_model_version_unknown`), yeniden istenmez; tesisat raporunda verilir (§3, §11.1) [EM3 Bölüm 3].

---

## 10. Config alanları (`configs/minipilot.json`): son hal

Config'te `TBD_PREREG` kalmadı [T67]. Aşağıdaki değerler depodaki dosyadan okundu (CFG, #73 sonrası; görev #74'te okundu).

| alan | değer | satır | kaynak / karar |
|---|---|---|---|
| `prereg_approved` | **`false`** (ayrı developer göreviyle `true` yapılır) | 3 | E6; EM3 Bölüm 5 |
| `run` | `"minipilot_{run_date}"` | 4 | EM2 m.13 |
| `cards` | `"cards/pilot_cards_v3.json"` | 5 | E1; EM2 K1 |
| `cards_sha256` | `a4f50d0f…a9aa` | 6 | EM3 3e |
| `cities` | `["Boston", "Riyadh"]` | 7 | E1 |
| `models` | deepseek-v4.1-flash, mistral-large-4-0, gpt-6-luna | 8 | §3 |
| `conditions` / `arms` | `["N"]` / `["group", "isolated"]` | 9–10 | E1 |
| `groups_per_cell` / `isolated_reps` | `2` / `2` | 11–12 | E1 |
| `isolated_points` | `[0, 5, 10, 15, 20]` | 13 | E1 |
| `isolated_frame` / `isolated_round_no` | `"fixed_round"` / `5` | 14–15 | GC C1 |
| `frames` | abstract_v3: deepseek, mistral, gpt; story: deepseek, gpt | 16–19 | EM3 Bölüm 1 |
| `frame_files` | abstract_v3 `09b4d67b…3e5a`; story `frames/story_A.json` `d8face90…0d7d` | 20–29 | EM2 K1; EM3 3b (q2 değişince yeni özetler) |
| `comprehension` / `rationale` | `true` / `true` | 30–31 | GC C4; E2a |
| `max_tokens`, `request_deadline_s`, `stall_timeout_s` | 16000, 900, 1800 | 32–34 | PR; A3 |
| `providers` | §3 | 35–49 | PR A6 |
| `runs_dir` | `…/PublicGoods/workspace/runs` | 50 | §9.4 |
| `seed_namespace` | `"pgg-minipilot"` | 51 | EM2 m.13 |
| `max_invalid` | `3` | 52 | configs/pilot.json |
| `budget_usd` | `10` | 53 | EM3 Bölüm 2 |
| `model_budget_usd` | `{"mistral": 5, "deepseek": 5, "gpt": 0.5}` | 54 | EM3 Bölüm 2; K3 |
| `expected_cost_gate_usd` | `4.5` | 55 | EM2 m.4; EM3 Bölüm 2 (değişmedi) |
| `invalid_rate_cap` / `stop_on_length` | `0.05` / `true` | 56–57 | PR §12 karar 8; PR §8.2 madde 3 |
| `check_snapshot` / `snapshot_version_models` | `true` / `["mistral"]` | 58–59 | EM2 m.15 |
| `reasoning_cap_rule` | `{"mistral": "max_reasoning_completion"}` | 60 | EM3 3a |
| `workers` / `parallel_units` | `4` / `3` | 61–62 | EM2 m.14 |

- **`_notes` alanı (satır 2):** EMİR 3 tasarımına göre baştan yazıldı (3f) [T73]. Çerçeve ataması, çağrı sayıları (1200 / 1200 / 600; 3000), linter ve `kind`, q2 metni, `comp_missing`, kart kilidi, bütçe, "kapı aşılırsa kol çıkarılmaz, raporlanır" ve `reasoning_cap_rule` bu belgeyle tutarlı (görev #74'te okundu).

---

## 11. Analiz ve okuma planı (E5)

### 11.1 Tesisat raporu (yalnız sayılar, yorum yok)

Model × çerçeve başına; ayrıca **model başına** toplam:
- yanıt ve geçerli satır sayısı (karar ve `step = "comprehension"` ayrı);
- `n_invalid`, `n_parse_fail`, `n_provider_error`;
- kural anlama geçersizleri ayrı: `n_comp_invalid`, `n_comp_parse_fail`, `n_comp_missing` (EM3 3c);
- `n_provider_mismatch` ve alt sayacı `n_provider_missing`, `n_provider_unknown`;
- `n_length`, `n_reasoning_capped`, `n_discarded`, `n_transport`;
- Mistral'da `reasoning_capped`'i belirleyen iki sayı ayrı: reasoning token ve completion token (EM3 3a);
- **`n_deadline` model başına** ve `n_deadline_cost_estimated` (sayı ve tutar) [EM2 M2];
- reasoning token ortalaması, medyanı ve en yükseği; completion token ortalaması; reasoning metni boş satır sayısı;
- `elapsed_s` ortalaması, medyanı ve en yükseği;
- gerçek maliyet, dry-run ortalamasına ve p95'ine oranı, model alt tavanına oranı;
- `model_stops` kayıtları;
- `model_version` değerleri ve `n_model_version_unknown`;
- her çerçevenin linter denetim sonucu (`frame_audit`: geçti / muaf, nedeniyle) (EM3 3d);
- §9.4'teki dosyalar ve satır sayıları.

### 11.2 Betimsel tablolar

Analiz kural anlama satırlarını `step == "comprehension"` ile ayırır (§6.1).

Model × çerçeve × kart başına:
- kural anlama doğru oranı (q1, q2, ikisi birden);
- grup kolunda tur bazında hücre ortalaması ve g;
- izole çizelge;
- taban, tavan ve tek değer oranları (BET §4);
- 9 kart çiftinde D_iso, D_grup(1), D_grup(9), D_grup(10);
- **ayrı başlık (S7):** nötr prosedür kartı ile minimal kart arasındaki stil çifti farkı, her şehirde (§5.2 b1);
- E2a (i) ve (ii) oranları (R, Q, R ∪ Q). (i) "experiment" dahil ve hariç verilir; geniş sözlükler ikincil sayım olarak;
- E3 U1–U3 sayıları;
- §6.4 duyarlılık tablosu.

### 11.3 Muhakeme okuması (ayrı görev; CL "After a pilot run, read the reasoning texts for design flaws")

**Örneklem** (model × çerçeve başına; PR §9 düzeni):
- izole satırların tamamı (60);
- her grubun 1., 5. ve 10. turlarındaki dört ajanın metni (12 grup × 3 tur × 4 ajan = 144);
- **ek:** kural anlama yanıtlarının tamamı (60), yanlış cevap veren ajanların 1. tur metni ve E2a sözlüklerinin eşleştiği tüm yanıtlar (bağlam denetimi).

**Kontrol listesi:**
1. **PR §9 madde 1–10.**
   - Madde 8 (minimal karttaki dolgu cümlesi) uygulanamaz [MUH §2].
   - Madde 9, nötr prosedür kartındaki şehre özgü olgu yankısı olarak okunur: "census", "power of attorney", "notary".
2. **Tanıma maddesi** (PV E2, madde 11): metin deneyin ya da yayımlanmış bir çalışmanın tanındığını veya "beklenen cevabın" arandığını gösteriyor mu? E2a sayımına ek olarak örneklemde elle okunur.
3. **Kural anlama yanıtları:** yanlış cevapların türü (q1 hesap hatası, q2 işaret hatası) ve rationale'deki gerekçe.
4. **Kimlik anılma sayımı** (PV E7): rationale'lerde kimlik ve kart anılması model × stil başına **sayım** olarak verilir (oran değil; analize girmez).
   - **Kök listesi (EM2 m.18 ile onaylandı):** `boston`, `riyadh`, `saudi`, `liberty`, `authority`, `elder`, `tribal`, `census`, `attorney`, `notary`, `student`, `grew up`, `cultur`, `background`, `american`, `arab`, `western`, `individualis`, `collectivis`, `stereotyp`.
   - EMİR 2'nin eklediği yedi kökten `saudi` listede zaten vardı; tekrar yazılmadı.
   - Not (tahmin): alt dizgi kuralıyla `arab`, "comparable" gibi sözcüklerde de eşleşir. Bu tür yanlış pozitifler §5.0'daki elle denetim kuralıyla, listelenerek çıkarılır.
   - Olgusal kartın "irrelevant" ya da "ilgisiz" diye anılması ayrı sayılır.
5. **Çerçeveye özgü maddeler:**
   - kurgunun gerçek sanılması ya da sorgulanması (uygulama, kredi, kavanoz);
   - çarpanın faiz veya getiri sanılması;
   - kart ile kurgu arasında modelin dile getirdiği çelişki;
   - paradigmanın yapıdan tanınması ("essentially a public goods game");
   - "tip jar" ya da oyunlaştırma çağrışımı (#62 riski, Ek A).

**Çıktı:** bulgular ve değişiklikler gerekçeleriyle bu dosyaya **tarihli ek** olarak yazılır. Metinlerden nedensel sonuç çıkarılmaz [PR §9; MUH §5.1]. Rapora giren her sayı sonuç dosyalarından yeniden doğrulanır [CL].

---

## 12. Pilot v2'den taşınan karar maddeleri (S1–S14, E1–E8): güncel durum

| madde | durum |
|---|---|
| S1 sonraki adım | Mini-pilot yolu GC, GE ve EMİR 2 ile açıldı. Tam deney kararı **açık** |
| S2–S3 izole yöntem ve tur bilgisi | **Karara bağlandı:** 5 nokta (GE E1), `fixed_round` (GC C1) |
| S4–S5 `reasoning_effort` ve `max_tokens` | Mini-pilotta gönderilmez, 16000 [CFG]. Ana deney için **açık** |
| S6–S8 ana deney bütçesi, alt tavan, kalibrasyon | Mini-pilot için **karara bağlandı** (EM2 m.4; EM3 Bölüm 2; M1 kalibrasyonu). Ana deney bütçesi **açık**; mini-pilot tavanı (10 USD) ana deney tavanı değildir |
| S10 #49 eşikleri | Mini-pilotta Ç6 (max(e, g)) ile; ana deney için **açık** |
| S11–S14 | **Açık.** Mini-pilotta P koşulu ve karma grup yok |
| PV E1 değer kartı çağrışım denetimi | **Açık;** E2b dolaylı ölçüyor |
| PV E2 tanıma maddesi | **Karara bağlandı** (E2a, E5; EM2 m.7–10) |
| PV E3 taban/sabit eşiği | **E ile kısmen:** E3 U1'de %80 (pilot v2 önerisi %50 idi) |
| PV E4 (a)(b) | (b) karara bağlandı; (a) 21 nokta GE E1 ile mini-pilotta yok |
| PV E5 (a) kural anlama | Karara bağlandı (GC C4; EM2 K2). (b) ve (c) mini-pilotta uygulanmaz |
| PV E6 D_grup(9) | **Karara bağlandı** (E2c) |
| PV E7 kimlik anılma | **Karara bağlandı** (E5; kök listesi EM2 m.18) |
| PV E8 (c) GPT reasoning özeti | E2a'da uygulanıyor (Ç2) |

**#61 ve #62'nin açık tesisat maddeleri (EM2 m.17: olduğu gibi):**
- sistem mesajı yalnız kart;
- izolede kural anlama çizelge başına bir kez;
- grup kolunda kural anlama satırları 1. tura bağlı;
- q2'nin "10 more" biçimi;
- şemadaki rationale açıklaması karar şemasıyla aynı.

T68'e göre beşi de iki çerçevede zaten uygulanmıştı; bunları sabitleyen bir test eklendi, kod değişikliği gerekmedi [T68 madde 17].

#62'nin şu açık maddeleri T68'in kapsamı dışında kaldı ve uygulanmadı: kart linter'ına "game" kökü eklenmesi, istem uzunluğunun ortak değişken olarak analizi [T68]. Bunlar mini-pilotu bekletmez (EM2 m.19).

---

## 13. Karar tablosu (EMİR 2 Bölüm 1, madde 1–19)

Bu tablo, önceki taslağın kapalı uçlu onay sorularının yerini alır. Madde numaraları önceki §13 soru numaralarıyla aynıdır. EMİR 3 ile değişen satırlarda (m.2, m.3, m.4, m.11) güncel karar yazıldı; EMİR 2'deki ilk hal değişiklik günlüğündedir.

| m. | konu | karar (EM2; EM3 ile güncel) | uygulanışı / not | etkilenen bölüm |
|---|---|---|---|---|
| 1 | Ç1 çerçeve | Taslak A (kavanoz). Balıkçı hikâyesi yok; C2 yasağı geçerli | `frames/story_A.json`, sha256 `d8face90…0d7d` kilitli; yasaklı kök denetimi koşu başında (T67, T73) | §0.1 Ç1, §4.1, §10 |
| 2 | Ç2 hikâye kolu | EM3 Bölüm 1: DeepSeek ve GPT. GPT'de E2a yalnız rationale | `frames.story` = deepseek, gpt | §0.1 Ç2, §2.2, §5.0 |
| 3 | Ç3 abstract_v3 kolu | EM3 Bölüm 1: üç modelde (deepseek, mistral, gpt); çerçeve karşılaştırması yalnız DeepSeek ve GPT içinde (sınırlılık) | Son tasarım 5 kol, 3000 çağrı (T73) | §0.1 Ç3, §2.2, §2.4, §5.1, §7 |
| 4 | Ç4 bütçe | EM3 Bölüm 2: tavan 10 USD, kapı 4,5 USD (ortalama); alt tavanlar Mistral 5 / DeepSeek 5 / GPT 0,5. Kapı aşılırsa koşulmaz, raporlanır | Config ve kod (T67, T68, T73); son dry-run kapıyı geçiyor | §0.1 Ç4, §8, §9.3, §15 |
| 5 | Ç5 kartlar | v3 olgusal kartlar olduğu gibi; stil adı "nötr prosedür kartı"; rolü içeriksiz kontrol; E2b(b1) yeniden yazılır. S7 = Evet; S2, S5 mevcut metin | Kart dosyası değişmedi (sha256 `a4f50d0f…a9aa`); EM3 3e ile `cards_sha256` kilidi | §0.1 Ç5, §2.1, §5.2, §11.2 |
| 6 | Ç6 fark tanımı | (b) max(e, g) | E3 U1'de | §0.1 Ç6, §7 |
| 7 | Ç7 karşılaştırma ölçütü | (a) Pilot v2 aynı kural ve aynı kodla yeniden sayılır. Ön sayım (i) 528/540, (ii) 387/540; 103/374 kullanılmaz; eşikler ≤ 176 / ≤ 129 | Analiz görevi yeniden üretir; tutmazsa raporlar | §0.1 Ç7, §5.1 |
| 8 | Ç8 "experiment" | (c) Dahil ve hariç iki biçim; etiket HARİÇ hal üzerinden | — | §0.1 Ç8, §5.1, §11.2 |
| 9 | 1/3 eşiği | Evet, iki sayımda da; (ii) için beklenti "azalmaz" | — | §5.1 |
| 10 | Sözlük varyantları; geniş sözlükler | Evet; geniş sözlükler ikincil sayım | — | §5.1 |
| 11 | E3 tanımları | U2 birimi "q1 ya da q2 yanlış"; U3 paydası karar + kural anlama; uygunlukta esas kol abstract_v3 | Mistral'ın E3 uygunluğu abstract_v3 kolundan (EM3 Bölüm 1; §17 (b)); Mistral'da U3 ölçüsü EM3 3a | §7 |
| 12 | Kural anlama yanlışlarında dışlama | Satır dışlama yok, yalnız duyarlılık | — | §6.4 |
| 13 | Run adı ve seed | `minipilot_<YYYYMMDD>`, `pgg-minipilot` | Config'te şablon `minipilot_{run_date}` | §2.3, §10 |
| 14 | `parallel_units` | 3 | En kötü uçuş aşımı ~0,41 USD (tahmin) | §8.3, §10 |
| 15 | `check_snapshot` | true; Mistral'ın tarihli sürümü (`openrouter_metadata`) her satıra loglanır | `snapshot_version_models: ["mistral"]`, `model_version` alanı (T68) | §3, §9.3, §11.1 |
| 16 | Mistral ön ölçümü | Evet (M1) | Yapıldı: `tesisat_olcum_20261007`, 0,103482 USD (T70) | §14, §15 |
| 17 | #61 ve #62 açık tesisat maddeleri | Evet, olduğu gibi | Kod değişikliği gerekmedi; testle sabitlendi (T68) | §12 |
| 18 | Kimlik kök listesi | Evet; eklenenler: saudi, american, arab, western, individualis, collectivis, stereotyp | `saudi` zaten vardı | §11.3 |
| 19 | Açık S/E maddeleri | Mini-pilotu bekletmez | — | §12, §16 |

### 13.1 Kod değişiklikleri (EMİR 2 Bölüm 2; T67 ve T68 sonuçlarındaki ifadelerle)

| # | değişiklik | kaynak | bölüm |
|---|---|---|---|
| K1 | **Çerçeve ve kart kilidi.** `frame_files` her iki çerçeve dosyasını yol ve sha256 ile kilitliyor. "Özet uyuşmazlığı: Hem gerçek koşu hem dry-run hiç çağrı yapmadan hata verip duruyor." Kart dosyası `cards/pilot_cards_v3.json` (`a4f50d0f…a9aa`) depoda | T67 K1 | §4, §9.2 |
| K1 | **Koşu başı linter.** `story` türündeki çerçevede "yasaklı kök denetimi … hem dosyadaki metinleri hem modele gidecek son istemleri tarıyor. Kök bulunursa koşu da dry-run da başlamıyor." Kirli kod denetimi `frames/*.json`, `configs/*.json` ve `cards/*.json` dosyalarını da kapsıyor. EMİR 3 3d ile linter varsayılan açık (§13.2) | T67 K1 | §4.1, §9.1–9.2 |
| K2 | **q2 metni** EMİR 2 K2 ile değişti; EMİR 3 3b ile yeniden değişti. Güncel metin §6.2'de. 28 / −6 anahtarı aynen | T67 K2; T73 3b | §6.2 |
| K2 | **Kural anlama satırları** "sonuç dosyasında `step = "comprehension"` ile ayrılıyor"; analiz bu adıma göre süzer | T67 K2; EM2 K2 | §5.0, §6.1, §11.2 |
| K3a | **Model alt tavanları:** "Bir modelin birikmiş maliyeti tavanına ulaşınca yalnız o model duruyor, öbürleri devam ediyor." | T68 K3a | §8.1, §9.3 |
| K3b | **Süre aşımı muhasebesi:** maliyeti bilinmeyen çağrı "Bütçeye 'istem + 16000 çıktı token'ı' liste fiyatıyla ekleniyor. Bu tahmin hem toplam tavana hem modelin alt tavanına sayılıyor." | T68 K3b | §8.1, §9.1 A3 |
| K3c | **Dry-run'da p95:** model başına ortalama ve p95 birlikte yazılıyor; kapı kararı ortalamaya göre | T68 K3c | §8.1, §15 |
| K4 | **Sağlayıcı adı dönmeyen yanıt:** "Sağlayıcısı sabitlenmiş bir modelde ad dönmezse yanıt artık karar sayılmıyor. Uyuşmazlık gibi yeniden isteniyor, maliyeti bütçeye giriyor, 4 deneme sınırı aynen geçerli." | T68 K4 | §9.1 A4 |
| A4 | **PR §8.2 madde 5'in değişikliği:** sağlayıcı uyuşmazlığında "dur" yerine **"yeniden iste ve say"**; K4 bunu sağlayıcı adı dönmeyen yanıtlara genişletti | #63 §8.1; T68 K4 | §9.1 |
| m.15 | **Mistral tarihli sürümü:** her satıra `model_version`; `check_snapshot` Mistral'da bu alanı karşılaştırıyor | T68 madde 15 | §3, §9.3 |
| K5 | **Sürdürmede istem eşitliği** testleri abstract_v3 ve story_A için, kural anlama açıkken | T68 K5 | §6.1 |
| M2a | **Mistral kalibrasyonu:** `configs/cost_calibration_minipilot_m1.json` (M1 ölçümü), pilot v2 dosyasının Mistral girdisinin üzerine yazılıyor | T71 §1 | §8.3, §15 |

### 13.2 Kod değişiklikleri (EMİR 3 Bölüm 1–3; T73)

| # | değişiklik | bölüm |
|---|---|---|
| Bölüm 1–2 | `configs/minipilot.json`: yeni çerçeve ataması; `budget_usd` 10; alt tavanlar mistral 5, deepseek 5, gpt 0,5. Kapı mesajı "kol çıkarılmaz, raporlanır"; kodda kol çıkarma mantığı kalmadı, bir test denetliyor | §2.2, §8, §10 |
| 3a | Mistral'da `reasoning_capped` = max(reasoning, completion) ≥ max_tokens − 4096 (`reasoning_cap_rule`); iki sayı ayrı yazılıyor; maliyet completion üzerinden | §7 U3, §9.5 |
| 3b | q2 iki çerçevede "Give the change as a whole number (it can be positive, zero or negative)."; "+3 / -3" örneği kalktı; anahtar 28 / −6; normalleştirme ve degraded logu duruyor | §6.2 |
| 3c | Kural anlama çağrısı koşuyu durdurmuyor: `comp_missing: true`, `pgg_comprehension_missing`; `n_comp_invalid`, `n_comp_parse_fail`, `n_comp_missing`; %5 tavanı yalnız karar çağrılarından (deepseek 54, mistral 27, gpt 54) | §6.1, §9.3 |
| 3d | `kind` zorunlu; linter her çerçevede, yalnız `"kind": "abstract"` muaf; sonuç özete ve `frame_audit`'e; `frames/SCHEMA.md` güncellendi | §4, §9.2, §9.5 |
| 3e | `cards_sha256` tutmazsa gerçek koşu da dry-run da başlamıyor | §2.1, §9.2, §9.5 |
| 3f | `_notes` baştan yazıldı | §10 |

- **Testler:** #73 sonrası **379 testin hepsi geçti** (16'sı yeni) [T73].
- **Kalibrasyon denetimi:** `pgg_cost_calibrate.py`'deki "çerçeve sha256'sı M1'dekiyle aynı olmalı" denetimi kaldırıldı (q2 değişince tutmuyor). Yerine: M1'in bütün istemleri bugünkü dosyayla yeniden üretiliyor ve logdakilerle birebir aynı çıkmak zorunda [T73].
- **Dal ve commit'ler:** değişiklikler `orc/PublicGoods` dalında: 855d78d (#67), 0b8e60b (#68), 533aca8 (#71), 3be3620 (#73).

---

## 14. Tesisat ölçümü (M1)

> **Bu veri hiçbir analize girmez.** Yalnız tesisat ölçümüdür ve maliyet kalibrasyonunda kullanıldı (§15). Katkı değerleri yorumlanmadı [EM2 M1; TO].

- **Koşu:** `tesisat_olcum_20261007`, 2026-10-07; seed namespace `pgg-tesisat-olcum` [TO].
- **Kod:** `orc/PublicGoods` ucu `0b8e60b` (#68). Mini-pilot koşu yolu kullanılmadı.
  - İstemler mini-pilotla aynı render yoluyla üretildi; çağrılar `llm_client.call_llm_valid` ile gitti.
  - Ayarlar `configs/minipilot.json`'dan alındı; `require_parameters` dahil [TO §0].
- **Sonuç:** **20/20** çağrı başarılı (Mistral 18, DeepSeek 1, GPT 1). Yeniden istem 0.
- **Toplam maliyet:** **0,103482 USD**; sert tavan 0,50 USD. Dağılım: Mistral 0,103434, DeepSeek 0,0000276, GPT 0,0000201 [TO Özet].

### 14.1 Mistral (abstract_v3; Boston ve Riyadh'ın 6 v3 kartı; kart başına 2 adet 1. tur katkı + 1 izole X = 10)

| ölçü | n | ortalama | medyan | en düşük | en yüksek |
|---|---|---|---|---|---|
| reasoning token | 18 | 2 659,8 | 2 664 | 1 541 | **3 895** |
| completion (çıktı) token | 18 | 2 624,6 | 2 511,5 | 1 521 | 4 113 |
| istem token | 18 | 383,7 | 383 | 366 | 394 |
| maliyet (USD, çağrı başına) | 18 | 0,005746 | 0,005517 | 0,003445 | 0,008855 |
| `elapsed_s` | 18 | 64,1 | 48,1 | 23,1 | **173,8** |

[TO §1.1]

- **Çağrı türüne göre reasoning:** katkıda ortalama 2 576,6, medyan 2 664, en yüksek 3 286; izolede ortalama 2 826,2, medyan 2 830, en yüksek 3 895.
- **Maliyet:** Mistral toplamı 0,103434 USD; katkı 0,066138, izole 0,037296. Sağlama: 18 × 0,005746 ≈ 0,1034.
- **Her çağrının `elapsed_s` değeri** (TO §1.2 sırasıyla, sn): 39,254; 35,944; 25,363; 44,364; 38,540; 51,902; 76,940; 23,106; 77,913; 74,918; 143,249; 60,109; 66,359; **173,757**; 38,384; 100,959; 40,702; 41,296.
- **900 sn sınırı:** en uzun çağrı 173,757 sn (riyadh_value, katkı, Player 2), yani `request_deadline_s` 900'ün yaklaşık %19'u. 600 sn'ye yaklaşan çağrı yok.
- **Reasoning metni:** **18/18 çağrıda döndü** (6 049–15 260 karakter). `finish_reason` 18/18 `stop`.
- **Sayaçlar:**
  - `n_invalid`, `parse_fail`, `reasoning_capped`, `n_transport` ve `n_deadline` 0.
  - Sağlayıcı uyuşmazlığı ve sağlayıcı adı dönmeyen yanıt da 0.
- **Sağlayıcı ve sürüm:** 18/18'de sağlayıcı `Mistral`, `model_version` `mistralai/mistral-large-4-0-20261006`.
- **Kalibrasyon için gözlem:** 18 yanıtın 11'inde `reasoning_tokens` > `completion_tokens`. Ücret completion üzerinden kesiliyor; bu yüzden kalibrasyon completion token'larıyla yapıldı [TO §1.2; T71 §1].

### 14.2 DeepSeek ve GPT ("Reply with ok"; oyun istemi değil)

| | DeepSeek | GPT |
|---|---|---|
| `require_parameters: true` ile kabul | Evet, ilk denemede | Evet, ilk denemede |
| sağlayıcı (yanıttaki) | DeepInfra | OpenAI |
| `model_version` | `deepseek/deepseek-v4.1-flash-20260910` | `openai/gpt-6-luna-20260922` |
| istem / çıktı / reasoning token | 86 / 37 / 29 | 66 / 27 / 13 |
| reasoning metni döndü mü | evet | hayır |
| maliyet (USD) | 0,00002758 | 0,00002010 |
| `elapsed_s` | 1,036 | 1,953 |

[TO §2] DeepSeek yanıtında fp8 alanı dönmüyor (§3).

### 14.3 Kalıcı dosyalar

`runs/tesisat_olcum_20261007/`; satır sayıları `wc -l` ile, T70'te [TO §3]:

| dosya | satır |
|---|---|
| `raw_calls.jsonl` | 22 |
| `results.jsonl` | 20 |
| `summary.json` | 82 |
| `olcum_ozet.json` | 261 |
| `console.out` | 21 |

Ham log hesap kimliği içerebilir; commit'e girmez.

---

## 15. Kalibre dry-run ve kapı kararı (son config; görev #73)

Dry-run API çağrısı yapmadan, `configs/cost_calibration_pilot_v2.json` + `configs/cost_calibration_minipilot_m1.json` kalibrasyonuyla, EMİR 3'ün son config'iyle yapıldı [T73; DRY]. Bütün sayılar **(tahmin)**. Önceki dry-run'ların (#71) sonuçları değişiklik günlüğündedir.

### 15.1 Model × kol

| çerçeve | model | çağrı | ortalama (USD) | p95 üst sınır (USD) |
|---|---|---|---|---|
| abstract_v3 | deepseek | 600 | 0,5635 | 2,2519 |
| abstract_v3 | mistral | 600 | 2,7601 | 4,6881 |
| abstract_v3 | gpt | 600 | 0,0734 | 0,1145 |
| story | deepseek | 600 | 0,5674 | 2,2573 |
| story | gpt | 600 | 0,0796 | 0,1231 |
| **toplam** | | **3000** | **~4,0440** | **~9,4348** |

- **Sağlama:** satırların toplamı ortalamada 4,0440, p95'te 9,4349 (dry-run 9,4348; yuvarlama) (§8.2).

### 15.2 Model başına, alt tavanla kıyas

| model | çağrı | ortalama | p95 | alt tavan | durum [DRY] |
|---|---|---|---|---|---|
| DeepSeek | 1200 | 1,1309 | 4,5092 | 5 | ortalama altında, p95 altında |
| Mistral | 600 | 2,7601 | 4,6881 | 5 | ortalama altında, p95 altında |
| GPT | 1200 | 0,1530 | 0,2376 | 0,5 | ortalama altında, p95 altında |

- Toplam p95 (~9,4348) 10 USD sert tavanın altında.
- Alt tavanların toplamı 10,5 USD (bilgi) [DRY].

### 15.3 Kapı kararı

- **Ortalama beklenti ~4,0440 USD < 4,5 USD:** "Beklenti kapısı expected_cost_gate_usd=4.5 USD: GEÇER (beklenti kapının altında)" [DRY].
- **Kural:** kapı aşılsaydı koşu yapılmaz, raporlanırdı; hiçbir kol çıkarılmazdı (§8.1) [EM3 Bölüm 1].
- **Çerçeve ve kart kilitleri** [DRY]:
  - abstract_v3 `09b4d67b…3e5a`: "kilitli, beklenenle aynı"; linter MUAF.
  - story_A `d8face90…0d7d`: "kilitli, beklenenle aynı"; linter GEÇTİ.
  - kartlar `a4f50d0f…a9aa`: "kilitli, beklenenle aynı".
- **Config sha256:** `34814a74b548f35d4ad97039d56120003c1cdc2404664bfd20d39e8c33ae7421` [T73].
- **Uyarı:** dry-run, değişiklikler commit edilmeden önce alındığı için "kod kirli" uyarısı verdi; değişiklikler sonra dala eklendi (3be3620). Koşu görevi temiz kodla dry-run'ı tekrarlar ve kapıyı o çıktıyla yeniden denetler (§9.2) [T73; DRY].

### 15.4 2.–10. tur varsayımı ve sınırlılıklar

1. **2.–10. tur varsayımı (değişmedi)** [T73; DRY]:
   - 1. tur ve X = 10 değerleri M1 ölçümünden geliyor (12 katkı ve 6 izole çağrı).
   - Sonraki turlar ve diğer X değerleri pilot v2'deki en büyük oranla hesaplanıyor (tahmin) (§8.3).
   - Kural anlama çağrıları contribute_N ölçümünden oranlanıyor (tahmin).
   - Kullanıcı bu varsayımı onayladı (§17 (c)). Tavanlar p95'i karşıladığı için varsayım tutmazsa koşunun tavanda yarım kalma riski azaldı [EM3 Bölüm 5]. Ortalama beklentinin kapıya mesafesi ~0,46 USD (4,5 − 4,0440).
   - Bu tasarım için alternatif varsayımla ("her tur 1. tur kadar düşünür") bir hesap #73'te yapılmadı.
2. **Mistral alt tavanı ve uçuş aşımı:** Mistral'ın p95'i (~4,6881) ile 5 USD alt tavanı arasında ~0,31 USD var. En kötü uçuş aşımı (~0,41 USD, tahmin; §8.3) bu farktan büyük (tahmin).
3. **Az veri:** Mistral kalibrasyonu 18 çağrıdan ve tek çerçeveden (abstract_v3) geliyor. Kural anlama token'ları oranla tahmin edildi. p95 değerleri pratikte en büyük gözleme yakın [T71 "Bilinen eksikler"].
4. **Ödenmiş-geçersiz payı:** pilot v2 havuzundan alındı (0,181866). O havuz yeniden başlatılan birimleri de içeriyordu [T71].
5. **İstem ölçeği:** kalibrasyon abstract_v2 istemleriyle ölçüldü; başka çerçevede istem token'ı karakter oranıyla ölçeklendi (tahmin) [DRY].

### 15.5 Süre aşımı (n_deadline)

- **`n_deadline` model başına raporlanır** (§11.1).
- **M1'deki durum:** Mistral'ın en uzun çağrısı 173,757 sn, yani 900 sn sınırının ~%19'u. M1 yalnız 1. turu ölçtü; sonraki turların süresi ölçülmedi [T71 §6; TO §1.1].
- **Sınırlılık:** süre aşımına uğrayıp yeniden istenen yanıtlar, en uzun akıl yürüten yanıtları sistematik olarak eleyebilir.
  - Kabul edilen satırlar bu yüzden daha kısa düşünülmüş yanıtlara kayabilir.
  - Bu, E2a sayımlarını (uzun reasoning daha fazla eşleşme fırsatı verir) ve U3'ü etkileyebilir (tahmin).
  - `n_deadline` ve `n_deadline_cost_estimated` bu nedenle model başına raporlanır ve okumada dikkate alınır.

---

## 16. Bekleyenler: ana deneyden önce (mini-pilotu etkilemez; şimdi işlem yok)

1. **Hikâye A'nın ceza adımı:** "başkasının bakiyesini azaltma" ("reductions") adımı inandırıcı değil. **P koşulu koşulmadan önce yeniden yazılacak** [EM2 Bölüm 4 NOT; EM3 Bölüm 6]. Mini-pilot yalnız N koşulunu koşar; bu adım istemlere girmez.
2. **D2: kurallarin uygulanmasını anlatan kurum olgusu kartı** (#69; ana deney için açık iş) [D2; T69]:
   - **Kaynak:** dört ülkeyi aynı yıl ve aynı yöntemle kapsayan tek uygun kaynak World Bank **Doing Business 2020, Enforcing Contracts, "Time (days)"**.
   - **Değerler:** ABD (NYC + LA) 444, Danimarka 485, Yunanistan 1 711, Suudi Arabistan (Riyadh) 575 gün.
   - **Suudi Arabistan usulsüzlük kontrolü:** DB2020 Suudi verisi incelemeye konu oldu. Dünya Bankası'nın Aralık 2020 incelemesine göre etkilenen göstergeler Getting Credit ve Paying Taxes; Enforcing Contracts'ın etkilendiğine dair kaynak bulunamadı.
     - Bu hüküm yalnız arama özeti düzeyinde. İnceleme PDF'i açılamadı, **birincil kaynaktan doğrulanamadı** [D2 §3].
   - **Açık sorular:** #69'un S1–S8'i **ana deney prereg'inde karara bağlanacak** [EM3 Bölüm 6]. Bunlardan S8, kartın nötr prosedür kartının yerine mi geçeceğini, ayrı bir stil mi olacağını soruyor.
   - Prereg'e yazılması önerilen sınırlılık: DB serisi veri usulsüzlükleri nedeniyle durduruldu [D2 §5].
3. **Diğer ertelenenler:**
   - Athens ve Copenhagen kartları (KV3 S3, S4);
   - [W] alıntılarının birincil doğrulaması (S6);
   - ana deney bütçesi, `reasoning_effort` ve `max_tokens` (§12).

---

## 17. Kullanıcı onayı (2026-10-07)

**Kullanıcı bu ön kaydı (prereg_minipilot.md) EMİR 3'teki değişikliklerle birlikte ONAYLADI** [EM3 Bölüm 5].

- **Onayın dayanağı:** #73'e göre testler geçti (379/379) ve son dry-run kapısı geçti (~4,0440 < 4,5 USD) [T73; DRY].
- **Uygulama:**
  - Başlık "ONAYLANDI — 2026-10-07 (kullanıcı)" oldu.
  - `configs/minipilot.json`'da `prereg_approved` = true **ayrı bir developer göreviyle** yapılır; o zamana kadar config'te false kalır [CFG satır 3].
  - **Koşu henüz başlamaz.** Mini-pilot ancak kullanıcı "BAŞLA" dedikten sonra, ayrı bir görevle koşulur. O görevde temiz kodla dry-run tekrarlanır, kapı yeniden denetlenir ve §9.4 veri kalıcılığı kuralı aynen uygulanır.
- **Üç uygulama kararı:**
  - **(a) q2: DEĞİŞTİ.** EMİR 3 3b'deki yeni metinle onaylandı: "Give the change as a whole number (it can be positive, zero or negative)." (§6.2).
  - **(b) Mistral'ın E3 uygunluğu: DEĞİŞTİ.** abstract_v3 kolundan raporlanır (EMİR 3 Bölüm 1; §7).
  - **(c) 2.–10. tur varsayımı: onaylandı.** Tavanlar p95'i karşıladığı için kapı kararı bu varsayıma artık daha az bağlı (§15.4).

---

## Ek A. #62 taslakları (Ç1 (b) için referans; değiştirilmeden #63'ten)

| | Taslak A (`frames_story_A.json`, `story_A_jar`) | Taslak B (`frames_story_B.json`, `story_B_basket`) |
|---|---|---|
| Kurgu | Uygulama her gün 20 kredi veriyor; kavanoz 1,6 katına çıkıyor ve dörde eşit bölünüyor | Mağaza her hafta 20 kupon veriyor; sepet 1,6 katına tamamlanıyor ve dörde eşit bölünüyor |
| Uzunluk (abstract_v3'e oran) | ×1,20 | ×1,31 |
| sha256 (#62 doğrulayıcısı) | `9fec03ee2c00df783be36955a2ca796768bc6b86d904ca72cdb065766e917db9` | `57f2ecfd199ffa9f3f3bfd4424258f9938a0e5b795690aa5579a32df51001118` |
| #62 riski | "tip jar" ve oyunlaştırma çağrışımı | ticari kurgu ve kampanya şüphesi |

Kaynak: HT §1.3, §5, §6, §8. Kural anlama metinleri: A "CHECK OF THE JAR'S RULES …", B "CHECK OF THE OFFER'S RULES …". Tam metinler HT §1.3'te.

---

## Kaynaklar ve doğrulama notları

- **Okunanlar (görev #74):**
  - Workspace: önceki `prereg_minipilot.md` (#72), `gorev73_dryrun.txt`. EMİR 3 metni ve görev #73'ün sonuç metni.
  - Depo (salt okunur, #73 sonrası): `configs/minipilot.json` (tamamı), `frames/abstract_v3.json` ve `frames/story_A.json` (`kind` ve kural anlama satırları 52–62), `frames/SCHEMA.md` (`kind` satırları).
- **Önceki sürümün okudukları (#72):**
  - Workspace: önceki `prereg_minipilot.md` (#66), `gorev_tesisat_olcum.md` (#70), `gorev_d2_kurum_uygulama.md` (#69). Görev #67, #68, #69, #70 ve #71'in sonuç metinleri.
  - Depo (salt okunur): `configs/minipilot.json`, `frames/story_A.json`, `frames/abstract_v3.json` (kural anlama bölümü), `cerceve_linter.py` (ROOTS), `configs/cost_calibration_minipilot_m1.json` (başlık alanları).
- **Önceki sürümün okudukları (#66):**
  - Workspace: `kart_tasarimi_v3.md`, `pilot_cards_v3.json`, `gorev_kurum_olgulari.md`, `pilot_v2_degerlendirme.md`, `pilot_v2_muhakeme_okuma.md`, `pilot_v2_betimsel.md`, `prereg_pilot.md`, `gorev_mistral_tesisat.md`, `dryrun_c2/dryrun_A_Sa.txt`, `gorev11_herrmann_degerler.md`.
  - Depo: `frames/abstract_v2.json`, `frames/SCHEMA.md`, `pgg_game.py` (satır 1170–1340).
- **Görev #74'te bağımsız sağlananlar:**
  - §2.4 çağrı sayıları (DRY ile aynı).
  - §8.2 ve §15 toplamları (DRY satırlarından).
  - §9.3'teki %5 sınırları (1080 × 0,05 = 54; 540 × 0,05 = 27).
  - §15.4'teki kapı mesafesi (0,46) ve Mistral p95–alt tavan farkı (0,31).
  - Depodaki config'teki frame sha256'larının ve `cards_sha256`'nın DRY ve T73 ile aynı olduğu.
- **Önceki görevlerde sağlananlar (#72):** §5.1 eşikleri (528/3, 387/3) ve oranlar; §8.3 uçuş aşımı; M1 maliyet çarpımı.
- **Doğrulanamayanlar:**
  - Üst yöneticinin 528/540 ve 387/540 ön sayımı; analiz görevi yeniden üretecek.
  - İlk çalışmanın 1/3 ölçütünün orijinal tanımı.
  - D2'deki Suudi usulsüzlük kapsamı (yalnız arama özeti düzeyinde).
  - Ek A'daki #62 sha256'ları; depodaki kilitli story_A özeti bunlardan farklı (§4.1).
  - Config sha256'sı (`34814a74…7421`) ve eski sha256'lar yalnız T73'ten; bu görevde hesaplanmadı (kod çalıştırılmadı).

---

## Değişiklik günlüğü (2026-10-07, EMİR 3, görev #74)

Hedefli düzenleme. Araç dosyayı bütün olarak yazdığı için metin yeniden yazıldı; aşağıda listelenmeyen bölümler önceki sürümden değiştirilmeden taşındı.

| tarih | değişiklik | bölüm |
|---|---|---|
| 2026-10-07 (EMİR 3) | Başlık "TASLAK — KULLANICI ONAYI BEKLİYOR" → "ONAYLANDI — 2026-10-07 (kullanıcı)". Altına `prereg_approved=true` ve "BAŞLA" notu eklendi. Belge adı "EMİR 2 sonrası son taslak" → "EMİR 3 sonrası onaylı sürüm" | başlık |
| 2026-10-07 (EMİR 3) | Durum, "bu görevde yapılmayanlar" (#74) ve öncelik kuralı (EMİR 3) güncellendi. Kaynak tablosuna EM3, T73, DRY eklendi; CFG satırı #73 sonrası hale çevrildi | başlık bloğu |
| 2026-10-07 (EMİR 3) | Çerçeve ataması: abstract_v3 × deepseek, gpt → deepseek, mistral, gpt; story × deepseek, mistral, gpt → deepseek, gpt | §0, §0.1 Ç2–Ç3, §1, §2.2, §10, §13 |
| 2026-10-07 (EMİR 3) | Çağrı sayıları: deepseek 1200, gpt 1200, mistral 600 (Mistral'ın kolu story → abstract_v3); toplam 3000 değişmedi. #73 dry-run'ı aynı sayıları veriyor, fark yok | §2.2, §2.4 |
| 2026-10-07 (EMİR 3) | §5.1: Mistral'ın E2a sayımları yalnız abstract_v3 kolundan ve betimsel. Çerçeve karşılaştırmasının yalnız DeepSeek ve GPT içinde yapılacağı sınırlılık olarak yazıldı | §0.1 Ç3, §2.2, §5.1 |
| 2026-10-07 (EMİR 3) | §7: Mistral'ın E3 uygunluğu story kolundan → abstract_v3 kolundan; "EM2 m.11 Mistral'e uygulanamaz" uyarlaması kaldırıldı | §7, §13 m.11 |
| 2026-10-07 (EMİR 3) | Geri çekilme kuralı: EMİR 2 m.4'teki "kapı aşılırsa önce Mistral'ın abstract_v3 kolu çıkar, dry-run tekrarlanır; yine aşılırsa koşulmaz" sırası kaldırıldı. Yeni kural: kapı aşılırsa koşulmaz, raporlanır; kol çıkarılmaz. Gerekçe: yanlış kolu seçiyordu; veri görülmeden düzeltildi | §0.1 Ç3–Ç4, §8.1, §9.2, §15.3 |
| 2026-10-07 (EMİR 3) | Bütçe: sert tavan 6 → 10 USD; alt tavanlar Mistral 3 → 5, DeepSeek 2 → 5, GPT 0,5 (aynı); kapı 4,5 USD (aynı, ortalamaya göre). Alt tavan toplamı 5,5 → 10,5 USD. Gerekçe: p95 değerleri eski tavanların üstündeydi; beklenen harcama değişmez | §0, §0.1 Ç4, §0.2, §1, §8.1, §8.2, §9.3, §10, §12, §13 m.4 |
| 2026-10-07 (EMİR 3) | §6.1: kural anlama çağrısı koşuyu durdurmaz; `max_invalid` tükenirse `comp_missing` satırı; geçersizler ayrı raporlanır, %5 tavanına sayılmaz | §6.1, §7 U2, §9.3, §11.1 |
| 2026-10-07 (EMİR 3) | §6.2: q2'nin son cümlesi "Give the change as a whole number with its sign, for example +{example} or -{example}." → "Give the change as a whole number (it can be positive, zero or negative)."; `example` yer tutucusu ve düz tire / Unicode eksi notu kaldırıldı | §6.2, §13.1 K2 |
| 2026-10-07 (EMİR 3) | 3a (Mistral'da reasoning_capped = max(reasoning, completion) ≥ max_tokens − 4096; iki sayı ayrı; maliyet completion), 3d (linter varsayılan açık, `kind` zorunlu, yalnız "abstract" muaf) ve 3e (kart sha256 kilidi) tesisat bölümüne işlendi; 3f (`_notes`) not edildi | §4.1, §4.2, §7 U3, §9.1 A2, §9.2, §9.5 (yeni), §10, §11.1 |
| 2026-10-07 (EMİR 3) | §9.3 madde 3: %5 sınırı 60 / 30 (tahmin; payda belirsiz) → yalnız karar çağrılarından 54 / 27 / 54 [T73]. Kaynaklar bölümündeki "kural anlama çağrılarının paydaya girip girmediği (doğrulanamadı)" maddesi kaldırıldı | §9.3, Kaynaklar |
| 2026-10-07 (EMİR 3) | §15 yeniden yazıldı: #73'ün son dry-run'ı (model × kol ortalama ve p95, toplam ~4,0440 / ~9,4348, kapı GEÇER, 2.–10. tur varsayımı). #71'in dry-run'ları çıkarıldı. Deneme 1: 3600 çağrı, ~6,8468 / ~14,1820, kapı aşıldı. Deneme 2 (Mistral yalnız story): 3000 çağrı, ~4,0867 / ~9,4940, Mistral story 2,8028 / 4,7472 | §0, §8.2, §8.3, §15 |
| 2026-10-07 (EMİR 3) | §17 "Kullanıcıya tek soru" → "Kullanıcı onayı": (a) q2 değişti, yeni metinle onaylandı (eski karar: düz tire `-3`); (b) Mistral E3 abstract_v3 kolundan (eski: story kolundan); (c) 2.–10. tur varsayımı onaylandı | §17 |
| 2026-10-07 (EMİR 3) | Bekleyenler: D2 S1–S8 ana deney prereg'ine kalır; Hikâye A'nın ceza adımı P koşulundan önce yeniden yazılacak (EM3 Bölüm 6 atfı eklendi) | §16 |
| 2026-10-07 (EMİR 3) | sha256 `frames/abstract_v3.json`: `9bdc919a0eebe1991e69212e9144e6ef49622da0f20cd9886bd94ded312bf163` → `09b4d67b7b6640e33c0c265bec3324b2572293e61ac5d58bac798757ecb93e5a` | §4.2, §10 |
| 2026-10-07 (EMİR 3) | sha256 `frames/story_A.json`: `4e38eb4891071419659a1b3f26b2c1a80a77fe88e3be74cc559b1f7575e49977` → `d8face90d927cb4d21ee23e53ace2458937f0e029996f88334441d3ab9190d7d` | §0.1 Ç1, §4.1, §10, §13 m.1 |
| 2026-10-07 (EMİR 3) | sha256 `cards/pilot_cards_v3.json`: `a4f50d0f36296c4f38450a78210703c81aeabec1af4f72830c91a00266d7a9aa` → aynı; artık config'te `cards_sha256` ile kilitli | §2.1, §9.5, §10 |
| 2026-10-07 (EMİR 3) | sha256 `configs/minipilot.json`: `4bcece91…b996` → `34814a74b548f35d4ad97039d56120003c1cdc2404664bfd20d39e8c33ae7421` [T73] | §15.3 |
| 2026-10-07 (EMİR 3) | §13.2 (EMİR 3 kod değişiklikleri, 379 test, commit 3be3620) eklendi; §0.2'ye EMİR 3 eşleme tablosu eklendi | §0.2, §13.2 |
| 2026-10-07 (EMİR 3) | CFG satır atıfları #73 sonrası config'e göre güncellendi: 6. satıra `cards_sha256`, 60. satıra `reasoning_cap_rule` eklendiği için alanlar kaydı. §10'daki "eski bilgi" notu kaldırıldı, çünkü `_notes` baştan yazıldı | §0, §0.1, §1, §2, §3, §4, §8.1, §9.1, §10 |

**Değiştirilmeden korunan bölümler** (görev #74): §0.1 Ç5–Ç8, §5.0, §5.2, §5.3, §6.3, §6.4, §9.4, §11.2, §11.3, §12 (S6–S8 satırı hariç), §13.1 (K1 linter satırına eklenen cümle ve K2 hariç), §14, §15.5, Ek A ve aşağıdaki EMİR 2 günlüğü.

---

## Değişiklik günlüğü (2026-10-07, EMİR 2, görev #72)

Dosya baştan yazıldı. Değişen bölümler:

1. **Başlık bloğu:**
   - Sürüm ve tarih notu güncellendi.
   - `prereg_approved: false` satır kaynağıyla yazıldı.
   - Öncelik kuralı EMİR 2'ye çevrildi.
   - Kaynak tablosuna EM2, T67–T71, TO, D2 eklendi; REPO ve CFG satırları güncellendi.
2. **§0:** Sonuç baştan yazıldı. §0.1 "çözülmesi gereken çelişkiler" yerine "kapatılan kararlar (Ç1–Ç8)". §0.2'ye EMİR 2 eşleme tablosu eklendi; GE tablosunda stil adı ve bütçe güncellendi.
3. **§1:** Pilot v2 ve #63 fark tabloları güncellendi (çerçeve, bütçe, kural anlama, sağlayıcı adı).
4. **§2:**
   - §2.1'de stil adı "nötr prosedür kartı" oldu.
   - §2.2'de son `frames` ataması yazıldı.
   - §2.3'te run adı ve seed karara bağlandı.
   - §2.4'te çağrı sayısı 3000 oldu.
5. **§3:** M1 sürümleri eklendi; Mistral reasoning bilgisi, `model_version` ve snapshot denetimi güncellendi.
6. **§4:**
   - §4.1'deki yer tutucu kaldırıldı; story_A, sha256 ve koşu başı linter yazıldı.
   - §4.2'ye sha256 ve kapsam (deepseek, gpt) eklendi.
7. **§5:**
   - §5.0'a `step` süzmesi ve Mistral alanı eklendi.
   - §5.1'de ölçüt 528/387, eşikler 176/129, Ç8 hariç etiketi, geniş sözlükler ikincil sayım olarak yazıldı.
   - §5.2'de b1 yeniden yazıldı ve D_min eklendi.
8. **§6:**
   - §6.1'e `step` süzmesi ve sürdürme eklendi.
   - §6.2'de yeni q2 metinleri ve story_A metni yer aldı.
   - §6.4 karara bağlandı.
9. **§7:** max(e, g); U2 ve U3 karara bağlandı; esas kol ve Mistral istisnası eklendi.
10. **§8:** 6 / 4,5 USD, alt tavanlar, geri çekilme, süre aşımı muhasebesi, kalibre maliyet ve uçuş aşımı (parallel_units 3) yazıldı.
11. **§9.1–9.3:**
    - A3 ve A4'e EMİR 2 K3 ve K4 eklendi.
    - Başlamama koşulları (kilit, linter, 4,5 kapı) ve durma koşulları (6 USD, alt tavan, `model_version_changed`) güncellendi.
12. **§10:** Öneri tablosu, config'in son hali tablosuna dönüştü.
13. **§11:**
    - §11.1'e model başına `n_deadline` ve yeni sayaçlar eklendi.
    - §11.2'ye S7 başlığı ve Ç8 eklendi.
    - §11.3'teki kimlik kök listesi genişletildi.
14. **§12:** S6–S8, PV E2, E5 ve E7 durumları ile madde 17 notu güncellendi.
15. **§13:** Onay soruları, karar tablosuna (m.1–19) dönüştü. §13.1 kod değişiklikleri eklendi.
16. **Yeni bölümler:** §14 (M1), §15 (kalibre dry-run, kapı, sınırlılıklar, n_deadline), §16 (ana deneyden önce), §17 (tek soru).
17. **Kaynaklar ve doğrulama notları** güncellendi.

**Değiştirilmeden korunan bölümler** (önceki metinle birebir aynı; görev #72'de satır satır karşılaştırıldı):
- §5.3 E2c;
- §6.3 cevap anahtarı;
- §9.4 veri kalıcılığı;
- Ek A.

**Önceki sürümdeki bölüm içi "Değişiklik (Görev E)" notları** (değişen bölümlerden buraya, metni değiştirilmeden taşındı):
- §1: Tablo E1'e göre güncellendi. Karışıklık (confound) sınırlılığı Ç3'e taşındı.
- §2: Kartlar v2'den v3'e geçti (kurum olgusu). 5 nokta ve 2/2 tekrar E1 ile sabitlendi (eski §11 soru 4–5). Hikâye kolu 3 modele çıkarıldı (Ç2'ye bağlı). Abstract_v3 Ç3'e bağlandı. Çağrı sayıları yeniden hesaplandı.
- §3: Çerçeve sütunu çıkarıldı (§2.2'ye taşındı). GPT için rationale kuralı eklendi.
- §4: A/B karşılaştırma tablosu ana metinden çıkarıldı (Ç1 (b) seçilirse kullanılmak üzere Ek A'da). Balıkçı metni yazılmadı; yer tutucu konuldu.
- §5: H-tanıma ve H-oyun teorisi E2a'nın (i) ve (ii) sayımlarına dönüştü. Sözlükler GE listesine indirildi. Karşılaştırma abstract_v3 yerine pilot v2'yle yapılıyor. H-kart, E2b'de kurum olgusu kartını da kapsıyor. Etiket max(e, g) yerine e = 2 (Ç6). E2c ve D_grup(9) eklendi.
- §6: A ve B metinleri Ek A'ya taşındı. Revizyon tetiğinin yerini E3 aldı. Dışlama sorusu Ç5'te açık kaldı.
- §7: Yeni bölüm (E3).
- §8: Tavan ve kapı 6 / 4,5 USD'den 4 / 3 USD'ye indi. Maliyet tahmini 5 nokta ve 3 modelli hikâye düzenine göre yeniden hesaplandı. 21 noktalı senaryo çıkarıldı (E1).
- §9: Tavan 4 USD ve kapı 3 USD oldu. Görev A ekleri E4'e göre yeniden sıralandı. İçerik #63 §8 ile aynı; PR §8.2 ve A2.3–A2.4 ile karşılaştırılarak korundu.
- §10: `cards`, `frames`, `frame_files`, `isolated_points`, `groups_per_cell`, `isolated_reps`, `budget_usd`, `expected_cost_gate_usd` ve `_notes` alanları E'ye göre güncellendi.
- §11: Tanıma, kural anlama ve kimlik anılma maddeleri E5'e göre açıkça eklendi. Örneklem kural anlama yanıtlarıyla genişletildi.
- §12: #63 §9 tabloları E ile cevaplananlara göre kısaltıldı. #61 ve #62'nin açık tesisat soruları değişmedi: sistem mesajı yalnız kart; izolede kural anlama çizelge başına bir kez; kural anlama satırları tur 1'e bağlı; q2'nin 10 puanlık biçimi; şemadaki rationale açıklaması [#63 §9.3].

---

# Teknik not — minipilot_20261008 (2026-10-09)

Bu not yukarıdaki metni değiştirmez. Prereg kuralları, sözlükler ve eşikler aynen geçerlidir. Not yalnız tesisatı ve sayıları kayda geçirir; bilimsel yorum içermez. Not yazılırken API çağrısı yapılmadı, yeni koşu başlatılmadı, `runs/minipilot_20261008/` dizinine yazılmadı ve `raw_calls.jsonl` kopyalanmadı (hesap kimliği içerir). Alıntılar redakte filtresinden geçti; üç alıntıda da hesap ya da anahtar kimliği bulunmadı (redakte sayısı 0).

Kaynaklar:
- **RES**: `runs/minipilot_20261008/minipilot_20261008.jsonl` (2780 satır).
- **RAW**: `runs/minipilot_20261008/raw_calls.jsonl` (3136 satır).
- **SUM**: `runs/minipilot_20261008/minipilot_20261008_summary.json` (segment 23 sonrası son hal).
- **KR**: `minipilot_kosu_raporu.md` (görev #76).
- **CFG**: `configs/minipilot.json` (orc/PublicGoods `149e73f`).
- **TNS**: `minipilot_analiz/teknik_not_sayilar.py`. Bu nottaki her sayıyı yeniden üretir. Çıktıları `minipilot_analiz/teknik_not_sayilar.json`, `teknik_not_sayilar_cikti.md` ve `redrawn_points.csv`.

## T1. Mistral durması (§9.3 madde 3, `invalid_rate_cap`)

**Kural ve sayı.** Mistral'ın geçersiz sayısı `n_invalid` + `n_parse_fail` = 28 + 0 = 28. Sınır 27 = 0,05 × 540 (540 = Mistral'ın planlanan karar çağrısı; 600 çağrıdan 60 kural anlama çağrısı düşülür). 28 > 27 olduğu için kural tetiklendi [SUM `model_stops.mistral`, `invalid_limit_per_model`].
- RAW'daki `pgg_model_stopped` olayı segment 14 numarasını taşıyor. Olay, segment 14'ün SIGINT kaydından 56,5 sn sonra yazıldı.
- SUM'da durma `at_resume: true` olarak görünüyor. Segment 15'ten itibaren Mistral'a çağrı gönderilmedi [KR §8].
- Kural değişmedi. Mistral yeniden başlatılmadı. Bu durum yalnız sınırlılık olarak kayda geçer.

**Neden: 28 geçersiz kaydın sınıflaması.** RAW'daki 29 `invalid_payload` olayından 28'i Mistral'a ait (DeepSeek 1, GPT 0). Bu 28 kaydın hepsi `response_parsed` biçimine göre sınıflandı [TNS `classify_invalid`]:

| Sınıf | n |
|---|---|
| Şema geri yazımı: model cevap yerine istemdeki JSON şemasını (`type`, `required`, `properties`) geri yazdı, cevap değeri yok | **25** |
| Şema içinde cevap: `properties` altına şema alanlarıyla birlikte `"contribution": <sayı>` ve `"rationale"` eklendi | **2** |
| Şema içinde cevap: şemanın `contribution` alanına `"value": <sayı>` eklendi | **1** |
| Diğer | **0** |
| **Toplam** | **28** |

- Adımlara dağılım: grup turu 27, izole 1, kural anlama 0. Kural anlama geçersizleri ayrı sayılır (`n_comp_invalid` = 0).
- 28 yanıtın hepsinde `finish_reason` = stop.
- Segmentlere dağılım: segment 0'da 2, 2'de 3, 3'te 5, 5'te 2, 6'da 5, 10'da 1, 11'de 2, 12'de 2, 13'te 3, 14'te 3.

**28 kaydın kaçı atılan yanıtlarda? Sayım tanımı.** SUM `n_invalid` değerini RAW'daki `invalid_payload` olaylarından sayar. Satırdaki `n_invalid` ise yalnız o satırı üreten çağrının, aynı segmentteki geçersiz denemelerini taşır [KOD `_scan_raw_log`]. Buna göre:
- **20** geçersiz, aynı segmentte kabul edilmiş bir satır üreten çağrılarda. Satırlardaki `n_invalid` toplamı da 20.
- **8** geçersiz, o segmentte kabul edilmiş yanıt üretmeyen çağrılarda. Geçersiz yanıttan sonraki deneme uçuştayken segment SIGINT ile kesildi. Bu 8 kayıt 6 karar noktasına ait (iki noktada ikişer geçersiz var). Her nokta bir sonraki segmentte yeniden istendi (T2'deki "ek 7 nokta"nın 6'sı).
- **0** geçersiz, atılan (discarded) yanıtlarda. Atılan yanıt tanım gereği geçerli, kabul edilmiş bir yanıttır.

KR §5.1'deki "+8 atılan yanıtlarda" ifadesi bu ayrımı yapmaz. Sayı (8) doğrudur ama bu 8 geçersiz atılan yanıtlarda değil, kesilen çağrılardadır. Durma kuralı SUM değeriyle (28) işledi.

**Örnek üç kayıt (birebir; RAW'daki `response_raw` metni).**

1. `raw_calls.jsonl` satır 133 (`invalid_payload`; yanıt kaydı satır 132). Segment 0; model mistral; çerçeve abstract_v3; adım grup turu (contribute), tur 3, ajan 3; birim `mistral|boston_minimal|minimal|N|group|0|abstract_v3`. Sınıf: şema geri yazımı.
```
{"type": "object", "required": ["contribution"], "properties": {"contribution": {"type": "integer", "minimum": 0, "maximum": 20}, "rationale": {"type": "string", "description": "One or two sentences on why you chose this."}}}
```
2. `raw_calls.jsonl` satır 1630 (`invalid_payload`; yanıt kaydı satır 1629). Segment 11; model mistral; çerçeve abstract_v3; adım izole (isolated), tur yok (izole), ajan 1; birim `mistral|boston_minimal|minimal|N|isolated|0|abstract_v3`. Sınıf: şema içinde cevap (properties altında değer).
```
{"type": "object", "required": ["contribution"], "properties": {"contribution": {"type": "integer", "minimum": 0, "maximum": 20}, "rationale": {"type": "string", "description": "One or two sentences on why you chose this."}, "contribution": 15, "rationale": "The other players averaged 15 points last round, so I'll match their cooperation to maintain trust and keep everyone contributing for the remaining five rounds."}}
```
3. `raw_calls.jsonl` satır 2129 (`invalid_payload`; yanıt kaydı satır 2128). Segment 13; model mistral; çerçeve abstract_v3; adım grup turu (contribute), tur 6, ajan 3; birim `mistral|riyadh_minimal|minimal|N|group|1|abstract_v3`. Sınıf: şema içinde cevap (şema alanına `value` eklenmiş). Bu çağrı satır üretmedi; geçersizden sonraki deneme kesildi.
```
{"type": "object", "required": ["contribution"], "properties": {"contribution": {"type": "integer", "minimum": 0, "maximum": 20, "value": 0}, "rationale": {"type": "string", "description": "Since other players contributed nothing in the last round and contributing when they don't lowers my earnings, I'll keep all 20 points to maximize my own payoff."}}}
```

28 kaydın tam listesi (ham log satırı, segment, birim, adım, tur, ajan, sınıf, akıbet) `minipilot_analiz/teknik_not_sayilar_cikti.md` dosyasında.

**Mistral'ın tamamlanma durumu.**
- Mistral'da planlanan 600 satırın **380**'i var: karar 342 (grup turu 312, izole 30) ve kural anlama 38.
- Planlanan 24 Mistral biriminden (12 grup birimi × 44 satır, 12 izole birim × 6 satır) **13**'ü tamamlandı.
- Koşulmayan **11** birim aşağıda [RES; RAW; SUM `units`, `resume_points`]:

| # | Birim | Durum | Satır / planlanan |
|---|---|---|---|
| 1 | `mistral\|riyadh_minimal\|minimal\|N\|group\|1\|abstract_v3` | **Yarım.** Tur 1–8 kabul edildi (segment 11–14). **9. turda kaldı:** RAW'da 9. ve sonraki turlar için hiç çağrı kaydı yok. 4 kural anlama satırı var. SUM `resume_points`: `from_round` 9, `rounds_kept` 8 | 36 / 44 |
| 2 | `mistral\|boston_minimal\|minimal\|N\|group\|1\|abstract_v3` | Hiç başlamadı (RAW'da oturum kaydı yok) | 0 / 44 |
| 3 | `mistral\|riyadh_factual\|factual\|N\|group\|1\|abstract_v3` | Hiç başlamadı | 0 / 44 |
| 4 | `mistral\|boston_factual\|factual\|N\|group\|1\|abstract_v3` | Hiç başlamadı | 0 / 44 |
| 5 | `mistral\|riyadh_value\|value\|N\|group\|1\|abstract_v3` | Hiç başlamadı | 0 / 44 |
| 6 | `mistral\|boston_minimal\|minimal\|N\|isolated\|1\|abstract_v3` | Hiç başlamadı | 0 / 6 |
| 7 | `mistral\|riyadh_value\|value\|N\|isolated\|1\|abstract_v3` | Hiç başlamadı | 0 / 6 |
| 8 | `mistral\|riyadh_factual\|factual\|N\|isolated\|1\|abstract_v3` | Hiç başlamadı | 0 / 6 |
| 9 | `mistral\|riyadh_minimal\|minimal\|N\|isolated\|1\|abstract_v3` | Hiç başlamadı | 0 / 6 |
| 10 | `mistral\|boston_factual\|factual\|N\|isolated\|1\|abstract_v3` | Hiç başlamadı | 0 / 6 |
| 11 | `mistral\|boston_value\|value\|N\|isolated\|1\|abstract_v3` | Hiç başlamadı | 0 / 6 |

Sıra, SUM `unit_order` içindeki sıradır. Bu 11 birimin planlanan satırı 5 × 44 + 6 × 6 = 256; bunların 36'sı var. Eksik satır 256 − 36 = 220, yani 600 − 380.

## T2. Zaman dilimli koşu

**Segmentler.** Koşu ön planda, araç süre sınırının (600 sn) altında kalan dilimlerle yürütüldü. Sarmalayıcı (`_segment_kos.py`) belirlenen sürede SIGINT gönderdi; süreç 45 sn içinde kapanmazsa KILL gönderdi.
- **24 segment** oluştu (0–23).
- **23 segment** `stop_reason: interrupted` ile bitti. RAW'da 23 `pgg_run_stopped` olayının hepsinde `signal: SIGINT` var.
- Segment 23 kendiliğinden bitti (`stop_reason` null; süre 541,4 sn).

Segment süreleri (SUM `segments[].duration_s`, sn):

| Seg | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Süre | 537,9 | 532,4 | 478,4 | 493,8 | 539,1 | 468,3 | 493,7 | 468,4 | 610,0 | 438,4 | 438,4 | 502,1 |
| SIGINT kaydı | 537,9 | 474,5 | 478,4 | 493,8 | 468,4 | 468,3 | 468,3 | 468,3 | 610,0 | 438,4 | 438,4 | 438,1 |

| Seg | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Süre | 438,4 | 438,1 | 438,2 | 519,6 | 499,0 | 498,1 | 499,2 | 498,8 | 499,2 | 499,1 | 498,9 | 541,4 |
| SIGINT kaydı | 438,4 | 438,1 | 438,2 | 519,6 | 499,0 | 498,1 | 499,2 | 498,7 | 499,2 | 499,1 | 498,9 | – |

"SIGINT kaydı" satırı, RAW'daki `pgg_run_stopped` kaydının segment başlangıcından (`pgg_run_start` ya da `pgg_run_resume`) itibaren kaçıncı saniyede yazıldığını gösterir.

Kesilen 23 segmentin süresi:
- En kısa 438,1 sn, medyan 498,8 sn, ortalama 492,5 sn, en uzun 610,0 sn.
- 23 segmentin 22'si **438,1–539,1 sn** aralığında. Tek istisna segment 8 (610,0 sn).

Fiilen her segment yaklaşık 440–540 sn'lik bir pencereydi; bir kez 610 sn'ye çıktı. Görev açıklamasındaki "~440–570 sn" ifadesinin üst ucu run dosyalarında görünmüyor. Gözlenen aralık 438–539 sn, artı bir kez 610 sn. Sarmalayıcının her segmentte kullandığı süre sınırı run dosyalarına yazılmadığı için segment 8'in uzunluğunun nedeni bu dosyalardan saptanamıyor.

**Config'teki 900 sn işlemedi.**
- CFG'deki süre değerleri: `request_deadline_s` = 900, `request_timeout_s` = 300, `stall_timeout_s` = 1800.
- En uzun segment 610,0 sn sürdü. Hiçbir segment 900 sn'ye ulaşmadı, dolayısıyla tek bir çağrının 900 sn'lik süre sınırına ulaşması mümkün olmadı.
- `n_deadline` = 0, `n_transport` = 0, `timeout_changes` boş.
- RAW'da `elapsed_s` taşıyan 2909 yanıt kaydının değerleri (usage dönen 2912 yanıttan 3 sağlayıcı hatası kaydında `elapsed_s` yok): en yüksek 527,5 sn, medyan 6,1 sn. 300 sn'yi aşan yanıt sayısı 10.
- Fiilî üst sınır segment penceresiydi. Pencere içinde dönmeyen çağrı SIGINT ile kesildi.

**Sayılamayan kısım.** SIGINT ya da KILL anında uçuşta olan çağrılar ham loga yazılmadı. Kodun bu sürümünde denemenin başladığını gösteren bir kayıt yok. Bu yüzden öldürülen çağrıların sayısı ve maliyeti run dosyalarından sayılamıyor. Görünen etki aşağıda.

**Görünen etki 1: 100 atılan (discarded) yanıt.**
- Kaynak: RAW'daki `pgg_discarded` olayları, toplam 100. SUM `n_discarded` = 100 (DeepSeek 74, Mistral 26, GPT 0).
- Nedenler: `found_on_resume` 87, `round_not_completed` 13.
- Atılan yanıt, kabul edilmiş (geçerli) ama satıra dönüşmemiş, faturalanmış yanıttır.

| Model × çerçeve | Grup turu | İzole | Kural anlama | Toplam |
|---|---|---|---|---|
| deepseek × abstract_v3 | 8 | 6 | 3 | 17 |
| deepseek × story | 12 | 21 | 24 | 57 |
| mistral × abstract_v3 | 21 | 3 | 2 | 26 |
| gpt × abstract_v3 | 0 | 0 | 0 | 0 |
| gpt × story | 0 | 0 | 0 | 0 |
| **Toplam** | **41** | **30** | **29** | **100** |

**Görünen etki 2: yeniden çekilen karar noktaları. Sayı 58 değil, 94.**

- **Karar noktası:** birim (oturum) × adım × tur × ajan. İzole adımda tur yoktur; nokta `others_mean` ile ayrılır.
- **Kullanılan tanım (birincil):** en az bir geçerli, kabul edilmiş yanıtı atılmış (`pgg_discarded`) ve sonra yeniden istenmiş nokta. Görevdeki iki tanım bu veride aynı kümeyi veriyor:
  - (i) "discarded sonrası yeniden istenen nokta" = **94**;
  - (ii) "kabul edilmiş satırın birden fazla denemeden geldiği nokta" = **94**. Buradaki deneme, segmentler boyunca geçerli kabul edilmiş yanıt demektir; `invalid_payload` ile geri alınan kabuller düşülür.
- İki küme birebir aynı. 94 noktanın hepsinin sonuç satırı var, yani hepsi yeniden istenip kabul edildi.
- **Kodda nasıl saptandı [TNS]:**
  - RAW'daki her `pgg_discarded` olayının `call` alanından (`step`, `round`, `agent_id`, `others_mean`) ve `session_id`'sinden nokta anahtarı kuruldu.
  - Aynı anahtar RES satırlarında arandı.
  - Kontrol için her noktanın geçerli kabul kayıtları (RAW'da `response_parsed` taşıyan kayıtlar, `invalid_payload` ile geri alınanlar hariç) sayıldı.
- `n_attempts` = noktanın geçerli kabul edilmiş yanıt sayısı (atılanlar ve satırdaki). Dağılım: 2 deneme 90 noktada, 3 deneme 2 noktada, 4 deneme 2 noktada. Toplam 90 × 1 + 2 × 2 + 2 × 3 = 100 atılan yanıt.
- Etkilenen birim sayısı 24.
- **Üst yöneticinin ön sayımı (58) yeniden üretilemedi.** Denenen diğer birleştirmeler:

  | Birleştirme | Sayı |
  |---|---|
  | Birim | 24 |
  | Birim × adım | 38 |
  | Birim × adım × tur | 42 |
  | Birim × atılma segmenti | 30 |
  | Birim × adım × tur × atılma segmenti | 46 |
  | Nokta, izolede `others_mean` yok sayılırsa | 78 |

  Hiçbiri 58 vermiyor. Farkın nedeni run dosyalarından saptanamadı. Bu notta 94 kullanılır.

| Model × çerçeve | Grup turu | İzole | Kural anlama | Toplam |
|---|---|---|---|---|
| deepseek × abstract_v3 | 8 | 6 | 3 | 17 |
| deepseek × story | 12 | 17 | 22 | 51 |
| mistral × abstract_v3 | 21 | 3 | 2 | 26 |
| gpt × abstract_v3 | 0 | 0 | 0 | 0 |
| gpt × story | 0 | 0 | 0 | 0 |
| **Toplam** | **41** | **26** | **27** | **94** |

- Atılan 100 yanıt ile 94 nokta arasındaki 6'lık fark: 2 noktada 2 atılma, 2 noktada 3 atılma var. Bu noktaların hepsi deepseek × story'de (izole 4, kural anlama 2).
- **Ek, birincil tanımın dışında: 7 nokta.**
  - Bu noktalarda atılmış geçerli yanıt yok. Önceki bir segmentte faturalanmış yalnız geçersiz denemeler var. Geçersizden sonraki deneme segment kesilince kayboldu, nokta sonraki segmentte yeniden istendi.
  - Dağılım: Mistral grup turu 6 (T1'deki 8 geçersiz), DeepSeek × story izole 1 (`deepseek|boston_minimal|minimal|N|isolated|1|story`, `others_mean` 20, segment 21 → satır segment 23).
  - Önceki bir segmentte faturalı denemesi olan nokta sayısı 94 + 7 = **101**.
  - Bu 7 nokta `redrawn_points.csv`'de yok. Listesi `teknik_not_sayilar.json` → `yeniden_cekilen.ek_atilmadan_yeniden_istenen` alanında.
- `redrawn_points.csv`'de atılan ve kabul edilen cevaplar ayrı sütunlarda (`discarded_answers`, `kept_answer`). Cevap aynı olan nokta 59, farklı olan nokta 35. Yalnız sayımdır.

**Sınırlılık: uzun düşünen çağrılar.** Uzun süren çağrıların pencere sonunda kesilme ve yeniden çekilme olasılığı daha yüksektir. Kesilip loglanmayan çağrılar sayılamadığı için bu etki tam ölçülemiyor. Betimsel karşılaştırma aşağıda, yorumsuz. Atılan 100 yanıtın her biri RAW'daki geçerli kabul kaydıyla eşleşti (100/100); kabul edilen değerler RES satırlarından alındı.

| Model × adım | Ölçü | Atılan: n / medyan / Ç1–Ç3 / en yüksek | Kabul edilen: n / medyan / Ç1–Ç3 / en yüksek |
|---|---|---|---|
| deepseek (tümü) | elapsed_s | 74 / 18,5 / 6,5–86,5 / 352,5 | 1200 / 10,3 / 5,8–48,4 / 527,5 |
| deepseek (tümü) | reasoning_tokens | 74 / 884 / 212,5–3977,5 / 11904 | 1200 / 399 / 221,2–2388 / 11904 |
| deepseek × grup turu | elapsed_s | 20 / 56,3 / 23,7–125,7 / 170,2 | 960 / 10,5 / 6,1–37,1 / 326,1 |
| deepseek × grup turu | reasoning_tokens | 20 / 2624 / 1198,8–3865,5 / 9968 | 960 / 416 / 234–1884,2 / 11904 |
| deepseek × izole | elapsed_s | 27 / 82,8 / 18,3–149,7 / 352,5 | 120 / 105,0 / 54,5–167,0 / 527,5 |
| deepseek × izole | reasoning_tokens | 27 / 4099 / 736–6682 / 11904 | 120 / 5634 / 2963,5–9586,8 / 11904 |
| deepseek × kural anlama | elapsed_s | 27 / 4,9 / 3,4–9,4 / 37,7 | 120 / 4,7 / 3,8–6,0 / 58,6 |
| deepseek × kural anlama | reasoning_tokens | 27 / 202 / 172–229 / 319 | 120 / 189,5 / 160,5–235,2 / 445 |
| mistral (tümü) | elapsed_s | 26 / 66,8 / 42,9–87,1 / 145,6 | 380 / 48,9 / 32,9–73,1 / 199,8 |
| mistral (tümü) | reasoning_tokens | 26 / 2909 / 2423,2–3586 / 7507 | 380 / 2469 / 1936,5–3043,8 / 7470 |
| mistral × grup turu | elapsed_s | 21 / 64,7 / 39,6–82,5 / 145,6 | 312 / 50,4 / 35,8–74,1 / 199,8 |
| mistral × grup turu | reasoning_tokens | 21 / 3074 / 2466–3696 / 7507 | 312 / 2550 / 2043,5–3077 / 7470 |
| mistral × izole | elapsed_s | 3 / 86,8 / 50,6–110,3 / 110,3 | 30 / 71,7 / 51,4–93,3 / 152,9 |
| mistral × kural anlama | elapsed_s | 2 / 79,6 / 71,6–87,5 / 84,9 | 38 / 25,7 / 20,6–31,5 / 67,9 |

- Ç1–Ç3: birinci ve üçüncü çeyrek (Python `statistics.quantiles`, n = 4, varsayılan yöntem).
- GPT'de atılan yanıt yok. GPT'nin 1200 kabul edilen satırında `elapsed_s` medyanı 3,6 sn, en yüksek değeri 13,8 sn.
- Bu tablo yalnız loglanmış atılan yanıtları kapsar. Kesilip loglanmayan çağrılar tabloda yok.

## T3. Yeniden üretim

```
cd workspace && python3 -I minipilot_analiz/teknik_not_sayilar.py
```

- Script `runs/minipilot_20261008/` dizinini yalnız okur. Çıktıları `minipilot_analiz/` altına yazar:
  - `teknik_not_sayilar.json` (bütün sayılar);
  - `teknik_not_sayilar_cikti.md` (tablolar ve 28 geçersizin listesi);
  - `redrawn_points.csv` (94 satır + başlık).
- CSV sütunları:
  - Görevde istenenler: `model`, `frame`, `unit_id`, `round`, `agent`, `step`, `n_attempts`.
  - Ek sütunlar: `others_mean`, `n_discarded`, `discarded_segments`, `discard_reasons`, `kept_segment`, `n_billed_responses`, `discarded_answers`, `kept_answer`.
  - `round`, izole noktalarda boştur.

---

# Okuma eki (2026-10-09)

Bu ek yukarıdaki metni değiştirmez; yalnız sona eklendi. Prereg kuralları, sözlükler ve eşikler aynen geçerlidir. Nedensel iddia yok: okuma metinlerinden nedensel sonuç çıkarılmadı, katkı değerleri yorumlanmadı. Bulgular §11.3 gereği betimseldir ve analize girmez.

- Ekin tarihi okuma raporlarının tarihidir (2026-10-09). Ek görev #89 ile 2026-10-10'da yazıldı. Bu görevde API çağrısı yapılmadı, kod çalıştırılmadı, runs/ ve raw_calls.jsonl açılmadı.
- Ayrıntı ve kaynaklar: minipilot_muhakeme_okuma.md (workspace kökü). Girdi raporları: minipilot_okuma_deepseek_abstract_p1.md (#87), minipilot_okuma_deepseek_abstract_p2.md (#88), minipilot_okuma_deepseek_story.md (#83), minipilot_okuma_mistral.md (#84), minipilot_okuma_gpt.md (#85). Sayımlar: minipilot_analiz/okuma_sayim.md (#81) ve minipilot_analiz/minipilot_analiz.md (#78).

## Kapsam

- Beş kol okundu: DeepSeek abstract_v3 (600 kayıt), DeepSeek story (600), Mistral abstract_v3 (380), GPT abstract_v3 (371) ve GPT story (432). Rationale'lerin hepsi okundu. Reasoning baştan sona DeepSeek'te kol başına 38, Mistral'da 32 kayıtta, GPT'de reasoning dönen her kayıtta okundu.
- DeepSeek abstract_v3 okuması iki parçadır (#87, #88). Toplamlar #81 ve #78 ile karşılaştırılabilen her maddede tutuyor: kayıt 600, değer kartı rationale'inde kimlik kökü 17 satır (25 eşleşme), reasoning_capped 6, kural anlama 60/60 doğru.

## Bulgular (özet)

1. Tanıma: E2a (i) "experiment" hariç, etiket alanında DeepSeek abstract_v3 537/540, DeepSeek story 533/540, Mistral 342/342; GPT'de etiket alanı rationale ve iki çerçevede 0/540 (#78). DeepSeek ve Mistral reasoning'de "beklenen cevap" ya da benchmark arıyor (ör. MP-2434, MP-1534). GPT'de tanıma yalnız reasoning özetinde görülüyor (ör. MP-348).
2. Kural anlama: yanlış yalnız GPT story'de var, 2/60; ikisinde de q1 alanına kavanoz payı (16) yazılmış (MP-588, MP-2244). Diğer kollarda 0. Faiz sanılan bir çarpan okuması gözlenmedi.
3. Kimlik anılma (değer kartı, karar rationale'i, kök sözlüğü): Mistral 107/130, DeepSeek abstract_v3 17/180, DeepSeek story 4/180, GPT 0/180 (#81). Nötr prosedür kartının olgusu rationale'e yalnız bir kayıtta giriyor (MP-1140); reasoning'de çoğunlukla "irrelevant" ya da "prompt injection" diye anılıyor.
4. Mistral'ın 28 geçersiz yanıtı: 25'i şemayı aynen geri yazma, 3'ü şema içinde cevap (2 ve 1). Aralık dışı, düzyazı ve diğer sınıfları 0. Sınıflama teknik not T1 ile aynı.
5. Abstract_v3 ile story karşılaştırması (yalnız DeepSeek ve GPT; Mistral girmez): DeepSeek story'de kavanoz kendiliğinden "public goods game" diye adlandırılıyor (444/540 karar satırı, #81) ve amaç ya da ödeme belirsizliği not ediliyor (MP-2433). GPT story'de gün sırası bazı rationale'lerde yanlış okunuyor (MP-7). Bunlar gözlemdir; farklar bir nedene bağlanmadı.

## Öneriler (karar değil)

Ana deney öncesi öneriler ayrıntılı rapordadır (§6, K1-K12). Başlıcaları: cevap talimatında şema metni yerine örnek nesne ya da json_schema strict karşılaştırması (EMİR 4 madde 4d); yalnız karttan oluşan sistem mesajının "prompt injection" gibi okunmasının tasarım notuna alınması; izole sorunun süren bir oyun gibi okunmasının sınırlılık olarak yazılması. Hiçbiri prereg kuralı, sözlük ya da eşik değişikliği değildir.

## Sınırlılıklar

- Zaman dilimli koşu: 24 segment, 23 SIGINT; #77 tanımıyla 94 karar noktası yeniden çekildi (DeepSeek abstract_v3 17, DeepSeek story 51, Mistral 26, GPT 0). Okunan satırlar bu noktalarla eşlenmedi.
- DeepSeek reasoning_capped sayımı eksik olabilir (story 28/600; atılanlar dahil 30/657).
- Mistral'da eksik veri: 380/600 satır; altı karttan dördünde tek grup var.
- Okuma derinliği kısmi: grup 5. turu reasoning'i DeepSeek'te tam okunmadı; yalnız E2a ile giren kayıtların reasoning'i büyük ölçüde okunmadı; bazı sayımlar anahtar kelime alt sınırıdır.
- Girdi raporları R ve Q kısaltmalarını tutarsız kullanıyor; iki madde doğrudan karşılaştırılamıyor (ayrıntılı rapor §8.1).
