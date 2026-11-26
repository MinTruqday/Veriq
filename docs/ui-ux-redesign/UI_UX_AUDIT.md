# UI/UX Audit Veriq

**Trạng thái:** Đang kiểm tra theo Phase 0. Đây là kiểm kê route và thành phần nguồn; một trang chỉ được nghiệm thu sau khi rà chức năng, quyền, trạng thái và thao tác thực tế.

## Phạm vi đang chạy

Frontend hiện có các route nghiệp vụ ở `frontend/app`, page trong `frontend/features`, navigation ở `frontend/shared/components/layout/navigation.js`, và API client trong `frontend/features/testing/services`. Những hành động có sẵn phải được giữ đúng quyền và API; audit không tự suy ra business từ tên component.

| Khu vực | Trang/route đang dùng | Thành phần nguồn cần bảo toàn | Kiểu trải nghiệm mục tiêu |
|---|---|---|---|
| Không gian làm việc | `/du-an` | Dự án, tìm/lọc, phân trang, lời mời, tạo dự án, lưu trữ/khôi phục | Lưới dự án và chế độ danh sách |
| Tổng quan | `/du-an/{id}` | Dashboard, tiến trình, số liệu, coverage, việc cần xử lý, lần chạy mới, lỗi, AI, hoạt động, thay đổi | Dashboard số liệu và hành động |
| Yêu cầu | `/du-an/{id}/yeu-cau` | Tìm/lọc, chọn nhiều, gắn nhãn, kiểm tra trùng, gộp/lưu trữ, tạo/sửa/version, review, AI, tài liệu nguồn, trace | Split view và không gian tài liệu |
| Kế hoạch | `/du-an/{id}/ke-hoach-kiem-thu` | Danh sách, tìm/lọc, chu kỳ, tạo/sửa, phạm vi, tiêu chí, review/duyệt, liên kết case | Danh sách kế hoạch và workspace tài liệu |
| Thiết kế | `/du-an/{id}/ca-kiem-thu`, `phan-tich-kiem-thu`, `du-lieu-kiem-thu`, `bo-kiem-thu` | Kho case, phân tích/điều kiện, dữ liệu, suite nếu route còn hoạt động, version, liên kết, AI/import/export | Repository/split view và step blocks |
| Thực thi | `/du-an/{id}/lan-chay-kiem-thu`, `thuc-thi`, `ban-phat-hanh`, `chu-ky-kiem-thu` | Danh sách run, execution/results, evidence, defect, retest, release/build/environment/period | Danh sách đợt chạy và execution workspace |
| Lỗi | `/du-an/{id}/loi` | Tìm/lọc, list/kanban, detail, severity, trạng thái, trace, retest | Kanban hoặc danh sách theo tác vụ |
| Báo cáo | `/du-an/{id}/bao-cao` | Báo cáo tiến độ/hoàn tất, bộ lọc, xem trước, export, trạng thái tạo | Analytics dashboard và report preview |
| Tài liệu | `/du-an/{id}/tai-lieu`, `/tri-thuc`, `/tim-kiem` | Kho file, reader, nguồn, tìm kiếm và trích dẫn | File explorer, reader, knowledge search |
| Theo dõi/AI | `thay-doi`, `truy-vet`, `ra-soat-ai`, `nhat-ky-kiem-toan`, `giam-sat-kiem-thu` | Impact/version, trace, AI jobs, audit, metrics theo route và permission | Workspace theo loại tác vụ; không gom các bảng chung |
| Cài đặt | `/du-an/{id}/cai-dat` | Thông tin dự án, thành viên/quyền, môi trường, nhật ký, hành động nguy hiểm | Settings navigation và section form |
| Quản trị | `/van-hanh` | Tài khoản, role, trạng thái, xem/cập nhật/vô hiệu hóa/xóa theo quyền | Bảng tài khoản và trang/khung chi tiết theo khả năng hiện có |
| Cá nhân/xác thực | route account/auth trong `frontend/app` | Hồ sơ, bảo mật, phiên, đăng nhập, xác minh, khôi phục mật khẩu | Auth layout và profile settings |

## Phát hiện đã xác minh khi xem source/runtime

- Requirement hiện gộp nội dung, ảnh hưởng, lịch sử và tài liệu nguồn trong cùng tab; tab lịch sử lại lặp bảng lịch sử. Danh sách biến mất khi mở một yêu cầu. Bản split view đang được triển khai để sửa bố cục này.
- Dashboard có số liệu thật và tiến trình, nhưng lặp số yêu cầu chuẩn/ca hoạt động ở hai vùng. Danh sách thay đổi gần đây đang là bảng. API có `latest_run.result_counts`, vì vậy có thể trình bày phân bố kết quả của lần chạy gần nhất mà không tạo dữ liệu giả.
- Trang dự án hiện dùng một danh sách dạng hàng ở mọi cỡ màn hình; chưa có lựa chọn Grid/List như prompt.
- Route và quyền cần tiếp tục đối chiếu từng trang. Các route phụ không hiện trên sidebar không được tự động coi là legacy hoặc xóa.

## Còn phải kiểm tra trong Phase 0/9

- Đọc sâu từng page/form/component/API client và lập danh sách hành động, field, quyền, loading/empty/error trước khi refactor trang đó.
- Xác minh route legacy, route chỉ mở từ màn hình cha, và các chức năng ẩn theo quyền.
- Kiểm tra keyboard/accessibility, responsive, lỗi API, thao tác destructive/review/approval và giữ nguyên state khi điều hướng.
- Chụp và so sánh UI trước/sau ở 1280×720, 1440×900 và 1920×1080. Build hiện tại chạy bằng Docker; trạng thái container cần kiểm tra sau từng phase.
