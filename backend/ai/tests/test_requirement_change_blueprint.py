import json
import unittest
from unittest.mock import AsyncMock, patch

from src.schemas.automation import AutomationFact
from src.services.testability_blueprint import (
    obligations_supported_by_requirement_version,
    requirement_version_source_text,
)
from src.tools.requirement_change_workflow import (
    assess_changed_requirement_quality,
    finalized_generation_warnings,
    list_all_impact_proposals,
    process_changed_requirement_version,
    requirement_quality_allows_automatic_publication,
    requirement_version_source_facts,
)
from src.tools.test_case_deduplication import consolidate_duplicate_test_case_drafts
from src.tools.testing import list_all_test_case_records
from src.tools.testing_api import AutomationOperationError


class RequirementChangeBlueprintTests(unittest.TestCase):
    def test_confirmed_duplicates_keep_one_case_and_merge_source_trace(self):
        drafts = [
            {
                "title": "Đăng nhập thành công",
                "acceptance_criterion_ids": ["AC-1"],
                "coverage_obligations": ["login-valid"],
                "evidence_refs": ["REQV-1"],
                "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "Thông tin hợp lệ"}],
                "source_evidence": [{"artifact_version_id": "REQV-1", "text": "Thông tin hợp lệ"}],
            },
            {
                "title": "Đăng nhập bằng thông tin hợp lệ",
                "acceptance_criterion_ids": ["AC-2"],
                "coverage_obligations": ["registered-user"],
                "evidence_refs": ["REQV-1"],
                "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "Tài khoản đã đăng ký"}],
                "source_evidence": [{"artifact_version_id": "REQV-1", "text": "Tài khoản đã đăng ký"}],
            },
        ]

        result, skipped, unresolved = consolidate_duplicate_test_case_drafts(
            drafts, [{"left_index": 0, "right_index": 1}]
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(skipped, 1)
        self.assertEqual(unresolved, [])
        self.assertEqual(set(result[0]["acceptance_criterion_ids"]), {"AC-1", "AC-2"})
        self.assertEqual(set(result[0]["coverage_obligations"]), {"login-valid", "registered-user"})
        self.assertEqual(len(result[0]["evidence_quotes"]), 2)
        self.assertEqual(len(result[0]["source_evidence"]), 2)

    def test_duplicate_merge_deduplicates_exact_source_evidence_only(self):
        evidence = {
            "artifact_version_id": "REQV-1",
            "chunk_id": "chunk-1",
            "text": "Tài khoản phải tồn tại.",
        }
        drafts = [
            {"title": "Kiểm tra tài khoản", "source_evidence": [evidence]},
            {
                "title": "Kiểm tra tài khoản hợp lệ",
                "source_evidence": [dict(evidence), {**evidence, "chunk_id": "chunk-2"}],
            },
        ]

        merged, skipped, unresolved = consolidate_duplicate_test_case_drafts(
            drafts, [{"left_index": 0, "right_index": 1}]
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(skipped, 1)
        self.assertEqual(unresolved, [])
        self.assertEqual(
            {item["chunk_id"] for item in merged[0]["source_evidence"]},
            {"chunk-1", "chunk-2"},
        )

    def test_non_transitive_duplicate_matches_are_not_merged_as_one_case(self):
        drafts = [{"title": "A"}, {"title": "B"}, {"title": "C"}]

        merged, skipped, unresolved = consolidate_duplicate_test_case_drafts(
            drafts,
            [
                {"left_index": 0, "right_index": 1},
                {"left_index": 1, "right_index": 2},
            ],
        )

        self.assertEqual(merged, [])
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(
            unresolved[0]["reason"], "DUPLICATE_RELATIONSHIP_NOT_TRANSITIVE"
        )
        self.assertEqual(unresolved[0]["candidate_indexes"], [0, 1, 2])

    def test_invalid_duplicate_comparison_fails_closed(self):
        drafts = [{"title": "A"}, {"title": "B"}]

        for comparison in (
            {"left_index": -1, "right_index": 1},
            {"left_index": 0, "right_index": 2},
            {"left_index": 0, "right_index": 0},
            {"left_index": True, "right_index": 1},
            {"left_index": "0", "right_index": 1},
            None,
        ):
            with self.subTest(comparison=comparison):
                merged, skipped, unresolved = consolidate_duplicate_test_case_drafts(
                    drafts, [comparison]
                )

                self.assertEqual(merged, [])
                self.assertEqual(skipped, 0)
                self.assertEqual(
                    unresolved[0]["reason"], "DUPLICATE_COMPARISON_INDEX_INVALID"
                )


    def test_duplicate_maintenance_targets_are_not_merged_automatically(self):
        drafts = [
            {"target_version_id": "TCV-1", "coverage_obligations": ["a"]},
            {"target_version_id": "TCV-2", "coverage_obligations": ["b"]},
        ]

        result, skipped, unresolved = consolidate_duplicate_test_case_drafts(
            drafts, [{"left_index": 0, "right_index": 1}]
        )

        self.assertEqual(result, [])
        self.assertEqual(skipped, 1)
        self.assertEqual(unresolved[0]["reason"], "DUPLICATE_MAINTENANCE_TARGET_CONFLICT")

    def test_successful_focused_retry_does_not_report_resolved_case_cap_warning(self):
        warnings = [
            ["MODEL_NOTE: first generation needed a focused retry"],
            ["MODEL_NOTE: output was shortened"],
        ]

        finalized = finalized_generation_warnings(warnings, coverage_complete=True)

        self.assertEqual(finalized, ["MODEL_NOTE: output was shortened"])

    def test_unresolved_coverage_keeps_case_cap_warning(self):
        warning = "Maximum cases limit (1) reached; obligation login-invalid was not covered"

        finalized = finalized_generation_warnings(
            [[warning], ["FOCUSED_GENERATION_EMPTY"]], coverage_complete=False
        )

        self.assertEqual(finalized, [warning, "FOCUSED_GENERATION_EMPTY"])

    def test_saved_requirement_sentences_have_exact_version_spans(self):
        version = {
            "_id": "REQV-1",
            "title": "MFA bắt buộc khi đăng nhập",
            "plain_text_projection": "Người dùng đăng nhập. Mật khẩu phải hợp lệ.",
        }

        facts, evidence = requirement_version_source_facts(version)

        self.assertEqual(
            [fact.quote for fact in facts],
            [
                "MFA bắt buộc khi đăng nhập",
                "Người dùng đăng nhập.",
                "Mật khẩu phải hợp lệ.",
            ],
        )
        for fact in facts:
            self.assertEqual(
                evidence[fact.artifact_version_id]["text"][fact.source_start : fact.source_end],
                fact.quote,
            )

    def test_saved_requirement_facts_include_acceptance_rules_and_api_details(self):
        version = {
            "_id": "REQV-1",
            "plain_text_projection": "Người dùng đăng nhập.",
            "acceptance_criteria": [
                {"_id": "AC-1", "key": "AC-1", "plain_text": "Mã xác thực hết hạn sau 5 phút."}
            ],
            "business_rules": ["Tài khoản bị khóa sau 3 lần sai."],
            "details": {
                "api_operations": [{"operation_id": "POST /login", "response": "401 khi sai mã"}]
            },
        }

        facts, evidence = requirement_version_source_facts(version)
        quotes = {fact.quote for fact in facts}
        source_text = evidence["REQV-1"]["text"]

        self.assertIn("Mã xác thực hết hạn sau 5 phút.", quotes)
        self.assertIn("Tài khoản bị khóa sau 3 lần sai.", quotes)
        self.assertIn("POST /login", source_text)
        for fact in facts:
            self.assertEqual(source_text[fact.source_start : fact.source_end], fact.quote)

    def test_event_facts_are_rebound_only_after_exact_readback_verification(self):
        version = {"_id": "REQV-1", "plain_text_projection": "Người dùng đăng nhập bằng email."}
        valid = AutomationFact(
            artifact_type="requirement_version",
            artifact_id="REQ-1",
            artifact_version_id="REQV-1",
            source="event",
            authority="project",
            quote="đăng nhập bằng email",
        )
        forged = valid.model_copy(update={"quote": "bắt buộc xác thực MFA"})

        facts, evidence = requirement_version_source_facts(version, [valid, forged])

        rebound = next(fact for fact in facts if fact.quote == valid.quote)
        self.assertEqual(rebound.artifact_id, "REQV-1")
        self.assertEqual(
            evidence["REQV-1"]["text"][rebound.source_start : rebound.source_end], valid.quote
        )
        self.assertNotIn(forged.quote, [fact.quote for fact in facts])

    def test_blueprint_obligation_must_quote_the_current_saved_version(self):
        version = {
            "_id": "REQV-1",
            "plain_text_projection": "Người dùng đăng nhập bằng mật khẩu hợp lệ.",
            "source_refs": [],
        }
        evidence = {"REQV-1": {"artifact_id": "REQV-1", "text": version["plain_text_projection"]}}
        obligations = [
            {
                "key": "login-valid",
                "source_ref": "REQV-1",
                "source_quote": "Người dùng đăng nhập bằng mật khẩu hợp lệ.",
                "obligation": "Kiểm tra đăng nhập bằng mật khẩu hợp lệ.",
            }
        ]

        supported, unsupported = obligations_supported_by_requirement_version(
            version, obligations, evidence
        )

        self.assertEqual(supported, obligations)
        self.assertEqual(unsupported, [])

    def test_business_rule_obligation_is_supported_by_saved_requirement_version(self):
        version = {
            "_id": "REQV-1",
            "plain_text_projection": "Người dùng đăng nhập.",
            "business_rules": ["Tài khoản bị khóa sau 3 lần sai."],
            "source_refs": [],
        }
        evidence = {
            "REQV-1": {"artifact_id": "REQV-1", "text": requirement_version_source_text(version)}
        }
        obligations = [
            {
                "key": "lockout",
                "source_ref": "REQV-1",
                "source_quote": "Tài khoản bị khóa sau 3 lần sai.",
                "obligation": "Kiểm tra khóa tài khoản sau số lần sai được nêu.",
            }
        ]

        supported, unsupported = obligations_supported_by_requirement_version(
            version, obligations, evidence
        )

        self.assertEqual(supported, obligations)
        self.assertEqual(unsupported, [])

    def test_blueprint_cannot_claim_a_quote_absent_from_saved_version(self):
        version = {
            "_id": "REQV-1",
            "plain_text_projection": "Người dùng đăng nhập.",
            "source_refs": [],
        }
        obligations = [
            {
                "key": "invented-limit",
                "source_ref": "REQV-1",
                "source_quote": "Mật khẩu dài ít nhất 12 ký tự.",
                "obligation": "Kiểm tra độ dài mật khẩu.",
            }
        ]

        supported, unsupported = obligations_supported_by_requirement_version(
            version, obligations, {}
        )

        self.assertEqual(supported, [])
        self.assertEqual([item["key"] for item in unsupported], ["invented-limit"])


class RequirementChangeAutomationTests(unittest.IsolatedAsyncioTestCase):
    def test_requirement_quality_gate_blocks_invalid_degraded_or_blocking_results(self):
        self.assertTrue(
            requirement_quality_allows_automatic_publication(
                {
                    "status": "SUCCESS",
                    "valid": True,
                    "degraded_mode": False,
                    "blocking_finding_count": 0,
                }
            )
        )
        for assessment in (
            {
                "status": "SUCCESS",
                "valid": False,
                "degraded_mode": False,
                "blocking_finding_count": 0,
            },
            {
                "status": "DEGRADED",
                "valid": True,
                "degraded_mode": True,
                "blocking_finding_count": 0,
            },
            {
                "status": "SUCCESS",
                "valid": True,
                "degraded_mode": False,
                "blocking_finding_count": 1,
            },
        ):
            with self.subTest(assessment=assessment):
                self.assertFalse(requirement_quality_allows_automatic_publication(assessment))

    async def test_changed_requirement_quality_failure_stops_before_baseline_or_generation(self):
        version = {
            "_id": "REQV-1",
            "project_id": "project-1",
            "requirement_id": "REQ-1",
            "status": "DRAFT",
            "revision": 1,
            "plain_text_projection": "Người dùng đăng nhập.",
        }
        requirement = {"_id": "REQ-1", "current_version": version}
        permissions = {
            "requirement.read",
            "requirement.review",
            "requirement.version.read",
            "ai.generate_testcase",
            "testcase.create",
            "testcase.read",
            "testcase.lint",
            "testcase.submit_review",
            "ai.run_lint",
            "changeset.create",
            "changeset.review",
            "impact.execute",
            "impact.review",
            "impact.close",
            "ai.run_impact",
            "ai.create_proposal",
            "proposal.read",
        }
        api = AsyncMock(side_effect=[version, requirement, {}])
        quality = {
            "analysis_id": "QUALITY-1",
            "status": "DEGRADED",
            "valid": False,
            "degraded_mode": True,
            "finding_count": 1,
            "blocking_finding_count": 1,
        }

        with (
            patch("src.tools.requirement_change_workflow.require_operation", api),
            patch(
                "src.tools.requirement_change_workflow.compile_testability_blueprint",
                new=AsyncMock(
                    return_value={
                        "status": "SUCCESS",
                        "obligations": [],
                        "evidence_refs": ["REQV-1"],
                    }
                ),
            ),
            patch(
                "src.tools.requirement_change_workflow.resolve_answered_clarifications",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.tools.requirement_change_workflow.assess_changed_requirement_quality",
                new=AsyncMock(return_value=quality),
            ),
        ):
            raw = await process_changed_requirement_version.ainvoke(
                {"project_id": "project-1", "requirement_version_id": "REQV-1"},
                config={"configurable": {"permissions": sorted(permissions)}},
            )

        result = json.loads(raw)
        self.assertEqual(result["reason_code"], "REQUIREMENT_QUALITY_GATE_FAILED")
        self.assertEqual(result["verification"]["status"], "INCOMPLETE")
        self.assertEqual(api.await_count, 3)
        self.assertEqual(
            [call.args[1] for call in api.await_args_list],
            [
                "/phien-ban-yeu-cau/REQV-1",
                "/yeu-cau/REQ-1",
                "/phien-ban-yeu-cau/REQV-1/phieu-lam-ro/tao-tu-ra-soat",
            ],
        )

    async def test_changed_requirement_quality_uses_revision_scoped_idempotency(self):
        version = {"_id": "REQV-1", "revision": 7}
        response = {
            "_id": "AIF-1",
            "project_id": "project-1",
            "artifact_id": "REQV-1",
            "requirement_version_id": "REQV-1",
            "result_type": "REQUIREMENT_QUALITY_ANALYSIS",
            "idempotency_key": "requirement-quality-event:REQV-1:7",
            "status": "SUCCESS",
            "valid": True,
            "degraded_mode": False,
            "findings": [{"severity": "warning"}, {"severity": "error"}],
        }
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new_callable=AsyncMock,
            return_value=response,
        ) as request:
            result = await assess_changed_requirement_quality(
                "project-1", version, {"configurable": {}}
            )

        self.assertEqual(result["analysis_id"], "AIF-1")
        self.assertEqual(result["finding_count"], 2)
        self.assertEqual(result["blocking_finding_count"], 1)
        self.assertNotIn("human_confirmation_required", result)
        request.assert_awaited_once()
        self.assertEqual(request.await_args.args[:2], (
            "POST",
            "/phien-ban-yeu-cau/REQV-1/ai/kiem-tra",
        ))
        self.assertEqual(
            request.await_args.args[3]["idempotency_key"],
            "requirement-quality-event:REQV-1:7",
        )

    async def test_changed_requirement_quality_rejects_cross_project_readback(self):
        response = {
            "_id": "AIF-1",
            "project_id": "other-project",
            "artifact_id": "REQV-1",
            "requirement_version_id": "REQV-1",
            "result_type": "REQUIREMENT_QUALITY_ANALYSIS",
            "idempotency_key": "requirement-quality-event:REQV-1:1",
            "findings": [],
        }
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new_callable=AsyncMock,
            return_value=response,
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "REQUIREMENT_QUALITY_READBACK_INVALID"
            ):
                await assess_changed_requirement_quality(
                    "project-1", {"_id": "REQV-1", "revision": 1}, {}
                )

    async def test_changed_requirement_quality_rejects_missing_revision_before_call(self):
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new_callable=AsyncMock,
        ) as request:
            with self.assertRaisesRegex(
                AutomationOperationError,
                "REQUIREMENT_QUALITY_SOURCE_REVISION_INVALID",
            ):
                await assess_changed_requirement_quality(
                    "project-1", {"_id": "REQV-1", "revision": True}, {}
                )
        request.assert_not_awaited()

    async def test_changed_requirement_quality_rejects_incomplete_analysis_contract(self):
        base = {
            "_id": "AIF-1",
            "project_id": "project-1",
            "artifact_id": "REQV-1",
            "requirement_version_id": "REQV-1",
            "result_type": "REQUIREMENT_QUALITY_ANALYSIS",
            "idempotency_key": "requirement-quality-event:REQV-1:1",
            "status": "SUCCESS",
            "valid": True,
            "degraded_mode": False,
        }
        for response, reason in (
            ({**base, "findings": [None]}, "REQUIREMENT_QUALITY_FINDINGS_INVALID"),
            (
                {**base, "findings": [{"severity": "unknown"}]},
                "REQUIREMENT_QUALITY_FINDINGS_INVALID",
            ),
            (
                {**base, "findings": [], "status": "UNKNOWN"},
                "REQUIREMENT_QUALITY_STATUS_INVALID",
            ),
            (
                {**base, "findings": [], "degraded_mode": None},
                "REQUIREMENT_QUALITY_STATUS_INVALID",
            ),
            (
                {**base, "findings": [], "valid": "true"},
                "REQUIREMENT_QUALITY_STATUS_INVALID",
            ),
        ):
            with self.subTest(reason=reason), patch(
                "src.tools.requirement_change_workflow.require_operation",
                new_callable=AsyncMock,
                return_value=response,
            ):
                with self.assertRaisesRegex(AutomationOperationError, reason):
                    await assess_changed_requirement_quality(
                        "project-1", {"_id": "REQV-1", "revision": 1}, {}
                    )

    async def test_blueprint_failure_stops_requirement_mutations(self):
        version = {
            "_id": "REQV-1",
            "project_id": "project-1",
            "requirement_id": "REQ-1",
            "status": "DRAFT",
            "revision": 1,
            "plain_text_projection": "Người dùng đăng nhập.",
        }
        requirement = {"_id": "REQ-1", "current_version": version}
        permissions = {
            "requirement.read",
            "requirement.review",
            "requirement.version.read",
            "requirement.submit_review",
            "requirement.approve",
            "ai.generate_testcase",
            "testcase.create",
            "testcase.read",
            "testcase.lint",
            "testcase.submit_review",
            "testcase.approve",
            "ai.run_lint",
            "changeset.create",
            "changeset.review",
            "impact.execute",
            "impact.review",
            "impact.close",
            "ai.run_impact",
            "ai.create_proposal",
            "proposal.read",
            "proposal.approve",
        }
        api = AsyncMock(side_effect=[version, requirement])

        with (
            patch("src.tools.requirement_change_workflow.require_operation", api),
            patch(
                "src.tools.requirement_change_workflow.compile_testability_blueprint",
                new=AsyncMock(
                    return_value={"status": "DEGRADED", "reason_codes": ["MODEL_UNAVAILABLE"]}
                ),
            ),
        ):
            raw = await process_changed_requirement_version.ainvoke(
                {"project_id": "project-1", "requirement_version_id": "REQV-1", "source_facts": []},
                config={"configurable": {"permissions": sorted(permissions)}},
            )

        self.assertEqual(
            __import__("json").loads(raw)["reason_code"], "TESTABILITY_BLUEPRINT_COMPILATION_FAILED"
        )
        self.assertEqual(api.await_count, 2)
        self.assertTrue(all(call.args[0] == "GET" for call in api.await_args_list))


class RequirementCasePaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_requirement_case_scope_rejects_invalid_page_size(self):
        with patch(
            "src.tools.testing.require_operation", new_callable=AsyncMock
        ) as request:
            with self.assertRaisesRegex(
                AutomationOperationError, "REQUIREMENT_TEST_CASE_PAGINATION_INVALID"
            ):
                await list_all_test_case_records(
                    "project-1", "requirement-1", {}, page_size=0
                )
        request.assert_not_awaited()

    async def test_requirement_case_scope_reads_every_page(self):
        with patch(
            "src.tools.testing.require_operation",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "items": [{"_id": "TC-1", "project_id": "project-1"}],
                    "page": 1,
                    "page_size": 1,
                    "total": 2,
                    "total_pages": 2,
                    "scope_fingerprint": "stable-scope",
                },
                {
                    "items": [{"_id": "TC-2", "project_id": "project-1"}],
                    "page": 2,
                    "page_size": 1,
                    "total": 2,
                    "total_pages": 2,
                    "scope_fingerprint": "stable-scope",
                },
            ],
        ) as request:
            records = await list_all_test_case_records(
                "project-1", "requirement-1", {}, page_size=1
            )

        self.assertEqual([item["_id"] for item in records], ["TC-1", "TC-2"])
        self.assertEqual(request.await_count, 2)
        self.assertIn("page=2", request.await_args_list[1].args[1])

    async def test_impact_proposal_scope_fails_closed_if_fingerprint_changes(self):
        page = {
            "items": [],
            "total": 2,
            "total_pages": 2,
            "page_size": 1,
        }
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new_callable=AsyncMock,
            side_effect=[
                {**page, "page": 1, "scope_fingerprint": "before"},
                {**page, "page": 2, "scope_fingerprint": "after"},
            ],
        ):
            with self.assertRaisesRegex(
                AutomationOperationError,
                "MAINTENANCE_PROPOSAL_SCOPE_CHANGED_DURING_READ",
            ):
                await list_all_impact_proposals("project-1", "IA-1", {}, page_size=1)

    async def test_requirement_case_scope_fails_closed_when_total_changes(self):
        with patch(
            "src.tools.testing.require_operation",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "items": [{"_id": "TC-1", "project_id": "project-1"}],
                    "page": 1,
                    "page_size": 1,
                    "total": 2,
                    "total_pages": 2,
                    "scope_fingerprint": "stable-scope",
                },
                {
                    "items": [{"_id": "TC-2", "project_id": "project-1"}],
                    "page": 2,
                    "page_size": 1,
                    "total": 3,
                    "total_pages": 3,
                    "scope_fingerprint": "changed-scope",
                },
            ],
        ):
            with self.assertRaisesRegex(
                AutomationOperationError,
                "REQUIREMENT_TEST_CASE_SCOPE_CHANGED_DURING_READ",
            ):
                await list_all_test_case_records(
                    "project-1", "requirement-1", {}, page_size=1
                )

    async def test_requirement_case_scope_requires_complete_pagination_contract(self):
        with patch(
            "src.tools.testing.require_operation",
            new_callable=AsyncMock,
            return_value={
                "items": [{"_id": "TC-1", "project_id": "project-1"}],
                "page": 1,
                "page_size": 1,
                "total": 2,
                "scope_fingerprint": "stable-scope",
            },
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "REQUIREMENT_TEST_CASE_PAGINATION_INVALID"
            ):
                await list_all_test_case_records(
                    "project-1", "requirement-1", {}, page_size=1
                )

    async def test_requirement_case_scope_rejects_short_page_before_final_page(self):
        with patch(
            "src.tools.testing.require_operation",
            new_callable=AsyncMock,
            return_value={
                "items": [],
                "page": 1,
                "page_size": 1,
                "total": 2,
                "total_pages": 2,
                "scope_fingerprint": "stable-scope",
            },
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "REQUIREMENT_TEST_CASE_PAGINATION_INCOMPLETE"
            ):
                await list_all_test_case_records(
                    "project-1", "requirement-1", {}, page_size=1
                )

    async def test_impact_proposal_scope_reads_every_page_and_checks_total(self):
        with patch(
            "src.tools.requirement_change_workflow.require_operation",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "items": [{
                        "_id": "MP-1",
                        "project_id": "project-1",
                        "impact_analysis_id": "IA-1",
                    }],
                    "page": 1,
                    "page_size": 1,
                    "total": 2,
                    "total_pages": 2,
                    "scope_fingerprint": "stable-scope",
                },
                {
                    "items": [{
                        "_id": "MP-2",
                        "project_id": "project-1",
                        "impact_analysis_id": "IA-1",
                    }],
                    "page": 2,
                    "page_size": 1,
                    "total": 2,
                    "total_pages": 2,
                    "scope_fingerprint": "stable-scope",
                },
            ],
        ) as request:
            proposals = await list_all_impact_proposals(
                "project-1", "IA-1", {}, page_size=1
            )

        self.assertEqual([item["_id"] for item in proposals], ["MP-1", "MP-2"])
        self.assertEqual(request.await_count, 2)
        self.assertIn("page=2", request.await_args_list[1].args[1])


if __name__ == "__main__":
    unittest.main()
