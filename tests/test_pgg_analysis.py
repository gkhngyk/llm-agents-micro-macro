"""pgg_analysis on synthetic data with known effects (prereg_main §7.6).

No stage-1 data: every row here is generated. The 0b smoke test (last class)
only checks that the loader and the analysis run on a real run directory; it
asserts nothing about its numbers and is skipped when the run is absent.
"""

import os
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENROUTER_API_KEY", "offline-test-no-calls")
import pgg_analysis as pa  # noqa: E402
from llm_client import stable_seed  # noqa: E402

N_BOOT = 2000
G = 8
PLANNED = {m: (G, 4) for m in pa.MODELS}


def make_rows(level, decay=None, iso=None, models=pa.MODELS, g=G, noise=0.0, seed=0,
              flags=None, skip_cells=()):
    """Synthetic rows. level(model, card) -> round-1 mean; decay(model, card) -> per-round
    change; iso(model, card, x) -> isolated answer. flags {(model, card, group): {field: v}}."""
    decay = decay or (lambda m, c: 0.0)
    iso = iso or (lambda m, c, x: float(x))
    flags = flags or {}
    rng = np.random.default_rng(seed)
    rows = []
    for m in models:
        for city in pa.CITIES:
            for style in pa.STYLES:
                cid = pa.card_id(city, style)
                if (m, cid) in skip_cells:
                    continue
                for k in range(g):
                    unit = f"{m}|{cid}|{style}|N|group|{k}|abstract_v4"
                    sess = f"s-{m}-{cid}-group-{k:03d}"
                    extra = flags.get((m, cid, k), {})
                    for a in range(1, 5):
                        rows.append({"model_key": m, "card_id": cid, "arm": "group", "unit": unit,
                                     "session_id": sess, "step": "comprehension", "round": 1,
                                     "agent_id": a, "comp_q1_correct": True, "comp_q2_correct": True,
                                     "comp_missing": False, **{x: v for x, v in extra.items()
                                                               if x.startswith("comp")}})
                    for t in range(1, 11):
                        for a in range(1, 5):
                            c = level(m, cid) + decay(m, cid) * (t - 1) + noise * rng.standard_normal()
                            rows.append({"model_key": m, "card_id": cid, "arm": "group", "unit": unit,
                                         "session_id": sess, "step": "contribute", "round": t,
                                         "agent_id": a, "contribution": float(np.clip(c, 0, 20)),
                                         "reasoning_capped": bool(extra.get("capped") and t == 3 and a == 1),
                                         "reused": bool(extra.get("reused") and t == 2 and a == 2)})
                for k in range(4):
                    unit = f"{m}|{cid}|{style}|N|isolated|{k}|abstract_v4"
                    sess = f"s-{m}-{cid}-isolated-{k:03d}"
                    rows.append({"model_key": m, "card_id": cid, "arm": "isolated", "unit": unit,
                                 "session_id": sess, "step": "comprehension", "round": None,
                                 "agent_id": 1, "comp_q1_correct": True, "comp_q2_correct": True,
                                 "comp_missing": False})
                    for x in pa.POINTS:
                        rows.append({"model_key": m, "card_id": cid, "arm": "isolated", "unit": unit,
                                     "session_id": sess, "step": "isolated", "round": None,
                                     "agent_id": 1, "others_mean": x,
                                     "contribution": float(np.clip(iso(m, cid, x), 0, 20))})
    return rows


def city(cid):
    return cid.split("_")[0]


def style(cid):
    return cid.split("_")[1]


class Basics(unittest.TestCase):
    def test_holm(self):
        adj = pa.holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.20})
        self.assertAlmostEqual(adj["a"], 0.04)
        self.assertAlmostEqual(adj["c"], 0.09)
        self.assertAlmostEqual(adj["b"], 0.09)     # monotone: max(0.08, 0.09)
        self.assertAlmostEqual(adj["d"], 0.20)

    def test_seed_is_llm_client_stable_seed(self):
        self.assertEqual(pa.seed("H1", "gpt", "copenhagen-athens"),
                         stable_seed("pgg-main-s1-analysis", "H1", "gpt", "copenhagen-athens"))

    def test_boot_p(self):
        self.assertEqual(pa.boot_p(np.array([1.0, 2.0, 3.0])), 0.0)
        self.assertEqual(pa.boot_p(np.array([-1.0, 1.0])), 1.0)

    def test_pairs_follow_herrmann(self):
        for a, b in pa.PAIRS:
            self.assertGreater(pa.HERRMANN_R1_10[a], pa.HERRMANN_R1_10[b])

    def test_interp_and_simulation(self):
        f = np.array([0.0, 5.0, 10.0, 15.0, 20.0])            # perfect matcher
        traj = pa.simulate(f, np.array([8.0, 8.0, 8.0, 8.0]))
        self.assertTrue(np.allclose(traj, 8.0))
        f2 = np.array([2.0, 2.0, 2.0, 2.0, 2.0])               # constant
        traj = pa.simulate(f2, np.array([20.0, 0.0, 10.0, 5.0]))
        self.assertTrue(np.allclose(traj[1:], 2.0))
        z = pa._interp(np.array([7.5]), np.array(pa.POINTS, float), np.array([0., 10., 20., 20., 20.]))
        self.assertAlmostEqual(float(z[0]), 15.0)

    def test_e2a_label_field(self):
        self.assertEqual(pa.match_terms("A Public-Goods game", pa.DICT_I), ["public good"])
        self.assertEqual(pa.match_terms("this is an experiment", pa.E2A_SETS["i_haric"]), [])
        self.assertEqual(pa.match_terms("this is an experiment", pa.E2A_SETS["i_dahil"]), ["experiment"])
        self.assertEqual(pa.match_terms("nasheez", pa.DICT_II), [])
        row = {"model_key": "gpt", "rationale": "fair", "reasoning": "Nash equilibrium"}
        self.assertEqual(pa.e2a_label_text(row), "fair")          # GPT: rationale only
        row["model_key"] = "deepseek"
        self.assertIn("Nash", pa.e2a_label_text(row))


class Directions(unittest.TestCase):
    """H1 / H2 labels with known cell differences."""

    @classmethod
    def setUpClass(cls):
        human = {"copenhagen": 14, "boston": 11, "riyadh": 8, "athens": 5}

        def level(m, cid):
            c, s = city(cid), style(cid)
            if s == "value":
                return human[c] if m != "mistral" else 19 - human[c]   # Mistral reversed
            if s == "factual":
                return 10.0                                           # no difference
            return 10.0
        cls.res = pa.run_analysis(make_rows(level, noise=1.0, seed=1), set(), PLANNED, N_BOOT)
        cls.main = cls.res["main"]

    def test_h1_human_direction(self):
        for pair in ("copenhagen-athens", "copenhagen-riyadh", "boston-athens", "copenhagen-boston",
                     "boston-riyadh", "riyadh-athens"):
            self.assertEqual(self.main["H1"]["deepseek"][pair]["label"], "insan yönü", pair)
            self.assertEqual(self.main["H1"]["mistral"][pair]["label"], "ters yön", pair)

    def test_h2_no_difference_is_equivalent(self):
        for pair, t in self.main["H2"]["gpt"].items():
            self.assertTrue(t["label"].startswith("fark yok"), pair)
            self.assertEqual(t["label"], "fark yok — eşdeğerlik sağlandı", pair)

    def test_holm_applied(self):
        t = self.main["H1"]["gpt"]["copenhagen-athens"]
        self.assertGreaterEqual(t["p_holm"], t["p"])

    def test_h5(self):
        h1 = self.main["H5"]["H1"]
        self.assertEqual(h1["copenhagen-athens"]["label"], "farklı")    # Mistral reversed
        self.assertEqual(self.main["H5"]["H3"]["factual:copenhagen-athens"]["label"], "aynı")

    def test_rank_summary(self):
        r = self.main["descriptive"]["deepseek"]["rank_vs_herrmann"]["value"]
        self.assertEqual(r["order"], ["copenhagen", "boston", "riyadh", "athens"])
        self.assertAlmostEqual(r["spearman"], 1.0)

    def test_deterministic(self):
        human = {"copenhagen": 14, "boston": 11, "riyadh": 8, "athens": 5}
        rows = make_rows(lambda m, c: human[city(c)] if style(c) == "value" else 10.0, noise=1.0, seed=1,
                         models=("gpt",))
        a = pa.run_analysis(rows, set(), PLANNED, 500, ("gpt",))
        b = pa.run_analysis(rows, set(), PLANNED, 500, ("gpt",))
        self.assertEqual(a["main"]["H1"]["gpt"]["boston-riyadh"]["ci"],
                         b["main"]["H1"]["gpt"]["boston-riyadh"]["ci"])


class Interaction(unittest.TestCase):
    """H3: grows / fades / sign flip / preserved."""

    def run_one(self, level, decay):
        rows = make_rows(level, decay, noise=0.5, seed=2, models=("deepseek",))
        return pa.run_analysis(rows, set(), PLANNED, N_BOOT, ("deepseek",))["main"]["H3"]["deepseek"]

    def test_grows(self):
        # copenhagen_value starts 2 above athens_value and the gap widens by 1 per round
        h3 = self.run_one(lambda m, c: 11.0 if c == "copenhagen_value" else 9.0 if c == "athens_value" else 10.0,
                          lambda m, c: 0.5 if c == "copenhagen_value" else -0.5 if c == "athens_value" else 0.0)
        self.assertEqual(h3["value:copenhagen-athens"]["label"], "büyür")
        self.assertEqual(h3["value:boston-riyadh"]["label"], "korunur — eşdeğerlik sağlandı")

    def test_fades(self):
        h3 = self.run_one(lambda m, c: 15.0 if c == "copenhagen_value" else 5.0 if c == "athens_value" else 10.0,
                          lambda m, c: -0.55 if c == "copenhagen_value" else 0.55 if c == "athens_value" else 0.0)
        self.assertEqual(h3["value:copenhagen-athens"]["label"], "söner")

    def test_sign_flip(self):
        h3 = self.run_one(lambda m, c: 14.0 if c == "copenhagen_factual" else 6.0 if c == "athens_factual" else 10.0,
                          lambda m, c: -0.9 if c == "copenhagen_factual" else 0.9 if c == "athens_factual" else 0.0)
        # D(1) = 8, D(10) = -8.2: |D| barely changes, the sign turns
        self.assertEqual(h3["factual:copenhagen-athens"]["label"], "söner (işaret döndü)")

    def test_born_in_group_and_zero_start(self):
        # identical round 1 (D(1) = 0 exactly), gap opens later: grows, and is noted
        rows = make_rows(lambda m, c: 10.0, lambda m, c: 1.0 if c == "boston_value" else 0.0,
                         noise=0.0, models=("gpt",))
        h3 = pa.run_analysis(rows, set(), PLANNED, N_BOOT, ("gpt",))["main"]["H3"]["gpt"]
        t = h3["value:boston-riyadh"]
        self.assertEqual(t["D1"], 0.0)
        self.assertEqual(t["label"], "büyür")
        self.assertEqual(t["note_born"], "grup içinde doğan fark")


class Flint(unittest.TestCase):
    """H4: group trajectory vs the no-interaction simulation from the isolated arm."""

    def test_matcher_group_is_consistent(self):
        # isolated: perfect matcher; groups: constant 10 -> simulation from round 1 = 10 everywhere
        rows = make_rows(lambda m, c: 10.0, iso=lambda m, c, x: float(x), models=("gpt",))
        h4 = pa.run_analysis(rows, set(), PLANNED, N_BOOT, ("gpt",))["main"]["H4"]["gpt"]
        for cid, t in h4.items():
            self.assertAlmostEqual(t["est"], 0.0, places=9)
            self.assertEqual(t["label"], "uyumlu — eşdeğerlik sağlandı", cid)

    def test_group_above_simulation(self):
        # isolated: everyone gives 2 whatever the others did; groups stay at 10
        rows = make_rows(lambda m, c: 10.0, iso=lambda m, c, x: 2.0, noise=0.5, seed=3, models=("gpt",))
        h4 = pa.run_analysis(rows, set(), PLANNED, N_BOOT, ("gpt",))["main"]["H4"]["gpt"]
        self.assertEqual(h4["boston_value"]["label"], "yukarı")
        self.assertAlmostEqual(h4["boston_value"]["est"], 8.0, delta=0.5)

    def test_group_below_simulation(self):
        rows = make_rows(lambda m, c: 10.0, lambda m, c: -1.0, iso=lambda m, c, x: float(x),
                         noise=0.5, seed=4, models=("gpt",))
        h4 = pa.run_analysis(rows, set(), PLANNED, N_BOOT, ("gpt",))["main"]["H4"]["gpt"]
        self.assertEqual(h4["athens_factual"]["label"], "aşağı")


class Sensitivity(unittest.TestCase):
    def test_exclusions_counted(self):
        flags = {("gpt", "boston_value", 0): {"capped": True},
                 ("gpt", "boston_value", 1): {"reused": True},
                 ("gpt", "riyadh_value", 2): {"comp_q1_correct": False}}
        rows = make_rows(lambda m, c: 10.0, noise=1.0, seed=5, models=("gpt",), flags=flags)
        length = {("s-gpt-athens_value-group-003", None)}
        res = pa.run_analysis(rows, length, PLANNED, 300, ("gpt",))
        s = res["sensitivity"]
        self.assertEqual(s["no_capped"]["excluded"], {"gpt|boston_value|group": 1, "gpt|athens_value|group": 1})
        self.assertEqual(s["no_reused"]["excluded"], {"gpt|boston_value|group": 1})
        self.assertEqual(s["comp_full"]["excluded"], {"gpt|riyadh_value|group": 1})
        self.assertEqual(res["main"]["cells"]["gpt"]["boston_value"]["n_groups"], G)
        self.assertEqual(s["no_capped"]["result"]["cells"]["gpt"]["boston_value"]["n_groups"], G - 1)

    def test_isolated_capped_point_only(self):
        rows = make_rows(lambda m, c: 10.0, models=("gpt",))
        for r in rows:
            if r["arm"] == "isolated" and r["card_id"] == "boston_value" and r.get("others_mean") == 5 \
                    and r["unit"].endswith("|0|abstract_v4"):
                r["reasoning_capped"] = True
        res = pa.run_analysis(rows, set(), PLANNED, 300, ("gpt",))
        self.assertEqual(res["sensitivity"]["no_capped"]["excluded"], {"gpt|boston_value|isolated_points": 1})
        h4 = res["sensitivity"]["no_capped"]["result"]["H4"]["gpt"]["boston_value"]
        self.assertEqual(h4["n_iso"]["5"], 3)


class MissingCells(unittest.TestCase):
    def test_incomplete_cell_and_h5_undetermined(self):
        rows = make_rows(lambda m, c: 10.0, noise=1.0, seed=6)
        drop = {f"mistral|athens_value|value|N|group|{k}|abstract_v4" for k in (0, 1)}
        rows = [r for r in rows if r["unit"] not in drop]
        res = pa.run_analysis(rows, set(), PLANNED, 300)
        self.assertFalse(res["main"]["cells"]["mistral"]["athens_value"]["complete"])
        self.assertEqual(res["main"]["H5"]["H1"]["copenhagen-athens"]["label"], "belirlenemedi")
        self.assertEqual(res["main"]["H1"]["mistral"]["copenhagen-athens"]["n"], [G, G - 2])

    def test_unfinished_group_is_not_a_unit(self):
        rows = make_rows(lambda m, c: 10.0, models=("gpt",))
        cut = "gpt|boston_value|value|N|group|0|abstract_v4"
        rows = [r for r in rows if not (r["unit"] == cut and r["step"] == "contribute" and r["round"] == 10)]
        u = pa.Units(rows)
        self.assertIn(cut, u.incomplete)
        self.assertNotIn(cut, u.groups)

    def test_empty_cell_undetermined(self):
        rows = make_rows(lambda m, c: 10.0, models=("gpt",), skip_cells={("gpt", "athens_value")})
        res = pa.run_analysis(rows, set(), PLANNED, 300, ("gpt",))
        self.assertEqual(res["main"]["H1"]["gpt"]["copenhagen-athens"]["label"], "belirlenemedi")
        self.assertEqual(res["main"]["H4"]["gpt"]["athens_value"]["label"], "belirlenemedi")


RUN_0B = Path("/Users/karbon/Desktop/Veri Bilimi/complexity-prj/orc/data/projects/PublicGoods/"
              "workspace/runs/main_s0b_20261012")


@unittest.skipUnless(RUN_0B.exists(), "0b run directory not on this machine")
class SmokeOn0b(unittest.TestCase):
    """Loader + analysis run end to end on the 0b run (prereg §7.6: 0b data only to see
    that the script works; nothing about its numbers is asserted or reported)."""

    def test_runs(self):
        rows, length, planned, meta = pa.load_run(
            str(Path(pa.ROOT) / "configs" / "main_s0b.json"), "main_s0b_20261012", str(RUN_0B.parent))
        self.assertEqual(len(rows), 1800)
        self.assertEqual(meta["planned_units"], 72)
        self.assertEqual(planned, {m: (1, 1) for m in pa.MODELS})
        res = pa.run_analysis(rows, length, planned, 200)
        self.assertEqual(res["n_units"], {"groups": 36, "schedules": 36, "incomplete": 0})
        for hyp in ("H1", "H2", "H3", "H4"):
            self.assertEqual(set(res["main"][hyp]), set(pa.MODELS))


if __name__ == "__main__":
    unittest.main()
