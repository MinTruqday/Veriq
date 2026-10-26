import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.projects.services.work_items import _validate_dependency_cycle


class WorkItemDependencyCycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_cycle_is_detected_across_more_than_the_old_page_limit(self):
        dependencies = [
            {
                "source_item_id": f"ITEM-{index + 1}",
                "target_item_id": f"ITEM-{index}",
                "dependency_type": "BLOCKS",
            }
            for index in range(0, 2_101)
        ]
        dependencies.append(
            {
                "source_item_id": "TARGET",
                "target_item_id": "ITEM-2101",
                "dependency_type": "BLOCKS",
            }
        )
        with patch(
            "src.modules.projects.services.work_items.work_item_repository.list_dependencies",
            new=AsyncMock(return_value=dependencies),
        ) as list_dependencies:
            with self.assertRaises(HTTPException) as raised:
                await _validate_dependency_cycle(
                    "PRJ-1", "ITEM-0", "TARGET", dependency_type="BLOCKS"
                )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["code"], "WORK_ITEM_DEPENDENCY_CYCLE")
        list_dependencies.assert_awaited_once_with("PRJ-1", session=None)

    async def test_non_cyclic_dependency_path_is_allowed(self):
        dependencies = [
            {
                "source_item_id": "ITEM-B",
                "target_item_id": "ITEM-A",
                "dependency_type": "BLOCKS",
            }
        ]
        with patch(
            "src.modules.projects.services.work_items.work_item_repository.list_dependencies",
            new=AsyncMock(return_value=dependencies),
        ):
            await _validate_dependency_cycle(
                "PRJ-1", "ITEM-C", "ITEM-B", dependency_type="BLOCKS"
            )

    async def test_relates_to_does_not_create_a_directed_cycle(self):
        with patch(
            "src.modules.projects.services.work_items.work_item_repository.list_dependencies",
            new=AsyncMock(side_effect=AssertionError("RELATES_TO is not a directed dependency")),
        ):
            await _validate_dependency_cycle(
                "PRJ-1", "ITEM-A", "ITEM-B", dependency_type="RELATES_TO"
            )


if __name__ == "__main__":
    unittest.main()
