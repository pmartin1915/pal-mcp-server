"""Parser for Kimi Code CLI stream-json output.

`kimi --print --output-format stream-json` emits one JSON object per line,
each a chat message: `{"role": "assistant"|"tool", "content": [parts...],
"tool_calls"?: [...], "tool_call_id"?: ...}`. Parts are typed: `think`
(reasoning, never part of the answer), `text`, and tool payloads. There is NO
terminal result/usage event in this format (measured 2026-09-03, kimi 1.12.0;
the `text` format prints `StatusUpdate`/`TurnEnd`, stream-json does not).

Completion contract (same posture as the qwen parser Sol audited 2026-08-30):
success REQUIRES that the LAST line be an assistant message carrying at least
one `text` part and no `tool_calls`. A stream ending on a tool result, or on
an assistant message still requesting tools, died mid-flight and raises with
partial text preserved diagnostically. Empty stdout is a hard error because
the CLI's cp1252 encoding crash exits 0 with empty output, so the exit code
alone cannot catch it. Non-JSON stdout with no messages at all (e.g. the plain
`LLM not set` line an unknown model produces, also exit 0) raises with the raw
text in the message.
"""

from __future__ import annotations

import json
from typing import Any

from .base import BaseParser, ParsedCLIResponse, ParserError

_PARTIAL_TEXT_LIMIT = 2000


class KimiStreamJSONParser(BaseParser):
    """Parse stdout produced by `kimi --print --output-format stream-json`."""

    name = "kimi_stream_json"

    def parse(self, stdout: str, stderr: str) -> ParsedCLIResponse:
        if not stdout.strip():
            raise ParserError(
                "kimi CLI returned empty stdout while stream-json output was expected "
                "(the CLI's cp1252 crash exits 0 with no output: keep prompts ASCII-only "
                "and PYTHONIOENCODING=utf-8)"
            )

        messages: list[dict[str, Any]] = []
        unparsed: list[str] = []
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                unparsed.append(line)
                continue
            if isinstance(obj, dict):
                messages.append(obj)
            else:
                unparsed.append(line)

        if not messages:
            raise ParserError(
                "kimi CLI produced no stream-json messages. Raw output: "
                + stdout.strip()[:_PARTIAL_TEXT_LIMIT]
            )

        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        metadata: dict[str, Any] = {
            "message_count": len(messages),
            "assistant_messages": len(assistant_messages),
            "tool_calls": sum(len(m.get("tool_calls") or []) for m in assistant_messages),
            "think_parts": sum(
                1 for m in assistant_messages for p in self._parts(m) if p.get("type") == "think"
            ),
        }
        if unparsed:
            metadata["unparsed_lines"] = len(unparsed)

        partial = "\n".join(t for m in assistant_messages if (t := self._text_of(m))).strip()
        partial_note = f" Partial assistant output: {partial[:_PARTIAL_TEXT_LIMIT]}" if partial else ""

        last = messages[-1]
        if last.get("role") != "assistant" or last.get("tool_calls"):
            raise ParserError(
                "kimi CLI stream ended before a final assistant text message "
                f"(last role: {last.get('role')!r}, pending tool_calls: {bool(last.get('tool_calls'))}); "
                "the run did not complete." + partial_note
            )

        content = self._text_of(last)
        if not content:
            raise ParserError(
                "kimi CLI final assistant message carried no text." + partial_note
            )

        if stderr and stderr.strip():
            metadata["stderr"] = stderr.strip()[:_PARTIAL_TEXT_LIMIT]
        return ParsedCLIResponse(content=content, metadata=metadata)

    @staticmethod
    def _parts(message: dict[str, Any]) -> list[dict[str, Any]]:
        content = message.get("content")
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        if not isinstance(content, list):
            return []
        return [p for p in content if isinstance(p, dict)]

    @classmethod
    def _text_of(cls, message: dict[str, Any]) -> str:
        texts = [
            p["text"] for p in cls._parts(message) if p.get("type") == "text" and isinstance(p.get("text"), str)
        ]
        return "\n".join(texts).strip()
