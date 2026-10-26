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

LESSONS_LEARNED_CLUSTERING_CONTRACT = """<lessons_learned_clustering_rules>
Cluster only the supplied lessons, preserve source indices, and propose improvement candidates without applying them. Do not invent lessons or claim an improvement was implemented.
</lessons_learned_clustering_rules>"""

QUALITY_CAPABILITY_CONTRACTS = {
    "security_test_generation": SECURITY_TEST_GENERATION_CONTRACT,
    "performance_plan_generation": PERFORMANCE_PLAN_GENERATION_CONTRACT,
    "automation_script_generation": AUTOMATION_SCRIPT_GENERATION_CONTRACT,
    "causal_analysis": CAUSAL_ANALYSIS_CONTRACT,
    "status_report_narrative": STATUS_REPORT_NARRATIVE_CONTRACT,
    "completion_report_narrative": COMPLETION_REPORT_NARRATIVE_CONTRACT,
    "lessons_learned_clustering": LESSONS_LEARNED_CLUSTERING_CONTRACT,
}
