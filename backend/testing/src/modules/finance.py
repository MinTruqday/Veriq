import logging
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.clients.ai_automation import ai_automation_client
from src.clients.authentication import load_accounts, resolve_account
from src.core.auth import CurrentUser, get_current_user, roles_for_membership
from src.core.common import audit, envelope, new_id, now
from src.core.configuration import settings
from src.core.database import database
from src.repositories.project import project_repository
from src.repositories.skill_profile import skill_profile_repository
from src.schemas.contracts.finance import (
    CapacityUpdate,
    CustomerCommercialTerms,
    PayrollColumnMapping,
    PayrollImportApply,
)

router = APIRouter(prefix="/kiem-thu/quan-tri/tai-chinh", tags=["Quản trị tài chính"])
logger = logging.getLogger(__name__)
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


def _require_admin(user):
    if not user.is_system_admin:
        raise HTTPException(status_code=403, detail={"code": "SYSTEM_ADMIN_REQUIRED"})


def _money(value):
    try:
        amount = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError("HOURLY_COST_INVALID") from None
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -4:
        raise ValueError("HOURLY_COST_INVALID")
    return format(amount, "f")


def _date(value, *, optional=False):
    if optional and (value is None or not str(value).strip()):
        return None
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except ValueError:
        raise ValueError("PAYROLL_DATE_INVALID") from None


async def _plan_resource_overview(project_id, plan):
    estimation = plan.get("estimation") or {}
    allocations = estimation.get("effort_allocations") or []
    allocated_by_user = {
        item["user_id"]: Decimal(str(item.get("planned_hours") or 0))
        for item in allocations
        if item.get("user_id")
    }
    allocated_ids = list(allocated_by_user)
    memberships = await project_repository.list_members(project_id)
    active_memberships = {
        item["user_id"]: item
        for item in memberships
        if item.get("status") == "ACTIVE" and item.get("user_id")
    }
    profiles = await skill_profile_repository.list_for_members(project_id, allocated_ids)
    profiles_by_user = {item["user_id"]: item for item in profiles}
    try:
        identities = await load_accounts(allocated_ids)
    except HTTPException as error:
        if error.status_code != 503:
            raise
        identities = {}

    active_run_counts = {user_id: 0 for user_id in allocated_ids}
    active_case_counts = {user_id: 0 for user_id in allocated_ids}
    active_project_ids = {user_id: set() for user_id in allocated_ids}
    async for run in skill_profile_repository.iter_active_runs_for_members(allocated_ids):
        assignments = run.get("test_case_assignments") or {}
        assigned_ids = set(assignments.values())
        if run.get("assignee_id"):
            assigned_ids.add(run["assignee_id"])
        for user_id in assigned_ids.intersection(active_run_counts):
            active_run_counts[user_id] += 1
            if run.get("project_id"):
                active_project_ids[user_id].add(run["project_id"])
        for user_id in assignments.values():
            if user_id in active_case_counts:
                active_case_counts[user_id] += 1

    schedule = plan.get("schedule") or {}
    start = str(schedule.get("planned_start_at") or "")[:10]
    end = str(schedule.get("planned_end_at") or "")[:10]
    capacity_status = "SCHEDULE_REQUIRED" if not start else "CAPACITY_NOT_DECLARED"
    capacity_by_user = {}
    if start:
        periods = await database.value.resource_capacity_periods.find(
            {"period_start": {"$lte": start}, "period_end": {"$gte": end or start}}
        ).to_list(100)
        if len(periods) == 1:
            capacity_status = "CAPACITY_DECLARED"
            capacity_by_user = {
                entry.get("user_id"): Decimal(str(entry.get("available_hours") or 0))
                for entry in periods[0].get("entries") or []
                if entry.get("user_id")
            }
        elif len(periods) > 1:
            capacity_status = "AMBIGUOUS_CAPACITY_PERIOD"

    people = []
    for user_id, hours in allocated_by_user.items():
        profile = profiles_by_user.get(user_id) or {}
        membership = active_memberships.get(user_id)
        skills = [item for item in profile.get("skills") or [] if item.get("confirmed") is True]
        experiences = [
            item for item in profile.get("experiences") or [] if item.get("confirmed") is True
        ]
        people.append(
            {
                "user_id": user_id,
                "label": (identities.get(user_id) or {}).get("label") or user_id,
                "active_project_member": membership is not None,
                "roles": sorted(roles_for_membership(membership)) if membership else [],
                "availability": profile.get("availability") or "NOT_RECORDED",
                "confirmed_skill_count": len(skills),
                "confirmed_skills": sorted(
                    {
                        str(item.get("name") or "").strip()
                        for item in skills
                        if str(item.get("name") or "").strip()
                    }
                ),
                "confirmed_experience_count": len(experiences),
                "confirmed_experiences": [
                    {
                        "title": str(item.get("title") or "").strip(),
                        "domain": str(item.get("domain") or "").strip(),
                        "technologies": [
                            str(value).strip()
                            for value in item.get("technologies") or []
                            if str(value).strip()
                        ],
                    }
                    for item in experiences
                    if str(item.get("title") or "").strip()
                ],
                "profile_status": "CONFIRMED_EVIDENCE_AVAILABLE"
                if skills or experiences
                else "NO_CONFIRMED_EVIDENCE",
                "planned_hours": str(hours),
                "declared_available_hours": str(capacity_by_user[user_id])
                if user_id in capacity_by_user
                else None,
                "active_test_run_count_across_projects": active_run_counts[user_id],
                "active_test_case_count_across_projects": active_case_counts[user_id],
                "active_project_count": len(active_project_ids[user_id]),
            }
        )

    risk_register = plan.get("risk_register") or []
    active_risks = [
        item for item in risk_register if item.get("status", "OPEN") not in {"CLOSED", "ACCEPTED"}
    ]
    allocated_hours = sum(allocated_by_user.values(), Decimal(0))
    declared_hours = sum(
        (capacity_by_user.get(user_id, Decimal(0)) for user_id in allocated_ids), Decimal(0)
    )
    capacity_assessment = {
        "status": capacity_status,
        "allocated_hours": str(allocated_hours),
        "declared_available_hours": str(declared_hours)
        if capacity_status == "CAPACITY_DECLARED"
        else None,
        "hours_covered": allocated_hours <= declared_hours
        if capacity_status == "CAPACITY_DECLARED"
        else None,
    }
    warnings = []
    if any(user_id not in active_memberships for user_id in allocated_ids):
        warnings.append("ALLOCATED_PERSON_NOT_ACTIVE_PROJECT_MEMBER")
    if any(person["availability"] not in {"AVAILABLE", "LIMITED"} for person in people):
        warnings.append("PERSON_AVAILABILITY_MISSING_OR_RESTRICTED")
    if any(person["profile_status"] == "NO_CONFIRMED_EVIDENCE" for person in people):
        warnings.append("CONFIRMED_SKILL_OR_EXPERIENCE_EVIDENCE_MISSING")
    if capacity_assessment["hours_covered"] is False:
        warnings.append("ALLOCATED_HOURS_EXCEED_DECLARED_CAPACITY")
    if any(active_run_counts.values()):
        warnings.append("CURRENT_TEST_RUN_LOAD_EXISTS")
    responsibilities = plan.get("responsibility_matrix") or []
    responsibility_people = {
        user_id for item in responsibilities for user_id in (item.get("responsible_user_ids") or [])
    }
    accountable_people = {
        item.get("accountable_user_id")
        for item in responsibilities
        if item.get("accountable_user_id")
    }
    if any(not item.get("responsible_user_ids") for item in responsibilities):
        warnings.append("PLAN_ACTIVITY_WITHOUT_RESPONSIBLE_PERSON")
    if responsibilities and any(not item.get("accountable_user_id") for item in responsibilities):
        warnings.append("PLAN_ACTIVITY_WITHOUT_ACCOUNTABLE_PERSON")
    if any(
        user_id not in active_memberships for user_id in responsibility_people | accountable_people
    ):
        warnings.append("RESPONSIBILITY_ASSIGNED_TO_INACTIVE_OR_NONMEMBER")
    if (responsibility_people | accountable_people) - set(allocated_ids):
        warnings.append("RESPONSIBILITY_PERSON_WITHOUT_PLAN_EFFORT_ALLOCATION")
    requirements = plan.get("requirement_version_ids") or []
    suites = plan.get("test_suite_snapshots") or []
    cases = plan.get("test_case_version_ids") or []
    scope_in = plan.get("scope_in") or []
    scope_out = plan.get("scope_out") or []
    milestones = plan.get("milestones") or []
    open_milestones = [
        item for item in milestones if item.get("status", "PLANNED") not in {"DONE", "CANCELLED"}
    ]
    test_data_plan = plan.get("test_data_plan") or {}
    defect_management = plan.get("defect_management") or {}
    communication_plan = plan.get("communication_plan") or {}
    dependencies = plan.get("dependencies") or []
    stakeholders = plan.get("stakeholders") or []
    schedule_days = None
    if start and end:
        try:
            schedule_days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        except ValueError:
            schedule_days = None
    plan_completeness = {
        "objective_declared": bool(str(plan.get("objective") or "").strip()),
        "scope_in_count": len(scope_in),
        "scope_out_count": len(scope_out),
        "environment_declared": bool(plan.get("environment") or plan.get("environment_id")),
        "test_approach_declared": bool(str(plan.get("test_approach") or "").strip()),
        "entry_criteria_count": len(plan.get("entry_criteria") or []),
        "exit_criteria_count": len(plan.get("exit_criteria") or []),
        "test_data_sources_count": len(test_data_plan.get("sources") or []),
        "test_data_preparation_declared": bool(
            str(test_data_plan.get("preparation") or "").strip()
        ),
        "defect_process_fields_completed": sum(
            bool(str(defect_management.get(key) or "").strip())
            for key in ("reporting", "classification", "triage", "retest", "closure")
        ),
        "communication_frequency_declared": bool(
            str(communication_plan.get("status_report_frequency") or "").strip()
        ),
        "stakeholder_count": len(stakeholders),
        "dependency_count": len(dependencies),
        "milestone_count": len(milestones),
        "open_milestone_count": len(open_milestones),
        "quality_target_count": len(plan.get("quality_targets") or []),
        "monitoring_metric_count": len(plan.get("monitoring_metrics") or []),
        "assumption_count": len(plan.get("assumptions") or []),
        "constraint_count": len(plan.get("constraints") or []),
        "risk_count": len(active_risks),
        "responsibility_activity_count": len(responsibilities),
        "responsible_activity_count": sum(
            bool(item.get("responsible_user_ids")) for item in responsibilities
        ),
        "accountable_activity_count": sum(
            bool(item.get("accountable_user_id")) for item in responsibilities
        ),
    }
    if not plan_completeness["objective_declared"]:
        warnings.append("PLAN_OBJECTIVE_NOT_DECLARED")
    if not scope_in:
        warnings.append("PLAN_INCLUDED_SCOPE_NOT_DECLARED")
    if not plan_completeness["environment_declared"]:
        warnings.append("PLAN_ENVIRONMENT_NOT_DECLARED")
    if (
        not plan_completeness["entry_criteria_count"]
        or not plan_completeness["exit_criteria_count"]
    ):
        warnings.append("PLAN_ENTRY_OR_EXIT_CRITERIA_INCOMPLETE")
    if not plan_completeness["test_data_sources_count"]:
        warnings.append("PLAN_TEST_DATA_SOURCE_NOT_DECLARED")
    if plan_completeness["defect_process_fields_completed"] < 5:
        warnings.append("PLAN_DEFECT_PROCESS_INCOMPLETE")
    role_coverage = {
        role: sum(
            1
            for user_id in allocated_ids
            if role
            in (
                active_memberships.get(user_id)
                and roles_for_membership(active_memberships[user_id])
                or set()
            )
        )
        for role in ("QA", "TESTER")
    }
    if not role_coverage["QA"]:
        warnings.append("NO_ACTIVE_QA_IN_PLAN_ALLOCATIONS")
    if not role_coverage["TESTER"]:
        warnings.append("NO_ACTIVE_TESTER_IN_PLAN_ALLOCATIONS")
    return {
        "people": people,
        "people_summary": {
            "planned_people": len(allocated_ids),
            "active_project_members": sum(
                1 for user_id in allocated_ids if user_id in active_memberships
            ),
            "unavailable_or_unknown": sum(
                1 for person in people if person["availability"] not in {"AVAILABLE", "LIMITED"}
            ),
            "without_confirmed_profile_evidence": sum(
                1 for person in people if person["profile_status"] == "NO_CONFIRMED_EVIDENCE"
            ),
            "distinct_active_projects": len(
                set().union(*(active_project_ids[user_id] for user_id in allocated_ids))
            ),
        },
        "team_coverage": {
            "role_member_counts": role_coverage,
            "responsibility_user_count": len(responsibility_people),
            "accountable_user_count": len(accountable_people),
            "responsibility_assignments_outside_plan_allocations": len(
                (responsibility_people | accountable_people) - set(allocated_ids)
            ),
            "activities_without_responsible_person": sum(
                1 for item in responsibilities if not item.get("responsible_user_ids")
            ),
            "activities_without_accountable_person": sum(
                1 for item in responsibilities if not item.get("accountable_user_id")
            ),
        },
        "capacity": capacity_assessment,
        "warnings": warnings,
        "plan_context": {
            "objective": plan.get("objective") or "",
            "scope_in_count": len(plan.get("scope_in") or []),
            "scope_out_count": len(plan.get("scope_out") or []),
            "scope_in": [str(item) for item in scope_in],
            "scope_out": [str(item) for item in scope_out],
            "requirement_version_count": len(requirements),
            "test_suite_count": len(suites),
            "test_case_version_count": len(cases),
            "test_level": plan.get("test_level"),
            "test_types": plan.get("test_types") or [],
            "environment": plan.get("environment"),
            "test_approach": plan.get("test_approach") or "",
            "entry_criteria_count": len(plan.get("entry_criteria") or []),
            "exit_criteria_count": len(plan.get("exit_criteria") or []),
            "release": plan.get("release") or "",
            "responsibility_activity_count": len(responsibilities),
            "activities_without_responsible_person": sum(
                1 for item in responsibilities if not item.get("responsible_user_ids")
            ),
            "accountable_activity_count": sum(
                1 for item in responsibilities if item.get("accountable_user_id")
            ),
            "open_risk_count": len(active_risks),
            "risk_exposure_total": str(
                sum((Decimal(str(item.get("exposure") or 0)) for item in active_risks), Decimal(0))
            ),
            "planned_start_at": schedule.get("planned_start_at"),
            "planned_end_at": schedule.get("planned_end_at"),
            "schedule_duration_days": schedule_days,
            "milestone_count": len(milestones),
            "open_milestone_count": len(open_milestones),
            "dependency_count": len(dependencies),
            "stakeholder_count": len(stakeholders),
            "quality_target_count": len(plan.get("quality_targets") or []),
            "monitoring_metric_count": len(plan.get("monitoring_metrics") or []),
            "assumption_count": len(plan.get("assumptions") or []),
            "constraint_count": len(plan.get("constraints") or []),
            "plan_completeness": plan_completeness,
        },
        "interpretation": "Human, workload, capacity, scope, schedule, risk, and plan-readiness factors are shown independently; this is not a suitability score and does not assign people.",
    }


async def _plan_staffing_options(project_id, plan, currency, effective_date):
    allocations = (plan.get("estimation") or {}).get("effort_allocations") or []
    memberships = await project_repository.list_members(project_id)
    active_members = {
        item["user_id"]: item
        for item in memberships
        if item.get("status") == "ACTIVE" and item.get("user_id")
    }
    membership_by_id = {item["user_id"]: item for item in memberships if item.get("user_id")}
    allocated_ids = [item["user_id"] for item in allocations if item.get("user_id")]
    member_ids = list(dict.fromkeys([*active_members, *allocated_ids]))
    profiles = await skill_profile_repository.list_for_members(project_id, member_ids)
    profile_by_id = {item["user_id"]: item for item in profiles}
    try:
        identities = await load_accounts(member_ids)
    except HTTPException as error:
        if error.status_code != 503:
            raise
        identities = {}
    end = str((plan.get("schedule") or {}).get("planned_end_at") or effective_date)[:10]
    periods = await database.value.resource_capacity_periods.find(
        {"period_start": {"$lte": effective_date}, "period_end": {"$gte": end}}
    ).to_list(100)
    capacity_by_user = {}
    capacity_status = "CAPACITY_NOT_DECLARED"
    if len(periods) == 1:
        capacity_status = "CAPACITY_DECLARED"
        capacity_by_user = {
            item.get("user_id"): Decimal(str(item.get("available_hours") or 0))
            for item in periods[0].get("entries") or []
            if item.get("user_id")
        }
    elif len(periods) > 1:
        capacity_status = "AMBIGUOUS_CAPACITY_PERIOD"

    workload = {user_id: {"runs": 0, "cases": 0, "projects": set()} for user_id in member_ids}
    async for run in skill_profile_repository.iter_active_runs_for_members(member_ids):
        assignments = run.get("test_case_assignments") or {}
        assigned = set(assignments.values())
        if run.get("assignee_id"):
            assigned.add(run["assignee_id"])
        for user_id in assigned.intersection(workload):
            workload[user_id]["runs"] += 1
            if run.get("project_id"):
                workload[user_id]["projects"].add(run["project_id"])
        for user_id in assignments.values():
            if user_id in workload:
                workload[user_id]["cases"] += 1

    async def labor_rate(user_id):
        return await database.value.payroll_rates.find_one(
            {
                "user_id": user_id,
                "currency": currency,
                "valid_from": {"$lte": effective_date},
                "$or": [{"valid_until": None}, {"valid_until": {"$gte": effective_date}}],
            },
            sort=[("valid_from", -1)],
        )

    rate_by_user = {user_id: await labor_rate(user_id) for user_id in member_ids}
    current_cost = Decimal(0)
    current_cost_complete = True
    for allocation in allocations:
        rate = rate_by_user.get(allocation["user_id"])
        if rate:
            current_cost += Decimal(str(rate["hourly_cost"])) * Decimal(
                str(allocation["planned_hours"])
            )
        else:
            current_cost_complete = False

    slots = []
    for allocation in allocations:
        incumbent_id = allocation["user_id"]
        incumbent_membership = active_members.get(incumbent_id)
        incumbent_roles = (
            roles_for_membership(incumbent_membership) if incumbent_membership else set()
        )
        hours = Decimal(str(allocation["planned_hours"]))
        incumbent_rate = rate_by_user.get(incumbent_id)
        candidates = []
        option_members = dict(active_members)
        if incumbent_id not in option_members:
            option_members[incumbent_id] = membership_by_id.get(incumbent_id) or {
                "user_id": incumbent_id,
                "status": "INACTIVE",
            }
        for member_id, membership in option_members.items():
            roles = roles_for_membership(membership)
            if member_id != incumbent_id and not (roles & incumbent_roles):
                continue
            rate = rate_by_user.get(member_id)
            profile = profile_by_id.get(member_id) or {}
            availability = profile.get("availability") or "NOT_RECORDED"
            active_project_member = member_id in active_members
            available_hours = capacity_by_user.get(member_id)
            team_cost = None
            cost_change = None
            if rate and (member_id == incumbent_id or incumbent_rate):
                if member_id == incumbent_id:
                    cost_change = Decimal(0)
                else:
                    cost_change = (
                        Decimal(str(rate["hourly_cost"]))
                        - Decimal(str(incumbent_rate["hourly_cost"]))
                    ) * hours
                if current_cost_complete:
                    team_cost = current_cost + cost_change
            skills = sorted(
                {
                    str(item.get("name") or "").strip()
                    for item in profile.get("skills") or []
                    if item.get("confirmed") is True and str(item.get("name") or "").strip()
                }
            )
            experiences = [
                str(item.get("title") or "").strip()
                for item in profile.get("experiences") or []
                if item.get("confirmed") is True and str(item.get("title") or "").strip()
            ]
            factors = []
            if not active_project_member:
                factors.append("NOT_ACTIVE_PROJECT_MEMBER")
            if availability not in {"AVAILABLE", "LIMITED"}:
                factors.append("AVAILABILITY_NOT_CONFIRMED")
            if capacity_status == "CAPACITY_DECLARED" and available_hours is None:
                factors.append("CAPACITY_NOT_DECLARED_FOR_MEMBER")
            elif available_hours is not None and available_hours < hours:
                factors.append("PLANNED_HOURS_EXCEED_AVAILABLE_CAPACITY")
            if not skills and not experiences:
                factors.append("NO_CONFIRMED_SKILL_OR_EXPERIENCE")
            load = workload[member_id]
            candidates.append(
                {
                    "user_id": member_id,
                    "label": (identities.get(member_id) or {}).get("label") or member_id,
                    "is_current_assignee": member_id == incumbent_id,
                    "roles": sorted(roles),
                    "active_project_member": active_project_member,
                    "confirmed_skills": skills,
                    "confirmed_experiences": experiences,
                    "availability": availability,
                    "planned_hours_for_slot": str(hours),
                    "declared_available_hours": str(available_hours)
                    if available_hours is not None
                    else None,
                    "active_test_case_count": load["cases"],
                    "active_test_run_count": load["runs"],
                    "active_project_count": len(load["projects"]),
                    "hourly_cost": str(rate["hourly_cost"]) if rate else None,
                    "currency": currency if rate else None,
                    "estimated_team_labor_cost": str(team_cost) if team_cost is not None else None,
                    "cost_change_from_current": str(cost_change)
                    if cost_change is not None
                    else None,
                    "review_factors": factors,
                }
            )
        slots.append(
            {
                "current_user_id": incumbent_id,
                "current_label": (identities.get(incumbent_id) or {}).get("label") or incumbent_id,
                "current_roles": sorted(incumbent_roles),
                "planned_hours": str(hours),
                "current_hourly_cost": str(incumbent_rate["hourly_cost"])
                if incumbent_rate
                else None,
                "candidates": candidates,
            }
        )
    return {
        "currency": currency,
        "effective_date": effective_date,
        "capacity_status": capacity_status,
        "current_team_labor_cost": str(current_cost) if current_cost_complete else None,
        "current_team_cost_complete": current_cost_complete,
        "replacement_model": "ONE_MEMBER_AT_A_TIME_WITH_SAME_PLANNED_HOURS_AND_ROLE_OVERLAP",
        "limitations": [
            "Mỗi phương án chỉ thay một người, giữ nguyên giờ công của vị trí đang phân bổ.",
            "Kỹ năng và kinh nghiệm hiển thị lấy từ hồ sơ đã xác nhận; Test Plan chưa gắn kỹ năng bắt buộc vào từng vị trí.",
            "Cần đối chiếu người được chọn với từng ca, vai trò và trách nhiệm trước khi cập nhật Test Plan.",
            "Chi phí là dự báo theo đơn giá có hiệu lực; không gồm thuế, chi phí khác hoặc chi phí thực tế.",
        ],
        "slots": slots,
    }


async def _parse_sheet(file):
    filename = (file.filename or "").lower()
    content = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=422, detail={"code": "PAYROLL_FILE_EMPTY"})
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail={"code": "PAYROLL_FILE_TOO_LARGE"})
    if not filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=415, detail={"code": "PAYROLL_FILE_FORMAT_UNSUPPORTED"})
    try:
        converted = await ai_automation_client.convert_attachment(filename, content)
    except Exception as error:
        logger.exception("Payroll document conversion failed")
        raise HTTPException(
            status_code=502, detail={"code": "PAYROLL_DOCLING_CONVERSION_FAILED"}
        ) from error
    markdown = converted.get("markdown") or ""
    if converted.get("unprocessed_blocks"):
        raise HTTPException(
            status_code=422, detail={"code": "PAYROLL_DOCUMENT_HAS_UNPROCESSED_BLOCKS"}
        )
    headers, rows = _payroll_markdown_table(markdown)
    if not headers or not rows:
        raise HTTPException(status_code=422, detail={"code": "PAYROLL_SHEET_EMPTY"})
    if any(not str(header).strip() for header in headers) or len(
        {str(header).strip().casefold() for header in headers}
    ) != len(headers):
        raise HTTPException(
            status_code=422,
            detail={"code": "PAYROLL_HEADERS_MUST_BE_NONEMPTY_AND_UNIQUE", "headers": headers},
        )
    return headers, rows


def _payroll_markdown_table(markdown):
    tables = []
    current = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            current.append([cell.strip().replace("\\|", "|") for cell in stripped[1:-1].split("|")])
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    for table in tables:
        if len(table) < 2:
            continue
        headers = table[0]
        data_rows = [
            row
            for row in table[1:]
            if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in row)
        ]
        if data_rows and all(len(row) == len(headers) for row in data_rows):
            return headers, [dict(zip(headers, row)) for row in data_rows]
    return [], []


@router.get("/bang-luong/mau.csv")
async def payroll_template(user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    body = "employee,hourly_cost,currency,valid_from,valid_until\n"
    return Response(
        content="\ufeff" + body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="veriq-payroll-template.csv"'},
    )


@router.post("/bang-luong/cot")
async def read_payroll_headers(
    file: UploadFile = File(...), user: CurrentUser = Depends(get_current_user)
):
    _require_admin(user)
    headers, _ = await _parse_sheet(file)
    return envelope({"headers": headers})


@router.post("/bang-luong/xem-truoc")
async def preview_payroll_import(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    user: CurrentUser = Depends(get_current_user),
):
    _require_admin(user)
    try:
        column_mapping = PayrollColumnMapping.model_validate_json(mapping)
    except Exception as error:
        raise HTTPException(
            status_code=422, detail={"code": "PAYROLL_COLUMN_MAPPING_INVALID"}
        ) from error
    headers, source_rows = await _parse_sheet(file)
    selected_columns = [
        column_mapping.employee,
        column_mapping.hourly_cost,
        column_mapping.currency,
        column_mapping.valid_from,
        *([column_mapping.valid_until] if column_mapping.valid_until else []),
    ]
    if any(column not in headers for column in selected_columns):
        raise HTTPException(
            status_code=422, detail={"code": "PAYROLL_COLUMN_NOT_FOUND", "headers": headers}
        )
    preview_rows = []
    users_to_resolve = {}
    seen = {}
    for row_number, source in enumerate(source_rows, start=2):
        row = {
            "row_number": row_number,
            "employee_reference": str(source.get(column_mapping.employee) or "").strip(),
        }
        try:
            if not row["employee_reference"]:
                raise ValueError("PAYROLL_EMPLOYEE_REQUIRED")
            row["hourly_cost"] = _money(source.get(column_mapping.hourly_cost))
            row["currency"] = str(source.get(column_mapping.currency) or "").strip().upper()
            if not _CURRENCY_PATTERN.fullmatch(row["currency"]):
                raise ValueError("PAYROLL_CURRENCY_INVALID")
            row["valid_from"] = _date(source.get(column_mapping.valid_from))
            row["valid_until"] = _date(
                source.get(column_mapping.valid_until) if column_mapping.valid_until else None,
                optional=True,
            )
            if row["valid_until"] and row["valid_until"] < row["valid_from"]:
                raise ValueError("PAYROLL_PERIOD_INVALID")
            key = (row["employee_reference"].casefold(), row["currency"], row["valid_from"])
            previous = seen.get(key)
            if previous:
                if all(
                    previous.get(field) == row.get(field)
                    for field in ("hourly_cost", "valid_until")
                ):
                    row["status"] = "DUPLICATE_IN_FILE"
                else:
                    previous["status"] = "CONFLICT_IN_FILE"
                    row["status"] = "CONFLICT_IN_FILE"
            else:
                seen[key] = row
                row["status"] = "PENDING_RESOLUTION"
                users_to_resolve[row["employee_reference"]] = None
        except ValueError as error:
            row["status"] = "INVALID"
            row["error_code"] = str(error)
        preview_rows.append(row)
    for reference in users_to_resolve:
        try:
            users_to_resolve[reference] = await resolve_account(reference)
        except HTTPException as error:
            if error.status_code != 404:
                raise
            users_to_resolve[reference] = None
            for row in preview_rows:
                if (
                    row.get("employee_reference") == reference
                    and row["status"] == "PENDING_RESOLUTION"
                ):
                    row["status"] = "INVALID"
                    row["error_code"] = "PAYROLL_EMPLOYEE_NOT_FOUND"
    rate_collection = database.value.payroll_rates
    for row in preview_rows:
        if row["status"] != "PENDING_RESOLUTION":
            continue
        row["user_id"] = users_to_resolve.get(row["employee_reference"])
        row.pop("employee_reference", None)
        if not row["user_id"]:
            row["status"] = "INVALID"
            row["error_code"] = "PAYROLL_EMPLOYEE_NOT_FOUND"
            continue
        existing = await rate_collection.find(
            {"user_id": row["user_id"], "currency": row["currency"]}
        ).to_list(5000)
        start = date.fromisoformat(row["valid_from"])
        end = date.fromisoformat(row["valid_until"]) if row["valid_until"] else date.max
        overlap = next(
            (
                item
                for item in existing
                if date.fromisoformat(item["valid_from"]) <= end
                and (
                    date.fromisoformat(item["valid_until"]) if item.get("valid_until") else date.max
                )
                >= start
            ),
            None,
        )
        if overlap:
            same = all(
                overlap.get(field) == row.get(field)
                for field in ("hourly_cost", "valid_from", "valid_until")
            )
            row["status"] = "UNCHANGED" if same else "CONFLICT_EXISTING"
            row["conflict_rate_id"] = overlap["_id"]
        else:
            row["status"] = "READY"
    preview_id = new_id("PAYPRE")
    preview = {
        "_id": preview_id,
        "revision": 1,
        "status": "PREVIEWED",
        "rows": preview_rows,
        "created_by": user.id,
        "created_at": now(),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=4),
        "source_filename": file.filename or "",
        "source_headers": headers,
    }
    await database.value.payroll_import_previews.insert_one(preview)
    await audit(
        user.id,
        "payroll_import_previewed",
        "PayrollImport",
        preview_id,
        None,
        {"row_count": len(preview_rows)},
    )
    return envelope(
        {"preview_id": preview_id, "revision": 1, "headers": headers, "rows": preview_rows}
    )


@router.post("/bang-luong/{preview_id}/ap-dung")
async def apply_payroll_import(
    preview_id: str, payload: PayrollImportApply, user: CurrentUser = Depends(get_current_user)
):
    _require_admin(user)
    previews = database.value.payroll_import_previews
    preview = await previews.find_one({"_id": preview_id, "status": "PREVIEWED"})
    if not preview:
        raise HTTPException(status_code=404, detail={"code": "PAYROLL_PREVIEW_NOT_FOUND"})
    if preview.get("revision") != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": "PAYROLL_PREVIEW_REVISION_CONFLICT"})
    if preview.get("expires_at") <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail={"code": "PAYROLL_PREVIEW_EXPIRED"})
    resolutions = {item.row_number: item.action for item in payload.resolutions}
    rows = preview.get("rows") or []
    unresolved = [
        row["row_number"]
        for row in rows
        if row["status"] in {"INVALID", "CONFLICT_IN_FILE", "CONFLICT_EXISTING"}
        and resolutions.get(row["row_number"]) != "SKIP"
    ]
    if unresolved:
        raise HTTPException(
            status_code=409,
            detail={"code": "PAYROLL_ROWS_REQUIRE_RESOLUTION", "row_numbers": unresolved},
        )
    selected = [
        row
        for row in rows
        if row["status"] == "READY" and resolutions.get(row["row_number"], "APPLY") == "APPLY"
    ]
    if any(
        row["status"] in {"CONFLICT_IN_FILE", "CONFLICT_EXISTING"}
        and resolutions.get(row["row_number"]) == "APPLY"
        for row in rows
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "PAYROLL_CONFLICT_MUST_BE_REIMPORTED_WITH_NON_OVERLAPPING_DATES"},
        )
    timestamp = now()
    rates = database.value.payroll_rates
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                rate_lock_keys = sorted({(row["user_id"], row["currency"]) for row in selected})
                locks = database.value.payroll_rate_locks
                for user_id, currency in rate_lock_keys:
                    await locks.update_one(
                        {"user_id": user_id, "currency": currency},
                        {"$inc": {"revision": 1}, "$setOnInsert": {"created_at": timestamp}},
                        upsert=True,
                        session=session,
                    )
                for row in selected:
                    end_value = row["valid_until"] or "9999-12-31"
                    overlap = await rates.find_one(
                        {
                            "user_id": row["user_id"],
                            "currency": row["currency"],
                            "valid_from": {"$lte": end_value},
                            "$or": [
                                {"valid_until": None},
                                {"valid_until": {"$gte": row["valid_from"]}},
                            ],
                        },
                        session=session,
                    )
                    if overlap:
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "code": "PAYROLL_RATE_CHANGED_REPREVIEW_REQUIRED",
                                "row_number": row["row_number"],
                            },
                        )
                    await rates.insert_one(
                        {
                            "_id": new_id("RATE"),
                            "user_id": row["user_id"],
                            "hourly_cost": row["hourly_cost"],
                            "currency": row["currency"],
                            "valid_from": row["valid_from"],
                            "valid_until": row["valid_until"],
                            "import_id": preview_id,
                            "created_by": user.id,
                            "created_at": timestamp,
                        },
                        session=session,
                    )
                result = await previews.update_one(
                    {
                        "_id": preview_id,
                        "revision": payload.expected_revision,
                        "status": "PREVIEWED",
                    },
                    {
                        "$set": {
                            "status": "APPLIED",
                            "applied_by": user.id,
                            "applied_at": timestamp,
                        },
                        "$inc": {"revision": 1},
                    },
                    session=session,
                )
                if result.modified_count != 1:
                    raise HTTPException(
                        status_code=409, detail={"code": "PAYROLL_PREVIEW_REVISION_CONFLICT"}
                    )
                await audit(
                    user.id,
                    "payroll_import_applied",
                    "PayrollImport",
                    preview_id,
                    None,
                    {"applied_rows": len(selected)},
                    session=session,
                )
    except HTTPException:
        raise
    except (DuplicateKeyError, PyMongoError) as error:
        raise HTTPException(
            status_code=409, detail={"code": "PAYROLL_RATE_CHANGED_REPREVIEW_REQUIRED"}
        ) from error
    return envelope(
        {
            "preview_id": preview_id,
            "applied_rows": len(selected),
            "skipped_rows": len(rows) - len(selected),
            "status": "APPLIED",
        },
        revision=payload.expected_revision + 1,
    )


@router.get("/bang-luong")
async def list_payroll_rates(user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    rows = (
        await database.value.payroll_rates.find(
            {},
            {
                "user_id": 1,
                "hourly_cost": 1,
                "currency": 1,
                "valid_from": 1,
                "valid_until": 1,
                "created_at": 1,
            },
        )
        .sort([("user_id", 1), ("valid_from", -1)])
        .to_list(10000)
    )
    identities = await load_accounts([item["user_id"] for item in rows])
    return envelope(
        [
            {**item, "employee": identities.get(item["user_id"]), "user_id": item["user_id"]}
            for item in rows
        ]
    )


@router.get("/du-an")
async def list_financial_projects(user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    projects = (
        await database.value.projects.find(
            {"status": {"$ne": "ARCHIVED"}}, {"name": 1, "key": 1, "status": 1}
        )
        .sort([("name", 1)])
        .to_list(5000)
    )
    return envelope(projects)


@router.get("/du-an/{project_id}/dieu-khoan")
async def get_project_commercial_terms(
    project_id: str, user: CurrentUser = Depends(get_current_user)
):
    _require_admin(user)
    project = await database.value.projects.find_one({"_id": project_id}, {"commercial_terms": 1})
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    return envelope(project.get("commercial_terms") or {"revision": 0, "status": "MISSING"})


@router.get("/du-an/{project_id}/ke-hoach")
async def list_financial_test_plans(project_id: str, user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    if not await database.value.projects.find_one({"_id": project_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    plans = (
        await database.value.test_plans.find(
            {"project_id": project_id},
            {
                "name": 1,
                "status": 1,
                "revision": 1,
                "estimation.planned_effort_hours": 1,
                "schedule.planned_start_at": 1,
            },
        )
        .sort([("updated_at", -1)])
        .to_list(1000)
    )
    return envelope(plans)


@router.put("/du-an/{project_id}/dieu-khoan")
async def set_project_commercial_terms(
    project_id: str, payload: CustomerCommercialTerms, user: CurrentUser = Depends(get_current_user)
):
    _require_admin(user)
    projects = database.value.projects
    project = await projects.find_one({"_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    current = project.get("commercial_terms") or {}
    if current.get("revision", 0) != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROJECT_FINANCIAL_REVISION_CONFLICT",
                "current_revision": current.get("revision", 0),
            },
        )
    revision = payload.expected_revision + 1
    terms = {
        "contract_price": format(payload.contract_price, "f"),
        "currency": payload.currency,
        "tax_included": payload.tax_included,
        "scope_note": payload.scope_note,
        "revision": revision,
        "updated_by": user.id,
        "updated_at": now(),
    }
    revision_filter = {"commercial_terms.revision": payload.expected_revision}
    if payload.expected_revision == 0:
        revision_filter = {"$or": [revision_filter, {"commercial_terms": {"$exists": False}}]}
    result = await projects.update_one(
        {"_id": project_id, **revision_filter}, {"$set": {"commercial_terms": terms}}
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_FINANCIAL_REVISION_CONFLICT"})
    await audit(
        user.id,
        "project_commercial_terms_updated",
        "Project",
        project_id,
        project_id,
        {"currency": payload.currency, "revision": revision},
    )
    return envelope({"project_id": project_id, **terms}, revision=revision)


@router.get("/du-an/{project_id}/ke-hoach/{test_plan_id}/du-toan")
async def project_cost_estimate(
    project_id: str, test_plan_id: str, user: CurrentUser = Depends(get_current_user)
):
    _require_admin(user)
    project = await database.value.projects.find_one({"_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    terms = project.get("commercial_terms")
    plan = await database.value.test_plans.find_one({"_id": test_plan_id, "project_id": project_id})
    if not plan:
        raise HTTPException(status_code=404, detail={"code": "TEST_PLAN_NOT_FOUND"})
    plan_source = (
        (plan.get("approved_snapshot") or plan) if plan.get("status") == "APPROVED" else plan
    )
    resource_overview = await _plan_resource_overview(project_id, plan_source)
    if not terms:
        return envelope(
            {
                "project_id": project_id,
                "test_plan_id": test_plan_id,
                "status": "MISSING_CUSTOMER_PRICE",
                "estimate": None,
                "resource_overview": resource_overview,
            }
        )
    estimation = plan_source.get("estimation") or {}
    planned_hours = Decimal(str(estimation.get("planned_effort_hours") or 0))
    if planned_hours <= 0:
        return envelope(
            {
                "project_id": project_id,
                "test_plan_id": test_plan_id,
                "status": "MISSING_EFFORT_ESTIMATE",
                "customer_price": terms["contract_price"],
                "currency": terms["currency"],
                "estimate": None,
                "resource_overview": resource_overview,
            }
        )
    allocations = estimation.get("effort_allocations") or []
    if not allocations:
        return envelope(
            {
                "project_id": project_id,
                "test_plan_id": test_plan_id,
                "status": "MISSING_EFFORT_ALLOCATION",
                "customer_price": terms["contract_price"],
                "currency": terms["currency"],
                "planned_effort_hours": str(planned_hours),
                "estimate": None,
                "resource_overview": resource_overview,
            }
        )
    allocated_hours = sum(Decimal(str(item["planned_hours"])) for item in allocations)
    if allocated_hours != planned_hours:
        return envelope(
            {
                "project_id": project_id,
                "test_plan_id": test_plan_id,
                "status": "EFFORT_ALLOCATION_MISMATCH",
                "customer_price": terms["contract_price"],
                "currency": terms["currency"],
                "planned_effort_hours": str(planned_hours),
                "allocated_effort_hours": str(allocated_hours),
                "estimate": None,
                "resource_overview": resource_overview,
            }
        )
    rate_total = Decimal(0)
    missing_rates = []
    schedule_start = (plan_source.get("schedule") or {}).get("planned_start_at")
    try:
        effective_date = date.fromisoformat(str(schedule_start)[:10]).isoformat()
    except ValueError:
        return envelope(
            {
                "project_id": project_id,
                "test_plan_id": test_plan_id,
                "status": "MISSING_PLAN_START_DATE",
                "customer_price": terms["contract_price"],
                "currency": terms["currency"],
                "estimate": None,
                "resource_overview": resource_overview,
            }
        )
    resource_overview["staffing_options"] = await _plan_staffing_options(
        project_id, plan_source, terms["currency"], effective_date
    )
    for allocation in allocations:
        user_id = allocation["user_id"]
        hours = Decimal(str(allocation["planned_hours"]))
        rate = await database.value.payroll_rates.find_one(
            {
                "user_id": user_id,
                "currency": terms["currency"],
                "valid_from": {"$lte": effective_date},
                "$or": [{"valid_until": None}, {"valid_until": {"$gte": effective_date}}],
            },
            sort=[("valid_from", -1)],
        )
        if not rate:
            missing_rates.append(user_id)
        else:
            rate_total += Decimal(rate["hourly_cost"]) * hours
    if missing_rates:
        return envelope(
            {
                "project_id": project_id,
                "test_plan_id": test_plan_id,
                "status": "MISSING_LABOR_RATES",
                "missing_user_ids": missing_rates,
                "planned_effort_hours": str(planned_hours),
                "customer_price": terms["contract_price"],
                "currency": terms["currency"],
                "estimate": None,
                "resource_overview": resource_overview,
            }
        )
    price = Decimal(terms["contract_price"])
    variance = price - rate_total
    return envelope(
        {
            "project_id": project_id,
            "test_plan_id": test_plan_id,
            "status": "FORECAST_ONLY",
            "customer_price": str(price),
            "estimated_labor_cost": str(rate_total),
            "variance": str(variance),
            "currency": terms["currency"],
            "planned_effort_hours": str(planned_hours),
            "comparison": "PRICE_BELOW_ESTIMATED_LABOR"
            if variance < 0
            else "PRICE_MATCHES_ESTIMATED_LABOR"
            if variance == 0
            else "PRICE_ABOVE_ESTIMATED_LABOR",
            "tax_included": terms["tax_included"],
            "commercial_scope_note": terms.get("scope_note") or "",
            "actual_cost_available": False,
            "resource_overview": resource_overview,
        }
    )


@router.put("/cong-suat")
async def update_capacity(payload: CapacityUpdate, user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    identities = await load_accounts([entry.user_id for entry in payload.entries])
    unknown = sorted({entry.user_id for entry in payload.entries} - set(identities))
    if unknown:
        raise HTTPException(
            status_code=422, detail={"code": "CAPACITY_USER_NOT_FOUND", "user_ids": unknown}
        )
    collection = database.value.resource_capacity_periods
    existing = await collection.find_one(
        {
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
        }
    )
    current_revision = existing.get("revision", 0) if existing else 0
    if current_revision != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": "CAPACITY_REVISION_CONFLICT", "current_revision": current_revision},
        )
    document = {
        "_id": existing["_id"] if existing else new_id("CAP"),
        "period_start": payload.period_start.isoformat(),
        "period_end": payload.period_end.isoformat(),
        "entries": [item.model_dump(mode="json") for item in payload.entries],
        "revision": current_revision + 1,
        "updated_by": user.id,
        "updated_at": now(),
    }
    if existing:
        result = await collection.replace_one(
            {"_id": existing["_id"], "revision": current_revision}, document
        )
        if result.modified_count != 1:
            raise HTTPException(status_code=409, detail={"code": "CAPACITY_REVISION_CONFLICT"})
    else:
        try:
            await collection.insert_one(document)
        except DuplicateKeyError as error:
            raise HTTPException(
                status_code=409, detail={"code": "CAPACITY_REVISION_CONFLICT"}
            ) from error
    await audit(
        user.id,
        "resource_capacity_updated",
        "ResourceCapacity",
        document["_id"],
        None,
        {"revision": document["revision"], "member_count": len(document["entries"])},
    )
    return envelope(document, revision=document["revision"])
