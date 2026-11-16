import json

from src.agents.runner.agent_validation import validated_tasks
from src.runtime.limits import limits
from src.schemas.agent import PlannedTask, ToolCall, ToolExecutionStatus
from src.tools.registry import registered_tools, tool_access


def direct_capability_task(run, state, evidence_refs):
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
    arguments = dict(getattr(run, "intent_arguments", {}) or {})
    verified_targets = (
        [
            str(value)
            for value in state.get("target_artifact_ids", [])
            if isinstance(value, str) and value.strip()
        ]
        if state.get("source_event_verified") is True
        else []
    )
    task_evidence_refs = list(dict.fromkeys([*evidence_refs, *verified_targets]))
    known_identifiers = list(task_evidence_refs)
    if "instruction" in properties and "instruction" not in arguments:
        arguments["instruction"] = run.objective
    if "source_facts" in properties and "source_facts" not in arguments:
        source_ids = {
            str(value)
            for value in (
                state.get("target_artifact_ids")
                or getattr(run, "target_artifact_ids", [])
            )
            if value
        }
        arguments["source_facts"] = [
            item
            for item in state.get("source_facts", [])
            if str(item.get("artifact_id") or "") in source_ids
            or str(item.get("artifact_version_id") or "") in source_ids
        ]
        known_identifiers.extend(
            str(item.get("source_fact_id"))
            for item in arguments["source_facts"]
            if item.get("source_fact_id")
        )
    tasks = validated_tasks(
        [
            PlannedTask(
                domain=domain,
                objective=run.objective,
                evidence_refs=task_evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[ToolCall(tool_name=access.name, arguments=arguments)],
            )
        ],
        run,
        task_evidence_refs,
        known_identifiers=known_identifiers,
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_change_simulation_task(run, state, evidence_refs):
    if not (state.get("constraints") or {}).get("change_simulation"):
        return None
    simulation = (state.get("constraints") or {}).get("change_simulation_input") or {}
    baseline_version_id = str(simulation.get("base_requirement_version_id") or "")
    proposed_source_text = str(simulation.get("proposed_source_text") or "").strip()
    if not baseline_version_id or not proposed_source_text:
        return None
    source = next(
        (
            item
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "requirement_version"
            and item.get("project_id") == run.project_id
            and item.get("artifact_version_id") == baseline_version_id
            and item.get("artifact_version_id") in evidence_refs
        ),
        None,
    )
    version_id = str(source.get("artifact_version_id")) if source else None
    if not version_id:
        return None
    completed_tasks = getattr(run, "completed_tasks", []) or []
    discovery_completed = any(
        (task.get("constraints") or {}).get("change_simulation_stage") == "DISCOVERY"
        for task in completed_tasks
    )
    if discovery_completed:
        linked_version_ids = simulation_linked_test_case_version_ids(
            getattr(run, "observations", []), baseline_version_id
        )
        read_version_ids = simulation_successfully_read_test_case_version_ids(
            getattr(run, "observations", [])
        )
        unread_linked_version_ids = [
            identifier for identifier in linked_version_ids if identifier not in read_version_ids
        ]
        pending_version_ids = unread_linked_version_ids[: limits.tool_calls_per_task]
        if not pending_version_ids:
            revalidation_completed = any(
                (task.get("constraints") or {}).get("change_simulation_stage")
                == "SCOPE_REVALIDATION"
                for task in completed_tasks
            )
            if revalidation_completed:
                return None
            trace_tool = registered_tools().get("get_traceability_links")
            trace_access = tool_access(trace_tool)
            if not trace_access or trace_access.permission not in run.permissions:
                return None
            planned = [
                PlannedTask(
                    domain="analysis",
                    objective=(
                        "Re-read the exact Requirement baseline traceability scope after all linked Test Case versions "
                        "were read. This is a read-only consistency check; do not inspect other Requirement versions "
                        "or mutate project data."
                    ),
                    evidence_refs=evidence_refs,
                    constraints={
                        "change_simulation": True,
                        "change_simulation_input": simulation,
                        "change_simulation_stage": "SCOPE_REVALIDATION",
                        "continue_after_observation": True,
                        "workflow_terminal": True,
                    },
                    tool_calls=[
                        ToolCall(
                            tool_name="get_traceability_links",
                            arguments={
                                "project_id": run.project_id,
                                "requirement_version_id": baseline_version_id,
                            },
                        )
                    ],
                )
            ]
            tasks = validated_tasks(
                planned,
                run,
                evidence_refs,
                maximum=1,
                known_identifiers=[baseline_version_id, *linked_version_ids, *evidence_refs],
            )
            return tasks[0] if tasks and tasks[0].tool_calls else None
        version_tool = registered_tools().get("get_test_case_version_by_id")
        version_access = tool_access(version_tool)
        if not version_access or version_access.permission not in run.permissions:
            return None
        omitted_count = max(0, len(unread_linked_version_ids) - len(pending_version_ids))
        planned = [
            PlannedTask(
                domain="analysis",
                objective=(
                    "Read every Test Case version linked to the exact Requirement baseline and compare it "
                    "with the baseline source evidence and proposed Requirement content. For each case, "
                    "classify STILL_VALID, POTENTIALLY_AFFECTED, NEEDS_UPDATE, or INSUFFICIENT_EVIDENCE; "
                    "state what needs review and cite both the Requirement and Test Case versions read. "
                    "Do not treat proposed content as approved evidence. This is a read-only simulation."
                ),
                evidence_refs=evidence_refs,
                constraints={
                    "change_simulation": True,
                    "change_simulation_input": simulation,
                    "change_simulation_stage": "LINKED_TEST_CASES",
                    "omitted_linked_test_case_count": omitted_count,
                    "continue_after_observation": True,
                    "workflow_terminal": False,
                },
                tool_calls=[
                    ToolCall(
                        tool_name="get_test_case_version_by_id",
                        arguments={"version_id": identifier},
                    )
                    for identifier in pending_version_ids
                ],
            )
        ]
        tasks = validated_tasks(
            planned,
            run,
            evidence_refs,
            maximum=1,
            known_identifiers=[version_id, *linked_version_ids, *evidence_refs],
        )
        return tasks[0] if tasks and tasks[0].tool_calls else None

    planned = [
        PlannedTask(
            domain="analysis",
            objective=(
                "Simulate a Requirement change against the specified baseline version. Compare the proposed "
                "content with the baseline, follow exact trace links, classify affected artifacts, and do not write data."
            ),
            evidence_refs=evidence_refs,
            constraints={
                "change_simulation": True,
                "change_simulation_input": simulation,
                "change_simulation_stage": "DISCOVERY",
                "continue_after_observation": True,
                "workflow_terminal": False,
            },
            tool_calls=[
                ToolCall(
                    tool_name="get_requirement_version",
                    arguments={"requirement_version_id": version_id},
                ),
                ToolCall(
                    tool_name="get_traceability_links",
                    arguments={
                        "project_id": run.project_id,
                        "requirement_version_id": baseline_version_id,
                    },
                ),
            ],
        )
    ]
    tasks = validated_tasks(
        planned, run, evidence_refs, maximum=1, known_identifiers=[version_id, *evidence_refs]
    )
    if not tasks or not tasks[0].tool_calls:
        return None
    return tasks[0]


def simulation_linked_test_case_version_ids(observations, baseline_version_id):
    return list(
        dict.fromkeys(
            str(link.get("target_id"))
            for link in simulation_baseline_trace_links(
                observations, baseline_version_id, stage="DISCOVERY"
            )
            if link.get("status") == "CONFIRMED"
            if str(link.get("target_id") or "").strip()
        )
    )


def simulation_successfully_read_test_case_version_ids(observations):
    return {
        str(item.get("source_version_id"))
        for item in observations or []
        if item.get("tool_name") == "get_test_case_version_by_id"
        and item.get("status") == ToolExecutionStatus.COMPLETED
        and item.get("source_version_id")
        and isinstance(item.get("result"), dict)
        and str(item["result"].get("_id") or "") == str(item["source_version_id"])
    }


def simulation_baseline_trace_links(observations, baseline_version_id, stage=None):
    links = []
    baseline_criterion_ids = set()
    for observation in observations or []:
        if (
            observation.get("tool_name") != "get_traceability_links"
            or observation.get("status") != ToolExecutionStatus.COMPLETED
            or observation.get("output_security")
            or stage is not None
            and observation.get("change_simulation_stage") != stage
            and not (stage == "DISCOVERY" and observation.get("change_simulation_stage") is None)
        ):
            continue
        result = observation.get("result") or {}
        if not isinstance(result, dict):
            continue
        for criterion in result.get("acceptance_criteria") or []:
            if (
                not isinstance(criterion, dict)
                or str(criterion.get("requirement_version_id") or "") != baseline_version_id
            ):
                continue
            criterion_id = str(criterion.get("_id") or criterion.get("id") or "")
            if criterion_id.strip():
                baseline_criterion_ids.add(criterion_id)
    for observation in observations or []:
        if (
            observation.get("tool_name") != "get_traceability_links"
            or observation.get("status") != ToolExecutionStatus.COMPLETED
            or observation.get("output_security")
            or stage is not None
            and observation.get("change_simulation_stage") != stage
            and not (stage == "DISCOVERY" and observation.get("change_simulation_stage") is None)
        ):
            continue
        result = observation.get("result") or {}
        if not isinstance(result, dict):
            continue
        for link in result.get("trace_links") or []:
            if not isinstance(link, dict):
                continue
            if link.get("target_type") != "test_case_version" or link.get("status") not in {
                "CONFIRMED",
                "SUGGESTED",
            }:
                continue
            source_type = link.get("source_type")
            source_id = str(link.get("source_id") or "")
            if not (
                source_type == "requirement_version"
                and source_id == baseline_version_id
                or source_type == "acceptance_criterion"
                and source_id in baseline_criterion_ids
            ):
                continue
            links.append(link)
    return links


def simulation_baseline_trace_snapshot(observations, baseline_version_id, stage):
    candidates = [
        item
        for item in observations or []
        if item.get("tool_name") == "get_traceability_links"
        and item.get("status") == ToolExecutionStatus.COMPLETED
        and (
            item.get("change_simulation_stage") == stage
            or stage == "DISCOVERY" and item.get("change_simulation_stage") is None
        )
    ]
    if not candidates:
        return None

    snapshots = []
    for observation in candidates:
        if observation.get("output_security"):
            return None
        result = observation.get("result")
        if not isinstance(result, dict):
            return None
        requirement_versions = result.get("requirement_versions")
        acceptance_criteria = result.get("acceptance_criteria")
        trace_links = result.get("trace_links")
        if not all(isinstance(value, list) for value in (requirement_versions, acceptance_criteria, trace_links)):
            return None
        matching_versions = [
            item
            for item in requirement_versions
            if isinstance(item, dict) and str(item.get("_id") or "") == baseline_version_id
        ]
        if len(matching_versions) != 1:
            return None
        if any(
            not isinstance(item, dict)
            or str(item.get("requirement_version_id") or "") != baseline_version_id
            or not str(item.get("_id") or "").strip()
            for item in acceptance_criteria
        ):
            return None
        if any(not isinstance(item, dict) for item in trace_links):
            return None

        scoped_links = simulation_baseline_trace_links(
            [observation], baseline_version_id, stage=stage
        )
        snapshots.append(
            {
                "requirement_version": json.dumps(
                    matching_versions[0], sort_keys=True, ensure_ascii=False, default=str
                ),
                "acceptance_criteria": sorted(
                    json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                    for item in acceptance_criteria
                ),
                "trace_links": sorted(
                    json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                    for item in scoped_links
                ),
            }
        )
    if any(snapshot != snapshots[0] for snapshot in snapshots[1:]):
        return None
    return snapshots[0]
