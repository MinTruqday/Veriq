import xml.etree.ElementTree as xml

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, new_id, now
from src.core.database import database
from src.modules.integrations.services.junit_import_identity import junit_import_source_hash


def junit_cases(content):
    try:
        root = xml.fromstring(content)
    except xml.ParseError as error:
        raise HTTPException(status_code=422, detail={"code": "INVALID_JUNIT_XML"}) from error
    values = []
    for case in root.findall(".//testcase"):
        properties = {
            item.get("name"): item.get("value", "")
            for item in case.findall("./properties/property")
            if item.get("name")
        }
        version_id = properties.get("veriq_test_case_version_id", "").strip()
        values.append({
            "name": case.get("name", ""),
            "classname": case.get("classname", ""),
            "test_case_version_id": version_id,
            "status": "FAIL" if case.find("./failure") is not None or case.find("./error") is not None else "SKIPPED" if case.find("./skipped") is not None else "PASS",
            "message": (case.findtext("./failure") or case.findtext("./error") or "").strip()[:5000],
        })
    if not values:
        raise HTTPException(status_code=422, detail={"code": "JUNIT_WITHOUT_TEST_CASE"})
    return values


async def import_junit_result(project_id, test_run_id, content, user):
    await get_project(project_id, user, "automation.create")
    run = await database.value.test_runs.find_one({"_id": test_run_id, "project_id": project_id})
    if not run:
        raise HTTPException(status_code=422, detail={"code": "INVALID_TEST_RUN"})
    source_hash = junit_import_source_hash(test_run_id, content)
    existing_receipt = await database.value.junit_result_imports.find_one(
        {"project_id": project_id, "test_run_id": test_run_id, "source_hash": source_hash}
    )
    if existing_receipt:
        return existing_receipt
    rows = junit_cases(content)
    allowed = set(run.get("test_case_version_ids", []))
    timestamp = now()
    imported, unresolved = [], []
    receipt = {
        "_id": new_id("JUNIT"),
        "project_id": project_id,
        "test_run_id": test_run_id,
        "source_hash": source_hash,
        "mapped_test_case_version_ids": imported,
        "unresolved": unresolved,
        "status": "NEEDS_MAPPING" if unresolved else "IMPORTED",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
    }
    try:
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                existing_receipt = await database.value.junit_result_imports.find_one(
                    {
                        "project_id": project_id,
                        "test_run_id": test_run_id,
                        "source_hash": source_hash,
                    },
                    session=session,
                )
                if existing_receipt:
                    return existing_receipt
                for row in rows:
                    version_id = row["test_case_version_id"]
                    if not version_id or version_id not in allowed:
                        unresolved.append(row)
                        continue
                    result = await database.value.test_results.find_one(
                        {"test_run_id": test_run_id, "test_case_version_id": version_id},
                        session=session,
                    )
                    if not result:
                        unresolved.append(row)
                        continue
                    updated_result = await database.value.test_results.update_one(
                        {"_id": result["_id"], "revision": result.get("revision", 1)},
                        {
                            "$set": {
                                "status": row["status"],
                                "note": row["message"],
                                "executor_id": "automation:junit",
                                "completed_at": timestamp,
                                "updated_at": timestamp,
                            },
                            "$inc": {"revision": 1},
                        },
                        session=session,
                    )
                    if not updated_result.matched_count:
                        raise HTTPException(
                            status_code=409,
                            detail={"code": "JUNIT_RESULT_CHANGED_RETRY_IMPORT"},
                        )
                    imported.append(version_id)
                receipt["mapped_test_case_version_ids"] = imported
                receipt["unresolved"] = unresolved
                receipt["status"] = "NEEDS_MAPPING" if unresolved else "IMPORTED"
                await database.value.junit_result_imports.insert_one(receipt, session=session)
                await audit(
                    user.id,
                    "junit_result_imported",
                    "JUnitResultImport",
                    receipt["_id"],
                    project_id,
                    {"mapped": len(imported), "unresolved": len(unresolved)},
                    session=session,
                )
    except DuplicateKeyError:
        existing_receipt = await database.value.junit_result_imports.find_one(
            {"project_id": project_id, "test_run_id": test_run_id, "source_hash": source_hash}
        )
        if existing_receipt:
            return existing_receipt
        raise
    return receipt


async def list_junit_imports(project_id, user):
    await get_project(project_id, user, "automation.read")
    return await database.value.junit_result_imports.find({"project_id": project_id}).sort("created_at", -1).to_list(200)


async def resolve_junit_unresolved_mapping(import_id, payload, user):
    receipt = await database.value.junit_result_imports.find_one({"_id": import_id})
    if not receipt:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    await get_project(receipt["project_id"], user, "automation.create")
    if receipt.get("revision", 1) != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    if receipt.get("status") != "NEEDS_MAPPING":
        raise HTTPException(status_code=409, detail={"code": "JUNIT_IMPORT_NOT_AWAITING_MAPPING"})
    unresolved = receipt.get("unresolved", [])
    if payload.unresolved_index >= len(unresolved):
        raise HTTPException(status_code=422, detail={"code": "INVALID_JUNIT_UNRESOLVED_INDEX"})
    run = await database.value.test_runs.find_one(
        {"_id": receipt["test_run_id"], "project_id": receipt["project_id"]}
    )
    if not run or payload.test_case_version_id not in set(run.get("test_case_version_ids", [])):
        raise HTTPException(status_code=422, detail={"code": "JUNIT_MAPPING_OUTSIDE_TEST_RUN_SCOPE"})
    if not await database.value.test_case_versions.find_one(
        {
            "_id": payload.test_case_version_id,
            "project_id": receipt["project_id"],
            "status": "ACTIVE",
        },
        {"_id": 1},
    ):
        raise HTTPException(status_code=422, detail={"code": "JUNIT_TEST_CASE_VERSION_NOT_FOUND"})
    result = await database.value.test_results.find_one(
        {
            "project_id": receipt["project_id"],
            "test_run_id": receipt["test_run_id"],
            "test_case_version_id": payload.test_case_version_id,
        }
    )
    if not result:
        raise HTTPException(status_code=422, detail={"code": "JUNIT_TEST_RESULT_NOT_FOUND"})
    row = unresolved[payload.unresolved_index]
    timestamp = now()
    claimed_receipt = await database.value.junit_result_imports.find_one_and_update(
        {
            "_id": import_id,
            "revision": payload.expected_revision,
            "status": "NEEDS_MAPPING",
        },
        {
            "$set": {"status": "MAPPING", "updated_at": timestamp},
            "$inc": {"revision": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not claimed_receipt:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    updated_result = await database.value.test_results.find_one_and_update(
        {"_id": result["_id"], "revision": result.get("revision", 1)},
        {
            "$set": {
                "status": row["status"],
                "note": row["message"],
                "executor_id": "automation:junit",
                "completed_at": timestamp,
                "updated_at": timestamp,
            },
            "$inc": {"revision": 1},
        },
    )
    if not updated_result:
        await database.value.junit_result_imports.find_one_and_update(
            {"_id": import_id, "revision": claimed_receipt["revision"], "status": "MAPPING"},
            {
                "$set": {"status": "NEEDS_MAPPING", "updated_at": now()},
                "$inc": {"revision": 1},
            },
        )
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    remaining = [item for index, item in enumerate(unresolved) if index != payload.unresolved_index]
    updated_receipt = await database.value.junit_result_imports.find_one_and_update(
        {"_id": import_id, "revision": claimed_receipt["revision"], "status": "MAPPING"},
        {
            "$set": {
                "unresolved": remaining,
                "status": "NEEDS_MAPPING" if remaining else "IMPORTED",
                "updated_at": timestamp,
            },
            "$push": {"mapped_test_case_version_ids": payload.test_case_version_id},
            "$inc": {"revision": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not updated_receipt:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(
        user.id,
        "junit_result_mapping_resolved",
        "JUnitResultImport",
        import_id,
        receipt["project_id"],
        {"test_case_version_id": payload.test_case_version_id},
    )
    return updated_receipt
