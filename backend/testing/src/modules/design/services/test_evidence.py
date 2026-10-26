from src.core.common import plain_text


def requirement_test_evidence_text(version):
    """Render the exact Requirement evidence shared by generation and persistence."""
    sections = [
        str(version.get("plain_text_projection") or plain_text(version.get("content_doc", {}))).strip()
    ]
    for field, label in (
        ("actors", "Tác nhân"),
        ("business_rules", "Quy tắc nghiệp vụ"),
        ("dependencies", "Phụ thuộc"),
    ):
        values = version.get(field) or []
        if values:
            sections.append(f"{label}:\n" + "\n".join(str(value).strip() for value in values if str(value).strip()))
    details = version.get("details") or {}
    for field, label in (
        ("main_flow", "Luồng chính"),
        ("exception_flow", "Luồng ngoại lệ"),
        ("data_rules", "Quy tắc dữ liệu"),
        ("integration", "Tích hợp"),
        ("quality_measure", "Thuộc tính chất lượng"),
    ):
        value = details.get(field)
        if isinstance(value, str) and value.strip():
            sections.append(f"{label}:\n{value.strip()}")
    return "\n\n".join(section for section in sections if section)
