"""Adversarial tests for the non-executing model-to-policy handoff."""
import dataclasses
import unittest
from test_proposal_policy_handoff import HandoffTests
from reference.proposal_policy_handoff import HandoffError, InputRule, prepare_plan

class HandoffDenialTests(unittest.TestCase):
    def setUp(self):
        self.h = HandoffTests()
        self.h.setUp()

    def test_changed_payload_digest(self):
        self.h.proposal.arguments["limit"] = 3
        with self.assertRaisesRegex(HandoffError, "arguments_changed"):
            self.h.plan()

    def test_target_substitution(self):
        with self.assertRaisesRegex(HandoffError, "target_denied"):
            self.h.plan(target_resource="list:other")

    def test_swapped_connector_binding(self):
        self.h.directory.bind("sample", connection_id="replacement",
                              transport="mcp")
        with self.assertRaisesRegex(HandoffError, "capability_changed"):
            self.h.plan()

    def test_unexpected_arguments(self):
        for args in ({"limit": True}, {"limit": "2"},
                     {"limit": 2, "unknown": True}, {}):
            draft = dataclasses.replace(self.h.proposal, arguments=args)
            with self.assertRaisesRegex(HandoffError, "invalid_arguments"):
                prepare_plan(draft, self.h.directory, self.h.requirements,
                             rules=self.h.rules, target_resource="list:mine",
                             expected_revision="v1", expected_connection="test-link",
                             expected_transport="mcp",
                             identity=self.h.identity, policy=self.h.policy,
                             now=1000)

    def test_policy_and_contract_changes(self):
        with self.assertRaisesRegex(HandoffError, "policy_denied"):
            self.h.plan(policy=dataclasses.replace(
                self.h.policy, tenant="other"))
        with self.assertRaisesRegex(HandoffError, "capability_changed"):
            self.h.plan(expected_revision="v2")
        with self.assertRaisesRegex(HandoffError, "invalid_arguments"):
            self.h.plan(rules=(InputRule("missing", "boolean"),))

if __name__ == "__main__":
    unittest.main()
