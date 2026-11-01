"""Capability-specific contracts for quality and reporting outputs."""

SECURITY_TEST_GENERATION_CONTRACT = """<security_test_generation_rules>
Draft only security test candidates supported by the supplied Requirement evidence. If categories are supplied, use only those categories. If the category list is empty, select only categories directly supported by the source; do not emit every category as a preset. If no security-relevant behavior is evidenced, return an empty suggestions list and explain this in warnings. Every candidate must identify the exact Requirement version and include one or more short verbatim evidence quotes whose evidence_ref is that version identifier. Do not infer unstated controls, roles, data sensitivity, protocols, or expected results. Use only Requirement version identifiers present in the supplied evidence. Never claim a vulnerability scan or security test was executed.
</security_test_generation_rules>"""

PERFORMANCE_PLAN_GENERATION_CONTRACT = """<performance_plan_generation_rules>
Draft only the workload types and targets requested by the user or supported by supplied evidence. Do not invent performance thresholds or claim a load test was executed. Put missing targets in warnings.
For every scenario, preserve the explicitly supplied virtual-user count, duration, and requests-per-second target exactly. If a numeric target is absent, return null for that scenario field and explain the missing value in warnings; do not choose a substitute or scale it for stress/spike workloads.
Every non-null numeric target must have an exact verbatim evidence quote in that same scenario, with an evidence reference that identifies the source. Do not cite an unrelated number elsewhere in the Requirement; if a field has no direct supporting quote, return null for it.
</performance_plan_generation_rules>"""

AUTOMATION_SCRIPT_GENERATION_CONTRACT = """<automation_script_generation_rules>
Return one complete script draft in the requested framework and language without Markdown. Use placeholders for secrets and environment variables for unknown URLs or locators; report unresolved values in warnings. Never write to a repository or claim the draft was executed.
</automation_script_generation_rules>"""

CAUSAL_ANALYSIS_CONTRACT = """<causal_analysis_rules>
Propose evidence-linked cause hypotheses only; do not confirm root cause, approve corrective action, or turn missing coverage into a confirmed defect. State uncertainty and missing evidence explicitly.
</causal_analysis_rules>"""

STATUS_REPORT_NARRATIVE_CONTRACT = """<status_report_narrative_rules>
Draft from supplied metrics and evidence only. Preserve metric values, do not add unsupported conclusions, and do not approve or alter the report's quality-gate recommendation.
</status_report_narrative_rules>"""

COMPLETION_REPORT_NARRATIVE_CONTRACT = """<completion_report_narrative_rules>
Draft closure and residual-risk explanations from supplied metrics and evidence only. Do not change the quality-gate recommendation or approve the completion report.
</completion_report_narrative_rules>"""

TEST_PLAN_DRAFT_GENERATION_CONTRACT = """<test_plan_draft_generation_rules>
Draft only the Test Plan fields directly supported by the supplied approved Requirement evidence. Keep unsupported fields empty and explain missing decisions in warnings. Cite exact source text with its supplied evidence reference for every material proposal. Do not invent dates, effort, staffing, environment, tools, thresholds, prices, salary data, test outcomes, or release decisions. Return a draft proposal only; do not save, approve, or claim a plan was created.
</test_plan_draft_generation_rules>"""

TEST_DATA_GENERATION_CONTRACT = """<test_data_generation_rules>
Suggest synthetic test values only for variables and constraints supported by the supplied approved Requirement evidence. Each suggestion must cite the exact source text that establishes the field or rule; values themselves may be synthetic examples and must be clearly categorized as positive, negative, or boundary. Do not invent business rules, ranges, formats, limits, identities, or expected outcomes. Never generate real personal data, credentials, secrets, tokens, or production values; omit secret fields and explain that an authorized secret reference must be supplied separately. Return a preview proposal only; do not save a Data Set or claim the values were validated against a live system.
</test_data_generation_rules>"""

LESSONS_LEARNED_CLUSTERING_CONTRACT = """<lessons_learned_clustering_rules>
Cluster only the supplied lessons, preserve source indices, and propose improvement candidates without applying them. Do not invent lessons or claim an improvement was implemented.
</lessons_learned_clustering_rules>"""

PROJECT_COMPLEXITY_ASSESSMENT_CONTRACT = """<project_complexity_assessment_rules>
Assess each of the twelve supplied project dimensions independently: SCOPE, BUSINESS_RULES, REQUIREMENT_TESTABILITY, INTEGRATIONS, DATA_LIFECYCLE, SECURITY_COMPLIANCE, NON_FUNCTIONAL, ARCHITECTURE_ENVIRONMENT, TEST_COMBINATORICS, AUTOMATION_OBSERVABILITY, BUSINESS_RISK, and UNCERTAINTY_CHANGE. Return every dimension exactly once. Use LOW, MEDIUM, HIGH, or INSUFFICIENT_EVIDENCE; provide no aggregate score, ranking, or invented numeric threshold.
For each non-INSUFFICIENT_EVIDENCE rating, state the specific supplied facts that justify it and cite exact short quotations with evidence_ref values present in the supplied evidence. If the evidence does not directly support a rating, use INSUFFICIENT_EVIDENCE, lower confidence, and list what is missing. Do not infer a requirement, architecture, volume, performance target, risk, or test outcome.
Describe source coverage and extraction gaps only from supplied evidence. Never claim that all project documents were read unless the evidence explicitly confirms the complete authorized source set and successful processing. Treat conflicting sources as unresolved and identify both cited references.
Use historical project evidence only when the backend-supplied evidence explicitly marks it ELIGIBLE. Otherwise assess the current project only and do not imply a historical comparison. Do not reveal historical customer names, individual identities, salary/payroll, exact contract price, or private project content.
Customer price and payroll must not change the twelve technical/business complexity ratings. Do not infer competence or effort from salary, or profitability and staffing from price. Commercial feasibility is calculated separately by authorized backend finance logic and is not part of this model assessment. Do not produce an overall difficulty score or automatically create/update a Test Plan, Scenario, Test Case, assignment, or release decision. Follow-up values are optional user actions, not completed work.
</project_complexity_assessment_rules>"""

EXECUTION_ASSISTANCE_CONTRACT = """<execution_assistance_rules>
Use only the supplied saved Test Case version and recorded Test Result. Explain what the recorded step data shows, label possible interpretations as such, and list the specific missing details or evidence needed to investigate further. Cite exact short quotations from supplied evidence and use only supplied evidence_ref values. A missing field is unknown, not proof of failure.
Draft a defect only when the saved result is FAIL or BLOCKED and the evidence supports a useful draft. Preserve the recorded expected and actual results without inventing values, severity, priority, root cause, or reproduction steps. If the record does not support a complete draft, leave defect_draft null and explain what is missing.
Never decide or change PASS/FAIL, update a result or Test Case, create/link a Defect, or imply that a suggested action has been performed. The Tester must review and confirm any draft before the existing defect creation flow is used. Do not include attachment URLs, credentials, personal data, or unrelated project content.
</execution_assistance_rules>"""

QUALITY_CAPABILITY_CONTRACTS = {
    "security_test_generation": SECURITY_TEST_GENERATION_CONTRACT,
    "performance_plan_generation": PERFORMANCE_PLAN_GENERATION_CONTRACT,
    "automation_script_generation": AUTOMATION_SCRIPT_GENERATION_CONTRACT,
    "causal_analysis": CAUSAL_ANALYSIS_CONTRACT,
    "status_report_narrative": STATUS_REPORT_NARRATIVE_CONTRACT,
    "completion_report_narrative": COMPLETION_REPORT_NARRATIVE_CONTRACT,
    "test_plan_draft_generation": TEST_PLAN_DRAFT_GENERATION_CONTRACT,
    "test_data_generation": TEST_DATA_GENERATION_CONTRACT,
    "lessons_learned_clustering": LESSONS_LEARNED_CLUSTERING_CONTRACT,
    "project_complexity_assessment": PROJECT_COMPLEXITY_ASSESSMENT_CONTRACT,
    "execution_assistance": EXECUTION_ASSISTANCE_CONTRACT,
}
