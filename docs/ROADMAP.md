# GoreeCloud AI — remaining engineering priorities

Source presence is not release evidence. Validate CI and real providers/devices
separately before marking any item complete.

## Implemented in development source

- OpenRouter/Ollama router, optional local fallback, stream/cancel API,
  consent-gated cloud routing and bounded request-count budget.
- Explicit local conversation snapshots, SQLite FTS5 search/retrieval,
  source-linked responses and document/conversation deletion.
- Web, Linux Qt Quick and Android Kotlin Compose clients, including the
  pinned GoreeCloud UI Material 3 Expressive source adapter.
- Native Android and Linux image studios can browse and choose server-reported
  image models without triggering paid generation.
- Android Compose has streamed chat/cancellation, host-side SSE framing tests
  and no new cloud consent bypass; real device/provider qualification pending.
- Native Qt Linux chat uses Qt Network SSE streaming and explicit cancellation
  with bounded frame decoding, redirect refusal and synthetic localhost tests;
  real desktop and provider acceptance remain pending.
- OpenRouter public image-model discovery, web selector, bounded provider
  response streaming and image format checks with no paid test calls.
- API mock tests, web typecheck/bundle, Linux offscreen QML boot and Android
  debug APK checks in GitHub Actions.

## Source-level security foundation (not production acceptance)

- Optional signed RS256/JWKS owner-scope verifier with source-tested,
  opt-in per-route read/write/inference/cloud/paid/tools/admin capabilities
  and fail-closed unknown protected routes (offline pinned keys).
- Optional capped OpenRouter key preflight with provider-owned limit.
- Source-tested deliberate owner-only OpenRouter generation metadata read
  with ID validation, bounded fixed-origin query and provider-reported
  USD cost only; no automatic requests, invoice matching or money cap.
- Manual MCP call admission/argument/output/time bounds, early operator
  allowlist check and opaque media omission; no real server interoperability
  acceptance or isolated MCP worker.
- Optional Bubblewrap parser isolation (read-only runtime, no network or
  host data mounts) with synthetic Linux checks; default subprocess retained.
- Owner-approved retention cleanup, metadata-only cloud admission receipts
  and separate opt-in, content-free, atomic local retention maintenance CLI
  with uninstalled systemd example; opt-in SQLCipher encrypted live
  SQLite/FTS5, non-overwriting offline migration and source-preserving
  encrypted-to-encrypted key rotation, and AES-GCM backup/restore for either
  storage mode (synthetic-tested).
- Protected preview capability metadata for future Mesh contracts.
- These do not establish GoreeCloud Identity/OIDC integration, complete
  GoreeShield enforcement, Wardveil certification, or backup operations.

## P0 — protect privacy and qualify release

1. Complete source-authenticated GoreeCloud Identity issuer integration beyond
   the offline pinned-JWKS and opt-in capability-scoped adapter; delegated
   multi-user scopes, TLS ingress, MFA and anti-abuse before public exposure.
2. GoreeShield enforced consent policy and verified runtime scheduling beyond
   the implemented opt-in local-only retention CLI and uninstalled timer template;
   qualify/activate optional SQLCipher with real operator key custody, encrypted
   deployment and rollback, harden backup custody, data minimization and
   verified erasure behavior.
3. Wardveil production-qualify opt-in Bubblewrap import isolation with
   dedicated host UID, seccomp and cgroup controls; add malware scanning,
   prompt/tool injection boundaries, MCP worker isolation and delegated
   authorization beyond bounded manual calls, and content-free audit.
4. Require/verify provider-enforced per-key credit caps, then add real
   monetary reservations, automatic admission-to-generation ID linkage
   and invoice-level reconciliation across workers. The optional manual
   metadata lookup and preflight are not a dollar spend guarantee.
5. Test real Ollama/OpenRouter chat, streaming, images and MCP with safe data;
   no paid API call without explicit approved operator budget.
6. Android real device, Linux interactive, browser/screen reader and UI quality
   tests. Qualify signed packages and repository supply-chain provenance.
7. Maintain protected main PR gates, SHA-pinned GitHub Actions, locked Python
   and web production dependency CVE checks, Python/npm lock inventories,
   declared direct Gradle dependencies and partial installed PySide6 wheel
   inventories. Complete **resolved** Android/Qt/OS dependency graph, licenses,
   reproducible builds, provenance/signing, and tested restore/rollback.

## P1 — capabilities

- Scoped vector embeddings/reranking, private RAG citations, sandboxed PDF and
  DOCX viewers and native import/export parity.
- Tool-capable agents with durable state, approvals, budgets, operation audit,
  sandbox execution, MCP delegated auth and policy decision points.
- OpenRouter model/image capability discovery, costs, pricing/version policy,
  routing profiles and physical-device native streaming/cancellation
  qualification; Android Compose and Linux Qt SSE are source-implemented,
  but live-provider, lifecycle and real-device acceptance remain open.
- Voice, transcription, TTS, editing history, media library and offline-first sync.

## P2 — ecosystem adoption

- Mesh SDK for service-to-AI calls, GoreeShield consent integration, Wardveil
  runtime enforcement, Identity authorization, and gc-ui-native interfaces.
- Source-authenticated production contracts, operational observability,
  encrypted backup/restore, compatibility migration and rollout gates.
- Stable/Anchor only after verified all-five-MIPS acceptance.
