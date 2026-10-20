import json

from src.prompts.requirement_templates import REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS
from src.prompts.testing_contract import STRUCTURED_TESTING_TEMPLATE


def build_testing_prompt(capability, project_id, instruction, evidence, evidence_refs, schema):
    prompt = STRUCTURED_TESTING_TEMPLATE.format(
        capability=capability,
        project_id=project_id,
        instruction=json.dumps(instruction, ensure_ascii=False),
        evidence_refs=json.dumps(evidence_refs, ensure_ascii=False),
        evidence=evidence,
    )
    contract = (schema.__doc__ or "").strip()
    if capability == "requirement_template_synthesis":
        contract = f"{contract}\n{REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS}"
    return f"{prompt}\n<capability_contract>{contract}</capability_contract>" if contract else prompt
