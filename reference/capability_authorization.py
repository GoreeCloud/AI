"""Development-only, non-executing capability authorization gate.

All evidence inputs MUST originate from trusted backend Identity, Policy, and
approval adapters. This pure reference module cannot authenticate those origins,
manage credentials, log audit evidence, or authorize live network execution.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from reference.integration_directory import IntegrationDirectory, IntegrationError, PinnedRoute
from reference.capability_requirements import RequirementCatalog, RequirementError, effective_risk

_SLUG = re.compile(r"^[a-z][a-z0-9_.:-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_RISKS = frozenset({"read", "write", "sensitive"})


class AuthorizationError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _valid_id(value: object) -> bool:
    return type(value) is str and _SLUG.fullmatch(value) is not None


@dataclass(frozen=True)
class CapabilityIntent:
    """Untrusted model-requested action metadata, NOT an execution command."""
    request_id: str
    service: str
    operation: str
    resource: str
    arguments_sha256: str

    def __post_init__(self) -> None:
        if (not all(_valid_id(v) for v in (self.request_id, self.service, self.operation))
                or type(self.resource) is not str or not 1 <= len(self.resource) <= 512
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in self.resource)
                or type(self.arguments_sha256) is not str
                or _DIGEST.fullmatch(self.arguments_sha256) is None):
            raise AuthorizationError("invalid_intent")


@dataclass(frozen=True)
class VerifiedIdentity:
    """Evidence supplied by the trusted Identity adapter, never by the model."""
    subject: str
    tenant: str
    session: str
    expires_at: int


@dataclass(frozen=True)
class PolicyEvidence:
    """Exact-request result from the trusted Policy + domain-authority adapters."""
    request_id: str
    subject: str
    tenant: str
    service: str
    operation: str
    resource: str
    arguments_sha256: str
    decision: str
    risk: str
    policy_revision: str
    expires_at: int
    permitted_services: frozenset[str]
    permitted_operations: frozenset[str]


@dataclass(frozen=True)
class ApprovalEvidence:
    """Trusted step-up/consent receipt bound to the exact proposed action."""
    request_id: str
    subject: str
    tenant: str
    session: str
    service: str
    operation: str
    resource: str
    arguments_sha256: str
    expires_at: int
    approved: bool


@dataclass(frozen=True)
class AuthorizedRoute:
    """Internal planning receipt only; NOT a bearer token or execution permit."""
    request_id: str
    subject: str
    tenant: str
    service: str
    operation: str
    resource: str
    arguments_sha256: str
    risk: str
    policy_revision: str
    requirement_revision: str
    route: PinnedRoute


def authorize(
    directory: IntegrationDirectory,
    requirements: RequirementCatalog,
    intent: CapabilityIntent,
    *,
    identity: VerifiedIdentity,
    policy: PolicyEvidence,
    approval: ApprovalEvidence | None = None,
    now: int,
) -> AuthorizedRoute:
    """Fail-closed plan after trusted adapters provide fresh, bound evidence.

    The actual executor must independently recheck policy, approval, connector
    binding/version, resource scope, args hash and replay/idempotency state.
    """
    if (type(directory) is not IntegrationDirectory
            or type(requirements) is not RequirementCatalog
            or type(intent) is not CapabilityIntent):
        raise AuthorizationError("invalid_request")
    if type(now) is not int or now < 0:
        raise AuthorizationError("invalid_clock")
    if (type(identity) is not VerifiedIdentity
            or any(not _valid_id(v) for v in (identity.subject, identity.tenant, identity.session))
            or type(identity.expires_at) is not int or identity.expires_at <= now):
        raise AuthorizationError("identity_unverified")
    if (type(policy) is not PolicyEvidence
            or policy.decision != "allow" or type(policy.risk) is not str or policy.risk not in _RISKS
            or not _valid_id(policy.policy_revision)
            or type(policy.expires_at) is not int or not now < policy.expires_at <= now + 300
            or (policy.request_id, policy.subject, policy.tenant, policy.service,
                policy.operation, policy.resource, policy.arguments_sha256)
            != (intent.request_id, identity.subject, identity.tenant, intent.service,
                intent.operation, intent.resource, intent.arguments_sha256)
            or type(policy.permitted_services) is not frozenset
            or type(policy.permitted_operations) is not frozenset):
        raise AuthorizationError("policy_denied")
    try:
        route = directory.resolve(intent.service, intent.operation,
                                  permitted_services=policy.permitted_services,
                                  permitted_operations=policy.permitted_operations)
        requirement = requirements.resolve(intent.service, intent.operation, route.transport)
        risk = effective_risk(requirement.minimum_risk, policy.risk)
    except (IntegrationError, RequirementError, TypeError, ValueError) as exc:
        raise AuthorizationError("capability_unavailable") from exc
    if risk != "read":
        if (type(approval) is not ApprovalEvidence or approval.approved is not True
                or type(approval.expires_at) is not int
                or not now < approval.expires_at <= now + 300
                or (approval.request_id, approval.subject, approval.tenant,
                    approval.session, approval.service, approval.operation,
                    approval.resource, approval.arguments_sha256)
                != (intent.request_id, identity.subject, identity.tenant,
                    identity.session, intent.service, intent.operation,
                    intent.resource, intent.arguments_sha256)):
            raise AuthorizationError("approval_required")
    return AuthorizedRoute(intent.request_id, identity.subject, identity.tenant,
                           intent.service, intent.operation, intent.resource,
                           intent.arguments_sha256, risk,
                           policy.policy_revision, requirement.revision, route)
