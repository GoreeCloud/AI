"""Two-stage, local-only action review contract. Never executes a service.

The local model proposes an action for review. A distinct later invocation,
with trusted Policy and consent evidence, can reserve it in the replay ledger.
This reference cannot authenticate the evidence's issuer or issue approvals.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field

from reference.capability_arguments import canonical_arguments, ArgumentError
from reference.capability_authorization import ApprovalEvidence, PolicyEvidence, VerifiedIdentity
from reference.capability_replay_ledger import ReplayError, ReplayLedger
from reference.capability_requirements import RequirementCatalog, RequirementError
from reference.integration_directory import IntegrationDirectory, IntegrationError
from reference.local_action_planner import LocalProposalError, propose_with_local_ollama
from reference.local_model_gateway import LocalOllamaGateway
from reference.model_action_proposal import ActionProposal
from reference.proposal_policy_handoff import HandoffError, InputRule, check_input, prepare_plan
from reference.local_preflight_pipeline import PreflightPreview


class ReviewError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fingerprint(proposal: ActionProposal, identity: VerifiedIdentity,
                 transport: str, connection_id: str, risk: str) -> str:
    data = [identity.subject, identity.tenant, identity.session,
            proposal.intent.request_id, proposal.intent.service,
            proposal.intent.operation, proposal.intent.resource,
            proposal.intent.arguments_sha256, proposal.requirement_revision,
            transport, connection_id, risk]
    return hashlib.sha256(json.dumps(
        data, ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReviewDraft:
    """Trusted-backend session state, NOT a signed token or user approval."""
    proposal: ActionProposal = field(repr=False)
    identity: VerifiedIdentity = field(repr=False)
    transport: str
    connection_id: str = field(repr=False)
    risk: str
    issued_at: int
    expires_at: int
    fingerprint: str

    def display(self) -> dict[str, object]:
        """Actual target and arguments for a private consent review.

        Do not log or send this object to the model. Escape text in every UI.
        """
        return {
            "service": self.proposal.intent.service,
            "operation": self.proposal.intent.operation,
            "target": self.proposal.intent.resource,
            "risk": self.risk,
            "arguments": json.loads(canonical_arguments(
                self.proposal.arguments).encoded),
            "status": "awaiting_user_review",
            "execution": "disabled",
        }


def draft_local_review(runtime: LocalOllamaGateway, model: str, user_prompt: str, *,
                       request_id: str, directory: IntegrationDirectory,
                       requirements: RequirementCatalog,
                       permitted_services: frozenset[str],
                       permitted_operations: frozenset[str],
                       rules: tuple[InputRule, ...], target_resource: str,
                       expected_revision: str, expected_connection: str,
                       expected_transport: str, identity: VerifiedIdentity,
                       now: int) -> ReviewDraft:
    """Draft and validate; deliberately does not require or grant approval."""
    if (type(identity) is not VerifiedIdentity or type(now) is not int
            or now < 0 or type(identity.expires_at) is not int
            or identity.expires_at <= now):
        raise ReviewError("identity_unverified")
    try:
        proposal = propose_with_local_ollama(
            runtime, model, user_prompt, request_id=request_id,
            directory=directory, requirements=requirements,
            permitted_services=permitted_services,
            permitted_operations=permitted_operations,
        ).draft
        if type(target_resource) is not str or proposal.intent.resource != target_resource:
            raise ReviewError("target_denied")
        check_input(proposal, rules)
        route = directory.resolve(proposal.intent.service, proposal.intent.operation,
                                  permitted_services=permitted_services,
                                  permitted_operations=permitted_operations)
        requirement = requirements.resolve(proposal.intent.service,
                                           proposal.intent.operation, route.transport)
        if (route.transport != expected_transport
                or route.connection_id != expected_connection
                or requirement.revision != expected_revision
                or proposal.requirement_revision != expected_revision
                or proposal.minimum_risk != requirement.minimum_risk):
            raise ReviewError("capability_changed")
        # Detach the exact canonical model payload before returning review state.
        args = json.loads(canonical_arguments(proposal.arguments).encoded)
        frozen_proposal = ActionProposal(proposal.intent, args,
                                         proposal.minimum_risk,
                                         proposal.requirement_revision)
        expires_at = min(identity.expires_at, now + 300)
        return ReviewDraft(
            frozen_proposal, identity, route.transport, route.connection_id,
            requirement.minimum_risk, now, expires_at,
            _fingerprint(frozen_proposal, identity, route.transport,
                         route.connection_id, requirement.minimum_risk),
        )
    except (LocalProposalError, HandoffError, IntegrationError, RequirementError,
            ArgumentError) as exc:
        raise ReviewError(getattr(exc, "code", "review_unavailable")) from exc


def reserve_reviewed_action(review: ReviewDraft, directory: IntegrationDirectory,
                            requirements: RequirementCatalog, *,
                            policy: PolicyEvidence, approval: ApprovalEvidence | None,
                            identity: VerifiedIdentity, rules: tuple[InputRule, ...],
                            ledger: ReplayLedger, now: int) -> PreflightPreview:
    """Review completed elsewhere; verify fresh evidence and reserve only."""
    if (type(review) is not ReviewDraft or type(identity) is not VerifiedIdentity
            or type(ledger) is not ReplayLedger or type(now) is not int
            or now < review.issued_at or now >= review.expires_at
            or identity != review.identity or identity.expires_at <= now):
        raise ReviewError("review_expired_or_changed")
    proposal = review.proposal
    expected = _fingerprint(proposal, identity, review.transport,
                            review.connection_id, review.risk)
    if (type(review.fingerprint) is not str
            or not hmac.compare_digest(review.fingerprint, expected)):
        raise ReviewError("review_changed")
    try:
        plan = prepare_plan(
            proposal, directory, requirements,
            rules=rules, target_resource=proposal.intent.resource,
            expected_revision=proposal.requirement_revision,
            expected_connection=review.connection_id,
            expected_transport=review.transport,
            identity=identity, policy=policy, approval=approval, now=now,
        )
        if plan.risk != review.risk:
            # A risk or policy escalation requires a fresh review.
            raise ReviewError("review_changed")
        ledger.reserve(plan, now=now)
    except (HandoffError, ReplayError) as exc:
        raise ReviewError(exc.code) from exc
    return PreflightPreview(plan.service, plan.operation, plan.risk,
                            len(proposal.arguments))
