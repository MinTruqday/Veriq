import hashlib
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from src.tools.automation_publication import verified_test_case_publication_readback
from src.tools.requirement_document_workflow import (
    AutomationOperationError,
    authorized_document_version_path,
    blueprint_obligation_is_represented,
    blueprint_source_lineage,
    blocking_blueprint_clarifications,
    blueprint_clarification_source_ids,
    classify_requirement_ingestion_outcome,
    apply_requirement_import_safely,
    existing_requirement_obligation_coverage,
    existing_test_case_supports_obligation,
    focused_requirement_generation_request,
    generated_obligation_evidence_matches,
    generate_grounded_test_case_preview,
    has_conflicting_blueprint_clarification,
    list_all_ai_readable_requirement_documents,
    persist_blueprint_clarifications,
    publish_grounded_requirement,
    publish_grounded_test_case,
    require_project_scoped_sources,
    resolve_existing_obligation_coverage,
    revalidate_compilation_sources,
    requirement_document_synthesis_snapshot,
    requirement_template_source_snapshot_matches,
    requirement_import_has_unresolved_matches,
    resumable_draft_matches_blueprint_scope,
    safe_requirement_import_resolution,
    source_extraction_gaps,
    source_extraction_warnings,
    uncovered_blueprint_obligations,
    unmapped_blueprint_clarifications_after_persistence,
    verified_document_facts,
    verified_requirement_source_citations,
)
from src.tools.testing import list_resumable_ai_test_case_drafts


class RequirementDocumentWorkflowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.obligation = {
            "key": "LOGIN_ACCESS",
            "source_quote": "Khi nhập đúng thông tin, người dùng vào được hệ thống.",
        }

        self.test_case = {
            "_id": "TC-1",
            "project_id": "project-1",
            "status": "ACTIVE",
            "current_version_id": "TCV-1",
        }
        self.test_case_version = {
            "_id": "TCV-1",
            "test_case_id": "TC-1",
            "project_id": "project-1",
            "status": "ACTIVE",
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["Kiểm tra quyền truy cập bằng thông tin hợp lệ"],
            "evidence_refs": ["REQV-1"],
            "source_evidence": [
                {"artifact_version_id": "REQV-1", "text": self.obligation["source_quote"]}
            ],
            "evidence_quotes": [
                {
                    "evidence_ref": "REQV-1",
                    "quote": self.obligation["source_quote"],
                }
            ],
        }

    def test_blueprint_obligation_accepts_a_grounded_subspan_from_the_same_source(self):
        source = "AC-1: Export includes the selected date range."
        quote = "Export includes the selected date range."
        start = source.index(quote)
        end = start + len(quote)
        represented = blueprint_obligation_is_represented(
            {"source_ref": "RDOC-1", "source_quote": source},
            [
                {
                    "source_refs": [
                        {
                            "requirement_document_id": "RDOC-1",
                            "source_quote": quote,
                            "source_start": start,
                            "source_end": end,
                        }
                    ]
                }
            ],
            {"RDOC-1": [{"artifact_id": "RDOC-1", "text": source}]},
        )
        self.assertTrue(represented)

    def test_blueprint_obligation_rejects_an_unrelated_source_span(self):
        source = "AC-1: Export includes the selected date range."
        unrelated = "AC-1"
        represented = blueprint_obligation_is_represented(
            {
                "source_ref": "RDOC-1",
                "source_quote": "Export includes the selected date range.",
            },
            [
                {
                    "source_refs": [
                        {
                            "requirement_document_id": "RDOC-1",
                            "source_quote": unrelated,
                            "source_start": 0,
                            "source_end": len(unrelated),
                        }
                    ]
                }
            ],
            {"RDOC-1": [{"artifact_id": "RDOC-1", "text": source}]},
        )
        self.assertFalse(represented)

    def test_blueprint_obligation_accepts_single_evidence_mapping_from_document_index(self):
        source = "AC-1: Export includes the selected date range."
        quote = "Export includes the selected date range."
        start = source.index(quote)
        end = start + len(quote)
        represented = blueprint_obligation_is_represented(
            {"source_ref": "RDOC-1", "source_quote": source},
            [
                {
                    "source_refs": [
                        {
                            "requirement_document_id": "RDOC-1",
                            "source_quote": quote,
                            "source_start": start,
                            "source_end": end,
                        }
                    ]
                }
            ],
            {"RDOC-1": {"artifact_id": "RDOC-1", "text": source}},
        )
        self.assertTrue(represented)

    def test_ambiguous_requirement_match_blocks_all_automatic_resolutions(self):
        comparisons = [
            {
                "candidate_id": "candidate-exact",
                "matches": [
                    {
                        "match_type": "EXACT",
                        "requirement_id": "REQ-1",
                        "version_id": "REQV-1",
                        "requirement_status": "ACTIVE",
                    }
                ],
            },
            {
                "candidate_id": "candidate-ambiguous",
                "matches": [
                    {
                        "match_type": "SAME_KEY",
                        "requirement_id": "REQ-2",
                        "version_id": "REQV-2",
                        "requirement_status": "ACTIVE",
                    },
                    {
                        "match_type": "SAME_KEY",
                        "requirement_id": "REQ-3",
                        "version_id": "REQV-3",
                        "requirement_status": "ACTIVE",
                    },
                ],
            },
        ]

        self.assertEqual(
            safe_requirement_import_resolution(comparisons[0]),
            (
                "link_source",
                {
                    "match_type": "EXACT",
                    "requirement_id": "REQ-1",
                    "version_id": "REQV-1",
                    "requirement_status": "ACTIVE",
                },
            ),
        )
        self.assertTrue(requirement_import_has_unresolved_matches(comparisons))

    def test_focused_generation_does_not_reinclude_covered_acceptance_criteria(self):
        request = focused_requirement_generation_request(
            {
                "acceptance_criterion_ids": ["AC-1", "AC-2"],
                "max_cases": 2,
                "instruction": "initial",
            },
            set(),
            [{"key": "OBL-1", "source_quote": "The account is locked."}],
        )

        self.assertEqual(request["acceptance_criterion_ids"], [])
        self.assertEqual(request["max_cases"], 1)
        self.assertIn("OBL-1", request["instruction"])

    def test_draft_template_reuse_requires_exact_current_source_snapshot(self):
        document = {
            "_id": "DOC-1",
            "project_id": "project-1",
            "revision": 4,
            "status": "READY",
            "ai_enabled": True,
            "source_version": "3",
            "source_version_sequence": 3,
            "source_series_id": "SERIES-1",
            "previous_source_version_id": "DOC-0",
            "content_hash": "source-hash-4",
            "authority": "APPROVED_SPECIFICATION",
            "source_type": "SRS",
            "format": "pdf",
            "index_status": "INDEXED",
            "normalized_content": "Yêu cầu hiện tại.",
        }
        template = {
            "synthesis": {
                "source_snapshot": {
                    "source_document_ids": ["DOC-1"],
                    "documents": requirement_document_synthesis_snapshot([document]),
                    "templates": {},
                }
            }
        }

        self.assertTrue(
            requirement_template_source_snapshot_matches(
                template, ["DOC-1"], {"DOC-1": document}
            )
        )
        self.assertFalse(
            requirement_template_source_snapshot_matches(
                template, ["DOC-1"], {"DOC-1": {**document, "revision": 5}}
            )
        )
        self.assertFalse(
            requirement_template_source_snapshot_matches(
                template,
                ["DOC-1"],
                {"DOC-1": {**document, "normalized_content": "Yêu cầu đã thay đổi."}},
            )
        )
        self.assertFalse(
            requirement_template_source_snapshot_matches(
                {"synthesis": {}}, ["DOC-1"], {"DOC-1": document}
            )
        )

    def test_incomplete_document_extraction_is_reported_with_bounded_diagnostics(self):
        documents = {
            "DOC-1": {
                "index_status": "DEGRADED",
                "parse_report": {
                    "parser": "docling",
                    "page_count": 20,
                    "unprocessed_block_count": 1,
                    "unprocessed_blocks": [
                        {"page_no": 8, "reason_code": "TABLE_TEXT_NOT_EXTRACTED"}
                    ],
                },
            },
            "DOC-2": {
                "index_status": "INDEXED",
                "parse_report": {
                    "unprocessed_block_count": 0,
                    "unprocessed_blocks_reported": True,
                },
            },
        }

        gaps = source_extraction_gaps(["DOC-1", "DOC-2"], documents)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["document_id"], "DOC-1")
        self.assertEqual(gaps[0]["reason"], "SOURCE_EXTRACTION_INCOMPLETE")
        self.assertEqual(gaps[0]["unprocessed_blocks"][0]["page_no"], 8)

    def test_legacy_source_without_extraction_status_fails_closed(self):
        gaps = source_extraction_gaps(
            ["DOC-1"], {"DOC-1": {"normalized_content": "text"}}
        )

        self.assertEqual(gaps[0]["index_status"], "UNKNOWN")
        self.assertEqual(gaps[0]["reason"], "SOURCE_EXTRACTION_INCOMPLETE")

    def test_legacy_parser_report_without_completeness_field_fails_closed(self):
        gaps = source_extraction_gaps(
            ["DOC-1"],
            {
                "DOC-1": {
                    "index_status": "INDEXED",
                    "parse_report": {"unprocessed_block_count": 0},
                }
            },
        )

        self.assertEqual(gaps[0]["unprocessed_blocks_reported"], False)
        self.assertEqual(gaps[0]["reason"], "SOURCE_EXTRACTION_INCOMPLETE")

    def test_source_extraction_warnings_are_bounded_with_accurate_truncation(self):
        documents = {
            f"DOC-{index}": {
                "parse_report": {
                    "extraction_warnings": [
                        {"page_no": warning_index, "reason_code": "OCR_REVIEW"}
                        for warning_index in range(100)
                    ]
                }
            }
            for index in range(1, 7)
        }

        warnings, truncated = source_extraction_warnings(
            list(documents), documents
        )

        self.assertEqual(len(warnings), 500)
        self.assertTrue(truncated)

        exact_documents = {
            f"DOC-{index}": {
                "parse_report": {
                    "extraction_warnings": [
                        {"page_no": warning_index, "reason_code": "OCR_REVIEW"}
                        for warning_index in range(100)
                    ]
                }
            }
            for index in range(1, 6)
        }
        exact_warnings, exact_truncated = source_extraction_warnings(
            list(exact_documents), exact_documents
        )

        self.assertEqual(len(exact_warnings), 500)
        self.assertFalse(exact_truncated)

    def test_focused_generation_keeps_only_uncovered_acceptance_criteria(self):
        request = focused_requirement_generation_request(
            {"acceptance_criterion_ids": ["AC-1", "AC-2", "AC-3"]},
            {"AC-3"},
            [],
        )

        self.assertEqual(request["acceptance_criterion_ids"], ["AC-3"])
        self.assertEqual(request["max_cases"], 1)

    def test_resumable_draft_coverage_remains_covered_after_focused_pass(self):
        obligations = [
            {"key": "PENDING"},
            {"key": "NEEDS_NEW"},
            {"key": "ALREADY_REUSED"},
        ]

        missing = uncovered_blueprint_obligations(
            obligations,
            [{"coverage_obligations": ["NEWLY_GENERATED"]}],
            {"ALREADY_REUSED": [{"test_case_id": "TC-1"}]},
            {"PENDING"},
        )

        self.assertEqual([item["key"] for item in missing], ["NEEDS_NEW"])

    async def test_requirement_is_auto_published_only_through_review_and_baseline_checks(self):
        responses = [
            {
                "_id": "REQ-1",
                "project_id": "project-1",
                "current_version_id": "REQV-1",
            },
            {
                "_id": "REQV-1",
                "requirement_id": "REQ-1",
                "project_id": "project-1",
                "status": "IN_REVIEW",
                "revision": 2,
            },
            {
                "_id": "REQV-1",
                "status": "BASELINED",
                "revision": 3,
                "requirement_id": "REQ-1",
                "project_id": "project-1",
            },
            {
                "_id": "REQ-1",
                "project_id": "project-1",
                "current_version_id": "REQV-1",
            },
        ]
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ) as operation:
            version = await publish_grounded_requirement(
                "project-1",
                {
                    "_id": "REQ-1",
                    "project_id": "project-1",
                    "current_version_id": "REQV-1",
                },
                {
                    "_id": "REQV-1",
                    "requirement_id": "REQ-1",
                    "project_id": "project-1",
                    "status": "DRAFT",
                    "revision": 1,
                },
                {},
            )
        self.assertEqual(version["status"], "BASELINED")
        self.assertEqual(operation.await_count, 4)
        self.assertEqual(operation.await_args_list[0].args[:2], ("GET", "/yeu-cau/REQ-1"))
        self.assertIn("gui-ra-soat", operation.await_args_list[1].args[1])
        self.assertIn("chot-chuan", operation.await_args_list[2].args[1])
        self.assertEqual(operation.await_args_list[3].args[:2], ("GET", "/yeu-cau/REQ-1"))

    async def test_already_baselined_stale_requirement_version_is_not_reported_as_current(self):
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(return_value={
                "_id": "REQ-1",
                "project_id": "project-1",
                "current_version_id": "REQV-2",
            }),
        ) as operation:
            with self.assertRaisesRegex(AutomationOperationError, "REQUIREMENT_VERSION_SUPERSEDED"):
                await publish_grounded_requirement(
                    "project-1",
                    {
                        "_id": "REQ-1",
                        "project_id": "project-1",
                        "current_version_id": "REQV-1",
                    },
                    {
                        "_id": "REQV-1",
                        "requirement_id": "REQ-1",
                        "project_id": "project-1",
                        "status": "BASELINED",
                    },
                    {},
                )
        operation.assert_awaited_once_with("GET", "/yeu-cau/REQ-1", {})

    async def test_compilation_sources_are_revalidated_before_artifact_writes(self):
        documents = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "source_version_sequence": 1,
                "normalized_content": "Requirement source one.",
                "index_status": "INDEXED",
                "parse_report": {
                    "unprocessed_block_count": 0,
                    "unprocessed_blocks_reported": True,
                },
            },
            "DOC-2": {
                "_id": "DOC-2",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "source_version_sequence": 1,
                "normalized_content": {"text": "Requirement source two."},
                "index_status": "INDEXED",
                "parse_report": {
                    "unprocessed_block_count": 0,
                    "unprocessed_blocks_reported": True,
                },
            },
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": list(documents.values())}),
        ) as operation:
            await revalidate_compilation_sources(
                "project-1", "/du-an/project-1", ["DOC-1", "DOC-2"], documents, {}
            )
        operation.assert_awaited_once()

    async def test_compilation_revalidation_detects_changed_extraction_report(self):
        previous = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "source_version_sequence": 1,
                "normalized_content": "Requirement source.",
                "index_status": "INDEXED",
                "parse_report": {
                    "unprocessed_block_count": 0,
                    "unprocessed_blocks_reported": True,
                },
            }
        }
        changed = dict(previous["DOC-1"])
        changed["index_status"] = "DEGRADED"
        changed["parse_report"] = {"unprocessed_block_count": 1}
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": [changed]}),
        ):
            with self.assertRaises(AutomationOperationError) as raised:
                await revalidate_compilation_sources(
                    "project-1", "/du-an/project-1", ["DOC-1"], previous, {}
                )
        self.assertEqual(
            str(raised.exception), "AI_SOURCE_SNAPSHOT_CHANGED_DURING_COMPILATION"
        )

    async def test_ai_source_enumeration_reads_every_cursor_page(self):
        pages = [
            {
                "items": [
                    {"_id": "DOC-1", "project_id": "project-1", "ai_enabled": True}
                ],
                "next_cursor": "opaque-cursor-1",
            },
            {
                "items": [
                    {"_id": "DOC-2", "project_id": "project-1", "ai_enabled": True}
                ],
                "next_cursor": None,
            },
        ]
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=pages),
        ) as operation:
            documents = await list_all_ai_readable_requirement_documents(
                "project-1", "/du-an/project-1", {}
            )

        self.assertEqual([item["_id"] for item in documents], ["DOC-1", "DOC-2"])
        self.assertEqual(operation.await_count, 2)
        self.assertIn("cursor=opaque-cursor-1", operation.await_args_list[1].args[1])

    async def test_ai_source_enumeration_continues_after_acl_filtered_empty_page(self):
        pages = [
            {"items": [], "next_cursor": "cursor-after-private-page"},
            {
                "items": [
                    {"_id": "DOC-readable", "project_id": "project-1", "ai_enabled": True}
                ],
                "next_cursor": None,
            },
        ]
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=pages),
        ) as operation:
            documents = await list_all_ai_readable_requirement_documents(
                "project-1", "/du-an/project-1", {}
            )

        self.assertEqual([item["_id"] for item in documents], ["DOC-readable"])
        self.assertEqual(operation.await_count, 2)
        self.assertIn(
            "cursor=cursor-after-private-page", operation.await_args_list[1].args[1]
        )

    async def test_ai_source_enumeration_fails_closed_on_duplicate_page_items(self):
        duplicate = {"_id": "DOC-1", "project_id": "project-1"}
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(
                side_effect=[
                    {"items": [duplicate], "next_cursor": "cursor-1"},
                    {"items": [duplicate], "next_cursor": None},
                ]
            ),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_SOURCE_PAGINATION_DUPLICATE"
            ):
                await list_all_ai_readable_requirement_documents(
                    "project-1", "/du-an/project-1", {}
                )

    async def test_compilation_fails_closed_when_source_access_is_revoked(self):
        documents = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "source_version_sequence": 1,
                "normalized_content": "Requirement source.",
            }
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": []}),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION"
            ):
                await revalidate_compilation_sources(
                    "project-1", "/du-an/project-1", ["DOC-1"], documents, {}
                )

    async def test_compilation_rejects_document_list_leaking_another_project(self):
        with self.assertRaisesRegex(
            AutomationOperationError, "AI_SOURCE_PROJECT_SCOPE_INVALID"
        ):
            require_project_scoped_sources(
                "project-1",
                {
                    "items": [
                        {
                            "_id": "DOC-OTHER",
                            "project_id": "project-2",
                            "status": "READY",
                            "ai_enabled": True,
                        }
                    ]
                },
            )

    async def test_compilation_rejects_cross_project_source_during_revalidation(self):
        original = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "normalized_content": "Original project source.",
            }
        }
        leaked = {
            "_id": "DOC-2",
            "project_id": "project-2",
            "status": "READY",
            "ai_enabled": True,
            "source_version": "1",
            "normalized_content": "Foreign project source.",
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": [original["DOC-1"], leaked]}),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_SOURCE_PROJECT_SCOPE_INVALID"
            ):
                await revalidate_compilation_sources(
                    "project-1", "/du-an/project-1", ["DOC-1"], original, {}
                )

    async def test_compilation_fails_closed_when_source_changes_mid_run(self):
        previous = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "source_version_sequence": 1,
                "normalized_content": "Before change.",
            }
        }
        current = {
            **previous["DOC-1"],
            "normalized_content": "After change.",
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": [current]}),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_SOURCE_SNAPSHOT_CHANGED_DURING_COMPILATION"
            ):
                await revalidate_compilation_sources(
                    "project-1", "/du-an/project-1", ["DOC-1"], previous, {}
                )

    async def test_compilation_fails_closed_when_new_source_changes_project_scope(self):
        previous = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "normalized_content": "Original source.",
            }
        }
        current = [
            previous["DOC-1"],
            {
                "_id": "DOC-2",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "normalized_content": "New source added during inference.",
            },
        ]
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": current}),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION"
            ):
                await revalidate_compilation_sources(
                    "project-1", "/du-an/project-1", ["DOC-1"], previous, {}
                )

    async def test_compilation_fails_closed_when_version_lineage_changes_mid_run(self):
        previous = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "revision": 4,
                "source_version": "2",
                "source_version_sequence": 2,
                "source_series_id": "SERIES-1",
                "previous_source_version_id": "DOC-0",
                "normalized_content": "Unchanged version text.",
            }
        }
        current = {
            **previous["DOC-1"],
            "previous_source_version_id": "OTHER-DOC",
            "revision": 5,
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": [current]}),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_SOURCE_SNAPSHOT_CHANGED_DURING_COMPILATION"
            ):
                await revalidate_compilation_sources(
                    "project-1", "/du-an/project-1", ["DOC-1"], previous, {}
                )

    async def test_compilation_fails_closed_when_document_revision_changes_mid_run(self):
        previous = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "status": "READY",
                "ai_enabled": True,
                "revision": 3,
                "source_version": "1",
                "source_version_sequence": 1,
                "normalized_content": "Same visible text.",
            }
        }
        current = {**previous["DOC-1"], "revision": 4}
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={"items": [current]}),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_SOURCE_SNAPSHOT_CHANGED_DURING_COMPILATION"
            ):
                await revalidate_compilation_sources(
                    "project-1", "/du-an/project-1", ["DOC-1"], previous, {}
                )

    async def test_ai_test_case_publication_requires_a_frozen_project_readback(self):
        responses = [
            {
                "_id": "DRAFT-1",
                "project_id": "project-1",
                "status": "IN_REVIEW",
                "revision": 2,
            },
            {
                "data": {
                    "test_case": {
                        "_id": "TC-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "current_version_id": "TCV-2",
                    },
                    "version": {
                        "_id": "TCV-2",
                        "test_case_id": "TC-1",
                        "status": "ACTIVE",
                    },
                },
                "status": "SUCCESS",
            },
        ]
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ) as operation:
            case, version, status = await publish_grounded_test_case(
                "project-1", {"_id": "DRAFT-1", "revision": 1}, {}
            )
        self.assertEqual(case["_id"], "TC-1")
        self.assertEqual(version["_id"], "TCV-2")
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(operation.await_count, 2)
        self.assertEqual(operation.await_args.kwargs["timeout"], 90)

    async def test_ai_test_case_publication_resumes_review_submitted_draft(self):
        draft = {
            "_id": "DRAFT-1",
            "project_id": "project-1",
            "status": "IN_REVIEW",
            "revision": 2,
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["OBL-1"],
            "evidence_refs": ["DOCV-1"],
            "evidence_quotes": [{"evidence_ref": "DOCV-1", "quote": "Nguồn"}],
        }
        final = {
            "test_case": {
                "_id": "TC-1",
                "project_id": "project-1",
                "status": "ACTIVE",
                "current_version_id": "TCV-2",
            },
            "version": {
                "_id": "TCV-2",
                "project_id": "project-1",
                "test_case_id": "TC-1",
                "status": "ACTIVE",
                "requirement_version_ids": ["REQV-1"],
                "coverage_obligations": ["OBL-1"],
                "evidence_refs": ["DOCV-1"],
                "evidence_quotes": [{"evidence_ref": "DOCV-1", "quote": "Nguồn"}],
            },
        }
        operation = AsyncMock(return_value=final)
        with patch("src.tools.automation_publication.require_operation", operation):
            case, version, status = await publish_grounded_test_case(
                "project-1", draft, {}
            )

        self.assertEqual(case["_id"], "TC-1")
        self.assertEqual(version["_id"], "TCV-2")
        self.assertEqual(status, "SUCCESS")
        operation.assert_awaited_once()
        self.assertIn("/DRAFT-1/phe-duyet", operation.await_args.args[1])

    async def test_ai_test_case_publication_recovers_after_approval_response_was_lost(self):
        draft = {
            "_id": "DRAFT-APPROVED",
            "project_id": "project-1",
            "status": "APPROVED",
            "revision": 4,
            "frozen_version_id": "TCV-1",
            "title": "Đăng nhập có căn cứ",
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["LOGIN_ACCESS"],
            "evidence_refs": ["REQV-1"],
            "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "Người dùng đăng nhập."}],
        }
        final = {
            "data": {
                "test_case": {
                    "_id": "TC-1",
                    "project_id": "project-1",
                    "status": "ACTIVE",
                    "current_version_id": "TCV-1",
                },
                "version": {
                    "_id": "TCV-1",
                    "test_case_id": "TC-1",
                    "project_id": "project-1",
                    "status": "ACTIVE",
                    "title": "Đăng nhập có căn cứ",
                    "requirement_version_ids": ["REQV-1"],
                    "coverage_obligations": ["LOGIN_ACCESS"],
                    "evidence_refs": ["REQV-1"],
                    "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "Người dùng đăng nhập."}],
                },
            },
            "status": "SUCCESS",
        }
        operation = AsyncMock(return_value=final)

        with patch("src.tools.automation_publication.require_operation", operation):
            case, version, status = await publish_grounded_test_case(
                "project-1", draft, {}
            )

        self.assertEqual(case["current_version_id"], "TCV-1")
        self.assertEqual(version["_id"], "TCV-1")
        self.assertEqual(status, "SUCCESS")
        operation.assert_awaited_once()
        self.assertIn("/DRAFT-APPROVED/phe-duyet", operation.await_args.args[1])

    async def test_approved_test_case_retry_rejects_a_different_current_version(self):
        draft = {
            "_id": "DRAFT-APPROVED",
            "project_id": "project-1",
            "status": "APPROVED",
            "revision": 4,
            "frozen_version_id": "TCV-1",
            "title": "Đăng nhập có căn cứ",
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["LOGIN_ACCESS"],
            "evidence_refs": ["REQV-1"],
            "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "Người dùng đăng nhập."}],
        }
        final = {
            "test_case": {
                "_id": "TC-1",
                "project_id": "project-1",
                "status": "ACTIVE",
                "current_version_id": "TCV-2",
            },
            "version": {
                "_id": "TCV-2",
                "test_case_id": "TC-1",
                "project_id": "project-1",
                "status": "ACTIVE",
                "title": "Đăng nhập có căn cứ",
                "requirement_version_ids": ["REQV-1"],
                "coverage_obligations": ["LOGIN_ACCESS"],
                "evidence_refs": ["REQV-1"],
                "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "Người dùng đăng nhập."}],
            },
        }
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(return_value=final),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "TEST_CASE_PUBLICATION_READBACK_INVALID"
            ):
                await publish_grounded_test_case("project-1", draft, {})

    async def test_ai_test_case_publication_rejects_review_readback_without_project_scope(self):
        responses = [
            {"_id": "DRAFT-1", "status": "IN_REVIEW", "revision": 2},
        ]
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ) as operation:
            with self.assertRaisesRegex(
                RuntimeError, "TEST_CASE_REVIEW_READBACK_INVALID"
            ):
                await publish_grounded_test_case(
                    "project-1", {"_id": "DRAFT-1", "revision": 1}, {}
                )
        operation.assert_awaited_once()

    async def test_resumable_draft_lookup_includes_ai_drafts_but_not_manual_drafts(self):
        responses = [
            [
                {
                    "_id": "AI-DRAFT",
                    "project_id": "project-1",
                    "requirement_version_ids": ["REQV-1"],
                    "status": "DRAFT",
                    "origin": "ai_generated",
                    "revision": 1,
                },
                {
                    "_id": "MANUAL-DRAFT",
                    "project_id": "project-1",
                    "requirement_version_ids": ["REQV-1"],
                    "status": "DRAFT",
                    "origin": "manual",
                    "revision": 1,
                },
            ],
            [
                {
                    "_id": "REVIEW-DRAFT",
                    "project_id": "project-1",
                    "requirement_version_ids": ["REQV-1"],
                    "status": "IN_REVIEW",
                    "origin": "ai_generated",
                    "revision": 2,
                }
            ],
        ]
        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(side_effect=responses),
        ) as operation:
            drafts = await list_resumable_ai_test_case_drafts(
                "project-1", "REQV-1", {}
            )

        self.assertEqual({draft["_id"] for draft in drafts}, {"AI-DRAFT", "REVIEW-DRAFT"})
        self.assertEqual(operation.await_count, 2)

    async def test_resumable_draft_lookup_rejects_scope_mismatch(self):
        with patch(
            "src.tools.testing.require_operation",
            new=AsyncMock(
                return_value=[
                    {
                        "_id": "OTHER-PROJECT-DRAFT",
                        "project_id": "other-project",
                        "requirement_version_ids": ["REQV-1"],
                        "status": "DRAFT",
                        "origin": "ai_generated",
                    }
                ]
            ),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError, "AI_TEST_CASE_DRAFT_SCOPE_INVALID"
            ):
                await list_resumable_ai_test_case_drafts("project-1", "REQV-1", {})

    async def test_ai_test_case_publication_rechecks_source_before_each_write(self):
        before_write = AsyncMock()
        responses = [
            {"_id": "DRAFT-1", "project_id": "project-1", "status": "IN_REVIEW", "revision": 2},
            {
                "data": {
                    "test_case": {
                        "_id": "TC-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "current_version_id": "TCV-2",
                    },
                    "version": {
                        "_id": "TCV-2",
                        "project_id": "project-1",
                        "test_case_id": "TC-1",
                        "status": "ACTIVE",
                        "requirement_version_ids": [],
                        "coverage_obligations": [],
                        "evidence_refs": [],
                        "evidence_quotes": [],
                    },
                },
            },
        ]
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ) as operation:
            await publish_grounded_test_case(
                "project-1",
                {"_id": "DRAFT-1", "revision": 1},
                {},
                before_write=before_write,
            )

        self.assertEqual(before_write.await_count, 2)
        self.assertEqual(operation.await_count, 2)

    async def test_ai_test_case_publication_stops_before_write_when_source_is_revoked(self):
        before_write = AsyncMock(
            side_effect=AutomationOperationError(
                "AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION"
            )
        )
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(),
        ) as operation:
            with self.assertRaisesRegex(
                AutomationOperationError,
                "AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION",
            ):
                await publish_grounded_test_case(
                    "project-1",
                    {"_id": "DRAFT-1", "revision": 1},
                    {},
                    before_write=before_write,
                )

        before_write.assert_awaited_once()
        operation.assert_not_awaited()

    async def test_ai_test_case_publication_accepts_unwrapped_testing_api_response(self):
        responses = [
            {"_id": "DRAFT-1", "project_id": "project-1", "status": "IN_REVIEW", "revision": 2},
            {
                "test_case": {
                    "_id": "TC-1",
                    "project_id": "project-1",
                    "status": "ACTIVE",
                    "current_version_id": "TCV-2",
                },
                "version": {
                    "_id": "TCV-2",
                    "test_case_id": "TC-1",
                    "project_id": "project-1",
                    "status": "ACTIVE",
                    "requirement_version_ids": ["REQV-1"],
                    "coverage_obligations": [],
                    "evidence_refs": [],
                    "evidence_quotes": [],
                },
            },
        ]
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ):
            case, version, status = await publish_grounded_test_case(
                "project-1",
                {
                    "_id": "DRAFT-1",
                    "revision": 1,
                    "requirement_version_ids": ["REQV-1"],
                },
                {},
            )
        self.assertEqual(case["_id"], "TC-1")
        self.assertEqual(version["_id"], "TCV-2")
        self.assertEqual(status, "SUCCESS")

    async def test_ai_test_case_publication_rejects_frozen_content_drift(self):
        draft = {
            "_id": "DRAFT-CONTENT-1",
            "project_id": "project-1",
            "status": "IN_REVIEW",
            "revision": 2,
            "title": "Đăng nhập bằng thông tin hợp lệ",
            "steps": [
                {
                    "action_doc": {"type": "doc", "content": []},
                    "expected_doc": {"type": "doc", "content": []},
                }
            ],
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["LOGIN_ACCESS"],
            "evidence_refs": ["DOCV-1"],
            "evidence_quotes": [{"evidence_ref": "DOCV-1", "quote": "Cho phép đăng nhập."}],
        }
        result = {
            "test_case": {
                "_id": "TC-1",
                "project_id": "project-1",
                "status": "ACTIVE",
                "current_version_id": "TCV-1",
            },
            "version": {
                "_id": "TCV-1",
                "project_id": "project-1",
                "test_case_id": "TC-1",
                "status": "ACTIVE",
                "title": "Đăng nhập thất bại",
                "steps": draft["steps"],
                "requirement_version_ids": draft["requirement_version_ids"],
                "coverage_obligations": draft["coverage_obligations"],
                "evidence_refs": draft["evidence_refs"],
                "evidence_quotes": draft["evidence_quotes"],
            },
        }
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(return_value=result),
        ) as operation:
            with self.assertRaisesRegex(
                RuntimeError, "TEST_CASE_PUBLICATION_READBACK_INVALID"
            ):
                await publish_grounded_test_case("project-1", draft, {})

        operation.assert_awaited_once()

    async def test_ai_test_case_publication_rejects_omitted_draft_field_added_on_freeze(self):
        draft = {
            "_id": "DRAFT-OMITTED-FIELD",
            "project_id": "project-1",
            "status": "IN_REVIEW",
            "revision": 2,
            "title": "Đăng nhập",
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": [],
            "evidence_refs": [],
            "evidence_quotes": [],
        }
        result = {
            "test_case": {
                "_id": "TC-OMITTED-FIELD",
                "project_id": "project-1",
                "status": "ACTIVE",
                "current_version_id": "TCV-OMITTED-FIELD",
            },
            "version": {
                "_id": "TCV-OMITTED-FIELD",
                "project_id": "project-1",
                "test_case_id": "TC-OMITTED-FIELD",
                "status": "ACTIVE",
                "title": "Đăng nhập",
                "test_data": {"password": "unexpected"},
                "requirement_version_ids": ["REQV-1"],
                "coverage_obligations": [],
                "evidence_refs": [],
                "evidence_quotes": [],
            },
        }
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(return_value=result),
        ) as operation:
            with self.assertRaisesRegex(
                RuntimeError, "TEST_CASE_PUBLICATION_READBACK_INVALID"
            ):
                await publish_grounded_test_case("project-1", draft, {})

        operation.assert_awaited_once()

    async def test_ai_test_case_publication_rejects_noncurrent_or_draft_readback(self):
        responses = [
            {"_id": "DRAFT-1", "project_id": "project-1", "status": "IN_REVIEW", "revision": 2},
            {
                "data": {
                    "test_case": {
                        "_id": "TC-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "current_version_id": "TCV-1",
                    },
                    "version": {
                        "_id": "TCV-2",
                        "test_case_id": "TC-1",
                        "status": "ACTIVE",
                    },
                },
                "status": "SUCCESS",
            },
        ]
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ):
            with self.assertRaisesRegex(RuntimeError, "TEST_CASE_PUBLICATION_READBACK_INVALID"):
                await publish_grounded_test_case(
                    "project-1", {"_id": "DRAFT-1", "revision": 1}, {}
                )

    async def test_ai_test_case_publication_rejects_missing_frozen_obligation_or_source_links(self):
        responses = [
            {"_id": "DRAFT-1", "project_id": "project-1", "status": "IN_REVIEW", "revision": 2},
            {
                "data": {
                    "test_case": {
                        "_id": "TC-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "current_version_id": "TCV-2",
                    },
                    "version": {
                        "_id": "TCV-2",
                        "test_case_id": "TC-1",
                        "status": "ACTIVE",
                        "requirement_version_ids": ["REQV-1"],
                        "coverage_obligations": [],
                        "evidence_refs": ["DOCV-1"],
                    },
                },
                "status": "SUCCESS",
            },
        ]
        draft = {
            "_id": "DRAFT-1",
            "revision": 1,
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["OBL-LOGIN"],
            "evidence_refs": ["DOCV-1"],
        }
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "TEST_CASE_PUBLICATION_READBACK_INVALID"
            ):
                await publish_grounded_test_case("project-1", draft, {})

    async def test_ai_test_case_publication_rejects_frozen_version_with_changed_source_refs(self):
        responses = [
            {"_id": "DRAFT-1", "project_id": "project-1", "status": "IN_REVIEW", "revision": 2},
            {
                "data": {
                    "test_case": {
                        "_id": "TC-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "current_version_id": "TCV-2",
                    },
                    "version": {
                        "_id": "TCV-2",
                        "test_case_id": "TC-1",
                        "status": "ACTIVE",
                        "requirement_version_ids": ["REQV-1"],
                        "coverage_obligations": ["OBL-LOGIN"],
                        "evidence_refs": ["DOCV-2"],
                    },
                },
                "status": "SUCCESS",
            },
        ]
        draft = {
            "_id": "DRAFT-1",
            "revision": 1,
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["OBL-LOGIN"],
            "evidence_refs": ["DOCV-1"],
        }
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "TEST_CASE_PUBLICATION_READBACK_INVALID"
            ):
                await publish_grounded_test_case("project-1", draft, {})

    async def test_ai_test_case_publication_rejects_changed_frozen_source_quote(self):
        responses = [
            {"_id": "DRAFT-1", "project_id": "project-1", "status": "IN_REVIEW", "revision": 2},
            {
                "data": {
                    "test_case": {
                        "_id": "TC-1",
                        "project_id": "project-1",
                        "status": "ACTIVE",
                        "current_version_id": "TCV-2",
                    },
                    "version": {
                        "_id": "TCV-2",
                        "test_case_id": "TC-1",
                        "status": "ACTIVE",
                        "requirement_version_ids": ["REQV-1"],
                        "coverage_obligations": ["OBL-LOGIN"],
                        "evidence_refs": ["DOCV-1"],
                        "evidence_quotes": [
                            {"evidence_ref": "DOCV-1", "quote": "Câu trích dẫn khác."}
                        ],
                    },
                },
                "status": "SUCCESS",
            },
        ]
        draft = {
            "_id": "DRAFT-1",
            "revision": 1,
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["OBL-LOGIN"],
            "evidence_refs": ["DOCV-1"],
            "evidence_quotes": [
                {"evidence_ref": "DOCV-1", "quote": "Câu trích dẫn có căn cứ."}
            ],
        }
        with patch(
            "src.tools.automation_publication.require_operation",
            new=AsyncMock(side_effect=responses),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "TEST_CASE_PUBLICATION_READBACK_INVALID"
            ):
                await publish_grounded_test_case("project-1", draft, {})

    def test_clarification_only_ingestion_waits_for_input_not_failure(self):
        outcome = classify_requirement_ingestion_outcome(
            [{"requirement_version_id": "REQV-1", "reason": "REQUIREMENT_CLARIFICATION_REQUIRED"}]
        )

        self.assertEqual(
            outcome,
            (
                "automation_waiting_for_input",
                "AWAITING_INPUT",
                "REQUIREMENT_CLARIFICATION_REQUIRED",
            ),
        )

    def test_ai_publication_approval_reason_is_not_a_human_checkpoint(self):
        for reason in ("REQUIREMENT_APPROVAL_REQUIRED", "TEST_CASE_APPROVAL_REQUIRED"):
            with self.subTest(reason=reason):
                self.assertEqual(classify_requirement_ingestion_outcome([{"reason": reason}])[0], "automation_partial_failure")

    def test_unresolved_maintenance_gate_is_not_confused_with_success(self):
        self.assertEqual(
            classify_requirement_ingestion_outcome([{"reason": "MAINTENANCE_APPROVAL_REQUIRED"}])[0],
            "automation_partial_failure",
        )

    def test_possible_duplicate_match_waits_for_input_not_pipeline_failure(self):
        outcome = classify_requirement_ingestion_outcome(
            [{
                "reason": "REQUIREMENT_MATCH_NEEDS_RECONCILIATION",
                "unmapped_obligation_keys": ["LOGIN_ACCESS"],
            }]
        )

        self.assertEqual(
            outcome,
            (
                "automation_waiting_for_input",
                "AWAITING_INPUT",
                "REQUIREMENT_MATCH_NEEDS_RECONCILIATION",
            ),
        )

    def test_possible_duplicate_plus_real_generation_gap_remains_incomplete(self):
        outcome = classify_requirement_ingestion_outcome(
            [
                {"reason": "REQUIREMENT_MATCH_NEEDS_RECONCILIATION"},
                {"reason": "TEST_CASE_GENERATION_NOT_GROUNDED"},
            ]
        )

        self.assertEqual(outcome, ("automation_partial_failure", "INCOMPLETE", None))

    def test_mixed_clarification_and_generation_gap_remains_incomplete(self):
        outcome = classify_requirement_ingestion_outcome(
            [
                {"reason": "REQUIREMENT_CLARIFICATION_REQUIRED"},
                {"reason": "TEST_CASE_GENERATION_NOT_GROUNDED"},
            ]
        )

        self.assertEqual(outcome, ("automation_partial_failure", "INCOMPLETE", None))

    def test_requirement_citations_are_returned_only_after_current_source_verification(self):
        source_text = "Đầu. " + self.obligation["source_quote"] + " Cuối."
        start = source_text.index(self.obligation["source_quote"])
        quote_hash = hashlib.sha256(
            self.obligation["source_quote"].encode("utf-8")
        ).hexdigest()
        source = {
            "_id": "DOC-1",
            "status": "READY",
            "ai_enabled": True,
            "source_version": "v2",
            "content_hash": "doc-hash-v2",
            "normalized_content": source_text,
            "authority": "PROJECT_REFERENCE",
        }
        requirement = {
            "source_refs": [{
                "requirement_document_id": "DOC-1",
                "source_version": "v2",
                "content_hash": "doc-hash-v2",
                "source_start": start,
                "source_end": start + len(self.obligation["source_quote"]),
                "source_quote": self.obligation["source_quote"],
                "source_text_hash": quote_hash,
            }]
        }

        facts, evidence = verified_requirement_source_citations(
            [requirement], {"DOC-1": source}, ["DOC-1"]
        )

        self.assertEqual(len(facts), 1)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(facts[0]["relationship_path"], ["DOC-1"])
        self.assertEqual(evidence[0]["relationship_path"], ["DOC-1"])
        self.assertEqual(evidence[0]["text"], self.obligation["source_quote"])
        self.assertEqual(evidence[0]["source_start"], start)
        self.assertEqual(
            evidence[0]["source_verification"],
            "VERIFIED_REQUIREMENT_SOURCE_CITATION",
        )

        stale = {**requirement, "source_refs": [{**requirement["source_refs"][0], "content_hash": "old-hash"}]}
        self.assertEqual(
            verified_requirement_source_citations([stale], {"DOC-1": source}, ["DOC-1"]),
            ([], []),
        )
        self.assertEqual(
            verified_requirement_source_citations([requirement], {"DOC-1": source}, []),
            ([], []),
        )

    def test_requirement_source_evidence_preserves_authorized_version_ancestry(self):
        quote = "Mật khẩu phải dài ít nhất 12 ký tự."
        root = {
            "_id": "DOC-1",
            "project_id": "project-1",
            "source_series_id": "SERIES-1",
            "source_version_sequence": 1,
            "source_version": "1",
        }
        current = {
            "_id": "DOC-2",
            "project_id": "project-1",
            "source_series_id": "SERIES-1",
            "source_version_sequence": 2,
            "previous_source_version_id": "DOC-1",
            "source_version": "2",
            "content_hash": "current-hash",
            "status": "READY",
            "ai_enabled": True,
            "normalized_content": quote,
        }
        requirement = {
            "source_refs": [{
                "requirement_document_id": "DOC-2",
                "source_version": "2",
                "content_hash": "current-hash",
                "source_start": 0,
                "source_end": len(quote),
                "source_quote": quote,
            }]
        }

        facts, evidence = verified_requirement_source_citations(
            [requirement], {"DOC-1": root, "DOC-2": current}, ["DOC-1", "DOC-2"]
        )

        self.assertEqual(facts[0]["relationship_path"], ["DOC-1", "DOC-2"])
        self.assertEqual(evidence[0]["relationship_path"], ["DOC-1", "DOC-2"])
        restricted_facts, restricted_evidence = verified_requirement_source_citations(
            [requirement], {"DOC-1": root, "DOC-2": current}, ["DOC-2"]
        )
        self.assertEqual(restricted_facts[0]["relationship_path"], ["DOC-2"])
        self.assertEqual(restricted_evidence[0]["relationship_path"], ["DOC-2"])

    def test_blueprint_receives_exact_facts_from_every_permitted_document(self):
        documents = {
            "DOC-1": {
                "_id": "DOC-1",
                "source_version": "v1",
                "normalized_content": "Tài khoản bị khóa sau 5 lần nhập sai.",
            },
            "DOC-2": {
                "_id": "DOC-2",
                "source_version": "v3",
                "normalized_content": "Tài khoản bị khóa sau 7 lần nhập sai.",
            },
        }

        facts, evidence = verified_document_facts(["DOC-1", "DOC-2"], documents)

        self.assertEqual({fact.artifact_id for fact in facts}, {"DOC-1", "DOC-2"})
        self.assertEqual(
            {fact.quote for fact in facts},
            {
                "Tài khoản bị khóa sau 5 lần nhập sai.",
                "Tài khoản bị khóa sau 7 lần nhập sai.",
            },
        )
        for fact in facts:
            source = evidence[fact.artifact_version_id]["text"]
            self.assertEqual(
                source[fact.source_start : fact.source_end], fact.quote
            )
            self.assertEqual(fact.relationship_path, [fact.artifact_id])
            self.assertEqual(
                evidence[fact.artifact_version_id]["relationship_path"],
                [fact.artifact_id],
            )

    def test_repeated_source_sentence_preserves_each_canonical_span(self):
        repeated = "Người dùng phải xác nhận email."
        source_text = f"{repeated}\n{repeated}"

        facts, evidence = verified_document_facts(
            ["DOC-1"],
            {"DOC-1": {"_id": "DOC-1", "normalized_content": source_text}},
        )

        self.assertEqual([fact.quote for fact in facts], [repeated, repeated])
        self.assertEqual(
            [(fact.source_start, fact.source_end) for fact in facts],
            [(0, len(repeated)), (len(repeated) + 1, (len(repeated) * 2) + 1)],
        )
        self.assertTrue(
            all(
                evidence[fact.artifact_version_id]["text"][fact.source_start:fact.source_end]
                == fact.quote
                for fact in facts
            )
        )

    def test_blueprint_source_lineage_returns_only_verified_claim_facts(self):
        documents = {
            "DOC-1": {
                "_id": "DOC-1",
                "normalized_content": "Tài khoản bị khóa sau 5 lần nhập sai. Nội dung khác.",
            }
        }
        facts, _ = verified_document_facts(["DOC-1"], documents)
        blueprint = {
            "obligations": [
                {
                    "key": "LOCKOUT",
                    "source_ref": "DOC-1",
                    "source_quote": "Tài khoản bị khóa sau 5 lần nhập sai.",
                }
            ],
            "clarifications": [],
        }

        source_facts, source_evidence = blueprint_source_lineage(blueprint, facts)

        self.assertEqual(len(source_facts), 1)
        self.assertEqual(source_facts[0]["artifact_version_id"], "DOC-1")
        self.assertEqual(source_facts[0]["quote"], blueprint["obligations"][0]["source_quote"])
        self.assertEqual(len(source_evidence), 1)
        self.assertEqual(source_evidence[0]["text"], source_facts[0]["quote"])
        self.assertEqual(source_evidence[0]["source_start"], source_facts[0]["source_start"])
        self.assertEqual(source_evidence[0]["source_end"], source_facts[0]["source_end"])

    def test_blueprint_source_lineage_does_not_claim_unmatched_or_unverified_quote(self):
        facts, _ = verified_document_facts(
            ["DOC-1"],
            {"DOC-1": {"_id": "DOC-1", "normalized_content": "Chỉ tài khoản đã đăng ký mới được đăng nhập."}},
        )
        blueprint = {
            "obligations": [
                {"key": "LOGIN", "source_ref": "DOC-1", "source_quote": "Mọi tài khoản đều được đăng nhập."}
            ],
            "clarifications": [],
        }

        source_facts, source_evidence = blueprint_source_lineage(blueprint, facts)

        self.assertEqual(source_facts, [])
        self.assertEqual(source_evidence, [])

    def test_blueprint_source_lineage_rejects_quote_inside_another_word(self):
        facts, _ = verified_document_facts(
            ["DOC-1"],
            {"DOC-1": {"_id": "DOC-1", "normalized_content": "invalid"}},
        )
        blueprint = {
            "obligations": [{"key": "VALID", "source_ref": "DOC-1", "source_quote": "valid"}],
            "clarifications": [],
        }

        source_facts, source_evidence = blueprint_source_lineage(blueprint, facts)

        self.assertEqual(source_facts, [])
        self.assertEqual(source_evidence, [])

    def test_generated_obligation_coverage_requires_the_compiled_quote(self):
        obligation = {
            "key": "LOCKOUT",
            "source_quote": "Tài khoản bị khóa sau 5 lần nhập sai.",
        }
        evidence = [{
            "obligation_key": "LOCKOUT",
            "evidence_quotes": [{
                "evidence_ref": "REQ-V1",
                "quote": "Tài khoản bị khóa sau 5 lần nhập sai.",
            }],
        }]

        self.assertTrue(generated_obligation_evidence_matches(
            ["LOCKOUT"], evidence, [obligation]
        ))
        self.assertTrue(generated_obligation_evidence_matches(
            ["LOCKOUT"], [{
                "obligation_key": "LOCKOUT",
                "evidence_quotes": [{
                    "evidence_ref": "REQ-V1",
                    "quote": "bị khóa sau 5 lần nhập sai.",
                }],
            }], [obligation]
        ))
        self.assertFalse(generated_obligation_evidence_matches(
            ["LOCKOUT"], [{
                "obligation_key": "LOCKOUT",
                "evidence_quotes": [{
                    "evidence_ref": "REQ-V1",
                    "quote": "Người dùng đăng nhập thành công.",
                }],
            }], [obligation]
        ))
        self.assertFalse(generated_obligation_evidence_matches(
            ["LOCKOUT"], [], [obligation]
        ))

    def test_generated_obligation_evidence_rejects_quote_inside_another_word(self):
        self.assertFalse(
            generated_obligation_evidence_matches(
                ["VALID"],
                [{
                    "obligation_key": "VALID",
                    "evidence_quotes": [{"evidence_ref": "REQ-V1", "quote": "invalid"}],
                }],
                [{"key": "VALID", "source_quote": "valid"}],
            )
        )

    def test_resumable_draft_rejects_quote_inside_another_word(self):
        draft = {
            "_id": "DRAFT-1",
            "origin": "ai_generated",
            "requirement_version_ids": ["REQ-V1"],
            "coverage_obligations": ["VALID"],
            "evidence_refs": ["REQ-V1"],
            "source_evidence": [{"artifact_version_id": "REQ-V1", "text": "invalid"}],
            "evidence_quotes": [{"evidence_ref": "REQ-V1", "quote": "valid"}],
        }

        self.assertFalse(
            resumable_draft_matches_blueprint_scope(
                draft,
                "REQ-V1",
                [],
                [{"key": "VALID", "source_quote": "valid"}],
            )
        )

    def test_independent_documents_with_same_display_version_keep_separate_evidence(self):
        documents = {
            "DOC-A": {
                "_id": "DOC-A",
                "source_version": "1",
                "normalized_content": "Chỉ tài khoản đã đăng ký mới được đăng nhập.",
            },
            "DOC-B": {
                "_id": "DOC-B",
                "source_version": "1",
                "normalized_content": "Mật khẩu phải có ít nhất 12 ký tự.",
            },
        }

        facts, evidence = verified_document_facts(["DOC-A", "DOC-B"], documents)

        self.assertEqual(set(evidence), {"DOC-A", "DOC-B"})
        self.assertEqual(
            {fact.artifact_version_id for fact in facts}, {"DOC-A", "DOC-B"}
        )
        self.assertEqual(evidence["DOC-A"]["source_version"], "1")
        self.assertEqual(evidence["DOC-B"]["source_version"], "1")
        for fact in facts:
            source = evidence[fact.artifact_version_id]
            self.assertEqual(source["artifact_id"], fact.artifact_id)
            self.assertEqual(
                source["text"][fact.source_start : fact.source_end], fact.quote
            )

    def test_requirement_citations_use_unique_source_version_record_identity(self):
        quote_a = "Chỉ tài khoản đã đăng ký mới được đăng nhập."
        quote_b = "Mật khẩu phải có ít nhất 12 ký tự."
        documents = {
            "DOC-A": {
                "_id": "DOC-A",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "content_hash": "hash-a",
                "normalized_content": quote_a,
            },
            "DOC-B": {
                "_id": "DOC-B",
                "status": "READY",
                "ai_enabled": True,
                "source_version": "1",
                "content_hash": "hash-b",
                "normalized_content": quote_b,
            },
        }
        requirements = [
            {
                "source_refs": [
                    {
                        "requirement_document_id": document_id,
                        "source_version": "1",
                        "content_hash": content_hash,
                        "source_start": 0,
                        "source_end": len(quote),
                        "source_quote": quote,
                    }
                ]
            }
            for document_id, content_hash, quote in [
                ("DOC-A", "hash-a", quote_a),
                ("DOC-B", "hash-b", quote_b),
            ]
        ]

        facts, evidence = verified_requirement_source_citations(
            requirements, documents, ["DOC-A", "DOC-B"]
        )

        self.assertEqual({fact["artifact_version_id"] for fact in facts}, {"DOC-A", "DOC-B"})
        self.assertEqual({item["artifact_id"] for item in evidence}, {"DOC-A", "DOC-B"})
        self.assertEqual({item["text"] for item in evidence}, {quote_a, quote_b})

    def test_document_fact_lineage_follows_only_visible_explicit_versions(self):
        documents = {
            "DOC-1": {
                "_id": "DOC-1",
                "project_id": "project-1",
                "source_series_id": "SERIES-1",
                "source_version_sequence": 1,
                "normalized_content": "Quy tắc phiên bản đầu.",
            },
            "DOC-2": {
                "_id": "DOC-2",
                "project_id": "project-1",
                "source_series_id": "SERIES-1",
                "source_version_sequence": 2,
                "previous_source_version_id": "DOC-1",
                "normalized_content": "Quy tắc phiên bản hai.",
            },
            "DOC-3": {
                "_id": "DOC-3",
                "project_id": "project-1",
                "source_series_id": "SERIES-OTHER",
                "previous_source_version_id": "DOC-2",
                "normalized_content": "Nguồn độc lập.",
            },
        }

        self.assertEqual(
            authorized_document_version_path("DOC-2", documents),
            ["DOC-1", "DOC-2"],
        )
        self.assertEqual(
            authorized_document_version_path("DOC-2", documents, {"DOC-2"}),
            ["DOC-2"],
        )
        self.assertEqual(
            authorized_document_version_path("DOC-3", documents), ["DOC-3"]
        )
        self.assertEqual(
            authorized_document_version_path(
                "DOC-2", {"DOC-2": documents["DOC-2"]}
            ),
            ["DOC-2"],
        )

    def test_document_fact_lineage_stops_at_invalid_parent_metadata(self):
        current = {
            "_id": "DOC-2",
            "project_id": "project-1",
            "source_series_id": "SERIES-1",
            "source_version_sequence": 2,
            "previous_source_version_id": "DOC-1",
        }
        parent = {
            "_id": "DOC-1",
            "project_id": "project-1",
            "source_series_id": "SERIES-1",
            "source_version_sequence": 1,
        }
        invalid_parents = [
            {**parent, "_id": "DOC-OTHER"},
            {**parent, "project_id": "project-other"},
            {**parent, "source_version_sequence": 0},
            {**parent, "source_series_id": None},
        ]

        for invalid_parent in invalid_parents:
            with self.subTest(parent=invalid_parent):
                self.assertEqual(
                    authorized_document_version_path(
                        "DOC-2", {"DOC-2": current, "DOC-1": invalid_parent}
                    ),
                    ["DOC-2"],
                )

    def test_conflicting_blueprint_clarifications_are_a_workflow_gate(self):
        self.assertTrue(
            has_conflicting_blueprint_clarification(
                {"clarifications": [{"category": "CONTRADICTION"}]}
            )
        )
        self.assertTrue(
            has_conflicting_blueprint_clarification(
                {"clarifications": [{"category": "INCONSISTENCY"}]}
            )
        )
        self.assertFalse(
            has_conflicting_blueprint_clarification(
                {"clarifications": [{"category": "OMISSION"}]}
            )
        )

    def test_only_unresolved_clarifications_that_unlock_obligations_block_automation(self):
        optional = {
            "source_ref": "DOC-1",
            "source_quote": "Chỉ tài khoản đã đăng ký mới được phép đăng nhập.",
            "question": "Hệ thống hiển thị thông báo nào?",
            "reason": "Reason persisted by an earlier model run.",
            "_id": "RCL-OPTIONAL",
        }
        conflict = {
            "source_ref": "DOC-1",
            "source_quote": "Tài khoản bị khóa sau 5 lần nhập sai.",
            "question": "Quy tắc khóa tài khoản nào có hiệu lực?",
            "reason": "Hai nguồn đưa ra số lần khóa khác nhau.",
            "_id": "RCL-CONFLICT",
        }
        blueprint = [
            {**optional, "unlocks_obligation_keys": []},
            {**conflict, "unlocks_obligation_keys": ["LOCKOUT_RULE"]},
        ]
        self.assertEqual(
            blocking_blueprint_clarifications([optional, conflict], blueprint),
            [conflict],
        )

    def test_blueprint_clarification_requires_current_permitted_source_span(self):
        quote = "Chỉ tài khoản đã đăng ký mới được phép đăng nhập."
        source_text = f"{quote} Người dùng vào trang chủ sau khi đăng nhập."
        start = source_text.index(quote)
        version = {
            "source_refs": [{
                "requirement_document_id": "DOC-1",
                "source_version": "v3",
                "content_hash": "hash-v3",
                "source_start": start,
                "source_end": start + len(quote),
                "source_quote": quote,
                "source_text_hash": hashlib.sha256(quote.encode()).hexdigest(),
            }]
        }
        evidence = {"DOC-1-v3": {"artifact_id": "DOC-1"}}
        documents = {"DOC-1": {
            "status": "READY",
            "ai_enabled": True,
            "source_version": "v3",
            "content_hash": "hash-v3",
            "normalized_content": source_text,
        }}
        clarification = {"evidence_refs": ["DOC-1-v3"], "source_quote": quote}
        self.assertEqual(
            blueprint_clarification_source_ids(version, clarification, evidence, documents),
            ["DOC-1"],
        )
        documents["DOC-1"]["ai_enabled"] = False
        self.assertEqual(
            blueprint_clarification_source_ids(version, clarification, evidence, documents),
            [],
        )

    async def test_blueprint_clarification_persistence_is_grounded_and_idempotent(self):
        quote = "Chỉ tài khoản đã đăng ký mới được phép đăng nhập."
        source_text = f"{quote} Hệ thống cấp phiên khi thông tin hợp lệ."
        start = source_text.index(quote)
        version = {
            "_id": "REQV-1",
            "source_refs": [{
                "requirement_document_id": "DOC-1",
                "source_version": "v1",
                "content_hash": "hash-v1",
                "source_start": start,
                "source_end": start + len(quote),
                "source_quote": quote,
                "source_text_hash": hashlib.sha256(quote.encode()).hexdigest(),
            }],
        }
        clarification = {
            "code": "LOGIN_UNREGISTERED",
            "question": "Hệ thống xử lý email chưa đăng ký như thế nào?",
            "reason": "Nguồn chỉ xác định ai được đăng nhập, chưa quy định nội dung phản hồi.",
            "evidence_refs": ["DOC-1-v1"],
            "source_quote": quote,
            "unlocks_obligation_keys": ["login_access"],
        }
        obligations = [
            {
                "key": "login_access",
                "source_quote": "Tài khoản đã đăng ký có thể đăng nhập.",
            }
        ]
        invalid_clarification = {
            **clarification,
            "unlocks_obligation_keys": ["login_access", "unknown_key"],
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(),
        ) as operation:
            with self.assertRaisesRegex(
                ValueError, "BLUEPRINT_CLARIFICATION_UNKNOWN_OBLIGATION_LINK"
            ):
                await persist_blueprint_clarifications(
                    version,
                    [invalid_clarification],
                    {"DOC-1-v1": {"artifact_id": "DOC-1"}},
                    {
                        "DOC-1": {
                            "status": "READY",
                            "ai_enabled": True,
                            "source_version": "v1",
                            "content_hash": "hash-v1",
                            "normalized_content": source_text,
                        }
                    },
                    {},
                    obligations,
                )
        operation.assert_not_awaited()

        evidence = {"DOC-1-v1": {"artifact_id": "DOC-1"}}
        documents = {"DOC-1": {
            "status": "READY", "ai_enabled": True, "source_version": "v1",
            "content_hash": "hash-v1", "normalized_content": source_text,
        }}
        saved = {
            "_id": "RCL-1", "requirement_version_id": "REQV-1",
            "source_ref": "DOC-1", "source_quote": quote,
            "question": clarification["question"], "reason": clarification["reason"],
            "unlocks_obligation_keys": ["login_access"],
            "unlocks_source_quotes": ["Tài khoản đã đăng ký có thể đăng nhập."],
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=[[], saved]),
        ) as operation:
            created, unmapped = await persist_blueprint_clarifications(
                version, [clarification], evidence, documents, {}, obligations
            )
        self.assertEqual(unmapped, [])
        self.assertEqual(created[0]["_id"], "RCL-1")
        self.assertEqual(operation.await_count, 2)
        self.assertEqual(operation.await_args_list[1].args[3]["source_quote"], quote)
        self.assertEqual(
            operation.await_args_list[1].args[3]["unlocks_obligation_keys"],
            ["login_access"],
        )
        self.assertEqual(
            operation.await_args_list[1].args[3]["unlocks_source_quotes"],
            ["Tài khoản đã đăng ký có thể đăng nhập."],
        )

        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value=[saved]),
        ) as operation:
            created, unmapped = await persist_blueprint_clarifications(
                version, [clarification], evidence, documents, {}, obligations
            )
        self.assertEqual(unmapped, [])
        self.assertEqual(created[0]["_id"], "RCL-1")
        operation.assert_awaited_once()

        saved_with_prior_reason = {**saved, "reason": "Câu hỏi đã được phát hiện ở lần chạy trước."}
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value=[saved_with_prior_reason]),
        ) as operation:
            created, unmapped = await persist_blueprint_clarifications(
                version, [clarification], evidence, documents, {}, obligations
            )
        self.assertEqual(unmapped, [])
        self.assertEqual(created[0]["_id"], "RCL-1")
        operation.assert_awaited_once()

    def test_blueprint_clarification_mapped_to_one_requirement_is_not_globally_unmapped(self):
        unmapped = [
            {"code": "LOCKOUT_THRESHOLD", "question": "How many attempts?"},
            {"code": "SESSION_TIMEOUT", "question": "When does the session expire?"},
        ]
        persisted = [
            {"blueprint_code": "LOCKOUT_THRESHOLD", "_id": "RCL-1"},
        ]

        self.assertEqual(
            unmapped_blueprint_clarifications_after_persistence(unmapped, persisted),
            [unmapped[1]],
        )

    def test_requirement_source_citation_serializes_structured_content_consistently(self):
        source_text = json.dumps(
            {"paths": {"/login": {"summary": "Đăng nhập"}}},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        quote = '"summary":"Đăng nhập"'
        start = source_text.index(quote)
        source = {
            "_id": "API-1",
            "status": "READY",
            "ai_enabled": True,
            "source_version": "v1",
            "normalized_content": {"paths": {"/login": {"summary": "Đăng nhập"}}},
        }
        requirement = {
            "source_refs": [{
                "requirement_document_id": "API-1",
                "source_version": "v1",
                "source_start": start,
                "source_end": start + len(quote),
                "source_quote": quote,
            }]
        }
        facts, evidence = verified_requirement_source_citations(
            [requirement], {"API-1": source}, ["API-1"]
        )
        self.assertEqual(facts[0]["quote"], quote)
        self.assertEqual(evidence[0]["text"], quote)

    def test_existing_active_case_with_exact_requirement_evidence_covers_obligation(self):
        self.assertTrue(
            existing_test_case_supports_obligation(
                "REQV-1", self.obligation, self.test_case, self.test_case_version
            )
        )

    def test_existing_case_from_another_requirement_does_not_cover_obligation(self):
        self.test_case_version["requirement_version_ids"] = ["REQV-OTHER"]
        self.assertFalse(
            existing_test_case_supports_obligation(
                "REQV-1", self.obligation, self.test_case, self.test_case_version
            )
        )

    def test_non_current_test_case_version_does_not_cover_obligation(self):
        self.test_case["current_version_id"] = "TCV-2"
        self.assertFalse(
            existing_test_case_supports_obligation(
                "REQV-1", self.obligation, self.test_case, self.test_case_version
            )
        )

    def test_stale_test_case_does_not_cover_obligation(self):
        self.test_case["stale_status"] = "STALE"
        self.assertFalse(
            existing_test_case_supports_obligation(
                "REQV-1", self.obligation, self.test_case, self.test_case_version
            )
        )

    def test_inactive_test_case_version_does_not_cover_obligation(self):
        self.test_case_version["status"] = "SUPERSEDED"
        self.assertFalse(
            existing_test_case_supports_obligation(
                "REQV-1", self.obligation, self.test_case, self.test_case_version
            )
        )

    def test_unverified_or_mismatched_quote_does_not_cover_obligation(self):
        self.test_case_version["evidence_quotes"][0]["quote"] = "Nội dung khác"
        self.assertFalse(
            existing_test_case_supports_obligation(
                "REQV-1", self.obligation, self.test_case, self.test_case_version
            )
        )
        self.test_case_version["evidence_quotes"][0].update(
            quote=self.obligation["source_quote"], evidence_ref="UNLINKED"
        )
        self.assertFalse(
            existing_test_case_supports_obligation(
                "REQV-1", self.obligation, self.test_case, self.test_case_version
            )
        )

    def test_requirement_coverage_rejects_quote_inside_another_word(self):
        obligation = {"key": "VALID", "source_quote": "valid"}
        version = {
            **self.test_case_version,
            "source_evidence": [{"artifact_version_id": "REQV-1", "text": "invalid"}],
            "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "valid"}],
        }

        self.assertFalse(
            existing_test_case_supports_obligation(
                "REQV-1", obligation, self.test_case, version
            )
        )

    async def test_duplicate_candidate_is_read_back_and_only_grounded_match_is_reused(self):
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(
                side_effect=[self.test_case_version, self.test_case]
            ),
        ) as operation:
            result = await resolve_existing_obligation_coverage(
                "REQV-1",
                "project-1",
                [self.obligation],
                {"LOGIN_ACCESS"},
                [{"target_version_id": "TCV-1"}],
                {},
                {},
            )

        self.assertEqual(
            result,
            {
                "LOGIN_ACCESS": [
                    {"test_case_id": "TC-1", "test_case_version_id": "TCV-1"}
                ]
            },
        )
        self.assertEqual(operation.await_count, 2)

    async def test_exact_existing_requirement_evidence_is_reused_even_if_model_key_changed(self):
        case = {
            **self.test_case,
            "current_version": {
                **self.test_case_version,
                "coverage_obligations": ["OLDER_GENERATED_KEY"],
            },
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={
                "items": [case],
                "total": 1,
                "total_pages": 1,
                "page": 1,
                "page_size": 500,
                "scope_fingerprint": "scope-v1",
            }),
        ) as operation:
            coverage = await existing_requirement_obligation_coverage(
                "REQ-1",
                "project-1",
                "REQV-1",
                [{"key": "NEW_GENERATED_KEY", "source_quote": self.obligation["source_quote"]}],
                {},
            )
        self.assertEqual(
            coverage,
            {"NEW_GENERATED_KEY": [{"test_case_id": "TC-1", "test_case_version_id": "TCV-1"}]},
        )
        operation.assert_awaited_once()

    async def test_existing_test_case_with_different_source_quote_does_not_cover_obligation(self):
        case = {
            **self.test_case,
            "current_version": {
                **self.test_case_version,
                "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "Nguồn khác."}],
            },
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(return_value={
                "items": [case],
                "total": 1,
                "total_pages": 1,
                "page": 1,
                "page_size": 500,
                "scope_fingerprint": "scope-v1",
            }),
        ):
            coverage = await existing_requirement_obligation_coverage(
                "REQ-1", "project-1", "REQV-1", [self.obligation], {}
            )
        self.assertEqual(coverage, {})

    async def test_duplicate_guard_reads_more_than_forty_pages_with_stable_scope(self):
        next_index = 0

        async def page_response(_method, _path, _config):
            nonlocal next_index
            next_index += 1
            return {
                "items": [{"_id": f"TC-{next_index}", "project_id": "project-1"}],
                "total": 41,
                "total_pages": 41,
                "page": next_index,
                "page_size": 1,
                "scope_fingerprint": "stable-scope",
            }

        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=page_response),
        ) as operation:
            coverage = await existing_requirement_obligation_coverage(
                "REQ-1", "project-1", "REQV-1", [], {}, page_size=1
            )

        self.assertEqual(coverage, {})
        self.assertEqual(operation.await_count, 41)

    async def test_duplicate_guard_rejects_scope_change_between_pages(self):
        responses = [
            {
                "items": [{"_id": "TC-1", "project_id": "project-1"}],
                "total": 2,
                "total_pages": 2,
                "page": 1,
                "page_size": 1,
                "scope_fingerprint": "scope-v1",
            },
            {
                "items": [{"_id": "TC-2", "project_id": "project-1"}],
                "total": 2,
                "total_pages": 2,
                "page": 2,
                "page_size": 1,
                "scope_fingerprint": "scope-v2",
            },
        ]
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=responses),
        ):
            with self.assertRaisesRegex(
                AutomationOperationError,
                "TEST_CASE_DEDUPLICATION_SCOPE_CHANGED_DURING_READ",
            ):
                await existing_requirement_obligation_coverage(
                    "REQ-1", "project-1", "REQV-1", [], {}, page_size=1
                )

    async def test_timed_out_import_is_recovered_from_confirmed_job_state(self):
        job = {"_id": "import-1", "revision": 3, "preview": [{}, {}]}
        confirmed = {
            "_id": "import-1",
            "status": "CONFIRMED",
            "created_requirement_ids": ["req-1", "req-2"],
        }
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=[httpx.ReadTimeout("response timed out"), confirmed]),
        ) as operation:
            result, latest = await apply_requirement_import_safely(job, {})

        self.assertEqual(latest, confirmed)
        self.assertEqual(result["requirements"], [])
        self.assertEqual(operation.await_count, 2)
        self.assertEqual(
            operation.await_args_list[0].kwargs["timeout"],
            180,
        )

    async def test_import_waits_for_confirmation_without_repeating_mutation(self):
        job = {"_id": "import-1", "revision": 3, "preview": [{}]}
        confirming = {"_id": "import-1", "status": "CONFIRMING"}
        confirmed = {"_id": "import-1", "status": "CONFIRMED"}
        with (
            patch(
                "src.tools.requirement_document_workflow.require_operation",
                new=AsyncMock(
                    side_effect=[httpx.ReadTimeout("response timed out"), confirming, confirmed]
                ),
            ) as operation,
            patch(
                "src.tools.requirement_document_workflow.asyncio.sleep",
                new=AsyncMock(),
            ) as sleep,
        ):
            result, latest = await apply_requirement_import_safely(job, {})

        self.assertEqual(latest["status"], "CONFIRMED")
        self.assertEqual(result["requirements"], [])
        self.assertEqual(operation.await_count, 3)
        sleep.assert_awaited_once_with(2)

    async def test_known_uncommitted_import_error_is_not_hidden(self):
        job = {"_id": "import-1", "revision": 3, "preview": [{}]}
        failure = AutomationOperationError("IMPORT_MATCH_REVIEW_REQUIRED")
        preview_ready = {"_id": "import-1", "status": "PREVIEW_READY"}
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=[failure, preview_ready]),
        ):
            with self.assertRaises(AutomationOperationError) as raised:
                await apply_requirement_import_safely(job, {})

        self.assertIs(raised.exception, failure)

    async def test_import_source_revocation_stops_before_confirmation_mutation(self):
        job = {"_id": "import-1", "revision": 3, "preview": [{}]}
        before_write = AsyncMock(
            side_effect=AutomationOperationError(
                "AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION"
            )
        )
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(),
        ) as operation:
            with self.assertRaisesRegex(
                AutomationOperationError,
                "AI_SOURCE_SCOPE_CHANGED_DURING_COMPILATION",
            ):
                await apply_requirement_import_safely(
                    job, {}, before_write=before_write
                )

        before_write.assert_awaited_once()
        operation.assert_not_awaited()

    async def test_ungrounded_test_case_preview_gets_one_constrained_retry(self):
        obligations = [{
            "key": "login-access",
            "obligation": "Người dùng vào được hệ thống",
            "source_quote": "Khi nhập đúng thông tin, người dùng vào được hệ thống.",
        }]
        preview = {"items": [{"draft": {"title": "Ca có căn cứ"}}]}
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(
                side_effect=[AutomationOperationError("AI_UNGROUNDED_OUTPUT"), preview]
            ),
        ) as operation:
            result = await generate_grounded_test_case_preview(
                "version-1",
                {},
                {"instruction": "original"},
                obligations,
            )

        self.assertEqual(result, preview)
        self.assertEqual(operation.await_count, 2)
        retry_payload = operation.await_args_list[1].args[3]
        self.assertIn("Regenerate the rejected preview from scratch", retry_payload["instruction"])
        self.assertIn("Người dùng vào được hệ thống", retry_payload["instruction"])

    async def test_test_case_generation_rechecks_source_before_retry(self):
        before_request = AsyncMock()
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(
                side_effect=[
                    AutomationOperationError("AI_UNGROUNDED_OUTPUT"),
                    {"items": []},
                ]
            ),
        ):
            await generate_grounded_test_case_preview(
                "version-1",
                {},
                {"instruction": "original"},
                [self.obligation],
                before_request=before_request,
            )

        self.assertEqual(before_request.await_count, 2)

    async def test_non_grounding_provider_error_does_not_repeat_generation(self):
        failure = AutomationOperationError("AI_PROVIDER_UNAVAILABLE")
        with patch(
            "src.tools.requirement_document_workflow.require_operation",
            new=AsyncMock(side_effect=failure),
        ) as operation:
            with self.assertRaises(AutomationOperationError) as raised:
                await generate_grounded_test_case_preview(
                    "version-1", {}, {"instruction": "original"}
                )

        self.assertIs(raised.exception, failure)
        operation.assert_awaited_once()

    def test_frozen_test_case_readback_must_preserve_exact_trace_links(self):
        case = {
            "_id": "TC-1",
            "project_id": "project-1",
            "status": "ACTIVE",
            "current_version_id": "TCV-2",
        }
        version = {
            "_id": "TCV-2",
            "project_id": "project-1",
            "test_case_id": "TC-1",
            "status": "ACTIVE",
            "requirement_version_ids": ["REQV-1"],
            "coverage_obligations": ["LOGIN_ACCESS"],
            "evidence_refs": ["DOCV-1"],
            "evidence_quotes": [
                {
                    "evidence_ref": "DOCV-1",
                    "quote": self.obligation["source_quote"],
                }
            ],
        }
        self.assertTrue(
            verified_test_case_publication_readback(
                "project-1", case, version, case, version
            )
        )
        self.assertFalse(
            verified_test_case_publication_readback(
                "project-1",
                case,
                version,
                case,
                {**version, "coverage_obligations": []},
            )
        )
        self.assertFalse(
            verified_test_case_publication_readback(
                "project-1",
                case,
                version,
                case,
                {**version, "evidence_quotes": []},
            )
        )
        authored_version = {**version, "title": "AI-generated title"}
        self.assertFalse(
            verified_test_case_publication_readback(
                "project-1",
                case,
                authored_version,
                case,
                {**authored_version, "title": "Unexpected frozen title"},
            )
        )


if __name__ == "__main__":
    unittest.main()
