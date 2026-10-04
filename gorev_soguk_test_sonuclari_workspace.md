# Soğuk test sonuçları (görev #24 + #26 eki)

Not: Bölüm 1–5 #24'ten (gemini-3.8-flash dahil) aynen korunmuştur; kıyas için kalır. Yeni model **Bölüm 6**'dadır.

Tarih: 2026-10-04. Senkron yol (`llm_client.call_llm`), her modele oyundan bağımsız **tek** istek, `response_format=json_object`.
İstem: `Return exactly {"ok": true, "n": 3} as JSON` (+ `call_llm`'in eklediği şema cümlesi).
Toplam 3 çağrı, 3'ü de ilk denemede başarılı (yeniden deneme olmadı). Ham kayıt: `logs/raw_calls.jsonl` (git dışı).

## 1. Kimlik doğrulama (GET /api/v1/models, faturalanmaz)

| model | kimlik | listede | bağlam (token) |
|---|---|---|---|
| deepseek | `deepseek/deepseek-v4.1-flash` | geçerli | 1 048 576 |
| gpt | `openai/gpt-6-luna` | geçerli | 1 050 000 |
| gemini | `google/gemini-3.8-flash` | geçerli | 1 048 576 |

## 2. Ölçümler

| | deepseek | gpt | gemini |
|---|---|---|---|
| JSON geçerli | evet | evet | evet |
| degraded (düzyazı sarma yedeği) | hayır | hayır | hayır |
| parse hatası (n_parse_fail) | 0 | 0 | 0 |
| attempt (0 tabanlı kayıt) | 0 (1. deneme) | 0 (1. deneme) | 0 (1. deneme) |
| model_snapshot (yanıttaki `model`) | `deepseek/deepseek-v4.1-flash` | `openai/gpt-6-luna` | `google/gemini-3.8-flash` |
| finish_reason | **loglanmadı** (aşağıda not) | **loglanmadı** | **loglanmadı** |
| prompt_tokens | 93 | 69 | 64 |
| completion_tokens (reasoning dahil) | 42 | 18 | 78 |
| reasoning_tokens | 29 | 0 | 67 |
| görünür çıktı tokenı (completion − reasoning) | 13 | 18 | 11 |
| maliyet, USD (`usage.cost`) | 0.00003066 | 0.0000159 | 0.0003405 |
| gecikme (sn, `call_llm` süresi, istemci tarafı) | 2.49 | 1.54 | 1.51 |
| max_tokens | 16000 (`DEFAULT_MAX_TOKENS`) | 16000 | 16000 |
| reasoning ayarı | gönderilmedi (sağlayıcı varsayılanı) | gönderilmedi | gönderilmedi |
| temperature | gönderilmedi, log: `"default"` | aynı | aynı |
| ham yanıt | `{"ok": true, "n": 3}` | aynı | aynı |

Maliyet kaynağı: üç modelde de yanıttaki `usage.cost` alanı (`is_byok=false`). Hesaplama için kullanılmadı, ama aşağıdaki fiyatlarla çapraz kontrol edildi.

`usage.completion_tokens` reasoning token'larını **içeriyor** (gemini: 78 × 3.75e-6 = 0.0002925 = `upstream_inference_completions_cost`; deepseek: 42 × 4.2e-7 = 1.764e-5). Reasoning ayrıca ücretlenmiyor, tamamlama fiyatından ücretleniyor. `usage.completion_tokens_details.reasoning_tokens` bunun alt kümesi.

## 3. Fiyatlar (USD / token ve USD / 1M token)

Kaynak: `GET /api/v1/models` (`pricing`), ve sağlayıcı bazlı `GET /api/v1/models/{id}/endpoints`.

| model | prompt | completion | internal_reasoning | not |
|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash | 3e-9 → 0.003 $/M | 2.4e-6 → 2.4 $/M | alan yok | **/models fiyatı gerçeği yansıtmıyor**, aşağıya bak |
| openai/gpt-6-luna | 1e-7 → 0.10 $/M | 5e-7 → 0.50 $/M | alan yok | 272k+ prompt token'da 2e-7 / 7.5e-7. Önbellek okuma 1e-8, yazma 1.25e-7 |
| google/gemini-3.8-flash | 7.5e-7 → 0.75 $/M | 3.75e-6 → 3.75 $/M | 3.75e-6 → 3.75 $/M (= completion) | önbellek okuma 7.5e-8. flex: yarı fiyat, priority: yaklaşık 1.8× |

### DeepSeek fiyat uyarısı (reporter için önemli)

`/models` listesindeki DeepSeek fiyatı, uç noktalar arasındaki **en ucuz** sağlayıcının (Relace) fiyatı. Gerçekte faturalanan fiyat bundan çok farklı:

- Ölçülen: prompt 1.302e-05 / 93 = **1.4e-7 $/token (0.14 $/M)**, completion 1.764e-05 / 42 = **4.2e-7 $/token (0.42 $/M)**.
- Bu, DeepInfra (fp8) uç noktasının liste fiyatıyla birebir aynı. İsteği hangi sağlayıcının karşıladığı yanıtta/logda **tutulmuyor**; bu çıkarım fiyat eşleşmesinden.
- DeepSeek için 31 uç nokta var. Prompt fiyatı 3e-9 ile 4.5e-7 $/token arasında, completion 1.8e-7 ile 2.4e-6 arasında (yaklaşık 13× aralık). Sağlayıcı sabitlenmediği için gerçek maliyet çağrıdan çağrıya değişebilir. Tek bir ölçüme dayanıyor.
- Maliyet analizinde `/models` değerini değil, ölçülen 0.14 / 0.42 $/M'i kullanmak (ve ± bir bant belirtmek) daha doğru olur.

Çapraz kontrol: gpt (6.9e-6 / 69 = 1e-7; 9e-6 / 18 = 5e-7) ve gemini (4.8e-5 / 64 = 7.5e-7; 2.925e-4 / 78 = 3.75e-6) ölçülen maliyetleri liste fiyatlarıyla birebir uyuşuyor.

## 4. Yeni log alanlarının gerçek kayıtta kontrolü

3 başarılı kayıtta (`logs/raw_calls.jsonl`):

- `temperature`: üç kayıtta `"default"` (istekte `temperature` gönderilmedi). Doğru.
- `model_snapshot`: dolu (üçünde de istenen kimlikle aynı; sürüm eki yok). Doğru.
- `degraded`: `false`. Doğru.
- `attempt`: 0.
- `usage`: tam sözlük (cost, cost_details, completion_tokens_details.reasoning_tokens dahil), yani reasoning ve maliyet loglardan okunabiliyor.
- `error_kind`: başarılı kayıtta **yazılmaz**, yalnızca başarısız deneme kayıtlarında. Gerçek API'de hata oluşmadığı için gerçek kayıtta doğrulanamadı. Bu alan mock testlerle doğrulanıyor (#19 testleri geçiyor).

## 5. Bilinen eksikler

- **finish_reason loglanmıyor.** `llm_client._call_llm_counted` başarı kaydına `choices[0].finish_reason` yazmıyor. Bu yüzden tabloda "loglanmadı" yazıyor. Kesilme olmadığı dolaylı olarak görülüyor (JSON eksiksiz ayrıştı, completion_tokens ≪ 16000), ama doğrudan kanıt değil. Eklenirse ek bir test çağrısı gerekir (3 çağrılık sınır doldu).
- **Gecikme logda yok**, yukarıdaki değerler betik içinde ölçüldü. Üç tek çağrı, soğuk/ısınmış ayrımı yok, istatistiksel anlamı yok.
- **Reasoning düzeyi sabitlenmedi.** `call_llm` `reasoning_effort` göndermiyor. Reasoning token'ı çok küçük bir istemde bile deepseek'te 29, gemini'de 67 çıktı. gemini'de görünür çıktının (11 token) yaklaşık 6 katı reasoning. Gerçek oyun istemlerinde bu pay büyük ve değişken olacak.
- **Sağlayıcı sabitlenmedi.** Fiyat ve davranış sağlayıcıya bağlı (özellikle deepseek). Yanıttaki sağlayıcı bilgisi de loglanmıyor.
- Ölçümler tek örnek. Tek bir kısa istem, oyun istemi uzunluğunu temsil etmez.

## 6. Ek (görev #26): google/gemini-2.5-flash-lite soğuk testi

Tarih: 2026-10-04. Kullanıcı kararı: maliyet nedeniyle Google modeli `google/gemini-3.8-flash` yerine `google/gemini-2.5-flash-lite`. `MODELS["gemini"]` buna çevrildi. Senkron yol (`call_llm`), **tek** istek, `response_format=json_object`, 1 çağrı, ilk denemede başarılı (yeniden deneme yok).
İstem #24'tekiyle aynı: `Return exactly {"ok": true, "n": 3} as JSON` (+ `call_llm`'in şema cümlesi). Şema (ok: boolean, n: integer) #24 betiği depoda olmadığı için yeniden kuruldu, #24'ünkiyle birebir aynı olmayabilir. Ham kayıt: `logs/raw_calls.jsonl` (git dışı).

| | gemini-3.8-flash (#24, kıyas) | **gemini-2.5-flash-lite (#26)** |
|---|---|---|
| kimlik geçerli (GET /models) | evet | **evet** (bağlam 1 048 576) |
| JSON geçerli | evet | **evet** |
| degraded | hayır | **hayır** |
| parse hatası (n_parse_fail) | 0 | **0** |
| attempt (0 tabanlı) | 0 | **0** (1. deneme) |
| model_snapshot (yanıttaki `model`) | `google/gemini-3.8-flash` | **`google/gemini-2.5-flash-lite`** (sürüm eki yok) |
| finish_reason | loglanmadı | **`stop`** (artık loglanıyor) |
| prompt_tokens | 64 | **64** |
| completion_tokens (reasoning dahil) | 78 | **11** |
| reasoning_tokens | 67 | **0** |
| görünür çıktı tokenı | 11 | **11** |
| maliyet, USD (`usage.cost`) | 0.0003405 | **0.0000108** |
| gecikme (sn, istemci tarafı) | 1.51 | **2.48** |
| max_tokens | 16000 | 16000 |
| reasoning ayarı | gönderilmedi | gönderilmedi (model bu çağrıda reasoning üretmedi) |
| temperature | gönderilmedi, log `"default"` | aynı |
| ham yanıt | `{"ok": true, "n": 3}` | `{"ok": true, "n": 3}` |

Fiyat (`GET /api/v1/models`, `pricing`): prompt 1e-7 → **0.10 $/M**, completion 4e-7 → **0.40 $/M**, internal_reasoning 4e-7 → 0.40 $/M (= completion), önbellek okuma 1e-8 → 0.01 $/M.
Çapraz kontrol: 64 × 1e-7 = 6.4e-6 (`upstream_inference_prompt_cost`), 11 × 4e-7 = 4.4e-6 (`upstream_inference_completions_cost`), toplam 1.08e-5 = `usage.cost`. Liste fiyatıyla birebir uyuşuyor. `is_byok=false`.

Yorum ve sınırlar:
- Tek örnek, tek kısa istem; gecikme ve token sayıları oyun istemini temsil etmez.
- Bu çağrıda reasoning token'ı 0 (3.8-flash'ta 67 idi). Gerçek oyun istemlerinde de 0 kalacağı bu testten çıkarılamaz.
- `finish_reason: stop`: kesilme yok. Bu, finish_reason'ın gerçek yanıtta loglandığının ilk doğrudan kanıtı.
- Sürüm eki olmayan kimlik; yanıttaki `model` istenenle aynı, gerçek alt sürüm ayırt edilemiyor.
- Anahtar ve hesap kimliği bu dosyaya yazılmadı.
