import unittest
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

from fastapi import HTTPException

from src.core.auth import get_current_user
from src.core.configuration import settings


class AIAutomationActiveRunAuthTests(unittest.IsolatedAsyncioTestCase):
    def claims(self):
        return {
            "uid": "ba-user",
            "email": "ba@example.test",
            "system_role": "USER",
            "ai_automation_run_id": "AUT-1",
            "ai_automation_worker_revision": 4,
            "ai_automation_source_document_ids": [],
        }

    def request(self):
        return SimpleNamespace(method="POST", state=SimpleNamespace())

    async def test_cancelled_run_identity_is_rejected_before_testing_route(self):
        with (
            patch("src.core.auth.jwt.decode", return_value=self.claims()),
            patch(
                "src.clients.ai_automation.automation_run_is_active",
                new=AsyncMock(return_value=False),
            ) as active,
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_current_user(
                    token="signed-token",
                    ai_automation_run_id="AUT-1",
                    x_internal_token=settings.SECRET_KEY,
                    request=self.request(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "AI_AUTOMATION_RUN_NOT_ACTIVE"
        )
        active.assert_awaited_once_with("AUT-1", 4)

    async def test_stale_worker_revision_is_rejected_even_when_run_is_active(self):
        with (
            patch("src.core.auth.jwt.decode", return_value=self.claims()),
            patch(
                "src.clients.ai_automation.automation_run_is_active",
                new=AsyncMock(return_value=False),
            ) as active,
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_current_user(
                    token="signed-token",
                    ai_automation_run_id="AUT-1",
                    x_internal_token=settings.SECRET_KEY,
                    request=self.request(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "AI_AUTOMATION_RUN_NOT_ACTIVE")
        active.assert_awaited_once_with("AUT-1", 4)

    async def test_active_run_identity_is_accepted(self):
        with (
            patch("src.core.auth.jwt.decode", return_value=self.claims()),
            patch(
                "src.clients.ai_automation.automation_run_is_active",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "src.repositories.ai_automation_access.ai_automation_access_repository.acquire",
                new=AsyncMock(return_value=True),
            ) as acquire,
        ):
            request = self.request()
            user = await get_current_user(
                token="signed-token",
                ai_automation_run_id="AUT-1",
                x_internal_token=settings.SECRET_KEY,
                request=request,
            )

        self.assertEqual(user._ai_automation_run_id, "AUT-1")
        self.assertEqual(request.state.ai_automation_leases[0][0], "run:AUT-1")
        acquire.assert_awaited_once_with("run:AUT-1", ANY)

    async def test_source_scoped_run_acquires_a_lease_for_each_source_document(self):
        claims = {**self.claims(), "ai_automation_source_document_ids": ["RDOC-1", "RDOC-2"]}
        with (
            patch("src.core.auth.jwt.decode", return_value=claims),
            patch(
                "src.clients.ai_automation.automation_run_is_active",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "src.repositories.ai_automation_access.ai_automation_access_repository.acquire",
                new=AsyncMock(return_value=True),
            ) as acquire,
        ):
            request = self.request()
            await get_current_user(
                token="signed-token",
                ai_automation_run_id="AUT-1",
                x_internal_token=settings.SECRET_KEY,
                request=request,
            )

        self.assertEqual(
            [scope for scope, _ in request.state.ai_automation_leases],
            ["run:AUT-1", "source:RDOC-1", "source:RDOC-2"],
        )
        self.assertEqual(acquire.await_count, 3)

    async def test_source_fence_denial_releases_previously_acquired_run_lease(self):
        claims = {**self.claims(), "ai_automation_source_document_ids": ["RDOC-1"]}
        with (
            patch("src.core.auth.jwt.decode", return_value=claims),
            patch(
                "src.clients.ai_automation.automation_run_is_active",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "src.repositories.ai_automation_access.ai_automation_access_repository.acquire",
                new=AsyncMock(side_effect=[True, False]),
            ),
            patch(
                "src.repositories.ai_automation_access.ai_automation_access_repository.release",
                new=AsyncMock(),
            ) as release,
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_current_user(
                    token="signed-token",
                    ai_automation_run_id="AUT-1",
                    x_internal_token=settings.SECRET_KEY,
                    request=self.request(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        release.assert_awaited_once()

    async def test_revoked_access_lease_rejects_request_after_status_preflight(self):
        with (
            patch("src.core.auth.jwt.decode", return_value=self.claims()),
            patch(
                "src.clients.ai_automation.automation_run_is_active",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "src.repositories.ai_automation_access.ai_automation_access_repository.acquire",
                new=AsyncMock(return_value=False),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_current_user(
                    token="signed-token",
                    ai_automation_run_id="AUT-1",
                    x_internal_token=settings.SECRET_KEY,
                    request=self.request(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "AI_AUTOMATION_RUN_ACCESS_REVOKED"
        )

    async def test_unavailable_run_status_fails_closed(self):
        with (
            patch("src.core.auth.jwt.decode", return_value=self.claims()),
            patch(
                "src.clients.ai_automation.automation_run_is_active",
                new=AsyncMock(side_effect=RuntimeError("AI service unavailable")),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await get_current_user(
                    token="signed-token",
                    ai_automation_run_id="AUT-1",
                    x_internal_token=settings.SECRET_KEY,
                    request=self.request(),
                )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(
            raised.exception.detail["code"], "AI_AUTOMATION_STATUS_UNAVAILABLE"
        )


if __name__ == "__main__":
    unittest.main()
