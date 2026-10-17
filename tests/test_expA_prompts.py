"""Experiment A prompts (prereg_expA §1.3, §8): arm B is the main experiment's prompt
byte for byte; arm T differs only in the last rules item and the history contribution
lines. No API calls."""

import collections
import hashlib
import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
B = pgg_frames.load_frame(ROOT / "frames" / "abstract_v4.json")
T = pgg_frames.load_frame(ROOT / "frames" / "abstract_v4_agg.json")
P = pgg_game.GameParams()
CARD = pgg_game.Card("boston_minimal", "minimal",
                     "You are a 21-year-old university student living in Boston.")
RUN_S1 = Path("/Users/karbon/Desktop/Veri Bilimi/complexity-prj/orc/data/projects/PublicGoods/"
              "workspace/runs/main_s1_20261014")


def history(*rounds):
    return [pgg_game.RoundRecord(t + 1, list(c), pgg_game.project_payoffs(P, list(c)))
            for t, c in enumerate(rounds)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Files(unittest.TestCase):
    def test_main_frame_unchanged(self):
        self.assertEqual(sha(ROOT / "frames" / "abstract_v4.json"),
                         "c00db315d9c3141b78b04de5ece650e4b922db907cb90ae124666c439633a9f4")

    def test_cards_are_the_main_minimal_cards(self):
        main = json.loads((ROOT / "cards" / "main_cards_v1.json").read_text(encoding="utf-8"))
        exp = json.loads((ROOT / "cards" / "expA_cards_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(exp, [c for c in main if c["style"] == "minimal"])
        self.assertEqual(len(exp), 4)

    def test_configs_lock_the_files(self):
        for name in ("expA_smoke", "expA_main"):
            c = json.loads((ROOT / "configs" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(c["cards_sha256"], sha(ROOT / c["cards"]))
            for label, f in c["frame_files"].items():
                self.assertEqual(f["sha256"], sha(ROOT / f["path"]), label)
            self.assertEqual(set(c["frames"]), {"abstract_v4", "abstract_v4_agg"})
            self.assertEqual(c["arms"], ["group"])
            self.assertTrue(c["prereg_approved"])
        main = json.loads((ROOT / "configs" / "expA_main.json").read_text(encoding="utf-8"))
        self.assertEqual(main["groups_per_cell_by_model"], {"deepseek": 12, "mistral": 8, "gpt": 12})
        self.assertEqual(main["parallel_units"], 3)
        self.assertEqual(main["stage"], "1")


class Prompts(unittest.TestCase):
    H = history((20, 15, 10, 20), (10, 0, 10, 20))

    def test_example_of_the_prereg(self):
        t = T.history_text(P, "N", self.H[:1], 1)
        self.assertIn("  Your contribution: 15. The other 3 players contributed, on average, "
                      "16.67 points each. Group total: 65.", t)
        b = B.history_text(P, "N", self.H[:1], 1)
        self.assertIn("  Contributions: Player 1: 20; Player 2 (you): 15; Player 3: 10; Player 4: 20. "
                      "Group total: 65.", b)

    def test_mean_format(self):
        self.assertEqual([pgg_frames.fmt_mean(x) for x in (50 / 3, 10, 40 / 3, 6.5, 0, 20)],
                         ["16.67", "10", "13.33", "6.5", "0", "20"])

    def test_t_differs_from_b_only_in_two_places(self):
        for me in range(4):
            for rounds in (0, 1, 2):
                mb = B.contribution_messages(P, "N", CARD, self.H[:rounds], me, rounds + 1)
                mt = T.contribution_messages(P, "N", CARD, self.H[:rounds], me, rounds + 1)
                self.assertEqual(mb[0], mt[0])                          # system message
                lb, lt = mb[1]["content"].split("\n"), mt[1]["content"].split("\n")
                self.assertEqual(len(lb), len(lt))
                diff = [(x, y) for x, y in zip(lb, lt) if x != y]
                self.assertEqual(diff[0], (
                    "- After each round you are told every player's contribution and your own earnings.",
                    "- After each round you are told your own contribution, the average contribution "
                    "of the other 3 players, and your own earnings."))
                self.assertEqual(len(diff), 1 + rounds)                 # one line per history round
                for x, y in diff[1:]:
                    self.assertTrue(x.startswith("  Contributions: ") and y.startswith("  Your contribution: "))

    def test_comprehension_differs_only_in_the_rules_item(self):
        # the rule check repeats the rules, so it differs only in item (a) (prereg_expA F-A.1)
        mb, mt = B.comprehension_messages(P, CARD), T.comprehension_messages(P, CARD)
        self.assertEqual(mb[0], mt[0])
        diff = [(x, y) for x, y in zip(mb[1]["content"].split("\n"), mt[1]["content"].split("\n")) if x != y]
        self.assertEqual(len(diff), 1)
        self.assertTrue(diff[0][1].startswith("- After each round you are told your own contribution"))


@unittest.skipUnless(RUN_S1.exists(), "stage 1 run directory not on this machine")
class SameAsStage1(unittest.TestCase):
    """Arm B renders exactly the messages stage 1 sent for minimal cards (raw log)."""

    def test_rendered_equals_sent(self):
        rows = collections.defaultdict(dict)
        cards = {c["card_id"]: c for c in json.loads((ROOT / "cards" / "main_cards_v1.json").read_text())}
        with open(RUN_S1 / "main_s1_20261014.jsonl") as f:
            for line in f:
                r = json.loads(line)
                if r["step"] == "contribute" and r["card_id"].endswith("_minimal"):
                    rows[r["session_id"]][(r["round"], r["agent_id"])] = r["contribution"]
        checked = 0
        with open(RUN_S1 / "raw_calls.jsonl") as f:
            for line in f:
                o = json.loads(line)
                call = o.get("call") or {}
                if o.get("event") is not None or call.get("step") != "contribute" or not o.get("messages"):
                    continue
                sid = o["session_id"]
                if sid not in rows or call.get("round") not in (1, 2, 5):
                    continue
                t, a = call["round"], call["agent_id"]
                c = rows[sid]
                hist = history(*[tuple(c[(k, j)] for j in range(1, 5)) for k in range(1, t)])
                cid = next(k for k in cards if f"-{k}-" in sid)
                card = pgg_game.Card(cid, "minimal", cards[cid]["text"])
                self.assertEqual(B.contribution_messages(P, "N", card, hist, a - 1, t), o["messages"])
                checked += 1
                if checked >= 60:
                    break
        self.assertGreaterEqual(checked, 60)


if __name__ == "__main__":
    unittest.main()
