"""Read-only inventory of legacy fields that need review before cleanup."""

import argparse
import json
import os
from collections import Counter
from pymongo import MongoClient

SAMPLE_LIMIT = 100


def has_content(value):
    if isinstance(value, dict):
        if "content" in value:
            return any(has_content(child) for child in value.get("content") or [])
        if value.get("text"):
            return True
        return any(has_content(child) for child in value.values())
    if isinstance(value, list):
        return any(has_content(child) for child in value)
    return bool(value)


def record_ref(row):
    return {
        "id": row.get("_id"),
        "project_id": row.get("project_id"),
        "title": row.get("title") or row.get("name"),
    }


def inventory_case_collection(collection, project_id):
    query = {"project_id": project_id} if project_id else {}
    projection = {"_id": 1, "project_id": 1, "title": 1, "test_data": 1, "expected_result_doc": 1}
    counts = Counter()
    samples = {"test_data": [], "expected_result_doc": []}
    for row in collection.find(query, projection, batch_size=1000):
        for field in samples:
            if has_content(row.get(field)):
                counts[field] += 1
                if len(samples[field]) < SAMPLE_LIMIT:
                    samples[field].append(record_ref(row))
    return {"counts": dict(counts), "sample_ids": samples}


def inventory_environment_collection(collection, project_id):
    query = {"project_id": project_id} if project_id else {}
    projection = {
        "_id": 1, "project_id": 1, "name": 1, "environment_type": 1,
        "capabilities": 1, "secret_refs": 1,
    }
    counts = Counter()
    samples = {"environment_type": [], "capabilities": [], "secret_refs": []}
    for row in collection.find(query, projection, batch_size=1000):
        for field in samples:
            if has_content(row.get(field)):
                counts[field] += 1
                if len(samples[field]) < SAMPLE_LIMIT:
                    samples[field].append(record_ref(row))
    return {"counts": dict(counts), "sample_ids": samples}


def inventory_closed_periods(collection, project_id):
    query = {"status": "CLOSED"}
    if project_id:
        query["project_id"] = project_id
    projection = {"_id": 1, "project_id": 1, "name": 1, "close_summary": 1}
    count = 0
    samples = []
    for row in collection.find(query, projection, batch_size=1000):
        if row.get("close_summary"):
            continue
        count += 1
        if len(samples) < SAMPLE_LIMIT:
            samples.append(record_ref(row))
    return {"closed_without_snapshot": count, "sample_ids": samples}


def inventory_access_policy(collection):
    access = collection.find_one({"_id": "active"}) or {}
    supported_roles = {"BA", "TESTER", "SYSTEM_ADMIN"}
    roles = Counter(grant.get("role") for grant in access.get("role_grants", []))
    unsupported_roles = sorted(role for role in roles if role and role not in supported_roles)
    capabilities = sorted(
        item.get("name")
        for item in access.get("capabilities", [])
        if isinstance(item, dict) and item.get("name")
    )
    return {
        "revision": access.get("revision"),
        "unsupported_role_grants": unsupported_roles,
        "legacy_environment_permission_present": "environment.secret_ref.manage" in capabilities,
        "capability_count": len(capabilities),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default="", help="Limit project-scoped inventories")
    args = parser.parse_args()
    uri = os.environ.get("MONGODB_URI")
    database_name = os.environ.get("TESTING_DB_NAME")
    if not uri or not database_name:
        parser.error("Set MONGODB_URI and TESTING_DB_NAME in the environment")

    with MongoClient(uri, readPreference="secondaryPreferred", serverSelectionTimeoutMS=5000) as client:
        db = client[database_name]
        report = {
            "mode": "READ_ONLY_DRY_RUN",
            "project_filter": args.project_id or None,
            "test_case_drafts": inventory_case_collection(db.test_case_drafts, args.project_id),
            "test_case_versions": inventory_case_collection(db.test_case_versions, args.project_id),
            "environments": inventory_environment_collection(db.test_environments, args.project_id),
            "closed_periods": inventory_closed_periods(db.test_periods, args.project_id),
            "project_access": inventory_access_policy(db.project_access_control),
            "note": "No documents are changed. Samples are limited to 100 IDs per field; counts include all matching records.",
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
