from pymongo import ReturnDocument

from src.core.database import database


class TestDesignRepository:
    async def list_repository_nodes(self, project_id):
        return await database.value.test_repository_nodes.find(
            {"project_id": project_id, "status": "ACTIVE"}
        ).sort("name", 1).to_list(5000)

    async def find_repository_node(self, project_id, node_id):
        return await database.value.test_repository_nodes.find_one(
            {"_id": node_id, "project_id": project_id, "status": "ACTIVE"}
        )

    async def insert_repository_node(self, value):
        await database.value.test_repository_nodes.insert_one(value)
        return value

    async def update_repository_node(self, node_id, project_id, revision, changes):
        return await database.value.test_repository_nodes.find_one_and_update(
            {"_id": node_id, "project_id": project_id, "status": "ACTIVE", "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def count_repository_children(self, project_id, node_id):
        return await database.value.test_repository_nodes.count_documents(
            {"project_id": project_id, "parent_id": node_id, "status": "ACTIVE"}
        )

    async def count_repository_cases(self, project_id, node_id):
        return await database.value.test_cases.count_documents(
            {"project_id": project_id, "repository_node_id": node_id}
        )

    async def list_reusable_steps(self, project_id):
        return await database.value.reusable_test_steps.find(
            {"project_id": project_id, "status": "ACTIVE"}
        ).sort("updated_at", -1).to_list(1000)

    async def find_reusable_step(self, project_id, step_id):
        return await database.value.reusable_test_steps.find_one(
            {"_id": step_id, "project_id": project_id, "status": "ACTIVE"}
        )

    async def find_reusable_step_version(self, project_id, version_id):
        return await database.value.reusable_test_step_versions.find_one(
            {"_id": version_id, "project_id": project_id, "status": "ACTIVE"}
        )

    async def insert_reusable_step(self, value, session=None):
        await database.value.reusable_test_steps.insert_one(value, session=session)
        return value

    async def insert_reusable_step_version(self, value, session=None):
        await database.value.reusable_test_step_versions.insert_one(value, session=session)
        return value

    async def update_reusable_step(self, step_id, project_id, revision, changes):
        return await database.value.reusable_test_steps.find_one_and_update(
            {"_id": step_id, "project_id": project_id, "status": "ACTIVE", "revision": revision},
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def list_cases(self, project_id, status=None, limit=20000):
        query = {"project_id": project_id}
        if status:
            query["status"] = status
        return await database.value.test_cases.find(query).to_list(limit)

    async def list_case_versions_by_ids(self, project_id, version_ids, limit=20000):
        return await database.value.test_case_versions.find(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        ).to_list(limit)

    async def list_confirmed_case_traces(self, project_id, version_ids, status, limit=50000):
        return await database.value.trace_links.find(
            {"project_id": project_id, "target_id": {"$in": version_ids}, "status": status},
            {"target_id": 1},
        ).to_list(limit)

    async def list_case_results(self, project_id, version_ids, limit=50000):
        return (
            await database.value.test_results.find(
                {"project_id": project_id, "test_case_version_id": {"$in": version_ids}}
            )
            .sort("updated_at", -1)
            .to_list(limit)
        )

    async def find_defect(self, project_id, defect_id):
        return await database.value.defects.find_one({"_id": defect_id, "project_id": project_id})

    async def find_suite(self, suite_id, project_id):
        return await database.value.test_suites.find_one(
            {"_id": suite_id, "project_id": project_id}
        )

    async def list_requirement_version_ids(self, project_id, requirement_id, limit=1000):
        return await database.value.requirement_versions.find(
            {"project_id": project_id, "requirement_id": requirement_id}, {"_id": 1}
        ).to_list(limit)

    async def list_case_drafts(self, project_id, limit, statuses=None):
        query = {"project_id": project_id}
        if statuses is not None:
            query["status"] = {"$in": statuses}
        return (
            await database.value.test_case_drafts.find(query)
            .sort("updated_at", -1)
            .to_list(limit)
        )

    async def list_related_case_drafts(self, project_id, version_id, limit, statuses=None):
        query = {"project_id": project_id, "requirement_version_ids": version_id}
        if statuses is not None:
            query["status"] = {"$in": statuses}
        return await database.value.test_case_drafts.find(query).sort("updated_at", -1).to_list(limit)

    async def list_versions_for_case(self, test_case_id, limit=500):
        return (
            await database.value.test_case_versions.find({"test_case_id": test_case_id})
            .sort("version", -1)
            .to_list(limit)
        )

    async def list_selected_case_versions(self, project_id, test_case_id, version_ids):
        return await database.value.test_case_versions.find(
            {
                "_id": {"$in": version_ids},
                "project_id": project_id,
                "test_case_id": test_case_id,
            }
        ).to_list(len(version_ids))

    async def set_case_lifecycle_status(self, test_case_id, project_id, status, changes):
        query = {"_id": test_case_id}
        if project_id:
            query["project_id"] = project_id
        await database.value.test_cases.update_one(
            query, {"$set": {**changes, "status": status}}
        )
        return await database.value.test_cases.find_one(query)

    async def insert_ai_finding(self, value):
        await database.value.ai_findings.insert_one(value)

    async def find_case_draft(self, draft_id, project_id):
        return await database.value.test_case_drafts.find_one(
            {"_id": draft_id, "project_id": project_id}
        )

    async def transition_case_draft(
        self, draft_id, project_id, revision, source_status, target_status, changes
    ):
        result = await database.value.test_case_drafts.update_one(
            {
                "_id": draft_id,
                "project_id": project_id,
                "revision": revision,
                "status": source_status,
            },
            {"$set": {**changes, "status": target_status}, "$inc": {"revision": 1}},
        )
        return result.matched_count == 1

    async def claim_case_draft(
        self, draft_id, project_id, revision, source_status, target_status, changes
    ):
        return await database.value.test_case_drafts.find_one_and_update(
            {
                "_id": draft_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            {"$set": {**changes, "status": target_status}, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def find_case_version(self, version_id, project_id):
        return await database.value.test_case_versions.find_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def find_case(self, test_case_id, project_id):
        return await database.value.test_cases.find_one(
            {"_id": test_case_id, "project_id": project_id}
        )

    async def find_case_by_key(self, project_id, test_case_key):
        return await database.value.test_cases.find_one(
            {"project_id": project_id, "test_case_key": test_case_key}
        )

    async def find_latest_case_version(self, test_case_id):
        return await database.value.test_case_versions.find_one(
            {"test_case_id": test_case_id}, sort=[("version", -1)]
        )

    async def insert_case(self, value):
        await database.value.test_cases.insert_one(value)

    async def insert_case_version(self, value):
        await database.value.test_case_versions.insert_one(value)

    async def set_case_version_index_result(
        self, version_id, project_id, index_status, error_code, indexed_at
    ):
        return await database.value.test_case_versions.update_one(
            {"_id": version_id, "project_id": project_id},
            {
                "$set": {
                    "index_status": index_status,
                    "index_error_code": error_code,
                    "indexed_at": indexed_at,
                }
            },
        )

    async def set_case_version_approval_result(
        self,
        version_id,
        project_id,
        index_status,
        index_error_code,
        indexed_at,
        trace_status,
        trace_error_code,
        approval_audit_status,
        approval_audit_error_code,
    ):
        return await database.value.test_case_versions.update_one(
            {"_id": version_id, "project_id": project_id},
            {
                "$set": {
                    "index_status": index_status,
                    "index_error_code": index_error_code,
                    "indexed_at": indexed_at,
                    "trace_status": trace_status,
                    "trace_error_code": trace_error_code,
                    "approval_audit_status": approval_audit_status,
                    "approval_audit_error_code": approval_audit_error_code,
                }
            },
        )

    async def activate_case_version(
        self, test_case_id, project_id, parent_version_id, version_id, status, updated_at
    ):
        result = await database.value.test_cases.update_one(
            {
                "_id": test_case_id,
                "project_id": project_id,
                "current_version_id": parent_version_id,
            },
            {
                "$set": {
                    "current_version_id": version_id,
                    "status": status,
                    "updated_at": updated_at,
                }
            },
        )
        return result.matched_count == 1

    async def approve_case_draft(
        self,
        draft_id,
        project_id,
        revision,
        source_status,
        target_status,
        version_id,
        updated_at,
    ):
        result = await database.value.test_case_drafts.update_one(
            {
                "_id": draft_id,
                "project_id": project_id,
                "status": source_status,
                "revision": revision,
            },
            {
                "$set": {
                    "status": target_status,
                    "frozen_version_id": version_id,
                    "updated_at": updated_at,
                },
                "$inc": {"revision": 1},
            },
        )
        return result.matched_count == 1

    async def delete_case_version(self, version_id, project_id):
        await database.value.test_case_versions.delete_one(
            {"_id": version_id, "project_id": project_id}
        )

    async def delete_unactivated_case(self, test_case_id, project_id, version_ids):
        await database.value.test_cases.delete_one(
            {
                "_id": test_case_id,
                "project_id": project_id,
                "current_version_id": {"$in": version_ids},
            }
        )

    async def restore_case_version(self, test_case_id, project_id, version_id, parent_id, updated_at):
        await database.value.test_cases.update_one(
            {
                "_id": test_case_id,
                "project_id": project_id,
                "current_version_id": version_id,
            },
            {"$set": {"current_version_id": parent_id, "updated_at": updated_at}},
        )

    async def reset_case_draft(
        self, draft_id, project_id, source_status, target_status, updated_at
    ):
        await database.value.test_case_drafts.update_one(
            {"_id": draft_id, "project_id": project_id, "status": source_status},
            {
                "$set": {
                    "status": target_status,
                    "approval_error_at": updated_at,
                    "updated_at": updated_at,
                }
            },
        )

    async def find_trace_link(self, query):
        return await database.value.trace_links.find_one(query)

    async def insert_trace_link(self, value):
        await database.value.trace_links.insert_one(value)

    async def count_requirement_versions(self, project_id, version_ids):
        return await database.value.requirement_versions.count_documents(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        )

    async def count_acceptance_criteria(self, query):
        return await database.value.acceptance_criteria.count_documents(query)

    async def list_acceptance_criteria_by_ids(self, project_id, requirement_version_ids, criterion_ids):
        return await database.value.acceptance_criteria.find(
            {
                "project_id": project_id,
                "requirement_version_id": {"$in": requirement_version_ids},
                "_id": {"$in": criterion_ids},
            }
        ).to_list(len(criterion_ids))

    async def find_scenario(self, scenario_id, project_id):
        return await database.value.test_scenarios.find_one(
            {"_id": scenario_id, "project_id": project_id}
        )

    async def find_project_settings(self, project_id):
        project = await database.value.projects.find_one(
            {"_id": project_id}, {"settings": 1}
        )
        return (project or {}).get("settings") or {}

    async def find_current_requirement(self, project_id, requirement_id):
        return await database.value.requirements.find_one(
            {"_id": requirement_id, "project_id": project_id},
            {"current_version_id": 1, "status": 1},
        )

    async def list_conditions(self, query, limit):
        return await database.value.test_conditions.find(
            query, {"_id": 1, "status": 1}
        ).to_list(limit)

    async def count_data_set_versions(self, project_id, version_ids):
        return await database.value.data_set_versions.count_documents(
            {"project_id": project_id, "_id": {"$in": version_ids}}
        )

    async def insert_case_draft(self, value):
        await database.value.test_case_drafts.insert_one(value)
        return value

    async def list_requirement_versions(self, query, limit):
        return await database.value.requirement_versions.find(query).to_list(limit)

    async def list_case_versions(self, query, limit, sort_field=None, direction=1):
        cursor = database.value.test_case_versions.find(query)
        if sort_field:
            cursor = cursor.sort(sort_field, direction)
        return await cursor.to_list(limit)

    async def list_trace_links(self, query, limit):
        return await database.value.trace_links.find(query).to_list(limit)

    async def insert_trace_links(self, values):
        if values:
            await database.value.trace_links.insert_many(values)
        return values

    async def insert_import(self, value):
        await database.value.test_imports.insert_one(value)
        return value

    async def claim_import(self, import_id, project_id):
        return await database.value.test_imports.find_one_and_update(
            {"_id": import_id, "project_id": project_id, "status": "PREVIEW_READY"},
            {"$set": {"status": "CONFIRMING"}},
            return_document=ReturnDocument.AFTER,
        )

    async def reset_import(self, import_id, project_id):
        await database.value.test_imports.update_one(
            {"_id": import_id, "project_id": project_id, "status": "CONFIRMING"},
            {"$set": {"status": "PREVIEW_READY"}},
        )

    async def delete_created_drafts(self, project_id, draft_ids):
        if draft_ids:
            await database.value.test_case_drafts.delete_many(
                {"_id": {"$in": draft_ids}, "project_id": project_id}
            )

    async def confirm_import(self, import_id, project_id, changes):
        return await database.value.test_imports.update_one(
            {"_id": import_id, "project_id": project_id, "status": "CONFIRMING"},
            {"$set": changes},
        )

    async def list_requirement_evidence(self, query, limit):
        return await database.value.requirement_versions.find(query).sort(
            "created_at", -1
        ).to_list(limit)

    async def list_security_suggestions(self, project_id, limit):
        return await database.value.security_test_suggestions.find(
            {"project_id": project_id}
        ).sort("created_at", -1).to_list(limit)

    async def find_security_suggestion(self, project_id, idempotency_key):
        return await database.value.security_test_suggestions.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_security_suggestion(self, value):
        await database.value.security_test_suggestions.insert_one(value)
        return value

    async def list_performance_drafts(self, project_id, limit):
        return await database.value.performance_plan_drafts.find(
            {"project_id": project_id}
        ).sort("created_at", -1).to_list(limit)

    async def find_performance_draft(self, project_id, idempotency_key):
        return await database.value.performance_plan_drafts.find_one(
            {"project_id": project_id, "idempotency_key": idempotency_key}
        )

    async def insert_performance_draft(self, value):
        await database.value.performance_plan_drafts.insert_one(value)
        return value

    async def insert_scenario(self, value):
        await database.value.test_scenarios.insert_one(value)
        return value

    async def list_scenarios(self, query, sort_field, direction, limit):
        return await database.value.test_scenarios.find(query).sort(
            sort_field, direction
        ).to_list(limit)

    async def list_scenario_cases(self, project_id, scenario_id, limit=5000):
        return await database.value.test_cases.find(
            {"project_id": project_id, "scenario_id": scenario_id}
        ).sort("test_case_key", 1).to_list(limit)

    async def list_acceptance_criteria(self, requirement_version_id, limit=500):
        return await database.value.acceptance_criteria.find(
            {"requirement_version_id": requirement_version_id}
        ).to_list(limit)

    async def insert_suite(self, value):
        await database.value.test_suites.insert_one(value)
        return value

    async def list_suites(self, query, sort_field, direction, limit=500):
        return await database.value.test_suites.find(query).sort(
            sort_field, direction
        ).to_list(limit)

    async def list_templates(self, query, limit=500):
        return await database.value.test_case_templates.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def insert_template(self, value):
        await database.value.test_case_templates.insert_one(value)
        return value

    async def update_template(
        self, template_id, project_id, revision, active_status, changes
    ):
        return await database.value.test_case_templates.find_one_and_update(
            {
                "_id": template_id,
                "project_id": project_id,
                "status": active_status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )

    async def list_device_matrices(self, query, limit=500):
        return await database.value.device_matrices.find(query).sort(
            "updated_at", -1
        ).to_list(limit)

    async def insert_device_matrix(self, value):
        await database.value.device_matrices.insert_one(value)
        return value

    async def artifact_exists(self, collection_name, project_id, artifact_id):
        return bool(
            await database.value[collection_name].find_one(
                {"_id": artifact_id, "project_id": project_id},
                {"_id": 1},
            )
        )

    async def find_active_attachment(self, project_id, owner_id, url, active_status):
        return await database.value.attachments.find_one(
            {
                "project_id": project_id,
                "owner_id": owner_id,
                "url": url,
                "status": active_status,
            }
        )

    async def insert_attachment(self, value):
        await database.value.attachments.insert_one(value)
        return value

    async def list_attachments(self, query, limit=5000):
        return await database.value.attachments.find(query).sort(
            "created_at", -1
        ).to_list(limit)

    async def mark_attachment_deleted(
        self,
        attachment_id,
        project_id,
        revision,
        active_status,
        changes,
    ):
        return await database.value.attachments.find_one_and_update(
            {
                "_id": attachment_id,
                "project_id": project_id,
                "status": active_status,
                "revision": revision,
            },
            {"$set": changes, "$inc": {"revision": 1}},
            return_document=ReturnDocument.AFTER,
        )


test_design_repository = TestDesignRepository()
