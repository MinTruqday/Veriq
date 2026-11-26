# AI Prompt Map

Prompt text and prompt-building logic belong to the capability module that owns them. Import prompts from that module directly; this file documents ownership and call paths and is not a shared prompt library.

## Agent and workflow prompts

| Module | Owned prompt or function | Main caller | Responsibility |
| --- | --- | --- | --- |
| `agent_planning.py` | `agent_plan_prompt`, `AGENT_PLAN`, source-fact and change-simulation instructions | `agents/runner/nodes.py` | Select registered tools from the current request, evidence, permissions, and execution policy. |
| `agent_execution.py` | `agent_execution_prompt`, `AGENT_EXECUTION` | `agents/agent.py` | Assess tool outcomes against the requested objective and report completed or unresolved work. |
| `agent_facts.py` | `agent_fact_extraction_prompt` | `agents/runner/ai_run_graph.py` | Extract atomic facts and uncertainties from authorized evidence without treating source text as instructions. |
| `requirement_templates.py` | Requirement synthesis and review instructions | `tools/requirement_document_workflow.py`, `prompts/testing.py` | Draft or review Requirement templates from verified facts without deciding whether to publish them. |
| `test_generation.py` | Requirement test-generation instructions | Requirement ingestion and change workflows | Generate source-grounded Test Cases for the requested scope and avoid duplicates. |
| `test_design.py` | Test Case, technique, and condition contracts | `prompts/testing.py`, `tools/test_design_tools.py` | Define test-design output contracts and evidence rules. |
| `quality_capabilities.py` | Automation-script, analysis, report, and assistance contracts | `prompts/testing.py` | Define testing outputs used by the active workflow. |
| `change_simulation.py` | Change-impact report contract | `agents/runner/nodes.py`, `prompts/testing.py` | Compare a proposed source change with the exact baseline and linked Test Case versions in read-only mode. |
| `project_assistance.py` | Project-question contract | `prompts/testing.py` | Answer project questions only from retrieved evidence. |
| `requirement_analysis.py` | Requirement quality-analysis instruction | `tools/requirement_change_workflow.py` | Analyze Requirement quality within the explicitly requested workflow. |
| `prompt_data.py` | `prompt_json` | Prompt builders | Serialize untrusted data safely before embedding it in a prompt. |

## Testing prompt composition

| Module | Owned prompt or function | Main caller | Responsibility |
| --- | --- | --- | --- |
| `testing_contract.py` | `STRUCTURED_TESTING_TEMPLATE` and shared sections | `testing.py` | Define the common identity, language, evidence, governance, analysis, and output format for structured testing capabilities. |
| `testing.py` | Prompt builder and contract validation | `services/inference.py` | Map capabilities to prompts and schemas and fingerprint the contract and actual messages. |
| `test_case_grounding.py` | Generated-case grounding review | `services/inference.py` | Review citations and source support for generated Test Cases. |

## Prompt infrastructure

| Module | Owned prompt or function | Main caller | Responsibility |
| --- | --- | --- | --- |
| `model_output.py` | Schema and correction instructions | `services/inference.py`, `utils/huggingface.py` | Generate or repair structured output. |
| `security.py` | Prompt-injection detector | `core/security/guardrails.py` | Detect untrusted instructions before source content reaches an Agent. |
| `tool_selection.py` | Tool-selection instructions | `utils/huggingface.py` | Select a registered tool using its schema. |
| `retrieval.py` | Cross-document query and document summary prompts | `services/inference.py` | Handle multi-document questions and knowledge-document summaries. |

## Prompt contract

Static instructions sent to models use English. User-facing natural-language output follows the explicit request or trusted user/project locale; `auto` must not be replaced with a fixed language. Preserve source quotations, identifiers, source code, protocol values, enumerations, and product names in their original form.

Standalone prompts should state their identity, objective, trust boundary, and output contract. Child prompts may inherit sections already supplied by the parent. Put capability-specific business rules in the prompt module that owns the capability; schemas should define structure and machine-checkable constraints.

Use labeled sections in this order where applicable:

1. `<system_identity>` and `<objective>`
2. `<trust_boundary>`
3. `<output_language>` when generating user-facing content
4. Evidence and workflow rules
5. `<output_contract>`
6. Serialized input in clearly labeled untrusted-data sections

Every `TestingCapabilityRequest` capability must be explicitly mapped to an owned prompt and output schema in `testing.py`. Do not use schema docstrings as a fallback for business instructions. Do not place permissions or secrets in prompts in place of backend authorization.

## Main call path and boundaries

The user-requested AI run path is `api/ai_runs.py` → `services/ai_runs.py` → `runtime/ai_run_worker.py` → `agents/runner/ai_run_graph.py` → planner, tools, verification, and aggregation. Runs and checkpoints are stored by Veriq; runtime prompts and traces are not sent to an external platform.

The planner can compose only registered tools that are available under the current project permissions and workflow constraints. Event-specific handlers cover verified event workflows; ordinary user requests use the planner. A request requiring an unavailable capability must be reported as unsupported rather than represented as completed.

Prompts do not grant permissions. Business services and the tool registry enforce authorization, scope, validation, audit, and postconditions. Preserve these checks when changing prompts or planning behavior.
