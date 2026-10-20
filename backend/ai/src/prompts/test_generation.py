"""Instructions for source-grounded test-case generation workflows."""


def requirement_test_generation_instruction():
    return "Tạo ca kiểm thử cụ thể từ tiêu chí và nguồn của Requirement. Không tạo hành vi hoặc giới hạn không có căn cứ."


def focused_requirement_test_generation_instruction():
    return (
        "Tập trung tạo ca kiểm thử cho đúng các acceptance criterion được chọn trong yêu cầu này. "
        "Không lặp lại nội dung đã được ca kiểm thử hiện có bao phủ. Chỉ dùng hành vi có dẫn chứng; "
        "nếu thiếu bằng chứng thì để trống thay vì tự suy diễn."
    )


def uncovered_obligation_test_generation_instruction():
    return (
        "Tạo ca kiểm thử mới chỉ cho nghĩa vụ chưa được ca hiện có bao phủ. Loại ca trùng, giữ liên "
        "kết phiên bản Requirement mới và chỉ dùng bằng chứng đã trích dẫn."
    )
