# Kế hoạch kiểm toán nghiệp vụ và thiết kế lại Veriq

**Trạng thái:** Đang thực hiện refactor toàn bộ frontend theo các Phase 0–9 trong `MASTER_PROMPT.md`. Chỉ quay lại kiểm toán và sửa business sau khi hoàn tất frontend, kiểm thử Docker và ghi nhận các vấn đề còn mở.

**Thứ tự hiện hành:** Phase 0 Audit UI → Phase 1 Design System/Global Layout → Phase 2 Dự án/Dashboard → Phase 3 Requirement → Phase 4 Test Plan → Phase 5 Test Case → Phase 6 Test Run/Defect → Phase 7 Báo cáo/Tài liệu → Phase 8 Cài đặt/Tài khoản/Xác thực → Phase 9 kiểm thử/nghiệm thu. Không dừng chờ người dùng accept giữa các phase. Sau khi toàn bộ frontend hoàn tất mới quay lại business audit theo 16 nhóm ở `docs/business-redesign/STATUS.md`.

## 1. Tài liệu làm căn cứ

| Tài liệu | Vai trò trong công việc |
|---|---|
| [`VERIQ_BUSINESS_REDESIGN_MASTER_PROMPT_V3.md`](./VERIQ_BUSINESS_REDESIGN_MASTER_PROMPT_V3.md) | Căn cứ cho kiểm toán nghiệp vụ, trường, hành động, quyền, trạng thái, quan hệ, số liệu, migration và bằng chứng. Ví dụ trong tài liệu là câu hỏi cần kiểm tra, không mặc định là bug. |
| [`MASTER_PROMPT.md`](./MASTER_PROMPT.md) | Căn cứ cho global layout, design system, wireframe từng trang, thành phần, tương tác, giai đoạn redesign và nghiệm thu UI. |
| [Link tham khảo UI/UX](https://chatgpt.com/share/6b06fd40-248c-83ec-89cc-41402a836ca0) | Tài liệu tham khảo bổ sung. Dùng để đối chiếu cách trình bày và thao tác, không thay hai prompt và không lấy ví dụ minh họa làm dữ liệu thật. |
| `docs/kien-truc/PHAN_TICH_SAN_PHAM_VERIQ.md` | Ghi chú phân tích cũ trong workspace. Đây là tài liệu làm việc cần đối chiếu với V3; nếu khác nhau thì không tự coi ghi chú cũ là quyết định cuối. |
| Source, API và dữ liệu hiện tại | Bằng chứng AS-IS và dependency. Không dùng hiện trạng làm lý do để giữ nghiệp vụ sai. |

### Quy tắc xử lý mâu thuẫn

1. Yêu cầu trực tiếp mới nhất của người dùng cho Veriq.
2. V3 cho nghiệp vụ và prompt UI cho thiết kế, áp dụng đúng phần việc của từng tài liệu.
3. Link chia sẻ cho tham khảo tương tác.
4. Source hiện tại để xác minh hành vi, quyền và dữ liệu cần bảo toàn.

V3 có ví dụ persona Developer, còn quyết định sản phẩm trước đó là BA, Tester và Admin. Persona Developer không tự tạo role Developer. Chỉ thay đổi role nếu có quyết định nghiệp vụ mới.

Prompt UI có đề xuất drawer và modal cho một số tác vụ. Yêu cầu trực tiếp trước đó của người dùng là các tác vụ chính phải có trang riêng và không dùng modal. Wireframe sẽ ưu tiên route/trang cho tạo, sửa, so sánh và xem chi tiết; không dùng drawer/modal làm nơi thay cho một trang công việc.

## 2. Những gì đã xác minh ở workspace

- HEAD là `09a8e5385` trên nhánh `main`, trùng baseline ghi trong V3.
- UI đã được sửa trong `ProjectsPage.jsx`, `DashboardPage.jsx`, `RequirementsPage.jsx`, `RequirementsListPanel.jsx`, `TraceabilityPage.jsx`, `ExecutionPage.jsx`, `TestDesignPage.jsx` và component `TestPlanCatalog.jsx`. Các chỉnh sửa này mới là triển khai, chưa được nghiệm thu toàn bộ.
- `docs/kien-truc/PHAN_TICH_SAN_PHAM_VERIQ.md` có nội dung phân tích trước đây nhưng chưa được đối chiếu toàn diện theo V3. Không xem những kết luận trong đó là đã xác minh.
- Đã kiểm tra runtime Dashboard trước khi phiên hết hạn. Sau khi dựng lại container, phiên đăng nhập Chrome bị hết hạn; route `/dang-nhap` trả 200 nhưng browser accessibility tree chỉ hiển thị khung trống/trạng thái chờ. Vì vậy chưa xác minh được các trang đã refactor bằng thao tác trình duyệt sau build.
- Docker frontend đã qua format, lint và production build. Đây là kiểm tra biên dịch, chưa thay thế nghiệm thu giao diện, quyền hoặc tác vụ đầu-cuối.
- Các lần xem trước cho thấy một số thành phần có bố cục dạng mẫu và lặp container. Nhận xét này chỉ áp dụng cho các màn đã xem; cần kiểm tra baseline đầy đủ và tác vụ thật trước khi kết luận toàn giao diện.

## 3. Phạm vi sản phẩm cần kiểm tra

Kiểm tra các luồng và trang có thật trong HEAD, không tạo thêm module chỉ vì có tên trong prompt hoặc còn route legacy:

1. Dự án và lời mời.
2. Tổng quan dự án.
3. Requirement, phiên bản, AC/BR, nguồn tài liệu và phân tích ảnh hưởng.
4. Test Plan, chu kỳ, phạm vi, người phụ trách, review và phê duyệt.
5. Test Case, phân tích/điều kiện kiểm thử, bộ kiểm thử, dữ liệu, phiên bản và trace.
6. Test Run, execution/result, Defect, retest, Release/Build/Environment.
7. Dashboard, báo cáo tiến độ/hoàn tất, metric và export.
8. Tài liệu dự án, trình đọc và thư viện tri thức.
9. Cài đặt dự án, thành viên, quyền, nhật ký.
10. Quản lý tài khoản, tài khoản cá nhân và xác thực.
11. AI capability đang tồn tại: tóm tắt tài liệu và xử lý phiên bản/ảnh hưởng theo quyết định sản phẩm mới nhất; các capability khác phải được kiểm kê trước khi quyết định giữ hay bỏ.

Menu, route hoặc schema tự thân không chứng minh tính năng đang được người dùng dùng. Cần nối UI → client → API → policy → service → persistence → event/worker → report/AI/test.

## 4. Giai đoạn 1 — Kiểm toán chiều rộng toàn sản phẩm

Mục tiêu là dựng được bản đồ Veriq trước khi sa vào phân tích một trường hoặc một module. `PLAN.owner_id` và các ví dụ V3 chỉ minh họa độ sâu cần đạt; không phải trọng tâm hay phạm vi ưu tiên.

### 1.1 Bảo toàn baseline

- Ghi HEAD, branch, working tree và danh sách file đã thay đổi.
- Tách thay đổi code, tài liệu, file sinh tự động và dữ liệu local.
- Không reset, xóa dữ liệu hoặc ghi đè thay đổi người dùng.
- Lấy ảnh baseline bằng Docker ở 1280×720, 1440×900 và 1920×1080 theo prompt UI; lưu riêng ảnh trước sửa. Nếu không thể cô lập baseline sạch, ghi rõ blocker và không gọi ảnh local là baseline gốc.

### 1.2 Quét toàn bộ repository và đọc logic theo luồng

- Quét cấu trúc toàn bộ source frontend, backend, worker, AI, cấu hình, schema, migration, job, test, tài liệu API và sơ đồ. Ghi module, loại file, số dòng, symbol, dependency và trạng thái trong manifest. Manifest tại `docs/business-redesign/00_SOURCE_MANIFEST.csv` đã có; script scan phải bỏ qua `node_modules`, build output và file sinh tự động.
- Không đọc tuần tự theo từng file. Bắt đầu từ các tác vụ chính và lần theo call graph UI → client → route → authorization → service → repository/persistence → worker/event → report/AI. Đọc trọn các module/rule liên quan trên đường đi; mở rộng sang call sites và legacy để xác định tác động trước khi đề xuất thay đổi.
- Dùng parser/search để lập index nhanh, nhưng không coi tên symbol hoặc chuỗi là kết luận nghiệp vụ. Đánh dấu `READ` chỉ khi đã đọc nội dung; `SPOT_CHECKED_NOT_COMPLETE` khi mới đọc một phần; `STRUCTURE_SCANNED` là trạng thái độc lập. Tập trung đọc sâu code mang nghiệp vụ; cấu hình thuần, asset, dependency vendored và file sinh tự động được phân loại riêng, không làm chậm việc xác định luồng dùng thật.
- Đọc entrypoints, router, component/page, client, contract/schema, service, repository, policy, worker, AI capability, report/export, migration và test theo từng luồng liên module. Nối đủ nơi tạo/sửa dữ liệu với mọi consumer quan trọng.
- Tạo bản đồ module, chức năng, chức năng con, route, API, entity/collection, job, tích hợp và sơ đồ phụ thuộc. Ghi cả tính năng API-only hoặc không có menu.

### 1.3 Dựng bản đồ tác vụ và phạm vi sản phẩm

- Tạo bản đồ tác vụ người dùng theo persona thực tế; cho từng tác vụ ghi mục tiêu, trigger, dữ liệu đầu vào, quyết định, kết quả, quyền và đường UI/API.
- Kiểm kê mọi màn hình, form, field lồng nhau, nút/hành động, filter, cột, trạng thái, transition, validation, rule và metric.
- Đối chiếu với use case, đề tài khóa luận, prompt V3, prompt UI và link tham khảo. Ghi nguồn và mức tin cậy cho từng yêu cầu; ví dụ trong tài liệu không tự thành kết luận sản phẩm.
- Phân biệt tính năng đang chạy, route legacy, capability ẩn, thử nghiệm, API nội bộ, chức năng trùng và chức năng không rõ người dùng.

### 1.4 Tìm vấn đề và dependency trên toàn hệ thống

- Xác định nhu cầu mà từng chức năng giải quyết; đánh dấu khi không tìm thấy tác vụ hoặc giá trị rõ ràng.
- Tìm nghiệp vụ bất hợp lý, dư thừa, thiếu, mâu thuẫn, chưa có rule, dữ liệu lặp, hành động khó hiểu và logic lệch giữa UI/API/database.
- Vẽ các quan hệ Requirement–Plan–Period–Suite–Case–Run–Result–Defect–Report, tài liệu/version, Release/Build/Environment, user/role/permission và AI.
- Theo từng entity, lần consumer/producer qua frontend, API, DB, event, worker, thông báo, tìm kiếm, import/export, report, AI, audit và migration.
- So sánh tác vụ với tài liệu sản phẩm chính thức của các công cụ kiểm thử hiện có. Ghi khác biệt và nguồn; không sao chép tính năng chỉ vì sản phẩm khác có.
- Tạo issue register cho toàn hệ thống. Gom biểu hiện có chung nguyên nhân gốc; tách `BUG`, `BUSINESS_CONFLICT`, `MISSING_DEFINITION`, `MISSING_CAPABILITY`, `FRICTION_OR_REDUNDANCY`, `DATA_MODEL_ISSUE` và `RISK_HYPOTHESIS`.

**Đầu ra Giai đoạn 1:** source manifest có độ phủ, bản đồ module/chức năng, bản đồ tác vụ, danh mục route/API/entity, sơ đồ dependency và issue register rộng. Chưa sửa nghiệp vụ chỉ dựa vào suy đoán; có thể sửa lỗi build hoặc blocker audit riêng nếu cần và có bằng chứng.

## 5. Giai đoạn 2 — Kiểm toán chiều sâu đồng đều

Chỉ bắt đầu đào sâu có hệ thống khi đã có bản đồ chiều rộng. Phương pháp V3 áp dụng cho toàn bộ trường và chức năng, không riêng `PLAN.owner_id` hay danh sách ví dụ.

### 2.1 Phân tầng và lấy mẫu có kiểm soát

- Dùng bản đồ giai đoạn 1 để chia công việc theo domain, luồng nghiệp vụ và mức tác động; không đi từng field theo thứ tự máy móc.
- Ưu tiên nhóm có dependency chéo, quyền/lifecycle, nguồn dữ liệu, snapshot/version, metric hoặc ảnh hưởng nhiều tác vụ. Vẫn thống kê độ phủ cho mọi module và field.
- Chọn lát dọc đại diện ở nhiều domain để xác minh cách audit, không biến một lát thành trọng tâm toàn dự án.

### 2.2 Phân tích sâu field/action/rule/relation/metric

Mỗi kết luận có ID ổn định và evidence. Dùng template V3 cho toàn bộ field và chức năng:

- Giá trị công việc và người dùng cần nó.
- Định nghĩa, nguồn chuẩn, kiểu, cardinality, default, required theo trạng thái và validation.
- Ai tạo/xem/sửa/xóa/chuyển, quyền backend, điều kiện và lifecycle.
- Nguồn dữ liệu, producer, consumer, snapshot, version và quan hệ với field gần nghĩa.
- Tác động khi member/role/account/artifact bị đổi, khóa, archive hoặc mất nguồn.
- Hành vi lỗi, retry, concurrent update, idempotency, stale revision và khôi phục.
- Migration, legacy data, report lịch sử và rollback.
- Nghiệm thu và regression liên quan.

Tạo và duy trì inventory, action/transition, rule, relationship, ownership matrix, UI/API/DB reconciliation, event impact, metric dictionary và decision log theo deliverable V3. Cột trường trong inventory phải là từng field path, không gộp các trường khác nghĩa vào một hàng.

### 2.3 Tìm nguyên nhân gốc và xác minh

- Mở rộng chủ động từ source, luồng, dữ liệu, quyền và test; không giới hạn ở issue đã được người dùng nêu hoặc prompt V3 liệt kê.
- Nhóm issue theo nguyên nhân như nguồn sự thật kép, lifecycle không nhất quán, quyền phân tán, trạng thái suy diễn sai, dữ liệu nhập lặp, snapshot không đúng ranh giới, hoặc metric sai mẫu số.
- Đối chiếu code tĩnh, cấu hình, migration, dữ liệu tổng hợp không định danh và hành vi runtime. Phân biệt `VERIFIED_CODE`, `VERIFIED_RUNTIME`, `HYPOTHESIS`, `UNVERIFIED`, `BLOCKED` và `NOT_RUN`.
- Thực hiện journey đầu-cuối với fixture an toàn; không dùng dữ liệu thật để tạo/sửa thử nếu chưa cô lập fixture. Ghi bằng chứng, lệnh và kết quả.
- Dùng số đếm chính xác theo ID ổn định để báo cáo độ phủ; không tự tuyên bố hoàn tất khi còn source hoặc consumer chưa kiểm kê.

**Đầu ra Giai đoạn 2:** hồ sơ sâu đồng đều, nguyên nhân gốc đã nhóm, các câu hỏi nghiệp vụ còn mở, dependency P0/P1, mức độ bao phủ và khoảng trống bằng chứng.

## 6. Giai đoạn 3 — Tái thiết kế nghiệp vụ tổng thể

- Chuyển issue đã xác minh thành phương án giữ, bỏ, gộp, sửa hoặc bổ sung. Không quyết định chỉ vì code hiện tại có/không có một trường.
- Xây dựng lại task flow, domain model/ERD, nguồn dữ liệu chuẩn, quy tắc, permission matrix, lifecycle/transition, ownership, snapshot/version, metric và xử lý lỗi.
- Giải quyết mâu thuẫn giữa các module tại nguyên nhân gốc. Tách quyết định đã chốt, đề xuất, giả thuyết và câu hỏi còn thiếu.
- Kiểm tra với các tình huống thật: dự án có/không có requirement, nhiều lần chạy, carry-over, thành viên đổi role/rời dự án, thay version sau duyệt, lỗi/retest, report chưa đủ dữ liệu, import và AI không chắc chắn.
- So sánh theo nhu cầu người dùng với Jira/Xray/TestRail/Azure DevOps và nguồn chính thức liên quan; không biến cấu trúc của sản phẩm khác thành yêu cầu bắt buộc.
- Cập nhật use case/kiến trúc khóa luận theo TO-BE đã chốt, nhưng giữ riêng hồ sơ AS-IS. Mỗi thay đổi có impact, acceptance, migration và rollback.

**Cổng trước triển khai:** bản đồ toàn hệ thống đủ độ phủ; issue P0/P1 và rule liên module có quyết định; thiết kế dữ liệu/permission/lifecycle nhất quán; migration và regression được xác định; blocker được ghi rõ. Không cần che giấu những phần chưa biết.

## 7. Giai đoạn 4 — Triển khai UI trước, business sau

### 4.1 Refactor frontend theo các phase UI

- Giữ nguyên API, schema, backend, quyền, state, routing và các chức năng hiện có theo `MASTER_PROMPT.md`.
- Hoàn tất từng phase UI theo đúng thứ tự trong prompt; kiểm kê và giữ vị trí tương ứng cho mọi chức năng trước khi đổi layout.
- Chạy format, lint, build bằng Docker. Kiểm tra trang, quyền, trạng thái tải/rỗng/lỗi và tác vụ ở các kích thước prompt.
- Không quay lại sửa business giữa các phase UI. Nếu phát hiện lỗi business/API khiến UI không thể hoạt động, ghi lại để xử lý sau frontend; chỉ sửa frontend tương thích hợp đồng hiện có.

### 4.2 Chuyển lại business sau UI

Sau Phase 9, kiểm tra toàn bộ luồng và chức năng frontend đã được chuyển sang giao diện mới, đối chiếu quyền và dữ liệu thật, rồi tiếp tục business audit theo thứ tự 16 nhóm. Frontend không được xem là hoàn tất chỉ dựa trên build xanh.

Không tạo wireframe mới hoặc đổi layout/component để hoàn thành prompt UI cũ. Không sửa giao diện tiện tay trong khi làm backend; nếu thay đổi business contract buộc phải cập nhật kết nối frontend để luồng hiện có không hỏng, chỉ sửa phần kết nối tối thiểu và ghi rõ phạm vi, không redesign.

### 4.3 Wireframe và UI/UX

Theo chỉ đạo mới nhất, hoàn tất frontend trước khi quay lại business audit. Dùng wireframe trong `MASTER_PROMPT.md` làm chuẩn cho từng trang; chỉ tạo hoặc cập nhật wireframe khi cần để triển khai một trang, không mở thêm đợt lập kế hoạch dài. Mỗi vùng cần khớp tác vụ, dữ liệu, hành động, quyền và trạng thái thật; không điền số giả.

Wireframe phải đối chiếu đầy đủ global layout và từng trang trong `MASTER_PROMPT.md`: Dự án, Dashboard, Requirement, Test Plan, Test Case, Test Run, Defect, Báo cáo, Tài liệu dự án, Thư viện tri thức, Cài đặt, Quản lý tài khoản, Tài khoản cá nhân, xác thực và AI theo ngữ cảnh. Mỗi trang có bố cục hợp với dữ liệu; không đổi bảng thành thẻ rồi gọi là redesign.

Các lựa chọn bảng, split view, inline edit, drawer và modal lấy theo prompt UI, nhưng phải kiểm tra với yêu cầu trực tiếp. Luồng chính và biểu mẫu dài dùng trang riêng; không đặt toàn bộ màn hình nghiệp vụ vào overlay. Giữ thương hiệu Veriq, không tagline vô nghĩa, không thêm comments trong code.

Đối chiếu `PAGE_MAPPING.md` và `FUNCTION_PRESERVATION.md` khi triển khai; không xem việc thêm tài liệu là thay thế cho trang chạy được hoặc kiểm tra trực tiếp.

### 4.4 Triển khai và nghiệm thu theo từng trang

Theo phase của prompt UI: Design System/Global Layout → Dự án/Dashboard → Requirement → Test Plan → Test Case → Test Run/Defect → Report/Tài liệu → Settings/Tài khoản/Xác thực → nghiệm thu.

Với mỗi trang:

1. Hoàn thiện một wireframe gắn dữ liệu và thao tác thật.
2. Đối chiếu route, API, quyền và các state trước khi code.
3. Triển khai layout riêng theo task; dùng chung component khi cùng hành vi.
4. Giữ mọi chức năng hiện có hoặc ghi quyết định chuyển/bỏ có evidence.
5. Chạy lint/format/build và các test liên quan theo script có sẵn.
6. Mở Docker ở các độ phân giải trong prompt, chạy tác vụ thật và lưu ảnh trước/sau.
7. Cập nhật `CHANGELOG.md`, `TEST_REPORT.md`, `KNOWN_ISSUES.md` và checkpoint.

Không đổi công thức, permission, trạng thái hoặc API chỉ để hợp giao diện. Nếu UI phát hiện business rule mới sai, quay lại decision log và sửa theo giai đoạn A.

## 8. Trạng thái hiện tại và việc tiếp theo

Trạng thái theo 16 nhóm nghiệp vụ được theo dõi tại [`docs/business-redesign/STATUS.md`](../business-redesign/STATUS.md). Nhóm chỉ được nghiệm thu sau khi có bằng chứng kiểm thử; các sửa đổi cũ trong working tree không tự được tính là hoàn tất.

- Nguồn chuẩn đã được phân biệt: V3 là khung phương pháp kiểm toán toàn hệ thống; UI master prompt là căn cứ thiết kế; link là tham khảo bổ sung.
- `docs/ui-ux-redesign/MASTER_PROMPT.md` là bản lưu prompt UI nguyên văn để dùng tiếp.
- Bản V3 được lưu cạnh prompt UI để giữ đúng phiên bản nguồn.
- `docs/kien-truc/PHAN_TICH_SAN_PHAM_VERIQ.md` là ghi chú cũ cần reconcile; chưa chứng minh toàn bộ audit V3.
- Working tree có sẵn nhiều thay đổi nghiệp vụ chưa nghiệm thu. Trong phase hiện tại chỉ thay đổi frontend phục vụ refactor giao diện; không hoàn tác hay ghi đè các sửa đổi sẵn có.
- Các ghi chú `PLAN.owner_id` trước đó đã được chuyển vào `docs/business-redesign/examples/`; chúng chỉ minh họa cách ghi evidence, không phải issue backlog, trọng tâm hay đại diện cho độ phủ audit.

**Trạng thái UI hiện tại:** Tiếp tục refactor toàn bộ frontend theo Phase 0–9. Chỉ chuyển sang kiểm toán business sau khi các trang, luồng hiển thị và trạng thái frontend đã được rà soát, Docker build và các kiểm tra giao diện khả dụng đã hoàn tất. Không dừng giữa các phase để chờ người dùng accept.

Các thay đổi giao diện đã có ở Dự án, Tổng quan, Requirement, Test Plan, Test Case/Test Suite, Test Analysis, Test Run/Defect, Báo cáo, Tài liệu/Tri thức, Chu kỳ/Release, Truy vết/Thay đổi, Cài đặt, Tài khoản và xác thực. Đây là trạng thái triển khai, chưa đồng nghĩa toàn bộ frontend đã nghiệm thu. Trong đợt này tiếp tục kiểm tra và sửa frontend; không mở lại các thay đổi backend nghiệp vụ đang có sẵn trong working tree.

Checkpoint gần nhất: Docker format check, ESLint, Next production build và `git diff --check` đã qua; frontend container healthy và route gốc trả HTTP 200. Không thể xác minh trực quan qua Chrome trong phiên này vì browser surface không khả dụng. Các nhóm cần rà tiếp: responsive và trạng thái trang Tài liệu/Tri thức; thao tác quản lý tài khoản/Cài đặt; Thông báo và xác thực; nghiệm thu luồng trang bằng trình duyệt khi browser surface sẵn sàng.
