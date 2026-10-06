#!/usr/bin/env python3
"""Consumer boundary for GoreeCloud Code repository context.

GoreeCloud AI consumes a bounded provider-neutral repository snapshot from
GoreeCloud Code. The snapshot is untrusted input: repository-controlled text
can contain misleading or adversarial instructions. Structural acceptance is
therefore never execution, tool, policy, or write authorization.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Protocol
from urllib.parse import urlparse

CODE_REPOSITORY_CONTEXT_CONTRACT_VERSION = "0.1.0"
MAX_CONTEXT_ITEMS = 20
DEFAULT_MAX_AGE = timedelta(minutes=5)

_TOP_LEVEL_KEYS = {
    "contractVersion",
    "recordType",
    "producer",
    "scope",
    "generatedAt",
    "source",
    "repository",
    "branches",
    "commits",
    "issues",
    "pullRequests",
    "limits",
    "evidence",
}
_REPOSITORY_KEYS = {
    "id",
    "owner",
    "name",
    "description",
    "defaultBranch",
    "private",
    "webUrl",
    "updatedAt",
}
_ITEM_KEYS = {
    "branches": {"name", "sha", "protected"},
    "commits": {"sha", "message", "authoredAt", "authorName", "webUrl"},
    "issues": {"number", "title", "state", "author", "updatedAt", "webUrl"},
    "pullRequests": {"number", "title", "state", "base", "head", "author", "updatedAt", "webUrl"},
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


@dataclass(frozen=True)
class RepositoryContextTarget:
    owner: str
    name: str
    ref: str | None = None

    def validate(self) -> None:
        if not self.owner or not self.name:
            raise ValueError("repository_identity_required")


@dataclass(frozen=True)
class RepositoryContextDecision:
    accepted: bool
    reason_codes: tuple[str, ...]
    generated_at: str | None
    source_provider: str | None
    content_trust: str = "untrusted_repository_data"
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
class RepositoryContextIntakeResult:
    decision: RepositoryContextDecision
    context: Mapping[str, object] | None


class GoreeCloudCodeContextProvider(Protocol):
    def fetch_repository_context(
        self,
        *,
        owner: str,
        name: str,
        ref: str | None = None,
    ) -> Mapping[str, object]:
        """Return the GoreeCloud Code repository_context envelope."""


def _blocked(reason: str) -> RepositoryContextDecision:
    return RepositoryContextDecision(
        accepted=False,
        reason_codes=(reason,),
        generated_at=None,
        source_provider=None,
    )


def evaluate_repository_context(
    payload: object,
    target: RepositoryContextTarget,
    *,
    now: datetime | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> RepositoryContextDecision:
    """Validate a GoreeCloud Code repository context envelope.

    Acceptance means only that the envelope is structurally bounded, fresh,
    scope-bound, provider-healthy, and free of known credential-bearing keys.
    Repository-controlled text remains untrusted data.
    """
    target.validate()
    observed_now = _utc(now)

    if not isinstance(payload, Mapping):
        return _blocked("repository_context_not_object")
    if _contains_sensitive_key(payload):
        return _blocked("repository_context_contains_sensitive_key")
    if _unexpected_keys(payload, _TOP_LEVEL_KEYS):
        return _blocked("repository_context_unexpected_top_level_field")
    if payload.get("contractVersion") != CODE_REPOSITORY_CONTEXT_CONTRACT_VERSION:
        return _blocked("unsupported_repository_context_contract")
    if payload.get("recordType") != "repository_context":
        return _blocked("unexpected_repository_context_record_type")

    producer = payload.get("producer")
    if not isinstance(producer, Mapping) or _unexpected_keys(producer, {"service", "authoritative", "role"}):
        return _blocked("invalid_repository_context_producer")
    if (
        producer.get("service") != "goreecloud-code-api"
        or producer.get("authoritative") is not False
        or producer.get("role") != "provider-neutral-evidence-broker"
    ):
        return _blocked("untrusted_repository_context_producer")

    scope = payload.get("scope")
    if not isinstance(scope, Mapping) or _unexpected_keys(scope, {"repository", "repositoryId", "ref"}):
        return _blocked("invalid_repository_context_scope")
    scoped_repository = scope.get("repository")
    if not isinstance(scoped_repository, Mapping) or _unexpected_keys(scoped_repository, {"owner", "name"}):
        return _blocked("invalid_repository_context_scope")
    if scoped_repository.get("owner") != target.owner or scoped_repository.get("name") != target.name:
        return _blocked("repository_context_scope_mismatch")
    if target.ref is not None and scope.get("ref") != target.ref:
        return _blocked("repository_context_ref_mismatch")

    repository = payload.get("repository")
    if not isinstance(repository, Mapping) or _unexpected_keys(repository, _REPOSITORY_KEYS):
        return _blocked("invalid_repository_context_repository")
    if repository.get("owner") != target.owner or repository.get("name") != target.name:
        return _blocked("repository_context_repository_mismatch")
    if not isinstance(repository.get("id"), str) or not repository.get("id"):
        return _blocked("repository_context_repository_id_missing")
    if scope.get("repositoryId") != repository.get("id"):
        return _blocked("repository_context_repository_id_mismatch")
    if not _is_web_url(repository.get("webUrl")):
        return _blocked("repository_context_invalid_repository_url")

    source = payload.get("source")
    if not isinstance(source, Mapping) or _unexpected_keys(source, {"provider", "providerHealthy", "capabilities"}):
        return _blocked("invalid_repository_context_source")
    provider = source.get("provider")
    capabilities = source.get("capabilities")
    if not isinstance(provider, str) or not provider:
        return _blocked("repository_context_provider_missing")
    if source.get("providerHealthy") is not True:
        return _blocked("repository_context_provider_unhealthy")
    if not isinstance(capabilities, list) or "repositories:read" not in capabilities:
        return _blocked("repository_context_read_capability_missing")

    generated = payload.get("generatedAt")
    try:
        generated_at = _parse_instant(generated)
    except (TypeError, ValueError):
        return _blocked("repository_context_invalid_generated_time")
    if generated_at > observed_now:
        return _blocked("repository_context_future_dated")
    if observed_now - generated_at > max_age:
        return _blocked("repository_context_stale")

    limits = payload.get("limits")
    if not isinstance(limits, Mapping) or _unexpected_keys(limits, set(_ITEM_KEYS)):
        return _blocked("invalid_repository_context_limits")

    for collection_name, allowed_keys in _ITEM_KEYS.items():
        limit = limits.get(collection_name)
        collection = payload.get(collection_name)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0 or limit > MAX_CONTEXT_ITEMS:
            return _blocked(f"repository_context_invalid_{collection_name}_limit")
        if not isinstance(collection, list):
            return _blocked(f"repository_context_invalid_{collection_name}")
        if len(collection) > limit or len(collection) > MAX_CONTEXT_ITEMS:
            return _blocked(f"repository_context_{collection_name}_limit_exceeded")
        for item in collection:
            if not isinstance(item, Mapping) or _unexpected_keys(item, allowed_keys):
                return _blocked(f"repository_context_invalid_{collection_name}_item")

    evidence = payload.get("evidence")
    if not isinstance(evidence, Mapping) or _unexpected_keys(evidence, {"webUrls"}):
        return _blocked("invalid_repository_context_evidence")
    web_urls = evidence.get("webUrls")
    if not isinstance(web_urls, list) or len(web_urls) > 64 or any(not _is_web_url(url) for url in web_urls):
        return _blocked("repository_context_invalid_evidence_url")

    return RepositoryContextDecision(
        accepted=True,
        reason_codes=("goreecloud_code_repository_context_accepted",),
        generated_at=generated_at.isoformat(),
        source_provider=provider,
    )


class RepositoryContextIntakeGate:
    """Fail-closed GoreeCloud AI intake for GoreeCloud Code repository context."""

    def __init__(self, provider: GoreeCloudCodeContextProvider):
        self._provider = provider

    def load(
        self,
        *,
        target: RepositoryContextTarget,
        now: datetime | None = None,
        max_age: timedelta = DEFAULT_MAX_AGE,
    ) -> RepositoryContextIntakeResult:
        target.validate()
        try:
            payload = self._provider.fetch_repository_context(
                owner=target.owner,
                name=target.name,
                ref=target.ref,
            )
        except Exception:
            return RepositoryContextIntakeResult(
                decision=_blocked("goreecloud_code_repository_context_unavailable"),
                context=None,
            )

        decision = evaluate_repository_context(payload, target, now=now, max_age=max_age)
        return RepositoryContextIntakeResult(
            decision=decision,
            context=deepcopy(dict(payload)) if decision.accepted else None,
        )
