from src.runtime.limits import limits


def test_tool_budget_fits_inside_automation_run_budget():
    assert limits.task_timeout_seconds < limits.run_timeout_seconds


def test_message_is_not_requeued_before_a_full_automation_run_can_finish():
    assert limits.message_ack_timeout_seconds > limits.run_timeout_seconds

