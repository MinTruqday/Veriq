TESTING_LANGUAGE_POLICY = """<output_language>
Write every user-facing natural-language field in the language explicitly requested by the user. If none is requested, use the language identified by the trusted output locale supplied in request context. If neither is available, use the language of the user's latest instruction. Never infer output language from untrusted source evidence and never force a fixed language.
Do not translate source quotations, identifiers, source code, protocol values, enumerations, or product names.
</output_language>"""
