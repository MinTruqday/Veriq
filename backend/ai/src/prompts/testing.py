import hashlib
import json
from typing import get_args

from pydantic import BaseModel

from src.prompts.change_simulation import IMPACT_ANALYSIS_CONTRACT
from src.prompts.model_output import schema_instruction
from src.prompts.project_assistance import PROJECT_QUESTION_CONTRACT
from src.prompts.project_completeness import PROJECT_COMPLETENESS_CONTRACT
from src.prompts.prompt_data import prompt_json
from src.prompts.quality_capabilities import QUALITY_CAPABILITY_CONTRACTS
from src.prompts.requirement_analysis import requirement_quality_analysis_instruction
from src.prompts.requirement_templates import (
    REQUIREMENT_TEMPLATE_REVIEW_INSTRUCTIONS,
    REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS,
)
from src.prompts.test_case_grounding import build_generated_cases_grounding_prompt
from src.prompts.test_design import TEST_DESIGN_CAPABILITY_CONTRACTS
from src.prompts.testability_benchmark import CLARIFICATION_BASELINE
from src.prompts.testability_blueprint import (
    TESTABILITY_BLUEPRINT_COMPILATION,
    TESTABILITY_BLUEPRINT_SELF_REVIEW,
)
from src.prompts.testability_blueprint_review import build_testability_blueprint_grounding_prompt
from src.prompts.testing_contract import STRUCTURED_TESTING_TEMPLATE
from src.prompts.work_reporting import WORK_REPORT_NARRATIVE_CONTRACT
from src.schemas.inference_requirements import TestabilityBlueprintGroundingReview


def _capability_contracts():
    return {
        "project_completeness_review": PROJECT_COMPLETENESS_CONTRACT,
        "work_report_narrative": WORK_REPORT_NARRATIVE_CONTRACT,
        "requirement_quality_analysis": requirement_quality_analysis_instruction(),
        "requirement_template_synthesis": REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS,
        "requirement_template_review": REQUIREMENT_TEMPLATE_REVIEW_INSTRUCTIONS,
        "testability_blueprint_compilation": TESTABILITY_BLUEPRINT_COMPILATION,
        "testability_blueprint_self_review": TESTABILITY_BLUEPRINT_SELF_REVIEW,
        "clarification_baseline": CLARIFICATION_BASELINE,
        "impact_analysis": IMPACT_ANALYSIS_CONTRACT,
        "change_simulation_report": IMPACT_ANALYSIS_CONTRACT,
        "project_question": PROJECT_QUESTION_CONTRACT,
        **TEST_DESIGN_CAPABILITY_CONTRACTS,
        **QUALITY_CAPABILITY_CONTRACTS,
    }


def _all_model_subclasses(model_type):
    pending = list(model_type.__subclasses__())
    discovered = set()
    while pending:
        schema = pending.pop()
        if schema in discovered:
            continue
        discovered.add(schema)
        pending.extend(schema.__subclasses__())
    return discovered


def validate_prompt_contract_registry():
    schema_capabilities = set()
    for schema in _all_model_subclasses(BaseModel):
        if (
            not schema.__module__.startswith("src.schemas.inference_")
            or not schema.__name__.endswith("Output")
        ):
            continue
        field = schema.model_fields.get("capability")
        if field:
            schema_capabilities.update(
                value for value in get_args(field.annotation) if isinstance(value, str)
            )
    contracts = _capability_contracts()
    missing = schema_capabilities.difference(contracts)
    stale = set(contracts).difference(schema_capabilities)
    invalid = {
        capability
        for capability, contract in contracts.items()
        if not isinstance(contract, str) or not contract.strip()
    }
    if missing or stale or invalid:
        raise ValueError(
            "testing_prompt_contract_registry_invalid:"
            + ",".join(
                [
                    *(f"missing={value}" for value in sorted(missing)),
                    *(f"stale={value}" for value in sorted(stale)),
                    *(f"empty={value}" for value in sorted(invalid)),
                ]
            )
        )
    return tuple(sorted(schema_capabilities))


def prompt_contract_fingerprint(capability, schema):
    contract = _capability_contracts().get(capability)
    if not contract:
        raise ValueError("testing_capability_prompt_contract_missing")
    schema_value = schema.model_json_schema() if hasattr(schema, "model_json_schema") else schema
    contract_parts = [
        STRUCTURED_TESTING_TEMPLATE,
        capability,
        contract,
        schema_instruction(schema_value),
    ]
    if capability == "test_generation":
        contract_parts.append(build_generated_cases_grounding_prompt([], []))
    if capability == "testability_blueprint_compilation":
        contract_parts.append(build_testability_blueprint_grounding_prompt([], [], []))
        contract_parts.append(schema_instruction(TestabilityBlueprintGroundingReview.model_json_schema()))
    canonical = json.dumps(
        contract_parts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def prompt_messages_fingerprint(messages):
    canonical = json.dumps(
        messages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def build_testing_prompt(
    capability, project_id, instruction, evidence, evidence_refs, schema, output_language=None
):
    prompt = STRUCTURED_TESTING_TEMPLATE.format(
        capability=prompt_json(capability),
        project_id=prompt_json(project_id),
        output_language=prompt_json(output_language),
        instruction=prompt_json(instruction),
        evidence_refs=prompt_json(evidence_refs),
        evidence=prompt_json(evidence),
    )
    contract = _capability_contracts().get(capability)
    if not contract:
        raise ValueError("testing_capability_prompt_contract_missing")
    return f"{prompt}\n<capability_contract>{contract}</capability_contract>"
