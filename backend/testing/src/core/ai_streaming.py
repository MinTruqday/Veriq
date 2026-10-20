import asyncio
import json

from src.core.ai_automation import stream_sink


class AIStreamingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers") or [])
        accepts_stream = b"text/event-stream" in headers.get(b"accept", b"")
        if scope.get("type") != "http" or scope.get("method") != "POST" or not accepts_stream:
            await self.app(scope, receive, send)
            return

        queue = asyncio.Queue()
        response_status = 500
        response_body = bytearray()

        async def emit(event):
            await queue.put(event if isinstance(event, dict) else {"type": "delta", "delta": event})

        async def capture(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))

        async def run():
            token = stream_sink.set(emit)
            try:
                await self.app(scope, receive, capture)
            except Exception as error:
                code = type(error).__name__
                await queue.put(
                    {
                        "type": "error",
                        "code": code,
                        "status": 500,
                        "data": {"error": {"code": code, "message": code}},
                    }
                )
            finally:
                stream_sink.reset(token)
                await queue.put(None)

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/event-stream; charset=utf-8"),
                    (b"cache-control", b"no-cache"),
                    (b"x-accel-buffering", b"no"),
                ],
            }
        )
        task = asyncio.create_task(run())
        while True:
            event = await queue.get()
            if event is None:
                break
            payload = json.dumps(event, ensure_ascii=False).encode()
            await send(
                {
                    "type": "http.response.body",
                    "body": b"data: " + payload + b"\n\n",
                    "more_body": True,
                }
            )
        if response_body:
            try:
                body = json.loads(response_body)
            except (TypeError, ValueError, json.JSONDecodeError):
                body = {"error": {"code": "AI_STREAM_RESPONSE_INVALID"}}
            event_type = "result" if response_status < 400 else "error"
            event = {"type": event_type, "data": body, "status": response_status}
            payload = json.dumps(event, ensure_ascii=False).encode()
            await send(
                {
                    "type": "http.response.body",
                    "body": b"data: " + payload + b"\n\n",
                    "more_body": True,
                }
            )
        await task
        await send({"type": "http.response.body", "body": b"", "more_body": False})
