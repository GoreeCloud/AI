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
- Owner shared-token check, no prompt logging, fixed upstream OpenRouter URL,
  disabled redirects, bounded requests, reference validation and PDF/DOCX
  file limits. DOCX decompression metadata limit is not a sandbox.
- Sensitive HTTP responses have Cache-Control no-store, nosniff and
  no-referrer headers. Web and Linux clients permit only HTTPS or loopback HTTP.
  Android release is HTTPS-only; emulator HTTP is debug-only.
- Owner-only deletion removes live document rows/FTS terms and conversation
  snapshots. SQLite freelist pages/backups are not securely wiped.

## Missing production gates

- **GoreeCloud Identity:** no verified OIDC issuer/claims contract, MFA,
  delegated token scopes, tenant isolation or per-user session policy.
- **GoreeShield:** no production policy engine, encrypted storage, fine-grained
  consent record, private-data retention schedule or cryptographic erasure.
- **Wardveil:** no runtime tool sandbox, credential broker, malware inspection,
  import parser isolation, threat monitoring or independent security acceptance.
- **GoreeCloud Mesh:** no production capability registry, service-to-service
  authentication adapter or resource policy propagation.
- **GoreeCloud UI:** web tokens and pinned MIT-licensed Android Material 3
  Expressive source adapter integrated; interactive/native visual acceptance open.
- No monetary spend cap, provider pricing reconciliation, vector RAG, autonomous
  tool agents, MCP OAuth, production backups or restore evidence.

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
