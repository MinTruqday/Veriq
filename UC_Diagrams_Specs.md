# Đặc tả nghiệp vụ Veriq, bản làm lại từ nguồn

Nội dung được dựng lại từ 33 bảng UC trong `32_Use_Case_Tables.md`. Các câu trong phần đặc tả diễn đạt hành vi theo góc nhìn người dùng và hệ thống; thông tin chưa có căn cứ được để riêng, không tự thêm vào luồng.

# UC01 - Đăng nhập

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép người dùng đăng nhập vào hệ thống bằng tài khoản đã được cấp.

**Tiền điều kiện:** Người dùng có tài khoản trong hệ thống.

**Hậu điều kiện:** Người dùng đăng nhập thành công và có thể sử dụng các chức năng theo quyền được cấp.

**Tác nhân chính:** Người dùng

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang đăng nhập. |  |
| 2 |  | Hệ thống hiển thị giao diện đăng nhập gồm email và mật khẩu. |
| 3 | Nhập email và mật khẩu. |  |
| 4 | Nhấn nút “Đăng nhập”. |  |
| 5 |  | Hệ thống kiểm tra thông tin đăng nhập. |
| 6 |  | Thông tin hợp lệ, hệ thống chuyển người dùng đến trang danh sách dự án hoặc trang được yêu cầu trước khi đăng nhập. |
| 7 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Nhấn vào “Quên mật khẩu”. |  |
| 3.1.2 |  | Hệ thống mở trang khôi phục mật khẩu, nơi người dùng tiếp tục UC04. |
| 5.1 |  | Email hoặc mật khẩu không chính xác, hệ thống hiển thị thông báo lỗi và quay về bước 3. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.2 |  | Tài khoản bị khóa hoặc bị vô hiệu hóa, hệ thống từ chối đăng nhập. |
| 5.3 |  | Số lần đăng nhập vượt quá giới hạn cho phép, hệ thống tạm thời ngừng tiếp nhận yêu cầu đăng nhập. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép người dùng đăng nhập vào hệ thống bằng tài khoản đã được cấp. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC02 - Đăng xuất

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép người dùng đăng xuất khỏi hệ thống.

**Tiền điều kiện:** Người dùng đã đăng nhập.

**Hậu điều kiện:** Người dùng đăng xuất thành công và trở về trang đăng nhập.

**Tác nhân chính:** Người dùng

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang tài khoản cá nhân. |  |
| 2 |  | Hệ thống hiển thị thông tin tài khoản cá nhân. |
| 3 | Nhấn nút “Đăng xuất”. |  |
| 4 |  | Hệ thống thực hiện đăng xuất và chuyển người dùng về trang đăng nhập. |
| 5 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

Nguồn không nêu bước cho luồng này.

### Luồng sự kiện ngoại lệ

Nguồn không nêu bước cho luồng này.

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép người dùng đăng xuất khỏi hệ thống. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC03 - Cập nhật thông tin cá nhân

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép người dùng xem, chỉnh sửa thông tin cá nhân và thay đổi mật khẩu của tài khoản.

**Tiền điều kiện:** Người dùng đã đăng nhập.

**Hậu điều kiện:** Thông tin cá nhân hoặc mật khẩu được cập nhật.

**Tác nhân chính:** Người dùng

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang tài khoản cá nhân. |  |
| 2 |  | Hệ thống hiển thị email, tên hiển thị, vai trò, ngôn ngữ và múi giờ. |
| 3 | Chỉnh sửa tên hiển thị, ngôn ngữ hoặc múi giờ. |  |
| 4 | Nhấn nút “Lưu thông tin”. |  |
| 5 |  | Hệ thống kiểm tra thông tin vừa nhập. |
| 6 |  | Thông tin hợp lệ, nội dung thay đổi được lưu và thông báo cập nhật thành công được hiển thị. |
| 7 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Truy cập mục “Đổi mật khẩu”. |  |
| 3.1.2 |  | Hệ thống hiển thị giao diện gồm mật khẩu hiện tại và mật khẩu mới. |
| 3.1.3 | Nhập mật khẩu hiện tại và mật khẩu mới. |  |
| 3.1.4 | Nhấn nút “Đổi mật khẩu”. |  |
| 3.1.5 |  | Hệ thống kiểm tra mật khẩu hiện tại và tính hợp lệ của mật khẩu mới. |
| 3.1.5.1 |  | Mật khẩu hiện tại không chính xác, hệ thống hiển thị thông báo lỗi và quay về bước 3.1.3. |
| 3.1.5.2 |  | Mật khẩu mới không đáp ứng yêu cầu độ dài hoặc trùng với mật khẩu hiện tại, hệ thống yêu cầu nhập mật khẩu khác. |
| 3.1.6 |  | Mật khẩu hợp lệ, hệ thống cập nhật mật khẩu mới và thông báo đổi mật khẩu thành công. |
| 3.1.7 |  | Kết thúc chức năng. |
| 5.1 |  | Tên hiển thị bị bỏ trống hoặc ngôn ngữ, múi giờ không hợp lệ, hệ thống yêu cầu điều chỉnh thông tin tại bước 3. |

### Luồng sự kiện ngoại lệ

Nguồn không nêu bước cho luồng này.

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép người dùng xem, chỉnh sửa thông tin cá nhân và thay đổi mật khẩu của tài khoản. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC04 - Khôi phục mật khẩu

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này hỗ trợ người dùng đặt lại mật khẩu khi không thể đăng nhập bằng mật khẩu hiện tại.

**Tiền điều kiện:** Người dùng có tài khoản và có thể truy cập email của tài khoản đó.

**Hậu điều kiện:** Mật khẩu mới được lưu và có thể sử dụng để đăng nhập.

**Tác nhân chính:** Người dùng

**Tác nhân phụ:** Dịch vụ gửi email

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Nhấn vào “Quên mật khẩu” tại trang đăng nhập. |  |
| 2 |  | Hệ thống hiển thị giao diện khôi phục mật khẩu. |
| 3 | Nhập email của tài khoản. |  |
| 4 | Nhấn nút “Gửi mã”. |  |
| 5 |  | Hệ thống kiểm tra email đã nhập. |
| 6 |  | Email tồn tại, hệ thống tạo mã xác thực gồm 6 chữ số và gửi mã đến email của người dùng. |
| 7 |  | Hiển thị giao diện nhập mã xác thực. |
| 8 | Nhập mã xác thực nhận được qua email. |  |
| 9 | Xác nhận mã xác thực. |  |
| 10 |  | Hệ thống kiểm tra tính hợp lệ của mã. |
| 11 |  | Mã xác thực hợp lệ, hệ thống chuyển đến giao diện đặt lại mật khẩu. |
| 12 | Nhập mật khẩu mới. |  |
| 13 | Xác nhận đặt lại mật khẩu. |  |
| 14 |  | Hệ thống kiểm tra mật khẩu mới và hiệu lực của yêu cầu khôi phục. |
| 15 |  | Thông tin hợp lệ, mật khẩu mới được lưu. |
| 16 |  | Chuyển người dùng về trang đăng nhập. |
| 17 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.1 |  | Email không tồn tại, hệ thống vẫn hiển thị giao diện nhập mã xác thực nhưng không gửi mã khôi phục. |
| 8.1.1 | Nhấn nút “Gửi lại mã” sau khi hết thời gian chờ. |  |
| 8.1.2 |  | Hệ thống tiếp nhận yêu cầu gửi mã mới. Quay về bước 8. |
| 10.1 |  | Mã xác thực không chính xác hoặc đã hết hạn, hệ thống hiển thị thông báo lỗi. Người dùng có thể nhập lại hoặc yêu cầu gửi mã mới. |
| 14.1 |  | Mật khẩu mới không đáp ứng yêu cầu độ dài, hệ thống yêu cầu nhập lại tại bước 12. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 14.2 |  | Yêu cầu khôi phục đã hết hiệu lực hoặc đã được sử dụng, hệ thống không thực hiện thay đổi mật khẩu. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này hỗ trợ người dùng đặt lại mật khẩu khi không thể đăng nhập bằng mật khẩu hiện tại. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC05 - Quản lý tài khoản

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép Quản trị viên hệ thống tạo, xem, tìm kiếm, chỉnh sửa và ẩn danh tài khoản người dùng qua chức năng quản trị nền tảng.

**Tiền điều kiện:** Quản trị viên hệ thống đã đăng nhập và được phép truy cập chức năng quản trị nền tảng.

**Hậu điều kiện:** Danh sách hoặc thông tin tài khoản được cập nhật theo thao tác quản trị hợp lệ.

**Tác nhân chính:** Quản trị viên hệ thống

**Tác nhân phụ:** Dịch vụ gửi email

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang quản lý tài khoản. |  |
| 2 |  | Hệ thống hiển thị danh sách tài khoản gồm email, họ tên, vai trò và trạng thái hoạt động. |
| 3 | Nhấn nút “Tạo tài khoản”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm email, họ tên, tên đăng nhập và lý do tạo tài khoản. |
| 5 | Nhập các thông tin trên. |  |
| 6 | Nhấn nút “Tạo và gửi lời mời”. |  |
| 7 |  | Hệ thống kiểm tra tính hợp lệ của thông tin và sự trùng lặp của email, tên đăng nhập. |
| 8 |  | Thông tin hợp lệ, hệ thống tạo tài khoản và gửi yêu cầu thiết lập mật khẩu qua email. |
| 9 |  | Hiển thị tài khoản vừa tạo trong danh sách. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn tài khoản cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị thông tin chi tiết và danh sách dự án mà tài khoản tham gia. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập email, họ tên hoặc tên đăng nhập vào ô tìm kiếm. |  |
| 3.2.2 |  | Danh sách tài khoản được cập nhật theo từ khóa tìm kiếm. |
| 3.2.3 | Chọn tài khoản cần xem. |  |
| 3.2.4 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | Chọn tài khoản cần chỉnh sửa. |  |
| 3.3.2 |  | Hệ thống hiển thị thông tin chi tiết tài khoản. |
| 3.3.3 | Chọn chức năng sửa hồ sơ. |  |
| 3.3.4 |  | Hệ thống hiển thị họ tên và tên đăng nhập hiện tại. |
| 3.3.5 | Chỉnh sửa thông tin và nhập lý do thay đổi. |  |
| 3.3.6 | Xác nhận lưu thông tin. |  |
| 3.3.7 |  | Hệ thống kiểm tra thông tin vừa nhập. |
| 3.3.7.1 |  | Tên đăng nhập vừa thay đổi đã tồn tại, hệ thống yêu cầu nhập tên khác. |
| 3.3.8 |  | Thông tin hợp lệ, nội dung thay đổi được lưu vào tài khoản tương ứng. |
| 3.3.9 |  | Cập nhật danh sách tài khoản. Kết thúc chức năng. |
| 3.4.1 | Chọn tài khoản cần ẩn danh. |  |
| 3.4.2 | Chọn “Xóa và ẩn danh tài khoản”. |  |
| 3.4.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập email xác nhận và lý do xóa. |
| 3.4.4 | Nhập email của tài khoản cần xóa và lý do. |  |
| 3.4.5 | Xác nhận ẩn danh tài khoản. |  |
| 3.4.6 |  | Hệ thống kiểm tra thông tin xác nhận và điều kiện xóa. |
| 3.4.7 |  | Hệ thống loại bỏ thông tin nhận dạng và ngừng hoạt động của tài khoản, đồng thời giữ lại lịch sử nghiệp vụ liên quan. |
| 3.4.8 |  | Cập nhật danh sách tài khoản. Kết thúc chức năng. |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng biểu mẫu, không tạo tài khoản mới. |
| 7.1 |  | Email hoặc tên đăng nhập đã tồn tại, hệ thống hiển thị thông báo lỗi và quay về bước 5. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.4.6.1 |  | Email xác nhận không trùng với email của tài khoản cần xóa, hệ thống từ chối thực hiện. |
| 3.4.6.2 |  | Tài khoản cần xóa là tài khoản của chính quản trị viên hoặc tài khoản quản trị viên cuối cùng đang hoạt động, hệ thống không cho phép xóa. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép Quản trị viên hệ thống tạo, xem, tìm kiếm, chỉnh sửa và ẩn danh tài khoản người dùng qua chức năng quản trị nền tảng. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC06 - Kiểm soát truy cập

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép Quản trị viên hệ thống quản lý trạng thái hoạt động, thay đổi vai trò và yêu cầu gửi lại thông tin kích hoạt hoặc đặt lại mật khẩu cho tài khoản.

**Tiền điều kiện:** Quản trị viên hệ thống đã đăng nhập và tài khoản cần quản lý tồn tại trong hệ thống.

**Hậu điều kiện:** Trạng thái hoạt động hoặc vai trò của tài khoản được cập nhật; yêu cầu thiết lập lại mật khẩu được gửi khi quản trị viên thực hiện chức năng tương ứng.

**Tác nhân chính:** Quản trị viên hệ thống

**Tác nhân phụ:** Dịch vụ gửi email

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang quản lý tài khoản. |  |
| 2 |  | Hệ thống hiển thị danh sách tài khoản. |
| 3 | Chọn tài khoản cần quản lý. |  |
| 4 |  | Hệ thống hiển thị thông tin và trạng thái hiện tại của tài khoản. |
| 5 | Chọn chức năng khóa tài khoản. |  |
| 6 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do khóa. |
| 7 | Nhập lý do và xác nhận. |  |
| 8 |  | Hệ thống kiểm tra điều kiện khóa tài khoản. |
| 9 |  | Tài khoản được khóa và không thể tiếp tục truy cập hệ thống. |
| 10 |  | Cập nhật trạng thái tài khoản. Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn chức năng thao tác hàng loạt. |  |
| 3.1.2 |  | Hệ thống hiển thị hai lựa chọn: vô hiệu hóa tài khoản và gửi lại lời mời. |
| 3.1.3 | Chọn thao tác, xác định các tài khoản cần xử lý và nhập lý do. |  |
| 3.1.4 | Chọn xem trước. |  |
| 3.1.5 |  | Hệ thống kiểm tra danh sách và hiển thị các tài khoản có thể xử lý. |
| 3.1.6 | Xác nhận thực hiện. |  |
| 3.1.7 |  | Hệ thống thực hiện thao tác đối với các tài khoản hợp lệ và hiển thị kết quả. |
| 3.1.8 |  | Kết thúc chức năng. |
| 5.1.1 | Chọn chức năng mở khóa. |  |
| 5.1.2 |  | Hệ thống yêu cầu nhập lý do mở khóa tài khoản. |
| 5.1.3 | Nhập lý do và xác nhận. |  |
| 5.1.4 |  | Hệ thống mở khóa tài khoản và cập nhật trạng thái. |
| 5.1.5 |  | Kết thúc chức năng. |
| 5.2.1 | Chọn chức năng vô hiệu hóa. |  |
| 5.2.2 |  | Hệ thống hiển thị hộp thoại xác nhận. |
| 5.2.3 | Nhập lý do và xác nhận. |  |
| 5.2.4 |  | Hệ thống chuyển tài khoản sang trạng thái bị vô hiệu hóa. |
| 5.2.5 |  | Kết thúc chức năng. |
| 5.3.1 | Chọn chức năng kích hoạt tài khoản đã bị vô hiệu hóa. |  |
| 5.3.2 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do. |
| 5.3.3 | Nhập lý do và xác nhận. |  |
| 5.3.4 |  | Hệ thống đưa tài khoản trở lại trạng thái hoạt động. |
| 5.3.5 |  | Kết thúc chức năng. |
| 5.4.1 | Chọn cấp quyền hoặc hạ quyền quản trị. |  |
| 5.4.2 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do thay đổi vai trò. |
| 5.4.3 | Nhập lý do và xác nhận. |  |
| 5.4.4 |  | Hệ thống kiểm tra và lưu vai trò mới của tài khoản. |
| 5.4.5 |  | Kết thúc chức năng. |
| 5.5.1 | Chọn chức năng “Gửi yêu cầu đặt lại mật khẩu”. |  |
| 5.5.2 |  | Hệ thống hiển thị hộp thoại xác nhận và yêu cầu nhập lý do. |
| 5.5.3 | Nhập lý do và xác nhận. |  |
| 5.5.4 |  | Hệ thống khởi tạo quy trình khôi phục mật khẩu và gửi hướng dẫn đến email của tài khoản được chọn; người dùng tự đặt mật khẩu mới qua quy trình này. |
| 5.5.5 |  | Kết thúc chức năng. |
| 5.6.1 | Chọn chức năng gửi lại lời mời kích hoạt. |  |
| 5.6.2 |  | Hệ thống hiển thị hộp thoại xác nhận. |
| 5.6.3 | Nhập lý do và xác nhận. |  |
| 5.6.4 |  | Hệ thống gửi lại yêu cầu thiết lập mật khẩu qua email. |
| 5.6.5 |  | Kết thúc chức năng. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.7.1 |  | Danh sách xem trước đã hết hiệu lực, hệ thống yêu cầu thực hiện lại bước 3.1.4. |
| 5.2.4.1 |  | quản trị viên tự vô hiệu hóa tài khoản của mình hoặc vô hiệu hóa tài khoản quản trị viên cuối cùng đang hoạt động, hệ thống không cho phép thực hiện. |
| 5.4.4.1 |  | Thao tác hạ quyền không đáp ứng quy định bảo vệ tài khoản quản trị viên, hệ thống từ chối thay đổi vai trò. |
| 8.1 |  | quản trị viên thực hiện khóa tài khoản của chính mình, hệ thống từ chối thao tác. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép Quản trị viên hệ thống quản lý trạng thái hoạt động, thay đổi vai trò và yêu cầu gửi lại thông tin kích hoạt hoặc đặt lại mật khẩu cho tài khoản. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC07 - Phân quyền

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép Quản trị viên hệ thống cập nhật ma trận quyền dự án theo các vai trò được hỗ trợ.

**Tiền điều kiện:** Quản trị viên hệ thống đã đăng nhập.

**Hậu điều kiện:** Bảng phân quyền được lưu và áp dụng cho các vai trò tương ứng.

**Tác nhân chính:** quản trị viên

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập mục phân quyền trong trang quản trị. |  |
| 2 |  | Hệ thống hiển thị ma trận quyền dự án theo các vai trò được hỗ trợ trong cấu hình. |
| 3 | Xem các quyền hiện tại của từng vai trò. |  |
| 4 | Điều chỉnh quyền được gán cho từng vai trò dự án. |  |
| 5 | Nhấn nút “Lưu phân quyền”. |  |
| 6 |  | Hệ thống kiểm tra các quyền vừa thiết lập. |
| 7 |  | Bảng phân quyền hợp lệ, hệ thống lưu nội dung thay đổi và thông báo cập nhật thành công. |
| 8 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

Nguồn không nêu bước cho luồng này.

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 6.1 |  | Bảng phân quyền đã được cập nhật bởi quản trị viên khác, hệ thống không lưu đè lên nội dung mới. |
| 6.2 |  | Vai trò hoặc quyền được thiết lập không hợp lệ, hệ thống từ chối lưu bảng phân quyền. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép Quản trị viên hệ thống cập nhật ma trận quyền dự án theo các vai trò được hỗ trợ. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC08 - Quản lý dự án

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép người có quyền quản lý dự án tạo, xem, tìm kiếm, chỉnh sửa, lưu trữ và khôi phục dự án; thao tác xóa cứng thuộc quy trình quản trị nền tảng.

**Tiền điều kiện:** Người dùng đã đăng nhập; việc tạo dự án phụ thuộc chính sách tạo dự án, còn các thao tác trên dự án phụ thuộc quyền hiệu lực của người dùng.

**Hậu điều kiện:** Dự án được tạo, cập nhật hoặc chuyển trạng thái theo thao tác được cấp quyền. Xóa cứng, nếu được thực hiện, do Quản trị viên hệ thống xử lý qua chức năng quản trị riêng.

**Tác nhân chính:** Người dùng có quyền tương ứng

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang danh sách dự án. |  |
| 2 |  | Hệ thống hiển thị các dự án hiện có. |
| 3 | Nhấn nút “Tạo dự án”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm mã dự án, tên dự án, loại dự án, mô tả, chủ dự án, ngày bắt đầu và ngày kết thúc dự kiến. |
| 5 | Nhập các thông tin trên. |  |
| 6 | Xác nhận tạo dự án. |  |
| 7 |  | Hệ thống kiểm tra mã dự án, thông tin chủ dự án và thời gian thực hiện. |
| 8 |  | Thông tin hợp lệ, hệ thống tạo dự án với trạng thái hoạt động. |
| 9 |  | Hiển thị dự án vừa tạo trong danh sách. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn dự án cần xem. |  |
| 3.1.2 |  | Hệ thống chuyển đến trang tổng quan của dự án, hiển thị thông tin và tiến độ kiểm thử. |
| 3.1.3 | Truy cập trang cài đặt dự án. |  |
| 3.1.4 |  | Hệ thống hiển thị thông tin chi tiết của dự án. |
| 3.1.5 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập mã hoặc tên dự án vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các dự án phù hợp với từ khóa. |
| 3.2.3 | Chọn dự án cần xem. |  |
| 3.2.4 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | Chọn dự án cần chỉnh sửa và truy cập trang cài đặt. |  |
| 3.3.2 |  | Hệ thống hiển thị thông tin hiện tại của dự án. |
| 3.3.3 | Thay đổi tên, loại dự án, mô tả, thời gian dự kiến hoặc thông tin chủ dự án, trưởng dự án. |  |
| 3.3.4 | Nhấn nút “Lưu thay đổi”. |  |
| 3.3.5 |  | Hệ thống kiểm tra thông tin vừa chỉnh sửa. |
| 3.3.6 |  | Thông tin hợp lệ, nội dung thay đổi được lưu vào dự án. |
| 3.3.7 |  | Kết thúc chức năng. |
| 3.4.1 | Quản trị viên hệ thống mở chức năng quản trị nền tảng và chọn dự án cần xóa cứng. |  |
| 3.4.2 | Chọn chức năng xóa cứng dự án. |  |
| 3.4.3 |  | Hệ thống yêu cầu nhập mã dự án và lý do xóa. |
| 3.4.4 | Nhập mã dự án và lý do xóa. |  |
| 3.4.5 | Xác nhận xóa. |  |
| 3.4.6 |  | Hệ thống đối chiếu mã xác nhận với mã của dự án cần xóa. |
| 3.4.7 |  | Thông tin xác nhận hợp lệ, hệ thống xóa dự án và dữ liệu liên quan theo quy trình quản trị, đồng thời ghi nhận lịch sử thao tác. |
| 3.4.8 |  | Cập nhật danh sách dự án. Kết thúc chức năng. |
| 3.5.1 | Chọn dự án cần lưu trữ và truy cập trang cài đặt. |  |
| 3.5.2 | Nhấn nút “Lưu trữ dự án”. |  |
| 3.5.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do lưu trữ. |
| 3.5.4 | Nhập lý do và xác nhận. |  |
| 3.5.5 |  | Hệ thống chuyển dự án sang trạng thái đã lưu trữ. Dữ liệu được giữ lại nhưng không thể tiếp tục chỉnh sửa. |
| 3.5.6 |  | Chuyển về trang danh sách dự án. Kết thúc chức năng. |
| 3.6.1 | Truy cập danh sách dự án đã lưu trữ. |  |
| 3.6.2 |  | Hệ thống hiển thị các dự án đã lưu trữ. |
| 3.6.3 | Chọn dự án cần khôi phục và nhấn nút “Khôi phục dự án”. |  |
| 3.6.4 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do khôi phục. |
| 3.6.5 | Nhập lý do và xác nhận. |  |
| 3.6.6 |  | Dự án được đưa trở lại trạng thái hoạt động. |
| 3.6.7 |  | Cập nhật danh sách dự án. Kết thúc chức năng. |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng biểu mẫu và không tạo dự án. |
| 7.1 |  | Mã dự án đã tồn tại, hệ thống yêu cầu nhập mã khác và quay về bước 5. |
| 7.2 |  | Ngày kết thúc dự kiến trước ngày bắt đầu, hệ thống yêu cầu điều chỉnh thời gian. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.5.1 |  | Người được chọn làm trưởng dự án không phải thành viên đang hoạt động của dự án, hệ thống không lưu thay đổi. |
| 3.4.6.1 |  | Mã xác nhận không trùng với mã dự án, hệ thống từ chối xóa. |
| 7.3 |  | Tài khoản được chọn làm chủ dự án không hoạt động, hệ thống từ chối tạo dự án. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép người có quyền quản lý dự án tạo, xem, tìm kiếm, chỉnh sửa, lưu trữ và khôi phục dự án; thao tác xóa cứng thuộc quy trình quản trị nền tảng. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC09 - Quản lý thành viên dự án

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép quản trị viên quản lý thành viên thông qua việc gửi lời mời tham gia, cập nhật vai trò, thay đổi trạng thái và loại bỏ thành viên khỏi dự án.

**Tiền điều kiện:** Người dùng đã đăng nhập, có quyền quản lý thành viên trong dự án và dự án đang hoạt động.

**Hậu điều kiện:** Lời mời tham gia, danh sách thành viên và quyền truy cập dự án được cập nhật.

**Tác nhân chính:** Người dùng có quyền quản lý thành viên

**Tác nhân phụ:** Người được mời tham gia dự án

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | quản trị viên chọn dự án và truy cập mục quản lý thành viên. |  |
| 2 |  | Hệ thống hiển thị danh sách thành viên, vai trò và trạng thái tham gia dự án. |
| 3 | Người dùng có quyền quản lý thành viên nhập thông tin tài khoản cần mời và chọn vai trò tương ứng. |  |
| 4 | Nhấn nút “Gửi lời mời”. |  |
| 5 |  | Hệ thống kiểm tra tài khoản và vai trò được chọn. |
| 6 |  | Thông tin hợp lệ, hệ thống tạo lời mời tham gia dự án. |
| 7 | Người được mời truy cập trang danh sách dự án. |  |
| 8 |  | Hệ thống hiển thị lời mời tham gia dự án. |
| 9 | Người được mời chấp nhận lời mời. |  |
| 10 |  | Hệ thống cập nhật danh sách thành viên và cấp quyền truy cập theo vai trò được phân công. |
| 11 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Người dùng có quyền quản lý thành viên chọn tài khoản chưa chấp nhận lời mời. |  |
| 3.1.2 | Nhấn nút “Gửi lại lời mời”. |  |
| 3.1.3 |  | Hệ thống cập nhật lời mời tham gia dự án. |
| 3.1.4 |  | Kết thúc chức năng. |
| 3.2.1 | Người dùng có quyền quản lý thành viên chọn lời mời cần hủy. |  |
| 3.2.2 | Nhấn nút “Hủy lời mời”. |  |
| 3.2.3 |  | Hệ thống hủy lời mời và cập nhật danh sách thành viên. |
| 3.2.4 |  | Kết thúc chức năng. |
| 3.3.1 | Người dùng có quyền quản lý thành viên chọn thành viên cần cập nhật. |  |
| 3.3.2 |  | Hệ thống hiển thị vai trò hiện tại của thành viên. |
| 3.3.3 | Chọn vai trò mới và xác nhận. |  |
| 3.3.4 |  | Hệ thống kiểm tra và lưu vai trò mới của thành viên. |
| 3.3.5 |  | Kết thúc chức năng. |
| 3.4.1 | Người dùng có quyền quản lý thành viên chọn thành viên cần thay đổi trạng thái. |  |
| 3.4.2 | Chọn vô hiệu hóa hoặc kích hoạt lại thành viên. |  |
| 3.4.3 |  | Hệ thống cập nhật trạng thái và quyền truy cập dự án của thành viên tương ứng. |
| 3.4.4 |  | Kết thúc chức năng. |
| 3.5.1 | Người dùng có quyền quản lý thành viên chọn thành viên cần xóa khỏi dự án. |  |
| 3.5.2 | Nhấn nút “Xóa thành viên”. |  |
| 3.5.3 |  | Hệ thống hiển thị hộp thoại xác nhận. |
| 3.5.4 | Xác nhận xóa. |  |
| 3.5.5 |  | Hệ thống loại bỏ thành viên khỏi dự án và thu hồi quyền truy cập dự án của thành viên đó. |
| 3.5.6 |  | Cập nhật danh sách thành viên. Kết thúc chức năng. |
| 9.1.1 | Người được mời từ chối tham gia dự án. |  |
| 9.1.2 |  | Hệ thống ghi nhận việc từ chối và không cấp quyền truy cập dự án. |
| 9.1.3 |  | Kết thúc chức năng. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.5.5.1 |  | Thành viên cần xóa đang giữ trách nhiệm trưởng dự án, hệ thống yêu cầu chuyển trách nhiệm trước khi xóa thành viên. |
| 5.1 |  | Tài khoản hoặc vai trò được chọn không hợp lệ, hệ thống từ chối tạo lời mời. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép quản trị viên quản lý thành viên thông qua việc gửi lời mời tham gia, cập nhật vai trò, thay đổi trạng thái và loại bỏ thành viên khỏi dự án. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC10 - Quản lý yêu cầu

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này hỗ trợ chuyên viên phân tích nghiệp vụ (BA) xây dựng, tra cứu, chỉnh sửa và lưu trữ nội dung yêu cầu theo từng phiên bản.

**Tiền điều kiện:** chuyên viên phân tích nghiệp vụ (BA) đã đăng nhập, tham gia dự án và được cấp quyền quản lý yêu cầu.

**Hậu điều kiện:** Yêu cầu mới được tạo hoặc nội dung yêu cầu được cập nhật. Lịch sử các phiên bản trước vẫn được giữ lại.

**Tác nhân chính:** chuyên viên phân tích nghiệp vụ (BA)

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang yêu cầu của dự án. |  |
| 2 |  | Hệ thống hiển thị danh sách yêu cầu. |
| 3 | Nhấn nút “Tạo yêu cầu”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm tên yêu cầu, loại yêu cầu, mức ưu tiên, nội dung, tiêu chí chấp nhận, quy tắc nghiệp vụ và người phụ trách. |
| 5 | Nhập các thông tin trên. |  |
| 6 | Nhấn nút “Lưu yêu cầu”. |  |
| 7 |  | Hệ thống kiểm tra tên, nội dung và các thông tin bắt buộc của yêu cầu. |
| 8 |  | Thông tin hợp lệ, hệ thống tạo mã yêu cầu, lưu phiên bản đầu tiên với trạng thái “Sẵn sàng”. |
| 9 |  | Hiển thị yêu cầu vừa tạo trong danh sách. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn yêu cầu cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị nội dung, tiêu chí chấp nhận, quy tắc nghiệp vụ, người phụ trách, phiên bản và trạng thái yêu cầu. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập từ khóa vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các yêu cầu phù hợp với từ khóa. |
| 3.2.3 | Chọn yêu cầu cần xem. |  |
| 3.2.4 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | Chọn yêu cầu đang ở trạng thái bản nháp. |  |
| 3.3.2 |  | Hệ thống hiển thị nội dung có thể chỉnh sửa. |
| 3.3.3 | Chỉnh sửa tên, nội dung, tiêu chí chấp nhận, quy tắc nghiệp vụ hoặc các thông tin liên quan. |  |
| 3.3.4 | Nhấn nút “Lưu bản nháp”. |  |
| 3.3.4.1 | Nhấn nút “Lưu yêu cầu”. |  |
| 3.3.4.2 |  | Nội dung hợp lệ được lưu. Yêu cầu chuyển sang trạng thái “Sẵn sàng”. |
| 3.3.4.3 |  | Kết thúc chức năng. |
| 3.3.5 |  | Hệ thống kiểm tra và lưu nội dung thay đổi, giữ nguyên trạng thái bản nháp. |
| 3.3.6 |  | Kết thúc chức năng. |
| 3.4.1 | Chọn yêu cầu đang ở trạng thái sẵn sàng hoặc đã được chấp nhận. |  |
| 3.4.2 |  | Hệ thống hiển thị nội dung phiên bản hiện tại. |
| 3.4.3 | Nhấn nút “Tạo bản nháp để chỉnh sửa”. |  |
| 3.4.4 |  | Hệ thống hiển thị hộp thoại gồm tên yêu cầu và lý do thay đổi. |
| 3.4.5 | Nhập thông tin và xác nhận. |  |
| 3.4.6 |  | Hệ thống tạo bản nháp của phiên bản mới từ nội dung phiên bản hiện tại. |
| 3.4.7 |  | Hiển thị bản nháp vừa tạo. Tiếp tục chỉnh sửa tại bước 3.3.3. |
| 3.5.1 | Truy cập lịch sử phiên bản của yêu cầu. |  |
| 3.5.2 |  | Hệ thống hiển thị danh sách các phiên bản đã lưu. |
| 3.5.3 | Chọn phiên bản cần xem. |  |
| 3.5.4 |  | Hệ thống hiển thị nội dung của phiên bản được chọn. |
| 3.5.5 | Chọn các phiên bản cần so sánh. |  |
| 3.5.6 |  | Hệ thống hiển thị những nội dung khác nhau giữa các phiên bản. |
| 3.5.7 |  | Kết thúc chức năng. |
| 3.6.1 | Chọn các yêu cầu cần thay đổi nhãn. |  |
| 3.6.2 | Chọn chức năng cập nhật nhãn hàng loạt. |  |
| 3.6.3 |  | Hệ thống hiển thị thao tác thêm hoặc loại bỏ nhãn. |
| 3.6.4 | Nhập nhãn cần thêm hoặc loại bỏ, rồi xác nhận. |  |
| 3.6.5 |  | Hệ thống cập nhật nhãn cho các yêu cầu hợp lệ và trả kết quả từng mục. |
| 3.6.6 |  | Kết thúc chức năng. |
| 6.1.1 | Nhấn nút “Lưu nháp”. |  |
| 6.1.2 |  | Hệ thống kiểm tra thông tin và lưu yêu cầu với trạng thái “Bản nháp”. |
| 6.1.3 |  | Cập nhật danh sách yêu cầu. Kết thúc chức năng. |
| 6.2 | Nhấn nút “Hủy”. |  |
| 6.3 |  | Hệ thống chuyển về danh sách yêu cầu, không tạo yêu cầu mới. |
| 7.1 |  | Tên hoặc nội dung yêu cầu bị bỏ trống, hệ thống yêu cầu bổ sung thông tin tại bước 5. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.5.1 |  | Yêu cầu không còn ở trạng thái bản nháp, hệ thống không cho phép chỉnh sửa trực tiếp. |
| 3.4.6.1 |  | Phiên bản hiện tại đã thay đổi trước khi tạo bản nháp mới, hệ thống từ chối sử dụng phiên bản cũ. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này hỗ trợ chuyên viên phân tích nghiệp vụ (BA) xây dựng, tra cứu, chỉnh sửa và lưu trữ nội dung yêu cầu theo từng phiên bản. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC11 - Trình duyệt yêu cầu

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép chuyên viên phân tích nghiệp vụ (BA) gửi yêu cầu đã soạn thảo đến quản trị viên để kiểm tra trước khi sử dụng làm cơ sở kiểm thử.

**Tiền điều kiện:** Yêu cầu đang ở trạng thái bản nháp hoặc sẵn sàng. chuyên viên phân tích nghiệp vụ (BA) được cấp quyền gửi rà soát.

**Hậu điều kiện:** Yêu cầu được chuyển sang trạng thái đang rà soát.

**Tác nhân chính:** chuyên viên phân tích nghiệp vụ (BA)

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn yêu cầu cần trình duyệt. |  |
| 2 |  | Hệ thống hiển thị nội dung và trạng thái hiện tại của yêu cầu. |
| 3 | Nhấn nút “Gửi rà soát”. |  |
| 4 |  | Hệ thống hiển thị hộp thoại gửi rà soát và ô nhập ghi chú. |
| 5 | Nhập ghi chú nếu cần. |  |
| 6 | Xác nhận gửi rà soát. |  |
| 7 |  | Hệ thống lưu những nội dung chưa được lưu và kiểm tra thông tin yêu cầu. |
| 8 |  | Nội dung hợp lệ, yêu cầu được chuyển sang trạng thái “Đang rà soát”. |
| 9 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.1 | Chọn yêu cầu đang rà soát và nhấn “Mở lại để chỉnh sửa”. |  |
| 1.1.2 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do. |
| 1.1.3 | Nhập lý do và nhấn “Mở bản nháp”. |  |
| 1.1.4 |  | Hệ thống chuyển yêu cầu về trạng thái “Bản nháp”. |
| 1.1.5 | Tiếp tục chỉnh sửa yêu cầu theo UC10. |  |
| 1.1.6 |  | Kết thúc chức năng. |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng hộp thoại và giữ nguyên trạng thái yêu cầu. |
| 7.1 |  | Nội dung yêu cầu chưa được nhập đầy đủ, hệ thống yêu cầu bổ sung trước khi gửi rà soát. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.2 |  | Yêu cầu không còn ở trạng thái cho phép gửi rà soát, hệ thống từ chối thực hiện. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép chuyên viên phân tích nghiệp vụ (BA) gửi yêu cầu đã soạn thảo đến quản trị viên để kiểm tra trước khi sử dụng làm cơ sở kiểm thử. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC12 - Xét duyệt yêu cầu

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép quản trị viên rà soát nội dung yêu cầu, chấp nhận yêu cầu hoặc trả về bản nháp để chuyên viên phân tích nghiệp vụ (BA) chỉnh sửa.

**Tiền điều kiện:** quản trị viên đã đăng nhập và yêu cầu đang chờ xét duyệt.

**Hậu điều kiện:** Yêu cầu được chấp nhận, ghi nhận kết quả rà soát hoặc chuyển về bản nháp.

**Tác nhân chính:** quản trị viên

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn yêu cầu đang chờ xét duyệt. |  |
| 2 |  | Hệ thống hiển thị nội dung yêu cầu, tiêu chí chấp nhận, quy tắc nghiệp vụ và các thông tin liên quan. |
| 3 | Kiểm tra nội dung yêu cầu. |  |
| 4 | Chọn chức năng chấp nhận yêu cầu. |  |
| 5 |  | Hệ thống hiển thị hộp thoại xác nhận và ô nhập ghi chú phê duyệt. |
| 6 | Nhập ghi chú nếu cần và xác nhận. |  |
| 7 |  | Hệ thống kiểm tra trạng thái yêu cầu và những vấn đề cần xử lý trước khi phê duyệt. |
| 8 |  | Yêu cầu đáp ứng quy định phê duyệt, phiên bản được chấp nhận và sử dụng làm cơ sở cho hoạt động kiểm thử. |
| 9 |  | Cập nhật trạng thái yêu cầu. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 4.1.1 | Nhấn nút “Ghi nhận rà soát”. |  |
| 4.1.2 |  | Hệ thống hiển thị hộp thoại nhập nội dung rà soát. |
| 4.1.3 | Nhập ghi chú và xác nhận. |  |
| 4.1.4 |  | Hệ thống lưu kết quả rà soát, yêu cầu vẫn ở trạng thái đang rà soát. |
| 4.1.5 |  | Kết thúc chức năng. |
| 4.2.1 | Nhấn nút “Yêu cầu chỉnh sửa”. |  |
| 4.2.2 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do và nội dung cần chỉnh sửa. |
| 4.2.3 | Nhập nhận xét và nhấn “Trả về bản nháp”. |  |
| 4.2.4 |  | Hệ thống lưu nhận xét và chuyển yêu cầu về trạng thái “Bản nháp”. |
| 4.2.5 |  | Kết thúc chức năng. |
| 6.1 | Hủy thao tác phê duyệt. |  |
| 6.2 |  | Hệ thống đóng hộp thoại, giữ nguyên trạng thái yêu cầu. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.1 |  | Yêu cầu còn vấn đề được xác định là bắt buộc phải chỉnh sửa, hệ thống không cho phép phê duyệt. |
| 7.2 |  | Nội dung yêu cầu đã thay đổi sau khi quản trị viên mở giao diện rà soát, hệ thống từ chối phê duyệt phiên bản đang xem. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép quản trị viên rà soát nội dung yêu cầu, chấp nhận yêu cầu hoặc trả về bản nháp để chuyên viên phân tích nghiệp vụ (BA) chỉnh sửa. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC13 - Quản lý hiệu lực yêu cầu

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép thay đổi hiệu lực từng yêu cầu hoặc một nhóm yêu cầu, đồng thời khôi phục yêu cầu riêng lẻ khi cần sử dụng lại.

**Tiền điều kiện:** chuyên viên phân tích nghiệp vụ (BA) đã đăng nhập và được cấp quyền thay đổi hiệu lực yêu cầu.

**Hậu điều kiện:** Yêu cầu được đánh dấu không còn hiệu lực hoặc khôi phục về trạng thái trước đó. Nội dung và lịch sử yêu cầu không bị xóa.

**Tác nhân chính:** chuyên viên phân tích nghiệp vụ (BA)

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn yêu cầu cần ngừng sử dụng. |  |
| 2 |  | Hệ thống hiển thị nội dung và trạng thái hiện tại. |
| 3 | Nhấn nút “Đánh dấu không còn hiệu lực”. |  |
| 4 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do. |
| 5 | Nhập lý do ngừng sử dụng. |  |
| 6 | Xác nhận thay đổi hiệu lực yêu cầu. |  |
| 7 |  | Hệ thống kiểm tra trạng thái hiện tại của yêu cầu. |
| 8 |  | Yêu cầu được chuyển sang trạng thái “Không còn hiệu lực”. Lịch sử các phiên bản được giữ lại. |
| 9 |  | Cập nhật danh sách yêu cầu. Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.1 | Chọn yêu cầu không còn hiệu lực. |  |
| 1.1.2 |  | Hệ thống hiển thị thông tin yêu cầu và chức năng khôi phục. |
| 1.1.3 | Nhấn nút “Khôi phục yêu cầu”. |  |
| 1.1.4 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do khôi phục. |
| 1.1.5 | Nhập lý do và xác nhận. |  |
| 1.1.6 |  | Yêu cầu được khôi phục về trạng thái trước khi ngừng hiệu lực. |
| 1.1.7 |  | Cập nhật danh sách yêu cầu. Kết thúc chức năng. |
| 1.2.1 | Chọn nhiều yêu cầu cần ngừng sử dụng. |  |
| 1.2.2 | Chọn chức năng lưu trữ hàng loạt. |  |
| 1.2.3 |  | Hệ thống hiển thị hộp thoại nhập lý do và có thể xem trước các mục đủ điều kiện. |
| 1.2.4 | Nhập lý do, xem trước nếu cần và xác nhận. |  |
| 1.2.5 |  | Hệ thống chuyển các yêu cầu hợp lệ sang trạng thái không còn hiệu lực, đồng thời trả kết quả xử lý từng mục. |
| 1.2.6 |  | Kết thúc chức năng. |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng hộp thoại và không thay đổi hiệu lực yêu cầu. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.1 |  | Trạng thái yêu cầu không cho phép thực hiện thao tác đã chọn, hệ thống từ chối cập nhật. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép thay đổi hiệu lực từng yêu cầu hoặc một nhóm yêu cầu, đồng thời khôi phục yêu cầu riêng lẻ khi cần sử dụng lại. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC14 - Tổ chức yêu cầu

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này hỗ trợ chuyên viên phân tích nghiệp vụ (BA) kiểm tra nội dung trùng lặp và tổ chức lại yêu cầu thông qua việc tách hoặc gộp yêu cầu.

**Tiền điều kiện:** Dự án đã có yêu cầu. chuyên viên phân tích nghiệp vụ (BA) được cấp quyền thực hiện chức năng tương ứng.

**Hậu điều kiện:** Kết quả kiểm tra trùng lặp được hiển thị hoặc các yêu cầu mới được hình thành từ nội dung yêu cầu hiện có.

**Tác nhân chính:** chuyên viên phân tích nghiệp vụ (BA)

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang danh sách yêu cầu. |  |
| 2 |  | Hệ thống hiển thị các yêu cầu trong dự án. |
| 3 | Chọn ít nhất hai yêu cầu cần kiểm tra trùng lặp. |  |
| 4 | Chọn chức năng kiểm tra trùng lặp. |  |
| 5 |  | Hệ thống đối chiếu nội dung các yêu cầu được chọn. |
| 6 |  | Hiển thị các cặp yêu cầu có khả năng trùng lặp. |
| 7 | Xem kết quả kiểm tra. |  |
| 8 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Không chọn yêu cầu cụ thể và thực hiện kiểm tra trùng lặp. |  |
| 3.1.2 |  | Hệ thống đối chiếu nội dung các yêu cầu trong dự án và hiển thị kết quả. |
| 3.1.3 |  | Tiếp tục tại bước 7. |
| 3.2.1 | Chọn một yêu cầu đã được chấp nhận và thực hiện tách yêu cầu. |  |
| 3.2.2 |  | Hệ thống hiển thị biểu mẫu gồm tên, nội dung, tiêu chí chấp nhận của các yêu cầu mới và lý do tách. |
| 3.2.3 | Nhập nội dung cho từng yêu cầu sau khi tách. |  |
| 3.2.4 | Xác nhận tách yêu cầu. |  |
| 3.2.5 |  | Hệ thống kiểm tra số lượng yêu cầu mới và sự tương ứng giữa tên, nội dung, tiêu chí chấp nhận. |
| 3.2.5.1 |  | Số lượng yêu cầu sau khi tách ít hơn hai hoặc nội dung không tương ứng với số lượng yêu cầu, hệ thống yêu cầu điều chỉnh tại bước 3.2.3. |
| 3.2.6 |  | Thông tin hợp lệ, hệ thống tạo các yêu cầu mới dưới dạng bản nháp và đánh dấu yêu cầu ban đầu đã được thay thế. |
| 3.2.7 |  | Hiển thị yêu cầu mới được tạo. Kết thúc chức năng. |
| 3.3.1 | Chọn ít nhất hai yêu cầu đã được chấp nhận và thực hiện gộp yêu cầu. |  |
| 3.3.2 |  | Hệ thống hiển thị biểu mẫu gồm tên yêu cầu mới, loại yêu cầu, nội dung, tiêu chí chấp nhận và lý do gộp. |
| 3.3.3 | Nhập nội dung của yêu cầu sau khi gộp. |  |
| 3.3.4 | Xác nhận gộp yêu cầu. |  |
| 3.3.5 |  | Hệ thống kiểm tra nội dung vừa nhập và trạng thái các yêu cầu được chọn. |
| 3.3.6 |  | Hệ thống tạo yêu cầu mới với trạng thái “Bản nháp”, đồng thời đánh dấu các yêu cầu ban đầu đã được thay thế. |
| 3.3.7 |  | Hiển thị yêu cầu vừa tạo. Kết thúc chức năng. |
| 5.1 |  | Chỉ có một yêu cầu được chọn, hệ thống yêu cầu chọn thêm yêu cầu hoặc bỏ chọn để kiểm tra toàn bộ dự án. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.5.2 |  | Yêu cầu cần tách chưa được chấp nhận hoặc không còn hiệu lực, hệ thống từ chối thực hiện. |
| 3.3.5.1 |  | Có yêu cầu trong danh sách chưa được chấp nhận hoặc đã thay đổi phiên bản, hệ thống không thực hiện gộp. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này hỗ trợ chuyên viên phân tích nghiệp vụ (BA) kiểm tra nội dung trùng lặp và tổ chức lại yêu cầu thông qua việc tách hoặc gộp yêu cầu. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC15 - Quản lý tài liệu nguồn

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép chuyên viên phân tích nghiệp vụ (BA) quản lý các tài liệu dùng làm căn cứ xây dựng yêu cầu, bao gồm tải lên, xem, cập nhật, chia sẻ, tải xuống, lưu trữ và khôi phục tài liệu.

**Tiền điều kiện:** chuyên viên phân tích nghiệp vụ (BA) đã đăng nhập, tham gia dự án và được cấp quyền quản lý tài liệu.

**Hậu điều kiện:** Tài liệu nguồn được lưu hoặc cập nhật theo thao tác của chuyên viên phân tích nghiệp vụ (BA). Nội dung tài liệu đã xử lý có thể được sử dụng làm căn cứ xây dựng yêu cầu.

**Tác nhân chính:** chuyên viên phân tích nghiệp vụ (BA)

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập mục tài liệu nguồn của dự án. |  |
| 2 |  | Hệ thống hiển thị danh sách tài liệu hiện có. |
| 3 | Chọn chức năng thêm tài liệu. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu tải tài liệu, gồm tệp nguồn, loại tài liệu và quyền xem tài liệu. |
| 5 | Chọn một hoặc nhiều tệp cần tải lên. |  |
| 6 | Xác định loại tài liệu, phạm vi chia sẻ và quyền sử dụng tài liệu bằng AI. |  |
| 7 | Nhấn nút “Lưu tài liệu”. |  |
| 8 |  | Hệ thống kiểm tra tài liệu trùng lặp hoặc có nội dung tương tự. |
| 9 |  | Tài liệu được chấp nhận, hệ thống lưu tệp gốc và thực hiện trích xuất nội dung. |
| 10 |  | Hiển thị tài liệu cùng trạng thái xử lý. |
| 11 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn tài liệu cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị nội dung tài liệu và các thông tin liên quan. |
| 3.1.3 | Nhập từ khóa tìm kiếm trong tài liệu nếu cần. |  |
| 3.1.4 |  | Hệ thống hiển thị những nội dung phù hợp với từ khóa. |
| 3.1.5 |  | Kết thúc chức năng. |
| 3.2.1 | Chọn tài liệu cần chỉnh sửa. |  |
| 3.2.2 | Mở chức năng cập nhật thông tin tài liệu. |  |
| 3.2.3 |  | Hệ thống hiển thị thông tin hiện tại có thể chỉnh sửa. |
| 3.2.4 | Thay đổi thông tin và xác nhận lưu. |  |
| 3.2.5 |  | Hệ thống kiểm tra và lưu nội dung thay đổi. |
| 3.2.6 |  | Kết thúc chức năng. |
| 3.3.1 | Chọn tài liệu và mở chức năng thay đổi quyền xem. |  |
| 3.3.2 |  | Hệ thống hiển thị các phạm vi chia sẻ tài liệu. |
| 3.3.3 | Chọn phạm vi chia sẻ và thành viên được xem tài liệu nếu cần. |  |
| 3.3.4 | Xác nhận thay đổi quyền xem. |  |
| 3.3.5 |  | Hệ thống cập nhật quyền truy cập tài liệu. |
| 3.3.6 |  | Kết thúc chức năng. |
| 3.4.1 | Chọn tài liệu và thực hiện tải xuống. |  |
| 3.4.2 |  | Hệ thống cung cấp tệp tài liệu gốc để tải xuống. |
| 3.4.3 |  | Kết thúc chức năng. |
| 3.5.1 | Chọn tài liệu cần ngừng sử dụng. |  |
| 3.5.2 | Nhấn nút “Lưu trữ”. |  |
| 3.5.3 |  | Hệ thống hiển thị hộp thoại xác nhận. |
| 3.5.4 | Xác nhận lưu trữ. |  |
| 3.5.5 |  | Hệ thống lưu trữ tài liệu và cập nhật danh sách. |
| 3.5.6 |  | Kết thúc chức năng. |
| 3.6.1 | Chọn tài liệu đã lưu trữ và thực hiện khôi phục. |  |
| 3.6.2 |  | Hệ thống hiển thị hộp thoại xác nhận. |
| 3.6.3 | Xác nhận khôi phục. |  |
| 3.6.4 |  | Hệ thống khôi phục tài liệu và cập nhật danh sách. |
| 3.6.5 |  | Kết thúc chức năng. |
| 5.1.1 | Chọn một tệp và xác định tài liệu phiên bản trước đó trong hệ thống. |  |
| 5.1.2 |  | Hệ thống tiếp nhận thông tin liên kết giữa tài liệu mới và tài liệu trước đó. |
| 5.1.3 |  | Tiếp tục tại bước 6. |
| 7.1 | Nhấn nút “Hủy”. |  |
| 7.2 |  | Hệ thống đóng biểu mẫu và không lưu tài liệu mới. |
| 8.1.1 |  | Hệ thống phát hiện tài liệu trùng hoặc tương tự và hiển thị kết quả đối chiếu. |
| 8.1.2 | Kiểm tra kết quả và lựa chọn cách xử lý. |  |
| 8.1.3 | Xác nhận tiếp tục. |  |
| 8.1.4 |  | Hệ thống lưu tệp mới, sử dụng tài liệu đã có hoặc bỏ qua tệp theo lựa chọn của chuyên viên phân tích nghiệp vụ (BA). |
| 8.1.5 |  | Cập nhật danh sách tài liệu. Kết thúc chức năng. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 9.1 |  | Quá trình trích xuất nội dung thất bại, hệ thống thông báo lỗi nhưng vẫn giữ lại tệp gốc. |
| 9.1.1 | Chọn chức năng tiếp tục xử lý tài liệu. |  |
| 9.1.2 |  | Hệ thống thực hiện lại quá trình trích xuất nội dung. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép chuyên viên phân tích nghiệp vụ (BA) quản lý các tài liệu dùng làm căn cứ xây dựng yêu cầu, bao gồm tải lên, xem, cập nhật, chia sẻ, tải xuống, lưu trữ và khôi phục tài liệu. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC16 - Quản lý kế hoạch kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép người kiểm thử xây dựng, tra cứu, chỉnh sửa, lưu nháp, nhân bản và lưu trữ kế hoạch kiểm thử của dự án.

**Tiền điều kiện:** người kiểm thử đã đăng nhập, tham gia dự án và được cấp quyền quản lý kế hoạch kiểm thử.

**Hậu điều kiện:** Kế hoạch kiểm thử được tạo mới, cập nhật, nhân bản hoặc lưu trữ.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang kế hoạch kiểm thử. |  |
| 2 |  | Hệ thống hiển thị danh sách kế hoạch kiểm thử của dự án. |
| 3 | Nhấn nút “Tạo kế hoạch”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm tên kế hoạch, mục tiêu, phạm vi, cách tiếp cận, loại kiểm thử, cấp độ kiểm thử, tiêu chí kiểm thử, môi trường, người phụ trách, thời gian dự kiến và rủi ro. |
| 5 | Nhập thông tin kế hoạch và chọn các yêu cầu thuộc phạm vi kiểm thử. |  |
| 6 | Nhấn nút “Lưu kế hoạch”. |  |
| 7 |  | Hệ thống kiểm tra mục tiêu, phạm vi yêu cầu, thời gian dự kiến và thông tin người phụ trách. |
| 8 |  | Thông tin hợp lệ, kế hoạch được tạo với trạng thái “Sẵn sàng”. |
| 9 |  | Hiển thị kế hoạch vừa tạo. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn kế hoạch cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị mục tiêu, phạm vi, tiêu chí kiểm thử, cách tiếp cận, người phụ trách, thời gian dự kiến, rủi ro và trạng thái kế hoạch. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập từ khóa vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các kế hoạch phù hợp. |
| 3.2.3 | Chọn điều kiện lọc nếu cần. |  |
| 3.2.4 |  | Danh sách kế hoạch được cập nhật theo điều kiện lọc. |
| 3.2.5 | Chọn kế hoạch cần xem. |  |
| 3.2.6 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | Chọn kế hoạch đang ở trạng thái bản nháp hoặc sẵn sàng. |  |
| 3.3.2 |  | Hệ thống hiển thị nội dung hiện tại của kế hoạch. |
| 3.3.3 | Chọn chức năng chỉnh sửa. |  |
| 3.3.4 |  | Hệ thống hiển thị biểu mẫu cập nhật kế hoạch. |
| 3.3.5 | Chỉnh sửa nội dung kế hoạch, bổ sung hoặc loại bỏ yêu cầu và ca kiểm thử thuộc phạm vi kế hoạch. |  |
| 3.3.6 | Nhấn nút “Lưu kế hoạch”. |  |
| 3.3.7 |  | Hệ thống kiểm tra nội dung và các liên kết kiểm thử sau khi thay đổi. |
| 3.3.8 |  | Thông tin hợp lệ, kế hoạch được cập nhật. |
| 3.3.9 |  | Kết thúc chức năng. |
| 3.4.1 | Chọn kế hoạch cần sao chép. |  |
| 3.4.2 | Chọn chức năng nhân bản kế hoạch. |  |
| 3.4.3 |  | Hệ thống sao chép nội dung kế hoạch và tạo kế hoạch mới với trạng thái “Bản nháp”. |
| 3.4.4 |  | Cập nhật danh sách kế hoạch. Kết thúc chức năng. |
| 3.5.1 | Chọn kế hoạch không còn sử dụng. |  |
| 3.5.2 | Nhấn nút “Lưu trữ kế hoạch”. |  |
| 3.5.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do lưu trữ. |
| 3.5.4 | Nhập lý do và xác nhận. |  |
| 3.5.5 |  | Kế hoạch được chuyển sang trạng thái “Đã lưu trữ”. Nội dung đã ghi nhận trước đó vẫn được giữ lại. |
| 3.5.6 |  | Cập nhật danh sách kế hoạch. Kết thúc chức năng. |
| 5.1.1 | Chọn tạo chu kỳ kiểm thử mới trong biểu mẫu kế hoạch. |  |
| 5.1.2 |  | Hệ thống hiển thị các trường thông tin của chu kỳ kiểm thử. |
| 5.1.3 | Nhập thông tin chu kỳ kiểm thử. |  |
| 5.1.3.1 | Chọn chu kỳ đã kết thúc làm nguồn cho chu kỳ mới. |  |
| 5.1.3.2 |  | Hệ thống tiếp nhận thông tin về các nội dung kiểm thử được chuyển tiếp từ chu kỳ trước. |
| 5.1.4 |  | Hệ thống tiếp nhận thông tin để tạo chu kỳ khi lưu kế hoạch. |
| 5.1.5 |  | Tiếp tục tại bước 6. |
| 6.1.1 | Nhấn nút “Lưu nháp”. |  |
| 6.1.2 |  | Hệ thống kiểm tra thông tin đã nhập và lưu kế hoạch với trạng thái “Bản nháp”. |
| 6.1.3 |  | Hiển thị kế hoạch trong danh sách. Kết thúc chức năng. |
| 6.2 | Nhấn nút “Hủy”. |  |
| 6.3 |  | Hệ thống chuyển về danh sách kế hoạch, không lưu kế hoạch mới. |
| 7.1 |  | Mục tiêu kiểm thử bị bỏ trống, hệ thống yêu cầu bổ sung tại bước 5. |
| 7.2 |  | Chưa xác định phạm vi yêu cầu, hệ thống yêu cầu chọn ít nhất một phiên bản yêu cầu. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.7.1 |  | Kế hoạch không còn ở trạng thái bản nháp hoặc sẵn sàng, hệ thống không cho phép chỉnh sửa trực tiếp. |
| 7.3 |  | Chu kỳ kiểm thử được chọn đã kết thúc, hệ thống không cho phép tạo kế hoạch thuộc chu kỳ đó. |
| 7.4 |  | Người phụ trách được chọn không còn là thành viên đang hoạt động của dự án, hệ thống từ chối lưu kế hoạch. |
| 7.5 |  | Yêu cầu, ca kiểm thử hoặc bộ kiểm thử được chọn không thuộc phạm vi hợp lệ của dự án, hệ thống không lưu kế hoạch. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép người kiểm thử xây dựng, tra cứu, chỉnh sửa, lưu nháp, nhân bản và lưu trữ kế hoạch kiểm thử của dự án. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC17 - Trình duyệt kế hoạch kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép người kiểm thử kiểm tra mức độ hoàn thiện của kế hoạch và gửi kế hoạch đến quản trị viên để xét duyệt.

**Tiền điều kiện:** Kế hoạch đang ở trạng thái bản nháp hoặc sẵn sàng. người kiểm thử được cấp quyền gửi rà soát.

**Hậu điều kiện:** Kế hoạch kiểm thử được chuyển sang trạng thái đang rà soát.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn kế hoạch cần trình duyệt. |  |
| 2 |  | Hệ thống hiển thị nội dung và trạng thái hiện tại của kế hoạch. |
| 3 | Nhấn nút “Gửi rà soát”. |  |
| 4 |  | Hệ thống hiển thị hộp thoại gửi rà soát và ô nhập ghi chú. |
| 5 | Nhập ghi chú gửi quản trị viên. |  |
| 6 | Xác nhận gửi rà soát. |  |
| 7 |  | Hệ thống kiểm tra mục tiêu, phạm vi yêu cầu, các ca kiểm thử được liên kết và trạng thái chu kỳ kiểm thử. |
| 8 |  | Kế hoạch đáp ứng điều kiện trình duyệt, hệ thống chuyển kế hoạch sang trạng thái “Đang rà soát”. |
| 9 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Nhấn nút “Kiểm tra kế hoạch”. |  |
| 3.1.2 |  | Hệ thống kiểm tra mục tiêu, phạm vi yêu cầu và phạm vi ca kiểm thử của kế hoạch. |
| 3.1.3 |  | Hiển thị kết quả kiểm tra và những nội dung cần bổ sung. |
| 3.1.4 | Xem kết quả, thực hiện chỉnh sửa kế hoạch theo UC16 nếu cần. |  |
| 3.1.5 | Tiếp tục gửi rà soát tại bước 3. |  |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng hộp thoại và giữ nguyên trạng thái kế hoạch. |
| 7.1 |  | Kế hoạch chưa có mục tiêu hoặc chưa xác định phạm vi yêu cầu, hệ thống yêu cầu bổ sung nội dung. |
| 7.2 |  | Kế hoạch chưa liên kết ca kiểm thử, hệ thống yêu cầu liên kết ít nhất một phiên bản ca kiểm thử trước khi gửi duyệt. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.3 |  | Chu kỳ kiểm thử liên quan đã kết thúc, hệ thống từ chối gửi rà soát. |
| 7.4 |  | Kế hoạch không còn ở trạng thái cho phép trình duyệt, hệ thống không thực hiện thay đổi trạng thái. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép người kiểm thử kiểm tra mức độ hoàn thiện của kế hoạch và gửi kế hoạch đến quản trị viên để xét duyệt. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC18 - Xét duyệt kế hoạch kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép quản trị viên xem xét nội dung kế hoạch, phê duyệt hoặc yêu cầu chỉnh sửa trước khi đưa vào thực hiện.

**Tiền điều kiện:** quản trị viên đã đăng nhập và kế hoạch kiểm thử đang chờ xét duyệt.

**Hậu điều kiện:** Kế hoạch được phê duyệt hoặc trả về bản nháp để người kiểm thử tiếp tục hoàn thiện.

**Tác nhân chính:** quản trị viên

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn kế hoạch kiểm thử đang chờ xét duyệt. |  |
| 2 |  | Hệ thống hiển thị nội dung chi tiết của kế hoạch. |
| 3 | Kiểm tra mục tiêu, phạm vi yêu cầu, ca kiểm thử, cách tiếp cận và tiêu chí kiểm thử. |  |
| 4 | Nhấn nút “Phê duyệt kế hoạch”. |  |
| 5 |  | Hệ thống kiểm tra kế hoạch và hiển thị hộp thoại xác nhận khi không phát hiện nội dung ngăn cản việc phê duyệt. |
| 6 | Nhập ghi chú và xác nhận phê duyệt. |  |
| 7 |  | Hệ thống kiểm tra lại phạm vi kiểm thử và nội dung kế hoạch. |
| 8 |  | Kế hoạch hợp lệ được chuyển sang trạng thái “Đã phê duyệt”. Nội dung tại thời điểm phê duyệt được giữ lại làm căn cứ thực hiện kiểm thử. |
| 9 |  | Cập nhật trạng thái kế hoạch. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 4.1.1 | Nhấn nút “Yêu cầu chỉnh sửa” khi nội dung chưa phù hợp. |  |
| 4.1.2 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập nhận xét. |
| 4.1.3 | Nhập nội dung cần chỉnh sửa. |  |
| 4.1.4 | Xác nhận yêu cầu chỉnh sửa. |  |
| 4.1.5 |  | Hệ thống lưu nhận xét và chuyển kế hoạch về trạng thái “Bản nháp”. |
| 4.1.6 |  | Kết thúc chức năng. |
| 5.1 |  | Kế hoạch thiếu mục tiêu, phạm vi yêu cầu hoặc phạm vi ca kiểm thử, hệ thống hiển thị những nội dung cần bổ sung và không tiếp tục phê duyệt. |
| 6.1 | Hủy thao tác phê duyệt. |  |
| 6.2 |  | Hệ thống đóng hộp thoại và giữ nguyên trạng thái kế hoạch. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.1 |  | Thành phần của bộ kiểm thử thuộc phạm vi kế hoạch đã thay đổi, hệ thống yêu cầu rà soát lại phạm vi kiểm thử. |
| 7.2 |  | Kế hoạch đã thay đổi nội dung trong quá trình xét duyệt, hệ thống không phê duyệt nội dung đang xem. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép quản trị viên xem xét nội dung kế hoạch, phê duyệt hoặc yêu cầu chỉnh sửa trước khi đưa vào thực hiện. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC19 - Quản lý điều kiện kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép người kiểm thử xác định, tra cứu và cập nhật những nội dung cần kiểm thử dựa trên cơ sở kiểm thử của dự án.

**Tiền điều kiện:** người kiểm thử đã tham gia dự án và được cấp quyền quản lý điều kiện kiểm thử.

**Hậu điều kiện:** Điều kiện kiểm thử được tạo mới, cập nhật, nhân bản hoặc lưu trữ.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang quản lý điều kiện kiểm thử. |  |
| 2 |  | Hệ thống hiển thị danh sách điều kiện kiểm thử. |
| 3 | Nhấn nút “Tạo điều kiện kiểm thử”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm tên, mô tả, cơ sở kiểm thử, cấp độ kiểm thử, loại kiểm thử, mức độ rủi ro và khả năng kiểm thử. |
| 5 | Nhập thông tin và chọn cơ sở kiểm thử liên quan. |  |
| 6 | Nhấn nút “Lưu điều kiện”. |  |
| 7 |  | Hệ thống kiểm tra nội dung và cơ sở kiểm thử được chọn. |
| 8 |  | Thông tin hợp lệ, hệ thống lưu điều kiện kiểm thử với trạng thái “Bản nháp”. |
| 9 |  | Cập nhật danh sách điều kiện kiểm thử. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn điều kiện kiểm thử cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị nội dung, cơ sở kiểm thử, mức độ rủi ro, khả năng kiểm thử và trạng thái. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập từ khóa vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các điều kiện kiểm thử phù hợp. |
| 3.2.3 | Chọn trạng thái cần lọc nếu cần. |  |
| 3.2.4 |  | Danh sách điều kiện kiểm thử được cập nhật theo trạng thái. |
| 3.3.1 | Chọn điều kiện kiểm thử đang ở trạng thái bản nháp. |  |
| 3.3.2 |  | Hệ thống hiển thị nội dung hiện tại. |
| 3.3.3 | Chọn chức năng chỉnh sửa. |  |
| 3.3.4 |  | Hệ thống hiển thị biểu mẫu cập nhật. |
| 3.3.5 | Chỉnh sửa nội dung điều kiện kiểm thử. |  |
| 3.3.6 | Nhấn nút “Lưu điều kiện”. |  |
| 3.3.7 |  | Hệ thống kiểm tra và lưu nội dung thay đổi. |
| 3.3.8 |  | Kết thúc chức năng. |
| 3.4.1 | Chọn điều kiện kiểm thử đã được phê duyệt. |  |
| 3.4.2 |  | Hệ thống hiển thị nội dung của điều kiện kiểm thử. |
| 3.4.3 | Nhấn nút “Tạo bản nháp mới”. |  |
| 3.4.4 |  | Hệ thống sao chép nội dung để tạo một điều kiện kiểm thử mới dưới dạng bản nháp. |
| 3.4.5 |  | Hiển thị bản nháp vừa tạo. |
| 3.4.6 | Chỉnh sửa nội dung và nhấn “Lưu điều kiện”. |  |
| 3.4.7 |  | Hệ thống lưu nội dung bản nháp sau khi kiểm tra. |
| 3.4.8 |  | Kết thúc chức năng. |
| 3.5.1 | Chọn điều kiện kiểm thử đang ở trạng thái bản nháp hoặc đã phê duyệt. |  |
| 3.5.2 | Nhấn nút “Lưu trữ”. |  |
| 3.5.3 |  | Hệ thống hiển thị hộp thoại xác nhận và ô nhập ghi chú. |
| 3.5.4 | Nhập ghi chú và xác nhận. |  |
| 3.5.5 |  | Hệ thống chuyển điều kiện kiểm thử sang trạng thái “Đã lưu trữ”. |
| 3.5.6 |  | Cập nhật danh sách điều kiện kiểm thử. Kết thúc chức năng. |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng biểu mẫu và không tạo điều kiện kiểm thử mới. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.7.1 |  | Điều kiện kiểm thử không còn ở trạng thái bản nháp, hệ thống không cho phép chỉnh sửa trực tiếp. |
| 3.4.4.1 |  | Điều kiện kiểm thử được chọn không còn ở trạng thái đã phê duyệt, hệ thống từ chối tạo bản nháp theo chức năng này. |
| 7.1 |  | Mã điều kiện kiểm thử bị trùng, hệ thống từ chối lưu bản ghi mới. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép người kiểm thử xác định, tra cứu và cập nhật những nội dung cần kiểm thử dựa trên cơ sở kiểm thử của dự án. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC20 - Xét duyệt điều kiện kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này hỗ trợ việc trình duyệt, rà soát và phê duyệt điều kiện kiểm thử. Những vấn đề được phát hiện trong quá trình phân tích có thể được phân công, xử lý và xác minh trước khi phê duyệt.

**Tiền điều kiện:** Điều kiện kiểm thử đã được tạo trong dự án.

**Hậu điều kiện:** Kết quả rà soát và xử lý phát hiện được ghi nhận. Điều kiện kiểm thử được phê duyệt khi không còn vấn đề ngăn cản việc phê duyệt.

**Tác nhân chính:** người kiểm thử, quản trị viên

**Tác nhân phụ:** Người được phân công xử lý phát hiện

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | người kiểm thử chọn điều kiện kiểm thử đang ở trạng thái bản nháp. |  |
| 2 |  | Hệ thống hiển thị nội dung điều kiện kiểm thử. |
| 3 | Nhấn nút “Gửi rà soát”. |  |
| 4 |  | Hệ thống hiển thị hộp thoại nhập ghi chú rà soát. |
| 5 | Nhập ghi chú và xác nhận. |  |
| 6 |  | Hệ thống kiểm tra nội dung, chuyển điều kiện kiểm thử sang trạng thái “Đang rà soát”. |
| 7 | quản trị viên chọn điều kiện kiểm thử đang chờ xét duyệt. |  |
| 8 |  | Hệ thống hiển thị nội dung, cơ sở kiểm thử và các vấn đề được phát hiện. |
| 9 | Kiểm tra nội dung và nhấn nút “Phê duyệt”. |  |
| 10 |  | Hệ thống hiển thị hộp thoại xác nhận phê duyệt. |
| 11 | Nhập ghi chú và xác nhận. |  |
| 12 |  | Hệ thống kiểm tra nội dung và các vấn đề ảnh hưởng đến khả năng kiểm thử chưa được giải quyết. |
| 13 |  | Điều kiện kiểm thử được chuyển sang trạng thái “Đã phê duyệt” nếu đáp ứng quy định phê duyệt. |
| 14 |  | Cập nhật danh sách điều kiện kiểm thử. |
| 15 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 6.1 |  | Điều kiện kiểm thử chưa có đầy đủ thông tin bắt buộc, hệ thống yêu cầu bổ sung nội dung trước khi gửi rà soát. |
| 9.1.1 | quản trị viên nhấn nút “Ghi nhận rà soát”. |  |
| 9.1.2 |  | Hệ thống hiển thị hộp thoại nhập nội dung rà soát. |
| 9.1.3 | Nhập ghi chú và xác nhận. |  |
| 9.1.4 |  | Kết quả rà soát được lưu, điều kiện kiểm thử vẫn ở trạng thái đang rà soát. |
| 9.1.5 |  | Kết thúc chức năng. |
| 9.2.1 | quản trị viên truy cập mục phát hiện và chọn vấn đề cần xử lý. |  |
| 9.2.2 |  | Hệ thống hiển thị nội dung phát hiện, mức độ và thông tin liên quan. |
| 9.2.3 | Nhấn nút “Phân công phát hiện”. |  |
| 9.2.4 |  | Hệ thống hiển thị giao diện lựa chọn người phụ trách. |
| 9.2.5 | Chọn thành viên và xác nhận phân công. |  |
| 9.2.6 |  | Hệ thống lưu thông tin người phụ trách và cập nhật trạng thái phát hiện. |
| 9.2.7 |  | Kết thúc chức năng. |
| 9.3.1 | Người được phân công chọn phát hiện cần xử lý. |  |
| 9.3.2 |  | Hệ thống hiển thị nội dung phát hiện và các thông tin liên quan. |
| 9.3.3 | Nhấn nút “Giải quyết phát hiện”. |  |
| 9.3.4 |  | Hệ thống hiển thị các trường kết quả xử lý, tham chiếu và ghi chú. |
| 9.3.5 | Chọn kết quả đã giải quyết, nhập tham chiếu và ghi chú. |  |
| 9.3.5.1 | quản trị viên chọn kết quả chấp nhận rủi ro, nhập tham chiếu và ghi chú. |  |
| 9.3.5.2 | Xác nhận kết quả xử lý. |  |
| 9.3.5.3 |  | Hệ thống ghi nhận việc chấp nhận rủi ro của phát hiện tương ứng. |
| 9.3.5.4 |  | Kết thúc chức năng. |
| 9.3.6 | Xác nhận kết quả xử lý. |  |
| 9.3.7 |  | Hệ thống lưu kết quả và cập nhật trạng thái phát hiện. |
| 9.3.8 |  | Kết thúc chức năng. |
| 9.4.1 | quản trị viên chọn phát hiện đã được giải quyết. |  |
| 9.4.2 |  | Hệ thống hiển thị nội dung và kết quả xử lý của phát hiện. |
| 9.4.3 | Nhấn nút “Xác minh phát hiện”. |  |
| 9.4.4 |  | Hệ thống hiển thị hộp thoại nhập kết quả xác minh. |
| 9.4.5 | Nhập kết quả xác minh và xác nhận. |  |
| 9.4.6 |  | Hệ thống lưu kết quả xác minh và cập nhật trạng thái phát hiện. |
| 9.4.7 |  | Kết thúc chức năng. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 9.2.6.1 |  | Người được chọn không phải thành viên hợp lệ của dự án, hệ thống không thực hiện phân công. |
| 12.1 |  | Điều kiện kiểm thử còn vấn đề ảnh hưởng đến khả năng kiểm thử chưa được giải quyết, hệ thống từ chối phê duyệt. |
| 12.2 |  | Nội dung điều kiện kiểm thử đã thay đổi trong quá trình xét duyệt, hệ thống không phê duyệt nội dung cũ. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này hỗ trợ việc trình duyệt, rà soát và phê duyệt điều kiện kiểm thử. Những vấn đề được phát hiện trong quá trình phân tích có thể được phân công, xử lý và xác minh trước khi phê duyệt. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC21 - Quản lý ca kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này hỗ trợ người kiểm thử xây dựng, tra cứu và duy trì các ca kiểm thử. Các thao tác bao gồm tạo mới, chỉnh sửa, lưu nháp, xóa bản nháp, nhân bản, lưu trữ và khôi phục.

**Tiền điều kiện:** người kiểm thử đã đăng nhập, tham gia dự án và được cấp quyền quản lý ca kiểm thử.

**Hậu điều kiện:** Ca kiểm thử được tạo mới hoặc cập nhật theo thao tác của người kiểm thử. Những phiên bản đã phê duyệt được giữ lại trong lịch sử.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang ca kiểm thử của dự án. |  |
| 2 |  | Hệ thống hiển thị danh sách ca kiểm thử. |
| 3 | Nhấn nút “Tạo ca kiểm thử”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm tên, mục tiêu, loại kiểm thử, mức ưu tiên, người phụ trách, thời gian thực hiện dự kiến, tiền điều kiện, các bước thực hiện, dữ liệu kiểm thử, kết quả mong đợi và hậu điều kiện. |
| 5 | Nhập thông tin ca kiểm thử, xác định yêu cầu hoặc điều kiện kiểm thử liên quan. |  |
| 6 | Nhấn nút “Lưu ca kiểm thử”. |  |
| 7 |  | Hệ thống kiểm tra nội dung ca kiểm thử, hành động và kết quả mong đợi của các bước, đồng thời kiểm tra cơ sở kiểm thử được liên kết. |
| 8 |  | Thông tin hợp lệ, hệ thống tạo mã ca kiểm thử và lưu với trạng thái “Sẵn sàng”. |
| 9 |  | Hiển thị ca kiểm thử vừa tạo trong danh sách. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn ca kiểm thử cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị nội dung chi tiết, tiền điều kiện, các bước thực hiện, dữ liệu kiểm thử, kết quả mong đợi, hậu điều kiện và yêu cầu liên quan. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập mã hoặc tên ca kiểm thử vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các ca kiểm thử phù hợp. |
| 3.2.3 | Chọn điều kiện lọc nếu cần. |  |
| 3.2.4 |  | Danh sách ca kiểm thử được cập nhật theo điều kiện lọc. |
| 3.2.5 | Chọn ca kiểm thử cần xem. |  |
| 3.2.6 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | Chọn ca kiểm thử đang ở trạng thái bản nháp hoặc sẵn sàng. |  |
| 3.3.2 |  | Hệ thống hiển thị nội dung có thể chỉnh sửa. |
| 3.3.3 | Chỉnh sửa thông tin, thêm hoặc loại bỏ bước kiểm thử, cập nhật dữ liệu và kết quả mong đợi. |  |
| 3.3.3.1 | Chọn tệp cần đính kèm vào bản nháp. |  |
| 3.3.3.2 |  | Hệ thống tiếp nhận tệp đính kèm. |
| 3.3.3.3 |  | Tiếp tục tại bước 3.3.4. |
| 3.3.4 | Nhấn nút “Lưu bản nháp”. |  |
| 3.3.5 |  | Hệ thống kiểm tra và lưu nội dung thay đổi dưới dạng bản nháp. |
| 3.3.6 |  | Kết thúc chức năng. |
| 3.4.1 | Chọn ca kiểm thử đang ở trạng thái bản nháp hoặc sẵn sàng. |  |
| 3.4.2 | Nhấn nút “Xóa bản nháp”. |  |
| 3.4.3 |  | Hệ thống hiển thị hộp thoại xác nhận xóa. |
| 3.4.4 | Xác nhận xóa bản nháp. |  |
| 3.4.5 |  | Hệ thống kiểm tra trạng thái ca kiểm thử và thực hiện xóa bản nháp. |
| 3.4.6 |  | Cập nhật danh sách ca kiểm thử. Kết thúc chức năng. |
| 3.5.1 | Chọn ca kiểm thử cần sao chép. |  |
| 3.5.2 | Chọn chức năng nhân bản ca kiểm thử. |  |
| 3.5.3 |  | Hệ thống sao chép nội dung và tạo một ca kiểm thử mới với mã riêng. |
| 3.5.4 |  | Hiển thị ca kiểm thử vừa tạo. Kết thúc chức năng. |
| 3.6.1 | Chọn ca kiểm thử không còn sử dụng. |  |
| 3.6.2 | Chọn chức năng lưu trữ. |  |
| 3.6.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do. |
| 3.6.4 | Nhập lý do và xác nhận. |  |
| 3.6.5 |  | Ca kiểm thử được đánh dấu không còn hiệu lực. Lịch sử phiên bản vẫn được giữ lại. |
| 3.6.6 |  | Cập nhật danh sách ca kiểm thử. Kết thúc chức năng. |
| 3.7.1 | Chọn ca kiểm thử không còn hiệu lực. |  |
| 3.7.2 | Chọn chức năng khôi phục. |  |
| 3.7.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do khôi phục. |
| 3.7.4 | Nhập lý do và xác nhận. |  |
| 3.7.5 |  | Hệ thống đưa ca kiểm thử trở lại trạng thái hoạt động. |
| 3.7.6 |  | Cập nhật danh sách ca kiểm thử. Kết thúc chức năng. |
| 3.8.1 | Chọn các ca kiểm thử cần cập nhật nhãn. |  |
| 3.8.2 | Chọn chức năng cập nhật nhãn hàng loạt. |  |
| 3.8.3 |  | Hệ thống hiển thị hộp thoại cập nhật nhãn. |
| 3.8.4 | Nhập nhãn cần thêm hoặc loại bỏ và xác nhận. |  |
| 3.8.5 |  | Hệ thống cập nhật nhãn của các ca kiểm thử được chọn. |
| 3.8.6 |  | Kết thúc chức năng. |
| 3.9.1 | Chọn các ca kiểm thử cần đưa vào bộ. |  |
| 3.9.2 | Chọn chức năng thêm vào bộ kiểm thử. |  |
| 3.9.3 |  | Hệ thống hiển thị danh sách bộ kiểm thử có thể lựa chọn. |
| 3.9.4 | Chọn bộ kiểm thử và xác nhận. |  |
| 3.9.5 |  | Hệ thống kiểm tra các phiên bản ca kiểm thử được chọn và cập nhật danh sách ca kiểm thử thuộc bộ. |
| 3.9.6 |  | Kết thúc chức năng. |
| 3.10.1 | Chọn các ca kiểm thử cần lưu trữ. |  |
| 3.10.2 | Chọn chức năng lưu trữ hàng loạt. |  |
| 3.10.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do. |
| 3.10.4 | Nhập lý do và xác nhận. |  |
| 3.10.5 |  | Hệ thống thực hiện lưu trữ các ca kiểm thử hợp lệ và cập nhật danh sách. |
| 3.10.6 |  | Kết thúc chức năng. |
| 5.1.1 | Chọn phương thức viết ca kiểm thử theo hành vi. |  |
| 5.1.2 |  | Hệ thống hiển thị các trường điều kiện ban đầu, hành động và kết quả mong đợi. |
| 5.1.3 | Nhập các thông tin trên. |  |
| 5.1.4 |  | Tiếp tục tại bước 6. |
| 6.1.1 | Nhấn nút “Lưu nháp”. |  |
| 6.1.2 |  | Hệ thống kiểm tra thông tin đã nhập và lưu ca kiểm thử với trạng thái “Bản nháp”. |
| 6.1.3 |  | Cập nhật danh sách ca kiểm thử. Kết thúc chức năng. |
| 6.2 | Nhấn nút “Hủy”. |  |
| 6.3 |  | Hệ thống chuyển về danh sách ca kiểm thử và không tạo ca kiểm thử mới. |
| 7.1 |  | Bước kiểm thử thiếu hành động hoặc kết quả mong đợi, hệ thống yêu cầu bổ sung nội dung tại bước 5. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.5.1 |  | Ca kiểm thử không còn ở trạng thái cho phép chỉnh sửa, hệ thống không lưu nội dung thay đổi. |
| 3.4.5.1 |  | Ca kiểm thử đang được rà soát hoặc đã được phê duyệt, hệ thống không cho phép xóa bản nháp theo chức năng này. |
| 7.2 |  | Yêu cầu hoặc điều kiện kiểm thử được liên kết không hợp lệ, hệ thống từ chối lưu ca kiểm thử. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này hỗ trợ người kiểm thử xây dựng, tra cứu và duy trì các ca kiểm thử. Các thao tác bao gồm tạo mới, chỉnh sửa, lưu nháp, xóa bản nháp, nhân bản, lưu trữ và khôi phục. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC22 - Trình duyệt ca kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép người kiểm thử gửi ca kiểm thử đã thiết kế đến quản trị viên để rà soát trước khi đưa vào thực hiện.

**Tiền điều kiện:** Ca kiểm thử đang ở trạng thái bản nháp hoặc sẵn sàng. người kiểm thử được cấp quyền gửi rà soát.

**Hậu điều kiện:** Ca kiểm thử được chuyển sang trạng thái đang rà soát.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn ca kiểm thử cần trình duyệt. |  |
| 2 |  | Hệ thống hiển thị nội dung và trạng thái ca kiểm thử. |
| 3 | Nhấn nút “Gửi rà soát”. |  |
| 4 |  | Hệ thống hiển thị hộp thoại xác nhận và ô nhập ghi chú. |
| 5 | Nhập ghi chú gửi quản trị viên. |  |
| 6 | Xác nhận gửi rà soát. |  |
| 7 |  | Hệ thống kiểm tra hành động, kết quả mong đợi của các bước và những nội dung cần đối chiếu với cơ sở kiểm thử. |
| 8 |  | Nội dung hợp lệ, ca kiểm thử được chuyển sang trạng thái “Đang rà soát”. |
| 9 |  | Cập nhật trạng thái ca kiểm thử. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.1 | Chọn các ca kiểm thử cần xem xét lại. |  |
| 1.1.2 | Chọn chức năng đánh dấu cần rà soát. |  |
| 1.1.3 |  | Hệ thống hiển thị hộp thoại xác nhận. |
| 1.1.4 | Xác nhận đánh dấu các ca kiểm thử đã chọn. |  |
| 1.1.5 |  | Hệ thống ghi nhận các ca kiểm thử cần được rà soát. |
| 1.1.6 |  | Cập nhật danh sách ca kiểm thử. Kết thúc chức năng. |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng hộp thoại, giữ nguyên trạng thái ca kiểm thử. |
| 7.1 |  | Ca kiểm thử chưa có đầy đủ hành động hoặc kết quả mong đợi, hệ thống yêu cầu bổ sung nội dung. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.2 |  | Ca kiểm thử còn nội dung bắt buộc phải chỉnh sửa, hệ thống từ chối gửi rà soát. |
| 7.3 |  | Ca kiểm thử do AI tạo chưa được đối chiếu với cơ sở kiểm thử theo quy định, hệ thống không cho phép gửi rà soát. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép người kiểm thử gửi ca kiểm thử đã thiết kế đến quản trị viên để rà soát trước khi đưa vào thực hiện. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC23 - Xét duyệt ca kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép quản trị viên kiểm tra, phê duyệt hoặc yêu cầu chỉnh sửa ca kiểm thử. Phiên bản được phê duyệt là căn cứ để thực hiện kiểm thử.

**Tiền điều kiện:** quản trị viên đã đăng nhập và ca kiểm thử đang chờ xét duyệt.

**Hậu điều kiện:** Ca kiểm thử được phê duyệt thành phiên bản chính thức hoặc trả về bản nháp.

**Tác nhân chính:** quản trị viên

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn ca kiểm thử đang chờ xét duyệt. |  |
| 2 |  | Hệ thống hiển thị nội dung, các bước thực hiện, kết quả mong đợi và yêu cầu liên quan. |
| 3 | Kiểm tra sự phù hợp giữa nội dung ca kiểm thử và yêu cầu được liên kết. |  |
| 4 | Nhấn nút “Phê duyệt”. |  |
| 5 |  | Hệ thống hiển thị hộp thoại xác nhận phê duyệt. |
| 6 | Nhập ghi chú và xác nhận. |  |
| 7 |  | Hệ thống kiểm tra tính đầy đủ của các bước kiểm thử, liên kết với yêu cầu và những vấn đề cần xử lý trước khi phê duyệt. |
| 8 |  | Ca kiểm thử đáp ứng quy định phê duyệt, hệ thống lưu phiên bản chính thức cùng thông tin phê duyệt. |
| 9 |  | Cập nhật trạng thái ca kiểm thử thành “Đã phê duyệt”. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.1 | Chọn các ca kiểm thử đang chờ xét duyệt. |  |
| 1.1.2 | Chọn chức năng duyệt nhóm. |  |
| 1.1.3 |  | Hệ thống kiểm tra các ca kiểm thử được chọn và hiển thị hộp thoại xác nhận. |
| 1.1.4 | Nhập ghi chú phê duyệt. |  |
| 1.1.5 | Nhấn nút “Đối chiếu và duyệt nhóm”. |  |
| 1.1.6 |  | Hệ thống kiểm tra điều kiện phê duyệt của từng ca kiểm thử. |
| 1.1.7 |  | Nếu tất cả ca kiểm thử đều hợp lệ, hệ thống phê duyệt toàn bộ nhóm. |
| 1.1.8 |  | Cập nhật danh sách ca kiểm thử. Kết thúc chức năng. |
| 4.1.1 | Chọn chức năng yêu cầu sửa khi phát hiện nội dung chưa phù hợp. |  |
| 4.1.2 |  | Hệ thống hiển thị hộp thoại gồm loại lý do và nội dung cần chỉnh sửa. |
| 4.1.3 | Chọn lý do và nhập nhận xét. |  |
| 4.1.4 | Xác nhận yêu cầu chỉnh sửa. |  |
| 4.1.5 |  | Hệ thống lưu nhận xét và chuyển ca kiểm thử về trạng thái “Bản nháp”. |
| 4.1.6 |  | Kết thúc chức năng. |
| 5.1 |  | Ca kiểm thử do AI tạo chưa được đối chiếu ở lần chỉnh sửa hiện tại, hệ thống yêu cầu thực hiện đối chiếu. |
| 5.1.1 | Mở giao diện đối chiếu ca kiểm thử. |  |
| 5.1.2 |  | Hệ thống hiển thị nội dung ca kiểm thử cùng căn cứ nguồn. |
| 5.1.3 | Kiểm tra nội dung và quay lại chức năng phê duyệt. |  |
| 5.1.4 |  | Tiếp tục tại bước 4. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.6.1 |  | Có ít nhất một ca kiểm thử không đáp ứng điều kiện phê duyệt, hệ thống không thực hiện phê duyệt bất kỳ ca kiểm thử nào trong nhóm. |
| 7.1 |  | Ca kiểm thử thiếu bước thực hiện, kết quả mong đợi hoặc liên kết bắt buộc với yêu cầu, hệ thống từ chối phê duyệt. |
| 7.2 |  | Ca kiểm thử còn vấn đề bắt buộc phải chỉnh sửa hoặc có nội dung trùng lặp chưa được xử lý, hệ thống không cho phép phê duyệt. |
| 7.3 |  | Nội dung ca kiểm thử đã thay đổi trong quá trình xét duyệt, hệ thống từ chối phê duyệt nội dung cũ. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép quản trị viên kiểm tra, phê duyệt hoặc yêu cầu chỉnh sửa ca kiểm thử. Phiên bản được phê duyệt là căn cứ để thực hiện kiểm thử. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC24 - Quản lý phiên bản ca kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép người kiểm thử xem lịch sử phiên bản và tạo bản nháp mới để chỉnh sửa ca kiểm thử mà không làm thay đổi phiên bản đã được phê duyệt.

**Tiền điều kiện:** Ca kiểm thử đã có phiên bản chính thức. người kiểm thử được cấp quyền quản lý phiên bản.

**Hậu điều kiện:** Lịch sử phiên bản được hiển thị hoặc bản nháp của phiên bản mới được tạo. Phiên bản trước đó không bị ghi đè.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Chọn ca kiểm thử cần thay đổi. |  |
| 2 |  | Hệ thống hiển thị nội dung phiên bản hiện tại. |
| 3 | Chọn chức năng tạo phiên bản mới. |  |
| 4 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do thay đổi. |
| 5 | Nhập lý do thay đổi. |  |
| 6 | Xác nhận tạo bản nháp. |  |
| 7 |  | Hệ thống kiểm tra phiên bản hiện tại của ca kiểm thử. |
| 8 |  | Nội dung của phiên bản hiện tại được sao chép để tạo bản nháp mới với cùng mã ca kiểm thử. |
| 9 |  | Hệ thống hiển thị bản nháp vừa tạo và giữ lại nội dung phiên bản trước đó. |
| 10 | Tiếp tục chỉnh sửa bản nháp theo UC21. |  |
| 11 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Truy cập lịch sử phiên bản của ca kiểm thử. |  |
| 3.1.2 |  | Hệ thống hiển thị các phiên bản cùng số phiên bản, trạng thái và lý do thay đổi. |
| 3.1.3 | Chọn phiên bản cần xem và mở căn cứ nguồn nếu có. |  |
| 3.1.4 |  | Hệ thống hiển thị thông tin phiên bản và nội dung trích dẫn liên quan. |
| 3.1.5 |  | Kết thúc chức năng. |
| 6.1 | Nhấn nút “Hủy”. |  |
| 6.2 |  | Hệ thống đóng hộp thoại và không tạo bản nháp mới. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 7.1 |  | Phiên bản ca kiểm thử đã thay đổi hoặc không còn tồn tại, hệ thống từ chối tạo bản nháp từ phiên bản cũ. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép người kiểm thử xem lịch sử phiên bản và tạo bản nháp mới để chỉnh sửa ca kiểm thử mà không làm thay đổi phiên bản đã được phê duyệt. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC25 - Quản lý bộ kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép người kiểm thử tập hợp các ca kiểm thử thành từng bộ, phục vụ việc xác định phạm vi và tổ chức thực hiện kiểm thử.

**Tiền điều kiện:** người kiểm thử đã tham gia dự án và được cấp quyền quản lý bộ kiểm thử.

**Hậu điều kiện:** Bộ kiểm thử được tạo mới, cập nhật thành phần, nhân bản hoặc lưu trữ.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang bộ kiểm thử. |  |
| 2 |  | Hệ thống hiển thị danh sách bộ kiểm thử của dự án. |
| 3 | Nhấn nút “Tạo bộ kiểm thử”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm tên, loại bộ kiểm thử và danh sách ca kiểm thử có thể lựa chọn. |
| 5 | Nhập tên, chọn loại bộ kiểm thử và các ca kiểm thử cần đưa vào bộ. |  |
| 6 | Xác nhận lưu bộ kiểm thử. |  |
| 7 |  | Hệ thống kiểm tra thông tin bộ kiểm thử và các phiên bản ca kiểm thử được chọn. |
| 8 |  | Thông tin hợp lệ, bộ kiểm thử được tạo với trạng thái hoạt động. |
| 9 |  | Cập nhật danh sách bộ kiểm thử. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn bộ kiểm thử cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị thông tin bộ kiểm thử và danh sách ca kiểm thử thuộc bộ. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập từ khóa vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các bộ kiểm thử phù hợp. |
| 3.2.3 | Chọn bộ kiểm thử cần xem. |  |
| 3.2.4 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | Chọn bộ kiểm thử cần chỉnh sửa. |  |
| 3.3.2 |  | Hệ thống hiển thị tên, loại bộ kiểm thử và danh sách ca kiểm thử hiện tại. |
| 3.3.3 | Chọn chức năng chỉnh sửa. |  |
| 3.3.4 |  | Hệ thống hiển thị biểu mẫu cập nhật. |
| 3.3.5 | Thay đổi tên, loại bộ kiểm thử, thêm hoặc loại bỏ ca kiểm thử khỏi bộ. |  |
| 3.3.6 | Xác nhận lưu. |  |
| 3.3.7 |  | Hệ thống kiểm tra và lưu nội dung thay đổi. |
| 3.3.8 |  | Cập nhật danh sách bộ kiểm thử. Kết thúc chức năng. |
| 3.4.1 | Chọn bộ kiểm thử cần sao chép. |  |
| 3.4.2 | Chọn chức năng nhân bản. |  |
| 3.4.3 |  | Hệ thống sao chép thông tin và danh sách ca kiểm thử để tạo bộ kiểm thử mới. |
| 3.4.4 |  | Cập nhật danh sách bộ kiểm thử. Kết thúc chức năng. |
| 3.5.1 | Chọn bộ kiểm thử không còn sử dụng. |  |
| 3.5.2 | Chọn chức năng lưu trữ bộ kiểm thử. |  |
| 3.5.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do lưu trữ. |
| 3.5.4 | Nhập lý do và xác nhận. |  |
| 3.5.5 |  | Hệ thống chuyển bộ kiểm thử sang trạng thái “Đã lưu trữ”. |
| 3.5.6 |  | Cập nhật danh sách bộ kiểm thử. Kết thúc chức năng. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.7.1 |  | Bộ kiểm thử đã được lưu trữ, hệ thống không cho phép chỉnh sửa. |
| 7.1 |  | Ca kiểm thử được chọn không có phiên bản hợp lệ, hệ thống từ chối lưu bộ kiểm thử. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép người kiểm thử tập hợp các ca kiểm thử thành từng bộ, phục vụ việc xác định phạm vi và tổ chức thực hiện kiểm thử. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC26 - Quản lý lần chạy kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép quản trị viên tổ chức thực hiện kiểm thử thông qua việc tạo lần chạy, xác định các ca cần thực hiện, phân công người kiểm thử và quản lý quá trình bắt đầu, hoàn tất hoặc hủy lần chạy.

**Tiền điều kiện:** quản trị viên đã đăng nhập và dự án có kế hoạch kiểm thử đã được phê duyệt.

**Hậu điều kiện:** Lần chạy kiểm thử được tạo, cập nhật thông tin phân công hoặc thay đổi trạng thái thực hiện.

**Tác nhân chính:** quản trị viên

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang lần chạy kiểm thử. |  |
| 2 |  | Hệ thống hiển thị danh sách lần chạy kiểm thử của dự án. |
| 3 | Nhấn nút “Tạo lần chạy”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm tên lần chạy, kế hoạch kiểm thử, bộ kiểm thử, ca kiểm thử và môi trường thực hiện. |
| 5 | Nhập tên lần chạy và chọn kế hoạch kiểm thử đã được phê duyệt. |  |
| 6 |  | Hệ thống hiển thị các ca kiểm thử thuộc phạm vi kế hoạch được chọn. |
| 7 | Chọn các ca kiểm thử cần thực hiện và bổ sung thông tin liên quan. |  |
| 8 | Nhấn nút “Tạo lần chạy”. |  |
| 9 |  | Hệ thống kiểm tra kế hoạch và phạm vi ca kiểm thử được chọn. |
| 10 |  | Thông tin hợp lệ, lần chạy kiểm thử được tạo với trạng thái “Bản nháp”. |
| 11 |  | Hiển thị lần chạy vừa tạo trong danh sách. |
| 12 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn lần chạy cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị thông tin lần chạy, kế hoạch liên quan, người phụ trách, danh sách ca kiểm thử và tiến độ thực hiện. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập từ khóa vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các lần chạy phù hợp. |
| 3.2.3 | Chọn điều kiện lọc nếu cần. |  |
| 3.2.4 |  | Danh sách lần chạy được cập nhật theo điều kiện lọc. |
| 3.2.5 | Chọn lần chạy cần xem. |  |
| 3.2.6 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | Chọn lần chạy cần phân công. |  |
| 3.3.2 |  | Hệ thống hiển thị thông tin lần chạy và danh sách ca kiểm thử. |
| 3.3.3 | Mở chức năng phân công. |  |
| 3.3.4 |  | Hệ thống hiển thị danh sách thành viên có quyền thực hiện kiểm thử. |
| 3.3.5 | Chọn người phụ trách lần chạy và người kiểm thử thực hiện từng ca kiểm thử. |  |
| 3.3.5.1 | Nhấn nút “Gán người này cho tất cả ca”. |  |
| 3.3.5.2 |  | Hệ thống chọn người phụ trách lần chạy làm người thực hiện tất cả ca kiểm thử. Tiếp tục tại bước 3.3.6. |
| 3.3.6 | Nhấn nút “Lưu phân công”. |  |
| 3.3.7 |  | Hệ thống kiểm tra tư cách thành viên và quyền thực hiện kiểm thử của những người được chọn. |
| 3.3.8 |  | Thông tin hợp lệ, hệ thống lưu người phụ trách lần chạy và người thực hiện từng ca kiểm thử. |
| 3.3.9 |  | Cập nhật thông tin phân công. Kết thúc chức năng. |
| 3.4.1 | Mở chức năng phân công tại lần chạy đã có người thực hiện. |  |
| 3.4.2 |  | Hệ thống hiển thị thông tin phân công hiện tại. |
| 3.4.3 | Thay đổi người phụ trách hoặc người kiểm thử được phân công thực hiện ca kiểm thử. |  |
| 3.4.4 | Nhấn nút “Lưu phân công”. |  |
| 3.4.5 |  | Hệ thống kiểm tra trạng thái lần chạy và thông tin người được chọn, sau đó lưu nội dung phân công mới nếu hợp lệ. |
| 3.4.6 |  | Kết thúc chức năng. |
| 3.5.1 | Chọn lần chạy chưa bắt đầu. |  |
| 3.5.2 |  | Hệ thống hiển thị nội dung lần chạy và thông tin phân công. |
| 3.5.3 | Nhấn nút “Bắt đầu”. |  |
| 3.5.4 |  | Hệ thống kiểm tra kế hoạch, phạm vi kiểm thử, môi trường và người thực hiện từng ca kiểm thử. |
| 3.5.4.1 |  | Lần chạy chưa được phân công đầy đủ người thực hiện, hệ thống yêu cầu hoàn tất phân công trước khi bắt đầu. |
| 3.5.5 |  | Lần chạy được chuyển sang trạng thái “Đang thực hiện” khi các thông tin đáp ứng điều kiện bắt đầu. |
| 3.5.6 |  | Hiển thị giao diện thực thi kiểm thử. Kết thúc chức năng. |
| 3.6.1 | Chọn lần chạy đang thực hiện và nhấn nút “Hoàn tất”. |  |
| 3.6.2 |  | Hệ thống kiểm tra số lượng ca kiểm thử đã có kết quả. |
| 3.6.2.1 |  | Còn ca kiểm thử chưa hoàn thành nhưng dự án cho phép kết thúc một phần, hệ thống hoàn tất lần chạy và giữ lại các kết quả đã ghi nhận. |
| 3.6.3 |  | Các ca kiểm thử đã được ghi nhận kết quả, hệ thống chuyển lần chạy sang trạng thái “Đã hoàn tất”. |
| 3.6.4 |  | Cập nhật thông tin lần chạy. Kết thúc chức năng. |
| 3.7.1 | Chọn lần chạy cần hủy. |  |
| 3.7.2 | Nhấn nút “Hủy lần chạy”. |  |
| 3.7.3 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do hủy. |
| 3.7.4 | Nhập lý do và xác nhận. |  |
| 3.7.5 |  | Hệ thống chuyển lần chạy sang trạng thái “Đã hủy” và giữ lại các kết quả kiểm thử đã ghi nhận. |
| 3.7.6 |  | Cập nhật danh sách lần chạy. Kết thúc chức năng. |
| 3.8.1 | Chọn lần chạy đã hoàn tất hoặc đã hủy. |  |
| 3.8.2 |  | Hệ thống hiển thị các kết quả kiểm thử đã ghi nhận. |
| 3.8.3 | Mở mục “Chạy lại ca thất bại”. |  |
| 3.8.4 |  | Hệ thống hiển thị danh sách ca kiểm thử có kết quả thất bại. |
| 3.8.5 | Chọn các ca kiểm thử cần thực hiện lại. |  |
| 3.8.6 | Nhấn nút “Tạo lần chạy lại”. |  |
| 3.8.7 |  | Hệ thống tạo lần chạy mới gồm các ca kiểm thử được chọn. Kết quả của lần chạy trước vẫn được giữ lại. |
| 3.8.8 |  | Hiển thị lần chạy vừa tạo. Kết thúc chức năng. |
| 8.1 | Nhấn nút “Hủy”. |  |
| 8.2 |  | Hệ thống đóng biểu mẫu và không tạo lần chạy mới. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.3.7.1 |  | Thành viên được chọn không có quyền thực hiện kiểm thử, hệ thống không lưu thông tin phân công. |
| 3.5.4.2 |  | Người được phân công không còn hoạt động trong dự án hoặc môi trường kiểm thử không còn khả dụng, hệ thống từ chối bắt đầu lần chạy. |
| 3.6.2.2 |  | Còn ca kiểm thử chưa hoàn thành và dự án không cho phép kết thúc một phần, hệ thống không thực hiện hoàn tất lần chạy. |
| 9.1 |  | Kế hoạch chưa được phê duyệt hoặc ca kiểm thử được chọn không thuộc phạm vi kế hoạch, hệ thống từ chối tạo lần chạy. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép quản trị viên tổ chức thực hiện kiểm thử thông qua việc tạo lần chạy, xác định các ca cần thực hiện, phân công người kiểm thử và quản lý quá trình bắt đầu, hoàn tất hoặc hủy lần chạy. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC27 - Thực thi kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép người kiểm thử thực hiện các ca kiểm thử được phân công, đối chiếu kết quả thực tế với kết quả mong đợi và ghi nhận kết quả thực hiện.

**Tiền điều kiện:** Lần chạy kiểm thử đang thực hiện và người kiểm thử được phân công thực hiện ca kiểm thử tương ứng.

**Hậu điều kiện:** Kết quả thực tế, kết quả từng bước, ghi chú và bằng chứng kiểm thử được lưu. Tiến độ lần chạy được cập nhật.

**Tác nhân chính:** người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập lần chạy kiểm thử đang thực hiện. |  |
| 2 |  | Hệ thống hiển thị danh sách ca kiểm thử, người thực hiện và tiến độ lần chạy. |
| 3 | Chọn ca kiểm thử được phân công. |  |
| 4 |  | Hệ thống hiển thị tiền điều kiện, dữ liệu kiểm thử, các bước thực hiện và kết quả mong đợi. |
| 5 | Thực hiện từng bước trên phần mềm cần kiểm thử. |  |
| 6 | Đối chiếu kết quả thực tế với kết quả mong đợi, nhập nội dung và chọn kết quả của từng bước kiểm thử. |  |
| 7 | Nhập ghi chú nếu cần và chọn kết quả “Đạt” cho ca kiểm thử. |  |
| 8 |  | Hệ thống kiểm tra thông tin kết quả và quyền thực hiện của người kiểm thử. |
| 9 |  | Thông tin hợp lệ, kết quả kiểm thử được lưu với trạng thái đạt. |
| 10 |  | Cập nhật kết quả và tiến độ lần chạy. |
| 11 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.1 | Chọn lần chạy đang thực hiện và nhấn nút “Tiếp tục thực thi”. |  |
| 1.1.2 |  | Hệ thống hiển thị tiến độ đã ghi nhận và các ca kiểm thử chưa hoàn thành. |
| 1.1.3 |  | Tiếp tục tại bước 3. |
| 3.1.1 | Chọn ca kiểm thử đã có kết quả. |  |
| 3.1.2 |  | Hệ thống hiển thị kết quả thực tế, kết quả từng bước, ghi chú, bằng chứng và lỗi liên quan nếu có. |
| 3.1.3 |  | Kết thúc chức năng. |
| 6.1.1 | Chọn hình ảnh hoặc tệp làm bằng chứng kiểm thử. |  |
| 6.1.2 |  | Hệ thống tiếp nhận tệp đính kèm để lưu cùng kết quả thực hiện. |
| 6.1.3 |  | Tiếp tục tại bước 7. |
| 7.1.1 | Chọn kết quả thất bại khi kết quả thực tế không đúng với kết quả mong đợi. |  |
| 7.1.2 |  | Hệ thống kiểm tra nội dung kết quả thực tế. |
| 7.1.2.1 |  | Ca kiểm thử thất bại chưa có nội dung kết quả thực tế, hệ thống yêu cầu bổ sung tại bước 6. |
| 7.1.3 |  | Thông tin hợp lệ, hệ thống lưu kết quả thất bại và cập nhật tiến độ lần chạy. |
| 7.1.4 | Tạo lỗi hoặc liên kết lỗi đã có theo UC28 nếu cần. |  |
| 7.1.5 |  | Kết thúc chức năng. |
| 7.2.1 | Chọn kết quả “Bị chặn” khi không thể thực hiện hoặc tiếp tục ca kiểm thử. |  |
| 7.2.2 |  | Hệ thống ghi nhận kết quả bị chặn của ca kiểm thử. |
| 7.2.3 |  | Cập nhật tiến độ lần chạy. Kết thúc chức năng. |
| 7.3.1 | Chọn kết quả “Bỏ qua”. |  |
| 7.3.2 |  | Hệ thống lưu kết quả và cập nhật tiến độ lần chạy. |
| 7.3.3 |  | Kết thúc chức năng. |
| 7.4.1 | Chọn kết quả “Không áp dụng” nếu dự án cho phép sử dụng kết quả này. |  |
| 7.4.2 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do. |
| 7.4.3 | Nhập lý do và xác nhận. |  |
| 7.4.4 |  | Hệ thống lưu kết quả không áp dụng cùng lý do đã nhập. |
| 7.4.5 |  | Cập nhật tiến độ lần chạy. Kết thúc chức năng. |
| 8.1 |  | Bước kiểm thử đã nhập thông tin nhưng chưa xác định kết quả, hệ thống yêu cầu chọn kết quả tương ứng. |
| 8.2 |  | Bước kiểm thử được đánh dấu không áp dụng nhưng chưa có lý do, hệ thống yêu cầu bổ sung lý do. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 8.3 |  | Lần chạy đã hoàn tất hoặc không còn ở trạng thái đang thực hiện, hệ thống từ chối ghi nhận kết quả. |
| 8.4 |  | người kiểm thử không được phân công thực hiện ca kiểm thử và không có quyền thực hiện thay, hệ thống từ chối lưu kết quả. |
| 8.5 |  | Kết quả kiểm thử đã được ghi nhận và không còn cho phép thay đổi trực tiếp, hệ thống không ghi đè kết quả trước đó. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép người kiểm thử thực hiện các ca kiểm thử được phân công, đối chiếu kết quả thực tế với kết quả mong đợi và ghi nhận kết quả thực hiện. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC28 - Quản lý lỗi

## Đặc tả nghiệp vụ

**Mô tả:** Cho phép người kiểm thử ghi nhận các lỗi phát hiện trong quá trình kiểm thử, tra cứu và liên kết lỗi với kết quả thực hiện. quản trị viên có thể phân công hoặc thay đổi người chịu trách nhiệm xử lý lỗi.

**Tiền điều kiện:** Người dùng đã đăng nhập và tham gia dự án.

**Hậu điều kiện:** Lỗi được ghi nhận, thông tin người xử lý được cập nhật hoặc liên kết giữa lỗi và nội dung kiểm thử được thiết lập.

**Tác nhân chính:** người kiểm thử, quản trị viên

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | người kiểm thử truy cập trang quản lý lỗi. |  |
| 2 |  | Hệ thống hiển thị danh sách lỗi của dự án. |
| 3 | Nhấn nút “Tạo lỗi”. |  |
| 4 |  | Hệ thống hiển thị biểu mẫu gồm tiêu đề, mức độ nghiêm trọng, mức ưu tiên, môi trường kiểm thử, mô tả lỗi, các bước tái hiện, kết quả thực tế, kết quả mong đợi và tệp đính kèm. |
| 5 | Nhập các thông tin trên và đính kèm bằng chứng nếu có. |  |
| 6 | Xác nhận tạo lỗi. |  |
| 7 |  | Hệ thống kiểm tra nội dung và các thông tin liên quan đến lỗi. |
| 8 |  | Thông tin hợp lệ, hệ thống tạo mã lỗi và lưu lỗi với trạng thái “Mới”. |
| 9 |  | Hiển thị lỗi vừa ghi nhận trong danh sách. |
| 10 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.1 | người kiểm thử truy cập lần chạy kiểm thử và chọn ca kiểm thử có kết quả thất bại. |  |
| 1.1.2 |  | Hệ thống hiển thị nội dung ca kiểm thử và kết quả thực tế. |
| 1.1.3 | Chọn chức năng tạo lỗi từ kết quả kiểm thử. |  |
| 1.1.4 |  | Hệ thống hiển thị biểu mẫu tạo lỗi cùng thông tin của ca kiểm thử liên quan. |
| 1.1.5 | Bổ sung tiêu đề, mức độ nghiêm trọng, mức ưu tiên, mô tả và bằng chứng lỗi. |  |
| 1.1.6 | Xác nhận tạo lỗi. |  |
| 1.1.7 |  | Hệ thống kiểm tra thông tin, tạo lỗi mới và liên kết với kết quả kiểm thử. |
| 1.1.8 |  | Kết thúc chức năng. |
| 1.2.1 | người kiểm thử chọn ca kiểm thử có kết quả thất bại chưa được liên kết lỗi. |  |
| 1.2.2 |  | Hệ thống hiển thị chức năng liên kết lỗi đã có. |
| 1.2.3 | Chọn lỗi đã được ghi nhận trong dự án. |  |
| 1.2.4 | Xác nhận liên kết lỗi. |  |
| 1.2.5 |  | Hệ thống kiểm tra tính hợp lệ của lỗi và kết quả kiểm thử được chọn. |
| 1.2.6 |  | Lỗi được liên kết với kết quả kiểm thử. |
| 1.2.7 |  | Cập nhật thông tin lần chạy. Kết thúc chức năng. |
| 3.1.1 | Chọn lỗi cần xem. |  |
| 3.1.2 |  | Hệ thống hiển thị tiêu đề, mô tả, bước tái hiện, kết quả thực tế, kết quả mong đợi, mức độ nghiêm trọng, người xử lý và trạng thái lỗi. |
| 3.1.3 |  | Kết thúc chức năng. |
| 3.2.1 | Nhập mã hoặc tên lỗi vào ô tìm kiếm. |  |
| 3.2.2 |  | Hệ thống hiển thị các lỗi phù hợp. |
| 3.2.3 | Chọn điều kiện lọc nếu cần. |  |
| 3.2.4 |  | Danh sách lỗi được cập nhật theo điều kiện lọc. |
| 3.2.5 | Chọn lỗi cần xem. |  |
| 3.2.6 |  | Tiếp tục tại bước 3.1.2. |
| 3.3.1 | quản trị viên chọn lỗi cần phân công. |  |
| 3.3.2 | Nhấn nút “Gán người xử lý”. |  |
| 3.3.3 |  | Hệ thống hiển thị danh sách thành viên có thể phân công. |
| 3.3.4 | Chọn người chịu trách nhiệm xử lý lỗi. |  |
| 3.3.5 | Xác nhận lưu thông tin phân công. |  |
| 3.3.6 |  | Hệ thống kiểm tra thông tin thành viên và lưu người xử lý lỗi. |
| 3.3.7 |  | Cập nhật danh sách lỗi. Kết thúc chức năng. |
| 3.4.1 | quản trị viên chọn lỗi đã được phân công. |  |
| 3.4.2 | Mở chức năng gán người xử lý. |  |
| 3.4.3 |  | Hệ thống hiển thị người xử lý hiện tại và danh sách thành viên có thể lựa chọn. |
| 3.4.4 | Chọn thành viên khác và xác nhận. |  |
| 3.4.4.1 | quản trị viên chọn “Chưa gán” và xác nhận. |  |
| 3.4.4.2 |  | Hệ thống loại bỏ thông tin người xử lý hiện tại của lỗi. |
| 3.4.4.3 |  | Kết thúc chức năng. |
| 3.4.5 |  | Hệ thống cập nhật người xử lý mới của lỗi. |
| 3.4.6 |  | Kết thúc chức năng. |
| 3.5.1 | người kiểm thử chọn chức năng kiểm tra lỗi trùng lặp. |  |
| 3.5.2 |  | Hệ thống đối chiếu nội dung các lỗi trong dự án. |
| 3.5.3 |  | Hiển thị danh sách lỗi có khả năng trùng lặp. |
| 3.5.4 |  | Kết thúc chức năng. |
| 3.6.1 | quản trị viên chọn lỗi và xem các liên kết truy vết được đề xuất. |  |
| 3.6.2 |  | Hệ thống hiển thị thông tin liên kết cùng căn cứ đề xuất. |
| 3.6.3 | Chọn liên kết phù hợp và xác nhận. |  |
| 3.6.3.1 | Chọn chức năng thu hồi liên kết đã thiết lập. |  |
| 3.6.3.2 |  | Hệ thống hiển thị hộp thoại xác nhận. |
| 3.6.3.3 | Xác nhận thu hồi liên kết. |  |
| 3.6.3.4 |  | Hệ thống cập nhật hiệu lực của liên kết. Kết thúc chức năng. |
| 3.6.4 |  | Hệ thống lưu liên kết được chấp nhận. |
| 3.6.5 |  | Kết thúc chức năng. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.7.1 |  | Kết quả kiểm thử được chọn không phải kết quả thất bại, hệ thống không cho phép tạo lỗi từ kết quả đó. |
| 1.2.5.1 |  | Lỗi được chọn không thuộc phạm vi liên kết hợp lệ của kết quả kiểm thử, hệ thống từ chối thiết lập liên kết. |
| 3.3.6.1 |  | Người được chọn không phải thành viên hợp lệ của dự án, hệ thống không thực hiện phân công. |
| 7.1 |  | Yêu cầu, ca kiểm thử hoặc lần chạy được liên kết không hợp lệ, hệ thống từ chối lưu lỗi. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Cho phép người kiểm thử ghi nhận các lỗi phát hiện trong quá trình kiểm thử, tra cứu và liên kết lỗi với kết quả thực hiện. quản trị viên có thể phân công hoặc thay đổi người chịu trách nhiệm xử lý lỗi. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC29 - Xử lý lỗi

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này hỗ trợ theo dõi quá trình xử lý lỗi thông qua việc cập nhật trạng thái và ghi nhận kết quả kiểm thử lại.

**Tiền điều kiện:** Lỗi đã được ghi nhận trong dự án. Người dùng được cấp quyền thực hiện thao tác tương ứng.

**Hậu điều kiện:** Trạng thái lỗi và lịch sử xử lý được cập nhật. Kết quả kiểm thử lại được sử dụng để xác định lỗi đã được khắc phục hay cần tiếp tục xử lý.

**Tác nhân chính:** quản trị viên, người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | quản trị viên truy cập trang quản lý lỗi. |  |
| 2 |  | Hệ thống hiển thị danh sách lỗi và trạng thái hiện tại của từng lỗi. |
| 3 | Chọn lỗi cần xử lý. |  |
| 4 |  | Hệ thống hiển thị nội dung lỗi và các trạng thái có thể chuyển đổi. |
| 5 | Chọn trạng thái mới của lỗi. |  |
| 6 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do chuyển trạng thái. |
| 7 | Nhập lý do. |  |
| 8 | Xác nhận chuyển trạng thái. |  |
| 9 |  | Hệ thống kiểm tra trạng thái hiện tại, điều kiện chuyển trạng thái và quyền thực hiện thao tác. |
| 10 |  | Thông tin hợp lệ, trạng thái mới được lưu cùng lịch sử xử lý lỗi. |
| 11 |  | Cập nhật danh sách lỗi. |
| 12 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1.1.1 | Truy cập lần chạy kiểm thử có kết quả đã liên kết lỗi. |  |
| 1.1.2 |  | Hệ thống hiển thị thông tin lỗi và trạng thái hiện tại. |
| 1.1.3 | Chọn trạng thái mới của lỗi. |  |
| 1.1.4 |  | Hệ thống hiển thị hộp thoại yêu cầu nhập lý do. |
| 1.1.5 | Nhập lý do và xác nhận. |  |
| 1.1.6 |  | Hệ thống kiểm tra điều kiện chuyển trạng thái và cập nhật lỗi. |
| 1.1.7 |  | Hiển thị thông tin lỗi sau khi cập nhật. Kết thúc chức năng. |
| 3.1.1 | người kiểm thử thực hiện lại ca kiểm thử liên quan đến lỗi theo UC27. |  |
| 3.1.2 |  | Hệ thống lưu kết quả kiểm thử mới. |
| 3.1.3 | Truy cập trang quản lý lỗi và chọn lỗi đang ở trạng thái sẵn sàng kiểm thử lại. |  |
| 3.1.4 |  | Hệ thống hiển thị danh sách kết quả kiểm thử lại có thể sử dụng. |
| 3.1.5 | Chọn kết quả kiểm thử lại đạt. |  |
| 3.1.5.1 | người kiểm thử chọn kết quả kiểm thử lại thất bại. |  |
| 3.1.5.2 |  | Hệ thống kiểm tra kết quả kiểm thử được chọn. |
| 3.1.5.3 |  | Kết quả hợp lệ, hệ thống ghi nhận kết quả kiểm thử lại và chuyển lỗi sang trạng thái “Mở lại”. |
| 3.1.5.4 |  | Cập nhật danh sách lỗi. Kết thúc chức năng. |
| 3.1.6 |  | Hệ thống kiểm tra phiên bản ca kiểm thử, kết quả được chọn và điều kiện ghi nhận kiểm thử lại. |
| 3.1.7 |  | Kết quả hợp lệ, hệ thống ghi nhận kết quả kiểm thử lại và chuyển lỗi sang trạng thái “Đã đóng”. |
| 3.1.8 |  | Cập nhật danh sách lỗi. Kết thúc chức năng. |
| 8.1 | Hủy thao tác chuyển trạng thái. |  |
| 8.2 |  | Hệ thống đóng hộp thoại và giữ nguyên trạng thái lỗi. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.6.1 |  | Kết quả được chọn là kết quả đã sử dụng để ghi nhận lỗi ban đầu, hệ thống yêu cầu sử dụng kết quả kiểm thử mới. |
| 3.1.6.2 |  | Kết quả kiểm thử lại không thuộc phiên bản ca kiểm thử liên quan đến lỗi, hệ thống từ chối ghi nhận. |
| 3.1.6.3 |  | Lỗi không còn ở trạng thái sẵn sàng kiểm thử lại, hệ thống không cho phép ghi nhận kết quả kiểm thử lại. |
| 9.1 |  | Trạng thái mới không phù hợp với quy trình xử lý của lỗi, hệ thống từ chối chuyển trạng thái. |
| 9.2 |  | Người dùng không được phép thực hiện thao tác xử lý lỗi, hệ thống không lưu thay đổi. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này hỗ trợ theo dõi quá trình xử lý lỗi thông qua việc cập nhật trạng thái và ghi nhận kết quả kiểm thử lại. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC30 - Quản lý báo cáo kiểm thử

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này cho phép quản trị viên và người kiểm thử theo dõi tiến độ, xem kết quả hoàn tất kiểm thử, lưu báo cáo tại từng thời điểm và xuất báo cáo thành tài liệu.

**Tiền điều kiện:** Dự án có kế hoạch kiểm thử đã được phê duyệt. Người dùng được cấp quyền sử dụng chức năng báo cáo.

**Hậu điều kiện:** Báo cáo kiểm thử được hiển thị, lưu lại hoặc xuất thành tệp PDF, Word.

**Tác nhân chính:** quản trị viên, người kiểm thử

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập trang báo cáo kiểm thử. |  |
| 2 |  | Hệ thống hiển thị các loại báo cáo, danh sách kế hoạch kiểm thử đã được phê duyệt và báo cáo đã lưu. |
| 3 | Chọn loại báo cáo tiến độ kiểm thử. |  |
| 4 | Chọn kế hoạch kiểm thử cần xem báo cáo. |  |
| 5 |  | Hệ thống tổng hợp thông tin kế hoạch, ca kiểm thử, lần chạy, kết quả thực hiện và các lỗi liên quan. |
| 6 |  | Hiển thị báo cáo tiến độ kiểm thử của kế hoạch được chọn. |
| 7 | Xem nội dung và số liệu báo cáo. |  |
| 8 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn loại báo cáo hoàn tất kiểm thử. |  |
| 3.1.2 | Chọn kế hoạch kiểm thử cần xem báo cáo. |  |
| 3.1.3 |  | Hệ thống tổng hợp kết quả kiểm thử, thông tin lỗi và đánh giá mức độ đáp ứng các tiêu chí hoàn thành của kế hoạch. |
| 3.1.4 |  | Hiển thị báo cáo hoàn tất kiểm thử. |
| 3.1.5 |  | Tiếp tục tại bước 7. |
| 3.2.1 | Chọn báo cáo trong danh sách báo cáo đã lưu. |  |
| 3.2.2 |  | Hệ thống hiển thị nội dung và số liệu tại thời điểm báo cáo được lưu. |
| 3.2.3 | Xem nội dung báo cáo. |  |
| 3.2.4 |  | Kết thúc chức năng. |
| 7.1.1 | Nhấn nút “Lưu bản chốt”. |  |
| 7.1.2 |  | Hệ thống kiểm tra số liệu báo cáo tại thời điểm lưu. |
| 7.1.3 |  | Báo cáo được lưu cùng số liệu tại thời điểm tạo bản chốt. |
| 7.1.4 |  | Hiển thị báo cáo vừa lưu trong danh sách. |
| 7.1.5 |  | Kết thúc chức năng. |
| 7.2.1 | Chọn chức năng xuất báo cáo PDF. |  |
| 7.2.2 |  | Hệ thống tạo tệp PDF từ nội dung báo cáo được chọn. |
| 7.2.3 |  | Cung cấp tệp báo cáo để người dùng tải xuống. |
| 7.2.4 |  | Kết thúc chức năng. |
| 7.3.1 | Chọn chức năng xuất báo cáo Word. |  |
| 7.3.2 |  | Hệ thống tạo tệp Word từ nội dung báo cáo được chọn. |
| 7.3.3 |  | Cung cấp tệp báo cáo để người dùng tải xuống. |
| 7.3.4 |  | Kết thúc chức năng. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.2.2.1 |  | Báo cáo được chọn không còn tồn tại, hệ thống hiển thị thông báo lỗi. |
| 5.1 |  | Kế hoạch kiểm thử được chọn không còn hợp lệ để lập báo cáo, hệ thống từ chối tổng hợp số liệu. |
| 7.1.2.1 |  | Số liệu kiểm thử đã thay đổi kể từ khi báo cáo được hiển thị, hệ thống yêu cầu xem lại báo cáo trước khi lưu bản chốt. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này cho phép quản trị viên và người kiểm thử theo dõi tiến độ, xem kết quả hoàn tất kiểm thử, lưu báo cáo tại từng thời điểm và xuất báo cáo thành tài liệu. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC31 - Tạo yêu cầu bằng AI

## Đặc tả nghiệp vụ

**Mô tả:** Chức năng này hỗ trợ chuyên viên phân tích nghiệp vụ (BA) xây dựng yêu cầu từ tài liệu nguồn bằng AI. Hệ thống xác định nội dung yêu cầu, tiêu chí chấp nhận và quy tắc nghiệp vụ dựa trên thông tin trong tài liệu, sau đó lưu kết quả dưới dạng bản nháp để chuyên viên phân tích nghiệp vụ (BA) kiểm tra.

**Tiền điều kiện:** Tài liệu nguồn thuộc dự án, ở trạng thái đã sẵn sàng, được phép sử dụng bằng AI và đáp ứng điều kiện nguồn của quy trình nhập yêu cầu. chuyên viên phân tích nghiệp vụ (BA) được cấp quyền tạo yêu cầu bằng AI.

**Hậu điều kiện:** Các yêu cầu có căn cứ nguồn hợp lệ được tạo dưới dạng bản nháp. Những nội dung chưa đủ căn cứ được ghi nhận để chuyên viên phân tích nghiệp vụ (BA) xem xét.

**Tác nhân chính:** chuyên viên phân tích nghiệp vụ (BA)

**Tác nhân phụ:** Không có

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Truy cập mục tài liệu nguồn của dự án. |  |
| 2 |  | Hệ thống hiển thị danh sách tài liệu, trạng thái xử lý và quyền sử dụng tài liệu bằng AI. |
| 3 | Chọn tài liệu cần sử dụng để tạo yêu cầu. |  |
| 4 | Nhấn nút “Chạy AI trên tài liệu”. |  |
| 5 |  | Hệ thống kiểm tra trạng thái tài liệu, quyền truy cập và quyền sử dụng AI của chuyên viên phân tích nghiệp vụ (BA). |
| 6 |  | Tài liệu có thể sử dụng, hệ thống tiếp nhận yêu cầu và bắt đầu xử lý bằng AI. |
| 7 | Truy cập mục “Hoạt động AI”. |  |
| 8 |  | Hệ thống hiển thị tiến độ xử lý tài liệu. |
| 9 |  | AI đọc nội dung tài liệu, xác định yêu cầu, tiêu chí chấp nhận, quy tắc nghiệp vụ và căn cứ nguồn tương ứng. |
| 10 |  | Hệ thống kiểm tra nội dung được tạo, đối chiếu với tài liệu nguồn và các yêu cầu hiện có trong dự án. |
| 11 |  | Những yêu cầu có căn cứ hợp lệ được lưu dưới dạng bản nháp cùng thông tin tài liệu nguồn. |
| 12 |  | Hiển thị kết quả xử lý và danh sách yêu cầu được tạo. |
| 13 | Chọn yêu cầu vừa được tạo. |  |
| 14 |  | Hệ thống hiển thị nội dung yêu cầu và căn cứ nguồn. |
| 15 | Kiểm tra, chỉnh sửa hoặc bổ sung nội dung theo UC10 nếu cần. |  |
| 16 |  | Kết thúc chức năng. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 3.1.1 | Chọn tài liệu chưa được phép sử dụng bằng AI. |  |
| 3.1.2 | Nhấn nút “Cho phép AI đọc tài liệu”. |  |
| 3.1.3 |  | Hệ thống cập nhật quyền sử dụng tài liệu bằng AI. |
| 3.1.4 |  | Tiếp tục tại bước 4 khi tài liệu đã sẵn sàng. |
| 5.1 |  | Tài liệu chưa hoàn thành quá trình trích xuất nội dung, hệ thống chưa cho phép bắt đầu xử lý bằng AI. |
| 5.1.1 | Thực hiện tiếp tục xử lý tài liệu theo UC15. |  |
| 5.1.2 |  | Sau khi tài liệu được xử lý thành công, tiếp tục tại bước 4. |
| 7.1.1 | Chọn hoạt động AI đã thực hiện trước đó. |  |
| 7.1.2 |  | Hệ thống hiển thị tài liệu nguồn, nội dung đã tạo và những công việc chưa hoàn thành. |
| 7.1.3 |  | Kết thúc chức năng. |
| 7.2.1 | Chọn hoạt động AI đang thực hiện và nhấn nút “Dừng tác vụ AI”. |  |
| 7.2.2 |  | Hệ thống tiếp nhận yêu cầu dừng xử lý. |
| 7.2.3 |  | Những nội dung đã được lưu trước khi dừng vẫn được giữ lại. |
| 7.2.4 |  | Cập nhật trạng thái hoạt động AI. Kết thúc chức năng. |
| 7.3.1 | Chọn hoạt động AI chưa hoàn thành và có thể tiếp tục xử lý. |  |
| 7.3.2 |  | Hệ thống hiển thị chức năng tiếp tục xử lý. |
| 7.3.3 | Xác nhận tiếp tục. |  |
| 7.3.4 |  | Hệ thống kiểm tra thông tin nguồn và tiếp tục phần công việc chưa hoàn thành. |
| 7.3.5 |  | Hiển thị tiến độ xử lý. Tiếp tục theo dõi tại bước 8. |
| 10.1 |  | Khi ứng viên trùng khớp an toàn với yêu cầu hiện có, quy trình có thể liên kết tài liệu làm nguồn hoặc tạo phiên bản mới nếu mã yêu cầu không đổi xác nhận cùng một yêu cầu. |
| 10.2 |  | Nếu kết quả đối chiếu còn mơ hồ, hệ thống ghi nhận mục cần xử lý thay vì tự chọn ứng viên đó làm yêu cầu mới. |
| 10.3 |  | Các ứng viên đủ căn cứ và được xử lý hợp lệ tiếp tục sang bước 11; mục còn xung đột chờ quyết định. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.2 |  | chuyên viên phân tích nghiệp vụ (BA) không có quyền sử dụng tài liệu hoặc thực hiện chức năng tạo yêu cầu bằng AI, hệ thống từ chối xử lý. |
| 9.1 |  | Quá trình xử lý bằng AI thất bại, hệ thống ghi nhận thông tin lỗi và trạng thái xử lý. |
| 9.2 |  | Tài liệu không cung cấp đủ căn cứ để xác định một số yêu cầu, hệ thống ghi nhận những nội dung cần làm rõ thay vì tạo yêu cầu thiếu căn cứ. |
| 11.1 |  | Tài liệu nguồn không còn hợp lệ tại thời điểm lưu yêu cầu, hệ thống từ chối tạo yêu cầu từ nguồn đó. |

### Giả định / Câu hỏi cần làm rõ

Nguồn mô tả: Chức năng này hỗ trợ chuyên viên phân tích nghiệp vụ (BA) xây dựng yêu cầu từ tài liệu nguồn bằng AI. Hệ thống xác định nội dung yêu cầu, tiêu chí chấp nhận và quy tắc nghiệp vụ dựa trên thông tin trong tài liệu, sau đó lưu kết quả dưới dạng bản nháp để chuyên viên phân tích nghiệp vụ (BA) kiểm tra. Không bổ sung hành vi ngoài bảng gốc; các điểm cần xác minh được nêu trong bảng rà soát riêng.

# UC32 - Đề xuất kế hoạch kiểm thử bằng AI

## Đặc tả nghiệp vụ đã đối chiếu

**Mô tả:** UC32 là chức năng độc lập cho phép đề xuất nội dung kế hoạch kiểm thử từ các phiên bản yêu cầu và tiêu chí chấp nhận được chọn. Kết quả chỉ để xem xét; UC32 không tự tạo hoặc lưu kế hoạch. UC31 hiện cũng gọi lại năng lực đề xuất này trong quy trình xử lý tài liệu, nhưng UC32 không phụ thuộc vào việc người dùng phải chạy UC31.

**Tiền điều kiện:** Người dùng có quyền đọc yêu cầu, xem kế hoạch kiểm thử và sử dụng AI của dự án. Có ít nhất một phiên bản yêu cầu hiện hành, thuộc đúng dự án và ở trạng thái đủ điều kiện; phiên bản có nội dung làm căn cứ. Người dùng cung cấp danh sách phiên bản yêu cầu và hướng dẫn bổ sung nếu cần. Bản mã hiện có chức năng xử lý riêng cho yêu cầu đề xuất, nhưng chưa tìm thấy màn hình riêng để người dùng nhập các thông tin này.

**Hậu điều kiện:** Hệ thống trả về đề xuất, thông tin căn cứ, các câu hỏi chưa được giải quyết và siêu dữ liệu kết quả AI. Không có kế hoạch mới được tạo hoặc lưu. Nếu kiểm tra đầu vào, quyền hoặc kết quả AI thất bại, đề xuất không được trả về như kết quả hợp lệ.

**Tác nhân chính:** Thành viên dự án có quyền đọc yêu cầu, đọc kế hoạch kiểm thử và sử dụng AI. Vai trò cụ thể không cố định là Tester.

**Tác nhân phụ:** Dịch vụ AI

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở chức năng đề xuất kế hoạch kiểm thử. |  |
| 2 | Chọn một hoặc nhiều phiên bản yêu cầu và nhập hướng dẫn bổ sung nếu cần. |  |
| 3 | Gửi yêu cầu tạo đề xuất. |  |
| 4 |  | Hệ thống kiểm tra quyền của người dùng, xác nhận từng phiên bản thuộc đúng dự án, còn là phiên bản hiện hành và ở trạng thái đủ điều kiện. |
| 5 |  | Hệ thống thu thập nội dung yêu cầu và tiêu chí chấp nhận làm căn cứ. |
| 6 |  | Dịch vụ AI tạo đề xuất từ căn cứ được cung cấp; đề xuất không tự lưu kế hoạch. |
| 7 |  | Hệ thống kiểm tra tham chiếu, trích dẫn và căn cứ của từng trường đề xuất cùng các rủi ro được nêu. |
| 8 |  | Hệ thống trả về đề xuất, thông tin căn cứ và câu hỏi còn bỏ ngỏ để nơi gọi chức năng hiển thị cho người dùng. |
| 9 | Xem xét đề xuất trong giao diện gọi chức năng. |  |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 2.1 |  | Nếu không có phiên bản yêu cầu nào được chọn hoặc danh sách không hợp lệ, hệ thống từ chối yêu cầu; kết thúc UC32. |
| 4.1 |  | Nếu một phiên bản không thuộc dự án, không còn hiện hành hoặc chưa ở trạng thái đủ điều kiện, hệ thống từ chối yêu cầu; kết thúc UC32. |
| 4.2 |  | Nếu người dùng thiếu quyền đọc kế hoạch, đọc yêu cầu hoặc sử dụng AI, hệ thống từ chối xử lý; kết thúc UC32. |
| 5.1 |  | Nếu không thu được căn cứ nội dung từ phiên bản yêu cầu và tiêu chí chấp nhận, hệ thống từ chối tạo đề xuất; kết thúc UC32. |
| 6.1 |  | Nếu dịch vụ AI không sẵn sàng hoặc bị gián đoạn, hệ thống trả thông báo lỗi có thể thử lại; kết thúc UC32. |
| 7.1 |  | Nếu đề xuất có tham chiếu không thuộc nguồn, trích dẫn không khớp, thiếu căn cứ cho trường được đề xuất hoặc có rủi ro dẫn nguồn không hợp lệ, hệ thống từ chối kết quả; kết thúc UC32. |

### Luồng sự kiện ngoại lệ

UC32 không có bước lưu kế hoạch hoặc thao tác chấp nhận/từ chối đề xuất. Người dùng có thể tạo kế hoạch riêng theo UC16, nhưng mã hiện tại không chuyển đề xuất sang UC16 tự động.

### Giả định / Câu hỏi cần làm rõ

- Bảng UC mô tả người dùng mở chức năng và chọn phiên bản yêu cầu. Cấu trúc yêu cầu của chức năng cũng nhận danh sách phiên bản và hướng dẫn; tuy nhiên chưa tìm thấy màn hình gọi trực tiếp ở frontend tại commit đang đối chiếu. Vì vậy các bước nhập liệu là hành vi theo đặc tả nghiệp vụ, còn vị trí/giao diện thao tác chưa được xác minh.
- UC31 hiện gọi cùng năng lực đề xuất trong xử lý tài liệu và giao diện Hoạt động AI hiển thị kết quả ở trạng thái chưa lưu. Đây là một nơi tái sử dụng UC32, không biến UC32 thành UC con hoặc bắt buộc người dùng phải vào UC31.
- Bảng nguồn nói người dùng chuyển các trường đề xuất sang UC16. Chưa thấy thao tác chuyển/lưu trực tiếp trong giao diện; giữ đây là câu hỏi cần xác nhận, không xem là hành vi đã triển khai.

# UC33 - Tạo ca kiểm thử bằng AI

## Đặc tả nghiệp vụ

**Mô tả:** Người kiểm thử có thể yêu cầu hệ thống đề xuất ca kiểm thử dựa trên một yêu cầu đã được duyệt. Người dùng xem các đề xuất, chọn mục phù hợp rồi lưu chúng thành ca nháp để tiếp tục chỉnh sửa và gửi duyệt.

**Tiền điều kiện:** Người dùng được phép tạo ca kiểm thử và sử dụng chức năng đề xuất; dự án có ít nhất một yêu cầu đã được duyệt.

**Hậu điều kiện:** Các đề xuất được người dùng chọn được lưu thành ca nháp. Những mục chưa chọn không được lưu.

**Tác nhân chính:** Người kiểm thử

**Tác nhân phụ:** Dịch vụ AI

### Luồng sự kiện chính

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 1 | Mở mục đề xuất ca kiểm thử. |  |
| 2 |  | Hệ thống hiển thị danh sách yêu cầu đã duyệt, ô chọn số lượng tối đa, ô nhập yêu cầu bổ sung và nút tạo đề xuất. |
| 3 | Chọn một yêu cầu đã duyệt; nhập số lượng tối đa và yêu cầu bổ sung nếu cần. |  |
| 4 | Nhấn “Tạo đề xuất”. |  |
| 5 |  | Hệ thống tạo đề xuất dựa trên yêu cầu đã chọn và hiển thị kết quả cùng cảnh báo nếu có. |
| 6 |  | Hệ thống hiển thị các mục tương tự nếu có và chọn sẵn những đề xuất chưa có mục tương tự. |
| 7 | Xem từng đề xuất, chọn hoặc bỏ chọn những mục cần lưu. |  |
| 8 | Nhấn nút lưu các đề xuất đã chọn. |  |
| 9 |  | Hệ thống lưu các mục đã chọn thành ca nháp, thông báo kết quả và làm mới danh sách ca nháp. |

### Luồng sự kiện thay thế

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.1 |  | Không có đề xuất phù hợp. Hệ thống thông báo và không hiển thị mục để lưu. Kết thúc UC. |
| 5.2 | Chọn yêu cầu khác sau khi đã xem kết quả. |  |
| 5.2.1 |  | Hệ thống xóa kết quả xem trước và lựa chọn trước đó. Quay lại bước 3. |

### Luồng sự kiện ngoại lệ

| Bước | Người dùng | Hệ thống |
|---|---|---|
| 5.3 |  | Không tạo được đề xuất. Hệ thống hiển thị thông báo lỗi và giữ người dùng ở màn hình hiện tại. Kết thúc UC. |
| 9.1 |  | Không lưu được các ca nháp đã chọn. Hệ thống hiển thị thông báo lỗi; các mục chưa lưu vẫn còn trong kết quả để người dùng thử lại. Quay lại bước 8. |

### Giả định / Câu hỏi cần làm rõ

Nhãn trên màn hình gọi chức năng này là “Đề xuất ca kiểm thử bằng AI”, trong khi mã UC hiện đặt tên “Tạo ca kiểm thử bằng AI”. Cần thống nhất tên UC với tên chức năng được trình bày trong khóa luận. Số lượng mặc định là 10 và giới hạn nhập là từ 1 đến 100; đây là cách màn hình đang hoạt động, không phải quy tắc nghiệp vụ tổng quát.
