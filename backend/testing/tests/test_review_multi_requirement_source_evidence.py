import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.design.services import test_case_review as review


class ReviewMultiRequirementSourceEvidenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.versions = {
            "requirement-v1": {
                "_id": "requirement-v1",
                "requirement_id": "requirement-1",
                "project_id": "project-1",
                "status": "BASELINED",
                "body": "Đăng nhập bằng email",
            },
            "requirement-v2": {
                "_id": "requirement-v2",
                "requirement_id": "requirement-2",
                "project_id": "project-1",
                "status": "BASELINED",
                "body": "Mật khẩu phải còn hiệu lực",
            },
        }
        self.criteria = {
            "requirement-v1": [],
            "requirement-v2": [
                {
                    "_id": "criterion-v2-1",
                    "plain_text": "Tài khoản bị khóa sau số lần đăng nhập thất bại được quy định",
                }
            ],
        }

    async def invoke(self, evidence):
        async def find_version(query, *_args, **_kwargs):
            version = self.versions.get(query["_id"])
            return version if version and version["project_id"] == query["project_id"] else None

        async def find_requirement(query, *_args, **_kwargs):
            version = next(
                (
                    item
                    for item in self.versions.values()
                    if item["requirement_id"] == query["_id"]
                    and item["project_id"] == query["project_id"]
                ),
                None,
            )
            return {"current_version_id": version["_id"]} if version else None

        db = SimpleNamespace(
            requirement_versions=SimpleNamespace(find_one=AsyncMock(side_effect=find_version)),
            requirements=SimpleNamespace(find_one=AsyncMock(side_effect=find_requirement)),
            test_case_versions=SimpleNamespace(find_one=AsyncMock(return_value=None)),
            test_cases=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        )
        draft = {
            "_id": "draft-1",
            "project_id": "project-1",
            "requirement_version_ids": ["requirement-v1", "requirement-v2"],
            "ai_proposal_snapshot": {"source_evidence": evidence},
        }
        with (
            patch.object(review, "database", SimpleNamespace(value=db)),
            patch.object(
                review,
                "list_acceptance_criteria_in_session",
                new=AsyncMock(side_effect=lambda version_id, _session: self.criteria[version_id]),
            ),
            patch.object(
                review,
                "requirement_test_evidence_text",
                side_effect=lambda version: version["body"],
            ),
        ):
            await review.assert_sources_current_in_session(draft, object())

    async def test_evidence_from_each_linked_requirement_is_validated_against_all_sources(self):
        await self.invoke(
            [
                {"artifact_version_id": "requirement-v1", "text": "Đăng nhập bằng email"},
                {
                    "artifact_version_id": "criterion-v2-1",
                    "text": "Tài khoản bị khóa sau số lần đăng nhập thất bại được quy định",
                },
            ]
        )

    async def test_evidence_outside_linked_requirements_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            await self.invoke(
                [{"artifact_version_id": "unlinked-source", "text": "Nguồn không liên kết"}]
            )
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "TEST_CASE_COMPARISON_STALE"
        )
        self.assertIn(
            "SOURCE_EVIDENCE_CHANGED", raised.exception.detail["reasons"]
        )


if __name__ == "__main__":
    unittest.main()
