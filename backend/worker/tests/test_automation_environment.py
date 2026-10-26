import unittest

from src.jobs.task import automation_environment


class AutomationEnvironmentTests(unittest.TestCase):
    def test_preserves_runtime_paths_and_accepts_regular_test_values(self):
        environment = automation_environment(
            "/tmp/veriq-run",
            {
                "PATH": "/tmp/untrusted-bin",
                "HOME": "/tmp/untrusted-home",
                "API_BASE_URL": "https://example.test",
                "TEST_USER": "runner",
            },
        )

        self.assertEqual(environment["PATH"], "/usr/local/bin:/usr/bin:/bin")
        self.assertEqual(environment["HOME"], "/tmp/veriq-run")
        self.assertEqual(environment["API_BASE_URL"], "https://example.test")
        self.assertEqual(environment["TEST_USER"], "runner")

    def test_drops_runtime_injection_and_dynamic_loader_variables(self):
        environment = automation_environment(
            "/tmp/veriq-run",
            {
                "NODE_OPTIONS": "--require=/tmp/inject.js",
                "PYTHONPATH": "/tmp/inject",
                "LD_PRELOAD": "/tmp/inject.so",
                "DYLD_INSERT_LIBRARIES": "/tmp/inject.dylib",
                "safe_value": "accepted",
            },
        )

        self.assertNotIn("NODE_OPTIONS", environment)
        self.assertNotIn("PYTHONPATH", environment)
        self.assertNotIn("LD_PRELOAD", environment)
        self.assertNotIn("DYLD_INSERT_LIBRARIES", environment)
        self.assertEqual(environment["safe_value"], "accepted")
