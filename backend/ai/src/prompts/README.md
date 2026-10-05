# Requirements AI map

| Chức năng | API cho giao diện | Nghiệp vụ | Prompt | Schema AI |
| --- | --- | --- | --- | --- |
| Rà soát chất lượng yêu cầu | `backend/testing/src/modules/requirements/api/requirement_analysis.py` | `backend/testing/src/modules/requirements/services/requirement_ai.py` | `backend/ai/src/prompts/testing.py` | `RequirementQualityModelOutput` trong `backend/ai/src/schemas/inference.py` |
| Tổng hợp mẫu Requirements | `backend/testing/src/modules/requirements/api/requirement_templates.py` | `backend/testing/src/modules/requirements/services/requirement_templates.py` | `backend/ai/src/prompts/requirements.py` qua `backend/ai/src/prompts/testing.py` | `RequirementTemplateSynthesisOutput` trong `backend/ai/src/schemas/inference.py` |
| Kiểm tra mẫu Requirements đã lưu | `backend/testing/src/modules/requirements/api/requirement_templates.py` | `backend/testing/src/modules/requirements/services/requirement_templates.py` | `backend/ai/src/prompts/testing.py` | `RequirementTemplateReviewOutput` trong `backend/ai/src/schemas/inference.py` |
| Xem trước và xác nhận nhập | `backend/testing/src/modules/requirements/api/requirement_imports.py` | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py` | Không gọi AI | `RequirementCandidateReview` và `ImportConfirm` trong `backend/testing/src/schemas/contracts/requirements.py` |

Các prompt chỉ đề xuất bản nháp  Quyền đọc nguồn được kiểm tra trong Testing trước khi gọi AI  Duyệt hoặc baseline vẫn thuộc quy trình Requirements
