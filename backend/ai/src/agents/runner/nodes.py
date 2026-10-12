from datetime import datetime, timezone

from src.agents.agent import execute_task
from src.knowledge.evidence import package
from src.knowledge.hybrid import hybrid_evidence
from src.prompts.agents import agent_plan_prompt
from src.runtime.limits import limits
from src.schemas.agent import (
    AgentApprovalStatus,
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
    invoke_tool,
    registered_tools,
    tool_access,
    verify_application,
)


def available_tools(permissions, intent="", compact=False):
    values = []
    tools = registered_tools()
    intent_tool_exists = bool(intent and tool_access(tools.get(intent)))
    for tool in tools.values():
        access = tool_access(tool)
        if (
            access
            and access.permission in permissions
            and (not intent_tool_exists or access.name == intent)
        ):
            schema = tool.args_schema.model_json_schema()
            arguments = schema
            if compact:
                arguments = {
                    "required": schema.get("required", []),
                    "properties": sorted(schema.get("properties", {})),
                }
            values.append(
                {
                    "name": access.name,
                    "domains": sorted(access.domains),
                    "action": access.action,
                    "requires_approval": access.requires_approval,
                    "arguments": arguments,
                }
            )
    return values


def direct_capability_task(run, evidence_refs):
    tool = registered_tools().get(run.intent)
    access = tool_access(tool)
    if not access or access.permission not in run.permissions:
        return None
    domain = access.owner_domain
    if domain is None and len(access.domains) == 1:
        domain = next(iter(access.domains))
    if domain is None:
        return None
    properties = tool.args_schema.model_json_schema().get("properties", {})
    arguments = {"instruction": run.objective} if "instruction" in properties else {}
    tasks = validated_tasks(
        [
            PlannedTask(
                domain=domain,
                objective=run.objective,
                evidence_refs=evidence_refs,
                tool_calls=[ToolCall(tool_name=access.name, arguments=arguments)],
            )
        ],
        run,
        evidence_refs,
        known_identifiers=evidence_refs,
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def bounded_tasks(tasks, run):
    first = next(iter(tasks), None)
    return [first] if first else []


def validated_tasks(tasks, run, evidence_refs, maximum=None, known_identifiers=None):
    tool_values = registered_tools()
    validated = []
    task_limit = max(0, 1 - len(run.completed_tasks))
    if maximum is not None:
        task_limit = min(task_limit, maximum)
    for planned in bounded_tasks(tasks, run)[:task_limit]:
        task = planned if isinstance(planned, PlannedTask) else PlannedTask(**planned)
        calls = []
        for call in task.tool_calls[: limits.tool_calls_per_task]:
            tool = tool_values.get(call.tool_name)
            access = tool_access(tool)
            if not access or task.domain not in access.domains:
                continue
            arguments = dict(call.arguments)
            schema = tool.args_schema.model_json_schema()
            properties = schema.get("properties", {})
            if "project_id" in properties:
                arguments["project_id"] = run.project_id
            identifiers = {
                str(value)
                for key, value in arguments.items()
                if key != "project_id" and key.endswith("_id") and value
            }
            if identifiers.difference(set(known_identifiers or evidence_refs)):
                continue
            required = set(schema.get("required", []))
            if required.difference(arguments):
                continue
            try:
                normalized = tool.args_schema.model_validate(arguments).model_dump(
                    mode="python", exclude_unset=True
                )
            except Exception:
                continue
            calls.append(ToolCall(tool_name=call.tool_name, arguments=normalized))
        validated.append(
            AgentTask(
                run_id=run.run_id,
                project_id=run.project_id,
                domain=task.domain,
                objective=task.objective,
                evidence_refs=task.evidence_refs or evidence_refs,
                constraints=task.constraints,
                tool_calls=calls,
            )
        )
    return validated


def state_run(state):
    return VeriqRunState(**state["run"])


async def load_context(state):
    run = state_run(state)
    if run.approval_status in {
        AgentApprovalStatus.APPROVED,
        AgentApprovalStatus.REJECTED,
    } and state.get("tasks"):
        return {}
    supplied = [EvidenceItem(**item) for item in state.get("evidence", [])]
    retrieved = await hybrid_evidence(
        run.project_id,
        run.objective,
        run.user_id,
        state.get("token"),
    )
    verified_refs = {
        item.artifact_version_id or item.artifact_id for item in retrieved.items
    }
    supplied = [
        item
        for item in supplied
        if item.project_id == run.project_id
        and (item.artifact_version_id or item.artifact_id) in verified_refs
    ]
    combined = package(
        run.project_id,
        run.objective,
        [*supplied, *retrieved.items],
        retrieved.degraded_flags,
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
    run = state_run(state)
    if run.approval_status == AgentApprovalStatus.APPROVED and state.get("tasks"):
        return "apply"
    if run.approval_status == AgentApprovalStatus.REJECTED and state.get("tasks"):
        return "finalize"
    return "plan"


async def plan(state):
    run = state_run(state)
    evidence_refs = [
        item.get("artifact_version_id") or item.get("artifact_id")
        for item in state.get("evidence", [])
    ]
    direct_task = direct_capability_task(run, evidence_refs)
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
    prompt = agent_plan_prompt(
        run.project_id,
        run.run_id,
        run.objective,
        run.intent,
        state.get("target_artifact_ids", []),
        available_tools(run.permissions, run.intent, compact=True),
        evidence_refs,
        state.get("constraints", {}),
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
            warnings=["AI_PROVIDER_UNAVAILABLE", "MANUAL_REVIEW_REQUIRED"],
        )
        return {
            "run": run.model_dump(mode="python"),
            "tasks": [],
            "success_criteria": [],
            "results": [result.model_dump(mode="python")],
        }
    allowed_identifiers = list(
        dict.fromkeys(
            [
                *evidence_refs,
                *state.get("target_artifact_ids", []),
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
    results = []
    if not tasks:
        results.append(
            AgentResult(
                task_id=f"PLAN-{run.run_id}",
                status=AgentTaskStatus.FAILED,
                summary="The plan contains no valid task",
                evidence_refs=evidence_refs,
                reason_codes=["VALIDATION_FAILED"],
                warnings=["MANUAL_REVIEW_REQUIRED"],
            ).model_dump(mode="python")
        )
    run.execution_plan = [task.model_dump(mode="json") for task in tasks]
    run.status = AgentRunStatus.RUNNING
    run.current_step = 1
    return {
        "run": run.model_dump(mode="python"),
        "tasks": [task.model_dump(mode="python") for task in tasks],
        "success_criteria": generated.success_criteria,
        "results": results,
    }


async def execute_agent(state):
    run = state_run(state)
    tasks = [AgentTask(**item) for item in state.get("tasks", [])]
    if not tasks:
        return {}
    task = tasks[0]
    run.active_task = task.model_dump(mode="json")
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
    result, observations = await execute_task(
        task,
        task_evidence,
        run.permissions,
        state["token"],
        run.approval_status,
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
    run.tool_calls.extend(
        {
            "task_id": task.task_id,
            "tool_name": item.tool_name,
            "arguments": audit_arguments(item.arguments),
        }
        for item in task.tool_calls
    )
    run.active_task = None
    run.current_step += 1
    return {
        "run": run.model_dump(mode="python"),
        "results": [*state.get("results", []), result.model_dump(mode="python")],
    }


def route_after_agent(state):
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
            "goal_complete": True,
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
        warnings=list(dict.fromkeys(warning for item in results for warning in item.warnings)),
        success_criteria_met=state.get("success_criteria", [])
        if all(item.status == AgentTaskStatus.COMPLETED for item in results)
        else [],
    )
    tasks = {item["task_id"]: AgentTask(**item) for item in state.get("tasks", [])}
    pending_actions = []
    if run.approval_status != AgentApprovalStatus.REJECTED:
        for result in results:
            task = tasks.get(result.task_id)
            if not task:
                continue
            planned_calls = {item.tool_name: item for item in task.tool_calls}
            for action in result.proposals:
                tool_name = action.get("tool_name")
                access = tool_access(registered_tools().get(tool_name))
                planned = planned_calls.get(tool_name)
                if not access or not access.requires_approval or not planned:
                    continue
                pending_actions.append(
                    {
                        "task_id": task.task_id,
                        "tool_name": tool_name,
                        "arguments": planned.arguments,
                    }
                )
    proposal.actions = pending_actions
    proposal.summary = normalize_narrative(proposal.summary)
    proposal.warnings = normalize_narratives(proposal.warnings)
    proposal.evidence_refs = [
        reference for reference in proposal.evidence_refs if reference in run.evidence_refs
    ]
    if not proposal.evidence_refs:
        proposal.evidence_refs = list(run.evidence_refs)
    run.proposal = proposal.model_dump(mode="json")
    run.evidence_refs = list(dict.fromkeys([*run.evidence_refs, *proposal.evidence_refs]))
    run.status = (
        AgentRunStatus.APPROVAL_REQUIRED if pending_actions else AgentRunStatus.VERIFYING
    )
    run.current_step += 1
    return {"run": run.model_dump(mode="python")}


def route_after_aggregate(state):
    return (
        "end"
        if state_run(state).status == AgentRunStatus.APPROVAL_REQUIRED
        else "verify"
    )


async def apply(state):
    run = state_run(state)
    tasks = {item["task_id"]: AgentTask(**item) for item in state.get("tasks", [])}
    applied = []
    run.status = AgentRunStatus.APPLYING
    for action in (run.proposal or {}).get("actions", []):
        task = tasks.get(action.get("task_id"))
        if not task:
            applied.append(
                {"status": ToolExecutionStatus.FAILED, "reason_code": "TASK_NOT_FOUND"}
            )
            continue
        result = await invoke_tool(
            task,
            action.get("tool_name", ""),
            action.get("arguments", {}),
            run.permissions,
            state["token"],
            AgentApprovalStatus.APPROVED,
        )
        if result.get("status") == ToolExecutionStatus.COMPLETED:
            result["verification"] = await verify_application(
                task,
                action.get("tool_name", ""),
                action.get("arguments", {}),
                result,
                state["token"],
            )
        applied.append(result)
    run.proposal = {**(run.proposal or {}), "applied_results": applied}
    run.status = AgentRunStatus.VERIFYING
    run.current_step += 1
    return {"run": run.model_dump(mode="python")}


async def verify(state):
    run = state_run(state)
    results = [AgentResult(**item) for item in state.get("results", [])]
    applied = (run.proposal or {}).get("applied_results", [])
    actions = (run.proposal or {}).get("actions", [])
    rejected = run.approval_status == AgentApprovalStatus.REJECTED
    result_ok = bool(results) and all(
        item.status in {AgentTaskStatus.COMPLETED, AgentTaskStatus.INSUFFICIENT_EVIDENCE}
        for item in results
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
    apply_ok = not applied or all(
        item.get("status") == ToolExecutionStatus.COMPLETED
        and item.get("verification", {}).get("status") == ToolExecutionStatus.COMPLETED
        for item in applied
    )
    apply_count_ok = (
        not actions
        or rejected
        or (run.approval_status == AgentApprovalStatus.APPROVED and len(applied) == len(actions))
    )
    verified = result_ok and evidence_ok and project_scope_ok and apply_ok and apply_count_ok
    verification = {
        "verified": verified,
        "project_id": run.project_id,
        "evidence_refs_resolved": evidence_ok,
        "completed_claims_grounded": claims_grounded,
        "project_scope_valid": project_scope_ok,
        "approval_status": run.approval_status,
        "applied_count": len(applied),
        "expected_apply_count": len(actions),
        "apply_count_valid": apply_count_ok,
        "rejected": rejected,
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
            else "VERIFICATION_FAILED"
        )
    run.current_step += 1
    return {"run": run.model_dump(mode="python")}
