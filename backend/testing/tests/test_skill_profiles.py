import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from src.modules.projects.services import skill_profiles
from src.modules.projects.services.skill_profiles import _public_profile, rank_skill_candidates
from src.repositories.skill_profile import SkillProfileRepository
from src.schemas.contracts.skill_profile import (
    AssignmentRecommendationInput,
    ConfirmedSkill,
    RelevantExperience,
    SkillProfilePatch,
)
from src.schemas.contracts.execution import TestRunCreate as RunCreateInput


def test_test_run_defaults_to_source_grounded_profile_assignment():
    payload = RunCreateInput(project_id="project-a", name="Run kiểm thử")

    assert payload.assignment_strategy == "PROFILE_EVIDENCE"
    assert RunCreateInput(
        project_id="project-a",
        name="Run thủ công",
        assignment_strategy="MANUAL",
    ).assignment_strategy == "MANUAL"


def test_test_case_owner_recommendation_does_not_require_price_or_payroll(monkeypatch):
    class Projects:
        async def find_one(self, *_args, **_kwargs):
            return {"_id": "project-a", "locale": "vi-VN"}

    class PayrollRates:
        def find(self, *_args, **_kwargs):
            raise AssertionError("Payroll query must not run without project currency")

    monkeypatch.setattr(
        type(skill_profiles.database),
        "value",
        property(lambda _self: SimpleNamespace(projects=Projects(), payroll_rates=PayrollRates())),
    )
    monkeypatch.setattr(skill_profiles, "get_project", _async_value({}))
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value([{"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"}]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([{"user_id": "tester-a", "availability": "AVAILABLE", "skills": []}]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))
    monkeypatch.setattr(
        skill_profiles,
        "load_user_identities",
        _async_value({"tester-a": {"label": "Tester A"}}),
    )
    monkeypatch.setattr(
        skill_profiles.ai_automation_client,
        "recommend_test_case_owners",
        AsyncMock(return_value={
            "recommendations": [{
                "candidate_id": "tester-a",
                "reason": "Đang khả dụng và có tải công việc hiện tại thấp.",
                "supporting_facts": ["availability", "active-cases"],
            }],
            "warnings": ["Chưa có bảng lương theo tiền tệ của dự án."],
        }),
    )

    result = asyncio.run(
        skill_profiles.recommend_test_case_owner(
            "project-a",
            SimpleNamespace(draft_id=None, required_skills=[]),
            SimpleNamespace(id="qa"),
        )
    )

    assert result["status"] == "CANDIDATES_FOUND"
    assert result["payroll_data_status"] == "MISSING_PROJECT_CURRENCY"
    assert result["recommended_user_id"] == "tester-a"
    assert result["candidates"][0]["payroll_rate_available"] is False
    assert result["candidates"][0]["score_0_to_1"] == 0.833
    assert result["candidates"][0]["ai_supporting_facts"]
    assert result["recommendation_engine"] == "AI"
    assert result["applies_automatically"] is False


def test_owner_recommendation_matches_ranked_candidate_when_ai_order_conflicts(monkeypatch):
    class Projects:
        async def find_one(self, *_args, **_kwargs):
            return {"_id": "project-a", "locale": "en-US"}

    class PayrollRates:
        def find(self, *_args, **_kwargs):
            raise AssertionError("Payroll query must not run without project currency")

    monkeypatch.setattr(
        type(skill_profiles.database),
        "value",
        property(lambda _self: SimpleNamespace(projects=Projects(), payroll_rates=PayrollRates())),
    )
    monkeypatch.setattr(skill_profiles, "get_project", _async_value({}))
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value([
            {"user_id": "loaded-tester", "status": "ACTIVE", "project_role": "TESTER"},
            {"user_id": "lightly-loaded-tester", "status": "ACTIVE", "project_role": "TESTER"},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([
            {"user_id": "loaded-tester", "availability": "AVAILABLE", "skills": [
                {"name": "Python", "level": "ADVANCED", "confirmed": True}
            ]},
            {"user_id": "lightly-loaded-tester", "availability": "AVAILABLE", "skills": [
                {"name": "Python", "level": "INTERMEDIATE", "confirmed": True}
            ]},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "iter_active_runs_for_members",
        _async_iter([{
            "project_id": "project-a",
            "status": "IN_PROGRESS",
            "assignee_id": "loaded-tester",
            "test_case_assignments": {},
        }]),
    )
    monkeypatch.setattr(
        skill_profiles,
        "load_user_identities",
        _async_value({
            "loaded-tester": {"label": "Loaded tester"},
            "lightly-loaded-tester": {"label": "Lightly loaded tester"},
        }),
    )
    monkeypatch.setattr(
        skill_profiles.ai_automation_client,
        "recommend_test_case_owners",
        AsyncMock(return_value={
            "recommendations": [
                {"candidate_id": "loaded-tester", "reason": "AI order", "supporting_facts": ["availability"]},
                {"candidate_id": "lightly-loaded-tester", "reason": "AI order", "supporting_facts": ["availability"]},
            ],
            "warnings": [],
        }),
    )

    result = asyncio.run(
        skill_profiles.recommend_test_case_owner(
            "project-a",
            SimpleNamespace(draft_id=None, required_skills=["Python"]),
            SimpleNamespace(id="qa"),
        )
    )

    assert result["candidates"][0]["user_id"] == "lightly-loaded-tester"
    assert result["candidates"][0]["active_run_count"] == 0
    assert result["candidates"][1]["user_id"] == "loaded-tester"
    assert result["candidates"][1]["active_run_count"] == 1
    assert result["recommended_user_id"] == result["candidates"][0]["user_id"]
    assert result["recommended_user_label"] == result["candidates"][0]["user_label"]


def test_payroll_rates_are_normalized_before_the_staffing_model_and_not_returned(monkeypatch):
    class RateCursor:
        def sort(self, *_args, **_kwargs):
            return self

        async def to_list(self, _limit):
            return [
                {"user_id": "tester-a", "hourly_cost": "100.00", "currency": "VND"},
                {"user_id": "tester-b", "hourly_cost": "200.00", "currency": "VND"},
            ]

    class PayrollRates:
        def find(self, *_args, **_kwargs):
            return RateCursor()

    class Projects:
        async def find_one(self, *_args, **_kwargs):
            return {"_id": "project-a", "locale": "en-US", "commercial_terms": {"currency": "VND"}}

    monkeypatch.setattr(
        type(skill_profiles.database),
        "value",
        property(lambda _self: SimpleNamespace(projects=Projects(), payroll_rates=PayrollRates())),
    )
    monkeypatch.setattr(skill_profiles, "get_project", _async_value({}))
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value([
            {"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"},
            {"user_id": "tester-b", "status": "ACTIVE", "project_role": "TESTER"},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([
            {"user_id": "tester-a", "availability": "AVAILABLE", "skills": []},
            {"user_id": "tester-b", "availability": "AVAILABLE", "skills": []},
        ]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))
    monkeypatch.setattr(
        skill_profiles,
        "load_user_identities",
        _async_value({"tester-a": {"label": "Tester A"}, "tester-b": {"label": "Tester B"}}),
    )
    model_call = AsyncMock(side_effect=lambda _project, _locale, _skills, candidates: {
        "recommendations": [
            {
                "candidate_id": item["candidate_id"],
                "reason": "The candidate matches the current evidence.",
                "supporting_facts": ["availability"],
            }
            for item in candidates
        ],
        "warnings": [],
    })
    monkeypatch.setattr(skill_profiles.ai_automation_client, "recommend_test_case_owners", model_call)

    result = asyncio.run(
        skill_profiles.recommend_test_case_owner(
            "project-a",
            SimpleNamespace(draft_id=None, required_skills=[]),
            SimpleNamespace(id="qa"),
        )
    )

    model_candidates = model_call.await_args.args[3]
    assert {item["payroll_cost_factor"] for item in model_candidates} == {0.0, 1.0}
    assert all("hourly_cost" not in item and "currency" not in item for item in model_candidates)
    assert "100.00" not in repr(result) and "200.00" not in repr(result)
    assert all("100.00" not in repr(item) and "200.00" not in repr(item) for item in model_candidates)


def test_assignment_only_uses_explicitly_confirmed_skills_and_availability():
    members = [
        {"user_id": "available", "status": "ACTIVE", "project_role": "TESTER"},
        {"user_id": "unconfirmed", "status": "ACTIVE", "project_role": "TESTER"},
        {"user_id": "unavailable", "status": "ACTIVE", "project_role": "TESTER"},
    ]
    profiles = [
        {
            "user_id": "available",
            "availability": "AVAILABLE",
            "skills": [{
                "name": "API testing",
                "level": "INTERMEDIATE",
                "evidence": "Designed API regression suites",
                "source_block_id": "cv-block-3",
                "source_page_no": 2,
                "confirmed": True,
            }],
        },
        {
            "user_id": "unconfirmed",
            "availability": "AVAILABLE",
            "skills": [{"name": "API testing", "confirmed": False}],
        },
        {
            "user_id": "unavailable",
            "availability": "UNAVAILABLE",
            "skills": [{"name": "API testing", "confirmed": True}],
        },
    ]

    required, ranked = rank_skill_candidates(members, profiles, {"available": 2}, [" API   Testing "])

    assert required == ["api testing"]
    assert [item["user_id"] for item in ranked] == ["available"]
    assert ranked[0]["matched_skills"] == ["API testing"]
    assert ranked[0]["matched_skill_evidence"] == [{
        "name": "API testing",
        "level": "INTERMEDIATE",
        "source_kind": "MEMBER_DECLARED",
        "confirmed": True,
    }]
    assert ranked[0]["active_run_count"] == 2


def test_assignment_without_required_skills_returns_members_but_not_unavailable():
    members = [
        {"user_id": "member-a", "status": "ACTIVE", "project_role": "TESTER"},
        {"user_id": "member-b", "status": "ACTIVE", "project_role": "TESTER"},
    ]

    required, ranked = rank_skill_candidates(
        members,
        [{"user_id": "member-b", "availability": "UNAVAILABLE"}],
        {},
        [],
    )

    assert required == []
    assert [item["user_id"] for item in ranked] == ["member-a"]
    assert ranked[0]["profile_exists"] is False


def test_profile_schema_defaults_unassessed_skills_and_requires_confirmation():
    profile = SkillProfilePatch(
        expected_revision=0,
        skills=[{"name": "  API   testing ", "confirmed": True}],
    )
    assert profile.skills[0].name == "API testing"
    assert profile.skills[0].confirmed is True
    assert profile.skills[0].level == "NOT_ASSESSED"
    with pytest.raises(ValidationError):
        ConfirmedSkill(name="", level="EXPERT")


def test_profile_schema_rejects_duplicate_skill_names_case_insensitively():
    with pytest.raises(ValidationError, match="skill_profile_duplicate_skill_name"):
        SkillProfilePatch(
            expected_revision=0,
            skills=[
                {"name": "API Testing", "confirmed": True},
                {"name": " api   testing ", "confirmed": False},
            ],
        )


def test_profile_schema_preserves_structured_cv_source_provenance():
    profile = SkillProfilePatch(
        expected_revision=0,
        skills=[
            {
                "name": "API testing",
                "evidence": "API testing: validated REST APIs",
                "source_block_id": "#/pages/4/blocks/2",
                "source_page_no": 4,
            }
        ],
        experiences=[
            {
                "title": "QA Engineer",
                "evidence": "QA Engineer validated releases",
                "source_block_id": "#/pages/5/blocks/1",
                "source_page_no": 5,
            }
        ],
    )

    assert profile.skills[0].source_block_id == "#/pages/4/blocks/2"
    assert profile.skills[0].source_page_no == 4
    assert profile.experiences[0].source_block_id == "#/pages/5/blocks/1"
    assert profile.experiences[0].source_page_no == 5


@pytest.mark.parametrize(
    "model, values",
    [
        (ConfirmedSkill, {"name": "API", "source_page_no": 2}),
        (ConfirmedSkill, {"name": "API", "source_block_id": "block-1"}),
        (ConfirmedSkill, {"name": "API", "source_sha256": "a" * 64}),
        (RelevantExperience, {"title": "QA", "source_page_no": 2}),
        (RelevantExperience, {"title": "QA", "source_block_id": "block-1"}),
        (RelevantExperience, {"title": "QA", "source_sha256": "a" * 64}),
    ],
)
def test_profile_source_metadata_requires_a_cited_evidence_pair(model, values):
    with pytest.raises(ValidationError):
        model(**values)


@pytest.mark.parametrize(
    "model, values",
    [
        (
            ConfirmedSkill,
            {
                "name": "Python expert",
                "evidence": "Used Python in test automation",
                "source_block_id": "cv-block-1",
                "source_sha256": "a" * 64,
            },
        ),
        (
            RelevantExperience,
            {
                "title": "QA Engineer",
                "domain": "Banking",
                "technologies": ["Playwright"],
                "evidence": "QA Engineer used Playwright",
                "source_block_id": "cv-block-1",
                "source_sha256": "a" * 64,
            },
        ),
    ],
)
def test_profile_source_provenance_cannot_be_kept_for_edited_unsupported_claims(model, values):
    with pytest.raises(ValidationError):
        model(**values)


def test_profile_source_claim_requires_a_token_boundary():
    with pytest.raises(ValidationError):
        ConfirmedSkill(
            name="Java",
            evidence="JavaScript automation experience",
            source_block_id="cv-block-1",
        )

    profile = ConfirmedSkill(
        name="JavaScript",
        evidence="JavaScript automation experience",
        source_block_id="cv-block-1",
    )
    assert profile.name == "JavaScript"


def test_cv_extraction_claim_requires_a_token_boundary():
    source_blocks = [{
        "block_id": "cv-block-1",
        "page_no": 2,
        "text": "JavaScript automation experience",
    }]
    extracted = {
        "skills": [{
            "name": "Java",
            "evidence_quote": "JavaScript automation experience",
            "source_block_id": "cv-block-1",
            "page_no": 2,
        }],
        "experiences": [],
    }

    assert skill_profiles._validate_cv_candidate_evidence(source_blocks, extracted) is False


def test_test_run_assignment_strategy_preserves_manual_default_and_supports_agent_mode():
    common = {"project_id": "project-a", "name": "Run kiểm thử"}
    assert RunCreateInput(**common).assignment_strategy == "PROFILE_EVIDENCE"
    assert RunCreateInput(**common, assignment_strategy="MANUAL").assignment_strategy == "MANUAL"
    assert RunCreateInput(**common, assignment_strategy="CONFIRMED_SKILLS").assignment_strategy == "CONFIRMED_SKILLS"
    assert RunCreateInput(**common, assignment_strategy="PROFILE_EVIDENCE").assignment_strategy == "PROFILE_EVIDENCE"
    with pytest.raises(ValidationError):
        RunCreateInput(**common, assignment_strategy="GUESS_FROM_CV")


def test_public_profile_does_not_expose_unrecognized_private_fields():
    profile = {
        "project_id": "project-a",
        "user_id": "member-a",
        "skills": [],
        "experiences": [],
        "availability": "AVAILABLE",
        "revision": 3,
        "updated_at": "now",
        "private_cv_storage_key": "private/cv.pdf",
        "raw_cv_text": "private content",
    }

    public = _public_profile(profile)

    assert "private_cv_storage_key" not in public
    assert "raw_cv_text" not in public


def test_profile_patch_preserves_exact_persisted_cv_sources_when_member_confirms_them():
    source_hash = "a" * 64
    existing = {
        "skills": [{
            "name": "Playwright",
            "evidence": "Used Playwright for browser testing",
            "source_block_id": "cv:4:2",
            "source_page_no": 4,
            "source_sha256": source_hash,
            "source_kind": "CV_EXTRACTED",
            "confirmed": False,
        }],
        "experiences": [{
            "title": "QA Engineer",
            "period": "2022-2024",
            "domain": "Banking",
            "technologies": ["Playwright"],
            "responsibilities": "Validated releases",
            "evidence": "QA Engineer in Banking validated releases",
            "source_block_id": "cv:5:1",
            "source_page_no": 5,
            "source_sha256": source_hash,
            "source_kind": "CV_EXTRACTED",
            "confirmed": False,
        }],
    }
    changes = {
        "skills": [{
            "name": "Playwright",
            "level": "INTERMEDIATE",
            "evidence": "Used Playwright for browser testing",
            "source_block_id": "cv:4:2",
            "source_page_no": 4,
            "source_sha256": source_hash,
            "source_kind": "MEMBER_DECLARED",
            "confirmed": True,
        }],
        "experiences": [{
            **{key: value for key, value in existing["experiences"][0].items() if key != "confirmed"},
            "confirmed": True,
        }],
    }

    updated = skill_profiles._profile_patch_with_trusted_sources(changes, existing)

    assert updated["skills"][0]["source_kind"] == "CV_EXTRACTED"
    assert updated["skills"][0]["confirmed"] is True
    assert updated["experiences"][0]["source_kind"] == "CV_EXTRACTED"
    assert updated["experiences"][0]["confirmed"] is True


@pytest.mark.parametrize("field,value", [
    ("evidence", "I claim Playwright without a source quote"),
    ("source_block_id", "other-document:1"),
    ("source_sha256", "b" * 64),
])
def test_profile_patch_downgrades_modified_or_spoofed_cv_skill_provenance(field, value):
    stored = {
        "name": "Playwright",
        "evidence": "Used Playwright for browser testing",
        "source_block_id": "cv:4:2",
        "source_page_no": 4,
        "source_sha256": "a" * 64,
        "source_kind": "CV_EXTRACTED",
    }
    submitted = {**stored, field: value, "source_kind": "CV_EXTRACTED"}
    changes = {"skills": [submitted], "experiences": []}

    updated = skill_profiles._profile_patch_with_trusted_sources(
        changes, {"skills": [stored], "experiences": []}
    )

    assert updated["skills"][0]["source_kind"] == "MEMBER_DECLARED"
    assert updated["skills"][0]["source_block_id"] is None
    assert updated["skills"][0]["source_page_no"] is None
    assert updated["skills"][0]["source_sha256"] is None


def test_profile_patch_cannot_claim_cv_source_without_a_persisted_source():
    changes = {
        "skills": [{
            "name": "Python",
            "evidence": "Python testing",
            "source_block_id": "invented:1",
            "source_page_no": 1,
            "source_sha256": "a" * 64,
            "source_kind": "CV_EXTRACTED",
        }],
        "experiences": [],
    }

    updated = skill_profiles._profile_patch_with_trusted_sources(changes, None)

    assert updated["skills"][0]["source_kind"] == "MEMBER_DECLARED"
    assert updated["skills"][0]["source_block_id"] is None
    assert updated["skills"][0]["source_page_no"] is None
    assert updated["skills"][0]["source_sha256"] is None


def test_new_cv_without_extractable_facts_replaces_old_cv_facts_and_keeps_declared_skills(monkeypatch):
    existing = {
        "project_id": "project-a",
        "user_id": "member-a",
        "skills": [
            {"name": "Python", "source_kind": "MEMBER_DECLARED", "confirmed": True},
            {"name": "Selenium", "source_kind": "CV_EXTRACTED", "source_sha256": "a" * 64},
        ],
        "experiences": [{
            "title": "Old QA role",
            "source_kind": "CV_EXTRACTED",
            "source_sha256": "a" * 64,
        }],
        "availability": "LIMITED",
        "revision": 4,
    }
    calls = {}

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, error_type, error, traceback):
            return False

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, error_type, error, traceback):
            return False

        def start_transaction(self):
            return Transaction()

    session = Session()

    async def start_session():
        return session

    async def find(project_id, user_id):
        assert (project_id, user_id) == ("project-a", "member-a")
        return existing

    async def upsert(project_id, user_id, expected_revision, changes, timestamp, *, session):
        calls.update(changes=changes, expected_revision=expected_revision, session=session)
        return {
            "project_id": project_id,
            "user_id": user_id,
            **changes,
            "revision": expected_revision + 1,
            "updated_at": timestamp,
        }

    async def audit(*args, session=None, **kwargs):
        calls["audit_session"] = session

    monkeypatch.setattr(skill_profiles.skill_profile_repository, "find", find)
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "upsert", upsert)
    monkeypatch.setattr(skill_profiles.database, "client", SimpleNamespace(start_session=start_session))
    monkeypatch.setattr(skill_profiles, "audit", audit)

    updated, changed = asyncio.run(
        skill_profiles._persist_cv_profile(
            "project-a",
            SimpleNamespace(id="member-a"),
            {"skills": [], "experiences": []},
            "b" * 64,
        )
    )

    assert changed is True
    assert updated["skills"] == [existing["skills"][0]]
    assert updated["experiences"] == []
    assert updated["availability"] == "LIMITED"
    assert calls["expected_revision"] == 4
    assert calls["session"] is session
    assert calls["audit_session"] is session


def test_profile_update_uses_optimistic_revision_and_only_own_identity(monkeypatch):
    calls = {}
    monkeypatch.setattr(skill_profiles, "get_project", _async_value(None))
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "find", _async_value(None))

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, error_type, error, traceback):
            return False

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, error_type, error, traceback):
            return False

        def start_transaction(self):
            return Transaction()

    session = Session()

    async def start_session():
        return session

    monkeypatch.setattr(
        skill_profiles.database,
        "client",
        SimpleNamespace(start_session=start_session),
    )

    async def upsert(project_id, user_id, expected_revision, changes, timestamp, *, session):
        calls.update(project_id=project_id, user_id=user_id, expected_revision=expected_revision)
        calls["upsert_session"] = session
        return {
            "project_id": project_id,
            "user_id": user_id,
            **changes,
            "revision": 1,
            "updated_at": timestamp,
        }

    monkeypatch.setattr(skill_profiles.skill_profile_repository, "upsert", upsert)
    async def audit(*args, session=None, **kwargs):
        calls["audit_session"] = session

    monkeypatch.setattr(skill_profiles, "audit", audit)
    user = type("User", (), {"id": "member-a"})()
    saved = asyncio.run(
        skill_profiles.update_own_skill_profile(
            "project-a",
            SkillProfilePatch(expected_revision=0, skills=[{"name": "API", "level": "ADVANCED", "confirmed": True}]),
            user,
        )
    )

    assert {
        key: calls[key]
        for key in ("project_id", "user_id", "expected_revision")
    } == {"project_id": "project-a", "user_id": "member-a", "expected_revision": 0}
    assert calls["upsert_session"] is session
    assert calls["audit_session"] is session
    assert saved["user_id"] == "member-a"
    assert saved["revision"] == 1


def test_assignment_recommendation_is_project_scoped_and_only_considers_testers(monkeypatch):
    monkeypatch.setattr(
        skill_profiles,
        "get_project_entity",
        _async_value({"_id": "run-a", "project_id": "project-a"}),
    )
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value(
            [
                {"user_id": "tester", "status": "ACTIVE", "project_role": "TESTER"},
                {"user_id": "developer", "status": "ACTIVE", "project_role": "DEVELOPER"},
            ]
        ),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([{"user_id": "tester", "skills": [{"name": "API", "confirmed": True}]}]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "iter_active_runs_for_members",
        _async_iter([]),
    )
    monkeypatch.setattr(skill_profiles.test_run_repository, "list_versions", _async_value([]))
    monkeypatch.setattr(skill_profiles, "load_user_identities", _async_value({"tester": {"label": "Tester"}}))
    user = type("User", (), {"id": "qa"})()

    result = asyncio.run(
        skill_profiles.recommend_test_run_assignments(
            "project-a", "run-a", AssignmentRecommendationInput(required_skills=["API"]), user
        )
    )

    assert [item["user_id"] for item in result["recommendations"]] == ["tester"]
    assert result["applies_automatically"] is False
    assert result["run_revision"] == 1
    assert result["skill_profile_revisions"] == {"tester": 0}

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            skill_profiles.recommend_test_run_assignments(
                "project-b", "run-a", AssignmentRecommendationInput(), user
            )
        )
    assert error.value.status_code == 422


def test_assignment_recommendation_rejects_a_stale_run_revision(monkeypatch):
    monkeypatch.setattr(
        skill_profiles,
        "get_project_entity",
        _async_value({"_id": "run-a", "project_id": "project-a", "revision": 4}),
    )
    members = AsyncMock()
    monkeypatch.setattr(skill_profiles.project_repository, "list_members", members)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            skill_profiles.recommend_test_run_assignments(
                "project-a",
                "run-a",
                AssignmentRecommendationInput(expected_run_revision=3),
                type("User", (), {"id": "qa"})(),
            )
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "TEST_RUN_CHANGED_RECOMMEND_AGAIN"
    members.assert_not_awaited()


def test_assignment_revision_fence_serializes_profile_edits_in_same_transaction(monkeypatch):
    repository = SkillProfileRepository()
    session = object()
    updates = []

    class Result:
        matched_count = 1
        upserted_id = None

    class Profiles:
        async def update_one(self, selector, update, *, upsert, session):
            updates.append((selector, update, upsert, session))
            return Result()

    monkeypatch.setattr(type(repository), "profiles", property(lambda _self: Profiles()))

    stale = asyncio.run(
        repository.fence_assignment_revisions(
            "project-a", {"tester-a": 7}, "now", session=session
        )
    )

    assert stale == []
    assert updates == [
        (
            {"project_id": "project-a", "user_id": "tester-a", "revision": 7},
            {
                "$inc": {"assignment_fence_revision": 1},
                "$set": {"assignment_fence_updated_at": "now"},
            },
            False,
            session,
        )
    ]


def test_assignment_revision_fence_materializes_a_revision_zero_profile_safely(monkeypatch):
    repository = SkillProfileRepository()
    session = object()
    calls = []

    class Profiles:
        async def update_one(self, selector, update, *, upsert, session):
            calls.append((selector, update, upsert, session))
            return type("Result", (), {"matched_count": 0, "upserted_id": "profile-a"})()

    monkeypatch.setattr(type(repository), "profiles", property(lambda _self: Profiles()))

    stale = asyncio.run(
        repository.fence_assignment_revisions(
            "project-a", {"tester-a": 0}, "now", session=session
        )
    )

    assert stale == []
    assert calls[0][0] == {"project_id": "project-a", "user_id": "tester-a", "revision": 0}
    assert calls[0][1]["$setOnInsert"] == {
        "skills": [],
        "experiences": [],
        "availability": "AVAILABLE",
        "created_at": "now",
    }
    assert calls[0][2] is True
    assert calls[0][3] is session


def test_case_assignment_plan_uses_frozen_case_skills_balances_load_and_preserves_manual(monkeypatch):
    monkeypatch.setattr(
        skill_profiles, "get_project_entity",
        _async_value({
            "_id": "run-a", "project_id": "project-a", "test_case_version_ids": ["v-api", "v-sec", "v-manual"],
            "test_case_assignments": {"v-manual": "tester-sec"},
        }),
    )
    monkeypatch.setattr(
        skill_profiles.project_repository, "list_members",
        _async_value([
            {"user_id": "tester-api", "status": "ACTIVE", "project_role": "TESTER"},
            {"user_id": "tester-sec", "status": "ACTIVE", "project_role": "TESTER"},
            {"user_id": "developer", "status": "ACTIVE", "project_role": "DEVELOPER"},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository, "list_for_members",
        _async_value([
            {"user_id": "tester-api", "revision": 4, "availability": "AVAILABLE", "skills": [{
                "name": "API", "level": "ADVANCED", "evidence": "Built API test strategy",
                "source_block_id": "cv-block-api", "source_page_no": 5, "confirmed": True,
            }]},
            {"user_id": "tester-sec", "availability": "AVAILABLE", "skills": [{"name": "Security", "confirmed": True}]},
        ]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))
    monkeypatch.setattr(
        skill_profiles.test_run_repository, "list_versions",
        _async_value([
            {"_id": "v-api", "project_id": "project-a", "required_skills": ["API"]},
            {"_id": "v-sec", "project_id": "project-a", "required_skills": ["Security"]},
            {"_id": "v-manual", "project_id": "project-a", "required_skills": ["API"]},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles, "load_user_identities",
        _async_value({"tester-api": {"label": "API tester"}, "tester-sec": {"label": "Security tester"}}),
    )

    result = asyncio.run(skill_profiles.recommend_test_run_assignments(
        "project-a", "run-a", AssignmentRecommendationInput(), type("User", (), {"id": "qa"})()
    ))

    by_case = {item["test_case_version_id"]: item for item in result["case_recommendations"]}
    assert by_case["v-api"]["assignee_id"] == "tester-api"
    assert by_case["v-api"]["matched_skill_evidence"] == [{
        "name": "API", "level": "ADVANCED",
        "source_kind": "MEMBER_DECLARED", "confirmed": True,
    }]
    assert by_case["v-sec"]["assignee_id"] == "tester-sec"
    assert by_case["v-manual"]["assignee_id"] == "tester-sec"
    assert by_case["v-manual"]["status"] == "EXISTING_ASSIGNMENT_PRESERVED"
    assert result["assignment_plan_status"] == "READY"
    assert result["applies_automatically"] is False


def test_case_assignment_plan_leaves_case_unassigned_without_full_confirmed_match(monkeypatch):
    monkeypatch.setattr(
        skill_profiles, "get_project_entity",
        _async_value({"_id": "run-a", "project_id": "project-a", "test_case_version_ids": ["v-api"]}),
    )
    monkeypatch.setattr(
        skill_profiles.project_repository, "list_members",
        _async_value([{"user_id": "tester", "status": "ACTIVE", "project_role": "TESTER"}]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository, "list_for_members",
        _async_value([{"user_id": "tester", "availability": "AVAILABLE", "skills": [{"name": "API", "confirmed": True}]}]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))
    monkeypatch.setattr(
        skill_profiles.test_run_repository, "list_versions",
        _async_value([{"_id": "v-api", "project_id": "project-a", "required_skills": ["API", "Security"]}]),
    )
    monkeypatch.setattr(skill_profiles, "load_user_identities", _async_value({"tester": {"label": "Tester"}}))

    result = asyncio.run(skill_profiles.recommend_test_run_assignments(
        "project-a", "run-a", AssignmentRecommendationInput(), type("User", (), {"id": "qa"})()
    ))

    proposal = result["case_recommendations"][0]
    assert proposal["assignee_id"] is None
    assert proposal["status"] == "NO_FULL_SKILL_MATCH"
    assert result["assignment_plan_status"] == "PARTIAL"


def test_case_assignment_recommendation_uses_active_run_load_after_case_load(monkeypatch):
    monkeypatch.setattr(
        skill_profiles, "get_project_entity",
        _async_value({"_id": "run-a", "project_id": "project-a", "test_case_version_ids": ["v-api"]}),
    )
    monkeypatch.setattr(
        skill_profiles.project_repository, "list_members",
        _async_value([
            {"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"},
            {"user_id": "tester-b", "status": "ACTIVE", "project_role": "TESTER"},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository, "list_for_members",
        _async_value([
            {"user_id": "tester-a", "availability": "AVAILABLE", "skills": [{"name": "API", "confirmed": True}]},
            {"user_id": "tester-b", "availability": "AVAILABLE", "skills": [{"name": "API", "confirmed": True}]},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository, "iter_active_runs_for_members",
        _async_iter([
            {
                "assignee_id": "tester-a",
                "test_case_assignments": {
                    "active-version-a": "tester-a",
                    "active-version-b": "tester-a",
                },
            },
            {"assignee_id": "tester-a", "test_case_assignments": {}},
            {"assignee_id": "tester-b", "test_case_assignments": {}},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.test_run_repository, "list_versions",
        _async_value([{"_id": "v-api", "project_id": "project-a", "required_skills": ["API"]}]),
    )
    monkeypatch.setattr(
        skill_profiles, "load_user_identities",
        _async_value({"tester-a": {"label": "A"}, "tester-b": {"label": "B"}}),
    )

    result = asyncio.run(skill_profiles.recommend_test_run_assignments(
        "project-a", "run-a", AssignmentRecommendationInput(), type("User", (), {"id": "qa"})()
    ))

    proposal = result["case_recommendations"][0]
    assert proposal["assignee_id"] == "tester-b"
    assert proposal["candidates"][0]["active_run_count"] == 1
    assert proposal["candidates"][0]["active_case_count"] == 0
    tester_a = next(item for item in proposal["candidates"] if item["user_id"] == "tester-a")
    assert tester_a["active_run_count"] == 2
    assert tester_a["active_case_count"] == 2


def test_automatic_assignment_allocates_restricted_cases_first_and_excludes_unavailable(monkeypatch):
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value([
            {"user_id": "api-tester", "status": "ACTIVE", "project_role": "TESTER"},
            {"user_id": "security-tester", "status": "ACTIVE", "project_role": "TESTER"},
            {"user_id": "unavailable-security", "status": "ACTIVE", "project_role": "TESTER"},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([
            {"user_id": "api-tester", "availability": "AVAILABLE", "skills": [{"name": "API", "confirmed": True}]},
            {"user_id": "security-tester", "availability": "AVAILABLE", "skills": [{"name": "Security", "confirmed": True}]},
            {"user_id": "unavailable-security", "availability": "UNAVAILABLE", "skills": [{"name": "Security", "confirmed": True}]},
        ]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))

    assignments, unresolved, decisions = asyncio.run(skill_profiles.automatically_assign_test_cases(
        "project-a",
        [
            {"_id": "flexible", "required_skills": []},
            {"_id": "specialist", "required_skills": ["Security"]},
            {"_id": "unknown", "required_skills": ["Performance"]},
        ],
    ))

    assert assignments == {"specialist": "security-tester", "flexible": "api-tester"}
    assert unresolved == [{"test_case_version_id": "unknown", "reason": "NO_FULL_SKILL_MATCH"}]
    assert decisions["specialist"]["matched_skills"] == ["Security"]
    assert decisions["specialist"]["skill_profile_revision"] == 0
    assert decisions["specialist"]["availability_at_assignment"] == "AVAILABLE"
    assert decisions["specialist"]["active_run_count_before_assignment"] == 0
    assert decisions["flexible"]["active_run_count_before_assignment"] == 0


def test_automatic_assignment_distinguishes_unconfirmed_profile_from_skill_mismatch(monkeypatch):
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value([
            {"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([
            {
                "user_id": "tester-a",
                "availability": "AVAILABLE",
                "skills": [{"name": "API", "confirmed": False}],
            },
        ]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))

    assignments, unresolved, decisions = asyncio.run(
        skill_profiles.automatically_assign_test_cases(
            "project-a",
            [{"_id": "version-a", "required_skills": ["API"]}],
        )
    )

    assert assignments == {}
    assert decisions == {}
    assert unresolved == [{"test_case_version_id": "version-a", "reason": "PROFILE_NOT_CONFIRMED"}]


def test_profile_evidence_assignment_requires_member_confirmation(monkeypatch):
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value([{"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"}]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([{
            "user_id": "tester-a",
            "revision": 3,
            "availability": "AVAILABLE",
            "skills": [{
                "name": "Postman",
                "confirmed": False,
                "source_kind": "CV_EXTRACTED",
                "source_block_id": "page-1-block-2",
                "source_sha256": "c" * 64,
                "evidence": "Used Postman for API tests",
            }],
        }]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))
    version = {"_id": "version-a", "required_skills": ["Postman"]}

    assignments, unresolved, _ = asyncio.run(
        skill_profiles.automatically_assign_test_cases(
            "project-a", [version]
        )
    )

    assert assignments == {}
    assert unresolved == [{"test_case_version_id": "version-a", "reason": "PROFILE_NOT_CONFIRMED"}]

    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([{
            "user_id": "tester-a",
            "revision": 4,
            "availability": "AVAILABLE",
            "skills": [{
                "name": "Postman",
                "confirmed": True,
                "source_kind": "CV_EXTRACTED",
                "source_block_id": "page-1-block-2",
                "source_sha256": "c" * 64,
                "evidence": "Used Postman for API tests",
            }],
        }]),
    )
    assignments, unresolved, _ = asyncio.run(
        skill_profiles.automatically_assign_test_cases("project-a", [version])
    )

    assert assignments == {"version-a": "tester-a"}
    assert unresolved == []


def test_automatic_assignment_keeps_legacy_confirmed_duplicate_skill(monkeypatch):
    monkeypatch.setattr(
        skill_profiles.project_repository,
        "list_members",
        _async_value([
            {"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"},
        ]),
    )
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "list_for_members",
        _async_value([
            {
                "user_id": "tester-a",
                "availability": "AVAILABLE",
                "skills": [
                    {"name": "API", "confirmed": True},
                    {"name": "api", "confirmed": False},
                ],
            },
        ]),
    )
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))

    assignments, unresolved, _ = asyncio.run(
        skill_profiles.automatically_assign_test_cases(
            "project-a",
            [{"_id": "version-a", "required_skills": ["API"]}],
        )
    )

    assert assignments == {"version-a": "tester-a"}
    assert unresolved == []


def test_automatic_assignment_reads_members_profiles_and_load_from_run_transaction(monkeypatch):
    session = object()
    calls = []

    async def list_members(project_id, *, session):
        calls.append(("members", project_id, session))
        return [{"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"}]

    async def list_profiles(project_id, user_ids, *, session):
        calls.append(("profiles", project_id, session))
        return [{
            "user_id": "tester-a",
            "revision": 7,
            "availability": "AVAILABLE",
            "skills": [{"name": "API", "confirmed": True}],
        }]

    async def active_runs(user_ids, *, session):
        calls.append(("runs", "project-a", session))
        async for run in _async_iter([])(user_ids, session=session):
            yield run

    monkeypatch.setattr(skill_profiles.project_repository, "list_members", list_members)
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "list_for_members", list_profiles)
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", active_runs)

    assignments, unresolved, decisions = asyncio.run(
        skill_profiles.automatically_assign_test_cases(
            "project-a",
            [{"_id": "version-a", "required_skills": ["API"]}],
            session=session,
        )
    )

    assert assignments == {"version-a": "tester-a"}
    assert unresolved == []
    assert decisions["version-a"]["skill_profile_revision"] == 7
    assert calls == [(name, "project-a", session) for name in ("members", "profiles", "runs")]


def test_automatic_assignment_counts_run_load_for_case_assignees_once_per_run(monkeypatch):
    members = [
        {"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"},
        {"user_id": "tester-b", "status": "ACTIVE", "project_role": "TESTER"},
    ]
    profiles = [
        {"user_id": "tester-a", "availability": "AVAILABLE", "skills": []},
        {"user_id": "tester-b", "availability": "AVAILABLE", "skills": []},
    ]
    monkeypatch.setattr(skill_profiles.project_repository, "list_members", _async_value(members))
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "list_for_members", _async_value(profiles))
    monkeypatch.setattr(
        skill_profiles.skill_profile_repository,
        "iter_active_runs_for_members",
        _async_iter([
            {
                "assignee_id": None,
                "test_case_assignments": {"old-version-a": "tester-a", "old-version-b": "tester-a"},
            }
        ]),
    )

    assignments, unresolved, decisions = asyncio.run(
        skill_profiles.automatically_assign_test_cases(
            "project-a",
            [{"_id": "new-version-a", "required_skills": []}],
        )
    )

    assert assignments == {"new-version-a": "tester-b"}
    assert unresolved == []
    assert decisions["new-version-a"]["active_run_count_before_assignment"] == 0
    assert decisions["new-version-a"]["active_case_count_before_assignment"] == 0


def test_automatic_assignment_balances_new_cases_against_existing_run_assignments(monkeypatch):
    members = [
        {"user_id": "tester-a", "status": "ACTIVE", "project_role": "TESTER"},
        {"user_id": "tester-b", "status": "ACTIVE", "project_role": "TESTER"},
    ]
    profiles = [
        {"user_id": "tester-a", "availability": "AVAILABLE", "skills": []},
        {"user_id": "tester-b", "availability": "AVAILABLE", "skills": []},
    ]
    monkeypatch.setattr(skill_profiles.project_repository, "list_members", _async_value(members))
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "list_for_members", _async_value(profiles))
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "iter_active_runs_for_members", _async_iter([]))

    assignments, unresolved, decisions = asyncio.run(
        skill_profiles.automatically_assign_test_cases(
            "project-a",
            [{"_id": "new-version", "required_skills": []}],
            existing_case_assignments={"existing-version": "tester-a"},
            existing_assignee_id="tester-a",
        )
    )

    assert assignments == {"new-version": "tester-b"}
    assert unresolved == []
    assert decisions["new-version"]["assignee_id"] == "tester-b"


def test_cv_source_blocks_preserve_parser_page_and_split_long_blocks():
    from src.modules.projects.services.skill_profiles import _cv_source_blocks

    parsed = SimpleNamespace(
        structure=[
            SimpleNamespace(
                extraction_status="EXTRACTED", block_id="#/pages/4/blocks/2",
                page_no=4, text="x" * 3500,
            ),
            SimpleNamespace(
                extraction_status="NO_TEXT_EXTRACTED", block_id="#/pages/5/blocks/1",
                page_no=5, text="",
            ),
        ],
        markdown="unused fallback",
    )
    blocks, total, truncated = _cv_source_blocks(parsed)
    assert len(blocks) == 2
    assert [item["page_no"] for item in blocks] == [4, 4]
    assert blocks[0]["block_id"] == "#/pages/4/blocks/2:part:1"
    assert blocks[1]["block_id"] == "#/pages/4/blocks/2:part:2"
    assert total == 3500
    assert truncated is False


def test_cv_markdown_fallback_does_not_invent_page_numbers():
    from src.modules.projects.services.skill_profiles import _cv_source_blocks

    parsed = SimpleNamespace(structure=[], markdown="Skill: API testing\n\nProject: Payments")
    blocks, _, truncated = _cv_source_blocks(parsed)
    assert [item["page_no"] for item in blocks] == [None, None]
    assert blocks[0]["text"] == "Skill: API testing"
    assert truncated is False


@pytest.mark.parametrize(
    "candidate, expected",
    [
        ({"name": "Postman", "source_block_id": "block-1", "evidence_quote": "Postman", "page_no": 2}, True),
        ({"name": "Postman", "source_block_id": "missing", "evidence_quote": "Postman", "page_no": 2}, False),
        ({"name": "Postman", "source_block_id": "block-1", "evidence_quote": "Postman proficiency", "page_no": 2}, False),
        ({"name": "Postman", "source_block_id": "block-1", "evidence_quote": "Postman", "page_no": 3}, False),
    ],
)
def test_cv_candidate_evidence_must_match_an_exact_source_block(candidate, expected):
    from src.modules.projects.services.skill_profiles import _validate_cv_candidate_evidence

    assert _validate_cv_candidate_evidence(
        [{"block_id": "block-1", "page_no": 2, "text": "Used Postman for API tests"}],
        {"skills": [candidate], "experiences": [], "warnings": []},
    ) is expected


def test_cv_candidate_claim_must_be_supported_by_the_same_source_block():
    from src.modules.projects.services.skill_profiles import _validate_cv_candidate_evidence

    source_blocks = [{
        "block_id": "block-1",
        "page_no": 2,
        "text": "Used Postman for API tests",
    }]

    assert not _validate_cv_candidate_evidence(
        source_blocks,
        {"skills": [{
            "name": "Selenium",
            "source_block_id": "block-1",
            "evidence_quote": "Used Postman",
            "page_no": 2,
        }]},
    )


def test_cv_experience_claims_must_be_supported_by_the_same_source_block():
    from src.modules.projects.services.skill_profiles import _validate_cv_candidate_evidence

    source_blocks = [{
        "block_id": "block-1",
        "page_no": 2,
        "text": "QA Engineer. Used Postman for API tests.",
    }]

    assert not _validate_cv_candidate_evidence(
        source_blocks,
        {"skills": [], "experiences": [{
            "title": "Senior QA Manager",
            "domain": "Banking",
            "technologies": ["Postman"],
            "responsibilities": "Led a team of twelve",
            "source_block_id": "block-1",
            "evidence_quote": "Used Postman for API tests",
            "page_no": 2,
        }]},
    )


def test_cv_experience_claim_must_be_supported_by_its_exact_quote_not_adjacent_source():
    from src.modules.projects.services.skill_profiles import _validate_cv_candidate_evidence

    source_blocks = [{
        "block_id": "block-1",
        "page_no": 2,
        "text": "QA Engineer used Postman. Kotlin appears in a separate training list.",
    }]

    assert not _validate_cv_candidate_evidence(
        source_blocks,
        {"skills": [], "experiences": [{
            "title": "QA Engineer",
            "technologies": ["Kotlin"],
            "evidence_quote": "QA Engineer used Postman",
            "source_block_id": "block-1",
            "page_no": 2,
        }]},
    )


def test_cv_experience_with_verbatim_claims_and_matching_citation_is_grounded():
    from src.modules.projects.services.skill_profiles import _validate_cv_candidate_evidence

    source_blocks = [{
        "block_id": "block-1",
        "page_no": 2,
        "text": "QA Engineer. Used Postman for API tests.",
    }]

    assert _validate_cv_candidate_evidence(
        source_blocks,
        {"skills": [], "experiences": [{
            "title": "QA Engineer",
            "domain": "",
            "technologies": ["Postman"],
            "responsibilities": "Used Postman for API tests.",
            "source_block_id": "block-1",
            "evidence_quote": "QA Engineer. Used Postman for API tests.",
            "page_no": 2,
        }]},
    )


def test_cv_experience_period_must_be_explicitly_grounded_in_its_quote():
    source_blocks = [{
        "block_id": "block-period",
        "page_no": 3,
        "text": "QA Engineer, 2020–2022, used Postman. QA Engineer used Postman for API testing.",
    }]
    grounded = {
        "skills": [],
        "experiences": [{
            "title": "QA Engineer",
            "period": "2020–2022",
            "technologies": ["Postman"],
            "evidence_quote": "QA Engineer, 2020–2022, used Postman.",
            "source_block_id": "block-period",
            "page_no": 3,
        }],
    }
    inferred_period = {
        "skills": [],
        "experiences": [{
            **grounded["experiences"][0],
            "period": "2018–2020",
            "evidence_quote": "QA Engineer used Postman for API testing.",
        }],
    }

    assert skill_profiles._validate_cv_candidate_evidence(source_blocks, grounded)
    assert not skill_profiles._validate_cv_candidate_evidence(source_blocks, inferred_period)


def test_cv_candidate_evidence_rejects_ambiguous_duplicate_source_block_ids():
    from src.modules.projects.services.skill_profiles import _validate_cv_candidate_evidence

    source_blocks = [
        {"block_id": "same", "page_no": 1, "text": "Postman"},
        {"block_id": "same", "page_no": 2, "text": "Postman"},
    ]

    assert not _validate_cv_candidate_evidence(
        source_blocks,
        {"skills": [{"source_block_id": "same", "evidence_quote": "Postman", "page_no": 2}]},
    )


def test_cv_upload_rejects_candidate_evidence_not_grounded_in_submitted_file(monkeypatch):
    from src.modules.projects.services import skill_profiles as service

    monkeypatch.setattr(service, "get_project", _async_value(None))
    monkeypatch.setattr(
        service,
        "convert_requirement_source",
        _async_value(SimpleNamespace(
            structure=[SimpleNamespace(
                extraction_status="EXTRACTED", block_id="page-1-block-1",
                page_no=1, text="Used Postman for API tests",
            )],
            markdown="Used Postman for API tests", unprocessed_blocks=[],
            parser="text", parser_version="1", page_count=1,
        )),
    )
    monkeypatch.setattr(
        service.ai_automation_client,
        "extract_skill_profile",
        _async_value({
            "skills": [{
                "name": "Postman",
                "evidence_quote": "Expert in Postman",
                "source_block_id": "page-1-block-1",
                "page_no": 1,
            }],
            "experiences": [],
            "warnings": [],
        }),
    )
    upload = type("Upload", (), {
        "filename": "candidate.txt", "read": _async_value(b"CV bytes"),
        "close": _async_value(None),
    })()

    with pytest.raises(HTTPException) as error:
        asyncio.run(service.extract_own_skill_profile_from_cv(
            "project-a", upload, type("User", (), {"id": "member-a"})()
        ))

    assert error.value.status_code == 502
    assert error.value.detail["code"] == "CV_AI_EVIDENCE_INVALID"


def test_cv_source_blocks_report_content_truncated_at_character_limit():
    from src.modules.projects.services.skill_profiles import _cv_source_blocks

    parsed = SimpleNamespace(
        structure=[
            SimpleNamespace(
                extraction_status="EXTRACTED", block_id="first", page_no=1,
                text="a" * 99_000,
            ),
            SimpleNamespace(
                extraction_status="EXTRACTED", block_id="second", page_no=2,
                text="b" * 2_000,
            ),
        ],
        markdown="",
    )

    blocks, total, truncated = _cv_source_blocks(parsed)

    assert total == 99_000
    assert len(blocks) == 33
    assert truncated is True


def test_cv_source_blocks_do_not_mark_exact_character_limit_as_truncated():
    from src.modules.projects.services.skill_profiles import _cv_source_blocks

    parsed = SimpleNamespace(
        structure=[
            SimpleNamespace(
                extraction_status="EXTRACTED", block_id="first", page_no=1,
                text="a" * 99_000,
            ),
            SimpleNamespace(
                extraction_status="EXTRACTED", block_id="second", page_no=2,
                text="b" * 1_000,
            ),
        ],
        markdown="",
    )

    blocks, total, truncated = _cv_source_blocks(parsed)

    assert total == 100_000
    assert len(blocks) == 34
    assert truncated is False


def test_cv_extraction_requires_project_access_supported_file_and_keeps_file_ephemeral(monkeypatch):
    from src.modules.projects.services import skill_profiles as service

    calls = {}
    monkeypatch.setattr(service, "get_project", _async_value(None))
    monkeypatch.setattr(
        service,
        "convert_requirement_source",
        _async_value(SimpleNamespace(
            structure=[SimpleNamespace(
                extraction_status="EXTRACTED", block_id="#/pages/1/blocks/1",
                page_no=1, text="Postman API testing",
            )],
            markdown="Postman API testing", unprocessed_blocks=[],
            parser="pymupdf_text", parser_version="1", page_count=1,
        )),
    )

    async def extract(project_id, blocks):
        calls.update(project_id=project_id, blocks=blocks)
        return {"skills": [{
            "name": "Postman", "evidence_quote": "Postman", "source_block_id": "#/pages/1/blocks/1", "page_no": 1,
        }], "experiences": [], "warnings": []}

    monkeypatch.setattr(service.ai_automation_client, "extract_skill_profile", extract)
    async def persist_profile(_project_id, _user, _extracted, source_sha256):
        return ({
            "project_id": "project-a",
            "user_id": "member-a",
            "skills": [{"name": "Postman", "source_kind": "CV_EXTRACTED", "source_sha256": source_sha256}],
            "experiences": [],
            "availability": "AVAILABLE",
            "revision": 4,
        }, True)

    monkeypatch.setattr(service, "_persist_cv_profile", persist_profile)
    upload = type("Upload", (), {
        "filename": "candidate.pdf", "read": _async_value(b"cv bytes"),
        "close": _async_value(None),
    })()
    result = asyncio.run(service.extract_own_skill_profile_from_cv(
        "project-a", upload, type("User", (), {"id": "member-a"})()
    ))

    assert calls["project_id"] == "project-a"
    assert result["skills"][0]["name"] == "Postman"
    assert result["skills"][0]["evidence_quote"] == "Postman"
    assert len(result["source_sha256"]) == 64
    assert "level" not in result["skills"][0]
    assert result["cv_persisted"] is False
    assert result["profile_facts_persisted"] is True
    assert result["profile_changed"] is True
    assert result["profile_revision"] == 4
    assert result["profile"]["revision"] == 4
    assert result["indexed_in_project_knowledge"] is False


def test_cv_extracted_skill_evidence_requires_confirmation_for_assignment():
    source_skill = {
        "name": "Postman",
        "level": "NOT_ASSESSED",
        "evidence": "Used Postman for API tests",
        "source_block_id": "page-1-block-2",
        "source_page_no": 1,
        "source_sha256": "a" * 64,
        "source_kind": "CV_EXTRACTED",
        "confirmed": False,
    }
    assert skill_profiles._assignment_skills({"skills": [source_skill]}) == {}
    confirmed_skill = {**source_skill, "confirmed": True}
    assert skill_profiles._assignment_skills({"skills": [confirmed_skill]})["postman"] == confirmed_skill


def test_cv_extraction_entries_keep_quote_and_source_coordinates_without_assessing_level():
    skills, experiences = skill_profiles._cv_profile_entries(
        {
            "skills": [{
                "name": "Postman",
                "evidence_quote": "Used Postman for API tests",
                "source_block_id": "page-1-block-2",
                "page_no": 1,
            }],
            "experiences": [{
                "title": "QA Engineer",
                "period": "2022-2024",
                "domain": "Banking",
                "technologies": ["Postman"],
                "responsibilities": "Tested APIs",
                "evidence_quote": "QA Engineer 2022-2024 Banking Postman Tested APIs",
                "source_block_id": "page-2-block-1",
                "page_no": 2,
            }],
        },
        "b" * 64,
    )

    assert skills == [{
        "name": "Postman",
        "level": "NOT_ASSESSED",
        "evidence": "Used Postman for API tests",
        "source_block_id": "page-1-block-2",
        "source_page_no": 1,
        "source_sha256": "b" * 64,
        "source_kind": "CV_EXTRACTED",
        "confirmed": False,
    }]
    assert experiences[0]["source_kind"] == "CV_EXTRACTED"
    assert experiences[0]["source_sha256"] == "b" * 64
    assert experiences[0]["source_page_no"] == 2


def test_cv_profile_persistence_replaces_prior_cv_facts_and_preserves_member_profile(monkeypatch):
    calls = {}
    existing = {
        "project_id": "project-a",
        "user_id": "member-a",
        "revision": 5,
        "availability": "LIMITED",
        "skills": [
            {"name": "API", "confirmed": True, "source_kind": "MEMBER_DECLARED"},
            {
                "name": "Old CV skill",
                "confirmed": False,
                "source_kind": "CV_EXTRACTED",
                "source_sha256": "a" * 64,
            },
        ],
        "experiences": [{
            "title": "Legacy CV role",
            "source_kind": "CV_EXTRACTED",
            "source_sha256": "a" * 64,
        }],
    }
    monkeypatch.setattr(skill_profiles.skill_profile_repository, "find", _async_value(existing))

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, error_type, error, traceback):
            return False

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, error_type, error, traceback):
            return False

        def start_transaction(self):
            return Transaction()

    session = Session()
    monkeypatch.setattr(
        skill_profiles.database,
        "client",
        SimpleNamespace(start_session=_async_value(session)),
    )

    async def upsert(project_id, user_id, expected_revision, changes, timestamp, *, session):
        calls.update(
            project_id=project_id,
            user_id=user_id,
            expected_revision=expected_revision,
            changes=changes,
            session=session,
        )
        return {
            "project_id": project_id,
            "user_id": user_id,
            **changes,
            "revision": 6,
            "updated_at": timestamp,
        }

    monkeypatch.setattr(skill_profiles.skill_profile_repository, "upsert", upsert)

    async def audit(*args, session=None, **kwargs):
        calls["audit_session"] = session

    monkeypatch.setattr(skill_profiles, "audit", audit)
    extracted = {
        "skills": [{
            "name": "Postman",
            "evidence_quote": "Used Postman for API tests",
            "source_block_id": "page-1-block-1",
            "page_no": 1,
        }],
        "experiences": [],
    }

    saved, changed = asyncio.run(
        skill_profiles._persist_cv_profile(
            "project-a",
            type("User", (), {"id": "member-a"})(),
            extracted,
            "d" * 64,
        )
    )

    assert changed is True
    assert calls["expected_revision"] == 5
    assert calls["session"] is session
    assert calls["audit_session"] is session
    assert calls["changes"]["availability"] == "LIMITED"
    assert calls["changes"]["skills"][0] == existing["skills"][0]
    assert [item["name"] for item in calls["changes"]["skills"]] == ["API", "Postman"]
    assert calls["changes"]["skills"][1]["source_sha256"] == "d" * 64
    assert calls["changes"]["experiences"] == []
    assert saved["revision"] == 6


def test_cv_extraction_rejects_unsupported_file_before_conversion(monkeypatch):
    from src.modules.projects.services import skill_profiles as service

    monkeypatch.setattr(service, "get_project", _async_value(None))
    converter = AsyncMock()
    monkeypatch.setattr(service, "convert_requirement_source", converter)
    upload = type("Upload", (), {
        "filename": "resume.exe", "closed": False, "read": _async_value(b"x"),
    })()

    async def close():
        upload.closed = True

    upload.close = close

    with pytest.raises(HTTPException) as error:
        asyncio.run(service.extract_own_skill_profile_from_cv(
            "project-a", upload, type("User", (), {"id": "member-a"})()
        ))
    assert error.value.detail["code"] == "CV_FORMAT_UNSUPPORTED"
    converter.assert_not_awaited()
    assert upload.closed


@pytest.mark.parametrize(
    "filename, content, max_size, expected_code, expected_status",
    [
        ("candidate.txt", b"", 10, "CV_FILE_EMPTY", 422),
        ("candidate.txt", b"too large", 4, "CV_FILE_TOO_LARGE", 413),
    ],
)
def test_cv_upload_closes_file_when_rejected_before_conversion(
    monkeypatch, filename, content, max_size, expected_code, expected_status
):
    from src.modules.projects.services import skill_profiles as service

    monkeypatch.setattr(service, "get_project", _async_value(None))
    monkeypatch.setattr(service.settings, "MAX_UPLOAD_SIZE_BYTES", max_size)
    converter = AsyncMock()
    monkeypatch.setattr(service, "convert_requirement_source", converter)
    upload = type("Upload", (), {
        "filename": filename,
        "closed": False,
        "read": _async_value(content),
        "close": AsyncMock(),
    })()

    async def close():
        upload.closed = True

    upload.close = close

    with pytest.raises(HTTPException) as error:
        asyncio.run(service.extract_own_skill_profile_from_cv(
            "project-a", upload, type("User", (), {"id": "member-a"})()
        ))

    assert error.value.status_code == expected_status
    assert error.value.detail["code"] == expected_code
    assert upload.closed is True
    converter.assert_not_awaited()


def _async_value(value):
    async def inner(*_args, **_kwargs):
        return value

    return inner


def _async_iter(values):
    async def inner(*_args, **_kwargs):
        for value in values:
            yield value

    return inner
