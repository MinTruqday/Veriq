import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.services import requirement_ai
from src.schemas.contracts.requirements import RequirementAISuggestionApply


class RequirementAISuggestionTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_quality_analysis_is_read_only_scoped_and_revision_aware(self):
        version = {"_id": "REQV-1", "project_id": "PRJ-1", "revision": 4}
        finding = {
            "_id": "AIF-1",
            "project_id": "PRJ-1",
            "artifact_id": "REQV-1",
            "result_type": "REQUIREMENT_QUALITY_ANALYSIS",
            "artifact_revision": 3,
            "findings": [],
        }
        user = SimpleNamespace(id="USER-1")
        with (
            patch.object(
                requirement_ai,
                "get_project_entity",
                new=AsyncMock(return_value=version),
            ) as get_version,
            patch.object(
                requirement_ai.requirement_ai_repository,
                "find_latest_quality_analysis",
                new=AsyncMock(return_value=finding),
            ) as find_latest,
        ):
            result = await requirement_ai.get_latest_requirement_quality_analysis(
                version["_id"], user
            )

        get_version.assert_awaited_once_with("requirement_versions", "REQV-1", user, "requirement.read")
        find_latest.assert_awaited_once_with("PRJ-1", "REQV-1")
        self.assertTrue(result["is_stale"])

    async def test_quality_analysis_result_and_audit_share_transaction(self):
        version, _, _, _, user = _input()
        session = _Session()
        with _patch_analysis_dependencies(session, version) as calls:
            result = await requirement_ai.analyze_requirement_quality(
                version["_id"],
                SimpleNamespace(idempotency_key="quality-run-0001", instruction=""),
                user,
            )

        self.assertEqual(result["_id"], "AIF-ANALYSIS")
        self.assertIs(result["degraded_mode"], False)
        self.assertIsNone(session.transaction.exception)
        self.assertIs(calls["insert"].await_args.kwargs["session"], session)
        self.assertIs(calls["audit"].await_args.kwargs["session"], session)

    async def test_quality_analysis_audit_failure_aborts_result_insert(self):
        version, _, _, _, user = _input()
        session = _Session()
        with _patch_analysis_dependencies(
            session, version, audit_error=RuntimeError("audit insert failed")
        ) as calls:
            with self.assertRaisesRegex(RuntimeError, "audit insert failed"):
                await requirement_ai.analyze_requirement_quality(
                    version["_id"],
                    SimpleNamespace(idempotency_key="quality-run-0002", instruction=""),
                    user,
                )

        self.assertIs(session.transaction.exception, RuntimeError)
        self.assertIs(calls["insert"].await_args.kwargs["session"], session)

    async def test_applied_suggestion_commits_version_event_marker_and_audit_together(self):
        version, result, suggestion, payload, user = _input()
        updated = {**version, "revision": 5, "title": suggestion["revised_title"]}
        session = _Session()
        with _patch_dependencies(
            session,
            version,
            result,
            updated,
            mark_result=True,
        ) as calls:
            response = await requirement_ai.apply_requirement_quality_suggestion(
                version["_id"], payload, user
            )

        self.assertEqual(response, updated)
        self.assertIsNone(session.transaction.exception)
        self.assertIs(calls["update"].await_args.kwargs["session"], session)
        self.assertIs(calls["mark"].await_args.kwargs["session"], session)
        self.assertIs(calls["queue"].await_args.args[2], session)
        self.assertIs(calls["audit"].await_args.kwargs["session"], session)

    async def test_stale_ai_suggestion_is_rejected_before_transaction(self):
        version, result, _, payload, user = _input()
        result["artifact_revision"] = version["revision"] - 1
        session = _Session()
        updated = {**version, "revision": 5}
        with _patch_dependencies(
            session, version, result, updated, mark_result=True
        ) as calls:
            with self.assertRaises(HTTPException) as error:
                await requirement_ai.apply_requirement_quality_suggestion(
                    version["_id"], payload, user
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "AI_SUGGESTION_STALE")
        calls["find_version"].assert_not_awaited()
        calls["update"].assert_not_awaited()

    async def test_ai_suggestion_revision_is_rechecked_inside_transaction(self):
        version, result, _, payload, user = _input()
        stale_result = {**result, "artifact_revision": version["revision"] - 1}
        updated = {**version, "revision": 5}
        session = _Session()
        with _patch_dependencies(
            session, version, result, updated, mark_result=True
        ) as calls:
            calls["find_finding"].side_effect = [result, stale_result]
            with self.assertRaises(HTTPException) as error:
                await requirement_ai.apply_requirement_quality_suggestion(
                    version["_id"], payload, user
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "AI_SUGGESTION_STALE")
        self.assertIs(session.transaction.exception, HTTPException)
        calls["update"].assert_not_awaited()

    async def test_failed_suggestion_marker_rolls_back_without_event_or_audit(self):
        version, result, suggestion, payload, user = _input()
        updated = {**version, "revision": 5, "title": suggestion["revised_title"]}
        session = _Session()
        with _patch_dependencies(
            session,
            version,
            result,
            updated,
            mark_result=False,
        ) as calls:
            with self.assertRaises(HTTPException) as error:
                await requirement_ai.apply_requirement_quality_suggestion(
                    version["_id"], payload, user
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertIs(session.transaction.exception, HTTPException)
        calls["queue"].assert_not_awaited()
        calls["audit"].assert_not_awaited()

    async def test_acceptance_criteria_failure_rolls_back_version_and_outbox(self):
        version, result, suggestion, payload, user = _input()
        criterion = {
            "key": "LOGIN_VALID",
            "content_doc": {
                "type": "doc",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Đăng nhập thành công."}]}
                ],
            },
        }
        suggestion["patch"] = {"acceptance_criteria": [criterion]}
        result["suggestions"] = [suggestion]
        updated = {**version, "revision": 5, "title": suggestion["revised_title"]}
        session = _Session()
        with _patch_dependencies(
            session,
            version,
            result,
            updated,
            mark_result=True,
            persist_error=RuntimeError("acceptance criterion insert failed"),
        ) as calls:
            with self.assertRaisesRegex(RuntimeError, "acceptance criterion insert failed"):
                await requirement_ai.apply_requirement_quality_suggestion(
                    version["_id"], payload, user
                )

        self.assertIs(session.transaction.exception, RuntimeError)
        calls["delete_criteria"].assert_awaited_once_with(
            version["_id"], session=session
        )
        calls["persist_criteria"].assert_awaited_once()
        self.assertIs(calls["persist_criteria"].await_args.kwargs["session"], session)
        calls["mark"].assert_not_awaited()
        calls["queue"].assert_not_awaited()
        calls["audit"].assert_not_awaited()


def _input():
    version = {
        "_id": "REQV-1",
        "project_id": "PRJ-1",
        "requirement_id": "REQ-1",
        "status": "DRAFT",
        "revision": 4,
        "title": "Đăng nhập",
        "plain_text_projection": "Người dùng đăng nhập",
        "content_doc": {},
    }
    suggestion = {
        "suggestion_id": "REQ-SUG-1",
        "revised_title": "Đăng nhập bằng mật khẩu",
        "patch": {},
        "reason_codes": ["TITLE_MORE_SPECIFIC"],
        "evidence_refs": ["REQV-1"],
    }
    result = {
        "_id": "AIF-1",
        "project_id": "PRJ-1",
        "artifact_id": "REQV-1",
        "result_type": "REQUIREMENT_QUALITY_ANALYSIS",
        "artifact_revision": 4,
        "status": "SUCCESS",
        "suggestions": [suggestion],
    }
    payload = RequirementAISuggestionApply(
        expected_revision=4,
        ai_result_id="AIF-1",
        suggestion_id="REQ-SUG-1",
    )
    user = SimpleNamespace(id="USER-1", _ai_automation_run_id=None)
    return version, result, suggestion, payload, user


def _patch_analysis_dependencies(session, version, audit_error=None):
    class Dependencies:
        def __enter__(self):
            self.stack = patch.multiple(
                requirement_ai.database,
                client=SimpleNamespace(start_session=AsyncMock(return_value=session)),
            )
            self.stack.__enter__()
            self.patches = {
                "get_version": patch.object(
                    requirement_ai,
                    "get_project_entity",
                    new=AsyncMock(return_value=version),
                ),
                "find_existing": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "find_finding",
                    new=AsyncMock(return_value=None),
                ),
                "list_criteria": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "list_acceptance_criteria",
                    new=AsyncMock(return_value=[]),
                ),
                "rules": patch.object(
                    requirement_ai,
                    "requirement_findings",
                    return_value=[],
                ),
                "model": patch.object(
                    requirement_ai,
                    "request_ai_automation",
                    new=AsyncMock(
                        return_value={
                            "status": "SUCCESS",
                            "degraded_mode": None,
                            "findings": [],
                            "suggestions": [],
                        }
                    ),
                ),
                "contract": patch.object(
                    requirement_ai,
                    "ai_contract_metadata",
                    return_value={"status": "SUCCESS", "degraded_mode": None},
                ),
                "new_id": patch.object(
                    requirement_ai, "new_id", return_value="AIF-ANALYSIS"
                ),
                "insert": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "insert_finding",
                    new=AsyncMock(),
                ),
                "audit": patch.object(
                    requirement_ai,
                    "audit",
                    new=AsyncMock(side_effect=audit_error),
                ),
            }
            self.calls = {}
            for key, value in self.patches.items():
                self.calls[key] = value.__enter__()
            return self

        def __exit__(self, exc_type, exc, traceback):
            for value in reversed(list(self.patches.values())):
                value.__exit__(exc_type, exc, traceback)
            self.stack.__exit__(exc_type, exc, traceback)
            return False

        def __getitem__(self, key):
            return self.calls[key]

    return Dependencies()


def _patch_dependencies(
    session, version, result, updated, mark_result, persist_error=None
):
    class Dependencies:
        def __enter__(self):
            self.stack = patch.multiple(
                requirement_ai.database,
                client=SimpleNamespace(start_session=AsyncMock(return_value=session)),
            )
            self.stack.__enter__()
            self.patches = {
                "get_project_entity": patch.object(
                    requirement_ai,
                    "get_project_entity",
                    new=AsyncMock(return_value=version),
                ),
                "find_version": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "find_requirement_version",
                    new=AsyncMock(return_value=version),
                ),
                "find_finding": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "find_finding",
                    new=AsyncMock(return_value=result),
                ),
                "list_criteria": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "list_acceptance_criteria",
                    new=AsyncMock(return_value=[]),
                ),
                "get_project": patch.object(
                    requirement_ai,
                    "get_project",
                    new=AsyncMock(),
                ),
                "update": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "update_requirement",
                    new=AsyncMock(return_value=updated),
                ),
                "delete_criteria": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "delete_acceptance_criteria",
                    new=AsyncMock(),
                ),
                "persist_criteria": patch.object(
                    requirement_ai,
                    "persist_acceptance_criteria",
                    new=AsyncMock(side_effect=persist_error),
                ),
                "mark": patch.object(
                    requirement_ai.requirement_ai_repository,
                    "mark_suggestion_applied",
                    new=AsyncMock(return_value=mark_result),
                ),
                "queue": patch.object(
                    requirement_ai,
                    "queue_requirement_changed",
                    new=AsyncMock(return_value="EVENT-1"),
                ),
                "audit": patch.object(
                    requirement_ai,
                    "audit",
                    new=AsyncMock(),
                ),
            }
            self.calls = {}
            for key, value in self.patches.items():
                self.calls[key] = value.__enter__()
            return self

        def __exit__(self, exc_type, exc, traceback):
            for value in reversed(list(self.patches.values())):
                value.__exit__(exc_type, exc, traceback)
            self.stack.__exit__(exc_type, exc, traceback)
            return False

        def __getitem__(self, key):
            return self.calls[key]

    return Dependencies()


class _Transaction:
    def __init__(self):
        self.exception = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.exception = exc_type
        return False


class _Session:
    def __init__(self):
        self.transaction = _Transaction()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def start_transaction(self):
        return self.transaction


if __name__ == "__main__":
    unittest.main()
