"""OpenUI Development adapter for GoreeCloud AI's existing local Ollama gateway.

This is an internal Python function, not an HTTP server or public inference API.
Requires the separately reviewed reference.local_model_gateway from PR #45.
It NEVER validates OpenUI Lang: the OpenUI TS parser must validate before render.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_PROMPT_CHARS = 12000
MAX_OPENUI_BYTES = 48000


class OpenUIBridgeError(RuntimeError):
    """Safe, non-secret operational error code for the calling application."""


@dataclass(frozen=True)
class OpenUICandidate:
    provider: str
    model: str
    processing: str
    response: str
    validation: str = "not_validated"


def generate_local_openui(*, model: str, user_prompt: str, trusted_system_prompt: str) -> OpenUICandidate:
    """Return raw candidate UI text using the existing, loopback-only model gateway.

    trusted_system_prompt must come from glazeOpenUILibrary.prompt(), never user
    input. This API is not suitable for direct exposure over an unauthenticated
    network route; authentication/capabilities belong to GoreeCloud AI.
    """
    for label, value in (("model", model), ("user_prompt", user_prompt),
                         ("trusted_system_prompt", trusted_system_prompt)):
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise OpenUIBridgeError(f"invalid_{label}")
    if len(user_prompt) > MAX_PROMPT_CHARS or len(trusted_system_prompt) > MAX_PROMPT_CHARS:
        raise OpenUIBridgeError("prompt_too_large")
    if not trusted_system_prompt.startswith("You are an AI assistant that responds using openui-lang"):
        raise OpenUIBridgeError("invalid_trusted_prompt")
    try:
        # Reuse the separate reviewed implementation; never implement another
        # HTTP provider, remote fallback, or credential handler here.
        from reference.local_model_gateway import ChatMessage, LocalOllamaGateway
    except ImportError as exc:
        raise OpenUIBridgeError("local_gateway_not_available") from exc

    result = LocalOllamaGateway().chat(model, [
        ChatMessage(role="system", content=trusted_system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ])
    if (result.provider != "ollama" or result.processing != "local" or result.model != model
            or not isinstance(result.content, str) or not result.content.strip()
            or "\x00" in result.content or len(result.content.encode("utf-8")) > MAX_OPENUI_BYTES):
        raise OpenUIBridgeError("untrusted_provider_response")
    return OpenUICandidate("ollama", model, "local", result.content)
