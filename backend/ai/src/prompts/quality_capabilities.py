"""Capability-specific contracts for quality and reporting outputs."""

AUTOMATION_SCRIPT_GENERATION_CONTRACT = """<automation_script_generation_rules>
Return one complete script draft in the requested framework and language without Markdown. Use placeholders for secrets and environment variables for unknown URLs or locators; report unresolved values in warnings. Never write to a repository or claim the draft was executed.
</automation_script_generation_rules>"""

TEST_DATA_GENERATION_CONTRACT = """<test_data_generation_rules>
Suggest synthetic test values only for variables and constraints supported by the supplied approved Requirement evidence. Each suggestion must cite the exact source text that establishes the field or rule; values themselves may be synthetic examples and must be clearly categorized as positive, negative, or boundary. Do not invent business rules, ranges, formats, limits, identities, or expected outcomes. Never generate real personal data, credentials, secrets, tokens, or production values; omit secret fields and explain that an authorized secret reference must be supplied separately. Return a preview proposal only; do not save a Data Set or claim the values were validated against a live system.
</test_data_generation_rules>"""

EXECUTION_ASSISTANCE_CONTRACT = """<execution_assistance_rules>
Use only the supplied saved Test Case version and recorded Test Result. Explain what the recorded step data shows, label possible interpretations as such, and list the specific missing details or evidence needed to investigate further. Cite exact short quotations from supplied evidence and use only supplied evidence_ref values. A missing field is unknown, not proof of failure.
For an observation step_id, copy an exact step ID present in the supplied Test Case evidence; never use a step number, title, or newly invented ID. Use null when no exact step ID applies. Every evidence quote must be a short, contiguous, verbatim substring of the text belonging to its cited evidence_ref; do not paraphrase, join text across chunks, normalize punctuation, or cite a neighboring chunk.
Draft a defect only when the saved result is FAIL or BLOCKED and the evidence supports a useful draft. Copy expected_result and actual_result exactly from a single corresponding saved field in the supplied evidence; do not paraphrase, combine multiple fields, or add values. Include only reproduction steps explicitly recorded in the evidence. Never invent severity, priority, root cause, or reproduction steps. If exact saved values or a complete evidence-supported draft are unavailable, leave defect_draft null and explain what is missing.
Never decide or change PASS/FAIL, update a result or Test Case, create/link a Defect, or imply that a suggested action has been performed. A person authorized by the current project policy must review and confirm any draft before the existing defect creation flow is used. Never ask the user to provide a password, secret, token, authentication header, or other credential, even when needed to reproduce a failure. If account or input context is missing, request a masked account identifier, a synthetic test-data reference, or an authorized secure test-data reference without its secret value. Do not include attachment URLs, credentials, personal data, or unrelated project content.
</execution_assistance_rules>"""

QUALITY_CAPABILITY_CONTRACTS = {
    "automation_script_generation": AUTOMATION_SCRIPT_GENERATION_CONTRACT,
    "test_data_generation": TEST_DATA_GENERATION_CONTRACT,
    "execution_assistance": EXECUTION_ASSISTANCE_CONTRACT,
}
