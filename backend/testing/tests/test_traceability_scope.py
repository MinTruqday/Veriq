import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.quality.services.traceability import (
    TraceabilityService,
    scope_traceability_matrix,
)


class TraceabilityScopeTests(unittest.IsolatedAsyncioTestCase):
    def test_scopes_matrix_to_baseline_and_directly_linked_test_versions(self):
        matrix = {
            "requirements": [{"_id": "REQ-1"}, {"_id": "REQ-2"}],
            "requirement_versions": [
                {"_id": "REQV-1", "requirement_id": "REQ-1"},
                {"_id": "REQV-2", "requirement_id": "REQ-2"},
            ],
            "acceptance_criteria": [
                {"_id": "AC-1", "requirement_version_id": "REQV-1"},
                {"_id": "AC-2", "requirement_version_id": "REQV-2"},
            ],
            "test_cases": [{"_id": "TC-1"}, {"_id": "TC-2"}],
            "test_case_versions": [
                {"_id": "TCV-1", "test_case_id": "TC-1"},
                {"_id": "TCV-2", "test_case_id": "TC-2"},
            ],
            "trace_links": [
                {
                    "_id": "TL-1",
                    "source_type": "requirement_version",
                    "source_id": "REQV-1",
                    "target_type": "test_case_version",
                    "target_id": "TCV-1",
                    "status": "CONFIRMED",
                },
                {
                    "_id": "TL-2",
                    "source_type": "requirement_version",
                    "source_id": "REQV-2",
                    "target_type": "test_case_version",
                    "target_id": "TCV-2",
                    "status": "CONFIRMED",
                },
                {
                    "_id": "TL-stale",
                    "source_type": "requirement_version",
                    "source_id": "REQV-1",
                    "target_type": "test_case_version",
                    "target_id": "TCV-2",
                    "status": "STALE",
                },
            ],
            "defects": [{"_id": "DEF-1"}],
        }

        scoped = scope_traceability_matrix(matrix, "REQV-1")

        self.assertEqual([item["_id"] for item in scoped["requirements"]], ["REQ-1"])
        self.assertEqual([item["_id"] for item in scoped["requirement_versions"]], ["REQV-1"])
        self.assertEqual([item["_id"] for item in scoped["acceptance_criteria"]], ["AC-1"])
        self.assertEqual([item["_id"] for item in scoped["test_cases"]], ["TC-1"])
        self.assertEqual([item["_id"] for item in scoped["test_case_versions"]], ["TCV-1"])
        self.assertEqual([item["_id"] for item in scoped["trace_links"]], ["TL-1"])
        self.assertEqual(scoped["defects"], [])

    async def test_multi_version_scope_loads_history_and_filters_links_before_limit(self):
        captured = {}

        async def list_records(collection, query, limit, *args):
            if collection == "requirements":
                return [
                    {
                        "_id": "REQ-1",
                        "project_id": "P-1",
                        "current_version_id": "REQV-current",
                    }
                ]
            if collection == "requirement_versions":
                ids = query.get("_id", {}).get("$in", [])
                return [
                    {"_id": value, "project_id": "P-1", "requirement_id": "REQ-1"}
                    for value in ids
                    if value in {"REQV-current", "REQV-old"}
                ]
            if collection == "acceptance_criteria":
                captured["criteria_query"] = query
                version_ids = query.get("requirement_version_id", {}).get("$in", [])
                return (
                    [
                        {
                            "_id": "AC-old",
                            "project_id": "P-1",
                            "requirement_version_id": "REQV-old",
                        }
                    ]
                    if "REQV-old" in version_ids
                    else []
                )
            if collection == "trace_links":
                captured["trace_query"] = query
                return [
                    {
                        "_id": "TL-old",
                        "project_id": "P-1",
                        "source_type": "acceptance_criterion",
                        "source_id": "AC-old",
                        "target_type": "test_case_version",
                        "target_id": "TCV-old",
                        "status": "CONFIRMED",
                    }
                ]
            if collection == "test_case_versions" and "_id" in query:
                version_ids = query.get("_id", {}).get("$in", [])
                return (
                    [
                        {
                            "_id": "TCV-old",
                            "project_id": "P-1",
                            "test_case_id": "TC-old",
                        }
                    ]
                    if "TCV-old" in version_ids
                    else []
                )
            return []

        user = SimpleNamespace(id="qa-1")
        with (
            patch(
                "src.modules.quality.services.traceability.get_project",
                new=AsyncMock(return_value={"_id": "P-1"}),
            ),
            patch(
                "src.modules.quality.services.traceability.get_project_role",
                new=AsyncMock(return_value="QA"),
            ),
            patch(
                "src.modules.quality.services.traceability.traceability_repository.list_records",
                new=AsyncMock(side_effect=list_records),
            ),
        ):
            result = await TraceabilityService.matrix(
                "P-1", user, requirement_version_ids=["REQV-old"]
            )

        self.assertEqual(
            [item["_id"] for item in result["requirement_versions"]], ["REQV-old"]
        )
        self.assertEqual([item["_id"] for item in result["trace_links"]], ["TL-old"])
        self.assertEqual(
            captured["trace_query"]["source_id"]["$in"], ["REQV-old", "AC-old"]
        )

    async def test_scoped_traceability_refuses_an_overflowing_acceptance_criteria_scope(self):
        async def list_records(collection, query, limit, *args):
            if collection == "requirements":
                return [{"_id": "REQ-1", "project_id": "P-1", "current_version_id": "REQV-1"}]
            if collection == "requirement_versions":
                return [{"_id": "REQV-1", "project_id": "P-1", "requirement_id": "REQ-1"}]
            if collection == "acceptance_criteria":
                return [
                    {"_id": f"AC-{index}", "project_id": "P-1", "requirement_version_id": "REQV-1"}
                    for index in range(limit)
                ]
            return []

        with (
            patch(
                "src.modules.quality.services.traceability.get_project",
                new=AsyncMock(return_value={"_id": "P-1"}),
            ),
            patch(
                "src.modules.quality.services.traceability.get_project_role",
                new=AsyncMock(return_value="QA"),
            ),
            patch(
                "src.modules.quality.services.traceability.traceability_repository.list_records",
                new=AsyncMock(side_effect=list_records),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await TraceabilityService.matrix(
                    "P-1", SimpleNamespace(id="qa-1"), requirement_version_id="REQV-1"
                )

        self.assertEqual(raised.exception.status_code, 413)
        self.assertEqual(
            raised.exception.detail["code"], "TRACEABILITY_SCOPE_TOO_LARGE"
        )

    def test_rejects_a_baseline_outside_the_matrix(self):
        with self.assertRaises(HTTPException) as raised:
            scope_traceability_matrix({"requirement_versions": []}, "REQV-missing")

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail["code"], "ENTITY_NOT_FOUND")

    def test_scopes_multiple_requirement_versions_and_acceptance_criterion_links(self):
        matrix = {
            "requirements": [{"_id": "REQ-1"}, {"_id": "REQ-2"}, {"_id": "REQ-3"}],
            "requirement_versions": [
                {"_id": "REQV-1", "requirement_id": "REQ-1"},
                {"_id": "REQV-2", "requirement_id": "REQ-2"},
                {"_id": "REQV-3", "requirement_id": "REQ-3"},
            ],
            "acceptance_criteria": [
                {"_id": "AC-1", "requirement_version_id": "REQV-1"},
                {"_id": "AC-2", "requirement_version_id": "REQV-2"},
                {"_id": "AC-3", "requirement_version_id": "REQV-3"},
            ],
            "test_cases": [{"_id": "TC-1"}, {"_id": "TC-2"}, {"_id": "TC-3"}],
            "test_case_versions": [
                {"_id": "TCV-1", "test_case_id": "TC-1"},
                {"_id": "TCV-2", "test_case_id": "TC-2"},
                {"_id": "TCV-3", "test_case_id": "TC-3"},
            ],
            "trace_links": [
                {
                    "source_type": "acceptance_criterion", "source_id": "AC-1",
                    "target_type": "test_case_version", "target_id": "TCV-1", "status": "CONFIRMED",
                },
                {
                    "source_type": "requirement_version", "source_id": "REQV-2",
                    "target_type": "test_case_version", "target_id": "TCV-2", "status": "SUGGESTED",
                },
                {
                    "source_type": "requirement_version", "source_id": "REQV-3",
                    "target_type": "test_case_version", "target_id": "TCV-3", "status": "CONFIRMED",
                },
            ],
            "defects": [],
        }

        scoped = scope_traceability_matrix(matrix, ["REQV-2", "REQV-1", "REQV-2"])

        self.assertEqual(
            [item["_id"] for item in scoped["requirement_versions"]], ["REQV-2", "REQV-1"]
        )
        self.assertEqual(
            {item["_id"] for item in scoped["test_case_versions"]}, {"TCV-1", "TCV-2"}
        )
        self.assertEqual(len(scoped["trace_links"]), 2)

    def test_rejects_a_multi_scope_request_if_any_version_is_missing(self):
        with self.assertRaises(HTTPException) as raised:
            scope_traceability_matrix(
                {"requirement_versions": [{"_id": "REQV-1", "requirement_id": "REQ-1"}]},
                ["REQV-1", "REQV-missing"],
            )

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
