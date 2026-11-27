# Mô tả chi tiết sáu quy trình nghiệp vụ Veriq

Các mục dưới đây được viết theo hướng thuyết minh quy trình, đi cùng sáu sơ đồ BPMN trong thư mục `drawio/`. Trình tự và điều kiện được đối chiếu với các service, API và bảng trạng thái trong source code. Một số quyền và chính sách có thể được cấu hình theo dự án; nơi mã nguồn không ấn định một giá trị chung, phần mô tả sẽ giữ nguyên tính điều kiện thay vì tự đặt quy tắc.

## 3.2.1 Quy trình nhập tài liệu và trích xuất yêu cầu

Quy trình bắt đầu khi người dùng có quyền nhập yêu cầu cung cấp một tài liệu hoặc nội dung nguồn. Tùy hình thức nhập, hệ thống kiểm tra định dạng, kích thước, nội dung và khả năng xử lý của tài liệu. Trước khi tiếp tục, Veriq còn có thể yêu cầu người dùng xác nhận nếu phát hiện tài liệu hoặc nội dung có khả năng trùng với nguồn đã nhập trước đó. Đầu vào không hợp lệ, tài liệu lưu trữ hoặc tài liệu chưa được phân tích nội dung sẽ không được đưa qua bước trích xuất như thể đã sẵn sàng.

Sau khi tạo bản ghi tài liệu và import job, Veriq đọc nội dung đã chuẩn hóa rồi trích xuất các **yêu cầu đề xuất từ tài liệu**. Tên gọi này phân biệt kết quả phân tích với yêu cầu chính thức: ở thời điểm này, nội dung mới là đề xuất có dẫn chiếu nguồn, chưa được ghi thành yêu cầu trong kho. Cách trích xuất có thể khác theo loại tài liệu và cấu hình; mã nguồn có đường xử lý riêng cho một số định dạng cấu trúc, do đó không nên hiểu rằng mọi tài liệu đều qua cùng một mô hình AI.

Khi có kết quả, người dùng rà soát từng đề xuất, đối chiếu phần trích dẫn với tài liệu, xem các kết quả so sánh trùng và quyết định nội dung cần giữ. Người dùng có thể chỉnh sửa nội dung, gộp các mục cùng ý, tách một mục chứa nhiều yêu cầu, hoặc loại mục không phù hợp. Nếu tài liệu không tạo ra đề xuất nào, luồng dừng với kết quả rỗng; nếu không chọn mục nào để nhập, hệ thống không tạo yêu cầu.

Để xác nhận, người dùng chọn ít nhất một mục. Veriq kiểm tra nội dung và dẫn chiếu nguồn, phát hiện xung đột mã yêu cầu hoặc trường hợp trùng chưa được giải quyết, rồi yêu cầu làm rõ nếu cần. Khi hợp lệ, các yêu cầu được tạo trong một transaction cùng trạng thái ghi nhận của import job; các mục không được chọn được lưu là không nhập. Nếu ghi dữ liệu thất bại, hệ thống đưa job về trạng thái có thể xử lý lại thay vì coi lần xác nhận là thành công. Các yêu cầu vừa nhập bắt đầu ở trạng thái `DRAFT`, nên vẫn phải đi qua quy trình soạn thảo và phê duyệt yêu cầu nếu cần trở thành baseline.

**Điểm kết thúc:** yêu cầu đã chọn được ghi nhận và liên kết về tài liệu nguồn; hoặc luồng dừng vì đầu vào không hợp lệ, không có đề xuất, người dùng không chọn mục nào, hay xung đột chưa được giải quyết.

**Căn cứ chính:** `requirement_import_workflow.py`: `create_requirement_import_job`, `extract_requirement_candidates`, `compare_requirement_import_job`, `review_requirement_import_job`, `merge_requirement_import_candidates`, `split_requirement_import_candidate`, `reject_requirement_import_candidate`, `apply_requirement_import_job`, `confirm_requirement_import_job`.

## 3.2.2 Quy trình soạn thảo và phê duyệt yêu cầu

Một yêu cầu có thể được tạo mới hoặc cập nhật trong bản nháp. Người soạn hoàn thiện nội dung, tiêu đề, loại yêu cầu, tiêu chí chấp nhận và những trường tùy chỉnh được dự án sử dụng. Trước khi gửi rà soát, hệ thống yêu cầu nội dung không rỗng, kiểm tra giá trị trường và đối chiếu revision hiện tại. Nhờ vậy, bản sửa cũ không thể âm thầm ghi đè lên thay đổi mới hơn.

Khi yêu cầu đã ở trạng thái `DRAFT` hoặc `READY`, người có quyền gửi rà soát chuyển phiên bản sang `IN_REVIEW` và ghi nhận người gửi, thời điểm cùng ghi chú. Nếu phiên bản không còn ở trạng thái cho phép, revision không khớp hoặc dữ liệu bắt buộc thiếu, thao tác bị từ chối và trạng thái không được chuyển tiếp. Một số vai trò đặc biệt có thể tự động phê duyệt theo chính sách quyền hiện hành; đây là nhánh điều kiện trong mã, không phải quyền mặc định của mọi người soạn.

Ở bước rà soát, người có quyền đánh giá nội dung và tiêu chí chấp nhận. Nếu cần sửa, yêu cầu được trả về `DRAFT` kèm nhận xét để người soạn cập nhật rồi gửi lại. Nếu nội dung được chấp thuận, Veriq kiểm tra các lỗi nghiêm trọng của yêu cầu và tiêu chí chấp nhận, sau đó thực hiện baseline trong transaction. Việc này cập nhật phiên bản chuẩn hiện hành, phê duyệt các tiêu chí liên quan và ghi nhận lịch sử. Vì vậy, hành động “người rà soát đồng ý” chưa tự nó đồng nghĩa với baseline đã hoàn tất.

Sau baseline, phiên bản được đưa vào chỉ mục để phục vụ tra cứu. Nếu chỉ mục vector không sẵn sàng, kết quả có thể ở chế độ suy giảm thay vì phủ nhận rằng baseline đã được ghi nhận; trạng thái này cần được hiểu là chất lượng lập chỉ mục chưa đầy đủ, không phải một phê duyệt nghiệp vụ khác. Rà soát kỹ thuật cũng có trong mã nguồn, nhưng không được áp đặt là bước bắt buộc cho tất cả trường hợp trong mô tả này.

**Điểm kết thúc:** phiên bản yêu cầu trở thành baseline và được ghi nhận; hoặc quay về bản nháp để chỉnh sửa; hoặc chưa được phê duyệt do lỗi nội dung, quyền, trạng thái hay xung đột phiên bản.

**Căn cứ chính:** `requirement_lifecycle.py`: `save_requirement_ready`, `submit_requirement_for_review`, `return_requirement_for_changes`, `technical_review_requirement`, `baseline_requirement`.

## 3.2.3 Quy trình lập và phê duyệt kế hoạch kiểm thử

Người lập khởi tạo kế hoạch kiểm thử trong dự án, có thể nhập phạm vi trực tiếp hoặc tham khảo gợi ý được tạo từ dữ liệu hiện có. Gợi ý tự động chỉ hỗ trợ việc lập kế hoạch; người dùng vẫn chịu trách nhiệm kiểm tra và hoàn thiện nội dung. Phạm vi thường liên quan đến phiên bản yêu cầu, bộ kiểm thử, ca kiểm thử, môi trường và kỳ kiểm thử nếu có. Các liên kết này cần còn hợp lệ trong dự án và đáp ứng quy tắc đầy đủ mà hệ thống kiểm tra.

Khi kế hoạch chưa đủ điều kiện, thao tác gửi rà soát bị chặn kèm các phát hiện để người lập bổ sung. Nếu nội dung đạt yêu cầu, người lập gửi kế hoạch; trạng thái chuyển sang `IN_REVIEW`, thông tin người gửi và ghi chú rà soát được lưu lại. Người rà soát độc lập có thể yêu cầu chỉnh sửa. Trong trường hợp đó, kế hoạch quay về `DRAFT`, kèm lý do, để người lập cập nhật và gửi lại. Nếu người lập thuộc nhóm được tự phê duyệt, hệ thống có thể thực hiện bước duyệt tiếp theo tự động, nhưng chỉ khi điều kiện về quyền và trạng thái thỏa mãn.

Khi phê duyệt, hệ thống không chỉ đổi trạng thái. Veriq kiểm tra lại phạm vi, tính đầy đủ, phiên bản bộ kiểm thử và điều kiện độc lập giữa người lập với người duyệt. Nếu bộ kiểm thử hoặc snapshot phạm vi thay đổi trong lúc rà soát, kế hoạch cần được xem xét lại; một snapshot cũ không nên được dùng như thể vẫn khớp với nội dung mới. Khi mọi điều kiện đạt, hệ thống lưu snapshot đã duyệt cùng hash làm dấu nhận diện phiên bản phạm vi.

Snapshot này có ý nghĩa ở quy trình thực thi: lượt chạy sau phải bám vào kế hoạch đã duyệt và phạm vi được đóng dấu, thay vì lấy ngầm nội dung đang chỉnh sửa. Như vậy, việc phê duyệt kế hoạch tạo ra một mốc kiểm soát có thể truy nguyên, không chỉ là một nhãn trạng thái.

**Điểm kết thúc:** kế hoạch được duyệt và có snapshot/hash; hoặc quay lại người lập để chỉnh sửa; hoặc bị chặn do thiếu phạm vi, quyền không phù hợp, dữ liệu tham chiếu thay đổi hay xung đột revision.

**Căn cứ chính:** `test_plan.py`: `create_test_plan_record`, `validate_test_plan_record`, `submit_test_plan_record`, `approve_test_plan_record`, `request_test_plan_revision`, `plan_snapshot`, `plan_snapshot_hash`; `test_plan_generation.py::generate_test_plan_suggestion`.

## 3.2.4 Quy trình thiết kế và phê duyệt ca kiểm thử

Người thiết kế bắt đầu từ một phiên bản yêu cầu phù hợp và còn hiệu lực. Họ có thể soạn ca kiểm thử thủ công, hoặc yêu cầu AI sinh bản xem trước dựa trên yêu cầu và tiêu chí chấp nhận đã chọn. Trước khi lưu các đề xuất sinh tự động, người dùng cần xem trước và lựa chọn; bản sinh tự động không được đưa thẳng thành ca đã phê duyệt. Hệ thống cũng kiểm tra nguồn có còn hiện hành trong thời gian sinh hay không. Nếu yêu cầu hoặc tiêu chí thay đổi giữa lúc tạo bản xem trước và lúc hoàn tất, kết quả được xem là cũ và cần tạo lại.

Sau khi chọn hoặc soạn nội dung, người thiết kế hoàn thiện hành động, dữ liệu kiểm thử khi cần, và kết quả mong đợi cho từng bước. Veriq chạy lint để tìm bước thiếu, dữ liệu không đầy đủ hoặc vấn đề về truy nguyên nguồn. Tùy thiết lập dự án, lỗi lint có thể chặn việc gửi duyệt; cấu hình mặc định trong mã đặt chế độ chặn là bật. Ca sinh bằng AI cần có bằng chứng nguồn để người rà soát kiểm tra nội dung có bám sát yêu cầu hay không.

Ca đủ điều kiện được gửi sang `IN_REVIEW`. Người rà soát kiểm tra tính kiểm chứng của từng bước, nguồn yêu cầu và khả năng trùng với ca đang hiệu lực. Nếu ca cần sửa, trạng thái quay về `DRAFT` cùng ghi chú. Nếu người rà soát đồng ý, hệ thống kiểm tra lại nguồn, lint, bước kiểm thử và kết quả mong đợi. Khi phát hiện ca gần trùng, người duyệt phải ghi lý do vì sao vẫn cần giữ riêng; nếu không, thao tác duyệt bị chặn để tránh tạo bản sao không được giải thích.

Khi các kiểm tra đạt, Veriq tạo phiên bản ca đã duyệt và đóng băng bản nháp tương ứng. Từ đây, việc thực thi nên tham chiếu phiên bản đã đóng băng để kết quả chạy gắn với nội dung cụ thể. Tự phê duyệt có thể xảy ra với vai trò phù hợp; các điều kiện độc lập rà soát vẫn phải được áp dụng theo mã nguồn.

**Điểm kết thúc:** phiên bản ca kiểm thử được duyệt và đóng băng; hoặc bản nháp quay lại để sửa; hoặc bị chặn vì thiếu bước kiểm chứng, lỗi lint, bằng chứng nguồn không còn hợp lệ hay trùng lặp chưa có giải trình.

**Căn cứ chính:** `test_case_generation.py::generate_test_case_draft_records`; `test_case_lifecycle.py`: `lint_test_case_draft_record`, `submit_test_case_review_record`, `request_test_case_changes_record`, `approve_test_case_draft_record`, `build_test_case_version`; các API trong `test_design.py`.

## 3.2.5 Quy trình phân công và thực thi kiểm thử

Người điều phối tạo lượt chạy bằng cách chọn kế hoạch kiểm thử, phạm vi ca hoặc bộ kiểm thử, môi trường và thông tin bản phát hành/bản dựng nếu cần. Theo mã hiện tại, kế hoạch đã duyệt là điều kiện bắt buộc để tạo lượt chạy. Veriq xác minh snapshot đã duyệt, kiểm tra rằng ca nằm trong phạm vi của kế hoạch và xác nhận các phiên bản ca còn hợp lệ. Nếu snapshot đã thay đổi, phạm vi rỗng, hoặc có ca ngoài phạm vi, hệ thống không tạo lượt chạy với dữ liệu không nhất quán.

Khi kiểm tra đạt, lượt chạy được tạo ở trạng thái ban đầu, gắn với snapshot kế hoạch và các phiên bản ca cụ thể; hệ thống khởi tạo kết quả cho phạm vi đó. Người điều phối có thể phân công toàn lượt chạy cho một tester hoặc chỉ định từng ca cho từng người. Một người thực thi chỉ được ghi kết quả cho các ca được giao cho họ. Do đó, “có quyền thực thi” và “được phân công vào ca cụ thể” là hai điều kiện khác nhau.

Tester bắt đầu lượt chạy, lần lượt thực thi từng ca được giao và ghi nhận trạng thái cùng kết quả bước. Các trạng thái kết quả được kiểm soát bằng ma trận chuyển trạng thái; ví dụ, kết quả chưa chạy có thể chuyển sang đang thực thi hoặc một trạng thái kết quả phù hợp. Gateway lặp trong sơ đồ biểu thị còn ca nào cần xử lý trong phạm vi của lượt chạy; nó không khẳng định toàn bộ ca chạy tuần tự hay song song. Khi kết quả kiểm thử thất bại, người thực thi có thể liên kết lỗi với kết quả đó để chuyển sang quy trình xử lý lỗi.

Khi hoàn tất, Veriq đếm số kết quả đã đạt trạng thái được xem là có kết quả. Nếu chưa đủ toàn bộ ca, lượt chạy chỉ được hoàn tất một phần khi cấu hình dự án `partial_complete_allowed` cho phép; mặc định trong mã là không cho phép. Người có quyền cũng có thể hủy lượt chạy khi nó còn ở trạng thái `DRAFT`, `READY` hoặc `IN_PROGRESS`, với lý do được ghi lại. Chạy lại một lượt đã kết thúc là chức năng có trong source, nhưng thuộc một thao tác vòng đời riêng và không nằm trong phạm vi sơ đồ này.

**Điểm kết thúc:** lượt chạy hoàn tất đầy đủ hoặc một phần theo chính sách; lượt chạy bị hủy có lý do; hoặc thao tác hoàn tất bị từ chối do còn thiếu kết quả hay trạng thái/revision không phù hợp.

**Căn cứ chính:** `test_run.py`: `create_test_run_record`, `assign_test_run_record`, `rerun_test_run_record`; `test_run_execution.py`: `start_test_run_record`, `record_test_result_entry`, `complete_test_run_record`, `abort_test_run_record`; `execution_state.py`: `execution_transitions`, `assigned_execution_versions`, `require_case_execution_assignment`.

## 3.2.6 Quy trình xử lý lỗi và kiểm thử lại

Một lỗi có thể được tạo từ kết quả kiểm thử thất bại hoặc được ghi nhận độc lập rồi liên kết sau. Khi gắn với kết quả, Veriq xác minh kết quả đó thực sự là `FAIL`, thuộc đúng dự án và có ngữ cảnh ca kiểm thử/lượt chạy hợp lệ. Nếu người dùng cung cấp phiên bản ca hoặc thông tin môi trường không khớp với kết quả đã liên kết, hệ thống từ chối để không tạo chuỗi truy nguyên sai. Lỗi mới được phân loại theo severity/priority phù hợp với cấu hình dự án.

Sau khi được ghi nhận, lỗi đi qua bước phân loại. Ma trận trạng thái cho phép lỗi mới (`NEW`) được xác nhận (`CONFIRMED`), đánh dấu trùng (`DUPLICATE`) hoặc từ chối (`REJECTED`). Lỗi đã xác nhận có thể tiếp tục được giao xử lý, chuyển sang `IN_PROGRESS`, hoặc được phân loại lại nếu có căn cứ. Trạng thái chuyển chỉ hợp lệ khi quyền của người thao tác, revision và quan hệ người được giao đều thỏa mãn. Các thay đổi quan trọng được ghi nhận cùng lý do và audit trail.

Người xử lý khắc phục lỗi rồi chuyển sang `RESOLVED`. Từ đây có hai hướng đáng chú ý: chuyển lỗi sang `READY_FOR_RETEST` để tester kiểm tra lại, hoặc mở lại trực tiếp (`REOPENED`) khi cần tiếp tục xử lý. Khi chạy kiểm thử lại, tester phải có quyền thực thi và được phân công đúng ca. Kết quả dùng để retest phải là kết quả mới, mang trạng thái `PASS` hoặc `FAIL`, đồng thời tham chiếu đúng phiên bản ca gắn với lỗi. Kết quả cũ, ca không khớp hoặc lỗi chưa ở trạng thái sẵn sàng kiểm thử lại đều không được chấp nhận.

Nếu kết quả mới là `PASS`, lỗi chuyển sang `CLOSED`. Ngược lại, `FAIL` đưa lỗi về `REOPENED` để tiếp tục khắc phục. Cần phân biệt điểm kết thúc của một lượt xử lý với kết thúc vĩnh viễn vòng đời lỗi: source cho phép mở lại lỗi từ một số trạng thái như `DUPLICATE`, `REJECTED` và `CLOSED`. Vì thế, sơ đồ biểu diễn kết thúc của lượt xử lý hiện tại; thao tác mở lại một lỗi đã đóng hoặc đã bị loại trừ có thể khởi động một lượt xử lý tiếp theo.

**Điểm kết thúc:** lỗi đóng sau khi retest đạt; lỗi mở lại khi retest không đạt; lỗi đang chờ kiểm thử lại; hoặc lượt phân loại kết thúc ở trùng/từ chối nhưng vẫn có thể được mở lại theo quyền và chuyển trạng thái cho phép.

**Căn cứ chính:** `defect_records.py`: `create_defect_record`, `_create_defect_record`; `defect_lifecycle.py`: `transition_defect_record`, `retest_defect_record`; `execution_state.py::defect_transitions`; quyền thực thi theo `assigned_execution_versions` và `require_case_execution_assignment`.

## Ghi chú về phạm vi

Tên lane trong sơ đồ là nhãn chức năng tổng quát, chẳng hạn người soạn, người rà soát, điều phối viên và tester. Source code xác định quyền thao tác tốt hơn chức danh tổ chức, nên cần chủ quy trình ánh xạ các lane sang vai trò thực tế trước khi dùng sơ đồ như tài liệu SOP. Các chính sách như tự phê duyệt, lint blocking hay hoàn tất một phần cũng có thể chịu ảnh hưởng của quyền và cấu hình dự án.
