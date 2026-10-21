from datetime import datetime, timezone
from typing import List

from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.schemas.evaluation import (
    TestabilityBenchmarkDataset,
    TestabilityBenchmarkDatasetCreate,
)


class TestabilityBenchmarkRepository:
    @property
    def _collection(self):
        return database.mongodb[settings.AI_DB_NAME].testability_benchmark_datasets

    @property
    def _runs(self):
        return database.mongodb[settings.AI_DB_NAME].testability_benchmark_runs

    async def create(
        self, payload: TestabilityBenchmarkDatasetCreate
    ) -> TestabilityBenchmarkDataset:
        dataset = TestabilityBenchmarkDataset(
            **payload.model_dump(),
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

    async def list(self, limit: int = 100) -> list[dict]:
        documents = await self._collection.find(
            {}, {"title": 1, "revision": 1, "created_at": 1, "created_by": 1, "cases": 1}
        ).sort([("created_at", -1), ("_id", 1)]).to_list(length=limit)
        return [
            {
                "dataset_id": str(value["_id"]),
                "title": value.get("title"),
                "revision": value.get("revision"),
                "case_count": len(value.get("cases") or []),
                "created_at": value.get("created_at"),
                "created_by": value.get("created_by"),
            }
            for value in documents
        ]

    async def save_run(self, report: dict) -> None:
        await self._runs.insert_one({"_id": report["run_id"], **report})

    async def list_runs(self, dataset_id: str, limit: int = 20) -> List[dict]:
        documents = await self._runs.find(
            {"dataset_id": dataset_id},
            {"_id": 1, "total_cases": 1, "duration_ms": 1,
             "pipeline_failures": 1, "created_at": 1,
             "compiler": 1, "direct_generation": 1,
             "clarification_without_obligation_planning": 1},
        ).sort("created_at", -1).to_list(length=limit)
        for document in documents:
            document["run_id"] = str(document.pop("_id"))
        return documents


testability_benchmark_repository = TestabilityBenchmarkRepository()
