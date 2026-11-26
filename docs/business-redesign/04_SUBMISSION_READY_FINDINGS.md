# Kết quả kiểm toán nghiệp vụ sơ bộ Veriq

**Mục đích:** Bản tóm tắt có thể dùng cho phần phân tích hiện trạng và vấn đề nghiệp vụ trong báo cáo. Đây là kết quả sơ bộ có bằng chứng từ source, không tuyên bố đã kiểm toán hết sản phẩm.

## 1. Phạm vi và cách kiểm tra

Veriq được xem như một sản phẩm gồm các luồng Dự án, Requirement, phân tích/thiết kế kiểm thử, Test Plan, Chu kỳ, Test Run, Result, Defect, Báo cáo, Tài liệu, quyền và AI. Đã quét cấu trúc 706 file code; tạo chỉ mục route, schema field, collection và chuỗi quyền. Đã đọc sâu một số điểm nối giữa quyền dự án, duyệt nội dung, kết quả chạy, chu kỳ và báo cáo.

Các chỉ mục tự động chỉ giúp tìm nơi cần đọc. Chúng không chứng minh nghiệp vụ đúng hoặc sai. Vì thời gian kiểm tra có hạn, các kết luận dưới đây chỉ áp dụng cho những đường code được dẫn rõ; chưa đại diện cho toàn bộ chức năng.

## 2. Phát hiện đã có bằng chứng

### 2.1 Chủ dự án và Trưởng dự án đang là hai định danh khác nhau

Source lưu `project_owner_user_id` và `project_lead_user_id` riêng. Danh sách dự án hiển thị tên Trưởng dự án từ `project_lead_user_id`; trong khi quyền toàn dự án và quyền tự duyệt được quyết định dựa trên system admin hoặc `project_owner_user_id`.

Điều này mâu thuẫn với quy tắc nghiệp vụ đã thống nhất cho Veriq: Admin và người đứng đầu dự án có quyền cao nhất; người này có thể tự chốt nội dung của mình. Nếu Chủ dự án khác Trưởng dự án, người dùng nhìn thấy một người phụ trách nhưng hệ thống có thể trao quyền cao nhất cho người khác.

**Hướng xử lý nghiệp vụ:** xác định một định danh duy nhất cho người đứng đầu dự án, hoặc ghi rõ vai trò của Chủ dự án và Trưởng dự án khác nhau. Sau đó dùng cùng quy tắc đó ở màn hình, quyền hiệu lực, duyệt, chuyển giao và audit. Không nên sửa riêng trường giao diện.

**Bằng chứng:** `backend/testing/src/modules/projects/services/project.py` (quyền hiệu lực và `can_self_approve`: dòng 97–123; tạo dự án: 180–211; nhãn Trưởng dự án: 311–325); `backend/testing/src/core/human_decisions.py` (Admin/Chủ dự án có thể tự chốt: dòng 5–12).

### 2.2 Các màn hình tính trạng thái kiểm thử theo quy tắc khác nhau

Plan progress chọn Result mới nhất theo thời gian hoàn tất/cập nhật/tạo. Summary Chu kỳ ưu tiên thời điểm tạo Test Run trước, rồi mới xét thời điểm cập nhật Result. Vì vậy, nếu một kết quả của Run cũ được sửa sau khi đã có Run mới, hai màn hình có thể chọn hai Result khác nhau cho cùng phiên bản Test Case.

Ngoài ra, ba nơi cùng trả về `pass_rate` nhưng dùng mẫu số khác nhau:

- Plan progress: `PASS / (PASS + FAIL + BLOCKED)`.
- Báo cáo: `PASS / (PASS + FAIL)`.
- Analytics: số PASS chia cho mọi Result kết thúc, gồm PASS, FAIL, BLOCKED, SKIPPED và NOT_APPLICABLE.

**Hướng xử lý nghiệp vụ:** định nghĩa rõ “kết quả mới nhất” và từng metric trước khi dùng chúng ở Dashboard, Chu kỳ, Plan và Báo cáo. Nếu các metric trả lời câu hỏi khác nhau, đặt tên khác nhau và hiển thị mẫu số; không ép mọi nơi dùng chung một con số.

**Bằng chứng:** `backend/testing/src/modules/execution/services/test_plan_progress.py` (dòng 30–59, 73–115); `backend/testing/src/modules/execution/services/test_period.py` (dòng 168–180); `backend/testing/src/modules/execution/api/simple_reports.py` (dòng 127–146, 225); `backend/testing/src/modules/quality/services/analytics.py` (dòng 891–902).

### 2.3 Báo cáo hiện có chế độ live và chế độ lưu snapshot

Trang báo cáo tự lấy báo cáo của Test Plan đã duyệt và làm mới dữ liệu định kỳ. Nút lưu báo cáo tạo một snapshot có hash và khóa idempotency; backend từ chối lưu nếu nguồn đã đổi sau khi xem trước.

Do đó, hệ thống không bắt người dùng tự tính hoặc tự tạo nội dung báo cáo hiện tại. Thao tác lưu nhằm giữ một mốc báo cáo cố định. Đây là phân biệt hợp lý giữa báo cáo live và bản lưu, nhưng giao diện và hướng dẫn cần nói rõ mục đích của nút lưu.

**Bằng chứng:** `frontend/features/testing/components/SimpleTestReports.jsx` (tải báo cáo live và lưu snapshot); `backend/testing/src/modules/execution/api/simple_reports.py` (API live: dòng 229–269; lưu snapshot và kiểm tra nguồn: dòng 317–339).

## 3. Vấn đề cấu trúc cần xem trong thiết kế tổng thể

Các slug route, menu và trang thực tế không trùng hoàn toàn. Một số route legacy chuyển sang trang khác; Test Plan và Test Run cùng được xử lý trong `ExecutionPage`; nhiều capability như truy vết, dữ liệu kiểm thử, bộ kiểm thử và tự động hóa cần được lần tiếp để phân biệt chức năng còn dùng, đã chuyển hay chỉ còn API.

Đây là bằng chứng về chỗ cần kiểm tra tính nhất quán điều hướng và ownership nghiệp vụ, chưa đủ căn cứ để xóa module. Cần quyết định theo tác vụ người dùng và dependency, không dựa riêng vào việc một mục có xuất hiện trong menu.

## 4. Đề xuất thứ tự giải quyết

1. Chốt mô hình quyền của Admin, Trưởng dự án, Chủ dự án và các role BA/Tester; dùng một quy tắc xuyên suốt cho quyền và duyệt.
2. Chốt cách chọn Result mới nhất và định nghĩa metric tiến độ/tỷ lệ đạt; ghi trong từ điển metric.
3. Giữ báo cáo live tự động; chỉ lưu snapshot khi cần lưu mốc phục vụ đối chiếu hoặc nghiệm thu.
4. Lần tiếp dependency của Requirement–Plan–Chu kỳ–Suite–Case–Run–Defect–Report, cùng Tài liệu và AI, trước khi bỏ/gộp chức năng.
5. Sau khi nghiệp vụ và hợp đồng dữ liệu ổn định, mới xem xét UI. Theo yêu cầu hiện tại, chưa triển khai redesign giao diện.

## 5. Giới hạn cần ghi trong báo cáo

Đây là audit sơ bộ từ source code, chưa phải kết quả kiểm thử runtime hoặc khảo sát người dùng. Chưa kiểm tra toàn bộ permission, migration, dữ liệu cũ, API consumer, worker, AI capability và mọi trường frontend. Không dùng các phát hiện này để tuyên bố mọi màn hình/module đều đã được nghiệm thu.
