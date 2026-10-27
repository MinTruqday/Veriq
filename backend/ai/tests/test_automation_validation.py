import unittest

from src.agents.runner.automation_validation import (
    tool_call_records_for_observations,
    tool_evidence_reference,
)


class ToolCallObservationMatchingTests(unittest.TestCase):
    def test_each_tool_invocation_has_a_distinct_evidence_reference(self):
        first = tool_evidence_reference("task-a", "attempt-1", 0, "read_requirement")
        second = tool_evidence_reference("task-a", "attempt-1", 1, "read_requirement")
        retried = tool_evidence_reference("task-a", "attempt-2", 0, "read_requirement")

        self.assertEqual(len({first, second, retried}), 3)

    def test_failed_same_name_call_does_not_consume_later_success_record(self):
        record = {
            "task_id": "task-a",
            "tool_call_index": 1,
            "tool_name": "update_test_case_draft",
            "mutation_fingerprint": "verified-second-call",
        }
        observations = [
            {
                "task_id": "task-a",
                "tool_call_index": 0,
                "tool_name": "update_test_case_draft",
                "status": "FAILED",
            },
            {
                "task_id": "task-a",
                "tool_call_index": 1,
                "tool_name": "update_test_case_draft",
                "status": "COMPLETED",
            },
        ]

        matched = tool_call_records_for_observations([record], observations)

        self.assertEqual(matched, [{}, record])

    def test_legacy_calls_match_only_observations_without_call_identity(self):
        first = {"tool_name": "read_requirement", "read_fingerprint": "first"}
        second = {"tool_name": "read_requirement", "read_fingerprint": "second"}

        matched = tool_call_records_for_observations(
            [first, second],
            [
                {"tool_name": "read_requirement", "status": "COMPLETED"},
                {"tool_name": "read_requirement", "status": "COMPLETED"},
            ],
        )

        self.assertEqual(matched, [first, second])

    def test_retried_task_call_uses_its_execution_batch(self):
        first_attempt = {
            "task_id": "task-a",
            "tool_call_index": 0,
            "tool_call_batch_id": "attempt-1",
            "tool_name": "update_test_case_draft",
            "mutation_fingerprint": "first-attempt",
        }
        second_attempt = {
            "task_id": "task-a",
            "tool_call_index": 0,
            "tool_call_batch_id": "attempt-2",
            "tool_name": "update_test_case_draft",
            "mutation_fingerprint": "second-attempt",
        }
        observations = [
            {
                "task_id": "task-a",
                "tool_call_index": 0,
                "tool_call_batch_id": "attempt-1",
                "tool_name": "update_test_case_draft",
            },
            {
                "task_id": "task-a",
                "tool_call_index": 0,
                "tool_call_batch_id": "attempt-2",
                "tool_name": "update_test_case_draft",
            },
        ]

        matched = tool_call_records_for_observations(
            [first_attempt, second_attempt], observations
        )

        self.assertEqual(matched, [first_attempt, second_attempt])

    def test_duplicate_identity_is_rejected_as_ambiguous(self):
        records = [
            {
                "task_id": "task-a",
                "tool_call_index": 0,
                "tool_call_batch_id": "attempt-1",
                "tool_name": "update_test_case_draft",
            },
            {
                "task_id": "task-a",
                "tool_call_index": 0,
                "tool_call_batch_id": "attempt-1",
                "tool_name": "update_test_case_draft",
            },
        ]
        observation = {
            "task_id": "task-a",
            "tool_call_index": 0,
            "tool_call_batch_id": "attempt-1",
            "tool_name": "update_test_case_draft",
        }

        self.assertEqual(tool_call_records_for_observations(records, [observation]), [{}])


if __name__ == "__main__":
    unittest.main()
