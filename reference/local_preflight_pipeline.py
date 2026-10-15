"""Development-only synthetic end-to-end AI capability preflight.

This path can ask a loopback Ollama model to draft an action, check backend
evidence, and reserve a request in a reference SQLite ledger. There is NO tool
dispatch, credential access, service mutation, or production authorization.
"""
from __future__ import annotations
from dataclasses import dataclass
from reference.capability_authorization import (
    ApprovalEvidence, PolicyEvidence, VerifiedIdentity,
)
from reference.capability_replay_ledger import ReplayError, ReplayLedger
from reference.capability_requirements import RequirementCatalog
from reference.integration_directory import IntegrationDirectory
from reference.local_action_planner import LocalProposalError, propose_with_local_ollama
from reference.local_model_gateway import LocalOllamaGateway
from reference.proposal_policy_handoff import HandoffError, InputRule, prepare_plan


class PreflightError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PreflightPreview:
    """Redacted result: this is a reservation, NOT an execution permit."""
    service: str
    operation: str
    risk: str
    argument_count: int
    status: str = "reserved_no_execution"
    processing: str = "local"
    execution: str = "disabled"

    def redacted(self) -> dict[str, str | int]:
        return {
            "service": self.service, "operation": self.operation,
            "risk": self.risk, "argument_count": self.argument_count,
            "status": self.status, "processing": self.processing,
            "execution": self.execution,
        }


def simulate_local_preflight(
    runtime: LocalOllamaGateway,
    model: str,
    user_prompt: str,
    *,
    request_id: str,
    directory: IntegrationDirectory,
    requirements: RequirementCatalog,
    permitted_services: frozenset[str],
    permitted_operations: frozenset[str],
    rules: tuple[InputRule, ...],
    target_resource: str,
    expected_revision: str,
    expected_connection: str,
    expected_transport: str,
    identity: VerifiedIdentity,
    policy: PolicyEvidence,
    ledger: ReplayLedger,
    now: int,
    approval: ApprovalEvidence | None = None,
) -> PreflightPreview:
    """Simulate one strict flow without ever executing a service capability.

    Trusted operator/Identity/Policy/approval inputs MUST come from independent
    backend authorities. This pure reference cannot authenticate them. A
    production executor MUST recheck everything at the time of side effect.
    """
    if type(ledger) is not ReplayLedger or type(now) is not int or now < 0:
        raise PreflightError("invalid_preflight")
    # Refuse obvious untrusted/denied contexts before even invoking the model.
    if (type(identity) is not VerifiedIdentity
            or type(identity.expires_at) is not int
            or identity.expires_at <= now
            or type(policy) is not PolicyEvidence
            or policy.decision != "allow"
            or type(policy.expires_at) is not int
            or not now < policy.expires_at <= now + 300
            or policy.request_id != request_id
            or policy.subject != identity.subject
            or policy.tenant != identity.tenant):
        raise PreflightError("identity_or_policy_denied")
    try:
        draft = propose_with_local_ollama(
            runtime, model, user_prompt,
            request_id=request_id, directory=directory,
            requirements=requirements,
            permitted_services=permitted_services,
            permitted_operations=permitted_operations,
        ).draft
        plan = prepare_plan(
            draft, directory, requirements, rules=rules,
            target_resource=target_resource,
            expected_revision=expected_revision,
            expected_connection=expected_connection,
            expected_transport=expected_transport,
            identity=identity, policy=policy,
            approval=approval, now=now,
        )
        # Reserve only after the complete plan has passed. Never dispatch.
        ledger.reserve(plan, now=now)
    except (LocalProposalError, HandoffError, ReplayError) as exc:
        raise PreflightError(exc.code) from exc
    return PreflightPreview(
        plan.service, plan.operation, plan.risk, len(draft.arguments))
