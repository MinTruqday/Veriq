from src.agents.runner.request_tasks import (
    direct_capability_task,
    direct_change_simulation_task,
    simulation_baseline_trace_links,
    simulation_baseline_trace_snapshot,
    simulation_linked_test_case_version_ids,
)
from src.agents.runner.agent_validation import (
    bounded_tasks,
    mutation_fingerprint,
    observed_draft_identifiers,
    observed_identifiers,
    proposal_fingerprint,
    tool_evidence_reference,
    validated_tasks,
    verified_tool_call_records,
)
from src.tools.registry import agent_available_tools, tool_access

__all__ = [
    "available_tools",
    "bounded_tasks",
    "direct_capability_task",
    "direct_change_simulation_task",
    "mutation_fingerprint",
    "observed_draft_identifiers",
    "observed_identifiers",
    "proposal_fingerprint",
    "simulation_baseline_trace_links",
    "simulation_baseline_trace_snapshot",
    "simulation_linked_test_case_version_ids",
    "tool_evidence_reference",
    "validated_tasks",
    "verified_tool_call_records",
]


def available_tools(permissions, compact=False, actions=None, domains=None):
    values = []
    tools = agent_available_tools(permissions)
    allowed_domains = set(domains) if domains is not None else None
    for tool in tools.values():
        access = tool_access(tool)
        if access and (actions is None or access.action in actions) and (
            allowed_domains is None or bool(set(access.domains).intersection(allowed_domains))
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
