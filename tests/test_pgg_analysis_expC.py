"""Experiment C (prereg_expC): group-size frames and configs, the n-agent state and simulation,
the forecast and C-H1..C-H3 on synthetic worlds with known answers. No API calls."""

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis_expB as pb  # noqa: E402
import pgg_analysis_expC as pc  # noqa: E402
import pgg_analysis_rules as pr  # noqa: E402
import pgg_frames  # noqa: E402
import pgg_game  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MATCHER = {x: np.array([float(x)] * 4) for x in (0, 5, 10, 15, 20)}
CARD = pgg_game.Card("boston_minimal", "minimal", "You are a 21-year-old university student living in Boston.")


def trigger_world():
    """All-10 groups stay at 10; one 0 among tens -> everyone 0 from round 2; all-0 stays."""
    coop = np.full((12, 10, 4), 10.0)
    tip = np.zeros((4, 10, 4))
    tip[:, 0, 1:] = 10
    return np.concatenate([coop, tip, np.zeros((2, 10, 4))])


def tolerant(n, G, rng, p0=0.06):
    """Groups that ignore single zeros: round 1 with some zeros, then everyone keeps round-1 values."""
    c1 = np.where(rng.random((G, n)) < p0, 0.0, 10.0)
    return np.repeat(c1[:, None, :], 10, axis=1)


def frozen_from(world, cards=("boston_minimal",), model="gpt"):
    return pb.build_frozen({(model, c): world for c in cards}, {(model, c): MATCHER for c in cards}, {"run": "synthetic"})


class FakeUnits(pc.UnitsN):
    def __init__(self, arrays: dict, n: int):
        super().__init__([], n=n)
        for (m, c), G in arrays.items():
            for k, g in enumerate(G):
                self.groups[f"{m}|{c}|{k}"] = {"model": m, "card": c, "c": g, "capped": False, "length": False,
                                               "comp_full": True}


class States(unittest.TestCase):
    def test_n4_states_equal_stage1(self):
        rng = np.random.default_rng(0)
        prev = rng.choice([0, 3, 10, 12, 20], size=(300, 4)).astype(float)
        own, mb, zero = pc.bins_n(prev)
        ref = pr.states_vec(prev, 2)
        self.assertEqual([(a, b, c) for a, b, c, _ in ref],
                         list(zip(own.ravel().tolist(), mb.ravel().tolist(), zero.ravel().tolist())))

    def test_r0_equals_stage1_at_n4(self):
        rng = np.random.default_rng(1)
        c1 = rng.choice([0, 5, 10, 20], size=(20, 4)).astype(float)
        f = np.array([0.5, 4.0, 9.0, 12.5, 17.0])
        self.assertTrue(np.allclose(pc.simulate_r0(f, c1), pb.simulate_R0(f, c1, 10)))

    def test_n_others_mean_and_zero(self):
        _, mb, zero = pc.bins_n(np.array([[0.0] + [10.0] * 15]))
        self.assertEqual((mb[0, 0], zero[0, 0]), (3, 0))           # the free rider sees 15 tens
        self.assertEqual((mb[0, 1], zero[0, 1]), (2, 1))           # a ten sees mean 9.33 and a zero


class ForecastAndHypotheses(unittest.TestCase):
    def setUp(self):
        self.fz = frozen_from(trigger_world())
        self.sizes = {"gpt": (4, 16)}
        self.cards = ("boston_minimal",)

    def test_trigger_world_collapses_more_in_large_groups(self):
        fc = pc.forecast(self.fz, s=2000, sizes=self.sizes, cards=self.cards)["gpt"]["mean_over_cards"]
        self.assertGreater(fc["16"]["rule"]["collapse_r8"], fc["4"]["rule"]["collapse_r8"] + 0.2)
        self.assertAlmostEqual(fc["16"]["R0"]["collapse_r8_minus_n4"], 0.0, delta=0.05)   # matcher: no size effect

    def _units(self, gen):
        rng = np.random.default_rng(5)
        rule = pb.rules_for(self.fz, "gpt", "boston_minimal", "R3")
        units = {}
        for n in (4, 16):
            if gen == "rule":
                pool = np.array(self.fz["models"]["gpt"]["cells"]["boston_minimal"]["round1"], float).ravel()
                G = pc.simulate_rule(rule, rng.choice(pool, size=(80, n)), rng)
            else:
                G = tolerant(n, 80, rng) if n == 16 else pc.simulate_rule(
                    rule, rng.choice(np.array(self.fz["models"]["gpt"]["cells"]["boston_minimal"]["round1"], float).ravel(),
                                     size=(80, n)), rng)
            units[n] = FakeUnits({("gpt", "boston_minimal"): G}, n)
        return units

    def test_rule_world_labels(self):
        res = pc.analyse(self.fz, self._units("rule"), s=100, n_boot=400, sizes=self.sizes, cards=self.cards)
        self.assertEqual(res["C_H1"]["gpt"]["label"], "artış")
        self.assertTrue(res["C_H2"]["gpt"]["family"]["16"]["label"].startswith("tahmin tuttu"))
        self.assertEqual(res["C_H3"]["gpt"]["16"]["label"], "yeniden üretiyor")

    def test_tolerant_world_deviates(self):
        res = pc.analyse(self.fz, self._units("tolerant"), s=100, n_boot=400, sizes=self.sizes, cards=self.cards)
        self.assertEqual(res["C_H3"]["gpt"]["16"]["label"], "sapıyor (gerçek daha düşük)")
        self.assertNotEqual(res["C_H1"]["gpt"]["label"], "artış")

    def test_no_change_world(self):
        units = {n: FakeUnits({("gpt", "boston_minimal"): np.full((60, 10, n), 10.0)}, n) for n in (4, 16)}
        res = pc.analyse(self.fz, units, s=50, n_boot=300, sizes=self.sizes, cards=self.cards)
        self.assertEqual(res["C_H1"]["gpt"]["label"], "değişim yok")

    def test_labels(self):
        self.assertEqual(pc.label_size({"ci": [0.05, 0.6]}), "artış")
        self.assertEqual(pc.label_size({"ci": [-0.3, -0.01]}), "azalış")
        self.assertEqual(pc.label_size({"ci": [-0.08, 0.09]}), "değişim yok")
        self.assertEqual(pc.label_size({"ci": [-0.2, 0.3]}), "belirsiz")
        self.assertEqual(pc.label_share({"est": 0.3, "ci": [0.2, 0.4]}), "sapıyor (gerçek daha yüksek)")

    def test_mechanism_counts(self):
        g = np.full((1, 10, 8), 10.0)
        g[0, 0, 0] = 0
        g[0, 1:, :] = 0                                    # everyone answers the zero with 0
        mech = pc.mechanism(g)
        self.assertEqual(mech["zero"]["share_0"], 1.0)
        self.assertEqual(mech["zero"]["n"], 7)


class FramesAndConfigs(unittest.TestCase):
    def test_decision_prompts_identical_and_keys(self):
        v4 = pgg_frames.load_frame(ROOT / "frames" / "abstract_v4.json")
        for n, key in ((8, 40), (16, 68), (32, 128)):
            fr = pgg_frames.load_frame(ROOT / "frames" / f"abstract_v4_n{n}.json")
            p = pgg_game.GameParams(group_size=n)
            self.assertEqual(fr.comprehension_key(p), {"q1": key, "q2": -6})
            rng = np.random.default_rng(n)
            hist = []
            for t in range(1, 10):
                c = [int(x) for x in rng.choice([0, 5, 10, 20], size=n)]
                hist.append(pgg_game.RoundRecord(t, c, pgg_game.project_payoffs(p, c)))
            for t in (1, 2, 10):
                for me in (0, n - 1):
                    self.assertEqual(fr.contribution_messages(p, "N", CARD, hist[:t - 1], me, t),
                                     v4.contribution_messages(p, "N", CARD, hist[:t - 1], me, t))
            user = fr.comprehension_messages(p, CARD)[1]["content"]
            self.assertTrue(user.startswith(v4.rules_text(p, "N") + "\n\n"))
            ref = v4.comprehension_messages(pgg_game.GameParams(), CARD)[1]["content"].split("\n")
            got = user.split("\n")
            q1 = [x for x in got if x.startswith("1. Suppose")][0]
            self.assertEqual(q1.count(","), n - 3)                 # n - 1 values, the last joined by "and"
            self.assertIn(f"the other {n - 1} players", q1)
            self.assertEqual([x for x in got if x.startswith("2. ")], [x for x in ref if x.startswith("2. ")])
            self.assertEqual(got[-1], ref[-1])
            self.assertEqual(fr.data["comprehension"]["questions"][1], v4.data["comprehension"]["questions"][1])
            for k in ("system", "rules", "history", "contribute", "isolated", "response", "player_label", "you_suffix"):
                self.assertEqual(fr.data[k], v4.data[k])

    def test_configs(self):
        for n in (4, 8, 16, 32):
            models = ["mistral", "gpt"] if n < 32 else ["gpt"]
            frame = "abstract_v4" if n == 4 else f"abstract_v4_n{n}"
            for kind in ("smoke", "main"):
                c = json.loads((ROOT / "configs" / f"expC_n{n}_{kind}.json").read_text())
                self.assertEqual(c["params"], {"group_size": n})
                self.assertEqual(c["frames"], {frame: models})
                self.assertEqual(c["frame_files"][frame]["sha256"],
                                 hashlib.sha256((ROOT / c["frame_files"][frame]["path"]).read_bytes()).hexdigest())
                self.assertEqual(c["cards_sha256"], hashlib.sha256((ROOT / c["cards"]).read_bytes()).hexdigest())
                self.assertEqual(c["arms"], ["group"])
                self.assertTrue(c["prereg_approved"])
                if kind == "main":
                    self.assertEqual(c["groups_per_cell_by_model"], {m: {"mistral": 6, "gpt": 12}[m] for m in models})
                    self.assertEqual(len(c["cities"]), 4)
                else:
                    self.assertEqual(c["groups_per_cell_by_model"], {m: 1 for m in models})
                    self.assertEqual(len(c["cities"]), 1)

    def test_units_n_drops_incomplete(self):
        rows = []
        for k, rounds in ((0, 10), (1, 9)):
            for t in range(1, rounds + 1):
                for a in range(1, 9):
                    rows.append({"arm": "group", "unit": f"u{k}", "model_key": "gpt", "card_id": "boston_minimal",
                                 "session_id": f"s{k}", "step": "contribute", "round": t, "agent_id": a,
                                 "contribution": 10.0})
        u = pc.UnitsN(rows, set(), 8)
        self.assertEqual((len(u.groups), u.incomplete), (1, ["u1"]))
        self.assertEqual(u.group_array("gpt", "boston_minimal").shape, (1, 10, 8))


sys.path.insert(0, str(ROOT / "tests"))
from test_pgg_game import CARD_A, EngineTestBase  # noqa: E402


class EngineEightPlayers(EngineTestBase):
    """Mock end-to-end: the engine plays a group of 8 with abstract_v4_n8 and UnitsN reads it."""

    def test_group_of_eight(self):
        path = ROOT / "frames" / "abstract_v4_n8.json"
        locked = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        rows = self.run_engine(run="c8", cards=[CARD_A], models={"gpt": "openai/gpt-6-luna"},
                               frames={"abstract_v4_n8": ["gpt"]}, frame_files={"abstract_v4_n8": locked},
                               comprehension=True, params=pgg_game.GameParams(group_size=8), arms=("group",),
                               groups_per_cell=1)
        comp = [r for r in rows if r["step"] == "comprehension"]
        self.assertEqual(len(comp), 8)
        self.assertTrue(all(r["comp_q1_correct"] is False and r["comp_q2_correct"] for r in comp))  # fake says 28
        u = pc.UnitsN(rows, set(), 8)
        self.assertEqual(u.group_array("gpt", "cityA").shape, (1, 10, 8))
        user = [c for c in self.api.calls if '"q1": {"type": "integer"' in c["messages"][-1]["content"]][0]
        self.assertIn("the other 7 players contribute 4, 12, 16, 0, 8, 20 and 2 points",
                      user["messages"][-1]["content"])


if __name__ == "__main__":
    unittest.main()
