import unittest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx

from src.utils.model_provider import HostedModelClient, ModelProviderUnavailable


class _Response:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {
            "choices": [{"message": {"content": "grounded response"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://model.invalid")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("provider failure", request=request, response=response)

    def json(self):
        return self._body


class _AsyncClientContext:
    def __init__(self):
        self.stream_response = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, *args, **kwargs):
        return await self._post(*args, **kwargs)

    @asynccontextmanager
    async def stream(self, *args, **kwargs):
        if isinstance(self.stream_response, Exception):
            raise self.stream_response
        yield self.stream_response


class _StreamResponse:
    def __init__(self, status_code=200, lines=()):
        self.status_code = status_code
        self.lines = list(lines)

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://model.invalid")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("provider failure", request=request, response=response)

    async def aiter_lines(self):
        for line in self.lines:
            if isinstance(line, Exception):
                raise line
            yield line


def _client(post_responses=(), stream_responses=()):
    post_values = iter(post_responses)
    stream_values = iter(stream_responses)
    post_calls = []
    stream_calls = []

    def create_client(*_args, **_kwargs):
        context = _AsyncClientContext()
        async def post(*args, **kwargs):
            post_calls.append((args, kwargs))
            value = next(post_values)
            if isinstance(value, Exception):
                raise value
            return value
        context._post = post
        context.stream_response = next(stream_values, None)
        stream_calls.append(context)
        return context

    return create_client, post_calls, stream_calls


class HostedModelRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retryable_primary_failure_uses_configured_fallback(self):
        request = httpx.Request("POST", "https://model.invalid")
        unavailable = httpx.HTTPStatusError(
            "provider unavailable",
            request=request,
            response=httpx.Response(503, request=request),
        )
        create_client, post_calls, _ = _client(
            [unavailable, unavailable, unavailable, _Response()]
        )
        client = HostedModelClient()

        with (
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_URL", "https://backup.invalid"),
            patch("src.utils.model_provider.settings.FALLBACK_LLM_MODEL", "backup-model"),
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_TOKEN", "backup-token"),
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client),
            patch("src.utils.model_provider.asyncio.sleep", new=AsyncMock()),
        ):
            response = await client.chat_completion(
                [{"role": "user", "content": "hello"}], response_schema={"type": "object"}
            )

        self.assertEqual(response.choices[0].message.content, "grounded response")
        self.assertEqual(response.model, "backup-model")
        self.assertEqual(len(post_calls), 4)
        self.assertEqual(post_calls[-1][0][0], "https://backup.invalid")
        self.assertEqual(post_calls[-1][1]["headers"]["Authorization"], "Bearer backup-token")
        self.assertEqual(post_calls[-1][1]["json"]["response_format"]["type"], "json_schema")
        self.assertEqual(client._runtime_status, "ready")

    async def test_requested_non_default_model_does_not_use_fallback(self):
        request = httpx.Request("POST", "https://model.invalid")
        unavailable = httpx.HTTPStatusError(
            "provider unavailable",
            request=request,
            response=httpx.Response(503, request=request),
        )
        create_client, post_calls, _ = _client([unavailable, unavailable, unavailable])
        client = HostedModelClient()

        with (
            patch("src.utils.model_provider.settings.LLM_MODEL", "default-model"),
            patch(
                "src.utils.model_provider.settings.PRIMARY_MODEL_URL",
                "https://model.invalid",
            ),
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_URL", "https://backup.invalid"),
            patch("src.utils.model_provider.settings.FALLBACK_LLM_MODEL", "backup-model"),
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client),
            patch("src.utils.model_provider.asyncio.sleep", new=AsyncMock()),
        ):
            with self.assertRaises(ModelProviderUnavailable):
                await client.chat_completion(
                    [{"role": "user", "content": "hello"}], model="explicit-model"
                )

        self.assertEqual(len(post_calls), 3)
        self.assertTrue(all(call[0][0] == "https://model.invalid" for call in post_calls))

    async def test_warmup_uses_fallback_when_primary_is_retryably_unavailable(self):
        request = httpx.Request("POST", "https://model.invalid")
        unavailable = httpx.HTTPStatusError(
            "provider unavailable",
            request=request,
            response=httpx.Response(503, request=request),
        )
        create_client, post_calls, _ = _client(
            [unavailable, unavailable, unavailable, _Response()]
        )
        client = HostedModelClient()

        with (
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_URL", "https://backup.invalid"),
            patch("src.utils.model_provider.settings.FALLBACK_LLM_MODEL", "backup-model"),
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client),
            patch("src.utils.model_provider.asyncio.sleep", new=AsyncMock()),
        ):
            ready = await client.warm_primary()

        self.assertTrue(ready)
        self.assertEqual(post_calls[-1][0][0], "https://backup.invalid")

    async def test_stream_uses_fallback_only_before_emitting_output(self):
        request = httpx.Request("POST", "https://model.invalid")
        unavailable = httpx.ConnectError("provider unavailable", request=request)
        response = _StreamResponse(
            lines=[
                'data: {"choices":[{"delta":{"content":"fallback"}}]}',
                "data: [DONE]",
            ]
        )
        create_client, _, stream_calls = _client(
            stream_responses=[unavailable, unavailable, unavailable, response]
        )
        client = HostedModelClient()

        with (
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_URL", "https://backup.invalid"),
            patch("src.utils.model_provider.settings.FALLBACK_LLM_MODEL", "backup-model"),
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client),
            patch("src.utils.model_provider.asyncio.sleep", new=AsyncMock()),
        ):
            stream = await client.chat_completion(
                [{"role": "user", "content": "hello"}], stream=True
            )
            chunks = [chunk async for chunk in stream]

        self.assertEqual(
            [chunk.choices[0].delta.content for chunk in chunks], ["fallback"]
        )
        self.assertEqual(len(stream_calls), 4)

    async def test_readiness_accepts_available_fallback_model(self):
        class _HealthResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"id": "backup-model"}]}

        class _HealthClient(_AsyncClientContext):
            async def get(self, url, **_kwargs):
                if url == "https://primary.invalid/models":
                    raise httpx.ConnectError("primary offline")
                return _HealthResponse()

        client = HostedModelClient()
        with (
            patch("src.utils.model_provider.settings.PRIMARY_MODEL_HEALTH_URL", "https://primary.invalid/models"),
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_URL", "https://backup.invalid/chat"),
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_HEALTH_URL", "https://backup.invalid/models"),
            patch("src.utils.model_provider.settings.FALLBACK_LLM_MODEL", "backup-model"),
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=lambda **_kwargs: _HealthClient()),
        ):
            result = await client.readiness()

        self.assertEqual(result, {"model": "ready"})
        self.assertEqual(client._runtime_status, "ready")

    async def test_readiness_does_not_accept_fallback_after_primary_authorization_failure(self):
        class _HealthResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"id": "backup-model"}]}

        class _HealthClient(_AsyncClientContext):
            async def get(self, url, **_kwargs):
                if url == "https://primary.invalid/models":
                    request = httpx.Request("GET", url)
                    response = httpx.Response(401, request=request)
                    raise httpx.HTTPStatusError(
                        "denied", request=request, response=response
                    )
                return _HealthResponse()

        client = HostedModelClient()
        with (
            patch("src.utils.model_provider.settings.PRIMARY_MODEL_HEALTH_URL", "https://primary.invalid/models"),
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_URL", "https://backup.invalid/chat"),
            patch("src.utils.model_provider.settings.FALLBACK_MODEL_HEALTH_URL", "https://backup.invalid/models"),
            patch("src.utils.model_provider.settings.FALLBACK_LLM_MODEL", "backup-model"),
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=lambda **_kwargs: _HealthClient()),
        ):
            result = await client.readiness()

        self.assertEqual(result, {"model": "unavailable"})
        self.assertEqual(client._runtime_status, "unavailable")

    async def test_non_retryable_authorization_error_is_not_retried(self):
        request = httpx.Request("POST", "https://model.invalid")
        denied = httpx.HTTPStatusError(
            "unauthorized", request=request, response=httpx.Response(401, request=request)
        )
        create_client, post_calls, _ = _client([denied])
        client = HostedModelClient()

        with patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client):
            with self.assertRaises(ModelProviderUnavailable):
                await client.chat_completion([{"role": "user", "content": "hello"}])

        self.assertEqual(len(post_calls), 1)
        self.assertEqual(client._runtime_status, "unavailable")

    async def test_rate_limit_retries_then_returns_model_response(self):
        request = httpx.Request("POST", "https://model.invalid")
        limited = httpx.HTTPStatusError(
            "rate limited", request=request, response=httpx.Response(429, request=request)
        )
        create_client, post_calls, _ = _client([limited, _Response()])
        client = HostedModelClient()

        with (
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client),
            patch("src.utils.model_provider.asyncio.sleep", new=AsyncMock()),
        ):
            response = await client.chat_completion([{"role": "user", "content": "hello"}])

        self.assertEqual(response.choices[0].message.content, "grounded response")
        self.assertEqual(len(post_calls), 2)
        self.assertEqual(client._runtime_status, "ready")

    async def test_request_timeout_retries_then_returns_model_response(self):
        request = httpx.Request("POST", "https://model.invalid")
        timed_out = httpx.ReadTimeout("provider timed out", request=request)
        create_client, post_calls, _ = _client([timed_out, _Response()])
        client = HostedModelClient()

        with (
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client),
            patch("src.utils.model_provider.asyncio.sleep", new=AsyncMock()),
        ):
            response = await client.chat_completion([{"role": "user", "content": "hello"}])

        self.assertEqual(response.choices[0].message.content, "grounded response")
        self.assertEqual(len(post_calls), 2)
        self.assertEqual(client._runtime_status, "ready")

    async def test_stream_transport_failure_after_first_token_fails_closed(self):
        request = httpx.Request("POST", "https://model.invalid")
        transport_error = httpx.ReadError("connection dropped", request=request)
        response = _StreamResponse(
            lines=[
                'data: {"choices":[{"delta":{"content":"partial"}}]}',
                transport_error,
            ]
        )
        create_client, _, stream_calls = _client(stream_responses=[response, response])
        client = HostedModelClient()

        with (
            patch("src.utils.model_provider.httpx.AsyncClient", side_effect=create_client),
            patch("src.utils.model_provider.asyncio.sleep", new=AsyncMock()),
        ):
            stream = await client.chat_completion(
                [{"role": "user", "content": "hello"}], stream=True
            )
            chunks = []
            with self.assertRaises(ModelProviderUnavailable):
                async for chunk in stream:
                    chunks.append(chunk.choices[0].delta.content)

        self.assertEqual(chunks, ["partial"])
        self.assertEqual(len(stream_calls), 1)
        self.assertEqual(client._runtime_status, "unavailable")


if __name__ == "__main__":
    unittest.main()
