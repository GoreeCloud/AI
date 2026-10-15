"""Offline SQLite request-replay reservation tests. No tools or services are called."""
import dataclasses
import hashlib
import os
import sqlite3
import tempfile
import unittest

from reference.capability_authorization import (
    CapabilityIntent, PolicyEvidence, VerifiedIdentity, authorize,
)
from reference.capability_replay_ledger import ReplayError, ReplayLedger, Reservation
from reference.capability_requirements import OperationRequirement, RequirementCatalog
from reference.integration_directory import IntegrationDirectory, Integration


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, "replay.db")
        self.connection = self.open_connection()
        self.addCleanup(self.connection.close)
        self.ledger = ReplayLedger(self.connection)

        directory = IntegrationDirectory()
        directory.register(Integration("example", "Example", ("mcp",), ("objects.write",)))
        directory.bind("example", connection_id="backend-binding", transport="mcp")
        requirements = RequirementCatalog()
        requirements.register(OperationRequirement("example", "objects.write", "write",
                                                   ("mcp",), "manifest-v1"))
        intent = CapabilityIntent("request-1", "example", "objects.write",
                                  "objects/private-resource",
                                  hashlib.sha256(b'{"value":"secret"}').hexdigest())
        identity = VerifiedIdentity("subject-1", "tenant-1", "session-1", 1080)
        policy = PolicyEvidence("request-1", "subject-1", "tenant-1", "example",
                                "objects.write", "objects/private-resource",
                                intent.arguments_sha256, "allow", "write", "policy-v1",
                                1050, frozenset({"example"}),
                                frozenset({"example:objects.write"}))
        from reference.capability_authorization import ApprovalEvidence
        approval = ApprovalEvidence("request-1", "subject-1", "tenant-1",
                                    "session-1", "example", "objects.write",
                                    "objects/private-resource",
                                    intent.arguments_sha256, 1040, True)
        self.plan = authorize(directory, requirements, intent,
                              identity=identity, policy=policy, approval=approval, now=1000)

    def open_connection(self):
        return sqlite3.connect(self.path, timeout=1, isolation_level=None)

    def test_atomic_reservation_blocks_duplicate(self):
        reservation = self.ledger.reserve(self.plan, now=1000)
        self.assertEqual(self.ledger.status(reservation), "reserved")
        with self.assertRaisesRegex(ReplayError, "replay_detected"):
            self.ledger.reserve(self.plan, now=1001)
        self.assertEqual(self.ledger.status(reservation), "reserved")

    def test_replay_is_blocked_after_reopening_same_file(self):
        reservation = self.ledger.reserve(self.plan, now=1000)
        self.ledger.resolve(reservation, outcome="succeeded", now=1001)
        other = self.open_connection()
        try:
            other_ledger = ReplayLedger(other)
            self.assertEqual(other_ledger.status(reservation), "succeeded")
            with self.assertRaisesRegex(ReplayError, "replay_detected"):
                other_ledger.reserve(self.plan, now=1010)
        finally:
            other.close()

    def test_failed_and_unknown_outcomes_still_block_replay(self):
        for i, state in enumerate(("failed", "unknown")):
            plan = dataclasses.replace(self.plan, request_id=f"request-{i + 2}")
            reservation = self.ledger.reserve(plan, now=1000)
            self.ledger.resolve(reservation, outcome=state, now=1002)
            self.assertEqual(self.ledger.status(reservation), state)
            with self.assertRaisesRegex(ReplayError, "replay_detected"):
                self.ledger.reserve(plan, now=1003)

    def test_changed_context_cannot_reuse_request_id(self):
        self.ledger.reserve(self.plan, now=1000)
        for replacement in (
            dataclasses.replace(self.plan, session="session-2"),
            dataclasses.replace(self.plan, resource="objects/other"),
            dataclasses.replace(self.plan, arguments_sha256="a" * 64),
            dataclasses.replace(self.plan, requirement_revision="manifest-v2"),
        ):
            with self.assertRaisesRegex(ReplayError, "replay_detected"):
                self.ledger.reserve(replacement, now=1001)

    def test_tenants_are_separated_but_request_reuse_within_tenant_is_not(self):
        first = self.ledger.reserve(self.plan, now=1000)
        second = self.ledger.reserve(dataclasses.replace(self.plan, tenant="tenant-2"),
                                     now=1001)
        self.assertNotEqual(first.key_hash, second.key_hash)
        self.assertEqual(self.ledger.status(second), "reserved")

    def test_immutable_terminal_state_and_matching_digest_required(self):
        reservation = self.ledger.reserve(self.plan, now=1000)
        with self.assertRaisesRegex(ReplayError, "reservation_unavailable"):
            self.ledger.resolve(dataclasses.replace(reservation, request_hash="0" * 64),
                                outcome="succeeded", now=1001)
        with self.assertRaisesRegex(ReplayError, "reservation_unavailable"):
            self.ledger.resolve(reservation, outcome="succeeded", now=999)
        self.ledger.resolve(reservation, outcome="unknown", now=1001)
        with self.assertRaisesRegex(ReplayError, "reservation_unavailable"):
            self.ledger.resolve(reservation, outcome="succeeded", now=1002)

    def test_invalid_args_fail_closed(self):
        with self.assertRaisesRegex(ReplayError, "invalid_plan"):
            self.ledger.reserve("fake", now=1000)
        with self.assertRaisesRegex(ReplayError, "invalid_clock"):
            self.ledger.reserve(self.plan, now=True)
        with self.assertRaisesRegex(ReplayError, "invalid_reservation"):
            self.ledger.status(Reservation("invalid", "0" * 64))
        receipt = self.ledger.reserve(self.plan, now=1000)
        with self.assertRaisesRegex(ReplayError, "invalid_outcome"):
            self.ledger.resolve(receipt, outcome="retry", now=1000)

    def test_backend_database_failure_is_not_silent(self):
        self.connection.execute("DROP TABLE capability_request_reservations")
        with self.assertRaisesRegex(ReplayError, "ledger_unavailable"):
            self.ledger.reserve(self.plan, now=1000)

    def test_ledger_persists_only_hashes_and_execution_state(self):
        receipt = self.ledger.reserve(self.plan, now=1000)
        self.assertEqual(len(receipt.key_hash), 64)
        sql = self.connection.execute(
            "SELECT key_hash, request_hash, state, reserved_at "
            "FROM capability_request_reservations").fetchall()
        self.assertEqual(len(sql), 1)
        self.assertNotIn("objects/private-resource", repr(sql))
        self.assertNotIn("backend-binding", repr(sql))
        self.assertNotIn("subject-1", repr(sql))
        self.assertNotIn(self.plan.arguments_sha256, repr(sql))


if __name__ == "__main__":
    unittest.main()
