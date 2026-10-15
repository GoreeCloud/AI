"""Offline, synthetic staged-catalog tests."""
import dataclasses
import hashlib
import json
import unittest

from reference.capability_catalog_loader import CatalogError, PinnedManifest, build_staged_catalog
from reference.capability_discovery import discover


def sample(service):
    value = {
        "schema": "goreecloud.ai.capability-manifest.v1",
        "service": service,
        "title": service,
        "revision": "v1",
        "transports": ["mcp"],
        "operations": [{"id": "items.read", "minimum_risk": "read", "transports": ["mcp"]}],
    }
    raw = json.dumps(value).encode()
    return PinnedManifest(raw, hashlib.sha256(raw).hexdigest())


class CatalogTests(unittest.TestCase):
    def test_good_catalog_defaults_to_disconnected(self):
        staged = build_staged_catalog((sample("alpha"), sample("bravo")))
        self.assertEqual(len(staged.revisions), 2)
        permissions = dict(permitted_services=frozenset({"alpha", "bravo"}),
                           permitted_operations=frozenset({"alpha:items.read", "bravo:items.read"}))
        self.assertEqual(discover(staged.directory, staged.requirements,
                                  **permissions).capabilities, ())
        staged.directory.bind("alpha", connection_id="test-connector", transport="mcp")
        visible = discover(staged.directory, staged.requirements, **permissions)
        self.assertEqual([v.service for v in visible.capabilities], ["alpha"])

    def test_bad_batch_does_not_touch_existing_catalog(self):
        old = build_staged_catalog((sample("alpha"),))
        invalid = dataclasses.replace(sample("bravo"), expected_sha256="0" * 64)
        with self.assertRaisesRegex(CatalogError, "manifest_rejected"):
            build_staged_catalog((sample("alpha"), invalid))
        self.assertEqual(len(old.revisions), 1)

    def test_duplicate_and_invalid_batches_rejected(self):
        with self.assertRaisesRegex(CatalogError, "conflicting_catalog"):
            build_staged_catalog((sample("alpha"), sample("alpha")))
        for value in ((), [], ("invalid",)):
            with self.assertRaisesRegex(CatalogError, "invalid_catalog_input"):
                build_staged_catalog(value)

    def test_revision_is_independent_of_input_order(self):
        first = build_staged_catalog((sample("bravo"), sample("alpha")))
        second = build_staged_catalog((sample("alpha"), sample("bravo")))
        self.assertEqual(first.catalog_sha256, second.catalog_sha256)


if __name__ == "__main__":
    unittest.main()
