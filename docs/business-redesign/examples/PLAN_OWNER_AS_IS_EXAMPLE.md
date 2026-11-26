# AS-IS nghiệp vụ — lát dọc Test Plan owner

**Trạng thái:** Đang kiểm tra source tĩnh. Các mục chưa có bằng chứng được ghi `UNVERIFIED`; chưa phải kết luận nghiệp vụ cuối.

## Tác vụ cần hiểu

Người dùng tạo hoặc sửa Test Plan; có thể gán một người phụ trách; lưu nháp hoặc gửi kế hoạch rà soát; người có quyền rà soát có thể duyệt. Audit cần xác định người phụ trách dùng cho trách nhiệm nào, đủ điều kiện nào, và có ảnh hưởng gì tới duyệt, thực thi, quyền và báo cáo.

## Bằng chứng AS-IS

| ID | Quan sát trong source | Bằng chứng | Mức bằng chứng |
|---|---|---|---|
| PLAN.owner_id-01 | `owner_id` là chuỗi tùy chọn trong schema tạo Test Plan; mặc định `None`. | `backend/testing/src/schemas/contracts/planning.py:121-127` | `VERIFIED_CODE` |
| PLAN.owner_id-02 | Form hiển thị trường “Người phụ trách” trong nhóm “Nhân sự và thời gian (tùy chọn)”; có lựa chọn rỗng `-`; danh sách gồm thành viên ACTIVE và giữ người đang được chọn. | `frontend/features/testing/components/TestPlanEditor.jsx:546-567` | `VERIFIED_CODE` |
| PLAN.owner_id-03 | Service kiểm tra khi owner có giá trị thì người đó phải là thành viên ACTIVE của cùng dự án. | `backend/testing/src/modules/execution/services/test_plan.py:250-257`; gọi lúc tạo tại `:348`, khi cập nhật owner/scenario tại `:570-575` | `VERIFIED_CODE` |
| PLAN.owner_id-04 | Tạo Test Plan yêu cầu capability `testplan.create`; owner không được tự động gán thành creator trong đoạn tạo record đã đọc. | `backend/testing/src/modules/execution/services/test_plan.py:313-318, 368-382` | `VERIFIED_CODE` |
| PLAN.owner_id-05 | Cập nhật kế hoạch giới hạn trạng thái ở `DRAFT` hoặc `READY`, yêu cầu `testplan.update`, và dùng optimistic patch theo revision. | `backend/testing/src/modules/execution/services/test_plan.py:496-510, 578-611` | `VERIFIED_CODE` |
| PLAN.owner_id-06 | Gửi rà soát từ `DRAFT`/`READY` chuyển sang `IN_REVIEW`; sau đó có thể tự duyệt nếu `can_auto_approve_project_content` trả true. Duyệt gọi `require_independent_review`. | `backend/testing/src/modules/execution/services/test_plan.py:619-665` | `VERIFIED_CODE` |
| PLAN.owner_id-07 | Danh sách thực thi có bộ lọc theo `owner_id` và cột “Người phụ trách”, fallback “Chưa phân công”. | `frontend/features/testing/pages/workspace/ExecutionPage.jsx:911-913,1691-1697` | `VERIFIED_CODE` |
| PLAN.owner_id-08 | `owner_id` nằm trong `PLAN_SNAPSHOT_FIELDS` và được đưa vào snapshot/hàm băm của Test Plan đã duyệt. | `backend/testing/src/modules/execution/services/test_plan.py:49-72,130-134` | `VERIFIED_CODE` |
| PLAN.owner_id-09 | Tạo Test Run liên kết tới kế hoạch đã duyệt; xác minh snapshot hash trước khi lưu và bắt đầu Run. Do owner nằm trong hash, owner là một phần của integrity check bản kế hoạch, dù `_pin_run_to_plan` không sao chép owner thành trường riêng của Run. | `backend/testing/src/modules/execution/services/test_run.py:114-122,185-200,264-289`; `backend/testing/src/modules/execution/services/test_run_execution.py:127-149` | `VERIFIED_CODE` |
| PLAN.owner_id-10 | `created_by` và `content_author_ids` được lưu riêng khi tạo. Thay đổi `owner_id` bị loại khỏi phần tính thay đổi tác giả nội dung. | `backend/testing/src/modules/execution/services/test_plan.py:368-385`; `backend/testing/src/core/human_decisions.py:27-49` | `VERIFIED_CODE` |
| PLAN.owner_id-11 | Duyệt dùng quyền `testplan.approve`; người tạo/sửa nội dung bị chặn tự duyệt, trừ người dùng là system admin hoặc project owner theo policy hiện có. Chỉ gán làm owner không tự cấp quyền duyệt và không tự thêm người đó vào danh sách tác giả. | `backend/testing/src/modules/execution/services/test_plan.py:657-665`; `backend/testing/src/core/human_decisions.py:5-13,52-70` | `VERIFIED_CODE` |
| PLAN.owner_id-12 | API danh sách không có tham số lọc `owner_id`; nó lọc từ danh sách đã tải ở client. API hỗ trợ query, environment, period, status và sort. | `backend/testing/src/modules/execution/api/execution.py:103-123`; `backend/testing/src/modules/execution/services/test_plan.py:457-487`; UI `ExecutionPage.jsx:911-913` | `VERIFIED_CODE` |

## Chưa được phép kết luận

- Chưa rõ owner là đầu mối chịu trách nhiệm, tác giả, người thực thi hay chỉ nhãn lọc.
- Chưa rõ owner có cần thiết ở mốc duyệt hoặc khi bắt đầu run không.
- Chưa chứng minh rằng owner có hoặc không có quyền duyệt; cần lần hết authorization/policy và kiểm thử API.
- Chưa biết behavior khi owner mất membership, tài khoản bị khóa, hoặc đổi role.
- Chưa rà hết consumer của `owner_id` trong notification, search/index, export/import, report, background jobs, migration và dữ liệu lịch sử.
- Tìm theo tên file migration trong repository chỉ thấy script kiểm tra migration Test Period; chưa tìm thấy migration chuyên biệt cho `TestPlan.owner_id`. Đây chưa phải bằng chứng rằng lịch sử/schema không có migration nào liên quan, và chưa kiểm tra các record đang lưu.
- Chưa kiểm chứng concurrent assignment, stale revision, hay trường hợp UI giữ owner không còn ACTIVE khi sửa trường khác.
- Chưa xác định quan hệ với `created_by`, thành viên kế hoạch, effort allocation, người chạy Test Run, reviewer và project owner.
- Chưa rõ vì sao `owner_id` được xem là một phần của snapshot bất biến, trong khi thay owner bị loại khỏi authorship tracking. Đây là hai hành vi đã thấy, chưa chứng minh là mâu thuẫn.
- Chưa rõ người được gán owner nhưng không sửa nội dung có được phép duyệt nếu họ có `testplan.approve`; logic tự duyệt hiện xét tác giả và quyền project owner/admin, không xét assignment owner.
- Không tìm thấy bộ lọc owner phía backend trong endpoint list đã đọc; UI lọc sau khi nhận danh sách tối đa 500 kế hoạch. Chưa đo tác động thực tế và chưa xác nhận đây là vấn đề cần sửa.

## Câu hỏi quyết định cần trả lời bằng evidence

1. Người dùng cụ thể nào cần owner và họ dùng nó để làm tác vụ nào?
2. Owner chịu trách nhiệm điều phối hay thực hiện kiểm thử? Nó khác `created_by`, reviewer, member và assignee ở điểm nào?
3. Gán owner có được cấp thêm quyền không? Kiểm tra ở cả API lẫn policy.
4. Ở lifecycle nào được đổi owner? Việc đổi có sửa nội dung đã duyệt hay chỉ metadata điều phối?
5. Nếu người đó rời dự án hoặc bị vô hiệu hóa thì dữ liệu lịch sử và kế hoạch đang chạy cần xử lý ra sao?
6. Báo cáo “theo owner” có ý nghĩa quản lý đúng không, hay chỉ phản ánh dữ liệu được nhập?
7. Cần giữ, đổi nghĩa, derive, để trống theo trạng thái, hay bỏ trường? Chỉ chọn sau khi hoàn tất consumer/migration audit.

## Kết luận tạm thời

Hiện đã xác minh thêm: owner tham gia snapshot/hash của bản kế hoạch được duyệt; Run kiểm tra hash đó khi tạo và bắt đầu. Quyền duyệt vẫn đến từ capability, còn tự duyệt dựa trên tác giả nội dung và ngoại lệ system admin/project owner. Owner không tự cấp quyền và không được tính là tác giả nội dung chỉ vì assignment. Các quan hệ này cần rule nghiệp vụ rõ trước khi sửa. **Chưa chạy journey trên UI/API, chưa kiểm tra dữ liệu cũ trong DB hay migration lịch sử, chưa sửa code, schema hay dữ liệu.** Docker service đang healthy nhưng điều đó không thay cho kiểm chứng luồng.
