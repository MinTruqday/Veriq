from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.runner.nodes import (
    aggregate,
    execute_agent,
    finalize,
    load_context,
    plan,
    route_after_agent,
    route_after_aggregate,
    verify,
)
from src.core.infrastructure.configuration import settings
from src.core.security.guardrails import guardrails_engine
from src.prompts.automation import automation_fact_extraction_prompt
from src.schemas.agent import AgentResult, AgentTaskStatus
from src.schemas.automation import (
    AutomationFactExtraction,
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationGraphSnapshot,
    AutomationStatus,
)
from src.services.inference import structured
from src.repositories.automation import automation_repository


class AutomationGraphState(TypedDict, total=False):
    automatic: bool
    run: dict[str, Any]
    token: str
    evidence: list[dict[str, Any]]
    degraded_flags: list[str]
    target_artifact_ids: list[str]
    constraints: dict[str, Any]
    tasks: list[dict[str, Any]]
    success_criteria: list[str]
    results: list[dict[str, Any]]
    source_facts: list[dict[str, Any]]
    uncertainties: list[dict[str, Any]]
    automation_phases: list[str]
    source_event_verified: bool
    planning_round: int
    resume_after_phase: str


def phase(state: AutomationGraphState, name: str) -> list[str]:
    return [*state.get("automation_phases", []), name]


async def resume_dispatch(state: AutomationGraphState):
    return {}


def route_resume(state: AutomationGraphState):
    completed = state.get("resume_after_phase")
    if completed == AutomationCheckpointPhase.OBSERVED.value:
        return "extract_source_facts"
    if completed == AutomationCheckpointPhase.FACTS_EXTRACTED.value:
        return "assess_uncertainty"
    if completed == AutomationCheckpointPhase.UNCERTAINTY_ASSESSED.value:
        return "create_action_plan"
    if completed == AutomationCheckpointPhase.PLAN_CREATED.value:
        return "execute_action" if state.get("tasks") else "finalize_automation"
    if completed == AutomationCheckpointPhase.ACTION_STARTED.value:
        return "execute_action"
    if completed == AutomationCheckpointPhase.ACTIONS_EXECUTED.value:
        return "execute_action"
    if completed == AutomationCheckpointPhase.FINALIZED.value:
        return "aggregate"
    if completed in {
        AutomationCheckpointPhase.ACTIONS_VERIFIED.value,
        AutomationCheckpointPhase.GRAPH_COMPLETED.value,
    }:
        return "end"
    return "observe_sources"


async def record_phase(state: AutomationGraphState, name: str, detail=None, status=None):
    snapshot_state = state.get("checkpoint_state") or state
    run = snapshot_state.get("run") or {}
    if not run.get("run_id"):
        return
    snapshot = AutomationGraphSnapshot.model_validate(
        {
            key: value
            for key, value in snapshot_state.items()
            if key in AutomationGraphSnapshot.model_fields and key != "completed_phase"
        }
        | {"completed_phase": name}
    )
    await automation_repository.save_checkpoint(
        AutomationCheckpoint(
            automation_run_id=run["run_id"],
            phase=AutomationCheckpointPhase(name),
            status=status or AutomationStatus.RUNNING,
            detail=detail or {},
            state_snapshot=snapshot,
        )
    )


async def observe_sources(state: AutomationGraphState):
    values = await load_context(state)
    checkpoint_state = {**state, **values}
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AutomationCheckpointPhase.OBSERVED.value,
        {
            "evidence_count": len(values.get("evidence", [])),
            "degraded_flags": values.get("degraded_flags", []),
        },
    )
    return {
        **values,
        "automation_phases": phase(state, "OBSERVED"),
    }


def bind_extracted_facts(extraction, evidence):
    facts = []
    for fact in extraction.facts:
        source = next(
            (
                item for item in evidence
                if str(item.get("artifact_id")) == fact.artifact_id
                and str(item.get("artifact_version_id") or "")
                == str(fact.artifact_version_id or "")
            ),
            None,
        )
        quote = fact.quote.strip()
        source_text = str(source.get("text") or "") if source else ""
        if not source or not quote or quote not in source_text:
            continue
        source_start = source_text.index(quote)
        facts.append(
            {
                "artifact_type": str(source.get("artifact_type") or fact.artifact_type),
                "artifact_id": str(source["artifact_id"]),
                "artifact_version_id": source.get("artifact_version_id"),
                "source": str(source.get("source") or fact.source),
                "authority": str(source.get("authority") or fact.authority),
                "quote": quote,
                "fact_kind": fact.fact_kind,
                "source_start": source_start,
                "source_end": source_start + len(quote),
            }
        )
    return facts


async def extract_source_facts(state: AutomationGraphState):
    evidence = [
        item for item in state.get("evidence", [])
        if str(item.get("text") or "").strip() and item.get("artifact_id")
    ]
    facts = []
    uncertainties = []
    if evidence:
        try:
            inspected = await guardrails_engine.async_inspect_input(
                "\n".join(str(item.get("text") or "") for item in evidence)
            )
            if not inspected.get("is_safe", False):
                raise ValueError("AUTOMATION_SOURCE_REJECTED_BY_GUARDRAILS")
            extraction = await structured(
                automation_fact_extraction_prompt(evidence),
                AutomationFactExtraction,
                max_tokens=1200,
                timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
            )
            facts = bind_extracted_facts(extraction, evidence)
            uncertainties = [
                {**item.model_dump(mode="python"), "blocking": False}
                for item in extraction.uncertainties
                if set(item.evidence_refs).issubset(
                    {
                        str(value.get("artifact_version_id") or value.get("artifact_id"))
                        for value in evidence
                    }
                )
            ]
            if not facts:
                uncertainties.append(
                    {
                        "code": "NO_VERIFIABLE_SOURCE_FACTS",
                        "question": "Có thể cung cấp hoặc xác nhận đoạn nguồn làm căn cứ cho yêu cầu này không?",
                        "reason": "Mô hình không trả về trích dẫn khớp nguyên văn với tài liệu được phép đọc",
                        "evidence_refs": [],
                        "blocking": True,
                    }
                )
        except Exception as error:
            rejected = str(error) == "AUTOMATION_SOURCE_REJECTED_BY_GUARDRAILS"
            uncertainties.append(
                {
                    "code": "SOURCE_INJECTION_REJECTED" if rejected else "FACT_EXTRACTION_UNAVAILABLE",
                    "question": (
                        "Có thể rà soát tài liệu nguồn và gửi lại sau khi loại bỏ chỉ dẫn không liên quan không?"
                        if rejected
                        else "Có thể tiếp tục sau khi dịch vụ phân tích nguồn hoạt động lại không?"
                    ),
                    "reason": (
                        "Nguồn bị chặn bởi cơ chế kiểm tra an toàn"
                        if rejected
                        else "Không thể trích xuất và kiểm chứng facts trong lượt chạy này"
                    ),
                    "evidence_refs": [],
                    "blocking": True,
                }
            )
    else:
        uncertainties.append(
            {
                "code": "NO_PERMITTED_SOURCE_EVIDENCE",
                "question": "Có tài liệu hoặc Requirement được phép AI đọc để làm căn cứ không?",
                "reason": "Không có nguồn dự án được phép đọc trong sự kiện này",
                "evidence_refs": [],
                "blocking": True,
            }
        )
    checkpoint_state = {
        **state,
        "source_facts": facts,
        "uncertainties": uncertainties,
        "automation_phases": phase(state, "FACTS_EXTRACTED"),
    }
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AutomationCheckpointPhase.FACTS_EXTRACTED.value,
        {"source_fact_count": len(facts)},
    )
    return {
        "source_facts": facts,
        "uncertainties": uncertainties,
        "automation_phases": phase(state, "FACTS_EXTRACTED"),
    }


async def assess_uncertainty(state: AutomationGraphState):
    uncertainties = list(state.get("uncertainties", []))
    if not state.get("source_facts") and not any(
        item.get("blocking") for item in uncertainties
    ):
        uncertainties.append(
            {
                "code": "CLARIFICATION_REQUIRED",
                "question": "Nguồn nào trong dự án cần được xác nhận trước khi tiếp tục?",
                "reason": "Không có facts nào được trích dẫn và kiểm chứng từ nguồn được phép đọc",
                "evidence_refs": [],
                "blocking": True,
            }
        )
    for flag in state.get("degraded_flags", []):
        uncertainties.append(
            {
                "code": str(flag),
                "question": "Có thể bổ sung hoặc xác nhận nguồn còn thiếu để hoàn tất đối chiếu không?",
                "reason": "Evidence retrieval was partial; available authoritative sources remain usable",
                "evidence_refs": [],
                "blocking": False,
            }
        )
    checkpoint_state = {**state, "uncertainties": uncertainties, "automation_phases": phase(state, "UNCERTAINTY_ASSESSED")}
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AutomationCheckpointPhase.UNCERTAINTY_ASSESSED.value,
        {
            "uncertainty_count": len(uncertainties),
            "blocking_count": sum(bool(item.get("blocking")) for item in uncertainties),
        },
    )
    return {
        "uncertainties": uncertainties,
        "automation_phases": phase(state, "UNCERTAINTY_ASSESSED"),
    }


async def create_action_plan(state: AutomationGraphState):
    blocking_uncertainties = [
        item for item in state.get("uncertainties", []) if item.get("blocking")
    ]
    if blocking_uncertainties:
        run = dict(state["run"])
        result = AgentResult(
            task_id=f"AUTOMATION-PLAN-{run['run_id']}",
            status=AgentTaskStatus.INSUFFICIENT_EVIDENCE,
            summary="Automation cannot continue until the missing or degraded source evidence is resolved",
            evidence_refs=run.get("evidence_refs", []),
            reason_codes=[item["code"] for item in blocking_uncertainties],
            warnings=["SOURCE_EVIDENCE_REQUIRED"],
        )
        checkpoint_state = {
            **state,
            "tasks": [],
            "planning_round": 1,
            "success_criteria": [],
            "results": [result.model_dump(mode="python")],
            "automation_phases": phase(state, "PLAN_CREATED"),
        }
        await record_phase(
            {**state, "checkpoint_state": checkpoint_state},
            AutomationCheckpointPhase.PLAN_CREATED.value,
            {"task_count": 0, "blocked": True},
        )
        return {
            "tasks": [],
            "planning_round": 1,
            "success_criteria": [],
            "results": [result.model_dump(mode="python")],
            "automation_phases": phase(state, "PLAN_CREATED"),
        }
    planning_state = dict(state)
    if state.get("degraded_flags"):
        planning_state["constraints"] = {
            **state.get("constraints", {}),
            "evidence_retrieval_warnings": list(dict.fromkeys(state["degraded_flags"])),
            "evidence_search_is_exhaustive": False,
        }
    values = await plan(planning_state)
    checkpoint_state = {
        **state,
        **values,
        "planning_round": state.get("planning_round", 0) + 1,
        "automation_phases": phase(state, "PLAN_CREATED"),
    }
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AutomationCheckpointPhase.PLAN_CREATED.value,
        {"task_count": len(values.get("tasks", [])), "planning_round": state.get("planning_round", 0) + 1},
    )
    return {
        **values,
        "planning_round": state.get("planning_round", 0) + 1,
        "automation_phases": phase(state, "PLAN_CREATED"),
    }


async def replan_after_observation(state: AutomationGraphState):
    values = await plan(state)
    checkpoint_state = {
        **state,
        **values,
        "planning_round": state.get("planning_round", 0) + 1,
        "automation_phases": phase(state, "PLAN_CREATED"),
    }
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AutomationCheckpointPhase.PLAN_CREATED.value,
        {"task_count": len(values.get("tasks", [])), "planning_round": state.get("planning_round", 0) + 1},
    )
    return {
        **values,
        "planning_round": state.get("planning_round", 0) + 1,
        "automation_phases": phase(state, "PLAN_CREATED"),
    }


def route_after_plan(state: AutomationGraphState):
    return "execute" if state.get("tasks") else "finalize"


async def execute_action(state: AutomationGraphState):
    values = await execute_agent(state)
    checkpoint_state = {**state, **values, "automation_phases": phase(state, "ACTIONS_EXECUTED")}
    results = values.get("results", [])
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AutomationCheckpointPhase.ACTIONS_EXECUTED.value,
        {
            "completed_task_count": len((values.get("run") or {}).get("completed_tasks", [])),
            "latest_task_status": (results[-1].get("status") if results else None),
        },
    )
    return {**values, "automation_phases": phase(state, "ACTIONS_EXECUTED")}


async def finalize_automation(state: AutomationGraphState):
    values = await finalize(state)
    await record_phase(
        {**state, "checkpoint_state": {**state, **values}},
        AutomationCheckpointPhase.FINALIZED.value,
        {"goal_complete": bool((values.get("run") or {}).get("proposal"))},
    )
    return {**values, "automation_phases": phase(state, "FINALIZED")}


async def verify_automation(state: AutomationGraphState):
    values = await verify(state)
    checkpoint_state = {**state, **values, "automation_phases": phase(state, "ACTIONS_VERIFIED")}
    verified_run = values.get("run") or {}
    terminal_status = (
        AutomationStatus.COMPLETED
        if verified_run.get("status") == "COMPLETED"
        else AutomationStatus.FAILED
    )
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AutomationCheckpointPhase.ACTIONS_VERIFIED.value,
        {"verified": bool((verified_run.get("proposal") or {}).get("verification", {}).get("verified"))},
        terminal_status,
    )
    await record_phase(
        {**state, "checkpoint_state": {**checkpoint_state, "automation_phases": [*phase(state, "ACTIONS_VERIFIED"), "GRAPH_COMPLETED"]}},
        AutomationCheckpointPhase.GRAPH_COMPLETED.value,
        {"agent_run_id": verified_run.get("run_id")},
        terminal_status,
    )
    return {
        **values,
        "automation_phases": [
            *phase(state, "ACTIONS_VERIFIED"),
            "GRAPH_COMPLETED",
        ],
    }


workflow = StateGraph(AutomationGraphState)
workflow.add_node("resume_dispatch", resume_dispatch)
workflow.add_node("observe_sources", observe_sources)
workflow.add_node("extract_source_facts", extract_source_facts)
workflow.add_node("assess_uncertainty", assess_uncertainty)
workflow.add_node("create_action_plan", create_action_plan)
workflow.add_node("replan_after_observation", replan_after_observation)
workflow.add_node("execute_action", execute_action)
workflow.add_node("finalize_automation", finalize_automation)
workflow.add_node("aggregate", aggregate)
workflow.add_node("verify_automation", verify_automation)
workflow.set_entry_point("resume_dispatch")
workflow.add_conditional_edges(
    "resume_dispatch",
    route_resume,
    {
        "observe_sources": "observe_sources",
        "extract_source_facts": "extract_source_facts",
        "assess_uncertainty": "assess_uncertainty",
        "create_action_plan": "create_action_plan",
        "execute_action": "execute_action",
        "finalize_automation": "finalize_automation",
        "aggregate": "aggregate",
        "end": END,
    },
)
workflow.add_edge("observe_sources", "extract_source_facts")
workflow.add_edge("extract_source_facts", "assess_uncertainty")
workflow.add_edge("assess_uncertainty", "create_action_plan")
workflow.add_conditional_edges(
    "create_action_plan",
    route_after_plan,
    {"execute": "execute_action", "finalize": "finalize_automation"},
)
workflow.add_conditional_edges(
    "execute_action",
    route_after_agent,
    {
        "execute": "execute_action",
        "replan": "replan_after_observation",
        "finalize": "finalize_automation",
    },
)
workflow.add_conditional_edges(
    "replan_after_observation",
    route_after_plan,
    {"execute": "execute_action", "finalize": "finalize_automation"},
)
workflow.add_edge("finalize_automation", "aggregate")
workflow.add_conditional_edges(
    "aggregate",
    route_after_aggregate,
    {"end": END, "verify": "verify_automation"},
)
workflow.add_edge("verify_automation", END)
automation_workflow = workflow.compile()
