from src.agents.runner.automation_event_tasks import (
    direct_approved_plan_task,
    direct_capability_task,
    direct_change_simulation_task,
    direct_changed_plan_task,
    direct_defect_event_task,
    direct_document_ingestion_task,
    direct_event_observation_task,
    direct_performance_configuration_task,
    direct_recorded_test_execution_task,
    direct_requirement_change_task,
    direct_test_case_change_impact_task,
    simulation_baseline_trace_links,
    simulation_linked_test_case_version_ids,
)
from src.agents.runner.automation_validation import (
    bounded_tasks,
    mutation_fingerprint,
    observed_draft_identifiers,
    observed_identifiers,
    proposal_fingerprint,
    validated_tasks,
    verified_tool_call_records,
)
from src.tools.registry import registered_tools, tool_access

__all__ = [
    "available_tools",
    "bounded_tasks",
    "direct_approved_plan_task",
    "direct_capability_task",
    "direct_change_simulation_task",
    "direct_changed_plan_task",
    "direct_defect_event_task",
    "direct_document_ingestion_task",
    "direct_event_observation_task",
    "direct_performance_configuration_task",
    "direct_recorded_test_execution_task",
    "direct_requirement_change_task",
    "direct_test_case_change_impact_task",
    "mutation_fingerprint",
    "observed_draft_identifiers",
    "observed_identifiers",
    "proposal_fingerprint",
    "simulation_baseline_trace_links",
    "simulation_linked_test_case_version_ids",
    "validated_tasks",
    "verified_tool_call_records",
]


def available_tools(permissions, intent="", compact=False, actions=None):
    values = []
    tools = registered_tools()
    intent_tool_exists = bool(intent and tool_access(tools.get(intent)))
    for tool in tools.values():
        access = tool_access(tool)
        if (
            access
            and access.permission in permissions
            and (actions is None or access.action in actions)
            and (not intent_tool_exists or access.name == intent)
        ):
            schema = tool.args_schema.model_json_schema()
            arguments = schema
            if compact:
                arguments = {
                    "required": schema.get("required", []),
                    "properties": {
                        name: {
                            key: value
                            for key, value in definition.items()
                            if key in {"type", "description", "enum", "minLength", "maxLength"}
                        }
                        for name, definition in schema.get("properties", {}).items()
                    },
                }
            values.append(
                {
                    "name": access.name,
                    "domains": sorted(access.domains),
                    "action": access.action,
                    "arguments": arguments,
                }
            )
    return values
