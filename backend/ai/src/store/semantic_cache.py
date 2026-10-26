import math
import time
from typing import Any

from loguru import logger


class SemanticCache:
    def __init__(self):
        self.similarity_minimum = 0.9
        self.ttl_seconds = 86400
        self.maximum_entries = 512
        self._entries: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _remove_expired(self, now: float):
        expired = [
            key
            for key, entry in self._entries.items()
            if now - entry["stored_at"] >= self.ttl_seconds
        ]
        for key in expired:
            self._entries.pop(key, None)

    def _make_room(self):
        while len(self._entries) >= self.maximum_entries:
            oldest_key = min(self._entries, key=lambda key: self._entries[key]["stored_at"])
            self._entries.pop(oldest_key, None)

    async def get(self, query_text: str, query_vector: list[float] | None = None) -> str | None:
        if not query_text:
            return None

        self._remove_expired(time.monotonic())
        if query_vector:
            best_score = 0.0
            best_response = None
            for item in self._entries.values():
                cached_vec = item.get("vector")
                if cached_vec:
                    score = self._cosine_similarity(query_vector, cached_vec)
                    if score > best_score:
                        best_score = score
                        best_response = item.get("response")

            if best_score >= self.similarity_minimum and best_response:
                logger.info("Semantic cache hit with similarity score {:.4f}", best_score)
                return best_response

        for item in self._entries.values():
            if item.get("query") == query_text:
                logger.info("Exact semantic cache hit")
                return item.get("response")

        return None

    async def set(
        self,
        query_text: str,
        response_text: str,
        query_vector: list[float] | None = None,
    ):
        if not query_text or not response_text:
            return

        now = time.monotonic()
        self._remove_expired(now)
        if query_text not in self._entries:
            self._make_room()
        self._entries[query_text] = {
            "query": query_text,
            "response": response_text,
            "vector": query_vector,
            "stored_at": now,
        }
        logger.info("Saved query and response to semantic cache")


semantic_cache = SemanticCache()
