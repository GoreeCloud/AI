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

from reference.code_repository_file_context import (
    MAX_FILE_CONTEXT_CHARS,
    RepositoryFileContextIntakeGate,
    RepositoryFileContextTarget,
    evaluate_repository_file_context,
)

NOW = datetime(2026, 10, 6, 22, 0, tzinfo=timezone.utc)
TARGET = RepositoryFileContextTarget("GoreeCloud", "code", "main", "README.md")
README_DIGEST = "43b2670c556a80b47bfe3a1dc23bceda9bfd9c9f155722cdd026f998dfd6b786"


def valid_payload() -> dict:
    return {
        "contractVersion": "0.1.0",
        "recordType": "repository_file_context",
        "producer": {
            "service": "goreecloud-code-api",
            "authoritative": False,
            "role": "provider-neutral-evidence-broker",
        },
        "scope": {
            "repository": {"owner": "GoreeCloud", "name": "code"},
            "repositoryId": "1347975254",
            "ref": "main",
            "path": "README.md",
        },
        "generatedAt": (NOW - timedelta(minutes=1)).isoformat(),
        "source": {
            "provider": "forgejo",
            "providerHealthy": True,
            "capabilities": ["repositories:read"],
        },
        "repository": {
            "id": "1347975254",
            "owner": "GoreeCloud",
            "name": "code",
            "private": False,
            "webUrl": "https://git.example.test/GoreeCloud/code",
        },
        "file": {
            "path": "README.md",
            "sha": "abc",
            "size": 14,
            "encoding": "utf-8",
            "content": "# GoreeCloud\n",
            "contentSha256": README_DIGEST,
            "truncated": False,
            "webUrl": "https://git.example.test/GoreeCloud/code/src/branch/main/README.md",
        },
        "limits": {"contentChars": MAX_FILE_CONTEXT_CHARS},
        "evidence": {
            "webUrls": [
                "https://git.example.test/GoreeCloud/code",
                "https://git.example.test/GoreeCloud/code/src/branch/main/README.md",
            ]
        },
    }


class FakeProvider:
    def __init__(self, payload=None, fail=False):
        self.payload = payload or valid_payload()
        self.fail = fail

    def fetch_repository_file_context(self, *, owner, name, ref, path):
        if self.fail:
            raise RuntimeError("unavailable")
        return deepcopy(self.payload)


class CodeRepositoryFileContextTests(unittest.TestCase):
    def test_accepts_fresh_exact_file_context_without_authorizing_actions(self):
        decision = evaluate_repository_file_context(valid_payload(), TARGET, now=NOW)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.content_trust, "untrusted_repository_file_data")
        self.assertFalse(decision.execution_authorized)
        self.assertFalse(decision.write_authorized)

    def test_scope_and_freshness_are_exact(self):
        payload = valid_payload()
        payload["scope"]["path"] = "src/index.ts"
        self.assertIn("repository_file_context_path_mismatch", evaluate_repository_file_context(payload, TARGET, now=NOW).reason_codes)

        payload = valid_payload()
        payload["scope"]["ref"] = "feature/other"
        self.assertIn("repository_file_context_ref_mismatch", evaluate_repository_file_context(payload, TARGET, now=NOW).reason_codes)

        payload = valid_payload()
        payload["generatedAt"] = (NOW - timedelta(minutes=6)).isoformat()
        self.assertIn("repository_file_context_stale", evaluate_repository_file_context(payload, TARGET, now=NOW).reason_codes)

    def test_untruncated_content_digest_must_match(self):
        payload = valid_payload()
        payload["file"]["contentSha256"] = "0" * 64
        self.assertIn("repository_file_context_digest_mismatch", evaluate_repository_file_context(payload, TARGET, now=NOW).reason_codes)

    def test_truncated_content_must_fill_the_declared_budget(self):
        payload = valid_payload()
        payload["file"]["content"] = "x" * MAX_FILE_CONTEXT_CHARS
        payload["file"]["contentSha256"] = "1" * 64
        payload["file"]["truncated"] = True
        self.assertTrue(evaluate_repository_file_context(payload, TARGET, now=NOW).accepted)

        payload["file"]["content"] = "x" * (MAX_FILE_CONTEXT_CHARS - 1)
        self.assertIn("repository_file_context_truncation_invalid", evaluate_repository_file_context(payload, TARGET, now=NOW).reason_codes)

    def test_sensitive_fields_and_secret_paths_fail_closed(self):
        payload = valid_payload()
        payload["source"]["token"] = "unexpected"
        self.assertIn("repository_file_context_contains_sensitive_key", evaluate_repository_file_context(payload, TARGET, now=NOW).reason_codes)

        with self.assertRaisesRegex(ValueError, "repository_file_context_path_blocked"):
            RepositoryFileContextTarget("GoreeCloud", "code", "main", ".env").validate()

        with self.assertRaisesRegex(ValueError, "repository_file_context_path_blocked"):
            RepositoryFileContextTarget("GoreeCloud", "code", "main", ".env/child.txt").validate()

    def test_gate_returns_context_only_after_acceptance(self):
        result = RepositoryFileContextIntakeGate(FakeProvider()).load(target=TARGET, now=NOW)
        self.assertTrue(result.decision.accepted)
        self.assertIsNotNone(result.context)

        unavailable = RepositoryFileContextIntakeGate(FakeProvider(fail=True)).load(target=TARGET, now=NOW)
        self.assertFalse(unavailable.decision.accepted)
        self.assertIsNone(unavailable.context)
        self.assertIn("goreecloud_code_repository_file_context_unavailable", unavailable.decision.reason_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
