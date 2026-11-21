"""Opt-in, single-process RAM cache and context trimming for chat requests.

No disk, network, Redis, database migrations or cross-worker synchronization.
All cache entries contain model output text in server RAM: do NOT enable for
sensitive content unless the owner accepts temporary plaintext memory storage.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from fastapi import HTTPException

MAX_ENTRIES = 64
MAX_RESPONSE_CHARS = 120_000
TTL_SECONDS = 300
_PROCESS_KEY = secrets.token_bytes(32)


def estimate_tokens(messages: list[dict]) -> int:
    """Rough character heuristic, NOT tokenizer output or an invoice."""
    return sum((len(message["content"].encode("utf-8")) + 3) // 4 + 4
               for message in messages)


def select_context(messages: list[dict], mode: str, keep_last: int) -> list[dict]:
    """Preserve system instructions in their original order and latest N turns.

    Only user/assistant history is trimmed. This does not summarize dropped text.
    """
    if mode == "full":
        return messages
    count = 0
    selected: set[int] = set()
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx]["role"] == "system":
            selected.add(idx)
        elif count < keep_last:
            selected.add(idx)
            count += 1
    return [message for idx, message in enumerate(messages) if idx in selected]


def preview(messages: list[dict], mode: str, keep_last: int) -> dict:
    selected = select_context(messages, mode, keep_last)
    original = estimate_tokens(messages)
    used = estimate_tokens(selected)
    return {
        "mode": mode,
        "messages_original": len(messages),
        "messages_sent": len(selected),
        "messages_omitted": len(messages) - len(selected),
        "estimated_input_tokens_original": original,
        "estimated_input_tokens_sent": used,
        "estimated_input_tokens_reduced": max(0, original - used),
        "estimate_method": "utf8-bytes-divided-by-four-plus-message-overhead; not a tokenizer",
        "sent_to_provider": False,
        "saved_to_disk": False,
    }


@dataclass
class Entry:
    expires_at: float
    provider: str
    model: str
    content: str


class ResponseCache:
    """Owner-only short-lived reuse of exact requests, under an ephemeral HMAC key.

    A cache hit never returns the old provider usage or generation ID. An OIDC
    caller must still satisfy the route/inference/cloud checks before lookup.
    """

    def __init__(self):
        self._guard = threading.Lock()
        self._entries: OrderedDict[str, Entry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def key(self, messages: list[dict], selected: str, model: str,
            allow_fallback: bool, max_output_tokens: int, provider_response_cache: bool,
            provider_prompt_cache: bool, session_id: str | None) -> str:
        # Invalidate when operator endpoint/key changes. None of these strings
        # or request contents are stored as cache KEYS or sent to logs.
        origin = (os.getenv("OPENROUTER_API_KEY", "")
                  if selected == "openrouter" else
                  os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
        material = json.dumps({
            "messages": messages, "selected": selected, "model": model,
            "fallback": allow_fallback, "max_output_tokens": max_output_tokens,
            "provider_response_cache": provider_response_cache,
            "provider_prompt_cache": provider_prompt_cache, "session_id": session_id,
            "origin": origin, "ollama_model": os.getenv("OLLAMA_MODEL", ""),
            "owner_auth_mode": os.getenv("GOREECLOUD_AI_AUTH_MODE", "owner"),
            "owner": (os.getenv("GOREECLOUD_AI_TOKEN", "") if
                      os.getenv("GOREECLOUD_AI_AUTH_MODE", "owner") == "owner" else
                      os.getenv("GOREECLOUD_AI_OIDC_OWNER_SUB", "")),
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hmac.new(_PROCESS_KEY, material.encode("utf-8"), hashlib.sha256).hexdigest()

    def _evict_expired(self):
        now = time.monotonic()
        for key in list(self._entries):
            if self._entries[key].expires_at <= now:
                self._entries.pop(key, None)

    def get(self, digest: str) -> Entry | None:
        with self._guard:
            self._evict_expired()
            found = self._entries.get(digest)
            if found is None:
                self._misses += 1
            else:
                self._entries.move_to_end(digest)
                self._hits += 1
            return found

    def put(self, digest: str, answer: dict) -> bool:
        if (not isinstance(answer, dict) or
                not all(isinstance(answer.get(name), str) for name in
                        ("content", "model", "provider")) or
                not 0 < len(answer["content"]) <= MAX_RESPONSE_CHARS):
            return False
        with self._guard:
            self._evict_expired()
            self._entries[digest] = Entry(
                time.monotonic() + TTL_SECONDS,
                answer["provider"], answer["model"], answer["content"],
            )
            self._entries.move_to_end(digest)
            while len(self._entries) > MAX_ENTRIES:
                self._entries.popitem(last=False)
            return True

    def clear(self):
        with self._guard:
            n = len(self._entries)
            self._entries.clear()
            self._hits = 0
            self._misses = 0
            return n

    def status(self):
        with self._guard:
            self._evict_expired()
            return {
                "mode": "opt-in-ephemeral-process-memory",
                "entries": len(self._entries),
                "max_entries": MAX_ENTRIES,
                "ttl_seconds": TTL_SECONDS,
                "hits": self._hits,
                "misses": self._misses,
                "stores_plaintext_model_output_in_ram": True,
                "disk_persistence": False,
                "shared_across_workers": False,
                "cloud_caches_controlled_here": False,
            }


def validate_cache_mode(selected: str, provider_response: bool,
                        provider_prompt: bool, model: str, session_id: str | None):
    if (provider_response or provider_prompt or session_id is not None) and selected != "openrouter":
        raise HTTPException(422, "Provider caching controls require OpenRouter")
    if provider_prompt and not model.startswith("anthropic/"):
        raise HTTPException(
            422, "Explicit prompt cache breakpoints currently require an Anthropic model"
        )
    if session_id is not None and not provider_prompt:
        raise HTTPException(422, "Sticky cache session requires explicit prompt caching")


response_cache = ResponseCache()
# Separate bounded owner-only answer store; no accidental chat/research key overlap.
research_cache = ResponseCache()
