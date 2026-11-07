import unittest

from src.modules.projects.services.skill_profiles import (
    _minimum_cost_case_assignment,
    _skill_key,
    rank_skill_candidates,
)
from src.schemas.contracts.skill_profile import ConfirmedSkill


class StaffingRecommendationTests(unittest.TestCase):
    def test_skill_matching_normalizes_unicode_case_and_spacing_without_aliases(self):
        self.assertEqual(_skill_key("  ÉQUIPE   QA "), _skill_key("équipe qa"))
        self.assertNotEqual(_skill_key("JS"), _skill_key("JavaScript"))

    def test_skill_proficiency_label_accepts_project_specific_values(self):
        skill = ConfirmedSkill(name="Skill do dự án", level="Bậc chuyên gia nội bộ")
        self.assertEqual(skill.level, "Bậc chuyên gia nội bộ")

    def test_partial_skill_profiles_remain_available_for_gap_review(self):
        required, candidates = rank_skill_candidates(
            [{"user_id": "member-1"}, {"user_id": "member-2"}],
            [
                {"user_id": "member-1", "availability": "AVAILABLE", "skills": [
                    {"name": "Kỹ năng A", "confirmed": True},
                ]},
                {"user_id": "member-2", "availability": "AVAILABLE", "skills": []},
            ],
            {},
            ["Kỹ năng A", "Kỹ năng B"],
        )

        self.assertEqual(required, ["Kỹ năng A", "Kỹ năng B"])
        self.assertEqual([item["user_id"] for item in candidates], ["member-1", "member-2"])
        self.assertEqual(candidates[0]["unmatched_skills"], ["Kỹ năng B"])
        self.assertEqual(candidates[1]["unmatched_skills"], ["Kỹ năng A", "Kỹ năng B"])

    def test_global_assignment_avoids_greedy_case_order_and_balances_load(self):
        result = _minimum_cost_case_assignment(
            ["flexible", "constrained"],
            {
                "flexible": {"member-a": 0, "member-b": 0},
                "constrained": {"member-a": 0},
            },
            {"member-a": 0, "member-b": 0},
        )

        self.assertEqual(result, {"flexible": "member-b", "constrained": "member-a"})

    def test_global_assignment_uses_existing_load_across_all_cases(self):
        result = _minimum_cost_case_assignment(
            ["case-1", "case-2", "case-3"],
            {case_id: {"busy": 0, "available": 0} for case_id in ("case-1", "case-2", "case-3")},
            {"busy": 3, "available": 0},
        )

        self.assertEqual(sum(value == "available" for value in result.values()), 3)


if __name__ == "__main__":
    unittest.main()
