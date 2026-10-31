import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.projects.services import attachment as attachment_service
from src.schemas.contracts.requirements import AttachmentCreate


class ExecutionEvidenceAttachmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_execution_evidence_is_registered_against_its_test_result(self):
        payload = AttachmentCreate(
            filename="EV-002.jpg",
            url="users/user-1/images/evidence.jpg",
            item_id="CLOUD-1",
            size=128,
            content_type="image/jpeg",
            artifact_type="test_result",
            artifact_id="TRES-1",
        )
        with (
            patch.object(attachment_service, "get_project", new=AsyncMock()),
            patch.object(
                attachment_service.test_design_repository,
                "artifact_exists",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                attachment_service.test_design_repository,
                "find_active_attachment",
                new=AsyncMock(return_value=None),
            ) as find_attachment,
            patch.object(
                attachment_service.test_design_repository,
                "insert_attachment",
                new=AsyncMock(),
            ),
            patch.object(attachment_service, "audit", new=AsyncMock()),
        ):
            result = await attachment_service.AttachmentService.register(
                "PROJECT-1", payload, SimpleNamespace(id="user-1")
            )

        self.assertEqual(result["artifact_type"], "test_result")
        self.assertEqual(result["artifact_id"], "TRES-1")
        self.assertEqual(result["item_id"], "CLOUD-1")
        find_attachment.assert_awaited_once_with(
            "PROJECT-1", "user-1", payload.url, "ACTIVE", "test_result", "TRES-1"
        )


if __name__ == "__main__":
    unittest.main()
