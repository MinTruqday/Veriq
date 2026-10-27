from dataclasses import dataclass

from src.core.infrastructure.configuration import settings


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
    automation_recovery_batch_size: int
    dead_letter_max_redrives: int


limits = RuntimeLimits(
    agent_steps=settings.AI_AGENT_MAX_STEPS,
    tool_calls_per_task=settings.AI_AGENT_MAX_TOOL_CALLS,
    tool_errors=settings.AI_AGENT_MAX_TOOL_ERRORS,
    retries=settings.AI_AUTOMATION_MAX_RETRIES,
    run_timeout_seconds=settings.AI_AUTOMATION_RUN_TIMEOUT_SECONDS,
    task_timeout_seconds=settings.AI_AUTOMATION_TASK_TIMEOUT_SECONDS,
    message_ack_timeout_seconds=settings.AI_MESSAGE_ACK_TIMEOUT_SECONDS,
    evidence_items=settings.AI_AGENT_MAX_EVIDENCE_ITEMS,
    queue_retry_base_seconds=settings.AI_QUEUE_RETRY_BASE_SECONDS,
    queue_retry_max_seconds=settings.AI_QUEUE_RETRY_MAX_SECONDS,
    queue_retry_scan_seconds=settings.AI_QUEUE_RETRY_SCAN_SECONDS,
    automation_recovery_batch_size=settings.AI_AUTOMATION_RECOVERY_BATCH_SIZE,
    dead_letter_max_redrives=settings.AI_DEAD_LETTER_MAX_REDRIVES,
)
