# Kiểm tra và hoàn thiện giao diện Veriq

Cập nhật lần cuối: 05/11/2026. Danh sách này theo các route và mục điều hướng đang có trong frontend. Chỉ đánh dấu hoàn tất sau khi kiểm tra trang có dữ liệu, quyền phù hợp và thao tác chính; kiểm tra desktop tại 1280, 1440 và 1920 px. Các lượt kiểm tra dùng API giả được ghi rõ, không được hiểu là nghiệm thu API thật.

## Trang đã hoàn tất

| Trang         | Trạng thái | Bằng chứng                                                                                                                                                                                                                                                                                                                                                     |
| ------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Yêu cầu       | ☑         | Smoke trình duyệt với dữ liệu giả ở 1280, 1440 và 1920 px: danh sách, chi tiết, yêu cầu chỉnh sửa, nhập tài liệu và lựa chọn trích xuất BR; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-requirements-{1280,1440,1920}.png`, `/tmp/veriq-requirement-detail-smoke-{1280,1440,1920}.png`, `/tmp/veriq-requirement-import-smoke-{1280,1440,1920}.png`. |
| Hồ sơ đảm bảo | ☑         | Smoke trình duyệt với dữ liệu giả ở 1280, 1440 và 1920 px: trạng thái/nhãn không lộ role, thao tác rà soát hiện đúng theo quyền QA, không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-assurance-1280.png`, `/tmp/veriq-assurance-1440.png`, `/tmp/veriq-assurance-1920.png`.                                                                              |
| Phiếu làm rõ  | ☑         | Smoke trình duyệt với dữ liệu giả ở 1280, 1440 và 1920 px: tạo phiếu, đưa Requirement đang rà soát về bản nháp, trạng thái và nội dung không lộ role, không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-requirement-clarification-1280.png`, `/tmp/veriq-requirement-clarification-1440.png`, `/tmp/veriq-requirement-clarification-1920.png`.            |
| Trang chủ     | ☑         | Nội dung, điều hướng đăng nhập/điều khoản và bố cục kiểm tra ở 1280, 1440, 1920 px; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-home-{1280,1440,1920}.png`.                                                                                                                                                                                                 |
| Đăng nhập     | ☑         | Trên giao diện Docker, đăng nhập tài khoản QA thật thành công và chuyển tới `/du-an`, không lỗi API/JavaScript. Kiểm tra bố cục, nút hiện/ẩn mật khẩu, không có đăng nhập Google và không tràn ngang ở 1280, 1440, 1920 px. Ảnh bố cục: `/tmp/veriq-login-{1280,1440,1920}.png`; ảnh phiên đăng nhập: `/tmp/veriq-login-smoke.png`.                                               |
| Quên mật khẩu | ☑         | Smoke trình duyệt ở 1280, 1440, 1920 px với API giả: gửi đúng email, chuyển sang nhập mã; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-forgot-password-{1280,1440,1920}.png`.                                                                                                                                                                                        |
| Đặt lại mật khẩu | ☑      | Smoke trình duyệt ở 1280, 1440, 1920 px với token/API giả: gửi đúng token và mật khẩu mới, chuyển về đăng nhập; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-reset-password-{1280,1440,1920}.png`.                                                                                                                                                                |
| Nhập mã khôi phục | ☑     | Smoke trình duyệt ở 1280, 1440, 1920 px với API giả: gửi mã, chuyển đúng sang đặt mật khẩu; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-verification-code-{1280,1440,1920}.png`.                                                                                                                                                                                 |
| Xác minh email | ☑        | Smoke trình duyệt ở 1280, 1440, 1920 px với API giả: gửi đúng token, hiện kết quả xác minh và liên kết đăng nhập; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-email-verification-{1280,1440,1920}.png`.                                                                                                                                                       |
| Điều khoản | ☑            | Smoke trình duyệt ở 1280, 1440, 1920 px: điều hướng mục trong trang và đúng neo nội dung; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-terms-{1280,1440,1920}.png`.                                                                                                                                                                                              |
| Tài khoản | ☑             | Smoke trình duyệt với API giả ở 1280, 1440, 1920 px: lưu hồ sơ, lưu tùy chọn thông báo, đóng phiên khác và giữ phiên hiện tại; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-account-{1280,1440,1920}.png`.                                                                                                                                                      |
| Danh sách dự án | ☑          | Smoke trình duyệt với dữ liệu giả tại 1280, 1440 và 1920 px: lọc theo ngày, tìm mã, nhận lời mời, tạo/lọc/khôi phục dự án; xác nhận ngày không hợp lệ chặn lưu, nhãn tạo dự án không lộ BA/QA, không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-projects-{1280,1440,1920}.png`.                                                                            |

## Trang cần rà soát theo thứ tự

### Công khai, xác thực và tài khoản

| Trang                | Route                   | Trạng thái |
| -------------------- | ----------------------- | ---------- |
| Trang chủ            | `/`                     | ☑          |
| Đăng nhập            | `/dang-nhap`            | ☑          |
| Quên mật khẩu        | `/quen-mat-khau`        | ☑          |
| Đặt lại mật khẩu     | `/dat-lai-mat-khau`     | ☑          |
| Xác minh thư điện tử | `/xac-minh-thu-dien-tu` | ☑          |
| Nhập mã khôi phục    | `/xac-thuc`             | ☑          |
| Điều khoản           | `/dieu-khoan`           | ☑          |
| Cài đặt tài khoản    | `/cai-dat`              | ☑          |

Trang chủ có nội dung và liên kết được kiểm tra ở 1280, 1440 và 1920 px; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-home-1280.png`, `/tmp/veriq-home-1440.png`, `/tmp/veriq-home-1920.png`.

### Không gian dự án và lập kế hoạch

| Trang               | Route                                     | Trạng thái |
| ------------------- | ----------------------------------------- | ---------- |
| Danh sách dự án     | `/du-an`                                  | ☑          |
| Tổng quan dự án     | `/du-an/{projectId}`                      | ☐          |
| Danh sách công việc | `/du-an/{projectId}/lap-ke-hoach/list`    | ☐          |
| Danh sách chờ       | `/du-an/{projectId}/lap-ke-hoach/backlog` | ☐          |
| Bảng công việc      | `/du-an/{projectId}/lap-ke-hoach/board`   | ☐          |
| Đợt lặp (Scrum)     | `/du-an/{projectId}/lap-ke-hoach/sprint`  | ☐          |
| Lộ trình            | `/du-an/{projectId}/lap-ke-hoach/roadmap` | ☐          |
| Bản phát hành       | `/du-an/{projectId}/ban-phat-hanh`        | ☐          |

### Bảo đảm yêu cầu

| Trang              | Route                              | Trạng thái |
| ------------------ | ---------------------------------- | ---------- |
| Yêu cầu            | `/du-an/{projectId}/yeu-cau`       | ☑         |
| Hồ sơ đảm bảo      | `/du-an/{projectId}/ho-so-dam-bao` | ☑         |
| Phiếu làm rõ       | `/du-an/{projectId}/phieu-lam-ro`  | ☑         |
| Phân tích thay đổi | `/du-an/{projectId}/thay-doi`      | ☐          |

### Phân tích và thiết kế kiểm thử

| Trang                          | Route                                        | Trạng thái |
| ------------------------------ | -------------------------------------------- | ---------- |
| Chiến lược kiểm thử            | `/du-an/{projectId}/quan-tri-kiem-thu`       | ☐          |
| Phân tích kiểm thử             | `/du-an/{projectId}/phan-tich-kiem-thu`      | ☐          |
| Kho kiểm thử                   | `/du-an/{projectId}/kho-kiem-thu`            | ☐          |
| Ca kiểm thử                    | `/du-an/{projectId}/ca-kiem-thu`             | ☐          |
| Nghĩa vụ kiểm thử              | `/du-an/{projectId}/ca-kiem-thu/do-day-du`   | ☐          |
| Hoạt động AI trong ca kiểm thử | `/du-an/{projectId}/ca-kiem-thu/ai`          | ☐          |
| Kịch bản                       | `/du-an/{projectId}/ca-kiem-thu/kich-ban`    | ☐          |
| Mẫu ca kiểm thử                | `/du-an/{projectId}/ca-kiem-thu/mau`         | ☐          |
| Mã kiểm thử tự động            | `/du-an/{projectId}/ca-kiem-thu/tu-dong-hoa` | ☐          |
| Ca kiểm thử API                | `/du-an/{projectId}/ca-kiem-thu/api`         | ☐          |
| Nhập và xuất ca kiểm thử       | `/du-an/{projectId}/ca-kiem-thu/nhap-xuat`   | ☐          |
| Bước dùng lại                  | `/du-an/{projectId}/buoc-dung-lai`           | ☐          |
| Dữ liệu kiểm thử               | `/du-an/{projectId}/du-lieu-kiem-thu`        | ☐          |
| Bộ kiểm thử                    | `/du-an/{projectId}/bo-kiem-thu`             | ☐          |

### Kế hoạch và thực thi

| Trang             | Route                                  | Trạng thái |
| ----------------- | -------------------------------------- | ---------- |
| Kế hoạch kiểm thử | `/du-an/{projectId}/ke-hoach-kiem-thu` | ☐          |
| Lần chạy kiểm thử | `/du-an/{projectId}/lan-chay-kiem-thu` | ☐          |
| Kết quả thực thi  | `/du-an/{projectId}/thuc-thi`          | ☐          |
| Tự động hóa       | `/du-an/{projectId}/tu-dong-hoa`       | ☐          |
| Lỗi               | `/du-an/{projectId}/loi`               | ☐          |

### Theo dõi, báo cáo và nguồn tài liệu

| Trang                           | Route                                      | Trạng thái |
| ------------------------------- | ------------------------------------------ | ---------- |
| Giám sát kiểm thử               | `/du-an/{projectId}/giam-sat-kiem-thu`     | ☐          |
| Truy vết                        | `/du-an/{projectId}/truy-vet`              | ☐          |
| Báo cáo                         | `/du-an/{projectId}/bao-cao`               | ☐          |
| Nhật ký kiểm toán               | `/du-an/{projectId}/nhat-ky-kiem-toan`     | ☐          |
| Hoạt động AI                    | `/du-an/{projectId}/ra-soat-ai`            | ☐          |
| Tài liệu tham chiếu và tìm kiếm | `/du-an/{projectId}/tri-thuc`              | ☐          |
| Trình đọc tài liệu              | `/du-an/{projectId}/tai-lieu/{documentId}` | ☐          |
| Cài đặt dự án                   | `/du-an/{projectId}/cai-dat`               | ☐          |

### Khu vực dùng chung và vận hành

| Trang                                | Route                 | Trạng thái |
| ------------------------------------ | --------------------- | ---------- |
| Thông báo                            | `/thong-bao`          | ☐          |
| Vận hành nền tảng: Tổng quan         | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Tài khoản         | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Bảng lương        | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Cấu hình nền tảng | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Đánh giá AI       | `/van-hanh`           | ☐          |
| Vận hành nền tảng                    | `/van-hanh`           | ☐          |
| Trang lỗi và không tìm thấy          | `error` / `not-found` | ☐          |

### Các chế độ xem bên trong trang

| Trang             | Chế độ xem                                                                              | Trạng thái |
| ----------------- | --------------------------------------------------------------------------------------- | ---------- |
| Lần chạy kiểm thử | Lần chạy, sự cố môi trường, kiểm thử phi chức năng (theo quyền)                         | ☐          |
| Tự động hóa       | Kết quả, kịch bản và thiết bị, AI Agent (theo quyền)                                    | ☐          |
| Báo cáo           | Công việc/định kỳ, tổng quan, báo cáo kiểm thử, chất lượng/cải tiến                     | ☐          |
| Cài đặt dự án     | Quyền của tôi, dự án, thành viên, năng lực, thông báo, tích hợp, phân tích (theo quyền) | ☐          |
| Thông báo         | Tất cả, chưa đọc                                                                        | ☐          |
| Tài khoản         | Hồ sơ, mật khẩu, phiên đăng nhập, tùy chọn thông báo                                    | ☐          |

## Quy tắc đánh dấu

- Hoàn thiện một trang rồi mới chuyển sang trang tiếp theo theo thứ tự trên.
- Một trang chỉ được đánh dấu ☑ khi đã kiểm tra bố cục, dữ liệu mẫu có ý nghĩa, trạng thái tải/rỗng/lỗi, quyền, thao tác chính và không có lỗi JavaScript hoặc tràn ngang tại các kích thước desktop đã nêu.
- Ghi rõ ảnh/bằng chứng, tài khoản/role và API giả hay API thật. Không dùng build thành công để thay cho kiểm tra giao diện.
- Giữ nguyên mọi chức năng và API hiện hữu khi chỉnh giao diện; không tự thêm màu/icon/tagline ngoài hệ thiết kế chung.
