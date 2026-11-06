from src.core.auth import ProjectRole


def legacy_required_business_role(permission: str) -> ProjectRole | set[ProjectRole] | None:
    domain, _, action = permission.partition(".")
    if domain == "workreport":
        if action == "manage":
            return ProjectRole.BA
        if action in {"review", "publish"}:
            return {ProjectRole.BA, ProjectRole.QA}
        if action in {"write", "ai"}:
            return {ProjectRole.BA, ProjectRole.QA, ProjectRole.TESTER, ProjectRole.DEVELOPER}
    if domain in {
        "apiartifact",
        "automation",
        "coverage",
        "device_matrix",
        "environment",
        "measurement",
        "nfrtest",
        "qualityevaluation",
        "qualitygate",
        "regression",
        "reviewsession",
        "risk",
        "statisticalquality",
        "trace",
        "testplan",
        "testcase",
        "testscenario",
        "testcondition",
        "testdata",
        "testsuite",
        "teststrategy",
        "teststatusreport",
        "testcompletion",
        "testmonitor",
        "testanalysis",
        "release",
        "testresult",
        "testrun",
    } and permission not in {"testrun.execute", "testresult.correct"} and not permission.endswith(".read") and action not in {"version.read", "template.read"}:
        return ProjectRole.QA
    if permission in {"testrun.execute", "testresult.correct"}:
        return ProjectRole.TESTER
    if domain == "build" and not permission.endswith(".read"):
        return ProjectRole.DEVELOPER
    if permission in {
        "requirement.create",
        "requirement.update",
        "requirement.version.create",
        "requirement.merge",
        "requirement.split",
        "requirement.submit_review",
        "requirement.archive",
        "requirement.restore",
        "acceptance_criteria.manage",
        "business_rule.manage",
        "requirement_dependency.manage",
        "requirement_document.upload",
        "requirement_document.extract",
        "requirement_document.review_extraction",
        "requirement_document.confirm_extraction",
        "requirement_document.archive",
        "requirement_document.restore",
        "project.update",
        "project.create",
        "project.settings.manage",
        "project.members.manage",
        "project.archive",
        "project.restore",
        "project.connector.manage",
        "project.connector.sync",
        "knowledge.manage",
        "notification.project_rule.manage",
    }:
        return ProjectRole.BA
    if permission == "requirement.duplicate_check":
        return {ProjectRole.BA, ProjectRole.QA}
    if permission in {
        "requirement.review",
        "requirement.approve",
        "proposal.approve",
        "proposal.bulk.approve",
        "attachment.moderate",
        "comment.moderate",
        "release.close",
        "defect.assign",
        "defect.close",
        "defect.triage",
        "defect.trace.manage",
        "project.connector.review",
    }:
        return ProjectRole.QA
    if permission == "collaboration.conflict.resolve":
        return {ProjectRole.BA, ProjectRole.QA}
    if permission in {"changeset.create", "changeset.review", "trace.create"}:
        return {ProjectRole.BA, ProjectRole.QA}
    if permission in {"causalanalysis.create", "causalanalysis.update", "preventionaction.manage"}:
        return {ProjectRole.QA, ProjectRole.DEVELOPER}
    if permission == "causalanalysis.approve":
        return ProjectRole.QA
    if permission in {"environmentincident.create"}:
        return {ProjectRole.QA, ProjectRole.TESTER, ProjectRole.DEVELOPER}
    if permission in {"environmentincident.update"}:
        return {ProjectRole.QA, ProjectRole.DEVELOPER}
    if permission == "environmentincident.close":
        return ProjectRole.QA
    if permission in {"impact.execute", "impact.close", "impact.override", "impact.review"}:
        return ProjectRole.QA
    if permission in {"processimprovement.approve", "processimprovement.decide"}:
        return ProjectRole.QA
    if permission in {
        "processimprovement.create",
        "processimprovement.evaluate",
        "processimprovement.measure",
        "processimprovement.update",
    }:
        return {ProjectRole.QA, ProjectRole.DEVELOPER}
    if domain == "cicd":
        return ProjectRole.DEVELOPER
    if permission in {
        "ai.generate_testcase",
        "ai.generate_api_testcase",
        "ai.generate_scenario",
        "ai.generate_automation_script",
        "ai.generate_performance_plan",
        "ai.generate_security_tests",
        "ai.generate_regression",
        "ai.create_proposal",
        "ai.suggest_bug_trace",
        "proposal.bulk.generate",
        "proposal.review",
        "proposal.reject",
        "defect.duplicate_check",
    }:
        return ProjectRole.QA
    if permission == "ai.ask_project":
        return {ProjectRole.BA, ProjectRole.QA}
    if permission in {"ai.run_lint", "ai.run_impact"}:
        return {ProjectRole.BA, ProjectRole.QA}
    if permission == "ai.run_duplicate_check":
        return {ProjectRole.BA, ProjectRole.QA}
    if permission == "defect.create":
        return {ProjectRole.QA, ProjectRole.TESTER}
    if permission == "defect.retest":
        return ProjectRole.TESTER
    if permission == "defect.update":
        return {ProjectRole.QA, ProjectRole.DEVELOPER}
    if permission == "defect.transition.developer":
        return ProjectRole.DEVELOPER
    if domain == "webhook" and not permission.endswith(".read"):
        return ProjectRole.DEVELOPER
    return None
