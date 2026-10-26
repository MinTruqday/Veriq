from hashlib import sha256

from src.core.database import database


class RequirementSourceBlockRepository:
    @property
    def blocks(self):
        return database.value.requirement_source_blocks

    @staticmethod
    def block_id(project_id: str, document_id: str, source_hash: str, index: int) -> str:
        identity = "\0".join((project_id, document_id, source_hash, str(index)))
        return sha256(identity.encode("utf-8")).hexdigest()

    async def replace_version(
        self, project_id: str, document_id: str, source_hash: str, blocks: list[dict]
    ) -> int:
        if blocks:
            from pymongo import UpdateOne

            operations = []
            for index, block in enumerate(blocks):
                payload = {
                    "_id": self.block_id(project_id, document_id, source_hash, index),
                    "project_id": project_id,
                    "document_id": document_id,
                    "source_hash": source_hash,
                    "block_index": index,
                    "block": block,
                }
                operations.append(
                    UpdateOne({"_id": payload["_id"]}, {"$set": payload}, upsert=True)
                )
            for start in range(0, len(operations), 500):
                await self.blocks.bulk_write(operations[start : start + 500], ordered=True)
        await self.blocks.delete_many(
            {
                "project_id": project_id,
                "document_id": document_id,
                "source_hash": source_hash,
                "block_index": {"$gte": len(blocks)},
            }
        )
        return len(blocks)

    async def list_version(
        self, project_id: str, document_id: str, source_hash: str
    ) -> list[dict]:
        rows = await self.blocks.find(
            {
                "project_id": project_id,
                "document_id": document_id,
                "source_hash": source_hash,
            },
            {"_id": 0, "block": 1},
        ).sort("block_index", 1).to_list(None)
        return [row["block"] for row in rows if isinstance(row.get("block"), dict)]

    async def page_version(
        self,
        project_id: str,
        document_id: str,
        source_hash: str,
        offset: int,
        limit: int,
    ) -> list[dict]:
        rows = await self.blocks.find(
            {
                "project_id": project_id,
                "document_id": document_id,
                "source_hash": source_hash,
                "block_index": {"$gte": offset},
            },
            {"_id": 0, "block_index": 1, "block": 1},
        ).sort("block_index", 1).limit(limit + 1).to_list(limit + 1)
        return rows

    async def delete_version(
        self, project_id: str, document_id: str, source_hash: str
    ) -> None:
        await self.blocks.delete_many(
            {
                "project_id": project_id,
                "document_id": document_id,
                "source_hash": source_hash,
            }
        )

    async def delete_obsolete_versions(
        self, project_id: str, document_id: str, keep_source_hash: str
    ) -> None:
        await self.blocks.delete_many(
            {
                "project_id": project_id,
                "document_id": document_id,
                "source_hash": {"$ne": keep_source_hash},
            }
        )


requirement_source_block_repository = RequirementSourceBlockRepository()
