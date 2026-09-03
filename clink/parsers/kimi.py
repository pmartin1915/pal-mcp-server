"""Parser for Kimi Code CLI stream-json output.

`kimi --print --output-format stream-json` emits one JSON object per line,
each a chat message: `{"role": "assistant"|"tool", "content": [parts...],
"tool_calls"?: [...], "tool_call_id"?: ...}`. Parts are typed: `think`
(reasoning, never part of the answer), `text`, and tool payloads. There is NO
terminal result/usage event in this format (measured 2026-09-03, kimi 1.12.0;
the `text` format prints `StatusUpdate`/`TurnEnd`, stream-json does not).

Completion contract (same posture as the qwen parser Sol audited 2026-08-30):
success REQUIRES that the PHYSICAL last non-blank stdout line be an assistant
message carrying at least one `text` part and no `tool_calls`; non-JSON lines
earlier in the stream are tolerated and counted, a non-JSON trailer is a
failure. The response is the ordered join of all assistant text parts. A stream ending on a tool result, or on
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
        last_line_is_message = False
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                unparsed.append(line)
                last_line_is_message = False
                continue
            if isinstance(obj, dict):
                messages.append(obj)
                last_line_is_message = True
            else:
                unparsed.append(line)
                last_line_is_message = False

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

        assistant_text = "\n\n".join(t for m in assistant_messages if (t := self._text_of(m))).strip()
        partial_note = f" Partial assistant output: {assistant_text[:_PARTIAL_TEXT_LIMIT]}" if assistant_text else ""

        if not last_line_is_message:
            # The PHYSICAL last line must be the accepted message. Kimi exits 0
            # on provider failures and prints them as plain text, so a valid
            # message followed by an "LLM not set"-style trailer is a failed
            # run (Sol review 2026-09-03, High).
            raise ParserError(
                "kimi CLI stream ended on non-JSON text, not a final assistant message: "
                + unparsed[-1][:_PARTIAL_TEXT_LIMIT]
                + partial_note
            )

        last = messages[-1]
        if last.get("role") != "assistant" or last.get("tool_calls"):
            raise ParserError(
                "kimi CLI stream ended before a final assistant text message "
                f"(last role: {last.get('role')!r}, pending tool_calls: {bool(last.get('tool_calls'))}); "
                "the run did not complete." + partial_note
            )

        if not self._text_of(last):
            raise ParserError("kimi CLI final assistant message carried no text." + partial_note)

        # Return every assistant text part in order, as the codex parser does:
        # in a multi-tool run the findings often sit on a tool-calling message
        # and the final message just says "Done." (Sol review 2026-09-03, Medium).
        content = assistant_text

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
