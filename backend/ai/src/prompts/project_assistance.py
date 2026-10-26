"""Prompt contracts for direct project-evidence answers."""


PROJECT_QUESTION_CONTRACT = """<project_question_rules>
Answer in Vietnamese using only the supplied project evidence. Cite only evidence references actually used. If the sources do not answer the question, state the limitation instead of guessing. Keep the answer to at most five sentences and preserve technical identifiers and source quotations exactly.
</project_question_rules>"""
