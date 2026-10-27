import unittest

from src.tools.requirement_document_workflow import (
    process_ingested_requirement_document,
    uncovered_blueprint_obligations,
)


class RequirementDocumentObligationBindingTests(unittest.TestCase):
    def test_ingestion_workflow_uses_module_obligation_checker(self):
        code = process_ingested_requirement_document.coroutine.__code__

        self.assertNotIn("uncovered_blueprint_obligations", code.co_varnames)
        self.assertIn("uncovered_blueprint_obligations", code.co_names)

        obligations = [{"key": "OBL-1"}]
        self.assertEqual(
            uncovered_blueprint_obligations(obligations, [], {}, set()),
            obligations,
        )


if __name__ == "__main__":
    unittest.main()
