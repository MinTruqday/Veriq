import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.api import inference
from src.schemas.auth import CurrentUser, SystemRole
from src.schemas.evaluation import (
    TestabilityBenchmarkAnswerKeyReview as BenchmarkAnswerKeyReviewSchema,
)
from src.schemas.evaluation import (
    TestabilityBenchmarkCaseAnswerKeyReview as BenchmarkCaseReviewSchema,
)
from src.schemas.evaluation import TestabilityBenchmarkDataset as BenchmarkDatasetSchema
from src.schemas.evaluation import TestabilityBenchmarkGoldCase as BenchmarkGoldCaseSchema
from src.schemas.evaluation import (
    TestabilityBenchmarkRepeatedReport as BenchmarkRepeatedReportSchema,
)


def _case_review(case_id):
    return BenchmarkCaseReviewSchema(
        case_id=case_id,
        source_quotes_verified=True,
        obligations_verified=True,
        clarifications_verified=True,
        rationale="Đã kiểm từng trích dẫn, nghĩa vụ và nhãn làm rõ của ca này.",
    )


class TestabilityBenchmarkRepeatedApiTests(unittest.IsolatedAsyncioTestCase):
    def test_returned_answer_key_cannot_start_a_benchmark(self):
        dataset = BenchmarkDatasetSchema(
            dataset_id="dataset-returned",
            title="Returned dataset",
            created_at="2026-10-24T00:00:00Z",
            created_by="admin-author",
            creator_identity_verified=True,
            answer_key_review=BenchmarkAnswerKeyReviewSchema(
                reviewer_id="admin-reviewer",
                reviewer_identity_verified=True,
                decision="RETURN_FOR_CORRECTION",
                reviewed_revision=1,
                rationale="Đáp án chuẩn cần sửa trước khi chạy đối chiếu.",
                reviewed_at="2026-10-24T00:00:00Z",
                case_reviews=[{
                    "case_id": "case-1",
                    "source_quotes_verified": True,
                    "obligations_verified": False,
                    "clarifications_verified": True,
                    "rationale": "Thiếu nghĩa vụ kiểm thử được nêu trong nguồn.",
                }],
            ),
            cases=[BenchmarkGoldCaseSchema(
                case_id="case-1",
                source_text="Mật khẩu tối thiểu 12 ký tự.",
                expected_source_quotes=["Mật khẩu tối thiểu 12 ký tự."],
                expected_obligation_keys=["password-minimum"],
            )],
        )

        with self.assertRaises(HTTPException) as raised:
            inference._require_independently_reviewed_benchmark_dataset(dataset)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"],
            "BENCHMARK_COMPLETE_INDEPENDENT_CASE_REVIEW_REQUIRED",
        )

    async def test_dataset_correction_uses_authenticated_admin_and_returns_revision_conflict(self):
        from src.schemas.evaluation import TestabilityBenchmarkDatasetUpdate

        admin = CurrentUser(
            _id="admin-2",
            email="admin2@example.test",
            system_role=SystemRole.ADMIN,
            session_id="session-2",
        )
        payload = TestabilityBenchmarkDatasetUpdate(
            expected_revision=4,
            title="Bộ tình huống đã chỉnh",
        )
        expected = object()
        with patch.object(
            inference.testability_benchmark_repository,
            "update",
            new=AsyncMock(return_value=expected),
        ) as update:
            result = await inference.update_testability_benchmark_dataset(
                "dataset-1", payload, admin
            )

        self.assertIs(result, expected)
        update.assert_awaited_once_with("dataset-1", payload, "admin-2")

        with patch.object(
            inference.testability_benchmark_repository,
            "update",
            new=AsyncMock(side_effect=ValueError("benchmark_dataset_revision_conflict")),
        ):
            with self.assertRaises(HTTPException) as raised:
                await inference.update_testability_benchmark_dataset(
                    "dataset-1", payload, admin
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "benchmark_dataset_revision_conflict"
        )

    async def test_dataset_creation_binds_creator_to_authenticated_admin(self):
        from src.schemas.evaluation import (
            TestabilityBenchmarkDatasetCreate,
            TestabilityBenchmarkGoldCase,
        )

        admin = CurrentUser(
            _id="admin-1",
            email="admin@example.test",
            system_role=SystemRole.ADMIN,
            session_id="session-1",
        )
        payload = TestabilityBenchmarkDatasetCreate(
            dataset_id="dataset-1",
            title="Benchmark",
            cases=[
                TestabilityBenchmarkGoldCase(
                    case_id="case-1",
                    source_text="Mật khẩu phải đổi sau 90 ngày.",
                    expected_source_quotes=["Mật khẩu phải đổi sau 90 ngày."],
                    expected_obligation_keys=["password-rotation"],
                )
            ],
        )
        expected = object()
        with patch.object(
            inference.testability_benchmark_repository,
            "create",
            new=AsyncMock(return_value=expected),
        ) as create:
            result = await inference.create_testability_benchmark_dataset(payload, admin)

        self.assertIs(result, expected)
        create.assert_awaited_once_with(payload, "admin-1")

    def test_legacy_quote_only_dataset_remains_readable(self):
        dataset = BenchmarkDatasetSchema(
            dataset_id="legacy-dataset",
            title="Legacy pilot",
            created_at="2026-10-24T00:00:00Z",
            created_by="qa-1",
            cases=[
                BenchmarkGoldCaseSchema(
                    case_id="legacy-case",
                    source_text="Mật khẩu tối thiểu 12 ký tự.",
                    expected_source_quotes=["Mật khẩu tối thiểu 12 ký tự."],
                )
            ],
        )

        self.assertEqual(dataset.cases[0].case_id, "legacy-case")
        with self.assertRaisesRegex(ValueError, "benchmark_case_requires_answer_key"):
            dataset.cases[0].validate_for_scoring()

    async def test_legacy_quote_only_dataset_is_blocked_before_running_pipelines(self):
        dataset = BenchmarkDatasetSchema(
            dataset_id="legacy-dataset",
            title="Legacy pilot",
            created_at="2026-10-24T00:00:00Z",
            created_by="qa-1",
            cases=[
                BenchmarkGoldCaseSchema(
                    case_id="legacy-case",
                    source_text="Mật khẩu tối thiểu 12 ký tự.",
                    expected_source_quotes=["Mật khẩu tối thiểu 12 ký tự."],
                )
            ],
        )
        with (
            patch.object(
                inference.testability_benchmark_repository,
                "get",
                new=AsyncMock(return_value=dataset),
            ),
            patch.object(
                inference.testability_benchmark, "run_dataset", new=AsyncMock()
            ) as run_once,
            patch.object(
                inference.testability_benchmark,
                "run_repeated_dataset",
                new=AsyncMock(),
            ) as run_repeated,
        ):
            with self.assertRaises(HTTPException) as once_error:
                await inference.evaluate_testability_benchmark_dataset("legacy-dataset")
            with self.assertRaises(HTTPException) as repeated_error:
                await inference.repeat_testability_benchmark_dataset("legacy-dataset", 2)

        self.assertEqual(once_error.exception.status_code, 409)
        self.assertEqual(
            once_error.exception.detail["code"],
            "BENCHMARK_DATASET_ANSWER_KEY_INCOMPLETE",
        )
        self.assertEqual(repeated_error.exception.status_code, 409)
        run_once.assert_not_awaited()
        run_repeated.assert_not_awaited()

    async def test_repeated_run_returns_not_found_without_starting_pipelines(self):
        with (
            patch.object(inference.testability_benchmark_repository, "get", new=AsyncMock(return_value=None)),
            patch.object(inference.testability_benchmark, "run_repeated_dataset", new=AsyncMock()) as run,
        ):
            with self.assertRaises(HTTPException) as raised:
                await inference.repeat_testability_benchmark_dataset("missing", 2)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail["code"], "BENCHMARK_DATASET_NOT_FOUND")
        run.assert_not_awaited()

    async def test_repeated_run_persists_each_pipeline_run_and_returns_summary(self):
        dataset = BenchmarkDatasetSchema(
            dataset_id="dataset-1",
            title="Pilot",
            created_at="2026-10-24T00:00:00Z",
            created_by="qa-1",
            creator_identity_verified=True,
            answer_key_review=BenchmarkAnswerKeyReviewSchema(
                reviewer_id="reviewer-1",
                reviewer_identity_verified=True,
                reviewed_revision=1,
                rationale="Đã rà lại nguồn, trích dẫn và nghĩa vụ cần kiểm thử.",
                reviewed_at="2026-10-24T00:00:00Z",
                case_reviews=[_case_review("case-1")],
            ),
            cases=[BenchmarkGoldCaseSchema(
                case_id="case-1",
                source_text="Mật khẩu tối thiểu 12 ký tự.",
                expected_source_quotes=["Mật khẩu tối thiểu 12 ký tự."],
                expected_obligation_sources={
                    "password_minimum": "Mật khẩu tối thiểu 12 ký tự."
                },
            )],
        )
        summary = BenchmarkRepeatedReportSchema(
            dataset_id="dataset-1",
            requested_repetitions=2,
            completed_repetitions=2,
            partial_repetitions=0,
            failed_repetitions=0,
            run_ids=["run-1", "run-2"],
            execution_status="COMPLETE",
            pipeline_statistics={
                name: {
                    "runs_with_scores": 2,
                    "runs_with_failures": 0,
                    "rejected_cases": 0,
                    "failed_cases": 0,
                    "metrics": {},
                }
                for name in (
                    "compiler",
                    "clarification_without_obligation_planning",
                    "direct_generation",
                )
            },
            clarification_savings_vs_baseline={
                "observed_runs": 0,
                "mean": None,
                "population_stddev": None,
                "minimum": None,
                "maximum": None,
            },
        )

        async def run_and_persist(_dataset_id, _cases, repetitions, on_report):
            self.assertEqual(repetitions, 2)
            for index in range(1, repetitions + 1):
                await on_report(
                    type(
                        "Report",
                        (),
                        {
                            "model_dump": lambda _self, mode: {
                                "run_id": f"run-{index}",
                                "dataset_id": "dataset-1",
                                "pipeline_metadata": {"repetition_index": index},
                            }
                        },
                    )()
                )
            return summary

        with (
            patch.object(inference.testability_benchmark_repository, "get", new=AsyncMock(return_value=dataset)),
            patch.object(inference.testability_benchmark_repository, "save_run", new=AsyncMock()) as save_run,
            patch.object(inference.testability_benchmark, "run_repeated_dataset", new=AsyncMock(side_effect=run_and_persist)),
        ):
            result = await inference.repeat_testability_benchmark_dataset("dataset-1", 2)

        self.assertEqual(result.run_ids, ["run-1", "run-2"])
        self.assertEqual(result.execution_status, "COMPLETE")
        self.assertEqual(save_run.await_count, 2)
        saved_runs = [call.args[0] for call in save_run.await_args_list]
        self.assertEqual([row["pipeline_metadata"]["repetition_index"] for row in saved_runs], [1, 2])

    async def test_unreviewed_dataset_cannot_run_real_pipelines(self):
        dataset = BenchmarkDatasetSchema(
            dataset_id="dataset-unreviewed",
            title="Pilot",
            created_at="2026-10-24T00:00:00Z",
            created_by="author-1",
            cases=[BenchmarkGoldCaseSchema(
                case_id="case-1",
                source_text="Mật khẩu tối thiểu 12 ký tự.",
                expected_source_quotes=["Mật khẩu tối thiểu 12 ký tự."],
                expected_obligation_sources={
                    "password_minimum": "Mật khẩu tối thiểu 12 ký tự."
                },
            )],
        )
        with (
            patch.object(
                inference.testability_benchmark_repository,
                "get",
                new=AsyncMock(return_value=dataset),
            ),
            patch.object(
                inference.testability_benchmark, "run_dataset", new=AsyncMock()
            ) as run_once,
            patch.object(
                inference.testability_benchmark,
                "run_repeated_dataset",
                new=AsyncMock(),
            ) as run_repeated,
        ):
            with self.assertRaises(HTTPException) as once_error:
                await inference.evaluate_testability_benchmark_dataset("dataset-unreviewed")
            with self.assertRaises(HTTPException) as repeated_error:
                await inference.repeat_testability_benchmark_dataset("dataset-unreviewed", 2)

        self.assertEqual(once_error.exception.status_code, 409)
        self.assertEqual(
            once_error.exception.detail["code"], "BENCHMARK_COMPLETE_INDEPENDENT_CASE_REVIEW_REQUIRED"
        )
        self.assertEqual(repeated_error.exception.status_code, 409)
        run_once.assert_not_awaited()
        run_repeated.assert_not_awaited()

    async def test_answer_key_review_endpoint_requires_an_independent_review(self):
        from src.schemas.evaluation import TestabilityBenchmarkDatasetReview

        review = TestabilityBenchmarkDatasetReview(
            expected_revision=1,
            case_reviews=[_case_review("case-1")],
            rationale="Đã rà lại nguồn, trích dẫn và nghĩa vụ cần kiểm thử.",
        )
        reviewer = CurrentUser(
            _id="reviewer-1",
            email="reviewer@example.test",
            system_role=SystemRole.ADMIN,
            session_id="session-1",
        )
        expected = object()
        with patch.object(
            inference.testability_benchmark_repository,
            "review_answer_key",
            new=AsyncMock(return_value=expected),
        ) as review_answer_key:
            result = await inference.review_testability_benchmark_answer_key(
                "dataset-1", review, reviewer
            )

        self.assertIs(result, expected)
        review_answer_key.assert_awaited_once_with("dataset-1", review, "reviewer-1")

        with patch.object(
            inference.testability_benchmark_repository,
            "review_answer_key",
            new=AsyncMock(side_effect=ValueError("benchmark_answer_key_reviewer_must_be_independent")),
        ):
            with self.assertRaises(HTTPException) as raised:
                await inference.review_testability_benchmark_answer_key(
                    "dataset-1", review, reviewer
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"],
            "benchmark_answer_key_reviewer_must_be_independent",
        )


if __name__ == "__main__":
    unittest.main()
