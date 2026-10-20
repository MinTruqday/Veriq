# Bản đồ sở hữu AI

## Luồng chung

Luồng AI agent tự động hóa chạy nền theo sự kiện nghiệp vụ và có thể được gọi theo yêu cầu  Testing ghi sự kiện vào outbox  bộ phát sự kiện gửi qua API nội bộ đến `backend/ai/src/api/automation.py`  `backend/ai/src/services/automation.py` xác thực người yêu cầu và chọn chủ thể thực thi thuộc dự án  `backend/ai/src/runtime/automation_worker.py` chạy đồ thị LangGraph tại `backend/ai/src/agents/runner/automation_graph.py`

Prompt nghiệp vụ Testing có một chủ sở hữu là `backend/ai/src/prompts/testing.py`  Prompt của riêng Requirements nằm trong `backend/ai/src/prompts/requirements.py` và được gọi từ prompt Testing  Prompt trích xuất facts của AI automation nằm trong `backend/ai/src/prompts/automation.py`  Schema đầu ra được phát hiện từ capability trong `output_schema` nên không có bảng cấu hình capability riêng

Trong lượt chạy tự động, agent có thể thực hiện tuần tự các thao tác mà chủ thể thực thi được cấp quyền  Mỗi thao tác thay đổi phải qua kiểm tra quyền nghiệp vụ, kiểm tra phiên bản và đọc lại hậu điều kiện  Không yêu cầu người dùng xác nhận riêng từng thao tác  Đây không phải quyền vượt qua workflow: nếu thiếu quyền, bằng chứng hoặc dữ liệu bắt buộc thì lượt chạy dừng với trạng thái chặn hoặc chưa hoàn tất

Các luồng đầu-cuối chuyên biệt hiện có gồm xử lý tài liệu Requirements mới, tiếp tục xử lý phiên bản Requirement vừa thay đổi, tạo phân tích có giả thuyết khi ghi nhận defect, ghi nhận kết quả FAIL có defect liên kết vào đúng nghĩa vụ kiểm thử và tạo Test Run từ snapshot Test Plan đã duyệt  Thay đổi Test Plan được kiểm tra scope trước khi tự duyệt và tạo Test Run  Các sự kiện Work Item, Test Case và Release còn lại chỉ đọc lại hoặc kiểm tra chất lượng trong planner tổng quát; chúng không tự sửa hay tự đóng artifact khi sự kiện không thể hiện một ý định nghiệp vụ an toàn

Khi có defect, agent tạo hoặc phát lại hồ sơ phân tích theo idempotency key, sinh giả thuyết có evidence rồi đọc lại hồ sơ  Giả thuyết không được ghi thành nguyên nhân gốc đã xác nhận  Khi Test Plan được duyệt, agent tạo Test Run từ snapshot bất biến, khởi chạy nếu chủ thể thực thi có quyền và đọc lại phạm vi  Agent không tạo kết quả giả cho ca manual

## Requirements

| Chức năng | API giao diện | Service sở hữu evidence và workflow | Capability | Schema đầu ra |
| --- | --- | --- | --- | --- |
| Rà soát chất lượng yêu cầu | `modules/requirements/api/requirement_analysis.py` | `modules/requirements/services/requirement_ai.py` | `requirement_quality_analysis` | `RequirementQualityModelOutput` |
| Tổng hợp mẫu từ tài liệu được cho phép đọc | `modules/requirements/api/requirement_templates.py` | `modules/requirements/services/requirement_templates.py` | `requirement_template_synthesis` | `RequirementTemplateSynthesisOutput` |
| Kiểm tra mẫu trước khi nhập | `modules/requirements/api/requirement_templates.py` | `modules/requirements/services/requirement_templates.py` | `requirement_template_review` | `RequirementTemplateReviewOutput` |
| Đối chiếu trùng và nhập User Story SRS OpenAPI trong lượt automation được cấp quyền | `modules/requirements/api/requirement_imports.py` | `modules/requirements/services/requirement_import_workflow.py` | Agent gọi workflow import và đọc lại kết quả | `RequirementCandidateReview` và `ImportConfirm` |

Nhập Requirements giữ nguồn và vị trí trích dẫn  Điều kiện sẵn sàng nhập và điều kiện đủ chất lượng để duyệt là hai bước nghiệp vụ khác nhau

## Test Design

| Chức năng | API giao diện | Service sở hữu evidence và workflow | Capability | Schema đầu ra |
| --- | --- | --- | --- | --- |
| Gợi ý kỹ thuật kiểm thử phù hợp với một phiên bản yêu cầu | `modules/design/api/test_design.py` | `modules/design/services/test_case_automation.py` | `technique_recommendation` | `TechniqueRecommendationsOutput` |
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
| Phân tích tác động thay đổi | `modules/quality/api/changes.py` | `modules/quality/services/impact_automation.py` | `impact_analysis` | `ImpactClassificationOutput` |
| Giả thuyết nguyên nhân gốc | `modules/quality/api/defect_prevention.py` | `modules/quality/services/causal_analysis_automation.py` | `causal_analysis` | `CausalHypothesesOutput` |
| Bản nháp diễn giải báo cáo trạng thái | `modules/execution/api/test_status_reports.py` | `modules/execution/services/test_status_report.py` | `status_report_narrative` | `StatusReportNarrativeOutput` |
| Bản nháp diễn giải và gom bài học báo cáo hoàn tất | `modules/execution/api/test_completion.py` | `modules/execution/services/test_completion_automation.py` | `completion_report_narrative` hoặc `lessons_learned_clustering` | `CompletionReportNarrativeOutput` hoặc `LessonsLearnedClustersOutput` |

## Agent và luồng tự động hóa

API agent tương tác ở `backend/ai/src/api/agents.py`  Agent tự động hóa sự kiện được chạy bởi `backend/ai/src/runtime/automation_worker.py` và đồ thị tại `backend/ai/src/agents/runner/automation_graph.py`  Prompt nằm ở `backend/ai/src/prompts/agents.py`  Schema nằm ở `backend/ai/src/schemas/agent.py` và `backend/ai/src/schemas/automation.py`

Agent quan sát nguồn, trích facts, đánh giá bất định, lập kế hoạch, chạy công cụ được cấp quyền, quan sát kết quả để lập bước tiếp theo khi cần, rồi xác minh hậu điều kiện  Mọi thao tác và kết quả được ghi trong Automation Run, checkpoint và derivation receipt  Kết quả chưa đủ căn cứ hoặc chưa qua được kiểm tra nghiệp vụ phải được báo là chưa hoàn tất, không được diễn giải thành thành công

Đánh giá nghiên cứu của compiler nằm tại `backend/ai/src/services/testability_benchmark.py` và được gọi nội bộ qua `POST /suy-luan/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu`  Người đánh giá cung cấp tình huống và đáp án chuẩn; hệ thống đo trích dẫn thật thuộc nguồn, recall điểm cần làm rõ và recall nghĩa vụ kiểm thử cho compiler so với đầu ra sinh trực tiếp  Nó không dùng BLEU, ROUGE hoặc LLM-as-a-judge để tuyên bố chất lượng của luồng này
