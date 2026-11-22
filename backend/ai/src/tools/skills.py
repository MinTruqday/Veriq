import json
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool

from src.schemas.agent import TestingSkillInput
from src.schemas.inference_requests import (
    TESTING_EVIDENCE_TEXT_MAX_LENGTH,
    TestingCapabilityRequest,
)
from src.services.ai_capabilities import generate_ai_capability


def _compact_evidence_value(value: Any, string_limit: int, list_limit: int):
    if isinstance(value, str):
        return value if len(value) <= string_limit else f"{value[:string_limit]}…"
    if isinstance(value, list):
        items = [
            _compact_evidence_value(item, string_limit, list_limit)
            for item in value[:list_limit]
        ]
        return (
            {"items": items, "omitted_count": len(value) - len(items)}
            if len(value) > list_limit
            else items
        )
    if isinstance(value, dict):
        return {
            key: _compact_evidence_value(item, string_limit, list_limit)
            for key, item in value.items()
        }
    return value


def _bounded_evidence(evidence):
    bounded = []
    compacted_prefix = "[COMPACTED FOR REQUEST SIZE; OMITTED CONTENT IS NOT EVIDENCE]\n"
    truncated_suffix = "\n[TRUNCATED FOR REQUEST SIZE; OMITTED CONTENT IS NOT EVIDENCE]"
    for item in evidence:
        value = item.model_dump(mode="python") if hasattr(item, "model_dump") else dict(item)
        text = str(value.get("text") or "")
        if len(text) > TESTING_EVIDENCE_TEXT_MAX_LENGTH:
            try:
                parsed = json.loads(text)
            except (TypeError, json.JSONDecodeError):
                value["text"] = (
                    text[: TESTING_EVIDENCE_TEXT_MAX_LENGTH - len(truncated_suffix)]
                    + truncated_suffix
                )
            else:
                compacted = None
                for string_limit, list_limit in ((300, 3), (150, 2), (80, 1)):
                    candidate = compacted_prefix + json.dumps(
                        _compact_evidence_value(parsed, string_limit, list_limit),
                        ensure_ascii=False,
                        separators=(",", ":"),
                        default=str,
                    )
                    if len(candidate) <= TESTING_EVIDENCE_TEXT_MAX_LENGTH:
                        compacted = candidate
                        break
                value["text"] = compacted or (
                    compacted_prefix
                    + text[
                        : TESTING_EVIDENCE_TEXT_MAX_LENGTH
                        - len(compacted_prefix)
                        - len(truncated_suffix)
                    ]
                    + truncated_suffix
                )
        bounded.append(value)
    return bounded


async def execute_skill(capability, project_id, instruction, config):
    configurable = (config or {}).get("configurable", {})
    evidence = configurable.get("evidence", [])
    if not evidence:
        return json.dumps(
            {
                "status": "INSUFFICIENT_EVIDENCE",
                "capability": capability,
                "reason_codes": ["INSUFFICIENT_EVIDENCE"],
            }
        )
    if capability == "completion_report_narrative" and not any(
        getattr(item, "artifact_type", None) == "test_completion_report"
        or isinstance(item, dict)
        and item.get("artifact_type") == "test_completion_report"
        for item in evidence
    ):
        return json.dumps(
            {
                "status": "INSUFFICIENT_EVIDENCE",
                "capability": capability,
                "reason_codes": ["COMPLETION_REPORT_EVIDENCE_REQUIRED"],
            }
        )
    result = await generate_ai_capability(
        TestingCapabilityRequest(
            capability=capability,
            project_id=project_id,
            instruction=instruction,
            output_language=configurable.get("output_language"),
            evidence=_bounded_evidence(evidence),
        )
    )
    return result.model_dump_json()


def testing_skill(capability, description, domains, permission, label=None, user_selectable=False):
    async def invoke(project_id: str, instruction: str = "", config: RunnableConfig = None):
        return await execute_skill(capability, project_id, instruction, config)

    value = StructuredTool.from_function(
        coroutine=invoke, name=capability, description=description, args_schema=TestingSkillInput
    )
    value.metadata = {
        "domains": domains,
        "owner_domain": domains[0] if len(domains) == 1 else None,
        "action": "PROPOSE",
        "permission": permission,
        "verification": None,
        "label": label or capability,
        "user_selectable": user_selectable,
    }
    return value


agent_capabilities = [
    testing_skill(
        "project_question",
        "Answer a project question only from retrieved evidence",
        ["reporting"],
        "ai.ask_project",
        "Hỏi đáp dự án",
        True,
    ),
    testing_skill(
        "requirement_template_synthesis",
        "Draft a Requirements template from permitted evidence",
        ["requirement"],
        "requirement.create",
    ),
    testing_skill(
        "requirement_template_review",
        "Review a Requirements template without changing it",
        ["requirement"],
        "requirement.read",
    ),
    testing_skill(
        "scenario_generation",
        "Generate structured test scenarios from evidence",
        ["test_design"],
        "ai.generate_scenario",
    ),
    testing_skill(
        "test_generation",
        "Generate structured test cases from evidence",
        ["test_design"],
        "ai.generate_testcase",
        "Sinh ca kiểm thử",
        True,
    ),
    testing_skill(
        "technique_recommendation",
        "Recommend evidence grounded test design techniques without creating tests",
        ["test_design"],
        "ai.generate_testcase",
    ),
    testing_skill(
        "impact_analysis",
        "Classify change impact from evidence",
        ["analysis"],
        "ai.run_impact",
        "Phân tích ảnh hưởng",
        True,
    ),
    testing_skill(
        "automation_script_generation",
        "Generate an automation script draft",
        ["execution"],
        "ai.generate_automation_script",
    ),
    testing_skill(
        "test_condition_generation",
        "Generate structured test conditions",
        ["test_design"],
        "testanalysis.run_ai",
    ),
    testing_skill(
        "completion_report_narrative",
        "Draft an evidence grounded completion report",
        ["reporting"],
        "testcompletion.update",
        "Báo cáo hoàn tất",
    ),
    testing_skill(
        "lessons_learned_clustering",
        "Cluster lessons learned from evidence",
        ["reporting"],
        "testcompletion.update",
    ),
]
