"""Isolated action proposal validation tests."""
import json
import unittest

from reference.integration_directory import IntegrationDirectory, Integration
from reference.capability_requirements import RequirementCatalog, OperationRequirement
from reference.model_action_proposal import parse_model_proposal, ProposalError
from reference.capability_arguments import canonical_arguments


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.directory = IntegrationDirectory()
        self.directory.register(Integration("sample", "Sample", ("mcp",),
                                            ("items.read", "items.write")))
        self.directory.bind("sample", connection_id="example", transport="mcp")
        self.requirements = RequirementCatalog()
        for op, risk in (("items.read", "read"), ("items.write", "write")):
            self.requirements.register(OperationRequirement("sample", op, risk,
                                                            ("mcp",), "v1"))
        self.data = dict(schema="goreecloud.ai.action-proposal.v1",
                         service="sample", operation="items.read",
                         resource="list:demo", arguments={"limit": 3})
        self.options = dict(request_id="req-1", directory=self.directory,
                            requirements=self.requirements,
                            permitted_services=frozenset({"sample"}),
                            permitted_operations=frozenset({"sample:items.read"}))

    def parse(self, value=None):
        content = json.dumps(self.data if value is None else value)
        return parse_model_proposal(content, **self.options)

    def test_proposal_is_not_authorization(self):
        result = self.parse()
        self.assertEqual(result.intent.request_id, "req-1")
        self.assertEqual(result.intent.arguments_sha256,
                         canonical_arguments({"limit": 3}).sha256)
        self.assertEqual(result.redacted_preview()["status"],
                         "proposed_not_authorized")
        self.assertNotIn("list:demo", repr(result.redacted_preview()))

    def test_model_claims_are_rejected(self):
        for item in ("approved", "request_id", "risk", "tenant"):
            with self.assertRaisesRegex(ProposalError, "invalid_proposal"):
                self.parse({**self.data, item: True})

    def test_ungranted_actions_are_unavailable(self):
        with self.assertRaisesRegex(ProposalError, "capability_unavailable"):
            self.parse({**self.data, "operation": "items.write"})
        self.directory.disable("sample")
        with self.assertRaisesRegex(ProposalError, "capability_unavailable"):
            self.parse()

    def test_malformed_fields(self):
        for item in ({"resource": ""}, {"arguments": []},
                     {"resource": "\n"}):
            with self.assertRaisesRegex(ProposalError, "invalid_proposal"):
                self.parse({**self.data, **item})

    def test_oversized_input(self):
        with self.assertRaisesRegex(ProposalError, "proposal_too_large"):
            self.parse({**self.data, "arguments": {"large": "x" * 65536}})

    def test_duplicate_keys_and_nonjson(self):
        for raw in ('{"schema":"x","schema":"y"}', "Not JSON"):
            with self.assertRaisesRegex(ProposalError, "invalid_proposal"):
                parse_model_proposal(raw, **self.options)


if __name__ == "__main__":
    unittest.main()
