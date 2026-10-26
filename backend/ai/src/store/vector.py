from typing import Dict, List, Optional

import httpx
from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from src.core.infrastructure.configuration import settings
from src.schemas.project import QdrantPointPayload


class VectorStore:
    UPSERT_BATCH_SIZE = 64
    PAYLOAD_INDEX_FIELDS = {
        "creator_id": PayloadSchemaType.KEYWORD,
        "owner_id": PayloadSchemaType.KEYWORD,
        "source_type": PayloadSchemaType.KEYWORD,
        "authority": PayloadSchemaType.KEYWORD,
        "project_id": PayloadSchemaType.KEYWORD,
        "artifact_type": PayloadSchemaType.KEYWORD,
        "artifact_id": PayloadSchemaType.KEYWORD,
        "artifact_version_id": PayloadSchemaType.KEYWORD,
        "module": PayloadSchemaType.KEYWORD,
        "status": PayloadSchemaType.KEYWORD,
        "document_id": PayloadSchemaType.KEYWORD,
        "visibility": PayloadSchemaType.KEYWORD,
        "shared_with": PayloadSchemaType.KEYWORD,
        "source_hash": PayloadSchemaType.KEYWORD,
        "content_type": PayloadSchemaType.KEYWORD,
        "parser_name": PayloadSchemaType.KEYWORD,
        "parser_version": PayloadSchemaType.KEYWORD,
        "ocr_enabled": PayloadSchemaType.BOOL,
        "extraction_status": PayloadSchemaType.KEYWORD,
        "unprocessed_block_count": PayloadSchemaType.INTEGER,
        "index_generation": PayloadSchemaType.KEYWORD,
        "indexed_at": PayloadSchemaType.DATETIME,
        "conflict_key": PayloadSchemaType.KEYWORD,
        "claim_value": PayloadSchemaType.KEYWORD,
        "embedding_model": PayloadSchemaType.KEYWORD,
    }
    UNINDEXED_POLYMORPHIC_PAYLOAD_FIELDS = ("source_version",)

    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=60.0,
        )
        self.collection_name = "veriq"
        self.upsert_batch_size = self.UPSERT_BATCH_SIZE

    async def ensure_collection(self):
        try:
            collections = await self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            if not exists:
                from src.services.embedding import embedder

                try:
                    await self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=embedder._dimensions, distance=Distance.COSINE
                        ),
                    )
                except Exception as error:
                    if "Alias with the same name already exists" not in str(error):
                        raise
                    logger.info("Using existing Qdrant alias for %s", self.collection_name)
            collection = await self.client.get_collection(self.collection_name)
            payload_schema = collection.payload_schema or {}
            for field, field_schema in self.PAYLOAD_INDEX_FIELDS.items():
                current = payload_schema.get(field)
                current_type = getattr(current, "data_type", None)
                if current_type is not None and current_type != field_schema:
                    try:
                        await self.client.delete_payload_index(
                            collection_name=self.collection_name,
                            field_name=field,
                            wait=True,
                        )
                    except Exception:
                        latest = await self.client.get_collection(self.collection_name)
                        latest_schema = latest.payload_schema or {}
                        latest_type = getattr(latest_schema.get(field), "data_type", None)
                        if latest_type != field_schema:
                            raise
                try:
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field,
                        field_schema=field_schema,
                        wait=True,
                    )
                except Exception:
                    latest = await self.client.get_collection(self.collection_name)
                    latest_schema = latest.payload_schema or {}
                    latest_type = getattr(latest_schema.get(field), "data_type", None)
                    if latest_type != field_schema:
                        raise
            for field in self.UNINDEXED_POLYMORPHIC_PAYLOAD_FIELDS:
                if field in payload_schema:
                    try:
                        await self.client.delete_payload_index(
                            collection_name=self.collection_name,
                            field_name=field,
                            wait=True,
                        )
                    except Exception:
                        latest = await self.client.get_collection(self.collection_name)
                        if field in (latest.payload_schema or {}):
                            raise
        except Exception:
            logger.exception("System search index structure initialization error")
            raise

    async def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
    ):
        if not (len(ids) == len(embeddings) == len(documents) == len(metadatas)):
            raise ValueError("vector_upsert_batch_lengths_must_match")
        batch_size = self.upsert_batch_size
        for batch_start in range(0, len(ids), batch_size):
            batch_end = min(batch_start + batch_size, len(ids))
            points = []
            for i in range(batch_start, batch_end):
                metadata = metadatas[i]
                if not isinstance(metadata, dict):
                    raise ValueError("vector_upsert_metadata_must_be_object")
                if "text" in metadata and metadata["text"] != documents[i]:
                    raise ValueError("vector_upsert_content_metadata_conflict")
                payload_values = dict(metadata)
                payload_values.setdefault("char_count", len(documents[i]))
                payload_values.setdefault("word_count", len(documents[i].split()))
                payload = QdrantPointPayload.model_validate(
                    {**payload_values, "text": documents[i]}
                ).model_dump(exclude_none=True)
                points.append(
                    PointStruct(id=ids[i], vector=embeddings[i], payload=payload)
                )
            await self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

    async def wait_upsert(self):
        return None

    async def query(
        self,
        query_vector: List[float],
        document_ids: Optional[List[str]] = None,
        limit: int = 20,
        requester_id: Optional[str] = None,
        is_admin: bool = False,
        metadata_filters: Optional[Dict] = None,
    ) -> List[Dict]:
        must = []
        if document_ids:
            must.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
        for key, value in (metadata_filters or {}).items():
            if value is None:
                continue
            match = MatchAny(any=value) if isinstance(value, list) else MatchValue(value=value)
            must.append(FieldCondition(key=key, match=match))
        if not is_admin:
            access_conditions = [
                FieldCondition(key="visibility", match=MatchValue(value="public")),
            ]
            project_scope = (metadata_filters or {}).get("project_id")
            if project_scope is not None:
                project_ids = project_scope if isinstance(project_scope, list) else [project_scope]
                project_ids = [str(value) for value in project_ids if value is not None]
                if project_ids:
                    access_conditions.append(
                        Filter(
                            must=[
                                FieldCondition(
                                    key="visibility",
                                    match=MatchValue(value="project"),
                                ),
                                FieldCondition(
                                    key="project_id",
                                    match=MatchAny(any=project_ids),
                                ),
                            ]
                        )
                    )
            if document_ids:
                access_conditions.append(
                    Filter(
                        must=[
                            FieldCondition(
                                key="visibility",
                                match=MatchValue(value="project"),
                            ),
                            FieldCondition(
                                key="document_id",
                                match=MatchAny(any=document_ids),
                            ),
                        ]
                    )
                )
            if requester_id:
                access_conditions.extend(
                    [
                        FieldCondition(key="owner_id", match=MatchValue(value=str(requester_id))),
                        FieldCondition(key="creator_id", match=MatchValue(value=str(requester_id))),
                        FieldCondition(key="shared_with", match=MatchAny(any=[str(requester_id)])),
                    ]
                )
            must.append(Filter(should=access_conditions))
        query_filter = Filter(must=must) if must else None

        if limit < 1 or limit > 100:
            raise ValueError("Vector query limit must be between 1 and 100")
        try:
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "id": str(hit.id),
                    "text": hit.payload.get("text", ""),
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                    "score": hit.score,
                }
                for hit in results
            ]
        except Exception:
            logger.exception("Search query parsing and processing error")
            raise

    async def scroll_all(self, batch_size: int = 256) -> List[Dict]:
        documents: List[Dict] = []
        async for batch in self.iter_scroll_batches(batch_size):
            documents.extend(batch)
        return documents

    async def iter_scroll_batches(self, batch_size: int = 256):
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
            raise ValueError("vector_scroll_batch_size_invalid")
        offset = None
        while True:
            points, next_offset = await self.client.scroll(
                collection_name=self.collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if points:
                yield [
                    {
                        "id": str(point.id),
                        "text": (point.payload or {}).get("text", ""),
                        "metadata": {
                            key: value
                            for key, value in (point.payload or {}).items()
                            if key != "text"
                        },
                    }
                    for point in points
                ]
            if next_offset is None:
                break
            offset = next_offset

    async def delete_by_document(self, document_id: str):
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                ),
            )
        except Exception:
            logger.exception("Search index deletion error")
            raise

    async def ids_by_document(self, document_id: str) -> List[str]:
        point_ids = []
        offset = None
        while True:
            points, next_offset = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                ),
                limit=256,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            point_ids.extend(str(point.id) for point in points)
            if next_offset is None:
                return point_ids
            offset = next_offset

    async def delete_ids(self, point_ids: List[str]):
        if not point_ids:
            return
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=point_ids),
            wait=True,
        )

    async def delete_payload_keys(self, point_ids: List[str], keys: List[str]):
        if not point_ids or not keys:
            return
        await self.client.delete_payload(
            collection_name=self.collection_name,
            keys=keys,
            points=PointIdsList(points=point_ids),
            wait=True,
        )

    async def ids_by_artifact_version(self, project_id: str, artifact_version_id: str) -> List[str]:
        point_ids = []
        offset = None
        query_filter = Filter(
            must=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(
                    key="artifact_version_id", match=MatchValue(value=artifact_version_id)
                ),
            ]
        )
        while True:
            points, next_offset = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=256,
                offset=offset,
                with_payload=["document_id"],
                with_vectors=False,
            )
            point_ids.extend(
                str(point.id)
                for point in points
                if not (point.payload or {}).get("document_id")
            )
            if next_offset is None:
                return point_ids
            offset = next_offset

    async def list_artifact_version_points(
        self, project_id: str, artifact_version_id: str
    ) -> List[Dict]:
        documents = []
        offset = None
        query_filter = Filter(
            must=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(
                    key="artifact_version_id", match=MatchValue(value=artifact_version_id)
                ),
            ]
        )
        while True:
            points, next_offset = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=256,
                offset=offset,
                with_payload=["index_generation", "indexed_at", "document_id"],
                with_vectors=False,
            )
            documents.extend(
                {
                    "id": str(point.id),
                    "metadata": dict(point.payload or {}),
                }
                for point in points
                if not (point.payload or {}).get("document_id")
            )
            if next_offset is None:
                return documents
            offset = next_offset

    async def scroll_artifact_version(
        self,
        project_id: str,
        artifact_version_id: str,
        limit: int,
        offset=None,
        index_generation: str | None = None,
    ):
        conditions = [
            FieldCondition(key="project_id", match=MatchValue(value=project_id)),
            FieldCondition(
                key="artifact_version_id", match=MatchValue(value=artifact_version_id)
            ),
        ]
        if index_generation and index_generation != "LEGACY":
            conditions.append(
                FieldCondition(key="index_generation", match=MatchValue(value=index_generation))
            )
        query_filter = Filter(must=conditions)
        documents = []
        next_offset = offset
        while len(documents) < limit:
            points, next_offset = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=limit - len(documents),
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )
            documents.extend(
                {
                    "id": str(point.id),
                    "text": str((point.payload or {}).get("text") or ""),
                    "metadata": {
                        key: value
                        for key, value in (point.payload or {}).items()
                        if key != "text"
                    },
                }
                for point in points
                if not (point.payload or {}).get("document_id")
                and (
                    index_generation != "LEGACY"
                    or not (point.payload or {}).get("index_generation")
                )
            )
            if next_offset is None:
                break
        if documents and next_offset is not None:
            page_cursor = next_offset
            lookahead_offset = page_cursor
            has_more_artifacts = False
            while lookahead_offset is not None:
                lookahead_points, lookahead_offset = await self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=query_filter,
                    limit=1,
                    offset=lookahead_offset,
                    with_payload=True,
                    with_vectors=False,
                )
                if any(
                    not (point.payload or {}).get("document_id")
                    and (
                        index_generation != "LEGACY"
                        or not (point.payload or {}).get("index_generation")
                    )
                    for point in lookahead_points
                ):
                    has_more_artifacts = True
                    break
            next_offset = page_cursor if has_more_artifacts else None
        return documents, next_offset


vector_store = VectorStore()
