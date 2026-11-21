# GoreeCloud AI — features and source status

**Classification:** Native GoreeCloud product incorporating MIT-licensed
GoreeCloud UI source and independently licensed dependencies. This is a
**developer preview**, not a deployed or certified service.

| Capability | Current source status | Verification and limitations |
| --- | --- | --- |
| OpenRouter and Ollama text inference | Implemented in FastAPI; safe optional generation ID and owner-deliberate provider-reported USD cost metadata retrieval | Consent-gated OpenRouter; local Ollama opt-in; real cost/invoice/provider compatibility needs live safe testing |
| Chat SSE streaming/cancel | Server stream and React stream/abort implemented | Mock tests and web build; native cancellation parity pending |
| Image generation and catalog | Source-level backend and web/Android/Linux model selectors | Explicit paid approval; tested mock provider shape; real pricing, model and media compatibility unverified |
| Document editing, import/export | SQLite CRUD with opt-in SQLCipher encrypted full database/FTS5, export and resource-limited Linux imports with optional Bubblewrap | Live encryption needs activation/verified key custody; native file-picker parity pending |
| Local search and cited answers | SQLite FTS5 lexical retrieval, bounded source-linked text | No vector indexes; no guarantee of model factuality; source text is untrusted |
| Saved chat and retention | Explicit saved snapshots, approved purge, dry-run-first local retention CLI with opt-in apply, and optional systemd timer templates | No enabled/deployed scheduler or secure erasure; backup copies may retain prior data |
| Cloud consent and quotas | Default-off per-request approval, daily atomic request admission and metadata-only receipts | Admission is not actual spend; no provider billing reconciliation or production privacy engine |
| Offline encrypted backups | AES-256-GCM export/restore CLI for either storage mode, source-preserving plaintext-to-SQLCipher migration and SQLCipher key rotation | Real key custody/restore, operating cutover and off-host recovery unverified |
| Identity | Owner token; optional pinned RS256/JWKS signed-owner token with opt-in route capability checks | No real GoreeCloud Identity issuer, MFA, multiuser delegation or tenant isolation |
| Manual tools and MCP | Approved local document.read and operator-allowlisted MCP HTTPS/loopback tools with bounded arguments/time/concurrency/sanitized outputs | No autonomous tool execution, OAuth, isolated MCP worker or real MCP interop proof |
| Integration metadata | Owner-authenticated read-only v1 preview capability manifest | Not a registered, production-authenticated GoreeCloud Mesh service |
| Web client | React/TypeScript UI, token memory, consent, documents, chat, model browsing | Real browser, accessibility and visual acceptance open |
| Linux client | Native Qt Quick, opt-in SSE streaming/cancel through Qt Network and bounded frame parser; existing GoreeCloud UI token source | Offscreen smoke and synthetic localhost transport tests, but real desktop, screen reader and signing pending |
| Android client | Kotlin Compose Material 3 Expressive, pinned MIT gc-ui adapter, opt-in SSE streaming with cancellation and bounded parser | Host-side JUnit/build checks only; physical-device SSE, accessibility and signed release pending |

Source evidence resides in the app, web, Linux and Android directories,
their tests and GitHub Actions history. For exact current implementation,
review the authoritative main-branch code; a checklist is not runtime proof.

## Mandatory release dependencies

See [ROADMAP.md](ROADMAP.md), [OBJECTIVES.md](OBJECTIVES.md),
[RELEASE_GATES.md](RELEASE_GATES.md), [ARCHITECTURE.md](ARCHITECTURE.md)
and [SUPPLY_CHAIN.md](SUPPLY_CHAIN.md) for objectives, gate evidence and
remaining blockers. Do not mark production readiness from preview-source or
mock-test results.
