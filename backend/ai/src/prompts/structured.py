"""Compatibility exports for model output and tool selection instructions."""

from src.prompts.model_output import correction_instruction, schema_instruction
from src.prompts.tool_selection import (
    tool_selection_correction_instruction,
    tool_selection_instruction,
)

__all__ = [
    "correction_instruction",
    "schema_instruction",
    "tool_selection_correction_instruction",
    "tool_selection_instruction",
]
