# GoreeCloud AI User Manual

## Status

GoreeCloud AI is under active native development. The current Draft Milestone 0 branch provides the first-party conversational application foundation, backend-owned Ollama access, persistent conversations, model roles, Workspaces, private attachment handling, Wardveil-gated attachment release, quota/deletion controls, bounded passive text extraction, read-only knowledge eligibility, and a bounded non-persistent knowledge-authorization assessment.

It is not Anchor-qualified or production-ready.

## Product Boundary

GoreeCloud AI owns the user-facing AI experience, conversations, Workspaces, files, future knowledge/RAG, research orchestration, tools, artifacts, and model access policy. Ollama is the primary local inference runtime. GoreeCloud Search is the intended first-party current-information and Internet-research provider.

The browser does not call Ollama directly. Model access is routed through the GoreeCloud AI backend so authentication, application authorization, Privacy Shield state, Wardveil enforcement, auditing, cancellation, and future runtime changes can remain server-owned.

The chat endpoint also rejects client-authored `system` messages. Browser chat history may contain only bounded user/assistant messages ending in a user request; Workspace system instructions are resolved and composed by the backend.

## Development Commands

Install dependencies and validate the current source with:

```bash
npm install
npm run check
npm run check:server
npm run test:server
npm run build
```

Start the client and backend with the development scripts in `package.json`. Active tokens, credentials, or environment-specific secrets belong in protected runtime configuration and must not be committed to source control.

## Conversations and Models

The current application supports Ollama model discovery through the backend, friendly GoreeCloud model-role selection, streaming chat responses, stop generation, Markdown/GFM rendering, persistent conversations, rename/edit, retry/recovery, conversation branching with parent lineage metadata, and Workspace association.

Use **Search conversations** in the sidebar to filter saved conversations by title, model, or Workspace name. Use the refresh control beside the model picker to re-query installed local models through the GoreeCloud AI backend.

While a response is streaming, GoreeCloud AI follows the latest output until you deliberately scroll away. Scrolling up suspends automatic following; use the down-arrow control to return to the latest message. If Ollama is reachable but reports no installed models, the runtime status says **No local models** rather than reporting an outage, and the composer explains that an approved local model must be installed before refreshing the list.

The download control exports the current visible conversation to a local Markdown file. This is a user-controlled browser export of the conversation transcript and basic model/Workspace metadata; it is not an Everkeep-governed backup, recovery, or full portability export.

Actual model identifiers remain runtime infrastructure and may change independently of the user-facing role names.

## Workspaces

Workspaces currently persist development state including name, instructions, default model role, file references, knowledge-collection placeholders, tool placeholders, and research preference state.

For a selected Workspace, **Rename** updates its display name and the **Default model role** selector updates the persisted role preference. When the chosen role has a recognized installed local model, GoreeCloud AI selects that model; when no matching model is installed, the UI states that no installed match exists instead of silently substituting one.

**Add instructions** or **Edit instructions** opens the private instruction editor. For each request, the browser sends the selected Workspace ID and the backend resolves the saved Workspace before prepending its instructions transiently as system context. The instructions are not inserted into the persisted conversation transcript, do not authorize tools or data access, and cannot override blocked Identity, Privacy Shield, Wardveil, Policy, knowledge, or external-processing gates.

Workspace membership and access boundaries are not yet backed by production GoreeCloud Identity multi-user/session enforcement and GoreeCloud AI application authorization.

## Attachments and Wardveil Trust States

Attachments enter private staging with restrictive local permissions. Storage alone does not make an attachment trusted or eligible for model context.

Current attachment states include:

- **Verified / available** — authoritative Wardveil evidence allowed release and context use for the exact SHA-256-bound artifact;
- **Unverified** — trust could not be established, including when no authenticated scanner transport is configured;
- **Held** — the trust decision requires review;
- **Blocked** — the trust decision requires blocking/quarantine handoff state.

The development application intentionally does not connect directly to ClamAV. Until an authenticated deployed Wardveil Scan transport exists, the scanner adapter remains unconfigured and uploads fail closed in private staging.

## Attachment Quotas and Deletion

The local development attachment library enforces configurable per-file, file-count, and aggregate-byte limits. Local file-store and delete mutations are serialized within one Node.js process.

Deleting a file removes its released or staged bytes, its derived text extraction when present, and stale Workspace file references. This is application cleanup only; it is not Wardveil quarantine, secure erasure, Everkeep retention proof, or proof that no other copies exist.

## Passive Text Extraction

The current post-release extraction boundary accepts only `text/plain`, `text/markdown`, `text/x-markdown`, and `application/json`.

Extraction requires the source attachment to be released and available, with Wardveil `releaseAllowed` and `useAsContextAllowed` state. GoreeCloud AI re-reads and SHA-256 hashes the released bytes before parsing so changed content cannot inherit prior trust evidence.

The parser uses fatal UTF-8 decoding, rejects unsupported control bytes, validates JSON, and applies a dedicated extraction-byte limit. Derived extraction records remain private and retain source/text digests for binding checks.

PDF, HTML, Office documents, archives, scripts/executables, images, audio, video, model artifacts, tool artifacts, and other parser-complex or active formats are not accepted by this initial extraction boundary.

Extraction does **not** authorize chunking, embeddings, indexing, retrieval, RAG participation, model-context use, tool execution, generated-code execution, research, or external processing.

## Knowledge Eligibility Assessment

For an existing attachment, the development API exposes:

`GET /api/files/:id/knowledge-eligibility`

This is a read-only inspection endpoint. It does not create an extraction, chunk data, compute embeddings, index content, retrieve content, insert model context, create authorization state, invoke research, or transfer data externally.

Without a separately supplied authorization assessment, the response reports Wardveil and extraction state while Identity/application authorization and Privacy Shield authorization remain pending. Indexing, retrieval, and model-context stages remain disabled.

Even when Wardveil release and safe extraction are satisfied, the current response keeps all of these false:

- `eligibleForIndexing`
- `eligibleForRetrieval`
- `eligibleForModelContext`

Do not interpret a pending state as approval.

## Knowledge Authorization Assessment

The current development API also exposes:

`POST /api/files/:id/knowledge-authorization-assessment`

This endpoint accepts bounded JSON for **assessment only**. It does not persist an authorization and does not execute a knowledge operation.

### Identity and application authorization

GoreeCloud Identity establishes authenticated identity and approved claims. GoreeCloud AI remains responsible for its own resource/Workspace authorization. The assessment therefore uses application-local operation names rather than inventing GoreeCloud-wide Identity permission scopes:

- `goreecloud-ai.knowledge.index`
- `goreecloud-ai.knowledge.retrieve`
- `goreecloud-ai.knowledge.model-context`

The supplied Identity/application context must include an authenticated actor, valid observation/expiration times, the exact attachment resource ID, and application authorization for the operation being assessed. Future-dated observations, expired/reversed time windows, resource mismatch, and missing operation permission fail closed.

### Privacy Shield decision input

The supplied Privacy Shield request/decision is checked against the current Privacy Shield authorization decision contract. The assessment checks request/decision binding, attachment resource ID, operation, requester/acting-user binding, processing zone, destination, permitted operations, decision expiration, optional request-retention expiration, and obligations. When a request-retention expiration is supplied, it must be a valid date-time or the assessment fails closed.

Outcome handling is preserved:

- `DENY` — blocked;
- `REQUIRE_USER_DECISION` — pending, not approval;
- `ALLOW` — structurally satisfied only when all checked bindings agree;
- `ALLOW_WITH_CONSTRAINTS` — structurally satisfied only when bindings agree, with obligations preserved.

The GoreeCloud AI operation names above are **not** new canonical Privacy Shield capability-registry identifiers.

### Why a satisfied assessment still cannot execute

Even when the supplied Identity/application and Privacy Shield inputs pass the structural checks, the response explicitly says:

- `sourceTrust.productionTrustedInput: false`
- `persistentAuthorizationCreated: false`
- `executionAuthorized: false`

The reason is that authenticated production Identity and Privacy Shield adapters, operation-bound capability/signature verification, durable authorization/evidence state, revocation/replay handling, and target-environment acceptance are not connected. A client-supplied JSON object cannot manufacture production authority.

A structurally satisfied assessment can report `pending_stage_implementation`, but all three knowledge execution eligibility booleans remain false. Privacy Shield `REQUIRE_USER_DECISION` reports `pending_privacy_user_decision`. Identity or Privacy denial remains blocked.

See `docs/KNOWLEDGE-AUTHORIZATION.md`.

## Live Runtime Validation

The repository includes:

```bash
npm run validate:runtime
```

By default the validator targets `http://127.0.0.1:8787`; set `GOREECLOUD_AI_URL` for an approved alternate test endpoint. If the API requires its development bearer, provide `GOREECLOUD_AI_API_TOKEN` in protected runtime configuration.

The validator checks the GoreeCloud AI health endpoint/service identity, reported Wardveil artifact-scanner configuration state, and Ollama model discovery through the GoreeCloud AI backend.

Set `VALIDATE_OLLAMA_MODEL=<installed-model-id>` to additionally send one bounded streamed chat request through the application backend. The validator requires assistant content chunks and a terminal done event but does not print the generated response content.

Set `VALIDATE_REQUIRE_WARDVEIL_SCANNER=true` only when validating an environment that is expected to have an authenticated Wardveil scanner transport. The check fails rather than treating an unconfigured scanner as acceptable evidence.

A passing runtime validation proves only the application/runtime path exercised by that run. It does not establish GoreeCloud Identity, Wardveil, Privacy Shield, Everkeep, Mesh, Glaze UI, deployment, recovery, or Anchor production acceptance.

## Glaze UI Migration State

The current authoritative Official Anchor consumer target is **Glaze V1.7 / 1.7.0** from `GoreeCloud/glaze`. Existing older Glaze UI and 2.x-labeled source is historical migration input and does not establish current conformance. GoreeCloud AI remains migration/reconciliation-required until its interface completes application-specific exact-revision 1.7.0 conformance/acceptance. Design-system promotion does not automatically promote this application.

## Privacy and External Processing

Privacy Shield remains authoritative for whether conversation, attachment, extracted, knowledge, or research data may be used for a purpose, retained, sent to a model, searched, or transferred externally. The structural assessment preserves Privacy Shield decisions but is not an authenticated Privacy Shield enforcement adapter.

GoreeCloud Search research integration and external-processing disclosure are not yet production-accepted. A Search outage must eventually remain isolated from local conversations and local knowledge workflows.

## Recovery and Portability

Everkeep remains authoritative for conversation/Workspace export, backup, restore, portability, preservation, retention, recovery evidence, continuity, and succession. Current local persistence and deletion behavior do not establish Everkeep recovery acceptance, including for future derived knowledge state.

## Current Acceptance Gaps

The Draft branch still requires, among other evidence:

- live authenticated Ollama interoperability evidence in the intended environment;
- a deployed authenticated Wardveil scanner transport, scanner/signature health, and controlled clean/malicious runtime validation;
- authenticated GoreeCloud Identity-backed multi-user/session boundaries plus GoreeCloud AI resource/Workspace authorization;
- authenticated Privacy Shield enforcement, operation-bound capability/evidence verification, and runtime data-use acceptance;
- Everkeep application lifecycle and recovery acceptance;
- GoreeCloud Mesh integration where required;
- additional safe parser decisions before broader ingestion;
- actual provenance/chunking/embeddings/indexing/retrieval/RAG/model-context execution with permission and privacy enforcement;
- migration/reconciliation to Glaze V1.7 / 1.7.0 and exact current consumer conformance evidence;
- deployment and broader production-readiness validation.

Do not represent successful source checks, a knowledge-eligibility/authorization assessment, or local runtime validation as Anchor or production-ready evidence.
