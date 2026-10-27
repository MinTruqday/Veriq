"""Structured objectives for AI-handled project lifecycle events."""

from src.prompts.prompt_data import prompt_json


def _event_objective(event_type, objective):
    return "\n".join(
        (
            "<event_workflow>",
            f"<event_type>{prompt_json(event_type)}</event_type>",
            f"<objective>{objective}</objective>",
            "<execution_rules>",
            "Use only authorized project evidence and permissions scoped to the verified event. Automatically perform permitted follow-up steps that pass deterministic checks; do not ask the user to reconfirm an already authorized automated step.",
            "Do not invent missing business facts or resolve conflicting sources. Record a clarification and pause only the dependent work when a required decision or evidence is missing.",
            "Preserve historical versions. Update only through existing versioned business APIs; read back results and links to verify every reported change.",
            "If permissions, versions, evidence, quality, or Release conditions fail, preserve prior data and state the blocker. Do not claim work ran unless its result was observed.",
            "</execution_rules>",
            "</event_workflow>",
        )
    )


def generic_event_objective(trigger):
    return _event_objective(
        trigger,
        "Handle the event within its project scope and continue all authorized related Requirement, test design, execution, Defect, planning, Release, or reporting work until results are read back and verified.",
    )


def document_ingested_objective():
    return _event_objective(
        "DOCUMENT_INGESTED",
        "Process the newly authorized document in this sequence: verify its source and version, extract evidence-backed facts, compile a testability blueprint, synthesize Requirements, resolve duplicate content, run deterministic quality checks, generate grounded Test Cases, and publish them automatically within the event's granted permissions. Record unresolved source conflicts or facts requiring a decision as clarifications; pause only artifacts that depend on the missing information. Read back every published artifact and its trace links.",
    )


def api_operation_confirmed_objective():
    return _event_objective(
        "API_OPERATION_CONFIRMED",
        "Read the confirmed API operation and the source document used to import it. Generate Test Cases only from documented parameters, request data, responses, and status codes; preserve operation/version citations and mark unsupported behavior as insufficient. Recheck the operation revision before every write. Automatically discard incomplete or duplicate candidates, import only unique grounded cases, run deterministic quality checks, publish immutable versions within the event's permissions, and read back each version and source link. If the source changes, a quality gate fails, or duplicate status changes concurrently, preserve existing artifacts and report unresolved cases; do not create duplicates or wait for user approval of an authorized step.",
    )


def requirement_changed_objective():
    return _event_objective(
        "REQUIREMENT_CHANGED",
        "Compare the correct prior Requirement baseline version with the new version, follow trace links within the project, classify linked Test Cases as still valid, affected, or requiring additions, and prepare only evidence-backed minimal maintenance changes. Never modify historical versions. Create a new version only when evidence, quality, revision, scope, and event permissions all pass; then read back each changed artifact and its trace links.",
    )


def defect_recorded_objective(trigger="DEFECT_RECORDED"):
    return _event_objective(
        trigger,
        "Create or resume the analysis record for the exact Defect revision in the verified event, prepare evidence-backed cause hypotheses and trace candidates, then read back every saved record. Keep hypotheses distinct from confirmed root causes; do not change Defect links or create corrective actions without supporting evidence.",
    )


def test_execution_recorded_objective():
    return _event_objective(
        "TEST_EXECUTION_RECORDED",
        "Compare the saved failed execution with its linked Defect and the exact Test Case version associated with the relevant test obligation. Record feedback only after verifying those links. A passing result does not by itself prove Test Case quality or that the system is defect-free.",
    )


def test_plan_approved_objective():
    return _event_objective(
        "TEST_PLAN_APPROVED",
        "Create exactly one idempotent Test Run from the approved Test Plan snapshot. Start execution only when current permissions and the environment allow it; then read back and verify the locked scope. Do not invent execution results.",
    )


def test_plan_changed_objective():
    return _event_objective(
        "TEST_PLAN_CHANGED",
        "Inspect the changed Test Plan in the correct project. If its scope is not locked, verify Requirement and Test Case versions, Release, build, environment, and completeness. Lock the snapshot through the business API only when every gate passes and the verified event principal has the required permissions; verify the snapshot again, then create an idempotent Test Run. If inputs, permissions, or conditions are missing, preserve the Test Plan and state the specific reason. Do not expand scope without authorization.",
    )


def performance_configuration_approved_objective():
    return _event_objective(
        "PERFORMANCE_CONFIGURATION_APPROVED",
        "Read the exact approved performance configuration and create a performance-plan draft only from explicitly populated, typed load fields and its linked Requirement version. If a required load value is missing or ambiguous, do not create a draft; record a clarification naming the missing field and source configuration. Preserve the approved source plan; verify the created draft and its provenance.",
    )


def test_execution_observation_objective():
    return _event_objective(
        "TEST_EXECUTION_OBSERVED",
        "Compare the newly recorded result with its Test Run, Test Case version, and linked Defect. Record only observed facts; do not infer a root cause or create a Defect solely because a Test Case failed.",
    )


def work_item_changed_observation_objective():
    return _event_objective(
        "WORK_ITEM_CHANGED",
        "Read the changed Work Item and only Requirements or Test Cases explicitly linked within the same project. Describe dependencies only from the typed dependency_edge supplied by the verified database event; preserve relationship_id, relationship_type, source_artifact_id, and target_artifact_id. Never infer an edge or its direction from prose or relationship_path. Review each endpoint only through its separately authorized event. Summarize observed impact and unresolved scope. This is impact review only: do not create Requirements or modify linked artifacts solely because a Work Item or dependency changed.",
    )


def test_case_changed_observation_objective():
    return _event_objective(
        "TEST_CASE_CHANGED",
        "Read the current draft revision, check quality, and search for near-duplicates. Analyze impact only when the verified event provides the exact prior and current revisions and the draft links to a Requirement or source. For a new draft, missing prior version, missing source, or insufficient evidence, report only verified facts. When evidence is sufficient, update only affected artifacts through the existing versioning workflow and read them back for verification. Never overwrite a locked version or invent details.",
    )


def test_case_approved_observation_objective():
    return _event_objective(
        "TEST_CASE_APPROVED",
        "Read the exact newly locked Test Case version and refresh the Requirement assurance snapshot from verified links. Use revisions to prevent overwriting concurrent changes and read back each refreshed snapshot. Update derived status only; do not approve an assurance record, change a QA decision, or modify a locked Test Case.",
    )


def release_changed_observation_objective():
    return _event_objective(
        "RELEASE_CHANGED",
        "Read back the changed Release. If it is ACTIVE, request closure through the business API using only close permissions scoped to the verified event. Close it only when the completion report, exit criteria, blocking Defects, evidence, and Requirement assurance gates all pass; then verify the CLOSED state. If any gate, permission, revision, or state condition fails, preserve the Release and state the reason; never bypass a gate.",
    )


def status_report_created_objective():
    return _event_objective(
        "STATUS_REPORT_CREATED",
        "Create an evidence-backed narrative draft for the exact newly created status report. Use only the saved report and immutable monitoring snapshot; preserve every calculated metric and report field, and store the narrative as a separately traceable candidate. Verify the project, report revision, source event, and saved result. Do not invent forecasts, modify report fields, or change the report lifecycle.",
    )


def test_completion_report_created_objective():
    return _event_objective(
        "TEST_COMPLETION_REPORT_CREATED",
        "Create an evidence-backed narrative and cluster recorded lessons for the exact newly created completion report. Use only the saved report and locked scope; preserve source metrics and lessons, store the candidate separately from the report, then read back both results and verify the project, report revision, event, and run provenance.",
    )
