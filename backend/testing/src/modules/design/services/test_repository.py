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
    try:
        await test_design_repository.insert_repository_node(value)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail={"code": "TEST_REPOSITORY_NAME_EXISTS"})
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
