"""
OpenRouter Batch API path: submit, persist the id, wait, download, match.

Source of the endpoint and field names: workspace/gorev_openrouter_batch.md
(task #21). Facts that matter here:
  * one POST /batches with a JSON body (no JSONL file, no upload step); the
    model is a batch-level field written WITHOUT the ":batch" suffix, the
    provider is pinned with provider.only
  * results come inline in GET /batches/{id} once the status is "completed"
  * failed / expired / cancelled batches return results = null, so the whole
    batch has to be sent again; OpenRouter deletes results 30 days after the
    batch is *created*, so they are saved to disk the moment they arrive
  * Google models: all requests of a batch must share one response_format

Contract (same spirit as llm_client):
  * the batch id is written to logs/batches.jsonl right after the POST answers
    and before any waiting
  * no temperature is sent; the logs say "default"
  * every request result is logged to logs/raw_calls.jsonl (batch_id,
    custom_id, requested model, model_snapshot, finish_reason, usage, raw)
  * invalid answers are counted by reason and re-queued into the next batch,
    never coded as decisions

Everything the research report marked "(doğrulanamadı)" is a constant or a
BATCH_MODELS entry below, so it can be changed in one place:
  API_BASE / ENDPOINT, REASONING_FIELD_STYLE, the provider.only slugs and
  reasoning_effort values in BATCH_MODELS, POLL_INTERVAL_S, and where the
  snapshot / reasoning token counts sit in a result (_extract_*).
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

import llm_client

PROJECT_DIR = Path(__file__).parent
BATCH_LOG_PATH = PROJECT_DIR / "logs" / "batches.jsonl"
BATCH_RAW_DIR = PROJECT_DIR / "logs" / "batch_raw"

API_BASE = "https://openrouter.ai/api/v1"
ENDPOINT = "/v1/chat/completions"  # value of the "endpoint" field of a batch
COMPLETION_WINDOW = "24h"          # the only accepted value
MAX_PAYLOAD_BYTES = 200 * 1024 * 1024  # 413 above this (documented)

# (doğrulanamadı) Whether the batch body takes the flat `reasoning_effort` or
# the `reasoning: {"effort": ...}` object is not shown by a batch example.
# "reasoning_effort" or "reasoning".
REASONING_FIELD_STYLE = "reasoning_effort"

# (doğrulanamadı) No documented polling interval. OpenRouter's own numbers:
# median 7 min, p90 1 h, p99 10.3 h, hard limit 24 h.
POLL_INTERVAL_S = 60.0
MAX_WAIT_S = 26 * 3600.0
MAX_POLL_ERRORS = 10  # consecutive transient GET failures before giving up

ACTIVE_STATUSES = {"validating", "in_progress", "finalizing", "cancelling"}
FAILED_STATUSES = {"failed", "expired", "cancelled"}  # results null: resend all
_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}

REASONS = ("provider_error", "bad_json", "invalid_value")

# One place for the per-model batch settings.
#   model             base slug, no ":batch" suffix (llm_client.MODELS has it)
#   provider_only     provider.only; no fallback if none matches.
#                     (doğrulanamadı) "deepinfra" and "openai" are inferred
#                     (the docs show "deepinfra/turbo" and "google-vertex"),
#                     the exact spelling is for the plumbing test to confirm.
#   reasoning_effort  fixed explicitly: the default effort is undocumented for
#                     all three. "high" is the one level the docs support for
#                     every model (Gemini 3: direct to thinkingLevel; DeepSeek
#                     V4 sibling pages: "high and xhigh supported"; Luna: only
#                     "at higher reasoning effort" is described).
#                     (doğrulanamadı) per-model allowed values.
#   max_tokens        reasoning tokens count against it on most providers, and
#                     the answer is a few dozen tokens of JSON. 16000 leaves
#                     room for a long "high" reasoning pass plus the answer;
#                     it is an estimate to calibrate with the plumbing test
#                     (look at usage reasoning tokens and finish_reason).
BATCH_MODELS = {
    "deepseek": {
        "model": "deepseek/deepseek-v4.1-flash",
        "provider_only": ["deepinfra"],
        "reasoning_effort": "high",
        "max_tokens": 16000,
    },
    "gpt": {
        "model": "openai/gpt-6-luna",
        "provider_only": ["openai"],
        "reasoning_effort": "high",
        "max_tokens": 16000,
    },
    "gemini": {
        "model": "google/gemini-3.8-flash",
        "provider_only": ["google-vertex"],
        "reasoning_effort": "high",
        "max_tokens": 16000,
    },
}

JSON_OBJECT = {"type": "json_object"}

_registry_lock = threading.Lock()


class BatchValidationError(ValueError):
    """The requests cannot go into one batch (checked before sending)."""


class BatchApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None,
                 transient: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.transient = transient


class BatchWaitTimeout(BatchApiError):
    """The batch did not finish within max_wait_s; its id is already on disk."""


@dataclass
class BatchItem:
    """One request: custom_id, chat messages, the JSON schema asked for."""
    custom_id: str
    messages: list[dict]
    schema: dict
    step: str  # e.g. "contribution", "punishment"; one step type per batch
    response_format: dict = field(default_factory=lambda: dict(JSON_OBJECT))


@dataclass
class BatchRunResult:
    parsed: dict[str, dict]      # custom_id -> valid payload
    unresolved: dict[str, str]   # custom_id -> last reason, attempts used up
    counts: dict[str, int]       # reason counters + n_batch_resubmit etc.
    attempts: dict[str, int]     # custom_id -> number of batches it was sent in
    batch_ids: list[str]

    @property
    def ok(self) -> bool:
        return not self.unresolved


def _append_jsonl(path: Path, record: dict, durable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _registry_lock:
        with open(path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            if durable:
                f.flush()
                os.fsync(f.fileno())


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def validate_items(items: list[BatchItem]) -> None:
    """Raises BatchValidationError before anything is sent."""
    if not items:
        raise BatchValidationError("no requests")
    ids = [it.custom_id for it in items]
    if any(not isinstance(i, str) or not i for i in ids):
        raise BatchValidationError("custom_id must be a non-empty string")
    if len(set(ids)) != len(ids):
        raise BatchValidationError("custom_id must be unique within a batch")
    steps = {it.step for it in items}
    if len(steps) != 1:
        raise BatchValidationError(f"step types must not be mixed in a batch: {sorted(steps)}")
    formats = {_canon(it.response_format) for it in items}
    if len(formats) != 1:
        raise BatchValidationError(
            f"all requests of a batch must share one response_format: {sorted(formats)}")


def build_payload(config: dict, items: list[BatchItem]) -> dict:
    """The POST /batches body. No temperature, no body-level model."""
    validate_items(items)
    effort = config["reasoning_effort"]
    if REASONING_FIELD_STYLE == "reasoning":
        reasoning = {"reasoning": {"effort": effort}}
    else:
        reasoning = {"reasoning_effort": effort}
    requests = []
    for it in items:
        body = {
            "messages": llm_client.augment_with_schema(it.messages, it.schema),
            "response_format": it.response_format,
            "max_tokens": config["max_tokens"],
            **reasoning,
        }
        requests.append({"custom_id": it.custom_id, "body": body})
    payload = {
        "endpoint": ENDPOINT,
        "model": config["model"],
        "completion_window": COMPLETION_WINDOW,
        "provider": {"only": list(config["provider_only"])},
        "requests": requests,
    }
    if len(json.dumps(payload).encode()) > MAX_PAYLOAD_BYTES:
        raise BatchValidationError("batch payload exceeds the 200 MB limit")
    return payload


class OpenRouterBatchHttp:
    """Thin HTTP layer. `http` can be any httpx.Client (tests: MockTransport)."""

    def __init__(self, api_key: str | None = None, *, http: httpx.Client | None = None,
                 base_url: str = API_BASE, timeout: float = 60.0):
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise BatchApiError("no OpenRouter API key given")
        self._http = http or httpx.Client(timeout=timeout)
        self._base = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "GABM public goods",
        }

    @staticmethod
    def _fail(resp: httpx.Response) -> BatchApiError:
        return BatchApiError(
            f"HTTP {resp.status_code}: {resp.text[:300]}", status_code=resp.status_code,
            transient=resp.status_code in _TRANSIENT_STATUS)

    def create(self, payload: dict) -> dict:
        """POST /batches. Only 429 (rejected before creating anything) is retried:
        retrying after a timeout or 5xx could open, and bill, a second batch."""
        for attempt in range(3):
            try:
                resp = self._http.post(f"{self._base}/batches", json=payload,
                                       headers=self._headers)
            except httpx.TransportError as e:
                raise BatchApiError(
                    f"batch create failed in transit ({type(e).__name__}); a batch may "
                    f"or may not exist, check the OpenRouter batch list: {e}") from e
            if resp.status_code == 429 and attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            if not 200 <= resp.status_code < 300:
                raise self._fail(resp)
            return resp.json()
        raise AssertionError("unreachable")

    def get(self, batch_id: str) -> dict:
        try:
            resp = self._http.get(f"{self._base}/batches/{batch_id}", headers=self._headers)
        except httpx.TransportError as e:
            raise BatchApiError(f"{type(e).__name__}: {e}", transient=True) from e
        if resp.status_code != 200:
            raise self._fail(resp)
        return resp.json()


# --- result extraction ------------------------------------------------------
# (doğrulanamadı) whether a batch result body carries `model` and
# `usage.completion_tokens_details.reasoning_tokens`; both fall back to None.

def _extract_snapshot(body: dict | None) -> str | None:
    return body.get("model") if isinstance(body, dict) else None


def _extract_reasoning_tokens(usage) -> int | None:
    if not isinstance(usage, dict):
        return None
    details = usage.get("completion_tokens_details")
    if not isinstance(details, dict):
        return None
    return details.get("reasoning_tokens")


def classify_result(row: dict | None, is_valid=None) -> dict:
    """Judge one result row. Returns a dict with:
      reason   None if valid, else provider_error / bad_json / invalid_value
      detail   short human text for the reason
      parsed, degraded, raw, finish_reason, usage, snapshot
    """
    out = {"reason": None, "detail": None, "parsed": None, "degraded": None,
           "raw": None, "finish_reason": None, "usage": None, "snapshot": None}
    if row is None:
        out.update(reason="provider_error", detail="no result row for this custom_id")
        return out
    resp = row.get("response")
    err = row.get("error")
    body = resp.get("body") if isinstance(resp, dict) else None
    out["snapshot"] = _extract_snapshot(body)
    out["usage"] = body.get("usage") if isinstance(body, dict) else None
    if err or not isinstance(resp, dict) or resp.get("status_code") != 200 \
            or not isinstance(body, dict):
        if isinstance(err, dict):
            detail = f"{err.get('error_type') or err.get('type')}: {err.get('message')}"
        elif isinstance(resp, dict) and resp.get("status_code") not in (None, 200):
            detail = f"status_code {resp.get('status_code')}"
        else:
            detail = "row has no usable response"
        out.update(reason="provider_error", detail=detail)
        return out
    choices = body.get("choices")
    if not choices or not isinstance(choices[0], dict):
        out.update(reason="provider_error", detail="response has no choices")
        return out
    choice = choices[0]
    out["finish_reason"] = choice.get("finish_reason")
    content = (choice.get("message") or {}).get("content")
    out["raw"] = content
    if out["finish_reason"] == "length":
        out.update(reason="bad_json", detail="finish_reason=length (truncated)")
        return out
    if content is None or not str(content).strip():
        out.update(reason="bad_json", detail="empty content")
        return out
    try:
        parsed, degraded = llm_client._parse_json_strict(content)
    except json.JSONDecodeError as e:
        out.update(reason="bad_json", detail=f"JSONDecodeError: {e}")
        return out
    out["degraded"] = degraded
    if not isinstance(parsed, dict):
        out.update(reason="bad_json", detail=f"payload is {type(parsed).__name__}, not an object")
        return out
    out["parsed"] = parsed
    if is_valid is not None:
        try:
            ok = bool(is_valid(parsed))
        except Exception as e:  # a validator tripping on a missing key = invalid
            out.update(reason="invalid_value", detail=f"validator raised {type(e).__name__}: {e}")
            return out
        if not ok:
            out.update(reason="invalid_value", detail="validator rejected the payload")
    return out


class BatchRunner:
    def __init__(self, http: OpenRouterBatchHttp | None = None, *,
                 models: dict | None = None,
                 poll_interval_s: float = POLL_INTERVAL_S,
                 max_wait_s: float = MAX_WAIT_S,
                 max_poll_errors: int = MAX_POLL_ERRORS):
        self.http = http or OpenRouterBatchHttp()
        self.models = models or BATCH_MODELS
        self.poll_interval_s = poll_interval_s
        self.max_wait_s = max_wait_s
        self.max_poll_errors = max_poll_errors

    # -- single batch --------------------------------------------------------
    def submit(self, model_key: str, items: list[BatchItem], attempt: int = 1) -> str:
        """Send one batch and write its id to logs/batches.jsonl before returning."""
        config = self.models[model_key]
        payload = build_payload(config, items)  # raises before any API call
        created = self.http.create(payload)
        batch_id = created["id"]
        _append_jsonl(BATCH_LOG_PATH, {
            "event": "submitted", "ts": time.time(), "batch_id": batch_id,
            "model": config["model"], "model_key": model_key,
            "provider_only": config["provider_only"], "step": items[0].step,
            "attempt": attempt, "status": created.get("status"),
            "custom_ids": [it.custom_id for it in items],
        }, durable=True)
        return batch_id

    def wait(self, batch_id: str) -> dict:
        """Poll until a terminal status; returns the last GET /batches/{id} body."""
        start = time.monotonic()
        errors = 0
        while True:
            try:
                batch = self.http.get(batch_id)
            except BatchApiError as e:
                if not e.transient:
                    raise
                errors += 1
                if errors > self.max_poll_errors:
                    raise
            else:
                errors = 0
                status = batch.get("status")
                if status == "completed" or status in FAILED_STATUSES:
                    return batch
                if status not in ACTIVE_STATUSES:
                    raise BatchApiError(f"batch {batch_id}: unknown status {status!r}")
            if time.monotonic() - start > self.max_wait_s:
                raise BatchWaitTimeout(
                    f"batch {batch_id} still not finished after {self.max_wait_s} s")
            time.sleep(self.poll_interval_s)

    @staticmethod
    def save_raw(batch: dict) -> Path:
        """Save the finished batch body (results included) at once."""
        BATCH_RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = BATCH_RAW_DIR / f"{batch['id']}.json"
        path.write_text(json.dumps(batch, ensure_ascii=False))
        return path

    # -- whole run -----------------------------------------------------------
    def run(self, model_key: str, items: list[BatchItem], *, is_valid=None,
            max_attempts: int = 3) -> BatchRunResult:
        """Send items, re-queue what is invalid, until all valid or max_attempts
        batches have been sent (a resent failed batch also uses up an attempt)."""
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        validate_items(items)
        config = self.models[model_key]
        pending = {it.custom_id: it for it in items}
        parsed: dict[str, dict] = {}
        last_reason: dict[str, str] = {}
        sent_in: dict[str, int] = {it.custom_id: 0 for it in items}
        counts = {r: 0 for r in REASONS}
        counts.update(n_batch_resubmit=0, n_batch_failed=0)
        batch_ids: list[str] = []

        for attempt in range(1, max_attempts + 1):
            if not pending:
                break
            batch_items = list(pending.values())
            batch_id = self.submit(model_key, batch_items, attempt=attempt)
            batch_ids.append(batch_id)
            for it in batch_items:
                sent_in[it.custom_id] += 1

            batch = self.wait(batch_id)
            status = batch.get("status")
            raw_path = self.save_raw(batch)
            _append_jsonl(BATCH_LOG_PATH, {
                "event": "finished", "ts": time.time(), "batch_id": batch_id,
                "model": config["model"], "step": batch_items[0].step,
                "attempt": attempt, "status": status, "raw_path": str(raw_path),
                "request_counts": batch.get("request_counts"),
                "usage": batch.get("usage"), "error": batch.get("error"),
            }, durable=True)

            if status in FAILED_STATUSES:
                # No partial results: the whole batch goes again.
                counts["n_batch_failed"] += 1
                for cid in pending:
                    last_reason[cid] = f"batch_{status}"
                if attempt < max_attempts:
                    counts["n_batch_resubmit"] += 1
                continue

            results = batch.get("results")
            if not isinstance(results, list):
                raise BatchApiError(f"batch {batch_id} completed but results is {results!r}")
            by_id = {r.get("custom_id"): r for r in results if isinstance(r, dict)}
            for it in batch_items:
                cid = it.custom_id
                verdict = classify_result(by_id.get(cid), is_valid)
                self._log_request(batch_id, config, it, attempt, by_id.get(cid), verdict)
                reason = verdict["reason"]
                if reason is None:
                    parsed[cid] = verdict["parsed"]
                    del pending[cid]
                else:
                    counts[reason] += 1
                    last_reason[cid] = reason
            for cid in by_id:
                if cid not in sent_in:
                    _append_jsonl(BATCH_LOG_PATH, {
                        "event": "unexpected_custom_id", "ts": time.time(),
                        "batch_id": batch_id, "custom_id": cid})

        return BatchRunResult(
            parsed=parsed,
            unresolved={cid: last_reason.get(cid, "not_sent") for cid in pending},
            counts=counts, attempts=sent_in, batch_ids=batch_ids)

    @staticmethod
    def _log_request(batch_id, config, item, attempt, row, v) -> None:
        resp = (row or {}).get("response") or {}
        record = {
            "ts": time.time(), "endpoint": "batch", "batch_id": batch_id,
            "custom_id": item.custom_id, "step": item.step,
            "model": config["model"], "model_snapshot": v["snapshot"],
            "provider_only": config["provider_only"],
            "reasoning_effort": config["reasoning_effort"],
            "max_tokens": config["max_tokens"],
            "temperature": llm_client.temperature_label(None),
            "messages": item.messages,
            "finish_reason": v["finish_reason"],
            "usage": v["usage"],
            "reasoning_tokens": _extract_reasoning_tokens(v["usage"]),
            "response_raw": v["raw"], "response_parsed": v["parsed"],
            "degraded": v["degraded"], "batch_result_raw": row,
            "request_id": resp.get("request_id") if isinstance(resp, dict) else None,
            "attempt": attempt, "invalid_reason": v["reason"],
            "invalid_detail": v["detail"],
        }
        llm_client._append_log(record)
