def verified_tool_evidence_records(evidence, project_id, allowed_refs):
    allowed_refs = set(allowed_refs or [])
    output = []
    seen_refs = set()
    for raw_item in evidence or []:
        item = raw_item if isinstance(raw_item, dict) else raw_item.model_dump(mode="python")
        artifact_id = str(item.get("artifact_id") or "")
        authority = str(item.get("authority") or "")
        text = str(item.get("text") or "")
        if (
            item.get("project_id") != project_id
            or item.get("source") != "tool"
            or item.get("artifact_type") != "tool_result"
            or not authority.startswith("verified_tool:")
            or artifact_id not in allowed_refs
            or artifact_id in seen_refs
            or not text.strip()
        ):
            continue
        seen_refs.add(artifact_id)
        output.append(
            {
                "artifact_id": artifact_id,
                "project_id": project_id,
                "source": "tool",
                "artifact_type": "tool_result",
                "authority": authority,
                "text": text,
            }
        )
    return output


def verified_tool_evidence(run, checkpoint=None):
    result = run.result or {}
    proposal_refs = set((result.get("proposal") or {}).get("evidence_refs") or [])
    run_refs = set(result.get("evidence_refs") or [])
    allowed_refs = proposal_refs & run_refs
    records = result.get("tool_evidence") or []
    if records:
        items = verified_tool_evidence_records(records, run.project_id, allowed_refs)
    else:
        if not checkpoint or not checkpoint.state_snapshot:
            return []
        snapshot = checkpoint.state_snapshot
        if (
            snapshot.run.run_id != run.ai_run_id
            or snapshot.run.project_id != run.project_id
        ):
            return []
        items = verified_tool_evidence_records(
            snapshot.evidence,
            run.project_id,
            allowed_refs,
        )
    return [
        {
            "evidence_ref": item["artifact_id"],
            "project_id": item["project_id"],
            "tool_name": item["authority"].removeprefix("verified_tool:"),
            "text": item["text"],
        }
        for item in items
    ]
