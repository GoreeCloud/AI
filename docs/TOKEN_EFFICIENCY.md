# GoreeCloud AI — opt-in token efficiency and caching

**State:** developer-preview source and synthetic tests; no verified provider
billing savings, production availability or real-user data tests.

## Controls and trust boundaries

| Mechanism | Default | Effect | Location and limits |
| --- | --- | --- | --- |
| Context trimming | Full history | Optional last_n or compact extractive older snippets, and budget auto-fit with declared model_context_window; all preserve system messages in order | Request memory only; no persistent summary; can lose important context |
| Context preview | Manually requested | Reports approximate input-token counts and omitted messages using UTF-8 bytes/4 plus message overhead | No model call or disk write; no message contents returned |
| Output cap | max_output_tokens=2048 | Optional 64–2048 caps OpenRouter max_tokens and (when changed) Ollama options.num_predict | Lower values may truncate useful replies |
| Local exact-response cache | local_response_cache=false | On identical completed chat or provider-terminal SSE requests, may skip inference and replay the model answer without stale usage or generation ID | Plaintext model output in server process RAM up to 300s, 64 LRU entries; no disk, SQLite or cross-worker sharing |
| OpenRouter response cache | provider_response_cache=false | Sends X-OpenRouter-Cache: true and X-OpenRouter-Cache-TTL: 300 to OpenRouter chat/stream | Provider-managed retention; reported HIT/MISS/UNKNOWN metadata; a HIT suppresses replayed provider usage/generation IDs, no independent dollar reconciliation |
| OpenRouter explicit prompt caching | provider_prompt_cache=false | Explicit Anthropic-model-only cache_control ephemeral breakpoint, optional stable cache_session_id | Provider-side repeated prompt prefix; cache writes may cost more, and many short/changed prompts never hit |

The local cache uses a process-random HMAC as its lookup key. Prompt contents,
server keys, and owner token are not persisted as cache keys or logged.
The cache temporarily retains only bounded model response text, provider and
model. A successful OpenRouter-to-Ollama fallback is not cached as a cloud
answer. This mechanism is in-process, not persistent or distributed.

Even for a local RAM cache hit, API owner authentication, cloud-processing
consent and strict OIDC capability checks still apply. Because a cache hit
never contacts a provider, there is no fresh cloud admission or provider
key-budget preflight. An upstream OpenRouter edge-cache request still counts
as an outbound cloud request at the GoreeCloud API boundary. Provider cache
flags require the selected OpenRouter route and explicit cloud consent.
The HTTP API still issues Cache-Control: no-store on private responses.

RAM plaintext can appear in process snapshots, swap or crash dumps; neither
the SQLCipher option nor eviction is secure erasure. Process restart and
current-worker admin-only cache clear do not clear provider caches or other
workers. The web UX resets its per-conversation caching choices when loading
saved history, branching or starting a new chat, but maintains intentional
context/output-length preferences. There is no automatic caching of private
input without owner opt-in to local or provider response caching. Some model
providers perform implicit prompt caching independently of these toggles.

Provider prompt caching may charge more for the first cache write and only
later reads can be cheaper; reported cached input tokens are not a statement
about billed dollars. Provider response cache HIT is reported only when its
header is validated. A displayed estimated context reduction is approximate,
not the actual provider tokenizer or an invoice. No live provider tests or
payment commitments were made.

## Lossy extractive context and declared-window budgeting

The optional compact context mode retains the latest N user/assistant
messages and every system message. It adds a locally computed, capped
extractive digest from older turns marked as untrusted, incomplete user
reference text; no abstractive model, API cost or durable storage is used.
The owner may inspect this digest using the deliberately invoked
POST /api/v1/chat/context-digest-preview route. It can omit important context
and does not produce a faithful comprehensive summary.

Budget mode requires caller-supplied model_context_window (1024–2M estimated
context tokens), reserves max_output_tokens plus a 10% safety margin (minimum
256), then sends as many recent turns as estimated to fit, preserving every
system message and the latest non-system turn. If even that content exceeds
the approximate allowance, inference is refused with 422; the local preview
shows the budget failure. Input counts use a UTF-8-byte heuristic only.
The declared window may be sourced from the model catalog or entered by the
owner; it is not proof of provider tokenizer equivalence or guaranteed fit.
See docs/CONTEXT_COMPACTION.md.

## Approved reviewable local summaries

POST /api/v1/chat/local-summary generates a **model-authored** summary draft
from the older user/assistant turns only, up to 12 KB, using exclusively the
server's configured loopback HTTP Ollama model. Explicit approved=true is
mandatory and strict OIDC capability is inference; the route refuses remote
Ollama even if the operator approved remote inference elsewhere. The result
is returned for owner review/edit, never persisted, auto-inserted into
history, or sent to OpenRouter. The browser can insert the reviewed result
into its unsent prompt and deliberately switch the next request to latest-4
context mode, resetting cloud consent.

The request itself consumes local inference compute/tokens, and model output
can be incorrect or omit important caveats. Optional
reuse_local_summary_cache=true stores only the bounded summary output in
ephemeral process RAM for at most 300 seconds, separate from ordinary chat
and research caches. The approved admin clear route also clears summary
entries in the handling API worker. Source details and threat boundaries
are in docs/LOCAL_SUMMARIES.md.

## Protected API controls

- POST /api/v1/chat/context-preview: strict OIDC read capability, no model.
- POST /api/v1/chat/local-summary: strict OIDC inference capability, explicit
  local-model approval; never a cloud request and never auto-persisted.
- GET /api/v1/cache/status: strict OIDC read capability, counts only, including
  rejected stale cache writes since the most recent clear and a selective-clear
  support flag. The web client reveals selective controls after reading this flag.
- POST /api/v1/cache/clear: strict OIDC admin, explicit approved=true required.
  Optional `selection` is `all` (default), `chat`, `research`, or `summaries`.
  Affects only the selected stores in the current worker, never the OpenRouter
  edge cache. Pending cache misses admitted before a clear cannot repopulate
  that store when their inference completes. A clear does not cancel inference,
  revoke already returned or in-progress replay data, or securely erase RAM.
- POST /api/v1/chat and /api/v1/chat/stream: strict inference/cloud permission
  remains required. Unsupported provider cache combinations fail before
  outbound contact. Local RAM cache is available to completed non-stream and fully terminated SSE
  streaming responses; interrupted/errored/unconfirmed upstream streams are
  never stored. Replayed SSE emits bounded deltas and a cache-hit done event
  without sending new model requests. See docs/STREAM_RESPONSE_CACHE.md.
- Default request behavior is unchanged: full history, 2048 output-token cap,
  no local cache or explicit third-party cache, ordinary cloud consent gate.

## How to evaluate savings safely

1. Preview selected context using synthetic data. Do not interpret estimates
   as actual billed tokens.
2. For repeat identical nonstream requests, explicitly enable RAM caching
   and inspect current-worker hits/misses without logging message content.
3. If policies permit upstream retention, opt into OpenRouter response caching
   or prompt caching for compatible Anthropic models; inspect reported headers
   and cached token counts, including possible cache-write premiums.
4. Reconcile actual provider usage and billing under an approved budget before
   claiming monetary savings. Real provider testing remains outstanding.

Source authority: server/app/token_savings.py, server/app/providers.py,
server/app/main.py, web/src/App.tsx and synthetic test modules
server/tests/test_token_savings.py and server/tests/test_provider_cache_flags.py.

Official reference sources verified November 21, 2026:
- https://openrouter.ai/blog/announcements/response-caching/
- https://openrouter.ai/blog/tutorials/prompt-caching-sticky-routing/
- https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion
- https://github.com/ollama/ollama/blob/main/api/types.go

Use the centralized GoreeCloud/CLI Commands/GoreeCloud/AI.md reference for
development verification commands. This guide is not a second CLI authority.
