import json


def consolidate_duplicate_test_case_drafts(drafts, comparisons):
    parents = list(range(len(drafts)))
    duplicate_pairs = set()

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for comparison in comparisons:
        left = comparison.get("left_index") if isinstance(comparison, dict) else None
        right = comparison.get("right_index") if isinstance(comparison, dict) else None
        if (
            not isinstance(left, int)
            or isinstance(left, bool)
            or not isinstance(right, int)
            or isinstance(right, bool)
            or left == right
            or left < 0
            or right < 0
            or left >= len(drafts)
            or right >= len(drafts)
        ):
            return [], 0, [
                {
                    "reason": "DUPLICATE_COMPARISON_INDEX_INVALID",
                    "candidate_indexes": [],
                }
            ]
        left_root, right_root = root(left), root(right)
        duplicate_pairs.add((min(left, right), max(left, right)))
        if left_root != right_root:
            parents[right_root] = left_root

    groups = {}
    for index in range(len(drafts)):
        groups.setdefault(root(index), []).append(index)

    merged = []
    unresolved = []
    for indexes in groups.values():
        candidates = [drafts[index] for index in indexes]
        if len(candidates) == 1:
            merged.append(candidates[0])
            continue
        if any(
            (min(left, right), max(left, right)) not in duplicate_pairs
            for offset, left in enumerate(indexes)
            for right in indexes[offset + 1 :]
        ):
            unresolved.append(
                {
                    "reason": "DUPLICATE_RELATIONSHIP_NOT_TRANSITIVE",
                    "candidate_indexes": indexes,
                }
            )
            continue
        targets = {
            str(item.get("target_version_id"))
            for item in candidates
            if item.get("target_version_id")
        }
        if len(targets) > 1:
            unresolved.append(
                {
                    "reason": "DUPLICATE_MAINTENANCE_TARGET_CONFLICT",
                    "candidate_indexes": indexes,
                }
            )
            continue
        requirement_scopes = {
            tuple(sorted(item.get("requirement_version_ids") or []))
            for item in candidates
        }
        if len(requirement_scopes) > 1 or any(
            item.get("challenge_hypotheses") for item in candidates
        ):
            unresolved.append(
                {
                    "reason": "DUPLICATE_CANDIDATE_SCOPE_REQUIRES_REGENERATION",
                    "candidate_indexes": indexes,
                }
            )
            continue
        representative = max(
            candidates,
            key=lambda item: (
                len(item.get("coverage_obligations") or []),
                len(item.get("acceptance_criterion_ids") or []),
                len(item.get("evidence_quotes") or []),
            ),
        )
        combined = dict(representative)
        for field in (
            "acceptance_criterion_ids",
            "coverage_item_ids",
            "coverage_obligations",
            "evidence_refs",
            "evidence_quotes",
        ):
            values = []
            seen = set()
            for candidate in candidates:
                for value in candidate.get(field) or []:
                    key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                    if key not in seen:
                        seen.add(key)
                        values.append(value)
            if values:
                combined[field] = values
        evidence_by_identity = {}
        for candidate in candidates:
            for evidence in candidate.get("source_evidence") or []:
                if not isinstance(evidence, dict):
                    continue
                key = json.dumps(
                    evidence, ensure_ascii=False, sort_keys=True, default=str
                )
                evidence_by_identity.setdefault(key, evidence)
        if evidence_by_identity:
            combined["source_evidence"] = list(evidence_by_identity.values())
        limits = {
            "acceptance_criterion_ids": 500,
            "coverage_item_ids": 500,
            "coverage_obligations": 100,
            "evidence_refs": 200,
            "evidence_quotes": 20,
        }
        if any(len(combined.get(field) or []) > limit for field, limit in limits.items()):
            unresolved.append(
                {
                    "reason": "DUPLICATE_TRACE_MERGE_LIMIT_EXCEEDED",
                    "candidate_indexes": indexes,
                }
            )
            continue
        merged.append(combined)
    return merged, len(drafts) - len(merged) - len(unresolved), unresolved
