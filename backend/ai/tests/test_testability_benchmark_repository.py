import unittest
from unittest.mock import patch

from src.repositories.testability_benchmark import TestabilityBenchmarkRepository
from src.schemas.evaluation import (
    TestabilityBenchmarkDatasetReview as BenchmarkDatasetReviewSchema,
)
from src.schemas.evaluation import TestabilityBenchmarkDatasetUpdate as BenchmarkDatasetUpdateSchema
from src.schemas.evaluation import benchmark_answer_key_review_covers_cases


def _case_review(case_id):
    return {
        "case_id": case_id,
        "source_quotes_verified": True,
        "obligations_verified": True,
        "clarifications_verified": True,
        "rationale": "Đã kiểm từng trích dẫn, nghĩa vụ và nhãn làm rõ của ca này.",
    }


class _Cursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, *_args):
        return self

    async def to_list(self, length):
        return self.documents[:length]


class TestabilityBenchmarkRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_answer_key_return_for_correction_is_recorded_but_not_ready(self):
        stored = {
            "_id": "dataset-return",
            "title": "Bộ đáp án thử nghiệm",
            "revision": 1,
            "created_at": "2026-10-24T00:00:00Z",
            "created_by": "author-1",
            "creator_identity_verified": True,
            "cases": [{
                "case_id": "case-1",
                "source_text": "Mật khẩu tối thiểu 12 ký tự.",
                "expected_source_quotes": ["Mật khẩu tối thiểu 12 ký tự."],
                "expected_obligation_keys": ["password-minimum"],
            }],
        }

        class _Collection:
            async def find_one(self, query):
                return stored.copy() if query.get("_id") == stored["_id"] else None

            async def update_one(self, query, update):
                if query.get("revision") != stored["revision"]:
                    return type("Result", (), {"modified_count": 0})()
                stored.update(update["$set"])
                stored["revision"] += update["$inc"]["revision"]
                return type("Result", (), {"modified_count": 1})()

        review = BenchmarkDatasetReviewSchema(
            expected_revision=1,
            decision="RETURN_FOR_CORRECTION",
            case_reviews=[{
                "case_id": "case-1",
                "source_quotes_verified": True,
                "obligations_verified": False,
                "clarifications_verified": True,
                "rationale": "Đáp án chuẩn bỏ sót nghĩa vụ về giới hạn tối thiểu.",
            }],
            rationale="Trả bộ dữ liệu để người tạo sửa nghĩa vụ kiểm thử bị thiếu.",
        )
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            result = await TestabilityBenchmarkRepository().review_answer_key(
                "dataset-return", review, "reviewer-1"
            )

        self.assertEqual(result.answer_key_review.decision, "RETURN_FOR_CORRECTION")
        self.assertFalse(result.answer_key_review.case_reviews[0].obligations_verified)
        self.assertFalse(
            benchmark_answer_key_review_covers_cases(result.cases, result.answer_key_review)
        )

    async def test_return_for_correction_requires_at_least_one_finding(self):
        stored = {
            "_id": "dataset-return",
            "revision": 1,
            "created_by": "author-1",
            "creator_identity_verified": True,
            "cases": [{
                "case_id": "case-1",
                "source_text": "Mật khẩu tối thiểu 12 ký tự.",
                "expected_source_quotes": ["Mật khẩu tối thiểu 12 ký tự."],
                "expected_obligation_keys": ["password-minimum"],
            }],
        }

        class _Collection:
            async def find_one(self, _query):
                return stored.copy()

        review = BenchmarkDatasetReviewSchema(
            expected_revision=1,
            decision="RETURN_FOR_CORRECTION",
            case_reviews=[_case_review("case-1")],
            rationale="Lý do trả sửa không thể ghi nếu không có phát hiện cụ thể.",
        )
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            with self.assertRaisesRegex(
                ValueError, "benchmark_answer_key_return_requires_findings"
            ):
                await TestabilityBenchmarkRepository().review_answer_key(
                    "dataset-return", review, "reviewer-1"
                )

    async def test_dataset_correction_increments_revision_and_invalidates_old_review(self):
        stored = {
            "_id": "dataset-correction",
            "title": "Pilot",
            "revision": 2,
            "created_at": "2026-10-24T00:00:00Z",
            "created_by": "author-1",
            "creator_identity_verified": True,
            "cases": [{
                "case_id": "case-1",
                "source_text": "Mật khẩu tối thiểu 12 ký tự.",
                "expected_source_quotes": ["Mật khẩu tối thiểu 12 ký tự."],
                "expected_obligation_keys": ["password-minimum"],
            }],
            "answer_key_review": {
                "reviewer_id": "reviewer-1",
                "reviewer_identity_verified": True,
                "reviewed_revision": 1,
                "rationale": "Đã rà bộ đáp án trước khi phát hiện cần sửa.",
                "reviewed_at": "2026-10-24T00:00:00Z",
                "case_reviews": [_case_review("case-1")],
            },
        }

        class _Collection:
            async def find_one(self, query):
                if query.get("_id") != stored["_id"]:
                    return None
                return stored.copy()

            async def update_one(self, query, update):
                if (
                    query.get("_id") != stored["_id"]
                    or query.get("revision") != stored["revision"]
                ):
                    return type("Result", (), {"modified_count": 0})()
                stored.update(update["$set"])
                stored["revision"] += update["$inc"]["revision"]
                return type("Result", (), {"modified_count": 1})()

        payload = BenchmarkDatasetUpdateSchema(
            expected_revision=2,
            cases=[{
                "case_id": "case-1",
                "source_text": "Mật khẩu có ít nhất 12 ký tự.",
                "expected_source_quotes": ["Mật khẩu có ít nhất 12 ký tự."],
                "expected_obligation_keys": ["password-minimum"],
            }],
        )
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            updated = await TestabilityBenchmarkRepository().update(
                "dataset-correction", payload, "admin-2"
            )

        self.assertEqual(updated.revision, 3)
        self.assertEqual(updated.updated_by, "admin-2")
        self.assertIsNone(updated.answer_key_review)
        self.assertEqual(updated.cases[0].source_text, "Mật khẩu có ít nhất 12 ký tự.")

    async def test_dataset_correction_rejects_stale_revision_without_mutating(self):
        stored = {
            "_id": "dataset-correction",
            "revision": 3,
            "title": "Pilot",
            "created_at": "2026-10-24T00:00:00Z",
            "created_by": "author-1",
            "cases": [{
                "case_id": "case-1",
                "source_text": "Giá trị gốc.",
                "expected_source_quotes": ["Giá trị gốc."],
                "expected_obligation_keys": ["source-obligation"],
            }],
        }

        class _Collection:
            async def find_one(self, _query):
                return stored.copy()

            async def update_one(self, _query, _update):
                return type("Result", (), {"modified_count": 0})()

        payload = BenchmarkDatasetUpdateSchema(
            expected_revision=2,
            title="Nội dung cũ",
        )
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            with self.assertRaisesRegex(ValueError, "benchmark_dataset_revision_conflict"):
                await TestabilityBenchmarkRepository().update(
                    "dataset-correction", payload, "admin-2"
                )

        self.assertEqual(stored["revision"], 3)
        self.assertEqual(stored["title"], "Pilot")

    async def test_dataset_creator_is_supplied_by_authenticated_api_identity(self):
        from src.schemas.evaluation import (
            TestabilityBenchmarkDatasetCreate,
            TestabilityBenchmarkGoldCase,
        )

        stored = {}

        class _Collection:
            async def insert_one(self, document):
                stored.update(document)

        payload = TestabilityBenchmarkDatasetCreate(
            dataset_id="dataset-verified",
            title="Verified dataset",
            cases=[
                TestabilityBenchmarkGoldCase(
                    case_id="case-1",
                    source_text="Mật khẩu phải đổi sau 90 ngày.",
                    expected_source_quotes=["Mật khẩu phải đổi sau 90 ngày."],
                    expected_obligation_keys=["password-rotation"],
                )
            ],
        )
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            dataset = await TestabilityBenchmarkRepository().create(payload, "admin-1")

        self.assertEqual(dataset.created_by, "admin-1")
        self.assertTrue(dataset.creator_identity_verified)
        self.assertEqual(stored["created_by"], "admin-1")
        self.assertTrue(stored["creator_identity_verified"])

    async def test_dataset_list_surfaces_answer_key_review_readiness(self):
        documents = [
            {
                "_id": "reviewed",
                "title": "Reviewed",
                "revision": 2,
                "created_at": "2026-10-24T00:00:00Z",
                "created_by": "author-1",
                "creator_identity_verified": True,
                "cases": [{
                    "case_id": "case-1",
                    "source_text": "Điều kiện đăng nhập hợp lệ.",
                    "expected_source_quotes": ["Điều kiện đăng nhập hợp lệ."],
                    "expected_obligation_keys": ["login-valid-credentials"],
                }],
                "answer_key_review": {
                    "reviewer_id": "reviewer-1",
                    "reviewer_identity_verified": True,
                    "case_reviews": [_case_review("case-1")],
                },
            },
            {
                "_id": "pending",
                "title": "Pending",
                "revision": 1,
                "created_at": "2026-10-23T00:00:00Z",
                "created_by": "author-2",
                "cases": [{
                    "case_id": "case-2",
                    "source_text": "Mật khẩu phải đổi định kỳ.",
                    "expected_source_quotes": ["Mật khẩu phải đổi định kỳ."],
                    "expected_obligation_keys": ["password-rotation"],
                }],
            },
            {
                "_id": "returned",
                "title": "Returned",
                "revision": 2,
                "created_at": "2026-10-22T00:00:00Z",
                "created_by": "author-3",
                "creator_identity_verified": True,
                "cases": [{
                    "case_id": "case-3",
                    "source_text": "Email phải được xác minh.",
                    "expected_source_quotes": ["Email phải được xác minh."],
                    "expected_obligation_keys": ["email-verification"],
                }],
                "answer_key_review": {
                    "reviewer_id": "reviewer-3",
                    "reviewer_identity_verified": True,
                    "decision": "RETURN_FOR_CORRECTION",
                    "case_reviews": [{
                        **_case_review("case-3"),
                        "obligations_verified": False,
                    }],
                },
            },
        ]

        class _Collection:
            projection = None

            def find(self, _query, projection):
                self.projection = projection
                return _Cursor(documents)

        collection = _Collection()
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = collection
            rows = await TestabilityBenchmarkRepository().list()

        self.assertEqual([row["ready_for_run"] for row in rows], [True, False, False])
        self.assertEqual(rows[0]["answer_key_review"]["reviewer_id"], "reviewer-1")
        self.assertEqual(collection.projection["answer_key_review"], 1)

    async def test_answer_key_review_requires_distinct_reviewer_and_expected_revision(self):
        stored = {
            "_id": "dataset-1",
            "dataset_id": "dataset-1",
            "title": "Pilot",
            "revision": 1,
            "created_at": "2026-10-24T00:00:00Z",
            "created_by": "author-1",
            "creator_identity_verified": True,
            "cases": [{
                "case_id": "case-1",
                "source_text": "Điều kiện đăng nhập hợp lệ.",
                "expected_source_quotes": ["Điều kiện đăng nhập hợp lệ."],
                "expected_obligation_keys": ["login-valid-credentials"],
            }],
        }

        class _Collection:
            async def find_one(self, query):
                return stored.copy() if query.get("_id") == stored["_id"] else None

            async def update_one(self, query, update):
                if (
                    query.get("_id") != stored["_id"]
                    or query.get("revision") != stored["revision"]
                    or query.get("created_by", {}).get("$ne") == stored["created_by"]
                    or query.get("answer_key_review") is not None
                    and stored.get("answer_key_review") is not None
                ):
                    return type("Result", (), {"modified_count": 0})()
                stored.update(update["$set"])
                stored["revision"] += update["$inc"]["revision"]
                return type("Result", (), {"modified_count": 1})()

        collection = _Collection()
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = collection
            repository = TestabilityBenchmarkRepository()
            review = BenchmarkDatasetReviewSchema(
                expected_revision=1,
                case_reviews=[_case_review("case-1")],
                rationale="Đã rà riêng nguồn trích dẫn và từng nghĩa vụ kiểm thử.",
            )

            with self.assertRaisesRegex(
                ValueError, "benchmark_answer_key_reviewer_must_be_independent"
            ):
                await repository.review_answer_key(
                    "dataset-1", review, "author-1"
                )
            with self.assertRaisesRegex(
                ValueError, "benchmark_dataset_revision_conflict"
            ):
                await repository.review_answer_key(
                    "dataset-1", review.model_copy(update={"expected_revision": 2}), "reviewer-1"
                )

            reviewed = await repository.review_answer_key("dataset-1", review, "reviewer-1")

        self.assertEqual(reviewed.revision, 2)
        self.assertEqual(reviewed.answer_key_review.reviewer_id, "reviewer-1")
        self.assertEqual(reviewed.answer_key_review.reviewed_revision, 1)
        self.assertEqual(
            reviewed.answer_key_review.rationale,
            "Đã rà riêng nguồn trích dẫn và từng nghĩa vụ kiểm thử.",
        )
        self.assertEqual(reviewed.answer_key_review.case_reviews[0].case_id, "case-1")

    async def test_answer_key_review_rejects_missing_or_unverified_case(self):
        stored = {
            "_id": "dataset-1",
            "revision": 1,
            "created_by": "author-1",
            "creator_identity_verified": True,
            "cases": [
                {
                    "case_id": "case-1",
                    "source_text": "Điều kiện đăng nhập hợp lệ.",
                    "expected_source_quotes": ["Điều kiện đăng nhập hợp lệ."],
                    "expected_obligation_keys": ["login-valid-credentials"],
                },
                {
                    "case_id": "case-2",
                    "source_text": "Mật khẩu phải đổi định kỳ.",
                    "expected_source_quotes": ["Mật khẩu phải đổi định kỳ."],
                    "expected_obligation_keys": ["password-rotation"],
                },
            ],
        }

        class _Collection:
            async def find_one(self, _query):
                return stored.copy()

        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            repository = TestabilityBenchmarkRepository()
            incomplete = BenchmarkDatasetReviewSchema(
                expected_revision=1,
                case_reviews=[_case_review("case-1")],
                rationale="Đã rà nhưng chưa bao phủ mọi ca trong bộ dữ liệu.",
            )
            unverified = BenchmarkDatasetReviewSchema(
                expected_revision=1,
                case_reviews=[
                    _case_review("case-1"),
                    {**_case_review("case-2"), "obligations_verified": False},
                ],
                rationale="Một ca chưa xác minh đủ nghĩa vụ nên chưa thể chấp nhận.",
            )

            for review in (incomplete, unverified):
                with self.assertRaisesRegex(
                    ValueError, "benchmark_answer_key_review_incomplete"
                ):
                    await repository.review_answer_key("dataset-1", review, "reviewer-1")

    async def test_answer_key_review_is_single_use(self):
        stored = {
            "_id": "dataset-1",
            "revision": 2,
            "created_by": "author-1",
            "creator_identity_verified": True,
            "answer_key_review": {
                "reviewer_id": "reviewer-1",
                "reviewer_identity_verified": True,
            },
        }

        class _Collection:
            async def find_one(self, _query):
                return stored.copy()

        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            with self.assertRaisesRegex(
                ValueError, "benchmark_answer_key_already_reviewed"
            ):
                await TestabilityBenchmarkRepository().review_answer_key(
                    "dataset-1",
                    BenchmarkDatasetReviewSchema(
                        expected_revision=2,
                        case_reviews=[_case_review("case-1")],
                        rationale="Đã rà lại toàn bộ đáp án chuẩn của bộ dữ liệu.",
                    ),
                    "reviewer-2",
                )

    async def test_legacy_dataset_with_asserted_author_cannot_be_independently_reviewed(self):
        stored = {
            "_id": "legacy-dataset",
            "revision": 1,
            "created_by": "author-claimed-in-request",
        }

        class _Collection:
            async def find_one(self, _query):
                return stored.copy()

        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_datasets = _Collection()
            with self.assertRaisesRegex(
                ValueError, "benchmark_dataset_creator_identity_unverified"
            ):
                await TestabilityBenchmarkRepository().review_answer_key(
                    "legacy-dataset",
                    BenchmarkDatasetReviewSchema(
                        expected_revision=1,
                        case_reviews=[_case_review("case-1")],
                        rationale="Không thể rà nếu danh tính người tạo cũ chưa xác thực.",
                    ),
                    "reviewer-authenticated",
                )

    async def test_run_list_preserves_execution_status_and_pipeline_counts(self):
        stored = {
            "_id": "TBR-1",
            "dataset_id": "dataset-1",
            "execution_status": "COMPLETE",
            "pipeline_case_counts": {"compiler": {"attempted": 3, "accepted": 3}},
            "total_cases": 3,
            "duration_ms": 1200,
            "created_at": "2026-10-23T00:00:00Z",
        }

        class _Collection:
            projection = None

            def find(self, _query, projection):
                self.projection = projection
                return _Cursor([stored])

        collection = _Collection()
        with patch("src.repositories.testability_benchmark.database") as database:
            database.mongodb.__getitem__.return_value.testability_benchmark_runs = collection
            rows = await TestabilityBenchmarkRepository().list_runs("dataset-1")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["run_id"], "TBR-1")
        self.assertEqual(rows[0]["execution_status"], "COMPLETE")
        self.assertEqual(
            rows[0]["pipeline_case_counts"],
            {"compiler": {"attempted": 3, "accepted": 3}},
        )
        self.assertEqual(collection.projection["execution_status"], 1)
        self.assertEqual(collection.projection["pipeline_case_counts"], 1)


if __name__ == "__main__":
    unittest.main()
