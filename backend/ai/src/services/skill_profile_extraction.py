import re
import unicodedata

from fastapi import HTTPException

from src.core.security.guardrails import guardrails_engine
from src.prompts.skill_profile import build_skill_profile_extraction_prompt
from src.schemas.inference_skill_profile import (
    ExtractedExperienceCandidate,
    ExtractedSkillCandidate,
    SkillProfileExtractionOutput,
    SkillProfileExtractionRequest,
)
from src.services.inference import structured


def _normalized_claim_is_present(claim: str, evidence: str) -> bool:
    normalized_claim = " ".join(unicodedata.normalize("NFC", claim).casefold().split())
    normalized_evidence = " ".join(unicodedata.normalize("NFC", evidence).casefold().split())
    if not normalized_claim:
        return True
    pattern = rf"(?<!\w){re.escape(normalized_claim)}(?!\w)"
    return re.search(pattern, normalized_evidence, flags=re.UNICODE) is not None


async def extract_skill_profile_candidates(
    request: SkillProfileExtractionRequest,
) -> SkillProfileExtractionOutput:
    source_blocks = [item.model_dump() for item in request.source_blocks]
    total_characters = sum(len(item["text"]) for item in source_blocks)
    if total_characters > 100_000:
        raise HTTPException(status_code=413, detail={"code": "CV_TEXT_LIMIT_EXCEEDED"})

    inspection = await guardrails_engine.async_inspect_input(
        "\n".join(item["text"] for item in source_blocks)
    )
    if not inspection.get("is_safe", False):
        raise HTTPException(status_code=422, detail={"code": "CV_CONTENT_UNSAFE"})

    output = await structured(
        build_skill_profile_extraction_prompt(source_blocks),
        SkillProfileExtractionOutput,
        max_tokens=5000,
        timeout_seconds=120,
        provider_schema=False,
    )
    block_by_id = {item["block_id"]: item for item in source_blocks}
    for candidate in [*output.skills, *output.experiences]:
        source = block_by_id.get(candidate.source_block_id)
        if not source or candidate.evidence_quote not in source["text"]:
            raise HTTPException(status_code=422, detail={"code": "CV_EVIDENCE_NOT_FOUND"})
        if candidate.page_no != source["page_no"]:
            raise HTTPException(status_code=422, detail={"code": "CV_PAGE_REFERENCE_MISMATCH"})
        claims = (
            [candidate.name]
            if isinstance(candidate, ExtractedSkillCandidate)
            else [
                candidate.title,
                candidate.domain,
                *candidate.technologies,
                candidate.responsibilities,
            ]
        )
        if any(
            not _normalized_claim_is_present(claim, candidate.evidence_quote)
            for claim in claims
            if claim.strip()
        ):
            raise HTTPException(status_code=422, detail={"code": "CV_CLAIM_NOT_GROUNDED"})

    return output
