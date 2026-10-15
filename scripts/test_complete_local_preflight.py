"""Synthetic non-executing capability flow: local model -> policy -> replay."""
import dataclasses
import hashlib
import json
import sqlite3
import unittest

from reference.capability_arguments import canonical_arguments
from reference.capability_authorization import ApprovalEvidence, PolicyEvidence, VerifiedIdentity
from reference.capability_replay_ledger import ReplayLedger
from reference.capability_requirements import OperationRequirement, RequirementCatalog
from reference.integration_directory import Integration, IntegrationDirectory
from reference.local_model_gateway import ChatResult, LocalOllamaGateway
from reference.local_preflight_pipeline import PreflightError, simulate_local_preflight
from reference.proposal_policy_handoff import InputRule


class StubModel(LocalOllamaGateway):
    def __init__(self, content):
        self.content = content
        self.calls = []

    def chat(self, model, messages, *, max_tokens=None):
        self.calls.append((model, messages, max_tokens))
        return ChatResult("ollama", model, "local", self.content)


class CompletePreflightTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.ledger = ReplayLedger(self.db)
        self.directory = IntegrationDirectory()
        self.directory.register(Integration("sample", "Sample", ("mcp",),
                                            ("items.read", "items.write")))
        self.directory.bind("sample", connection_id="connector-a", transport="mcp")
        self.requirements = RequirementCatalog()
        for op, risk in (("items.read", "read"), ("items.write", "write")):
            self.requirements.register(OperationRequirement(
                "sample", op, risk, ("mcp",), "v1"))
        self.identity = VerifiedIdentity("subject", "tenant", "session", 1050)
        self.response = dict(
            schema="goreecloud.ai.action-proposal.v1",
            service="sample", operation="items.read",
            resource="list:mine", arguments={"count": 2},
        )
        self.runtime = StubModel(json.dumps(self.response))
        self.policy = self.make_policy("items.read", "read")
        self.options = dict(
            request_id="req-1",
            directory=self.directory, requirements=self.requirements,
            permitted_services=frozenset({"sample"}),
            permitted_operations=frozenset({"sample:items.read"}),
            rules=(InputRule("count", "integer"),),
            target_resource="list:mine",
            expected_revision="v1", expected_connection="connector-a",
            expected_transport="mcp",
            identity=self.identity, policy=self.policy,
            ledger=self.ledger, now=1000,
        )

    def make_policy(self, operation, risk):
        return PolicyEvidence(
            "req-1", "subject", "tenant", "sample", operation, "list:mine",
            canonical_arguments({"count": 2}).sha256,
            "allow", risk, "policy-v1", 1020, frozenset({"sample"}),
            frozenset({"sample:" + operation}),
        )

    def run_flow(self, **updates):
        args = dict(self.options)
        args.update(updates)
        return simulate_local_preflight(
            self.runtime, "sample:latest", "List two items", **args)

    def count_reservations(self):
        return self.db.execute(
            "SELECT COUNT(*) FROM capability_request_reservations").fetchone()[0]

    def test_read_preflight_reserves_but_does_not_execute(self):
        preview = self.run_flow().redacted()
        self.assertEqual(preview["status"], "reserved_no_execution")
        self.assertEqual(preview["execution"], "disabled")
        self.assertEqual(preview["risk"], "read")
        self.assertEqual(preview["argument_count"], 1)
        self.assertEqual(self.count_reservations(), 1)
        self.assertEqual(len(self.runtime.calls), 1)
        self.assertNotIn("connector-a", repr(preview))
        self.assertNotIn("list:mine", repr(preview))
        self.assertNotIn("count", repr(preview))

    def test_replay_rejected_even_after_identical_model_reply(self):
        self.run_flow()
        with self.assertRaisesRegex(PreflightError, "replay_detected"):
            self.run_flow()
        self.assertEqual(self.count_reservations(), 1)

    def test_policy_denial_and_expired_identity_stop_before_model(self):
        for changed in (
            {"policy": dataclasses.replace(self.policy, decision="deny")},
            {"policy": dataclasses.replace(self.policy, expires_at=999)},
            {"identity": dataclasses.replace(self.identity, expires_at=1000)},
            {"identity": dataclasses.replace(self.identity, tenant="other")},
        ):
            with self.assertRaisesRegex(PreflightError, "identity_or_policy_denied"):
                self.run_flow(**changed)
        self.assertEqual(self.runtime.calls, [])
        self.assertEqual(self.count_reservations(), 0)

    def test_write_requires_matching_approval(self):
        self.response["operation"] = "items.write"
        self.runtime.content = json.dumps(self.response)
        policy = self.make_policy("items.write", "write")
        updates = {"policy": policy,
                   "permitted_operations": frozenset({"sample:items.write"})}
        with self.assertRaisesRegex(PreflightError, "approval_required"):
            self.run_flow(**updates)
        self.assertEqual(self.count_reservations(), 0)
        receipt = ApprovalEvidence(
            "req-1", "subject", "tenant", "session",
            "sample", "items.write", "list:mine",
            policy.arguments_sha256, 1010, True)
        result = self.run_flow(approval=receipt, **updates)
        self.assertEqual(result.risk, "write")
        self.assertEqual(self.count_reservations(), 1)

    def test_changed_args_resource_or_connection_does_not_reserve(self):
        for response, changes in (
            ({**self.response, "resource": "list:other"}, {}),
            ({**self.response, "arguments": {"count": 3}}, {}),
            (self.response, {"expected_connection": "old-connection"}),
        ):
            self.runtime.content = json.dumps(response)
            with self.assertRaises(PreflightError):
                self.run_flow(**changes)
        self.assertEqual(self.count_reservations(), 0)

    def test_model_cannot_select_ungranted_operation(self):
        self.runtime.content = json.dumps({**self.response,
                                           "operation": "items.write"})
        with self.assertRaisesRegex(PreflightError, "capability_unavailable"):
            self.run_flow()
        self.assertEqual(self.count_reservations(), 0)


if __name__ == "__main__":
    unittest.main()
