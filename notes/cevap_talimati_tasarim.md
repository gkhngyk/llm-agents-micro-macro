# Cevap talimatı: tasarım notu ve karşılaştırma (EMİR 4 / 4d, görev #80)

Tarih: 2026-10-09. Bu belge yalnız not ve karşılaştırmadır. Hangi seçeneğin kullanılacağı ve üç
modelde küçük biçim testi ayrı bir emirle yapılacak. API çağrısı yapılmadı; yalnız ücretsiz
`GET /api/v1/models/{id}/endpoints` okundu. Kodda iki seçenek bir config bayrağıyla eklendi;
varsayılan kapalı ve bugünkü istekler bayt bayt aynı (§9).

## 1. Sorun

Bugün her çağrının son mesajına kod (llm_client.augment_with_schema) şu metni ekliyor; çerçeve
dosyalarında bu metin yok:

```
Respond with ONLY a JSON object matching this schema:
{"type": "object", "required": ["contribution"], "properties": {"contribution": {"type": "integer", "minimum": 0, "maximum": 20}, "rationale": {"type": "string", "description": "One or two sentences on why you chose this."}}}
```

İstekte ayrıca `response_format: {"type": "json_object"}` var.

Mini-pilotta (`minipilot_20261008`, özet ve ham log, 2026-10-09'da yeniden sayıldı):

| Model | Yanıt | Geçersiz (`n_invalid`) | Parse hatası | degraded |
|---|---|---|---|---|
| Mistral Large 4 | 436 | **28** | 0 | 0 |
| DeepSeek V4.1 Flash | 1275 | 1 | 0 | 0 |
| GPT-6 Luna | 1201 | 0 | 0 | 0 |

Mistral `invalid_rate_cap` ile durdu (28 > 27). 28 geçersizin 25'inde model cevap yerine şemayı geri
yazdı, 3'ünde cevap şemanın içine yazılmıştı; hepsinde `finish_reason` = stop (prereg_minipilot.md
teknik not T1). Pilot v2'de (DeepSeek, GPT, Gemini) geçersiz 0, degraded 0.

## 2. Seçenekler

**A — örnek cevap nesnesi (şema metni yerine).** İki biçimi var:
- A1 (somut değerli): `{"contribution": 10, "rationale": "..."}`. Sayı içerdiği için çapalama riski
  taşır (§5). Uygulanmadı.
- A2 (yer tutuculu, uygulandı: `answer_format: "example"`). Tamsayı alanı soruda zaten yazan
  aralıkla, metin alanı açıklamasıyla gösterilir. Başka sayı yazılmaz. Sonuç geçerli bir JSON
  değildir, bir kalıptır:
  ```
  Respond with ONLY a JSON object of this form, with your own values in place of the <...> parts:
  {"contribution": <whole number from 0 to 20>, "rationale": "<One or two sentences on why you chose this.>"}
  ```
  Kural anlamada `{"q1": <whole number>, "q2": <whole number>, ...}`, cezada
  `{"punishments": {"2": <whole number from 0 to 10>, ...}}`, story_A'da
  `{"credits_into_jar": <whole number from 0 to 20>, ...}`. `response_format` json_object kalır.

**B — `response_format: json_schema`, `strict: true`.** Uygulandı: `answer_format: "json_schema"`.
- B1 (uygulandı): mesajlar bugünküyle bayt bayt aynı kalır, şema metni istemde durur. Yalnız
  `response_format` değişir:
  ```json
  {"type": "json_schema", "json_schema": {"name": "answer", "strict": true, "schema": {…, "required": ["contribution", "rationale"], "additionalProperties": false}}}
  ```
- B2 (şema metnini istemden çıkarmak): uygulanmadı. İstem değişir, B1'in karşılaştırılabilirlik
  avantajı kaybolur.
- Strict kipte her nesne kapalıdır (`additionalProperties: false`) ve her alan zorunludur.
  OpenAI dokümanı: "all fields … must be specified as `required`". Bu yüzden **`rationale` zorunlu
  hale gelir**; bugün isteğe bağlı ama pratikte hep yazılıyor. Ayrıca "outputs will be produced in
  the same order as the ordering of keys in the schema": cevap, gerekçeden önce yazılır. Bugün de
  şemadaki sıra bu; akıl yürütme modelleri gizli düşünmeyi zaten cevaptan önce yapıyor.

## 3. Üç modelde destek durumu

Kaynak: `GET https://openrouter.ai/api/v1/models/{id}/endpoints`, 2026-10-09 (ham yanıtlar
`workspace/gorev80_endpoints/`, tarih `fetched_at.txt`). OpenRouter dokümanına göre destek uç
nokta düzeyindedir ve `supported_parameters` içindeki `structured_outputs` ile gösterilir
(https://openrouter.ai/docs/features/structured-outputs).

| Model (config'teki uç nokta) | provider_name / quant | `response_format` | `structured_outputs` | Not |
|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash, `deepinfra/fp8` | DeepInfra / fp8 | var | var | Aynı modelin bazı uç noktalarında `structured_outputs` yok (ör. deepseek, novita/fp8, gmicloud/fp8). Bizim sabitlediğimiz uç noktada var |
| mistralai/mistral-large-4-0, `mistral` | Mistral / unknown | var | var | mistral/eu ve mistral/zdr de aynı |
| openai/gpt-6-luna, `openai` | OpenAI / unknown | var | var | `temperature` desteklenmiyor (zaten gönderilmiyor) |

Listede bulunmak, şemanın üretim sırasında zorla uygulandığı anlamına gelmez. OpenRouter dokümanı:
"exact compliance is not guaranteed on every endpoint". Bazı sağlayıcılar şemayı yalnız ipucu olarak
kullanabilir.
- OpenAI dokümanı strict kipte `minimum` / `maximum`'u destekliyor
  (https://developers.openai.com/api/docs/guides/structured-outputs).
- DeepInfra dokümanı json_schema için "The model is constrained to produce only values that match
  your schema" diyor, ama hangi şema anahtar sözcüklerinin desteklendiğini yazmıyor
  (https://docs.deepinfra.com/chat/structured-outputs).
- Mistral'ın kendi dokümanında `strict`'in nasıl uygulandığını ve min/max desteğini bulamadım.
  Kılavuz şemanın cevabı biçimlendirdiğini söylüyor
  (https://docs.mistral.ai/capabilities/structured-output/custom_structured_output/).

Üç uç noktada strict'in **gerçekten uygulanıp uygulanmadığı (doğrulanmadı)**; biçim testinin asıl
sorusu bu.

## 4. `require_parameters` ile etkileşim

- Bugün üç modelin hepsi `provider: {order: [slug], only: [slug], allow_fallbacks: false,
  require_parameters: true}` ile gidiyor (pgg_game.provider_routing).
- OpenRouter dokümanı (https://openrouter.ai/docs/features/provider-routing): `require_parameters`
  false iken `response_format` (yapılandırılmış çıktı dahil) yalnız **yumuşak tercihtir**. Hiçbir
  sağlayıcı desteklemiyorsa istek yine gider ve parametre sessizce **yok sayılır**. true iken
  desteklemeyen sağlayıcıya istek hiç yönlendirilmez. Structured-outputs sayfası da
  `require_parameters: true` öneriyor.
- **A:** `response_format` json_object olarak kalır; yönlendirme bugünkü gibidir.
- **B:** `require_parameters: true` + `only` + `allow_fallbacks: false` birlikteyken, sabitlenmiş uç
  nokta `structured_outputs`'u bırakırsa istek sessizce şemasız gitmez, hata alır. Bu hata `http`
  türüdür, dört denemeye kadar yeniden denenir. Sonra karar çağrısı koşuyu `run_aborted` ile
  durdurur; kural anlama çağrısı `comp_missing` olur. Bu doğru davranış: sessiz yok saymaya göre
  tercih edilir. Bu yüzden B'de `require_parameters: true` **zorunlu** kalmalı. Bugün kodda zaten
  sabit (PROVIDER_POLICY), config'ten kapatılamıyor.
- Şemayı sağlayıcı reddederse (desteklenmeyen anahtar sözcük; ör. min/max) yine `http` hatası olur.
  Bunu biçim testi gösterir.

## 5. Çapalama riski (A) ve azaltma yolları

- **A1'de risk yüksek.** Örnekteki sayı (ör. 10) katkıyı o sayıya çekebilir. Etki karta ve stile
  göre farklı olabilir. Bu durumda yalnız düzey kaymaz, stil etkisi (çalışmanın asıl ölçtüğü şey)
  de karışır.
- **Kural anlamada daha da tehlikeli.** Örnekteki sayı doğru cevabı (28 / −6) sızdırabilir ya da
  cevabı çekebilir. Bu yüzden A1, kural anlamada hiç kullanılmamalı.
- **Geçerlilik ölçüsünü yanıltır.** Örneği aynen kopyalayan bir yanıt geçerli sayılır. Geçersiz
  oranı düşer, ama veri bozulmuş olur ve bu, sayımda görünmez.
- Azaltma yolları:
  1. **Yer tutucu (A2, uygulandı):** yeni sayı yok. Testte, örnekteki her sayının sorunun kendi
     metninde zaten geçtiği denetleniyor (`0` ve `20`). Yeni risk: model yer tutucuyu aynen yazabilir
     (`<whole number …>`). Bu JSON değildir, parse hatası olur ve yeniden istenir. Mistral'ın şemayı
     geri yazmasına benzer bir hata türü, sayılabilir.
  2. **Alan dışı ya da sayısal olmayan örnek:** `"contribution": "<integer>"` gibi. A2'nin bir
     çeşididir.
  3. **Rastgele örnek değeri (stable_seed ile, çağrı başına):** Ortalama çapa koşullardan
     bağımsız olur, ama varyans ekler ve dağılımın ortasına çeker. Satıra örnek değeri yazılmalı.
     Önerilmez.
  4. **Sabit örnek, tüm koşullarda aynı:** Koşul farkları için yansız olabilir ama düzeyi kaydırır.
     Stille etkileşimi ölçülmeden kabul edilmemeli.
  5. **Ölçüm:** A1 düşünülürse, iki farklı sabit örnek değeriyle (ör. 3 ve 17) küçük bir test,
     katkı ortalamalarının farkına bakılarak yapılabilir. A2 / B'de buna gerek yok.

## 6. Çerçeve metinleri ve sha kilitleri

- Cevap talimatı çerçeve dosyasında değil, kodda (llm_client). frames/SCHEMA.md: "the engine then
  appends the response schema (llm_client)". Bu yüzden A da B de `abstract_v3.json`, `story_A.json`,
  `abstract_v2.json` dosyalarına ve config'teki `frame_files` sha256 kilitlerine **dokunmaz**. Çerçeve
  linter'ı da bu metni görmez. sha256'lar bu görevden sonra da aynı:
  abstract_v2 `02f9e84e…6f71`, abstract_v3 `09b4d67b…3e5a`, story_A `d8face90…0d7d`
  (testler değişmedi).
- **Yeni çerçeve sürümü gerekmez.** Ama istemin değiştiği (A) ya da isteğin değiştiği (B) bir
  satırın bunu taşıması gerekir. Bayrak ayarlıyken:
  - `answer_format` config kaydına girer. Başka bir değerle `--resume` çağrı yapmadan durur
    (test edildi).
  - Her satıra ve ham log kaydına yazılır.
  - `prompt_sha256`'ya girer: kabul edilmiş cevap başka biçimle yeniden kullanılmaz.
  - Kod sürümü (`git_commit`) kaydı zaten her segmentte var.
- **Ana deney için öneri (karar değil):** Prensip "modelin gördüğü her metin çerçeve dosyasındadır".
  Talimat da çerçeveye taşınırsa (ör. `response.instruction` şablonu), bu yeni çerçeve sürümleri
  (abstract_v4 / story_A2) ve yeni sha kilitleri demek; çerçeve linter'ı da o metni görür. B1'de
  istem değişmediği için bu gerekmez.
- story_A'nın alan adları (`credits_into_jar`, `reductions`) A2 kalıbında da aynen görünür. B'de
  istemde zaten görünüyorlar. Linter story metnini denetliyor, kod tarafındaki talimatı denetlemiyor.
  Kalıp metninde yeni bir yasak kök yok ("whole number", "your own values"). Bu bir gözlem, linter
  ile çalıştırılmadı **(doğrulanmadı)**.

## 7. Geçerlilik ve degraded sayımına etkisi

| | Bugün (şema metni, json_object) | A2 (yer tutuculu örnek) | B1 (json_schema strict) |
|---|---|---|---|
| `n_invalid` (şemaya uymayan ama parse edilen) | Mistral'da şema geri yazımı burada (28) | Şema metni yok, geri yazılamaz. Beklenen: düşer **(doğrulanmadı)** | Strict uygulanıyorsa ~0. O zaman `n_invalid` modelin talimata uymasını değil, sağlayıcının zorlamasını ölçer. Uygulanmıyorsa bugünkü gibi |
| `n_parse_fail` | 0 | Yer tutucu aynen yazılırsa artar (yeni hata türü) | Kesilen yanıt (`length`) ve OpenAI reddi (`refusal`, boş içerik → parse hatası) kalır |
| aralık dışı değer (0–20) | `is_valid` yakalar, yeniden ister | Aynı | Sağlayıcı min/max uygularsa ~0; uygulamasa `is_valid` yine yakalar |
| degraded (düzyazı içinde JSON; kural anlamada `+3`) | 0 (iki koşuda da) | Aynı kalması beklenir | `+3` gibi yazımlar tip zorlamasıyla ortadan kalkar; degraded ~0 |
| `n_provider_error` / `http` | Mevcut | Aynı | Şemayı reddeden sağlayıcıda artar; 4 denemeden sonra karar çağrısı koşuyu durdurur |
| `invalid_rate_cap` (%5, durdurma kuralı) | Mistral'ı durdurdu | Aynı kural | Aynı kural; B'de pratikte tetiklenmemesi beklenir. E3 (U1–U3: tek değer, kural anlama yanlışı, reasoning_capped) geçersiz oranını kullanmıyor (prereg_minipilot.md §7). Ama U2'nin paydası (geçerli kural anlama satırı) ve `comp_missing` sayısı biçimden etkilenebilir |

Kural anlama (`n_comp_invalid`) için de aynı tablo geçerli. B'de `rationale` zorunlu olduğundan kural
anlama yanıtlarında da gerekçe her zaman olur.

## 8. Pilot v2 ve mini-pilot ile karşılaştırılabilirlik

- **B1:** Mesajlar bayt bayt aynı (test: `answer_format: "json_schema"` ile her isteğin mesajları
  varsayılanınkiyle aynı). Değişen yalnız kod çözme kısıtı. DeepSeek ve GPT mini-pilotta zaten
  ~%0 geçersizle cevap verdiği için, katkı dağılımı karşılaştırılabilir kalmalı **(doğrulanmadı)**.
  Constrained decoding cevap dağılımını değiştirebilir; biçim testinde DeepSeek/GPT'nin katkı
  dağılımı mini-pilotla kaba olarak karşılaştırılmalı (betimsel). Mistral'ın mini-pilot verisi zaten
  eksik (380/600), karşılaştırma yapılamaz.
- **A2:** Her istemin son paragrafı değişir.
  - Mini-pilot ve pilot v2 ile istem düzeyinde aynılık yok.
  - Mini-pilot `--resume` ile A2'ye geçilemez (config farkı durdurur; yeni koşu adı gerekir).
  - Pilot v2 / mini-pilot verisi, ana deneyle ancak "biçim değişti" notuyla birlikte okunabilir.
- **İki seçenekte de:** Ana deneyde üç model aynı biçimi kullanmalı. Aksi halde model farkı biçim
  farkına karışır.
- **Bugünkü hal:** Mini-pilot ve pilot v2'nin biçimi (şema metni + json_object) varsayılan olarak
  korunuyor. O koşular bugünkü kodla aynı isteklerle sürdürülebilir (test: 811fdcc ile istek
  hash'leri aynı).

## 9. Kod (isteğe bağlı kısım, varsayılan kapalı)

- Config / RunConfig anahtarı `answer_format`:
  - yok ya da `"schema_text"`: bugünkü istek;
  - `"example"`: A2;
  - `"json_schema"`: B1.
  - `llm_client.answer_request` isteği kurar. `example_template` ve `strict_json_schema` saf
    fonksiyonlardır.
- Ayarsızken config kaydı, satırlar, ham log kayıtları ve `prompt_sha256` önceki kodunkiyle aynı.
- `tests/test_answer_format.py` (9 test):
  - **811fdcc ile bayt bayt aynılık:** Üç küçük tasarımın bütün istekleri (model, mesajlar,
    `response_format`, `max_tokens`, gövde, başlıklar) 811fdcc koduyla üretilen hash'lerle
    karşılaştırılıyor: `tests/fixtures/request_hashes_811fdcc.json`, 85 istek. Tasarımlar şunlar:
    - abstract_v3 + story_A, kural anlama + fixed_round izole;
    - abstract_v3, P (ceza adımı);
    - abstract_v2 (pilot v2), N + P.
  - açık `"schema_text"` = varsayılan;
  - varsayılanın `prompt_sha256`'sı değişmedi;
  - A2: talimattan önceki her şey aynı, şema metni yok, örnekte sorunun metninde olmayan sayı yok;
  - B1: mesajlar aynı, şema kapalı ve tüm alanlar zorunlu;
  - başka biçimle `--resume` çağrısız durur;
  - geçersiz değer reddedilir.
- Yapılmayanlar: üç modelde gerçek biçim testi (ayrı emir), A1, B2, talimatın çerçeveye taşınması,
  dry-run maliyet tahmininde json_schema'nın istek boyuna etkisi (küçük; tahmin bugünkü gibi).

## 10. Özet karşılaştırma

| Ölçüt | A2 — yer tutuculu örnek | B1 — json_schema strict |
|---|---|---|
| Mistral'ın şema geri yazımı | Şema metni yok; geri yazım olamaz, yer tutucu kopyalama yeni risk | Strict uygulanıyorsa olamaz **(doğrulanmadı)** |
| Üç uç noktada destek (endpoints, 2026-10-09) | Gerek yok (json_object; üçünde var) | `structured_outputs` üçünde var; uygulama derecesi **(doğrulanmadı)** |
| `require_parameters` | Değişmez | true şart (kodda sabit); desteğin düşmesi sessiz değil, hata |
| Çapalama | Yeni sayı yok (test); A1'de yüksek risk | Yok (istem aynı) |
| İstem değişimi | Son paragraf değişir | Yok (bayt bayt aynı) |
| Çerçeve sha kilitleri | Değişmez (talimat kodda) | Değişmez |
| Yeni çerçeve sürümü | Gerekmez; talimat çerçeveye taşınırsa gerekir | Gerekmez |
| Geçersiz / degraded sayımı | Anlamı aynı, yeni bir parse-hata türü | Geçersiz ~0'a iner, anlamı değişir (sağlayıcı zorlaması) |
| Pilot v2 / mini-pilot ile karşılaştırma | İstem düzeyinde yok, not gerekir | İstem aynı; kod çözme kısıtı farkı kalır |
| `rationale` | İsteğe bağlı kalır | Zorunlu olur |
| Biçim testinde bakılacak | Yer tutucu kopyalama oranı, geçersiz oranı, katkı dağılımı | Üç uç noktada şema reddi (http), geçersiz oranı, refusal / boş içerik, katkı dağılımı |
