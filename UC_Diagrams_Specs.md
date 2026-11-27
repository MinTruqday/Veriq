# Phân tích UC và đặc tả sơ đồ UML

## Cấu hình đầu ra và quy ước

- Hệ thống: Veriq.
- Chế độ: PROMPT. Bạn đã làm rõ mục tiêu là chuẩn bị prompt để Visual Paradigm vẽ sơ đồ, nên tài liệu xuất prompt tự đủ, không kèm mã sơ đồ riêng.
- Công cụ nhận prompt: Visual Paradigm AI Chatbot.
- Định dạng: PlantUML.
- Ngôn ngữ nhãn: Tiếng Việt.
- Nguồn nghiệp vụ: `32_Use_Case_Tables.md`, đối chiếu mã nguồn commit `15c4a3f93dcc9145e4cb0846bd25a2b188cf3db1`.
- Không tạo UC quản lý phiên đăng nhập. Trong sơ đồ xác thực chỉ mô tả luồng người dùng đăng nhập.


## Cách viết prompt dựa trên hướng dẫn Visual Paradigm

Visual Paradigm hướng dẫn mô tả quy trình bằng ngôn ngữ tự nhiên có cấu trúc: điểm bắt đầu, người tham gia/trách nhiệm, các bước theo thứ tự, điều kiện rẽ và kết quả, ngoại lệ, cùng phạm vi quy trình. Hướng dẫn Activity nhấn mạnh rằng kết quả cần được rà soát, nhất là điểm bắt đầu/kết thúc, hành động, guard, merge, trách nhiệm và nhánh lỗi. Do đó, mỗi prompt trong tài liệu sẽ đưa đủ đặc tả và bảng phân rã vào một yêu cầu tường minh, yêu cầu PlantUML, và cấm AI tự thêm nghiệp vụ. Đây là cấu trúc biên soạn cho tác vụ này, không phải một cú pháp prompt chính thức bắt buộc của Visual Paradigm.

Nguồn tham khảo:
- Activity prompt guidance: https://blog.visual-paradigm.com/generating-uml-activity-diagrams-with-ai-in-visual-paradigm/
- AI Chatbot natural-language input and supported UML diagrams: https://ai.visual-paradigm.com/tool/ai-chatbot/
- Sequence diagram generation and iterative refinement: https://blog.visual-paradigm.com/generate-uml-sequence-diagrams-instantly-with-ai/

## BƯỚC 0 - Bảng theo dõi (33 UC)

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
---

# UC01 - Đăng nhập

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 3.1.1 | SAI | Nhánh “Quên mật khẩu” đánh số như thể rẽ từ bước 3 nhập email/mật khẩu; trên giao diện, liên kết đã có ngay ở màn hình đăng nhập. | Đổi thành nhánh 2.1, rẽ sau khi hệ thống hiển thị màn hình (đã sửa). |
| 5.1 | MƠ HỒ | “Thông tin không chính xác” không nói tài khoản không tồn tại và mật khẩu sai có cùng phản hồi nhằm tránh tiết lộ tài khoản. | Gộp hai điều kiện vào một nhánh với thông báo chung “Thông tin đăng nhập không chính xác”; quay lại bước 3 (đã sửa). |
| 5.2 | THIẾU | Đặc tả chưa phân biệt tài khoản đang bị khóa do nhiều lần nhập sai với tài khoản bị vô hiệu hóa. Backend trả kết quả khác nhau cho hai trạng thái. | Tách nhánh khóa tạm thời ở bước 8 và tài khoản không hoạt động ở bước 9; cả hai đều kết thúc thất bại (đã sửa). |
| 5.3 | MƠ HỒ | “Vượt quá giới hạn” không nêu ngưỡng và cửa sổ giới hạn. | Ghi ngưỡng API hiện có: quá 5 yêu cầu trong 60 giây; không suy rộng thành chính sách khác (đã sửa). |
| 3 | THIẾU | Tiền điều kiện ban đầu yêu cầu người dùng phải có tài khoản, khiến nhánh thử email không tồn tại không thể thuộc cùng UC. | Chỉ yêu cầu người dùng đang ở màn hình đăng nhập; tài khoản không tồn tại được xử lý trong nhánh sai thông tin (đã sửa). |
| 5 | THIẾU | Chưa nêu trường bắt buộc bị bỏ trống, lỗi hạ tầng xác thực hoặc trạng thái kết thúc thất bại. | Thêm kiểm tra trường bắt buộc ở bước 5 và nhánh lỗi xử lý ở bước 8; bổ sung hậu điều kiện thất bại (đã sửa). Lỗi hạ tầng chưa có thông điệp sản phẩm được xác định, được ghi là giả định. |
| 6 | MÂU THUẪN | Bảng cũ nói đăng nhập bằng email, trong khi service API có thể tra cứu cả email lẫn slug; giao diện commit đang xét chỉ hiển thị trường email. | Mô tả theo hành vi giao diện là email; ghi khả năng slug của API vào mục giả định/giới hạn, không biến thành chức năng UI (đã sửa). |
| 6–7 | THIẾU | Luồng chính gộp xác thực thông tin và kiểm tra trạng thái tài khoản nên chưa chỉ ra điểm ra của sai mật khẩu, khóa tạm thời hoặc vô hiệu hóa. | Tách kiểm tra thông tin đăng nhập và trạng thái tài khoản thành các bước riêng; bổ sung guard cụ thể (đã sửa). |
| 10–11 | MƠ HỒ | “Đăng nhập thành công” không nói hệ thống cấp thông tin xác thực và phản hồi điều hướng nào. | Nêu hệ thống cấp thông tin xác thực rồi điều hướng về trang dự án hoặc đích ban đầu nếu có (đã sửa). |
| Không áp dụng | MƠ HỒ | “Hết phiên” và kiểm tra quyền dự án không phải nhánh của thao tác đăng nhập chưa xác thực. | Không thêm tình huống hết phiên hay quyền chức năng vào UC01; chúng thuộc luồng khác. Không có nút hủy chuyên biệt trong UI; việc người dùng dừng sau lỗi được mô hình hóa như kết thúc chưa đăng nhập, không tạo thay đổi tài khoản. |

Đã kiểm: **5 điểm rẽ, 7 nhánh, 6 tình huống lỗi** (trường bắt buộc thiếu, giới hạn yêu cầu, tài khoản không tồn tại/sai mật khẩu, khóa tạm, vô hiệu hóa, lỗi hạ tầng); đã rà tiền/hậu điều kiện, tác nhân, CRUD quản lý và nhất quán. CRUD không áp dụng cho UC đăng nhập. Không thêm nhánh hết phiên vì người dùng chưa xác thực.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Cho phép người dùng xác thực bằng email và mật khẩu để truy cập Veriq. Giao diện có liên kết chuyển sang UC04 nếu người dùng quên mật khẩu.

**Tiền điều kiện:** Người dùng truy cập được màn hình đăng nhập. Tài khoản tồn tại và đang hoạt động là điều kiện để đăng nhập thành công, nhưng không phải tiền điều kiện chung vì UC cũng xử lý thông tin sai hoặc tài khoản không tồn tại.

**Hậu điều kiện:**
- Thành công: hệ thống chấp nhận thông tin xác thực, tạo thông tin truy cập cần thiết và điều hướng người dùng tới danh sách dự án hoặc đích ban đầu nếu có.
- Thất bại: không cấp quyền truy cập; giao diện hiển thị lỗi tương ứng. Với sai email/mật khẩu hoặc tài khoản khóa tạm, thông báo không xác nhận tài khoản có tồn tại hay không.
- Chuyển UC: khi chọn Quên mật khẩu, UC01 kết thúc tại điểm bàn giao và người dùng tiếp tục UC04.

**Tác nhân chính:** Người dùng chưa xác thực.

**Tác nhân phụ:** Không có tác nhân ngoài được xác nhận trong luồng đăng nhập này.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập màn hình đăng nhập. | |
| 2 | | Hiển thị trường Email, Mật khẩu, nút Đăng nhập và liên kết Quên mật khẩu. |
| 3 | Nhập email và mật khẩu. | |
| 4 | Chọn Đăng nhập. | |
| 5 | | Kiểm tra hai trường bắt buộc trước khi gửi yêu cầu. |
| 6 | | Áp dụng giới hạn API hiện hành: tối đa 5 yêu cầu đăng nhập trong 60 giây. |
| 7 | | Tìm thông tin xác thực theo email và kiểm tra mật khẩu. |
| 8 | | Kiểm tra trạng thái khóa tạm thời và trạng thái hoạt động của tài khoản. |
| 9 | | Khi thông tin đúng và tài khoản hoạt động, cấp thông tin truy cập cần thiết. |
| 10 | | Trả kết quả thành công và điều hướng đến danh sách dự án hoặc đích ban đầu nếu có. |
| 11 | | Kết thúc UC với hậu điều kiện thành công. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1.1 | Chọn liên kết Quên mật khẩu. | |
| 2.1.2 | | Mở màn hình khôi phục mật khẩu và bàn giao sang UC04; UC01 kết thúc tại đây. |
| 7.1 | | Nếu email không tồn tại hoặc mật khẩu sai, hiển thị thông báo chung “Thông tin đăng nhập không chính xác”. Chờ người dùng chọn thử lại hoặc dừng. |
| 5.2/7.1.1 | Chọn sửa và thử lại tại bước 3, hoặc dừng thao tác đăng nhập. | Nếu người dùng dừng, kết thúc UC với hậu điều kiện thất bại, không cấp quyền truy cập. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.1 | | Nếu email hoặc mật khẩu để trống, trình duyệt không gửi biểu mẫu và yêu cầu điền trường bắt buộc; quay lại bước 3. |
| 6.1 | | Nếu vượt giới hạn 5 yêu cầu trong 60 giây, từ chối yêu cầu đăng nhập, hiển thị lỗi giới hạn tần suất và kết thúc UC với hậu điều kiện thất bại. |
| 8.1 | | Nếu tài khoản đang bị khóa tạm do đăng nhập sai nhiều lần, từ chối đăng nhập với phản hồi không tiết lộ trạng thái xác thực; kết thúc thất bại. |
| 8.2 | | Nếu tài khoản không hoạt động, từ chối đăng nhập và hiển thị lỗi tài khoản không hoạt động; kết thúc thất bại. |
| 7.2 | | Nếu kho dữ liệu hoặc xử lý xác thực gặp lỗi, không cấp quyền truy cập; trả lỗi cho giao diện và kết thúc thất bại. Nội dung thông báo cụ thể chưa được mã nguồn xác định ở mức Use Case. |

**Giả định / Câu hỏi cần làm rõ**
- Mã nguồn dịch vụ đăng nhập nhận email hoặc slug, trong khi giao diện tại commit được đối chiếu chỉ hiển thị Email. UC này theo giao diện đang có; cần xác nhận nếu sản phẩm muốn công bố đăng nhập bằng slug.
- Mã nguồn xác nhận giới hạn 5 yêu cầu/60 giây, nhưng chưa xác minh tại đây cấu hình triển khai có thể ghi đè giá trị hay không.
- Nhánh lỗi hạ tầng là kết quả an toàn ở mức nghiệp vụ; thông điệp cụ thể hiển thị cho người dùng cần được xác nhận từ cấu hình vận hành.
- Yêu cầu khuôn sequence muốn mỗi ô nhập liệu phát sinh lời gọi API, nhưng UI hiện tại chỉ cập nhật trạng thái trường ở client và gửi API sau nút Đăng nhập. Bảng giữ đúng hành vi mã nguồn, không tạo request cho từng lần nhập.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

Sơ đồ chỉ giữ các lựa chọn và kết quả người dùng cần hiểu. Chi tiết kiểm tra ở API được gom ở một Action; không đưa lớp kỹ thuật vào Activity.

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu khi người dùng mở trang đăng nhập |
| A1 | 1 | Action | Người dùng | [1] Mở trang đăng nhập |
| A2 | 2 | Action | Hệ thống | [2] Hiển thị biểu mẫu đăng nhập |
| D1 | 2.1 | Decision | Người dùng | [2.1] Chọn đăng nhập hay khôi phục mật khẩu? |
| A3 | 2.1.2 | Action | Hệ thống | [2.1.2] Mở UC04 khôi phục mật khẩu |
| F1 | 2.1.2 | Final | Hệ thống | Kết thúc UC01, chuyển sang UC04 |
| A4 | 3-4 | Action | Người dùng | [3-4] Nhập email, mật khẩu và gửi yêu cầu |
| D2 | 5 | Decision | Hệ thống | [5] Đã nhập đủ email và mật khẩu? |
| A5 | 5.1 | Action | Hệ thống | [5.1] Báo thiếu thông tin bắt buộc |
| A6 | 6-8 | Action | Hệ thống | [6-8] Kiểm tra giới hạn, thông tin đăng nhập và trạng thái tài khoản |
| D3 | 6-8 | Decision | Hệ thống | [6-8] Kết quả xác thực? |
| A7 | 6.1/7.1/7.2/8.1/8.2 | Action | Hệ thống | [6.1/7.1/7.2/8.1/8.2] Báo đăng nhập thất bại phù hợp |
| D4 | 7.1.1 | Decision | Người dùng | [7.1.1] Thử lại hay dừng? |
| A8 | 9-10 | Action | Hệ thống | [9-10] Cấp thông tin truy cập và điều hướng |
| F2 | 10 | Final | Hệ thống | Kết thúc thành công, người dùng đã đăng nhập |
| F3 | 7.1.1 | Final | Người dùng | Kết thúc thất bại, người dùng chưa đăng nhập |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu UC |
| A1 | A2 | Trang được mở |
| A2 | D1 | Biểu mẫu đã hiển thị |
| D1 | A3 | [Chọn khôi phục mật khẩu] |
| A3 | F1 | [Bàn giao UC04] |
| D1 | A4 | [Chọn đăng nhập] |
| A4 | D2 | Yêu cầu đã gửi |
| D2 | A5 | [Thiếu email hoặc mật khẩu] |
| A5 | A4 | [Người dùng nhập lại] |
| D2 | A6 | [Đủ hai trường] |
| A6 | D3 | Đã kiểm tra yêu cầu |
| D3 | A8 | [Trong giới hạn, thông tin đúng, tài khoản hoạt động] |
| D3 | A7 | [Sai thông tin, bị giới hạn, bị khóa, không hoạt động hoặc lỗi xác thực] |
| A7 | D4 | Thông báo lỗi đã hiển thị |
| D4 | A4 | [Thử lại] |
| D4 | F3 | [Dừng] |
| A8 | F2 | Điều hướng hoàn tất |

### 3c. Số liệu

Action = 8, Decision = 4, cạnh = 17. Đây là sơ đồ quy trình nghiệp vụ, không nhằm phản ánh từng kiểm tra nội bộ của phần mềm.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

### 4a. Lifeline trái sang phải

Người dùng → Giao diện đăng nhập → API xác thực → Cơ sở dữ liệu tài khoản. Không có hệ thống ngoài trong UC01. Mỗi lifeline đại diện một vai trò đủ để giải thích tương tác, không phản ánh sơ đồ lớp của toàn bộ mã nguồn.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện đăng nhập | [1] moTrangDangNhap() | đồng bộ | chính |
| 2 | 2 | Giao diện đăng nhập | Người dùng | [2] hienThiBieuMau() | trả về | chính |
| 3 | 2.1 | Người dùng | Giao diện đăng nhập | [2.1] chonKhoiPhucMatKhau() | đồng bộ | alt [Khôi phục mật khẩu] |
| 4 | 2.1.2 | Giao diện đăng nhập | Người dùng | [2.1.2] moUC04() | trả về | alt [Khôi phục mật khẩu] |
| 5 | 3-4 | Người dùng | Giao diện đăng nhập | [3-4] guiThongTinDangNhap(email, matKhau) | đồng bộ | alt [Đăng nhập], loop mỗi lần gửi |
| 6 | 5.1 | Giao diện đăng nhập | Người dùng | [5.1] thongBaoThieuTruongBatBuoc() | trả về | alt [Thiếu trường] |
| 7 | 6 | Giao diện đăng nhập | API xác thực | [6] dangNhap(email, matKhau) | đồng bộ | alt [Đủ trường] |
| 8 | 7-8 | API xác thực | Cơ sở dữ liệu tài khoản | [7-8] timTaiKhoanVaTrangThai(email) | đồng bộ | alt [Trong giới hạn] |
| 9 | 7-8 | Cơ sở dữ liệu tài khoản | API xác thực | [7-8] traTaiKhoanHoacKhongTimThay() | trả về | alt [Trong giới hạn] |
| 10 | 9 | API xác thực | Giao diện đăng nhập | [9] traKetQuaDangNhap() | trả về | alt [Xác thực thành công] |
| 11 | 10 | Giao diện đăng nhập | Người dùng | [10] dieuHuongSauDangNhap() | trả về | alt [Xác thực thành công] |
| 12 | 6.1/7.1/7.2/8.1/8.2 | API xác thực | Giao diện đăng nhập | [6.1/7.1/7.2/8.1/8.2] traLoiDangNhapThatBai(maLoi) | trả về | alt [Xác thực thất bại] |
| 13 | 6.1/7.1/7.2/8.1/8.2 | Giao diện đăng nhập | Người dùng | [6.1/7.1/7.2/8.1/8.2] hienThiThongBaoLoi() | trả về | alt [Xác thực thất bại] |

### 4c. Số liệu

Lifeline = 4, message = 13, fragment = 4: alt chọn khôi phục hoặc đăng nhập, loop gửi lại, alt thiếu trường và alt kết quả xác thực. Mỗi request tới API hoặc CSDL có message trả về tương ứng; kết quả thành công và thất bại có hai operand riêng.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC01 - Đăng nhập của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Dùng swimlane Người dùng và Hệ thống, nhãn Tiếng Việt. Trình bày thoáng, ít nút, giống sơ đồ quy trình khóa luận. Không tạo tiêu đề thừa hoặc đưa lớp kỹ thuật vào sơ đồ.

Mô tả: Người dùng đăng nhập Veriq bằng email và mật khẩu; có thể chuyển sang UC04 để khôi phục mật khẩu.
Tiền điều kiện: Người dùng mở được trang đăng nhập. Tài khoản đúng và hoạt động là điều kiện thành công, không phải tiền điều kiện bắt buộc.
Hậu điều kiện: Thành công thì cấp thông tin truy cập và điều hướng vào hệ thống. Thất bại thì không cấp quyền. Chọn khôi phục thì bàn giao sang UC04.
Tác nhân: Người dùng chưa xác thực. Tác nhân phụ: Không có.
Luồng chính: (1) mở trang đăng nhập; (2) hệ thống hiển thị biểu mẫu; (3) người dùng nhập email/mật khẩu; (4) gửi đăng nhập; (5) kiểm tra trường bắt buộc; (6) kiểm tra giới hạn yêu cầu; (7) xác thực thông tin; (8) kiểm tra trạng thái tài khoản; (9) cấp thông tin truy cập; (10) điều hướng sau đăng nhập.
Nhánh: từ bước 2, người dùng chọn khôi phục thì mở UC04 và kết thúc UC01. Thiếu thông tin thì báo lỗi và quay lại nhập. Sai thông tin, bị giới hạn, bị khóa, tài khoản không hoạt động hoặc lỗi xác thực thì báo thất bại; người dùng có thể thử lại hoặc dừng.

Dùng đúng các node sau:
I Initial: bắt đầu khi người dùng mở trang đăng nhập.
A1 Action, Người dùng: [1] Mở trang đăng nhập.
A2 Action, Hệ thống: [2] Hiển thị biểu mẫu đăng nhập.
D1 Decision, Người dùng: [2.1] Chọn đăng nhập hay khôi phục mật khẩu?
A3 Action, Hệ thống: [2.1.2] Mở UC04 khôi phục mật khẩu.
F1 Final: kết thúc UC01, chuyển sang UC04.
A4 Action, Người dùng: [3-4] Nhập email, mật khẩu và gửi yêu cầu.
D2 Decision, Hệ thống: [5] Đã nhập đủ email và mật khẩu?
A5 Action, Hệ thống: [5.1] Báo thiếu thông tin bắt buộc.
A6 Action, Hệ thống: [6-8] Kiểm tra giới hạn, thông tin đăng nhập và trạng thái tài khoản.
D3 Decision, Hệ thống: [6-8] Kết quả xác thực?
A7 Action, Hệ thống: [6.1/7.1/7.2/8.1/8.2] Báo đăng nhập thất bại phù hợp.
D4 Decision, Người dùng: [7.1.1] Thử lại hay dừng?
A8 Action, Hệ thống: [9-10] Cấp thông tin truy cập và điều hướng.
F2 Final: kết thúc thành công, người dùng đã đăng nhập.
F3 Final: kết thúc thất bại, người dùng chưa đăng nhập.

Nối đúng cạnh và guard:
I->A1; A1->A2; A2->D1.
D1->A3 [Chọn khôi phục mật khẩu]; A3->F1.
D1->A4 [Chọn đăng nhập]; A4->D2.
D2->A5 [Thiếu trường]; A5->A4 [Nhập lại].
D2->A6 [Đủ trường]; A6->D3.
D3->A8 [Trong giới hạn, thông tin đúng, tài khoản hoạt động]; A8->F2.
D3->A7 [Sai thông tin, bị giới hạn, bị khóa, không hoạt động hoặc lỗi xác thực].
A7->D4; D4->A4 [Thử lại]; D4->F3 [Dừng].

Không thêm nghiệp vụ. Mọi cạnh rời Decision phải có guard. Giữ hai kết quả cuối riêng cho thành công và thất bại, cộng điểm kết thúc bàn giao UC04. Kiểm tra số node: 8 Action, 4 Decision, 17 cạnh; báo kết quả đối chiếu sau sơ đồ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC01 - Đăng nhập của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Dùng tiếng Việt, bố cục thoáng và ít lifeline như sơ đồ khóa luận. Dùng activation bar, return và alt/loop có guard. Không thêm Repository, hệ thống ngoài hay quản lý phiên.

ĐẶC TẢ
Mô tả: Người dùng xác thực bằng email và mật khẩu để truy cập Veriq; liên kết Quên mật khẩu chuyển sang UC04.
Tiền điều kiện: Người dùng truy cập được trang đăng nhập. Tài khoản hoạt động là điều kiện để thành công, không phải tiền điều kiện bắt buộc.
Hậu điều kiện: Thành công thì cấp thông tin truy cập và điều hướng vào hệ thống. Thất bại thì không cấp quyền. Chọn khôi phục thì kết thúc UC01 và mở UC04.
Tác nhân chính: Người dùng chưa xác thực. Tác nhân phụ: Không có.
Luồng chính: mở trang, hiển thị biểu mẫu, gửi email/mật khẩu; giao diện kiểm tra trường; API áp dụng giới hạn và xác thực tài khoản; trả kết quả.
Nhánh/ngoại lệ: Quên mật khẩu thì mở UC04. Thiếu trường thì giao diện báo lỗi. Sai thông tin, giới hạn yêu cầu, tài khoản khóa/không hoạt động hoặc lỗi xác thực thì trả thất bại, không cấp quyền; người dùng có thể thử lại.

LIFELINE trái sang phải: Người dùng | Giao diện đăng nhập | API xác thực | Cơ sở dữ liệu tài khoản.

MESSAGE
1. Người dùng -> Giao diện đăng nhập: [1] moTrangDangNhap()
2. Giao diện đăng nhập --> Người dùng: [2] hienThiBieuMau()
3. Trong alt [Khôi phục mật khẩu], Người dùng -> Giao diện đăng nhập: [2.1] chonKhoiPhucMatKhau()
4. Trong cùng nhánh, Giao diện đăng nhập --> Người dùng: [2.1.2] moUC04()
5. Trong operand alt [Đăng nhập], lặp cho mỗi lần gửi thông tin:
   5.1 Người dùng -> Giao diện đăng nhập: [3-4] guiThongTinDangNhap(email, matKhau)
   5.2 Trong alt [Thiếu trường], Giao diện đăng nhập --> Người dùng: [5.1] thongBaoThieuTruongBatBuoc()
   5.3 Trong alt [Đủ trường], Giao diện đăng nhập -> API xác thực: [6] dangNhap(email, matKhau)
   5.4 API xác thực -> Cơ sở dữ liệu tài khoản: [7-8] timTaiKhoanVaTrangThai(email)
   5.5 Cơ sở dữ liệu tài khoản --> API xác thực: [7-8] traTaiKhoanHoacKhongTimThay()
   5.6 Trong alt [Xác thực thành công], API xác thực --> Giao diện đăng nhập: [9] traKetQuaDangNhap()
   5.7 Trong cùng nhánh, Giao diện đăng nhập --> Người dùng: [10] dieuHuongSauDangNhap()
   5.8 Trong alt [Xác thực thất bại], API xác thực --> Giao diện đăng nhập: [6.1/7.1/7.2/8.1/8.2] traLoiDangNhapThatBai(maLoi)
   5.9 Trong cùng nhánh, Giao diện đăng nhập --> Người dùng: [6.1/7.1/7.2/8.1/8.2] hienThiThongBaoLoi()

YÊU CẦU
Giữ message theo thứ tự. Mọi lời gọi đồng bộ có return trong cùng nhánh: giao diện trả về người dùng, CSDL trả về API, API trả về giao diện. Không làm lộ việc email có tồn tại hay không trong thông báo sai thông tin. Không đưa chi tiết kỹ thuật không có trong đặc tả. Đối chiếu lifeline=4, message=13, fragment=4; báo kết quả sau sơ đồ.
```

## TỰ KIỂM TRA UC01

- [x] Đặc tả nghiệp vụ được giữ đầy đủ; sơ đồ đã giảm chi tiết kỹ thuật nội bộ.
- [x] Activity: 8 Action, 4 Decision, 17 cạnh; mọi Decision có guard.
- [x] Sequence: 4 lifeline, 13 message, 4 fragment; nhánh lỗi và thành công có phản hồi.
- [x] Hai prompt chép đầy đủ đặc tả nghiệp vụ và bảng sơ đồ; không dùng “như trên”.
- Trạng thái UC01: hoàn tất ở mức sơ đồ khóa luận.


## Bảng theo dõi sau UC01

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC02 - Đăng xuất

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1 | MƠ HỒ | Bản cũ dẫn người dùng vào trang tài khoản, nơi còn có khu vực liên quan đến các phiên khác. Phạm vi được yêu cầu không gồm quản lý phiên. | Bắt đầu từ lệnh Đăng xuất trong menu tài khoản dùng chung (đã sửa). |
| 3–4 | THIẾU | “Thực hiện đăng xuất” gộp xác thực, thu hồi lần truy cập hiện tại, xóa cookie và dọn trạng thái UI. | Làm rõ ba kết quả nghiệp vụ: xác thực yêu cầu, thu hồi phía máy chủ và dọn trạng thái giao diện; sơ đồ không tách từng lớp nội bộ (đã sửa). |
| 4 | THIẾU | Chưa nói giao diện xử lý thế nào nếu API lỗi. Hook hiện tại dọn trạng thái cục bộ trong `finally`; vì thế không thể khẳng định máy chủ luôn thu hồi thành công. | Thêm ngoại lệ và hậu điều kiện thất bại có giới hạn (đã sửa). |
| 2–3 | THIẾU | Chưa xử lý credential không hợp lệ hoặc không còn token ở giao diện. | Bổ sung nhánh không gọi API khi token vắng mặt và nhánh API từ chối credential (đã sửa). |
| Không áp dụng | MƠ HỒ | CRUD, tìm kiếm/lọc và quyền chức năng không áp dụng; giao diện không có hộp thoại xác nhận để hủy. | Không thêm những hành vi này vào UC. |

Đã kiểm: **3 điểm rẽ, 3 nhánh, 3 tình huống lỗi** (token không có, credential bị từ chối, API/thu hồi thất bại); đã rà tiền/hậu điều kiện và actor. CRUD không áp dụng. Không có hệ thống ngoài.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người dùng đã xác thực chọn Đăng xuất để kết thúc lần truy cập hiện tại và trở về trang đăng nhập. UC không bao gồm xem hoặc quản lý các phiên khác.

**Tiền điều kiện:** Người dùng đang ở giao diện đã xác thực. Nếu token cục bộ không còn, giao diện vẫn có thể dọn trạng thái cục bộ mà không gọi API.

**Hậu điều kiện:**
- Thành công phía máy chủ: lần truy cập hiện tại được thu hồi, cookie làm mới bị xóa, trạng thái cục bộ được dọn và UI điều hướng về `/dang-nhap`.
- API lỗi hoặc token vắng mặt: UI dọn trạng thái cục bộ và điều hướng về trang đăng nhập; việc thu hồi phía máy chủ chưa được xác nhận.

**Tác nhân chính:** Người dùng đã đăng nhập.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở menu tài khoản và chọn “Đăng xuất”. | |
| 2 | | Giao diện kiểm tra token cục bộ và gửi yêu cầu `POST /xac-thuc/dang-xuat` khi token hiện diện. |
| 3 | | API xác thực yêu cầu và chuyển danh tính hiện tại cho service. |
| 4 | | Service yêu cầu repository thu hồi lần truy cập hiện tại. |
| 5 | | Repository cập nhật trạng thái thu hồi; API xóa cookie làm mới và trả kết quả. |
| 6 | | Giao diện dọn trạng thái đăng nhập cục bộ và điều hướng đến `/dang-nhap`. |
| 7 | | Kết thúc UC với hậu điều kiện thành công. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Nếu token cục bộ vắng mặt, hàm gọi API kết thúc mà không gửi request; giao diện vẫn dọn trạng thái cục bộ và điều hướng đến trang đăng nhập. Kết thúc với hậu điều kiện thất bại giới hạn. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | | Nếu API từ chối credential, giao diện vẫn chạy `finally`, dọn trạng thái cục bộ và điều hướng về trang đăng nhập. |
| 4.1 | | Nếu mạng hoặc thao tác thu hồi phía máy chủ lỗi, giao diện vẫn dọn trạng thái cục bộ và điều hướng về trang đăng nhập; trạng thái thu hồi phía máy chủ chưa được xác nhận. |

**Giả định / Câu hỏi cần làm rõ**
- “Kết thúc phiên truy cập hiện tại” chỉ mô tả hiệu ứng của nút Đăng xuất. Không tạo UC xem danh sách phiên, đăng xuất thiết bị khác hay quản lý thiết bị.
- Token vắng mặt được suy ra từ `logoutAPI`, hàm này bỏ qua request khi không lấy được token; `logoutState` vẫn chạy phần `finally`.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức nghiệp vụ phù hợp khóa luận)

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Hệ thống | Bắt đầu; tiền điều kiện: người dùng đang ở giao diện đã xác thực |
| A1 | 1 | Action | Người dùng | [1] Chọn Đăng xuất |
| A2 | 2 | Action | Hệ thống | [2] Gửi yêu cầu đăng xuất nếu có token |
| D1 | 2 | Decision | Hệ thống | [2] Token cục bộ có sẵn? |
| A3 | 3-5 | Action | Hệ thống | [3-5] Xác thực yêu cầu và thu hồi lần truy cập hiện tại |
| D2 | 3-5 | Decision | Hệ thống | [3-5] Máy chủ xác thực và thu hồi thành công? |
| A4 | 2.1 | Action | Hệ thống | [2.1] Bỏ qua API vì thiếu token |
| A5 | 3.1/4.1 | Action | Hệ thống | [3.1/4.1] Ghi nhận credential không hợp lệ hoặc lỗi thu hồi |
| M1 | 2.1/3.1/4.1 | Merge | Hệ thống | Nhập các kết quả cần dọn trạng thái giao diện |
| A6 | 6 | Action | Hệ thống | [6] Xóa trạng thái cục bộ và điều hướng đến đăng nhập |
| F1 | 7 | Final | Hệ thống | Đăng xuất và thu hồi phía máy chủ thành công |
| F2 | 2.1/3.1/4.1 | Final | Hệ thống | Giao diện đã thoát; thu hồi phía máy chủ không được xác nhận |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | D1 | Người dùng chọn Đăng xuất |
| D1 | A2 | [Token hiện diện] |
| D1 | A4 | [Token vắng mặt] |
| A2 | A3 | Yêu cầu được gửi |
| A3 | D2 | Máy chủ trả kết quả |
| D2 | A6 | [Credential hợp lệ và thu hồi thành công] |
| D2 | A5 | [Credential không hợp lệ hoặc xảy ra lỗi] |
| A4 | M1 | API được bỏ qua |
| A5 | M1 | Kết quả lỗi đã được nhận |
| M1 | A6 | Giao diện luôn dọn trạng thái cục bộ |
| A6 | F1 | [Máy chủ xác nhận thu hồi] |
| A6 | F2 | [Không có xác nhận thu hồi] |

### 3c. Số liệu

N = 7 ô nghiệp vụ có nội dung; M = 6 Action, D = 2 Decision, E = 13 cạnh. Đây là sơ đồ mức người dùng, không tách riêng thao tác nội bộ của từng lớp phần mềm.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức nghiệp vụ phù hợp khóa luận)

### 4a. Lifeline trái sang phải

Người dùng → Giao diện → API đăng xuất → Dịch vụ xác thực → Cơ sở dữ liệu. Không có hệ thống ngoài. Không tạo UC quản lý phiên; chỉ mô tả kết quả của thao tác đăng xuất lần truy cập hiện tại.

### 4b. Bảng message theo thời gian

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện | [1] chonDangXuat() | đồng bộ | chính |
| 2 | 1 | Giao diện | Người dùng | [1] hienThiKetQuaChon() | trả về | chính |
| 3 | 2 | Giao diện | Giao diện | [2] kiemTraTokenCucBo() | tự gọi | chính |
| 4 | 2 | Giao diện | Giao diện | [2] traKetQuaKiemTraToken() | trả về | chính |
| 5 | 2 | Giao diện | API đăng xuất | [2] guiYeuCauDangXuat(token) | đồng bộ | alt [Có token] |
| 6 | 3 | API đăng xuất | API đăng xuất | [3] xacThucCredential() | tự gọi | alt [Có token] |
| 7 | 3 | API đăng xuất | API đăng xuất | [3] traKetQuaXacThuc() | trả về | alt [Có token] |
| 8 | 3-4 | API đăng xuất | Dịch vụ xác thực | [3-4] yeuCauThuHoi(currentUser) | đồng bộ | alt [Credential hợp lệ] |
| 9 | 4-5 | Dịch vụ xác thực | Cơ sở dữ liệu | [4-5] thuHoiLanTruyCapHienTai() | đồng bộ | alt [Credential hợp lệ] |
| 10 | 4-5 | Cơ sở dữ liệu | Dịch vụ xác thực | [4-5] traKetQuaThuHoi() | trả về | alt [Credential hợp lệ] |
| 11 | 5 | Dịch vụ xác thực | API đăng xuất | [5] traKetQuaDangXuat() | trả về | alt [Thu hồi thành công/lỗi] |
| 12 | 5 | API đăng xuất | Giao diện | [5] traPhanHoiDangXuat() | trả về | alt [Có token] |
| 13 | 6 | Giao diện | Giao diện | [6] xoaTrangThaiDangNhapCucBo() | tự gọi | chính |
| 14 | 6 | Giao diện | Giao diện | [6] xacNhanDaDonTrangThai() | trả về | chính |
| 15 | 6 | Giao diện | Người dùng | [6] dieuHuongDenDangNhap() | trả về | chính |

### 4c. Số liệu

N = 7; M = 15 message; F = 2 fragment (alt token hiện diện/vắng mặt, alt thu hồi thành công/thất bại); L = 5 lifeline. Số message phản ánh các trao đổi cần đọc, không theo tỷ lệ nhân tạo.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC02 - Đăng xuất của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt.

ĐẶC TẢ ĐẦY ĐỦ:
## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người dùng đã xác thực chọn Đăng xuất để kết thúc lần truy cập hiện tại và trở về trang đăng nhập. UC không bao gồm xem hoặc quản lý các phiên khác.

**Tiền điều kiện:** Người dùng đang ở giao diện đã xác thực. Nếu token cục bộ không còn, giao diện vẫn có thể dọn trạng thái cục bộ mà không gọi API.

**Hậu điều kiện:**
- Thành công phía máy chủ: lần truy cập hiện tại được thu hồi, cookie làm mới bị xóa, trạng thái cục bộ được dọn và UI điều hướng về `/dang-nhap`.
- API lỗi hoặc token vắng mặt: UI dọn trạng thái cục bộ và điều hướng về trang đăng nhập; việc thu hồi phía máy chủ chưa được xác nhận.

**Tác nhân chính:** Người dùng đã đăng nhập.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở menu tài khoản và chọn “Đăng xuất”. | |
| 2 | | Giao diện kiểm tra token cục bộ và gửi yêu cầu `POST /xac-thuc/dang-xuat` khi token hiện diện. |
| 3 | | API xác thực yêu cầu và chuyển danh tính hiện tại cho service. |
| 4 | | Service yêu cầu repository thu hồi lần truy cập hiện tại. |
| 5 | | Repository cập nhật trạng thái thu hồi; API xóa cookie làm mới và trả kết quả. |
| 6 | | Giao diện dọn trạng thái đăng nhập cục bộ và điều hướng đến `/dang-nhap`. |
| 7 | | Kết thúc UC với hậu điều kiện thành công. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Nếu token cục bộ vắng mặt, hàm gọi API kết thúc mà không gửi request; giao diện vẫn dọn trạng thái cục bộ và điều hướng đến trang đăng nhập. Kết thúc với hậu điều kiện thất bại giới hạn. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | | Nếu API từ chối credential, giao diện vẫn chạy `finally`, dọn trạng thái cục bộ và điều hướng về trang đăng nhập. |
| 4.1 | | Nếu mạng hoặc thao tác thu hồi phía máy chủ lỗi, giao diện vẫn dọn trạng thái cục bộ và điều hướng về trang đăng nhập; trạng thái thu hồi phía máy chủ chưa được xác nhận. |

**Giả định / Câu hỏi cần làm rõ**
- “Kết thúc phiên truy cập hiện tại” chỉ mô tả hiệu ứng của nút Đăng xuất. Không tạo UC xem danh sách phiên, đăng xuất thiết bị khác hay quản lý thiết bị.
- Token vắng mặt được suy ra từ `logoutAPI`, hàm này bỏ qua request khi không lấy được token; `logoutState` vẫn chạy phần `finally`.

BẢNG NODE:
| ID | Loại | Swimlane | Nhãn |
|---|---|---|---|
| I | Initial | Hệ thống | Bắt đầu; tiền điều kiện: người dùng đang ở giao diện đã xác thực |
| A1 | Action | Người dùng | [1] Chọn Đăng xuất |
| A2 | Action | Hệ thống | [2] Gửi yêu cầu đăng xuất nếu có token |
| D1 | Decision | Hệ thống | [2] Token cục bộ có sẵn? |
| A3 | Action | Hệ thống | [3-5] Xác thực yêu cầu và thu hồi lần truy cập hiện tại |
| D2 | Decision | Hệ thống | [3-5] Máy chủ xác thực và thu hồi thành công? |
| A4 | Action | Hệ thống | [2.1] Bỏ qua API vì thiếu token |
| A5 | Action | Hệ thống | [3.1/4.1] Ghi nhận credential không hợp lệ hoặc lỗi thu hồi |
| M1 | Merge | Hệ thống | Nhập các kết quả cần dọn trạng thái giao diện |
| A6 | Action | Hệ thống | [6] Xóa trạng thái cục bộ và điều hướng đến đăng nhập |
| F1 | Final | Hệ thống | Đăng xuất và thu hồi phía máy chủ thành công |
| F2 | Final | Hệ thống | Giao diện đã thoát; thu hồi phía máy chủ không được xác nhận |

BẢNG CẠNH:
| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | D1 | Người dùng chọn Đăng xuất |
| D1 | A2 | [Token hiện diện] |
| D1 | A4 | [Token vắng mặt] |
| A2 | A3 | Yêu cầu được gửi |
| A3 | D2 | Máy chủ trả kết quả |
| D2 | A6 | [Credential hợp lệ và thu hồi thành công] |
| D2 | A5 | [Credential không hợp lệ hoặc xảy ra lỗi] |
| A4 | M1 | API được bỏ qua |
| A5 | M1 | Kết quả lỗi đã được nhận |
| M1 | A6 | Giao diện luôn dọn trạng thái cục bộ |
| A6 | F1 | [Máy chủ xác nhận thu hồi] |
| A6 | F2 | [Không có xác nhận thu hồi] |

YÊU CẦU: Vẽ chính xác các node/cạnh/guard/swimlane đã liệt kê; có Initial và hai Final. Không thêm chức năng quản lý phiên. Giữ nguyên mã bước. Đối chiếu số lượng: Action=6, Decision=2, cạnh=13.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC02 - Đăng xuất của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt.

ĐẶC TẢ ĐẦY ĐỦ:
## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người dùng đã xác thực chọn Đăng xuất để kết thúc lần truy cập hiện tại và trở về trang đăng nhập. UC không bao gồm xem hoặc quản lý các phiên khác.

**Tiền điều kiện:** Người dùng đang ở giao diện đã xác thực. Nếu token cục bộ không còn, giao diện vẫn có thể dọn trạng thái cục bộ mà không gọi API.

**Hậu điều kiện:**
- Thành công phía máy chủ: lần truy cập hiện tại được thu hồi, cookie làm mới bị xóa, trạng thái cục bộ được dọn và UI điều hướng về `/dang-nhap`.
- API lỗi hoặc token vắng mặt: UI dọn trạng thái cục bộ và điều hướng về trang đăng nhập; việc thu hồi phía máy chủ chưa được xác nhận.

**Tác nhân chính:** Người dùng đã đăng nhập.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở menu tài khoản và chọn “Đăng xuất”. | |
| 2 | | Giao diện kiểm tra token cục bộ và gửi yêu cầu `POST /xac-thuc/dang-xuat` khi token hiện diện. |
| 3 | | API xác thực yêu cầu và chuyển danh tính hiện tại cho service. |
| 4 | | Service yêu cầu repository thu hồi lần truy cập hiện tại. |
| 5 | | Repository cập nhật trạng thái thu hồi; API xóa cookie làm mới và trả kết quả. |
| 6 | | Giao diện dọn trạng thái đăng nhập cục bộ và điều hướng đến `/dang-nhap`. |
| 7 | | Kết thúc UC với hậu điều kiện thành công. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Nếu token cục bộ vắng mặt, hàm gọi API kết thúc mà không gửi request; giao diện vẫn dọn trạng thái cục bộ và điều hướng đến trang đăng nhập. Kết thúc với hậu điều kiện thất bại giới hạn. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | | Nếu API từ chối credential, giao diện vẫn chạy `finally`, dọn trạng thái cục bộ và điều hướng về trang đăng nhập. |
| 4.1 | | Nếu mạng hoặc thao tác thu hồi phía máy chủ lỗi, giao diện vẫn dọn trạng thái cục bộ và điều hướng về trang đăng nhập; trạng thái thu hồi phía máy chủ chưa được xác nhận. |

**Giả định / Câu hỏi cần làm rõ**
- “Kết thúc phiên truy cập hiện tại” chỉ mô tả hiệu ứng của nút Đăng xuất. Không tạo UC xem danh sách phiên, đăng xuất thiết bị khác hay quản lý thiết bị.
- Token vắng mặt được suy ra từ `logoutAPI`, hàm này bỏ qua request khi không lấy được token; `logoutState` vẫn chạy phần `finally`.

LIFELINE TỪ TRÁI SANG PHẢI: Người dùng, Giao diện, API đăng xuất, Dịch vụ xác thực, Cơ sở dữ liệu.

MESSAGE THEO THỨ TỰ:
1. Người dùng -> Giao diện: [1] chonDangXuat()
2. Giao diện --> Người dùng: [1] hienThiKetQuaChon()
3. Giao diện -> Giao diện: [2] kiemTraTokenCucBo()
4. Giao diện --> Giao diện: [2] traKetQuaKiemTraToken()
5. Giao diện -> API đăng xuất: [2] guiYeuCauDangXuat(token) [alt có token]
6. API đăng xuất -> API đăng xuất: [3] xacThucCredential() [alt có token]
7. API đăng xuất --> API đăng xuất: [3] traKetQuaXacThuc() [alt có token]
8. API đăng xuất -> Dịch vụ xác thực: [3-4] yeuCauThuHoi(currentUser) [alt credential hợp lệ]
9. Dịch vụ xác thực -> Cơ sở dữ liệu: [4-5] thuHoiLanTruyCapHienTai() [alt credential hợp lệ]
10. Cơ sở dữ liệu --> Dịch vụ xác thực: [4-5] traKetQuaThuHoi()
11. Dịch vụ xác thực --> API đăng xuất: [5] traKetQuaDangXuat() [alt thu hồi thành công/lỗi]
12. API đăng xuất --> Giao diện: [5] traPhanHoiDangXuat() [alt có token]
13. Giao diện -> Giao diện: [6] xoaTrangThaiDangNhapCucBo()
14. Giao diện --> Giao diện: [6] xacNhanDaDonTrangThai()
15. Giao diện --> Người dùng: [6] dieuHuongDenDangNhap()

YÊU CẦU: Có activation bar, return và alt guard. Trường hợp thiếu token phải thể hiện không gọi API nhưng vẫn dọn trạng thái cục bộ; lỗi credential hoặc thu hồi phải thể hiện giao diện đăng xuất cục bộ nhưng không xác nhận thu hồi máy chủ. Không thêm quản lý phiên. Đối chiếu L=5, M=15, F=2.
```

## TỰ KIỂM TRA UC02

- [x] Giữ đủ hành vi xác nhận được; sơ đồ chỉ mô tả thao tác đăng xuất hiện tại.
- [x] Activity: 6 Action, 2 Decision, 13 cạnh; các quyết định có guard và có hai kết thúc riêng.
- [x] Sequence: 5 lifeline, 15 message, 2 fragment; phân biệt kết quả máy chủ và dọn trạng thái giao diện.
- [x] Hai prompt tự đủ, gồm đặc tả và bảng sơ đồ; không dùng “tương tự UC trước”.

## Bảng theo dõi sau UC02

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |


# UC03 - Cập nhật thông tin cá nhân

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Mô tả/luồng | MÂU THUẪN | Tên UC nói cập nhật hồ sơ, nhưng mô tả gộp đổi mật khẩu vào cùng UC; hai biểu mẫu trong giao diện lại là hai thao tác độc lập. | Giữ nguyên tên UC của tài liệu gốc, nêu rõ hai nhánh độc lập và ghi sự bất tương thích tên-phạm vi cần được chủ văn bản xác nhận. |
| 2 | THIẾU | Đặc tả không nêu dữ liệu hiển thị hay tách trường chỉ đọc khỏi trường chỉnh sửa được. | Nêu tên hiển thị, email, vai trò, locale, timezone; mã giao diện chỉ cho sửa tên hiển thị, locale, timezone. |
| 5 | MƠ HỒ | Một ô gộp nhập và gửi dữ liệu, không nói rõ dữ liệu nào được nhập. | Tách hành động nhập và gửi trong các luồng hồ sơ/mật khẩu. |
| 6 | MƠ HỒ | “Kiểm tra thông tin” không nói rõ kiểm tra nào ở giao diện, API hay service. | Nêu kiểm tra locale/timezone tại UI; schema tại API; xác thực mật khẩu hiện tại và mật khẩu mới khác mật khẩu cũ tại service. |
| 7 | THIẾU | Chưa phân biệt cập nhật hồ sơ với cập nhật thông tin xác thực, cũng chưa nêu hậu quả thành công riêng. | Tách hai luồng; hồ sơ dùng PATCH `/xac-thuc/ca-nhan`; mật khẩu dùng POST `/xac-thuc/doi-mat-khau`. |
| 6.3 | THIẾU | Không có nhánh rõ cho trường bỏ trống, không hợp lệ, không có thay đổi, hoặc sai schema. | Bổ sung lỗi validation, theo mã nguồn `ProfileUpdate` từ chối field lạ; service từ chối payload không có trường cần cập nhật. |
| 3.2.3–3.2.5 | THIẾU | Mật khẩu hiện tại sai, mật khẩu mới sai giới hạn hoặc trùng mật khẩu cũ chưa có điểm quay lại. | Bổ sung nhánh lỗi quay lại nhập mật khẩu; căn cứ giới hạn 12–128 ký tự và kiểm tra mật khẩu mới khác hiện tại. |
| 6.1–7.1 | THIẾU | Thiếu hết phiên/không đủ quyền, tài khoản không tìm thấy, lỗi API/CSDL. | Nêu phản hồi xác thực 401/403, 404, 422 và lỗi hạ tầng; lỗi không hợp lệ quay lại biểu mẫu, lỗi khác kết thúc thất bại. |
| Hủy | MƠ HỒ | Mã UI không có nút hủy/xác nhận rời trang riêng. | Không bịa hộp thoại hủy. Ghi rõ người dùng có thể rời trang trước khi gửi, khi ấy trình duyệt không gửi cập nhật. |
| Tiền/hậu điều kiện | THIẾU | Hậu điều kiện gốc không mô tả thất bại; tiền điều kiện chưa nêu tài khoản xác thực còn tồn tại. | Nêu token hợp lệ, tài khoản hiện hành tồn tại; chia hậu điều kiện thành thành công hồ sơ, thành công mật khẩu, thất bại và rời trước khi gửi. |
| Tác nhân | Đã kiểm | API dùng tác nhân đã xác thực, không có bằng chứng yêu cầu vai trò BA/Tester/Admin cho hồ sơ cá nhân. | Tác nhân chính là Người dùng đã đăng nhập; không gán tác nhân nghiệp vụ phụ. |
| UC quản lý/CRUD | Không áp dụng | Đây không phải UC quản trị danh sách tài khoản. | Không thêm danh sách, tìm kiếm, lọc, thêm hoặc xóa tài khoản. |
| Phiên đăng nhập | Ngoài phạm vi | Cùng trang có mục xem/thu hồi phiên nhưng người dùng yêu cầu bỏ toàn bộ quản lý phiên. Đổi mật khẩu tự thu hồi phiên khác ở backend. | Không mô tả danh sách/thu hồi phiên như chức năng người dùng; ghi side effect backend ở hậu điều kiện để không che giấu hành vi. |

Đã kiểm: 4 điểm rẽ nghiệp vụ (chọn thao tác, validation hồ sơ, validation mật khẩu, phản hồi hệ thống), 7 trường hợp lỗi/hủy được tách riêng; đã rà thiếu bắt buộc, giá trị không hợp lệ, dữ liệu không tìm thấy, quyền/token, lỗi hệ thống/CSDL và hủy trước khi gửi. Không có tích hợp hệ thống ngoài. Việc người dùng rời trang được nêu như hành vi trình duyệt, không phải nút hủy có xác nhận.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Tại trang “Tài khoản và bảo mật”, người dùng có thể sửa tên hiển thị, locale, timezone hoặc đổi mật khẩu bằng mật khẩu hiện tại. Đây là hai nhánh độc lập trong một UC theo tài liệu đầu vào. Email và vai trò được hiển thị nhưng không sửa tại form này.

### Tiền điều kiện
- Người dùng đã đăng nhập, token còn hiệu lực và tài khoản hiện hành còn tồn tại.
- Người dùng chỉ thao tác trên hồ sơ của chính mình.
- Nhánh đổi mật khẩu yêu cầu người dùng cung cấp mật khẩu hiện tại.

### Hậu điều kiện
- Thành công nhánh hồ sơ: các trường được gửi hợp lệ được lưu, hồ sơ được tải lại và UI báo “Đã cập nhật thông tin cá nhân”.
- Thành công nhánh mật khẩu: hash và thời điểm đổi mật khẩu được lưu; backend thu hồi phiên khác như side effect, rồi UI báo “Đã đổi mật khẩu và đóng các phiên khác”. Danh sách hay thao tác quản lý phiên không thuộc UC này.
- Thất bại: UI hiển thị lỗi; nếu lỗi validation thì dữ liệu form còn để sửa. Không khẳng định rollback khi kết quả ghi CSDL không xác định.
- Rời trang trước khi gửi: không có yêu cầu cập nhật được gửi.

### Tác nhân chính
Người dùng đã đăng nhập.

### Tác nhân phụ
Không có tác nhân nghiệp vụ phụ. API, service và cơ sở dữ liệu là thành phần nội bộ.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang “Tài khoản và bảo mật”. |  |
| 2 |  | Đọc hồ sơ hiện hành qua API cá nhân; hiển thị tên hiển thị, email, vai trò, locale, timezone và form đổi mật khẩu. (đã sửa) |
| 3 | Chọn thao tác cập nhật hồ sơ hoặc đổi mật khẩu. (đã sửa) |  |
| 4 |  | Hiển thị form tương ứng; email và vai trò vẫn chỉ đọc. (đã sửa) |
| 5 | Nhập dữ liệu vào form được chọn. (đã sửa) |  |
| 6 | Gửi form tương ứng. (đã sửa) |  |
| 7 |  | Xác thực token, quyền truy cập tài khoản hiện hành và dữ liệu theo nhánh đã chọn. (đã sửa) |
| 8 |  | Nếu cập nhật thành công, trả kết quả; nhánh hồ sơ tải lại hồ sơ, nhánh mật khẩu xóa giá trị mật khẩu trên form. (đã sửa) |
| 9 |  | Hiển thị thông báo thành công và kết thúc UC. (đã sửa) |

### Luồng sự kiện thay thế

**3.1. Cập nhật hồ sơ cá nhân**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Sửa tên hiển thị, locale hoặc timezone; email và vai trò không chỉnh sửa được. (đã sửa) |  |
| 3.1.2 | Nhấn “Lưu thông tin”. |  |
| 3.1.3 |  | Kiểm tra locale nếu có và kiểm tra timezone; gửi PATCH `/xac-thuc/ca-nhan`. (đã sửa) |
| 3.1.4 |  | API kiểm tra schema (`full_name` 2–100, `locale` 2–20, `timezone` 2–100 ký tự; field lạ bị từ chối); service từ chối payload rỗng. (đã sửa) |
| 3.1.5 |  | Cập nhật hồ sơ và audit các trường đổi; trả dữ liệu cập nhật. (đã sửa) |
| 3.1.6 |  | Gọi lại API hồ sơ, hiển thị dữ liệu mới và thông báo thành công. (đã sửa) |
| 3.1.7 |  | Kết thúc UC thành công. (thêm mới) |

**3.2. Đổi mật khẩu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.1 | Nhập mật khẩu hiện tại và mật khẩu mới. |  |
| 3.2.2 | Nhấn “Đổi mật khẩu”. |  |
| 3.2.3 |  | Kiểm tra mật khẩu hiện tại dài 1–128 và mật khẩu mới dài 12–128 ký tự; gửi POST `/xac-thuc/doi-mat-khau`. (đã sửa) |
| 3.2.4 |  | Service xác minh mật khẩu hiện tại. (đã sửa) |
| 3.2.5 |  | Service từ chối mật khẩu mới trùng mật khẩu hiện tại. |
| 3.2.6 |  | Lưu hash và thời điểm đổi; backend thu hồi phiên khác như side effect. (đã sửa) |
| 3.2.7 |  | UI xóa giá trị hai ô mật khẩu và hiển thị thông báo đổi mật khẩu thành công. (đã sửa) |
| 3.2.8 |  | Kết thúc UC thành công. (thêm mới) |

### Luồng sự kiện ngoại lệ

- **7.1.** Token hết hạn hoặc người dùng không còn quyền truy cập: API từ chối với 401/403; UI báo lỗi xác thực và kết thúc UC thất bại.
- **7.2.** Hồ sơ/tài khoản không tìm thấy: API trả 404; UI báo không tìm thấy, kết thúc UC thất bại.
- **7.3.** Thiếu `full_name`, giá trị không đúng độ dài, locale/timezone không hợp lệ, payload rỗng hoặc có field ngoài schema: UI giữ form và thông báo lỗi; quay lại bước 3.1.1.
- **7.4.** Mật khẩu hiện tại sai: API từ chối (403); UI báo lỗi và quay lại bước 3.2.1.
- **7.5.** Mật khẩu mới quá ngắn/quá dài hoặc trùng mật khẩu hiện tại: API/service từ chối; UI báo lỗi và quay lại bước 3.2.1.
- **7.6.** Người dùng rời trang trước bước 6: trình duyệt không gửi form, kết thúc UC không thay đổi dữ liệu. Mã UI không thể hiện hộp thoại xác nhận hủy.
- **7.7.** Lỗi API/CSDL khi đọc hoặc ghi: UI báo lỗi yêu cầu và kết thúc thất bại. Trạng thái ghi không xác định không được mô tả như rollback chắc chắn.
- **7.8.** Không có trường hồ sơ cần cập nhật: service trả 422; UI báo không có dữ liệu cần cập nhật và quay lại bước 3.1.1.

### Giả định / Câu hỏi cần làm rõ
- Tiêu đề UC03 là “Cập nhật thông tin cá nhân”, song phần mô tả gốc đồng thời đưa đổi mật khẩu vào; giữ phạm vi gộp theo luồng nguồn thay vì tự đổi mã UC. Có thể tách đổi mật khẩu thành UC riêng nếu chủ tài liệu xác nhận.
- Schema cho locale/timezone đặt giới hạn độ dài nhưng kiểm tra danh sách giá trị được hỗ trợ hiện nằm ở giao diện. Không giả định API tự kiểm tra chuẩn locale/timezone.
- Trang có thêm các API xem/thu hồi phiên. Theo yêu cầu, chúng bị loại khỏi bộ UC; side effect thu hồi phiên khác khi đổi mật khẩu vẫn được ghi nhận ở mức hệ thống.

## PHẦN 3 - PHÂN RÃ ACTIVITY (chưa vẽ)

Mô hình ở mức nghiệp vụ cho khóa luận. Các bước nhập, xác nhận, lựa chọn và kết quả chính vẫn hiện diện; những kiểm tra nội bộ nhỏ được giữ trong một action phù hợp.

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---:|---|---|---|
| A0 |  | Initial | Hệ thống | Bắt đầu; điều kiện: người dùng đã đăng nhập |
| A1 | 1 | Action | Người dùng | [1] Mở trang tài khoản |
| A2 | 2 | Action | Hệ thống | [2] Hiển thị hồ sơ và biểu mẫu |
| D1 | 3 | Decision | Hệ thống | [3] Chọn thao tác |
| A3 | 3.1 | Action | Người dùng | [3.1] Sửa tên, locale hoặc timezone |
| A4 | 3.1 | Action | Người dùng | [3.1] Gửi cập nhật hồ sơ |
| D2 | 3.1 | Decision | Hệ thống | [3.1] Dữ liệu hồ sơ hợp lệ? |
| A5 | 3.1 | Action | Hệ thống | [3.1] Lưu hồ sơ |
| A6 | 3.1 | Action | Hệ thống | [3.1] Hiển thị hồ sơ mới và báo thành công |
| A7 | 3.2 | Action | Người dùng | [3.2] Nhập mật khẩu hiện tại và mật khẩu mới |
| A8 | 3.2 | Action | Người dùng | [3.2] Gửi yêu cầu đổi mật khẩu |
| D3 | 3.2 | Decision | Hệ thống | [3.2] Mật khẩu hợp lệ? |
| A9 | 3.2 | Action | Hệ thống | [3.2] Lưu mật khẩu mới |
| A10 | 3.2 | Action | Hệ thống | [3.2] Báo đổi mật khẩu thành công |
| A11 | 7.1–7.3 | Action | Hệ thống | [7.1–7.3] Báo lỗi xác thực hoặc dữ liệu hồ sơ |
| A12 | 7.4–7.5 | Action | Hệ thống | [7.4–7.5] Báo lỗi mật khẩu |
| A13 | 7.6 | Action | Người dùng | [7.6] Rời trang trước khi gửi |
| A14 | 7.7 | Action | Hệ thống | [7.7] Báo lỗi API hoặc dữ liệu |
| M1 |  | Merge | Hệ thống | Nhập các luồng thành công |
| F1 |  | Final | Hệ thống | Kết thúc thành công |
| F2 |  | Final | Hệ thống | Kết thúc thất bại |
| F3 |  | Final | Hệ thống | Kết thúc không gửi thay đổi |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| A0 | A1 | luôn |
| A1 | A2 | luôn |
| A2 | D1 | luôn |
| D1 | A3 | [cập nhật hồ sơ] |
| D1 | A7 | [đổi mật khẩu] |
| D1 | A13 | [rời trang] |
| A3 | A4 | luôn |
| A4 | D2 | luôn |
| D2 | A5 | [hợp lệ] |
| D2 | A11 | [không hợp lệ] |
| A5 | A6 | [lưu thành công] |
| A5 | A14 | [lỗi khi lưu] |
| A6 | M1 | luôn |
| A7 | A8 | luôn |
| A8 | D3 | luôn |
| D3 | A9 | [mật khẩu hiện tại đúng, mật khẩu mới đạt giới hạn và khác mật khẩu cũ] |
| D3 | A12 | [mật khẩu sai/không hợp lệ] |
| A9 | A10 | [cập nhật thành công] |
| A9 | A14 | [lỗi khi cập nhật] |
| A10 | M1 | luôn |
| A11 | A3 | [người dùng sửa lại] |
| A11 | F2 | [người dùng dừng] |
| A12 | A7 | [người dùng nhập lại] |
| A12 | F2 | [người dùng dừng] |
| A13 | F3 | luôn |
| A14 | F2 | luôn |
| M1 | F1 | luôn |

### 3c. Số liệu

N = 32 ô nội dung ở đặc tả; M = 14 Action khái quát; D = 3 Decision; E = 27 cạnh. Mô hình không tăng node chỉ để thỏa một tỷ lệ số học.

## PHẦN 4 - PHÂN RÃ SEQUENCE (chưa vẽ)

### 4a. Lifeline trái sang phải
Người dùng → Giao diện → Controller/API → Service → Database. Không có hệ thống ngoài. Các thao tác phiên không được mô hình hóa thành chức năng.

### 4b. Bảng message theo thời gian

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện | [1] moTrangTaiKhoan() | đồng bộ | chính |
| 2 | 2 | Giao diện | Controller/API | [2] getHoSoCaNhan() | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] layHoSoNguoiDung(userId) | đồng bộ | chính |
| 4 | 2 | Service | Database | [2] docHoSo(userId) | đồng bộ | chính |
| 5 | 2 | Database | Service | [2] traHoSo() | trả về | chính |
| 6 | 2 | Service | Controller/API | [2] traDuLieuHoSo() | trả về | chính |
| 7 | 2 | Controller/API | Giao diện | [2] traHoSoVaBieuMau() | trả về | chính |
| 8 | 2 | Giao diện | Người dùng | [2] hienThiHoSoVaForm() | trả về | chính |
| 9 | 3.1 | Người dùng | Giao diện | [3.1] suaVaGuiHoSo(thongTin) | đồng bộ | alt [cập nhật hồ sơ] |
| 10 | 3.1 | Giao diện | Controller/API | [3.1] patchHoSo(thongTin) | đồng bộ | alt [cập nhật hồ sơ] |
| 11 | 3.1 | Controller/API | Service | [3.1] kiemTraQuyenVaCapNhatHoSo() | đồng bộ | alt [dữ liệu hợp lệ] |
| 12 | 3.1 | Service | Database | [3.1] luuHoSo(userId, thongTin) | đồng bộ | alt [dữ liệu hợp lệ] |
| 13 | 3.1 | Database | Service | [3.1] traKetQuaLuuHoSo() | trả về | alt [dữ liệu hợp lệ] |
| 14 | 3.1 | Service | Controller/API | [3.1] traKetQuaHoSo() | trả về | alt [thành công/lỗi] |
| 15 | 3.1 | Controller/API | Giao diện | [3.1] traHoSoMoiHoacLoi() | trả về | alt [thành công/lỗi] |
| 16 | 3.1 | Giao diện | Người dùng | [3.1] hienThiHoSoMoiHoacLoi() | trả về | alt [thành công/lỗi] |
| 17 | 3.2 | Người dùng | Giao diện | [3.2] nhapVaGuiMatKhau(current, new) | đồng bộ | alt [đổi mật khẩu] |
| 18 | 3.2 | Giao diện | Controller/API | [3.2] postDoiMatKhau(current, new) | đồng bộ | alt [đổi mật khẩu] |
| 19 | 3.2 | Controller/API | Service | [3.2] xacThucVaCapNhatMatKhau() | đồng bộ | alt [dữ liệu hợp lệ] |
| 20 | 3.2 | Service | Database | [3.2] capNhatCredential(userId, hash) | đồng bộ | alt [dữ liệu hợp lệ] |
| 21 | 3.2 | Database | Service | [3.2] traKetQuaDoiMatKhau() | trả về | alt [dữ liệu hợp lệ] |
| 22 | 3.2 | Service | Controller/API | [3.2] traKetQuaDoiMatKhau() | trả về | alt [thành công/lỗi] |
| 23 | 3.2 | Controller/API | Giao diện | [3.2] traKetQua() | trả về | alt [thành công/lỗi] |
| 24 | 3.2 | Giao diện | Người dùng | [3.2] xoaTruongMatKhauVaThongBao() | trả về | alt [thành công/lỗi] |
| 25 | 7.6 | Người dùng | Giao diện | [7.6] roiTrangTruocKhiGui() | đồng bộ | opt [hủy trước khi gửi] |
| 26 | 7.6 | Giao diện | Người dùng | [7.6] khongGuiCapNhat() | trả về | opt [hủy trước khi gửi] |

### 4c. Số liệu

N = 32 ô nội dung đặc tả; M = 26 message; F = 4 fragment (alt chọn nhánh, alt hồ sơ, alt mật khẩu, alt lỗi/hủy); L = 5.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```
Vẽ UML ACTIVITY DIAGRAM cho UC03 - Cập nhật thông tin cá nhân của hệ thống Veriq, định dạng PlantUML, nhãn Tiếng Việt. Sơ đồ dành cho khóa luận, thể hiện đúng các thao tác và quyết định nghiệp vụ, tránh chi tiết triển khai nội bộ.
ĐẶC TẢ ĐÃ CHỐT, chép đầy đủ:
## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Tại trang “Tài khoản và bảo mật”, người dùng có thể sửa tên hiển thị, locale, timezone hoặc đổi mật khẩu bằng mật khẩu hiện tại. Đây là hai nhánh độc lập trong một UC theo tài liệu đầu vào. Email và vai trò được hiển thị nhưng không sửa tại form này.

### Tiền điều kiện
- Người dùng đã đăng nhập, token còn hiệu lực và tài khoản hiện hành còn tồn tại.
- Người dùng chỉ thao tác trên hồ sơ của chính mình.
- Nhánh đổi mật khẩu yêu cầu người dùng cung cấp mật khẩu hiện tại.

### Hậu điều kiện
- Thành công nhánh hồ sơ: các trường được gửi hợp lệ được lưu, hồ sơ được tải lại và UI báo “Đã cập nhật thông tin cá nhân”.
- Thành công nhánh mật khẩu: hash và thời điểm đổi mật khẩu được lưu; backend thu hồi phiên khác như side effect, rồi UI báo “Đã đổi mật khẩu và đóng các phiên khác”. Danh sách hay thao tác quản lý phiên không thuộc UC này.
- Thất bại: UI hiển thị lỗi; nếu lỗi validation thì dữ liệu form còn để sửa. Không khẳng định rollback khi kết quả ghi CSDL không xác định.
- Rời trang trước khi gửi: không có yêu cầu cập nhật được gửi.

### Tác nhân chính
Người dùng đã đăng nhập.

### Tác nhân phụ
Không có tác nhân nghiệp vụ phụ. API, service và cơ sở dữ liệu là thành phần nội bộ.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang “Tài khoản và bảo mật”. |  |
| 2 |  | Đọc hồ sơ hiện hành qua API cá nhân; hiển thị tên hiển thị, email, vai trò, locale, timezone và form đổi mật khẩu. (đã sửa) |
| 3 | Chọn thao tác cập nhật hồ sơ hoặc đổi mật khẩu. (đã sửa) |  |
| 4 |  | Hiển thị form tương ứng; email và vai trò vẫn chỉ đọc. (đã sửa) |
| 5 | Nhập dữ liệu vào form được chọn. (đã sửa) |  |
| 6 | Gửi form tương ứng. (đã sửa) |  |
| 7 |  | Xác thực token, quyền truy cập tài khoản hiện hành và dữ liệu theo nhánh đã chọn. (đã sửa) |
| 8 |  | Nếu cập nhật thành công, trả kết quả; nhánh hồ sơ tải lại hồ sơ, nhánh mật khẩu xóa giá trị mật khẩu trên form. (đã sửa) |
| 9 |  | Hiển thị thông báo thành công và kết thúc UC. (đã sửa) |

### Luồng sự kiện thay thế

**3.1. Cập nhật hồ sơ cá nhân**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Sửa tên hiển thị, locale hoặc timezone; email và vai trò không chỉnh sửa được. (đã sửa) |  |
| 3.1.2 | Nhấn “Lưu thông tin”. |  |
| 3.1.3 |  | Kiểm tra locale nếu có và kiểm tra timezone; gửi PATCH `/xac-thuc/ca-nhan`. (đã sửa) |
| 3.1.4 |  | API kiểm tra schema (`full_name` 2–100, `locale` 2–20, `timezone` 2–100 ký tự; field lạ bị từ chối); service từ chối payload rỗng. (đã sửa) |
| 3.1.5 |  | Cập nhật hồ sơ và audit các trường đổi; trả dữ liệu cập nhật. (đã sửa) |
| 3.1.6 |  | Gọi lại API hồ sơ, hiển thị dữ liệu mới và thông báo thành công. (đã sửa) |
| 3.1.7 |  | Kết thúc UC thành công. (thêm mới) |

**3.2. Đổi mật khẩu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.1 | Nhập mật khẩu hiện tại và mật khẩu mới. |  |
| 3.2.2 | Nhấn “Đổi mật khẩu”. |  |
| 3.2.3 |  | Kiểm tra mật khẩu hiện tại dài 1–128 và mật khẩu mới dài 12–128 ký tự; gửi POST `/xac-thuc/doi-mat-khau`. (đã sửa) |
| 3.2.4 |  | Service xác minh mật khẩu hiện tại. (đã sửa) |
| 3.2.5 |  | Service từ chối mật khẩu mới trùng mật khẩu hiện tại. |
| 3.2.6 |  | Lưu hash và thời điểm đổi; backend thu hồi phiên khác như side effect. (đã sửa) |
| 3.2.7 |  | UI xóa giá trị hai ô mật khẩu và hiển thị thông báo đổi mật khẩu thành công. (đã sửa) |
| 3.2.8 |  | Kết thúc UC thành công. (thêm mới) |

### Luồng sự kiện ngoại lệ

- **7.1.** Token hết hạn hoặc người dùng không còn quyền truy cập: API từ chối với 401/403; UI báo lỗi xác thực và kết thúc UC thất bại.
- **7.2.** Hồ sơ/tài khoản không tìm thấy: API trả 404; UI báo không tìm thấy, kết thúc UC thất bại.
- **7.3.** Thiếu `full_name`, giá trị không đúng độ dài, locale/timezone không hợp lệ, payload rỗng hoặc có field ngoài schema: UI giữ form và thông báo lỗi; quay lại bước 3.1.1.
- **7.4.** Mật khẩu hiện tại sai: API từ chối (403); UI báo lỗi và quay lại bước 3.2.1.
- **7.5.** Mật khẩu mới quá ngắn/quá dài hoặc trùng mật khẩu hiện tại: API/service từ chối; UI báo lỗi và quay lại bước 3.2.1.
- **7.6.** Người dùng rời trang trước bước 6: trình duyệt không gửi form, kết thúc UC không thay đổi dữ liệu. Mã UI không thể hiện hộp thoại xác nhận hủy.
- **7.7.** Lỗi API/CSDL khi đọc hoặc ghi: UI báo lỗi yêu cầu và kết thúc thất bại. Trạng thái ghi không xác định không được mô tả như rollback chắc chắn.
- **7.8.** Không có trường hồ sơ cần cập nhật: service trả 422; UI báo không có dữ liệu cần cập nhật và quay lại bước 3.1.1.

### Giả định / Câu hỏi cần làm rõ
- Tiêu đề UC03 là “Cập nhật thông tin cá nhân”, song phần mô tả gốc đồng thời đưa đổi mật khẩu vào; giữ phạm vi gộp theo luồng nguồn thay vì tự đổi mã UC. Có thể tách đổi mật khẩu thành UC riêng nếu chủ tài liệu xác nhận.
- Schema cho locale/timezone đặt giới hạn độ dài nhưng kiểm tra danh sách giá trị được hỗ trợ hiện nằm ở giao diện. Không giả định API tự kiểm tra chuẩn locale/timezone.
- Trang có thêm các API xem/thu hồi phiên. Theo yêu cầu, chúng bị loại khỏi bộ UC; side effect thu hồi phiên khác khi đổi mật khẩu vẫn được ghi nhận ở mức hệ thống.

BẢNG NODE 3a:
| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---:|---|---|---|
| A0 |  | Initial | Hệ thống | Bắt đầu; điều kiện: người dùng đã đăng nhập |
| A1 | 1 | Action | Người dùng | [1] Mở trang tài khoản |
| A2 | 2 | Action | Hệ thống | [2] Hiển thị hồ sơ và biểu mẫu |
| D1 | 3 | Decision | Hệ thống | [3] Chọn thao tác |
| A3 | 3.1 | Action | Người dùng | [3.1] Sửa tên, locale hoặc timezone |
| A4 | 3.1 | Action | Người dùng | [3.1] Gửi cập nhật hồ sơ |
| D2 | 3.1 | Decision | Hệ thống | [3.1] Dữ liệu hồ sơ hợp lệ? |
| A5 | 3.1 | Action | Hệ thống | [3.1] Lưu hồ sơ |
| A6 | 3.1 | Action | Hệ thống | [3.1] Hiển thị hồ sơ mới và báo thành công |
| A7 | 3.2 | Action | Người dùng | [3.2] Nhập mật khẩu hiện tại và mật khẩu mới |
| A8 | 3.2 | Action | Người dùng | [3.2] Gửi yêu cầu đổi mật khẩu |
| D3 | 3.2 | Decision | Hệ thống | [3.2] Mật khẩu hợp lệ? |
| A9 | 3.2 | Action | Hệ thống | [3.2] Lưu mật khẩu mới |
| A10 | 3.2 | Action | Hệ thống | [3.2] Báo đổi mật khẩu thành công |
| A11 | 7.1–7.3 | Action | Hệ thống | [7.1–7.3] Báo lỗi xác thực hoặc dữ liệu hồ sơ |
| A12 | 7.4–7.5 | Action | Hệ thống | [7.4–7.5] Báo lỗi mật khẩu |
| A13 | 7.6 | Action | Người dùng | [7.6] Rời trang trước khi gửi |
| A14 | 7.7 | Action | Hệ thống | [7.7] Báo lỗi API hoặc dữ liệu |
| M1 |  | Merge | Hệ thống | Nhập các luồng thành công |
| F1 |  | Final | Hệ thống | Kết thúc thành công |
| F2 |  | Final | Hệ thống | Kết thúc thất bại |
| F3 |  | Final | Hệ thống | Kết thúc không gửi thay đổi |

BẢNG CẠNH 3b:
| Từ ID | Đến ID | Guard |
|---|---|---|
| A0 | A1 | luôn |
| A1 | A2 | luôn |
| A2 | D1 | luôn |
| D1 | A3 | [cập nhật hồ sơ] |
| D1 | A7 | [đổi mật khẩu] |
| D1 | A13 | [rời trang] |
| A3 | A4 | luôn |
| A4 | D2 | luôn |
| D2 | A5 | [hợp lệ] |
| D2 | A11 | [không hợp lệ] |
| A5 | A6 | [lưu thành công] |
| A5 | A14 | [lỗi khi lưu] |
| A6 | M1 | luôn |
| A7 | A8 | luôn |
| A8 | D3 | luôn |
| D3 | A9 | [mật khẩu hiện tại đúng, mật khẩu mới đạt giới hạn và khác mật khẩu cũ] |
| D3 | A12 | [mật khẩu sai/không hợp lệ] |
| A9 | A10 | [cập nhật thành công] |
| A9 | A14 | [lỗi khi cập nhật] |
| A10 | M1 | luôn |
| A11 | A3 | [người dùng sửa lại] |
| A11 | F2 | [người dùng dừng] |
| A12 | A7 | [người dùng nhập lại] |
| A12 | F2 | [người dùng dừng] |
| A13 | F3 | luôn |
| A14 | F2 | luôn |
| M1 | F1 | luôn |

YÊU CẦU: Vẽ theo đúng các node, cạnh, guard và swimlane. Có Initial, Decision, Merge, Final thành công/thất bại/hủy; không node treo. Không tạo action cho API hay truy vấn DB không có trong bảng. Báo rõ nếu phát hiện thiếu hoặc mâu thuẫn trước khi đề xuất điều chỉnh. Kiểm tra Action=14, Decision=3, cạnh=27.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```
Vẽ UML SEQUENCE DIAGRAM cho UC03 - Cập nhật thông tin cá nhân của hệ thống Veriq, định dạng PlantUML, nhãn Tiếng Việt. Mức chi tiết phù hợp với sơ đồ khóa luận, không tách mỗi truy vấn nội bộ thành message riêng.
ĐẶC TẢ ĐÃ CHỐT, chép đầy đủ:
## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Tại trang “Tài khoản và bảo mật”, người dùng có thể sửa tên hiển thị, locale, timezone hoặc đổi mật khẩu bằng mật khẩu hiện tại. Đây là hai nhánh độc lập trong một UC theo tài liệu đầu vào. Email và vai trò được hiển thị nhưng không sửa tại form này.

### Tiền điều kiện
- Người dùng đã đăng nhập, token còn hiệu lực và tài khoản hiện hành còn tồn tại.
- Người dùng chỉ thao tác trên hồ sơ của chính mình.
- Nhánh đổi mật khẩu yêu cầu người dùng cung cấp mật khẩu hiện tại.

### Hậu điều kiện
- Thành công nhánh hồ sơ: các trường được gửi hợp lệ được lưu, hồ sơ được tải lại và UI báo “Đã cập nhật thông tin cá nhân”.
- Thành công nhánh mật khẩu: hash và thời điểm đổi mật khẩu được lưu; backend thu hồi phiên khác như side effect, rồi UI báo “Đã đổi mật khẩu và đóng các phiên khác”. Danh sách hay thao tác quản lý phiên không thuộc UC này.
- Thất bại: UI hiển thị lỗi; nếu lỗi validation thì dữ liệu form còn để sửa. Không khẳng định rollback khi kết quả ghi CSDL không xác định.
- Rời trang trước khi gửi: không có yêu cầu cập nhật được gửi.

### Tác nhân chính
Người dùng đã đăng nhập.

### Tác nhân phụ
Không có tác nhân nghiệp vụ phụ. API, service và cơ sở dữ liệu là thành phần nội bộ.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang “Tài khoản và bảo mật”. |  |
| 2 |  | Đọc hồ sơ hiện hành qua API cá nhân; hiển thị tên hiển thị, email, vai trò, locale, timezone và form đổi mật khẩu. (đã sửa) |
| 3 | Chọn thao tác cập nhật hồ sơ hoặc đổi mật khẩu. (đã sửa) |  |
| 4 |  | Hiển thị form tương ứng; email và vai trò vẫn chỉ đọc. (đã sửa) |
| 5 | Nhập dữ liệu vào form được chọn. (đã sửa) |  |
| 6 | Gửi form tương ứng. (đã sửa) |  |
| 7 |  | Xác thực token, quyền truy cập tài khoản hiện hành và dữ liệu theo nhánh đã chọn. (đã sửa) |
| 8 |  | Nếu cập nhật thành công, trả kết quả; nhánh hồ sơ tải lại hồ sơ, nhánh mật khẩu xóa giá trị mật khẩu trên form. (đã sửa) |
| 9 |  | Hiển thị thông báo thành công và kết thúc UC. (đã sửa) |

### Luồng sự kiện thay thế

**3.1. Cập nhật hồ sơ cá nhân**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Sửa tên hiển thị, locale hoặc timezone; email và vai trò không chỉnh sửa được. (đã sửa) |  |
| 3.1.2 | Nhấn “Lưu thông tin”. |  |
| 3.1.3 |  | Kiểm tra locale nếu có và kiểm tra timezone; gửi PATCH `/xac-thuc/ca-nhan`. (đã sửa) |
| 3.1.4 |  | API kiểm tra schema (`full_name` 2–100, `locale` 2–20, `timezone` 2–100 ký tự; field lạ bị từ chối); service từ chối payload rỗng. (đã sửa) |
| 3.1.5 |  | Cập nhật hồ sơ và audit các trường đổi; trả dữ liệu cập nhật. (đã sửa) |
| 3.1.6 |  | Gọi lại API hồ sơ, hiển thị dữ liệu mới và thông báo thành công. (đã sửa) |
| 3.1.7 |  | Kết thúc UC thành công. (thêm mới) |

**3.2. Đổi mật khẩu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.1 | Nhập mật khẩu hiện tại và mật khẩu mới. |  |
| 3.2.2 | Nhấn “Đổi mật khẩu”. |  |
| 3.2.3 |  | Kiểm tra mật khẩu hiện tại dài 1–128 và mật khẩu mới dài 12–128 ký tự; gửi POST `/xac-thuc/doi-mat-khau`. (đã sửa) |
| 3.2.4 |  | Service xác minh mật khẩu hiện tại. (đã sửa) |
| 3.2.5 |  | Service từ chối mật khẩu mới trùng mật khẩu hiện tại. |
| 3.2.6 |  | Lưu hash và thời điểm đổi; backend thu hồi phiên khác như side effect. (đã sửa) |
| 3.2.7 |  | UI xóa giá trị hai ô mật khẩu và hiển thị thông báo đổi mật khẩu thành công. (đã sửa) |
| 3.2.8 |  | Kết thúc UC thành công. (thêm mới) |

### Luồng sự kiện ngoại lệ

- **7.1.** Token hết hạn hoặc người dùng không còn quyền truy cập: API từ chối với 401/403; UI báo lỗi xác thực và kết thúc UC thất bại.
- **7.2.** Hồ sơ/tài khoản không tìm thấy: API trả 404; UI báo không tìm thấy, kết thúc UC thất bại.
- **7.3.** Thiếu `full_name`, giá trị không đúng độ dài, locale/timezone không hợp lệ, payload rỗng hoặc có field ngoài schema: UI giữ form và thông báo lỗi; quay lại bước 3.1.1.
- **7.4.** Mật khẩu hiện tại sai: API từ chối (403); UI báo lỗi và quay lại bước 3.2.1.
- **7.5.** Mật khẩu mới quá ngắn/quá dài hoặc trùng mật khẩu hiện tại: API/service từ chối; UI báo lỗi và quay lại bước 3.2.1.
- **7.6.** Người dùng rời trang trước bước 6: trình duyệt không gửi form, kết thúc UC không thay đổi dữ liệu. Mã UI không thể hiện hộp thoại xác nhận hủy.
- **7.7.** Lỗi API/CSDL khi đọc hoặc ghi: UI báo lỗi yêu cầu và kết thúc thất bại. Trạng thái ghi không xác định không được mô tả như rollback chắc chắn.
- **7.8.** Không có trường hồ sơ cần cập nhật: service trả 422; UI báo không có dữ liệu cần cập nhật và quay lại bước 3.1.1.

### Giả định / Câu hỏi cần làm rõ
- Tiêu đề UC03 là “Cập nhật thông tin cá nhân”, song phần mô tả gốc đồng thời đưa đổi mật khẩu vào; giữ phạm vi gộp theo luồng nguồn thay vì tự đổi mã UC. Có thể tách đổi mật khẩu thành UC riêng nếu chủ tài liệu xác nhận.
- Schema cho locale/timezone đặt giới hạn độ dài nhưng kiểm tra danh sách giá trị được hỗ trợ hiện nằm ở giao diện. Không giả định API tự kiểm tra chuẩn locale/timezone.
- Trang có thêm các API xem/thu hồi phiên. Theo yêu cầu, chúng bị loại khỏi bộ UC; side effect thu hồi phiên khác khi đổi mật khẩu vẫn được ghi nhận ở mức hệ thống.

LIFELINE 4a, trái sang phải: Người dùng, Giao diện, Controller/API, Service, Database.

BẢNG MESSAGE 4b:

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện | [1] moTrangTaiKhoan() | đồng bộ | chính |
| 2 | 2 | Giao diện | Controller/API | [2] getHoSoCaNhan() | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] layHoSoNguoiDung(userId) | đồng bộ | chính |
| 4 | 2 | Service | Database | [2] docHoSo(userId) | đồng bộ | chính |
| 5 | 2 | Database | Service | [2] traHoSo() | trả về | chính |
| 6 | 2 | Service | Controller/API | [2] traDuLieuHoSo() | trả về | chính |
| 7 | 2 | Controller/API | Giao diện | [2] traHoSoVaBieuMau() | trả về | chính |
| 8 | 2 | Giao diện | Người dùng | [2] hienThiHoSoVaForm() | trả về | chính |
| 9 | 3.1 | Người dùng | Giao diện | [3.1] suaVaGuiHoSo(thongTin) | đồng bộ | alt [cập nhật hồ sơ] |
| 10 | 3.1 | Giao diện | Controller/API | [3.1] patchHoSo(thongTin) | đồng bộ | alt [cập nhật hồ sơ] |
| 11 | 3.1 | Controller/API | Service | [3.1] kiemTraQuyenVaCapNhatHoSo() | đồng bộ | alt [dữ liệu hợp lệ] |
| 12 | 3.1 | Service | Database | [3.1] luuHoSo(userId, thongTin) | đồng bộ | alt [dữ liệu hợp lệ] |
| 13 | 3.1 | Database | Service | [3.1] traKetQuaLuuHoSo() | trả về | alt [dữ liệu hợp lệ] |
| 14 | 3.1 | Service | Controller/API | [3.1] traKetQuaHoSo() | trả về | alt [thành công/lỗi] |
| 15 | 3.1 | Controller/API | Giao diện | [3.1] traHoSoMoiHoacLoi() | trả về | alt [thành công/lỗi] |
| 16 | 3.1 | Giao diện | Người dùng | [3.1] hienThiHoSoMoiHoacLoi() | trả về | alt [thành công/lỗi] |
| 17 | 3.2 | Người dùng | Giao diện | [3.2] nhapVaGuiMatKhau(current, new) | đồng bộ | alt [đổi mật khẩu] |
| 18 | 3.2 | Giao diện | Controller/API | [3.2] postDoiMatKhau(current, new) | đồng bộ | alt [đổi mật khẩu] |
| 19 | 3.2 | Controller/API | Service | [3.2] xacThucVaCapNhatMatKhau() | đồng bộ | alt [dữ liệu hợp lệ] |
| 20 | 3.2 | Service | Database | [3.2] capNhatCredential(userId, hash) | đồng bộ | alt [dữ liệu hợp lệ] |
| 21 | 3.2 | Database | Service | [3.2] traKetQuaDoiMatKhau() | trả về | alt [dữ liệu hợp lệ] |
| 22 | 3.2 | Service | Controller/API | [3.2] traKetQuaDoiMatKhau() | trả về | alt [thành công/lỗi] |
| 23 | 3.2 | Controller/API | Giao diện | [3.2] traKetQua() | trả về | alt [thành công/lỗi] |
| 24 | 3.2 | Giao diện | Người dùng | [3.2] xoaTruongMatKhauVaThongBao() | trả về | alt [thành công/lỗi] |
| 25 | 7.6 | Người dùng | Giao diện | [7.6] roiTrangTruocKhiGui() | đồng bộ | opt [hủy trước khi gửi] |
| 26 | 7.6 | Giao diện | Người dùng | [7.6] khongGuiCapNhat() | trả về | opt [hủy trước khi gửi] |

YÊU CẦU: Giữ thứ tự message, return và guard. Dùng alt cho chọn cập nhật hồ sơ/đổi mật khẩu, kết quả validation; opt cho rời trang trước khi gửi. Không gọi nhảy lớp, không thêm quản lý phiên. Mỗi lời gọi đồng bộ phải có return. Kiểm tra L=5, M=26, F=4; báo nếu bảng có điểm thiếu.
```

## TỰ KIỂM TRA UC03

- [x] Phần 1 ghi vấn đề phát hiện và số tình huống đã rà.
- [x] Phần 2 đủ mô tả, tiền/hậu điều kiện, tác nhân và ba loại luồng; có giả định/câu hỏi.
- [x] Phần 3: Action=14, Decision=3, cạnh=27; mọi node có đường vào/ra hợp lệ.
- [x] Phần 4: bảng và prompt Sequence có cùng 26 message; M=26; F=4, L=5; các request có return; mỗi request có return được kiểm theo cặp endpoint/bước; các nhánh dùng alt guards.
- [x] Phần 5/6 chứa đặc tả, bảng node/cạnh, lifeline/message tự đủ.
- [x] Đã đối chiếu: số Action/node/edge, message và prompt table khớp; không xuất code vì cấu hình PROMPT.
## Bảng theo dõi sau UC03

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |


# UC04 - Khôi phục mật khẩu

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 5–7 | SAI | Đặc tả nói email không tồn tại thì hiển thị form nhập mã, nhưng không phản ánh hành vi bảo vệ khỏi dò tài khoản. Backend vẫn trả phản hồi chung, không tạo mã nếu email lạ. | Dùng cùng phản hồi và form cho cả hai kết quả; không tuyên bố mã đã được gửi. |
| 6 | THIẾU | Không nêu mã 6 số, hạn 1 phút, vô hiệu mã cũ, audit, hoặc lỗi dịch vụ email bị bắt. | Nêu các hành vi có trong service; lỗi gửi mail được log nhưng không tạo thông báo riêng. |
| 8.1 | THIẾU | Không nêu countdown hoặc giới hạn gửi lại. | UI cho resend sau 60 giây; API giới hạn 3 yêu cầu/5 phút. |
| 10 | MƠ HỒ | Chưa nói rõ mã phải còn hạn, chưa dùng; verify endpoint có rate limit. | Bổ sung trạng thái mã và giới hạn 5/5 phút. |
| 14 | THIẾU | Không nêu độ dài mật khẩu, rate limit, token bị consume trước cập nhật. | Bổ sung mật khẩu 12–128, giới hạn 5/5 phút và thứ tự tiêu thụ mã. |
| 5, 6, 10, 14 | THIẾU | Thiếu invalid email, rate limit, mail error, mã sai/hết hạn/dùng rồi, token hết hạn giữa verify/reset, account missing, lỗi API/CSDL và hủy. | Thêm các nhánh có điểm quay lại hoặc kết thúc UC; ghi rõ mail failure vẫn theo phản hồi chung. |
| Tiền/hậu điều kiện | THIẾU | Chưa ghi thất bại sau khi consume token và tác động khi đổi mật khẩu. | Nêu hậu điều kiện thành công/thất bại thận trọng; phiên bị thu hồi là side effect, không là UC riêng. |
| Tác nhân phụ | MƠ HỒ | Không xác định nhà cung cấp email. | Giữ tác nhân tổng quát “Dịch vụ email”. |
| CRUD quản lý | Không áp dụng | UC phục hồi mật khẩu không phải UC quản lý danh sách tài khoản. | Không thêm thao tác quản trị tài khoản. |

Đã kiểm: 5 điểm rẽ chính và các tình huống email không hợp lệ/không tồn tại, rate limit, mail failure, mã sai/hết hạn/đã dùng, password sai độ dài, thiếu token, account missing, lỗi API/CSDL và hủy.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Người chưa đăng nhập yêu cầu mã qua email, xác minh mã và đặt mật khẩu mới. Hệ thống trả phản hồi chung để không tiết lộ email có gắn với tài khoản hay không.

### Tiền điều kiện
- Người dùng truy cập được màn hình đăng nhập và có thể nhập email.
- Để hoàn tất, người dùng cần truy cập hộp thư tương ứng và cung cấp mã chưa hết hạn.
- Không yêu cầu đăng nhập.

### Hậu điều kiện
- Thành công: password hash được cập nhật và giao diện chuyển về trang đăng nhập.
- Mã khôi phục được consume khi gửi yêu cầu đặt lại. Mã có thể hết hiệu lực nếu lỗi phát sinh sau thao tác consume.
- Backend thu hồi các phiên đăng nhập hiện có sau khi đổi mật khẩu. Đây là side effect, không mở rộng thành UC quản lý phiên.
- Email không gắn với tài khoản vẫn nhận phản hồi chung; hệ thống không tạo mã.

### Tác nhân chính
Người dùng chưa đăng nhập.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu gửi mã khôi phục 6 chữ số. Nhà cung cấp cụ thể không được xác định trong mã nguồn.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn “Quên mật khẩu” tại trang đăng nhập. |  |
| 2 |  | Hiển thị form email. |
| 3 | Nhập email. |  |
| 4 | Nhấn “Gửi mã”. |  |
| 5 |  | Kiểm tra định dạng email và giới hạn 3 yêu cầu trong 5 phút. (đã sửa) |
| 6 |  | Nếu tìm thấy tài khoản, tạo mã 6 số, vô hiệu hóa mã trước, lưu mã băm với hạn 1 phút, ghi audit và thử gửi email. Lỗi gửi email được log, không hiện thành lỗi riêng. (đã sửa) |
| 7 |  | Trả thông báo chung và mở form nhập mã, bất kể tài khoản có tồn tại hay không. (đã sửa) |
| 8 | Nhập mã nhận qua email. |  |
| 9 | Xác nhận mã. |  |
| 10 |  | Kiểm tra mã chưa dùng, chưa hết hạn và chưa vượt giới hạn 5 lần/5 phút. (đã sửa) |
| 11 |  | Mã hợp lệ thì mở form đặt mật khẩu mới, giữ mã trên URL. |
| 12 | Nhập mật khẩu mới. |  |
| 13 | Xác nhận đặt lại. |  |
| 14 |  | Kiểm tra mật khẩu 12–128 ký tự, giới hạn endpoint và consume mã trước khi tìm credential. (đã sửa) |
| 15 |  | Cập nhật password hash và audit; backend thu hồi phiên hiện có như side effect. (đã sửa) |
| 16 |  | Trả thành công và chuyển về trang đăng nhập. |
| 17 |  | Kết thúc UC. |

### Luồng sự kiện thay thế

- **5.1. Email không có tài khoản:** không tạo mã; hệ thống vẫn trả thông báo chung tại bước 7 và tiếp tục bước 8. (đã sửa)
- **8.1.1.** Sau countdown 60 giây, người dùng chọn “Gửi lại mã”. **8.1.2.** UI gọi lại endpoint gửi mã, chịu cùng rate limit; khi API chấp nhận yêu cầu, countdown đặt lại. Mã cũ bị vô hiệu khi có mã mới.
- **10.1. Mã sai hoặc hết hạn:** giao diện báo lỗi; quay lại bước 8 hoặc chọn gửi lại mã.
- **14.1. Mật khẩu mới sai độ dài:** hiển thị lỗi và quay lại bước 12.

### Luồng sự kiện ngoại lệ

- **5.2.** Email sai định dạng hoặc vượt giới hạn gửi mã: API từ chối; giao diện báo lỗi và kết thúc lần gửi hiện tại.
- **6.2.** Dịch vụ email lỗi: backend ghi log nhưng vẫn trả thông báo chung; người dùng có thể không nhận được email.
- **10.2.** Mã không tồn tại, đã dùng hoặc hết hạn: báo lỗi; quay lại bước 8 hoặc nhánh gửi lại.
- **14.2.** Mã hết hạn/đã dùng sau bước xác minh: không cập nhật mật khẩu; bắt đầu lại UC04.
- **14.3.** Không tìm thấy credential theo email trong mã: API từ chối. Mã có thể đã bị consume.
- **7.1.** Lỗi mạng/API/CSDL khi lưu token hoặc cập nhật mật khẩu: hiển thị lỗi nếu API trả lỗi; không báo hoàn tất. Không khẳng định rollback sau khi token đã consume.
- **11.1.** Mở form đặt lại không có token trên URL: UI chuyển về trang khôi phục mật khẩu.
- **13.1.** Rời trang trước khi gửi mật khẩu mới: không gửi yêu cầu đặt lại.

### Giả định / Câu hỏi cần làm rõ
- Backend sinh đúng 6 chữ số, trong khi form nhận token có độ dài tối đa 128 và yêu cầu tối thiểu 6; schema không buộc chỉ gồm chữ số.
- Hạn mã là 1 phút; countdown gửi lại là 60 giây. Rate limit có thể vẫn chặn resend sau khi countdown hết.
- Lỗi gửi email được bắt và ghi log. Không thể kết luận email đã tới người nhận chỉ từ phản hồi chung.
- Token bị đánh dấu đã dùng trước khi cập nhật credential. Nếu bước tiếp theo lỗi, người dùng có thể cần yêu cầu mã mới.


## PHẦN 3 - PHÂN RÃ ACTIVITY (mức nghiệp vụ phù hợp khóa luận)

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Hệ thống | Bắt đầu; không yêu cầu đăng nhập |
| A1 | 1-2 | Action | Người dùng / Hệ thống | [1-2] Mở form khôi phục mật khẩu |
| A2 | 3-4 | Action | Người dùng | [3-4] Nhập email và yêu cầu gửi mã |
| D1 | 5 | Decision | Hệ thống | [5] Email hợp lệ và còn trong giới hạn gửi? |
| A3 | 5.2 | Action | Hệ thống | [5.2] Báo lỗi định dạng hoặc giới hạn |
| D2 | 6 | Decision | Hệ thống | [6] Có tài khoản khớp email? |
| A4 | 6 | Action | Hệ thống | [6] Tạo mã, lưu an toàn và thử gửi email |
| A5 | 6.2 | Action | Hệ thống ngoài | [6.2] Trả lỗi gửi email (nếu xảy ra) |
| M1 | 6-7 | Merge | Hệ thống | Gộp phản hồi chung cho email có hoặc không có tài khoản |
| A6 | 7-9 | Action | Người dùng / Hệ thống | [7-9] Nhận form, nhập mã và xác nhận |
| D3 | 10 | Decision | Hệ thống | [10] Mã còn hiệu lực và request chưa vượt giới hạn? |
| A7 | 10.1/10.2 | Action | Hệ thống | [10.1/10.2] Báo mã không hợp lệ hoặc hết hạn |
| A8 | 11 | Action | Hệ thống | [11] Mở form mật khẩu mới với mã khôi phục |
| A9 | 12-13 | Action | Người dùng | [12-13] Nhập mật khẩu mới và gửi yêu cầu |
| D4 | 14 | Decision | Hệ thống | [14] Mật khẩu hợp lệ và mã còn dùng được? |
| A10 | 14.1-14.3 | Action | Hệ thống | [14.1-14.3] Báo lỗi mật khẩu, mã hoặc tài khoản |
| A11 | 14-16 | Action | Hệ thống | [14-16] Consume mã, cập nhật mật khẩu và trả kết quả |
| A12 | 7.1/7.7 | Action | Hệ thống | [7.1/7.7] Báo lỗi xử lý yêu cầu |
| A13 | 8.1.1-8.1.2 | Action | Người dùng / Hệ thống | [8.1.1-8.1.2] Gửi lại mã sau countdown |
| A14 | 13.1 | Action | Người dùng | [13.1] Rời trang trước khi gửi mật khẩu |
| A15 | 16-17 | Action | Hệ thống | [16-17] Chuyển về đăng nhập và kết thúc |
| M2 | 10.1/8.1 | Merge | Hệ thống | Nhập lại mã hoặc gửi lại mã |
| F1 | 17 | Final | Hệ thống | Đặt lại mật khẩu thành công |
| F2 | 5.2/7.1/7.7/14.3 | Final | Hệ thống | Kết thúc thất bại, không xác nhận đổi mật khẩu |
| F3 | 13.1 | Final | Hệ thống | Kết thúc trước khi gửi, không đổi mật khẩu |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | A2 | Form email hiển thị |
| A2 | D1 | Người dùng gửi email |
| D1 | A3 | [Email sai định dạng hoặc vượt giới hạn] |
| D1 | D2 | [Email hợp lệ và trong giới hạn] |
| A3 | F2 | Yêu cầu bị từ chối |
| D2 | A4 | [Có tài khoản] |
| D2 | M1 | [Không có tài khoản] |
| A4 | A5 | [Dịch vụ email trả lỗi] |
| A4 | M1 | [Email gửi được chấp nhận] |
| A5 | M1 | Lỗi gửi được bắt; phản hồi chung vẫn được trả |
| M1 | A6 | Không tiết lộ trạng thái tài khoản |
| A6 | D3 | Người dùng xác nhận mã |
| D3 | A7 | [Mã sai/hết hạn/đã dùng hoặc vượt giới hạn] |
| D3 | A8 | [Mã hợp lệ] |
| A7 | M2 | Có thể nhập lại hoặc gửi lại |
| M2 | A6 | [Nhập lại mã] |
| M2 | A13 | [Gửi lại sau countdown] |
| A13 | M1 | Yêu cầu gửi mã mới được xử lý theo giới hạn |
| A8 | A9 | Form đặt mật khẩu mới hiển thị |
| A9 | D4 | Người dùng gửi mật khẩu mới |
| D4 | A10 | [Mật khẩu sai độ dài hoặc mã/tài khoản không hợp lệ] |
| D4 | A11 | [Mật khẩu hợp lệ và mã được consume] |
| A10 | A9 | [Lỗi có thể sửa tại form] |
| A10 | F2 | [Mã hết hạn/đã dùng hoặc tài khoản không còn] |
| A11 | A12 | [Lỗi API/CSDL trong xử lý] |
| A11 | A15 | [Cập nhật mật khẩu thành công] |
| A12 | F2 | Không báo thành công |
| A9 | A14 | [Người dùng rời trang trước khi submit] |
| A14 | F3 | Không gửi yêu cầu đặt lại |
| A15 | F1 | Mật khẩu mới đã lưu |

### 3c. Số liệu

N = 20 ô nghiệp vụ có nội dung; M = 15 Action; D = 4 Decision; E = 31 cạnh. Action gộp các tương tác liền nhau theo mức người dùng, không phóng đại thao tác hạ tầng thành các node riêng.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức nghiệp vụ phù hợp khóa luận)

### 4a. Lifeline trái sang phải

Người dùng → Giao diện → API khôi phục → Dịch vụ xác thực → Cơ sở dữ liệu → Dịch vụ email. Chỉ giữ thành phần cần thiết để giải thích quy trình; không tách Repository, không vẽ quản lý phiên.

### 4b. Bảng message theo thời gian

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện | [1] chonQuenMatKhau() | đồng bộ | chính |
| 2 | 1-2 | Giao diện | Người dùng | [1-2] hienThiFormEmail() | trả về | chính |
| 3 | 3-4 | Người dùng | Giao diện | [3-4] nhapEmailVaGui(email) | đồng bộ | chính |
| 4 | 5 | Giao diện | API khôi phục | [5] yeuCauGuiMa(email) | đồng bộ | alt [email hợp lệ, trong giới hạn] |
| 5 | 5-6 | API khôi phục | Dịch vụ xác thực | [5-6] xuLyYeuCauKhoiPhuc(email) | đồng bộ | alt [email hợp lệ, trong giới hạn] |
| 6 | 6 | Dịch vụ xác thực | Cơ sở dữ liệu | [6] timTaiKhoanVaLuuMa(email) | đồng bộ | alt [tài khoản tồn tại] |
| 7 | 6 | Cơ sở dữ liệu | Dịch vụ xác thực | [6] traKetQuaTaiKhoanVaMa() | trả về | alt [tài khoản tồn tại] |
| 8 | 6 | Dịch vụ xác thực | Dịch vụ email | [6] guiMaKhoiPhuc(email, ma) | đồng bộ | opt [tài khoản tồn tại] |
| 9 | 6.2 | Dịch vụ email | Dịch vụ xác thực | [6.2] traKetQuaGuiMail() | trả về | opt [mail lỗi thì ghi log và tiếp tục] |
| 10 | 7 | Dịch vụ xác thực | API khôi phục | [7] traPhanHoiChung() | trả về | alt [email có/không có tài khoản] |
| 11 | 7 | API khôi phục | Giao diện | [7] moFormNhapMa() | trả về | alt [email hợp lệ] |
| 12 | 7 | Giao diện | Người dùng | [7] hienThiThongBaoChung() | trả về | alt [email hợp lệ] |
| 13 | 8-9 | Người dùng | Giao diện | [8-9] nhapVaXacNhanMa(ma) | đồng bộ | loop [nhập mã hoặc yêu cầu gửi lại sau countdown] |
| 14 | 10 | Giao diện | API khôi phục | [10] xacMinhMa(ma) | đồng bộ | alt [xác minh mã] |
| 15 | 10 | API khôi phục | Dịch vụ xác thực | [10] kiemTraMaVaHan(ma) | đồng bộ | alt [request không vượt giới hạn] |
| 16 | 10 | Dịch vụ xác thực | Cơ sở dữ liệu | [10] docTrangThaiMa(ma) | đồng bộ | alt [request không vượt giới hạn] |
| 17 | 10 | Cơ sở dữ liệu | Dịch vụ xác thực | [10] traTrangThaiMa() | trả về | alt [request không vượt giới hạn] |
| 18 | 10-11 | Dịch vụ xác thực | API khôi phục | [10-11] traKetQuaXacMinh() | trả về | alt [mã hợp lệ/sai/hết hạn/đã dùng] |
| 19 | 10-11 | API khôi phục | Giao diện | [10-11] traKetQuaMa() | trả về | alt [mã hợp lệ/sai/hết hạn/đã dùng] |
| 20 | 10.1/10.2/11 | Giao diện | Người dùng | [10.1/10.2/11] hienThiLoiHoacFormMatKhau() | trả về | alt [mã không hợp lệ / mã hợp lệ] |
| 21 | 8.1.1-8.1.2 | Giao diện | API khôi phục | [8.1.1-8.1.2] yeuCauGuiLaiMa(email) | đồng bộ | opt [đã hết countdown] |
| 22 | 8.1.2 | API khôi phục | Giao diện | [8.1.2] traKetQuaGuiLai() | trả về | opt [rate limit chấp nhận] |
| 23 | 12-13 | Người dùng | Giao diện | [12-13] nhapVaGuiMatKhauMoi(matKhau) | đồng bộ | alt [đặt lại mật khẩu] |
| 24 | 14 | Giao diện | API khôi phục | [14] datLaiMatKhau(token, matKhau) | đồng bộ | alt [đầu vào hợp lệ] |
| 25 | 14-15 | API khôi phục | Dịch vụ xác thực | [14-15] consumeMaVaCapNhatMatKhau() | đồng bộ | alt [mật khẩu hợp lệ] |
| 26 | 14-15 | Dịch vụ xác thực | Cơ sở dữ liệu | [14-15] consumeMaVaLuuMatKhauMoi() | đồng bộ | alt [mật khẩu hợp lệ] |
| 27 | 14-15 | Cơ sở dữ liệu | Dịch vụ xác thực | [14-15] traKetQuaCapNhat() | trả về | alt [cập nhật thành công/lỗi] |
| 28 | 14.1-14.3 | Dịch vụ xác thực | API khôi phục | [14.1-14.3] traLoiTuChoi() | trả về | alt [mật khẩu sai/mã hết hạn/tài khoản thiếu] |
| 29 | 14.1-14.3 | API khôi phục | Giao diện | [14.1-14.3] hienThiLoiDatLai() | trả về | alt [dữ liệu không hợp lệ hoặc lỗi xử lý] |
| 30 | 15-16 | Dịch vụ xác thực | API khôi phục | [15-16] traDatLaiThanhCong() | trả về | alt [đã lưu mật khẩu mới] |
| 31 | 16 | API khôi phục | Giao diện | [16] chuyenDenDangNhap() | trả về | alt [thành công] |
| 32 | 16 | Giao diện | Người dùng | [16] hienThiTrangDangNhap() | trả về | alt [thành công] |
| 33 | 13.1 | Người dùng | Giao diện | [13.1] roiTrangTruocKhiGui() | đồng bộ | opt [hủy trước khi submit] |
| 34 | 13.1 | Giao diện | Người dùng | [13.1] khongGuiYeuCauDatLai() | trả về | opt [hủy trước khi submit] |

### 4c. Số liệu

N = 20 ô nội dung nghiệp vụ; M = 34 message; F = 7 fragment (alt đầu vào/rate limit, alt tài khoản, opt lỗi email, alt xác minh mã, loop gửi lại mã, alt đặt mật khẩu, opt rời trang); L = 6. Các trao đổi nội bộ chỉ thể hiện khi cần giải thích quyết định nghiệp vụ.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC04 - Khôi phục mật khẩu của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt. Sơ đồ dành cho khóa luận, trình bày ở mức nghiệp vụ.

ĐẶC TẢ ĐẦY ĐỦ:
## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Người chưa đăng nhập yêu cầu mã qua email, xác minh mã và đặt mật khẩu mới. Hệ thống trả phản hồi chung để không tiết lộ email có gắn với tài khoản hay không.

### Tiền điều kiện
- Người dùng truy cập được màn hình đăng nhập và có thể nhập email.
- Để hoàn tất, người dùng cần truy cập hộp thư tương ứng và cung cấp mã chưa hết hạn.
- Không yêu cầu đăng nhập.

### Hậu điều kiện
- Thành công: password hash được cập nhật và giao diện chuyển về trang đăng nhập.
- Mã khôi phục được consume khi gửi yêu cầu đặt lại. Mã có thể hết hiệu lực nếu lỗi phát sinh sau thao tác consume.
- Backend thu hồi các phiên đăng nhập hiện có sau khi đổi mật khẩu. Đây là side effect, không mở rộng thành UC quản lý phiên.
- Email không gắn với tài khoản vẫn nhận phản hồi chung; hệ thống không tạo mã.

### Tác nhân chính
Người dùng chưa đăng nhập.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu gửi mã khôi phục 6 chữ số. Nhà cung cấp cụ thể không được xác định trong mã nguồn.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn “Quên mật khẩu” tại trang đăng nhập. |  |
| 2 |  | Hiển thị form email. |
| 3 | Nhập email. |  |
| 4 | Nhấn “Gửi mã”. |  |
| 5 |  | Kiểm tra định dạng email và giới hạn 3 yêu cầu trong 5 phút. (đã sửa) |
| 6 |  | Nếu tìm thấy tài khoản, tạo mã 6 số, vô hiệu hóa mã trước, lưu mã băm với hạn 1 phút, ghi audit và thử gửi email. Lỗi gửi email được log, không hiện thành lỗi riêng. (đã sửa) |
| 7 |  | Trả thông báo chung và mở form nhập mã, bất kể tài khoản có tồn tại hay không. (đã sửa) |
| 8 | Nhập mã nhận qua email. |  |
| 9 | Xác nhận mã. |  |
| 10 |  | Kiểm tra mã chưa dùng, chưa hết hạn và chưa vượt giới hạn 5 lần/5 phút. (đã sửa) |
| 11 |  | Mã hợp lệ thì mở form đặt mật khẩu mới, giữ mã trên URL. |
| 12 | Nhập mật khẩu mới. |  |
| 13 | Xác nhận đặt lại. |  |
| 14 |  | Kiểm tra mật khẩu 12–128 ký tự, giới hạn endpoint và consume mã trước khi tìm credential. (đã sửa) |
| 15 |  | Cập nhật password hash và audit; backend thu hồi phiên hiện có như side effect. (đã sửa) |
| 16 |  | Trả thành công và chuyển về trang đăng nhập. |
| 17 |  | Kết thúc UC. |

### Luồng sự kiện thay thế

- **5.1. Email không có tài khoản:** không tạo mã; hệ thống vẫn trả thông báo chung tại bước 7 và tiếp tục bước 8. (đã sửa)
- **8.1.1.** Sau countdown 60 giây, người dùng chọn “Gửi lại mã”. **8.1.2.** UI gọi lại endpoint gửi mã, chịu cùng rate limit; khi API chấp nhận yêu cầu, countdown đặt lại. Mã cũ bị vô hiệu khi có mã mới.
- **10.1. Mã sai hoặc hết hạn:** giao diện báo lỗi; quay lại bước 8 hoặc chọn gửi lại mã.
- **14.1. Mật khẩu mới sai độ dài:** hiển thị lỗi và quay lại bước 12.

### Luồng sự kiện ngoại lệ

- **5.2.** Email sai định dạng hoặc vượt giới hạn gửi mã: API từ chối; giao diện báo lỗi và kết thúc lần gửi hiện tại.
- **6.2.** Dịch vụ email lỗi: backend ghi log nhưng vẫn trả thông báo chung; người dùng có thể không nhận được email.
- **10.2.** Mã không tồn tại, đã dùng hoặc hết hạn: báo lỗi; quay lại bước 8 hoặc nhánh gửi lại.
- **14.2.** Mã hết hạn/đã dùng sau bước xác minh: không cập nhật mật khẩu; bắt đầu lại UC04.
- **14.3.** Không tìm thấy credential theo email trong mã: API từ chối. Mã có thể đã bị consume.
- **7.1.** Lỗi mạng/API/CSDL khi lưu token hoặc cập nhật mật khẩu: hiển thị lỗi nếu API trả lỗi; không báo hoàn tất. Không khẳng định rollback sau khi token đã consume.
- **11.1.** Mở form đặt lại không có token trên URL: UI chuyển về trang khôi phục mật khẩu.
- **13.1.** Rời trang trước khi gửi mật khẩu mới: không gửi yêu cầu đặt lại.

### Giả định / Câu hỏi cần làm rõ
- Backend sinh đúng 6 chữ số, trong khi form nhận token có độ dài tối đa 128 và yêu cầu tối thiểu 6; schema không buộc chỉ gồm chữ số.
- Hạn mã là 1 phút; countdown gửi lại là 60 giây. Rate limit có thể vẫn chặn resend sau khi countdown hết.
- Lỗi gửi email được bắt và ghi log. Không thể kết luận email đã tới người nhận chỉ từ phản hồi chung.
- Token bị đánh dấu đã dùng trước khi cập nhật credential. Nếu bước tiếp theo lỗi, người dùng có thể cần yêu cầu mã mới.

BẢNG NODE VÀ BẢNG CẠNH:
### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Hệ thống | Bắt đầu; không yêu cầu đăng nhập |
| A1 | 1-2 | Action | Người dùng / Hệ thống | [1-2] Mở form khôi phục mật khẩu |
| A2 | 3-4 | Action | Người dùng | [3-4] Nhập email và yêu cầu gửi mã |
| D1 | 5 | Decision | Hệ thống | [5] Email hợp lệ và còn trong giới hạn gửi? |
| A3 | 5.2 | Action | Hệ thống | [5.2] Báo lỗi định dạng hoặc giới hạn |
| D2 | 6 | Decision | Hệ thống | [6] Có tài khoản khớp email? |
| A4 | 6 | Action | Hệ thống | [6] Tạo mã, lưu an toàn và thử gửi email |
| A5 | 6.2 | Action | Hệ thống ngoài | [6.2] Trả lỗi gửi email (nếu xảy ra) |
| M1 | 6-7 | Merge | Hệ thống | Gộp phản hồi chung cho email có hoặc không có tài khoản |
| A6 | 7-9 | Action | Người dùng / Hệ thống | [7-9] Nhận form, nhập mã và xác nhận |
| D3 | 10 | Decision | Hệ thống | [10] Mã còn hiệu lực và request chưa vượt giới hạn? |
| A7 | 10.1/10.2 | Action | Hệ thống | [10.1/10.2] Báo mã không hợp lệ hoặc hết hạn |
| A8 | 11 | Action | Hệ thống | [11] Mở form mật khẩu mới với mã khôi phục |
| A9 | 12-13 | Action | Người dùng | [12-13] Nhập mật khẩu mới và gửi yêu cầu |
| D4 | 14 | Decision | Hệ thống | [14] Mật khẩu hợp lệ và mã còn dùng được? |
| A10 | 14.1-14.3 | Action | Hệ thống | [14.1-14.3] Báo lỗi mật khẩu, mã hoặc tài khoản |
| A11 | 14-16 | Action | Hệ thống | [14-16] Consume mã, cập nhật mật khẩu và trả kết quả |
| A12 | 7.1/7.7 | Action | Hệ thống | [7.1/7.7] Báo lỗi xử lý yêu cầu |
| A13 | 8.1.1-8.1.2 | Action | Người dùng / Hệ thống | [8.1.1-8.1.2] Gửi lại mã sau countdown |
| A14 | 13.1 | Action | Người dùng | [13.1] Rời trang trước khi gửi mật khẩu |
| A15 | 16-17 | Action | Hệ thống | [16-17] Chuyển về đăng nhập và kết thúc |
| M2 | 10.1/8.1 | Merge | Hệ thống | Nhập lại mã hoặc gửi lại mã |
| F1 | 17 | Final | Hệ thống | Đặt lại mật khẩu thành công |
| F2 | 5.2/7.1/7.7/14.3 | Final | Hệ thống | Kết thúc thất bại, không xác nhận đổi mật khẩu |
| F3 | 13.1 | Final | Hệ thống | Kết thúc trước khi gửi, không đổi mật khẩu |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | A2 | Form email hiển thị |
| A2 | D1 | Người dùng gửi email |
| D1 | A3 | [Email sai định dạng hoặc vượt giới hạn] |
| D1 | D2 | [Email hợp lệ và trong giới hạn] |
| A3 | F2 | Yêu cầu bị từ chối |
| D2 | A4 | [Có tài khoản] |
| D2 | M1 | [Không có tài khoản] |
| A4 | A5 | [Dịch vụ email trả lỗi] |
| A4 | M1 | [Email gửi được chấp nhận] |
| A5 | M1 | Lỗi gửi được bắt; phản hồi chung vẫn được trả |
| M1 | A6 | Không tiết lộ trạng thái tài khoản |
| A6 | D3 | Người dùng xác nhận mã |
| D3 | A7 | [Mã sai/hết hạn/đã dùng hoặc vượt giới hạn] |
| D3 | A8 | [Mã hợp lệ] |
| A7 | M2 | Có thể nhập lại hoặc gửi lại |
| M2 | A6 | [Nhập lại mã] |
| M2 | A13 | [Gửi lại sau countdown] |
| A13 | M1 | Yêu cầu gửi mã mới được xử lý theo giới hạn |
| A8 | A9 | Form đặt mật khẩu mới hiển thị |
| A9 | D4 | Người dùng gửi mật khẩu mới |
| D4 | A10 | [Mật khẩu sai độ dài hoặc mã/tài khoản không hợp lệ] |
| D4 | A11 | [Mật khẩu hợp lệ và mã được consume] |
| A10 | A9 | [Lỗi có thể sửa tại form] |
| A10 | F2 | [Mã hết hạn/đã dùng hoặc tài khoản không còn] |
| A11 | A12 | [Lỗi API/CSDL trong xử lý] |
| A11 | A15 | [Cập nhật mật khẩu thành công] |
| A12 | F2 | Không báo thành công |
| A9 | A14 | [Người dùng rời trang trước khi submit] |
| A14 | F3 | Không gửi yêu cầu đặt lại |
| A15 | F1 | Mật khẩu mới đã lưu |

### Số liệu Activity
Action=15, Decision=4, cạnh=31.

YÊU CẦU: Vẽ mọi node và cạnh đã liệt kê, giữ guard, swimlane, mã bước, ba kết thúc riêng. Có thể gom các thao tác liền nhau như trong nhãn Action; không được thêm nghiệp vụ hoặc chi tiết lớp nội bộ. Nếu phát hiện mâu thuẫn, ghi rõ và ưu tiên đặc tả đã chốt.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC04 - Khôi phục mật khẩu của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt. Sơ đồ dành cho khóa luận, giữ các trao đổi nghiệp vụ chính.

ĐẶC TẢ ĐẦY ĐỦ:
## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Người chưa đăng nhập yêu cầu mã qua email, xác minh mã và đặt mật khẩu mới. Hệ thống trả phản hồi chung để không tiết lộ email có gắn với tài khoản hay không.

### Tiền điều kiện
- Người dùng truy cập được màn hình đăng nhập và có thể nhập email.
- Để hoàn tất, người dùng cần truy cập hộp thư tương ứng và cung cấp mã chưa hết hạn.
- Không yêu cầu đăng nhập.

### Hậu điều kiện
- Thành công: password hash được cập nhật và giao diện chuyển về trang đăng nhập.
- Mã khôi phục được consume khi gửi yêu cầu đặt lại. Mã có thể hết hiệu lực nếu lỗi phát sinh sau thao tác consume.
- Backend thu hồi các phiên đăng nhập hiện có sau khi đổi mật khẩu. Đây là side effect, không mở rộng thành UC quản lý phiên.
- Email không gắn với tài khoản vẫn nhận phản hồi chung; hệ thống không tạo mã.

### Tác nhân chính
Người dùng chưa đăng nhập.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu gửi mã khôi phục 6 chữ số. Nhà cung cấp cụ thể không được xác định trong mã nguồn.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn “Quên mật khẩu” tại trang đăng nhập. |  |
| 2 |  | Hiển thị form email. |
| 3 | Nhập email. |  |
| 4 | Nhấn “Gửi mã”. |  |
| 5 |  | Kiểm tra định dạng email và giới hạn 3 yêu cầu trong 5 phút. (đã sửa) |
| 6 |  | Nếu tìm thấy tài khoản, tạo mã 6 số, vô hiệu hóa mã trước, lưu mã băm với hạn 1 phút, ghi audit và thử gửi email. Lỗi gửi email được log, không hiện thành lỗi riêng. (đã sửa) |
| 7 |  | Trả thông báo chung và mở form nhập mã, bất kể tài khoản có tồn tại hay không. (đã sửa) |
| 8 | Nhập mã nhận qua email. |  |
| 9 | Xác nhận mã. |  |
| 10 |  | Kiểm tra mã chưa dùng, chưa hết hạn và chưa vượt giới hạn 5 lần/5 phút. (đã sửa) |
| 11 |  | Mã hợp lệ thì mở form đặt mật khẩu mới, giữ mã trên URL. |
| 12 | Nhập mật khẩu mới. |  |
| 13 | Xác nhận đặt lại. |  |
| 14 |  | Kiểm tra mật khẩu 12–128 ký tự, giới hạn endpoint và consume mã trước khi tìm credential. (đã sửa) |
| 15 |  | Cập nhật password hash và audit; backend thu hồi phiên hiện có như side effect. (đã sửa) |
| 16 |  | Trả thành công và chuyển về trang đăng nhập. |
| 17 |  | Kết thúc UC. |

### Luồng sự kiện thay thế

- **5.1. Email không có tài khoản:** không tạo mã; hệ thống vẫn trả thông báo chung tại bước 7 và tiếp tục bước 8. (đã sửa)
- **8.1.1.** Sau countdown 60 giây, người dùng chọn “Gửi lại mã”. **8.1.2.** UI gọi lại endpoint gửi mã, chịu cùng rate limit; khi API chấp nhận yêu cầu, countdown đặt lại. Mã cũ bị vô hiệu khi có mã mới.
- **10.1. Mã sai hoặc hết hạn:** giao diện báo lỗi; quay lại bước 8 hoặc chọn gửi lại mã.
- **14.1. Mật khẩu mới sai độ dài:** hiển thị lỗi và quay lại bước 12.

### Luồng sự kiện ngoại lệ

- **5.2.** Email sai định dạng hoặc vượt giới hạn gửi mã: API từ chối; giao diện báo lỗi và kết thúc lần gửi hiện tại.
- **6.2.** Dịch vụ email lỗi: backend ghi log nhưng vẫn trả thông báo chung; người dùng có thể không nhận được email.
- **10.2.** Mã không tồn tại, đã dùng hoặc hết hạn: báo lỗi; quay lại bước 8 hoặc nhánh gửi lại.
- **14.2.** Mã hết hạn/đã dùng sau bước xác minh: không cập nhật mật khẩu; bắt đầu lại UC04.
- **14.3.** Không tìm thấy credential theo email trong mã: API từ chối. Mã có thể đã bị consume.
- **7.1.** Lỗi mạng/API/CSDL khi lưu token hoặc cập nhật mật khẩu: hiển thị lỗi nếu API trả lỗi; không báo hoàn tất. Không khẳng định rollback sau khi token đã consume.
- **11.1.** Mở form đặt lại không có token trên URL: UI chuyển về trang khôi phục mật khẩu.
- **13.1.** Rời trang trước khi gửi mật khẩu mới: không gửi yêu cầu đặt lại.

### Giả định / Câu hỏi cần làm rõ
- Backend sinh đúng 6 chữ số, trong khi form nhận token có độ dài tối đa 128 và yêu cầu tối thiểu 6; schema không buộc chỉ gồm chữ số.
- Hạn mã là 1 phút; countdown gửi lại là 60 giây. Rate limit có thể vẫn chặn resend sau khi countdown hết.
- Lỗi gửi email được bắt và ghi log. Không thể kết luận email đã tới người nhận chỉ từ phản hồi chung.
- Token bị đánh dấu đã dùng trước khi cập nhật credential. Nếu bước tiếp theo lỗi, người dùng có thể cần yêu cầu mã mới.

LIFELINE: Người dùng, Giao diện, API khôi phục, Dịch vụ xác thực, Cơ sở dữ liệu, Dịch vụ email.

BẢNG MESSAGE ĐẦY ĐỦ:

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện | [1] chonQuenMatKhau() | đồng bộ | chính |
| 2 | 1-2 | Giao diện | Người dùng | [1-2] hienThiFormEmail() | trả về | chính |
| 3 | 3-4 | Người dùng | Giao diện | [3-4] nhapEmailVaGui(email) | đồng bộ | chính |
| 4 | 5 | Giao diện | API khôi phục | [5] yeuCauGuiMa(email) | đồng bộ | alt [email hợp lệ, trong giới hạn] |
| 5 | 5-6 | API khôi phục | Dịch vụ xác thực | [5-6] xuLyYeuCauKhoiPhuc(email) | đồng bộ | alt [email hợp lệ, trong giới hạn] |
| 6 | 6 | Dịch vụ xác thực | Cơ sở dữ liệu | [6] timTaiKhoanVaLuuMa(email) | đồng bộ | alt [tài khoản tồn tại] |
| 7 | 6 | Cơ sở dữ liệu | Dịch vụ xác thực | [6] traKetQuaTaiKhoanVaMa() | trả về | alt [tài khoản tồn tại] |
| 8 | 6 | Dịch vụ xác thực | Dịch vụ email | [6] guiMaKhoiPhuc(email, ma) | đồng bộ | opt [tài khoản tồn tại] |
| 9 | 6.2 | Dịch vụ email | Dịch vụ xác thực | [6.2] traKetQuaGuiMail() | trả về | opt [mail lỗi thì ghi log và tiếp tục] |
| 10 | 7 | Dịch vụ xác thực | API khôi phục | [7] traPhanHoiChung() | trả về | alt [email có/không có tài khoản] |
| 11 | 7 | API khôi phục | Giao diện | [7] moFormNhapMa() | trả về | alt [email hợp lệ] |
| 12 | 7 | Giao diện | Người dùng | [7] hienThiThongBaoChung() | trả về | alt [email hợp lệ] |
| 13 | 8-9 | Người dùng | Giao diện | [8-9] nhapVaXacNhanMa(ma) | đồng bộ | loop [nhập mã hoặc yêu cầu gửi lại sau countdown] |
| 14 | 10 | Giao diện | API khôi phục | [10] xacMinhMa(ma) | đồng bộ | alt [xác minh mã] |
| 15 | 10 | API khôi phục | Dịch vụ xác thực | [10] kiemTraMaVaHan(ma) | đồng bộ | alt [request không vượt giới hạn] |
| 16 | 10 | Dịch vụ xác thực | Cơ sở dữ liệu | [10] docTrangThaiMa(ma) | đồng bộ | alt [request không vượt giới hạn] |
| 17 | 10 | Cơ sở dữ liệu | Dịch vụ xác thực | [10] traTrangThaiMa() | trả về | alt [request không vượt giới hạn] |
| 18 | 10-11 | Dịch vụ xác thực | API khôi phục | [10-11] traKetQuaXacMinh() | trả về | alt [mã hợp lệ/sai/hết hạn/đã dùng] |
| 19 | 10-11 | API khôi phục | Giao diện | [10-11] traKetQuaMa() | trả về | alt [mã hợp lệ/sai/hết hạn/đã dùng] |
| 20 | 10.1/10.2/11 | Giao diện | Người dùng | [10.1/10.2/11] hienThiLoiHoacFormMatKhau() | trả về | alt [mã không hợp lệ / mã hợp lệ] |
| 21 | 8.1.1-8.1.2 | Giao diện | API khôi phục | [8.1.1-8.1.2] yeuCauGuiLaiMa(email) | đồng bộ | opt [đã hết countdown] |
| 22 | 8.1.2 | API khôi phục | Giao diện | [8.1.2] traKetQuaGuiLai() | trả về | opt [rate limit chấp nhận] |
| 23 | 12-13 | Người dùng | Giao diện | [12-13] nhapVaGuiMatKhauMoi(matKhau) | đồng bộ | alt [đặt lại mật khẩu] |
| 24 | 14 | Giao diện | API khôi phục | [14] datLaiMatKhau(token, matKhau) | đồng bộ | alt [đầu vào hợp lệ] |
| 25 | 14-15 | API khôi phục | Dịch vụ xác thực | [14-15] consumeMaVaCapNhatMatKhau() | đồng bộ | alt [mật khẩu hợp lệ] |
| 26 | 14-15 | Dịch vụ xác thực | Cơ sở dữ liệu | [14-15] consumeMaVaLuuMatKhauMoi() | đồng bộ | alt [mật khẩu hợp lệ] |
| 27 | 14-15 | Cơ sở dữ liệu | Dịch vụ xác thực | [14-15] traKetQuaCapNhat() | trả về | alt [cập nhật thành công/lỗi] |
| 28 | 14.1-14.3 | Dịch vụ xác thực | API khôi phục | [14.1-14.3] traLoiTuChoi() | trả về | alt [mật khẩu sai/mã hết hạn/tài khoản thiếu] |
| 29 | 14.1-14.3 | API khôi phục | Giao diện | [14.1-14.3] hienThiLoiDatLai() | trả về | alt [dữ liệu không hợp lệ hoặc lỗi xử lý] |
| 30 | 15-16 | Dịch vụ xác thực | API khôi phục | [15-16] traDatLaiThanhCong() | trả về | alt [đã lưu mật khẩu mới] |
| 31 | 16 | API khôi phục | Giao diện | [16] chuyenDenDangNhap() | trả về | alt [thành công] |
| 32 | 16 | Giao diện | Người dùng | [16] hienThiTrangDangNhap() | trả về | alt [thành công] |
| 33 | 13.1 | Người dùng | Giao diện | [13.1] roiTrangTruocKhiGui() | đồng bộ | opt [hủy trước khi submit] |
| 34 | 13.1 | Giao diện | Người dùng | [13.1] khongGuiYeuCauDatLai() | trả về | opt [hủy trước khi submit] |

YÊU CẦU: Dùng activation bar, return và alt/opt/loop có guard; giữ thứ tự, mã bước, lifeline và thông báo cuối cho người dùng. Không vẽ quản lý phiên. Không tách Repository hoặc truy vấn nội bộ thành lifeline. Đối chiếu L=6, M=34, F=7; nêu rõ nếu bộ đếm của Visual Paradigm khác bảng.
```

## TỰ KIỂM TRA UC04

- [x] Phần 1 rà lỗi, nhánh, actor, điều kiện, hậu điều kiện và lỗi hệ thống.
- [x] Phần 2 giữ đầy đủ nghiệp vụ, giả định và giới hạn chứng cứ.
- [x] Activity: 15 Action, 4 Decision, 31 cạnh; guard được ghi cho mọi nhánh quyết định.
- [x] Sequence: 6 lifeline, 34 message, 7 fragment; giữ nhánh email, OTP, resend và đặt lại mật khẩu.
- [x] Hai prompt chép đặc tả và bảng tương ứng; diagram không mô hình hóa quản lý phiên.

## Bảng theo dõi sau UC04

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC05 - Quản lý tài khoản

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | Luồng gốc chưa nêu rõ quyền truy cập, tìm kiếm, phân trang và dữ liệu danh sách. | Chốt tác nhân là Admin hệ thống; mô tả danh sách, tìm theo email/họ tên/tên đăng nhập và phân trang giao diện. API còn nhận bộ lọc vai trò/trạng thái, nhưng giao diện tại commit không có bộ lọc tương ứng nên không mô tả thành thao tác UI. |
| 3.1 | THIẾU | Xem chi tiết tài khoản gồm cả thành viên dự án, nhưng kết quả phụ thuộc dịch vụ kiểm thử nội bộ. | Nêu rõ hệ thống lấy chi tiết tài khoản và siêu dữ liệu thành viên dự án; nếu dịch vụ nội bộ lỗi, giao diện báo lỗi tải chi tiết. |
| 5-8 | MƠ HỒ | “Tạo tài khoản và gửi lời mời” không chỉ rõ các trường, kiểm tra trùng hay nội dung email. | Dùng email, họ tên, tên đăng nhập, lý do; kiểm tra schema và trùng email/tên đăng nhập. Mã gọi quy trình xác minh email và đặt mật khẩu; không khẳng định email đã được giao tới hộp thư. |
| 3.3 | THIẾU | Cập nhật hồ sơ cần chỉ rõ trường được sửa và trường lý do bắt buộc. | Giới hạn cập nhật vào họ tên, tên đăng nhập và lý do; nêu phản hồi lỗi khi dữ liệu không hợp lệ hoặc không tìm thấy tài khoản. |
| 3.4 | SAI | “Xóa” có thể bị hiểu là xóa vật lý, trong khi mã nguồn thay thông tin nhận dạng, đánh dấu DELETED và gỡ một số trường cá nhân. | Dùng thuật ngữ “Ẩn danh và vô hiệu hóa tài khoản”; cần email xác nhận và lý do. |
| 3.4.6 | THIẾU | Chưa nêu chặn tự ẩn danh hoặc bảo vệ Admin hoạt động cuối cùng. | Thêm nhánh từ chối nếu tự thao tác hoặc kết quả làm mất Admin hoạt động cuối cùng, theo guard phía repository. |
| Hủy | THIẾU | Chưa mô tả hủy hộp thoại tạo/sửa/xóa trước khi gửi. | Nêu việc đóng hộp thoại trước xác nhận không gửi yêu cầu và không thay đổi dữ liệu. |
| Ngoại lệ | THIẾU | Thiếu token hết hạn/không đủ quyền, tài khoản không tồn tại, lỗi CSDL/API và lỗi dịch vụ email. | Bổ sung nhánh 401/403, 404, lỗi xử lý; lỗi gửi email được ghi log và không chứng minh thư đã tới nơi. |
| Hậu điều kiện | MƠ HỒ | “Danh sách hoặc thông tin được cập nhật” chưa phân biệt thành công, thất bại và ẩn danh. | Tách hậu điều kiện theo xem/tìm, tạo, sửa, ẩn danh và thất bại; ghi rõ thao tác ẩn danh không xóa lịch sử nghiệp vụ bằng UC này. |
| Quản lý/CRUD | THIẾU | Luồng gốc chưa tổ chức danh sách/tìm kiếm, xem chi tiết, thêm, sửa, xóa theo các nhánh nhất quán. | Bổ sung đủ các thao tác quản lý có căn cứ. “Xóa” được diễn đạt là ẩn danh, không hard-delete. Không thêm bộ lọc UI chưa có. |
| Tác nhân/phiên | Đã kiểm | Admin hệ thống bị bảo vệ bởi dependency quản trị. Việc ẩn danh thu hồi credential hiện hữu là side effect. | Không tạo UC quản lý phiên; chỉ ghi tác động thu hồi truy cập như kết quả phụ khi ẩn danh. |

Đã kiểm: **6 điểm rẽ nghiệp vụ, 8 nhánh và 8 nhóm lỗi** (dữ liệu sai/thiếu, trùng email hoặc tên đăng nhập, không đủ quyền/hết xác thực, không tìm thấy, Admin tự thao tác/loại bỏ Admin cuối, lỗi API/CSDL, dịch vụ email và hủy hộp thoại). CRUD được rà theo các thao tác thực tế; bộ lọc chỉ ghi nhận ở API, không giả làm chức năng giao diện.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Admin hệ thống có thể xem danh sách và chi tiết tài khoản, tìm kiếm, tạo tài khoản, sửa hồ sơ cơ bản hoặc ẩn danh một tài khoản. Việc khóa, kích hoạt, thay đổi vai trò hệ thống và yêu cầu đặt lại mật khẩu được mô tả ở UC06, UC07 hoặc luồng tương ứng, không gộp vào UC05.

### Tiền điều kiện
- Admin hệ thống đã đăng nhập, credential còn hiệu lực và có quyền quản trị nền tảng.
- Tài khoản đích phải tồn tại đối với thao tác xem/sửa/ẩn danh.
- Tạo tài khoản không đòi hỏi tài khoản đích có trước.

### Hậu điều kiện
- Xem/tìm kiếm: danh sách hoặc chi tiết được hiển thị; dữ liệu không bị thay đổi.
- Tạo: tài khoản USER được tạo ở trạng thái hoạt động nhưng chưa xác minh email; hệ thống khởi tạo quy trình xác minh và đặt mật khẩu. Không khẳng định email đã tới người nhận.
- Sửa: họ tên và/hoặc tên đăng nhập được cập nhật; giao diện tải lại danh sách/chi tiết.
- Ẩn danh: thông tin nhận dạng được thay bằng giá trị ẩn danh, tài khoản chuyển trạng thái DELETED, một số trường cá nhân bị gỡ và truy cập hiện hữu bị thu hồi. Thao tác không xóa lịch sử nghiệp vụ liên quan.
- Thất bại/hủy: lỗi được hiển thị; thao tác chưa gửi hoặc bị từ chối không được xem là thành công. Nếu lỗi xảy ra giữa nhiều lần ghi, tính nguyên tử không được khẳng định ngoài những giao dịch mà mã nguồn bảo đảm.

### Tác nhân chính
Admin hệ thống.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu xác minh/thiết lập thông tin truy cập. Dịch vụ kiểm thử nội bộ cung cấp siêu dữ liệu thành viên dự án khi xem chi tiết tài khoản.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang quản lý tài khoản. | |
| 2 | | Kiểm tra quyền quản trị; tải và hiển thị danh sách tài khoản gồm email, họ tên, vai trò hệ thống và trạng thái. |
| 3 | Chọn một thao tác: tìm kiếm, xem chi tiết, tạo, sửa hồ sơ hoặc ẩn danh. | |
| 4 | | Thực hiện nhánh tương ứng trong luồng thay thế; sau thay đổi thành công, tải lại dữ liệu liên quan. |
| 5 | | Kết thúc UC khi kết quả được hiển thị. |

### Luồng sự kiện thay thế

**3.1. Tìm kiếm tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Nhập email, họ tên hoặc tên đăng nhập rồi gửi tìm kiếm. | |
| 3.1.2 | | Tìm theo từ khóa không phân biệt hoa thường và hiển thị danh sách khớp; giao diện phân trang cục bộ. |
| 3.1.3 | Chọn tài khoản cần xem hoặc tiếp tục tìm. | |
| 3.1.4 | | Nếu chọn tài khoản, chuyển sang bước 3.2.2; nếu tìm tiếp, quay lại 3.1.1. |

**3.2. Xem chi tiết và thành viên dự án**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.1 | Chọn một tài khoản trong danh sách. | |
| 3.2.2 | | Tải hồ sơ chi tiết và danh sách thành viên dự án từ dịch vụ kiểm thử nội bộ. |
| 3.2.3 | | Hiển thị email, họ tên, vai trò hệ thống, trạng thái và dữ liệu thành viên dự án. |
| 3.2.4 | | Kết thúc nhánh xem. |

**3.3. Tạo tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.1 | Chọn “Tạo tài khoản”. | |
| 3.3.2 | | Hiển thị form email, họ tên, tên đăng nhập và lý do. |
| 3.3.3 | Nhập dữ liệu và chọn “Tạo và gửi lời mời”. | |
| 3.3.4 | | Kiểm tra schema, quyền tạo và trùng email/tên đăng nhập. |
| 3.3.5 | | Tạo tài khoản USER, khởi tạo xác minh email và quy trình đặt mật khẩu. |
| 3.3.6 | | Hiển thị tài khoản vừa tạo trong danh sách và thông báo kết quả. |
| 3.3.7 | | Kết thúc nhánh tạo. |

**3.4. Sửa hồ sơ tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.4.1 | Chọn “Sửa hồ sơ” ở chi tiết tài khoản. | |
| 3.4.2 | | Hiển thị họ tên, tên đăng nhập và trường lý do. |
| 3.4.3 | Sửa thông tin và gửi lưu. | |
| 3.4.4 | | Kiểm tra schema, tìm tài khoản đích và cập nhật hồ sơ/audit. |
| 3.4.5 | | Tải lại danh sách/chi tiết và thông báo thành công. |
| 3.4.6 | | Kết thúc nhánh sửa. |

**3.5. Ẩn danh tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.5.1 | Chọn “Xóa và ẩn danh tài khoản”. | |
| 3.5.2 | | Hiển thị yêu cầu nhập chính xác email tài khoản và lý do. |
| 3.5.3 | Nhập email xác nhận, lý do và xác nhận thao tác. | |
| 3.5.4 | | Kiểm tra email xác nhận, quyền, tài khoản đích và quy tắc bảo vệ Admin hoạt động cuối cùng. |
| 3.5.5 | | Ẩn danh hồ sơ, đánh dấu DELETED, gỡ thông tin cá nhân được chỉ định, thu hồi credential truy cập và ghi audit. |
| 3.5.6 | | Đóng chi tiết, tải lại danh sách và thông báo thành công. |
| 3.5.7 | | Kết thúc nhánh ẩn danh. |

### Luồng sự kiện ngoại lệ

- **3.3.4.1.** Email hoặc tên đăng nhập đã tồn tại: từ chối tạo và báo lỗi; quay lại bước 3.3.3.
- **3.3.4.2.** Email, họ tên, slug hoặc lý do không đạt schema: báo lỗi xác thực; quay lại bước 3.3.3.
- **3.4.4.1.** Họ tên/tên đăng nhập không hợp lệ hoặc payload không có trường cập nhật: báo lỗi; quay lại bước 3.4.3. Mã nguồn hiện không có kiểm tra slug trùng riêng trong `update_profile`; hành vi khi vi phạm chỉ mục duy nhất phụ thuộc lỗi lưu trữ.
- **3.2.2.1.** Tài khoản không tìm thấy: báo không tìm thấy và kết thúc nhánh thất bại.
- **3.4.4.2/3.5.4.1.** Tài khoản không tìm thấy trong thao tác cập nhật/ẩn danh: API trả lỗi; không báo thành công.
- **3.5.4.2.** Email xác nhận không khớp: từ chối ẩn danh; quay lại bước 3.5.3.
- **3.5.4.3.** Admin tự ẩn danh hoặc thao tác làm giảm số Admin hoạt động xuống dưới một: từ chối và giữ nguyên dữ liệu.
- **2/3.2.2.** Hết credential hoặc không đủ quyền: trả lỗi xác thực/phân quyền; dừng thao tác, dữ liệu không được xác nhận đã đổi.
- **3.3.5.** Dịch vụ email lỗi: backend ghi log và vẫn có thể trả kết quả tạo tài khoản; không thể kết luận người nhận đã nhận thư. Người dùng quản trị có thể cần dùng lại quy trình gửi hướng dẫn ở UC06.
- **2/3.2/3.3/3.4/3.5.** Lỗi API/CSDL hoặc dịch vụ kiểm thử nội bộ: giao diện hiển thị lỗi tương ứng; không suy diễn rằng mọi thao tác nhiều bước đã rollback.
- **3.3.3/3.4.3/3.5.3.** Admin đóng hộp thoại trước khi gửi: không phát sinh thay đổi dữ liệu.

### Giả định / Câu hỏi cần làm rõ
- API danh sách nhận tham số lọc vai trò và trạng thái, nhưng giao diện `PlatformUsersPanel` tại commit chỉ hiển thị tìm kiếm và phân trang cục bộ. Cần xác nhận có nên bổ sung bộ lọc ở UI; đặc tả hiện không coi đó là chức năng đã cung cấp.
- Tạo tài khoản gọi cả luồng xác minh email và quy trình đặt mật khẩu. Mã nguồn bắt lỗi gửi email, nên “gửi lời mời” chỉ có thể khẳng định là hệ thống đã khởi tạo yêu cầu gửi.
- `update_profile` không kiểm tra slug trùng một cách tường minh. Không giả định thông báo lỗi thân thiện cho trường hợp này nếu chưa kiểm tra chỉ mục và bộ xử lý exception ở môi trường chạy.
- Dịch vụ kiểm thử nội bộ trả metadata thành viên dự án; nếu nghiệp vụ khóa luận không cần nội dung này, có thể tách khỏi chi tiết UC05 theo quyết định của người hướng dẫn.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức nghiệp vụ khóa luận)

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Hệ thống | Bắt đầu; tiền điều kiện: Admin có quyền quản trị nền tảng |
| A1 | 1-2 | Action | Admin | [1-2] Mở trang và xem danh sách tài khoản |
| D0 | 2 | Decision | Hệ thống | [2] Danh sách tải thành công? |
| D1 | 3 | Decision | Admin | [3] Chọn thao tác nào? |
| A2 | 3.1.1-3.1.2 | Action | Admin / Hệ thống | [3.1.1-3.1.2] Tìm tài khoản theo từ khóa |
| D2 | 3.1.2 | Decision | Hệ thống | [3.1.2] Tìm kiếm thành công và có kết quả? |
| A3 | 3.1.2 | Action | Hệ thống | [3.1.2] Hiển thị danh sách rỗng |
| A4 | 3.2.1-3.2.3 | Action | Admin / Hệ thống | [3.2.1-3.2.3] Xem chi tiết và thành viên dự án |
| D6 | 3.2.3 | Decision | Admin | [3.2.3] Chỉ xem, sửa hồ sơ hay ẩn danh? |
| A5 | 3.3.1-3.3.3 | Action | Admin | [3.3.1-3.3.3] Nhập và gửi form tạo tài khoản |
| D3 | 3.3.4 | Decision | Hệ thống | [3.3.4] Dữ liệu hợp lệ và không trùng? |
| A6 | 3.3.5 | Action | Hệ thống | [3.3.5] Tạo tài khoản và khởi tạo gửi hướng dẫn |
| A7 | 3.4.1-3.4.3 | Action | Admin | [3.4.1-3.4.3] Sửa hồ sơ và gửi lưu |
| D4 | 3.4.4 | Decision | Hệ thống | [3.4.4] Hồ sơ hợp lệ và tài khoản còn tồn tại? |
| A8 | 3.4.4 | Action | Hệ thống | [3.4.4] Cập nhật hồ sơ tài khoản |
| A9 | 3.5.1-3.5.3 | Action | Admin | [3.5.1-3.5.3] Xác nhận email và lý do ẩn danh |
| D5 | 3.5.4 | Decision | Hệ thống | [3.5.4] Xác nhận và điều kiện Admin hợp lệ? |
| A10 | 3.5.5 | Action | Hệ thống | [3.5.5] Ẩn danh và vô hiệu hóa tài khoản |
| A11 | 3.3.4.1/3.4.4.1/3.5.4 | Action | Hệ thống | [3.3.4.1/3.4.4.1/3.5.4] Báo lỗi dữ liệu hoặc từ chối thao tác |
| D8 | 3.3.4.1/3.4.4.1/3.5.4 | Decision | Admin | [3.3.4.1/3.4.4.1/3.5.4] Sửa lại hay dừng? |
| A12 | 2/3.2.2/3.3.5/3.4.4/3.5.5 | Action | Hệ thống | [2/3.2.2/3.3.5/3.4.4/3.5.5] Báo lỗi quyền, tải dữ liệu hoặc xử lý |
| A13 | 3.3.6/3.4.5/3.5.6 | Action | Hệ thống | [3.3.6/3.4.5/3.5.6] Tải lại dữ liệu và thông báo kết quả |
| D7 | 3.2-3.5 | Decision | Hệ thống | [3.2-3.5] Tải chi tiết/thao tác thành công? |
| F1 | 3.2/3.3.7/3.4.6/3.5.7 | Final | Hệ thống | Kết thúc sau thao tác thành công hoặc xem |
| F2 | 2/3.2/3.3/3.4/3.5 | Final | Hệ thống | Kết thúc thất bại; không xác nhận thay đổi |
| F3 | 3.3/3.4/3.5 | Final | Admin | Kết thúc do hủy trước khi gửi |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | D0 | Danh sách được yêu cầu |
| D0 | D1 | [Tải thành công] |
| D0 | A12 | [Lỗi quyền/API/CSDL] |
| D1 | A2 | [Tìm kiếm] |
| D1 | A4 | [Xem tài khoản] |
| D1 | A5 | [Tạo tài khoản] |
| D1 | F3 | [Hủy trước khi gửi] |
| A2 | D2 | Đã gửi từ khóa |
| D2 | A4 | [Có kết quả và chọn tài khoản] |
| D2 | A3 | [Không có kết quả] |
| D2 | A12 | [Lỗi tìm kiếm] |
| A3 | A2 | [Sửa từ khóa] |
| A4 | D7 | Đã yêu cầu chi tiết và thành viên dự án |
| D7 | D6 | [Chi tiết tải thành công] |
| D7 | A12 | [Lỗi tải chi tiết] |
| D6 | F1 | [Chỉ xem] |
| D6 | A7 | [Sửa hồ sơ] |
| D6 | A9 | [Ẩn danh] |
| A5 | D3 | Đã gửi form tạo |
| D3 | A6 | [Hợp lệ, chưa trùng] |
| D3 | A11 | [Thiếu/sai dữ liệu hoặc trùng] |
| A6 | D7 | Đã xử lý yêu cầu tạo |
| A7 | D4 | Đã gửi form sửa |
| D4 | A8 | [Tài khoản tồn tại, schema hợp lệ] |
| D4 | A11 | [Không tồn tại hoặc dữ liệu sai] |
| A8 | D7 | Đã xử lý yêu cầu sửa |
| A9 | D5 | Đã gửi email xác nhận và lý do |
| D5 | A10 | [Email khớp, không tự ẩn danh, còn Admin hoạt động] |
| D5 | A11 | [Email sai hoặc vi phạm bảo vệ Admin] |
| A10 | D7 | Đã xử lý yêu cầu ẩn danh |
| A11 | D8 | Lỗi nghiệp vụ đã hiển thị |
| D8 | A5 | [Sửa lại dữ liệu tạo] |
| D8 | A7 | [Sửa lại hồ sơ] |
| D8 | A9 | [Sửa lại yêu cầu ẩn danh] |
| D8 | F2 | [Dừng thao tác] |
| D7 | A13 | [Thao tác ghi thành công] |
| D7 | F1 | [Đã xem chi tiết, không thay đổi dữ liệu] |
| D7 | A12 | [Lỗi API/CSDL/dịch vụ nội bộ] |
| A12 | F2 | Không thể tiếp tục |
| A13 | F1 | Kết quả đã hiển thị |

### 3c. Số liệu

N = 15 nhóm tương tác/ô nghiệp vụ được mô hình hóa; M = 13 Action; D = 9 Decision; E = 41 cạnh. Các action đại diện tương tác nghiệp vụ liền nhau, không truy vấn nội bộ lặp lại.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức nghiệp vụ khóa luận)

### 4a. Lifeline trái sang phải

Admin → Giao diện quản trị → Backend quản trị (API và dịch vụ tài khoản) → Cơ sở dữ liệu → Dịch vụ kiểm thử nội bộ → Dịch vụ email. Gộp API và service vào một lifeline để giữ Sequence ở mức kiến trúc nghiệp vụ; hai dịch vụ phụ chỉ tham gia khi xem thành viên dự án hoặc tạo tài khoản.

### 4b. Bảng message theo thời gian

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Admin | Giao diện quản trị | [1] moQuanLyTaiKhoan() | đồng bộ | chính |
| 2 | 2 | Giao diện quản trị | Backend quản trị | [2] layDanhSachTaiKhoan() | đồng bộ | chính |
| 3 | 2 | Backend quản trị | Cơ sở dữ liệu | [2] timTaiKhoan(search, limit) | đồng bộ | chính |
| 4 | 2 | Cơ sở dữ liệu | Backend quản trị | [2] traDanhSach() | trả về | chính |
| 5 | 2 | Backend quản trị | Giao diện quản trị | [2] traDanhSachTaiKhoan() | trả về | chính |
| 6 | 2 | Giao diện quản trị | Admin | [2] hienThiDanhSach() | trả về | chính |
| 7 | 3.1 | Admin | Giao diện quản trị | [3.1] timTheoTuKhoa(search) | đồng bộ | alt [tìm kiếm] |
| 8 | 3.1 | Giao diện quản trị | Backend quản trị | [3.1] timTaiKhoan(search) | đồng bộ | alt [tìm kiếm] |
| 9 | 3.1 | Backend quản trị | Cơ sở dữ liệu | [3.1] truyVanDanhSach(search) | đồng bộ | alt [tìm kiếm] |
| 10 | 3.1 | Cơ sở dữ liệu | Backend quản trị | [3.1] traKetQuaTimKiem() | trả về | alt [tìm kiếm] |
| 11 | 3.1 | Backend quản trị | Giao diện quản trị | [3.1] traDanhSachKetQua() | trả về | alt [tìm kiếm] |
| 12 | 3.1 | Giao diện quản trị | Admin | [3.1] hienThiKetQua() | trả về | alt [tìm kiếm] |
| 13 | 3.2 | Admin | Giao diện quản trị | [3.2] chonTaiKhoan() | đồng bộ | alt [xem chi tiết] |
| 14 | 3.2 | Giao diện quản trị | Backend quản trị | [3.2] layChiTietVaThanhVien(userId) | đồng bộ | alt [xem chi tiết] |
| 15 | 3.2 | Backend quản trị | Cơ sở dữ liệu | [3.2] docChiTietTaiKhoan(userId) | đồng bộ | alt [xem chi tiết] |
| 16 | 3.2 | Cơ sở dữ liệu | Backend quản trị | [3.2] traChiTietTaiKhoan() | trả về | alt [xem chi tiết] |
| 17 | 3.2 | Backend quản trị | Dịch vụ kiểm thử nội bộ | [3.2] layThanhVienDuAn(userId) | đồng bộ | alt [xem chi tiết] |
| 18 | 3.2 | Dịch vụ kiểm thử nội bộ | Backend quản trị | [3.2] traThanhVienDuAn() | trả về | alt [xem chi tiết] |
| 19 | 3.2 | Backend quản trị | Giao diện quản trị | [3.2] traChiTietVaThanhVien() | trả về | alt [xem chi tiết] |
| 20 | 3.2 | Giao diện quản trị | Admin | [3.2] hienThiChiTiet() | trả về | alt [xem chi tiết] |
| 21 | 3.3 | Admin | Giao diện quản trị | [3.3] guiFormTao(email, fullName, slug, reason) | đồng bộ | alt [tạo] |
| 22 | 3.3 | Giao diện quản trị | Backend quản trị | [3.3] taoTaiKhoan(payload) | đồng bộ | alt [tạo] |
| 23 | 3.3 | Backend quản trị | Cơ sở dữ liệu | [3.3] taoTaiKhoanVaAudit(payload) | đồng bộ | alt [dữ liệu hợp lệ, chưa trùng] |
| 24 | 3.3 | Cơ sở dữ liệu | Backend quản trị | [3.3] traTaiKhoanMoi() | trả về | alt [tạo thành công] |
| 25 | 3.3 | Backend quản trị | Dịch vụ email | [3.3] khoiTaoXacMinhVaDatMatKhau(email) | đồng bộ | alt [tạo thành công] |
| 26 | 3.3 | Dịch vụ email | Backend quản trị | [3.3] traTrangThaiGui() | trả về | alt [thành công hoặc lỗi được bắt] |
| 27 | 3.3 | Backend quản trị | Giao diện quản trị | [3.3] traKetQuaTao() | trả về | alt [tạo thành công] |
| 28 | 3.3 | Giao diện quản trị | Admin | [3.3] hienThiTaiKhoanMoi() | trả về | alt [tạo thành công] |
| 29 | 3.4 | Admin | Giao diện quản trị | [3.4] guiCapNhatHoSo(userId, fullName, slug, reason) | đồng bộ | alt [sửa hồ sơ] |
| 30 | 3.4 | Giao diện quản trị | Backend quản trị | [3.4] capNhatHoSo(userId, payload) | đồng bộ | alt [sửa hồ sơ] |
| 31 | 3.4 | Backend quản trị | Cơ sở dữ liệu | [3.4] luuHoSoVaAudit(userId, payload) | đồng bộ | alt [tài khoản tồn tại] |
| 32 | 3.4 | Cơ sở dữ liệu | Backend quản trị | [3.4] traKetQuaCapNhat() | trả về | alt [thành công/lỗi] |
| 33 | 3.4 | Backend quản trị | Giao diện quản trị | [3.4] traKetQuaHoSo() | trả về | alt [thành công/lỗi] |
| 34 | 3.4 | Giao diện quản trị | Admin | [3.4] hienThiHoSoMoiHoacLoi() | trả về | alt [thành công/lỗi] |
| 35 | 3.5 | Admin | Giao diện quản trị | [3.5] xacNhanAnDanh(userId, email, reason) | đồng bộ | alt [ẩn danh] |
| 36 | 3.5 | Giao diện quản trị | Backend quản trị | [3.5] anDanhTaiKhoan(userId, confirmation, reason) | đồng bộ | alt [ẩn danh] |
| 37 | 3.5 | Backend quản trị | Cơ sở dữ liệu | [3.5] anDanhVaThuHoiTruyCap(userId) | đồng bộ | alt [email khớp, còn Admin hoạt động] |
| 38 | 3.5 | Cơ sở dữ liệu | Backend quản trị | [3.5] traKetQuaAnDanh() | trả về | alt [thành công/lỗi] |
| 39 | 3.5 | Backend quản trị | Giao diện quản trị | [3.5] traKetQuaAnDanh() | trả về | alt [thành công/lỗi] |
| 40 | 3.5 | Giao diện quản trị | Admin | [3.5] dongChiTietVaTaiLaiDanhSach() | trả về | alt [thành công/lỗi] |
| 41 | 3.3.4.1/3.4.4.1/3.5.4 | Backend quản trị | Giao diện quản trị | [3.3.4.1/3.4.4.1/3.5.4] traLoiLoiNghiepVuHoacHaTang() | trả về | alt [lỗi validation/trùng/không tìm thấy/lỗi hệ thống] |
| 42 | 3.3.4.1/3.4.4.1/3.5.4 | Giao diện quản trị | Admin | [3.3.4.1/3.4.4.1/3.5.4] hienThiLoi() | trả về | alt [lỗi] |
| 43 | 3.3/3.4/3.5 | Admin | Giao diện quản trị | [3.3/3.4/3.5] huyHopThoaiTruocKhiGui() | đồng bộ | opt [hủy trước submit] |
| 44 | 3.3/3.4/3.5 | Giao diện quản trị | Admin | [3.3/3.4/3.5] dongHopThoaiKhongThayDoi() | trả về | opt [hủy trước submit] |

### 4c. Số liệu

N = 15 nhóm tương tác nghiệp vụ; M = 44 message; F = 7 fragment (alt tìm kiếm, alt chi tiết, alt tạo, alt sửa, alt ẩn danh, alt lỗi, opt hủy); L = 6 lifeline. Không tách lời gọi lặp lại giữa các lớp nội bộ.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC05 - Quản lý tài khoản của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt. Mức chi tiết phù hợp khóa luận.

ĐẶC TẢ ĐẦY ĐỦ:

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Admin hệ thống có thể xem danh sách và chi tiết tài khoản, tìm kiếm, tạo tài khoản, sửa hồ sơ cơ bản hoặc ẩn danh một tài khoản. Việc khóa, kích hoạt, thay đổi vai trò hệ thống và yêu cầu đặt lại mật khẩu được mô tả ở UC06, UC07 hoặc luồng tương ứng, không gộp vào UC05.

### Tiền điều kiện
- Admin hệ thống đã đăng nhập, credential còn hiệu lực và có quyền quản trị nền tảng.
- Tài khoản đích phải tồn tại đối với thao tác xem/sửa/ẩn danh.
- Tạo tài khoản không đòi hỏi tài khoản đích có trước.

### Hậu điều kiện
- Xem/tìm kiếm: danh sách hoặc chi tiết được hiển thị; dữ liệu không bị thay đổi.
- Tạo: tài khoản USER được tạo ở trạng thái hoạt động nhưng chưa xác minh email; hệ thống khởi tạo quy trình xác minh và đặt mật khẩu. Không khẳng định email đã tới người nhận.
- Sửa: họ tên và/hoặc tên đăng nhập được cập nhật; giao diện tải lại danh sách/chi tiết.
- Ẩn danh: thông tin nhận dạng được thay bằng giá trị ẩn danh, tài khoản chuyển trạng thái DELETED, một số trường cá nhân bị gỡ và truy cập hiện hữu bị thu hồi. Thao tác không xóa lịch sử nghiệp vụ liên quan.
- Thất bại/hủy: lỗi được hiển thị; thao tác chưa gửi hoặc bị từ chối không được xem là thành công. Nếu lỗi xảy ra giữa nhiều lần ghi, tính nguyên tử không được khẳng định ngoài những giao dịch mà mã nguồn bảo đảm.

### Tác nhân chính
Admin hệ thống.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu xác minh/thiết lập thông tin truy cập. Dịch vụ kiểm thử nội bộ cung cấp siêu dữ liệu thành viên dự án khi xem chi tiết tài khoản.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang quản lý tài khoản. | |
| 2 | | Kiểm tra quyền quản trị; tải và hiển thị danh sách tài khoản gồm email, họ tên, vai trò hệ thống và trạng thái. |
| 3 | Chọn một thao tác: tìm kiếm, xem chi tiết, tạo, sửa hồ sơ hoặc ẩn danh. | |
| 4 | | Thực hiện nhánh tương ứng trong luồng thay thế; sau thay đổi thành công, tải lại dữ liệu liên quan. |
| 5 | | Kết thúc UC khi kết quả được hiển thị. |

### Luồng sự kiện thay thế

**3.1. Tìm kiếm tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Nhập email, họ tên hoặc tên đăng nhập rồi gửi tìm kiếm. | |
| 3.1.2 | | Tìm theo từ khóa không phân biệt hoa thường và hiển thị danh sách khớp; giao diện phân trang cục bộ. |
| 3.1.3 | Chọn tài khoản cần xem hoặc tiếp tục tìm. | |
| 3.1.4 | | Nếu chọn tài khoản, chuyển sang bước 3.2.2; nếu tìm tiếp, quay lại 3.1.1. |

**3.2. Xem chi tiết và thành viên dự án**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.1 | Chọn một tài khoản trong danh sách. | |
| 3.2.2 | | Tải hồ sơ chi tiết và danh sách thành viên dự án từ dịch vụ kiểm thử nội bộ. |
| 3.2.3 | | Hiển thị email, họ tên, vai trò hệ thống, trạng thái và dữ liệu thành viên dự án. |
| 3.2.4 | | Kết thúc nhánh xem. |

**3.3. Tạo tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.1 | Chọn “Tạo tài khoản”. | |
| 3.3.2 | | Hiển thị form email, họ tên, tên đăng nhập và lý do. |
| 3.3.3 | Nhập dữ liệu và chọn “Tạo và gửi lời mời”. | |
| 3.3.4 | | Kiểm tra schema, quyền tạo và trùng email/tên đăng nhập. |
| 3.3.5 | | Tạo tài khoản USER, khởi tạo xác minh email và quy trình đặt mật khẩu. |
| 3.3.6 | | Hiển thị tài khoản vừa tạo trong danh sách và thông báo kết quả. |
| 3.3.7 | | Kết thúc nhánh tạo. |

**3.4. Sửa hồ sơ tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.4.1 | Chọn “Sửa hồ sơ” ở chi tiết tài khoản. | |
| 3.4.2 | | Hiển thị họ tên, tên đăng nhập và trường lý do. |
| 3.4.3 | Sửa thông tin và gửi lưu. | |
| 3.4.4 | | Kiểm tra schema, tìm tài khoản đích và cập nhật hồ sơ/audit. |
| 3.4.5 | | Tải lại danh sách/chi tiết và thông báo thành công. |
| 3.4.6 | | Kết thúc nhánh sửa. |

**3.5. Ẩn danh tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.5.1 | Chọn “Xóa và ẩn danh tài khoản”. | |
| 3.5.2 | | Hiển thị yêu cầu nhập chính xác email tài khoản và lý do. |
| 3.5.3 | Nhập email xác nhận, lý do và xác nhận thao tác. | |
| 3.5.4 | | Kiểm tra email xác nhận, quyền, tài khoản đích và quy tắc bảo vệ Admin hoạt động cuối cùng. |
| 3.5.5 | | Ẩn danh hồ sơ, đánh dấu DELETED, gỡ thông tin cá nhân được chỉ định, thu hồi credential truy cập và ghi audit. |
| 3.5.6 | | Đóng chi tiết, tải lại danh sách và thông báo thành công. |
| 3.5.7 | | Kết thúc nhánh ẩn danh. |

### Luồng sự kiện ngoại lệ

- **3.3.4.1.** Email hoặc tên đăng nhập đã tồn tại: từ chối tạo và báo lỗi; quay lại bước 3.3.3.
- **3.3.4.2.** Email, họ tên, slug hoặc lý do không đạt schema: báo lỗi xác thực; quay lại bước 3.3.3.
- **3.4.4.1.** Họ tên/tên đăng nhập không hợp lệ hoặc payload không có trường cập nhật: báo lỗi; quay lại bước 3.4.3. Mã nguồn hiện không có kiểm tra slug trùng riêng trong `update_profile`; hành vi khi vi phạm chỉ mục duy nhất phụ thuộc lỗi lưu trữ.
- **3.2.2.1.** Tài khoản không tìm thấy: báo không tìm thấy và kết thúc nhánh thất bại.
- **3.4.4.2/3.5.4.1.** Tài khoản không tìm thấy trong thao tác cập nhật/ẩn danh: API trả lỗi; không báo thành công.
- **3.5.4.2.** Email xác nhận không khớp: từ chối ẩn danh; quay lại bước 3.5.3.
- **3.5.4.3.** Admin tự ẩn danh hoặc thao tác làm giảm số Admin hoạt động xuống dưới một: từ chối và giữ nguyên dữ liệu.
- **2/3.2.2.** Hết credential hoặc không đủ quyền: trả lỗi xác thực/phân quyền; dừng thao tác, dữ liệu không được xác nhận đã đổi.
- **3.3.5.** Dịch vụ email lỗi: backend ghi log và vẫn có thể trả kết quả tạo tài khoản; không thể kết luận người nhận đã nhận thư. Người dùng quản trị có thể cần dùng lại quy trình gửi hướng dẫn ở UC06.
- **2/3.2/3.3/3.4/3.5.** Lỗi API/CSDL hoặc dịch vụ kiểm thử nội bộ: giao diện hiển thị lỗi tương ứng; không suy diễn rằng mọi thao tác nhiều bước đã rollback.
- **3.3.3/3.4.3/3.5.3.** Admin đóng hộp thoại trước khi gửi: không phát sinh thay đổi dữ liệu.

### Giả định / Câu hỏi cần làm rõ
- API danh sách nhận tham số lọc vai trò và trạng thái, nhưng giao diện `PlatformUsersPanel` tại commit chỉ hiển thị tìm kiếm và phân trang cục bộ. Cần xác nhận có nên bổ sung bộ lọc ở UI; đặc tả hiện không coi đó là chức năng đã cung cấp.
- Tạo tài khoản gọi cả luồng xác minh email và quy trình đặt mật khẩu. Mã nguồn bắt lỗi gửi email, nên “gửi lời mời” chỉ có thể khẳng định là hệ thống đã khởi tạo yêu cầu gửi.
- `update_profile` không kiểm tra slug trùng một cách tường minh. Không giả định thông báo lỗi thân thiện cho trường hợp này nếu chưa kiểm tra chỉ mục và bộ xử lý exception ở môi trường chạy.
- Dịch vụ kiểm thử nội bộ trả metadata thành viên dự án; nếu nghiệp vụ khóa luận không cần nội dung này, có thể tách khỏi chi tiết UC05 theo quyết định của người hướng dẫn.

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Hệ thống | Bắt đầu; tiền điều kiện: Admin có quyền quản trị nền tảng |
| A1 | 1-2 | Action | Admin | [1-2] Mở trang và xem danh sách tài khoản |
| D0 | 2 | Decision | Hệ thống | [2] Danh sách tải thành công? |
| D1 | 3 | Decision | Admin | [3] Chọn thao tác nào? |
| A2 | 3.1.1-3.1.2 | Action | Admin / Hệ thống | [3.1.1-3.1.2] Tìm tài khoản theo từ khóa |
| D2 | 3.1.2 | Decision | Hệ thống | [3.1.2] Tìm kiếm thành công và có kết quả? |
| A3 | 3.1.2 | Action | Hệ thống | [3.1.2] Hiển thị danh sách rỗng |
| A4 | 3.2.1-3.2.3 | Action | Admin / Hệ thống | [3.2.1-3.2.3] Xem chi tiết và thành viên dự án |
| D6 | 3.2.3 | Decision | Admin | [3.2.3] Chỉ xem, sửa hồ sơ hay ẩn danh? |
| A5 | 3.3.1-3.3.3 | Action | Admin | [3.3.1-3.3.3] Nhập và gửi form tạo tài khoản |
| D3 | 3.3.4 | Decision | Hệ thống | [3.3.4] Dữ liệu hợp lệ và không trùng? |
| A6 | 3.3.5 | Action | Hệ thống | [3.3.5] Tạo tài khoản và khởi tạo gửi hướng dẫn |
| A7 | 3.4.1-3.4.3 | Action | Admin | [3.4.1-3.4.3] Sửa hồ sơ và gửi lưu |
| D4 | 3.4.4 | Decision | Hệ thống | [3.4.4] Hồ sơ hợp lệ và tài khoản còn tồn tại? |
| A8 | 3.4.4 | Action | Hệ thống | [3.4.4] Cập nhật hồ sơ tài khoản |
| A9 | 3.5.1-3.5.3 | Action | Admin | [3.5.1-3.5.3] Xác nhận email và lý do ẩn danh |
| D5 | 3.5.4 | Decision | Hệ thống | [3.5.4] Xác nhận và điều kiện Admin hợp lệ? |
| A10 | 3.5.5 | Action | Hệ thống | [3.5.5] Ẩn danh và vô hiệu hóa tài khoản |
| A11 | 3.3.4.1/3.4.4.1/3.5.4 | Action | Hệ thống | [3.3.4.1/3.4.4.1/3.5.4] Báo lỗi dữ liệu hoặc từ chối thao tác |
| D8 | 3.3.4.1/3.4.4.1/3.5.4 | Decision | Admin | [3.3.4.1/3.4.4.1/3.5.4] Sửa lại hay dừng? |
| A12 | 2/3.2.2/3.3.5/3.4.4/3.5.5 | Action | Hệ thống | [2/3.2.2/3.3.5/3.4.4/3.5.5] Báo lỗi quyền, tải dữ liệu hoặc xử lý |
| A13 | 3.3.6/3.4.5/3.5.6 | Action | Hệ thống | [3.3.6/3.4.5/3.5.6] Tải lại dữ liệu và thông báo kết quả |
| D7 | 3.2-3.5 | Decision | Hệ thống | [3.2-3.5] Tải chi tiết/thao tác thành công? |
| F1 | 3.2/3.3.7/3.4.6/3.5.7 | Final | Hệ thống | Kết thúc sau thao tác thành công hoặc xem |
| F2 | 2/3.2/3.3/3.4/3.5 | Final | Hệ thống | Kết thúc thất bại; không xác nhận thay đổi |
| F3 | 3.3/3.4/3.5 | Final | Admin | Kết thúc do hủy trước khi gửi |


### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | D0 | Danh sách được yêu cầu |
| D0 | D1 | [Tải thành công] |
| D0 | A12 | [Lỗi quyền/API/CSDL] |
| D1 | A2 | [Tìm kiếm] |
| D1 | A4 | [Xem tài khoản] |
| D1 | A5 | [Tạo tài khoản] |
| D1 | F3 | [Hủy trước khi gửi] |
| A2 | D2 | Đã gửi từ khóa |
| D2 | A4 | [Có kết quả và chọn tài khoản] |
| D2 | A3 | [Không có kết quả] |
| D2 | A12 | [Lỗi tìm kiếm] |
| A3 | A2 | [Sửa từ khóa] |
| A4 | D7 | Đã yêu cầu chi tiết và thành viên dự án |
| D7 | D6 | [Chi tiết tải thành công] |
| D7 | A12 | [Lỗi tải chi tiết] |
| D6 | F1 | [Chỉ xem] |
| D6 | A7 | [Sửa hồ sơ] |
| D6 | A9 | [Ẩn danh] |
| A5 | D3 | Đã gửi form tạo |
| D3 | A6 | [Hợp lệ, chưa trùng] |
| D3 | A11 | [Thiếu/sai dữ liệu hoặc trùng] |
| A6 | D7 | Đã xử lý yêu cầu tạo |
| A7 | D4 | Đã gửi form sửa |
| D4 | A8 | [Tài khoản tồn tại, schema hợp lệ] |
| D4 | A11 | [Không tồn tại hoặc dữ liệu sai] |
| A8 | D7 | Đã xử lý yêu cầu sửa |
| A9 | D5 | Đã gửi email xác nhận và lý do |
| D5 | A10 | [Email khớp, không tự ẩn danh, còn Admin hoạt động] |
| D5 | A11 | [Email sai hoặc vi phạm bảo vệ Admin] |
| A10 | D7 | Đã xử lý yêu cầu ẩn danh |
| A11 | D8 | Lỗi nghiệp vụ đã hiển thị |
| D8 | A5 | [Sửa lại dữ liệu tạo] |
| D8 | A7 | [Sửa lại hồ sơ] |
| D8 | A9 | [Sửa lại yêu cầu ẩn danh] |
| D8 | F2 | [Dừng thao tác] |
| D7 | A13 | [Thao tác ghi thành công] |
| D7 | F1 | [Đã xem chi tiết, không thay đổi dữ liệu] |
| D7 | A12 | [Lỗi API/CSDL/dịch vụ nội bộ] |
| A12 | F2 | Không thể tiếp tục |
| A13 | F1 | Kết quả đã hiển thị |

### Số liệu
Action=13, Decision=9, cạnh=41.

YÊU CẦU: Vẽ chính xác node, cạnh, guard và swimlane đã nêu. Giữ riêng kết thúc thành công, thất bại và hủy. Không biến thao tác ẩn danh thành xóa vật lý, không thêm bộ lọc giao diện hoặc quản lý phiên. Nếu thấy mâu thuẫn, báo rõ trước khi hiệu chỉnh; không tự thêm nghiệp vụ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC05 - Quản lý tài khoản của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt. Mức chi tiết phù hợp khóa luận.

ĐẶC TẢ ĐẦY ĐỦ:

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Admin hệ thống có thể xem danh sách và chi tiết tài khoản, tìm kiếm, tạo tài khoản, sửa hồ sơ cơ bản hoặc ẩn danh một tài khoản. Việc khóa, kích hoạt, thay đổi vai trò hệ thống và yêu cầu đặt lại mật khẩu được mô tả ở UC06, UC07 hoặc luồng tương ứng, không gộp vào UC05.

### Tiền điều kiện
- Admin hệ thống đã đăng nhập, credential còn hiệu lực và có quyền quản trị nền tảng.
- Tài khoản đích phải tồn tại đối với thao tác xem/sửa/ẩn danh.
- Tạo tài khoản không đòi hỏi tài khoản đích có trước.

### Hậu điều kiện
- Xem/tìm kiếm: danh sách hoặc chi tiết được hiển thị; dữ liệu không bị thay đổi.
- Tạo: tài khoản USER được tạo ở trạng thái hoạt động nhưng chưa xác minh email; hệ thống khởi tạo quy trình xác minh và đặt mật khẩu. Không khẳng định email đã tới người nhận.
- Sửa: họ tên và/hoặc tên đăng nhập được cập nhật; giao diện tải lại danh sách/chi tiết.
- Ẩn danh: thông tin nhận dạng được thay bằng giá trị ẩn danh, tài khoản chuyển trạng thái DELETED, một số trường cá nhân bị gỡ và truy cập hiện hữu bị thu hồi. Thao tác không xóa lịch sử nghiệp vụ liên quan.
- Thất bại/hủy: lỗi được hiển thị; thao tác chưa gửi hoặc bị từ chối không được xem là thành công. Nếu lỗi xảy ra giữa nhiều lần ghi, tính nguyên tử không được khẳng định ngoài những giao dịch mà mã nguồn bảo đảm.

### Tác nhân chính
Admin hệ thống.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu xác minh/thiết lập thông tin truy cập. Dịch vụ kiểm thử nội bộ cung cấp siêu dữ liệu thành viên dự án khi xem chi tiết tài khoản.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang quản lý tài khoản. | |
| 2 | | Kiểm tra quyền quản trị; tải và hiển thị danh sách tài khoản gồm email, họ tên, vai trò hệ thống và trạng thái. |
| 3 | Chọn một thao tác: tìm kiếm, xem chi tiết, tạo, sửa hồ sơ hoặc ẩn danh. | |
| 4 | | Thực hiện nhánh tương ứng trong luồng thay thế; sau thay đổi thành công, tải lại dữ liệu liên quan. |
| 5 | | Kết thúc UC khi kết quả được hiển thị. |

### Luồng sự kiện thay thế

**3.1. Tìm kiếm tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Nhập email, họ tên hoặc tên đăng nhập rồi gửi tìm kiếm. | |
| 3.1.2 | | Tìm theo từ khóa không phân biệt hoa thường và hiển thị danh sách khớp; giao diện phân trang cục bộ. |
| 3.1.3 | Chọn tài khoản cần xem hoặc tiếp tục tìm. | |
| 3.1.4 | | Nếu chọn tài khoản, chuyển sang bước 3.2.2; nếu tìm tiếp, quay lại 3.1.1. |

**3.2. Xem chi tiết và thành viên dự án**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.1 | Chọn một tài khoản trong danh sách. | |
| 3.2.2 | | Tải hồ sơ chi tiết và danh sách thành viên dự án từ dịch vụ kiểm thử nội bộ. |
| 3.2.3 | | Hiển thị email, họ tên, vai trò hệ thống, trạng thái và dữ liệu thành viên dự án. |
| 3.2.4 | | Kết thúc nhánh xem. |

**3.3. Tạo tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.1 | Chọn “Tạo tài khoản”. | |
| 3.3.2 | | Hiển thị form email, họ tên, tên đăng nhập và lý do. |
| 3.3.3 | Nhập dữ liệu và chọn “Tạo và gửi lời mời”. | |
| 3.3.4 | | Kiểm tra schema, quyền tạo và trùng email/tên đăng nhập. |
| 3.3.5 | | Tạo tài khoản USER, khởi tạo xác minh email và quy trình đặt mật khẩu. |
| 3.3.6 | | Hiển thị tài khoản vừa tạo trong danh sách và thông báo kết quả. |
| 3.3.7 | | Kết thúc nhánh tạo. |

**3.4. Sửa hồ sơ tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.4.1 | Chọn “Sửa hồ sơ” ở chi tiết tài khoản. | |
| 3.4.2 | | Hiển thị họ tên, tên đăng nhập và trường lý do. |
| 3.4.3 | Sửa thông tin và gửi lưu. | |
| 3.4.4 | | Kiểm tra schema, tìm tài khoản đích và cập nhật hồ sơ/audit. |
| 3.4.5 | | Tải lại danh sách/chi tiết và thông báo thành công. |
| 3.4.6 | | Kết thúc nhánh sửa. |

**3.5. Ẩn danh tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.5.1 | Chọn “Xóa và ẩn danh tài khoản”. | |
| 3.5.2 | | Hiển thị yêu cầu nhập chính xác email tài khoản và lý do. |
| 3.5.3 | Nhập email xác nhận, lý do và xác nhận thao tác. | |
| 3.5.4 | | Kiểm tra email xác nhận, quyền, tài khoản đích và quy tắc bảo vệ Admin hoạt động cuối cùng. |
| 3.5.5 | | Ẩn danh hồ sơ, đánh dấu DELETED, gỡ thông tin cá nhân được chỉ định, thu hồi credential truy cập và ghi audit. |
| 3.5.6 | | Đóng chi tiết, tải lại danh sách và thông báo thành công. |
| 3.5.7 | | Kết thúc nhánh ẩn danh. |

### Luồng sự kiện ngoại lệ

- **3.3.4.1.** Email hoặc tên đăng nhập đã tồn tại: từ chối tạo và báo lỗi; quay lại bước 3.3.3.
- **3.3.4.2.** Email, họ tên, slug hoặc lý do không đạt schema: báo lỗi xác thực; quay lại bước 3.3.3.
- **3.4.4.1.** Họ tên/tên đăng nhập không hợp lệ hoặc payload không có trường cập nhật: báo lỗi; quay lại bước 3.4.3. Mã nguồn hiện không có kiểm tra slug trùng riêng trong `update_profile`; hành vi khi vi phạm chỉ mục duy nhất phụ thuộc lỗi lưu trữ.
- **3.2.2.1.** Tài khoản không tìm thấy: báo không tìm thấy và kết thúc nhánh thất bại.
- **3.4.4.2/3.5.4.1.** Tài khoản không tìm thấy trong thao tác cập nhật/ẩn danh: API trả lỗi; không báo thành công.
- **3.5.4.2.** Email xác nhận không khớp: từ chối ẩn danh; quay lại bước 3.5.3.
- **3.5.4.3.** Admin tự ẩn danh hoặc thao tác làm giảm số Admin hoạt động xuống dưới một: từ chối và giữ nguyên dữ liệu.
- **2/3.2.2.** Hết credential hoặc không đủ quyền: trả lỗi xác thực/phân quyền; dừng thao tác, dữ liệu không được xác nhận đã đổi.
- **3.3.5.** Dịch vụ email lỗi: backend ghi log và vẫn có thể trả kết quả tạo tài khoản; không thể kết luận người nhận đã nhận thư. Người dùng quản trị có thể cần dùng lại quy trình gửi hướng dẫn ở UC06.
- **2/3.2/3.3/3.4/3.5.** Lỗi API/CSDL hoặc dịch vụ kiểm thử nội bộ: giao diện hiển thị lỗi tương ứng; không suy diễn rằng mọi thao tác nhiều bước đã rollback.
- **3.3.3/3.4.3/3.5.3.** Admin đóng hộp thoại trước khi gửi: không phát sinh thay đổi dữ liệu.

### Giả định / Câu hỏi cần làm rõ
- API danh sách nhận tham số lọc vai trò và trạng thái, nhưng giao diện `PlatformUsersPanel` tại commit chỉ hiển thị tìm kiếm và phân trang cục bộ. Cần xác nhận có nên bổ sung bộ lọc ở UI; đặc tả hiện không coi đó là chức năng đã cung cấp.
- Tạo tài khoản gọi cả luồng xác minh email và quy trình đặt mật khẩu. Mã nguồn bắt lỗi gửi email, nên “gửi lời mời” chỉ có thể khẳng định là hệ thống đã khởi tạo yêu cầu gửi.
- `update_profile` không kiểm tra slug trùng một cách tường minh. Không giả định thông báo lỗi thân thiện cho trường hợp này nếu chưa kiểm tra chỉ mục và bộ xử lý exception ở môi trường chạy.
- Dịch vụ kiểm thử nội bộ trả metadata thành viên dự án; nếu nghiệp vụ khóa luận không cần nội dung này, có thể tách khỏi chi tiết UC05 theo quyết định của người hướng dẫn.

LIFELINE TỪ TRÁI SANG PHẢI: Admin, Giao diện quản trị, Backend quản trị, Cơ sở dữ liệu, Dịch vụ kiểm thử nội bộ, Dịch vụ email.

### 4b. Bảng message theo thời gian

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Admin | Giao diện quản trị | [1] moQuanLyTaiKhoan() | đồng bộ | chính |
| 2 | 2 | Giao diện quản trị | Backend quản trị | [2] layDanhSachTaiKhoan() | đồng bộ | chính |
| 3 | 2 | Backend quản trị | Cơ sở dữ liệu | [2] timTaiKhoan(search, limit) | đồng bộ | chính |
| 4 | 2 | Cơ sở dữ liệu | Backend quản trị | [2] traDanhSach() | trả về | chính |
| 5 | 2 | Backend quản trị | Giao diện quản trị | [2] traDanhSachTaiKhoan() | trả về | chính |
| 6 | 2 | Giao diện quản trị | Admin | [2] hienThiDanhSach() | trả về | chính |
| 7 | 3.1 | Admin | Giao diện quản trị | [3.1] timTheoTuKhoa(search) | đồng bộ | alt [tìm kiếm] |
| 8 | 3.1 | Giao diện quản trị | Backend quản trị | [3.1] timTaiKhoan(search) | đồng bộ | alt [tìm kiếm] |
| 9 | 3.1 | Backend quản trị | Cơ sở dữ liệu | [3.1] truyVanDanhSach(search) | đồng bộ | alt [tìm kiếm] |
| 10 | 3.1 | Cơ sở dữ liệu | Backend quản trị | [3.1] traKetQuaTimKiem() | trả về | alt [tìm kiếm] |
| 11 | 3.1 | Backend quản trị | Giao diện quản trị | [3.1] traDanhSachKetQua() | trả về | alt [tìm kiếm] |
| 12 | 3.1 | Giao diện quản trị | Admin | [3.1] hienThiKetQua() | trả về | alt [tìm kiếm] |
| 13 | 3.2 | Admin | Giao diện quản trị | [3.2] chonTaiKhoan() | đồng bộ | alt [xem chi tiết] |
| 14 | 3.2 | Giao diện quản trị | Backend quản trị | [3.2] layChiTietVaThanhVien(userId) | đồng bộ | alt [xem chi tiết] |
| 15 | 3.2 | Backend quản trị | Cơ sở dữ liệu | [3.2] docChiTietTaiKhoan(userId) | đồng bộ | alt [xem chi tiết] |
| 16 | 3.2 | Cơ sở dữ liệu | Backend quản trị | [3.2] traChiTietTaiKhoan() | trả về | alt [xem chi tiết] |
| 17 | 3.2 | Backend quản trị | Dịch vụ kiểm thử nội bộ | [3.2] layThanhVienDuAn(userId) | đồng bộ | alt [xem chi tiết] |
| 18 | 3.2 | Dịch vụ kiểm thử nội bộ | Backend quản trị | [3.2] traThanhVienDuAn() | trả về | alt [xem chi tiết] |
| 19 | 3.2 | Backend quản trị | Giao diện quản trị | [3.2] traChiTietVaThanhVien() | trả về | alt [xem chi tiết] |
| 20 | 3.2 | Giao diện quản trị | Admin | [3.2] hienThiChiTiet() | trả về | alt [xem chi tiết] |
| 21 | 3.3 | Admin | Giao diện quản trị | [3.3] guiFormTao(email, fullName, slug, reason) | đồng bộ | alt [tạo] |
| 22 | 3.3 | Giao diện quản trị | Backend quản trị | [3.3] taoTaiKhoan(payload) | đồng bộ | alt [tạo] |
| 23 | 3.3 | Backend quản trị | Cơ sở dữ liệu | [3.3] taoTaiKhoanVaAudit(payload) | đồng bộ | alt [dữ liệu hợp lệ, chưa trùng] |
| 24 | 3.3 | Cơ sở dữ liệu | Backend quản trị | [3.3] traTaiKhoanMoi() | trả về | alt [tạo thành công] |
| 25 | 3.3 | Backend quản trị | Dịch vụ email | [3.3] khoiTaoXacMinhVaDatMatKhau(email) | đồng bộ | alt [tạo thành công] |
| 26 | 3.3 | Dịch vụ email | Backend quản trị | [3.3] traTrangThaiGui() | trả về | alt [thành công hoặc lỗi được bắt] |
| 27 | 3.3 | Backend quản trị | Giao diện quản trị | [3.3] traKetQuaTao() | trả về | alt [tạo thành công] |
| 28 | 3.3 | Giao diện quản trị | Admin | [3.3] hienThiTaiKhoanMoi() | trả về | alt [tạo thành công] |
| 29 | 3.4 | Admin | Giao diện quản trị | [3.4] guiCapNhatHoSo(userId, fullName, slug, reason) | đồng bộ | alt [sửa hồ sơ] |
| 30 | 3.4 | Giao diện quản trị | Backend quản trị | [3.4] capNhatHoSo(userId, payload) | đồng bộ | alt [sửa hồ sơ] |
| 31 | 3.4 | Backend quản trị | Cơ sở dữ liệu | [3.4] luuHoSoVaAudit(userId, payload) | đồng bộ | alt [tài khoản tồn tại] |
| 32 | 3.4 | Cơ sở dữ liệu | Backend quản trị | [3.4] traKetQuaCapNhat() | trả về | alt [thành công/lỗi] |
| 33 | 3.4 | Backend quản trị | Giao diện quản trị | [3.4] traKetQuaHoSo() | trả về | alt [thành công/lỗi] |
| 34 | 3.4 | Giao diện quản trị | Admin | [3.4] hienThiHoSoMoiHoacLoi() | trả về | alt [thành công/lỗi] |
| 35 | 3.5 | Admin | Giao diện quản trị | [3.5] xacNhanAnDanh(userId, email, reason) | đồng bộ | alt [ẩn danh] |
| 36 | 3.5 | Giao diện quản trị | Backend quản trị | [3.5] anDanhTaiKhoan(userId, confirmation, reason) | đồng bộ | alt [ẩn danh] |
| 37 | 3.5 | Backend quản trị | Cơ sở dữ liệu | [3.5] anDanhVaThuHoiTruyCap(userId) | đồng bộ | alt [email khớp, còn Admin hoạt động] |
| 38 | 3.5 | Cơ sở dữ liệu | Backend quản trị | [3.5] traKetQuaAnDanh() | trả về | alt [thành công/lỗi] |
| 39 | 3.5 | Backend quản trị | Giao diện quản trị | [3.5] traKetQuaAnDanh() | trả về | alt [thành công/lỗi] |
| 40 | 3.5 | Giao diện quản trị | Admin | [3.5] dongChiTietVaTaiLaiDanhSach() | trả về | alt [thành công/lỗi] |
| 41 | 3.3.4.1/3.4.4.1/3.5.4 | Backend quản trị | Giao diện quản trị | [3.3.4.1/3.4.4.1/3.5.4] traLoiLoiNghiepVuHoacHaTang() | trả về | alt [lỗi validation/trùng/không tìm thấy/lỗi hệ thống] |
| 42 | 3.3.4.1/3.4.4.1/3.5.4 | Giao diện quản trị | Admin | [3.3.4.1/3.4.4.1/3.5.4] hienThiLoi() | trả về | alt [lỗi] |
| 43 | 3.3/3.4/3.5 | Admin | Giao diện quản trị | [3.3/3.4/3.5] huyHopThoaiTruocKhiGui() | đồng bộ | opt [hủy trước submit] |
| 44 | 3.3/3.4/3.5 | Giao diện quản trị | Admin | [3.3/3.4/3.5] dongHopThoaiKhongThayDoi() | trả về | opt [hủy trước submit] |

### Số liệu
N=15, message=44, fragment=7, lifeline=6.

YÊU CẦU: Dùng activation bar, return và fragment alt/opt có guard. Giữ thứ tự, mã bước, phản hồi lỗi và kết quả từng nhánh. Không gọi nhảy lớp; API và service đã được gộp trong lifeline Backend quản trị. Email lỗi không được thể hiện như bảo đảm thư đã giao. Không thêm quản lý phiên hoặc hard-delete. Đối chiếu L=6, M=44, F=7.
```

## TỰ KIỂM TRA UC05

- [x] Phần 1 kiểm tra CRUD, điểm rẽ, actor, điều kiện, ngoại lệ, lỗi và tính nhất quán.
- [x] Phần 2 ghi rõ giới hạn chứng cứ và các nhánh thành công/thất bại/hủy.
- [x] Activity: Action=13, Decision=9, cạnh=41; Decision đều có guard và graph không có node treo.
- [x] Sequence: 6 lifeline, 44 message, 7 fragment; mọi lời gọi đồng bộ có phản hồi trong nhánh tương ứng.
- [x] Prompt 5/6 chép nguyên văn đặc tả và bảng phân rã; không còn chỗ giữ chỗ hoặc tham chiếu “như trên”.

## Bảng theo dõi sau UC05

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC06 - Kiểm soát truy cập

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Mô tả | MÂU THUẪN | Đặc tả gọi thao tác “Gửi lại lời mời kích hoạt”, nhưng dịch vụ `resend_activation` gọi `forgot_password`, tức khởi tạo quy trình khôi phục mật khẩu. | Mô tả theo hành vi code là khởi tạo/gửi lại hướng dẫn đặt lại mật khẩu; ghi sai khác nhãn UI trong giả định, không khẳng định gửi lại thư xác minh. |
| 5.5 | MƠ HỒ | Nhãn hiện tại có sắc thái bắt buộc đổi ngay, trong khi thao tác chỉ khởi tạo luồng khôi phục mật khẩu. | Dùng nhãn “Yêu cầu đặt lại mật khẩu”: API khởi tạo luồng email; người nhận tự đặt mật khẩu qua UC04. |
| 5.1–5.5 | THIẾU | Luồng chưa tách khóa, mở khóa, vô hiệu hóa, kích hoạt và vai trò hệ thống. | Ghi rõ trạng thái đích, trường hợp UI hiển thị hành động, yêu cầu lý do và guard bảo vệ Admin. |
| 5.4 | MÂU THUẪN | UI hiện hiển thị nút kích hoạt cho mọi trạng thái không ACTIVE và không LOCKED, gồm cả DELETED; backend không có guard loại DELETED. | Đặc tả đường chính cho tài khoản DISABLED; ghi riêng tình trạng DELETED cần xác nhận, không coi việc tái kích hoạt account đã ẩn danh là chính sách đã duyệt. |
| 3.1 | THIẾU | Tác vụ hàng loạt chỉ nói “xem trước” rồi “thực hiện”, thiếu dữ liệu hợp lệ/thiếu, chủ sở hữu và thời hạn preview. | Bổ sung preview 15 phút, danh sách tài khoản tìm thấy/không tìm thấy, xác nhận một lần và lỗi preview hết hạn/đã dùng. |
| Tài khoản hàng loạt | MÂU THUẪN | Backend còn action thu hồi các phiên, nhưng giao diện chỉ cung cấp vô hiệu hóa và gửi lại lời mời; người dùng yêu cầu không có UC quản lý phiên. | Chỉ mô tả hai lựa chọn giao diện là vô hiệu hóa và khởi tạo quy trình đặt lại mật khẩu; không đưa thu hồi phiên thành thao tác. |
| 8.1 | THIẾU | Chưa nêu chặn tự khóa/tự vô hiệu hóa, Admin hoạt động cuối cùng và tự hạ quyền. | Thêm các nhánh từ chối theo kiểm tra trong service và repository. |
| Hậu điều kiện | THIẾU | Chưa phân biệt trạng thái đổi, thư chỉ được khởi tạo, và lỗi/hủy. | Tách hậu điều kiện theo thao tác; ghi thu hồi credential truy cập là side effect khi code thực hiện, không mô hình hóa quản lý phiên. |
| Lỗi/hủy | THIẾU | Chưa xử lý reason không hợp lệ, account không tồn tại, không đủ quyền, lỗi lưu trữ/email và hủy xác nhận. | Bổ sung lỗi áp dụng; mail failure được bắt/log trong quy trình khôi phục và không bảo đảm email đã tới nơi. |
| Tác nhân/UC07 | MƠ HỒ | “Thay đổi vai trò” có thể bị nhầm với phân quyền dự án. | Giới hạn UC06 vào `system_role` USER/ADMIN. Ma trận quyền dự án thuộc UC07. |

Đã kiểm: **8 điểm rẽ, 10 nhánh và 9 nhóm lỗi** (self/last Admin, dữ liệu thiếu/sai, tài khoản thiếu, không đủ quyền, preview sai/hết hạn/đã dùng, lỗi lưu trữ, lỗi mail, hủy). Đã rà actor, điều kiện, thành công/thất bại, điểm quay lại, CRUD không áp dụng, khác biệt UC07 và tác dụng phụ thu hồi credential. Không thêm UC quản lý phiên.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Admin hệ thống quản lý trạng thái truy cập và vai trò hệ thống của tài khoản; khởi tạo quy trình đặt lại mật khẩu qua email; hoặc thao tác hàng loạt để vô hiệu hóa tài khoản/gửi hướng dẫn đặt lại. Vai trò hệ thống USER/ADMIN khác ma trận quyền dự án của UC07.

### Tiền điều kiện
- Admin đã đăng nhập và có quyền quản trị nền tảng.
- Với thao tác đơn, tài khoản đích tồn tại và Admin xem được chi tiết.
- Với thao tác hàng loạt, Admin chọn ít nhất một mã tài khoản và nêu lý do; danh sách có thể chứa ID không tồn tại, được báo ở preview.

### Hậu điều kiện
- Khóa, mở khóa, vô hiệu hóa, kích hoạt hoặc đổi vai trò: trạng thái/vai trò được cập nhật và audit được ghi. Khi khóa/vô hiệu hóa hoặc đổi system_role, code thu hồi credential truy cập; mở khóa/kích hoạt không gọi thu hồi. Đây là side effect, không phải chức năng quản lý phiên.
- Yêu cầu đặt lại mật khẩu: hệ thống khởi tạo luồng email UC04; không đặt mật khẩu mới thay người dùng và không khẳng định email đã được giao.
- Gửi lại theo nút đang có: code gọi cùng quy trình `forgot_password`; không thể khẳng định đó là thư xác minh kích hoạt.
- Bulk: thao tác chỉ chạy sau preview và xác nhận hợp lệ. Hệ thống lưu kết quả tổng hợp số tài khoản xử lý; không cung cấp bảng kết quả chi tiết từng email.
- Thất bại/hủy: lỗi được hiển thị; không báo thành công nếu cập nhật bị từ chối hoặc preview không còn hiệu lực. Không khẳng định rollback cho chuỗi tác vụ nhiều bước ngoài giao dịch được code bảo đảm.

### Tác nhân chính
Admin hệ thống.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu gửi hướng dẫn khôi phục mật khẩu. Không có tác nhân phiên/thiết bị.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang quản lý tài khoản. | |
| 2 | | Kiểm tra quyền quản trị và hiển thị danh sách tài khoản. |
| 3 | Chọn tài khoản cần kiểm soát. | |
| 4 | | Hiển thị chi tiết, vai trò hệ thống và trạng thái hiện tại. |
| 5 | Chọn thao tác đơn hoặc thao tác hàng loạt. | |
| 6 | | Thực hiện một trong các nhánh thay thế 5.1–5.8. |
| 7 | | Hiển thị kết quả và tải lại dữ liệu khi thao tác thành công. |
| 8 | | Kết thúc UC. |

### Luồng sự kiện thay thế

**5.1. Khóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.1.1 | Chọn “Khóa tài khoản”. | |
| 5.1.2 | | Hiển thị hộp thoại yêu cầu lý do. |
| 5.1.3 | Nhập lý do và xác nhận. | |
| 5.1.4 | | Từ chối nếu Admin khóa chính mình hoặc làm mất Admin hoạt động cuối; nếu hợp lệ, đặt trạng thái LOCKED, thu hồi credential truy cập và ghi audit. |
| 5.1.5 | | Trả kết quả; giao diện cập nhật chi tiết/danh sách. Kết thúc nhánh. |

**5.2. Mở khóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.2.1 | Chọn “Mở khóa tài khoản”. | |
| 5.2.2 | Nhập lý do và xác nhận. | |
| 5.2.3 | | Đặt trạng thái ACTIVE, lưu lý do/audit và trả kết quả. |
| 5.2.4 | | Cập nhật giao diện; kết thúc nhánh. |

**5.3. Vô hiệu hóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.3.1 | Chọn “Vô hiệu hóa tài khoản”. | |
| 5.3.2 | Nhập lý do và xác nhận. | |
| 5.3.3 | | Từ chối nếu Admin thao tác trên chính mình hoặc loại bỏ Admin hoạt động cuối; nếu hợp lệ, đặt trạng thái DISABLED, thu hồi credential truy cập và ghi audit. |
| 5.3.4 | | Hiển thị kết quả và cập nhật danh sách; kết thúc nhánh. |

**5.4. Kích hoạt tài khoản DISABLED**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.4.1 | Chọn “Kích hoạt tài khoản” trên tài khoản DISABLED. | |
| 5.4.2 | Nhập lý do và xác nhận. | |
| 5.4.3 | | Đặt trạng thái ACTIVE và ghi audit. |
| 5.4.4 | | Hiển thị kết quả; kết thúc nhánh. |

**5.5. Thay đổi vai trò hệ thống**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.5.1 | Chọn cấp hoặc hạ vai trò quản trị. | |
| 5.5.2 | Nhập lý do và xác nhận. | |
| 5.5.3 | | Từ chối tự hạ quyền Admin hiện tại hoặc làm mất Admin hoạt động cuối; nếu hợp lệ, lưu system_role USER/ADMIN, ghi audit và thu hồi credential truy cập theo hành vi code. |
| 5.5.4 | | Cập nhật giao diện; kết thúc nhánh. |

**5.6. Yêu cầu đặt lại mật khẩu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.6.1 | Chọn “Yêu cầu đặt lại mật khẩu”. | |
| 5.6.2 | Nhập lý do và xác nhận. | |
| 5.6.3 | | Khởi tạo luồng khôi phục UC04 cho email tài khoản, thu hồi credential truy cập theo hành vi code và ghi audit. |
| 5.6.4 | | Trả trạng thái xử lý yêu cầu; không khẳng định email đã được nhận. Kết thúc nhánh. |

**5.7. Gửi lại hướng dẫn qua email theo nút hiện có**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.7.1 | Chọn nút đang mang nhãn “Gửi lại quy trình kích hoạt”. | |
| 5.7.2 | Nhập lý do và xác nhận. | |
| 5.7.3 | | Gọi `forgot_password` cho tài khoản và ghi audit; đây là quy trình khôi phục mật khẩu theo code, không khẳng định gửi thư xác minh kích hoạt. |
| 5.7.4 | | Trả trạng thái xử lý; kết thúc nhánh. |

**5.8. Thao tác hàng loạt**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.8.1 | Chọn vô hiệu hóa hoặc gửi hướng dẫn đặt lại, nhập ID tài khoản và lý do. | |
| 5.8.2 | Chọn “Tạo bản xem trước”. | |
| 5.8.3 | | Loại ID trùng, tìm tài khoản tồn tại, ghi nhận ID thiếu và tạo preview hết hạn sau 15 phút. |
| 5.8.4 | | Hiển thị số tài khoản tìm thấy và ID không tồn tại. |
| 5.8.5 | Xác nhận thực hiện hoặc hủy. | |
| 5.8.6 | | Kiểm tra preview còn hạn, chưa dùng và do Admin hiện tại tạo; thực hiện thao tác trên các tài khoản hợp lệ. |
| 5.8.7 | | Trả trạng thái COMPLETED và số lượng đã xử lý; cập nhật danh sách. Kết thúc nhánh. |

### Luồng sự kiện ngoại lệ

- **5.1.4.1.** Admin tự khóa hoặc là Admin hoạt động cuối: từ chối; quay lại bước 5.1.1 hoặc kết thúc nếu Admin dừng.
- **5.3.3.1.** Admin tự vô hiệu hóa hoặc làm mất Admin hoạt động cuối: từ chối; quay lại bước 5.3.1 hoặc kết thúc.
- **5.5.3.1.** Admin tự hạ quyền hoặc làm mất Admin hoạt động cuối: từ chối; quay lại bước 5.5.1 hoặc kết thúc.
- **5.1.3/5.2.2/5.3.2/5.4.2/5.5.2/5.6.2/5.7.2/5.8.1.** Lý do thiếu hoặc không đạt schema (lý do 3–1000 ký tự; danh sách bulk 1–500 ID): API từ chối; quay lại form tương ứng.
- **3/5.** Tài khoản không tìm thấy hoặc Admin hết quyền: trả 404/401/403; kết thúc nhánh thất bại, không báo cập nhật thành công.
- **5.6.3/5.7.3.** Dịch vụ email lỗi được xử lý bên trong luồng khôi phục; response chung không chứng minh thư đã tới người nhận.
- **5.8.3.** Không tìm thấy ID nào hợp lệ: không có tài khoản để xử lý; yêu cầu nhập danh sách khác.
- **5.8.6.1.** Preview không tồn tại, đã hết hạn, đã dùng hoặc không thuộc Admin hiện tại: từ chối; quay lại bước 5.8.2 để tạo preview mới.
- **5.8.6.2.** Tài khoản đích là Admin cuối cùng trong thao tác vô hiệu hóa: guard từ chối cập nhật; không báo hoàn tất.
- **2/5.1–5.8.** Lỗi API/CSDL/hệ thống ngoài: hiển thị lỗi nếu có phản hồi; không khẳng định toàn bộ tác vụ nhiều bước đã rollback.
- **5.1.3/5.2.2/5.3.2/5.4.2/5.5.2/5.6.2/5.7.2/5.8.5.** Admin đóng hộp thoại hoặc hủy xác nhận trước khi gửi: không chạy thao tác tiếp theo.

### Giả định / Câu hỏi cần làm rõ
- Nhãn UI hiện tại có thể hàm ý đổi ngay; endpoint chỉ khởi tạo luồng khôi phục để người dùng tự đặt mật khẩu. Đặc tả dùng “Yêu cầu đặt lại mật khẩu”.
- Nút “Gửi lại quy trình kích hoạt” gọi service `forgot_password`, không gọi trực tiếp `issue_email_verification`; cần xác nhận lại ý định sản phẩm hoặc đổi nhãn UI.
- UI hiện hiển thị nút kích hoạt cho trạng thái khác ACTIVE/LOCKED; với tài khoản DELETED được ẩn danh, backend không có guard riêng trước khi chuyển status ACTIVE. Cần xác nhận chính sách và cân nhắc chặn thao tác này.
- Trong thao tác bulk, backend loại ID của Admin hiện hành khỏi tập xử lý khi xác nhận. Preview UI không nêu rõ mục bị loại; đặc tả không coi tài khoản Admin đó là đã xử lý.
- Bulk API có thêm action thu hồi phiên, nhưng giao diện không cung cấp action này và nó bị loại khỏi UC theo yêu cầu không đặc tả quản lý phiên.
- `confirm_bulk` chỉ trả số lượng tổng thể; không có bằng chứng giao diện nhận kết quả chi tiết theo từng email.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức nghiệp vụ khóa luận)

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Hệ thống | Bắt đầu; tiền điều kiện: Admin có quyền quản trị nền tảng |
| A1 | 1-2 | Action | Admin / Hệ thống | [1-2] Mở trang và tải danh sách tài khoản |
| D8 | 2 | Decision | Hệ thống | [2] Danh sách tải thành công? |
| D1 | 2-5 | Decision | Admin | [2-5] Chọn thao tác đơn, hàng loạt hay hủy? |
| A2 | 3-4 | Action | Admin / Hệ thống | [3-4] Chọn tài khoản và xem chi tiết |
| D2 | 5 | Decision | Admin | [5] Chọn thao tác đơn nào? |
| A3 | 5.1-5.4 | Action | Admin | [5.1-5.4] Gửi thay đổi trạng thái kèm lý do |
| D3 | 5.1-5.4 | Decision | Hệ thống | [5.1-5.4] Trạng thái đích qua guard Admin? |
| A4 | 5.1-5.4 | Action | Hệ thống | [5.1-5.4] Lưu trạng thái, audit và xử lý credential truy cập |
| A5 | 5.5 | Action | Admin | [5.5] Gửi thay đổi vai trò hệ thống kèm lý do |
| D4 | 5.5 | Decision | Hệ thống | [5.5] Vai trò mới qua guard Admin? |
| A6 | 5.5 | Action | Hệ thống | [5.5] Lưu USER/ADMIN, audit và xử lý credential truy cập |
| A7 | 5.6-5.7 | Action | Admin | [5.6-5.7] Gửi yêu cầu đặt lại/gửi lại hướng dẫn kèm lý do |
| A8 | 5.6-5.7 | Action | Hệ thống | [5.6-5.7] Khởi tạo quy trình khôi phục mật khẩu |
| A9 | 5.8.1-5.8.2 | Action | Admin | [5.8.1-5.8.2] Chọn action hàng loạt, ID và lý do |
| D5 | 5.8.3 | Decision | Hệ thống | [5.8.3] Có tài khoản hợp lệ để tạo preview? |
| A10 | 5.8.3-5.8.4 | Action | Hệ thống | [5.8.3-5.8.4] Tạo preview và hiển thị ID thiếu |
| D6 | 5.8.5 | Decision | Admin | [5.8.5] Xác nhận hay hủy preview? |
| A11 | 5.8.6 | Action | Admin / Hệ thống | [5.8.6] Xác nhận và gửi operation ID |
| D7 | 5.8.6 | Decision | Hệ thống | [5.8.6] Preview còn hiệu lực và thao tác thành công? |
| A12 | 5.8.7/7 | Action | Hệ thống | [5.8.7/7] Hiển thị kết quả tổng hợp và tải lại danh sách |
| A13 | 2/5.1-5.8 | Action | Hệ thống | [2/5.1-5.8] Báo lỗi quyền, validation, preview hoặc hệ thống |
| F1 | 7 | Final | Hệ thống | Kết thúc thành công |
| F2 | 2/5.1-5.8 | Final | Hệ thống | Kết thúc thất bại; không báo thao tác hoàn tất |
| F3 | 5/5.8.5 | Final | Admin | Kết thúc do hủy trước khi gửi/xác nhận |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | D8 | Danh sách được yêu cầu |
| D8 | D1 | [Danh sách tải thành công] |
| D8 | A13 | [Lỗi quyền/API/CSDL] |
| D1 | A2 | [Thao tác đơn] |
| D1 | A9 | [Thao tác hàng loạt] |
| D1 | F3 | [Hủy] |
| A2 | D2 | Chi tiết đã hiển thị |
| D2 | A3 | [Khóa/mở khóa/vô hiệu hóa/kích hoạt] |
| D2 | A5 | [Đổi vai trò hệ thống] |
| D2 | A7 | [Yêu cầu đặt lại/gửi lại hướng dẫn] |
| D2 | F3 | [Hủy hộp thoại] |
| A3 | D3 | Admin đã xác nhận lý do |
| D3 | A4 | [Trạng thái hợp lệ, không vi phạm guard] |
| D3 | A13 | [Tự khóa/tự vô hiệu hóa/Admin cuối/schema sai] |
| A4 | F1 | Cập nhật trạng thái thành công |
| A5 | D4 | Admin đã xác nhận vai trò và lý do |
| D4 | A6 | [Thay đổi hợp lệ, không tự hạ quyền/Admin cuối] |
| D4 | A13 | [Vi phạm guard hoặc schema] |
| A6 | F1 | Vai trò hệ thống đã lưu |
| A7 | A8 | Yêu cầu được gửi |
| A8 | F1 | Quy trình khôi phục đã khởi tạo; không bảo đảm email đã giao |
| A9 | D5 | Admin gửi action, danh sách ID và lý do |
| D5 | A10 | [Có ít nhất một tài khoản khớp] |
| D5 | A13 | [Không có ID hợp lệ/lỗi preview] |
| A10 | D6 | Preview tạo xong, hết hạn sau 15 phút |
| D6 | A11 | [Admin xác nhận] |
| D6 | F3 | [Admin hủy] |
| A11 | D7 | Backend nhận operation ID |
| D7 | A12 | [Preview hợp lệ và thao tác hoàn tất] |
| D7 | A13 | [Hết hạn/đã dùng/sai chủ sở hữu/lỗi thao tác] |
| A12 | F1 | Kết quả tổng hợp đã hiển thị |
| A13 | F2 | Lỗi hoặc từ chối không thể tiếp tục |

### 3c. Số liệu

N = 16 nhóm tương tác nghiệp vụ; M = 13 Action; D = 8 Decision; E = 33 cạnh. Các node gộp thao tác liền nhau theo nghiệp vụ.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức nghiệp vụ khóa luận)

### 4a. Lifeline trái sang phải

Admin → Giao diện quản trị → Backend quản trị (API và service) → Cơ sở dữ liệu → Dịch vụ email. Backend được gộp để giảm bước lặp giữa controller và service; không tách Repository. Không có lifeline quản lý phiên.

### 4b. Bảng message theo thời gian

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Admin | Giao diện quản trị | [1] moQuanLyTaiKhoan() | đồng bộ | chính |
| 2 | 2 | Giao diện quản trị | Backend quản trị | [2] layDanhSachTaiKhoan() | đồng bộ | chính |
| 3 | 2 | Backend quản trị | Cơ sở dữ liệu | [2] timDanhSachTaiKhoan() | đồng bộ | chính |
| 4 | 2 | Cơ sở dữ liệu | Backend quản trị | [2] traDanhSachTaiKhoan() | trả về | chính |
| 5 | 2 | Backend quản trị | Giao diện quản trị | [2] traDanhSachTaiKhoan() | trả về | chính |
| 6 | 2 | Giao diện quản trị | Admin | [2] hienThiDanhSach() | trả về | chính |
| 7 | 3-4 | Admin | Giao diện quản trị | [3-4] chonTaiKhoanVaXemChiTiet(userId) | đồng bộ | chính |
| 8 | 4 | Giao diện quản trị | Backend quản trị | [4] layChiTietTaiKhoan(userId) | đồng bộ | chính |
| 9 | 4 | Backend quản trị | Cơ sở dữ liệu | [4] docTaiKhoan(userId) | đồng bộ | chính |
| 10 | 4 | Cơ sở dữ liệu | Backend quản trị | [4] traChiTietVaTrangThai() | trả về | chính |
| 11 | 4 | Backend quản trị | Giao diện quản trị | [4] traChiTietTaiKhoan() | trả về | chính |
| 12 | 4 | Giao diện quản trị | Admin | [4] hienThiTrangThaiTaiKhoan() | trả về | chính |
| 13 | 5.1-5.7 | Admin | Giao diện quản trị | [5.1-5.7] chonThaoTacVaGuiLyDo() | đồng bộ | alt [status/role] / else [yêu cầu email] |
| 14 | 5.1-5.5 | Giao diện quản trị | Backend quản trị | [5.1-5.5] capNhatStatusHoacSystemRole(userId, payload) | đồng bộ | alt [status/role] |
| 15 | 5.1-5.5 | Backend quản trị | Cơ sở dữ liệu | [5.1-5.5] kiemTraAdminGuardVaLuuThayDoi() | đồng bộ | alt [thay đổi trạng thái/vai trò] |
| 16 | 5.1-5.5 | Cơ sở dữ liệu | Backend quản trị | [5.1-5.5] traKetQuaThayDoi() | trả về | alt [thành công/bị từ chối] |
| 17 | 5.1-5.5 | Backend quản trị | Giao diện quản trị | [5.1-5.5] traKetQuaStatusHoacRole() | trả về | alt [thành công/bị từ chối] |
| 18 | 5.1-5.5 | Giao diện quản trị | Admin | [5.1-5.5] hienThiKetQuaThayDoi() | trả về | alt [thành công/bị từ chối] |
| 19 | 5.6-5.7 | Giao diện quản trị | Backend quản trị | [5.6-5.7] khoiTaoForgotPassword(userId, reason) | đồng bộ | alt [yêu cầu đặt lại/gửi lại hướng dẫn] |
| 20 | 5.6-5.7 | Backend quản trị | Cơ sở dữ liệu | [5.6-5.7] taoMaKhoiPhucVaAudit() | đồng bộ | alt [tài khoản tồn tại] |
| 21 | 5.6-5.7 | Cơ sở dữ liệu | Backend quản trị | [5.6-5.7] traKetQuaTaoMa() | trả về | alt [tài khoản tồn tại] |
| 22 | 5.6-5.7 | Backend quản trị | Dịch vụ email | [5.6-5.7] guiHuongDanKhoiPhuc(email) | đồng bộ | opt [gửi email] |
| 23 | 5.6-5.7 | Dịch vụ email | Backend quản trị | [5.6-5.7] traTrangThaiGui() | trả về | opt [email thành công/lỗi được bắt] |
| 24 | 5.6-5.7 | Backend quản trị | Giao diện quản trị | [5.6-5.7] traTrangThaiYeuCau() | trả về | alt [đã khởi tạo] |
| 25 | 5.6-5.7 | Giao diện quản trị | Admin | [5.6-5.7] hienThiTrangThaiYeuCau() | trả về | alt [đã khởi tạo] |
| 26 | 5.8.1-5.8.2 | Admin | Giao diện quản trị | [5.8.1-5.8.2] guiActionIdsVaReason(action, ids, reason) | đồng bộ | alt [bulk preview] |
| 27 | 5.8.3 | Giao diện quản trị | Backend quản trị | [5.8.3] taoPreview(action, ids, reason) | đồng bộ | alt [bulk preview] |
| 28 | 5.8.3 | Backend quản trị | Cơ sở dữ liệu | [5.8.3] timIdsVaLuuPreview(expiresIn=15m) | đồng bộ | alt [bulk preview] |
| 29 | 5.8.3-5.8.4 | Cơ sở dữ liệu | Backend quản trị | [5.8.3-5.8.4] traIdsHopLeVaThieu() | trả về | alt [preview hợp lệ/không có kết quả] |
| 30 | 5.8.4 | Backend quản trị | Giao diện quản trị | [5.8.4] traTomTatPreview() | trả về | alt [preview tạo được] |
| 31 | 5.8.4 | Giao diện quản trị | Admin | [5.8.4] hienThiSoLuongHopLeVaThieu() | trả về | alt [preview tạo được] |
| 32 | 5.8.5 | Admin | Giao diện quản trị | [5.8.5] xacNhanHoacHuyPreview() | đồng bộ | alt [xác nhận] / else [hủy] |
| 33 | 5.8.6 | Giao diện quản trị | Backend quản trị | [5.8.6] xacNhanPreview(operationId) | đồng bộ | alt [xác nhận] |
| 34 | 5.8.6 | Backend quản trị | Cơ sở dữ liệu | [5.8.6] claimVaApDungBulkAction(operationId) | đồng bộ | alt [preview còn hiệu lực, đúng chủ] |
| 35 | 5.8.6 | Cơ sở dữ liệu | Backend quản trị | [5.8.6] traKetQuaBulk() | trả về | alt [hoàn tất/lỗi] |
| 36 | 5.8.6 | Backend quản trị | Dịch vụ email | [5.8.6] guiHuongDanDatLaiChoTaiKhoanHopLe() | đồng bộ | loop [action gửi hướng dẫn] |
| 37 | 5.8.6 | Dịch vụ email | Backend quản trị | [5.8.6] traKetQuaGui() | trả về | loop [mỗi tài khoản; lỗi gửi được bắt và tiếp tục] |
| 38 | 5.8.7 | Backend quản trị | Giao diện quản trị | [5.8.7] traTongSoDaXuLyHoacLoiPreview() | trả về | alt [hoàn tất/preview lỗi] |
| 39 | 5.8.7 | Giao diện quản trị | Admin | [5.8.7] hienThiKetQuaVaTaiLai() | trả về | alt [hoàn tất/preview lỗi] |

### 4c. Số liệu

N = 16 nhóm tương tác nghiệp vụ; M = 39 message; F = 6 fragment (alt chọn thao tác đơn, alt kết quả thao tác, opt lỗi email, alt kết quả preview, alt xác nhận/hủy, loop gửi hướng dẫn theo từng tài khoản); L = 5. Sequence giữ các trao đổi nghiệp vụ chính, không tách controller/service/repository.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC06 - Kiểm soát truy cập của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt. Mức chi tiết phù hợp khóa luận.

ĐẶC TẢ ĐẦY ĐỦ:

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Admin hệ thống quản lý trạng thái truy cập và vai trò hệ thống của tài khoản; khởi tạo quy trình đặt lại mật khẩu qua email; hoặc thao tác hàng loạt để vô hiệu hóa tài khoản/gửi hướng dẫn đặt lại. Vai trò hệ thống USER/ADMIN khác ma trận quyền dự án của UC07.

### Tiền điều kiện
- Admin đã đăng nhập và có quyền quản trị nền tảng.
- Với thao tác đơn, tài khoản đích tồn tại và Admin xem được chi tiết.
- Với thao tác hàng loạt, Admin chọn ít nhất một mã tài khoản và nêu lý do; danh sách có thể chứa ID không tồn tại, được báo ở preview.

### Hậu điều kiện
- Khóa, mở khóa, vô hiệu hóa, kích hoạt hoặc đổi vai trò: trạng thái/vai trò được cập nhật và audit được ghi. Khi khóa/vô hiệu hóa hoặc đổi system_role, code thu hồi credential truy cập; mở khóa/kích hoạt không gọi thu hồi. Đây là side effect, không phải chức năng quản lý phiên.
- Yêu cầu đặt lại mật khẩu: hệ thống khởi tạo luồng email UC04; không đặt mật khẩu mới thay người dùng và không khẳng định email đã được giao.
- Gửi lại theo nút đang có: code gọi cùng quy trình `forgot_password`; không thể khẳng định đó là thư xác minh kích hoạt.
- Bulk: thao tác chỉ chạy sau preview và xác nhận hợp lệ. Hệ thống lưu kết quả tổng hợp số tài khoản xử lý; không cung cấp bảng kết quả chi tiết từng email.
- Thất bại/hủy: lỗi được hiển thị; không báo thành công nếu cập nhật bị từ chối hoặc preview không còn hiệu lực. Không khẳng định rollback cho chuỗi tác vụ nhiều bước ngoài giao dịch được code bảo đảm.

### Tác nhân chính
Admin hệ thống.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu gửi hướng dẫn khôi phục mật khẩu. Không có tác nhân phiên/thiết bị.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang quản lý tài khoản. | |
| 2 | | Kiểm tra quyền quản trị và hiển thị danh sách tài khoản. |
| 3 | Chọn tài khoản cần kiểm soát. | |
| 4 | | Hiển thị chi tiết, vai trò hệ thống và trạng thái hiện tại. |
| 5 | Chọn thao tác đơn hoặc thao tác hàng loạt. | |
| 6 | | Thực hiện một trong các nhánh thay thế 5.1–5.8. |
| 7 | | Hiển thị kết quả và tải lại dữ liệu khi thao tác thành công. |
| 8 | | Kết thúc UC. |

### Luồng sự kiện thay thế

**5.1. Khóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.1.1 | Chọn “Khóa tài khoản”. | |
| 5.1.2 | | Hiển thị hộp thoại yêu cầu lý do. |
| 5.1.3 | Nhập lý do và xác nhận. | |
| 5.1.4 | | Từ chối nếu Admin khóa chính mình hoặc làm mất Admin hoạt động cuối; nếu hợp lệ, đặt trạng thái LOCKED, thu hồi credential truy cập và ghi audit. |
| 5.1.5 | | Trả kết quả; giao diện cập nhật chi tiết/danh sách. Kết thúc nhánh. |

**5.2. Mở khóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.2.1 | Chọn “Mở khóa tài khoản”. | |
| 5.2.2 | Nhập lý do và xác nhận. | |
| 5.2.3 | | Đặt trạng thái ACTIVE, lưu lý do/audit và trả kết quả. |
| 5.2.4 | | Cập nhật giao diện; kết thúc nhánh. |

**5.3. Vô hiệu hóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.3.1 | Chọn “Vô hiệu hóa tài khoản”. | |
| 5.3.2 | Nhập lý do và xác nhận. | |
| 5.3.3 | | Từ chối nếu Admin thao tác trên chính mình hoặc loại bỏ Admin hoạt động cuối; nếu hợp lệ, đặt trạng thái DISABLED, thu hồi credential truy cập và ghi audit. |
| 5.3.4 | | Hiển thị kết quả và cập nhật danh sách; kết thúc nhánh. |

**5.4. Kích hoạt tài khoản DISABLED**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.4.1 | Chọn “Kích hoạt tài khoản” trên tài khoản DISABLED. | |
| 5.4.2 | Nhập lý do và xác nhận. | |
| 5.4.3 | | Đặt trạng thái ACTIVE và ghi audit. |
| 5.4.4 | | Hiển thị kết quả; kết thúc nhánh. |

**5.5. Thay đổi vai trò hệ thống**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.5.1 | Chọn cấp hoặc hạ vai trò quản trị. | |
| 5.5.2 | Nhập lý do và xác nhận. | |
| 5.5.3 | | Từ chối tự hạ quyền Admin hiện tại hoặc làm mất Admin hoạt động cuối; nếu hợp lệ, lưu system_role USER/ADMIN, ghi audit và thu hồi credential truy cập theo hành vi code. |
| 5.5.4 | | Cập nhật giao diện; kết thúc nhánh. |

**5.6. Yêu cầu đặt lại mật khẩu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.6.1 | Chọn “Yêu cầu đặt lại mật khẩu”. | |
| 5.6.2 | Nhập lý do và xác nhận. | |
| 5.6.3 | | Khởi tạo luồng khôi phục UC04 cho email tài khoản, thu hồi credential truy cập theo hành vi code và ghi audit. |
| 5.6.4 | | Trả trạng thái xử lý yêu cầu; không khẳng định email đã được nhận. Kết thúc nhánh. |

**5.7. Gửi lại hướng dẫn qua email theo nút hiện có**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.7.1 | Chọn nút đang mang nhãn “Gửi lại quy trình kích hoạt”. | |
| 5.7.2 | Nhập lý do và xác nhận. | |
| 5.7.3 | | Gọi `forgot_password` cho tài khoản và ghi audit; đây là quy trình khôi phục mật khẩu theo code, không khẳng định gửi thư xác minh kích hoạt. |
| 5.7.4 | | Trả trạng thái xử lý; kết thúc nhánh. |

**5.8. Thao tác hàng loạt**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.8.1 | Chọn vô hiệu hóa hoặc gửi hướng dẫn đặt lại, nhập ID tài khoản và lý do. | |
| 5.8.2 | Chọn “Tạo bản xem trước”. | |
| 5.8.3 | | Loại ID trùng, tìm tài khoản tồn tại, ghi nhận ID thiếu và tạo preview hết hạn sau 15 phút. |
| 5.8.4 | | Hiển thị số tài khoản tìm thấy và ID không tồn tại. |
| 5.8.5 | Xác nhận thực hiện hoặc hủy. | |
| 5.8.6 | | Kiểm tra preview còn hạn, chưa dùng và do Admin hiện tại tạo; thực hiện thao tác trên các tài khoản hợp lệ. |
| 5.8.7 | | Trả trạng thái COMPLETED và số lượng đã xử lý; cập nhật danh sách. Kết thúc nhánh. |

### Luồng sự kiện ngoại lệ

- **5.1.4.1.** Admin tự khóa hoặc là Admin hoạt động cuối: từ chối; quay lại bước 5.1.1 hoặc kết thúc nếu Admin dừng.
- **5.3.3.1.** Admin tự vô hiệu hóa hoặc làm mất Admin hoạt động cuối: từ chối; quay lại bước 5.3.1 hoặc kết thúc.
- **5.5.3.1.** Admin tự hạ quyền hoặc làm mất Admin hoạt động cuối: từ chối; quay lại bước 5.5.1 hoặc kết thúc.
- **5.1.3/5.2.2/5.3.2/5.4.2/5.5.2/5.6.2/5.7.2/5.8.1.** Lý do thiếu hoặc không đạt schema (lý do 3–1000 ký tự; danh sách bulk 1–500 ID): API từ chối; quay lại form tương ứng.
- **3/5.** Tài khoản không tìm thấy hoặc Admin hết quyền: trả 404/401/403; kết thúc nhánh thất bại, không báo cập nhật thành công.
- **5.6.3/5.7.3.** Dịch vụ email lỗi được xử lý bên trong luồng khôi phục; response chung không chứng minh thư đã tới người nhận.
- **5.8.3.** Không tìm thấy ID nào hợp lệ: không có tài khoản để xử lý; yêu cầu nhập danh sách khác.
- **5.8.6.1.** Preview không tồn tại, đã hết hạn, đã dùng hoặc không thuộc Admin hiện tại: từ chối; quay lại bước 5.8.2 để tạo preview mới.
- **5.8.6.2.** Tài khoản đích là Admin cuối cùng trong thao tác vô hiệu hóa: guard từ chối cập nhật; không báo hoàn tất.
- **2/5.1–5.8.** Lỗi API/CSDL/hệ thống ngoài: hiển thị lỗi nếu có phản hồi; không khẳng định toàn bộ tác vụ nhiều bước đã rollback.
- **5.1.3/5.2.2/5.3.2/5.4.2/5.5.2/5.6.2/5.7.2/5.8.5.** Admin đóng hộp thoại hoặc hủy xác nhận trước khi gửi: không chạy thao tác tiếp theo.

### Giả định / Câu hỏi cần làm rõ
- Nhãn UI hiện tại có thể hàm ý đổi ngay; endpoint chỉ khởi tạo luồng khôi phục để người dùng tự đặt mật khẩu. Đặc tả dùng “Yêu cầu đặt lại mật khẩu”.
- Nút “Gửi lại quy trình kích hoạt” gọi service `forgot_password`, không gọi trực tiếp `issue_email_verification`; cần xác nhận lại ý định sản phẩm hoặc đổi nhãn UI.
- UI hiện hiển thị nút kích hoạt cho trạng thái khác ACTIVE/LOCKED; với tài khoản DELETED được ẩn danh, backend không có guard riêng trước khi chuyển status ACTIVE. Cần xác nhận chính sách và cân nhắc chặn thao tác này.
- Trong thao tác bulk, backend loại ID của Admin hiện hành khỏi tập xử lý khi xác nhận. Preview UI không nêu rõ mục bị loại; đặc tả không coi tài khoản Admin đó là đã xử lý.
- Bulk API có thêm action thu hồi phiên, nhưng giao diện không cung cấp action này và nó bị loại khỏi UC theo yêu cầu không đặc tả quản lý phiên.
- `confirm_bulk` chỉ trả số lượng tổng thể; không có bằng chứng giao diện nhận kết quả chi tiết theo từng email.

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Hệ thống | Bắt đầu; tiền điều kiện: Admin có quyền quản trị nền tảng |
| A1 | 1-2 | Action | Admin / Hệ thống | [1-2] Mở trang và tải danh sách tài khoản |
| D8 | 2 | Decision | Hệ thống | [2] Danh sách tải thành công? |
| D1 | 2-5 | Decision | Admin | [2-5] Chọn thao tác đơn, hàng loạt hay hủy? |
| A2 | 3-4 | Action | Admin / Hệ thống | [3-4] Chọn tài khoản và xem chi tiết |
| D2 | 5 | Decision | Admin | [5] Chọn thao tác đơn nào? |
| A3 | 5.1-5.4 | Action | Admin | [5.1-5.4] Gửi thay đổi trạng thái kèm lý do |
| D3 | 5.1-5.4 | Decision | Hệ thống | [5.1-5.4] Trạng thái đích qua guard Admin? |
| A4 | 5.1-5.4 | Action | Hệ thống | [5.1-5.4] Lưu trạng thái, audit và xử lý credential truy cập |
| A5 | 5.5 | Action | Admin | [5.5] Gửi thay đổi vai trò hệ thống kèm lý do |
| D4 | 5.5 | Decision | Hệ thống | [5.5] Vai trò mới qua guard Admin? |
| A6 | 5.5 | Action | Hệ thống | [5.5] Lưu USER/ADMIN, audit và xử lý credential truy cập |
| A7 | 5.6-5.7 | Action | Admin | [5.6-5.7] Gửi yêu cầu đặt lại/gửi lại hướng dẫn kèm lý do |
| A8 | 5.6-5.7 | Action | Hệ thống | [5.6-5.7] Khởi tạo quy trình khôi phục mật khẩu |
| A9 | 5.8.1-5.8.2 | Action | Admin | [5.8.1-5.8.2] Chọn action hàng loạt, ID và lý do |
| D5 | 5.8.3 | Decision | Hệ thống | [5.8.3] Có tài khoản hợp lệ để tạo preview? |
| A10 | 5.8.3-5.8.4 | Action | Hệ thống | [5.8.3-5.8.4] Tạo preview và hiển thị ID thiếu |
| D6 | 5.8.5 | Decision | Admin | [5.8.5] Xác nhận hay hủy preview? |
| A11 | 5.8.6 | Action | Admin / Hệ thống | [5.8.6] Xác nhận và gửi operation ID |
| D7 | 5.8.6 | Decision | Hệ thống | [5.8.6] Preview còn hiệu lực và thao tác thành công? |
| A12 | 5.8.7/7 | Action | Hệ thống | [5.8.7/7] Hiển thị kết quả tổng hợp và tải lại danh sách |
| A13 | 2/5.1-5.8 | Action | Hệ thống | [2/5.1-5.8] Báo lỗi quyền, validation, preview hoặc hệ thống |
| F1 | 7 | Final | Hệ thống | Kết thúc thành công |
| F2 | 2/5.1-5.8 | Final | Hệ thống | Kết thúc thất bại; không báo thao tác hoàn tất |
| F3 | 5/5.8.5 | Final | Admin | Kết thúc do hủy trước khi gửi/xác nhận |


### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | Luôn |
| A1 | D8 | Danh sách được yêu cầu |
| D8 | D1 | [Danh sách tải thành công] |
| D8 | A13 | [Lỗi quyền/API/CSDL] |
| D1 | A2 | [Thao tác đơn] |
| D1 | A9 | [Thao tác hàng loạt] |
| D1 | F3 | [Hủy] |
| A2 | D2 | Chi tiết đã hiển thị |
| D2 | A3 | [Khóa/mở khóa/vô hiệu hóa/kích hoạt] |
| D2 | A5 | [Đổi vai trò hệ thống] |
| D2 | A7 | [Yêu cầu đặt lại/gửi lại hướng dẫn] |
| D2 | F3 | [Hủy hộp thoại] |
| A3 | D3 | Admin đã xác nhận lý do |
| D3 | A4 | [Trạng thái hợp lệ, không vi phạm guard] |
| D3 | A13 | [Tự khóa/tự vô hiệu hóa/Admin cuối/schema sai] |
| A4 | F1 | Cập nhật trạng thái thành công |
| A5 | D4 | Admin đã xác nhận vai trò và lý do |
| D4 | A6 | [Thay đổi hợp lệ, không tự hạ quyền/Admin cuối] |
| D4 | A13 | [Vi phạm guard hoặc schema] |
| A6 | F1 | Vai trò hệ thống đã lưu |
| A7 | A8 | Yêu cầu được gửi |
| A8 | F1 | Quy trình khôi phục đã khởi tạo; không bảo đảm email đã giao |
| A9 | D5 | Admin gửi action, danh sách ID và lý do |
| D5 | A10 | [Có ít nhất một tài khoản khớp] |
| D5 | A13 | [Không có ID hợp lệ/lỗi preview] |
| A10 | D6 | Preview tạo xong, hết hạn sau 15 phút |
| D6 | A11 | [Admin xác nhận] |
| D6 | F3 | [Admin hủy] |
| A11 | D7 | Backend nhận operation ID |
| D7 | A12 | [Preview hợp lệ và thao tác hoàn tất] |
| D7 | A13 | [Hết hạn/đã dùng/sai chủ sở hữu/lỗi thao tác] |
| A12 | F1 | Kết quả tổng hợp đã hiển thị |
| A13 | F2 | Lỗi hoặc từ chối không thể tiếp tục |

### Số liệu
Action=13, Decision=8, cạnh=33.

YÊU CẦU: Vẽ đúng node, cạnh, guard và swimlane; có Initial, Final thành công/thất bại/hủy. Không thêm thao tác quản lý phiên, không gọi yêu cầu đặt lại thành ép đổi mật khẩu. Báo rõ nếu phát hiện mâu thuẫn, không tự thêm nghiệp vụ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC06 - Kiểm soát truy cập của hệ thống Veriq bằng Visual Paradigm AI Chatbot, đầu ra PlantUML, nhãn Tiếng Việt. Mức chi tiết phù hợp khóa luận.

ĐẶC TẢ ĐẦY ĐỦ:

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

### Mô tả
Admin hệ thống quản lý trạng thái truy cập và vai trò hệ thống của tài khoản; khởi tạo quy trình đặt lại mật khẩu qua email; hoặc thao tác hàng loạt để vô hiệu hóa tài khoản/gửi hướng dẫn đặt lại. Vai trò hệ thống USER/ADMIN khác ma trận quyền dự án của UC07.

### Tiền điều kiện
- Admin đã đăng nhập và có quyền quản trị nền tảng.
- Với thao tác đơn, tài khoản đích tồn tại và Admin xem được chi tiết.
- Với thao tác hàng loạt, Admin chọn ít nhất một mã tài khoản và nêu lý do; danh sách có thể chứa ID không tồn tại, được báo ở preview.

### Hậu điều kiện
- Khóa, mở khóa, vô hiệu hóa, kích hoạt hoặc đổi vai trò: trạng thái/vai trò được cập nhật và audit được ghi. Khi khóa/vô hiệu hóa hoặc đổi system_role, code thu hồi credential truy cập; mở khóa/kích hoạt không gọi thu hồi. Đây là side effect, không phải chức năng quản lý phiên.
- Yêu cầu đặt lại mật khẩu: hệ thống khởi tạo luồng email UC04; không đặt mật khẩu mới thay người dùng và không khẳng định email đã được giao.
- Gửi lại theo nút đang có: code gọi cùng quy trình `forgot_password`; không thể khẳng định đó là thư xác minh kích hoạt.
- Bulk: thao tác chỉ chạy sau preview và xác nhận hợp lệ. Hệ thống lưu kết quả tổng hợp số tài khoản xử lý; không cung cấp bảng kết quả chi tiết từng email.
- Thất bại/hủy: lỗi được hiển thị; không báo thành công nếu cập nhật bị từ chối hoặc preview không còn hiệu lực. Không khẳng định rollback cho chuỗi tác vụ nhiều bước ngoài giao dịch được code bảo đảm.

### Tác nhân chính
Admin hệ thống.

### Tác nhân phụ
Dịch vụ email, nhận yêu cầu gửi hướng dẫn khôi phục mật khẩu. Không có tác nhân phiên/thiết bị.

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang quản lý tài khoản. | |
| 2 | | Kiểm tra quyền quản trị và hiển thị danh sách tài khoản. |
| 3 | Chọn tài khoản cần kiểm soát. | |
| 4 | | Hiển thị chi tiết, vai trò hệ thống và trạng thái hiện tại. |
| 5 | Chọn thao tác đơn hoặc thao tác hàng loạt. | |
| 6 | | Thực hiện một trong các nhánh thay thế 5.1–5.8. |
| 7 | | Hiển thị kết quả và tải lại dữ liệu khi thao tác thành công. |
| 8 | | Kết thúc UC. |

### Luồng sự kiện thay thế

**5.1. Khóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.1.1 | Chọn “Khóa tài khoản”. | |
| 5.1.2 | | Hiển thị hộp thoại yêu cầu lý do. |
| 5.1.3 | Nhập lý do và xác nhận. | |
| 5.1.4 | | Từ chối nếu Admin khóa chính mình hoặc làm mất Admin hoạt động cuối; nếu hợp lệ, đặt trạng thái LOCKED, thu hồi credential truy cập và ghi audit. |
| 5.1.5 | | Trả kết quả; giao diện cập nhật chi tiết/danh sách. Kết thúc nhánh. |

**5.2. Mở khóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.2.1 | Chọn “Mở khóa tài khoản”. | |
| 5.2.2 | Nhập lý do và xác nhận. | |
| 5.2.3 | | Đặt trạng thái ACTIVE, lưu lý do/audit và trả kết quả. |
| 5.2.4 | | Cập nhật giao diện; kết thúc nhánh. |

**5.3. Vô hiệu hóa tài khoản**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.3.1 | Chọn “Vô hiệu hóa tài khoản”. | |
| 5.3.2 | Nhập lý do và xác nhận. | |
| 5.3.3 | | Từ chối nếu Admin thao tác trên chính mình hoặc loại bỏ Admin hoạt động cuối; nếu hợp lệ, đặt trạng thái DISABLED, thu hồi credential truy cập và ghi audit. |
| 5.3.4 | | Hiển thị kết quả và cập nhật danh sách; kết thúc nhánh. |

**5.4. Kích hoạt tài khoản DISABLED**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.4.1 | Chọn “Kích hoạt tài khoản” trên tài khoản DISABLED. | |
| 5.4.2 | Nhập lý do và xác nhận. | |
| 5.4.3 | | Đặt trạng thái ACTIVE và ghi audit. |
| 5.4.4 | | Hiển thị kết quả; kết thúc nhánh. |

**5.5. Thay đổi vai trò hệ thống**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.5.1 | Chọn cấp hoặc hạ vai trò quản trị. | |
| 5.5.2 | Nhập lý do và xác nhận. | |
| 5.5.3 | | Từ chối tự hạ quyền Admin hiện tại hoặc làm mất Admin hoạt động cuối; nếu hợp lệ, lưu system_role USER/ADMIN, ghi audit và thu hồi credential truy cập theo hành vi code. |
| 5.5.4 | | Cập nhật giao diện; kết thúc nhánh. |

**5.6. Yêu cầu đặt lại mật khẩu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.6.1 | Chọn “Yêu cầu đặt lại mật khẩu”. | |
| 5.6.2 | Nhập lý do và xác nhận. | |
| 5.6.3 | | Khởi tạo luồng khôi phục UC04 cho email tài khoản, thu hồi credential truy cập theo hành vi code và ghi audit. |
| 5.6.4 | | Trả trạng thái xử lý yêu cầu; không khẳng định email đã được nhận. Kết thúc nhánh. |

**5.7. Gửi lại hướng dẫn qua email theo nút hiện có**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.7.1 | Chọn nút đang mang nhãn “Gửi lại quy trình kích hoạt”. | |
| 5.7.2 | Nhập lý do và xác nhận. | |
| 5.7.3 | | Gọi `forgot_password` cho tài khoản và ghi audit; đây là quy trình khôi phục mật khẩu theo code, không khẳng định gửi thư xác minh kích hoạt. |
| 5.7.4 | | Trả trạng thái xử lý; kết thúc nhánh. |

**5.8. Thao tác hàng loạt**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.8.1 | Chọn vô hiệu hóa hoặc gửi hướng dẫn đặt lại, nhập ID tài khoản và lý do. | |
| 5.8.2 | Chọn “Tạo bản xem trước”. | |
| 5.8.3 | | Loại ID trùng, tìm tài khoản tồn tại, ghi nhận ID thiếu và tạo preview hết hạn sau 15 phút. |
| 5.8.4 | | Hiển thị số tài khoản tìm thấy và ID không tồn tại. |
| 5.8.5 | Xác nhận thực hiện hoặc hủy. | |
| 5.8.6 | | Kiểm tra preview còn hạn, chưa dùng và do Admin hiện tại tạo; thực hiện thao tác trên các tài khoản hợp lệ. |
| 5.8.7 | | Trả trạng thái COMPLETED và số lượng đã xử lý; cập nhật danh sách. Kết thúc nhánh. |

### Luồng sự kiện ngoại lệ

- **5.1.4.1.** Admin tự khóa hoặc là Admin hoạt động cuối: từ chối; quay lại bước 5.1.1 hoặc kết thúc nếu Admin dừng.
- **5.3.3.1.** Admin tự vô hiệu hóa hoặc làm mất Admin hoạt động cuối: từ chối; quay lại bước 5.3.1 hoặc kết thúc.
- **5.5.3.1.** Admin tự hạ quyền hoặc làm mất Admin hoạt động cuối: từ chối; quay lại bước 5.5.1 hoặc kết thúc.
- **5.1.3/5.2.2/5.3.2/5.4.2/5.5.2/5.6.2/5.7.2/5.8.1.** Lý do thiếu hoặc không đạt schema (lý do 3–1000 ký tự; danh sách bulk 1–500 ID): API từ chối; quay lại form tương ứng.
- **3/5.** Tài khoản không tìm thấy hoặc Admin hết quyền: trả 404/401/403; kết thúc nhánh thất bại, không báo cập nhật thành công.
- **5.6.3/5.7.3.** Dịch vụ email lỗi được xử lý bên trong luồng khôi phục; response chung không chứng minh thư đã tới người nhận.
- **5.8.3.** Không tìm thấy ID nào hợp lệ: không có tài khoản để xử lý; yêu cầu nhập danh sách khác.
- **5.8.6.1.** Preview không tồn tại, đã hết hạn, đã dùng hoặc không thuộc Admin hiện tại: từ chối; quay lại bước 5.8.2 để tạo preview mới.
- **5.8.6.2.** Tài khoản đích là Admin cuối cùng trong thao tác vô hiệu hóa: guard từ chối cập nhật; không báo hoàn tất.
- **2/5.1–5.8.** Lỗi API/CSDL/hệ thống ngoài: hiển thị lỗi nếu có phản hồi; không khẳng định toàn bộ tác vụ nhiều bước đã rollback.
- **5.1.3/5.2.2/5.3.2/5.4.2/5.5.2/5.6.2/5.7.2/5.8.5.** Admin đóng hộp thoại hoặc hủy xác nhận trước khi gửi: không chạy thao tác tiếp theo.

### Giả định / Câu hỏi cần làm rõ
- Nhãn UI hiện tại có thể hàm ý đổi ngay; endpoint chỉ khởi tạo luồng khôi phục để người dùng tự đặt mật khẩu. Đặc tả dùng “Yêu cầu đặt lại mật khẩu”.
- Nút “Gửi lại quy trình kích hoạt” gọi service `forgot_password`, không gọi trực tiếp `issue_email_verification`; cần xác nhận lại ý định sản phẩm hoặc đổi nhãn UI.
- UI hiện hiển thị nút kích hoạt cho trạng thái khác ACTIVE/LOCKED; với tài khoản DELETED được ẩn danh, backend không có guard riêng trước khi chuyển status ACTIVE. Cần xác nhận chính sách và cân nhắc chặn thao tác này.
- Trong thao tác bulk, backend loại ID của Admin hiện hành khỏi tập xử lý khi xác nhận. Preview UI không nêu rõ mục bị loại; đặc tả không coi tài khoản Admin đó là đã xử lý.
- Bulk API có thêm action thu hồi phiên, nhưng giao diện không cung cấp action này và nó bị loại khỏi UC theo yêu cầu không đặc tả quản lý phiên.
- `confirm_bulk` chỉ trả số lượng tổng thể; không có bằng chứng giao diện nhận kết quả chi tiết theo từng email.

LIFELINE TỪ TRÁI SANG PHẢI: Admin, Giao diện quản trị, Backend quản trị (API và service), Cơ sở dữ liệu, Dịch vụ email.

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Admin | Giao diện quản trị | [1] moQuanLyTaiKhoan() | đồng bộ | chính |
| 2 | 2 | Giao diện quản trị | Backend quản trị | [2] layDanhSachTaiKhoan() | đồng bộ | chính |
| 3 | 2 | Backend quản trị | Cơ sở dữ liệu | [2] timDanhSachTaiKhoan() | đồng bộ | chính |
| 4 | 2 | Cơ sở dữ liệu | Backend quản trị | [2] traDanhSachTaiKhoan() | trả về | chính |
| 5 | 2 | Backend quản trị | Giao diện quản trị | [2] traDanhSachTaiKhoan() | trả về | chính |
| 6 | 2 | Giao diện quản trị | Admin | [2] hienThiDanhSach() | trả về | chính |
| 7 | 3-4 | Admin | Giao diện quản trị | [3-4] chonTaiKhoanVaXemChiTiet(userId) | đồng bộ | chính |
| 8 | 4 | Giao diện quản trị | Backend quản trị | [4] layChiTietTaiKhoan(userId) | đồng bộ | chính |
| 9 | 4 | Backend quản trị | Cơ sở dữ liệu | [4] docTaiKhoan(userId) | đồng bộ | chính |
| 10 | 4 | Cơ sở dữ liệu | Backend quản trị | [4] traChiTietVaTrangThai() | trả về | chính |
| 11 | 4 | Backend quản trị | Giao diện quản trị | [4] traChiTietTaiKhoan() | trả về | chính |
| 12 | 4 | Giao diện quản trị | Admin | [4] hienThiTrangThaiTaiKhoan() | trả về | chính |
| 13 | 5.1-5.7 | Admin | Giao diện quản trị | [5.1-5.7] chonThaoTacVaGuiLyDo() | đồng bộ | alt [status/role] / else [yêu cầu email] |
| 14 | 5.1-5.5 | Giao diện quản trị | Backend quản trị | [5.1-5.5] capNhatStatusHoacSystemRole(userId, payload) | đồng bộ | alt [status/role] |
| 15 | 5.1-5.5 | Backend quản trị | Cơ sở dữ liệu | [5.1-5.5] kiemTraAdminGuardVaLuuThayDoi() | đồng bộ | alt [thay đổi trạng thái/vai trò] |
| 16 | 5.1-5.5 | Cơ sở dữ liệu | Backend quản trị | [5.1-5.5] traKetQuaThayDoi() | trả về | alt [thành công/bị từ chối] |
| 17 | 5.1-5.5 | Backend quản trị | Giao diện quản trị | [5.1-5.5] traKetQuaStatusHoacRole() | trả về | alt [thành công/bị từ chối] |
| 18 | 5.1-5.5 | Giao diện quản trị | Admin | [5.1-5.5] hienThiKetQuaThayDoi() | trả về | alt [thành công/bị từ chối] |
| 19 | 5.6-5.7 | Giao diện quản trị | Backend quản trị | [5.6-5.7] khoiTaoForgotPassword(userId, reason) | đồng bộ | alt [yêu cầu đặt lại/gửi lại hướng dẫn] |
| 20 | 5.6-5.7 | Backend quản trị | Cơ sở dữ liệu | [5.6-5.7] taoMaKhoiPhucVaAudit() | đồng bộ | alt [tài khoản tồn tại] |
| 21 | 5.6-5.7 | Cơ sở dữ liệu | Backend quản trị | [5.6-5.7] traKetQuaTaoMa() | trả về | alt [tài khoản tồn tại] |
| 22 | 5.6-5.7 | Backend quản trị | Dịch vụ email | [5.6-5.7] guiHuongDanKhoiPhuc(email) | đồng bộ | opt [gửi email] |
| 23 | 5.6-5.7 | Dịch vụ email | Backend quản trị | [5.6-5.7] traTrangThaiGui() | trả về | opt [email thành công/lỗi được bắt] |
| 24 | 5.6-5.7 | Backend quản trị | Giao diện quản trị | [5.6-5.7] traTrangThaiYeuCau() | trả về | alt [đã khởi tạo] |
| 25 | 5.6-5.7 | Giao diện quản trị | Admin | [5.6-5.7] hienThiTrangThaiYeuCau() | trả về | alt [đã khởi tạo] |
| 26 | 5.8.1-5.8.2 | Admin | Giao diện quản trị | [5.8.1-5.8.2] guiActionIdsVaReason(action, ids, reason) | đồng bộ | alt [bulk preview] |
| 27 | 5.8.3 | Giao diện quản trị | Backend quản trị | [5.8.3] taoPreview(action, ids, reason) | đồng bộ | alt [bulk preview] |
| 28 | 5.8.3 | Backend quản trị | Cơ sở dữ liệu | [5.8.3] timIdsVaLuuPreview(expiresIn=15m) | đồng bộ | alt [bulk preview] |
| 29 | 5.8.3-5.8.4 | Cơ sở dữ liệu | Backend quản trị | [5.8.3-5.8.4] traIdsHopLeVaThieu() | trả về | alt [preview hợp lệ/không có kết quả] |
| 30 | 5.8.4 | Backend quản trị | Giao diện quản trị | [5.8.4] traTomTatPreview() | trả về | alt [preview tạo được] |
| 31 | 5.8.4 | Giao diện quản trị | Admin | [5.8.4] hienThiSoLuongHopLeVaThieu() | trả về | alt [preview tạo được] |
| 32 | 5.8.5 | Admin | Giao diện quản trị | [5.8.5] xacNhanHoacHuyPreview() | đồng bộ | alt [xác nhận] / else [hủy] |
| 33 | 5.8.6 | Giao diện quản trị | Backend quản trị | [5.8.6] xacNhanPreview(operationId) | đồng bộ | alt [xác nhận] |
| 34 | 5.8.6 | Backend quản trị | Cơ sở dữ liệu | [5.8.6] claimVaApDungBulkAction(operationId) | đồng bộ | alt [preview còn hiệu lực, đúng chủ] |
| 35 | 5.8.6 | Cơ sở dữ liệu | Backend quản trị | [5.8.6] traKetQuaBulk() | trả về | alt [hoàn tất/lỗi] |
| 36 | 5.8.6 | Backend quản trị | Dịch vụ email | [5.8.6] guiHuongDanDatLaiChoTaiKhoanHopLe() | đồng bộ | loop [action gửi hướng dẫn] |
| 37 | 5.8.6 | Dịch vụ email | Backend quản trị | [5.8.6] traKetQuaGui() | trả về | loop [mỗi tài khoản; lỗi gửi được bắt và tiếp tục] |
| 38 | 5.8.7 | Backend quản trị | Giao diện quản trị | [5.8.7] traTongSoDaXuLyHoacLoiPreview() | trả về | alt [hoàn tất/preview lỗi] |
| 39 | 5.8.7 | Giao diện quản trị | Admin | [5.8.7] hienThiKetQuaVaTaiLai() | trả về | alt [hoàn tất/preview lỗi] |


YÊU CẦU: Dùng activation bar, return và alt/opt/loop có guard. Giữ thứ tự message và mã bước. Không tách Repository; API và service đã gộp trong Backend quản trị. Không vẽ chức năng quản lý phiên. Không diễn đạt yêu cầu đặt lại thành ép đổi mật khẩu ngay. Đối chiếu L=5, M=39, F=6; báo nếu bộ đếm khác bảng.
```

## TỰ KIỂM TRA UC06

- [x] Phần 1 rà soát điểm rẽ, actor, quyền, trạng thái, lỗi và CRUD không áp dụng.
- [x] Phần 2 có đủ mô tả, tiền/hậu điều kiện, actor, luồng chính/thay thế/ngoại lệ và giả định.
- [x] Activity: Action=13, Decision=8, cạnh=33; mọi Decision có guard và node được nối.
- [x] Sequence: 5 lifeline, 39 message, 6 fragment; mỗi request đồng bộ có return ở nhánh tương ứng.
- [x] Prompt 5/6 chép đầy đủ đặc tả và bảng; không còn placeholder hoặc tham chiếu “như trên”.
## Bảng theo dõi sau UC06

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Chưa | Chưa | Chưa | Chưa |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC07 - Phân quyền

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1–2 | THIẾU | Đặc tả gốc nêu màn hình ma trận nhưng chưa chỉ rõ các vai trò, nguồn dữ liệu hay lỗi khi tải. | Nêu ba vai trò dự án BA, TESTER, SYSTEM_ADMIN; ma trận lấy từ cấu hình quyền hiện hành. Thêm trường hợp tải lỗi. |
| 3–4 | MƠ HỒ | “Điều chỉnh quyền” có thể bị hiểu là cho phép sửa cả vai trò Admin hoặc tạo quyền mới. | Ghi rõ giao diện khóa cột SYSTEM_ADMIN; Admin chỉ thay đổi danh sách quyền của BA và TESTER. Danh mục quyền hợp lệ lấy từ hệ thống, không cho tự tạo capability ở UC này. |
| 6–7 | THIẾU | “Kiểm tra hợp lệ” không chỉ ra các quy tắc hoặc xung đột đồng thời. | Đối chiếu revision, tập vai trò phải đúng, quyền phải thuộc danh mục capability đã khai báo; cập nhật có điều kiện theo revision để tránh ghi đè. |
| 7 | THIẾU | Chưa nêu các tác quả phụ khi lưu thành công. | Ghi tăng revision, làm mới access policy cache và tạo audit record; sau đó trả ma trận đã lưu. |
| Ngoại lệ | THIẾU | Chưa có lỗi 401/403, dữ liệu cấu hình không hợp lệ, lỗi lưu trữ hoặc người dùng bỏ thao tác. | Thêm các nhánh áp dụng; không suy diễn thông báo UI cụ thể ngoài dữ liệu lỗi mà giao diện nhận được. |
| Toàn UC | MƠ HỒ | Gọi tác nhân là “Admin” có thể lẫn với vai trò dự án SYSTEM_ADMIN. | Dùng “Admin hệ thống”; đây là quyền quản trị nền tảng, khác với vai trò dự án trong ma trận. |
| CRUD | Không áp dụng | UC thay đổi cấu hình quyền, không phải quản lý đối tượng có đủ CRUD. | Không thêm Xem chi tiết, Thêm hoặc Xóa giả định. Màn hình tải/xem danh sách quyền hiện có và cập nhật ma trận. |

Đã kiểm: **2 điểm rẽ, 4 nhánh, 6 tình huống lỗi** (chưa đăng nhập/hết thông tin xác thực, không đủ quyền, revision xung đột, vai trò không khớp, capability không hợp lệ, lỗi cơ sở dữ liệu/dịch vụ). Chức năng CRUD đầy đủ không áp dụng. Mã nguồn cho thấy chỉ Admin hệ thống được đọc/ghi ma trận; ba vai trò dự án là BA, TESTER và SYSTEM_ADMIN; cột SYSTEM_ADMIN bị khóa trên giao diện.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Admin hệ thống xem ma trận quyền dự án và cập nhật tập quyền gán cho các vai trò BA và TESTER. Cấu hình được kiểm tra theo danh mục capability và phiên bản hiện hành.

**Tiền điều kiện:** Admin hệ thống đã xác thực và có quyền quản trị nền tảng. Cấu hình kiểm soát truy cập dự án đang tồn tại.

**Hậu điều kiện:**
- Thành công: ma trận hợp lệ được lưu với revision tăng một đơn vị; access policy được làm mới và thao tác được ghi audit.
- Thất bại: cấu hình hiện tại không bị ghi đè; giao diện nhận lỗi tương ứng.
- Bỏ thao tác: thay đổi chưa lưu chỉ tồn tại ở giao diện và không làm đổi cấu hình.

**Tác nhân chính:** Admin hệ thống.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở khu vực quản trị và mục quyền theo vai trò dự án. | |
| 2 | | Xác thực quyền Admin hệ thống và tải danh mục quyền, ma trận BA/TESTER/SYSTEM_ADMIN cùng revision hiện tại. |
| 3 | Xem ma trận quyền. | Hiển thị danh sách capability; khóa chỉnh sửa cột SYSTEM_ADMIN. |
| 4 | Chọn hoặc bỏ chọn quyền ở cột BA hoặc TESTER. | Cập nhật bản nháp trên giao diện; chưa ghi xuống máy chủ. |
| 5 | Chọn “Lưu phân quyền”. | Gửi ma trận cùng revision đã tải. |
| 6 | | Kiểm tra revision, vai trò bắt buộc và các capability được khai báo. |
| 7 | | Ghi cấu hình theo điều kiện revision hiện tại, tăng revision, làm mới access policy và ghi audit. |
| 8 | | Trả ma trận cùng revision mới; giao diện cập nhật dữ liệu đã lưu và báo thành công. Kết thúc UC. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 4.1 | Rời trang hoặc không chọn Lưu. | Bản nháp không được gửi; kết thúc UC, cấu hình đã lưu không thay đổi. |
| 6.1 | | Nếu revision đã thay đổi bởi thao tác khác, từ chối cập nhật và trả lỗi xung đột; giao diện báo lỗi. Quay lại bước 2 để tải cấu hình mới trước khi chỉnh sửa lại. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Nếu thông tin xác thực không còn hiệu lực, từ chối yêu cầu; kết thúc UC thất bại. Không mô hình hóa quản lý phiên đăng nhập. |
| 2.2 | | Nếu người dùng không phải Admin hệ thống, trả lỗi 403; kết thúc UC thất bại. |
| 2.3 | | Nếu không tải được cấu hình do lỗi dịch vụ/CSDL, giao diện báo không thể tải; kết thúc UC thất bại. |
| 6.2 | | Nếu tập vai trò khác chính xác BA, TESTER, SYSTEM_ADMIN, hoặc quyền tham chiếu capability không tồn tại, từ chối lưu; giao diện báo lỗi. Quay lại bước 2 để tải dữ liệu hợp lệ. |
| 7.1 | | Nếu ghi CSDL thất bại, giữ nguyên cấu hình cũ, trả lỗi; kết thúc UC thất bại. |

**Giả định / Câu hỏi cần làm rõ:** Mã nguồn thể hiện tên nhóm quyền “BA” và “TESTER”, đồng thời định danh “SYSTEM_ADMIN” cho quyền quản trị hệ thống. Cần xác nhận với giảng viên/đơn vị rằng trong luận văn có nên Việt hóa nhãn hai vai trò đầu hay giữ nguyên mã vai trò. Không suy diễn rằng sửa ma trận sẽ thay đổi quyền của mọi người dùng ngay lập tức ngoài việc làm mới policy cache.

## PHẦN 3 - PHÂN RÃ ACTIVITY (chưa vẽ)

Mô hình ở mức quy trình người dùng, không đưa kiểm tra nội bộ thành hàng chục node riêng. Mỗi nhánh thể hiện kết quả có ý nghĩa đối với người thao tác.

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| A0 | Không áp dụng | Initial | Người dùng | Bắt đầu, tiền điều kiện Admin hệ thống đã xác thực |
| A1 | 1 | Action | Người dùng | 1 Mở mục quyền theo vai trò |
| A2 | 2 | Action | Hệ thống | 2 Tải ma trận và revision |
| D1 | 2 | Decision | Hệ thống | Admin hệ thống được phép? |
| A3 | 2.2 | Action | Hệ thống | 2.2 Báo từ chối truy cập |
| F0 | Không áp dụng | Final | Hệ thống | Kết thúc thất bại: không đủ quyền |
| A4 | 3 | Action | Hệ thống | 3 Hiển thị ma trận quyền |
| A5 | 4 | Action | Người dùng | 4 Chỉnh quyền BA hoặc TESTER |
| D2 | 4.1 | Decision | Người dùng | Người dùng tiếp tục chỉnh và lưu? |
| F1 | Không áp dụng | Final | Người dùng | Kết thúc chưa lưu: cấu hình không đổi |
| A6 | 5 | Action | Người dùng | 5 Gửi ma trận và revision |
| D3 | 6 | Decision | Hệ thống | Revision và capability hợp lệ? |
| A7 | 6.1 | Action | Hệ thống | 6.1 Báo xung đột hoặc dữ liệu quyền không hợp lệ |
| A8 | 6.1.1 | Action | Người dùng | 6.1.1 Tải lại ma trận để sửa |
| A9 | 7 | Action | Hệ thống | 7 Lưu ma trận, tăng revision, làm mới policy và ghi audit |
| D4 | 7 | Decision | Hệ thống | Ghi cấu hình thành công? |
| A10 | 7.1 | Action | Hệ thống | 7.1 Báo lỗi lưu, giữ cấu hình cũ |
| F2 | Không áp dụng | Final | Hệ thống | Kết thúc thất bại: không đổi cấu hình |
| A11 | 8 | Action | Hệ thống | 8 Trả ma trận và revision mới |
| A12 | 8.1 | Action | Người dùng | 8.1 Xem thông báo lưu thành công |
| F3 | Không áp dụng | Final | Hệ thống | Kết thúc thành công |
| A13 | 2.3 | Action | Hệ thống | 2.3 Báo lỗi tải cấu hình |
| F4 | Không áp dụng | Final | Hệ thống | Kết thúc thất bại: không tải được dữ liệu |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| A0 | A1 | Bắt đầu UC |
| A1 | A2 | Luôn luôn |
| A2 | D1 | Yêu cầu tải được xử lý |
| D1 | A4 | [Admin hệ thống hợp lệ] |
| D1 | A3 | [Không có quyền Admin hệ thống] |
| A3 | F0 | Luôn luôn |
| A4 | A5 | Ma trận đã hiển thị |
| A5 | D2 | Người dùng đã xem/chỉnh bản nháp |
| D2 | A6 | [Chọn lưu] |
| D2 | F1 | [Rời trang hoặc bỏ lưu] |
| A6 | D3 | Máy chủ nhận dữ liệu |
| D3 | A9 | [Revision hiện hành và dữ liệu hợp lệ] |
| D3 | A7 | [Xung đột revision hoặc capability/role không hợp lệ] |
| A7 | A8 | Lỗi có thể khắc phục bằng tải lại |
| A8 | A2 | [Tải lại để sửa] |
| A9 | D4 | Kết quả ghi dữ liệu |
| D4 | A11 | [Ghi thành công] |
| D4 | A10 | [Lỗi lưu trữ] |
| A10 | F2 | Luôn luôn |
| A11 | A12 | Phản hồi thành công |
| A12 | F3 | Luôn luôn |
| A2 | A13 | [Lỗi tải cấu hình/CSDL] |
| A13 | F4 | Luôn luôn |

**Số liệu Activity:** N = 8 ô đặc tả có nội dung; M = 13 Action; D = 4 Decision; E = 22 cạnh. Không tính Initial, Merge hoặc Final vào số Action. Mỗi nhánh kết thúc ở trạng thái phù hợp; vòng tải lại quay về bước 2.

## PHẦN 4 - PHÂN RÃ SEQUENCE (chưa vẽ)

### 4a. Lifeline trái sang phải

1. Admin hệ thống
2. Giao diện quản trị
3. API quyền dự án
4. CSDL cấu hình quyền

Không có hệ thống ngoài. API bao gồm phần xác thực, kiểm tra và ghi audit ở cùng biên dịch vụ để sơ đồ giữ ở mức luận văn; thao tác audit chỉ xảy ra sau khi lưu thành công.

### 4b. Bảng message theo thời gian

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---|---|---|---|---|---|---|
| 1 | 1 | Admin hệ thống | Giao diện quản trị | 1 moQuyenVaiTro() | đồng bộ | Không áp dụng |
| 2 | 2 | Giao diện quản trị | API quyền dự án | 2 layMaTran() | đồng bộ | Không áp dụng |
| 3 | 2 | API quyền dự án | CSDL cấu hình quyền | 2 selectActivePolicy() | đồng bộ | Không áp dụng |
| 4 | 2 | CSDL cấu hình quyền | API quyền dự án | 2 policy, revision | trả về | Không áp dụng |
| 5 | 2 | API quyền dự án | Giao diện quản trị | 2 maTran, danhMucQuyen | trả về | Không áp dụng |
| 6 | 3 | Giao diện quản trị | Admin hệ thống | 3 hienThiMaTran() | trả về | Không áp dụng |
| 7 | 4 | Admin hệ thống | Giao diện quản trị | 4 thayDoiQuyen(role, capability) | đồng bộ | Không áp dụng |
| 8 | 4 | Giao diện quản trị | Admin hệ thống | 4 capNhatBanNhap() | trả về | Không áp dụng |
| 9 | 5 | Admin hệ thống | Giao diện quản trị | 5 yeuCauLuu() | đồng bộ | Không áp dụng |
| 10 | 5 | Giao diện quản trị | API quyền dự án | 5 capNhatMaTran(revision, role_permissions) | đồng bộ | Không áp dụng |
| 11 | 6 | API quyền dự án | API quyền dự án | 6 kiemTraRevisionVaCapability() | tự gọi | alt hợp lệ / không hợp lệ |
| 12 | 6 | API quyền dự án | CSDL cấu hình quyền | 6 selectActivePolicy(revision) | đồng bộ | alt hợp lệ / xung đột |
| 13 | 6 | CSDL cấu hình quyền | API quyền dự án | 6 policyHienHanh | trả về | alt hợp lệ / xung đột |
| 14 | 6.1 | API quyền dự án | Giao diện quản trị | 6.1 traLoiLoi(409/422) | trả về | alt dữ liệu không hợp lệ |
| 15 | 6.1 | Giao diện quản trị | Admin hệ thống | 6.1 hienThiLoiVaYeuCauTaiLai() | trả về | alt dữ liệu không hợp lệ |
| 16 | 7 | API quyền dự án | CSDL cấu hình quyền | 7 updatePolicyNeuRevisionKhop() | đồng bộ | alt cập nhật thành công / lỗi |
| 17 | 7 | CSDL cấu hình quyền | API quyền dự án | 7 ketQuaCapNhat | trả về | alt cập nhật thành công / lỗi |
| 18 | 7.1 | API quyền dự án | Giao diện quản trị | 7.1 traLoiLoiLuu() | trả về | alt lỗi ghi |
| 19 | 7.1 | Giao diện quản trị | Admin hệ thống | 7.1 hienThiLoiLuu() | trả về | alt lỗi ghi |
| 20 | 7 | API quyền dự án | API quyền dự án | 7 lamMoiPolicyVaGhiAudit() | tự gọi | alt cập nhật thành công |
| 21 | 8 | API quyền dự án | Giao diện quản trị | 8 traMaTranVaRevisionMoi() | trả về | alt cập nhật thành công |
| 22 | 8 | Giao diện quản trị | Admin hệ thống | 8 hienThiThanhCong() | trả về | alt cập nhật thành công |
| 23 | 4.1 | Admin hệ thống | Giao diện quản trị | 4.1 boThayDoi() | đồng bộ | opt không lưu |
| 24 | 4.1 | Giao diện quản trị | Admin hệ thống | 4.1 ketThucKhongLuu() | trả về | opt không lưu |
| 25 | 2.3 | API quyền dự án | Giao diện quản trị | 2.3 traLoiLoiTai() | trả về | alt lỗi tải |
| 26 | 2.3 | Giao diện quản trị | Admin hệ thống | 2.3 hienThiLoiTai() | trả về | alt lỗi tải |

**Số liệu Sequence:** N = 8 ô đặc tả có nội dung; M = 26 message; F = 4 fragment; L = 4 lifeline. Các lời gọi API/CSDL có phản hồi được thể hiện. Kiểm tra quyền được mô tả tại biên API; không vẽ message nào gọi nhảy tầng.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML ACTIVITY DIAGRAM cho UC07 - Phân quyền của hệ thống Veriq, định dạng PlantUML, nhãn Tiếng Việt. Dùng swimlane Người dùng và Hệ thống.

ĐẶC TẢ
Mô tả: Admin hệ thống xem ma trận quyền dự án và cập nhật tập quyền gán cho các vai trò BA và TESTER. Cấu hình được kiểm tra theo danh mục capability và revision hiện hành.
Tiền điều kiện: Admin hệ thống đã xác thực và cấu hình kiểm soát truy cập dự án đang tồn tại.
Hậu điều kiện thành công: ma trận hợp lệ được lưu với revision tăng một; access policy được làm mới và thao tác được ghi audit.
Hậu điều kiện thất bại: cấu hình cũ không bị ghi đè; giao diện nhận lỗi tương ứng.
Tác nhân: Admin hệ thống. Không có tác nhân phụ.
Luồng chính: (1) Mở mục quyền theo vai trò. (2) Hệ thống tải danh mục quyền, ma trận BA/TESTER/SYSTEM_ADMIN và revision. (3) Hiển thị ma trận, khóa cột SYSTEM_ADMIN. (4) Admin chọn hoặc bỏ chọn quyền BA/TESTER, chỉ tạo bản nháp giao diện. (5) Gửi ma trận và revision khi chọn Lưu. (6) Hệ thống kiểm tra revision, role và capability. (7) Lưu có điều kiện revision, tăng revision, làm mới policy, ghi audit. (8) Trả kết quả và báo thành công.
Nhánh: (4.1) bỏ lưu thì kết thúc, không đổi cấu hình. (6.1) conflict revision hoặc role/capability không hợp lệ thì báo lỗi và quay lại bước 2. Ngoại lệ: (2.1) thông tin xác thực hết hiệu lực, kết thúc thất bại; (2.2) không có quyền Admin hệ thống, kết thúc thất bại; (2.3) lỗi tải, kết thúc thất bại; (7.1) lỗi ghi, giữ cấu hình cũ và kết thúc thất bại.

BẢNG NODE
| ID | Loại | Swimlane | Nhãn |
| A0 | Initial | Người dùng | Bắt đầu, Admin hệ thống đã xác thực |
| A1 | Action | Người dùng | 1 Mở mục quyền theo vai trò |
| A2 | Action | Hệ thống | 2 Tải ma trận và revision |
| D1 | Decision | Hệ thống | Admin hệ thống được phép? |
| A3 | Action | Hệ thống | 2.2 Báo từ chối truy cập |
| F0 | Final | Hệ thống | Kết thúc thất bại: không đủ quyền |
| A4 | Action | Hệ thống | 3 Hiển thị ma trận quyền |
| A5 | Action | Người dùng | 4 Chỉnh quyền BA hoặc TESTER |
| D2 | Decision | Người dùng | Người dùng tiếp tục chỉnh và lưu? |
| F1 | Final | Người dùng | Kết thúc chưa lưu: cấu hình không đổi |
| A6 | Action | Người dùng | 5 Gửi ma trận và revision |
| D3 | Decision | Hệ thống | Revision và capability hợp lệ? |
| A7 | Action | Hệ thống | 6.1 Báo xung đột hoặc dữ liệu không hợp lệ |
| A8 | Action | Người dùng | 6.1.1 Tải lại ma trận để sửa |
| A9 | Action | Hệ thống | 7 Lưu ma trận, tăng revision, làm mới policy và ghi audit |
| D4 | Decision | Hệ thống | Ghi cấu hình thành công? |
| A10 | Action | Hệ thống | 7.1 Báo lỗi lưu, giữ cấu hình cũ |
| F2 | Final | Hệ thống | Kết thúc thất bại: không đổi cấu hình |
| A11 | Action | Hệ thống | 8 Trả ma trận và revision mới |
| A12 | Action | Người dùng | 8.1 Xem thông báo lưu thành công |
| F3 | Final | Hệ thống | Kết thúc thành công |
| A13 | Action | Hệ thống | 2.3 Báo lỗi tải cấu hình |
| F4 | Final | Hệ thống | Kết thúc thất bại: không tải được dữ liệu |

BẢNG CẠNH
| Từ | Đến | Guard |
| A0 | A1 | Bắt đầu UC |
| A1 | A2 | Luôn luôn |
| A2 | D1 | Yêu cầu tải đã xử lý |
| D1 | A4 | [Admin hệ thống hợp lệ] |
| D1 | A3 | [Không có quyền Admin hệ thống] |
| A3 | F0 | Luôn luôn |
| A4 | A5 | Ma trận đã hiển thị |
| A5 | D2 | Bản nháp đã chỉnh hoặc giữ nguyên |
| D2 | A6 | [Chọn lưu] |
| D2 | F1 | [Bỏ lưu hoặc rời trang] |
| A6 | D3 | Máy chủ đã nhận dữ liệu |
| D3 | A9 | [Revision và dữ liệu hợp lệ] |
| D3 | A7 | [Conflict hoặc dữ liệu quyền không hợp lệ] |
| A7 | A8 | Có thể tải lại dữ liệu |
| A8 | A2 | [Tải lại để sửa] |
| A9 | D4 | Kết quả ghi dữ liệu |
| D4 | A11 | [Ghi thành công] |
| D4 | A10 | [Lỗi lưu trữ] |
| A10 | F2 | Luôn luôn |
| A11 | A12 | Phản hồi thành công |
| A12 | F3 | Luôn luôn |
| A2 | A13 | [Lỗi tải cấu hình/CSDL] |
| A13 | F4 | Luôn luôn |

YÊU CẦU: Vẽ đúng các node/cạnh/guard trên, không thêm nghiệp vụ; hiển thị Initial và các Final riêng biệt; không node treo. Kiểm tra số Action=13, Decision=4, cạnh=22 và báo đối chiếu cuối sơ đồ. Không dùng dấu lược bỏ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML SEQUENCE DIAGRAM cho UC07 - Phân quyền của hệ thống Veriq, định dạng PlantUML, nhãn Tiếng Việt.

ĐẶC TẢ
Mô tả: Admin hệ thống xem ma trận quyền dự án và cập nhật quyền của BA, TESTER. SYSTEM_ADMIN hiển thị nhưng không chỉnh được trên giao diện.
Tiền điều kiện: Admin hệ thống đã xác thực; cấu hình quyền dự án tồn tại.
Hậu điều kiện thành công: lưu cấu hình mới, tăng revision, làm mới access policy, ghi audit. Thất bại: không ghi đè cấu hình cũ.
Tác nhân: Admin hệ thống. Tác nhân phụ: không có.
Luồng: (1) mở mục quyền. (2) giao diện gọi API tải danh mục, ma trận, revision. (3) hiển thị. (4) Admin chỉnh bản nháp BA/TESTER. (5) gửi ma trận và revision. (6) API kiểm tra revision, role và capability. (7) cập nhật CSDL có điều kiện; nếu thành công làm mới policy và ghi audit. (8) trả kết quả, hiển thị thành công.
Nhánh thay thế/ngoại lệ: bỏ lưu thì kết thúc không đổi cấu hình; revision xung đột hoặc dữ liệu quyền không hợp lệ trả lỗi và yêu cầu tải lại; mất xác thực, không đủ Admin hoặc lỗi tải thì báo thất bại; lỗi ghi giữ cấu hình cũ và báo lỗi.

LIFELINE trái sang phải: Admin hệ thống | Giao diện quản trị | API quyền dự án | CSDL cấu hình quyền.

BẢNG MESSAGE
| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
| 1 | 1 | Admin hệ thống | Giao diện quản trị | 1 moQuyenVaiTro() | đồng bộ | Không áp dụng |
| 2 | 2 | Giao diện quản trị | API quyền dự án | 2 layMaTran() | đồng bộ | Không áp dụng |
| 3 | 2 | API quyền dự án | CSDL cấu hình quyền | 2 selectActivePolicy() | đồng bộ | alt tải thành công/lỗi |
| 4 | 2 | CSDL cấu hình quyền | API quyền dự án | 2 policy, revision | trả về | alt tải thành công/lỗi |
| 5 | 2 | API quyền dự án | Giao diện quản trị | 2 maTran, danhMucQuyen | trả về | alt tải thành công/lỗi |
| 6 | 3 | Giao diện quản trị | Admin hệ thống | 3 hienThiMaTran() | trả về | Không áp dụng |
| 7 | 4 | Admin hệ thống | Giao diện quản trị | 4 thayDoiQuyen(role, capability) | đồng bộ | opt chỉnh sửa |
| 8 | 4 | Giao diện quản trị | Admin hệ thống | 4 capNhatBanNhap() | trả về | opt chỉnh sửa |
| 9 | 5 | Admin hệ thống | Giao diện quản trị | 5 yeuCauLuu() | đồng bộ | alt lưu/bỏ lưu |
| 10 | 5 | Giao diện quản trị | API quyền dự án | 5 capNhatMaTran(revision, role_permissions) | đồng bộ | alt lưu |
| 11 | 6 | API quyền dự án | API quyền dự án | 6 kiemTraRevisionVaCapability() | tự gọi | alt hợp lệ/conflict |
| 12 | 6 | API quyền dự án | CSDL cấu hình quyền | 6 selectActivePolicy(revision) | đồng bộ | alt hợp lệ/conflict |
| 13 | 6 | CSDL cấu hình quyền | API quyền dự án | 6 policyHienHanh | trả về | alt hợp lệ/conflict |
| 14 | 6.1 | API quyền dự án | Giao diện quản trị | 6.1 traLoiLoi(409/422) | trả về | alt conflict/không hợp lệ |
| 15 | 6.1 | Giao diện quản trị | Admin hệ thống | 6.1 hienThiLoiVaYeuCauTaiLai() | trả về | alt conflict/không hợp lệ |
| 16 | 7 | API quyền dự án | CSDL cấu hình quyền | 7 updatePolicyNeuRevisionKhop() | đồng bộ | alt thành công/lỗi ghi |
| 17 | 7 | CSDL cấu hình quyền | API quyền dự án | 7 ketQuaCapNhat | trả về | alt thành công/lỗi ghi |
| 18 | 7.1 | API quyền dự án | Giao diện quản trị | 7.1 traLoiLoiLuu() | trả về | alt lỗi ghi |
| 19 | 7.1 | Giao diện quản trị | Admin hệ thống | 7.1 hienThiLoiLuu() | trả về | alt lỗi ghi |
| 20 | 7 | API quyền dự án | API quyền dự án | 7 lamMoiPolicyVaGhiAudit() | tự gọi | alt thành công |
| 21 | 8 | API quyền dự án | Giao diện quản trị | 8 traMaTranVaRevisionMoi() | trả về | alt thành công |
| 22 | 8 | Giao diện quản trị | Admin hệ thống | 8 hienThiThanhCong() | trả về | alt thành công |
| 23 | 4.1 | Admin hệ thống | Giao diện quản trị | 4.1 boThayDoi() | đồng bộ | opt bỏ lưu |
| 24 | 4.1 | Giao diện quản trị | Admin hệ thống | 4.1 ketThucKhongLuu() | trả về | opt bỏ lưu |
| 25 | 2.3 | API quyền dự án | Giao diện quản trị | 2.3 traLoiLoiTai() | trả về | alt lỗi tải |
| 26 | 2.3 | Giao diện quản trị | Admin hệ thống | 2.3 hienThiLoiTai() | trả về | alt lỗi tải |

YÊU CẦU: Vẽ đúng thứ tự, lifeline, message, return và fragment có guard. Dùng activation bar. Không gọi nhảy tầng. Không mô hình hóa quản lý phiên. Kiểm tra lifeline=4, message=26, fragment=4; nếu khác thì báo rõ. Không thêm nghiệp vụ hoặc lược bỏ message.
```

## TỰ KIỂM TRA UC07

- [x] Phần 1 nêu vấn đề cụ thể, tình huống lỗi và phạm vi CRUD.
- [x] Phần 2 có đủ mô tả, tiền/hậu điều kiện, tác nhân, luồng chính/thay thế/ngoại lệ và giả định.
- [x] Activity có 13 Action, 4 Decision, 22 cạnh; tất cả Decision có guard.
- [x] Sequence có 4 lifeline, 26 message, 4 fragment; có return cho lời gọi đồng bộ và nhánh lỗi.
- [x] Prompt chứa đặc tả, bảng node/cạnh hoặc message độc lập, không dùng “như trên”.
- [x] Không thêm UC quản lý phiên đăng nhập.
## Bảng theo dõi sau UC07

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC08 - Quản lý dự án

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | Luồng danh sách chưa nói rõ tìm kiếm, lọc trạng thái, phạm vi dự án người dùng được xem và giới hạn kết quả. | Ghi tìm theo mã/tên, lọc trạng thái và giới hạn danh sách theo quyền hiện hành; giao diện chia trang từ kết quả trả về. |
| 3-8 | MÂU THUẪN | Giao diện gửi trường `project_owner_user_id`, nhưng schema `ProjectCreate` không khai báo trường này; service gán người tạo làm trưởng dự án. | Ghi rõ lựa chọn Chủ dự án ở giao diện hiện không được lưu qua API tại commit nguồn. Không khẳng định người được chọn thành chủ dự án; giữ riêng sự kiện người tạo trở thành trưởng dự án. |
| 3.3 | THIẾU | Cập nhật thiếu kiểm soát revision, quyền sửa trưởng dự án và tính hợp lệ lịch. | Bổ sung revision hiện hành, yêu cầu trưởng dự án mới là thành viên ACTIVE, ngày kết thúc phải sau ngày bắt đầu. |
| 3.4-3.6 | MƠ HỒ | Lưu trữ, khôi phục và xóa cứng đang bị trình bày như các thao tác CRUD ngang nhau. | Phân biệt lưu trữ/khôi phục qua quyền dự án với xóa cứng qua giao diện quản trị nội bộ. Xóa cứng xác nhận bằng đúng mã dự án; payload backend không nhận lý do dù hộp thoại giao diện có trường này. |
| Toàn UC | THIẾU | Thiếu lỗi quyền, dự án không tồn tại, trùng mã, dữ liệu lịch sai, xung đột revision, lỗi dịch vụ/CSDL và hủy trước khi gửi. | Thêm các nhánh phù hợp trong đặc tả; không mô tả quản lý phiên. |
| CRUD | MƠ HỒ | “Quản lý dự án” chưa tách xem/tìm, chi tiết, tạo, sửa, lưu trữ, khôi phục và xóa cứng. | Nêu riêng từng mục trong nhánh hoạt động; không gộp cập nhật hồ sơ với chuyển trạng thái. |

Đã kiểm: **7 điểm rẽ nghiệp vụ, 7 nhánh và 8 tình huống lỗi** (hết xác thực/không đủ quyền, mã trùng, dữ liệu bắt buộc hoặc lịch sai, trưởng dự án không còn là thành viên ACTIVE, revision xung đột, không tìm thấy dự án, lỗi dịch vụ/CSDL, hủy biểu mẫu). CRUD được phân loại theo hành vi thực tế. Có một điểm chưa thống nhất về lý do xóa cứng, ghi rõ bên dưới.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người dùng có quyền xem danh sách dự án được cấp, tìm kiếm/lọc, xem chi tiết, tạo và cập nhật dự án, lưu trữ hoặc khôi phục dự án. Admin vận hành nội bộ có thể xóa cứng dự án qua giao diện quản trị nền tảng.

**Tiền điều kiện:** Người dùng đã xác thực. Thao tác trên dự án yêu cầu quyền tương ứng. Tạo dự án phụ thuộc chính sách tạo hiện hành. Xóa cứng yêu cầu quyền truy cập giao diện quản trị nội bộ.

**Hậu điều kiện:**
- Thành công: danh sách/chi tiết được trả về; hoặc dự án được tạo, cập nhật, lưu trữ/khôi phục theo thao tác. Khi tạo, người tạo được đặt làm trưởng dự án và thành viên ban đầu. Xóa cứng chỉ xảy ra sau khi mã xác nhận khớp mã dự án.
- Lựa chọn Chủ dự án trong giao diện tạo hiện chưa được lưu ở backend theo schema tại commit nguồn.
- Thất bại: dữ liệu dự án không đổi nếu thao tác bị từ chối hoặc lưu thất bại.
- Hủy: đóng biểu mẫu/hộp thoại trước khi gửi thì không thay đổi dữ liệu.

**Tác nhân chính:** Người dùng có quyền dự án tương ứng.

**Tác nhân phụ:** Admin vận hành nền tảng đối với xóa cứng; quyền này được bảo vệ qua tuyến quản trị nội bộ, không phải quyền dự án thông thường.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang danh sách dự án. | |
| 2 | | Tải và hiển thị các dự án người dùng được xem; mặc định trạng thái đang hoạt động. |
| 3 | Tìm theo mã/tên hoặc lọc trạng thái; chọn một dự án hoặc thao tác tạo mới. | |
| 4 | | Trả danh sách phù hợp hoặc mở trang chi tiết dự án được chọn. |
| 5 | Chọn tạo mới, sửa, lưu trữ hoặc khôi phục tùy quyền và trạng thái. | |
| 6 | Nhập dữ liệu/lý do cần thiết và xác nhận thao tác. | |
| 7 | | Kiểm tra quyền, dữ liệu và revision; ngày kết thúc dự kiến phải sau ngày bắt đầu. Khi tạo, người tạo trở thành trưởng dự án; trường Chủ dự án do UI gửi hiện không được schema nhận. |
| 8 | | Ghi thao tác hợp lệ và trả kết quả; lưu trữ/khôi phục giữ lại dữ liệu dự án. |
| 9 | | Làm mới danh sách hoặc chi tiết và thông báo kết quả. Kết thúc UC. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Chọn một dự án để xem. | Tải và hiển thị tổng quan/chi tiết theo quyền đọc; kết thúc UC hoặc quay về bước 2. |
| 3.2 | Tìm mã hoặc tên, chọn trạng thái. | Lọc danh sách theo điều kiện; quay lại bước 2 với kết quả phù hợp. |
| 5.1 | Chọn tạo dự án. | Hiển thị biểu mẫu gồm mã, tên, loại, mô tả, locale, timezone, cấu hình và lịch dự kiến. Quay lại bước 6. |
| 5.2 | Chọn lưu trữ hoặc khôi phục. | Yêu cầu lý do; khi xác nhận, xử lý ở bước 7-9. Lý do có độ dài 2-2000 ký tự theo schema. |
| 5.3 | Admin vận hành mở xóa cứng và nhập mã dự án xác nhận. | Nếu mã khớp, quản trị nội bộ xóa dự án và dữ liệu liên quan; cập nhật danh sách. Kết thúc UC. |
| 6.1 | Hủy biểu mẫu/hộp thoại trước khi gửi. | Đóng biểu mẫu, không ghi dữ liệu; kết thúc UC. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Thông tin xác thực hết hiệu lực hoặc không đủ quyền: từ chối tải/tác vụ, báo lỗi phù hợp và kết thúc thất bại. |
| 4.1 | | Dự án không tồn tại hoặc không thuộc phạm vi được xem: báo không tìm thấy/không truy cập được; kết thúc thất bại. |
| 7.1 | | Mã dự án trùng, trường sai/thiếu hoặc ngày kết thúc không sau ngày bắt đầu: báo lỗi và quay lại bước 6. |
| 7.2 | | Trưởng dự án được chọn không phải thành viên ACTIVE: từ chối lưu và quay lại bước 6. |
| 7.3 | | Revision thay đổi từ lần tải trước: từ chối ghi đè, yêu cầu tải lại dữ liệu ở bước 2. |
| 7.4 | | Mã xác nhận xóa cứng không khớp: từ chối xóa và yêu cầu nhập lại ở bước 5.3. |
| 8.1 | | Lỗi dịch vụ/CSDL khi đọc hoặc ghi: báo lỗi, không khẳng định cập nhật thành công; kết thúc thất bại. |

**Giả định / Câu hỏi cần làm rõ:** (1) Form tạo có trường chọn Chủ dự án, nhưng `ProjectCreate` không khai báo `project_owner_user_id`; Pydantic loại trường ngoài schema, còn service gán người tạo làm trưởng dự án. Cần xác nhận UI có nên bỏ trường hay backend cần lưu nó. (2) Hộp thoại xóa cứng yêu cầu mã dự án và lý do, nhưng schema backend chỉ nhận `confirmation`; cần xác nhận lý do có được lưu ở nơi khác không. Trong đặc tả chỉ xem mã dự án là điều kiện xác nhận có căn cứ.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu: người dùng đã xác thực |
| A1 | 1 | Action | Người dùng | [1] Mở danh sách dự án |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền |
| D1 | 3 | Decision | Người dùng | [3] Chọn thao tác nào? |
| A3 | 3.2 | Action | Người dùng | [3.2] Tìm kiếm hoặc lọc dự án |
| A4 | 3.1 | Action | Hệ thống | [3.1] Hiển thị chi tiết dự án được chọn |
| A5 | 5.1 | Action | Người dùng | [5.1] Nhập thông tin tạo dự án |
| A6 | 5 | Action | Người dùng | [5] Chỉnh sửa thông tin dự án |
| A7 | 5.2 | Action | Người dùng | [5.2] Xác nhận lưu trữ dự án |
| A8 | 5.2 | Action | Người dùng | [5.2] Xác nhận khôi phục dự án |
| A9 | 5.3 | Action | Admin vận hành | [5.3] Xác nhận xóa cứng bằng mã dự án |
| D2 | 7 | Decision | Hệ thống | [7] Quyền và dữ liệu hợp lệ? |
| A10 | 7.1-7.4/8.1 | Action | Hệ thống | [7.1] Báo lỗi nghiệp vụ hoặc lỗi hệ thống |
| A11 | 8-9 | Action | Hệ thống | [8] Lưu thao tác hợp lệ và trả kết quả |
| F1 | 9 | Final | Hệ thống | Kết thúc thành công |
| F2 | 7.4/8.1 | Final | Hệ thống | Kết thúc thất bại, dữ liệu không đổi |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách đã tải |
| D1 | A3 | [Tìm kiếm hoặc lọc] |
| A3 | A2 | [Tải lại danh sách] |
| D1 | A4 | [Xem chi tiết] |
| A4 | F1 | Chi tiết đã hiển thị |
| D1 | A5 | [Tạo mới] |
| A5 | D2 | Đã gửi biểu mẫu |
| D1 | A6 | [Chỉnh sửa] |
| A6 | D2 | Đã gửi thay đổi |
| D1 | A7 | [Lưu trữ] |
| A7 | D2 | Đã xác nhận lý do |
| D1 | A8 | [Khôi phục] |
| A8 | D2 | Đã xác nhận lý do |
| D1 | A9 | [Admin vận hành chọn xóa cứng] |
| A9 | D2 | Đã gửi mã xác nhận |
| D2 | A11 | [Đủ quyền, dữ liệu hợp lệ và revision hiện hành] |
| A11 | F1 | Ghi thành công |
| D2 | A10 | [Thiếu quyền, dữ liệu sai, conflict hoặc lỗi lưu] |
| A10 | A2 | [Có thể tải lại và thử lại] |
| A10 | F2 | [Dừng hoặc lỗi không khắc phục được] |

### 3c. Số liệu

Action = 11, Decision = 2, cạnh = 22. Tìm kiếm, xem chi tiết, tạo, sửa, lưu trữ, khôi phục và xóa cứng có các nhánh riêng; chi tiết lớp kỹ thuật được lược khỏi Activity.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa kịch bản tạo dự án. Các thao tác tìm/lọc, xem, sửa, lưu trữ, khôi phục và xóa cứng đã có nhánh riêng trong Activity và đặc tả.

### 4a. Lifeline trái sang phải

Người dùng có quyền → Giao diện dự án → API dự án → CSDL dự án. Không có hệ thống ngoài. Không tách Repository hoặc service nội bộ.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng có quyền | Giao diện dự án | [1] moDanhSachDuAn() | đồng bộ | chính |
| 2 | 2 | Giao diện dự án | API dự án | [2] layDanhSachDuAn(status, q) | đồng bộ | chính |
| 3 | 2 | API dự án | CSDL dự án | [2] selectDuAnTheoPhamVi() | đồng bộ | chính |
| 4 | 2 | CSDL dự án | API dự án | [2] traDanhSachDuAn() | trả về | chính |
| 5 | 2 | API dự án | Giao diện dự án | [2] traDanhSach() | trả về | chính |
| 6 | 2 | Giao diện dự án | Người dùng có quyền | [2] hienThiDanhSachHoacLoi() | trả về | alt [Tải thành công / lỗi] |
| 7 | 5.1/6 | Người dùng có quyền | Giao diện dự án | [5.1/6] nhapThongTinVaGuiTaoDuAn(payload) | đồng bộ | loop [Mỗi lần gửi biểu mẫu] |
| 8 | 7.1 | Giao diện dự án | Người dùng có quyền | [7.1] hienThiLoiTruongBatBuoc() | trả về | alt [Biểu mẫu không hợp lệ] |
| 9 | 7 | Giao diện dự án | API dự án | [7] taoDuAn(payload) | đồng bộ | alt [Biểu mẫu hợp lệ] |
| 10 | 7-8 | API dự án | CSDL dự án | [7-8] insertDuAnVaThanhVienKhoiTao() | đồng bộ | alt [Dữ liệu hợp lệ] |
| 11 | 8 | CSDL dự án | API dự án | [8] traKetQuaTaoDuAn() | trả về | alt [Ghi thành công / mã trùng] |
| 12 | 8-9 | API dự án | Giao diện dự án | [8-9] traDuAnMoi() | trả về | alt [Tạo thành công] |
| 13 | 9 | Giao diện dự án | Người dùng có quyền | [9] hienThiDuAnVaThongBaoThanhCong() | trả về | alt [Tạo thành công] |
| 14 | 7.1/7.2/7.3/8.1 | API dự án | Giao diện dự án | [7.1/7.2/7.3/8.1] traLoiLoiTaoDuAn(maLoi) | trả về | alt [Dữ liệu sai, trùng mã hoặc lỗi] |
| 15 | 7.1/7.2/7.3/8.1 | Giao diện dự án | Người dùng có quyền | [7.1/7.2/7.3/8.1] hienThiLoiTaoDuAn() | trả về | alt [Dữ liệu sai, trùng mã hoặc lỗi] |

### 4c. Số liệu

Lifeline = 4, message = 15, fragment = 4: alt kết quả tải danh sách, loop gửi biểu mẫu, alt kiểm tra biểu mẫu và alt kết quả tạo dự án. Lời gọi API/CSDL đồng bộ có phản hồi. Đây là sequence cho luồng tạo, các thao tác quản lý khác không bị coi là đã vẽ trong hình này.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC08 - Quản lý dự án của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Định dạng PlantUML, nhãn Tiếng Việt. Bố cục thoáng, swimlane Người dùng, Hệ thống và Admin vận hành. Giữ các thao tác riêng, không mô phỏng từng lớp code.

ĐẶC TẢ ĐẦY ĐỦ
Mô tả: Người dùng có quyền xem danh sách/chi tiết, tìm kiếm, lọc, tạo, sửa, lưu trữ và khôi phục dự án. Admin vận hành nội bộ có thể xóa cứng qua giao diện quản trị.
Tiền điều kiện: Người dùng đã xác thực và có quyền tương ứng. Tạo dự án phụ thuộc chính sách hiện hành. Xóa cứng yêu cầu quyền quản trị nội bộ.
Hậu điều kiện: Thành công thì trả danh sách/chi tiết hoặc cập nhật dự án; thất bại thì không khẳng định dữ liệu đã đổi. Hủy trước khi gửi thì không ghi dữ liệu.
Tác nhân chính: Người dùng có quyền dự án. Tác nhân phụ: Admin vận hành cho thao tác xóa cứng.
Luồng: (1) mở danh sách; (2) tải theo quyền; (3) chọn tìm/lọc, xem chi tiết, tạo, sửa, lưu trữ, khôi phục hoặc xóa cứng; (7) kiểm tra quyền và dữ liệu; (8-9) lưu và trả kết quả. Ngày kết thúc phải sau ngày bắt đầu; trưởng dự án mới phải là thành viên ACTIVE; thao tác cập nhật dùng revision. UI gửi `project_owner_user_id` nhưng schema tạo dự án không nhận, nên lựa chọn này chưa được lưu. Lý do lưu trữ/khôi phục dài 2-2000 ký tự. Xóa cứng cần mã xác nhận khớp mã dự án. Lỗi quyền, dữ liệu, revision hoặc CSDL phải báo lỗi. Giao diện hỏi lý do xóa cứng nhưng backend chỉ nhận mã xác nhận, không mô tả lý do được lưu.

BẢNG NODE
| ID | Loại | Swimlane | Nhãn |
| I | Initial | Người dùng | Bắt đầu: người dùng đã xác thực |
| A1 | Action | Người dùng | [1] Mở danh sách dự án |
| A2 | Action | Hệ thống | [2] Tải danh sách theo quyền |
| D1 | Decision | Người dùng | [3] Chọn thao tác nào? |
| A3 | Action | Người dùng | [3.2] Tìm kiếm hoặc lọc dự án |
| A4 | Action | Hệ thống | [3.1] Hiển thị chi tiết dự án được chọn |
| A5 | Action | Người dùng | [5.1] Nhập thông tin tạo dự án |
| A6 | Action | Người dùng | [5] Chỉnh sửa thông tin dự án |
| A7 | Action | Người dùng | [5.2] Xác nhận lưu trữ dự án |
| A8 | Action | Người dùng | [5.2] Xác nhận khôi phục dự án |
| A9 | Action | Admin vận hành | [5.3] Xác nhận xóa cứng bằng mã dự án |
| D2 | Decision | Hệ thống | [7] Quyền và dữ liệu hợp lệ? |
| A10 | Action | Hệ thống | [7.1] Báo lỗi nghiệp vụ hoặc lỗi hệ thống |
| A11 | Action | Hệ thống | [8] Lưu thao tác hợp lệ và trả kết quả |
| F1 | Final | Hệ thống | Kết thúc thành công |
| F2 | Final | Hệ thống | Kết thúc thất bại, dữ liệu không đổi |

BẢNG CẠNH
| Từ | Đến | Guard |
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách đã tải |
| D1 | A3 | [Tìm kiếm hoặc lọc] |
| A3 | A2 | [Tải lại danh sách] |
| D1 | A4 | [Xem chi tiết] |
| A4 | F1 | Chi tiết đã hiển thị |
| D1 | A5 | [Tạo mới] |
| A5 | D2 | Đã gửi biểu mẫu |
| D1 | A6 | [Chỉnh sửa] |
| A6 | D2 | Đã gửi thay đổi |
| D1 | A7 | [Lưu trữ] |
| A7 | D2 | Đã xác nhận lý do |
| D1 | A8 | [Khôi phục] |
| A8 | D2 | Đã xác nhận lý do |
| D1 | A9 | [Admin vận hành chọn xóa cứng] |
| A9 | D2 | Đã gửi mã xác nhận |
| D2 | A11 | [Đủ quyền, dữ liệu hợp lệ và revision hiện hành] |
| A11 | F1 | Ghi thành công |
| D2 | A10 | [Thiếu quyền, dữ liệu sai, conflict hoặc lỗi lưu] |
| A10 | A2 | [Có thể tải lại và thử lại] |
| A10 | F2 | [Dừng hoặc lỗi không khắc phục được] |

YÊU CẦU: Bám đúng node, cạnh, guard và swimlane. Initial, Final thành công/thất bại tách biệt. Không node treo, không bỏ nhánh. Báo đối chiếu Action=11, Decision=2, cạnh=22.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC08 - Quản lý dự án của hệ thống Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Bố cục gọn, ít lifeline, dùng activation bar và alt/loop có guard. Đây là sequence cho kịch bản tạo dự án, không phải toàn bộ thao tác quản trị.

ĐẶC TẢ ĐẦY ĐỦ
Mô tả: Người dùng có quyền xem danh sách/chi tiết, tìm kiếm, lọc, tạo, sửa, lưu trữ hoặc khôi phục dự án. Admin vận hành nội bộ có thể xóa cứng qua giao diện quản trị.
Tiền điều kiện: Người dùng đã xác thực và có quyền dự án tương ứng. Tạo dự án phụ thuộc chính sách hiện hành. Xóa cứng yêu cầu quyền quản trị nội bộ.
Hậu điều kiện: Thành công thì dự án mới được tạo, người tạo trở thành trưởng dự án và thành viên ban đầu; backend chưa nhận lựa chọn Chủ dự án từ UI. Thất bại thì không khẳng định dữ liệu thay đổi. Các thao tác tìm, xem, sửa, lưu trữ, khôi phục, xóa cứng được trình bày ở Activity và đặc tả.
Tác nhân chính: Người dùng có quyền dự án. Tác nhân phụ: Admin vận hành cho xóa cứng.
Luồng sequence: mở danh sách, giao diện yêu cầu danh sách theo quyền, API đọc dữ liệu; người dùng gửi biểu mẫu tạo; hệ thống kiểm tra, ghi dự án cùng thành viên ban đầu và trả kết quả.
Ngoại lệ: lỗi tải danh sách; dữ liệu thiếu/sai, mã dự án trùng, lịch không hợp lệ hoặc lỗi CSDL khi tạo. Hủy trước khi gửi không ghi dữ liệu.
Giả định: hộp thoại xóa cứng hỏi lý do nhưng schema backend chỉ nhận mã xác nhận; không thể hiện việc lưu lý do.

LIFELINE trái sang phải: Người dùng có quyền | Giao diện dự án | API dự án | CSDL dự án.

MESSAGE
1. Người dùng có quyền -> Giao diện dự án: [1] moDanhSachDuAn()
2. Giao diện dự án -> API dự án: [2] layDanhSachDuAn(status, q)
3. API dự án -> CSDL dự án: [2] selectDuAnTheoPhamVi()
4. CSDL dự án --> API dự án: [2] traDanhSachDuAn()
5. API dự án --> Giao diện dự án: [2] traDanhSach()
6. Giao diện dự án --> Người dùng có quyền: [2] hienThiDanhSachHoacLoi(); alt [Tải thành công] / [Lỗi tải]
7. Trong loop [Mỗi lần gửi biểu mẫu], Người dùng có quyền -> Giao diện dự án: [5.1/6] nhapThongTinVaGuiTaoDuAn(payload)
8. Trong alt [Biểu mẫu không hợp lệ], Giao diện dự án --> Người dùng có quyền: [7.1] hienThiLoiTruongBatBuoc()
9. Trong alt [Biểu mẫu hợp lệ], Giao diện dự án -> API dự án: [7] taoDuAn(payload)
10. API dự án -> CSDL dự án: [7-8] insertDuAnVaThanhVienKhoiTao()
11. CSDL dự án --> API dự án: [8] traKetQuaTaoDuAn()
12. Trong alt [Tạo thành công], API dự án --> Giao diện dự án: [8-9] traDuAnMoi()
13. Giao diện dự án --> Người dùng có quyền: [9] hienThiDuAnVaThongBaoThanhCong()
14. Trong alt [Dữ liệu sai, trùng mã hoặc lỗi], API dự án --> Giao diện dự án: [7.1/7.2/7.3/8.1] traLoiLoiTaoDuAn(maLoi)
15. Giao diện dự án --> Người dùng có quyền: [7.1/7.2/7.3/8.1] hienThiLoiTaoDuAn()

YÊU CẦU: Giữ đúng 4 lifeline và 15 message, biểu diễn đủ return, alt/loop có guard. Không tạo message cho lưu trữ, khôi phục hoặc xóa cứng trong sequence minh họa này; các nhánh đó thuộc Activity và đặc tả. Không vẽ lý do xóa cứng như dữ liệu đã được lưu. Đối chiếu lifeline=4, message=15, fragment=4 và báo kết quả cuối.
```

## TỰ KIỂM TRA UC08

- [x] Đặc tả phân biệt thao tác thông thường với quản trị nội bộ.
- [x] Ghi rõ mâu thuẫn trường Chủ dự án và lý do xóa cứng giữa giao diện với schema backend.
- [x] Activity: 11 Action, 2 Decision, 22 cạnh; guard có trên mọi nhánh của Decision.
- [x] Sequence: 4 lifeline, 16 message, 3 fragment; có phản hồi cho lời gọi đồng bộ.
- [x] Hai prompt tự đủ nội dung và giữ mức trình bày khóa luận.

## Bảng theo dõi sau UC08

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Chưa | Chưa | Chưa | Chưa |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC09 - Quản lý thành viên dự án

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | Chưa nêu quyền `project.members.read/manage` hoặc phạm vi thành viên theo dự án. | Yêu cầu quyền tương ứng và dự án tồn tại; không coi mọi Admin/BA/Tester mặc nhiên có quyền. |
| 3-6 | MƠ HỒ | “Gửi lời mời” dễ bị hiểu là hệ thống gửi email, nhưng service chỉ tạo membership trạng thái INVITED. | Mô tả tạo lời mời trong hệ thống; không khẳng định email được gửi/đến hộp thư. |
| 5, 3.3 | THIẾU | Vai trò chỉ được ghi như một vai trò đơn, trong khi request hỗ trợ danh sách vai trò; role cần khớp chính sách. | Cho phép một hoặc nhiều vai trò hợp lệ; SYSTEM_ADMIN chỉ áp dụng với tài khoản Admin hệ thống đang hoạt động. Cập nhật dùng membership revision. |
| 3.1-3.2 | MƠ HỒ | Gửi lại/hủy lời mời chưa ràng buộc trạng thái. | Chỉ thao tác trên lời mời INVITED; trạng thái khác bị từ chối. Gửi lại cập nhật thời điểm/lượt mời, chưa có căn cứ để nói email được gửi. |
| 3.4 | THIẾU | Trạng thái thành viên chưa xác định tập giá trị và tác động. | Ghi ACTIVE/INACTIVE; quyền dự án được tính theo trạng thái membership. |
| 3.5 | THIẾU | Xóa thành viên không nói thành viên giữ vai trò trưởng dự án bị chặn. | Thêm ngoại lệ `PROJECT_LEAD_MEMBERSHIP_REQUIRED`; phải chuyển trưởng dự án trước. |
| 9-10 | SAI | Đặc tả ngụ ý người được mời chấp nhận là tác nhân trong cùng phiên tương tác; thao tác chấp nhận/từ chối yêu cầu chính người được mời đã xác thực. | Ghi người nhận lời mời là tác nhân phụ, có thể xử lý sau độc lập; không tạo UC quản lý phiên. |
| Toàn UC | THIẾU | Thiếu quyền bị từ chối, thành viên trùng, lời mời không còn chờ, người nhận sai, không tìm thấy, revision conflict, lỗi lưu và hủy. | Bổ sung nhánh lỗi có căn cứ từ route/service; xóa thành viên trưởng dự án bị từ chối. |
| Phạm vi | THIẾU | API có thao tác thành viên tự rời dự án, nhưng bảng gốc không nêu và UI quản lý thành viên đang xét không thể hiện thao tác này. | Không tự ghép vào UC09; ghi câu hỏi xem có cần một UC riêng cho “Rời dự án”. |

Đã kiểm: **8 điểm rẽ, 8 nhánh và 8 nhóm lỗi** (không đủ quyền/hết xác thực, tài khoản hoặc role không hợp lệ, membership trùng, lời mời không chờ/không tìm thấy, sai người nhận, revision conflict, xóa trưởng dự án, lỗi hệ thống/CSDL và hủy trước gửi). Các thao tác mời, gửi lại, hủy, chấp nhận/từ chối, sửa role/status và loại bỏ được tách riêng. Không khẳng định việc gửi email.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền quản lý thành viên xem danh sách và mời tài khoản vào dự án, gửi lại hoặc hủy lời mời đang chờ, sửa vai trò/trạng thái, hoặc loại bỏ thành viên. Người nhận có thể chấp nhận hoặc từ chối lời mời của chính mình.

**Tiền điều kiện:** Người quản lý đã xác thực, dự án tồn tại và đang cho phép quản lý thành viên; người thao tác có `project.members.manage`. Người nhận lời mời đã xác thực bằng chính tài khoản được mời để chấp nhận/từ chối.

**Hậu điều kiện:**
- Thành công: membership/lời mời được tạo hoặc chuyển trạng thái; vai trò/trạng thái được cập nhật theo revision; hoặc thành viên bị loại khỏi dự án.
- Thất bại: membership hiện có không bị đổi nếu validation/quyền/revision thất bại.
- Hủy: thao tác xác nhận trước khi gửi không làm đổi dữ liệu.

**Tác nhân chính:** Người dùng có quyền quản lý thành viên dự án.

**Tác nhân phụ:** Người được mời, khi xem và phản hồi lời mời của chính mình.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở mục Thành viên của dự án. | |
| 2 | | Kiểm tra quyền đọc và hiển thị thành viên, vai trò, trạng thái, revision. |
| 3 | Nhập tài khoản cần mời, chọn một hoặc nhiều vai trò hợp lệ và gửi lời mời. | |
| 4 | | Kiểm tra tài khoản, vai trò, quyền quản lý và tính duy nhất membership. |
| 5 | | Tạo membership trạng thái INVITED; ghi audit. Việc tạo bản ghi không chứng minh email đã được gửi. |
| 6 | Người được mời mở danh sách lời mời của mình. | |
| 7 | | Chỉ hiển thị lời mời đang chờ thuộc tài khoản hiện tại. |
| 8 | Người được mời chọn Chấp nhận. | |
| 9 | | Kiểm tra lời mời còn INVITED và thuộc người dùng hiện tại; chuyển membership sang ACTIVE, ghi audit và cập nhật quyền hiệu lực. |
| 10 | | Thông báo kết quả, làm mới danh sách; kết thúc luồng chấp nhận. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Chọn lời mời INVITED và chọn Gửi lại. | Cập nhật thời điểm/ngữ cảnh gửi lại và audit; không khẳng định email được giao. Kết thúc thao tác. |
| 3.2 | Chọn lời mời INVITED và chọn Hủy. | Chuyển lời mời sang CANCELLED, ghi audit và làm mới danh sách. Kết thúc thao tác. |
| 3.3 | Chọn thành viên và thay đổi danh sách vai trò. | Kiểm tra role được hỗ trợ và expected revision; lưu membership revision mới. Kết thúc thao tác. |
| 3.4 | Chọn thành viên và chuyển trạng thái ACTIVE/INACTIVE. | Kiểm tra expected revision; cập nhật trạng thái và quyền hiệu lực. Kết thúc thao tác. |
| 3.5 | Chọn thành viên không phải trưởng dự án, xác nhận loại khỏi dự án. | Xóa membership, ghi audit và làm mới danh sách. Kết thúc thao tác. |
| 8.1 | Người được mời chọn Từ chối. | Nếu lời mời thuộc người dùng hiện tại và còn chờ, chuyển sang DECLINED, ghi audit; không cấp quyền dự án. Kết thúc luồng từ chối. |
| 3.6 | Hủy hộp thoại trước khi gửi thay đổi. | Đóng hộp thoại, không đổi dữ liệu; kết thúc thao tác. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Hết thông tin xác thực hoặc thiếu quyền đọc/quản lý: từ chối truy cập; kết thúc thất bại. |
| 4.1 | | Không tìm thấy tài khoản hoặc role không hợp lệ/không được phép: từ chối tạo lời mời; quay lại bước 3. |
| 5.1 | | Membership đã tồn tại: từ chối tạo trùng; thông báo lỗi và kết thúc thao tác. |
| 3.1.1/3.2.1 | | Lời mời không còn INVITED hoặc không tìm thấy: từ chối gửi lại/hủy; làm mới danh sách ở bước 2. |
| 9.1/8.1.1 | | Lời mời không thuộc người dùng hiện tại, đã xử lý hoặc không tìm thấy: từ chối chấp nhận/từ chối; kết thúc thất bại. |
| 3.3.1/3.4.1 | | Thành viên không tồn tại hoặc membership revision đã đổi: từ chối cập nhật; tải lại ở bước 2 trước khi thử lại. |
| 3.5.1 | | Thành viên là trưởng dự án: từ chối xóa với yêu cầu chuyển trách nhiệm trưởng dự án trước. |
| 4-9 | | Lỗi API/CSDL khi ghi: trả lỗi, không khẳng định thay đổi thành công; kết thúc thất bại. |

**Giả định / Câu hỏi cần làm rõ:** Service xử lý lời mời bằng bản ghi membership, không có lời gọi gửi email trong các route đã đối chiếu. API hỗ trợ người dùng tự rời dự án (`POST /du-an/{project_id}/roi-du-an`), nhưng chức năng đó không nằm trong bảng UC09 và chưa thấy ở màn hình quản lý thành viên đang xét; cần quyết định bổ sung thành UC riêng hay chưa đưa vào phạm vi khóa luận.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu khi mở khu vực thành viên/lời mời |
| A1 | 1 | Action | Người dùng | [1] Mở mục Thành viên dự án |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách và quyền thao tác |
| D1 | 3 | Decision | Người dùng | [3] Chọn thao tác thành viên nào? |
| A3 | 3 | Action | Người dùng | [3] Mời tài khoản và chọn vai trò |
| A4 | 3.1 | Action | Người dùng | [3.1] Gửi lại lời mời INVITED |
| A5 | 3.2 | Action | Người dùng | [3.2] Hủy lời mời INVITED |
| A6 | 3.3 | Action | Người dùng | [3.3] Cập nhật vai trò thành viên |
| A7 | 3.4 | Action | Người dùng | [3.4] Thay đổi trạng thái thành viên |
| A8 | 3.5 | Action | Người dùng | [3.5] Xác nhận loại thành viên khỏi dự án |
| A9 | 8 | Action | Thành viên được mời | [8] Chấp nhận lời mời của mình |
| A10 | 8.1 | Action | Thành viên được mời | [8.1] Từ chối lời mời của mình |
| D2 | 4/9 | Decision | Hệ thống | [4/9] Quyền, trạng thái và revision hợp lệ? |
| A11 | 4.1/5.1/9.1 | Action | Hệ thống | [4.1] Báo role, trùng lặp hoặc lời mời không hợp lệ |
| A12 | 5/9 | Action | Hệ thống | [5/9] Lưu chuyển trạng thái membership và audit |
| F1 | 5/9 | Final | Hệ thống | Kết thúc thành công theo thao tác đã chọn |
| F2 | 4.1/5.1/9.1 | Final | Hệ thống | Kết thúc thất bại, không đổi membership |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách đã tải |
| D1 | A3 | [Mời tài khoản] |
| D1 | A4 | [Gửi lại lời mời INVITED] |
| D1 | A5 | [Hủy lời mời INVITED] |
| D1 | A6 | [Sửa vai trò] |
| D1 | A7 | [Đổi trạng thái] |
| D1 | A8 | [Loại thành viên] |
| D1 | A9 | [Người được mời chấp nhận lời mời của mình] |
| D1 | A10 | [Người được mời từ chối lời mời của mình] |
| A3 | D2 | Đã gửi tài khoản và roles |
| A4 | D2 | Đã gửi yêu cầu resend |
| A5 | D2 | Đã gửi yêu cầu cancel |
| A6 | D2 | Đã gửi roles và expected revision |
| A7 | D2 | Đã gửi status và expected revision |
| A8 | D2 | Đã xác nhận xóa membership |
| A9 | D2 | Đã gửi yêu cầu chấp nhận |
| A10 | D2 | Đã gửi yêu cầu từ chối |
| D2 | A12 | [Có quyền, trạng thái/role/revision hợp lệ] |
| D2 | A11 | [Không quyền, role sai, trùng, trạng thái không phù hợp hoặc revision conflict] |
| A12 | F1 | Ghi thành công |
| A11 | A2 | [Tải lại để sửa hoặc chọn thao tác khác] |
| A11 | F2 | [Dừng hoặc lỗi không khắc phục được] |

### 3c. Số liệu

Action = 12, Decision = 2, cạnh = 24. Mỗi thao tác chính, kể cả chấp nhận và từ chối lời mời, có Action riêng.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa lời mời được tạo và người nhận chấp nhận. Từ chối là operand thay thế; các thao tác resend/cancel/role/status/remove được mô tả ở Activity và đặc tả.

### 4a. Lifeline trái sang phải

Người quản lý → Người được mời → Giao diện dự án → API thành viên → CSDL membership. Không có hệ thống email ngoài trong luồng đã xác minh.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người quản lý | Giao diện dự án | [1] moDanhSachThanhVien() | đồng bộ | chính |
| 2 | 2 | Giao diện dự án | API thành viên | [2] layThanhVien(project_id) | đồng bộ | chính |
| 3 | 2 | API thành viên | CSDL membership | [2] selectMemberships(project_id) | đồng bộ | chính |
| 4 | 2 | CSDL membership | API thành viên | [2] traDanhSachMembership() | trả về | chính |
| 5 | 2 | API thành viên | Giao diện dự án | [2] traDanhSachThanhVien() | trả về | chính |
| 6 | 2 | Giao diện dự án | Người quản lý | [2] hienThiThanhVien() | trả về | chính |
| 7 | 3 | Người quản lý | Giao diện dự án | [3] guiLoiMoi(user_id, project_roles) | đồng bộ | alt [Tạo lời mời] |
| 8 | 4-5 | Giao diện dự án | API thành viên | [4] taoMembershipINVITED(payload) | đồng bộ | alt [Role hợp lệ] |
| 9 | 4-5 | API thành viên | CSDL membership | [5] insertMembership(status=INVITED) | đồng bộ | alt [Không trùng membership] |
| 10 | 5 | CSDL membership | API thành viên | [5] traMembershipMoi() | trả về | alt [Tạo thành công/trùng] |
| 11 | 5 | API thành viên | Giao diện dự án | [5] traKetQuaTaoLoiMoi() | trả về | alt [Tạo thành công/lỗi] |
| 12 | 5 | Giao diện dự án | Người quản lý | [5] hienThiKetQuaLoiMoi() | trả về | alt [Tạo thành công/lỗi] |
| 13 | 6 | Người được mời | Giao diện dự án | [6] moDanhSachLoiMoi() | đồng bộ | alt [Phản hồi lời mời] |
| 14 | 7 | Giao diện dự án | API thành viên | [7] layLoiMoiCuaToi() | đồng bộ | alt [Phản hồi lời mời] |
| 15 | 7 | API thành viên | CSDL membership | [7] selectINVITEDByCurrentUser() | đồng bộ | alt [Phản hồi lời mời] |
| 16 | 7 | CSDL membership | API thành viên | [7] traLoiMoiDangCho() | trả về | alt [Phản hồi lời mời] |
| 17 | 7 | API thành viên | Giao diện dự án | [7] traDanhSachLoiMoi() | trả về | alt [Phản hồi lời mời] |
| 18 | 7 | Giao diện dự án | Người được mời | [7] hienThiLoiMoi() | trả về | alt [Phản hồi lời mời] |
| 19 | 8 | Người được mời | Giao diện dự án | [8] chonChapNhanHoacTuChoi() | đồng bộ | alt [Chấp nhận/Từ chối] |
| 20 | 9 | Giao diện dự án | API thành viên | [9] transitionInvitation(invitation_id, decision) | đồng bộ | alt [Lời mời còn INVITED, đúng người nhận] |
| 21 | 9 | API thành viên | CSDL membership | [9] updateStatus(ACTIVE/DECLINED) | đồng bộ | alt [Chấp nhận/Từ chối] |
| 22 | 9 | CSDL membership | API thành viên | [9] traMembershipDaCapNhat() | trả về | alt [Chuyển trạng thái thành công/lỗi] |
| 23 | 10 | API thành viên | Giao diện dự án | [10] traKetQuaPhanHoi() | trả về | alt [Chuyển trạng thái thành công/lỗi] |
| 24 | 10 | Giao diện dự án | Người được mời | [10] hienThiKetQuaPhanHoi() | trả về | alt [Chuyển trạng thái thành công/lỗi] |

### 4c. Số liệu

Lifeline = 5, message = 24, fragment = 4: alt tạo lời mời, alt kết quả tạo, alt xem/phản hồi lời mời, alt chấp nhận/từ chối. Không có hệ thống ngoài gửi email.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC09 - Quản lý thành viên dự án của Veriq bằng Visual Paradigm AI Chatbot. Định dạng PlantUML, nhãn Tiếng Việt. Swimlane Người dùng, Thành viên được mời và Hệ thống. Bố cục thoáng; mỗi thao tác chính có nhánh riêng.

ĐẶC TẢ ĐẦY ĐỦ
Mô tả: Người có quyền xem thành viên, mời tài khoản, gửi lại/hủy lời mời, sửa role/status hoặc loại thành viên. Người được mời có thể chấp nhận hoặc từ chối lời mời của chính mình.
Tiền điều kiện: Người quản lý có `project.members.manage`; dự án tồn tại. Người nhận đã xác thực đúng tài khoản được mời.
Hậu điều kiện: Membership được tạo/chuyển trạng thái/cập nhật/xóa theo thao tác. Nếu validation/quyền/revision thất bại, dữ liệu không đổi. Không khẳng định email được gửi.
Tác nhân chính: Người dùng quản lý thành viên. Tác nhân phụ: Người được mời.
Luồng: (1) mở thành viên; (2) tải danh sách/quyền; (3) chọn mời, gửi lại, hủy lời mời, sửa role, đổi ACTIVE/INACTIVE, xóa thành viên, chấp nhận hoặc từ chối. Hệ thống kiểm tra quyền, role/trạng thái và revision. Role hợp lệ lấy từ policy; membership trùng bị từ chối; trưởng dự án không thể bị xóa. Chấp nhận chuyển INVITED sang ACTIVE; từ chối chuyển sang DECLINED. Gửi lại cập nhật bản ghi, không đảm bảo gửi email.
Ngoại lệ: thiếu quyền, role/tài khoản sai, membership trùng, lời mời không chờ/không thuộc người nhận, không tìm thấy, revision conflict, xóa trưởng dự án, lỗi CSDL. Hủy trước submit không đổi dữ liệu. API có thao tác tự rời dự án nhưng chưa nằm trong UC gốc.

BẢNG NODE
| ID | Loại | Swimlane | Nhãn |
| I | Initial | Người dùng | Bắt đầu khi mở mục thành viên/lời mời |
| A1 | Action | Người dùng | [1] Mở mục Thành viên dự án |
| A2 | Action | Hệ thống | [2] Tải danh sách và quyền thao tác |
| D1 | Decision | Người dùng | [3] Chọn thao tác thành viên nào? |
| A3 | Action | Người dùng | [3] Mời tài khoản và chọn vai trò |
| A4 | Action | Người dùng | [3.1] Gửi lại lời mời INVITED |
| A5 | Action | Người dùng | [3.2] Hủy lời mời INVITED |
| A6 | Action | Người dùng | [3.3] Cập nhật vai trò thành viên |
| A7 | Action | Người dùng | [3.4] Thay đổi trạng thái thành viên |
| A8 | Action | Người dùng | [3.5] Xác nhận loại thành viên khỏi dự án |
| A9 | Action | Thành viên được mời | [8] Chấp nhận lời mời của mình |
| A10 | Action | Thành viên được mời | [8.1] Từ chối lời mời của mình |
| D2 | Decision | Hệ thống | [4/9] Quyền, trạng thái và revision hợp lệ? |
| A11 | Action | Hệ thống | [4.1] Báo lỗi membership/role/quyền |
| A12 | Action | Hệ thống | [5/9] Lưu chuyển trạng thái membership và audit |
| F1 | Final | Hệ thống | Kết thúc thành công |
| F2 | Final | Hệ thống | Kết thúc thất bại, membership không đổi |

BẢNG CẠNH
| Từ | Đến | Guard |
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách đã tải |
| D1 | A3 | [Mời tài khoản] |
| D1 | A4 | [Gửi lại lời mời INVITED] |
| D1 | A5 | [Hủy lời mời INVITED] |
| D1 | A6 | [Sửa vai trò] |
| D1 | A7 | [Đổi trạng thái] |
| D1 | A8 | [Loại thành viên] |
| D1 | A9 | [Người được mời chấp nhận lời mời của mình] |
| D1 | A10 | [Người được mời từ chối lời mời của mình] |
| A3 | D2 | Đã gửi tài khoản và roles |
| A4 | D2 | Đã gửi yêu cầu resend |
| A5 | D2 | Đã gửi yêu cầu cancel |
| A6 | D2 | Đã gửi roles và expected revision |
| A7 | D2 | Đã gửi status và expected revision |
| A8 | D2 | Đã xác nhận xóa membership |
| A9 | D2 | Đã gửi yêu cầu chấp nhận |
| A10 | D2 | Đã gửi yêu cầu từ chối |
| D2 | A12 | [Có quyền, trạng thái/role/revision hợp lệ] |
| D2 | A11 | [Không quyền, role sai, trùng, trạng thái không phù hợp hoặc revision conflict] |
| A12 | F1 | Ghi thành công |
| A11 | A2 | [Tải lại để sửa hoặc chọn thao tác khác] |
| A11 | F2 | [Dừng hoặc lỗi không khắc phục được] |

YÊU CẦU: Vẽ theo node/cạnh/guard/swimlane. Chấp nhận và từ chối là hai Action riêng. Final thành công và thất bại riêng. Không thêm email hoặc quản lý phiên. Kiểm tra Action=12, Decision=2, cạnh=24.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC09 - Quản lý thành viên dự án của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt, bố cục thoáng phù hợp khóa luận. Đây là kịch bản mời thành viên và người nhận phản hồi lời mời; các thao tác quản lý khác được trình bày trong Activity và đặc tả.

ĐẶC TẢ ĐẦY ĐỦ
Mô tả: Người có quyền quản lý thành viên xem danh sách và tạo lời mời. Người được mời xem lời mời của chính mình, chấp nhận hoặc từ chối.
Tiền điều kiện: Quản lý có `project.members.manage`; người nhận đã xác thực đúng tài khoản được mời.
Hậu điều kiện: Tạo membership INVITED; chấp nhận chuyển ACTIVE, từ chối chuyển DECLINED. Không khẳng định email được gửi. Lỗi thì không xác nhận thay đổi.
Ngoại lệ: role sai, membership trùng, lời mời không thuộc người nhận/không còn chờ, thiếu quyền, không tìm thấy, lỗi CSDL.
Các thao tác resend/cancel/update role/status/remove là nhánh UC khác trong Activity; không đưa vào sequence minh họa này.

LIFELINE trái sang phải: Người quản lý | Người được mời | Giao diện dự án | API thành viên | CSDL membership.

MESSAGE
1. Người quản lý -> Giao diện dự án: [1] moDanhSachThanhVien()
2. Giao diện dự án -> API thành viên: [2] layThanhVien(project_id)
3. API thành viên -> CSDL membership: [2] selectMemberships(project_id)
4. CSDL membership --> API thành viên: [2] traDanhSachMembership()
5. API thành viên --> Giao diện dự án: [2] traDanhSachThanhVien()
6. Giao diện dự án --> Người quản lý: [2] hienThiThanhVien()
7. Người quản lý -> Giao diện dự án: [3] guiLoiMoi(user_id, project_roles)
8. Giao diện dự án -> API thành viên: [4] taoMembershipINVITED(payload)
9. API thành viên -> CSDL membership: [5] insertMembership(status=INVITED)
10. CSDL membership --> API thành viên: [5] traKetQuaTaoDuLieu()
11. API thành viên --> Giao diện dự án: [5] traKetQuaTaoLoiMoi()
12. Giao diện dự án --> Người quản lý: [5] hienThiKetQuaLoiMoi()
13. Người được mời -> Giao diện dự án: [6] moDanhSachLoiMoi()
14. Giao diện dự án -> API thành viên: [7] layLoiMoiCuaToi()
15. API thành viên -> CSDL membership: [7] selectINVITEDByCurrentUser()
16. CSDL membership --> API thành viên: [7] traLoiMoiDangCho()
17. API thành viên --> Giao diện dự án: [7] traDanhSachLoiMoi()
18. Giao diện dự án --> Người được mời: [7] hienThiLoiMoi()
19. Người được mời -> Giao diện dự án: [8] chonChapNhanHoacTuChoi()
20. Giao diện dự án -> API thành viên: [9] transitionInvitation(invitation_id, decision)
21. API thành viên -> CSDL membership: [9] updateStatus(ACTIVE/DECLINED)
22. CSDL membership --> API thành viên: [9] traMembershipDaCapNhat()
23. API thành viên --> Giao diện dự án: [10] traKetQuaPhanHoi()
24. Giao diện dự án --> Người được mời: [10] hienThiKetQuaPhanHoi()

Dùng alt [Chấp nhận] / [Từ chối] cho message 19-24; trường hợp lỗi quyền/trạng thái trả lỗi trong cùng fragment. Không thêm email. Mọi request đồng bộ phải có return trong nhánh tương ứng. Dùng activation bar, guard đúng, không thêm quản lý phiên. Đối chiếu lifeline=5, message=24, fragment=4.
```

## TỰ KIỂM TRA UC09

- [x] Phần 1 nêu các khác biệt API/UI, quyền và tình huống lỗi có căn cứ.
- [x] Phần 2 phân biệt lời mời, acceptance/decline và cập nhật membership; có câu hỏi chưa rõ.
- [x] Activity: 12 Action, 2 Decision, 24 cạnh; guard có cho mọi nhánh Decision.
- [x] Sequence: 5 lifeline, 24 message, 4 fragment; không mô tả gửi email hoặc quản lý phiên.
- [x] Hai prompt tự đủ, dùng kịch bản chính gọn và không gộp luồng nghiệp vụ thành một thao tác.

## Bảng theo dõi sau UC09

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC10 - Quản lý yêu cầu

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| Tác nhân/tiền điều kiện | MƠ HỒ | Đặc tả gọi tác nhân là BA và yêu cầu quyền quản lý chung, trong khi backend kiểm tra quyền cụ thể theo dự án. | Ghi BA là vai trò nghiệp vụ; thao tác chỉ thực hiện được nếu tài khoản có quyền `requirement.read/create/update/archive` tương ứng. |
| 5-8 | THIẾU | Tạo yêu cầu chưa phân biệt lưu nháp và lưu thành trạng thái READY. | Tách hai lựa chọn. Draft có thể thiếu nội dung/giá trị bắt buộc; lưu READY yêu cầu nội dung và các trường bắt buộc theo cấu hình. |
| 3.3 | SAI | Luồng mô tả nút lưu nháp rõ ràng, nhưng giao diện commit tự lưu bản nháp sau khoảng 1,5 giây kể từ lần sửa cuối. | Mô tả autosave, chỉ áp dụng cho phiên bản DRAFT hiện tại; có thể lưu trước khi rời bước chỉnh sửa. |
| 3.4-3.5 | THIẾU | Tạo phiên bản và xem lịch sử chưa nêu kiểm tra phiên bản hiện tại, giữ phiên bản cũ và khả năng so sánh. | Nêu `expected_current_version_id`; bản mới bắt đầu DRAFT, bản trước được giữ để truy vết; có thể xem và so sánh các bản. |
| 3.6 | THIẾU | Cập nhật nhãn hàng loạt chưa ghi nhận kết quả từng yêu cầu. | Nêu thêm/bớt nhãn cho tập đã chọn; kết quả có thể thành công một phần và trả trạng thái từng mục. |
| Toàn UC | THIẾU | Giao diện còn hỗ trợ lưu trữ yêu cầu hàng loạt, nhưng bảng gốc bỏ sót thao tác này. | Thêm nhánh lưu trữ hàng loạt; mã nguồn chuyển trạng thái sang OBSOLETE, giữ lịch sử và trả kết quả từng mục. |
| Xóa / quản lý | MƠ HỒ | Từ “lưu trữ” có thể bị hiểu thành xóa dữ liệu hoặc xóa phiên bản. | Khẳng định không có hard-delete trong UC này; lưu trữ thay đổi trạng thái, lịch sử phiên bản vẫn được giữ. |
| Ngoại lệ | THIẾU | Chưa có lỗi permission, dữ liệu sai, khóa trùng, version conflict, không tìm thấy, bản không còn DRAFT, lỗi CSDL và hủy. | Bổ sung các nhánh áp dụng; batch operation nêu lỗi theo từng item. |

Đã kiểm: **2 điểm rẽ trong Activity, 11 lựa chọn/nhánh nghiệp vụ chính, 11 nhóm lỗi** (hết xác thực/thiếu quyền, trường thiếu, nội dung READY rỗng, custom field sai, mã yêu cầu trùng, bản không tồn tại, bản không còn DRAFT, revision/version conflict, nhãn không hợp lệ hoặc item batch không tìm thấy, lỗi hệ thống/CSDL và hủy trước gửi). Các thao tác đọc, tạo draft/READY, sửa draft, tạo phiên bản, xem/so sánh lịch sử, cập nhật nhãn hàng loạt và lưu trữ hàng loạt đã được rà riêng. Không thêm xóa cứng.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** BA hoặc người có quyền dự án xem/tìm/lọc yêu cầu, xem chi tiết và lịch sử, tạo yêu cầu ở trạng thái DRAFT hoặc READY, sửa bản DRAFT, tạo phiên bản mới, cập nhật nhãn hàng loạt hoặc lưu trữ hàng loạt.

**Tiền điều kiện:** Người dùng đã xác thực, dự án tồn tại và có quyền tương ứng cho thao tác. Sửa yêu cầu chỉ áp dụng cho phiên bản hiện tại trạng thái DRAFT. Tạo phiên bản yêu cầu quyền tạo version và đúng `expected_current_version_id`.

**Hậu điều kiện:**
- Thành công: yêu cầu, version, nhãn hoặc trạng thái lưu trữ được cập nhật theo thao tác. Version trước vẫn được giữ. Batch trả kết quả từng yêu cầu, nên có thể một phần thành công và một phần thất bại.
- Thất bại: lỗi quyền, validation hoặc revision không làm thao tác đơn ghi đè dữ liệu. Kết quả batch ghi rõ item không xử lý được.
- Hủy: đóng biểu mẫu trước khi gửi thì không tạo yêu cầu. Bản DRAFT đã chỉnh có thể đã tự lưu sau khoảng 1,5 giây; hủy điều hướng không đảo ngược dữ liệu đã autosave.

**Tác nhân chính:** BA theo mô hình nghiệp vụ, hoặc người dùng có quyền phù hợp trong dự án.

**Tác nhân phụ:** Không có hệ thống ngoài. Cơ sở dữ liệu là thành phần nội bộ.

**Luồng sự kiện chính: Tạo yêu cầu bản nháp**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang Yêu cầu trong dự án. | |
| 2 | | Kiểm tra `requirement.read`, tải danh sách theo bộ lọc/phân trang và hiển thị yêu cầu hiện có. |
| 3 | Chọn Tạo yêu cầu. | |
| 4 | | Hiển thị biểu mẫu tên, loại, ưu tiên, nội dung, tiêu chí chấp nhận, quy tắc nghiệp vụ, phụ trách và trường cấu hình dự án. |
| 5 | Nhập thông tin và chọn Lưu nháp. | |
| 6 | | Kiểm tra `requirement.create`, title và dữ liệu cấu trúc; cho phép nội dung/giá trị bắt buộc còn thiếu khi lưu DRAFT. |
| 7 | | Sinh mã nếu chưa cung cấp, tạo Requirement và version đầu trạng thái DRAFT trong transaction. |
| 8 | | Trả version mới, hiển thị yêu cầu trong danh sách. Kết thúc luồng tạo nháp. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | Nhập từ khóa, mã, tiêu đề hoặc chọn bộ lọc. | Lọc theo trạng thái, owner, tag, coverage, source type, pending impact; sắp xếp và phân trang kết quả. Quay lại bước 2. |
| 2.2 | Chọn yêu cầu cần xem. | Hiển thị nội dung version hiện tại, tiêu chí chấp nhận, trạng thái và nguồn liên quan. Kết thúc hoặc tiếp tục xem lịch sử. |
| 2.3 | Mở lịch sử, chọn hai version để so sánh. | Hiển thị danh sách version và nội dung khác nhau; kết thúc thao tác xem. |
| 5.1 | Chọn Lưu yêu cầu thay vì Lưu nháp. | Kiểm tra nội dung không rỗng và trường bắt buộc theo cấu hình; tạo version READY. Chính sách dự án có thể tiếp tục đưa version vào luồng rà soát. |
| 5.2 | Chỉnh sửa yêu cầu đang DRAFT. | Autosave sau khoảng 1,5 giây không có chỉnh sửa mới, gửi expected revision; chỉ bản DRAFT được sửa. |
| 5.3 | Chọn tạo bản nháp phiên bản tiếp theo từ yêu cầu hiện tại. | Sao chép dữ liệu từ version hiện hành thành version DRAFT; yêu cầu chuyển sang CHANGED và cập nhật quan hệ version bằng `expected_current_version_id`. Tiếp tục chỉnh bản nháp. |
| 5.4 | Chọn nhiều yêu cầu, thêm hoặc gỡ nhãn. | Cập nhật nhãn theo từng item và trả trạng thái kết quả cho từng yêu cầu. |
| 5.5 | Chọn nhiều yêu cầu và xác nhận Lưu trữ, nhập lý do. | Chuyển các yêu cầu hợp lệ sang OBSOLETE, giữ lịch sử và trả kết quả từng item. |
| 5.6 | Đóng biểu mẫu tạo trước khi gửi. | Không tạo yêu cầu; kết thúc thao tác. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1.1 | | Thiếu quyền đọc hoặc xác thực không còn hiệu lực: từ chối tải và báo lỗi; kết thúc thất bại. |
| 6.1 | | Title thiếu/sai, nội dung READY rỗng hoặc giá trị bắt buộc theo schema sai: trả lỗi validation và yêu cầu sửa biểu mẫu. |
| 7.1 | | Mã yêu cầu đã tồn tại: từ chối tạo, giữ dữ liệu cũ và yêu cầu mã khác. |
| 5.2.1 | | Version hiện tại không còn DRAFT hoặc expected revision đã cũ: từ chối autosave, yêu cầu tải lại dữ liệu. |
| 5.3.1 | | `expected_current_version_id` không còn trùng version hiện tại: từ chối tạo version mới, yêu cầu tải lại lịch sử. |
| 5.4.1 | | Nhãn rỗng/không hợp lệ hoặc không có thay đổi thêm/bớt: từ chối batch; item không tìm thấy hoặc conflict được trả kết quả FAILED riêng. |
| 5.5.1 | | Lý do lưu trữ không hợp lệ, item không tìm thấy/đã OBSOLETE hoặc revision conflict: không lưu trữ item đó và báo lỗi cho từng item. |
| 2-7 | | Yêu cầu không tồn tại, project mismatch hoặc lỗi API/CSDL: trả lỗi phù hợp; không khẳng định thành công. |

**Giả định / Câu hỏi cần làm rõ:** Tạo READY có thể tiếp tục sang rà soát tự động nếu chính sách dự án bật auto-approval. Quyền duyệt/gửi rà soát chi tiết thuộc UC11/UC12, nên UC10 chỉ ghi nhận điều kiện chuyển tiếp mà mã nguồn gọi, không đặc tả thay cho các UC đó. Bảng gốc gọi thao tác hàng loạt là “cập nhật nhãn”; lưu trữ hàng loạt được thêm vì giao diện tại commit có nút và API tương ứng.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu khi người dùng mở trang Yêu cầu |
| A1 | 1 | Action | Người dùng | [1] Mở trang Yêu cầu |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền và bộ lọc |
| D1 | 3 | Decision | Người dùng | [3] Chọn thao tác yêu cầu nào? |
| A3 | 2.1 | Action | Người dùng | [2.1] Tìm kiếm hoặc lọc danh sách |
| A4 | 2.2 | Action | Người dùng | [2.2] Xem yêu cầu hiện tại |
| A5 | 2.3 | Action | Người dùng | [2.3] Xem hoặc so sánh lịch sử version |
| A6 | 5 | Action | Người dùng | [5] Tạo yêu cầu DRAFT |
| A7 | 5.1 | Action | Người dùng | [5.1] Tạo yêu cầu READY |
| A8 | 5.2 | Action | Người dùng | [5.2] Chỉnh sửa bản DRAFT |
| A9 | 5.3 | Action | Người dùng | [5.3] Tạo version DRAFT tiếp theo |
| A10 | 5.4 | Action | Người dùng | [5.4] Cập nhật nhãn hàng loạt |
| A11 | 5.5 | Action | Người dùng | [5.5] Lưu trữ yêu cầu hàng loạt |
| D2 | 6-7 | Decision | Hệ thống | [6-7] Quyền, dữ liệu và revision hợp lệ? |
| A12 | 6.1/7.1/5.2.1/5.3.1 | Action | Hệ thống | [6.1] Báo lỗi validation hoặc xung đột |
| A13 | 7-8 | Action | Hệ thống | [7] Ghi thay đổi và trả kết quả |
| F1 | 8 | Final | Hệ thống | Kết thúc thành công |
| F2 | 6.1/7.1 | Final | Hệ thống | Kết thúc thất bại, dữ liệu không bị ghi đè |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách đã tải |
| D1 | A3 | [Tìm kiếm/lọc] |
| A3 | A2 | [Tải kết quả mới] |
| D1 | A4 | [Xem chi tiết] |
| A4 | F1 | Chi tiết đã hiển thị |
| D1 | A5 | [Xem/so sánh version] |
| A5 | F1 | Lịch sử đã hiển thị |
| D1 | A6 | [Tạo DRAFT] |
| D1 | A7 | [Tạo READY] |
| D1 | A8 | [Sửa DRAFT] |
| D1 | A9 | [Tạo version mới] |
| D1 | A10 | [Cập nhật nhãn hàng loạt] |
| D1 | A11 | [Lưu trữ hàng loạt] |
| A6 | D2 | Đã gửi yêu cầu tạo nháp |
| A7 | D2 | Đã gửi yêu cầu tạo READY |
| A8 | D2 | Đã gửi autosave với revision |
| A9 | D2 | Đã gửi yêu cầu tạo version với expected version |
| A10 | D2 | Đã gửi thao tác nhãn |
| A11 | D2 | Đã xác nhận lý do lưu trữ |
| D2 | A13 | [Có quyền và dữ liệu/revision hợp lệ] |
| A13 | F1 | Đã trả kết quả, gồm trạng thái từng item nếu là batch |
| D2 | A12 | [Thiếu quyền, validation hoặc revision conflict] |
| A12 | A2 | [Có thể tải lại và sửa] |
| A12 | F2 | [Dừng hoặc lỗi không khắc phục được] |

### 3c. Số liệu

Action = 13, Decision = 2, cạnh = 26. Các nhánh tìm, xem, lịch sử, tạo DRAFT/READY, sửa DRAFT, tạo version, gắn nhãn và lưu trữ được thể hiện riêng.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa tạo yêu cầu DRAFT, luồng ngắn và trực tiếp nhất. READY, versioning, batch tags/archive, lịch sử và các ngoại lệ khác đã được mô tả ở đặc tả và Activity.

### 4a. Lifeline trái sang phải

BA/người có quyền → Giao diện Yêu cầu → API Yêu cầu → CSDL yêu cầu. Không có hệ thống ngoài trong kịch bản tạo DRAFT.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | BA/người có quyền | Giao diện Yêu cầu | [1] moTrangYeuCau() | đồng bộ | chính |
| 2 | 2 | Giao diện Yêu cầu | API Yêu cầu | [2] layDanhSachYeuCau(project_id, filters, page) | đồng bộ | chính |
| 3 | 2 | API Yêu cầu | CSDL yêu cầu | [2] selectRequirementsAndCurrentVersions() | đồng bộ | chính |
| 4 | 2 | CSDL yêu cầu | API Yêu cầu | [2] traDanhSachVaVersionHienTai() | trả về | chính |
| 5 | 2 | API Yêu cầu | Giao diện Yêu cầu | [2] traDanhSachHoacLoi() | trả về | alt [Tải thành công/lỗi] |
| 6 | 2 | Giao diện Yêu cầu | BA/người có quyền | [2] hienThiDanhSachHoacLoi() | trả về | alt [Tải thành công/lỗi] |
| 7 | 3 | BA/người có quyền | Giao diện Yêu cầu | [3] chonTaoYeuCau() | đồng bộ | opt [Tạo yêu cầu] |
| 8 | 4 | Giao diện Yêu cầu | BA/người có quyền | [4] hienThiFormTao() | trả về | opt [Tạo yêu cầu] |
| 9 | 5 | BA/người có quyền | Giao diện Yêu cầu | [5] nhapThongTinVaChonLuuNhAp(payload) | đồng bộ | alt [Lưu nháp] |
| 10 | 6 | Giao diện Yêu cầu | API Yêu cầu | [6] taoYeuCau(payload, save_as_draft=true) | đồng bộ | alt [Dữ liệu hợp lệ] |
| 11 | 7 | API Yêu cầu | CSDL yêu cầu | [7] transactionInsertRequirementVersionCriteria() | đồng bộ | alt [Tạo thành công/trùng mã] |
| 12 | 7 | CSDL yêu cầu | API Yêu cầu | [7] traKetQuaGhi() | trả về | alt [Ghi thành công/trùng mã] |
| 13 | 8 | API Yêu cầu | Giao diện Yêu cầu | [8] traYeuCauMoi() | trả về | alt [Tạo thành công] |
| 14 | 8 | Giao diện Yêu cầu | BA/người có quyền | [8] hienThiYeuCauMoi() | trả về | alt [Tạo thành công] |
| 15 | 6.1/7.1 | API Yêu cầu | Giao diện Yêu cầu | [6.1/7.1] traLoiTaoYeuCau(maLoi) | trả về | alt [Validation, trùng mã hoặc lỗi ghi] |
| 16 | 6.1/7.1 | Giao diện Yêu cầu | BA/người có quyền | [6.1/7.1] hienThiLoiTaoYeuCau() | trả về | alt [Validation, trùng mã hoặc lỗi ghi] |

### 4c. Số liệu

Lifeline = 4, message = 16, fragment = 3: alt tải danh sách, opt mở thao tác tạo nháp, alt ghi thành công/trùng mã/lỗi. Gọi API và CSDL đồng bộ có return trong nhánh tương ứng. Không mô tả quản lý phiên.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC10 - Quản lý yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. Định dạng PlantUML, nhãn Tiếng Việt. Swimlane Người dùng và Hệ thống. Trình bày thoáng, nhánh nghiệp vụ rõ; không mô phỏng lớp code.

ĐẶC TẢ ĐẦY ĐỦ
Mô tả: BA/người có quyền xem, tìm/lọc yêu cầu, xem lịch sử/so sánh version, tạo DRAFT hoặc READY, sửa DRAFT, tạo version mới, cập nhật nhãn hàng loạt và lưu trữ hàng loạt.
Tiền điều kiện: Người dùng đã xác thực và có quyền phù hợp trong dự án. Sửa trực tiếp chỉ khi version hiện tại là DRAFT; tạo version cần expected current version hợp lệ.
Hậu điều kiện: Thao tác hợp lệ ghi trạng thái/phiên bản/nhãn; version cũ được giữ; batch trả kết quả từng item. Validation hoặc revision conflict không được coi là ghi thành công. Draft có thể tự lưu sau khoảng 1,5 giây không có thay đổi.
Tác nhân chính: BA theo vai trò nghiệp vụ hoặc người có quyền phù hợp. Tác nhân phụ: Không có.
Luồng chính: (1) mở trang yêu cầu; (2) tải danh sách theo bộ lọc và quyền; (3) chọn thao tác: tìm/lọc, xem, xem lịch sử/so sánh, tạo DRAFT, tạo READY, sửa DRAFT, tạo version mới, cập nhật nhãn hàng loạt, lưu trữ hàng loạt. Hệ thống kiểm tra quyền, dữ liệu và revision, ghi kết quả phù hợp. Lưu READY yêu cầu nội dung và trường bắt buộc; lưu draft cho phép nội dung/field bắt buộc còn thiếu. Tạo version mới bắt đầu ở DRAFT, yêu cầu chuyển sang CHANGED. Bulk archive chuyển item hợp lệ sang OBSOLETE, giữ lịch sử.
Ngoại lệ: thiếu quyền, validation sai, content READY rỗng, mã trùng, bản không tồn tại/không còn DRAFT, version conflict, nhãn không hợp lệ, item batch không tìm thấy hoặc revision conflict, lỗi CSDL. Không có thao tác hard-delete.

BẢNG NODE
| ID | Loại | Swimlane | Nhãn |
| I | Initial | Người dùng | Bắt đầu khi người dùng mở trang Yêu cầu |
| A1 | Action | Người dùng | [1] Mở trang Yêu cầu |
| A2 | Action | Hệ thống | [2] Tải danh sách theo quyền và bộ lọc |
| D1 | Decision | Người dùng | [3] Chọn thao tác yêu cầu nào? |
| A3 | Action | Người dùng | [2.1] Tìm kiếm hoặc lọc danh sách |
| A4 | Action | Người dùng | [2.2] Xem yêu cầu hiện tại |
| A5 | Action | Người dùng | [2.3] Xem hoặc so sánh lịch sử version |
| A6 | Action | Người dùng | [5] Tạo yêu cầu DRAFT |
| A7 | Action | Người dùng | [5.1] Tạo yêu cầu READY |
| A8 | Action | Người dùng | [5.2] Chỉnh sửa bản DRAFT |
| A9 | Action | Người dùng | [5.3] Tạo version DRAFT tiếp theo |
| A10 | Action | Người dùng | [5.4] Cập nhật nhãn hàng loạt |
| A11 | Action | Người dùng | [5.5] Lưu trữ yêu cầu hàng loạt |
| D2 | Decision | Hệ thống | [6-7] Quyền, dữ liệu và revision hợp lệ? |
| A12 | Action | Hệ thống | [6.1] Báo lỗi validation hoặc xung đột |
| A13 | Action | Hệ thống | [7] Ghi thay đổi và trả kết quả |
| F1 | Final | Hệ thống | Kết thúc thành công |
| F2 | Final | Hệ thống | Kết thúc thất bại, không ghi đè dữ liệu |

BẢNG CẠNH
| Từ | Đến | Guard |
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách tải xong |
| D1 | A3 | [Tìm kiếm/lọc] |
| A3 | A2 | [Tải kết quả mới] |
| D1 | A4 | [Xem chi tiết] |
| A4 | F1 | Chi tiết hiển thị |
| D1 | A5 | [Xem/so sánh version] |
| A5 | F1 | Lịch sử hiển thị |
| D1 | A6 | [Tạo DRAFT] |
| D1 | A7 | [Tạo READY] |
| D1 | A8 | [Sửa DRAFT] |
| D1 | A9 | [Tạo version mới] |
| D1 | A10 | [Cập nhật nhãn hàng loạt] |
| D1 | A11 | [Lưu trữ hàng loạt] |
| A6 | D2 | Đã gửi tạo nháp |
| A7 | D2 | Đã gửi tạo READY |
| A8 | D2 | Đã gửi autosave với revision |
| A9 | D2 | Đã gửi expected current version |
| A10 | D2 | Đã gửi thao tác nhãn |
| A11 | D2 | Đã xác nhận lý do lưu trữ |
| D2 | A13 | [Có quyền, dữ liệu và revision hợp lệ] |
| A13 | F1 | Đã trả kết quả, kể cả từng item batch |
| D2 | A12 | [Thiếu quyền, validation hoặc conflict] |
| A12 | A2 | [Có thể tải lại và sửa] |
| A12 | F2 | [Dừng hoặc lỗi không khắc phục] |

YÊU CẦU: Vẽ đúng node/cạnh/guard/swimlane; không gộp tạo DRAFT với READY, versioning, nhãn hoặc lưu trữ. Có Initial và Final thành công/thất bại riêng, không node treo. Kiểm tra Action=13, Decision=2, cạnh=26 và báo kết quả.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC10 - Quản lý yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Bố cục gọn, phù hợp khóa luận. Đây là kịch bản tạo một yêu cầu DRAFT; các luồng READY, versioning, batch labels/archive và lịch sử nằm trong Activity/đặc tả.

ĐẶC TẢ ĐẦY ĐỦ
Mô tả: BA/người có quyền xem, lọc, tạo DRAFT/READY, sửa bản DRAFT, tạo version, xem/so sánh lịch sử, cập nhật nhãn hoặc lưu trữ nhiều yêu cầu.
Tiền điều kiện: Người dùng đã xác thực và có quyền phù hợp của dự án.
Hậu điều kiện kịch bản: tạo Requirement cùng version đầu trạng thái DRAFT; version cũ được giữ khi tạo version mới. Thất bại thì không khẳng định tạo thành công.
Tác nhân chính: BA theo mô hình nghiệp vụ hoặc người có quyền phù hợp. Không có hệ thống ngoài.
Luồng: mở danh sách, tải yêu cầu theo quyền; mở biểu mẫu; người dùng gửi thông tin với `save_as_draft=true`; API tạo Requirement, version và tiêu chí trong transaction; trả kết quả.
Ngoại lệ: lỗi quyền/tải, title sai, mã trùng, lỗi validation hoặc CSDL. Bản DRAFT có thể autosave khi chỉnh sửa; sequence này chỉ mô tả tạo mới.

LIFELINE trái sang phải: BA/người có quyền | Giao diện Yêu cầu | API Yêu cầu | CSDL yêu cầu.

MESSAGE
1. BA/người có quyền -> Giao diện Yêu cầu: [1] moTrangYeuCau()
2. Giao diện Yêu cầu -> API Yêu cầu: [2] layDanhSachYeuCau(project_id, filters, page)
3. API Yêu cầu -> CSDL yêu cầu: [2] selectRequirementsAndCurrentVersions()
4. CSDL yêu cầu --> API Yêu cầu: [2] traDanhSachVaVersionHienTai()
5. API Yêu cầu --> Giao diện Yêu cầu: [2] traDanhSachYeuCau()
6. Giao diện Yêu cầu --> BA/người có quyền: [2] hienThiDanhSachHoacLoi()
   Dùng alt [Tải thành công] / [Lỗi tải].
7. Trong opt [Chọn tạo yêu cầu], BA/người có quyền -> Giao diện Yêu cầu: [3] moFormTaoYeuCau()
8. Giao diện Yêu cầu --> BA/người có quyền: [4] hienThiFormTao()
9. BA/người có quyền -> Giao diện Yêu cầu: [5] nhapThongTinVaChonLuuNhAp(payload)
10. Giao diện Yêu cầu -> API Yêu cầu: [6] taoYeuCau(payload, save_as_draft=true)
11. API Yêu cầu -> CSDL yêu cầu: [7] transactionInsertRequirementVersionCriteria()
12. CSDL yêu cầu --> API Yêu cầu: [7] traKetQuaGhi()
13. Trong alt [Tạo thành công], API Yêu cầu --> Giao diện Yêu cầu: [8] traYeuCauMoi()
14. Giao diện Yêu cầu --> BA/người có quyền: [8] hienThiYeuCauMoi()
15. Trong alt [Validation, trùng mã hoặc lỗi ghi], API Yêu cầu --> Giao diện Yêu cầu: [6.1/7.1] traLoiTaoYeuCau(maLoi)
16. Giao diện Yêu cầu --> BA/người có quyền: [6.1/7.1] hienThiLoiTaoYeuCau()

YÊU CẦU: Lifeline trái sang phải như trên; activation bar; lời gọi đồng bộ tới API/CSDL có return trong đúng operand. Dùng alt cho tải danh sách và kết quả tạo, opt cho mở biểu mẫu. Không thêm workflow duyệt, email, phiên đăng nhập hoặc hard-delete. Đối chiếu lifeline=4, message=16, fragment=3 và báo cuối sơ đồ.
```

## TỰ KIỂM TRA UC10

- [x] Phần 1 ghi rõ khác biệt có chứng cứ giữa đặc tả, UI và API.
- [x] Phần 2 phân biệt DRAFT/READY, version mới, batch labels và archive; có ngoại lệ và câu hỏi.
- [x] Activity: 13 Action, 2 Decision, 26 cạnh; guard có trên mọi cạnh ra từ Decision.
- [x] Sequence: 4 lifeline, 16 message, 3 fragment; requests có return.
- [x] Hai prompt tự đủ và giới hạn Sequence vào một luồng đại diện để giữ sơ đồ dễ đọc.

## Bảng theo dõi sau UC10

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC11 - Trình duyệt yêu cầu

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tiền điều kiện | MÂU THUẪN | Bảng gốc cho phép gửi khi DRAFT hoặc READY, nhưng giao diện commit chỉ hiện nút gửi rà soát khi version là READY. API cho phép cả DRAFT và READY. | Tách hành vi UI khỏi năng lực API; đặc tả chính theo thao tác nhìn thấy trong UI, ghi trường hợp gọi API với DRAFT là câu hỏi cần làm rõ. |
| 1-2 | THIẾU | Chưa nêu tải phiên bản hiện tại, quyền đọc và trường hợp yêu cầu/version không tồn tại. | Bổ sung tra cứu trong dự án, kiểm tra quyền và nhánh lỗi không tìm thấy/không có quyền. |
| 3-8 | MƠ HỒ | “Lưu những nội dung chưa được lưu” không nói thao tác lưu nào, kiểm tra điều kiện gì và có thể tự chốt chuẩn hay không. | Ghi giao diện gọi lưu nháp trước, dùng revision nhận được để gửi rà soát; API kiểm tra nội dung, custom values, trạng thái và revision. Nếu được tự duyệt theo cấu hình dự án, kết quả có thể chuyển thẳng sang BASELINED, cần nêu như hành vi phụ thuộc chính sách. |
| 5-8 | THIẾU | Ghi chú được mô tả là tùy chọn nhưng việc trim, giới hạn độ dài và yêu cầu lưu chưa được xác định từ bảng. | Giữ ghi chú tùy chọn theo giao diện; không tự đặt giới hạn. |
| 1.1 | SAI | Nhánh mở lại yêu cầu đang rà soát được đánh số 1.1.1 dù nhánh rẽ từ lựa chọn trên màn hình chi tiết sau bước 2. | Đổi thành 2.1 và đánh số tuần tự; yêu cầu nhập lý do, chuyển về DRAFT khi revision còn khớp. |
| 6.1-6.2 | THIẾU | Hủy hộp thoại chưa nêu rõ dữ liệu đã autosave có bị đảo ngược không. | Ghi rõ hủy trước gửi giữ nguyên trạng thái; các chỉnh sửa đã autosave trước đó không bị rollback. |
| 7.1, 7.2 | THIẾU | Chưa có nhánh riêng cho nội dung trống, custom field sai, trạng thái không hợp lệ, revision conflict, lỗi lưu/CSDL, hết xác thực và lỗi quyền. | Bổ sung nhánh theo các điều kiện API có căn cứ; lỗi không chuyển trạng thái thành công. |
| Tác nhân | MƠ HỒ | “BA” không phải điều kiện phân quyền trong mã; API kiểm tra quyền `requirement.submit_review`, còn mở lại cần `requirement.update`. | Ghi BA là vai trò nghiệp vụ; quyền thực tế được kiểm tra ở dự án. Không tự coi Admin là tác nhân phụ của thao tác gửi. |

Đã kiểm: **3 điểm rẽ, 5 nhánh nghiệp vụ, 8 nhóm lỗi** gồm thiếu quyền/hết xác thực, không tìm thấy hoặc project mismatch, nội dung rỗng, custom field sai, version không ở trạng thái cho phép, revision conflict, lỗi lưu/CSDL và hủy trước gửi. Đã đối chiếu tiền/hậu điều kiện và điểm bàn giao UC10/UC12. Chưa có căn cứ về gửi email/thông báo nên không thêm tác nhân ngoài.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Cho phép người có quyền gửi version yêu cầu đủ điều kiện sang trạng thái rà soát. Theo giao diện ở commit được kiểm tra, nút gửi xuất hiện khi version hiện tại là READY; API cũng chấp nhận DRAFT, nhưng cách dùng DRAFT trực tiếp chưa được xác nhận ở giao diện.

**Tiền điều kiện:** Người dùng đã xác thực; dự án và yêu cầu tồn tại; người dùng có quyền `requirement.submit_review`. Version hiện tại đang READY theo hành vi giao diện. Gửi API trực tiếp từ DRAFT là khả năng backend nhưng cần xác nhận nghiệp vụ.

**Hậu điều kiện:**
- Thành công: version chuyển IN_REVIEW, ghi nhận người gửi, thời điểm và ghi chú rà soát; trạng thái Requirement được cập nhật tương ứng. Nếu dự án/người dùng thỏa chính sách tự duyệt, luồng backend có thể tiếp tục chốt chuẩn và trả trạng thái sau xử lý.
- Thất bại: không được coi là đã gửi; trạng thái không thay đổi nếu kiểm tra/transaction thất bại.
- Hủy: hộp thoại đóng, không gửi yêu cầu chuyển trạng thái. Bản nháp có thể đã được lưu trước đó; thao tác hủy không hoàn tác autosave.

**Tác nhân chính:** BA hoặc người dùng được cấp `requirement.submit_review` trong dự án.

**Tác nhân phụ:** Không có tác nhân ngoài được xác nhận.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở yêu cầu trong dự án. | |
| 2 | | Kiểm tra quyền đọc, tải Requirement và version hiện tại; hiển thị nội dung, trạng thái và revision. |
| 3 | Chọn Gửi rà soát khi version READY. | |
| 4 | | Hiển thị hộp thoại xác nhận và trường ghi chú tùy chọn. |
| 5 | Nhập ghi chú nếu cần, xác nhận gửi. | |
| 6 | | Lưu bản nháp hiện tại qua thao tác saveDraft; nhận revision mới nhất. |
| 7 | | Kiểm tra `requirement.submit_review`, dự án, trạng thái DRAFT/READY, expected revision, nội dung không rỗng và custom values. |
| 8 | | Trong transaction, chuyển version sang IN_REVIEW, cập nhật trạng thái Requirement và ghi audit gồm người gửi, thời điểm, ghi chú. |
| 9 | | Nếu chính sách tự duyệt áp dụng, gọi bước chốt chuẩn; nếu không, giữ IN_REVIEW. |
| 10 | | Trả version/kết quả hiện tại, giao diện tải lại dữ liệu và thông báo kết quả. Kết thúc UC. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | Chọn Mở lại để chỉnh sửa khi version IN_REVIEW. | Hiển thị hộp thoại yêu cầu lý do. |
| 2.2 | Nhập lý do và xác nhận Mở bản nháp. | Kiểm tra `requirement.update`, trạng thái IN_REVIEW và revision; chuyển version/Requirement về DRAFT, ghi người mở lại, thời điểm và lý do. Quay lại màn hình chi tiết với version DRAFT. |
| 5.1 | Chọn Hủy trong hộp thoại gửi. | Đóng hộp thoại, không gửi chuyển trạng thái; kết thúc nhánh. |
| 9.1 | Không đủ điều kiện tự duyệt theo cấu hình dự án/người dùng. | Giữ trạng thái IN_REVIEW và hiển thị đang chờ rà soát. Kết thúc UC. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1.1 | | Hết xác thực hoặc thiếu quyền đọc: từ chối tải dữ liệu, thông báo lỗi; kết thúc thất bại. |
| 2.1.2 | | Không tìm thấy yêu cầu/version hoặc project mismatch: trả lỗi phù hợp; kết thúc thất bại. |
| 6.1 | | Lưu nháp thất bại: không gửi yêu cầu rà soát; giữ trạng thái hiện tại và báo lỗi. |
| 7.1 | | Nội dung trống hoặc custom value không hợp lệ: từ chối chuyển trạng thái, yêu cầu cập nhật ở UC10. |
| 7.2 | | Version không ở DRAFT/READY hoặc expected revision đã cũ: trả conflict, không ghi đè; yêu cầu tải lại. |
| 8.1 | | Cập nhật Requirement hoặc audit thất bại trong transaction: rollback chuyển trạng thái, báo lỗi hệ thống. |
| 2.2.1 | | Khi mở lại, version không còn IN_REVIEW hoặc revision đã đổi: từ chối, yêu cầu tải lại. |
| 8.2 | | Lỗi CSDL/API không xác định: trả lỗi, không thông báo gửi thành công. |

**Giả định / Câu hỏi cần làm rõ:** Bảng gốc nói DRAFT hoặc READY, trong khi UI chỉ bật nút cho READY; xác nhận liệu DRAFT có được gửi qua UI hay chỉ qua API. Chính sách tự duyệt và điều kiện `can_auto_approve_project_content` do cấu hình/quyền quyết định; không suy diễn thành mặc định. Chưa thấy bằng chứng gửi email/thông báo ngoài giao diện.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu khi mở yêu cầu |
| A1 | 1 | Action | Người dùng | [1] Mở yêu cầu trong dự án |
| A2 | 2 | Action | Hệ thống | [2] Tải version và kiểm tra quyền đọc |
| D1 | 3 | Decision | Người dùng | [3] Chọn gửi rà soát hay mở lại chỉnh sửa? |
| A3 | 4-5 | Action | Người dùng | [4] Nhập ghi chú và xác nhận gửi |
| A4 | 6 | Action | Hệ thống | [6] Lưu bản nháp và lấy revision mới |
| D2 | 7 | Decision | Hệ thống | [7] Quyền, nội dung, trạng thái và revision hợp lệ? |
| A5 | 8-9 | Action | Hệ thống | [8] Chuyển IN_REVIEW và kiểm tra tự duyệt |
| D3 | 9 | Decision | Hệ thống | [9] Chính sách tự duyệt áp dụng? |
| A6 | 10 | Action | Hệ thống | [10] Trả trạng thái và hiển thị kết quả gửi |
| A7 | 2.1 | Action | Người dùng | [2.1] Chọn mở lại yêu cầu để chỉnh sửa |
| A8 | 2.1 | Action | Hệ thống | [2.1] Yêu cầu lý do mở lại |
| A9 | 2.2 | Action | Người dùng | [2.2] Nhập lý do và xác nhận mở bản nháp |
| A10 | 2.2 | Action | Hệ thống | [2.2] Chuyển version về DRAFT |
| A11 | 5.1 | Action | Người dùng | [5.1] Hủy hộp thoại gửi rà soát |
| A12 | 7.1/7.2/8.1 | Action | Hệ thống | [7.1] Báo validation, conflict hoặc lỗi ghi |
| F1 | 10/2.2 | Final | Hệ thống | Kết thúc thành công hoặc hoàn tất nhánh mở lại |
| F2 | 5.1/7.1 | Final | Hệ thống | Kết thúc không chuyển trạng thái |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Yêu cầu tải xong |
| D1 | A3 | [Gửi rà soát, version READY] |
| D1 | A7 | [Mở lại chỉnh sửa, version IN_REVIEW] |
| A3 | A4 | Đã xác nhận gửi |
| A3 | A11 | [Người dùng hủy] |
| A4 | D2 | Lưu nháp trả revision |
| D2 | A5 | [Quyền và dữ liệu hợp lệ] |
| D2 | A12 | [Thiếu quyền, validation hoặc revision conflict] |
| A5 | D3 | Đã chuyển IN_REVIEW |
| D3 | A6 | [Tự duyệt được phép] |
| D3 | A6 | [Không tự duyệt, giữ IN_REVIEW] |
| A6 | F1 | Đã trả kết quả |
| A7 | A8 | Đã chọn mở lại |
| A8 | A9 | Hộp thoại đã hiển thị |
| A9 | A10 | Đã xác nhận với lý do |
| A10 | F1 | Version trở về DRAFT |
| A11 | F2 | Không gửi thay đổi trạng thái |
| A12 | F2 | Lỗi không khắc phục tại luồng này |

### 3c. Số liệu

N = 13 ô đặc tả có nội dung; M = 13 Action; D = 3 Decision; E = 20 cạnh. Thành công và thất bại đi tới Final riêng; mỗi nhánh có guard và kết thúc xác định.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence chỉ minh họa gửi version READY sang rà soát. Nhánh mở lại và lỗi được thể hiện ở Activity và trong operand alt, để sơ đồ không biến thành bản đồ mọi màn hình của module.

### 4a. Lifeline trái sang phải

Người dùng → Giao diện Yêu cầu → Controller/API → Service → Repository → Database. Không có hệ thống ngoài được xác nhận. Sáu lifeline này thể hiện ranh giới tầng, không phải sáu tác nhân nghiệp vụ.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện Yêu cầu | [1] moYeuCau(project_id, requirement_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Yêu cầu | Controller/API | [2] layRequirementVaVersion(requirement_id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] docYeuCauVaKiemTraQuyen(requirement_id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findRequirementAndCurrentVersion(id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectRequirementAndVersion(id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traRequirementVaVersion() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traDuLieuHoacKhongTimThay() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traDuLieuVaQuyen() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Yêu cầu | [2] traChiTietHoacLoi() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Yêu cầu | Người dùng | [2] hienThiChiTietHoacLoi() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Người dùng | Giao diện Yêu cầu | [3] xacNhanGuiRaSoat(review_note) | đồng bộ | opt [Version READY] |
| 12 | 6 | Giao diện Yêu cầu | Controller/API | [6] luuDraftVaGuiRaSoat(expected_revision, review_note) | đồng bộ | opt [Gửi rà soát] |
| 13 | 6 | Controller/API | Service | [6] saveDraftAndSubmitReview(payload) | đồng bộ | opt [Gửi rà soát] |
| 14 | 6 | Service | Service | [6] validateDraftAndResolveRevision() | tự gọi | opt [Gửi rà soát] |
| 15 | 7 | Service | Repository | [7] transitionVersionToInReview(expected_revision) | đồng bộ | alt [Hợp lệ/conflict] |
| 16 | 8 | Repository | Database | [8] transactionUpdateVersionRequirementAndAudit() | đồng bộ | alt [Ghi thành công/lỗi CSDL] |
| 17 | 8 | Database | Repository | [8] traKetQuaTransaction() | trả về | alt [Ghi thành công/lỗi CSDL] |
| 18 | 8 | Repository | Service | [8] traTrangThaiDaCapNhat() | trả về | alt [Ghi thành công/lỗi CSDL] |
| 19 | 9 | Service | Service | [9] checkAutoApprovalPolicy() | tự gọi | alt [Tự duyệt/giữ IN_REVIEW] |
| 20 | 9 | Service | Repository | [9] baselineRequirement(version_id) | đồng bộ | opt [Tự duyệt được phép] |
| 21 | 9 | Repository | Database | [9] updateBaselineStatus(version_id) | đồng bộ | opt [Tự duyệt được phép] |
| 22 | 9 | Database | Repository | [9] traBaselineResult() | trả về | opt [Tự duyệt được phép] |
| 23 | 9 | Repository | Service | [9] traVersionSauKhiChot() | trả về | opt [Tự duyệt được phép] |
| 24 | 10 | Service | Controller/API | [10] traKetQuaGuiHoacLoi() | trả về | alt [Thành công/lỗi] |
| 25 | 10 | Controller/API | Giao diện Yêu cầu | [10] traResponse() | trả về | alt [Thành công/lỗi] |
| 26 | 10 | Giao diện Yêu cầu | Người dùng | [10] hienThiTrangThaiVaThongBao() | trả về | alt [Thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 26, fragment = 4 (alt tải, opt gửi, alt ghi, opt tự duyệt; có operand kết quả tương ứng). Mỗi request đồng bộ có phản hồi trên cùng đường gọi; lỗi validation/conflict được trả qua chuỗi controller, giao diện và người dùng.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC11 - Trình duyệt yêu cầu của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Định dạng PlantUML, nhãn Tiếng Việt. Tạo hai swimlane Người dùng và Hệ thống. Bố cục thoáng, ưu tiên luồng chính từ trên xuống; dùng guard ngắn, có ngoặc vuông. Đây là sơ đồ luận văn, không vẽ các lớp kỹ thuật.

ĐẶC TẢ
Mô tả: Người có quyền gửi version yêu cầu đủ điều kiện sang IN_REVIEW. Theo UI ở commit được kiểm tra, nút gửi chỉ hiện khi READY; API chấp nhận DRAFT hoặc READY.
Tiền điều kiện: Đã xác thực; project/requirement/version tồn tại; có `requirement.submit_review`; UI yêu cầu version READY.
Hậu điều kiện: Thành công chuyển version và Requirement sang IN_REVIEW, ghi người gửi/thời điểm/ghi chú. Nếu chính sách tự duyệt áp dụng, backend có thể tiếp tục chốt chuẩn. Thất bại không được báo gửi thành công. Hủy đóng hộp thoại, không rollback draft đã autosave.
Tác nhân chính: BA hoặc người có quyền `requirement.submit_review`. Tác nhân phụ: Không có.
Luồng chính: (1) mở yêu cầu; (2) hệ thống tải version/quyền; (3) chọn gửi rà soát khi READY; (4) hệ thống hiện hộp thoại và trường ghi chú tùy chọn; (5) xác nhận; (6) lưu draft và lấy revision; (7) kiểm tra quyền, trạng thái, revision, nội dung và custom values; (8) transaction chuyển version/Requirement IN_REVIEW và ghi audit; (9) xét chính sách tự duyệt; (10) trả kết quả.
Thay thế: (2.1) mở lại version IN_REVIEW, nhập lý do và chuyển về DRAFT nếu trạng thái/revision hợp lệ; (5.1) hủy trước khi gửi; (9.1) không tự duyệt thì giữ IN_REVIEW.
Ngoại lệ: thiếu quyền/hết xác thực; không tìm thấy hoặc project mismatch; lưu draft thất bại; nội dung rỗng/custom value sai; trạng thái sai hoặc revision conflict; transaction/CSDL lỗi. Không tự thêm email/thông báo ngoài.

NODE
I Initial, Người dùng, Bắt đầu khi mở yêu cầu
A1 Action, Người dùng, [1] Mở yêu cầu trong dự án
A2 Action, Hệ thống, [2] Tải version và kiểm tra quyền đọc
D1 Decision, Người dùng, [3] Chọn gửi rà soát hay mở lại chỉnh sửa?
A3 Action, Người dùng, [4] Nhập ghi chú và xác nhận gửi
A4 Action, Hệ thống, [6] Lưu bản nháp và lấy revision mới
D2 Decision, Hệ thống, [7] Quyền, nội dung, trạng thái và revision hợp lệ?
A5 Action, Hệ thống, [8] Chuyển IN_REVIEW và kiểm tra tự duyệt
D3 Decision, Hệ thống, [9] Chính sách tự duyệt áp dụng?
A6 Action, Hệ thống, [10] Trả trạng thái và hiển thị kết quả gửi
A7 Action, Người dùng, [2.1] Chọn mở lại yêu cầu để chỉnh sửa
A8 Action, Hệ thống, [2.1] Yêu cầu lý do mở lại
A9 Action, Người dùng, [2.2] Nhập lý do và xác nhận mở bản nháp
A10 Action, Hệ thống, [2.2] Chuyển version về DRAFT
A11 Action, Người dùng, [5.1] Hủy hộp thoại gửi rà soát
A12 Action, Hệ thống, [7.1] Báo validation, conflict hoặc lỗi ghi
F1 Final, Hệ thống, Kết thúc thành công hoặc hoàn tất mở lại
F2 Final, Hệ thống, Kết thúc không chuyển trạng thái

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Tải xong]
D1 -> A3 [Gửi, version READY]
D1 -> A7 [Mở lại, version IN_REVIEW]
A3 -> A4 [Đã xác nhận]
A3 -> A11 [Hủy]
A4 -> D2 [Đã nhận revision]
D2 -> A5 [Dữ liệu hợp lệ]
D2 -> A12 [Thiếu quyền, validation hoặc conflict]
A5 -> D3 [Đã chuyển IN_REVIEW]
D3 -> A6 [Tự duyệt được phép]
D3 -> A6 [Không tự duyệt, giữ IN_REVIEW]
A6 -> F1 [Đã trả kết quả]
A7 -> A8 [Đã chọn mở lại]
A8 -> A9 [Đã hiển thị hộp thoại]
A9 -> A10 [Đã xác nhận với lý do]
A10 -> F1 [Version trở về DRAFT]
A11 -> F2 [Không gửi]
A12 -> F2 [Không thể khắc phục tại luồng này]

YÊU CẦU: Vẽ đúng node, cạnh, guard và swimlane đã liệt kê. Chỉ một Decision cho mỗi điểm rẽ. Không gộp hành động nhập lý do với lưu dữ liệu. Initial có ghi chú tiền điều kiện. Dùng Final thành công và thất bại riêng, không để node treo. Không thêm bước gửi email.
ĐỐI CHIẾU: Action = 13, Decision = 3, cạnh = 20. Báo kết quả kiểm đếm ở cuối sơ đồ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC11 - Trình duyệt yêu cầu của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Định dạng PlantUML, nhãn Tiếng Việt. Bố cục ngang thoáng, actor ở trái, các tầng ứng dụng theo thứ tự. Sequence chỉ minh họa kịch bản gửi một version READY; dùng alt/opt có guard rõ.

ĐẶC TẢ
Mô tả: Người có quyền gửi version yêu cầu đủ điều kiện sang IN_REVIEW. UI tại commit chỉ hiện nút khi READY; API chấp nhận DRAFT hoặc READY.
Tiền điều kiện: Đã xác thực; project/requirement/version tồn tại; có `requirement.submit_review`; version READY trong kịch bản này.
Hậu điều kiện: Thành công chuyển version và Requirement sang IN_REVIEW, lưu người gửi, thời điểm và ghi chú; nếu chính sách cho phép có thể chốt chuẩn tiếp. Lỗi không được báo thành công.
Tác nhân chính: BA hoặc người có quyền gửi rà soát. Tác nhân phụ: Không có.
Luồng chính: mở yêu cầu, đọc version/quyền, xác nhận gửi sau khi lưu draft, kiểm tra revision/nội dung, transaction cập nhật trạng thái/audit, xét tự duyệt, trả kết quả.
Thay thế: hủy hộp thoại; nếu quyền tự duyệt không áp dụng thì kết quả giữ IN_REVIEW.
Ngoại lệ: thiếu quyền/hết xác thực, không tìm thấy/project mismatch, draft save lỗi, nội dung/custom value sai, state/revision conflict, lỗi transaction/CSDL.

LIFELINE trái sang phải: Người dùng; Giao diện Yêu cầu; Controller/API; Service; Repository; Database.

MESSAGE THEO THỨ TỰ
1 | bước 1 | Người dùng -> Giao diện Yêu cầu | [1] moYeuCau(project_id, requirement_id) | đồng bộ | chính
2 | bước 2 | Giao diện Yêu cầu -> Controller/API | [2] layRequirementVaVersion(requirement_id) | đồng bộ | chính
3 | bước 2 | Controller/API -> Service | [2] docYeuCauVaKiemTraQuyen(requirement_id) | đồng bộ | chính
4 | bước 2 | Service -> Repository | [2] findRequirementAndCurrentVersion(id) | đồng bộ | chính
5 | bước 2 | Repository -> Database | [2] selectRequirementAndVersion(id) | đồng bộ | chính
6 | bước 2 | Database -> Repository | [2] traRequirementVaVersion() | trả về | chính
7 | bước 2 | Repository -> Service | [2] traDuLieuHoacKhongTimThay() | trả về | chính
8 | bước 2 | Service -> Controller/API | [2] traDuLieuVaQuyen() | trả về | chính
9 | bước 2 | Controller/API -> Giao diện Yêu cầu | [2] traChiTietHoacLoi() | trả về | alt [Tải thành công/lỗi]
10 | bước 2 | Giao diện Yêu cầu -> Người dùng | [2] hienThiChiTietHoacLoi() | trả về | alt [Tải thành công/lỗi]
11 | bước 3-5 | Người dùng -> Giao diện Yêu cầu | [3] xacNhanGuiRaSoat(review_note) | đồng bộ | opt [Version READY]
12 | bước 6 | Giao diện Yêu cầu -> Controller/API | [6] luuDraftVaGuiRaSoat(expected_revision, review_note) | đồng bộ | opt [Gửi rà soát]
13 | bước 6 | Controller/API -> Service | [6] saveDraftAndSubmitReview(payload) | đồng bộ | opt [Gửi rà soát]
14 | bước 6 | Service -> Service | [6] validateDraftAndResolveRevision() | tự gọi | opt [Gửi rà soát]
15 | bước 7 | Service -> Repository | [7] transitionVersionToInReview(expected_revision) | đồng bộ | alt [Hợp lệ/conflict]
16 | bước 8 | Repository -> Database | [8] transactionUpdateVersionRequirementAndAudit() | đồng bộ | alt [Ghi thành công/lỗi CSDL]
17 | bước 8 | Database -> Repository | [8] traKetQuaTransaction() | trả về | alt [Ghi thành công/lỗi CSDL]
18 | bước 8 | Repository -> Service | [8] traTrangThaiDaCapNhat() | trả về | alt [Ghi thành công/lỗi CSDL]
19 | bước 9 | Service -> Service | [9] checkAutoApprovalPolicy() | tự gọi | alt [Tự duyệt/giữ IN_REVIEW]
20 | bước 9 | Service -> Repository | [9] baselineRequirement(version_id) | đồng bộ | opt [Tự duyệt]
21 | bước 9 | Repository -> Database | [9] updateBaselineStatus(version_id) | đồng bộ | opt [Tự duyệt]
22 | bước 9 | Database -> Repository | [9] traBaselineResult() | trả về | opt [Tự duyệt]
23 | bước 9 | Repository -> Service | [9] traVersionSauKhiChot() | trả về | opt [Tự duyệt]
24 | bước 10 | Service -> Controller/API | [10] traKetQuaGuiHoacLoi() | trả về | alt [Thành công/lỗi]
25 | bước 10 | Controller/API -> Giao diện Yêu cầu | [10] traResponse() | trả về | alt [Thành công/lỗi]
26 | bước 10 | Giao diện Yêu cầu -> Người dùng | [10] hienThiTrangThaiVaThongBao() | trả về | alt [Thành công/lỗi]

YÊU CẦU: Giữ đúng thứ tự, đủ 6 lifeline và 26 message; dùng activation bar, self-message cho validate và kiểm tra chính sách; không gọi nhảy lớp. alt/opt phải ghi guard dễ hiểu, return theo tầng phải thể hiện. Không thêm tác nhân ngoài hoặc thông báo email.
KIỂM TRA: lifeline = 6, message = 26, fragment = 4. Báo kết quả đối chiếu sau sơ đồ.
```

## TỰ KIỂM TRA UC11

- [x] Phần 1 đối chiếu UI, API, quyền, trạng thái, revision và lỗi có căn cứ.
- [x] Phần 2 có đủ mô tả, điều kiện, tác nhân và ba luồng; nhánh đánh số theo điểm rẽ.
- [x] Activity: 13 Action, 3 Decision, 20 cạnh; hai kết quả cuối riêng.
- [x] Sequence: 6 lifeline, 26 message; request theo tầng và có phản hồi.
- [x] Prompt chép đủ đặc tả và bảng phân rã; giữ phạm vi một kịch bản dễ đọc.

## Bảng theo dõi sau UC11

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC12 - Xét duyệt yêu cầu

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tác nhân/tiền điều kiện | MƠ HỒ | “Admin” dễ bị hiểu là chỉ có một vai trò cố định; API kiểm tra các quyền dự án `requirement.review` và `requirement.approve`, kèm chính sách không tự duyệt. | Ghi người rà soát/chấp nhận là người có quyền tương ứng, đồng thời giữ BA/Admin như tên vai trò nghiệp vụ. |
| 2-3 | THIẾU | Chưa nêu dữ liệu phải xem, trạng thái IN_REVIEW hay tình huống không tìm thấy/không có quyền. | Thêm tải version hiện hành, tiêu chí chấp nhận, kết quả rà soát và kiểm tra quyền/trạng thái. |
| 4-9 | MÂU THUẪN | Đặc tả gộp ghi nhận rà soát, trả chỉnh sửa và chấp nhận thành một quy trình; đây là ba kết quả khác nhau. | Tách thành ba lựa chọn. Ghi nhận rà soát giữ IN_REVIEW; yêu cầu chỉnh sửa trả về DRAFT; chấp nhận chuyển BASELINED. |
| 4-9 | THIẾU | “Cập nhật trạng thái” không nói version nào thành chuẩn, tiêu chí nào được cập nhật, hay kết quả lập chỉ mục. | Chốt hành vi baseline: cập nhật version chuẩn, chấp nhận tiêu chí draft liên quan, ghi audit, sau đó lập chỉ mục. Không coi lập chỉ mục là điều kiện đã thành công nếu API báo chưa xong. |
| 7.1 | MƠ HỒ | “Còn vấn đề bắt buộc chỉnh sửa” chưa định nghĩa nguồn đánh giá. | Dựa trên `requirement_findings`; lỗi severity error chặn baseline. Cảnh báo không tự suy thành lỗi chặn. |
| 6.1-6.2 | THIẾU | Hủy được mô tả chỉ cho phê duyệt dù hai lựa chọn còn lại cũng có hộp thoại xác nhận. | Ghi hủy từng hộp thoại trước khi gọi API thì không thay đổi trạng thái. |
| Ngoại lệ | THIẾU | Chưa nêu revision conflict, trạng thái thay đổi, tự duyệt bị cấm, tiêu chí lint chặn, lỗi transaction/lập chỉ mục. | Thêm lỗi có căn cứ; phân biệt transaction baseline và bước indexing sau đó. |
| Quyền | THIẾU | Chưa kiểm tra trường hợp reviewer là tác giả hoặc không có quyền cụ thể. | Nêu kiểm tra policy không tự rà soát/chấp nhận chính mình và quyền theo thao tác; trả lỗi quyền nếu không đáp ứng. |

Đã kiểm: **3 điểm rẽ, 5 nhánh xử lý, 8 nhóm lỗi** gồm hết xác thực/thiếu quyền, không tìm thấy/project mismatch, trạng thái không phải IN_REVIEW, revision conflict, reviewer tự duyệt bị cấm, finding severity error, lỗi transaction/CSDL và lỗi lập chỉ mục sau baseline. CRUD không áp dụng cho UC xét duyệt. Chưa có căn cứ về gửi email nên không thêm tác nhân ngoài.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền rà soát một version yêu cầu đang IN_REVIEW, có thể ghi nhận rà soát, trả về DRAFT để chỉnh sửa hoặc chấp nhận làm version chuẩn.

**Tiền điều kiện:** Người dùng đã xác thực; project, requirement và version tồn tại; version hiện tại IN_REVIEW. Thao tác ghi nhận/trả chỉnh sửa cần quyền `requirement.review`; chấp nhận cần `requirement.approve` và thỏa chính sách không tự duyệt.

**Hậu điều kiện:**
- Ghi nhận rà soát: version vẫn IN_REVIEW, lưu ghi chú kỹ thuật, người rà soát, thời điểm và revision đã rà.
- Yêu cầu chỉnh sửa: version và Requirement chuyển DRAFT; lưu ghi chú, người yêu cầu và thời điểm.
- Chấp nhận: version chuyển BASELINED, cập nhật baseline hiện hành, ghi nhận người chấp nhận/thời điểm/ghi chú, cập nhật tiêu chí draft sang approved và audit. Sau transaction, hệ thống thử lập chỉ mục; lỗi indexing không đảo ngược transaction baseline.
- Thất bại/hủy: không được báo kết quả chuyển trạng thái thành công; hủy trước gửi không đổi trạng thái.

**Tác nhân chính:** Người rà soát được cấp quyền tương ứng; có thể là Admin theo vai trò nghiệp vụ.

**Tác nhân phụ:** Không có tác nhân ngoài được xác nhận. Bộ lập chỉ mục là xử lý nội bộ.

**Luồng sự kiện chính: Chấp nhận version yêu cầu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở version đang IN_REVIEW. | |
| 2 | | Kiểm tra quyền đọc, tải nội dung, tiêu chí chấp nhận, quy tắc và revision. |
| 3 | Rà soát nội dung và chọn Chấp nhận Requirement. | |
| 4 | | Hiển thị xác nhận cùng trường ghi chú rà soát tùy chọn. |
| 5 | Nhập ghi chú nếu cần và xác nhận. | |
| 6 | | Kiểm tra quyền `requirement.approve`, trạng thái IN_REVIEW, revision và chính sách không tự duyệt. |
| 7 | | Đánh giá findings; nếu có severity error thì từ chối baseline. |
| 8 | | Trong transaction, chuyển version sang BASELINED, cập nhật baseline hiện hành, tiêu chí liên quan và audit. |
| 9 | | Thử lập chỉ mục version baseline. |
| 10 | | Trả trạng thái baseline/indexing và hiển thị kết quả. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Chọn Ghi nhận rà soát, nhập ghi chú và xác nhận. | Kiểm tra `requirement.review`, trạng thái/revision; lưu ghi chú kỹ thuật, reviewer và revision đã rà; giữ IN_REVIEW. Trả kết quả và kết thúc. |
| 3.2 | Chọn Yêu cầu chỉnh sửa, nhập nhận xét/lý do và xác nhận Trả về bản nháp. | Kiểm tra `requirement.review`, trạng thái/revision và chính sách không tự duyệt; transaction chuyển version/Requirement sang DRAFT, lưu nhận xét và audit. Trả kết quả, kết thúc. |
| 5.1 | Hủy hộp thoại. | Đóng hộp thoại, không gọi thao tác chuyển trạng thái; kết thúc nhánh. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Hết xác thực/không có quyền đọc hoặc version không tìm thấy: từ chối tải, báo lỗi; kết thúc thất bại. |
| 6.1 | | Thiếu quyền chấp nhận hoặc reviewer vi phạm chính sách không tự duyệt: từ chối thao tác; không đổi trạng thái. |
| 6.2 | | Version không còn IN_REVIEW, project mismatch hoặc revision đã đổi: trả lỗi/conflict và yêu cầu tải lại. |
| 7.1 | | Có finding severity error: trả `REQUIREMENT_LINT_BLOCKED` cùng findings; yêu cầu chuyển UC10 để sửa. |
| 8.1 | | Transaction cập nhật version/baseline/tiêu chí/audit thất bại: rollback, báo lỗi; không xác nhận baseline. |
| 9.1 | | Lập chỉ mục thất bại sau khi baseline transaction thành công: báo trạng thái baseline kèm indexing chưa sẵn sàng; không mô tả như thể transaction bị rollback. |
| 3.1.1 | | Ghi nhận rà soát sai trạng thái/revision hoặc lỗi CSDL: không lưu kết quả; thông báo thất bại. |
| 3.2.1 | | Yêu cầu chỉnh sửa sai trạng thái/revision hoặc thiếu quyền: không chuyển về DRAFT; báo lỗi. |

**Giả định / Câu hỏi cần làm rõ:** Bảng gốc gọi reviewer là Admin, còn quyền thực tế dựa trên quyền dự án và policy. Tên tiếng Việt của `BASELINED` nên được thống nhất trong luận văn, chẳng hạn “đã chốt chuẩn”. Thông báo indexing lỗi cụ thể chưa được xác định trong bảng gốc.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu khi mở version IN_REVIEW |
| A1 | 1 | Action | Người dùng | [1] Mở version yêu cầu đang rà soát |
| A2 | 2 | Action | Hệ thống | [2] Tải nội dung và kiểm tra quyền đọc |
| D0 | 2 | Decision | Hệ thống | [2] Tải được dữ liệu và đủ quyền đọc? |
| A3 | 3 | Action | Người dùng | [3] Đọc nội dung và chọn kết quả rà soát |
| D1 | 3 | Decision | Người dùng | [3] Chọn chấp nhận, ghi nhận hay yêu cầu sửa? |
| A4 | 4-5 | Action | Người dùng | [4] Nhập ghi chú và xác nhận chấp nhận |
| A5 | 6 | Action | Hệ thống | [6] Kiểm tra quyền, trạng thái, revision và policy |
| D2 | 6 | Decision | Hệ thống | [6] Điều kiện thao tác hợp lệ? |
| A6 | 7 | Action | Hệ thống | [7] Đánh giá findings của version |
| D3 | 7 | Decision | Hệ thống | [7] Có finding severity error? |
| A7 | 8-9 | Action | Hệ thống | [8] Chốt baseline, tiêu chí, audit và lập chỉ mục |
| A8 | 10 | Action | Hệ thống | [10] Trả kết quả chấp nhận |
| A9 | 3.1 | Action | Người dùng | [3.1] Ghi chú kết quả rà soát |
| A10 | 3.1 | Action | Hệ thống | [3.1] Lưu kết quả, giữ IN_REVIEW |
| A11 | 3.2 | Action | Người dùng | [3.2] Nhập nhận xét yêu cầu chỉnh sửa |
| A12 | 3.2 | Action | Hệ thống | [3.2] Chuyển version về DRAFT |
| A13 | 5.1 | Action | Người dùng | [5.1] Hủy hộp thoại |
| A14 | 2.1/6.1 | Action | Hệ thống | [2.1] Báo lỗi tải, quyền, trạng thái hoặc revision |
| A15 | 7.1 | Action | Hệ thống | [7.1] Hiển thị findings chặn baseline |
| F1 | 10/3.1/3.2 | Final | Hệ thống | Kết thúc với kết quả thao tác đã ghi nhận |
| F2 | 5.1/2.1/6.1/7.1 | Final | Hệ thống | Kết thúc không chấp nhận version |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D0 | Đã yêu cầu tải dữ liệu |
| D0 | A3 | [Tải thành công và đủ quyền đọc] |
| D0 | A14 | [Hết xác thực, thiếu quyền hoặc không tìm thấy] |
| A3 | D1 | Đã xem version |
| D1 | A4 | [Chấp nhận] |
| D1 | A9 | [Ghi nhận rà soát] |
| D1 | A11 | [Yêu cầu chỉnh sửa] |
| A4 | A13 | [Hủy] |
| A4 | A5 | Đã xác nhận |
| A5 | D2 | Kiểm tra quyền/state/revision/policy xong |
| D2 | A6 | [Điều kiện hợp lệ] |
| D2 | A14 | [Thiếu quyền, sai trạng thái, self-review bị cấm hoặc conflict] |
| A6 | D3 | Findings đã được đánh giá |
| D3 | A15 | [Có severity error] |
| D3 | A7 | [Không có severity error] |
| A7 | A8 | Baseline transaction thành công, đã có trạng thái indexing |
| A8 | F1 | Kết quả đã trả |
| A9 | A10 | Đã xác nhận ghi chú |
| A10 | F1 | Đã lưu, vẫn IN_REVIEW |
| A11 | A12 | Đã xác nhận nhận xét |
| A12 | F1 | Đã chuyển DRAFT |
| A13 | F2 | Đã hủy trước API |
| A14 | F2 | Thao tác không thể tiếp tục |
| A15 | F2 | Baseline bị chặn |

### 3c. Số liệu

N = 10 ô bước/người dùng/hệ thống có nội dung trong các luồng chính và thay thế; M = 15 Action; D = 3 Decision; E = 26 cạnh. Kết quả ghi nhận/chỉnh sửa/chấp nhận đi tới Final thành công; hủy, lỗi và findings chặn đi tới Final thất bại.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa một lần chấp nhận version. Ghi nhận rà soát và yêu cầu chỉnh sửa là hai lựa chọn khác được trình bày trong Activity và trong alt.

### 4a. Lifeline trái sang phải

Người dùng → Giao diện Yêu cầu → Controller/API → Service → Repository → Database. Không có hệ thống ngoài. Lập chỉ mục là xử lý nội bộ sau baseline transaction.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện Yêu cầu | [1] moVersion(requirement_id, version_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Yêu cầu | Controller/API | [2] layVersionDangReview(version_id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] docVersionVaKiemTraQuyen(version_id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findVersionAndCriteria(version_id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectVersionCriteriaAndFindings(version_id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traVersionCriteriaFindings() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traDuLieu() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traChiTietHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Yêu cầu | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Yêu cầu | Người dùng | [2] hienThiNoiDungVaLoi() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Người dùng | Giao diện Yêu cầu | [3] xacNhanChapNhan(review_note) | đồng bộ | opt [Chấp nhận] |
| 12 | 6 | Giao diện Yêu cầu | Controller/API | [6] approveRequirement(expected_revision, review_note) | đồng bộ | opt [Chấp nhận] |
| 13 | 6-7 | Controller/API | Service | [6] baselineRequirement(version_id, payload) | đồng bộ | opt [Chấp nhận] |
| 14 | 6 | Service | Service | [6] checkPermissionStateRevisionAndSelfReview() | tự gọi | opt [Chấp nhận] |
| 15 | 7 | Service | Repository | [7] loadAcceptanceCriteriaAndEvaluateFindings(version_id) | đồng bộ | alt [Có lỗi chặn/không có lỗi chặn] |
| 16 | 7 | Repository | Database | [7] selectCriteriaAndRequirement(version_id) | đồng bộ | alt [Đánh giá findings] |
| 17 | 7 | Database | Repository | [7] traCriteriaVaRequirement() | trả về | alt [Đánh giá findings] |
| 18 | 7 | Repository | Service | [7] traDuLieuDanhGia() | trả về | alt [Đánh giá findings] |
| 19 | 8 | Service | Repository | [8] baselineVersionAndApproveCriteria(expected_revision) | đồng bộ | alt [Không lỗi chặn/transaction lỗi] |
| 20 | 8 | Repository | Database | [8] transactionUpdateBaselineCriteriaAndAudit() | đồng bộ | alt [Transaction thành công/lỗi] |
| 21 | 8 | Database | Repository | [8] traKetQuaTransaction() | trả về | alt [Transaction thành công/lỗi] |
| 22 | 8 | Repository | Service | [8] traVersionBaseline() | trả về | alt [Transaction thành công/lỗi] |
| 23 | 9 | Service | Service | [9] indexRequirementVersion(version_id) | tự gọi | opt [Baseline thành công] |
| 24 | 10 | Service | Controller/API | [10] traBaselineVaIndexStatus() | trả về | alt [Thành công/lỗi indexing] |
| 25 | 10 | Controller/API | Giao diện Yêu cầu | [10] traKetQuaChapNhan() | trả về | alt [Thành công/lỗi] |
| 26 | 10 | Giao diện Yêu cầu | Người dùng | [10] hienThiBaselineVaIndexStatus() | trả về | alt [Thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 26, fragment = 4: alt tải, opt chấp nhận, alt findings/transaction, opt lập chỉ mục. Không vẽ tác nhân ngoài. Các lỗi được trả về tầng giao diện; lỗi indexing không biến thành rollback baseline.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC12 - Xét duyệt yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. Định dạng PlantUML, nhãn Tiếng Việt; hai swimlane Người dùng và Hệ thống. Bố cục gọn, phân biệt ba kết quả rà soát, tránh đưa tên lớp hay tên hàm vào nhãn.

ĐẶC TẢ
Mô tả: Người có quyền rà soát version IN_REVIEW; có thể ghi nhận rà soát, yêu cầu sửa hoặc chấp nhận thành baseline.
Tiền điều kiện: Đã xác thực, version/project tồn tại, version IN_REVIEW; quyền review/approve phù hợp, không vi phạm chính sách tự duyệt.
Hậu điều kiện: Ghi nhận review giữ IN_REVIEW; yêu cầu sửa chuyển DRAFT; chấp nhận chuyển BASELINED, cập nhật baseline/criteria/audit và thử indexing. Lỗi/hủy không báo chuyển trạng thái thành công.
Tác nhân chính: Reviewer/Admin theo nghiệp vụ, quyền thực tế theo project. Tác nhân phụ: Không có.
Luồng chính: (1) mở version; (2) hệ thống tải nội dung, tiêu chí, revision; (3) reviewer chọn chấp nhận; (4) nhập ghi chú; (5) xác nhận; (6) kiểm tra quyền/trạng thái/revision/policy; (7) findings severity error chặn; (8) transaction baseline, approve criteria, audit; (9) indexing; (10) trả kết quả.
Thay thế: (3.1) ghi nhận rà soát, vẫn IN_REVIEW; (3.2) yêu cầu chỉnh sửa, chuyển DRAFT; (5.1) hủy.
Ngoại lệ: hết xác thực/thiếu quyền, không tìm thấy/project mismatch, sai trạng thái, revision conflict, cấm tự duyệt, finding error, transaction/CSDL hoặc indexing lỗi. Indexing lỗi sau baseline không rollback transaction.

NODE
I Initial Người dùng Bắt đầu khi mở version IN_REVIEW
A1 Action Người dùng [1] Mở version yêu cầu đang rà soát
A2 Action Hệ thống [2] Tải nội dung và kiểm tra quyền đọc
A3 Action Người dùng [3] Đọc nội dung và chọn kết quả rà soát
D1 Decision Người dùng [3] Chọn chấp nhận, ghi nhận hay yêu cầu sửa?
A4 Action Người dùng [4] Nhập ghi chú và xác nhận chấp nhận
A5 Action Hệ thống [6] Kiểm tra quyền, trạng thái, revision và findings
D2 Decision Hệ thống [7] Có finding severity error?
A6 Action Hệ thống [8] Chốt baseline, tiêu chí và lập chỉ mục
A7 Action Hệ thống [10] Trả kết quả chấp nhận
A8 Action Người dùng [3.1] Ghi chú kết quả rà soát
A9 Action Hệ thống [3.1] Lưu kết quả, giữ IN_REVIEW
A10 Action Người dùng [3.2] Nhập nhận xét yêu cầu chỉnh sửa
A11 Action Hệ thống [3.2] Chuyển version về DRAFT
A12 Action Người dùng [5.1] Hủy hộp thoại
A13 Action Hệ thống [6.1] Báo lỗi quyền, trạng thái hoặc transaction
A14 Action Hệ thống [7.1] Hiển thị findings chặn baseline
F1 Final Hệ thống Kết thúc với kết quả thao tác đã ghi nhận
F2 Final Hệ thống Kết thúc không chấp nhận version

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> A3 [Dữ liệu tải thành công]
A3 -> D1 [Đã xem version]
D1 -> A4 [Chấp nhận]
D1 -> A8 [Ghi nhận rà soát]
D1 -> A10 [Yêu cầu chỉnh sửa]
A4 -> A5 [Đã xác nhận]
A4 -> A12 [Hủy]
A5 -> D2 [Kiểm tra xong]
D2 -> A14 [Có finding severity error]
D2 -> A6 [Không có finding severity error]
A6 -> A7 [Baseline transaction xong, đã có trạng thái indexing]
A7 -> F1 [Đã hiển thị kết quả]
A8 -> A9 [Đã xác nhận ghi chú]
A9 -> F1 [Đã lưu, vẫn IN_REVIEW]
A10 -> A11 [Đã xác nhận nhận xét]
A11 -> F1 [Đã chuyển DRAFT]
A12 -> F2 [Đã hủy]
A13 -> F2 [Lỗi quyền/trạng thái/transaction]
A14 -> F2 [Baseline bị chặn]

YÊU CẦU: Không gộp ba lựa chọn. Giữ guard trên các cạnh rẽ, không thêm email. Initial ghi tiền điều kiện. Final thành công và thất bại riêng; lỗi indexing phải cho thấy baseline transaction vẫn có thể đã thành công.
KIỂM TRA: Action = 15, Decision = 3, cạnh = 26. Báo kiểm đếm cuối sơ đồ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC12 - Xét duyệt yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. Định dạng PlantUML, nhãn Tiếng Việt. Bố cục ngang, actor và UI bên trái, các tầng backend tuần tự. Minh họa kịch bản chấp nhận một version; không vẽ hết chức năng quản lý yêu cầu.

ĐẶC TẢ
Mô tả: Reviewer có quyền chấp nhận version IN_REVIEW làm BASELINED.
Tiền điều kiện: Đã xác thực, version tồn tại/IN_REVIEW, có `requirement.approve`, policy không tự duyệt được thỏa.
Hậu điều kiện: Version BASELINED, baseline hiện hành và tiêu chí draft được cập nhật, audit được ghi; indexing được thử sau transaction. Error finding chặn baseline. Lỗi indexing không rollback baseline.
Tác nhân chính: Reviewer/Admin theo nghiệp vụ. Tác nhân phụ: Không có.
Luồng chính: đọc version/criteria, xác nhận chấp nhận, validate quyền/state/revision/findings, transaction baseline và audit, indexing, trả kết quả.
Thay thế: ghi nhận review hoặc yêu cầu chỉnh sửa là hai lựa chọn khác; hủy không gọi API.
Ngoại lệ: thiếu quyền/hết xác thực, không tìm thấy/project mismatch, state/revision conflict, self-review bị cấm, lint blocked, lỗi transaction hoặc indexing.

LIFELINE: Người dùng; Giao diện Yêu cầu; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Người dùng -> Giao diện Yêu cầu | [1] moVersion(requirement_id, version_id) | đồng bộ | chính
2 | 2 | Giao diện Yêu cầu -> Controller/API | [2] layVersionDangReview(version_id) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] docVersionVaKiemTraQuyen(version_id) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findVersionAndCriteria(version_id) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectVersionCriteriaAndFindings(version_id) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traVersionCriteriaFindings() | trả về | chính
7 | 2 | Repository -> Service | [2] traDuLieu() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traChiTietHoacLoi() | trả về | chính
9 | 2 | Controller/API -> Giao diện Yêu cầu | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Yêu cầu -> Người dùng | [2] hienThiNoiDungVaLoi() | trả về | alt [Tải thành công/lỗi]
11 | 3-5 | Người dùng -> Giao diện Yêu cầu | [3] xacNhanChapNhan(review_note) | đồng bộ | opt [Chấp nhận]
12 | 6 | Giao diện Yêu cầu -> Controller/API | [6] approveRequirement(expected_revision, review_note) | đồng bộ | opt [Chấp nhận]
13 | 6-7 | Controller/API -> Service | [6] baselineRequirement(version_id, payload) | đồng bộ | opt [Chấp nhận]
14 | 6 | Service -> Service | [6] checkPermissionStateRevisionAndSelfReview() | tự gọi | opt [Chấp nhận]
15 | 7 | Service -> Repository | [7] loadAcceptanceCriteriaAndEvaluateFindings(version_id) | đồng bộ | alt [Có lỗi chặn/không lỗi chặn]
16 | 7 | Repository -> Database | [7] selectCriteriaAndRequirement(version_id) | đồng bộ | alt [Đánh giá findings]
17 | 7 | Database -> Repository | [7] traCriteriaVaRequirement() | trả về | alt [Đánh giá findings]
18 | 7 | Repository -> Service | [7] traDuLieuDanhGia() | trả về | alt [Đánh giá findings]
19 | 8 | Service -> Repository | [8] baselineVersionAndApproveCriteria(expected_revision) | đồng bộ | alt [Transaction thành công/lỗi]
20 | 8 | Repository -> Database | [8] transactionUpdateBaselineCriteriaAndAudit() | đồng bộ | alt [Transaction thành công/lỗi]
21 | 8 | Database -> Repository | [8] traKetQuaTransaction() | trả về | alt [Transaction thành công/lỗi]
22 | 8 | Repository -> Service | [8] traVersionBaseline() | trả về | alt [Transaction thành công/lỗi]
23 | 9 | Service -> Service | [9] indexRequirementVersion(version_id) | tự gọi | opt [Baseline transaction thành công]
24 | 10 | Service -> Controller/API | [10] traBaselineVaIndexStatus() | trả về | alt [Thành công/lỗi indexing]
25 | 10 | Controller/API -> Giao diện Yêu cầu | [10] traKetQuaChapNhan() | trả về | alt [Thành công/lỗi]
26 | 10 | Giao diện Yêu cầu -> Người dùng | [10] hienThiBaselineVaIndexStatus() | trả về | alt [Thành công/lỗi]

YÊU CẦU: Đủ 6 lifeline, 26 message, activation bar; self-message cho kiểm tra nội bộ; không gọi nhảy lớp. Mỗi đồng bộ có return theo cùng đường gọi. Dùng alt/opt theo guard; lỗi indexing không biểu diễn rollback transaction.
KIỂM TRA: lifeline = 6, message = 26, fragment = 4. Báo kết quả đối chiếu cuối sơ đồ.
```

## TỰ KIỂM TRA UC12

- [x] Phần 1 tách ba kết quả và các quyền/API tương ứng.
- [x] Phần 2 có các luồng chính, thay thế, ngoại lệ; kết quả indexing phân biệt với transaction.
- [x] Activity: 15 Action, 3 Decision, 26 cạnh.
- [x] Sequence: 6 lifeline, 26 message, bốn nhóm fragment.
- [x] Prompt tự đủ, giới hạn sơ đồ Sequence vào kịch bản chấp nhận.

## Bảng theo dõi sau UC12

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC13 - Quản lý hiệu lực yêu cầu

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | Chưa kiểm quyền đọc, tải version hiện tại và ghi rõ trường hợp không tìm thấy yêu cầu. | Bổ sung kiểm tra quyền theo thao tác và tải trạng thái/version/revision. |
| 3-8 | MƠ HỒ | “Không còn hiệu lực” nghe như cờ độc lập, trong khi backend chuyển Requirement và current version sang OBSOLETE. | Nêu đúng chuyển trạng thái, lưu reason, actor/thời điểm và giữ nguyên lịch sử. |
| 3-8 | THIẾU | Thiếu kiểm soát expected current version để tránh lưu trữ nhầm khi có cập nhật đồng thời. | Kiểm tra ID version hiện hành và revision trong transaction; conflict thì từ chối. |
| 1.1 | SAI | Nhánh khôi phục đánh số 1.1 dù rẽ từ lựa chọn thao tác sau khi tải chi tiết. | Đánh lại nhánh 2.1; chỉ khôi phục item đang OBSOLETE, dùng trạng thái đã lưu trước đó. |
| 1.2 | THIẾU | Lưu trữ hàng loạt chưa tách xem trước, xác nhận và kết quả từng item. | Mô tả preview là tùy chọn; sau xác nhận xử lý item hợp lệ và trả kết quả từng item, không giả định cả lô cùng thành công. |
| Hủy | THIẾU | Bước 6.1 hủy chỉ áp dụng luồng lưu trữ đơn; chưa áp dụng khôi phục và batch. | Cho phép đóng hộp thoại trước khi gửi ở các thao tác có xác nhận; không cập nhật trạng thái. |
| Ngoại lệ | THIẾU | Chưa nêu thiếu quyền, lý do không hợp lệ, version conflict, sai trạng thái, project mismatch, lỗi CSDL và lỗi từng item batch. | Bổ sung nhánh tương ứng; batch ghi rõ kết quả riêng. |
| Tác nhân | MƠ HỒ | “BA” không phải ràng buộc trong API. Lưu trữ và khôi phục có quyền riêng. | Ghi BA là vai trò nghiệp vụ; kiểm tra `requirement.archive` hoặc `requirement.restore`. |

Đã kiểm: **3 điểm rẽ, 4 nhánh nghiệp vụ, 8 nhóm lỗi** gồm hết xác thực/thiếu quyền, không tìm thấy/project mismatch, reason không hợp lệ, state/version conflict, item batch không đủ điều kiện, lỗi transaction/CSDL và hủy. Đây là quản lý hiệu lực/lưu trữ, không phải xóa cứng; lịch sử version được giữ.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền chuyển một yêu cầu hoặc các yêu cầu được chọn sang OBSOLETE; có thể khôi phục riêng một yêu cầu về trạng thái trước khi lưu trữ.

**Tiền điều kiện:** Đã xác thực; dự án/yêu cầu tồn tại; có `requirement.archive` để lưu trữ hoặc `requirement.restore` để khôi phục. Thao tác dùng version hiện hành/revision mà người dùng đã tải.

**Hậu điều kiện:**
- Thành công: Requirement và version hiện hành chuyển OBSOLETE khi lưu trữ; lưu lý do, người thao tác, thời điểm; version/history không bị xóa. Khôi phục đưa Requirement/version về trạng thái đã lưu trước khi OBSOLETE.
- Batch: mỗi item có kết quả; có thể thành công một phần.
- Thất bại/hủy: không được coi là đã cập nhật; conflict đơn lẻ không ghi đè trạng thái mới. Hủy trước gửi không thay đổi hiệu lực.

**Tác nhân chính:** BA hoặc người có quyền archive/restore trong dự án.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính: Lưu trữ một yêu cầu**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn yêu cầu trong danh sách. | |
| 2 | | Kiểm tra quyền đọc, hiển thị trạng thái, version hiện tại và revision. |
| 3 | Chọn Đánh dấu không còn hiệu lực. | |
| 4 | | Hiển thị hộp thoại yêu cầu lý do. |
| 5 | Nhập lý do và xác nhận. | |
| 6 | | Kiểm tra `requirement.archive`, reason, trạng thái và expected current version. |
| 7 | | Trong transaction, chuyển Requirement và version hiện hành sang OBSOLETE, lưu reason và audit. |
| 8 | | Trả kết quả, tải lại danh sách/chi tiết. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | Chọn yêu cầu OBSOLETE và chọn Khôi phục. | Hiển thị trạng thái lưu trước đó và hộp thoại lý do khôi phục. |
| 2.2 | Nhập lý do, xác nhận. | Kiểm tra `requirement.restore`, state OBSOLETE và expected current version; transaction khôi phục trạng thái đã lưu, ghi audit, tải lại chi tiết. Kết thúc. |
| 2.3 | Chọn nhiều yêu cầu, chọn Lưu trữ hàng loạt. | Hiển thị form lý do; có thể preview các mục đủ điều kiện trước xác nhận. |
| 2.4 | Nhập lý do, xem trước nếu muốn và xác nhận. | Xử lý từng item phù hợp, chuyển item thành công sang OBSOLETE, trả kết quả theo item. Kết thúc. |
| 5.1 | Hủy hộp thoại trước khi xác nhận. | Đóng hộp thoại, không gọi thao tác cập nhật; kết thúc nhánh. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1.1 | | Hết xác thực/thiếu quyền đọc hoặc yêu cầu không tồn tại: từ chối tải và kết thúc thất bại. |
| 6.1 | | Thiếu `requirement.archive`, reason không hợp lệ, project mismatch hoặc expected version cũ: trả lỗi/conflict, không ghi đè. |
| 6.2 | | Version hiện hành không thuộc trạng thái được lưu trữ hoặc đã thay đổi: từ chối cập nhật. |
| 2.2.1 | | Yêu cầu không ở OBSOLETE, version không hợp lệ hoặc expected version conflict: từ chối khôi phục. |
| 2.4.1 | | Item batch không tìm thấy, không đủ điều kiện hoặc conflict: báo kết quả FAILED cho item đó, tiếp tục/trả kết quả các item khác theo API. |
| 7.1 | | Transaction/CSDL lỗi: rollback thay đổi đơn, báo thất bại. |
| 5.1 | | Người dùng hủy: không có trạng thái mới được ghi. |

**Giả định / Câu hỏi cần làm rõ:** UI batch có preview tùy chọn; tiêu chí chi tiết một item đủ điều kiện phụ thuộc API và nên được nêu trong phần thiết kế, không tự thêm quy tắc nghiệp vụ ngoài. “Khôi phục về trạng thái trước đó” dựa vào metadata `status_before_obsolete`; backend có fallback khi metadata không có, nên cần quyết định liệu có công bố fallback này trong luận văn hay không.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu ở danh sách yêu cầu |
| A1 | 1 | Action | Người dùng | [1] Chọn yêu cầu cần đổi hiệu lực |
| A2 | 2 | Action | Hệ thống | [2] Tải trạng thái, version và kiểm tra quyền |
| D1 | 3 | Decision | Người dùng | [3] Chọn lưu trữ đơn, khôi phục hay lưu trữ hàng loạt? |
| A3 | 3 | Action | Người dùng | [3] Chọn đánh dấu không còn hiệu lực |
| A4 | 4-5 | Action | Người dùng | [4] Nhập lý do và xác nhận lưu trữ |
| D2 | 6 | Decision | Hệ thống | [6] Quyền, lý do, trạng thái và version hợp lệ? |
| A5 | 7-8 | Action | Hệ thống | [7] Chuyển trạng thái sang OBSOLETE và trả kết quả |
| A6 | 2.1-2.2 | Action | Người dùng | [2.1] Chọn khôi phục và nhập lý do |
| A7 | 2.2 | Action | Hệ thống | [2.2] Khôi phục trạng thái đã lưu |
| A8 | 2.3-2.4 | Action | Người dùng | [2.3] Chọn batch, nhập lý do và xác nhận |
| A9 | 2.4 | Action | Hệ thống | [2.4] Xử lý item và trả kết quả từng mục |
| A10 | 5.1 | Action | Người dùng | [5.1] Hủy hộp thoại |
| A11 | 6.1/7.1 | Action | Hệ thống | [6.1] Báo lỗi hoặc conflict |
| F1 | 8/2.2/2.4 | Final | Hệ thống | Kết thúc thao tác đã trả kết quả |
| F2 | 5.1/6.1 | Final | Hệ thống | Kết thúc không cập nhật |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Dữ liệu tải thành công |
| D1 | A3 | [Lưu trữ một yêu cầu] |
| D1 | A6 | [Khôi phục một yêu cầu] |
| D1 | A8 | [Lưu trữ hàng loạt] |
| A3 | A4 | Đã chọn lưu trữ |
| A4 | D2 | Đã nhập reason và xác nhận |
| A4 | A10 | [Hủy] |
| D2 | A5 | [Đủ quyền, reason và version hợp lệ] |
| D2 | A11 | [Thiếu quyền, reason sai hoặc conflict] |
| A5 | F1 | Đã trả kết quả OBSOLETE |
| A6 | A7 | Đã xác nhận khôi phục |
| A7 | F1 | Khôi phục thành công |
| A8 | A9 | Đã xác nhận batch |
| A9 | F1 | Đã trả kết quả từng item |
| A10 | F2 | Không gửi cập nhật |
| A11 | F2 | Không ghi đè trạng thái |

### 3c. Số liệu

N = 10 ô bước có nội dung trong luồng chính và thay thế; M = 11 Action; D = 2 Decision; E = 18 cạnh. Batch có thể trả kết quả hỗn hợp; thành công và thất bại có Final riêng.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa lưu trữ một yêu cầu. Khôi phục và batch giữ nguyên trong Activity để sơ đồ tuần tự vẫn phù hợp quy mô luận văn.

### 4a. Lifeline trái sang phải

Người dùng → Giao diện Yêu cầu → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện Yêu cầu | [1] chonYeuCau(requirement_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Yêu cầu | Controller/API | [2] layYeuCauVaVersion(id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] docYeuCauVaKiemTraQuyen(id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findRequirementAndVersion(id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectRequirementAndVersion(id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traYeuCauVaVersion() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traDuLieu() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traChiTietHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Yêu cầu | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Yêu cầu | Người dùng | [2] hienThiTrangThaiHoacLoi() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Người dùng | Giao diện Yêu cầu | [3] xacNhanLuuTru(reason) | đồng bộ | opt [Xác nhận] |
| 12 | 6 | Giao diện Yêu cầu | Controller/API | [6] archiveRequirement(expected_current_version_id, reason) | đồng bộ | opt [Lưu trữ] |
| 13 | 6 | Controller/API | Service | [6] makeRequirementObsolete(payload) | đồng bộ | opt [Lưu trữ] |
| 14 | 6 | Service | Service | [6] checkPermissionAndExpectedVersion() | tự gọi | opt [Lưu trữ] |
| 15 | 7 | Service | Repository | [7] markRequirementAndVersionObsolete(expected_version) | đồng bộ | alt [Hợp lệ/conflict] |
| 16 | 7 | Repository | Database | [7] transactionUpdateRequirementVersionAndAudit() | đồng bộ | alt [Ghi thành công/lỗi] |
| 17 | 7 | Database | Repository | [7] traKetQuaTransaction() | trả về | alt [Ghi thành công/lỗi] |
| 18 | 7 | Repository | Service | [7] traRequirementObsolete() | trả về | alt [Ghi thành công/lỗi] |
| 19 | 8 | Service | Controller/API | [8] traKetQuaLuuTruHoacLoi() | trả về | alt [Thành công/lỗi] |
| 20 | 8 | Controller/API | Giao diện Yêu cầu | [8] traResponse() | trả về | alt [Thành công/lỗi] |
| 21 | 8 | Giao diện Yêu cầu | Người dùng | [8] hienThiKetQuaVaTaiLai() | trả về | alt [Thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 21, fragment = 3: alt tải, opt xác nhận, alt cập nhật thành công/conflict. Đường gọi repository/database không bị bỏ tầng; response lỗi quay về người dùng.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC13 - Quản lý hiệu lực yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Người dùng và Hệ thống. Trình bày gọn, giữ rõ ba lựa chọn lưu trữ đơn, khôi phục, lưu trữ hàng loạt.

ĐẶC TẢ
Mô tả: Người có quyền lưu trữ một hoặc nhiều yêu cầu, hoặc khôi phục riêng yêu cầu OBSOLETE. Không xóa dữ liệu/lịch sử.
Tiền điều kiện: Đã xác thực, yêu cầu tồn tại, quyền `requirement.archive` hoặc `requirement.restore`, có version/revision hiện hành.
Hậu điều kiện: Lưu trữ chuyển Requirement/version hiện hành sang OBSOLETE, lưu reason/audit; khôi phục dùng trạng thái trước OBSOLETE; batch trả kết quả từng item. Hủy/lỗi không báo cập nhật thành công.
Tác nhân chính: BA hoặc người có quyền dự án. Tác nhân phụ: Không có.
Luồng chính: chọn yêu cầu, tải status/version; chọn lưu trữ đơn; nhập lý do/xác nhận; kiểm tra quyền, trạng thái, expected version; transaction cập nhật Requirement/version/audit; trả kết quả.
Thay thế: khôi phục item OBSOLETE về trạng thái đã lưu; lưu trữ batch có preview tùy chọn, kết quả riêng theo item; hủy trước gửi.
Ngoại lệ: thiếu quyền/hết xác thực, không tìm thấy/project mismatch, reason sai, state/version conflict, item batch thất bại, lỗi CSDL. Lưu trữ không phải xóa cứng.

NODE
I Initial Người dùng Bắt đầu ở danh sách yêu cầu
A1 Action Người dùng [1] Chọn yêu cầu cần đổi hiệu lực
A2 Action Hệ thống [2] Tải trạng thái, version và kiểm tra quyền
D1 Decision Người dùng [3] Chọn lưu trữ đơn, khôi phục hay lưu trữ hàng loạt?
A3 Action Người dùng [3] Chọn đánh dấu không còn hiệu lực
A4 Action Người dùng [4] Nhập lý do và xác nhận lưu trữ
D2 Decision Hệ thống [6] Quyền, lý do, trạng thái và version hợp lệ?
A5 Action Hệ thống [7] Chuyển trạng thái sang OBSOLETE và trả kết quả
A6 Action Người dùng [2.1] Chọn khôi phục và nhập lý do
A7 Action Hệ thống [2.2] Khôi phục trạng thái đã lưu
A8 Action Người dùng [2.3] Chọn batch, nhập lý do và xác nhận
A9 Action Hệ thống [2.4] Xử lý item và trả kết quả từng mục
A10 Action Người dùng [5.1] Hủy hộp thoại
A11 Action Hệ thống [6.1] Báo lỗi hoặc conflict
F1 Final Hệ thống Kết thúc thao tác đã trả kết quả
F2 Final Hệ thống Kết thúc không cập nhật

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Dữ liệu tải thành công]
D1 -> A3 [Lưu trữ một yêu cầu]
D1 -> A6 [Khôi phục một yêu cầu]
D1 -> A8 [Lưu trữ hàng loạt]
A3 -> A4 [Đã chọn lưu trữ]
A4 -> D2 [Đã nhập reason và xác nhận]
A4 -> A10 [Hủy]
D2 -> A5 [Đủ quyền, reason và version hợp lệ]
D2 -> A11 [Thiếu quyền, reason sai hoặc conflict]
A5 -> F1 [Đã trả kết quả OBSOLETE]
A6 -> A7 [Đã xác nhận khôi phục]
A7 -> F1 [Khôi phục thành công]
A8 -> A9 [Đã xác nhận batch]
A9 -> F1 [Đã trả kết quả từng item]
A10 -> F2 [Không gửi cập nhật]
A11 -> F2 [Không ghi đè trạng thái]

YÊU CẦU: Mỗi lựa chọn là node/nhánh riêng; guard trên mọi cạnh từ Decision; không node treo; có Final thành công/thất bại, không hard delete. Không tự thêm điều kiện nghiệp vụ cho batch preview.
KIỂM TRA: Action = 11, Decision = 2, cạnh = 18. Báo đối chiếu cuối sơ đồ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC13 - Quản lý hiệu lực yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt, bố cục gọn. Chỉ minh họa kịch bản lưu trữ một yêu cầu để sơ đồ dễ đọc; batch và khôi phục có trong Activity.

ĐẶC TẢ
Mô tả: Lưu trữ yêu cầu hiện hành bằng chuyển status sang OBSOLETE, giữ lịch sử và ghi lý do/audit.
Tiền điều kiện: Đã xác thực; requirement/version tồn tại; có `requirement.archive`; expected current version khớp.
Hậu điều kiện: Transaction cập nhật Requirement, version và audit. Conflict/lỗi không được báo thành công. Không xóa cứng.
Tác nhân chính: Người có quyền archive. Tác nhân phụ: Không có.
Luồng chính: chọn item, tải version/status, nhập lý do/xác nhận, kiểm quyền/version, transaction cập nhật, trả kết quả.
Thay thế: hủy trước gọi API; khôi phục/batch nằm ngoài kịch bản Sequence này.
Ngoại lệ: thiếu quyền, không tìm thấy, state/version conflict, transaction/CSDL lỗi.

LIFELINE: Người dùng; Giao diện Yêu cầu; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Người dùng -> Giao diện Yêu cầu | [1] chonYeuCau(requirement_id) | đồng bộ | chính
2 | 2 | Giao diện Yêu cầu -> Controller/API | [2] layYeuCauVaVersion(id) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] docYeuCauVaKiemTraQuyen(id) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findRequirementAndVersion(id) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectRequirementAndVersion(id) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traYeuCauVaVersion() | trả về | chính
7 | 2 | Repository -> Service | [2] traDuLieu() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traChiTietHoacLoi() | trả về | chính
9 | 2 | Controller/API -> Giao diện Yêu cầu | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Yêu cầu -> Người dùng | [2] hienThiTrangThaiHoacLoi() | trả về | alt [Tải thành công/lỗi]
11 | 3-5 | Người dùng -> Giao diện Yêu cầu | [3] xacNhanLuuTru(reason) | đồng bộ | opt [Xác nhận]
12 | 6 | Giao diện Yêu cầu -> Controller/API | [6] archiveRequirement(expected_current_version_id, reason) | đồng bộ | opt [Lưu trữ]
13 | 6 | Controller/API -> Service | [6] makeRequirementObsolete(payload) | đồng bộ | opt [Lưu trữ]
14 | 6 | Service -> Service | [6] checkPermissionAndExpectedVersion() | tự gọi | opt [Lưu trữ]
15 | 7 | Service -> Repository | [7] markRequirementAndVersionObsolete(expected_version) | đồng bộ | alt [Hợp lệ/conflict]
16 | 7 | Repository -> Database | [7] transactionUpdateRequirementVersionAndAudit() | đồng bộ | alt [Ghi thành công/lỗi]
17 | 7 | Database -> Repository | [7] traKetQuaTransaction() | trả về | alt [Ghi thành công/lỗi]
18 | 7 | Repository -> Service | [7] traRequirementObsolete() | trả về | alt [Ghi thành công/lỗi]
19 | 8 | Service -> Controller/API | [8] traKetQuaLuuTruHoacLoi() | trả về | alt [Thành công/lỗi]
20 | 8 | Controller/API -> Giao diện Yêu cầu | [8] traResponse() | trả về | alt [Thành công/lỗi]
21 | 8 | Giao diện Yêu cầu -> Người dùng | [8] hienThiKetQuaVaTaiLai() | trả về | alt [Thành công/lỗi]

YÊU CẦU: Đủ 6 lifeline, 21 message; activation bar; self-call cho kiểm tra nội bộ; không gọi nhảy tầng. Vẽ alt/opt có guard, trả response cả khi lỗi. Không vẽ thao tác xóa dữ liệu.
KIỂM TRA: lifeline = 6, message = 21, fragment = 3. Báo kết quả đối chiếu cuối sơ đồ.
```

## TỰ KIỂM TRA UC13

- [x] Phần 1 nêu đúng khác biệt giữa OBSOLETE và xóa dữ liệu.
- [x] Phần 2 có thao tác đơn, khôi phục, batch, hủy và lỗi.
- [x] Activity: 11 Action, 2 Decision, 18 cạnh.
- [x] Sequence: 6 lifeline, 21 message, ba fragment.
- [x] Prompt chỉ dẫn đủ đặc tả và bảng, sequence giới hạn vào lưu trữ đơn.

## Bảng theo dõi sau UC13

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC14 - Tổ chức yêu cầu

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tiền điều kiện | MƠ HỒ | “Có yêu cầu” chưa đủ cho split/merge; backend chỉ cho biến đổi nguồn đang BASELINED. | Tách quyền `requirement.duplicate_check`, `.split`, `.merge`; yêu cầu nguồn BASELINED và version hiện tại phải khớp. |
| 3-6 | THIẾU | Kiểm tra trùng chưa nêu tập dữ liệu, ngưỡng, giới hạn hay các tín hiệu so sánh. | Ghi UI gửi threshold 0,72, limit 100; so sánh content, business rules và acceptance criteria; kết quả là ứng viên theo điểm, không phải kết luận trùng tuyệt đối. |
| 3.2 | SAI | Bảng gốc cho phép chọn một yêu cầu, nhưng không nói yêu cầu phải BASELINED hay đầu ra tối thiểu hai draft. | Chốt điều kiện BASELINED; UI yêu cầu số phần/nội dung/tiêu chí tương ứng và ít nhất hai đầu ra. |
| 3.3 | THIẾU | Gộp yêu cầu chưa nêu cần từ hai nguồn BASELINED, snapshot version, idempotency và output DRAFT. | Bổ sung kiểm tra source version; tạo một yêu cầu DRAFT mới, giữ liên kết nguồn và đánh dấu nguồn SUPERSEDED. |
| 3.2.6/3.3.6 | MƠ HỒ | “Đánh dấu đã thay thế” chưa cho biết trạng thái dữ liệu, giữ history hay xử lý rollback. | Nêu nguồn Requirement/version chuyển SUPERSEDED; transaction lỗi thì rollback source và loại output dở dang. |
| 5.1 | SAI | Nhánh chỉ chọn một yêu cầu được gắn bước 5 dù rẽ từ lựa chọn đầu vào bước 3. | Đánh thành 3.1.1; yêu cầu chọn >=2 hoặc bỏ chọn để scan toàn dự án. |
| Ngoại lệ | THIẾU | Thiếu scan limit, selection không tồn tại, snapshot lỗi, key đầu ra trùng, idempotency conflict, quyền, lỗi lưu/indexing. | Thêm ngoại lệ theo mã API; lỗi indexing sau tạo đầu ra được biểu thị kết quả degraded, không nói biến đổi thất bại toàn phần. |

Đã kiểm: **4 điểm rẽ, 6 nhánh chức năng, 9 nhóm lỗi** gồm thiếu quyền/hết xác thực, selection sai, quá giới hạn, version snapshot thiếu, source không BASELINED/stale, nội dung/criteria sai, output key trùng, idempotency/concurrency conflict, lỗi lưu/CSDL và indexing degraded. Kết quả similarity là candidate; người dùng phải tự đánh giá. Không khẳng định thuật toán phát hiện trùng hoàn hảo.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền phân tích ứng viên trùng lặp hoặc tổ chức các yêu cầu đã chốt chuẩn bằng cách tách một nguồn thành nhiều yêu cầu DRAFT, hay gộp nhiều nguồn thành một yêu cầu DRAFT.

**Tiền điều kiện:** Đã xác thực; dự án tồn tại; quyền phù hợp theo chức năng. Split/merge yêu cầu version nguồn hiện tại BASELINED và ID snapshot còn khớp. Duplicate scan giới hạn dữ liệu theo cấu hình backend.

**Hậu điều kiện:** Scan lưu kết quả gồm các cặp candidate, điểm và lý do. Split/merge tạo output DRAFT liên kết nguồn; nguồn và version cũ chuyển SUPERSEDED. Nếu xử lý biến đổi lỗi, backend rollback source/output. Indexing có thể trả SUCCESS hoặc DEGRADED; dữ liệu biến đổi không đồng nghĩa vector index luôn sẵn sàng.

**Tác nhân chính:** BA hoặc người được cấp quyền tương ứng trong dự án.

**Tác nhân phụ:** Không có hệ thống ngoài.

**Luồng sự kiện chính: Kiểm tra trùng lặp tập yêu cầu đã chọn**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở danh sách yêu cầu. | |
| 2 | | Tải danh sách trong phạm vi quyền dự án. |
| 3 | Chọn từ hai yêu cầu trở lên. | |
| 4 | Chọn Kiểm tra trùng lặp. | |
| 5 | | Kiểm tra `requirement.duplicate_check`, selection, current version snapshot và giới hạn scan; chạy so sánh theo content, business rules, acceptance criteria với threshold/limit được gửi. |
| 6 | | Lưu scan và trả các cặp đạt ngưỡng, score, match type, reasons. |
| 7 | Xem xét ứng viên trùng. | |
| 8 | | Hiển thị kết quả; kết thúc, không tự gộp yêu cầu. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Bỏ chọn toàn bộ, yêu cầu scan toàn dự án. | Scan các yêu cầu không OBSOLETE/ARCHIVED trong giới hạn cấu hình; tiếp tục bước 5. |
| 3.2 | Chọn một yêu cầu BASELINED và chọn Tách. | Hiển thị biểu mẫu tên, nội dung, tiêu chí cho mỗi phần và lý do. |
| 3.2.1 | Nhập ít nhất hai phần với số tên/nội dung/nhóm criteria bằng nhau; xác nhận. | Kiểm tra quyền `requirement.split`, source BASELINED/version còn hiện hành, dữ liệu, keys và idempotency; tạo output DRAFT có nguồn dẫn xuất; supersede nguồn trong cùng quy trình. Trả output và kết quả indexing. |
| 3.3 | Chọn ít nhất hai yêu cầu BASELINED và chọn Gộp. | Tải chi tiết từng nguồn, xác nhận trạng thái/version snapshot; hiển thị biểu mẫu hợp nhất. |
| 3.3.1 | Nhập nội dung/criteria/lý do và xác nhận gộp. | Kiểm tra quyền `requirement.merge`, các nguồn BASELINED và snapshot; tạo một output DRAFT, supersede nguồn, trả output/indexing. |
| 5.1 | Chỉ chọn một item khi scan có chọn lọc. | Yêu cầu chọn thêm item hoặc bỏ chọn để scan toàn dự án; quay lại bước 3. |
| 5.2 | Hủy biểu mẫu split/merge. | Không tạo output hay supersede nguồn; kết thúc nhánh. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Hết xác thực/thiếu quyền: từ chối tải hoặc thao tác. |
| 5.1 | | Selection không tồn tại, version snapshot không đầy đủ hoặc vượt giới hạn item/criteria: từ chối scan và báo lỗi. |
| 5.2 | | Source version không còn current/BASELINED: từ chối biến đổi; yêu cầu tải lại. |
| 3.2.1 | | Có ít hơn hai phần, tên/nội dung/criteria không tương ứng hoặc document/key không hợp lệ: giữ biểu mẫu để sửa. |
| 3.3.1 | | Output sai schema hoặc key đầu ra trùng: từ chối biến đổi. |
| 3.2.1/3.3.1 | | Idempotency key dùng lại với payload khác, thao tác đang chạy hoặc source conflict: trả conflict; không nhân đôi kết quả. |
| 3.2.1/3.3.1 | | Lỗi transaction: rollback các source đã supersede và loại output chưa hoàn tất. |
| 3.2.1/3.3.1 | | Indexing không hoàn tất sau biến đổi: trả trạng thái DEGRADED; không khẳng định thất bại tạo output. |

**Giả định / Câu hỏi cần làm rõ:** Ngưỡng 0,72 và limit 100 là giá trị UI hiện tại, không nhất thiết là chính sách cố định. Mã nguồn dùng score/candidate và mô hình tín hiệu; kết quả cần reviewer xác nhận. Bảng gốc gọi nguồn “đã được chấp nhận”; đặc tả dùng trạng thái BASELINED theo thực thi.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu ở danh sách yêu cầu |
| A1 | 1 | Action | Người dùng | [1] Mở danh sách yêu cầu |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền dự án |
| D1 | 3 | Decision | Người dùng | [3] Chọn scan, tách hay gộp? |
| A3 | 3-4 | Action | Người dùng | [3] Chọn yêu cầu và chạy scan trùng lặp |
| A4 | 5-6 | Action | Hệ thống | [5] So sánh và lưu kết quả candidate |
| A5 | 7-8 | Action | Người dùng | [7] Xem kết quả trùng lặp |
| A6 | 3.1.1 | Action | Người dùng | [3.1.1] Chạy scan toàn dự án |
| A7 | 3.2 | Action | Người dùng | [3.2] Nhập các phần để tách |
| A8 | 3.2.1 | Action | Hệ thống | [3.2.1] Tạo các draft và supersede nguồn |
| A9 | 3.3 | Action | Người dùng | [3.3] Chọn nguồn và nhập nội dung gộp |
| A10 | 3.3.1 | Action | Hệ thống | [3.3.1] Tạo draft hợp nhất và supersede nguồn |
| D2 | 5/3.2.1/3.3.1 | Decision | Hệ thống | [5] Quyền, snapshot và dữ liệu hợp lệ? |
| A11 | 5.1 | Action | Hệ thống | [5.1] Báo selection/validation/conflict |
| F1 | 7/3.2.1/3.3.1 | Final | Hệ thống | Kết thúc với kết quả đã trả |
| F2 | 5.1 | Final | Hệ thống | Kết thúc thất bại hoặc chờ sửa |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách tải xong |
| D1 | A3 | [Scan selection] |
| D1 | A6 | [Scan toàn dự án] |
| D1 | A7 | [Tách BASELINED] |
| D1 | A9 | [Gộp từ hai nguồn BASELINED trở lên] |
| A3 | D2 | Đã chọn >=2 và gửi scan |
| A6 | D2 | Đã gửi scan toàn dự án |
| D2 | A4 | [Scan hợp lệ] |
| A4 | A5 | Kết quả scan đã lưu |
| A5 | F1 | Đã hiển thị kết quả |
| D2 | A11 | [Scan sai selection/limit/snapshot] |
| A11 | F2 | Đã báo lỗi scan |
| A7 | D2 | Đã gửi split payload |
| D2 | A8 | [Split hợp lệ, source snapshot BASELINED] |
| A8 | F1 | Draft tách đã trả |
| A9 | D2 | Đã gửi merge payload |
| D2 | A10 | [Merge hợp lệ, mọi source snapshot BASELINED] |
| A10 | F1 | Draft hợp nhất đã trả |
| D2 | A11 | [Validation, quyền, idempotency hoặc conflict lỗi] |
| A11 | F2 | Đã báo lỗi và không xác nhận thành công |

### 3c. Số liệu

N = 8 ô bước có nội dung; M = 11 Action; D = 2 Decision; E = 22 cạnh. Ba chức năng tách biệt; scan chỉ báo candidate, không tự thực hiện merge.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa scan trùng lặp với selection hợp lệ. Người dùng vẫn là người đánh giá candidate; không tự động hợp nhất.

### 4a. Lifeline trái sang phải

Người dùng → Giao diện Yêu cầu → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện Yêu cầu | [1] moDanhSachYeuCau(project_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Yêu cầu | Controller/API | [2] layDanhSachYeuCau(project_id, filters) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] docDanhSachTheoQuyen(project_id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] listRequirements(project_id, filters) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectRequirements(project_id, filters) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDanhSach() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traItems() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traResult() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Yêu cầu | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Yêu cầu | Người dùng | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-4 | Người dùng | Giao diện Yêu cầu | [3] chonItemsVaScan(ids, threshold=0.72, limit=100) | đồng bộ | opt [Có selection] |
| 12 | 5 | Giao diện Yêu cầu | Controller/API | [5] findDuplicateRequirements(ids, threshold, limit) | đồng bộ | opt [Scan hợp lệ] |
| 13 | 5 | Controller/API | Service | [5] findRequirementDuplicates(project_id, payload) | đồng bộ | opt [Scan hợp lệ] |
| 14 | 5 | Service | Service | [5] validatePermissionSelectionAndLimit() | tự gọi | opt [Scan] |
| 15 | 5 | Service | Repository | [5] loadRequirementsCurrentVersionsAndCriteria(ids) | đồng bộ | alt [Snapshot hợp lệ/lỗi] |
| 16 | 5 | Repository | Database | [5] selectRequirementsVersionsCriteria(ids) | đồng bộ | alt [Snapshot hợp lệ/lỗi] |
| 17 | 5 | Database | Repository | [5] traSnapshot() | trả về | alt [Snapshot hợp lệ/lỗi] |
| 18 | 5 | Repository | Service | [5] traSnapshotHoacLoi() | trả về | alt [Snapshot hợp lệ/lỗi] |
| 19 | 5 | Service | Service | [5] scoreRequirementPairs(threshold) | tự gọi | opt [Snapshot hợp lệ] |
| 20 | 6 | Service | Repository | [6] insertDuplicateScan(candidates) | đồng bộ | alt [Lưu thành công/lỗi] |
| 21 | 6 | Repository | Database | [6] insertScanAndAudit(scan) | đồng bộ | alt [Lưu thành công/lỗi] |
| 22 | 6 | Database | Repository | [6] traScanDaLuu() | trả về | alt [Lưu thành công/lỗi] |
| 23 | 6 | Repository | Service | [6] traCandidateScan() | trả về | alt [Lưu thành công/lỗi] |
| 24 | 6 | Service | Controller/API | [6] traCandidatesHoacLoi() | trả về | alt [Kết quả/lỗi] |
| 25 | 6 | Controller/API | Giao diện Yêu cầu | [6] traResponse() | trả về | alt [Kết quả/lỗi] |
| 26 | 7-8 | Giao diện Yêu cầu | Người dùng | [7] hienThiUngVienVaDiem() | trả về | alt [Kết quả/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 26, fragment = 4: alt tải, opt scan selection, alt snapshot, alt ghi kết quả. Thông điệp score là xử lý nội bộ; trả về có thể là danh sách rỗng. Không có tự động gộp.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC14 - Tổ chức yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Người dùng và Hệ thống. Giữ ba lựa chọn scan, split, merge thành các nhánh riêng, bố cục thoáng.

ĐẶC TẢ
Mô tả: Scan ứng viên trùng; tách một requirement BASELINED thành ít nhất hai draft; gộp từ hai requirement BASELINED thành một draft. Candidate không đồng nghĩa kết luận trùng.
Tiền điều kiện: Đã xác thực, có quyền `requirement.duplicate_check`, `.split` hoặc `.merge`. Split/merge cần source version đang BASELINED và current snapshot khớp.
Hậu điều kiện: Scan trả candidate/score/reasons. Split/merge tạo output DRAFT liên kết nguồn và chuyển nguồn thành SUPERSEDED; lỗi biến đổi rollback. Indexing có thể SUCCESS hoặc DEGRADED.
Tác nhân chính: BA hoặc người có quyền theo chức năng. Tác nhân phụ: Không có.
Luồng chính: mở danh sách, chọn chức năng. Scan: đối chiếu theo threshold 0,72, limit UI 100 và hiển thị cặp candidate. Split: nhập ít nhất hai phần phù hợp, tạo draft. Merge: chọn >=2 source baseline, nhập nội dung, tạo draft và supersede sources.
Thay thế: không chọn item để scan toàn dự án; chọn một item thì yêu cầu chọn thêm hoặc bỏ chọn. Hủy form thì không biến đổi.
Ngoại lệ: permission, selection missing, limit/snapshot error, source stale/not BASELINED, payload mismatch, duplicate output key, idempotency/concurrency conflict, transaction rollback, indexing DEGRADED.

NODE
I Initial Người dùng Bắt đầu ở danh sách yêu cầu
A1 Action Người dùng [1] Mở danh sách yêu cầu
A2 Action Hệ thống [2] Tải danh sách theo quyền dự án
D1 Decision Người dùng [3] Chọn scan, tách hay gộp?
A3 Action Người dùng [3] Chọn yêu cầu và chạy scan trùng lặp
A4 Action Hệ thống [5] So sánh và lưu kết quả candidate
A5 Action Người dùng [7] Xem kết quả trùng lặp
A6 Action Người dùng [3.1.1] Chạy scan toàn dự án
A7 Action Người dùng [3.2] Nhập các phần để tách
A8 Action Hệ thống [3.2.1] Tạo các draft và supersede nguồn
A9 Action Người dùng [3.3] Chọn nguồn và nhập nội dung gộp
A10 Action Hệ thống [3.3.1] Tạo draft hợp nhất và supersede nguồn
D2 Decision Hệ thống [5] Quyền, snapshot và dữ liệu hợp lệ?
A11 Action Hệ thống [5.1] Báo selection, validation hoặc conflict
F1 Final Hệ thống Kết thúc với kết quả đã trả
F2 Final Hệ thống Kết thúc thất bại hoặc chờ sửa

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Danh sách tải xong]
D1 -> A3 [Scan selection]
D1 -> A6 [Scan toàn dự án]
D1 -> A7 [Tách BASELINED]
D1 -> A9 [Gộp ít nhất hai nguồn BASELINED]
A3 -> D2 [Đã chọn ít nhất hai và gửi scan]
A6 -> D2 [Đã gửi scan toàn dự án]
D2 -> A4 [Scan hợp lệ]
A4 -> A5 [Scan đã lưu]
A5 -> F1 [Đã hiển thị candidate]
D2 -> A11 [Selection, limit hoặc snapshot lỗi]
A7 -> D2 [Đã gửi split payload]
D2 -> A8 [Split hợp lệ, source snapshot BASELINED]
A8 -> F1 [Draft tách đã trả]
A9 -> D2 [Đã gửi merge payload]
D2 -> A10 [Merge hợp lệ, source BASELINED]
A10 -> F1 [Draft gộp đã trả]
D2 -> A11 [Validation, permission, idempotency hoặc conflict lỗi]
A11 -> F2 [Đã báo lỗi]

YÊU CẦU: Mọi nhánh từ Decision có guard; candidate scan không tự động gộp; không xóa lịch sử source; có final thành công/thất bại; không thêm nghiệp vụ.
KIỂM TRA: Action = 11, Decision = 2, cạnh = 22. Báo kiểm đếm cuối sơ đồ.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC14 - Tổ chức yêu cầu của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Sequence chỉ minh họa scan trùng lặp với selection hợp lệ. Không biến sơ đồ thành kết luận tự gộp.

ĐẶC TẢ
Mô tả: Tính các candidate trùng cho tập yêu cầu được chọn.
Tiền điều kiện: Đã xác thực, có `requirement.duplicate_check`, selection/current version snapshot hợp lệ và trong giới hạn.
Hậu điều kiện: Lưu scan, trả score/match type/reasons; không tự hợp nhất. Thất bại trả lỗi phù hợp.
Tác nhân chính: Người dùng có quyền scan. Tác nhân phụ: Không có.
Luồng chính: mở danh sách, chọn >=2 yêu cầu, gửi scan, backend tải current versions/criteria, đánh điểm, lưu scan và hiển thị candidate.
Thay thế: scan toàn dự án khi không có selection; hành vi nằm ngoài kịch bản Sequence cụ thể này.
Ngoại lệ: thiếu quyền, selection missing, limit exceeded, incomplete snapshot, lỗi DB.

LIFELINE: Người dùng; Giao diện Yêu cầu; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Người dùng -> Giao diện Yêu cầu | [1] moDanhSachYeuCau(project_id) | đồng bộ | chính
2 | 2 | Giao diện Yêu cầu -> Controller/API | [2] layDanhSachYeuCau(project_id, filters) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] docDanhSachTheoQuyen(project_id) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] listRequirements(project_id, filters) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectRequirements(project_id, filters) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traDanhSach() | trả về | chính
7 | 2 | Repository -> Service | [2] traItems() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traResult() | trả về | chính
9 | 2 | Controller/API -> Giao diện Yêu cầu | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Yêu cầu -> Người dùng | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi]
11 | 3-4 | Người dùng -> Giao diện Yêu cầu | [3] chonItemsVaScan(ids, threshold=0.72, limit=100) | đồng bộ | opt [Có selection]
12 | 5 | Giao diện Yêu cầu -> Controller/API | [5] findDuplicateRequirements(ids, threshold, limit) | đồng bộ | opt [Scan hợp lệ]
13 | 5 | Controller/API -> Service | [5] findRequirementDuplicates(project_id, payload) | đồng bộ | opt [Scan hợp lệ]
14 | 5 | Service -> Service | [5] validatePermissionSelectionAndLimit() | tự gọi | opt [Scan]
15 | 5 | Service -> Repository | [5] loadRequirementsVersionsAndCriteria(ids) | đồng bộ | alt [Snapshot hợp lệ/lỗi]
16 | 5 | Repository -> Database | [5] selectRequirementsVersionsCriteria(ids) | đồng bộ | alt [Snapshot hợp lệ/lỗi]
17 | 5 | Database -> Repository | [5] traSnapshot() | trả về | alt [Snapshot hợp lệ/lỗi]
18 | 5 | Repository -> Service | [5] traSnapshotHoacLoi() | trả về | alt [Snapshot hợp lệ/lỗi]
19 | 5 | Service -> Service | [5] scoreRequirementPairs(threshold) | tự gọi | opt [Snapshot hợp lệ]
20 | 6 | Service -> Repository | [6] insertDuplicateScan(candidates) | đồng bộ | alt [Lưu thành công/lỗi]
21 | 6 | Repository -> Database | [6] insertScanAndAudit(scan) | đồng bộ | alt [Lưu thành công/lỗi]
22 | 6 | Database -> Repository | [6] traScanDaLuu() | trả về | alt [Lưu thành công/lỗi]
23 | 6 | Repository -> Service | [6] traCandidateScan() | trả về | alt [Lưu thành công/lỗi]
24 | 6 | Service -> Controller/API | [6] traCandidatesHoacLoi() | trả về | alt [Kết quả/lỗi]
25 | 6 | Controller/API -> Giao diện Yêu cầu | [6] traResponse() | trả về | alt [Kết quả/lỗi]
26 | 7-8 | Giao diện Yêu cầu -> Người dùng | [7] hienThiUngVienVaDiem() | trả về | alt [Kết quả/lỗi]

YÊU CẦU: Đủ 6 lifeline, 26 message theo thứ tự, activation bar, self-call cho validation/scoring; không gọi nhảy tầng. Return cho request đồng bộ. Các lỗi nằm trong alt có guard. Không tạo message tự động merge.
KIỂM TRA: lifeline = 6, message = 26, fragment = 4. Báo đối chiếu ở cuối.
```

## TỰ KIỂM TRA UC14

- [x] Phần 1 phân biệt candidate score với xác nhận trùng và nêu điều kiện BASELINED.
- [x] Phần 2 tách scan, split, merge; có lỗi permission, snapshot, rollback và indexing degraded.
- [x] Activity: 11 Action, 2 Decision, 22 cạnh.
- [x] Sequence: 6 lifeline, 26 message, bốn nhóm fragment.
- [x] Hai prompt tự đủ và không biến scan thành hành động gộp.

## Bảng theo dõi sau UC14

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Chưa | Chưa | Chưa | Chưa |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC15 - Quản lý tài liệu nguồn

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tác nhân/tiền điều kiện | MƠ HỒ | “BA được cấp quyền quản lý tài liệu” gộp upload, đọc, quản trị metadata, tải xuống, archive/restore thành một quyền. | Tách quyền theo API và quyền đọc tài liệu theo visibility/owner/recipient. |
| 3-10 | THIẾU | Upload chưa nêu validate format, kích thước, nội dung rỗng, quyền chia sẻ, OCR, idempotency và khả năng trùng. | Bổ sung các kiểm tra API và trạng thái xử lý; không khẳng định tài liệu luôn được chấp nhận. |
| 6 | MƠ HỒ | “Quyền sử dụng bằng AI” bị nhập chung với visibility. Code có `ai_enabled`, `visibility`, `shared_with` và OCR language độc lập. | Tách các trường: phạm vi truy cập, danh sách người nhận, cờ AI-read, loại nguồn; chỉ mô tả trường được chọn. |
| 8-10 | SAI | Mô tả gộp lưu file và trích xuất thành một bước đồng bộ. Backend lưu raw source rồi ingestion/parse/index có trạng thái riêng. | Tách tiếp nhận tệp, ghi metadata/raw source và xử lý nền/trạng thái; kết quả có thể pending/degraded. |
| 3.1 | MƠ HỒ | “Hiển thị nội dung tài liệu” có thể bị hiểu là mọi định dạng được preview trực tiếp. | Nêu xem/đọc nội dung theo khả năng định dạng và quyền; tìm kiếm dựa trên nội dung đã lập chỉ mục nếu khả dụng. |
| 3.2-3.3 | THIẾU | Metadata, access control, AI-read consent là các thao tác riêng; chia sẻ chỉ owner mới chỉnh. | Tách sửa metadata khỏi visibility/shared recipients và ai_enabled; yêu cầu revision/owner, ghi lỗi conflict. |
| 3.4 | THIẾU | Download thiếu quyền chuyên biệt và access check. | Ghi quyền `requirement_document.download` cùng kiểm tra can_read. |
| 3.5-3.6 | THIẾU | Archive/restore thiếu expected revision, dọn quyền AI/index, trạng thái trước lưu trữ và lỗi phục hồi. | Ghi luồng cleanup và indexing/recovery theo trạng thái; không coi archive là xóa lịch sử ngay. |
| Ngoại lệ | THIẾU | Thiếu file rỗng/quá lớn/format không hỗ trợ, duplicate decision, recipient không thuộc dự án, hết phiên, permission, revision conflict, storage/parser/indexing lỗi. | Thêm các lỗi API có căn cứ; phân biệt thất bại upload, parse chưa xong và indexing degraded. |

Đã kiểm: **6 điểm rẽ, 8 nhóm luồng thao tác, 11 nhóm lỗi** gồm format/file rỗng/quá cỡ, duplicate confirmation, recipient/visibility sai, quyền/xác thực, revision conflict, tài liệu không tìm thấy/không được xem, storage/object store, parse/OCR, indexing/AI-read, download, archive/restore cleanup và lỗi CSDL. UC quản lý tài liệu có xem/tìm kiếm, chi tiết, thêm, sửa, archive/restore; xóa cứng không được đặc tả.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền tải, đọc/tìm, cập nhật metadata, quản lý visibility/AI-read, tải xuống, lưu trữ và khôi phục tài liệu nguồn trong dự án.

**Tiền điều kiện:** Người dùng đã xác thực và thuộc phạm vi dự án. Mỗi thao tác yêu cầu quyền cụ thể. Tài liệu phải qua kiểm tra access policy; chỉnh sửa metadata/access/archive/restore dùng revision hiện hành. Người nhận chia sẻ phải là thành viên ACTIVE của dự án.

**Hậu điều kiện:**
- Upload hợp lệ: raw source/metadata được lưu; xử lý parse/index được theo dõi bằng trạng thái, có thể SUCCESS hoặc DEGRADED/PENDING.
- Cập nhật metadata/access: revision mới, audit tương ứng; đổi visibility/shared/AI-read có thể yêu cầu cập nhật index/revocation.
- Archive/restore: trạng thái và thông tin lý do/người/thời điểm được cập nhật; raw source không mặc nhiên bị xóa vĩnh viễn. Khôi phục AI-enabled có thể chờ ingestion/index/access recovery.
- Thất bại: lỗi quyền/validation/conflict không được báo thành công. Upload trùng có thể trả bản tái sử dụng theo deduplication, không nhất thiết tạo bản mới.

**Tác nhân chính:** BA hoặc người có quyền phù hợp trong dự án.

**Tác nhân phụ:** Dịch vụ lưu trữ tệp và pipeline trích xuất/OCR/index nội bộ. Chưa có bằng chứng cần mô hình AI bên ngoài cho mọi upload.

**Luồng sự kiện chính: Tải một tài liệu lên**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở mục Tài liệu nguồn của dự án. | |
| 2 | | Kiểm tra quyền đọc và hiển thị danh sách theo trạng thái/từ khóa. |
| 3 | Chọn Thêm tài liệu. | |
| 4 | | Hiển thị form tệp, format, visibility, người được chia sẻ, AI-read, loại nguồn và OCR language nếu áp dụng. |
| 5 | Chọn tệp và nhập các tùy chọn cần thiết. | |
| 6 | Xác nhận tải lên. | |
| 7 | | Kiểm tra `requirement_document.upload`, format, kích thước, file không rỗng, recipient và cấu hình access. |
| 8 | | Kiểm tra nội dung trùng; yêu cầu quyết định xác nhận nếu có duplicate candidate. |
| 9 | | Lưu raw source và metadata, khởi tạo ingestion; áp dụng deduplication/idempotent reuse nếu phù hợp. |
| 10 | | Trả tài liệu cùng status parse/index; hiển thị trạng thái. Kết thúc upload, các thao tác xử lý tiếp tục theo trạng thái nền. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | Nhập từ khóa/chọn trạng thái hoặc mở một tài liệu. | Lọc danh sách; với chi tiết, kiểm tra access policy rồi hiển thị metadata/nội dung đọc được. |
| 2.2 | Nhập cụm từ cần tìm trong nội dung. | Tìm trong dữ liệu sẵn có; hiển thị đoạn phù hợp hoặc trạng thái chưa có chỉ mục. |
| 3.1 | Chọn cập nhật metadata. | Tải các trường được phép sửa và revision. |
| 3.1.1 | Sửa metadata và xác nhận. | Kiểm tra `knowledge.manage`, schema và revision; cập nhật/audit, reindex nếu AI-enabled. |
| 3.2 | Chọn thay đổi visibility, người chia sẻ hoặc AI-read. | Kiểm tra quyền owner, người nhận ACTIVE, trạng thái không ARCHIVED; cập nhật hoặc thu hồi index theo cấu hình. |
| 3.3 | Chọn Tải xuống. | Kiểm tra `requirement_document.download` và can_read; trả tệp gốc. |
| 3.4 | Chọn Lưu trữ và xác nhận lý do. | Kiểm tra quyền/revision; bắt đầu cleanup quyền/index, đánh dấu ARCHIVED và ghi audit. |
| 3.5 | Chọn Khôi phục trên tài liệu ARCHIVED, xác nhận lý do. | Khôi phục status_before_archive; nếu AI-enabled, reindex và phục hồi access trước khi báo sẵn sàng. |
| 3.6 | Hủy form trước khi gửi. | Đóng form, không gửi thay đổi. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.1 | | File rỗng, vượt kích thước tối đa hoặc format không hỗ trợ: trả validation/413, không tạo tài liệu. |
| 7.2 | | Visibility/shared_with không hợp lệ, thiếu recipient khi visibility=shared, hoặc recipient không ACTIVE trong dự án: từ chối upload. |
| 8.1 | | Có bản trùng nhưng chưa xác nhận theo danh sách duplicate candidate: yêu cầu xác nhận thay vì tự tạo bản trùng. |
| 9.1 | | Lỗi ghi storage/metadata: không trả upload thành công; dọn nguồn raw chưa được claim nếu có. |
| 10.1 | | Parse/OCR lỗi hoặc chưa hoàn thành: hiển thị trạng thái phù hợp; có thể retry theo quyền/API, không khẳng định nội dung đã sẵn sàng. |
| 2.1.1 | | Không có quyền đọc, tài liệu không tồn tại hoặc visibility không cho phép: từ chối chi tiết/download. |
| 3.1.1/3.2 | | Revision conflict, access update đang chạy, revocation pending hoặc tài liệu đã ARCHIVED: từ chối sửa và yêu cầu tải lại. |
| 3.3.1 | | Thiếu download permission/access: không trả tệp. |
| 3.4.1 | | Archive cleanup chưa hoàn tất hoặc lỗi: báo trạng thái xử lý, không giả định thu hồi đã xong. |
| 3.5.1 | | Restore revision sai, reindex/access recovery lỗi: trả conflict/503 và trạng thái phục hồi đang chờ. |
| Mọi bước | | Hết xác thực hoặc lỗi CSDL/API: trả lỗi, không thông báo thao tác thành công. |

**Giả định / Câu hỏi cần làm rõ:** Giao diện liệt kê một số format/chia sẻ cụ thể; phần này giữ tên cấu hình tổng quát để tránh đóng đinh danh sách có thể thay đổi. AI-read là quyền cho pipeline xử lý/đọc, không đồng nghĩa người dùng bất kỳ được xem tài liệu. Hành vi duplicate reuse phụ thuộc hash, format và access settings.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu ở mục Tài liệu nguồn |
| A1 | 1 | Action | Người dùng | [1] Mở mục Tài liệu nguồn |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền |
| D1 | 3 | Decision | Người dùng | [3] Chọn upload, xem, sửa, chia sẻ, tải, archive hay restore? |
| A3 | 3-6 | Action | Người dùng | [3] Chọn tệp và gửi upload |
| D2 | 7-8 | Decision | Hệ thống | [7] Tệp, quyền và duplicate decision hợp lệ? |
| A4 | 9-10 | Action | Hệ thống | [9] Lưu tài liệu và trả trạng thái xử lý |
| A5 | 2.1-2.2 | Action | Người dùng | [2.1] Tìm, mở hoặc tìm trong tài liệu |
| A6 | 2.1-2.2 | Action | Hệ thống | [2.1] Kiểm tra quyền và trả nội dung/kết quả |
| A7 | 3.1-3.1.1 | Action | Người dùng | [3.1] Sửa metadata |
| A8 | 3.1.1 | Action | Hệ thống | [3.1.1] Lưu metadata và reindex nếu cần |
| A9 | 3.2 | Action | Người dùng | [3.2] Thay đổi visibility hoặc AI-read |
| A10 | 3.2 | Action | Hệ thống | [3.2] Kiểm owner/recipient và cập nhật access |
| A11 | 3.3 | Action | Người dùng | [3.3] Yêu cầu tải tài liệu |
| A12 | 3.3 | Action | Hệ thống | [3.3] Kiểm quyền và trả file gốc |
| A13 | 3.4/3.5 | Action | Người dùng | [3.4] Xác nhận archive hoặc restore |
| A14 | 3.4/3.5 | Action | Hệ thống | [3.4] Cập nhật trạng thái và cleanup/recovery |
| A15 | 3.6 | Action | Người dùng | [3.6] Hủy form |
| A16 | 7.1/9.1 | Action | Hệ thống | [7.1] Báo validation, duplicate hoặc storage error |
| F1 | 10/2.2/3.1.1/3.2-3.5 | Final | Hệ thống | Kết thúc với kết quả thao tác |
| F2 | 3.6/7.1 | Final | Hệ thống | Kết thúc không ghi thay đổi |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách tải xong |
| D1 | A3 | [Thêm tài liệu] |
| A3 | D2 | Đã gửi form upload |
| D2 | A4 | [Tệp/quyền hợp lệ, duplicate được xác nhận hoặc không có] |
| D2 | A16 | [Validation/permission/duplicate chưa xác nhận] |
| A4 | F1 | Đã trả trạng thái parse/index |
| D1 | A5 | [Xem/tìm] |
| A5 | A6 | Đã gửi yêu cầu đọc/tìm |
| A6 | F1 | Đã trả nội dung/kết quả |
| D1 | A7 | [Sửa metadata] |
| A7 | A8 | Đã xác nhận metadata |
| A8 | F1 | Đã lưu/reindex status trả về |
| D1 | A9 | [Chia sẻ/AI-read] |
| A9 | A10 | Đã xác nhận access settings |
| A10 | F1 | Đã cập nhật hoặc trả indexing status |
| D1 | A11 | [Tải xuống] |
| A11 | A12 | Đã yêu cầu tải |
| A12 | F1 | File đã trả hoặc lỗi được báo |
| D1 | A13 | [Archive/restore] |
| A13 | A14 | Đã xác nhận |
| A14 | F1 | Trả trạng thái archive/restore |
| D1 | A15 | [Hủy form] |
| A15 | F2 | Không gửi thay đổi |
| A16 | F2 | Không báo upload thành công |

### 3c. Số liệu

N = 11 ô bước có nội dung trong các luồng chính và thay thế; M = 16 Action; D = 2 Decision; E = 25 cạnh. Các thao tác quản trị được tách riêng; status indexing/processing không bị nhập làm một trạng thái hoàn tất.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa upload một tệp hợp lệ. Đọc, sửa metadata/access, download, archive/restore vẫn có trong Activity và đặc tả.

### 4a. Lifeline trái sang phải

Người dùng → Giao diện Tài liệu → Controller/API → Service → Repository → Database → Storage/Worker. Storage/Worker là hệ thống ngoài/nội bộ tích hợp được gọi trong upload; cần xác nhận việc vẽ Worker như lifeline riêng nếu mô hình triển khai xem queue là thành phần nội bộ.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Người dùng | Giao diện Tài liệu | [1] moTaiLieuNguon(project_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Tài liệu | Controller/API | [2] listRequirementDocuments(project_id, q, status) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listDocumentsAndCheckPermission(project_id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findDocuments(project_id, filters) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectRequirementDocuments(filters) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDanhSach() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traItems() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traDanhSachHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Tài liệu | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Tài liệu | Người dùng | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi] |
| 11 | 5-6 | Người dùng | Giao diện Tài liệu | [5] chonFileVaXacNhanUpload(file, options) | đồng bộ | opt [Upload] |
| 12 | 7 | Giao diện Tài liệu | Controller/API | [7] uploadRequirementDocument(file, format, visibility, ai_enabled) | đồng bộ | opt [Upload hợp lệ] |
| 13 | 7 | Controller/API | Service | [7] uploadRequirementDocumentRecord(payload) | đồng bộ | opt [Upload hợp lệ] |
| 14 | 7-8 | Service | Service | [7] validateFormatSizeRecipientsAndDuplicate() | tự gọi | alt [Hợp lệ/validation error] |
| 15 | 9 | Service | Storage/Worker | [9] storeRawSourceAndQueueIngestion(file) | đồng bộ | alt [Lưu thành công/lỗi] |
| 16 | 9 | Storage/Worker | Service | [9] traSourceKeyVaIngestionStatus() | trả về | alt [Lưu thành công/lỗi] |
| 17 | 9 | Service | Repository | [9] insertDocumentMetadata(status, source_key) | đồng bộ | alt [Metadata thành công/lỗi] |
| 18 | 9 | Repository | Database | [9] insertRequirementDocument(document) | đồng bộ | alt [Metadata thành công/lỗi] |
| 19 | 9 | Database | Repository | [9] traDocumentRevision() | trả về | alt [Metadata thành công/lỗi] |
| 20 | 9 | Repository | Service | [9] traDocument() | trả về | alt [Metadata thành công/lỗi] |
| 21 | 10 | Service | Controller/API | [10] traDocumentAndProcessingStatus() | trả về | alt [Được tạo/lỗi] |
| 22 | 10 | Controller/API | Giao diện Tài liệu | [10] traResponse(status, revision) | trả về | alt [Được tạo/lỗi] |
| 23 | 10 | Giao diện Tài liệu | Người dùng | [10] hienThiTaiLieuVaTrangThai() | trả về | alt [Được tạo/lỗi] |

### 4c. Số liệu

Lifeline = 7, message = 23, fragment = 3: alt tải, opt upload, alt validation/storage/metadata. Tác vụ ingestion/index có thể tiếp tục nền; sơ đồ không khẳng định đã trích xuất xong ngay trong request.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC15 - Quản lý tài liệu nguồn của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Người dùng và Hệ thống. Bố cục luận văn, chia nhánh theo thao tác, không gộp CRUD/access/download/archive.

ĐẶC TẢ
Mô tả: Tải, xem/tìm, sửa metadata, chia sẻ/AI-read, tải xuống, lưu trữ và khôi phục tài liệu nguồn.
Tiền điều kiện: Đã xác thực, thuộc dự án, có quyền riêng cho thao tác; quyền đọc còn phụ thuộc owner/visibility/recipient. Recipient shared phải ACTIVE.
Hậu điều kiện: Upload lưu raw source/metadata rồi trả trạng thái parse/index; cập nhật có revision/audit; archive/restore giữ dữ liệu và có cleanup/recovery. Lỗi không báo thành công.
Tác nhân chính: BA/người có quyền. Tác nhân phụ: storage và pipeline xử lý.
Luồng chính: mở danh sách; hệ thống tải theo quyền; người dùng chọn upload, xem/tìm, metadata, access, download hoặc archive/restore. Upload validate format/kích thước/duplicate/access, lưu raw source/metadata, trả trạng thái xử lý.
Thay thế: đọc/tìm nội dung; cập nhật metadata và reindex; đổi access; tải file gốc; archive/restore theo revision; hủy form trước gửi.
Ngoại lệ: file rỗng/quá lớn/format sai, duplicate decision, recipient không thuộc dự án, thiếu quyền/hết xác thực, revision conflict, tài liệu không tồn tại/không được xem, storage/parser/index/download/cleanup/recovery error.

NODE
I Initial Người dùng Bắt đầu ở mục Tài liệu nguồn
A1 Action Người dùng [1] Mở mục Tài liệu nguồn
A2 Action Hệ thống [2] Tải danh sách theo quyền
D1 Decision Người dùng [3] Chọn upload, xem, sửa, chia sẻ, tải, archive hay restore?
A3 Action Người dùng [3] Chọn tệp và gửi upload
D2 Decision Hệ thống [7] Tệp, quyền và duplicate decision hợp lệ?
A4 Action Hệ thống [9] Lưu tài liệu và trả trạng thái xử lý
A5 Action Người dùng [2.1] Tìm, mở hoặc tìm trong tài liệu
A6 Action Hệ thống [2.1] Kiểm tra quyền và trả nội dung/kết quả
A7 Action Người dùng [3.1] Sửa metadata
A8 Action Hệ thống [3.1] Lưu metadata và reindex nếu cần
A9 Action Người dùng [3.2] Thay đổi visibility hoặc AI-read
A10 Action Hệ thống [3.2] Kiểm owner/recipient và cập nhật access
A11 Action Người dùng [3.3] Yêu cầu tải tài liệu
A12 Action Hệ thống [3.3] Kiểm quyền và trả file gốc
A13 Action Người dùng [3.4] Xác nhận archive hoặc restore
A14 Action Hệ thống [3.4] Cập nhật trạng thái và cleanup/recovery
A15 Action Người dùng [3.6] Hủy form
A16 Action Hệ thống [7.1] Báo validation, duplicate hoặc storage error
F1 Final Hệ thống Kết thúc với kết quả thao tác
F2 Final Hệ thống Kết thúc không ghi thay đổi

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Danh sách tải xong]
D1 -> A3 [Thêm tài liệu]
A3 -> D2 [Đã gửi upload]
D2 -> A4 [Tệp/quyền hợp lệ, duplicate đã xử lý]
D2 -> A16 [Validation/permission/duplicate chưa xác nhận]
A4 -> F1 [Đã trả parse/index status]
D1 -> A5 [Xem/tìm]
A5 -> A6 [Đã gửi yêu cầu đọc/tìm]
A6 -> F1 [Đã trả nội dung/kết quả]
D1 -> A7 [Sửa metadata]
A7 -> A8 [Đã xác nhận metadata]
A8 -> F1 [Đã trả kết quả]
D1 -> A9 [Chia sẻ/AI-read]
A9 -> A10 [Đã xác nhận access settings]
A10 -> F1 [Đã trả kết quả]
D1 -> A11 [Tải xuống]
A11 -> A12 [Đã yêu cầu tải]
A12 -> F1 [Đã trả file hoặc lỗi]
D1 -> A13 [Archive/restore]
A13 -> A14 [Đã xác nhận]
A14 -> F1 [Đã trả trạng thái]
D1 -> A15 [Hủy]
A15 -> F2 [Không gửi thay đổi]
A16 -> F2 [Không báo upload thành công]

YÊU CẦU: Mọi nhánh từ D1/D2 có guard. Không gọi tác vụ parse/index là tức thời nếu status cho biết đang xử lý. Tách đọc, sửa, access, download và archive. Final thành công/thất bại riêng, không node treo.
KIỂM TRA: Action = 16, Decision = 2, cạnh = 25. Báo kiểm đếm cuối.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC15 - Quản lý tài liệu nguồn của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Chỉ minh họa upload một tệp hợp lệ; không nhồi mọi CRUD lên một sequence.

ĐẶC TẢ
Mô tả: Upload tài liệu nguồn với tùy chọn format, visibility, recipients và AI-read.
Tiền điều kiện: Đã xác thực, có `requirement_document.upload`, recipient ACTIVE nếu shared.
Hậu điều kiện: Raw source và metadata được lưu; trả revision/status xử lý. Parse/index có thể tiếp tục nền hoặc DEGRADED. Duplicate có thể yêu cầu xác nhận/reuse.
Tác nhân chính: Người có quyền upload. Tác nhân phụ: Storage/worker pipeline.
Luồng chính: mở danh sách, tải theo quyền, chọn file/options, validate, duplicate check, lưu source/metadata, trả trạng thái.
Ngoại lệ: format sai, file rỗng/quá lớn, recipient/access sai, duplicate chưa xác nhận, storage/DB lỗi.

LIFELINE: Người dùng; Giao diện Tài liệu; Controller/API; Service; Repository; Database; Storage/Worker.

MESSAGE
1 | 1 | Người dùng -> Giao diện Tài liệu | [1] moTaiLieuNguon(project_id) | đồng bộ | chính
2 | 2 | Giao diện Tài liệu -> Controller/API | [2] listRequirementDocuments(project_id, q, status) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] listDocumentsAndCheckPermission(project_id) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findDocuments(project_id, filters) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectRequirementDocuments(filters) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traDanhSach() | trả về | chính
7 | 2 | Repository -> Service | [2] traItems() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traDanhSachHoacLoi() | trả về | chính
9 | 2 | Controller/API -> Giao diện Tài liệu | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Tài liệu -> Người dùng | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi]
11 | 5-6 | Người dùng -> Giao diện Tài liệu | [5] chonFileVaXacNhanUpload(file, options) | đồng bộ | opt [Upload]
12 | 7 | Giao diện Tài liệu -> Controller/API | [7] uploadRequirementDocument(file, format, visibility, ai_enabled) | đồng bộ | opt [Upload hợp lệ]
13 | 7 | Controller/API -> Service | [7] uploadRequirementDocumentRecord(payload) | đồng bộ | opt [Upload hợp lệ]
14 | 7-8 | Service -> Service | [7] validateFormatSizeRecipientsAndDuplicate() | tự gọi | alt [Hợp lệ/validation error]
15 | 9 | Service -> Storage/Worker | [9] storeRawSourceAndQueueIngestion(file) | đồng bộ | alt [Lưu thành công/lỗi]
16 | 9 | Storage/Worker -> Service | [9] traSourceKeyVaIngestionStatus() | trả về | alt [Lưu thành công/lỗi]
17 | 9 | Service -> Repository | [9] insertDocumentMetadata(status, source_key) | đồng bộ | alt [Metadata thành công/lỗi]
18 | 9 | Repository -> Database | [9] insertRequirementDocument(document) | đồng bộ | alt [Metadata thành công/lỗi]
19 | 9 | Database -> Repository | [9] traDocumentRevision() | trả về | alt [Metadata thành công/lỗi]
20 | 9 | Repository -> Service | [9] traDocument() | trả về | alt [Metadata thành công/lỗi]
21 | 10 | Service -> Controller/API | [10] traDocumentAndProcessingStatus() | trả về | alt [Được tạo/lỗi]
22 | 10 | Controller/API -> Giao diện Tài liệu | [10] traResponse(status, revision) | trả về | alt [Được tạo/lỗi]
23 | 10 | Giao diện Tài liệu -> Người dùng | [10] hienThiTaiLieuVaTrangThai() | trả về | alt [Được tạo/lỗi]

YÊU CẦU: Đủ 7 lifeline, 23 message; activation bar; self-message validation; không gọi nhảy tầng. alt/opt có guard. Tách response API khỏi trạng thái parse/index, không khẳng định extraction hoàn tất ngay.
KIỂM TRA: lifeline = 7, message = 23, fragment = 3. Báo kết quả cuối.
```

## TỰ KIỂM TRA UC15

- [x] Phần 1 phân biệt quyền dự án, visibility, shared recipients và AI-read.
- [x] Phần 2 gồm xem/tìm, thêm, sửa, chia sẻ, download, archive/restore và lỗi xử lý nền.
- [x] Activity: 16 Action, 2 Decision, 25 cạnh.
- [x] Sequence: 7 lifeline, 23 message, ba nhóm fragment.
- [x] Prompt tự đủ; upload không bị mô tả là trích xuất đồng bộ chắc chắn.

## Bảng theo dõi sau UC15

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC16 - Quản lý kế hoạch kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | “Danh sách kế hoạch” chưa nêu quyền đọc, tìm/lọc, xem chi tiết và dữ liệu không tìm thấy. | Bổ sung quyền `testplan.read`, bộ lọc project/status/environment/period và phản hồi lỗi. |
| 4-8 | THIẾU | Luồng tạo không phân biệt lưu DRAFT với lưu READY; trường hợp READY có thể tự gửi/duyệt theo quyền. | Tách lựa chọn save_as_draft; READY yêu cầu objective và requirement scope; tự duyệt là có điều kiện, không mặc định. |
| 5, 7 | MƠ HỒ | “Chọn yêu cầu” không nói phải là phiên bản baseline; chưa kiểm suite/case/owner/period/environment. | Nêu kiểm tra requirement version, suite/case scope, owner ACTIVE, environment và period theo API. |
| 3.2 | THIẾU | Tìm kiếm/lọc chưa ghi rõ điều kiện và quay lại danh sách. | Ghi tìm/lọc theo tham số được hỗ trợ rồi quay lại danh sách. |
| 3.3 | THIẾU | Cập nhật thiếu revision lạc quan và điều kiện status DRAFT/READY. | Thêm expected revision; chỉ DRAFT/READY được sửa trực tiếp. |
| 3.4 | THIẾU | Nhân bản chưa nói nội dung chuẩn/approval metadata nào bị sao chép. | Ghi clone tạo DRAFT revision 1, gỡ approval/baseline/history metadata; giữ liên kết nguồn. |
| 3.5 | THIẾU | Lưu trữ thiếu lý do, revision và trạng thái ARCHIVED. | Ghi quyền `testplan.archive`, lý do, expected revision, audit; không xóa kế hoạch. |
| 5.1, 7.3 | MÂU THUẪN | Luồng cho tạo chu kỳ mới từ kỳ đã đóng nhưng exception nói chọn kỳ đã đóng thì bị từ chối. | Phân biệt chọn chu kỳ đang đóng trực tiếp với tạo chu kỳ mới lấy carry-over từ nguồn đã đóng; nguồn đóng được phép cho carry-over theo API. |
| Ngoại lệ | THIẾU | Thiếu period conflict/closed, owner không ACTIVE, scope sai, revision conflict, lỗi CSDL, hủy tạo. | Thêm lỗi theo validator/service; hủy trước gửi không tạo plan. |

Đã kiểm: **5 điểm rẽ, 7 nhánh chức năng, 10 nhóm lỗi** gồm permission/auth, thiếu objective/scope, owner không ACTIVE, invalid requirement/suite/case, period không tồn tại/đóng, environment/carry-over sai, revision/state conflict, validation schema, lỗi transaction/CSDL, hủy. UC quản lý có list/search/filter/detail/create/update/clone/archive; không có hard-delete trong đặc tả này.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Tester hoặc người có quyền xem/tìm/lọc kế hoạch, tạo ở DRAFT/READY, sửa DRAFT/READY, nhân bản thành DRAFT, lưu trữ kế hoạch và tạo chu kỳ kiểm thử cùng kế hoạch khi phù hợp.

**Tiền điều kiện:** Đã xác thực; dự án tồn tại; quyền `testplan.read/create/update/archive` tương ứng. Scope yêu cầu phải là các version thuộc project và hợp lệ; owner phải là thành viên ACTIVE. Period trực tiếp được chọn không CLOSED.

**Hậu điều kiện:** Tạo/sửa/clone lưu trạng thái phù hợp; clone tạo DRAFT và xóa approval metadata; archive chuyển ARCHIVED, giữ dữ liệu. Thất bại validation/revision không ghi đè. Khi tạo READY và điều kiện policy cho phép, backend có thể tự chuyển sang bước gửi/duyệt. Hủy biểu mẫu trước gửi không tạo kế hoạch.

**Tác nhân chính:** Tester hoặc người có quyền tương ứng trong dự án.

**Tác nhân phụ:** Không có hệ thống ngoài.

**Luồng sự kiện chính: Tạo kế hoạch DRAFT**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang Kế hoạch kiểm thử. | |
| 2 | | Kiểm tra `testplan.read`, tải danh sách theo query, status, environment, period và sort. |
| 3 | Chọn Tạo kế hoạch. | |
| 4 | | Hiển thị form thông tin kế hoạch, scope yêu cầu/suite/case, owner, environment, period và carry-over. |
| 5 | Nhập thông tin, chọn Lưu nháp. | |
| 6 | | Kiểm tra `testplan.create`, project, owner ACTIVE, scope IDs, period/environment và dữ liệu theo schema. |
| 7 | | Tạo bản ghi plan trạng thái DRAFT, revision 1; nếu có yêu cầu tạo period mới thì tạo period trong transaction cùng plan. |
| 8 | | Ghi audit, trả kế hoạch mới và cập nhật danh sách. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | Nhập từ khóa/chọn status, environment, period hoặc sort. | Tải lại danh sách theo bộ lọc; quay lại bước 2. |
| 2.2 | Chọn kế hoạch. | Kiểm tra quyền và hiển thị chi tiết; kết thúc nhánh xem. |
| 5.1 | Chọn Lưu kế hoạch thay vì Lưu nháp. | Yêu cầu objective và ít nhất một requirement version hợp lệ; tạo READY. Nếu policy tự duyệt đủ điều kiện, có thể chuyển tiếp theo workflow. |
| 2.3 | Chọn kế hoạch DRAFT/READY, sửa nội dung/scope và lưu. | Kiểm tra status, expected revision, owner/period/scope; lưu cập nhật. |
| 2.4 | Chọn Nhân bản. | Tạo bản DRAFT mới revision 1, source_plan_id liên kết bản gốc, loại approval/baseline history. |
| 2.5 | Chọn Lưu trữ, nhập lý do và xác nhận. | Kiểm tra quyền/revision, chuyển ARCHIVED, ghi reason/actor/time/audit. |
| 4.1 | Chọn tạo period mới; có thể chọn period CLOSED làm nguồn carry-over. | Tạo period mới trong transaction với plan; không dùng period CLOSED trực tiếp làm period đích. |
| 6.1 | Hủy trước khi lưu. | Trở về danh sách; không tạo plan/period mới. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Hết xác thực/thiếu quyền đọc hoặc plan không thuộc dự án: từ chối truy cập. |
| 6.1 | | Objective hoặc requirement scope thiếu khi không lưu draft: trả lỗi TEST_PLAN_INCOMPLETE, yêu cầu sửa form. |
| 6.2 | | Owner không còn ACTIVE, requirement/suite/case không thuộc scope, environment không hợp lệ: từ chối lưu. |
| 6.3 | | Period không tồn tại/đã CLOSED khi được chọn làm đích, hoặc source period không CLOSED khi dùng carry-over: trả lỗi phù hợp. |
| 6.4 | | Expected revision cũ hoặc plan đã chuyển trạng thái khác DRAFT/READY: từ chối cập nhật, yêu cầu tải lại. |
| 7.1 | | Transaction tạo plan/period hoặc ghi audit lỗi: rollback và báo thất bại. |
| 2.5.1 | | Archive conflict/không đủ quyền: không đổi status. |
| 6.1.1 | | Người dùng hủy trước gửi: không ghi dữ liệu. |

**Giả định / Câu hỏi cần làm rõ:** Bảng gốc nói scope có cả yêu cầu và ca kiểm thử; backend cho tạo READY với objective + requirement scope, còn approval đầy đủ yêu cầu thêm case scope. Tên trạng thái “Sẵn sàng” tương ứng READY. Tạo period mới cùng plan có nhiều trường riêng và nên có UC quản lý period nếu cần mô tả sâu.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu tại trang kế hoạch |
| A1 | 1 | Action | Người dùng | [1] Mở trang kế hoạch kiểm thử |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền và bộ lọc |
| D1 | 3 | Decision | Người dùng | [3] Chọn xem, tìm, tạo, sửa, clone hay archive? |
| A3 | 2.1 | Action | Người dùng | [2.1] Tìm hoặc lọc kế hoạch |
| A4 | 2.2 | Action | Người dùng | [2.2] Mở chi tiết kế hoạch |
| A5 | 5 | Action | Người dùng | [5] Nhập dữ liệu và chọn Lưu nháp |
| A6 | 5.1 | Action | Người dùng | [5.1] Nhập dữ liệu và chọn Lưu kế hoạch |
| A7 | 2.3 | Action | Người dùng | [2.3] Sửa kế hoạch DRAFT/READY |
| A8 | 2.4 | Action | Người dùng | [2.4] Nhân bản kế hoạch |
| A9 | 2.5 | Action | Người dùng | [2.5] Xác nhận lưu trữ |
| A10 | 6 | Action | Hệ thống | [6] Kiểm tra quyền, scope, owner, period và revision |
| D2 | 6 | Decision | Hệ thống | [6] Dữ liệu hợp lệ và thao tác được phép? |
| A11 | 7-8 | Action | Hệ thống | [7] Ghi plan/period, audit và trả kết quả |
| A12 | 6.1/6.2 | Action | Hệ thống | [6.1] Báo validation, quyền hoặc conflict |
| A13 | 6.1 | Action | Người dùng | [6.1] Hủy form tạo |
| F1 | 8/2.2/2.4/2.5 | Final | Hệ thống | Kết thúc với kết quả thao tác |
| F2 | 6.1/6.2 | Final | Hệ thống | Kết thúc không tạo hoặc cập nhật |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách tải xong |
| D1 | A3 | [Tìm/lọc] |
| A3 | A2 | [Tải kết quả mới] |
| D1 | A4 | [Xem chi tiết] |
| A4 | F1 | Chi tiết hiển thị |
| D1 | A5 | [Tạo/lưu DRAFT] |
| D1 | A6 | [Tạo READY] |
| D1 | A7 | [Sửa DRAFT/READY] |
| D1 | A8 | [Clone] |
| D1 | A9 | [Archive] |
| A5 | A10 | Đã gửi payload draft |
| A6 | A10 | Đã gửi payload READY |
| A7 | A10 | Đã gửi patch với revision |
| A8 | A10 | Đã yêu cầu clone |
| A9 | A10 | Đã xác nhận reason archive |
| A10 | D2 | Kiểm tra xong |
| D2 | A11 | [Đủ quyền, scope/status/revision hợp lệ] |
| A11 | F1 | Đã trả kết quả |
| D2 | A12 | [Validation/quyền/state/revision lỗi] |
| A12 | F2 | Đã báo lỗi |
| A5 | A13 | [Hủy trước gửi] |
| A13 | F2 | Không tạo plan |

### 3c. Số liệu

N = 9 ô có nội dung; M = 13 Action; D = 2 Decision; E = 23 cạnh. Tạo DRAFT/READY, update, clone, archive và read/filter có nhánh riêng.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa tạo DRAFT. Các thao tác cập nhật/clone/archive được giữ trong đặc tả và Activity để Sequence không quá dày.

### 4a. Lifeline trái sang phải

Tester → Giao diện Kế hoạch → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Kế hoạch | [1] moTrangKeHoach(project_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Kế hoạch | Controller/API | [2] listTestPlans(project_id, filters) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listTestPlanRecords(filters) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findPlans(project_id, filters) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectTestPlans(filters) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDanhSachPlan() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traPlans() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traPlansHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Kế hoạch | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Kế hoạch | Tester | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Tester | Giao diện Kế hoạch | [3] nhapKeHoachVaChonLuuNhAp(payload) | đồng bộ | opt [Tạo DRAFT] |
| 12 | 6 | Giao diện Kế hoạch | Controller/API | [6] createTestPlan(save_as_draft=true, payload) | đồng bộ | opt [Tạo DRAFT] |
| 13 | 6 | Controller/API | Service | [6] createTestPlanRecord(payload, project_id) | đồng bộ | opt [Tạo DRAFT] |
| 14 | 6 | Service | Service | [6] validateOwnerScopePeriodEnvironment() | tự gọi | opt [Tạo DRAFT] |
| 15 | 7 | Service | Repository | [7] insertPlan(plan) | đồng bộ | alt [Ghi thành công/lỗi] |
| 16 | 7 | Repository | Database | [7] insertTestPlanAndAudit(plan) | đồng bộ | alt [Ghi thành công/lỗi] |
| 17 | 7 | Database | Repository | [7] traPlanRevision() | trả về | alt [Ghi thành công/lỗi] |
| 18 | 7 | Repository | Service | [7] traPlan() | trả về | alt [Ghi thành công/lỗi] |
| 19 | 8 | Service | Controller/API | [8] traPlanMoiHoacLoi() | trả về | alt [Tạo thành công/lỗi] |
| 20 | 8 | Controller/API | Giao diện Kế hoạch | [8] traResponse() | trả về | alt [Tạo thành công/lỗi] |
| 21 | 8 | Giao diện Kế hoạch | Tester | [8] hienThiPlanVaCapNhatDanhSach() | trả về | alt [Tạo thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 21, fragment = 3: alt tải, opt tạo DRAFT, alt ghi thành công/lỗi. Tạo period mới chưa chọn trong kịch bản sequence này.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC16 - Quản lý kế hoạch kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt, swimlane Người dùng/Hệ thống. Bố cục rõ nhánh list/read/create/update/clone/archive.

ĐẶC TẢ
Mô tả: Người có quyền xem/tìm/lọc, tạo DRAFT/READY, sửa, clone thành DRAFT, archive kế hoạch.
Tiền điều kiện: Đã xác thực, project tồn tại, quyền theo thao tác; scope IDs thuộc project; owner ACTIVE; period đích không CLOSED.
Hậu điều kiện: Plan lưu đúng trạng thái; clone tạo DRAFT revision 1, bỏ approval metadata; archive giữ nội dung; lỗi/hủy không báo lưu thành công. READY có thể theo policy tự gửi/duyệt.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Không có.
Luồng: mở trang và tải danh sách; chọn tìm/lọc, xem chi tiết, tạo DRAFT/READY, update, clone, archive. Validate objective/scope/owner/period/environment/revision. DRAFT được lưu; READY yêu cầu objective và requirement scope. Có thể tạo period mới cùng plan, lấy carry-over từ period CLOSED làm nguồn.
Ngoại lệ: permission, objective/scope thiếu, owner inactive, invalid requirement/suite/case/environment, period closed/missing, stale revision/status, transaction lỗi, hủy.

NODE
I Initial Người dùng Bắt đầu tại trang kế hoạch
A1 Action Người dùng [1] Mở trang kế hoạch kiểm thử
A2 Action Hệ thống [2] Tải danh sách theo quyền và bộ lọc
D1 Decision Người dùng [3] Chọn xem, tìm, tạo, sửa, clone hay archive?
A3 Action Người dùng [2.1] Tìm hoặc lọc kế hoạch
A4 Action Người dùng [2.2] Mở chi tiết kế hoạch
A5 Action Người dùng [5] Nhập dữ liệu và chọn Lưu nháp
A6 Action Người dùng [5.1] Nhập dữ liệu và chọn Lưu kế hoạch
A7 Action Người dùng [2.3] Sửa kế hoạch DRAFT/READY
A8 Action Người dùng [2.4] Nhân bản kế hoạch
A9 Action Người dùng [2.5] Xác nhận lưu trữ
A10 Action Hệ thống [6] Kiểm tra quyền, scope, owner, period và revision
D2 Decision Hệ thống [6] Dữ liệu hợp lệ và thao tác được phép?
A11 Action Hệ thống [7] Ghi plan/period, audit và trả kết quả
A12 Action Hệ thống [6.1] Báo validation, quyền hoặc conflict
A13 Action Người dùng [6.1] Hủy form tạo
F1 Final Hệ thống Kết thúc với kết quả thao tác
F2 Final Hệ thống Kết thúc không tạo hoặc cập nhật

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Danh sách tải xong]
D1 -> A3 [Tìm/lọc]
A3 -> A2 [Tải kết quả mới]
D1 -> A4 [Xem chi tiết]
A4 -> F1 [Chi tiết hiển thị]
D1 -> A5 [Tạo/lưu DRAFT]
D1 -> A6 [Tạo READY]
D1 -> A7 [Sửa DRAFT/READY]
D1 -> A8 [Clone]
D1 -> A9 [Archive]
A5 -> A10 [Đã gửi payload draft]
A6 -> A10 [Đã gửi payload READY]
A7 -> A10 [Đã gửi patch với revision]
A8 -> A10 [Đã yêu cầu clone]
A9 -> A10 [Đã xác nhận reason archive]
A10 -> D2 [Kiểm tra xong]
D2 -> A11 [Đủ quyền, scope/status/revision hợp lệ]
A11 -> F1 [Đã trả kết quả]
D2 -> A12 [Validation/quyền/state/revision lỗi]
A12 -> F2 [Đã báo lỗi]
A5 -> A13 [Hủy trước gửi]
A13 -> F2 [Không tạo plan]

YÊU CẦU: Guard trên mọi cạnh ra Decision, không gộp CRUD. Final thành công/thất bại riêng. Không coi period CLOSED là period đích hợp lệ; chỉ dùng làm nguồn carry-over khi tạo kỳ mới.
KIỂM TRA: Action = 13, Decision = 2, cạnh = 23. Báo kết quả.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC16 - Quản lý kế hoạch kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Chỉ minh họa tạo plan DRAFT để sơ đồ vừa trang luận văn.

ĐẶC TẢ
Mô tả: Tester/người có quyền tạo kế hoạch DRAFT.
Tiền điều kiện: Đã xác thực, project tồn tại, có `testplan.create`; các tham chiếu và owner phải thuộc project/hợp lệ.
Hậu điều kiện: Plan DRAFT revision 1 được lưu, audit được ghi; lỗi validation/transaction không báo tạo thành công.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Không có.
Luồng chính: mở danh sách, UI tải plans; nhập form và lưu draft; API kiểm tra quyền/scope/period/owner; ghi plan; trả dữ liệu mới.
Thay thế: READY/update/clone/archive nằm trong Activity, không thuộc sequence minh họa.
Ngoại lệ: thiếu quyền, invalid scope/owner/period/environment, lỗi CSDL, hủy trước gửi.

LIFELINE: Tester; Giao diện Kế hoạch; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Tester -> Giao diện Kế hoạch | [1] moTrangKeHoach(project_id) | đồng bộ | chính
2 | 2 | Giao diện Kế hoạch -> Controller/API | [2] listTestPlans(project_id, filters) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] listTestPlanRecords(filters) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findPlans(project_id, filters) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectTestPlans(filters) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traDanhSachPlan() | trả về | chính
7 | 2 | Repository -> Service | [2] traPlans() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traPlansHoacLoi() | trả về | chính
9 | 2 | Controller/API -> Giao diện Kế hoạch | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Kế hoạch -> Tester | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi]
11 | 3-5 | Tester -> Giao diện Kế hoạch | [3] nhapKeHoachVaChonLuuNhAp(payload) | đồng bộ | opt [Tạo DRAFT]
12 | 6 | Giao diện Kế hoạch -> Controller/API | [6] createTestPlan(save_as_draft=true, payload) | đồng bộ | opt [Tạo DRAFT]
13 | 6 | Controller/API -> Service | [6] createTestPlanRecord(payload, project_id) | đồng bộ | opt [Tạo DRAFT]
14 | 6 | Service -> Service | [6] validateOwnerScopePeriodEnvironment() | tự gọi | opt [Tạo DRAFT]
15 | 7 | Service -> Repository | [7] insertPlan(plan) | đồng bộ | alt [Ghi thành công/lỗi]
16 | 7 | Repository -> Database | [7] insertTestPlanAndAudit(plan) | đồng bộ | alt [Ghi thành công/lỗi]
17 | 7 | Database -> Repository | [7] traPlanRevision() | trả về | alt [Ghi thành công/lỗi]
18 | 7 | Repository -> Service | [7] traPlan() | trả về | alt [Ghi thành công/lỗi]
19 | 8 | Service -> Controller/API | [8] traPlanMoiHoacLoi() | trả về | alt [Tạo thành công/lỗi]
20 | 8 | Controller/API -> Giao diện Kế hoạch | [8] traResponse() | trả về | alt [Tạo thành công/lỗi]
21 | 8 | Giao diện Kế hoạch -> Tester | [8] hienThiPlanVaCapNhatDanhSach() | trả về | alt [Tạo thành công/lỗi]

YÊU CẦU: 6 lifeline, 21 message, activation bar; self-call validation; không gọi nhảy lớp. Mỗi sync có return qua đúng tầng. alt/opt có guard; không thêm period creation vì sequence mẫu không chọn period mới.
KIỂM TRA: lifeline = 6, message = 21, fragment = 3. Báo đối chiếu cuối.
```

## TỰ KIỂM TRA UC16

- [x] Phần 1 đối chiếu đầy đủ quyền, CRUD, period, owner và scope.
- [x] Phần 2 tách DRAFT/READY, clone, archive, search/filter và hủy.
- [x] Activity: 13 Action, 2 Decision, 23 cạnh.
- [x] Sequence: 6 lifeline, 21 message, ba fragment.
- [x] Prompt tự đủ và mô tả rõ scope của sequence.

## Bảng theo dõi sau UC16

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC17 - Trình duyệt kế hoạch kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tiền điều kiện | MƠ HỒ | “DRAFT hoặc READY” chưa nói quyền submit và trạng thái period. | Bổ sung `testplan.submit_review`, trạng thái DRAFT/READY, revision và period đang mở nếu plan gắn period. |
| 3-8 | THIẾU | “Kiểm tra hoàn thiện” không nêu tiêu chí khác nhau giữa validate trước xem và điều kiện gửi. | API check trước approval yêu cầu objective, requirement scope và test-case scope; endpoint validate công khai trả completeness. |
| 7.1-7.2 | MÂU THUẪN | Ngoại lệ 7.1/7.2 chỉ nêu objective/requirement, còn API submission cũng chặn thiếu test-case versions. | Bổ sung điều kiện test-case scope; không thêm yêu cầu suite nếu code không bắt buộc trực tiếp. |
| 3.1 | THIẾU | Nhánh validate chưa nói quyền, response findings hoặc quay lại bước gửi. | Ghi quyền đọc, trả mã findings và tiếp tục gửi ở bước 3 sau khi sửa theo UC16. |
| 6.1-6.2 | THIẾU | Hủy chưa ghi rõ không gọi API/không đổi status. | Nêu hủy hộp thoại trước gửi giữ nguyên state. |
| 7.3 | MƠ HỒ | “Chu kỳ kết thúc” chưa phân biệt period CLOSED làm nguồn carry-over với period đích của plan. | Submission chạm/touch test period đang mở; period unavailable/closed thì conflict, bản ghi không chuyển IN_REVIEW. |
| 7.4 | THIẾU | Thiếu revision conflict, state đã đổi, thiếu permission, lỗi transaction, khả năng tự duyệt. | Bổ sung nhánh theo service; auto-approval chỉ nếu policy và quyền cho phép. |

Đã kiểm: **3 điểm rẽ, 4 nhánh nghiệp vụ, 7 nhóm lỗi** gồm hết xác thực/thiếu quyền, incomplete objective/requirement/case scope, period closed/unavailable, state sai, revision conflict, lỗi transaction/CSDL và hủy. UC này không phải CRUD; thay đổi nội dung kế hoạch quay UC16.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền kiểm tra tính đầy đủ của kế hoạch và gửi version DRAFT/READY sang IN_REVIEW.

**Tiền điều kiện:** Người dùng đã xác thực, có `testplan.read` để validate hoặc `testplan.submit_review` để gửi; plan tồn tại ở DRAFT/READY, revision hiện hành; period gắn với plan không CLOSED.

**Hậu điều kiện:** Thành công đặt status IN_REVIEW, ghi người gửi/thời gian/ghi chú và audit. Nếu chính sách tự duyệt áp dụng, backend có thể tiếp tục approve và trả APPROVED. Hủy/lỗi không báo gửi thành công.

**Tác nhân chính:** Tester hoặc người có `testplan.submit_review`.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở kế hoạch cần gửi rà soát. | |
| 2 | | Kiểm tra quyền, tải nội dung/status/revision. |
| 3 | Chọn Gửi rà soát. | |
| 4 | | Hiển thị hộp thoại ghi chú gửi. |
| 5 | Nhập ghi chú và xác nhận. | |
| 6 | | Kiểm tra `testplan.submit_review`, DRAFT/READY, objective, ít nhất một requirement version, ít nhất một test-case version, expected revision và period đang mở. |
| 7 | | Trong transaction, chuyển sang IN_REVIEW, lưu note/submitter/time và audit. |
| 8 | | Nếu policy tự duyệt hợp lệ, tiếp tục approve; nếu không, giữ IN_REVIEW. |
| 9 | | Trả status mới và hiển thị kết quả. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Chọn Kiểm tra kế hoạch. | Kiểm tra `testplan.read`, trả readiness và findings: objective, requirement scope, case scope. |
| 3.2 | Xem findings, sửa bằng UC16 nếu cần. | Không đổi status; khi người dùng quay lại, tiếp tục tại bước 3. |
| 5.1 | Chọn Hủy. | Đóng hộp thoại, giữ nguyên trạng thái kế hoạch; kết thúc nhánh. |
| 8.1 | Không đủ điều kiện auto-approve. | Giữ IN_REVIEW để reviewer khác xử lý; kết thúc. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Thiếu quyền đọc/hết xác thực hoặc không tìm thấy plan: từ chối tải. |
| 6.1 | | Thiếu objective, requirement version hoặc test-case version: trả `TEST_PLAN_INCOMPLETE`, giữ nguyên status. |
| 6.2 | | Period đã CLOSED/unavailable hoặc state không còn DRAFT/READY: từ chối submit. |
| 7.1 | | Revision conflict hoặc transaction lỗi: rollback, không báo IN_REVIEW. |
| 8.2 | | Điều kiện reviewer/policy tự duyệt không đạt: giữ IN_REVIEW; đây không phải lỗi gửi nếu bước submit đã commit. |
| Mọi bước | | Lỗi API/CSDL: trả lỗi và không xác nhận thao tác chưa commit. |

**Giả định / Câu hỏi cần làm rõ:** Bảng gốc ghi Admin nhận kế hoạch, nhưng không có tích hợp thông báo bên ngoài trong luồng này. “Chu kỳ đã kết thúc” được diễn giải theo status period đích đang CLOSED; nếu muốn cho phép gửi sau khi đóng period, cần xác nhận nghiệp vụ.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu tại chi tiết kế hoạch |
| A1 | 1 | Action | Người dùng | [1] Mở kế hoạch cần gửi rà soát |
| A2 | 2 | Action | Hệ thống | [2] Tải plan, quyền và revision |
| D1 | 3 | Decision | Người dùng | [3] Chọn kiểm tra, gửi hay hủy? |
| A3 | 3.1 | Action | Người dùng | [3.1] Yêu cầu kiểm tra completeness |
| A4 | 3.1 | Action | Hệ thống | [3.1] Trả readiness và findings |
| A5 | 3.2 | Action | Người dùng | [3.2] Sửa plan theo findings |
| A6 | 4-5 | Action | Người dùng | [4] Nhập ghi chú và xác nhận gửi |
| A7 | 6 | Action | Hệ thống | [6] Kiểm quyền, scope, state, revision và period |
| D2 | 6 | Decision | Hệ thống | [6] Plan đủ điều kiện gửi? |
| A8 | 7-8 | Action | Hệ thống | [7] Chuyển IN_REVIEW và xử lý policy tự duyệt |
| A9 | 9 | Action | Hệ thống | [9] Trả status và kết quả |
| A10 | 5.1 | Action | Người dùng | [5.1] Hủy hộp thoại |
| A11 | 6.1/7.1 | Action | Hệ thống | [6.1] Báo thiếu scope, period hoặc revision conflict |
| F1 | 9/3.1 | Final | Hệ thống | Kết thúc với kết quả đã trả |
| F2 | 5.1/6.1 | Final | Hệ thống | Kết thúc không chuyển trạng thái |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Plan tải xong |
| D1 | A3 | [Kiểm tra] |
| A3 | A4 | Đã gửi validate |
| A4 | F1 | Findings đã hiển thị |
| A4 | A5 | [Cần chỉnh sửa] |
| A5 | A2 | [Đã lưu bằng UC16, tải lại] |
| D1 | A6 | [Gửi rà soát] |
| D1 | A10 | [Hủy] |
| A6 | A7 | Đã xác nhận |
| A7 | D2 | Validate xong |
| D2 | A8 | [Objective, requirement, case, period và revision hợp lệ] |
| D2 | A11 | [Thiếu điều kiện hoặc conflict] |
| A8 | A9 | Submit transaction đã trả |
| A9 | F1 | Kết quả đã hiển thị |
| A10 | F2 | Không gọi submit API |
| A11 | F2 | Không chuyển status |

### 3c. Số liệu

N = 8 ô bước có nội dung; M = 11 Action; D = 2 Decision; E = 18 cạnh. Validate là nhánh đọc, submit là nhánh chuyển trạng thái; hủy/lỗi kết thúc không đổi status.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa submit sau khi người dùng xác nhận. Validate riêng là operand alt/opt; update plan ở UC16 không nằm trong sequence này.

### 4a. Lifeline trái sang phải

Tester → Giao diện Kế hoạch → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Kế hoạch | [1] moKeHoach(plan_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Kế hoạch | Controller/API | [2] getTestPlan(plan_id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] getTestPlanRecord(plan_id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findPlan(plan_id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectTestPlan(plan_id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traPlan() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traPlanHoacLoi() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traResponse() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Kế hoạch | [2] traPlan() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Kế hoạch | Tester | [2] hienThiPlan() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3.1 | Tester | Giao diện Kế hoạch | [3.1] yeuCauKiemTraPlan() | đồng bộ | opt [Kiểm tra trước] |
| 12 | 3.1 | Giao diện Kế hoạch | Controller/API | [3.1] validateTestPlan(plan_id) | đồng bộ | opt [Kiểm tra trước] |
| 13 | 3.1 | Controller/API | Service | [3.1] validateTestPlanRecord(plan_id) | đồng bộ | opt [Kiểm tra trước] |
| 14 | 3.1 | Service | Service | [3.1] evaluateObjectiveRequirementAndCaseScope() | tự gọi | opt [Kiểm tra trước] |
| 15 | 3.1 | Service | Controller/API | [3.1] traReadinessAndFindings() | trả về | opt [Kiểm tra trước] |
| 16 | 3.1 | Controller/API | Giao diện Kế hoạch | [3.1] traFindings() | trả về | opt [Kiểm tra trước] |
| 17 | 3.1 | Giao diện Kế hoạch | Tester | [3.1] hienThiFindings() | trả về | opt [Kiểm tra trước] |
| 18 | 4-5 | Tester | Giao diện Kế hoạch | [4] xacNhanGuiRaSoat(note) | đồng bộ | opt [Submit] |
| 19 | 6 | Giao diện Kế hoạch | Controller/API | [6] submitTestPlan(expected_revision, note) | đồng bộ | opt [Submit] |
| 20 | 6 | Controller/API | Service | [6] submitTestPlanRecord(payload) | đồng bộ | opt [Submit] |
| 21 | 6 | Service | Service | [6] validatePermissionCompletenessPeriodRevision() | tự gọi | alt [Hợp lệ/lỗi] |
| 22 | 7 | Service | Repository | [7] optimisticPatchStatus(IN_REVIEW) | đồng bộ | alt [Commit/conflict] |
| 23 | 7 | Repository | Database | [7] transactionSubmitAndAudit(plan) | đồng bộ | alt [Commit/lỗi] |
| 24 | 7 | Database | Repository | [7] traPlanRevision() | trả về | alt [Commit/lỗi] |
| 25 | 7 | Repository | Service | [7] traSubmittedPlan() | trả về | alt [Commit/lỗi] |
| 26 | 8 | Service | Service | [8] checkAutoApprovalPolicy() | tự gọi | opt [Policy tự duyệt] |
| 27 | 8 | Service | Controller/API | [8] traStatusIN_REVIEWHoacAPPROVED() | trả về | alt [Submit thành công/lỗi] |
| 28 | 9 | Controller/API | Giao diện Kế hoạch | [9] traKetQuaSubmit() | trả về | alt [Submit thành công/lỗi] |
| 29 | 9 | Giao diện Kế hoạch | Tester | [9] hienThiTrangThai() | trả về | alt [Submit thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 29, fragment = 4: opt validate, opt submit, alt validation/commit, opt auto-approval. Mỗi request đồng bộ được trả kết quả qua các tầng.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC17 - Trình duyệt kế hoạch kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Người dùng/Hệ thống. Tách thao tác kiểm tra completeness và submit.

ĐẶC TẢ
Mô tả: Kiểm tra readiness và gửi plan DRAFT/READY sang IN_REVIEW.
Tiền điều kiện: Đã xác thực, quyền `testplan.read` cho validate hoặc `testplan.submit_review` để gửi; plan/revision tồn tại, period đích còn mở.
Hậu điều kiện: Submit lưu IN_REVIEW, submitter/time/note/audit; policy có thể tiếp tục auto-approve. Hủy/lỗi không báo gửi.
Tác nhân chính: Tester/người được quyền. Tác nhân phụ: Không có.
Luồng chính: mở plan; tải quyền/status; chọn gửi; nhập note; hệ thống kiểm objective, requirement versions, test-case versions, period, status, revision; commit IN_REVIEW; kiểm tra policy; trả kết quả.
Thay thế: validate trả findings; người dùng sửa bằng UC16; hủy; nếu policy không tự duyệt thì giữ IN_REVIEW.
Ngoại lệ: incomplete scope/objective, permission/auth, period closed, state/revision conflict, transaction/DB lỗi.

NODE
I Initial Người dùng Bắt đầu tại chi tiết kế hoạch
A1 Action Người dùng [1] Mở kế hoạch cần gửi rà soát
A2 Action Hệ thống [2] Tải plan, quyền và revision
D1 Decision Người dùng [3] Chọn kiểm tra, gửi hay hủy?
A3 Action Người dùng [3.1] Yêu cầu kiểm tra completeness
A4 Action Hệ thống [3.1] Trả readiness và findings
A5 Action Người dùng [3.2] Sửa plan theo findings
A6 Action Người dùng [4] Nhập ghi chú và xác nhận gửi
A7 Action Hệ thống [6] Kiểm quyền, scope, state, revision và period
D2 Decision Hệ thống [6] Plan đủ điều kiện gửi?
A8 Action Hệ thống [7] Chuyển IN_REVIEW và xử lý policy tự duyệt
A9 Action Hệ thống [9] Trả status và kết quả
A10 Action Người dùng [5.1] Hủy hộp thoại
A11 Action Hệ thống [6.1] Báo thiếu scope, period hoặc revision conflict
F1 Final Hệ thống Kết thúc với kết quả đã trả
F2 Final Hệ thống Kết thúc không chuyển trạng thái

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Plan tải xong]
D1 -> A3 [Kiểm tra]
A3 -> A4 [Đã gửi validate]
A4 -> F1 [Findings hiển thị]
A4 -> A5 [Cần chỉnh sửa]
A5 -> A2 [Đã lưu bằng UC16 và tải lại]
D1 -> A6 [Gửi rà soát]
D1 -> A10 [Hủy]
A6 -> A7 [Đã xác nhận]
A7 -> D2 [Validate xong]
D2 -> A8 [Objective, requirement, case, period, revision hợp lệ]
D2 -> A11 [Thiếu điều kiện hoặc conflict]
A8 -> A9 [Submit transaction trả]
A9 -> F1 [Đã hiển thị kết quả]
A10 -> F2 [Không gọi submit]
A11 -> F2 [Không chuyển status]

YÊU CẦU: Decision có guard; validate không đổi status; không trộn luồng UC16 chỉnh sửa; final riêng; không thêm gửi email.
KIỂM TRA: Action = 11, Decision = 2, cạnh = 18. Báo đối chiếu cuối.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC17 - Trình duyệt kế hoạch kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Sequence minh họa submit sau xác nhận, có nhánh validate riêng.

ĐẶC TẢ
Mô tả: Gửi plan DRAFT/READY đủ điều kiện sang IN_REVIEW.
Tiền điều kiện: Đã xác thực, có `testplan.submit_review`; plan/current revision tồn tại; period đang mở.
Hậu điều kiện: Lưu status IN_REVIEW, note, submitter/time/audit; policy có thể auto-approve. Lỗi không báo thành công.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Không có.
Luồng chính: load plan, validate tùy chọn, xác nhận submit, kiểm completeness/objective/requirement/test-case scope/period/revision, transaction đổi state, policy, phản hồi UI.
Thay thế: validate findings, hủy hộp thoại.
Ngoại lệ: permission, scope thiếu, period unavailable, invalid state, revision conflict, DB error.

LIFELINE: Tester; Giao diện Kế hoạch; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Tester -> Giao diện Kế hoạch | [1] moKeHoach(plan_id) | đồng bộ | chính
2 | 2 | Giao diện Kế hoạch -> Controller/API | [2] getTestPlan(plan_id) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] getTestPlanRecord(plan_id) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findPlan(plan_id) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectTestPlan(plan_id) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traPlan() | trả về | chính
7 | 2 | Repository -> Service | [2] traPlanHoacLoi() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traResponse() | trả về | chính
9 | 2 | Controller/API -> Giao diện Kế hoạch | [2] traPlan() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Kế hoạch -> Tester | [2] hienThiPlan() | trả về | alt [Tải thành công/lỗi]
11 | 3.1 | Tester -> Giao diện Kế hoạch | [3.1] yeuCauKiemTraPlan() | đồng bộ | opt [Kiểm tra trước]
12 | 3.1 | Giao diện Kế hoạch -> Controller/API | [3.1] validateTestPlan(plan_id) | đồng bộ | opt [Kiểm tra trước]
13 | 3.1 | Controller/API -> Service | [3.1] validateTestPlanRecord(plan_id) | đồng bộ | opt [Kiểm tra trước]
14 | 3.1 | Service -> Service | [3.1] evaluateObjectiveRequirementAndCaseScope() | tự gọi | opt [Kiểm tra trước]
15 | 3.1 | Service -> Controller/API | [3.1] traReadinessAndFindings() | trả về | opt [Kiểm tra trước]
16 | 3.1 | Controller/API -> Giao diện Kế hoạch | [3.1] traFindings() | trả về | opt [Kiểm tra trước]
17 | 3.1 | Giao diện Kế hoạch -> Tester | [3.1] hienThiFindings() | trả về | opt [Kiểm tra trước]
18 | 4-5 | Tester -> Giao diện Kế hoạch | [4] xacNhanGuiRaSoat(note) | đồng bộ | opt [Submit]
19 | 6 | Giao diện Kế hoạch -> Controller/API | [6] submitTestPlan(expected_revision, note) | đồng bộ | opt [Submit]
20 | 6 | Controller/API -> Service | [6] submitTestPlanRecord(payload) | đồng bộ | opt [Submit]
21 | 6 | Service -> Service | [6] validatePermissionCompletenessPeriodRevision() | tự gọi | alt [Hợp lệ/lỗi]
22 | 7 | Service -> Repository | [7] optimisticPatchStatus(IN_REVIEW) | đồng bộ | alt [Commit/conflict]
23 | 7 | Repository -> Database | [7] transactionSubmitAndAudit(plan) | đồng bộ | alt [Commit/lỗi]
24 | 7 | Database -> Repository | [7] traPlanRevision() | trả về | alt [Commit/lỗi]
25 | 7 | Repository -> Service | [7] traSubmittedPlan() | trả về | alt [Commit/lỗi]
26 | 8 | Service -> Service | [8] checkAutoApprovalPolicy() | tự gọi | opt [Policy tự duyệt]
27 | 8 | Service -> Controller/API | [8] traStatusIN_REVIEWHoacAPPROVED() | trả về | alt [Submit thành công/lỗi]
28 | 9 | Controller/API -> Giao diện Kế hoạch | [9] traKetQuaSubmit() | trả về | alt [Submit thành công/lỗi]
29 | 9 | Giao diện Kế hoạch -> Tester | [9] hienThiTrangThai() | trả về | alt [Submit thành công/lỗi]

YÊU CẦU: Đủ 6 lifeline, 29 message, activation bar, self-message validation/policy. Không gọi nhảy tầng; mỗi request sync có return. Guards rõ, hủy thì không submit.
KIỂM TRA: lifeline = 6, message = 29, fragment = 4. Báo kết quả cuối sơ đồ.
```

## TỰ KIỂM TRA UC17

- [x] Phần 1 phân biệt validate completeness với submit state transition.
- [x] Phần 2 nêu objective, requirement scope, case scope, period, quyền và revision.
- [x] Activity: 11 Action, 2 Decision, 18 cạnh.
- [x] Sequence: 6 lifeline, 29 message, bốn nhóm fragment.
- [x] Prompt tự đủ và không thay UC16.

## Bảng theo dõi sau UC17

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC18 - Xét duyệt kế hoạch kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tác nhân/tiền điều kiện | MƠ HỒ | “Admin” và quyền “xét duyệt” chưa phân biệt `testplan.approve` với `testplan.review`. | Tách quyền approve và request changes; yêu cầu independent review để người tạo không tự duyệt theo policy. |
| 1-3 | THIẾU | Chưa nêu snapshot, tiêu chí completeness hay period; người duyệt phải xem dữ liệu hiện hành. | Thêm tải plan/status/revision, validate objective/requirement/case scope và period. |
| 4-9 | THIẾU | Phê duyệt chưa mô tả approved snapshot/hash và approval history. | Nêu chụp snapshot tại thời điểm duyệt, ghi hash, actor/time/note và audit. |
| 4.1 | SAI | Nhánh yêu cầu chỉnh sửa đánh số 4.1 nhưng cần xác định lựa chọn tại bước 4; phần phụ bước phải theo điểm rẽ. | Giữ nhánh 4.1 có ghi chú; tách note bắt buộc, transition IN_REVIEW sang DRAFT. |
| 5.1 | MƠ HỒ | “Thiếu phạm vi” chưa nêu findings cụ thể. | Nêu objective, requirement scope, test-case scope; endpoint validate trả findings. |
| 7.1 | THIẾU | Suite snapshot thay đổi chưa nêu hậu quả. | Chặn approve với `TEST_SET_CHANGED_REVIEW_REQUIRED`, yêu cầu gửi rà soát lại. |
| 7.2 | THIẾU | Chưa nêu revision conflict/self-review/status conflict, period đóng, lỗi CSDL, hủy. | Thêm nhánh lỗi; cancel trước API không đổi status. |
| CRUD/coverage | MƠ HỒ | UC xét duyệt không phải chức năng quản lý plan CRUD; “xem” chỉ phục vụ review. | Không ép thêm create/update/delete; chuyển nội dung sang UC16. |

Đã kiểm: **3 điểm rẽ, 4 nhánh kết quả, 8 nhóm lỗi** gồm thiếu quyền/hết xác thực, state sai, self-review bị cấm, incomplete scope, suite snapshot đổi, revision conflict, period unavailable, transaction/CSDL lỗi và hủy. Không có thao tác xóa.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền xem và đánh giá plan đang IN_REVIEW, sau đó phê duyệt thành APPROVED hoặc yêu cầu chỉnh sửa về DRAFT.

**Tiền điều kiện:** Đã xác thực; plan ở IN_REVIEW; người phê duyệt có `testplan.approve` và qua kiểm tra independent review; yêu cầu chỉnh sửa cần `testplan.review`. Scope hiện hành phải đọc được trong project.

**Hậu điều kiện:**
- Phê duyệt: plan chuyển APPROVED; lưu approved snapshot/hash, baseline hash, actor/time/note, approval history và audit.
- Yêu cầu chỉnh sửa: plan chuyển DRAFT; note và history lưu action CHANGES_REQUESTED.
- Thất bại/hủy: không được báo đã đổi status. Scope thay đổi hoặc revision conflict yêu cầu tải/gửi rà soát lại.

**Tác nhân chính:** Reviewer/Admin theo nghiệp vụ có quyền approve hoặc review.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính: Phê duyệt kế hoạch**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở plan IN_REVIEW. | |
| 2 | | Kiểm tra quyền, tải plan, status, revision và scope snapshot. |
| 3 | Rà soát mục tiêu, requirement/case scope, cách tiếp cận và tiêu chí. | |
| 4 | Chọn Phê duyệt kế hoạch. | |
| 5 | | Kiểm tra completeness; nếu đủ thì hiển thị xác nhận và trường ghi chú. |
| 6 | Nhập ghi chú và xác nhận. | |
| 7 | | Kiểm tra `testplan.approve`, independent review, status/revision, scope và period. |
| 8 | | Tính approved snapshot/hash; trong transaction cập nhật APPROVED, approval history và audit. |
| 9 | | Trả plan được duyệt và cập nhật giao diện. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 4.1 | Chọn Yêu cầu chỉnh sửa, nhập nhận xét bắt buộc và xác nhận. | Kiểm tra `testplan.review`, independent review, status/revision; transaction chuyển DRAFT, lưu nhận xét/history/audit. Kết thúc. |
| 5.1 | Chọn Hủy hộp thoại. | Đóng hộp thoại, giữ IN_REVIEW; kết thúc nhánh. |
| 5.2 | Chọn Kiểm tra trước khi duyệt. | Trả completeness findings; không đổi status. Quay lại bước 3 sau khi nội dung được bổ sung qua UC16. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Không có quyền đọc/hết xác thực/plan không tồn tại: từ chối tải. |
| 7.1 | | Không có approve permission hoặc vi phạm independent review: từ chối, không đổi status. |
| 7.2 | | Plan không còn IN_REVIEW, revision thay đổi hoặc period unavailable: conflict; yêu cầu tải lại. |
| 7.3 | | Objective/requirement/case scope thiếu: trả `TEST_PLAN_INCOMPLETE`, không approve. |
| 7.4 | | Test suite snapshot đã đổi so với snapshot được rà soát: trả `TEST_SET_CHANGED_REVIEW_REQUIRED`, cần rà soát lại. |
| 8.1 | | Transaction/audit lỗi: rollback approval state, báo thất bại. |
| 4.1.1 | | Note yêu cầu chỉnh sửa rỗng hoặc revision/status conflict: từ chối transition. |
| 5.1.1 | | Hủy trước xác nhận: không gọi mutation API. |

**Giả định / Câu hỏi cần làm rõ:** Bảng gốc gọi người duyệt là Admin; hệ thống dùng quyền và policy độc lập, nên không khóa đặc tả vào một tên role. Note tại UI hiện là trường bắt buộc ở dialog cho cả approve/revise, trong khi endpoint approval schema có thể cho chuỗi rỗng; đặc tả ưu tiên ràng buộc UI hiện tại.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu tại plan IN_REVIEW |
| A1 | 1 | Action | Người dùng | [1] Mở plan đang chờ xét duyệt |
| A2 | 2 | Action | Hệ thống | [2] Tải plan và kiểm tra quyền |
| D0 | 2 | Decision | Hệ thống | [2] Plan tải được và truy cập hợp lệ? |
| A3 | 3 | Action | Người dùng | [3] Rà soát nội dung và scope |
| D1 | 4 | Decision | Người dùng | [4] Chọn phê duyệt hay yêu cầu sửa? |
| A4 | 5-6 | Action | Người dùng | [5] Nhập ghi chú và xác nhận approve |
| A5 | 7 | Action | Hệ thống | [7] Kiểm quyền, policy, state, revision, scope |
| D2 | 7 | Decision | Hệ thống | [7] Điều kiện duyệt còn hợp lệ? |
| A6 | 8-9 | Action | Hệ thống | [8] Ghi APPROVED snapshot và trả kết quả |
| A7 | 4.1 | Action | Người dùng | [4.1] Nhập nhận xét yêu cầu chỉnh sửa |
| A8 | 4.1 | Action | Hệ thống | [4.1] Chuyển plan về DRAFT và ghi history |
| A9 | 5.1 | Action | Người dùng | [5.1] Hủy hộp thoại |
| A10 | 5.2 | Action | Người dùng | [5.2] Yêu cầu validate completeness |
| A11 | 5.2 | Action | Hệ thống | [5.2] Trả findings không đổi status |
| A12 | 7.3/7.4/8.1 | Action | Hệ thống | [7.3] Báo incomplete, stale scope hoặc lỗi |
| F1 | 9/4.1/5.2 | Final | Hệ thống | Kết thúc với kết quả đã hiển thị |
| F2 | 5.1/7.1-7.4 | Final | Hệ thống | Kết thúc không approve |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D0 | Đã yêu cầu tải plan |
| D0 | A3 | [Plan tồn tại, truy cập hợp lệ] |
| D0 | A12 | [Hết xác thực, thiếu quyền hoặc không tìm thấy] |
| A3 | D1 | Đã rà soát nội dung |
| D1 | A4 | [Phê duyệt] |
| D1 | A7 | [Yêu cầu chỉnh sửa] |
| D1 | A10 | [Kiểm tra completeness] |
| A4 | A9 | [Hủy] |
| A4 | A5 | Đã xác nhận |
| A5 | D2 | Validate xong |
| D2 | A6 | [Quyền, policy, state, revision và scope hợp lệ] |
| D2 | A12 | [Incomplete, snapshot stale, period/state/revision conflict] |
| A6 | F1 | APPROVED đã trả |
| A7 | A8 | Đã nhập note và xác nhận |
| A8 | F1 | DRAFT đã trả |
| A9 | F2 | Giữ IN_REVIEW |
| A10 | A11 | Đã yêu cầu validate |
| A11 | F1 | Findings hiển thị, status không đổi |
| A12 | F2 | Đã báo lỗi, không approve |

### 3c. Số liệu

N = 9 ô bước có nội dung; M = 12 Action; D = 3 Decision; E = 22 cạnh. Approval, revise, validate, cancel và lỗi có đích rõ.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa approve; revise, validate findings và cancel là operand khác/nhánh Activity.

### 4a. Lifeline trái sang phải

Reviewer → Giao diện Kế hoạch → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Reviewer | Giao diện Kế hoạch | [1] moPlan(plan_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Kế hoạch | Controller/API | [2] getTestPlan(plan_id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] getTestPlanRecord(plan_id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findPlan(plan_id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectPlanAndScope(plan_id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traPlanAndScope() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traPlan() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traPlanHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Kế hoạch | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Kế hoạch | Reviewer | [2] hienThiPlan() | trả về | alt [Tải thành công/lỗi] |
| 11 | 4-6 | Reviewer | Giao diện Kế hoạch | [4] xacNhanApprove(note) | đồng bộ | opt [Approve] |
| 12 | 7 | Giao diện Kế hoạch | Controller/API | [7] approveTestPlan(expected_revision, note) | đồng bộ | opt [Approve] |
| 13 | 7 | Controller/API | Service | [7] approveTestPlanRecord(payload) | đồng bộ | opt [Approve] |
| 14 | 7 | Service | Service | [7] checkPermissionIndependentReviewStateAndRevision() | tự gọi | opt [Approve] |
| 15 | 7 | Service | Repository | [7] validateScopeAndSnapshot(plan) | đồng bộ | alt [Scope hợp lệ/stale] |
| 16 | 7 | Repository | Database | [7] selectCurrentRequirementSuiteAndCaseVersions() | đồng bộ | alt [Scope hợp lệ/stale] |
| 17 | 7 | Database | Repository | [7] traScopeSnapshot() | trả về | alt [Scope hợp lệ/stale] |
| 18 | 7 | Repository | Service | [7] traScopeVaSnapshot() | trả về | alt [Scope hợp lệ/stale] |
| 19 | 8 | Service | Service | [8] computeApprovedSnapshotHash(plan) | tự gọi | opt [Scope hợp lệ] |
| 20 | 8 | Service | Repository | [8] optimisticPatchApprovedSnapshot(expected_revision) | đồng bộ | alt [Commit/conflict] |
| 21 | 8 | Repository | Database | [8] transactionSaveApprovalHistoryAndAudit() | đồng bộ | alt [Commit/lỗi] |
| 22 | 8 | Database | Repository | [8] traApprovedRevision() | trả về | alt [Commit/lỗi] |
| 23 | 8 | Repository | Service | [8] traPlanApproved() | trả về | alt [Commit/lỗi] |
| 24 | 9 | Service | Controller/API | [9] traApprovedPlanHoacLoi() | trả về | alt [Approve thành công/lỗi] |
| 25 | 9 | Controller/API | Giao diện Kế hoạch | [9] traResponse() | trả về | alt [Approve thành công/lỗi] |
| 26 | 9 | Giao diện Kế hoạch | Reviewer | [9] hienThiKetQuaApprove() | trả về | alt [Approve thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 26, fragment = 4: alt tải, opt approve, alt scope/commit, alt kết quả. Request/return theo tầng; stale snapshot trả lỗi thay vì approve.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC18 - Xét duyệt kế hoạch kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Reviewer/Hệ thống. Tách approve, request changes, validate findings và cancel.

ĐẶC TẢ
Mô tả: Xét plan IN_REVIEW, approve thành APPROVED hoặc trả DRAFT để sửa.
Tiền điều kiện: Đã xác thực; reviewer có `testplan.approve`/`testplan.review`; plan IN_REVIEW; independent review hợp lệ.
Hậu điều kiện: Approve lưu approved snapshot/hash, baseline hash, reviewer/time/note/history/audit; request changes chuyển DRAFT. Lỗi/hủy không báo approve.
Tác nhân chính: Reviewer/Admin có quyền. Tác nhân phụ: Không có.
Luồng chính: mở plan; hệ thống tải plan/scope/revision; reviewer rà soát; approve; kiểm completeness, quyền, independent review, state, revision, period, current scope; snapshot suite thay đổi chặn; transaction lưu APPROVED và history; trả kết quả.
Thay thế: yêu cầu sửa với note bắt buộc, chuyển DRAFT; validate findings không đổi state; cancel.
Ngoại lệ: missing permission/auth, invalid state, self-review denied, incomplete, scope changed, revision conflict, period unavailable, transaction error.

NODE
I Initial Người dùng Bắt đầu tại plan IN_REVIEW
A1 Action Người dùng [1] Mở plan đang chờ xét duyệt
A2 Action Hệ thống [2] Tải plan và kiểm tra quyền
D0 Decision Hệ thống [2] Plan tải được và truy cập hợp lệ?
A3 Action Người dùng [3] Rà soát nội dung và scope
D1 Decision Người dùng [4] Chọn phê duyệt, yêu cầu sửa hay validate?
A4 Action Người dùng [5] Nhập ghi chú và xác nhận approve
A5 Action Hệ thống [7] Kiểm quyền, policy, state, revision, scope
D2 Decision Hệ thống [7] Điều kiện duyệt còn hợp lệ?
A6 Action Hệ thống [8] Ghi APPROVED snapshot và trả kết quả
A7 Action Người dùng [4.1] Nhập nhận xét yêu cầu chỉnh sửa
A8 Action Hệ thống [4.1] Chuyển plan về DRAFT và ghi history
A9 Action Người dùng [5.1] Hủy hộp thoại
A10 Action Người dùng [5.2] Yêu cầu validate completeness
A11 Action Hệ thống [5.2] Trả findings không đổi status
A12 Action Hệ thống [7.3] Báo incomplete, stale scope hoặc lỗi
F1 Final Hệ thống Kết thúc với kết quả đã hiển thị
F2 Final Hệ thống Kết thúc không approve

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D0 [Đã yêu cầu tải]
D0 -> A3 [Plan tồn tại, truy cập hợp lệ]
D0 -> A12 [Hết xác thực/thiếu quyền/không tìm thấy]
A3 -> D1 [Đã rà soát]
D1 -> A4 [Phê duyệt]
D1 -> A7 [Yêu cầu chỉnh sửa]
D1 -> A10 [Validate]
A4 -> A9 [Hủy]
A4 -> A5 [Đã xác nhận]
A5 -> D2 [Validate xong]
D2 -> A6 [Quyền, policy, state, revision và scope hợp lệ]
D2 -> A12 [Incomplete, snapshot stale hoặc conflict]
A6 -> F1 [APPROVED đã trả]
A7 -> A8 [Note đã xác nhận]
A8 -> F1 [DRAFT đã trả]
A9 -> F2 [Giữ IN_REVIEW]
A10 -> A11 [Đã gọi validate]
A11 -> F1 [Findings hiển thị, status không đổi]
A12 -> F2 [Đã báo lỗi]

YÊU CẦU: Guards trên mọi cạnh rẽ; không tự thêm hành động sửa trực tiếp; validate không đổi state; final thành công/thất bại riêng.
KIỂM TRA: Action = 12, Decision = 3, cạnh = 22. Báo kết quả.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC18 - Xét duyệt kế hoạch kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Kịch bản chính là approve một plan, gọn theo tầng.

ĐẶC TẢ
Mô tả: Approve plan IN_REVIEW và lưu snapshot tại thời điểm phê duyệt.
Tiền điều kiện: Đã xác thực, quyền `testplan.approve`, plan IN_REVIEW, independent review hợp lệ.
Hậu điều kiện: APPROVED, approved snapshot/hash, baseline hash, approval history/audit. Lỗi scope/revision không duyệt.
Tác nhân chính: Reviewer có quyền. Tác nhân phụ: Không có.
Luồng chính: mở plan, tải nội dung/scope, xác nhận, kiểm permission/state/revision/scope, tính hash, transaction lưu approval, trả UI.
Thay thế: revise/validate/cancel nằm trong Activity.
Ngoại lệ: scope incomplete/stale, revision conflict, period unavailable, DB error, self-review denied.

LIFELINE: Reviewer; Giao diện Kế hoạch; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Reviewer -> Giao diện Kế hoạch | [1] moPlan(plan_id) | đồng bộ | chính
2 | 2 | Giao diện Kế hoạch -> Controller/API | [2] getTestPlan(plan_id) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] getTestPlanRecord(plan_id) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findPlan(plan_id) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectPlanAndScope(plan_id) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traPlanAndScope() | trả về | chính
7 | 2 | Repository -> Service | [2] traPlan() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traPlanHoacLoi() | trả về | chính
9 | 2 | Controller/API -> Giao diện Kế hoạch | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Kế hoạch -> Reviewer | [2] hienThiPlan() | trả về | alt [Tải thành công/lỗi]
11 | 4-6 | Reviewer -> Giao diện Kế hoạch | [4] xacNhanApprove(note) | đồng bộ | opt [Approve]
12 | 7 | Giao diện Kế hoạch -> Controller/API | [7] approveTestPlan(expected_revision, note) | đồng bộ | opt [Approve]
13 | 7 | Controller/API -> Service | [7] approveTestPlanRecord(payload) | đồng bộ | opt [Approve]
14 | 7 | Service -> Service | [7] checkPermissionIndependentReviewStateAndRevision() | tự gọi | opt [Approve]
15 | 7 | Service -> Repository | [7] validateScopeAndSnapshot(plan) | đồng bộ | alt [Scope hợp lệ/stale]
16 | 7 | Repository -> Database | [7] selectCurrentRequirementSuiteAndCaseVersions() | đồng bộ | alt [Scope hợp lệ/stale]
17 | 7 | Database -> Repository | [7] traScopeSnapshot() | trả về | alt [Scope hợp lệ/stale]
18 | 7 | Repository -> Service | [7] traScopeVaSnapshot() | trả về | alt [Scope hợp lệ/stale]
19 | 8 | Service -> Service | [8] computeApprovedSnapshotHash(plan) | tự gọi | opt [Scope hợp lệ]
20 | 8 | Service -> Repository | [8] optimisticPatchApprovedSnapshot(expected_revision) | đồng bộ | alt [Commit/conflict]
21 | 8 | Repository -> Database | [8] transactionSaveApprovalHistoryAndAudit() | đồng bộ | alt [Commit/lỗi]
22 | 8 | Database -> Repository | [8] traApprovedRevision() | trả về | alt [Commit/lỗi]
23 | 8 | Repository -> Service | [8] traPlanApproved() | trả về | alt [Commit/lỗi]
24 | 9 | Service -> Controller/API | [9] traApprovedPlanHoacLoi() | trả về | alt [Approve thành công/lỗi]
25 | 9 | Controller/API -> Giao diện Kế hoạch | [9] traResponse() | trả về | alt [Approve thành công/lỗi]
26 | 9 | Giao diện Kế hoạch -> Reviewer | [9] hienThiKetQuaApprove() | trả về | alt [Approve thành công/lỗi]

YÊU CẦU: Đủ 6 lifeline, 26 message, activation bar, self-call cho policy/hash; đúng thứ tự và tầng, request có return. Scope stale nằm trong alt và không approve.
KIỂM TRA: lifeline = 6, message = 26, fragment = 4. Báo kết quả.
```

## TỰ KIỂM TRA UC18

- [x] Phần 1 tách quyền review/approve và phát hiện scope snapshot.
- [x] Phần 2 có approve, request changes, validate, cancel và lỗi.
- [x] Activity: 12 Action, 3 Decision, 22 cạnh.
- [x] Sequence: 6 lifeline, 26 message, bốn fragment.
- [x] Prompt tự đủ, không gộp trả sửa với phê duyệt.

## Bảng theo dõi sau UC18

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC19 - Quản lý điều kiện kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tác nhân/tiền điều kiện | MƠ HỒ | “Tester” không phản ánh quyền cụ thể cho read/create/update/archive. | Ghi vai trò nghiệp vụ và quyền theo thao tác. |
| 1-2 | THIẾU | Danh sách chưa có bộ lọc ngoài trạng thái; chưa nêu tìm theo key/title/coverage, risk/testability. | Bổ sung tham số lọc và phân trang API. |
| 4-8 | THIẾU | Không nêu basis refs được resolve/snapshot, tự sinh key, revision và duplicate key conflict. | Nêu DRAFT, key tự sinh nếu bỏ trống, basis snapshots và lỗi key trùng. |
| 3.3 | SAI | Bảng chỉ cho sửa DRAFT nhưng chưa nêu optimistic revision; status khác DRAFT phải immutable. | Bổ sung expected revision và từ chối sửa trạng thái khác. |
| 3.4 | THIẾU | Clone từ APPROVED chưa nói dữ liệu approval được bỏ và nguồn liên kết. | Nêu tạo bản ghi mới DRAFT revision 1, source_condition_id, reset approval history/reviewed_by. |
| 3.5 | THIẾU | Archive chỉ nêu chuyển trạng thái, thiếu quyền, ghi chú, revision và điều kiện source state. | Nêu chỉ DRAFT/APPROVED, lưu reason/actor/time, giữ dữ liệu; không hard-delete. |
| Hủy | MƠ HỒ | Nhánh 6.1 chỉ nói hủy form tạo; không áp dụng update/archive. | Phân biệt hủy trước gửi của từng hộp thoại, không lưu thay đổi. |
| Ngoại lệ | THIẾU | Thiếu basis không hợp lệ, validation schema, missing permission, revision conflict, state invalid, lỗi DB. | Bổ sung nhánh kiểm tra phù hợp theo API. |

Đã kiểm: **5 điểm rẽ, 7 nhánh chức năng, 8 nhóm lỗi** gồm permission/auth, dữ liệu thiếu/sai, basis không hợp lệ, key trùng, trạng thái immutable, revision conflict, không tìm thấy, archive state conflict và lỗi CSDL/hủy. UC quản lý có list/search/filter/detail/create/update/clone/archive. Không có xóa cứng hay khôi phục archive trong API này.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền tra cứu, tạo và cập nhật điều kiện kiểm thử; tạo draft mới từ bản APPROVED và lưu trữ điều kiện đủ điều kiện.

**Tiền điều kiện:** Đã xác thực; dự án tồn tại; có quyền `testcondition.read/create/update/archive`; basis refs thuộc project và có thể resolve. Sửa trực tiếp chỉ khi trạng thái DRAFT.

**Hậu điều kiện:** Tạo mới/clone ở DRAFT; cập nhật tăng revision; clone giữ nguồn tham chiếu nhưng reset approval metadata; archive chuyển ARCHIVED, giữ nội dung. Lỗi/hủy không được báo lưu thành công.

**Tác nhân chính:** Tester/người được cấp quyền thao tác tương ứng.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính: Tạo điều kiện DRAFT**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang Điều kiện kiểm thử. | |
| 2 | | Kiểm tra `testcondition.read`, tải danh sách theo q/status/risk/testability_status và phân trang. |
| 3 | Chọn Tạo điều kiện. | |
| 4 | | Hiển thị form title, description, basis refs, level/type/risk/testability và nội dung liên quan. |
| 5 | Nhập dữ liệu và xác nhận lưu. | |
| 6 | | Kiểm tra `testcondition.create`, schema và resolve basis refs thành snapshot. |
| 7 | | Sinh condition_key nếu chưa nhập, tạo record DRAFT revision 1, khởi tạo approval history. |
| 8 | | Ghi audit, trả record và tải lại danh sách. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | Nhập từ khóa/chọn status, risk hoặc testability status. | Tải danh sách phù hợp; quay lại bước 2. |
| 2.2 | Chọn điều kiện cần xem. | Kiểm tra read permission, hiển thị nội dung, basis/status; kết thúc nhánh. |
| 3.1 | Chọn condition DRAFT, sửa và lưu. | Kiểm tra `testcondition.update`, status DRAFT, expected revision, validate nội dung/basis snapshot; update và audit. |
| 3.2 | Chọn condition APPROVED, tạo bản nháp mới. | Kiểm tra `testcondition.create`; copy approved snapshot, tạo key mới/DRAFT revision 1, liên kết source và reset approval fields. |
| 3.3 | Chọn condition DRAFT/APPROVED, lưu trữ và xác nhận ghi chú. | Kiểm tra `testcondition.archive`, state và revision; chuyển ARCHIVED, ghi actor/time/reason/audit. |
| 5.1 | Hủy biểu mẫu trước gửi. | Đóng form, không tạo hoặc cập nhật record. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1.1 | | Hết xác thực/thiếu read permission hoặc condition không tồn tại: từ chối tải. |
| 6.1 | | Title/field sai hoặc basis refs không hợp lệ: trả validation, giữ form. |
| 7.1 | | Condition key trùng: trả `TEST_CONDITION_KEY_EXISTS`, không tạo record. |
| 3.1.1 | | Condition không còn DRAFT hoặc revision conflict: từ chối update, yêu cầu tải lại. |
| 3.2.1 | | Nguồn không còn APPROVED: từ chối clone. |
| 3.3.1 | | Source state không thuộc DRAFT/APPROVED hoặc expected revision conflict: không archive. |
| Mọi bước | | Lỗi CSDL/API: không thông báo thành công; audit/update phải theo kết quả thực sự. |

**Giả định / Câu hỏi cần làm rõ:** Tên trường trên biểu mẫu cần thống nhất với schema `TestConditionCreate`; bảng gốc gọi “cơ sở kiểm thử”, trong API có thể là basis refs/snapshots. Không có endpoint restore archive được phát hiện trong UC19.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Người dùng | Bắt đầu tại danh sách điều kiện |
| A1 | 1 | Action | Người dùng | [1] Mở trang Điều kiện kiểm thử |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền và bộ lọc |
| D1 | 3 | Decision | Người dùng | [3] Chọn tìm, xem, tạo, sửa, clone hay archive? |
| A3 | 2.1 | Action | Người dùng | [2.1] Tìm hoặc lọc điều kiện |
| A4 | 2.2 | Action | Người dùng | [2.2] Xem chi tiết điều kiện |
| A5 | 5 | Action | Người dùng | [5] Nhập dữ liệu tạo DRAFT |
| A6 | 3.1 | Action | Người dùng | [3.1] Sửa điều kiện DRAFT |
| A7 | 3.2 | Action | Người dùng | [3.2] Tạo draft từ APPROVED |
| A8 | 3.3 | Action | Người dùng | [3.3] Xác nhận archive |
| A9 | 6-7 | Action | Hệ thống | [6] Kiểm quyền, basis, status và revision |
| D2 | 6-7 | Decision | Hệ thống | [6] Dữ liệu hợp lệ và thao tác được phép? |
| A10 | 7-8 | Action | Hệ thống | [7] Ghi condition, audit và trả kết quả |
| A11 | 6.1/7.1 | Action | Hệ thống | [6.1] Báo validation, key trùng hoặc conflict |
| A12 | 5.1 | Action | Người dùng | [5.1] Hủy form |
| F1 | 8/2.2/3.2/3.3 | Final | Hệ thống | Kết thúc với kết quả thao tác |
| F2 | 5.1/6.1 | Final | Hệ thống | Kết thúc không lưu thành công |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách tải xong |
| D1 | A3 | [Tìm/lọc] |
| A3 | A2 | [Tải lại danh sách] |
| D1 | A4 | [Xem chi tiết] |
| A4 | F1 | Đã hiển thị |
| D1 | A5 | [Tạo DRAFT] |
| D1 | A6 | [Sửa DRAFT] |
| D1 | A7 | [Clone APPROVED] |
| D1 | A8 | [Archive DRAFT/APPROVED] |
| A5 | A9 | Đã gửi form |
| A6 | A9 | Đã gửi patch/revision |
| A7 | A9 | Đã yêu cầu clone |
| A8 | A9 | Đã xác nhận archive |
| A5 | A12 | [Hủy trước gửi] |
| A9 | D2 | Kiểm tra xong |
| D2 | A10 | [Permission, schema, basis, state, revision hợp lệ] |
| D2 | A11 | [Validation/key/state/revision lỗi] |
| A10 | F1 | Kết quả đã trả |
| A11 | F2 | Đã báo lỗi |
| A12 | F2 | Không gửi thay đổi |

### 3c. Số liệu

N = 8 ô bước có nội dung; M = 12 Action; D = 2 Decision; E = 22 cạnh. Mỗi thao tác quản lý có nhánh riêng, archive không bị mô tả như delete.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa tạo condition DRAFT. Các thao tác update/clone/archive thuộc Activity.

### 4a. Lifeline trái sang phải

Tester → Giao diện Điều kiện → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Điều kiện | [1] moTrangDieuKien(project_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Điều kiện | Controller/API | [2] listConditions(project_id, filters, page) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listConditions(filters) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findConditions(project_id, filters) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectConditions(filters) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traConditions() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traPage() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traResults() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Điều kiện | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Điều kiện | Tester | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Tester | Giao diện Điều kiện | [3] nhapConditionVaLuu(payload) | đồng bộ | opt [Tạo mới] |
| 12 | 6 | Giao diện Điều kiện | Controller/API | [6] createTestCondition(project_id, payload) | đồng bộ | opt [Tạo mới] |
| 13 | 6 | Controller/API | Service | [6] createCondition(project_id, payload) | đồng bộ | opt [Tạo mới] |
| 14 | 6 | Service | Service | [6] resolveBasisAndValidateSchema() | tự gọi | alt [Hợp lệ/lỗi] |
| 15 | 7 | Service | Repository | [7] createCondition(condition_DRAFT) | đồng bộ | alt [Tạo thành công/key trùng] |
| 16 | 7 | Repository | Database | [7] insertConditionAndAudit(condition) | đồng bộ | alt [Ghi thành công/lỗi] |
| 17 | 7 | Database | Repository | [7] traConditionRevision() | trả về | alt [Ghi thành công/lỗi] |
| 18 | 7 | Repository | Service | [7] traCondition() | trả về | alt [Ghi thành công/lỗi] |
| 19 | 8 | Service | Controller/API | [8] traConditionHoacLoi() | trả về | alt [Thành công/lỗi] |
| 20 | 8 | Controller/API | Giao diện Điều kiện | [8] traResponse() | trả về | alt [Thành công/lỗi] |
| 21 | 8 | Giao diện Điều kiện | Tester | [8] hienThiConditionVaTaiDanhSach() | trả về | alt [Thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 21, fragment = 3: alt tải, opt tạo, alt validation/key/DB. Tạo thành công trả DRAFT; không gửi sang review trong UC này.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC19 - Quản lý điều kiện kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Tester/Hệ thống. Bố cục rõ các thao tác quản lý riêng.

ĐẶC TẢ
Mô tả: Tìm/lọc/xem, tạo DRAFT, sửa DRAFT, clone từ APPROVED và archive điều kiện.
Tiền điều kiện: Đã xác thực; quyền `testcondition.read/create/update/archive`; basis refs hợp lệ; edit chỉ DRAFT.
Hậu điều kiện: create/clone DRAFT; update tăng revision; archive chuyển ARCHIVED và giữ nội dung; lỗi/hủy không báo thành công.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Không có.
Luồng: mở danh sách; chọn search/filter/read/create/update/clone/archive; validate permission/schema/basis/status/revision; ghi audit và trả kết quả.
Ngoại lệ: hết xác thực/permission, field/basis invalid, key trùng, record missing, state không cho phép, revision conflict, DB error, cancel.

NODE
I Initial Tester Bắt đầu tại danh sách điều kiện
A1 Action Tester [1] Mở trang Điều kiện kiểm thử
A2 Action Hệ thống [2] Tải danh sách theo quyền và bộ lọc
D1 Decision Tester [3] Chọn tìm, xem, tạo, sửa, clone hay archive?
A3 Action Tester [2.1] Tìm hoặc lọc điều kiện
A4 Action Tester [2.2] Xem chi tiết điều kiện
A5 Action Tester [5] Nhập dữ liệu tạo DRAFT
A6 Action Tester [3.1] Sửa điều kiện DRAFT
A7 Action Tester [3.2] Tạo draft từ APPROVED
A8 Action Tester [3.3] Xác nhận archive
A9 Action Hệ thống [6] Kiểm quyền, basis, status và revision
D2 Decision Hệ thống [6] Dữ liệu hợp lệ và thao tác được phép?
A10 Action Hệ thống [7] Ghi condition, audit và trả kết quả
A11 Action Hệ thống [6.1] Báo validation, key trùng hoặc conflict
A12 Action Tester [5.1] Hủy form
F1 Final Hệ thống Kết thúc với kết quả thao tác
F2 Final Hệ thống Kết thúc không lưu thành công

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Danh sách tải xong]
D1 -> A3 [Tìm/lọc]
A3 -> A2 [Tải lại danh sách]
D1 -> A4 [Xem chi tiết]
A4 -> F1 [Đã hiển thị]
D1 -> A5 [Tạo DRAFT]
D1 -> A6 [Sửa DRAFT]
D1 -> A7 [Clone APPROVED]
D1 -> A8 [Archive DRAFT/APPROVED]
A5 -> A9 [Đã gửi form]
A6 -> A9 [Đã gửi patch/revision]
A7 -> A9 [Đã yêu cầu clone]
A8 -> A9 [Đã xác nhận archive]
A5 -> A12 [Hủy]
A9 -> D2 [Kiểm tra xong]
D2 -> A10 [Permission/schema/basis/state/revision hợp lệ]
D2 -> A11 [Validation/key/state/revision lỗi]
A10 -> F1 [Kết quả đã trả]
A11 -> F2 [Đã báo lỗi]
A12 -> F2 [Không gửi thay đổi]

YÊU CẦU: Mọi nhánh có guard, không node treo; archive không phải xóa; không thêm restore.
KIỂM TRA: Action = 12, Decision = 2, cạnh = 22. Báo kết quả cuối.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC19 - Quản lý điều kiện kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Chỉ minh họa tạo condition DRAFT.

ĐẶC TẢ
Mô tả: Tạo condition từ thông tin và basis refs hợp lệ.
Tiền điều kiện: Đã xác thực, project tồn tại, quyền `testcondition.create`, basis refs thuộc project.
Hậu điều kiện: DRAFT revision 1 được lưu, audit; duplicate key/validation/DB error không báo thành công.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Không có.
Luồng chính: load list, nhập form, API kiểm tra schema/basis, sinh key, insert DRAFT, trả dữ liệu.
Thay thế: search/filter/clone/update/archive thuộc Activity.
Ngoại lệ: missing permission, invalid basis/schema, duplicate key, DB error.

LIFELINE: Tester; Giao diện Điều kiện; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Tester -> Giao diện Điều kiện | [1] moTrangDieuKien(project_id) | đồng bộ | chính
2 | 2 | Giao diện Điều kiện -> Controller/API | [2] listConditions(project_id, filters, page) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] listConditions(filters) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findConditions(project_id, filters) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectConditions(filters) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traConditions() | trả về | chính
7 | 2 | Repository -> Service | [2] traPage() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traResults() | trả về | chính
9 | 2 | Controller/API -> Giao diện Điều kiện | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Điều kiện -> Tester | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi]
11 | 3-5 | Tester -> Giao diện Điều kiện | [3] nhapConditionVaLuu(payload) | đồng bộ | opt [Tạo mới]
12 | 6 | Giao diện Điều kiện -> Controller/API | [6] createTestCondition(project_id, payload) | đồng bộ | opt [Tạo mới]
13 | 6 | Controller/API -> Service | [6] createCondition(project_id, payload) | đồng bộ | opt [Tạo mới]
14 | 6 | Service -> Service | [6] resolveBasisAndValidateSchema() | tự gọi | alt [Hợp lệ/lỗi]
15 | 7 | Service -> Repository | [7] createCondition(condition_DRAFT) | đồng bộ | alt [Tạo thành công/key trùng]
16 | 7 | Repository -> Database | [7] insertConditionAndAudit(condition) | đồng bộ | alt [Ghi thành công/lỗi]
17 | 7 | Database -> Repository | [7] traConditionRevision() | trả về | alt [Ghi thành công/lỗi]
18 | 7 | Repository -> Service | [7] traCondition() | trả về | alt [Ghi thành công/lỗi]
19 | 8 | Service -> Controller/API | [8] traConditionHoacLoi() | trả về | alt [Thành công/lỗi]
20 | 8 | Controller/API -> Giao diện Điều kiện | [8] traResponse() | trả về | alt [Thành công/lỗi]
21 | 8 | Giao diện Điều kiện -> Tester | [8] hienThiConditionVaTaiDanhSach() | trả về | alt [Thành công/lỗi]

YÊU CẦU: 6 lifeline, 21 message, activation bar, self-call validation, no layer skipping, sync calls have returns, alt/opt guards included.
KIỂM TRA: lifeline = 6, message = 21, fragment = 3. Báo kết quả đối chiếu.
```

## TỰ KIỂM TRA UC19

- [x] Phần 1 có CRUD/clone/archive, quyền, basis, key và revision.
- [x] Phần 2 nêu rõ không có restore/hard delete trong luồng đã xác nhận.
- [x] Activity: 12 Action, 2 Decision, 22 cạnh.
- [x] Sequence: 6 lifeline, 21 message, ba fragment.
- [x] Prompt tự đủ và giới hạn sequence vào tạo mới.

## Bảng theo dõi sau UC19

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC20 - Xét duyệt điều kiện kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tiền điều kiện | THIẾU | Chỉ nói condition đã tạo; submission yêu cầu DRAFT, approve yêu cầu IN_REVIEW và quyền riêng. | Ghi trạng thái, permission theo từng hành động và independent review. |
| 1-6 | THIẾU | Submit không kiểm đủ schema, revision, findings/ghi chú. | Nêu validate condition, expected revision, transition DRAFT→IN_REVIEW và audit. |
| 7-13 | MƠ HỒ | “Admin rà soát” gộp review note, approve và request changes, dù mỗi thao tác có endpoint/state khác. | Tách ghi nhận reviewer giữ IN_REVIEW, approve sang APPROVED, request changes về DRAFT. |
| 12 | THIẾU | “Vấn đề chưa giải quyết” không rõ tiêu chí chặn approve. | API chặn nếu có analysis finding trạng thái OPEN; lưu ý code kiểm list này, không suy diễn mọi warning đều chặn. |
| 9.2 | MÂU THUẪN | Phân công tác nhân phụ nói thành viên dự án, nhưng điều kiện membership và quyền chưa được ghi. | Chỉ thành viên ACTIVE mới nhận assignment; quyền assign riêng. |
| 9.3 | THIẾU | Xử lý finding gộp `resolve_finding` của condition với AnalysisFinding assignment/workflow. | Tách rõ finding gắn condition (DRAFT/IN_REVIEW) với issue/finding độc lập có owner; không khẳng định hai record là cùng một entity. |
| 9.3.5.1 | MƠ HỒ | Chấp nhận rủi ro chưa nêu trạng thái cuối. | Ghi API nhận status resolution, ref/note; trạng thái cụ thể theo payload enum, không tự gọi “đã xác minh”. |
| 9.4 | THIẾU | Xác minh chỉ hợp lệ trên trạng thái RESOLVED, cần revision và quyền verifier. | Bổ sung kiểm tra state/revision và chuyển RESOLVED→VERIFIED. |
| Ngoại lệ | THIẾU | Thiếu stale revision, finding đã xử lý, condition immutable/ARCHIVED, member không hợp lệ, open finding, incomplete condition, self-review và lỗi DB. | Bổ sung nhánh có căn cứ; không duyệt nếu còn OPEN findings. |

Đã kiểm: **5 điểm rẽ, 7 nhánh kết quả, 10 nhóm lỗi** gồm permission/auth, condition thiếu/không đủ schema, state/revision conflict, self-review, OPEN findings, finding không tồn tại/đã xử lý, assignee không ACTIVE, invalid resolution, archived/immutable condition, lỗi CSDL và hủy. UC20 không phải CRUD; thao tác quản lý condition thuộc UC19.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Gửi condition DRAFT đi rà soát, ghi nhận kết quả reviewer, approve condition hợp lệ, yêu cầu sửa; xử lý/assign/verify findings liên quan theo quyền.

**Tiền điều kiện:** Đã xác thực; condition tồn tại trong project. Submit cần DRAFT và `testcondition.review`; review/assign/resolve/verify có quyền tương ứng; approve cần IN_REVIEW, `testcondition.approve` và independent review. Assignee phải là thành viên ACTIVE.

**Hậu điều kiện:** Submit: IN_REVIEW, submitted_by/time/note. Review: giữ IN_REVIEW, append reviewer và note. Approve: APPROVED, approved snapshot/hash/history; không còn OPEN testability findings. Request changes: ở UC20 không có endpoint riêng được thấy trong route; bảng gốc không mô tả thao tác này cho condition, nên không tự đặc tả. Finding resolve/verify thay đổi finding status theo endpoint, không đồng nghĩa condition được duyệt.

**Tác nhân chính:** Tester/reviewer/admin theo quyền cụ thể.

**Tác nhân phụ:** Thành viên ACTIVE được phân công xử lý finding.

**Luồng sự kiện chính: Submit và approve condition**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn condition DRAFT. | |
| 2 | | Kiểm tra quyền, tải nội dung, basis snapshot và revision. |
| 3 | Chọn Gửi rà soát, nhập note và xác nhận. | |
| 4 | | Kiểm tra schema/condition completeness và expected revision. |
| 5 | | Chuyển DRAFT→IN_REVIEW, lưu submitter/time/note và audit. |
| 6 | Reviewer mở condition IN_REVIEW. | |
| 7 | | Tải nội dung/basis/findings và kiểm tra quyền. |
| 8 | Reviewer chọn Phê duyệt và nhập note. | |
| 9 | | Kiểm tra independent review, condition schema, expected revision và findings OPEN. |
| 10 | | Nếu đủ điều kiện, chuyển APPROVED, lưu snapshot/hash/approval history và audit. |
| 11 | | Trả status và làm mới giao diện. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 8.1 | Chọn Ghi nhận rà soát và nhập note. | Lưu reviewer/note, giữ IN_REVIEW, audit; kết thúc nhánh. |
| 9.1 | Mở finding, chọn thành viên để giao việc. | Kiểm tra quyền assign và thành viên ACTIVE; cập nhật owner/status IN_PROGRESS/revision. |
| 9.2 | Assignee xử lý finding, nhập resolution/ref/note và xác nhận. | Kiểm tra quyền/state/revision; chuyển OPEN/IN_PROGRESS sang trạng thái được gửi trong payload, ghi resolver/time. |
| 9.3 | Reviewer xác minh finding RESOLVED. | Kiểm tra quyền/state/revision; chuyển RESOLVED→VERIFIED, ghi verifier/time. |
| 3.1 | Hủy hộp thoại submit/approve. | Đóng hộp thoại, không gọi transition API. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Hết xác thực, thiếu permission hoặc condition không tìm thấy: từ chối. |
| 4.1 | | Condition thiếu field/schema bắt buộc: trả `TEST_CONDITION_INCOMPLETE`, giữ DRAFT. |
| 5.1 | | Revision/state đổi đồng thời: trả transition conflict, không ghi trạng thái cũ. |
| 9.1 | | Reviewer không độc lập theo policy hoặc condition không còn IN_REVIEW: từ chối approve. |
| 9.2 | | Có finding status OPEN: trả `OPEN_TESTABILITY_FINDINGS`, không chuyển APPROVED. |
| 9.3 | | Finding không tồn tại/đã resolved, archived/immutable condition hoặc revision stale: từ chối resolve. |
| 9.1.1 | | Thành viên được chọn không ACTIVE: từ chối assignment. |
| 9.3.1 | | Finding không ở RESOLVED khi verify, hoặc đã đổi revision: từ chối xác minh. |
| Mọi bước | | Lỗi CSDL/API: không xác nhận transition chưa commit. |

**Giả định / Câu hỏi cần làm rõ:** Bảng gốc có luồng “yêu cầu chỉnh sửa condition” gián tiếp qua việc xử lý finding, nhưng route/service được kiểm tra không có transition condition IN_REVIEW→DRAFT theo request changes. Vì vậy không mô tả đó là endpoint đã triển khai. Quy ước status cho risk acceptance phụ thuộc payload schema và cần rà thêm nếu cần mô tả enum cụ thể.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Tester | Bắt đầu với condition DRAFT |
| A1 | 1 | Action | Tester | [1] Chọn condition DRAFT |
| A2 | 2 | Action | Hệ thống | [2] Tải condition và basis snapshot |
| A3 | 3-5 | Action | Tester | [3] Gửi condition để rà soát |
| A4 | 4-5 | Action | Hệ thống | [4] Validate và chuyển IN_REVIEW |
| A5 | 6-7 | Action | Reviewer | [6] Mở và rà soát condition |
| D1 | 8 | Decision | Reviewer | [8] Chọn ghi nhận, approve hay xử lý finding? |
| A6 | 8.1 | Action | Reviewer | [8.1] Ghi nhận review note |
| A7 | 9-10 | Action | Hệ thống | [9] Kiểm findings và approve snapshot |
| D2 | 9 | Decision | Hệ thống | [9] Schema hợp lệ, không còn OPEN finding? |
| A8 | 11 | Action | Hệ thống | [10] Trả status APPROVED |
| A9 | 9.1-9.3 | Action | Thành viên/Reviewer | [9.1] Assign, resolve hoặc verify finding |
| A10 | 9.1-9.3 | Action | Hệ thống | [9.1] Cập nhật finding theo quyền/state/revision |
| A11 | 3.1 | Action | Người dùng | [3.1] Hủy transition |
| A12 | 4.1/9.2 | Action | Hệ thống | [4.1] Báo validation, open finding hoặc conflict |
| F1 | 5/8.1/11/9.3 | Final | Hệ thống | Kết thúc với kết quả đã ghi nhận |
| F2 | 3.1/4.1/9.2 | Final | Hệ thống | Kết thúc không approve |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | A3 | Condition tải được |
| A3 | A4 | Người dùng xác nhận submit |
| A3 | A11 | [Hủy] |
| A4 | F1 | Condition chuyển IN_REVIEW |
| A4 | A12 | [Incomplete/state/revision error] |
| A12 | F2 | Không submit được |
| A5 | D1 | Reviewer tải xong |
| D1 | A6 | [Ghi nhận review] |
| A6 | F1 | Đã lưu, vẫn IN_REVIEW |
| D1 | A7 | [Approve] |
| A7 | D2 | Validation xong |
| D2 | A8 | [Schema hợp lệ và không OPEN finding] |
| D2 | A12 | [Incomplete hoặc có OPEN finding] |
| A8 | F1 | Đã trả APPROVED |
| D1 | A9 | [Quản lý finding] |
| A9 | A10 | Đã gửi assign/resolve/verify |
| A10 | F1 | Finding transition đã trả |
| A7 | A11 | [Hủy approve trước API] |
| A11 | F2 | Không gọi transition |

### 3c. Số liệu

N = 9 ô nội dung; M = 12 Action; D = 2 Decision; E = 21 cạnh. Approval chỉ đi qua nhánh không còn OPEN findings; xử lý finding không tự đồng nghĩa approve.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa submit condition DRAFT; xét duyệt/finding workflow được mô tả trong Activity để không dồn nhiều actor và state machine vào một hình.

### 4a. Lifeline trái sang phải

Tester → Giao diện Điều kiện → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Điều kiện | [1] chonCondition(condition_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Điều kiện | Controller/API | [2] getTestCondition(condition_id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] getConditionForUser(condition_id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findCondition(condition_id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectCondition(condition_id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traCondition() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traConditionHoac404() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traCondition() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Điều kiện | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Điều kiện | Tester | [2] hienThiCondition() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Tester | Giao diện Điều kiện | [3] xacNhanGuiRaSoat(note) | đồng bộ | opt [Submit] |
| 12 | 4 | Giao diện Điều kiện | Controller/API | [4] submitTestCondition(expected_revision, note) | đồng bộ | opt [Submit] |
| 13 | 4 | Controller/API | Service | [4] transitionCondition(action=submit) | đồng bộ | opt [Submit] |
| 14 | 4 | Service | Service | [4] validateConditionSchemaAndState() | tự gọi | alt [Hợp lệ/lỗi] |
| 15 | 5 | Service | Repository | [5] updateStatusAndSubmitMetadata(IN_REVIEW) | đồng bộ | alt [Commit/conflict] |
| 16 | 5 | Repository | Database | [5] updateConditionAndRevision(expected_revision) | đồng bộ | alt [Commit/conflict] |
| 17 | 5 | Database | Repository | [5] traUpdatedCondition() | trả về | alt [Commit/conflict] |
| 18 | 5 | Repository | Service | [5] traCondition() | trả về | alt [Commit/conflict] |
| 19 | 5 | Service | Controller/API | [5] traStatusVaAudit() | trả về | alt [Thành công/lỗi] |
| 20 | 5 | Controller/API | Giao diện Điều kiện | [5] traResponse() | trả về | alt [Thành công/lỗi] |
| 21 | 5 | Giao diện Điều kiện | Tester | [5] hienThiIN_REVIEW() | trả về | alt [Thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 21, fragment = 3: alt tải, opt submit, alt validate/commit. Ghi nhận/approve/resolve không nằm trong sequence minh họa.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC20 - Xét duyệt điều kiện kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Người gửi, Reviewer và Hệ thống. Bố cục luận văn, tách submit, review, approve và finding workflow.

ĐẶC TẢ
Mô tả: Submit condition DRAFT, reviewer ghi nhận/approve; findings có thể được assign, resolve, verify.
Tiền điều kiện: Đã xác thực; quyền theo hành động; submit DRAFT; approve IN_REVIEW, independent reviewer; assignee ACTIVE.
Hậu điều kiện: Submit IN_REVIEW; review giữ IN_REVIEW; approve APPROVED với snapshot/hash chỉ khi schema hợp lệ và không còn OPEN testability finding. Finding transition tách biệt.
Tác nhân chính: Tester/reviewer/admin theo permission. Tác nhân phụ: thành viên ACTIVE được assign.
Luồng: tải condition; submit; reviewer chọn ghi nhận, approve hoặc finding management. Approve kiểm schema/finding; finding management assign/resolve/verify theo state.
Ngoại lệ: incomplete, missing rights, self-review, open finding, stale revision/state, assignee invalid, archived/immutable, finding missing/already resolved, DB error, cancel.

NODE
I Initial Tester Bắt đầu với condition DRAFT
A1 Action Tester [1] Chọn condition DRAFT
A2 Action Hệ thống [2] Tải condition và basis snapshot
A3 Action Tester [3] Gửi condition để rà soát
A4 Action Hệ thống [4] Validate và chuyển IN_REVIEW
A5 Action Reviewer [6] Mở và rà soát condition
D1 Decision Reviewer [8] Chọn ghi nhận, approve hay xử lý finding?
A6 Action Reviewer [8.1] Ghi nhận review note
A7 Action Hệ thống [9] Kiểm findings và approve snapshot
D2 Decision Hệ thống [9] Schema hợp lệ, không còn OPEN finding?
A8 Action Hệ thống [10] Trả status APPROVED
A9 Action Thành viên/Reviewer [9.1] Assign, resolve hoặc verify finding
A10 Action Hệ thống [9.1] Cập nhật finding theo quyền/state/revision
A11 Action Người dùng [3.1] Hủy transition
A12 Action Hệ thống [4.1] Báo validation, open finding hoặc conflict
F1 Final Hệ thống Kết thúc với kết quả đã ghi nhận
F2 Final Hệ thống Kết thúc không approve

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> A3 [Condition tải được]
A3 -> A4 [Xác nhận submit]
A3 -> A11 [Hủy]
A4 -> F1 [Chuyển IN_REVIEW]
A4 -> A12 [Incomplete/state/revision error]
A12 -> F2 [Không submit được]
A5 -> D1 [Reviewer tải xong]
D1 -> A6 [Ghi nhận review]
A6 -> F1 [Đã lưu, vẫn IN_REVIEW]
D1 -> A7 [Approve]
A7 -> D2 [Validation xong]
D2 -> A8 [Schema hợp lệ và không OPEN finding]
D2 -> A12 [Incomplete hoặc OPEN finding]
A8 -> F1 [Đã trả APPROVED]
D1 -> A9 [Quản lý finding]
A9 -> A10 [Đã gửi assign/resolve/verify]
A10 -> F1 [Finding transition đã trả]
A7 -> A11 [Hủy approve trước API]
A11 -> F2 [Không gọi transition]

YÊU CẦU: Mỗi nhánh Decision có guard; finding resolve không đồng nghĩa approve; không thêm endpoint request-change cho condition nếu chưa có. Final thành công/thất bại riêng.
KIỂM TRA: Action = 12, Decision = 2, cạnh = 21. Báo đối chiếu cuối.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC20 - Xét duyệt điều kiện kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Sequence chỉ minh họa gửi condition DRAFT sang IN_REVIEW.

ĐẶC TẢ
Mô tả: Người có quyền gửi condition DRAFT để reviewer rà soát.
Tiền điều kiện: Đã xác thực, quyền `testcondition.review`, condition DRAFT và revision hiện tại.
Hậu điều kiện: IN_REVIEW, lưu submitter/time/note và audit. Validation/conflict không chuyển state.
Tác nhân chính: Tester/người submit. Tác nhân phụ: Không có trong kịch bản này.
Luồng: đọc condition, xác nhận submit, kiểm schema/state/revision, cập nhật IN_REVIEW, trả kết quả.
Thay thế: approve/review/findings được thể hiện ở Activity, không nằm trong sequence này.
Ngoại lệ: missing permission, incomplete schema, revision/state conflict, DB error.

LIFELINE: Tester; Giao diện Điều kiện; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Tester -> Giao diện Điều kiện | [1] chonCondition(condition_id) | đồng bộ | chính
2 | 2 | Giao diện Điều kiện -> Controller/API | [2] getTestCondition(condition_id) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] getConditionForUser(condition_id) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findCondition(condition_id) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectCondition(condition_id) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traCondition() | trả về | chính
7 | 2 | Repository -> Service | [2] traConditionHoac404() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traCondition() | trả về | chính
9 | 2 | Controller/API -> Giao diện Điều kiện | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Điều kiện -> Tester | [2] hienThiCondition() | trả về | alt [Tải thành công/lỗi]
11 | 3-5 | Tester -> Giao diện Điều kiện | [3] xacNhanGuiRaSoat(note) | đồng bộ | opt [Submit]
12 | 4 | Giao diện Điều kiện -> Controller/API | [4] submitTestCondition(expected_revision, note) | đồng bộ | opt [Submit]
13 | 4 | Controller/API -> Service | [4] transitionCondition(action=submit) | đồng bộ | opt [Submit]
14 | 4 | Service -> Service | [4] validateConditionSchemaAndState() | tự gọi | alt [Hợp lệ/lỗi]
15 | 5 | Service -> Repository | [5] updateStatusAndSubmitMetadata(IN_REVIEW) | đồng bộ | alt [Commit/conflict]
16 | 5 | Repository -> Database | [5] updateConditionAndRevision(expected_revision) | đồng bộ | alt [Commit/conflict]
17 | 5 | Database -> Repository | [5] traUpdatedCondition() | trả về | alt [Commit/conflict]
18 | 5 | Repository -> Service | [5] traCondition() | trả về | alt [Commit/conflict]
19 | 5 | Service -> Controller/API | [5] traStatusVaAudit() | trả về | alt [Thành công/lỗi]
20 | 5 | Controller/API -> Giao diện Điều kiện | [5] traResponse() | trả về | alt [Thành công/lỗi]
21 | 5 | Giao diện Điều kiện -> Tester | [5] hienThiIN_REVIEW() | trả về | alt [Thành công/lỗi]

YÊU CẦU: Đủ 6 lifeline, 21 message, activation bar, self-call validate; không gọi nhảy lớp. alt/opt có guard, mọi request sync có return.
KIỂM TRA: lifeline = 6, message = 21, fragment = 3. Báo đối chiếu cuối.
```

## TỰ KIỂM TRA UC20

- [x] Phần 1 tách condition transitions khỏi finding transitions.
- [x] Phần 2 có submit/review/approve/finding assign-resolve-verify, nêu giới hạn request changes.
- [x] Activity: 12 Action, 2 Decision, 21 cạnh.
- [x] Sequence: 6 lifeline, 21 message, ba fragment.
- [x] Prompt tự đủ, sequence giới hạn vào submit.

## Bảng theo dõi sau UC20

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC21 - Quản lý ca kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | Danh sách chưa mô tả query/filter/page/sort và quyền. | Nêu `testcase.read`, các bộ lọc được API hỗ trợ, phân trang và chi tiết theo quyền. |
| 4-8 | MÂU THUẪN | “Lưu ca” tạo READY, trong khi backend dùng endpoint draft với `save_as_draft`; READY đòi trace link và steps có thể xác minh. | Tách DRAFT và READY; lưu DRAFT cho phép chưa hoàn thiện, READY phải có liên kết requirement/criteria và bước có action/result. |
| 5-7 | THIẾU | Kiểm cơ sở kiểm thử gộp requirement, acceptance criteria, test conditions, coverage items, owner và attachment permissions. | Liệt kê validator; yêu cầu/condition phải thuộc project và hợp lệ. |
| 3.3 | SAI | Bản READY được mô tả chỉnh sửa thành DRAFT; code hỗ trợ update DRAFT/READY nhưng mọi thay đổi READY chuyển draft và dùng revision. | Nêu chuyển về DRAFT khi sửa READY, giữ optimistic revision. |
| 3.4 | MÂU THUẪN | “Xóa bản nháp” không phân biệt test_case_draft record với test case đã phát hành. | Đặc tả delete chỉ áp dụng record DRAFT/READY chưa submit; không xóa version đã phê duyệt. |
| 3.5 | THIẾU | Clone chưa nói revision snapshot và key mới. | Nêu clone nguồn version theo expected current version; tạo draft mới, key riêng, source lineage. |
| 3.6-3.7 | THIẾU | Archive/restore thiếu state ACTIVE/NEEDS_UPDATE/OBSOLETE, reason, current version và revision. | Nêu status transitions, giữ version history, kiểm expected current version. |
| 3.8-3.10 | THIẾU | Các thao tác bulk chưa nêu quyền, idempotency, preview tùy chọn hay kết quả từng item. Đánh dấu cần rà soát có điều kiện trạng thái khác cách hiểu thông thường. | Bổ sung bulk tags, add-to-suite, mark review required, bulk archive; ghi per-item result, permission, idempotency. Mark review required hiện code chỉ xử lý ca OBSOLETE sang NEEDS_UPDATE. |
| 5.1 / attachment | THIẾU | BDD và attachment chưa có kiểm tra nội dung/quyền riêng. | Mô tả BDD là cách nhập; attachment yêu cầu `attachment.manage`. |
| Ngoại lệ | THIẾU | Thiếu trace invalid, step unverifiable, owner inactive, revision, state, clone stale, archive/restore conflict, file, lỗi DB. | Bổ sung nhánh theo service và mã lỗi. |

Đã kiểm: **7 điểm rẽ, 10 nhóm nhánh chức năng, 12 nhóm lỗi** gồm quyền/auth, payload/step không hợp lệ, trace/source scope sai, owner không ACTIVE, key/target version conflict, revision/state stale, draft delete không đủ điều kiện, attachment permission, archive/restore conflict, finding/data missing, lỗi DB và hủy. List/search/filter/detail/create/update/delete draft/clone/archive/restore được đối chiếu; bulk tags/add-to-suite/mark review/bulk archive có endpoint; mark review required chỉ nhận ca OBSOLETE và đưa sang NEEDS_UPDATE theo implementation.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Người có quyền tra cứu, tạo ca kiểm thử ở DRAFT/READY, cập nhật draft, xóa riêng draft chưa submit, clone, lưu trữ/khôi phục và thực hiện bulk tags, add-to-suite, mark review required hoặc bulk archive.

**Tiền điều kiện:** Đã xác thực; có quyền `testcase.read/create/update/clone/archive/restore` phù hợp; dự án tồn tại. Các requirement versions, acceptance criteria, test conditions và coverage items phải thuộc project và hợp lệ; owner phải được validate.

**Hậu điều kiện:** DRAFT/READY được ghi theo lựa chọn; update READY chuyển về DRAFT; xóa chỉ loại draft chưa submit; clone tạo draft mới liên kết nguồn; archive chuyển ACTIVE/NEEDS_UPDATE sang OBSOLETE và restore đưa về ACTIVE; version/history đã phát hành được giữ. Bulk thao tác trả kết quả theo item, có thể một phần thất bại; idempotency key hỗ trợ replay. READY có thể tự submit/approve nếu policy cho phép. Lỗi/hủy không xác nhận lưu.

**Tác nhân chính:** Tester/người có quyền.

**Tác nhân phụ:** Không có. Attachment storage là hạ tầng, không có tác nhân ngoài được xác nhận.

**Luồng sự kiện chính: Tạo ca kiểm thử DRAFT**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang Ca kiểm thử dự án. | |
| 2 | | Kiểm tra `testcase.read`; tải danh sách theo query/key/title/status/priority/type/technique/stale/automation/requirement/suite/tag/owner/page/sort. |
| 3 | Chọn Tạo ca kiểm thử. | |
| 4 | | Hiển thị form thông tin, pre/postcondition, steps, test data, expected result, links, owner, tags và attachments. |
| 5 | Nhập nội dung, chọn Lưu nháp. | |
| 6 | | Kiểm tra `testcase.create`, owner, source links, coverage, schema và attachments. |
| 7 | | Sinh key và lưu record DRAFT; ghi audit. |
| 8 | | Trả draft và cập nhật danh sách. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | Tìm theo mã/tên, chọn filter/sort. | Tải kết quả có phân trang; quay lại bước 2. |
| 2.2 | Chọn ca kiểm thử. | Kiểm tra quyền và hiển thị chi tiết/current version/trace links. |
| 5.1 | Chọn lưu READY thay vì DRAFT. | Yêu cầu trace tới ít nhất một requirement version hoặc acceptance criterion và verifiable steps; lưu trạng thái tương ứng theo endpoint. |
| 3.1 | Chọn DRAFT/READY để sửa, cập nhật steps/data/links và lưu. | Kiểm `testcase.update`, status/revision/sources; READY có thay đổi trở về DRAFT. Attachment cần `attachment.manage`. |
| 3.2 | Chọn xóa draft chưa submit. | Kiểm status DRAFT/READY, permission/revision; xóa draft record trong transaction, không xóa approved version. |
| 3.3 | Clone ca hiện hành. | Kiểm current version snapshot, tạo draft mới với key riêng và nguồn lineage. |
| 3.4 | Lưu trữ ACTIVE/NEEDS_UPDATE, nhập reason. | Kiểm `testcase.archive`/expected current version; chuyển OBSOLETE, giữ lịch sử. |
| 3.5 | Khôi phục OBSOLETE, nhập reason. | Kiểm `testcase.restore`/current version; chuyển ACTIVE, ghi audit. |
| 3.6 | Hủy form trước lưu. | Đóng form, không tạo draft. |
| 3.7 | Chọn ca, thêm/gỡ tags hàng loạt. | Kiểm `testcase.bulk.update`; trả preview/result từng item, xử lý idempotently. |
| 3.8 | Chọn ca và bộ test suite, xác nhận thêm. | Kiểm suite/revision và `testcase.bulk.update`; bổ sung current version IDs vào suite, trả per-item result. |
| 3.9 | Chọn ca đánh dấu cần rà soát. | Endpoint hiện xử lý ca OBSOLETE và đổi sang NEEDS_UPDATE, theo quyền bulk update; trả kết quả từng item. |
| 3.10 | Chọn ca lưu trữ hàng loạt, nhập reason và xác nhận. | Kiểm `testcase.bulk.archive`; preview tùy chọn; bỏ qua item có active run, lưu trữ item hợp lệ sang OBSOLETE, trả per-item result. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1.1 | | Thiếu quyền/hết xác thực hoặc record không thuộc project: từ chối truy cập. |
| 6.1 | | Step thiếu action/result khi READY, invalid schema/trace/coverage/condition: trả validation; không lưu READY. |
| 6.2 | | Owner không hợp lệ/inactive hoặc source version thay đổi/không thuộc project: từ chối ghi. |
| 6.3 | | Key trùng hoặc target version/expected current version stale: trả conflict, không nhân đôi. |
| 3.1.1 | | Draft không còn DRAFT/READY, revision conflict hoặc có attachment mà thiếu quyền: không update. |
| 3.2.1 | | Draft đã submit/approve hoặc revision đổi: không xóa; version history giữ nguyên. |
| 3.4.1/3.5.1 | | Status/current version không phù hợp hoặc revision conflict: không đổi lifecycle status. |
| 3.6.1 | | Người dùng hủy trước request: không lưu. |
| Mọi bước | | Lỗi DB/API/storage: trả lỗi; không báo thành công nếu chưa commit. |

**Giả định / Câu hỏi cần làm rõ:** UI gọi “Đánh dấu cần rà soát” nhưng backend hiện chỉ nhận ca OBSOLETE và chuyển sang NEEDS_UPDATE; cần xác nhận đây là cách vận hành chủ ý. Table nói thêm vào suite; implementation lưu current version IDs vào suite và kiểm revision. Table dùng “xóa bản nháp”, nên chỉ mô tả xóa draft entity chưa submit.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Tester | Bắt đầu ở danh sách ca kiểm thử |
| A1 | 1 | Action | Tester | [1] Mở trang Ca kiểm thử |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền và bộ lọc |
| D1 | 3 | Decision | Tester | [3] Chọn xem/tìm/tạo/sửa/xóa/clone/archive/restore/bulk? |
| A3 | 2.1 | Action | Tester | [2.1] Tìm hoặc lọc ca kiểm thử |
| A4 | 2.2 | Action | Tester | [2.2] Xem chi tiết ca kiểm thử |
| A5 | 5 | Action | Tester | [5] Nhập ca và chọn lưu DRAFT |
| A6 | 5.1 | Action | Tester | [5.1] Lưu ca ở trạng thái READY |
| A7 | 3.1 | Action | Tester | [3.1] Cập nhật draft hoặc READY |
| A8 | 3.2 | Action | Tester | [3.2] Xóa draft chưa submit |
| A9 | 3.3 | Action | Tester | [3.3] Clone ca kiểm thử |
| A10 | 3.4/3.5 | Action | Tester | [3.4] Archive hoặc restore ca |
| D2 | 6/3.1-3.5 | Decision | Hệ thống | [6] Permission, source, state và revision hợp lệ? |
| A11 | 7 | Action | Hệ thống | [7] Validate, commit thao tác và trả kết quả từng item |
| A12 | 8 | Action | Hệ thống | [8] Trả kết quả và làm mới danh sách |
| A13 | 6.1/3.2.1 | Action | Hệ thống | [6.1] Báo validation/state/revision error |
| A14 | 6.3 | Action | Tester | [6.3] Hủy tạo mới |
| A15 | 3.7 | Action | Tester | [3.7] Thêm hoặc gỡ nhãn hàng loạt |
| A16 | 3.8 | Action | Tester | [3.8] Thêm ca vào suite |
| A17 | 3.9 | Action | Tester | [3.9] Đánh dấu cần rà soát hàng loạt |
| A18 | 3.10 | Action | Tester | [3.10] Lưu trữ hàng loạt |
| F1 | 8/2.2/3.2-3.5 | Final | Hệ thống | Kết thúc với kết quả thao tác |
| F2 | 6.1/6.3 | Final | Hệ thống | Kết thúc không ghi thành công |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Danh sách tải xong |
| D1 | A3 | [Tìm/lọc] |
| A3 | A2 | [Tải danh sách mới] |
| D1 | A4 | [Xem chi tiết] |
| A4 | F1 | Đã hiển thị |
| D1 | A5 | [Tạo DRAFT] |
| D1 | A6 | [Tạo READY] |
| D1 | A7 | [Sửa DRAFT/READY] |
| D1 | A8 | [Xóa draft chưa submit] |
| D1 | A9 | [Clone] |
| D1 | A10 | [Archive/restore] |
| A5 | D2 | Đã gửi payload draft |
| A6 | D2 | Đã gửi payload READY |
| A7 | D2 | Đã gửi patch/revision |
| A8 | D2 | Đã xác nhận xóa draft |
| A9 | D2 | Đã yêu cầu clone với current version |
| A10 | D2 | Đã xác nhận lifecycle transition |
| A5 | A14 | [Hủy trước gửi] |
| D1 | A15 | [Bulk tags] |
| D1 | A16 | [Thêm vào suite] |
| D1 | A17 | [Mark review required] |
| D1 | A18 | [Bulk archive] |
| A15 | D2 | Đã gửi bulk tag payload/idempotency key |
| A16 | D2 | Đã gửi suite ID và expected revision |
| A17 | D2 | Đã gửi bulk review payload |
| A18 | D2 | Đã xác nhận reason bulk archive |
| D2 | A11 | [Bulk operation hợp lệ; kết quả từng item sẵn sàng] |
| D2 | A11 | [Quyền/schema/source/state/revision hợp lệ] |
| D2 | A13 | [Validation/quyền/state/revision lỗi] |
| A11 | A12 | Đã commit hoặc trả trạng thái thao tác |
| A12 | F1 | Đã hiển thị kết quả |
| A13 | F2 | Đã báo lỗi, không ghi thành công |
| A14 | F2 | Không tạo draft |

### 3c. Số liệu

N = 10 ô có nội dung; M = 18 Action; D = 2 Decision; E = 34 cạnh. Các thao tác được tách, xóa chỉ dành cho draft chưa submit; nhãn hàng loạt/add-to-suite không đưa vào do chưa xác nhận endpoint.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa tạo draft thủ công. Các thao tác archive/version/delete thuộc Activity để sơ đồ không quá tải.

### 4a. Lifeline trái sang phải

Tester → Giao diện Ca kiểm thử → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Ca kiểm thử | [1] moTrangCaKiemThu(project_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Ca kiểm thử | Controller/API | [2] listTestCases(project_id, filters, page) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listTestCaseRecords(filters) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findCases(project_id, filters) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectTestCases(filters) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDanhSachCases() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traPage() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traCasesHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Ca kiểm thử | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Ca kiểm thử | Tester | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Tester | Giao diện Ca kiểm thử | [3] nhapTestCaseVaChonLuuNhAp(payload) | đồng bộ | opt [Tạo draft] |
| 12 | 6 | Giao diện Ca kiểm thử | Controller/API | [6] createTestCaseDraft(save_as_draft=true, payload) | đồng bộ | opt [Tạo draft] |
| 13 | 6 | Controller/API | Service | [6] createTestCaseDraftRecord(project_id, payload) | đồng bộ | opt [Tạo draft] |
| 14 | 6 | Service | Service | [6] validateOwnerSourcesCoverageAndAttachments() | tự gọi | alt [Hợp lệ/lỗi] |
| 15 | 7 | Service | Repository | [7] insertTestCaseDraft(draft) | đồng bộ | alt [Tạo thành công/lỗi] |
| 16 | 7 | Repository | Database | [7] insertDraftAndAudit(draft) | đồng bộ | alt [Ghi thành công/lỗi] |
| 17 | 7 | Database | Repository | [7] traDraftRevision() | trả về | alt [Ghi thành công/lỗi] |
| 18 | 7 | Repository | Service | [7] traDraft() | trả về | alt [Ghi thành công/lỗi] |
| 19 | 8 | Service | Controller/API | [8] traDraftHoacLoi() | trả về | alt [Tạo thành công/lỗi] |
| 20 | 8 | Controller/API | Giao diện Ca kiểm thử | [8] traResponse() | trả về | alt [Tạo thành công/lỗi] |
| 21 | 8 | Giao diện Ca kiểm thử | Tester | [8] hienThiDraftVaDanhSach() | trả về | alt [Tạo thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 21, fragment = 3: alt tải, opt tạo draft, alt validate/commit. READY-specific trace/step validation không chạy trong kịch bản draft.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC21 - Quản lý ca kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Tester/Hệ thống. Bố cục rõ, không gộp create/update/delete/clone/archive/restore.

ĐẶC TẢ
Mô tả: Xem/tìm/lọc, tạo DRAFT/READY, cập nhật, xóa draft chưa submit, clone, archive/restore, bulk tags, thêm vào suite, đánh dấu review required và bulk archive.
Tiền điều kiện: Đã xác thực, quyền theo thao tác; source links thuộc project; owner hợp lệ; attachment cần `attachment.manage`.
Hậu điều kiện: Draft lưu; READY cần source trace và verifiable steps; sửa READY chuyển DRAFT; delete chỉ xóa draft chưa submit; clone tạo draft key riêng; archive ACTIVE/NEEDS_UPDATE→OBSOLETE; restore OBSOLETE→ACTIVE; lịch sử phát hành được giữ.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Không có.
Luồng chính: mở danh sách; chọn read/search/create draft/create ready/update/delete draft/clone/archive/restore; validate; lưu và trả kết quả.
Ngoại lệ: permission/auth, invalid step/trace/source/coverage/owner, key/current version/revision conflict, state immutable, attachment permission, DB error, cancel. Bulk tags/add-to-suite/mark review/archive có endpoint và được mô tả riêng ở các nhánh 3.7-3.10.

NODE
I Initial Tester Bắt đầu ở danh sách ca kiểm thử
A1 Action Tester [1] Mở trang Ca kiểm thử
A2 Action Hệ thống [2] Tải danh sách theo quyền và bộ lọc
D1 Decision Tester [3] Chọn tìm, xem, tạo, sửa, xóa, clone, archive, restore hay bulk?
A3 Action Tester [2.1] Tìm hoặc lọc ca kiểm thử
A4 Action Tester [2.2] Xem chi tiết ca kiểm thử
A5 Action Tester [5] Nhập ca và chọn lưu DRAFT
A6 Action Tester [5.1] Lưu ca ở trạng thái READY
A7 Action Tester [3.1] Cập nhật draft hoặc READY
A8 Action Tester [3.2] Xóa draft chưa submit
A9 Action Tester [3.3] Clone ca kiểm thử
A10 Action Tester [3.4] Archive hoặc restore ca
D2 Decision Hệ thống [6] Permission, source, state và revision hợp lệ?
A11 Action Hệ thống [7] Validate, commit thao tác và trả kết quả từng item
A12 Action Hệ thống [8] Trả kết quả và làm mới danh sách
A13 Action Hệ thống [6.1] Báo validation/state/revision error
A14 Action Tester [6.3] Hủy tạo mới
A15 Action Tester [3.7] Thêm hoặc gỡ nhãn hàng loạt
A16 Action Tester [3.8] Thêm ca vào suite
A17 Action Tester [3.9] Đánh dấu cần rà soát hàng loạt
A18 Action Tester [3.10] Lưu trữ hàng loạt
F1 Final Hệ thống Kết thúc với kết quả thao tác
F2 Final Hệ thống Kết thúc không ghi thành công

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Danh sách tải xong]
D1 -> A3 [Tìm/lọc]
A3 -> A2 [Tải danh sách mới]
D1 -> A4 [Xem]
A4 -> F1 [Chi tiết hiển thị]
D1 -> A5 [Tạo DRAFT]
D1 -> A6 [Tạo READY]
D1 -> A7 [Sửa DRAFT/READY]
D1 -> A8 [Xóa draft chưa submit]
D1 -> A9 [Clone]
D1 -> A10 [Archive/restore]
A5 -> D2 [Đã gửi payload draft]
A6 -> D2 [Đã gửi payload READY]
A7 -> D2 [Đã gửi patch/revision]
A8 -> D2 [Đã xác nhận xóa draft]
A9 -> D2 [Đã gửi expected current version]
A10 -> D2 [Đã xác nhận lifecycle transition]
A5 -> A14 [Hủy trước gửi]
D1 -> A15 [Bulk tags]
D1 -> A16 [Thêm vào suite]
D1 -> A17 [Mark review required]
D1 -> A18 [Bulk archive]
A15 -> D2 [Đã gửi bulk tag payload/idempotency key]
A16 -> D2 [Đã gửi suite ID và expected revision]
A17 -> D2 [Đã gửi bulk review payload]
A18 -> D2 [Đã xác nhận reason bulk archive]
D2 -> A11 [Bulk operation hợp lệ; kết quả từng item sẵn sàng]
D2 -> A11 [Quyền/schema/source/state/revision hợp lệ]
D2 -> A13 [Validation/quyền/state/revision lỗi]
A11 -> A12 [Đã commit hoặc trả trạng thái]
A12 -> F1 [Kết quả hiển thị]
A13 -> F2 [Đã báo lỗi]
A14 -> F2 [Không tạo draft]

YÊU CẦU: Guard cho mọi cạnh Decision, no hanging nodes. Delete chỉ draft chưa submit; không xóa version được duyệt. Không tự thêm thao tác nhãn hàng loạt/add-to-suite.
KIỂM TRA: Action = 18, Decision = 2, cạnh = 34. Báo kiểm đếm cuối.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC21 - Quản lý ca kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Sequence chỉ minh họa tạo draft thủ công.

ĐẶC TẢ
Mô tả: Tạo test case draft.
Tiền điều kiện: Đã xác thực, có `testcase.create`, project tồn tại.
Hậu điều kiện: DRAFT được lưu; validation/DB error không báo thành công.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Không có.
Luồng chính: load list, nhập form, API validate source/owner/coverage/attachments, lưu draft, trả UI.
Thay thế: READY/update/delete/clone/archive/restore thuộc Activity.
Ngoại lệ: quyền, owner/source/schema invalid, attachment permission, DB error.

LIFELINE: Tester; Giao diện Ca kiểm thử; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Tester -> Giao diện Ca kiểm thử | [1] moTrangCaKiemThu(project_id) | đồng bộ | chính
2 | 2 | Giao diện Ca kiểm thử -> Controller/API | [2] listTestCases(project_id, filters, page) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] listTestCaseRecords(filters) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findCases(project_id, filters) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectTestCases(filters) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traDanhSachCases() | trả về | chính
7 | 2 | Repository -> Service | [2] traPage() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traCasesHoacLoi() | trả về | chính
9 | 2 | Controller/API -> Giao diện Ca kiểm thử | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Ca kiểm thử -> Tester | [2] hienThiDanhSach() | trả về | alt [Tải thành công/lỗi]
11 | 3-5 | Tester -> Giao diện Ca kiểm thử | [3] nhapTestCaseVaChonLuuNhAp(payload) | đồng bộ | opt [Tạo draft]
12 | 6 | Giao diện Ca kiểm thử -> Controller/API | [6] createTestCaseDraft(save_as_draft=true, payload) | đồng bộ | opt [Tạo draft]
13 | 6 | Controller/API -> Service | [6] createTestCaseDraftRecord(project_id, payload) | đồng bộ | opt [Tạo draft]
14 | 6 | Service -> Service | [6] validateOwnerSourcesCoverageAndAttachments() | tự gọi | alt [Hợp lệ/lỗi]
15 | 7 | Service -> Repository | [7] insertTestCaseDraft(draft) | đồng bộ | alt [Tạo thành công/lỗi]
16 | 7 | Repository -> Database | [7] insertDraftAndAudit(draft) | đồng bộ | alt [Ghi thành công/lỗi]
17 | 7 | Database -> Repository | [7] traDraftRevision() | trả về | alt [Ghi thành công/lỗi]
18 | 7 | Repository -> Service | [7] traDraft() | trả về | alt [Ghi thành công/lỗi]
19 | 8 | Service -> Controller/API | [8] traDraftHoacLoi() | trả về | alt [Tạo thành công/lỗi]
20 | 8 | Controller/API -> Giao diện Ca kiểm thử | [8] traResponse() | trả về | alt [Tạo thành công/lỗi]
21 | 8 | Giao diện Ca kiểm thử -> Tester | [8] hienThiDraftVaDanhSach() | trả về | alt [Tạo thành công/lỗi]

YÊU CẦU: Đủ 6 lifeline, 21 message, activation bar, self-call validation, no skipped layer. Sync requests have returns, alt/opt guards included. Do not show READY as a result in this draft scenario.
KIỂM TRA: lifeline = 6, message = 21, fragment = 3. Báo đối chiếu cuối.
```

## TỰ KIỂM TRA UC21

- [x] Phần 1 nêu các mâu thuẫn DRAFT/READY, delete draft, bulk tags/suite chưa thấy API.
- [x] Phần 2 tách thao tác và kiểm tra scope/owner/attachment/status.
- [x] Activity: 18 Action, 2 Decision, 34 cạnh.
- [x] Sequence: 6 lifeline, 21 message, ba fragment.
- [x] Prompt tự đủ; bulk actions có căn cứ route/service và giữ kết quả theo item.

## Bảng theo dõi sau UC21

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC22 - Trình duyệt ca kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tiền điều kiện | MƠ HỒ | Bảng cho DRAFT/READY nhưng không nêu quyền submit, assignment hay expected revision. | Ghi `testcase.submit_review`, revision hiện tại và trạng thái được phép. |
| 3-8 | THIẾU | “Kiểm tra hành động/kết quả” chưa nêu nguồn trace, AI evidence và lint policy. | Thêm kiểm source citations, verifiable steps, lint findings; lỗi severity error chặn nếu project setting bật lint blocking. |
| 7.1-7.3 | THIẾU | Bảng chỉ nêu thiếu action/result và AI evidence; thiếu revision/state, scope references, permission, lỗi DB và auto-approval. | Bổ sung các điều kiện từ service; auto-approve chỉ theo policy. |
| 1.1 | SAI | Đánh dấu cần rà soát hàng loạt không phải gửi review state; backend route riêng và chỉ chuyển ca OBSOLETE sang NEEDS_UPDATE. | Để nhánh bulk riêng; ghi rõ trạng thái nguồn và permission `testcase.bulk.update`, per-item result/idempotency. |
| 6.1 | THIẾU | Hủy hộp thoại chưa nêu không gọi transition API. | Bổ sung hậu điều kiện giữ nguyên status. |
| Tác nhân | MƠ HỒ | “Gửi đến Admin” gợi ý có notification ngoài, nhưng endpoint chỉ đổi state/audit. | Ghi reviewer là người xử lý downstream; không tự thêm gửi thông báo. |

Đã kiểm: **3 điểm rẽ, 4 nhánh nghiệp vụ, 8 nhóm lỗi** gồm permission/auth, incomplete steps, source/evidence invalid, lint blocking, status/revision conflict, current source changed, AI source review required, DB error, hủy và bulk item không đủ điều kiện. UC submit không phải CRUD; bulk mark review là action riêng.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Gửi test case draft đủ điều kiện sang IN_REVIEW; có thể đánh dấu hàng loạt ca cần xem lại qua thao tác riêng.

**Tiền điều kiện:** Đã xác thực; user có `testcase.submit_review` và được phép thao tác draft; draft ở DRAFT/READY, revision hiện hành; source links và steps phải hợp lệ. Bulk review-required cần `testcase.bulk.update`.

**Hậu điều kiện:** Thành công chuyển draft sang IN_REVIEW, ghi note, người gửi/thời gian và audit. Nếu auto-approval policy cho phép, service có thể tiếp tục approve. Bulk flag trả per-item outcomes, ca phù hợp OBSOLETE chuyển NEEDS_UPDATE. Hủy/lỗi không được báo submit thành công.

**Tác nhân chính:** Tester/người có quyền gửi rà soát.

**Tác nhân phụ:** Reviewer xử lý review sau đó; không có notification system đã xác nhận.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn ca kiểm thử DRAFT/READY cần gửi. | |
| 2 | | Kiểm tra quyền, tải draft, revision, source refs và trạng thái. |
| 3 | Chọn Gửi rà soát. | |
| 4 | | Hiển thị xác nhận và trường ghi chú. |
| 5 | Nhập ghi chú, xác nhận. | |
| 6 | | Kiểm tra `testcase.submit_review`, project, status/revision, evidence sources, hành động/kết quả xác minh được và lint findings. |
| 7 | | Nếu policy lint blocking bật và có finding severity error, từ chối; nếu hợp lệ, chuyển draft sang IN_REVIEW, lưu note/submitter/time/audit. |
| 8 | | Kiểm tra auto-approval policy; nếu không áp dụng, giữ IN_REVIEW. |
| 9 | | Trả draft/status mới và hiển thị kết quả. Kết thúc. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1 | Chọn nhiều ca và chọn Đánh dấu cần rà soát. | Nhập lý do, gửi bulk request có idempotency key. |
| 1.2 | Xác nhận bulk action. | Kiểm `testcase.bulk.update`; xem từng ID, đánh dấu ca OBSOLETE sang NEEDS_UPDATE, trả PREVIEW hoặc SUCCEEDED/FAILED theo item. |
| 5.1 | Hủy hộp thoại submit. | Đóng dialog, không gọi transition API; giữ status. |
| 8.1 | Policy không cho tự duyệt. | Giữ IN_REVIEW để reviewer xử lý độc lập. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Hết xác thực/thiếu quyền hoặc draft không thuộc project/assignment: từ chối. |
| 6.1 | | Draft không còn DRAFT/READY hoặc expected revision stale: trả conflict, không ghi trạng thái cũ. |
| 6.2 | | Không có thao tác/kết quả xác minh được hoặc AI-generated draft thiếu evidence refs: chặn submit và yêu cầu hoàn thiện/đối chiếu nguồn. |
| 6.3 | | Source version/criteria không còn hợp lệ hoặc thay đổi sau khi soạn: từ chối submit, yêu cầu tải lại. |
| 7.1 | | Lint blocking bật và có finding severity error: trả findings, không chuyển IN_REVIEW. |
| 7.2 | | Transaction/audit thất bại: không xác nhận submit. |
| 1.2.1 | | ID không tìm thấy hoặc không ở OBSOLETE: trả FAILED riêng; operation có thể một phần thành công. |
| 1.2.2 | | Idempotency key tái sử dụng với payload khác/actor khác: trả conflict/forbidden. |

**Giả định / Câu hỏi cần làm rõ:** “Gửi Admin” trong bảng gốc không cho thấy cơ chế notification; nội dung chốt chỉ đổi status. Tác vụ bulk “đánh dấu cần rà soát” hiện yêu cầu reason và chỉ áp dụng cho OBSOLETE, điều này có thể không khớp ý nghĩa UI; cần xác nhận thiết kế mong muốn.

## PHẦN 3 - PHÂN RÃ ACTIVITY (mức trình bày khóa luận)

### 3a. Bảng node

| ID | Bước | Loại | Swimlane | Nhãn |
|---|---|---|---|---|
| I | - | Initial | Tester | Bắt đầu tại danh sách/chi tiết draft |
| A1 | 1 | Action | Tester | [1] Chọn ca DRAFT/READY cần gửi |
| A2 | 2 | Action | Hệ thống | [2] Tải draft, quyền, revision và sources |
| D1 | 3 | Decision | Tester | [3] Chọn gửi một ca, đánh dấu bulk hay hủy? |
| A3 | 4-5 | Action | Tester | [4] Nhập ghi chú và xác nhận submit |
| A4 | 6 | Action | Hệ thống | [6] Kiểm permission, state, evidence, steps và lint |
| D2 | 6-7 | Decision | Hệ thống | [6] Draft và nguồn đủ điều kiện gửi? |
| A5 | 7-8 | Action | Hệ thống | [7] Chuyển IN_REVIEW và xét policy tự duyệt |
| A6 | 9 | Action | Hệ thống | [9] Trả trạng thái và hiển thị kết quả |
| A7 | 1.1-1.2 | Tester | Tester | [1.1] Chọn nhiều ca, nhập lý do và bulk action |
| A8 | 1.2 | Action | Hệ thống | [1.2] Đánh dấu item hợp lệ NEEDS_UPDATE |
| A9 | 5.1 | Action | Tester | [5.1] Hủy submit |
| A10 | 6.1/6.2/7.1 | Action | Hệ thống | [6.1] Báo conflict, evidence hoặc lint findings |
| F1 | 9/1.2 | Final | Hệ thống | Kết thúc với kết quả trả về |
| F2 | 5.1/6.1/7.1 | Final | Hệ thống | Kết thúc không submit được |

### 3b. Bảng cạnh

| Từ | Đến | Guard |
|---|---|---|
| I | A1 | Bắt đầu |
| A1 | A2 | Luôn |
| A2 | D1 | Tải thành công |
| D1 | A3 | [Gửi một ca] |
| D1 | A7 | [Bulk đánh dấu review-required] |
| D1 | A9 | [Hủy] |
| A3 | A9 | [Hủy dialog] |
| A3 | A4 | Đã xác nhận submit |
| A4 | D2 | Kiểm tra xong |
| D2 | A5 | [Permission/status/revision/source/steps hợp lệ] |
| D2 | A10 | [Thiếu điều kiện/lint blocker/conflict] |
| A5 | A6 | Submit đã commit; auto-approve theo policy nếu có |
| A6 | F1 | Kết quả đã hiển thị |
| A7 | A8 | Đã xác nhận bulk action |
| A8 | F1 | Per-item outcomes đã trả |
| A9 | F2 | Không gọi mutation |
| A10 | F2 | Không chuyển state thành công |

### 3c. Số liệu

N = 7 ô có nội dung; M = 10 Action; D = 2 Decision; E = 17 cạnh. Submit đơn và bulk flag là hai luồng khác nhau; lỗi lint dừng trước transition.

## PHẦN 4 - PHÂN RÃ SEQUENCE (mức trình bày khóa luận)

Sequence minh họa submit một draft. Bulk mark-review-required được giữ trong Activity để biểu đồ sequence dễ đọc.

### 4a. Lifeline trái sang phải

Tester → Giao diện Ca kiểm thử → Controller/API → Service → Repository → Database. Không có hệ thống ngoài.

### 4b. Bảng message

| STT | Bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Ca kiểm thử | [1] chonDraft(test_case_draft_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Ca kiểm thử | Controller/API | [2] getTestCaseDraft(id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] requireAssignedDesignDraft(id, testcase.read) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findCaseDraft(id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectTestCaseDraft(id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDraft() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traDraftHoacNotFound() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traDraft() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Ca kiểm thử | [2] traResponse() | trả về | alt [Tải thành công/lỗi] |
| 10 | 2 | Giao diện Ca kiểm thử | Tester | [2] hienThiDraft() | trả về | alt [Tải thành công/lỗi] |
| 11 | 3-5 | Tester | Giao diện Ca kiểm thử | [3] xacNhanGuiRaSoat(note) | đồng bộ | opt [Submit] |
| 12 | 6 | Giao diện Ca kiểm thử | Controller/API | [6] submitTestCaseReview(project_id, draft_id, expected_revision, note) | đồng bộ | opt [Submit] |
| 13 | 6 | Controller/API | Service | [6] submitTestCaseReviewRecord(payload) | đồng bộ | opt [Submit] |
| 14 | 6 | Service | Service | [6] validateSourcesVerifiableStepsAndLint() | tự gọi | alt [Hợp lệ/lỗi] |
| 15 | 7 | Service | Repository | [7] transitionDraftToInReview(expected_revision) | đồng bộ | alt [Commit/conflict] |
| 16 | 7 | Repository | Database | [7] updateDraftAndAudit(IN_REVIEW) | đồng bộ | alt [Commit/conflict] |
| 17 | 7 | Database | Repository | [7] traUpdatedDraft() | trả về | alt [Commit/conflict] |
| 18 | 7 | Repository | Service | [7] traDraft() | trả về | alt [Commit/conflict] |
| 19 | 8 | Service | Service | [8] checkAutoApprovalPolicy() | tự gọi | opt [Policy tự duyệt] |
| 20 | 9 | Service | Controller/API | [9] traIN_REVIEWHoacApprovalResult() | trả về | alt [Thành công/lỗi] |
| 21 | 9 | Controller/API | Giao diện Ca kiểm thử | [9] traResponse() | trả về | alt [Thành công/lỗi] |
| 22 | 9 | Giao diện Ca kiểm thử | Tester | [9] hienThiTrangThai() | trả về | alt [Thành công/lỗi] |

### 4c. Số liệu

Lifeline = 6, message = 22, fragment = 4: alt tải, opt submit, alt validation/commit, opt auto-approval. Mỗi request đồng bộ có phản hồi theo tầng.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC22 - Trình duyệt ca kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt; swimlane Tester/Hệ thống. Bố cục gọn, tách submit đơn và bulk review-required.

ĐẶC TẢ
Mô tả: Gửi test case DRAFT/READY sang IN_REVIEW; có bulk action riêng đánh dấu cần rà soát.
Tiền điều kiện: Đã xác thực, có `testcase.submit_review`, draft status/revision hợp lệ; bulk cần `testcase.bulk.update`.
Hậu điều kiện: Submit chuyển IN_REVIEW, lưu note/submitter/time/audit; policy có thể auto-approve. Bulk endpoint hiện chỉ chuyển ca OBSOLETE sang NEEDS_UPDATE, trả kết quả từng item.
Tác nhân chính: Tester/người có quyền. Tác nhân phụ: Reviewer downstream, không khẳng định notification.
Luồng chính: tải draft; chọn submit; nhập note; kiểm permission/status/revision/evidence/verifiable steps/lint; nếu hợp lệ chuyển IN_REVIEW; xét policy; trả trạng thái.
Thay thế: bulk review-required yêu cầu lý do/idempotency và kết quả từng item; hủy không gọi API.
Ngoại lệ: thiếu quyền, state/revision conflict, source/evidence invalid, thiếu action/result, lint blocking, DB lỗi, bulk item không tồn tại/không OBSOLETE.

NODE
I Initial Tester Bắt đầu tại danh sách/chi tiết draft
A1 Action Tester [1] Chọn ca DRAFT/READY cần gửi
A2 Action Hệ thống [2] Tải draft, quyền, revision và sources
D1 Decision Tester [3] Chọn gửi một ca, đánh dấu bulk hay hủy?
A3 Action Tester [4] Nhập ghi chú và xác nhận submit
A4 Action Hệ thống [6] Kiểm permission, state, evidence, steps và lint
D2 Decision Hệ thống [6] Draft và nguồn đủ điều kiện gửi?
A5 Action Hệ thống [7] Chuyển IN_REVIEW và xét policy tự duyệt
A6 Action Hệ thống [9] Trả trạng thái và hiển thị kết quả
A7 Action Tester [1.1] Chọn nhiều ca, nhập lý do và bulk action
A8 Action Hệ thống [1.2] Đánh dấu item hợp lệ NEEDS_UPDATE
A9 Action Tester [5.1] Hủy submit
A10 Action Hệ thống [6.1] Báo conflict, evidence hoặc lint findings
F1 Final Hệ thống Kết thúc với kết quả trả về
F2 Final Hệ thống Kết thúc không submit được

CẠNH
I -> A1 [Bắt đầu]
A1 -> A2 [Luôn]
A2 -> D1 [Tải thành công]
D1 -> A3 [Gửi một ca]
D1 -> A7 [Bulk đánh dấu review-required]
D1 -> A9 [Hủy]
A3 -> A9 [Hủy dialog]
A3 -> A4 [Đã xác nhận submit]
A4 -> D2 [Kiểm tra xong]
D2 -> A5 [Permission/status/revision/source/steps hợp lệ]
D2 -> A10 [Thiếu điều kiện/lint blocker/conflict]
A5 -> A6 [Submit đã commit; auto-approve theo policy nếu có]
A6 -> F1 [Kết quả đã hiển thị]
A7 -> A8 [Đã xác nhận bulk action]
A8 -> F1 [Per-item outcomes đã trả]
A9 -> F2 [Không gọi mutation]
A10 -> F2 [Không chuyển state thành công]

YÊU CẦU: Guards rõ; bulk không mô tả như submit; mark review-required đúng phạm vi OBSOLETE→NEEDS_UPDATE; lỗi không nối sang thành công; không thêm email.
KIỂM TRA: Action = 10, Decision = 2, cạnh = 17. Báo đối chiếu ở cuối.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC22 - Trình duyệt ca kiểm thử của Veriq bằng Visual Paradigm AI Chatbot. PlantUML, nhãn Tiếng Việt. Minh họa submit một draft, bố cục vừa trang.

ĐẶC TẢ
Mô tả: Gửi ca DRAFT/READY đủ điều kiện sang IN_REVIEW.
Tiền điều kiện: Đã xác thực, permission testcase.submit_review, assigned draft tồn tại và revision hiện hành.
Hậu điều kiện: Status IN_REVIEW, note/submitter/time/audit; auto-approval tùy policy. Lỗi validation/conflict không submit.
Tác nhân chính: Tester/người gửi. Tác nhân phụ: Không có trong sequence này.
Luồng chính: load draft, xác nhận, validate source/steps/lint, update IN_REVIEW, policy check, trả kết quả.
Thay thế: bulk action, hủy nằm ngoài kịch bản sequence.
Ngoại lệ: permission, state/revision, source/evidence, missing steps, lint blocker, DB error.

LIFELINE: Tester; Giao diện Ca kiểm thử; Controller/API; Service; Repository; Database.

MESSAGE
1 | 1 | Tester -> Giao diện Ca kiểm thử | [1] chonDraft(test_case_draft_id) | đồng bộ | chính
2 | 2 | Giao diện Ca kiểm thử -> Controller/API | [2] getTestCaseDraft(id) | đồng bộ | chính
3 | 2 | Controller/API -> Service | [2] requireAssignedDesignDraft(id, testcase.read) | đồng bộ | chính
4 | 2 | Service -> Repository | [2] findCaseDraft(id) | đồng bộ | chính
5 | 2 | Repository -> Database | [2] selectTestCaseDraft(id) | đồng bộ | chính
6 | 2 | Database -> Repository | [2] traDraft() | trả về | chính
7 | 2 | Repository -> Service | [2] traDraftHoacNotFound() | trả về | chính
8 | 2 | Service -> Controller/API | [2] traDraft() | trả về | chính
9 | 2 | Controller/API -> Giao diện Ca kiểm thử | [2] traResponse() | trả về | alt [Tải thành công/lỗi]
10 | 2 | Giao diện Ca kiểm thử -> Tester | [2] hienThiDraft() | trả về | alt [Tải thành công/lỗi]
11 | 3-5 | Tester -> Giao diện Ca kiểm thử | [3] xacNhanGuiRaSoat(note) | đồng bộ | opt [Submit]
12 | 6 | Giao diện Ca kiểm thử -> Controller/API | [6] submitTestCaseReview(project_id, draft_id, expected_revision, note) | đồng bộ | opt [Submit]
13 | 6 | Controller/API -> Service | [6] submitTestCaseReviewRecord(payload) | đồng bộ | opt [Submit]
14 | 6 | Service -> Service | [6] validateSourcesVerifiableStepsAndLint() | tự gọi | alt [Hợp lệ/lỗi]
15 | 7 | Service -> Repository | [7] transitionDraftToInReview(expected_revision) | đồng bộ | alt [Commit/conflict]
16 | 7 | Repository -> Database | [7] updateDraftAndAudit(IN_REVIEW) | đồng bộ | alt [Commit/conflict]
17 | 7 | Database -> Repository | [7] traUpdatedDraft() | trả về | alt [Commit/conflict]
18 | 7 | Repository -> Service | [7] traDraft() | trả về | alt [Commit/conflict]
19 | 8 | Service -> Service | [8] checkAutoApprovalPolicy() | tự gọi | opt [Policy tự duyệt]
20 | 9 | Service -> Controller/API | [9] traIN_REVIEWHoacApprovalResult() | trả về | alt [Thành công/lỗi]
21 | 9 | Controller/API -> Giao diện Ca kiểm thử | [9] traResponse() | trả về | alt [Thành công/lỗi]
22 | 9 | Giao diện Ca kiểm thử -> Tester | [9] hienThiTrangThai() | trả về | alt [Thành công/lỗi]

YÊU CẦU: Đủ 6 lifeline, 22 message, activation bars, self-call validation/policy; không gọi nhảy lớp; request sync có return; guards/alt/opt rõ.
KIỂM TRA: lifeline = 6, message = 22, fragment = 4. Báo kết quả.
```

## TỰ KIỂM TRA UC22

- [x] Phần 1 phân biệt submit transition với bulk mark review required.
- [x] Phần 2 nêu lint/source/evidence, auto-approval và lỗi có căn cứ.
- [x] Activity: 10 Action, 2 Decision, 17 cạnh.
- [x] Sequence: 6 lifeline, 22 message, bốn fragment.
- [x] Prompt tự đủ; bulk review-required ghi đúng trạng thái hiện triển khai.

## Bảng theo dõi sau UC22

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC23 - Xét duyệt ca kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | Chưa nêu quyền xét duyệt độc lập và dữ liệu so sánh phiên bản/nguồn cần tải để Admin kiểm tra. | Bổ sung quyền `testcase.review`/`testcase.approve`, trạng thái IN_REVIEW, revision và nguồn; không cho người tạo tự duyệt nếu chính sách độc lập áp dụng. |
| 4-9 | MƠ HỒ | “Đáp ứng quy định”, “vấn đề cần xử lý” chưa định nghĩa điều kiện. | Nêu kiểm tra bước có thể xác minh, nguồn còn hiệu lực, revision, lỗi lint cấu hình chặn, trùng lặp có lý do và đối chiếu lại nội dung AI khi cần. |
| 4.1 | SAI | Nhánh yêu cầu chỉnh sửa có thể được mô tả như lựa chọn duyệt sau khi Admin đã xem nội dung, nhưng bước hiện tại chưa phân biệt hai quyết định. | Đặt Decision sau bước 3: phê duyệt hay yêu cầu chỉnh sửa. API xác nhận endpoint trả IN_REVIEW về DRAFT, lưu review note, reason code, người và thời điểm yêu cầu. |
| 1.1 | MƠ HỒ | Nhánh duyệt nhóm tuyên bố phê duyệt tất cả hoặc không ca nào, nhưng chưa mô tả đối chiếu phiên bản/nguồn và xung đột đồng thời. | Giữ hành vi nguyên tử: mọi item phải qua kiểm tra; lỗi một item làm toàn nhóm không commit. Nêu revision, comparison token, độc lập, nguồn và lỗi trùng. |
| 5.1 | THIẾU | Chưa nói rõ khi nào bắt buộc đối chiếu ca AI và quay lại bước phê duyệt nào. | Thêm điều kiện `origin=ai_generated` và chưa có bằng chứng nguồn sau lần chỉnh sửa; đối chiếu, lưu nguồn rồi quay lại bước 4. |
| 7.1-7.3 | THIẾU | Bỏ qua quyền, người tự duyệt, nguồn đổi, lỗi lưu/CSDL và các điều kiện lint/trùng. | Bổ sung ngoại lệ theo kiểm tra thực tế; lỗi không làm thay đổi trạng thái hay phiên bản chính thức. |
| Tiền/hậu điều kiện | THIẾU | Chỉ nói Admin đăng nhập và ca chờ duyệt; chưa yêu cầu quyền, dự án, revision và kết quả thất bại. | Bổ sung quyền và đối tượng thuộc dự án; hậu điều kiện riêng cho được duyệt, toàn nhóm được duyệt, bị từ chối và lỗi không commit. |
| Tác nhân | MƠ HỒ | “Admin” ở bảng nghiệp vụ có thể là vai trò hệ thống; mã nguồn kiểm tra permission. | Giữ nhãn Admin theo bảng gốc, yêu cầu quyền tương ứng; xác nhận tên vai trò chính thức trong mục câu hỏi. |
| CRUD | Không áp dụng | UC xét duyệt không phải UC quản lý dữ liệu tổng quát. | Không thêm xem danh sách/tìm kiếm/thêm/xóa ngoài các chức năng xét duyệt đã nêu. |
| 4.1 | THIẾU | Chưa yêu cầu reason code/ghi chú, kiểm tra revision và quyền độc lập cho thao tác trả ca về bản nháp. | Thêm các điều kiện này theo `request_test_case_changes_record`; kết quả hợp lệ chuyển IN_REVIEW→DRAFT và ghi audit. |

Đã kiểm: **4 điểm rẽ, 6 nhánh, 10 tình huống lỗi/biên**; đã rà điều kiện quyền, trạng thái, revision, nguồn, bước xác minh, lint, trùng lặp, tính nguyên tử của duyệt nhóm, lưu/CSDL, hậu điều kiện và tác nhân. Đã xác minh API yêu cầu chỉnh sửa chuyển IN_REVIEW về DRAFT; còn cần đối chiếu giao diện có hiện đúng thao tác và trường reason code hay không.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Admin có quyền xét duyệt một hoặc nhiều ca kiểm thử đang ở trạng thái IN_REVIEW. Ca được duyệt tạo phiên bản chính thức; việc xét duyệt nhóm là nguyên tử.

**Tiền điều kiện:** Người dùng đã đăng nhập; có quyền `testcase.review` để xem/ngữ cảnh xét duyệt và `testcase.approve` để duyệt; ca thuộc dự án được truy cập, đang IN_REVIEW và có revision hiện hành. Duyệt cá nhân phải tuân thủ chính sách người duyệt độc lập.

**Hậu điều kiện:**
- Thành công cá nhân: tạo version chính thức, cập nhật draft thành APPROVED, liên kết version đã đóng băng, ghi người/thời điểm duyệt và audit.
- Thành công nhóm: tất cả draft được duyệt trong một giao dịch hoặc không draft nào được commit; kết quả ghi nhận batch.
- Không đủ điều kiện/xung đột/lỗi lưu: không tạo kết quả duyệt một phần; trạng thái và version chính thức không bị đổi bởi lần gọi thất bại.
- Yêu cầu chỉnh sửa: nếu được chọn, ca chuyển về DRAFT, lưu review note/reason code, người và thời điểm yêu cầu, đồng thời ghi audit.

**Tác nhân chính:** Admin có quyền xét duyệt ca kiểm thử.

**Tác nhân phụ:** Không có tác nhân ngoài đã được xác nhận.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn ca đang chờ duyệt. | |
| 2 | | Kiểm tra quyền và tải nội dung, revision, liên kết yêu cầu, các bước, căn cứ nguồn và kết quả đối chiếu. |
| 3 | Đọc nội dung, đối chiếu ca với yêu cầu và căn cứ. | |
| 4 | Chọn Phê duyệt, nhập ghi chú nếu cần và xác nhận. | |
| 5 | | Kiểm tra trạng thái IN_REVIEW, quyền duyệt độc lập, revision, bước có thể xác minh, nguồn hiện hành, lint theo cấu hình và kết quả rà trùng. |
| 6 | | Trong giao dịch, tạo version chính thức, cập nhật draft APPROVED, lưu người/thời điểm duyệt và audit. |
| 7 | | Hoàn tất xử lý chỉ mục/dữ liệu dẫn xuất; nếu phần dẫn xuất còn chờ, ghi nhận trạng thái chờ thay vì báo đã hoàn tất đồng bộ. |
| 8 | | Trả kết quả và hiển thị version được duyệt. Kết thúc thành công. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Nếu ca do AI tạo cần đối chiếu lại, mở nội dung cùng nguồn, kiểm tra căn cứ hiện có và quay lại bước 4. Không giả định có thao tác lưu riêng. |
| 4.1 | Chọn duyệt nhóm, chọn các ca IN_REVIEW, nhập ghi chú và xác nhận. | Kiểm tra tất cả mục gồm revision, comparison token, quyền độc lập, nguồn, bước, lint và trùng; nếu hợp lệ, duyệt cả nhóm trong một giao dịch rồi trả kết quả. Kết thúc thành công. |
| 4.2 | Chọn Yêu cầu chỉnh sửa, chọn reason code, nhập nhận xét và xác nhận. | Kiểm tra quyền `testcase.review`, trạng thái IN_REVIEW, revision và người duyệt độc lập; chuyển draft về DRAFT, lưu reason/note, người và thời điểm, ghi audit; hiển thị kết quả. Kết thúc UC. |
| 4.1.1 | Hủy hộp thoại xác nhận. | Không gọi thao tác ghi; kết thúc UC, không đổi dữ liệu. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Không có quyền hoặc ca không thuộc phạm vi dự án. Từ chối truy cập; kết thúc thất bại. |
| 2.2 | | Không tìm thấy ca hoặc ca không còn IN_REVIEW. Thông báo cần tải lại; kết thúc thất bại. |
| 5.1 | | Revision, comparison token, nguồn hoặc phiên bản gốc đã đổi. Không duyệt bản cũ; yêu cầu tải lại và đối chiếu, kết thúc thất bại. |
| 5.2 | | Thiếu bước có kết quả mong đợi, nguồn bắt buộc, đối chiếu AI, lý do giữ ca trùng, hoặc có lint error được cấu hình chặn. Trả lỗi/finding; kết thúc thất bại. |
| 5.3 | | Có bản trùng chưa xử lý hoặc version chính thức xung đột. Không ghi nhận phê duyệt; kết thúc thất bại. |
| 4.1.1.1 | | Một thành viên nhóm không hợp lệ hoặc giao dịch/CSDL thất bại. Hủy toàn bộ giao dịch; trả lỗi theo item; kết thúc thất bại. |
| 6.1 | | Lỗi hệ thống khi tạo version, cập nhật draft hoặc ghi audit. Rollback giao dịch nếu chưa commit; kết thúc thất bại. |
| 7.1 | | Dữ liệu dẫn xuất/chỉ mục chưa hoàn tất sau khi version đã commit. Trả version đã duyệt kèm trạng thái chờ xử lý; không khẳng định thất bại của transaction đã commit. |
| 4.2.1 | | Thiếu quyền, sai trạng thái/revision hoặc lỗi ghi nhận khi yêu cầu chỉnh sửa. Không đổi trạng thái; hiển thị lỗi và kết thúc thất bại. |

**Giả định / Câu hỏi cần làm rõ**
- Tên vai trò Admin có tương ứng chính xác với permission `testcase.approve` không?
- Cần xác nhận giao diện có hiển thị reason code giống API và giới hạn độ dài review note như thế nào.
- “Ghi chú” ở duyệt cá nhân là tùy chọn; API có thể không lưu cùng mô hình với batch. Cần xác nhận UI/API nếu luận văn mô tả trường bắt buộc.

## PHẦN 3 - PHÂN RÃ ACTIVITY (chưa vẽ)

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---:|---|---|---|
| I | — | Initial | Hệ thống | Bắt đầu, người dùng đã xác thực |
| A1 | 1 | Action | Người dùng | [1] Chọn ca chờ duyệt |
| A2 | 2 | Action | Hệ thống | [2] Tải nội dung và revision |
| D1 | 2 | Decision | Hệ thống | Ca tồn tại và người dùng có quyền? |
| A3 | 2.1 | Action | Hệ thống | [2.1] Báo lỗi truy cập hoặc không tìm thấy |
| A4 | 3 | Action | Người dùng | [3] Đọc và đối chiếu nội dung |
| D2 | 3.1 | Decision | Người dùng | Có cần đối chiếu lại nguồn AI? |
| A5 | 3.1.1 | Action | Hệ thống | [3.1.1] Hiển thị nguồn và đối chiếu |
| A6 | 3.1.2 | Action | Người dùng | [3.1.2] Hoàn tất xem căn cứ và quay lại duyệt |
| M1 | 4 | Merge | Hệ thống | Tiếp tục thao tác duyệt |
| D3 | 4 | Decision | Người dùng | Duyệt cá nhân, duyệt nhóm, yêu cầu sửa hay hủy? |
| A7 | 4.1 | Action | Người dùng | [4.1] Chọn nhóm và xác nhận duyệt |
| A8 | 5 | Action | Hệ thống | [5] Kiểm tra điều kiện và revision |
| D4 | 5 | Decision | Hệ thống | Tất cả điều kiện xét duyệt hợp lệ? |
| A9 | 5.1 | Action | Hệ thống | [5.1] Trả finding và lỗi xét duyệt |
| A10 | 6 | Action | Hệ thống | [6] Tạo version và ghi quyết định duyệt |
| D5 | 6 | Decision | Hệ thống | Giao dịch đã commit? |
| A11 | 6.1 | Action | Hệ thống | [6.1] Báo lỗi lưu và rollback |
| A12 | 7 | Action | Hệ thống | [7] Hoàn tất dữ liệu dẫn xuất |
| D6 | 7 | Decision | Hệ thống | Dữ liệu dẫn xuất đã hoàn tất? |
| A13 | 7.1 | Action | Hệ thống | [7.1] Đánh dấu chờ đồng bộ dẫn xuất |
| A14 | 8 | Action | Hệ thống | [8] Trả kết quả và hiển thị version |
| A15 | 4.1.1 | Action | Người dùng | [4.1.1] Hủy xác nhận duyệt nhóm |
| A16 | 4.2 | Action | Người dùng | [4.2] Nhập lý do và xác nhận yêu cầu chỉnh sửa |
| A17 | 4.2.1 | Action | Hệ thống | [4.2.1] Trả draft về DRAFT và ghi audit |
| F1 | — | Final | Hệ thống | Kết thúc thành công |
| F2 | — | Final | Hệ thống | Kết thúc không thay đổi dữ liệu |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | UC bắt đầu |
| A1 | A2 | Đã chọn ca |
| A2 | D1 | Đã tải kết quả |
| D1 | A4 | Ca tồn tại và quyền hợp lệ |
| D1 | A3 | Không có quyền hoặc không tìm thấy |
| A3 | F2 | Lỗi đã hiển thị |
| A4 | D2 | Đã đọc nội dung |
| D2 | A5 | Ca AI cần đối chiếu lại |
| D2 | M1 | Không cần đối chiếu lại |
| A5 | A6 | Đã hiển thị nguồn |
| A6 | M1 | Đã xem căn cứ hiện có |
| M1 | D3 | Tiếp tục xét duyệt |
| D3 | A8 | Duyệt cá nhân |
| D3 | A7 | Chọn duyệt nhóm |
| D3 | A15 | Hủy thao tác |
| D3 | A16 | Yêu cầu chỉnh sửa |
| A7 | A8 | Đã xác nhận nhóm |
| A15 | F2 | Không gửi yêu cầu ghi |
| A16 | A17 | Đã xác nhận yêu cầu sửa |
| A17 | F1 | Chuyển DRAFT và hiển thị kết quả |
| A8 | D4 | Kiểm tra hoàn tất |
| D4 | A10 | Tất cả điều kiện hợp lệ |
| D4 | A9 | Có finding hoặc xung đột |
| A9 | F2 | Lỗi đã trả về |
| A10 | D5 | Đã thử commit |
| D5 | A12 | Commit thành công |
| D5 | A11 | Commit thất bại |
| A11 | F2 | Rollback hoàn tất |
| A12 | D6 | Đã xử lý dữ liệu dẫn xuất |
| D6 | A14 | Dữ liệu dẫn xuất hoàn tất |
| D6 | A13 | Còn chờ xử lý |
| A13 | A14 | Trạng thái chờ đã ghi nhận |
| A14 | F1 | Kết quả đã hiển thị |

### 3c. Số liệu

N = 13 ô đặc tả có nội dung (8 chính, 4 thay thế, 1 ngoại lệ đại diện). M = 16 Action, D = 6 Decision, E = 36 cạnh. Một nhánh lỗi ngoại lệ bổ sung theo cùng cấu trúc A8→D4→A9→F2.

## PHẦN 4 - PHÂN RÃ SEQUENCE (chưa vẽ)

### 4a. Lifeline trái sang phải

Admin → Giao diện xét duyệt → Controller/API → Service → Repository → Database. Hệ thống ngoài: không có.

### 4b. Bảng message

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Admin | Giao diện xét duyệt | [1] chonCaChoDuyet(id) | đồng bộ | chính |
| 2 | 2 | Giao diện xét duyệt | Controller/API | [2] getReviewContext(id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] loadReviewContext(id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] findDraftAndSources(id) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectDraftSourcesRevision(id) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDraftNguonRevision() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traReviewContext() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traReviewContextHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện xét duyệt | [2] traReviewResponse() | trả về | chính |
| 10 | 2 | Giao diện xét duyệt | Admin | [2] hienThiNoiDungNguonVaFinding() | trả về | chính |
| 11 | 3.1 | Admin | Giao diện xét duyệt | [3.1] xemCanCuAI() | đồng bộ | opt [Ca AI cần đối chiếu] |
| 12 | 3.1 | Giao diện xét duyệt | Admin | [3.1] hienThiCanCuDaCo() | trả về | opt [Ca AI cần đối chiếu] |
| 13 | 4 | Admin | Giao diện xét duyệt | [4] chonQuyetDinh(note, expected_revision) | đồng bộ | alt [duyệt/yêu cầu sửa/hủy] |
| 14 | 5 | Giao diện xét duyệt | Controller/API | [5] guiQuyetDinh(payload) | đồng bộ | alt [duyệt/yêu cầu sửa/hủy] |
| 15 | 5 | Controller/API | Service | [5] processReviewDecision(payload) | đồng bộ | alt [duyệt/yêu cầu sửa/hủy] |
| 16 | 5 | Service | Service | [5] validatePermissionStateRevisionAndReview() | tự gọi | alt [đủ điều kiện/lỗi] |
| 17 | 6 | Service | Repository | [6] publishApprovedVersion(expected_revision) | đồng bộ | alt [duyệt cá nhân/duyệt nhóm] |
| 18 | 6 | Repository | Database | [6] transactionInsertVersionUpdateDraftAndAudit() | đồng bộ | alt [commit/lỗi] |
| 19 | 6 | Database | Repository | [6] traCommitHoacRollback() | trả về | alt [commit/lỗi] |
| 20 | 6 | Repository | Service | [6] traPublicationResult() | trả về | alt [commit/lỗi] |
| 21 | 6.1 | Service | Repository | [6.1] transitionInReviewToDraft(reason_code, note, expected_revision) | đồng bộ | alt [yêu cầu sửa] |
| 22 | 6.1 | Repository | Database | [6.1] updateDraftAndAudit() | đồng bộ | alt [yêu cầu sửa] |
| 23 | 6.1 | Database | Repository | [6.1] traDraftDaCapNhat() | trả về | alt [yêu cầu sửa] |
| 24 | 6.1 | Repository | Service | [6.1] traChangeRequestResult() | trả về | alt [yêu cầu sửa] |
| 25 | 7 | Service | Service | [7] finalizeDerivedData(version_id) | tự gọi | opt [Duyệt đã commit] |
| 26 | 8 | Service | Controller/API | [8] traApprovalOrChangeRequestResult() | trả về | alt [thành công/lỗi] |
| 27 | 8 | Controller/API | Giao diện xét duyệt | [8] traResponse() | trả về | alt [thành công/lỗi] |
| 28 | 8 | Giao diện xét duyệt | Admin | [8] hienThiKetQuaVaTrangThaiDongBo() | trả về | alt [thành công/lỗi] |

### 4c. Số liệu

N = 13 (như Phần 3c), M = 28 message, F = 4 fragment (opt đối chiếu nguồn; alt lựa chọn/kết quả; alt commit; opt dữ liệu dẫn xuất), L = 6 lifeline. Bảng message mô tả một luồng duyệt cá nhân và các opt/alt; duyệt nhóm là operand thay thế ở message 21-28, không triển khai thành các vòng lặp từng ca để giữ sequence vừa trang.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC23 - Xét duyệt ca kiểm thử của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Dùng PlantUML, nhãn Tiếng Việt. Ưu tiên bố cục gọn, phù hợp trang luận văn: hai swimlane Người dùng và Hệ thống; hành động ngắn, mỗi nhánh có guard dễ đọc; không đưa chi tiết repository/database vào Activity.

ĐẶC TẢ ĐÃ CHỐT
Mô tả: Admin có quyền xét duyệt một hoặc nhiều ca kiểm thử IN_REVIEW; ca được duyệt tạo version chính thức; duyệt nhóm nguyên tử.
Tiền điều kiện: Đã đăng nhập, có quyền testcase.review/testcase.approve, draft thuộc dự án, trạng thái và revision còn hiện hành; tuân thủ xét duyệt độc lập.
Hậu điều kiện: Thành công tạo version, draft APPROVED và audit. Duyệt nhóm commit toàn bộ hoặc không commit ca nào. Lỗi không đổi version. Dữ liệu dẫn xuất có thể ở trạng thái chờ sau commit.
Tác nhân chính: Admin có quyền xét duyệt. Tác nhân phụ: Không có.
Luồng chính: (1) Chọn ca IN_REVIEW. (2) Hệ thống tải nội dung, revision, liên kết, nguồn và đối chiếu. (3) Admin đọc và đối chiếu. (4) Chọn phê duyệt, ghi chú tùy chọn, xác nhận. (5) Hệ thống kiểm tra quyền độc lập, trạng thái/revision, bước, nguồn, lint và trùng. (6) Tạo version và audit trong giao dịch. (7) Hoàn tất hoặc đánh dấu chờ dữ liệu dẫn xuất. (8) Hiển thị kết quả.
Thay thế: 3.1 Nếu ca AI cần đối chiếu, xem nguồn, xác nhận xem căn cứ hiện có và quay lại bước 4. 4.1 Duyệt nhóm: kiểm tra mọi ca và chỉ commit khi tất cả hợp lệ. 4.1.1 Hủy thì kết thúc không thay đổi dữ liệu.
Ngoại lệ: Không quyền/không tìm thấy; trạng thái hoặc revision/nguồn thay đổi; thiếu bước, nguồn, lý do trùng hoặc lint blocker; conflict version; lỗi giao dịch. Báo kết quả phù hợp, không duyệt một phần. Dữ liệu dẫn xuất lỗi sau commit được ghi là chờ xử lý.

BẢNG NODE
I Initial Hệ thống: Bắt đầu, người dùng đã xác thực
A1 Action Người dùng: [1] Chọn ca chờ duyệt
A2 Action Hệ thống: [2] Tải nội dung và revision
D1 Decision Hệ thống: Ca tồn tại và người dùng có quyền?
A3 Action Hệ thống: [2.1] Báo lỗi truy cập hoặc không tìm thấy
A4 Action Người dùng: [3] Đọc và đối chiếu nội dung
D2 Decision Người dùng: Có cần đối chiếu lại nguồn AI?
A5 Action Hệ thống: [3.1.1] Hiển thị nguồn và đối chiếu
A6 Action Người dùng: [3.1.2] Xem căn cứ hiện có và quay lại duyệt
M1 Merge Hệ thống: Tiếp tục xét duyệt
D3 Decision Người dùng: Duyệt cá nhân, duyệt nhóm, yêu cầu sửa hay hủy?
A7 Action Người dùng: [4.1] Chọn nhóm và xác nhận duyệt
A8 Action Hệ thống: [5] Kiểm tra điều kiện và revision
D4 Decision Hệ thống: Tất cả điều kiện xét duyệt hợp lệ?
A9 Action Hệ thống: [5.1] Trả finding và lỗi xét duyệt
A10 Action Hệ thống: [6] Tạo version và ghi quyết định duyệt
D5 Decision Hệ thống: Giao dịch đã commit?
A11 Action Hệ thống: [6.1] Báo lỗi lưu và rollback
A12 Action Hệ thống: [7] Hoàn tất dữ liệu dẫn xuất
D6 Decision Hệ thống: Dữ liệu dẫn xuất đã hoàn tất?
A13 Action Hệ thống: [7.1] Đánh dấu chờ đồng bộ dẫn xuất
A14 Action Hệ thống: [8] Trả kết quả và hiển thị version
A15 Action Người dùng: [4.1.1] Hủy xác nhận duyệt nhóm
A16 Action Người dùng: [4.2] Nhập lý do và xác nhận yêu cầu chỉnh sửa
A17 Action Hệ thống: [4.2.1] Trả draft về DRAFT và ghi audit
F1 Final Hệ thống: Kết thúc thành công
F2 Final Hệ thống: Kết thúc không thay đổi dữ liệu

BẢNG CẠNH
I -> A1 [UC bắt đầu]; A1 -> A2 [Đã chọn ca]; A2 -> D1 [Đã tải kết quả]; D1 -> A4 [Tồn tại và có quyền]; D1 -> A3 [Không quyền/không tìm thấy]; A3 -> F2 [Lỗi đã hiển thị]; A4 -> D2 [Đã đọc]; D2 -> A5 [Ca AI cần đối chiếu]; D2 -> M1 [Không cần đối chiếu]; A5 -> A6 [Nguồn đã hiển thị]; A6 -> M1 [Đã xem căn cứ hiện có]; M1 -> D3 [Tiếp tục]; D3 -> A8 [Duyệt cá nhân]; D3 -> A7 [Duyệt nhóm]; D3 -> A15 [Hủy]; D3 -> A16 [Yêu cầu chỉnh sửa]; A7 -> A8 [Đã xác nhận]; A15 -> F2 [Không ghi dữ liệu]; A8 -> D4 [Kiểm tra xong]; D4 -> A10 [Hợp lệ]; D4 -> A9 [Có finding/conflict]; A9 -> F2 [Lỗi đã trả]; A10 -> D5 [Đã thử commit]; D5 -> A12 [Commit thành công]; D5 -> A11 [Commit thất bại]; A11 -> F2 [Đã rollback]; A12 -> D6 [Đã xử lý dẫn xuất]; D6 -> A14 [Hoàn tất]; D6 -> A13 [Còn chờ]; A13 -> A14 [Đã ghi trạng thái chờ]; A14 -> F1 [Đã hiển thị kết quả].

YÊU CẦU: Giữ nguyên swimlane, guards và nhãn số bước. Bố trí nhánh duyệt nhóm trong cùng nhánh nghiệp vụ, không nhân bản từng thao tác cho từng ca. Không tự thêm yêu cầu trả DRAFT. Đầu ra phải gọn và đọc được khi đặt trong trang luận văn.
ĐỐI CHIẾU: 16 Action, 6 Decision, 36 cạnh. Báo nếu số node/cạnh không khớp.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC23 - Xét duyệt ca kiểm thử của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Dùng PlantUML, nhãn Tiếng Việt. Bố cục ngang vừa trang luận văn; chỉ giữ lifeline nghiệp vụ và lớp xử lý cần thiết; gom trao đổi nội bộ thành lời gọi service có tên rõ. Dùng alt/opt cho nhánh, tránh message lặp theo từng bản ghi.

ĐẶC TẢ ĐÃ CHỐT
Mô tả: Admin có quyền xét duyệt ca kiểm thử IN_REVIEW; phê duyệt tạo version chính thức. Duyệt nhóm là nguyên tử.
Tiền điều kiện: Đã đăng nhập, quyền xét duyệt hợp lệ, draft thuộc dự án và revision còn hiện hành.
Hậu điều kiện: Thành công lưu version, trạng thái APPROVED và audit. Lỗi kiểm tra/commit không tạo duyệt một phần. Dữ liệu dẫn xuất có thể chờ xử lý sau commit.
Tác nhân chính: Admin. Tác nhân phụ: Không có.
Luồng chính: Chọn ca; tải ngữ cảnh xét duyệt; đối chiếu; xác nhận; kiểm quyền, revision, nguồn, bước, lint và trùng; commit version; trả kết quả.
Thay thế: Ca AI chưa đối chiếu thì xem căn cứ hiện có rồi quay lại xác nhận. Duyệt nhóm là operand thay cho duyệt cá nhân và chỉ commit toàn bộ nếu hợp lệ. Hủy không gửi mutation.
Ngoại lệ: Quyền/ca không hợp lệ, revision/nguồn đổi, validation hoặc conflict, lỗi lưu; hiển thị lỗi. Dữ liệu dẫn xuất chậm thì báo trạng thái chờ sau commit.

LIFELINE trái sang phải: Admin; Giao diện xét duyệt; Controller/API; Service; Repository; Database.

MESSAGE THEO THỨ TỰ
1 [1] chonCaChoDuyet(id): Admin -> Giao diện
2 [2] getReviewContext(id): Giao diện -> Controller/API
3 [2] loadReviewContext(id): Controller/API -> Service
4 [2] findDraftAndSources(id): Service -> Repository
5 [2] selectDraftSourcesRevision(id): Repository -> Database
6 [2] traDraftNguonRevision(): Database -> Repository (return)
7 [2] traReviewContext(): Repository -> Service (return)
8 [2] traReviewContextHoacLoi(): Service -> Controller/API (return)
9 [2] traReviewResponse(): Controller/API -> Giao diện (return)
10 [2] hienThiNoiDungNguonVaFinding(): Giao diện -> Admin (return)
11 [3.1] xemCanCuAI(): Admin -> Giao diện (opt [Ca AI cần đối chiếu])
12 [3.1] hienThiCanCuDaCo(): Giao diện -> Admin (return, opt)
13 [4] chonQuyetDinh(note, expected_revision): Admin -> Giao diện
14 [5] guiQuyetDinh(payload): Giao diện -> Controller/API
15 [5] processReviewDecision(payload): Controller/API -> Service
16 [5] validatePermissionStateRevisionAndReview(): Service -> Service (self-call, alt [đủ điều kiện/lỗi])
17 [6] publishApprovedVersion(expected_revision): Service -> Repository (alt [duyệt cá nhân/duyệt nhóm])
18 [6] transactionInsertVersionUpdateDraftAndAudit(): Repository -> Database
19 [6] traCommitHoacRollback(): Database -> Repository (return, alt [commit/lỗi])
20 [6] traPublicationResult(): Repository -> Service (return)
21 [6.1] transitionInReviewToDraft(reason_code, note, expected_revision): Service -> Repository (alt [yêu cầu chỉnh sửa])
22 [6.1] updateDraftAndAudit(): Repository -> Database
23 [6.1] traDraftDaCapNhat(): Database -> Repository (return)
24 [6.1] traChangeRequestResult(): Repository -> Service (return)
25 [7] finalizeDerivedData(version_id): Service -> Service (self-call, opt [duyệt đã commit])
26 [8] traApprovalOrChangeRequestResult(): Service -> Controller/API (return)
27 [8] traResponse(): Controller/API -> Giao diện (return)
28 [8] hienThiKetQuaVaTrangThaiDongBo(): Giao diện -> Admin (return)

YÊU CẦU: Dùng activation bars. Mọi request đi qua lớp kế tiếp, không gọi tắt. Có return cho lời gọi đồng bộ. Dùng alt [duyệt cá nhân] / [duyệt nhóm, tất cả hợp lệ] / [yêu cầu chỉnh sửa, chuyển DRAFT] / [có lỗi, không commit]; opt [đối chiếu AI] và opt [dữ liệu dẫn xuất chờ]. Có nhánh request changes, return DRAFT và thông báo kết quả. Giữ sơ đồ thoáng, không ép toàn bộ message chiếm chiều ngang không đọc được; có thể chia operand dài theo chiều dọc.
ĐỐI CHIẾU: 6 lifeline, 28 message, 4 fragment. Báo số thực tế.
```

## TỰ KIỂM TRA UC23

- [x] Đã tách hành vi đã xác minh khỏi yêu cầu trả DRAFT chưa được xác nhận.
- [x] Đã mô tả duyệt nhóm nguyên tử và các điều kiện nguồn/revision/độc lập.
- [x] Activity có hai final, guard và nhánh lỗi; 16 Action, 6 Decision, 36 cạnh.
- [x] Sequence có 6 lifeline, 28 message, các return và alt/opt.
- [x] Prompt chép đủ đặc tả cùng node/cạnh hoặc message; ưu tiên sơ đồ gọn, phù hợp luận văn.


## Bảng theo dõi sau UC23

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

# UC24 - Quản lý phiên bản ca kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| Tiền điều kiện | MƠ HỒ | Yêu cầu có phiên bản chính thức phù hợp cho xem lịch sử, nhưng chưa chắc cần thiết khi xem danh sách; mã nguồn cho phép tải lịch sử theo test case. | Nêu ca kiểm thử phải tồn tại; để thao tác tạo draft yêu cầu có phiên bản hiện hành. Người dùng cần quyền `testcase.version.read` hoặc `testcase.version.create` theo thao tác. |
| 1-2 | THIẾU | Chưa nói rõ tải lịch sử theo thứ tự nào, số lượng tối đa và quyền truy cập. | Ghi mã nguồn trả lịch sử tối đa 500 phiên bản, sắp số phiên bản giảm dần; lỗi quyền hoặc không tìm thấy kết thúc thất bại. |
| 3.1 | THIẾU | “Xem lịch sử” chưa nêu kiểm tra chọn version, hoặc giới hạn dữ liệu nguồn. | Bổ sung chọn version trong danh sách; màn hình hiển thị chi tiết và nguồn/citation nếu có, theo dữ liệu trả về. |
| 3 | THIẾU | Có API xem khác biệt giữa hai phiên bản nhưng UC gốc bỏ qua chức năng này. | Thêm nhánh xem khác biệt, yêu cầu hai version thuộc cùng test case; kết quả thể hiện các trường thay đổi. |
| 5-9 | THIẾU | Lý do đổi bắt buộc, phiên bản hiện hành và expected ID chưa được kiểm tra rõ; có thể phát sinh xung đột nếu ca vừa được cập nhật. | Bổ sung validate lý do, quyền, ID version hiện hành; stale version trả conflict, không tạo draft từ dữ liệu cũ. |
| 8 | MƠ HỒ | “Sao chép nội dung” không nêu draft kế thừa những trường nào hay giữ nguyên version đã phát hành. | Mô tả tạo draft cùng test case key, parent_version_id trỏ version nguồn và change_reason; version chính thức được giữ nguyên. |
| 10 | MÂU THUẪN | UC24 nói tiếp tục chỉnh sửa theo UC21 nhưng chưa phân định điểm kết thúc; phần này có thể bị hiểu là UC24 tự chỉnh sửa. | Xem UC21 là UC mở rộng độc lập; kết thúc UC24 khi draft mới được hiển thị, chỉnh sửa tiếp thuộc UC21. |
| 6.1 | THIẾU | Nhánh hủy mới nói đóng hộp thoại, chưa nói quay lại đâu. | Ghi đóng hộp thoại, không gọi tạo draft và quay lại bước 3. |
| Ngoại lệ | THIẾU | Chưa có lỗi quyền, dữ liệu bắt buộc, không tìm thấy version, sai cặp version, lỗi lưu/CSDL và hủy. | Bổ sung nhánh cụ thể; không tạo draft nếu thao tác thất bại. |
| Tác nhân / quản lý | MƠ HỒ | Tester là tác nhân nghiệp vụ nhưng chưa gắn permission; UC tên “Quản lý” có thể bị hiểu phải có CRUD tổng quát. | Giữ Tester; gắn quyền thao tác. Không thêm sửa/xóa version chính thức vì phiên bản là bản ghi bất biến. |

Đã kiểm: **4 điểm rẽ, 5 nhánh, 8 tình huống lỗi/biên**; rà quyền, tính tồn tại, cặp version, lý do bắt buộc, xung đột current version, lưu/CSDL, hậu điều kiện và ranh giới UC21. Không thêm login/session management. CRUD sửa/xóa version chính thức không áp dụng theo thiết kế bất biến.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Tester xem lịch sử, xem chi tiết hoặc so sánh các phiên bản ca kiểm thử; có thể tạo bản nháp kế tiếp từ phiên bản đang hiện hành để sửa tiếp.

**Tiền điều kiện:** Người dùng đã xác thực và có quyền phù hợp với thao tác. Test case tồn tại trong dự án. Muốn tạo draft, test case phải có current version hợp lệ và người dùng có `testcase.version.create`.

**Hậu điều kiện:**
- Xem lịch sử/chi tiết/khác biệt: trả dữ liệu tương ứng, không thay đổi version.
- Tạo draft: một draft mới cùng test case key được tạo từ current version; ghi parent version và change reason. Phiên bản chính thức không bị ghi đè.
- Thất bại/hủy: không tạo draft hay sửa version; trả lỗi hoặc quay lại màn hình hiện tại.

**Tác nhân chính:** Tester có quyền quản lý phiên bản.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang phiên bản của ca kiểm thử. | |
| 2 | | Kiểm tra `testcase.version.read`, tải tối đa 500 version theo thứ tự giảm dần và hiển thị lịch sử. |
| 3 | Chọn một version để xem chi tiết hoặc chọn hai version để xem khác biệt. | |
| 4 | | Kiểm tra version được chọn thuộc cùng test case; hiển thị chi tiết/nguồn hoặc danh sách trường khác biệt. |
| 5 | Chọn Tạo bản nháp từ phiên bản hiện hành. | |
| 6 | | Kiểm tra `testcase.version.create`, nạp current version và hiển thị biểu mẫu lý do thay đổi. |
| 7 | Nhập lý do thay đổi và xác nhận tạo bản nháp. | |
| 8 | | Kiểm tra lý do, current version ID và trạng thái phiên bản nguồn. |
| 9 | | Sao chép nội dung cùng liên kết, nguồn và metadata được hỗ trợ sang draft mới; gắn parent version và change reason. |
| 10 | | Trả draft mới, giữ nguyên version chính thức và hiển thị draft. Kết thúc UC24. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Chọn Xem lịch sử, chọn một version trong danh sách và mở chi tiết/nguồn nếu có. | Hiển thị chi tiết version, số version, trường nội dung và căn cứ nguồn sẵn có. Kết thúc UC. |
| 3.2 | Chọn hai version để so sánh. | Tính khác biệt các trường hỗ trợ, hiển thị trước/sau; quay lại bước 3. |
| 7.1 | Hủy biểu mẫu tạo bản nháp. | Đóng biểu mẫu, không gửi yêu cầu tạo draft; quay lại bước 3. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Không có quyền đọc hoặc test case không tồn tại. Hiển thị lỗi truy cập/không tìm thấy; kết thúc thất bại. |
| 4.1 | | Một version không tồn tại hoặc không thuộc test case này. Từ chối chi tiết/so sánh; kết thúc thất bại. |
| 7.2 | | Lý do thay đổi trống, dưới 2 ký tự hoặc quá giới hạn 2000 ký tự; yêu cầu sửa và quay lại bước 7. |
| 8.1 | | Current version đã đổi so với expected ID. Báo xung đột, không tạo từ phiên bản cũ; tải lại và quay lại bước 2. |
| 8.2 | | Không còn version nguồn hợp lệ. Báo không tìm thấy; kết thúc thất bại. |
| 9.1 | | Lỗi khi ghi draft/DB. Báo lỗi và không tuyên bố đã tạo draft; kết thúc thất bại. |

**Giả định / Câu hỏi cần làm rõ**
- “Quản lý phiên bản” ở giao diện có nút so sánh trực tiếp không? API diff đã tồn tại, nhưng chưa đối chiếu trạng thái UI trong phạm vi rà soát này.
- Version history API giới hạn 500 mục; chưa xác định UI có phân trang hay chỉ hiển thị phần trả về.

## PHẦN 3 - PHÂN RÃ ACTIVITY (chưa vẽ)

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---:|---|---|---|
| I | — | Initial | Hệ thống | Bắt đầu khi người dùng đã đăng nhập |
| A1 | 1 | Action | Người dùng | [1] Mở trang phiên bản ca |
| A2 | 2 | Action | Hệ thống | [2] Tải lịch sử theo quyền |
| D1 | 2 | Decision | Hệ thống | Ca tồn tại và có quyền đọc? |
| A3 | 2.1 | Action | Hệ thống | [2.1] Báo lỗi truy cập hoặc không tìm thấy |
| A4 | 3 | Action | Người dùng | [3] Chọn xem chi tiết, so sánh hoặc tạo draft |
| D2 | 3 | Decision | Người dùng | Chọn thao tác nào? |
| A5 | 3.1 | Action | Hệ thống | [3.1] Hiển thị chi tiết version và nguồn |
| A6 | 3.2 | Action | Hệ thống | [3.2] Hiển thị khác biệt hai version |
| A7 | 5 | Action | Hệ thống | [5] Kiểm tra quyền tạo draft và tải current version |
| D3 | 5 | Decision | Hệ thống | Current version còn khớp và tồn tại? |
| A8 | 5.1 | Action | Hệ thống | [5.1] Báo conflict hoặc version không tồn tại |
| A9 | 6 | Action | Hệ thống | [6] Hiển thị biểu mẫu lý do thay đổi |
| A10 | 7 | Action | Người dùng | [7] Nhập lý do và xác nhận tạo draft |
| D4 | 7 | Decision | Người dùng | Xác nhận tạo hay hủy? |
| D5 | 8 | Decision | Hệ thống | Lý do hợp lệ và version còn hiện hành? |
| A11 | 8.1 | Action | Hệ thống | [8.1] Hiển thị lỗi kiểm tra hoặc conflict |
| A12 | 9 | Action | Hệ thống | [9] Tạo draft kế thừa version nguồn |
| D6 | 9 | Decision | Hệ thống | Ghi draft thành công? |
| A13 | 9.1 | Action | Hệ thống | [9.1] Báo lỗi lưu |
| A14 | 10 | Action | Hệ thống | [10] Hiển thị draft mới |
| A15 | 7.1 | Action | Người dùng | [7.1] Hủy tạo draft |
| F1 | — | Final | Hệ thống | Kết thúc thành công hoặc chỉ xem |
| F2 | — | Final | Hệ thống | Kết thúc thất bại hoặc hủy, không đổi version |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | UC bắt đầu |
| A1 | A2 | Đã mở trang |
| A2 | D1 | Tải xong |
| D1 | A4 | Có quyền và ca tồn tại |
| D1 | A3 | Thiếu quyền hoặc không tìm thấy |
| A3 | F2 | Lỗi đã hiển thị |
| A4 | D2 | Đã chọn thao tác |
| D2 | A5 | Xem chi tiết |
| D2 | A6 | So sánh hai version |
| D2 | A7 | Tạo draft từ current version |
| A5 | F1 | Chi tiết đã hiển thị |
| A6 | F1 | Khác biệt đã hiển thị |
| A7 | D3 | Đã tải current version |
| D3 | A9 | ID khớp và version tồn tại |
| D3 | A8 | ID không khớp hoặc version không tồn tại |
| A8 | F2 | Lỗi đã hiển thị |
| A9 | D4 | Form đã hiển thị |
| D4 | A10 | Người dùng xác nhận |
| D4 | A15 | Người dùng hủy |
| A10 | D5 | Đã nhập lý do và xác nhận |
| D5 | A12 | Lý do hợp lệ và current version còn hiện hành |
| D5 | A11 | Lý do sai hoặc current version thay đổi |
| A11 | A9 | Có thể sửa lý do hoặc tải lại form |
| A15 | F2 | Không gửi yêu cầu ghi |

| A12 | D6 | Đã thử ghi draft |
| D6 | A14 | Ghi thành công |
| D6 | A13 | Ghi thất bại |
| A13 | F2 | Lỗi đã hiển thị |
| A14 | F1 | Draft mới đã hiển thị |

### 3c. Số liệu

N = 11 ô đặc tả được thể hiện (8 chính, 3 thay thế); M = 15 Action; D = 6 Decision; E = 29 cạnh. Action xem chi tiết và so sánh kết thúc độc lập, không nhập vào luồng tạo draft.

## PHẦN 4 - PHÂN RÃ SEQUENCE (chưa vẽ)

### 4a. Lifeline trái sang phải

Tester → Giao diện phiên bản → Controller/API → Service → Repository → Database. Hệ thống ngoài: không có.

### 4b. Bảng message

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện phiên bản | [1] moLichSu(test_case_id) | đồng bộ | chính |
| 2 | 2 | Giao diện phiên bản | Controller/API | [2] listTestCaseVersions(id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listTestCaseVersions(id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] listVersionsForCase(id, 500) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectVersions(order=desc, limit=500) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traVersions() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traHistory() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traHistoryHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện phiên bản | [2] traResponse() | trả về | chính |
| 10 | 2 | Giao diện phiên bản | Tester | [2] hienThiLichSu() | trả về | chính |
| 11 | 3.1 | Tester | Giao diện phiên bản | [3.1] chonVersion(version_id) | đồng bộ | alt [chi tiết/so sánh/tạo draft] |
| 12 | 4 | Giao diện phiên bản | Controller/API | [4] getVersionDetail(id) | đồng bộ | alt [chi tiết] |
| 13 | 4 | Controller/API | Service | [4] requireVersionReadPermission(id) | đồng bộ | alt [chi tiết] |
| 14 | 4 | Service | Repository | [4] findVersion(id) | đồng bộ | alt [chi tiết] |
| 15 | 4 | Repository | Database | [4] selectVersion(id) | đồng bộ | alt [chi tiết] |
| 16 | 4 | Database | Repository | [4] traVersion() | trả về | alt [chi tiết] |
| 17 | 4 | Repository | Service | [4] traVersion() | trả về | alt [chi tiết] |
| 18 | 4 | Service | Controller/API | [4] traDetailHoacNotFound() | trả về | alt [chi tiết] |
| 19 | 4 | Controller/API | Giao diện phiên bản | [4] traResponse() | trả về | alt [chi tiết] |
| 20 | 4 | Giao diện phiên bản | Tester | [4] hienThiVersionVaNguon() | trả về | alt [chi tiết] |
| 21 | 3.2 | Tester | Giao diện phiên bản | [3.2] chonSoSanh(version_a, version_b) | đồng bộ | alt [so sánh] |
| 22 | 4.1 | Giao diện phiên bản | Controller/API | [4.1] diffTestCaseVersions(a, b) | đồng bộ | alt [so sánh] |
| 23 | 4.1 | Controller/API | Service | [4.1] diffTestCaseVersionRecords(a, b) | đồng bộ | alt [so sánh] |
| 24 | 4.1 | Service | Repository | [4.1] listSelectedCaseVersions(a, b) | đồng bộ | alt [so sánh] |
| 25 | 4.1 | Repository | Database | [4.1] selectVersionsForSameCase(a, b) | đồng bộ | alt [so sánh] |
| 26 | 4.1 | Database | Repository | [4.1] traHaiVersion() | trả về | alt [so sánh] |
| 27 | 4.1 | Repository | Service | [4.1] traHaiVersion() | trả về | alt [so sánh] |
| 28 | 4.1 | Service | Controller/API | [4.1] traFieldDifferencesHoacLoi() | trả về | alt [so sánh] |
| 29 | 4.1 | Controller/API | Giao diện phiên bản | [4.1] traResponse() | trả về | alt [so sánh] |
| 30 | 4.1 | Giao diện phiên bản | Tester | [4.1] hienThiKhacBiet() | trả về | alt [so sánh] |
| 31 | 5 | Tester | Giao diện phiên bản | [5] taoDraftMoi() | đồng bộ | alt [tạo draft/hủy] |
| 32 | 6 | Giao diện phiên bản | Controller/API | [6] createTestCaseVersionDraft(payload) | đồng bộ | alt [tạo draft/hủy] |
| 33 | 6 | Controller/API | Service | [6] createTestCaseVersionDraftRecord(id, payload) | đồng bộ | alt [tạo draft/hủy] |
| 34 | 8 | Service | Service | [8] validateReasonAndExpectedCurrentVersion() | tự gọi | alt [hợp lệ/conflict] |
| 35 | 9 | Service | Repository | [9] createDraftFromVersion(parent_version_id, reason) | đồng bộ | alt [ghi thành công/lỗi] |
| 36 | 9 | Repository | Database | [9] insertDraftAndAudit() | đồng bộ | alt [ghi thành công/lỗi] |
| 37 | 9 | Database | Repository | [9] traDraftMoi() | trả về | alt [ghi thành công/lỗi] |
| 38 | 9 | Repository | Service | [9] traCreatedDraft() | trả về | alt [ghi thành công/lỗi] |
| 39 | 10 | Service | Controller/API | [10] traDraftResponse() | trả về | alt [ghi thành công/lỗi] |
| 40 | 10 | Controller/API | Giao diện phiên bản | [10] traResponse() | trả về | alt [ghi thành công/lỗi] |
| 41 | 10 | Giao diện phiên bản | Tester | [10] hienThiDraftMoi() | trả về | alt [ghi thành công/lỗi] |

### 4c. Số liệu

N = 11 (như Phần 3c), M = 41 message, F = 4 fragment (alt lịch sử/chi tiết/so sánh/tạo draft; alt thành công/lỗi khi tải; alt validate; alt ghi/hủy), L = 6 lifeline. Kịch bản vẽ giữ các nhánh chi tiết, compare và create draft trong alt; không gọi trực tiếp giữa các lớp.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC24 - Quản lý phiên bản ca kiểm thử của hệ thống Veriq, dùng Visual Paradigm AI Chatbot, định dạng PlantUML, nhãn Tiếng Việt. Sơ đồ phù hợp trang luận văn: hai swimlane Người dùng và Hệ thống, bố cục thoáng, không đưa lời gọi kỹ thuật vào node.

ĐẶC TẢ ĐÃ CHỐT
Mô tả: Tester xem lịch sử, chi tiết, khác biệt giữa các version; có thể tạo draft mới từ version hiện hành để tiếp tục chỉnh sửa ở UC21.
Tiền điều kiện: Đã xác thực, có permission testcase.version.read/create thích hợp; test case tồn tại. Tạo draft cần current version hợp lệ.
Hậu điều kiện: Xem/so sánh không thay đổi dữ liệu. Tạo draft lưu bản sao từ current version, parent version và change reason; không ghi đè version chính thức. Lỗi/hủy không tạo draft.
Tác nhân chính: Tester. Tác nhân phụ: Không có.
Luồng chính: (1) Mở lịch sử. (2) Hệ thống kiểm quyền, tải tối đa 500 version mới nhất theo thứ tự giảm dần. (3) Chọn xem chi tiết, so sánh hoặc tạo draft. (4) Hệ thống hiển thị kết quả tương ứng hoặc biểu mẫu change reason. (5) Người dùng nhập lý do và xác nhận. (6) Hệ thống kiểm tra quyền, lý do và expected current version. (7) Tạo draft kế thừa nội dung/liên kết/nguồn, lưu parent version và reason. (8) Hiển thị draft.
Thay thế: 3.1 Xem chi tiết version và nguồn nếu có, kết thúc. 3.2 Chọn hai version cùng ca để xem khác biệt, kết thúc. 5.1 Hủy biểu mẫu, quay lại danh sách.
Ngoại lệ: Thiếu quyền, không tìm thấy ca/version, version so sánh không cùng ca, reason không hợp lệ, current version đã đổi, lỗi ghi DB; không ghi version mới khi thất bại.

BẢNG NODE
I Initial Hệ thống: Bắt đầu, người dùng đã đăng nhập
A1 Action Người dùng: [1] Mở trang phiên bản ca
A2 Action Hệ thống: [2] Tải lịch sử theo quyền
D1 Decision Hệ thống: Ca tồn tại và có quyền đọc?
A3 Action Hệ thống: [2.1] Báo lỗi truy cập hoặc không tìm thấy
A4 Action Người dùng: [3] Chọn xem chi tiết, so sánh hoặc tạo draft
D2 Decision Người dùng: Chọn thao tác nào?
A5 Action Hệ thống: [3.1] Hiển thị chi tiết version và nguồn
A6 Action Hệ thống: [3.2] Hiển thị khác biệt hai version
A7 Action Hệ thống: [5] Kiểm quyền tạo draft và tải current version
D3 Decision Hệ thống: Current version tồn tại và khớp expected ID?
A8 Action Hệ thống: [5.1] Báo conflict hoặc version không tồn tại
A9 Action Hệ thống: [6] Hiển thị form lý do
A10 Action Người dùng: [7] Nhập lý do và xác nhận
D4 Decision Người dùng: Xác nhận tạo hay hủy?
D5 Decision Hệ thống: Lý do hợp lệ và version còn hiện hành?
A11 Action Hệ thống: [8.1] Báo lỗi lý do hoặc conflict
A12 Action Hệ thống: [9] Tạo draft từ version nguồn
D6 Decision Hệ thống: Ghi draft thành công?
A13 Action Hệ thống: [9.1] Báo lỗi lưu
A14 Action Hệ thống: [10] Hiển thị draft mới
A15 Action Người dùng: [7.1] Hủy tạo draft
F1 Final Hệ thống: Kết thúc xem/so sánh/tạo draft thành công
F2 Final Hệ thống: Kết thúc thất bại hoặc hủy, không đổi version

BẢNG CẠNH
I -> A1 [Bắt đầu]; A1 -> A2 [Đã mở trang]; A2 -> D1 [Tải hoàn tất]; D1 -> A4 [Có quyền và ca tồn tại]; D1 -> A3 [Thiếu quyền/không tìm thấy]; A3 -> F2 [Lỗi hiển thị]; A4 -> D2 [Đã chọn]; D2 -> A5 [Xem chi tiết]; D2 -> A6 [So sánh]; D2 -> A7 [Tạo draft]; A5 -> F1 [Chi tiết hiển thị]; A6 -> F1 [Khác biệt hiển thị]; A7 -> D3 [Đã tải current version]; D3 -> A9 [ID khớp, version còn tồn tại]; D3 -> A8 [Conflict hoặc không tìm thấy]; A8 -> F2 [Lỗi hiển thị]; A9 -> D4 [Form hiển thị]; D4 -> A10 [Xác nhận]; D4 -> A15 [Hủy]; A10 -> D5 [Đã nhập lý do]; D5 -> A12 [Lý do hợp lệ, current version khớp]; D5 -> A11 [Lý do sai hoặc current version đổi]; A11 -> A9 [Sửa lý do hoặc tải lại]; A15 -> F2 [Không gửi mutation]; A12 -> D6 [Đã thử lưu]; D6 -> A14 [Ghi thành công]; D6 -> A13 [Ghi thất bại]; A13 -> F2 [Lỗi hiển thị]; A14 -> F1 [Draft đã hiển thị].

YÊU CẦU: Giữ guards và số bước; mọi Decision có ít nhất hai nhánh, không node treo. Tách chi tiết, so sánh và tạo draft thành ba nhánh dễ đọc. Không thêm thao tác sửa/xóa version chính thức.
ĐỐI CHIẾU: 15 Action, 6 Decision, 29 cạnh. Báo số thực tế.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC24 - Quản lý phiên bản ca kiểm thử của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Dùng PlantUML, nhãn Tiếng Việt. Bố cục ngang vừa trang luận văn. Dùng alt cho xem chi tiết/so sánh/tạo draft và alt cho lỗi; tránh lặp message theo từng thuộc tính.

ĐẶC TẢ ĐÃ CHỐT
Mô tả: Tester xem lịch sử, chi tiết hoặc so sánh version và tạo draft mới từ current version.
Tiền điều kiện: Đã xác thực; có testcase.version.read hoặc testcase.version.create; test case tồn tại. Tạo draft đòi current version hợp lệ.
Hậu điều kiện: Lịch sử/so sánh chỉ đọc. Draft mới kế thừa version nguồn, parent_version_id, change reason; version chính thức không đổi. Lỗi/hủy không tạo draft.
Tác nhân chính: Tester. Tác nhân phụ: Không có.
Luồng chính: Tải lịch sử, chọn nhánh xem chi tiết/so sánh/tạo draft. Nhánh tạo draft kiểm permission, expected current version và reason, tạo bản sao draft rồi trả giao diện.
Thay thế: Chi tiết gồm nguồn nếu có. Compare yêu cầu hai version cùng test case và trả trường khác biệt. Hủy form không gửi mutation.
Ngoại lệ: Không quyền, không tìm thấy version, hai version sai phạm vi, current version stale, reason không hợp lệ hoặc lỗi DB.

LIFELINE trái sang phải: Tester; Giao diện phiên bản; Controller/API; Service; Repository; Database.

DANH SÁCH MESSAGE (giữ nguyên thứ tự, nội dung và fragment):

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện phiên bản | [1] moLichSu(test_case_id) | đồng bộ | chính |
| 2 | 2 | Giao diện phiên bản | Controller/API | [2] listTestCaseVersions(id) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listTestCaseVersions(id) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] listVersionsForCase(id, 500) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectVersions(order=desc, limit=500) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traVersions() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traHistory() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traHistoryHoacLoi() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện phiên bản | [2] traResponse() | trả về | chính |
| 10 | 2 | Giao diện phiên bản | Tester | [2] hienThiLichSu() | trả về | chính |
| 11 | 3.1 | Tester | Giao diện phiên bản | [3.1] chonVersion(version_id) | đồng bộ | alt [chi tiết/so sánh/tạo draft] |
| 12 | 4 | Giao diện phiên bản | Controller/API | [4] getVersionDetail(id) | đồng bộ | alt [chi tiết] |
| 13 | 4 | Controller/API | Service | [4] requireVersionReadPermission(id) | đồng bộ | alt [chi tiết] |
| 14 | 4 | Service | Repository | [4] findVersion(id) | đồng bộ | alt [chi tiết] |
| 15 | 4 | Repository | Database | [4] selectVersion(id) | đồng bộ | alt [chi tiết] |
| 16 | 4 | Database | Repository | [4] traVersion() | trả về | alt [chi tiết] |
| 17 | 4 | Repository | Service | [4] traVersion() | trả về | alt [chi tiết] |
| 18 | 4 | Service | Controller/API | [4] traDetailHoacNotFound() | trả về | alt [chi tiết] |
| 19 | 4 | Controller/API | Giao diện phiên bản | [4] traResponse() | trả về | alt [chi tiết] |
| 20 | 4 | Giao diện phiên bản | Tester | [4] hienThiVersionVaNguon() | trả về | alt [chi tiết] |
| 21 | 3.2 | Tester | Giao diện phiên bản | [3.2] chonSoSanh(version_a, version_b) | đồng bộ | alt [so sánh] |
| 22 | 4.1 | Giao diện phiên bản | Controller/API | [4.1] diffTestCaseVersions(a, b) | đồng bộ | alt [so sánh] |
| 23 | 4.1 | Controller/API | Service | [4.1] diffTestCaseVersionRecords(a, b) | đồng bộ | alt [so sánh] |
| 24 | 4.1 | Service | Repository | [4.1] listSelectedCaseVersions(a, b) | đồng bộ | alt [so sánh] |
| 25 | 4.1 | Repository | Database | [4.1] selectVersionsForSameCase(a, b) | đồng bộ | alt [so sánh] |
| 26 | 4.1 | Database | Repository | [4.1] traHaiVersion() | trả về | alt [so sánh] |
| 27 | 4.1 | Repository | Service | [4.1] traHaiVersion() | trả về | alt [so sánh] |
| 28 | 4.1 | Service | Controller/API | [4.1] traFieldDifferencesHoacLoi() | trả về | alt [so sánh] |
| 29 | 4.1 | Controller/API | Giao diện phiên bản | [4.1] traResponse() | trả về | alt [so sánh] |
| 30 | 4.1 | Giao diện phiên bản | Tester | [4.1] hienThiKhacBiet() | trả về | alt [so sánh] |
| 31 | 5 | Tester | Giao diện phiên bản | [5] taoDraftMoi() | đồng bộ | alt [tạo draft/hủy] |
| 32 | 6 | Giao diện phiên bản | Controller/API | [6] createTestCaseVersionDraft(payload) | đồng bộ | alt [tạo draft/hủy] |
| 33 | 6 | Controller/API | Service | [6] createTestCaseVersionDraftRecord(id, payload) | đồng bộ | alt [tạo draft/hủy] |
| 34 | 8 | Service | Service | [8] validateReasonAndExpectedCurrentVersion() | tự gọi | alt [hợp lệ/conflict] |
| 35 | 9 | Service | Repository | [9] createDraftFromVersion(parent_version_id, reason) | đồng bộ | alt [ghi thành công/lỗi] |
| 36 | 9 | Repository | Database | [9] insertDraftAndAudit() | đồng bộ | alt [ghi thành công/lỗi] |
| 37 | 9 | Database | Repository | [9] traDraftMoi() | trả về | alt [ghi thành công/lỗi] |
| 38 | 9 | Repository | Service | [9] traCreatedDraft() | trả về | alt [ghi thành công/lỗi] |
| 39 | 10 | Service | Controller/API | [10] traDraftResponse() | trả về | alt [ghi thành công/lỗi] |
| 40 | 10 | Controller/API | Giao diện phiên bản | [10] traResponse() | trả về | alt [ghi thành công/lỗi] |
| 41 | 10 | Giao diện phiên bản | Tester | [10] hienThiDraftMoi() | trả về | alt [ghi thành công/lỗi] |

YÊU CẦU: Activation bars; không gọi nhảy lớp; mỗi lời gọi đồng bộ có return; guard cho các nhánh chi tiết/so sánh/tạo draft, stale version, invalid reason, hủy và lỗi lưu. Không tạo message xóa/sửa version chính thức.
ĐỐI CHIẾU: 6 lifeline, 41 message, 4 fragment. Báo số thực tế.
```

## TỰ KIỂM TRA UC24

- [x] Kiểm tra quyền đọc/tạo theo từng thao tác và current version expected ID.
- [x] Bổ sung compare version theo API; không bịa khả năng phục hồi/ghi đè version.
- [x] Activity có 15 Action, 6 Decision, 29 cạnh và hai final.
- [x] Sequence có 6 lifeline, 41 message, alt/opt; từng request chính có phản hồi.
- [x] Prompt chép đặc tả và bảng cần vẽ; nhãn ngắn, bố cục luận văn.

# UC25 - Quản lý bộ kiểm thử

## PHẦN 1 - KẾT QUẢ KIỂM TRA ĐẶC TẢ

| Số bước | Loại | Mô tả vấn đề | Cách sửa |
|---|---|---|---|
| 1-2 | THIẾU | Đặc tả chỉ nói hiển thị danh sách, chưa nêu quyền, tìm kiếm/lọc/sắp xếp và giới hạn kết quả. | Ghi permission `testsuite.read`; API hỗ trợ tìm theo tên, lọc loại/trạng thái, sắp xếp một số trường và trả tối đa 500 bộ. |
| 3-8 | THIẾU | Tên và loại có ràng buộc độ dài/enum; danh sách version kiểm tra nhưng chưa rõ có bắt buộc chọn ít nhất một ca hay không. | Nêu tên 2-300 ký tự, loại theo enum; danh sách version có thể rỗng, tối đa 5000 ID; ID được khử trùng và phải tồn tại trong cùng dự án. |
| 3.1 | THIẾU | Chi tiết bộ chưa được mô tả kèm quyền và trường lưu. | Bổ sung tải chi tiết, danh sách version thành viên và trạng thái theo quyền `testsuite.read`. |
| 3.3 | THIẾU | Chưa có optimistic revision, loại trạng thái không cho sửa và lỗi validation khi cập nhật. | Dùng expected revision; bộ APPROVED bất biến, ARCHIVED không sửa; version ID phải hợp lệ trong dự án. |
| 3.4 | MƠ HỒ | “Nhân bản” chưa xác định trạng thái, mã ID mới hoặc quan hệ nguồn. | Mô tả tạo record mới với ID mới, tên hậu tố “bản sao”, source_suite_id, trạng thái ACTIVE, revision 1; bỏ metadata lưu trữ. |
| 3.5 | THIẾU | Lý do lưu trữ và quyền chưa gắn với trạng thái, revision. | Ghi `testsuite.archive`, expected revision, reason 2-2000 ký tự; chuyển status ARCHIVED và lưu người/thời gian/lý do. |
| Ngoại lệ | THIẾU | Chưa bao quát thiếu quyền, dữ liệu sai, ID version không tồn tại/khác dự án, không tìm thấy, conflict revision, bộ đã lưu trữ/đã duyệt và lỗi DB. | Bổ sung nhánh theo từng thao tác; không xóa cứng hoặc báo thành công nếu mutation thất bại. |
| CRUD | THIẾU | UC tên “Quản lý” thiếu tường minh xem danh sách, tìm kiếm/lọc, chi tiết; gốc có tạo/sửa/lưu trữ nhưng dễ hiểu lưu trữ là xóa. | Tách list/search/filter, detail, create, update, clone, archive. Không đặc tả xóa cứng vì không có endpoint delete. |
| Tác nhân / điều kiện | MƠ HỒ | Tester là tác nhân nhưng quyền thực tế chia theo operation; trạng thái đăng nhập chưa được nói. | Ghi Tester đã xác thực và permission cụ thể theo chức năng; không tạo UC quản lý phiên đăng nhập. |

Đã kiểm: **6 điểm rẽ, 8 nhánh, 10 tình huống lỗi/biên**; rà dữ liệu bắt buộc, độ dài/enum, trùng version ID, quyền, project scope, not found, revision conflict, trạng thái immutable/archive, lỗi lưu, hủy, hậu điều kiện và tác nhân. Tạo bộ không bắt buộc có thành viên vì schema cho phép danh sách rỗng. Xóa cứng không được hỗ trợ.

## PHẦN 2 - ĐẶC TẢ ĐÃ CHỐT

**Mô tả:** Tester tạo, tìm, xem, cập nhật, nhân bản hoặc lưu trữ các bộ kiểm thử của dự án. Mỗi bộ chứa metadata và danh sách ID phiên bản ca kiểm thử.

**Tiền điều kiện:** Tester đã xác thực và tham gia dự án; quyền cụ thể phụ thuộc thao tác: `testsuite.read`, `.create`, `.update`, `.clone`, `.archive`. Dự án tồn tại. Thao tác sửa/lưu trữ yêu cầu bộ còn khả dụng và revision phù hợp.

**Hậu điều kiện:**
- Xem/tìm/lọc: trả danh sách hoặc chi tiết, không ghi dữ liệu.
- Tạo: tạo bộ ACTIVE, revision 1, ghi created_by/timestamps và audit.
- Sửa: cập nhật trường được gửi với optimistic revision; version chính thức của từng ca không đổi.
- Nhân bản: tạo bộ mới ACTIVE, revision 1, giữ nguồn `source_suite_id`, nội dung thành viên được sao chép.
- Lưu trữ: status ARCHIVED, lý do, người và thời điểm được lưu; record không bị xóa.
- Hủy hoặc thất bại: không xác nhận mutation thành công; dữ liệu giữ trạng thái trước thao tác nếu ghi không commit.

**Tác nhân chính:** Tester có quyền trên dự án.

**Tác nhân phụ:** Không có.

**Luồng sự kiện chính**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở trang Bộ kiểm thử của dự án. | |
| 2 | | Kiểm tra quyền `testsuite.read`; tải danh sách tối đa 500 kết quả, sắp xếp theo trường được hỗ trợ. |
| 3 | Nhập từ khóa hoặc chọn bộ lọc loại/trạng thái; chọn một bộ hoặc thao tác tạo mới. | |
| 4 | | Áp dụng tìm kiếm tên, lọc loại/trạng thái; hiển thị kết quả. Nếu chọn bộ, tải chi tiết và các phiên bản thành viên. |
| 5 | Chọn Tạo bộ kiểm thử. | |
| 6 | | Hiển thị form tên, loại và danh sách phiên bản ca có thể chọn. |
| 7 | Nhập tên, chọn loại và 0-n phiên bản ca; xác nhận lưu. | |
| 8 | | Kiểm tra quyền `testsuite.create`, tên 2-300 ký tự, enum loại, giới hạn danh sách và project scope của từng version ID. Khử trùng ID lặp. |
| 9 | | Tạo bộ ACTIVE, revision 1; ghi creator, thời gian và audit. |
| 10 | | Hiển thị bộ vừa tạo và cập nhật danh sách. Kết thúc thành công. |

**Luồng sự kiện thay thế**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1 | Chọn một bộ kiểm thử trong danh sách. | Kiểm tra quyền đọc, tải metadata, trạng thái và version thành viên; hiển thị chi tiết. Kết thúc UC. |
| 3.2 | Nhập từ khóa, lọc loại/trạng thái, chọn tiêu chí sắp xếp. | Kiểm tra query, áp dụng các bộ lọc và trả tối đa 500 kết quả; quay lại bước 3. |
| 3.3 | Chọn bộ có thể sửa, đổi tên/loại/thành viên, xác nhận. | Kiểm quyền `testsuite.update`, trạng thái, expected revision và version ID trong dự án; optimistic patch, audit và hiển thị danh sách mới. Kết thúc UC. |
| 3.4 | Chọn Nhân bản bộ. | Kiểm quyền `testsuite.clone`; tạo record mới ACTIVE với ID mới và source_suite_id; bỏ metadata lưu trữ; hiển thị bộ mới. Kết thúc UC. |
| 3.5 | Chọn Lưu trữ, nhập reason và xác nhận. | Kiểm permission `testsuite.archive`, expected revision và reason; chuyển ARCHIVED, ghi người/thời gian/lý do, audit; cập nhật danh sách. Kết thúc UC. |
| 3.6 | Hủy form tạo/sửa hoặc hộp thoại lưu trữ. | Đóng form, không gửi mutation; quay lại danh sách. |

**Luồng sự kiện ngoại lệ**

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 | | Thiếu quyền đọc hoặc dự án không tồn tại/ngoài phạm vi. Từ chối truy cập; kết thúc thất bại. |
| 4.1 | | Bộ không tồn tại hoặc không thuộc dự án. Hiển thị không tìm thấy; kết thúc thất bại. |
| 8.1 | | Tên thiếu/quá dài, loại ngoài enum, danh sách vượt giới hạn hoặc version không tồn tại/khác dự án. Trả lỗi kiểm tra; quay lại form. |
| 8.2 | | Không có quyền tạo. Từ chối mutation; kết thúc thất bại. |
| 9.1 | | DB/audit lỗi khi tạo. Không báo đã tạo; hiển thị lỗi. |
| 3.3.1 | | Bộ APPROVED bất biến, ARCHIVED không sửa, thiếu quyền hoặc revision đã đổi. Không cập nhật; báo lỗi/conflict và yêu cầu tải lại. |
| 3.4.1 | | Thiếu quyền hoặc bộ nguồn không tìm thấy. Không nhân bản; báo lỗi. |
| 3.5.1 | | Reason sai, revision stale, quyền thiếu hoặc DB lỗi. Không xác nhận lưu trữ; báo lỗi. |

**Giả định / Câu hỏi cần làm rõ**
- Schema API cho phép `test_case_version_ids` rỗng, dù UI nghiệp vụ có thể hướng Tester chọn ít nhất một ca. Đặc tả theo API hiện tại, cần xác nhận quy tắc sản phẩm.
- API duyệt bộ APPROVED bất biến, nhưng UC25 không có thao tác phê duyệt; luồng phê duyệt thuộc UC khác nếu có.

## PHẦN 3 - PHÂN RÃ ACTIVITY (chưa vẽ)

### 3a. Bảng node

| ID | Số bước | Loại | Swimlane | Nhãn |
|---|---:|---|---|---|
| I | — | Initial | Hệ thống | Bắt đầu khi Tester đã xác thực |
| A1 | 1 | Action | Người dùng | [1] Mở trang bộ kiểm thử |
| A2 | 2 | Action | Hệ thống | [2] Tải danh sách theo quyền |
| D1 | 2 | Decision | Hệ thống | Có quyền đọc và dự án hợp lệ? |
| A3 | 2.1 | Action | Hệ thống | [2.1] Báo lỗi quyền hoặc dự án |
| A4 | 3 | Action | Người dùng | [3] Tìm, lọc hoặc chọn thao tác |
| A5 | 4 | Action | Hệ thống | [4] Trả danh sách hoặc chi tiết |
| D2 | 4 | Decision | Người dùng | Chọn tạo, sửa, nhân bản, lưu trữ hay chỉ xem? |
| A6 | 6 | Action | Hệ thống | [6] Hiển thị form tạo/sửa/archive |
| A7 | 7 | Action | Người dùng | [7] Nhập dữ liệu và xác nhận |
| A8 | 8 | Action | Hệ thống | [8] Kiểm quyền, trường và version scope |
| D3 | 8 | Decision | Hệ thống | Dữ liệu hợp lệ và revision khớp? |
| A9 | 8.1 | Action | Hệ thống | [8.1] Hiển thị validation hoặc conflict |
| A10 | 9 | Action | Hệ thống | [9] Lưu tạo mới hoặc cập nhật bộ |
| A11 | 9.1 | Action | Hệ thống | [9.1] Báo lỗi DB hoặc audit |
| A12 | 3.3 | Action | Hệ thống | [3.3] Chặn sửa bộ APPROVED/ARCHIVED |
| A13 | 3.4 | Action | Hệ thống | [3.4] Nhân bản bộ sang ACTIVE mới |
| A14 | 3.5 | Action | Hệ thống | [3.5] Lưu trữ với lý do và audit |
| A15 | 3.6 | Action | Người dùng | [3.6] Hủy thao tác |
| D4 | 9.1 | Decision | Hệ thống | Mutation đã ghi thành công? |
| A16 | 10 | Action | Hệ thống | [10] Hiển thị kết quả và làm mới danh sách |
| F1 | — | Final | Hệ thống | Kết thúc thành công hoặc chỉ xem |
| F2 | — | Final | Hệ thống | Kết thúc lỗi/hủy, không mutation thành công |

### 3b. Bảng cạnh

| Từ ID | Đến ID | Guard |
|---|---|---|
| I | A1 | UC bắt đầu |
| A1 | A2 | Trang đã mở |
| A2 | D1 | Đã nhận kết quả tải |
| D1 | A4 | Có quyền và dự án hợp lệ |
| D1 | A3 | Thiếu quyền hoặc dự án sai |
| A3 | F2 | Lỗi đã hiển thị |
| A4 | A5 | Chỉ tìm/lọc/xem danh sách |
| A5 | F1 | Danh sách/chi tiết đã hiển thị |
| A4 | D2 | Chọn thao tác quản lý |
| D2 | A6 | Tạo hoặc sửa hoặc lưu trữ |
| D2 | A12 | Yêu cầu sửa bộ không được phép |
| D2 | A13 | Nhân bản |
| D2 | A14 | Lưu trữ đã xác nhận |
| A6 | A7 | Form đã hiển thị |
| A7 | A8 | Đã xác nhận form |
| A7 | A15 | Hủy form |
| A15 | F2 | Không gửi mutation |
| A8 | D3 | Validation hoàn tất |
| D3 | A9 | Thiếu trường/version sai/revision stale |
| D3 | A10 | Dữ liệu hợp lệ và quyền khớp |
| A9 | A6 | Người dùng quay lại sửa form hoặc tải lại |
| A10 | D4 | Đã thử ghi |
| D4 | A16 | Ghi thành công |
| D4 | A11 | Ghi lỗi |
| A11 | F2 | Lỗi đã hiển thị |
| A12 | F2 | Không cập nhật bộ |
| A13 | A16 | Clone thành công, đã hiển thị bộ mới |
| A14 | A16 | Lưu trữ thành công, đã cập nhật danh sách |
| A16 | F1 | Kết quả đã hiển thị |

### 3c. Số liệu

N = 15 ô đặc tả có nội dung (luồng chính và các ô thay thế/ngoại lệ được gom theo thao tác). M = 16 Action; D = 4 Decision; E = 29 cạnh. CRUD và clone/archive có nhánh riêng, không đưa xóa cứng vì API không hỗ trợ.

## PHẦN 4 - PHÂN RÃ SEQUENCE (chưa vẽ)

### 4a. Lifeline trái sang phải

Tester → Giao diện Bộ kiểm thử → Controller/API → Service → Repository → Database. Hệ thống ngoài: không có.

### 4b. Bảng message

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Bộ kiểm thử | [1] moDanhSach(project_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Bộ kiểm thử | Controller/API | [2] listTestSuites(q, type, status, sort) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listTestSuiteRecords(filters) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] listSuites(projectQuery, sort, 500) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectSuites(filters, sort, limit=500) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDanhSach() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traDanhSach() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traListResponse() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Bộ kiểm thử | [2] traResponse() | trả về | chính |
| 10 | 2 | Giao diện Bộ kiểm thử | Tester | [2] hienThiDanhSach() | trả về | chính |
| 11 | 3.1 | Tester | Giao diện Bộ kiểm thử | [3.1] chonBo(suite_id) | đồng bộ | alt [xem chi tiết] |
| 12 | 3.1 | Giao diện Bộ kiểm thử | Controller/API | [3.1] getTestSuite(id) | đồng bộ | alt [xem chi tiết] |
| 13 | 3.1 | Controller/API | Service | [3.1] getTestSuiteRecord(id) | đồng bộ | alt [xem chi tiết] |
| 14 | 3.1 | Service | Repository | [3.1] findSuite(id) | đồng bộ | alt [xem chi tiết] |
| 15 | 3.1 | Repository | Database | [3.1] selectSuiteAndMembers(id) | đồng bộ | alt [xem chi tiết] |
| 16 | 3.1 | Database | Repository | [3.1] traBo() | trả về | alt [xem chi tiết] |
| 17 | 3.1 | Repository | Service | [3.1] traBoHoacNotFound() | trả về | alt [xem chi tiết] |
| 18 | 3.1 | Service | Controller/API | [3.1] traDetailResponse() | trả về | alt [xem chi tiết] |
| 19 | 3.1 | Controller/API | Giao diện Bộ kiểm thử | [3.1] traResponse() | trả về | alt [xem chi tiết] |
| 20 | 3.1 | Giao diện Bộ kiểm thử | Tester | [3.1] hienThiChiTiet() | trả về | alt [xem chi tiết] |
| 21 | 5 | Tester | Giao diện Bộ kiểm thử | [5] taoBo(name, type, version_ids) | đồng bộ | alt [tạo] |
| 22 | 8 | Giao diện Bộ kiểm thử | Controller/API | [8] createTestSuite(payload) | đồng bộ | alt [tạo] |
| 23 | 8 | Controller/API | Service | [8] createTestSuiteRecord(payload) | đồng bộ | alt [tạo] |
| 24 | 8 | Service | Service | [8] validateNameTypeAndDeduplicateVersions() | tự gọi | alt [hợp lệ/lỗi] |
| 25 | 8 | Service | Repository | [8] validateProjectVersions(project_id, version_ids) | đồng bộ | alt [hợp lệ/lỗi] |
| 26 | 8 | Repository | Database | [8] countVersionsInProject(ids) | đồng bộ | alt [hợp lệ/lỗi] |
| 27 | 8 | Database | Repository | [8] traSoVersionHopLe() | trả về | alt [hợp lệ/lỗi] |
| 28 | 9 | Service | Repository | [9] insertSuiteAndAudit(suite) | đồng bộ | alt [tạo thành công/lỗi] |
| 29 | 9 | Repository | Database | [9] insertSuite(suite) | đồng bộ | alt [tạo thành công/lỗi] |
| 30 | 9 | Database | Repository | [9] traSuiteMoi() | trả về | alt [tạo thành công/lỗi] |
| 31 | 10 | Service | Controller/API | [10] traCreatedSuite() | trả về | alt [tạo thành công/lỗi] |
| 32 | 10 | Controller/API | Giao diện Bộ kiểm thử | [10] traResponse() | trả về | alt [tạo thành công/lỗi] |
| 33 | 10 | Giao diện Bộ kiểm thử | Tester | [10] hienThiBoVaTaiLaiDanhSach() | trả về | alt [tạo thành công/lỗi] |
| 34 | 3.3 | Tester | Giao diện Bộ kiểm thử | [3.3] capNhatBo(suite_id, expected_revision, changes) | đồng bộ | alt [sửa/clone/archive] |
| 35 | 3.3 | Giao diện Bộ kiểm thử | Controller/API | [3.3] patchTestSuite(payload) | đồng bộ | alt [sửa] |
| 36 | 3.3 | Controller/API | Service | [3.3] updateTestSuiteRecord(payload) | đồng bộ | alt [sửa] |
| 37 | 3.3 | Service | Repository | [3.3] optimisticPatch(expected_revision, changes) | đồng bộ | alt [sửa/conflict] |
| 38 | 3.3 | Repository | Database | [3.3] updateSuiteAndRevision() | đồng bộ | alt [sửa/conflict] |
| 39 | 3.3 | Database | Repository | [3.3] traUpdatedSuiteHoacConflict() | trả về | alt [sửa/conflict] |
| 40 | 3.3 | Repository | Service | [3.3] traUpdateResult() | trả về | alt [sửa/conflict] |
| 41 | 3.3 | Service | Controller/API | [3.3] traResponse() | trả về | alt [sửa/conflict] |
| 42 | 3.3 | Controller/API | Giao diện Bộ kiểm thử | [3.3] traResponse() | trả về | alt [sửa/conflict] |
| 43 | 3.3 | Giao diện Bộ kiểm thử | Tester | [3.3] hienThiKetQua() | trả về | alt [sửa/conflict] |
| 44 | 3.4 | Tester | Giao diện Bộ kiểm thử | [3.4] nhanBanBo(id) | đồng bộ | alt [nhân bản] |
| 45 | 3.4 | Giao diện Bộ kiểm thử | Controller/API | [3.4] cloneTestSuite(id) | đồng bộ | alt [nhân bản] |
| 46 | 3.4 | Controller/API | Service | [3.4] cloneTestSuiteRecord(id) | đồng bộ | alt [nhân bản] |
| 47 | 3.4 | Service | Repository | [3.4] insertClonedSuite(new_id, source_id) | đồng bộ | alt [nhân bản] |
| 48 | 3.4 | Repository | Database | [3.4] insertSuite(cloned) | đồng bộ | alt [nhân bản] |
| 49 | 3.4 | Database | Repository | [3.4] traClonedSuite() | trả về | alt [nhân bản] |
| 50 | 3.4 | Repository | Service | [3.4] traCloneResult() | trả về | alt [nhân bản] |
| 51 | 3.4 | Service | Controller/API | [3.4] traCloneResponse() | trả về | alt [nhân bản] |
| 52 | 3.4 | Controller/API | Giao diện Bộ kiểm thử | [3.4] traResponse() | trả về | alt [nhân bản] |
| 53 | 3.4 | Giao diện Bộ kiểm thử | Tester | [3.4] hienThiBoMoi() | trả về | alt [nhân bản] |
| 54 | 3.5 | Tester | Giao diện Bộ kiểm thử | [3.5] luuTruBo(id, reason, expected_revision) | đồng bộ | alt [lưu trữ] |
| 55 | 3.5 | Giao diện Bộ kiểm thử | Controller/API | [3.5] archiveTestSuite(payload) | đồng bộ | alt [lưu trữ] |
| 56 | 3.5 | Controller/API | Service | [3.5] archiveTestSuiteRecord(payload) | đồng bộ | alt [lưu trữ] |
| 57 | 3.5 | Service | Repository | [3.5] optimisticPatchArchive(reason, expected_revision) | đồng bộ | alt [lưu trữ/conflict] |
| 58 | 3.5 | Repository | Database | [3.5] updateStatusReasonAndAudit(ARCHIVED) | đồng bộ | alt [lưu trữ/conflict] |
| 59 | 3.5 | Database | Repository | [3.5] traArchivedSuiteHoacConflict() | trả về | alt [lưu trữ/conflict] |
| 60 | 3.5 | Repository | Service | [3.5] traArchiveResult() | trả về | alt [lưu trữ/conflict] |
| 61 | 3.5 | Service | Controller/API | [3.5] traResponse() | trả về | alt [lưu trữ/conflict] |
| 62 | 3.5 | Controller/API | Giao diện Bộ kiểm thử | [3.5] traResponse() | trả về | alt [lưu trữ/conflict] |
| 63 | 3.5 | Giao diện Bộ kiểm thử | Tester | [3.5] hienThiTrangThaiArchived() | trả về | alt [lưu trữ/conflict] |

### 4c. Số liệu

N = 15 (như Phần 3c), M = 63 message, F = 5 fragment (alt list/detail, create, update, clone, archive), L = 6 lifeline. Mọi thao tác ghi có nhánh kết quả/lỗi; sequence đầy đủ cho từng thao tác quản lý.

## PHẦN 5 - PROMPT VẼ ACTIVITY

```text
Vẽ UML Activity Diagram cho UC25 - Quản lý bộ kiểm thử của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Dùng PlantUML, nhãn Tiếng Việt, bố cục phù hợp trang luận văn: hai swimlane Người dùng và Hệ thống; giữ nhánh CRUD/nhân bản/lưu trữ dễ đọc, không đưa chi tiết repository/database vào node.

ĐẶC TẢ ĐÃ CHỐT
Mô tả: Tester tìm, xem, tạo, sửa, nhân bản và lưu trữ bộ kiểm thử của dự án.
Tiền điều kiện: Đã xác thực, thuộc dự án; quyền riêng theo thao tác testsuite.read/create/update/clone/archive.
Hậu điều kiện: Create tạo ACTIVE revision 1; update dùng expected revision; clone tạo ID mới từ bộ nguồn; archive đặt trạng thái ARCHIVED cùng reason, actor/time. Xem/tìm không ghi; lỗi/hủy không ghi thành công. Không có xóa cứng.
Tác nhân chính: Tester. Tác nhân phụ: Không có.
Luồng chính: (1) Mở trang. (2) Hệ thống kiểm quyền, tải danh sách tối đa 500. (3) Tìm/lọc/chọn xem hoặc thao tác quản lý. (4) Hiển thị danh sách/chi tiết hoặc form. (5) Nhập dữ liệu. (6) Hệ thống kiểm name 2-300, type enum, version IDs cùng project, quyền, revision và trạng thái. (7) Tạo/cập nhật, clone hoặc archive theo lựa chọn. (8) Ghi audit và hiển thị kết quả.
Thay thế: xem chi tiết; tìm/lọc theo tên, type, status và sort; cập nhật thành viên; nhân bản bộ; lưu trữ với reason. Hủy đóng form, không gửi mutation.
Ngoại lệ: thiếu quyền, không tìm thấy, dữ liệu sai, selected version thiếu/khác project, conflict revision, bộ APPROVED bất biến, ARCHIVED không sửa, lỗi DB/audit. Bộ có thể rỗng theo schema API.

BẢNG NODE
I Initial Hệ thống: Bắt đầu, Tester đã xác thực
A1 Action Người dùng: [1] Mở trang bộ kiểm thử
A2 Action Hệ thống: [2] Tải danh sách theo quyền
D1 Decision Hệ thống: Có quyền đọc và dự án hợp lệ?
A3 Action Hệ thống: [2.1] Báo lỗi quyền hoặc dự án
A4 Action Người dùng: [3] Tìm, lọc hoặc chọn thao tác
A5 Action Hệ thống: [4] Trả danh sách hoặc chi tiết
D2 Decision Người dùng: Chọn tạo, sửa, nhân bản, lưu trữ hay chỉ xem?
A6 Action Hệ thống: [6] Hiển thị form tạo/sửa/archive
A7 Action Người dùng: [7] Nhập dữ liệu và xác nhận
A8 Action Hệ thống: [8] Kiểm quyền, trường và version scope
D3 Decision Hệ thống: Dữ liệu hợp lệ và revision khớp?
A9 Action Hệ thống: [8.1] Hiển thị validation hoặc conflict
A10 Action Hệ thống: [9] Lưu tạo mới hoặc cập nhật bộ
A11 Action Hệ thống: [9.1] Báo lỗi DB hoặc audit
A12 Action Hệ thống: [3.3] Chặn sửa bộ APPROVED/ARCHIVED
A13 Action Hệ thống: [3.4] Nhân bản bộ sang ACTIVE mới
A14 Action Hệ thống: [3.5] Lưu trữ với lý do và audit
A15 Action Người dùng: [3.6] Hủy thao tác
D4 Decision Hệ thống: Mutation đã ghi thành công?
A16 Action Hệ thống: [10] Hiển thị kết quả và làm mới danh sách
F1 Final Hệ thống: Kết thúc thành công hoặc chỉ xem
F2 Final Hệ thống: Kết thúc lỗi/hủy, không mutation thành công

BẢNG CẠNH
I -> A1 [Bắt đầu]; A1 -> A2 [Trang đã mở]; A2 -> D1 [Tải hoàn tất]; D1 -> A4 [Có quyền/dự án hợp lệ]; D1 -> A3 [Thiếu quyền/dự án sai]; A3 -> F2 [Lỗi hiển thị]; A4 -> A5 [Chỉ tìm/lọc/xem]; A5 -> F1 [Danh sách/chi tiết hiển thị]; A4 -> D2 [Chọn thao tác quản lý]; D2 -> A6 [Tạo/sửa]; D2 -> A12 [Bộ APPROVED/ARCHIVED không sửa]; D2 -> A13 [Nhân bản]; D2 -> A14 [Lưu trữ]; A6 -> A7 [Form hiển thị]; A7 -> A8 [Đã xác nhận]; A7 -> A15 [Hủy]; A15 -> F2 [Không gửi mutation]; A8 -> D3 [Validation xong]; D3 -> A9 [Dữ liệu sai/conflict]; D3 -> A10 [Dữ liệu hợp lệ]; A9 -> A6 [Sửa form/tải lại]; A10 -> D4 [Đã thử ghi]; D4 -> A16 [Ghi thành công]; D4 -> A11 [Ghi thất bại]; A11 -> F2 [Lỗi hiển thị]; A12 -> F2 [Không cập nhật]; A13 -> A16 [Clone và trả kết quả]; A14 -> A16 [Archive và trả kết quả]; A16 -> F1 [Kết quả hiển thị].

YÊU CẦU: Giữ guard rõ ở mỗi nhánh; thành công và thất bại là final riêng. Xem/tìm/lọc kết thúc riêng; sửa, clone, archive không gộp chung action. Không vẽ xóa cứng. Không tạo node treo.
ĐỐI CHIẾU: 16 Action, 4 Decision, 29 cạnh. Báo số thực tế.
```

## PHẦN 6 - PROMPT VẼ SEQUENCE

```text
Vẽ UML Sequence Diagram cho UC25 - Quản lý bộ kiểm thử của hệ thống Veriq bằng Visual Paradigm AI Chatbot. Dùng PlantUML, nhãn Tiếng Việt. Bố cục ngang phù hợp trang luận văn. Dùng 6 lifeline theo thứ tự, các nhóm alt gọn theo thao tác. Mọi lời gọi đồng bộ có return; không lược qua lớp.

ĐẶC TẢ ĐÃ CHỐT
Mô tả: Tester tìm/xem/tạo/sửa/nhân bản/lưu trữ bộ kiểm thử.
Tiền điều kiện: Đã xác thực, dự án hợp lệ, quyền testsuite.read/create/update/clone/archive phù hợp.
Hậu điều kiện: Bộ mới ACTIVE; sửa theo optimistic revision; clone giữ nguồn và tạo mới; archive đặt ARCHIVED, lưu lý do/actor/time. Đọc không ghi; hủy/lỗi không xác nhận thành công. Không có delete API.
Tác nhân chính: Tester. Tác nhân phụ: Không có.
Luồng chính: Load danh sách đã lọc; nhánh CRUD, clone, archive kiểm tra permission và dữ liệu, đọc/ghi qua Repository/Database, trả kết quả.
Thay thế: detail; search/filter; create (version list rỗng được chấp nhận); update; clone; archive; cancel.
Ngoại lệ: quyền, project scope, name/type/version invalid, not found, expected revision conflict, APPROVED immutable, ARCHIVED update denied, DB/audit failure.

LIFELINE trái sang phải: Tester; Giao diện Bộ kiểm thử; Controller/API; Service; Repository; Database.

DANH SÁCH MESSAGE (đầy đủ, theo đúng thứ tự):

| STT | Số bước | Từ | Đến | Nội dung | Loại | Fragment |
|---:|---|---|---|---|---|---|
| 1 | 1 | Tester | Giao diện Bộ kiểm thử | [1] moDanhSach(project_id) | đồng bộ | chính |
| 2 | 2 | Giao diện Bộ kiểm thử | Controller/API | [2] listTestSuites(q, type, status, sort) | đồng bộ | chính |
| 3 | 2 | Controller/API | Service | [2] listTestSuiteRecords(filters) | đồng bộ | chính |
| 4 | 2 | Service | Repository | [2] listSuites(projectQuery, sort, 500) | đồng bộ | chính |
| 5 | 2 | Repository | Database | [2] selectSuites(filters, sort, limit=500) | đồng bộ | chính |
| 6 | 2 | Database | Repository | [2] traDanhSach() | trả về | chính |
| 7 | 2 | Repository | Service | [2] traDanhSach() | trả về | chính |
| 8 | 2 | Service | Controller/API | [2] traListResponse() | trả về | chính |
| 9 | 2 | Controller/API | Giao diện Bộ kiểm thử | [2] traResponse() | trả về | chính |
| 10 | 2 | Giao diện Bộ kiểm thử | Tester | [2] hienThiDanhSach() | trả về | chính |
| 11 | 3.1 | Tester | Giao diện Bộ kiểm thử | [3.1] chonBo(suite_id) | đồng bộ | alt [xem chi tiết] |
| 12 | 3.1 | Giao diện Bộ kiểm thử | Controller/API | [3.1] getTestSuite(id) | đồng bộ | alt [xem chi tiết] |
| 13 | 3.1 | Controller/API | Service | [3.1] getTestSuiteRecord(id) | đồng bộ | alt [xem chi tiết] |
| 14 | 3.1 | Service | Repository | [3.1] findSuite(id) | đồng bộ | alt [xem chi tiết] |
| 15 | 3.1 | Repository | Database | [3.1] selectSuiteAndMembers(id) | đồng bộ | alt [xem chi tiết] |
| 16 | 3.1 | Database | Repository | [3.1] traBo() | trả về | alt [xem chi tiết] |
| 17 | 3.1 | Repository | Service | [3.1] traBoHoacNotFound() | trả về | alt [xem chi tiết] |
| 18 | 3.1 | Service | Controller/API | [3.1] traDetailResponse() | trả về | alt [xem chi tiết] |
| 19 | 3.1 | Controller/API | Giao diện Bộ kiểm thử | [3.1] traResponse() | trả về | alt [xem chi tiết] |
| 20 | 3.1 | Giao diện Bộ kiểm thử | Tester | [3.1] hienThiChiTiet() | trả về | alt [xem chi tiết] |
| 21 | 5 | Tester | Giao diện Bộ kiểm thử | [5] taoBo(name, type, version_ids) | đồng bộ | alt [tạo] |
| 22 | 8 | Giao diện Bộ kiểm thử | Controller/API | [8] createTestSuite(payload) | đồng bộ | alt [tạo] |
| 23 | 8 | Controller/API | Service | [8] createTestSuiteRecord(payload) | đồng bộ | alt [tạo] |
| 24 | 8 | Service | Service | [8] validateNameTypeAndDeduplicateVersions() | tự gọi | alt [hợp lệ/lỗi] |
| 25 | 8 | Service | Repository | [8] validateProjectVersions(project_id, version_ids) | đồng bộ | alt [hợp lệ/lỗi] |
| 26 | 8 | Repository | Database | [8] countVersionsInProject(ids) | đồng bộ | alt [hợp lệ/lỗi] |
| 27 | 8 | Database | Repository | [8] traSoVersionHopLe() | trả về | alt [hợp lệ/lỗi] |
| 28 | 9 | Service | Repository | [9] insertSuiteAndAudit(suite) | đồng bộ | alt [tạo thành công/lỗi] |
| 29 | 9 | Repository | Database | [9] insertSuite(suite) | đồng bộ | alt [tạo thành công/lỗi] |
| 30 | 9 | Database | Repository | [9] traSuiteMoi() | trả về | alt [tạo thành công/lỗi] |
| 31 | 10 | Service | Controller/API | [10] traCreatedSuite() | trả về | alt [tạo thành công/lỗi] |
| 32 | 10 | Controller/API | Giao diện Bộ kiểm thử | [10] traResponse() | trả về | alt [tạo thành công/lỗi] |
| 33 | 10 | Giao diện Bộ kiểm thử | Tester | [10] hienThiBoVaTaiLaiDanhSach() | trả về | alt [tạo thành công/lỗi] |
| 34 | 3.3 | Tester | Giao diện Bộ kiểm thử | [3.3] capNhatBo(suite_id, expected_revision, changes) | đồng bộ | alt [sửa/clone/archive] |
| 35 | 3.3 | Giao diện Bộ kiểm thử | Controller/API | [3.3] patchTestSuite(payload) | đồng bộ | alt [sửa] |
| 36 | 3.3 | Controller/API | Service | [3.3] updateTestSuiteRecord(payload) | đồng bộ | alt [sửa] |
| 37 | 3.3 | Service | Repository | [3.3] optimisticPatch(expected_revision, changes) | đồng bộ | alt [sửa/conflict] |
| 38 | 3.3 | Repository | Database | [3.3] updateSuiteAndRevision() | đồng bộ | alt [sửa/conflict] |
| 39 | 3.3 | Database | Repository | [3.3] traUpdatedSuiteHoacConflict() | trả về | alt [sửa/conflict] |
| 40 | 3.3 | Repository | Service | [3.3] traUpdateResult() | trả về | alt [sửa/conflict] |
| 41 | 3.3 | Service | Controller/API | [3.3] traResponse() | trả về | alt [sửa/conflict] |
| 42 | 3.3 | Controller/API | Giao diện Bộ kiểm thử | [3.3] traResponse() | trả về | alt [sửa/conflict] |
| 43 | 3.3 | Giao diện Bộ kiểm thử | Tester | [3.3] hienThiKetQua() | trả về | alt [sửa/conflict] |
| 44 | 3.4 | Tester | Giao diện Bộ kiểm thử | [3.4] nhanBanBo(id) | đồng bộ | alt [nhân bản] |
| 45 | 3.4 | Giao diện Bộ kiểm thử | Controller/API | [3.4] cloneTestSuite(id) | đồng bộ | alt [nhân bản] |
| 46 | 3.4 | Controller/API | Service | [3.4] cloneTestSuiteRecord(id) | đồng bộ | alt [nhân bản] |
| 47 | 3.4 | Service | Repository | [3.4] insertClonedSuite(new_id, source_id) | đồng bộ | alt [nhân bản] |
| 48 | 3.4 | Repository | Database | [3.4] insertSuite(cloned) | đồng bộ | alt [nhân bản] |
| 49 | 3.4 | Database | Repository | [3.4] traClonedSuite() | trả về | alt [nhân bản] |
| 50 | 3.4 | Repository | Service | [3.4] traCloneResult() | trả về | alt [nhân bản] |
| 51 | 3.4 | Service | Controller/API | [3.4] traCloneResponse() | trả về | alt [nhân bản] |
| 52 | 3.4 | Controller/API | Giao diện Bộ kiểm thử | [3.4] traResponse() | trả về | alt [nhân bản] |
| 53 | 3.4 | Giao diện Bộ kiểm thử | Tester | [3.4] hienThiBoMoi() | trả về | alt [nhân bản] |
| 54 | 3.5 | Tester | Giao diện Bộ kiểm thử | [3.5] luuTruBo(id, reason, expected_revision) | đồng bộ | alt [lưu trữ] |
| 55 | 3.5 | Giao diện Bộ kiểm thử | Controller/API | [3.5] archiveTestSuite(payload) | đồng bộ | alt [lưu trữ] |
| 56 | 3.5 | Controller/API | Service | [3.5] archiveTestSuiteRecord(payload) | đồng bộ | alt [lưu trữ] |
| 57 | 3.5 | Service | Repository | [3.5] optimisticPatchArchive(reason, expected_revision) | đồng bộ | alt [lưu trữ/conflict] |
| 58 | 3.5 | Repository | Database | [3.5] updateStatusReasonAndAudit(ARCHIVED) | đồng bộ | alt [lưu trữ/conflict] |
| 59 | 3.5 | Database | Repository | [3.5] traArchivedSuiteHoacConflict() | trả về | alt [lưu trữ/conflict] |
| 60 | 3.5 | Repository | Service | [3.5] traArchiveResult() | trả về | alt [lưu trữ/conflict] |
| 61 | 3.5 | Service | Controller/API | [3.5] traResponse() | trả về | alt [lưu trữ/conflict] |
| 62 | 3.5 | Controller/API | Giao diện Bộ kiểm thử | [3.5] traResponse() | trả về | alt [lưu trữ/conflict] |
| 63 | 3.5 | Giao diện Bộ kiểm thử | Tester | [3.5] hienThiTrangThaiArchived() | trả về | alt [lưu trữ/conflict] |

Vẽ tất cả các dòng message và return theo thứ tự; có thể bố trí operand alt theo chiều dọc để sơ đồ vừa trang, nhưng không bỏ message.

YÊU CẦU VẼ: Dùng activation bars; hiển thị đủ lifeline. Dùng alt [xem/tìm/lọc], [tạo], [sửa], [nhân bản], [lưu trữ], [lỗi hoặc conflict], opt [hủy]. Chuyển mọi message của mỗi operand vào đúng nhánh; request đồng bộ phải có return qua đúng lớp. Không dùng ellipsis, không gộp CRUD, không gọi thẳng từ giao diện xuống Database. Tên operation giữ nguyên theo message table. Không thêm xóa cứng hoặc buộc bộ có ít nhất một ca.
ĐỐI CHIẾU: 6 lifeline, 63 message, 5 fragment. Báo số thực tế và mọi chỗ không khớp.
```

## TỰ KIỂM TRA UC25

- [x] Phần 1 nêu lỗi thực và kiểm tra đủ CRUD, lỗi, quyền, tiền/hậu điều kiện.
- [x] Phần 2 có mô tả, điều kiện, tác nhân, ba luồng, giả định; nhánh có quay lại/kết thúc.
- [x] Activity: 16 Action, 4 Decision, 29 cạnh; thành công/thất bại riêng.
- [x] Sequence: 6 lifeline, 63 message, 5 fragment; thao tác qua từng lớp và có return.
- [x] Prompt Activity chép đủ đặc tả, node và cạnh; prompt Sequence chứa đủ 63 dòng message, không dùng “như trên”.

## Bảng theo dõi sau UC25

| Mã UC | Tên UC | Module | Kiểm tra | Chốt | Prompt Activity | Prompt Sequence |
|---|---|---|---|---|---|---|
| UC01 | Đăng nhập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC02 | Đăng xuất | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC03 | Cập nhật thông tin cá nhân | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC04 | Khôi phục mật khẩu | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC05 | Quản lý tài khoản | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC06 | Kiểm soát truy cập | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC07 | Phân quyền | 1. Quản lý tài khoản | Xong | Xong | Xong | Xong |
| UC08 | Quản lý dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC09 | Quản lý thành viên dự án | 2. Quản lý dự án | Xong | Xong | Xong | Xong |
| UC10 | Quản lý yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC11 | Trình duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC12 | Xét duyệt yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC13 | Quản lý hiệu lực yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC14 | Tổ chức yêu cầu | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC15 | Quản lý tài liệu nguồn | 3. Quản lý yêu cầu | Xong | Xong | Xong | Xong |
| UC16 | Quản lý kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC17 | Trình duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC18 | Xét duyệt kế hoạch kiểm thử | 4. Quản lý kế hoạch kiểm thử | Xong | Xong | Xong | Xong |
| UC19 | Quản lý điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC20 | Xét duyệt điều kiện kiểm thử | 5. Quản lý điều kiện kiểm thử | Xong | Xong | Xong | Xong |
| UC21 | Quản lý ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC22 | Trình duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC23 | Xét duyệt ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC24 | Quản lý phiên bản ca kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC25 | Quản lý bộ kiểm thử | 6. Quản lý ca kiểm thử | Xong | Xong | Xong | Xong |
| UC26 | Quản lý lần chạy kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC27 | Thực thi kiểm thử | 7. Thực thi kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC28 | Quản lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC29 | Xử lý lỗi | 8. Quản lý lỗi | Chưa | Chưa | Chưa | Chưa |
| UC30 | Quản lý báo cáo kiểm thử | 9. Báo cáo kiểm thử | Chưa | Chưa | Chưa | Chưa |
| UC31 | Tạo yêu cầu bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC32 | Đề xuất kế hoạch kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |
| UC33 | Tạo ca kiểm thử bằng AI | 10. Hỗ trợ nghiệp vụ bằng AI | Chưa | Chưa | Chưa | Chưa |

