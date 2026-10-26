import unittest

from src.modules.design.services.linters import requirement_findings


class RequirementFindingsTests(unittest.TestCase):
    def findings_by_rule(self, business_rules, acceptance_criteria):
        version = {
            "title": "Yêu cầu có nguồn kiểm chứng",
            "plain_text_projection": "Hành vi được mô tả trong nguồn.",
            "actors": ["Người dùng"],
            "business_rules": business_rules,
        }
        return {
            finding["rule_id"]: finding
            for finding in requirement_findings(version, acceptance_criteria)
        }

    def test_acceptance_criteria_can_satisfy_behavior_gate_when_rule_field_is_absent(self):
        findings = self.findings_by_rule(
            [],
            [{"key": "AC-1", "plain_text": "Khi nhập đúng dữ liệu, hệ thống chấp nhận."}],
        )

        self.assertEqual(findings["MISSING_BUSINESS_RULE"]["severity"], "warning")
        self.assertNotIn("MISSING_ACCEPTANCE_CRITERIA", findings)

    def test_business_rule_can_satisfy_behavior_gate_when_acceptance_criteria_is_absent(self):
        findings = self.findings_by_rule(
            ["Khi nhập đúng dữ liệu, hệ thống chấp nhận."],
            [],
        )

        self.assertEqual(findings["MISSING_ACCEPTANCE_CRITERIA"]["severity"], "warning")
        self.assertNotIn("MISSING_BUSINESS_RULE", findings)

    def test_missing_both_behavior_sources_remains_blocking(self):
        findings = self.findings_by_rule([], [])

        self.assertEqual(findings["MISSING_BUSINESS_RULE"]["severity"], "error")
        self.assertEqual(findings["MISSING_ACCEPTANCE_CRITERIA"]["severity"], "error")

    def test_missing_actor_metadata_is_visible_but_does_not_block_grounded_behavior(self):
        version = {
            "title": "Đăng nhập",
            "plain_text_projection": "Người dùng đăng nhập bằng thông tin hợp lệ.",
            "actors": [],
            "business_rules": ["Mật khẩu không khớp thì từ chối đăng nhập."],
        }

        findings = {
            finding["rule_id"]: finding
            for finding in requirement_findings(
                version,
                [{"key": "AC-1", "plain_text": "Thông tin hợp lệ thì cho phép truy cập."}],
            )
        }

        self.assertEqual(findings["MISSING_ACTOR"]["severity"], "warning")
        self.assertNotIn("MISSING_BUSINESS_RULE", findings)
        self.assertNotIn("MISSING_ACCEPTANCE_CRITERIA", findings)


if __name__ == "__main__":
    unittest.main()
