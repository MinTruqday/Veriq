import unittest
from unittest.mock import patch

from src.clients import project_knowledge


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, *_args, **_kwargs):
        return self.response


class ProjectKnowledgeIndexStatusTests(unittest.IsolatedAsyncioTestCase):
    async def call_index(self, status):
        response = FakeResponse({"status": status})
        with patch.object(
            project_knowledge.httpx,
            "AsyncClient",
            return_value=FakeAsyncClient(response),
        ):
            return await project_knowledge.index_artifact(
                "project-1",
                "requirement_version",
                "requirement-1",
                "requirement-version-1",
                "Login requirement",
                "A person can sign in.",
                "BASELINED",
                "APPROVED_SOURCE",
            )

    async def test_indexed_status_is_reported_as_success(self):
        self.assertTrue(await self.call_index("indexed"))

    async def test_degraded_status_is_not_reported_as_success(self):
        self.assertFalse(await self.call_index("degraded"))

    async def test_missing_status_fails_closed(self):
        response = FakeResponse({"chunks_count": 3})
        with patch.object(
            project_knowledge.httpx,
            "AsyncClient",
            return_value=FakeAsyncClient(response),
        ):
            indexed = await project_knowledge.index_artifact(
                "project-1",
                "requirement_version",
                "requirement-1",
                "requirement-version-1",
                "Login requirement",
                "A person can sign in.",
                "BASELINED",
                "APPROVED_SOURCE",
            )

        self.assertFalse(indexed)


if __name__ == "__main__":
    unittest.main()
