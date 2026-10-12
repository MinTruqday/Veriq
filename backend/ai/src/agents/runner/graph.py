from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.supervisor.nodes import (
    aggregate,
    apply,
    execute_agent,
    load_context,
    plan,
    route_after_aggregate,
    route_after_context,
    route_after_review,
    route_after_agent,
    re_evaluate,
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
    task_index: int
    results: list[dict[str, Any]]
    review_complete: bool


workflow = StateGraph(CanonicalState)
workflow.add_node("load_context", load_context)
workflow.add_node("plan", plan)
workflow.add_node("execute", execute_agent)
workflow.add_node("re_evaluate", re_evaluate)
workflow.add_node("aggregate", aggregate)
workflow.add_node("apply", apply)
workflow.add_node("verify", verify)
workflow.set_entry_point("load_context")
workflow.add_conditional_edges(
    "load_context",
    route_after_context,
    {
        "plan": "plan",
        "apply": "apply",
        "verify": "verify",
        "re_evaluate": "re_evaluate",
    },
)
workflow.add_edge("plan", "execute")
workflow.add_conditional_edges(
    "execute",
    route_after_agent,
    {"execute": "execute", "review": "re_evaluate"},
)
workflow.add_conditional_edges(
    "re_evaluate",
    route_after_review,
    {"execute": "execute", "aggregate": "aggregate"},
)
workflow.add_conditional_edges(
    "aggregate",
    route_after_aggregate,
    {"end": END, "verify": "verify"},
)
workflow.add_edge("apply", "verify")
workflow.add_edge("verify", END)
canonical_workflow = workflow.compile()
