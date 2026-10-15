"""Development-only, non-executing model proposal handoff."""
from __future__ import annotations
from dataclasses import dataclass
from reference.capability_arguments import canonical_arguments, ArgumentError
from reference.capability_authorization import authorize, AuthorizationError
from reference.model_action_proposal import ActionProposal

class HandoffError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

@dataclass(frozen=True)
class InputRule:
    key: str
    kind: str
    required: bool = True

    def __post_init__(self):
        import re
        if (type(self.key) is not str
                or re.fullmatch(r"[a-z][a-z0-9_.-]{0,95}", self.key) is None
                or type(self.kind) is not str
                or self.kind not in ("string", "integer", "boolean", "string_list")
                or type(self.required) is not bool):
            raise HandoffError("invalid_rules")

def _match(kind, value):
    if kind == "string":
        return type(value) is str and len(value) <= 4096
    if kind == "integer":
        return type(value) is int and abs(value) <= 2**53 - 1
    if kind == "boolean":
        return type(value) is bool
    if kind == "string_list":
        return (type(value) is list and len(value) <= 64
                and all(type(entry) is str and len(entry) <= 4096
                        for entry in value))
    return False

def check_input(proposal, rules):
    if type(proposal) is not ActionProposal or type(rules) is not tuple:
        raise HandoffError("invalid_input")
    if any(type(x) is not InputRule or type(x.key) is not str
           or x.kind not in ("string", "integer", "boolean", "string_list")
           or type(x.required) is not bool for x in rules):
        raise HandoffError("invalid_rules")
    fields = {x.key: x for x in rules}
    if len(fields) != len(rules) or len(rules) > 32:
        raise HandoffError("invalid_rules")
    args = proposal.arguments
    if (type(args) is not dict or any(k not in fields for k in args)
            or any(x.required and x.key not in args for x in rules)
            or any(not _match(fields[k].kind, v) for k, v in args.items())):
        raise HandoffError("invalid_arguments")
    try:
        digest = canonical_arguments(args).sha256
    except ArgumentError as exc:
        raise HandoffError("invalid_arguments") from exc
    if digest != proposal.intent.arguments_sha256:
        raise HandoffError("arguments_changed")
    return args

def prepare_plan(proposal, directory, requirements, *,
                 rules, target_resource, expected_revision,
                 expected_connection, expected_transport,
                 identity, policy, approval=None, now=0):
    """Trusted-input preflight. The returned plan cannot execute anything."""
    from reference.capability_requirements import RequirementError
    from reference.integration_directory import IntegrationError
    from reference.capability_authorization import PolicyEvidence
    import json
    if type(policy) is not PolicyEvidence:
        raise HandoffError("policy_denied")
    if type(proposal) is not ActionProposal or (
            type(target_resource) is not str
            or proposal.intent.resource != target_resource):
        raise HandoffError("target_denied")
    arguments = check_input(proposal, rules)
    try:
        route = directory.resolve(
            proposal.intent.service, proposal.intent.operation,
            permitted_services=policy.permitted_services,
            permitted_operations=policy.permitted_operations)
        requirement = requirements.resolve(
            proposal.intent.service, proposal.intent.operation, route.transport)
    except (IntegrationError, RequirementError, TypeError, AttributeError) as exc:
        raise HandoffError("capability_unavailable") from exc
    if (route.transport != expected_transport
            or route.connection_id != expected_connection
            or requirement.revision != expected_revision
            or proposal.requirement_revision != expected_revision
            or proposal.minimum_risk != requirement.minimum_risk):
        raise HandoffError("capability_changed")
    snapshot = json.loads(canonical_arguments(arguments).encoded)
    try:
        return authorize(directory, requirements, proposal.intent,
                         identity=identity, policy=policy,
                         validated_arguments=snapshot, approval=approval, now=now)
    except AuthorizationError as exc:
        raise HandoffError(exc.code) from exc
