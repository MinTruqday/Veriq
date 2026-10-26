"""Structured objectives for project lifecycle events handled by the AI agent."""

from src.prompts.prompt_data import prompt_json


def _event_objective(event_type, objective):
    return "\n".join(
        (
            "<event_workflow>",
            f"<event_type>{prompt_json(event_type)}</event_type>",
            f"<objective>{objective}</objective>",
            "<execution_rules>",
            "Use only authorized project evidence and event-scoped permissions. Execute all downstream actions that are explicitly in scope and pass deterministic validation; do not wait for a human confirmation for an authorized automated step.",
            "Do not invent missing business facts or resolve conflicting sources. Record a clarification and pause only the dependent work when a decision or required evidence is missing.",
            "Preserve historical versions. Apply changes only through the existing versioned business APIs, and verify every claimed mutation by reading back its result and links.",
            "If permission, revision, evidence, quality, or release gates fail, preserve prior data and report the specific block. Never claim execution without an observed result.",
            "</execution_rules>",
            "</event_workflow>",
        )
    )


def generic_event_objective(trigger):
    return _event_objective(
        trigger,
        "Process the event within its project scope and continue all relevant authorized Requirements, test design, execution, defect, planning, release, or reporting work to verified completion.",
    )


def document_ingested_objective():
    return _event_objective(
        "DOCUMENT_INGESTED",
        "Process the newly authorized document through source/version checks, evidence-backed fact extraction, testability blueprint compilation, Requirement synthesis, duplicate handling, deterministic quality checks, grounded Test Case generation, and authorized publication. Record unresolved source conflicts or missing decision facts as clarifications; stop only dependent artifacts. Read back every published artifact and its trace links.",
    )


def api_operation_confirmed_objective():
    return _event_objective(
        "API_OPERATION_CONFIRMED",
        "Read the exact confirmed API operation and its source import. Generate Test Cases only from documented parameters, request data, responses, and status codes; preserve operation/version citations and mark unsupported behavior incomplete. Recheck the operation revision before every mutation. Automatically omit incomplete or duplicate candidates, import only unique grounded cases, run deterministic quality checks, publish immutable versions through the event-authorized lifecycle, and read each version and source link back. If the source changes, a quality gate fails, or duplicate state changes concurrently, preserve existing artifacts and report the specific unresolved case; never create a duplicate or wait for a user to approve an authorized step.",
    )


def requirement_changed_objective():
    return _event_objective(
        "REQUIREMENT_CHANGED",
        "Compare the exact prior baseline and new Requirement versions, follow project-scoped trace links, classify linked Test Cases as still valid, affected, or needing additions, and prepare only evidence-grounded minimal maintenance changes. Never modify historical versions. Apply a new version only when evidence, quality, revision, scope, and event permissions pass; then read back each changed artifact and trace link.",
    )


def defect_recorded_objective(trigger="DEFECT_RECORDED"):
    return _event_objective(
        trigger,
        "Create or resume the analysis record for the exact defect revision in the verified event, produce evidence-grounded cause hypotheses and trace candidates, and read every saved record back. Keep hypotheses separate from confirmed root cause; never mutate defect links automatically or create corrective actions without supporting evidence.",
    )


def test_execution_recorded_objective():
    return _event_objective(
        "TEST_EXECUTION_RECORDED",
        "Compare a stored failed execution with its linked defect and the exact Test Case version attached to the relevant test obligation. Record feedback only after verifying those links. A passing result alone does not establish test quality or prove the absence of defects.",
    )


def test_plan_approved_objective():
    return _event_objective(
        "TEST_PLAN_APPROVED",
        "Create one idempotent Test Run from the approved Test Plan snapshot. Start execution only when current permissions and environment allow it, then read back and verify the exact frozen scope. Never fabricate execution results.",
    )


def test_plan_changed_objective():
    return _event_objective(
        "TEST_PLAN_CHANGED",
        "Inspect the changed Test Plan in its project. If its scope is not yet frozen, validate Requirement and Test Case versions, release, build, environment, and completeness. Freeze the snapshot through the business API only when all gates pass and the verified event principal has the required permission; verify the snapshot and create an idempotent Test Run. If a required input, permission, or gate is missing, preserve the plan and report the specific reason. Never expand scope implicitly.",
    )


def performance_configuration_approved_objective():
    return _event_objective(
        "PERFORMANCE_CONFIGURATION_APPROVED",
        "Read the exact approved performance configuration and derive a performance-plan draft only from its typed, explicitly populated workload fields and linked Requirement versions. If required workload values are absent or ambiguous, create no draft and record a clarification that names the missing fields and source configuration. Preserve the approved source plan and verify any generated draft and its provenance.",
    )


def test_execution_observation_objective():
    return _event_objective(
        "TEST_EXECUTION_OBSERVED",
        "Verify the newly recorded result against its Test Run, Test Case version, and linked defects. Record only observed outcomes; do not infer a root cause or create a defect solely because a test failed.",
    )


def work_item_changed_observation_objective():
    return _event_objective(
        "WORK_ITEM_CHANGED",
        "Read the changed Work Item and only its explicitly linked Requirements and Test Cases in the same project. Use only the typed dependency_edge supplied by the verified database event to describe a dependency: preserve its exact relationship_id, relationship_type, source_artifact_id, and target_artifact_id. Do not infer an edge or its direction from prose or relationship_path. Review each endpoint only through its separately authorized event. Summarize observable impact and unresolved scope. This is an impact review: do not create Requirements or modify linked artifacts based only on a Work Item or dependency change.",
    )


def test_case_changed_observation_objective():
    return _event_objective(
        "TEST_CASE_CHANGED",
        "Read the current draft revision, run quality checks, and search for near-duplicates. Analyze impact only when the verified event provides the exact before and after revisions and the draft has a Requirement or source link. For a new draft, missing prior version, missing source, or insufficient evidence, report only verified facts. When evidence is sufficient, update only affected artifacts through the existing versioned workflow and verify the readback. Never overwrite a frozen version or invent details.",
    )


def test_case_approved_observation_objective():
    return _event_objective(
        "TEST_CASE_APPROVED",
        "Read the exact newly frozen Test Case version and refresh derived Requirement assurance snapshots for its verified links. Use revisions to avoid overwriting concurrent changes and read back each refreshed snapshot. Update derived state only; do not approve an assurance assessment, alter a QA decision, or change the frozen Test Case.",
    )


def release_changed_observation_objective():
    return _event_objective(
        "RELEASE_CHANGED",
        "Read back the changed Release. If it is ACTIVE, request closure through the business API using only the verified event-scoped close permission. Close only when the completion report, exit criteria, blocker defects, evidence, and Requirement assurance gates pass, then verify CLOSED. If any gate, permission, revision, or state condition fails, preserve the Release and report why; never bypass a gate.",
    )


def status_report_created_objective():
    return _event_objective(
        "STATUS_REPORT_CREATED",
        "Create an evidence-grounded narrative draft for the exact newly created status report. Use only the saved report and its immutable monitoring snapshot, preserve all computed metrics and the report itself, and store the result as a separately traceable candidate. Verify project, report revision, source event, and saved result. Do not invent forecasts, alter report fields, or change the report lifecycle.",
    )


def test_completion_report_created_objective():
    return _event_objective(
        "TEST_COMPLETION_REPORT_CREATED",
        "Create an evidence-grounded narrative and group recorded lessons for the exact newly created completion report. Use only the saved report and its frozen scope; preserve metrics and source lessons, keep candidates separate from the report, and read back both results with matching project, report revision, event and run provenance.",
    )
