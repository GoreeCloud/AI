#!/usr/bin/env python3
"""GoreeCloud AI consumer boundary for Wardveil artifact scan findings.

Every file-like object entering an AI workflow is untrusted input, including
user uploads, knowledge documents, imported assets, model artifacts, tool
artifacts, and files produced by tools. This module consumes Wardveil Scan
evidence and gates release from private staging. It never talks directly to
ClamAV and never executes quarantine itself.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Mapping, Protocol

WARDVEIL_RUNTIME_CONTRACT_VERSION = "0.1.0"
EXPECTED_RESOURCE_TYPE = "ai_artifact"
ARTIFACT_KINDS = {
    "chat_upload",
    "knowledge_document",
    "imported_asset",
    "model_artifact",
    "tool_artifact",
    "generated_file",
}
SCAN_RESULTS = {"clean", "suspicious", "malicious", "unknown", "unsupported"}


def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("timestamp_must_be_timezone_aware")
    return value.astimezone(timezone.utc)


def _parse_instant(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("missing_timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class AIArtifact:
    context_id: str
    artifact_id: str
    artifact_kind: str
    media_type: str = "application/octet-stream"

    @property
    def resource_id(self) -> str:
        return f"ai:{self.context_id}:artifact:{self.artifact_id}"

    def validate(self) -> None:
        if not self.context_id or not self.artifact_id:
            raise ValueError("artifact_identity_required")
        if self.artifact_kind not in ARTIFACT_KINDS:
            raise ValueError("unsupported_artifact_kind")


@dataclass(frozen=True)
class WardveilScanEnvelope:
    resource_id: str
    resource_digest_sha256: str
    scan_record: Mapping[str, object]


@dataclass(frozen=True)
class ArtifactSecurityDecision:
    disposition: str
    release_allowed: bool
    use_as_context_allowed: bool
    quarantine_required: bool
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    scan_record_id: str | None

    def as_dict(self) -> dict:
        return {
            "disposition": self.disposition,
            "release_allowed": self.release_allowed,
            "use_as_context_allowed": self.use_as_context_allowed,
            "quarantine_required": self.quarantine_required,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "scan_record_id": self.scan_record_id,
        }

    def quarantine_handoff(self, *, artifact: AIArtifact) -> dict | None:
        if not self.quarantine_required:
            return None
        return {
            "action": "quarantine",
            "scope": {
                "resource_type": EXPECTED_RESOURCE_TYPE,
                "resource_id": artifact.resource_id,
            },
            "source_scan_record_id": self.scan_record_id,
            "evidence_refs": list(self.evidence_refs),
            "requires_explicit_executor_authority": True,
            "destructive_action": False,
        }


@dataclass(frozen=True)
class ArtifactReleaseResult:
    decision: ArtifactSecurityDecision
    released_path: Path | None
    staged_path_retained: bool


class WardveilArtifactScanner(Protocol):
    def scan_staged_file(
        self,
        *,
        artifact: AIArtifact,
        staged_path: Path,
        digest_sha256: str,
    ) -> WardveilScanEnvelope:
        """Return normalized Wardveil Scan evidence for the exact staged file."""


def _blocked(
    reason: str,
    *,
    record_id: str | None = None,
    evidence=(),
) -> ArtifactSecurityDecision:
    return ArtifactSecurityDecision(
        disposition="blocked_unverified",
        release_allowed=False,
        use_as_context_allowed=False,
        quarantine_required=False,
        reason_codes=(reason,),
        evidence_refs=tuple(evidence),
        scan_record_id=record_id,
    )


def evaluate_artifact_scan(
    artifact: AIArtifact,
    digest_sha256: str,
    envelope: WardveilScanEnvelope,
    *,
    now: datetime | None = None,
) -> ArtifactSecurityDecision:
    """Map Wardveil Scan evidence to GoreeCloud AI artifact release behavior.

    Only a current authoritative clean finding with evidence can release an
    artifact from security staging. A clean malware scan authorizes only this
    malware-release boundary; it does not by itself authorize model loading,
    tool execution, code execution, deserialization, or other active use.
    """
    artifact.validate()
    observed_now = _utc(now)
    # Scanner output is an untrusted boundary. Reject malformed objects and
    # digest fields before calling string methods or inspecting scan evidence.
    if not isinstance(digest_sha256, str) or len(digest_sha256) != 64 or any(
        character not in "0123456789abcdefABCDEF" for character in digest_sha256
    ):
        return _blocked("invalid_artifact_digest")
    if not isinstance(envelope, WardveilScanEnvelope):
        return _blocked("invalid_scan_envelope")
    if not isinstance(envelope.resource_id, str):
        return _blocked("invalid_scan_resource_id")
    if not isinstance(envelope.resource_digest_sha256, str) or len(envelope.resource_digest_sha256) != 64 or any(
        character not in "0123456789abcdefABCDEF" for character in envelope.resource_digest_sha256
    ):
        return _blocked("invalid_scan_digest")
    expected_digest = digest_sha256.lower()

    if envelope.resource_id != artifact.resource_id:
        return _blocked("resource_binding_mismatch")
    if envelope.resource_digest_sha256.lower() != expected_digest:
        return _blocked("content_digest_mismatch")

    if not isinstance(envelope.scan_record, Mapping):
        return _blocked("invalid_scan_record")
    record = dict(envelope.scan_record)
    record_id = record.get("record_id") if isinstance(record.get("record_id"), str) else None
    raw_evidence = record.get("evidence_refs")
    # A scalar string iterates into single-character pseudo-references. Only a
    # bounded, entirely valid sequence constitutes evidence for a clean scan.
    valid_evidence = (
        isinstance(raw_evidence, (list, tuple))
        and len(raw_evidence) <= 32
        and all(
            isinstance(ref, str) and 0 < len(ref) <= 512 and ref.strip() == ref
            for ref in raw_evidence
        )
    )
    evidence = tuple(raw_evidence) if valid_evidence else ()

    if record.get("contract_version") != WARDVEIL_RUNTIME_CONTRACT_VERSION:
        return _blocked("unsupported_wardveil_runtime_contract", record_id=record_id, evidence=evidence)
    if record.get("record_type") != "scan_finding":
        return _blocked("unexpected_wardveil_record_type", record_id=record_id, evidence=evidence)

    producer = record.get("producer")
    if (
        not isinstance(producer, Mapping)
        or producer.get("authoritative") is not True
        or not isinstance(producer.get("id"), str)
        or not producer["id"].strip()
    ):
        return _blocked("non_authoritative_scan_record", record_id=record_id, evidence=evidence)

    scope = record.get("scope")
    if not isinstance(scope, Mapping):
        return _blocked("missing_scan_scope", record_id=record_id, evidence=evidence)
    if scope.get("resource_type") != EXPECTED_RESOURCE_TYPE or scope.get("resource_id") != artifact.resource_id:
        return _blocked("scan_scope_mismatch", record_id=record_id, evidence=evidence)

    result = record.get("scan_result")
    if not isinstance(result, str) or result not in SCAN_RESULTS:
        return _blocked("unsupported_scan_result", record_id=record_id, evidence=evidence)

    try:
        observed_at = _parse_instant(record.get("observed_at"))
        valid_until = _parse_instant(record.get("valid_until"))
    except (TypeError, ValueError):
        return _blocked("invalid_scan_evidence_time", record_id=record_id, evidence=evidence)

    if observed_at > observed_now:
        return _blocked("future_dated_scan_evidence", record_id=record_id, evidence=evidence)
    if valid_until <= observed_at:
        return _blocked("invalid_scan_validity_window", record_id=record_id, evidence=evidence)

    if result == "malicious":
        reasons = ["wardveil_scan_malicious"]
        if observed_now > valid_until:
            reasons.append("expired_malicious_evidence_remains_blocking_for_bound_digest")
        return ArtifactSecurityDecision(
            disposition="block_quarantine",
            release_allowed=False,
            use_as_context_allowed=False,
            quarantine_required=True,
            reason_codes=tuple(reasons),
            evidence_refs=evidence,
            scan_record_id=record_id,
        )

    if result == "suspicious":
        return ArtifactSecurityDecision(
            disposition="hold_review",
            release_allowed=False,
            use_as_context_allowed=False,
            quarantine_required=False,
            reason_codes=("wardveil_scan_suspicious",),
            evidence_refs=evidence,
            scan_record_id=record_id,
        )

    if result in {"unknown", "unsupported"}:
        return _blocked(f"wardveil_scan_{result}", record_id=record_id, evidence=evidence)

    if not evidence:
        return _blocked("clean_scan_missing_evidence_refs", record_id=record_id)
    if observed_now > valid_until:
        return _blocked("clean_scan_evidence_expired", record_id=record_id, evidence=evidence)

    context_allowed = artifact.artifact_kind in {
        "chat_upload",
        "knowledge_document",
        "imported_asset",
    }
    return ArtifactSecurityDecision(
        disposition="allow",
        release_allowed=True,
        use_as_context_allowed=context_allowed,
        quarantine_required=False,
        reason_codes=("wardveil_scan_clean_current",),
        evidence_refs=evidence,
        scan_record_id=record_id,
    )


class ArtifactIntakeGate:
    """Fail-closed staging-release gate for GoreeCloud AI file-like artifacts."""

    def __init__(self, scanner: WardveilArtifactScanner):
        self._scanner = scanner

    def finalize(
        self,
        *,
        artifact: AIArtifact,
        staged_path: Path,
        final_path: Path,
        now: datetime | None = None,
    ) -> ArtifactReleaseResult:
        artifact.validate()
        staged_path = Path(staged_path)
        final_path = Path(final_path)

        if staged_path == final_path:
            return ArtifactReleaseResult(_blocked("staging_and_final_path_must_differ"), None, staged_path.exists())
        if staged_path.is_symlink():
            return ArtifactReleaseResult(_blocked("staged_artifact_symlink_not_allowed"), None, True)
        if not staged_path.is_file():
            return ArtifactReleaseResult(_blocked("staged_artifact_unavailable"), None, False)
        if final_path.exists() or final_path.is_symlink():
            return ArtifactReleaseResult(_blocked("final_destination_already_exists"), None, True)

        before_digest = sha256_file(staged_path)
        try:
            envelope = self._scanner.scan_staged_file(
                artifact=artifact,
                staged_path=staged_path,
                digest_sha256=before_digest,
            )
        except Exception:
            return ArtifactReleaseResult(_blocked("wardveil_scan_unavailable_or_error"), None, True)

        decision = evaluate_artifact_scan(artifact, before_digest, envelope, now=now)
        if not decision.release_allowed:
            return ArtifactReleaseResult(decision, None, True)

        # Re-bind immediately before publication so mutated staging cannot inherit
        # a clean finding that belongs to different bytes.
        after_digest = sha256_file(staged_path)
        if after_digest != before_digest:
            return ArtifactReleaseResult(_blocked("staged_artifact_changed_during_verification"), None, True)

        try:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic destination creation: unlike os.replace(), hard-link
            # creation fails if another writer wins the destination race.
            os.link(staged_path, final_path, follow_symlinks=False)
        except FileExistsError:
            return ArtifactReleaseResult(_blocked("final_destination_already_exists"), None, staged_path.exists())
        except OSError:
            return ArtifactReleaseResult(_blocked("artifact_release_failed"), None, staged_path.exists())

        # The scan is bound to bytes, not a filename. Ensure the newly
        # published link is still a regular file with those exact bytes.
        try:
            if final_path.is_symlink() or sha256_file(final_path) != before_digest:
                try:
                    final_path.unlink()
                except OSError:
                    pass
                return ArtifactReleaseResult(
                    _blocked("staged_artifact_changed_during_release"), None, staged_path.exists()
                )
            staged_path.unlink()
        except OSError:
            try:
                final_path.unlink()
            except OSError:
                pass
            return ArtifactReleaseResult(_blocked("artifact_release_failed"), None, staged_path.exists())

        return ArtifactReleaseResult(decision, final_path, False)
