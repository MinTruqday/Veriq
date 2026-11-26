# Baseline nghiệp vụ Veriq

**Trạng thái:** Đã ghi nhận baseline source; chưa kiểm thử runtime và chưa kết luận audit toàn hệ thống hoàn tất.

## Mốc source

| Thuộc tính | Giá trị |
|---|---|
| Nhánh | `main` |
| HEAD tại lúc ghi nhận | `09a8e5385` |
| Working tree | Có thay đổi đã tồn tại trước lượt audit: `docs/kien-truc/PHAN_TICH_SAN_PHAM_VERIQ.md`; thư mục `docs/ui-ux-redesign/` chứa prompt và kế hoạch đã lưu. Không sửa hay hoàn tác các thay đổi này. |
| Runtime | Lúc kiểm tra, `docker compose ps` báo các service trong compose đang `running`, healthcheck hiển thị `healthy`. Chỉ xác nhận sức khỏe container; chưa đăng nhập, gọi luồng nghiệp vụ hay ghi dữ liệu. |

## Bản đồ route và trang dự án đã thấy trong source

Đây là route/component map tĩnh, không khẳng định các route đều đang được người dùng sử dụng hoặc có quyền truy cập.

| Nhóm | Route hoặc trang/component | Bằng chứng |
|---|---|---|
| Danh sách dự án | `/du-an` | `frontend/app/(main)/du-an/page.jsx` |
| Không gian dự án | `/du-an/[projectId]/[[...section]]` | `frontend/app/(main)/du-an/[projectId]/[[...section]]/page.jsx` |
| Dashboard | `DashboardPage` | `frontend/features/testing/pages/workspace/DashboardPage.jsx` |
| Yêu cầu | `RequirementsPage` | `frontend/features/testing/pages/workspace/RequirementsPage.jsx` |
| Phân tích/điều kiện kiểm thử | `TestAnalysisPage` | `frontend/features/testing/pages/workspace/TestAnalysisPage.jsx` |
| Thiết kế kiểm thử/ca/bộ kiểm thử | `TestDesignPage` | `frontend/features/testing/pages/workspace/TestDesignPage.jsx` |
| Kế hoạch và thực thi | `ExecutionPage` | `frontend/features/testing/pages/workspace/ExecutionPage.jsx` |
| Chu kỳ kiểm thử | `TestPeriodsPage` | `frontend/features/testing/pages/workspace/TestPeriodsPage.jsx` |
| Lỗi | `DefectsPage` | `frontend/features/testing/pages/workspace/DefectsPage.jsx` |
| Báo cáo | `ReportsPage` | `frontend/features/testing/pages/workspace/ReportsPage.jsx` |
| Tài liệu đọc | `DocumentReaderPage` | `frontend/features/testing/pages/workspace/DocumentReaderPage.jsx` |
| Phát hành/bản dựng | `ReleasesPage` | `frontend/features/testing/pages/workspace/ReleasesPage.jsx` |
| Tri thức | `KnowledgePage` | `frontend/features/testing/pages/workspace/KnowledgePage.jsx` |
| Rà soát AI | `ReviewQueuePage` | `frontend/features/testing/pages/workspace/ReviewQueuePage.jsx` |
| Cài đặt dự án | `SettingsPage` | `frontend/features/testing/pages/workspace/SettingsPage.jsx` |

`ProjectWorkspacePage.jsx` ánh xạ slug sang các trang trên, kiểm tra một số capability và chuyển các slug legacy về route hiện tại. Cần so sánh tiếp với navigation, API và tài liệu khóa luận để xác định route nào là luồng chính, route nào chỉ tương thích ngược.

## Phạm vi đã đọc

- V3: khung kiểm toán chiều sâu, độ bao phủ và deliverable. Ví dụ field trong V3 chỉ minh họa phương pháp.
- UI master prompt: lưu nguyên văn tại `docs/ui-ux-redesign/MASTER_PROMPT.md`; hash khớp tệp prompt người dùng gửi.
- V3: lưu nguyên văn tại `docs/ui-ux-redesign/VERIQ_BUSINESS_REDESIGN_MASTER_PROMPT_V3.md`; hash khớp tệp người dùng gửi.
- Source sơ bộ: `ProjectWorkspacePage`, `TestPlanEditor`, hợp đồng tạo kế hoạch và service Test Plan.
- Ghi chú cũ `docs/kien-truc/PHAN_TICH_SAN_PHAM_VERIQ.md` chưa được reconcile với V3.
- Tạo `00_SOURCE_MANIFEST.csv` từ 750 file tracked: 706 file code (`.py`, `.js`, `.jsx`, `.mjs`), 44 file tài liệu/cấu hình/tài sản. Quét cú pháp/name index trên toàn bộ 706 file code; về đọc logic, 33 file xem một phần, 12 file đọc hết và 661 file chưa đọc. Manifest ghi binary asset không có line count.
- Tạo index cấu trúc: 670 khai báo route Python trong `01_API_ROUTE_INVENTORY.csv`, 2,201 field Pydantic trong `02_SCHEMA_FIELD_INVENTORY.csv`, 78 tên collection Mongo và 190 chuỗi permission trong `03_CROSSCUTTING_INDEX.csv`. Đây là chỉ mục để tìm đường đọc, không phải inventory nghiệp vụ hoàn chỉnh.

## Giới hạn của baseline

- Chưa xác minh đăng nhập, tài khoản/role thực tế hoặc dữ liệu local.
- Chưa chụp baseline giao diện theo các kích thước màn hình.
- Chưa lần hết endpoint, background worker, notification, export/import, report consumer và migration.
- Chưa đọc toàn bộ 706 file code; đây là công việc của Giai đoạn 1 và được theo dõi trong manifest. Việc có tên file hoặc thống kê AST không được tính là đã đọc nội dung.
- Chưa chạy bộ kiểm thử. Vì vậy các mục trên không được ghi là PASS.

## Tiếp theo

Mở rộng task map và AS-IS flow trên toàn hệ thống. Đối chiếu mỗi trang với client/API, quyền, service, persistence, worker và report; mở rộng inventory theo chức năng, field, hành động, trạng thái và dependency. Không lấy riêng `PLAN.owner_id` làm lát audit ưu tiên.
