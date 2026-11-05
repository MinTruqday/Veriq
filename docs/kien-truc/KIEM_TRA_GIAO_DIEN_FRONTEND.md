# Kiểm tra và hoàn thiện giao diện Veriq

Cập nhật lần cuối: 05/11/2026. Danh sách này theo các route và mục điều hướng đang có trong frontend. Chỉ đánh dấu hoàn tất sau khi kiểm tra trang có dữ liệu, quyền phù hợp và thao tác chính; kiểm tra desktop tại 1280, 1440 và 1920 px. Các lượt kiểm tra dùng API giả được ghi rõ, không được hiểu là nghiệm thu API thật.

## Mục đích và phạm vi

Đây là kế hoạch hoàn thiện toàn bộ giao diện hiện có, không chỉ các lỗi đã được người dùng chỉ ra. Không bỏ route, thao tác, trường dữ liệu, API hay quyền đang dùng. Có thể sắp xếp lại và thu gọn phần ít dùng để làm rõ thứ tự thông tin; mọi chức năng vẫn phải truy cập được và giữ đúng hành vi.

Mỗi trang được làm trọn một lượt: rà cấu trúc và dữ liệu → chỉnh bố cục, nội dung và thao tác → chạy trang với dữ liệu có ý nghĩa → kiểm quyền, trạng thái và lỗi → xem ảnh ở ba kích thước desktop → ghi bằng chứng và tick trang đó. Chỉ sau khi qua bước này mới chuyển trang tiếp theo. Một lượt rà toàn cục cuối cùng kiểm tra các thành phần dùng chung và hồi quy.

## Quy tắc áp dụng cho mọi trang

- **Thứ bậc:** tiêu đề trang, mục tiêu/trạng thái, thông tin chính, thao tác chính, nội dung chi tiết theo đúng mức độ quan trọng. Tránh lặp tiêu đề, mô tả vô nghĩa, thuật ngữ nội bộ và role trong câu chữ khi người dùng chỉ cần biết hành động tiếp theo.
- **Bố cục:** một vùng nội dung chính có độ rộng nhất quán; căn lề và khoảng cách theo hệ token hiện có; không lồng nhiều khung trắng/bảng vào nhau nếu không biểu thị một nhóm dữ liệu thực sự. Dùng bảng cho dữ liệu so sánh theo hàng/cột, biểu mẫu cho nhập liệu, danh sách khi cần quét nhanh. Hạn chế cột rỗng, hàng quá cao và chữ bị cắt.
- **Thao tác:** hành động thường dùng ở gần nội dung tương ứng; thao tác nguy hiểm có xác nhận; icon chỉ dùng cho hành động quen thuộc và có tên truy cập/tooltip; hành động quan trọng vẫn có nhãn chữ. Bộ lọc, tìm kiếm và sắp xếp đặt cạnh danh sách chúng điều khiển.
- **Dữ liệu:** không thêm dữ liệu mẫu/demo vào sản phẩm hoặc dùng giá trị mẫu làm dữ liệu thật. Không hardcode người dùng, dự án, kết quả, quyền, số liệu, ngưỡng nghiệp vụ, lựa chọn động, trạng thái nghiệp vụ hay route. Lấy chúng từ API/cấu hình có thẩm quyền; dùng catalog tập trung để dịch enum và chuỗi giao diện. Không suy diễn số 0 khi dữ liệu thiếu.
- **Quyền:** quyền API vẫn là nguồn quyết định. Giao diện chỉ ẩn/hiện hành động theo quyền trả về và phải xử lý từ chối quyền từ server; không hardcode role thành cơ chế phân quyền. Những nơi người quản trị cần chọn role vẫn ghi tên role rõ ràng trong bộ chọn.
- **Ngôn ngữ:** dùng locale người dùng cho nội dung sinh động; nhãn giao diện nhất quán, không trộn Việt/Anh trừ thuật ngữ người dùng cần nhận diện. Không hiện mã trạng thái, mã lỗi hay tên capability nội bộ.
- **Trạng thái:** mọi danh sách/form phải có tải, rỗng, lỗi, thử lại, thành công, lưu đang xử lý/đã lưu/thất bại, dữ liệu dài và nội dung chưa đủ quyền. Không báo thành công giả hoặc xóa nội dung người dùng đã nhập sau lỗi.
- **Màn hình và truy cập:** desktop 1280/1440/1920 px; không tràn ngang, chồng lấn, cắt chữ hoặc tạo khoảng trống bất thường. Kiểm tra bàn phím, focus, nhãn form, tương phản, bảng có cuộn trong vùng phù hợp và tên dài.
- **Mã nguồn:** không thêm code comments. Không nhầm comments với docstrings: giữ nguyên docstrings có ý nghĩa, không đổi thành comments hoặc xóa chúng khi chỉnh code. Không thêm test fixture vào sản phẩm; dữ liệu kiểm tra đặt ngoài luồng người dùng và không commit vào repository nếu không được yêu cầu.

## Phạm vi sửa theo từng trang

Phạm vi dưới đây là đầu việc bắt buộc cho từng route/view. Các điều kiện chung phía trên cũng áp dụng cho từng dòng.

### Công khai, đăng nhập và tài khoản

| Trang | Sửa giao diện và thao tác |
|---|---|
| Trang chủ `/` | Làm rõ giá trị sản phẩm và đường vào đăng nhập; bỏ câu quảng cáo rỗng; căn lại khối nội dung, logo và CTA; kiểm tra điều hướng. |
| Đăng nhập `/dang-nhap` | Nhóm lỗi đăng nhập sát form; giữ dữ liệu email khi lỗi; icon hiện/ẩn mật khẩu có nhãn truy cập; bố trí quên mật khẩu và đăng nhập bằng khóa truy cập; không có đăng nhập Google. |
| Quên mật khẩu `/quen-mat-khau` | Một form email gọn, giải thích kết quả trung tính; chặn gửi lặp; trạng thái gửi/lỗi/thành công rõ và giữ email. |
| Nhập mã khôi phục `/xac-thuc` | Hiển thị rõ email đích, nhập và gửi lại mã, thời gian chờ nếu API cung cấp; lỗi mã đặt cạnh ô nhập; điều hướng sửa email. |
| Đặt lại mật khẩu `/dat-lai-mat-khau` | Gom hai ô mật khẩu, quy tắc và nút; icon hiện/ẩn; giữ lỗi xác nhận; trạng thái token hết hạn và gửi lại. |
| Xác minh email `/xac-minh-thu-dien-tu` | Phân biệt đang xác minh, thành công, token lỗi/hết hạn; CTA tiếp theo nhất quán, không để trang trắng. |
| Điều khoản `/dieu-khoan` | Mục lục dễ quét, neo cuộn đúng tiêu đề, độ rộng dòng đọc được; giữ đầy đủ nội dung và ngày hiệu lực từ nguồn. |
| Cài đặt tài khoản `/cai-dat` | Tách hồ sơ, mật khẩu, phiên và thông báo thành nhóm dễ hiểu; lưu theo nhóm; phân biệt lỗi từng nhóm; xác nhận đóng phiên và không đóng phiên hiện tại. |

### Không gian dự án và lập kế hoạch

| Trang | Sửa giao diện và thao tác |
|---|---|
| Danh sách dự án `/du-an` | Cố định cấu trúc cột theo nội dung thay vì độ dài mã; ngày, người phụ trách, tiến độ, hoạt động và cập nhật gần nhất thẳng hàng; tìm kiếm/lọc/lịch đặt cạnh nhau; tạo, nhận lời mời, lưu trữ và khôi phục có trạng thái. |
| Tổng quan `/du-an/{id}` | Đưa tiến độ và số liệu chính lên trước; hoạt động AI gọn, không có khoảng trắng giả; đánh giá AI và số liệu chi tiết thu gọn đến khi người dùng mở; liên kết khu vực dạng danh sách điều hướng thay vì nhiều thẻ lồng nhau; lỗi, lần chạy, thay đổi có nội dung và liên kết nguồn. |
| Danh sách công việc `/lap-ke-hoach/list` | Tổ chức bộ lọc, tìm kiếm, nhóm và sắp xếp thành một thanh; mã/tên/người phụ trách/ngày/ưu tiên có cột ổn định; thao tác hàng dễ nhận; giữ lọc khi mở/đóng chi tiết. |
| Danh sách chờ `/lap-ke-hoach/backlog` | Làm rõ việc chưa xếp lịch, thứ tự ưu tiên, ước lượng, người phụ trách và phụ thuộc; kéo thả có vùng đích và phản hồi; bảng không bị khung con hoặc cột lệch. |
| Bảng công việc `/lap-ke-hoach/board` | Cột ngang cuộn mượt, kéo thả thẻ; mở/đóng cột theo chiều ngang, giữ độ rộng đọc được; thẻ ưu tiên thông tin tên, mã, người phụ trách, ngày và nhãn; menu thao tác gọn; không mã hóa màu nghiệp vụ ngoài bảng màu chuẩn. |
| Đợt lặp `/lap-ke-hoach/sprint` | Chỉ hiện cho Scrum; tóm tắt mục tiêu, ngày, tiến độ, sức chứa và việc còn lại; thao tác bắt đầu/kết thúc/đưa việc vào đợt có xác nhận; Kanban không truy cập được route Sprint. |
| Lộ trình `/lap-ke-hoach/roadmap` | Trục thời gian và danh sách hạng mục căn cùng dữ liệu; ngày bắt đầu/hạn có nhãn rõ, không làm đậm lẫn nhau; lọc theo thời gian bằng lịch; thu gọn/mở cấp cha-con ngang; phân biệt nhóm việc bằng cấu trúc, không màu tùy tiện; tránh khung lặp và cắt nội dung khi cuộn. |
| Bản phát hành `/ban-phat-hanh` | Danh sách phiên bản, trạng thái, ngày, phạm vi và điều kiện phát hành; chi tiết rủi ro/độ phủ/lần chạy; quyết định phát hành có căn cứ, quyền và xác nhận. |

### Yêu cầu và thay đổi

| Trang | Sửa giao diện và thao tác |
|---|---|
| Yêu cầu `/yeu-cau` | Danh sách có mã/tên/trạng thái/phiên bản/người phụ trách; nhập tài liệu và nhập thủ công có luồng riêng dễ tìm; bộ lọc và bảng không lấn nút; tạo/sửa/gửi rà soát/duyệt giữ toàn bộ trường. |
| Hồ sơ đảm bảo `/ho-so-dam-bao` | Nêu rõ mức bao phủ, nguồn thiếu và hành động kế tiếp; tách số liệu, yêu cầu và quyết định; nhãn trạng thái thân thiện; thao tác chỉ hiện theo quyền. |
| Phiếu làm rõ `/phieu-lam-ro` | Câu hỏi, người cần trả lời, hạn và trạng thái thành luồng đọc được; phân biệt nội dung trả lời với lịch sử; không viết “yêu cầu role X chỉnh sửa”; nút trả lời/gửi lại đặt theo trạng thái. |
| Phân tích thay đổi `/thay-doi` | Tóm tắt thay đổi, nguồn trước/sau, ảnh hưởng đến test và quyết định; bảng đối chiếu có cột ưu tiên; không trộn chi tiết kỹ thuật vào nhãn chính. |

### Phân tích và thiết kế kiểm thử

| Trang | Sửa giao diện và thao tác |
|---|---|
| Chiến lược kiểm thử `/quan-tri-kiem-thu` | Tách mục tiêu, phạm vi, cách tiếp cận, rủi ro, tiêu chí và lịch; biểu mẫu theo nhóm; trạng thái duyệt và lịch sử; thuật ngữ thống nhất với Test Plan. |
| Phân tích kiểm thử `/phan-tich-kiem-thu` | Tổ chức điều kiện, quy tắc, nguồn và khoảng trống theo Requirement; đưa việc cần quyết định lên trước; giữ liên kết truy vết; nhập/xuất và trạng thái tải/lỗi rõ. |
| Kho kiểm thử `/kho-kiem-thu` | Cây thư mục và danh sách đồng bộ, chọn thư mục không che nội dung; tìm/lọc; trạng thái rỗng có hướng tạo; thao tác nhiều mục có thanh hành động riêng. |
| Ca kiểm thử `/ca-kiem-thu` | Danh sách và chi tiết có mã/tên/trạng thái/phiên bản/nguồn; tạo/sửa/duyệt/gửi rà soát; bước kiểm thử đọc tuần tự, không lộ mã nội bộ; quyền giữ nguyên. |
| Nghĩa vụ kiểm thử `/ca-kiem-thu/do-day-du` | Tiêu chí, bằng chứng, độ phủ và phần thiếu trình bày theo từng Requirement; không biến dữ liệu thiếu thành 0; giải thích hành động khắc phục. |
| Hoạt động AI trong ca kiểm thử `/ca-kiem-thu/ai` | Lịch sử lượt Agent theo yêu cầu người dùng; tiêu đề dễ hiểu, trạng thái dịch, nguồn mở được; chi tiết kỹ thuật nằm trong phần mở rộng; không hiện khung trống khi không có lượt. |
| Kịch bản `/ca-kiem-thu/kich-ban` | Nhóm điều kiện và ca liên quan theo luồng; thứ tự và trạng thái nổi bật; tạo, liên kết, tái sử dụng có phản hồi; phân trang và lọc giữ lựa chọn. |
| Mẫu ca kiểm thử `/ca-kiem-thu/mau` | Tìm mẫu, xem trước cấu trúc, tạo/sửa/áp dụng; phân biệt mẫu hệ thống và mẫu dự án; không làm mất trường mở rộng. |
| Mã kiểm thử tự động `/ca-kiem-thu/tu-dong-hoa` | Hiển thị liên kết mã, phiên bản, môi trường và kết quả đồng bộ; xuất mã chỉ khi được quyền; không biến AI Agent thành luồng tự chạy. |
| Ca kiểm thử API `/ca-kiem-thu/api` | Danh sách API theo phương thức/đường dẫn; schema và xác thực trong phần chi tiết; dữ liệu nhạy cảm che theo quyền; trạng thái đồng bộ dễ hiểu. |
| Nhập và xuất `/ca-kiem-thu/nhap-xuat` | Chọn tệp, ánh xạ cột, xem trước lỗi/dữ liệu, xác nhận nhập; tiến trình và kết quả đếm theo API; xuất chọn phạm vi/định dạng; không mất tệp hoặc lựa chọn khi lỗi. |
| Bước dùng lại `/buoc-dung-lai` | Thư viện bước có tên, mục tiêu, dữ liệu, kết quả mong đợi và phiên bản; tìm kiếm; liên kết ca; cảnh báo thay đổi ảnh hưởng. |
| Dữ liệu kiểm thử `/du-lieu-kiem-thu` | Nhóm bộ dữ liệu, biến, môi trường và quyền; che bí mật; nhập/xuất có xem trước; bảng dài đọc được. |
| Bộ kiểm thử `/bo-kiem-thu` | Bộ, thành viên ca, thứ tự, lọc và tổng số; thêm/bỏ nhiều mục có xác nhận; trạng thái đồng bộ; tránh thao tác nằm ngoài màn hình. |

### Kế hoạch, thực thi và lỗi

| Trang | Sửa giao diện và thao tác |
|---|---|
| Kế hoạch kiểm thử `/ke-hoach-kiem-thu` | Thông tin kế hoạch, phạm vi, mục tiêu, chiến lược, cấp/loại kiểm thử, vai trò, môi trường, dữ liệu, tiêu chí, lịch, rủi ro, lỗi và deliverables thành các mục quét được; phân công và duyệt theo quyền. |
| Lần chạy kiểm thử `/lan-chay-kiem-thu` | Danh sách theo Test Plan/build/môi trường/trạng thái; lọc và hành động tạo/chạy/kết thúc; số liệu PASS/FAIL/BLOCKED rõ; thông tin lỗi môi trường và kiểm thử phi chức năng theo quyền. |
| Kết quả thực thi `/thuc-thi` | Danh sách ca theo trạng thái, bước và bằng chứng; nhập kết quả liền mạch; cập nhật lỗi liên kết; lưu tự động có trạng thái; điều hướng ca trước/sau. |
| Tự động hóa `/tu-dong-hoa` | Tách cấu hình tích hợp, kịch bản và kết quả; không tự chạy thay thao tác người dùng đã yêu cầu; trạng thái đồng bộ, log và lỗi có phần tóm tắt rồi mới mở chi tiết. |
| Lỗi `/loi` | Mức độ, ưu tiên, trạng thái, người phụ trách, bước tái hiện và liên kết test phân biệt rõ; lọc theo dự án/lần chạy; chuyển trạng thái có xác nhận; lịch sử không lẫn với mô tả. |

### Theo dõi, báo cáo và tài liệu

| Trang | Sửa giao diện và thao tác |
|---|---|
| Giám sát kiểm thử `/giam-sat-kiem-thu` | Chỉ số và xu hướng có nhãn/phạm vi/kỳ; bộ lọc kỳ và nguồn; không dùng biểu đồ không có dữ liệu; bảng chi tiết mở từ chỉ số. |
| Truy vết `/truy-vet` | Ma trận Requirement–Scenario–Case–Run–Defect, lọc đầu/cuối; thiếu liên kết nổi bật; cuộn bảng trong vùng; mở được từng thực thể. |
| Báo cáo `/bao-cao` | Điều hướng giữa báo cáo công việc và kiểm thử; tạo, soạn, duyệt, phát hành, xuất và theo dõi người nhận theo quyền; trình soạn và bản xem trước phân biệt; giữ dữ liệu khi lỗi. |
| Nhật ký kiểm toán `/nhat-ky-kiem-toan` | Bộ lọc thời gian/người/đối tượng/hành động; thời điểm và thay đổi đọc được; dữ liệu nhạy cảm không lộ; phân trang và xuất theo quyền. |
| Hoạt động AI `/ra-soat-ai` | Danh sách tác vụ do người dùng khởi tạo, trạng thái và kết quả; bước xử lý kỹ thuật mặc định thu gọn; chứng cứ, đề xuất và thao tác tiếp tục/hủy rõ quyền. |
| Tài liệu tham chiếu `/tri-thuc` | Tìm kiếm, nguồn, bộ lọc và quyền; kết quả có trích đoạn/phiên bản/nguồn; tải và mở đọc riêng; trạng thái index không hiện mã nội bộ. |
| Trình đọc tài liệu `/tai-lieu/{id}` | Thanh công cụ theo định dạng, nội dung/bảng/trang phù hợp, tìm trong tài liệu, nguồn trích dẫn, tóm tắt và tải gốc; lỗi định dạng có hướng xử lý, không màn trắng. |
| Cài đặt dự án `/cai-dat` | Các phần quyền, thành viên, cấu hình, thông báo, tích hợp và phân tích được nhóm/điều hướng; chỉ hiện phần có quyền; form lưu riêng, trạng thái rõ; giữ role ở bộ chọn quyền cần thiết. |

### Thông báo, vận hành và lỗi hệ thống

| Trang | Sửa giao diện và thao tác |
|---|---|
| Thông báo `/thong-bao` | Phân biệt tất cả/chưa đọc, nhóm theo thời gian, xem nhanh/mở nguồn, đánh dấu đã đọc; trạng thái rỗng và lỗi; không coi đọc thông báo là đã xem báo cáo. |
| Vận hành: tổng quan `/van-hanh` | Tình trạng dịch vụ, tải và cảnh báo có nguồn/thời điểm; lỗi đặt cạnh dịch vụ liên quan; tóm tắt trước chi tiết kỹ thuật. |
| Vận hành: tài khoản | Tìm/lọc, trạng thái tài khoản, vai trò và thao tác quản trị; xác nhận thao tác nguy hiểm; dữ liệu trang giữ khi sửa. |
| Vận hành: bảng lương | Thông tin chọn tệp không tràn; xem trước lỗi/dòng/đơn giá; phân biệt chi phí và phân công nguồn lực; không báo lưu khi import thất bại. |
| Vận hành: cấu hình nền tảng | Chia nhóm cấu hình, giải thích tác động, giá trị hiện tại và lưu/khôi phục; không hardcode cấu hình runtime vào giao diện. |
| Vận hành: đánh giá AI | Mẫu đánh giá, phiên bản và kết quả theo lô; lỗi/tiến trình có thể đọc; đầu ra theo locale; phân biệt hành động người dùng với xử lý nền. |
| Lỗi và không tìm thấy | Thông báo ngắn, nguyên nhân có thể hành động, thử lại/quay về nơi hợp lệ; không phơi stack trace, mã nội bộ hoặc link sai quyền. |

### Thành phần và chế độ xem dùng chung

| Khu vực | Sửa giao diện và thao tác |
|---|---|
| Khung ứng dụng và điều hướng | Rà sidebar, breadcrumb, tiêu đề, tìm kiếm toàn cục, thông báo và tài khoản; route bị cấm phải rời trang; active state chính xác; không trùng điều hướng con. |
| Modal, form, bảng và trạng thái | Chuẩn hóa kích thước, footer, nút, validate, focus, phím Escape, cuộn nội dung, cột bảng, empty/error/loading và thông báo lưu; giữ nguyên hành vi API. |
| Cộng tác và chia sẻ | Viewer/editor/commenter áp dụng cùng quy ước các nơi có cộng tác; người chỉ xem không thấy thao tác sửa; bình luận và quyền gắn đúng đối tượng/phiên bản. |
| Danh sách tab trong một route | Mỗi tab có trạng thái URL hoặc lưu lựa chọn nhất quán, nội dung không mất khi chuyển tab nếu chưa lưu; kiểm role/quyền riêng cho từng tab. |

## Tiêu chí tick một trang

Chỉ đánh dấu ☑ nếu đồng thời đủ: (1) trang đã được rà trên toàn bộ phần nhìn thấy và phần mở rộng, (2) dữ liệu thật hoặc API giả có fixture tách khỏi source sản phẩm và đủ phong phú để lộ lỗi bố cục, (3) tải/rỗng/lỗi/quyền được kiểm, (4) thao tác chính đã thử thành công và thất bại, (5) 1280/1440/1920 px không tràn/cắt/chồng và ảnh đã được xem bằng mắt, (6) console không có lỗi, (7) `git diff --check` và kiểm tra định dạng/lint phạm vi file đạt, (8) ghi đúng route, role, nguồn dữ liệu và ảnh. Nếu có API giả thì ghi rõ; không gọi đó là nghiệm thu tích hợp thật.

Các route có nhiều tab/view chỉ được tick sau khi mọi view thuộc trang đó qua kiểm tra. Một trang có thay đổi bố cục nhưng chưa kiểm thao tác không được tick. Không tick lại phần nhỏ; nếu hồi quy làm trang đã tick hỏng, bỏ tick trang đó, ghi nguyên nhân rồi nghiệm thu lại toàn trang.

## Cách làm theo lô

1. Hoàn tất khung dùng chung và dự án/lập kế hoạch theo đúng thứ tự checklist.
2. Hoàn tất yêu cầu/thay đổi, rồi toàn bộ phân tích/thiết kế kiểm thử.
3. Hoàn tất kế hoạch/thực thi/lỗi; tiếp theo theo dõi/báo cáo/tài liệu.
4. Hoàn tất thông báo/vận hành/tài khoản/lỗi; sau đó kiểm hồi quy toàn bộ route.
5. Chỉ sau khi các trang đủ bằng chứng mới chạy production build và xác minh Docker frontend một lần từ mã đã ghép. Không xây service backend không đổi.

Không chuyển sang trang khác để bắt đầu chỉnh dở trong lúc trang hiện tại chưa qua cổng tick. Nếu phát hiện lỗi ảnh hưởng nhiều trang, ghi vấn đề dùng chung, hoàn tất sửa tại component dùng chung, chạy lại toàn bộ trang đã tick bị ảnh hưởng rồi mới tiếp tục thứ tự.

## Trang đã hoàn tất

| Trang         | Trạng thái | Bằng chứng                                                                                                                                                                                                                                                                                                                                                     |
| ------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Yêu cầu       | ☑         | Smoke trình duyệt với dữ liệu giả ở 1280, 1440 và 1920 px: danh sách, chi tiết, yêu cầu chỉnh sửa, nhập tài liệu và lựa chọn trích xuất BR; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-requirements-{1280,1440,1920}.png`, `/tmp/veriq-requirement-detail-smoke-{1280,1440,1920}.png`, `/tmp/veriq-requirement-import-smoke-{1280,1440,1920}.png`. |
| Hồ sơ đảm bảo | ☑         | Smoke trình duyệt với dữ liệu giả ở 1280, 1440 và 1920 px: trạng thái/nhãn không lộ role, thao tác rà soát hiện đúng theo quyền QA, không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-assurance-1280.png`, `/tmp/veriq-assurance-1440.png`, `/tmp/veriq-assurance-1920.png`.                                                                              |
| Phiếu làm rõ  | ☑         | Smoke trình duyệt với dữ liệu giả ở 1280, 1440 và 1920 px: tạo phiếu, đưa Requirement đang rà soát về bản nháp, trạng thái và nội dung không lộ role, không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-requirement-clarification-1280.png`, `/tmp/veriq-requirement-clarification-1440.png`, `/tmp/veriq-requirement-clarification-1920.png`.            |
| Trang chủ     | ☑         | Nội dung, điều hướng đăng nhập/điều khoản và bố cục kiểm tra ở 1280, 1440, 1920 px; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-home-{1280,1440,1920}.png`.                                                                                                                                                                                                 |
| Đăng nhập     | ☑         | Trên giao diện Docker, đăng nhập tài khoản QA thật thành công và chuyển tới `/du-an`, không lỗi API/JavaScript. Kiểm tra bố cục, nút hiện/ẩn mật khẩu, không có đăng nhập Google và không tràn ngang ở 1280, 1440, 1920 px. Ảnh bố cục: `/tmp/veriq-login-{1280,1440,1920}.png`; ảnh phiên đăng nhập: `/tmp/veriq-login-smoke.png`.                                               |
| Quên mật khẩu | ☑         | Smoke trình duyệt ở 1280, 1440, 1920 px với API giả: gửi đúng email, chuyển sang nhập mã; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-forgot-password-{1280,1440,1920}.png`.                                                                                                                                                                                        |
| Đặt lại mật khẩu | ☑      | Smoke trình duyệt ở 1280, 1440, 1920 px với token/API giả: gửi đúng token và mật khẩu mới, chuyển về đăng nhập; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-reset-password-{1280,1440,1920}.png`.                                                                                                                                                                |
| Nhập mã khôi phục | ☑     | Smoke trình duyệt ở 1280, 1440, 1920 px với API giả: gửi mã, chuyển đúng sang đặt mật khẩu; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-verification-code-{1280,1440,1920}.png`.                                                                                                                                                                                 |
| Xác minh email | ☑        | Smoke trình duyệt ở 1280, 1440, 1920 px với API giả: gửi đúng token, hiện kết quả xác minh và liên kết đăng nhập; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-email-verification-{1280,1440,1920}.png`.                                                                                                                                                       |
| Điều khoản | ☑            | Smoke trình duyệt ở 1280, 1440, 1920 px: điều hướng mục trong trang và đúng neo nội dung; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-terms-{1280,1440,1920}.png`.                                                                                                                                                                                              |
| Tài khoản | ☑             | Smoke trình duyệt với API giả ở 1280, 1440, 1920 px: lưu hồ sơ, lưu tùy chọn thông báo, đóng phiên khác và giữ phiên hiện tại; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-account-{1280,1440,1920}.png`.                                                                                                                                                      |
| Danh sách dự án | ☑          | Smoke trình duyệt với dữ liệu giả tại 1280, 1440 và 1920 px: lọc theo ngày, tìm mã, nhận lời mời, tạo/lọc/khôi phục dự án; xác nhận ngày không hợp lệ chặn lưu, nhãn tạo dự án không lộ BA/QA, không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-projects-{1280,1440,1920}.png`.                                                                            |
| Tổng quan dự án | ☑          | Smoke trình duyệt với dữ liệu có nội dung ở 1280/1440/1920 px; ảnh đã xem, không tràn ngang; trạng thái AI có dữ liệu/rỗng được kiểm, nhãn trạng thái đã dịch; không có quyền AI thì phần đánh giá bị ẩn; hai thao tác AI không gửi yêu cầu khi tải trang và chỉ gửi sau khi bấm; lỗi API giữ trang và hiện nút tải lại. API giả, chưa phải nghiệm thu Docker/API thật. Ảnh: `/tmp/veriq-dashboard-{1280,1440,1920}.png`, `/tmp/veriq-dashboard-ai-expanded-1280.png`. |

## Trang cần rà soát theo thứ tự

### Công khai, xác thực và tài khoản

| Trang                | Route                   | Trạng thái |
| -------------------- | ----------------------- | ---------- |
| Trang chủ            | `/`                     | ☑          |
| Đăng nhập            | `/dang-nhap`            | ☑          |
| Quên mật khẩu        | `/quen-mat-khau`        | ☑          |
| Đặt lại mật khẩu     | `/dat-lai-mat-khau`     | ☑          |
| Xác minh thư điện tử | `/xac-minh-thu-dien-tu` | ☑          |
| Nhập mã khôi phục    | `/xac-thuc`             | ☑          |
| Điều khoản           | `/dieu-khoan`           | ☑          |
| Cài đặt tài khoản    | `/cai-dat`              | ☑          |

Trang chủ có nội dung và liên kết được kiểm tra ở 1280, 1440 và 1920 px; không tràn ngang hoặc lỗi JavaScript. Ảnh: `/tmp/veriq-home-1280.png`, `/tmp/veriq-home-1440.png`, `/tmp/veriq-home-1920.png`.

### Không gian dự án và lập kế hoạch

| Trang               | Route                                     | Trạng thái |
| ------------------- | ----------------------------------------- | ---------- |
| Danh sách dự án     | `/du-an`                                  | ☑          |
| Tổng quan dự án     | `/du-an/{projectId}`                      | ☑          |
| Danh sách công việc | `/du-an/{projectId}/lap-ke-hoach/list`    | ☐          |
| Danh sách chờ       | `/du-an/{projectId}/lap-ke-hoach/backlog` | ☐          |
| Bảng công việc      | `/du-an/{projectId}/lap-ke-hoach/board`   | ☐          |
| Đợt lặp (Scrum)     | `/du-an/{projectId}/lap-ke-hoach/sprint`  | ☐          |
| Lộ trình            | `/du-an/{projectId}/lap-ke-hoach/roadmap` | ☐          |
| Bản phát hành       | `/du-an/{projectId}/ban-phat-hanh`        | ☐          |

### Bảo đảm yêu cầu

| Trang              | Route                              | Trạng thái |
| ------------------ | ---------------------------------- | ---------- |
| Yêu cầu            | `/du-an/{projectId}/yeu-cau`       | ☑         |
| Hồ sơ đảm bảo      | `/du-an/{projectId}/ho-so-dam-bao` | ☑         |
| Phiếu làm rõ       | `/du-an/{projectId}/phieu-lam-ro`  | ☑         |
| Phân tích thay đổi | `/du-an/{projectId}/thay-doi`      | ☐          |

### Phân tích và thiết kế kiểm thử

| Trang                          | Route                                        | Trạng thái |
| ------------------------------ | -------------------------------------------- | ---------- |
| Chiến lược kiểm thử            | `/du-an/{projectId}/quan-tri-kiem-thu`       | ☐          |
| Phân tích kiểm thử             | `/du-an/{projectId}/phan-tich-kiem-thu`      | ☐          |
| Kho kiểm thử                   | `/du-an/{projectId}/kho-kiem-thu`            | ☐          |
| Ca kiểm thử                    | `/du-an/{projectId}/ca-kiem-thu`             | ☐          |
| Nghĩa vụ kiểm thử              | `/du-an/{projectId}/ca-kiem-thu/do-day-du`   | ☐          |
| Hoạt động AI trong ca kiểm thử | `/du-an/{projectId}/ca-kiem-thu/ai`          | ☐          |
| Kịch bản                       | `/du-an/{projectId}/ca-kiem-thu/kich-ban`    | ☐          |
| Mẫu ca kiểm thử                | `/du-an/{projectId}/ca-kiem-thu/mau`         | ☐          |
| Mã kiểm thử tự động            | `/du-an/{projectId}/ca-kiem-thu/tu-dong-hoa` | ☐          |
| Ca kiểm thử API                | `/du-an/{projectId}/ca-kiem-thu/api`         | ☐          |
| Nhập và xuất ca kiểm thử       | `/du-an/{projectId}/ca-kiem-thu/nhap-xuat`   | ☐          |
| Bước dùng lại                  | `/du-an/{projectId}/buoc-dung-lai`           | ☐          |
| Dữ liệu kiểm thử               | `/du-an/{projectId}/du-lieu-kiem-thu`        | ☐          |
| Bộ kiểm thử                    | `/du-an/{projectId}/bo-kiem-thu`             | ☐          |

### Kế hoạch và thực thi

| Trang             | Route                                  | Trạng thái |
| ----------------- | -------------------------------------- | ---------- |
| Kế hoạch kiểm thử | `/du-an/{projectId}/ke-hoach-kiem-thu` | ☐          |
| Lần chạy kiểm thử | `/du-an/{projectId}/lan-chay-kiem-thu` | ☐          |
| Kết quả thực thi  | `/du-an/{projectId}/thuc-thi`          | ☐          |
| Tự động hóa       | `/du-an/{projectId}/tu-dong-hoa`       | ☐          |
| Lỗi               | `/du-an/{projectId}/loi`               | ☐          |

### Theo dõi, báo cáo và nguồn tài liệu

| Trang                           | Route                                      | Trạng thái |
| ------------------------------- | ------------------------------------------ | ---------- |
| Giám sát kiểm thử               | `/du-an/{projectId}/giam-sat-kiem-thu`     | ☐          |
| Truy vết                        | `/du-an/{projectId}/truy-vet`              | ☐          |
| Báo cáo                         | `/du-an/{projectId}/bao-cao`               | ☐          |
| Nhật ký kiểm toán               | `/du-an/{projectId}/nhat-ky-kiem-toan`     | ☐          |
| Hoạt động AI                    | `/du-an/{projectId}/ra-soat-ai`            | ☐          |
| Tài liệu tham chiếu và tìm kiếm | `/du-an/{projectId}/tri-thuc`              | ☐          |
| Trình đọc tài liệu              | `/du-an/{projectId}/tai-lieu/{documentId}` | ☐          |
| Cài đặt dự án                   | `/du-an/{projectId}/cai-dat`               | ☐          |

### Khu vực dùng chung và vận hành

| Trang                                | Route                 | Trạng thái |
| ------------------------------------ | --------------------- | ---------- |
| Thông báo                            | `/thong-bao`          | ☐          |
| Vận hành nền tảng: Tổng quan         | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Tài khoản         | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Bảng lương        | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Cấu hình nền tảng | `/van-hanh`           | ☐          |
| Vận hành nền tảng: Đánh giá AI       | `/van-hanh`           | ☐          |
| Vận hành nền tảng                    | `/van-hanh`           | ☐          |
| Trang lỗi và không tìm thấy          | `error` / `not-found` | ☐          |

### Các chế độ xem bên trong trang

| Trang             | Chế độ xem                                                                              | Trạng thái |
| ----------------- | --------------------------------------------------------------------------------------- | ---------- |
| Lần chạy kiểm thử | Lần chạy, sự cố môi trường, kiểm thử phi chức năng (theo quyền)                         | ☐          |
| Tự động hóa       | Kết quả, kịch bản và thiết bị, AI Agent (theo quyền)                                    | ☐          |
| Báo cáo           | Công việc/định kỳ, tổng quan, báo cáo kiểm thử, chất lượng/cải tiến                     | ☐          |
| Cài đặt dự án     | Quyền của tôi, dự án, thành viên, năng lực, thông báo, tích hợp, phân tích (theo quyền) | ☐          |
| Thông báo         | Tất cả, chưa đọc                                                                        | ☐          |
| Tài khoản         | Hồ sơ, mật khẩu, phiên đăng nhập, tùy chọn thông báo                                    | ☐          |

## Quy tắc đánh dấu

- Hoàn thiện một trang rồi mới chuyển sang trang tiếp theo theo thứ tự trên.
- Một trang chỉ được đánh dấu ☑ khi đã kiểm tra bố cục, dữ liệu mẫu có ý nghĩa, trạng thái tải/rỗng/lỗi, quyền, thao tác chính và không có lỗi JavaScript hoặc tràn ngang tại các kích thước desktop đã nêu.
- Ghi rõ ảnh/bằng chứng, tài khoản/role và API giả hay API thật. Không dùng build thành công để thay cho kiểm tra giao diện.
- Giữ nguyên mọi chức năng và API hiện hữu khi chỉnh giao diện; không tự thêm màu/icon/tagline ngoài hệ thiết kế chung.
