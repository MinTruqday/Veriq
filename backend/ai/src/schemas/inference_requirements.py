from typing import Annotated, Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RequirementQualityCategory = Literal[
    "AMBIGUITY", "OMISSION", "INCONSISTENCY", "CONTRADICTION", "UNTESTABLE",
    "MISSING_ACCEPTANCE_CRITERIA", "MISSING_ERROR_BEHAVIOR",
    "MISSING_PERMISSION_RULE", "MISSING_BOUNDARY", "MISSING_STATE_RULE",
    "MISSING_DATA_RULE", "MISSING_NON_FUNCTIONAL_CRITERIA", "OTHER",
]


class RequirementQualityFindingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: RequirementQualityCategory
    severity: Literal["error", "warning", "info"]
    message: str = Field(min_length=2, max_length=5000)
    suggestion: str = Field(min_length=2, max_length=5000)
    evidence_refs: List[str] = Field(min_length=1, max_length=100)
    reason_codes: List[str] = Field(min_length=1, max_length=100)

class RequirementAcceptanceCriterionSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=2, max_length=5000)

class RequirementRevisionSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revised_title: str | None = Field(default=None, min_length=2, max_length=300)
    revised_content: str | None = Field(default=None, min_length=2, max_length=20000)
    revised_actors: List[str] | None = Field(default=None, min_length=1, max_length=100)
    revised_business_rules: List[str] | None = Field(default=None, min_length=1, max_length=200)
    revised_acceptance_criteria: List[RequirementAcceptanceCriterionSuggestionOutput] | None = (
        Field(default=None, min_length=1, max_length=200)
    )
    revised_dependencies: List[str] | None = Field(default=None, max_length=200)
    target_fields: List[
        Literal[
            "title", "content", "actors", "business_rules", "acceptance_criteria", "dependencies"
        ]
    ] = Field(default_factory=list, max_length=6)
    rationale: str = Field(default="", max_length=5000)
    evidence_refs: List[str] = Field(default_factory=list, max_length=100)
    reason_codes: List[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def require_revision_value(self):
        values = {
            "title": self.revised_title,
            "content": self.revised_content,
            "actors": self.revised_actors,
            "business_rules": self.revised_business_rules,
            "acceptance_criteria": self.revised_acceptance_criteria,
            "dependencies": self.revised_dependencies,
        }
        revised_fields = {field for field, value in values.items() if value is not None}
        if not revised_fields:
            raise ValueError("requirement_revision_value_required")
        self.target_fields = [
            field
            for field in (
                "title",
                "content",
                "actors",
                "business_rules",
                "acceptance_criteria",
                "dependencies",
            )
            if field in revised_fields
        ]
        for values in (self.revised_actors, self.revised_business_rules):
            if values is not None and any(not value.strip() for value in values):
                raise ValueError("requirement_revision_blank_list_value")
        return self

class RequirementQualityModelOutput(BaseModel):
    """Evaluate content actors business rules acceptance criteria and dependencies separately. Treat absent behavior actors or business rules as blocking. Return every field finding with an evidence grounded revision, make target_fields match non-null revised values, merge related revisions, and never apply changes automatically."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["requirement_quality_analysis"] = "requirement_quality_analysis"
    suggestions: List[RequirementRevisionSuggestionOutput] = Field(
        default_factory=list,
        max_length=1,
        description="Return an empty list when no concrete revision is justified. Each suggestion must include at least one non-null revised field, and target_fields must contain only the names of those non-null revised fields.",
    )

class RequirementTemplateAPIOperationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(min_length=1, max_length=200)
    method: str = Field(min_length=1, max_length=20)
    path: str | None = None
    url_template: str | None = None
    operation_id: str | None = None
    folder: str | None = None

class RequirementTemplateContextOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectives: str = Field(default="", max_length=10000)
    in_scope: str = Field(default="", max_length=10000)
    out_of_scope: str = Field(default="", max_length=10000)
    stakeholders: List[str] = Field(default_factory=list, max_length=200)
    actors_and_systems: List[str] = Field(default_factory=list, max_length=200)
    glossary: List[str] = Field(default_factory=list, max_length=500)
    assumptions: List[str] = Field(default_factory=list, max_length=200)
    constraints: List[str] = Field(default_factory=list, max_length=200)

class RequirementTemplateSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300)
    type: Literal["functional", "non_functional", "business_rule", "api", "ui", "data", "permission", "integration", "constraint"]
    content: str = Field(min_length=2, max_length=10000)
    evidence_refs: List[str] = Field(min_length=1, max_length=20)
    source_quotes: dict[str, str] = Field(default_factory=dict)
    missing_sections: List[str] = Field(default_factory=list, max_length=20)
    not_applicable_sections: List[str] = Field(default_factory=list, max_length=20)
    acceptance_criteria: List[str] = Field(default_factory=list, max_length=50)
    actors: List[str] = Field(default_factory=list, max_length=50)
    business_rules: List[str] = Field(default_factory=list, max_length=50)
    dependencies: List[str] = Field(default_factory=list, max_length=50)
    user_story_actor: str | None = None
    user_story_goal: str | None = None
    user_story_value: str | None = None
    main_flow: str | None = None
    exception_flow: str | None = None
    data_rules: str | None = None
    integration: str | None = None
    quality_measure: str | None = None
    api_operations: List[RequirementTemplateAPIOperationOutput] = Field(default_factory=list, max_length=50)

class RequirementTemplateSynthesisOutput(BaseModel):
    """Synthesize a Requirements template draft only from supplied documents or templates. Context may contain only objectives in_scope out_of_scope stakeholders actors_and_systems glossary assumptions and constraints. Each proposed requirement must cite exact evidence and a verbatim quote for document evidence. Preserve source distinctions, report duplicates and conflicts, and mark absent applicable information as missing. Never create test cases or approve import."""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["requirement_template_synthesis"] = "requirement_template_synthesis"
    context: RequirementTemplateContextOutput = Field(default_factory=RequirementTemplateContextOutput)
    suggestions: List[RequirementTemplateSuggestionOutput] = Field(default_factory=list, max_length=100)
    conflicts: List[dict[str, Any]] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=50)

class RequirementTemplateReviewFindingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_index: int | None = Field(default=None, ge=0)
    field: str = Field(min_length=1, max_length=100)
    issue: str = Field(min_length=2, max_length=1000)
    evidence_refs: List[str] = Field(min_length=1, max_length=20)
    suggested_source_quote: str | None = Field(default=None, min_length=2, max_length=2000)

class RequirementTemplateReviewOutput(BaseModel):
    """Review whether a Requirements template is suitable for import without changing it  Report a missing field only when the source shows that field applies to this specific requirement and its omission prevents import  A field absent from the source is not automatically required  Do not demand data rules dependencies quality measures or User Story fields merely because they exist in the schema  Distinguish missing applicable information from not applicable information  Identify contradictions and unsupported assumptions  Write issue in the requested natural language without raw schema names  Suggest an exact source quote only when it appears in an AI permitted source document  Do not invent fields requirements actors acceptance criteria response codes or quality limits  Do not generate test cases or approve import"""
    model_config = ConfigDict(extra="forbid")

    capability: Literal["requirement_template_review"]
    readiness: Literal["ready_for_import", "needs_information", "conflict"]
    findings: List[RequirementTemplateReviewFindingOutput] = Field(default_factory=list, max_length=50)
    evidence_refs: List[str] = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=20)


class TestabilityBlueprintObligationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=160)
    obligation: str = Field(min_length=2, max_length=2000)
    source_ref: str = Field(min_length=1, max_length=200)
    source_quote: str = Field(min_length=2, max_length=2000)


class TestabilityBlueprintClarificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=160)
    category: RequirementQualityCategory
    question: str = Field(min_length=2, max_length=1000)
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    evidence_refs: List[str] = Field(min_length=1, max_length=20)
    source_quote: str = Field(min_length=2, max_length=2000)
    unlocks_obligation_keys: List[str] = Field(default_factory=list, max_length=100)


class TestabilityBlueprintCompilationOutput(BaseModel):
    """Compile verified source facts into uniquely keyed test obligations and actionable clarifications. Each obligation needs one allowed exact source quote that directly entails it. Do not invent behavior, expected results, actors, limits, or rules. Ask a clarification only when missing or conflicting source information blocks a specific obligation. Use stable concise keys and do not repeat equivalent obligations. Do not generate test cases."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["testability_blueprint_compilation"] = "testability_blueprint_compilation"
    obligations: List[TestabilityBlueprintObligationOutput] = Field(default_factory=list, max_length=300)
    clarifications: List[TestabilityBlueprintClarificationOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_blueprint_links(self):
        obligation_keys = [item.key for item in self.obligations]
        clarification_codes = [item.code for item in self.clarifications]
        if len(set(obligation_keys)) != len(obligation_keys):
            raise ValueError("benchmark_obligation_keys_must_be_unique")
        if len(set(clarification_codes)) != len(clarification_codes):
            raise ValueError("benchmark_clarification_codes_must_be_unique")
        if any(
            not set(item.unlocks_obligation_keys).issubset(obligation_keys)
            for item in self.clarifications
        ):
            raise ValueError("benchmark_clarification_unlocks_unknown_obligation")
        return self


class ClarificationBaselineQuestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=160)
    category: RequirementQualityCategory
    question: str = Field(min_length=2, max_length=1000)
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    evidence_refs: List[str] = Field(min_length=1, max_length=20)
    source_quote: str = Field(min_length=2, max_length=2000)


class ClarificationBaselineOutput(BaseModel):
    """Ask the smallest set of source-grounded questions needed to make a requirement testable, without first decomposing it into test obligations. Return no question for details that are not needed to test stated behavior. Never invent missing behavior or treat absence alone as a defect."""

    model_config = ConfigDict(extra="forbid")

    capability: Literal["clarification_baseline"] = "clarification_baseline"
    clarifications: List[ClarificationBaselineQuestionOutput] = Field(default_factory=list, max_length=100)
    evidence_refs: List[str] = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list, max_length=50)

