REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS = """Draft Requirements only
The template must distinguish project context from individual requirements
Context may contain only objectives in_scope out_of_scope stakeholders actors_and_systems glossary assumptions and constraints
Use each context field only when its wording is present in the supplied evidence
Use User Story fields only when the source is a User Story
Do not turn every API operation into a requirement
When a requirement is derived from OpenAPI or Postman link only its relevant operations in api_operations using their exact source_ref and method plus path or url_template from the cited document
Do not invent operation identifiers paths methods or response codes
For each cited document reference return an exact quote in source_quotes keyed by that evidence reference
Copy extracted actors rules dependencies and acceptance criteria only when their wording is present in the cited evidence
Fill User Story actor goal and value only from a User Story source
Do not add source_quotes for template references
List duplicate or contradictory source claims in conflicts without choosing a winner
Mark applicable but absent details in missing_sections
Do not invent actors acceptance criteria response codes performance targets or external facts
Do not generate test cases or claim that the draft has been imported"""


def requirement_document_synthesis_instruction(verified_facts):
    rendered_facts = "\n".join(
        f"[{fact.artifact_type}:{fact.artifact_id}:{fact.artifact_version_id or ''} | {fact.fact_kind}] {fact.quote}"
        for fact in verified_facts
    )
    return (
        "Tổng hợp thành blueprint kiểm thử phù hợp riêng với dự án từ toàn bộ nguồn được chọn. "
        "Giữ nguyên nguồn và trích dẫn cho từng đề xuất. Phân biệt dữ kiện, thông tin còn thiếu, "
        "mơ hồ và mâu thuẫn giữa các nguồn. Không tự chọn cách giải quyết mâu thuẫn; thể hiện rõ "
        "các quyết định cần BA hoặc QA làm rõ. Không suy đoán actor, quy tắc, tiêu chí chấp nhận, "
        "dữ liệu, mã phản hồi hoặc giới hạn không có trong nguồn. Dùng các facts đã trích xuất và "
        "kiểm chứng dưới đây làm đầu vào cấu trúc; mỗi fact chỉ được áp dụng nếu trích dẫn và nguồn "
        "vẫn khớp tài liệu hiện hành. Không bỏ qua hoặc mở rộng ý nghĩa trích dẫn.\n\n"
        "FACTS ĐÃ KIỂM CHỨNG:\n" + rendered_facts
    )
