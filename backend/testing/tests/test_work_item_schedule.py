import unittest
from datetime import datetime, timezone

from fastapi import HTTPException

from src.modules.projects.services.work_items import _validate_planned_dates
from src.modules.projects.services.project import _validate_project_dates
from src.schemas.contracts.project import WorkItemCreate, WorkItemPatch, WorkItemType


class WorkItemScheduleTests(unittest.TestCase):
    def test_create_contract_accepts_optional_schedule(self):
        item = WorkItemCreate(item_type=WorkItemType.TASK, title="Chuẩn bị phát hành")
        self.assertIsNone(item.planned_start_at)
        self.assertIsNone(item.planned_end_at)

    def test_patch_contract_exposes_schedule_fields(self):
        patch = WorkItemPatch(
            expected_revision=1,
            planned_start_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
            planned_end_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        self.assertEqual(
            set(patch.model_dump(exclude_unset=True))
            & {"planned_start_at", "planned_end_at"},
            {"planned_start_at", "planned_end_at"},
        )

    def test_valid_range_and_partial_range_are_allowed(self):
        _validate_planned_dates(
            datetime(2026, 10, 20, tzinfo=timezone.utc),
            datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        _validate_planned_dates(datetime(2026, 10, 20, tzinfo=timezone.utc), None)

    def test_equal_or_reversed_range_is_rejected(self):
        for start, end in (
            (datetime(2026, 10, 20), datetime(2026, 10, 20)),
            (datetime(2026, 10, 21), datetime(2026, 10, 20)),
        ):
            with self.subTest(start=start, end=end):
                with self.assertRaises(HTTPException) as raised:
                    _validate_planned_dates(start, end)
                self.assertEqual(raised.exception.status_code, 422)
                self.assertEqual(raised.exception.detail["code"], "WORK_ITEM_SCHEDULE_INVALID")

    def test_timezone_mismatch_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            _validate_planned_dates(
                datetime(2026, 10, 20),
                datetime(2026, 10, 21, tzinfo=timezone.utc),
            )
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            raised.exception.detail["code"], "WORK_ITEM_SCHEDULE_TIMEZONE_MISMATCH"
        )

    def test_project_schedule_rejects_end_not_after_start(self):
        with self.assertRaises(HTTPException) as raised:
            _validate_project_dates(
                datetime(2026, 10, 24, tzinfo=timezone.utc),
                datetime(2026, 10, 24, tzinfo=timezone.utc),
            )
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["code"], "PROJECT_SCHEDULE_INVALID")

    def test_project_schedule_accepts_open_ended_and_ordered_dates(self):
        _validate_project_dates(datetime(2026, 10, 24, tzinfo=timezone.utc), None)
        _validate_project_dates(
            datetime(2026, 10, 24, tzinfo=timezone.utc),
            datetime(2026, 10, 25, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
