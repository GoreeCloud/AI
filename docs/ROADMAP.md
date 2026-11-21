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
- OpenRouter public image-model discovery, web selector, bounded provider
  response streaming and image format checks with no paid test calls.
- API mock tests, web typecheck/bundle, Linux offscreen QML boot and Android
  debug APK checks in GitHub Actions.

## Source-level security foundation (not production acceptance)

- Optional signed RS256/JWKS owner-scope verifier (offline pinned keys).
- Optional capped OpenRouter key preflight with provider-owned limit.
- Owner-approved retention cleanup and offline AES-GCM backup/restore.
- Protected preview capability metadata for future Mesh contracts.
- These do not establish GoreeCloud Identity/OIDC integration, complete
  GoreeShield enforcement, Wardveil certification, or backup operations.

## P0 — protect privacy and qualify release

1. Complete the source-authenticated GoreeCloud Identity issuer and claims
   integration beyond the pinned JWKS verifier; per-route delegated scopes,
   TLS ingress, MFA and anti-abuse controls before public exposure.
2. GoreeShield enforced consent records and retention scheduling beyond the
   explicitly approved snapshot purge; encrypt the live database, harden
   backup custody, data minimization and verified erasure behavior.
3. Wardveil scans and real untrusted-document sandboxing beyond the tested
   subprocess limits; enforce OS identity and network isolation, prompt/tool
   injection boundaries, MCP worker isolation and content-free security audit.
4. Require/verify provider-enforced per-key credit caps, then add real
   monetary reservations and usage/billing reconciliation across workers;
   present preflight is not a dollar spend guarantee.
5. Test real Ollama/OpenRouter chat, streaming, images and MCP with safe data;
   no paid API call without explicit approved operator budget.
6. Android real device, Linux interactive, browser/screen reader and UI quality
   tests. Qualify signed packages and repository supply-chain provenance.
7. Maintain protected main PR gates, SHA-pinned GitHub Actions, locked Python
   and web production dependency CVE checks and lockfile-derived component
   inventories. Finish native Android/Qt SBOM, provenance/signing, and tested
   restore/rollback.

## P1 — capabilities

- Scoped vector embeddings/reranking, private RAG citations, sandboxed PDF and
  DOCX viewers and native import/export parity.
- Tool-capable agents with durable state, approvals, budgets, operation audit,
  sandbox execution, MCP delegated auth and policy decision points.
- OpenRouter model/image capability discovery, costs, pricing/version policy,
  routing profiles and native streaming/cancellation.
- Voice, transcription, TTS, editing history, media library and offline-first sync.

## P2 — ecosystem adoption

- Mesh SDK for service-to-AI calls, GoreeShield consent integration, Wardveil
  runtime enforcement, Identity authorization, and gc-ui-native interfaces.
- Source-authenticated production contracts, operational observability,
  encrypted backup/restore, compatibility migration and rollout gates.
- Stable/Anchor only after verified all-five-MIPS acceptance.
