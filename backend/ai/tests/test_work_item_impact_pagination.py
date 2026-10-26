import unittest
from unittest.mock import AsyncMock, patch

from src.tools.execution_tools import list_all_requirement_test_cases
from src.tools.testing_api import AutomationOperationError


class WorkItemImpactPaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_every_page_and_preserves_the_complete_result_set(self):
        first = {
            "items": [
                {"_id": f"TC-{index}", "project_id": "PRJ-1"}
                for index in range(1, 501)
            ],
            "page": 1,
            "page_size": 500,
            "total": 501,
            "total_pages": 2,
        }
        second = {
            "items": [{"_id": "TC-501", "project_id": "PRJ-1"}],
            "page": 2,
            "page_size": 500,
            "total": 501,
            "total_pages": 2,
        }
        with patch(
            "src.tools.execution_tools.require_operation",
            new=AsyncMock(side_effect=[first, second]),
        ) as request:
            cases = await list_all_requirement_test_cases(
                "PRJ-1", "REQ-1", {"configurable": {}}
            )

        self.assertEqual(len(cases), 501)
        self.assertEqual(cases[0]["_id"], "TC-1")
        self.assertEqual(cases[-1]["_id"], "TC-501")
        self.assertEqual(request.await_count, 2)
        self.assertIn("page=1&page_size=500", request.await_args_list[0].args[1])
        self.assertIn("page=2&page_size=500", request.await_args_list[1].args[1])

    async def test_rejects_changed_page_metadata_instead_of_reporting_partial_impact(self):
        first = {
            "items": [
                {"_id": f"TC-{index}", "project_id": "PRJ-1"}
                for index in range(1, 501)
            ],
            "page": 1,
            "page_size": 500,
            "total": 501,
            "total_pages": 2,
        }
        second = {
            "items": [{"_id": "TC-2", "project_id": "PRJ-1"}],
            "page": 2,
            "page_size": 500,
            "total": 502,
            "total_pages": 2,
        }
        with patch(
            "src.tools.execution_tools.require_operation",
            new=AsyncMock(side_effect=[first, second]),
        ):
            with self.assertRaises(AutomationOperationError) as raised:
                await list_all_requirement_test_cases(
                    "PRJ-1", "REQ-1", {"configurable": {}}
                )

        self.assertEqual(
            raised.exception.reason_code, "WORK_ITEM_IMPACT_PAGINATION_CHANGED"
        )

    async def test_rejects_duplicate_or_cross_project_rows(self):
        response = {
            "items": [
                {"_id": "TC-1", "project_id": "PRJ-1"},
                {"_id": "TC-1", "project_id": "PRJ-1"},
            ],
            "page": 1,
            "page_size": 500,
            "total": 2,
            "total_pages": 1,
        }
        with patch(
            "src.tools.execution_tools.require_operation",
            new=AsyncMock(return_value=response),
        ):
            with self.assertRaises(AutomationOperationError) as raised:
                await list_all_requirement_test_cases(
                    "PRJ-1", "REQ-1", {"configurable": {}}
                )

        self.assertEqual(
            raised.exception.reason_code, "WORK_ITEM_IMPACT_PAGINATION_INCOMPLETE"
        )

    async def test_rejects_the_testing_query_service_result_ceiling(self):
        response = {
            "items": [],
            "page": 1,
            "page_size": 500,
            "total": 20000,
            "total_pages": 40,
        }
        with patch(
            "src.tools.execution_tools.require_operation",
            new=AsyncMock(return_value=response),
        ):
            with self.assertRaises(AutomationOperationError) as raised:
                await list_all_requirement_test_cases(
                    "PRJ-1", "REQ-1", {"configurable": {}}
                )

        self.assertEqual(
            raised.exception.reason_code, "WORK_ITEM_IMPACT_RESULT_LIMIT_REACHED"
        )


if __name__ == "__main__":
    unittest.main()
