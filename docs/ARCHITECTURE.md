# GoreeCloud AI — architecture and security boundary

**Single-owner developer preview.** This is source and tests, not a certified
production deployment.

## Components and data

- React web, Qt Quick 6.12 Linux and Kotlin Compose Android use an authenticated
  versioned FastAPI API, with server-only OpenRouter keys and local Ollama.
- Chat history stays in client memory unless saved as an explicit local snapshot.
- Documents and conversation snapshots remain plaintext SQLite by default.
  Optional SQLCipher encrypts the entire live database, including FTS5
  indexed title/body, when explicitly installed/configured with an external
  key and either newly initialized or offline-migrated into a new path.
  Local FTS5 search remains available; no embeddings or external
  service is used for search. No existing database is auto-converted.
- Retrieval question-answering selects bounded local excerpts and source IDs.
  Sources are untrusted reference material, not executable instructions.
  Excerpts are sent to OpenRouter only when expressly consented, else Ollama.
- MCP tools require server-configured HTTPS/loopback endpoint, name allowlist,
  authenticated owner request and explicit per-call approval. Model-produced
  text never automatically invokes MCP. The MCP boundary checks the allowlist
  before opening a connection, rejects argument depth >16, JSON payloads over
  256 KB and non-finite values, and admits at most two sessions per API worker.
  Session initialization/discovery are individually bounded at 10 seconds,
  tool calls at 30 seconds, and admission at 0.5 seconds. Results expose at
  most 10 text blocks of 12k characters each with explicit truncation/media
  omission flags; discovery lists at most 100 tool names. Output is untrusted
  data, never implicit authorization for another action.

## Implemented controls

- Cloud-processing consent defaults false for chat, streaming, research
  and agent plans. Auto uses OpenRouter only with consent and configured key,
  otherwise local Ollama or fail closed. Paid image requests require their
  own approval and also transmit data to a cloud provider.
- SQLite-atomic daily external-provider request admissions default to 20
  (GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT). This is **not** a currency cap:
  provider pricing, token bills and charge reconciliation are independent.
  Failed requests may still consume an admission slot.
- Each accepted cloud admission also creates a locally stored metadata-only
  receipt in the same SQLite transaction, but only after an explicit positive
  approval argument. Kinds include chat, chat-stream, image, agent-plan and
  research. No prompt, model response, provider key, caller IP, account ID or
  text is saved. Receipts are retained for 30 days by default, configurable
  between 1 and 365, pruned on later admissions or owner review, and may be
  explicitly cleared without refunding request quota. An admission is **not**
  proof that transfer, provider completion or billing occurred; default
  SQLite live rows remain plaintext, while opt-in SQLCipher encrypts database
  pages and indexes. Neither mode proves secure erasure of freed pages, OS
  copies or provider data.
- Owner shared-token check, no prompt logging, bounded streamed JSON responses,
  validated base64 image formats, fixed upstream OpenRouter URL,
  disabled redirects, bounded requests, reference validation and PDF/DOCX
  file limits. PDF/DOCX/TXT/MD extraction now runs in a separate Linux worker
  with 512 MiB virtual memory, 6 CPU seconds, 10-second wall timeout, sanitized
  worker environment and 6 MB input/25 MB DOCX-expanded/250k-character output
  bounds plus a two-slot per-API-process import admission semaphore.
  Default process mode shares host UID, filesystem and network; optional
  GOREECLOUD_AI_IMPORT_ISOLATION=bwrap runs the worker behind Linux
  namespaces, read-only interpreter/code, isolated /tmp and no network.
  Requested bwrap failures do not downgrade to process mode. No complete
  Wardveil/production acceptance is implied. See docs/SECURITY_IMPORTS.md.
- Sensitive HTTP responses have Cache-Control no-store, nosniff and
  no-referrer headers. Web and Linux clients permit only HTTPS or loopback HTTP.
  Android release is HTTPS-only; emulator HTTP is debug-only.
- Owner-only deletion removes live document rows/FTS terms and conversation
  snapshots. SQLite freelist pages/backups are not securely wiped.

## Missing production gates

- **GoreeCloud Identity:** pinned-JWKS RS256 verifier checks issuer, audience,
  exact owner subject and baseline scope; source-tested opt-in route capability
  scopes distinguish read, write, inference, cloud, paid, tools and admin,
  with fail-closed unknown routes. No verified GoreeCloud Identity issuer,
  MFA, delegated multiuser permissions, session lifecycle, tenant isolation
  or live trusted key-rotation contract yet.
- **GoreeShield:** opt-in SQLCipher local encryption with synthetic tests and
  non-destructive migration code exists; no verified activation, key custody,
  production policy enforcement, scheduled retention or cryptographic erasure.
- **Wardveil:** Linux parser subprocess resource bounds plus optional,
  synthetic-tested Bubblewrap namespace/filesystem/network isolation. No
  dedicated host UID, seccomp policy, workload cgroup, credential broker,
  malware inspection, threat monitoring or independent security acceptance.
- **GoreeCloud Mesh:** no production capability registry, service-to-service
  authentication adapter or resource policy propagation.
- **GoreeCloud UI:** web tokens and pinned MIT-licensed Android Material 3
  Expressive source adapter integrated; interactive/native visual acceptance open.
- No provider-cost reconciliation, currency reservations, vector RAG,
  autonomous tool agents, MCP OAuth, cross-worker global quotas or MCP
  server-process sandboxing. SDK transport parsing, redirects and remote
  provider behavior are not fully controlled by these application bounds. An offline encrypted snapshot/restore
  tool exists and is synthetic-tested, not a production backup policy.

## Optional security features

- Operator-controlled OIDC adapter verifies offline pinned RS256 JWKS keys,
  issuer, audience, owner subject, expiry and owner scope. Optional strict
  capability checks deny operations outside their read/write/inference/cloud/
  paid/tools/admin scopes. Default owner mode and the unextended signed-owner
  preview remain backwards compatible. No authoritative issuer integration
  or session lifecycle verification has occurred.
- Optional OpenRouter provider-key budget preflight checks the remote
  key's assigned credit limit and remaining balance before cloud inference.
  It is not a local USD reservation or end-to-end billing guarantee.
  In strict cap mode, the provider must explicitly confirm BYOK usage is
  included in the key's cap; false or missing confirmation fails closed.
- Explicit retention purge only targets old opt-in conversation snapshots;
  no background retention service is configured.
- Offline encrypted AES-256-GCM SQLite snapshot and isolated, checked restore
  tooling exist with synthetic tests. Live SQLite and FTS are plaintext.
  See docs/RECOVERY_AND_IDENTITY.md.

## Provider model discovery

- Owner-authenticated GET /api/v1/images/models fetches the fixed-origin
  OpenRouter image-model catalog only upon an operator/client request.
  The backend sends its **server-only OpenRouter key** as required by the
  provider's API; the public model metadata is size-limited and reduced
  to model ID/name/stream/reference capabilities. No documents, prompts,
  owner bearer tokens or provider API keys are returned to clients.
- Browser UI offers a discoverable model selector while retaining an explicit
  model ID field; discovery never automatically starts a paid generation.
- Generated image bytes are checked for allowed PNG/JPEG/WebP signatures and
  bounded at 12 MB before returning a data URL; this is not full media-decoder
  or third-party-content safety validation.
- Real OpenRouter acceptance, prices, provider policy and live model routing
  remain unverified; mock tests alone do not authorize purchases.

## Explicit provider-reported generation cost lookup

- OpenRouter may return a bounded generation ID on a successful model/image
  response or the final chat-stream event. IDs must match its documented
  `gen-...` format, not arbitrary URLs, tokens or untrusted control bytes.
- An authenticated owner (or `goreecloud.ai.admin` with strict signed-JWT
  scopes) can explicitly request GET
  `/api/v1/usage/openrouter/{generation_id}`, which queries the fixed
  `https://openrouter.ai/api/v1/generation` metadata endpoint using the
  server-managed key, with no redirects/ambient proxy, 8-second timeout,
  two concurrent requests per API worker and 64 KB response cap.
- The result is restricted to the selected generation ID, model, reported USD
  cost and explanatory source; it never stores or reflects prompts, completions,
  provider headers, raw provider metadata, key or user IDs. It does not
  automatically call the provider, spend model tokens, reserve currency,
  reconcile an independent invoice, or guarantee BYOK and multi-worker limits.
  Real-provider authority, billing, permissions, cost stability and rate
  limits require verification before production.

## Database upgrade and privacy

Before upgrading an existing SQLite database, privately back it up and test
restore in isolation. An additional offline SQLCipher-to-SQLCipher key
rotation exports into a distinct new-key encrypted destination; the source
remains unchanged. Old snapshots still require their original database key.
See docs/RECOVERY_AND_IDENTITY.md for source-preserving rollback and custody.
SQLCipher mode deliberately fails on plaintext input and
on wrong/missing keys. Migrate only with the API stopped using
`python -m app.migrate_sqlcipher --source OLD --output NEW` with a 32-byte
secret-manager-provided database key; the source is retained until explicitly
managed by its owner. See docs/RECOVERY_AND_IDENTITY.md.
The first new connection creates FTS5 index tables,
snapshot/message tables and admission counters, using PRAGMA user_version 1
for the indexed migration. File mode 0600 and directory mode 0700 are applied,
but encryption/OS backups and secure deletion are still the operator's duty.

## Sources

- OpenRouter image API: https://openrouter.ai/blog/tutorials/image-generation/
- OpenRouter unified media: https://openrouter.ai/blog/insights/every-modality-one-api/
- FastAPI streaming: https://fastapi.tiangolo.com/advanced/stream-data/
- Ollama API: https://docs.ollama.com/api/chat
