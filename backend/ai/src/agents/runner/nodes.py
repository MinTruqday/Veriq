import hashlib
import json
from datetime import datetime, timezone

from src.agents.agent import execute_task
from src.knowledge.evidence import package
from src.knowledge.hybrid import hybrid_evidence
from src.prompts.agent_planning import agent_plan_prompt
from src.runtime.limits import limits
from src.schemas.agent import (
    AgentResult,
    AgentRunStatus,
    AgentTaskStatus,
    AgentTask,
    PlannedTask,
    EvidenceItem,
    AgentPlan,
    AgentProposal,
    ToolExecutionStatus,
    ToolCall,
    VeriqRunState,
)
from src.runtime.output import normalize_narrative, normalize_narratives
from src.services.inference import structured
from src.tools.registry import (
    audit_arguments,
    registered_tools,
    tool_access,
    verify_application,
)
from src.tools.mcp_gateway import discover_project_tools
from src.repositories.automation import automation_repository
from src.schemas.automation import (
    AutomationCheckpoint,
    AutomationCheckpointPhase,
    AutomationGraphSnapshot,
    AutomationStatus,
)


from src.agents.runner.automation_planning import (
    available_tools,
    bounded_tasks,
    direct_approved_plan_task,
    direct_capability_task,
    direct_changed_plan_task,
    direct_defect_event_task,
    direct_document_ingestion_task,
    direct_event_observation_task,
    direct_recorded_test_execution_task,
    direct_requirement_change_task,
    mutation_fingerprint,
    observed_identifiers,
    proposal_fingerprint,
    validated_tasks,
    verified_tool_call_records,
)


def state_run(state):
    return VeriqRunState(**state["run"])


async def load_context(state):
    run = state_run(state)
    supplied = [EvidenceItem(**item) for item in state.get("evidence", [])]
    event_scope = state.get("source_event_verified") is True
    supplied = [item for item in supplied if item.project_id == run.project_id]
    if event_scope:
        # A verified business event already carries its authoritative source. Broad
        # project retrieval here mixes unrelated artifacts into the event's audit
        # receipt; later planning can request related evidence explicitly.
        evidence_items = supplied
        degraded_flags = []
    else:
        retrieved = await hybrid_evidence(
            run.project_id,
            run.objective,
            run.user_id,
            state.get("token"),
            automation_run_id=run.run_id if state.get("automatic") else None,
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


def route_after_context(state):
    return "plan"


async def plan(state):
    run = state_run(state)
    simulation = bool((state.get("constraints") or {}).get("change_simulation"))
    evidence_refs = [
        item.get("artifact_version_id") or item.get("artifact_id")
        for item in state.get("evidence", [])
    ]
    direct_task = None
    if not simulation:
        direct_task = direct_document_ingestion_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = direct_requirement_change_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = direct_recorded_test_execution_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = direct_defect_event_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = direct_approved_plan_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = direct_changed_plan_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = direct_event_observation_task(run, state, evidence_refs)
    if not simulation and not direct_task:
        direct_task = (
            direct_capability_task(run, evidence_refs)
            if run.intent and not run.completed_tasks
            else None
        )
    if direct_task:
        run.execution_plan = [direct_task.model_dump(mode="json")]
        run.status = AgentRunStatus.RUNNING
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
            "source_start": item.get("source_start"),
            "source_end": item.get("source_end"),
        }
        for item in state.get("source_facts", [])
        if item.get("quote")
        and (item.get("artifact_version_id") or item.get("artifact_id")) in evidence_refs
    ]
    prompt = agent_plan_prompt(
        run.project_id,
        run.run_id,
        run.objective,
        run.intent,
        state.get("target_artifact_ids", []),
        available_tools(
            run.permissions,
            run.intent
            if not simulation and (not state.get("automatic") or not run.completed_tasks)
            else "",
            compact=True,
            actions={"READ"} if simulation else None,
        ),
        evidence_refs,
        {
            **state.get("constraints", {}),
            "verified_source_facts": verified_source_facts,
            "source_fact_use": (
                "Build the plan and downstream artifact proposals from these exact verified quotes. "
                "Every generated requirement, test obligation, or test case must retain the source "
                "artifact/version reference. Do not generate an artifact from an uncited fact."
            ),
            "change_simulation": simulation,
            "simulation_rule": (
                "This is a non-mutating change simulation. Read current evidence and produce an "
                "impact plan only. Do not call any create, update, approve, execute, or delete tool."
                if simulation
                else None
            ),
            "execution_mode": "AUTOMATIC_WITHIN_EXECUTION_PRINCIPAL_PERMISSIONS"
            if state.get("automatic")
            else "INTERACTIVE_AGENT",
            "completed_tool_calls": run.tool_calls,
            "recent_tool_observations": run.observations[-limits.agent_steps :],
            "mcp_read_tools": await discover_project_tools(run.project_id, run.permissions),
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
        run.status = AgentRunStatus.RUNNING
        if not run.completed_tasks:
            run.current_step = 1
        run.observations.append(
            {"phase": "PLAN", "reason_code": "AI_PROVIDER_UNAVAILABLE"}
        )
        result = AgentResult(
            task_id=f"PLAN-{run.run_id}",
            status=AgentTaskStatus.INSUFFICIENT_EVIDENCE,
            summary="The AI provider is unavailable so a plan cannot be created",
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
    tasks = validated_tasks(
        generated.tasks,
        run,
        evidence_refs,
        known_identifiers=allowed_identifiers,
    )
    tasks = [task for task in tasks if task.tool_calls]
    results = list(state.get("results", []))
    if not tasks:
        prior_results = [AgentResult(**item) for item in results]
        observed_automatic_event = (
            bool(state.get("automatic"))
            and bool(run.completed_tasks)
            and bool(prior_results)
            and all(item.status == AgentTaskStatus.COMPLETED for item in prior_results)
        )
        if observed_automatic_event:
            results.append(
                AgentResult(
                    task_id=f"PLAN-{run.run_id}",
                    status=AgentTaskStatus.COMPLETED,
                    summary="Đã hoàn tất các hành động có căn cứ; không còn hành động tiếp theo hợp lệ trong phạm vi quyền hiện tại",
                    evidence_refs=evidence_refs,
                    warnings=["NO_FURTHER_ACTION_SUPPORTED"],
                ).model_dump(mode="python")
            )
        else:
            results.append(
                AgentResult(
                    task_id=f"PLAN-{run.run_id}",
                    status=AgentTaskStatus.FAILED,
                    summary="The plan contains no valid task",
                    evidence_refs=evidence_refs,
                    reason_codes=["VALIDATION_FAILED"],
                    warnings=["NO_VALID_AUTOMATION_ACTION"],
                ).model_dump(mode="python")
            )
    run.execution_plan.extend(task.model_dump(mode="json") for task in tasks)
    run.status = AgentRunStatus.RUNNING
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
            summary="Mô phỏng thay đổi chỉ cho phép đọc bằng chứng, không thực hiện thao tác ghi",
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
    evidence_by_ref = {
        item.get("artifact_version_id") or item.get("artifact_id"): item
        for item in state.get("evidence", [])
    }
    task_evidence = [
        EvidenceItem(**evidence_by_ref[reference])
        for reference in task.evidence_refs
        if reference in evidence_by_ref
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
            "completed_phase": AutomationCheckpointPhase.ACTION_STARTED,
        }
        snapshot = {
            key: value
            for key, value in checkpoint_state.items()
            if key in AutomationGraphSnapshot.model_fields
            and key != "completed_phase"
        }
        snapshot["completed_phase"] = AutomationCheckpointPhase.ACTION_STARTED
        await automation_repository.save_checkpoint(
            AutomationCheckpoint(
                automation_run_id=run.run_id,
                phase=AutomationCheckpointPhase.ACTION_STARTED,
                status=AutomationStatus.RUNNING,
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
                state_snapshot=AutomationGraphSnapshot.model_validate(snapshot),
            )
        )

    result, observations = await execute_task(
        task,
        task_evidence,
        run.permissions,
        state["token"],
        automation_run_id=run.run_id,
        automatic=bool(state.get("automatic")),
        checkpoint_action=checkpoint_action if state.get("automatic") else None,
    )
    tool_evidence_refs = []
    for observation in observations:
        if observation.get("status") != ToolExecutionStatus.COMPLETED:
            continue
        evidence_ref = f"{task.task_id}:{observation.get('tool_name', 'tool')}"
        observation["evidence_ref"] = evidence_ref
        tool_evidence_refs.append(evidence_ref)
    if tool_evidence_refs:
        run.evidence_refs = list(dict.fromkeys([*run.evidence_refs, *tool_evidence_refs]))
        result.evidence_refs = list(
            dict.fromkeys([*result.evidence_refs, *tool_evidence_refs])
        )
    run.completed_tasks.append(task.model_dump(mode="json"))
    run.agent_results.append(result.model_dump(mode="json"))
    run.observations.extend(observations)
    run.tool_calls.extend(verified_tool_call_records(task, observations))
    run.active_task = None
    run.current_step += 1
    return {
        "run": run.model_dump(mode="python"),
        "results": [*state.get("results", []), result.model_dump(mode="python")],
    }


def route_after_agent(state):
    run = state_run(state)
    task_ids = {item.get("task_id") for item in state.get("tasks", [])}
    completed_task_ids = {item.get("task_id") for item in run.completed_tasks}
    if task_ids.difference(completed_task_ids):
        return "execute"
    run = state_run(state)
    if run.agent_results and run.agent_results[-1].get("status") != AgentTaskStatus.COMPLETED:
        return "finalize"
    latest_completed_task = run.completed_tasks[-1] if run.completed_tasks else {}
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


def route_after_finalize(state):
    return "aggregate"


async def aggregate(state):
    run = state_run(state)
    results = [AgentResult(**item) for item in state.get("results", [])]
    proposal = AgentProposal(
        summary=" ".join(item.summary for item in results),
        evidence_refs=list(
            dict.fromkeys(reference for item in results for reference in item.evidence_refs)
        ),
        actions=[action for item in results for action in item.proposals],
        warnings=list(
            dict.fromkeys(
                [
                    *(warning for item in results for warning in item.warnings),
                    *state.get("degraded_flags", []),
                ]
            )
        ),
        success_criteria_met=state.get("success_criteria", [])
        if all(item.status == AgentTaskStatus.COMPLETED for item in results)
        else [],
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
    run.status = AgentRunStatus.VERIFYING
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
    project_scope_ok = all(
        item.get("project_id") == run.project_id for item in run.completed_tasks
    )
    verified = result_ok and evidence_ok and project_scope_ok
    verification = {
        "verified": verified,
        "project_id": run.project_id,
        "evidence_refs_resolved": evidence_ok,
        "completed_claims_grounded": claims_grounded,
        "project_scope_valid": project_scope_ok,
    }
    run.proposal = {**(run.proposal or {}), "verification": verification}
    reason_codes = {
        code for item in results for code in [*item.reason_codes, *item.warnings]
    }
    if "AI_PROVIDER_UNAVAILABLE" in reason_codes:
        run.status = AgentRunStatus.FAILED
        run.error_code = "AI_PROVIDER_UNAVAILABLE"
    elif verified:
        run.status = AgentRunStatus.COMPLETED
        run.error_code = None
    else:
        run.status = AgentRunStatus.FAILED
        run.error_code = (
            "VALIDATION_FAILED"
            if "VALIDATION_FAILED" in reason_codes
            else "INSUFFICIENT_EVIDENCE"
            if any(item.status == AgentTaskStatus.INSUFFICIENT_EVIDENCE for item in results)
            else "VERIFICATION_FAILED"
        )
    run.current_step += 1
    return {"run": run.model_dump(mode="python")}
