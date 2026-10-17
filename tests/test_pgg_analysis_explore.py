"""pgg_analysis_explore (prereg F.12, exploratory) on synthetic data."""

import os
import unittest

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis as pa  # noqa: E402
import pgg_analysis_explore as px  # noqa: E402
try:  # run from the repo root (-m unittest tests.x) or from tests/ (discover -s tests)
    from tests.test_pgg_analysis import make_rows, PLANNED  # noqa: E402
except ImportError:
    from test_pgg_analysis import make_rows, PLANNED  # noqa: E402


class Windows(unittest.TestCase):
    def test_full_window_reproduces_main_h4(self):
        rows = make_rows(lambda m, c: 10.0, lambda m, c: -0.5, iso=lambda m, c, x: 0.8 * x + 1,
                         noise=1.0, seed=7, models=("gpt",))
        units = pa.Units(rows)
        main = pa.analyse(units, PLANNED, 300, ("gpt",))["H4"]["gpt"]
        ex = px.explore(units, 300, ("gpt",))["gpt"]["2-10"]
        for cid in main:
            self.assertAlmostEqual(main[cid]["est"], ex[cid]["est"], places=12)

    def test_end_game_only_drop_disappears_in_2_8(self):
        # matcher in isolation, groups flat at 10 except a collapse in rounds 9-10
        rows = make_rows(lambda m, c: 10.0, iso=lambda m, c, x: float(x), models=("gpt",))
        for r in rows:
            if r["step"] == "contribute" and r["round"] in (9, 10):
                r["contribution"] = 0.0
        res = px.explore(pa.Units(rows), 500, ("gpt",))["gpt"]
        t_full, t_28 = res["2-10"]["boston_value"], res["2-8"]["boston_value"]
        self.assertAlmostEqual(t_full["est"], -20 / 9, places=9)     # 2 of 9 rounds at 0 instead of 10
        self.assertEqual(t_full["label"], "aşağı")
        self.assertAlmostEqual(t_28["est"], 0.0, places=9)
        self.assertTrue(t_28["label"].startswith("uyumlu"))

    def test_summary_counts(self):
        rows = make_rows(lambda m, c: 10.0, iso=lambda m, c, x: float(x), models=("gpt",))
        s = px.summary(px.explore(pa.Units(rows), 200, ("gpt",)))
        self.assertEqual(s["gpt"]["2-8"]["uyumlu"], 12)
        self.assertEqual(s["gpt"]["2-8"]["n_negative"], 0)


if __name__ == "__main__":
    unittest.main()
