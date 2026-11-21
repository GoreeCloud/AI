# GoreeCloud AI — features and source status

**Classification:** Native GoreeCloud product incorporating MIT-licensed
GoreeCloud UI source and independently licensed dependencies. This is a
**developer preview**, not a deployed or certified service.

| Capability | Current source status | Verification and limitations |
| --- | --- | --- |
| OpenRouter and Ollama text inference | Implemented FastAPI; server-only OpenRouter text-model catalog with sanitized read-only metadata, explicit web selection; safe optional generation ID/cost read | Consent-gated OpenRouter; model metadata is not a price quote or compatibility guarantee; real provider acceptance and invoice reconciliation pending |
| Chat SSE streaming/cancel | Server and React stream/cancel, native Android Compose and Linux Qt streaming/cancel with host-side SSE tests | Physical device, real desktop, lifecycle, browser and provider acceptance pending |
| Token efficiency and caching | Explicit last-N history trimming with preserved system messages, local no-provider preview, configurable output-token caps, opt-in exact-response RAM cache and OpenRouter response/prompt cache controls; web editor toggles | RAM entries contain plaintext for up to 300s and are not shared across workers; upstream caches may retain prompt/answer data and incur write charges; no verified savings or native client parity |
| Image generation and catalog | Source-level backend and web/Android/Linux model selectors | Explicit paid approval; tested mock provider shape; real pricing, model and media compatibility unverified |
| Document editing, import/export and revisions | SQLite CRUD with opt-in SQLCipher/FTS5, per-save opt-in revisions capped at 20 with approved atomic restore and web history UI; export and import preflight | Extra content stored only with opt-in; no malware scanning, real key custody or native revision parity |
| Local search and cited answers | SQLite FTS5 lexical retrieval, bounded source-linked text and explicitly opt-in, source-version-keyed 300-second RAM reuse of exact research answers | Rechecks source versions per request; no semantic nearest-neighbor substitutions, vector index, data-at-rest encryption by default, or correctness guarantee |
| Saved chat and retention | Explicit snapshots, local FTS5 message/title search, owner-authenticated rename and JSON/Markdown export, bounded JSON import as a new snapshot, web in-memory branching, approved purge and dry-run-first opt-in retention CLI | Web library only (native UI parity pending); plaintext downloads and backup copies require protection; no deployed scheduler or secure erasure |
| Cloud consent and quotas | Default-off per-request approval, daily atomic request admission and metadata-only receipts | Admission is not actual spend; no provider billing reconciliation or production privacy engine |
| Offline encrypted backups | AES-256-GCM export/restore CLI for either storage mode, source-preserving plaintext-to-SQLCipher migration and SQLCipher key rotation | Real key custody/restore, operating cutover and off-host recovery unverified |
| Identity | Owner token; optional pinned RS256/JWKS signed-owner token with opt-in route capability checks | No real GoreeCloud Identity issuer, MFA, multiuser delegation or tenant isolation |
| Manual tools and MCP | Approved local document.read and operator-allowlisted MCP HTTPS/loopback tools with bounded arguments/time/concurrency/sanitized outputs | No autonomous tool execution, OAuth, isolated MCP worker or real MCP interop proof |
| Integration metadata | Owner-authenticated read-only v1 preview capability manifest | Not a registered, production-authenticated GoreeCloud Mesh service |
| Supply-chain inventories | CycloneDX 1.6 Python/npm locks and direct Gradle declarations; separate selected installed PySide6 wheel versions | No resolved Android dependency graph, complete native library SBOM, provenance or signing |
| Web client | React/TypeScript UI, token memory, consent, documents, chat, model browsing | Real browser, accessibility and visual acceptance open |
| Linux client | Qt Quick, SSE chat/cancel and redirect-refusing bounded Qt Network; private conversation library plus native latest-N history, output-token and opt-in local/OpenRouter caching controls; verified UI token source | Offscreen smoke and synthetic localhost PATCH/DELETE/JSON tests; real desktop, accessibility, package signing and file import/export pending |
| Android client | Kotlin Compose Material 3 Expressive, pinned MIT gc-ui adapter, SSE/cancel with bounded parser, private conversation import/export/delete, native token and opt-in caching controls; debug emulator-only HTTP | Pure host-side method policy tests and CI build pending; physical device/emulator networking, accessibility and signed release remain unverified |

Source evidence resides in the app, web, Linux and Android directories,
their tests and GitHub Actions history. For exact current implementation,
review the authoritative main-branch code; a checklist is not runtime proof.

## Mandatory release dependencies

See [ROADMAP.md](ROADMAP.md), [OBJECTIVES.md](OBJECTIVES.md),
[RELEASE_GATES.md](RELEASE_GATES.md), [ARCHITECTURE.md](ARCHITECTURE.md)
and [SUPPLY_CHAIN.md](SUPPLY_CHAIN.md) for objectives, gate evidence and
remaining blockers. Do not mark production readiness from preview-source or
mock-test results.
