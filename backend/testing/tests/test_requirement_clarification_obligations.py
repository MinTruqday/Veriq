import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.modules.requirements.services import requirement_clarifications
from src.modules.requirements.services.requirement_clarifications import _create
from src.repositories import requirement_clarification as clarification_repository_module
from src.schemas.contracts.requirement_clarification import RequirementClarificationCreate


class RequirementClarificationObligationTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_rejects_clarification_when_source_revision_is_stale(self):
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        find_one = AsyncMock(return_value=None)
        database_value = SimpleNamespace(
            requirement_versions=SimpleNamespace(find_one=find_one)
        )
        client = _DatabaseClient(database_value, session)
        with (
            patch.object(requirement_clarifications.database, "client", client),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "insert",
                new=AsyncMock(),
            ) as insert,
            patch.object(
                requirement_clarifications.requirement_repository,
                "bump_clarification_gate_revision",
                new=AsyncMock(),
            ) as bump_gate,
            patch.object(requirement_clarifications, "audit", new=AsyncMock()) as audit,
        ):
            with self.assertRaises(HTTPException) as raised:
                await _create(
                    "PRJ-1",
                    "REQ-1",
                    "REQV-1",
                    {"question": "Nêu rõ kết quả", "reason": "Thiếu kết quả"},
                    SimpleNamespace(id="qa-1"),
                    expected_version_revision=4,
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "REQUIREMENT_VERSION_CHANGED")
        insert.assert_not_awaited()
        bump_gate.assert_not_awaited()
        audit.assert_not_awaited()
        self.assertEqual(
            find_one.await_args.args[0],
            {
                "_id": "REQV-1",
                "project_id": "PRJ-1",
                "requirement_id": "REQ-1",
                "revision": 4,
            },
        )

    async def test_historical_requirement_version_cannot_resolve_clarification(self):
        clarification = {
            "_id": "RCL-1",
            "project_id": "PRJ-1",
            "requirement_id": "REQ-1",
            "requirement_version_id": "REQV-1",
            "status": "ANSWERED",
        }
        current_requirement = {"current_version_id": "REQV-2"}
        payload = SimpleNamespace(
            requirement_version_id="REQV-1",
            evidence_quote="Bằng chứng có trong phiên bản cũ",
        )
        with (
            patch.object(requirement_clarifications, "require_automation_publication_authority"),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "find",
                new=AsyncMock(return_value=clarification),
            ),
            patch.object(
                requirement_clarifications,
                "get_project_entity",
                new=AsyncMock(return_value=current_requirement),
            ),
            patch.object(requirement_clarifications, "_require_role", new=AsyncMock()),
            patch.object(
                requirement_clarifications.requirement_repository,
                "find_version",
                new=AsyncMock(return_value={"_id": "REQV-1"}),
            ),
            patch.object(
                requirement_clarifications,
                "_replace_and_audit",
                new=AsyncMock(),
            ) as replace,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_clarifications.resolve_clarification(
                    "RCL-1", payload, SimpleNamespace(id="qa-1")
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "RESOLUTION_VERSION_NOT_CURRENT")
        replace.assert_not_awaited()

    async def test_resolution_after_requirement_version_change_uses_clarification_source_revision(self):
        clarification = {
            "_id": "RCL-1",
            "project_id": "PRJ-1",
            "requirement_id": "REQ-1",
            "requirement_version_id": "REQV-1",
            "status": "ANSWERED",
        }
        current_requirement = {"current_version_id": "REQV-2"}
        current_version = {
            "_id": "REQV-2",
            "revision": 3,
            "status": "DRAFT",
            "content_doc": {"type": "doc", "content": []},
            "business_rules": [],
        }
        source_version = {"_id": "REQV-1", "revision": 1}
        payload = SimpleNamespace(
            expected_revision=2,
            requirement_version_id="REQV-2",
            evidence_quote="Bằng chứng trong phiên bản hiện tại",
        )
        with (
            patch.object(requirement_clarifications, "require_automation_publication_authority"),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "find",
                new=AsyncMock(return_value=clarification),
            ),
            patch.object(
                requirement_clarifications,
                "get_project_entity",
                new=AsyncMock(return_value=current_requirement),
            ),
            patch.object(requirement_clarifications, "_require_role", new=AsyncMock()),
            patch.object(
                requirement_clarifications.requirement_repository,
                "find_version",
                new=AsyncMock(side_effect=[current_version, source_version]),
            ),
            patch.object(
                requirement_clarifications.requirement_repository,
                "list_acceptance_criteria",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_clarifications,
                "_version_evidence",
                return_value="bằng chứng trong phiên bản hiện tại",
            ),
            patch.object(
                requirement_clarifications,
                "_replace_and_audit",
                new=AsyncMock(return_value={"_id": "RCL-1", "status": "RESOLVED"}),
            ) as replace,
        ):
            await requirement_clarifications.resolve_clarification(
                "RCL-1", payload, SimpleNamespace(id="qa-1")
            )

        self.assertEqual(replace.await_args.kwargs["requirement_current_version_id"], "REQV-2")
        self.assertEqual(replace.await_args.kwargs["requirement_version_revision"], 1)

    async def test_historical_requirement_version_cannot_be_decided(self):
        clarification = {
            "_id": "RCL-1",
            "project_id": "PRJ-1",
            "requirement_id": "REQ-1",
            "requirement_version_id": "REQV-1",
            "status": "ANSWERED",
        }
        payload = SimpleNamespace(
            expected_revision=3,
            status="WAIVED",
            reason="Đã ghi nhận rủi ro trong phiên bản mới.",
        )
        with (
            patch.object(requirement_clarifications, "require_automation_publication_authority"),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "find",
                new=AsyncMock(return_value=clarification),
            ),
            patch.object(
                requirement_clarifications,
                "get_project_entity",
                new=AsyncMock(return_value={"current_version_id": "REQV-2"}),
            ),
            patch.object(requirement_clarifications, "_require_role", new=AsyncMock()),
            patch.object(
                requirement_clarifications.requirement_repository,
                "find_version",
                new=AsyncMock(return_value={"_id": "REQV-1", "revision": 4}),
            ),
            patch.object(
                requirement_clarifications,
                "_replace_and_audit",
                new=AsyncMock(),
            ) as replace,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_clarifications.decide_clarification(
                    "RCL-1", payload, SimpleNamespace(id="qa-1")
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "CLARIFICATION_VERSION_NOT_CURRENT")
        replace.assert_not_awaited()

    async def test_clarification_decision_fences_current_requirement_revision(self):
        clarification = {
            "_id": "RCL-1",
            "project_id": "PRJ-1",
            "requirement_id": "REQ-1",
            "requirement_version_id": "REQV-1",
            "status": "ANSWERED",
        }
        version = {"_id": "REQV-1", "revision": 7, "status": "DRAFT"}
        payload = SimpleNamespace(
            expected_revision=3,
            status="NOT_APPLICABLE",
            reason="Bằng chứng mới cho thấy mục này không áp dụng.",
        )
        with (
            patch.object(requirement_clarifications, "require_automation_publication_authority"),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "find",
                new=AsyncMock(return_value=clarification),
            ),
            patch.object(
                requirement_clarifications,
                "get_project_entity",
                new=AsyncMock(return_value={"current_version_id": "REQV-1"}),
            ),
            patch.object(requirement_clarifications, "_require_role", new=AsyncMock()),
            patch.object(
                requirement_clarifications.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=version),
            ),
            patch.object(
                requirement_clarifications,
                "_replace_and_audit",
                new=AsyncMock(return_value={"_id": "RCL-1", "status": "NOT_APPLICABLE"}),
            ) as replace,
        ):
            await requirement_clarifications.decide_clarification(
                "RCL-1", payload, SimpleNamespace(id="qa-1")
            )

        self.assertEqual(
            replace.await_args.kwargs["requirement_current_version_id"], "REQV-1"
        )
        self.assertEqual(replace.await_args.kwargs["requirement_version_revision"], 7)

    async def test_resolution_current_version_check_shares_transaction_with_audit(self):
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        updated = {"_id": "RCL-1", "status": "RESOLVED"}
        requirement_update = SimpleNamespace(matched_count=1)
        requirements = SimpleNamespace(update_one=AsyncMock(return_value=requirement_update))
        database_value = SimpleNamespace(requirements=requirements)
        client = _DatabaseClient(database_value, session)
        clarification = {
            "_id": "RCL-1",
            "project_id": "PRJ-1",
            "requirement_id": "REQ-1",
            "requirement_version_id": "REQV-1",
            "revision": 3,
        }
        payload = SimpleNamespace(expected_revision=3)
        with (
            patch.object(requirement_clarifications.database, "client", client),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "replace",
                new=AsyncMock(return_value=updated),
            ) as replace,
            patch.object(
                requirement_clarifications.requirement_repository,
                "bump_clarification_gate_revision",
                new=AsyncMock(return_value=True),
            ) as bump_gate,
            patch.object(requirement_clarifications, "audit", new=AsyncMock()) as audit,
        ):
            result = await requirement_clarifications._replace_and_audit(
                clarification,
                payload,
                {"status": "RESOLVED", "updated_at": "2026-10-26T00:00:00Z"},
                SimpleNamespace(id="qa-1"),
                "requirement_clarification_resolved",
                requirement_current_version_id="REQV-2",
                requirement_version_revision=5,
            )

        self.assertIs(result, updated)
        self.assertEqual(
            requirements.update_one.await_args.args[0],
            {
                "_id": "REQ-1",
                "project_id": "PRJ-1",
                "current_version_id": "REQV-2",
            },
        )
        self.assertIs(requirements.update_one.await_args.kwargs["session"], session)
        self.assertIs(replace.await_args.kwargs["session"], session)
        self.assertIs(bump_gate.await_args.kwargs["session"], session)
        self.assertEqual(bump_gate.await_args.kwargs["expected_revision"], 5)
        self.assertIs(audit.await_args.kwargs["session"], session)

    async def test_resolution_aborts_when_requirement_revision_changes_before_commit(self):
        session = _AsyncSession()
        requirement_update = SimpleNamespace(matched_count=1)
        requirements = SimpleNamespace(update_one=AsyncMock(return_value=requirement_update))
        client = _DatabaseClient(SimpleNamespace(requirements=requirements), session)
        clarification = {
            "_id": "RCL-1",
            "project_id": "PRJ-1",
            "requirement_id": "REQ-1",
            "requirement_version_id": "REQV-1",
            "revision": 3,
        }
        with (
            patch.object(requirement_clarifications.database, "client", client),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "replace",
                new=AsyncMock(),
            ) as replace,
            patch.object(
                requirement_clarifications.requirement_repository,
                "bump_clarification_gate_revision",
                new=AsyncMock(return_value=False),
            ) as bump_gate,
            patch.object(requirement_clarifications, "audit", new=AsyncMock()) as audit,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_clarifications._replace_and_audit(
                    clarification,
                    SimpleNamespace(expected_revision=3),
                    {"status": "RESOLVED", "updated_at": "2026-10-26T00:00:00Z"},
                    SimpleNamespace(id="qa-1"),
                    "requirement_clarification_resolved",
                    requirement_current_version_id="REQV-1",
                    requirement_version_revision=5,
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "REQUIREMENT_VERSION_CHANGED")
        replace.assert_awaited_once()
        audit.assert_not_awaited()
        self.assertEqual(bump_gate.await_args.kwargs["expected_revision"], 5)

    async def test_open_clarification_gate_uses_complete_paged_query_in_transaction(self):
        session = object()
        items = [{"_id": f"RCL-{index}"} for index in range(1001)]
        with patch.object(
            clarification_repository_module.common_repository,
            "list_all_by_id",
            new=AsyncMock(return_value=items),
        ) as list_all:
            result = await clarification_repository_module.requirement_clarification_repository.list_open_for_version(
                "PRJ-1", "REQV-1", session=session
            )

        self.assertEqual(len(result), 1001)
        self.assertEqual(
            list_all.await_args.args,
            (
                "requirement_clarifications",
                {
                    "project_id": "PRJ-1",
                    "requirement_version_id": "REQV-1",
                    "status": {"$in": ["OPEN", "ANSWERED"]},
                },
                session,
            ),
        )

    async def test_requirement_list_reads_all_open_clarifications_across_versions(self):
        items = [{"_id": f"RCL-{index}"} for index in range(5001)]
        with patch.object(
            clarification_repository_module.common_repository,
            "list_all_by_id",
            new=AsyncMock(return_value=items),
        ) as list_all:
            result = await clarification_repository_module.requirement_clarification_repository.list_open_for_versions(
                "PRJ-1", ["REQV-1", "REQV-2"]
            )

        self.assertEqual(len(result), 5001)
        self.assertEqual(
            list_all.await_args.args,
            (
                "requirement_clarifications",
                {
                    "project_id": "PRJ-1",
                    "requirement_version_id": {"$in": ["REQV-1", "REQV-2"]},
                    "status": {"$in": ["OPEN", "ANSWERED"]},
                },
            ),
        )

    async def test_new_requirement_version_keeps_answered_clarification_resolvable(self):
        update_many = AsyncMock()
        database_value = SimpleNamespace(requirement_clarifications=SimpleNamespace(update_many=update_many))
        session = object()
        with patch.object(
            clarification_repository_module, "database", SimpleNamespace(value=database_value)
        ):
            await clarification_repository_module.requirement_clarification_repository.supersede_for_requirement(
                "PRJ-1", "REQ-1", "REQV-2", "2026-10-25T00:00:00Z", session=session
            )

        query = update_many.await_args.args[0]
        self.assertEqual(query["status"], "OPEN")
        self.assertEqual(query["requirement_version_id"], {"$ne": "REQV-2"})
        self.assertIs(update_many.await_args.kwargs["session"], session)

    async def test_version_detail_returns_every_clarification_newest_first(self):
        records = [
            {"_id": "RCL-OLD", "created_at": "2025-01-01T00:00:00+00:00"},
            {"_id": "RCL-NEW", "created_at": "2026-01-01T00:00:00+00:00"},
        ]
        with patch.object(
            clarification_repository_module.common_repository,
            "list_all_by_id",
            new=AsyncMock(return_value=records),
        ) as list_all:
            result = await clarification_repository_module.requirement_clarification_repository.list_for_version(
                "PRJ-1", "REQV-1"
            )

        self.assertEqual([item["_id"] for item in result], ["RCL-NEW", "RCL-OLD"])
        self.assertEqual(list_all.await_args.args[0], "requirement_clarifications")
        self.assertEqual(
            list_all.await_args.args[1],
            {"project_id": "PRJ-1", "requirement_version_id": "REQV-1"},
        )

    async def test_generate_clarifications_retries_concurrent_duplicate_as_idempotent(self):
        version = {
            "_id": "REQV-1",
            "requirement_id": "REQ-1",
            "project_id": "PRJ-1",
            "revision": 1,
        }
        findings = [
            {
                "severity": "error",
                "rule_id": "RULE-1",
                "target_field": "actor",
                "suggestion": "Nêu rõ tác nhân.",
                "message": "Thiếu tác nhân.",
            },
            {
                "severity": "error",
                "rule_id": "RULE-2",
                "target_field": "outcome",
                "suggestion": "Nêu rõ kết quả.",
                "message": "Thiếu kết quả.",
            },
        ]
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(side_effect=[session, session]))
        previously_resolved_finding = {"_id": "RCL-EXISTING", "status": "RESOLVED"}
        with (
            patch.object(requirement_clarifications.database, "client", client),
            patch.object(
                requirement_clarifications,
                "get_project_entity",
                new=AsyncMock(return_value=version),
            ),
            patch.object(requirement_clarifications, "_require_question_author", new=AsyncMock()),
            patch.object(
                requirement_clarifications.requirement_repository,
                "list_acceptance_criteria",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(requirement_clarifications, "requirement_findings", return_value=findings),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "find_finding",
                new=AsyncMock(
                    side_effect=[None, None, previously_resolved_finding, previously_resolved_finding]
                ),
            ) as find_active,
            patch.object(
                requirement_clarifications,
                "_create",
                new=AsyncMock(side_effect=[{"_id": "RCL-NEW"}, DuplicateKeyError("concurrent insert")]),
            ) as create,
        ):
            result = await requirement_clarifications.generate_clarifications(
                "REQV-1", SimpleNamespace(id="qa-1")
            )

        self.assertEqual(result, [])
        self.assertEqual(client.start_session.await_count, 2)
        self.assertEqual(find_active.await_count, 4)
        self.assertEqual(create.await_count, 2)
        self.assertTrue(create.await_args_list[0].kwargs["clarification_id"].startswith("RCL-"))
        self.assertTrue(create.await_args_list[1].kwargs["clarification_id"].startswith("RCL-"))

    async def test_create_persists_explicit_obligation_and_coverage_links(self):
        payload = RequirementClarificationCreate(
            question="Quy tắc nào cần áp dụng?",
            reason="Nguồn có hai hành vi mâu thuẫn.",
            source_ref="DOC-1",
            source_quote="Nguồn mô tả hành vi đăng nhập.",
            unlocks_obligation_keys=["login-valid", "login-valid", "login-invalid"],
            unlocks_source_quotes=["Đăng nhập hợp lệ.", "Đăng nhập hợp lệ."],
            unlocks_coverage_item_ids=["COV-1", "COV-1", "COV-2"],
        )
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))

        with (
            patch.object(requirement_clarifications.database, "client", client),
            patch(
                "src.modules.requirements.services.requirement_clarifications.requirement_clarification_repository.insert",
                new=AsyncMock(),
            ) as insert,
            patch.object(
                requirement_clarifications.requirement_repository,
                "bump_clarification_gate_revision",
                new=AsyncMock(return_value=True),
            ) as bump_gate,
            patch(
                "src.modules.requirements.services.requirement_clarifications.audit",
                new=AsyncMock(),
            ) as audit,
        ):
            created = await _create(
                "PRJ-1",
                "REQ-1",
                "REQV-1",
                payload.model_dump(),
                SimpleNamespace(id="qa-1"),
            )

        self.assertEqual(created["unlocks_obligation_keys"], ["login-valid", "login-invalid"])
        self.assertEqual(created["unlocks_source_quotes"], ["Đăng nhập hợp lệ."])
        self.assertEqual(created["unlocks_coverage_item_ids"], ["COV-1", "COV-2"])
        insert.assert_awaited_once_with(created, session=session)
        self.assertIs(bump_gate.await_args.kwargs["session"], session)
        audit.assert_awaited_once()
        self.assertIs(audit.await_args.kwargs["session"], session)

    async def test_clarification_update_and_audit_share_a_transaction(self):
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        clarification = {
            "_id": "RCL-1",
            "project_id": "PRJ-1",
            "requirement_version_id": "REQV-1",
            "revision": 4,
        }
        payload = SimpleNamespace(expected_revision=4)
        updated = {**clarification, "revision": 5, "status": "ANSWERED"}
        with (
            patch.object(requirement_clarifications.database, "client", client),
            patch.object(
                requirement_clarifications.requirement_clarification_repository,
                "replace",
                new=AsyncMock(return_value=updated),
            ) as replace,
            patch.object(
                requirement_clarifications.requirement_repository,
                "bump_clarification_gate_revision",
                new=AsyncMock(return_value=True),
            ) as bump_gate,
            patch.object(requirement_clarifications, "audit", new=AsyncMock()) as audit,
        ):
            result = await requirement_clarifications._replace_and_audit(
                clarification,
                payload,
                {"status": "ANSWERED"},
                SimpleNamespace(id="ba-1"),
                "requirement_clarification_answered",
            )

        self.assertIs(result, updated)
        self.assertIs(replace.await_args.kwargs["session"], session)
        self.assertIs(bump_gate.await_args.kwargs["session"], session)
        self.assertIs(audit.await_args.kwargs["session"], session)

    def test_legacy_create_payload_defaults_to_no_obligation_links(self):
        payload = RequirementClarificationCreate(
            question="Câu hỏi làm rõ",
            reason="Nguồn hiện chưa xác định hành vi.",
        )

        self.assertEqual(payload.unlocks_obligation_keys, [])
        self.assertEqual(payload.unlocks_source_quotes, [])
        self.assertEqual(payload.unlocks_coverage_item_ids, [])


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _AsyncSession(_AsyncContext):
    def start_transaction(self):
        return _AsyncContext()

    async def with_transaction(self, callback):
        return await callback(self)


class _DatabaseClient:
    def __init__(self, value, session):
        self.value = value
        self.start_session = AsyncMock(return_value=session)

    def __getitem__(self, _name):
        return self.value
