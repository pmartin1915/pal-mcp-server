"""Parser for qwen-code CLI JSON output.

qwen-code (QwenLM's fork of gemini-cli) diverged from the ancestor's output
contract: `qwen -o json` emits a single JSON *array* of typed events
(`system`, `assistant`, `result`, ...) rather than an object with a top-level
`response` string. The terminal `result` event carries the final text in its
`result` field and per-model stats under `stats.models` (that inner shape is
still gemini-like: `api.totalLatencyMs`, `tokens.{prompt,candidates,total}`).

Contract enforced here (per the 2026-08-30 Sol audit of this integration):
success REQUIRES a terminal `result` event with `is_error` falsy and text.
An error result, or a stream that ended before its result event, raises
ParserError — partial text is preserved in the error message diagnostically,
never returned as a successful response.
"""

from __future__ import annotations

import json
from typing import Any

from .base import BaseParser, ParsedCLIResponse, ParserError

_PARTIAL_TEXT_LIMIT = 2000


class QwenJSONParser(BaseParser):
    """Parse stdout produced by `qwen -o json`."""

    name = "qwen_json"

    def parse(self, stdout: str, stderr: str) -> ParsedCLIResponse:
        if not stdout.strip():
            raise ParserError("qwen CLI returned empty stdout while JSON output was expected")

        try:
            payload: Any = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ParserError(f"Failed to decode qwen CLI JSON output: {exc}") from exc

        if not isinstance(payload, list):
            raise ParserError(
                "qwen CLI JSON output was not the expected event array; "
                f"got {type(payload).__name__}"
            )

        events = [event for event in payload if isinstance(event, dict)]
        result_event = next(
            (event for event in reversed(events) if event.get("type") == "result"),
            None,
        )

        metadata: dict[str, Any] = {"event_types": [event.get("type") for event in events]}
        assistant_text = self._assistant_text(events)

        if result_event is None:
            # The stream ended before its terminal result event: the run died
            # mid-flight. Assistant fragments are diagnostics, not an answer.
            detail = f" Partial assistant output: {assistant_text[:_PARTIAL_TEXT_LIMIT]}" if assistant_text else ""
            raise ParserError(
                "qwen CLI output has no terminal result event; the run did not complete." + detail
            )

        metadata["subtype"] = result_event.get("subtype")
        usage = result_event.get("usage")
        if isinstance(usage, dict):
            metadata["usage"] = usage
        stats = result_event.get("stats")
        if isinstance(stats, dict):
            models = stats.get("models")
            if isinstance(models, dict) and models:
                model_name = next(iter(models.keys()))
                metadata["model_used"] = model_name
                model_stats = models.get(model_name)
                if isinstance(model_stats, dict):
                    tokens = model_stats.get("tokens")
                    if isinstance(tokens, dict):
                        metadata["token_usage"] = tokens
                    api_stats = model_stats.get("api")
                    if isinstance(api_stats, dict):
                        metadata["latency_ms"] = api_stats.get("totalLatencyMs")

        result_text = result_event.get("result")
        content = result_text.strip() if isinstance(result_text, str) else ""

        if result_event.get("is_error"):
            # An error is an error even when text came with it: never let a
            # failed run masquerade as a successful response.
            detail = result_event.get("subtype") or "unknown error"
            parts = [f"qwen CLI reported an error (subtype: {detail})."]
            if content:
                parts.append(f"Error text: {content[:_PARTIAL_TEXT_LIMIT]}")
            elif assistant_text:
                parts.append(f"Partial assistant output: {assistant_text[:_PARTIAL_TEXT_LIMIT]}")
            if stderr and stderr.strip():
                parts.append(f"stderr: {stderr.strip()[:_PARTIAL_TEXT_LIMIT]}")
            raise ParserError(" ".join(parts))

        if not content and assistant_text:
            # Result event present and successful but with empty text; some
            # builds put the prose only in assistant events.
            metadata["content_source"] = "assistant_events"
            content = assistant_text

        if content:
            if stderr and stderr.strip():
                metadata["stderr"] = stderr.strip()
            return ParsedCLIResponse(content=content, metadata=metadata)

        raise ParserError("qwen CLI returned a successful result event with no text")

    @staticmethod
    def _assistant_text(events: list[dict[str, Any]]) -> str:
        texts: list[str] = []
        for event in events:
            if event.get("type") != "assistant":
                continue
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            for block in message.get("content") or []:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    texts.append(block["text"])
        return "\n".join(texts).strip()
