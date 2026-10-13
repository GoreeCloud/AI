"""Offline redaction check for local-only conversation turn index."""
import unittest
import test_local_chat_controls as controls

class RedactedTurnIndexTests(unittest.TestCase):
    def test_private_prompt_text_never_appears_in_index(self):
        harness = controls.ConsoleControlTests("test_missing_model_does_not_discard_context")
        harness.setUp()
        try:
            result = harness.run_console("private-alpha\nprivate-beta\n/turns\n/delete 1\n/turns\n/exit\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Completed local turn numbers: 1, 2", result.stdout)
            self.assertIn("Completed local turn numbers: 1", result.stdout)
            self.assertNotIn("private-alpha", result.stdout)
            self.assertNotIn("private-beta", result.stdout)
            self.assertEqual(len(harness.server.requests), 2)
        finally:
            harness.tearDown()

if __name__ == "__main__":
    unittest.main()
