# Uzun ömürlü koşu: yöntem karşılaştırması ve çalıştırma talimatı (EMİR 4 / 4a, görev #80)

Tarih: 2026-10-09. API çağrısı yok. Bu ortamda yapılan denemeler aşağıda tarihli ve
sonucuyla yazılı; denenemeyenler **(doğrulanmadı)** diye işaretli.

## 1. Sorun

- Mini-pilot (`minipilot_20261008`) araç süre sınırı (600 sn) yüzünden 24 segmente bölündü,
  23 segment SIGINT ile kesildi. Segmentler fiilen 438–539 sn (bir kez 610 sn) sürdü; config'teki
  `request_deadline_s` = 900 sn hiç işlemedi (prereg_minipilot.md teknik not T2).
- Pilot v2'de (#43) `nohup … &` ile başlatılan segment 1, 58 sn sonra üç modelde aynı anda
  "Connection error" ile `run_aborted` oldu; o zamanki açıklama "başlatan sandbox komutu bitince
  ağ proxy'si kapandı" idi. Araç düzeyinde arka plan komutu ise görev oturumuna bağlı kaldı
  (#44: "görev oturumu kapanınca `interrupted` ile kapanması olası").
- İstenen: koşu, görev / araç oturumundan bağımsız bir süreçte yürüsün; orc ve kullanıcı ilerlemeyi
  yalnız dosyalardan izlesin.

## 2. Bu ortamda denenenler (2026-10-09, orc sandbox'ı, macOS 14.5)

| Deneme | Sonuç |
|---|---|
| `which setsid` | Yok: macOS'ta `setsid` komutu yok. Python `subprocess.Popen(start_new_session=True)` aynı `setsid()` çağrısını yapıyor |
| `scripts/runctl.py start` ile sahte koşu (tests/fake_long_run.py, sahte API) | Süreç ayrı oturumda başladı. Başlatan komut bitti, süreç sonraki komutlarda heartbeat yazmayı sürdürdü (1 sn aralık, 6+ heartbeat) |
| Ayrık süreçten ağ: başlatan komut bittikten ~16 sn sonra ücretsiz `GET /api/v1/models/mistralai/mistral-large-4-0/endpoints` | HTTP 200 (iki deneme: t=1 sn ve t=20 sn). Yani proxy komut bitince **kapanmadı**. #43'teki açıklama bu oturumda tekrar etmedi. Görev (orc oturumu) bittikten sonra ne olduğu **(doğrulanmadı)** |
| Sonraki bir komuttan aynı sürece `SIGTERM` (`runctl.py stop`) | `PermissionError`. Sandbox, başka bir komutun sürecine sinyal göndermeye izin vermiyor. `runctl.py stop` otomatik olarak `stop_request.json` yoluna düştü; koşu ~1 sn içinde kendine SIGTERM gönderdi, `stop_reason="interrupted"` |
| Aynı komut içinde `SIGTERM` (test takımı) | Çalışıyor (`tests/test_runctl.py`) |
| `tmux -S $TMPDIR/x.sock new -d` | `error creating … (Operation not permitted)`: sandbox Unix soketi açtırmıyor; tmux sandbox içinde kullanılamaz |
| `launchctl print gui/501` | Okuma çalışıyor. `launchctl bootstrap` denenmedi: kullanıcı oturumuna kalıcı bir ajan kurar (geri alınması gereken sistem değişikliği) **(doğrulanmadı)** |
| `caffeinate -is -w PID` | Çalışıyor: hedef süreç yaşarken açık, hedef bitince kendisi de çıkıyor |

## 3. Seçeneklerin karşılaştırması

| Seçenek | Sandbox'ta çalışırlık | Oturum / görev kapanınca | Durdurma / sürdürme | Log yeri | Risk |
|---|---|---|---|---|---|
| **A. Araç arka plan komutu** (bugünkü yol, `run_in_background` / 600 sn ön plan) | Çalışır | Görev bitince süreç ölür ya da `interrupted` olur (#44); 600 sn ön plan sınırı segment böldürür (mini-pilot) | SIGINT/SIGTERM, `--resume` | Komut çıktısı + run dizini | Uçuştaki çağrılar kaybolur (mini-pilot: 100 atılan yanıt); kesinti sayısı araç sınırına bağlı |
| **B. setsid + SIGHUP yok sayma (nohup eşdeğeri), `scripts/runctl.py start`** | Başlar, komut bitince yaşar, ağ en az 16 sn sonra da açık (denendi). Orc görevi bittikten sonra ağ **(doğrulanmadı)**; süreç sandbox profilini miras alır | Kullanıcının kendi Terminal'inden başlatılınca: terminal kapanması süreci etkilemez (oturumu ve kontrol terminali yok) **(bu ortamda terminal yok, doğrulanmadı)**. macOS'ta oturumu kapatma (logout) ve yeniden başlatma süreci öldürür **(doğrulanmadı)** | `runctl.py stop` → SIGTERM (aynı kullanıcı, sandbox dışı) ya da `stop_request.json` (orc sandbox'ı); `runctl.py start --resume` | `runs/<run>/console.log` (stdout+stderr), `launcher.jsonl`, `status.json`; ham log ve özet her zamanki yerde | Mac uykuya geçerse bağlantılar kopar (`--caffeinate` ile azalır; kapak kapanınca yine uyur). Süreç ölürse durum dosyası "bayat" görünür, `--resume` ile devam edilir |
| **C. tmux / screen** | tmux sandbox'ta açılamıyor (Unix soketi yasak, denendi); screen de aynı kısıtta olmalı **(doğrulanmadı)** | Kullanıcının terminalinde: tmux sunucusu terminal kapanınca yaşar; logout'ta ölür **(doğrulanmadı)** | Panede Ctrl-C (SIGINT → `interrupted`), `--resume` | Panenin kaydırma geçmişi; dosyaya ancak `tee` ile | Yanlışlıkla Ctrl-C; orc bağlanıp izleyemez, yalnız dosyalardan izler (B ile aynı); ek araç bilgisi gerekir |
| **D. launchd kullanıcı ajanı** (`~/Library/LaunchAgents/*.plist`, `launchctl bootstrap gui/501`) | Kurulum denenmedi **(doğrulanmadı)**. launchd'nin başlattığı süreç orc sandbox'ının **dışında** çalışır; bu yüzden ajanı orc değil kullanıcı kurmalı | Terminalden ve orc'tan bağımsız; logout'ta `gui` alanındaki ajanlar biter **(doğrulanmadı)** | `launchctl bootout` ya da SIGTERM; `KeepAlive` açık kalırsa durdurulan koşu yeniden başlatılır (çift faturalama riski), kapalı olmalı | `StandardOutPath` / `StandardErrorPath` | Kabuk ortamı yok: anahtar `../.env`'den okunmalı ya da plist'e yazılmalı (düz metin anahtar, kabul edilemez); `_kod_<sha>/` kopyasında `../.env` = `workspace/.env` yok. Kurulum ve temizlik (plist silme) gerekir |
| (E. OpenRouter Batch) | — | Süreç gerekmez | Batch kimliği diskte, `--resume` toplar | Batch logları | Ayrı mimari; kullanıcı notundaki batch yolu. Bu emrin konusu değil |

## 4. Öneri

**B: `scripts/runctl.py start`, ücretli koşularda kullanıcının kendi Terminal'inden (sandbox
dışında) `--caffeinate` ile.** Orc koşuyu yalnız dosyalardan izler (`runctl.py status`) ve gerekirse
`runctl.py stop` ile durdurur.

Gerekçe:
- Sistemde kalıcı bir şey kurmuyor (D'nin aksine). Komut, `--resume`, kilit dosyası ve kod sürümü
  denetimi aynen pgg_game.py'ninki.
- Durdurma iki yoldan da aynı sona varıyor: `stop_reason="interrupted"`, özet hemen yazılır,
  uçuştaki çağrılar beklenir. Orc sandbox'ı sinyal gönderemediği için durdurma isteği dosyası var
  (denendi).
- Araç süre sınırı ortadan kalkıyor; config'teki 900 sn deadline ve 1800 sn stall bekçisi yeniden
  işler.
- Sandbox dışında başlatılan süreç orc'un ağ proxy'sine bağlı değil. Orc sandbox'ında başlatılan
  süreçte ağ, komut bittikten sonra açık kaldı. Ancak görev bitince ne olacağı doğrulanmadı.
  Ücretli bir koşu bu belirsizliğe bırakılmamalı.
- Orc'un kendi başlatması yalnız deneme / tesisat içindir (sahte API ya da birkaç ücretsiz GET).
  Gerçek koşuyu orc başlatacaksa, önce sandbox'ta başlatılmış bir sürecin orc görevi bittikten
  sonra da ağa eriştiği ücretsiz bir GET denemesiyle gösterilmeli.

## 5. Durum dosyası (`runs/<run>/status.json`)

Koşu süreci kendisi yazar (pgg_game.py): segment başında, sonra her `--heartbeat-interval` sn'de
(varsayılan 30) ve sonda. Dosya atomik olarak değiştirilir (geçici dosya + `os.replace`). Okuyan
taraf hiçbir zaman yarım dosya görmez.

| Alan | Anlam |
|---|---|
| `pid`, `host`, `run`, `segment`, `resume` | Koşu süreci ve segmenti |
| `state` | `running`; durma nedeni oluşunca `stopping`; sonda `ended` |
| `heartbeat_ts` / `heartbeat_at`, `heartbeat_interval_s`, `n_heartbeats` | Son heartbeat |
| `units` | `n_units`, `n_complete` (önceki segmentler + bu segmentte biten birimler; sonda özetteki sayı, `source: summary`) |
| `cost_usd` | `total`, `segment`, `per_model` (sonda özetteki toplam) |
| `stop_reason`, `signal`, `stopped_models`, `stop_request` | Durma bilgisi |
| `outcome`, `ended_at`, `error`, `summary` | Yalnız sonda: `completed` / `stopped` / `aborted` / `error` |

Heartbeat yalnız sürecin yaşadığını gösterir, ilerlemeyi göstermez. İlerleme için birimlere, maliyete
ve `runctl.py status` çıktısındaki "Ham log son yazım" satırına bakılır. Takılmayı ayrıca stall
bekçisi yakalar. Denetimlerde reddedilen bir koşu ya da sürdürme `status.json` yazmaz: önceki segmentin
dosyası olduğu gibi kalır (test edildi).

## 6. Adım adım çalıştırma (kullanıcı, kendi Terminal'inde)

1. Kodu sabitleyin (bugünkü yöntem):
   ```bash
   cd "/Users/karbon/Desktop/Veri Bilimi/complexity-prj/project-publicgoods"
   W="/Users/karbon/Desktop/Veri Bilimi/complexity-prj/orc/data/projects/PublicGoods/workspace"
   SHA=<commit>
   mkdir "$W/_kod_$SHA" && git archive $SHA | tar -x -C "$W/_kod_$SHA"
   .venv/bin/python pgg_game.py --write-code-version "$W/_kod_$SHA" --code-commit $SHA
   ```
2. Anahtar: `_kod_<sha>/` kopyasında `../.env` yok (`workspace/.env`). Anahtarı yalnız o
   terminal için ortama verin, ekrana yazdırmadan. Örneğin
   `set -a; source "/Users/karbon/Desktop/Veri Bilimi/complexity-prj/.env"; set +a`.
   `runctl.py` anahtarın değerini okumaz, yalnız var olup olmadığına bakar. `launcher.jsonl`
   ortamı kaydetmez.
3. Kuru çalıştırma ve kapı:
   ```bash
   cd "$W/_kod_$SHA"
   PY="/Users/karbon/Desktop/Veri Bilimi/complexity-prj/project-publicgoods/.venv/bin/python"
   $PY pgg_game.py --dry-run --config configs/<config>.json            # yeni koşu
   $PY pgg_game.py --dry-run --resume --config configs/<config>.json --run <run>   # sürdürme
   ```
4. Başlatın (açık run adıyla; `{run_date}` şablonu kabul edilmez):
   ```bash
   $PY scripts/runctl.py start --config configs/<config>.json --run <run> \
       --runs-dir "$W/runs" --caffeinate
   # sürdürme: aynı komut + --resume
   ```
   Komut, koşunun ilk `status.json`'u yazmasını bekler (en çok 60 sn), durumu yazar ve çıkar.
   Süreç erken biterse (ör. prereg / kapı / kod sürümü reddi) konsol logunun sonunu gösterir ve
   1 ile çıkar. Terminal artık kapatılabilir; Mac uyumamalı (kapak açık, prize takılı).
5. İzleyin (orc da aynı komutu kullanır; yalnız dosya okur):
   ```bash
   $PY scripts/runctl.py status --runs-dir "$W/runs" --run <run>     # --json da var
   ```
   Çıkış kodları: 0 çalışıyor, 3 bitti, 4 heartbeat bayat (süreç ölmüş olabilir: konsol loguna
   bakın, `start --resume`), 2 `status.json` yok.
6. Durdurun:
   ```bash
   $PY scripts/runctl.py stop --runs-dir "$W/runs" --run <run> --wait 1000
   ```
   SIGTERM gider; kilit dosyasındaki pid ile `status.json` pid'i aynı değilse sinyal gönderilmez.
   Orc sandbox'ından çağrılınca `stop_request.json` yazılır. Koşu özeti hemen yazar, uçuştaki
   çağrıları bekler (en çok `request_deadline_s`), sonra `state=ended`. İkinci bir SIGTERM bekleme
   sırasında süreci hemen bitirir; uçuştaki çağrıların sonucu kaybolur ama #79'daki
   `attempt_started` kaydıyla sayılır.
7. Bittikten sonra: `runs/<run>/` altındaki `<run>.jsonl`, `<run>_summary.json`,
   `raw_calls.jsonl`, `<run>.accepted.jsonl`, `status.json`, `console.log`, `launcher.jsonl`
   dosyaları ve satır sayıları raporlanır (veri kalıcılığı kuralı). Ham log commit'e girmez.

## 7. Bilinen sınırlılıklar

- Mac uykuya geçerse (kapak kapanırsa ya da pil modunda `-s` işlemez) açık bağlantılar kopar. Bunlar
  transport hatası olarak yeniden denenir; uzun bir uykuda stall bekçisi koşuyu `stalled` ile durdurur.
  Sonra `--resume` gerekir.
- Logout ve yeniden başlatma süreci öldürür **(doğrulanmadı)**. O zaman `status.json` bayat kalır,
  kilit bayatlar; `start --resume` kilidi devralır (bu kayda geçer).
- `status.json` sonuç dosyası değildir; sayılar için özet ve sonuç dosyaları esastır. Heartbeat'teki
  birim sayısı yaklaşık bir değerdir (sonda özetteki sayı yazılır).
- Orc görevi bittikten sonra sandbox içinde başlatılmış bir sürecin ağa erişimi doğrulanmadı.
