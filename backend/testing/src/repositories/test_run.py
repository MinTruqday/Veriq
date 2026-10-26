from pymongo import ReturnDocument

from src.core.database import database


class TestRunRepository:
    async def find_plan(self, plan_id, project_id, session=None):
        return await database.value.test_plans.find_one(
            {"_id": plan_id, "project_id": project_id},
            **({"session": session} if session is not None else {}),
        )

    async def list_suites(self, project_id, suite_ids, limit):
        return await database.value.test_suites.find(
            {"project_id": project_id, "_id": {"$in": suite_ids}}
        ).to_list(limit)

    async def insert_run(self, value, session=None):
        await database.value.test_runs.insert_one(value, session=session)
        return value

    async def find_run_by_idempotency_key(self, project_id, idempotency_key):
        return await database.value.test_runs.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def find_rerun_by_key(self, project_id, source_run_id, idempotency_key, session=None):
        return await database.value.test_runs.find_one(
            {
                "project_id": project_id,
                "rerun_of_run_id": source_run_id,
                "idempotency_key": idempotency_key,
            },
            **({"session": session} if session is not None else {}),
        )

    async def insert_results(self, values, session=None):
        if values:
            await database.value.test_results.insert_many(values, session=session)
        return values

    async def delete_run_results(self, run_id, project_id):
        await database.value.test_results.delete_many(
            {"test_run_id": run_id, "project_id": project_id}
        )

    async def delete_run(self, run_id, project_id):
        await database.value.test_runs.delete_one(
            {"_id": run_id, "project_id": project_id}
        )

    async def find_active_tester(self, project_id, user_id, status, role):
        return await database.value.project_members.find_one(
            {
                "project_id": project_id,
                "user_id": user_id,
                "status": status,
                "$or": [{"project_role": role}, {"project_roles": role}],
            }
        )

    async def count_active_testers(self, project_id, user_ids, status, role):
        return await database.value.project_members.count_documents(
            {
                "project_id": project_id,
                "user_id": {"$in": user_ids},
                "status": status,
                "$or": [{"project_role": role}, {"project_roles": role}],
            }
        )

    async def count_runs(self, query):
        return await database.value.test_runs.count_documents(query)

    async def list_runs(self, query, sort_field, direction, skip, limit):
        return await database.value.test_runs.find(query).sort(
            sort_field, direction
        ).skip(skip).limit(limit).to_list(limit)

    async def list_results(self, query, limit, sort_field=None, direction=-1, session=None):
        cursor = database.value.test_results.find(
            query, **({"session": session} if session is not None else {})
        )
        if sort_field:
            cursor = cursor.sort(sort_field, direction)
        return await cursor.to_list(limit)

    async def delete_results_for_versions(self, run_id, project_id, version_ids, session=None):
        if not version_ids:
            return 0
        result = await database.value.test_results.delete_many(
            {
                "test_run_id": run_id,
                "project_id": project_id,
                "test_case_version_id": {"$in": version_ids},
            },
            **({"session": session} if session is not None else {}),
        )
        return result.deleted_count

    async def list_versions(self, version_ids, limit, session=None):
        return await database.value.test_case_versions.find(
            {"_id": {"$in": version_ids}}, session=session
        ).to_list(limit)

    async def list_defects_for_results(self, project_id, result_ids, limit):
        return await database.value.defects.find(
            {"project_id": project_id, "linked_test_result_id": {"$in": result_ids}}
        ).to_list(limit)

    async def find_environment(self, environment_id, project_id):
        return await database.value.test_environments.find_one(
            {"_id": environment_id, "project_id": project_id}
        )

    async def transition_run(self, query, changes):
        return await database.value.test_runs.find_one_and_update(
            query,
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_resume_event(self, run_id, idempotency_key):
        return await database.value.test_run_resume_events.find_one(
            {"test_run_id": run_id, "idempotency_key": idempotency_key}
        )

    async def insert_resume_event(self, value):
        await database.value.test_run_resume_events.insert_one(value)
        return value

    async def delete_resume_event(self, event_id):
        await database.value.test_run_resume_events.delete_one({"_id": event_id})

    async def set_resume_event_revision(self, event_id, revision):
        await database.value.test_run_resume_events.update_one(
            {"_id": event_id}, {"$set": {"run_revision": revision}}
        )

    async def find_result_for_case(self, run_id, version_id):
        return await database.value.test_results.find_one(
            {"test_run_id": run_id, "test_case_version_id": version_id}
        )

    async def update_result(self, query, changes, push=None, session=None):
        update = {"$set": changes, "$inc": {"revision": 1}}
        if push:
            update["$push"] = push
        return await database.value.test_results.find_one_and_update(
            query,
            update,
            return_document=ReturnDocument.AFTER,
            **({"session": session} if session is not None else {}),
        )

    async def insert_result(self, value, session=None):
        await database.value.test_results.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def touch_run(self, run_id, project_id, updated_at, session=None):
        query = {"_id": run_id}
        if project_id is not None:
            query["project_id"] = project_id
        await database.value.test_runs.update_one(
            query,
            {"$set": {"updated_at": updated_at}, "$inc": {"revision": 1}},
            **({"session": session} if session is not None else {}),
        )

    async def find_execution_update(self, result_id, idempotency_key, session=None):
        return await database.value.test_execution_updates.find_one(
            {"test_result_id": result_id, "idempotency_key": idempotency_key},
            **({"session": session} if session is not None else {}),
        )

    async def insert_execution_update(self, value, session=None):
        await database.value.test_execution_updates.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def find_result(self, result_id):
        return await database.value.test_results.find_one({"_id": result_id})

    async def find_run(self, run_id, project_id=None, session=None):
        query = {"_id": run_id}
        if project_id is not None:
            query["project_id"] = project_id
        return await database.value.test_runs.find_one(
            query, **({"session": session} if session is not None else {})
        )

    async def find_correction(self, result_id, idempotency_key, session=None):
        return await database.value.test_result_corrections.find_one(
            {"test_result_id": result_id, "idempotency_key": idempotency_key},
            **({"session": session} if session is not None else {}),
        )

    async def insert_correction(self, value, session=None):
        await database.value.test_result_corrections.insert_one(
            value, **({"session": session} if session is not None else {})
        )
        return value

    async def count_results_by_status(self, run_id, statuses):
        return await database.value.test_results.count_documents(
            {"test_run_id": run_id, "status": {"$in": statuses}}
        )

    async def project_settings(self, project_id):
        return await database.value.projects.find_one(
            {"_id": project_id}, {"settings": 1}
        )

    async def update_run(self, run_id, changes):
        await database.value.test_runs.update_one(
            {"_id": run_id}, {"$set": changes, "$inc": {"revision": 1}}
        )
        return await self.find_run(run_id)


test_run_repository = TestRunRepository()
