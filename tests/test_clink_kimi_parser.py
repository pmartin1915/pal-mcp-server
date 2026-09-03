"""Tests for the Kimi Code CLI stream-json parser and its registry wiring."""

import json

import pytest

from clink import get_registry
from clink.parsers.kimi import KimiStreamJSONParser, ParserError

# Fixtures are verbatim shapes measured from kimi 1.12.0 on 2026-09-03.
_THINK = {"type": "think", "think": "Simple compliance.", "encrypted": None}


def _assistant(text=None, tool_calls=None, think=True):
    content = [_THINK] if think else []
    if text is not None:
        content.append({"type": "text", "text": text})
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _tool_result(text, call_id="tool_1"):
    return {
        "role": "tool",
        "content": [
            {"type": "text", "text": "<system>Command executed successfully.</system>"},
            {"type": "text", "text": text},
        ],
        "tool_call_id": call_id,
    }


_SHELL_CALL = [
    {
        "type": "function",
        "id": "tool_1",
        "function": {"name": "Shell", "arguments": json.dumps({"command": "git log --oneline -1"})},
    }
]


def _stream(*messages) -> str:
    return "\n".join(json.dumps(m) for m in messages) + "\n"


def test_single_message_success_excludes_think():
    parsed = KimiStreamJSONParser().parse(_stream(_assistant("OK")), "")
    assert parsed.content == "OK"
    assert "Simple compliance" not in parsed.content
    assert parsed.metadata["message_count"] == 1
    assert parsed.metadata["think_parts"] == 1
    assert parsed.metadata["tool_calls"] == 0


def test_tool_round_trip_returns_final_text():
    stdout = _stream(
        _assistant(tool_calls=_SHELL_CALL),
        _tool_result("75c6caa roadmaps: something\n"),
        _assistant("75c6caa"),
    )
    parsed = KimiStreamJSONParser().parse(stdout, "")
    assert parsed.content == "75c6caa"
    assert parsed.metadata["message_count"] == 3
    assert parsed.metadata["assistant_messages"] == 2
    assert parsed.metadata["tool_calls"] == 1


def test_multi_step_assistant_text_is_preserved_in_order():
    # Findings often sit on the tool-calling message; the final one just says Done.
    stdout = _stream(
        _assistant("Finding: the lock file is stale.", tool_calls=_SHELL_CALL),
        _tool_result("ok\n"),
        _assistant("Done."),
    )
    parsed = KimiStreamJSONParser().parse(stdout, "")
    assert parsed.content == "Finding: the lock file is stale.\n\nDone."


def test_empty_stdout_is_an_error_even_with_exit_zero():
    with pytest.raises(ParserError, match="empty stdout"):
        KimiStreamJSONParser().parse("", "")


def test_plain_text_stdout_without_messages_surfaces_raw_text():
    # `kimi -m bogus-model` prints this and exits 0.
    with pytest.raises(ParserError, match="LLM not set"):
        KimiStreamJSONParser().parse("LLM not set\n", "")


def test_plain_text_trailer_after_valid_message_is_a_failure():
    # Kimi exits 0 on provider failures and prints them as plain text.
    stdout = _stream(_assistant("Partial, not final")) + "LLM not set\n"
    with pytest.raises(ParserError) as excinfo:
        KimiStreamJSONParser().parse(stdout, "")
    assert "LLM not set" in str(excinfo.value)
    assert "Partial, not final" in str(excinfo.value)


def test_stream_ending_on_tool_result_is_incomplete():
    stdout = _stream(_assistant("Let me check.", tool_calls=_SHELL_CALL), _tool_result("abc\n"))
    with pytest.raises(ParserError) as excinfo:
        KimiStreamJSONParser().parse(stdout, "")
    assert "did not complete" in str(excinfo.value)
    assert "Let me check." in str(excinfo.value)


def test_stream_ending_on_pending_tool_calls_is_incomplete():
    with pytest.raises(ParserError, match="pending tool_calls: True"):
        KimiStreamJSONParser().parse(_stream(_assistant(tool_calls=_SHELL_CALL)), "")


def test_final_assistant_without_text_is_an_error():
    stdout = _stream(_assistant("earlier prose"), _assistant(None))
    with pytest.raises(ParserError) as excinfo:
        KimiStreamJSONParser().parse(stdout, "")
    assert "carried no text" in str(excinfo.value)
    assert "earlier prose" in str(excinfo.value)


def test_leading_junk_lines_are_counted_not_fatal():
    stdout = "DEBUG something\n" + _stream(_assistant("OK"))
    parsed = KimiStreamJSONParser().parse(stdout, "")
    assert parsed.content == "OK"
    assert parsed.metadata["unparsed_lines"] == 1


def test_stderr_is_preserved_in_metadata():
    parsed = KimiStreamJSONParser().parse(_stream(_assistant("OK")), "warning: cache miss\n")
    assert parsed.metadata["stderr"] == "warning: cache miss"


def test_string_content_is_tolerated():
    parsed = KimiStreamJSONParser().parse(json.dumps({"role": "assistant", "content": "plain"}) + "\n", "")
    assert parsed.content == "plain"


def test_registry_wires_kimi_client():
    registry = get_registry()
    assert "kimi" in registry.list_clients()
    client = registry.get_client("kimi")
    assert client.parser == "kimi_stream_json"
    assert client.internal_args == ["--print", "--output-format", "stream-json"]
    assert client.env["PYTHONIOENCODING"] == "utf-8"
    assert {"default", "planner", "codereviewer"} <= set(registry.list_roles("kimi"))
