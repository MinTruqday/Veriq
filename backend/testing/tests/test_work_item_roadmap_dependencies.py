import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.projects.services.work_items import WorkItemService


class _Cursor:
    def __init__(self, values):
        self.values = values

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return self.values[:length] if length is not None else self.values


class _Collection:
    def __init__(self, values):
        self.values = values

    def find(self, *args, **kwargs):
        return _Cursor(self.values)


class WorkItemRoadmapDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_roadmap_resolves_dependency_endpoints_to_item_names_and_types(self):
        dependencies = [
            {
                "_id": "DEP-1",
                "project_id": "PRJ-1",
                "source_item_id": "WI-1",
                "target_item_id": "WI-2",
                "dependency_type": "BLOCKS",
            }
        ]
        database = SimpleNamespace(
            value=SimpleNamespace(
                releases=_Collection([]),
                work_items=_Collection(
                    [
                        {"_id": "WI-1", "title": "Chuẩn bị dữ liệu", "item_type": "EPIC"},
                        {"_id": "WI-2", "title": "Chạy hồi quy", "item_type": "TASK"},
                    ]
                ),
            )
        )
        with (
            patch(
                "src.modules.projects.services.work_items._project_planning",
                new=AsyncMock(return_value={"planning_method": "SCRUM"}),
            ),
            patch(
                "src.modules.projects.services.work_items.work_item_repository.list_items",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.modules.projects.services.work_items.work_item_repository.list_dependencies",
                new=AsyncMock(return_value=dependencies),
            ),
            patch("src.modules.projects.services.work_items.database", database),
        ):
            roadmap = await WorkItemService.roadmap("PRJ-1", object())

        self.assertEqual(
            roadmap["dependencies"],
            [
                {
                    **dependencies[0],
                    "source_item_title": "Chuẩn bị dữ liệu",
                    "source_item_type": "EPIC",
                    "target_item_title": "Chạy hồi quy",
                    "target_item_type": "TASK",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
