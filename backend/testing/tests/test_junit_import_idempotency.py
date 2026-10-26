from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from src.modules.integrations.services.junit_import import import_junit_result
from src.modules.integrations.services.junit_import_identity import junit_import_source_hash


class JUnitImportIdempotencyTests(unittest.IsolatedAsyncioTestCase):
    def test_source_hash_is_stable_and_scoped_to_run_and_content(self):
        content = "<testsuite><testcase name='login'/></testsuite>"

        self.assertEqual(
            junit_import_source_hash("run-1", content),
            junit_import_source_hash("run-1", content),
        )
        self.assertNotEqual(
            junit_import_source_hash("run-1", content),
            junit_import_source_hash("run-2", content),
        )
        self.assertNotEqual(
            junit_import_source_hash("run-1", content),
            junit_import_source_hash("run-1", content.replace("login", "logout")),
        )

    async def test_same_payload_returns_existing_receipt_without_reapplying_results(self):
        content = "<testsuite><testcase name='login'/></testsuite>"
        source_hash = junit_import_source_hash("run-1", content)
        receipt = {
            "_id": "JUNIT-1",
            "project_id": "project-1",
            "test_run_id": "run-1",
            "source_hash": source_hash,
            "status": "IMPORTED",
            "revision": 1,
        }
        test_runs = SimpleNamespace(
            find_one=AsyncMock(return_value={"_id": "run-1", "test_case_version_ids": []})
        )
        imports = SimpleNamespace(find_one=AsyncMock(return_value=receipt))
        database_value = SimpleNamespace(test_runs=test_runs, junit_result_imports=imports)
        user = SimpleNamespace(id="user-1")

        with (
            patch(
                "src.modules.integrations.services.junit_import.get_project",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.integrations.services.junit_import.database",
                SimpleNamespace(value=database_value),
            ),
        ):
            result = await import_junit_result("project-1", "run-1", content, user)

        self.assertEqual(result, receipt)
        self.assertEqual(imports.find_one.await_args.args[0]["source_hash"], source_hash)
