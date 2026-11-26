# MASTER PROMPT — REDESIGN TOÀN BỘ UI/UX HỆ THỐNG VERIQ

## PHẦN 1. VAI TRÒ VÀ NHIỆM VỤ

Bạn hãy đóng vai đồng thời là:

- Senior UI/UX Designer.
- Product Designer chuyên thiết kế hệ thống SaaS.
- Senior Frontend Engineer.
- Chuyên gia thiết kế hệ thống quản lý kiểm thử phần mềm.
- Chuyên gia đánh giá trải nghiệm người dùng.

Nhiệm vụ của bạn là đọc, phân tích và thiết kế lại toàn bộ giao diện hệ thống Veriq.

Repository: https://github.com/MinTruqday/Veriq

Veriq là hệ thống quản lý kiểm thử phần mềm tích hợp AI. Dự án đã có mã nguồn, kiến trúc, API, phân quyền và quy trình nghiệp vụ.

Hiện tại, nhiều giao diện sử dụng bảng dữ liệu, biểu mẫu dài và các khối thông tin có cách trình bày tương tự nhau. Điều này khiến người dùng khó phân biệt mục đích của từng màn hình, mất thời gian tìm kiếm chức năng và phải thực hiện nhiều thao tác không cần thiết.

Mục tiêu là chuyển Veriq thành một hệ thống có giao diện hiện đại, trực quan, dễ hiểu, dễ thao tác và phù hợp với đặc thù quản lý kiểm thử phần mềm.

Không xây dựng một ứng dụng mới thay thế Veriq. Hãy cải tiến trực tiếp dự án hiện tại.

---

# PHẦN 2. QUY TẮC BẮT BUỘC

## 2.1. Đọc mã nguồn trước khi thực hiện

Trước khi chỉnh sửa, phải kiểm tra phiên bản hiện tại của repository và đọc các thành phần liên quan:

- Frontend.
- Backend API.
- Service xử lý nghiệp vụ.
- Schema và cấu trúc dữ liệu.
- Routing.
- Authentication.
- Authorization và permission.
- Các component dùng chung.
- Design token.
- Theme và Tailwind CSS.
- Các biểu mẫu hiện tại.
- Các trạng thái của từng đối tượng.
- API client.
- Các chức năng AI.
- Các chức năng phân tích phiên bản.
- Các bài kiểm thử frontend hiện có.

Không được chỉ đọc tên file rồi suy diễn nghiệp vụ.

Đặc biệt kiểm tra:

- frontend/features/testing/pages/
- frontend/features/testing/pages/workspace/
- frontend/features/testing/components/
- frontend/features/authentication/
- frontend/shared/
- frontend/app/
- frontend/tailwind.config.js
- frontend/package.json
- backend/testing/src/modules/
- backend/authentication/src/
- backend/ai/src/

Đường dẫn trên là cơ sở khảo sát ban đầu. Nếu cấu trúc repository đã thay đổi, phải sử dụng cấu trúc thực tế mới nhất.

## 2.2. Không thay đổi nghiệp vụ

Phạm vi chính của nhiệm vụ là UI/UX và frontend.

Không được tự ý:

- Thay đổi quy trình nghiệp vụ.
- Thay đổi cấu trúc database.
- Thay đổi API contract.
- Thay đổi quyền của người dùng.
- Thay đổi công thức tính tiến độ.
- Thay đổi công thức tính tỷ lệ kiểm thử.
- Thay đổi trạng thái nghiệp vụ.
- Thay đổi quy trình phê duyệt.
- Xóa chức năng đang hoạt động.
- Tạo dữ liệu giả để che giấu lỗi API.
- Hardcode kết quả kiểm thử.
- Hardcode số liệu báo cáo.
- Thêm chức năng AI mà backend chưa hỗ trợ.
- Khôi phục các chức năng legacy chỉ vì còn mã nguồn.
- Thay thế toàn bộ framework frontend hiện tại.

Nếu phát hiện backend thiếu dữ liệu phục vụ một thiết kế mới, hãy sử dụng dữ liệu hiện có để điều chỉnh thiết kế và ghi rõ hạn chế.

Không tự ý sửa backend để phù hợp với giao diện đề xuất.

## 2.3. Giữ nguyên phân quyền

Mọi nút, hành động và dữ liệu phải tuân theo permission hiện tại.

Ví dụ:

- Người chỉ có quyền xem không được sửa.
- Người không có quyền duyệt không được nhìn thấy nút phê duyệt.
- Người không có quyền tạo không được sử dụng nút tạo mới.
- Quyền quản trị hệ thống không tự động thay thế quyền nghiệp vụ trong dự án.
- Không được bỏ qua điều kiện chuyển trạng thái.
- Không cho phép người dùng thực hiện hành động ngoài phạm vi được giao.

Không hardcode quyền theo tên BA, QA, Tester hoặc Developer nếu hệ thống thực tế sử dụng capability hoặc role có thể cấu hình.

## 2.4. Nguyên tắc UI/UX

Giao diện phải đạt các mục tiêu:

- Nhìn vào biết màn hình dùng để làm gì.
- Biết trạng thái hiện tại của đối tượng.
- Biết thao tác tiếp theo cần thực hiện.
- Hạn chế số lần chuyển trang.
- Hạn chế mở nhiều modal lồng nhau.
- Chỉnh sửa tại chỗ khi phù hợp.
- Không hiển thị trùng lặp thông tin.
- Không hiển thị quá nhiều số liệu không có giá trị.
- Không sử dụng bảng cho mọi loại nội dung.
- Không sử dụng card cho mọi thành phần một cách máy móc.
- Không sử dụng màu sắc quá nhiều.
- Không tạo khoảng trắng dư thừa.
- Không thu nhỏ chữ quá mức để nhồi nhét nội dung.
- Ưu tiên trải nghiệm desktop cho hệ thống nghiệp vụ.

Áp dụng Progressive Disclosure: thông tin chính hiển thị trước, thông tin nâng cao chỉ xuất hiện khi người dùng cần.

---

# PHẦN 3. CÁC SẢN PHẨM THAM KHẢO

Tham khảo cách tổ chức giao diện của:

| Sản phẩm | Nội dung tham khảo |
|---|---|
| Qase | Test Case Repository, Test Run, Test Wizard |
| Testmo | Split View, tổ chức ca kiểm thử, thực thi |
| TestRail | Test Plan, Test Run, báo cáo và tiến độ |
| Jira | Quản lý lỗi, Kanban, bộ lọc |
| Linear | Danh sách công việc, thao tác nhanh, giao diện tối giản |
| Notion | Trình soạn thảo, cấu trúc tài liệu |
| Google Drive | Quản lý và xem trước tài liệu |
| NotebookLM | Quản lý nguồn tri thức |
| GitHub | Cài đặt, lịch sử phiên bản, so sánh thay đổi |

Chỉ học hỏi các nguyên tắc thiết kế và cách tổ chức thông tin.

Không sao chép toàn bộ giao diện hoặc thương hiệu của các sản phẩm khác.

Veriq phải có phong cách giao diện riêng, đồng nhất giữa tất cả các trang.

---

# PHẦN 4. XÂY DỰNG DESIGN SYSTEM

## 4.1. Màu sắc

Đọc theme và hệ thống màu sắc hiện tại của Veriq.

Ưu tiên giữ nguyên màu thương hiệu hiện tại.

Các mã màu dưới đây chỉ là định hướng nếu hệ thống chưa có design token phù hợp:

- Primary: #2563EB.
- Success: #16A34A.
- Warning: #D97706.
- Error: #DC2626.
- Neutral: #64748B.
- Background: sử dụng màu nền hiện tại hoặc màu trung tính nhẹ.
- Surface: sử dụng màu bề mặt thống nhất với theme hiện tại.

Màu xanh lá dùng cho trạng thái thành công.

Màu đỏ dùng cho lỗi hoặc trạng thái không đạt.

Màu cam dùng cho cảnh báo hoặc trạng thái cần chú ý.

Màu trung tính dùng cho trạng thái chưa thực hiện, bản nháp hoặc thông tin phụ.

Không phụ thuộc hoàn toàn vào màu sắc. Phải có nhãn hoặc biểu tượng phân biệt trạng thái.

Không tự ý đổi ý nghĩa màu của các trạng thái hiện tại.

## 4.2. Typography

- Ưu tiên font chữ hiện tại nếu hỗ trợ tiếng Việt tốt.
- Có thể cân nhắc Inter hoặc Be Vietnam Pro nếu cần.
- Tiêu đề trang: khoảng 24px.
- Tiêu đề khu vực: 16–18px.
- Nội dung thông thường: 14px.
- Metadata: 12–13px.
- Số liệu quan trọng: 24–32px.
- Không lạm dụng chữ in hoa.
- Không sử dụng quá nhiều font weight.

## 4.3. Khoảng cách và hình khối

Sử dụng spacing system thống nhất:

- 4px.
- 8px.
- 12px.
- 16px.
- 24px.
- 32px.

Card sử dụng bo góc khoảng 6–8px.

Đường viền nhẹ.

Đổ bóng nhẹ khi cần phân biệt các lớp giao diện.

Không sử dụng gradient, hiệu ứng kính hoặc animation phức tạp không phục vụ nghiệp vụ.

Không tạo card quá lớn trong khi chỉ chứa một dòng thông tin.

## 4.4. Component dùng chung

Kiểm tra các component hiện tại và tái sử dụng trước khi xây dựng component mới.

Chuẩn hóa các component tương đương:

- PageHeader.
- SectionHeader.
- SearchField.
- FilterBar.
- StatusBadge.
- PriorityBadge.
- ProgressBar.
- SegmentedProgress.
- DonutChart.
- MetricCard.
- ProjectCard.
- CollapsibleSection.
- SplitView.
- DetailDrawer.
- EmptyState.
- LoadingState.
- ErrorState.
- ConfirmDialog.
- DropdownMenu.
- Pagination.
- AvatarGroup.
- ActivityTimeline.
- VersionTimeline.
- ComparisonView.
- AttachmentList.
- PermissionAwareAction.
- ListView.
- DataTable.
- KanbanBoard.

Tên component có thể thay đổi để phù hợp với convention hiện tại.

Không tạo hai component có cùng mục đích chỉ vì chúng được sử dụng ở hai màn hình khác nhau.

Chỉ xây dựng component mới khi thực sự cần thiết.

---

# PHẦN 5. THIẾT KẾ LẠI GLOBAL LAYOUT

## 5.1. Sidebar

Giữ cấu trúc điều hướng và các route đang hoạt động của Veriq.

Tổ chức sidebar thành các nhóm:

Không gian làm việc:

- Dự án.
- Quản lý tài khoản.

Tổng quan:

- Tổng quan dự án.

Bảo đảm yêu cầu:

- Yêu cầu.

Kế hoạch kiểm thử:

- Kế hoạch kiểm thử.

Thiết kế kiểm thử:

- Ca kiểm thử.

Thực thi kiểm thử:

- Lần chạy kiểm thử.
- Lỗi.

Báo cáo:

- Báo cáo.

Tài liệu:

- Tài liệu dự án.
- Tài liệu tham chiếu.
- Cài đặt dự án.

Tài khoản:

- Tài khoản cá nhân.

Đối chiếu cấu trúc trên với navigation thực tế trước khi triển khai.

Không tự ý thêm Test Scenario, Test Analysis hoặc các module legacy vào menu chính nếu phiên bản hiện tại không hiển thị chúng.

Yêu cầu:

- Sidebar rộng khoảng 224–248px khi mở.
- Có thể thu gọn còn khoảng 64–72px.
- Khi thu gọn chỉ hiển thị icon và tooltip.
- Highlight đúng trang đang truy cập.
- Các nhóm chức năng phân biệt rõ ràng.
- Có thể thu gọn nhóm điều hướng nếu cần.
- Không hiển thị menu ngoài quyền người dùng.
- Không sử dụng nhiều màu cho icon điều hướng.

## 5.2. Header

Header nên chứa những thành phần thực sự cần thiết:

- Breadcrumb.
- Tên dự án hiện tại.
- Thông báo nếu đã có.
- Avatar người dùng.
- Menu tài khoản.
- Chức năng chuyển dự án nếu được hỗ trợ.

Không lặp lại tên trang và tên dự án ở quá nhiều vị trí.

## 5.3. Content Area

- Tận dụng chiều rộng màn hình desktop.
- Không cố định chiều rộng quá nhỏ cho trang nghiệp vụ.
- Header và vùng thao tác chính phải dễ tiếp cận.
- Bộ lọc đặt gần nội dung cần lọc.
- Các màn hình dài có thể sử dụng sticky toolbar.
- Không tạo thanh cuộn ngang ở toàn bộ ứng dụng.
- Bảng dữ liệu lớn có thể cuộn trong vùng chứa riêng.

Kiểm tra giao diện ở độ phân giải:

- 1280 × 720.
- 1440 × 900.
- 1920 × 1080.

Trên màn hình nhỏ, chuyển Split View thành chế độ danh sách và chi tiết lần lượt hoặc Drawer phù hợp.

---

# PHẦN 6. REDESIGN CHI TIẾT TỪNG TRANG

## 6.1. Trang danh sách dự án — Projects

Nguồn kiểm tra:

frontend/features/testing/pages/ProjectsPage.jsx

### Mục tiêu

Người dùng nhìn vào danh sách và biết ngay dự án nào đang thực hiện, tiến độ ra sao, dự án nào cần mở hoặc xử lý.

### Thiết kế

Sử dụng Project Card View làm chế độ mặc định nếu phù hợp với giao diện hiện tại.

Cung cấp thêm List View cho người dùng có nhiều dự án.

Thanh công cụ phía trên gồm:

- Tiêu đề Dự án.
- Nút Tạo dự án theo quyền.
- Tìm kiếm dự án.
- Bộ lọc trạng thái.
- Bộ lọc thời gian nếu hiện có.
- Nút chuyển Grid View/List View.

Mỗi Project Card hiển thị:

- Icon hoặc ký hiệu dự án.
- Mã dự án.
- Tên dự án.
- Trạng thái.
- Tiến độ dự án.
- Thanh tiến độ.
- Thành viên nếu dữ liệu hiện có.
- Thời gian hoặc hoạt động cập nhật gần nhất.
- Menu thao tác theo quyền.

Bố cục minh họa:

    ┌─────────────────────────────────┐
    │ [LIB]  Hệ thống thư viện số   ⋯  │
    │        Dự án đang thực hiện     │
    │                                 │
    │ Tiến độ                    75%  │
    │ ███████████████░░░░░            │
    │                                 │
    │ 5 thành viên     Cập nhật gần đây│
    └─────────────────────────────────┘

Hiển thị khoảng 3–4 card mỗi hàng trên màn hình desktop lớn, tùy chiều rộng thực tế.

### Lời mời dự án

Nếu có lời mời tham gia, hiển thị một khu vực riêng phía trên danh sách.

Cho phép chấp nhận hoặc từ chối theo logic hiện tại.

Không để lời mời chiếm diện tích khi không có dữ liệu.

### Tương tác

- Click vào card để mở dự án.
- Menu ba chấm chứa hành động phù hợp.
- Không đặt quá nhiều nút bên trong card.
- Giữ chức năng lưu trữ và khôi phục nếu hiện có.
- Không thay đổi cách tính phần trăm tiến độ.

---

## 6.2. Trang Tổng quan — Dashboard

Nguồn kiểm tra:

frontend/features/testing/pages/workspace/DashboardPage.jsx

### Mục tiêu

Đây là màn hình quan trọng nhất của dự án.

Trong khoảng 5–10 giây, người dùng phải hiểu được:

- Dự án đang tiến triển thế nào.
- Yêu cầu đã được xử lý đến đâu.
- Tình hình ca kiểm thử.
- Kết quả thực thi.
- Lỗi đang mở.
- Công việc cần xử lý.
- Thay đổi nào đang ảnh hưởng đến kiểm thử.

Không biến Dashboard thành nơi tập hợp tất cả các bảng dữ liệu của hệ thống.

### Bố cục tổng thể

    ┌───────────────────────────────────────────────┐
    │ TỔNG QUAN DỰ ÁN                              │
    │ Tên dự án                      Trạng thái     │
    ├───────────────────────────────────────────────┤
    │ TIẾN TRÌNH KIỂM THỬ                           │
    │ Yêu cầu ─ Kế hoạch ─ Thiết kế ─ Thực thi ─ BC  │
    ├──────────────┬───────────────┬────────────────┤
    │ Yêu cầu      │ Ca kiểm thử   │ Lỗi đang mở    │
    │ Donut chart  │ Progress      │ Bar chart      │
    ├──────────────┴───────────────┼────────────────┤
    │ Tình hình thực thi           │ Cần xử lý      │
    │ Biểu đồ kết quả              │ Action list    │
    ├──────────────────────────────┼────────────────┤
    │ Thay đổi gần đây             │ Lần chạy mới   │
    │ Timeline                     │ Compact card   │
    ├──────────────────────────────┴────────────────┤
    │ Thông tin dự án / thành viên                  │
    └───────────────────────────────────────────────┘

### Khu vực 1. Tiến trình kiểm thử

Giữ hoặc cải tiến thành phần tiến trình kiểm thử hiện có.

Biểu diễn các giai đoạn:

1. Yêu cầu.
2. Kế hoạch.
3. Thiết kế.
4. Thực thi.
5. Báo cáo.

Mỗi giai đoạn có:

- Tên giai đoạn.
- Trạng thái.
- Tiến độ nếu hệ thống có dữ liệu.
- Liên kết mở trang tương ứng.

Sử dụng Process Stepper hoặc Progress Timeline.

Không giả định các giai đoạn luôn thực hiện tuần tự hoặc bắt buộc hoàn thành giai đoạn trước mới bắt đầu giai đoạn sau.

Trạng thái và phần trăm phải lấy từ logic thực tế.

### Khu vực 2. Yêu cầu đã duyệt

Sử dụng Donut Chart.

Hiển thị:

- Tổng số yêu cầu.
- Số yêu cầu đã duyệt.
- Tỷ lệ yêu cầu đã duyệt.
- Các trạng thái còn lại nếu có dữ liệu.

Ví dụ minh họa:

    Yêu cầu đã duyệt

          80%
        ◯ ◯ ◯

    24 / 30 yêu cầu

Click vào biểu đồ hoặc chú thích để mở trang yêu cầu với bộ lọc tương ứng nếu được hỗ trợ.

### Khu vực 3. Ca kiểm thử

Hiển thị:

- Tổng số ca kiểm thử đang hoạt động.
- Ca đã duyệt.
- Ca cần rà soát.
- Ca cần cập nhật nếu có.

Sử dụng thanh tiến độ phân đoạn hoặc Donut Chart nhỏ.

Không sử dụng kết quả PASS/FAIL để biểu diễn trạng thái thiết kế ca kiểm thử.

Phân biệt rõ trạng thái của Test Case với kết quả Test Execution.

### Khu vực 4. Lỗi đang mở

Hiển thị tổng lỗi đang mở.

Sử dụng biểu đồ thanh ngang phân theo mức độ nghiêm trọng hoặc trạng thái thực tế.

Ví dụ:

    Lỗi đang mở             12

    Nghiêm trọng    ██       2
    Cao             ████     4
    Khác            ██████   6

Click vào từng nhóm để chuyển đến màn hình lỗi với bộ lọc phù hợp.

### Khu vực 5. Tình hình thực thi

Sử dụng dữ liệu kết quả thực thi hiện có:

- Pass.
- Fail.
- Blocked.
- Chưa thực hiện.
- Các trạng thái khác nếu có trong hệ thống.

Biểu diễn bằng biểu đồ phân đoạn hoặc biểu đồ tròn.

Nếu API có dữ liệu lịch sử theo thời gian, sử dụng biểu đồ đường để hiển thị tiến độ thực thi.

Nếu không có dữ liệu lịch sử, không được vẽ biểu đồ đường giả.

Thay bằng biểu đồ kết quả hiện tại.

### Khu vực 6. Cần xử lý

Đây là danh sách hành động, không phải danh sách thống kê lặp lại.

Có thể hiển thị các nội dung được hệ thống hỗ trợ:

- Yêu cầu chờ duyệt.
- Ca kiểm thử cần rà soát.
- Ca kiểm thử cần cập nhật.
- Yêu cầu thay đổi.
- Lần chạy chưa hoàn tất.
- Lỗi cần xử lý.

Mỗi mục gồm:

- Icon.
- Tên công việc.
- Số lượng nếu có.
- Link đến đúng trang hoặc đối tượng.

Chỉ hiển thị công việc mà người dùng có quyền xem.

### Khu vực 7. Thay đổi gần đây

Sử dụng Activity Timeline.

Hiển thị các thay đổi có dữ liệu thật:

- Đối tượng thay đổi.
- Nội dung tóm tắt.
- Người thực hiện nếu có.
- Thời gian.
- Phiên bản nếu có.
- Link xem chi tiết.

Không sử dụng bảng nhiều cột cho phần này.

### Khu vực 8. Lần chạy mới nhất

Hiển thị compact card:

- Tên lần chạy.
- Trạng thái.
- Tiến độ thực thi.
- Kết quả.
- Nút mở lần chạy.

### Khu vực 9. Thông tin dự án và thành viên

Đặt ở phần dưới Dashboard.

Không hiển thị thông tin thành viên ở nhiều khu vực khác nhau.

Có thể sử dụng:

- AvatarGroup.
- Tên người dùng.
- Vai trò thực tế.
- Nút xem thành viên.

Nếu cho phép chỉnh sửa, sử dụng inline editing hoặc khung chi tiết theo quyền.

### Yêu cầu đặc biệt

- Không lặp số liệu lỗi giữa nhiều card.
- Không lặp số liệu thành viên.
- Không lặp tỷ lệ tiến độ dưới nhiều tên gọi.
- Không đưa toàn bộ bảng yêu cầu và ca kiểm thử vào Dashboard.
- Không tạo biểu đồ chỉ để trang trí.
- Mọi số liệu phải có ý nghĩa rõ ràng.
- Mỗi biểu đồ phải có trạng thái loading, empty và error.

---

## 6.3. Trang Yêu cầu — Requirement

Nguồn kiểm tra:

- RequirementsPage.jsx.
- RequirementCreateModal.jsx.
- RequirementCurrentVersionPanel.jsx.
- RequirementHistoryPanel.jsx.
- RequirementImpactPanel.jsx.
- RequirementTracePanel.jsx.
- RequirementsListPanel.jsx.
- RequirementImportModal.jsx.

### Mục tiêu

BA và người phụ trách yêu cầu phải có thể đọc, tạo, chỉnh sửa, rà soát, phê duyệt và theo dõi phiên bản yêu cầu mà không cần mở quá nhiều cửa sổ.

### Bố cục

Sử dụng Split View.

    ┌────────────────────────────────────────────────────┐
    │ Yêu cầu       Tìm kiếm       Nhập tài liệu   + Tạo  │
    ├──────────────────┬─────────────────────────────────┤
    │ DANH SÁCH        │ CHI TIẾT YÊU CẦU                │
    │                  │                                 │
    │ REQ-001          │ REQ-001 · Phiên bản 2           │
    │ Đăng nhập        │ Đăng nhập                       │
    │ Đã duyệt         │ Đã duyệt                        │
    │                  │                                 │
    │ REQ-002          │ Nội dung | Phiên bản | Ảnh hưởng│
    │ Đăng ký          │                                 │
    │ Chờ duyệt        │ Mô tả                           │
    │                  │                                 │
    │ REQ-003          │ Tiêu chí chấp nhận              │
    │ Mượn sách        │ AC-01 ...                       │
    │ Bản nháp         │ AC-02 ...                       │
    │                  │                                 │
    │                  │ Quy tắc nghiệp vụ               │
    │                  │ BR-01 ...                       │
    │                  │                                 │
    │                  │ Tài liệu nguồn                  │
    └──────────────────┴─────────────────────────────────┘

### Thanh công cụ

- Tìm kiếm.
- Bộ lọc trạng thái.
- Các bộ lọc hiện có.
- Nút nhập tài liệu.
- Nút tạo yêu cầu.
- Thao tác AI theo quyền và chức năng hiện tại.

### Danh sách bên trái

Chiều rộng tham khảo: 280–340px.

Mỗi yêu cầu hiển thị:

- Mã yêu cầu.
- Tiêu đề.
- Trạng thái.
- Phiên bản nếu cần.
- Chỉ báo cần rà soát hoặc có thay đổi nếu dữ liệu hỗ trợ.

Không hiển thị toàn bộ mô tả trong danh sách.

Có thể hỗ trợ chọn nhiều yêu cầu nếu nghiệp vụ hiện có cho phép thao tác hàng loạt.

### Khung nội dung bên phải

Hiển thị:

- Mã yêu cầu.
- Tiêu đề.
- Trạng thái.
- Phiên bản.
- Thông tin liên quan.
- Nút chỉnh sửa.
- Nút hành động theo quy trình hiện tại.

Các nhóm nội dung được tổ chức thành tab:

- Nội dung.
- Lịch sử phiên bản.
- Phân tích ảnh hưởng.
- Truy vết.
- Rà soát hoặc nhận xét nếu có.

Trong tab Nội dung:

- Mô tả.
- Tiêu chí chấp nhận.
- Quy tắc nghiệp vụ.
- Các trường nghiệp vụ hiện có.
- Tài liệu nguồn.
- Tệp đính kèm nếu được hỗ trợ.

Mỗi AC hoặc BR hiển thị thành một block nội dung gọn.

Ví dụ:

    AC-01
    Hệ thống cho phép người dùng đăng nhập
    bằng thông tin hợp lệ.

    BR-01
    Tài khoản phải đang hoạt động.

Không nhồi AC và BR vào bảng nhiều cột.

### Tạo và chỉnh sửa yêu cầu

Sử dụng một workspace soạn thảo hoặc Drawer rộng.

Thông tin chính hiển thị trước.

Thông tin bổ sung đặt trong các section có thể thu gọn.

Giữ toàn bộ trường dữ liệu, validation và điều kiện bắt buộc hiện có.

Không bỏ trường bắt buộc để làm giao diện ngắn hơn.

### Phân tích phiên bản yêu cầu

Đây là chức năng cần ưu tiên về trải nghiệm.

Thiết kế Comparison Workspace.

    ┌──────────────────────┬──────────────────────┐
    │ Phiên bản trước      │ Phiên bản mới        │
    │ Version 1            │ Version 2            │
    ├──────────────────────┼──────────────────────┤
    │ Nội dung cũ          │ Nội dung mới         │
    │ - Dòng bị xóa        │ + Dòng được thêm     │
    │ Nội dung thay đổi    │ Nội dung thay đổi    │
    ├──────────────────────┴──────────────────────┤
    │ Phân tích ảnh hưởng                        │
    │ Yêu cầu / ca kiểm thử liên quan             │
    │ Các đề xuất xử lý thực tế                   │
    └─────────────────────────────────────────────┘

Sử dụng:

- Màu xanh cho nội dung được thêm.
- Màu đỏ nhạt cho nội dung bị xóa.
- Màu trung tính cho nội dung không thay đổi.
- Chỉ báo nội dung đã sửa.
- Điều hướng giữa các điểm thay đổi.

Hiển thị các ca kiểm thử bị ảnh hưởng nếu backend cung cấp.

Cho phép mở ca kiểm thử liên quan và xem nội dung chi tiết.

Các đề xuất AI phải hiển thị rõ là đề xuất hoặc bản nháp.

Không tự động áp dụng đề xuất nếu quy trình hiện tại yêu cầu người dùng xác nhận.

---

## 6.4. Trang Kế hoạch kiểm thử — Test Plan

Nguồn kiểm tra:

- ExecutionPage.jsx.
- TestPlanEditor và các component liên quan.
- Backend test_plan.py.
- Các API kế hoạch kiểm thử.

### Mục tiêu

Kế hoạch kiểm thử phải giống một tài liệu nghiệp vụ có cấu trúc, không phải biểu mẫu hành chính dài với hàng chục trường được hiển thị cùng lúc.

### Giao diện bên ngoài

Hiển thị danh sách kế hoạch dưới dạng compact card hoặc danh sách phân cấp.

Mỗi kế hoạch gồm:

- Mã kế hoạch.
- Tên kế hoạch.
- Trạng thái.
- Thời gian thực hiện.
- Người phụ trách nếu có.
- Tiến độ.
- Số đối tượng kiểm thử liên kết nếu dữ liệu hỗ trợ.
- Menu thao tác.

Cho phép tìm kiếm, lọc và chuyển List View khi cần.

### Giao diện chi tiết

    ┌─────────────────────────────────────────────┐
    │ TP-001                       Đã duyệt       │
    │ Kế hoạch kiểm thử thư viện                   │
    │ Thời gian: 01/11 - 30/11                    │
    │                                             │
    │ Tiến độ                          68%        │
    │ █████████████░░░░░░                         │
    ├──────────────┬──────────────┬───────────────┤
    │ Yêu cầu      │ Ca kiểm thử  │ Lần chạy      │
    ├──────────────┴──────────────┴───────────────┤
    │ Nội dung kế hoạch                          │
    │                                             │
    │ ▼ Phạm vi kiểm thử                    Sửa   │
    │   Nội dung phạm vi                          │
    │                                             │
    │ ▼ Mục tiêu chất lượng                 Sửa   │
    │   Các điều kiện chất lượng                  │
    │                                             │
    │ ▶ Cách tiếp cận kiểm thử                    │
    │ ▶ Nhân sự và lịch thực hiện                 │
    │ ▶ Rủi ro                                   │
    │ ▶ Chính sách báo cáo                        │
    │ ▶ Thiết lập bổ sung                         │
    └─────────────────────────────────────────────┘

### Các nhóm nội dung

Tổ chức theo schema thực tế:

1. Thông tin chung.
2. Phạm vi kiểm thử.
3. Mục tiêu chất lượng.
4. Cách tiếp cận kiểm thử.
5. Nhân sự và trách nhiệm.
6. Lịch thực hiện.
7. Rủi ro.
8. Điều kiện bắt đầu và kết thúc.
9. Chính sách báo cáo.
10. Các thiết lập khác.

Nếu các trường trên không tồn tại trong mã nguồn, không được tự tạo thêm.

Nếu các trường bắt buộc khác tồn tại, phải giữ lại và đặt vào nhóm thích hợp.

### Mục tiêu chất lượng

Không hiển thị một bảng cấu hình kỹ thuật phức tạp nếu người dùng chỉ cần thiết lập các ngưỡng chất lượng.

Chuyển thành những dòng dễ hiểu.

Ví dụ minh họa:

    Tỷ lệ thực thi tối thiểu          [ 90 ] %
    Tỷ lệ kiểm thử đạt tối thiểu      [ 95 ] %
    Số lỗi nghiêm trọng tối đa        [  0 ]
    Độ bao phủ yêu cầu tối thiểu      [ 90 ] %

Các điều kiện phải được ánh xạ đúng với key và validation thực tế.

Không thay đổi giá trị mặc định của hệ thống nếu chưa có yêu cầu.

### Chỉnh sửa kế hoạch

- Cho phép chỉnh sửa từng section.
- Lưu và hủy rõ ràng.
- Hiển thị lỗi validation ngay dưới trường tương ứng.
- Không ép người dùng mở lại biểu mẫu toàn bộ kế hoạch chỉ để sửa một trường.
- Nếu backend yêu cầu cập nhật toàn bộ payload, frontend phải bảo toàn các trường không thay đổi.

### Trạng thái và phê duyệt

Nút hành động chính phải phù hợp với trạng thái kế hoạch.

Giữ đúng các hành động hiện có như gửi rà soát, phê duyệt, yêu cầu chỉnh sửa, nhân bản hoặc lưu trữ nếu được hỗ trợ.

Không cho phép chỉnh sửa trực tiếp dữ liệu đã khóa nếu quy trình yêu cầu mở bản nháp hoặc phiên bản mới.

---

## 6.5. Trang Ca kiểm thử — Test Case

Nguồn kiểm tra:

- TestDesignPage.jsx.
- TestCaseCreateForm.jsx.
- TestCaseOptions.jsx.
- TestCaseCompareWorkspace.jsx.
- RequirementCoverageSelector.jsx.
- Các component thiết kế kiểm thử.

### Mục tiêu

Xây dựng Test Case Repository trực quan tương tự cách Qase và Testmo tổ chức kho kiểm thử.

Người dùng phải có thể xem danh sách, đọc nội dung, chỉnh sửa, rà soát và quản lý phiên bản mà không phải liên tục chuyển trang.

### Bố cục

    ┌──────────────────────────────────────────────────┐
    │ Ca kiểm thử    Tìm kiếm   Bộ lọc   AI    + Tạo   │
    ├────────────────────┬─────────────────────────────┤
    │ DANH SÁCH CA       │ CHI TIẾT CA KIỂM THỬ       │
    │                    │                             │
    │ ▼ Đăng nhập (3)    │ TC-001 · Version 2          │
    │ □ TC-001           │ Đăng nhập hợp lệ            │
    │   Đăng nhập đúng   │ Đã duyệt · Ưu tiên cao      │
    │ □ TC-002           │                             │
    │   Sai mật khẩu     │ Chi tiết | Phiên bản        │
    │ □ TC-003           │                             │
    │   Tài khoản khóa   │ Tiền điều kiện              │
    │                    │ Tài khoản đang hoạt động    │
    │ ▶ Quản lý sách     │                             │
    │ ▶ Mượn sách        │ Bước kiểm thử               │
    │ ▶ Trả sách         │ 1. Mở trang đăng nhập       │
    │                    │    Mong đợi: ...            │
    │                    │ 2. Nhập thông tin           │
    │                    │    Mong đợi: ...            │
    │                    │                             │
    │                    │ Liên kết yêu cầu            │
    └────────────────────┴─────────────────────────────┘

### Danh sách ca kiểm thử

Có thể nhóm theo:

- Yêu cầu liên kết.
- Nhóm chức năng có dữ liệu thật.
- Các cách phân nhóm hiện có.

Không tự tạo Test Suite hoặc Test Scenario mới chỉ để xây dựng cây thư mục.

Nếu một ca liên kết nhiều yêu cầu, phải xử lý việc hiển thị để không tạo dữ liệu trùng lặp hoặc làm sai thao tác hàng loạt.

Mỗi ca hiển thị:

- Checkbox nếu có hỗ trợ chọn nhiều.
- Mã ca kiểm thử.
- Tiêu đề.
- Trạng thái.
- Mức ưu tiên nếu có.

Cho phép:

- Tìm kiếm.
- Lọc.
- Chọn nhiều.
- Thao tác hàng loạt theo nghiệp vụ hiện tại.
- Chuyển giữa Split View và List View.

### Khung chi tiết

Phần đầu:

- Mã ca kiểm thử.
- Tiêu đề.
- Phiên bản.
- Trạng thái.
- Mức ưu tiên.
- Các metadata quan trọng.
- Nút chỉnh sửa.
- Menu thao tác.

Các tab:

- Chi tiết.
- Phiên bản.
- Liên kết.
- Nhận xét hoặc lịch sử nếu có.

Phần nội dung hiển thị:

- Mô tả.
- Tiền điều kiện.
- Hậu điều kiện.
- Bước kiểm thử.
- Kết quả mong đợi.
- Luồng thay thế.
- Luồng ngoại lệ.
- Dữ liệu kiểm thử.
- Yêu cầu liên kết.
- AC và BR liên kết.
- Tệp đính kèm.
- Các nội dung khác thực sự có trong schema.

Những phần không có dữ liệu được thu gọn hoặc hiển thị trạng thái trống phù hợp.

### Trình bày các bước kiểm thử

Không sử dụng một bảng nhiều cột khiến nội dung bị hẹp.

Sử dụng Step Block.

    ┌──────────────────────────────────────┐
    │ 01. Mở trang đăng nhập           ⋯  │
    │                                      │
    │ Hành động                            │
    │ Truy cập màn hình đăng nhập.         │
    │                                      │
    │ Kết quả mong đợi                     │
    │ Hiển thị biểu mẫu đăng nhập.         │
    └──────────────────────────────────────┘

Hoặc trên màn hình rộng:

    ┌────┬─────────────────┬───────────────────┐
    │ 01 │ Hành động       │ Kết quả mong đợi  │
    │    │ Nội dung bước   │ Nội dung kết quả  │
    └────┴─────────────────┴───────────────────┘

Chỉ giữ hai cột nghiệp vụ cần thiết cho bước và kết quả, không thêm nhiều cột phụ không cần thiết.

Khi chỉnh sửa:

- Thêm bước.
- Xóa bước.
- Đổi thứ tự bước nếu schema hỗ trợ.
- Chỉnh sửa nội dung.
- Hiển thị validation.
- Giữ đúng liên kết dữ liệu của từng bước.

### Giao diện tạo ca kiểm thử

Bố cục đề xuất:

Thông tin chung:

- Mã ca kiểm thử.
- Tiêu đề.
- Mô tả.
- Mức ưu tiên.
- Mức độ nếu có.
- Loại kiểm thử.
- Kỹ thuật kiểm thử nếu có.
- Người phụ trách nếu có.

Điều kiện:

- Tiền điều kiện.
- Hậu điều kiện.

Nội dung kiểm thử:

- Luồng chính.
- Luồng thay thế.
- Luồng ngoại lệ.
- Bước kiểm thử.
- Kết quả mong đợi.

Dữ liệu và liên kết:

- Dữ liệu kiểm thử.
- Requirement.
- AC.
- BR.
- Tệp đính kèm.
- Các trường liên kết hiện tại.

Thông tin bổ sung:

- Tag.
- Trạng thái.
- Các trường nâng cao.

Nếu mã ca được hệ thống sinh tự động hoặc không được phép sửa, phải giữ đúng cơ chế đó.

### Chức năng AI và phân tích phiên bản

Giữ các chức năng hiện có liên quan đến:

- Sinh bản nháp.
- Rà soát.
- So sánh.
- Đề xuất chỉnh sửa.
- Phân tích ảnh hưởng.
- Ghép nội dung.
- Chấp nhận hoặc từ chối.

Thiết kế giao diện so sánh hai phiên bản:

    Phiên bản hiện tại | Bản nháp đề xuất

Hiển thị rõ nội dung được thêm, sửa và xóa.

Cho phép người dùng xem xét trước khi chấp nhận.

Không tự động ghi đè phiên bản đang hoạt động.

---

## 6.6. Trang Lần chạy kiểm thử — Test Run

Nguồn kiểm tra:

- ExecutionPage.jsx.
- RunExecutionWorkspace.jsx.
- Các service test_run và test_run_execution.

### Mục tiêu

Tách rõ trải nghiệm quản lý lần chạy và trải nghiệm trực tiếp thực thi kiểm thử.

### Giao diện danh sách

Mỗi lần chạy hiển thị:

- Mã lần chạy.
- Tên lần chạy.
- Kế hoạch liên kết.
- Trạng thái.
- Người thực hiện.
- Tổng số ca.
- Tiến độ.
- Kết quả phân đoạn.

Ví dụ:

    RUN-001 · Kiểm thử đăng nhập

    ████████████▓▓▓░░░░░

    6 Pass    2 Fail    4 Chưa chạy

    Đã thực hiện: 8/12

Không sử dụng dữ liệu minh họa khi triển khai.

### Execution Workspace

Khi mở lần chạy, sử dụng bố cục chuyên biệt.

    ┌──────────────────────────────────────────────────┐
    │ RUN-001                         Đang thực thi   │
    │ Tiến độ 8/12                                     │
    │ █████████████▓▓▓▓░░░░░                           │
    ├───────────────────┬──────────────────────────────┤
    │ DANH SÁCH CA      │ CA ĐANG THỰC HIỆN           │
    │                   │                              │
    │ ✓ TC-001 Pass     │ TC-004                       │
    │ ✗ TC-002 Fail     │ Bỏ trống mật khẩu           │
    │ ✓ TC-003 Pass     │                              │
    │ ● TC-004          │ Tiền điều kiện               │
    │ ○ TC-005          │ Dữ liệu kiểm thử             │
    │                   │                              │
    │                   │ Bước 1                       │
    │                   │ Hành động                    │
    │                   │ Kết quả mong đợi             │
    │                   │ Kết quả thực tế              │
    │                   │                              │
    │                   │ [Pass] [Fail] [Blocked]      │
    │                   │ Đính kèm bằng chứng          │
    │                   │                              │
    │                   │ [Ca trước] [Lưu và tiếp theo]│
    └───────────────────┴──────────────────────────────┘

### Danh sách ca bên trái

- Mã ca.
- Tiêu đề.
- Trạng thái thực thi.
- Icon trạng thái.
- Bộ lọc kết quả.
- Tìm kiếm.

Click vào ca để mở nội dung tương ứng mà không tải lại toàn bộ trang.

### Khu vực thực thi

Hiển thị:

- Thông tin ca kiểm thử.
- Phiên bản ca đang chạy.
- Tiền điều kiện.
- Dữ liệu kiểm thử.
- Bước thực hiện.
- Kết quả mong đợi.
- Kết quả thực tế.
- Ghi chú.
- Bằng chứng.
- Trạng thái thực thi.

Hiển thị đúng các trạng thái được backend hỗ trợ.

Không tự ý thêm hoặc bỏ trạng thái.

Nếu hệ thống chỉ ghi kết quả ở cấp ca, không được tự tạo cơ chế ghi kết quả cấp bước.

Nếu hệ thống hỗ trợ ghi kết quả từng bước, tối ưu thành Step Block.

### Thao tác nhanh

- Ca trước.
- Ca tiếp theo.
- Lưu kết quả.
- Lưu và chuyển ca tiếp theo nếu có thể triển khai bằng API hiện tại.
- Đính kèm bằng chứng.
- Tạo lỗi.
- Liên kết lỗi hiện có nếu được hỗ trợ.

Khi chọn Fail, hiển thị thao tác tạo lỗi tại đúng ngữ cảnh.

Không tự động tạo lỗi nếu người dùng chưa xác nhận.

### Quy tắc

- Không mất kết quả chưa lưu khi chuyển ca mà không cảnh báo.
- Không cho phép thay đổi kết quả ngoài quyền.
- Không thay đổi phiên bản ca đã được gắn với lần chạy.
- Không đánh dấu hoàn thành khi chưa đạt điều kiện nghiệp vụ.
- Không làm mất chức năng retest, rerun hoặc phân công hiện có.

---

## 6.7. Trang Lỗi — Defect

Nguồn kiểm tra:

- DefectsPage.jsx.
- defectAccess.logic.mjs.
- defectRetest.logic.mjs.
- Các service defect_lifecycle và defect_authorization.

### Mục tiêu

Người dùng có thể quan sát vòng đời lỗi, biết lỗi nào đang cần xử lý và truy cập chi tiết nhanh chóng.

### Chế độ xem

Cung cấp hai chế độ:

- Kanban View.
- List View.

Kanban dùng để theo dõi trạng thái.

List View dùng để lọc, tìm kiếm và quản lý số lượng lớn.

### Kanban View

    ┌────────────┬────────────┬────────────┬───────────┐
    │ Mở         │ Đang xử lý │ Chờ retest │ Đã đóng   │
    ├────────────┼────────────┼────────────┼───────────┤
    │ BUG-001    │ BUG-002    │ BUG-003    │ BUG-004   │
    │ Lỗi A      │ Lỗi B      │ Lỗi C      │ Lỗi D     │
    │ Cao        │ Cao        │ Trung bình │ Thấp      │
    │ Avatar     │ Avatar     │ Avatar     │ Avatar    │
    └────────────┴────────────┴────────────┴───────────┘

Các cột trên chỉ minh họa bố cục.

Phải sử dụng danh mục trạng thái thật trong Veriq.

Mỗi Defect Card gồm:

- Mã lỗi.
- Tiêu đề.
- Mức độ nghiêm trọng.
- Mức ưu tiên nếu cần.
- Người được phân công.
- Chỉ báo cần retest nếu có.

Không nhồi toàn bộ mô tả và bằng chứng vào card.

### Chuyển trạng thái

Nếu triển khai kéo thả:

- Kiểm tra permission.
- Kiểm tra transition hợp lệ.
- Hiển thị yêu cầu xác nhận nếu cần.
- Thu thập lý do hoặc trường bắt buộc.
- Chỉ cập nhật giao diện sau khi thao tác được xác nhận thành công hoặc có cơ chế rollback đúng.

Nếu kéo thả làm phức tạp nghiệp vụ, sử dụng menu chuyển trạng thái.

### Defect Detail Drawer

Khi chọn một lỗi, mở khung chi tiết bên phải.

Hiển thị:

- Mã lỗi.
- Tiêu đề.
- Trạng thái.
- Mức độ.
- Mức ưu tiên.
- Người báo lỗi.
- Người xử lý.
- Mô tả.
- Bước tái hiện.
- Kết quả mong đợi.
- Kết quả thực tế.
- Bằng chứng.
- Requirement liên kết.
- Test Case liên kết.
- Test Run liên kết.
- Lịch sử xử lý.
- Kết quả retest.
- Các đề xuất AI hiện có.

Các dữ liệu phải phù hợp với schema thực tế.

### Lỗi trùng lặp và truy vết

Chuyển các kết quả phân tích lỗi trùng và liên kết truy vết thành danh sách đề xuất có thể mở rộng.

Hiển thị mức tương đồng, căn cứ và thao tác quyết định nếu hệ thống đã có.

Không biến chúng thành các bảng lớn luôn xuất hiện trên trang chính.

---

## 6.8. Trang Báo cáo — Test Report

Nguồn kiểm tra:

- ReportsPage.jsx.
- SimpleTestReports và các component liên quan.
- simple_reports.py.

### Mục tiêu

Báo cáo phải giúp người dùng đánh giá chất lượng và tình hình kiểm thử.

Không chỉ hiển thị một bảng danh sách các báo cáo đã được tạo.

### Bố cục

    ┌────────────────────────────────────────────────┐
    │ Báo cáo kiểm thử                  Xuất báo cáo │
    │ Kế hoạch [▼]       Phạm vi / thời gian [▼]      │
    ├──────────────┬───────────────┬─────────────────┤
    │ Đã thực thi  │ Tỷ lệ đạt     │ Độ bao phủ      │
    │     80%      │     81%       │     92%         │
    ├──────────────┴───────────────┴─────────────────┤
    │ Kết quả kiểm thử                              │
    │ Đăng nhập    ███████████▓░                     │
    │ Mượn sách    ███████▓▓░░░                      │
    │ Trả sách     █████████▓░░                      │
    ├───────────────────────────┬────────────────────┤
    │ Điều kiện hoàn tất        │ Lỗi còn tồn tại    │
    │ ✓ Độ bao phủ              │ Biểu đồ trạng thái │
    │ ✗ Tỷ lệ thực thi          │                    │
    ├───────────────────────────┴────────────────────┤
    │ Báo cáo đã lưu / Xem trước                     │
    └────────────────────────────────────────────────┘

### Bộ lọc

Sử dụng đúng các bộ lọc được API hỗ trợ:

- Kế hoạch.
- Loại báo cáo.
- Phạm vi báo cáo.
- Thời gian nếu có.

### Số liệu quan trọng

Hiển thị những số liệu thực sự có giá trị:

- Tỷ lệ thực thi.
- Tỷ lệ đạt.
- Độ bao phủ.
- Kết quả theo trạng thái.
- Lỗi chưa xử lý.
- Điều kiện hoàn tất.

Không tạo công thức frontend khác với công thức nghiệp vụ.

### Biểu đồ

Có thể sử dụng:

- Donut Chart cho kết quả kiểm thử.
- Stacked Bar Chart cho nhóm chức năng nếu có dữ liệu.
- Horizontal Bar Chart cho phân loại lỗi.
- Line Chart nếu có lịch sử theo thời gian.

Không tạo nhóm chức năng hoặc dữ liệu xu hướng giả.

### Điều kiện hoàn tất

Hiển thị danh sách trực quan:

    Điều kiện                  Thực tế    Yêu cầu
    Độ bao phủ yêu cầu           92%        90%    ✓
    Tỷ lệ thực thi               80%        90%    ✗
    Tỷ lệ đạt                    81%        95%    ✗

Các điều kiện phải lấy từ kế hoạch và logic đánh giá hiện tại.

Phân biệt rõ:

- Đạt.
- Không đạt.
- Chưa đủ dữ liệu để đánh giá.

### Báo cáo đã tạo

Đặt trong tab hoặc khu vực riêng:

- Tên báo cáo.
- Loại báo cáo.
- Phạm vi.
- Ngày tạo.
- Người tạo.
- Xem trước.
- Xuất báo cáo.

Giữ nguyên chức năng xuất PDF và DOCX hiện có.

Không tự quyết định phát hành sản phẩm thay cho người dùng.

---

## 6.9. Trang Tài liệu dự án — Project Documents

Nguồn kiểm tra:

- DocumentReaderPage.jsx.
- RequirementSourceDocumentsPanel.jsx.
- Các component quản lý và nhập tài liệu hiện có.

### Mục tiêu

Quản lý tài liệu giống một thư viện tệp chuyên nghiệp, không phải một bảng metadata kỹ thuật.

### Giao diện danh sách

Sử dụng File Grid View kết hợp List View.

    ┌────────────────────────────────────────────────┐
    │ Tài liệu dự án             Tìm kiếm   + Tải lên │
    ├───────────────┬───────────────┬────────────────┤
    │     PDF       │     DOCX      │     XLSX       │
    │               │               │                │
    │ SRS.pdf       │ Rules.docx    │ Data.xlsx      │
    │ Đã xử lý      │ Đã xử lý      │ Đang xử lý     │
    └───────────────┴───────────────┴────────────────┘

Mỗi tệp hiển thị:

- Icon định dạng.
- Tên tài liệu.
- Trạng thái xử lý.
- Phiên bản nếu có.
- Thời gian cập nhật.
- Menu thao tác.

Chỉ hiển thị dữ liệu được backend cung cấp.

### Tương tác

- Tải lên.
- Xem trước.
- Mở tài liệu.
- Tìm kiếm.
- Lọc.
- Tải xuống nếu được phép.
- Các hành động lưu trữ và phiên bản hiện có.

### Document Reader

Sử dụng bố cục tối đa ba vùng:

    ┌───────────────┬──────────────────┬──────────────┐
    │ Mục lục       │ Nội dung tài liệu│ Công cụ      │
    │               │                  │              │
    │ Chương 1      │ PDF / Markdown   │ Tóm tắt      │
    │ Chương 2      │ Văn bản          │ Tìm kiếm     │
    │ Chương 3      │ Bảng             │ Đối chiếu    │
    │               │ Hình ảnh         │              │
    └───────────────┴──────────────────┴──────────────┘

Mục lục chỉ hiển thị nếu dữ liệu cấu trúc tài liệu hỗ trợ.

Thanh công cụ có thể thu gọn.

Các thao tác AI phải sử dụng chức năng thực tế của dự án.

Giữ rõ sự khác biệt giữa:

- Tệp gốc.
- Nội dung được trích xuất.
- Nội dung AI tạo.
- Cảnh báo tài liệu chưa được đọc đầy đủ.

Không đánh đồng tải tệp thành công với trích xuất hoặc lập chỉ mục thành công.

---

## 6.10. Trang Tài liệu tham chiếu — Knowledge Library

Nguồn kiểm tra:

frontend/features/testing/pages/workspace/KnowledgePage.jsx

### Mục tiêu

Tổ chức tài liệu tham chiếu giống thư viện tri thức, giúp người dùng tìm và đọc nguồn thông tin dễ dàng.

### Bố cục

    ┌───────────────────────────────────────────┐
    │ Tài liệu tham chiếu              + Thêm   │
    │                                           │
    │ [ Tìm kiếm trong tri thức dự án...     ] │
    ├───────────────────────────────────────────┤
    │ 📄 ISTQB CTFL                             │
    │ Tiêu chuẩn kiểm thử                       │
    │ Đã lập chỉ mục                            │
    ├───────────────────────────────────────────┤
    │ 📄 Quy tắc nghiệp vụ                      │
    │ Tài liệu nội bộ                           │
    │ Đã lập chỉ mục                            │
    ├───────────────────────────────────────────┤
    │ 📄 Hướng dẫn nghiệp vụ                    │
    │ Đang xử lý                               │
    └───────────────────────────────────────────┘

### Trang chính

Hiển thị:

- Tìm kiếm tri thức.
- Tên tài liệu.
- Loại nguồn.
- Trạng thái.
- Mức độ chính thức nếu dữ liệu hỗ trợ.
- Thao tác mở chi tiết.
- Thao tác thêm tài liệu.
- Bộ lọc.

### Kết quả tìm kiếm

Không trình bày kết quả chỉ bằng một bảng gồm tên, loại và điểm số.

Sử dụng Search Result Item.

Mỗi kết quả gồm:

- Tiêu đề nguồn.
- Đoạn nội dung liên quan.
- Vị trí nguồn nếu có.
- Tài liệu tham chiếu.
- Bằng chứng hoặc mức liên quan nếu backend trả về.
- Nút mở nguồn.

### Chi tiết kỹ thuật

Đưa các thông tin kỹ thuật vào tab nâng cao hoặc Drawer:

- Trạng thái lập chỉ mục.
- Danh sách chunk.
- Cấu trúc nguồn.
- Hình ảnh nguồn.
- Các metadata được phép xem.
- Lập chỉ mục lại.
- Lưu trữ nguồn.

Không hiển thị vector, chunk hoặc dữ liệu kỹ thuật Qdrant trên màn hình mặc định.

Giữ chức năng kỹ thuật cho người có quyền cần sử dụng.

---

## 6.11. Trang Cài đặt dự án — Project Settings

Nguồn kiểm tra:

frontend/features/testing/pages/workspace/SettingsPage.jsx

### Mục tiêu

Tổ chức cấu hình theo từng nhóm, tương tự GitHub Settings.

Không hiển thị một trang dài chứa tất cả cấu hình dự án.

### Bố cục

    ┌───────────────────┬─────────────────────────────┐
    │ CÀI ĐẶT DỰ ÁN     │ THÔNG TIN CHUNG             │
    │                   │                             │
    │ Thông tin chung   │ Tên dự án                   │
    │ Thành viên        │ [                        ]  │
    │ Quyền của tôi     │                             │
    │ Môi trường        │ Mô tả                       │
    │ Thông báo         │ [                        ]  │
    │ Phân tích         │                             │
    │ Nhật ký kiểm toán │ Thời gian dự án             │
    │                   │                             │
    │                   │                 [Lưu]       │
    └───────────────────┴─────────────────────────────┘

### Nhóm cài đặt

Giữ đúng các nhóm có trong phiên bản hiện tại:

- Thông tin dự án.
- Thành viên.
- Quyền của tôi.
- Môi trường kiểm thử.
- Thông báo.
- Phân tích.
- Nhật ký kiểm toán.
- Các nhóm khác nếu thực sự tồn tại.

Chỉ hiển thị nhóm mà người dùng có quyền truy cập.

### Thông tin dự án

Sử dụng biểu mẫu đơn giản.

- Tên dự án.
- Mã dự án nếu được chỉnh sửa.
- Mô tả.
- Thời gian.
- Trạng thái.
- Các cấu hình trách nhiệm hiện có.

Nút lưu chỉ xuất hiện hoặc được kích hoạt khi có thay đổi hợp lệ.

### Thành viên

Sử dụng compact list hoặc bảng đơn giản:

- Avatar.
- Tên.
- Email.
- Vai trò.
- Trạng thái tham gia.
- Thao tác.

Quản lý thành viên trong Drawer nếu phù hợp.

Giữ logic lời mời, phân công, thay đổi vai trò và rời dự án.

### Môi trường kiểm thử

Sử dụng card hoặc compact list.

Hiển thị:

- Tên môi trường.
- Thông tin môi trường.
- Trạng thái.
- Các thao tác hiện có.

Không tự thêm thông tin cấu hình hạ tầng mà API không cung cấp.

### Nhật ký kiểm toán

Có thể sử dụng bảng vì đây là dữ liệu cần tìm kiếm và đối chiếu.

Các cột gồm những dữ liệu thực sự có:

- Thời gian.
- Người thực hiện.
- Hành động.
- Đối tượng.
- Chi tiết.

Hỗ trợ tìm kiếm và lọc nếu hiện có.

### Khu vực hành động nguy hiểm

Tách riêng:

- Lưu trữ dự án.
- Xóa hoặc loại bỏ thành viên.
- Các thao tác có hậu quả lớn khác.

Sử dụng nhãn cảnh báo và xác nhận theo nghiệp vụ hiện tại.

Không bổ sung thao tác xóa vĩnh viễn nếu người dùng không có quyền hoặc hệ thống không hỗ trợ.

---

## 6.12. Trang Quản lý tài khoản — Admin

Nguồn kiểm tra:

- OperationsPage.jsx.
- Các component quản trị nền tảng.
- platform.service.js.
- Backend authentication platform.py.
- Backend platform_controls.py.

### Mục tiêu

Admin có thể quản lý nhiều tài khoản nhanh chóng, đồng thời xem thông tin chi tiết và thực hiện thao tác quản trị mà không bị quá tải.

Đây là màn hình phù hợp để giữ DataTable.

### Thanh công cụ

- Tìm kiếm tài khoản.
- Bộ lọc trạng thái.
- Bộ lọc vai trò.
- Nút tạo tài khoản.
- Thao tác hàng loạt nếu được hỗ trợ.

### Bảng tài khoản

Chỉ hiển thị các cột chính:

- Người dùng.
- Email.
- Vai trò hệ thống.
- Trạng thái.
- Thao tác.

Các thông tin ít sử dụng đưa vào Drawer.

### Bố cục

    ┌──────────────────────────────────────────────────┐
    │ Quản lý tài khoản                     + Tạo      │
    │ [Tìm kiếm] [Vai trò ▼] [Trạng thái ▼]             │
    ├───────────────┬────────────────┬─────────────────┤
    │ Người dùng    │ Vai trò        │ Trạng thái    ⋯ │
    │ Nguyễn Văn A  │ Admin          │ Hoạt động       │
    │ Trần Văn B    │ Người dùng     │ Hoạt động       │
    │ Lê Văn C      │ Người dùng     │ Đã khóa         │
    └───────────────┴────────────────┴─────────────────┘

### Drawer chi tiết tài khoản

    ┌──────────────────────────────┐
    │ [Avatar]                    × │
    │ Nguyễn Văn A                 │
    │ email@example.com            │
    │                              │
    │ Hồ sơ                        │
    │ Vai trò và quyền             │
    │ Dự án tham gia               │
    │ Trạng thái tài khoản         │
    │                              │
    │ [Chỉnh sửa]                  │
    │ [Khóa tài khoản]             │
    └──────────────────────────────┘

Giữ các chức năng thực tế:

- Tạo tài khoản.
- Cập nhật tài khoản.
- Chỉnh sửa hồ sơ.
- Kích hoạt.
- Vô hiệu hóa.
- Khóa.
- Mở khóa.
- Buộc đổi mật khẩu.
- Thay đổi vai trò hệ thống.
- Xem vai trò dự án.
- Gửi lại xác minh.
- Các thao tác quản trị khác đang được hỗ trợ trên frontend.

Không biến API nội bộ hoặc API chưa có giao diện thành chức năng mới một cách tự ý.

Thao tác xóa, ẩn danh hóa và vô hiệu hóa phải được phân biệt theo logic thực tế.

### Các nhóm quản trị khác

Nếu OperationsPage hiện có các tab quản trị ngoài tài khoản, phải giữ chúng.

Ví dụ: quản lý role, permission hoặc cấu hình nền tảng nếu đang được triển khai.

Không thu gọn toàn bộ trang quản trị thành một bảng tài khoản rồi làm mất các chức năng khác.

---

## 6.13. Trang Tài khoản cá nhân — Account

Nguồn kiểm tra:

frontend/features/authentication/pages/AccountPage.jsx

### Mục tiêu

Người dùng dễ dàng quản lý thông tin cá nhân và bảo mật tài khoản.

### Bố cục

Sử dụng Settings Layout.

Các nhóm nội dung:

- Hồ sơ cá nhân.
- Mật khẩu và bảo mật.
- Phiên đăng nhập.
- Thiết lập cá nhân hiện có.

### Hồ sơ cá nhân

Hiển thị:

- Avatar nếu được hỗ trợ.
- Tên người dùng.
- Email.
- Các thông tin hồ sơ hiện có.
- Múi giờ.
- Ngôn ngữ.

Chỉ giữ trường thực tế được phép cập nhật.

### Mật khẩu và bảo mật

- Mật khẩu hiện tại.
- Mật khẩu mới.
- Các yêu cầu validation.
- Nút đổi mật khẩu.
- Chức năng xác minh hoặc bảo mật hiện có.

Không tạo biểu mẫu MFA giả nếu hệ thống không triển khai.

### Phiên đăng nhập

Sử dụng danh sách thay vì bảng phức tạp.

Mỗi phiên có thể hiển thị:

- Thiết bị hoặc thông tin phiên nếu API cung cấp.
- Thời gian.
- Phiên hiện tại.
- Trạng thái.
- Nút thu hồi phiên.

Giữ chức năng đăng xuất khỏi các phiên theo đúng nghiệp vụ.

---

## 6.14. Các trang xác thực

Đồng bộ giao diện các trang:

- Đăng nhập.
- Quên mật khẩu.
- Xác minh.
- Xác minh email.
- Đặt lại mật khẩu.
- Các trang xác thực đang tồn tại.

Sử dụng Auth Layout dùng chung.

Yêu cầu:

- Logo và thương hiệu Veriq.
- Biểu mẫu gọn.
- Label rõ ràng.
- Hiển thị lỗi dưới trường nhập.
- Hiển thị trạng thái đang xử lý.
- Hỗ trợ hiện hoặc ẩn mật khẩu nếu đã có.
- Điều hướng rõ giữa các bước.
- Giữ đúng validation và luồng xác thực.

Không thêm chức năng đăng ký, đăng nhập mạng xã hội hoặc phương thức xác thực khác nếu dự án chưa hỗ trợ.

---

# PHẦN 7. THIẾT KẾ GIAO DIỆN AI

AI là chức năng hỗ trợ trong Veriq. Giao diện AI phải được tích hợp vào đúng ngữ cảnh nghiệp vụ.

Không tạo một chatbot nổi trên toàn bộ ứng dụng nếu hệ thống không có chức năng đó.

## 7.1. Nguyên tắc

- AI xuất hiện ở nơi có nhiệm vụ cụ thể.
- Người dùng biết AI đang xử lý nội dung gì.
- Hiển thị rõ nguồn được sử dụng nếu có.
- Không tự động chạy AI ngoài quy trình hiện tại.
- Không đánh đồng kết quả AI với dữ liệu đã được duyệt.
- Không tự động ghi đè dữ liệu.
- Không hiển thị chain-of-thought hoặc suy luận nội bộ của mô hình.

## 7.2. Bố cục AI Panel

    ┌─────────────────────────────────┐
    │ AI hỗ trợ                       │
    │                                 │
    │ Nhiệm vụ                        │
    │ Phân tích yêu cầu               │
    │                                 │
    │ Nguồn dữ liệu                   │
    │ REQ-001 · Phiên bản 2           │
    │                                 │
    │ [Bắt đầu phân tích]             │
    │                                 │
    │ Trạng thái xử lý                │
    │ ● Đang xử lý                    │
    │                                 │
    │ Kết quả                         │
    │ Đề xuất 1                       │
    │ Đề xuất 2                       │
    │                                 │
    │ [Xem chi tiết] [Chấp nhận]      │
    └─────────────────────────────────┘

Các nút hành động chỉ xuất hiện nếu nghiệp vụ hỗ trợ.

## 7.3. Trạng thái xử lý AI

Hiển thị đúng trạng thái từ API:

- Đang chờ.
- Đang xử lý.
- Hoàn tất.
- Thất bại.
- Đã hủy.
- Các trạng thái khác nếu tồn tại.

Không tạo phần trăm tiến trình giả nếu backend không cung cấp tiến độ.

Có thể sử dụng trạng thái đang xử lý không xác định phần trăm.

Giữ chức năng thử lại hoặc hủy nếu được hỗ trợ.

## 7.4. Kết quả AI

Kết quả phải có bố cục dễ đọc:

- Tóm tắt.
- Danh sách đề xuất.
- Nguồn và bằng chứng.
- Cảnh báo.
- Những điểm chưa đủ căn cứ nếu hệ thống trả về.
- So sánh nội dung nếu có.
- Thao tác quyết định theo quyền.

Không hiển thị JSON thô cho người dùng nghiệp vụ.

Không thêm hiệu ứng AI nhiều màu hoặc animation không cần thiết.

---

# PHẦN 8. QUY TẮC TƯƠNG TÁC TOÀN HỆ THỐNG

## 8.1. Khi nào sử dụng bảng?

Sử dụng bảng khi người dùng cần:

- So sánh nhiều đối tượng.
- Sắp xếp.
- Lọc dữ liệu.
- Chọn nhiều.
- Thực hiện thao tác hàng loạt.
- Xem nhật ký.
- Quản lý tài khoản.

Không sử dụng bảng làm bố cục chính cho:

- Nội dung yêu cầu.
- Nội dung kế hoạch kiểm thử.
- Mô tả ca kiểm thử.
- Trình đọc tài liệu.
- Màn hình thực thi.
- Hồ sơ cá nhân.
- Cấu hình dự án.
- Dashboard.

## 8.2. Khi nào sử dụng Drawer?

Sử dụng Drawer để:

- Xem nhanh đối tượng.
- Chỉnh sửa thông tin đơn giản.
- Xem lỗi.
- Xem tài khoản.
- Xem chi tiết tài liệu.
- Xem thông tin nâng cao.

Không sử dụng Drawer hẹp cho biểu mẫu dài hoặc chức năng so sánh hai phiên bản cần nhiều không gian.

## 8.3. Khi nào sử dụng Modal?

Chỉ ưu tiên Modal cho:

- Xác nhận.
- Thao tác nhỏ.
- Nhập lý do.
- Các biểu mẫu ngắn.
- Hành động có hậu quả cần xác nhận.

Không mở Modal lồng Modal nếu có cách trình bày đơn giản hơn.

## 8.4. Inline Editing

Cho phép chỉnh sửa tại chỗ khi:

- Người dùng có quyền.
- Trạng thái đối tượng cho phép.
- API hiện tại hỗ trợ.
- Không làm sai quy trình phiên bản.

Phải có:

- Lưu.
- Hủy.
- Loading.
- Validation.
- Hiển thị lỗi.
- Bảo toàn dữ liệu chưa chỉnh sửa.

## 8.5. Search và Filter

Các màn hình danh sách sử dụng cấu trúc thống nhất:

- Ô tìm kiếm.
- Bộ lọc.
- Số lượng kết quả nếu có.
- Các điều kiện lọc đang áp dụng.
- Nút xóa bộ lọc.
- Chuyển chế độ xem.

Không hiển thị toàn bộ bộ lọc nâng cao ngay từ đầu.

Có thể đưa các bộ lọc ít dùng vào Filter Popover.

## 8.6. Loading, Empty và Error

Mỗi màn hình phải xử lý đầy đủ:

Loading:

- Skeleton phù hợp với bố cục.
- Không để toàn trang trống.
- Không hiển thị dữ liệu giả.

Empty State:

- Giải thích chưa có dữ liệu.
- Hiển thị hành động phù hợp theo quyền.
- Phân biệt chưa có dữ liệu với không tìm thấy kết quả.

Error State:

- Hiển thị lỗi rõ ràng.
- Cho phép tải lại hoặc thử lại nếu phù hợp.
- Không nuốt lỗi.
- Không hiển thị kết quả thành công khi API thất bại.

## 8.7. Accessibility

- Hỗ trợ thao tác bằng bàn phím.
- Focus state rõ ràng.
- Nút có accessible name.
- Icon button có tooltip hoặc nhãn phù hợp.
- Màu chữ và nền đủ tương phản.
- Không dùng màu sắc làm dấu hiệu duy nhất.
- Drawer và Modal quản lý focus đúng.
- Biểu đồ có chú thích và thông tin thay thế.
- Không gây mất nội dung khi phóng to giao diện.

Hướng đến WCAG 2.2 AA trong phạm vi frontend, không tuyên bố đạt chuẩn nếu chưa được đánh giá.

---

# PHẦN 9. QUY TRÌNH TRIỂN KHAI

Thực hiện theo từng phase để tránh phá vỡ hệ thống.

## Phase 0 — Audit

- Kiểm kê toàn bộ màn hình frontend.
- Xác định route đang hoạt động.
- Xác định route legacy.
- Xác định component dùng chung.
- Xác định các bảng đang sử dụng.
- Xác định API và schema liên quan.
- Xác định quyền và trạng thái nghiệp vụ.
- Xác định các thành phần cần giữ nguyên.
- Ghi nhận vấn đề UI/UX.
- Lập bản đồ chức năng trước khi redesign.

Đầu ra:

UI_UX_AUDIT.md

## Phase 1 — Design System và Global Layout

- Chuẩn hóa màu sắc.
- Typography.
- Spacing.
- Component.
- Sidebar.
- Header.
- Content Layout.
- Loading.
- Empty State.
- Error State.
- FilterBar.
- Split View.
- Drawer.

Đảm bảo các màn hình cũ vẫn hoạt động.

## Phase 2 — Dự án và Dashboard

- Thiết kế lại danh sách dự án.
- Project Card.
- Grid/List View.
- Dashboard.
- Biểu đồ.
- Tiến trình kiểm thử.
- Action List.
- Activity Timeline.

## Phase 3 — Requirement

- Split View.
- Trình soạn thảo yêu cầu.
- AC và BR.
- Nhập tài liệu.
- Lịch sử.
- Phân tích phiên bản.
- Phân tích ảnh hưởng.
- Truy vết.

## Phase 4 — Test Plan

- Danh sách kế hoạch.
- Workspace tài liệu.
- Section thu gọn.
- Inline Editing.
- Mục tiêu chất lượng.
- Phạm vi.
- Rủi ro.
- Nhân sự.
- Quy trình phê duyệt.

## Phase 5 — Test Case

- Repository View.
- Split View.
- Tìm kiếm và lọc.
- Thao tác hàng loạt.
- Step Block.
- Biểu mẫu tạo ca kiểm thử.
- Lịch sử phiên bản.
- So sánh nội dung.
- Các chức năng AI hiện có.

## Phase 6 — Test Run và Defect

- Giao diện danh sách lần chạy.
- Execution Workspace.
- Thao tác ghi kết quả.
- Bằng chứng.
- Tạo lỗi.
- Defect Kanban.
- Defect List.
- Defect Drawer.
- Retest.

## Phase 7 — Báo cáo và Tài liệu

- Report Dashboard.
- Report Preview.
- Xuất báo cáo.
- Project Documents.
- Document Reader.
- Knowledge Library.

## Phase 8 — Cài đặt và Tài khoản

- Project Settings.
- Thành viên.
- Môi trường.
- Nhật ký.
- Quản lý tài khoản.
- Tài khoản cá nhân.
- Các trang xác thực.

## Phase 9 — Kiểm thử và hoàn thiện

- Kiểm thử tất cả route đang hoạt động.
- Kiểm thử phân quyền.
- Kiểm thử nghiệp vụ.
- Kiểm thử responsive.
- Kiểm thử accessibility.
- Kiểm thử API integration.
- Kiểm thử các trạng thái giao diện.
- Kiểm thử các biểu mẫu.
- Kiểm thử lỗi và mất kết nối.
- Regression testing.

Có thể thực hiện tuần tự các phase mà không cần hỏi lại sau mỗi phase, miễn là không thay đổi nghiệp vụ hoặc thực hiện hành động vượt phạm vi.

Nếu phát hiện xung đột quan trọng giữa thiết kế đề xuất và mã nguồn, ưu tiên bảo toàn nghiệp vụ rồi ghi nhận quyết định.

---

# PHẦN 10. KIỂM THỬ VÀ NGHIỆM THU

Không được kết luận hoàn thành chỉ vì đã sửa mã nguồn hoặc giao diện có thể build.

## 10.1. Kiểm tra kỹ thuật

Sử dụng package manager và các script hiện có trong repository.

Thực hiện các kiểm tra phù hợp:

- Lint.
- Format check.
- Build.
- Unit Test.
- Integration Test.
- Frontend Test.
- Docker build nếu môi trường hỗ trợ.
- Smoke test.
- Regression test.

Không tự ý tắt lint hoặc bỏ qua test đang thất bại.

Phân biệt lỗi tồn tại từ trước với lỗi phát sinh do redesign.

## 10.2. Kiểm tra giao diện thực tế

Nếu có quyền sử dụng browser hoặc hệ thống đang chạy:

- Mở từng màn hình.
- Kiểm tra bố cục.
- Kiểm tra thao tác.
- Kiểm tra cuộn trang.
- Kiểm tra modal và drawer.
- Kiểm tra trạng thái loading.
- Kiểm tra dữ liệu trống.
- Kiểm tra lỗi API.
- Kiểm tra các độ phân giải desktop.
- Kiểm tra responsive trên màn hình nhỏ.
- Chụp ảnh bằng chứng trước và sau khi chỉnh sửa.

Không tuyên bố đã kiểm tra giao diện bằng trình duyệt nếu thực tế chưa truy cập được.

## 10.3. Kiểm thử phân quyền

Đối chiếu hành động với capability thực tế.

Kiểm tra:

- Người chỉ có quyền đọc.
- Người có quyền tạo.
- Người có quyền chỉnh sửa.
- Người có quyền rà soát.
- Người có quyền phê duyệt.
- Người thực thi kiểm thử.
- Người xử lý lỗi.
- Người quản trị.

Không tạo tài khoản hoặc thay đổi dữ liệu thật nếu chưa được cho phép.

## 10.4. Tiêu chí nghiệm thu

Một màn hình chỉ được đánh dấu hoàn thành khi:

- Không làm mất chức năng hiện có.
- API hoạt động đúng.
- Phân quyền được bảo toàn.
- Validation hoạt động đúng.
- Không có dữ liệu giả trong giao diện thực tế.
- Không phát sinh lỗi console nghiêm trọng.
- Không mất dữ liệu khi chuyển trang hoặc thao tác.
- Không tràn bố cục.
- Không có thông tin lặp lại không cần thiết.
- Có loading, empty và error state.
- Giao diện sử dụng thành phần nhất quán.
- Có thể thực hiện nghiệp vụ chính mà không gặp lỗi do redesign.
- Đã ghi nhận kết quả kiểm tra và hạn chế còn tồn tại.

---

# PHẦN 11. CÁC ARTIFACT PHẢI BÀN GIAO

Tạo thư mục tài liệu redesign theo convention hiện tại của repository.

Có thể sử dụng:

    docs/ui-ux-redesign/
    ├── UI_UX_AUDIT.md
    ├── DESIGN_SYSTEM.md
    ├── PAGE_MAPPING.md
    ├── IMPLEMENTATION_PLAN.md
    ├── FUNCTION_PRESERVATION.md
    ├── CHANGELOG.md
    ├── TEST_REPORT.md
    ├── KNOWN_ISSUES.md
    └── screenshots/
        ├── before/
        └── after/

## UI_UX_AUDIT.md

Ghi nhận vấn đề của từng màn hình trước khi sửa.

## DESIGN_SYSTEM.md

Mô tả màu sắc, typography, spacing, component và quy tắc sử dụng.

## PAGE_MAPPING.md

Ánh xạ:

- Trang.
- Route.
- Component cũ.
- Component mới.
- API.
- Chức năng.
- Quyền liên quan.

## FUNCTION_PRESERVATION.md

Chứng minh các chức năng hiện có được bảo toàn.

Ghi rõ chức năng nào được:

- Giữ nguyên.
- Đổi vị trí.
- Tổ chức lại.
- Thu gọn.
- Chưa triển khai redesign.
- Không thể kiểm tra.

## CHANGELOG.md

Ghi danh sách file đã tạo và chỉnh sửa.

Nêu mục đích thay đổi.

## TEST_REPORT.md

Ghi kết quả kiểm thử:

- PASS.
- FAIL.
- BLOCKED.
- NOT RUN.

Kèm bằng chứng khi có.

Không đánh dấu PASS nếu chưa thực hiện kiểm tra.

## KNOWN_ISSUES.md

Ghi:

- Lỗi chưa xử lý.
- Thiếu dữ liệu.
- Hạn chế API.
- Hạn chế môi trường.
- Chức năng chưa thể kiểm tra.
- Rủi ro phát sinh.

---

# PHẦN 12. NHỮNG ĐIỀU TUYỆT ĐỐI KHÔNG ĐƯỢC LÀM

1. Không chỉ đổi màu và bo góc rồi gọi đó là redesign.
2. Không biến tất cả màn hình thành bảng.
3. Không biến tất cả nội dung thành card.
4. Không tự thêm chức năng không có trong dự án.
5. Không xóa chức năng chỉ vì giao diện phức tạp.
6. Không tạo biểu đồ bằng dữ liệu giả.
7. Không hardcode số liệu.
8. Không tự thay đổi quyền.
9. Không tự thay đổi công thức tiến độ.
10. Không tự thay đổi trạng thái nghiệp vụ.
11. Không tạo component trùng lặp.
12. Không lạm dụng modal.
13. Không hiển thị thông tin lặp lại.
14. Không thêm animation không cần thiết.
15. Không đưa dữ liệu kỹ thuật vào màn hình nghiệp vụ mặc định.
16. Không bỏ qua validation.
17. Không tự ghi đè dữ liệu đã được duyệt.
18. Không làm mất chức năng AI đang hoạt động.
19. Không khôi phục module legacy ngoài phạm vi.
20. Không tuyên bố hoàn thành khi chưa kiểm thử.
21. Không commit hoặc push lên GitHub nếu chưa được yêu cầu.

---

# PHẦN 13. KẾT QUẢ CUỐI CÙNG MONG MUỐN

Veriq sau redesign phải có sự phân biệt rõ giữa các loại giao diện:

| Trang | Phong cách thiết kế chính |
|---|---|
| Dự án | Project Card và List View |
| Dashboard | Biểu đồ, tiến trình, Action List |
| Requirement | Split View và Document Editor |
| Phân tích phiên bản | Side-by-side Comparison |
| Test Plan | Document Workspace |
| Test Case | Test Repository và Step Block |
| Test Run | Execution Workspace |
| Defect | Kanban và List View |
| Report | Analytics Dashboard và Report Preview |
| Tài liệu dự án | File Explorer và Document Reader |
| Tài liệu tham chiếu | Knowledge Library |
| Cài đặt dự án | Grouped Settings |
| Quản lý tài khoản | DataTable và Detail Drawer |
| Tài khoản cá nhân | Profile Settings |
| Xác thực | Auth Layout |
| AI | Contextual AI Workspace |

Hãy bắt đầu bằng việc đọc mã nguồn hiện tại, thực hiện Audit, xác định cấu trúc UI thực tế, sau đó tiến hành redesign theo các phase đã mô tả.

Không chỉ trả về bản phân tích hoặc hướng dẫn chung. Hãy thực hiện chỉnh sửa trực tiếp mã nguồn frontend trong phạm vi được phép, kiểm tra kết quả và bàn giao đầy đủ.

Triết lý thiết kế cuối cùng của Veriq:

**Đơn giản nhưng đầy đủ.**

**Trực quan nhưng không màu mè.**

**Ít thao tác nhưng không mất chức năng.**

**Thông tin xuất hiện đúng nơi, đúng lúc và đúng quyền.**

**Nhìn vào là hiểu, bấm vào là làm được.**
