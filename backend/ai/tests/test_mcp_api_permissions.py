import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.api.mcp import _connection_response, list_mcp_call_audits, list_mcp_connections
from src.repositories.mcp import MCPRepository
from src.schemas.auth import CurrentUser
from src.schemas.mcp import MCPConnection


class MCPReadAPIPermissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = CurrentUser(_id="user-1", email="user@example.test")
        self.access = patch(
            "src.services.project_access.project_access", new_callable=AsyncMock
        )
        self.audits = patch(
            "src.api.mcp.mcp_repository.list_call_audits", new_callable=AsyncMock
        )
        self.connections = patch(
            "src.api.mcp.mcp_repository.list_project", new_callable=AsyncMock
        )
        self.access_mock = self.access.start()
        self.audits_mock = self.audits.start()
        self.connections_mock = self.connections.start()
        self.audits_mock.return_value = []
        self.connections_mock.return_value = []
        self.addCleanup(self.access.stop)
        self.addCleanup(self.audits.stop)
        self.addCleanup(self.connections.stop)

    async def test_project_member_without_read_permission_cannot_read_audits(self):
        self.access_mock.return_value = ("Tester", ["automation.read"])

        with self.assertRaises(HTTPException) as raised:
            await list_mcp_call_audits("project-1", "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail["code"], "PROJECT_READ_FORBIDDEN")
        self.audits_mock.assert_not_awaited()

    async def test_project_read_permission_allows_scoped_audit_history(self):
        self.access_mock.return_value = ("Viewer", ["project.read"])

        await list_mcp_call_audits("project-1", "token", self.user)

        self.audits_mock.assert_awaited_once_with(
            "project-1",
            limit=100,
            automation_run_id=None,
            task_id=None,
        )

    async def test_project_read_permission_can_filter_audits_to_one_run_and_task(self):
        self.access_mock.return_value = ("Viewer", ["project.read"])

        await list_mcp_call_audits(
            "project-1",
            "token",
            self.user,
            automation_run_id="run-1",
            task_id="task-1",
            limit=25,
        )

        self.audits_mock.assert_awaited_once_with(
            "project-1",
            limit=25,
            automation_run_id="run-1",
            task_id="task-1",
        )

    async def test_invalid_audit_filters_are_rejected_before_repository_read(self):
        self.access_mock.return_value = ("QA", ["project.read"])

        with self.assertRaises(HTTPException) as raised:
            await list_mcp_call_audits(
                "project-1", "token", self.user, task_id=" "
            )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["code"], "MCP_AUDIT_TASK_FILTER_INVALID")
        self.audits_mock.assert_not_awaited()

    async def test_repository_filters_audits_inside_the_project_scope(self):
        cursor = SimpleNamespace()
        cursor.sort = lambda *_args: cursor
        cursor.to_list = AsyncMock(return_value=[])
        collection = SimpleNamespace(find=lambda query: self.record_query(query, cursor))
        database = SimpleNamespace(
            mongodb={"test-db": SimpleNamespace(mcp_tool_call_audits=collection)}
        )
        repository = MCPRepository()

        with (
            patch("src.repositories.mcp.database", database),
            patch("src.repositories.mcp.settings.AI_DB_NAME", "test-db"),
        ):
            result = await repository.list_call_audits(
                "project-1",
                limit=20,
                automation_run_id="run-1",
                task_id="task-1",
            )

        self.assertEqual(result, [])
        self.assertEqual(
            self.captured_query,
            {
                "project_id": "project-1",
                "automation_run_id": "run-1",
                "task_id": "task-1",
            },
        )
        cursor.to_list.assert_awaited_once_with(length=20)

    def record_query(self, query, cursor):
        self.captured_query = query
        return cursor

    async def test_project_member_without_read_permission_cannot_list_connections(self):
        self.access_mock.return_value = ("Tester", [])

        with self.assertRaises(HTTPException) as raised:
            await list_mcp_connections("project-1", "token", self.user)

        self.assertEqual(raised.exception.status_code, 403)
        self.connections_mock.assert_not_awaited()

    async def test_project_read_permission_allows_listing_connections(self):
        self.access_mock.return_value = ("QA", ["project.read"])

        await list_mcp_connections("project-1", "token", self.user)

        self.connections_mock.assert_awaited_once_with("project-1")

    def test_connection_response_hides_legacy_url_credentials_and_query(self):
        connection = MCPConnection(
            connection_id="connection-1",
            project_id="project-1",
            name="External MCP",
            endpoint="https://user:secret@mcp.example/server?token=private#fragment",
            credential_environment_variable="MCP_EXTERNAL_TOKEN",
            allowed_read_tools=["read"],
            created_by="admin-1",
        )

        response = _connection_response(connection)

        self.assertEqual(response["endpoint"], "https://mcp.example/server")
        self.assertNotIn("credential_environment_variable", response)
        self.assertNotIn("secret", str(response))
        self.assertNotIn("private", str(response))
