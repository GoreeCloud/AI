"""Bounded, in-memory, fail-closed multi-turn chat for the local-only Ollama adapter.

No persistence, remote-provider fallback, tool calls or shell access.
A turn is committed only after a full successful assistant response.
"""

from __future__ import annotations

import json
from contextlib import closing
from typing import Iterator

from reference.local_model_gateway import (
    ChatMessage,
    ChatResult,
    ChatStreamEvent,
    LocalModelError,
    LocalOllamaGateway,
    MAX_MESSAGE_BYTES,
    MAX_MESSAGES,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    _validated_messages,
)


class LocalChatSession:
    """A single-process, sequential session. Do not share concurrently across clients."""

    def __init__(self, runtime: LocalOllamaGateway, model: str):
        self.runtime = runtime
        self.model = model
        self._turns: list[tuple[ChatMessage, ChatMessage]] = []
        self.last_reply_retained = True

    @property
    def turns(self) -> tuple[tuple[ChatMessage, ChatMessage], ...]:
        return tuple(self._turns)

    def reset(self) -> None:
        """Clear references to completed conversation turns; no disk is written."""
        self._turns.clear()
        self.last_reply_retained = True

    def _prepare(self, prompt: str, *, stream: bool) -> tuple[list[tuple[ChatMessage, ChatMessage]], list[ChatMessage]]:
        candidate = ChatMessage("user", prompt)
        _validated_messages([candidate])
        kept = list(self._turns)
        while True:
            messages = [part for turn in kept for part in turn] + [candidate]
            if len(messages) <= MAX_MESSAGES:
                _validated_messages(messages)
                payload = {
                    "model": self.model,
                    "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
                    "stream": stream,
                }
                try:
                    size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                except UnicodeEncodeError:
                    raise LocalModelError("invalid_messages", "Messages must use valid UTF-8.") from None
                if size <= MAX_REQUEST_BYTES:
                    return kept, messages
            if not kept:
                raise LocalModelError("request_too_large", "Conversation payload exceeds its size limit.")
            kept.pop(0)  # Always evict an entire old user/assistant pair.

    def _commit(self, kept: list[tuple[ChatMessage, ChatMessage]], prompt: str, answer: str) -> None:
        try:
            encoded = answer.encode("utf-8")
        except UnicodeEncodeError:
            self.reset()
            raise LocalModelError("invalid_response", "Local model returned invalid text.") from None
        if not answer or "\x00" in answer or len(encoded) > MAX_MESSAGE_BYTES:
            # Never retain orphaned old turns after failing to retain the newest turn.
            self.reset()
            self.last_reply_retained = False
            return
        self._turns = kept + [(ChatMessage("user", prompt), ChatMessage("assistant", answer))]
        self.last_reply_retained = True

    def reply(self, prompt: str) -> ChatResult:
        kept, messages = self._prepare(prompt, stream=False)
        result = self.runtime.chat(self.model, messages)
        if (not isinstance(result, ChatResult) or result.model != self.model
                or result.provider != "ollama" or result.processing != "local"):
            raise LocalModelError("invalid_response", "Unexpected local model response identity.")
        self._commit(kept, prompt, result.content)
        return result

    def iter_reply(self, prompt: str) -> Iterator[ChatStreamEvent]:
        """Stream text deltas; commit history only after receiving an explicit done event.

        Consumers must close the iterator when cancelled, e.g. with contextlib.closing.
        """
        kept, messages = self._prepare(prompt, stream=True)
        chunks: list[str] = []
        total_bytes = 0
        with closing(self.runtime.iter_chat(self.model, messages)) as events:
            for event in events:
                if (not isinstance(event, ChatStreamEvent) or event.provider != "ollama"
                        or event.processing != "local" or event.model != self.model
                        or not isinstance(event.delta, str) or not isinstance(event.done, bool)):
                    raise LocalModelError("invalid_response", "Unexpected local stream identity.")
                if event.done:
                    if event.delta:
                        raise LocalModelError("invalid_response", "Completion must not carry text.")
                    self._commit(kept, prompt, "".join(chunks))
                    yield event
                    return
                try:
                    size = len(event.delta.encode("utf-8"))
                except UnicodeEncodeError:
                    raise LocalModelError("invalid_response", "Local stream returned invalid text.") from None
                total_bytes += size
                if total_bytes > MAX_RESPONSE_BYTES:
                    raise LocalModelError("response_too_large", "Local answer exceeded its size limit.")
                chunks.append(event.delta)
                yield event
        raise LocalModelError("incomplete_stream", "Local response ended without completion.")
