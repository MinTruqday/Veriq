import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from src.agents.agent import execute_task
from src.agents.runner.planning import (
    available_tools,
    direct_capability_task,
    direct_change_simulation_task,
    observed_draft_identifiers,
    observed_identifiers,
    simulation_baseline_trace_links,
    simulation_baseline_trace_snapshot,
    simulation_linked_test_case_version_ids,
    tool_evidence_reference,
    validated_tasks,
    verified_tool_call_records,
)
from src.core.security.guardrails import guardrails_engine
from src.knowledge.evidence import package
from src.knowledge.hybrid import hybrid_evidence
from src.prompts.agent_planning import (
    agent_plan_prompt,
    change_simulation_instruction,
    verified_source_fact_instruction,
)
from src.prompts.change_simulation import change_simulation_report_instruction
from src.repositories.ai_runs import ai_run_repository
from src.runtime.limits import limits
from src.runtime.output import normalize_narrative, normalize_narratives
from src.schemas.agent import (
    AgentPlan,
    AgentProposal,
    AgentResult,
    AIRunExecutionStatus,
    AgentTask,
    AgentTaskStatus,
    EvidenceItem,
    ToolExecutionStatus,
    VeriqRunState,
)
from src.schemas.ai_runs import (
    AIRunCheckpoint,
    AIRunPhase,
    AIRunStateSnapshot,
)
from src.schemas.inference_change_simulation import ChangeSimulationReportOutput
from src.services.change_simulation import (
    change_simulation_batches,
    simulation_trace_scope_is_current,
    simulation_source_payload,
    validate_change_simulation_report,
)
from src.services.inference import structured
from src.tools.registry import registered_tools, tool_access


def state_run(state):
    return VeriqRunState(**state["run"])


def evidence_for_references(evidence, references):
    by_reference = {}
    for item in evidence or []:
        reference = item.get("artifact_version_id") or item.get("artifact_id")
        if reference:
            by_reference.setdefault(str(reference), []).append(item)

    selected = []
    seen = set()
    for reference in references or []:
        for item in by_reference.get(str(reference), []):
            identity = (
                str(item.get("artifact_type") or ""),
                str(item.get("artifact_version_id") or item.get("artifact_id") or ""),
                str(item.get("chunk_id") or ""),
                str(item.get("text") or ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            selected.append(item)
    return selected


def test_case_change_context(run, evidence):
    event_text = "\n".join(str(item.get("text") or "") for item in evidence)
    event_kind = next(
        (line.partition(":")[2].strip() for line in event_text.splitlines() if line.startswith("Event type:")),
        "",
    )
    changed_fields = next(
        (line.partition(":")[2].strip() for line in event_text.splitlines() if line.startswith("Changed fields:")),
        "",
    )
    has_comparison = (
        event_kind == "TEST_CASE_UPDATED"
        and bool(changed_fields)
        and changed_fields.casefold() != "none"
        and "Before Test Case content:" in event_text
        and "Current Test Case content:" in event_text
    )
    current_draft = next(
        (
            item.get("result") or {}
            for item in run.observations
            if item.get("tool_name") == "get_test_case_draft"
            and item.get("status") == ToolExecutionStatus.COMPLETED
        ),
        {},
    )
    source_event = next(
        (
            item
            for item in evidence
            if item.get("artifact_type") == "test_case_draft"
            and item.get("artifact_id") == current_draft.get("_id")
        ),
        None,
    )
    event_revision = (source_event or {}).get("artifact_revision")
    event_revision_match = re.search(r"^Current revision:\s*(\d+)$", event_text, re.MULTILINE)
    expected_revision = (
        event_revision
        if type(event_revision) is int and event_revision >= 1
        else int(event_revision_match.group(1)) if event_revision_match else None
    )
    if expected_revision is not None and current_draft.get("revision") != expected_revision:
        has_comparison = False
    has_source_link = any(
        current_draft.get(field)
        for field in (
            "requirement_version_ids",
            "acceptance_criterion_ids",
            "coverage_item_ids",
            "test_condition_ids",
            "evidence_refs",
            "source_evidence",
        )
    )
    return {
        "event_kind": event_kind,
        "changed_fields": changed_fields,
        "has_comparison": has_comparison,
        "has_source_link": bool(has_source_link),
        "current_draft": current_draft,
    }


async def load_context(state):
    run = state_run(state)
    supplied = [EvidenceItem(**item) for item in state.get("evidence", [])]
    event_scope = state.get("source_event_verified") is True
    constraints = state.get("constraints") or {}
    simulation_scope = bool(constraints.get("change_simulation"))
    supplied = [item for item in supplied if item.project_id == run.project_id]
    if simulation_scope:
        simulation = constraints.get("change_simulation_input") or {}
        baseline_version_id = str(simulation.get("base_requirement_version_id") or "")
        supplied = [
            item for item in supplied
            if item.artifact_type == "requirement_version"
            and item.artifact_version_id == baseline_version_id
        ]
    if event_scope or simulation_scope:
        evidence_items = supplied
        degraded_flags = []
    else:
        retrieved = await hybrid_evidence(
            run.project_id,
            run.objective,
            run.user_id,
            state.get("token"),
            ai_run_id=run.run_id if state.get("automatic") else None,
        )
        verified_refs = {
            item.artifact_version_id or item.artifact_id for item in retrieved.items
        }
        supplied = [
            item
            for item in supplied
            if (item.artifact_version_id or item.artifact_id) in verified_refs
        ]
        evidence_items = [*supplied, *retrieved.items]
        degraded_flags = retrieved.degraded_flags
    combined = package(
        run.project_id,
        run.objective,
        evidence_items,
        degraded_flags,
    )
    run.evidence_refs = list(
        dict.fromkeys(item.artifact_version_id or item.artifact_id for item in combined.items)
    )
    run.observations.append(
        {
            "phase": "LOAD_CONTEXT",
            "evidence_count": len(combined.items),
            "degraded_flags": combined.degraded_flags,
        }
    )
    run.updated_at = datetime.now(timezone.utc)
    return {
        "run": run.model_dump(mode="python"),
        "evidence": [item.model_dump(mode="python") for item in combined.items],
        "degraded_flags": combined.degraded_flags,
    }


async def plan(state):
    run = state_run(state)
    constraints = state.get("constraints") or {}
    simulation = bool(constraints.get("change_simulation"))
    evidence_refs = [
        item.get("artifact_version_id") or item.get("artifact_id")
        for item in state.get("evidence", [])
    ]
    direct_task = None
    if simulation:
        direct_task = direct_change_simulation_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = (
            direct_capability_task(run, state, evidence_refs)
            if run.intent and not run.completed_tasks
            else None
        )
    if direct_task:
        run.execution_plan = [direct_task.model_dump(mode="json")]
        run.status = AIRunExecutionStatus.RUNNING
        run.current_step = 1
        return {
            "run": run.model_dump(mode="python"),
            "tasks": [direct_task.model_dump(mode="python")],
            "success_criteria": [run.objective],
            "results": [],
        }
    verified_source_facts = [
        {
            "artifact_type": item.get("artifact_type"),
            "artifact_id": item.get("artifact_id"),
            "artifact_version_id": item.get("artifact_version_id"),
            "quote": item.get("quote"),
            "fact_kind": item.get("fact_kind"),
            "relationship_path": list(item.get("relationship_path") or []),
        }
        for item in state.get("source_facts", [])
        if item.get("quote")
        and (item.get("artifact_version_id") or item.get("artifact_id")) in evidence_refs
    ]
    verified_tool_evidence = [
        item
        for item in state.get("evidence", [])
        if item.get("source") == "tool"
        and item.get("artifact_id") in run.evidence_refs
    ]
    prior_verified_tool_refs = [
        item.get("artifact_id") for item in verified_tool_evidence[:-1]
        if item.get("artifact_id")
    ]
    completed_results = {
        str(item.get("task_id") or ""): item
        for item in run.agent_results
        if isinstance(item, dict) and item.get("task_id")
    }
    completed_task_context = []
    for task in run.completed_tasks[-limits.agent_steps :]:
        if not isinstance(task, dict):
            continue
        task_constraints = task.get("constraints") or {}
        result = completed_results.get(str(task.get("task_id") or ""), {})
        completed_task_context.append(
            {
                "task_id": task.get("task_id"),
                "domain": task.get("domain"),
                "objective": str(task.get("objective") or "")[:1200],
                "stage": task_constraints.get("change_simulation_stage"),
                "workflow_terminal": task_constraints.get("workflow_terminal"),
                "status": result.get("status"),
                "summary": str(result.get("summary") or "")[:1200],
            }
        )
    prompt = agent_plan_prompt(
        run.project_id,
        run.run_id,
        run.objective,
        run.intent,
        state.get("target_artifact_ids", []),
        available_tools(
            run.permissions,
            compact=True,
            actions={"READ"} if simulation else None,
        ),
        evidence_refs,
        {
            **state.get("constraints", {}),
            "verified_source_facts": verified_source_facts,
            "verified_tool_results": [
                {
                    "evidence_ref": item.get("artifact_id"),
                    "authority": item.get("authority"),
                    "content": item.get("text"),
                }
                for item in verified_tool_evidence[-limits.agent_steps :]
            ],
            "prior_verified_tool_refs": prior_verified_tool_refs,
            "source_fact_use": verified_source_fact_instruction(),
            "change_simulation": simulation,
            "simulation_rule": change_simulation_instruction() if simulation else None,
            "completed_task_context": completed_task_context,
            "execution_mode": "AUTOMATIC_WITHIN_EXECUTION_PRINCIPAL_PERMISSIONS"
            if state.get("automatic")
            else "INTERACTIVE_AGENT",
            "completed_tool_calls": run.tool_calls,
            "recent_tool_observations": [
                {
                    key: item.get(key)
                    for key in ("phase", "status", "tool_name", "reason_code", "evidence_ref")
                    if item.get(key) is not None
                }
                for item in run.observations[-limits.agent_steps :]
            ],
        },
    )
    try:
        generated = await structured(
            prompt,
            AgentPlan,
            max_tokens=1600,
            timeout_seconds=limits.task_timeout_seconds,
        )
    except Exception:
        run.intent = run.intent or "project_question"
        run.status = AIRunExecutionStatus.RUNNING
        if not run.completed_tasks:
            run.current_step = 1
        run.observations.append(
            {"phase": "PLAN", "reason_code": "AI_PROVIDER_UNAVAILABLE"}
        )
        result = AgentResult(
            task_id=f"PLAN-{run.run_id}",
            status=AgentTaskStatus.INSUFFICIENT_EVIDENCE,
            summary='Nhà cung cấp AI hiện không khả dụng nên chưa thể lập kế hoạch xử lý.',
            evidence_refs=evidence_refs,
            reason_codes=["AI_PROVIDER_UNAVAILABLE"],
            warnings=["AI_PROVIDER_UNAVAILABLE"],
        )
        return {
            "run": run.model_dump(mode="python"),
            "tasks": [],
            "success_criteria": [],
            "results": [*state.get("results", []), result.model_dump(mode="python")],
        }
    allowed_identifiers = list(
        dict.fromkeys(
            [
                *evidence_refs,
                *state.get("target_artifact_ids", []),
                *observed_identifiers(run.observations),
                *[
                    item.get("artifact_id")
                    for item in state.get("evidence", [])
                    if item.get("artifact_id")
                ],
            ]
        )
    )
    run.intent = run.intent or generated.intent
    planned_tasks = validated_tasks(
        generated.tasks,
        run,
        evidence_refs,
        known_identifiers=allowed_identifiers,
        known_draft_identifiers=observed_draft_identifiers(
            [state.get("evidence", []), run.observations]
        ),
    )
    tasks = [task for task in planned_tasks if task.tool_calls]
    results = list(state.get("results", []))
    if not tasks:
        prior_results = [AgentResult(**item) for item in results]
        completed_user_request = (
            bool(state.get("automatic"))
            and bool(run.completed_tasks)
            and bool(prior_results)
            and all(item.status == AgentTaskStatus.COMPLETED for item in prior_results)
        )
        if completed_user_request:
            results.append(
                AgentResult(
                    task_id=f"PLAN-{run.run_id}",
                    status=AgentTaskStatus.COMPLETED,
                    summary='Các hành động có căn cứ đã hoàn tất. Không còn hành động tiếp theo phù hợp với quyền hiện tại.',
                    evidence_refs=evidence_refs,
                    warnings=["NO_FURTHER_ACTION_SUPPORTED"],
                ).model_dump(mode="python")
            )
        else:
            capability_unavailable = not generated.tasks
            results.append(
                AgentResult(
                    task_id=f"PLAN-{run.run_id}",
                    status=(
                        AgentTaskStatus.INSUFFICIENT_EVIDENCE
                        if capability_unavailable
                        else AgentTaskStatus.FAILED
                    ),
                    summary=('Yêu cầu nằm ngoài các khả năng hiện được cung cấp cho dự án. Hệ thống chưa thực hiện hành động nào.' if capability_unavailable else 'Kế hoạch tạo ra không vượt qua kiểm tra khả năng, bằng chứng hoặc quyền. Hệ thống chưa thực hiện hành động nào.'),
                    evidence_refs=evidence_refs,
                    reason_codes=[
                        "CAPABILITY_NOT_AVAILABLE"
                        if capability_unavailable
                        else "PLAN_VALIDATION_FAILED"
                    ],
                    warnings=[
                        "NO_SUPPORTED_CAPABILITY"
                        if capability_unavailable
                        else "PLAN_VALIDATION_FAILED"
                    ],
                ).model_dump(mode="python")
            )
    run.execution_plan.extend(task.model_dump(mode="json") for task in tasks)
    run.status = AIRunExecutionStatus.RUNNING
    if not run.completed_tasks:
        run.current_step = 1
    return {
        "run": run.model_dump(mode="python"),
        "tasks": [task.model_dump(mode="python") for task in tasks],
        "success_criteria": list(
            dict.fromkeys([*state.get("success_criteria", []), *generated.success_criteria])
        ),
        "results": results,
    }


async def execute_agent(state):
    run = state_run(state)
    tasks = [AgentTask(**item) for item in state.get("tasks", [])]
    if not tasks:
        return {}
    completed_task_ids = {item.get("task_id") for item in run.completed_tasks}
    task = next((item for item in tasks if item.task_id not in completed_task_ids), None)
    if not task:
        return {}
    run.active_task = task.model_dump(mode="json")
    simulation = bool((state.get("constraints") or {}).get("change_simulation"))
    if simulation and any(
        (access := tool_access(registered_tools().get(call.tool_name))) is None
        or access.action != "READ"
        for call in task.tool_calls
    ):
        result = AgentResult(
            task_id=task.task_id,
            status=AgentTaskStatus.FAILED,
            summary='Mô phỏng thay đổi chỉ đọc bằng chứng và không thực hiện thao tác ghi.',
            evidence_refs=list(task.evidence_refs),
            reason_codes=["CHANGE_SIMULATION_MUTATION_BLOCKED"],
        )
        run.completed_tasks.append(task.model_dump(mode="json"))
        run.agent_results.append(result.model_dump(mode="json"))
        run.observations.append(
            {
                "tool_name": "change_simulation_guard",
                "status": ToolExecutionStatus.DENIED,
                "reason_code": "CHANGE_SIMULATION_MUTATION_BLOCKED",
            }
        )
        run.active_task = None
        return {
            "run": run.model_dump(mode="python"),
            "results": [*state.get("results", []), result.model_dump(mode="python")],
        }
    evidence_by_ref = evidence_for_references(
        state.get("evidence", []), task.evidence_refs
    )
    task_evidence = [
        EvidenceItem(**item) for item in evidence_by_ref
    ]
    if not task_evidence:
        task_evidence = [EvidenceItem(**item) for item in state.get("evidence", [])]
    task_has_mutation = False
    for call in task.tool_calls:
        access = tool_access(registered_tools().get(call.tool_name))
        if access and access.action == "MUTATE":
            task_has_mutation = True
            break

    async def checkpoint_action(tool_name, index, action, arguments):
        checkpoint_state = {
            **state,
            "run": run.model_dump(mode="python"),
            "completed_phase": AIRunPhase.ACTION_STARTED,
        }
        snapshot = {
            key: value
            for key, value in checkpoint_state.items()
            if key in AIRunStateSnapshot.model_fields
            and key != "completed_phase"
        }
        snapshot["completed_phase"] = AIRunPhase.ACTION_STARTED
        checkpoint_saved = await ai_run_repository.save_checkpoint(
            AIRunCheckpoint(
                ai_run_id=run.run_id,
                phase=AIRunPhase.ACTION_STARTED,
                status=AIRunExecutionStatus.RUNNING,
                detail={
                    "task_id": task.task_id,
                    "tool_name": tool_name,
                    "tool_index": index,
                    "action": action,
                    "task_has_mutation": task_has_mutation,
                    "arguments_sha256": hashlib.sha256(
                        json.dumps(arguments, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest(),
                },
                state_snapshot=AIRunStateSnapshot.model_validate(snapshot),
            ),
            expected_worker_revision=state.get("worker_revision"),
        )
        if not checkpoint_saved:
            raise RuntimeError("AI_RUN_WORKER_FENCE_LOST")

    tool_call_batch_id = uuid4().hex
    result, observations = await execute_task(
        task,
        task_evidence,
        run.permissions,
        state["token"],
        ai_run_id=run.run_id,
        automatic=bool(state.get("automatic")),
        checkpoint_action=checkpoint_action if state.get("automatic") else None,
        request_constraints=state.get("constraints"),
    )
    for tool_call_index, (call, observation) in enumerate(
        zip(task.tool_calls, observations)
    ):
        observation["task_id"] = task.task_id
        observation["tool_call_index"] = tool_call_index
        observation["tool_call_batch_id"] = tool_call_batch_id
        if (task.constraints or {}).get("change_simulation"):
            observation["change_simulation_stage"] = (task.constraints or {}).get(
                "change_simulation_stage"
            )
        if call.tool_name == "get_test_case_version_by_id":
            observation["source_version_id"] = str(
                (call.arguments or {}).get("version_id") or ""
            )
    if (
        (task.constraints or {}).get("continue_after_observation") is True
        and task.tool_calls
        and len(observations) == len(task.tool_calls)
        and all(item.get("status") == ToolExecutionStatus.COMPLETED for item in observations)
        and all(
            (access := tool_access(registered_tools().get(call.tool_name))) is not None
            and access.action != "MUTATE"
            for call in task.tool_calls
        )
    ):
        result.status = AgentTaskStatus.COMPLETED
        result.summary = 'Đã rà soát nguồn; tiếp tục xử lý với các bằng chứng liên quan.'
        result.reason_codes = []
        result.warnings = []
        if (
            (state.get("constraints") or {}).get("change_simulation")
            and (task.constraints or {}).get("change_simulation_stage") == "DISCOVERY"
        ):
            simulation = (state.get("constraints") or {}).get("change_simulation_input") or {}
            baseline_version_id = str(simulation.get("base_requirement_version_id") or "")
            if not simulation_linked_test_case_version_ids(observations, baseline_version_id):
                result.summary = 'Đã đọc Requirement baseline và liên kết truy vết nhưng chưa có phiên bản Test Case liên kết để đối chiếu.'
    for observation_index, observation in enumerate(observations):
        if observation.get("status") != ToolExecutionStatus.COMPLETED:
            continue
        observation["evidence_ref"] = tool_evidence_reference(
            task.task_id,
            tool_call_batch_id,
            observation.get("tool_call_index", observation_index),
            observation.get("tool_name"),
        )
    tool_evidence = []
    tool_output_rejected = False
    for observation in observations:
        if observation.get("status") != ToolExecutionStatus.COMPLETED:
            continue
        tool_name = str(observation.get("tool_name") or "")
        access = tool_access(registered_tools().get(tool_name))
        if not access:
            continue
        if access.action == "MUTATE" and (
            observation.get("verification") or {}
        ).get("status") != ToolExecutionStatus.COMPLETED:
            continue
        evidence_ref = observation.get("evidence_ref")
        if not evidence_ref:
            continue
        observed_text = json.dumps(
            {"tool_name": tool_name, "result": observation.get("result")},
            ensure_ascii=False,
            default=str,
        )
        try:
            inspection = await guardrails_engine.async_inspect_tool_output(observed_text)
        except Exception:
            tool_output_rejected = True
            observation["output_security"] = {
                "status": "UNAVAILABLE",
                "reason_code": "TOOL_OUTPUT_INSPECTION_FAILED",
            }
            observation.pop("result", None)
            continue
        if not inspection.get("is_safe", False):
            tool_output_rejected = True
            observation["output_security"] = {
                "status": "REJECTED",
                "reason_code": str(inspection.get("threat_category") or "UNSAFE_TOOL_OUTPUT"),
            }
            observation.pop("result", None)
            continue
        tool_evidence.append(
            EvidenceItem(
                artifact_type="tool_result",
                artifact_id=str(evidence_ref),
                source="tool",
                authority=f"verified_tool:{tool_name}",
                text=inspection.get("sanitized_text") or observed_text,
                project_id=run.project_id,
            ).model_dump(mode="python")
        )
    verified_tool_refs = [item["artifact_id"] for item in tool_evidence]
    if verified_tool_refs:
        run.evidence_refs = list(dict.fromkeys([*run.evidence_refs, *verified_tool_refs]))
    if tool_output_rejected:
        result.status = AgentTaskStatus.INSUFFICIENT_EVIDENCE
        result.summary = 'Kết quả công cụ không vượt qua kiểm tra an toàn nên không được dùng làm căn cứ.'
        result.evidence_refs = list(verified_tool_refs)
        result.reason_codes = list(
            dict.fromkeys([*result.reason_codes, "TOOL_OUTPUT_REJECTED"])
        )
        result.warnings = list(
            dict.fromkeys([*result.warnings, "TOOL_OUTPUT_REJECTED"])
        )
    allowed_evidence_refs = {
        str(item.artifact_version_id or item.artifact_id)
        for item in task_evidence
        if item.artifact_version_id or item.artifact_id
    } | set(verified_tool_refs)
    result.evidence_refs = list(
        dict.fromkeys(
            reference
            for reference in [*result.evidence_refs, *verified_tool_refs]
            if reference in allowed_evidence_refs
        )
    )
    run.completed_tasks.append(task.model_dump(mode="json"))
    run.agent_results.append(result.model_dump(mode="json"))
    run.observations.extend(observations)
    run.tool_calls.extend(verified_tool_call_records(task, observations))
    run.active_task = None
    run.current_step += 1
    return {
        "run": run.model_dump(mode="python"),
        "evidence": [*state.get("evidence", []), *tool_evidence],
        "degraded_flags": list(
            dict.fromkeys(
                [
                    *state.get("degraded_flags", []),
                    *(["TOOL_OUTPUT_REJECTED"] if tool_output_rejected else []),
                ]
            )
        ),
        "results": [*state.get("results", []), result.model_dump(mode="python")],
    }


def route_after_agent(state):
    run = state_run(state)
    if run.agent_results and run.agent_results[-1].get("status") != AgentTaskStatus.COMPLETED:
        return "finalize"
    task_ids = {item.get("task_id") for item in state.get("tasks", [])}
    completed_task_ids = {item.get("task_id") for item in run.completed_tasks}
    if task_ids.difference(completed_task_ids):
        return "execute"
    latest_completed_task = run.completed_tasks[-1] if run.completed_tasks else {}
    if (
        (state.get("constraints") or {}).get("change_simulation")
        and (latest_completed_task.get("constraints") or {}).get("change_simulation_stage") == "DISCOVERY"
    ):
        return "replan"
    if (
        (state.get("constraints") or {}).get("change_simulation")
        and (latest_completed_task.get("constraints") or {}).get("change_simulation_stage")
        == "LINKED_TEST_CASES"
        and (latest_completed_task.get("constraints") or {}).get("workflow_terminal") is not True
    ):
        return "replan"
    if (latest_completed_task.get("constraints") or {}).get("workflow_terminal") is True:
        return "finalize"
    if (
        state.get("automatic")
        and len(run.completed_tasks) < limits.agent_steps
        and state.get("planning_round", 0) < limits.agent_steps
    ):
        return "replan"
    return "finalize"


async def finalize(state):
    run = state_run(state)
    results = [AgentResult(**item) for item in state.get("results", [])]
    reason_codes = list(
        dict.fromkeys(code for item in results for code in item.reason_codes)
    )
    run.observations.append(
        {
            "phase": "FINALIZE",
            "goal_complete": bool(results)
            and all(item.status == AgentTaskStatus.COMPLETED for item in results),
            "reason_codes": reason_codes,
            "new_task_count": 0,
        }
    )
    return {
        "run": run.model_dump(mode="python"),
        "success_criteria": state.get("success_criteria", []),
    }


async def aggregate(state):
    run = state_run(state)
    results = [AgentResult(**item) for item in state.get("results", [])]
    summary = " ".join(item.summary for item in results)
    answer_task_ids = {
        str(item.get("task_id") or "")
        for item in run.observations
        if item.get("tool_name") == "project_question"
        and item.get("status") == ToolExecutionStatus.COMPLETED
        and item.get("task_id")
    }
    if answer_task_ids:
        read_task_ids = {
            str(item.get("task_id") or "")
            for item in run.observations
            if item.get("task_id")
            and (access := tool_access(registered_tools().get(item.get("tool_name"))))
            and access.action == "READ"
        }
        selected_results = [
            item
            for item in results
            if item.task_id in answer_task_ids
            or (
                item.task_id not in read_task_ids
                and not item.task_id.startswith("PLAN-")
            )
            or item.status != AgentTaskStatus.COMPLETED
            or item.reason_codes
            or item.proposals
        ]
        selected_summaries = [
            item.summary for item in selected_results if item.summary.strip()
        ]
        if selected_summaries:
            summary = " ".join(selected_summaries)
    warnings = list(
        dict.fromkeys(
            [
                *(warning for item in results for warning in item.warnings),
                *state.get("degraded_flags", []),
            ]
        )
    )
    trigger = str((state.get("constraints") or {}).get("trigger") or "")
    if trigger == "TEST_CASE_CHANGED":
        tool_results = {
            observation.get("tool_name"): observation.get("result") or {}
            for observation in run.observations
            if observation.get("status") == ToolExecutionStatus.COMPLETED
            and observation.get("tool_name")
        }
        impact = tool_results.get("impact_analysis", {})
        if impact:
            warnings.extend(impact.get("warnings") or [])
        change_context = test_case_change_context(run, state.get("evidence", []))
        if change_context["event_kind"] == "TEST_CASE_CREATED":
            warnings.append("TEST_CASE_CREATED_WITHOUT_CHANGE_BASELINE")
        elif not change_context["has_comparison"]:
            warnings.append("TEST_CASE_CHANGE_BASELINE_UNAVAILABLE")
        elif not change_context["has_source_link"]:
            warnings.append("TEST_CASE_CHANGE_SOURCE_LINK_UNAVAILABLE")
        impact_observations = [
            item for item in run.observations
            if item.get("status") == ToolExecutionStatus.COMPLETED
        ]
        parent_reads = [
            item.get("result") or {}
            for item in impact_observations
            if item.get("tool_name") == "get_test_case_version_by_id"
        ]
        trace_result = next(
            (
                item.get("result") or {}
                for item in impact_observations
                if item.get("tool_name") == "get_traceability_links"
            ),
            None,
        )
        current_draft = change_context.get("current_draft") or {}
        if parent_reads or trace_result is not None:
            linked_version_ids = {
                str(item.get("_id") or item.get("version_id") or "")
                for item in parent_reads
                if isinstance(item, dict)
            }
            parent_version_id = str(current_draft.get("parent_version_id") or "")
            if parent_version_id and parent_version_id not in linked_version_ids:
                warnings.append("TEST_CASE_PARENT_VERSION_READBACK_UNAVAILABLE")
            if trace_result is None:
                warnings.append("TEST_CASE_TRACE_IMPACT_READBACK_UNAVAILABLE")
    if trigger == "WORK_ITEM_CHANGED":
        context = next(
            (
                observation.get("result")
                for observation in run.observations
                if observation.get("tool_name") == "get_work_item_impact_context"
                and observation.get("status") == ToolExecutionStatus.COMPLETED
            ),
            None,
        )
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except (TypeError, ValueError):
                context = None
        if isinstance(context, dict) and context.get("status") != "completed":
            warnings.append("WORK_ITEM_IMPACT_CONTEXT_UNAVAILABLE")
    if trigger == "RELEASE_CHANGED":
        release_result = next(
            (
                observation.get("result")
                for observation in run.observations
                if observation.get("tool_name") == "process_changed_release"
                and observation.get("status") == ToolExecutionStatus.COMPLETED
            ),
            None,
        )
        if isinstance(release_result, str):
            try:
                release_result = json.loads(release_result)
            except (TypeError, ValueError):
                release_result = None
        if isinstance(release_result, dict) and release_result.get("status") != "completed":
            warnings.append(
                str(release_result.get("reason_code") or "RELEASE_PROCESSING_INCOMPLETE")
            )
    coverage = next(
        (
            observation.get("result") or {}
            for observation in run.observations
            if observation.get("tool_name") == "calculate_coverage"
            and observation.get("status") == ToolExecutionStatus.COMPLETED
        ),
        None,
    )
    if coverage is not None:
        warnings.append("COVERAGE_METRICS_ARE_SCOPE_SNAPSHOT_NOT_QUALITY_CLAIMS")
    change_simulation_report = None
    if (state.get("constraints") or {}).get("change_simulation"):
        simulation_input = (state.get("constraints") or {}).get("change_simulation_input") or {}
        baseline_version_id = str(simulation_input.get("base_requirement_version_id") or "")
        trace_links = simulation_baseline_trace_links(
            run.observations, baseline_version_id, stage="DISCOVERY"
        )
        discovery_scope = simulation_baseline_trace_snapshot(
            run.observations, baseline_version_id, "DISCOVERY"
        )
        revalidated_scope = simulation_baseline_trace_snapshot(
            run.observations, baseline_version_id, "SCOPE_REVALIDATION"
        )
        scope_unchanged = simulation_trace_scope_is_current(
            discovery_scope, revalidated_scope, revalidated_scope is not None
        )
        suggested_count = sum(link.get("status") == "SUGGESTED" for link in trace_links)
        observed_version_ids = {
            str(item.get("source_version_id"))
            for item in run.observations
            if item.get("tool_name") == "get_test_case_version_by_id"
            and item.get("status") == ToolExecutionStatus.COMPLETED
            and item.get("result") is not None
            and item.get("source_version_id")
            and isinstance(item.get("result"), dict)
            and str(item["result"].get("_id") or "") == str(item["source_version_id"])
        }
        linked_version_ids = simulation_linked_test_case_version_ids(
            run.observations,
            baseline_version_id,
        )
        omitted_count = len(set(linked_version_ids) - observed_version_ids)
        if omitted_count:
            warnings.append("SIMULATION_LINKED_TEST_CASE_READ_LIMIT_REACHED")
        if suggested_count:
            warnings.append("SUGGESTED_TRACE_LINKS_NOT_CONFIRMED")
        if not scope_unchanged:
            warnings.append("CHANGE_SIMULATION_SCOPE_CHANGED_OR_NOT_REVALIDATED")
        read_version_ids = observed_version_ids
        read_scope_incomplete = omitted_count > 0 or set(linked_version_ids) != read_version_ids.intersection(linked_version_ids)
        if read_scope_incomplete:
            warnings.append("CHANGE_SIMULATION_CLASSIFICATION_SCOPE_INCOMPLETE")
        if read_scope_incomplete or not scope_unchanged:
            if not scope_unchanged:
                warnings.append("CHANGE_SIMULATION_CLASSIFICATION_SKIPPED_STALE_SCOPE")
            unresolved_reasons = []
            if read_scope_incomplete:
                unresolved_reasons.append(
                    'Chưa đọc đủ phiên bản Test Case được liên kết nên không phân loại các mục chưa đọc.'
                )
            if not scope_unchanged:
                unresolved_reasons.append(
                    'Phạm vi truy vết đã thay đổi hoặc chưa được xác minh lại; cần chạy mô phỏng mới trước khi sử dụng kết quả phân loại.'
                )
            change_simulation_report = {
                "capability": "change_simulation_report",
                "baseline_requirement_version_id": baseline_version_id,
                "classifications": [],
                "unresolved": unresolved_reasons,
                "warnings": list(dict.fromkeys([
                    *(["CHANGE_SIMULATION_CLASSIFICATION_SCOPE_INCOMPLETE"] if read_scope_incomplete else []),
                    *(["CHANGE_SIMULATION_SCOPE_CHANGED_OR_NOT_REVALIDATED"] if not scope_unchanged else []),
                ])),
                "verified": False,
            }
        else:
            try:
                simulation = state.get("constraints", {}).get("change_simulation_input") or {}
                proposed_text = str(simulation.get("proposed_source_text") or "")
                source_payload = simulation_source_payload(
                    run.observations,
                    state.get("evidence", []),
                    baseline_version_id,
                    proposed_text,
                )
                if linked_version_ids:
                    source_versions = {
                        item["test_case_version_id"]: item
                        for item in source_payload["linked_test_case_versions"]
                    }
                    classifications = []
                    unresolved = []
                    simulation_warnings = []
                    for version_batch in change_simulation_batches(
                        linked_version_ids, limits.tool_calls_per_task
                    ):
                        batch_ids = set(version_batch)
                        batch_sources = [
                            source_versions[version_id]
                            for version_id in version_batch
                            if version_id in source_versions
                        ]
                        if len(batch_sources) != len(version_batch):
                            raise ValueError("change_simulation_batch_source_missing")
                        generated_batch = await structured(
                            change_simulation_report_instruction(
                                baseline_version_id,
                                source_payload["baseline"],
                                proposed_text,
                                batch_sources,
                                (state.get("constraints") or {}).get("output_language"),
                            ),
                            ChangeSimulationReportOutput,
                            max_tokens=min(5000, 800 + 900 * len(version_batch)),
                        )
                        validated_batch = validate_change_simulation_report(
                            generated_batch,
                            baseline_version_id,
                            proposed_text,
                            version_batch,
                            run.observations,
                            state.get("evidence", []),
                        )
                        if any(
                            item["test_case_version_id"] not in batch_ids
                            for item in validated_batch["classifications"]
                        ):
                            raise ValueError("change_simulation_batch_scope_mismatch")
                        classifications.extend(validated_batch["classifications"])
                        unresolved.extend(validated_batch["unresolved"])
                        simulation_warnings.extend(validated_batch["warnings"])
                    generated = ChangeSimulationReportOutput(
                        baseline_requirement_version_id=baseline_version_id,
                        classifications=classifications,
                        unresolved=list(dict.fromkeys(unresolved)),
                        warnings=list(dict.fromkeys(simulation_warnings)),
                    )
                else:
                    generated = ChangeSimulationReportOutput(
                        baseline_requirement_version_id=baseline_version_id,
                        classifications=[],
                        warnings=[],
                    )
                change_simulation_report = validate_change_simulation_report(
                    generated,
                    baseline_version_id,
                    proposed_text,
                    linked_version_ids,
                    run.observations,
                    state.get("evidence", []),
                )
                if linked_version_ids:
                    warnings.append("CHANGE_SIMULATION_CLASSIFIED_LINKED_TEST_CASES")
                else:
                    warnings.append("CHANGE_SIMULATION_NO_CONFIRMED_LINKED_TEST_CASES")
                if change_simulation_report["unresolved"]:
                    warnings.append("CHANGE_SIMULATION_HAS_UNRESOLVED_EVIDENCE_GAPS")
                warnings.extend(change_simulation_report["warnings"])
                change_simulation_report["verified"] = scope_unchanged
            except Exception as error:
                warnings.append("CHANGE_SIMULATION_REPORT_VALIDATION_FAILED")
                run.observations.append(
                    {
                        "phase": "CHANGE_SIMULATION_CLASSIFICATION",
                        "status": "FAILED",
                        "reason_code": str(error)[:200] or "report_generation_failed",
                    }
                )
    proposal = AgentProposal(
        summary=summary,
        evidence_refs=list(
            dict.fromkeys(reference for item in results for reference in item.evidence_refs)
        ),
        actions=[action for item in results for action in item.proposals],
        warnings=warnings,
        success_criteria_met=state.get("success_criteria", [])
        if all(item.status == AgentTaskStatus.COMPLETED for item in results)
        else [],
        change_simulation_report=change_simulation_report,
    )
    proposal.summary = normalize_narrative(proposal.summary)
    proposal.warnings = normalize_narratives(proposal.warnings)
    proposal.evidence_refs = [
        reference for reference in proposal.evidence_refs if reference in run.evidence_refs
    ]
    if not proposal.evidence_refs:
        proposal.evidence_refs = list(run.evidence_refs)
    run.proposal = proposal.model_dump(mode="json")
    run.evidence_refs = list(dict.fromkeys([*run.evidence_refs, *proposal.evidence_refs]))
    run.status = AIRunExecutionStatus.VERIFYING
    run.current_step += 1
    return {"run": run.model_dump(mode="python")}


def route_after_aggregate(state):
    return "verify"


async def verify(state):
    run = state_run(state)
    results = [AgentResult(**item) for item in state.get("results", [])]
    result_ok = bool(results) and all(
        item.status == AgentTaskStatus.COMPLETED for item in results
    )
    completed_claims = any(item.status == AgentTaskStatus.COMPLETED for item in results)
    proposal_refs = set((run.proposal or {}).get("evidence_refs", []))
    result_refs = {
        reference
        for item in results
        for reference in item.evidence_refs
    }
    claims_grounded = all(
        item.status != AgentTaskStatus.COMPLETED
        or bool(item.evidence_refs)
        and set(item.evidence_refs).issubset(set(run.evidence_refs))
        for item in results
    )
    evidence_ok = (
        (not completed_claims or bool(run.evidence_refs))
        and proposal_refs.issubset(set(run.evidence_refs))
        and result_refs.issubset(set(run.evidence_refs))
        and claims_grounded
    )
    simulation_required = bool((state.get("constraints") or {}).get("change_simulation"))
    simulation_report = (run.proposal or {}).get("change_simulation_report") or {}
    simulation_report_ok = not simulation_required or simulation_report.get("verified") is True
    project_scope_ok = all(
        item.get("project_id") == run.project_id for item in run.completed_tasks
    )
    verified = result_ok and evidence_ok and project_scope_ok and simulation_report_ok
    verification = {
        "verified": verified,
        "project_id": run.project_id,
        "evidence_refs_resolved": evidence_ok,
        "completed_claims_grounded": claims_grounded,
        "project_scope_valid": project_scope_ok,
        "change_simulation_report_valid": simulation_report_ok,
    }
    run.proposal = {**(run.proposal or {}), "verification": verification}
    reason_codes = {
        code for item in results for code in [*item.reason_codes, *item.warnings]
    }
    if "AI_PROVIDER_UNAVAILABLE" in reason_codes:
        run.status = AIRunExecutionStatus.FAILED
        run.error_code = "AI_PROVIDER_UNAVAILABLE"
    elif {"CLARIFICATION_REQUIRED", "USER_DECISION_REQUIRED"} & reason_codes:
        run.status = AIRunExecutionStatus.FAILED
        run.error_code = "AI_RUN_WAITING_FOR_INPUT"
    elif verified:
        run.status = AIRunExecutionStatus.COMPLETED
        run.error_code = None
    else:
        run.status = AIRunExecutionStatus.FAILED
        run.error_code = (
            "CHANGE_SIMULATION_REPORT_INCOMPLETE"
            if simulation_required and not simulation_report_ok
            else "VALIDATION_FAILED"
            if "VALIDATION_FAILED" in reason_codes
            else "INSUFFICIENT_EVIDENCE"
            if any(item.status == AgentTaskStatus.INSUFFICIENT_EVIDENCE for item in results)
            else "VERIFICATION_FAILED"
        )
    run.current_step += 1
    return {"run": run.model_dump(mode="python")}
