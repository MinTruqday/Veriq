from src.schemas.inference_change_simulation import ChangeSimulationReportOutput


def change_simulation_batches(version_ids, batch_size):
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
        raise ValueError("change_simulation_batch_size_invalid")
    ordered_ids = list(
        dict.fromkeys(
            str(value).strip()
            for value in version_ids
            if value is not None and str(value).strip()
        )
    )
    return [ordered_ids[index : index + batch_size] for index in range(0, len(ordered_ids), batch_size)]


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _strings(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from _strings(nested)


def _completed_tool_results(observations):
    return {
        str(item.get("tool_name")): item.get("result")
        for item in observations or []
        if item.get("status") == "COMPLETED" and item.get("tool_name")
    }


def _trace_scope_signature(links):
    return {
        (
            str(item.get("source_type") or ""),
            str(item.get("source_id") or ""),
            str(item.get("target_type") or ""),
            str(item.get("target_id") or ""),
            str(item.get("link_type") or ""),
            str(item.get("status") or ""),
        )
        for item in links
    }


def simulation_trace_scope_is_current(discovery_links, revalidation_links, revalidation_present):
    return bool(revalidation_present) and _trace_scope_signature(
        discovery_links
    ) == _trace_scope_signature(revalidation_links)


def validate_change_simulation_report(
    report: ChangeSimulationReportOutput,
    baseline_version_id: str,
    proposed_text: str,
    linked_version_ids: list[str],
    observations: list[dict],
    evidence: list[dict],
):
    """Reject incomplete classifications and any quote not found in its exact source."""
    if report.baseline_requirement_version_id != baseline_version_id:
        raise ValueError("change_simulation_baseline_mismatch")

    expected_ids = list(dict.fromkeys(str(value) for value in linked_version_ids))
    actual_ids = [item.test_case_version_id for item in report.classifications]
    if len(actual_ids) != len(set(actual_ids)):
        raise ValueError("change_simulation_duplicate_test_case_classification")
    if set(actual_ids) != set(expected_ids):
        raise ValueError("change_simulation_classification_scope_incomplete")

    sources = {
        ("BASELINE_REQUIREMENT", baseline_version_id): [],
        ("PROPOSED_REQUIREMENT", baseline_version_id): [proposed_text],
    }
    for item in evidence or []:
        if (
            item.get("artifact_type") == "requirement_version"
            and str(item.get("artifact_version_id") or "") == baseline_version_id
        ):
            sources[("BASELINE_REQUIREMENT", baseline_version_id)].extend(_strings(item.get("text")))

    results = _completed_tool_results(observations)
    baseline = results.get("get_requirement_version")
    if (
        isinstance(baseline, dict)
        and str(baseline.get("_id") or "") == baseline_version_id
    ):
        sources[("BASELINE_REQUIREMENT", baseline_version_id)].extend(_strings(baseline))

    result_by_version = {
        str(item.get("source_version_id")): item.get("result")
        for item in observations or []
        if item.get("tool_name") == "get_test_case_version_by_id"
        and item.get("status") == "COMPLETED"
        and item.get("source_version_id")
        and item.get("result") is not None
        and isinstance(item.get("result"), dict)
        and str(item["result"].get("_id") or "") == str(item["source_version_id"])
    }
    for version_id in expected_ids:
        result = result_by_version.get(version_id)
        if result is not None:
            sources[("TEST_CASE_VERSION", version_id)] = list(_strings(result))

    for classification in report.classifications:
        quoted_source_types = {quote.source_type for quote in classification.evidence}
        if not {
            "BASELINE_REQUIREMENT",
            "PROPOSED_REQUIREMENT",
            "TEST_CASE_VERSION",
        }.issubset(quoted_source_types):
            raise ValueError("change_simulation_comparison_evidence_incomplete")
        for quote in classification.evidence:
            key = (quote.source_type, quote.artifact_version_id)
            if key not in sources:
                raise ValueError("change_simulation_quote_source_out_of_scope")
            if quote.source_type == "TEST_CASE_VERSION" and key[1] != classification.test_case_version_id:
                raise ValueError("change_simulation_quote_test_case_mismatch")
            if not any(quote.quote in source for source in sources[key]):
                raise ValueError("change_simulation_quote_not_found_in_source")

    return report.model_dump(mode="json")


def simulation_source_payload(observations, evidence, baseline_version_id, proposed_text):
    results = _completed_tool_results(observations)
    baseline = results.get("get_requirement_version")
    if (
        not isinstance(baseline, dict)
        or str(baseline.get("_id") or "") != baseline_version_id
    ):
        baseline = None
    if baseline is None:
        baseline = next(
            (
                item.get("text")
                for item in evidence or []
                if item.get("artifact_type") == "requirement_version"
                and str(item.get("artifact_version_id") or "") == baseline_version_id
            ),
            "",
        )
    test_cases = []
    by_observed_id = {
        str(item.get("source_version_id")): item.get("result")
        for item in observations or []
        if item.get("tool_name") == "get_test_case_version_by_id"
        and item.get("status") == "COMPLETED"
        and item.get("source_version_id")
        and item.get("result") is not None
        and isinstance(item.get("result"), dict)
        and str(item["result"].get("_id") or "") == str(item["source_version_id"])
    }
    for version_id in by_observed_id:
        test_cases.append({
            "test_case_version_id": version_id,
            "content": by_observed_id[version_id],
        })
    return {
        "baseline": baseline,
        "proposed_text": proposed_text,
        "linked_test_case_versions": test_cases,
    }
