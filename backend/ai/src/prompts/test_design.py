"""Capability-specific contracts for AI-assisted test design."""


TEST_CASE_GENERATION_CONTRACT = """<test_case_generation_rules>
When categories are supplied, return exactly the requested count for each category. When selected techniques are supplied without categories, generate only evidence-supported cases up to the requested maximum and label only techniques each case actually demonstrates.
When the instruction includes an approved upstream Test Plan or Scenario, use it to check coverage and consistency. Requirement evidence remains authoritative. Report concrete conflicts in warnings, and do not silently resolve a conflict or turn upstream suggestions into new business rules.
Every case must contain a concrete input, a verifiable outcome, a source reference, and an exact contiguous quotation that directly supports the behavior. Use only acceptance-criterion identifiers present in the supplied evidence.
When the instruction supplies the active project's risk and priority levels, assign each case only a listed level when the supplied evidence supports the assessment; otherwise use "unassessed". Never invent a level or use defect-severity levels as risk levels. When no project levels are supplied, use "unassessed".
Only describe alternate or exception flows supported by the cited source. Leave them empty if absent. A branch requiring its own execution result should be a separate case.
For a step with no separate test data, use an empty object for its test_data field.
Derive equivalence classes, boundaries, decision rules, states, and error hypotheses only from evidence. A successful flow does not establish undocumented failure behavior. If a technique needs an undocumented prerequisite, omit it and name the missing information in warnings. Use interface-neutral actions when the source does not identify an interface.
Do not invent values, behavior, generic templates, messages, limits, or implementation details. Do not create a separate duplicate case for each technique when one case's same steps, input, and expected result genuinely demonstrate multiple techniques.
</test_case_generation_rules>"""


TECHNIQUE_RECOMMENDATION_CONTRACT = """<technique_recommendation_rules>
Assess each supplied test-design technique against the cited Requirement evidence and existing coverage. Only evidence explicitly typed as an existing Test Case counts as active coverage; drafts are not active coverage.
Recommend a technique only when the source defines enough input classes, rules, boundaries, or states to apply it concretely. Otherwise mark it possible, insufficient_evidence, or not_applicable and state the missing prerequisite. Expected and incremental coverage must remain source-supported. Do not assume empty input, unchanged data, extra states, reverse transitions, numeric limits, or defect history.
This capability must never create or save Test Cases.
</technique_recommendation_rules>"""


AUTOMATED_TECHNIQUE_RECOMMENDATION_INSTRUCTION = "Recommend test-design techniques supported by the normalized Requirement and current test scope. Include only evidence-based recommendations; do not create or save Test Cases."


TEST_CONDITION_GENERATION_CONTRACT = """<test_condition_generation_rules>
Generate evidence-grounded condition candidates with concrete titles, descriptions, coverage items, test levels, test types, risk, priority, candidate techniques, and testability status. Use risk and priority terms stated by the user or project evidence; do not force a fixed vocabulary. Give each condition a concise category that describes the evidence-supported behavior. Do not force a preset category list. If a category cannot be grounded, return a warning rather than inventing behavior or limits.
For every candidate, include one or more exact contiguous evidence quotes and the corresponding evidence references from the supplied sources; a candidate without a verifiable quote is invalid. Use only cited evidence references and distinguish an untestable condition from a condition whose needed information is missing. Do not create executable Test Cases in this capability.
</test_condition_generation_rules>"""


TEST_DESIGN_CAPABILITY_CONTRACTS = {
    "scenario_generation": TEST_CASE_GENERATION_CONTRACT,
    "test_generation": TEST_CASE_GENERATION_CONTRACT,
    "technique_recommendation": TECHNIQUE_RECOMMENDATION_CONTRACT,
    "test_condition_generation": TEST_CONDITION_GENERATION_CONTRACT,
}
