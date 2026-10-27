import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

from src.repositories.mcp import mcp_repository


class MCPAuditRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_marks_only_running_audits_older_than_runtime_deadline(self):
        collection = SimpleNamespace(
            update_many=AsyncMock(return_value=SimpleNamespace(modified_count=2))
        )
        with (
            patch.object(
                type(mcp_repository),
                "_audit_collection",
                new_callable=PropertyMock,
                return_value=collection,
            ),
            patch(
                "src.repositories.mcp.limits",
                SimpleNamespace(task_timeout_seconds=840, message_ack_timeout_seconds=960),
            ),
        ):
            recovered = await mcp_repository.recover_interrupted_call_audits()

        self.assertEqual(recovered, 2)
        selector, update = collection.update_many.await_args.args
        self.assertEqual(selector["status"], "running")
        self.assertLessEqual(
            selector["started_at"]["$lte"],
            datetime.now(timezone.utc) - timedelta(seconds=1800),
        )
        self.assertEqual(update["$set"]["status"], "degraded")
        self.assertEqual(
            update["$set"]["reason_code"],
            "MCP_CALL_INTERRUPTED_DURING_WORKER_RESTART",
        )


if __name__ == "__main__":
    unittest.main()
