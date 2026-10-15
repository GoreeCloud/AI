"""Offline proposal boundary contract tests."""
import unittest
from reference.local_action_planner import LocalProposalError, propose_with_local_ollama

class PlannerSmokeTests(unittest.TestCase):
    def test_reject_invalid_runtime(self):
        with self.assertRaisesRegex(LocalProposalError, 'invalid_runtime'):
            propose_with_local_ollama(None, 'example:latest', 'Request', request_id='req-1', directory=None, requirements=None, permitted_services=frozenset(), permitted_operations=frozenset())

if __name__ == '__main__':
    unittest.main()
