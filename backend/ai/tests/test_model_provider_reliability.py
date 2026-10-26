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
