from pymongo import ReturnDocument

from src.core.database import database


class ReportingRepository:
    def collection(self, name):
        if name not in {"work_reports", "report_templates", "report_settings", "report_comments", "report_deliveries", "report_exports", "report_schedules", "report_schedule_runs", "report_actions", "report_template_previews", "report_ai_drafts", "report_notifications", "report_assets"}:
            raise ValueError("REPORT_COLLECTION_INVALID")
        return database.value[name]

    async def find(self, name, query, session=None):
        return await self.collection(name).find_one(query, session=session)

    async def list(self, name, query, limit=200, sort="updated_at"):
        return await self.collection(name).find(query).sort(sort, -1).limit(limit).to_list(limit)

    async def insert(self, name, value, session=None):
        await self.collection(name).insert_one(value, session=session)
        return value

    async def change(self, name, query, update, session=None):
        return await self.collection(name).find_one_and_update(query, update, return_document=ReturnDocument.AFTER, session=session)

    async def initialize(self):
        indexes = {
            "work_reports": [("project_id", "created_by", "idempotency_key"), ("series_id", "version")],
            "report_templates": [("project_id", "template_id", "version")],
            "report_settings": [("project_id",)],
            "report_comments": [("report_id", "created_by", "idempotency_key")],
            "report_deliveries": [("report_id", "user_id")],
            "report_exports": [("report_id", "revision", "format", "renderer_version")],
            "report_schedules": [("project_id", "idempotency_key")],
            "report_schedule_runs": [("schedule_id", "occurrence_index")],
            "report_actions": [("report_id", "actor_id", "idempotency_key")],
            "report_ai_drafts": [("report_id", "requested_by", "idempotency_key")],
            "report_notifications": [("user_id", "event_key")],
            "report_assets": [("project_id", "created_by", "sha256")],
        }
        await self.collection("report_exports").update_many({"renderer_version": {"$exists": False}}, {"$set": {"renderer_version": "legacy-report-export-v1"}})
        for name, groups in indexes.items():
            for fields in groups:
                await self.collection(name).create_index([(field, 1) for field in fields], unique=True)
        for index in await self.collection("report_exports").list_indexes().to_list(100):
            if dict(index["key"]) == {"report_id": 1, "revision": 1, "format": 1}:
                await self.collection("report_exports").drop_index(index["name"])
        for name in ("work_reports", "report_comments", "report_deliveries", "report_exports", "report_schedules"):
            await self.collection(name).create_index([("project_id", 1), ("updated_at", -1)])
        await self.collection("report_schedules").create_index([("enabled", 1), ("next_run_at", 1)])
        await self.collection("report_exports").create_index([("status", 1), ("lease_until", 1)])
        await self.collection("report_deliveries").create_index([("user_id", 1), ("status", 1)])


reporting_repository = ReportingRepository()
