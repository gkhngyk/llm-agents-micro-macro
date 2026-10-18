"""pgg_analysis_rules (prereg_main F.14, exploratory) on synthetic data."""

import os
import unittest

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis_rules as pr  # noqa: E402


def zero_trigger_world(g=8, p_zero=0.25, seed=0):
    """Round 1: each agent gives 0 with prob p_zero, else 10. Later: 0 if one of the others
    gave 0 in the previous round, else 10 (a 'visible free rider' rule)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((g, 10, 4))
    for k in range(g):
        out[k, 0] = np.where(rng.random(4) < p_zero, 0, 10)
        for t in range(1, 10):
            prev = out[k, t - 1]
            for i in range(4):
                out[k, t, i] = 0 if np.delete(prev, i).min() == 0 else 10
    return out


MATCHER = {x: np.array([float(x)] * 4) for x in (0, 5, 10, 15, 20)}


class Features(unittest.TestCase):
    def test_bins(self):
        self.assertEqual([pr.own_bin(x) for x in (0, 5, 10, 15, 20)], [0, 1, 2, 3, 4])
        self.assertEqual([pr.mean_bin(x) for x in (0, 3.3, 6.67, 10, 13.3, 15, 20)], [0, 1, 2, 3, 4, 5, 5])
        self.assertEqual([pr.round_bin(t) for t in (2, 8, 9, 10)], [0, 0, 1, 2])

    def test_vector_states_equal_scalar(self):
        rng = np.random.default_rng(1)
        prev = rng.choice([0, 5, 10, 12, 20], size=(50, 4)).astype(float)
        vec = pr.states_vec(prev, 9)
        scal = [pr.state(prev[k], i, 9) for k in range(50) for i in range(4)]
        self.assertEqual(vec, scal)

    def test_decisions_and_backoff(self):
        self.assertEqual(len(pr.decisions(zero_trigger_world(1)[0])), 36)
        self.assertEqual(pr.backoff_order("R3"), [(0, 1, 2, 3), (0, 1, 2), (0, 1), (1,)])
        self.assertEqual(pr.backoff_order("R1"), [(0, 1), (1,)])

    def test_unseen_state_backs_off(self):
        tab = pr.Table(pr.backoff_order("R2"))
        tab.add([((2, 3, 0, 0), 10)])
        r = pr.Rule("R2", tab, pr.Table(pr.backoff_order("R2")))
        d = r.dist((4, 3, 1, 0))                 # unseen own/zero -> mean bin 3 only
        self.assertEqual(int(np.argmax(d)), 10)
        self.assertIn((2, "cell"), r.used)


class Recovery(unittest.TestCase):
    def test_logo_closes_gap_with_the_right_state(self):
        groups = {("gpt", "a_minimal"): zero_trigger_world(seed=2), ("gpt", "b_minimal"): zero_trigger_world(seed=3)}
        iso = {k: MATCHER for k in groups}
        res = pr.evaluate_logo(groups, iso, ("gpt",), n_boot=300, s=40)["gpt"]
        for c in ("a_minimal", "b_minimal"):
            r0 = res["R0"]["2-10"]["cells"][c]["est"]
            r2 = res["R2"]["2-10"]["cells"][c]["est"]
            self.assertLess(r0, -2, c)                    # matching simulation misses the collapse
            self.assertLess(abs(r2), 0.5, c)              # the zero-indicator rule recovers it
        self.assertLess(res["R2"]["mean_rmse"], res["R0"]["mean_rmse"])

    def test_new_data(self):
        train = {("gpt", "a_minimal"): zero_trigger_world(seed=4)}
        test = {("gpt", "a_minimal"): zero_trigger_world(seed=5)}
        res = pr.evaluate_new_data(train, {("gpt", "a_minimal"): MATCHER}, test, ("gpt",), n_boot=300, s=40)["gpt"]
        self.assertLess(abs(res["R2"]["2-10"]["cells"]["a_minimal"]["est"]), 0.5)
        self.assertLess(res["R0"]["2-10"]["cells"]["a_minimal"]["est"], -2)

    def test_deterministic(self):
        groups = {("gpt", "a_minimal"): zero_trigger_world(g=4, seed=6)}
        iso = {k: MATCHER for k in groups}
        a = pr.evaluate_logo(groups, iso, ("gpt",), n_boot=100, s=20)
        b = pr.evaluate_logo(groups, iso, ("gpt",), n_boot=100, s=20)
        self.assertEqual(a["gpt"]["R3"]["2-10"]["cells"]["a_minimal"]["est"],
                         b["gpt"]["R3"]["2-10"]["cells"]["a_minimal"]["est"])


if __name__ == "__main__":
    unittest.main()
