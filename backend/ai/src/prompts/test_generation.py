"""Structured instructions for source-grounded Test Case generation."""

def _render_generation_instruction(task, coverage_rules):
    sections = [
        "<generation_task>" + task + "</generation_task>",
        "<project_format_rules>Return only fields supported by Veriq's active Test Case generation schema. Preserve its structure: title, objective, preconditions, steps with step-level test data, expected result, supported alternate and exception flows, acceptance-criterion links, and evidence. Do not add fields, replace the project format with a generic template, or duplicate test data or expected results in extra fields. Leave optional values empty when the Requirement does not support them.</project_format_rules>",
        "<evidence_rules>Use only behavior stated in the selected Requirement version and its cited acceptance criteria, business rules, and applicable evidence. Acceptance criteria are optional: when none are supplied, derive cases only from behavior explicitly stated in the Requirement content and cite the exact Requirement version as the basis. State the documented, observable outcome directly and preserve its meaning. A user action explicitly described by a criterion, such as entering the value that the criterion validates, is supported test input; do not reject it merely because the source does not separately specify a screen control for that action. Do not add inferred intermediate behavior, implementation details, UI destinations, messages, status codes, limits, or test data absent from the source. Reuse the documented outcome in expected results where possible. When no concrete value is documented, keep input at the source's semantic level instead of inventing a value. Leave priority and risk unassessed; never inherit these assessments from a Requirement.</evidence_rules>",
        "<technique_selection_rules>When the request does not prescribe techniques, independently choose only the applicable techniques from equivalence_partitioning, boundary_value, decision_table, state_transition, and error_guessing. Select one or more only when the source evidence supports their use; do not attach all techniques by default. Leave techniques empty when the source does not support a defensible selection. The selected techniques must be reflected by the case's actual inputs, steps, and expected outcome; do not claim a technique that the case does not implement.</technique_selection_rules>",
        "<coverage_rules>" + coverage_rules + "</coverage_rules>",
    ]
    return "\n\n".join(sections)


def requirement_test_generation_instruction():
    return _render_generation_instruction(
        "Generate concrete Test Cases from the selected Requirement content, optional acceptance criteria, and cited sources.",
        "Create cases only for source-supported behavior. If acceptance criteria are absent, cite the Requirement content/version as the basis. Avoid duplicates and retain links to the exact Requirement version and any selected acceptance criteria.",
    )


def focused_requirement_test_generation_instruction():
    return _render_generation_instruction(
        "Generate Test Cases only for the selected uncovered acceptance criteria.",
        "Do not repeat behavior already covered by existing Test Cases. Retain the link to the exact Requirement version and selected acceptance criteria.",
    )


def retry_grounded_requirement_test_generation_instruction():
    return _render_generation_instruction(
        "Regenerate the rejected preview from scratch for the selected Requirement evidence.",
        "Remove every claim not supported by the Requirement or cited acceptance criteria. Keep expected results at the documented final outcome; do not infer intermediate behavior. Return no case for a gap the source cannot support. Avoid duplicates and preserve exact Requirement and acceptance-criteria links.",
    )
