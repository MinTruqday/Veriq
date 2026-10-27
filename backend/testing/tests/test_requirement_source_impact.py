import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.requirements.services import requirement_documents


class RequirementSourceImpactTests(unittest.IsolatedAsyncioTestCase):
    async def test_reports_only_artifacts_linked_to_documents_in_the_same_series(self):
        user = SimpleNamespace(id="member-1")
        source = {
            "_id": "DOC-2",
            "project_id": "PROJECT-1",
            "source_series_id": "SERIES-1",
            "source_version": "2",
            "source_version_sequence": 2,
            "previous_source_version_id": "DOC-1",
        }
        versions = [
            {
                "_id": "DOC-1",
                "source_series_id": "SERIES-1",
                "source_version": "1",
                "source_version_sequence": 1,
                "previous_source_version_id": None,
                "content_hash": "hash-1",
                "status": "READY",
            },
            {
                **source,
                "content_hash": "hash-2",
                "status": "UPLOADED",
            },
        ]
        requirement_versions = [
            {
                "_id": "REQV-1",
                "requirement_id": "REQ-1",
                "version": 1,
                "status": "SUPERSEDED",
                "source_refs": [{"requirement_document_id": "DOC-1"}],
            },
            {
                "_id": "REQV-2",
                "requirement_id": "REQ-1",
                "version": 2,
                "status": "APPROVED",
                "source_refs": [{"requirement_document_id": "DOC-2"}],
            },
        ]
        cases = [
            {
                "_id": "TC-1",
                "test_case_key": "VERIQ-T1",
                "current_version_id": "TCV-1",
                "current_version": {"requirement_version_ids": ["REQV-2"]},
            }
        ]
        case_versions = [
            {
                "_id": "TCV-1",
                "test_case_id": "TC-1",
                "version": 1,
                "status": "APPROVED",
                "requirement_version_ids": ["REQV-2"],
            }
        ]
        with (
            patch.object(
                requirement_documents,
                "get_requirement_document_record",
                new=AsyncMock(return_value=source),
            ),
            patch.object(requirement_documents, "get_project", new=AsyncMock()) as get_project,
            patch.object(
                requirement_documents,
                "require_document_access",
                new=AsyncMock(side_effect=lambda value, *_args: value),
            ) as check_source_access,
            patch.object(
                requirement_documents.requirement_document_repository,
                "list_source_series",
                new=AsyncMock(return_value=versions),
            ) as list_series,
            patch.object(
                requirement_documents.requirement_repository,
                "list_versions_by_source_documents",
                new=AsyncMock(return_value=requirement_versions),
            ) as list_requirement_versions,
            patch.object(
                requirement_documents.test_design_repository,
                "list_cases_linked_to_requirement",
                new=AsyncMock(return_value=cases),
            ) as list_cases,
            patch.object(
                requirement_documents.test_design_repository,
                "list_case_versions_linked_to_requirements",
                new=AsyncMock(return_value=case_versions),
            ) as list_case_versions,
            patch.object(
                requirement_documents.test_design_repository,
                "list_cases_by_ids",
                new=AsyncMock(return_value=cases),
            ) as list_case_records,
        ):
            result = await requirement_documents.get_requirement_source_impact(
                "DOC-2", user
            )

        get_project.assert_awaited_once_with("PROJECT-1", user, "requirement.read")
        self.assertEqual(check_source_access.await_count, 2)
        list_series.assert_awaited_once_with("PROJECT-1", "SERIES-1")
        list_requirement_versions.assert_awaited_once_with(
            "PROJECT-1", ["DOC-1", "DOC-2"]
        )
        list_cases.assert_awaited_once_with("PROJECT-1", ["REQV-1", "REQV-2"])
        list_case_versions.assert_awaited_once_with("PROJECT-1", ["REQV-1", "REQV-2"])
        list_case_records.assert_awaited_once_with("PROJECT-1", ["TC-1"])
        self.assertEqual(result["latest_document_id"], "DOC-2")
        self.assertEqual(result["impact_status"], "HAS_DOWNSTREAM_ARTIFACTS")
        self.assertEqual(
            result["affected_requirements"],
            [
                {
                    "requirement_id": "REQ-1",
                    "requirement_version_ids": ["REQV-1", "REQV-2"],
                }
            ],
        )
        self.assertEqual(
            result["affected_requirement_versions"][0]["requirement_version_id"],
            "REQV-1",
        )
        self.assertNotIn("source_refs", result["affected_requirement_versions"][0])
        self.assertEqual(result["affected_test_cases"][0]["test_case_id"], "TC-1")

    async def test_reports_no_downstream_artifacts_without_inventing_impact(self):
        user = SimpleNamespace(id="member-1")
        source = {
            "_id": "DOC-1",
            "project_id": "PROJECT-1",
            "source_version": "1",
            "source_version_sequence": 1,
            "content_hash": "hash-1",
            "previous_source_version_id": None,
        }
        with (
            patch.object(
                requirement_documents,
                "get_requirement_document_record",
                new=AsyncMock(return_value=source),
            ),
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(
                requirement_documents,
                "require_document_access",
                new=AsyncMock(side_effect=lambda value, *_args: value),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "list_source_series",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_documents.requirement_repository,
                "list_versions_by_source_documents",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_documents.test_design_repository,
                "list_cases_linked_to_requirement",
                new=AsyncMock(return_value=[]),
            ) as list_cases,
            patch.object(
                requirement_documents.test_design_repository,
                "list_case_versions_linked_to_requirements",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_documents.test_design_repository,
                "list_cases_by_ids",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await requirement_documents.get_requirement_source_impact(
                "DOC-1", user
            )

        list_cases.assert_awaited_once_with("PROJECT-1", [])
        self.assertEqual(result["source_versions"][0]["document_id"], "DOC-1")
        self.assertEqual(result["affected_requirement_versions"], [])
        self.assertEqual(result["affected_test_cases"], [])
        self.assertEqual(result["impact_status"], "NO_DOWNSTREAM_ARTIFACTS")

    async def test_fails_closed_for_broken_source_version_chain(self):
        from fastapi import HTTPException

        user = SimpleNamespace(id="member-1")
        source = {
            "_id": "DOC-2",
            "project_id": "PROJECT-1",
            "source_series_id": "SERIES-1",
            "source_version": "2",
            "source_version_sequence": 2,
            "previous_source_version_id": "DOC-1",
            "content_hash": "hash-2",
        }
        broken_versions = [
            {
                "_id": "DOC-1",
                "project_id": "PROJECT-1",
                "source_series_id": "SERIES-1",
                "source_version": "1",
                "source_version_sequence": 1,
                "previous_source_version_id": None,
                "content_hash": "hash-1",
            },
            {**source, "previous_source_version_id": "UNRELATED-DOC"},
        ]
        with (
            patch.object(
                requirement_documents,
                "get_requirement_document_record",
                new=AsyncMock(return_value=source),
            ),
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(
                requirement_documents,
                "require_document_access",
                new=AsyncMock(side_effect=lambda value, *_args: value),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "list_source_series",
                new=AsyncMock(return_value=broken_versions),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.get_requirement_source_impact(
                    "DOC-2", user
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "SOURCE_VERSION_LINEAGE_INVALID"
        )


if __name__ == "__main__":
    unittest.main()
