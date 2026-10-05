# GoreeCloud AI — Notes

**Document version:** 0.2  
**Lifecycle:** Development

## Current verified repository state

GoreeCloud AI is under active Milestone 0 development in Draft PR #1 on branch `agent/milestone-0-foundation`.

Exact head `0ef9e7261be21c9d8652d47f3f7a793897e035fa` previously passed Validate GoreeCloud AI run `35006998441` and GoreeCloud AI Platform Contract run `35006999549` under the superseded Contract 0.2 / seven-system authority. That evidence remains exact-revision historical evidence only and does not establish Contract 2.0, Policy, Observability, or current Official Anchor Glaze UI conformance for a later candidate.

Current source version is `0.1.0-dev.0`. The application is not Anchor-qualified, production-ready, or accepted as a current Official Anchor Glaze UI consumer.

## Current implemented foundations

- React / TypeScript / Vite client.
- First-party Node.js backend bound to loopback by default.
- Backend-owned Ollama model discovery and streaming chat.
- Conversation and Workspace persistence.
- Private attachment storage with quotas and deletion handling.
- Wardveil-gated attachment release model and reference tests.
- Bounded safe-text extraction for approved passive text formats.
- Read-only knowledge eligibility and non-authorizing knowledge-authorization assessment.
- Strict runtime-evidence envelope assessment.
- Development-only durable hashed evidence/request use and revocation registry for replay state.
- Opt-in live runtime validator for backend health, Ollama discovery, and an explicitly selected streamed request.

## Current blockers / non-claims

The following are not established by current source alone:

- current Official Anchor Glaze `1.7.0` implementation and GoreeCloud AI-specific acceptance;
- authenticated GoreeCloud Identity transport and production application authorization;
- authenticated Privacy Shield enforcement, capability/evidence authority, durable authorization, revocation and replay acceptance;
- accepted live Wardveil transport/runtime evidence;
- GoreeCloud Manager acceptance;
- Everkeep backup/restore/export/portability acceptance;
- GoreeCloud Mesh integration and acceptance;
- GoreeCloud Policy AI-specific runtime decision, enforcement, and evidence acceptance;
- GoreeCloud Observability AI-specific health, telemetry, diagnostics, freshness, and evidence acceptance;
- production RAG, embeddings, indexing, retrieval, model-context authorization, or research integration;
- supported deployment, signing/package/release, representative runtime, or Anchor evidence.

A structurally valid caller-supplied trust record remains non-authoritative. `productionTrustedInput`, `persistentAuthorizationCreated`, `executionAuthorized`, and knowledge-stage eligibility must remain fail-closed until real authority is established.

## Governance correction

The current central machine-readable authority is Platform Contract `0.4`, accepted in `GoreeCloud/GoreeCloud` at exact merge revision `6cb150d512647a0401b4da9e4741d7591693dee0`. GoreeCloud AI must evaluate exactly nine Integral Platform Systems: GoreeCloud Manager, Privacy Shield, Wardveil Security, Everkeep, Glaze UI, GoreeCloud Mesh, GoreeCloud Identity, GoreeCloud Policy, and GoreeCloud Observability. GoreeCloud Sync remains separately governed and must not appear as a tenth `platform_systems` entry.

The current mandatory Official Anchor Glaze target is `1.7.0` from `GoreeCloud/glaze`. Prior GoreeCloud AI references to Glaze UI `1.6.0`, `1.4.1`, `1.1.0`, or experimental `2.x` targets are historical or stale current-state material and must not be relabeled as current acceptance.

The Contract 0.4 declaration keeps all nine application-specific integrations fail-closed unless accepted evidence exists. Adding Policy and Observability declarations records applicability and blockers; it does not manufacture runtime integration or conformance.

## Validation authority

`.github/workflows/validate.yml` checks the exact pull-request head for application type safety, server syntax, native server tests, production client build, Wardveil reference behavior, integration-contract validation, and Python compilation. `.github/workflows/platform-contract.yml` independently validates `goreecloud.platform.yaml` against the accepted central Contract 0.4 implementation pinned to exact revision `6cb150d512647a0401b4da9e4741d7591693dee0`.

A successful workflow result belongs only to the exact evaluated source revision. Any source change creates a new candidate and requires fresh exact-head validation; predecessor success never transfers automatically.

## Release boundary

Keep Draft PR #1 in Forge until exact-head validation and all applicable runtime, platform-system, privacy, security, recovery, accessibility, deployment, release, and representative acceptance gates are complete. Merge, Seal, deployment, production acceptance, and Anchor are separate decisions.
