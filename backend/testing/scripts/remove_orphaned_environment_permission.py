"""Dry-run or remove the unused environment.secret_ref.manage permission."""

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timezone

from pymongo import MongoClient


PERMISSION = "environment.secret_ref.manage"
ACCESS_ID = "active"


def remove_permission(document):
    updated = deepcopy(document)
    before = {
        "capabilities": sum(
            1 for item in document.get("capabilities", [])
            if item.get("name") == PERMISSION
        ),
        "role_grants": sum(
            1 for grant in document.get("role_grants", [])
            if PERMISSION in (grant.get("permissions") or [])
        ),
        "setting_grants": sum(
            1 for grant in document.get("setting_grants", [])
            if PERMISSION in (grant.get("permissions") or [])
        ),
    }
    updated["capabilities"] = [
        item for item in document.get("capabilities", [])
        if item.get("name") != PERMISSION
    ]
    for field in ("role_grants", "setting_grants"):
        updated[field] = [
            {
                **grant,
                "permissions": [
                    value for value in grant.get("permissions", [])
                    if value != PERMISSION
                ],
            }
            for grant in document.get(field, [])
        ]
    return updated, before


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the removal with revision check and an audit event",
    )
    args = parser.parse_args()
    uri = os.environ.get("MONGODB_URI")
    database_name = os.environ.get("TESTING_DB_NAME")
    if not uri or not database_name:
        parser.error("Set MONGODB_URI and TESTING_DB_NAME in the environment")

    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        db = client[database_name]
        document = db.project_access_control.find_one({"_id": ACCESS_ID})
        if not document:
            parser.error("Active project access policy was not found")
        updated, counts = remove_permission(document)
        if not any(counts.values()):
            print(json.dumps({"mode": "NO_CHANGE", "removed": counts}))
            return
        if not args.apply:
            print(json.dumps({
                "mode": "READ_ONLY_DRY_RUN",
                "previous_revision": document.get("revision"),
                "would_remove": PERMISSION,
                "affected_records": counts,
                "writes_performed": False,
            }, ensure_ascii=False))
            return

        revision = int(document.get("revision", 0))
        updated["revision"] = revision + 1
        timestamp = datetime.now(timezone.utc)
        updated["updated_at"] = timestamp
        event_id = f"MIG-remove-orphaned-environment-permission-v{revision + 1}"
        async_session = client.start_session()
        with async_session as session:
            with session.start_transaction():
                result = db.project_access_control.replace_one(
                    {"_id": ACCESS_ID, "revision": revision},
                    updated,
                    session=session,
                )
                if result.modified_count != 1:
                    parser.error("Access policy revision changed; no migration applied")
                db.audit_events.update_one(
                    {"_id": event_id},
                    {"$setOnInsert": {
                        "actor_id": "SYSTEM_MIGRATION",
                        "action": "orphaned_environment_permission_removed",
                        "entity_type": "ProjectAccessControl",
                        "entity_id": ACCESS_ID,
                        "project_id": None,
                        "created_at": timestamp,
                        "details": {
                            "permission": PERMISSION,
                            "previous_revision": revision,
                            "affected_records": counts,
                        },
                    }},
                    upsert=True,
                    session=session,
                )
        print(json.dumps({
            "mode": "APPLIED",
            "revision": revision + 1,
            "removed": counts,
            "audit_event_id": event_id,
            "writes_performed": True,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
