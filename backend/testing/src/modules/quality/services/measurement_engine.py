import ast
import math

from src.core.common import now
from src.repositories.measurement import measurement_repository


SAFE_EXPRESSION_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
)


def ratio(numerator, denominator):
    if not denominator:
        return None
    return round(float(numerator) * 100 / float(denominator), 4)


def validate_formula_source(formula_type, formula, data_sources):
    unknown_sources = sorted(set(data_sources) - {
        'testing-domain',
        'test_monitoring_snapshots',
        'test_results',
        'test_cases',
        'test_case_versions',
        'automation_script_drafts',
        'automation_executions',
        'defects',
        'requirements',
        'requirement_versions',
        'maintenance_proposals',
        'regression_recommendations',
        'environment_incidents',
    })
    if unknown_sources:
        return {
            "valid": False,
            "errors": [{"code": 'MEASUREMENT_SOURCE_UNSUPPORTED', "sources": unknown_sources}],
        }
    if formula_type != 'CUSTOM_SAFE_EXPRESSION':
        return {"valid": True, "errors": []}
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError:
        return {"valid": False, "errors": [{"code": 'MEASUREMENT_FORMULA_SYNTAX_INVALID'}]}
    forbidden = sorted(
        {
            type(node).__name__
            for node in ast.walk(tree)
            if not isinstance(node, SAFE_EXPRESSION_NODES)
        }
    )
    if forbidden:
        return {
            "valid": False,
            "errors": [{"code": 'MEASUREMENT_FORMULA_OPERATION_UNSUPPORTED', "nodes": forbidden}],
        }
    nodes = list(ast.walk(tree))
    if len(nodes) > 100:
        return {"valid": False, "errors": [{"code": 'MEASUREMENT_FORMULA_TOO_COMPLEX'}]}
    if any(
        isinstance(node, ast.Constant)
        and (isinstance(node.value, bool) or not isinstance(node.value, (int, float)))
        for node in nodes
    ):
        return {"valid": False, "errors": [{"code": 'MEASUREMENT_FORMULA_CONSTANT_INVALID'}]}
    if any(
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Pow)
        and isinstance(node.right, ast.Constant)
        and abs(node.right.value) > 10
        for node in nodes
    ):
        return {"valid": False, "errors": [{"code": 'MEASUREMENT_FORMULA_EXPONENT_INVALID'}]}
    return {
        "valid": True,
        "errors": [],
        "variables": sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}),
    }


def evaluate_safe_expression(formula, variables):
    
    tree = ast.parse(formula, mode="eval")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ValueError("MEASUREMENT_FORMULA_CONSTANT_INVALID")
            return float(node.value)
        if isinstance(node, ast.Name):
            value = variables.get(node.id)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("MEASUREMENT_FORMULA_VARIABLE_UNAVAILABLE")
            return float(value)
        if isinstance(node, ast.UnaryOp):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        left = evaluate(node.left)
        right = evaluate(node.right)
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.Mod):
            result = left % right
        elif isinstance(node.op, ast.Pow):
            if (
                abs(right) > 10
                or abs(left) > 1000000
            ):
                raise ValueError("MEASUREMENT_FORMULA_EXPONENT_INVALID")
            result = left**right
        else:
            raise ValueError("MEASUREMENT_FORMULA_OPERATION_UNSUPPORTED")
        if not math.isfinite(result) or abs(result) > 1000000000000:
            raise ValueError("MEASUREMENT_FORMULA_RESULT_INVALID")
        return result

    return round(evaluate(tree), 6)


async def compute_custom_metric(project_id, release_id, definition):
    
    query = {"project_id": project_id}
    if release_id:
        query["release_id"] = release_id
    snapshot = await measurement_repository.find_monitoring_snapshot(project_id, release_id)
    variables = {}
    if snapshot:
        variables.update(
            {
                key: value
                for key, value in snapshot.get("metrics", {}).items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            }
        )
    collection_names = {
        'requirements',
        'acceptance_criteria',
        'test_conditions',
        'test_results',
        'test_cases',
        'test_case_versions',
        'automation_script_drafts',
        'automation_executions',
        'defects',
        'maintenance_proposals',
        'regression_recommendations',
        'environment_incidents',
    }
    requested = (
        collection_names
        if 'testing-domain' in definition.get("data_sources", [])
        else collection_names & set(definition.get("data_sources", []))
    )
    for collection_name in requested:
        count_query = {"project_id": project_id}
        if release_id and collection_name in {
            'test_results', 'automation_executions', 'defects', 'environment_incidents'
        }:
            count_query["release_id"] = release_id
        variables[f"{collection_name}_count"] = await measurement_repository.count_collection(
            collection_name, count_query
        )
    validation = validate_formula_source(
        definition["formula_type"], definition["formula"], definition["data_sources"]
    )
    if not validation["valid"]:
        return None, {"reason": 'MEASUREMENT_DEFINITION_INVALID', "errors": validation["errors"]}
    missing = sorted(set(validation.get("variables", [])) - set(variables))
    if missing:
        return None, {"reason": 'MEASUREMENT_FORMULA_VARIABLE_UNAVAILABLE', "variables": missing}
    try:
        value = evaluate_safe_expression(definition["formula"], variables)
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        return None, {"reason": str(error) or 'MEASUREMENT_FORMULA_EVALUATION_FAILED'}
    return value, {
        "formula": definition["formula"],
        "variables": {key: variables[key] for key in validation.get("variables", [])},
        "monitoring_snapshot_id": snapshot.get("_id") if snapshot else None,
    }


async def compute_metric(project_id, release_id, key):
    source = {"key": key, "release_id": release_id}
    snapshot_metric = None
    if key == 'REQUIREMENT_COVERAGE':
        snapshot_metric = 'requirement_coverage'
    elif key in {'AC_COVERAGE', 'ACCEPTANCE_CRITERION_COVERAGE'}:
        snapshot_metric = 'acceptance_criteria_coverage'
    elif key in {'CONDITION_COVERAGE', 'TEST_CONDITION_COVERAGE'}:
        snapshot_metric = 'test_condition_coverage'
    elif key == 'RISK_COVERAGE':
        snapshot_metric = 'risk_coverage'
    elif key == 'EXECUTION_PROGRESS':
        snapshot_metric = 'execution_percent'
    elif key == 'PASS_RATE':
        snapshot_metric = 'pass_rate'
    if snapshot_metric:
        query = {"project_id": project_id}
        if release_id:
            query["release_id"] = release_id
        snapshot = await measurement_repository.find_monitoring_snapshot(
            project_id, release_id
        )
        if not snapshot:
            return None, source
        metrics = snapshot.get("metrics", {})
        value = metrics.get(snapshot_metric)
        source.update(
            {
                "monitoring_snapshot_id": snapshot["_id"],
                "monitoring_source_fingerprint": snapshot.get("source_fingerprint"),
            }
        )
        return value, source
    if key == 'BLOCKED_RATE':
        query = {"project_id": project_id}
        if release_id:
            query["release_id"] = release_id
        snapshot = await measurement_repository.find_monitoring_snapshot(
            project_id, release_id
        )
        if not snapshot:
            return None, source
        metrics = snapshot.get("metrics", {})
        denominator = (
            int(metrics.get("pass", 0))
            + int(metrics.get("fail", 0))
            + int(metrics.get("blocked", 0))
        )
        source.update(
            {
                "monitoring_snapshot_id": snapshot["_id"],
                "blocked": metrics.get("blocked", 0),
                "decisive": denominator,
            }
        )
        return ratio(metrics.get("blocked", 0), denominator), source
    if key == 'STALE_TEST_RATIO':
        total = await measurement_repository.count_collection(
            'test_cases',
            {"project_id": project_id, "status": {"$ne": 'ARCHIVED'}},
        )
        stale = await measurement_repository.count_collection(
            'test_cases',
            {"project_id": project_id, "status": 'NEEDS_UPDATE'},
        )
        source.update({"test_case_count": total, "stale_count": stale})
        return ratio(stale, total), source
    if key == 'AUTOMATION_COVERAGE':
        total = await measurement_repository.count_collection(
            'test_case_versions',
            {"project_id": project_id, "status": {"$in": ['APPROVED', 'FROZEN']}},
        )
        automated = await measurement_repository.count_collection(
            'automation_script_drafts',
            {"project_id": project_id, "status": 'APPROVED'},
        )
        source.update({"test_case_version_count": total, "approved_script_count": automated})
        return ratio(min(automated, total), total), source
    defects = {"project_id": project_id}
    runs = {"project_id": project_id}
    if release_id:
        defects["release_id"] = release_id
        runs["release_id"] = release_id
    if key == 'DEFECT_REOPEN_RATE':
        total = await measurement_repository.count_collection('defects', defects)
        reopened = await measurement_repository.count_collection(
            'defects',
            {
                **defects,
                "$or": [
                    {"reopen_count": {"$gt": 0}},
                    {"history.action": 'REOPENED'},
                ],
            },
        )
        source.update({"defect_count": total, "reopened_count": reopened})
        return ratio(reopened, total), source
    if key == 'CRITICAL_DEFECT_AGING':
        rows = await measurement_repository.list_defect_dates(
            {
                **defects,
                "severity": {"$in": ['blocker', 'critical', 'BLOCKER', 'CRITICAL']},
                "status": {"$nin": ['CLOSED', 'REJECTED']},
            },
            {"created_at": 1},
            10000,
        )
        if not rows:
            return None, source
        timestamp = now()
        value = (
            sum(max(0, (timestamp - item["created_at"]).total_seconds()) for item in rows)
            / len(rows)
            / 86400
        )
        source["defect_ids"] = [item["_id"] for item in rows]
        return round(value, 4), source
    if key == 'MEAN_TIME_TO_RETEST':
        rows = await measurement_repository.list_defect_dates(
            {**defects, "resolved_at": {"$type": "date"}, "retested_at": {"$type": "date"}},
            {"resolved_at": 1, "retested_at": 1},
            10000,
        )
        durations = [
            (item["retested_at"] - item["resolved_at"]).total_seconds()
            / 3600
            for item in rows
            if item["retested_at"] >= item["resolved_at"]
        ]
        source["sample_size"] = len(durations)
        return round(sum(durations) / len(durations), 4) if durations else None, source
    if key == 'REQUIREMENT_VOLATILITY':
        total = await measurement_repository.count_collection(
            'requirements', {"project_id": project_id}
        )
        changed = len(await measurement_repository.distinct_changed_requirements(project_id))
        source.update({"requirement_count": total, "changed_requirement_count": changed})
        return ratio(changed, total), source
    if key == 'IMPACT_PROPOSAL_ACCEPTANCE_RATE':
        query = {"project_id": project_id}
        total = await measurement_repository.count_collection(
            'maintenance_proposals', query
        )
        accepted = await measurement_repository.count_collection(
            'maintenance_proposals',
            {**query, "status": {"$in": ['ACCEPTED', 'APPROVED', 'APPLIED']}},
        )
        source.update({"proposal_count": total, "accepted_count": accepted})
        return ratio(accepted, total), source
    if key == 'REGRESSION_EFFECTIVENESS':
        rows = await measurement_repository.list_regression_results(
            project_id, 10000
        )
        selected = sum(len(item.get("selected_test_case_ids", [])) for item in rows)
        detected = sum(len(item.get("detected_defect_ids", [])) for item in rows)
        source.update({"selected_count": selected, "detected_defect_count": detected})
        return ratio(detected, selected), source
    if key in {'AUTOMATION_STABILITY', 'AUTOMATION_PASS_STABILITY'}:
        rows = await measurement_repository.list_automation_statuses(
            runs, 10000
        )
        completed = [
            item for item in rows if item.get("status") in {'PASSED', 'FAILED', 'COMPLETED'}
        ]
        passed = sum(
            1 for item in completed if item.get("status") == 'PASSED'
        )
        source.update({"execution_count": len(completed), "passed_count": passed})
        return ratio(passed, len(completed)), source
    if key in {'ESCAPED_DEFECT_RATE', 'DEFECT_REMOVAL_EFFICIENCY'}:
        production = await measurement_repository.count_collection(
            'environment_incidents',
            {"project_id": project_id, "production": True, "linked_defect_ids.0": {"$exists": True}},
        )
        removed = await measurement_repository.count_collection(
            'defects',
            {**defects, "status": 'CLOSED'},
        )
        if not production:
            return None, {**source, "reason": 'PRODUCTION_INCIDENT_DATA_UNAVAILABLE'}
        denominator = production + removed
        source.update({"escaped_count": production, "removed_count": removed})
        return (
            ratio(production, denominator)
            if key == 'ESCAPED_DEFECT_RATE'
            else ratio(removed, denominator)
        ), source
    return None, {**source, "reason": 'METRIC_SOURCE_UNAVAILABLE'}
