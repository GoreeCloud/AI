# GoreeCloud AI — local extractive context and model-window planning

**Status:** Developer-preview source with synthetic tests; no provider context
window or billed input-token acceptance. All modes are explicit opt-ins.

Full context remains the default. Last-N mode preserves system instructions
and the latest N user/assistant turns. Compact mode keeps the same necessary
messages but inserts a bounded extractive digest of older turns as an
untrusted *user reference message*. It quotes selected sentences/paragraphs
chosen by local lexical relevance to the current user request and recency.

**This is a lossy digest, not abstractive summarization or an authoritative
memory.** It may omit key caveats, chronology and instructions. Users should
select compact mode deliberately and inspect its output via
POST /api/v1/chat/context-digest-preview before sending important requests.
No provider sees the preview request; no disk, database, analytics or
external network call is made by local extraction. The selected context is
transmitted to a provider **only** if the separately consent-gated chat API
is called, following existing provider routing.

Budget mode accepts a *caller-declared* model_context_window of 1,024 to
2,000,000 tokens. It reserves max_output_tokens (64–2048) and a margin of
max(256, ceil(window/10)) and greedily retains recent consecutive turns that
fit a rough UTF-8-byte tokenizer heuristic. System instructions and the most
recent non-system message are never silently dropped. If they cannot fit,
both chat and streaming requests refuse paid inference with 422; owner-only
preview still reports the budget deficit.

Only signed owner scoped clients can invoke the read-only previews; strict
OIDC maps context-digest-preview to the read capability. Prompt data are
not logged or persisted by these controls. The web UI can choose compact
or budget mode, inspect the digest, and view estimated input reductions.
When a model is selected from the metadata catalog, its advertised context
length can prepopulate the **declared** window. This provider metadata
is not guaranteed, and no automated proof of billable token savings exists.

### Risks and further work

- Lexical extraction is not semantic reasoning or a long-term memory store.
  The quote selection may be irrelevant or miss safety/requirements context.
- Budget heuristics cannot guarantee token equivalence; verify token counts
  with supported provider model-native tokenizers and provider response usage.
- No automatic session-level persistent summaries, semantic embeddings, or
  cross-device retained memory have been introduced. The existing explicit
  saved-conversation option remains the durable data authority.
- Provider caching and temporary RAM responses still require opt-in and
  obey separate GoreeShield cloud-consent gates.

Source and synthetic tests: server/app/context_compaction.py,
server/app/token_savings.py, server/app/main.py, web/src/App.tsx and
server/tests/test_context_compaction.py.

Use the existing centralized GoreeCloud/CLI Commands/GoreeCloud/AI.md
for development verification, not a competing CLI master.
