TESTING_LANGUAGE_POLICY = """<language_policy>
Detect the language of user_instruction and write every user facing natural language field in that language
When user_instruction contains multiple languages follow an explicit language request otherwise use its dominant natural language
Preserve identifiers source code protocol values enumerations and product names exactly instead of translating them
</language_policy>"""
