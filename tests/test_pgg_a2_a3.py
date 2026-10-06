"""Mock tests of A2 (hidden reasoning cap) and A3 (deadlines, counts, timeouts on resume).

(a) reasoning_capped: reasoning_tokens >= max_tokens - 4096 flags a row, the
answer is kept and not re-requested, counted per model / segment / total and
rebuilt from the raw log; (b) elapsed_s, n_transport and n_deadline on rows
and in the summary; (c) an attempt past its deadline through the HTTP layer
llm_client really uses (its client constructor, the openai SDK, httpx and the
_cut_at_deadline hook; only the network is an httpx.MockTransport, because
this sandbox cannot bind a local port): what arrived is logged, a known cost
goes into the budget, an unknown one is counted; (d) request_deadline_s /
stall_timeout_s are compared on --resume. No network, no ../.env.
"""

import contextlib
import io
import json
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_llm_client_logging import MESSAGES, SCHEMA, LoggingTestBase  # noqa: E402
from test_pgg_deadline import _Iter, _until  # noqa: E402
from test_pgg_game import CARD_A, CARD_B, FakeAPI, _payload  # noqa: E402
from test_pgg_guards import CostAPI  # noqa: E402
from test_pgg_resume import GEMINI, ResumeBase, _rows, _tree  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, RunStopped  # noqa: E402


def _usage(reasoning_tokens=None, cost=0.0001):
    usage = {"prompt_tokens": 100, "completion_tokens": 20, "cost": cost}
    if reasoning_tokens is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return usage


def _successes(raw: Path) -> list[dict]:
    return [r for r in map(json.loads, raw.read_text().splitlines()) if "response_parsed" in r
            and r.get("event") is None]


# --------------------------------------------------------------------------
# (a) A2: hidden reasoning cap
# --------------------------------------------------------------------------

class ReasoningCapRule(unittest.TestCase):
    def test_rule_at_the_boundary_and_the_offline_copy(self):
        self.assertEqual(llm_client.REASONING_RESERVE_TOKENS, 4096)
        self.assertEqual(pgg_game.OfflineLLM.REASONING_RESERVE_TOKENS,
                         llm_client.REASONING_RESERVE_TOKENS)
        cases = [(_usage(11904), 16000, True), (_usage(11903), 16000, False),
                 (_usage(15000), 16000, True), (_usage(0), 16000, False),
                 (_usage(11904), 20000, False), (_usage(7904), 12000, True),
                 (_usage(None), 16000, None), (None, 16000, None),
                 ({"completion_tokens_details": {"reasoning_tokens": None}}, 16000, None),
                 ({"completion_tokens_details": {"reasoning_tokens": True}}, 16000, None),
                 ({"completion_tokens_details": None}, 16000, None)]
        for usage, max_tokens, want in cases:
            with self.subTest(usage=usage, max_tokens=max_tokens):
                self.assertIs(llm_client.reasoning_capped(usage, max_tokens), want)
                self.assertIs(pgg_game.OfflineLLM.reasoning_capped(usage, max_tokens), want)


class ReasoningCapRun(ResumeBase):
    @staticmethod
    def tokens(kwargs):
        """contribute: agent 1 at the cap, agent 2 one below; isolated 20: no reasoning_tokens."""
        kind, agent, _rnd, others = FakeAPI.parse(kwargs)
        if kind == "contribute":
            return {1: 11904, 2: 11903}.get(agent, 500)
        return None if others == 20 else 500

    def test_capped_answer_is_flagged_kept_and_counted(self):
        api = CostAPI(usage_fn=lambda kw: _usage(self.tokens(kw)))
        self.use(api)
        Engine(self.rcfg()).run()
        self.assertEqual(len(api.calls), 52)            # nothing re-requested
        rows = _rows(self.results)
        self.assertEqual(len(rows), 52)
        for r in rows:
            want = {11904: True, 11903: False, 500: False, None: None}[self.tokens(
                {"messages": [{"content": ""}, {"content": self._prompt(r)}]})]
            self.assertIs(r["reasoning_capped"], want, r["unit"])
            self.assertEqual(r["max_tokens"], 16000)
            self.assertIsInstance(r["contribution"], int)  # kept as a decision
            self.assertEqual(r["n_invalid"], 0)
        self.assertEqual(sum(r["reasoning_capped"] is True for r in rows), 8)
        # the raw log's success records carry the same flag
        raw = _successes(self.raw)
        self.assertEqual(len(raw), 52)
        self.assertEqual(sum(r["reasoning_capped"] is True for r in raw), 8)
        self.assertEqual(sum(r["reasoning_capped"] is None for r in raw), 4)
        self.assertTrue(all(r["max_tokens"] == 16000 for r in raw))
        summary = self.summary_now()
        self.assertEqual({m: s["n_reasoning_capped"] for m, s in summary["per_model"].items()},
                         {"v/m1": 4, "v/m2": 4})
        self.assertEqual(summary["n_reasoning_capped"], 8)
        self.assertEqual(summary["segments"][-1]["n_reasoning_capped"], 8)
        self.assertIn("max_tokens - 4096", summary["reasoning_capped_rule"])
        # rebuilt from the raw log for a resume
        plan = Engine(self.rcfg(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual({k: s["n_reasoning_capped"] for k, s in plan.prior_stats.items()},
                         {"m1": 4, "m2": 4})
        self.assertEqual(plan.segments[0]["n_reasoning_capped"], 8)

    @staticmethod
    def _prompt(row):
        """Enough of a prompt for FakeAPI.parse to name the row's decision."""
        if row["step"] == "isolated":
            return f"QUESTION\non average, {row['others_mean']} points"
        return f"ROUND {row['round']} of 2. You are Player {row['agent_id']}."

    def test_the_row_s_max_tokens_sets_the_cap(self):
        self.use(CostAPI(usage_fn=lambda kw: _usage(15904)))
        Engine(self.rcfg(max_tokens=20000, arms=("isolated",))).run()
        self.assertEqual({r["reasoning_capped"] for r in _rows(self.results)}, {True})
        self.use(CostAPI(usage_fn=lambda kw: _usage(15903)))
        Engine(self.rcfg(run="r2", max_tokens=20000, arms=("isolated",))).run()
        rows = _rows(self.tmp / "runs" / "r2" / "r2.jsonl")
        self.assertEqual({(r["reasoning_capped"], r["max_tokens"]) for r in rows}, {(False, 20000)})

    def test_an_invalid_capped_answer_is_not_counted(self):
        api = CostAPI()
        # call 1: invalid and capped (re-requested); call 2: its valid answer, not
        # capped; call 5: a valid capped answer
        api.content_fn = lambda kw, c: (_payload({"contribution": 99}) if len(api.calls) == 1
                                        else c)
        api.usage_fn = lambda kw: _usage(11904 if len(api.calls) in (1, 5) else 10)
        self.use(api)
        Engine(self.rcfg(models=dict(GEMINI), cards=[CARD_A])).run()
        summary = self.summary_now()
        stats = summary["per_model"][GEMINI["gemini"]]
        self.assertEqual((stats["n_invalid"], stats["n_reasoning_capped"]), (1, 1))
        self.assertEqual(sum(bool(r["reasoning_capped"]) for r in _rows(self.results)), 1)
        plan = Engine(self.rcfg(models=dict(GEMINI), cards=[CARD_A]),
                      llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual((plan.prior_stats["gemini"]["n_invalid"],
                          plan.prior_stats["gemini"]["n_reasoning_capped"]), (1, 1))


# --------------------------------------------------------------------------
# (b) A3: elapsed_s, n_transport, n_deadline (mocked SDK call)
# --------------------------------------------------------------------------

class RowCounts(ResumeBase):
    def cfg1(self, **kw):
        return self.rcfg(models=dict(GEMINI), cards=[CARD_A], **kw)

    def test_transport_error_is_counted_on_its_row_and_in_the_summary(self):
        api = CostAPI()
        n = [0]

        def create(**kw):
            n[0] += 1
            if n[0] == 3:
                raise httpx.ConnectError("connection reset")
            return api(**kw)

        self.create.side_effect = create
        Engine(self.cfg1()).run()
        rows = _rows(self.results)
        self.assertEqual(len(rows), 8 + 5)
        hit = [r for r in rows if r["n_transport"]]
        self.assertEqual(len(hit), 1)
        self.assertEqual((hit[0]["n_transport"], hit[0]["n_deadline"]), (1, 0))
        self.assertTrue(all(r["n_deadline"] == 0 for r in rows))
        # elapsed_s: on every row and on its raw-log success record
        raw = {(r["call"]["step"], r["call"]["round"], r["call"]["agent_id"],
                r["call"]["others_mean"]): r for r in _successes(self.raw)}
        for r in rows:
            self.assertIsInstance(r["elapsed_s"], float)
            self.assertGreaterEqual(r["elapsed_s"], 0)
            key = (r["step"], r["round"], r["agent_id"], r.get("others_mean"))
            self.assertEqual(raw[key]["elapsed_s"], r["elapsed_s"])
        failed = [r for r in map(json.loads, self.raw.read_text().splitlines())
                  if r.get("error_kind") == "transport"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["call"]["agent_id"], hit[0]["agent_id"])
        summary = self.summary_now()
        stats = summary["per_model"][GEMINI["gemini"]]
        self.assertEqual((stats["n_transport"], stats["n_deadline"]), (1, 0))
        self.assertEqual((summary["n_transport"], summary["n_deadline"]), (1, 0))
        self.assertEqual(summary["segments"][-1]["n_transport"], 1)
        plan = Engine(self.cfg1(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertEqual((plan.prior_stats["gemini"]["n_transport"],
                          plan.prior_stats["gemini"]["n_deadline"]), (1, 0))

    def test_deadline_is_counted_on_its_row_with_unknown_cost(self):
        api = CostAPI()
        release = threading.Event()
        n = [0]

        def create(**kw):
            n[0] += 1
            if n[0] == 3:                     # the third call answers only after the test
                release.wait(30)
                raise ConnectionError("released")
            return api(**kw)

        self.create.side_effect = create
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(release.set)
        Engine(self.cfg1(request_deadline_s=0.2, stall_timeout_s=30)).run()
        rows = _rows(self.results)
        hit = [r for r in rows if r["n_deadline"]]
        self.assertEqual(len(hit), 1)
        self.assertEqual((hit[0]["n_deadline"], hit[0]["n_transport"]), (1, 0))
        rec = [r for r in map(json.loads, self.raw.read_text().splitlines())
               if r.get("error_subkind") == "deadline"]
        self.assertEqual(len(rec), 1)
        self.assertEqual((rec[0]["cost_unknown"], rec[0]["response_partial"],
                          rec[0]["response_partial_n_bytes"], rec[0]["attempt_ended"],
                          rec[0]["response_complete"]), (True, "", 0, False, False))
        self.assertNotIn("usage", rec[0])
        summary = self.summary_now()
        stats = summary["per_model"][GEMINI["gemini"]]
        self.assertEqual((stats["n_deadline"], stats["n_cost_unknown"], stats["deadline_cost_usd"]),
                         (1, 1, 0.0))
        self.assertEqual((summary["n_deadline"], summary["n_cost_unknown"]), (1, 1))
        self.assertEqual(stats["n_responses"], 13)                # not counted as a response
        plan = Engine(self.cfg1(request_deadline_s=0.2, stall_timeout_s=30),
                      llm=pgg_game.OfflineLLM()).resume_plan()
        st = plan.prior_stats["gemini"]
        self.assertEqual((st["n_deadline"], st["n_cost_unknown"], st["n_transport"]), (1, 1, 0))
        self.assertEqual(plan.problems, [])


# --------------------------------------------------------------------------
# (c) A3: the real HTTP layer (SDK + httpx + hook), MockTransport network
# --------------------------------------------------------------------------

def _completion(content: str, cost: float, reasoning_tokens=None, model="vendor/model-1") -> bytes:
    usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": cost}
    if reasoning_tokens is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return json.dumps({
        "id": "gen-1", "object": "chat.completion", "created": 0, "model": model,
        "provider": "FakeProv", "usage": usage,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}]}).encode()


# Deadline of the slow first attempt and when its second half comes (after the
# stream started). The grace ends SLOW_DEADLINE_S after the deadline, measured
# from the attempt's start, so the second half is caught as long as setting up
# the request takes less than 2 * SLOW_DEADLINE_S - SLOW_SECOND_HALF_S = 0.7 s
# (0.5 / 0.75 left 0.25 s and failed now and then under load).
SLOW_DEADLINE_S = 1.0
SLOW_SECOND_HALF_S = 1.3


def _slow_whole(body: bytes, at: float):
    """First half at once, the rest `at` seconds later (after the deadline)."""
    def plan(stop):
        yield body[:len(body) // 2]
        stop.wait(at)
        yield body[len(body) // 2:]
    return plan


def _trickle(stop):
    """Keep-alive bytes, never a whole body."""
    while not stop.is_set():
        yield b" "
        stop.wait(0.02)


def _silent_after(prefix: bytes):
    """Some bytes, then nothing until the test ends."""
    def plan(stop):
        yield prefix
        stop.wait(30)
        yield b""
    return plan


class Network:
    """httpx.MockTransport handler: request k gets plans[k] (a body generator) while
    there are plans, every later one fast(request_number) at once."""

    def __init__(self, plans, fast):
        self.plans, self.fast = list(plans), fast
        self.requests = []
        self.stop = threading.Event()        # ends every slow body (time.sleep is mocked)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        headers = {"content-type": "application/json"}
        if self.plans:
            return httpx.Response(200, headers=headers, stream=_Iter(self.plans.pop(0)(self.stop)))
        return httpx.Response(200, headers=headers, content=self.fast(len(self.requests)))


class HttpPathMixin:
    def use_network(self, net: Network):
        """llm_client._client as llm_client builds it, on a MockTransport."""
        http = llm_client._new_http_client(transport=httpx.MockTransport(net))
        client = llm_client._new_client(http, base_url="https://openrouter.invalid/api/v1")
        self.assertIn(llm_client._cut_at_deadline, client._client.event_hooks["response"])
        patch = mock.patch.object(llm_client, "_client", client)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(net.stop.set)
        return net


class DeadlineThroughHttpx(HttpPathMixin, LoggingTestBase):
    def setUp(self):
        super().setUp()
        self.assertEqual(llm_client.abandoned_attempts_alive(), 0)

    def call(self, deadline, **kw):
        counts, seen, responses = {}, [], []
        out = llm_client.call_llm_valid(
            "vendor/model-1", MESSAGES, schema=SCHEMA, session_id="s", is_valid=lambda c: True,
            request_deadline_s=deadline, counts=counts, on_deadline=seen.append,
            on_response=responses.append, **kw)
        return out, counts, seen, responses

    def test_body_cut_at_the_deadline_logs_content_and_cost(self):
        body = _completion('{"action": 7}', cost=0.0123, reasoning_tokens=11904)
        net = self.use_network(Network([_slow_whole(body, at=SLOW_SECOND_HALF_S)],
                                       lambda k: _completion('{"action": 1}', cost=0.001)))
        started = time.monotonic()
        out, counts, seen, responses = self.call(SLOW_DEADLINE_S)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(out, ({"action": 1}, 0))           # the cut response is no decision
        self.assertEqual(len(net.requests), 2)
        self.assertEqual((counts["n_deadline"], counts["n_transport"]), (1, 0))
        cut, ok = self.records()
        self.assertEqual((cut["error_kind"], cut["error_subkind"], cut["retrying"]),
                         ("transport", "deadline", True))
        self.assertGreaterEqual(cut["elapsed_s"], SLOW_DEADLINE_S)
        self.assertEqual(cut["response_partial"], body.decode())
        self.assertEqual(cut["response_partial_n_bytes"], len(body))
        self.assertEqual((cut["response_complete"], cut["attempt_ended"], cut["cost_unknown"],
                          cut["late_response"], cut["response_partial_truncated"]),
                         (True, True, False, False, False))
        self.assertEqual(cut["usage"]["cost"], 0.0123)
        self.assertEqual((cut["response_raw"], cut["finish_reason"], cut["provider"],
                          cut["model_snapshot"], cut["response_status_code"]),
                         ('{"action": 7}', "stop", "FakeProv", "vendor/model-1", 200))
        self.assertNotIn("response_parsed", cut)
        self.assertEqual(seen, [{"usage": cut["usage"], "cost_unknown": False,
                                 "late_response": False, "n_bytes": len(body)}])
        self.assertEqual(len(responses), 1)                 # only the accepted one
        self.assertEqual(ok["response_parsed"], {"action": 1})
        self.assertGreaterEqual(ok["elapsed_s"], 0)
        self.assertEqual(ok["usage"]["cost"], 0.001)        # usage.cost through the real SDK
        self.assertIs(ok["reasoning_capped"], None)

    def test_keep_alive_bytes_only_cost_unknown(self):
        net = self.use_network(Network([_trickle], lambda k: _completion('{"action": 1}', 0.001)))
        out, counts, seen, _ = self.call(0.3)
        self.assertEqual(out, ({"action": 1}, 0))
        self.assertEqual(counts["n_deadline"], 1)
        cut = self.records()[0]
        self.assertEqual(cut["error_subkind"], "deadline")
        self.assertGreater(cut["response_partial_n_bytes"], 0)
        self.assertEqual(cut["response_partial"].strip(), "")
        self.assertEqual((cut["response_complete"], cut["attempt_ended"], cut["cost_unknown"]),
                         (False, True, True))
        self.assertNotIn("usage", cut)
        self.assertEqual(seen[0]["usage"], None)
        self.assertTrue(seen[0]["cost_unknown"])
        self.assertEqual(len(net.requests), 2)

    def test_silent_connection_logs_what_arrived_before_the_deadline(self):
        prefix = b'{"id": "gen-1", "choices": [{"message": {"content": "{\\"act'
        self.use_network(Network([_silent_after(prefix)],
                                 lambda k: _completion('{"action": 1}', 0.001)))
        out, counts, seen, _ = self.call(0.3)
        self.assertEqual(out, ({"action": 1}, 0))
        cut = self.records()[0]
        self.assertEqual(cut["response_partial"], prefix.decode())
        self.assertEqual((cut["attempt_ended"], cut["response_complete"], cut["cost_unknown"]),
                         (False, False, True))
        self.assertEqual(cut["abandoned_attempts_alive"], 1)

    def test_partial_body_is_bounded(self):
        with mock.patch.object(llm_client, "PARTIAL_BODY_MAX_BYTES", 10):
            self.use_network(Network([_trickle], lambda k: _completion('{"action": 1}', 0.001)))
            self.call(0.3)
        cut = self.records()[0]
        self.assertEqual(len(cut["response_partial"]), 10)
        self.assertGreater(cut["response_partial_n_bytes"], 10)
        self.assertTrue(cut["response_partial_truncated"])


class LateWithinGrace(LoggingTestBase):
    def test_whole_response_after_the_deadline_is_billed_once(self):
        """It arrives within the grace: logged as late_response (with its cost); the
        deadline record points there instead of counting the cost again."""
        from test_pgg_guards import _response
        late = _response('{"action": 9}', model="m", cost=0.5)
        ok = _response('{"action": 1}', model="m", cost=0.001)
        gate = threading.Event()
        replies = iter([late, ok])

        def create(**kw):
            reply = next(replies)
            if reply is late:
                gate.wait(0.3)                 # deadline 0.2, grace until 0.4
            return reply

        self.create.side_effect = create
        self.addCleanup(_until, lambda: llm_client.abandoned_attempts_alive() == 0)
        self.addCleanup(gate.set)
        seen, late_seen = [], []
        out = llm_client.call_llm("m", MESSAGES, schema=SCHEMA, session_id="s",
                                  request_deadline_s=0.2, on_deadline=seen.append,
                                  on_late_response=late_seen.append)
        self.assertEqual(out, {"action": 1})
        self.assertTrue(_until(lambda: len(self.records()) == 3))
        recs = {r.get("event") or r.get("error_subkind") or "ok": r for r in self.records()}
        self.assertEqual((recs["deadline"]["late_response"], recs["deadline"]["cost_unknown"],
                          recs["deadline"]["attempt_ended"]), (True, False, True))
        self.assertNotIn("usage", recs["deadline"])
        self.assertEqual(recs["late_response"]["usage"]["cost"], 0.5)
        self.assertEqual(seen, [{"usage": None, "cost_unknown": False, "late_response": True,
                                 "n_bytes": 0}])
        self.assertEqual(len(late_seen), 1)
        # the engine adds nothing for the deadline record (the late response is counted)
        s = pgg_game._new_stats()
        engine = Engine.__new__(Engine)
        engine._count_deadline_cost(s, "m1", None, False, True)
        self.assertEqual((s["cost_usd"], s["n_cost_unknown"]), (0.0, 0))


class EngineDeadlineThroughHttpx(HttpPathMixin, ResumeBase):
    """Engine -> llm_client -> openai SDK -> httpx (+ hook) -> MockTransport."""

    def network(self):
        content = _payload({"contribution": 5, "rationale": "because"})
        # first request (others_mean 0): cut at the deadline, its usage arrived;
        # later: fast, reasoning at the cap on odd request numbers
        return self.use_network(Network(
            [_slow_whole(_completion(content, cost=0.0123, reasoning_tokens=11904),
                         at=SLOW_SECOND_HALF_S)],
            lambda k: _completion(content, cost=0.001,
                                  reasoning_tokens=11904 if k % 2 else 11903)))

    def cfg1(self, **kw):
        base = dict(models={"m1": "vendor/model-1"}, cards=[CARD_A], arms=("isolated",),
                    request_deadline_s=SLOW_DEADLINE_S, stall_timeout_s=30)
        base.update(kw)
        return self.rcfg(**base)

    def test_cut_response_cost_is_in_the_budget_and_the_summary(self):
        net = self.network()
        engine = Engine(self.cfg1())
        engine.run()
        self.assertEqual(len(net.requests), 6)              # 5 decisions + 1 cut attempt
        rows = _rows(self.results)
        self.assertEqual([r["others_mean"] for r in rows], [0, 5, 10, 15, 20])
        self.assertEqual([r["n_deadline"] for r in rows], [1, 0, 0, 0, 0])
        self.assertTrue(all(r["n_transport"] == 0 and r["elapsed_s"] >= 0 for r in rows))
        # requests 2..6 answered the decisions: 11903 on even, 11904 on odd numbers
        self.assertEqual([r["reasoning_capped"] for r in rows], [False, True, False, True, False])
        self.assertTrue(all(r["provider"] == "FakeProv" for r in rows))
        summary = self.summary_now()
        stats = summary["per_model"]["vendor/model-1"]
        self.assertAlmostEqual(stats["cost_usd"], 0.0123 + 5 * 0.001, places=12)
        self.assertAlmostEqual(stats["deadline_cost_usd"], 0.0123, places=12)
        self.assertAlmostEqual(summary["total_cost_usd"], 0.0173, places=12)
        self.assertAlmostEqual(engine.total_cost, 0.0173, places=12)
        self.assertEqual((stats["n_deadline"], stats["n_cost_unknown"], stats["n_responses"],
                          stats["n_reasoning_capped"]), (1, 0, 5, 2))
        self.assertEqual((summary["n_deadline"], summary["deadline_cost_usd"]), (1, 0.0123))
        cut = [r for r in map(json.loads, self.raw.read_text().splitlines())
               if r.get("error_subkind") == "deadline"]
        self.assertEqual(len(cut), 1)
        self.assertEqual((cut[0]["usage"]["cost"], cut[0]["call"]["others_mean"]), (0.0123, 0))
        # a resume rebuilds the same cost from the raw log
        plan = Engine(self.cfg1(), llm=pgg_game.OfflineLLM()).resume_plan()
        self.assertAlmostEqual(plan.prior_cost_usd, 0.0173, places=12)
        self.assertAlmostEqual(plan.prior_stats["m1"]["deadline_cost_usd"], 0.0123, places=12)
        self.assertEqual(plan.prior_stats["m1"]["n_deadline"], 1)

    def test_cut_response_cost_can_stop_the_run_at_the_budget(self):
        # 3 decisions at 0.001 stay below 0.015; with the cut response's 0.0123 the
        # budget is reached before the 4th decision
        net = self.network()
        engine = Engine(self.cfg1(budget_usd=0.015))
        with self.assertRaisesRegex(RunStopped, "budget"):
            engine.run()
        self.assertEqual(len(net.requests), 4)
        summary = self.summary_now()
        self.assertEqual(summary["stop_reason"], "budget")
        self.assertAlmostEqual(summary["total_cost_usd"], 0.0123 + 3 * 0.001, places=12)


# --------------------------------------------------------------------------
# (d) A3: request_deadline_s / stall_timeout_s on --resume
# --------------------------------------------------------------------------

class TimeoutsOnResume(ResumeBase):
    def argv(self, *extra):
        cards = self.tmp / "cards.json"
        cards.write_text(json.dumps([{"card_id": c.card_id, "style": c.style, "text": c.text}
                                     for c in (CARD_A, CARD_B)]))
        return ["--run", "r1", "--cards", str(cards), "--models", "gemini", "--rounds", "2",
                "--groups-per-cell", "1", "--isolated-reps", "1",
                "--runs-dir", str(self.tmp / "runs"), "--resume", *extra]

    def main(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = pgg_game.main(self.argv(*extra))
        return code, out.getvalue() + err.getvalue()

    def first_segment(self):
        self.interrupted_run(at=14, models=dict(GEMINI), budget_usd=None, invalid_rate_cap=None,
                             request_deadline_s=60, stall_timeout_s=120)

    def test_dry_run_reports_the_difference(self):
        self.first_segment()
        before = _tree(self.run_dir)
        code, text = self.main("--dry-run")
        self.assertEqual(code, 1, text)
        self.assertIn("FARKLI (segment 0'e göre): request_deadline_s 60 -> 900, "
                      "stall_timeout_s 120 -> 1800", text)
        self.assertIn("SORUN (sürdürme başlamaz):", text)
        code, text = self.main("--dry-run", "--request-deadline", "60", "--stall-timeout", "120")
        self.assertEqual(code, 0, text)
        self.assertIn("compared with segment 0", text)
        self.assertIn("Config tutarlı", text)
        self.assertNotIn("FARKLI", text)
        code, text = self.main("--dry-run", "--allow-timeout-change")
        self.assertEqual(code, 0, text)
        self.assertIn("--allow-timeout-change verildi", text)
        self.assertEqual(_tree(self.run_dir), before)

    def test_resume_refuses_a_change_before_any_call_unless_allowed(self):
        self.first_segment()
        api = CostAPI()
        self.use(api)
        before = _tree(self.run_dir)
        code, text = self.main("--stall-timeout", "120")         # deadline back at 900
        self.assertEqual(code, 1, text)
        self.assertIn("HATA", text)
        self.assertIn("request_deadline_s / stall_timeout_s differ from segment 0", text)
        self.assertEqual(api.calls, [])
        self.assertEqual(_tree(self.run_dir), before)
        code, text = self.main("--stall-timeout", "120", "--allow-timeout-change")
        self.assertEqual(code, 0, text)
        summary = self.summary_now()
        change = {"from_segment": 0, "earlier": {"request_deadline_s": 60, "stall_timeout_s": 120},
                  "now": {"request_deadline_s": 900.0, "stall_timeout_s": 120.0}, "allowed": True}
        self.assertEqual(summary["timeout_changes"], [change])
        self.assertEqual([s.get("timeout_change") for s in summary["segments"]], [None, change])
        self.assertEqual(summary["units"]["n_remaining"], 0)

    def test_allow_timeout_change_must_be_a_bool(self):
        with self.assertRaises(ValueError):
            self.rcfg(allow_timeout_change="yes").validate()


if __name__ == "__main__":
    unittest.main()
