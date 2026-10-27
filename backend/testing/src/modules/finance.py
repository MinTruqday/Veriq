import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.core.auth import CurrentUser, get_current_user
from src.core.common import audit, envelope, new_id, now
from src.core.configuration import settings
from src.core.database import database
from src.schemas.contracts.finance import (
    CapacityUpdate,
    CustomerCommercialTerms,
    PayrollColumnMapping,
    PayrollImportApply,
)
from src.clients.authentication import load_accounts, resolve_account
from src.clients.ai_automation import ai_automation_client


router = APIRouter(prefix="/quan-tri/tai-chinh", tags=["Quản trị tài chính"])
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
        raise HTTPException(status_code=502, detail={"code": "PAYROLL_DOCLING_CONVERSION_FAILED"}) from error
    markdown = converted.get("markdown") or ""
    if converted.get("unprocessed_blocks"):
        raise HTTPException(status_code=422, detail={"code": "PAYROLL_DOCUMENT_HAS_UNPROCESSED_BLOCKS"})
    headers, rows = _payroll_markdown_table(markdown)
    if not headers or not rows:
        raise HTTPException(status_code=422, detail={"code": "PAYROLL_SHEET_EMPTY"})
    if any(not str(header).strip() for header in headers) or len({str(header).strip().casefold() for header in headers}) != len(headers):
        raise HTTPException(status_code=422, detail={"code": "PAYROLL_HEADERS_MUST_BE_NONEMPTY_AND_UNIQUE", "headers": headers})
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
        data_rows = [row for row in table[1:] if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in row)]
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
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
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
        raise HTTPException(status_code=422, detail={"code": "PAYROLL_COLUMN_MAPPING_INVALID"}) from error
    headers, source_rows = await _parse_sheet(file)
    selected_columns = [
        column_mapping.employee,
        column_mapping.hourly_cost,
        column_mapping.currency,
        column_mapping.valid_from,
        *([column_mapping.valid_until] if column_mapping.valid_until else []),
    ]
    if any(column not in headers for column in selected_columns):
        raise HTTPException(status_code=422, detail={"code": "PAYROLL_COLUMN_NOT_FOUND", "headers": headers})
    preview_rows = []
    users_to_resolve = {}
    seen = {}
    for row_number, source in enumerate(source_rows, start=2):
        row = {"row_number": row_number, "employee_reference": str(source.get(column_mapping.employee) or "").strip()}
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
                if all(previous.get(field) == row.get(field) for field in ("hourly_cost", "valid_until")):
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
                if row.get("employee_reference") == reference and row["status"] == "PENDING_RESOLUTION":
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
        existing = await rate_collection.find({"user_id": row["user_id"], "currency": row["currency"]}).to_list(5000)
        start = date.fromisoformat(row["valid_from"])
        end = date.fromisoformat(row["valid_until"]) if row["valid_until"] else date.max
        overlap = next(
            (
                item for item in existing
                if date.fromisoformat(item["valid_from"]) <= end
                and (date.fromisoformat(item["valid_until"]) if item.get("valid_until") else date.max) >= start
            ),
            None,
        )
        if overlap:
            same = all(overlap.get(field) == row.get(field) for field in ("hourly_cost", "valid_from", "valid_until"))
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
    await audit(user.id, "payroll_import_previewed", "PayrollImport", preview_id, None, {"row_count": len(preview_rows)})
    return envelope({"preview_id": preview_id, "revision": 1, "headers": headers, "rows": preview_rows})


@router.post("/bang-luong/{preview_id}/ap-dung")
async def apply_payroll_import(
    preview_id: str,
    payload: PayrollImportApply,
    user: CurrentUser = Depends(get_current_user),
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
        row["row_number"] for row in rows
        if row["status"] in {"INVALID", "CONFLICT_IN_FILE", "CONFLICT_EXISTING"}
        and resolutions.get(row["row_number"]) != "SKIP"
    ]
    if unresolved:
        raise HTTPException(status_code=409, detail={"code": "PAYROLL_ROWS_REQUIRE_RESOLUTION", "row_numbers": unresolved})
    selected = [row for row in rows if row["status"] == "READY" and resolutions.get(row["row_number"], "APPLY") == "APPLY"]
    if any(row["status"] in {"CONFLICT_IN_FILE", "CONFLICT_EXISTING"} and resolutions.get(row["row_number"]) == "APPLY" for row in rows):
        raise HTTPException(status_code=409, detail={"code": "PAYROLL_CONFLICT_MUST_BE_REIMPORTED_WITH_NON_OVERLAPPING_DATES"})
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
                            detail={"code": "PAYROLL_RATE_CHANGED_REPREVIEW_REQUIRED", "row_number": row["row_number"]},
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
                    {"_id": preview_id, "revision": payload.expected_revision, "status": "PREVIEWED"},
                    {"$set": {"status": "APPLIED", "applied_by": user.id, "applied_at": timestamp}, "$inc": {"revision": 1}},
                    session=session,
                )
                if result.modified_count != 1:
                    raise HTTPException(status_code=409, detail={"code": "PAYROLL_PREVIEW_REVISION_CONFLICT"})
                await audit(user.id, "payroll_import_applied", "PayrollImport", preview_id, None, {"applied_rows": len(selected)}, session=session)
    except HTTPException:
        raise
    except (DuplicateKeyError, PyMongoError) as error:
        raise HTTPException(status_code=409, detail={"code": "PAYROLL_RATE_CHANGED_REPREVIEW_REQUIRED"}) from error
    return envelope({"preview_id": preview_id, "applied_rows": len(selected), "skipped_rows": len(rows) - len(selected), "status": "APPLIED"}, revision=payload.expected_revision + 1)


@router.get("/bang-luong")
async def list_payroll_rates(user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    rows = await database.value.payroll_rates.find({}, {"user_id": 1, "hourly_cost": 1, "currency": 1, "valid_from": 1, "valid_until": 1, "created_at": 1}).sort([("user_id", 1), ("valid_from", -1)]).to_list(10000)
    identities = await load_accounts([item["user_id"] for item in rows])
    return envelope([
        {**item, "employee": identities.get(item["user_id"]), "user_id": item["user_id"]}
        for item in rows
    ])


@router.get("/du-an")
async def list_financial_projects(user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    projects = await database.value.projects.find(
        {"status": {"$ne": "ARCHIVED"}}, {"name": 1, "key": 1, "status": 1}
    ).sort([("name", 1)]).to_list(5000)
    return envelope(projects)


@router.get("/du-an/{project_id}/dieu-khoan")
async def get_project_commercial_terms(project_id: str, user: CurrentUser = Depends(get_current_user)):
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
    plans = await database.value.test_plans.find(
        {"project_id": project_id},
        {"name": 1, "status": 1, "revision": 1, "estimation.planned_effort_hours": 1, "schedule.planned_start_at": 1},
    ).sort([("updated_at", -1)]).to_list(1000)
    return envelope(plans)


@router.put("/du-an/{project_id}/dieu-khoan")
async def set_project_commercial_terms(
    project_id: str,
    payload: CustomerCommercialTerms,
    user: CurrentUser = Depends(get_current_user),
):
    _require_admin(user)
    projects = database.value.projects
    project = await projects.find_one({"_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    current = project.get("commercial_terms") or {}
    if current.get("revision", 0) != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_FINANCIAL_REVISION_CONFLICT", "current_revision": current.get("revision", 0)})
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
    result = await projects.update_one({"_id": project_id, **revision_filter}, {"$set": {"commercial_terms": terms}})
    if result.modified_count != 1:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_FINANCIAL_REVISION_CONFLICT"})
    await audit(user.id, "project_commercial_terms_updated", "Project", project_id, project_id, {"currency": payload.currency, "revision": revision})
    return envelope({"project_id": project_id, **terms}, revision=revision)


@router.get("/du-an/{project_id}/ke-hoach/{test_plan_id}/du-toan")
async def project_cost_estimate(project_id: str, test_plan_id: str, user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    project = await database.value.projects.find_one({"_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    terms = project.get("commercial_terms")
    if not terms:
        return envelope({"project_id": project_id, "status": "MISSING_CUSTOMER_PRICE", "estimate": None})
    plan = await database.value.test_plans.find_one({"_id": test_plan_id, "project_id": project_id})
    if not plan:
        raise HTTPException(status_code=404, detail={"code": "TEST_PLAN_NOT_FOUND"})
    plan_source = (plan.get("approved_snapshot") or plan) if plan.get("status") == "APPROVED" else plan
    estimation = plan_source.get("estimation") or {}
    planned_hours = Decimal(str(estimation.get("planned_effort_hours") or 0))
    if planned_hours <= 0:
        return envelope({"project_id": project_id, "test_plan_id": test_plan_id, "status": "MISSING_EFFORT_ESTIMATE", "customer_price": terms["contract_price"], "currency": terms["currency"], "estimate": None})
    allocations = estimation.get("effort_allocations") or []
    if not allocations:
        return envelope({"project_id": project_id, "test_plan_id": test_plan_id, "status": "MISSING_EFFORT_ALLOCATION", "customer_price": terms["contract_price"], "currency": terms["currency"], "planned_effort_hours": str(planned_hours), "estimate": None})
    allocated_hours = sum(Decimal(str(item["planned_hours"])) for item in allocations)
    if allocated_hours != planned_hours:
        return envelope({"project_id": project_id, "test_plan_id": test_plan_id, "status": "EFFORT_ALLOCATION_MISMATCH", "customer_price": terms["contract_price"], "currency": terms["currency"], "planned_effort_hours": str(planned_hours), "allocated_effort_hours": str(allocated_hours), "estimate": None})
    rate_total = Decimal(0)
    missing_rates = []
    schedule_start = (plan_source.get("schedule") or {}).get("planned_start_at")
    try:
        effective_date = date.fromisoformat(str(schedule_start)[:10]).isoformat()
    except ValueError:
        return envelope({"project_id": project_id, "test_plan_id": test_plan_id, "status": "MISSING_PLAN_START_DATE", "customer_price": terms["contract_price"], "currency": terms["currency"], "estimate": None})
    for allocation in allocations:
        user_id = allocation["user_id"]
        hours = Decimal(str(allocation["planned_hours"]))
        rate = await database.value.payroll_rates.find_one({"user_id": user_id, "currency": terms["currency"], "valid_from": {"$lte": effective_date}, "$or": [{"valid_until": None}, {"valid_until": {"$gte": effective_date}}]}, sort=[("valid_from", -1)])
        if not rate:
            missing_rates.append(user_id)
        else:
            rate_total += Decimal(rate["hourly_cost"]) * hours
    if missing_rates:
        return envelope({"project_id": project_id, "test_plan_id": test_plan_id, "status": "MISSING_LABOR_RATES", "missing_user_ids": missing_rates, "planned_effort_hours": str(planned_hours), "customer_price": terms["contract_price"], "currency": terms["currency"], "estimate": None})
    price = Decimal(terms["contract_price"])
    variance = price - rate_total
    return envelope({"project_id": project_id, "test_plan_id": test_plan_id, "status": "FORECAST_ONLY", "customer_price": str(price), "estimated_labor_cost": str(rate_total), "variance": str(variance), "currency": terms["currency"], "planned_effort_hours": str(planned_hours), "comparison": "PRICE_BELOW_ESTIMATED_LABOR" if variance < 0 else "PRICE_MATCHES_ESTIMATED_LABOR" if variance == 0 else "PRICE_ABOVE_ESTIMATED_LABOR", "tax_included": terms["tax_included"], "actual_cost_available": False})


@router.put("/cong-suat")
async def update_capacity(payload: CapacityUpdate, user: CurrentUser = Depends(get_current_user)):
    _require_admin(user)
    identities = await load_accounts([entry.user_id for entry in payload.entries])
    unknown = sorted({entry.user_id for entry in payload.entries} - set(identities))
    if unknown:
        raise HTTPException(status_code=422, detail={"code": "CAPACITY_USER_NOT_FOUND", "user_ids": unknown})
    collection = database.value.resource_capacity_periods
    existing = await collection.find_one({"period_start": payload.period_start.isoformat(), "period_end": payload.period_end.isoformat()})
    current_revision = existing.get("revision", 0) if existing else 0
    if current_revision != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": "CAPACITY_REVISION_CONFLICT", "current_revision": current_revision})
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
        result = await collection.replace_one({"_id": existing["_id"], "revision": current_revision}, document)
        if result.modified_count != 1:
            raise HTTPException(status_code=409, detail={"code": "CAPACITY_REVISION_CONFLICT"})
    else:
        try:
            await collection.insert_one(document)
        except DuplicateKeyError as error:
            raise HTTPException(status_code=409, detail={"code": "CAPACITY_REVISION_CONFLICT"}) from error
    await audit(user.id, "resource_capacity_updated", "ResourceCapacity", document["_id"], None, {"revision": document["revision"], "member_count": len(document["entries"])})
    return envelope(document, revision=document["revision"])
