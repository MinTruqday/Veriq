# Báo cáo công việc trong Veriq

## Mục đích

Báo cáo công việc là một khu vực tùy chọn theo từng dự án, dùng để lập, rà soát, phát hành và theo dõi báo cáo theo kỳ. Tính năng này bổ sung cho báo cáo trạng thái và báo cáo hoàn tất kiểm thử hiện có; không thay thế Test Plan, Test Run hoặc báo cáo kiểm thử chính thức.

Báo cáo có thể là cá nhân, nhóm hoặc toàn dự án. Kỳ báo cáo có ngày giờ bắt đầu, kết thúc và múi giờ. Có thể tạo bản nháp thủ công hoặc đặt lịch để hệ thống chuẩn bị bản nháp và tệp xuất. Mọi bản phát hành đều cần người có quyền rà soát và bấm phát hành.

## Phân quyền theo năng lực và phân công

Quyền báo cáo được quyết định bởi capability hiện hành, membership còn hiệu lực và phạm vi phân công trên từng báo cáo. Tên role của dự án là dữ liệu cấu hình; không có role nào được ngầm hiểu là người viết, người duyệt hoặc người nhận.

| Năng lực hoặc phân công | Tạo và viết | Rà soát và phát hành | Nhận báo cáo |
|---|---|---|---|
| Quản lý cấu hình báo cáo | Quản lý loại báo cáo, mẫu, lịch và phân công trong phạm vi được cấp; quyền này không tự cấp quyền sửa nội dung báo cáo | Không mặc định được duyệt hoặc phát hành | Có thể xem khi được phân công hoặc được cấp quyền đọc |
| Người phụ trách hoặc biên tập viên được giao | Sửa bản nháp và phần nội dung thuộc phạm vi được giao | Không mặc định được tự duyệt nội dung mình đã sửa | Có thể xem, bình luận hoặc tải nếu được cấp riêng |
| Người rà soát được chỉ định | Xem phiên bản gửi rà soát | Yêu cầu chỉnh sửa hoặc duyệt; phát hành chỉ khi có capability tương ứng | Có thể xem, bình luận hoặc tải nếu được cấp riêng |
| Người nhận có quyền xem | Không sửa nội dung | Không duyệt hoặc phát hành | Chỉ xem; bình luận, xác nhận hoặc tải cần capability riêng |
| Quản trị nền tảng | Quản trị tài khoản và cấu hình nền tảng theo quyền hiện có | Không mặc nhiên có quyền nghiệp vụ trong dự án | Chỉ xem báo cáo nếu có membership và quyền nội dung tương ứng |

Quyền được kiểm tra tại API; ẩn nút trên giao diện không phải là cơ chế bảo vệ dữ liệu. Quyền nhận báo cáo có thể thu hồi, sau đó truy cập và tải bị chặn ngay ở backend.

## Luồng trạng thái

1. Người có capability quản lý cấu hình bật báo cáo cho dự án, chọn múi giờ, loại báo cáo được phép và mẫu dùng chung.
2. Người tạo chọn loại, kỳ, chủ sở hữu, biên tập viên, người rà soát và người nhận. Máy chủ xác nhận các tài khoản được phân công là thành viên đang hoạt động và có capability phù hợp.
3. Veriq chụp ảnh dữ liệu công việc trong phạm vi tại thời điểm tạo. Nội dung có thể được biên tập trực tiếp bằng Tiptap; phần dữ liệu nguồn được phân biệt với nội dung do người viết bổ sung.
4. Người viết lưu bản nháp, yêu cầu thay đổi hoặc gửi rà soát. Nội dung sửa đổi dùng revision để từ chối ghi đè nếu một người khác đã cập nhật trước.
5. Người rà soát có thể yêu cầu chỉnh sửa hoặc duyệt. Tệp DOCX/PDF phải hoàn tất cho đúng revision đã duyệt trước khi phát hành.
6. Khi phát hành, Veriq đóng băng nội dung, ảnh chụp số liệu và các tệp đã phát hành. Người nhận có thể xem, bình luận, xác nhận đã nhận/đã đọc hoặc tải nếu được cấp.
7. Chỉnh sửa sau phát hành tạo phiên bản mới, giữ nguyên phiên bản cũ, nhận xét, biên nhận và tệp đã phát hành.

Các thao tác tạo, gửi, duyệt, phát hành, thay đổi người nhận, thu hồi, bình luận và tải được ghi nhận để truy vết. Yêu cầu lặp có cùng khóa idempotency không tạo thêm báo cáo hoặc hành động trùng.

## Lịch báo cáo

Lịch hỗ trợ một lần, theo giờ, ngày, tuần, tháng, quý hoặc năm; có khoảng cách lặp, múi giờ, kỳ tùy chỉnh hoặc kỳ liền trước, hạn xử lý và định dạng DOCX/PDF. Lịch đến hạn tạo một bản nháp riêng cùng yêu cầu xuất tệp. Báo cáo vẫn ở trạng thái nháp; hệ thống không tự gửi rà soát, tự duyệt hay tự phát hành.

Kỳ tháng/năm giữ nguyên ngày neo khi có thể, và lùi về ngày cuối tháng khi tháng đó ngắn hơn. Khi hệ thống bỏ lỡ nhiều kỳ, chỉ tạo kỳ mới nhất đến hạn, ghi số kỳ đã bỏ qua và tiếp tục lịch tương lai; không tạo hàng loạt bản trễ. Nếu thiếu quyền, người rà soát không hợp lệ hoặc dữ liệu không đáp ứng điều kiện, lịch ghi lượt bị chặn và lý do; sau khi xử lý có thể tiếp tục.

Tắt tính năng ở cấp dự án tạm dừng lịch nhưng giữ lịch sử. Bật lại không phát bù mọi kỳ trong thời gian tắt.

## Mẫu và định dạng

Veriq cung cấp mẫu cá nhân, nhóm và dự án bằng ngôn ngữ tương ứng. Có thể nhập DOCX để xem trước, cảnh báo phần bố cục cần kiểm tra và lưu phiên bản mẫu mới. Tệp gốc được giữ lại. Phiên bản mẫu đã dùng trong báo cáo không bị thay đổi khi mẫu mới được tạo.

DOCX/PDF dùng khổ A4, Times New Roman cỡ 14 cho nội dung, lề trên/dưới/phải 2 cm và trái 3 cm, thụt dòng đầu 1,27 cm, cách đoạn trước/sau 6 pt, căn đều; bảng có lưới và dòng đầu bảng lặp lại khi qua trang. Trang đầu không hiện số trang, các trang sau có số trang. Ngày giờ được hiển thị theo ngôn ngữ và múi giờ đã chọn.

Tệp DOCX nhập có thể dùng kiểu đánh số, section, header/footer, drawing hoặc bố cục phức tạp mà bộ chuyển đổi không thể tái tạo chính xác. Veriq hiển thị cảnh báo trước khi lưu mẫu; người dùng cần kiểm tra bản xem trước. Bản gốc luôn còn để tải lại. PDF là bản chuyển đổi và có thể khác Word ở font hoặc ngắt trang.

## Số liệu và giới hạn lịch sử

Bản nháp ghi thời điểm chụp số liệu, phạm vi công việc, trạng thái, mức ưu tiên, ước lượng, người được giao và các giới hạn dữ liệu. Tiến độ tham chiếu tổng hợp công việc hiện có; số việc hoàn tất tại thời điểm chụp không đồng nghĩa với số việc đã hoàn tất trong cả kỳ.

Dữ liệu trạng thái được chụp tại thời điểm lập báo cáo, không dựng lại đầy đủ lịch sử trạng thái ở đầu kỳ. Veriq không suy ra giờ làm thực tế từ thời điểm cập nhật, ước lượng hoặc mức lương. Trường hợp chưa có dữ liệu giờ làm được ghi nhận là thiếu dữ liệu thay vì tạo số liệu ước tính. Người viết có thể cập nhật ảnh chụp có giải thích trước khi gửi rà soát.

## Hỗ trợ AI

AI chỉ chạy khi người dùng bấm yêu cầu. AI có thể soạn, rà soát, tóm tắt hoặc dịch phần nội dung dựa trên dữ liệu đã chụp và văn bản trong báo cáo. Kết quả là đề xuất; người viết chọn phần cần áp dụng. Việc áp dụng kiểm tra revision, lưu nguồn gốc phần AI, không tự gửi, duyệt hoặc phát hành.

Prompt dùng tiếng Anh theo cấu trúc prompt chung của Veriq; đầu ra theo ngôn ngữ báo cáo/người dùng đã chọn. AI không được bịa trải nghiệm cá nhân, cảm xúc, chi tiết quan sát hoặc dữ liệu vận hành không có trong nguồn. Nếu bằng chứng chưa đủ, nội dung phải thể hiện điều chưa biết hoặc yêu cầu người viết bổ sung.

## Lỗi, retry và khôi phục

- Tệp xuất đang chạy hoặc lỗi có trạng thái riêng. Người dùng có thể yêu cầu thử lại; generation mới làm cho kết quả worker cũ không thể ghi đè lên lần mới.
- Nếu dữ liệu nguồn thay đổi trước khi hoàn thành, bản xuất cũ không được gắn với revision mới. Người dùng cần xuất lại revision hiện hành.
- Lỗi worker hoặc gián đoạn được phát hiện khi đối soát. Tác vụ bị ngắt được đánh dấu lỗi và cần thao tác thử lại rõ ràng.
- Lỗi lưu, revision xung đột hoặc mất quyền không hiển thị thành công giả; nội dung nháp còn được giữ để xử lý tiếp khi quyền cho phép.
- Thu hồi quyền trong lúc chạy được kiểm tra lại trước khi lưu kết quả hoặc trả tệp.

## Kiểm chứng chức năng

Kiểm thử tích hợp bao gồm các tổ hợp capability và phân công: người quản lý cấu hình, người viết, người rà soát, người nhận chỉ xem/nhận xét/tải; đồng thời kiểm tra người không có quyền, revision xung đột, mẫu DOCX có bảng/ảnh, tạo DOCX/PDF qua worker, lịch đến hạn tạo nháp, duyệt/phát hành, biên nhận, bình luận, tải/thu hồi quyền, retry sau lỗi nguồn, tính lặp idempotency và đầu ra AI có kiểm soát. Kiểm thử giao diện dùng dữ liệu thử trong dự án cách ly; không ghi dữ liệu mẫu vào dự án nghiệp vụ.
