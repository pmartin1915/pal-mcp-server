"""Per-call daily budget gate (pure functions, no I/O, no env reads).

Layer 2 of the PAL cost-safety stack. Designed 2026-05-06 after a Google Cloud
billing incident where PAL routed enough calls through a billed Gemini key to
exceed free-tier-within-Tier-1 limits. This module is the in-process count +
decision logic; `call_budget_io` is the impure shell that handles ledger files
and env reads. Pure / impure separation mirrors the budget-dispatcher's
`drift-engine.mjs` / `drift-engine-cli.mjs` precedent.

Day boundary is UTC midnight, not local time. All timestamps are ISO 8601 with
explicit timezone (entries lacking timezone info are treated as not-today).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

# Gate decision reason codes. Constants so callers can match exactly.
BUDGET_GATE_OK = "ok"
BUDGET_GATE_EXHAUSTED = "exhausted"
BUDGET_GATE_DISABLED = "disabled"
BUDGET_GATE_LEDGER_CORRUPT = "ledger-corrupt"


def is_today_utc(ts_iso: str, now_utc: datetime) -> bool:
    """Return True iff `ts_iso` falls within the current UTC day.

    The window is `[start_of_today_utc, start_of_tomorrow_utc)` — inclusive at
    00:00:00Z of today, exclusive at 00:00:00Z of tomorrow. Returns False on
    parse failure or on naive (no tzinfo) timestamps.
    """
    try:
        normalized = ts_iso[:-1] + "+00:00" if ts_iso.endswith("Z") else ts_iso
        ts = datetime.fromisoformat(normalized)
    except (ValueError, TypeError, AttributeError):
        return False
    if ts.tzinfo is None:
        return False
    ts_utc = ts.astimezone(timezone.utc)
    start_today = now_utc.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_tomorrow = start_today + timedelta(days=1)
    return start_today <= ts_utc < start_tomorrow


def parse_ledger_line(line: str) -> dict | None:
    """Parse a single JSONL line into a dict.

    Returns None on empty input, whitespace-only input, JSON parse failure, or
    when the parsed value is not a dict (e.g., bare array or scalar).
    """
    if not isinstance(line, str):
        return None
    stripped = line.strip()
    if not stripped:
        return None
    try:
        obj = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def parse_ledger(jsonl_text: str) -> list[dict]:
    """Parse multi-line JSONL text into a list of dicts.

    Lines that fail to parse are silently dropped. Order is preserved across
    surviving entries.
    """
    if not isinstance(jsonl_text, str):
        return []
    results: list[dict] = []
    for line in jsonl_text.splitlines():
        entry = parse_ledger_line(line)
        if entry is not None:
            results.append(entry)
    return results


def tally_today(entries: list[dict], model: str, now_utc: datetime) -> int:
    """Count entries whose `ts` falls in the current UTC day AND whose `model`
    matches exactly.

    Entries with non-string `ts`, missing or mismatched `model`, or unparseable
    timestamps are skipped silently.
    """
    if not entries:
        return 0
    count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ts = entry.get("ts")
        if not isinstance(ts, str):
            continue
        if entry.get("model") != model:
            continue
        if is_today_utc(ts, now_utc):
            count += 1
    return count


def evaluate_budget(daily_count: int, model: str, config: dict) -> dict[str, Any]:
    """Decide whether a call is allowed under the daily budget.

    `config` shape:
        {
            "enabled": bool,                  # soft kill switch
            "budgets": {model_name: int, ...} # per-model daily caps
        }

    Returns:
        {
            "allowed": bool,
            "reason": str,        # one of the BUDGET_GATE_* constants
            "remaining": int,     # calls left today; -1 when not meaningful
        }

    Behavior:
    - If `enabled` is False → allow with reason DISABLED (kill switch path).
    - If `model` is not in `budgets` → allow with reason OK and remaining=-1.
      (Non-Gemini providers fall here per spec; expected, not an error.)
    - Otherwise → allow if `daily_count < limit`, else exhausted.
    """
    if not isinstance(config, dict) or not config.get("enabled", True):
        return {
            "allowed": True,
            "reason": BUDGET_GATE_DISABLED,
            "remaining": -1,
        }
    budgets = config.get("budgets") or {}
    if not isinstance(budgets, dict):
        budgets = {}
    limit = budgets.get(model)
    if limit is None:
        return {
            "allowed": True,
            "reason": BUDGET_GATE_OK,
            "remaining": -1,
        }
    try:
        limit_int = int(limit)
    except (ValueError, TypeError):
        return {
            "allowed": True,
            "reason": BUDGET_GATE_OK,
            "remaining": -1,
        }
    if daily_count >= limit_int:
        return {
            "allowed": False,
            "reason": BUDGET_GATE_EXHAUSTED,
            "remaining": 0,
        }
    return {
        "allowed": True,
        "reason": BUDGET_GATE_OK,
        "remaining": max(0, limit_int - daily_count),
    }
