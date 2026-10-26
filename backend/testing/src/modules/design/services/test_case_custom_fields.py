from datetime import date
from math import isfinite

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_roles, new_id, now
from src.repositories.test_design import test_design_repository


def inherit_custom_values(proposed_values, current_version):
    """Keep manually curated metadata when AI proposes a new version without it."""
    return proposed_values or current_version.get("custom_values", {})


async def list_test_case_custom_fields(project_id, user):
    await get_project(project_id, user, "testcase.read")
    return await test_design_repository.list_test_case_custom_fields(project_id)


async def list_all_test_case_custom_fields(project_id, user):
    await get_project(project_id, user, "project.update")
    roles = await get_project_roles(project_id, user.id)
    if "QA" not in roles:
        raise HTTPException(403, detail={"code": "CUSTOM_FIELD_MANAGER_REQUIRED"})
    fields = await test_design_repository.list_all_test_case_custom_fields(project_id)
    for field in fields:
        field.setdefault("revision", 1)
    return fields


async def create_test_case_custom_field(project_id, payload, user):
    await get_project(project_id, user, "project.update")
    roles = await get_project_roles(project_id, user.id)
    if "QA" not in roles:
        raise HTTPException(403, detail={"code": "CUSTOM_FIELD_MANAGER_REQUIRED"})
    field = {
        "_id": new_id("TCF"),
        "project_id": project_id,
        **payload.model_dump(),
        "status": "ACTIVE",
        "revision": 1,
        "created_at": now(),
        "created_by": user.id,
    }
    try:
        await test_design_repository.insert_test_case_custom_field(field)
    except DuplicateKeyError as error:
        raise HTTPException(409, detail={"code": "TEST_CASE_CUSTOM_FIELD_EXISTS"}) from error
    await audit(
        user.id,
        "test_case_custom_field_created",
        "TestCaseCustomField",
        field["_id"],
        project_id,
        {"key": field["key"], "value_type": field["value_type"], "required": field["required"]},
    )
    return field


async def update_test_case_custom_field(project_id, field_id, payload, user):
    await get_project(project_id, user, "project.update")
    roles = await get_project_roles(project_id, user.id)
    if "QA" not in roles:
        raise HTTPException(403, detail={"code": "CUSTOM_FIELD_MANAGER_REQUIRED"})
    current = await test_design_repository.find_test_case_custom_field(project_id, field_id)
    if not current:
        raise HTTPException(404, detail={"code": "TEST_CASE_CUSTOM_FIELD_NOT_FOUND"})
    current_revision = current.get("revision", 1)
    if current_revision != payload.expected_revision:
        raise HTTPException(
            409,
            detail={
                "code": "REVISION_CONFLICT",
                "current_revision": current_revision,
            },
        )
    changes = payload.model_dump(exclude={"expected_revision"}, exclude_unset=True)
    changes["updated_at"] = now()
    updated = await test_design_repository.update_test_case_custom_field(
        project_id, field_id, payload.expected_revision, changes
    )
    if not updated:
        latest = await test_design_repository.find_test_case_custom_field(
            project_id, field_id
        )
        if not latest:
            raise HTTPException(404, detail={"code": "TEST_CASE_CUSTOM_FIELD_NOT_FOUND"})
        raise HTTPException(
            409,
            detail={"code": "REVISION_CONFLICT", "current_revision": latest.get("revision", 1)},
        )
    await audit(
        user.id,
        "test_case_custom_field_updated",
        "TestCaseCustomField",
        field_id,
        project_id,
        {
            "before": {
                "label": current.get("label"),
                "required": current.get("required", False),
                "status": current.get("status"),
                "revision": current_revision,
            },
            "after": {
                "label": updated.get("label"),
                "required": updated.get("required", False),
                "status": updated.get("status"),
                "revision": updated.get("revision"),
            },
        },
    )
    return updated


def _valid_value(field, value):
    value_type = field["value_type"]
    if value_type == "text":
        return isinstance(value, str)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "date":
        if not isinstance(value, str):
            return False
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False
    if value_type == "choice":
        return isinstance(value, str) and value in field.get("choices", [])
    return False


async def validate_test_case_custom_values(
    project_id, values, enforce_required=False, session=None
):
    fields = await test_design_repository.list_all_test_case_custom_fields(
        project_id, session=session
    )
    fields_by_key = {field["key"]: field for field in fields}
    unknown = sorted(set(values) - set(fields_by_key))
    if unknown:
        raise HTTPException(
            422,
            detail={"code": "TEST_CASE_CUSTOM_FIELD_UNKNOWN", "field_keys": unknown},
        )
    missing = sorted(
        field["key"]
        for field in fields
        if enforce_required
        and field.get("status", "ACTIVE") == "ACTIVE"
        and field.get("required")
        and (field["key"] not in values or values[field["key"]] in (None, ""))
    )
    if missing:
        raise HTTPException(
            422,
            detail={"code": "TEST_CASE_CUSTOM_FIELD_REQUIRED", "field_keys": missing},
        )
    invalid = sorted(
        key for key, value in values.items() if not _valid_value(fields_by_key[key], value)
    )
    if invalid:
        raise HTTPException(
            422,
            detail={"code": "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID", "field_keys": invalid},
        )
