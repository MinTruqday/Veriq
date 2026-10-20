def tool_selection_instruction(tool_definitions, forced_name=None):
    rules = [
        "Select exactly one registered tool that directly satisfies the request",
        "Return only one JSON object containing name and arguments",
        "The name must exactly match a registered tool",
        "The arguments must be a JSON object conforming to that tool schema",
        "Never invent missing identifiers or required arguments",
        "Silently verify authorization relevance and schema conformance before answering",
        "Do not reveal hidden reasoning",
    ]
    if forced_name:
        rules.append(f"Use exactly this tool {forced_name}")
    rules.append(f"REGISTERED_TOOLS {tool_definitions}")
    return "\n".join(rules)


def tool_selection_correction_instruction(error):
    return "\n".join(
        [
            "The previous tool selection was invalid",
            f"Validation error {str(error)[:1000]}",
            "Return only one corrected tool call JSON object",
            "Do not explain the correction",
        ]
    )
