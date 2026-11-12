from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.repositories.analysis import analysis_repository
from src.repositories.test_strategy import test_strategy_repository
from src.schemas.contracts.design import (
    RiskRankingApproval,
    RiskRankingGenerate,
    RiskRankingPatch,
)
from src.schemas.test_strategy import RiskRankingWeights

def resolve_ranking_weights(risk_model):
    configured = (risk_model or {}).get("ranking_weights") or {}
    defaults = RiskRankingWeights().model_dump()
    return {
        key: configured.get(key)
        if isinstance(configured.get(key), (int, float))
        and not isinstance(configured.get(key), bool)
        else defaults[key]
        for key in defaults
    }


class RiskRankingService:
    @staticmethod
    async def current(project_id: str, user: CurrentUser):
        
        await get_project(project_id, user, "risk.read")
        ranking = await analysis_repository.find_latest_risk_ranking(project_id)
        if ranking:
            return ranking
        return {
            "project_id": project_id,
            "status": 'DERIVED',
            "items": await RiskRankingService._build_items(project_id),
        }

    @staticmethod
    async def generate(
        project_id: str,
        payload: RiskRankingGenerate,
        user: CurrentUser,
    ):
        await get_project(project_id, user, "risk.generate")
        items = await RiskRankingService._build_items(project_id)
        if payload.max_items:
            items = items[: payload.max_items]
        
        ranking = {
            "_id": new_id('RISK'),
            "project_id": project_id,
            "items": items,
            "status": 'PENDING_APPROVAL',
            "model_version": 'risk_scoring',
            "revision": 1,
            "created_by": user.id,
            "created_at": now(),
            "updated_at": now(),
        }
        await analysis_repository.insert_risk_ranking(ranking)
        await audit(user.id, "risk_ranking_generated", "RiskRanking", ranking["_id"], project_id)
        return ranking

    @staticmethod
    async def review(
        ranking_id: str,
        payload: RiskRankingPatch,
        user: CurrentUser,
    ):
        
        ranking = await get_project_entity("risk_rankings", ranking_id, user, "risk.review")
        items = list(ranking.get("items") or [])
        by_version = {item.get("test_case_version_id"): item for item in items}
        target = by_version.get(payload.test_case_version_id)
        if not target:
            raise HTTPException(status_code=404, detail={"code": 'RISK_ITEM_NOT_FOUND'})
        target.update({"included": payload.included, "review_reason": payload.reason})
        updated = await optimistic_patch(
            "risk_rankings",
            ranking_id,
            ranking["project_id"],
            payload.expected_revision,
            {"items": list(by_version.values())},
        )
        await audit(
            user.id,
            "risk_ranking_reviewed",
            "RiskRanking",
            ranking_id,
            ranking["project_id"],
            {"test_case_version_id": payload.test_case_version_id},
        )
        return updated

    @staticmethod
    async def approve(
        ranking_id: str,
        payload: RiskRankingApproval,
        user: CurrentUser,
    ):
        
        ranking = await get_project_entity("risk_rankings", ranking_id, user, "risk.approve")
        if ranking.get("status") == 'APPROVED':
            return ranking
        if ranking.get("status") != 'PENDING_APPROVAL':
            raise HTTPException(status_code=409, detail={"code": 'RISK_RANKING_STATE_INVALID'})
        updated = await optimistic_patch(
            "risk_rankings",
            ranking_id,
            ranking["project_id"],
            payload.expected_revision,
            {
                "status": 'APPROVED',
                "approved_by": user.id,
                "approved_at": now(),
                "review_note": payload.review_note,
            },
        )
        await audit(
            user.id,
            "risk_ranking_approved",
            "RiskRanking",
            ranking_id,
            ranking["project_id"],
        )
        return updated

    @staticmethod
    def _configured_scale(scale: list[dict], label_key: str, order_key: str):
        ordered = sorted(
            (
                item
                for item in scale
                if str(item.get(label_key, "")).strip()
                and any(
                    isinstance(item.get(key), (int, float))
                    and not isinstance(item.get(key), bool)
                    for key in (order_key, "max")
                )
            ),
            key=lambda item: item[order_key]
            if isinstance(item.get(order_key), (int, float))
            and not isinstance(item.get(order_key), bool)
            else item["max"],
        )
        count = len(ordered)
        return {
            str(item[label_key]).strip().casefold(): (index / (count - 1) if count > 1 else 0.5)
            for index, item in enumerate(ordered)
        }

    @staticmethod
    def _score(
        test_case: dict,
        version: dict,
        failure_count: int,
        assessment_scores: dict,
        ranking_weights: dict,
    ):
        risk = assessment_scores["risk"].get(
            str(version.get("risk", "")).strip().casefold(),
            ranking_weights["unassessed_score"],
        )
        priority = assessment_scores["priority"].get(
            str(version.get("priority", "")).strip().casefold(),
            ranking_weights["unassessed_score"],
        )
        stale = (
            ranking_weights["staleness_penalty"]
            if test_case.get("status") == 'NEEDS_UPDATE'
            else 0
        )
        failures = min(
            ranking_weights["failure_penalty_cap"],
            failure_count * ranking_weights["failure_penalty_per_occurrence"],
        )
        return round(
            min(
                ranking_weights["maximum_score"],
                risk * ranking_weights["risk_weight"]
                + priority * ranking_weights["priority_weight"]
                + stale
                + failures,
            ),
            4,
        )

    @staticmethod
    async def _build_items(project_id: str):
        strategy = await test_strategy_repository.active_approved(project_id, "APPROVED")
        risk_model = (strategy or {}).get("risk_model") or {}
        assessment_scores = {
            "risk": RiskRankingService._configured_scale(
                risk_model.get("thresholds") or [], "level", "min"
            ),
            "priority": RiskRankingService._configured_scale(
                risk_model.get("priority_scale") or [], "label", "value"
            ),
        }
        ranking_weights = resolve_ranking_weights(risk_model)
        cases = await analysis_repository.list_current_test_cases(
            project_id,
            'OBSOLETE',
            {"_id": 1, "test_case_key": 1, "current_version_id": 1, "status": 1},
        )
        version_ids = [
            item.get("current_version_id") for item in cases if item.get("current_version_id")
        ]
        versions = await analysis_repository.list_test_case_versions(
            project_id,
            version_ids,
            {"_id": 1, "test_case_id": 1, "title": 1, "risk": 1, "priority": 1},
        )
        failures = await analysis_repository.failure_counts(project_id)
        failure_counts = {item["_id"]: item["count"] for item in failures}
        by_case = {item["_id"]: item for item in cases}
        items = []
        for version in versions:
            case = by_case.get(version.get("test_case_id"), {})
            failure_count = failure_counts.get(version["_id"], 0)
            items.append(
                {
                    "test_case_id": version.get("test_case_id"),
                    "test_case_version_id": version["_id"],
                    "test_case_key": case.get("test_case_key"),
                    "title": version.get("title"),
                    "risk": version.get("risk", ""),
                    "priority": version.get("priority", ""),
                    "failure_count": failure_count,
                    "score": RiskRankingService._score(
                        case, version, failure_count, assessment_scores, ranking_weights
                    ),
                    "included": True,
                    "reason_codes": list(['RISK', 'PRIORITY'])
                    + (['RECENT_FAILURE'] if failure_count else [])
                    + (
                        ['NEEDS_UPDATE']
                        if case.get("status") == 'NEEDS_UPDATE'
                        else []
                    ),
                }
            )
        items.sort(key=lambda item: (-item["score"], item.get("test_case_key") or ""))
        for index, item in enumerate(items, 1):
            item["rank"] = index
        return items
