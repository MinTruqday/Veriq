import hashlib
import json
import re
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
from src.prompts.agent_facts import agent_fact_extraction_prompt
from src.repositories.ai_runs import ai_run_repository
from src.schemas.agent import AIRunExecutionStatus, AgentResult, AgentTaskStatus
from src.schemas.ai_runs import (
    AIRunCheckpoint,
    AIRunPhase,
    AgentFactExtraction,
    AIRunStateSnapshot,
    AIRunStatus,
)
from src.services.source_provenance import (
    is_source_fact_evidence,
    source_location_metadata,
    source_quote_spans,
    verified_source_offset_basis,
)
from src.services.inference import structured


class AgentExecutionState(TypedDict, total=False):
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
    completed_phases: list[str]
    source_event_verified: bool
    planning_round: int
    resume_after_phase: str
    worker_revision: int
    task_instruction: str


def phase(state: AgentExecutionState, name: str) -> list[str]:
    return [*state.get("completed_phases", []), name]


def distinct_uncertainty_codes(uncertainties):
    output = []
    fingerprints_by_code = {}
    used_codes = set()
    for uncertainty in uncertainties:
        value = (
            uncertainty.model_dump(mode="python")
            if hasattr(uncertainty, "model_dump")
            else dict(uncertainty)
        )
        base_code = str(value.get("code") or "").strip()
        if len(base_code) > 140:
            base_code = (
                f"{base_code[:120]}#"
                f"{hashlib.sha256(base_code.encode('utf-8')).hexdigest()[:16]}"
            )
        fingerprint_value = {
            key: child
            for key, child in value.items()
            if key not in {"code", "evidence_refs"}
        }
        fingerprint_value["evidence_refs"] = sorted(
            set(value.get("evidence_refs") or [])
        )
        fingerprint = json.dumps(
            fingerprint_value, ensure_ascii=False, sort_keys=True, default=str
        )
        fingerprints = fingerprints_by_code.setdefault(base_code, set())
        if fingerprint in fingerprints:
            continue
        code = base_code
        if fingerprints or code in used_codes:
            suffix = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12]
            code = f"{base_code}#{suffix}"
            suffix_index = 1
            while code in used_codes:
                code = f"{base_code}#{suffix}-{suffix_index}"
                suffix_index += 1
        value["code"] = code
        fingerprints.add(fingerprint)
        used_codes.add(code)
        output.append(value)
    return output


def project_source_evidence(evidence):
    return [
        item
        for item in evidence
        if str(item.get("artifact_type") or "").casefold() != "tool_result"
        and not str(item.get("authority") or "").casefold().startswith("verified_tool:")
        and is_source_fact_evidence(item)
    ]


def safety_inspection_evidence(evidence):
    return [
        *project_source_evidence(evidence),
        *[
            item
            for item in evidence
            if str(item.get("authority") or "").casefold()
            in {"user_clarification", "user_answer"}
        ],
    ]


def route_resume(state: AgentExecutionState):
    completed = state.get("resume_after_phase")
    if completed == AIRunPhase.OBSERVED.value:
        return "extract_source_facts"
    if completed == AIRunPhase.FACTS_EXTRACTED.value:
        return "assess_uncertainty"
    if completed == AIRunPhase.UNCERTAINTY_ASSESSED.value:
        return "create_action_plan"
    if completed == AIRunPhase.PLAN_CREATED.value:
        return "execute_action" if state.get("tasks") else "finalize_run"
    if completed == AIRunPhase.ACTION_STARTED.value:
        return "execute_action"
    if completed == AIRunPhase.ACTIONS_EXECUTED.value:
        return "execute_action"
    if completed == AIRunPhase.FINALIZED.value:
        return "aggregate"
    if completed in {
        AIRunPhase.ACTIONS_VERIFIED.value,
        AIRunPhase.GRAPH_COMPLETED.value,
    }:
        return "end"
    return "observe_sources"


async def record_phase(state: AgentExecutionState, name: str, detail=None, status=None):
    snapshot_state = state.get("checkpoint_state") or state
    run = snapshot_state.get("run") or {}
    if not run.get("run_id"):
        return
    snapshot = AIRunStateSnapshot.model_validate(
        {
            key: value
            for key, value in snapshot_state.items()
            if key in AIRunStateSnapshot.model_fields and key != "completed_phase"
        }
        | {"completed_phase": name}
    )
    checkpoint_saved = await ai_run_repository.save_checkpoint(
        AIRunCheckpoint(
            ai_run_id=run["run_id"],
            phase=AIRunPhase(name),
            status=status or AIRunStatus.RUNNING,
            detail=detail or {},
            state_snapshot=snapshot,
        ),
        expected_worker_revision=state.get("worker_revision"),
    )
    if not checkpoint_saved:
        raise RuntimeError("AI_RUN_WORKER_FENCE_LOST")


async def observe_sources(state: AgentExecutionState):
    values = await load_context(state)
    checkpoint_state = {**state, **values}
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AIRunPhase.OBSERVED.value,
        {
            "evidence_count": len(values.get("evidence", [])),
            "degraded_flags": values.get("degraded_flags", []),
        },
    )
    return {
        **values,
        "completed_phases": phase(state, "OBSERVED"),
    }


def bind_extracted_facts(extraction, evidence):
    facts = []
    for fact in extraction.facts:
        candidates = [
            item
            for item in evidence
            if str(item.get("artifact_id")) == fact.artifact_id
            and (
                not item.get("artifact_type")
                or str(item.get("artifact_type")) == fact.artifact_type
            )
            and (
                not fact.artifact_version_id
                or str(item.get("artifact_version_id") or "")
                == str(fact.artifact_version_id)
            )
        ]
        source_versions = {
            str(item.get("artifact_version_id") or item.get("artifact_id"))
            for item in candidates
        }
        quote = fact.quote.strip()
        source = None
        source_start = None
        if candidates and len(source_versions) == 1 and quote:
            for item in candidates:
                text = str(item.get("text") or "")
                matching_spans = source_quote_spans(text, quote)
                if matching_spans:
                    source = item
                    source_start = matching_spans[0][0]
                    break
        if not source:
            continue
        facts.append(
            {
                "artifact_type": str(source.get("artifact_type") or fact.artifact_type),
                "artifact_id": str(source["artifact_id"]),
                "artifact_version_id": source.get("artifact_version_id"),
                "source": str(source.get("source") or fact.source),
                "authority": str(source.get("authority") or fact.authority),
                "relationship_path": list(source.get("relationship_path") or []),
                "quote": quote,
                "fact_kind": fact.fact_kind,
                "source_start": source_start,
                "source_end": source_start + len(quote),
                **source_location_metadata(source),
                "source_offset_basis": verified_source_offset_basis(source),
            }
        )
    return facts


def complete_source_segments(facts, evidence):
    """Retain exact source sentences even when a model omits explicit statements."""
    output = list(facts)
    seen = {
        (
            str(item.get("artifact_id") or ""),
            str(item.get("artifact_version_id") or item.get("artifact_id") or ""),
            item.get("source_start"),
            item.get("source_end"),
            str(item.get("quote") or ""),
        )
        for item in output
    }
    for source in evidence:
        text = str(source.get("text") or "")
        source_id = str(source.get("artifact_id") or "")
        source_version_id = str(
            source.get("artifact_version_id") or source.get("artifact_id") or ""
        )
        cursor = 0
        for line in text.splitlines() or [text]:
            for segment in re.split(r"(?<=[.!?。！？])\s+", line):
                quote = segment.strip()
                if not quote:
                    continue
                start = text.find(quote, cursor)
                if start < 0:
                    start = text.find(quote)
                if start < 0:
                    continue
                end = start + len(quote)
                identity = (source_id, source_version_id, start, end, quote)
                if identity in seen:
                    cursor = end
                    continue
                output.append(
                    {
                        "artifact_type": str(source.get("artifact_type") or "artifact"),
                        "artifact_id": str(source["artifact_id"]),
                        "artifact_version_id": source.get("artifact_version_id"),
                        "source": str(source.get("source") or "database"),
                        "authority": str(source.get("authority") or "project"),
                        "relationship_path": list(source.get("relationship_path") or []),
                        "quote": quote,
                        "fact_kind": "source_text_segment",
                        "source_start": start,
                        "source_end": end,
                        **source_location_metadata(source),
                        "source_offset_basis": verified_source_offset_basis(source),
                    }
                )
                cursor = end
                seen.add(identity)
    return output


async def extract_source_facts(state: AgentExecutionState):
    run = state.get("run") or {}
    document_ingestion_intent = (
        run.get("intent") == "process_ingested_requirement_document"
    )
    evidence = [
        item for item in state.get("evidence", [])
        if str(item.get("text") or "").strip() and item.get("artifact_id")
    ]
    source_evidence = project_source_evidence(evidence)
    safety_evidence = safety_inspection_evidence(evidence)
    facts = []
    uncertainties = []
    degraded_flags = list(state.get("degraded_flags", []))
    output_language = (state.get("constraints") or {}).get("output_language")
    if safety_evidence:
        try:
            inspected = await guardrails_engine.async_inspect_input(
                "\n".join(str(item.get("text") or "") for item in safety_evidence)
            )
        except Exception:
            inspected = None
            uncertainties.append(
                {
                    "code": "SOURCE_SAFETY_CHECK_UNAVAILABLE",
                    "reason": 'Không xác minh được độ an toàn của nguồn nên nội dung chưa được chuyển cho AI.',
                    "evidence_refs": [],
                    "blocking": True,
                }
            )
        if inspected is not None and not inspected.get("is_safe", False):
            safety_check_unavailable = (
                inspected.get("threat_category") == "classifier_unavailable"
            )
            uncertainties.append(
                {
                    "code": (
                        "SOURCE_SAFETY_CHECK_UNAVAILABLE"
                        if safety_check_unavailable
                        else "SOURCE_INJECTION_REJECTED"
                    ),
                    "reason": (
                        'Không xác minh được độ an toàn của nguồn nên nội dung chưa được chuyển cho AI.'
                        if safety_check_unavailable
                        else 'Nguồn đã bị chặn bởi cơ chế kiểm tra an toàn.'
                    ),
                    "evidence_refs": [],
                    "blocking": True,
                }
            )
        elif inspected is not None:
            if source_evidence:
                try:
                    extraction_prompt = agent_fact_extraction_prompt(
                        source_evidence,
                        state.get("task_instruction", ""),
                        (state.get("constraints") or {}).get("output_language"),
                    )
                    extraction = await structured(
                        extraction_prompt,
                        AgentFactExtraction,
                        max_tokens=1200,
                        timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
                        provider_schema=False,
                        initial_temperature=0,
                    )
                    facts = complete_source_segments(
                        bind_extracted_facts(extraction, source_evidence), source_evidence
                    )
                    source_refs = {
                        str(value.get("artifact_version_id") or value.get("artifact_id"))
                        for value in source_evidence
                    }
                    uncertainties = distinct_uncertainty_codes(
                        [
                            item.model_copy(update={"blocking": False})
                            for item in extraction.uncertainties
                            if set(item.evidence_refs).issubset(source_refs)
                        ]
                    )
                except Exception:
                    facts = complete_source_segments([], source_evidence)
                    if facts:
                        degraded_flags.append("FACT_EXTRACTION_FALLBACK_USED")
                    else:
                        uncertainties.append(
                            {
                                "code": "FACT_EXTRACTION_UNAVAILABLE",
                                "reason": 'Không trích xuất được dữ kiện và cũng không có đoạn nguồn đủ điều kiện làm căn cứ.',
                                "evidence_refs": [],
                                "blocking": True,
                            }
                        )
            elif not document_ingestion_intent:
                uncertainties.append(
                    {
                        "code": "NO_PERMITTED_SOURCE_EVIDENCE",
                        "reason": 'Câu trả lời làm rõ không thay thế được tài liệu hoặc Requirement có nguồn được phép.',
                        "evidence_refs": [],
                        "blocking": True,
                    }
                )
            if (
                not facts
                and not document_ingestion_intent
                and not any(item.get("blocking") for item in uncertainties)
            ):
                uncertainties.append(
                    {
                        "code": "NO_VERIFIABLE_SOURCE_FACTS",
                        "reason": 'Không có trích dẫn khớp nguyên văn với nguồn được phép đọc.',
                        "evidence_refs": [],
                        "blocking": True,
                    }
                )
    elif not document_ingestion_intent:
        uncertainties.append(
            {
                "code": "NO_PERMITTED_SOURCE_EVIDENCE",
                "reason": 'Câu trả lời làm rõ không thay thế được tài liệu hoặc Requirement có nguồn được phép.',
                "evidence_refs": [],
                "blocking": True,
            }
        )
    checkpoint_state = {
        **state,
        "degraded_flags": degraded_flags,
        "source_facts": facts,
        "uncertainties": uncertainties,
        "completed_phases": phase(state, "FACTS_EXTRACTED"),
    }
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AIRunPhase.FACTS_EXTRACTED.value,
        {"source_fact_count": len(facts)},
    )
    return {
        "degraded_flags": degraded_flags,
        "source_facts": facts,
        "uncertainties": uncertainties,
        "completed_phases": phase(state, "FACTS_EXTRACTED"),
    }


async def assess_uncertainty(state: AgentExecutionState):
    run = state.get("run") or {}
    document_ingestion_intent = (
        run.get("intent") == "process_ingested_requirement_document"
    )
    uncertainties = list(state.get("uncertainties", []))
    if (
        not document_ingestion_intent
        and not state.get("source_facts")
        and not any(
            item.get("blocking") for item in uncertainties
        )
    ):
        uncertainties.append(
            {
                "code": "SOURCE_INPUT_REQUIRED",
                "reason": 'Không có dữ kiện nào được trích dẫn và xác minh từ nguồn được phép đọc. Cần chọn nguồn phù hợp rồi chạy lại.',
                "evidence_refs": [],
                "blocking": True,
            }
        )
    for flag in state.get("degraded_flags", []):
        uncertainties.append(
            {
                "code": str(flag),
                "reason": 'Việc truy xuất bằng chứng chưa đầy đủ; các nguồn có thẩm quyền đã lấy được vẫn có thể sử dụng.',
                "evidence_refs": [],
                "blocking": False,
            }
        )
    uncertainties = distinct_uncertainty_codes(uncertainties)
    checkpoint_state = {**state, "uncertainties": uncertainties, "completed_phases": phase(state, "UNCERTAINTY_ASSESSED")}
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AIRunPhase.UNCERTAINTY_ASSESSED.value,
        {
            "uncertainty_count": len(uncertainties),
            "blocking_count": sum(bool(item.get("blocking")) for item in uncertainties),
        },
    )
    return {
        "uncertainties": uncertainties,
        "completed_phases": phase(state, "UNCERTAINTY_ASSESSED"),
    }


async def create_action_plan(state: AgentExecutionState):
    blocking_uncertainties = [
        item for item in state.get("uncertainties", []) if item.get("blocking")
    ]
    if blocking_uncertainties:
        run = dict(state["run"])
        result = AgentResult(
            task_id=f"RUN-PLAN-{run['run_id']}",
            status=AgentTaskStatus.INSUFFICIENT_EVIDENCE,
            summary='Chưa thể tiếp tục xử lý vì bằng chứng nguồn được phép đang thiếu hoặc chưa đầy đủ.',
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
            "completed_phases": phase(state, "PLAN_CREATED"),
        }
        await record_phase(
            {**state, "checkpoint_state": checkpoint_state},
            AIRunPhase.PLAN_CREATED.value,
            {"task_count": 0, "blocked": True},
        )
        return {
            "tasks": [],
            "planning_round": 1,
            "success_criteria": [],
            "results": [result.model_dump(mode="python")],
            "completed_phases": phase(state, "PLAN_CREATED"),
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
        "completed_phases": phase(state, "PLAN_CREATED"),
    }
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AIRunPhase.PLAN_CREATED.value,
        {"task_count": len(values.get("tasks", [])), "planning_round": state.get("planning_round", 0) + 1},
    )
    return {
        **values,
        "planning_round": state.get("planning_round", 0) + 1,
        "completed_phases": phase(state, "PLAN_CREATED"),
    }


async def replan_after_observation(state: AgentExecutionState):
    values = await plan(state)
    checkpoint_state = {
        **state,
        **values,
        "planning_round": state.get("planning_round", 0) + 1,
        "completed_phases": phase(state, "PLAN_CREATED"),
    }
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AIRunPhase.PLAN_CREATED.value,
        {"task_count": len(values.get("tasks", [])), "planning_round": state.get("planning_round", 0) + 1},
    )
    return {
        **values,
        "planning_round": state.get("planning_round", 0) + 1,
        "completed_phases": phase(state, "PLAN_CREATED"),
    }


def route_after_plan(state: AgentExecutionState):
    return "execute" if state.get("tasks") else "finalize"


async def execute_action(state: AgentExecutionState):
    values = await execute_agent(state)
    checkpoint_state = {**state, **values, "completed_phases": phase(state, "ACTIONS_EXECUTED")}
    results = values.get("results", [])
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AIRunPhase.ACTIONS_EXECUTED.value,
        {
            "completed_task_count": len((values.get("run") or {}).get("completed_tasks", [])),
            "latest_task_status": (results[-1].get("status") if results else None),
        },
    )
    return {**values, "completed_phases": phase(state, "ACTIONS_EXECUTED")}


async def finalize_run(state: AgentExecutionState):
    values = await finalize(state)
    await record_phase(
        {**state, "checkpoint_state": {**state, **values}},
        AIRunPhase.FINALIZED.value,
        {"goal_complete": bool((values.get("run") or {}).get("proposal"))},
    )
    return {**values, "completed_phases": phase(state, "FINALIZED")}


async def verify_run(state: AgentExecutionState):
    values = await verify(state)
    checkpoint_state = {**state, **values, "completed_phases": phase(state, "ACTIONS_VERIFIED")}
    verified_run = values.get("run") or {}
    terminal_status = (
        AIRunExecutionStatus.COMPLETED
        if verified_run.get("status") == "COMPLETED"
        else AIRunExecutionStatus.FAILED
    )
    await record_phase(
        {**state, "checkpoint_state": checkpoint_state},
        AIRunPhase.ACTIONS_VERIFIED.value,
        {"verified": bool((verified_run.get("proposal") or {}).get("verification", {}).get("verified"))},
        terminal_status,
    )
    await record_phase(
        {**state, "checkpoint_state": {**checkpoint_state, "completed_phases": [*phase(state, "ACTIONS_VERIFIED"), "GRAPH_COMPLETED"]}},
        AIRunPhase.GRAPH_COMPLETED.value,
        {"ai_run_id": verified_run.get("run_id")},
        terminal_status,
    )
    return {
        **values,
        "completed_phases": [
            *phase(state, "ACTIONS_VERIFIED"),
            "GRAPH_COMPLETED",
        ],
    }


async def resume_dispatch(state: AgentExecutionState):
    return {}


ai_run_graph_builder = StateGraph(AgentExecutionState)
ai_run_graph_builder.add_node("resume_dispatch", resume_dispatch)
ai_run_graph_builder.add_node("observe_sources", observe_sources)
ai_run_graph_builder.add_node("extract_source_facts", extract_source_facts)
ai_run_graph_builder.add_node("assess_uncertainty", assess_uncertainty)
ai_run_graph_builder.add_node("create_action_plan", create_action_plan)
ai_run_graph_builder.add_node("replan_after_observation", replan_after_observation)
ai_run_graph_builder.add_node("execute_action", execute_action)
ai_run_graph_builder.add_node("finalize_run", finalize_run)
ai_run_graph_builder.add_node("aggregate", aggregate)
ai_run_graph_builder.add_node("verify_run", verify_run)
ai_run_graph_builder.set_entry_point("resume_dispatch")
ai_run_graph_builder.add_conditional_edges(
    "resume_dispatch",
    route_resume,
    {
        "observe_sources": "observe_sources",
        "extract_source_facts": "extract_source_facts",
        "assess_uncertainty": "assess_uncertainty",
        "create_action_plan": "create_action_plan",
        "execute_action": "execute_action",
        "finalize_run": "finalize_run",
        "aggregate": "aggregate",
        "end": END,
    },
)
ai_run_graph_builder.add_edge("observe_sources", "extract_source_facts")
ai_run_graph_builder.add_edge("extract_source_facts", "assess_uncertainty")
ai_run_graph_builder.add_edge("assess_uncertainty", "create_action_plan")
ai_run_graph_builder.add_conditional_edges(
    "create_action_plan",
    route_after_plan,
    {"execute": "execute_action", "finalize": "finalize_run"},
)
ai_run_graph_builder.add_conditional_edges(
    "execute_action",
    route_after_agent,
    {
        "execute": "execute_action",
        "replan": "replan_after_observation",
        "finalize": "finalize_run",
    },
)
ai_run_graph_builder.add_conditional_edges(
    "replan_after_observation",
    route_after_plan,
    {"execute": "execute_action", "finalize": "finalize_run"},
)
ai_run_graph_builder.add_edge("finalize_run", "aggregate")
ai_run_graph_builder.add_conditional_edges(
    "aggregate",
    route_after_aggregate,
    {"verify": "verify_run", "end": END},
)
ai_run_graph_builder.add_edge("verify_run", END)
ai_run_graph = ai_run_graph_builder.compile()


async def run_ai_run_graph(initial_state: AgentExecutionState) -> AgentExecutionState:
    return await ai_run_graph.ainvoke(
        initial_state,
        config={"recursion_limit": settings.AI_AGENT_MAX_STEPS * 6 + 24},
    )
