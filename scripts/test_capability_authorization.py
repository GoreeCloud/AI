"""Isolated fail-closed capability broker tests, with synthetic evidence only."""
import dataclasses
import hashlib
import unittest

from reference.capability_authorization import (
    ApprovalEvidence, AuthorizationError, CapabilityIntent, PolicyEvidence,
    VerifiedIdentity, authorize,
)
from reference.integration_directory import example_directory


class GateTests(unittest.TestCase):
    def setUp(self):
        self.directory = example_directory()
        self.directory.bind("github", connection_id="test-connection", transport="mcp")
        self.intent = CapabilityIntent("req-1", "github", "repos.read", "repo:sample/demo",
                                       hashlib.sha256(b'{"page":1}').hexdigest())
        self.identity = VerifiedIdentity("person-1", "tenant-1", "session-1", 1100)
        self.policy = PolicyEvidence(
            self.intent.request_id, self.identity.subject, self.identity.tenant,
            self.intent.service, self.intent.operation, self.intent.resource,
            self.intent.arguments_sha256, "allow", "read", "policy-v1", 1050,
            frozenset({"github"}), frozenset({"github:repos.read"}),
        )

    def check_error(self, expected, **overrides):
        args = dict(identity=self.identity, policy=self.policy, now=1000)
        args.update(overrides)
        with self.assertRaises(AuthorizationError) as cm:
            authorize(self.directory, self.intent, **args)
        self.assertEqual(cm.exception.code, expected)

    def test_read_with_exact_fresh_grants(self):
        receipt = authorize(self.directory, self.intent, identity=self.identity,
                            policy=self.policy, now=1000)
        self.assertEqual((receipt.route.service, receipt.route.transport), ("github", "mcp"))
        self.assertEqual(receipt.policy_revision, "policy-v1")

    def test_missing_stale_and_mismatched_identity(self):
        self.check_error("identity_unverified", identity=None)
        self.check_error("identity_unverified", identity=dataclasses.replace(self.identity, expires_at=1000))
        self.check_error("policy_denied", identity=dataclasses.replace(self.identity, tenant="other-tenant"))

    def test_fail_closed_policy_states(self):
        for decision in ("deny", "conditional", "unknown", "defer", "error", "indeterminate"):
            self.check_error("policy_denied", policy=dataclasses.replace(self.policy, decision=decision))
        self.check_error("policy_denied", policy=dataclasses.replace(self.policy, expires_at=1000))
        self.check_error("policy_denied", policy=dataclasses.replace(self.policy, expires_at=999999))
        self.check_error("policy_denied", policy=dataclasses.replace(self.policy, policy_revision=""))

    def test_exact_request_and_arguments_binding(self):
        for name, value in (("request_id", "req-2"), ("resource", "repo:someone/else"),
                            ("service", "gmail"), ("operation", "pulls.write"),
                            ("arguments_sha256", "0" * 64)):
            self.check_error("policy_denied", policy=dataclasses.replace(self.policy, **{name: value}))
        self.check_error("capability_unavailable", policy=dataclasses.replace(
            self.policy, permitted_operations=frozenset()))

    def test_no_connected_service_no_route(self):
        self.directory.disable("github")
        self.check_error("capability_unavailable")

    def test_write_requires_approval_bound_to_request_and_args(self):
        intent = dataclasses.replace(self.intent, operation="issues.write")
        policy = dataclasses.replace(self.policy, operation="issues.write", risk="write",
                                     permitted_operations=frozenset({"github:issues.write"}))
        with self.assertRaisesRegex(AuthorizationError, "approval_required"):
            authorize(self.directory, intent, identity=self.identity, policy=policy, now=1000)
        approved = ApprovalEvidence(intent.request_id, self.identity.subject,
                                    self.identity.tenant, intent.arguments_sha256, 1030, True)
        for data in (dataclasses.replace(approved, approved=False),
                     dataclasses.replace(approved, arguments_sha256="f" * 64),
                     dataclasses.replace(approved, expires_at=1000),
                     dataclasses.replace(approved, tenant="other-tenant")):
            with self.assertRaisesRegex(AuthorizationError, "approval_required"):
                authorize(self.directory, intent, identity=self.identity, policy=policy,
                          approval=data, now=1000)
        receipt = authorize(self.directory, intent, identity=self.identity, policy=policy,
                            approval=approved, now=1000)
        self.assertEqual(receipt.risk, "write")
        self.assertEqual(receipt.route.operation, "issues.write")

    def test_invalid_requests(self):
        with self.assertRaisesRegex(AuthorizationError, "invalid_intent"):
            CapabilityIntent("req-1", "github", "repos.read", "\n", self.intent.arguments_sha256)
        with self.assertRaisesRegex(AuthorizationError, "invalid_intent"):
            CapabilityIntent("req-1", "github", "repos.read", "repo", "not-a-sha")
        self.check_error("invalid_clock", now=True)
        self.check_error("invalid_clock", now=-5)


if __name__ == "__main__":
    unittest.main()
