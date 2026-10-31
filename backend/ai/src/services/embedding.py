import hashlib
import json
from typing import List

import redis

from src.core.infrastructure.configuration import settings
from src.utils.model_provider import auxiliary_client


class EmbeddingService:
    def __init__(self):
        self._model_name = settings.EMBEDDING_MODEL
        self._dimensions = 1024
        self._batch_size = 8

        redis_url = settings.REDIS_URI
        try:
            self._cache = redis.from_url(redis_url, decode_responses=False)
            self._cache.ping()
        except Exception:
            self._cache = None

    async def initialize(self):
        return (await auxiliary_client.embed(["readiness"], "query"))[0]

    def _cache_key(self, text: str, prompt_name: str) -> str:
        return f"emb:hf:{self._model_name}:{prompt_name}:{hashlib.sha256(text.encode()).hexdigest()[:24]}"

    async def _embed_single(self, text: str, prompt_name: str) -> List[float]:
        if self._cache:
            cached = self._cache.get(self._cache_key(text, prompt_name))
            if cached:
                return json.loads(cached)

        embedding = (await auxiliary_client.embed([text], prompt_name))[0]

        if self._cache:
            self._cache.setex(self._cache_key(text, prompt_name), 86400 * 7, json.dumps(embedding))

        return embedding

    async def embed_query(self, query: str) -> List[float]:
        return await self._embed_single(query, "query")

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = [None] * len(texts)
        uncached_indices_by_text = {}
        uncached_texts = []

        for i, text in enumerate(texts):
            if self._cache:
                cached = self._cache.get(self._cache_key(text, "passage"))
                if cached:
                    all_embeddings[i] = json.loads(cached)
                    continue
            if text not in uncached_indices_by_text:
                uncached_indices_by_text[text] = []
                uncached_texts.append(text)
            uncached_indices_by_text[text].append(i)

        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), self._batch_size):
                batch = uncached_texts[batch_start : batch_start + self._batch_size]
                batch_embeddings = await auxiliary_client.embed(batch, "passage")

                for j, emb in enumerate(batch_embeddings):
                    text = batch[j]
                    for real_idx in uncached_indices_by_text[text]:
                        all_embeddings[real_idx] = emb
                    if self._cache:
                        self._cache.setex(
                            self._cache_key(text, "passage"), 86400 * 7, json.dumps(emb)
                        )

        return all_embeddings

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return await self._embed_batch(texts)


embedder = EmbeddingService()
