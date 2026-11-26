REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS = """<requirement_template_rules>
Draft Requirement suggestions only; never create Test Cases or claim import.
When a project Requirement template is supplied, follow its field meaning and structure. Otherwise use the Requirement output schema. Do not add fields or replace the project's format with a generic User Story. Separate project context from Requirements and fill context only from evidence. Use User Story fields only when the source itself is a User Story.
Use only cited evidence; return an exact source_quotes entry for each cited document. Extract every supported entry from sections, lists, tables, and labeled fields; preserve each criterion and rule separately with its source identifier. For each independently verifiable behavior or constraint stated in a Requirement, include an acceptance_criteria entry even when the source does not label it as an acceptance criterion. Copy the complete criterion as a contiguous verbatim source excerpt; do not paraphrase, combine separate criteria, or add inferred conditions. Preserve unrelated grounded Requirements when one lacks sufficient evidence. Do not create one Requirement per sentence unless each sentence states a separately verifiable behavior or constraint; do not turn every API operation into a Requirement or cite a template. For OpenAPI/Postman, link only relevant operations with exact source reference, method, and path/URL. Never invent behavior, IDs, paths, methods, response codes, limits, or expected results. Copy an assigned Requirement ID unchanged; otherwise leave it empty. Keep all fields in one Requirement; never use a field label as its title.
Report duplicates and contradictions without resolving them. Mark applicable omissions; leave unsupported optional fields empty.
</requirement_template_rules>"""


REQUIREMENT_TEMPLATE_REVIEW_INSTRUCTIONS = """<requirement_template_review_rules>
Assess whether the supplied Requirement template can be imported without changing it.
Report missing information only when permitted evidence proves both conditions:
it applies to a specific Requirement, and its absence blocks import.
Do not treat information absent from the source as automatically required.
Do not require data rules, dependencies, quality measures, or User Story fields
only because the schema supports them.
Distinguish missing applicable information from information that does not apply.
Identify source contradictions and unsupported assumptions without choosing a winner.
Do not invent fields, Requirements, acceptance criteria, response codes, or quality limits.
Do not generate Test Cases, modify the template, or approve import.
A batch is not the complete source set unless explicitly stated.
Do not declare the whole template ready from a partial batch.
Every finding must cite permitted evidence references.
Copy a suggested source quote exactly from a cited permitted source document.
Do not use template content as evidence for claims about source documents.
</requirement_template_review_rules>"""


def requirement_document_synthesis_instruction():
    return REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS
