REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS = """Draft Requirements only
The template must distinguish project context from individual requirements
Use User Story fields only when the source is a User Story
Do not turn every API operation into a requirement
When a requirement is derived from OpenAPI or Postman link only its relevant operations in api_operations using their exact source_ref and method plus path or url_template from the cited document
Do not invent operation identifiers paths methods or response codes
For each cited document reference return an exact quote in source_quotes keyed by that evidence reference
Copy extracted actors rules dependencies and acceptance criteria only when their wording is present in the cited evidence
Fill User Story actor goal and value only from a User Story source
Do not add source_quotes for template references
List duplicate or contradictory source claims in conflicts without choosing a winner
Mark applicable but absent details in missing_sections
Do not invent actors acceptance criteria response codes performance targets or external facts
Do not generate test cases or claim that the draft has been imported"""
