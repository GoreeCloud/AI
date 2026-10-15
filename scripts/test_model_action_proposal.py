"""Synthetic fail-closed model proposal tests; no external services."""
import hashlib
import json
import unittest

from reference.capability_arguments import canonical_arguments
from reference.integration_directory import IntegrationDirectory, Integration
from reference.capability_requirements import RequirementCatalog, OperationRequirement
from reference.model_action_proposal import ProposalError, parse_model_proposal

SCHEMA = "goreecloud.ai.action-proposal.v1"


class ModelProposalTests(unittest.TestCase):
    def setUp(self):
        self.directory = IntegrationDirectory()
        self.directory.register(Integration("example", "Example", ("mcp",), 
                                            ("items.read", "items.write")))
        self.directory.register(Integration("hidden", "Hidden", ("mcp",),
                                            ("items.read",)))
        self.directory.bind("example", connection_id="private-connection", transport="mcp")
        self.requirements = RequirementCatalog()
        for svc, op, risk in (("example", "items.read", "read"),
                              ("example", "items.write", "write"),
                              ("hidden", "items.read", "read")):
            self.requirements.register(OperationRequirement(svc, op, risk,
                                                            ("mcp",), "v1"))
        self.permitted_services = frozenset({"example"})
        self.permitted_operations = frozenset({"example:items.read"})
        self.payload = {"schema": SCHEMA, "service": "example",
                        "operation": "items.read", "resource": "list:sample",
                        "arguments": {"limit": 5}}

    def parse(self, response=None, **overrides):
        kwargs = dict(request_id="backend-req-1", directory=self.directory,
                      requirements=self.requirements,
                      permitted_services=self.permitted_services,
                      permitted_operations=self.permitted_operations)
        kwargs.update(overrides)
        return parse_model_proposal(
            json.dumps(self.payload if response is None else response)
            if not isinstance(response, str) else response, **kwargs
        )

    def test_draft_is_backend_identified_and_argument_bound(self):
        draft = self.parse()
        self.assertEqual(draft.intent.request_id, "backend-req-1")
        self.assertEqual(draft.intent.arguments_sha256,
                         canonical_arguments({"limit": 5}).sha256)
        self.assertEqual(draft.minimum_risk, "read")
        preview = draft.redacted_preview()
        self.assertNotIn("private-connection", repr(preview))
        self.assertNotIn("list:sample", repr(preview))
        self.assertNotIn("'limit': 5", repr(preview))
        self.assertEqual(preview["status"], "proposed_not_authorized")

    def test_reject_model_claims_to_permissions_or_approval(self):
        for extra in ("approved", "risk", "tenant", "request_id",
                      "credentials", "tool_calls", "policy"):
            with self.subTest(extra=extra), self.assertRaisesRegex(
                    ProposalError, "invalid_proposal"):
                self.parse({**self.payload, extra: True})

    def test_inaccessible_disconnected_or_unmanifested_tools_denied(self):
        attempts = (("example", "items.write"),
                    ("hidden", "items.read"),
                    ("ghost", "items.read"))
        for service, operation in attempts:
            with self.subTest(service=service, operation=operation):
                with self.assertRaisesRegex(ProposalError, "capability_unavailable"):
                    self.parse({**self.payload, "service": service,
                                "operation": operation})
        self.directory.disable("example")
        with self.assertRaisesRegex(ProposalError, "capability_unavailable"):
            self.parse()

    def test_duplicate_keys_markdown_and_nonfinite_rejected(self):
        for raw in (
            '{"schema":"goreecloud.ai.action-proposal.v1","schema":"x"}',
            "Here is JSON: " + json.dumps(self.payload),
            "json\n" + json.dumps(self.payload),
            '{"schema":"goreecloud.ai.action-proposal.v1",'
            '"service":"example","operation":"items.read",'
            '"resource":"sample","arguments":{"a":NaN}}',
        ):
            with self.subTest(raw=raw[:35]), self.assertRaisesRegex(
                    ProposalError, "invalid_proposal"):
                self.parse(raw)

    def test_extra_nested_arg_values_are_not_approvals(self):
        draft = self.parse({**self.payload,
                            "arguments": {"approved": True, "limit": 5}})
        self.assertNotEqual(draft.intent.arguments_sha256,
                            canonical_arguments({"limit": 5}).sha256)
        self.assertEqual(draft.redacted_preview()["status"],
                         "proposed_not_authorized")

    def test_invalid_resource_and_args_are_denied(self):
        for change in (
            {"resource": "\n"},
            {"resource": ""},
            {"resource": "x" * 513},
            {"arguments": ["wrong"]},
            {"arguments": {"large": "x" * 65536}},
        ):
            with self.assertRaisesRegex(ProposalError, "invalid_proposal"):
                self.parse({**self.payload, **change})

    def test_oversized_or_invalid_backend_id(self):
        with self.assertRaisesRegex(ProposalError, "proposal_too_large"):
            self.parse(json.dumps(self.payload) + " " * 65536)
        with self.assertRaisesRegex(ProposalError, "invalid_proposal"):
            self.parse(request_id="malformed id")

    def test_malformed_grants_rejected(self):
        with self.assertRaisesRegex(ProposalError, "invalid_input"):
            self.parse(permitted_services={"example"})


if __name__ == "__main__":
    unittest.main()
