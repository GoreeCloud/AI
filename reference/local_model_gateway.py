"""Bounded, local-only Ollama adapter for GoreeCloud AI Development.

This is an application-side runtime boundary, not an authorization or policy
service. No external provider, tools, prompt logging, or conversation storage.
"""

from __future__ import annotations

import ipaddress
import json
import math
import time
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterator, Sequence

MAX_MESSAGES = 32
MAX_MESSAGE_BYTES = 16 * 1024
MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_MODELS = 200
MAX_STREAM_FRAME_BYTES = 64 * 1024
MAX_STREAM_FRAMES = 4096
MAX_STREAM_WIRE_BYTES = 2 * MAX_RESPONSE_BYTES
MAX_STREAM_SECONDS = 15 * 60  # One finite total-budget guard against trickle streams.
MAX_JSON_SECONDS = 15 * 60  # Also bound trickle responses for discovery and nonstream chat.
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
class ChatStreamEvent:
    provider: str
    model: str
    processing: str
    delta: str
    done: bool


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
        or address not in (ipaddress.IPv4Address("127.0.0.1"), ipaddress.IPv6Address("::1"))
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
        try:
            size = len(item.content.encode("utf-8"))
        except UnicodeEncodeError:
            raise LocalModelError("invalid_messages", "Messages must use valid UTF-8.") from None
        if size > MAX_MESSAGE_BYTES:
            raise LocalModelError("request_too_large", "An individual message is too large.")
        prepared.append({"role": item.role, "content": item.content})
    if prepared[-1]["role"] != "user":
        raise LocalModelError("invalid_messages", "Last message must be from the user.")
    return prepared



def _bounded_json_body(response, deadline: float) -> bytes:
    """Bound total body duration even if the peer dribbles within socket timeout.

    HTTPResponse.read(n) can wait until n bytes arrive or EOF. Using read(1)
    makes the deadline observable inside an unfinished JSON body.
    """
    raw = bytearray()
    while len(raw) <= MAX_RESPONSE_BYTES:
        if time.monotonic() >= deadline:
            raise LocalModelError("runtime_timeout", "Local response exceeded its total duration limit.")
        part = response.read(1)
        if time.monotonic() >= deadline:
            raise LocalModelError("runtime_timeout", "Local response exceeded its total duration limit.")
        if not part:
            return bytes(raw)
        raw.extend(part)
    raise LocalModelError("response_too_large", "Local model response exceeds size limit.")


def _bounded_stream_frame(response, deadline: float) -> bytes:
    """Read one NDJSON frame, checking the total deadline after every byte.

    A single buffered readline() can run without end while its peer trickles
    bytes faster than the per-socket timeout. Bytewise reads prevent that.
    """
    raw = bytearray()
    while len(raw) <= MAX_STREAM_FRAME_BYTES:
        if time.monotonic() >= deadline:
            raise LocalModelError("runtime_timeout", "Local stream exceeded its total duration limit.")
        part = response.read(1)
        if time.monotonic() >= deadline:
            raise LocalModelError("runtime_timeout", "Local stream exceeded its total duration limit.")
        if not part:
            break
        raw.extend(part)
        if part == b"\n":
            break
    return bytes(raw)


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
        deadline = time.monotonic() + MAX_JSON_SECONDS
        try:
            with self._opener.open(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise LocalModelError("runtime_error", "Local model service returned an error.")
                data = _bounded_json_body(response, deadline)
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
        if "error" in parsed:
            raise LocalModelError("runtime_error", "Local model service returned an error.")
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

    def chat(self, model: str, messages: Sequence[ChatMessage], *,
             max_tokens: int | None = None) -> ChatResult:
        """Optionally bound model generation without changing default chat behavior."""
        name = _model_name(model)
        if max_tokens is not None and (type(max_tokens) is not int or not 1 <= max_tokens <= 512):
            raise LocalModelError("invalid_generation_limit", "Output token limit must be 1–512.")
        normalized = _validated_messages(messages)
        payload = {"model": name, "messages": normalized, "stream": False}
        if max_tokens is not None:
            payload["options"] = {"num_predict": max_tokens}
        response = self._json_request("/api/chat", payload)
        if response.get("model", name) != name:
            raise LocalModelError("invalid_response", "Local model identity mismatch.")
        message = response.get("message")
        if (
            response.get("done") is not True
            or not isinstance(message, dict)
            or message.get("role") != "assistant"
            or not isinstance(message.get("content"), str)
            or "tool_calls" in message
            or "images" in message
        ):
            raise LocalModelError("invalid_response", "Local model returned an incomplete response.")
        content = message["content"]
        try:
            size = len(content.encode("utf-8"))
        except UnicodeEncodeError:
            raise LocalModelError("invalid_response", "Local model returned invalid text.") from None
        if size > MAX_RESPONSE_BYTES:
            raise LocalModelError("response_too_large", "Local model response exceeds size limit.")
        return ChatResult(provider="ollama", model=name, processing="local", content=content)

    def iter_chat(self, model: str, messages: Sequence[ChatMessage]) -> Iterator[ChatStreamEvent]:
        """Yield bounded local text deltas and a final completion acknowledgement.

        No token is a completed answer until the caller observes done=True.
        Closing this iterator (e.g. contextlib.closing) closes its HTTP response.
        No automatic retry/fallback may duplicate or externalize a prompt.
        """
        name = _model_name(model)
        normalized = _validated_messages(messages)
        body = json.dumps(
            {"model": name, "messages": normalized, "stream": True},
            ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        if len(body) > MAX_REQUEST_BYTES:
            raise LocalModelError("request_too_large", "Conversation payload is too large.")

        request = urllib.request.Request(
            self.endpoint + "/api/chat",
            data=body,
            method="POST",
            headers={"Accept": "application/x-ndjson", "Content-Type": "application/json"},
        )
        deadline = time.monotonic() + MAX_STREAM_SECONDS
        try:
            try:
                response = self._opener.open(request, timeout=self.timeout_seconds)
            except urllib.error.HTTPError as exc:
                exc.close()
                if 300 <= exc.code < 400:
                    raise LocalModelError("redirect_blocked", "Local runtime redirect refused.") from None
                raise LocalModelError("runtime_error", "Local model service returned an error.") from None

            with response:
                if response.status != 200:
                    raise LocalModelError("runtime_error", "Local model service returned an error.")

                frames = 0
                wire_bytes = 0
                answer_bytes = 0
                while True:
                    raw = _bounded_stream_frame(response, deadline)
                    if not raw:
                        raise LocalModelError("incomplete_stream", "Local response ended without completion.")
                    frames += 1
                    wire_bytes += len(raw)
                    if (len(raw) > MAX_STREAM_FRAME_BYTES
                            or frames > MAX_STREAM_FRAMES
                            or wire_bytes > MAX_STREAM_WIRE_BYTES):
                        raise LocalModelError("response_too_large", "Local stream exceeded its size limit.")

                    try:
                        frame = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError):
                        raise LocalModelError("invalid_response", "Local stream returned invalid JSON.") from None
                    if not isinstance(frame, dict) or frame.get("model") != name:
                        raise LocalModelError("invalid_response", "Local stream model identity is invalid.")
                    if not isinstance(frame.get("done"), bool) or "error" in frame:
                        raise LocalModelError("invalid_response", "Local stream returned an invalid frame.")

                    done = frame["done"]
                    message = frame.get("message")
                    if message is None and not done:
                        raise LocalModelError("invalid_response", "Local stream returned no message.")
                    if message is None:
                        delta = ""
                    elif (not isinstance(message, dict)
                          or message.get("role") != "assistant"
                          or not isinstance(message.get("content"), str)
                          or "tool_calls" in message
                          or "images" in message):
                        raise LocalModelError("invalid_response", "Local stream contained unsupported output.")
                    else:
                        delta = message["content"]

                    try:
                        answer_bytes += len(delta.encode("utf-8"))
                    except UnicodeEncodeError:
                        raise LocalModelError("invalid_response", "Local stream returned invalid text.") from None
                    if answer_bytes > MAX_RESPONSE_BYTES:
                        raise LocalModelError("response_too_large", "Local answer exceeded its size limit.")
                    if delta:
                        yield ChatStreamEvent("ollama", name, "local", delta, False)
                    if done:
                        yield ChatStreamEvent("ollama", name, "local", "", True)
                        return
        except (urllib.error.URLError, TimeoutError, OSError):
            raise LocalModelError("runtime_unavailable", "Local model service is unavailable.") from None
