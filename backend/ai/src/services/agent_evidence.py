def verified_tool_evidence(run, checkpoint):
    if not checkpoint or not checkpoint.state_snapshot:
        return []
    snapshot = checkpoint.state_snapshot
    if (
        snapshot.run.run_id != run.automation_run_id
        or snapshot.run.project_id != run.project_id
    ):
        return []
    result = run.result or {}
    proposal = result.get("proposal") or {}
    proposal_refs = set(proposal.get("evidence_refs") or [])
    run_refs = set(result.get("evidence_refs") or [])
    allowed_refs = proposal_refs & run_refs
    output = []
    for item in snapshot.evidence:
        if (
            item.project_id != run.project_id
            or item.source != "tool"
            or item.artifact_type != "tool_result"
            or not item.authority.startswith("verified_tool:")
            or item.artifact_id not in allowed_refs
            or not item.text.strip()
        ):
            continue
        output.append(
            {
                "evidence_ref": item.artifact_id,
                "project_id": item.project_id,
                "tool_name": item.authority.removeprefix("verified_tool:"),
                "text": item.text,
            }
        )
    return output
