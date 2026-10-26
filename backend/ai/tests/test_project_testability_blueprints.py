import copy
import hashlib
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.api.automation import list_project_testability_blueprints
from src.core.infrastructure.database import database
from src.repositories.automation import AutomationRepository
from src.schemas.auth import SystemRole
from src.schemas.automation import SourceFact


class _Cursor:
    def __init__(self, values):
        self.values = values

    def sort(self, keys, direction=None):
        if isinstance(keys, str):
            keys = [(keys, direction or 1)]
        for key, order in reversed(keys):
            self.values.sort(key=lambda item: item.get(key), reverse=order < 0)
        return self

    async def to_list(self, length=None):
        return copy.deepcopy(self.values[:length] if length is not None else self.values)


class _Collection:
    def __init__(self):
        self.values = []

    @staticmethod
    def _matches(document, query):
        for key, expected in (query or {}).items():
            actual = document.get(key)
            if isinstance(actual, list):
                if expected not in actual:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, query=None, sort=None):
        values = [item for item in self.values if self._matches(item, query)]
        if sort:
            _Cursor(values).sort(sort)
        return copy.deepcopy(values[0]) if values else None

    def find(self, query=None):
        return _Cursor([item for item in self.values if self._matches(item, query)])

    async def insert_one(self, payload):
        for existing in self.values:
            same_project = existing.get("project_id") == payload.get("project_id")
            if same_project and (
                existing.get("version") == payload.get("version")
                or existing.get("source_digest") == payload.get("source_digest")
                or set(existing.get("automation_run_ids", []))
                & set(payload.get("automation_run_ids", []))
            ):
                raise DuplicateKeyError("duplicate project blueprint")
        self.values.append(copy.deepcopy(payload))

    async def update_one(self, query, update):
        for item in self.values:
            if self._matches(item, query):
                item.setdefault("automation_run_ids", [])
                run_id = update.get("$addToSet", {}).get("automation_run_ids")
                if run_id is not None and run_id not in item["automation_run_ids"]:
                    item["automation_run_ids"].append(run_id)
                return


class _Database:
    def __init__(self):
        self.automation_project_blueprints = _Collection()

    def __getitem__(self, _name):
        return self


class ProjectTestabilityBlueprintRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mongo = _Database()
        self.database_patch = patch.object(database, "mongodb", self.mongo)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.repository = AutomationRepository()

    @staticmethod
    def make_fact(run_id="run-1", version_id="document-v1", quote="Người dùng đăng nhập hợp lệ"):
        return SourceFact(
            automation_run_id=run_id,
            project_id="project-1",
            artifact_type="requirement_document",
            artifact_id="document-1",
            artifact_version_id=version_id,
            source="document",
            authority="project",
            quote=quote,
            quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            source_start=0,
            source_end=len(quote),
        )

    @staticmethod
    def make_compilation(version_id="document-v1", quote="Người dùng đăng nhập hợp lệ"):
        return {
            "capability": "testability_blueprint_compilation",
            "obligations": [
                {
                    "key": "login-valid",
                    "obligation": "Xác minh đăng nhập với thông tin hợp lệ",
                    "source_ref": version_id,
                    "source_quote": quote,
                }
            ],
            "clarifications": [],
            "evidence_refs": [version_id],
            "confidence": 0.9,
            "warnings": [],
        }

    async def test_saves_first_blueprint_version_and_deduplicates_identical_compilation(self):
        first = await self.repository.save_project_blueprint(
            "run-1", "project-1", [self.make_fact()], self.make_compilation()
        )
        repeated = await self.repository.save_project_blueprint(
            "run-2",
            "project-1",
            [self.make_fact("run-2")],
            self.make_compilation(),
        )

        self.assertEqual(first.version, 1)
        self.assertEqual(repeated.blueprint_id, first.blueprint_id)
        self.assertEqual(repeated.automation_run_ids, ["run-1", "run-2"])
        self.assertEqual(len(self.mongo.automation_project_blueprints.values), 1)

    async def test_source_revision_change_creates_next_immutable_version(self):
        first = await self.repository.save_project_blueprint(
            "run-1", "project-1", [self.make_fact()], self.make_compilation()
        )
        quote = "Người dùng đăng nhập với mã xác thực hợp lệ"
        second = await self.repository.save_project_blueprint(
            "run-2",
            "project-1",
            [self.make_fact("run-2", "document-v2", quote)],
            self.make_compilation("document-v2", quote),
        )
        history = await self.repository.list_project_blueprints("project-1")

        self.assertEqual(second.version, 2)
        self.assertEqual([item.version for item in history], [2, 1])
        self.assertEqual(history[1].blueprint_id, first.blueprint_id)
        self.assertEqual(second.source_revisions[0].artifact_version_id, "document-v2")

    async def test_rejects_compilation_without_source_fact_for_each_cited_revision(self):
        with self.assertRaisesRegex(ValueError, "BLUEPRINT_SOURCE_FACTS_MISSING"):
            await self.repository.save_project_blueprint(
                "run-1", "project-1", [self.make_fact()], self.make_compilation("document-v2")
            )
        self.assertEqual(self.mongo.automation_project_blueprints.values, [])

    async def test_same_run_cannot_silently_replace_its_blueprint(self):
        await self.repository.save_project_blueprint(
            "run-1", "project-1", [self.make_fact()], self.make_compilation()
        )
        quote = "Người dùng đăng nhập với mã xác thực hợp lệ"
        with self.assertRaisesRegex(ValueError, "AUTOMATION_RUN_BLUEPRINT_CONFLICT"):
            await self.repository.save_project_blueprint(
                "run-1",
                "project-1",
                [self.make_fact("run-1", "document-v2", quote)],
                self.make_compilation("document-v2", quote),
            )

    async def test_rejects_source_facts_without_verifiable_positions_or_with_a_false_digest(self):
        missing_position = self.make_fact()
        missing_position.source_start = None
        missing_position.source_end = None
        with self.assertRaisesRegex(ValueError, "BLUEPRINT_SOURCE_POSITION_MISSING"):
            await self.repository.save_project_blueprint(
                "run-1", "project-1", [missing_position], self.make_compilation()
            )

        false_digest = self.make_fact()
        false_digest.quote_sha256 = "0" * 64
        with self.assertRaisesRegex(ValueError, "BLUEPRINT_SOURCE_QUOTE_DIGEST_INVALID"):
            await self.repository.save_project_blueprint(
                "run-1", "project-1", [false_digest], self.make_compilation()
            )


class ProjectTestabilityBlueprintApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_endpoint_checks_project_membership_and_returns_latest_first(self):
        older = type("Blueprint", (), {"version": 1})()
        newer = type("Blueprint", (), {"version": 2})()
        with (
            patch("src.api.automation.project_access", new=AsyncMock(return_value=("QA", ["requirement.read"]))) as access,
            patch("src.api.automation.automation_repository.list_project_blueprints", new=AsyncMock(return_value=[newer, older])) as listing,
        ):
            result = await list_project_testability_blueprints(
                "project-1", 10, "Bearer token", type("User", (), {"system_role": SystemRole.USER})()
            )

        self.assertEqual(result, {"project_id": "project-1", "current_version": 2, "versions": [newer, older]})
        access.assert_awaited_once_with("project-1", "Bearer token")
        listing.assert_awaited_once_with("project-1", 10)

    async def test_history_endpoint_does_not_read_blueprints_without_project_access(self):
        denied = HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
        with (
            patch("src.api.automation.project_access", new=AsyncMock(side_effect=denied)),
            patch("src.api.automation.automation_repository.list_project_blueprints", new=AsyncMock()) as listing,
        ):
            with self.assertRaises(HTTPException) as caught:
                await list_project_testability_blueprints(
                    "project-1", 10, "Bearer token", type("User", (), {"system_role": SystemRole.USER})()
                )

        self.assertIs(caught.exception, denied)
        listing.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
