# Bản đồ module Veriq — khởi tạo từ cấu trúc source

**Trạng thái:** Bản đồ chiều rộng ban đầu. Tên thư mục và số lượng file là bằng chứng cấu trúc, chưa phải mô tả đầy đủ nghiệp vụ. Các trách nhiệm ghi dưới đây cần được xác minh khi đọc source.

## Độ phủ source

- Git có 750 file tracked: 706 file code (`.py`, `.js`, `.jsx`, `.mjs`) và 44 file tài liệu, cấu hình hoặc asset.
- Manifest tại `00_SOURCE_MANIFEST.csv` tách `structure_scan_status` khỏi `review_status`. Đã quét cấu trúc toàn bộ 706 file code tracked, nhưng quét tên/chuỗi không được tính là đọc logic.
- 33 file source đã được xem từng phần, 12 file đã đọc đầy đủ; các file đọc đầy đủ chủ yếu là route registry/aggregator và một số rule hẹp. Đây chưa phải audit module hoàn chỉnh. Không coi việc liệt kê route, tên hàm hoặc thư mục là đã đọc source.
- Số dòng trong manifest là thống kê văn bản, không bao gồm binary.

## Frontend

| Khu vực source | File code | Dòng văn bản | Phạm vi thấy từ cấu trúc |
|---|---:|---:|---|
| `frontend/app` | 17 | 181 | Route/layout Next.js, xác thực, dự án, vận hành, cài đặt |
| `frontend/shared` | 23 | 2,465 | Component, context, lib và service dùng chung |
| `frontend/features/testing` | 104 | 41,305 | Trang dự án, Requirement, Plan, Case, Run, Defect, báo cáo, tài liệu, cài đặt và thành phần liên quan |
| `frontend/features/authentication` | 17 | 1,595 | Đăng nhập, đăng ký, xác thực và khôi phục tài khoản |
| `frontend/features/notification` | 4 | 582 | Thông báo |
| `frontend/features/cloud`, `legal`, `marketing` | 3 | 252 | Tính năng cloud, pháp lý và marketing |
| Cấu hình frontend (`middleware`, Next, Tailwind, PostCSS) | 4 | 164 | Hành vi ứng dụng và build |

### Route không gian dự án thấy trong source

`frontend/features/testing/routes.js` khai báo các slug: `phan-tich-kiem-thu`, `giam-sat-kiem-thu`, `ban-phat-hanh`, `yeu-cau`, `thiet-ke-kiem-thu`, `ca-kiem-thu`, `du-lieu-kiem-thu`, `bo-kiem-thu`, `ke-hoach-kiem-thu`, `chu-ky-kiem-thu`, `lan-chay-kiem-thu`, `tu-dong-hoa`, `truy-vet`, `thay-doi`, `thuc-thi`, `ra-soat-ai`, `loi`, `bao-cao`, `nhat-ky-kiem-toan`, `tri-thuc`, `tai-lieu`, `cai-dat`.

Đây mới là slug catalog. `ProjectWorkspacePage.jsx` có ánh xạ một số slug legacy; cần xác minh từng route với navigation, quyền, API và tác vụ trước khi quyết định module nào hiện/ẩn/gộp/bỏ.

## Backend

| Service / domain | File code | Dòng văn bản | Nhóm thư mục đã thấy |
|---|---:|---:|---|
| AI | 145 | 26,197 | agents, api, clients, core, knowledge, memory, prompts, repositories, runtime, schemas, services, store, tools, utils |
| Authentication | 34 | 4,980 | api, clients, core, repositories, schemas, services, templates |
| Cloud | 52 | 4,333 | api, clients, core, repositories, schemas, services |
| Content | 39 | 4,001 | api, clients, core, repositories, schemas, services |
| Notification | 19 | 772 | api, clients, core, repositories, schemas, services |
| Testing — entrypoint/core/client/schema/repository | 84 | 12,361 | api, clients, core, repositories, schemas, service, package initializer |
| Testing — design | 25 | 7,911 | module `design` |
| Testing — execution | 21 | 6,392 | module `execution` |
| Testing — integrations | 13 | 1,890 | module `integrations` |
| Testing — operations | 16 | 1,586 | module `operations` |
| Testing — projects | 16 | 2,244 | module `projects` |
| Testing — quality | 30 | 7,232 | module `quality` |
| Testing — requirements | 27 | 12,664 | module `requirements` |
| Worker | 12 | 1,529 | core, jobs, repositories, services |
| Shared | 1 | 1 | shared package |

Tên domain nêu trên phản ánh cách source được chia hiện nay; chưa phải TO-BE đã duyệt. Phải rà cả dependency giữa các service và route nội bộ.

## Index cấu trúc API và schema

- `01_API_ROUTE_INVENTORY.csv`: phát hiện 670 khai báo route từ decorator trong Python backend. Đây là số khai báo, chưa khử alias/route trùng và chưa ghép prefix ở entrypoint; chưa ánh xạ quyền hay side effect.
- `02_SCHEMA_FIELD_INVENTORY.csv`: phát hiện 2,201 khai báo field trong lớp Pydantic backend. Đây là chỉ mục cấu trúc, chưa bao gồm tất cả field trong Mongo document hoặc form React; chưa phân loại ý nghĩa, độ bắt buộc hay consumer.
- `03_CROSSCUTTING_INDEX.csv`: quét 706 source code tracked để lập chỉ mục 78 tên collection Mongo và 195 chuỗi literal trông như permission. Danh sách collection là tham chiếu cú pháp, không khẳng định collection canonical; chuỗi permission chưa đối chiếu schema chính sách, tên alias hoặc enforcement.
- AST parser chạy được trên các file Python tracked, không gặp lỗi parse. Parser thành công không đồng nghĩa đã đọc hoặc audit source.

## Hạ tầng runtime

Compose khai báo frontend, backend services, worker, MongoDB, Redis, RabbitMQ, Qdrant, Grafana, Nginx và Traefik. Ở lần ghi nhận gần nhất, `docker compose ps` báo service đang chạy và healthy. Đây chỉ là healthcheck container, không chứng minh nghiệp vụ hoặc tích hợp hoạt động đúng.

## Phần chưa hoàn tất

- Chưa lập danh mục function, endpoint, permission, entity, field, action, transition hay business rule đầy đủ.
- Chưa vẽ dependency graph; hiện mới có danh sách domain/module.
- Chưa xác minh mọi route có UI tương ứng, mọi API có consumer, hoặc các module legacy.
- Chưa đọc source toàn diện, chưa benchmark usability và chưa chạy journey.

Tiếp theo dùng `00_SOURCE_MANIFEST.csv` để đọc theo domain/luồng, đánh dấu trạng thái file sau khi hoàn tất và bổ sung function/API/entity map với evidence.

## Bản đồ tác vụ và các điểm kiểm toán ban đầu

- `01_AS_IS_TASK_MAP.md` ghi các khu vực tác vụ hiện quan sát được, dependency ứng viên và bất nhất cấu trúc cần xác minh.
- `02_AUDIT_LEADS.md` tập hợp các điểm kiểm toán rộng; tất cả hiện là lead, chưa phải kết luận bug.
- `03_CROSSCUTTING_INDEX.csv` chứa tham chiếu collection và permission literal được quét từ source code.
- Độ phủ manifest hiện là 706 file code đã quét cấu trúc; 33 file được xem logic một phần, 12 file đã đọc hết, 661 file code chưa đọc logic. Còn 44 file docs/config/assets cần phân loại theo giá trị kiểm toán. Chưa tuyên bố hoàn tất kiểm toán source.
