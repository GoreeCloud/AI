#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "code.repository-context.schema.json"
FILE_CONTRACT = ROOT / "contracts" / "code.repository-file-context.schema.json"
MANIFEST_CONTRACT = ROOT / "contracts" / "code.repository-file-manifest.schema.json"
SOURCE = ROOT / "reference" / "code_repository_context.py"
FILE_SOURCE = ROOT / "reference" / "code_repository_file_context.py"
MANIFEST_SOURCE = ROOT / "reference" / "code_repository_file_manifest.py"
MANIFEST_SELECTOR = ROOT / "reference" / "repository_file_manifest_selection.py"
PATH_POLICY = ROOT / "reference" / "repository_path_policy.py"
SELECTOR = ROOT / "reference" / "repository_context_selection.py"
TESTS = ROOT / "scripts" / "test_code_repository_context.py"
FILE_TESTS = ROOT / "scripts" / "test_code_repository_file_context.py"
MANIFEST_TESTS = ROOT / "scripts" / "test_code_repository_file_manifest.py"
DOC = ROOT / "docs" / "CODE_REPOSITORY_CONTEXT.md"
FILE_DOC = ROOT / "docs" / "CODE_REPOSITORY_FILE_CONTEXT.md"
MANIFEST_DOC = ROOT / "docs" / "CODE_REPOSITORY_FILE_MANIFEST.md"
README = ROOT / "README.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"GoreeCloud AI Code-context validation failed: {message}")


def main() -> None:
    for path in (CONTRACT, FILE_CONTRACT, MANIFEST_CONTRACT, SOURCE, FILE_SOURCE, MANIFEST_SOURCE, MANIFEST_SELECTOR, PATH_POLICY, SELECTOR, TESTS, FILE_TESTS, MANIFEST_TESTS, DOC, FILE_DOC, MANIFEST_DOC, README):
        require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}")

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    file_contract = json.loads(FILE_CONTRACT.read_text(encoding="utf-8"))
    manifest_contract = json.loads(MANIFEST_CONTRACT.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")
    file_source = FILE_SOURCE.read_text(encoding="utf-8")
    manifest_source = MANIFEST_SOURCE.read_text(encoding="utf-8")
    manifest_selector = MANIFEST_SELECTOR.read_text(encoding="utf-8")
    path_policy = PATH_POLICY.read_text(encoding="utf-8")
    selector = SELECTOR.read_text(encoding="utf-8")
    docs = (DOC.read_text(encoding="utf-8") + "\n" + FILE_DOC.read_text(encoding="utf-8") + "\n" + MANIFEST_DOC.read_text(encoding="utf-8") + "\n" + README.read_text(encoding="utf-8")).lower()

    properties = contract.get("properties") or {}
    require(properties.get("contractVersion", {}).get("const") == "0.1.0", "unexpected contract version")
    require(properties.get("recordType", {}).get("const") == "repository_context", "unexpected record type")
    require(contract.get("additionalProperties") is False, "top-level contract must reject extra fields")

    producer = properties.get("producer", {}).get("properties") or {}
    require(producer.get("service", {}).get("const") == "goreecloud-code-api", "unexpected producer")
    require(producer.get("authoritative", {}).get("const") is False, "Code envelope must not claim repository authority")

    for collection in ("branches", "commits", "issues", "pullRequests"):
        require(properties.get(collection, {}).get("maxItems") == 20, f"{collection} must remain bounded to 20")

    for token in (
        'CODE_REPOSITORY_CONTEXT_CONTRACT_VERSION = "0.1.0"',
        'MAX_CONTEXT_ITEMS = 20',
        '"repository_context_contains_sensitive_key"',
        '"repository_context_stale"',
        '"repository_context_provider_unhealthy"',
        'content_trust: str = "untrusted_repository_data"',
        "execution_authorized: bool = False",
        "write_authorized: bool = False",
    ):
        require(token in source, f"consumer boundary missing invariant: {token}")

    file_properties = file_contract.get("properties") or {}
    require(file_properties.get("contractVersion", {}).get("const") == "0.1.0", "unexpected file-context contract version")
    require(file_properties.get("recordType", {}).get("const") == "repository_file_context", "unexpected file-context record type")
    require(file_contract.get("additionalProperties") is False, "file-context contract must reject extra fields")
    require(file_properties.get("limits", {}).get("properties", {}).get("contentChars", {}).get("const") == 65536, "file-context character limit drifted")
    require("excerptSha256" in file_properties.get("file", {}).get("required", []), "file excerpt digest must be required")

    for token in (
        'CODE_REPOSITORY_FILE_CONTEXT_CONTRACT_VERSION = "0.1.0"',
        "MAX_FILE_CONTEXT_CHARS = 65_536",
        '"repository_file_context_digest_mismatch"',
        '"repository_file_context_excerpt_digest_mismatch"',
        '"repository_file_context_path_blocked"',
        'content_trust: str = "untrusted_repository_file_data"',
        "execution_authorized: bool = False",
        "write_authorized: bool = False",
    ):
        require(token in file_source, f"file-context consumer boundary missing invariant: {token}")

    manifest_properties = manifest_contract.get("properties") or {}
    require(manifest_properties.get("contractVersion", {}).get("const") == "0.1.0", "unexpected manifest contract version")
    require(manifest_properties.get("recordType", {}).get("const") == "repository_file_manifest", "unexpected manifest record type")
    require(manifest_contract.get("additionalProperties") is False, "manifest contract must reject extra fields")
    require(manifest_properties.get("entries", {}).get("maxItems") == 128, "manifest entry limit drifted")

    for token in (
        'CODE_REPOSITORY_FILE_MANIFEST_CONTRACT_VERSION = "0.1.0"',
        "MAX_FILE_MANIFEST_ITEMS = 128",
        '"repository_file_manifest_blocked_path_exposed"',
        '"repository_file_manifest_entry_not_direct_child"',
        'content_trust: str = "untrusted_repository_path_data"',
        "execution_authorized: bool = False",
        "write_authorized: bool = False",
    ):
        require(token in manifest_source, f"manifest consumer boundary missing invariant: {token}")

    for token in (
        "MAX_QUERY_CHARS = 512",
        "MAX_QUERY_TERMS = 32",
        "MAX_SELECTION_ITEMS = 20",
        "candidates.sort",
    ):
        require(token in manifest_selector, f"manifest selection missing invariant: {token}")

    require("repository_path_allowed" in path_policy, "shared repository path policy missing")
    require("repository_path_allowed" in file_source, "file context must use shared repository path policy")

    for token in (
        "MAX_QUERY_CHARS = 512",
        "MAX_QUERY_TERMS = 32",
        "MAX_RESULT_TEXT_CHARS = 600",
        "ranked.sort",
    ):
        require(token in selector, f"repository selection missing invariant: {token}")

    for phrase in (
        "provider-neutral",
        "untrusted repository content",
        "not an execution authorization",
        "goreecloud code",
        "forgejo credentials",
        "identity",
        "mesh",
    ):
        require(phrase in docs, f"documentation missing boundary: {phrase}")

    print("GoreeCloud AI repository-context integration validation passed.")


if __name__ == "__main__":
    main()
