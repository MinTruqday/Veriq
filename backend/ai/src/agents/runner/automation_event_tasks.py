import json
import re

from src.agents.runner.automation_validation import validated_tasks
from src.prompts.automation_events import (
    api_operation_confirmed_objective,
    defect_recorded_objective,
    document_ingested_objective,
    performance_configuration_approved_objective,
    release_changed_observation_objective,
    requirement_changed_objective,
    status_report_created_objective,
    test_case_approved_observation_objective,
    test_case_changed_observation_objective,
    test_completion_report_created_objective,
    test_execution_observation_objective,
    test_execution_recorded_objective,
    test_plan_approved_objective,
    test_plan_changed_objective,
    work_item_changed_observation_objective,
)
from src.runtime.limits import limits
from src.schemas.agent import PlannedTask, ToolCall, ToolExecutionStatus
from src.tools.registry import registered_tools, tool_access


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
    arguments = dict(getattr(run, "intent_arguments", {}) or {})
    if "instruction" in properties and "instruction" not in arguments:
        arguments["instruction"] = run.objective
    tasks = validated_tasks(
        [
            PlannedTask(
                domain=domain,
                objective=run.objective,
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[ToolCall(tool_name=access.name, arguments=arguments)],
            )
        ],
        run,
        evidence_refs,
        known_identifiers=[
            *evidence_refs,
            *(
                [str(value) for key, value in arguments.items() if key.endswith("_id") and value]
                if access.name == "call_mcp_read_tool"
                else []
            ),
        ],
        authorized_mcp_tools=(
            {(str(arguments.get("connection_id") or ""), str(arguments.get("tool_name") or ""))}
            if access.name == "call_mcp_read_tool"
            else None
        ),
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


def direct_document_ingestion_task(run, state, evidence_refs):
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or (state.get("constraints") or {}).get("trigger") != "DOCUMENT_INGESTED"
    ):
        return None
    tool_name = "process_ingested_requirement_document"
    tool = registered_tools().get(tool_name)
    access = tool_access(tool)
    if not access or access.permission not in run.permissions:
        return None
    identifiers = list(
        dict.fromkeys(
            [
                *state.get("target_artifact_ids", []),
                *[
                    str(item.get("artifact_id"))
                    for item in state.get("evidence", [])
                    if item.get("artifact_id")
                ],
            ]
        )
    )
    document_id = next(
        (
            value
            for value in identifiers
            if any(
                value == str(item.get("artifact_id"))
                and str(item.get("artifact_type", "")).startswith("requirement_document")
                for item in state.get("evidence", [])
            )
        ),
        None,
    )
    if not document_id:
        return None
    previous_ingestion = next(
        (
            item.get("result")
            for item in reversed(getattr(run, "observations", []) or [])
            if item.get("tool_name") == "process_ingested_requirement_document"
            and item.get("status") == ToolExecutionStatus.COMPLETED
            and isinstance(item.get("result"), dict)
            and item["result"].get("requirement_import_job_id")
        ),
        {},
    )
    clarification_responses = list(
        (state.get("constraints") or {}).get("clarification_responses", []) or []
    )
    tool_arguments = {
        "project_id": run.project_id,
        "document_id": document_id,
        "source_facts": [
            item
            for item in state.get("source_facts", [])
            if str(item.get("artifact_id") or "") in identifiers
        ],
        "clarification_responses": clarification_responses,
    }
    if clarification_responses and previous_ingestion:
        tool_arguments.update(
            {
                "resume_import_job_id": previous_ingestion.get(
                    "requirement_import_job_id"
                ),
                "resume_requirement_ids": previous_ingestion.get(
                    "requirement_ids", []
                ),
            }
        )
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="requirement",
                objective=document_ingested_objective(),
                evidence_refs=evidence_refs,
                constraints={
                    "workflow_terminal": True,
                    "resume_after_clarification": bool(clarification_responses),
                },
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments=tool_arguments,
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[
            *identifiers,
            *evidence_refs,
            *(
                [
                    str(previous_ingestion.get("requirement_import_job_id")),
                    *map(str, previous_ingestion.get("requirement_ids", [])),
                ]
                if clarification_responses and previous_ingestion
                else []
            ),
        ],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_requirement_change_task(run, state, evidence_refs):
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or (state.get("constraints") or {}).get("trigger") != "REQUIREMENT_CHANGED"
    ):
        return None
    tool_name = "process_changed_requirement_version"
    tool = registered_tools().get(tool_name)
    access = tool_access(tool)
    if not access or access.permission not in run.permissions:
        return None
    version_ids = list(state.get("target_artifact_ids", []))
    version_ids.extend(
        str(item.get("artifact_version_id"))
        for item in state.get("evidence", [])
        if item.get("artifact_type") == "requirement_version" and item.get("artifact_version_id")
    )
    version_id = next(
        (value for value in dict.fromkeys(version_ids) if value in evidence_refs), None
    )
    if not version_id:
        return None
    source = next(
        (
            item
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "requirement_version"
            and str(item.get("artifact_version_id") or "") == version_id
            and type(item.get("artifact_revision")) is int
            and item["artifact_revision"] >= 1
        ),
        None,
    )
    tool_calls = []
    recommendation_name = "recommend_test_design_techniques_for_requirement_change"
    recommendation_tool = registered_tools().get(recommendation_name)
    recommendation_access = tool_access(recommendation_tool)
    if source and recommendation_access and recommendation_access.permission in run.permissions:
        tool_calls.append(
            ToolCall(
                tool_name=recommendation_name,
                arguments={
                    "project_id": run.project_id,
                    "requirement_version_id": version_id,
                    "expected_revision": source["artifact_revision"],
                },
            )
        )
    tool_calls.append(
        ToolCall(
            tool_name=tool_name,
            arguments={
                "project_id": run.project_id,
                "requirement_version_id": version_id,
                "source_facts": [
                    item
                    for item in state.get("source_facts", [])
                    if str(item.get("artifact_version_id") or "") == version_id
                ],
            },
        )
    )
    security_name = "generate_security_suggestions_for_requirement"
    security_tool = registered_tools().get(security_name)
    security_access = tool_access(security_tool)
    baseline_event_id = (
        f"requirement-version:{version_id}:{source['artifact_revision']}:BASELINED"
        if source
        else ""
    )
    if (
        source
        and str(run.source_event_id or "") == baseline_event_id
        and security_access
        and security_access.permission in run.permissions
    ):
        tool_calls.append(
            ToolCall(
                tool_name=security_name,
                arguments={
                    "project_id": run.project_id,
                    "requirement_version_id": version_id,
                    "source_event_id": baseline_event_id,
                    "source_event_revision": source["artifact_revision"],
                },
            )
        )
    conditions_name = "generate_test_conditions_for_requirement_baseline"
    conditions_tool = registered_tools().get(conditions_name)
    conditions_access = tool_access(conditions_tool)
    if (
        source
        and str(run.source_event_id or "") == baseline_event_id
        and conditions_access
        and conditions_access.permission in run.permissions
    ):
        tool_calls.append(
            ToolCall(
                tool_name=conditions_name,
                arguments={
                    "project_id": run.project_id,
                    "requirement_version_id": version_id,
                    "source_event_id": baseline_event_id,
                    "source_event_revision": source["artifact_revision"],
                },
            )
        )
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="requirement",
                objective=requirement_changed_objective(),
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=tool_calls,
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[*version_ids, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_defect_event_task(run, state, evidence_refs):
    trigger = (state.get("constraints") or {}).get("trigger")
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or trigger not in {"DEFECT_RECORDED", "DEFECT_CHANGED"}
    ):
        return None
    defect_ids = list(state.get("target_artifact_ids", []))
    defect_ids.extend(
        str(item.get("artifact_id"))
        for item in state.get("evidence", [])
        if item.get("artifact_type") == "defect" and item.get("artifact_id")
    )
    defect_id = next(
        (
            value
            for value in dict.fromkeys(defect_ids)
            if any(
                value
                in {str(item.get("artifact_id") or ""), str(item.get("artifact_version_id") or "")}
                and item.get("artifact_type") == "defect"
                and str(item.get("text") or "").strip()
                for item in state.get("evidence", [])
            )
        ),
        None,
    )
    source = next(
        (
            item
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "defect"
            and str(item.get("artifact_id") or "") == defect_id
            and type(item.get("artifact_revision")) is int
            and item["artifact_revision"] >= 1
        ),
        None,
    )
    if not source:
        return None
    source_event_id = f"defect:{defect_id}:{source['artifact_revision']}"
    if str(getattr(run, "source_event_id", "") or "") != source_event_id:
        return None
    tool_name = "process_recorded_defect"
    access = tool_access(registered_tools().get(tool_name))
    if not defect_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="analysis",
                objective=defect_recorded_objective(trigger),
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True, "event_trigger": trigger},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={
                            "project_id": run.project_id,
                            "defect_id": defect_id,
                            "source_event_id": source_event_id,
                            "source_event_revision": source["artifact_revision"],
                        },
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[*defect_ids, source_event_id, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_recorded_test_execution_task(run, state, evidence_refs):
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or (state.get("constraints") or {}).get("trigger") != "TEST_EXECUTION_RECORDED"
    ):
        return None
    result_ids = list(state.get("target_artifact_ids", []))
    result_ids.extend(
        str(item.get("artifact_id"))
        for item in state.get("evidence", [])
        if item.get("artifact_type") == "test_result" and item.get("artifact_id")
    )
    source = next(
        (
            item
            for value in dict.fromkeys(result_ids)
            for item in state.get("evidence", [])
            if value == str(item.get("artifact_id") or "")
            and item.get("artifact_type") == "test_result"
            and type(item.get("artifact_revision")) is int
            and item["artifact_revision"] >= 1
            and str(item.get("text") or "").strip()
        ),
        None,
    )
    result_id = str(source.get("artifact_id")) if source else None
    tool_name = "process_recorded_test_execution"
    access = tool_access(registered_tools().get(tool_name))
    if not result_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="execution",
                objective=test_execution_recorded_objective(),
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={
                            "project_id": run.project_id,
                            "result_id": result_id,
                            "expected_revision": source["artifact_revision"],
                        },
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[*result_ids, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_approved_plan_task(run, state, evidence_refs):
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or (state.get("constraints") or {}).get("trigger") != "TEST_PLAN_APPROVED"
    ):
        return None
    plan_id = next(
        (
            str(item.get("artifact_id"))
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "test_plan"
            and item.get("project_id") == run.project_id
            and item.get("artifact_id")
            and type(item.get("artifact_revision")) is int
            and item["artifact_revision"] >= 1
        ),
        None,
    )
    source = next(
        (
            item
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "test_plan"
            and item.get("project_id") == run.project_id
            and str(item.get("artifact_id") or "") == plan_id
            and type(item.get("artifact_revision")) is int
            and item["artifact_revision"] >= 1
        ),
        None,
    )
    expected_revision = source.get("artifact_revision") if source else None
    expected_event_id = (
        f"test-plan:{plan_id}:{expected_revision}:TEST_PLAN_APPROVED"
        if plan_id and expected_revision
        else ""
    )
    if not expected_event_id or str(run.source_event_id or "") != expected_event_id:
        return None
    tool_name = "process_approved_test_plan"
    access = tool_access(registered_tools().get(tool_name))
    if not plan_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="execution",
                objective=test_plan_approved_objective(),
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={
                            "project_id": run.project_id,
                            "test_plan_id": plan_id,
                            "expected_revision": expected_revision,
                            "source_event_id": expected_event_id,
                        },
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[plan_id, expected_event_id, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_performance_configuration_task(run, state, evidence_refs):
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or (state.get("constraints") or {}).get("trigger")
        != "PERFORMANCE_CONFIGURATION_APPROVED"
    ):
        return None
    source = next(
        (
            item
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "non_functional_test_plan"
            and item.get("project_id") == run.project_id
            and item.get("artifact_id")
            and type(item.get("artifact_revision")) is int
            and item["artifact_revision"] >= 1
        ),
        None,
    )
    if not source:
        return None
    plan_id = str(source["artifact_id"])
    revision = source["artifact_revision"]
    expected_event_id = (
        f"performance-configuration:{plan_id}:{revision}:"
        "PERFORMANCE_CONFIGURATION_APPROVED"
    )
    if str(run.source_event_id or "") != expected_event_id:
        return None
    tool_name = "process_approved_performance_configuration"
    access = tool_access(registered_tools().get(tool_name))
    if not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="test_design",
                objective=performance_configuration_approved_objective(),
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={
                            "project_id": run.project_id,
                            "plan_id": plan_id,
                            "source_event_id": expected_event_id,
                            "source_event_revision": revision,
                        },
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[plan_id, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_changed_plan_task(run, state, evidence_refs):
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or (state.get("constraints") or {}).get("trigger") != "TEST_PLAN_CHANGED"
    ):
        return None
    source = next(
        (
            item
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "test_plan"
            and item.get("project_id") == run.project_id
            and item.get("artifact_id")
        ),
        None,
    )
    plan_id = str(source.get("artifact_id") or "") if source else ""
    event_revision = source.get("artifact_revision") if source else None
    if type(event_revision) is not int or event_revision < 1:
        return None
    tool_name = "process_changed_test_plan"
    access = tool_access(registered_tools().get(tool_name))
    if not plan_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="execution",
                objective=test_plan_changed_objective(),
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={
                            "project_id": run.project_id,
                            "test_plan_id": plan_id,
                            "expected_revision": event_revision,
                        },
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[plan_id, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_event_observation_task(run, state, evidence_refs):
    tools = registered_tools()
    if not state.get("automatic") or state.get("source_event_verified") is not True:
        return None
    trigger = (state.get("constraints") or {}).get("trigger")
    evidence = state.get("evidence", [])
    tool_name = None
    domain = None
    permission = None
    objective = None
    identifier = None
    identifier_name = None
    dependency_edge = None
    if trigger == "TEST_EXECUTION_RECORDED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "test_result" and item.get("artifact_id")
            ),
            None,
        )
        tool_name, domain, permission = "get_test_result", "execution", "testrun.read"
        objective, identifier_name = test_execution_observation_objective(), "result_id"
    elif trigger == "WORK_ITEM_CHANGED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "work_item"
                and item.get("artifact_id")
                and type(item.get("artifact_revision")) is int
                and item["artifact_revision"] >= 1
            ),
            None,
        )
        tool_name, domain, permission = "get_work_item_impact_context", "analysis", "project.read"
        objective, identifier_name = work_item_changed_observation_objective(), "work_item_id"
        if source:
            relationship = source.get("relationship")
            if isinstance(relationship, dict):
                edge = {
                    "relationship_id": str(relationship.get("relationship_id") or ""),
                    "relationship_type": str(relationship.get("relationship_type") or ""),
                    "project_id": str(relationship.get("project_id") or ""),
                    "source_artifact_id": str(relationship.get("source_artifact_id") or ""),
                    "target_artifact_id": str(relationship.get("target_artifact_id") or ""),
                }
                if (
                    edge["relationship_id"]
                    and edge["relationship_type"] in {"BLOCKS", "RELATES_TO"}
                    and edge["project_id"] == run.project_id
                    and edge["source_artifact_id"] != edge["target_artifact_id"]
                    and source.get("artifact_id")
                    in {edge["source_artifact_id"], edge["target_artifact_id"]}
                ):
                    dependency_edge = edge
    elif trigger == "TEST_CASE_CHANGED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "test_case_draft"
                and item.get("artifact_id")
                and (
                    (
                        type(item.get("artifact_revision")) is int
                        and item["artifact_revision"] >= 1
                    )
                    or re.search(
                        r"^Current revision:\s*[1-9]\d*$",
                        str(item.get("text") or ""),
                        re.MULTILINE,
                    )
                )
            ),
            None,
        )
        tool_name, domain, permission = "lint_testcase", "test_design", "testcase.lint"
        objective, identifier_name = test_case_changed_observation_objective(), "test_case_draft_id"
    elif trigger == "API_OPERATION_CONFIRMED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "api_operation"
                and item.get("artifact_id")
                and type(item.get("artifact_revision")) is int
                and item["artifact_revision"] >= 1
            ),
            None,
        )
        tool_name, domain, permission = (
            "process_confirmed_api_operation",
            "test_design",
            "ai.generate_api_testcase",
        )
        objective, identifier_name = api_operation_confirmed_objective(), "operation_id"
    elif trigger == "TEST_CASE_APPROVED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "test_case_version"
                and item.get("artifact_id")
                and type(item.get("artifact_revision")) is int
                and item["artifact_revision"] >= 1
            ),
            None,
        )
        tool_name, domain, permission = (
            "refresh_assurance_after_test_case_approval",
            "analysis",
            "testcase.read",
        )
        objective, identifier_name = test_case_approved_observation_objective(), "version_id"
    elif trigger == "STATUS_REPORT_CREATED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "test_status_report"
                and item.get("artifact_id")
                and type(item.get("artifact_revision")) is int
                and item["artifact_revision"] >= 1
            ),
            None,
        )
        tool_name, domain, permission = (
            "process_created_status_report",
            "reporting",
            "teststatusreport.update",
        )
        objective, identifier_name = status_report_created_objective(), "report_id"
    elif trigger == "TEST_COMPLETION_REPORT_CREATED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "test_completion_report"
                and item.get("artifact_id")
                and type(item.get("artifact_revision")) is int
                and item["artifact_revision"] >= 1
            ),
            None,
        )
        tool_name, domain, permission = (
            "process_created_test_completion_report",
            "reporting",
            "testcompletion.update",
        )
        objective, identifier_name = (test_completion_report_created_objective(), "report_id")
    elif trigger == "RELEASE_CHANGED":
        source = next(
            (
                item
                for item in evidence
                if item.get("artifact_type") == "release"
                and item.get("authority") == "release_gate"
                and item.get("artifact_id")
                and type(item.get("artifact_revision")) is int
                and item["artifact_revision"] >= 1
            ),
            None,
        )
        tool_name, domain, permission = "process_changed_release", "execution", "release.close"
        objective, identifier_name = release_changed_observation_objective(), "release_id"
    else:
        return None
    if source and str(source.get("project_id") or "") != str(run.project_id):
        return None
    if (
        not source
        or not tool_access(tools.get(tool_name))
        or permission not in run.permissions
    ):
        return None
    if any(record.get("tool_name") == tool_name for record in run.tool_calls):
        return None
    identifier = str(source["artifact_id"])
    arguments = {identifier_name: identifier}
    if trigger == "STATUS_REPORT_CREATED":
        expected_event_id = (
            f"status-report:{identifier}:{source['artifact_revision']}:STATUS_REPORT_CREATED"
        )
        if str(run.source_event_id or "") != expected_event_id:
            return None
        arguments["source_event_id"] = expected_event_id
        arguments["source_event_revision"] = source["artifact_revision"]
    if trigger == "TEST_COMPLETION_REPORT_CREATED":
        expected_event_id = (
            f"completion-report:{identifier}:{source['artifact_revision']}:"
            "TEST_COMPLETION_REPORT_CREATED"
        )
        if str(run.source_event_id or "") != expected_event_id:
            return None
        arguments["source_event_id"] = expected_event_id
        arguments["source_event_revision"] = source["artifact_revision"]
    if trigger == "WORK_ITEM_CHANGED":
        relationship = source.get("relationship")
        expected_event_id = (
            f"work-item-dependency:{relationship['relationship_id']}:{identifier}:WORK_ITEM_CHANGED"
            if isinstance(relationship, dict) and dependency_edge is not None
            else f"work-item:{identifier}:{source['artifact_revision']}:WORK_ITEM_CHANGED"
        )
        if str(run.source_event_id or "") != expected_event_id:
            return None
    if trigger == "API_OPERATION_CONFIRMED":
        arguments["expected_revision"] = source["artifact_revision"]
    if trigger == "RELEASE_CHANGED":
        arguments["expected_revision"] = source["artifact_revision"]
    if trigger == "TEST_CASE_APPROVED":
        arguments["event_key"] = (
            f"test-case-version:{identifier}:{source['artifact_revision']}:TEST_CASE_APPROVED"
        )
        arguments["event_revision"] = source["artifact_revision"]
    if trigger == "WORK_ITEM_CHANGED":
        arguments["expected_revision"] = source["artifact_revision"]
    if "project_id" in tools[tool_name].args_schema.model_json_schema().get(
        "properties", {}
    ):
        arguments["project_id"] = run.project_id
    tool_calls = [ToolCall(tool_name=tool_name, arguments=arguments)]
    if trigger == "TEST_CASE_CHANGED":
        draft_tool = tools.get("get_test_case_draft")
        draft_access = tool_access(draft_tool)
        duplicate_tool = tools.get("find_near_duplicates")
        duplicate_access = tool_access(duplicate_tool)
        if not draft_access or draft_access.permission not in run.permissions:
            return None
        tool_calls = [
            ToolCall(tool_name="get_test_case_draft", arguments={"draft_id": identifier}),
            ToolCall(tool_name="lint_testcase", arguments={"test_case_draft_id": identifier}),
        ]
        if (
            duplicate_access
            and duplicate_access.permission in run.permissions
            and "ai.run_duplicate_check" in run.permissions
        ):
            tool_calls.append(
                ToolCall(
                    tool_name="find_near_duplicates",
                    arguments={
                        "project_id": run.project_id,
                        "test_case_draft_id": identifier,
                        "expected_revision": source["artifact_revision"],
                    },
                )
            )
    if trigger == "TEST_CASE_APPROVED" and "ai.generate_automation_script" in run.permissions:
        tool_calls.append(
            ToolCall(
                tool_name="generate_automation_script_after_test_case_approval",
                arguments={
                    "project_id": run.project_id,
                    "version_id": identifier,
                    "event_key": arguments["event_key"],
                    "event_revision": arguments["event_revision"],
                },
            )
        )
    task_constraints = {
        "event_trigger": trigger,
        "continue_after_observation": True,
        "workflow_terminal": trigger
        in {
            "WORK_ITEM_CHANGED",
            "API_OPERATION_CONFIRMED",
            "TEST_CASE_APPROVED",
            "STATUS_REPORT_CREATED",
            "TEST_COMPLETION_REPORT_CREATED",
            "RELEASE_CHANGED",
        },
    }
    if trigger == "WORK_ITEM_CHANGED":
        task_constraints["dependency_edge"] = dependency_edge

    tasks = validated_tasks(
        [
            PlannedTask(
                domain=domain,
                objective=objective,
                evidence_refs=evidence_refs,
                constraints=task_constraints,
                tool_calls=tool_calls,
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[
            identifier,
            *evidence_refs,
            *(
                [arguments["source_event_id"]]
                if trigger in {"STATUS_REPORT_CREATED", "TEST_COMPLETION_REPORT_CREATED"}
                else []
            ),
        ],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_test_case_change_impact_task(run, state, evidence_refs):
    constraints = state.get("constraints") or {}
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or constraints.get("trigger") != "TEST_CASE_CHANGED"
    ):
        return None

    from src.agents.runner.nodes import test_case_change_context

    run_state = getattr(run, "observations", [])
    context = test_case_change_context(run, state.get("evidence", []))
    draft = context.get("current_draft") or {}
    if (
        context.get("event_kind") != "TEST_CASE_UPDATED"
        or not context.get("has_comparison")
        or not context.get("has_source_link")
        or not draft.get("_id")
        or draft.get("project_id") != run.project_id
    ):
        return None

    already_read = {
        str((item.get("arguments") or {}).get("version_id"))
        for item in getattr(run, "tool_calls", [])
        if item.get("tool_name") == "get_test_case_version_by_id"
    }
    current_requirement_version_ids = list(
        dict.fromkeys(str(value) for value in draft.get("requirement_version_ids", []) if value)
    )
    parent_version_id = str(draft.get("parent_version_id") or "")
    parent_observation = next(
        (
            item
            for item in run_state
            if item.get("tool_name") == "get_test_case_version_by_id"
            and item.get("status") == ToolExecutionStatus.COMPLETED
            and str((item.get("result") or {}).get("_id") or "") == parent_version_id
        ),
        None,
    )
    parent_version = (parent_observation or {}).get("result") or {}
    if parent_version_id and (
        not parent_version or parent_version.get("project_id") != run.project_id
    ):
        if parent_version_id in already_read:
            return None
        tools = registered_tools()
        version_tool = tools.get("get_test_case_version_by_id")
        version_access = tool_access(version_tool)
        if not version_access or version_access.permission not in run.permissions:
            return None
        planned = validated_tasks(
            [
                PlannedTask(
                    domain="analysis",
                    objective="Read the parent Test Case version in the correct project before calculating the affected Requirement set. Do not infer impact from the draft alone.",
                    evidence_refs=evidence_refs,
                    constraints={
                        "event_trigger": "TEST_CASE_CHANGED",
                        "test_case_change_stage": "PARENT_VERSION_READ",
                    },
                    tool_calls=[
                        ToolCall(
                            tool_name="get_test_case_version_by_id",
                            arguments={"version_id": parent_version_id},
                        )
                    ],
                )
            ],
            run,
            evidence_refs,
            maximum=1,
            known_identifiers=[*evidence_refs, str(draft.get("_id")), parent_version_id],
        )
        return planned[0] if planned else None

    linked_requirement_version_ids = list(
        dict.fromkeys(
            [
                *current_requirement_version_ids,
                *[
                    str(value)
                    for value in parent_version.get("requirement_version_ids", [])
                    if value
                ],
            ]
        )
    )
    already_read_links = any(
        item.get("tool_name") == "get_traceability_links"
        and item.get("status") == ToolExecutionStatus.COMPLETED
        and list(
            dict.fromkeys(
                str(value)
                for value in (item.get("arguments") or {}).get("requirement_version_ids", [])
                if value
            )
        )
        == linked_requirement_version_ids
        for item in getattr(run, "tool_calls", [])
    )
    tools = registered_tools()
    calls = []

    trace_tool = tools.get("get_traceability_links")
    trace_access = tool_access(trace_tool)
    trace_properties = (
        trace_tool.args_schema.model_json_schema().get("properties", {})
        if trace_tool and hasattr(trace_tool.args_schema, "model_json_schema")
        else {}
    )
    trace_arguments = {"project_id": run.project_id}
    if "requirement_version_ids" in trace_properties and linked_requirement_version_ids:
        trace_arguments["requirement_version_ids"] = linked_requirement_version_ids
    elif len(linked_requirement_version_ids) == 1 and "requirement_version_id" in trace_properties:
        trace_arguments["requirement_version_id"] = linked_requirement_version_ids[0]
    else:
        trace_arguments = None
    if (
        not already_read_links
        and trace_access
        and trace_access.permission in run.permissions
        and trace_arguments
    ):
        calls.append(ToolCall(tool_name="get_traceability_links", arguments=trace_arguments))
    if not calls:
        return None

    known_identifiers = [
        *evidence_refs,
        str(draft.get("_id")),
        parent_version_id,
        *[
            str(value)
            for field in (
                "requirement_version_ids",
                "acceptance_criterion_ids",
                "coverage_item_ids",
                "test_condition_ids",
                "evidence_refs",
            )
            for value in (draft.get(field) or [])
        ],
    ]
    planned = validated_tasks(
        [
            PlannedTask(
                domain="analysis",
                objective=(
                    "Compare the changed Test Case draft with its exact parent version and trace links for the "
                    "Requirement versions linked to that case. List only Requirements, criteria, obligations, "
                    "and test cases in that verified scope; identify links needing QA review because fields changed. "
                    "Do not read the project-wide matrix to infer broader impact. Do not modify Requirements, drafts, "
                    "or frozen versions, and do not infer relationships from textual similarity alone. If a source "
                    "cannot be read, report that part as unverified."
                ),
                evidence_refs=evidence_refs,
                constraints={
                    "event_trigger": "TEST_CASE_CHANGED",
                    "test_case_change_stage": "TRACE_IMPACT_READBACK",
                    "workflow_terminal": True,
                },
                tool_calls=calls,
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[item for item in known_identifiers if item],
    )
    return planned[0] if planned and planned[0].tool_calls else None
