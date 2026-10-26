from fastapi import HTTPException
from pymongo import ReturnDocument

from src.core.database import database


class TestCaseReviewRepository:
    async def merge(self, draft, changes, decision):
        async def commit(session):
            previous = await database.value.audit_events.find_one({"_id": decision["_id"]}, session=session)
            if previous:
                if (
                    previous.get("actor_id") != decision["actor_id"]
                    or (previous.get("details") or {}).get("request_hash")
                    != decision["details"]["request_hash"]
                ):
                    raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_REUSED"})
                current = await database.value.test_case_drafts.find_one({"_id": draft["_id"], "project_id": draft["project_id"]}, session=session)
                from src.modules.design.services.test_case_review import validate_merge_replay

                return validate_merge_replay(
                    previous,
                    current,
                    decision_id=decision["_id"],
                    draft_id=draft["_id"],
                    project_id=draft["project_id"],
                    actor_id=decision["actor_id"],
                    expected_revision=draft["revision"],
                    request_hash=decision["details"]["request_hash"],
                )
            current = await database.value.test_case_drafts.find_one(
                {"_id": draft["_id"], "project_id": draft["project_id"], "revision": draft["revision"], "status": {"$in": ["DRAFT", "IN_REVIEW"]}},
                session=session,
            )
            if not current:
                raise HTTPException(409, detail={"code": "REVISION_CONFLICT"})
            from src.modules.design.services.test_case_review import assert_sources_current_in_session

            await assert_sources_current_in_session({**current, **changes}, session)
            result = await database.value.test_case_drafts.find_one_and_update(
                {"_id": draft["_id"], "project_id": draft["project_id"], "revision": draft["revision"], "status": {"$in": ["DRAFT", "IN_REVIEW"]}},
                {"$set": changes, "$inc": {"revision": 1}, "$push": {"merge_decision_ids": decision["_id"]}},
                return_document=ReturnDocument.AFTER, session=session,
            )
            if not result:
                raise HTTPException(409, detail={"code": "REVISION_CONFLICT"})
            await database.value.audit_events.insert_one(decision, session=session)
            return {"draft": result, "applied_revision": result["revision"], "idempotent": False}

        async with await database.client.start_session() as session:
            return await session.with_transaction(commit)

    async def find_decision(self, decision_id):
        return await database.value.audit_events.find_one({"_id": decision_id})


test_case_review_repository = TestCaseReviewRepository()
