import asyncio
import json
from types import SimpleNamespace
from typing import Any, AsyncIterator

import httpx
from loguru import logger

from src.core.infrastructure.configuration import settings


class ModelProviderUnavailable(RuntimeError):
    pass


def _response(
    content: str, prompt_tokens: int = 0, completion_tokens: int = 0, model_used: str = ""
):
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    message = SimpleNamespace(content=content)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)], usage=usage, model=model_used
    )


class HostedModelClient:
    def __init__(self):
        self._runtime_status = "unverified"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.HF_TOKEN}", "Content-Type": "application/json"}

    def _can_retry(self, error: Exception) -> bool:
        if isinstance(error, httpx.TransportError):
            return True
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code == 429 or error.response.status_code >= 500
        return False

    def _payload(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": response_schema,
                },
            }
        return payload

    async def _completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        response_schema: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ):
        payload = self._payload(model, messages, max_tokens, temperature, response_schema)
        maximum_attempts = 3
        for attempt in range(maximum_attempts):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout_seconds or settings.MODEL_TIMEOUT_SECONDS
                ) as client:
                    response = await client.post(
                        settings.PRIMARY_MODEL_URL, headers=self._headers(), json=payload
                    )
                response.raise_for_status()
                break
            except Exception as provider_error:
                if attempt == maximum_attempts - 1 or not self._can_retry(provider_error):
                    raise
                logger.warning(
                    "Hosted model request retry attempt={} error_type={}",
                    attempt + 1,
                    type(provider_error).__name__,
                )
                await asyncio.sleep(2**attempt)
        body = response.json()
        choices = body.get("choices") or []
        content = str(choices[0].get("message", {}).get("content", "")).strip() if choices else ""
        if not content:
            self._runtime_status = "unavailable"
            raise ModelProviderUnavailable("hosted_model_empty_response")
        self._runtime_status = "ready"
        usage = body.get("usage") or {}
        return _response(
            content,
            int(usage.get("prompt_tokens", 0) or 0),
            int(usage.get("completion_tokens", 0) or 0),
            str(body.get("model") or model),
        )

    def active_model(self) -> str:
        return settings.LLM_MODEL

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        stream: bool = False,
        response_schema: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        **_: Any,
    ):
        effective_model = model or settings.LLM_MODEL
        if stream:
            return self._stream(effective_model, messages, max_tokens, temperature, response_schema)
        try:
            return await self._completion(
                effective_model,
                messages,
                max_tokens,
                temperature,
                response_schema,
                timeout_seconds,
            )
        except Exception as provider_error:
            self._runtime_status = "unavailable"
            logger.warning(
                "Configured model failed error_type={} model={}",
                type(provider_error).__name__,
                effective_model,
            )
            raise ModelProviderUnavailable("configured_model_unavailable") from provider_error

    async def warm_primary(self) -> bool:
        try:
            await self._completion(
                settings.LLM_MODEL, [{"role": "user", "content": "Reply OK"}], 4, 0
            )
            return True
        except Exception:
            self._runtime_status = "unavailable"
            return False

    async def _stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        response_schema: dict[str, Any] | None = None,
    ) -> AsyncIterator[Any]:
        payload = self._payload(model, messages, max_tokens, temperature, response_schema)
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
        emitted = False
        prompt_tokens = 0
        completion_tokens = 0
        maximum_attempts = 3
        for attempt in range(maximum_attempts):
            try:
                async with httpx.AsyncClient(timeout=settings.MODEL_TIMEOUT_SECONDS) as client:
                    async with client.stream(
                        "POST", settings.PRIMARY_MODEL_URL, headers=self._headers(), json=payload
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            value = line[6:]
                            if value == "[DONE]":
                                break
                            body = json.loads(value)
                            usage = body.get("usage") or {}
                            prompt_tokens = int(
                                usage.get("prompt_tokens", prompt_tokens) or prompt_tokens
                            )
                            completion_tokens = int(
                                usage.get("completion_tokens", completion_tokens)
                                or completion_tokens
                            )
                            choices = body.get("choices") or []
                            token = (
                                str(choices[0].get("delta", {}).get("content", ""))
                                if choices
                                else ""
                            )
                            if token:
                                emitted = True
                                delta = SimpleNamespace(content=token)
                                yield SimpleNamespace(choices=[SimpleNamespace(delta=delta)])
                break
            except Exception as provider_error:
                if (
                    emitted
                    or attempt == maximum_attempts - 1
                    or not self._can_retry(provider_error)
                ):
                    self._runtime_status = "unavailable"
                    raise ModelProviderUnavailable(
                        "configured_model_unavailable"
                    ) from provider_error
                logger.warning(
                    "Hosted model stream retry attempt={} error_type={}",
                    attempt + 1,
                    type(provider_error).__name__,
                )
                await asyncio.sleep(2**attempt)
        if not emitted:
            self._runtime_status = "unavailable"
            raise ModelProviderUnavailable("hosted_model_empty_response")
        from src.services.token_accounting import record_usage

        record_usage(
            _response("", prompt_tokens, completion_tokens, model),
            sum(len(str(message.get("content", ""))) for message in messages),
            0,
        )
        self._runtime_status = "ready"

    async def readiness(self) -> dict[str, str]:
        checks = {"model": "unavailable"}
        try:
            async with httpx.AsyncClient(timeout=settings.MODEL_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    settings.PRIMARY_MODEL_HEALTH_URL, headers=self._headers()
                )
            response.raise_for_status()
            target = settings.LLM_MODEL.lower()
            available = any(
                str(item.get("id", "")).lower() == target
                for item in response.json().get("data", [])
            )
            if available:
                self._runtime_status = "ready"
                checks["model"] = "ready"
        except Exception:
            self._runtime_status = "unavailable"
        return checks


model_client = HostedModelClient()


class HostedAuxiliaryClient:
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.HF_TOKEN}", "Content-Type": "application/json"}

    def _endpoint(self, model: str) -> str:
        return f"{settings.HF_INFERENCE_URL.rstrip('/')}/{model}"

    @staticmethod
    def _can_retry(error: Exception) -> bool:
        if isinstance(error, httpx.TransportError):
            return True
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code == 429 or error.response.status_code >= 500
        return False

    async def _post(self, model: str, payload: dict[str, Any]) -> Any:
        maximum_attempts = 3
        for attempt in range(maximum_attempts):
            try:
                async with httpx.AsyncClient(timeout=settings.MODEL_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        self._endpoint(model), headers=self._headers(), json=payload
                    )
                response.raise_for_status()
                body = response.json()
                if isinstance(body, dict) and body.get("error"):
                    raise ModelProviderUnavailable("hosted_auxiliary_model_error")
                return body
            except Exception as provider_error:
                if attempt == maximum_attempts - 1 or not self._can_retry(provider_error):
                    raise ModelProviderUnavailable(
                        "hosted_auxiliary_model_unavailable"
                    ) from provider_error
                logger.warning(
                    "Hosted auxiliary request retry attempt={} error_type={} model={}",
                    attempt + 1,
                    type(provider_error).__name__,
                    model,
                )
                await asyncio.sleep(2**attempt)
        raise ModelProviderUnavailable("hosted_auxiliary_model_unavailable")

    async def embed(self, texts: list[str], prompt_name: str) -> list[list[float]]:
        if not texts:
            return []
        prefix = "query" if prompt_name == "query" else "passage"
        body = await self._post(
            settings.EMBEDDING_MODEL,
            {
                "inputs": [f"{prefix}: {text}" for text in texts],
                "normalize": True,
                "truncate": True,
            },
        )
        if not isinstance(body, list) or len(body) != len(texts):
            raise ModelProviderUnavailable("hosted_embedding_shape_invalid")
        embeddings = [[float(value) for value in vector] for vector in body]
        if any(len(vector) != 1024 for vector in embeddings):
            raise ModelProviderUnavailable("hosted_embedding_dimension_invalid")
        return embeddings

    async def rerank(self, pairs: list[list[str]]) -> list[float]:
        if not pairs:
            return []
        body = await self._post(
            settings.RERANKER_MODEL,
            {
                "inputs": [
                    {"text": str(pair[0])[:4000], "text_pair": str(pair[1])[:8000]}
                    for pair in pairs
                ]
            },
        )
        entries = body[0] if isinstance(body, list) and len(body) == 1 else body
        if not isinstance(entries, list) or len(entries) != len(pairs):
            raise ModelProviderUnavailable("hosted_reranker_shape_invalid")
        scores = []
        for entry in entries:
            candidates = entry if isinstance(entry, list) else [entry]
            values = [
                float(candidate.get("score", 0.0))
                for candidate in candidates
                if isinstance(candidate, dict)
            ]
            if not values:
                raise ModelProviderUnavailable("hosted_reranker_score_invalid")
            scores.append(max(values))
        return scores

    async def entailment(self, premise: str, hypothesis: str) -> float:
        body = await self._post(
            settings.NLI_MODEL_NAME,
            {
                "inputs": premise[:8000],
                "parameters": {"candidate_labels": [hypothesis[:4000]], "multi_label": True},
            },
        )
        if not isinstance(body, list) or not body or not isinstance(body[0], dict):
            raise ModelProviderUnavailable("hosted_nli_shape_invalid")
        return float(body[0].get("score", 0.0))


auxiliary_client = HostedAuxiliaryClient()
