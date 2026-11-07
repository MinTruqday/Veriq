import unittest
from types import SimpleNamespace

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


if __name__ == "__main__":
    unittest.main()
