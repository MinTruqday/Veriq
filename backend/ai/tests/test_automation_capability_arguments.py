import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.schemas.automation import AutomationKind, AutomationRunRequest
from src.schemas.mcp import MCPConnection
from src.services.automation import AutomationService


class AutomationCapabilityArgumentTests(unittest.IsolatedAsyncioTestCase):
    def request(self, tool_name="getAuthenticatedUser"):
        return AutomationRunRequest(
            project_id="project-1",
            objective="Read authenticated Postman connection status without exposing account details",
            intent="call_mcp_read_tool",
            intent_arguments={
                "connection_id": "postman-1",
                "tool_name": tool_name,
                "arguments": {},
            },
            kind=AutomationKind.ON_DEMAND,
        )

    def connection(self, *, project_id=None, allowed=("getAuthenticatedUser",)):
        return MCPConnection(
            connection_id="postman-1",
            project_id=project_id,
            name="Postman",
            endpoint="https://mcp.postman.com/mcp",
            credential_environment_variable="MCP_POSTMAN_API_KEY",
            allowed_read_tools=list(allowed),
            created_by="qa-1",
        )

    async def test_allowlisted_project_or_global_mcp_arguments_are_queued(self):
        service = AutomationService()
        with (
            patch("src.services.automation.mcp_repository.get", new=AsyncMock(return_value=self.connection())),
            patch(
                "src.services.automation.automation_repository.create_run_with_checkpoint",
                new=AsyncMock(side_effect=lambda run, **_: run),
            ) as create_run,
            patch("src.services.automation.mq.publish", new=AsyncMock(return_value=True)),
        ):
            run = await service.create(self.request(), "qa-1", "QA", ["project.read"])

        self.assertEqual(run.intent_arguments["connection_id"], "postman-1")
        self.assertEqual(run.intent_arguments["tool_name"], "getAuthenticatedUser")
        create_run.assert_awaited_once()

    async def test_non_allowlisted_mcp_tool_is_rejected_before_run_creation(self):
        service = AutomationService()
        with (
            patch("src.services.automation.mcp_repository.get", new=AsyncMock(return_value=self.connection())),
            patch("src.services.automation.automation_repository.create_run_with_checkpoint", new=AsyncMock()) as create_run,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.create(self.request("deleteCollection"), "qa-1", "QA", ["project.read"])

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail["code"], "MCP_TOOL_SCOPE_OR_ALLOWLIST_DENIED")
        create_run.assert_not_awaited()
        publish.assert_not_awaited()

    async def test_project_scoped_connection_cannot_be_used_from_another_project(self):
        service = AutomationService()
        with (
            patch("src.services.automation.mcp_repository.get", new=AsyncMock(return_value=self.connection(project_id="project-2"))),
            patch("src.services.automation.automation_repository.create_run_with_checkpoint", new=AsyncMock()) as create_run,
            patch("src.services.automation.mq.publish", new=AsyncMock()) as publish,
        ):
            with self.assertRaises(HTTPException) as error:
                await service.create(self.request(), "qa-1", "QA", ["project.read"])

        self.assertEqual(error.exception.detail["code"], "MCP_TOOL_SCOPE_OR_ALLOWLIST_DENIED")
        create_run.assert_not_awaited()
        publish.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
