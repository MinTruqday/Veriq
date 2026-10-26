import asyncio
from hashlib import sha256
from typing import Dict, List, Optional

from loguru import logger

from src.clients.content import ContentClient
from src.core.infrastructure.configuration import settings
from src.knowledge.metadata import public_retrieval_metadata
from src.repositories.project_artifact_generation import project_artifact_generation_repository
from src.services.embedding import embedder
from src.services.inference import decompose_retrieval
from src.store.bm25 import bm25_store
from src.store.vector import vector_store
from src.utils.model_provider import auxiliary_client


class RetrievalUnavailableError(RuntimeError):
    pass


async def initialize_retrieval():
    embedding = await embedder.initialize()
    if len(embedding) != embedder._dimensions:
        raise RuntimeError("Embedding model dimension does not match the retrieval index")
    await vector_store.ensure_collection()

    async def current_documents():
        legacy_count = 0
        migrated_count = 0
        async for documents in vector_store.iter_scroll_batches():
            legacy_file_url_ids = [
                document["id"]
                for document in documents
                if document.get("metadata", {}).get("file_url")
            ]
            if legacy_file_url_ids:
                await vector_store.delete_payload_keys(legacy_file_url_ids, ["file_url"])
                legacy_count += len(legacy_file_url_ids)
                for document in documents:
                    metadata = document.get("metadata") or {}
                    metadata.pop("file_url", None)
                    document["metadata"] = metadata

            stale_documents = [
                document
                for document in documents
                if document.get("metadata", {}).get("embedding_model")
                != settings.EMBEDDING_MODEL
            ]
            if stale_documents:
                embeddings = await embedder.embed_batch(
                    [document.get("text", "") for document in stale_documents]
                )
                metadatas = [
                    {
                        **document.get("metadata", {}),
                        "embedding_model": settings.EMBEDDING_MODEL,
                        "embedding_input_mode": "TEXT",
                        "embedding_input_hash": sha256(
                            document.get("text", "").encode("utf-8")
                        ).hexdigest(),
                    }
                    for document in stale_documents
                ]
                await vector_store.upsert(
                    ids=[document["id"] for document in stale_documents],
                    embeddings=embeddings,
                    documents=[document.get("text", "") for document in stale_documents],
                    metadatas=metadatas,
                )
                for document, metadata in zip(stale_documents, metadatas):
                    document["metadata"] = metadata
                migrated_count += len(stale_documents)

            for document in documents:
                yield document

        if legacy_count:
            logger.info(
                "Removed legacy object-storage URLs from {} vector payloads",
                legacy_count,
            )
        if migrated_count:
            logger.info("Migrated {} AI vector points to hosted embedding model", migrated_count)

    await bm25_store.initialize_stream(current_documents())
    await retriever.initialize()
    logger.info("AI retrieval capability initialized and ready")


class RetrievalService:
    def __init__(self):
        self._reranker_ready = False

    @staticmethod
    async def _filter_active_artifact_generations(documents: List[Dict]) -> List[Dict]:
        try:
            return await project_artifact_generation_repository.filter_active(documents)
        except Exception as error:
            logger.warning(
                "Artifact generation verification failed error_type={}", type(error).__name__
            )
            raise RetrievalUnavailableError(
                "artifact_generation_verification_unavailable"
            ) from error

    @staticmethod
    async def _filter_currently_accessible_sources(
        documents: List[Dict], requester_id: Optional[str], is_admin: bool
    ) -> List[Dict]:
        source_ids_by_result = []
        index_document_ids_by_result = []
        invalid_source_metadata_by_result = []
        all_source_ids = []
        for document in documents:
            metadata = document.get("metadata") or document
            source_ids = []
            invalid_source_metadata = False
            for key in ("document_id", "source_document_id"):
                value = metadata.get(key)
                if value:
                    source_ids.append(str(value).strip())
            related_source_ids = metadata.get("source_document_ids")
            if related_source_ids is not None:
                if not isinstance(related_source_ids, list) or any(
                    not isinstance(value, (str, int)) or not str(value).strip()
                    for value in related_source_ids
                ):
                    invalid_source_metadata = True
                else:
                    source_ids.extend(str(value).strip() for value in related_source_ids)
            source_ids = list(dict.fromkeys(value for value in source_ids if value))
            source_ids_by_result.append(source_ids)
            invalid_source_metadata_by_result.append(invalid_source_metadata)
            all_source_ids.extend(source_ids)
            indexed_document_id = str(metadata.get("document_id") or "").strip()
            index_document_ids_by_result.append(
                [indexed_document_id] if indexed_document_id else []
            )

        if not all_source_ids:
            return [
                document
                for document, invalid in zip(
                    documents, invalid_source_metadata_by_result
                )
                if not invalid
            ]
        all_source_ids = list(dict.fromkeys(all_source_ids))

        try:
            active_generations = await ContentClient.active_index_generations_many(
                all_source_ids, requester_id, is_admin
            )
        except Exception as error:
            logger.warning(
                "Live document access check failed error_type={}", type(error).__name__
            )
            raise RetrievalUnavailableError(
                "document_access_verification_unavailable"
            ) from error

        current_documents = []
        for document, source_ids, indexed_document_ids, invalid_source_metadata in zip(
            documents,
            source_ids_by_result,
            index_document_ids_by_result,
            invalid_source_metadata_by_result,
        ):
            if invalid_source_metadata:
                continue
            if not all(source_id in active_generations for source_id in source_ids):
                continue
            metadata = document.get("metadata") or document
            point_generation = str(metadata.get("index_generation") or "")
            if any(
                str(active_generations[source_id] or "") != point_generation
                for source_id in indexed_document_ids
            ):
                continue
            current_documents.append(document)
        return current_documents

    async def initialize(self):
        try:
            scores = await auxiliary_client.rerank(
                [["readiness", "readiness"], ["readiness", "unrelated"]]
            )
            self._reranker_ready = len(scores) == 2
        except Exception:
            logger.exception("AI ranking model loading error")
            self._reranker_ready = False

    def get_citations(self, results: List[Dict]) -> List[Dict]:
        seen = set()
        citations = []
        for doc in results:
            meta = public_retrieval_metadata(doc.get("metadata", {}))
            doc_id = str(meta.get("document_id") or "")
            artifact_id = str(meta.get("artifact_id") or "")
            artifact_version_id = str(meta.get("artifact_version_id") or "")
            title = meta.get("title", "")
            chunk_idx = meta.get("chunk_index", "")
            chunk_id = str(meta.get("chunk_id") or "")
            point_id = str(doc.get("id") or "")
            identity = point_id or "|".join(
                (doc_id, artifact_id, artifact_version_id, chunk_id, str(chunk_idx))
            )
            if not identity.strip("|") or identity in seen:
                continue
            seen.add(identity)
            subject_id = artifact_id or doc_id
            label = (
                f"{title} (ID: {subject_id}, chunk {chunk_idx})"
                if title
                else f"ID: {subject_id}, chunk {chunk_idx}"
            )
            citations.append(
                {
                    "point_id": point_id,
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "title": title,
                    "chunk_index": chunk_idx,
                    "label": label,
                    "artifact_type": str(meta.get("artifact_type") or ""),
                    "artifact_id": artifact_id,
                    "artifact_version_id": artifact_version_id,
                    "source_version": meta.get("source_version"),
                    "page_numbers": list(meta.get("page_numbers") or []),
                    "source_spans": list(meta.get("source_spans") or []),
                }
            )
        return citations

    @staticmethod
    def detect_source_conflicts(results: List[Dict]) -> List[Dict]:
        grouped: Dict[str, Dict[str, List[Dict]]] = {}
        for document in results:
            metadata = document.get("metadata", {})
            conflict_key = str(metadata.get("conflict_key") or "").strip()
            claim_value = str(metadata.get("claim_value") or "").strip()
            if not conflict_key or not claim_value:
                continue
            grouped.setdefault(conflict_key, {}).setdefault(claim_value, []).append(
                {
                    "document_id": metadata.get("document_id"),
                    "chunk_id": metadata.get("chunk_id"),
                    "authority": metadata.get("authority"),
                    "source_version": metadata.get("source_version"),
                }
            )
        return [
            {
                "conflict_key": key,
                "claims": [
                    {"value": value, "sources": sources} for value, sources in claims.items()
                ],
            }
            for key, claims in grouped.items()
            if len(claims) > 1
        ]

    @staticmethod
    def _result_key(document: Dict) -> str:
        if document.get("id"):
            return str(document["id"])
        metadata = document.get("metadata", {})
        return "|".join(
            [
                str(metadata.get("document_id", "")),
                str(metadata.get("chunk_id", "")),
                document.get("text", ""),
            ]
        )

    def _rrf_fuse(
        self,
        dense_documents: List[Dict],
        sparse_documents: List[Dict],
        rank_constant: Optional[int] = None,
    ) -> List[Dict]:
        if rank_constant is None:
            rank_constant = 60
        fused: Dict[str, Dict] = {}
        for source, documents in (("dense", dense_documents), ("bm25", sparse_documents)):
            for rank, document in enumerate(documents, start=1):
                key = self._result_key(document)
                metadata = document.get("metadata") or {}
                public_document = {
                    **document,
                    "metadata": public_retrieval_metadata(metadata),
                }
                entry = fused.setdefault(
                    key, {**public_document, "rrf_score": 0.0, "retrieval_sources": []}
                )
                entry["rrf_score"] += 1.0 / (rank_constant + rank)
                if source not in entry["retrieval_sources"]:
                    entry["retrieval_sources"].append(source)
                if source == "dense":
                    entry["dense_score"] = float(document.get("score", 0.0))
                else:
                    entry["bm25_score"] = float(
                        document.get("bm25_score", document.get("score", 0.0))
                    )
        results = sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)
        for result in results:
            result["score"] = result["rrf_score"]
        return results

    async def retrieve(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        k: Optional[int] = None,
        query_vector_override: Optional[List[float]] = None,
        requester_id: Optional[str] = None,
        is_admin: bool = False,
        metadata_filters: Optional[Dict] = None,
    ) -> List[Dict]:
        result_count = 5 if k is None else k
        fetch_limit = min(
            max(result_count * 3, result_count),
            100,
        )

        async def dense_search():
            query_vector = query_vector_override
            if query_vector is None:
                query_vector = await embedder.embed_query(query)
            return await vector_store.query(
                query_vector=query_vector,
                document_ids=document_ids,
                limit=fetch_limit,
                requester_id=requester_id,
                is_admin=is_admin,
                metadata_filters=metadata_filters,
            )

        dense_result, sparse_result = await asyncio.gather(
            asyncio.wait_for(
                dense_search(), timeout=settings.MODEL_TIMEOUT_SECONDS
            ),
            bm25_store.search(
                query=query,
                document_ids=document_ids,
                limit=fetch_limit,
                requester_id=requester_id,
                is_admin=is_admin,
                metadata_filters=metadata_filters,
            ),
            return_exceptions=True,
        )
        if isinstance(dense_result, Exception):
            logger.error("Dense retrieval failed: {}", type(dense_result).__name__)
            dense_documents = []
        else:
            dense_documents = dense_result
        if isinstance(sparse_result, Exception):
            logger.error("BM25 retrieval failed: {}", type(sparse_result).__name__)
            sparse_documents = []
        else:
            sparse_documents = sparse_result
        if isinstance(dense_result, Exception) and isinstance(sparse_result, Exception):
            raise RetrievalUnavailableError("dense_and_sparse_retrieval_unavailable")
        candidates = [*dense_documents, *sparse_documents]
        if not candidates:
            return []

        candidates = await self._filter_active_artifact_generations(candidates)
        candidates = await self._filter_currently_accessible_sources(
            candidates, requester_id, is_admin
        )
        if not candidates:
            return []

        current_candidate_keys = {self._result_key(document) for document in candidates}
        dense_documents = [
            document
            for document in dense_documents
            if self._result_key(document) in current_candidate_keys
        ]
        sparse_documents = [
            document
            for document in sparse_documents
            if self._result_key(document) in current_candidate_keys
        ]
        documents = self._rrf_fuse(dense_documents, sparse_documents)
        if not documents:
            return []

        if not self._reranker_ready:
            return documents[:result_count]

        try:
            pairs = [[query, doc.get("text", "")] for doc in documents]
            scores = await asyncio.wait_for(
                auxiliary_client.rerank(pairs),
                timeout=settings.MODEL_TIMEOUT_SECONDS,
            )
            scored_documents = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
            results = await self._filter_active_artifact_generations(
                [doc for doc, _ in scored_documents[:result_count]]
            )
            return await self._filter_currently_accessible_sources(
                results, requester_id, is_admin
            )
        except Exception:
            logger.exception("Search result sorting error")
            results = await self._filter_active_artifact_generations(
                documents[:result_count]
            )
            return await self._filter_currently_accessible_sources(
                results, requester_id, is_admin
            )

    async def cross_document_retrieve(
        self,
        question: str,
        document_ids: List[str],
        k: Optional[int] = None,
        requester_id: Optional[str] = None,
        is_admin: bool = False,
        metadata_filters: Optional[Dict] = None,
    ) -> List[Dict]:
        result_count = 5 if k is None else k
        if not document_ids or len(document_ids) < 2:
            return await self.retrieve(
                query=question,
                document_ids=document_ids,
                k=result_count,
                requester_id=requester_id,
                is_admin=is_admin,
                metadata_filters=metadata_filters,
            )

        sub_queries = [question] * len(document_ids)
        try:
            decomposed = await decompose_retrieval(question, document_ids)
            if len(decomposed) == len(document_ids):
                sub_queries = decomposed
        except Exception:
            logger.exception("Cross-document query decomposition failed")

        tasks = [
            self.retrieve(
                sub_queries[index],
                [doc_id],
                k=result_count,
                requester_id=requester_id,
                is_admin=is_admin,
                metadata_filters=metadata_filters,
            )
            for index, doc_id in enumerate(document_ids)
        ]
        results_per_doc = await asyncio.gather(*tasks, return_exceptions=True)
        if results_per_doc and all(isinstance(result, Exception) for result in results_per_doc):
            raise RetrievalUnavailableError("cross_document_retrieval_unavailable")

        merged: List[Dict] = []
        for r in results_per_doc:
            if isinstance(r, list):
                merged.extend(r)

        seen = set()
        unique = []
        for d in merged:
            t = d.get("text", "")
            if t not in seen:
                seen.add(t)
                unique.append(d)

        return await self._filter_active_artifact_generations(
            self._lost_in_the_middle_reorder(unique)[:result_count]
        )

    def _lost_in_the_middle_reorder(self, documents: List[Dict]) -> List[Dict]:
        if len(documents) <= 2:
            return documents
        result = [None] * len(documents)
        left, right = 0, len(documents) - 1
        for i, doc in enumerate(documents):
            if i % 2 == 0:
                result[left] = doc
                left += 1
            else:
                result[right] = doc
                right -= 1
        return [d for d in result if d is not None]


retriever = RetrievalService()
