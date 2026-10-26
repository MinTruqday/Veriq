from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.schemas.document_ingestion_checkpoint import DocumentIngestionPageCheckpoint


class DocumentIngestionCheckpointRepository:
    @property
    def collection(self):
        return database.mongodb[settings.AI_DB_NAME].document_ingestion_page_checkpoints

    @staticmethod
    def _key(
        document_id: str,
        project_id: str,
        owner_id: str,
        source_hash: str,
        parser_name: str,
        parser_version: str,
        parser_contract_version: int,
        ocr_language: str,
        page_no: int,
    ) -> str:
        identity = "\0".join(
            (
                document_id,
                project_id,
                owner_id,
                source_hash,
                parser_name,
                parser_version,
                str(parser_contract_version),
                ocr_language,
                str(page_no),
            )
        )
        return sha256(identity.encode("utf-8")).hexdigest()

    async def iter_pages(
        self,
        document_id: str,
        project_id: str,
        owner_id: str,
        source_hash: str,
        parser_name: str,
        parser_version: str,
        parser_contract_version: int,
        ocr_language: str,
    ) -> AsyncIterator[DocumentIngestionPageCheckpoint]:
        query = {
            "document_id": document_id,
            "project_id": project_id,
            "owner_id": owner_id,
            "source_hash": source_hash,
            "parser_name": parser_name,
            "parser_version": parser_version,
            "parser_contract_version": parser_contract_version,
            "ocr_language": ocr_language,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        }
        cursor = self.collection.find(query).sort("page_no", 1)
        async for row in cursor:
            yield DocumentIngestionPageCheckpoint.model_validate(row)

    async def save_page(
        self, checkpoint: DocumentIngestionPageCheckpoint
    ) -> None:
        now = datetime.now(timezone.utc)
        payload = checkpoint.model_dump()
        payload["_id"] = self._key(
            checkpoint.document_id,
            checkpoint.project_id,
            checkpoint.owner_id,
            checkpoint.source_hash,
            checkpoint.parser_name,
            checkpoint.parser_version,
            checkpoint.parser_contract_version,
            checkpoint.ocr_language,
            checkpoint.page_no,
        )
        payload["created_at"] = now
        payload["expires_at"] = now + timedelta(
            days=settings.DOCUMENT_INGESTION_CHECKPOINT_TTL_DAYS
        )
        await self.collection.replace_one(
            {"_id": payload["_id"]}, payload, upsert=True
        )

    async def delete_source_version(
        self,
        document_id: str,
        project_id: str,
        owner_id: str,
        source_hash: str,
    ) -> None:
        await self.collection.delete_many(
            {
                "document_id": document_id,
                "project_id": project_id,
                "owner_id": owner_id,
                "source_hash": source_hash,
            }
        )

    async def delete_document_versions(
        self,
        document_id: str,
        project_id: str,
    ) -> int:
        result = await self.collection.delete_many(
            {
                "document_id": document_id,
                "project_id": project_id,
            }
        )
        return int(result.deleted_count or 0)


document_ingestion_checkpoint_repository = DocumentIngestionCheckpointRepository()
