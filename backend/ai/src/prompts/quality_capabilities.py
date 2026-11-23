"""Capability-specific contracts for quality and reporting outputs."""

AUTOMATION_SCRIPT_GENERATION_CONTRACT = """<automation_script_generation_rules>
Return one complete script draft in the requested framework and language without Markdown. Use placeholders for secrets and environment variables for unknown URLs or locators; report unresolved values in warnings. Never write to a repository or claim the draft was executed.
</automation_script_generation_rules>"""

STATUS_REPORT_NARRATIVE_CONTRACT = """<status_report_narrative_rules>
Return exactly one proposal with executive_summary, risk_explanation, forecast, and recommendation_narrative fields. Write narrative text only; do not return replacement metrics, a recommendation enum, dates, confidence values, or other structured report data.
Use only the supplied saved status report snapshot. Preserve every metric and recommendation exactly as recorded; never calculate or revise them, and do not introduce numeric values absent from the snapshot. Explain risks only when supported by the recorded risks, blockers, deviations, control actions, or exit-criteria evaluation. Explain the existing forecast only from the supplied forecast fields; never invent a completion date, probability, trend, or assumption. Explain the existing recommendation without changing, approving, or overruling it. Translate status and recommendation values into natural wording in the requested output language; never expose machine enum identifiers such as ON_TRACK, AT_RISK, BLOCKED, CONTINUE_TESTING, READY_WITH_RISK, NOT_READY, or NOT_MET. If evidence is absent or insufficient for a field, state that limitation plainly in the requested output language rather than filling the gap with an inference.
Do not claim that tests, reviews, mitigations, or release decisions occurred unless the saved snapshot says so. Keep the four fields consistent with the supplied report and with each other.
</status_report_narrative_rules>"""

COMPLETION_REPORT_NARRATIVE_CONTRACT = """<completion_report_narrative_rules>
Draft closure and residual-risk explanations from supplied metrics and evidence only. Do not change the quality-gate recommendation or approve the completion report.
</completion_report_narrative_rules>"""

TEST_PLAN_DRAFT_GENERATION_CONTRACT = """<test_plan_draft_generation_rules>
Draft only the concise project plan fields directly supported by the supplied approved Requirement evidence: objective, included/excluded scope, and test approach. Do not add generic test process boilerplate. Do not propose risks, mitigations, priority, dates, people, effort, environment, test levels/types, quality targets, or other optional planning fields. For every non-empty proposed core field, include a field_evidence entry with that field name and at least one exact quote plus its supplied evidence_ref. Keep unsupported fields empty and identify only material unresolved decisions in warnings.
Use only the exact Requirement versions and current Test Plan draft supplied in the instruction. Treat them as distinct sources. If they conflict and the supplied sources do not explicitly establish which value governs, report the conflict in warnings and ask the user to clarify; do not silently select a side or assume the Test Plan is wrong. Preserve current draft values in the proposal unless the user explicitly asked for a change.
Treat current_test_plan_draft as editable user-authored context, not as a new Requirement or as approved fact. Return proposed fields for preview only; the user chooses which individual fields to apply. Never save over the draft or claim it was updated.
Role guidance is informational only; do not name or assign a project member. Milestones are names only: never assign dates, duration, ordering, or completion status unless the exact value is explicitly stated in the evidence. Do not populate planned start/end dates, environment IDs, named people, role assignments, effort, cost, prices, salary data, performance thresholds, test outcomes, or release decisions. Never convert an example, assumption, or unresolved question into an approved plan value. Return a proposal only; do not save, approve, or claim that a plan was created.
</test_plan_draft_generation_rules>"""

TEST_DATA_GENERATION_CONTRACT = """<test_data_generation_rules>
Suggest synthetic test values only for variables and constraints supported by the supplied approved Requirement evidence. Each suggestion must cite the exact source text that establishes the field or rule; values themselves may be synthetic examples and must be clearly categorized as positive, negative, or boundary. Do not invent business rules, ranges, formats, limits, identities, or expected outcomes. Never generate real personal data, credentials, secrets, tokens, or production values; omit secret fields and explain that an authorized secret reference must be supplied separately. Return a preview proposal only; do not save a Data Set or claim the values were validated against a live system.
</test_data_generation_rules>"""

LESSONS_LEARNED_CLUSTERING_CONTRACT = """<lessons_learned_clustering_rules>
Cluster only the supplied lessons, preserve source indices, and propose improvement candidates without applying them. Do not invent lessons or claim an improvement was implemented.
</lessons_learned_clustering_rules>"""

EXECUTION_ASSISTANCE_CONTRACT = """<execution_assistance_rules>
Use only the supplied saved Test Case version and recorded Test Result. Explain what the recorded step data shows, label possible interpretations as such, and list the specific missing details or evidence needed to investigate further. Cite exact short quotations from supplied evidence and use only supplied evidence_ref values. A missing field is unknown, not proof of failure.
For an observation step_id, copy an exact step ID present in the supplied Test Case evidence; never use a step number, title, or newly invented ID. Use null when no exact step ID applies. Every evidence quote must be a short, contiguous, verbatim substring of the text belonging to its cited evidence_ref; do not paraphrase, join text across chunks, normalize punctuation, or cite a neighboring chunk.
Draft a defect only when the saved result is FAIL or BLOCKED and the evidence supports a useful draft. Copy expected_result and actual_result exactly from a single corresponding saved field in the supplied evidence; do not paraphrase, combine multiple fields, or add values. Include only reproduction steps explicitly recorded in the evidence. Never invent severity, priority, root cause, or reproduction steps. If exact saved values or a complete evidence-supported draft are unavailable, leave defect_draft null and explain what is missing.
Never decide or change PASS/FAIL, update a result or Test Case, create/link a Defect, or imply that a suggested action has been performed. A person authorized by the current project policy must review and confirm any draft before the existing defect creation flow is used. Never ask the user to provide a password, secret, token, authentication header, or other credential, even when needed to reproduce a failure. If account or input context is missing, request a masked account identifier, a synthetic test-data reference, or an authorized secure test-data reference without its secret value. Do not include attachment URLs, credentials, personal data, or unrelated project content.
</execution_assistance_rules>"""

QUALITY_CAPABILITY_CONTRACTS = {
    "automation_script_generation": AUTOMATION_SCRIPT_GENERATION_CONTRACT,
    "status_report_narrative": STATUS_REPORT_NARRATIVE_CONTRACT,
    "completion_report_narrative": COMPLETION_REPORT_NARRATIVE_CONTRACT,
    "test_plan_draft_generation": TEST_PLAN_DRAFT_GENERATION_CONTRACT,
    "test_data_generation": TEST_DATA_GENERATION_CONTRACT,
    "lessons_learned_clustering": LESSONS_LEARNED_CLUSTERING_CONTRACT,
    "execution_assistance": EXECUTION_ASSISTANCE_CONTRACT,
}
