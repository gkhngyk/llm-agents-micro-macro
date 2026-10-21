# Grup dinamiğini, tek başına sorulan sorular değil, oyun içinde ölçülen kurallar üretir: LLM ajan gruplarında mikrodan makroya

*Üç dil modeliyle tekrarlı bir kamu malı oyununda çöküş tuzakları, devrilme noktaları ve zaman ufku ile grup büyüklüğüne dair önceden belirlenmiş testler*

**Türkçe okuma kopyası.** İngilizce ön baskının (sürüm 1, 2026-10-21; https://doi.org/10.5281/zenodo.23539451) çevirisidir; resmî metin İngilizcedir. Şekiller İngilizce sürümdekilerin aynısıdır, şekil içindeki yazılar İngilizcedir. Sayılar Türkçe yazımla verilmiştir (ondalık virgül; güven aralıklarında noktalı virgül).

Gökhan Geyik (Empler AI)

---

## Özet

Üretken ajan tabanlı modeller (GABM), büyük dil modellerini (LLM) ajan olarak kullanır ve onları çoğu zaman tek başına sorulan sorularla ayarlar ya da doğrular. Bu bireysel (mikro) cevapların bir nüfusun toplu (makro) dinamiğini üretip üretmediği, ajan tabanlı sosyal bilimin mikro–makro sorusudur. Bu soruyu, üç LLM (DeepSeek-V4.1-Flash, Mistral-Large-4, GPT-6-Luna) ile tekrarlı bir kamu malı oyununda (tur başına 20 puan, MPCR 0,4) dört çalışmada (1.200 grup) inceledik; her çalışma veriden önce yazılmış bir planı izledi. Her ajanın tek başına sorulan bir soruya verdiği cevaptan kurulan simülasyon, üç modelde de grup yörüngelerini yanlış tahmin etti. Dört kişilik gruplardaki oyun içi kararlardan öğrenilen, bir tur geriye bakan bir kural (kendi son katkısı, ötekilerin son ortalaması, birinin 0 verip vermediği, kalan tur sayısı) yörüngeleri örneklem dışında yeniden üretti ve önceden dondurulduğunda, ajanların hiç oynamadığı 15 turluk bir oyunu tahmin etti (ortalama hata 20 puan üzerinden −0,06 ile +0,82). Keşifsel analizlerde kural, dört kişilik grupların makro yapısını da üretiyor: emici bir çöküş durumu, yapışkan bir işbirliği, iki uçta toplanan sonlar ve iki modelde tek bir bedavacıda devrilme noktası. Tek başına verilen cevaplar ise bunun yerine ortalamaya çeken bir dinamik öngörüyor. Tahminin ana koşudan önce herkese açık olarak kaydedildiği, önceden kaydedilmiş bir ölçek testinde iki model de büyük gruplarda daha sık çöktü: Mistral'da grupların 0,29'u 4 ajanda, 0,79'u 16 ajanda; GPT'de 0,23'ü 4 ajanda, 0,69'u 32 ajanda (arada tekdüze değil). Her grubun ilk turundan başlatılan dondurulmuş kural, Mistral'daki artışı tahmin etti (gözlenen +0,50'ye karşı +0,47; kaydedilen tahmin +0,40), ama kısmen birbirini götüren hatalar sayesinde; GPT'dekini ise tahmin edemedi (+0,46'ya karşı −0,12; kaydedilen −0,08). Keşifsel analizler iki katkıya işaret ediyor: ajanlar birinin 0 verip vermediğine değil, ötekilerin kaçının ya da ne kadarının 0 verdiğine tepki verdi (dört kişilik gruplarda sayı ile pay aynı şeydir); büyük GPT gruplarında da bedavacılar daha sık 0'da kaldı. Bu bilgiyi kullanan düzeltilmiş bir kural, önceden belirlenmiş bir karar kapısında durduruldu (gereken 0,05'e karşı 0,047 iyileşme); asıl kuralı birkaç grup büyüklüğünden öğrenmek daha çok işe yaradı (keşifsel). Aynı oyunu oynayan insan grupları (230 grup) başka bir rejimdedir: çöküşten çıkılabiliyor ve sonlar yayılıyor. Arka plan değişkeni olarak çeşitlendirilen kimlik tanımları, adını verdikleri şehirler üzerinden değil, ifadeleri üzerinden etki etti (değer cümleleri ve bir modelde bir kurumsal olgu). Üretken ajan tabanlı modeller için ders şudur: mikro kurallar bağlam içinde ve simüle edilecek ölçekte ölçülmeli. Bir LLM ajanının tek başına söylediği, grubunun yaptığını kötü üretir; küçük gruplarda ölçülen bir kural da büyük gruplara taşınmayabilir.

---

## 1. Giriş

Ajan tabanlı sosyal bilim bir makro örüntüyü mikro kurallardan "büyüterek" açıklar: bir makro örüntü ancak belirli mikro kuralları izleyen bir ajan nüfusu onu üretebiliyorsa açıklanmış sayılır ("büyütemediysen açıklamamışsındır"; Epstein, 1999). Üretken ajan tabanlı modeller (GABM), elle yazılmış kuralların yerine bir rol oynamaya yönlendirilmiş dil modellerini koyar. Mikro kurallar artık yazılmaz; ölçülmeleri gerekir. Bunları ölçmenin yaygın yolu, ajana tarif edilen bir durumda ne yapacağını sormaktır. Bu da mikro–makro sorusunu yeni bir biçimde ortaya çıkarır: bir LLM ajanının tek başına söyledikleri, bu tür ajanlardan oluşan bir nüfusun yaptıklarını üretir mi?

İnsanlar için kamu malı oyunu klasik bir cevap verir. Fischbacher, Gächter ve Fehr (2001) *katkı çizelgelerini* (bir kişinin, ötekilerin her olası ortalama katkısına karşılık ne kadar katkı vereceği) topladı ve deneklerinin yaklaşık yarısının koşullu işbirlikçi, yaklaşık üçte birinin bedavacı olduğunu buldu. Fischbacher ve Gächter (2010), bu çizelgelerin beklentilerle birlikte tekrarlı oyunda işbirliğinin düşüşünü açıkladığını gösterdi. Beyan edilen koşullu kurallar bireyi gruba bağlar.

LLM ajanları için kanıtlar karışıktır:
- toplu sonuçlar insanlara benzeyebilir, ama altta yatan karar kuralları benzemez (Ferraz de Arruda ve ark., 2026);
- açık ağırlıklı modellerde insan kamu malı verisiyle uyum ilk tur katkılarında var, son durumlarda yok (Bin Tareaf, 2026);
- tek bir aileden açık modeller (0,5–32 milyar parametre), oyun içinde pek güncellenmeyen durağan "level-k" oyuncular gibi davranır (Teo, 2026);
- personalar açık ödemelerin önüne geçebilir (Manoranjan ve Gaikwad, 2026) ya da görev anlatıları arasında çoğunlukla eylemlere karşılık gelen sözcükler üzerinden taşınır (Wang, Lester ve Srivastava, 2026).

Önceki çalışmamızda, ültimatom oyununda LLM ajanlarının davranışını bir kimlik tanımının adını verdiği kültürün değil, *ifadesinin* belirlediğini bulmuştuk (Geyik, 2026a).

Toplu davranış çoğu zaman eşiklerle yönetilir: bir bireyin harekete geçip geçmemesi kaç kişinin harekete geçtiğine bağlıdır ve birkaç bireydeki küçük farklar bütün bir grubu devirebilir (Granovetter, 1978). Bir mikro kuralın bu tür eşikler, emici durumlar ya da iki tepeli sonlar üretip üretmediği makro dinamiğin bir özelliğidir. Bir kural ortalama yörüngeleri tutturup bu özellikleri yine de yanlış üretebilir. Bu özellikler genellikle mikro kurallardan okunarak değil, simüle edilerek elde edilir; bu da onları Bedau'nun (1997) anlamında "zayıf biçimde ortaya çıkan" (weakly emergent) özellikler yapar.

Dört soru soruyoruz:

1. **Mikrodan makroya.** Her ajanın tek başına sorulan bir soruya verdiği cevaptan simüle edilen bir nüfus gerçek grupları yeniden üretir mi? Üretmiyorsa, oyun içinde öğrenilen bir kural bunu örneklem dışında yapar mı ve önceden dondurulduğunda ajanların hiç oynamadığı bir oyunu tahmin eder mi?
2. **Makro yapı.** Her kural hangi toplu özellikleri üretir (emici durumlar, devrilme noktaları, son durumların dağılımı) ve hangilerini doğru üretir? LLM grupları aynı oyunu oynayan insan gruplarıyla nasıl karşılaştırılır?
3. **Ölçek.** Dört kişilik gruplarda ölçülen bir kural, gruplar 8, 16 ve 32 ajana büyüdükçe toplu sonuçların nasıl değişeceğini tahmin eder mi?
4. **Kimlik (arka plan).** Kimlik tanımları (şehir adları, değer cümleleri, kurumsal olgular) katkıları insanların kültürlerarası sıralaması yönünde değiştirir mi (Herrmann, Thöni ve Gächter, 2008)?

Katkılarımız:
- (i) tek seferlik, tek başına verilen cevaplar üç modelde de grup dinamiğini yanlış tahmin ediyor;
- (ii) Çalışma 1 ve 2'den sonra tasarlanan basit bir bağlam içi kural boşluğu kapatıyor ve önceden dondurulduğunda görülmemiş uzunlukta bir oyunu tahmin ediyor;
- (iii) keşifsel analizlerde bağlam içi kural emici bir çöküş durumu olan bir eşik sistemi üretiyor; tek başına verilen cevaplar bunu kaçırıyor ve bu yapı insan rejiminden farklı;
- (iv) sınanan iki modelde de LLM grupları büyüdükçe daha sık çöktü; dört kişilik gruplardan öğrenilen kural bunu bir model için tahmin etti, ötekisi için edemedi; keşifsel analizler iki katkıya işaret ediyor (ajanlar ötekilerin kaçının ya da ne kadarının 0 verdiğine tepki veriyor; büyük GPT gruplarında bedavacılar 0'da kalıyor);
- (v) kimlik etkileri şehir adlarından değil, tanımların ifadesinden geliyor (değer cümleleri; Mistral'da ayrıca mahkeme süresi olgusu);
- (vi) önceden belirlenmiş testler kendi açıklamalarımızın bir kısmını desteklemedi: "görünen bedavacı" mekanizması üç modelin ikisinde desteklenmedi ve iki modelin ters yönde ölçekleneceği tahmini doğrulanmadı (iki model de aynı yönde ölçeklendi).

Bütün planlar, ekler, kod, veri ve muhakeme metinleri açıktır.

## 2. Yöntem

### 2.1 Oyun ve modeller

Dört homojen ajandan oluşan gruplar (dördü de aynı kimlik kartını alır) doğrusal bir kamu malı oyunu oynar:
- her turda her oyuncu 20 puan alır ve 0 ile 20 arasında bir tam sayı katkı verir;
- katkı verilen her puan her oyuncuya 0,4 puan getirir;
- her turdan sonra oyuncular herkesin katkısını ve kendi kazancını görür;
- ceza yoktur.

Oyundan önce her ajan iki kural anlama sorusunu cevaplar (doğru cevaplar 28 ve −6).

Üç modelin her biri OpenRouter üzerinden tek bir sağlayıcıya sabitlendi:
- `deepseek/deepseek-v4.1-flash` (DeepInfra, fp8);
- `mistralai/mistral-large-4-0` (Mistral);
- `openai/gpt-6-luna` (OpenAI).

Model sürümleri her çağrıda kaydedildi ve çalışmalar boyunca değişmedi. Sıcaklık ve muhakeme düzeyi sağlayıcı varsayılanlarında bırakıldı; `max_tokens` 16.000 idi. Cevaplar, bir katkı ve bir-iki cümlelik gerekçe içeren bir JSON nesnesi olarak istendi; geçersiz cevaplar yeniden istendi ve sayıldı, hiçbir zaman elle kodlanmadı.

### 2.2 Kimlik kartları

On iki kart: dört şehir (Boston, Kopenhag, Atina, Riyad) × üç üslup.
- *Minimal:* "You are a 21-year-old university student living in {city}." ("{Şehir}'de yaşayan 21 yaşında bir üniversite öğrencisisin.")
- *Değer:* minimal + bir değer cümlesi (ör. Boston: "Where you grew up, people prize personal liberty and speaking up against authority." — "Büyüdüğün yerde insanlar kişisel özgürlüğe ve otoriteye karşı sesini yükseltmeye değer verir."; Riyad: "…people strongly respect family elders and tribal leaders." — "…insanlar aile büyüklerine ve kabile liderlerine güçlü bir saygı duyar.").
- *Olgusal:* minimal + "In your country, a lawsuit over an unpaid bill takes about N days" ("Ülkende ödenmemiş bir fatura için açılan dava yaklaşık N gün sürer"; Doing Business 2020'deki sözleşme uygulama süresi, Dünya Bankası, 2019: 444, 485, 1.711, 575).

Sistem mesajı "The following describes you:" ("Aşağıdaki seni tanımlar:") diye başlayıp kartla devam ediyordu (Mistral'da sağlayıcı görünüşe göre bir JSON biçim talimatı ekledi; bkz. Sınırlılıklar). Şehirler, Herrmann ve ark.'ndaki (2008) insan sıralamaları bilinsin diye seçildi (tur 1–10: Kopenhag > Boston > Riyad > Atina).

### 2.3 İki mikro kural

**Beyan edilen tepki (R0).** Ayrı bir kolda, aynı kartı alan ajanlar tek sorular cevapladı: "This is round 5 of 10. In the previous round the other 3 players of your group contributed, on average, X points each" ("10 turun 5.'si. Önceki turda grubundaki öteki 3 oyuncu ortalama X puan katkı verdi"), X ∈ {0, 5, 10, 15, 20}, dört tekrar. Hücrenin ortalama cevapları parçalı doğrusal bir f fonksiyonu tanımlar. R0 modelinde her ajan c_i,t = f(c̄_−i,t−1) katkı verir; c̄_−i ötekilerin önceki ortalamasıdır. Bu, katkı çizelgesinin LLM karşılığıdır ve belirlenimcidir.

**Bağlam içi kural (R3).** Ajanın durumu dört parçadan oluşur:
- kendi önceki katkısı (dilimler 0, 1–9, 10, 11–19, 20);
- ötekilerin önceki ortalaması (0, (0, 5), [5, 10), 10, (10, 15), [15, 20]);
- ötekilerden birinin 0 verip vermediği;
- kalan turlar (≥ 2, sondan bir önceki, son).

Her durumda ajan, eğitim gruplarında o durumda gözlenen gerçek kararlardan birini çeker. Bu, gerçek kararlardaki 0/10/20 kesikliliğini korur. Görülmemiş durumlar daha kaba durumlara ve modelin öteki kartlarına geri çekilir. Grup süreci dört katkı üzerinde bir Markov zinciridir. Orta oyunda (iki ya da daha fazla tur kalmışken) zamanla değişmez; bu da uzun dönem özelliklerini iyi tanımlı kılar. R3, Çalışma 1 ve 2'nin sonuçları bilinirken tasarlandı (Bölüm 4) ve Çalışma 3'ten önce donduruldu (Bölüm 6).

### 2.4 İnsan karşılaştırma verisi

Herrmann, Thöni ve Gächter (2008) aynı oyunu oynattı: sabit üyeli dört kişilik gruplar, 20 jeton, MPCR 0,4 ve 10 dönem. "N deneyi"nde ceza yoktur. N deneyinin önce oynandığı oturumları kullanıyoruz: 16 şehirde 230 grup. Veri herkese açıktır (Herrmann, Thöni ve Gächter, 2017, Dryad). Karşılaştırma için aynı bağlam içi kural sınıfı bu verilere de uyduruldu (örneklem içi).

### 2.5 Makro ölçüler

Ortalama katkısı ≤ 2,5 olan bir grup **çökmüş** (çöküş bölgesinde), ≥ 7,5 olan bir grup **işbirlikçi** sayılır; aradaki değerler *ara* bölgededir. Eşikler planda sabitlendi; son durum paylarına 1/9 eşikleriyle bir duyarlılık kontrolü uygulanır.

Beş özelliği ölçüyoruz:
- Simetrik durumların (hepsi 0, hepsi 10, hepsi 20) **kalıcılığı**: grubun bir sonraki turda aynı durumu tekrarlama olasılığı (p = π⁴; π ajan düzeyindeki olasılık).
- İşbirliğinin **ömrü**: orta oyun kuralı altında hepsi-10 durumundan ilk çöküşe kadar geçen tur sayısı.
- **Devrilme noktası** k*: 1. turdaki bedavacı sayısının (öteki 4 − k ajan 10 verir), grubun 13. turda 0,5 ya da daha yüksek olasılıkla çöküş bölgesinde olduğu en küçük değeri.
- **Geri dönüş**: çökmüş grupların sonradan işbirliğine dönen payı.
- **Son durum dağılımı**: orta oyunun sonunda (10 turluk oyunda 8. tur, 15 turlukta 13. tur) çökmüş / ara / işbirlikçi payları.

Gözlenen değerler, her kuralın aynı gruplar için, gözlenen 1. turlarından başlatılarak yaptığı tahminle karşılaştırılır. Üç etiket kullanılır (bağlam içi kural için; R0 için aralık hesaplanmadı):
- gözlenen − tahmin farkı ±0,15 içinde ve güven aralığı da bandın içindeyse "yeniden üretiyor";
- güven aralığı tamamen bandın dışındaysa "sapıyor";
- diğer durumlarda "belirsiz".

### 2.6 Süreç

Her çalışma için, ücretli ilk çağrıdan önce yazılı bir plan commit edildi. Plan, iki yönü de yazılmış hipotezleri, karar kurallarını ve sentetik veriyle test edilmiş analiz kodunu içeriyordu. Analiz betikleri eksik veride çalışmayı reddeder. Keşifsel analizler de hesaplanmadan önce yazılı olarak planlandı; sapmalar gerekçeleriyle tarihli ekler olarak kaydedildi. Planlar Türkçe yazıldı; bunlar herkese açık bir depodaki iç yazılı planlardır, kamuya açık bir kayıt sistemindeki girdiler değildir; bu yüzden onlara "önceden belirlenmiş" diyoruz. Yalnız Çalışma 4'ün planı ve tahmini ana koşudan önce ayrıca herkese açık olarak kaydedildi; o teste "önceden kaydedilmiş" diyoruz. Planlarda ve arşivde Çalışma 1 ana deneydir, Çalışma 2, 3 ve 4 Deney A, B ve C'dir; durdurulan 64 ajanlık test Deney D'dir.

Bir fark, nokta tahmini 2 puanı aştığında ve grup düzeyindeki bootstrap %95 güven aralığı 0'ı dışladığında "var" sayılır (10.000 yeniden örnekleme). Bir ailede birden çok test varsa model ve hipotez ailesi içinde Holm düzeltmesi uygulanır.

Araştırma, yazarın yönetiminde bir yapay zekâ asistanıyla (Claude) yürütüldü. Her sayı sonuç dosyalarından alındı; temel sayılar bağımsız kodla yeniden hesaplandı. Sayılar kesin değerlerden yarımı yukarı yuvarlandı. Kaynaklar Crossref, DataCite ya da arXiv kayıtlarıyla kontrol edildi (arXiv ön baskıları özetleri düzeyinde).

## 3. Çalışma 1: tek başına verilen cevaplardaki boşluk

**Tasarım.**
- 12 kart × 3 model; DeepSeek ve GPT için hücre başına 16 grup, Mistral için 10 (504 grup, 10 tur).
- 144 izole çizelge.
- Toplam 23.040 cevap; maliyet 45,34 USD.
- Kural anlama soruları DeepSeek'te 816/816, Mistral'da 528/528 ve GPT'de 811/816 ajan tarafından doğru cevaplandı.

### 3.1 Tek başına verilen cevaplardaki boşluk

Her hücre için, her gerçek grubun 1. tur katkılarından başlayarak, her ajanın R0'ı izlediği bir grup simüle ettik. Gerçek gruplar 36 hücrenin 13'ünde bu simülasyonlardan daha az katkı verdi, hiçbirinde daha fazla vermedi (ortalama fark −1,64; −1,53; −2,17 puan; 36 hücrenin 32'sinde negatif).

Tek başına verilen cevaplar "ötekiler ne verdiyse onu ver"e yakındı: GPT'nin ortalama cevabı, 12 hücresinin 10'unda her noktada X'e eşitti. Keşifsel bir analizde, son iki tur çıkarıldığında boşluk DeepSeek ve Mistral'da sürdü (tur 2–8: altta kalan hücre sayısı 3 ve 5; GPT'de 0).

### 3.2 Kimlik ve etkileşim (özet; ayrıntılar Ek S1–S2'de)

Kimlik tanımları Çalışma 1'in manipüle edilen arka planıydı. Şehir adları tek başına fark edilebilir bir etki yapmadı: minimal kartlarda hiçbir modelde hiçbir şehir çifti farklılaşmadı (en büyük |fark| 1,02; 1,54 ve 2,22 puan). Değer cümleleri katkıları 14,45 puana kadar değiştirdi; bu değişim şehirlerin insan sıralaması yönünde değil, cümlelerin ifadesi yönündeydi (Tablo 1). DeepSeek ve Mistral'da Boston değer kartı ("kişisel özgürlük ve otoriteye karşı ses yükseltme") sıfıra yakın katkılar (0,15 ve 0,20), Riyad değer kartı ("aile büyüklerine ve kabile liderlerine saygı") bütün kartların en yüksek katkılarını (13,06 ve 14,65) üretti; bu, insan sıralamasının tersidir. Mahkeme süresi olgusu yalnız Mistral'da etkili oldu (Atina 1,59; öteki olgusal kartlar 5,51–7,81). DeepSeek ve Mistral kartı sıklıkla deneycinin bir ipucu olarak okudu. Önceden belirlenmiş 36 etkileşim testinde farkların 4'ü oyun içinde büyüdü, 10'u azaldı, 22'si korundu; GPT'deki büyüme tamamen son turdan geldi.

**Tablo 1.** On tur boyunca ortalama katkı (20 üzerinden), değer ve minimal kartlar.

| | Boston | Kopenhag | Atina | Riyad |
|---|---:|---:|---:|---:|
| DeepSeek, minimal | 0,61 | 1,63 | 1,47 | 1,45 |
| DeepSeek, değer | 0,15 | 9,26 | 1,94 | 13,06 |
| Mistral, minimal | 6,03 | 7,56 | 6,76 | 7,29 |
| Mistral, değer | 0,20 | 10,11 | 10,42 | 14,65 |
| GPT, minimal | 7,81 | 8,17 | 7,90 | 5,96 |
| GPT, değer | 8,91 | 11,28 | 9,08 | 9,25 |
| İnsanlar, N deneyi, dönem 1–10 (Herrmann ve ark.) | 9,33 | 11,53 | 6,36 | 7,63 |

## 4. Mikro kuralı oyun içinde öğrenmek (keşifsel)

Bu analizler keşifseldir; her biri hesaplanmadan önce yazıya geçirildi. Aşağıdaki iki düzenlilik Çalışma 1'den sonra fark edildi ve Çalışma 2'ye yol açtı; R1–R3 kuralları ise Çalışma 2'nin sonuçları da bilinirken tasarlandı.

İki düzenlilik öne çıktı:
1. **Katkılar odak değerlerde toplandı.** 20.160 bireysel kararın %96,0'ı tam olarak 0, 10 ya da 20 idi.
2. **Görünen bir sıfır katkıyı bırakma izledi.** 2–9. turlarda, ajanın önceki turda kendisinin ≥ 10 verdiği ve ötekilerin ortalamasının ≥ 5 olduğu kararlara baktık. Ötekilerden biri 0 verdiğinde ajan vakaların %65'inde (DeepSeek), %61'inde (Mistral) ve %15'inde (GPT) 0 verdi; kimse 0 vermediğinde bu oranlar %2, %3 ve %0 idi.

İzole soru yalnız bir ortalama gösterdiği için R0 bunu temsil edemez. Bu yüzden grup verisinden giderek zenginleşen kurallar öğrendik:
- R1: kendi ve ötekilerin önceki katkıları;
- R2: R1 + ötekilerden birinin 0 verip vermediği;
- R3: R2 + kalan turlar.

Kuralları Çalışma 1'de birer grubu dışarıda bırakan çapraz doğrulamayla ve yeniden öğrenmeden Çalışma 2'nin bağımsız B kolu gruplarında değerlendirdik (aynı istem, üç gün sonra başlayan yeni bir koşu; kurallar bu gruplara uydurulmadı, ama toplu sonuçları kurallar tasarlanırken biliniyordu; Tablo 2).

**Tablo 2.** Yörünge RMSE'si (puan), tek başına verilen cevap (R0) ile oyun içinde öğrenilen kurallar.

| | R0 beyan | R1 kendi + ötekiler | R2 + sıfır | R3 + kalan tur |
|---|---:|---:|---:|---:|
| DeepSeek, Çalışma 1 (çapraz doğrulama) | 2,01 | 0,76 | 0,66 | **0,41** |
| Mistral, Çalışma 1 | 3,76 | 2,05 | 2,03 | **0,58** |
| GPT, Çalışma 1 | 3,04 | 1,83 | 1,81 | **0,44** |
| DeepSeek, yeni koşu | 2,10 | 0,42 | 0,40 | **0,41** |
| Mistral, yeni koşu | 4,34 | 3,14 | 3,17 | **0,76** |
| GPT, yeni koşu | 2,83 | 2,16 | 2,00 | **0,67** |

Kalın değerler, makalenin geri kalanında kullanılan kural R3'ü gösterir; DeepSeek'in yeni koşusunda R2 çok az daha düşüktü.

R3, Çalışma 1'in 36 hücresinin ve yeni koşunun 12 hücresinin hepsinde gerçek gruplarla uyumluydu (hiçbir hücre üstte ya da altta değil). Eksik olan parça modele göre değişiyordu:
- DeepSeek'te oyun içi davranışın kendisi: R1 zaten yetiyordu; oyunda DeepSeek, beyan ettiği "ötekilere uy" kuralından çok daha az işbirlikçi;
- Mistral ve GPT'de ufuk: kalan tur bilgisi olmadan simülasyonlar gerçek grupların altında kaldı (gözlenen − simüle edilen ortalama fark R1 ile Mistral'da +1,58, GPT'de +0,61).

## 5. Çalışma 2: bedavacıyı görmek çöküşe mi yol açıyor?

Bölüm 4'teki sayım bir mekanizma düşündürdü; bunu önceden belirlenmiş bir geri bildirim manipülasyonuyla sınadık:
- B kolu her oyuncunun katkısını gösterdi (Çalışma 1'in istemi);
- T kolu yalnız ajanın kendi katkısını ve ötekilerin ortalamasını gösterdi.

Dört minimal kart; hücre başına 12, 8 ve 12 grup (256 grup); 23,81 USD. B kolu, Çalışma 1'in minimal hücrelerini 12 hücrenin 11'inde yeniden üretti (|fark| ≤ 2).

**Birincil hipotez: hiçbir modelde desteklenmedi.** Hipotez, görünürlüğün çöküşü hızlandıracağıydı (tur 2–9, T − B > 2). Sonuçlar:
- DeepSeek +0,43 [−0,21; +0,98], farksızlıkla eşdeğer;
- Mistral −1,65 [−3,12; −0,14];
- GPT −1,98 [−3,55; −0,42].

Son ikisi ters yönü gösteriyor ama 2 puanlık eşiğin altında kalıyor.

**Mekanizma testi: yalnız DeepSeek'te desteklendi.** Test, iki kolda da aynı gerçek durumda, bir sıfır katkıdan sonra 0 verme payını karşılaştırdı:
- DeepSeek: sıfırlar görünürken 0,88, görünmezken 0,58 (−0,31 [−0,53; −0,08]);
- Mistral 0,60'a karşı 0,56, fark yok;
- GPT 0,13'e karşı 0,04, fark yok.

Bireysel bilgi olmadan Mistral grupları daha hızlı düştü; bu, ajanların düşen ortalamaya tepki vermesiyle tutarlı. GPT'nin kolları daha 1. turda, hiçbir geri bildirimden önce farklıydı (−1,77 [−3,13; −0,42]): tek bir kural cümlesinin yeniden ifade edilmesi açılış katkısını düşürdü; dolayısıyla GPT'deki T − B farkı çoğunlukla görünürlüğü değil istemi yansıtıyor.

## 6. Çalışma 3: kuralın hiç görmediği bir oyunu tahmin etmek

Öğrenilen kuralı ileriye dönük sınamak için R3'ü dondurduk (tablolar yalnız Çalışma 1'den öğrenildi; dosyanın özeti planda) ve hiçbir çağrıdan önce 15 turluk bir oyun için tahminini hesapladık. İstem Çalışma 1'den yalnız tur sayısında farklıydı. Rakip bir varyant olan R3-mutlak, turları eğitimdeki gibi mutlak numaralarına göre eşler (9. ve 10. turlar oyun sonu) ve bu yüzden erken bir çöküş öngörür. Sekiz kart (minimal ve değer), hücre başına 8, 6 ve 8 grup (176 grup); faturalanan 23,08 USD.

**Önceden belirlenmiş sonuçlar.** Her grubu gözlenen 1. turundan başlatan dondurulmuş kural, 2–15. turları üç modelde de eşdeğerlik bandı içinde tahmin etti (Tablo 3, Şekil 1); 24 hücrenin 23'ü uyumluydu. 9–13. turlarda mutlak tur varyantı Mistral'da +4,38, GPT'de +6,87 puan yanıldı: gerçek gruplar erken çökmedi. Yani Mistral ve GPT "açıklanan ufku izliyor". DeepSeek'te aynı hata daha küçüktü (+1,49 [+0,82; +2,18]) ve test ayırt edici olmadı.

**Tablo 3.** Çalışma 3: gözlenen eksi tahmin (tur 2–15) ve yörünge RMSE'si.

| | gözlenen − tahmin, tur 2–15 [%95 GA] | etiket | RMSE R3 | R3-mutlak | R1 | R0 beyan |
|---|---|---|---:|---:|---:|---:|
| DeepSeek | −0,06 [−0,60; +0,48] | tuttu (sıkı) | **0,37** | 1,35 | 0,81 | 1,83 |
| Mistral | +0,82 [+0,17; +1,52] | tuttu | **0,89** | 3,13 | 2,82 | 2,29 |
| GPT | +0,67 [−0,17; +1,46] | tuttu | **0,77** | 5,29 | 2,92 | 2,36 |

Koşudan önce yazılan koşulsuz tahminin (1. tur Çalışma 1'den çekildi) RMSE'si 0,53, 0,45 ve 2,19 idi. GPT'nin daha büyük hatası 1. turdan geliyor: uzun oyunda GPT, Çalışma 1'dekinden daha yüksek açtı (12,1; tahmin 9,8).

![Şekil 1](fig/fig1_study3_forecast.png)

**Şekil 1.** Çalışma 3. Tur başına ortalama katkı (sekiz kartın ortalaması) ve dört tahmin:
- her grubun gözlenen 1. turundan başlatılan dondurulmuş kural (kalan turlar);
- aynı kural, mutlak tur numaralarıyla;
- tek başına verilen cevap (R0);
- koşudan önce yazılan koşulsuz tahmin.

## 7. Makro yapı: tuzaklar, devrilme noktaları ve son durumlar (keşifsel)

Bölüm 4 ve 6, R3'ün ortalama yörüngeleri yeniden ürettiğini gösteriyor. Burada grupların makro yapısını da üretip üretmediğini ve R0'ın bunun yerine ne öngördüğünü soruyoruz. Plan (`prereg/prereg_dyn.md`), okuma kuralları dahil, bütün önceki sonuçlar biliniyorken ama bu bölümdeki hiçbir nicelik hesaplanmadan önce yazıldı ve commit edildi. Raporlamadan önce bir sapma kaydedildi: bedavacı sınıflarında karta göre tabakalı bootstrap sıfır genişlikte aralıklar verdi ve tabakasız bootstrap ile değiştirildi; bu aralıkları genişletti. Her yerde dondurulmuş R3 tablolarını kullanıyoruz. Çalışma 1 üzerindeki karşılaştırmalar R3 için örneklem içidir; Çalışma 2 (B kolu) ve Çalışma 3 örneklem dışıdır.

**Tablo 4.** Makro yapı. Kural özellikleri (model düzeyindeki kural, orta oyun) ve gözlenen örneklem dışı değerler.

| | DeepSeek | Mistral | GPT | İnsanlar |
|---|---:|---:|---:|---:|
| Hepsi-0 kendini tekrarlar, tur başına (kural) | 0,95 | 0,92 | 1,00 | 0,32 |
| Hepsi-10 kendini tekrarlar, tur başına (kural) | 0,96 | 0,95 | 1,00 | 0,00 ᵃ |
| Hepsi-10'dan çöküşe tur sayısı, medyan (kural) | 25 | 15 | > 100 ᵇ | 13 |
| 13. turda çöküş bölgesinde, bedavacı yok (kural) | 0,28 | 0,42 | 0,00 | 0,19 |
| 13. turda çöküş bölgesinde, bir bedavacı (kural) | 0,96 | 0,98 | 0,04 | 0,23 |
| Devrilme noktası k* (kural) | 1 | 1 | 3 ᶜ | yok |
| İşbirliğine dönen çökmüş gruplar (gözlenen, Çalışma 2 / Çalışma 3) | 0,02 / 0,06 | 0,00 / 0,00 | 0,08 / 0,00 | 0,19 |
| Ara bölgede biten gruplar (gözlenen, Çalışma 2 / Çalışma 3) | 0,02 / 0,02 | 0,00 / 0,02 | 0,02 / 0,03 | 0,30 |

Notlar:
- İnsan sütunu: aynı kural sınıfı insan gruplarından öğrenildi (örneklem içi); gözlenen değerler insan gruplarının 8. döneminden. Kural satırları insan kuralını 10 dönemlik oyunun ötesine, 13. tura kadar çalıştırır; 8. dönemde iki çöküş payı 0,15 ve 0,22'dir.
- ᵃ Hepsi-10 durumu insan verisinde neredeyse hiç yok (1 geçiş).
- ᵇ Simüle edilen grupların %99'u 100 turdan sonra hâlâ çökmemişti.
- ᶜ Sınır durumu: üç bedavacıyla başlangıç (0, 0, 0, 10) ortalaması 2,5'tir ve zaten çökmüş sayılır.
- Geri dönüş paylarının arkasındaki çökmüş grup sayıları: 47 / 50, 10 / 15 ve 13 / 5 (Çalışma 2 / Çalışma 3; DeepSeek / Mistral / GPT); insanlarda 59.

### 7.1 Çöküş bir tuzak; işbirliği yapışkan

Üç modelde de hepsi-0 durumu emici olmaya yakın. Kural altında tur başına 0,92–1,00 olasılıkla kendini tekrarlıyor. Gözlenen LLM gruplarında tur başına kalıcılık her veri kümesinde 0,93–1,00 idi ve çökmüş grupların neredeyse hiçbiri geri dönmedi (Tablo 4). İşbirliği de yapışkan: hepsi-10 durumu 0,95–1,00 olasılıkla kendini tekrarlıyor ve orta oyun kuralı altında işbirlikçi bir grup medyan olarak 25 (DeepSeek) ve 15 (Mistral) tur, GPT'de ise 100 turdan fazla yaşıyor.

Kural, orta oyunun sonunda henüz çökmemiş grupların payını Çalışma 2 ve Çalışma 3'te DeepSeek ve GPT için yeniden üretti (Şekil 2 Çalışma 3'ü gösterir). Mistral'da karşılaştırma iki çalışmada da belirsizdi: Çalışma 2'de fark +0,08 [−0,06; +0,20] idi; 15 turluk oyunda ise işbirliği kuralın öngördüğünden uzun sürdü: grupların 0,69'u 13. tura kadar çökmemişti, tahmin 0,56 idi (fark +0,12 [+0,04; +0,21], belirsiz).

![Şekil 2](fig/fig2_survival.png)

**Şekil 2.** Orta oyun boyunca henüz çökmemiş grupların payı (grup ortalaması > 2,5): gözlenen ile aynı grupların 1. turundan başlayan tahminler; bağlam içi kural ve LLM panellerinde ayrıca tek başına verilen cevap (R0). LLM panelleri: Çalışma 3, örneklem dışı; insan paneli: aynı veriden öğrenilen kural.

### 7.2 Tek bir bedavacı grubu deviriyor (DeepSeek, Mistral), GPT'de değil

k ajan 0 ve öteki 4 − k ajan 10 ile başlayınca kural, çoğunlukla ayakta kalan bir grubu k = 1'de çökmüş bir gruba çeviriyor: DeepSeek'te 13. turda çöküş bölgesinde olma 0,28'den 0,96'ya, Mistral'da 0,42'den 0,98'e çıkıyor. Burada başlangıç (0, 10, 10, 10) ortalaması 7,5'tir; yani devrilme oyun sırasında oluyor. GPT'de eğri kademeli: bir bedavacıyla 0,04, ikiyle 0,30. GPT'nin k* = 3 değeri bir sınır durumudur, çünkü üç sıfırla başlayan bir grup zaten çökmüş sayılır (0,81'i çökmüş kalıyor). Hücre bazında k*, DeepSeek'in 12 hücresinin 8'inde ve Mistral'ın 12 hücresinin 6'sında 1, GPT'nin 12 hücresinin 11'inde 2–3 idi.

Çalışma 3'ün gerçek grupları (örneklem dışı) bu örüntüyü gösteriyor, ama bedavacı sınıfları küçük (Şekil 3). En az beş gruplu dokuz sınıftan dördü ±0,15 kuralımızla "yeniden üretiyor" (DeepSeek'te 2–4 sıfır, GPT'de sıfırsız), beşi "belirsiz", hiçbiri "sapıyor" değildi. 1. turunda bir sıfır olan DeepSeek gruplarında (17 grup) 13. turda çöküş bölgesindeki pay gözlenen 0,94, bağlam içi kuralda 0,84, R0'da 0,47 idi; 1. turunda iki sıfır olan GPT gruplarında (11 grup) 0,09, 0,38 ve 0,00.

- Mistral'ın Çalışma 3'te k1 = 1 olan yalnız 4 grubu vardı. Çalışma 1 ve 2'de k1 = 1 olan bütün Mistral grupları 8. turda çöküş bölgesindeydi (9 ve 5 grup); R0'ın tahminleri 0,56 ve 0,40 idi.
- Çalışma 3'te GPT'nin k1 = 2 gruplarında R0 (0,00), gözlenen 0,09'a kuraldan (0,38) daha yakındı. Çalışma 1'de aynı sınıfta gözlenen 0,44, kural 0,29, R0 0,00 idi.

![Şekil 3](fig/fig3_tipping.png)

**Şekil 3.** Devrilme noktası: 13. turda (LLM'ler, Çalışma 3) ya da 8. dönemde (insanlar) çöküş bölgesindeki grupların payı.
- Çizgiler: idealleştirilmiş bir başlangıçtan (k ajan 0, ötekiler 10) model düzeyindeki bağlam içi kural; insanlarda insan gruplarından havuzlanmış kural.
- İşaretler: 1. turdaki sıfır sayısına göre gruplanmış gerçek gruplar (en az 5 gruplu sınıflar). Gözlenen payı %95 güven aralığıyla ve aynı gruplar için hücre düzeyindeki bağlam içi kuralın (insanlarda havuzlanmış insan kuralı) ve tek başına verilen cevabın ortalama tahminini gösterirler (insanlar için tek başına verilen cevap yok).

### 7.3 İki uçlu sonlar ve yol bağımlılığı

LLM grupları orta oyunu uçlardan birinde bitirdi (Şekil 4). Çalışma 1'de 8. turda ara bölgedeki grupların payı:
- gözlenen: %1 (DeepSeek), %1 (Mistral) ve %4 (GPT);
- aynı gruplar için kural: %2, %2 ve %5;
- R0: %16, %2 ve %19.

Örneklem dışında kural, DeepSeek ve GPT için Çalışma 2 ve 3'teki üç son durum payının hepsini yeniden üretti (12 karşılaştırmanın 12'si). Mistral'da ara bölge payını yeniden üretti ama çöküşü fazla öngördü (Çalışma 3: tahmin 0,43, gözlenen 0,29; belirsiz). Daha sıkı 1/9 eşikleriyle bütün etiketler aynı kaldı; ara bölge payı LLM gruplarında %2–9'a, insanlarda %53'e çıktı.

"İki çekici" için önceden yazdığımız okuma kuralının üç parçası vardı: iki simetrik durumun da kural altında yapışkan olması, grupların %20'den azının ara bölgede bitmesi ve her uçta en az %10 bulunması; hem Çalışma 2'de hem Çalışma 3'te. Yalnız Mistral bu kuralı karşıladı. DeepSeek, Çalışma 2'de gruplarının yalnız %2'si işbirlikçi bittiği için karşılamadı (çoğunun 1. turunda bir sıfır vardı). GPT, Çalışma 3'te yalnız %8'i çöktüğü için karşılamadı. Kural üç modelde de iki uçlu; grupların hangi uçta bittiği büyük ölçüde nasıl başladıklarına bağlı.

Çalışma 1'in 12 hücresinin 3'ünde (DeepSeek), 7'sinde (Mistral) ve 8'inde (GPT) iki uç aynı hücrede birlikte görüldü. Aynı başlangıçlar farklı sonlara gitti: dört ajanın da 10 ile açtığı 65 Mistral grubundan %22'si 8. turda çöküş bölgesindeydi, %77'si işbirlikçiydi (kural: %28). Kural altında sonun başlangıçta belirsiz olduğu (çöküş olasılığı 0,2 ile 0,8 arasında) gruplar Mistral'da %35–59, GPT'de %14–22, DeepSeek'te %2–9 idi.

![Şekil 4](fig/fig4_endstates.png)

**Şekil 4.** 8. turda grup ortalama katkısı. LLM grupları: Çalışma 1, bütün kartlar. İnsanlar: Herrmann ve ark.'nın (2008) N deneyi, önce oynandığı oturumlar.

### 7.4 Tek başına verilen cevaplar bunun yerine ne öngörüyor

Tek başına verilen cevap haritası R0, "ötekilerin ortalamasına uy"a yakın. 12 hücrenin 12'sinde (DeepSeek), 5'inde (Mistral) ve 12'sinde (GPT) f(x) = x olan bir bölümü var. Hiçbir hücrede birbirinden ayrı iki kararlı durumu yok. Böyle bir harita ortalamaya çeker: karışık gruplar ara bir düzeye yakınsar ve tek bir bedavacı grubu bir eşiği aşacak kadar değil, orantılı olarak aşağı çeker. Bu yüzden R0, DeepSeek ve GPT için gözlenenden fazla ara son (%11–23'e karşı %1–4) ve tek bir bedavacıdan sonra çok az çöküş öngörüyor (DeepSeek, Çalışma 1: gözlenen 0,82'ye karşı 0,36). GPT'de R0, hiçbir hücrede bir ya da iki bedavacılı grubun çökmesine izin vermiyor; Çalışma 1'de 1. turunda iki sıfır olan GPT gruplarının 0,44'ü çöktü.

Önceden yazdığımız okuma kuralına göre (model düzeyindeki haritanın kararlı durum sayısı ve devrilme noktası) R0 üç modelde de makro yapıyı yanlış öngörüyor. Bu kural kaba. Mistral'da devrilme noktası kısmı bir sınır durumuna dayanıyor: model düzeyindeki harita 13. turda 2,497 grup ortalamasına iniyor, 2,5 eşiğinin hemen altına. Sonuç bu olmadan da geçerli, çünkü model düzeyindeki haritanın bir kararlı durumu var, kuralın ise iki yapışkan durumu.

Mistral'da tablo karışık. Tek başına verdiği cevaplar Çalışma 3'ün sonunda henüz çökmemiş grupların payına yaklaştı (gözlenen 0,69'a karşı 0,71; R0 için aralık hesaplanmadı). Çalışma 2 ve 3'te çöküş ve işbirliği paylarına da R3'ten daha yakındı (Çalışma 3 çöküş: R0 0,29, gözlenen 0,29, R3 0,43). R3 ara bölge payında daha yakındı. Tek başına verilen cevaplar, tek bir bedavacıya verilen tepkiyi ve işbirliği düzeyini kaçırdı (Tablo 3).

### 7.5 İnsan grupları başka bir rejimde

Aynı oyunda insan grupları her ölçüde farklı davranıyor:
- çöküş bir tuzak değil: hepsi-0 olan bir insan grubu gözlenen 22 geçişin 9'unda kendini tekrarladı (0,41) ve çökmüş insan gruplarının %61'i sonradan çöküş bölgesinden çıktı (%19'u işbirliğine ulaştı);
- son durumlar yayılıyor: grupların %30'u ara bölgede bitti (Şekil 4);
- 1. turdaki bedavacılar sonucu kademeli olarak düşürdü: 1. turda 0, 1 ve 2 sıfır olan grupların %11'i, %40'ı ve %63'ü 8. dönemde çöküş bölgesindeydi.

İnsan verisine uydurulan aynı tek-tur bellekli kural sınıfı hayatta kalma eğrisini ve son durum paylarını ±0,15 içinde tuttu (örneklem içi; betimsel, insanlar için önceden etiket belirlenmedi), ama bedavacı eğimini üretemedi: bir ve iki sıfır için 0,23 ve 0,25 öngördü, gözlenen 0,40 ve 0,63 idi. Sınamadığımız olası bir neden, kişiler arasındaki kalıcı farklardır, örneğin bedavacı tipleri (Fischbacher ve ark., 2001'de deneklerin yaklaşık üçte biri). Kişiler üzerinden havuzlanmış ve bir tur hatırlayan bir kural bu bilgiyi taşıyamaz. LLM grupları özdeş ajanlardan oluşuyor ve onlar için havuzlanmış tek-tur bellekli kural yetti.

## 8. Çalışma 4: gruplar büyüdükçe ne oluyor? (ileriye dönük)

Buraya kadarki bütün sonuçlar dört kişilik gruplarla ilgili. Bir karmaşıklık bilimi okurunun ilk itirazı, dört ajanın büyük bir sistem olmadığıdır. Bağlam içi kural büyüklükten bağımsız özelliklerle tanımlı (kendi önceki katkı, ötekilerin ortalaması, ötekilerden birinin 0 verip vermediği, kalan turlar); bu yüzden yeniden öğrenmeden her grup büyüklüğü n için bir tahmin üretir. Bir özellik büyüklüğe duyarlı: n − 1 öteki varken en az birinin 0 verme şansı n ile artar. Bu yüzden dondurulmuş kurala, hiçbir veriden önce, sonuçların 4'ten 8, 16 ve 32 ajana nasıl değişeceğini sorduk.

**Tasarım** (plan `prereg/prereg_expC.md`, ücretli ilk çağrıdan önce onaylandı ve commit edildi).
- GPT için 4, 8, 16 ve 32 kişilik gruplar (her büyüklükte 48 grup); Mistral için 4, 8 ve 16 kişilik gruplar (her büyüklükte 24 grup).
- Dört minimal kart ve 10 tur. Dört kişilik gruplar eşzamanlı kontroldür.
- İstem, oyuncu sayısı dışında Çalışma 1'inkiyle aynı. Kural anlama sorusundaki örnek öteki oyuncuları listelediği için n ile uzuyor.
- DeepSeek alınmadı: minimal kartlarla grupları n = 4'te bile neredeyse her zaman çöküyor; bir büyüklük etkisi görülemezdi.

**Dondurulmuş tahmin** (`data/expC/forecast_v1.json`, sha256 `00d88e05…be9df`; Tablo 5). Plan ve tahmin, ana koşudan önce herkese açık olarak kaydedildi (Geyik, 2026b). Oyun içi kural iki modelin ters yönde ölçekleneceğini öngörüyor:
- Mistral grupları büyüdükçe daha sık çöküş bölgesinde bitiyor (8. turda 0,37 → 0,57 → 0,77);
- GPT gruplarında öyle değil (0,23 → 0,19 → 0,16 → 0,15).

Tek başına verilen cevaplar (R0), dondurulmuş tahminde Mistral için büyüklük etkisi öngörmüyor (0,30 → 0,31). Farklı büyüklükte insan gruplarını sınamadık.

**Tablo 5.** Dondurulmuş tahmin: 8. turda çöküş bölgesindeki grupların payı (dört minimal kartın ortalaması).

| model | kural | n = 4 | n = 8 | n = 16 | n = 32 |
|---|---|---:|---:|---:|---:|
| Mistral | oyun içi kural (R3) | 0,373 | 0,570 | 0,772 | — |
| Mistral | tek başına cevap (R0) | 0,297 | 0,298 | 0,311 | — |
| GPT | oyun içi kural (R3) | 0,228 | 0,188 | 0,158 | 0,146 |
| GPT | tek başına cevap (R0) | 0,063 | 0,013 | 0,000 | 0,000 |

**Önceden kaydedilmiş testler.**
- **C-H1, büyüklük etkisinin yönü (birincil):** 8. turda çökmüş pay, en büyük n eksi n = 4. Etiketler: "artış", "azalış", "değişim yok" (güven aralığı ±0,10 içinde) ya da "belirsiz". "Ters yönlü ölçek doğrulandı" ancak Mistral'da artış olur ve GPT'de olmazsa yazılır.
- **C-H2, aktarım (birincil):** dondurulmuş kuralın her büyüklükte, her grubun gözlenen 1. turundan başlayarak yaptığı ortalama katkı tahmini; Çalışma 3'ün eşdeğerlik bandıyla.
- **C-H3, makro aktarım (ikincil):** her büyüklükte çökmüş pay, ±0,15 bandı.
- **C-H4, eğri (betimsel):** sonuç ile log₂ n ilişkisi.
- **Mekanizma:** görünen bir sıfırdan sonra 0'a geçme payı, büyüklüğe göre. Sıfır tetikleyicisinin kalabalıkta ("31 kişiden biri") sürüp sürmediğini ya da sönüp sönmediğini ölçer.

**Sonuçlar** (`results/expC_main_20261020_analysis.json`; 264 grup, 56,67 USD; Şekil 5). Bütün koşular tamamlandı; geçersiz cevap yok (ayrıştırılamayan 4 GPT cevabı yeniden istendi); model sürümleri öncekiyle aynı.

- **İki model de büyük gruplarda daha sık çöktü (iki modelde de C-H1 "artış"; arada tekdüze değil).**
  - Mistral: 8. turda çöküş bölgesindeki grupların payı n = 4'te 0,29, 8'de 0,21, 16'da 0,79; 16 − 4 = +0,50 [+0,29; +0,71].
  - GPT: n = 4, 8, 16 ve 32'de 0,23; 0,56; 0,48 ve 0,69; 32 − 4 = +0,46 [+0,29; +0,63].
  - Çalışma 1–2'nin tarihsel dört kişilik gruplarıyla karşılaştırınca da etiketler aynıydı.
- **Mistral: tahmin yön ve büyüklükte tuttu (kısmen birbirini götüren hatalar sayesinde; aşağıya bakınız).** Kural, grupların gözlenen 1. turundan +0,47 öngördü (dondurulmuş tahminde +0,40); bu değer güven aralığının içinde. Aynı ilk turlardan başlatılan tek başına verilen cevaplar +0,17 öngördü. Grup büyüklüğünün her ikiye katlanışında çöküş payı +0,25 [+0,15; +0,35] arttı, kural +0,23 öngördü. İstisna sekiz kişilik gruplardı: tahminden daha işbirlikçiydiler (ortalama katkı kuralın 2,31 puan üstünde; çöküş payı 0,61 tahmine karşı 0,21).
- **GPT: tahmin tutmadı.** Kural hafif bir azalış öngördü (−0,12). Gerçek gruplar dörtten büyük her büyüklükte tahminden daha az katkı verdi (8, 16 ve 32'de −2,10; −1,43 ve −2,01 puan; ortadaki "belirsiz") ve daha sık çöktü (+0,34; +0,35 ve +0,52). Grup büyüklüğünün her ikiye katlanışında çöküş payı +0,13 [+0,07; +0,18] arttı; kural −0,05 öngörmüştü.
- **Bu yüzden "ters yönlü ölçek doğrulandı" yazılmadı:** iki model de aynı yönde ölçeklendi.
- Eşzamanlı kontrol olan n = 4'te kuralın ortalama katkı tahmini iki modelde de tuttu (C-H2); çöküş payı karşılaştırması belirsizdi (C-H3: −0,09 ve −0,06).
- Kural anlama sorusunu yanlış cevaplayan ya da uzunluk sınırına takılan bir cevabı olan grupları çıkarmak hiçbir C-H1 etiketini değiştirmedi; yalnız GPT'nin n = 32 katkı etiketini "belirsiz"e çevirdi.

**Önceden kaydedilmiş mekanizma ölçüsü.** Ötekilerin ortalaması en az 5 iken en az 10 vermiş ajanlar arasında, ötekilerden biri 0 verdikten sonra 0 verenlerin payı Mistral'da büyüklükle düştü (n = 4, 8 ve 16'da 0,57; 0,42 ve 0,35; Çalışma 1'in minimal kart gruplarında 0,69), GPT'de sabit kaldı (n = 4'ten 32'ye 0,17; 0,17; 0,14 ve 0,19). Ötekiler arasında sıfır yokken bu pay Çalışma 4'ün her büyüklüğünde 0,005–0,026 idi.

**Kural nerede yanıldı (keşifsel; `prereg/prereg_expC.md` F-C.8–F-C.9; Şekil 6).** Bu analizler hataların nedenini değil, nerede oluştuğunu gösterir. İki model de yalnız birinin 0 verip vermediğine değil, ötekilerin kaçının ya da ne kadarının 0 verdiğine tepki verdi. En az bir sıfır gören işbirlikçiler arasında (ötekilerin ortalaması [5, 10), orta oyun):
- **GPT** tek bir sıfırı neredeyse hiç umursamadı (her büyüklükte %0–2'si bıraktı), ama üç ya da daha fazla sıfırdan sonra vakaların %28–42'sinde bıraktı;
- **Mistral'ın** tek bir sıfıra tepkisi gruplar büyüdükçe zayıfladı (n = 4, 8 ve 16'da %57, %32 ve %20) ve üç ya da daha fazla sıfırdan sonra yeniden yükseldi (16'da %57).

Dört kişilik gruplarda "biri 0 verdi" çoğunlukla "üç kişiden biri" demektir: sayı ile pay aynıdır ve kuralın göstergesi ikisini birleştirir. Gruplar büyüdükçe bunlar ayrışıyor ve veri hangisinin belirleyici olduğunu çözmüyor: GPT'nin iki sıfıra tepkisi dört kişilik gruplarda 0,82 (11 karar), 8'de 0,12, 16'da 0,04 idi. Büyük GPT gruplarında üç ya da daha fazla sıfır olağandı (n = 32'de bu durumdaki 1.336 kararın 1.271'i) ve bedavacılar işbirliğine kuralın varsaydığından daha az döndü (0,40–0,46'ya karşı 0,33–0,38); 0'da kalan bedavacılar, kuralın GPT'deki tek adım hatasının en büyük parçasıydı (n = 8, 16 ve 32'de −0,31'in −0,22'si, −0,42'nin −0,23'ü ve −0,65'in −0,28'i). Mistral'da n = 16'daki doğru tahmin kısmen birbirini götüren hatalardan geliyor: işbirlikçiler kuraldan daha hoşgörülüydü, çökmüş gruplar ise 0'da daha sık kaldı.

**Önceden belirlenmiş bir karar kapısının durdurduğu düzeltici test.** Son bir test planladık (`prereg/prereg_expD.md`): 0 verenlerin sayısını ya da payını ekleyen, mevcut bütün grup büyüklüklerinden öğrenilen ve 64 GPT ajanlık bir oyundan önce dondurulacak bir kural. Önce dışarıda bırakılan grup büyüklükleri üzerinde bir karar kapısı vardı. Düzeltilmiş kural, aynı veriden öğrenilen aynı durumlu kuralı, çöküş payının ortalama mutlak hatasında 0,05 farkla geçmeliydi; ikinci koşul (GPT'nin dışarıda bırakılan üç büyüklüğünün en az ikisinde o kuralı geçmek) sağlandı. 0,047 iyileşti; bu yüzden test yapılmadı.

Dışarıda bırakılan büyüklük analizi yine de bilgi veriyor (keşifsel):
- asıl kuralı birkaç grup büyüklüğünden öğrenmek, GPT'nin görülmemiş büyüklükteki hatasını kabaca yarıya indirdi (0,41 → 0,22) ve Mistral'ınkini dörtte bir azalttı (0,23 → 0,17);
- sayı ya da pay bilgisi en büyük büyüklüğe dışdeğerlemede yardım etti (32 ajan: 0,39 → 0,11–0,14), ama GPT'nin 16 ajanlık tahminini kötüleştirdi (0,10 → 0,14–0,22);
- hiçbir kural Mistral'ın sekiz kişilik gruplarını iyi tahmin edemedi.

![Şekil 5](fig/fig5_scaling.png)

**Şekil 5.** Çalışma 4: 8. turda çöküş bölgesindeki grupların payı, grup büyüklüğüne göre. Paneller şunları gösterir:
- gözlenen değerler (%95 Wilson aralıkları);
- dondurulmuş kuralın koşudan önce yazılan tahmini;
- aynı kuralın her grubun gözlenen 1. turundan başlatılmış hali;
- tek başına verilen cevaplar (R0), yine her grubun gözlenen 1. turundan başlatılarak.

![Şekil 6](fig/fig6_count.png)

**Şekil 6.** Ötekiler arasında bir, iki ya da üç ve daha fazla sıfır gördükten sonra 0 veren işbirlikçilerin payı, grup büyüklüğüne göre; her çubuğun üstünde karar sayısı. Veri: ötekilerin ortalaması [5, 10) olan işbirlikçiler, orta oyun; 10'dan az kararlı çubuklar gösterilmedi. Keşifsel: şekil tepkinin nerede farklılaştığını gösterir, nedenini değil.

## 9. Tartışma

**Tek başına verilen cevaplar LLM grup dinamiğinin kötü bir üreticisi.** İnsanlarda katkı çizelgeleri bireyi gruba bağlar (Fischbacher ve Gächter, 2010). LLM ajanlarında "10 turun 5.'si" üzerine tek seferlik bir soru bunu yapmadı. Tek başına verilen cevap oyun içindeki davranıştan farklıydı (DeepSeek) ve ufku kaçırdı (Mistral, GPT). Ayrıca farklı türde bir sistem öngördü: emici bir çöküşü olan bir eşik süreci yerine ortalamaya çeken bir harita. GABM ajanlarını tek başına sorulan sorularla ayarlamak ya da doğrulamak, her cevap mantıklı görünse bile, yalnız işbirliği düzeyini değil makro yapısını da yanlış gösterebilir.

**Bağlam içinde ölçülen kurallar makro yapıyı üretiyor.** Bir tur bellekli, ötekilerin ortalamasına, bir sıfır göstergesine ve kalan turlara bakan bir kural dört şey yaptı:
- yörüngeleri yeniden üretti;
- yeni bir koşuya genellendi;
- dondurulduğunda görülmemiş uzunlukta bir oyunu tahmin etti;
- gruplarda görülen çöküş tuzağını, yapışkan işbirliği durumunu, iki uçlu sonları ve devrilme noktalarını üretti (keşifsel); Mistral'daki istisnalar Bölüm 7.1, 7.3 ve 7.4'te.

Ajan tabanlı sosyal bilimin diliyle, bu makro özellikler mikro kurallar tarafından üretiliyor, ama yalnız işledikleri yerde ölçülen kurallar tarafından. Ömürleri, devrilme noktalarını ve son durum dağılımlarını kuraldan okuyarak değil, kuralı simüle ederek elde ettik; bu, Bedau'nun (1997) zayıf ortaya çıkış kavramının ruhuna uygundur. Bu, LLM nüfuslarında makro ile mikronun ayrıştığına dair bulguları tamamlıyor (Ferraz de Arruda ve ark., 2026): toplu uyum doğru mikro kuralları garanti etmez ve bizim düzenimizde doğru mikro kurallar bağlam içinde ölçülmeyi gerektirdi.

**LLM grupları büyük gruplarda daha kırılgandı.** Sınanan iki modelde de çökmüş grupların payı en büyük gruplarda dört kişilik gruplardakinden yüksekti (büyüklüğün her ikiye katlanışında pozitif bir eğilim; tekdüze bir artış değil). Keşifsel analizlerimiz iki katkıya işaret ediyor: ajanlar ötekilerin kaçının ya da ne kadarının 0 verdiğine tepki veriyor; GPT'nin en büyük gruplarında (32 ajan) birkaç bedavacı olağandı ve bedavacılar 0'da kaldı. Bu yüzden simüle edilmiş bir LLM ajan toplumunu büyütmek tarafsız bir işlem değil: küçük gruplarda işbirliğini sürdüren aynı ajanlar büyük gruplarda onu kaybedebilir.

**Mikro kurallar simüle edilecek ölçekte ölçülmeli.** Dört kişilik gruplarda ölçülen bir kural daha uzun bir oyunu ve bir modelde daha büyük grupları tahmin etti (kısmen birbirini götüren hatalarla); öteki modelde edemedi. Olası bir neden, dört kişilik grupların "biri bıraktı" ile "ötekilerin üçte biri bıraktı"yı nadiren ayırmasıdır; bu fikre dayanan düzeltici kural yalnız kısmen desteklendi ve karar kapısında durduruldu. Asıl kuralı birkaç grup büyüklüğünden öğrenmek, GPT'nin görülmemiş büyüklükteki hatasını kabaca yarıya indirdi ve Mistral'ınkini dörtte bir azalttı (keşifsel). Üretken ajan tabanlı modeller için bu, ilgilenilen nüfus büyüklüklerinde ya da bunlar boyunca ayarlama yapmak ve aktarımı ileriye dönük sınamak demek.

**LLM grupları eşik sistemleri gibi davranıyor, DeepSeek ve Mistral'da keskin biçimde.** Bu iki modelde tek bir bırakan, dört kişilik bir grubun olası sonunu değiştirdi ve çökmüş bir grup neredeyse hiç toparlanmadı. Bu, toplu davranışın eşik modellerinin yapısıdır (Granovetter, 1978); burada eşik çok düşük ve dipteki durum neredeyse emici. Bu, LLM nüfuslarını başlangıç koşullarına ve seyrek sapmalara duyarlı yapar. Aynı oyundaki insan grupları daha bağışlayıcı ve daha çeşitliydi. LLM ajanlarını insanların yerine kullanan simülasyonlar, insan verisindekinden daha keskin devrilmeler ve daha az ara son gösterebilir.

**Kimlik tanımları talimat olarak okunuyor gibi görünüyor.** Şehir adları fark edilebilir bir etki yapmadı; değer cümleleri (ve Mistral'da mahkeme süresi olgusu) ifadeleri üzerinden etki etti; DeepSeek ve Mistral kartı sıklıkla deneycinin bir ipucu olarak tarif etti (Ek S1). Bu, davranışsal çapalarla (Wang ve ark., 2026) ve ültimatom oyunundaki sonuçlarımızla (Geyik, 2026a) tutarlı.

**Kendi mekanizmamız adil bir testi geçemedi.** Muhakeme metinlerini okuduktan sonra akla yatan "görünen bedavacı" açıklaması yalnız bir modelde tuttu. Daha geniş açıklama (ufuk dahil, bağlam içi kurallar) zaman ufkunun ileriye dönük testini geçti; grup büyüklüğünde iki modelin birinde tuttu (kısmen birbirini götüren hatalarla).

### Sınırlılıklar

- **Ölçek ve ortam.** Çalışma 1–3 dört kişilik grupları kullandı; Çalışma 4 32 ajana kadar çıkıyor, bu da büyük bir nüfustan hâlâ çok uzak. Gruplar homojendi ve en çok 15 tur oynadı; ağ ve ceza yoktu. Çalışma 4'te istem grup büyüklüğüyle uzuyor; dolayısıyla büyüklük ile istem uzunluğu ayrılamıyor.
- **Çalışma 4.** Minimal kartlar ve iki model kullanıldı; DeepSeek, minimal kartlı gruplarının neredeyse hepsi dört ajanda bile çöktüğü için alınmadı (Çalışma 2, B kolu: 0,96). Mistral'ın sekiz kişilik grupları açıklanamadı. Sayı/pay açıklaması keşifsel ve yalnız kısmen destekleniyor; düzeltici testi önceden belirlenmiş bir karar kapısında durduruldu.
- **Büyük gruplar.** Duman testi okumasında ajanlar uzun geçmişlerde ara sıra sıfır verenleri yanlış saydı; bir sayım hatası aynı muhakeme içinde düzeltildi. Ajan başına belirli bir hata oranı için, kural anlama sorusunda herhangi bir yanlış cevabı olan grupları çıkarmak büyüklük arttıkça daha çok grubu dışarıda bırakır; bu duyarlılık analizi büyüklükle karışıktır (pratikte n = 4, 8, 16 ve 32'de 2, 0, 2 ve 1 GPT grubu çıkarıldı, hiç Mistral grubu çıkarılmadı). Dondurulmuş kural, ajanların durumlarını kararların %88–100'ünde tam ayrıntıda buldu (aynı kart içinde %81–97; kalanı daha kaba durumlara geri çekildi; Ek S4).
- **Makro analizlerin statüsü.** Keşifseldir: ana sonuçlardan sonra seçildi; eşikler önceden sabitlendi ama doğrulanmadı; yalnız son durumlar için 1/9 duyarlılık kontrolü yapıldı.
- **Ömürler.** 100 turluk ömürler kuralın özellikleridir, gözlenen ufkun (en çok 12 orta oyun turu) çok ötesindedir.
- **İnsan karşılaştırması.** Betimseldir; insan kuralı örneklem içinde uydurulmuştur.
- **Modeller ve sağlayıcılar.** Üç tescilli ya da sağlayıcı üzerinden sunulan model kullanıldı; sağlayıcılar yalnız belgeleyebildiğimiz biçimlerde müdahale etti:
  - Mistral'ın sağlayıcısı görünüşe göre JSON çıktısı hakkında bir sistem talimatı ekledi;
  - DeepSeek'in sağlayıcısı hız sınırları uyguladı;
  - Çalışma 3'ü bir Mistral kesintisi böldü.
- **DeepSeek.** Minimal kartlarla tabana yakın katkı verdi; bu, testlerinin birkaçını sınırlıyor.
- **Tanıma.** DeepSeek ve Mistral oyunu ve literatürünü tanıyor (Ek S1); "insana benzer" davranış yeniden üretilen bilgi olabilir.

## 10. Veri ve kodun erişilebilirliği

Bu ön baskı, eki, bütün planlar ve ekleri, kod, ayarlar, istem çerçeveleri ve kimlik kartları, dondurulmuş kural tabloları ve tahminler, analiz çıktıları ve şekil betikleri ile bütün kararlar ve muhakeme metinleri https://doi.org/10.5281/zenodo.23539451 adresinde birlikte arşivlenmiştir (içerik ve yeniden üretme adımları `RELEASE.md`'de). Çalışma 4'ün planı ve tahmini, ana koşusundan önce ayrıca kaydedildi (Geyik, 2026b). Ham API kayıtları hesap kimliği çıkarılarak yayımlanmıştır. Ek (`paper/preprint_v1_supplement.md`) kimlik ve etkileşim ayrıntılarını (S1–S2), hücre düzeyindeki makro yapıyı (S3) ve Çalışma 4 ayrıntılarını (S4) içerir.

## Kaynaklar

Kaynakça İngilizce sürümdekiyle aynıdır.

- Bedau, M. A. (1997). Weak emergence. *Noûs*, 31(s11), 375–399. https://doi.org/10.1111/0029-4624.31.s11.17
- Bin Tareaf, R. (2026). Benchmarking large language model agent societies against human behavioural distributions. arXiv:2608.28182
- Epstein, J. M. (1999). Agent-based computational models and generative social science. *Complexity*, 4(5), 41–60. https://doi.org/10.1002/(SICI)1099-0526(199905/06)4:5<41::AID-CPLX9>3.0.CO;2-F
- Ferraz de Arruda, H., Gracia Lázaro, C., Aleta, A., & Moreno, Y. (2026). Collective cooperation without individual fidelity in LLM agents. arXiv:2606.30454
- Fischbacher, U., & Gächter, S. (2010). Social preferences, beliefs, and the dynamics of free riding in public goods experiments. *American Economic Review*, 100(1), 541–556. https://doi.org/10.1257/aer.100.1.541
- Fischbacher, U., Gächter, S., & Fehr, E. (2001). Are people conditionally cooperative? Evidence from a public goods experiment. *Economics Letters*, 71(3), 397–404. https://doi.org/10.1016/S0165-1765(01)00394-9
- Geyik, G. (2026a). LLMs simulate the description of a culture, not the culture: An attempt to reproduce Henrich's cross-cultural ultimatum game finding with LLM agents. Zenodo. https://doi.org/10.5281/zenodo.23119302
- Geyik, G. (2026b). Pre-registered forecast: how cooperation among LLM agents changes with group size (Experiment C). Zenodo. https://doi.org/10.5281/zenodo.23483296
- Granovetter, M. (1978). Threshold models of collective behavior. *American Journal of Sociology*, 83(6), 1420–1443. https://doi.org/10.1086/226707
- Herrmann, B., Thöni, C., & Gächter, S. (2008). Antisocial punishment across societies. *Science*, 319(5868), 1362–1367. https://doi.org/10.1126/science.1153808
- Herrmann, B., Thöni, C., & Gächter, S. (2017). Data from: Antisocial punishment across societies. Dryad. https://doi.org/10.5061/dryad.87301
- Manoranjan, V., & Gaikwad, S. N. S. (2026). When identity overrides incentives: Representational choices as governance decisions in multi-agent LLM systems. arXiv:2601.10102
- Teo, P. H. (2026). LLM agents as static level-k players in behavioural games. arXiv:2606.27845
- Wang, Y., Lester, J., & Srivastava, S. (2026). The story shapes the agent: Narrative priors in LLM behavior. arXiv:2607.18566
- World Bank (2019). *Doing Business 2020: Comparing business regulation in 190 economies*. Washington, DC: World Bank. https://doi.org/10.1596/978-1-4648-1440-2
