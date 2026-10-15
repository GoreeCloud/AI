"""Strict scalar, optional and list-contract regressions for local review."""
import dataclasses
import json
import unittest

from reference.capability_arguments import canonical_arguments
from reference.capability_requirements import OperationRequirement, RequirementCatalog
from reference.integration_directory import Integration, IntegrationDirectory
from reference.model_action_proposal import parse_model_proposal
from reference.proposal_policy_handoff import HandoffError, InputRule, check_input


class TypedReviewArgumentsTests(unittest.TestCase):
    def setUp(self):
        self.directory = IntegrationDirectory()
        self.directory.register(Integration("sample", "Sample", ("mcp",), ("items.read",)))
        self.directory.bind("sample", connection_id="synthetic", transport="mcp")
        self.requirements = RequirementCatalog()
        self.requirements.register(OperationRequirement(
            "sample", "items.read", "read", ("mcp",), "v1"))

    def proposal(self, arguments):
        return parse_model_proposal(json.dumps({
            "schema": "goreecloud.ai.action-proposal.v1",
            "service": "sample", "operation": "items.read",
            "resource": "list:mine", "arguments": arguments,
        }), request_id="req-1", directory=self.directory,
            requirements=self.requirements,
            permitted_services=frozenset({"sample"}),
            permitted_operations=frozenset({"sample:items.read"}))

    def test_optional_list_can_be_absent(self):
        draft = self.proposal({"count": 2})
        actual = check_input(draft, (
            InputRule("count", "integer"),
            InputRule("tags", "string_list", False),
        ))
        self.assertEqual(actual, {"count": 2})

    def test_bounded_list_preserves_canonical_hash(self):
        args = {"count": 2, "tags": ["first", "second"]}
        draft = self.proposal(args)
        rules = (InputRule("count", "integer"),
                 InputRule("tags", "string_list", False))
        self.assertEqual(check_input(draft, rules), args)
        self.assertEqual(draft.intent.arguments_sha256, canonical_arguments(args).sha256)

    def test_empty_and_max_size_lists(self):
        rule = (InputRule("tags", "string_list"),)
        for values in ([], ["a"] * 64):
            self.assertEqual(check_input(self.proposal({"tags": values}), rule)["tags"],
                             values)

    def test_missing_required_and_unknown_fields_denied(self):
        for args in ({}, {"count": 2, "unused": True}):
            with self.subTest(args=args), self.assertRaisesRegex(
                    HandoffError, "invalid_arguments"):
                check_input(self.proposal(args), (InputRule("count", "integer"),))

    def test_wrong_list_shapes_denied(self):
        rules = (InputRule("tags", "string_list"),)
        for value in ("first", [True], [1], ["ok", None], ["x"] * 65,
                      ["x" * 4097]):
            with self.subTest(shape=str(type(value))), self.assertRaisesRegex(
                    HandoffError, "invalid_arguments"):
                check_input(self.proposal({"tags": value}), rules)

    def test_changed_nested_content_denied(self):
        draft = self.proposal({"tags": ["approved"]})
        draft.arguments["tags"].append("added-later")
        with self.assertRaisesRegex(HandoffError, "arguments_changed"):
            check_input(draft, (InputRule("tags", "string_list"),))

    def test_invalid_backend_contract_denied_early(self):
        for item in (
            ("UPPER", "string", True),
            ("x:colon", "string", True),
            ("name", "array", True),
            ("name", "string", 1),
            ("name", "string_list", "no"),
        ):
            with self.subTest(item=item), self.assertRaisesRegex(
                    HandoffError, "invalid_rules"):
                InputRule(*item)

    def test_duplicate_operator_rules_denied(self):
        draft = self.proposal({"tags": []})
        with self.assertRaisesRegex(HandoffError, "invalid_rules"):
            check_input(draft, (
                InputRule("tags", "string_list"),
                InputRule("tags", "string_list", False),
            ))


if __name__ == "__main__":
    unittest.main()
