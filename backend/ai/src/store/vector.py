from typing import Dict, List, Optional

import httpx
from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    IsEmptyCondition,
    MatchAny,
    MatchValue,
    PayloadField,
    PayloadSchemaType,
    Prefetch,
    PointIdsList,
    PointStruct,
    Rrf,
    RrfQuery,
    TextIndexParams,
    TextIndexType,
    TextQuery,
    TextScoringType,
    TokenizerType,
    VectorParams,
)

from src.core.infrastructure.configuration import settings
from src.schemas.project import (
    DOCUMENT_INDEXED_ARTIFACT_TYPES,
    QdrantPointPayload,
    is_document_indexed_payload,
)


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
        "ai_enabled": PayloadSchemaType.BOOL,
        "document_id": PayloadSchemaType.KEYWORD,
        "source_document_id": PayloadSchemaType.KEYWORD,
        "visibility": PayloadSchemaType.KEYWORD,
        "shared_with": PayloadSchemaType.KEYWORD,
        "content_type": PayloadSchemaType.KEYWORD,
        "index_generation": PayloadSchemaType.KEYWORD,
        "document_index_contract_version": PayloadSchemaType.INTEGER,
        "embedding_model": PayloadSchemaType.KEYWORD,
    }
    @staticmethod
    def _is_project_artifact_payload(payload: Dict) -> bool:
        return not payload.get("document_id") or payload.get("artifact_type") == "requirement_document"

    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=60.0,
        )
        self.collection_name = "veriq"
        self.upsert_batch_size = self.UPSERT_BATCH_SIZE

    @staticmethod
    def _has_bm25_text_index(schema) -> bool:
        if schema is None or schema.data_type != PayloadSchemaType.TEXT:
            return False
        params = schema.params
        scoring = getattr(params, "scoring", None)
        if scoring is True:
            return True
        return getattr(scoring, "type", None) == TextScoringType.BM25

    async def _ensure_text_scoring_index(self):
        collection = await self.client.get_collection(self.collection_name)
        schema = (collection.payload_schema or {}).get("text")
        if schema is None:
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="text",
                field_schema=TextIndexParams(
                    type=TextIndexType.TEXT,
                    tokenizer=TokenizerType.WORD,
                    lowercase=True,
                    min_token_len=1,
                    scoring=True,
                ),
                wait=True,
            )
            return
        if not self._has_bm25_text_index(schema):
            raise RuntimeError("qdrant_text_scoring_index_schema_mismatch")

    @staticmethod
    def _point_results(points) -> List[Dict]:
        return [
            {
                "id": str(point.id),
                "text": (point.payload or {}).get("text", ""),
                "metadata": {
                    key: value for key, value in (point.payload or {}).items() if key != "text"
                },
                "score": point.score,
            }
            for point in points
        ]

    async def close(self):
        await self.client.close()

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
            from src.services.embedding import embedder

            vector_config = collection.config.params.vectors
            if (
                isinstance(vector_config, dict)
                or getattr(vector_config, "size", None) != embedder._dimensions
                or getattr(vector_config, "distance", None) != Distance.COSINE
            ):
                raise RuntimeError("qdrant_collection_vector_schema_mismatch")
            payload_schema = collection.payload_schema or {}
            for field, field_schema in self.PAYLOAD_INDEX_FIELDS.items():
                current = payload_schema.get(field)
                current_type = getattr(current, "data_type", None)
                if current is not None:
                    if current_type != field_schema:
                        raise RuntimeError(f"qdrant_payload_index_schema_mismatch:{field}")
                    continue
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
                        raise RuntimeError(
                            f"qdrant_payload_index_schema_mismatch:{field}"
                        )
            await self._ensure_text_scoring_index()
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
                if (
                    is_document_indexed_payload(payload)
                    and payload.get("artifact_type")
                    not in DOCUMENT_INDEXED_ARTIFACT_TYPES
                ):
                    raise ValueError("qdrant_document_artifact_type_missing")
                if (
                    is_document_indexed_payload(payload)
                    and payload.get("document_index_contract_version")
                    != settings.DOCUMENT_INDEX_CONTRACT_VERSION
                ):
                    raise ValueError("qdrant_document_index_contract_version_mismatch")
                points.append(
                    PointStruct(id=ids[i], vector=embeddings[i], payload=payload)
                )
            await self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

    async def query(
        self,
        query_vector: List[float],
        document_ids: Optional[List[str]] = None,
        limit: int = 20,
        requester_id: Optional[str] = None,
        is_admin: bool = False,
        metadata_filters: Optional[Dict] = None,
    ) -> List[Dict]:
        query_filter = self._query_filter(
            document_ids=document_ids,
            requester_id=requester_id,
            is_admin=is_admin,
            metadata_filters=metadata_filters,
        )
        if limit < 1 or limit > 100:
            raise ValueError("Vector query limit must be between 1 and 100")
        try:
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return self._point_results(response.points)
        except Exception:
            logger.exception("Search query parsing and processing error")
            raise

    async def hybrid_query(
        self,
        query_text: str,
        query_vector: List[float],
        document_ids: Optional[List[str]] = None,
        limit: int = 20,
        requester_id: Optional[str] = None,
        is_admin: bool = False,
        metadata_filters: Optional[Dict] = None,
    ) -> List[Dict]:
        query_text = str(query_text or "").strip()
        if not query_text:
            return await self.query(
                query_vector=query_vector,
                document_ids=document_ids,
                limit=limit,
                requester_id=requester_id,
                is_admin=is_admin,
                metadata_filters=metadata_filters,
            )
        if limit < 1 or limit > 100:
            raise ValueError("Vector query limit must be between 1 and 100")
        query_filter = self._query_filter(
            document_ids=document_ids,
            requester_id=requester_id,
            is_admin=is_admin,
            metadata_filters=metadata_filters,
        ).model_dump(mode="json", exclude_none=True)
        response = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                Prefetch(query=query_vector, filter=query_filter, limit=limit),
                Prefetch(
                    query=TextQuery(text=query_text),
                    using="text",
                    filter=query_filter,
                    limit=limit,
                ),
            ],
            query=RrfQuery(rrf=Rrf(k=60)),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return self._point_results(response.points)

    def _query_filter(
        self,
        document_ids: Optional[List[str]],
        requester_id: Optional[str],
        is_admin: bool,
        metadata_filters: Optional[Dict],
    ) -> Filter:
        must = [
            FieldCondition(
                key="embedding_model",
                match=MatchValue(value=settings.EMBEDDING_MODEL),
            )
        ]
        if document_ids:
            must.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
        for key, value in (metadata_filters or {}).items():
            if value is None:
                continue
            match = MatchAny(any=value) if isinstance(value, list) else MatchValue(value=value)
            must.append(FieldCondition(key=key, match=match))
        must.append(
            Filter(
                should=[
                    Filter(
                        must_not=[
                            FieldCondition(
                                key="artifact_type",
                                match=MatchAny(
                                    any=list(DOCUMENT_INDEXED_ARTIFACT_TYPES)
                                ),
                            ),
                            IsEmptyCondition(is_empty=PayloadField(key="artifact_type")),
                        ],
                    ),
                    Filter(
                        must=[
                            IsEmptyCondition(is_empty=PayloadField(key="artifact_type")),
                            IsEmptyCondition(is_empty=PayloadField(key="document_id")),
                            IsEmptyCondition(is_empty=PayloadField(key="source_document_id")),
                        ]
                    ),
                    Filter(
                        must=[
                            FieldCondition(
                                key="artifact_type",
                                match=MatchValue(value="requirement_document"),
                            ),
                            FieldCondition(key="ai_enabled", match=MatchValue(value=True)),
                            FieldCondition(key="status", match=MatchValue(value="READY")),
                            FieldCondition(
                                key="document_index_contract_version",
                                match=MatchValue(
                                    value=settings.DOCUMENT_INDEX_CONTRACT_VERSION
                                ),
                            ),
                        ]
                    ),
                    Filter(
                        must=[
                            FieldCondition(
                                key="artifact_type",
                                match=MatchAny(
                                    any=[
                                        artifact_type
                                        for artifact_type in DOCUMENT_INDEXED_ARTIFACT_TYPES
                                        if artifact_type != "requirement_document"
                                    ]
                                ),
                            ),
                            FieldCondition(
                                key="document_index_contract_version",
                                match=MatchValue(
                                    value=settings.DOCUMENT_INDEX_CONTRACT_VERSION
                                ),
                            ),
                        ],
                        must_not=[
                            FieldCondition(
                                key="ai_enabled", match=MatchValue(value=False)
                            )
                        ],
                    ),
                ]
            )
        )
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

        return Filter(must=must) if must else Filter()

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
        document_id = str(document_id or "").strip()
        if not document_id:
            raise ValueError("document_index_cleanup_scope_invalid")
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                ),
                wait=True,
            )
        except Exception:
            logger.exception("Search index deletion error")
            raise

    async def delete_document_generation(
        self, document_id: str, index_generation: str
    ):
        document_id = str(document_id or "").strip()
        index_generation = str(index_generation or "").strip()
        if not document_id or not index_generation:
            raise ValueError("document_index_cleanup_scope_invalid")
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id", match=MatchValue(value=document_id)
                    ),
                    FieldCondition(
                        key="index_generation",
                        match=MatchValue(value=index_generation),
                    ),
                ]
            ),
            wait=True,
        )

    async def delete_stale_document_generations(
        self, document_id: str, active_generation: str
    ):
        document_id = str(document_id or "").strip()
        active_generation = str(active_generation or "").strip()
        if not document_id or not active_generation:
            raise ValueError("document_index_cleanup_scope_invalid")
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id", match=MatchValue(value=document_id)
                    )
                ],
                must_not=[
                    FieldCondition(
                        key="index_generation",
                        match=MatchValue(value=active_generation),
                    )
                ],
            ),
            wait=True,
        )

    async def delete_artifact_generation(
        self,
        project_id: str,
        artifact_type: str,
        artifact_id: str,
        artifact_version_id: str,
        index_generation: str,
    ):
        scope = tuple(
            str(value or "").strip()
            for value in (
                project_id,
                artifact_type,
                artifact_id,
                artifact_version_id,
                index_generation,
            )
        )
        if any(not value for value in scope):
            raise ValueError("project_artifact_cleanup_scope_invalid")
        (
            project_id,
            artifact_type,
            artifact_id,
            artifact_version_id,
            index_generation,
        ) = scope
        must_conditions = [
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(key="artifact_type", match=MatchValue(value=artifact_type)),
                FieldCondition(key="artifact_id", match=MatchValue(value=artifact_id)),
                FieldCondition(
                    key="artifact_version_id",
                    match=MatchValue(value=artifact_version_id),
                ),
                FieldCondition(
                    key="index_generation", match=MatchValue(value=index_generation)
                ),
            ]
        if artifact_type != "requirement_document":
            must_conditions.append(
                IsEmptyCondition(is_empty=PayloadField(key="document_id"))
            )
        query_filter = Filter(must=must_conditions)
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=query_filter,
            wait=True,
        )

    async def delete_stale_artifact_generations(
        self,
        project_id: str,
        artifact_type: str,
        artifact_id: str,
        artifact_version_id: str,
        active_generation: str,
    ):
        scope = tuple(
            str(value or "").strip()
            for value in (
                project_id,
                artifact_type,
                artifact_id,
                artifact_version_id,
                active_generation,
            )
        )
        if any(not value for value in scope):
            raise ValueError("project_artifact_cleanup_scope_invalid")
        (
            project_id,
            artifact_type,
            artifact_id,
            artifact_version_id,
            active_generation,
        ) = scope
        must_conditions = [
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(key="artifact_type", match=MatchValue(value=artifact_type)),
                FieldCondition(key="artifact_id", match=MatchValue(value=artifact_id)),
                FieldCondition(
                    key="artifact_version_id",
                    match=MatchValue(value=artifact_version_id),
                ),
            ]
        if artifact_type != "requirement_document":
            must_conditions.append(
                IsEmptyCondition(is_empty=PayloadField(key="document_id"))
            )
        query_filter = Filter(
            must=must_conditions,
            must_not=[
                FieldCondition(
                    key="index_generation", match=MatchValue(value=active_generation)
                )
            ],
        )
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=query_filter,
            wait=True,
        )

    async def delete_artifact_version(
        self, project_id: str, artifact_type: str, artifact_id: str, artifact_version_id: str
    ):
        scope = tuple(
            str(value or "").strip()
            for value in (project_id, artifact_type, artifact_id, artifact_version_id)
        )
        if any(not value for value in scope):
            raise ValueError("project_artifact_cleanup_scope_invalid")
        project_id, artifact_type, artifact_id, artifact_version_id = scope
        must_conditions = [
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(key="artifact_type", match=MatchValue(value=artifact_type)),
                FieldCondition(key="artifact_id", match=MatchValue(value=artifact_id)),
                FieldCondition(
                    key="artifact_version_id",
                    match=MatchValue(value=artifact_version_id),
                ),
            ]
        if artifact_type != "requirement_document":
            must_conditions.append(
                IsEmptyCondition(is_empty=PayloadField(key="document_id"))
            )
        query_filter = Filter(must=must_conditions)
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=query_filter,
            wait=True,
        )

    async def delete_project_artifact_version(
        self, project_id: str, artifact_version_id: str
    ):
        scope = tuple(
            str(value or "").strip() for value in (project_id, artifact_version_id)
        )
        if any(not value for value in scope):
            raise ValueError("project_artifact_cleanup_scope_invalid")
        project_id, artifact_version_id = scope
        requirement_document_filter = Filter(
            must=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(
                    key="artifact_version_id",
                    match=MatchValue(value=artifact_version_id),
                ),
                FieldCondition(
                    key="artifact_type", match=MatchValue(value="requirement_document")
                ),
            ]
        )
        project_artifact_filter = Filter(
            must=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(
                    key="artifact_version_id",
                    match=MatchValue(value=artifact_version_id),
                ),
                IsEmptyCondition(is_empty=PayloadField(key="document_id")),
            ],
            must_not=[
                IsEmptyCondition(is_empty=PayloadField(key="artifact_type")),
                IsEmptyCondition(is_empty=PayloadField(key="artifact_id")),
            ],
        )
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=requirement_document_filter,
            wait=True,
        )
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=project_artifact_filter,
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

    async def iter_artifact_version_summaries(
        self, project_id: str, artifact_version_id: str
    ):
        offset = None
        query_filter = Filter(
            must=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(
                    key="artifact_version_id",
                    match=MatchValue(value=artifact_version_id),
                ),
            ]
        )
        while True:
            points, next_offset = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=256,
                offset=offset,
                with_payload=["index_generation", "indexed_at", "document_id", "artifact_type"],
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                if self._is_project_artifact_payload(payload):
                    yield {
                        "id": str(point.id),
                        "index_generation": payload.get("index_generation"),
                        "indexed_at": payload.get("indexed_at"),
                    }
            if next_offset is None:
                return
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
                if self._is_project_artifact_payload(point.payload or {})
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
                    self._is_project_artifact_payload(point.payload or {})
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
