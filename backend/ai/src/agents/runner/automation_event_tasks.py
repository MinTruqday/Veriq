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
from src.agents.runner.automation_validation import validated_tasks

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
                        arguments={
                            "project_id": run.project_id,
                            "document_id": document_id,
                            "source_facts": [
                                item for item in state.get("source_facts", [])
                                if str(item.get("artifact_id") or "") in identifiers
                            ],
                        },
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
                    "event_trigger": trigger,
                    "continue_after_observation": True,
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

