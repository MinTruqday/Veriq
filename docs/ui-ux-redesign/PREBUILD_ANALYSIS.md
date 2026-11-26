# Phân tích toàn bộ giao diện Veriq trước khi dựng lại

## Trạng thái

Đây là phân tích từ frontend hiện ở Git `HEAD`, sau yêu cầu khôi phục giao diện gốc. Không coi các mục “implemented” trong `UI_REFACTOR_PROGRESS.md` là trạng thái hiện tại: ghi chú đó thuộc lượt giao diện trước khi reset. Đã đối chiếu đủ 11 ảnh: Dự án, Dashboard, Requirement, Test Case, Test Run, Defect, Báo cáo, Tài liệu dự án, Knowledge Library, Cài đặt, Test Plan và chi tiết chu kỳ. Working tree backend có thay đổi sẵn của người dùng; phạm vi dưới đây không sửa backend, API, schema, quyền hay nghiệp vụ. Hai file Requirement mới chạm thử trong lúc phân tích đã được trả về `HEAD`; hiện phân tích chưa để lại thay đổi frontend.

## Căn cứ thiết kế

- Ảnh tham chiếu Requirement: thanh thao tác chung; danh sách chọn ở trái; nội dung dạng tài liệu bên phải; tab nội dung, lịch sử, ảnh hưởng, truy vết; AC/BR tách bạch.
- Ảnh Test Plan: một khu vực có hai chế độ Kế hoạch / Quản lý chu kỳ; nhóm chu kỳ thu gọn; kế hoạch không thuộc chu kỳ ở nhóm riêng; mở chu kỳ ra dashboard tổng kết, danh sách kế hoạch, rà soát và đóng chu kỳ.
- Yêu cầu trực tiếp: hai trang phải có ngôn ngữ thị giác ăn nhập với Dự án/Tổng quan, thoáng, không lồng nhiều khung khiến nội dung như “bị bọc” và chật.
- Pasted prompt là chỉ dẫn thiết kế bổ trợ, không thay thế yêu cầu trực tiếp: giữ brand/tokens, API, dữ liệu, quyền, workflow, validation; không dùng dữ liệu giả hoặc bỏ tính năng.

## Nguyên tắc nhất quán xuyên màn hình

“Ăn nhập” không có nghĩa biến tất cả trang thành cùng một mẫu. Các màn nên chia sẻ một khung: cùng vị trí tiêu đề và hành động, chiều rộng nội dung có kiểm soát, cùng cỡ chữ/nhịp khoảng cách, trạng thái và cách dùng nút; sau đó mỗi khu vực có bố cục hợp việc cần làm. Ảnh minh họa dùng màu xanh dương, còn Veriq dùng token thương hiệu riêng; giữ nhận diện Veriq và mượn cấu trúc/nhịp đọc của ảnh, không sao chép màu rời khỏi design system.

Điểm gây cảm giác “lột da” khi sửa là thay nền/khung toàn app mà không giữ liên kết với shell; điểm gây “ngộp” là lồng `WorkspacePage` → nhiều `Panel` → bảng/form lại có viền/nền riêng. Cách sửa phải đặt ở đúng tầng: giữ shell/sidebar/header, thống nhất nội dung trang, rồi giảm lớp viền bên trong. Không dùng thêm card làm thuốc chữa cho card.

## Kiểm kê 11 màn theo ảnh và hướng xử lý

| Màn | Tác vụ và cấu trúc đúng theo ảnh | Phát hiện ở code gốc / rủi ro | Quyết định trước triển khai |
|---|---|---|---|
| 1. Dự án | Chọn dự án nhanh: thẻ dự án, tìm/lọc, Grid/List, tiến độ, thành viên, trạng thái | `ProjectsPage.jsx` hiện có bảng/list dạng hàng và nhiều cột; chưa có lựa chọn thẻ Grid theo thiết kế gửi | Làm lưới 2–3 cột mặc định, giữ list toggle, tìm/lọc/pagination, lời mời, tạo/archiving; chỉ hiện tiến độ/thành viên khi số liệu API thật hỗ trợ |
| 2. Tổng quan | Nhìn tiến trình, kết quả, lỗi và việc cần xử lý ngay | `DashboardPage.jsx` đã có dữ liệu dashboard/coverage thật, stepper có liên kết và trạng thái tải/lỗi; dùng nhiều panel nhưng mỗi panel phục vụ nhóm dữ liệu khác nhau | Giữ bố cục thoáng dạng ảnh, ưu tiên stepper và 3 cụm KPI; không lặp metric; trend chỉ khi có lịch sử thật, nếu thiếu thì dùng phân bố trạng thái hiện có hoặc empty state |
| 3. Requirement | Danh sách bên trái, tài liệu yêu cầu bên phải, tab nội dung/lịch sử/ảnh hưởng/truy vết | Route chọn yêu cầu làm biến mất danh sách; bên phải dồn nội dung, ảnh hưởng, lịch sử, trace nối tiếp; history còn xuất hiện lặp. Danh sách là table nên không thể thu hẹp nguyên dạng | Split view 30/70 với list rows; tab tách nội dung liên quan; AC/BR dạng tài liệu; giữ versioning, review, AI, import, bulk actions, permissions |
| 4. Test Case | Kho case có nhóm và nội dung ca đọc được, bước rõ | `TestDesignPage.jsx` chứa nhiều panel: thông tin chung, luồng, pre/postcondition, steps, liên kết, lịch sử và các bảng. Dồn cả kho và nội dung vào một trang dài có nguy cơ quá tải | Repository/list và detail split; chi tiết dùng nhóm phẳng/tab theo dữ liệu thật; giữ table tùy chọn cho số lượng lớn, chọn nhiều, version/AI/review/trace |
| 5. Test Run | Không gian thao tác của Tester: list ca + step đang thực hiện + lưu kết quả/bằng chứng | Đã có `RunExecutionWorkspace.jsx` tách biệt, gồm trạng thái, các bước, evidence và điều hướng; khác các màn đọc/CRUD nên không ép chung layout | Giữ execution workspace riêng; thống nhất header, trạng thái, spacing; ưu tiên bước hiện tại và nút lưu; bảo toàn enum, lưu trước khi chuyển, defect inline và quyền |
| 6. Defect | Kanban theo vòng đời và List để lọc số lượng lớn | `DefectsPage.jsx` có bảng danh sách, chuyển trạng thái có gate và retest; tìm trùng, AI/trace workflow xuất hiện trong trang. Chưa thấy Kanban trong route đang dùng | Bổ sung view switch nếu trạng thái/transition hiện có cho phép; không tự do kéo thả vượt rule; detail/AI/retest/history giữ nguyên |
| 7. Báo cáo | Dashboard tình hình test hiện thời, filter plan/time, KPIs, grouped outcomes, completion criteria, export | `ReportsPage.jsx` bọc `SimpleTestReports`; component có báo cáo động và snapshot/lịch sử, nên phải kiểm kê snapshot/export và không thay công thức bằng mẫu chart | Dùng dashboard + preview, ưu tiên plan/time và KPI; chart chỉ dựa trên report response; lịch sử/export giữ nguyên |
| 8. Tài liệu dự án | File explorer; khi mở: TOC, reader, AI theo ngữ cảnh | `DocumentReaderPage.jsx` là luồng reader riêng, có parse định dạng/reader nội dung; upload, parse state và AI cần bảo toàn | Tách thư viện tệp khỏi reader; reader ba vùng chỉ khi nguồn có TOC và AI context; nếu không, dùng empty/ẩn panel phù hợp, không bịa |
| 9. Knowledge Library | Tìm kiếm tri thức và danh sách nguồn đã lập chỉ mục | `KnowledgePage.jsx` hiện đặt tìm kiếm, bảng kết quả và thư viện trong panel nối tiếp, có nhiều trạng thái indexing/degraded và quyền quản trị | Để search làm điểm vào, kết quả có trích dẫn/source; nguồn là danh sách gọn; trạng thái lập chỉ mục/degraded và thao tác thật giữ nguyên |
| 10. Cài đặt | Cấu hình theo nhóm: menu trái, form phải | `SettingsPage.jsx` đã dùng segmented tabs và nhiều panel nối tiếp; nhiều trường/ngành cài đặt hiện tại hơn ví dụ ảnh | Dùng settings nav trên desktop, content theo một nhóm; giữ member/access tables ở chỗ cần quản lý hàng loạt; không gom tất cả form thành trang dài |
| 11. Test Plan + chu kỳ | Hai chế độ cùng một khu vực; plan xếp theo cycle; detail cycle là dashboard và bước rà soát trước đóng | Plan hiện là bảng rộng trong `ExecutionPage.jsx`; cycle là route riêng `TestPeriodsPage.jsx`; detail plan là form read-only nhiều section và cycle detail dùng panel nối tiếp | Một catalog/tabs, group theo cycle và “không thuộc chu kỳ”; detail plan dạng document; detail cycle summary → plans → results → review/close; URL cũ vẫn tương thích |

Các nhóm màn khác trong prompt (documents, account, auth, admin, trace, AI, releases) không xuất hiện đủ trong 11 ảnh nhưng vẫn là phạm vi bảo toàn nếu refactor chạm shared shell. Không tuyên bố đã redesign các màn đó chỉ vì dùng chung token hoặc header.

## Hệ thống dữ liệu và thao tác – đường dẫn phải được rà trước mỗi module

| Khu vực | UI đang dùng | Tầng dữ liệu/logic cần giữ khi làm lại |
|---|---|---|
| Dự án/Tổng quan | `ProjectsPage.jsx`, `DashboardPage.jsx` | `testing.service.js`, endpoint project/dashboard/coverage, permission trong project workspace |
| Requirement | `RequirementsPage.jsx`, `workspace/requirements/*` | API list/detail/version/document/AI/impact/trace, permission checks, autosave draft/version/review |
| Test Plan/Cycle | `ExecutionPage.jsx`, `TestPeriodsPage.jsx`, `TestPlanEditor.jsx` | API plan/period/progress/run; owner/scope/suite/cases/schedule/risks; revision control; carry-over eligibility/reason/close gate |
| Case/Run/Defect | `TestDesignPage.jsx`, `RunExecutionWorkspace.jsx`, `DefectsPage.jsx` | API lifecycle/version/step result/evidence/retest/transition; existing enum and transition policy |
| Report/Docs/Knowledge/Settings | `SimpleTestReports.jsx`, `DocumentReaderPage.jsx`, `KnowledgePage.jsx`, `SettingsPage.jsx` | report snapshots/export; upload/parse/retry; indexing/search citation/degraded mode; settings/member/access permission |

## Chẩn đoán hệ thống, không chỉ hai màn

1. **Cấp vỏ:** `WorkspacePage` có typography/spacing của riêng nó nhưng title đang lớn 28–32px, so với prompt 22–24px; các ảnh tham chiếu nội dung căn lề khác nhau, nếu giữ nguyên khi lồng trong shell thì độ rộng/nhịp không nhất quán. Chỉ chỉnh token/shared page header khi kiểm tra ảnh các màn khác, tránh làm đổi sidebar/header toàn cục lần nữa.
2. **Cấp bố cục:** các module chuyên biệt đều dùng `Panel`; một số đúng mục đích (Dashboard/report), một số tạo panel trong panel quanh tài liệu/form. Phải chọn theo tác vụ thay vì xóa mọi khung hoặc bọc tất cả thành thẻ.
3. **Cấp mật độ:** Requirement/Test Plan/Test Case là các màn đọc/soạn nội dung nhưng trình bày kiểu quản trị bảng/form. Đây là lý do chúng ngộp hơn Projects/Dashboard vốn đã có phân cấp theo mục đích.
4. **Cấp dữ liệu:** tiến độ plan/cycle, line chart và report có thể rỗng hoặc API lỗi. Giao diện phải phân biệt `0`, không có dữ liệu, chưa tải và tải lỗi; không lấp bằng demo.
5. **Cấp responsive:** split view phải chuyển thành 1 cột có điều hướng quay lại; bảng dùng vùng cuộn có chủ đích; header actions được wrap. Không làm cột 30/70 trên viewport hẹp.
6. **Cấp hồi quy:** shared styles có thể làm màn đã dễ nhìn (Projects/Dashboard/Run execution) xấu theo. Nghiệm thu phải mở lại các trang mốc, không chỉ nhìn trang đang chỉnh.

## Nguyên nhân gốc đã đối chiếu với code

### Requirement

1. Route danh sách và route chi tiết là hai trạng thái tách rời. Khi mở một yêu cầu, danh sách biến mất (`RequirementsPage.jsx`); người dùng mất điểm tựa để đổi đối tượng.
2. Danh sách trong `RequirementsListPanel.jsx` là `Panel` chứa toolbar, bộ lọc mở rộng, `DataTable` và pagination. Nếu đặt vào split view 30%, bảng vốn thiết kế cho chiều rộng trang sẽ bị ép và tạo nhiều lớp đường viền.
3. Tab chi tiết chỉ có “Yêu cầu” và “Lịch sử và rà soát”. Trong tab đầu, component phiên bản hiện tại, ảnh hưởng, lịch sử và truy vết được xếp dọc; lịch sử lại được render lần nữa ở tab sau. Đây là nguyên nhân trực tiếp làm trang dài và lặp.
4. Workspace chi tiết dùng panel/form hiện hữu vốn tối ưu cho quản trị trường dữ liệu, trong khi tác vụ chính là đọc và phân tích nội dung.

### Test Plan / Chu kỳ

1. Kế hoạch được hiển thị như bảng rộng (`DataTable`) trong một `Panel`, với bộ lọc nhiều trường; chu kỳ lại là route độc lập (`TestPeriodsPage.jsx`). Người dùng phải đổi trang để qua lại hai phần vốn cùng một tác vụ.
2. Route chu kỳ chỉ có tạo chu kỳ và danh sách chu kỳ. Thiếu tìm kiếm/ lọc và cách nhóm kế hoạch theo chu kỳ ngay tại catalog.
3. Chi tiết kế hoạch hiển thị `TestPlanEditor` read-only bên trong một `Panel`; form sửa đầy đủ các trường tạo cảm giác đặc, dù người dùng chỉ cần đọc cấu trúc kế hoạch.
4. Chi tiết chu kỳ có các panel nối tiếp cho kế hoạch, thống kê và rà soát. Thứ tự dữ liệu đúng nghiệp vụ nhưng phân cấp chưa rõ và không tạo một mặt bằng làm việc thống nhất với danh sách.

## Quyết định bố cục TO-BE

### Ngôn ngữ chung cho hai module

- Giữ `WorkspacePage`, app shell, sidebar, header, typography, màu thương hiệu và nút hiện tại. Không áp màu xanh trong ảnh tham chiếu nếu khác token Veriq.
- Dùng một tiêu đề trang và một vùng làm việc chính. Chia khu vực bằng khoảng cách, nền nhẹ và divider; chỉ dùng viền cho ranh giới vùng lớn. Không bọc từng trường/nhóm bằng panel.
- Giữ mật độ, chiều rộng nội dung và trạng thái chọn nhất quán; từng module vẫn có cấu trúc riêng theo tác vụ.
- Desktop: tận dụng chiều ngang app; responsive: split view chuyển thành danh sách → chi tiết có nút quay lại, không ép hai cột hẹp.

### Requirement — Split Document Workspace

- Thanh đầu: “Yêu cầu”, nhập tài liệu, tạo yêu cầu; tác vụ hàng loạt (nhãn, dò trùng, gộp, lưu trữ) chỉ hiện khi có lựa chọn và đủ quyền.
- Toolbar gọn: tìm kiếm luôn thấy; trạng thái lọc nhanh. Các lọc nâng cao/sắp xếp hiện tại tiếp tục có trong disclosure.
- Trái ~30%: danh sách dạng hàng/văn bản, mỗi dòng mã, tiêu đề, phiên bản, trạng thái; chọn dòng cập nhật chi tiết mà không rời workspace. Giữ phân trang khi nguồn API phân trang.
- Phải ~70%: mã/phiên bản, tiêu đề, trạng thái và thao tác theo quyền; tab thật sự tách Nội dung / Lịch sử & rà soát / Ảnh hưởng / Truy vết. Không render nội dung tab ẩn trùng lặp.
- Nội dung: mô tả đọc như tài liệu; AC và BR là các dòng/khối phẳng có mã; trường bổ sung, nguồn và liên kết giữ nguyên nhưng xếp sau phần cốt lõi hoặc disclosure. Chỉnh sửa vẫn dùng cơ chế draft/version, không biến phiên bản khóa thành editable.
- Chọn “Tạo yêu cầu”, import tài liệu, kiểm tra trùng/gộp, bulk tags/archive, review, compare, source document, permission gate, loading/error và deep link phải còn đường thao tác tương ứng.

### Test Plan — một catalog hai chế độ

- Trong route kế hoạch, đặt segmented navigation “Kế hoạch” / “Quản lý chu kỳ”; giữ route chu kỳ hiện có làm điểm vào/deep link tương thích.
- Catalog kế hoạch: tìm kiếm, trạng thái và chu kỳ ở toolbar gọn; giữ lọc người phụ trách/sắp xếp trong bộ lọc nâng cao. Nhóm theo chu kỳ có thể thu gọn; kế hoạch ngoài chu kỳ nằm trong nhóm riêng.
- Mỗi kế hoạch là hàng/card phẳng: mã, tên, trạng thái, ngày/phạm vi khi API có, tiến độ chỉ khi API trả hợp lệ, menu/đường mở. Không tính lại hoặc bịa %.
- Chi tiết kế hoạch: header tài liệu (mã, tên, trạng thái, owner nếu có), hành động sửa/tạo run theo quyền; phần đọc chia section theo đúng các trường/schema đang tồn tại. Form create/edit giữ nguyên đầy đủ field, mặc định, validation, lưu toàn object và hỗ trợ tạo/chọn chu kỳ.
- Chế độ chu kỳ: nhóm chu kỳ và kế hoạch liên kết trên cùng catalog; nút tạo chu kỳ được giữ. Nhấn chu kỳ mở trang chi tiết hiện tại theo cùng page frame.
- Chi tiết chu kỳ: tiêu đề/trạng thái; số liệu thật; thanh tổng kết pass/fail/chưa chạy khi nguồn hỗ trợ; kế hoạch liên kết; danh sách rà soát/carry-over ở cuối với checkbox, lý do bắt buộc, ghi chú, điều kiện open-run, xác nhận đóng. Giữ tạo kế hoạch tiếp theo từ chu kỳ đóng.
- Không tự chuyển ca, không sao chép kết quả, không thay điều kiện đóng.

## Bản đồ bảo toàn chức năng

| Module | Chức năng hiện tại cần giữ | Vị trí sau khi đổi bố cục |
|---|---|---|
| Requirement | Tìm/lọc/sắp xếp/phân trang; chọn nhiều; nhãn; dò trùng; gộp; archive; tạo/sửa draft/version; review/approve/request changes; history/compare; AI/quality; impact; trace; source document import/process/retry; collaboration/comments; permission/loading/error | Toolbar + list; header detail; các tab; nội dung và disclosure; form/route chuyên dụng |
| Test Plan | List/search/status/period/owner/sort; create/edit; draft/ready; period selection/new period; requirements/scenarios/suites/tests/members/environments/runs; review/approval; plan progress; create run; link/deep routes | Catalog/tabs; grouped plan rows; read workspace; edit/create form route |
| Cycle | Create/list/detail/summary; linked approved plans; case eligibility; carry-over selection and reasons; close note; open-run gate; closed carry-over view; next plan creation | Tab/quản lý chu kỳ; expandable groups; cycle dashboard; review/close section |

## Rủi ro dữ liệu và các điểm kiểm tra trước nghiệm thu

- `TestPlanEditor` và các API progress là nguồn chuẩn. Read layout phải đọc toàn bộ field hiện hữu, không làm mất field chỉ vì chuyển từ form sang tài liệu.
- Catalog hiện lấy kế hoạch và chu kỳ từ endpoint riêng. Không được tạo bản sao state sai lệch; cần kiểm tra refresh, deep link, query filter và kết quả sau create/update/close.
- Dữ liệu dự án đã xem trước đó không có kế hoạch/chu kỳ đủ để xem populated states; một progress endpoint có lỗi. Trạng thái này phải hiện như unavailable/empty/error thật, không sinh fixture. Không đóng chu kỳ hoặc tạo dữ liệu lên dự án thật để chụp ảnh.
- Hiện chưa có bằng chứng đủ cho viewport desktop lớn. Nghiệm thu cần mở tối thiểu 1280px và một viewport hẹp; kiểm tra menu/tab/forms không tràn.

## Thứ tự triển khai sau khi hoàn tất phân tích toàn bộ

1. Chốt nền dùng chung theo 11 ảnh và so với Projects/Dashboard hiện tại; không thay shell/brand nếu chưa có căn cứ.
2. Chuyển Projects sang grid + list toggle và rà Dashboard vì đây là hai chuẩn độ thoáng/nhận diện trong cùng bộ ảnh.
3. Làm Requirement Split Document Workspace, bỏ lớp panel/nội dung lặp, giữ nguyên API và hành động.
4. Gộp trải nghiệm Plan/Cycle tại catalog, bảo toàn URL chu kỳ; làm gọn plan detail và cycle dashboard theo phân cấp đã chốt.
5. Tiếp tục Case/Run/Defect/Report/Documents/Knowledge/Settings theo bảng kiểm kê, bảo toàn luồng riêng từng module.
6. Responsive, empty/error/permission states, quyền và các luồng chính; chỉ dùng dữ liệu thật.
7. Mới build và mở web; đối chiếu 1280px, 1440px, 1920px và viewport hẹp; kiểm tra lại trang mốc để phát hiện hồi quy toàn cục.

Không thay đổi backend hoặc dữ liệu để làm giao diện dễ trình diễn. Chưa triển khai frontend trong bước phân tích này.
