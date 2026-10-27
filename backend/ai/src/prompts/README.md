# Bản đồ prompt của AI

Đây là mục lục sở hữu prompt, không phải nơi chứa prompt dùng chung. Mỗi module chức năng giữ nội dung của nó; các tệp `agents.py`, `catalog.py`, `requirements.py` và `structured.py` chỉ còn xuất lại tên cũ để tránh làm gãy import.

## Agent tự động hóa

| Module | Prompt/hàm sở hữu | Nơi gọi | Mục đích |
| --- | --- | --- | --- |
| `agent_planning.py` | `agent_plan_prompt`, `AGENT_PLAN`, `verified_source_fact_instruction`, `change_simulation_instruction` | `agents/runner/nodes.py` | Chọn tác vụ/công cụ theo mục tiêu, quyền và bằng chứng; quy định cách dùng fact và mô phỏng thay đổi |
| `agent_execution.py` | `agent_execution_prompt`, `AGENT_EXECUTION` | `agents/agent.py` | Đánh giá kết quả gọi công cụ và ghi nhận điều đã làm/còn thiếu |
| `automation.py` | `automation_fact_extraction_prompt` | `agents/runner/automation_graph.py` | Trích fact và câu hỏi chưa được nguồn trả lời; chỉ giữ fact có trích dẫn nguyên văn |
| `automation_events.py` | `generic_event_objective`, `document_ingested_objective`, `api_operation_confirmed_objective`, `requirement_changed_objective`, `defect_recorded_objective`, `test_execution_recorded_objective`, `test_plan_approved_objective`, `test_plan_changed_objective`, `test_execution_observation_objective`, `work_item_changed_observation_objective`, `test_case_changed_observation_objective`, `test_case_approved_observation_objective`, `release_changed_observation_objective` | `services/automation.py`, `agents/runner/automation_event_tasks.py` | Mục tiêu riêng theo sự kiện; tự chạy các bước được cấp quyền sự kiện và qua kiểm tra xác định, giữ nguyên gate nghiệp vụ và không báo thành công khi chưa đọc lại artifact |
| `requirement_templates.py` | `requirement_document_synthesis_instruction`, `REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS`, `REQUIREMENT_TEMPLATE_REVIEW_INSTRUCTIONS` | `tools/requirement_document_workflow.py`, `prompts/testing.py` | Tổng hợp mẫu Requirement từ facts đã xác minh và rà mẫu có nguồn, không tự quyết nhập |
| `test_generation.py` | `requirement_test_generation_instruction`, `focused_requirement_test_generation_instruction`, `retry_grounded_requirement_test_generation_instruction`, `uncovered_obligation_test_generation_instruction` | Requirement ingestion/change workflows | Tạo Test Case cho phạm vi còn thiếu, có căn cứ và tránh trùng |
| `test_design.py` | `TEST_CASE_GENERATION_CONTRACT`, `TECHNIQUE_RECOMMENDATION_CONTRACT`, `AUTOMATED_TECHNIQUE_RECOMMENDATION_INSTRUCTION`, `TEST_CONDITION_GENERATION_CONTRACT`, `TEST_DESIGN_CAPABILITY_CONTRACTS` | `prompts/testing.py` qua `services/ai_automation.py`, `tools/test_design_tools.py` | Quy tắc sinh ca, gợi ý kỹ thuật, sinh điều kiện và chỉ gắn kỹ năng cần thiết khi nguồn ghi rõ; schema chỉ mô tả cấu trúc dữ liệu |
| `quality_capabilities.py` | `SECURITY_TEST_GENERATION_CONTRACT`, `PERFORMANCE_PLAN_GENERATION_CONTRACT`, `AUTOMATION_SCRIPT_GENERATION_CONTRACT`, `CAUSAL_ANALYSIS_CONTRACT`, `STATUS_REPORT_NARRATIVE_CONTRACT`, `COMPLETION_REPORT_NARRATIVE_CONTRACT`, `LESSONS_LEARNED_CLUSTERING_CONTRACT`, `QUALITY_CAPABILITY_CONTRACTS` | `prompts/testing.py` qua `services/ai_automation.py` | Hợp đồng cho kiểm thử chuyên sâu, báo cáo và phân tích; schema chỉ mô tả cấu trúc dữ liệu |
| `testability_blueprint.py` | `TESTABILITY_BLUEPRINT_COMPILATION` | `services/testability_blueprint.py` qua `services/ai_automation.py` | Biên dịch fact đã xác minh (loại fact + trích dẫn gốc) thành nghĩa vụ kiểm thử và câu hỏi làm rõ; nghĩa vụ phải trích từ fact đã trích, không chỉ từ đoạn văn chứa nó |
| `testability_blueprint_review.py` | `build_testability_blueprint_grounding_prompt` | `services/testability_blueprint.py` qua `services/ai_automation.py` | Rà nghĩa của từng nghĩa vụ/câu hỏi làm rõ với fact đã xác minh; chỉ trả cụm nội dung không được nguồn hỗ trợ, không viết lại ứng viên |
| `testability_benchmark.py` | `clarification_baseline_instruction`, `direct_generation_baseline_instruction`, `CLARIFICATION_BASELINE` | `services/testability_benchmark.py` qua `services/ai_automation.py` | Baseline hỏi làm rõ và sinh Test Case trực tiếp để so sánh; không lập nghĩa vụ trước |
| `change_simulation.py` | `change_simulation_report_instruction`, `IMPACT_ANALYSIS_CONTRACT` | `agents/runner/nodes.py`, `prompts/testing.py` qua `services/ai_automation.py` | Phân loại từng Test Case version liên kết bằng trích dẫn; bản vá xem trước chỉ nhận các trường Test Case có kiểu, không áp dụng trong lượt mô phỏng |
| `project_assistance.py` | `PROJECT_QUESTION_CONTRACT` | `prompts/testing.py` qua `services/ai_automation.py` | Trả lời câu hỏi dự án bằng chứng cứ đã truy xuất, nêu giới hạn khi nguồn không đủ |
| `skill_profile.py` | `build_skill_profile_extraction_prompt` | `services/skill_profile_extraction.py` | Trích kỹ năng/kinh nghiệm CV có dẫn chứng; giữ thời gian đúng nguyên văn khi có, không suy ra mức thành thạo hay số năm |
| `staffing_recommendation.py` | `build_staffing_recommendation_prompt` | `services/staffing_recommendation.py` | Xếp thứ tự ứng viên đủ điều kiện từ kỹ năng, kinh nghiệm, khả dụng, tải việc và chi phí; mọi lý do trỏ tới fact của đúng ứng viên |
| `defect_analysis.py` | `causal_hypothesis_instruction` | `tools/execution_workflows.py` | Tạo giả thuyết defect, không khẳng định nguyên nhân đã xác nhận |
| `requirement_analysis.py` | `requirement_quality_analysis_instruction` | `testing/modules/requirements/services/requirement_ai.py` qua `tools/requirement_change_workflow.py` | Đánh giá tự động Requirement khi có sự kiện thay đổi; UI chỉ đọc kết quả |
| `prompt_data.py` | `prompt_json` | Các prompt có đầu vào động | Tuần tự hóa JSON và escape dấu đóng thẻ trước khi nhúng dữ liệu vào prompt |

Các objective bổ sung của `automation_events.py` là `performance_configuration_approved_objective`, `status_report_created_objective` và `test_completion_report_created_objective`; chúng được gọi qua `services/automation.py` và `agents/runner/automation_event_tasks.py` như các objective sự kiện cùng module.

## Requirements và kiểm thử

| Module | Prompt/hàm sở hữu | Nơi gọi | Mục đích |
| --- | --- | --- | --- |
| `testing_identity.py` | `TESTING_IDENTITY` | `testing_contract.py` | Vai trò và mục tiêu của agent kiểm thử |
| `testing_analysis.py` | `TESTING_ANALYSIS_PROTOCOL` | `testing_contract.py` | Các bước phân tích nội bộ và kiểm tra tính nhất quán |
| `testing_language.py` | `TESTING_LANGUAGE_POLICY` | `testing_contract.py` | Ngôn ngữ đầu ra và bảo toàn định danh kỹ thuật |
| `testing_evidence.py` | `TESTING_EVIDENCE_CONTRACT` | `testing_contract.py` | Ranh giới bằng chứng, trích dẫn và giới hạn suy diễn |
| `testing_governance.py` | `TESTING_GOVERNANCE` | `testing_contract.py` | Tách capability gợi ý khỏi workflow tự động đã được phân quyền; nền tảng vẫn kiểm soát quyền, audit và xác minh |
| `testing_examples.py` | `TESTING_FEW_SHOT_EXAMPLES` | `testing_contract.py` | Ví dụ hành vi đúng/sai của hợp đồng kiểm thử |
| `testing_contract.py` | `STRUCTURED_TESTING_TEMPLATE` | `testing.py` | Ghép các phần hợp đồng dùng chung, không sở hữu nội dung nghiệp vụ riêng |
| `testing.py` | `build_testing_prompt`, `validate_prompt_contract_registry`, `prompt_contract_fingerprint`, `prompt_execution_fingerprint`, `prompt_messages_fingerprint` | `services/ai_automation.py`, `services/inference.py` | Ghép hợp đồng theo capability, kiểm tra capability/schema/prompt có khai báo tương ứng; fingerprint hợp đồng ổn định và fingerprint từng bộ messages thực sự gửi, gồm cả lần sửa output; chỉ lưu hash, không lưu nội dung nguồn trong metadata |
| `test_case_grounding.py` | `build_generated_cases_grounding_prompt` | `services/ai_automation.py` | Rà trích dẫn và độ bám nguồn của Test Case được sinh |


## Hạ tầng prompt

| Module | Prompt/hàm sở hữu | Nơi gọi | Mục đích |
| --- | --- | --- | --- |
| `model_output.py` | `schema_instruction`, `correction_instruction` | `services/inference.py`, `utils/huggingface.py` | Chỉ dẫn tạo và sửa đầu ra theo schema |
| `tool_selection.py` | `tool_selection_instruction`, `tool_selection_correction_instruction` | `utils/huggingface.py` | Chọn một công cụ đã đăng ký theo schema |
| `security.py` | `prompt_injection_detector`, `security_scan` | `core/security/guardrails.py`, `core/security/scanning.py` | Phân loại chỉ dẫn không tin cậy và rà nội dung an toàn |
| `retrieval.py` | `cross_document_query`, `document_global_summary` | `services/inference.py` | Tách truy vấn đa tài liệu và tóm tắt tài liệu tri thức |
| `evaluation.py` | `eval_judge`, `evaluation_harness_prompt` | `services/evaluation.py` | Chấm đầu ra trong harness đánh giá |

## Định dạng dùng chung

Chỉ dẫn tĩnh gửi cho model viết bằng tiếng Anh thống nhất; đây là ngôn ngữ của prompt, không phải ngôn ngữ đầu ra. Ngôn ngữ đầu ra phải lấy từ locale của người dùng được truyền vào capability, không mặc định tiếng Việt; trích dẫn nguồn, mã định danh, tên kỹ thuật và giá trị giao thức giữ nguyên như nguồn. Prompt độc lập dùng thứ tự có nhãn thống nhất, không ghép chỉ dẫn và dữ liệu vào một đoạn văn tự do:

1. `<system_identity>` rồi `<objective>` nêu vai trò và việc cần làm.
2. `<trust_boundary>` phân biệt chỉ dẫn đáng tin với tài liệu, CV, câu trích dẫn và dữ liệu MCP không đáng tin.
3. `<output_language>` quy định ngôn ngữ trường nội dung hướng người dùng theo locale đã truyền; không gán ngôn ngữ mặc định. Không dùng tên thay thế như `<language_policy>`.
4. `<evidence_rules>` / `<workflow_rules>` ghi căn cứ, quyền và hành vi được phép.
5. `<output_contract>` nêu schema/định dạng trả về.
6. Dữ liệu đầu vào đặt riêng sau hợp đồng, trong vùng có tên `<untrusted_...>` và được tuần tự hóa theo capability.

Prompt độc lập phải có vai trò, mục tiêu, ranh giới tin cậy và hợp đồng đầu ra. Prompt con hoặc phần ghép được quyền kế thừa mục đã có từ hợp đồng cha; không lặp lại cùng một chỉ dẫn nhiều lần. `<output_language>` bắt buộc khi capability tạo nội dung hướng người dùng, nhưng không cần cho bộ chọn công cụ hay bộ sửa JSON thuần cấu trúc. Capability-specific business rules phải nằm trong module prompt sở hữu; schema chỉ giữ cấu trúc, kiểu dữ liệu và constraint máy kiểm tra được. Prompt theo sự kiện là objective con được nhúng vào prompt Agent, nên vẫn giữ ranh giới quyền, dữ kiện thiếu và xác minh hậu điều kiện.

Mọi capability của `TestingAutomationRequest` phải có hợp đồng tường minh trong module prompt và được map tại `testing.py`; không lấy docstring schema làm fallback cho chỉ dẫn nghiệp vụ. Prompt mới hoặc prompt được sửa phải có owner ở bảng trên, giữ payload đúng output schema, bảo vệ vùng dữ liệu không tin cậy và có kiểm tra contract/model phù hợp. Không đưa token hoặc quyền vào prompt để thay thế kiểm tra backend.

## Luồng gọi chính

`api/automation.py` → `services/automation.py` → `runtime/automation_worker.py` → `agents/runner/automation_graph.py` → planner, tool, xác minh và tổng hợp. Trạng thái vận hành được lưu trong checkpoint, audit và kết quả lượt chạy của Veriq; runtime không gửi trace tới nền tảng bên ngoài.

Sự kiện tài liệu mới đi qua trích xuất fact đã xác minh trước khi workflow Requirements nhận chúng. Planner nhận lại chính các fact có quote thuộc evidence của run, cùng reference của artifact và phiên bản; fact không được xác minh không trở thành căn cứ sinh artifact. Mô phỏng thay đổi yêu cầu chạy tối đa hai lượt đọc có giới hạn: đọc đúng phiên bản Requirement baseline và ma trận liên kết của dự án, sau đó chỉ khi có liên kết tới phiên bản Test Case thì đọc các phiên bản đó trong giới hạn công cụ mỗi lượt. Agent so sánh baseline, nội dung đề xuất và Test Case đã đọc để đưa ra phân loại cùng căn cứ; phần vượt giới hạn phải được báo là chưa đối chiếu, không kết luận ảnh hưởng. Nội dung đề xuất không được coi là bằng chứng chuẩn. Run `CHANGE_SIMULATION` chỉ cho phép công cụ `READ`; nó không ghi Requirement, Test Case, waiver hay quyết định Release.

Blueprint được xác minh được lưu thành lịch sử phiên bản theo dự án trong `automation_project_blueprints`; cùng nguồn và cùng nội dung biên dịch được gộp idempotent, còn khi nguồn hoặc blueprint đổi thì tạo phiên bản mới. API đọc lịch sử là `/tu-dong-hoa-ai/du-an/{project_id}/ho-so-kha-nang-kiem-thu`; ngoài membership, API yêu cầu quyền `requirement.read` vì blueprint chứa nội dung và nguồn Requirement.

MCP chỉ là cổng công cụ ngoài theo kết nối dự án, danh sách tool đọc được cấp rõ ràng và quyền đọc của project. Output MCP được kiểm tra an toàn trước khi trở lại agent. Service Veriq tiếp tục sở hữu dữ liệu, quyền, workflow, version và audit nghiệp vụ.

## Ranh giới

- Prompt không cấp quyền. Quyền cuối cùng do service nghiệp vụ và registry công cụ kiểm tra.
- Nội dung tài liệu và kết quả MCP là dữ liệu không tin cậy, không phải chỉ dẫn cho agent.
- Không lưu prompt nghiệp vụ trong JSON hay tệp policy tổng hợp.
- Khi sửa prompt, cập nhật đúng module sở hữu và chạy kiểm tra đầu ra của capability tương ứng.
