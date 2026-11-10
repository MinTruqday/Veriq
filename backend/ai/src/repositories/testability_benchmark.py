from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata
from typing import List
from uuid import uuid4

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


def calculate_pipeline_stage_scores(gold_items: list[dict], candidate_items: list[str]) -> dict:
    def normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.casefold())
        return " ".join(re.sub(r"[^\w\s]", " ", normalized).split())

    normalized_candidates = [normalize(item) for item in candidate_items]
    matched_gold = []
    for item in gold_items:
        keywords = [normalize(value) for value in item["keywords"]]
        if any(
            keyword and any(keyword in candidate for candidate in normalized_candidates)
            for keyword in keywords
        ):
            matched_gold.append(item["label"])
    matched_candidate_count = sum(
        any(
            normalize(keyword) in candidate
            for item in gold_items
            for keyword in item["keywords"]
            if normalize(keyword)
        )
        for candidate in normalized_candidates
    )
    precision = matched_candidate_count / len(candidate_items) if candidate_items else 0.0
    recall = len(matched_gold) / len(gold_items) if gold_items else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "matched_gold_items": matched_gold,
        "missed_gold_items": [item["label"] for item in gold_items if item["label"] not in matched_gold],
        "candidate_count": len(candidate_items),
        "gold_count": len(gold_items),
        "matched_candidate_count": matched_candidate_count,
        "duplicate_rate": round(
            (len(candidate_items) - len(set(normalized_candidates))) / len(candidate_items), 4
        ) if candidate_items else 0.0,
    }


class TestabilityBenchmarkRepository:
    @property
    def _collection(self):
        return database.mongodb[settings.AI_DB_NAME].testability_benchmark_datasets

    @property
    def _runs(self):
        return database.mongodb[settings.AI_DB_NAME].testability_benchmark_runs

    @property
    def _pipeline_runs(self):
        return database.mongodb[settings.AI_DB_NAME].testability_pipeline_benchmark_runs

    async def save_pipeline_stage_run(self, payload, created_by: str) -> dict:
        gold_items = payload.gold_items
        candidate_items = payload.candidate_items
        scores = calculate_pipeline_stage_scores(gold_items, candidate_items)
        report = {
            "run_id": str(uuid4()),
            "project_id": payload.project_id,
            "requirement_version_id": payload.requirement_version_id,
            "stage": payload.stage,
            "mode": payload.mode,
            "upstream_context": payload.upstream_context,
            "gold_items": gold_items,
            "candidate_items": candidate_items,
            "generation_metadata": payload.generation_metadata,
            "scores": scores,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scoring_method": "Human-authored keyword coverage; a keyword match is a lexical baseline, not semantic QA judgment.",
        }
        await self._pipeline_runs.insert_one({"_id": report["run_id"], **report})
        return report

    async def list_pipeline_stage_runs(self, project_id: str, limit: int = 50) -> list[dict]:
        documents = await self._pipeline_runs.find(
            {"project_id": project_id},
            {"_id": 1, "requirement_version_id": 1, "stage": 1, "mode": 1,
             "scores": 1, "generation_metadata": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(length=limit)
        results = []
        for item in documents:
            run_id = str(item.pop("_id"))
            results.append({"run_id": run_id, **item})
        return results

    async def get_pipeline_stage_run(self, project_id: str, run_id: str) -> dict | None:
        document = await self._pipeline_runs.find_one(
            {"_id": run_id, "project_id": project_id}, {"_id": 0}
        )
        return document

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
