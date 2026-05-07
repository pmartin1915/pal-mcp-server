"""Tests for utils/call_budget_io.py — the impure I/O shell for the budget gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from utils.call_budget_io import (
    _DEFAULT_BUDGETS,
    append_entry,
    get_ledger_path,
    load_config_from_env,
    read_ledger,
)

# ---------------------------------------------------------------------------
# get_ledger_path
# ---------------------------------------------------------------------------


class TestGetLedgerPath:
    def test_default_path_is_repo_root(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PAL_LEDGER_PATH", None)
            path = get_ledger_path()
        assert path.name == ".pal-call-log.jsonl"
        # Should be at project root, not inside utils/
        assert path.parent.name == "pal-mcp-server"

    def test_custom_path_from_env(self, tmp_path):
        custom = str(tmp_path / "custom.jsonl")
        with patch.dict(os.environ, {"PAL_LEDGER_PATH": custom}):
            path = get_ledger_path()
        assert path == Path(custom).resolve()

    def test_tilde_expansion(self, tmp_path):
        # ~ should be expanded
        with patch.dict(os.environ, {"PAL_LEDGER_PATH": "~/pal.jsonl"}):
            path = get_ledger_path()
        assert "~" not in str(path)

    def test_empty_env_var_uses_default(self):
        with patch.dict(os.environ, {"PAL_LEDGER_PATH": "   "}):
            path = get_ledger_path()
        assert path.name == ".pal-call-log.jsonl"


# ---------------------------------------------------------------------------
# read_ledger
# ---------------------------------------------------------------------------


class TestReadLedger:
    def test_missing_file_returns_empty_string(self, tmp_path):
        result = read_ledger(tmp_path / "nonexistent.jsonl")
        assert result == ""

    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "ledger.jsonl"
        f.write_text('{"ts":"2026-05-06T00:00:00+00:00","model":"gemini-2.5-pro"}\n', encoding="utf-8")
        assert read_ledger(f) != ""

    def test_returns_full_content(self, tmp_path):
        f = tmp_path / "ledger.jsonl"
        content = '{"ts":"2026-05-06T01:00:00+00:00","model":"gemini-2.5-pro"}\n{"ts":"2026-05-06T02:00:00+00:00","model":"gemini-2.5-flash"}\n'
        f.write_text(content, encoding="utf-8")
        assert read_ledger(f) == content

    def test_empty_file_returns_empty_string(self, tmp_path):
        f = tmp_path / "ledger.jsonl"
        f.write_text("", encoding="utf-8")
        assert read_ledger(f) == ""

    def test_permission_error_returns_empty_and_warns(self, tmp_path, caplog):
        import logging

        f = tmp_path / "ledger.jsonl"
        f.write_text("data", encoding="utf-8")
        with patch("pathlib.Path.read_text", side_effect=OSError("permission denied")):
            with caplog.at_level(logging.WARNING):
                result = read_ledger(f)
        assert result == ""
        assert "permission denied" in caplog.text.lower() or "budget check bypassed" in caplog.text


# ---------------------------------------------------------------------------
# append_entry
# ---------------------------------------------------------------------------


class TestAppendEntry:
    def test_creates_file_if_missing(self, tmp_path):
        path = tmp_path / "new.jsonl"
        append_entry(path, "gemini-2.5-pro", "2026-05-06T10:00:00+00:00")
        assert path.exists()

    def test_written_entry_is_valid_json(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        append_entry(path, "gemini-2.5-pro", "2026-05-06T10:00:00+00:00")
        line = path.read_text(encoding="utf-8").strip()
        obj = json.loads(line)
        assert obj["model"] == "gemini-2.5-pro"
        assert obj["ts"] == "2026-05-06T10:00:00+00:00"

    def test_multiple_appends_produce_multiple_lines(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        append_entry(path, "gemini-2.5-pro", "2026-05-06T10:00:00+00:00")
        append_entry(path, "gemini-2.5-flash", "2026-05-06T11:00:00+00:00")
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 2

    def test_ioerror_is_swallowed(self, tmp_path, caplog):
        import logging
        from pathlib import Path

        path = tmp_path / "ledger.jsonl"
        with patch.object(Path, "open", side_effect=OSError("disk full")):
            with caplog.at_level(logging.WARNING, logger="utils.call_budget_io"):
                append_entry(path, "gemini-2.5-pro", "2026-05-06T10:00:00+00:00")
        # Must not raise; warning should be logged
        assert "disk full" in caplog.text or "ledger" in caplog.text.lower()

    def test_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c" / "ledger.jsonl"
        append_entry(nested, "gemini-2.5-pro", "2026-05-06T10:00:00+00:00")
        assert nested.exists()


# ---------------------------------------------------------------------------
# load_config_from_env
# ---------------------------------------------------------------------------


class TestLoadConfigFromEnv:
    def _clean_env(self):
        """Remove all budget env vars so tests start from a known state."""
        keys = ["PAL_BUDGET_ENABLED", "PAL_DAILY_BUDGET_GEMINI_25_PRO", "PAL_DAILY_BUDGET_GEMINI_25_FLASH"]
        return dict.fromkeys(keys)

    def test_defaults_when_no_env_vars(self):
        base = self._clean_env()
        with patch.dict(os.environ, {}, clear=False):
            for k in base:
                os.environ.pop(k, None)
            cfg = load_config_from_env()
        assert cfg["enabled"] is True
        assert cfg["budgets"]["gemini-2.5-pro"] == _DEFAULT_BUDGETS["gemini-2.5-pro"]
        assert cfg["budgets"]["gemini-2.5-flash"] == _DEFAULT_BUDGETS["gemini-2.5-flash"]

    def test_enabled_false_variants(self):
        for val in ("false", "False", "FALSE", "0", "no", "NO", "off", "OFF"):
            with patch.dict(os.environ, {"PAL_BUDGET_ENABLED": val}):
                cfg = load_config_from_env()
            assert cfg["enabled"] is False, f"Expected False for PAL_BUDGET_ENABLED={val!r}"

    def test_enabled_true_variants(self):
        for val in ("true", "True", "1", "yes", "on", "anything"):
            with patch.dict(os.environ, {"PAL_BUDGET_ENABLED": val}):
                cfg = load_config_from_env()
            assert cfg["enabled"] is True, f"Expected True for PAL_BUDGET_ENABLED={val!r}"

    def test_custom_pro_budget(self):
        with patch.dict(os.environ, {"PAL_DAILY_BUDGET_GEMINI_25_PRO": "42"}):
            cfg = load_config_from_env()
        assert cfg["budgets"]["gemini-2.5-pro"] == 42

    def test_custom_flash_budget(self):
        with patch.dict(os.environ, {"PAL_DAILY_BUDGET_GEMINI_25_FLASH": "300"}):
            cfg = load_config_from_env()
        assert cfg["budgets"]["gemini-2.5-flash"] == 300

    def test_invalid_budget_value_uses_default_and_warns(self, caplog):
        import logging

        with patch.dict(os.environ, {"PAL_DAILY_BUDGET_GEMINI_25_PRO": "not-a-number"}):
            with caplog.at_level(logging.WARNING):
                cfg = load_config_from_env()
        assert cfg["budgets"]["gemini-2.5-pro"] == _DEFAULT_BUDGETS["gemini-2.5-pro"]
        assert "not-a-number" in caplog.text or "invalid" in caplog.text.lower()

    def test_config_shape_compatible_with_evaluate_budget(self):
        """Smoke-test that load_config_from_env() output is accepted by evaluate_budget()."""
        from utils.call_budget import evaluate_budget

        cfg = load_config_from_env()
        result = evaluate_budget(0, "gemini-2.5-pro", cfg)
        assert "allowed" in result
        assert "reason" in result
        assert "remaining" in result
