"""Coverage for the GEMINI_API_KEY_BILLED fallback path.

Audit (2026-05-09) flagged that the previous trigger fired on per-minute
throttles, wasting the daily Layer A allowance. These tests pin the
fixed behaviour: daily quota promotes, per-minute throttles do not.
"""

from unittest.mock import MagicMock

import pytest

from providers.gemini import GeminiModelProvider


@pytest.fixture
def provider(monkeypatch):
    """Build a Gemini provider with both clients mocked and budget gate off."""
    monkeypatch.setenv("PAL_BUDGET_ENABLED", "false")
    p = GeminiModelProvider(api_key="primary-key")
    # Force both clients into pre-initialised state so the lazy properties
    # short-circuit and do not try to reach the network.
    p._client = MagicMock(name="primary_client")
    p._billed_api_key = "billed-key"
    p._billed_client = MagicMock(name="billed_client")
    return p


def _make_response(text: str = "ok"):
    """Build a minimal stub that _build_model_response can consume."""
    candidate = MagicMock()
    candidate.finish_reason = MagicMock(name="STOP")
    candidate.finish_reason.name = "STOP"
    part = MagicMock()
    part.text = text
    part.thought = None
    candidate.content.parts = [part]
    candidate.safety_ratings = []

    response = MagicMock()
    response.candidates = [candidate]
    response.usage_metadata.prompt_token_count = 1
    response.usage_metadata.candidates_token_count = 1
    response.usage_metadata.total_token_count = 2
    response.usage_metadata.thoughts_token_count = 0
    return response


def test_daily_quota_error_promotes_to_billed_key(provider):
    """A daily quota exhaustion should fall back to the billed client."""
    provider._client.models.generate_content.side_effect = Exception(
        "429 RESOURCE_EXHAUSTED. Quota exceeded for quota metric "
        "'GenerateRequestsPerDayPerProjectPerModel'"
    )
    provider._billed_client.models.generate_content.return_value = _make_response("billed-ok")

    result = provider.generate_content(prompt="hello", model_name="gemini-2.5-flash")

    assert provider._billed_client.models.generate_content.called, (
        "billed_client should have been invoked after primary quota exhaustion"
    )
    assert result is not None
    assert result.model_name == "gemini-2.5-flash"


def test_per_minute_throttle_does_not_promote_to_billed_key(provider):
    """Per-minute rate limits must NOT consume the billed allowance."""
    provider._client.models.generate_content.side_effect = Exception(
        "429 RESOURCE_EXHAUSTED. Quota exceeded for quota metric "
        "'GenerateRequestsPerMinutePerProjectPerModel'"
    )

    with pytest.raises(RuntimeError) as excinfo:
        provider.generate_content(prompt="hello", model_name="gemini-2.5-flash")

    assert not provider._billed_client.models.generate_content.called, (
        "billed_client must NOT be called for per-minute throttles"
    )
    assert "per-minute" in str(excinfo.value).lower(), (
        "error message should clearly identify per-minute throttle"
    )


def test_tokens_per_min_throttle_does_not_promote(provider):
    """Token-rate per-minute throttles also stay on the primary key."""
    provider._client.models.generate_content.side_effect = Exception(
        "429 Too many tokens per min for the project"
    )

    with pytest.raises(RuntimeError):
        provider.generate_content(prompt="hello", model_name="gemini-2.5-flash")

    assert not provider._billed_client.models.generate_content.called


def test_no_billed_key_no_fallback(monkeypatch):
    """If GEMINI_API_KEY_BILLED is unset, daily quota errors raise — no promotion."""
    monkeypatch.setenv("PAL_BUDGET_ENABLED", "false")
    p = GeminiModelProvider(api_key="primary-key")
    p._client = MagicMock(name="primary_client")
    p._billed_api_key = None  # explicit
    p._billed_client = None
    p._client.models.generate_content.side_effect = Exception(
        "429 RESOURCE_EXHAUSTED. Quota exceeded ... PerDay ..."
    )

    with pytest.raises(RuntimeError) as excinfo:
        p.generate_content(prompt="hello", model_name="gemini-2.5-flash")

    assert "daily quota" in str(excinfo.value).lower()
