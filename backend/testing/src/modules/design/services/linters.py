import re
from difflib import SequenceMatcher

from src.core.common import plain_text


def evaluate_rules(scope, value):
    if scope == "requirement":
        return [
            finding
            for finding in (
                _finding("MISSING_REQUIREMENT_CONTENT", "error", "Nội dung yêu cầu đang để trống", "Nhập mô tả phạm vi hoặc chức năng mà hệ thống phải đáp ứng", "content") if not _text(value.get("content")) else None,
                _finding("MISSING_ACTOR", "error", "Yêu cầu chưa xác định tác nhân", "Bổ sung tác nhân thực hiện hoặc chịu tác động", "actors") if not _values(value.get("actors")) else None,
                _finding("MISSING_BUSINESS_RULE", "error", "Yêu cầu chưa có quy tắc nghiệp vụ", "Bổ sung quy tắc có căn cứ hoặc xác nhận rõ yêu cầu không có quy tắc nghiệp vụ", "business_rules") if not _values(value.get("business_rules")) else None,
                _finding("MISSING_ACCEPTANCE_CRITERIA", "error", "Yêu cầu chưa có tiêu chí chấp nhận", "Bổ sung ít nhất một điều kiện chấp nhận có thể kiểm thử", "acceptance_criteria") if not _values(value.get("acceptance_criteria")) else None,
            )
            if finding
        ]
    if scope == "acceptance_criterion" and not _text(value.get("text")):
        return [_finding("EMPTY_ACCEPTANCE_CRITERION", "error", f"Tiêu chí {value.get('key') or ''} đang để trống", "Nhập điều kiện kích hoạt và hành vi quan sát được", "acceptance_criteria")]
    if scope == "test_case":
        findings = []
        if not _text(value.get("expected_result_doc")):
            findings.append(_finding("TCQ-001", "error", "Thiếu kết quả mong đợi", "Cập nhật kết quả mong đợi rồi chạy kiểm tra lại"))
        if not _values(value.get("requirement_version_ids")) and not _values(value.get("acceptance_criterion_ids")):
            findings.append(_finding("TCQ-005", "error", "Ca kiểm thử chưa có liên kết truy vết", "Liên kết yêu cầu hoặc tiêu chí chấp nhận rồi chạy kiểm tra lại"))
        if not value.get("test_data") and not any(item.get("test_data") for item in value.get("steps", [])):
            findings.append(_finding("TCQ-009", "warning", "Thiếu dữ liệu kiểm thử", "Bổ sung dữ liệu kiểm thử cho ca hoặc từng bước"))
        return findings
    if scope == "test_step" and not _text(value.get("expected_doc")):
        return [_finding("TCQ-001", "warning", "Bước chưa có kết quả mong đợi", "Bổ sung kết quả mong đợi cho bước")]
    if scope == "test_basis" and not _text(value.get("text")):
        return [{**_finding("EMPTY_EXPECTED_BEHAVIOR", "BLOCKER", "Nội dung kiểm thử đang trống", "Bổ sung tiêu chí quan sát được và có thể kiểm chứng"), "category": "UNTESTABLE"}]
    return []


def _finding(rule_id, severity, message, suggestion, target_field=None):
    finding = {"rule_id": rule_id, "severity": severity, "span": None, "message": message, "suggestion": suggestion}
    if target_field:
        finding["target_field"] = target_field
    return finding


def _text(value):
    return plain_text(value).strip() if isinstance(value, dict) else str(value or "").strip()


def _values(value):
    values = value if isinstance(value, list) else [value]
    return [item for item in values if _text(item)]


def requirement_findings(version, acceptance_criteria=None):
    text = version.get("plain_text_projection") or plain_text(version.get("content_doc", {}))
    criteria = []
    for index, item in enumerate(acceptance_criteria or []):
        content = (
            str(item.get("plain_text") or plain_text(item.get("content_doc", {})) or "")
            if isinstance(item, dict)
            else str(item or "")
        ).strip()
        criteria.append(
            {
                "id": item.get("_id") if isinstance(item, dict) else None,
                "key": item.get("key")
                if isinstance(item, dict)
                else f"AC-{index + 1:02d}",
                "text": content,
            }
        )
    normalized_version = {
        **version,
        "content": text,
        "acceptance_criteria": [item["text"] for item in criteria]
        if acceptance_criteria is not None
        else version.get("acceptance_criterion_ids", []),
    }
    findings = evaluate_rules("requirement", normalized_version)
    for criterion in criteria:
        identity = {"criterion_id": criterion["id"], "criterion_key": criterion["key"]}
        findings.extend(
            {**finding, **identity}
            for finding in evaluate_rules("acceptance_criterion", criterion)
        )
    return findings


def requirement_duplicate_score(left, right):
    left_text = _requirement_projection(left)
    right_text = _requirement_projection(right)
    if not left_text or not right_text:
        return 0, []
    if left_text == right_text:
        return 1, ["Nội dung yêu cầu trùng khớp hoàn toàn"]
    lexical = SequenceMatcher(None, left_text, right_text).ratio()
    left_terms = set(re.findall(r"[\wÀ-ỹ]+", left_text))
    right_terms = set(re.findall(r"[\wÀ-ỹ]+", right_text))
    semantic = len(left_terms & right_terms) / max(1, len(left_terms | right_terms))
    left_rules = {
        str(value).strip().lower() for value in left.get("business_rules", []) if str(value).strip()
    }
    right_rules = {
        str(value).strip().lower()
        for value in right.get("business_rules", [])
        if str(value).strip()
    }
    rule_overlap = (
        len(left_rules & right_rules) / max(1, len(left_rules | right_rules))
        if left_rules or right_rules
        else 0
    )
    score = min(
        1,
        0.65 * lexical + 0.25 * semantic + 0.1 * rule_overlap,
    )
    reasons = []
    if lexical >= 0.75:
        reasons.append("Tiêu đề và nội dung gần giống")
    if semantic >= 0.55:
        reasons.append("Có nhiều thuật ngữ nghiệp vụ chung")
    if rule_overlap > 0:
        reasons.append("Có quy tắc nghiệp vụ trùng nhau")
    return round(score, 4), reasons


def lint_test_case(draft):
    findings = evaluate_rules("test_case", draft)
    if (
        draft.get("origin") == "ai_generated"
        and draft.get("source_evidence")
        and not draft.get("evidence_refs")
    ):
        findings.append(
            {
                "rule_id": "AI_EVIDENCE_INVALIDATED",
                "severity": "warning",
                "span": None,
                "message": "Dẫn chứng AI không còn áp dụng sau khi ca được chỉnh sửa",
                "suggestion": "Rà soát lại ca theo yêu cầu và tiêu chí chấp nhận trước khi duyệt",
            }
        )
    if not has_verifiable_steps(draft):
        findings.append({
            "rule_id": "TEST_CASE_STEPS_REQUIRED",
            "severity": "error",
            "span": None,
            "message": "Ca kiểm thử cần có bước thực hiện và kết quả mong đợi cho từng bước",
            "suggestion": "Bổ sung các bước có hành động và kết quả kiểm chứng trước khi gửi duyệt",
        })
    for step in draft.get("steps", []):
        findings.extend(
            {**finding, "step_id": step.get("id")}
            for finding in evaluate_rules("test_step", step)
        )
    return findings


def has_verifiable_steps(draft):
    steps = draft.get("steps") or []
    return bool(steps) and all(
        plain_text(step.get("action_doc") or {}).strip()
        and plain_text(step.get("expected_doc") or {}).strip()
        for step in steps
    )


def duplicate_score(left, right, threshold):
    left_text = _test_projection(left)
    right_text = _test_projection(right)
    lexical = SequenceMatcher(None, left_text, right_text).ratio()
    left_data = [left.get("test_data") or {}, *(step.get("test_data") or {} for step in left.get("steps", []))]
    right_data = [right.get("test_data") or {}, *(step.get("test_data") or {} for step in right.get("steps", []))]
    left_actions = " ".join(plain_text(step.get("action_doc", {})) for step in left.get("steps", []))
    right_actions = " ".join(plain_text(step.get("action_doc", {})) for step in right.get("steps", []))
    def conflicting_data_values(left_value, right_value):
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            return any(
                conflicting_data_values(left_value[key], right_value[key])
                for key in left_value.keys() & right_value.keys()
            )
        if isinstance(left_value, list) and isinstance(right_value, list):
            return any(
                conflicting_data_values(left_item, right_item)
                for left_item, right_item in zip(left_value, right_value)
            )
        if isinstance(left_value, (str, int, float, bool)) and isinstance(
            right_value, (str, int, float, bool)
        ):
            return str(left_value) != str(right_value)
        return False

    if any(
        conflicting_data_values(left_value, right_value)
        for left_value, right_value in zip(left_data, right_data)
    ):
        return 0, ["Giá trị dữ liệu đầu vào khác nhau"]
    left_values = set(re.findall(r"\d+(?:[.,]\d+)?", left_actions))
    right_values = set(re.findall(r"\d+(?:[.,]\d+)?", right_actions))
    if left_values and right_values and left_values != right_values:
        return 0, ["Giá trị đầu vào khác nhau"]
    left_step_outcomes = [
        " ".join(plain_text(step.get("expected_doc", {})).lower().split())
        for step in left.get("steps", [])
    ]
    right_step_outcomes = [
        " ".join(plain_text(step.get("expected_doc", {})).lower().split())
        for step in right.get("steps", [])
    ]
    if left_step_outcomes and right_step_outcomes and left_step_outcomes != right_step_outcomes:
        return 0, ["Kết quả từng bước khác nhau"]
    left_outcome = " ".join(" ".join([
        *(plain_text(step.get("expected_doc", {})) for step in left.get("steps", [])),
        plain_text(left.get("expected_result_doc", {})),
    ]).lower().split())
    right_outcome = " ".join(" ".join([
        *(plain_text(step.get("expected_doc", {})) for step in right.get("steps", [])),
        plain_text(right.get("expected_result_doc", {})),
    ]).lower().split())
    if (
        not left_outcome
        or not right_outcome
        or SequenceMatcher(None, left_outcome, right_outcome).ratio() < threshold
    ):
        return 0, ["Kết quả mong đợi không trùng khớp"]
    left_links = set(left.get("requirement_version_ids", [])) | set(
        left.get("acceptance_criterion_ids", [])
    )
    right_links = set(right.get("requirement_version_ids", [])) | set(
        right.get("acceptance_criterion_ids", [])
    )
    trace = len(left_links & right_links) / max(1, len(left_links | right_links))
    left_steps = len(left.get("steps", []))
    right_steps = len(right.get("steps", []))
    structure = 1 - abs(left_steps - right_steps) / max(1, left_steps, right_steps)
    score = (
        0.6 * lexical + 0.25 * trace + 0.15 * structure
    )
    reasons = []
    if lexical >= 0.75:
        reasons.append("Nội dung và kết quả mong đợi gần giống")
    if trace > 0:
        reasons.append("Cùng liên kết yêu cầu hoặc tiêu chí chấp nhận")
    if structure >= 0.8:
        reasons.append("Cấu trúc bước tương đồng")
    return round(score, 4), reasons


def _test_projection(value):
    step_text = " ".join(
        f"{plain_text(step.get('action_doc', {}))} {plain_text(step.get('expected_doc', {}))}"
        for step in value.get("steps", [])
    )
    return " ".join(
        [
            str(value.get("title", "")),
            plain_text(value.get("preconditions_doc", {})),
            step_text,
            plain_text(value.get("expected_result_doc", {})),
        ]
    ).lower()


def _requirement_projection(value):
    title = str(value.get("title", ""))
    content = value.get("plain_text_projection") or plain_text(value.get("content_doc", {}))
    criteria = " ".join(
        item.get("plain_text") or plain_text(item.get("content_doc", {}))
        for item in value.get("acceptance_criteria", [])
    )
    return " ".join(f"{title} {content} {criteria}".lower().split())
