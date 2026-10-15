"""Turn untrusted local model text into a non-executing capability proposal.

Proposals are NEVER permissions, approvals or execution requests. Request IDs,
trusted service/operation grants and backend pinning do not come from Ollama.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from reference.capability_arguments import ArgumentError, canonical_arguments
from reference.capability_authorization import AuthorizationError, CapabilityIntent
from reference.capability_requirements import RequirementCatalog, RequirementError
from reference.integration_directory import IntegrationDirectory, IntegrationError

_SCHEMA = "goreecloud.ai.action-proposal.v1"
_FIELDS = frozenset({"schema", "service", "operation", "resource", "arguments"})
_MAX_RESPONSE_BYTES = 65536


class ProposalError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _object_pairs(pairs: list[tuple[str, object]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ProposalError("invalid_proposal")
        obj[key] = value
    return obj


def _bad_constant(value: str):
    raise ProposalError("invalid_proposal")


@dataclass(frozen=True)
class ActionProposal:
    """Internal, untrusted action draft. Do not serialize into model context."""
    intent: CapabilityIntent
    arguments: dict[str, object] = field(repr=False)
    minimum_risk: str
    requirement_revision: str

    def redacted_preview(self) -> dict[str, object]:
        """User-facing metadata only, without raw arguments or backend IDs."""
        return {
            "service": self.intent.service,
            "operation": self.intent.operation,
            "minimum_risk": self.minimum_risk,
            "argument_count": len(self.arguments),
            "arguments_sha256": self.intent.arguments_sha256,
            "status": "proposed_not_authorized",
        }


def parse_model_proposal(
    response: str,
    *,
    request_id: str,
    directory: IntegrationDirectory,
    requirements: RequirementCatalog,
    permitted_services: frozenset[str],
    permitted_operations: frozenset[str],
) -> ActionProposal:
    """Validate one JSON proposal against trusted, connected scope.

    An allowlisted catalog entry is discovery metadata, not a resource grant.
    Identity, Policy, Privacy Shield, Wardveil, approval, replay and effects
    remain separate mandatory backend responsibilities.
    """
    if (type(response) is not str or not response.strip()
            or type(request_id) is not str
            or type(directory) is not IntegrationDirectory
            or type(requirements) is not RequirementCatalog
            or type(permitted_services) is not frozenset
            or type(permitted_operations) is not frozenset):
        raise ProposalError("invalid_input")
    try:
        raw = response.encode("utf-8")
    except UnicodeError as exc:
        raise ProposalError("invalid_proposal") from exc
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise ProposalError("proposal_too_large")
    try:
        doc = json.loads(response, object_pairs_hook=_object_pairs,
                         parse_constant=_bad_constant)
    except ProposalError:
        raise
    except (TypeError, ValueError, RecursionError) as exc:
        raise ProposalError("invalid_proposal") from exc
    if (type(doc) is not dict or frozenset(doc) != _FIELDS
            or doc["schema"] != _SCHEMA
            or type(doc["service"]) is not str
            or type(doc["operation"]) is not str
            or type(doc["resource"]) is not str
            or type(doc["arguments"]) is not dict):
        raise ProposalError("invalid_proposal")
    try:
        normalized = canonical_arguments(doc["arguments"])
        intent = CapabilityIntent(
            request_id, doc["service"], doc["operation"],
            doc["resource"], normalized.sha256,
        )
    except (ArgumentError, AuthorizationError) as exc:
        raise ProposalError("invalid_proposal") from exc
    try:
        route = directory.resolve(
            intent.service, intent.operation,
            permitted_services=permitted_services,
            permitted_operations=permitted_operations,
        )
        requirement = requirements.resolve(
            intent.service, intent.operation, route.transport,
        )
    except (IntegrationError, RequirementError, TypeError, ValueError) as exc:
        raise ProposalError("capability_unavailable") from exc
    return ActionProposal(intent, doc["arguments"],
                          requirement.minimum_risk, requirement.revision)
