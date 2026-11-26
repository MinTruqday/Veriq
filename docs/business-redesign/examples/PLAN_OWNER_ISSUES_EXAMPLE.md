# Vấn đề và quyết định nghiệp vụ

**Trạng thái:** Nhật ký đang mở. Chỉ ghi kết luận sau khi có rule mục tiêu và bằng chứng vi phạm; câu hỏi chưa rõ không được ghi thành bug.

| ID | Phân loại | Mức | Quan sát / câu hỏi | Bằng chứng hiện tại | Trạng thái |
|---|---|---|---|---|---|
| BR-PLAN-OWNER-001 | `MISSING_DEFINITION` | Chưa xếp | Chưa có định nghĩa được xác minh về trách nhiệm nghiệp vụ của `TestPlan.owner_id`; source chỉ chứng minh có trường tùy chọn, kiểm tra thành viên ACTIVE và lọc/hiển thị danh sách. | `01_AS_IS_BUSINESS.md`, PLAN.owner_id-01–07 | `INVESTIGATING`, không phải bug |
| BR-PLAN-OWNER-002 | `UNVERIFIED_DEPENDENCY` | Chưa xếp | Chưa kiểm kê hết consumer ngoài form, service và danh sách kế hoạch. Chưa đề xuất bỏ/đổi trường trước khi rà dependency. | Chưa đủ bằng chứng | `OPEN` |
| BR-PLAN-OWNER-003 | `MISSING_DEFINITION` | Chưa xếp | Owner tham gia snapshot/hash của kế hoạch đã duyệt nhưng bị loại khỏi content authorship tracking; chưa có rule xác nhận liệu owner assignment có ảnh hưởng tới quyền tự duyệt hay không. | `01_AS_IS_BUSINESS.md`, PLAN.owner_id-08–11 | `INVESTIGATING`, chưa chứng minh mâu thuẫn |
| BR-PLAN-OWNER-004 | `UNVERIFIED_DEPENDENCY` | Chưa xếp | Lọc owner đang chạy client-side trên danh sách tối đa 500 kế hoạch; chưa biết giới hạn này có làm sai tác vụ khi dự án vượt ngưỡng không. | `backend/testing/src/modules/execution/services/test_plan.py:457-487`; `frontend/features/testing/pages/workspace/ExecutionPage.jsx:911-913` | `OPEN`, chưa chứng minh bug |

## Quy tắc phân loại

- `BUG`: chỉ khi có quy tắc mục tiêu có căn cứ và evidence chứng minh implementation vi phạm.
- `BUSINESS_CONFLICT`: hai quy tắc hoặc luồng đã xác nhận mâu thuẫn.
- `MISSING_DEFINITION`: chưa có quy tắc đủ rõ để quyết định đúng/sai.
- `MISSING_CAPABILITY`: tác vụ cần thiết đã được xác nhận nhưng hệ thống chưa hỗ trợ.
- `FRICTION_OR_REDUNDANCY`: thao tác/trường gây ma sát hoặc trùng lặp, cần đo tác vụ và nguồn dữ liệu.
- `DATA_MODEL_ISSUE`: định danh, cardinality, ownership, snapshot hoặc lifecycle không đáp ứng quy tắc đã chốt.
- `RISK_HYPOTHESIS`: khả năng có tác động nhưng chưa tái hiện.

Mỗi quyết định cuối cần liên kết tới source, task người dùng, tác động, phương án được chọn, migration/rollback nếu có và acceptance test.
