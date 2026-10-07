#!/usr/bin/env python3
"""Consumer boundary for GoreeCloud Code repository file context."""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Protocol
from urllib.parse import urlparse

CODE_REPOSITORY_FILE_CONTEXT_CONTRACT_VERSION = "0.1.0"
MAX_FILE_CONTEXT_CHARS = 65_536
DEFAULT_MAX_AGE = timedelta(minutes=5)

_TOP_LEVEL_KEYS = {
    "contractVersion",
    "recordType",
    "producer",
    "scope",
    "generatedAt",
    "source",
    "repository",
    "file",
    "limits",
    "evidence",
}
_REPOSITORY_KEYS = {"id", "owner", "name", "private", "webUrl"}
_FILE_KEYS = {
    "path",
    "sha",
    "size",
    "encoding",
    "content",
    "contentSha256",
    "truncated",
    "webUrl",
}
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
from reference.repository_path_policy import repository_path_allowed

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _valid_file_path_shape(path: str) -> bool:
    if not path or len(path) > 1_024 or path.startswith("/") or path.endswith("/") or "\\" in path:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in path):
        return False
    return all(segment not in {"", ".", ".."} for segment in path.split("/"))


@dataclass(frozen=True)
class RepositoryFileContextTarget:
    owner: str
    name: str
    ref: str
    path: str

    def validate(self) -> None:
        if not self.owner or not self.name or not self.ref or not self.path:
            raise ValueError("repository_file_context_scope_required")
        if len(self.owner) > 256 or len(self.name) > 256 or len(self.ref) > 255 or len(self.path) > 1_024:
            raise ValueError("repository_file_context_scope_invalid")
        if not _valid_file_path_shape(self.path):
            raise ValueError("repository_file_context_scope_invalid")
        if not repository_path_allowed(self.path):
            raise ValueError("repository_file_context_path_blocked")


@dataclass(frozen=True)
class RepositoryFileContextDecision:
    accepted: bool
    reason_codes: tuple[str, ...]
    generated_at: str | None
    source_provider: str | None
    content_trust: str = "untrusted_repository_file_data"
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
class RepositoryFileContextIntakeResult:
    decision: RepositoryFileContextDecision
    context: Mapping[str, object] | None


class GoreeCloudCodeFileContextProvider(Protocol):
    def fetch_repository_file_context(
        self,
        *,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> Mapping[str, object]:
        """Return the GoreeCloud Code repository_file_context envelope."""


def _blocked(reason: str) -> RepositoryFileContextDecision:
    return RepositoryFileContextDecision(
        accepted=False,
        reason_codes=(reason,),
        generated_at=None,
        source_provider=None,
    )


def evaluate_repository_file_context(
    payload: object,
    target: RepositoryFileContextTarget,
    *,
    now: datetime | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> RepositoryFileContextDecision:
    target.validate()
    observed_now = _utc(now)

    if not isinstance(payload, Mapping):
        return _blocked("repository_file_context_not_object")
    if _contains_sensitive_key(payload):
        return _blocked("repository_file_context_contains_sensitive_key")
    if _unexpected_keys(payload, _TOP_LEVEL_KEYS):
        return _blocked("repository_file_context_unexpected_top_level_field")
    if payload.get("contractVersion") != CODE_REPOSITORY_FILE_CONTEXT_CONTRACT_VERSION:
        return _blocked("unsupported_repository_file_context_contract")
    if payload.get("recordType") != "repository_file_context":
        return _blocked("unexpected_repository_file_context_record_type")

    producer = payload.get("producer")
    if not isinstance(producer, Mapping) or _unexpected_keys(producer, {"service", "authoritative", "role"}):
        return _blocked("invalid_repository_file_context_producer")
    if (
        producer.get("service") != "goreecloud-code-api"
        or producer.get("authoritative") is not False
        or producer.get("role") != "provider-neutral-evidence-broker"
    ):
        return _blocked("untrusted_repository_file_context_producer")

    scope = payload.get("scope")
    if not isinstance(scope, Mapping) or _unexpected_keys(scope, {"repository", "repositoryId", "ref", "path"}):
        return _blocked("invalid_repository_file_context_scope")
    scoped_repository = scope.get("repository")
    if not isinstance(scoped_repository, Mapping) or _unexpected_keys(scoped_repository, {"owner", "name"}):
        return _blocked("invalid_repository_file_context_scope")
    if scoped_repository.get("owner") != target.owner or scoped_repository.get("name") != target.name:
        return _blocked("repository_file_context_scope_mismatch")
    if scope.get("ref") != target.ref:
        return _blocked("repository_file_context_ref_mismatch")
    if scope.get("path") != target.path:
        return _blocked("repository_file_context_path_mismatch")
    if not repository_path_allowed(target.path):
        return _blocked("repository_file_context_path_blocked")

    repository = payload.get("repository")
    if not isinstance(repository, Mapping) or _unexpected_keys(repository, _REPOSITORY_KEYS):
        return _blocked("invalid_repository_file_context_repository")
    if repository.get("owner") != target.owner or repository.get("name") != target.name:
        return _blocked("repository_file_context_repository_mismatch")
    if not _bounded_string(repository.get("id"), 256, required=True):
        return _blocked("repository_file_context_repository_id_missing")
    if scope.get("repositoryId") != repository.get("id"):
        return _blocked("repository_file_context_repository_id_mismatch")
    if not isinstance(repository.get("private"), bool):
        return _blocked("repository_file_context_visibility_invalid")
    if not _is_web_url(repository.get("webUrl")):
        return _blocked("repository_file_context_invalid_repository_url")

    source = payload.get("source")
    if not isinstance(source, Mapping) or _unexpected_keys(source, {"provider", "providerHealthy", "capabilities"}):
        return _blocked("invalid_repository_file_context_source")
    provider = source.get("provider")
    capabilities = source.get("capabilities")
    if not isinstance(provider, str) or not provider:
        return _blocked("repository_file_context_provider_missing")
    if source.get("providerHealthy") is not True:
        return _blocked("repository_file_context_provider_unhealthy")
    if (
        not isinstance(capabilities, list)
        or len(capabilities) > 32
        or any(not _bounded_string(capability, 128, required=True) for capability in capabilities)
        or len(set(capabilities)) != len(capabilities)
        or "repositories:read" not in capabilities
    ):
        return _blocked("repository_file_context_read_capability_missing")

    generated = payload.get("generatedAt")
    try:
        generated_at = _parse_instant(generated)
    except (TypeError, ValueError):
        return _blocked("repository_file_context_invalid_generated_time")
    if generated_at > observed_now:
        return _blocked("repository_file_context_future_dated")
    if observed_now - generated_at > max_age:
        return _blocked("repository_file_context_stale")

    file_context = payload.get("file")
    if not isinstance(file_context, Mapping) or _unexpected_keys(file_context, _FILE_KEYS):
        return _blocked("invalid_repository_file_context_file")
    if file_context.get("path") != target.path or not _bounded_string(file_context.get("path"), 1_024, required=True):
        return _blocked("repository_file_context_file_path_mismatch")
    if not _bounded_string(file_context.get("sha"), 128, required=True):
        return _blocked("repository_file_context_file_sha_invalid")
    size = file_context.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        return _blocked("repository_file_context_file_size_invalid")
    if file_context.get("encoding") != "utf-8":
        return _blocked("repository_file_context_encoding_invalid")
    content = file_context.get("content")
    if not isinstance(content, str) or len(content) > MAX_FILE_CONTEXT_CHARS:
        return _blocked("repository_file_context_content_invalid")
    digest = file_context.get("contentSha256")
    if not isinstance(digest, str) or _HASH_RE.fullmatch(digest) is None:
        return _blocked("repository_file_context_digest_invalid")
    truncated = file_context.get("truncated")
    if not isinstance(truncated, bool):
        return _blocked("repository_file_context_truncation_invalid")
    if truncated and len(content) != MAX_FILE_CONTEXT_CHARS:
        return _blocked("repository_file_context_truncation_invalid")
    if not truncated and hashlib.sha256(content.encode("utf-8")).hexdigest() != digest:
        return _blocked("repository_file_context_digest_mismatch")
    if file_context.get("webUrl") is not None and not _is_web_url(file_context.get("webUrl")):
        return _blocked("repository_file_context_invalid_file_url")

    limits = payload.get("limits")
    if (
        not isinstance(limits, Mapping)
        or _unexpected_keys(limits, {"contentChars"})
        or limits.get("contentChars") != MAX_FILE_CONTEXT_CHARS
    ):
        return _blocked("repository_file_context_invalid_limits")

    evidence = payload.get("evidence")
    if not isinstance(evidence, Mapping) or _unexpected_keys(evidence, {"webUrls"}):
        return _blocked("invalid_repository_file_context_evidence")
    web_urls = evidence.get("webUrls")
    if (
        not isinstance(web_urls, list)
        or len(web_urls) > 8
        or any(not _is_web_url(url) or len(url) > 4_096 for url in web_urls)
        or len(set(web_urls)) != len(web_urls)
    ):
        return _blocked("repository_file_context_invalid_evidence_url")

    return RepositoryFileContextDecision(
        accepted=True,
        reason_codes=("goreecloud_code_repository_file_context_accepted",),
        generated_at=generated_at.isoformat(),
        source_provider=provider,
    )


class RepositoryFileContextIntakeGate:
    def __init__(self, provider: GoreeCloudCodeFileContextProvider):
        self._provider = provider

    def load(
        self,
        *,
        target: RepositoryFileContextTarget,
        now: datetime | None = None,
        max_age: timedelta = DEFAULT_MAX_AGE,
    ) -> RepositoryFileContextIntakeResult:
        target.validate()
        try:
            payload = self._provider.fetch_repository_file_context(
                owner=target.owner,
                name=target.name,
                ref=target.ref,
                path=target.path,
            )
        except Exception:
            return RepositoryFileContextIntakeResult(
                decision=_blocked("goreecloud_code_repository_file_context_unavailable"),
                context=None,
            )

        decision = evaluate_repository_file_context(payload, target, now=now, max_age=max_age)
        return RepositoryFileContextIntakeResult(
            decision=decision,
            context=deepcopy(dict(payload)) if decision.accepted else None,
        )
