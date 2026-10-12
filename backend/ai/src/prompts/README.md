# Bản đồ sở hữu AI

## Luồng chung

`Giao diện` gọi API nghiệp vụ của Testing  Service nghiệp vụ kiểm tra quyền dự án và chuẩn bị evidence đã được phép đọc  `backend/testing/src/core/ai_assistance.py` gọi API nội bộ AI  `backend/ai/src/api/inference.py` chọn prompt trong `backend/ai/src/prompts` và schema bằng `output_schema` tại `backend/ai/src/schemas/inference.py`  `backend/ai/src/services/ai_assistance.py` gọi model và trả về bản nháp có evidence refs

Prompt nghiệp vụ Testing có một chủ sở hữu là `backend/ai/src/prompts/testing.py`  Prompt của riêng Requirements nằm trong `backend/ai/src/prompts/requirements.py` và được gọi từ prompt Testing  Schema đầu ra được phát hiện từ capability trong `output_schema` nên không có bảng cấu hình capability riêng

AI không được tự thay đổi requirement test case hay báo cáo  Service nghiệp vụ chỉ lưu bản nháp hoặc đề xuất  Người dùng rà soát rồi xác nhận theo workflow hiện có

## Requirements

| Chức năng | API giao diện | Service sở hữu evidence và workflow | Capability | Schema đầu ra |
| --- | --- | --- | --- | --- |
| Rà soát chất lượng yêu cầu | `modules/requirements/api/requirement_analysis.py` | `modules/requirements/services/requirement_ai.py` | `requirement_quality_analysis` | `RequirementQualityModelOutput` |
| Tổng hợp mẫu từ tài liệu được cho phép đọc | `modules/requirements/api/requirement_templates.py` | `modules/requirements/services/requirement_templates.py` | `requirement_template_synthesis` | `RequirementTemplateSynthesisOutput` |
| Kiểm tra mẫu trước khi nhập | `modules/requirements/api/requirement_templates.py` | `modules/requirements/services/requirement_templates.py` | `requirement_template_review` | `RequirementTemplateReviewOutput` |
| Xem trước và xác nhận nhập User Story SRS OpenAPI | `modules/requirements/api/requirement_imports.py` | `modules/requirements/services/requirement_import_workflow.py` | Không gọi AI | `RequirementCandidateReview` và `ImportConfirm` |

Nhập Requirements giữ nguồn và vị trí trích dẫn  Điều kiện sẵn sàng nhập và điều kiện đủ chất lượng để duyệt là hai bước nghiệp vụ khác nhau

## Test Design

| Chức năng | API giao diện | Service sở hữu evidence và workflow | Capability | Schema đầu ra |
| --- | --- | --- | --- | --- |
| Gợi ý kỹ thuật kiểm thử phù hợp với một phiên bản yêu cầu | `modules/design/api/test_design.py` | `modules/design/services/test_case_assistance.py` | `technique_recommendation` | `TechniqueRecommendationsOutput` |
| Sinh test case hoặc kịch bản từ requirement đã baseline | `modules/design/api/test_design.py` | `modules/design/services/generation.py` | `test_generation` hoặc `scenario_generation` | `GeneratedCasesOutput` |
| Sinh điều kiện kiểm thử trước khi sinh case | `modules/design/api/test_analysis.py` | `modules/design/services/test_analysis.py` | `test_condition_generation` | `TestConditionSuggestionsOutput` |
| Gợi ý kiểm thử bảo mật | `modules/design/api/design_suggestions.py` | `modules/design/services/design_suggestion.py` | `security_test_generation` | `SecuritySuggestionsOutput` |
| Lập bản nháp kế hoạch hiệu năng | `modules/design/api/design_suggestions.py` | `modules/design/services/design_suggestion.py` | `performance_plan_generation` | `PerformanceSuggestionsOutput` |
| Sinh bản nháp script tự động hóa | `modules/integrations/api/automation_scripts.py` | `modules/integrations/services/automation_script.py` | `automation_script_generation` | `AutomationScriptOutput` |

Kỹ thuật kiểm thử là lựa chọn một hoặc nhiều kỹ thuật  AI có thể đề xuất nhưng không ép chọn tất cả  Lưu test case vẫn đi qua kiểm tra evidence trùng lặp và version resolution

## Chất lượng và thực thi

| Chức năng | API giao diện | Service sở hữu evidence và workflow | Capability | Schema đầu ra |
| --- | --- | --- | --- | --- |
| Hỏi đáp tri thức dự án | `modules/quality/api/analytics.py` | `modules/quality/services/analytics.py` | `project_question` | `ProjectQuestionOutput` |
| Phân tích tác động thay đổi | `modules/quality/api/changes.py` | `modules/quality/services/impact_assistance.py` | `impact_analysis` | `ImpactClassificationOutput` |
| Giả thuyết nguyên nhân gốc | `modules/quality/api/defect_prevention.py` | `modules/quality/services/causal_analysis_assistance.py` | `causal_analysis` | `CausalHypothesesOutput` |
| Bản nháp diễn giải báo cáo trạng thái | `modules/execution/api/test_status_reports.py` | `modules/execution/services/test_status_report.py` | `status_report_narrative` | `StatusReportNarrativeOutput` |
| Bản nháp diễn giải và gom bài học báo cáo hoàn tất | `modules/execution/api/test_completion.py` | `modules/execution/services/test_completion_assistance.py` | `completion_report_narrative` hoặc `lessons_learned_clustering` | `CompletionReportNarrativeOutput` hoặc `LessonsLearnedClustersOutput` |

## Agent tổng quát

API agent ở `backend/ai/src/api/agents.py`  Điều phối một tác vụ trong mỗi lượt chạy ở `backend/ai/src/agents/runner`  Prompt nằm ở `backend/ai/src/prompts/agents.py`  Schema nằm ở `backend/ai/src/schemas/agent.py`

Agent chỉ gọi capability đã có evidence và hợp đồng đầu ra  Một lượt hoàn tất sau kết quả tác vụ đầu tiên  Agent không tự lập chuỗi tác vụ mới và không tự áp dụng thay đổi vào dự án
