from pymongo import ReturnDocument

from src.core.database import database


class RequirementTemplateRepository:
    async def list_visible(self, project_id):
        return await database.value.requirement_templates.find(
            {"$or": [{"project_id": project_id}, {"status": "PUBLISHED"}]}
        ).sort("updated_at", -1).to_list(500)

    async def find(self, template_id):
        return await database.value.requirement_templates.find_one({"_id": template_id})

    async def insert(self, template):
        await database.value.requirement_templates.insert_one(template)
        await self.save_version(template)
        return template

    async def save_version(self, template):
        snapshot = {
            "_id": f"{template['_id']}:v{template['version']}",
            "template_id": template["_id"],
            "project_id": template["project_id"],
            "version": template["version"],
            "snapshot": {key: value for key, value in template.items() if key != "_id"},
            "created_at": template.get("updated_at") or template.get("created_at"),
        }
        await database.value.requirement_template_versions.replace_one(
            {"_id": snapshot["_id"]}, snapshot, upsert=True
        )

    async def list_versions(self, template_id, project_id):
        return await database.value.requirement_template_versions.find(
            {"template_id": template_id, "project_id": project_id},
            {"snapshot": 0},
        ).sort("version", -1).to_list(200)

    async def find_version(self, template_id, project_id, version):
        return await database.value.requirement_template_versions.find_one(
            {"template_id": template_id, "project_id": project_id, "version": version}
        )

    async def update(self, template_id, version, changes):
        updated = await database.value.requirement_templates.find_one_and_update(
            {"_id": template_id, "version": version},
            {"$set": changes, "$inc": {"version": 1, "revision": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            await self.save_version(updated)
        return updated

    async def update_state(self, template_id, revision, changes):
        return await database.value.requirement_templates.find_one_and_update(
            {"_id": template_id, "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def list_fields(self, project_id):
        return await database.value.requirement_custom_fields.find(
            {"project_id": project_id}
        ).sort("created_at", 1).to_list(200)

    async def insert_field(self, field):
        await database.value.requirement_custom_fields.insert_one(field)
        return field


requirement_template_repository = RequirementTemplateRepository()
