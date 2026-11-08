# Veriq: quy trình quản lý kiểm thử cho một dự án

> **Cách dùng tài liệu:** Phần 1 là bài nói có thể đọc trực tiếp. Phần 2 là ghi chú để trả lời câu hỏi. Đây là mô tả nghiệp vụ mục tiêu; khi thuyết trình về chức năng đã chạy được, chỉ trình diễn những phần đã kiểm tra trên phiên bản hiện tại.

## 1. Bài trình bày

Em xin giới thiệu Veriq, một hệ thống giúp nhóm dự án quản lý công việc kiểm thử và theo dõi căn cứ của từng quyết định.

Trong một dự án, thông tin thường nằm rải rác trong nhiều tài liệu. Nếu chỉ lưu tài liệu mà không nối chúng với yêu cầu, ca kiểm thử và kết quả chạy, nhóm sẽ khó biết mình đã kiểm tra đủ chưa, ai chịu trách nhiệm, hoặc một kết quả đang dựa trên phiên bản yêu cầu nào. Veriq giải quyết việc đó bằng cách liên kết các bước trong cùng một dự án.

Quy trình bắt đầu từ tài liệu và thông tin dự án. Người dùng tải tài liệu lên, xem lại nội dung được trích xuất và kiểm tra cảnh báo nếu có trang hoặc phần chưa đọc được. Các quy tắc nghiệp vụ (BR) có thể được AI trích xuất hoặc đề xuất khi người dùng chủ động bấm chức năng tương ứng; AI không tự sinh BR ngay khi tải tệp. Người được giao phụ trách nghiệp vụ kiểm tra và xác nhận nội dung; người có capability rà soát kiểm thử đánh giá yêu cầu có đủ rõ và có thể kiểm thử hay chưa. Những điểm thiếu hoặc mâu thuẫn được đưa thành câu hỏi để người được chỉ định trả lời; hệ thống không tự đoán câu trả lời.

Sau khi yêu cầu được xác nhận, người có capability lập kế hoạch kiểm thử tạo **Kế hoạch kiểm thử**. Kế hoạch nêu rõ sẽ kiểm tra phần nào, mục tiêu là gì, dùng cách kiểm thử nào, cần môi trường và dữ liệu gì, ai tham gia, khi nào thực hiện, điều kiện bắt đầu và điều kiện kết thúc ra sao, cũng như rủi ro và cách xử lý lỗi.

Từ kế hoạch, người được phân công thiết kế xác định **Tình huống kiểm thử** — những hành vi cần xác minh. Mỗi tình huống được triển khai thành một hoặc nhiều **Ca kiểm thử**. Ca kiểm thử ghi điều kiện ban đầu, dữ liệu, từng bước thao tác và kết quả mong đợi. Người có capability rà soát kiểm tra, chỉnh sửa hoặc duyệt nội dung trước khi đưa vào sử dụng.

Khi sẵn sàng kiểm thử, người có capability điều phối tạo **Đợt chạy kiểm thử** và chọn phiên bản ca cần chạy, môi trường, bản dựng phần mềm cùng người thực hiện. Người thực thi được giao chạy ca, ghi kết quả thực tế và đính kèm bằng chứng. Nếu phát hiện lỗi, nhóm ghi nhận lỗi, xử lý, kiểm tra lại và giữ lịch sử của từng lần chạy.

Cuối cùng, **Báo cáo kiểm thử** tổng hợp phạm vi đã chạy, phần chưa chạy, kết quả đạt hoặc không đạt, độ bao phủ yêu cầu và các lỗi còn mở. Người có trách nhiệm dựa trên dữ liệu đó để quyết định bước tiếp theo. Veriq không tự quyết định phát hành thay cho nhóm dự án.

Vì vậy, luồng chính là: **Tài liệu và bối cảnh dự án → Requirement → Test Plan → Test Scenario → Test Case → Test Run → Test Report**. Có thể lần từ một kết quả chạy về ca kiểm thử, tình huống, yêu cầu và tài liệu làm căn cứ.

AI trong Veriq là trợ lý do người dùng chủ động yêu cầu. Người dùng chọn chức năng rồi bấm chạy khi cần. AI có thể đọc, tóm tắt, tìm chỗ thiếu, đề xuất Requirement/BR, kế hoạch hoặc ca kiểm thử, và phân tích ảnh hưởng; người có quyền sẽ xem, sửa, chấp nhận hoặc từ chối. AI không tự duyệt yêu cầu, tự công bố ca kiểm thử hay tự ghi kết quả thực thi. Một số việc nền như chuyển đổi tệp hoặc cập nhật chỉ mục có thể chạy sau khi người dùng khởi động thao tác tương ứng; điều đó không có nghĩa AI tự quyết toàn bộ quy trình.

Veriq cũng lưu lịch sử phiên bản. Nếu yêu cầu hoặc ca kiểm thử thay đổi, kết quả cũ vẫn gắn với phiên bản đã chạy trước đó. Nhờ vậy, nhóm không nhầm kết quả cũ với lần kiểm thử mới.

## 2. Ghi chú để trả lời câu hỏi

### Vì sao có cả Test Plan, Scenario và Test Case?

- **Test Plan** trả lời: dự án sẽ kiểm thử phạm vi nào, bằng cách nào, với nguồn lực và điều kiện gì.
- **Test Scenario** trả lời: cần xác minh hành vi hoặc tình huống nào.
- **Test Case** trả lời: người kiểm thử thực hiện những bước cụ thể nào và kết quả mong đợi là gì.
- **Test Run** ghi lại một lần thực hiện các phiên bản ca đã chọn.
- **Test Report** tổng hợp kết quả của phạm vi chạy đã xác định.

Đây là các mức thông tin khác nhau. Scenario không thay cho Test Plan; Test Case cũng không thay cho Scenario. Một Scenario có thể có nhiều Test Case, và một Test Case có thể được dùng lại trong nhiều Test Run. Mỗi lần chạy vẫn có kết quả riêng.

### Test Plan gồm những gì?

Người được giao lập kế hoạch chọn các nội dung phù hợp với dự án, thường gồm:

- Phạm vi kiểm thử và phần không kiểm thử.
- Mục tiêu, chiến lược và cách tiếp cận.
- Cấp độ, loại kiểm thử và nguồn lực tham gia.
- Môi trường, dữ liệu, công cụ và phụ thuộc.
- Điều kiện bắt đầu và điều kiện kết thúc.
- Lịch thực hiện, mốc và ước lượng.
- Rủi ro, cách quản lý lỗi và sản phẩm bàn giao.

Không phải dự án nào cũng cần mọi loại kiểm thử. Người phụ trách kế hoạch ghi rõ lý do chọn hoặc loại trừ nội dung quan trọng.

### Dự án cần nhập những tài liệu nào?

Tùy sản phẩm, nhóm có thể cung cấp đặc tả yêu cầu, quy tắc nghiệp vụ, User Story và tiêu chí chấp nhận; tài liệu API; thiết kế giao diện; kiến trúc và tích hợp; mô hình dữ liệu; yêu cầu bảo mật hoặc hiệu năng; hướng dẫn vận hành; thay đổi phiên bản; và lỗi đã biết.

Không bắt buộc dự án nào cũng phải có đủ mọi loại tài liệu. Điều quan trọng là có đủ thông tin để hiểu hành vi cần xây dựng, điều kiện áp dụng, dữ liệu, ngoại lệ, quyền và cách xác nhận kết quả. AI có thể chỉ ra phần có vẻ thiếu, nhưng người được giao chịu trách nhiệm nghiệp vụ mới xác nhận nội dung.

Tải được một tệp không đồng nghĩa đã đọc hết tệp. Nếu tài liệu bị hỏng, scan kém, có bảng hoặc hình chưa trích xuất được, hệ thống phải nêu rõ phần chưa xử lý để người dùng bổ sung hoặc kiểm tra thủ công.

### Ai làm gì?

| Vai trò | Trách nhiệm |
|---|---|
| Người phụ trách Requirement | Làm rõ nghiệp vụ và chịu trách nhiệm nội dung Requirement theo phân công. |
| Người có capability rà soát kiểm thử | Rà soát Requirement, Test Plan, Scenario và Test Case trong phạm vi được giao; duyệt độc lập khi có quyền và được chỉ định. |
| Người thực thi được giao | Chạy ca, ghi kết quả thực tế, lưu bằng chứng và báo lỗi; không ghi kết quả thay người khác hoặc tự sửa baseline đã duyệt. |
| Người xử lý phát triển hoặc lỗi | Xử lý công việc kỹ thuật được giao và cập nhật trạng thái theo workflow; không tự xác nhận retest nếu không có capability tương ứng. |
| Quản trị viên nền tảng | Quản trị tài khoản và cấu hình nền tảng theo quyền được cấp; không mặc nhiên có quyền nghiệp vụ của dự án. |

Quyền được kiểm tra ở máy chủ cho từng thao tác. Việc ẩn nút trên giao diện không thay thế kiểm tra quyền của API. Một người có thể giữ nhiều vai trò nếu được cấp rõ ràng; quyền của vai trò này không tự động kéo theo quyền của vai trò khác.

### AI hỗ trợ những việc nào?

Các năng lực dưới đây là danh mục nghiệp vụ AI được thiết kế cho Veriq. Mỗi năng lực phải có thao tác, quyền, dữ liệu đầu vào và cách người dùng xem lại kết quả rõ ràng. Không nên giới thiệu một năng lực là đã hoàn tất nếu chưa xác minh trên phiên bản đang trình diễn.

| Mã | AI hỗ trợ | Người dùng quyết định |
|---|---|---|
| AI-01 | Tìm Requirement mơ hồ, thiếu điều kiện, ngoại lệ hoặc mâu thuẫn; đề xuất câu hỏi làm rõ có dẫn nguồn. | Người được giao phụ trách Requirement sửa/trả lời; người có quyền rà soát kiểm tra theo capability. |
| AI-02 | Đối chiếu yêu cầu và tiêu chí với Scenario/Test Case để chỉ ra phần đã có, chưa có hoặc chưa đủ căn cứ. | Người phụ trách thiết kế xác nhận phạm vi cần kiểm thử. |
| AI-03 | Đề xuất nội dung cho các mục của Test Plan từ nguồn đã chọn. | Người được giao chỉnh sửa, lưu nháp; người có quyền và được chỉ định mới duyệt. |
| AI-04 | Đề xuất Scenario và Test Case có liên kết Requirement, tiêu chí và nguồn; cảnh báo nội dung tương tự. | Người phụ trách thiết kế chọn, ghép, sửa; người có quyền và được chỉ định duyệt. |
| AI-05 | Phân tích ảnh hưởng khi Requirement hoặc tài liệu đổi; chỉ ra tài sản kiểm thử cần xem lại. | Người được giao xác nhận phạm vi và tạo phiên bản mới khi có quyền. |
| AI-06 | Đề xuất bộ dữ liệu kiểm thử tổng hợp, gồm trường hợp biên và trường hợp lỗi. | Người được giao kiểm tra trước khi lưu hoặc sử dụng. |
| AI-07 | Gợi ý người phụ trách ca hoặc phương án nhân lực theo kỹ năng đã xác nhận, vai trò, khả dụng và tải công việc. | Người có quyền chọn hoặc sửa phân công. Người chạy Test Run được phân riêng. |
| AI-08 | Giải thích bước kiểm thử và gợi ý nội dung Defect dựa trên kết quả đã nhập. | Người thực thi xác nhận kết quả và nội dung lỗi. |
| AI-09 | Soạn phần diễn giải báo cáo từ số liệu và snapshot đã lưu. | Người rà soát được chỉ định xem lại báo cáo; dữ liệu gốc không bị AI thay đổi. |
| AI-10 | Tổng hợp chất lượng các đề xuất AI đã được chấp nhận, sửa hoặc từ chối. | Người quản lý xem số liệu; phản hồi không tự huấn luyện hay đổi hành vi mô hình. |
| AI-11 | Đánh giá mức độ khó và mức sẵn sàng kiểm thử của dự án theo nhiều chiều. | Người dùng xem từng căn cứ rồi bấm riêng để yêu cầu tạo Plan, Scenario/Case hoặc phương án nhân lực. |
| AI-12 | Rà mức đầy đủ của bộ tài liệu theo loại dự án; chỉ ra tài liệu, thông tin hoặc quyết định có thể còn thiếu. | Người phụ trách nghiệp vụ và người phụ trách kiểm thử xác nhận mục nào thực sự áp dụng, rồi bổ sung nguồn theo quyền được cấp. |

Mọi đề xuất cần chỉ ra căn cứ. Nếu không có nguồn phù hợp, tài liệu chưa đọc đủ hoặc các nguồn mâu thuẫn, AI phải thể hiện giới hạn thay vì tự điền dữ kiện.

### AI-11 đánh giá độ khó như thế nào?

AI-11 không kết luận bằng một điểm tổng duy nhất. Hồ sơ nên trình bày từng chiều áp dụng, ví dụ:

- Độ rõ và độ đầy đủ của tài liệu.
- Số lượng quy tắc, ngoại lệ và luồng nghiệp vụ.
- Độ phức tạp tích hợp và phụ thuộc bên ngoài.
- Độ nhạy, khối lượng và chất lượng dữ liệu.
- Yêu cầu bảo mật, hiệu năng, độ sẵn sàng và tuân thủ.
- Phạm vi ảnh hưởng, nền tảng và môi trường kiểm thử.
- Thời hạn, nguồn lực và các rủi ro đã biết.
- Mức phù hợp giữa phạm vi, giá khách hàng và ngân sách dự kiến.

Giá khách hàng là một đầu vào để xem xét tính khả thi về phạm vi, thời gian và chi phí; giá cao hay thấp tự nó không chứng minh dự án dễ hay khó. Mặc định chỉ phân tích dự án hiện tại. Dữ liệu dự án cũ chỉ được dùng nếu đã được cho phép, đủ tin cậy và tương đồng.

### CV, kỹ năng và bảng lương dùng ra sao?

CV có thể giúp trích xuất kỹ năng, công cụ, lĩnh vực và kinh nghiệm liên quan. Nhân viên cần xem và xác nhận thông tin trước khi hệ thống dùng để gợi ý. AI không được biến việc một người từng dùng công cụ thành kết luận rằng người đó thành thạo.

Bảng lương là dữ liệu nhạy cảm. Chỉ người có capability tương ứng trong phạm vi được phép mới được nhập và xem đơn giá; không suy quyền này từ tên role. Bảng có kỳ hiệu lực; hệ thống cần xem trước dữ liệu, phát hiện dòng trùng hoặc kỳ bị chồng lấn, hỗ trợ nhập bổ sung có kiểm soát và lưu dấu người nhập. Bảng lương hỗ trợ dự toán chi phí, không phải thước đo năng lực.

Khi đề xuất nhân sự, cần xét riêng năng lực đã xác nhận, vai trò phù hợp, mức sẵn sàng, tải công việc, giới hạn tham gia nhiều dự án và ngân sách. Không tự gán người lương cao cho dự án lớn. Người quản lý xem lý do và quyết định phương án cuối cùng.

Phân công **người phụ trách Test Case** khác với phân công **người thực thi Test Run**. Ca có thể có người phụ trách nội dung; mỗi đợt chạy có người thực thi và kết quả riêng.

### Tài liệu được tìm trong Qdrant như thế nào?

Qdrant là nơi lưu vector để tìm các đoạn có nội dung gần nghĩa. Nó không lưu tệp gốc và không tự biến tài liệu thành cây. Tệp gốc và cấu trúc tài liệu thuộc kho lưu trữ của ứng dụng; Qdrant giữ từng đoạn đã chọn để tìm kiếm cùng các mã định danh và thuộc tính cần thiết.

Một đoạn cần liên kết về dự án, tài liệu, phiên bản, mã đoạn và loại nội dung. Khi nguồn cung cấp được, có thể lưu thêm mục cha, thứ tự, trang hoặc vị trí, tiêu đề, trạng thái xử lý và thông tin cần để kiểm tra quyền. Không tạo số trang hay tọa độ nếu công cụ trích xuất không xác định được.

Khi tìm được đoạn, ứng dụng dùng các mã định danh để mở đúng tài liệu và phiên bản, rồi kiểm tra quyền trước khi trả nội dung. Nếu tài liệu bị cập nhật hoặc thu hồi quyền, kết quả cũ không được tiếp tục dùng như nguồn hiện hành.

### Các trường hợp cần xử lý rõ

- **Thiếu thông tin:** tạo câu hỏi hoặc mục cần bổ sung; không tự suy diễn yêu cầu.
- **Tài liệu mâu thuẫn:** chỉ ra các nguồn và phiên bản liên quan; người có trách nhiệm quyết định nguồn đúng.
- **Tệp đọc lỗi hoặc chỉ đọc được một phần:** báo phần chưa xử lý; không gọi là đã phân tích đầy đủ.
- **Nguồn thay đổi sau khi AI chạy:** đánh dấu đề xuất cũ cần đối chiếu lại.
- **Người dùng không đủ quyền:** chặn tại API và không để nội dung bị lộ qua kết quả AI hoặc tìm kiếm.
- **AI hoặc dịch vụ gặp lỗi:** giữ bản nháp/kết quả tốt trước đó, báo lỗi và cho phép thử lại an toàn.
- **Ca được dùng lại:** giữ nguyên phiên bản và kết quả của lần chạy cũ; lần chạy mới có kết quả mới.
- **Không có người phù hợp:** để trạng thái chưa phân công và nêu lý do; không tự chọn người gần đúng.

### Kịch bản trình diễn ngắn

1. Mở một tài liệu và chỉ ra một yêu cầu có căn cứ trong tài liệu đó.
2. Mở Requirement, Test Plan, Scenario và Test Case được liên kết.
3. Cho xem phiên bản ca được chọn trong một Test Run.
4. Ghi một kết quả chạy và mở báo cáo tương ứng.
5. Nếu trình diễn AI, chủ động bấm một chức năng, xem nguồn dẫn và cho thấy người có quyền có thể sửa hoặc từ chối đề xuất.

Chỉ giới thiệu thao tác thực sự chạy được trên môi trường demo. Phần mới ở mức thiết kế cần được gọi là kế hoạch, không trình bày như chức năng đã nghiệm thu.
