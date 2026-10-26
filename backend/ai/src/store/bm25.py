import asyncio
import re
from typing import Dict, List, Optional

from loguru import logger


class BM25Store:
    def __init__(self):
        self._documents: Dict[str, Dict] = {}
        self._ordered_ids: List[str] = []
        self._index = None
        self._staged_documents: Dict[str, Dict[str, Dict]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)

    def _build_index(self, documents: Dict[str, Dict]):
        from rank_bm25 import BM25Okapi

        ordered_ids = [
            point_id
            for point_id, document in documents.items()
            if self._tokenize(document.get("text", ""))
        ]
        if not ordered_ids:
            return [], None
        corpus = [
            self._tokenize(documents[point_id]["text"])
            for point_id in ordered_ids
        ]
        return ordered_ids, BM25Okapi(corpus)

    async def initialize(self, documents: List[Dict]) -> None:
        async def document_stream():
            for document in documents:
                yield document

        await self.initialize_stream(document_stream())

    async def initialize_stream(self, documents) -> None:
        async with self._lock:
            replacement = {}
            async for document in documents:
                if document.get("id") is None or not document.get("text", "").strip():
                    continue
                point_id = str(document["id"])
                replacement[point_id] = {
                    "id": point_id,
                    "text": document.get("text", ""),
                    "metadata": dict(document.get("metadata", {})),
                }
            ordered_ids, index = self._build_index(replacement)
            self._documents = replacement
            self._ordered_ids = ordered_ids
            self._index = index
            self._staged_documents = {}
        logger.info("Independent BM25 index initialized with {} chunks", len(replacement))

    async def stage_upsert(self, documents: List[Dict], stage_id: str = "default") -> None:
        normalized_stage_id = str(stage_id or "").strip()
        if not normalized_stage_id:
            raise ValueError("bm25_stage_id_invalid")
        async with self._lock:
            staged = self._staged_documents.setdefault(normalized_stage_id, {})
            for document in documents:
                point_id = str(document.get("id") or "")
                text = document.get("text", "").strip()
                if not point_id or not text:
                    continue
                staged[point_id] = {
                    "id": point_id,
                    "text": text,
                    "metadata": dict(document.get("metadata", {})),
                }

    async def publish_staged(self, stage_id: str = "default") -> None:
        normalized_stage_id = str(stage_id or "").strip()
        if not normalized_stage_id:
            raise ValueError("bm25_stage_id_invalid")
        async with self._lock:
            staged = self._staged_documents.get(normalized_stage_id)
            if not staged:
                raise RuntimeError("bm25_stage_not_found")
            replacement = {**self._documents, **staged}
            ordered_ids, index = self._build_index(replacement)
            self._documents = replacement
            self._ordered_ids = ordered_ids
            self._index = index
            self._staged_documents.pop(normalized_stage_id, None)

    async def discard_staged(self, stage_id: str) -> None:
        normalized_stage_id = str(stage_id or "").strip()
        if not normalized_stage_id:
            return
        async with self._lock:
            self._staged_documents.pop(normalized_stage_id, None)

    async def upsert(self, documents: List[Dict]) -> None:
        async with self._lock:
            replacement = dict(self._documents)
            for document in documents:
                point_id = str(document.get("id") or "")
                text = document.get("text", "").strip()
                if not point_id or not text:
                    continue
                replacement[point_id] = {
                    "id": point_id,
                    "text": text,
                    "metadata": dict(document.get("metadata", {})),
                }
            ordered_ids, index = self._build_index(replacement)
            self._documents = replacement
            self._ordered_ids = ordered_ids
            self._index = index

    async def delete_by_document(self, document_id: str) -> None:
        async with self._lock:
            replacement = {
                point_id: document
                for point_id, document in self._documents.items()
                if str(document.get("metadata", {}).get("document_id")) != str(document_id)
            }
            ordered_ids, index = self._build_index(replacement)
            self._documents = replacement
            self._ordered_ids = ordered_ids
            self._index = index
            for staged in self._staged_documents.values():
                stale_ids = [
                    point_id
                    for point_id, document in staged.items()
                    if str(document.get("metadata", {}).get("document_id"))
                    == str(document_id)
                ]
                for point_id in stale_ids:
                    staged.pop(point_id, None)

    async def ids_by_document(self, document_id: str) -> List[str]:
        async with self._lock:
            return [
                point_id
                for point_id, document in self._documents.items()
                if str(document.get("metadata", {}).get("document_id")) == str(document_id)
            ]

    async def ids_by_artifact_version(
        self, project_id: str, artifact_version_id: str
    ) -> List[str]:
        async with self._lock:
            return [
                point_id
                for point_id, document in self._documents.items()
                if str(document.get("metadata", {}).get("project_id")) == str(project_id)
                and str(document.get("metadata", {}).get("artifact_version_id"))
                == str(artifact_version_id)
                and not document.get("metadata", {}).get("document_id")
            ]

    async def list_artifact_version_points(
        self, project_id: str, artifact_version_id: str
    ) -> List[Dict]:
        async with self._lock:
            return [
                {
                    "id": point_id,
                    "metadata": dict(document.get("metadata", {})),
                }
                for point_id, document in self._documents.items()
                if str(document.get("metadata", {}).get("project_id")) == str(project_id)
                and str(document.get("metadata", {}).get("artifact_version_id"))
                == str(artifact_version_id)
                and not document.get("metadata", {}).get("document_id")
            ]

    async def delete_ids(self, point_ids: List[str]) -> None:
        if not point_ids:
            return
        remove = set(map(str, point_ids))
        async with self._lock:
            replacement = {
                point_id: document
                for point_id, document in self._documents.items()
                if point_id not in remove
            }
            ordered_ids, index = self._build_index(replacement)
            self._documents = replacement
            self._ordered_ids = ordered_ids
            self._index = index
            for staged in self._staged_documents.values():
                for point_id in remove:
                    staged.pop(point_id, None)

    @staticmethod
    def _can_access(
        metadata: Dict,
        requester_id: Optional[str],
        is_admin: bool,
        document_ids: Optional[List[str]] = None,
        metadata_filters: Optional[Dict] = None,
    ) -> bool:
        if is_admin:
            return True
        visibility = metadata.get("visibility")
        if visibility == "public":
            return True
        if visibility == "project":
            project_scope = (metadata_filters or {}).get("project_id")
            project_scopes = (
                project_scope if isinstance(project_scope, list) else [project_scope]
            )
            if any(
                value is not None
                and str(value) == str(metadata.get("project_id") or "")
                for value in project_scopes
            ):
                return True
            if bool(document_ids) and str(metadata.get("document_id") or "") in set(
                map(str, document_ids)
            ):
                return True
        owner_id = metadata.get("owner_id") or metadata.get("creator_id")
        return bool(requester_id) and (
            str(owner_id or "") == str(requester_id)
            or str(requester_id) in {str(value) for value in metadata.get("shared_with", [])}
        )

    @staticmethod
    def _matches_filters(metadata: Dict, metadata_filters: Optional[Dict]) -> bool:
        for key, expected in (metadata_filters or {}).items():
            if expected is None:
                continue
            actual = metadata.get(key)
            if isinstance(expected, list):
                actual_values = actual if isinstance(actual, list) else [actual]
                if not set(map(str, expected)).intersection(map(str, actual_values)):
                    return False
            elif isinstance(actual, list):
                if str(expected) not in set(map(str, actual)):
                    return False
            elif str(actual) != str(expected):
                return False
        return True

    async def search(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        limit: int = 20,
        requester_id: Optional[str] = None,
        is_admin: bool = False,
        metadata_filters: Optional[Dict] = None,
    ) -> List[Dict]:
        query_tokens = self._tokenize(query)
        if not query_tokens or limit < 1:
            return []

        async with self._lock:
            if self._index is None:
                return []
            index = self._index
            ordered_ids = list(self._ordered_ids)
            snapshot = dict(self._documents)
        scores = await asyncio.to_thread(index.get_scores, query_tokens)

        allowed_document_ids = set(map(str, document_ids or []))
        candidates = []
        for point_id, score in zip(ordered_ids, scores):
            document = snapshot[point_id]
            metadata = document.get("metadata", {})
            if not set(query_tokens).intersection(self._tokenize(document["text"])):
                continue
            if (
                allowed_document_ids
                and str(metadata.get("document_id")) not in allowed_document_ids
            ):
                continue
            if not self._can_access(
                metadata,
                requester_id,
                is_admin,
                document_ids=document_ids,
                metadata_filters=metadata_filters,
            ):
                continue
            if not self._matches_filters(metadata, metadata_filters):
                continue
            candidates.append({**document, "score": float(score), "bm25_score": float(score)})

        candidates.sort(key=lambda item: item["bm25_score"], reverse=True)
        return candidates[:limit]


bm25_store = BM25Store()
