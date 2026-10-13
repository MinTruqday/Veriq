from pymongo import ReturnDocument

from src.core.database import database


class ProjectRepository:
    @property
    def projects(self):
        return database.value.projects

    @property
    def members(self):
        return database.value.project_members

    @property
    def grants(self):
        return database.value.break_glass_grants

    @property
    def tasks(self):
        return database.value.project_tasks

    async def create_with_creator(self, project, membership):
        await self.projects.insert_one(project)
        try:
            await self.members.insert_one(membership)
        except Exception:
            await self.projects.delete_one({"_id": project["_id"]})
            raise

    async def list_active_memberships(self, user_id, active_status, limit=5000):
        return await self.members.find(
            {"user_id": user_id, "status": active_status}
        ).to_list(limit)

    async def list_active_grants(self, user_id, active_status, active_after, limit=5000):
        return await self.grants.find(
            {
                "user_id": user_id,
                "status": active_status,
                "expires_at": {"$gt": active_after},
            }
        ).to_list(limit)

    async def list_projects(self, query, limit):
        return await self.projects.find(query).sort("updated_at", -1).to_list(limit)

    async def list_invitations(self, user_id, invited_status, limit=500):
        return await self.members.find(
            {"user_id": user_id, "status": invited_status}
        ).sort("invited_at", -1).to_list(limit)

    async def list_project_summaries(self, project_ids):
        if not project_ids:
            return []
        return await self.projects.find(
            {"_id": {"$in": list(project_ids)}},
            {"key": 1, "name": 1, "description": 1, "status": 1},
        ).to_list(len(project_ids))

    async def find_member(self, project_id, user_id, status=None, projection=None):
        query = {"project_id": project_id, "user_id": user_id}
        if status:
            query["status"] = status
        return await self.members.find_one(query, projection)

    async def find_active_grant(self, project_id, user_id, active_status, active_after):
        return await self.grants.find_one(
            {
                "project_id": project_id,
                "user_id": user_id,
                "status": active_status,
                "expires_at": {"$gt": active_after},
            }
        )

    async def list_members(self, project_id, limit=5000):
        return await self.members.find({"project_id": project_id}).sort(
            "created_at", 1
        ).to_list(limit)

    async def add_member(self, membership):
        await self.members.insert_one(membership)
        return membership

    async def transition_invitation(self, invitation_id, user_id, current_status, changes):
        return await self.members.find_one_and_update(
            {"_id": invitation_id, "user_id": user_id, "status": current_status},
            {"$set": changes, "$inc": {"membership_revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def transition_membership(self, project_id, user_id, current_status, changes):
        return await self.members.find_one_and_update(
            {"project_id": project_id, "user_id": user_id, "status": current_status},
            {"$set": changes, "$inc": {"membership_revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def update_invitation(
        self, project_id, user_id, invited_status, changes, increments=None
    ):
        return await self.members.find_one_and_update(
            {"project_id": project_id, "user_id": user_id, "status": invited_status},
            {
                "$set": changes,
                "$inc": {"membership_revision": 1, **(increments or {})},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def count_members_by_role_status(self, project_id, role, status):
        return await self.members.count_documents(
            {"project_id": project_id, "project_role": role, "status": status}
        )

    async def update_member(self, project_id, user_id, revision, changes):
        return await self.members.find_one_and_update(
            {
                "project_id": project_id,
                "user_id": user_id,
                "membership_revision": revision,
            },
            {"$set": changes, "$inc": {"membership_revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def restore_member(self, membership, previous, updated_at):
        return await self.members.update_one(
            {
                "_id": membership["_id"],
                "project_id": membership["project_id"],
                "membership_revision": membership["membership_revision"],
            },
            {
                "$set": {
                    "project_role": previous["project_role"],
                    "status": previous["status"],
                    "updated_at": updated_at,
                },
                "$inc": {"membership_revision": 1},
            },
        )

    async def remove_member(self, project_id, user_id):
        return await self.members.delete_one(
            {"project_id": project_id, "user_id": user_id}
        )

    async def list_tasks(self, project_id, status=None, limit=1000):
        query = {"project_id": project_id}
        if status:
            query["status"] = status
        return await self.tasks.find(query).sort("updated_at", -1).to_list(limit)

    async def list_tasks_for_projects(self, project_ids, limit=10000):
        if not project_ids:
            return []
        return await self.tasks.find({"project_id": {"$in": list(project_ids)}}).to_list(limit)

    async def find_task(self, project_id, task_id):
        return await self.tasks.find_one({"_id": task_id, "project_id": project_id})

    async def create_task(self, task):
        await self.tasks.insert_one(task)
        return task

    async def update_task(self, project_id, task_id, revision, changes):
        return await self.tasks.find_one_and_update(
            {"_id": task_id, "project_id": project_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def delete_task(self, project_id, task_id, revision):
        return await self.tasks.delete_one(
            {"_id": task_id, "project_id": project_id, "revision": revision}
        )


project_repository = ProjectRepository()
