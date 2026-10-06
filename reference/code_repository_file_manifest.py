#!/usr/bin/env python3
"""Consumer boundary for GoreeCloud Code repository file manifests."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Protocol
from urllib.parse import urlparse

from reference.repository_path_policy import repository_path_allowed

CODE_REPOSITORY_FILE_MANIFEST_CONTRACT_VERSION = "0.1.0"
MAX_FILE_MANIFEST_ITEMS = 128
DEFAULT_MAX_AGE = timedelta(minutes=5)
_CONTENT_TYPES = {"file", "directory", "symlink", "submodule", "unknown"}

_TOP_LEVEL_KEYS = {
    "contractVersion",
    "recordType",
    "producer",
    "scope",
    "generatedAt",
    "source",
    "repository",
    "entries",
    "truncated",
    "limits",
    "evidence",
}
_REPOSITORY_KEYS = {"id", "owner", "name", "private", "webUrl"}
_ENTRY_KEYS = {"name", "path", "type", "size", "sha"}
_SENSITIVE_KEYS = {
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "private_key",
    "cookie",
    "set_cookie",
}


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


def _unexpected_keys(value: Mapping[str, object], allowed: set[str]) -> bool:
    return any(not isinstance(key, str) or key not in allowed for key in value)


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _contains_sensitive_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                normalized = _normalize_key(key)
                if (
                    normalized in _SENSITIVE_KEYS
                    or normalized.endswith("_token")
                    or normalized.endswith("_secret")
                    or normalized.endswith("_password")
                    or normalized.endswith("_private_key")
                    or normalized.endswith("_api_key")
                ):
                    return True
            if _contains_sensitive_key(child):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _is_web_url(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _bounded_string(value: object, maximum: int, *, required: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    if required and not value:
        return False
    return len(value) <= maximum


def _path_shape_valid(path: str, *, allow_root: bool) -> bool:
    if allow_root and path == "":
        return True
    if not path or len(path) > 1_024 or path.startswith("/") or path.endswith("/") or "\" in path:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in path):
        return False
    return all(segment not in {"", ".", ".."} for segment in path.split("/"))


@dataclass(frozen=True)
class RepositoryFileManifestTarget:
    owner: str
    name: str
    ref: str
    path: str = ""

    def validate(self) -> None:
        if not self.owner or not self.name or not self.ref:
            raise ValueError("repository_file_manifest_scope_required")
        if len(self.owner) > 256 or len(self.name) > 256 or len(self.ref) > 255:
            raise ValueError("repository_file_manifest_scope_invalid")
        if not _path_shape_valid(self.path, allow_root=True):
            raise ValueError("repository_file_manifest_scope_invalid")
        if self.path and not repository_path_allowed(self.path):
            raise ValueError("repository_file_manifest_path_blocked")


@dataclass(frozen=True)
class RepositoryFileManifestDecision:
    accepted: bool
    reason_codes: tuple[str, ...]
    generated_at: str | None
    source_provider: str | None
    content_trust: str = "untrusted_repository_path_data"
    execution_authorized: bool = False
    write_authorized: bool = False

    def as_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
            "generated_at": self.generated_at,
            "source_provider": self.source_provider,
            "content_trust": self.content_trust,
            "execution_authorized": self.execution_authorized,
            "write_authorized": self.write_authorized,
        }


@dataclass(frozen=True)
class RepositoryFileManifestIntakeResult:
    decision: RepositoryFileManifestDecision
    context: Mapping[str, object] | None


class GoreeCloudCodeFileManifestProvider(Protocol):
    def fetch_repository_file_manifest(
        self,
        *,
        owner: str,
        name: str,
        ref: str,
        path: str = "",
    ) -> Mapping[str, object]:
        """Return the GoreeCloud Code repository_file_manifest envelope."""


def _blocked(reason: str) -> RepositoryFileManifestDecision:
    return RepositoryFileManifestDecision(
        accepted=False,
        reason_codes=(reason,),
        generated_at=None,
        source_provider=None,
    )


def evaluate_repository_file_manifest(
    payload: object,
    target: RepositoryFileManifestTarget,
    *,
    now: datetime | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> RepositoryFileManifestDecision:
    target.validate()
    observed_now = _utc(now)

    if not isinstance(payload, Mapping):
        return _blocked("repository_file_manifest_not_object")
    if _contains_sensitive_key(payload):
        return _blocked("repository_file_manifest_contains_sensitive_key")
    if _unexpected_keys(payload, _TOP_LEVEL_KEYS):
        return _blocked("repository_file_manifest_unexpected_top_level_field")
    if payload.get("contractVersion") != CODE_REPOSITORY_FILE_MANIFEST_CONTRACT_VERSION:
        return _blocked("unsupported_repository_file_manifest_contract")
    if payload.get("recordType") != "repository_file_manifest":
        return _blocked("unexpected_repository_file_manifest_record_type")

    producer = payload.get("producer")
    if not isinstance(producer, Mapping) or _unexpected_keys(producer, {"service", "authoritative", "role"}):
        return _blocked("invalid_repository_file_manifest_producer")
    if (
        producer.get("service") != "goreecloud-code-api"
        or producer.get("authoritative") is not False
        or producer.get("role") != "provider-neutral-evidence-broker"
    ):
        return _blocked("untrusted_repository_file_manifest_producer")

    scope = payload.get("scope")
    if not isinstance(scope, Mapping) or _unexpected_keys(scope, {"repository", "repositoryId", "ref", "path"}):
        return _blocked("invalid_repository_file_manifest_scope")
    scoped_repository = scope.get("repository")
    if not isinstance(scoped_repository, Mapping) or _unexpected_keys(scoped_repository, {"owner", "name"}):
        return _blocked("invalid_repository_file_manifest_scope")
    if scoped_repository.get("owner") != target.owner or scoped_repository.get("name") != target.name:
        return _blocked("repository_file_manifest_scope_mismatch")
    if scope.get("ref") != target.ref:
        return _blocked("repository_file_manifest_ref_mismatch")
    if scope.get("path") != target.path:
        return _blocked("repository_file_manifest_path_mismatch")

    repository = payload.get("repository")
    if not isinstance(repository, Mapping) or _unexpected_keys(repository, _REPOSITORY_KEYS):
        return _blocked("invalid_repository_file_manifest_repository")
    if repository.get("owner") != target.owner or repository.get("name") != target.name:
        return _blocked("repository_file_manifest_repository_mismatch")
    if not _bounded_string(repository.get("id"), 256, required=True):
        return _blocked("repository_file_manifest_repository_id_missing")
    if scope.get("repositoryId") != repository.get("id"):
        return _blocked("repository_file_manifest_repository_id_mismatch")
    if not isinstance(repository.get("private"), bool):
        return _blocked("repository_file_manifest_visibility_invalid")
    if not _is_web_url(repository.get("webUrl")):
        return _blocked("repository_file_manifest_invalid_repository_url")

    source = payload.get("source")
    if not isinstance(source, Mapping) or _unexpected_keys(source, {"provider", "providerHealthy", "capabilities"}):
        return _blocked("invalid_repository_file_manifest_source")
    provider = source.get("provider")
    capabilities = source.get("capabilities")
    if not isinstance(provider, str) or not provider:
        return _blocked("repository_file_manifest_provider_missing")
    if source.get("providerHealthy") is not True:
        return _blocked("repository_file_manifest_provider_unhealthy")
    if (
        not isinstance(capabilities, list)
        or len(capabilities) > 32
        or any(not _bounded_string(capability, 128, required=True) for capability in capabilities)
        or len(set(capabilities)) != len(capabilities)
        or "repositories:read" not in capabilities
    ):
        return _blocked("repository_file_manifest_read_capability_missing")

    generated = payload.get("generatedAt")
    try:
        generated_at = _parse_instant(generated)
    except (TypeError, ValueError):
        return _blocked("repository_file_manifest_invalid_generated_time")
    if generated_at > observed_now:
        return _blocked("repository_file_manifest_future_dated")
    if observed_now - generated_at > max_age:
        return _blocked("repository_file_manifest_stale")

    limits = payload.get("limits")
    if (
        not isinstance(limits, Mapping)
        or _unexpected_keys(limits, {"entries"})
        or limits.get("entries") != MAX_FILE_MANIFEST_ITEMS
    ):
        return _blocked("repository_file_manifest_invalid_limits")

    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_FILE_MANIFEST_ITEMS:
        return _blocked("repository_file_manifest_entries_limit_exceeded")
    seen_paths: set[str] = set()
    for item in entries:
        if not isinstance(item, Mapping) or _unexpected_keys(item, _ENTRY_KEYS) or not _ENTRY_KEYS.issubset(item):
            return _blocked("repository_file_manifest_invalid_entry")
        name = item.get("name")
        path = item.get("path")
        size = item.get("size")
        if not _bounded_string(name, 256, required=True) or not _bounded_string(path, 1_024, required=True):
            return _blocked("repository_file_manifest_invalid_entry")
        if not _path_shape_valid(path, allow_root=False) or path.rsplit("/", 1)[-1] != name:
            return _blocked("repository_file_manifest_invalid_entry")
        if target.path:
            if not path.startswith(f"{target.path}/"):
                return _blocked("repository_file_manifest_entry_outside_scope")
            relative = path[len(target.path) + 1 :]
        else:
            relative = path
        if "/" in relative:
            return _blocked("repository_file_manifest_entry_not_direct_child")
        if not repository_path_allowed(path):
            return _blocked("repository_file_manifest_blocked_path_exposed")
        if item.get("type") not in _CONTENT_TYPES:
            return _blocked("repository_file_manifest_invalid_entry")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            return _blocked("repository_file_manifest_invalid_entry")
        if not _bounded_string(item.get("sha"), 128, required=True):
            return _blocked("repository_file_manifest_invalid_entry")
        if path in seen_paths:
            return _blocked("repository_file_manifest_duplicate_path")
        seen_paths.add(path)

    if not isinstance(payload.get("truncated"), bool):
        return _blocked("repository_file_manifest_truncation_invalid")

    evidence = payload.get("evidence")
    if not isinstance(evidence, Mapping) or _unexpected_keys(evidence, {"webUrls"}):
        return _blocked("invalid_repository_file_manifest_evidence")
    web_urls = evidence.get("webUrls")
    if (
        not isinstance(web_urls, list)
        or len(web_urls) > 8
        or any(not _is_web_url(url) or len(url) > 4_096 for url in web_urls)
        or len(set(web_urls)) != len(web_urls)
    ):
        return _blocked("repository_file_manifest_invalid_evidence_url")

    return RepositoryFileManifestDecision(
        accepted=True,
        reason_codes=("goreecloud_code_repository_file_manifest_accepted",),
        generated_at=generated_at.isoformat(),
        source_provider=provider,
    )


class RepositoryFileManifestIntakeGate:
    def __init__(self, provider: GoreeCloudCodeFileManifestProvider):
        self._provider = provider

    def load(
        self,
        *,
        target: RepositoryFileManifestTarget,
        now: datetime | None = None,
        max_age: timedelta = DEFAULT_MAX_AGE,
    ) -> RepositoryFileManifestIntakeResult:
        target.validate()
        try:
            payload = self._provider.fetch_repository_file_manifest(
                owner=target.owner,
                name=target.name,
                ref=target.ref,
                path=target.path,
            )
        except Exception:
            return RepositoryFileManifestIntakeResult(
                decision=_blocked("goreecloud_code_repository_file_manifest_unavailable"),
                context=None,
            )

        decision = evaluate_repository_file_manifest(payload, target, now=now, max_age=max_age)
        return RepositoryFileManifestIntakeResult(
            decision=decision,
            context=deepcopy(dict(payload)) if decision.accepted else None,
        )
