from src.core.common import audit, get_project, now, optimistic_patch
from src.core.database import database


class ProjectProgressService:
    @staticmethod
    async def _require_project_editor(project_id, user):
        await get_project(project_id, user, "project.update")

    @staticmethod
    async def update_project_progress(project_id, payload, user):
        await ProjectProgressService._require_project_editor(project_id, user)

        async def operation(session):
            current = await database.value.projects.find_one(
                {"_id": project_id, "revision": payload.expected_revision},
                session=session,
            )
            if not current:
                return await optimistic_patch(
                    "projects",
                    project_id,
                    project_id,
                    payload.expected_revision,
                    {"project_completion_percent": payload.project_completion_percent},
                    session=session,
                )
            updated = await optimistic_patch(
                "projects",
                project_id,
                project_id,
                payload.expected_revision,
                {"project_completion_percent": payload.project_completion_percent},
                session=session,
            )
            await audit(
                user.id,
                "project_completion_percent_updated",
                "Project",
                project_id,
                project_id,
                {
                    "previous_value": int(current.get("project_completion_percent", 0)),
                    "new_value": payload.project_completion_percent,
                    "note": payload.note,
                },
                session=session,
            )
            return updated

        client = database.client
        if client is None:
            raise RuntimeError("Cơ sở dữ liệu chưa sẵn sàng")
        async with await client.start_session() as session:
            return await session.with_transaction(operation)
