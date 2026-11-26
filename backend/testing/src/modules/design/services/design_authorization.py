from src.core.common import get_project, get_project_entity
from src.core.human_decisions import can_auto_approve_project_content


async def require_assigned_design_draft(collection, artifact_id, user, permission, proposed_changes=None):
    artifact = await get_project_entity(collection, artifact_id, user, permission)
    if not await can_auto_approve_project_content(artifact["project_id"], user):
        if artifact.get("owner_id") != user.id:
            await get_project(
                artifact["project_id"], user, permission,
                assigned_user_id=artifact.get("owner_id"),
            )
    if (
        proposed_changes
        and "owner_id" in proposed_changes
        and proposed_changes["owner_id"] != artifact.get("owner_id")
    ):
        await get_project(artifact["project_id"], user, "project.members.read")
    return artifact
