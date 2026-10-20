"""Compose the shared test-generation contract from its owning prompt modules."""

from src.prompts.testing_analysis import TESTING_ANALYSIS_PROTOCOL
from src.prompts.testing_evidence import TESTING_EVIDENCE_CONTRACT
from src.prompts.testing_examples import TESTING_FEW_SHOT_EXAMPLES
from src.prompts.testing_governance import TESTING_GOVERNANCE
from src.prompts.testing_identity import TESTING_IDENTITY
from src.prompts.testing_language import TESTING_LANGUAGE_POLICY

STRUCTURED_TESTING_TEMPLATE = "\n\n".join(
    (
        TESTING_IDENTITY,
        TESTING_ANALYSIS_PROTOCOL,
        TESTING_LANGUAGE_POLICY,
        TESTING_EVIDENCE_CONTRACT,
        TESTING_GOVERNANCE,
        TESTING_FEW_SHOT_EXAMPLES,
        """<request_context>
<capability>{capability}</capability>
<project_id>{project_id}</project_id>
<user_instruction>{instruction}</user_instruction>
<allowed_evidence_refs>{evidence_refs}</allowed_evidence_refs>
</request_context>

<untrusted_evidence>
{evidence}
</untrusted_evidence>""",
    )
)
