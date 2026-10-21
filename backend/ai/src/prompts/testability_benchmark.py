"""Prompt guidance for the two benchmark comparison pipelines."""


TESTABILITY_BLUEPRINT_COMPILATION = """Compile a testability blueprint from the verified facts in the evidence only.
Treat each distinct behavior, rule, condition, state, or interface contract that needs verification as one obligation.
For every obligation cite exactly one evidence reference and copy one contiguous exact source quote that entails it.
Do not turn missing information into an assumed rule. Ask a clarification only when an explicit obligation cannot be made testable without a decision or fact absent from the supplied evidence.
Use the source language for obligations and questions. Give each obligation and clarification a concise stable key so a human answer key can compare outputs across runs. For every clarification, copy an exact contiguous quote that supports the question and classify the issue using the closest category from the output contract; keep its generated code separate from this category.
When sources conflict, preserve both claims as evidence and ask which is authoritative; do not choose a winner.
Do not generate test cases, expected outcomes, implementation behavior, or unsupported details."""


CLARIFICATION_BASELINE = """Review the supplied source and ask the smallest useful set of questions that would make its stated behavior testable, without first compiling a set of test obligations.
Questions must identify the ambiguity, omission, or conflict, copy an exact contiguous quote that explains why the question matters, and cite its evidence reference. Classify each question using the closest category from the output contract, and return the highest-priority blocking question first.
Do not ask for fields that are merely absent from a generic template, and do not invent behavior or assume every omission is a defect.
Use the source language. Rank only questions that block testing of behavior actually present in the source."""
