# Bản đồ prompt của AI

Đây là mục lục sở hữu prompt, không phải nơi chứa prompt dùng chung. Mỗi module chức năng giữ nội dung của nó; các tệp `agents.py`, `catalog.py`, `requirements.py` và `structured.py` chỉ còn xuất lại tên cũ để tránh làm gãy import.

## Agent tự động hóa

| Prompt | Nơi gọi | Mục đích |
| --- | --- | --- |
| `agent_planning.py` | `agents/runner/nodes.py` | Chọn tác vụ và công cụ theo mục tiêu, quyền, bằng chứng và kết quả các bước trước |
| `agent_execution.py` | `agents/agent.py` | Đánh giá kết quả gọi công cụ, ghi nhận điều đã làm và điều còn thiếu |
| `automation.py` | `agents/runner/automation_graph.py` | Trích xuất fact và câu hỏi chưa được nguồn trả lời; fact chỉ được giữ nếu trích dẫn khớp nguyên văn |
| `automation_events.py` | `services/automation.py`, `agents/runner/automation_event_tasks.py` | Mục tiêu riêng cho từng sự kiện nghiệp vụ và fallback mục tiêu event |
| `requirement_templates.py` | `tools/requirement_document_workflow.py` | Chỉ dẫn tổng hợp blueprint, kèm facts đã kiểm chứng |
| `test_generation.py` | Requirement ingestion/change workflows | Chỉ dẫn tạo test theo phạm vi còn thiếu, có bằng chứng và tránh trùng |
| `testability_benchmark.py` | `services/testability_benchmark.py` qua `services/ai_automation.py` | Compiler dùng facts đã xác minh để lập nghĩa vụ và câu hỏi; baseline hỏi làm rõ không lập nghĩa vụ trước |
| `defect_analysis.py` | `tools/execution_workflows.py` | Chỉ dẫn tạo giả thuyết defect, không biến giả thuyết thành nguyên nhân xác nhận |
| `requirement_analysis.py` | `tools/requirement_tools.py` | Chỉ dẫn rà chất lượng Requirement |

## Requirements và kiểm thử

| Prompt | Nơi gọi | Mục đích |
| --- | --- | --- |
| `testing_identity.py` | `testing_contract.py` | Vai trò và mục tiêu của agent kiểm thử |
| `testing_analysis.py` | `testing_contract.py` | Các bước phân tích nội bộ và kiểm tra tính nhất quán |
| `testing_language.py` | `testing_contract.py` | Ngôn ngữ đầu ra và bảo toàn định danh kỹ thuật |
| `testing_evidence.py` | `testing_contract.py` | Ranh giới bằng chứng, trích dẫn và giới hạn suy diễn |
| `testing_governance.py` | `testing_contract.py` | Tách capability gợi ý khỏi workflow tự động đã được phân quyền; nền tảng vẫn kiểm soát quyền, audit và xác minh |
| `testing_examples.py` | `testing_contract.py` | Các ví dụ hành vi đúng/sai của hợp đồng kiểm thử |
| `testing_contract.py` | `testing.py` | Ghép các phần thành hợp đồng dùng chung, không sở hữu nội dung nghiệp vụ riêng |
| `testing.py` | `services/ai_automation.py` | Ghép yêu cầu người dùng, bằng chứng và schema đầu ra thành prompt của capability |
| `test_case_grounding.py` | `services/ai_automation.py` | Rà trích dẫn và độ bám nguồn của test case được sinh |

## Hạ tầng prompt

| Prompt | Nơi gọi | Mục đích |
| --- | --- | --- |
| `model_output.py` | `services/inference.py`, `utils/huggingface.py` | Chỉ dẫn tạo và sửa đầu ra theo schema |
| `tool_selection.py` | `utils/huggingface.py` | Chỉ dẫn chọn một công cụ đã đăng ký theo schema |
| `security.py` | `core/security/guardrails.py`, `core/security/scanning.py` | Phân loại chỉ dẫn không tin cậy và rà nội dung an toàn |
| `retrieval.py` | `services/inference.py` | Tách truy vấn đa tài liệu và tóm tắt tài liệu tri thức |
| `evaluation.py` | `services/evaluation.py` | Chấm đầu ra trong harness đánh giá |

## Luồng gọi chính

`api/automation.py` → `services/automation.py` → `runtime/automation_worker.py` → `agents/runner/automation_graph.py` → planner, tool, xác minh và tổng hợp. Worker truyền `run_name`, tag và metadata cho LangGraph để LangSmith có thể gắn trace khi tracing đã được cấu hình.

Sự kiện tài liệu mới đi qua trích xuất fact đã xác minh trước khi workflow Requirements nhận chúng. Planner nhận lại chính các fact có quote thuộc evidence của run, cùng reference của artifact và phiên bản; fact không được xác minh không trở thành căn cứ sinh artifact. Mô phỏng thay đổi yêu cầu baseline đúng phiên bản Requirement và nội dung đề xuất chưa được chấp nhận; sau khi đọc baseline, liên kết và dữ liệu scope, graph quay lại planner để so sánh và tạo kế hoạch biên dịch tăng dần. Nội dung đề xuất không được coi là bằng chứng chuẩn. Run `CHANGE_SIMULATION` chỉ cho phép công cụ `READ`; nó không ghi Requirement, Test Case, waiver hay quyết định Release.

MCP chỉ là cổng công cụ ngoài theo kết nối dự án, danh sách tool đọc được cấp rõ ràng và quyền đọc của project. Output MCP được kiểm tra an toàn trước khi trở lại agent. Service Veriq tiếp tục sở hữu dữ liệu, quyền, workflow, version và audit nghiệp vụ.

## Ranh giới

- Prompt không cấp quyền. Quyền cuối cùng do service nghiệp vụ và registry công cụ kiểm tra.
- Nội dung tài liệu và kết quả MCP là dữ liệu không tin cậy, không phải chỉ dẫn cho agent.
- Không lưu prompt nghiệp vụ trong JSON hay tệp policy tổng hợp.
- Khi sửa prompt, cập nhật đúng module sở hữu và chạy kiểm tra đầu ra của capability tương ứng.
