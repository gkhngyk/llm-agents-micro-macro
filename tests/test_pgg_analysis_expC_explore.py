"""prereg_expC F-C.8 exploratory diagnosis on synthetic data. No API calls."""

import os
import unittest

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis_expB as pb  # noqa: E402
import pgg_analysis_expC as pc  # noqa: E402
import pgg_analysis_expC_explore as px  # noqa: E402

MATCHER = {x: np.array([float(x)] * 4) for x in (0, 5, 10, 15, 20)}


def world():
    coop = np.full((12, 10, 4), 10.0)
    tip = np.zeros((4, 10, 4))
    tip[:, 0, 1:] = 10
    return np.concatenate([coop, tip, np.zeros((2, 10, 4))])


FZ = pb.build_frozen({("gpt", "boston_minimal"): world()}, {("gpt", "boston_minimal"): MATCHER}, {"run": "s"})


class Diagnosis(unittest.TestCase):
    def test_rule_generated_data_has_no_one_step_bias(self):
        rng = np.random.default_rng(3)
        pool = np.array(FZ["models"]["gpt"]["cells"]["boston_minimal"]["round1"], float).ravel()
        G = pc.simulate_rule(pb.rules_for(FZ, "gpt", "boston_minimal", "R3"), rng.choice(pool, size=(60, 8)), rng)
        r = px.t1(FZ, "gpt", {"boston_minimal": G})
        self.assertLess(abs(r["bias_total"]), 0.2)
        self.assertAlmostEqual(sum(r["coarse"].values()), r["bias_total"], places=9)

    def test_persistent_defectors_show_in_t3(self):
        """Defectors who never come back, while the rule (from the world) has no such state seen."""
        G = np.full((10, 10, 8), 10.0)
        G[:, :, 0] = 0                                   # one agent always 0, the others always 10
        out = px.t2_t3(FZ, "gpt", {"boston_minimal": G}, 8)
        self.assertEqual(out["T3"]["est"], 0.0)          # never returns
        self.assertEqual(out["T2"]["est"], 0.0)          # cooperators ignore the zero
        self.assertGreater(out["T2"]["rule_p0"], 0.9)    # the rule says they defect
        self.assertEqual(out["T2"]["by_zero_count"]["1"]["trials"], 10 * 7 * 7)

    def test_decisions_fields(self):
        g = np.full((10, 4), 10.0)
        g[0, 1] = 0
        d = px.decisions(g)
        self.assertEqual(len(d), 9 * 4)
        s, _, k, m = d[0]
        self.assertEqual((s, k), ((2, 2, 1, 0), 1))
        self.assertAlmostEqual(m, 20 / 3)


if __name__ == "__main__":
    unittest.main()
