# GoreeCloud AI — exact completed SSE answer replay

**Status:** developer-preview source and mocked provider tests. No real
provider, production deployment, multiworker coherence or measured costs.

## Default and opt-in behavior

The existing POST /api/v1/chat/stream response remains a no-store SSE
stream. By default it never creates a local cache entry. A request with
local_response_cache=true explicitly allows exact answers in RAM.

On a cache hit, the API authenticates the owner and checks selected provider,
cloud consent, optional strict OIDC cloud capability and request validity.
It returns bounded SSE delta chunks followed by a fresh done event with
cache.hit=true and provider_contacted=false. No provider call or fresh
paid-key preflight/admission occurs, and **no old provider usage or
generation_id is replayed**.

On a miss, the API retains a bounded in-memory accumulator of deltas only
until it has witnessed the provider's real terminal marker:
OpenRouter data: [DONE] or Ollama done:true. It stores a result only
if the terminal marker was received, at least one nonempty delta exists,
content is within 120,000 characters, the reported provider matches the
selected provider and the bounded cache accepts a valid text/model record.
Malformed provider data and premature EOF end the stream with a generic SSE
error for both default and cache-enabled requests. Providers may bill for
tokens produced before a cancel.

The server only exposes upstream_terminal metadata when the caller opts
into local response caching; ordinary SSE clients and existing provider
response shapes remain backward-compatible. The RAM HMAC key includes
messages (after selected context reduction), provider, model, fallback
policy, max-output cap and provider cache/session options, preventing
cross-configuration reuse.

The response cache remains a 64-entry process-local LRU, TTL 300 seconds,
plaintext model output in RAM, no SQLite/disk storage, no cross-worker
cache coherence or secure erasure. Cache clear requires approved=true and
strict admin capability and applies only to the handling worker. The
separate OpenRouter edge response cache is not controlled by local clear.

## Native and browser settings

React, Android Compose and Linux Qt now permit the existing opt-in RAM
response cache checkbox when streaming is selected. The client still
controls cloud consent separately. On a local SSE hit, the browser notice
identifies that no provider was contacted. Native clients render normal
SSE frames with limited cache-hit status details. The browser closes the request
on the first terminal event and offers Stop while a stream is active.
Android and Linux Qt remove an empty assistant turn when streaming ends and
preserve any text already received. The next request can continue the chat
after a cancellation or a completion with no text.
On Linux Qt, a provider error preserves preceding streamed text, including
when both events arrive in the same network read. The client displays a
fixed error message to keep upstream details private.

## Remaining verification

- Test real Ollama/OpenRouter streams with pre-approved synthetic prompts;
  no real-provider call or money was spent for these tests.
- Test mid-stream cancellation on real native/browser clients, backpressure,
  multiworker cache invalidation, process memory exposure and restart.
- Use provider-owned usage/billing to verify actual savings. No inference
  price or token bill guarantee is made from a local cache counter.

Source: server/app/main.py, server/app/providers.py,
web/src/App.tsx, linux/Main.qml and Android MainActivity.kt.
Synthetic tests: server/tests/test_stream_response_cache.py.
All CLI commands for this repo remain in the canonical
GoreeCloud/CLI Commands/GoreeCloud/AI.md Drive registry.
