# GoreeCloud AI — architecture and security boundary

**Single-owner developer preview.** This is source and tests, not a certified
production deployment.

## Components and data

- React web, Qt Quick 6.12 Linux and Kotlin Compose Android use an authenticated
  versioned FastAPI API, with server-only OpenRouter keys and local Ollama.
- Chat history stays in client memory unless saved as an explicit local snapshot.
- Documents and conversation snapshots remain plaintext in owner-controlled
  SQLite. Local FTS5 search indexes title/body; no embeddings or external
  service is used for search.
- Retrieval question-answering selects bounded local excerpts and source IDs.
  Sources are untrusted reference material, not executable instructions.
  Excerpts are sent to OpenRouter only when expressly consented, else Ollama.
- MCP tools require server-configured HTTPS/loopback endpoint, name allowlist,
  authenticated owner request and explicit per-call approval. Model-produced
  text never automatically invokes MCP.

## Implemented controls

- Cloud-processing consent defaults false for chat, streaming, research
  and agent plans. Auto uses OpenRouter only with consent and configured key,
  otherwise local Ollama or fail closed. Paid image requests require their
  own approval and also transmit data to a cloud provider.
- SQLite-atomic daily external-provider request admissions default to 20
  (GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT). This is **not** a currency cap:
  provider pricing, token bills and charge reconciliation are independent.
  Failed requests may still consume an admission slot.
- Owner shared-token check, no prompt logging, bounded streamed JSON responses,
  validated base64 image formats, fixed upstream OpenRouter URL,
  disabled redirects, bounded requests, reference validation and PDF/DOCX
  file limits. PDF/DOCX/TXT/MD extraction now runs in a separate Linux worker
  with 512 MiB virtual memory, 6 CPU seconds, 10-second wall timeout, sanitized
  worker environment and 6 MB input/25 MB DOCX-expanded/250k-character output
  bounds plus a two-slot per-API-process import admission semaphore.
  It is **not a sandbox**: the worker retains same OS UID, filesystem
  permissions and network namespace; full Wardveil isolation is still required.
- Sensitive HTTP responses have Cache-Control no-store, nosniff and
  no-referrer headers. Web and Linux clients permit only HTTPS or loopback HTTP.
  Android release is HTTPS-only; emulator HTTP is debug-only.
- Owner-only deletion removes live document rows/FTS terms and conversation
  snapshots. SQLite freelist pages/backups are not securely wiped.

## Missing production gates

- **GoreeCloud Identity:** the optional pinned JWKS verifier checks RS256,
  issuer, audience, owner subject and required scope. No verified GoreeCloud
  Identity issuer/claims contract, MFA, delegated per-route scopes, tenant
  isolation or operational key lifecycle yet.
- **GoreeShield:** no production policy engine, encrypted storage, fine-grained
  consent record, private-data retention schedule or cryptographic erasure.
- **Wardveil:** a resource-limited Linux import subprocess isolates crashes
  and bounded parser execution from the API process. No OS user/container sandbox,
  network denial, credential broker, malware inspection, threat monitoring or
  independent security acceptance.
- **GoreeCloud Mesh:** no production capability registry, service-to-service
  authentication adapter or resource policy propagation.
- **GoreeCloud UI:** web tokens and pinned MIT-licensed Android Material 3
  Expressive source adapter integrated; interactive/native visual acceptance open.
- No provider-cost reconciliation, currency reservations, vector RAG,
  autonomous tool agents or MCP OAuth. An offline encrypted snapshot/restore
  tool exists and is synthetic-tested, not a production backup policy.

## Optional security features

- Operator-controlled OIDC adapter verifies offline pinned RS256 JWKS keys,
  issuer, audience, owner subject, expiry and owner scope. It is not yet
  connected to the authoritative GoreeCloud Identity source issuer or sessions.
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

## Database upgrade and privacy

Before upgrading an existing SQLite database, privately back it up and test
restore in isolation. The first new connection creates FTS5 index tables,
snapshot/message tables and admission counters, using PRAGMA user_version 1
for the indexed migration. File mode 0600 and directory mode 0700 are applied,
but encryption/OS backups and secure deletion are still the operator's duty.

## Sources

- OpenRouter image API: https://openrouter.ai/blog/tutorials/image-generation/
- OpenRouter unified media: https://openrouter.ai/blog/insights/every-modality-one-api/
- FastAPI streaming: https://fastapi.tiangolo.com/advanced/stream-data/
- Ollama API: https://docs.ollama.com/api/chat
