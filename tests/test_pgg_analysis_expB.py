"""Experiment B (prereg_expB): frozen rules, 15-round forecast, B-H1 / B-H2 on synthetic worlds,
and the 15-round prompt. No API calls."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis_expB as pb  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MATCHER = {x: np.array([float(x)] * 4) for x in (0, 5, 10, 15, 20)}


def world(T, quit_from, g=6):
    """Everyone gives 10 until round quit_from - 1 and 0 from round quit_from on."""
    out = np.zeros((g, T, 4))
    out[:, :quit_from - 1, :] = 10
    return out


def frozen_from(train):
    groups = {("gpt", "a_minimal"): train}
    return pb.build_frozen(groups, {("gpt", "a_minimal"): MATCHER}, {"run": "synthetic"})


def rows_from(groups_by_card, T, model="gpt"):
    rows = []
    for card, G in groups_by_card.items():
        for k, g in enumerate(G):
            unit = f"{model}|{card}|minimal|N|group|{k}|abstract_v4"
            sess = f"s-{model}-{card}-{k:03d}"
            for a in range(1, 5):
                rows.append({"model_key": model, "card_id": card, "arm": "group", "unit": unit, "session_id": sess,
                             "step": "comprehension", "round": 1, "agent_id": a, "comp_q1_correct": True,
                             "comp_q2_correct": True, "comp_missing": False})
            for t in range(1, T + 1):
                for a in range(1, 5):
                    rows.append({"model_key": model, "card_id": card, "arm": "group", "unit": unit, "session_id": sess,
                                 "step": "contribute", "round": t, "agent_id": a,
                                 "contribution": float(g[t - 1, a - 1])})
    return rows


class Bins(unittest.TestCase):
    def test_same_bins_in_training_length(self):
        self.assertEqual([pb.bin_kalan(t, 10) for t in range(2, 11)], [pb.bin_mutlak(t, 10) for t in range(2, 11)])

    def test_bins_in_15_rounds(self):
        self.assertEqual([pb.bin_kalan(t, 15) for t in (2, 9, 13, 14, 15)], [0, 0, 0, 1, 2])
        self.assertEqual([pb.bin_mutlak(t, 15) for t in (2, 8, 9, 10, 15)], [0, 0, 1, 2, 2])


class Frozen(unittest.TestCase):
    def test_sha_lock(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.json"
            p.write_text(json.dumps(frozen_from(world(10, 9))))
            good = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertIn("models", pb.load_frozen(p, good))
            with self.assertRaises(ValueError):
                pb.load_frozen(p, "0" * 64)

    def test_round_trip_tables(self):
        fz = json.loads(json.dumps(frozen_from(world(10, 9))))
        r = pb.rules_for(fz, "gpt", "a_minimal", "R3")
        self.assertEqual(int(np.argmax(r.dist((2, 3, 0, 0)))), 10)       # mid game: keep 10
        self.assertEqual(int(np.argmax(r.dist((2, 3, 0, 1)))), 0)        # second-to-last round: quit

    def test_forecast_horizon_world(self):
        fz = frozen_from(world(10, 9))
        fc = pb.forecast(fz, ("gpt",), ("a_minimal",), T=15, s=50)["gpt"]["a_minimal"]
        self.assertEqual(fc["R3-kalan"], [10.0] * 13 + [0.0, 0.0])
        self.assertEqual(fc["R3-mutlak"], [10.0] * 8 + [0.0] * 7)


class Hypotheses(unittest.TestCase):
    def run_world(self, test_world):
        fz = frozen_from(world(10, 9))
        rows = rows_from({"a_minimal": test_world}, 15)
        return pb.run_analysis(fz, rows, set(), ("gpt",), ("a_minimal",), 15, 30, 300)["main"]

    def test_horizon_tracking_world(self):
        r = self.run_world(world(15, 14))
        self.assertEqual(r["B_H1"]["gpt"]["label"], "tahmin tuttu (sıkı eşdeğerlik)")
        self.assertEqual(r["B_H2"]["gpt"]["label"], "açıklanan ufku izliyor")
        self.assertLess(r["B_H3"]["gpt"]["rmse"]["R3-kalan"], r["B_H3"]["gpt"]["rmse"]["R3-mutlak"])

    def test_absolute_round_world(self):
        r = self.run_world(world(15, 9))
        self.assertEqual(r["B_H2"]["gpt"]["label"], "mutlak tur numarasına bağlı")
        self.assertEqual(r["B_H1"]["gpt"]["label"], "tahmin sapıyor: gerçek daha düşük")

    def test_r0_is_deterministic_matcher(self):
        fz = frozen_from(world(10, 9))
        sim = pb.simulate_variant(fz, "gpt", "a_minimal", "R0", np.array([10.0, 10, 0, 10]), 15, 5, ("x",))
        self.assertEqual(sim.shape, (5, 15, 4))
        self.assertTrue(np.allclose(sim[0, 1], [20 / 3, 20 / 3, 10, 20 / 3]))


class Prompt15(unittest.TestCase):
    def test_only_the_round_count_changes(self):
        fr = pgg_frames.load_frame(ROOT / "frames" / "abstract_v4.json")
        p10, p15 = pgg_game.GameParams(), pgg_game.GameParams(rounds=15)
        card = pgg_game.Card("boston_minimal", "minimal", "You are a 21-year-old university student living in Boston.")
        hist = [pgg_game.RoundRecord(1, [10, 10, 0, 10], pgg_game.project_payoffs(p10, [10, 10, 0, 10]))]
        a = fr.contribution_messages(p10, "N", card, hist, 0, 2)[1]["content"].split("\n")
        b = fr.contribution_messages(p15, "N", card, hist, 0, 2)[1]["content"].split("\n")
        diff = [(x, y) for x, y in zip(a, b) if x != y]
        self.assertEqual(diff, [("- The same 4 players stay together for all 10 rounds.",
                                 "- The same 4 players stay together for all 15 rounds."),
                                ("ROUND 2 of 10. You are Player 1. All players decide at the same time, without seeing each other's choice for this round.",
                                 "ROUND 2 of 15. You are Player 1. All players decide at the same time, without seeing each other's choice for this round.")])

    def test_configs(self):
        for name, G in (("expB_smoke", {"deepseek": 1, "mistral": 1, "gpt": 1}),
                        ("expB_main", {"deepseek": 8, "mistral": 6, "gpt": 8})):
            c = json.loads((ROOT / "configs" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(c["params"], {"rounds": 15})
            self.assertEqual(c["groups_per_cell_by_model"], G)
            self.assertEqual(c["arms"], ["group"])
            self.assertEqual(set(c["frames"]), {"abstract_v4"})
            self.assertEqual(c["cards_sha256"], hashlib.sha256((ROOT / c["cards"]).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
