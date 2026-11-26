# Bảo toàn chức năng khi refactor UI

**Quy tắc:** đổi vị trí hoặc cách hiển thị không thay đổi API, schema, quyền, workflow hay dữ liệu. Mỗi hàng cần được kiểm tra lại sau khi làm trang.

| Nhóm | Chức năng phải còn dùng được | Trạng thái kiểm tra |
|---|---|---|
| Dự án | Tìm kiếm, trạng thái, ngày, phân trang, tạo dự án, lời mời nhận/từ chối, khôi phục dự án, điều hướng vào dự án | Grid/List đã có trong source; chưa nghiệm thu thao tác do phiên UI hết hạn |
| Dashboard | Tiến trình, chỉ số quyền hạn, coverage, việc cần xử lý, kết quả lần chạy gần nhất, mức độ lỗi, AI, thay đổi và hoạt động hiện có | Giữ số liệu thật, hàng đợi xử lý, link khu vực độc lập không lặp số, kết quả run, lỗi, AI và thay đổi. Không biểu diễn workflow thành chuỗi bắt buộc. Quyền giữ nguyên; browser authenticated chưa kiểm tra |
| Requirement | Tìm/lọc, chọn nhiều, cập nhật nhãn, phát hiện trùng, gộp/lưu trữ, tạo/sửa/lưu nháp/gửi rà soát/chốt, phiên bản/so sánh, impact/retry, trace, comments, collaboration, tài liệu/AI | Refactor sang split 30/70, compact list, active row và tab Nội dung/Ảnh hưởng/Truy vết/Lịch sử & rà soát; form tạo là document workspace. API/quyền giữ nguyên; bản tinh chỉnh chưa build và browser chưa có session |
| Test Plan / Cycle | Tìm/lọc, nhóm kế hoạch theo chu kỳ hoặc độc lập, phạm vi, tạo/sửa/lưu, review/approval, scope case, cycle summary, close/carry-over | Hai chế độ trong cùng khu vực; nhóm cycle có thể thu gọn; kế hoạch không thuộc chu kỳ nằm riêng; summary dùng status distribution thật. Giữ lựa chọn tạo cycle mới/hiện có/không cycle, validation đóng chu kỳ và chọn carry-over thủ công. Docker build/runtime PASS; authenticated interaction chưa nghiệm thu |
| Test Case | Tìm/lọc/chọn nhiều, CRUD và version, các bước, điều kiện, dữ liệu, liên kết Requirement/AC/BR, review, AI/import/export nếu route dùng | Step Block đã triển khai; danh sách/repository và thao tác chưa nghiệm thu |
| Test Run | Tạo/chạy/tiếp tục/dừng, kết quả, actual result, bằng chứng, fail và defect, retest, phạm vi theo plan/period | Form route riêng hỗ trợ run độc lập hoặc theo plan bằng contract hiện tại; xác minh Docker và thao tác authenticated đang chờ |
| Defect | Lọc/list/kanban, mở chi tiết, liên kết run/case, cập nhật theo quyền, duplicate và retest | Có chế độ danh sách/bảng trạng thái; chưa nghiệm thu thao tác |
| Report | Hai kiểu report hiện có, xem trước, export PDF/Word, trạng thái và quyền | Chưa kiểm tra |
| Tài liệu/tri thức | Upload/parse/AI permission, preview/reader, search, source/evidence và trạng thái lỗi | Chưa kiểm tra |
| Cấu hình/tài khoản | Project settings, thành viên/role, environment, audit; tài khoản, hồ sơ, xác minh, phiên và authentication | Chưa kiểm tra |

Không được đánh dấu “giữ” chỉ vì nút còn trong source. Nghiệm thu cần thao tác UI thật, API hợp lệ, kiểm tra quyền và trạng thái tải/rỗng/lỗi.
