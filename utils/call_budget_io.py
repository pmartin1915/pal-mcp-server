"""Impure I/O shell for the PAL daily budget gate.

Handles file system access and environment variable reads.
Pure decision logic lives in `call_budget.py`.

Ledger format: JSONL, one entry per line.
  {"ts": "2026-05-06T14:22:01.123456+00:00", "model": "gemini-2.5-pro"}
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_LEDGER_FILENAME = ".pal-call-log.jsonl"

# Hardcoded env-var names so callers get clear variable names in .env
_BUDGET_ENV_VARS: dict[str, str] = {
    "gemini-2.5-pro": "PAL_DAILY_BUDGET_GEMINI_25_PRO",
    "gemini-2.5-flash": "PAL_DAILY_BUDGET_GEMINI_25_FLASH",
}

# Conservative per-machine defaults — well below Google's free-tier limit per machine
_DEFAULT_BUDGETS: dict[str, int] = {
    "gemini-2.5-pro": 60,
    "gemini-2.5-flash": 150,
}


def get_ledger_path() -> Path:
    """Resolve the ledger file path from PAL_LEDGER_PATH env var or default to repo root."""
    raw = os.environ.get("PAL_LEDGER_PATH", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    repo_root = Path(__file__).parent.parent
    return repo_root / _DEFAULT_LEDGER_FILENAME


def read_ledger(path: Path) -> str:
    """Read the JSONL ledger, returning empty string if missing or unreadable.

    On IOError (not FileNotFoundError), logs a warning and returns empty string
    so the budget check fails-open: the caller proceeds and Layer A (Google Cloud
    quota cap) remains the hard stop.
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        logger.warning("Could not read ledger %s: %s — budget check bypassed (fail-open)", path, exc)
        return ""


def append_entry(path: Path, model: str, ts_iso: str) -> None:
    """Append one JSONL entry to the ledger. Best-effort: never raises."""
    import json

    entry = json.dumps({"ts": ts_iso, "model": model})
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(entry + "\n")
    except OSError as exc:
        logger.warning("Could not append to ledger %s: %s — call not logged", path, exc)


def load_config_from_env() -> dict:
    """Build a budget config dict from environment variables.

    Returns a dict compatible with `call_budget.evaluate_budget()`:
        {"enabled": bool, "budgets": {"gemini-2.5-pro": int, ...}}

    Reads:
        PAL_BUDGET_ENABLED      — "false"/"0"/"no"/"off" disables (default: enabled)
        PAL_DAILY_BUDGET_GEMINI_25_PRO   — int, daily Pro cap per machine
        PAL_DAILY_BUDGET_GEMINI_25_FLASH — int, daily Flash cap per machine
    """
    enabled_raw = os.environ.get("PAL_BUDGET_ENABLED", "true").strip().lower()
    enabled = enabled_raw not in ("false", "0", "no", "off")

    budgets: dict[str, int] = {}
    for model, env_var in _BUDGET_ENV_VARS.items():
        raw = os.environ.get(env_var, "").strip()
        if raw:
            try:
                budgets[model] = int(raw)
            except ValueError:
                logger.warning("Invalid %s value %r — using default %d", env_var, raw, _DEFAULT_BUDGETS[model])
                budgets[model] = _DEFAULT_BUDGETS[model]
        else:
            budgets[model] = _DEFAULT_BUDGETS[model]

    return {"enabled": enabled, "budgets": budgets}
