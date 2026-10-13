#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "wardveil.ai-artifact-scan.json"
SOURCE = ROOT / "reference" / "ai_artifact_security.py"
DOC = ROOT / "docs" / "WARDVEIL_ARTIFACT_SECURITY.md"
README = ROOT / "README.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"GoreeCloud AI Wardveil validation failed: {message}")


def main() -> None:
    for path in (CONTRACT, SOURCE, DOC, README):
        require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}")

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")
    docs = (DOC.read_text(encoding="utf-8") + "\n" + README.read_text(encoding="utf-8")).lower()

    require(contract.get("consumer") == "GoreeCloud AI", "unexpected consumer identity")
    require(contract.get("resource_type") == "ai_artifact", "unexpected resource type")
    require(contract.get("direct_clamav_access_allowed") is False, "AI must not connect directly to ClamAV")
    require(contract.get("production_runtime_status") == "unaccepted", "source must not claim runtime acceptance")

    requirements = contract.get("requirements") or {}
    for key in (
        "private_staging_before_release",
        "sha256_digest_binding",
        "authoritative_scan_record_required",
        "clean_requires_current_unexpired_evidence",
        "clean_requires_evidence_refs",
        "rehash_staging_after_clean_before_release",
        "atomic_destination_create_no_clobber",
        "staged_symlink_rejected",
        "staged_inode_identity_verified_before_release_and_cleanup",
        "rehash_released_link_before_retiring_staging",
        "unknown_and_unsupported_fail_closed",
        "scanner_unavailable_fails_closed",
        "malicious_bound_digest_remains_blocking_after_evidence_expiry",
    ):
        require(requirements.get(key) is True, f"missing security requirement: {key}")

    boundaries = contract.get("authority_boundaries") or {}
    require(boundaries.get("clean_scan_authorizes_active_execution") is False, "clean scan must not authorize active execution")
    require(boundaries.get("model_loading_requires_separate_runtime_policy") is True, "model loading must retain separate policy")
    require(boundaries.get("tool_execution_requires_separate_runtime_policy") is True, "tool execution must retain separate policy")
    require(boundaries.get("quarantine_requires_explicit_executor_authority") is True, "quarantine must require authority")
    require(boundaries.get("quarantine_is_deletion") is False, "quarantine must not equal deletion")

    privacy = contract.get("privacy") or {}
    require(privacy.get("raw_artifact_content_required_in_shared_security_records") is False, "shared evidence must not require raw content")
    require(privacy.get("credentials_or_session_tokens_allowed_in_shared_security_records") is False, "shared evidence must reject credentials/tokens")
    require(privacy.get("data_minimization_required") is True, "Privacy Shield minimization must remain required")

    for token in (
        'EXPECTED_RESOURCE_TYPE = "ai_artifact"',
        '"wardveil_scan_unavailable_or_error"',
        '"staged_artifact_changed_during_verification"',
        '"expired_malicious_evidence_remains_blocking_for_bound_digest"',
        '"requires_explicit_executor_authority": True',
        'os.link(staged_path, final_path, follow_symlinks=False)',
        '"staged_artifact_symlink_not_allowed"',
        '"final_destination_already_exists"',
        '"staged_artifact_changed_during_release"',
        '"staged_artifact_replaced_during_verification"',
        '"staged_artifact_replaced_during_release"',
        "initial_identity = (initial_stat.st_dev, initial_stat.st_ino)",
        'final_path.is_symlink()',
        'sha256_file(final_path) != before_digest',
    ):
        require(token in source, f"implementation missing invariant: {token}")

    for phrase in (
        "does not connect directly to `clamd`",
        "clean malware scan is not an execution authorization",
        "production_runtime_status` remains `unaccepted`",
        "private staging",
        "privacy shield",
    ):
        require(phrase in docs, f"documentation missing boundary: {phrase}")

    print("GoreeCloud AI Wardveil artifact integration validation passed.")


if __name__ == "__main__":
    main()
