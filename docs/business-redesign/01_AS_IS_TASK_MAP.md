# Bản đồ AS-IS: khu vực, tác vụ và điểm nối

**Trạng thái:** Kiểm kê chiều rộng đang thực hiện. Đây là bản đồ điều hướng source và tác vụ ứng viên, chưa phải TO-BE hay kết luận lỗi.

## Cách đọc

- `Quan sát source`: điều đã thấy trực tiếp trong route, navigation hoặc component.
- `Tác vụ người dùng`: mục tiêu suy ra từ tên/chức năng; cần xác minh bằng service/API và hành vi runtime.
- `Chưa xác minh`: không được coi là yêu cầu sản phẩm hoặc bug trước khi lần đủ đường đi dữ liệu.
- Các màn hình/chức năng không có trong menu vẫn phải được kiểm toán nếu có route/API, kể cả API nội bộ, job, export, import hoặc AI.

## Bản đồ khu vực người dùng

| Khu vực hiện có | Tác vụ người dùng cần hoàn thành | Quan sát source | Điểm nối cần kiểm toán | Trạng thái |
|---|---|---|---|---|
| Dự án | Tìm/chọn dự án để làm việc; hiểu quyền và thành viên của dự án | Route `/du-an`; backend testing có nhóm projects/access/collaboration/attachments | danh sách dự án → membership → project permissions → project settings → archive/invitation | Chưa lần hết API, trạng thái dự án và quyền |
| Tổng quan | Nắm tiến độ và nơi cần xử lý tiếp | Dashboard là trang mặc định; có `DashboardPage` | report/analytics → nguồn đếm → filter theo dự án, thời gian, trạng thái và quyền | Chưa kiểm tra metric với truy vấn nguồn |
| Yêu cầu | Ghi/sửa yêu cầu, quản lý phiên bản/tiêu chí, xem liên kết và tài liệu nguồn | `RequirementsPage` có danh sách, lọc, phân trang, lịch sử/phiên bản, import tài liệu, trùng lặp, trace và impact panel | Requirement ↔ source document ↔ version ↔ AC/BR ↔ review ↔ test condition/case ↔ change analysis | Chưa lần hết API, lifecycle, AI và quy tắc version |
| Phân tích kiểm thử | Chuyển yêu cầu/tiêu chí thành nội dung phân tích hỗ trợ thiết kế test | Có trang `TestAnalysisPage`, slug riêng và điều kiện permission | requirement/version → test condition/scenario → case; xác minh chức năng có trùng bước/field nơi khác không | Chưa xác định dữ liệu chuẩn và mức cần thiết |
| Thiết kế kiểm thử | Tạo, sửa, rà soát và quản lý test case; tìm kiếm theo trạng thái/ưu tiên/bộ | `TestDesignPage` nạp requirement, test condition, scenario, data set, draft, suite, case, member và AI runs; menu hiện “Ca kiểm thử” | requirement/version/AC → condition/scenario → case version/draft → suite → approval → run | Chưa lập field/action/transition inventory |
| Kế hoạch kiểm thử | Xác định phạm vi, mục tiêu, điều kiện và nguồn lực cho hoạt động test | Test Plan nằm trong `ExecutionPage` với `workspaceView=test-plans`; editor riêng; có lọc chu kỳ, trạng thái, người phụ trách | requirement versions → test plan snapshot/readiness/review → suite/case scope → period → run → report | Chưa xác minh field trùng lặp, quy tắc duyệt và nguồn schedule |
| Chu kỳ kiểm thử | Gom kế hoạch theo đợt công việc; đóng chu kỳ và chuyển ca chưa hoàn tất | Trang riêng `TestPeriodsPage`; có kế hoạch thuộc chu kỳ, summary, chọn ca chuyển tiếp và lý do bắt buộc | period ↔ plan ↔ case version ↔ run result ↔ carry-over sang period kế tiếp | Chưa xác minh ý nghĩa nghiệp vụ, metric và truy vết carry-over đầu-cuối |
| Thực thi kiểm thử | Tạo lần chạy, thực thi case, lưu kết quả, ghi lỗi và chạy lại | `ExecutionPage` xử lý plan/run, môi trường, release/build, suite, case, requirement, run, result, defect và progress | plan/suite/case versions → run context → result/step result/evidence → defect → retest → latest result/report | Chưa đối chiếu semantics của status, retry, scope và số liệu |
| Lỗi | Theo dõi lỗi, mức độ, người sửa và trạng thái xử lý | Có `DefectsPage`; API thực thi có route CRUD/transition/duplicate/export lỗi | failed result ↔ defect ↔ assignee/severity/status ↔ fix ↔ retest ↔ closure | Chưa lần toàn bộ permission và vòng đời |
| Báo cáo | Xem tiến độ/hoàn tất và xuất thông tin phục vụ quyết định | `ReportsPage` render `SimpleTestReports`; báo cáo hiện tại tự làm mới mỗi 30 giây, có thao tác lưu snapshot; API có preview/create/list/export PDF/DOCX | result/defect/requirement coverage → metric → snapshot/report → export and permission | `AUD-005`; mẫu số pass rate khác Plan progress và Analytics (`AUD-011`) |
| Tài liệu dự án và tri thức | Lưu/đọc tài liệu dự án, tìm tài liệu tham chiếu | Có `DocumentReaderPage`, `KnowledgePage`; backend content/cloud/AI tách service | file storage → document/version/access → indexing/embedding/retrieval → AI summary/source refs → requirement | Chưa xác minh phân quyền, retention, indexing và phân biệt hai kho |
| Cài đặt dự án và nhật ký | Quản lý thành viên/quyền/cấu hình; xem hoạt động được ghi nhận | Source tách `project_owner_user_id` khỏi `project_lead_user_id`; danh sách hiển thị Trưởng dự án, còn policy cấp toàn quyền/self-approve dựa trên Chủ dự án hoặc system admin | membership/role/capability → owner/lead/responsibility → policy enforcement → review/sign-off → audit/event | Mâu thuẫn với quyết định nghiệp vụ session; theo dõi ở `AUD-010`, chưa sửa khi chưa rà hết dependency |
| Quản lý tài khoản | Tạo/cập nhật/disable/xóa tài khoản; quản lý quyền nền tảng | Navigation hiển thị ngoài không gian dự án cho admin; authentication service có platform và platform controls | platform admin → account state/session → project membership/role → permission cache | Chưa xác minh thao tác thực tế và tác động khi tài khoản bị khóa/xóa |
| Xác thực và tài khoản cá nhân | Đăng nhập, khôi phục, cập nhật thông tin và bảo vệ phiên | Có app routes và service authentication riêng | session/token → account verification → password reset → access revocation | Chưa kiểm tra security flow hoặc thời hạn phiên |
| AI | Tóm tắt tài liệu và hỗ trợ xử lý phiên bản/thay đổi theo phạm vi đã yêu cầu | Backend AI service có inference, AI runs, ingestion/indexing/retrieval/embedding/queue recovery; code cần phân loại capability được giữ/loại | project authorization → AI capability → input/provenance → run/queue → structured result → review/apply → revision state | Chưa xác định API nào thuộc tính năng sản phẩm đang dùng; không kết luận chỉ từ tên thư mục |
| Tích hợp và tự động hóa | Nhập artifact, JUnit, chạy/tích hợp API hoặc script khi dự án dùng | Backend có API artifacts, automation scripts, JUnit import; frontend TestDesign có panel liên quan | external artifact → validation/import → run/result → duplicate/idempotency → report | Chưa xác minh có thuộc phạm vi người dùng hiện tại hay là capability thử nghiệm |

## Các bất nhất cấu trúc đã quan sát

Đây là điểm cần nối theo luồng trước khi quyết định sửa:

1. `routes.js` khai báo 22 slug. Navigation chỉ đưa một tập con vào menu. `ProjectWorkspacePage` chuyển một số slug cũ (`giam-sat-kiem-thu`, `truy-vet`, `thay-doi`, `bo-kiem-thu`, `du-lieu-kiem-thu`, `tu-dong-hoa`) sang trang khác.
2. Test Plan, Test Run và một phần thực thi được ánh xạ vào `ExecutionPage` theo `workspaceView`; trang này chứa nhiều tác vụ và dữ liệu khác nhau. Cần đánh giá khả năng tìm thấy và phân biệt tác vụ bằng journey, không thể kết luận từ việc dùng chung component.
3. Chu kỳ có trang/route riêng, nhưng trang kế hoạch cũng lọc theo `test_period_id`; tạo chu kỳ trên trang hiện dùng tên là dữ liệu chính, còn ngày bắt đầu/kết thúc chưa xuất hiện trong luồng tạo đã đọc. Cần xác minh đầy đủ model, API, dữ liệu cũ và nhu cầu trước khi giữ/bỏ metadata.
4. Tiến độ Plan chọn Result theo thời gian Result (`completed_at`/`updated_at`/`created_at`), còn summary Chu kỳ ưu tiên thời gian tạo Run rồi mới đến thời gian Result. Cùng một ca có thể có trạng thái mới nhất khác nhau khi kết quả cũ được cập nhật sau Run mới. Đã ghi `AUD-009`; chưa xác nhận ảnh hưởng runtime hoặc chốt cách hiểu đúng.
5. Navigation gom “Tài liệu dự án”, “Tài liệu tham chiếu” và “Cài đặt dự án” cùng nhóm “Tài liệu”, dù mục tiêu và quyền khác nhau. Đây là bất nhất phân loại cần đối chiếu prompt UI và người dùng.
6. `testCaseSubsectionItems(..., includeLegacy=true)` còn mô tả Bộ kiểm thử, Mẫu, Nhập/Xuất; route legacy của Bộ kiểm thử chuyển về trang ca. Cần xác minh chức năng còn hiện qua nơi khác/API trước khi coi là dead code.

## Quan hệ liên module quan sát được

```text
Tài khoản/xác thực
  └── thành viên + role + permission của dự án
       ├── Requirement ↔ tài liệu nguồn ↔ phiên bản ↔ AC/BR
       │    └── phân tích/điều kiện ↔ kịch bản ↔ Test Case/version
       ├── Test Suite ───────────────────────┐
       └── Test Plan ↔ Chu kỳ ───────────────┤
                                              v
                    Release/Build/Environment → Test Run
                                              └── Result/step/evidence
                                                   └── Defect → fix/retest
       Result + scope + defect ────────────────→ Dashboard/Report/Export
       Document/version ─→ AI indexing/retrieval/summary/impact → review/apply
```

Sơ đồ chỉ biểu diễn các liên kết candidate thấy từ tên source, props và luồng đọc một phần. Mỗi mũi tên còn cần xác minh bằng API, contract, service, repository và persistence; không được dùng như ERD đã chốt.

## Câu hỏi kiểm toán toàn hệ thống

- Tác vụ nào là mục tiêu chính cho nhóm khóa luận; tác vụ nào là capability phụ hoặc nội bộ?
- Người dùng có thể bắt đầu công việc từ Requirement, Test Case, Test Plan hoặc Test Run mà không bị khóa vào một chuỗi tuyến tính không?
- Khi một module chưa có dữ liệu, luồng kế tiếp có cách bắt đầu hợp lệ không? Điều kiện chặn nằm ở đâu và có đúng thời điểm không?
- Trường nào là dữ liệu gốc; trường nào chỉ là snapshot, cấu hình, mặc định hoặc giá trị tính toán?
- “Chu kỳ”, “bộ kiểm thử”, “kịch bản”, “phân tích kiểm thử” có owner, mục đích và quan hệ riêng đủ rõ để người dùng hiểu không?
- Role nền tảng, role dự án và permission cụ thể có cùng ý nghĩa ở navigation và backend không?
- `project_owner_user_id`, `project_lead_user_id`, `SYSTEM_ADMIN` project role và `ADMIN` system role khác nhau thế nào; đâu là người có quyền cao nhất và ai tự chốt nội dung của mình?
- Dashboard/report dùng cùng định nghĩa tiến độ/Pass/Fail/coverage với execution không?
- Tỷ lệ đạt trả lời câu hỏi nào: tỷ lệ trong số ca có kết luận, trong số ca đã thực thi, hay trong toàn bộ scope? Có cần metric theo từng câu hỏi thay vì cùng tên `pass_rate` không?
- AI chỉ giữ capability đã xác nhận ra sao; nguồn input, provenance, revision và thao tác apply được kiểm soát thế nào?

## Việc cần hoàn tất trước khi gọi đây là AS-IS đầy đủ

1. Đọc và đánh dấu từng source file theo manifest; ưu tiên nối các luồng liên module, không đánh dấu file chỉ vì đã thấy tên.
2. Tạo route/action inventory thực có đầy đủ prefix, method, request/response, permission, side effect và consumer.
3. Tạo entity/field inventory gồm Mongo collections, Pydantic, React forms, defaults, validation, create/edit/read/report/import/export mapping.
4. Lập status transition và decision matrix từ backend; đối chiếu với nhãn/nút frontend.
5. Xác minh toàn bộ producers/consumers gồm queue, notification, AI, audit, search/vector index, export, report, migration và dữ liệu cũ.
6. Chạy journey an toàn trên Docker khi cần kiểm chứng hành vi; chỉ ghi kết quả quan sát được và không dùng số liệu giả.
7. Sau đó mới chốt issue register, root cause, TO-BE và wireframe.
