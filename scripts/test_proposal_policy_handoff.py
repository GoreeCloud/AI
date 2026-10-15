"""Offline proposal-to-policy end-to-end planning tests."""
import dataclasses
import json
import unittest
from reference.capability_authorization import (
    VerifiedIdentity, PolicyEvidence, ApprovalEvidence)
from reference.capability_requirements import RequirementCatalog, OperationRequirement
from reference.integration_directory import IntegrationDirectory, Integration
from reference.model_action_proposal import parse_model_proposal
from reference.proposal_policy_handoff import InputRule, HandoffError, prepare_plan

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.directory = IntegrationDirectory()
        self.directory.register(Integration("sample", "Sample", ("mcp",),
                                            ("items.read", "items.write")))
        self.directory.bind("sample", connection_id="test-link", transport="mcp")
        self.requirements = RequirementCatalog()
        for op, risk in (("items.read", "read"), ("items.write", "write")):
            self.requirements.register(OperationRequirement(
                "sample", op, risk, ("mcp",), "v1"))
        self.identity = VerifiedIdentity("subject", "tenant", "session", 1200)
        self.rules = (InputRule("limit", "integer"),)
        self.make("items.read")

    def make(self, operation):
        data = dict(schema="goreecloud.ai.action-proposal.v1",
                    service="sample", operation=operation, resource="list:mine",
                    arguments={"limit": 2})
        self.proposal = parse_model_proposal(
            json.dumps(data), request_id="req-1", directory=self.directory,
            requirements=self.requirements,
            permitted_services=frozenset({"sample"}),
            permitted_operations=frozenset({"sample:items.read", "sample:items.write"}))
        risk = "write" if operation == "items.write" else "read"
        self.policy = PolicyEvidence(
            "req-1", "subject", "tenant", "sample", operation, "list:mine",
            self.proposal.intent.arguments_sha256, "allow", risk, "policy-v1", 1050,
            frozenset({"sample"}), frozenset({"sample:" + operation}))

    def plan(self, **changes):
        opts = dict(rules=self.rules, target_resource="list:mine",
                    expected_revision="v1", expected_connection="test-link",
                    expected_transport="mcp", identity=self.identity,
                    policy=self.policy, now=1000)
        opts.update(changes)
        return prepare_plan(self.proposal, self.directory, self.requirements,
                            **opts)

    def test_read_is_checked_by_policy_without_effect(self):
        result = self.plan()
        self.assertEqual(result.route.connection_id, "test-link")
        self.assertEqual(result.policy_revision, "policy-v1")

    def test_unapproved_write_is_denied(self):
        self.make("items.write")
        with self.assertRaisesRegex(HandoffError, "approval_required"):
            self.plan()

    def test_write_with_matching_trusted_receipt(self):
        self.make("items.write")
        receipt = ApprovalEvidence(
            "req-1", "subject", "tenant", "session", "sample", "items.write",
            "list:mine", self.proposal.intent.arguments_sha256, 1030, True)
        self.assertEqual(self.plan(approval=receipt).risk, "write")

if __name__ == "__main__":
    unittest.main()
