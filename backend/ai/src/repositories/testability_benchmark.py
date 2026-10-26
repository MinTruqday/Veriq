from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.schemas.evaluation import (
    TestabilityBenchmarkDataset,
    TestabilityBenchmarkDatasetCreate,
    TestabilityBenchmarkDatasetReview,
    TestabilityBenchmarkDatasetUpdate,
    benchmark_answer_key_review_covers_cases,
    benchmark_answer_key_review_has_case_coverage,
)


class TestabilityBenchmarkRepository:
    @property
    def _collection(self):
        return database.mongodb[settings.AI_DB_NAME].testability_benchmark_datasets

    @property
    def _runs(self):
        return database.mongodb[settings.AI_DB_NAME].testability_benchmark_runs

    async def create(
        self, payload: TestabilityBenchmarkDatasetCreate, created_by: str
    ) -> TestabilityBenchmarkDataset:
        dataset = TestabilityBenchmarkDataset(
            **payload.model_dump(),
            created_by=created_by,
            creator_identity_verified=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        document = dataset.model_dump(mode="python")
        document["_id"] = document.pop("dataset_id")
        try:
            await self._collection.insert_one(document)
        except DuplicateKeyError:
            raise
        return dataset

    async def get(self, dataset_id: str) -> TestabilityBenchmarkDataset | None:
        document = await self._collection.find_one({"_id": dataset_id})
        if not document:
            return None
        document["dataset_id"] = str(document.pop("_id"))
        return TestabilityBenchmarkDataset.model_validate(document)

    async def update(
        self,
        dataset_id: str,
        payload: TestabilityBenchmarkDatasetUpdate,
        updated_by: str,
    ) -> TestabilityBenchmarkDataset:
        current = await self._collection.find_one({"_id": dataset_id})
        if not current:
            raise ValueError("benchmark_dataset_not_found")
        if current.get("revision", 1) != payload.expected_revision:
            raise ValueError("benchmark_dataset_revision_conflict")

        values = payload.model_dump(exclude={"expected_revision"}, exclude_none=True)
        values.update(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": updated_by,
                "answer_key_review": None,
            }
        )
        result = await self._collection.update_one(
            {"_id": dataset_id, "revision": payload.expected_revision},
            {"$set": values, "$inc": {"revision": 1}},
        )
        if result.modified_count != 1:
            raise ValueError("benchmark_dataset_revision_conflict")
        dataset = await self.get(dataset_id)
        if not dataset:
            raise ValueError("benchmark_dataset_not_found")
        return dataset

    async def review_answer_key(
        self, dataset_id: str, review: TestabilityBenchmarkDatasetReview, reviewer_id: str
    ) -> TestabilityBenchmarkDataset:
        current = await self._collection.find_one({"_id": dataset_id})
        if not current:
            raise ValueError("benchmark_dataset_not_found")
        if not current.get("creator_identity_verified"):
            raise ValueError("benchmark_dataset_creator_identity_unverified")
        if current.get("created_by") == reviewer_id:
            raise ValueError("benchmark_answer_key_reviewer_must_be_independent")
        if current.get("answer_key_review"):
            raise ValueError("benchmark_answer_key_already_reviewed")
        if current.get("revision", 1) != review.expected_revision:
            raise ValueError("benchmark_dataset_revision_conflict")
        if not benchmark_answer_key_review_has_case_coverage(
            current.get("cases") or [], review.case_reviews
        ):
            raise ValueError("benchmark_answer_key_review_incomplete")
        fully_verified = benchmark_answer_key_review_covers_cases(
            current.get("cases") or [], review.case_reviews
        )
        if review.decision == "APPROVE" and not fully_verified:
            raise ValueError("benchmark_answer_key_review_incomplete")
        if review.decision == "RETURN_FOR_CORRECTION" and fully_verified:
            raise ValueError("benchmark_answer_key_return_requires_findings")

        reviewed_at = datetime.now(timezone.utc).isoformat()
        result = await self._collection.update_one(
            {
                "_id": dataset_id,
                "revision": review.expected_revision,
                "created_by": {"$ne": reviewer_id},
                "answer_key_review": None,
            },
            {
                "$set": {
                    "answer_key_review": {
                        "reviewer_id": reviewer_id,
                        "reviewer_identity_verified": True,
                        "reviewed_revision": review.expected_revision,
                        "decision": review.decision,
                        "rationale": review.rationale.strip(),
                        "reviewed_at": reviewed_at,
                        "case_reviews": [
                            item.model_dump(mode="json") for item in review.case_reviews
                        ],
                    }
                },
                "$inc": {"revision": 1},
            },
        )
        if result.modified_count != 1:
            raise ValueError("benchmark_dataset_revision_conflict")
        dataset = await self.get(dataset_id)
        if not dataset:
            raise ValueError("benchmark_dataset_not_found")
        return dataset

    async def list(self, limit: int = 100) -> list[dict]:
        documents = await self._collection.find(
            {},
            {
                "title": 1,
                "revision": 1,
                "created_at": 1,
                "created_by": 1,
                "creator_identity_verified": 1,
                "cases": 1,
                "answer_key_review": 1,
            },
        ).sort([("created_at", -1), ("_id", 1)]).to_list(length=limit)
        return [
            {
                "dataset_id": str(value["_id"]),
                "title": value.get("title"),
                "revision": value.get("revision"),
                "case_count": len(value.get("cases") or []),
                "created_at": value.get("created_at"),
                "created_by": value.get("created_by"),
                "answer_key_review": value.get("answer_key_review"),
                "ready_for_run": bool(
                    value.get("creator_identity_verified")
                    and (value.get("answer_key_review") or {}).get(
                        "reviewer_identity_verified"
                    )
                    and (value.get("answer_key_review") or {}).get("reviewer_id")
                    != value.get("created_by")
                    and (value.get("answer_key_review") or {}).get("decision", "APPROVE")
                    == "APPROVE"
                    and benchmark_answer_key_review_covers_cases(
                        value.get("cases") or [], value.get("answer_key_review")
                    )
                ),
            }
            for value in documents
        ]

    async def save_run(self, report: dict) -> None:
        await self._runs.insert_one({"_id": report["run_id"], **report})

    async def get_run(self, dataset_id: str, run_id: str) -> dict | None:
        document = await self._runs.find_one({"_id": run_id, "dataset_id": dataset_id})
        if not document:
            return None
        document["run_id"] = str(document.pop("_id"))
        return document

    async def list_runs(self, dataset_id: str | list[str], limit: int = 20) -> List[dict]:
        dataset_filter = (
            {"dataset_id": {"$in": dataset_id}}
            if isinstance(dataset_id, list)
            else {"dataset_id": dataset_id}
        )
        documents = await self._runs.find(
            dataset_filter,
            {"_id": 1, "dataset_id": 1, "dataset_revision": 1,
             "answer_key_review": 1, "total_cases": 1, "duration_ms": 1,
             "pipeline_failures": 1, "pipeline_rejections": 1, "created_at": 1,
             "execution_status": 1, "pipeline_case_counts": 1,
             "paired_pipeline_comparisons": 1,
             "clarification_savings_vs_baseline": 1,
             "clarification_savings_paired_cases": 1,
             "pipeline_metadata": 1,
             "compiler": 1, "direct_generation": 1,
             "clarification_without_obligation_planning": 1},
        ).sort("created_at", -1).to_list(length=limit)
        for document in documents:
            document["run_id"] = str(document.pop("_id"))
        return documents


testability_benchmark_repository = TestabilityBenchmarkRepository()
