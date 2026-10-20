import hashlib
import json

from src.runtime.limits import limits
from src.schemas.agent import (
    AgentTask,
    PlannedTask,
    ToolExecutionStatus,
    ToolCall,
)
from src.tools.registry import audit_arguments, registered_tools, tool_access

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
                    "properties": {
                        name: {
                            key: value
                            for key, value in definition.items()
                            if key in {"type", "description", "enum", "minLength", "maxLength"}
                        }
                        for name, definition in schema.get("properties", {}).items()
                    },
                }
            values.append(
                {
                    "name": access.name,
                    "domains": sorted(access.domains),
                    "action": access.action,
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
                constraints={"workflow_terminal": True},
                tool_calls=[ToolCall(tool_name=access.name, arguments=arguments)],
            )
        ],
        run,
        evidence_refs,
        known_identifiers=evidence_refs,
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


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
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="requirement",
                objective="Tự động xử lý tài liệu mới theo luồng Requirements, tạo mẫu có nguồn, tránh Requirement và Test Case trùng, kiểm tra chất lượng, hoàn tất vòng đời khi được quyền và xác minh mọi thay đổi",
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={"project_id": run.project_id, "document_id": document_id},
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[*identifiers, *evidence_refs],
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
    version_id = next((value for value in dict.fromkeys(version_ids) if value in evidence_refs), None)
    if not version_id:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="requirement",
                objective="Tự động rà soát phiên bản Requirement vừa đổi, chốt theo cổng chất lượng, tạo các ca còn thiếu, loại trùng, đóng băng ca đạt chuẩn và xác minh dữ liệu đã lưu",
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={"project_id": run.project_id, "requirement_version_id": version_id},
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[*version_ids, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


def direct_defect_event_task(run, state, evidence_refs):
    if (
        not state.get("automatic")
        or state.get("source_event_verified") is not True
        or (state.get("constraints") or {}).get("trigger") != "DEFECT_RECORDED"
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
            value for value in dict.fromkeys(defect_ids)
            if any(
                value in {str(item.get("artifact_id") or ""), str(item.get("artifact_version_id") or "")}
                and item.get("artifact_type") == "defect"
                and str(item.get("text") or "").strip()
                for item in state.get("evidence", [])
            )
        ),
        None,
    )
    tool_name = "process_recorded_defect"
    access = tool_access(registered_tools().get(tool_name))
    if not defect_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="analysis",
                objective="Tạo hồ sơ phân tích cho defect mới bằng nội dung nguồn đã xác thực, tự sinh giả thuyết có căn cứ và đọc lại hồ sơ; không biến giả thuyết thành nguyên nhân đã xác nhận",
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={"project_id": run.project_id, "defect_id": defect_id},
                    )
                ],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[*defect_ids, *evidence_refs],
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
    result_id = next(
        (
            value for value in dict.fromkeys(result_ids)
            if any(
                value == str(item.get("artifact_id") or "")
                and item.get("artifact_type") == "test_result"
                and str(item.get("text") or "").strip()
                for item in state.get("evidence", [])
            )
        ),
        None,
    )
    tool_name = "process_recorded_test_execution"
    access = tool_access(registered_tools().get(tool_name))
    if not result_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="execution",
                objective="Đối chiếu kết quả FAIL đã lưu với defect liên kết và các Nghĩa vụ kiểm thử có chứa đúng phiên bản Test Case; chỉ ghi feedback khi quan hệ đã được xác minh, không suy diễn từ kết quả PASS",
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={"project_id": run.project_id, "result_id": result_id},
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
        ),
        None,
    )
    tool_name = "process_approved_test_plan"
    access = tool_access(registered_tools().get(tool_name))
    if not plan_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="execution",
                objective="Từ Test Plan vừa được duyệt, tạo Test Run idempotent đúng snapshot đã duyệt, khởi chạy nếu quyền và môi trường cho phép, rồi đọc lại để xác minh phạm vi; không giả lập kết quả thực thi",
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={"project_id": run.project_id, "test_plan_id": plan_id},
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
    plan_id = next(
        (
            str(item.get("artifact_id"))
            for item in state.get("evidence", [])
            if item.get("artifact_type") == "test_plan"
            and item.get("project_id") == run.project_id
            and item.get("artifact_id")
        ),
        None,
    )
    tool_name = "process_changed_test_plan"
    access = tool_access(registered_tools().get(tool_name))
    if not plan_id or not access or access.permission not in run.permissions:
        return None
    tasks = validated_tasks(
        [
            PlannedTask(
                domain="execution",
                objective="Kiểm tra Test Plan vừa thay đổi; nếu scope đủ điều kiện thì tự duyệt bằng quyền QA của dự án, tạo và khởi chạy Test Run theo snapshot, rồi đọc lại xác minh. Nếu thiếu điều kiện thì ghi rõ khoảng thiếu và không duyệt",
                evidence_refs=evidence_refs,
                constraints={"workflow_terminal": True},
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments={"project_id": run.project_id, "test_plan_id": plan_id},
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
    if trigger == "TEST_EXECUTION_RECORDED":
        source = next((item for item in evidence if item.get("artifact_type") == "test_result" and item.get("artifact_id")), None)
        tool_name, domain, permission = "get_test_result", "execution", "testrun.read"
        objective, identifier_name = "Đối chiếu kết quả thực thi vừa ghi với Test Run, phiên bản Test Case và defect đã liên kết; chỉ ghi nhận trạng thái có bằng chứng, không tự kết luận nguyên nhân hoặc tạo defect từ một kết quả thất bại", "result_id"
    elif trigger == "WORK_ITEM_CHANGED":
        source = next((item for item in evidence if item.get("artifact_type") == "work_item" and item.get("artifact_id")), None)
        tool_name, domain, permission = "get_work_item", "analysis", "project.read"
        objective, identifier_name = "Đọc lại Work Item vừa thay đổi trong phạm vi dự án rồi đánh giá tác động có bằng chứng trước mọi đề xuất tiếp theo", "work_item_id"
    elif trigger == "TEST_CASE_CHANGED":
        source = next((item for item in evidence if item.get("artifact_type") == "test_case_draft" and item.get("artifact_id")), None)
        tool_name, domain, permission = "lint_testcase", "test_design", "testcase.lint"
        objective, identifier_name = "Tự động kiểm tra chất lượng bản nháp Test Case vừa thay đổi bằng bộ kiểm tra dự án, lưu kết quả kiểm tra và báo rõ các phát hiện; không tự sửa nội dung bản nháp", "test_case_draft_id"
    elif trigger == "TEST_CASE_APPROVED":
        source = next((item for item in evidence if item.get("artifact_type") == "test_case_version" and item.get("artifact_id")), None)
        tool_name, domain, permission = "get_test_case_version_by_id", "test_design", "testcase.version.read"
        objective, identifier_name = "Đọc lại phiên bản Test Case đã đóng băng, xác minh trạng thái và các liên kết nguồn đang lưu; chỉ ghi nhận kết quả đọc lại, không sửa snapshot đã duyệt", "version_id"
    elif trigger == "RELEASE_CHANGED":
        source = next((item for item in evidence if item.get("artifact_type") == "release" and item.get("artifact_id")), None)
        tool_name, domain, permission = "get_release", "execution", "release.read"
        objective, identifier_name = "Đọc lại Release sau thay đổi, đối chiếu trạng thái và bằng chứng kiểm thử liên quan trước khi đề xuất bước tiếp theo", "release_id"
    else:
        return None
    if not source or not tool_access(registered_tools().get(tool_name)) or permission not in run.permissions:
        return None
    if any(record.get("tool_name") == tool_name for record in run.tool_calls):
        return None
    identifier = str(source["artifact_id"])
    arguments = {identifier_name: identifier}
    if "project_id" in registered_tools()[tool_name].args_schema.model_json_schema().get("properties", {}):
        arguments["project_id"] = run.project_id
    tasks = validated_tasks(
        [
            PlannedTask(
                domain=domain,
                objective=objective,
                evidence_refs=evidence_refs,
                constraints={
                    "workflow_terminal": trigger in {"TEST_CASE_CHANGED", "TEST_CASE_APPROVED"}
                },
                tool_calls=[ToolCall(tool_name=tool_name, arguments=arguments)],
            )
        ],
        run,
        evidence_refs,
        maximum=1,
        known_identifiers=[identifier, *evidence_refs],
    )
    return tasks[0] if tasks and tasks[0].tool_calls else None


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


def verified_tool_call_records(task, observations):
    records = []
    for call, observation in zip(task.tool_calls, observations):
        access = tool_access(registered_tools().get(call.tool_name))
        if observation.get("status") != ToolExecutionStatus.COMPLETED or not access:
            continue
        if access.action == "MUTATE" and (
            observation.get("verification") or {}
        ).get("status") != ToolExecutionStatus.COMPLETED:
            continue
        record = {
            "task_id": task.task_id,
            "tool_name": call.tool_name,
            "arguments": audit_arguments(call.arguments),
        }
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


def validated_tasks(
    tasks,
    run,
    evidence_refs,
    maximum=None,
    known_identifiers=None,
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
                if key.endswith("_id") and key != "project_id" and isinstance(value, str)
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
            if any(
                key.endswith("_id")
                and key != "project_id"
                and (not isinstance(value, str) or not value.strip())
                for key, value in arguments.items()
            ):
                continue
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
