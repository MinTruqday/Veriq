# UI refactor report

## Đã triển khai

- Chuẩn hóa design token đang dùng thành bán kính control 7px và panel 8px, giữ màu và font thương hiệu hiện hữu.
- Đồng bộ các class Tailwind `rounded-sm/md/lg/xl/2xl/3xl` về cùng thang 4/6/8px để form, modal, card và auth không còn dùng bán kính 12–24px rải rác.
- Thu gọn phân cấp trang/panel, khoảng đệm và control để tăng mật độ nội dung theo hướng enterprise SaaS.
- Đồng bộ chiều cao top bar giữa header, sidebar và main content.
- Chuẩn hóa metric card dùng chung: bỏ shadow trang trí, giảm số lớn 30px xuống 26px, cho phép nội dung dài xuống dòng.
- Đồng bộ WorkspacePage với PageHeader dùng chung; panel title hỗ trợ xuống dòng an toàn.
- Refactor Dự án thành thẻ thông tin có tiến độ/lịch và summary; Tổng quan thành các giai đoạn kiểm thử có thể điều hướng; Requirement detail thành Document Workspace 30/70 với navigator bên trái. Các tab nội dung, lịch sử phiên bản, phân tích ảnh hưởng, truy vết và rà soát/liên quan được tách riêng. Chi tiết hiện có metadata owner, AC/BR dạng block có mã; draft có owner selector và tiếp tục lưu qua cơ chế draft/revision hiện hữu.
- Refactor Kế hoạch kiểm thử sang thẻ có summary theo trạng thái; Chu kỳ kiểm thử sang bố cục tổng quan, danh sách thẻ và detail hai cột cho kế hoạch/số liệu.
- Danh sách Chu kỳ kiểm thử được hoàn thiện thêm với 4 KPI trạng thái, bộ lọc trạng thái có số lượng, tìm kiếm toàn hàng và chuyển Thẻ/Danh sách. Visual QA trên Docker phát hiện thanh tìm bị co khi đặt cùng filter; đã tách thành hai hàng và xác nhận lại trên dữ liệu thật.
- Refactor tiếp các module ngoài nhóm đầu: Releases có summary/filter theo trạng thái và tìm kiếm các trường nội dung; Hoạt động AI có tìm/lọc lịch sử khi có quyền; Test Analysis có tìm/lọc findings; Knowledge có điều hướng danh sách tài liệu theo metadata và trạng thái chỉ mục. Không thêm dữ liệu mẫu và không đổi hành vi API/quyền.
- Requirement theo prompt Document Workspace: nội dung hiển thị AC/BR thành khối, nguồn trích dẫn có vị trí và link tới reader; lịch sử so sánh phiên bản cạnh nhau; phân tích ảnh hưởng có tóm tắt và đối chiếu trước/sau, giữ nhãn thay đổi bằng chữ.
- Editor của Requirement ở chế độ chỉ đọc không còn được expose như ô nhập trong accessibility tree; phiên bản chuẩn đọc như tài liệu, còn DRAFT giữ editor tương tác theo quyền hiện hữu.
- Defect có Board/List. Board lấy lane từ workflow trạng thái hiện tại, card mở đúng lỗi qua bộ lọc danh sách; không kéo-thả thay đổi trạng thái.
- Empty state Defect phân biệt dự án chưa có lỗi với bộ lọc không khớp. CTA tạo lỗi xuất hiện theo quyền; khi lọc rỗng, CTA xóa lọc khôi phục toàn bộ điều kiện ban đầu.
- Kanban Defect giữ đủ 9 trạng thái workflow, nhưng mỗi lane nay có chiều rộng tối thiểu để đọc thẻ và cuộn ngang thay vì nén cả board vào 68rem; list locale hóa mức độ và ưu tiên. Docker xác nhận 9 lane và cuộn ngang; project kiểm tra rỗng nên chưa có thẻ dữ liệu thật để xác nhận trạng thái dương.
- Cài đặt dự án đổi sang điều hướng trái/phải theo nhóm quyền hiện có; không đổi endpoint hoặc quyền.
- Danh sách Test Run hiển thị tiến độ theo số ca đã ghi nhận và tổng ca, có CTA Tiếp tục/Xem theo trạng thái.
- Form tạo Test Run hướng dẫn khi chưa có kế hoạch được duyệt, chỉ hiện liên kết về kế hoạch nếu có permission đọc; khi chọn plan, tóm tắt số ca của snapshot và số ca sẽ chạy cập nhật theo lựa chọn phạm vi. Giữ nguyên API/payload; Docker kiểm bằng plan thật 1 ca và hủy form trước khi submit.
- Thêm kiểm kê route/module trong `UI_REFACTOR_PROGRESS.md`, bao gồm màn hình condition theo permission.
- Test Case detail chuyển thành split view 30/70 với các tab Nội dung, Phiên bản, Truy vết và Rà soát. Nhận xét tiếp tục gắn trên draft theo contract hiện có; giao diện chỉ dẫn cách tạo draft để review thay vì gọi API với artifact type không được hỗ trợ.
- Reports có dashboard với KPI tiến độ/đạt/lỗi, donut kết quả và thanh ngang theo trạng thái dựa trên counts trả về; completion checklist cho biết rõ tiêu chí nào chưa được cấu hình hoặc chưa được đánh giá, không tự kết luận đạt.
- Chú giải donut của Reports được chuyển xuống dưới biểu đồ thành nhãn co giãn theo nội dung; tránh cắt tên trạng thái khi dashboard thu hẹp cạnh khu vực snapshot. Dữ liệu và cách tính không đổi.
- Reports được refactor bố cục JSX thành bộ chọn phạm vi đầu trang, header preview/hành động, dải KPI + phân bố kết quả, bảng ca, checklist hoàn tất và lịch sử snapshot riêng. Trên Docker đã xác nhận route thật với kế hoạch/ca/bản chốt, chuyển loại báo cáo cập nhật preview; không lưu hoặc export trong kiểm tra.
- Test Analysis findings đổi từ bảng cột sang thẻ có nội dung đầy đủ để đọc mô tả/đề xuất và thấy thao tác phân công, giải quyết, xác minh theo permission. Các API ghi và expected revision vẫn giữ nguyên. Docker build và route PASS; dự án kiểm tra hiện có 0 findings nên trạng thái dương chưa thể xác nhận bằng dữ liệu thật.
- Trang cá nhân được tổ chức theo Profile Settings gồm hồ sơ, bảo mật, phiên đăng nhập và thông báo; phiên dùng danh sách gọn thay cho bảng hồ sơ. Docker mở được 36 phiên thật; chỉ xem, không đổi mật khẩu, thu hồi phiên hay lưu preference.
- Các form xác thực dùng chung điều hướng cuối form, giúp quay lại bước nhập email/đăng nhập từ trang xác minh mã và thoát về đăng nhập từ trang đặt mật khẩu khi token còn hợp lệ. API xác thực và validation không đổi.
- Trang chủ và Điều khoản dùng chung header/footer công khai; đồng bộ logo, chiều cao thanh điều hướng, nền/border và vị trí liên kết. Điều khoản giữ mục lục bên cạnh nội dung và có footer điều hướng. Không thêm tagline hay sửa nội dung pháp lý.
- Cài đặt thông báo dự án đổi sang bố cục 2 cột cân bằng: theo dõi và tùy chọn cá nhân đặt cạnh nhau, quy tắc dự án có toàn bề ngang. Các trường không còn phải đoán theo placeholder; giờ yên lặng, sự kiện và ngưỡng leo thang có nhãn/hướng dẫn trực tiếp. API, quyền và payload giữ nguyên.
- Kho tài liệu nguồn đang được router sử dụng có tìm đa trường, lọc trạng thái và chuyển List/Grid. List giữ đầy đủ thao tác quản lý hiện có; Grid cung cấp thẻ đọc nhanh và mở reader. Luồng tải lên tiếp tục dùng import flow hiện tại.
- Notifications có tìm theo nội dung, lọc loại thông báo hiện có và empty state phân biệt không có dữ liệu với không có kết quả. `DOCUMENT_UPDATE` ưu tiên title/body gốc để không làm mất ngữ cảnh.
- Khung auth dùng chung được tổ chức lại cho đăng nhập, khôi phục mật khẩu và xác minh: phần đầu trang gọn, tiêu đề theo thang trang, card hẹp hơn, đường phân tách nội dung/footer, bỏ bóng lớn và thêm focus ring dễ nhận biết cho liên kết. Không thêm nội dung tagline hoặc đổi auth flow.
- Form Tạo dự án chia thành hai nhóm nghiệp vụ: thông tin cơ bản và thời gian dự kiến. Giữ toàn bộ trường, quyền owner, validation ngày và payload hiện có; lịch vẫn không bắt buộc.
- Tổng kết chu kỳ kiểm thử nhóm ba chỉ số run/ca/lỗi còn mở, đồng thời thêm phân bố trạng thái ca gần nhất bằng progress bar theo dữ liệu từ `latest_case_statuses`. Từng trạng thái chỉ hiện khi có count dương; chu kỳ không có kết quả nhận empty state rõ. Không thay đổi API, công thức nghiệp vụ, hay hành vi đóng/chuyển tiếp.
- Cycle detail hiện mở bằng dải ba metric, sau đó là kế hoạch dạng thẻ và phân bố kết quả độc lập; dữ liệu 0 được giữ đúng như response, không tự tạo số tiến độ. Test Run list chuyển từ hàng dọc sang grid thẻ responsive, đưa status/progress lên trước, hiển thị trạng thái không có phạm vi khi API thiếu danh sách ca, và đặt CTA mở/thực thi ở cuối thẻ. Không thay bộ lọc, phân trang, permission hay route.
- Form tạo lỗi chuyển sang drawer chia theo thông tin/phân loại, ngữ cảnh release/build/môi trường, tái hiện, kết quả và bằng chứng; footer lưu/hủy cố định, nhóm ngữ cảnh phụ thu gọn. Bổ sung label locale cho option mức độ/ưu tiên để không còn lựa chọn trống. Permission và payload không đổi.
- Knowledge đổi kết quả tìm kiếm từ bảng rộng thành thẻ chứa loại, trạng thái, mức chính thức, nguồn (khi response có) và đoạn trích; thư viện tài liệu tham chiếu có switch Thẻ/Danh sách để phù hợp cả duyệt nguồn lẫn quản lý. Giữ nguyên query/service/filter và quyền.
- Form tạo Test Case tách trường thành các phần thông tin ca, steps thủ công (thao tác/dữ liệu/kết quả), BDD, liên kết Requirement và metadata mở rộng. Nội dung chi tiết được mở trong vùng mở rộng; toàn bộ field, required rule, requirement/AC/condition linkage và payload được giữ nguyên.
- Chi tiết Test Plan bổ sung metadata ở phần đầu (mã, trạng thái, người phụ trách, chu kỳ, lịch dự kiến) để người đọc xác định ngữ cảnh ngay khi mở; trạng thái lưu, quyền, API và form nhóm hiện có được giữ nguyên.
- Action dialog dùng chung cho workspace được tổ chức thành header, vùng trường cuộn độc lập và footer thao tác cố định trong khung giới hạn chiều cao màn hình; giữ nguyên promise, validation, xử lý lỗi, Escape, focus trap và submit. Điều này áp dụng cho các luồng archive, chuyển trạng thái, phân công và thao tác xác nhận khác đang dùng `useActionDialog`.
- Dashboard mục “Cần xử lý” tận dụng các số liệu đã có trong response analytics: yêu cầu chưa phê duyệt (tổng không obsolete trừ baseline), đề xuất bảo trì đang chờ, impact job đang chờ/đang chạy, ca cần cập nhật, lỗi mở và run chưa hoàn thành. Liên kết chỉ hiện khi quyền tương ứng cho phép; empty state xét đủ các mục mới. Không đổi API hoặc công thức backend.
- Đóng Test Cycle có bước xác nhận tách riêng trước khi gửi mutation. Mô tả xác nhận nêu chu kỳ và số ca sẽ chuyển tiếp (nếu có); payload đóng chu kỳ, ghi chú tùy chọn, lý do bắt buộc cho từng ca được chọn và guard số run đang mở được giữ nguyên.
- Test Plan detail tách khỏi editor: chế độ đọc hiển thị theo Document Workspace với mục tiêu, Requirement/case/suite trong phạm vi, ngoài phạm vi, loại/cấp kiểm thử, môi trường, entry/exit criteria; nhân sự/lịch và rủi ro nằm trong nhóm thu gọn. Create/edit tiếp tục dùng editor hiện có, không đổi validation hay payload; ngày dùng locale/timezone từ project/user.
- Luồng kiểm thử sau Requirement được quan sát tiếp trên Docker: Test Plan 3 mục, Test Case split view 3 ca, Test Run 1 run với 0/1 ca, Defect empty state từ dữ liệu thật và Report 1 ca chưa chạy. Report donut có nhãn “Chưa chạy 1” không bị cắt sau khi refactor bố cục chú giải.

## Bảo toàn

Không chỉnh sửa backend, API contract, database, routing, permission guard hay quy tắc nghiệp vụ. Các route cũ tiếp tục xử lý bởi redirect hiện hữu. Cấu trúc sidebar và permission visibility được giữ nguyên theo prompt; phần thêm nhóm menu trong batch trước đã được hoàn nguyên. Các trang Release, AI Activity và Test Analysis vẫn được refactor trên route/CTA sẵn có.

## Xác minh

- `docker compose config --quiet`: PASS.
- Docker Compose đang chạy; các container được liệt kê đều healthy trước build.
- `docker compose config --quiet`: PASS; các service hiện liệt kê đều healthy.
- Docker frontend build chạy `format:check`, `lint` và `next build`: PASS cho batch Project, Requirement, Defect Board/List, Settings Navigation và Test Run list.
- Docker frontend build mới nhất sau Execution workspace, nhãn ma trận quyền và chuẩn hóa mã AC/BR: `format:check`, ESLint (`--max-warnings=0`) và Next production build PASS; frontend đã recreate và healthcheck healthy.
- Frontend container đã được recreate riêng, status healthy; không đụng volume/database.
- Docker build sau stacked distribution ở Execution, localized Cycle và Drawer quản trị tài khoản: `format:check`, ESLint không warning, Next production build PASS; frontend recreated và healthy.
- Docker build gần nhất sau chỉnh sửa Knowledge, Test Analysis, AI Activity và Releases: PASS; format check, lint và Next production build đều PASS.
- Frontend container sau build: healthy. Đã kiểm tra tuyến Dự án → Tổng quan → Requirement trên Docker; tiếp tục kiểm tra Releases (`/ban-phat-hanh`), Test Analysis, Knowledge và AI Review. Không ghi dữ liệu.
- Browser session hiện có mở được dữ liệu dự án E2E. Đã xem Projects, Dashboard, Requirements list/form và Test Plan list/form ở chế độ chỉ đọc. Không lưu hoặc thay đổi dữ liệu.
- Rà tiếp Home, Requirement detail/history/review tab/create form/options, Test Plan detail và Test Run detail trên cùng dữ liệu. Không tạo nháp, nhận xét, phân công, ghi kết quả hoặc export.
- Rà Test Case list/detail/create form và modal tạo Test Run; tìm kiếm local trên Test Run lọc về đúng một bản ghi khớp rồi được xóa. Không chạy AI hoặc submit form.
- Rà project settings tabs Môi trường, Thành viên và Thông báo; xác nhận route legacy `/thay-doi` chuyển về `/yeu-cau`.
- Rà login, khôi phục mật khẩu, xác minh mã/email và 404. Không nhập hoặc gửi email, mã hay mật khẩu. `/dat-lai-mat-khau` thiếu token chuyển về recovery; không tìm thấy route `/dang-ky` trong app router, giữ nguyên.
- Sau build frontend mới, đăng nhập hiển thị đúng khung auth cập nhật trên Docker. Không gửi credential. Điều hướng browser quay về qua Dự án → mở Tổng quan dự án → Yêu cầu.
- Sau build Docker cho form tạo dự án, mở modal và cuộn/focus tới ngày kết thúc: trường lịch hiển thị đầy đủ phía trên sticky footer. Không submit form. Quay lại Requirement qua Dự án → Tổng quan → Yêu cầu.
- Sau build Docker cho Test Cycle, kiểm tra hai chu kỳ QA thật: một chu kỳ có kế hoạch nháp nhưng chưa có case/run, một chu kỳ chưa có kế hoạch. Cả hai hiện thông báo không có kết quả để phân bố; không đóng chu kỳ hoặc ghi dữ liệu. Dữ liệu trong môi trường hiện không có sample để xác minh các thanh có count > 0.
- Batch Test Run/Cycle gần nhất: Docker `format:check`, ESLint (`--max-warnings=0`) và Next production build PASS; frontend recreate, healthcheck `running healthy`. Browser trên dự án thật xác nhận danh sách run 0/1 ca với CTA “Tiếp tục thực thi”, và cycle detail 0 run/0 ca/0 lỗi mở với trạng thái empty phân bố; không ghi/chỉnh dữ liệu.
- Drawer tạo lỗi trên Docker đã mở với dữ liệu thật; nhóm trường, dropdown severity/priority, khu vực context thu gọn, bằng chứng và footer đều hiện đúng. Đóng bằng Hủy, không tạo defect. Dự án này chưa cấu hình severity/priority scale nên danh sách option trống; code đã bổ sung nhãn `valueLabel`, nhưng chưa thể kiểm tra bằng dữ liệu hiển thị. Docker `format:check`, ESLint và Next production build PASS; container sau recreate `running healthy`.
- Knowledge build kế tiếp: `format:check`, ESLint (`--max-warnings=0`), Next production build PASS; frontend `running healthy`. Docker browser xác nhận thư viện 1 nguồn chuyển Thẻ/Danh sách; tìm `unique project key` trả 5 card với trích đoạn thật. Không ghi dữ liệu.
- Sau build Docker cho form Test Case, mở danh sách có 8 ca, mở form, xem steps và liên kết Requirement rồi chuyển local select từ MANUAL sang BDD. 5 trường BDD bắt buộc xuất hiện; hủy form không lưu.
- Đọc log service AI: `/san-sang` và list activity trả 200, endpoint capability trả 403. Refactor `AIRunPanel` để 403 capability riêng được diễn giải thành trạng thái không có thao tác AI khả dụng; các lỗi khác vẫn báo lỗi. Đã xác minh trên AI Review và Dashboard sau build.
- Kiểm tra sau batch mới trên project QA có dữ liệu: Releases hiển thị 1 bản đã đóng; Knowledge có `srs-login-e2e.md` đã lập chỉ mục; tìm kiếm nội bộ với truy vấn không khớp trả 0/1 và hiện thao tác xóa lọc. AI Review hiển thị các lượt xử lý tài liệu lịch sử; truy vấn không khớp hiện trạng thái rỗng và xóa lọc. Khả năng tạo lượt AI vẫn bị ẩn theo capability. Test Analysis mở đúng route; project E2E khác chưa có điều kiện kiểm thử. Không tạo hoặc sửa dữ liệu.
- `docker compose ps`: frontend và các service được Compose liệt kê đều healthy; frontend log báo Next.js Ready.
- Đã xem form Test Plan tại viewport mặc định hẹp, 1280×800; kiểm tra thêm 1024/1920 nhưng ảnh browser bị crop, không tính là xác minh breakpoint.
- Dashboard mới được kiểm tra lại trên image Docker tại 1280×800; menu chuyển sang mobile navigation ở viewport hẹp. Ảnh browser connector tại 1024/1440/1920/390px bị crop hoặc scale không ổn định, nên không kết luận toàn bộ responsive đã nghiệm thu.
- Docker browser check mới: mở từ Dự án → Tổng quan → Requirement, xác nhận nguồn tài liệu thật mở được; Board hiển thị lane rỗng ở project không có defect, và card DEF-0001 trong project E2E đưa về đúng list item đã lọc. Chuyển nhóm Cài đặt sang Thành viên không thực hiện thao tác ghi.
- Test Run list trên Docker hiển thị tiến độ thật 8/8 và 5/5, CTA Xem cho run đã hoàn tất; không ghi kết quả.
- Modal tạo Test Run trên Docker hiển thị kế hoạch đã duyệt với 8 ca; bật “Chỉ chạy một phần ca” hiện danh sách TC-0001–TC-0008 cùng tiêu đề thật. Hủy modal, không tạo run hoặc ghi dữ liệu; quay lại Requirement bằng luồng Dự án → Tổng quan → Yêu cầu.
- Execution workspace trên Docker hiển thị 8 ca chạy ở panel trái, ca đang chọn cùng kết quả/steps/evidence ở panel phải; thao tác chỉ đọc.
- Sau cập nhật stacked status, run thật trên Docker hiển thị 8/8 và “Đạt 8”; legend tính từ kết quả API. Không ghi kết quả và browser trả về Requirement.
- Quản lý tài khoản trên Docker giữ 5 cột; chi tiết tài khoản thật mở ở Drawer bên phải kèm các thao tác hiện có và bảng thành viên dự án. Chỉ xem, không thay đổi hồ sơ hoặc permission.
- Sau bổ sung stacked result distribution, Docker cho thấy run thật 8/8 và Đạt 8 ở thanh phân bố, bên cạnh danh sách ca và chi tiết ca. Không ghi dữ liệu; quay lại Requirement theo luồng Dự án → Tổng quan → Yêu cầu.
- Ma trận quyền trên Docker hiển thị 292/292 quyền với nhãn tiếng Việt cho các nhóm AI, tài liệu API, phân tích, testcase, giám sát kiểm thử và báo cáo; checkbox không đổi và không bấm Lưu phân quyền.
- Docker build sau ActionDialog: Prettier check, ESLint không warning và Next production build PASS; frontend container healthy sau recreate. Mở hộp thoại xác nhận lưu trữ dự án, kiểm tra trường lý do và nút thao tác cố định; Hủy trước khi ghi, sau đó quay lại Dự án → Tổng quan → Yêu cầu.
- Docker build sau Dashboard action items: format check, ESLint không warning và Next production build PASS; container healthy sau recreate. Browser cho dự án đang dùng hiển thị 1 run chưa hoàn thành và liên kết tới đúng `/lan-chay-kiem-thu`; các số Requirement/coverage khớp dữ liệu thật. Môi trường đó không có proposal hoặc impact job chờ xử lý nên không xác nhận nhánh hiển thị dương; không tạo dữ liệu.
- Docker build sau xác nhận đóng Test Cycle: format check, ESLint không warning, Next production build PASS; container recreated. Browser ở chu kỳ thật xác nhận modal có tên chu kỳ, thông tin lưu lịch sử, Hủy và Đóng chu kỳ; đã hủy để bảo toàn dữ liệu.
- Docker build sau Test Plan detail Document Workspace: format check, ESLint không warning, Next production build PASS; container healthy sau recreate. Browser ở plan đã duyệt có dữ liệu thật xác nhận Objective, Requirement scope, type/level, environment và entry/exit criteria render như nội dung đọc; viewport screenshot không có input disabled ở nội dung chính. Không tạo run hoặc sửa plan.
- Docker build sau khi hoàn nguyên phần mở rộng sidebar: format check, ESLint không warning và Next production build PASS; frontend được recreate để chạy đúng cấu trúc menu gốc. `git diff --check` PASS.
- Requirement trên Docker hiển thị AC theo thứ tự mã; tiền tố AC/BR lặp trong nội dung được loại ở phần trình bày, còn dữ liệu nội dung gốc không bị cập nhật.
- Defect Board và List trên Docker mở cùng drawer chi tiết cho `DEF-0001` với dữ liệu thật; xác nhận trạng thái “Chưa gán”, bước tái hiện, expected/actual và kết quả liên quan. Không thực hiện chuyển trạng thái, phân công hoặc cập nhật truy vết.
- Test Case `TC-0001` trên Docker xác nhận các tab Nội dung, Phiên bản v1, Truy vết `REQ-0002` và Rà soát; Reports trên dữ liệu thật xác nhận 1/1 ca đã chạy, Pass 100% và một defect mở. Không tạo draft, comment, snapshot hoặc export.
- Kho tài liệu trên Docker hiển thị tài liệu thật trong List/Grid; tìm truy vấn không khớp trả 0/1, trở về list giữ nút phân loại, lập chỉ mục, AI, quyền, tải xuống và lưu trữ. Không upload hoặc sửa hồ sơ.
- Notifications trên Docker xác nhận số liệu tài khoản 0/0, trạng thái không có thông báo, tìm không khớp và nút mark-all disabled; không có dữ liệu để kiểm tra item actions.
- Cài đặt Thông báo trên Docker: ba nhóm theo dõi/tùy chọn cá nhân/quy tắc dự án tải độc lập; form khóa đến khi cấu hình tương ứng tải thành công; lưu có trạng thái; có nút tải lại. Dữ liệu của project thật tải không lỗi, không gửi thay đổi.
- Nhật ký kiểm toán trên Docker nạp 57 sự kiện thật. Bộ lọc loại dữ liệu giảm kết quả xuống 1, nút Xóa bộ lọc phục hồi 57 kết quả; giao diện ở viewport 390px không tràn ngang. Bộ lọc thời gian đã render nhưng thao tác nhập ngày qua browser automation không kích hoạt cập nhật React, nên chưa tính đã nghiệm thu lọc theo ngày.
- Quản lý tài khoản trên Docker: lọc vai trò `USER` cho 78/100 tài khoản; kết hợp trạng thái `DISABLED` còn 9/100. Table 5 cột được giữ nguyên; viewport 390px không tràn ngang. Chỉ lọc dữ liệu đang tải, không cập nhật hồ sơ/tài khoản/quyền.
- Môi trường kiểm thử trên Docker mở drawer tạo với đủ 9 trường và footer Hủy/Lưu; viewport 390px không tràn, nội dung cuộn trong drawer. Hủy form và không tạo dữ liệu.
- Docker build cho các thay đổi cài đặt thông báo, audit, tài khoản và drawer môi trường: `format:check`, ESLint (`--max-warnings=0`) và Next production build PASS; frontend được recreate. `git diff --check` PASS.
- Docker build sau chỉnh bố cục chú giải donut: format check, ESLint (`--max-warnings=0`) và Next production build PASS; frontend container healthy sau recreate; browser xác nhận donut và tên trạng thái render đầy đủ theo dữ liệu báo cáo thật. `git diff --check` PASS.
- Docker build sau chỉnh ngữ nghĩa editor read-only: format check, ESLint (`--max-warnings=0`) và Next production build PASS; Requirement phiên bản BASELINED render như nội dung tài liệu, tree không còn field nhập. Draft và permission guard không đổi. Frontend healthy sau recreate.
- Test Plan trên Docker: đổi giữa Theo chu kỳ/Thẻ/Danh sách, xác nhận 3 kế hoạch thật chia đúng thành 1 kế hoạch trong chu kỳ và 2 không thuộc chu kỳ. Không sửa kế hoạch.
- Test Case trên Docker mặc định vào Split View, nhóm 3 ca theo Requirement thật; Danh sách đầy đủ mở lại bảng có chọn nhiều, Mở Split View quay về chi tiết. Không tạo/sửa ca.
- Requirement trên Docker mở từ Dự án → Tổng quan → Yêu cầu: điểm vào tự mở Split View với Requirement đầu tiên; Danh sách đầy đủ/Mở Split View chuyển qua lại. Nội dung, AC, BR và nguồn thật hiển thị; không thay đổi dữ liệu.
- Execution Workspace trên Docker thêm bộ lọc theo kết quả; run thật 8/8 xác nhận Đã có kết quả (8), thứ tự ca gốc và ca đang chọn vẫn hiển thị. Không ghi kết quả.
- Defect Kanban trên Docker hiển thị đủ 9 trạng thái nghiệp vụ trong dự án QA rỗng; phần thẻ được nối tới dữ liệu người xử lý/retest hiện có. Không tạo defect để minh họa.
- Docker build sau các cập nhật Test Plan/Test Case/Defect/Execution/Requirement: Prettier format check, ESLint không warning, Next production build PASS; frontend được recreate. `git diff --check` PASS.
- Kiểm tra chức năng menu mobile ở viewport 390px: mở drawer, danh sách điều hướng xuất hiện, nút đóng nhận focus; đóng drawer đưa focus về nút mở.
- Không có ảnh trước/sau được lưu thành file artifact.

AI Review chỉ có quyền đọc activity ở project kiểm tra: capability endpoint trả 403. Sau khi sửa, trang hiển thị đúng empty state theo quyền, không chạy tác vụ và không đổi permission/API/backend.

- Sau image Docker cập nhật Defect và Report, đã kiểm tra tuyến còn lại: Test Plan, Test Case split view, Test Run, Defect và Báo cáo. Empty state Defect xác nhận riêng cả dự án rỗng và bộ lọc không có kết quả; donut Report giữ nhãn trạng thái đầy đủ. `git diff --check` PASS; frontend Docker healthy.

## Đối chiếu form yêu cầu

Form không yêu cầu giới hạn refactor ở vài dòng. Ngược lại, form yêu cầu rà các màn hình ACTIVE/CONDITIONAL và luồng liên quan, không chỉ sửa một số trang đại diện. Vì vậy checklist đánh dấu các cụm chưa kiểm chứng là TODO/BLOCKED/PARTIAL, không tuyên bố hoàn tất hệ thống.

## Phạm vi còn lại

Đây là các batch giao diện thực tế đã mở rộng sang Projects → Dashboard → Requirements → Test Plan/Cycle → Test Run → Defect → Releases → AI Activity → Test Analysis → Knowledge → Settings, chưa hoàn tất toàn bộ scope của form. Các màn hình account/auth/public/notification và các trạng thái điều kiện theo permission vẫn cần đối chiếu tiếp; chưa nghiệm thu mọi luồng ghi dữ liệu. Không kết luận toàn hệ thống đã hoàn tất.

## Diễn giải yêu cầu gốc

Pasted form không yêu cầu chỉ sửa vài dòng. Form ghi rõ không chỉ đổi CSS và không chỉ sửa một số trang đại diện. Batch hiện tại đã refactor layout và thao tác ở nhiều cụm trang; phạm vi toàn hệ thống vẫn chưa đạt nghiệm thu vì checklist còn PARTIAL/TODO/BLOCKED.

## Batch chi tiết Test Case

Màn chi tiết ca kiểm thử được tổ chức lại theo công việc thực thi: bảng bước kiểm thử là nội dung chính, metadata là sidebar, mô tả và luồng chính gom thành một nhóm. Điều kiện, luồng thay thế/ngoại lệ, kỹ thuật, thẻ và liên kết đặt trong disclosure để vẫn giữ đủ dữ liệu nhưng không tạo cột trống lớn. Không đổi API, quyền, dữ liệu hoặc nghiệp vụ. Xác nhận trên Docker bằng dữ liệu thật TC-0003; không ghi dữ liệu. `docker compose build frontend` chạy thành công với `format:check`, ESLint và Next production build; container đã recreate.

## Batch Workspace thực thi Test Run

Header trạng thái được refactor khỏi hàng flex dùng chung với mã lần chạy: trạng thái/link kế hoạch, mã có xuống dòng, metadata môi trường và khối tiến độ/phân bố kết quả có vùng riêng theo breakpoint. Trên run thật `E2E-UX-20261127: execution` (0/1 ca), viewport hẹp không còn ép progress thành cột chữ. Không lưu kết quả hoặc đổi trạng thái run. Docker build mới qua `format:check`, ESLint, Next production build và frontend được recreate.

## Batch form Test Plan

Form dài có sticky footer để Hủy/Lưu tiếp cận được ở cuối biểu mẫu; chế độ tạo có thêm Lưu nháp. Thông báo lỗi của form đặt cạnh nhóm hành động nên nhìn thấy khi người dùng đang ở cuối. Các nút gọi cùng form và submitter value sẵn có, không đổi payload hoặc quy tắc validation. Browser xác nhận trên form chỉnh sửa plan thật sau khi cuộn tới cuối; không lưu dữ liệu. Docker build qua `format:check`, ESLint và Next production build.

## Batch form và route tạo Test Case

Sửa điều kiện tự mở ca đầu tiên để bỏ qua route `tao-moi`; trước sửa, trang tự chuyển tới TC-0003 sau khi tải danh sách. Form tạo được thêm sticky footer với Hủy/quay lại kế hoạch, Lưu nháp, Lưu ca và hiển thị lỗi validation trong footer. Docker/browser xác nhận route ở lại sau khi load, footer hiện ở cuối; bấm Lưu ca khi tên rỗng bị native validation chặn và Lưu nháp hiển thị lỗi tên theo validation sẵn có. Không gửi request tạo hoặc thay đổi dữ liệu.

## Batch Reader tài liệu nguồn

Reader đổi thứ tự responsive để văn bản/tệp là bề mặt chính ngay trên màn hẹp; desktop giữ vùng đọc rộng ở cột chính, Trợ lý tài liệu và metadata ở sidebar bên phải. Nút tóm tắt chuyển vào vùng trợ lý; kết quả dài cuộn độc lập. Trạng thái xử lý, tiến độ theo tài liệu/chunk, hủy, retry, tình trạng chưa đầy đủ và link về tài liệu nguồn được giữ. Không đổi API, quyền hay dữ liệu. Docker build qua `format:check`, ESLint và Next production build; frontend healthy. Browser xác nhận trên tài liệu SRS thật ở desktop và viewport 390px, nội dung đọc đứng trước trợ lý trên mobile, không tràn ngang. Không chạy AI, tải bản gốc hoặc ghi dữ liệu.

## Batch sửa CTA nhập tài liệu từ Requirement detail

Nút `Nhập tài liệu` đã hiển thị trong header ở cả detail/split view lẫn list, nhưng modal chỉ được render bên trong nhánh list. Đưa modal dùng chung ra ngoài nhánh hiển thị để CTA mở được từ detail và list; giữ nguyên điều kiện quyền, trạng thái xử lý, upload handler và payload. Docker build qua format, ESLint và production build; browser trên route Requirement detail xác nhận modal mở, Hủy đóng và quay lại trang. Không chọn tệp hoặc gửi dữ liệu.

## QA các tab Requirement trên dữ liệu dự án

Mở Requirement thật trong Docker và chuyển lần lượt Lịch sử phiên bản, Truy vết, Ảnh hưởng đến kiểm thử. Lịch sử có một phiên bản nên các trường so sánh để trống rõ ràng; ma trận Truy vết hiển thị 4 liên kết đã xác nhận và từng AC chưa liên kết; Ảnh hưởng hiển thị empty state do chưa có job. Ở viewport 390px, thanh tab có điều khiển trái/phải và không tràn trang. Chỉ đọc, không thay đổi trạng thái hay dữ liệu.

## Batch danh sách Bộ kiểm thử và sửa route

Route canonical `/ca-kiem-thu/bo-kiem-thu` trước đây bị điều kiện redirect legacy chuyển nhầm về chi tiết ca đầu tiên, làm màn danh sách suite không thể mở. Bỏ điều kiện redirect chỉ áp dụng cho nested route này; đường dẫn legacy `/bo-kiem-thu` vẫn giữ redirect cũ. Refactor danh sách khỏi lưới card sang các hàng quản lý responsive; thêm số lượng tổng/đang sử dụng/đã lưu trữ lấy từ bộ dữ liệu hiện tải, thanh tìm kiếm và lọc trạng thái có đếm cùng empty state khôi phục bộ lọc. Giữ API, quyền cập nhật/lưu trữ và editor modal. Docker production build qua Prettier `format:check`, ESLint `--max-warnings=0`, Next build; container frontend được recreate và healthy. Browser xác nhận route canonical mở đúng danh sách, form tạo mở/đóng được, lọc đã lưu trữ trả empty state theo dữ liệu thật rồi xóa lọc phục hồi một suite. Không ghi dữ liệu.

## Batch form Test Plan theo progressive disclosure

Form tạo/sửa kế hoạch được tổ chức lại theo thứ tự: tên, mục tiêu, requirement và phạm vi testcase luôn hiển thị; ngoài phạm vi, phân loại, môi trường, điều kiện, nhân sự/lịch, chu kỳ và rủi ro chuyển thành disclosure tùy chọn. Nhãn nhóm hiển thị giá trị/tóm tắt đã lưu; khi mở kế hoạch có dữ liệu ở nhóm tùy chọn, nhóm đó được mở sẵn. Trường Chu kỳ và luồng chọn/tạo chu kỳ cùng danh sách ca chuyển tiếp được đặt trong đúng nhóm để rút gọn phần đầu nhưng vẫn giữ nghiệp vụ. Rủi ro tự mở khi validation báo lỗi; trường tên chu kỳ mới không thể bị ẩn khi còn bắt buộc. Không thay schema, API payload, quy tắc validation hoặc quyền.

Docker production build qua Prettier `format:check`, ESLint `--max-warnings=0` và Next production build; frontend được recreate. Browser từ Dashboard → Kế hoạch xác nhận create form ưu tiên các trường cốt lõi và đóng các nhóm tùy chọn; mở nhóm Nhân sự/Chu kỳ/Thời gian thấy danh sách chu kỳ thật, thành viên, thời gian và nút tạo chu kỳ. Mở draft thật xác nhận nhóm có chu kỳ mở sẵn và tên/mục tiêu/requirement/bộ test còn nguyên; hủy cả hai form, không lưu dữ liệu. Container frontend healthy; `git diff --check` sạch.

## Batch trạng thái tải dùng chung cho Authentication

Tạo `AuthSubmitButton` dùng cho đăng nhập, khôi phục mật khẩu, nhập mã khôi phục, đặt lại mật khẩu và xác minh email. Nút có spinner, nhãn trạng thái riêng theo hành động, tự khóa khi đang gửi, `aria-busy` và thông báo loading cho screen reader; các hook và hành vi submit hiện có giữ nguyên. AuthLoading chuyển sang dùng AuthFrame/logo/spacing/design token chung, bỏ nền và bóng hardcode.

Docker production build qua `format:check`, ESLint `--max-warnings=0` và Next build; frontend được recreate. Browser xác nhận trang đăng nhập, thao tác bật/tắt hiện mật khẩu, Khôi phục mật khẩu, Xác minh mã, trang reset thiếu token và fallback AuthLoading. Không nhập email/mật khẩu/mã/token hoặc gửi form. Submit/loading trực tiếp, lỗi server và trạng thái thành công còn chưa được xác minh.

## Batch hai chế độ xem danh sách Test Run

Danh sách lần chạy hiện cho phép đổi giữa thẻ và danh sách gọn để phù hợp với cả việc theo dõi từng run lẫn rà nhiều run. Dạng gọn xếp tên/mã, trạng thái, tiến độ theo số ca đã ghi nhận, kế hoạch, môi trường và người thực hiện (chỉ lấy từ dữ liệu run/membership đang có), thời điểm cập nhật và nút tiếp tục/mở thành hàng; ở viewport hẹp các vùng tự xếp dọc để không tràn ngang. Bộ lọc, phân trang, quyền, API và hành vi mở run không đổi. Báo cáo dùng semantic chart tokens gắn với brand/danger/warning/muted/border hiện tại thay vì mã màu rời rạc; trạng thái biểu đồ vẫn được lấy từ kết quả API.

Docker production build qua `format:check`, ESLint (`--max-warnings=0`) và Next production build; frontend healthy sau recreate. Browser xác nhận trên project có run thật 0/1 ca, người thực hiện, chuyển qua lại hai chế độ và giữ CTA “Tiếp tục thực thi”; không ghi dữ liệu. Trên Báo cáo, xác nhận dữ liệu 1 ca chưa chạy, biểu đồ/phân bố và bảng ca; chọn kế hoạch không có phạm vi hiển thị số liệu rỗng, sau đó khôi phục kế hoạch có dữ liệu. Không lưu snapshot hoặc export. `git diff --check` sạch.

## Batch icon định dạng File Explorer

Explorer nguồn tài liệu giữ nguyên list/grid, bộ lọc, tìm kiếm, chọn hàng loạt, quyền và thao tác hiện có. Bổ sung biểu tượng theo trường định dạng/tên tệp ở cả hai chế độ: văn bản/PDF, bảng tính, ảnh, mã/spec và icon tổng quát cho định dạng khác. Không thêm metadata giả; icon chỉ phân loại chuỗi format/filename mà API đã trả. Docker production build qua `format:check`, ESLint (`--max-warnings=0`) và Next build; container healthy. Browser trên một tài liệu `.txt` thật xác nhận icon ở List/Grid, trạng thái xử lý và thao tác theo quyền giữ nguyên; không tải xuống, đổi quyền hoặc chạy AI.

## Batch ma trận phân quyền quản trị

Ma trận permission giữ nguyên 292 quyền từ API, nhóm resource, ba cột vai trò và checkbox có thể sửa theo cơ chế hiện tại. Đưa table vào vùng cuộn giới hạn chiều cao, ghim hàng tên role và cột permission để người dùng luôn biết đang đổi quyền nào; bảng có chiều rộng tối thiểu để nhãn không ép checkbox trên màn hẹp. Nút lưu nằm ngay sau vùng ma trận.

Docker production build qua `format:check`, ESLint (`--max-warnings=0`) và Next build; frontend healthy. Browser trên `/van-hanh` xác nhận 292 quyền, header giữ nguyên khi cuộn dọc, cột tên quyền giữ nguyên khi cuộn ngang và nút “Lưu phân quyền” luôn ở dưới vùng. Không thay checkbox hoặc lưu cấu hình.

## Batch cài đặt thông báo cá nhân

Tổ chức lại ba tùy chọn API thành các khối theo sự kiện với biểu tượng, mô tả, trạng thái bật/tắt và switch có nhãn trợ năng; thêm tổng số tùy chọn đang bật và đặt trạng thái lưu cạnh vùng thao tác. Giữ nguyên ba khóa cấu hình, thao tác lưu/tải lại, payload và lỗi API. Docker production build qua `format:check`, ESLint (`--max-warnings=0`) và Next production build; container healthy. Browser xác nhận ba tùy chọn thật hiển thị và bố cục hẹp xếp dọc; không đổi cấu hình.

## Batch điều hướng tài khoản responsive

Giữ nguyên bốn section tài khoản, chuyển điều hướng thành thanh tab cuộn ngang trên màn hẹp và sidebar ghim trên màn rộng. Trạng thái hiện tại vẫn được công bố bằng `aria-current`; không đổi URL, section, dữ liệu hay hành vi lưu.

## Rà soát lại luồng dự án → tổng quan → Requirement

Trên frontend Docker, mở `/du-an`, chọn dự án `E2E26NEW`, xác nhận Dashboard có 1 Requirement, 3 Test Case, 1 run chưa hoàn thành và đường dẫn “Mở yêu cầu”. Từ Dashboard mở Requirement: split view tự chọn `REQ-PROJECT-CREATE-01` và hiển thị nội dung, 4 AC, BR, trạng thái chuẩn và tài liệu nguồn thật. Chuyển sang Danh sách đầy đủ rồi trở lại Split View; yêu cầu đang chọn và dữ liệu liên quan được giữ. Không thay đổi dữ liệu.

Trên `/du-an`, đổi qua lại hai chế độ Lưới/Danh sách với dữ liệu API hiện có; ở viewport 650px mỗi chế độ xếp dọc và không tràn ngang. Mở form Tạo dự án xác nhận nhóm Thông tin cơ bản/Lịch dự kiến, nội dung cuộn trong modal và footer Hủy/Lưu luôn thấy; đóng form, không tạo dự án.

