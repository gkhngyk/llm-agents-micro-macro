"""Mock tests of the answer-instruction options (task #80, EMIR 4d; #90, EMIR 5 M4; off by default).

answer_format (config / RunConfig, default None = "schema_text"):
  * None / "schema_text": the request is byte for byte what the code before
    task #80 (811fdcc) sent: the schema text appended to the last message,
    response_format json_object. Checked against request hashes recorded
    with that commit (tests/fixtures/request_hashes_811fdcc.json).
  * "example_object" (option A): a placeholder example object instead of the
    schema text (no number that is not already in the question), every field
    required; json_object.
  * "json_schema_strict" (option B, task #90): the strict schema (every object
    closed, every field required) as the schema text in the prompt AND as
    response_format json_schema with strict true: the prompt says what is enforced.
  In A and B "rationale" is required in the prompt and in the check.
No network, no ../.env. Regenerate the fixture with an export of the commit:
    git archive 811fdcc | tar -x -C DIR; cp tests/test_answer_format.py DIR/tests/
    python DIR/tests/test_answer_format.py --print-hashes > tests/fixtures/request_hashes_811fdcc.json
"""

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_pgg_game import CARD_A, ROOT, EngineTestBase  # noqa: E402

import llm_client  # noqa: E402
import pgg_game  # noqa: E402
from pgg_game import Engine, GameParams, RunConfig  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "request_hashes_811fdcc.json"
EXAMPLE_INTRO = "parts (every field is required):\n"
STORY_A = ROOT / "frames" / "story_A.json"


def _answer(schema):
    """A valid answer to a JSON schema (integers at their minimum, strings "x")."""
    t = schema.get("type")
    if t == "object":
        return {k: _answer(v) for k, v in schema.get("properties", {}).items()}
    if t == "integer":
        return schema.get("minimum", 0)
    return "x"


def _example_answer(text):
    """A valid answer from a placeholder example object (option A)."""
    text = re.sub(r"<whole number from (-?\d+) to -?\d+>", r"\1", text)
    text = re.sub(r"<whole number>", "0", text)
    return json.loads(text)


class SchemaAPI:
    """Answers every request validly from the schema it carries (any frame, any format)."""

    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        user = kwargs["messages"][-1]["content"]
        rf = kwargs.get("response_format") or {}
        if rf.get("type") == "json_schema":
            answer = _answer(rf["json_schema"]["schema"])
        elif "matching this schema:\n" in user:
            answer = _answer(json.loads(user.rsplit("matching this schema:\n", 1)[1]))
        else:
            answer = _example_answer(user.rsplit(EXAMPLE_INTRO, 1)[1])
        message = SimpleNamespace(content=json.dumps(answer), reasoning=None)
        usage = SimpleNamespace(model_dump=lambda: {"prompt_tokens": 10, "completion_tokens": 5})
        return SimpleNamespace(model=kwargs["model"], usage=usage,
                               choices=[SimpleNamespace(message=message, finish_reason="stop")])


def request_sha(kwargs) -> str:
    """sha256 of what goes out: model, messages, response_format, max_tokens, body."""
    sent = {k: kwargs.get(k) for k in ("model", "messages", "response_format", "max_tokens",
                                       "extra_body", "extra_headers", "temperature")}
    return hashlib.sha256(json.dumps(sent, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()


# Three small designs covering every prompt kind: abstract_v3 + story_A with
# rule comprehension and the fixed_round isolated question (N); abstract_v3
# under P (punishment step); abstract_v2 (pilot v2, no frames) under N and P.
DESIGNS = {
    "v3_story": dict(frames={"abstract_v3": ["m1"], "story": ["m1"]},
                     frame_files={"story": str(STORY_A)}, comprehension=True,
                     isolated_frame="fixed_round", isolated_round_no=2, conditions=("N",),
                     arms=("group", "isolated")),
    "v3_P": dict(frames={"abstract_v3": ["m1"]}, comprehension=True,
                 isolated_frame="fixed_round", isolated_round_no=2, conditions=("P",),
                 arms=("group",)),
    "v2": dict(conditions=("N", "P"), arms=("group", "isolated"), isolated_frame="repeated"),
}


def run_design(name, tmp: Path, **extra) -> list:
    """Requests (kwargs) of one design, with the API replaced by SchemaAPI."""
    api = SchemaAPI()
    log = tmp / f"{name}_raw.jsonl"
    with mock.patch.object(llm_client, "LOG_PATH", log), \
            mock.patch.object(llm_client, "_client") as client, \
            mock.patch.object(llm_client.time, "sleep"), \
            mock.patch.object(pgg_game, "_REQUIRE_VERIFIED_CODE", False):
        client.chat.completions.create.side_effect = api
        (tmp / name).mkdir()
        cfg = RunConfig(run=f"rf_{name}", cards=[CARD_A], models={"m1": "vendor/model-1"},
                        params=GameParams(rounds=2), groups_per_cell=1, isolated_reps=1,
                        results_dir=tmp / name, **DESIGNS[name], **extra)
        Engine(cfg).run()
    return api.calls


def request_hashes() -> dict:
    with tempfile.TemporaryDirectory() as d:
        return {name: sorted(request_sha(k) for k in run_design(name, Path(d)))
                for name in DESIGNS}


class DefaultIsByteIdentical(EngineTestBase):
    def test_requests_equal_those_of_811fdcc(self):
        expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
        got = request_hashes()
        self.assertEqual({k: len(v) for k, v in got.items()},
                         {k: len(v) for k, v in expected.items()})
        self.assertEqual(got, expected)

    def test_explicit_schema_text_equals_the_default(self):
        for name in DESIGNS:
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                default = sorted(request_sha(k) for k in run_design(name, Path(d)))
            with tempfile.TemporaryDirectory() as d:
                explicit = sorted(request_sha(k) for k in run_design(
                    name, Path(d), answer_format="schema_text"))
            self.assertEqual(explicit, default)

    def test_prompt_sha256_of_the_default_is_unchanged(self):
        args = ("v/m", [{"role": "user", "content": "x"}], {"type": "object"})
        old = hashlib.sha256(json.dumps({"model": args[0], "messages": args[1],
                                         "schema": args[2]}, ensure_ascii=False,
                                        sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(pgg_game.prompt_sha256(*args), old)
        self.assertNotEqual(pgg_game.prompt_sha256(*args, "example_object"), old)


def _instruction_cut(content: str) -> str:
    return content.split("\n\nRespond with ONLY a JSON object")[0]


class Options(EngineTestBase):
    def runs(self, name, fmt):
        with tempfile.TemporaryDirectory() as d:
            default = run_design(name, Path(d))
        with tempfile.TemporaryDirectory() as d:
            calls = run_design(name, Path(d), answer_format=fmt)
            rows = [json.loads(x) for x in (Path(d) / name / f"rf_{name}.jsonl")
                    .read_text().splitlines()]
            summary = json.loads((Path(d) / name / f"rf_{name}_summary.json").read_text())
            raw = [json.loads(x) for x in (Path(d) / f"{name}_raw.jsonl")
                   .read_text().splitlines()]
        return default, calls, rows, summary, raw

    def test_constants_agree(self):
        self.assertEqual(pgg_game.ANSWER_FORMATS, llm_client.ANSWER_FORMATS)
        self.assertEqual(pgg_game.ALL_FIELDS_REQUIRED_FORMATS,
                         llm_client.ALL_FIELDS_REQUIRED_FORMATS)
        with self.assertRaisesRegex(ValueError, "answer_format must be one of"):
            RunConfig(run="x", cards=[CARD_A], models={"m1": "v/m"}, answer_format="xml",
                      results_dir=self.tmp).validate()

    def test_example_object_replaces_the_schema_text(self):
        for name in DESIGNS:
            with self.subTest(name):
                default, calls, rows, summary, raw = self.runs(name, "example_object")
                self.assertEqual(len(calls), len(default))
                # everything before the instruction is the default's, byte for byte
                key = lambda k: json.dumps([k["messages"][:-1],  # noqa: E731
                                            _instruction_cut(k["messages"][-1]["content"])])
                self.assertEqual(sorted(map(key, calls)), sorted(map(key, default)))
                for k in calls:
                    user = k["messages"][-1]["content"]
                    self.assertNotIn("matching this schema", user)
                    self.assertNotIn('"type"', user)
                    self.assertIn("with your own values in place of the <...> " + EXAMPLE_INTRO
                                  + "{", user)
                    self.assertEqual(k["response_format"], {"type": "json_object"})
                    # the example writes no number the question does not hold already
                    question = _instruction_cut(user)
                    example = user.rsplit(EXAMPLE_INTRO, 1)[1]
                    for number in re.findall(r"\d+", example):
                        self.assertRegex(question, rf"(?<!\d){number}(?!\d)")
                self.assertEqual({r["answer_format"] for r in rows}, {"example_object"})
                self.assertEqual(summary["config"]["answer_format"], "example_object")
                self.assertTrue(all(r.get("answer_format") == "example_object"
                                    for r in raw if "messages" in r))

    def test_example_template(self):
        f = pgg_game.load_frame_file("abstract_v3", None)
        p = GameParams()
        self.assertEqual(
            llm_client.example_template(pgg_game.contribution_schema(p, True, f)),
            '{"contribution": <whole number from 0 to 20>, '
            '"rationale": "<One or two sentences on why you chose this.>"}')
        self.assertEqual(
            llm_client.example_template(f.comprehension_schema(False)),
            '{"q1": <whole number>, "q2": <whole number>}')
        self.assertEqual(
            llm_client.example_template(pgg_game.punishment_schema(p, [2, 3], False, f)),
            '{"punishments": {"2": <whole number from 0 to 10>, '
            '"3": <whole number from 0 to 10>}}')
        story = pgg_game.load_frame_file("story", str(STORY_A))
        self.assertTrue(llm_client.example_template(
            pgg_game.contribution_schema(p, True, story)).startswith(
            '{"credits_into_jar": <whole number from 0 to 20>'))

    def test_json_schema_strict_states_the_enforced_schema(self):
        def text_schema(k):
            return json.loads(k["messages"][-1]["content"].rsplit("matching this schema:\n", 1)[1])

        for name in DESIGNS:
            with self.subTest(name):
                default, calls, rows, summary, raw = self.runs(name, "json_schema_strict")
                self.assertEqual(len(calls), len(default))
                # task #90: everything before the schema text is the default's, byte for
                # byte; the schema text is the strict form of the default's schema text
                key = lambda k: json.dumps([k["messages"][:-1],  # noqa: E731
                                            _instruction_cut(k["messages"][-1]["content"])])
                self.assertEqual(sorted(map(key, calls)), sorted(map(key, default)))
                self.assertEqual(
                    sorted(json.dumps([key(k), llm_client.strict_json_schema(text_schema(k))],
                                      sort_keys=True) for k in default),
                    sorted(json.dumps([key(k), text_schema(k)], sort_keys=True) for k in calls))
                for k in calls:
                    rf = k["response_format"]
                    self.assertEqual((rf["type"], rf["json_schema"]["strict"],
                                      rf["json_schema"]["name"]), ("json_schema", True, "answer"))
                    schema = rf["json_schema"]["schema"]
                    # the prompt states exactly the enforced schema (rationale required in both)
                    self.assertEqual(text_schema(k), schema)
                    if "rationale" in schema["properties"]:
                        self.assertIn("rationale", schema["required"])

                    def closed(s):
                        if s.get("type") == "object":
                            self.assertIs(s["additionalProperties"], False)
                            self.assertEqual(set(s["required"]), set(s["properties"]))
                            for v in s["properties"].values():
                                closed(v)
                    closed(schema)
                self.assertEqual({r["answer_format"] for r in rows}, {"json_schema_strict"})
                self.assertEqual(summary["config"]["answer_format"], "json_schema_strict")

    def test_strict_schema_does_not_change_its_input(self):
        f = pgg_game.load_frame_file("abstract_v3", None)
        schema = pgg_game.punishment_schema(GameParams(), [1, 3], True, f)
        before = json.dumps(schema, sort_keys=True)
        strict = llm_client.strict_json_schema(schema)
        self.assertEqual(json.dumps(schema, sort_keys=True), before)
        self.assertEqual(strict["required"], ["punishments", "rationale"])
        self.assertEqual(strict["properties"]["punishments"]["required"], ["1", "3"])
        self.assertEqual(strict["properties"]["punishments"]["properties"]["1"],
                         {"type": "integer", "minimum": 0, "maximum": 10})


class ResumeWithAnotherFormat(unittest.TestCase):
    def test_config_difference_stops_the_resume(self):
        from test_pgg_resume import ResumeBase

        class T(ResumeBase):
            def runTest(self):
                self.interrupted_run()
                engine, api = self.resume(answer_format="json_schema_strict")
                with self.assertRaisesRegex(ValueError, "answer_format"):
                    engine.run(resume=True)
                self.assertEqual(api.calls, [])
        result = unittest.TestResult()
        T().run(result)
        self.assertEqual((result.errors, result.failures), ([], []))


if __name__ == "__main__":
    if sys.argv[1:] == ["--print-hashes"]:
        with mock.patch("sys.stdout", new=sys.stdout):
            print(json.dumps(request_hashes(), indent=1))
    else:
        unittest.main()
