"""
Shared model-calling layer, carried over from project-ultimatum.

Contract (unchanged from the first study):
  * every call goes through OpenRouter and is logged to logs/raw_calls.jsonl
    with a session_id, the messages, the raw response and token usage
  * structured JSON output only — never regex-parse a decision
  * degenerate payloads (e.g. {"action": -1}) are never coded as decisions:
    they are re-requested and counted
  * seeds are stable across processes and models (crc32, never hash())

The API key is read from ../.env (OPENROUTER_API_KEY), shared with the other
projects in this folder; it is not copied here.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import zlib
from pathlib import Path

import httpx
from dotenv import load_dotenv
import openai
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

PROJECT_DIR = Path(__file__).parent
LOG_PATH = PROJECT_DIR / "logs" / "raw_calls.jsonl"

# Generating models of this study (the `__main__` loop runs over this dict).
MODELS = {
    "deepseek": "deepseek/deepseek-v4.1-flash:batch",
    "gpt":      "openai/gpt-6-luna:batch",
    "gemini":   "google/gemini-3.8-flash:batch",
}

# Record of the first (ultimatum) study. Kept apart from MODELS on purpose, so
# that nothing iterating over MODELS calls the old models.
MODELS_ULTIMATUM = {
    "haiku":  "anthropic/claude-haiku-4.5",
    "gemma":  "google/gemma-4-31b-it",
    "gptoss": "openai/gpt-oss-120b",
}

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL = "typesafe/jev-1.13"
SPAN_MODEL = "respan/span-01"

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    timeout=60.0,
    max_retries=0,  # we handle retries ourselves
)

_http = httpx.Client(
    timeout=60.0,
    headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "X-Title": "GABM public goods",
    },
)

# Reasoning models: reasoning tokens count against max_tokens on most providers
# (OpenRouter docs: reasoning-tokens, parameters). A low limit returns empty or
# half-finished content with finish_reason "length", billed anyway. The first
# study's 500 is far too low for the reasoning models used here.
DEFAULT_MAX_TOKENS = 16000

_log_lock = threading.Lock()
_RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}


def stable_seed(namespace: str, *parts, base: int = 0) -> int:
    """Seed that is identical across processes, models and conditions."""
    key = "|".join([namespace, *map(str, parts)])
    return base + zlib.crc32(key.encode()) % 1_000_000


def _append_log(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _log_lock:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def temperature_label(temperature: float | None) -> float | str:
    """What the logs record: the number sent, or "default" when none was sent."""
    return "default" if temperature is None else temperature


def augment_with_schema(messages: list[dict], schema: dict) -> list[dict]:
    """Copy of messages whose last one also asks for ONLY a JSON object of schema."""
    augmented = list(messages)
    augmented[-1] = {
        **augmented[-1],
        "content": (
            augmented[-1]["content"]
            + "\n\nRespond with ONLY a JSON object matching this schema:\n"
            + json.dumps(schema, ensure_ascii=False)
        ),
    }
    return augmented


def _usage_dict(u) -> dict | None:
    if u is None:
        return None
    try:
        return u.model_dump()
    except Exception:
        return None


def _parse_json_strict(raw: str) -> tuple[dict, bool]:
    """Parse a JSON payload; returns (parsed, degraded).

    degraded is True when the prose-wrapping fallback was needed. The fallback
    behaves as before; it is only labelled so the log shows it.
    """
    try:
        return json.loads(raw), False
    except json.JSONDecodeError:
        # Fallback for models that wrap JSON in prose — logged as degraded.
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0)), True


class _EmptyResponseError(ValueError):
    """The response content was None or empty, so there was nothing to parse."""


def _error_kind(e: Exception) -> str:
    """Class of a failed attempt: transport, http, parse or other."""
    if isinstance(e, (openai.APIConnectionError, httpx.TransportError)):
        return "transport"  # APITimeoutError is a subclass of APIConnectionError
    if isinstance(e, openai.APIStatusError):
        return "http"
    if isinstance(e, (json.JSONDecodeError, _EmptyResponseError)):
        return "parse"
    return "other"


def _call_llm_counted(
    model: str,
    messages: list[dict],
    *,
    schema: dict,
    session_id: str,
    temperature: float | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_retries: int = 4,
) -> tuple[dict, int]:
    """call_llm that also returns the number of parse failures it retried.

    Returns (parsed, n_parse_fail). If every attempt fails, the RuntimeError
    carries the count in its n_parse_fail attribute.
    """
    augmented = augment_with_schema(messages, schema)
    # temperature=None: not sent, the provider's own default applies.
    extra = {} if temperature is None else {"temperature": temperature}

    last_err = None
    n_parse_fail = 0
    for attempt in range(max_retries):
        # Only the API call and the parsing are inside the try: a failing log
        # write must not trigger a retry (it would bill the same call again).
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=augmented,
                max_tokens=max_tokens,
                **extra,
                response_format={"type": "json_object"},
                extra_headers={"X-Title": "GABM public goods"},
                extra_body={"session_id": session_id[:256]},
            )
            raw = resp.choices[0].message.content
            if raw is None or not raw.strip():
                raise _EmptyResponseError("empty response content")
            parsed, degraded = _parse_json_strict(raw)
        except Exception as e:
            last_err = e
            kind = _error_kind(e)
            if kind == "parse":
                n_parse_fail += 1
            record = {
                "ts": time.time(), "model": model, "session_id": session_id,
                "temperature": temperature_label(temperature), "messages": messages,
                "error_type": type(e).__name__, "error_kind": kind,
                "error": str(e), "attempt": attempt, "retrying": True,
            }
            if isinstance(e, openai.APIStatusError):
                record["status_code"] = e.status_code
            _append_log(record)
            time.sleep(1.5 * (attempt + 1))
            continue
        _append_log({
            "ts": time.time(), "model": model, "session_id": session_id,
            "temperature": temperature_label(temperature), "messages": messages,
            "response_raw": raw, "response_parsed": parsed,
            "usage": _usage_dict(getattr(resp, "usage", None)),
            "model_snapshot": getattr(resp, "model", None),
            "attempt": attempt, "degraded": degraded,
        })
        return parsed, n_parse_fail
    final = {
        "ts": time.time(), "model": model, "session_id": session_id,
        "error_type": type(last_err).__name__, "error_kind": _error_kind(last_err),
        "error": str(last_err), "attempt": max_retries, "messages": messages,
    }
    if isinstance(last_err, openai.APIStatusError):
        final["status_code"] = last_err.status_code
    _append_log(final)
    err = RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")
    err.n_parse_fail = n_parse_fail
    raise err


def call_llm(
    model: str,
    messages: list[dict],
    *,
    schema: dict,
    session_id: str,
    temperature: float | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_retries: int = 4,
) -> dict:
    """Call OpenRouter with structured JSON output. Retries on transient errors.

    temperature=None (default) is not sent, so the provider's own default
    applies and the log says "default"; an explicit number is sent and logged.

    Every failed attempt is logged with error_type (exception class name) and
    error_kind (transport / http / parse / other; status_code for http). Parse
    failures are retried; use call_llm_valid(..., return_parse_fail=True) to
    get their count.
    """
    parsed, _ = _call_llm_counted(
        model, messages, schema=schema, session_id=session_id,
        temperature=temperature, max_tokens=max_tokens, max_retries=max_retries)
    return parsed


def call_llm_valid(
    model: str,
    messages: list[dict],
    *,
    schema: dict,
    session_id: str,
    is_valid,
    temperature: float | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_invalid: int = 3,
    return_parse_fail: bool = False,
) -> tuple[dict, int] | tuple[dict, int, int]:
    """call_llm, re-requesting payloads for which is_valid(parsed) is False.

    Returns (parsed, n_invalid). Invalid payloads are never coded as decisions;
    store n_invalid with the row and report it. With return_parse_fail=True it
    returns (parsed, n_invalid, n_parse_fail), where n_parse_fail counts the
    unparseable responses retried across all calls. It is a separate count: it
    is not added to n_invalid.
    """
    call: dict = {}
    n_parse_fail = 0
    for n_invalid in range(max_invalid + 1):
        call, n_pf = _call_llm_counted(
            model, messages, schema=schema, session_id=session_id,
            temperature=temperature, max_tokens=max_tokens)
        n_parse_fail += n_pf
        if is_valid(call):
            if return_parse_fail:
                return call, n_invalid, n_parse_fail
            return call, n_invalid
        _append_log({
            "ts": time.time(), "model": model, "session_id": session_id,
            "event": "invalid_payload", "invalid": True,
            "n_invalid": n_invalid, "response_parsed": call,
        })
    raise RuntimeError(f"{max_invalid + 1} invalid payloads in a row: {call!r}")


def call_decisions(
    state: dict | str,
    questions: dict,
    *,
    session_id: str,
    model: str = JEV_MODEL,
    max_retries: int = 4,
) -> dict:
    """Typed-question call to a decision model (Jev, Span-01) for text coding.

    Span-01 accepts only noul questions and a plain-string (or input/output
    span) state; Jev accepts any JSON state. Returns the full response dict.
    """
    body = {"model": model, "state": state, "questions": questions}
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = _http.post(DECISIONS_URL, json=body)
            if resp.status_code in _RETRY_STATUS:
                raise httpx.HTTPStatusError(
                    f"retryable {resp.status_code}: {resp.text[:300]}",
                    request=resp.request, response=resp,
                )
            if resp.status_code != 200:
                _append_log({
                    "ts": time.time(), "model": model, "endpoint": "alpha/decisions",
                    "session_id": session_id, "state": state, "questions": questions,
                    "error": f"{resp.status_code}: {resp.text[:1000]}", "attempt": attempt,
                })
                raise RuntimeError(f"decision call rejected ({resp.status_code}): {resp.text[:500]}")
            data = resp.json()
            _append_log({
                "ts": time.time(), "model": model, "model_snapshot": data.get("model"),
                "endpoint": "alpha/decisions", "session_id": session_id,
                "state": state, "questions": questions, "response_raw": data,
                "usage": data.get("usage"), "attempt": attempt,
            })
            return data
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    _append_log({
        "ts": time.time(), "model": model, "endpoint": "alpha/decisions",
        "session_id": session_id, "error": str(last_err), "attempt": max_retries,
        "state": state, "questions": questions,
    })
    raise RuntimeError(f"decision call failed after {max_retries} attempts: {last_err}")


if __name__ == "__main__":
    # Plumbing check: one tiny call per generating model.
    schema = {"type": "object", "required": ["answer"],
              "properties": {"answer": {"type": "string", "enum": ["ok"]}}}
    for key, slug in MODELS.items():
        out, n_bad, n_pf = call_llm_valid(
            slug, [{"role": "user", "content": "Reply with the word ok."}],
            schema=schema, session_id=f"pgg-plumbing-{key}",
            is_valid=lambda c: isinstance(c.get("answer"), str),
            return_parse_fail=True)
        print(key, out, "invalid payloads:", n_bad, "parse failures:", n_pf)
    print("seed check:", stable_seed("demo", "weird", 10, 0))
