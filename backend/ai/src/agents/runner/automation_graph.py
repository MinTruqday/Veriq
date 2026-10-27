import asyncio
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
from src.core.infrastructure.observability import trace_span
from src.core.security.guardrails import guardrails_engine
from src.prompts.automation import automation_fact_extraction_prompt
from src.repositories.automation import automation_repository
from src.schemas.agent import AgentResult, AgentTaskStatus
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationFactExtraction,
    AutomationGraphSnapshot,
    AutomationStatus,
)
from src.services.automation_provenance import (
    is_source_fact_evidence,
    source_location_metadata,
    source_quote_spans,
    verified_release_gate_control_evidence,
    verified_source_offset_basis,
)
from src.services.inference import structured


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
    worker_revision: int


def phase(state: AutomationGraphState, name: str) -> list[str]:
    return [*state.get("automation_phases", []), name]


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
    checkpoint_saved = await automation_repository.save_checkpoint(
        AutomationCheckpoint(
            automation_run_id=run["run_id"],
            phase=AutomationCheckpointPhase(name),
            status=status or AutomationStatus.RUNNING,
            detail=detail or {},
            state_snapshot=snapshot,
        ),
        expected_worker_revision=state.get("worker_revision"),
    )
    if not checkpoint_saved:
        raise RuntimeError("AUTOMATION_WORKER_FENCE_LOST")


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


async def extract_source_facts(state: AutomationGraphState):
    evidence = [
        item for item in state.get("evidence", [])
        if str(item.get("text") or "").strip() and item.get("artifact_id")
    ]
    release_controls = verified_release_gate_control_evidence(state)
    release_control_ids = {id(item) for item in release_controls}
    source_evidence = [
        item
        for item in evidence
        if is_source_fact_evidence(item)
        and id(item) not in release_control_ids
    ]
    safety_evidence = [
        item
        for item in evidence
        if id(item) not in release_control_ids
    ]
    facts = []
    uncertainties = []
    degraded_flags = list(state.get("degraded_flags", []))
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
                    "question": "Có thể tiếp tục sau khi dịch vụ kiểm tra an toàn nguồn hoạt động lại không?",
                    "reason": "Không xác minh được độ an toàn của nguồn nên không thể chuyển nguồn cho AI",
                    "evidence_refs": [],
                    "blocking": True,
                    "response_allowed": False,
                }
            )
        if inspected is not None and not inspected.get("is_safe", False):
            uncertainties.append(
                {
                    "code": "SOURCE_INJECTION_REJECTED",
                    "question": "Có thể rà soát tài liệu nguồn và gửi lại sau khi loại bỏ chỉ dẫn không liên quan không?",
                    "reason": "Nguồn bị chặn bởi cơ chế kiểm tra an toàn",
                    "evidence_refs": [],
                    "blocking": True,
                    "response_allowed": False,
                }
            )
        elif inspected is not None:
            if source_evidence:
                try:
                    extraction_prompt = automation_fact_extraction_prompt(source_evidence)
                    extraction = await structured(
                        extraction_prompt,
                        AutomationFactExtraction,
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
                                "question": "Có thể tiếp tục sau khi dịch vụ phân tích nguồn hoạt động lại không?",
                                "reason": "Không trích xuất được facts và cũng không có đoạn nguồn đủ điều kiện làm căn cứ",
                                "evidence_refs": [],
                                "blocking": True,
                                "response_allowed": False,
                            }
                        )
            elif not release_controls:
                uncertainties.append(
                    {
                        "code": "NO_PERMITTED_SOURCE_EVIDENCE",
                        "question": "Có tài liệu hoặc Requirement được phép AI đọc để làm căn cứ không?",
                        "reason": "Câu trả lời làm rõ của người dùng không thay thế tài liệu hoặc Requirement có nguồn",
                        "evidence_refs": [],
                        "blocking": True,
                        "response_allowed": False,
                    }
                )
            if (
                not facts
                and not release_controls
                and not any(item.get("blocking") for item in uncertainties)
            ):
                uncertainties.append(
                    {
                        "code": "NO_VERIFIABLE_SOURCE_FACTS",
                        "question": "Có thể cung cấp hoặc xác nhận đoạn nguồn làm căn cứ cho yêu cầu này không?",
                        "reason": "Không có trích dẫn khớp nguyên văn với tài liệu được phép đọc",
                        "evidence_refs": [],
                        "blocking": True,
                    }
                )
    elif not release_controls:
        uncertainties.append(
            {
                "code": "NO_PERMITTED_SOURCE_EVIDENCE",
                "question": "Có tài liệu hoặc Requirement được phép AI đọc để làm căn cứ không?",
                "reason": "Không có nguồn dự án được phép đọc trong sự kiện này",
                "evidence_refs": [],
                "blocking": True,
                "response_allowed": False,
            }
        )
    checkpoint_state = {
        **state,
        "degraded_flags": degraded_flags,
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
        "degraded_flags": degraded_flags,
        "source_facts": facts,
        "uncertainties": uncertainties,
        "automation_phases": phase(state, "FACTS_EXTRACTED"),
    }


async def assess_uncertainty(state: AutomationGraphState):
    uncertainties = list(state.get("uncertainties", []))
    clarification_responses = {
        str(item.get("uncertainty_code") or ""): item
        for item in (state.get("constraints") or {}).get("clarification_responses", [])
        if isinstance(item, dict) and item.get("uncertainty_code")
    }
    uncertainties = [
        {
            **item,
            "resolution_status": (
                "USER_ANSWERED" if not item.get("blocking") else "OPEN"
            ),
            "answer": clarification_responses[str(item.get("code"))].get("answer"),
            "answered_by": clarification_responses[str(item.get("code"))].get("answered_by"),
            "answered_at": clarification_responses[str(item.get("code"))].get("answered_at"),
        }
        if item.get("response_allowed", True)
        and str(item.get("code") or "") in clarification_responses
        else item
        for item in uncertainties
    ]
    if (
        not state.get("source_facts")
        and not verified_release_gate_control_evidence(state)
        and not any(
        item.get("blocking") for item in uncertainties
        )
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
                "reason": "Việc truy xuất bằng chứng chưa đầy đủ; các nguồn có thẩm quyền đã lấy được vẫn có thể sử dụng",
                "evidence_refs": [],
                "blocking": False,
            }
        )
    uncertainties = distinct_uncertainty_codes(uncertainties)
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
            summary="Chưa thể tiếp tục tự động xử lý vì bằng chứng nguồn đang thiếu hoặc chưa đầy đủ",
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


def traced_node(name, node):
    async def invoke(state):
        run = state.get("run") or {}
        with trace_span(
            f"automation.node.{name}",
            {
                "automation.run_id": run.get("run_id"),
                "automation.node": name,
            },
        ) as span:
            try:
                result = await node(state)
            except asyncio.CancelledError:
                if span is not None:
                    span.set_attribute("event.status", "cancelled")
                raise
            except Exception:
                if span is not None:
                    span.set_attribute("event.status", "failed")
                raise
            if span is not None:
                span.set_attribute("event.status", "completed")
            return result

    return invoke


workflow = StateGraph(AutomationGraphState)
workflow.add_node("resume_dispatch", traced_node("resume_dispatch", resume_dispatch))
workflow.add_node("observe_sources", traced_node("observe_sources", observe_sources))
workflow.add_node("extract_source_facts", traced_node("extract_source_facts", extract_source_facts))
workflow.add_node("assess_uncertainty", traced_node("assess_uncertainty", assess_uncertainty))
workflow.add_node("create_action_plan", traced_node("create_action_plan", create_action_plan))
workflow.add_node("replan_after_observation", traced_node("replan_after_observation", replan_after_observation))
workflow.add_node("execute_action", traced_node("execute_action", execute_action))
workflow.add_node("finalize_automation", traced_node("finalize_automation", finalize_automation))
workflow.add_node("aggregate", traced_node("aggregate", aggregate))
workflow.add_node("verify_automation", traced_node("verify_automation", verify_automation))
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
