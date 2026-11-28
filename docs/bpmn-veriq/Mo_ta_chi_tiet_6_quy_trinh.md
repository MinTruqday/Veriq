# Mô tả chi tiết sáu quy trình nghiệp vụ

Tài liệu diễn giải sáu sơ đồ theo từng bước. Tùy nội dung, mỗi bước nêu người thực hiện, thông tin đầu vào, cách xử lý, kết quả và điều kiện phát sinh. Các luồng được đối chiếu với hệ thống và đặc tả nghiệp vụ của dự án; phần nào không có căn cứ sẽ không được tự thêm thành quy định.

## Vai trò và thuật ngữ

Các vai trò trong quy trình gồm BA, Tester, Admin và Hệ thống. BA phụ trách yêu cầu; Tester lập kế hoạch, thiết kế ca và thực hiện kiểm thử; Admin đảm nhiệm các bước xét duyệt hoặc quản trị theo đặc tả. Riêng ca kiểm thử do Admin phê duyệt. Tester không tự phê duyệt ca, và thao tác gửi ca chỉ chuyển hồ sơ sang bước chờ Admin xem xét. Ở quy trình xử lý lỗi, người khắc phục là người được giao phụ trách; đây là phân công công việc, không phải chức danh riêng.

Một số thuật ngữ được dùng thống nhất: **phiên bản chuẩn** là phiên bản yêu cầu đã được rà soát và ghi nhận làm căn cứ cho các bước sau; **ảnh chụp phạm vi** là thông tin cố định về phạm vi kế hoạch đã duyệt; **kiểm tra tự động** là việc hệ thống rà cấu trúc và mức đầy đủ của nội dung; **truy vết** là khả năng lần theo liên hệ giữa yêu cầu, ca kiểm thử, kết quả và lỗi; **giao dịch dữ liệu** là nhóm thao tác được ghi nhận cùng nhau để tránh lưu dữ liệu dở dang nếu có sự cố.

## 3.2.1 Quy trình nhập tài liệu và trích xuất yêu cầu

BA cung cấp tài liệu hoặc nội dung nguồn để Hệ thống kiểm tra định dạng, dung lượng, nội dung và khả năng tài liệu đã được nhập trước đó. Khi đầu vào hợp lệ, hệ thống lập hồ sơ và trích xuất các yêu cầu đề xuất. Đây chưa phải yêu cầu chính thức: BA cần đối chiếu với tài liệu gốc, xử lý nội dung trùng, chỉnh sửa, gộp, tách hoặc loại bỏ mục chưa phù hợp. Trước khi ghi dữ liệu, Hệ thống kiểm tra lại xung đột và chỉ tạo những yêu cầu được chọn; các yêu cầu mới tiếp tục sang quy trình soạn thảo và phê duyệt.

**Tác nhân:** BA thực hiện nhập và rà soát nội dung yêu cầu theo vai trò nghiệp vụ; Hệ thống kiểm tra quyền thao tác nhập/rà soát trước khi xử lý.

### Bước 1. Cung cấp tài liệu hoặc nội dung nguồn

**Tác nhân:** BA và Hệ thống

**Đầu vào:** Tệp tài liệu hoặc nội dung do người dùng gửi qua chức năng tiếp nhận dữ liệu nhập yêu cầu.

**Xử lý:** Hệ thống kiểm tra dữ liệu nhận vào. Với đường tải tệp, các điều kiện định dạng được hỗ trợ, nội dung rỗng và giới hạn dung lượng được xác thực tại tuyến nhập. Hệ thống tính dấu vân tay nội dung và kiểm tra khả năng tài liệu đã được nhập trước đó. Nếu phát hiện trường hợp trùng cần quyết định, người dùng phải xác nhận hoặc cung cấp thông tin xác nhận phù hợp trước khi hệ thống tiếp tục.

**Đầu ra:** Đầu vào hợp lệ để tạo hồ sơ tài liệu; hoặc thông báo lỗi/đòi xác nhận trùng, chưa tạo hồ sơ nhập tài liệu thành công.

**Nhánh lỗi/điều kiện:** Nếu tệp sai định dạng, rỗng, vượt giới hạn hoặc bị nhận diện trùng mà chưa có xác nhận phù hợp, hệ thống dừng trước khi tạo hồ sơ nhập tài liệu.

### Bước 2. Tạo hồ sơ tài liệu và kiểm tra khả năng trích xuất

**Tác nhân:** Hệ thống

**Đầu vào:** Nội dung đã qua kiểm tra và thông tin tài liệu.

**Xử lý:** Hệ thống tạo bản ghi tài liệu nguồn rồi yêu cầu trích xuất. Hệ thống chỉ tiếp nhận trích xuất khi nội dung đã được chuẩn hóa. Tài liệu lưu trữ, tài liệu chưa phân tích hoặc nội dung nguồn đã thay đổi so với hồ sơ nhập tài liệu trước có thể bị từ chối. Luồng phân tích nội dung tài liệu nguồn là một xử lý riêng trong hệ thống; sơ đồ này bắt đầu ở chức năng tiếp nhận dữ liệu nhập yêu cầu và không mô tả chi tiết tiến trình nền phân tích nội dung đó.

**Đầu ra:** Hồ sơ tài liệu đủ điều kiện để trích xuất; hoặc lỗi trạng thái như tài liệu chưa phân tích nội dung, bị lưu trữ, nguồn đã đổi hay không thể xác minh lần nhập trước.

**Nhánh lỗi/điều kiện:** Nếu tài liệu chưa được phân tích nội dung, đã lưu trữ, thiếu nội dung đã chuẩn hóa hoặc nguồn khác với hồ sơ trước, không cho trích xuất theo hồ sơ đó.

### Bước 3. Trích xuất yêu cầu đề xuất

**Tác nhân:** Hệ thống

**Đầu vào:** Tài liệu nguồn có nội dung chuẩn hóa.

**Xử lý:** Hệ thống trích xuất các mục có thể biểu diễn thành yêu cầu và gắn tham chiếu về nguồn. Cách trích xuất phụ thuộc loại tài liệu và cấu hình; một số định dạng có cấu trúc được xử lý theo nhánh riêng. Vì thế, không thể mặc định mọi tài liệu đều đi qua cùng một cách trích xuất.

**Đầu ra:** Danh sách **yêu cầu đề xuất từ tài liệu** kèm dữ liệu nguồn, cảnh báo hoặc xung đột nếu phát hiện. Đây chưa phải các yêu cầu chính thức trong kho yêu cầu.

**Nhánh lỗi/điều kiện:** Cách trích xuất phụ thuộc loại tài liệu và cấu hình; không mặc định mọi định dạng đều qua trí tuệ nhân tạo. Lỗi xử lý được trả về để người dùng rà soát lại.

### Bước 4. Rà soát và đối chiếu trùng

**Tác nhân:** BA và Hệ thống

**Đầu vào:** Danh sách yêu cầu đề xuất.

**Xử lý:** Người dùng xem từng mục, đối chiếu với nội dung tài liệu và kết quả so sánh với yêu cầu hiện có. Họ có thể sửa nội dung đề xuất, kiểm tra mã yêu cầu hoặc xử lý các mục có khả năng trùng. Hệ thống từ chối xác nhận nếu tập đề xuất bị thay đổi ngoài lần sửa đổi đang được rà soát.

**Đầu ra:** Bản xem trước đã được rà soát; hoặc yêu cầu được giữ lại để người dùng xử lý thêm.

**Nhánh lỗi/điều kiện:** Khi lần sửa đổi đã thay đổi hoặc có mục trùng/xung đột, bản xem trước phải được tải lại hoặc xử lý trước khi xác nhận.

### Bước 5. Chỉnh sửa cấu trúc đề xuất khi cần

**Tác nhân:** BA và Hệ thống

**Đầu vào:** Một hay nhiều đề xuất chưa phù hợp để nhập nguyên trạng.

**Xử lý:** Người dùng có thể chỉnh sửa bản xem trước, gộp nhiều mục thành một, tách một mục thành nhiều yêu cầu nhỏ hơn, hoặc từ chối một mục kèm lý do theo thao tác tương ứng. Hệ thống lưu quan hệ giữa nội dung đã gộp/tách và các đề xuất nguồn để duy trì khả năng truy nguyên.

**Đầu ra:** Tập đề xuất đã được chuẩn hóa, hoặc tập còn mục bị loại.

**Nhánh lỗi/điều kiện:** Chỉ áp dụng thao tác gộp/tách/từ chối khi nội dung và liên kết nguồn còn hợp lệ; thao tác không hợp lệ không được đưa vào tập nhập.

### Bước 6. Chọn yêu cầu cần nhập

**Tác nhân:** BA và Hệ thống

**Đầu vào:** Bản xem trước sau rà soát.

**Xử lý:** Người dùng chọn một hoặc nhiều mục để tạo yêu cầu. Không được xác nhận một tập rỗng. Mỗi mục được chọn phải có nội dung đọc được và tham chiếu nguồn; chỉ mục hợp lệ trong bản xem trước mới được phép chọn.

**Đầu ra:** Danh sách chỉ mục sẽ nhập, cùng thông tin giải trình nếu người dùng quyết định giữ riêng các mục có kết quả trùng.

**Nhánh lỗi/điều kiện:** Không cho xác nhận nếu không chọn mục nào, mục đã không còn cập nhật hoặc thiếu lý do giữ riêng khi có trùng.

### Bước 7. Xác minh xung đột trước khi ghi

**Tác nhân:** Hệ thống

**Đầu vào:** Danh sách mục đã chọn và quyết định xử lý trùng.

**Xử lý:** Hệ thống chạy so sánh lại ngay trước xác nhận để tránh dựa trên kết quả cũ. Xung đột mã yêu cầu, kết quả trùng chưa được giải quyết, hoặc thiếu lý do khi chọn giữ riêng sẽ chặn thao tác. Điều kiện này bảo vệ tính duy nhất và hạn chế tạo yêu cầu trùng ngoài ý muốn.

**Đầu ra:** Tập dữ liệu được phép ghi; hoặc danh sách lỗi/xung đột yêu cầu người dùng quay lại rà soát.

**Nhánh lỗi/điều kiện:** Nếu kết quả so sánh mới phát hiện mã trùng hay xung đột chưa được giải quyết, quay lại rà soát; không ghi dữ liệu.

### Bước 8. Xác nhận và tạo yêu cầu

**Tác nhân:** BA xác nhận; Hệ thống ghi nhận

**Đầu vào:** Tập mục đã chọn, lần sửa đổi hồ sơ nhập tài liệu và các quyết định xung đột hợp lệ.

**Xử lý:** Hệ thống đánh dấu hồ sơ đang được xác nhận để chống hai thao tác xác nhận đồng thời, sau đó tạo các yêu cầu và cập nhật trạng thái hồ sơ trong giao dịch dữ liệu. Mục không được chọn được lưu là không nhập. Nếu giao dịch dữ liệu thất bại, trạng thái xác nhận được hoàn nguyên để có thể xử lý lại. Khi thành công, hệ thống tiếp tục phục hồi/cập nhật dữ liệu phục vụ tra cứu cho các phiên bản liên quan.

**Đầu ra:** Các yêu cầu được tạo ở trạng thái bản nháp, có nguồn truy nguyên; hoặc hồ sơ được trả về trạng thái có thể thử lại. Muốn trở thành phiên bản chuẩn, yêu cầu mới cần đi tiếp Quy trình 3.2.2.

**Nhánh lỗi/điều kiện:** Nếu hồ sơ đã được tiến trình khác xác nhận hoặc giao dịch dữ liệu ghi thất bại, hệ thống không tạo kết quả một phần; hồ sơ được đưa về trạng thái có thể thử lại.



Hình 3.2.1. Sơ đồ BPMN quy trình nhập tài liệu và trích xuất yêu cầu. [Tệp sơ đồ](drawio/BPMN_Requirements_01_Nhap_tai_lieu_va_trich_xuat_yeu_cau_v1.drawio).

## 3.2.2 Quy trình soạn thảo và phê duyệt yêu cầu

BA tạo hoặc cập nhật yêu cầu, hoàn thiện nội dung rồi gửi để rà soát. Hệ thống kiểm tra trường bắt buộc và lần cập nhật hiện hành trước khi chuyển yêu cầu sang bước chờ xem xét. Admin đánh giá nội dung, có thể yêu cầu BA chỉnh sửa hoặc phê duyệt để ghi nhận phiên bản chuẩn. Sau phê duyệt, Hệ thống cập nhật dữ liệu phục vụ tra cứu; nếu việc này gặp sự cố, yêu cầu vẫn có thể đã được ghi nhận trong khi khả năng tra cứu bị suy giảm.

**Tác nhân:** BA soạn, cập nhật và gửi yêu cầu. Admin đảm nhiệm rà soát/chấp nhận. Hệ thống vẫn kiểm tra quyền gửi yêu cầu để rà soát, quyền rà soát yêu cầu và quyền phê duyệt yêu cầu; do đó làn vai trò không thay thế điều kiện quyền thao tác hoặc quy tắc không tự duyệt.

### Bước 1. Tạo hoặc cập nhật bản nháp

**Tác nhân:** BA

**Đầu vào:** Yêu cầu mới, hoặc yêu cầu đã có cần chỉnh sửa; nội dung, tiêu đề, loại, tiêu chí chấp nhận và các trường tùy chỉnh nếu dự án sử dụng.

**Xử lý:** Người dùng có quyền cập nhật nội dung. Hệ thống lưu nội dung theo lần sửa đổi và trạng thái hiện hành. Đối với yêu cầu mới, trạng thái khởi đầu là bản nháp; các bản nhập từ tài liệu cũng bắt đầu ở trạng thái này.

**Đầu ra:** Bản nháp có lần sửa đổi xác định.

**Nhánh lỗi/điều kiện:** Không lưu được nếu thiếu trường bắt buộc, sai dự án, thiếu quyền hoặc lần sửa đổi gửi lên không còn hiện hành.

### Bước 2. Kiểm tra tính sẵn sàng trước rà soát

**Tác nhân:** Hệ thống

**Đầu vào:** Bản nháp hoặc phiên bản sẵn sàng gửi duyệt cùng lần sửa đổi kỳ vọng.

**Xử lý:** Hệ thống kiểm tra nội dung không rỗng, trường tùy chỉnh, dự án sở hữu và lần sửa đổi. Nếu người dùng thực hiện thao tác lưu sẵn sàng, trạng thái có thể chuyển từ bản nháp sang sẵn sàng gửi duyệt; chỉ phiên bản phù hợp mới được cập nhật.

**Đầu ra:** Yêu cầu sẵn sàng gửi; hoặc lỗi dữ liệu, sai dự án, sai trạng thái hay xung đột lần sửa đổi.

**Nhánh lỗi/điều kiện:** Chỉ chuyển sang sẵn sàng gửi duyệt khi nội dung và trường tùy chỉnh hợp lệ; trạng thái/lần sửa đổi không khớp sẽ bị từ chối.

### Bước 3. Gửi yêu cầu để rà soát

**Tác nhân:** BA gửi; Hệ thống kiểm tra

**Đầu vào:** Yêu cầu ở bản nháp hoặc sẵn sàng gửi duyệt, quyền gửi yêu cầu để rà soát, lần sửa đổi và ghi chú rà soát.

**Xử lý:** Hệ thống xác thực trạng thái, lần sửa đổi, nội dung và trường tùy chỉnh, sau đó chuyển phiên bản sang đang chờ rà soát. Người gửi, thời điểm gửi và ghi chú được lưu cùng thay đổi trạng thái. Một số tài khoản, như quản trị viên hệ thống hoặc trưởng dự án theo kiểm tra trong hệ thống, có thể đi qua cơ chế tự động ghi nhận phiên bản chuẩn.

**Đầu ra:** Yêu cầu đang chờ rà soát; hoặc đã sang bước phiên bản chuẩn theo cơ chế tự phê duyệt; hoặc bị chặn bởi điều kiện đầu vào.

**Nhánh lỗi/điều kiện:** Chỉ gửi từ bản nháp/sẵn sàng gửi duyệt với quyền phù hợp. Một số tài khoản có thể theo nhánh phiên bản chuẩn tự động được hệ thống cho phép; nếu không, yêu cầu chờ rà soát.

### Bước 4. Rà soát và quyết định

**Tác nhân:** Admin rà soát; Hệ thống kiểm tra và lưu quyết định

**Đầu vào:** Phiên bản đang chờ rà soát cùng nội dung và tiêu chí chấp nhận.

**Xử lý:** Người có quyền rà soát kiểm tra yêu cầu. Hệ thống cho phép thao tác trả yêu cầu để sửa và một thao tác rà soát kỹ thuật riêng. Không có căn cứ để kết luận rà soát kỹ thuật là bước bắt buộc trong mọi lần duyệt. Nếu trả sửa, hệ thống yêu cầu một người không thuộc nhóm tác giả nội dung duyệt độc lập, ngoại trừ trường hợp quyền tự duyệt được cho phép.

**Đầu ra:** Quyết định yêu cầu chỉnh sửa; ghi nhận rà soát kỹ thuật nếu được gọi; hoặc quyết định tiếp tục phê duyệt.

**Nhánh lỗi/điều kiện:** Quyết định chỉ được ghi khi người rà soát có quyền và trạng thái còn đang chờ rà soát; tự phê duyệt bị chặn, trừ ngoại lệ quyền được hệ thống quy định.

### Bước 5. Trả về chỉnh sửa nếu chưa đạt

**Tác nhân:** Admin trả yêu cầu; BA cập nhật

**Đầu vào:** Yêu cầu đang chờ rà soát, lần sửa đổi hiện tại và nhận xét rà soát.

**Xử lý:** Người có quyền trả nội dung về bản nháp. Hệ thống cập nhật người yêu cầu chỉnh sửa, thời điểm và ghi chú; kiểm tra tự phê duyệt và lần sửa đổi trước khi ghi.

**Đầu ra:** Bản nháp quay lại cho người cập nhật. Sau chỉnh sửa, quy trình có thể lặp từ Bước 2.

**Nhánh lỗi/điều kiện:** Thiếu lý do, trạng thái sai hoặc lần sửa đổi xung đột thì không chuyển yêu cầu về trạng thái bản nháp.

### Bước 6. Kiểm định và ghi nhận phiên bản chuẩn

**Tác nhân:** Admin phê duyệt; Hệ thống kiểm định và ghi phiên bản chuẩn

**Đầu vào:** Yêu cầu đang rà soát, lần sửa đổi khớp và các tiêu chí chấp nhận liên quan.

**Xử lý:** Hệ thống chạy kiểm định nội dung. Nếu có lỗi mức chặn, phiên bản chuẩn không được ghi. Khi hợp lệ, Hệ thống cập nhật phiên bản thành đã ghi nhận làm phiên bản chuẩn, đặt phiên bản hiện hành của yêu cầu, cập nhật tiêu chí liên quan và ghi nhật ký thao tác trong giao dịch dữ liệu.

**Đầu ra:** Phiên bản yêu cầu được ghi nhận làm phiên bản chuẩn; hoặc thao tác bị chặn bởi kiểm tra tự động, quyền, trạng thái, xung đột lần sửa đổi hoặc xung đột phiên bản hiện hành.

**Nhánh lỗi/điều kiện:** Lỗi kiểm tra tự động ở mức chặn, thiếu quyền, lần sửa đổi lỗi hoặc phiên bản chuẩn hiện hành xung đột sẽ chặn giao dịch dữ liệu.

### Bước 7. Cập nhật chỉ mục

**Tác nhân:** Hệ thống

**Đầu vào:** Phiên bản chuẩn hiện hành.

**Xử lý:** Hệ thống đưa phiên bản vào chỉ mục phục vụ truy vấn. Nếu chỉ mục tìm kiếm theo ngữ nghĩa gặp sự cố, hệ thống có thể trả kết quả tra cứu suy giảm dù trạng thái phiên bản chuẩn đã được ghi nhận. Đây là sự cố ở năng lực tra cứu, không nên hiểu thành yêu cầu bị trả duyệt.

**Đầu ra:** Phiên bản chuẩn có thể truy vấn đầy đủ, hoặc phiên bản chuẩn ở chế độ chỉ mục suy giảm cần xử lý vận hành.

**Nhánh lỗi/điều kiện:** Nếu cập nhật dữ liệu phục vụ tra cứu thất bại sau khi phiên bản chuẩn đã được ghi nhận, giữ phiên bản chuẩn và báo tình trạng suy giảm khả năng tra cứu để xử lý vận hành.



Hình 3.2.2. Sơ đồ BPMN quy trình soạn thảo và phê duyệt yêu cầu. [Tệp sơ đồ](drawio/BPMN_Requirements_02_Soan_thao_va_phe_duyet_yeu_cau_v1.drawio).

## 3.2.3 Quy trình lập và phê duyệt kế hoạch kiểm thử

Tester lập kế hoạch, chọn phạm vi kiểm thử, môi trường và các bộ hoặc ca liên quan. Hệ thống kiểm tra mức đầy đủ cũng như tính hợp lệ của những đối tượng được tham chiếu trước khi nhận gửi duyệt. Admin xem xét độc lập, trả kế hoạch để chỉnh sửa nếu cần hoặc phê duyệt. Khi duyệt, Hệ thống ghi nhận ảnh chụp phạm vi làm căn cứ kiểm tra các lượt chạy sau.

**Tác nhân:** Tester lập và gửi kế hoạch; Admin rà soát hoặc phê duyệt. Hệ thống kiểm tra quyền gửi và phê duyệt kế hoạch kiểm thử, tính độc lập của người duyệt và ảnh chụp phạm vi.

### Bước 1. Khởi tạo kế hoạch

**Tác nhân:** Tester

**Đầu vào:** Dự án, tên/mục tiêu kế hoạch và phạm vi kiểm thử dự kiến.

**Xử lý:** Người dùng tạo kế hoạch và có thể khai báo phiên bản yêu cầu, bộ kiểm thử, phiên bản ca kiểm thử, môi trường hoặc kỳ kiểm thử. Có thể lập thủ công hoặc yêu cầu Hệ thống gợi ý kế hoạch. Gợi ý không tự trở thành kế hoạch đã duyệt.

**Đầu ra:** Kế hoạch ở trạng thái nháp hoặc kế hoạch đã được người dùng hoàn thiện một phần.

**Nhánh lỗi/điều kiện:** Gợi ý tự động chỉ tạo nội dung đề xuất; kế hoạch vẫn cần Tester rà soát và lưu thành bản kế hoạch.

### Bước 2. Hoàn thiện phạm vi và cấu hình

**Tác nhân:** Tester và Hệ thống

**Đầu vào:** Bản nháp kế hoạch cùng các đối tượng được chọn.

**Xử lý:** Người lập bổ sung phạm vi, môi trường và bộ kiểm thử. Hệ thống kiểm tra quyền sở hữu, tính hợp lệ của các đối tượng tham chiếu và tính đầy đủ. Lần sửa đổi được dùng để phát hiện cập nhật đồng thời.

**Đầu ra:** Kế hoạch đủ điều kiện gửi rà soát; hoặc danh sách phát hiện thiếu/sai để cập nhật.

**Nhánh lỗi/điều kiện:** Không cho gửi nếu đối tượng tham chiếu sai dự án, thiếu quyền, phạm vi không hợp lệ hoặc dữ liệu đã đổi.

### Bước 3. Gửi kế hoạch để rà soát

**Tác nhân:** Tester gửi; Hệ thống kiểm tra

**Đầu vào:** Kế hoạch ở bản nháp hoặc sẵn sàng gửi duyệt, lần sửa đổi và ghi chú gửi duyệt.

**Xử lý:** Hệ thống tính mức đầy đủ. Nếu chưa đạt, thao tác gửi bị từ chối. Nếu đạt, Hệ thống chuyển trạng thái sang đang chờ rà soát và lưu thông tin gửi. Cơ chế tự phê duyệt chỉ áp dụng khi tài khoản thỏa điều kiện phân quyền hiện hành.

**Đầu ra:** Kế hoạch chờ rà soát; hoặc được phê duyệt tự động nếu đáp ứng điều kiện; hoặc bị chặn vì chưa đầy đủ.

**Nhánh lỗi/điều kiện:** Chỉ nhận kế hoạch đủ điều kiện và đúng lần sửa đổi. Cơ chế tự phê duyệt, nếu có, phụ thuộc điều kiện quyền được cấu hình.

### Bước 4. Rà soát độc lập

**Tác nhân:** Admin rà soát; Hệ thống kiểm tra quyền và trạng thái

**Đầu vào:** Kế hoạch đang chờ rà soát, phạm vi và trạng thái nguồn tham chiếu.

**Xử lý:** Người có quyền phê duyệt kiểm tra kế hoạch. Hệ thống áp dụng quy tắc rà soát độc lập, nên người duyệt thông thường phải độc lập với tác giả nội dung; ngoại lệ tự duyệt được kiểm soát riêng theo trưởng dự án/quản trị viên hệ thống. Người duyệt có thể yêu cầu chỉnh sửa, và khi đó lý do rà soát là bắt buộc.

**Đầu ra:** Quyết định phê duyệt; hoặc yêu cầu trả về bản nháp.

**Nhánh lỗi/điều kiện:** Người tạo không tự duyệt theo quy tắc độc lập, trừ ngoại lệ được hệ thống cho phép; thiếu quyền hoặc sai trạng thái thì từ chối.

### Bước 5. Chỉnh sửa khi được yêu cầu

**Tác nhân:** Tester cập nhật

**Đầu vào:** Kế hoạch bị trả về cùng nhận xét/lý do.

**Xử lý:** Người có quyền cập nhật phạm vi, các bộ/ca kiểm thử hoặc thông tin môi trường. Kế hoạch trở lại bản nháp, sau đó phải được kiểm tra và gửi rà soát lại.

**Đầu ra:** Kế hoạch đã điều chỉnh để gửi lại; hoặc tiếp tục chưa hợp lệ nếu thiếu điều kiện.

**Nhánh lỗi/điều kiện:** Cần nhận xét/lý do khi trả sửa; nếu lần sửa đổi đã đổi thì không ghi đè bản cập nhật mới.

### Bước 6. Xác minh phạm vi ngay trước khi phê duyệt

**Tác nhân:** Hệ thống

**Đầu vào:** Kế hoạch đang rà soát, các phiên bản yêu cầu, bộ kiểm thử và ca kiểm thử được tham chiếu.

**Xử lý:** Hệ thống kiểm tra lại phạm vi, tính đầy đủ và ảnh chụp phạm vi của bộ kiểm thử. Nếu phạm vi đã đổi so với ảnh chụp phạm vi đang được rà soát, hoặc nguồn không còn hợp lệ, thao tác phê duyệt bị chặn để kế hoạch được rà soát lại.

**Đầu ra:** Phạm vi được xác nhận không đổi và đủ điều kiện ghi nhận; hoặc lỗi xung đột cần quay lại rà soát.

**Nhánh lỗi/điều kiện:** Nếu ảnh chụp phạm vi, phiên bản yêu cầu, bộ hoặc ca kiểm thử đã thay đổi, dừng phê duyệt và yêu cầu rà soát lại.

### Bước 7. Phê duyệt và tạo ảnh chụp phạm vi

**Tác nhân:** Admin phê duyệt; Hệ thống tạo ảnh chụp phạm vi

**Đầu vào:** Kế hoạch hợp lệ, lần sửa đổi khớp và quyết định phê duyệt.

**Xử lý:** Hệ thống chuyển trạng thái sang đã phê duyệt, lưu ảnh chụp phạm vi, mã kiểm tra, người duyệt, thời gian và lịch sử phê duyệt. Mã kiểm tra giúp lượt chạy sau kiểm tra rằng kế hoạch được dùng đúng phiên bản đã duyệt.

**Đầu ra:** Kế hoạch đã duyệt và có ảnh chụp phạm vi/mã kiểm tra; hoặc phê duyệt bị chặn bởi quyền, tự phê duyệt, thay đổi bộ kiểm thử, thiếu phạm vi hay xung đột lần sửa đổi.

**Nhánh lỗi/điều kiện:** Chỉ tạo ảnh chụp phạm vi khi phạm vi còn hợp lệ và lần sửa đổi khớp; thiếu phạm vi, tự phê duyệt hoặc xung đột sẽ chặn phê duyệt.



Hình 3.2.3. Sơ đồ BPMN quy trình lập và phê duyệt kế hoạch kiểm thử. [Tệp sơ đồ](drawio/BPMN_Testing_03_Lap_va_phe_duyet_ke_hoach_kiem_thu_v1.drawio).

## 3.2.4 Quy trình thiết kế và phê duyệt ca kiểm thử

Tester thiết kế ca thủ công hoặc tạo bản xem trước từ yêu cầu, sau đó chọn và hoàn thiện các bước, dữ liệu kiểm thử, kết quả mong đợi cùng căn cứ nguồn. Hệ thống kiểm tra nội dung trước khi nhận gửi duyệt. Admin là người phê duyệt ca; nếu nội dung chưa đạt, ca được trả lại để chỉnh sửa. Khi ca được chấp thuận, Hệ thống tạo phiên bản đã duyệt để dùng trong kế hoạch và lượt chạy. Thao tác gửi của Tester không đồng thời phê duyệt ca.

**Tác nhân:** Tester thiết kế và gửi ca; Admin là người duy nhất phê duyệt. Hệ thống kiểm tra quyền Admin, trạng thái rà soát, lần sửa đổi, nguồn, bằng chứng và điều kiện độc lập trước khi tạo phiên bản được duyệt. Trước đây, hệ thống cấp nhầm quyền phê duyệt ca kiểm thử cho Tester, đồng thời cho phép một số trưởng dự án đi vào cơ chế tự phê duyệt. Các hành vi này đã được sửa: Tester không thể nhận hoặc sử dụng quyền phê duyệt, và gửi ca luôn đưa bản nháp vào trạng thái chờ Admin xét duyệt.

### Bước 1. Chọn nguồn thiết kế

**Tác nhân:** Tester và Hệ thống

**Đầu vào:** Phiên bản yêu cầu đã được ghi nhận là phiên bản chuẩn và tiêu chí chấp nhận phù hợp.

**Xử lý:** Người dùng chọn soạn thủ công hoặc tạo bản xem trước bằng công cụ hỗ trợ tự động. Với nhánh tạo đề xuất tự động, Hệ thống kiểm tra quyền sử dụng nguồn thiết kế và phiên bản yêu cầu còn hiện hành. Người dùng phải yêu cầu chế độ bản xem trước trước khi chọn nội dung sinh.

**Đầu ra:** Bản nháp thủ công hoặc bản xem trước các ca đề xuất, có thông tin nguồn và cảnh báo.

**Nhánh lỗi/điều kiện:** Nguồn chưa phiên bản chuẩn, thiếu quyền hoặc bản xem trước được tạo tự động không hợp lệ thì không tạo bản nháp từ nguồn đó.

### Bước 2. Kiểm tra tính hiện hành và bằng chứng nguồn

**Tác nhân:** Hệ thống

**Đầu vào:** Đề xuất sinh từ yêu cầu/tiêu chí.

**Xử lý:** Trong lúc sinh và trước khi lưu, hệ thống kiểm tra phiên bản yêu cầu, tiêu chí chấp nhận và các bằng chứng trích dẫn. Nếu nguồn thay đổi trong quá trình này, bản xem trước trở thành không còn cập nhật và cần tạo lại. Kết quả còn có thể kèm thông tin tương đồng với ca hiện có để người dùng đánh giá trùng lặp.

**Đầu ra:** Bản xem trước còn hợp lệ để người dùng lựa chọn; hoặc lỗi nguồn thay đổi cần chạy lại.

**Nhánh lỗi/điều kiện:** Nếu phiên bản yêu cầu/bằng chứng thay đổi, bản xem trước không còn cập nhật và cần tạo lại trước khi dùng.

### Bước 3. Chọn và hoàn thiện bản nháp

**Tác nhân:** Tester

**Đầu vào:** Bản xem trước hoặc thông tin do người dùng soạn.

**Xử lý:** Người dùng chọn ca cần giữ, hoàn thiện bước thực thi, dữ liệu kiểm thử và kết quả mong đợi. Mỗi bước cần thể hiện hành động và kết quả mong đợi đủ để kiểm chứng. Nội dung được tạo tự động đã được sửa cần đối chiếu lại nguồn trước khi gửi duyệt.

**Đầu ra:** Bản nháp ca kiểm thử có nội dung và liên kết nguồn.

**Nhánh lỗi/điều kiện:** Chỉ các mục được Tester chọn và có nội dung kiểm chứng được mới trở thành bản nháp; mục không được chọn không được lưu thành ca.

### Bước 4. Chạy kiểm tra tự động và kiểm tra mức đầy đủ

**Tác nhân:** Hệ thống

**Đầu vào:** Bản nháp đã hoàn thiện.

**Xử lý:** Hệ thống kiểm tra khả năng xác minh các bước, bằng chứng nguồn và các phát hiện kiểm tra tự động. Cấu hình dự án quyết định lỗi kiểm tra tự động có chặn gửi duyệt hay không; mặc định hệ thống bật cơ chế chặn. Nếu thiếu hành động hoặc kết quả mong đợi, ca không được gửi.

**Đầu ra:** Bản nháp đạt điều kiện rà soát; hoặc danh sách lỗi cần cập nhật.

**Nhánh lỗi/điều kiện:** Nếu thiếu hành động hoặc kết quả mong đợi, không cho gửi. Lỗi kiểm tra tự động có chặn hay không phụ thuộc cấu hình chặn lỗi kiểm tra tự động, mặc định bật.

### Bước 5. Gửi ca để rà soát

**Tác nhân:** Tester gửi; Hệ thống chuyển trạng thái

**Đầu vào:** Bản nháp ở trạng thái bản nháp hoặc sẵn sàng gửi duyệt, lần sửa đổi hiện hành và ghi chú gửi duyệt.

**Xử lý:** Hệ thống kiểm tra nguồn yêu cầu còn hiệu lực, bằng chứng của ca được tạo từ nguồn tự động, cấu trúc các bước và kiểm tra tự động. Nếu đạt, chuyển ca sang đang chờ rà soát để Admin xét duyệt riêng; thao tác gửi không tự phê duyệt ca, kể cả khi người gửi là trưởng dự án.

**Đầu ra:** Ca ở trạng thái đang chờ Admin phê duyệt; hoặc thao tác gửi bị từ chối nếu chưa đáp ứng điều kiện.

**Nhánh lỗi/điều kiện:** Khi đủ điều kiện, trạng thái luôn là đang chờ rà soát và chờ Admin; Tester và trưởng dự án không tự duyệt qua thao tác gửi.

### Bước 6. Rà soát và xử lý yêu cầu chỉnh sửa

**Tác nhân:** Admin rà soát; Hệ thống kiểm tra độc lập

**Đầu vào:** Ca đang chờ rà soát, nguồn yêu cầu, tiêu chí và kết quả so sánh với ca hiện có.

**Xử lý:** Người có quyền rà soát đánh giá khả năng kiểm chứng, mức bao phủ nguồn và khả năng trùng. Nếu chưa đạt, người rà soát yêu cầu chỉnh sửa; Hệ thống kiểm tra người duyệt độc lập với tác giả nội dung, ngoại trừ trường hợp tự duyệt có thẩm quyền.

**Đầu ra:** Quyết định duyệt; hoặc bản nháp được chuyển lại cho người chỉnh sửa kèm ghi chú/lý do.

**Nhánh lỗi/điều kiện:** Chỉ Admin được phê duyệt. Admin phải đáp ứng điều kiện độc lập; người không có quyền hoặc ca không còn đang chờ rà soát phải bị từ chối. Yêu cầu sửa chuyển bản nháp về cho người chỉnh sửa kèm lý do.

### Bước 7. Kiểm tra cuối và đóng băng phiên bản

**Tác nhân:** Admin quyết định; Hệ thống kiểm tra và đóng băng phiên bản

**Đầu vào:** Ca được đề xuất phê duyệt.

**Xử lý:** Hệ thống chạy lại kiểm tra bước, kiểm tra tự động và tính hiện hành của nguồn. Hệ thống đối chiếu mức độ trùng lặp theo ngữ cảnh; nếu có ca gần trùng, người duyệt cần đưa ra lý do xử lý trường hợp trùng trước khi tiếp tục. Khi hợp lệ, hệ thống tạo phiên bản ca đã duyệt, liên kết nguồn và đóng băng bản nháp.

**Đầu ra:** Ca kiểm thử có phiên bản đã duyệt để dùng khi tạo lượt chạy; hoặc thao tác bị chặn vì nguồn lỗi thời, nội dung thiếu, kiểm tra tự động hoặc trùng lặp chưa được giải trình.

**Nhánh lỗi/điều kiện:** Nếu nguồn đã không còn cập nhật, thiếu bước/bằng chứng, kiểm tra tự động còn lỗi chặn hoặc trùng chưa có lý do xử lý trường hợp trùng, không tạo phiên bản đã phê duyệt.



Hình 3.2.4. Sơ đồ BPMN quy trình thiết kế và phê duyệt ca kiểm thử. [Tệp sơ đồ](drawio/BPMN_Testing_04_Thiet_ke_va_phe_duyet_ca_kiem_thu_v1.drawio).

## 3.2.5 Quy trình phân công và thực thi kiểm thử

Admin tạo lượt kiểm thử từ kế hoạch đã duyệt, xác minh phạm vi và môi trường rồi phân công toàn lượt hoặc từng ca cho Tester đủ điều kiện. Hệ thống khởi tạo kết quả cho các ca trong lượt. Tester bắt đầu lượt được giao, thực hiện từng ca và ghi kết quả; ca không đạt có thể được liên kết với lỗi tương ứng. Khi kết quả đáp ứng điều kiện, Admin hoàn tất lượt chạy. Nếu vẫn còn ca chưa có kết quả, việc hoàn tất một phần chỉ được thực hiện khi thiết lập của dự án cho phép.

**Tác nhân:** Admin quản lý lượt chạy và phân công; Tester thực thi. Hệ thống yêu cầu quyền tạo/phân công, sau đó kiểm tra Tester có quyền thực thi kiểm thử và được giao đúng lượt hoặc phiên bản ca.

### Bước 1. Khai báo lượt chạy

**Tác nhân:** Admin

**Đầu vào:** Dự án, kế hoạch kiểm thử, phạm vi ca/bộ kiểm thử, môi trường và thông tin đợt phát hành/bản dựng nếu có.

**Xử lý:** Người có quyền tạo lượt chạy khai báo các tham số. Hiện tại, hệ thống yêu cầu kế hoạch kiểm thử đã duyệt khi tạo lượt kiểm thử. Kế hoạch phải có ảnh chụp phạm vi đã được phê duyệt hợp lệ; nếu không có kế hoạch, chưa duyệt hoặc ảnh chụp phạm vi mã kiểm tra thay đổi, yêu cầu bị từ chối.

**Đầu ra:** Yêu cầu tạo lượt chạy hợp lệ; hoặc lỗi kế hoạch/ảnh chụp phạm vi.

**Nhánh lỗi/điều kiện:** Không tạo lượt chạy nếu thiếu kế hoạch đã duyệt hoặc ảnh chụp phạm vi hợp lệ.

### Bước 2. Kiểm tra phạm vi và môi trường

**Tác nhân:** Hệ thống

**Đầu vào:** Danh sách phiên bản ca, bộ kiểm thử, môi trường, đợt phát hành/bản dựng và ảnh chụp phạm vi của kế hoạch.

**Xử lý:** Hệ thống giải quyết ngữ cảnh thực thi, loại bỏ mã ca lặp, xác nhận các ca nằm trong phạm vi đã được chụp tại thời điểm phê duyệt và kiểm tra phiên bản ca còn tồn tại trong dự án. Bộ kiểm thử gắn vào lượt chạy cần phù hợp với ảnh chụp phạm vi của bộ đã duyệt.

**Đầu ra:** phạm vi thực thi đã xác minh; hoặc lỗi ca ngoài kế hoạch, phạm vi rỗng, môi trường không hợp lệ hoặc nguồn đã đổi.

**Nhánh lỗi/điều kiện:** phạm vi rỗng, ca ngoài ảnh chụp phạm vi, môi trường không hợp lệ hoặc phiên bản đã đổi sẽ chặn tạo lượt chạy.

### Bước 3. Tạo lượt chạy và kết quả ban đầu

**Tác nhân:** Admin khởi tạo; Hệ thống tạo lượt chạy

**Đầu vào:** Tham số lượt chạy đã kiểm tra.

**Xử lý:** Hệ thống tạo lượt kiểm thử ở trạng thái khởi tạo, ghim vào ảnh chụp phạm vi của kế hoạch và khởi tạo kết quả tương ứng cho từng phiên bản ca. Hệ thống cũng ghi nhận người tạo và lần sửa đổi. Mã nhận diện yêu cầu lặp, nếu có, được dùng để nhận diện yêu cầu lặp và ngăn tạo trùng ngoài ý muốn.

**Đầu ra:** Lượt kiểm thử mới cùng các bản ghi kết quả ban đầu; hoặc bản ghi hiện có được trả lại nếu yêu cầu lặp hợp lệ.

**Nhánh lỗi/điều kiện:** Nếu yêu cầu lặp có cùng mã nhận diện yêu cầu gửi lặp, trả lại bản ghi phù hợp; nếu nội dung khác hoặc giao dịch dữ liệu lỗi, không tạo lượt chạy trùng.

### Bước 4. Phân công lượt chạy hoặc từng ca

**Tác nhân:** Admin phân công; Hệ thống kiểm tra thành viên và quyền

**Đầu vào:** Lượt kiểm thử và danh sách thành viên dự án được chọn.

**Xử lý:** Người có quyền phân công kiểm thử gán toàn lượt cho một người hoặc gán từng phiên bản ca. Người được chỉ định phải là thành viên đang hoạt động và có quyền thực thi kiểm thử. Người tạo có thể là người được giao xử lý mặc định nếu họ có quyền thực thi, nhưng không tự động trở thành người được giao xử lý trong mọi trường hợp.

**Đầu ra:** Phân công đã lưu; hoặc lỗi nếu người nhận không hợp lệ hay không có quyền thực thi.

**Nhánh lỗi/điều kiện:** Chỉ phân công thành viên đang hoạt động và có quyền thực thi kiểm thử; người không hợp lệ hoặc thiếu quyền không được gán.

### Bước 5. Bắt đầu lượt chạy

**Tác nhân:** Tester bắt đầu; Hệ thống xác minh phân công

**Đầu vào:** Lượt kiểm thử đã tạo, người thực thi và phân công hợp lệ.

**Xử lý:** Tester có quyền thực thi kiểm thử bắt đầu lượt chạy. Trước khi ghi kết quả cho một ca cụ thể, hệ thống xác minh ca đó nằm trong phân công của người dùng. Có quyền chung nhưng không được giao đúng ca vẫn chưa đủ điều kiện thao tác.

**Đầu ra:** Lượt chạy ở trạng thái đang thực hiện; hoặc lỗi quyền/phân công/trạng thái.

**Nhánh lỗi/điều kiện:** Tester phải có quyền thực thi và được giao đúng lượt kiểm thử hoặc ca; trạng thái không cho phép bắt đầu thì hệ thống từ chối.

### Bước 6. Thực thi và ghi kết quả theo ca

**Tác nhân:** Tester thực thi; Hệ thống ghi kết quả

**Đầu vào:** Phiên bản ca được giao, dữ liệu chạy, kết quả từng bước và trạng thái thực thi.

**Xử lý:** Tester thực hiện ca và ghi kết quả mới. Các chuyển trạng thái chịu ràng buộc bởi quy tắc chuyển trạng thái kết quả, như chưa thực hiện sang đang thực hiện rồi sang kết quả phù hợp. Hệ thống không quy định ở sơ đồ này rằng các ca phải chạy song song hay theo một thứ tự nghiệp vụ cố định. Khi kết quả là thất bại, người có quyền có thể liên kết lỗi với kết quả tương ứng.

**Đầu ra:** Kết quả ca đã ghi; hoặc yêu cầu bị từ chối do phân công, trạng thái kết quả hoặc lần sửa đổi không hợp lệ.

**Nhánh lỗi/điều kiện:** Kết quả chỉ được ghi theo chuyển trạng thái hợp lệ và đúng phân công; kết quả sai trạng thái/lần sửa đổi không được lưu.

### Bước 7. Hoàn tất lượt chạy

**Tác nhân:** Admin yêu cầu hoàn tất; Hệ thống kiểm tra kết quả và chính sách dự án

**Đầu vào:** Lượt kiểm thử đang thực hiện và tập kết quả hiện tại.

**Xử lý:** Hệ thống đếm số kết quả đã đạt trạng thái được chấp nhận và so sánh với tổng số ca. Nếu thiếu kết quả, mặc định hệ thống chặn hoàn tất; dự án có thể bật cấu hình cho phép hoàn tất một phần để hệ thống cho phép kết thúc khi còn ca chưa có kết quả. Giá trị cấu hình cần được xác minh tại môi trường chạy.

**Đầu ra:** Lượt kiểm thử chuyển sang đã hoàn tất, kèm số lượng kết quả và thông tin về việc hoàn tất một phần; hoặc lỗi do lượt kiểm thử chưa đầy đủ để tiếp tục xử lý.

**Nhánh lỗi/điều kiện:** Nếu còn ca chưa có kết quả, mặc định chặn hoàn tất; chỉ cho hoàn tất một phần khi cấu hình cho phép hoàn tất một phần được bật.

### Bước 8. Hủy hoặc chạy lại

**Tác nhân:** Admin hủy hoặc khởi tạo chạy lại; Hệ thống kiểm tra trạng thái

**Đầu vào:** Yêu cầu hủy lượt đang ở bản nháp, sẵn sàng gửi duyệt hoặc đang thực hiện; hoặc yêu cầu tạo lượt chạy lại.

**Xử lý:** Người có quyền hủy cần ghi lý do; hệ thống chuyển trạng thái sang đã hủy. Mã nguồn cũng có chức năng chạy lại, nhưng đây là luồng riêng với điều kiện trạng thái/chống xử lý lặp lại riêng và không được gộp vào nhánh lặp từng ca trong sơ đồ này.

**Đầu ra:** Lượt chạy bị hủy có nhật ký thao tác; hoặc một lượt kiểm thử chạy lại riêng nếu thỏa các điều kiện chạy lại.

**Nhánh lỗi/điều kiện:** Chỉ hủy ở trạng thái được hỗ trợ và phải có lý do. Chạy lại là lượt chạy riêng, tuân theo điều kiện trạng thái và chống xử lý lặp lại riêng.



Hình 3.2.5. Sơ đồ BPMN quy trình phân công và thực thi kiểm thử. [Tệp sơ đồ](drawio/BPMN_Testing_05_Phan_cong_va_thuc_thi_kiem_thu_v1.drawio).

## 3.2.6 Quy trình xử lý lỗi và kiểm thử lại

Khi một kết quả kiểm thử không đạt, Tester có thể ghi nhận lỗi và liên kết lỗi với ca, lượt kiểm thử cùng thông tin liên quan. Admin phân loại lỗi; lỗi được xác nhận sẽ chuyển cho người phụ trách theo phân công. Sau khi cập nhật và đánh dấu đã xử lý, lỗi có thể chờ kiểm thử lại hoặc được mở lại để tiếp tục khắc phục. Tester thực hiện lại ca được giao. Kết quả đạt dẫn đến đóng lỗi; kết quả không đạt đưa lỗi trở lại bước xử lý.

**Tác nhân:** Tester ghi nhận lỗi từ kết quả thực thi và thực hiện kiểm thử lại; Admin phân loại lỗi theo vai trò nghiệp vụ. Khâu khắc phục thuộc người dùng được giao cho người phụ trách xử lý, có thể là BA, Tester hoặc Admin tùy cấu hình. Hệ thống yêu cầu quyền phân loại lỗi, quyền cập nhật trạng thái lỗi, quyền kiểm thử lại lỗi và quyền thực thi/phân công phù hợp; hệ thống không quy định người được giao xử lý bằng một chức danh cố định.

### Bước 1. Ghi nhận lỗi

**Tác nhân:** Tester ghi nhận; Hệ thống xác thực

**Đầu vào:** Thông tin lỗi, mức độ nghiêm trọng, mức ưu tiên, dự án và liên kết tùy chọn tới kết quả, ca kiểm thử, yêu cầu, đợt phát hành/bản dựng/môi trường.

**Xử lý:** Hệ thống kiểm tra dự án, phân loại và các tham chiếu. Nếu lỗi liên kết với kết quả kiểm thử, kết quả phải ở trạng thái không đạt, thuộc đúng dự án, có ca kiểm thử phiên bản và nằm trong phạm vi lượt kiểm thử. Thông tin môi trường hoặc phiên bản ca khai báo không được mâu thuẫn với ngữ cảnh của lượt chạy. Mã nhận diện yêu cầu lặp, nếu gửi, giúp chống tạo lỗi lặp từ cùng yêu cầu.

**Đầu ra:** Lỗi mới ở trạng thái mới ghi nhận, có ngữ cảnh truy nguyên hợp lệ; hoặc lỗi kiểm tra dữ liệu nếu kết quả/ca/dự án không khớp.

**Nhánh lỗi/điều kiện:** Nếu kết quả không đạt, thuộc dự án khác/lượt kiểm thử hoặc ca kiểm thử phiên bản hoặc ngữ cảnh môi trường mâu thuẫn, không tạo lỗi liên kết.

### Bước 2. Phân loại lỗi

**Tác nhân:** Admin phân loại lỗi; Hệ thống kiểm tra chuyển trạng thái

**Đầu vào:** Lỗi mới ghi nhận.

**Xử lý:** Người có quyền thao tác phân loại lỗi đánh giá nội dung và đưa ra một chuyển trạng thái được cho phép: đã xác nhận, trùng lặp hoặc bị từ chối. Đây là quyền thao tác, không có nghĩa nguồn quy định mọi dự án phải có một chức danh riêng tên “Người phân loại lỗi”.

**Đầu ra:** Lỗi được xác nhận để xử lý, được ghi nhận trùng, hoặc bị từ chối. Việc chuyển trạng thái sai ma trận hoặc thiếu quyền thao tác bị chặn.

**Nhánh lỗi/điều kiện:** Chỉ cho phép lỗi mới ghi nhận được chuyển sang trạng thái hợp lệ như đã xác nhận, trùng lặp hoặc bị từ chối; chuyển trạng thái ngoài ma trận bị chặn.

### Bước 3. Giao và bắt đầu xử lý

**Tác nhân:** Người được giao xử lý; Hệ thống xác minh quyền và phân công

**Đầu vào:** Lỗi đã xác nhận, cùng người được phân công nếu trường phân công được sử dụng.

**Xử lý:** Người có quyền chuyển lỗi sang đang thực hiện. Một số thao tác xử lý yêu cầu người đang thực hiện phải khớp người được giao xử lý; quyền được kiểm tra theo trạng thái đích và phân công. Hệ thống lưu lý do chuyển, người thao tác, thời điểm, nhật ký thao tác và yêu cầu cập nhật dữ liệu phục vụ tra cứu tìm kiếm.

**Đầu ra:** Lỗi đang được xử lý; hoặc lỗi quyền, phân công, lần sửa đổi hay chuyển trạng thái.

**Nhánh lỗi/điều kiện:** Nếu người được giao xử lý không khớp hoặc thiếu quyền chuyển trạng thái, không đưa lỗi sang đang thực hiện.

### Bước 4. Cập nhật và khắc phục lỗi

**Tác nhân:** Người được giao xử lý

**Đầu vào:** Lỗi đang thực hiện, dữ liệu nguyên nhân và kết quả sửa lỗi.

**Xử lý:** Người có quyền cập nhật thông tin lỗi và tiếp tục thao tác sửa trong phạm vi ứng dụng. Hệ thống thể hiện cập nhật/trạng thái, nhưng không mô tả đủ chi tiết quy trình kỹ thuật nội bộ để khẳng định hoạt động sửa hệ thống, triển khai hay phát hành diễn ra theo một chuỗi cụ thể.

**Đầu ra:** Lỗi còn đang xử lý; hoặc sẵn sàng chuyển sang trạng thái đã xử lý khi người dùng xác nhận.

**Nhánh lỗi/điều kiện:** Hệ thống không quy định chuỗi sửa hệ thống/phát hành; mô tả chỉ ghi nhận cập nhật lỗi, không suy diễn thêm hoạt động ngoài hệ thống.

### Bước 5. Đánh dấu đã xử lý và quyết định kiểm thử lại

**Tác nhân:** Admin hoặc người có quyền cập nhật trạng thái; Hệ thống ghi nhận quyết định kiểm thử lại

**Đầu vào:** Lỗi đang thực hiện đã được cập nhật.

**Xử lý:** Người có quyền chuyển sang đã xử lý. Theo ma trận quy tắc chuyển trạng thái lỗi, từ đã xử lý có thể chuyển sang chờ kiểm thử lại hoặc đã mở lại. Nhánh chờ kiểm thử lại chờ một lượt thực thi kiểm tra lại; nhánh đã mở lại đưa lỗi quay lại xử lý mà không cần dùng kết quả kiểm thử lại không hợp lệ.

**Đầu ra:** Lỗi chờ kiểm thử lại; hoặc lỗi mở lại để tiếp tục xử lý.

**Nhánh lỗi/điều kiện:** Chỉ chuyển trạng thái được ma trận cho phép mới được ghi. Trường hợp chờ kiểm thử lại chờ kết quả mới; đã mở lại quay lại xử lý.

### Bước 6. Thực thi kiểm thử lại

**Tác nhân:** Tester thực thi kiểm thử lại; Hệ thống xác minh ca và kết quả

**Đầu vào:** Lỗi ở chờ kiểm thử lại, kết quả kiểm thử mới và phiên bản ca liên kết.

**Xử lý:** Người kiểm thử lại phải có quyền thực thi kiểm thử và được phân công đúng ca kiểm thử phiên bản trong lượt kiểm thử. Kết quả phải là mới, thuộc đúng ca kiểm thử phiên bản gắn với lỗi và có trạng thái đạt hoặc không đạt. Kết quả cũ, trạng thái khác hoặc ca không khớp bị từ chối. Hệ thống ghi nhận sự kiện kiểm thử lại, người thực hiện và kết quả được dùng.

**Đầu ra:** Sự kiện kiểm thử lại được ghi nhận với kết quả đạt hoặc không đạt; hoặc lỗi nếu lỗi chưa ở trạng thái chờ kiểm thử lại, kết quả không hợp lệ, chưa được giao ca hoặc không cùng phiên bản ca.

**Nhánh lỗi/điều kiện:** Kiểm thử lại cần lỗi chờ kiểm thử lại, kết quả mới ở mức đạt hoặc không đạt, đúng phiên bản và phân công; sai một điều kiện thì không ghi sự kiện kiểm thử lại.

### Bước 7. Đóng hoặc mở lại lỗi

**Tác nhân:** Hệ thống áp dụng kết quả; Tester nhận thông tin trạng thái

**Đầu vào:** Sự kiện kiểm thử lại hợp lệ.

**Xử lý:** Nếu kết quả là đạt, Hệ thống chuyển lỗi sang đã đóng. Nếu là không đạt, lỗi chuyển sang đã mở lại để tiếp tục khắc phục. Đây là ánh xạ quy tắc chuyển trạng thái của hệ thống: đạt → đã đóng; không đạt → đã mở lại.

**Đầu ra:** Lỗi đóng sau kiểm thử lại đạt; hoặc quay lại luồng xử lý sau kiểm thử lại không đạt. Cần lưu ý rằng đã đóng, bị từ chối và trùng lặp vẫn có chuyển trạng thái mở lại trong ma trận; kết thúc một lượt BPMN không có nghĩa bản ghi lỗi sẽ không bao giờ được mở lại.

**Nhánh lỗi/điều kiện:** đạt thì chuyển lỗi sang đã đóng; không đạt thì chuyển sang đã mở lại. Không có kết quả hợp lệ thì không đóng lỗi.



Hình 3.2.6. Sơ đồ BPMN quy trình xử lý lỗi và kiểm thử lại. [Tệp sơ đồ](drawio/BPMN_Quality_06_Xu_ly_loi_va_kiem_thu_lai_v1.drawio).

## Quy tắc nghiệp vụ tổng hợp

### 3.3.1 Nhập tài liệu và trích xuất yêu cầu

Chỉ tài liệu vượt qua kiểm tra đầu vào mới được lập hồ sơ để trích xuất. Nội dung trích xuất là đề xuất, BA cần rà soát và lựa chọn trước khi xác nhận. Hệ thống kiểm tra lại trùng lặp và xung đột trước khi ghi để tránh tạo yêu cầu không hợp lệ hoặc lưu dữ liệu dở dang.

### 3.3.2 Soạn thảo và phê duyệt yêu cầu

Yêu cầu phải có đủ nội dung bắt buộc và được gửi từ lần cập nhật hiện hành. Admin rà soát và có thể yêu cầu chỉnh sửa. Chỉ khi nội dung qua kiểm định và được phê duyệt, yêu cầu mới được ghi nhận làm phiên bản chuẩn.

### 3.3.3 Lập và phê duyệt kế hoạch kiểm thử

Kế hoạch phải thuộc đúng dự án và có phạm vi hợp lệ trước khi gửi duyệt. Người phê duyệt cần đáp ứng điều kiện độc lập theo quy định hiện hành. Trước khi duyệt, Hệ thống kiểm tra lại phạm vi và các đối tượng tham chiếu; kế hoạch được duyệt phải lưu ảnh chụp phạm vi làm căn cứ tạo lượt chạy.

### 3.3.4 Thiết kế và phê duyệt ca kiểm thử

Ca kiểm thử cần nêu hành động thực hiện và kết quả mong đợi đủ để kiểm chứng, đồng thời duy trì liên kết với yêu cầu nguồn khi có sử dụng nguồn. Tester gửi ca để Admin xét duyệt; thao tác gửi không tự phê duyệt ca. Lỗi kiểm tra tự động thuộc mức chặn hoặc trường hợp trùng chưa được giải trình sẽ ngăn việc tạo phiên bản đã duyệt.

### 3.3.5 Phân công và thực thi kiểm thử

Lượt kiểm thử chỉ được tạo từ kế hoạch đã duyệt với phạm vi còn hợp lệ. Người thực hiện phải được giao đúng lượt hoặc ca và có quyền thực thi. Kết quả cần tuân theo trình tự chuyển trạng thái mà Hệ thống chấp nhận. Nếu chưa có đủ kết quả, chỉ được hoàn tất một phần khi thiết lập dự án cho phép.

### 3.3.6 Xử lý lỗi và kiểm thử lại

Lỗi gắn với kết quả kiểm thử phải tham chiếu đúng dự án, lượt chạy và phiên bản ca; kết quả nguồn cần ở trạng thái không đạt. Trước khi ghi nhận lần kiểm thử lại, Hệ thống xác minh lỗi đang chờ kiểm thử lại, ca được giao đúng người và kết quả thuộc phiên bản ca liên quan. Kết quả đạt dẫn đến đóng lỗi; kết quả không đạt đưa lỗi trở lại bước xử lý.

## Lưu ý khi dùng sơ đồ

1. làn vai trò BA, Tester và Admin được lấy theo đặc tả ca sử dụng; làn “Người được giao xử lý” ở quy trình 06 phản ánh trường phân công trong quy trình xử lý lỗi, không phải vai trò mới.
2. Ma trận khi vận hành có thể được Admin cập nhật. Nên xác minh quyền thao tác thực tế trước khi dùng các sơ đồ như ma trận truy cập/quy trình vận hành triển khai.
3. Sơ đồ không thêm họp, email, sửa hệ thống hoặc phát hành nếu không có căn cứ trong hệ thống và đặc tả đã rà.
4. Cổng rẽ nhánh lặp tại thực thi biểu thị còn ca cần xử lý, không xác nhận chạy song song. Các nhánh ngoại lệ còn phụ thuộc quyền thao tác, lần cập nhật và thiết lập của từng quy trình.
