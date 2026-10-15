"""Offline tests for operator-pinned declarative capability manifests."""
import hashlib
import json
import unittest

from reference.capability_manifest import ManifestError, parse_pinned_manifest
from reference.capability_requirements import RequirementCatalog
from reference.integration_directory import IntegrationDirectory
from reference.capability_discovery import discover


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.sample = {
            "schema": "goreecloud.ai.capability-manifest.v1",
            "service": "example",
            "title": "Example Service",
            "revision": "v1",
            "transports": ["mcp", "api"],
            "operations": [
                {"id": "objects.read", "minimum_risk": "read", "transports": ["mcp"]},
                {"id": "objects.write", "minimum_risk": "write", "transports": ["api"]},
            ],
        }

    def parse(self, value=None):
        raw = json.dumps(self.sample if value is None else value,
                         ensure_ascii=False, sort_keys=True).encode()
        return parse_pinned_manifest(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_pinned_declarative_manifest_is_not_auto_connected(self):
        manifest = self.parse()
        directory = IntegrationDirectory()
        catalog = RequirementCatalog()
        directory.register(manifest.definition)
        for rule in manifest.requirements:
            catalog.register(rule)
        perms = dict(permitted_services=frozenset({"example"}),
                     permitted_operations=frozenset({"example:objects.read",
                                                      "example:objects.write"}))
        self.assertEqual(discover(directory, catalog, **perms).capabilities, ())
        directory.bind("example", connection_id="local-only", transport="mcp")
        self.assertEqual([x.operation for x in discover(directory, catalog,
                                                        **perms).capabilities],
                         ["objects.read"])

    def test_pin_mismatch_rejected(self):
        raw = json.dumps(self.sample).encode()
        with self.assertRaisesRegex(ManifestError, "digest_mismatch"):
            parse_pinned_manifest(raw, expected_sha256="0" * 64)

    def test_duplicate_keys_rejected(self):
        raw = b'{"schema":"a","schema":"b"}'
        with self.assertRaisesRegex(ManifestError, "duplicate_key"):
            parse_pinned_manifest(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_extra_fields_not_allowed(self):
        changed = {**self.sample, "unknown_field": "value"}
        with self.assertRaisesRegex(ManifestError, "invalid_manifest_schema"):
            self.parse(changed)

    def test_operation_risk_and_transport_must_be_declared(self):
        changed = {**self.sample, "operations": [
            {"id": "objects.read", "minimum_risk": "read", "transports": ["webhook"]}
        ]}
        with self.assertRaisesRegex(ManifestError, "transport_not_declared"):
            self.parse(changed)
        changed["operations"] = [
            {"id": "objects.read", "transports": ["mcp"]}
        ]
        with self.assertRaises(ManifestError):
            self.parse(changed)

    def test_bad_number_and_overlarge_manifest_fail_closed(self):
        raw = b"NaN"
        with self.assertRaisesRegex(ManifestError, "invalid_number"):
            parse_pinned_manifest(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
        raw = b" " * 65537
        with self.assertRaisesRegex(ManifestError, "invalid_manifest_input"):
            parse_pinned_manifest(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
