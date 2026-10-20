from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.runner.nodes import (
    aggregate,
    execute_agent,
    load_context,
    plan,
    route_after_aggregate,
    route_after_context,
    route_after_finalize,
    route_after_agent,
    finalize,
    verify,
)


class CanonicalState(TypedDict, total=False):
    run: dict[str, Any]
    token: str
    evidence: list[dict[str, Any]]
    degraded_flags: list[str]
    target_artifact_ids: list[str]
    constraints: dict[str, Any]
    tasks: list[dict[str, Any]]
    success_criteria: list[str]
    results: list[dict[str, Any]]


workflow = StateGraph(CanonicalState)
workflow.add_node("load_context", load_context)
workflow.add_node("plan", plan)
workflow.add_node("execute", execute_agent)
workflow.add_node("finalize", finalize)
workflow.add_node("aggregate", aggregate)
workflow.add_node("verify", verify)
workflow.set_entry_point("load_context")
workflow.add_conditional_edges(
    "load_context",
    route_after_context,
    {"plan": "plan"},
)
workflow.add_edge("plan", "execute")
workflow.add_conditional_edges(
    "execute",
    route_after_agent,
    {"execute": "execute", "finalize": "finalize"},
)
workflow.add_conditional_edges(
    "finalize",
    route_after_finalize,
    {"aggregate": "aggregate"},
)
workflow.add_conditional_edges(
    "aggregate",
    route_after_aggregate,
    {"verify": "verify"},
)
workflow.add_edge("verify", END)
canonical_workflow = workflow.compile()
