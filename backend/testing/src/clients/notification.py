import httpx
import logging

from src.core.configuration import settings

logger = logging.getLogger(__name__)


class NotificationClient:
    async def send(self, target_user_id, title, body, notification_type, idempotency_key):
        if not settings.NOTIFICATION_URL:
            return None
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{settings.NOTIFICATION_URL.rstrip('/')}/thong-bao/gui-di",
                json={
                    "target_user_id": target_user_id,
                    "title": title,
                    "body": body,
                    "type": notification_type,
                    "idempotency_key": idempotency_key,
                },
                headers={"X-Internal-Token": settings.SECRET_KEY},
            )
        response.raise_for_status()
        return response.json()

    async def notify_watchers(self, event):
        if not event.get("project_id"):
            return
        kind = {
            "requirement": "requirement",
            "requirementversion": "requirement",
            "testcase": "test_case",
            "testcaseversion": "test_case",
            "testrun": "test_run",
            "testrunexecution": "test_run",
            "defect": "defect",
            "testresult": "test_run",
        }.get(str(event.get("entity_type", "")).replace("_", "").lower())
        if not kind:
            return
        from src.core.database import database

        artifact_id = event["entity_id"]
        entity_type = str(event.get("entity_type", "")).replace("_", "").lower()
        if entity_type == "requirementversion":
            version = await database.value.requirement_versions.find_one(
                {"_id": artifact_id}, {"requirement_id": 1}
            )
            artifact_id = (version or {}).get("requirement_id")
        elif entity_type == "testcaseversion":
            version = await database.value.test_case_versions.find_one(
                {"_id": artifact_id}, {"test_case_id": 1}
            )
            artifact_id = (version or {}).get("test_case_id")
        elif entity_type == "testresult":
            result = await database.value.test_results.find_one(
                {"_id": artifact_id}, {"test_run_id": 1}
            )
            artifact_id = (result or {}).get("test_run_id")
        if not artifact_id:
            return

        watchers = await database.value.notification_subscriptions.find(
            {
                "project_id": event["project_id"],
                "artifact_type": kind,
                "artifact_id": artifact_id,
            },
            {"user_id": 1},
        ).to_list(1000)
        recipients = sorted(
            {
                watcher["user_id"]
                for watcher in watchers
                if watcher.get("user_id") and watcher["user_id"] != event.get("actor_id")
            }
        )
        if not recipients:
            return
        preferences = await database.value.project_notification_preferences.find(
            {"project_id": event["project_id"], "user_id": {"$in": recipients}},
            {"user_id": 1, "channels": 1, "muted_events": 1, "digest_frequency": 1},
        ).to_list(len(recipients))
        preferences_by_user = {item["user_id"]: item for item in preferences}
        labels = {
            "requirement": "yêu cầu",
            "test_case": "ca kiểm thử",
            "test_run": "lần chạy kiểm thử",
            "defect": "lỗi",
        }
        action_labels = {
            "created": "được tạo",
            "updated": "được cập nhật",
            "deleted": "được xóa",
            "approved": "được phê duyệt",
            "submitted": "được gửi rà soát",
            "archived": "được lưu trữ",
        }
        action = str(event.get("action", "")).lower()
        verb = next((label for key, label in action_labels.items() if key in action), "có thay đổi")
        title = f"Cập nhật {labels[kind]}"
        body = f"Một {labels[kind]} bạn đang theo dõi {verb} trong dự án"
        for user_id in recipients:
            preference = preferences_by_user.get(user_id) or {}
            if preference.get("digest_frequency") == "off":
                continue
            if "in_app" not in preference.get("channels", ["in_app"]):
                continue
            if action in preference.get("muted_events", []):
                continue
            try:
                await self.send(
                    user_id,
                    title,
                    body,
                    "PROJECT_ACTIVITY",
                    f"project-activity:{event['_id']}:{user_id}",
                )
            except Exception:
                logger.exception(
                    "Failed to dispatch project activity notification for audit event %s",
                    event.get("_id"),
                )


notification_client = NotificationClient()
