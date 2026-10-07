#!/usr/bin/env python3
"""Çerçeve linter'ı (görev #62, hedef C2; görev #67'de depoya alındı).

Depoda iki kullanımı var: (1) bu komut satırı aracı (aşağıda); (2) koşu başı
denetimi: pgg_game.RunConfig._validate_frames, "kind": "story" olan her
çerçevede ROOTS'u frame_file_hits ve render edilmiş istemlerle tarar; takılan
kök varsa koşu (ve dry-run) başlamaz. Soyut çerçeveler ("kind": "abstract" ya
da alan yok) bilerek "game" / "contribute" içerir, denetlenmez.

Hikâye çerçevesi dosyalarında (frames/SCHEMA.md, şema 1) ve bunlardan motorla
render edilmiş TAM istemlerde (sistem + kullanıcı mesajı + llm_client'ın
eklediği şema isteği) yasaklı kök arar. kart_linter.py'nin eşleşme mantığını
izler: büyük/küçük harf duyarsız ALT DİZGİ araması (sözcük sınırı yok), takılan
kök içinde geçtiği sözcükle yazılır. Tek fark: tire ve alt çizgi boşluk
sayılır ("free-rider", "public_goods", "group_project" yakalanır).

Kullanım:
  python cerceve_linter.py --selftest
  python cerceve_linter.py --frames A.json B.json [--reference abstract_v3.json]
        [--render --code KOD_DIZINI --cards KART.json] [--md CIKTI.md]

  --frames     : denetlenen hikâye çerçeveleri (takılan kök çıkış kodunu 1 yapar)
  --reference  : karşılaştırma için soyut çerçeve (takılanlar raporlanır, çıkış
                 kodunu etkilemez; linter'ın tam istemde çalıştığının kanıtı)
  --render     : her çerçeveden tüm çağrı türlerinin tam istemlerini motorun kendi
                 fonksiyonlarıyla üretir (grup N/P tur 1..R, dört oyuncu konumu,
                 ceza adımı, izole 0..endowment, kural anlama N/P) x tüm kartlar
                 ve bölüt bazında tarar: kart (sistem mesajı), çerçeve (kullanıcı
                 mesajı), kod_sonek (şema isteği cümlesi), şema (JSON şeması).

Ek denetimler (UYARI; çıkış kodunu etkilemez, şart tablosuna kanıt):
  * şart sözlüğü: emek/hak ediş, ortak kaynak/tükenme, kurum/yaptırım imgeleri
    (sözcük başı eşleşmesi, ör. "\\bearn" "learn"e takılmaz);
  * sayı sözcükleri (one..twenty, twice, double, half, ten ...): sayılar yer
    tutucudan gelmeli.
Yalnız standart kütüphane (render için kod dizinindeki pgg_game / pgg_frames).
Çıkış kodu: hikâye çerçevelerinin metinlerinde ve (--render ile) çerçeve/şema/
kod bölütlerinde yasak kök yoksa 0, varsa 1. Kart bölütündeki takılmalar ayrı
listelenir (kart metni bu görevin konusu değil) ve çıkış kodunu etkilemez.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOTS = ["game", "experiment", "participant", "player", "contribut", "public good",
         "group project", "cooperat", "free rid", "commons", "tragedy", "punish", "token",
         "payoff", "nash", "equilibrium"]

# Şart sözlüğü (uyarı): kök -> şart. Sözcük başında eşleşir.
CONDITION_WORDS = {
    # emek / hak ediş / kazanma
    "earn": "emek/hak ediş", "work": "emek/hak ediş", "effort": "emek/hak ediş",
    "deserv": "emek/hak ediş", "labo": "emek/hak ediş", "salary": "emek/hak ediş",
    "wage": "emek/hak ediş", "won": "emek/hak ediş", "win": "emek/hak ediş",
    "reward": "emek/hak ediş", "merit": "emek/hak ediş", "task": "emek/hak ediş",
    # ortak kaynak / tükenme
    "fish": "ortak kaynak", "pasture": "ortak kaynak", "graz": "ortak kaynak",
    "forest": "ortak kaynak", "water": "ortak kaynak", "deplet": "ortak kaynak",
    "resource": "ortak kaynak", "harvest": "ortak kaynak", "well": "ortak kaynak",
    "lake": "ortak kaynak", "field": "ortak kaynak", "herd": "ortak kaynak",
    # kurum / yaptırım / şikâyet
    "complain": "kurum/yaptırım", "court": "kurum/yaptırım", "sanction": "kurum/yaptırım",
    "fine": "kurum/yaptırım", "penal": "kurum/yaptırım", "police": "kurum/yaptırım",
    "law": "kurum/yaptırım", "judge": "kurum/yaptırım", "report": "kurum/yaptırım",
    "authorit": "kurum/yaptırım", "government": "kurum/yaptırım", "tax": "kurum/yaptırım",
    # kültür / din / meslek
    "church": "kültür/din", "mosque": "kültür/din", "temple": "kültür/din",
    "charity": "kültür/din", "zakat": "kültür/din", "tithe": "kültür/din",
    "interest": "kültür/din (faiz)", "dollar": "kültür (para birimi)",
    "euro": "kültür (para birimi)", "riyal": "kültür (para birimi)",
    "krone": "kültür (para birimi)", "christmas": "kültür/din", "ramadan": "kültür/din",
    "farmer": "meslek", "fisher": "meslek", "employ": "meslek", "office": "meslek",
    # oyun/deney literatürüne yakın ama yasak listede olmayan (bilgi)
    "pool": "literatür (kart linter kökü)", "team": "literatür (kart linter kökü)",
    "shar": "literatür (kart linter kökü)", "give": "literatür (kart linter kökü)",
    "selfless": "literatür (kart linter kökü)", "fair": "literatür (kart linter kökü)",
    "trust": "literatür (kart linter kökü)", "invest": "literatür (kart linter kökü)",
    "dilemma": "literatür", "strateg": "literatür", "round": "literatür (soyut terim)",
    "points": "literatür (soyut terim)", "rational": "literatür",
}
NUMBER_WORDS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
                "eighteen", "nineteen", "twenty", "twice", "double", "half", "triple",
                "once", "first", "last", "second", "third", "fourth", "fifth"]


def _norm(text: str) -> str:
    """Küçük harf; tire ve alt çizgi boşluk (uzunluk korunur, indeksler aynı)."""
    return text.lower().replace("-", " ").replace("_", " ")


def _word_at(text: str, s: int, e: int) -> str:
    while s > 0 and (text[s - 1].isalnum() or text[s - 1] in "-'_"):
        s -= 1
    while e < len(text) and (text[e].isalnum() or text[e] in "-'_"):
        e += 1
    return text[s:e]


def find_hits(text: str) -> list[tuple[str, str]]:
    """[(kök, kökün içinde geçtiği sözcük)] — yasak kökler, alt dizgi."""
    low = _norm(text)
    hits = []
    for root in ROOTS:
        for m in re.finditer(re.escape(root), low):
            hits.append((root, _word_at(text, m.start(), m.end())))
    return hits


def find_condition_words(text: str) -> list[tuple[str, str, str]]:
    """[(kök, şart, sözcük)] — şart sözlüğü, sözcük başı eşleşmesi (uyarı)."""
    low = _norm(text)
    out = []
    for root, cond in CONDITION_WORDS.items():
        pat = r"\b" + re.escape(root) + (r"\b" if root in ("won", "win", "well", "fine", "law",
                                                           "tax", "round", "task") else "")
        for m in re.finditer(pat, low):
            out.append((root, cond, _word_at(text, m.start(), m.end())))
    return out


def find_number_words(text: str) -> list[str]:
    low = text.lower()
    return [m.group(0) for w in NUMBER_WORDS for m in re.finditer(r"\b" + w + r"\b", low)]


# --------------------------------------------------------------------------
# Çerçeve dosyasındaki metinler
# --------------------------------------------------------------------------

def frame_strings(obj, path="") -> list[tuple[str, str]]:
    """(yol, metin) — "_" ile başlayan yorum anahtarları hariç tüm metinler."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_") or k in ("schema",):
                continue
            out += frame_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += frame_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


_PLACEHOLDER = re.compile(r"(?<!\{)\{[A-Za-z_][A-Za-z0-9_]*\}(?!\})")


def strip_placeholders(text: str) -> str:
    """Yer tutucu adları ({max_punish}, {player_no} ...) modele gitmez: render'da
    sayı/etiketle değişir. Taramadan önce "{}" ile değiştirilir; render edilmiş
    istem taraması (--render) asıl gösterilen metni ayrıca denetler."""
    return _PLACEHOLDER.sub("{}", text)


def lint_frame_texts(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for p, text in frame_strings(raw):
        shown = _shown(p)
        t = strip_placeholders(text)
        rows.append({"path": p, "hits": find_hits(t),
                     "cond": find_condition_words(t) if shown else [],
                     "numwords": find_number_words(t) if shown else [], "shown": shown})
    return {"frame": raw.get("name"), "file": str(path), "rows": rows}


def frame_file_hits(raw: dict) -> list[tuple[str, str, str]]:
    """[(JSON yolu, kök, sözcük)] — çerçeve belgesinin tüm metinlerinde (yorumlar
    hariç, yer tutucu adları ayıklanmış) yasak kökler. Koşu başı denetimi
    (pgg_game.story_frame_problems, görev #67) bunu ve render edilmiş istemleri
    tarar; görev #73'ten beri varsayılan olarak her çerçeveye uygulanır, yalnız
    açıkça "kind": "abstract" yazan çerçeve muaftır."""
    return [(p, root, word) for p, text in frame_strings(raw)
            for root, word in find_hits(strip_placeholders(text))]


def _shown(p: str) -> bool:
    """Bu metin modele gösteriliyor mu (description, name, answer kind gösterilmez)."""
    return not (p in ("name", "description") or ".answer." in p or p.endswith(".id")
                or re.fullmatch(r"isolated\.\w+\.rules", p) or ".when" in p)


# --------------------------------------------------------------------------
# Render edilmiş tam istemler
# --------------------------------------------------------------------------

def render_all(code_dir: Path, frame_path: Path, cards_path: Path, isolated_round_no=5):
    """[(çağrı türü, kart_id, bölüt, metin)] — motorun kendi fonksiyonlarıyla."""
    sys.path.insert(0, str(code_dir))
    import pgg_frames  # noqa
    import pgg_game as g  # noqa
    frame = pgg_frames.load_frame(frame_path)
    params = g.GameParams()
    cards = g.load_cards(str(cards_path), None)
    suffix = g.SCHEMA_PROMPT_SUFFIX
    n, R, E = params.group_size, params.rounds, params.endowment
    # çeşitli sentetik geçmiş (sayılar değişsin): tur r'de katkılar
    def contribs(r):
        return [(r * 3 + j * 5) % (E + 1) for j in range(n)]
    out = []

    def add(kind, card, messages, schema):
        out.append((kind, card.card_id, "kart", messages[0]["content"]))
        out.append((kind, card.card_id, "çerçeve", messages[1]["content"]))
        out.append((kind, card.card_id, "kod_sonek", suffix))
        out.append((kind, card.card_id, "şema", json.dumps(schema, ensure_ascii=False)))

    for card in cards:
        for cond in ("N", "P"):
            hist = []
            for r in range(1, R + 1):
                c = contribs(r)
                for me in range(n):
                    add(f"grup_{cond}_tur{r}", card,
                        g.contribution_messages(params, cond, card, hist, me, r, prompt_frame=frame),
                        g.contribution_schema(params, True, prompt_frame=frame))
                pe = g.project_payoffs(params, c)
                rec = g.RoundRecord(r, c, pe, final_earnings=pe)
                if cond == "P":
                    for me in range(n):
                        targets = [j + 1 for j in range(n) if j != me]
                        add(f"ceza_P_tur{r}", card,
                            g.punishment_messages(params, card, hist, me, r, c, pe[me],
                                                  prompt_frame=frame),
                            g.punishment_schema(params, targets, True, prompt_frame=frame))
                    pun = [[(i + j + r) % 3 if i != j else 0 for j in range(n)] for i in range(n)]
                    rec.punishment = pun
                    rec.final_earnings, rec.cost_paid, rec.received = g.apply_punishment(
                        params, pe, pun)
                hist.append(rec)
        for iso in frame.isolated_frames:
            for x in range(0, E + 1):
                add(f"izole_{iso}", card,
                    g.isolated_messages(params, card, x, iso, isolated_round_no,
                                        prompt_frame=frame),
                    g.contribution_schema(params, True, prompt_frame=frame))
        if frame.has_comprehension:
            for cond in ("N", "P"):
                add(f"kural_anlama_{cond}", card, frame.comprehension_messages(params, card, cond),
                    frame.comprehension_schema(True))
    return frame, out


def lint_rendered(code_dir, frame_path, cards_path):
    frame, parts = render_all(code_dir, frame_path, cards_path)
    seen = {}
    agg = defaultdict(lambda: {"n": 0, "hits": defaultdict(set), "cards": set()})
    n_prompts = len({(k, c, i) for i, (k, c, _s, _t) in enumerate(parts) if _s == "çerçeve"})
    contribution_in_prompt = 0
    for kind, card_id, seg, text in parts:
        base = re.sub(r"_tur\d+$", "", kind)
        key = (base, seg)
        agg[key]["n"] += 1
        if seg != "kart" and "contribution" in text.lower():
            contribution_in_prompt += 1
        cache_key = (seg, text)
        hits = seen.get(cache_key)
        if hits is None:
            hits = seen[cache_key] = find_hits(text)
        for root, word in hits:
            agg[key]["hits"][root].add(word)
            agg[key]["cards"].add(card_id)
    return {"frame": frame.name, "sha256": frame.sha256, "n_prompts": n_prompts,
            "agg": agg, "contribution_in_prompt": contribution_in_prompt,
            "decision_key": frame.decision_key, "punishment_key": frame.punishment_key}


CODE_FIXED = [
    ("kod_sonek", "\\n\\nRespond with ONLY a JSON object matching this schema:\\n",
     "llm_client.augment_with_schema"),
    ("şema", "JSON şema yapı sözcükleri: type, object, required, properties, integer, "
             "minimum, maximum, string, description", "pgg_game.contribution_schema / punishment_schema"),
    ("şema", "alan adı \"rationale\" (gerekçe alanı)", "pgg_game (sabit, çerçeve değiştiremez)"),
    ("şema", "alan adları \"q1\", \"q2\" ve açıklamaları \"Answer to question 1/2\"",
     "pgg_frames.Frame.comprehension_schema"),
    ("şema", "ceza şemasındaki hedef anahtarları \"2\", \"3\", \"4\" (oyuncu numarası)",
     "pgg_game.punishment_schema"),
    ("çerçeve", "sayı biçimi (12.0 -> 12, 0.4) ve oyuncu numaraları", "pgg_frames.fmt_num"),
]


# --------------------------------------------------------------------------
# Kendi kendine test
# --------------------------------------------------------------------------

def selftest() -> bool:
    cases = {
        "This is a GAME.": ["game"],
        "Games and endgame.": ["game", "game"],
        "a decision-making experiment": ["experiment"],
        "You are a participant.": ["participant"],
        "Player 1 and the players": ["player", "player"],
        "Your contribution; contributing": ["contribut", "contribut"],
        "public goods, public-good, public_good": ["public good"] * 3,
        "the group project / group_project": ["group project"] * 2,
        "Cooperation is cooperative.": ["cooperat", "cooperat"],
        "a free rider, free-riding": ["free rid", "free rid"],
        "tragedy of the commons": ["commons", "tragedy"],
        "punishment points; unpunished": ["punish", "punish"],
        "Tokens!": ["token"],
        "the payoff matrix": ["payoff"],
        "Nash EQUILIBRIUM": ["equilibrium", "nash"],
        "credits_into_jar": [],
        "You put credits into the jar.": [],
        "A common room": [],          # "common" yasak değil, "commons" yasak
        "a group of users": [],       # "group" tek başına yasak değil
        "The project manager": [],    # "project" tek başına yasak değil
        "a voucher basket": [],
    }
    ok = True
    for text, want in cases.items():
        got = sorted(r for r, _ in find_hits(text))
        good = got == sorted(want)
        ok &= good
        print(f"  [{'OK ' if good else 'HATA'}] {text!r} -> {got} (beklenen {sorted(want)})")
    # sözcük gösterimi
    w = find_hits("A free-rider here")[0][1]
    good = w == "free-rider"
    ok &= good
    print(f"  [{'OK ' if good else 'HATA'}] takılan sözcük 'free-rider' -> {w!r}")
    cond_cases = {
        "You earned it.": ["earn"], "You learn fast.": [], "They won.": [], "Fish and water": [],
        "a court": ["court"], "fine weather": ["fine"], "refined": [],
    }
    # "won" sözcük sınırlı: "They won." yakalanmalı
    cond_cases["They won."] = ["won"]
    cond_cases["Fish and water"] = ["fish", "water"]
    for text, want in cond_cases.items():
        got = sorted(r for r, _c, _w in find_condition_words(text))
        good = got == sorted(want)
        ok &= good
        print(f"  [{'OK ' if good else 'HATA'}] şart sözlüğü {text!r} -> {got} (beklenen {sorted(want)})")
    st = strip_placeholders("up to {max_punish} by {player_no}, literal {{player}}")
    good = find_hits(st) == [("player", "player")]
    ok &= good
    print(f"  [{'OK ' if good else 'HATA'}] yer tutucu ayıklama -> {st!r}, kökler {find_hits(st)}")
    nw = find_number_words("the four of you, someone, one another, twice")
    good = sorted(nw) == ["four", "one", "twice"]
    ok &= good
    print(f"  [{'OK ' if good else 'HATA'}] sayı sözcükleri -> {sorted(nw)}")
    return ok


# --------------------------------------------------------------------------
# Rapor
# --------------------------------------------------------------------------

def _fmt_hits(hits) -> str:
    return ", ".join(f"{r} (<{w}>)" for r, w in hits) or "—"


def report(frames, refs, rendered) -> tuple[str, bool]:
    lines = []
    fail = False
    lines.append("## 1. Çerçeve dosyası metinleri (yasak kökler)\n")
    lines.append("| taslak | metin parçası (JSON yolu) | modele gösterilir mi | takılan kök |")
    lines.append("|---|---|---|---|")
    for res, is_ref in [(r, False) for r in frames] + [(r, True) for r in refs]:
        tag = res["frame"] + (" (referans)" if is_ref else "")
        hit_rows = [r for r in res["rows"] if r["hits"]]
        if not hit_rows:
            lines.append(f"| {tag} | tüm {len(res['rows'])} metin parçası | — | **temiz** |")
        for r in hit_rows:
            if not is_ref:
                fail = True
            lines.append(f"| {tag} | `{r['path']}` | {'evet' if r['shown'] else 'hayır'} | "
                         f"{_fmt_hits(r['hits'])} |")
    lines.append("\n## 2. Şart sözlüğü ve sayı sözcükleri (UYARI, çıkış kodunu etkilemez)\n")
    lines.append("| taslak | metin parçası | şart sözlüğü eşleşmesi | sayı sözcüğü |")
    lines.append("|---|---|---|---|")
    for res, is_ref in [(r, False) for r in frames] + [(r, True) for r in refs]:
        tag = res["frame"] + (" (referans)" if is_ref else "")
        any_ = False
        for r in res["rows"]:
            if r["cond"] or r["numwords"]:
                any_ = True
                cond = ", ".join(f"{root} → {c} (<{w}>)" for root, c, w in r["cond"]) or "—"
                lines.append(f"| {tag} | `{r['path']}` | {cond} | {', '.join(r['numwords']) or '—'} |")
        if not any_:
            lines.append(f"| {tag} | tümü | — | — |")
    if rendered:
        lines.append("\n## 3. Render edilmiş tam istemler (bölüt bazında)\n")
        lines.append("Bölütler: **kart** = sistem mesajı (kimlik kartı), **çerçeve** = kullanıcı "
                     "mesajı (çerçeve metni + motorun doldurduğu sayılar/etiketler), "
                     "**kod_sonek** = llm_client'ın eklediği şema isteği cümlesi, **şema** = "
                     "JSON şeması (alan adları çerçeveden ya da koddan).\n")
        lines.append("| taslak | çağrı türü | bölüt | parça sayısı | takılan kök (sözcük) | takılan kartlar |")
        lines.append("|---|---|---|---|---|---|")
        for res, is_ref in rendered:
            tag = res["frame"] + (" (referans)" if is_ref else "")
            for (kind, seg), a in sorted(res["agg"].items()):
                if not a["hits"]:
                    continue
                if seg != "kart" and not is_ref:
                    fail = True
                h = "; ".join(f"{r} ({', '.join(sorted(ws))})" for r, ws in sorted(a["hits"].items()))
                lines.append(f"| {tag} | {kind} | {seg} | {a['n']} | {h} | "
                             f"{', '.join(sorted(a['cards']))} |")
            clean = [(k, s) for (k, s), a in res["agg"].items() if not a["hits"] and s != "kart"]
            lines.append(f"| {tag} | (tüm çağrı türleri) | çerçeve/kod_sonek/şema | "
                         f"{sum(res['agg'][k]['n'] for k in clean)} | **temiz** | — |")
        lines.append("\n### 3a. İstemde \"contribution\" alan adı / sözcüğü\n")
        lines.append("| taslak | toplam tam istem | kart dışı bölütte \"contribution\" geçen parça | karar alanı adı | ceza alanı adı |")
        lines.append("|---|---|---|---|---|")
        for res, is_ref in rendered:
            tag = res["frame"] + (" (referans)" if is_ref else "")
            lines.append(f"| {tag} | {res['n_prompts']} | {res['contribution_in_prompt']} | "
                         f"`{res['decision_key']}` | `{res['punishment_key']}` |")
        lines.append("\n### 3b. Hikâye isteminde kalan, koddan gelen sabit parçalar\n")
        lines.append("| bölüt | parça | kaynak |")
        lines.append("|---|---|---|")
        for seg, what, src in CODE_FIXED:
            lines.append(f"| {seg} | {what} | {src} |")
    return "\n".join(lines), fail


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--frames", nargs="*", default=[])
    ap.add_argument("--reference", nargs="*", default=[])
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--code")
    ap.add_argument("--cards")
    ap.add_argument("--md")
    a = ap.parse_args(argv)
    if a.selftest:
        print("Kendi kendine test:")
        ok = selftest()
        print("SONUÇ:", "GEÇTİ" if ok else "KALDI")
        return 0 if ok else 1
    if not a.frames:
        ap.error("--frames gerekli (ya da --selftest)")
    frames = [lint_frame_texts(Path(p)) for p in a.frames]
    refs = [lint_frame_texts(Path(p)) for p in a.reference]
    rendered = []
    if a.render:
        if not a.code or not a.cards:
            ap.error("--render için --code ve --cards gerekli")
        for p in a.frames:
            rendered.append((lint_rendered(Path(a.code), Path(p), Path(a.cards)), False))
        for p in a.reference:
            rendered.append((lint_rendered(Path(a.code), Path(p), Path(a.cards)), True))
    text, fail = report(frames, refs, rendered)
    head = (f"# Çerçeve linter sonucu\n\nYasak kökler ({len(ROOTS)}): "
            + ", ".join(ROOTS) + "\n\nSONUÇ: " + ("KALDI (hikâye metninde/isteminde yasak kök var)"
                                                 if fail else "GEÇTİ (hikâye metinleri ve "
                                                 "istemlerin çerçeve/kod/şema bölütleri temiz)")
            + "\n")
    out = head + "\n" + text + "\n"
    if a.md:
        Path(a.md).write_text(out, encoding="utf-8")
    print(out)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
