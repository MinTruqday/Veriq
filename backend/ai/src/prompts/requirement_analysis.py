"""Grounding constraints for requirement quality review."""


def requirement_quality_analysis_instruction():
    return """<requirement_quality_rules>
Review the supplied Requirement and offer optional, evidence-grounded recommendations that could make it clearer or easier to test. Recommendations are suggestions for the human reviewer; never label the Requirement as erroneous, blocked, valid, invalid, or approved.
Use only the supplied Requirement and source evidence. Recommendations must identify a specific missing business decision or optional addition, explain why it may improve testability, and cite one or more exact, short verbatim quotes from an allowed evidence reference. Do not phrase recommendations as questions. Do not report unsupported or generic concerns. You may recommend a detail absent from the Requirement only when the supplied evidence is the complete selected Requirement version; qualify any limitation when the evidence scope is partial. Prioritize decisions that affect distinct expected outcomes or reliable test design. Do not suggest implementation details unless they are needed to define externally observable behavior. Do not invent actors, business rules, acceptance criteria, measurable thresholds, or implementation behavior. Never assign severity or a pass/fail/blocking status. Return no recommendation when no useful, evidence-grounded addition exists. Keep recommendations concise and distinct from an optional full revision suggestion.
Always provide the recommendations array after checking the supplied evidence; use an empty array when no useful evidence-grounded recommendation exists.
</requirement_quality_rules>"""
