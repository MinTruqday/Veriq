import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from src.repositories import requirement_import as requirement_import_repository_module
from src.modules.requirements.services import requirement_import_workflow
from src.modules.requirements.services import requirement_indexing
from src.schemas.contracts.requirements import RequirementImportResolution


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class Session:
    def start_transaction(self):
        return AsyncContext(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class RequirementImportCandidateResolutionTests(unittest.IsolatedAsyncioTestCase):
    def test_paraphrased_ai_citation_returns_reviewable_draft(self):
        source = "Nếu người dùng nhập sai mật khẩu, hệ thống hiển thị thông báo lỗi."
        document = {
            "_id": "DOC-1",
            "content_hash": "source-hash",
            "source_version": "1",
            "normalized_content": source,
            "format": "docx",
            "source_type": "SPECIFICATION",
        }
        reference = "DOC-1:0"
        result = {
            "conflicts": [],
            "suggestions": [
                {
                    "requirement_key": "REQ-1",
                    "title": "Thông báo khi đăng nhập sai",
                    "type": "FUNCTIONAL",
                    "content": "Khi mật khẩu không đúng, hệ thống sẽ thông báo đăng nhập thất bại.",
                    "evidence_refs": [reference],
                    "source_quotes": {
                        reference: "Khi mật khẩu không đúng, hệ thống sẽ thông báo đăng nhập thất bại."
                    },
                    "acceptance_criteria": [],
                    "actors": [],
                    "business_rules": [],
                    "dependencies": [],
                }
            ],
        }

        candidates, conflicts = requirement_import_workflow.grounded_requirement_candidates(
            document, [result]
        )

        self.assertEqual(conflicts, [])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_grounding_status"], "NEEDS_REVIEW")
        self.assertEqual(candidates[0]["source_refs"][0]["requirement_document_id"], "DOC-1")
        self.assertNotIn("source_quote", candidates[0]["source_refs"][0])
        self.assertIn(
            "REQUIREMENT_SOURCE_REVIEW_REQUIRED",
            requirement_import_workflow.prepare_requirement_candidates("JOB-1", candidates)[0]["quality_issues"],
        )

    async def test_structured_source_span_uses_rendered_document_text(self):
        source = "Nếu người dùng nhập sai mật khẩu, hệ thống hiển thị thông báo lỗi."
        source_doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": source}],
                }
            ],
        }
        reference = {
            "requirement_document_id": "DOC-1",
            "content_hash": "source-hash",
            "source_version": "1",
            "source_start": 0,
            "source_end": len(source),
            "source_text_hash": __import__("hashlib").sha256(source.encode("utf-8")).hexdigest(),
            "source_quote": source,
        }
        document = {
            "_id": "DOC-1",
            "project_id": "PROJECT-1",
            "content_hash": "source-hash",
            "source_version": "1",
            "normalized_content": source_doc,
        }
        with (
            patch.object(
                requirement_indexing.requirement_document_repository,
                "list_by_ids",
                new=AsyncMock(return_value=[document]),
            ),
            patch(
                "src.modules.requirements.services.requirement_documents.require_document_access",
                new=AsyncMock(),
            ),
        ):
            await requirement_indexing.validate_requirement_sources(
                "PROJECT-1", [reference], SimpleNamespace(id="user-1")
            )

    async def test_semantic_duplicate_candidate_is_preserved_for_review(self):
        candidate = {
            "candidate_id": "CAND-1",
            "requirement_key": "REQ-NEW",
            "title": "Đăng nhập bằng tài khoản",
            "type": "FUNCTIONAL",
            "content_doc": {"type": "doc", "content": []},
            "acceptance_criteria": [],
        }
        job = {"_id": "IMPORT-1", "project_id": "PRJ-1", "revision": 1, "preview": [candidate]}
        requirement = {
            "_id": "REQ-1",
            "project_id": "PRJ-1",
            "requirement_key": "REQ-1",
            "current_version_id": "REQV-1",
            "status": "ACTIVE",
        }
        version = {
            "_id": "REQV-1",
            "project_id": "PRJ-1",
            "requirement_id": "REQ-1",
            "type": "FUNCTIONAL",
            "title": "Người dùng xác thực danh tính",
            "content_doc": {"type": "doc", "content": []},
        }
        with (
            patch.object(requirement_import_workflow, "authorize_requirement_import_job", new=AsyncMock()),
            patch.object(requirement_import_workflow, "get_project", new=AsyncMock()),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "list_current_requirements",
                new=AsyncMock(return_value=([requirement], {"REQV-1": version})),
            ),
            patch.object(
                requirement_import_workflow.analysis_repository,
                "list_acceptance_criteria",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_import_workflow,
                "requirement_duplicate_score",
                return_value=(0.12, []),
            ),
            patch.object(
                requirement_import_workflow,
                "search_project_with_status",
                new=AsyncMock(
                    return_value={
                        "degraded_mode": "NORMAL",
                        "items": [{"artifact_version_id": "REQV-1"}],
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow,
                "compare_project_text_semantics",
                new=AsyncMock(return_value=[0.91]),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "list_linked_test_cases",
                new=AsyncMock(return_value=([], [])),
            ),
        ):
            result = await requirement_import_workflow.compare_requirement_import_job(
                job, SimpleNamespace(id="user-1")
            )

        matches = result["comparisons"][0]["matches"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["requirement_id"], "REQ-1")
        self.assertEqual(matches[0]["match_type"], "POSSIBLE")
        self.assertEqual(matches[0]["score"], 0.91)

    def test_strong_semantic_match_is_not_suppressed_by_low_lexical_similarity(self):
        score = requirement_import_workflow.requirement_import_match_score(
            lexical_score=0.12,
            semantic_score=0.91,
            threshold=0.72,
        )

        self.assertEqual(score, 0.91)

    def test_semantic_score_below_review_threshold_keeps_combined_score(self):
        score = requirement_import_workflow.requirement_import_match_score(
            lexical_score=0.12,
            semantic_score=0.68,
            threshold=0.72,
        )

        self.assertAlmostEqual(score, (0.12 * 0.68) ** 0.5)

    async def test_already_linked_source_resolves_candidate_without_new_version(self):
        source_ref = {"requirement_document_id": "DOC-1"}
        candidate = {
            "candidate_id": "CAND-1",
            "source_refs": [source_ref],
        }
        remaining = {"candidate_id": "CAND-2"}
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "PREVIEW_READY",
            "revision": 5,
            "preview": [candidate, remaining],
        }
        requirement = {
            "_id": "REQ-1",
            "project_id": "PROJECT-1",
            "current_version_id": "REQV-1",
        }
        version = {
            "_id": "REQV-1",
            "project_id": "PROJECT-1",
            "requirement_id": "REQ-1",
            "source_refs": [source_ref],
        }
        updated = {
            **job,
            "revision": 7,
            "preview": [remaining],
            "resolutions": [
                {
                    "candidate_id": "CAND-1",
                    "action": "link_source_already_present",
                    "requirement_id": "REQ-1",
                }
            ],
        }
        session = Session()
        payload = RequirementImportResolution(
            expected_revision=5,
            target_requirement_id="REQ-1",
            expected_target_version_id="REQV-1",
            action="link_source",
            reason="Nguồn đã được liên kết ở lần xử lý trước",
        )

        async def get_entity(collection, entity_id, user, permission):
            return job if collection == "import_jobs" else requirement

        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(side_effect=get_entity),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow,
                "compare_requirement_import_job",
                new=AsyncMock(
                    return_value={
                        "comparisons": [
                            {
                                "candidate_id": "CAND-1",
                                "candidate_index": 0,
                                "matches": [
                                    {
                                        "requirement_id": "REQ-1",
                                        "version_id": "REQV-1",
                                        "match_type": "EXACT",
                                    }
                                ],
                            }
                        ]
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow.analysis_repository,
                "list_acceptance_criteria",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "find_current_version",
                new=AsyncMock(return_value=version),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "claim_confirmation",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "finish_resolution",
                new=AsyncMock(return_value=updated),
            ) as finish_resolution,
            patch.object(
                requirement_import_workflow,
                "database",
                SimpleNamespace(
                    client=SimpleNamespace(
                        start_session=AsyncMock(return_value=session)
                    ),
                    value=SimpleNamespace(
                        requirements=SimpleNamespace(
                            find_one=AsyncMock(return_value=requirement)
                        ),
                        requirement_versions=SimpleNamespace(
                            find_one=AsyncMock(return_value=version)
                        ),
                    ),
                ),
            ),
            patch.object(requirement_import_workflow, "audit", new=AsyncMock()),
        ):
            result = await requirement_import_workflow.resolve_requirement_import_candidate(
                "IMPORT-1", "CAND-1", payload, SimpleNamespace(id="user-1")
            )

        self.assertEqual(result["preview"], [remaining])
        self.assertEqual(
            finish_resolution.await_args.args[4]["action"],
            "link_source_already_present",
        )
        self.assertEqual(finish_resolution.await_args.kwargs["session"], session)

    async def test_new_requirement_resolution_stores_ids_for_index_recovery(self):
        captured = {}
        returned = {"_id": "IMPORT-1", "status": "PREVIEW_READY"}

        async def find_one_and_update(query, update, **kwargs):
            captured["query"] = query
            captured["update"] = update
            captured["kwargs"] = kwargs
            return returned

        collection = SimpleNamespace(
            find_one_and_update=AsyncMock(side_effect=find_one_and_update)
        )
        with patch.object(
            requirement_import_repository_module,
            "database",
            SimpleNamespace(value=SimpleNamespace(import_jobs=collection)),
        ):
            result = await requirement_import_repository_module.requirement_import_repository.finish_resolution(
                "IMPORT-1",
                "PROJECT-1",
                8,
                [{"candidate_id": "CAND-2"}],
                {
                    "candidate_id": "CAND-1",
                    "action": "create_requirement",
                    "requirement_id": "REQ-1",
                    "to_version_id": "REQV-1",
                },
                "2026-10-27T00:00:00Z",
            )

        self.assertIs(result, returned)
        self.assertEqual(
            captured["update"]["$addToSet"],
            {
                "created_requirement_ids": "REQ-1",
                "created_requirement_version_ids": "REQV-1",
            },
        )
        self.assertEqual(captured["update"]["$set"]["status"], "PREVIEW_READY")

    async def test_import_confirmation_preserves_versions_resolved_before_batch(self):
        captured = {}

        async def update_one(query, update, **kwargs):
            captured["query"] = query
            captured["update"] = update
            captured["kwargs"] = kwargs
            return SimpleNamespace(matched_count=1)

        collection = SimpleNamespace(update_one=AsyncMock(side_effect=update_one))
        with patch.object(
            requirement_import_repository_module,
            "database",
            SimpleNamespace(value=SimpleNamespace(import_jobs=collection)),
        ):
            result = await requirement_import_repository_module.requirement_import_repository.confirm(
                "IMPORT-1",
                "PROJECT-1",
                "CONFIRMING",
                "CONFIRMED",
                ["REQ-2"],
                [1],
                [0],
                ["REQV-2"],
                "user-1",
                "2026-10-27T00:00:00Z",
            )

        self.assertTrue(result)
        self.assertNotIn("created_requirement_ids", captured["update"]["$set"])
        self.assertNotIn("created_requirement_version_ids", captured["update"]["$set"])
        self.assertEqual(
            captured["update"]["$addToSet"],
            {
                "created_requirement_ids": {"$each": ["REQ-2"]},
                "created_requirement_version_ids": {"$each": ["REQV-2"]},
            },
        )

    async def test_version_resolution_adds_version_to_import_recovery_set(self):
        captured = {}

        async def find_one_and_update(query, update, **kwargs):
            captured["query"] = query
            captured["update"] = update
            captured["kwargs"] = kwargs
            return {"_id": "IMPORT-1", "status": "PREVIEW_READY"}

        collection = SimpleNamespace(
            find_one_and_update=AsyncMock(side_effect=find_one_and_update)
        )
        with patch.object(
            requirement_import_repository_module,
            "database",
            SimpleNamespace(value=SimpleNamespace(import_jobs=collection)),
        ):
            await requirement_import_repository_module.requirement_import_repository.finish_resolution(
                "IMPORT-1",
                "PROJECT-1",
                9,
                [{"candidate_id": "CAND-2"}],
                {
                    "candidate_id": "CAND-1",
                    "action": "create_version",
                    "requirement_id": "REQ-1",
                    "to_version_id": "REQV-2",
                },
                "2026-10-27T00:00:00Z",
            )

        self.assertEqual(
            captured["update"]["$addToSet"],
            {"created_requirement_version_ids": "REQV-2"},
        )

    async def test_candidate_with_possible_match_cannot_be_created_as_new(self):
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "PREVIEW_READY",
            "revision": 4,
            "preview": [{"candidate_id": "CAND-1"}],
        }
        payload = RequirementImportResolution(
            expected_revision=4,
            action="create_requirement",
            reason="Đang xác nhận đây không phải Requirement trùng",
        )
        user = SimpleNamespace(id="user-1")

        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(return_value=job),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow,
                "compare_requirement_import_job",
                new=AsyncMock(
                    return_value={
                        "comparisons": [
                            {
                                "candidate_id": "CAND-1",
                                "candidate_index": 0,
                                "matches": [
                                    {"requirement_id": "REQ-1", "match_type": "POSSIBLE"}
                                ],
                            }
                        ]
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "claim_confirmation",
                new=AsyncMock(return_value=True),
            ) as claim,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_import_workflow.resolve_requirement_import_candidate(
                    "IMPORT-1", "CAND-1", payload, user
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "IMPORT_MATCH_REVIEW_REQUIRED"
        )
        claim.assert_not_awaited()

    async def test_version_creation_and_resolution_share_one_transaction(self):
        candidate = {"candidate_id": "CAND-1", "source_refs": [{"requirement_document_id": "DOC-1"}]}
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "PREVIEW_READY",
            "revision": 3,
            "preview": [candidate],
        }
        requirement = {
            "_id": "REQ-1",
            "project_id": "PROJECT-1",
            "current_version_id": "REQV-1",
            "status": "ACTIVE",
        }
        current = {
            "_id": "REQV-1",
            "project_id": "PROJECT-1",
            "requirement_id": "REQ-1",
            "version": 1,
            "title": "Đăng nhập",
            "type": "functional",
            "content_doc": {"type": "doc", "content": []},
            "source_refs": [],
        }
        version = {"_id": "REQV-2", "project_id": "PROJECT-1"}
        updated = {**job, "status": "CONFIRMED", "preview": []}
        session = Session()
        payload = RequirementImportResolution(
            expected_revision=3,
            target_requirement_id="REQ-1",
            expected_target_version_id="REQV-1",
            action="create_version",
            reason="Cập nhật theo tài liệu mới",
        )

        async def get_entity(collection, entity_id, user, permission):
            return job if collection == "import_jobs" else requirement

        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(side_effect=get_entity),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow,
                "compare_requirement_import_job",
                new=AsyncMock(
                    return_value={
                        "comparisons": [
                            {
                                "candidate_id": "CAND-1",
                                "candidate_index": 0,
                                "matches": [
                                    {
                                        "requirement_id": "REQ-1",
                                        "version_id": "REQV-1",
                                        "match_type": "SAME_KEY",
                                    }
                                ],
                            }
                        ]
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow.analysis_repository,
                "list_acceptance_criteria",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "find_current_version",
                new=AsyncMock(return_value=current),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "claim_confirmation",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                requirement_import_workflow,
                "create_requirement_version_record",
                new=AsyncMock(return_value=version),
            ) as create_version,
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "finish_resolution",
                new=AsyncMock(return_value=updated),
            ) as finish_resolution,
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "confirm_document",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow,
                "index_requirement_version",
                new=AsyncMock(return_value=True),
            ) as index_version,
            patch.object(requirement_import_workflow, "audit", new=AsyncMock()),
            patch.object(
                requirement_import_workflow,
                "database",
                SimpleNamespace(
                    client=SimpleNamespace(start_session=AsyncMock(return_value=session))
                ),
            ),
        ):
            result = await requirement_import_workflow.resolve_requirement_import_candidate(
                "IMPORT-1", "CAND-1", payload, SimpleNamespace(id="user-1")
            )

        self.assertEqual(result["status"], "CONFIRMED")
        self.assertIs(create_version.await_args.kwargs["session"], session)
        self.assertIs(finish_resolution.await_args.kwargs["session"], session)
        index_version.assert_awaited_once_with(version)

    async def test_create_unmatched_candidate_keeps_ambiguous_candidates_pending(self):
        candidate = {
            "candidate_id": "CAND-1",
            "title": "Requirement độc lập",
            "content_doc": {"type": "doc", "content": []},
            "source_refs": [{"requirement_document_id": "DOC-1"}],
        }
        ambiguous_candidate = {
            "candidate_id": "CAND-2",
            "title": "Requirement cần đối chiếu",
            "content_doc": {"type": "doc", "content": []},
            "source_refs": [{"requirement_document_id": "DOC-1"}],
        }
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "PREVIEW_READY",
            "revision": 4,
            "preview": [candidate, ambiguous_candidate],
        }
        updated = {
            **job,
            "status": "PREVIEW_READY",
            "revision": 6,
            "preview": [ambiguous_candidate],
            "created_requirement_ids": ["REQ-1"],
            "created_requirement_version_ids": ["REQV-1"],
            "resolutions": [
                {"candidate_id": "CAND-1", "requirement_id": "REQ-1"}
            ],
        }
        session = Session()
        payload = RequirementImportResolution(
            expected_revision=4,
            action="create_requirement",
            reason="Không có Requirement tương ứng trong dự án",
        )

        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(return_value=job),
            ),
            patch.object(
                requirement_import_workflow,
                "compare_requirement_import_job",
                new=AsyncMock(
                    return_value={
                        "comparisons": [
                            {"candidate_id": "CAND-1", "candidate_index": 0, "matches": []},
                            {
                                "candidate_id": "CAND-2",
                                "candidate_index": 1,
                                "matches": [{"requirement_id": "REQ-X", "match_type": "POSSIBLE"}],
                            },
                        ]
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow,
                "get_project",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "claim_confirmation",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                requirement_import_workflow,
                "create_requirement_record",
                new=AsyncMock(
                    return_value={
                        "_id": "REQ-1",
                        "current_version": {"_id": "REQV-1"},
                    }
                ),
            ) as create_requirement,
            patch.object(
                requirement_import_workflow,
                "index_requirement_version",
                new=AsyncMock(return_value=True),
            ) as index_requirement,
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "finish_resolution",
                new=AsyncMock(return_value=updated),
            ) as finish_resolution,
            patch.object(
                requirement_import_workflow,
                "database",
                SimpleNamespace(
                    client=SimpleNamespace(
                        start_session=AsyncMock(return_value=session)
                    )
                ),
            ),
            patch.object(
                requirement_import_workflow, "audit", new=AsyncMock()
            ),
        ):
            result = await requirement_import_workflow.resolve_requirement_import_candidate(
                "IMPORT-1",
                "CAND-1",
                payload,
                SimpleNamespace(id="user-1"),
            )

        self.assertEqual(result["preview"], [ambiguous_candidate])
        create_requirement.assert_awaited_once()
        index_requirement.assert_awaited_once_with(
            {"_id": "REQV-1"}
        )
        self.assertEqual(
            create_requirement.await_args.kwargs["session"], session
        )
        self.assertEqual(
            finish_resolution.await_args.args[3], [ambiguous_candidate]
        )
        self.assertEqual(
            finish_resolution.await_args.kwargs["session"], session
        )

