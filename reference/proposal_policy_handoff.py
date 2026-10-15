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

def _match(kind, value):
    if kind == "string":
        return type(value) is str and len(value) <= 4096
    if kind == "integer":
        return type(value) is int and abs(value) <= 2**53 - 1
    if kind == "boolean":
        return type(value) is bool
    return False

def check_input(proposal, rules):
    if type(proposal) is not ActionProposal or type(rules) is not tuple:
        raise HandoffError("invalid_input")
    if any(type(x) is not InputRule or type(x.key) is not str
           or x.kind not in ("string", "integer", "boolean")
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
