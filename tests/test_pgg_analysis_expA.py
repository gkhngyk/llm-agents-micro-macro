"""pgg_analysis_expA on synthetic data with known effects (prereg_expA §4, §8 item 5)."""

import os
import unittest

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis_expA as ax  # noqa: E402
from llm_client import stable_seed  # noqa: E402

N_BOOT = 1000


def rows_for(traj, models=("gpt",), g=8, noise=0.0, seed=0, comp_ok=True):
    """traj(model, card, arm, group, round, agent) -> contribution."""
    rng = np.random.default_rng(seed)
    out = []
    for m in models:
        for card in ax.CARDS:
            for arm, frame in ax.ARMS.items():
                for k in range(g):
                    unit = f"{m}|{card}|minimal|N|group|{k}|{frame}"
                    sess = f"s-{m}-{card}-{frame}-{k:03d}"
                    for a in range(1, 5):
                        out.append({"model_key": m, "card_id": card, "arm": "group", "unit": unit,
                                    "session_id": sess, "step": "comprehension", "round": 1, "agent_id": a,
                                    "comp_q1_correct": comp_ok, "comp_q2_correct": True, "comp_missing": False})
                    for t in range(1, 11):
                        for a in range(1, 5):
                            c = traj(m, card, arm, k, t, a) + noise * rng.standard_normal()
                            out.append({"model_key": m, "card_id": card, "arm": "group", "unit": unit,
                                        "session_id": sess, "step": "contribute", "round": t, "agent_id": a,
                                        "contribution": float(np.clip(round(c), 0, 20))})
    return out


class Primary(unittest.TestCase):
    def test_visibility_speeds_collapse(self):
        # B decays from 10 by 1 per round, T stays at 10: r2-9 differs by ~4.5
        rows = rows_for(lambda m, c, arm, k, t, a: 10 - (t - 1) if arm == "B" else 10, noise=1.0, seed=1)
        r = ax.run_analysis(rows, set(), ("gpt",), N_BOOT)["main"]
        self.assertEqual(r["A_H1"]["gpt"]["label"], "görünürlük çöküşü hızlandırır")
        self.assertAlmostEqual(r["A_H1"]["gpt"]["est"], 4.5, delta=0.6)
        self.assertFalse(r["balance_round1"]["gpt"]["flag"])

    def test_reverse(self):
        rows = rows_for(lambda m, c, arm, k, t, a: 10 - (t - 1) if arm == "T" else 10, noise=1.0, seed=2)
        r = ax.run_analysis(rows, set(), ("gpt",), N_BOOT)["main"]
        self.assertEqual(r["A_H1"]["gpt"]["label"], "görünürlük işbirliğini destekler")

    def test_no_difference_equivalent(self):
        rows = rows_for(lambda m, c, arm, k, t, a: 10, noise=1.0, seed=3)
        r = ax.run_analysis(rows, set(), ("gpt",), N_BOOT)["main"]
        self.assertEqual(r["A_H1"]["gpt"]["label"], "fark yok — eşdeğerlik sağlandı")

    def test_rounds_1_and_10_do_not_count(self):
        # arms differ only in round 1 and round 10: r2-9 identical, the balance flag fires
        rows = rows_for(lambda m, c, arm, k, t, a: 20 if (arm == "T" and t in (1, 10)) else 10)
        r = ax.run_analysis(rows, set(), ("gpt",), N_BOOT)["main"]
        self.assertAlmostEqual(r["A_H1"]["gpt"]["est"], 0.0)
        self.assertTrue(r["balance_round1"]["gpt"]["flag"])

    def test_seed(self):
        self.assertEqual(ax.seed("A_H1", "gpt"), stable_seed("pgg-expA-analysis", "A_H1", "gpt"))


class Mechanism(unittest.TestCase):
    def test_visible_free_rider(self):
        # agent 4 always gives 0; agents 1-3 give 10 in round 1. In B they quit after
        # seeing the 0 (they give 0 from round 2), in T they keep 10. Event decisions:
        # round 2, own 10, others' mean (10+10+0)/3 = 6.67 >= 5, one of them 0.
        def traj(m, c, arm, k, t, a):
            if a == 4:
                return 0
            return 10 if (t == 1 or arm == "T") else 0
        r = ax.run_analysis(rows_for(traj), set(), ("gpt",), N_BOOT)["main"]
        h2 = r["A_H2"]["gpt"]
        self.assertEqual((h2["p_T"], h2["p_B"]), (0.0, 1.0))
        self.assertEqual(h2["label"], "mekanizma destekleniyor")

    def test_no_events_undetermined(self):
        rows = rows_for(lambda m, c, arm, k, t, a: 10)        # nobody ever gives 0
        r = ax.run_analysis(rows, set(), ("gpt",), N_BOOT)["main"]
        self.assertEqual(r["A_H2"]["gpt"]["label"], "belirlenemedi")
        self.assertEqual(r["A_H2_control"]["gpt"]["est"], 0.0)

    def test_event_definition(self):
        c = np.zeros((1, 10, 4))
        c[0, 0] = [10, 10, 0, 10]       # round 1: agent 3 gives 0
        c[0, 1] = [0, 10, 0, 10]        # round 2: agent 1 quits, agents 2 and 4 stay
        s = ax.event_shares(c, True)
        # round-2 events: agents 1, 2, 4 (own 10, others mean 6.67, a 0 among others): 1 of 3 quits;
        # round-3 events from round 2: agents 2 and 4 (others 0,0,10 -> mean 3.33 < 5): none
        self.assertAlmostEqual(float(s[0]), 1 / 3)


class Sensitivity(unittest.TestCase):
    def test_comp_full_excludes(self):
        rows = rows_for(lambda m, c, arm, k, t, a: 10, comp_ok=False)
        r = ax.run_analysis(rows, set(), ("gpt",), 200)
        self.assertEqual(r["sensitivity"]["comp_full"]["excluded_groups"], 64)
        self.assertEqual(r["sensitivity"]["comp_full"]["labels"]["gpt"]["A_H1"], "belirlenemedi")


if __name__ == "__main__":
    unittest.main()
