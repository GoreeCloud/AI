"""Synthetic two-stage review/approval regression tests; no service execution."""
import dataclasses
import json
import sqlite3
import unittest

from reference.capability_arguments import canonical_arguments
from reference.capability_authorization import (
    ApprovalEvidence, PolicyEvidence, VerifiedIdentity,
)
from reference.capability_replay_ledger import ReplayLedger
from reference.capability_requirements import OperationRequirement, RequirementCatalog
from reference.integration_directory import Integration, IntegrationDirectory
from reference.local_model_gateway import ChatResult, LocalOllamaGateway
from reference.local_review_lifecycle import (
    ReviewError, draft_local_review, reserve_reviewed_action,
)
from reference.proposal_policy_handoff import InputRule


class StubOllama(LocalOllamaGateway):
    def __init__(self, content):
        self.content = content
        self.calls = []

    def chat(self, model, messages, *, max_tokens=None):
        self.calls.append((model, messages, max_tokens))
        return ChatResult("ollama", model, "local", self.content)


class ReviewLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.ledger = ReplayLedger(self.db)
        self.directory = IntegrationDirectory()
        self.directory.register(Integration("sample", "Sample", ("mcp",),
                                            ("items.read", "items.write")))
        self.directory.bind("sample", connection_id="connector-a", transport="mcp")
        self.requirements = RequirementCatalog()
        for operation, risk in (("items.read", "read"), ("items.write", "write")):
            self.requirements.register(OperationRequirement(
                "sample", operation, risk, ("mcp",), "v1"))
        self.identity = VerifiedIdentity("subject", "tenant", "session", 1500)
        self.rules = (InputRule("count", "integer"),)
        self.operation = "items.read"
        self.model = StubOllama("")
        self.options = dict(
            request_id="req-1", directory=self.directory,
            requirements=self.requirements,
            permitted_services=frozenset({"sample"}),
            permitted_operations=frozenset({"sample:items.read", "sample:items.write"}),
            rules=self.rules, target_resource="list:mine", expected_revision="v1",
            expected_connection="connector-a", expected_transport="mcp",
            identity=self.identity, now=1000,
        )
        self.update_model()

    def update_model(self):
        self.model.content = json.dumps(dict(
            schema="goreecloud.ai.action-proposal.v1",
            service="sample", operation=self.operation,
            resource="list:mine", arguments={"count": 2}))

    def draft(self, **updates):
        opts = dict(self.options)
        opts.update(updates)
        return draft_local_review(self.model, "sample:latest", "List two items", **opts)

    def policy(self, review, risk=None):
        return PolicyEvidence(
            review.proposal.intent.request_id,
            "subject", "tenant", "sample", self.operation, "list:mine",
            canonical_arguments({"count": 2}).sha256,
            "allow", risk or ("write" if self.operation == "items.write" else "read"),
            "policy-v1", 1090, frozenset({"sample"}),
            frozenset({"sample:" + self.operation}),
        )

    def finalize(self, review, **updates):
        opts = dict(
            policy=self.policy(review), approval=None, identity=self.identity,
            rules=self.rules, ledger=self.ledger, now=1010,
        )
        opts.update(updates)
        return reserve_reviewed_action(
            review, self.directory, self.requirements, **opts)

    def reserved(self):
        return self.db.execute(
            "SELECT COUNT(*) FROM capability_request_reservations").fetchone()[0]

    def test_two_distinct_stages_no_early_reservation(self):
        review = self.draft()
        visible = review.display()
        self.assertEqual(visible["status"], "awaiting_user_review")
        self.assertEqual(visible["execution"], "disabled")
        self.assertEqual(visible["target"], "list:mine")
        self.assertEqual(visible["arguments"], {"count": 2})
        self.assertEqual(self.reserved(), 0)
        result = self.finalize(review).redacted()
        self.assertEqual(result["status"], "reserved_no_execution")
        self.assertEqual(result["execution"], "disabled")
        self.assertEqual(self.reserved(), 1)
        self.assertEqual(len(self.model.calls), 1)

    def test_write_needs_consent_after_drafting(self):
        self.operation = "items.write"
        self.update_model()
        review = self.draft()
        self.assertEqual(review.risk, "write")
        self.assertEqual(self.reserved(), 0)
        with self.assertRaisesRegex(ReviewError, "approval_required"):
            self.finalize(review)
        self.assertEqual(self.reserved(), 0)
        receipt = ApprovalEvidence(
            "req-1", "subject", "tenant", "session", "sample",
            "items.write", "list:mine",
            review.proposal.intent.arguments_sha256, 1060, True)
        self.assertEqual(self.finalize(review, approval=receipt).risk, "write")
        self.assertEqual(len(self.model.calls), 1)

    def test_second_finalization_is_replay(self):
        review = self.draft()
        self.finalize(review)
        with self.assertRaisesRegex(ReviewError, "replay_detected"):
            self.finalize(review)
        self.assertEqual(self.reserved(), 1)

    def test_changed_review_payload_and_resource_are_denied(self):
        review = self.draft()
        review.proposal.arguments["count"] = 3
        with self.assertRaisesRegex(ReviewError, "arguments_changed"):
            self.finalize(review)
        self.assertEqual(self.reserved(), 0)

    def test_session_and_review_expiration(self):
        review = self.draft()
        with self.assertRaisesRegex(ReviewError, "review_expired_or_changed"):
            self.finalize(review, identity=dataclasses.replace(
                self.identity, session="different"))
        with self.assertRaisesRegex(ReviewError, "review_expired_or_changed"):
            self.finalize(review, now=review.expires_at)
        self.assertEqual(self.reserved(), 0)

    def test_binding_drift_or_policy_downgrade(self):
        review = self.draft()
        self.directory.bind("sample", connection_id="connector-b", transport="mcp")
        with self.assertRaisesRegex(ReviewError, "capability_changed"):
            self.finalize(review)
        self.assertEqual(self.reserved(), 0)

    def test_policy_escalation_requires_new_review(self):
        review = self.draft()
        with self.assertRaisesRegex(ReviewError, "approval_required"):
            self.finalize(review, policy=self.policy(review, risk="sensitive"))
        self.assertEqual(self.reserved(), 0)


if __name__ == "__main__":
    unittest.main()
