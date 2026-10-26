import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.repositories import analysis as analysis_module
from src.repositories import test_design as test_design_module


class Cursor:
    def __init__(self, items):
        self.items = items

    def sort(self, *_args):
        return self

    async def to_list(self, limit):
        return self.items[:limit]


class TestActiveTestCaseVersionPagination(unittest.IsolatedAsyncioTestCase):
    async def test_draft_iterator_reads_all_matching_drafts_in_stable_pages(self):
        drafts = [
            {"_id": f"draft-{index:03d}", "status": "DRAFT"}
            for index in range(5)
        ]
        queries = []

        class DraftCollection:
            def find(self, query):
                queries.append(query)
                remaining = [
                    draft for draft in drafts
                    if draft["status"] in query["status"]["$in"]
                    and ("_id" not in query or draft["_id"] > query["_id"]["$gt"])
                ]
                return Cursor(remaining)

        with patch.object(
            test_design_module,
            "database",
            SimpleNamespace(value=SimpleNamespace(test_case_drafts=DraftCollection())),
        ):
            pages = [
                page
                async for page in test_design_module.test_design_repository.iter_case_draft_pages(
                    "project", ["DRAFT"], page_size=2
                )
            ]

        self.assertEqual([len(page) for page in pages], [2, 2, 1])
        self.assertEqual(
            [draft["_id"] for page in pages for draft in page],
            [f"draft-{index:03d}" for index in range(5)],
        )
        self.assertEqual(queries[1]["_id"], {"$gt": "draft-001"})

    async def test_iterator_reads_all_current_versions_in_stable_pages(self):
        cases = [
            {"_id": f"case-{index:03d}", "current_version_id": f"version-{index:03d}"}
            for index in range(5)
        ]
        versions = [
            {"_id": f"version-{index:03d}", "test_case_id": f"case-{index:03d}"}
            for index in range(5)
        ]
        case_queries = []

        class CaseCollection:
            def find(self, query, _projection):
                case_queries.append(query)
                remaining = [
                    case
                    for case in cases
                    if "_id" not in query or case["_id"] > query["_id"]["$gt"]
                ]
                return Cursor(remaining)

        class VersionCollection:
            def find(self, query):
                wanted = set(query["_id"]["$in"])
                return Cursor([version for version in versions if version["_id"] in wanted])

        db = SimpleNamespace(
            test_cases=CaseCollection(),
            test_case_versions=VersionCollection(),
        )

        async def collect_pages():
            return [
                page
                async for page in analysis_module.analysis_repository.iter_active_test_case_version_pages(
                    "project", "ACTIVE", page_size=2
                )
            ]

        with patch.object(analysis_module, "database", SimpleNamespace(value=db)):
            pages = await collect_pages()

        self.assertEqual([len(page) for page in pages], [2, 2, 1])
        self.assertEqual(
            [version["_id"] for page in pages for version in page],
            [f"version-{index:03d}" for index in range(5)],
        )
        self.assertEqual(len(case_queries), 3)
        self.assertEqual(case_queries[1]["_id"], {"$gt": "case-001"})
        self.assertEqual(case_queries[2]["_id"], {"$gt": "case-003"})

    async def test_iterator_fails_closed_for_a_missing_current_version(self):
        class CaseCollection:
            def find(self, *_args):
                return Cursor([{"_id": "case-a", "current_version_id": "missing"}])

        class VersionCollection:
            def find(self, *_args):
                return Cursor([])

        db = SimpleNamespace(
            test_cases=CaseCollection(),
            test_case_versions=VersionCollection(),
        )
        with patch.object(analysis_module, "database", SimpleNamespace(value=db)):
            with self.assertRaises(analysis_module.ActiveTestCaseVersionIntegrityError):
                async for _page in analysis_module.analysis_repository.iter_active_test_case_version_pages(
                    "project", "ACTIVE", page_size=1
                ):
                    self.fail("The iterator must reject a dangling current-version pointer")

if __name__ == "__main__":
    unittest.main()
