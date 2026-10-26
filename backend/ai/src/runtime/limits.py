from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeLimits:
    agent_steps: int
    tool_calls_per_task: int
    tool_errors: int
    retries: int
    run_timeout_seconds: int
    task_timeout_seconds: int
    message_ack_timeout_seconds: int
    evidence_items: int
    queue_retry_base_seconds: int
    queue_retry_max_seconds: int
    queue_retry_scan_seconds: int


limits = RuntimeLimits(
    agent_steps=8,
    tool_calls_per_task=6,
    tool_errors=2,
    retries=2,
    run_timeout_seconds=900,
    task_timeout_seconds=840,
    message_ack_timeout_seconds=960,
    evidence_items=100,
    queue_retry_base_seconds=15,
    queue_retry_max_seconds=300,
    queue_retry_scan_seconds=5,
)
