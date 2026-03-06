"""
Handoff tool - Generate comprehensive session handoff summaries

This tool creates structured summaries of development sessions for seamless handoffs
between developers or AI agents. It captures completed tasks, in-progress work,
modified files, next steps, and blockers.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from systemprompts import HANDOFF_PROMPT
from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest

from .simple.base import SimpleTool

logger = logging.getLogger(__name__)

# Field descriptions
HANDOFF_FIELD_DESCRIPTIONS = {
    "prompt": (
        "The session context for generating a handoff summary. Include: "
        "what tasks were completed, what is still in progress, files that were modified, "
        "any blockers encountered, and suggested next steps. The more context provided, "
        "the better the summary."
    ),
    "session_notes": (
        "Optional additional notes about the session that should be included in the summary. "
        "Can include observations, decisions made, or context that may not be obvious from the task list."
    ),
    "output_format": (
        "Format for the summary output. Options: 'markdown' (default), 'json', 'plain'. "
        "Markdown provides a readable format; JSON is structured for programmatic use."
    ),
}


class HandoffRequest(ToolRequest):
    """Request model for Handoff tool"""

    prompt: str = Field(..., description=HANDOFF_FIELD_DESCRIPTIONS["prompt"])
    session_notes: Optional[str] = Field(
        default=None,
        description=HANDOFF_FIELD_DESCRIPTIONS["session_notes"],
    )
    output_format: Optional[str] = Field(
        default="markdown",
        description=HANDOFF_FIELD_DESCRIPTIONS["output_format"],
    )


class HandoffTool(SimpleTool):
    """
    Handoff tool for generating comprehensive session handoff summaries.

    This tool analyzes provided session context and generates a structured
    summary document that enables seamless handoffs between developers or
    AI agents. It extracts and organizes:
    - Completed tasks
    - In-progress items
    - Modified files
    - Next steps
    - Blockers and issues
    - Important context and notes
    """

    def get_name(self) -> str:
        return "handoff"

    def get_description(self) -> str:
        return (
            "Generate comprehensive session handoff summaries for seamless transitions. "
            "Captures completed tasks, in-progress items, modified files, next steps, "
            "blockers, and important context. Use when ending a session or handing off work."
        )

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Handoff is a read-only analysis tool."""
        return {"readOnlyHint": True}

    def get_system_prompt(self) -> str:
        return HANDOFF_PROMPT

    def get_default_temperature(self) -> float:
        # Use analytical temperature for structured output
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Handoff benefits from fast, efficient models for summary generation"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.FAST_RESPONSE

    def get_request_model(self):
        """Return the Handoff-specific request model"""
        return HandoffRequest

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema for the handoff tool."""
        required_fields = ["prompt"]
        if self.is_effective_auto_mode():
            required_fields.append("model")

        schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": HANDOFF_FIELD_DESCRIPTIONS["prompt"],
                },
                "session_notes": {
                    "type": "string",
                    "description": HANDOFF_FIELD_DESCRIPTIONS["session_notes"],
                },
                "output_format": {
                    "type": "string",
                    "enum": ["markdown", "json", "plain"],
                    "default": "markdown",
                    "description": HANDOFF_FIELD_DESCRIPTIONS["output_format"],
                },
                "model": self.get_model_field_schema(),
                "temperature": {
                    "type": "number",
                    "description": COMMON_FIELD_DESCRIPTIONS["temperature"],
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": COMMON_FIELD_DESCRIPTIONS["thinking_mode"],
                },
                "continuation_id": {
                    "type": "string",
                    "description": COMMON_FIELD_DESCRIPTIONS["continuation_id"],
                },
            },
            "required": required_fields,
            "additionalProperties": False,
        }

        return schema

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Tool-specific field definitions used by SimpleTool scaffolding."""
        return {
            "prompt": {
                "type": "string",
                "description": HANDOFF_FIELD_DESCRIPTIONS["prompt"],
            },
            "session_notes": {
                "type": "string",
                "description": HANDOFF_FIELD_DESCRIPTIONS["session_notes"],
            },
            "output_format": {
                "type": "string",
                "enum": ["markdown", "json", "plain"],
                "default": "markdown",
                "description": HANDOFF_FIELD_DESCRIPTIONS["output_format"],
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for Handoff tool"""
        return ["prompt"]

    async def prepare_prompt(self, request: HandoffRequest) -> str:
        """
        Prepare the handoff prompt with session context and optional notes.
        """
        # Build the main prompt with session context
        prompt_parts = [
            "=== SESSION CONTEXT FOR HANDOFF ===",
            request.prompt,
        ]

        # Add session notes if provided
        if request.session_notes:
            prompt_parts.extend(
                [
                    "",
                    "=== ADDITIONAL SESSION NOTES ===",
                    request.session_notes,
                ]
            )

        # Add output format instruction
        output_format = request.output_format or "markdown"
        format_instructions = {
            "markdown": "Generate the handoff summary in well-formatted Markdown.",
            "json": (
                "Generate the handoff summary as a valid JSON object with keys: "
                "'session_summary', 'completed_tasks', 'in_progress_items', "
                "'modified_files', 'next_steps', 'blockers', 'context_notes'"
            ),
            "plain": "Generate the handoff summary in plain text format.",
        }

        prompt_parts.extend(
            [
                "",
                "=== OUTPUT FORMAT ===",
                format_instructions.get(output_format, format_instructions["markdown"]),
                "",
                "=== END SESSION CONTEXT ===",
                "",
                "Please generate a comprehensive handoff summary based on the context above:",
            ]
        )

        return "\n".join(prompt_parts)

    def format_response(
        self, response: str, request: HandoffRequest, model_info: Optional[dict] = None
    ) -> str:
        """
        Format the handoff response, optionally adding metadata.
        """
        output_format = request.output_format or "markdown"

        if output_format == "json":
            # For JSON, return as-is (should already be valid JSON)
            return response

        # For markdown/plain, add a clear header and timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        if output_format == "markdown":
            header = "# Session Handoff Summary\n\n"
            footer = f"\n\n---\n_Generated: {timestamp}_"
        else:
            header = "SESSION HANDOFF SUMMARY\n" + "=" * 25 + "\n\n"
            footer = f"\n\n---\nGenerated: {timestamp}"

        return f"{header}{response}{footer}"

    def get_websearch_guidance(self) -> Optional[str]:
        """
        Handoff summaries don't typically need web searches.
        """
        return None
