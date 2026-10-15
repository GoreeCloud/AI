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
    _model_name,
)


class LocalChatSession:
    """A single-process, sequential session. Do not share concurrently across clients."""

    def __init__(self, runtime: LocalOllamaGateway, model: str):
        self.runtime = runtime
        self.model = model
        self._turns: list[tuple[ChatMessage, ChatMessage]] = []
        self.last_reply_retained = True
        self.turn_limit: int | None = None
        self._system_instruction: ChatMessage | None = None

    @property
    def turns(self) -> tuple[tuple[ChatMessage, ChatMessage], ...]:
        return tuple(self._turns)

    @property
    def has_system_instruction(self) -> bool:
        return self._system_instruction is not None

    def clear_turns(self) -> int:
        """Forget all completed turns while preserving ephemeral session settings.

        No network requests or disk writes. The system instruction and
        configured turn cap remain active for the next prompt.
        """
        removed = len(self._turns)
        self._turns.clear()
        self.last_reply_retained = self.turn_limit != 0
        return removed

    def undo_last_turn(self) -> bool:
        """Discard the last completed pair without requesting model inference."""
        if not self._turns:
            return False
        self._turns.pop()
        self.last_reply_retained = True
        return True

    def delete_turn(self, index: int) -> bool:
        """Delete one completed local turn without inference or disk writes.

        Indices are zero-based. Negative or boolean values never delete the
        most recent private turn by accident.
        """
        if type(index) is not int or index < 0 or index >= len(self._turns):
            return False
        del self._turns[index]
        self.last_reply_retained = True
        return True


    def rewind_to(self, count: int) -> int:
        """Keep the first count completed pairs, discarding all later turns."""
        if type(count) is not int or not 0 <= count <= len(self._turns):
            raise LocalModelError("invalid_turn_index", "Choose a completed turn count.")
        removed = len(self._turns) - count
        if removed:
            del self._turns[count:]
        self.last_reply_retained = self.turn_limit != 0
        return removed

    def forget_oldest(self, count: int) -> int:
        """Discard count oldest pairs without inference or persistent copies."""
        if type(count) is not int or not 0 <= count <= len(self._turns):
            raise LocalModelError("invalid_turn_index", "Choose a completed turn count.")
        if count:
            del self._turns[:count]
        self.last_reply_retained = self.turn_limit != 0
        return count

    def set_turn_limit(self, limit: int) -> None:
        """Limit retained completed turns, 0-50; remove older context now.

        This setting is session-local, never written to disk. System
        instructions are separate and remain unchanged.
        """
        if type(limit) is not int or not 0 <= limit <= 50:
            raise LocalModelError("invalid_turn_limit", "Choose a limit from 0 through 50.")
        self.turn_limit = limit
        if limit == 0:
            self._turns.clear()
            self.last_reply_retained = False
        elif len(self._turns) > limit:
            self._turns = self._turns[-limit:]

    def restore_automatic_retention(self) -> None:
        """Restore automatic retention without recovering previously discarded turns."""
        self.turn_limit = None
        self.last_reply_retained = True

    def switch_model(self, name: str) -> bool:
        """Only select installed local models; isolate conversation context by model."""
        name = _model_name(name)
        if name == self.model:
            return False
        available = self.runtime.list_models()
        if name not in (model.name for model in available):
            raise LocalModelError("model_not_installed", "The requested local model is not installed.")
        self.reset()
        self.model = name
        return True

    def set_system_instruction(self, text: str | None) -> None:
        """Set an in-memory first-message instruction, discarding old conversation."""
        if text is None:
            self.reset()
            return
        instruction = ChatMessage("system", text)
        _validated_messages([instruction, ChatMessage("user", "validation")])
        self.reset()
        self._system_instruction = instruction

    def reset(self) -> None:
        """Clear turns and system instruction references; never write them to disk."""
        self._turns.clear()
        self._system_instruction = None
        self.last_reply_retained = True

    def _prepare(self, prompt: str, *, stream: bool, prior_turns: list[tuple[ChatMessage, ChatMessage]] | None = None) -> tuple[list[tuple[ChatMessage, ChatMessage]], list[ChatMessage]]:
        candidate = ChatMessage("user", prompt)
        _validated_messages([candidate])
        kept = list(self._turns if prior_turns is None else prior_turns)
        while True:
            messages = ([self._system_instruction] if self._system_instruction is not None else []) + [part for turn in kept for part in turn] + [candidate]
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
            self.last_reply_retained = False
            raise LocalModelError("invalid_response", "Local model returned invalid text.") from None
        if not answer or "\x00" in answer or len(encoded) > MAX_MESSAGE_BYTES:
            # Never retain orphaned old turns after failing to retain the newest turn.
            self.reset()
            self.last_reply_retained = False
            return
        self._turns = kept + [(ChatMessage("user", prompt), ChatMessage("assistant", answer))]
        if self.turn_limit is not None:
            self._turns = self._turns[-self.turn_limit:] if self.turn_limit else []
        self.last_reply_retained = bool(self._turns)

    def reply(self, prompt: str) -> ChatResult:
        kept, messages = self._prepare(prompt, stream=False)
        result = self.runtime.chat(self.model, messages)
        if (not isinstance(result, ChatResult) or result.model != self.model
                or result.provider != "ollama" or result.processing != "local"):
            raise LocalModelError("invalid_response", "Unexpected local model response identity.")
        self._commit(kept, prompt, result.content)
        return result


    def _replacement_is_retained(self, answer: str) -> None:
        """Fail before altering the previous completed answer."""
        if not isinstance(answer, str) or not answer or "\x00" in answer:
            raise LocalModelError("invalid_response", "Replacement answer cannot be retained.")
        try:
            size = len(answer.encode("utf-8"))
        except UnicodeEncodeError:
            raise LocalModelError("invalid_response", "Replacement answer contains invalid text.") from None
        if size > MAX_MESSAGE_BYTES:
            raise LocalModelError("response_too_large", "Replacement answer cannot be retained.")

    def reply_once(self, prompt: str) -> ChatResult:
        """Perform one local inference without sharing or retaining prior turns."""
        _, messages = self._prepare(prompt, stream=False, prior_turns=[])
        result = self.runtime.chat(self.model, messages)
        if (not isinstance(result, ChatResult) or result.model != self.model
                or result.provider != "ollama" or result.processing != "local"):
            raise LocalModelError("invalid_response", "Unexpected local model response identity.")
        if not isinstance(result.content, str):
            raise LocalModelError("invalid_response", "Local model returned invalid text.")
        try:
            answer_bytes = len(result.content.encode("utf-8"))
        except UnicodeEncodeError:
            raise LocalModelError("invalid_response", "Local model returned invalid text.") from None
        if answer_bytes > MAX_RESPONSE_BYTES:
            raise LocalModelError("response_too_large", "Local answer exceeded its size limit.")
        return result

    def iter_reply_once(self, prompt: str) -> Iterator[ChatStreamEvent]:
        """Stream a one-time reply without reading or saving conversation turns."""
        yield from self._stream_answer(prompt, regenerate=False, ephemeral=True)

    def regenerate_last(self) -> ChatResult:
        """Explicitly retry last user prompt, atomically replacing its saved reply."""
        if not self._turns:
            raise LocalModelError("no_turns", "No completed answer to regenerate.")
        prompt = self._turns[-1][0].content
        kept, messages = self._prepare(prompt, stream=False, prior_turns=self._turns[:-1])
        result = self.runtime.chat(self.model, messages)
        if (not isinstance(result, ChatResult) or result.model != self.model
                or result.provider != "ollama" or result.processing != "local"):
            raise LocalModelError("invalid_response", "Unexpected local model response identity.")
        self._replacement_is_retained(result.content)
        self._commit(kept, prompt, result.content)
        return result

    def edit_last(self, prompt: str) -> ChatResult:
        if not self._turns:
            raise LocalModelError("no_turns", "No completed turn to edit.")
        kept, messages = self._prepare(prompt, stream=False, prior_turns=self._turns[:-1])
        result = self.runtime.chat(self.model, messages)
        if not isinstance(result, ChatResult) or (result.provider, result.model, result.processing) != ("ollama", self.model, "local"):
            raise LocalModelError("invalid_response", "Unexpected local model response identity.")
        self._replacement_is_retained(result.content)
        self._commit(kept, prompt, result.content)
        return result

    def iter_edit_last(self, prompt: str) -> Iterator[ChatStreamEvent]:
        if not self._turns:
            raise LocalModelError("no_turns", "No completed turn to edit.")
        yield from self._stream_answer(prompt, regenerate=True)

    def iter_reply(self, prompt: str) -> Iterator[ChatStreamEvent]:
        """Stream an answer, committing only after an explicit completion."""
        yield from self._stream_answer(prompt, regenerate=False)

    def iter_regenerate_last(self) -> Iterator[ChatStreamEvent]:
        """Explicitly retry latest turn; cancellation preserves the old answer."""
        if not self._turns:
            raise LocalModelError("no_turns", "No completed answer to regenerate.")
        yield from self._stream_answer(self._turns[-1][0].content, regenerate=True)

    def _stream_answer(self, prompt: str, *, regenerate: bool, ephemeral: bool = False) -> Iterator[ChatStreamEvent]:
        kept, messages = self._prepare(
            prompt, stream=True, prior_turns=[] if ephemeral else self._turns[:-1] if regenerate else None
        )
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
                    answer = "".join(chunks)
                    if regenerate:
                        self._replacement_is_retained(answer)
                    if not ephemeral:
                        self._commit(kept, prompt, answer)
                    yield event
                    return
                try:
                    size = len(event.delta.encode("utf-8"))
                except UnicodeEncodeError:
                    raise LocalModelError("invalid_response", "Local stream returned invalid text.") from None
                total_bytes += size
                if total_bytes > MAX_RESPONSE_BYTES:
                    raise LocalModelError("response_too_large", "Local answer exceeded its size limit.")
                if not ephemeral:
                    chunks.append(event.delta)
                yield event
        raise LocalModelError("incomplete_stream", "Local response ended without completion.")
