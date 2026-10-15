from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.repositories.test_design import test_design_repository


async def create_repository_node(payload, user):
    await get_project(payload.project_id, user, "testcase.create")
    if payload.parent_id and not await test_design_repository.find_repository_node(
        payload.project_id, payload.parent_id
    ):
        raise HTTPException(status_code=422, detail={"code": "INVALID_TEST_REPOSITORY_PARENT"})
    timestamp = now()
    value = {
        "_id": new_id("TREP"),
        **payload.model_dump(),
        "status": "ACTIVE",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await test_design_repository.insert_repository_node(value)
    await audit(user.id, "test_repository_node_created", "TestRepositoryNode", value["_id"], payload.project_id)
    return value


async def list_repository_nodes(project_id, user):
    await get_project(project_id, user, "testcase.read")
    return await test_design_repository.list_repository_nodes(project_id)


async def update_repository_node(node_id, payload, user):
    node = await get_project_entity("test_repository_nodes", node_id, user, "testcase.update")
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    parent_id = changes.get("parent_id", node.get("parent_id"))
    if parent_id == node_id:
        raise HTTPException(status_code=422, detail={"code": "TEST_REPOSITORY_SELF_PARENT"})
    if parent_id and not await test_design_repository.find_repository_node(node["project_id"], parent_id):
        raise HTTPException(status_code=422, detail={"code": "INVALID_TEST_REPOSITORY_PARENT"})
    if parent_id:
        nodes = await test_design_repository.list_repository_nodes(node["project_id"])
        parents = {item["_id"]: item.get("parent_id") for item in nodes}
        ancestor_id = parent_id
        while ancestor_id:
            if ancestor_id == node_id:
                raise HTTPException(status_code=422, detail={"code": "TEST_REPOSITORY_CYCLIC_PARENT"})
            ancestor_id = parents.get(ancestor_id)
    changes["updated_at"] = now()
    updated = await test_design_repository.update_repository_node(
        node_id, node["project_id"], payload.expected_revision, changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await audit(user.id, "test_repository_node_updated", "TestRepositoryNode", node_id, node["project_id"])
    return updated


async def create_reusable_step(payload, user):
    await get_project(payload.project_id, user, "testcase.create")
    timestamp = now()
    version_id = new_id("TRSV")
    value = {
        "_id": new_id("TRS"),
        **payload.model_dump(),
        "version": 1,
        "current_version_id": version_id,
        "status": "ACTIVE",
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await test_design_repository.insert_reusable_step(value)
    await test_design_repository.insert_reusable_step_version(
        {
            "_id": version_id,
            "project_id": payload.project_id,
            "reusable_step_id": value["_id"],
            "version": 1,
            "name": value["name"],
            "action_doc": value["action_doc"],
            "expected_doc": value["expected_doc"],
            "status": "ACTIVE",
            "created_by": user.id,
            "created_at": timestamp,
        }
    )
    await audit(user.id, "reusable_test_step_created", "ReusableTestStep", value["_id"], payload.project_id)
    return value


async def list_reusable_steps(project_id, user):
    await get_project(project_id, user, "testcase.read")
    return await test_design_repository.list_reusable_steps(project_id)


async def update_reusable_step(step_id, payload, user):
    step = await get_project_entity("reusable_test_steps", step_id, user, "testcase.update")
    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    timestamp = now()
    version = step.get("version", 1) + 1
    version_id = new_id("TRSV")
    changes.update({"version": version, "current_version_id": version_id, "updated_at": timestamp})
    updated = await test_design_repository.update_reusable_step(
        step_id, step["project_id"], payload.expected_revision, changes
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT"})
    await test_design_repository.insert_reusable_step_version(
        {
            "_id": version_id,
            "project_id": step["project_id"],
            "reusable_step_id": step_id,
            "version": version,
            "name": updated["name"],
            "action_doc": updated["action_doc"],
            "expected_doc": updated["expected_doc"],
            "status": "ACTIVE",
            "created_by": user.id,
            "created_at": timestamp,
        }
    )
    await audit(user.id, "reusable_test_step_version_created", "ReusableTestStep", step_id, step["project_id"])
    return updated
