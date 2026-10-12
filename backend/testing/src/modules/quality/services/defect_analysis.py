from difflib import SequenceMatcher

from src.core.common import plain_text
from src.repositories.analysis import analysis_repository


def confidence_band(score):
    if score >= 0.75:
        return 'HIGH'
    if score >= 0.5:
        return 'MEDIUM'
    return 'LOW'


async def find_duplicate_defect_pairs(project_id):
    
    defects = await analysis_repository.list_active_defects(
        project_id, set(['REJECTED', 'DUPLICATE'])
    )
    pairs = []
    for index, left in enumerate(defects):
        left_text = " ".join(
            [left.get("title", ""), plain_text(left.get("description_doc", {}))]
        ).lower()
        for right in defects[index + 1 :]:
            right_text = " ".join(
                [right.get("title", ""), plain_text(right.get("description_doc", {}))]
            ).lower()
            similarity = round(SequenceMatcher(None, left_text, right_text).ratio(), 4)
            if similarity < 0.65:
                continue
            pairs.append(
                {
                    "_id": f"{left['_id']}:{right['_id']}",
                    "left": left,
                    "right": right,
                    "similarity": similarity,
                    "reason": 'Tiêu đề và mô tả có mức tương đồng cao',
                }
            )
    pairs.sort(key=lambda item: item["similarity"], reverse=True)
    return pairs[: 100]


async def build_defect_trace_candidates(defect):
    
    text = " ".join(
        [
            defect.get("title", ""),
            plain_text(defect.get("description_doc", {})),
            plain_text(defect.get("actual_result_doc", {})),
            plain_text(defect.get("expected_result_doc", {})),
        ]
    ).lower()
    requirements = await analysis_repository.list_current_requirements(
        defect["project_id"], 'OBSOLETE'
    )
    requirement_version_ids = [
        item.get("current_version_id") for item in requirements if item.get("current_version_id")
    ]
    requirement_versions = await analysis_repository.list_requirement_versions(
        defect["project_id"], requirement_version_ids
    )
    requirement_by_version = {
        item.get("current_version_id"): item
        for item in requirements
        if item.get("current_version_id")
    }
    test_cases = await analysis_repository.list_current_test_cases(
        defect["project_id"],
        'OBSOLETE',
        limit=2000,
    )
    current_ids = [
        item.get("current_version_id") for item in test_cases if item.get("current_version_id")
    ]
    versions = await analysis_repository.list_test_case_versions(
        defect["project_id"], current_ids, limit=2000
    )
    linked_requirements = set(defect.get("linked_requirement_version_ids", []))
    linked_test_version = next(
        (item for item in versions if item["_id"] == defect.get("linked_test_case_version_id")),
        None,
    )
    linked_test_requirements = set(
        linked_test_version.get("requirement_version_ids", []) if linked_test_version else []
    )
    requirement_candidates = []
    for version in requirement_versions:
        requirement = requirement_by_version.get(version["_id"], {})
        version_text = " ".join(
            [
                requirement.get("title", ""),
                version.get("title", ""),
                version.get("plain_text_projection", ""),
                plain_text(version.get("content_doc", {})),
            ]
        ).lower()
        similarity = SequenceMatcher(None, text, version_text).ratio()
        direct = version["_id"] in linked_requirements
        test_trace = version["_id"] in linked_test_requirements
        score = min(
            1,
            similarity * 0.7
            + (0.35 if direct else 0)
            + (0.2 if test_trace else 0),
        )
        if score < 0.25:
            continue
        reasons = []
        if direct:
            reasons.append('CURRENT_REQUIREMENT_LINK')
        if test_trace:
            reasons.append('LINKED_TEST_CASE_TRACE')
        if similarity >= 0.3:
            reasons.append('SIMILAR_REQUIREMENT_TEXT')
        requirement_candidates.append(
            {
                "candidate_id": f"requirement_version:{version['_id']}",
                "artifact_type": 'requirement_version',
                "artifact_id": version["_id"],
                "requirement_id": version["requirement_id"],
                "requirement_key": version.get("requirement_key")
                or requirement.get("requirement_key"),
                "title": version.get("title") or requirement.get("title", ""),
                "confidence": round(score, 4),
                "confidence_band": confidence_band(score),
                "reason_codes": reasons,
                "evidence": [
                    {
                        "artifact_type": 'defect',
                        "artifact_id": defect["_id"],
                    },
                    {
                        "artifact_type": 'requirement_version',
                        "artifact_id": version["_id"],
                    },
                ],
                "proposed_change": {
                    "operation": 'ADD_REQUIREMENT_LINK',
                    "linked_requirement_version_id": version["_id"],
                },
            }
        )
    test_case_candidates = []
    for version in versions:
        version_text = " ".join(
            [version.get("title", ""), version.get("plain_text_projection", "")]
        ).lower()
        similarity = SequenceMatcher(None, text, version_text).ratio()
        shared_requirements = linked_requirements & set(version.get("requirement_version_ids", []))
        direct = defect.get("linked_test_case_version_id") == version["_id"]
        score = min(
            1,
            similarity * 0.7
            + (0.25 if shared_requirements else 0)
            + (0.3 if direct else 0),
        )
        if score < 0.3:
            continue
        reasons = []
        if direct:
            reasons.append('CURRENT_LINK')
        if shared_requirements:
            reasons.append('SHARED_REQUIREMENT_TRACE')
        if similarity >= 0.35:
            reasons.append('SIMILAR_BEHAVIOR_TEXT')
        test_case_candidates.append(
            {
                "candidate_id": f"test_case_version:{version['_id']}",
                "artifact_type": 'test_case_version',
                "artifact_id": version["_id"],
                "test_case_id": version["test_case_id"],
                "test_case_version_id": version["_id"],
                "test_case_key": version["test_case_key"],
                "title": version["title"],
                "requirement_version_ids": version.get("requirement_version_ids", []),
                "confidence": round(score, 4),
                "confidence_band": confidence_band(score),
                "reason_codes": reasons,
                "evidence": [
                    {
                        "artifact_type": 'defect',
                        "artifact_id": defect["_id"],
                    },
                    {
                        "artifact_type": 'test_case_version',
                        "artifact_id": version["_id"],
                    },
                ],
                "proposed_change": {
                    "operation": 'SET_TEST_CASE_LINK',
                    "linked_test_case_version_id": version["_id"],
                },
            }
        )
    requirement_candidates.sort(key=lambda item: item["confidence"], reverse=True)
    test_case_candidates.sort(key=lambda item: item["confidence"], reverse=True)
    
    return requirement_candidates[:50], test_case_candidates[:50]
