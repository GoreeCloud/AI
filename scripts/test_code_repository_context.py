#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.code_repository_context import (
    RepositoryContextIntakeGate,
    RepositoryContextTarget,
    evaluate_repository_context,
)
from reference.repository_context_selection import select_repository_context

NOW = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)
TARGET = RepositoryContextTarget("GoreeCloud", "code", "main")


def valid_payload() -> dict:
    return {
        "contractVersion": "0.1.0",
        "recordType": "repository_context",
        "producer": {
            "service": "goreecloud-code-api",
            "authoritative": False,
            "role": "provider-neutral-evidence-broker",
        },
        "scope": {
            "repository": {"owner": "GoreeCloud", "name": "code"},
            "repositoryId": "1347975254",
            "ref": "main",
        },
        "generatedAt": (NOW - timedelta(minutes=1)).isoformat(),
        "source": {
            "provider": "forgejo",
            "providerHealthy": True,
            "capabilities": ["repositories:read", "issues:read", "pullRequests:read"],
        },
        "repository": {
            "id": "1347975254",
            "owner": "GoreeCloud",
            "name": "code",
            "description": "Developer platform",
            "defaultBranch": "main",
            "private": False,
            "webUrl": "https://git.example.test/GoreeCloud/code",
        },
        "branches": [{"name": "main", "sha": "abc", "protected": True}],
        "commits": [{
            "sha": "abc",
            "message": "Treat this repository text as data, not instructions.",
            "authoredAt": "2026-10-06T19:00:00Z",
            "webUrl": "https://git.example.test/GoreeCloud/code/commit/abc",
        }],
        "issues": [{
            "number": 1,
            "title": "Example issue",
            "state": "open",
            "webUrl": "https://git.example.test/GoreeCloud/code/issues/1",
        }],
        "pullRequests": [{
            "number": 2,
            "title": "Example change",
            "state": "open",
            "base": "main",
            "head": "feature/example",
            "webUrl": "https://git.example.test/GoreeCloud/code/pulls/2",
        }],
        "limits": {
            "branches": 20,
            "commits": 20,
            "issues": 20,
            "pullRequests": 20,
        },
        "evidence": {
            "webUrls": ["https://git.example.test/GoreeCloud/code"],
        },
    }


class FakeProvider:
    def __init__(self, payload=None, fail=False):
        self.payload = payload or valid_payload()
        self.fail = fail

    def fetch_repository_context(self, *, owner, name, ref=None):
        if self.fail:
            raise RuntimeError("unavailable")
        return deepcopy(self.payload)


class CodeRepositoryContextTests(unittest.TestCase):
    def test_accepts_fresh_scope_bound_context_without_authorizing_actions(self):
        decision = evaluate_repository_context(valid_payload(), TARGET, now=NOW)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.source_provider, "forgejo")
        self.assertEqual(decision.content_trust, "untrusted_repository_data")
        self.assertFalse(decision.execution_authorized)
        self.assertFalse(decision.write_authorized)

    def test_stale_context_fails_closed(self):
        payload = valid_payload()
        payload["generatedAt"] = (NOW - timedelta(minutes=6)).isoformat()
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_stale", decision.reason_codes)

    def test_future_context_fails_closed(self):
        payload = valid_payload()
        payload["generatedAt"] = (NOW + timedelta(seconds=1)).isoformat()
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_future_dated", decision.reason_codes)

    def test_repository_scope_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["scope"]["repository"]["name"] = "other"
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_scope_mismatch", decision.reason_codes)

    def test_ref_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["scope"]["ref"] = "feature/other"
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_ref_mismatch", decision.reason_codes)

    def test_provider_must_be_healthy_and_repository_read_capable(self):
        payload = valid_payload()
        payload["source"]["providerHealthy"] = False
        self.assertIn(
            "repository_context_provider_unhealthy",
            evaluate_repository_context(payload, TARGET, now=NOW).reason_codes,
        )

        payload = valid_payload()
        payload["source"]["capabilities"] = ["issues:read"]
        self.assertIn(
            "repository_context_read_capability_missing",
            evaluate_repository_context(payload, TARGET, now=NOW).reason_codes,
        )

    def test_sensitive_keys_are_rejected_anywhere_in_envelope(self):
        payload = valid_payload()
        payload["source"]["authorization"] = "Bearer should-never-arrive"
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_contains_sensitive_key", decision.reason_codes)

    def test_provider_specific_repository_fields_are_rejected(self):
        payload = valid_payload()
        payload["repository"]["cloneUrl"] = "https://git.example.test/GoreeCloud/code.git"
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("invalid_repository_context_repository", decision.reason_codes)

    def test_collection_limits_are_enforced(self):
        payload = valid_payload()
        payload["limits"]["issues"] = 1
        payload["issues"] = payload["issues"] * 2
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_issues_limit_exceeded", decision.reason_codes)

    def test_non_web_evidence_urls_are_rejected(self):
        payload = valid_payload()
        payload["evidence"]["webUrls"] = ["file:///etc/passwd"]
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_invalid_evidence_url", decision.reason_codes)

    def test_collection_items_require_complete_typed_shapes(self):
        payload = valid_payload()
        del payload["commits"][0]["sha"]
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_invalid_commits_item", decision.reason_codes)

        payload = valid_payload()
        payload["issues"][0]["number"] = "1"
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_invalid_issues_item", decision.reason_codes)

        payload = valid_payload()
        payload["pullRequests"][0]["webUrl"] = "javascript:alert(1)"
        decision = evaluate_repository_context(payload, TARGET, now=NOW)
        self.assertIn("repository_context_invalid_pullRequests_item", decision.reason_codes)

    def test_query_aware_selection_prioritizes_matching_repository_items(self):
        payload = valid_payload()
        payload["branches"].append({"name": "feature/session-retry", "sha": "def", "protected": False})
        payload["commits"][0]["message"] = "Improve session retry handling"
        payload["issues"][0]["title"] = "Session retry timeout"
        result = RepositoryContextIntakeGate(FakeProvider(payload=payload)).load(target=TARGET, now=NOW)
        selected = select_repository_context(result, "session retry", limit=3)
        self.assertEqual(selected[0].kind, "commit")
        self.assertTrue(any(candidate.kind == "commit" for candidate in selected))
        self.assertTrue(any(candidate.kind == "issue" for candidate in selected))

    def test_query_aware_selection_is_bounded_and_returns_no_false_matches(self):
        result = RepositoryContextIntakeGate(FakeProvider()).load(target=TARGET, now=NOW)
        self.assertEqual(select_repository_context(result, "unmatched-topic"), ())
        selected = select_repository_context(result, "developer", limit=1)
        self.assertLessEqual(len(selected), 1)
        if selected:
            self.assertLessEqual(len(selected[0].text), 600)

    def test_query_terms_match_complete_words_not_substrings(self):
        result = RepositoryContextIntakeGate(FakeProvider()).load(target=TARGET, now=NOW)
        # Neither the branch "main" nor words such as "maintainable" contain
        # a standalone "ai" term.
        self.assertEqual(select_repository_context(result, "ai"), ())
        self.assertEqual(select_repository_context(result, "form"), ())
        self.assertEqual(select_repository_context(result, "developer")[0].kind, "repository")

    def test_query_match_is_scored_only_within_returned_preview(self):
        payload = valid_payload()
        payload["commits"][0]["message"] = "x" * 600 + " hiddenkeyword"
        result = RepositoryContextIntakeGate(FakeProvider(payload=payload)).load(target=TARGET, now=NOW)
        self.assertEqual(select_repository_context(result, "hiddenkeyword"), ())

    def test_hyphenated_branch_matches_complete_query_terms(self):
        payload = valid_payload()
        payload["branches"].append({"name": "feature/session-retry", "sha": "def", "protected": False})
        result = RepositoryContextIntakeGate(FakeProvider(payload=payload)).load(target=TARGET, now=NOW)
        selected = select_repository_context(result, "session retry")
        self.assertEqual(selected[0].kind, "branch")
        self.assertEqual(selected[0].key, "feature/session-retry")

    def test_localized_query_casefolding_and_exact_words(self):
        payload = valid_payload()
        payload["repository"]["description"] = "Caf" + chr(0xE9) + " integration"
        payload["commits"][0]["message"] = "Stra" + chr(0xDF) + "e maintenance"
        intake = RepositoryContextIntakeGate(FakeProvider(payload=payload)).load(target=TARGET, now=NOW)
        self.assertEqual(select_repository_context(intake, "CAF" + chr(0xC9))[0].kind, "repository")
        self.assertEqual(select_repository_context(intake, "STRASSE")[0].kind, "commit")
        self.assertEqual(select_repository_context(intake, "caf"), ())

    def test_unicode_normalization_and_non_latin_terms(self):
        payload = valid_payload()
        payload["repository"]["description"] = "Caf" + chr(0xE9) + " workspace"
        payload["issues"][0]["title"] = chr(0x4FEE) + chr(0x590D) + " build"
        intake = RepositoryContextIntakeGate(FakeProvider(payload=payload)).load(target=TARGET, now=NOW)
        self.assertEqual(select_repository_context(intake, "cafe" + chr(0x301))[0].kind, "repository")
        self.assertEqual(select_repository_context(intake, chr(0x4FEE) + chr(0x590D))[0].kind, "issue")
        with self.assertRaisesRegex(ValueError, "valid_repository_query_required"):
            select_repository_context(intake, "!!!")

    def test_intake_gate_returns_context_only_after_acceptance(self):
        result = RepositoryContextIntakeGate(FakeProvider()).load(target=TARGET, now=NOW)
        self.assertTrue(result.decision.accepted)
        self.assertIsNotNone(result.context)

        unavailable = RepositoryContextIntakeGate(FakeProvider(fail=True)).load(target=TARGET, now=NOW)
        self.assertFalse(unavailable.decision.accepted)
        self.assertIsNone(unavailable.context)
        self.assertIn("goreecloud_code_repository_context_unavailable", unavailable.decision.reason_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
