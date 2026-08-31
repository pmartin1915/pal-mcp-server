"""qwen-code-specific CLI agent hooks."""

from __future__ import annotations

import json

from clink.models import ResolvedCLIClient
from clink.parsers.base import ParsedCLIResponse, ParserError

from .base import AgentOutput, BaseCLIAgent


class QwenAgent(BaseCLIAgent):
    """qwen-code behaviour.

    GeminiAgent's error recovery scans combined output for the first ``{`` and
    expects one JSON *object*; qwen-code emits a JSON *array* of events, so
    that recovery can never fire (2026-08-30 Sol audit, finding 3). On a
    non-zero exit we instead re-run our own parser over stdout: a structured
    error result then surfaces as a ParserError message with subtype/stderr
    preserved, instead of collapsing into a generic exit-status error.
    """

    def __init__(self, client: ResolvedCLIClient):
        super().__init__(client)

    def _recover_from_error(
        self,
        *,
        returncode: int,
        stdout: str,
        stderr: str,
        sanitized_command: list[str],
        duration_seconds: float,
        output_file_content: str | None,
    ) -> AgentOutput | None:
        if not stdout.strip():
            return None
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, list):
            return None

        try:
            parsed = self._parser.parse(stdout, stderr)
        except ParserError as exc:
            # The stream is a well-formed qwen event array describing a
            # failure. Surface the parser's structured diagnosis as the
            # response rather than a bare exit-status error.
            parsed = ParsedCLIResponse(
                content=str(exc),
                metadata={"cli_error_recovered": True, "returncode": returncode},
            )

        return AgentOutput(
            parsed=parsed,
            sanitized_command=sanitized_command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration_seconds,
            parser_name=self._parser.name,
            output_file_content=output_file_content,
        )
