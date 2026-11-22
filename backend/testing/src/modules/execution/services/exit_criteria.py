from src.schemas.test_monitoring import ExitCriterionDefinition


def normalize_criterion(raw, index):
    rule_type = str(raw.get("type") or raw.get("key") or "").upper()
    if rule_type in {"EXECUTION_PROGRESS", "EXECUTION_PERCENT"}:
        rule_type = "EXECUTION_PERCENT_MIN"
    elif rule_type == "PASS_RATE":
        rule_type = "PASS_RATE_MIN"
    elif rule_type == "OPEN_BLOCKER":
        rule_type = "OPEN_BLOCKER_MAX"
    elif rule_type == "OPEN_CRITICAL":
        rule_type = "OPEN_CRITICAL_MAX"
    elif rule_type == "REQUIREMENT_COVERAGE":
        rule_type = "REQUIREMENT_COVERAGE_MIN"
    elif rule_type in {"AC_COVERAGE", "ACCEPTANCE_CRITERION_COVERAGE"}:
        rule_type = "AC_COVERAGE_MIN"
    elif rule_type == "CONDITION_COVERAGE":
        rule_type = "CONDITION_COVERAGE_MIN"
    elif rule_type == "STALE_TESTCASES":
        rule_type = "STALE_TESTCASE_MAX"
    threshold = raw.get("threshold", raw.get("value"))
    supported = {"EXECUTION_PERCENT_MIN", "PASS_RATE_MIN", "OPEN_BLOCKER_MAX", "OPEN_CRITICAL_MAX", "REQUIREMENT_COVERAGE_MIN", "AC_COVERAGE_MIN", "CONDITION_COVERAGE_MIN", "STALE_TESTCASE_MAX", "REQUIRED_RUNS_COMPLETED", "CUSTOM_MANUAL_GATE"}
    if rule_type not in supported:
        rule_type = 'CUSTOM_MANUAL_GATE'
        threshold = False
    return ExitCriterionDefinition(
        criterion_id=str(
            raw.get("criterion_id")
            or raw.get("id")
            or f"{'EXIT-'}{index}"
        ),
        criterion=str(raw.get("criterion") or raw.get("name") or rule_type),
        type=rule_type,
        threshold=threshold,
    )


def evaluate_exit_criteria(definitions, metrics, completed_run_ids):
    results = []
    for index, raw in enumerate(definitions, 1):
        definition = normalize_criterion(raw, index)
        if definition.type == 'CUSTOM_MANUAL_GATE':
            actual = None
            status = 'INSUFFICIENT_DATA'
        elif definition.type == 'REQUIRED_RUNS_COMPLETED':
            required = set(definition.threshold)
            missing = sorted(required - set(completed_run_ids))
            actual = {"completed": sorted(required & set(completed_run_ids)), "missing": missing}
            status = 'PASS' if not missing else 'FAIL'
        else:
            actual = metrics.get({"EXECUTION_PERCENT_MIN": "execution_percent", "PASS_RATE_MIN": "pass_rate", "OPEN_BLOCKER_MAX": "open_blocker", "OPEN_CRITICAL_MAX": "open_critical", "REQUIREMENT_COVERAGE_MIN": "requirement_coverage", "AC_COVERAGE_MIN": "acceptance_criteria_coverage", "CONDITION_COVERAGE_MIN": "test_condition_coverage", "STALE_TESTCASE_MAX": "stale_testcases"}[definition.type], 0)
            threshold = float(definition.threshold)
            denominator_key = {"EXECUTION_PERCENT_MIN": "execution_denominator", "PASS_RATE_MIN": "pass_rate_denominator", "REQUIREMENT_COVERAGE_MIN": "requirement_coverage_denominator", "AC_COVERAGE_MIN": "acceptance_criteria_coverage_denominator", "CONDITION_COVERAGE_MIN": "test_condition_coverage_denominator"}.get(definition.type)
            if denominator_key and not metrics.get(denominator_key, 0):
                actual = None
                status = 'INSUFFICIENT_DATA'
            else:
                if (
                    definition.type in {"AC_COVERAGE_MIN", "CONDITION_COVERAGE_MIN", "EXECUTION_PERCENT_MIN", "PASS_RATE_MIN", "REQUIREMENT_COVERAGE_MIN"}
                    and 0
                    <= threshold
                    <= 1
                ):
                    threshold *= 100
                passed = (
                    actual >= threshold if definition.type in {"AC_COVERAGE_MIN", "CONDITION_COVERAGE_MIN", "EXECUTION_PERCENT_MIN", "PASS_RATE_MIN", "REQUIREMENT_COVERAGE_MIN"} else actual <= threshold
                )
                status = 'PASS' if passed else 'FAIL'
        results.append(
            {
                **definition.model_dump(),
                "actual": actual,
                "status": status,
                "overridden": False,
                "evidence_refs": [],
            }
        )
    return results


def quality_gate_status(evaluations):
    if any(item["status"] == 'FAIL' for item in evaluations):
        return 'FAIL'
    incomplete = {'INSUFFICIENT_DATA', 'MANUAL_REQUIRED'}
    if any(item["status"] in incomplete for item in evaluations):
        return 'INSUFFICIENT_DATA'
    if any(item["status"] == 'WARN' for item in evaluations):
        return 'WARN'
    return 'PASS' if evaluations else 'INSUFFICIENT_DATA'
