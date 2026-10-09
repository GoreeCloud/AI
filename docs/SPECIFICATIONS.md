# GoreeCloud AI Specifications

## Product boundary

GoreeCloud AI is original GoreeCloud-owned AI application and orchestration software. Ollama is the initial replaceable local model runtime; GoreeCloud AI owns conversations, Workspaces, model-role abstraction, files, knowledge/RAG direction, tools/agents boundaries, research orchestration, and the user-facing product.

## Planned product scope and external-resource candidates

The owner-defined full product vision, 22-section capability map, proposed first-party architecture, candidate third-party dependencies and phased roadmap are maintained in [AI Product Vision and Architecture](./AI-PRODUCT-VISION-AND-ARCHITECTURE.md). This planning annex does not constitute a deployed feature, dependency selection, license acceptance, security approval, authenticated integration, runtime evidence or production qualification. The Development source contracts and fail-closed gates documented below continue to govern verified current implementation.

## Current Forge state

The active Milestone 0 foundation is in the canonical Forge lifecycle under Platform Contract 2.0. It includes a React/TypeScript/Vite client, Node.js backend, Ollama model discovery/streaming chat boundary, conversation persistence, model roles, Workspaces, private attachment storage, Wardveil-gated attachment release, attachment quotas/deletion, passive-text extraction, read-only knowledge eligibility, bounded Identity/application + Privacy Shield authorization-input assessment, an opt-in baseline live runtime validator, and a separately opt-in approved-model runtime validator for one policy-bound exact-model streamed Development request through the existing backend. The Draft pull request remains nonconformant and has not entered Seal or Anchor.

The default development server intentionally has no fabricated Wardveil scanner transport. Without an authenticated scanner adapter, uploads remain private/staged and `unverified` rather than becoming eligible for extraction or AI context.

## Development-only model routing

The Draft source includes an additive 13-role approved-model selector, a bounded backend preflight requiring explicit backend-supplied policy and installed-model discovery adapters, a restrictive local policy-file reader, and literal-loopback-only runtime discovery. The preflight rejects invalid, unapproved, expired, unavailable, or aborted requests and marks any selected model `policyTrust: development-unverified` and `inferenceAuthorized: false`. The adapters are not imported by the live backend and do not change the existing manual chat path, confer authenticated administrative provenance, execute inference, or establish platform acceptance. See `docs/MODEL_ROUTING.md`, `docs/MODEL_ROUTING_PREFLIGHT.md`, and `docs/MODEL_ROUTING_LOCAL_ADAPTERS.md`.

The isolated `server/model-resource-readiness.mjs` evaluator additionally checks an exact Development preflight selection against a strictly structured operator-declared role/capability profile, local-only workload, fresh host-capacity snapshot, context and estimated memory budgets, and concurrent-request headroom. It is not in the live HTTP/chat path. The opt-in `scripts/validate-model-resource.mjs` command composes this evaluator with the protected local policy/profile readers, read-only literal-loopback model discovery and a local free-system-RAM sample. Neither module measures actual GPU VRAM, proves runtime capabilities or grants inference/tool authority; all positive results remain development-unverified. See `docs/MODEL_RESOURCE_READINESS.md` and `docs/MODEL_RESOURCE_DIAGNOSTIC.md`.

## Attachment and extraction contract

Attachment intake separates storage from security release. A clean result is accepted only when current authoritative Wardveil evidence is bound to the exact AI resource and SHA-256 digest; released bytes are re-hashed before release.

Text extraction is a second, separate gate. It requires an `available`/`released` attachment whose Wardveil decision allows release and context use. Immediately before parsing, GoreeCloud AI re-hashes the released bytes and requires the digest to match the accepted attachment record.

Initial extraction media types are limited to `text/plain`, `text/markdown`, `text/x-markdown`, and `application/json`. UTF-8 decoding is fatal, unsupported control bytes fail closed, JSON must parse, and source size is bounded by `MAX_TEXT_EXTRACTION_BYTES`. Extracted records are private mode-0600 application data with source/content digests.

This source foundation does not authorize PDF/Office/HTML/archive parsing, embeddings, indexing, RAG retrieval, model-context use, tool execution, generated-code execution, or external processing.

## Knowledge-eligibility observation contract

`GET /api/files/:id/knowledge-eligibility` is a read-only assessment surface. It does not create extraction, embeddings, chunks, indexes, retrieval entries, model context, authorization state, or external processing.

It reports Wardveil release/context-use state, safe text-extraction eligibility/binding, Identity/application-authorization state, Privacy Shield authorization state, and whether indexing/retrieval/model-context stages exist. Without supplied authorization assessment, Identity and Privacy Shield remain pending.

The source always reports `eligibleForIndexing: false`, `eligibleForRetrieval: false`, and `eligibleForModelContext: false` because the downstream stages are still disabled and no authenticated production authorization adapters are connected.

## Knowledge authorization-input assessment contract

`POST /api/files/:id/knowledge-authorization-assessment` accepts bounded JSON and performs a **non-persistent, non-executable assessment** against the current attachment/extraction state.

GoreeCloud Identity's current architecture establishes authenticated identity/claims while each application remains responsible for its own authorization. Therefore the source uses GoreeCloud AI application-local operation identifiers rather than inventing central Identity scopes:

- `goreecloud-ai.knowledge.index`;
- `goreecloud-ai.knowledge.retrieve`; and
- `goreecloud-ai.knowledge.model-context`.

Identity input must be time-valid, authenticated, resource-bound, and paired with GoreeCloud AI application authorization permitting the selected operation.

Privacy input is structurally aligned to the current Privacy Shield decision contract. Request/decision binding, resource, operation, requester/acting-user, processing zone, destination, permitted operations, decision expiration, optional request-retention expiration, and obligations are checked. Malformed optional retention expiration fails closed. `DENY` blocks. `REQUIRE_USER_DECISION` remains pending. `ALLOW` and `ALLOW_WITH_CONSTRAINTS` can become structurally satisfied only when checked constraints agree.

These local operation names are not new canonical Privacy Shield capability IDs. Privacy Shield capability-registry adoption remains separately governed.

Even when both inputs are structurally satisfied, the result explicitly remains non-authoritative:

- `sourceTrust.productionTrustedInput: false`;
- `persistentAuthorizationCreated: false`;
- `executionAuthorized: false`.

Authenticated Identity/Privacy runtime adapters, operation-bound capability/signature verification, durable authorization/evidence state, revocation/replay handling, and production acceptance are not connected. Client-supplied JSON cannot manufacture production authority.

A satisfied structural assessment may produce `pending_stage_implementation`, but indexing, retrieval, and model-context booleans remain false. See `docs/KNOWLEDGE-AUTHORIZATION.md`.

## Live runtime-validation contract

`npm run validate:runtime` validates the first-party application path rather than connecting a browser client directly to Ollama. The base run checks GoreeCloud AI service health, reported Wardveil scanner configuration state, and Ollama model discovery through `/api/ollama/models`. The public health response exposes capability/configuration state only; it does not return the configured Ollama endpoint.

When `VALIDATE_OLLAMA_MODEL` explicitly selects an installed model, the validator sends one bounded chat request through `/api/ollama/chat` and requires streamed assistant content plus a terminal `done` event. The live backend also enforces bounded total-stream and per-event NDJSON limits, strict UTF-8/JSON parsing, public-field reduction, and response backpressure handling before forwarding stream events to the browser. Generated response content is not printed by the validator.

If the application test endpoint requires the current development bearer, `GOREECLOUD_AI_API_TOKEN` may be supplied through protected runtime configuration. `VALIDATE_REQUIRE_WARDVEIL_SCANNER=true` is an explicit expectation gate: the validator fails if the application reports the Wardveil artifact scanner as unconfigured rather than converting absence into positive evidence.

A passing run proves only the runtime path exercised. It does not establish GoreeCloud Identity, Wardveil, Privacy Shield, Everkeep, Mesh, exact Glaze UI conformance, deployment, recovery, or Anchor production acceptance.

### Approved-model runtime-validation extension

`npm run validate:approved-model-runtime` is a stricter Development evidence path for one exact model request. It requires `VALIDATE_APPROVED_MODEL_RUNTIME=local-development-only`, a protected absolute `VALIDATE_MODEL_POLICY_PATH`, a supported `VALIDATE_MODEL_ROLE`, an exact `VALIDATE_MODEL_PREFERRED`, and a literal-loopback GoreeCloud AI URL. It reuses the protected local policy loader and bounded approved-role preflight, but obtains installed-model discovery through the first-party application before invoking the existing chat endpoint.

The command uses a fixed non-sensitive prompt, bounds JSON/stream size and time, rejects redirects and non-loopback targets, and never prints generated content, bearer values, policy contents/paths, configured URLs or arbitrary upstream bodies. Successful output is sanitized and explicitly scoped to one operator-initiated Development request with `productionInferenceAuthorized=false`, `productionAccepted=false` and `stableQualified=false`.

This extension is not imported by `server/index.mjs`, changes no HTTP route or authentication behavior, does not load models, and does not establish target-host GPU/VRAM capacity, sustained workload suitability, authenticated administrator provenance or platform acceptance. See `docs/APPROVED_MODEL_RUNTIME_VALIDATION.md`.

## Platform-system requirements

- **Glaze:** current mandatory consumer target is Official Anchor **Glaze V1.7 / 1.7.0** from `GoreeCloud/glaze`. GoreeCloud AI remains migration/reconciliation-required until exact-revision 1.7.0 consumer acceptance is completed; older Glaze UI and 2.x-labeled source is historical migration input and is not current conformance evidence.
- **Wardveil Security:** source-level artifact trust enforcement exists, but authenticated deployed Scan transport and application production acceptance remain pending. GoreeCloud AI does not connect directly to ClamAV.
- **Privacy Shield:** the current decision contract is consumed for structural assessment, but authenticated runtime enforcement, trusted capabilities/evidence, durable state, and AI consumer acceptance remain pending. A structurally satisfied supplied decision is not production authority.
- **Everkeep:** export, backup, restore, preservation, portability, succession, attachment/extraction/derived-knowledge lifecycle, and application recovery acceptance remain pending.
- **GoreeCloud Identity:** Identity provides authenticated identity/claims while GoreeCloud AI owns application authorization. Current assessment validates supplied identity/application context but no authenticated production Identity adapter or durable multi-user boundary is connected.
- **GoreeCloud Mesh:** cross-system capability/evidence coordination remains pending and cannot manufacture AI security/privacy/continuity truth.

## Validation

CI validates application TypeScript, server syntax including authorization/eligibility modules and both runtime validators, native server/security/lifecycle/knowledge/model-routing tests, production client build, Python Wardveil reference behavior, the AI/Wardveil contract, and Python compilation. The approved-model runtime diagnostic has isolated subprocess/loopback tests, but CI never runs real model inference. Live target-host model/hardware, Identity, Privacy, Policy and Wardveil interoperability remains separate acceptance evidence.

## Anchor boundary

GoreeCloud AI is not Anchor-qualified or production-ready. Live Ollama/Wardveil interoperability, migration/reconciliation to current Official Anchor Glaze V1.7 / 1.7.0 and consumer evidence, Identity-backed multi-user/application authorization, Privacy Shield runtime acceptance, Everkeep lifecycle/recovery, Mesh integration, safe parsers/RAG stages, and broader runtime/deployment evidence remain required.
