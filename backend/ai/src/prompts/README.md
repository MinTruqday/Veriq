# Bản đồ prompt của AI

Đây là mục lục sở hữu prompt, không phải nơi chứa prompt dùng chung. Mỗi module chức năng giữ nội dung của nó; các tệp `agents.py`, `catalog.py`, `requirements.py` và `structured.py` chỉ còn xuất lại tên cũ để tránh làm gãy import.

## Agent tự động hóa

| Prompt | Nơi gọi | Mục đích |
| --- | --- | --- |
| `agent_planning.py` | `agents/runner/nodes.py` | Chọn tác vụ và công cụ theo mục tiêu, quyền, bằng chứng và kết quả các bước trước |
| `agent_execution.py` | `agents/agent.py` | Đánh giá kết quả gọi công cụ, ghi nhận điều đã làm và điều còn thiếu |
| `automation.py` | `agents/runner/automation_graph.py` | Trích xuất fact và câu hỏi chưa được nguồn trả lời; fact chỉ được giữ nếu trích dẫn khớp nguyên văn |

## Requirements và kiểm thử

| Prompt | Nơi gọi | Mục đích |
| --- | --- | --- |
| `testing_contract.py` | `testing.py` | Hợp đồng chung về ngôn ngữ, ranh giới bằng chứng, đầu ra và hành vi an toàn |
| `testing.py` | `services/ai_automation.py` | Ghép yêu cầu người dùng, bằng chứng và schema đầu ra thành prompt của capability |
| `requirement_templates.py` | `testing.py` | Quy tắc riêng khi tổng hợp mẫu Requirements từ nhiều nguồn |
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

Sự kiện tài liệu mới đi qua trích xuất fact đã xác minh trước khi workflow Requirements nhận chúng. Planner nhận lại chính các fact có quote thuộc evidence của run, cùng reference của artifact và phiên bản; fact không được xác minh không trở thành căn cứ sinh artifact. Thay đổi nguồn dùng run `CHANGE_SIMULATION` chỉ cho phép công cụ `READ`; nó không ghi Requirement, Test Case, waiver hay quyết định Release.

MCP chỉ là cổng công cụ ngoài theo kết nối dự án, danh sách tool đọc được cấp rõ ràng và quyền đọc của project. Output MCP được kiểm tra an toàn trước khi trở lại agent. Service Veriq tiếp tục sở hữu dữ liệu, quyền, workflow, version và audit nghiệp vụ.

## Ranh giới

- Prompt không cấp quyền. Quyền cuối cùng do service nghiệp vụ và registry công cụ kiểm tra.
- Nội dung tài liệu và kết quả MCP là dữ liệu không tin cậy, không phải chỉ dẫn cho agent.
- Không lưu prompt nghiệp vụ trong JSON hay tệp policy tổng hợp.
- Khi sửa prompt, cập nhật đúng module sở hữu và chạy kiểm tra đầu ra của capability tương ứng.
