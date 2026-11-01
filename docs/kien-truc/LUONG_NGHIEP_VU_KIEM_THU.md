# Luồng nghiệp vụ kiểm thử Veriq

## Quy trình và quan hệ dữ liệu

Luồng hướng dẫn: tài liệu → Requirement → Test Plan nháp → phân tích → Scenario → Test Case → chốt Plan → chuẩn bị → Test Run → báo cáo → quyết định phát hành.

Plan nháp được tạo trước ca, được hoàn thiện dần và khóa phạm vi khi duyệt. Scenario và Test Case thuộc kho dùng lại; Plan chọn các phiên bản cần thực hiện. Việc dùng lại không tạo bản sao hoặc chuyển kết quả PASS/FAIL cũ sang lần chạy mới.

| Bước | Dữ liệu và trách nhiệm |
| --- | --- |
| Nguồn | Tệp gốc, loại tài liệu, phiên bản, quyền, sự đồng ý cho AI đọc, nội dung chuẩn hóa, khối/vị trí và cảnh báo trích xuất. |
| Requirement | Mã, loại, tên, nội dung, tác nhân, quy tắc, phụ thuộc, tiêu chí chấp nhận có mã, ưu tiên/rủi ro, chi tiết theo loại, nguồn, người phụ trách và lịch sử. BA soạn/sửa; QA rà duyệt. |
| Test Plan | Mục tiêu; trong/ngoài phạm vi; phiên bản yêu cầu; chiến lược/cách tiếp cận; cấp/loại; người và trách nhiệm; môi trường; kế hoạch dữ liệu; điều kiện bắt đầu/kết thúc; lịch/mốc; ước lượng; rủi ro/biện pháp; quy trình Defect; bàn giao/báo cáo; phụ thuộc/ràng buộc; tạm dừng/tiếp tục; chỉ số chất lượng; duyệt và snapshot. |
| Phân tích | Điều kiện kiểm thử và nghĩa vụ bao phủ từ tiêu chí chấp nhận, quy tắc, nhánh, biên, ngoại lệ và rủi ro. Câu hỏi làm rõ dẫn về BA; QA đánh giá khả năng kiểm thử. |
| Scenario | Mã, tên, mục tiêu, nhóm, mô tả, tác nhân, tiền điều kiện, luồng/ngoại lệ, kết quả khái quát, dữ liệu/biến thể, cấp/loại, ưu tiên/rủi ro, người phụ trách, nhãn, yêu cầu/tiêu chí/điều kiện và ca liên quan. QA tạo, chỉnh và duyệt. |
| Test Case | Mã, tên, mục tiêu, loại/cấp, ưu tiên/rủi ro/ảnh hưởng, tiền/hậu điều kiện, Step ID, hành động/dữ liệu/kết quả từng bước, dataset/bước dùng lại, BDD khi có, Scenario, yêu cầu/tiêu chí, nguồn, người sở hữu, kỹ năng, tự động hóa và phiên bản/duyệt. QA quản lý định nghĩa; Tester nhận xét. |
| Chuẩn bị | Kiểm tra kế hoạch/phiên bản ca, môi trường, build, dữ liệu, tài khoản/công cụ, người chạy và điều kiện bắt đầu. Ngoại lệ có lý do và người quyết định. |
| Test Run | Kế hoạch/snapshot, ca phiên bản, build/release/môi trường, phân công thực thi, lịch, từng kết quả/bước, Actual Result, bằng chứng, thời gian, lý do bị chặn/bỏ qua, Defect và lượt chạy lại. |
| Defect | Mã, mô tả, bước tái hiện, Expected/Actual, severity/priority, build/môi trường, bằng chứng, người báo/xử lý, workflow, retest và liên kết nguồn/ca/lượt chạy. |
| Báo cáo | Báo cáo trạng thái trong lúc chạy; báo cáo hoàn tất có phạm vi, các lượt/build/môi trường được tính, kết quả/độ phủ, điều kiện kết thúc, lỗi/rủi ro còn lại, ngoại lệ, bàn giao, kết luận và người duyệt. |

Người phụ trách Test Case và người thực thi trong Test Run là hai thông tin riêng. Đề xuất nhân sự dùng hồ sơ đã xác nhận, khả dụng, tải và chính sách chi phí. Người có quyền quyết định chấp nhận hoặc thay đổi đề xuất. Admin quản trị tài khoản và đơn giá; quyền Admin không tự thay thế quyền nghiệp vụ QA.

## Nguồn đầu vào và tính đầy đủ

Đường tải tệp nhận PDF, DOCX, TXT, MD, CSV, XLSX, JSON, YAML/YML. Đường nhập nội dung hỗ trợ các định dạng được công bố riêng, gồm OpenAPI/Postman. Nhận định dạng không chứng minh trích xuất đầy đủ; cảnh báo trang/khối đọc lỗi phải được giữ.

Phân loại nguồn tái sử dụng danh mục có sẵn: SRS, BRD, User Story, tiêu chí chấp nhận, quy tắc nghiệp vụ, API, UI, kiến trúc, biên bản, thay đổi phát hành, lịch sử lỗi, tài sản kiểm thử, quy định, tham chiếu và nguồn khác. Đặc tả dữ liệu, phân quyền và phi chức năng được liên kết theo nội dung Requirement tương ứng.

QA xác định những nguồn áp dụng với dự án. Đánh giá dựa vào thông tin: mục tiêu, hành vi, tác nhân, điều kiện, quy tắc, dữ liệu/quyền, tiêu chí đo được, ngoại lệ và phụ thuộc. Thiếu thông tin tạo mục cần bổ sung hoặc làm rõ; không suy ra từ số lượng tệp và không yêu cầu mọi dự án có đủ mọi loại tài liệu.

## Quyền, AI và phiên bản

- BA quản lý nội dung nghiệp vụ; QA đề nghị sửa và duyệt Requirement, quản lý thiết kế/kế hoạch/thực thi/báo cáo. Tester chỉ thực thi phần được giao, báo lỗi và đề nghị chỉnh ca. Developer xử lý Defect/công việc được giao. Viewer đọc theo phạm vi.
- Scenario mới luôn là nháp. Các chuyển trạng thái gửi rà soát, duyệt và trả chỉnh sửa kiểm tra quyền QA và revision; nội dung đã duyệt không được sửa đè.
- AI chỉ chạy khi người dùng yêu cầu theo mặc định. `AI_DOMAIN_AUTOMATION_ENABLED=false` chặn việc nhận sự kiện nghiệp vụ để khởi tạo lượt AI tự động. Chuyển đổi tệp, lập chỉ mục, lưu nháp và tính toán xác định vẫn dùng hạ tầng nền hiện có.
- Đề xuất AI không tự duyệt/công bố. Ca AI phải qua preview, lưu nháp, so sánh/chỉnh và quyết định của QA. Báo cáo AI là đề xuất riêng, không thay số liệu hoặc quyết định trong báo cáo gốc.
- Báo cáo hoàn tất ghi nhận phiên bản Chiến lược kiểm thử đã duyệt nếu Test Plan gắn chiến lược đó; nếu không, dùng cách tiếp cận đã đóng băng trong snapshot Test Plan và ghi rõ nguồn là Test Plan. Không cần tạo một hồ sơ chiến lược riêng chỉ để lặp lại nội dung đã duyệt trong kế hoạch.
- QA chỉ thực thi khi được phân công vào Run hoặc ca cụ thể; Tester cũng chỉ thực thi phạm vi được giao. BA, Developer và Viewer không trở thành người thực thi chỉ vì có tên trong dự án.
- Prompt theo cấu trúc tiếng Anh hiện có; đầu ra theo ngôn ngữ người dùng. Nguồn, quyền và revision được kiểm tra tại backend.
- Plan cũ giữ nguyên digest và snapshot; trường kế hoạch dữ liệu/Defect chỉ được đưa vào digest khi có trong snapshot. Trường mới không ghi bù vào bản đã duyệt.
- Run tiếp tục khóa phiên bản, build và môi trường theo hợp đồng hiện hữu. Ca/yêu cầu đổi tạo phiên bản và phạm vi mới; lịch sử kết quả được giữ.

## Thay đổi giao diện và API

- Menu đưa kế hoạch kiểm thử lên trước thiết kế, kịch bản lên trước ca; các URL cũ được giữ.
- Requirement đã duyệt có thao tác lập Plan mang theo phiên bản nguồn. Plan xem được đầy đủ; Plan nháp lưu được khi chưa có ca/lịch. Plan đã duyệt có thao tác tạo Run mang theo snapshot và bối cảnh.
- Schema tạo/sửa Plan thêm `test_data_plan` và `defect_management`, có mặc định cho dữ liệu cũ. Người chuẩn bị dữ liệu phải là thành viên đang hoạt động.
- API Plan thêm `POST /ke-hoach-kiem-thu/{id}/yeu-cau-chinh-sua`, có revision, lý do và transaction/audit.
- Scenario được mở xem/sửa đầy đủ và có API gửi rà soát, duyệt, yêu cầu chỉnh sửa. API dùng quyền cập nhật Scenario và kiểm tra vai trò QA, không tạo hệ quyền độc lập.
- Tạo Test Case chọn Scenario hiện hữu và nhận liên kết nguồn. Ca cũ thiếu Scenario vẫn được giữ.
- Các API sinh Scenario/preview ca dùng phiên đăng nhập với quyền tương ứng; không bắt buộc danh tính sự kiện tự động. Sinh ca vẫn bắt buộc preview và giữ kiểm tra nguồn/trùng lặp.
- API diễn giải báo cáo chấp nhận yêu cầu thủ công với revision/idempotency. Provider lỗi, mất quyền hoặc báo cáo đổi trong lúc chạy không lưu kết quả thành công. Lịch sử kết quả tự động trước đây vẫn đọc được.

## Bằng chứng và trạng thái triển khai

Đây là đặc tả nghiệp vụ và ghi nhận thay đổi; không phải biên bản đã nghiệm thu toàn hệ thống.

| Nhóm | Kiểm chứng hiện có |
| --- | --- |
| Hợp đồng/luồng mới | 20 kiểm tra service đạt: nháp Plan, hợp đồng typed, tương thích/tamper snapshot, người chuẩn bị dữ liệu, patch Scenario, tính bất biến, rà duyệt/quyền/revision, AI thủ công, provider lỗi, nguồn đổi và mất quyền. |
| Hồi quy service | 33 kiểm tra hiện hữu về duyệt nhóm/đối chiếu ca, phân công Run và tính nguyên tử retest đạt. |
| Logic giao diện | 21 kiểm tra hiện hữu về dữ liệu bản nháp, đường dẫn và quyền đạt. Phát hiện và sửa việc patch thiếu trường gây lỗi hoặc có thể xóa nội dung không được chỉnh. |
| Chất lượng frontend | Production build cục bộ, kiểm tra định dạng và lint toàn frontend đạt tại lượt kiểm tra. |
| Luồng API trên Docker | Dự án thử riêng đã đi qua tài liệu → Requirement nháp/duyệt → Plan nháp/duyệt → Scenario nháp/rà soát/duyệt → Test Case nháp/rà soát/duyệt → phân công QA → Run → kết quả → mốc giám sát → báo cáo hoàn tất → QA ký → duyệt → đóng. Một lượt kiểm tra bổ sung, tách biệt sau đó, ghi nhận FAIL → tạo lỗi có liên kết → xác nhận/đang xử lý/đã sửa/chờ kiểm thử lại → Run mới PASS → lỗi đóng. Báo cáo hoàn tất dùng cách tiếp cận từ snapshot Plan khi không gắn chiến lược riêng. Dữ liệu kiểm chứng được ghi rõ là tổng hợp, không phải kết quả kiểm thử sản phẩm khách hàng. |
| Trình duyệt trên Docker | Màn Báo cáo và báo cáo hoàn tất có dữ liệu thật đã mở ở 1280, 1440, 1920 px; không có lỗi JavaScript hoặc tràn ngang. Bảng hoạt động hiển thị nhãn tiếng Việt, không lộ mã sự kiện của luồng này. Ảnh lưu tại `/tmp/veriq-business-workflow-checks/completion-1280.png`, `completion-1440.png`, `completion-1920.png`. Frontend image đã qua format check, lint, production build và được chạy lại trong Docker. |

Hồi quy Defect/retest hiện có đạt 33 kiểm tra về tính nguyên tử và phân công; lượt API tổng hợp cũng kiểm tra đường FAIL → Defect → retest PASS và trạng thái lỗi cuối `CLOSED`. Dự án thử chỉ chứa dữ liệu tổng hợp. Không thay đổi phiên bản lịch sử đã duyệt hoặc kết quả cũ. Các kiểm tra bổ sung không tạo thêm mã công việc ngoài phạm vi kế hoạch này.
