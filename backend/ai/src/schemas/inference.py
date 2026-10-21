from typing import get_args

from pydantic import BaseModel

from src.schemas.inference_requests import (
    TestingAutomationStatus,
    TestingAutomationDegradedMode,
    CrossDocumentExpansionRequest,
    KnowledgeChunkSafetyRequest,
    KnowledgeDocumentSummaryRequest,
    TestingEvidence,
    TestingAutomationRequest,
    TestingAutomationResult,
)
from src.schemas.inference_shared import (
    ProjectQuestionOutput,
)
from src.schemas.inference_requirements import (
    RequirementQualityFindingOutput,
    RequirementAcceptanceCriterionSuggestionOutput,
    RequirementRevisionSuggestionOutput,
    RequirementQualityModelOutput,
    RequirementTemplateAPIOperationOutput,
    RequirementTemplateContextOutput,
    RequirementTemplateSuggestionOutput,
    RequirementTemplateSynthesisOutput,
    RequirementTemplateReviewFindingOutput,
    RequirementTemplateReviewOutput,
    TestabilityBlueprintObligationOutput,
    TestabilityBlueprintClarificationOutput,
    TestabilityBlueprintCompilationOutput,
    ClarificationBaselineQuestionOutput,
    ClarificationBaselineOutput,
)
from src.schemas.inference_test_design import (
    GeneratedStepOutput,
    GeneratedEvidenceQuoteOutput,
    GeneratedCaseOutput,
    GeneratedCasesOutput,
    GeneratedCaseGroundingReview,
    GeneratedCasesGroundingReview,
    TestDesignChallengeOutput,
    TechniqueRecommendationItemOutput,
    TechniqueRecommendationsOutput,
    TestConditionSuggestionOutput,
    TestConditionSuggestionsOutput,
)
from src.schemas.inference_impact import (
    ImpactClassificationSuggestionOutput,
    MaintenanceTestStepOutput,
    MaintenanceTestCasePatchOutput,
    NewTestCandidateOutput,
    ImpactClassificationOutput,
)
from src.schemas.inference_quality import (
    SecuritySuggestionOutput,
    SecuritySuggestionsOutput,
    PerformanceSuggestionOutput,
    PerformanceSuggestionsOutput,
    AutomationScriptSuggestionOutput,
    AutomationScriptOutput,
    CausalHypothesisSuggestionOutput,
    CausalHypothesesOutput,
    StatusReportNarrativeSuggestionOutput,
    StatusReportNarrativeOutput,
    CompletionReportNarrativeSuggestionOutput,
    CompletionReportNarrativeOutput,
    LessonsLearnedClusterSuggestionOutput,
    LessonsLearnedClustersOutput,
)

def output_schema(capability):
    for schema in BaseModel.__subclasses__():
        if not schema.__module__.startswith("src.schemas.inference_") or not schema.__name__.endswith("Output"):
            continue
        field = schema.model_fields.get("capability")
        if field and capability in get_args(field.annotation):
            return schema
    raise ValueError("testing_capability_schema_missing")
