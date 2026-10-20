"""Task objectives for automatic project lifecycle event workflows."""


def generic_event_objective(trigger):
    return (
        f"Tự xử lý sự kiện {trigger} trong dự án theo bằng chứng nguồn và các bằng chứng liên "
        "quan được phép. Hoàn tất các bước tiếp theo cần thiết trong vòng đời Requirement, thiết "
        "kế kiểm thử, thực thi, lỗi, planning, release hoặc báo cáo khi chúng có liên quan. Thực "
        "hiện trong quyền hiện hành của chủ thể thực thi dự án, không dừng để xin duyệt từng hành "
        "động, ghi lại thay đổi và xác minh kết quả. Không suy đoán dữ kiện hay tuyên bố đã thực "
        "thi nếu chưa có kết quả thực tế."
    )


def document_ingested_objective():
    return (
        "Tự động xử lý tài liệu mới theo luồng Requirements, tạo mẫu có nguồn, tránh Requirement "
        "và Test Case trùng, kiểm tra chất lượng, hoàn tất vòng đời khi được quyền và xác minh "
        "mọi thay đổi"
    )


def requirement_changed_objective():
    return (
        "Tự động rà soát phiên bản Requirement vừa đổi, chốt theo cổng chất lượng, tạo các ca "
        "còn thiếu, loại trùng, đóng băng ca đạt chuẩn và xác minh dữ liệu đã lưu"
    )


def defect_recorded_objective():
    return (
        "Tạo hồ sơ phân tích cho defect mới bằng nội dung nguồn đã xác thực, tự sinh giả thuyết "
        "có căn cứ và đọc lại hồ sơ; không biến giả thuyết thành nguyên nhân đã xác nhận"
    )


def test_execution_recorded_objective():
    return (
        "Đối chiếu kết quả FAIL đã lưu với defect liên kết và các Nghĩa vụ kiểm thử có chứa đúng "
        "phiên bản Test Case; chỉ ghi feedback khi quan hệ đã được xác minh, không suy diễn từ "
        "kết quả PASS"
    )


def test_plan_approved_objective():
    return (
        "Từ Test Plan vừa được duyệt, tạo Test Run idempotent đúng snapshot đã duyệt, khởi chạy "
        "nếu quyền và môi trường cho phép, rồi đọc lại để xác minh phạm vi; không giả lập kết quả "
        "thực thi"
    )


def test_plan_changed_objective():
    return (
        "Kiểm tra Test Plan vừa thay đổi; nếu scope đủ điều kiện thì tự duyệt bằng quyền QA của "
        "dự án, tạo và khởi chạy Test Run theo snapshot, rồi đọc lại xác minh. Nếu thiếu điều kiện "
        "thì ghi rõ khoảng thiếu và không duyệt"
    )


def test_execution_observation_objective():
    return (
        "Đối chiếu kết quả thực thi vừa ghi với Test Run, phiên bản Test Case và defect đã liên "
        "kết; chỉ ghi nhận trạng thái có bằng chứng, không tự kết luận nguyên nhân hoặc tạo defect "
        "từ một kết quả thất bại"
    )


def work_item_changed_observation_objective():
    return (
        "Đọc lại Work Item vừa thay đổi trong phạm vi dự án rồi đánh giá tác động có bằng chứng "
        "trước mọi đề xuất tiếp theo"
    )


def test_case_changed_observation_objective():
    return (
        "Tự động kiểm tra chất lượng bản nháp Test Case vừa thay đổi bằng bộ kiểm tra dự án, lưu "
        "kết quả kiểm tra và báo rõ các phát hiện; không tự sửa nội dung bản nháp"
    )


def test_case_approved_observation_objective():
    return (
        "Đọc lại phiên bản Test Case đã đóng băng, xác minh trạng thái và các liên kết nguồn đang "
        "lưu; chỉ ghi nhận kết quả đọc lại, không sửa snapshot đã duyệt"
    )


def release_changed_observation_objective():
    return (
        "Đọc lại Release sau thay đổi, đối chiếu trạng thái và bằng chứng kiểm thử liên quan trước "
        "khi đề xuất bước tiếp theo"
    )
