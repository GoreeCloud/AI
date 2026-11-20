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
- API mock tests, web typecheck/bundle, Linux offscreen QML boot and Android
  debug APK checks in GitHub Actions.

## P0 — protect privacy and qualify release

1. GoreeCloud Identity signed-token/OIDC and per-client scoped access,
   trusted HTTPS ingress and anti-abuse controls before public exposure.
2. GoreeShield real consent policy, encrypted database+backup, retention
   controls, data minimization and verified erasure behavior.
3. Wardveil scans, document parser sandbox, prompt/tool injection boundaries,
   MCP allowlists/worker isolation and secure audit without content leakage.
4. True monetary caps based on provider prices, account credit/billing data,
   concurrency reservations and usage reconciliation across worker processes.
5. Test real Ollama/OpenRouter chat, streaming, images and MCP with safe data;
   no paid API call without explicit approved operator budget.
6. Android real device, Linux interactive, browser/screen reader and UI quality
   tests. Qualify signed packages and repository supply-chain provenance.
7. Maintain protected main PR gates, lockfiles, dependency audit, SBOM and
   tested restore/rollback.

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
