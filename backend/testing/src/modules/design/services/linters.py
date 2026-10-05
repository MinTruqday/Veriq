import re
from difflib import SequenceMatcher

from src.core.common import plain_text
from src.modules.quality.services.quality_policy import evaluate_rules


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
    for step in draft.get("steps", []):
        findings.extend(
            {**finding, "step_id": step.get("id")}
            for finding in evaluate_rules("test_step", step)
        )
    return findings


def duplicate_score(left, right):
    left_text = _test_projection(left)
    right_text = _test_projection(right)
    lexical = SequenceMatcher(None, left_text, right_text).ratio()
    left_data = [left.get("test_data") or {}, *(step.get("test_data") or {} for step in left.get("steps", []))]
    right_data = [right.get("test_data") or {}, *(step.get("test_data") or {} for step in right.get("steps", []))]
    if any(left_data) and any(right_data) and left_data != right_data:
        return 0, ["Dữ liệu kiểm thử khác nhau"]
    left_actions = " ".join(plain_text(step.get("action_doc", {})) for step in left.get("steps", []))
    right_actions = " ".join(plain_text(step.get("action_doc", {})) for step in right.get("steps", []))
    left_values = set(re.findall(r"\d+(?:[.,]\d+)?", left_actions))
    right_values = set(re.findall(r"\d+(?:[.,]\d+)?", right_actions))
    if left_values and right_values and left_values != right_values:
        return 0, ["Giá trị đầu vào khác nhau"]
    left_outcome = " ".join(" ".join([
        *(plain_text(step.get("expected_doc", {})) for step in left.get("steps", [])),
        plain_text(left.get("expected_result_doc", {})),
    ]).lower().split())
    right_outcome = " ".join(" ".join([
        *(plain_text(step.get("expected_doc", {})) for step in right.get("steps", [])),
        plain_text(right.get("expected_result_doc", {})),
    ]).lower().split())
    if not left_outcome or not right_outcome or left_outcome != right_outcome:
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
