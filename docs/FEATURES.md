# GoreeCloud AI — features and source status

**Classification:** Native GoreeCloud product incorporating MIT-licensed
GoreeCloud UI source and independently licensed dependencies. This is a
**developer preview**, not a deployed or certified service.

| Capability | Current source status | Verification and limitations |
| --- | --- | --- |
| OpenRouter and Ollama text inference | Implemented in FastAPI; safe optional generation ID and owner-deliberate provider-reported USD cost metadata retrieval | Consent-gated OpenRouter; local Ollama opt-in; real cost/invoice/provider compatibility needs live safe testing |
| Chat SSE streaming/cancel | Server and React stream/cancel, native Android Compose and Linux Qt streaming/cancel with host-side SSE tests | Physical device, real desktop, lifecycle, browser and provider acceptance pending |
| Image generation and catalog | Source-level backend and web/Android/Linux model selectors | Explicit paid approval; tested mock provider shape; real pricing, model and media compatibility unverified |
| Document editing, import/export | SQLite CRUD and opt-in SQLCipher/FTS5, export, PDF/ZIP signatures and UTF-8 text preflight before bounded Linux parser and optional Bubblewrap | No malware inspection; real encryption/key custody, full parser security and native picker parity pending |
| Local search and cited answers | SQLite FTS5 lexical retrieval, bounded source-linked text | No vector indexes; no guarantee of model factuality; source text is untrusted |
| Saved chat and retention | Explicit saved snapshots, approved purge, dry-run-first local retention CLI with opt-in apply, and optional systemd timer templates | No enabled/deployed scheduler or secure erasure; backup copies may retain prior data |
| Cloud consent and quotas | Default-off per-request approval, daily atomic request admission and metadata-only receipts | Admission is not actual spend; no provider billing reconciliation or production privacy engine |
| Offline encrypted backups | AES-256-GCM export/restore CLI for either storage mode, source-preserving plaintext-to-SQLCipher migration and SQLCipher key rotation | Real key custody/restore, operating cutover and off-host recovery unverified |
| Identity | Owner token; optional pinned RS256/JWKS signed-owner token with opt-in route capability checks | No real GoreeCloud Identity issuer, MFA, multiuser delegation or tenant isolation |
| Manual tools and MCP | Approved local document.read and operator-allowlisted MCP HTTPS/loopback tools with bounded arguments/time/concurrency/sanitized outputs | No autonomous tool execution, OAuth, isolated MCP worker or real MCP interop proof |
| Integration metadata | Owner-authenticated read-only v1 preview capability manifest | Not a registered, production-authenticated GoreeCloud Mesh service |
| Supply-chain inventories | CycloneDX 1.6 Python/npm locks and direct Gradle declarations; separate selected installed PySide6 wheel versions | No resolved Android dependency graph, complete native library SBOM, provenance or signing |
| Web client | React/TypeScript UI, token memory, consent, documents, chat, model browsing | Real browser, accessibility and visual acceptance open |
| Linux client | Qt Quick, SSE chat/cancel and all authenticated REST through redirect-refusing bounded Qt Network bridges; verified GoreeCloud UI token source | Offscreen smoke and synthetic loopback redirect/credential/JSON tests, but real desktop, screen reader and signing pending |
| Android client | Kotlin Compose Material 3 Expressive, pinned MIT gc-ui adapter, SSE/cancel with bounded parser; debug-only cleartext exception for emulator alias | Source policy tests and CI build, but physical device/emulator networking, accessibility and signed release pending |

Source evidence resides in the app, web, Linux and Android directories,
their tests and GitHub Actions history. For exact current implementation,
review the authoritative main-branch code; a checklist is not runtime proof.

## Mandatory release dependencies

See [ROADMAP.md](ROADMAP.md), [OBJECTIVES.md](OBJECTIVES.md),
[RELEASE_GATES.md](RELEASE_GATES.md), [ARCHITECTURE.md](ARCHITECTURE.md)
and [SUPPLY_CHAIN.md](SUPPLY_CHAIN.md) for objectives, gate evidence and
remaining blockers. Do not mark production readiness from preview-source or
mock-test results.
