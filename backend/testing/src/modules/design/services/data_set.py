from itertools import product
from math import prod

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now
from src.core.database import database
from src.modules.design.services.test_case_records import require_current_baselined_version
from src.repositories.execution_asset import execution_asset_repository





def public_version(version):
    if not version:
        return None
    return {
        **version,
        "variable_names": sorted((version.get("variables") or {}).keys()),
        "secret_names": sorted((version.get("secret_refs") or {}).keys()),
        "secret_refs": {
            key: '[BÍ MẬT]'
            for key in sorted((version.get("secret_refs") or {}).keys())
        },
    }


def expand_variables(variables, max_rows):
    keys = sorted(variables)
    choices = []
    for key in keys:
        value = variables[key]
        values = value if isinstance(value, list) else [value]
        choices.append(values[:max_rows])
    total = prod(len(values) for values in choices) if choices else 1
    rows = []
    combinations = product(*choices) if choices else [()]
    for combination in combinations:
        rows.append(dict(zip(keys, combination)))
        if len(rows) >= max_rows:
            break
    return rows, total > max_rows


class DataSetService:
    @staticmethod
    async def _get_version(data_set_id, version_id, user, permission=None):
        data_set = await get_project_entity(
            'data_sets',
            data_set_id,
            user,
            permission or 'testdata.read',
        )
        version = await execution_asset_repository.find_data_set_version(
            data_set["project_id"], data_set_id, version_id
        )
        if not version:
            raise HTTPException(status_code=404, detail={"code": 'DATA_SET_VERSION_NOT_FOUND'})
        return data_set, version

    @staticmethod
    async def create(project_id, payload, user):
        await get_project(project_id, user, 'testdata.create')
        if payload.source_requirement_version_ids:
            source_ids = payload.source_requirement_version_ids
            versions = await database.value.requirement_versions.find({
                "project_id": project_id,
                "_id": {"$in": source_ids},
                "status": "BASELINED",
            }).to_list(len(source_ids))
            if len(versions) != len(source_ids):
                raise HTTPException(422, detail={"code": "TEST_DATA_SOURCE_REQUIREMENT_INVALID"})
            for version in versions:
                await require_current_baselined_version(version)
        timestamp = now()
        data_set_id = new_id('DATA')
        version = {
            "_id": new_id('DATAV'),
            "project_id": project_id,
            "data_set_id": data_set_id,
            "version": 1,
            **payload.model_dump(),
            "change_reason": 'Tạo bộ dữ liệu kiểm thử',
            "created_by": user.id,
            "created_at": timestamp,
        }
        data_set = {
            "_id": data_set_id,
            "project_id": project_id,
            "name": payload.name,
            "current_version_id": version["_id"],
            "revision": 1,
            "status": 'ACTIVE',
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await execution_asset_repository.create_data_set(data_set, version)
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail={"code": 'DATA_SET_NAME_EXISTS'})
        await audit(
            user.id,
            'data_set_created',
            'DataSet',
            data_set_id,
            project_id,
            {
                "source_requirement_version_ids": version.get("source_requirement_version_ids", []),
            },
        )
        return {**data_set, "current_version": public_version(version)}

    @staticmethod
    async def list(project_id, query_text, limit, user):
        await get_project(project_id, user, 'testdata.read')
        query = {"project_id": project_id, "status": 'ACTIVE'}
        if query_text:
            query["name"] = {"$regex": query_text, "$options": "i"}
        items = await execution_asset_repository.list_data_sets(query, limit)
        version_ids = [item["current_version_id"] for item in items]
        versions = await execution_asset_repository.list_data_set_versions(
            {"project_id": project_id, "_id": {"$in": version_ids}}, limit
        )
        by_id = {item["_id"]: item for item in versions}
        return [
            {**item, "current_version": public_version(by_id.get(item["current_version_id"]))}
            for item in items
        ]

    @staticmethod
    async def get(data_set_id, user):
        data_set = await get_project_entity('data_sets', data_set_id, user, 'testdata.read')
        version = await execution_asset_repository.find_data_set_version(
            data_set["project_id"], data_set_id, data_set["current_version_id"]
        )
        return {**data_set, "current_version": public_version(version)}

    @staticmethod
    async def list_versions(data_set_id, user):
        data_set = await get_project_entity('data_sets', data_set_id, user, 'testdata.read')
        versions = await execution_asset_repository.list_data_set_versions(
            {"project_id": data_set["project_id"], "data_set_id": data_set_id},
            500,
            newest_first=True,
        )
        return [public_version(version) for version in versions]

    @staticmethod
    async def create_version(data_set_id, payload, user):
        data_set = await get_project_entity('data_sets', data_set_id, user, 'testdata.update')
        if data_set.get("current_version_id") != payload.expected_current_version_id:
            raise HTTPException(
                status_code=409,
                detail={"code": 'REVISION_CONFLICT', "current_version_id": data_set.get("current_version_id")},
            )
        current = await execution_asset_repository.find_data_set_version(
            data_set["project_id"], data_set_id, payload.expected_current_version_id
        )
        if not current:
            raise HTTPException(status_code=409, detail={"code": 'DATA_SET_HISTORY_INVALID'})
        timestamp = now()
        version = {
            "_id": new_id('DATAV'),
            "project_id": data_set["project_id"],
            "data_set_id": data_set_id,
            "version": int(current["version"]) + 1,
            "name": payload.name,
            "variables": payload.variables,
            "secret_refs": payload.secret_refs,
            "change_reason": payload.change_reason,
            "parent_version_id": current["_id"],
            "created_by": user.id,
            "created_at": timestamp,
        }
        try:
            created = await execution_asset_repository.create_data_set_version(
                data_set, version, payload.name, timestamp
            )
        except DuplicateKeyError as error:
            raise HTTPException(status_code=409, detail={"code": 'DATA_SET_VERSION_CONFLICT'}) from error
        if not created:
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        await audit(
            user.id,
            'data_set_version_created',
            'DataSetVersion',
            version["_id"],
            data_set["project_id"],
            {"data_set_id": data_set_id, "version": version["version"]},
        )
        return public_version(version), data_set["revision"] + 1

    @classmethod
    async def bind(cls, project_id, data_set_id, payload, user):
        data_set, version = await cls._get_version(
            data_set_id, payload.data_set_version_id, user, 'testdata.bind'
        )
        if data_set["project_id"] != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        draft = await get_project_entity('test_case_drafts', payload.test_case_draft_id, user, 'testdata.bind')
        if draft["project_id"] != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        if draft.get("status") != 'DRAFT':
            raise HTTPException(status_code=409, detail={"code": 'TEST_CASE_DRAFT_IMMUTABLE'})
        updated = await execution_asset_repository.bind_data_set_version(
            draft["_id"],
            project_id,
            payload.expected_revision,
            version["_id"],
            'DRAFT',
            now(),
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        await audit(
            user.id,
            'data_set_bound',
            'DataSetVersion',
            version["_id"],
            project_id,
            {"test_case_draft_id": draft["_id"]},
        )
        return updated

    @classmethod
    async def preview(cls, project_id, data_set_id, payload, user):
        data_set, version = await cls._get_version(data_set_id, payload.data_set_version_id, user)
        if data_set["project_id"] != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        rows, truncated = expand_variables(version.get("variables") or {}, payload.max_rows)
        return {
            "data_set_id": data_set_id,
            "data_set_version_id": version["_id"],
            "items": rows,
            "secret_names": sorted((version.get("secret_refs") or {}).keys()),
            "truncated": truncated,
        }

    @staticmethod
    async def archive(project_id, data_set_id, payload, user):
        data_set = await get_project_entity('data_sets', data_set_id, user, 'testdata.archive')
        if data_set["project_id"] != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        if data_set.get("status") == 'ARCHIVED':
            return data_set
        updated = await execution_asset_repository.archive_data_set(
            data_set_id,
            project_id,
            payload.expected_revision,
            payload.reason,
            'ACTIVE',
            'ARCHIVED',
            now(),
        )
        if not updated:
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        await audit(user.id, 'data_set_archived', 'DataSet', data_set_id, project_id, {"reason": payload.reason})
        return updated
