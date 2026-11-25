"""Read-only inventory of legacy phase values before cycle migration."""

import argparse
import json
import os
import re
from collections import defaultdict
from pymongo import MongoClient


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def load_rows(collection, fields, project_id):
    query = {"project_id": project_id} if project_id else {}
    projection = {field: 1 for field in fields}
    return collection.find(query, projection, batch_size=1000)


def summarize(db, project_id=""):
    plans = load_rows(
        db.test_plans,
        ["project_id", "phase", "test_period_id", "name", "_id"],
        project_id,
    )
    runs = load_rows(
        db.test_runs,
        ["project_id", "phase", "test_period_id", "test_plan_id", "name", "_id"],
        project_id,
    )
    grouped = defaultdict(lambda: {
        "display_values": set(),
        "plans": [],
        "runs": [],
        "plans_count": 0,
        "runs_count": 0,
    })
    missing_phase = {"plans": [], "runs": []}
    scanned = {"plans": 0, "runs": 0}
    linked = {"plans": 0, "runs": 0}
    for kind, rows in (("plans", plans), ("runs", runs)):
        for row in rows:
            scanned[kind] += 1
            if row.get("test_period_id"):
                linked[kind] += 1
                continue
            phase = str(row.get("phase") or "").strip()
            key = normalize(phase)
            if not key:
                missing_phase[kind].append(row["_id"])
                continue
            group = grouped[(row.get("project_id", ""), key)]
            group["display_values"].add(phase)
            group[f"{kind}_count"] += 1
            if len(group[kind]) < 100:
                group[kind].append(row["_id"])
    groups = []
    for (project, normalized), data in sorted(grouped.items()):
        groups.append({
            "project_id": project,
            "normalized_phase": normalized,
            "display_values": sorted(data["display_values"]),
            "plan_count": data["plans_count"],
            "run_count": data["runs_count"],
            "plan_ids": data["plans"][:100],
            "run_ids": data["runs"][:100],
            "requires_human_mapping": True,
        })
    return {
        "mode": "READ_ONLY_DRY_RUN",
        "project_filter": project_id or None,
        "counts": {
            "plans_scanned": scanned["plans"],
            "runs_scanned": scanned["runs"],
            "plans_already_linked": linked["plans"],
            "runs_already_linked": linked["runs"],
            "legacy_phase_groups": len(groups),
            "plans_without_phase": len(missing_phase["plans"]),
            "runs_without_phase": len(missing_phase["runs"]),
        },
        "groups": groups,
        "unmapped_records": {
            "plans_without_phase": missing_phase["plans"][:100],
            "runs_without_phase": missing_phase["runs"][:100],
        },
        "note": "This report never writes or merges records. A matching phase string is only a review candidate, not proof that records belong to one cycle.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default="", help="Limit the read-only scan to one project")
    args = parser.parse_args()
    uri = os.environ.get("MONGODB_URI")
    database_name = os.environ.get("TESTING_DB_NAME")
    if not uri or not database_name:
        parser.error("Set MONGODB_URI and TESTING_DB_NAME in the environment")
    with MongoClient(uri, readPreference="secondaryPreferred", serverSelectionTimeoutMS=5000) as client:
        report = summarize(client[database_name], args.project_id)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
