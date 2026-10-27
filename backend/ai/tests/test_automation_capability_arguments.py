import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.schemas.automation import AutomationKind, AutomationRunRequest
from src.services.automation import AutomationService


class AutomationCapabilityArgumentTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_capability_runs_are_rejected_before_persistence_or_queueing(self):
        payload = AutomationRunRequest(
            project_id="project-1",
            objective="Read the authorized project artifact",
            intent="get_requirement",
            intent_arguments={"requirement_id": "REQ-1"},
            kind=AutomationKind.ON_DEMAND,
        )
        service = AutomationService()
        with (
            patch(
                "src.services.automation.automation_repository.create_run_with_checkpoint",
                new=AsyncMock(),
            ) as create_run,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.create(payload, "qa-1", "QA", ["requirement.read"])

        self.assertEqual(error.exception.status_code, 410)
        self.assertEqual(error.exception.detail["code"], "DIRECT_AUTOMATION_RUN_RETIRED")
        create_run.assert_not_awaited()
        publish.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
