import json

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool

from src.schemas.agent import TestingSkillInput
from src.schemas.inference_requests import TestingAutomationRequest
from src.services.ai_automation import generate_ai_automation


async def execute_skill(capability, project_id, instruction, config):
    evidence = (config or {}).get("configurable", {}).get("evidence", [])
    if not evidence:
        return json.dumps(
            {
                "status": "INSUFFICIENT_EVIDENCE",
                "capability": capability,
                "reason_codes": ["INSUFFICIENT_EVIDENCE"],
            }
        )
    result = await generate_ai_automation(
        TestingAutomationRequest(
            capability=capability, project_id=project_id, instruction=instruction, evidence=evidence
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


structured_skills = [
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
        "security_test_generation",
        "Generate security test candidates",
        ["test_design"],
        "ai.generate_security_tests",
    ),
    testing_skill(
        "performance_plan_generation",
        "Generate performance test plan candidates",
        ["test_design"],
        "ai.generate_performance_plan",
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
        "causal_analysis",
        "Generate evidence grounded causal hypotheses",
        ["analysis"],
        "causalanalysis.update",
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
