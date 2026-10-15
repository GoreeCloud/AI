"""Opt-in local Ollama proposal drafting, with no connector/tool execution.

Only locally installed Ollama can produce the text. The model is not permitted
to bind connectors, approve actions, create permissions or dispatch any tool.
"""
from __future__ import annotations

from dataclasses import dataclass
from reference.capability_discovery import DiscoveryError, discover
from reference.capability_requirements import RequirementCatalog
from reference.integration_directory import IntegrationDirectory
from reference.local_model_gateway import (
    ChatMessage, ChatResult, LocalModelError, LocalOllamaGateway, _validated_messages,
)
from reference.model_action_proposal import ActionProposal, ProposalError, parse_model_proposal

_MAX_EXPOSED_CAPABILITIES = 48

_INSTRUCTION = (
    "You are a proposal formatter, NOT a tool executor. "
    "Return exactly one JSON object, without markdown, code fences, commentary or tool calls. "
    'Use this exact schema: {"schema":"goreecloud.ai.action-proposal.v1",'
    '"service":"ID","operation":"ID","resource":"target",'
    '"arguments":{}}. '
    "Only propose a listed service and operation. Arguments and resource must reflect "
    "the user's request; do not invent credentials or assert that any action is approved. "
    "The backend independently checks every proposal. "
    "Available service:operation (minimum risk) entries: "
)


class LocalProposalError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class LocalProposal:
    model: str
    draft: ActionProposal

    def redacted_preview(self) -> dict[str, object]:
        return {"provider": "ollama", "processing": "local",
                **self.draft.redacted_preview()}


def propose_with_local_ollama(
    runtime: LocalOllamaGateway,
    model: str,
    user_prompt: str,
    *,
    request_id: str,
    directory: IntegrationDirectory,
    requirements: RequirementCatalog,
    permitted_services: frozenset[str],
    permitted_operations: frozenset[str],
) -> LocalProposal:
    """One bounded local inference, followed by strictly scoped parsing only.

    Caller-supplied grants must originate from a trusted backend. No prompts
    or model replies are persisted by this function. This function does not
    call the actual authorization gate or a connector.
    """
    if not isinstance(runtime, LocalOllamaGateway):
        raise LocalProposalError("invalid_runtime")
    if type(model) is not str or not model:
        raise LocalProposalError("invalid_model")
    if type(user_prompt) is not str:
        raise LocalProposalError("invalid_prompt")
    try:
        candidate = ChatMessage("user", user_prompt)
        _validated_messages([candidate])
        page = discover(
            directory, requirements,
            permitted_services=permitted_services,
            permitted_operations=permitted_operations,
            page_size=_MAX_EXPOSED_CAPABILITIES,
        )
    except (LocalModelError, DiscoveryError) as exc:
        raise LocalProposalError("invalid_request") from exc
    if not page.capabilities:
        raise LocalProposalError("no_capabilities")
    choices = ", ".join(
        f"{item.service}:{item.operation} ({item.minimum_risk})"
        for item in page.capabilities
    )
    messages = [
        ChatMessage("system", _INSTRUCTION + choices),
        candidate,
    ]
    try:
        result = runtime.chat(model, messages, max_tokens=512)
    except LocalModelError as exc:
        # Do not print raw model requests or contents.
        raise LocalProposalError("model_unavailable") from exc
    if (type(result) is not ChatResult or result.provider != "ollama"
            or result.processing != "local" or result.model != model):
        raise LocalProposalError("invalid_model_response")
    try:
        draft = parse_model_proposal(
            result.content, request_id=request_id, directory=directory,
            requirements=requirements,
            permitted_services=permitted_services,
            permitted_operations=permitted_operations,
        )
    except ProposalError as exc:
        raise LocalProposalError(exc.code) from exc
    # The displayed capability list is a bounded prompt, never the source of
    # authority. Refuse a capability not explicitly listed to the model.
    if not any(item.service == draft.intent.service
               and item.operation == draft.intent.operation
               for item in page.capabilities):
        raise LocalProposalError("not_in_exposed_scope")
    return LocalProposal(model, draft)
