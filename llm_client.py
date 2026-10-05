"""
Shared model-calling layer, carried over from project-ultimatum.

Contract (unchanged from the first study):
  * every call goes through OpenRouter and is logged to logs/raw_calls.jsonl
    (or to the file set with set_log_path, e.g. a run directory outside the
    repository) with a session_id, the messages, the raw response and token
    usage
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
    "deepseek": "deepseek/deepseek-v4.1-flash",
    "gpt":      "openai/gpt-6-luna",
    "gemini":   "google/gemini-2.5-flash-lite",
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

# Client timeout in seconds. Long reasoning completions (up to max_tokens
# 16000) need far more than the first study's 60 s; a call may also pass its
# own timeout (pgg_game reads it from the run config).
DEFAULT_TIMEOUT_S = 300.0

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    timeout=DEFAULT_TIMEOUT_S,
    max_retries=0,  # we handle retries ourselves
)

_http = httpx.Client(
    timeout=DEFAULT_TIMEOUT_S,
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


def set_log_path(path: str | Path) -> Path:
    """Send the raw log to another file (e.g. a run directory outside the repo).

    Returns the previous path, so a caller can restore it.
    """
    global LOG_PATH
    previous, LOG_PATH = LOG_PATH, Path(path)
    return previous


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


def _finish_reason(resp) -> str | None:
    """choices[0].finish_reason of a response; None when absent or no response."""
    try:
        value = resp.choices[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        return None
    return value if isinstance(value, str) else None


def _reasoning_text(resp) -> str | None:
    """Reasoning text of choices[0].message (OpenRouter's `reasoning` field), if any."""
    try:
        value = resp.choices[0].message.reasoning
    except (AttributeError, IndexError, TypeError):
        return None
    return value if isinstance(value, str) and value.strip() else None


def _extra_field(resp, name: str):
    """A top-level response field outside the OpenAI schema (None if absent).

    The openai SDK keeps unknown fields in model_extra; plain objects (test
    doubles) may carry them as attributes. Mock attributes are ignored.
    """
    extra = getattr(resp, "model_extra", None)
    if isinstance(extra, dict) and name in extra:
        return extra[name]
    value = getattr(resp, name, None)
    return value if isinstance(value, (str, dict, list)) else None


def _provider_info(resp) -> tuple[str | None, str | None]:
    """(provider name, quantization) of the endpoint that served the response.

    Read from openrouter_metadata.endpoints.available[selected=true] (sent
    when the X-OpenRouter-Metadata: enabled header is set, OpenRouter docs
    "Router Metadata"), else from a top-level "provider" string. Quantization
    is taken only when the response carries one (the documented schema has
    none); otherwise None.
    """
    provider, quantization = None, None
    meta = _extra_field(resp, "openrouter_metadata")
    if isinstance(meta, dict):
        available = (meta.get("endpoints") or {}).get("available") or []
        selected = [e for e in available if isinstance(e, dict) and e.get("selected") is True]
        if selected:
            provider = selected[0].get("provider")
            quantization = selected[0].get("quantization")
    if provider is None:
        provider = _extra_field(resp, "provider")
    if quantization is None:
        quantization = _extra_field(resp, "quantization")
    return (provider if isinstance(provider, str) else None,
            quantization if isinstance(quantization, str) else None)


def _response_info(resp) -> dict:
    """What on_response hooks receive.

    usage, finish_reason, model_snapshot, provider, provider_quantization and
    provider_error (True for a provider-error response, see
    _is_provider_error; such a response is retried, never parsed).
    """
    provider, quantization = _provider_info(resp)
    return {
        "usage": _usage_dict(getattr(resp, "usage", None)),
        "finish_reason": _finish_reason(resp),
        "model_snapshot": getattr(resp, "model", None),
        "provider": provider,
        "provider_quantization": quantization,
        "provider_error": _is_provider_error(resp),
    }


def _is_provider_error(resp) -> bool:
    """A response that the provider failed to produce.

    finish_reason "error", or a response with 0 prompt and 0 completion
    tokens and a cost of 0 (or no cost field). pilot_20261005: Gemini returned
    three of these as broken JSON, which were counted as parse failures.
    """
    if _finish_reason(resp) == "error":
        return True
    usage = _usage_dict(getattr(resp, "usage", None))
    if not isinstance(usage, dict):
        return False
    tokens = [usage.get("prompt_tokens"), usage.get("completion_tokens")]
    if not all(isinstance(t, int) and not isinstance(t, bool) for t in tokens):
        return False
    cost = usage.get("cost", 0)
    return sum(tokens) == 0 and isinstance(cost, (int, float)) and cost == 0


def reasoning_effort_label(reasoning_effort: str | None) -> str:
    """What the logs record: the effort sent, or "default" when none was sent."""
    return "default" if reasoning_effort is None else reasoning_effort


class _EmptyResponseError(ValueError):
    """The response content was None or empty, so there was nothing to parse."""


class _ProviderErrorResponse(Exception):
    """A response that arrived but that the provider failed to produce."""


def _error_kind(e: Exception) -> str:
    """Class of a failed attempt: provider, transport, http, parse or other."""
    if isinstance(e, _ProviderErrorResponse):
        return "provider"
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
    reasoning_effort: str | None = None,
    meta: dict | None = None,
    before_call=None,
    on_response=None,
    provider: dict | None = None,
    timeout: float | None = None,
) -> tuple[dict, int, int]:
    """call_llm that also returns the parse failures and provider errors it retried.

    Returns (parsed, n_parse_fail, n_provider_error). If every attempt fails,
    the RuntimeError carries both counts as attributes.

    reasoning_effort=None is not sent (provider default, logged "default");
    otherwise it goes out as OpenRouter's reasoning.effort. When meta is a
    dict, the successful response's model_snapshot, finish_reason, usage and
    reasoning text are written into it.

    provider: OpenRouter provider-routing object sent as-is in the body (e.g.
    {"order": [...], "only": [...], "allow_fallbacks": false}); None = not
    sent. timeout: seconds for this request; None = the client's
    DEFAULT_TIMEOUT_S. Every record with a response carries "provider" and
    "provider_quantization" (null when the response has none).

    A provider-error response (_is_provider_error: finish_reason "error", or
    0 tokens at 0 cost) is logged with error_kind "provider", retried and
    counted in n_provider_error, never in n_parse_fail.

    Hooks (both optional): before_call() runs before every attempt, retries
    included, and may raise to stop without sending (the exception is not
    retried). on_response(info) runs for every response that arrived, also
    one that then failed to parse (it is billed), with info as in
    _response_info; it runs after the attempt is logged.
    """
    augmented = augment_with_schema(messages, schema)
    # temperature=None: not sent, the provider's own default applies.
    extra = {} if temperature is None else {"temperature": temperature}
    if timeout is not None:
        extra["timeout"] = timeout
    body = {"session_id": session_id[:256]}
    if reasoning_effort is not None:
        body["reasoning"] = {"effort": reasoning_effort}
    if provider is not None:
        body["provider"] = provider
    effort_label = reasoning_effort_label(reasoning_effort)

    last_err = None
    last_finish_reason = None
    n_parse_fail = 0
    n_provider_error = 0
    for attempt in range(max_retries):
        resp = None
        if before_call is not None:
            before_call()
        # Only the API call and the parsing are inside the try: a failing log
        # write must not trigger a retry (it would bill the same call again).
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=augmented,
                max_tokens=max_tokens,
                **extra,
                response_format={"type": "json_object"},
                # X-OpenRouter-Metadata: the response then names the provider
                # that served it (openrouter_metadata, "Router Metadata" docs).
                extra_headers={"X-Title": "GABM public goods",
                               "X-OpenRouter-Metadata": "enabled"},
                extra_body=body,
            )
            if _is_provider_error(resp):
                raise _ProviderErrorResponse(
                    f"provider error response (finish_reason={_finish_reason(resp)!r}, "
                    f"usage={_usage_dict(getattr(resp, 'usage', None))!r})")
            raw = resp.choices[0].message.content
            if raw is None or not raw.strip():
                raise _EmptyResponseError("empty response content")
            parsed, degraded = _parse_json_strict(raw)
        except Exception as e:
            last_err = e
            last_finish_reason = _finish_reason(resp)
            kind = _error_kind(e)
            if kind == "parse":
                n_parse_fail += 1
            elif kind == "provider":
                n_provider_error += 1
            record = {
                "ts": time.time(), "model": model, "session_id": session_id,
                "temperature": temperature_label(temperature), "messages": messages,
                "error_type": type(e).__name__, "error_kind": kind,
                "error": str(e), "attempt": attempt, "retrying": True,
                "finish_reason": _finish_reason(resp),
                "reasoning_effort": effort_label,
            }
            if isinstance(e, openai.APIStatusError):
                record["status_code"] = e.status_code
            if resp is not None:
                record["usage"] = _usage_dict(getattr(resp, "usage", None))
                record["model_snapshot"] = getattr(resp, "model", None)
                record["provider"], record["provider_quantization"] = _provider_info(resp)
            _append_log(record)
            if resp is not None and on_response is not None:
                on_response(_response_info(resp))
            time.sleep(1.5 * (attempt + 1))
            continue
        provider_name, quantization = _provider_info(resp)
        _append_log({
            "ts": time.time(), "model": model, "session_id": session_id,
            "temperature": temperature_label(temperature), "messages": messages,
            "response_raw": raw, "response_parsed": parsed,
            "usage": _usage_dict(getattr(resp, "usage", None)),
            "model_snapshot": getattr(resp, "model", None),
            "attempt": attempt, "degraded": degraded,
            "finish_reason": _finish_reason(resp),
            "reasoning_effort": effort_label,
            "provider": provider_name, "provider_quantization": quantization,
        })
        if on_response is not None:
            on_response(_response_info(resp))
        if meta is not None:
            meta.update({
                "model_snapshot": getattr(resp, "model", None),
                "finish_reason": _finish_reason(resp),
                "usage": _usage_dict(getattr(resp, "usage", None)),
                "reasoning": _reasoning_text(resp),
            })
        return parsed, n_parse_fail, n_provider_error
    final = {
        "ts": time.time(), "model": model, "session_id": session_id,
        "error_type": type(last_err).__name__, "error_kind": _error_kind(last_err),
        "error": str(last_err), "attempt": max_retries, "messages": messages,
        "finish_reason": last_finish_reason,
        "reasoning_effort": effort_label,
    }
    if isinstance(last_err, openai.APIStatusError):
        final["status_code"] = last_err.status_code
    _append_log(final)
    err = RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")
    err.n_parse_fail = n_parse_fail
    err.n_provider_error = n_provider_error
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
    reasoning_effort: str | None = None,
    meta: dict | None = None,
    before_call=None,
    on_response=None,
    provider: dict | None = None,
    timeout: float | None = None,
) -> dict:
    """Call OpenRouter with structured JSON output. Retries on transient errors.

    temperature=None (default) is not sent, so the provider's own default
    applies and the log says "default"; an explicit number is sent and logged.

    Every record (success and failed attempt) carries finish_reason from
    choices[0].finish_reason, null when the response lacks it or never came.

    Every failed attempt is logged with error_type (exception class name) and
    error_kind (provider / transport / http / parse / other; status_code for
    http). Parse failures and provider errors are retried; use
    call_llm_valid(..., return_parse_fail=True) or its counts dict to get
    their counts.
    """
    parsed, _, _ = _call_llm_counted(
        model, messages, schema=schema, session_id=session_id,
        temperature=temperature, max_tokens=max_tokens, max_retries=max_retries,
        reasoning_effort=reasoning_effort, meta=meta,
        before_call=before_call, on_response=on_response,
        provider=provider, timeout=timeout)
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
    reasoning_effort: str | None = None,
    meta: dict | None = None,
    before_call=None,
    on_response=None,
    provider: dict | None = None,
    timeout: float | None = None,
    counts: dict | None = None,
) -> tuple[dict, int] | tuple[dict, int, int]:
    """call_llm, re-requesting payloads for which is_valid(parsed) is False.

    Returns (parsed, n_invalid). Invalid payloads are never coded as decisions;
    store n_invalid with the row and report it. With return_parse_fail=True it
    returns (parsed, n_invalid, n_parse_fail), where n_parse_fail counts the
    unparseable responses retried across all calls. It is a separate count: it
    is not added to n_invalid.

    counts: when a dict, it is kept up to date with "n_invalid",
    "n_parse_fail" and "n_provider_error" (provider-error responses retried;
    a third separate count), also when the call finally fails.

    reasoning_effort, meta, provider, timeout and the before_call /
    on_response hooks are passed through to the underlying call; meta ends up
    holding the metadata of the accepted (last) response.
    """
    call: dict = {}
    n_parse_fail = 0
    n_provider_error = 0
    if counts is not None:
        counts.update(n_invalid=0, n_parse_fail=0, n_provider_error=0)
    for n_invalid in range(max_invalid + 1):
        try:
            call, n_pf, n_pe = _call_llm_counted(
                model, messages, schema=schema, session_id=session_id,
                temperature=temperature, max_tokens=max_tokens,
                reasoning_effort=reasoning_effort, meta=meta,
                before_call=before_call, on_response=on_response,
                provider=provider, timeout=timeout)
        except RuntimeError as e:
            if counts is not None:
                counts.update(
                    n_invalid=n_invalid,
                    n_parse_fail=n_parse_fail + getattr(e, "n_parse_fail", 0),
                    n_provider_error=n_provider_error + getattr(e, "n_provider_error", 0))
            raise
        n_parse_fail += n_pf
        n_provider_error += n_pe
        if counts is not None:
            counts.update(n_invalid=n_invalid, n_parse_fail=n_parse_fail,
                          n_provider_error=n_provider_error)
        if is_valid(call):
            if return_parse_fail:
                return call, n_invalid, n_parse_fail
            return call, n_invalid
        _append_log({
            "ts": time.time(), "model": model, "session_id": session_id,
            "event": "invalid_payload", "invalid": True,
            "n_invalid": n_invalid, "response_parsed": call,
        })
    if counts is not None:
        counts["n_invalid"] = max_invalid + 1
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
