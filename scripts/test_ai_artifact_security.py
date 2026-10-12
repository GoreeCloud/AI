#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.ai_artifact_security import (
    AIArtifact,
    ArtifactIntakeGate,
    WardveilScanEnvelope,
    evaluate_artifact_scan,
    sha256_file,
)

NOW = datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc)


def artifact(kind: str = "chat_upload") -> AIArtifact:
    return AIArtifact("context-1", "artifact-1", kind, "application/octet-stream")


def record(
    item: AIArtifact,
    *,
    result: str = "clean",
    observed_at: datetime | None = None,
    valid_until: datetime | None = None,
    evidence=True,
    authoritative=True,
    resource_type="ai_artifact",
    resource_id: str | None = None,
) -> dict:
    observed_at = observed_at or NOW - timedelta(minutes=1)
    valid_until = valid_until or NOW + timedelta(minutes=4)
    return {
        "contract_version": "0.1.0",
        "record_type": "scan_finding",
        "record_id": "scan-1",
        "producer": {"id": "wardveil-scan", "authoritative": authoritative},
        "scope": {
            "resource_type": resource_type,
            "resource_id": resource_id or item.resource_id,
        },
        "scan_result": result,
        "observed_at": observed_at.isoformat(),
        "valid_until": valid_until.isoformat(),
        "evidence_refs": ["evidence:scanner-health", "evidence:scan"] if evidence else [],
    }


def envelope(item: AIArtifact, digest: str, **kwargs) -> WardveilScanEnvelope:
    return WardveilScanEnvelope(item.resource_id, digest, record(item, **kwargs))


class FakeScanner:
    def __init__(self, *, result="clean", mutate=False, fail=False, record_overrides=None):
        self.result = result
        self.mutate = mutate
        self.fail = fail
        self.record_overrides = record_overrides or {}

    def scan_staged_file(self, *, artifact, staged_path, digest_sha256):
        if self.fail:
            raise RuntimeError("scanner unavailable")
        scan_record = record(artifact, result=self.result)
        scan_record.update(self.record_overrides)
        if self.mutate:
            staged_path.write_bytes(staged_path.read_bytes() + b"changed")
        return WardveilScanEnvelope(artifact.resource_id, digest_sha256, scan_record)


class ArtifactSecurityTests(unittest.TestCase):
    def test_sha256_file_known_vector(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "abc.bin"
            path.write_bytes(b"abc")
            self.assertEqual(sha256_file(path), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_clean_chat_upload_releases_and_can_be_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "released" / "upload.bin"
            staged.write_bytes(b"clean")
            result = ArtifactIntakeGate(FakeScanner()).finalize(artifact=artifact(), staged_path=staged, final_path=final, now=NOW)
            self.assertEqual(result.decision.disposition, "allow")
            self.assertTrue(result.decision.use_as_context_allowed)
            self.assertEqual(result.released_path, final)
            self.assertTrue(final.is_file())
            self.assertFalse(staged.exists())

    def test_clean_model_artifact_does_not_authorize_context_use(self):
        item = artifact("model_artifact")
        digest = "a" * 64
        decision = evaluate_artifact_scan(item, digest, envelope(item, digest), now=NOW)
        self.assertTrue(decision.release_allowed)
        self.assertFalse(decision.use_as_context_allowed)

    def test_expired_clean_fails_closed(self):
        item = artifact()
        digest = "b" * 64
        decision = evaluate_artifact_scan(
            item,
            digest,
            envelope(item, digest, valid_until=NOW - timedelta(seconds=1)),
            now=NOW,
        )
        self.assertEqual(decision.disposition, "blocked_unverified")

    def test_clean_without_evidence_fails_closed(self):
        item = artifact()
        digest = "c" * 64
        decision = evaluate_artifact_scan(item, digest, envelope(item, digest, evidence=False), now=NOW)
        self.assertIn("clean_scan_missing_evidence_refs", decision.reason_codes)

    def test_malicious_requires_quarantine_handoff(self):
        item = artifact("tool_artifact")
        digest = "d" * 64
        decision = evaluate_artifact_scan(item, digest, envelope(item, digest, result="malicious"), now=NOW)
        self.assertEqual(decision.disposition, "block_quarantine")
        self.assertTrue(decision.quarantine_required)
        handoff = decision.quarantine_handoff(artifact=item)
        self.assertTrue(handoff["requires_explicit_executor_authority"])
        self.assertFalse(handoff["destructive_action"])

    def test_expired_malicious_remains_blocking(self):
        item = artifact()
        digest = "e" * 64
        decision = evaluate_artifact_scan(
            item,
            digest,
            envelope(item, digest, result="malicious", valid_until=NOW - timedelta(seconds=1)),
            now=NOW,
        )
        self.assertEqual(decision.disposition, "block_quarantine")
        self.assertIn("expired_malicious_evidence_remains_blocking_for_bound_digest", decision.reason_codes)

    def test_suspicious_is_held(self):
        item = artifact()
        digest = "f" * 64
        decision = evaluate_artifact_scan(item, digest, envelope(item, digest, result="suspicious"), now=NOW)
        self.assertEqual(decision.disposition, "hold_review")
        self.assertFalse(decision.release_allowed)

    def test_unknown_and_unsupported_fail_closed(self):
        item = artifact()
        digest = "1" * 64
        for result in ("unknown", "unsupported"):
            with self.subTest(result=result):
                decision = evaluate_artifact_scan(item, digest, envelope(item, digest, result=result), now=NOW)
                self.assertEqual(decision.disposition, "blocked_unverified")

    def test_digest_mismatch_fails_closed(self):
        item = artifact()
        decision = evaluate_artifact_scan(item, "2" * 64, envelope(item, "3" * 64), now=NOW)
        self.assertIn("content_digest_mismatch", decision.reason_codes)

    def test_scope_mismatch_fails_closed(self):
        item = artifact()
        digest = "4" * 64
        decision = evaluate_artifact_scan(item, digest, envelope(item, digest, resource_id="ai:other:artifact:x"), now=NOW)
        self.assertIn("scan_scope_mismatch", decision.reason_codes)

    def test_non_authoritative_record_fails_closed(self):
        item = artifact()
        digest = "5" * 64
        decision = evaluate_artifact_scan(item, digest, envelope(item, digest, authoritative=False), now=NOW)
        self.assertIn("non_authoritative_scan_record", decision.reason_codes)

    def test_future_dated_evidence_fails_closed(self):
        item = artifact()
        digest = "6" * 64
        decision = evaluate_artifact_scan(
            item,
            digest,
            envelope(item, digest, observed_at=NOW + timedelta(minutes=1), valid_until=NOW + timedelta(minutes=6)),
            now=NOW,
        )
        self.assertIn("future_dated_scan_evidence", decision.reason_codes)

    def test_scanner_exception_retains_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "final"
            staged.write_bytes(b"payload")
            result = ArtifactIntakeGate(FakeScanner(fail=True)).finalize(artifact=artifact(), staged_path=staged, final_path=final, now=NOW)
            self.assertIn("wardveil_scan_unavailable_or_error", result.decision.reason_codes)
            self.assertTrue(staged.exists())
            self.assertFalse(final.exists())

    def test_changed_during_verification_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "final"
            staged.write_bytes(b"payload")
            result = ArtifactIntakeGate(FakeScanner(mutate=True)).finalize(artifact=artifact(), staged_path=staged, final_path=final, now=NOW)
            self.assertIn("staged_artifact_changed_during_verification", result.decision.reason_codes)
            self.assertTrue(staged.exists())
            self.assertFalse(final.exists())

    def test_competing_destination_created_during_scan_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "final"
            staged.write_bytes(b"scanned")

            class RacingScanner(FakeScanner):
                def scan_staged_file(self, **kwargs):
                    final.write_bytes(b"another-writer")
                    return super().scan_staged_file(**kwargs)

            result = ArtifactIntakeGate(RacingScanner()).finalize(
                artifact=artifact(), staged_path=staged, final_path=final, now=NOW
            )
            self.assertIn("final_destination_already_exists", result.decision.reason_codes)
            self.assertIsNone(result.released_path)
            self.assertEqual(final.read_bytes(), b"another-writer")
            self.assertEqual(staged.read_bytes(), b"scanned")

    def test_staged_symlink_is_not_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original"
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "final"
            original.write_bytes(b"secret")
            staged.symlink_to(original)
            result = ArtifactIntakeGate(FakeScanner()).finalize(
                artifact=artifact(), staged_path=staged, final_path=final, now=NOW
            )
            self.assertIn("staged_artifact_symlink_not_allowed", result.decision.reason_codes)
            self.assertFalse(final.exists())
            self.assertEqual(original.read_bytes(), b"secret")

    def test_dangling_final_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "final"
            staged.write_bytes(b"clean")
            final.symlink_to(Path(tmp) / "absent")
            result = ArtifactIntakeGate(FakeScanner()).finalize(
                artifact=artifact(), staged_path=staged, final_path=final, now=NOW
            )
            self.assertIn("final_destination_already_exists", result.decision.reason_codes)
            self.assertTrue(final.is_symlink())
            self.assertEqual(staged.read_bytes(), b"clean")

    def test_changed_bytes_after_link_are_not_left_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "final"
            staged.write_bytes(b"scanned")
            actual_link = os.link

            def mutate_after_link(source, destination, **kwargs):
                actual_link(source, destination, **kwargs)
                staged.write_bytes(b"changed-after-link")

            with patch("reference.ai_artifact_security.os.link", side_effect=mutate_after_link):
                result = ArtifactIntakeGate(FakeScanner()).finalize(
                    artifact=artifact(), staged_path=staged, final_path=final, now=NOW
                )
            self.assertIn("staged_artifact_changed_during_release", result.decision.reason_codes)
            self.assertFalse(final.exists())
            self.assertEqual(staged.read_bytes(), b"changed-after-link")

    def test_existing_final_destination_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "staged"
            final = Path(tmp) / "final"
            staged.write_bytes(b"new")
            final.write_bytes(b"existing")
            result = ArtifactIntakeGate(FakeScanner()).finalize(artifact=artifact(), staged_path=staged, final_path=final, now=NOW)
            self.assertIn("final_destination_already_exists", result.decision.reason_codes)
            self.assertEqual(final.read_bytes(), b"existing")


    def test_malformed_clean_scan_evidence_never_authorizes_release(self):
        item = artifact()
        digest = "7" * 64
        invalid_values = (
            "evidence:scanner-health",
            {"source": "evidence:scanner-health"},
            ["evidence:valid", 123],
            [""],
            ["  "],
            [" padded "],
            ["reference:" + "x" * 600],
            ["evidence:valid"] * 33,
        )
        for evidence_refs in invalid_values:
            with self.subTest(value=repr(evidence_refs)[:75]):
                payload = record(item)
                payload["evidence_refs"] = evidence_refs
                finding = WardveilScanEnvelope(item.resource_id, digest, payload)
                decision = evaluate_artifact_scan(item, digest, finding, now=NOW)
                self.assertFalse(decision.release_allowed)
                self.assertIn("clean_scan_missing_evidence_refs", decision.reason_codes)

    def test_malformed_scan_record_result_and_producer_fail_closed(self):
        item = artifact()
        digest = "8" * 64
        invalid_record = WardveilScanEnvelope(item.resource_id, digest, "untrusted")
        self.assertIn(
            "invalid_scan_record",
            evaluate_artifact_scan(item, digest, invalid_record, now=NOW).reason_codes,
        )

        bad_result = record(item)
        bad_result["scan_result"] = ["clean"]
        self.assertIn(
            "unsupported_scan_result",
            evaluate_artifact_scan(
                item, digest, WardveilScanEnvelope(item.resource_id, digest, bad_result), now=NOW
            ).reason_codes,
        )

        bad_producer = record(item)
        bad_producer["producer"] = {"id": 1, "authoritative": True}
        self.assertIn(
            "non_authoritative_scan_record",
            evaluate_artifact_scan(
                item, digest, WardveilScanEnvelope(item.resource_id, digest, bad_producer), now=NOW
            ).reason_codes,
        )

    def test_valid_tuple_scan_evidence_still_authorizes_clean_artifact(self):
        item = artifact()
        digest = "9" * 64
        payload = record(item)
        payload["evidence_refs"] = ("evidence:scan", "evidence:scanner-health")
        decision = evaluate_artifact_scan(
            item, digest, WardveilScanEnvelope(item.resource_id, digest, payload), now=NOW
        )
        self.assertTrue(decision.release_allowed)



    def test_untrusted_envelope_and_digest_shapes_fail_closed(self):
        item = artifact()
        digest = "a" * 64
        for malformed in (None, {}, "untrusted", 123, ["scan"]):
            with self.subTest(envelope=repr(malformed)):
                decision = evaluate_artifact_scan(item, digest, malformed, now=NOW)
                self.assertFalse(decision.release_allowed)
                self.assertIn("invalid_scan_envelope", decision.reason_codes)

        for malformed in (None, 123, [], "", "g" * 64, "a" * 63, "a" * 65):
            with self.subTest(expected_digest=repr(malformed)):
                decision = evaluate_artifact_scan(item, malformed, envelope(item, digest), now=NOW)
                self.assertFalse(decision.release_allowed)
                self.assertIn("invalid_artifact_digest", decision.reason_codes)
            with self.subTest(scan_digest=repr(malformed)):
                finding = WardveilScanEnvelope(item.resource_id, malformed, record(item))
                decision = evaluate_artifact_scan(item, digest, finding, now=NOW)
                self.assertFalse(decision.release_allowed)
                self.assertIn("invalid_scan_digest", decision.reason_codes)

        malformed_resource = WardveilScanEnvelope(123, digest, record(item))
        self.assertIn(
            "invalid_scan_resource_id",
            evaluate_artifact_scan(item, digest, malformed_resource, now=NOW).reason_codes,
        )

    def test_uppercase_hex_digest_remains_compatible(self):
        item = artifact()
        lower = "abcdef0123456789" * 4
        result = evaluate_artifact_scan(item, lower, envelope(item, lower.upper()), now=NOW)
        self.assertTrue(result.release_allowed)



if __name__ == "__main__":
    unittest.main(verbosity=2)
