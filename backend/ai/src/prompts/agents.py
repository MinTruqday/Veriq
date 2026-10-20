"""Compatibility exports for the agent planning and execution prompts."""

from src.prompts.agent_execution import AGENT_EXECUTION, agent_execution_prompt
from src.prompts.agent_planning import AGENT_PLAN, agent_plan_prompt

__all__ = [
    "AGENT_EXECUTION",
    "AGENT_PLAN",
    "agent_execution_prompt",
    "agent_plan_prompt",
]
