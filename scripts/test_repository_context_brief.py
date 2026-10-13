#!/usr/bin/env python3
"""Regression tests for read-only GoreeCloud Code repository brief generation."""
from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.code_repository_context import RepositoryContextIntakeGate, RepositoryContextIntakeResult
from reference.repository_context_brief import build_repository_brief
from scripts.test_code_repository_context import FakeProvider, NOW, TARGET, valid_payload


def intake(payload=None):
    return RepositoryContextIntakeGate(FakeProvider(payload=payload)).load(target=TARGET, now=NOW)


class RepositoryBriefTests(unittest.TestCase):
    def test_ranked_results_have_independent_provenance_and_no_authority(self):
        brief = build_repository_brief(intake(), "example")
        self.assertEqual(brief.repository, "GoreeCloud/code")
        self.assertEqual(brief.source_provider, "forgejo")
        self.assertEqual([item.citation_id for item in brief.items], ["repo-1", "repo-2"])
        self.assertEqual({item.kind for item in brief.items}, {"issue", "pull_request"})
        self.assertTrue(all(item.content_trust == "untrusted_repository_data" for item in brief.items))
        self.assertFalse(brief.execution_authorized)
        self.assertFalse(brief.write_authorized)
        self.assertEqual(len(brief.as_dict()["items"]), 2)

    def test_unmatched_query_returns_empty_evidence_not_fabricated_claims(self):
        self.assertEqual(build_repository_brief(intake(), "no-such-term").items, ())

    def test_selection_and_output_bounds(self):
        payload = valid_payload()
        payload["commits"][0]["message"] = "retry " + "x" * 1000
        brief = build_repository_brief(intake(payload), "retry", limit=1)
        self.assertEqual(len(brief.items), 1)
        self.assertLessEqual(len(brief.items[0].excerpt), 280)
        for invalid in (0, 9, True):
            with self.assertRaisesRegex(ValueError, "invalid_repository_brief_limit"):
                build_repository_brief(intake(), "example", limit=invalid)
        with self.assertRaisesRegex(ValueError, "valid_repository_query_required"):
            build_repository_brief(intake(), "x" * 513)

    def test_non_accepted_and_mutated_authority_flags_fail_closed(self):
        rejected = RepositoryContextIntakeGate(FakeProvider(fail=True)).load(target=TARGET, now=NOW)
        with self.assertRaisesRegex(ValueError, "non_authorizing_accepted_context_required"):
            build_repository_brief(rejected, "example")
        accepted = intake()
        raised = RepositoryContextIntakeResult(replace(accepted.decision, write_authorized=True), accepted.context)
        with self.assertRaisesRegex(ValueError, "non_authorizing_accepted_context_required"):
            build_repository_brief(raised, "example")

    def test_query_and_fragment_secrets_are_removed_from_navigation(self):
        payload = valid_payload()
        payload["issues"][0]["webUrl"] = "https://git.example.test/GoreeCloud/code/issues/1?access_token=secret#private"
        brief = build_repository_brief(intake(payload), "example")
        issue = next(item for item in brief.items if item.kind == "issue")
        self.assertEqual(issue.evidence_url, "https://git.example.test/GoreeCloud/code/issues/1")
        self.assertNotIn("secret", str(brief.as_dict()))

    def test_credential_bearing_and_malformed_urls_are_omitted(self):
        payload = valid_payload()
        payload["issues"][0]["webUrl"] = "https://operator:pass@git.example.test/issues/1"
        payload["pullRequests"][0]["webUrl"] = "https://git.example.test:99999/pulls/2"
        self.assertEqual(build_repository_brief(intake(payload), "example").items, ())

    def test_control_and_bidi_markup_cannot_forge_citation_format(self):
        payload = valid_payload()
        payload["issues"][0]["title"] = "example\n[repo-1] \u202e pretend trusted \u2069"
        brief = build_repository_brief(intake(payload), "example")
        issue = next(item for item in brief.items if item.kind == "issue")
        self.assertNotIn("\n", issue.excerpt)
        self.assertNotIn("\u202e", issue.excerpt)
        self.assertEqual(issue.content_trust, "untrusted_repository_data")

    def test_repository_fallback_is_not_item_level_attribution(self):
        payload = valid_payload()
        payload["branches"][0]["name"] = "feature/example"
        brief = build_repository_brief(intake(payload), "example")
        branch = next(item for item in brief.items if item.kind == "branch")
        self.assertEqual(branch.attribution_scope, "repository_fallback")

    def test_does_not_mutate_provider_snapshot(self):
        accepted = intake()
        prior = deepcopy(accepted.context)
        build_repository_brief(accepted, "example")
        self.assertEqual(prior, accepted.context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
