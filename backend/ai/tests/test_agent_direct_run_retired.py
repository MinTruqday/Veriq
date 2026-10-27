import unittest

from fastapi import HTTPException

from src.api.agents import create_agent_run
from src.schemas.agent import AgentRunRequest
from src.schemas.auth import CurrentUser


class DirectAgentRunRetiredTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_agent_run_is_rejected_and_event_workflow_is_named(self):
        payload = AgentRunRequest(
            project_id="project-1",
            objective="Analyze the latest requirement",
        )
        user = CurrentUser(_id="user-1", email="user@example.test")

        with self.assertRaises(HTTPException) as error:
            await create_agent_run(payload, "Bearer token", user)

        self.assertEqual(error.exception.status_code, 410)
        self.assertEqual(error.exception.detail["code"], "DIRECT_AGENT_RUN_RETIRED")
        self.assertEqual(
            error.exception.detail["replacement"],
            "tu-dong-hoa-ai/noi-bo/su-kien",
        )


if __name__ == "__main__":
    unittest.main()
