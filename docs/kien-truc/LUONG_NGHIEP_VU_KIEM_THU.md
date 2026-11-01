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

Người phụ trách Test Case và người thực thi trong Test Run là hai thông tin riêng. Đề xuất nhân sự phải xét đồng thời độ phù hợp năng lực, vai trò, kinh nghiệm đã xác nhận, khả dụng, tải và giới hạn phân bổ qua nhiều dự án. Ở cấp Test Plan/dự án, phép tính nguồn lực còn xét độ phức tạp, rủi ro, phạm vi, thời hạn, giá trị/giá khách hàng, ngân sách và chi phí nhân công theo bảng lương có hiệu lực. Đơn giá là dữ liệu chi phí, không phải bằng chứng về năng lực: không tự kết luận người lương cao giỏi hơn hoặc mặc định giao họ cho dự án lớn. Người có quyền quyết định chấp nhận hoặc thay đổi đề xuất. Admin quản trị tài khoản và đơn giá; quyền Admin không tự thay thế quyền nghiệp vụ QA.

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

## Danh mục 10 năng lực AI trong cùng luồng

Mười năng lực dưới đây là các thao tác có chủ đích trên dữ liệu Veriq hiện có, không phải mười chatbot hay mười kho dữ liệu. Người dùng bấm đúng thao tác ở đúng bước; mỗi kết quả là đề xuất có nguồn và trạng thái riêng. AI không tự chuyển sang bước kế tiếp, không tự lưu nội dung nghiệp vụ, không tự duyệt và không quyết định phát hành.

| ID | Thời điểm người dùng gọi | Đầu vào và kết quả cần nhận | Bước kiểm soát của người dùng |
| --- | --- | --- | --- |
| AI-01 | Khi rà Requirement | Tìm câu mơ hồ, thiếu điều kiện/ngoại lệ, mâu thuẫn và câu hỏi cần BA trả lời; mỗi phát hiện trỏ về đúng phiên bản và đoạn nguồn. | BA sửa hoặc trả lời; QA duyệt Requirement. AI không viết đè. |
| AI-02 | Sau khi chọn Requirement đã duyệt | Lập bản đồ tiêu chí, quy tắc, nhánh, biên, quyền và rủi ro thành nghĩa vụ kiểm thử; chỉ ra nghĩa vụ đã có/chưa có Scenario hoặc Test Case. | QA xác nhận nghĩa vụ áp dụng; mục chưa đủ căn cứ thành câu hỏi, không tự bịa kết quả. |
| AI-03 | Khi tạo/sửa Test Plan nháp | Đề xuất mục tiêu, phạm vi, chiến lược, cấp/loại, môi trường, dữ liệu, tiêu chí vào/ra, lịch, rủi ro, phân công vai trò, giờ công và bàn giao theo các trường Test Plan hiện có. | QA sửa và lưu nháp; QA duyệt theo quy trình hiện có. Giờ công là ước lượng, không phải lịch hay chi phí thực tế. |
| AI-04 | Khi thiết kế Scenario/Test Case | Sinh bản xem trước có liên kết Requirement/tiêu chí và phần trích dẫn; đánh dấu ca tương tự/trùng, cho chọn từng đề xuất. | QA chọn, ghép/sửa, lưu nháp, gửi rà soát và duyệt. Kịch bản cũng phải xem trước và chọn trước khi lưu. |
| AI-05 | Sau khi Requirement hoặc nguồn liên quan đổi | Phân tích ảnh hưởng theo liên kết truy vết, đề xuất Scenario/Case/Plan/Run cần rà soát và phạm vi hồi quy. | QA xác nhận phạm vi; chỉ người có quyền mới tạo phiên bản/phạm vi mới. Không sửa lịch sử Run. |
| AI-06 | Khi chuẩn bị Data Set | Đề xuất dữ liệu kiểm thử tổng hợp theo điều kiện và loại dữ liệu; nêu giá trị biên/âm, ràng buộc, cách reset và rủi ro riêng tư. | QA kiểm tra, làm sạch và lưu thành Data Set phiên bản mới. Không dùng dữ liệu cá nhân thật làm dữ liệu mẫu. |
| AI-07 | Khi giao người phụ trách Test Case hoặc lập nguồn lực Plan/Run | Gợi ý ứng viên đủ năng lực theo kỹ năng/kinh nghiệm đã xác nhận, vai trò, khả dụng, tải và phân bổ đa dự án. Ở cấp Plan, so sánh các phương án nhân lực/giờ công với độ phức tạp, rủi ro, phạm vi, thời hạn, giá trị/giá khách hàng, ngân sách và dự toán chi phí từ bảng lương. | Người có quyền chọn/sửa phân công và phương án. Không coi lương là năng lực hay tự động gán người lương cao vào dự án lớn. Đơn giá được tính ở backend; AI chỉ nhận dữ liệu tổng hợp không định danh nếu thật sự cần diễn giải. Run executor là phân công riêng. |
| AI-08 | Trong lúc Tester thực thi | Giải thích bước, nêu thông tin/evidence còn thiếu và đề xuất nội dung Defect từ kết quả đã ghi. | Tester xác nhận trước khi ghi Defect/kết quả; không tự PASS/FAIL, không tự sửa Test Case. |
| AI-09 | Khi xem báo cáo trạng thái/hoàn tất | Viết phần diễn giải dựa trên snapshot, số liệu thực thi, độ phủ và Defect đã lưu; chỉ rõ giới hạn dữ liệu và rủi ro còn lại. | QA chỉnh sửa và duyệt báo cáo. Số liệu gốc, tiêu chí kết thúc và quyết định phát hành vẫn thuộc workflow hiện có. |
| AI-10 | Sau các quyết định chấp nhận/sửa/từ chối | Tổng hợp báo cáo chất lượng: loại đề xuất, phần thường được sửa, lý do từ chối, lỗi nguồn/grounding và điểm nghẽn; chỉ dùng bản ghi được phép. | Người quản lý xem báo cáo. Không huấn luyện/tinh chỉnh model, cá nhân hóa hay tự đổi điểm xếp hạng từ phản hồi này. |

## AI-11: Hồ sơ độ khó và mức sẵn sàng kiểm thử của dự án

AI-11 chạy khi người có quyền bấm đánh giá sau khi đã chọn tài liệu/Requirement cần xét. Hệ thống kiểm tra trạng thái phân tích, quyền AI đọc, phiên bản, phạm vi nguồn và cảnh báo trích xuất trước khi gọi model. “Đầy đủ” không có nghĩa phải có mọi loại tài liệu; đó là mức đủ căn cứ để mô tả các chiều đánh giá áp dụng. Tệp thiếu trang/khối, nguồn hết hiệu lực, chưa được cho phép hoặc mâu thuẫn chưa giải quyết phải được liệt kê và làm giảm phạm vi kết luận, không được coi như đã đọc đủ.

### Các tiêu chí đánh giá

Mỗi chiều có mức riêng `THẤP`, `TRUNG BÌNH`, `CAO` hoặc `CHƯA ĐỦ CĂN CỨ`, kèm dẫn chứng nguồn, giải thích, độ tin cậy, điểm chưa biết và tác động kiểm thử. Không cộng thành một điểm độ khó tổng, không suy luận chỉ từ số lượng trang/tệp/yêu cầu. Mức là nhận định định tính dựa trên dấu hiệu trong bảng; thiếu bằng chứng trực tiếp thì trả `CHƯA ĐỦ CĂN CỨ`, không tự đặt ngưỡng số. Tổ chức có thể cấu hình rubric bổ sung nhưng không được ghi đè dấu vết nguồn.

| Chiều | Dấu hiệu cần xem xét | Hệ quả có thể đề xuất cho kiểm thử |
| --- | --- | --- |
| 1. Quy mô phạm vi và phân rã | Module, luồng nghiệp vụ, vai trò, tiêu chí chấp nhận và hệ thống con có trong phạm vi; liên kết phụ thuộc; phần bao gồm/loại trừ rõ đến đâu. Đếm chỉ để mô tả, không tự biến số lượng thành độ khó. | Chia phạm vi theo module/luồng, ưu tiên rủi ro và lập mốc kiểm thử. |
| 2. Độ phức tạp quy tắc nghiệp vụ | Số nhánh có ý nghĩa, điều kiện kết hợp, ngoại lệ, trạng thái, thời điểm, chính sách và quan hệ giữa các quy tắc; quy tắc có xung đột hoặc phụ thuộc nhau không. | Thêm Scenario cho nhánh, tổ hợp, chuyển trạng thái, ngoại lệ và điều kiện biên có nguồn. |
| 3. Độ rõ và khả năng kiểm thử của yêu cầu | Mơ hồ, thiếu tác nhân/điều kiện/expected result, tiêu chí không đo được, mâu thuẫn giữa phiên bản hoặc thiếu nguồn; tỷ lệ yêu cầu có thể truy nguyên đến điều kiện kiểm thử. | Tạo câu hỏi BA, làm rõ tiêu chí trước khi sinh ca; không tự bù expected result. |
| 4. Tích hợp và phụ thuộc | API/dịch vụ/hệ thống bên ngoài, giao thức, đồng bộ/bất đồng bộ, hợp đồng dữ liệu, xác thực, giới hạn tốc độ, lỗi mạng, retry và quyền kiểm soát môi trường đối tác. | Bổ sung kiểm thử hợp đồng, lỗi/timeout, tương thích phiên bản, giả lập hoặc kiểm thử đầu-cuối khi có môi trường. |
| 5. Dữ liệu và vòng đời dữ liệu | Cấu trúc/quan hệ, khối lượng được nêu, biến đổi/migration, chất lượng, dữ liệu biên, dữ liệu lịch sử, tính nhất quán, lưu trữ/xóa và khả năng tạo/reset bộ dữ liệu. | Tạo Data Set tổng hợp, kiểm thử migration/toàn vẹn/biên; chỉ đề xuất tải dữ liệu khi có số liệu nguồn. |
| 6. Bảo mật, quyền riêng tư và tuân thủ | Danh tính, vai trò/quyền, dữ liệu nhạy cảm, bí mật, phân tách tenant, audit, lưu giữ/xóa, yêu cầu pháp lý hoặc chính sách được nêu và bề mặt truy cập. | Ưu tiên kiểm thử quyền, bảo vệ dữ liệu và audit; nêu điểm chưa rõ cho người phụ trách tuân thủ. |
| 7. Yêu cầu phi chức năng | Hiệu năng, tải, độ trễ, khả dụng, khả năng phục hồi, mở rộng, tương thích, khả năng tiếp cận, usability và mục tiêu đo được. | Đề xuất loại kiểm thử phi chức năng; không tự đặt ngưỡng, tải hoặc cam kết khi nguồn chưa nêu. |
| 8. Kiến trúc, nền tảng và môi trường | Thành phần triển khai, nền tảng/thiết bị/trình duyệt, cấu hình, feature flag, topology, sự khác nhau giữa staging/production và khả năng dựng môi trường. | Nêu ma trận môi trường cần có, biến cấu hình và rủi ro không tái tạo được production. |
| 9. Tổ hợp trạng thái và ma trận kiểm thử | Số chiều tổ hợp có căn cứ như vai trò × trạng thái × thiết bị × phiên bản; khả năng bùng nổ tổ hợp; nhánh thời gian, locale hoặc tương thích ngược. | Đề xuất phân lớp tương đương, biên, pairwise hoặc chọn ma trận có giải thích; QA xác nhận phạm vi áp dụng. |
| 10. Khả năng quan sát và tự động hóa | Có test hook, API ổn định, log/metric/trace, dữ liệu kiểm thử, sandbox, thiết lập/làm sạch và tính lặp lại; không suy đoán từ việc có công cụ. | Nêu phần tự động hóa khả thi, phần cần thao tác tay và khoảng trống quan sát cần khắc phục. |
| 11. Rủi ro kinh doanh và mức độ ảnh hưởng | Thiệt hại được mô tả khi lỗi xảy ra, số người/luồng bị ảnh hưởng, tính trọng yếu, phụ thuộc vận hành, mức chấp nhận rủi ro và tiêu chí phát hành đã duyệt. | Ưu tiên dựa trên rủi ro được khai báo; không tự gán mức nghiêm trọng hoặc quyết định phát hành. |
| 12. Bất định và thay đổi | Tần suất/yếu tố thay đổi nguồn, quyết định còn mở, phụ thuộc chưa chốt, công nghệ mới, lịch sử lỗi liên quan đã được xác nhận và tuổi của bằng chứng. | Đánh dấu cần rà lại, lập kịch bản thay đổi/hồi quy và tránh đóng băng giả định thiếu căn cứ. |

### Dùng lịch sử dự án khi nào

Mặc định AI-11 chỉ dùng dữ liệu của dự án hiện tại và các nguồn được người dùng cho phép. Có thể bật dữ liệu lịch sử khi kho dự án có nguồn được phép dùng cho mục đích này và kiểm tra chất lượng đạt chính sách tổ chức. Một dự án lịch sử chỉ đủ tin cậy khi: dự án đã hoàn tất/đóng; Test Plan và phạm vi được duyệt, có snapshot/version; Scenario/Test Case truy nguyên được về Requirement; kết quả Test Run và Defect có trạng thái cuối; giờ kế hoạch và giờ thực tế phân biệt được nếu dùng để ước lượng effort; dữ liệu không còn thiếu/chưa xử lý trọng yếu; loại công việc và nền tảng đủ tương đồng; quyền dùng lại và khử định danh đã được xác nhận.

Ngưỡng tối thiểu về độ đầy đủ, số dự án tương đồng và độ mới của dữ liệu phải do chính sách tổ chức cấu hình, không hardcode trong prompt. Nếu chưa có chính sách/ngưỡng, mẫu quá ít, các dự án không so sánh được hoặc dữ liệu sai lệch thì bỏ đối chiếu lịch sử, ghi rõ “chỉ dùng dữ liệu dự án hiện tại”. Khi dùng lịch sử, đầu ra chỉ nêu nhóm dự án tham chiếu, khoảng thời gian và giới hạn mẫu; không lộ tên khách hàng, nội dung bí mật, bảng lương hoặc xếp hạng nhân viên. Giờ thực tế lịch sử là tham khảo có sai số, không phải cam kết tiến độ/giá.

### Khả thi thương mại: tách khỏi độ khó

Giá khách hàng, ngân sách và biên chi phí **không làm thay đổi mức phức tạp kỹ thuật/nghiệp vụ trong 12 chiều**, nhưng là một phần của đánh giá **độ khó triển khai tổng thể** vì ràng buộc ngân sách có thể làm khó việc bố trí đủ nhân lực, thời gian và năng lực kiểm thử. Hệ thống phải trình bày hai góc nhìn riêng, không cộng thành một điểm mơ hồ: (1) độ phức tạp kỹ thuật/nghiệp vụ và (2) áp lực ngân sách/khả thi thương mại. Một dự án có thể kỹ thuật phức tạp nhưng nguồn lực phù hợp; hoặc kỹ thuật đơn giản nhưng khó triển khai nếu ngân sách không đáp ứng công việc cần làm.

AI-11 trình bày hai kết quả tách biệt: (1) hồ sơ độ khó kỹ thuật/nghiệp vụ theo 12 chiều phía trên; (2) tình trạng áp lực ngân sách/khả thi thương mại nếu có giá khách hàng, ước lượng giờ và bảng đơn giá hợp lệ. Phần thứ hai được tính ở backend tài chính có quyền, không gửi số tiền vào model. Nếu chưa có giờ/nhân lực được duyệt hoặc chưa có đơn giá còn hiệu lực, phải báo chưa đủ dữ liệu thay vì tự ước tính lợi nhuận. Giá thấp hơn dự toán nhân công là cảnh báo làm tăng rủi ro triển khai và cần người có quyền xem lại phạm vi, kế hoạch, thương lượng hoặc chấp nhận rủi ro; không được tự cắt kiểm thử bắt buộc, giảm chất lượng, đổi Test Plan hay phân công.

Giá hợp đồng và bảng lương chỉ được đọc/tính ở backend tài chính theo quyền hiện có. Không gửi giá chính xác, mức lương, tên nhân viên hay dữ liệu tài chính cá nhân vào model. Giao diện chỉ hiển thị chi tiết giá cho quyền tài chính; kết quả độ khó không phụ thuộc mức giá. Khi chuyển sang AI-07, hệ thống có thể so phương án nhân lực đã tính với giá/ngân sách theo chính sách quyền, đồng thời hiển thị đánh đổi riêng về năng lực, tải, rủi ro và chi phí.

### Đầu ra và nối sang các bước khác

Kết quả lưu thành bản đánh giá có phiên bản, phạm vi nguồn, các chiều và dẫn chứng, vấn đề chưa rõ, nguồn bị loại, lựa chọn có/không dùng lịch sử, thời điểm, model/prompt, trạng thái lỗi/đầy đủ và người yêu cầu. Trạng thái nguồn đổi làm bản đánh giá thành cũ và yêu cầu chạy lại trước khi dùng để lập kế hoạch. Không sửa Requirement, Test Plan, Scenario, Test Case hoặc phân công trong thao tác đánh giá.

Từ hồ sơ, giao diện mở thao tác riêng để người dùng bấm: đề xuất Test Plan (AI-03), phân tích nghĩa vụ (AI-02), sinh Scenario/Test Case (AI-04), xem ảnh hưởng/hồi quy (AI-05), hoặc so sánh phương án nhân lực/chi phí (AI-07). Mỗi thao tác lấy đúng nguồn/version và tiếp tục qua preview, chỉnh sửa, lưu nháp và duyệt như luồng hiện tại. AI-11 không tự sinh cả gói và không tự chọn/người giao việc. AI-07 dùng hồ sơ kỹ năng, vai trò, tải, khả dụng, giờ/công suất và đơn giá có quyền; không gửi mức lương hay giá khách hàng cho model.

## AI-12: Rà soát độ đầy đủ và đề xuất bổ sung hồ sơ dự án

AI-11 đánh giá độ phức tạp từ căn cứ hiện có; AI-12 giúp người dùng xác định hồ sơ đang thiếu loại nguồn, phần thông tin hoặc chi tiết nào để làm rõ Requirement và chuẩn bị kiểm thử. AI-12 không khẳng định dự án “đủ mọi tài liệu” theo mẫu cứng và không coi số lượng tệp là độ đầy đủ.

### Phần đã có và phần còn thiếu

Luồng nhập Requirement đã kiểm tra một số phần như tác nhân, quy tắc nghiệp vụ, tiêu chí chấp nhận và phụ thuộc; bản xem trước có thể nêu phần thiếu. Bộ đọc tài liệu cũng lưu trạng thái phân tích, khối/trang chưa xử lý và cảnh báo trích xuất. Đây là kiểm tra ở cấp tài liệu/Requirement. Chưa có một lượt rà soát tổng thể theo dự án để đối chiếu nhiều tài liệu, phiên bản và giai đoạn rồi đề xuất người dùng cần bổ sung nguồn hay chi tiết gì tiếp theo. AI-12 lấp phần còn thiếu đó, tái sử dụng các kiểm tra hiện hữu thay vì tạo luồng nhập hoặc kho dữ liệu mới.

### Thời điểm chạy và phạm vi

- AI-12 chỉ chạy khi người dùng bấm **Rà soát độ đầy đủ hồ sơ** sau khi tải tài liệu hoặc khi muốn kiểm tra lại; không tự chạy AI nền sau mỗi lần tải tệp.
- Người chạy chọn nguồn hoặc chấp nhận phạm vi mặc định gồm tài liệu hiện hành mà họ có quyền đọc và đã cho phép AI xử lý. Màn hình xác nhận tệp/phiên bản được xét, loại trừ và trạng thái chưa xử lý.
- Có thể chọn mục đích như làm rõ nghiệp vụ, tạo Requirement, lập Test Plan, thiết kế Scenario/Test Case, kiểm thử tích hợp hoặc chuẩn bị phát hành. Nếu chưa chọn, kết quả chỉ mô tả mức đủ căn cứ cho bước tiếp theo.
- Đánh giá xét nội dung trích xuất, Requirement đã duyệt, metadata loại nguồn do người dùng khai báo, phiên bản và cảnh báo parser. Dùng tìm kiếm hiện có khi cần; kiểm tra lại quyền và phiên bản trước khi tạo kết quả.

### Nhóm kiểm tra

1. **Nguồn và độ bao phủ:** nguồn nào đã có/chưa có theo phạm vi đã chọn; tài liệu trùng phiên bản, hết hiệu lực, bị loại, chưa cho phép AI hoặc còn xử lý dở. Các loại như đặc tả yêu cầu, quy trình nghiệp vụ, giao diện, API, dữ liệu, bảo mật, phi chức năng, môi trường và phát hành chỉ được đề xuất khi áp dụng cho dự án/giai đoạn.
2. **Thông tin trong nguồn:** mục tiêu/phạm vi, tác nhân, luồng chính và ngoại lệ, điều kiện, quy tắc, tiêu chí chấp nhận đo được, dữ liệu và phân quyền, tích hợp/phụ thuộc, xử lý lỗi, yêu cầu phi chức năng, môi trường, điều kiện bắt đầu/kết thúc kiểm thử. Không ép mọi loại tài liệu chứa mọi trường.
3. **Mâu thuẫn và chất lượng nguồn:** giá trị khác nhau giữa tài liệu/phiên bản, thuật ngữ không nhất quán, thông tin lỗi thời, bảng/hình/OCR không đọc đủ, phần không có vị trí nguồn xác thực. Phân biệt “không tìm thấy trong phạm vi đã đọc” với “không tồn tại trong toàn dự án”.
4. **Ảnh hưởng tới bước sau:** chỉ ra mục nào cản trở hoặc làm giảm độ tin cậy của Requirement, Test Plan, Scenario/Test Case hay Run; ai nên xử lý (BA, QA, chủ tài liệu hoặc người có thẩm quyền) và bước tiếp theo có thể làm được.

Mỗi mục có trạng thái `CÓ CĂN CỨ`, `MỘT PHẦN`, `CHƯA TÌM THẤY`, `MÂU THUẪN`, `NGUỒN CHƯA ĐỌC ĐỦ`, `KHÔNG ÁP DỤNG` hoặc `CẦN NGƯỜI XÁC NHẬN`. Chỉ dùng “chưa tìm thấy trong phạm vi đã đọc” sau khi đã xét toàn bộ phạm vi nguồn được chốt. Không chuyển sự im lặng của tài liệu thành khẳng định chắc chắn rằng nội dung bị thiếu.

### Đề xuất và giới hạn

- Mỗi đề xuất nêu thông tin cần bổ sung, lý do, bước nghiệp vụ bị ảnh hưởng, người có thể xác nhận, mức ưu tiên theo rủi ro/trở ngại, dẫn chứng ủng hộ hoặc cho thấy khoảng trống và nguồn/phiên bản liên quan.
- Có thể gợi ý câu hỏi hoặc mẫu nội dung cần xin; ví dụ “cần xác nhận thời hạn khóa tài khoản” thay vì tự điền một giá trị.
- Người dùng có thể đánh dấu cần bổ sung, đã có nguồn khác, không áp dụng, hoãn lại hoặc đã xử lý; lưu người quyết định và thời điểm. “Không áp dụng” cần lý do khi mục đó thuộc rubric đã chọn.
- Không tạo yêu cầu/tài liệu giả, không sửa hoặc duyệt Requirement, không yêu cầu mọi loại tài liệu, không chặn tải lên, không tự sinh Test Plan/Test Case và không tuyên bố bao phủ toàn dự án khi phạm vi/khả năng đọc chưa chứng minh điều đó.
- Không hiển thị một tỷ lệ “đầy đủ %” nếu chưa có mẫu số/rubric được người dùng hoặc tổ chức xác nhận. Có thể hiển thị số mục theo trạng thái và mức sẵn sàng cho bước được chọn, kèm phạm vi và giới hạn.

### Lưu kết quả, thay đổi nguồn và giao diện

Kết quả AI-12 lưu scope manifest/hash, phiên bản nguồn, giai đoạn, rubric, phát hiện, dẫn chứng, loại trừ, cảnh báo trích xuất, thời điểm, người chạy và phiên bản prompt/model. Nhấp lặp cùng phạm vi có thể dùng lại kết quả còn hiệu lực. Tài liệu, Requirement hoặc quyền đổi thì kết quả cũ thành hết hiệu lực; kiểm tra lại quyền trước khi trả nội dung hoặc mở dẫn chứng.

Giao diện chia thành **Đã có căn cứ**, **Cần bổ sung/làm rõ**, **Mâu thuẫn**, **Chưa đọc đủ** và **Không áp dụng**; có bộ lọc theo loại nguồn/giai đoạn/mức ảnh hưởng. Chọn một mục mở đúng trích dẫn, tài liệu và vị trí nếu có; hành động tiếp theo điều hướng sang luồng nhập/tạo Requirement hoặc bổ sung tài liệu hiện tại. Nhãn và hướng dẫn dùng ngôn ngữ người dùng; chi tiết parser nằm trong phần mở rộng.

### Kiểm chứng AI-12

Kiểm tra hồ sơ đầy đủ, thiếu từng loại nguồn, thiếu chi tiết giữa nhiều tệp, tài liệu trùng/phiên bản cũ, mâu thuẫn, nguồn bị thu hồi quyền, scan/bảng/hình đọc thiếu, dự án không cần một nhóm tài liệu và câu trả lời nằm ngoài nguồn. Mọi phát hiện phải mở được nguồn thật hoặc ghi rõ chưa có nguồn. Thử đổi revision/quyền trong lúc chạy, nhấp lặp, provider lỗi và worker khởi động lại; xác nhận AI-12 không tự tạo/sửa/duyệt dữ liệu nghiệp vụ. Kết quả phải phân biệt mục thiếu thật với nguồn chưa đọc được và lựa chọn không áp dụng.

### Hợp đồng dùng chung cho 10 năng lực AI, AI-11 và AI-12

- Mỗi thao tác phải kiểm tra quyền, trạng thái và phiên bản nguồn tại backend trước khi gọi model; kết quả lưu cùng ID/version nguồn, prompt/model version, thời lượng, trạng thái, cảnh báo và người yêu cầu.
- Màn hình phân biệt rõ nội dung AI đề xuất với nội dung do người dùng viết; người dùng có thể bỏ qua đề xuất. Lỗi provider, nguồn thiếu, trích xuất chưa đầy đủ hoặc nguồn đổi phải hiện là chưa hoàn tất/cần chạy lại, không báo thành công giả.
- Không gửi bảng lương, mức lương, giá hợp đồng hoặc dữ liệu tài chính cá nhân sang model. Backend dùng bảng giá có quyền, giờ công, tiền tệ/ngày hiệu lực và dữ liệu giá trị/ngân sách được duyệt để tính các phương án; nếu cần AI diễn giải, chỉ gửi số tổng hợp đã loại định danh sau kiểm tra quyền. Thiếu dữ liệu đầu vào thì báo chưa đủ cơ sở, không ước đoán.
- Tách hai câu hỏi: “ai đủ năng lực nhận việc?” và “phương án nhân lực nào phù hợp với bài toán kinh tế của dự án?”. Câu đầu dùng ngưỡng năng lực/role xác nhận, khả dụng, tải và xung đột lịch; câu sau so tổng độ bao phủ năng lực, giờ công, chi phí, rủi ro và ngân sách/giá trị dự án. Không dùng lương như đại diện cho kỹ năng, cấp bậc hay chất lượng; không loại người chỉ vì thiếu dòng lương. Không mặc định chọn người rẻ nhất hoặc người đắt nhất.
- Đánh giá phương án theo thứ tự: (1) thỏa điều kiện bắt buộc về vai trò/kỹ năng và khả dụng; (2) đủ độ bao phủ cho phạm vi, mức rủi ro và thời hạn; (3) không vượt năng lực phân bổ đã xác nhận; (4) so chi phí nhân công dự kiến với ngân sách/giá trị và các ngưỡng lợi nhuận do tổ chức cấu hình. Trả nhiều phương án khả thi cùng chi phí, phần thiếu, rủi ro và lý do; không tự giao việc. Các ngưỡng kinh doanh do người có quyền cấu hình, không hardcode.
- Đề xuất ở cấp Test Case chỉ chọn trong nhóm đủ điều kiện theo kỹ năng/role, tải và khả dụng; bảng lương không tham gia xếp hạng ca đơn lẻ. Đề xuất ở cấp Test Plan/dự án mới được so sánh chi phí giữa phương án nhân lực vì có giờ công, phạm vi và bối cảnh ngân sách. Chi tiết lương chỉ hiện cho quyền tài chính; người quản lý dự án chỉ xem tổng hợp/nhãn ngân sách nếu chính sách cho phép.
- Phản hồi AI được lưu phục vụ báo cáo chất lượng có quyền đọc; không dùng để tự học. Mọi thay đổi thành dữ liệu nghiệp vụ phải qua thao tác lưu/duyệt thông thường và ghi audit.
- Tái sử dụng embedding/search đã có khi cần tìm ứng viên. Không tạo lượt embedding cosine thứ hai cho cùng đầu vào chỉ để tính lại độ gần; giữ kiểm tra mã chính xác, nguồn, phiên bản và quyền.

### Phạm vi lập chỉ mục Qdrant cho 10 năng lực AI, AI-11 và AI-12

Qdrant là chỉ mục tìm kiếm vector và từ khóa, không phải nơi lưu chính, không phải cơ sở dữ liệu cây. MongoDB giữ bản ghi nghiệp vụ/version; Neo4j giữ quan hệ; Qdrant giữ các đoạn nội dung cần tìm tương tự cùng ID tham chiếu và payload lọc. Với dữ liệu không có nhu cầu truy xuất ngữ nghĩa, không lập chỉ mục chỉ để “có trong Qdrant”.

| Năng lực | Nên đưa vào Qdrant | Không đưa vào Qdrant |
| --- | --- | --- |
| AI-01 Requirement | Tài liệu nguồn và Requirement đã duyệt (đang có). | Nhận xét/phân tích AI tạm thời; dùng DB nghiệp vụ và trỏ về Requirement nguồn. |
| AI-02 Nghĩa vụ bao phủ | Điều kiện kiểm thử đã duyệt và nội dung tiêu chí (đang có thể truy nguyên nguồn). | Trạng thái độ phủ dạng snapshot; tính từ liên kết DB/graph để không trả số cũ. |
| AI-03 Test Plan | Chỉ mục tùy chọn cho mục tiêu, phạm vi, cách tiếp cận và rủi ro của Plan đã duyệt, nếu có nhu cầu tìm Plan tương tự. | Thành viên, giờ phân bổ, đơn giá, dự toán, ngày lịch chi tiết, Plan nháp và snapshot thực thi. |
| AI-04 Scenario/Test Case | Test Case đã duyệt đang được lập chỉ mục; nên bổ sung Scenario đã duyệt để tìm kịch bản tương tự. | Bản nháp AI, đề xuất bị từ chối và phiên bản chưa duyệt. |
| AI-05 Ảnh hưởng thay đổi | Tái dùng Requirement, Scenario và Test Case đã duyệt; không lập chỉ mục báo cáo ảnh hưởng tạm. | Đồ thị ảnh hưởng/snapshot đề xuất; truy vấn lại quan hệ và revision hiện hành từ DB/Neo4j. |
| AI-06 Dữ liệu kiểm thử | Có thể lập chỉ mục mô tả schema/loại dữ liệu đã duyệt nếu cần tìm Data Set theo mục đích. | Giá trị dữ liệu thật, tài khoản, token, PII, dữ liệu bí mật hoặc giá trị sinh riêng cho một lượt chạy. |
| AI-07 Nhân sự/dự toán | Không cần Qdrant; tra kỹ năng/kinh nghiệm đã xác nhận, membership, tải, khả dụng, đơn giá và điều khoản dự án bằng DB có quyền; tính phương án bằng bộ tối ưu xác định. | CV gốc, kỹ năng cá nhân, availability, tải, bảng lương, giá khách hàng và phép tính dự toán. Không đưa dữ liệu đó vào payload Qdrant. |
| AI-08 Hỗ trợ thực thi | Defect đã được làm sạch thông tin nhạy cảm (đang có thể lập chỉ mục) để tìm lỗi tương tự. | Actual Result/evidence của lần chạy, dữ liệu chạy, log có bí mật và trạng thái PASS/FAIL cũ. |
| AI-09 Báo cáo | Không cần Qdrant; số liệu lấy từ snapshot Run/Defect/coverage. Có thể lập chỉ mục bài học đã được duyệt riêng nếu dự án cần tìm lại kinh nghiệm. | Báo cáo nháp, số liệu tổng hợp cũ và kết luận chưa duyệt. |
| AI-10 Phản hồi chất lượng | Không cần Qdrant; báo cáo chấp nhận/sửa/từ chối lấy từ bảng ghi nhận và tổng hợp trong DB. | Phản hồi thô gắn với cá nhân, nội dung đề xuất bị từ chối và dữ liệu dùng để huấn luyện model. |
| AI-11 Độ khó dự án | Không cần Qdrant riêng; tái dùng DB/graph và retrieval có quyền để lấy nguồn hiện tại hoặc dự án lịch sử đủ điều kiện. | Điểm đánh giá tạm, lịch sử bị loại/chưa duyệt, thông tin khách hàng/nhân viên, bảng lương và mọi dữ liệu chưa được phép so sánh. |
| AI-12 Độ đầy đủ hồ sơ | Tái sử dụng chỉ mục tài liệu/Requirement hiện hành để tìm nguồn theo quyền. | Bản rà soát AI tạm, mục “còn thiếu” chưa được người dùng xác nhận và payload lặp lại chỉ để lưu kết quả. |

Scenario đã duyệt được lập chỉ mục bằng `artifact_type=test_scenario`; bản nháp không được lập chỉ mục và khi lưu trữ thì gỡ khỏi chỉ mục. Kết quả lập chỉ mục được ghi thành `index_status`; lỗi chỉ mục không làm mất bản nghiệp vụ. Plan chỉ được cân nhắc lập chỉ mục nếu có nhu cầu tìm Plan tương tự; hiện mặc định chưa cần. Mỗi điểm Qdrant có `project_id`, `artifact_type`, `artifact_id`, `artifact_version_id`, trạng thái hiệu lực, hash nội dung và thông tin mô hình embedding; nguồn tài liệu bổ sung vị trí trang/khối. Không đưa payload tài chính hay hồ sơ nhân sự vào metadata. Trước khi trả kết quả phải lọc project/quyền/trạng thái và đọc lại bản ghi có thẩm quyền từ DB.

### Cách xét phương án nhân lực và chi phí

Phân bổ là bài toán tối ưu có ràng buộc, không phải quy tắc “lương cao thì dự án lớn”. Trước tiên loại các phương án không đạt vai trò/kỹ năng bắt buộc, không còn khả dụng hoặc vượt tải phân bổ đã xác nhận. Với các phương án còn lại, đánh giá cả nhóm theo độ bao phủ kỹ năng, kinh nghiệm liên quan đã xác nhận, tính liên tục, rủi ro/phạm vi dự án, thời hạn, giờ công, chi phí theo đơn giá có hiệu lực, ngân sách và giá trị/giá khách hàng. Dự án có giá trị hoặc độ rủi ro cao có thể cần người giàu kinh nghiệm hơn, nhưng phải có bằng chứng năng lực và còn khả dụng; mức lương chỉ tác động đến chi phí phương án.

Kết quả cần so sánh tối thiểu: phương án đủ năng lực với chi phí thấp hơn; phương án tăng độ phủ/chuyên môn hoặc giảm rủi ro; và trạng thái “không có phương án đạt” khi ngân sách/nhân lực không đáp ứng. Mỗi phương án hiển thị các giả định, giờ công, phần trăm/ngưỡng ngân sách nếu được phép, kỹ năng còn thiếu, xung đột tải và đánh đổi chất lượng/chi phí. Giá khách hàng bằng chi phí nhân công không đồng nghĩa dự án hòa vốn vì có thể còn chi phí khác, thuế và biên lợi nhuận; không gọi đó là “giá hợp lý” nếu thiếu các dữ liệu này. Con người có quyền phê duyệt và sửa phân bổ. Thay đổi bảng lương, giá khách hàng, giờ công, năng lực hoặc khả dụng làm phương án hết hiệu lực và cần tính lại; lịch sử phương án đã duyệt được giữ nguyên.

### Nối với mã hiện có và phần được nâng cấp

Các năng lực Requirement quality, phân tích điều kiện/độ phủ, sinh Scenario/Test Case, phân tích ảnh hưởng, hồ sơ CV/đề xuất người, trợ lý báo cáo, Test Run và tính dự toán đã có module hoặc API tương ứng. Đợt nâng cấp này nối chúng vào quy trình thống nhất, giữ quyền và trạng thái duyệt hiện hữu; không nhân đôi module. Kịch bản AI được chuyển sang cùng quy tắc preview → chọn → lưu nháp như Test Case. Đề xuất người phụ trách tách hoàn toàn khỏi đơn giá; dự toán vẫn nằm ở API tài chính đang giới hạn Admin. Các khả năng chưa có nút/đường dẫn trong màn hình hiện hữu không được coi là đã hoàn tất chỉ vì backend có một API.

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
