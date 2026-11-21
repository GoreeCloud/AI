# GoreeCloud AI — features and source status

**Classification:** Native GoreeCloud product incorporating MIT-licensed
GoreeCloud UI source and independently licensed dependencies. This is a
**developer preview**, not a deployed or certified service.

| Capability | Current source status | Verification and limitations |
| --- | --- | --- |
| OpenRouter and Ollama text inference | Implemented in FastAPI | Consent-gated OpenRouter; local Ollama opt-in; network/provider compatibility needs live safe testing |
| Chat SSE streaming/cancel | Server stream and React stream/abort implemented | Mock tests and web build; native cancellation parity pending |
| Image generation and catalog | Source-level backend and web/Android/Linux model selectors | Explicit paid approval; tested mock provider shape; real pricing, model and media compatibility unverified |
| Document editing, import/export | SQLite CRUD, Markdown/DOCX export; resource-limited Linux PDF/DOCX/TXT import with opt-in Bubblewrap network/filesystem isolation | Live SQLite/FTS plaintext; production sandbox review and native file-picker parity pending |
| Local search and cited answers | SQLite FTS5 lexical retrieval, bounded source-linked text | No vector indexes; no guarantee of model factuality; source text is untrusted |
| Saved chat and retention | Explicit local conversation snapshots, delete and approved purge | No secure erasure or scheduled service; backups may retain prior data |
| Cloud consent and quotas | Default-off per-request approval, daily atomic request admission and metadata-only receipts | Admission is not actual spend; no provider billing reconciliation or production privacy engine |
| Offline encrypted backups | AES-256-GCM encrypted export/restore CLI, synthetic tests | Running database remains plaintext; off-host recovery unverified |
| Identity | Owner token; optional pinned RS256/JWKS signed-owner token with opt-in route capability checks | No real GoreeCloud Identity issuer, MFA, multiuser delegation or tenant isolation |
| Manual tools and MCP | Approved local document.read and operator-allowlisted MCP HTTPS/loopback tools with bounded arguments/time/concurrency/sanitized outputs | No autonomous tool execution, OAuth, isolated MCP worker or real MCP interop proof |
| Integration metadata | Owner-authenticated read-only v1 preview capability manifest | Not a registered, production-authenticated GoreeCloud Mesh service |
| Web client | React/TypeScript UI, token memory, consent, documents, chat, model browsing | Real browser, accessibility and visual acceptance open |
| Linux client | Native Qt Quick preview using GoreeCloud UI token source | Headless smoke only; interactive desktop and package signing pending |
| Android client | Kotlin Compose Material 3 Expressive, pinned MIT gc-ui adapter | Debug APK CI only; physical-device and signed release pending |

Source evidence resides in the app, web, Linux and Android directories,
their tests and GitHub Actions history. For exact current implementation,
review the authoritative main-branch code; a checklist is not runtime proof.

## Mandatory release dependencies

See [ROADMAP.md](ROADMAP.md), [OBJECTIVES.md](OBJECTIVES.md),
[RELEASE_GATES.md](RELEASE_GATES.md), [ARCHITECTURE.md](ARCHITECTURE.md)
and [SUPPLY_CHAIN.md](SUPPLY_CHAIN.md) for objectives, gate evidence and
remaining blockers. Do not mark production readiness from preview-source or
mock-test results.
