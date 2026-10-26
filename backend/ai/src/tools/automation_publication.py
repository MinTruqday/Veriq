from src.tools.testing_api import AutomationOperationError, require_operation


def _same_unique_values(left, right):
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    if any(
        not isinstance(value, str) or not value.strip() for value in (*left, *right)
    ):
        return False
    return (
        len(left) == len(set(left))
        and len(right) == len(set(right))
        and set(left) == set(right)
    )


def _same_evidence_quotes(left, right):
    if not isinstance(left, list) or not isinstance(right, list):
        return False

    def identities(values):
        result = []
        for value in values:
            if not isinstance(value, dict):
                return None
            reference = value.get("evidence_ref")
            quote = value.get("quote")
            if not isinstance(reference, str) or not reference.strip():
                return None
            if not isinstance(quote, str) or not quote.strip():
                return None
            result.append((reference, quote))
        return result

    left_ids = identities(left)
    right_ids = identities(right)
    return (
        left_ids is not None
        and right_ids is not None
        and len(left_ids) == len(set(left_ids))
        and len(right_ids) == len(set(right_ids))
        and set(left_ids) == set(right_ids)
    )


def _same_authored_test_case_content(draft, version):
    defaults = {
        "test_case_key": None,
        "title": None,
        "type": "happy_path",
        "test_level": None,
        "test_kind": None,
        "expected_impact": "unassessed",
        "assessment_reason": "",
        "priority": "unassessed",
        "risk": "unassessed",
        "objective_doc": {"type": "doc", "content": []},
        "preconditions_doc": {"type": "doc", "content": []},
        "steps": [],
        "test_data": {},
        "expected_result_doc": {"type": "doc", "content": []},
        "postconditions_doc": {"type": "doc", "content": []},
        "tags": [],
        "required_skills": [],
        "custom_values": {},
        "owner_id": None,
        "techniques": [],
        "automation_status": "manual",
        "attachments": [],
        "data_set_version_ids": [],
        "requirement_version_ids": [],
        "acceptance_criterion_ids": [],
        "coverage_item_ids": [],
        "test_condition_ids": [],
        "scenario_id": None,
        "repository_node_id": None,
        "bdd": None,
        "coverage_obligations": [],
        "evidence_refs": [],
        "evidence_quotes": [],
        "challenge_hypotheses": [],
        "ai_proposal_snapshot": None,
        "review_acceptance_criteria_snapshot_ids": None,
        "merge_decision_ids": [],
        "parent_version_id": None,
    }

    def canonical(value, field):
        default = defaults[field]
        if field not in value or (
            value.get(field) is None and isinstance(default, (list, dict))
        ):
            return default
        return value[field]

    if any(
        canonical(draft, field) != canonical(version, field)
        for field in defaults
        if field != "owner_id"
    ):
        return False
    expected_owner = draft.get("owner_id") or draft.get("created_by")
    if expected_owner != canonical(version, "owner_id"):
        return False
    expected_source_evidence = (
        draft.get("source_evidence", [])
        if draft.get("origin", "manual") != "ai_generated"
        or draft.get("evidence_refs")
        else []
    )
    frozen_source_evidence = version.get("source_evidence", [])
    if frozen_source_evidence is None:
        frozen_source_evidence = []
    if expected_source_evidence != frozen_source_evidence:
        return False
    return True


def verified_test_case_publication_readback(
    project_id, expected_case, expected_version, case_readback, version_readback
):
    version_id = str(expected_version.get("_id") or "")
    case_id = str(expected_case.get("_id") or "")
    if not version_id or not case_id:
        return False
    if (
        expected_case.get("project_id") != project_id
        or expected_case.get("status") != "ACTIVE"
        or expected_case.get("current_version_id") != version_id
        or expected_version.get("project_id") != project_id
        or expected_version.get("test_case_id") != case_id
        or expected_version.get("status") != "ACTIVE"
        or case_readback.get("_id") != case_id
        or case_readback.get("project_id") != project_id
        or case_readback.get("status") != "ACTIVE"
        or case_readback.get("current_version_id") != version_id
        or version_readback.get("_id") != version_id
        or version_readback.get("project_id") != project_id
        or version_readback.get("test_case_id") != case_id
        or version_readback.get("status") != "ACTIVE"
    ):
        return False
    return all(
        _same_unique_values(expected_version.get(field), version_readback.get(field))
        for field in ("requirement_version_ids", "coverage_obligations", "evidence_refs")
    ) and _same_evidence_quotes(
        expected_version.get("evidence_quotes"), version_readback.get("evidence_quotes")
    ) and _same_authored_test_case_content(expected_version, version_readback)


async def publish_grounded_requirement(
    project_id, requirement, version, config, before_write=None
):
    """Publish a Requirement after the Testing service's deterministic gates pass."""
    if version.get("status") == "BASELINED":
        return version
    if version.get("status") == "DRAFT":
        if before_write is not None:
            await before_write()
        version = await require_operation(
            "POST",
            f"/du-an/{project_id}/yeu-cau/{requirement['_id']}/gui-ra-soat",
            config,
            {
                "expected_revision": version["revision"],
                "review_note": "AI tự động kiểm tra nguồn, cấu trúc và tiêu chí trước khi đưa vào sử dụng",
            },
        )
    if version.get("status") != "IN_REVIEW":
        raise AutomationOperationError("REQUIREMENT_STATE_NOT_AUTOMATABLE")
    if before_write is not None:
        await before_write()
    version = await require_operation(
        "POST",
        f"/phien-ban-yeu-cau/{version['_id']}/chot-chuan",
        config,
        {
            "expected_revision": version["revision"],
            "review_note": "Tự động công bố sau khi kiểm tra nguồn, câu hỏi làm rõ và chất lượng đều đạt",
        },
    )
    if (
        version.get("status") != "BASELINED"
        or version.get("_id") != requirement.get("current_version_id", version.get("_id"))
        or version.get("requirement_id") != requirement.get("_id")
        or version.get("project_id") != project_id
    ):
        raise RuntimeError("REQUIREMENT_PUBLICATION_READBACK_INVALID")
    return version


async def publish_grounded_test_case(project_id, draft, config, before_write=None):
    """Freeze an AI-created draft after independent source and quality checks."""
    draft_status = draft.get("status", "DRAFT")
    if draft_status == "IN_REVIEW":
        reviewed = draft
    elif draft_status == "DRAFT":
        if before_write is not None:
            await before_write()
        reviewed = await require_operation(
            "POST",
            f"/du-an/{project_id}/ca-kiem-thu/{draft['_id']}/gui-ra-soat",
            config,
            {
                "expected_revision": draft["revision"],
                "review_note": "AI tự động rà nguồn, trùng lặp và chất lượng trước khi công bố",
            },
        )
    else:
        raise AutomationOperationError("TEST_CASE_DRAFT_STATE_NOT_RESUMABLE")
    if reviewed.get("status") != "IN_REVIEW":
        raise RuntimeError("TEST_CASE_REVIEW_READBACK_INVALID")
    if (
        reviewed.get("_id") != draft.get("_id")
        or reviewed.get("project_id") != project_id
        or not isinstance(reviewed.get("revision"), int)
        or isinstance(reviewed.get("revision"), bool)
        or reviewed["revision"] <= 0
    ):
        raise RuntimeError("TEST_CASE_REVIEW_READBACK_INVALID")
    if before_write is not None:
        await before_write()
    result = await require_operation(
        "POST",
        f"/du-an/{project_id}/ca-kiem-thu/{draft['_id']}/phe-duyet",
        config,
        {
            "expected_revision": reviewed["revision"],
            "change_reason": "Tự động công bố ca kiểm thử đã qua kiểm tra nguồn và chất lượng",
            "review_note": "Tự động công bố theo chính sách luồng AI của dự án",
        },
    )
    data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(data, dict) and isinstance(result, dict):
        data = result
    case = data.get("test_case") if isinstance(data, dict) else None
    version = data.get("version") if isinstance(data, dict) else None
    if (
        not case
        or not version
        or case.get("project_id") != project_id
        or case.get("status") != "ACTIVE"
        or not case.get("current_version_id")
        or version.get("_id") != case.get("current_version_id")
        or version.get("test_case_id") != case.get("_id")
        or version.get("status") != "ACTIVE"
        or not _same_unique_values(
            draft.get("requirement_version_ids", []),
            version.get("requirement_version_ids", []),
        )
        or not _same_unique_values(
            draft.get("coverage_obligations", []),
            version.get("coverage_obligations", []),
        )
        or not _same_unique_values(
            draft.get("evidence_refs", []), version.get("evidence_refs", [])
        )
        or not _same_evidence_quotes(
            draft.get("evidence_quotes", []), version.get("evidence_quotes", [])
        )
        or not _same_authored_test_case_content(draft, version)
    ):
        raise RuntimeError("TEST_CASE_PUBLICATION_READBACK_INVALID")
    return case, version, result.get("status", "SUCCESS")
