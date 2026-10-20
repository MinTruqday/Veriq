TESTING_ANALYSIS_PROTOCOL = """<analysis_protocol>
Use private step by step reasoning internally before answering
1 Parse the user intent and capability constraints
2 Extract only relevant facts from the evidence boundary
3 Separate direct facts from defensible inferences
4 Generate candidate conclusions or proposals
5 Reject every candidate that lacks evidence or violates a constraint
6 Verify identifiers evidence references field consistency and schema conformance
Do not reveal private chain of thought or intermediate analysis
</analysis_protocol>"""
