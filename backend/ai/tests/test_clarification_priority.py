import unittest
from unittest.mock import AsyncMock, patch

from src.tools.testing import plan_clarification_priority


class ClarificationPriorityTests(unittest.IsolatedAsyncioTestCase):
    async def test_persisted_obligation_quote_links_only_the_exact_unresolved_source(self):
        version = {"_id": "REQV-1"}
        clarifications = [
            {
                "_id": "RCL-1",
                "question": "Quy tắc nào áp dụng?",
                "status": "OPEN",
                "unlocks_obligation_keys": ["obligation-1"],
                "unlocks_source_quotes": ["Tài khoản đã đăng ký có thể đăng nhập."],
            }
        ]
        assessment = {
            "coverage_items": [
                {
                    "coverage_item_id": "COV-1",
                    "source_quote": "Tài khoản đã đăng ký có thể đăng nhập.",
                    "status": "UNASSESSED",
                },
                {
                    "coverage_item_id": "COV-2",
                    "source_quote": "Tài khoản chưa đăng ký không thể đăng nhập.",
                    "status": "UNASSESSED",
                },
                {
                    "coverage_item_id": "COV-3",
                    "source_quote": "Tài khoản khác có thể đăng nhập.",
                    "status": "VERIFIED_COVERED",
                },
            ]
        }

        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(return_value=assessment),
        ):
            result = await plan_clarification_priority(version, clarifications, {})

        self.assertEqual(result[0]["unlocks_coverage_item_ids"], ["COV-1"])
        self.assertEqual(result[0]["unlock_count"], 1)

    async def test_legacy_clarification_does_not_fuzzy_match_quote_substrings(self):
        version = {"_id": "REQV-1"}
        clarifications = [
            {
                "_id": "RCL-1",
                "question": "Quy tắc nào áp dụng?",
                "status": "OPEN",
                "source_quote": "Người dùng có thể đăng nhập",
            }
        ]
        assessment = {
            "coverage_items": [
                {
                    "coverage_item_id": "COV-1",
                    "source_quote": "Người dùng có thể đăng nhập bằng tài khoản đã kích hoạt.",
                    "status": "UNASSESSED",
                }
            ]
        }

        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(return_value=assessment),
        ):
            result = await plan_clarification_priority(version, clarifications, {})

        self.assertEqual(result[0]["unlocks_coverage_item_ids"], [])
        self.assertEqual(result[0]["unlock_count"], 0)
