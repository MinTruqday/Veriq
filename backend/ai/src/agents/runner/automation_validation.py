import hashlib
import json

from src.runtime.limits import limits
from src.schemas.agent import AgentTask, PlannedTask, ToolCall, ToolExecutionStatus
from src.tools.registry import audit_arguments, registered_tools, tool_access


def observed_identifiers(value):
    identifiers = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if (key == "_id" or key.endswith("_id")) and isinstance(item, str):
                identifiers.add(item)
            identifiers.update(observed_identifiers(item))
    elif isinstance(value, list):
        for item in value:
            identifiers.update(observed_identifiers(item))
    return identifiers


def observed_draft_identifiers(value):
    """Return only identifiers explicitly typed as drafts in source or tool payloads."""
    identifiers = set()
    if isinstance(value, dict):
        artifact_type = str(value.get("artifact_type") or "").casefold()
        if artifact_type.endswith("_draft") and value.get("artifact_id"):
            identifiers.add(str(value["artifact_id"]))
        for key, item in value.items():
            if key.endswith("_draft_id") and isinstance(item, str):
                identifiers.add(item)
            elif key == "_id" and artifact_type.endswith("_draft") and isinstance(item, str):
                identifiers.add(item)
            identifiers.update(observed_draft_identifiers(item))
    elif isinstance(value, list):
        for item in value:
            identifiers.update(observed_draft_identifiers(item))
    return identifiers

def bounded_tasks(tasks, run):
    remaining = max(0, limits.agent_steps - len(run.completed_tasks))
    return list(tasks)[:remaining]

def mutation_fingerprint(tool_name, arguments):
    encoded = json.dumps(
        {"tool_name": tool_name, "arguments": arguments},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def proposal_fingerprint(tool_name, arguments):
    scoped_arguments = {
        key: value
        for key, value in arguments.items()
        if key not in {"instruction", "objective"}
    }
    return mutation_fingerprint(tool_name, scoped_arguments or arguments)


def tool_evidence_reference(task_id, batch_id, call_index, tool_name):
    return ":".join(
        (
            str(task_id),
            str(batch_id),
            str(call_index),
            str(tool_name or "tool"),
        )
    )


def verified_tool_call_records(task, observations):
    records = []
    for tool_call_index, (call, observation) in enumerate(
        zip(task.tool_calls, observations)
    ):
        access = tool_access(registered_tools().get(call.tool_name))
        if observation.get("status") != ToolExecutionStatus.COMPLETED or not access:
            continue
        if access.action == "MUTATE" and (
            observation.get("verification") or {}
        ).get("status") != ToolExecutionStatus.COMPLETED:
            continue
        record = {
            "task_id": task.task_id,
            "tool_call_index": tool_call_index,
            "tool_name": call.tool_name,
            "arguments": audit_arguments(call.arguments),
        }
        if observation.get("tool_call_batch_id"):
            record["tool_call_batch_id"] = observation["tool_call_batch_id"]
        if access.action == "MUTATE":
            record["mutation_fingerprint"] = mutation_fingerprint(
                call.tool_name, call.arguments
            )
        elif access.action == "READ":
            record["read_fingerprint"] = mutation_fingerprint(
                call.tool_name, call.arguments
            )
        elif access.action == "PROPOSE":
            record["proposal_fingerprint"] = proposal_fingerprint(
                call.tool_name, call.arguments
            )
        records.append(record)
    return records


def tool_call_records_for_observations(tool_calls, observations):
    indexed_records = {}
    ambiguous_records = set()
    legacy_records = {}
    for record in tool_calls:
        task_id = record.get("task_id")
        call_index = record.get("tool_call_index")
        batch_id = record.get("tool_call_batch_id")
        if (
            isinstance(task_id, str)
            and task_id
            and isinstance(call_index, int)
            and not isinstance(call_index, bool)
            and call_index >= 0
        ):
            identity = (
                ("batch", batch_id, call_index)
                if isinstance(batch_id, str) and batch_id
                else ("task", task_id, call_index)
            )
            if identity in indexed_records:
                ambiguous_records.add(identity)
            else:
                indexed_records[identity] = record
        else:
            legacy_records.setdefault(str(record.get("tool_name") or ""), []).append(record)

    matched = []
    for observation in observations:
        task_id = observation.get("task_id")
        call_index = observation.get("tool_call_index")
        batch_id = observation.get("tool_call_batch_id")
        if (
            isinstance(task_id, str)
            and task_id
            and isinstance(call_index, int)
            and not isinstance(call_index, bool)
            and call_index >= 0
        ):
            identity = (
                ("batch", batch_id, call_index)
                if isinstance(batch_id, str) and batch_id
                else ("task", task_id, call_index)
            )
            record = indexed_records.get(identity, {})
            if (
                identity in ambiguous_records
                or record.get("tool_name") != observation.get("tool_name")
            ):
                record = {}
            matched.append(record)
            continue
        records = legacy_records.get(str(observation.get("tool_name") or ""), [])
        matched.append(records.pop(0) if records else {})
    return matched


def validated_tasks(
    tasks,
    run,
    evidence_refs,
    maximum=None,
    known_identifiers=None,
    known_draft_identifiers=None,
    authorized_mcp_tools=None,
):
    tool_values = registered_tools()
    validated = []
    completed_mutations = set()
    completed_proposals = set()
    legacy_mutations = set()
    completed_reads = set()
    for record in run.tool_calls:
        recorded_tool = record.get("tool_name")
        recorded_access = tool_access(tool_values.get(recorded_tool))
        if not recorded_access:
            continue
        if recorded_access.action == "READ":
            read_fingerprint = record.get("read_fingerprint")
            if read_fingerprint:
                completed_reads.add(read_fingerprint)
            continue
        if recorded_access.action == "PROPOSE":
            recorded_proposal_fingerprint = record.get("proposal_fingerprint")
            if recorded_proposal_fingerprint:
                completed_proposals.add(recorded_proposal_fingerprint)
            continue
        if recorded_access.action != "MUTATE":
            continue
        completed_reads.clear()
        recorded_fingerprint = record.get("mutation_fingerprint")
        if recorded_fingerprint:
            completed_mutations.add(recorded_fingerprint)
        recorded_ids = tuple(
            sorted(
                (key, str(value))
                for key, value in (record.get("arguments") or {}).items()
                if key.endswith("_id")
                and key not in {"project_id", "source_event_id"}
                and isinstance(value, str)
            )
        )
        if not recorded_fingerprint:
            legacy_mutations.add((recorded_tool, recorded_ids))
    task_limit = max(0, limits.agent_steps - len(run.completed_tasks))
    if maximum is not None:
        task_limit = min(task_limit, maximum)
    for planned in bounded_tasks(tasks, run)[:task_limit]:
        task = planned if isinstance(planned, PlannedTask) else PlannedTask(**planned)
        calls = []
        for call in task.tool_calls[: limits.tool_calls_per_task]:
            tool = tool_values.get(call.tool_name)
            access = tool_access(tool)
            if (
                not access
                or task.domain not in access.domains
            ):
                continue
            arguments = dict(call.arguments)
            schema = tool.args_schema.model_json_schema()
            properties = schema.get("properties", {})
            if "project_id" in properties:
                arguments["project_id"] = run.project_id
            if call.tool_name == "call_mcp_read_tool":
                mcp_tool = (
                    str(arguments.get("connection_id") or ""),
                    str(arguments.get("tool_name") or ""),
                )
                if mcp_tool not in set(authorized_mcp_tools or ()):
                    continue
            if any(
                key.endswith("_id")
                and key not in {"project_id", "source_event_id"}
                and not (
                    call.tool_name == "call_mcp_read_tool"
                    and key == "connection_id"
                )
                and (not isinstance(value, str) or not value.strip())
                for key, value in arguments.items()
            ):
                continue
            identifiers = {
                str(value)
                for key, value in arguments.items()
                if key != "project_id"
                and key.endswith("_id")
                and key != "source_event_id"
                and value
                and not (
                    call.tool_name == "call_mcp_read_tool"
                    and key == "connection_id"
                )
            }
            if identifiers.difference(set(known_identifiers or evidence_refs)):
                continue
            draft_arguments = {
                str(value)
                for key, value in arguments.items()
                if key.endswith("_draft_id") and value
            }
            if known_draft_identifiers is not None and draft_arguments.difference(
                known_draft_identifiers
            ):
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
            if access.action == "MUTATE":
                fingerprint = mutation_fingerprint(access.name, normalized)
                mutation_ids = tuple(
                    sorted(
                        (key, str(value))
                        for key, value in normalized.items()
                        if key.endswith("_id")
                        and key != "project_id"
                        and isinstance(value, str)
                    )
                )
                if fingerprint in completed_mutations or (
                    access.name,
                    mutation_ids,
                ) in legacy_mutations:
                    continue
            elif access.action == "READ":
                fingerprint = mutation_fingerprint(access.name, normalized)
                if fingerprint in completed_reads:
                    continue
                completed_reads.add(fingerprint)
            elif access.action == "PROPOSE":
                fingerprint = proposal_fingerprint(access.name, normalized)
                if fingerprint in completed_proposals:
                    continue
                completed_proposals.add(fingerprint)
            calls.append(ToolCall(tool_name=call.tool_name, arguments=normalized))
            if access.action == "MUTATE":
                completed_mutations.add(fingerprint)
        validated.append(
            AgentTask(
                run_id=run.run_id,
                project_id=run.project_id,
                user_id=run.user_id,
                domain=task.domain,
                objective=task.objective,
                evidence_refs=task.evidence_refs or evidence_refs,
                constraints=task.constraints,
                tool_calls=calls,
            )
        )
    return validated

