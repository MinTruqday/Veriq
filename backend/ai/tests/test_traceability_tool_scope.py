import json
import unittest
from unittest.mock import AsyncMock, patch

from src.tools.execution_tools import get_work_item_impact_context
from src.tools.requirement_tools import get_traceability_links


class TraceabilityToolScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_work_item_impact_read_marks_stale_event_as_superseded(self):
        work_item = {
            "_id": "WI-1",
            "project_id": "PRJ-1",
            "revision": 5,
            "requirement_ids": [],
        }
        config = {
            "configurable": {
                "permissions": [
                    "project.read",
                    "requirement.read",
                    "requirement.version.read",
                    "testcase.read",
                ]
            }
        }
        with patch(
            "src.tools.execution_tools.require_operation",
            new=AsyncMock(return_value=work_item),
        ) as read:
            result = await get_work_item_impact_context.ainvoke(
                {
                    "project_id": "PRJ-1",
                    "work_item_id": "WI-1",
                    "expected_revision": 4,
                },
                config,
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "superseded")
        self.assertEqual(payload["reason_code"], "WORK_ITEM_EVENT_REVISION_SUPERSEDED")
        self.assertEqual(payload["current_revision"], 5)
        read.assert_awaited_once()

    async def test_work_item_impact_read_accepts_the_event_revision(self):
        work_item = {
            "_id": "WI-1",
            "project_id": "PRJ-1",
            "revision": 5,
            "requirement_ids": [],
        }
        config = {
            "configurable": {
                "permissions": [
                    "project.read",
                    "requirement.read",
                    "requirement.version.read",
                    "testcase.read",
                ]
            }
        }
        with patch(
            "src.tools.execution_tools.require_operation",
            new=AsyncMock(return_value=work_item),
        ):
            result = await get_work_item_impact_context.ainvoke(
                {
                    "project_id": "PRJ-1",
                    "work_item_id": "WI-1",
                    "expected_revision": 5,
                },
                config,
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["work_item"]["revision"], 5)

    async def test_multiple_requirement_versions_are_encoded_as_repeated_query_parameters(self):
        with patch(
            "src.tools.requirement_tools.call",
            new=AsyncMock(return_value='{"data": {}}'),
        ) as call:
            result = await get_traceability_links.ainvoke(
                {
                    "project_id": "PRJ-1",
                    "requirement_version_ids": ["REQV/1", "REQV-2"],
                },
                {"configurable": {"testing_service_url": "http://testing"}},
            )

        self.assertEqual(result, '{"data": {}}')
        self.assertEqual(
            call.await_args.args[:2],
            (
                "GET",
                "/du-an/PRJ-1/truy-vet?requirement_version_ids=REQV%2F1&requirement_version_ids=REQV-2",
            ),
        )
        self.assertEqual(call.await_args.args[2]["configurable"]["testing_service_url"], "http://testing")


if __name__ == "__main__":
    unittest.main()
