"""prereg_dyn: dynamics of the learned rule on synthetic worlds with known answers. No API calls."""

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis_dynamics as pd  # noqa: E402
import pgg_analysis_expB as pb  # noqa: E402

MATCHER = {x: np.array([float(x)] * 4) for x in (0, 5, 10, 15, 20)}


def bistable_world():
    """All-10 groups stay at 10, all-0 groups stay at 0, one 0 among tens -> everyone 0."""
    coop = np.full((4, 10, 4), 10.0)
    zero = np.zeros((4, 10, 4))
    tip = np.zeros((4, 10, 4))
    tip[:, 0, 1:] = 10
    return np.concatenate([coop, zero, tip])


def frozen(world):
    return pb.build_frozen({("gpt", "a_minimal"): world}, {("gpt", "a_minimal"): MATCHER}, {"run": "synthetic"})


class RuleProperties(unittest.TestCase):
    def setUp(self):
        self.fz = frozen(bistable_world())
        self.rule = pd.model_rule(self.fz, "gpt")

    def test_persistence(self):
        p = pd.persistence(self.rule)
        self.assertEqual(p["Z"]["p"], 1.0)
        self.assertEqual(p["C10"]["p"], 1.0)
        self.assertIsNone(p["Z"]["holding_rounds"])
        self.assertEqual(p["Z"]["source"]["depth"], 0)

    def test_lifetime_censored(self):
        life = pd.lifetime(self.rule, 10, np.random.default_rng(1), s=50, rounds=30)
        self.assertEqual(life["median"], 30.0)
        self.assertEqual(life["censored_share"], 1.0)

    def test_one_free_rider_tips(self):
        tip = pd.tipping(self.rule, np.random.default_rng(2), s=50)
        self.assertEqual(tip["by_k"][0]["r13"]["coop"], 1.0)
        self.assertEqual(tip["by_k"][1]["r13"]["collapse"], 1.0)
        self.assertEqual(tip["by_k"][4]["r13"]["collapse"], 1.0)
        self.assertEqual(tip["k_star"], 1)

    def test_fragile_world(self):
        """All-10 groups fall to 0 in round 3: lifetime from all-10 is 1 round."""
        w = np.full((4, 10, 4), 10.0)
        w[:, 2:, :] = 0
        rule = pd.model_rule(frozen(w), "gpt")
        life = pd.lifetime(rule, 10, np.random.default_rng(3), s=200, rounds=20)
        self.assertLess(life["median"], 4)


class R0(unittest.TestCase):
    def test_fixed_points(self):
        two = pd.fixed_points([0, 0, 10, 20, 20])
        self.assertEqual([(p["x"], p["stable"]) for p in two["points"]], [(0.0, True), (10.0, False), (20.0, True)])
        self.assertEqual(two["n_stable"], 2)
        one = pd.fixed_points([5, 7, 9, 11, 13])
        self.assertEqual(one["n_stable"], 1)
        self.assertAlmostEqual(one["points"][0]["x"], 5 / 0.6)
        self.assertEqual(pd.fixed_points([0, 5, 10, 15, 20])["continua"], [[0.0, 5.0], [5.0, 10.0], [10.0, 15.0], [15.0, 20.0]])

    def test_r0_tipping(self):
        half = np.array([0, 2.5, 5, 7.5, 10])            # f(x) = x / 2: everything decays to 0
        self.assertEqual(pd.r0_tipping(half)["k_star"], 0)
        self.assertIsNone(pd.r0_tipping(np.array([10.0] * 5))["k_star"])


class Observed(unittest.TestCase):
    def test_persistence_and_survival(self):
        G = bistable_world()
        op = pd.observed_persistence(G, 8)
        self.assertEqual(op["Z"]["stay_share"], 1.0)
        self.assertEqual(op["C10"]["n_from"], 4 * 7)
        st = pd.observed_stats(G, 8)
        self.assertEqual(st["surv"][:, -1].tolist(), [1.0] * 4 + [0.0] * 8)
        self.assertEqual(st["recovery"]["n"], 8)
        self.assertEqual(st["recovery"]["to_coop"], 0.0)

    def test_recovery_counted(self):
        m = np.array([[10, 0, 0, 10, 10, 10, 10, 10.0]])
        r = pd.recovery(m, 8)
        self.assertEqual((r["n"], r["to_coop"], r["leave_collapse"]), (1, 1.0, 1.0))

    def test_dataset_reproduces_in_sample(self):
        fz = frozen(bistable_world())
        cells = {"a_minimal": np.concatenate([bistable_world(), bistable_world()])}   # 8 groups per type
        rules = {"a_minimal": pb.rules_for(fz, "gpt", "a_minimal", "R3")}
        r0 = {"a_minimal": fz["models"]["gpt"]["cells"]["a_minimal"]["iso_f"]}
        out = pd.analyse_dataset("t", cells, 8, rules, r0, s=40, n_boot=200)
        self.assertEqual(out["D3a"]["main"]["collapse"]["observed"]["est"], 8 / 12)
        self.assertEqual(out["D3a"]["main"]["collapse"]["label"], "yeniden üretiyor")
        self.assertEqual((out["D2_by_k1"][1]["n"], out["D2_by_k1"][1]["rule"]), (8, 1.0))
        self.assertEqual(out["D2_by_k1"][2], {"n": 0})
        self.assertEqual(out["D3a"]["main"]["collapse"]["R0"], 4 / 12)   # matcher: the tipping groups stay at 7.5
        self.assertEqual(out["D3b"]["clusters"]["10,10,10,10"]["coop"], 1.0)

    def test_band_label(self):
        self.assertEqual(pd.band_label({"est": 0.05, "ci": [-0.1, 0.12]}), "yeniden üretiyor")
        self.assertEqual(pd.band_label({"est": 0.3, "ci": [0.2, 0.4]}), "sapıyor")
        self.assertEqual(pd.band_label({"est": 0.1, "ci": [-0.1, 0.3]}), "belirsiz")


class Loaders(unittest.TestCase):
    def test_human_loader(self):
        hdr = "sessionid,groupid,mgroupid,subjectid,p,secseq,city,period,senderscontribution,otherscontribution"
        lines = ['"title line",,,', hdr]
        for t in range(1, 11):
            for s in range(1, 5):
                for _ in range(3):
                    lines.append(f"S1,1,1,{s},N-experiment,0,Boston,{t},{s * t % 21},0")
                    lines.append(f"S1,1,1,{s},P-experiment,1,Boston,{t},20,0")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "h.csv"
            p.write_bytes(("﻿" + "\r".join(lines)).encode("utf-8"))
            h = pd.load_human(p)
        self.assertEqual(h["Boston"].shape, (1, 10, 4))
        self.assertEqual(h["Boston"][0, 1].tolist(), [2.0, 4.0, 6.0, 8.0])

    def test_frozen_sha_locked(self):
        root = Path(pd.__file__).resolve().parent
        with self.assertRaises(ValueError):
            pb.load_frozen(root / pd.FROZEN, "0" * 64)
        self.assertIn("models", pb.load_frozen(root / pd.FROZEN, pd.FROZEN_SHA))


class Labels(unittest.TestCase):
    def test_bistable_world_labels(self):
        fz = frozen(bistable_world())
        w = np.concatenate([bistable_world(), bistable_world()])
        rules = {"a_minimal": pb.rules_for(fz, "gpt", "a_minimal", "R3")}
        r0 = {"a_minimal": fz["models"]["gpt"]["cells"]["a_minimal"]["iso_f"]}
        ds = {d: pd.analyse_dataset(d, {"a_minimal": w}, 8, rules, r0, s=40, n_boot=200) for d in ("AB", "EB")}
        mr = pd.rule_properties(pd.model_rule(fz, "gpt"), ("t",), s=50)
        f = np.array(r0["a_minimal"])
        lab = pd.labels(mr, ds, {"fixed_points": pd.fixed_points(f), "D2": pd.r0_tipping(f)})
        self.assertEqual(lab["1_trap"], "çöküş emici (tuzak)")
        self.assertEqual(lab["2_coop"], "yarı kararlı işbirliği (kilitlenme)")
        self.assertEqual(lab["3_bistable"], "iki çekici")
        self.assertEqual(lab["4_tipping"], "tek bedavacı grubu deviriyor")
        self.assertEqual(lab["5_R0"], "izole kural makro yapıyı nitel olarak yanlış öngörüyor")   # matcher: a continuum


if __name__ == "__main__":
    unittest.main()
