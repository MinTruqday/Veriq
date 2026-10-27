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

    async def test_work_item_change_during_linked_reads_is_not_reported_as_complete(self):
        original = {
            "_id": "WI-1",
            "project_id": "PRJ-1",
            "revision": 5,
            "requirement_ids": [],
        }
        latest = {**original, "revision": 6}
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
            new=AsyncMock(side_effect=[original, latest]),
        ) as read:
            result = await get_work_item_impact_context.ainvoke(
                {
                    "project_id": "PRJ-1",
                    "work_item_id": "WI-1",
                    "expected_revision": 5,
                },
                config,
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "superseded")
        self.assertEqual(
            payload["reason_code"], "WORK_ITEM_IMPACT_SCOPE_CHANGED_DURING_READ"
        )
        self.assertEqual(read.await_count, 2)

    async def test_requirement_version_change_during_linked_reads_is_not_complete(self):
        work_item = {
            "_id": "WI-1",
            "project_id": "PRJ-1",
            "revision": 5,
            "requirement_ids": ["REQ-1"],
        }
        original_requirement = {
            "_id": "REQ-1",
            "project_id": "PRJ-1",
            "current_version_id": "REQV-1",
            "current_version": {
                "_id": "REQV-1",
                "project_id": "PRJ-1",
                "requirement_id": "REQ-1",
            },
        }
        changed_requirement = {
            **original_requirement,
            "current_version_id": "REQV-2",
            "current_version": {
                "_id": "REQV-2",
                "project_id": "PRJ-1",
                "requirement_id": "REQ-1",
            },
        }
        empty_cases = {
            "items": [],
            "page": 1,
            "page_size": 500,
            "total": 0,
            "total_pages": 0,
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
            new=AsyncMock(
                side_effect=[
                    work_item,
                    original_requirement,
                    empty_cases,
                    work_item,
                    changed_requirement,
                ]
            ),
        ) as read:
            result = await get_work_item_impact_context.ainvoke(
                {
                    "project_id": "PRJ-1",
                    "work_item_id": "WI-1",
                    "expected_revision": 5,
                },
                config,
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "superseded")
        self.assertEqual(
            payload["reason_code"],
            "WORK_ITEM_REQUIREMENT_VERSION_CHANGED_DURING_READ",
        )
        self.assertEqual(payload["expected_requirement_version_id"], "REQV-1")
        self.assertEqual(payload["current_requirement_version_id"], "REQV-2")
        self.assertEqual(read.await_count, 5)

    async def test_test_case_version_change_during_linked_reads_is_not_complete(self):
        work_item = {
            "_id": "WI-1",
            "project_id": "PRJ-1",
            "revision": 5,
            "requirement_ids": ["REQ-1"],
        }
        requirement = {
            "_id": "REQ-1",
            "project_id": "PRJ-1",
            "current_version_id": "REQV-1",
            "current_version": {
                "_id": "REQV-1",
                "project_id": "PRJ-1",
                "requirement_id": "REQ-1",
            },
        }
        listed_case = {
            "_id": "TC-1",
            "project_id": "PRJ-1",
            "current_version_id": "TCV-1",
            "current_version": {
                "_id": "TCV-1",
                "project_id": "PRJ-1",
                "test_case_id": "TC-1",
                "requirement_version_ids": ["REQV-1"],
            },
        }
        changed_case = {
            **listed_case,
            "current_version_id": "TCV-2",
            "current_version": {
                **listed_case["current_version"],
                "_id": "TCV-2",
            },
        }
        listed_cases = {
            "items": [listed_case],
            "page": 1,
            "page_size": 500,
            "total": 1,
            "total_pages": 1,
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
            new=AsyncMock(
                side_effect=[
                    work_item,
                    requirement,
                    listed_cases,
                    work_item,
                    changed_case,
                    requirement,
                ]
            ),
        ) as read:
            result = await get_work_item_impact_context.ainvoke(
                {
                    "project_id": "PRJ-1",
                    "work_item_id": "WI-1",
                    "expected_revision": 5,
                },
                config,
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "superseded")
        self.assertEqual(
            payload["reason_code"],
            "WORK_ITEM_TEST_CASE_VERSION_CHANGED_DURING_READ",
        )
        self.assertEqual(payload["expected_test_case_version_id"], "TCV-1")
        self.assertEqual(payload["current_test_case_version_id"], "TCV-2")
        self.assertEqual(read.await_count, 5)

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
