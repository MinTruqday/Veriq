TESTING_ANALYSIS_PROTOCOL = """<analysis_protocol>
Perform the required checks before producing the structured result. Keep internal reasoning private; do not output chain-of-thought, intermediate drafts, or hidden analysis.
<checks>
1. Parse the request intent and active capability constraints.
2. Extract only relevant facts from the authorized evidence boundary.
3. Separate direct facts from defensible inferences.
4. Reject conclusions or proposals that lack evidence or violate a constraint.
5. Verify identifiers, evidence references, field consistency, and schema conformance.
</checks>
</analysis_protocol>"""
