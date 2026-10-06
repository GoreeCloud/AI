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

from reference.code_repository_file_manifest import (
    MAX_FILE_MANIFEST_ITEMS,
    RepositoryFileManifestIntakeGate,
    RepositoryFileManifestTarget,
    evaluate_repository_file_manifest,
)
from reference.repository_file_manifest_selection import select_repository_file_candidates

NOW = datetime(2026, 10, 6, 23, 0, tzinfo=timezone.utc)
TARGET = RepositoryFileManifestTarget("GoreeCloud", "code", "main")


def valid_payload() -> dict:
    return {
        "contractVersion": "0.1.0",
        "recordType": "repository_file_manifest",
        "producer": {
            "service": "goreecloud-code-api",
            "authoritative": False,
            "role": "provider-neutral-evidence-broker",
        },
        "scope": {
            "repository": {"owner": "GoreeCloud", "name": "code"},
            "repositoryId": "1347975254",
            "ref": "main",
            "path": "",
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
        "entries": [
            {"name": "README.md", "path": "README.md", "type": "file", "size": 100, "sha": "readme"},
            {"name": "src", "path": "src", "type": "directory", "size": 0, "sha": "src"},
        ],
        "truncated": False,
        "limits": {"entries": MAX_FILE_MANIFEST_ITEMS},
        "evidence": {"webUrls": ["https://git.example.test/GoreeCloud/code"]},
    }


class FakeProvider:
    def __init__(self, payload=None, fail=False):
        self.payload = payload or valid_payload()
        self.fail = fail

    def fetch_repository_file_manifest(self, *, owner, name, ref, path=""):
        if self.fail:
            raise RuntimeError("unavailable")
        return deepcopy(self.payload)


class CodeRepositoryFileManifestTests(unittest.TestCase):
    def test_accepts_fresh_manifest_without_authorizing_actions(self):
        decision = evaluate_repository_file_manifest(valid_payload(), TARGET, now=NOW)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.content_trust, "untrusted_repository_path_data")
        self.assertFalse(decision.execution_authorized)
        self.assertFalse(decision.write_authorized)

    def test_scope_freshness_and_direct_child_rules_fail_closed(self):
        payload = valid_payload()
        payload["scope"]["ref"] = "feature/other"
        self.assertIn("repository_file_manifest_ref_mismatch", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

        payload = valid_payload()
        payload["generatedAt"] = (NOW - timedelta(minutes=6)).isoformat()
        self.assertIn("repository_file_manifest_stale", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

        payload = valid_payload()
        payload["entries"][0]["path"] = "docs/README.md"
        self.assertIn("repository_file_manifest_entry_not_direct_child", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

    def test_blocked_paths_and_duplicate_paths_fail_closed(self):
        payload = valid_payload()
        payload["entries"][0] = {"name": ".env", "path": ".env", "type": "file", "size": 32, "sha": "secret"}
        self.assertIn("repository_file_manifest_blocked_path_exposed", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

        payload = valid_payload()
        payload["entries"].append(deepcopy(payload["entries"][0]))
        self.assertIn("repository_file_manifest_duplicate_path", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

    def test_nested_scope_requires_direct_descendants(self):
        target = RepositoryFileManifestTarget("GoreeCloud", "code", "main", "docs")
        payload = valid_payload()
        payload["scope"]["path"] = "docs"
        payload["entries"] = [
            {"name": "SECURITY.md", "path": "docs/SECURITY.md", "type": "file", "size": 100, "sha": "security"}
        ]
        self.assertTrue(evaluate_repository_file_manifest(payload, target, now=NOW).accepted)

        payload["entries"][0]["path"] = "docs/guides/SECURITY.md"
        self.assertIn("repository_file_manifest_entry_not_direct_child", evaluate_repository_file_manifest(payload, target, now=NOW).reason_codes)

    def test_item_limit_and_sensitive_fields_fail_closed(self):
        payload = valid_payload()
        payload["entries"] = [
            {"name": f"{index}.txt", "path": f"{index}.txt", "type": "file", "size": index, "sha": f"sha-{index}"}
            for index in range(MAX_FILE_MANIFEST_ITEMS + 1)
        ]
        self.assertIn("repository_file_manifest_entries_limit_exceeded", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

        payload = valid_payload()
        payload["source"]["token"] = "unexpected"
        self.assertIn("repository_file_manifest_contains_sensitive_key", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

        payload = valid_payload()
        payload["truncated"] = True
        self.assertIn("repository_file_manifest_truncation_invalid", evaluate_repository_file_manifest(payload, TARGET, now=NOW).reason_codes)

        with self.assertRaisesRegex(ValueError, "repository_file_manifest_path_blocked"):
            RepositoryFileManifestTarget("GoreeCloud", "code", "main", ".env/child").validate()

    def test_query_aware_selection_prioritizes_matching_paths(self):
        payload = valid_payload()
        payload["entries"].extend([
            {"name": "security.ts", "path": "security.ts", "type": "file", "size": 10, "sha": "security"},
            {"name": "security", "path": "security", "type": "directory", "size": 0, "sha": "dir"},
        ])
        result = RepositoryFileManifestIntakeGate(FakeProvider(payload=payload)).load(target=TARGET, now=NOW)
        selected = select_repository_file_candidates(result, "security", limit=2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0].type, "file")
        self.assertEqual(selected[0].path, "security.ts")

    def test_gate_returns_manifest_only_after_acceptance(self):
        result = RepositoryFileManifestIntakeGate(FakeProvider()).load(target=TARGET, now=NOW)
        self.assertTrue(result.decision.accepted)
        self.assertIsNotNone(result.context)

        unavailable = RepositoryFileManifestIntakeGate(FakeProvider(fail=True)).load(target=TARGET, now=NOW)
        self.assertFalse(unavailable.decision.accepted)
        self.assertIsNone(unavailable.context)
        self.assertIn("goreecloud_code_repository_file_manifest_unavailable", unavailable.decision.reason_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
