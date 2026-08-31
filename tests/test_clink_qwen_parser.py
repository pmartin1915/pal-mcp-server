"""Tests for the qwen-code CLI JSON parser and its registry wiring."""

import json

import pytest

from clink import get_registry
from clink.parsers.qwen import ParserError, QwenJSONParser


def _event_stream(
    result_text="ok",
    is_error=False,
    include_result=True,
    assistant_text=None,
    models=None,
) -> str:
    events = [
        {"type": "system", "subtype": "init", "session_id": "abc", "model": "qwen3-coder:30b-48k"},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "qwen3-coder:30b-48k",
                "content": [{"type": "text", "text": assistant_text if assistant_text is not None else result_text}],
            },
        },
    ]
    if include_result:
        if models is None:
            models = {
                "qwen3-coder:30b-48k": {
                    "api": {"totalRequests": 1, "totalErrors": 0, "totalLatencyMs": 1234},
                    "tokens": {"prompt": 100, "candidates": 2, "total": 102},
                }
            }
        events.append(
            {
                "type": "result",
                "subtype": "success" if not is_error else "error_during_execution",
                "is_error": is_error,
                "result": result_text,
                "usage": {"input_tokens": 100, "output_tokens": 2, "total_tokens": 102},
                "stats": {"models": models},
            }
        )
    return json.dumps(events)


def test_qwen_parser_extracts_result_and_stats():
    parsed = QwenJSONParser().parse(_event_stream(), stderr="")

    assert parsed.content == "ok"
    assert parsed.metadata["model_used"] == "qwen3-coder:30b-48k"
    assert parsed.metadata["token_usage"]["total"] == 102
    assert parsed.metadata["latency_ms"] == 1234
    assert parsed.metadata["subtype"] == "success"


def test_qwen_parser_uses_assistant_text_when_result_text_empty():
    parsed = QwenJSONParser().parse(
        _event_stream(result_text="", assistant_text="the real answer"), stderr=""
    )

    assert parsed.content == "the real answer"
    assert parsed.metadata["content_source"] == "assistant_events"


def test_qwen_parser_rejects_stream_without_result_event():
    # A run that died before its terminal result event is not a success, even
    # with assistant text present (Sol audit finding 2).
    with pytest.raises(ParserError) as exc:
        QwenJSONParser().parse(_event_stream(result_text="partial answer", include_result=False), stderr="")
    assert "no terminal result event" in str(exc.value)
    assert "partial answer" in str(exc.value)


def test_qwen_parser_rejects_error_result_with_text():
    # is_error wins over any text: a failed run must not masquerade as an
    # answer (Sol audit finding 1).
    with pytest.raises(ParserError) as exc:
        QwenJSONParser().parse(_event_stream(result_text="looks plausible", is_error=True), stderr="")
    assert "error_during_execution" in str(exc.value)
    assert "looks plausible" in str(exc.value)


def test_qwen_parser_rejects_error_result_with_assistant_text_only():
    with pytest.raises(ParserError) as exc:
        QwenJSONParser().parse(
            _event_stream(result_text="", is_error=True, assistant_text="partial work"), stderr="boom"
        )
    message = str(exc.value)
    assert "partial work" in message
    assert "boom" in message


def test_qwen_parser_rejects_error_result_with_no_text():
    with pytest.raises(ParserError) as exc:
        QwenJSONParser().parse(_event_stream(result_text="", is_error=True, assistant_text=""), stderr="")
    assert "error_during_execution" in str(exc.value)


def test_qwen_parser_tolerates_malformed_model_stats():
    # A truthy non-dict model entry must not raise AttributeError (Sol audit
    # finding 4).
    parsed = QwenJSONParser().parse(_event_stream(models={"weird": "unavailable"}), stderr="")

    assert parsed.content == "ok"
    assert parsed.metadata["model_used"] == "weird"
    assert "token_usage" not in parsed.metadata


def test_qwen_parser_rejects_non_array_payload():
    with pytest.raises(ParserError):
        QwenJSONParser().parse('{"response": "ok"}', stderr="")


def test_qwen_parser_rejects_empty_stdout():
    with pytest.raises(ParserError):
        QwenJSONParser().parse("", stderr="")


def test_registry_resolves_qwen_client_with_qwen_runner():
    registry = get_registry()
    clients = registry.list_clients()
    assert "qwen" in clients

    client = registry.get_client("qwen")
    assert client.parser == "qwen_json"
    assert client.runner == "qwen"
    assert "-o" in client.internal_args and "json" in client.internal_args
    assert "default" in registry.list_roles("qwen")
    assert "codereviewer" in registry.list_roles("qwen")


def test_qwen_agent_recovers_structured_error_on_nonzero_exit():
    # Agent-level: a non-zero exit whose stdout is a well-formed qwen event
    # array describing a failure surfaces the structured diagnosis (Sol audit
    # finding 3), not a generic exit-status error.
    from clink.agents import create_agent
    from clink.agents.qwen import QwenAgent

    registry = get_registry()
    client = registry.get_client("qwen")
    agent = create_agent(client)
    assert isinstance(agent, QwenAgent)

    stdout = _event_stream(result_text="ran out of quota", is_error=True)
    recovered = agent._recover_from_error(
        returncode=1,
        stdout=stdout,
        stderr="exit 1",
        sanitized_command=["qwen", "-o", "json"],
        duration_seconds=1.0,
        output_file_content=None,
    )

    assert recovered is not None
    assert recovered.parsed.metadata.get("cli_error_recovered") is True
    assert "ran out of quota" in recovered.parsed.content
    assert recovered.returncode == 1


def test_qwen_agent_recovery_ignores_non_array_stdout():
    from clink.agents import create_agent

    registry = get_registry()
    agent = create_agent(registry.get_client("qwen"))
    assert (
        agent._recover_from_error(
            returncode=1,
            stdout='{"error": {"code": 429}}',
            stderr="",
            sanitized_command=["qwen"],
            duration_seconds=0.1,
            output_file_content=None,
        )
        is None
    )
