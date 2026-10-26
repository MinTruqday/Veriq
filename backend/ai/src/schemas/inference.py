from typing import get_args

from pydantic import BaseModel

from src.schemas.inference_change_simulation import ChangeSimulationReportOutput
from src.schemas.inference_impact import (
    ImpactClassificationOutput,
    ImpactClassificationSuggestionOutput,
    MaintenanceTestCasePatchOutput,
    MaintenanceTestStepOutput,
    NewTestCandidateOutput,
)
from src.schemas.inference_quality import (
    AutomationScriptOutput,
    AutomationScriptSuggestionOutput,
    CausalHypothesesOutput,
    CausalHypothesisSuggestionOutput,
    CompletionReportNarrativeOutput,
    CompletionReportNarrativeSuggestionOutput,
    LessonsLearnedClustersOutput,
    LessonsLearnedClusterSuggestionOutput,
    PerformanceSuggestionOutput,
    PerformanceSuggestionsOutput,
    SecuritySuggestionOutput,
    SecuritySuggestionsOutput,
    StatusReportNarrativeOutput,
    StatusReportNarrativeSuggestionOutput,
)
from src.schemas.inference_requests import (
    CrossDocumentExpansionRequest,
    KnowledgeChunkSafetyRequest,
    KnowledgeDocumentSummaryRequest,
    TestingAutomationDegradedMode,
    TestingAutomationRequest,
    TestingAutomationResult,
    TestingAutomationStatus,
    TestingEvidence,
    VerifiedSourceFactCitation,
)
from src.schemas.inference_requirements import (
    ClarificationBaselineOutput,
    ClarificationBaselineQuestionOutput,
    RequirementAcceptanceCriterionSuggestionOutput,
    RequirementQualityFindingOutput,
    RequirementQualityModelOutput,
    RequirementRevisionSuggestionOutput,
    RequirementTemplateAPIOperationOutput,
    RequirementTemplateContextOutput,
    RequirementTemplateReviewFindingOutput,
    RequirementTemplateReviewOutput,
    RequirementTemplateSuggestionOutput,
    RequirementTemplateSynthesisOutput,
    TestabilityBlueprintClarificationOutput,
    TestabilityBlueprintCompilationOutput,
    TestabilityBlueprintObligationOutput,
)
from src.schemas.inference_shared import ProjectQuestionOutput
from src.schemas.inference_test_design import (
    GeneratedCaseGroundingReview,
    GeneratedCaseOutput,
    GeneratedCasesGroundingReview,
    GeneratedCasesOutput,
    GeneratedEvidenceQuoteOutput,
    GeneratedStepOutput,
    TechniqueRecommendationItemOutput,
    TechniqueRecommendationsOutput,
    TestConditionSuggestionOutput,
    TestConditionSuggestionsOutput,
    TestDesignChallengeOutput,
)

__all__ = [
    "AutomationScriptOutput",
    "AutomationScriptSuggestionOutput",
    "CausalHypothesesOutput",
    "CausalHypothesisSuggestionOutput",
    "ChangeSimulationReportOutput",
    "ClarificationBaselineOutput",
    "ClarificationBaselineQuestionOutput",
    "CompletionReportNarrativeOutput",
    "CompletionReportNarrativeSuggestionOutput",
    "CrossDocumentExpansionRequest",
    "GeneratedCaseGroundingReview",
    "GeneratedCaseOutput",
    "GeneratedCasesGroundingReview",
    "GeneratedCasesOutput",
    "GeneratedEvidenceQuoteOutput",
    "GeneratedStepOutput",
    "ImpactClassificationOutput",
    "ImpactClassificationSuggestionOutput",
    "KnowledgeChunkSafetyRequest",
    "KnowledgeDocumentSummaryRequest",
    "LessonsLearnedClusterSuggestionOutput",
    "LessonsLearnedClustersOutput",
    "MaintenanceTestCasePatchOutput",
    "MaintenanceTestStepOutput",
    "NewTestCandidateOutput",
    "PerformanceSuggestionOutput",
    "PerformanceSuggestionsOutput",
    "ProjectQuestionOutput",
    "RequirementAcceptanceCriterionSuggestionOutput",
    "RequirementQualityFindingOutput",
    "RequirementQualityModelOutput",
    "RequirementRevisionSuggestionOutput",
    "RequirementTemplateAPIOperationOutput",
    "RequirementTemplateContextOutput",
    "RequirementTemplateReviewFindingOutput",
    "RequirementTemplateReviewOutput",
    "RequirementTemplateSuggestionOutput",
    "RequirementTemplateSynthesisOutput",
    "SecuritySuggestionOutput",
    "SecuritySuggestionsOutput",
    "StatusReportNarrativeOutput",
    "StatusReportNarrativeSuggestionOutput",
    "TechniqueRecommendationItemOutput",
    "TechniqueRecommendationsOutput",
    "TestabilityBlueprintClarificationOutput",
    "TestabilityBlueprintCompilationOutput",
    "TestabilityBlueprintObligationOutput",
    "TestConditionSuggestionOutput",
    "TestConditionSuggestionsOutput",
    "TestDesignChallengeOutput",
    "TestingAutomationDegradedMode",
    "TestingAutomationRequest",
    "TestingAutomationResult",
    "TestingAutomationStatus",
    "TestingEvidence",
    "VerifiedSourceFactCitation",
    "output_schema",
]


def output_schema(capability):
    for schema in BaseModel.__subclasses__():
        if not schema.__module__.startswith("src.schemas.inference_") or not schema.__name__.endswith("Output"):
            continue
        field = schema.model_fields.get("capability")
        if field and capability in get_args(field.annotation):
            return schema
    raise ValueError("testing_capability_schema_missing")
