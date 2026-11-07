import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.api import automation as automation_api
from src.services.agent_evidence import verified_tool_evidence


def evidence_item(
    reference,
    *,
    project_id="project-1",
    source="tool",
    artifact_type="tool_result",
    authority="verified_tool:retrieve_project_evidence",
    text="sanitized result",
):
    return SimpleNamespace(
        artifact_id=reference,
        project_id=project_id,
        source=source,
        artifact_type=artifact_type,
        authority=authority,
        text=text,
    )


class VerifiedToolEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(
            automation_run_id="run-1",
            project_id="project-1",
            result={
                "evidence_refs": ["citation-1", "citation-2"],
                "proposal": {"evidence_refs": ["citation-1"]},
            },
        )
        self.checkpoint = SimpleNamespace(
            state_snapshot=SimpleNamespace(
                run=SimpleNamespace(run_id="run-1", project_id="project-1"),
                evidence=[
                    evidence_item("citation-1"),
                    evidence_item("citation-2"),
                    evidence_item("other-project", project_id="project-2"),
                    evidence_item("unverified", authority="tool:unknown"),
                    evidence_item("document-source", source="document"),
                    evidence_item("empty", text="  "),
                ],
            )
        )

    def test_returns_only_project_scoped_verified_tool_refs_in_proposal(self):
        result = verified_tool_evidence(self.run, self.checkpoint)

        self.assertEqual(
            result,
            [
                {
                    "evidence_ref": "citation-1",
                    "project_id": "project-1",
                    "tool_name": "retrieve_project_evidence",
                    "text": "sanitized result",
                }
            ],
        )

    def test_rejects_checkpoint_from_other_run_or_project(self):
        self.checkpoint.state_snapshot.run.project_id = "project-2"
        self.assertEqual(verified_tool_evidence(self.run, self.checkpoint), [])

    def test_handles_missing_checkpoint(self):
        self.assertEqual(verified_tool_evidence(self.run, None), [])


class AutomationEvidenceApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_returns_tool_evidence_after_read_authorization(self):
        run = SimpleNamespace(
            automation_run_id="run-1",
            project_id="project-1",
            result={
                "evidence_refs": ["citation-1"],
                "proposal": {"evidence_refs": ["citation-1"]},
            },
        )
        checkpoint = SimpleNamespace(
            state_snapshot=SimpleNamespace(
                run=SimpleNamespace(run_id="run-1", project_id="project-1"),
                evidence=[evidence_item("citation-1")],
            )
        )
        with (
            patch.object(automation_api, "_readable_run", new=AsyncMock(return_value=run)) as read_run,
            patch.object(
                automation_api.automation_repository,
                "latest_checkpoint_with_evidence",
                new=AsyncMock(return_value=checkpoint),
            ),
            patch.object(
                automation_api.automation_repository,
                "list_source_facts",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                automation_api.automation_repository,
                "get_receipt",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await automation_api.get_automation_evidence("run-1", "token", None)

        read_run.assert_awaited_once_with("run-1", "token", None)
        self.assertEqual(result["tool_evidence"][0]["evidence_ref"], "citation-1")

    async def test_endpoint_does_not_read_evidence_when_run_access_is_denied(self):
        denied = HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
        with (
            patch.object(automation_api, "_readable_run", new=AsyncMock(side_effect=denied)),
            patch.object(
                automation_api.automation_repository,
                "latest_checkpoint_with_evidence",
                new=AsyncMock(),
            ) as get_checkpoint,
        ):
            with self.assertRaises(HTTPException) as error:
                await automation_api.get_automation_evidence("run-1", "token", None)

        self.assertEqual(error.exception.status_code, 403)
        get_checkpoint.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
