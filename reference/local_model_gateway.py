"""Bounded, local-only Ollama adapter for GoreeCloud AI Development.

This is an application-side runtime boundary, not an authorization or policy
service. No external provider, tools, prompt logging, or conversation storage.
"""

from __future__ import annotations

import ipaddress
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Sequence

MAX_MESSAGES = 32
MAX_MESSAGE_BYTES = 16 * 1024
MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_MODELS = 200
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+:@-]{0,159}$")


class LocalModelError(RuntimeError):
    """Sanitized failure suitable for UI and CLI display."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatResult:
    provider: str
    model: str
    processing: str
    content: str


@dataclass(frozen=True)
class LocalModel:
    name: str
    size_bytes: int | None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _endpoint_url(endpoint: str) -> str:
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 200:
        raise LocalModelError("invalid_endpoint", "A local loopback endpoint is required.")
    try:
        parts = urllib.parse.urlsplit(endpoint)
        host = parts.hostname
        port = parts.port
        address = ipaddress.ip_address(host or "")
    except (ValueError, TypeError):
        raise LocalModelError("invalid_endpoint", "Use an HTTP loopback IP address.") from None
    if (
        parts.scheme != "http"
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
        or not address.is_loopback
        or not port
    ):
        raise LocalModelError(
            "invalid_endpoint", "Only http://127.0.0.1:PORT or http://[::1]:PORT is permitted."
        )
    return f"http://[{address.compressed}]:{port}" if address.version == 6 else f"http://{address.compressed}:{port}"


def _model_name(name: str) -> str:
    if not isinstance(name, str) or not _MODEL_NAME.fullmatch(name):
        raise LocalModelError("invalid_model", "Invalid local model identifier.")
    return name


def _validated_messages(messages: Sequence[ChatMessage]) -> list[dict[str, str]]:
    if isinstance(messages, (str, bytes)) or not isinstance(messages, (list, tuple)):
        raise LocalModelError("invalid_messages", "Messages must be an ordered sequence.")
    if not 1 <= len(messages) <= MAX_MESSAGES:
        raise LocalModelError("invalid_messages", "Conversation message limit exceeded.")
    prepared: list[dict[str, str]] = []
    for i, item in enumerate(messages):
        if not isinstance(item, ChatMessage) or item.role not in ("system", "user", "assistant"):
            raise LocalModelError("invalid_messages", "Unsupported message role or shape.")
        if item.role == "system" and i != 0:
            raise LocalModelError("invalid_messages", "System instructions must be first.")
        if not isinstance(item.content, str) or not item.content.strip() or "\x00" in item.content:
            raise LocalModelError("invalid_messages", "Message text must be nonempty plain text.")
        if len(item.content.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise LocalModelError("request_too_large", "An individual message is too large.")
        prepared.append({"role": item.role, "content": item.content})
    if prepared[-1]["role"] != "user":
        raise LocalModelError("invalid_messages", "Last message must be from the user.")
    return prepared


class LocalOllamaGateway:
    """Explicitly loopback-only provider adapter with no redirect or proxy use."""

    def __init__(self, endpoint: str = "http://127.0.0.1:11434", timeout_seconds: float = 30.0):
        self.endpoint = _endpoint_url(endpoint)
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 1 <= timeout_seconds <= 120
        ):
            raise LocalModelError("invalid_timeout", "Timeout must be 1–120 seconds.")
        self.timeout_seconds = float(timeout_seconds)
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), urllib.request.HTTPHandler(), _NoRedirect()
        )

    def _json_request(self, path: str, payload: dict | None = None) -> dict:
        # Paths are constants owned by this adapter; no input becomes a URL path.
        body = None if payload is None else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        if body is not None and len(body) > MAX_REQUEST_BYTES:
            raise LocalModelError("request_too_large", "Conversation payload is too large.")
        req = urllib.request.Request(
            self.endpoint + path,
            data=body,
            method="GET" if body is None else "POST",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with self._opener.open(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise LocalModelError("runtime_error", "Local model service returned an error.")
                data = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            exc.close()  # HTTPError carries a response stream; avoid leaking failed requests.
            if 300 <= exc.code < 400:
                raise LocalModelError("redirect_blocked", "Local runtime redirect refused.") from None
            raise LocalModelError("runtime_error", "Local model service returned an error.") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise LocalModelError("runtime_unavailable", "Local model service is unavailable.") from None
        if len(data) > MAX_RESPONSE_BYTES:
            raise LocalModelError("response_too_large", "Local model response exceeds size limit.")
        try:
            parsed = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            raise LocalModelError("invalid_response", "Local model service returned invalid JSON.") from None
        if not isinstance(parsed, dict):
            raise LocalModelError("invalid_response", "Local model service returned an invalid result.")
        return parsed

    def list_models(self) -> tuple[LocalModel, ...]:
        response = self._json_request("/api/tags")
        models = response.get("models")
        if not isinstance(models, list) or len(models) > MAX_MODELS:
            raise LocalModelError("invalid_response", "Local model catalog is invalid.")
        found: dict[str, LocalModel] = {}
        for item in models:
            if not isinstance(item, dict):
                raise LocalModelError("invalid_response", "Local model catalog is invalid.")
            try:
                name = _model_name(item.get("name"))
            except LocalModelError:
                raise LocalModelError("invalid_response", "Local model catalog is invalid.") from None
            size = item.get("size")
            if size is not None and (isinstance(size, bool) or not isinstance(size, int) or size < 0):
                raise LocalModelError("invalid_response", "Local model catalog is invalid.")
            if name in found:
                raise LocalModelError("invalid_response", "Duplicate model identifiers found.")
            found[name] = LocalModel(name=name, size_bytes=size)
        return tuple(found[k] for k in sorted(found))

    def chat(self, model: str, messages: Sequence[ChatMessage]) -> ChatResult:
        name = _model_name(model)
        normalized = _validated_messages(messages)
        response = self._json_request(
            "/api/chat",
            {"model": name, "messages": normalized, "stream": False},
        )
        message = response.get("message")
        if (
            response.get("done") is not True
            or not isinstance(message, dict)
            or message.get("role") != "assistant"
            or not isinstance(message.get("content"), str)
        ):
            raise LocalModelError("invalid_response", "Local model returned an incomplete response.")
        content = message["content"]
        if len(content.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise LocalModelError("response_too_large", "Local model response exceeds size limit.")
        return ChatResult(provider="ollama", model=name, processing="local", content=content)
