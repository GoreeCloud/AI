# GoreeCloud AI — approved Ollama summary drafts

**State:** Developer-preview implementation, synthetic regression tests only.
No real local model, physical device, provider billing, production encryption
or measured token savings have been verified for this feature.

## Owner-controlled workflow

The owner explicitly approves a new POST /api/v1/chat/local-summary request,
supplying at most 32 chat messages and retain_last_messages (1–16; default 4).
The API refuses requests lacking approved=true. It excludes all system turns
and the latest N user/assistant turns, serializes only the older turns in
bounded JSON (12,000 bytes maximum) and asks the server's configured Ollama
model to create a provisional, compact factual summary.

Only **http://127.0.0.1:PORT** or **http://localhost:PORT** Ollama is accepted;
remote HTTPS Ollama origins are rejected for this feature even when enabled
for regular local-provider chat. The owner must configure OLLAMA_MODEL. The
server never calls OpenRouter through the summarization route. It uses one
separate local model call, capped at 384 predicted tokens and two concurrent
summary generations per API process. Provider client code refuses redirects,
ambient proxy environment variables and oversized upstream responses.

The result is a review-only text draft with source/result metadata and flags
sent_to_cloud=false, saved_to_disk=false and auto_applied=false. The React
browser offers editable review and an explicit "Insert into prompt" action:
it adds the owner's reviewed text to the *unsent* prompt as untrusted reference
material, selects latest-four context mode to reduce next-call input, and
resets cloud-processing consent. The original on-screen history remains
intact. The user must separately send that modified prompt.

## Privacy and security

- User-supplied history may contain malicious instructions. The Ollama
  instruction explicitly treats all excerpts as untrusted data; no tools,
  policy changes or agent execution are enabled. Generated summaries remain
  untrusted and may hallucinate, omit contradictions or discard caveats.
- Summaries are not stored in SQLite, durable memory or browser localStorage.
  An optional reuse_local_summary_cache=true allows exactly keyed reuse in
  plaintext process RAM for 300 seconds, 64 entries maximum. Its keys are
  process-random HMACs, partitioned by owner and local model configuration.
  RAM, swap, crash dumps and replicated processes do not guarantee erasure.
- Strict signed-owner OIDC maps this *inference* action to inference scope;
  default owner token is also required. No provider paid/cloud admission or
  cloud consent is required because this route never contacts a cloud model.
- Cache/status only reveals counters, and cache/clear requires explicit
  approved=true and the strict OIDC admin capability. It clears the handling
  process's chat/research/summary caches, not remote providers or other workers.
- There is no source retention, persistent background summarization, external
  embeddings/semantic search, provider billing reconciliation, or production
  security/privacy policy acceptance.

## Limits and validation

Input is bounded by the chat schema and 12 KB older JSON; a missing local
model, non-loopback host, absent older history, empty or oversized summary
fails before a valid result. Output is bounded to 2,400 characters.
The model's output is fallible; **do not assume** a smaller summary equals
a faithful record or saved monetary tokens without actual token accounting.

The implementation is in server/app/main.py and server/app/token_savings.py,
web/src/App.tsx and synthetic tests
server/tests/test_local_summary.py. Use the existing centralized
GoreeCloud/CLI Commands/GoreeCloud/AI.md for locked build and test commands;
this document does not supersede the command registry.
