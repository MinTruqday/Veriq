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
    ExecutionAssistanceDefectDraftOutput,
    ExecutionAssistanceObservationOutput,
    ExecutionAssistanceOutput,
    ExecutionAssistanceSuggestionOutput,
    TestDataSuggestionItemOutput,
    TestDataSuggestionsOutput,
)
from src.schemas.inference_requests import (
    CrossDocumentExpansionRequest,
    KnowledgeDocumentSummaryRequest,
    TestingAIDegradedMode,
    TestingCapabilityRequest,
    TestingCapabilityResult,
    TestingCapabilityStatus,
    TestingEvidence,
    VerifiedSourceFactCitation,
)
from src.schemas.inference_requirements import (
    RequirementAcceptanceCriterionSuggestionOutput,
    RequirementQualityModelOutput,
    RequirementQualityRecommendationOutput,
    RequirementRevisionSuggestionOutput,
    RequirementTemplateAPIOperationOutput,
    RequirementTemplateContextOutput,
    RequirementTemplateReviewFindingOutput,
    RequirementTemplateReviewOutput,
    RequirementTemplateSuggestionOutput,
    RequirementTemplateSynthesisOutput,
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
)
from src.schemas.inference_test_plan import (
    TestPlanFieldEvidenceOutput,
    TestPlanGenerationOutput,
    TestPlanRiskSuggestionOutput,
    TestPlanSuggestionOutput,
    TestPlanEvidenceQuoteOutput,
)

__all__ = [
    "AutomationScriptOutput",
    "AutomationScriptSuggestionOutput",
    "ChangeSimulationReportOutput",
    "ExecutionAssistanceDefectDraftOutput",
    "ExecutionAssistanceObservationOutput",
    "ExecutionAssistanceOutput",
    "ExecutionAssistanceSuggestionOutput",
    "CrossDocumentExpansionRequest",
    "GeneratedCaseGroundingReview",
    "GeneratedCaseOutput",
    "GeneratedCasesGroundingReview",
    "GeneratedCasesOutput",
    "GeneratedEvidenceQuoteOutput",
    "GeneratedStepOutput",
    "ImpactClassificationOutput",
    "ImpactClassificationSuggestionOutput",
    "KnowledgeDocumentSummaryRequest",
    "MaintenanceTestCasePatchOutput",
    "MaintenanceTestStepOutput",
    "NewTestCandidateOutput",
    "ProjectQuestionOutput",
    "RequirementAcceptanceCriterionSuggestionOutput",
    "RequirementQualityModelOutput",
    "RequirementQualityRecommendationOutput",
    "RequirementRevisionSuggestionOutput",
    "RequirementTemplateAPIOperationOutput",
    "RequirementTemplateContextOutput",
    "RequirementTemplateReviewFindingOutput",
    "RequirementTemplateReviewOutput",
    "RequirementTemplateSuggestionOutput",
    "RequirementTemplateSynthesisOutput",
    "TestDataSuggestionItemOutput",
    "TestDataSuggestionsOutput",
    "TechniqueRecommendationItemOutput",
    "TechniqueRecommendationsOutput",
    "TestConditionSuggestionOutput",
    "TestConditionSuggestionsOutput",
    "TestPlanEvidenceQuoteOutput",
    "TestPlanFieldEvidenceOutput",
    "TestPlanGenerationOutput",
    "TestPlanRiskSuggestionOutput",
    "TestPlanSuggestionOutput",
    "TestingAIDegradedMode",
    "TestingCapabilityRequest",
    "TestingCapabilityResult",
    "TestingCapabilityStatus",
    "TestingEvidence",
    "VerifiedSourceFactCitation",
    "output_schema",
]


def output_schema(capability):
    for schema in BaseModel.__subclasses__():
        if not schema.__module__.startswith(
            "src.schemas.inference_"
        ) or not schema.__name__.endswith("Output"):
            continue
        field = schema.model_fields.get("capability")
        if field and capability in get_args(field.annotation):
            return schema
    raise ValueError("testing_capability_schema_missing")
