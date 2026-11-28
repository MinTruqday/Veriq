# Veriq system overview

## Service extraction totals
Service | Collections | Route handlers | Frontend pages | Domain classes | ERD fields | BCE groups
---|---:|---:|---:|---:|---:|---:
authentication | 12 | 107 | 9 | 1 | 132 | 22
content | 7 | 41 | 0 | 6 | 30 | 17
cloud | 5 | 77 | 3 | 5 | 33 | 35
notification | 2 | 9 | 2 | 2 | 3 | 4
testing | 76 | 369 | 37 | 70 | 481 | 125
worker | 2 | 9 | 0 | 0 | 28 | 1
ai | 12 | 35 | 0 | 5 | 87 | 31

## Static inter-service references
Caller | Referenced service | Evidence
---|---|---
ai | content | `backend/ai/src/agents/runner/nodes.py`
ai | content | `backend/ai/src/core/model_runtime.py`
ai | content | `backend/ai/src/runtime/output.py`
ai | content | `backend/ai/src/schemas/inference_requirements.py`
ai | content | `backend/ai/src/services/change_simulation.py`
ai | content | `backend/ai/src/services/inference.py`
ai | content | `backend/ai/src/tools/grounded_publication.py`
ai | content | `backend/ai/src/utils/huggingface.py`
ai | content | `backend/ai/src/utils/model_provider.py`
authentication | ai | `backend/authentication/src/services/platform_ai.py`
authentication | ai | `backend/authentication/src/services/platform_control_operations.py`
authentication | ai | `backend/authentication/src/services/platform_operations.py`
authentication | cloud | `backend/authentication/src/services/platform_control_operations.py`
authentication | cloud | `backend/authentication/src/services/platform_operations.py`
authentication | content | `backend/authentication/src/services/platform_operations.py`
authentication | testing | `backend/authentication/src/services/platform_accounts.py`
authentication | testing | `backend/authentication/src/services/platform_control_operations.py`
authentication | testing | `backend/authentication/src/services/platform_operations.py`
authentication | testing | `backend/authentication/src/services/platform_projects.py`
authentication | worker | `backend/authentication/src/services/platform_control_operations.py`
authentication | worker | `backend/authentication/src/services/platform_operations.py`
authentication | worker | `backend/authentication/src/services/platform_projects.py`
testing | content | `backend/testing/src/core/common.py`
testing | content | `backend/testing/src/core/rich_text.py`
testing | content | `backend/testing/src/modules/design/services/linters.py`
testing | content | `backend/testing/src/modules/design/services/test_case_lifecycle.py`
testing | content | `backend/testing/src/modules/design/services/test_case_query.py`
testing | content | `backend/testing/src/modules/design/services/test_case_records.py`
testing | content | `backend/testing/src/modules/design/services/test_case_review.py`
testing | content | `backend/testing/src/modules/design/services/test_case_transfer.py`
testing | content | `backend/testing/src/modules/execution/services/report_document.py`
testing | content | `backend/testing/src/modules/execution/services/test_run.py`
testing | content | `backend/testing/src/modules/integrations/api/api_artifacts.py`
testing | content | `backend/testing/src/modules/quality/services/impact_ai.py`
testing | content | `backend/testing/src/modules/quality/services/impact_automation.py`
testing | content | `backend/testing/src/modules/quality/services/proposal_application.py`
testing | content | `backend/testing/src/modules/quality/services/requirement_version_diff.py`
testing | content | `backend/testing/src/modules/quality/services/review_comment.py`
testing | content | `backend/testing/src/modules/requirements/services/document_reader.py`
testing | content | `backend/testing/src/modules/requirements/services/requirement_ai.py`
testing | content | `backend/testing/src/modules/requirements/services/requirement_documents.py`
testing | content | `backend/testing/src/modules/requirements/services/requirement_import.py`
testing | content | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py`
testing | content | `backend/testing/src/modules/requirements/services/requirement_sources.py`
testing | content | `backend/testing/src/modules/requirements/services/requirement_templates.py`
testing | content | `backend/testing/src/modules/requirements/services/requirement_workflow.py`
testing | content | `backend/testing/src/schemas/contracts/common.py`
