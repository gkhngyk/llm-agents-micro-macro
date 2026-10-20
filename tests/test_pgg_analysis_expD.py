"""Experiment D (prereg_expD): count-aware state, rules with back-off, leave-one-size-out choice and
gate on a synthetic "count world", the 64-player frame and config. No API calls."""

import hashlib
import json
import os
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis_expC as pc  # noqa: E402
import pgg_analysis_expD as pd  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CARD = pgg_game.Card("boston_minimal", "minimal", "You are a 21-year-old university student living in Boston.")


def count_world(n, G, rng, p0=0.08, threshold=3):
    """Cooperators give 10 unless at least `threshold` others gave 0 last round; zeros stay 0."""
    out = np.zeros((G, 10, n))
    out[:, 0] = np.where(rng.random((G, n)) < p0, 0.0, 10.0)
    for t in range(1, 10):
        prev = out[:, t - 1]
        z = prev == 0
        k = z.sum(axis=1, keepdims=True) - z
        out[:, t] = np.where(z | (k >= threshold), 0.0, 10.0)
    return out


class State(unittest.TestCase):
    def test_new_elements_agree_with_the_indicator(self):
        rng = np.random.default_rng(0)
        for n in (4, 8, 32):
            prev = rng.choice([0, 5, 10, 20], size=(200, n)).astype(float)
            k = pd.keys_n(prev, 3)
            own, mb, zero = pc.bins_n(prev)
            self.assertTrue(np.array_equal(k[..., 0], own) and np.array_equal(k[..., 1], mb))
            self.assertTrue(np.array_equal(k[..., 2], zero))
            self.assertTrue(np.array_equal(k[..., 2] == 1, k[..., 4] > 0))
            self.assertTrue(np.array_equal(k[..., 4] > 0, k[..., 5] > 0))

    def test_count_and_share_bins(self):
        prev = np.array([[10.0] * 12 + [0.0] * 4])            # n = 16, four zeros
        k = pd.keys_n(prev, 2)[0]
        self.assertEqual(tuple(k[0, 4:]), (3, 2))              # a ten sees 4 zeros of 15: 3+, share 0.27
        self.assertEqual(tuple(k[-1, 4:]), (3, 1))             # a zero sees 3 zeros of 15: 3+, share 0.2 is in (0, 0.2]
        prev2 = np.array([[10.0] * 15 + [0.0]])
        self.assertEqual(tuple(pd.keys_n(prev2, 2)[0][0, 4:]), (1, 1))

    def test_backoff_to_r3_state(self):
        G = count_world(4, 30, np.random.default_rng(1))
        cells, model = pd.train([{"boston_minimal": G}])
        r = pd.rule_of("R4-sayı", cells, model, "boston_minimal")
        unseen = (2, 2, 1, 0, 3, 3)                           # never seen at n = 4 with mean bin 2
        d = r.dist(unseen)
        ref = cells["boston_minimal"].counts[(0, 1, 2, 3)].get((2, 2, 1, 0))
        if ref is not None and ref.sum() > 0:
            self.assertTrue(np.allclose(d, ref / ref.sum()))


class SelectionAndGate(unittest.TestCase):
    def test_count_world_prefers_the_count_rule(self):
        rng = np.random.default_rng(2)
        data = {"base": [{c: count_world(4, 40, rng) for c in pd.CARDS}],
                "C": {n: {c: count_world(n, 30, rng) for c in pd.CARDS} for n in (4, 8, 16, 32)}}
        res = pd.loso(data, "gpt", (16, 32), s=60)
        for h in ("16", "32"):
            self.assertLess(res[h]["R4-sayı"]["abs_err"], res[h]["R3-tümü"]["abs_err"])
        g = pd.gate({"gpt": res})
        self.assertIn(g["chosen"], ("R4-sayı", "R4-pay"))

    def test_gate_rule(self):
        def row(r3, r4s, r4p):
            return {"R3-tümü": {"abs_err": r3, "rmse": 1}, "R4-sayı": {"abs_err": r4s, "rmse": 1},
                    "R4-pay": {"abs_err": r4p, "rmse": 1}}
        good = {"gpt": {"8": row(0.3, 0.1, 0.2), "16": row(0.3, 0.1, 0.2), "32": row(0.3, 0.2, 0.25)},
                "mistral": {"8": row(0.2, 0.1, 0.1), "16": row(0.1, 0.1, 0.1)}}
        g = pd.gate(good)
        self.assertEqual((g["chosen"], g["passed"], g["gpt_wins_vs_R3_all"]), ("R4-sayı", True, 3))
        bad = {"gpt": {"8": row(0.2, 0.18, 0.2), "16": row(0.2, 0.19, 0.2), "32": row(0.2, 0.2, 0.2)},
               "mistral": {"8": row(0.2, 0.2, 0.2), "16": row(0.2, 0.2, 0.2)}}
        self.assertFalse(pd.gate(bad)["passed"])
        self.assertEqual(pd.label_improve({"ci": [0.01, 0.2]}), "R4 daha iyi")
        self.assertEqual(pd.label_improve({"ci": [-0.1, 0.2]}), "ayırt edilemedi")

    def test_frozen_round_trip(self):
        rng = np.random.default_rng(3)
        data = {"base": [{c: count_world(4, 10, rng) for c in pd.CARDS}],
                "C": {8: {c: count_world(8, 10, rng) for c in pd.CARDS}}}
        fz = json.loads(json.dumps(pd.build_frozen(data, "R4-sayı", {"x": "y"})))
        cells, model = pd.train(data["base"] + list(data["C"].values()))
        for key in ((2, 3, 0, 0, 0, 0), (2, 2, 1, 0, 1, 1), (0, 0, 1, 0, 3, 3)):
            a = pd.frozen_rule(fz, "R4-sayı", "boston_minimal").dist(key)
            b = pd.rule_of("R4-sayı", cells, model, "boston_minimal").dist(key)
            self.assertTrue(np.allclose(a, b))


class FrameAndConfig(unittest.TestCase):
    def test_n64_prompt_and_key(self):
        v4 = pgg_frames.load_frame(ROOT / "frames" / "abstract_v4.json")
        fr = pgg_frames.load_frame(ROOT / "frames" / "abstract_v4_n64.json")
        p = pgg_game.GameParams(group_size=64)
        self.assertEqual(fr.comprehension_key(p), {"q1": 240, "q2": -6})
        rng = np.random.default_rng(64)
        hist = []
        for t in range(1, 10):
            c = [int(x) for x in rng.choice([0, 10, 20], size=64)]
            hist.append(pgg_game.RoundRecord(t, c, pgg_game.project_payoffs(p, c)))
        for t in (1, 5, 10):
            self.assertEqual(fr.contribution_messages(p, "N", CARD, hist[:t - 1], 7, t),
                             v4.contribution_messages(p, "N", CARD, hist[:t - 1], 7, t))
        for k in ("system", "rules", "history", "contribute", "isolated", "response", "player_label", "you_suffix"):
            self.assertEqual(fr.data[k], v4.data[k])

    def test_config(self):
        c = json.loads((ROOT / "configs" / "expD_n64_main.json").read_text())
        self.assertEqual(c["params"], {"group_size": 64})
        self.assertEqual(c["frames"], {"abstract_v4_n64": ["gpt"]})
        self.assertEqual(c["groups_per_cell_by_model"], {"gpt": 12})
        self.assertEqual(c["models"], ["openai/gpt-6-luna"])
        f = c["frame_files"]["abstract_v4_n64"]
        self.assertEqual(f["sha256"], hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest())
        self.assertEqual(c["cards_sha256"], hashlib.sha256((ROOT / c["cards"]).read_bytes()).hexdigest())
        self.assertTrue(c["prereg_approved"])


if __name__ == "__main__":
    unittest.main()
