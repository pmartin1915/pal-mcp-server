"""Unit tests for utils.call_budget pure functions.

Pure-function tests only — no I/O, no env, no mocks. All time-dependent
assertions inject a fixed `now_utc` to ensure determinism.
"""

from datetime import datetime, timezone

from utils.call_budget import (
    BUDGET_GATE_DISABLED,
    BUDGET_GATE_EXHAUSTED,
    BUDGET_GATE_OK,
    evaluate_budget,
    is_today_utc,
    parse_ledger,
    parse_ledger_line,
    tally_today,
)

# Anchor for all time-dependent tests — Tuesday 2026-05-06 12:00 UTC.
FIXED_NOW = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)


class TestEvaluateBudget:
    def test_under_budget_allows(self):
        decision = evaluate_budget(
            daily_count=10,
            model="gemini-2.5-pro",
            config={"enabled": True, "budgets": {"gemini-2.5-pro": 80}},
        )
        assert decision["allowed"] is True
        assert decision["reason"] == BUDGET_GATE_OK
        assert decision["remaining"] == 70

    def test_at_budget_exhausted(self):
        decision = evaluate_budget(
            daily_count=80,
            model="gemini-2.5-pro",
            config={"enabled": True, "budgets": {"gemini-2.5-pro": 80}},
        )
        assert decision["allowed"] is False
        assert decision["reason"] == BUDGET_GATE_EXHAUSTED
        assert decision["remaining"] == 0

    def test_over_budget_exhausted(self):
        decision = evaluate_budget(
            daily_count=200,
            model="gemini-2.5-pro",
            config={"enabled": True, "budgets": {"gemini-2.5-pro": 80}},
        )
        assert decision["allowed"] is False
        assert decision["reason"] == BUDGET_GATE_EXHAUSTED
        assert decision["remaining"] == 0

    def test_model_not_in_config_allows(self):
        decision = evaluate_budget(
            daily_count=999,
            model="some-non-gemini-model",
            config={"enabled": True, "budgets": {"gemini-2.5-pro": 80}},
        )
        assert decision["allowed"] is True
        assert decision["reason"] == BUDGET_GATE_OK
        assert decision["remaining"] == -1

    def test_disabled_short_circuits(self):
        decision = evaluate_budget(
            daily_count=999_999,
            model="gemini-2.5-pro",
            config={"enabled": False, "budgets": {"gemini-2.5-pro": 80}},
        )
        assert decision["allowed"] is True
        assert decision["reason"] == BUDGET_GATE_DISABLED

    def test_empty_budgets_treated_as_unlisted(self):
        decision = evaluate_budget(
            daily_count=5,
            model="gemini-2.5-pro",
            config={"enabled": True, "budgets": {}},
        )
        assert decision["allowed"] is True
        assert decision["reason"] == BUDGET_GATE_OK


class TestTallyToday:
    def test_empty_entries_returns_zero(self):
        assert tally_today([], "gemini-2.5-pro", FIXED_NOW) == 0

    def test_per_model_filter(self):
        entries = [
            {"ts": "2026-05-06T10:00:00+00:00", "model": "gemini-2.5-pro"},
            {"ts": "2026-05-06T10:30:00+00:00", "model": "gemini-2.5-flash"},
            {"ts": "2026-05-06T11:00:00+00:00", "model": "gemini-2.5-pro"},
        ]
        assert tally_today(entries, "gemini-2.5-pro", FIXED_NOW) == 2
        assert tally_today(entries, "gemini-2.5-flash", FIXED_NOW) == 1

    def test_utc_midnight_boundary_prior_day_excluded(self):
        # 23:59:59 prior day → must NOT be counted as today.
        entries = [{"ts": "2026-05-05T23:59:59+00:00", "model": "gemini-2.5-pro"}]
        assert tally_today(entries, "gemini-2.5-pro", FIXED_NOW) == 0

    def test_utc_midnight_boundary_start_of_today_included(self):
        # 00:00:00 today → MUST be counted.
        entries = [{"ts": "2026-05-06T00:00:00+00:00", "model": "gemini-2.5-pro"}]
        assert tally_today(entries, "gemini-2.5-pro", FIXED_NOW) == 1

    def test_non_string_ts_ignored(self):
        entries = [
            {"ts": None, "model": "gemini-2.5-pro"},
            {"ts": 123456, "model": "gemini-2.5-pro"},
            {"ts": "2026-05-06T10:00:00+00:00", "model": "gemini-2.5-pro"},
        ]
        assert tally_today(entries, "gemini-2.5-pro", FIXED_NOW) == 1

    def test_missing_model_ignored(self):
        entries = [
            {"ts": "2026-05-06T10:00:00+00:00"},
            {"ts": "2026-05-06T10:30:00+00:00", "model": "gemini-2.5-pro"},
        ]
        assert tally_today(entries, "gemini-2.5-pro", FIXED_NOW) == 1

    def test_z_suffix_timestamp_handled(self):
        # The "Z" suffix is canonical ISO 8601; must round-trip correctly.
        entries = [{"ts": "2026-05-06T10:00:00Z", "model": "gemini-2.5-pro"}]
        assert tally_today(entries, "gemini-2.5-pro", FIXED_NOW) == 1


class TestParseLedgerLine:
    def test_well_formed_line_returns_dict(self):
        line = '{"ts":"2026-05-06T10:00:00Z","model":"gemini-2.5-pro"}'
        result = parse_ledger_line(line)
        assert result == {"ts": "2026-05-06T10:00:00Z", "model": "gemini-2.5-pro"}

    def test_malformed_json_returns_none(self):
        assert parse_ledger_line('{"unterminated": ') is None
        assert parse_ledger_line("not json at all") is None

    def test_empty_line_returns_none(self):
        assert parse_ledger_line("") is None

    def test_whitespace_only_line_returns_none(self):
        assert parse_ledger_line("   \t  ") is None

    def test_json_array_returns_none(self):
        # JSONL convention: each line is a dict, not an array.
        assert parse_ledger_line("[1, 2, 3]") is None

    def test_json_scalar_returns_none(self):
        assert parse_ledger_line("42") is None
        assert parse_ledger_line('"just a string"') is None


class TestParseLedger:
    def test_skips_malformed_lines(self):
        text = (
            '{"ts":"2026-05-06T10:00:00Z","model":"gemini-2.5-pro"}\n'
            "garbage line here\n"
            '{"ts":"2026-05-06T11:00:00Z","model":"gemini-2.5-flash"}\n'
        )
        result = parse_ledger(text)
        assert len(result) == 2
        assert result[0]["model"] == "gemini-2.5-pro"
        assert result[1]["model"] == "gemini-2.5-flash"

    def test_preserves_order(self):
        text = (
            '{"n":1}\n'
            '{"n":2}\n'
            '{"n":3}\n'
        )
        result = parse_ledger(text)
        assert [e["n"] for e in result] == [1, 2, 3]

    def test_empty_text_returns_empty_list(self):
        assert parse_ledger("") == []

    def test_only_blank_lines_returns_empty_list(self):
        assert parse_ledger("\n\n\n") == []


class TestIsTodayUtc:
    def test_start_of_today_inclusive(self):
        assert is_today_utc("2026-05-06T00:00:00+00:00", FIXED_NOW) is True

    def test_next_day_midnight_exclusive(self):
        assert is_today_utc("2026-05-07T00:00:00+00:00", FIXED_NOW) is False

    def test_middle_of_today_counted(self):
        assert is_today_utc("2026-05-06T18:30:45+00:00", FIXED_NOW) is True

    def test_yesterday_excluded(self):
        assert is_today_utc("2026-05-05T18:00:00+00:00", FIXED_NOW) is False

    def test_malformed_timestamp_returns_false(self):
        assert is_today_utc("not a timestamp", FIXED_NOW) is False
        assert is_today_utc("", FIXED_NOW) is False

    def test_naive_timestamp_returns_false(self):
        # No tzinfo — must NOT be guessed as UTC. Fail closed → not-today.
        assert is_today_utc("2026-05-06T12:00:00", FIXED_NOW) is False

    def test_z_suffix_handled(self):
        assert is_today_utc("2026-05-06T12:00:00Z", FIXED_NOW) is True

    def test_non_utc_offset_normalized(self):
        # 2026-05-06T20:00:00-05:00 == 2026-05-07T01:00:00+00:00 → tomorrow → False.
        assert is_today_utc("2026-05-06T20:00:00-05:00", FIXED_NOW) is False
        # 2026-05-06T05:00:00-05:00 == 2026-05-06T10:00:00+00:00 → today → True.
        assert is_today_utc("2026-05-06T05:00:00-05:00", FIXED_NOW) is True


class TestDeterminism:
    def test_injected_now_decouples_from_wall_clock(self):
        """Verify that tally_today's result depends only on the injected `now_utc`,
        not on the actual current time. Critical for reproducible tests."""
        entries = [{"ts": "2026-05-06T10:00:00+00:00", "model": "m"}]
        # Same entries, different injected "now" → different counts
        now_today = datetime(2026, 5, 6, 23, 59, 59, tzinfo=timezone.utc)
        now_tomorrow = datetime(2026, 5, 7, 0, 0, 0, tzinfo=timezone.utc)
        assert tally_today(entries, "m", now_today) == 1
        assert tally_today(entries, "m", now_tomorrow) == 0
