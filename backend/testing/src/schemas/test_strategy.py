import ast
import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RiskRankingWeights(BaseModel):
    risk_weight: float | None = Field(default=0.45, ge=0, le=1)
    priority_weight: float | None = Field(default=0.25, ge=0, le=1)
    unassessed_score: float | None = Field(default=0.5, ge=0, le=1)
    staleness_penalty: float | None = Field(default=0.2, ge=0, le=1)
    failure_penalty_per_occurrence: float | None = Field(default=0.1, ge=0, le=1)
    failure_penalty_cap: float | None = Field(default=0.4, ge=0, le=1)
    maximum_score: float | None = Field(default=1.0, gt=0, le=1)


class RiskModel(BaseModel):
    probability_scale: list[dict[str, Any]] = Field(min_length=1, max_length=20)
    impact_scale: list[dict[str, Any]] = Field(min_length=1, max_length=20)
    severity_scale: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    blocking_severities: list[str] = Field(default_factory=list, max_length=20)
    critical_severities: list[str] = Field(default_factory=list, max_length=20)
    priority_scale: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    ranking_weights: RiskRankingWeights = Field(default_factory=RiskRankingWeights)
    risk_exposure_formula: str = Field(min_length=1, max_length=1000)
    thresholds: list[dict[str, Any]] = Field(min_length=1, max_length=50)
    mandatory_test_depth: dict[str, Any] = Field(default_factory=dict)
    regression_priority_rules: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_risk_model(self):
        formula = self.risk_exposure_formula.strip()
        expression = (
            formula.split("=", 1)[1].strip()
            if formula.lower().startswith("risk_exposure") and "=" in formula
            else formula
        )
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as error:
            raise ValueError("INVALID_RISK_MODEL") from error
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Name,
            ast.Load,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Pow,
            ast.Mod,
            ast.UAdd,
            ast.USub,
        )
        if any(not isinstance(node, allowed_nodes) for node in ast.walk(tree)):
            raise ValueError("INVALID_RISK_MODEL")
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        if (
            not names
            or not names <= {"probability", "impact"}
            or not {"probability", "impact"} <= names
        ):
            raise ValueError("INVALID_RISK_MODEL")
        if any(
            isinstance(node, ast.Constant)
            and (not isinstance(node.value, (int, float)) or isinstance(node.value, bool))
            for node in ast.walk(tree)
        ):
            raise ValueError("INVALID_RISK_MODEL")
        for scale in (
            self.probability_scale,
            self.impact_scale,
            self.severity_scale,
            self.priority_scale,
        ):
            values = [item.get("value") for item in scale]
            if any(
                not isinstance(value, (int, float)) or isinstance(value, bool) for value in values
            ) or len(set(values)) != len(values):
                raise ValueError("INVALID_RISK_MODEL")
        priority_labels = [
            " ".join(str(item.get("label", "")).split()).casefold()
            for item in self.priority_scale
        ]
        if any(not label for label in priority_labels) or len(set(priority_labels)) != len(priority_labels):
            raise ValueError("INVALID_RISK_MODEL")
        severity_labels = [
            " ".join(str(item.get("label", "")).split()) for item in self.severity_scale
        ]
        normalized_severity_labels = [label.casefold() for label in severity_labels]
        if (
            any(not label for label in severity_labels)
            or len(set(normalized_severity_labels)) != len(normalized_severity_labels)
        ):
            raise ValueError("INVALID_RISK_MODEL")
        if self.blocking_severities or self.critical_severities:
            if not self.severity_scale:
                raise ValueError("INVALID_RISK_MODEL")
            normalized_blocking = [
                " ".join(label.split()).casefold() for label in self.blocking_severities
            ]
            normalized_critical = [
                " ".join(label.split()).casefold() for label in self.critical_severities
            ]
            configured_blocking = set(normalized_blocking)
            configured_critical = set(normalized_critical)
            if (
                any(not label for label in normalized_blocking + normalized_critical)
                or len(configured_blocking) != len(self.blocking_severities)
                or len(configured_critical) != len(self.critical_severities)
                or not configured_blocking.issubset(set(normalized_severity_labels))
                or not configured_critical.issubset(set(normalized_severity_labels))
            ):
                raise ValueError("INVALID_RISK_MODEL")
        if any(
            not item.get("level")
            or not any(
                isinstance(item.get(bound), (int, float)) and not isinstance(item.get(bound), bool)
                for bound in ("min", "max")
            )
            for item in self.thresholds
        ):
            raise ValueError("INVALID_RISK_MODEL")
        return self


class TestStrategyFields(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    objective: str = Field(min_length=2, max_length=5000)
    test_levels: list[str] = Field(min_length=1, max_length=20)
    test_types: list[str] = Field(min_length=1, max_length=100)
    approach: str = Field(min_length=2, max_length=10000)
    risk_model: RiskModel
    technique_policy: dict[str, Any] = Field(default_factory=dict)
    automation_policy: dict[str, Any] = Field(default_factory=dict)
    environment_policy: dict[str, Any] = Field(default_factory=dict)
    test_data_policy: dict[str, Any] = Field(default_factory=dict)
    defect_policy: dict[str, Any] = Field(default_factory=dict)
    review_policy: dict[str, Any] = Field(default_factory=dict)
    entry_criteria_defaults: list[str] = Field(default_factory=list, max_length=200)
    exit_criteria_defaults: list[str] = Field(default_factory=list, max_length=200)
    suspension_criteria: list[str] = Field(default_factory=list, max_length=200)
    resumption_criteria: list[str] = Field(default_factory=list, max_length=200)
    deliverables: list[str] = Field(default_factory=list, max_length=200)
    reporting_policy: dict[str, Any] = Field(default_factory=dict)
    quality_objectives: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    standards_refs: list[str] = Field(default_factory=list, max_length=100)
    tailoring_rationale: str = Field(default="", max_length=5000)
    reviewer_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_suspension_pairs(self):
        if bool(self.suspension_criteria) != bool(self.resumption_criteria):
            raise ValueError("Tiêu chí đình chỉ và tiếp tục phải được khai báo cùng nhau")
        return self


class TestStrategyCreate(TestStrategyFields):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[A-Z][A-Z0-9_-]+$")


class TestStrategyPatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    objective: str | None = Field(default=None, min_length=2, max_length=5000)
    test_levels: list[str] | None = Field(default=None, min_length=1, max_length=20)
    test_types: list[str] | None = Field(default=None, min_length=1, max_length=100)
    approach: str | None = Field(default=None, min_length=2, max_length=10000)
    risk_model: RiskModel | None = None
    technique_policy: dict[str, Any] | None = None
    automation_policy: dict[str, Any] | None = None
    environment_policy: dict[str, Any] | None = None
    test_data_policy: dict[str, Any] | None = None
    defect_policy: dict[str, Any] | None = None
    review_policy: dict[str, Any] | None = None
    entry_criteria_defaults: list[str] | None = Field(default=None, max_length=200)
    exit_criteria_defaults: list[str] | None = Field(default=None, max_length=200)
    suspension_criteria: list[str] | None = Field(default=None, max_length=200)
    resumption_criteria: list[str] | None = Field(default=None, max_length=200)
    deliverables: list[str] | None = Field(default=None, max_length=200)
    reporting_policy: dict[str, Any] | None = None
    quality_objectives: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    standards_refs: list[str] | None = Field(default=None, max_length=100)
    tailoring_rationale: str | None = Field(default=None, max_length=5000)
    reviewer_ids: list[str] | None = Field(default=None, max_length=100)


class StrategyTransitionInput(BaseModel):
    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=5000)


class StrategyVersionInput(BaseModel):
    expected_revision: int = Field(ge=1)
    change_reason: str = Field(min_length=2, max_length=5000)


class StrategyCloneInput(BaseModel):
    source_strategy_id: str = Field(min_length=1, max_length=200)
    key: str = Field(min_length=2, max_length=80, pattern=r"^[A-Z][A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=300)
    tailoring_rationale: str = Field(min_length=2, max_length=5000)


def strategy_completeness(strategy):
    checks = (
        ("STRATEGY_OBJECTIVE_MISSING", bool(str(strategy.get("objective", "")).strip())),
        ("STRATEGY_TEST_LEVEL_MISSING", bool(strategy.get("test_levels"))),
        ("STRATEGY_TEST_TYPE_MISSING", bool(strategy.get("test_types"))),
        ("STRATEGY_RISK_MODEL_MISSING", bool(strategy.get("risk_model"))),
        (
            "STRATEGY_DEFECT_CLASSIFICATION_MISSING",
            bool((strategy.get("risk_model") or {}).get("severity_scale"))
            and bool((strategy.get("risk_model") or {}).get("priority_scale")),
        ),
        ("STRATEGY_ENTRY_CRITERIA_MISSING", bool(strategy.get("entry_criteria_defaults"))),
        ("STRATEGY_EXIT_CRITERIA_MISSING", bool(strategy.get("exit_criteria_defaults"))),
        ("STRATEGY_SUSPENSION_CRITERIA_MISSING", bool(strategy.get("suspension_criteria"))),
        ("STRATEGY_RESUMPTION_CRITERIA_MISSING", bool(strategy.get("resumption_criteria"))),
        (
            "STRATEGY_REPORTING_CADENCE_MISSING",
            bool(strategy.get("reporting_policy", {}).get("cadence")),
        ),
        ("STRATEGY_QUALITY_OBJECTIVE_MISSING", bool(strategy.get("quality_objectives"))),
    )
    findings = [{"code": code, "blocks_review": True} for code, passed in checks if not passed]
    return {"ready_for_review": not findings, "findings": findings}


def compare_strategy_snapshots(left, right):
    left_snapshot = strategy_snapshot(left)
    right_snapshot = strategy_snapshot(right)
    ignored = {"strategy_id", "version"}
    changed_fields = [
        field
        for field in sorted(set(left_snapshot) | set(right_snapshot))
        if field not in ignored and left_snapshot.get(field) != right_snapshot.get(field)
    ]
    return {
        "left_strategy_id": left["_id"],
        "right_strategy_id": right["_id"],
        "left_version": left["version"],
        "right_version": right["version"],
        "changed_fields": changed_fields,
        "changes": [
            {"field": field, "before": left_snapshot.get(field), "after": right_snapshot.get(field)}
            for field in changed_fields
        ],
    }


def strategy_snapshot(strategy):
    fields = tuple(TestStrategyFields.model_fields)
    return {
        "strategy_id": strategy["_id"],
        "lineage_id": strategy["lineage_id"],
        "project_id": strategy["project_id"],
        "key": strategy["key"],
        "version": strategy["version"],
        **{field: strategy.get(field) for field in fields},
    }


def strategy_hash(strategy):
    value = json.dumps(
        strategy_snapshot(strategy),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
