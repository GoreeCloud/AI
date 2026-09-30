# GoreeCloud AI

Native GoreeCloud-owned AI application for private conversations, Workspaces, knowledge/RAG direction, research, tools, agents, files, artifacts, and locally operated intelligence.

> **Lifecycle:** Forge — Milestone 0 foundation under active development in Draft PR #1. This repository is not production-accepted, Seal-qualified, or Anchor-qualified.

## Project records

- [Specifications](docs/SPECIFICATIONS.md)
- [Implemented features — canonical current capability state](docs/IMPLEMENTED-FEATURES.md)
- [Planned/open features — canonical incomplete capability state](docs/PLANNED-FEATURES.md)
- [Changelogs — canonical repository change history](docs/CHANGELOGS.md)
- [Feature overview](docs/FEATURES.md)
- [Benefits](docs/BENEFITS.md)
- [Competitive objectives](docs/COMPETITIVE-OBJECTIVES.md)
- [User manual](docs/USER-MANUAL.md)
- [Knowledge authorization boundary](docs/KNOWLEDGE-AUTHORIZATION.md)
- [Development model routing](docs/MODEL_ROUTING.md)
- [Bounded routing preflight](docs/MODEL_ROUTING_PREFLIGHT.md)
- [Local-only routing adapters](docs/MODEL_ROUTING_LOCAL_ADAPTERS.md)
- [Opt-in developer model-routing diagnostic](docs/MODEL_ROUTING_DIAGNOSTIC.md)
- [Development-only model capability and resource-fit guard](docs/MODEL_RESOURCE_READINESS.md)
- [Opt-in local model-resource diagnostic](docs/MODEL_RESOURCE_DIAGNOSTIC.md)
- [Approved local model runtime validation](docs/APPROVED_MODEL_RUNTIME_VALIDATION.md)
- [Branding authority](docs/BRANDING.md)

## Product boundary

GoreeCloud AI is an original first-party GoreeCloud application rather than a reskinned third-party AI interface. The intended permanent component relationship is:

- **GoreeCloud AI** — conversations, Workspaces, knowledge/RAG, files, tools, agents, artifacts, research orchestration, application authorization, model-role selection, and the user-facing product.
- **Ollama** — replaceable local model-execution runtime.
- **GoreeCloud Search** — first-party current-information and Internet-research provider.
- **GoreeCloud Identity** — authenticated identity, sessions, credentials, and approved identity claims; GoreeCloud AI still owns application authorization/data-access decisions.
- **Wardveil Security** — protection, trust, scanning, policy, verification, and response boundaries.
- **Privacy Shield** — privacy, consent, purpose, data-use, and minimization authority.
- **Everkeep** — backup, restore, recovery, preservation, portability, succession, and continuity authority.
- **GoreeCloud Mesh** — cross-system coordination, governance, and evidence transport.
- **Glaze UI** — visual, interaction, accessibility, responsive, and design-system authority.

Open WebUI, AnythingLLM, SearXNG, individual model names, and individual scanner engines are replacement targets/infrastructure rather than permanent product boundaries.

## Current implementation

The repository includes:

- React + TypeScript + Vite client and responsive conversation shell.
- Backend-owned Ollama discovery and streaming NDJSON chat with cancellation, timeout, and upstream failure isolation.
- Stable GoreeCloud model-role abstraction mapped to replaceable installed Ollama models.
- Development-only approved 13-role model selector, bounded server-side routing preflight, private local policy-file reader, and loopback-only model discovery. These components are not connected to live chat and grant no production inference authority.
- Independent operator-declared model capability/resource-fit assessor and a separately opt-in Development-only local diagnostic. The latter samples free system RAM but does not measure GPU VRAM, establish real model capabilities, run inference, or grant authorization.
- Separately opt-in approved-model runtime validation that requires a protected Development approval policy, exact role/model selection and literal-loopback GoreeCloud AI; it executes one streamed request through the existing backend and emits only sanitized evidence. It does not change live routing or grant production authorization.
- Persistent conversations with rename, delete, edit/resubmit, regeneration, branching, and lineage metadata.
- Native Workspaces with instructions, default model role, file references, knowledge/tool placeholders, and research preferences.
- Private attachment staging, restrictive permissions, SHA-256 binding, quotas, storage usage, deletion, and Workspace reference reconciliation.
- Node-native Wardveil artifact trust gate with exact resource/digest binding, fail-closed unavailable/unknown behavior, and non-destructive quarantine handoff state.
- Passive post-Wardveil text extraction for released UTF-8 text, Markdown, and JSON with source-digest revalidation and private derived records.
- Read-only knowledge-eligibility assessment that never authorizes indexing, retrieval, or model context.
- Bounded non-persistent knowledge-authorization assessment for supplied GoreeCloud Identity/application context plus the current Privacy Shield decision contract.
- Strict resource, operation, actor, request, processing-zone, destination, obligation, decision-expiration, and optional request-retention-expiration validation with Privacy Shield `DENY`/`REQUIRE_USER_DECISION` semantics preserved.
- Explicit source-trust boundary: supplied authorization JSON is not production-trusted, creates no durable authorization, and cannot execute a knowledge stage while authenticated adapters are absent.
- Independent Python Wardveil artifact-intake reference contract and validation suite.
- Opt-in live runtime validator for first-party service health/model discovery and optional streamed Ollama chat through the GoreeCloud AI backend.

The current development server deliberately has no fabricated Wardveil scanner transport. Default uploads therefore remain private/staged and `unverified`; they cannot enter text extraction or AI context.

## Architecture

```text
Browser / native client
        |
        v
GoreeCloud AI backend
        |
        +-- Identity authenticated actor/session adapter        [planned]
        +-- GoreeCloud AI application authorization            [assessment foundation]
        +-- conversation persistence                            [foundation]
        +-- Workspace persistence                               [foundation]
        +-- private attachment staging + trust state            [foundation]
        +-- Wardveil artifact runtime gate                      [source foundation]
        +-- authenticated Wardveil Scan transport               [planned]
        +-- passive text extraction                             [foundation]
        +-- knowledge eligibility                               [observation foundation]
        +-- Privacy Shield decision-input assessment            [source foundation]
        +-- authenticated Privacy Shield enforcement/capability [planned]
        +-- chunking / embeddings / indexing / RAG              [planned]
        +-- Everkeep lifecycle/recovery                         [planned]
        +-- GoreeCloud Search research                          [planned]
        +-- GoreeCloud Mesh integration                         [planned]
        +-- Ollama adapter                                      [foundation]
                 |
                 v
              Ollama
```

Clients do not connect directly to Ollama or ClamAV.

## Attachment trust and extraction

Upload flow:

```text
untrusted bytes
  -> private staging
  -> SHA-256 binding
  -> Wardveil Scan decision contract
  -> evidence validation
  -> post-scan SHA-256 recheck
  -> released OR retained staged
```

`server/artifact-security.mjs` enforces the native trust transition. Unknown, unsupported, stale, expired, malformed, mismatched, non-authoritative, or scanner-unavailable evidence fails closed. Suspicious content is held. Malicious content is blocked and can produce a non-destructive quarantine handoff request that still requires separate executor authority.

A clean malware result is not permission to execute code, load models, run tools, deserialize unsafe content, or publish data.

### Passive text extraction

`POST /api/files/:id/extraction` is a separate post-release gate. It accepts only attachments that are `available`, stored in `released` state, and whose Wardveil decision allows release/context-oriented use.

Before parsing, the released bytes are re-hashed and must still match the accepted attachment digest. Initial media types are `text/plain`, `text/markdown`, `text/x-markdown`, and `application/json`. Fatal UTF-8 decoding, unsupported-control rejection, JSON validation, and `MAX_TEXT_EXTRACTION_BYTES` apply. Extracted text remains private application data bound to source/content SHA-256 digests.

Extraction is not chunking, embedding, indexing, retrieval, RAG eligibility, model-context authorization, Privacy Shield authorization, or external-processing permission.

## Knowledge gate observation and authorization assessment

`GET /api/files/:id/knowledge-eligibility` reports current Wardveil, extraction, Identity/application, Privacy Shield, indexing, retrieval, and model-context gate state without creating or advancing any stage.

`POST /api/files/:id/knowledge-authorization-assessment` additionally accepts bounded authorization inputs for one application-local operation:

- `goreecloud-ai.knowledge.index`
- `goreecloud-ai.knowledge.retrieve`
- `goreecloud-ai.knowledge.model-context`

These are GoreeCloud AI application-local operation identifiers. They are not new central GoreeCloud Identity scopes and are not additions to the canonical Privacy Shield capability registry.

The Identity input must bind an authenticated actor, valid observation/expiry window, exact attachment resource ID, and GoreeCloud AI application permission. Privacy input is structurally aligned to the current Privacy Shield decision contract and checks request/decision binding, resource, operation, requester/acting user, processing zone, destination, permitted operations, obligations, decision expiration, and optional request-retention expiration. A malformed optional request-retention expiration fails closed.

Privacy Shield `DENY` blocks; `REQUIRE_USER_DECISION` remains pending; `ALLOW`/`ALLOW_WITH_CONSTRAINTS` can only become structurally satisfied when checked bindings agree.

Crucially, a structurally satisfied assessment still returns:

- `sourceTrust.productionTrustedInput: false`
- `persistentAuthorizationCreated: false`
- `executionAuthorized: false`
- `eligibleForIndexing: false`
- `eligibleForRetrieval: false`
- `eligibleForModelContext: false`

Authenticated GoreeCloud Identity/Privacy Shield adapters, operation-bound capability/signature verification, durable decision/evidence state, revocation/replay handling, and actual indexing/retrieval/model-context implementation remain absent. A client-supplied JSON object cannot manufacture production authority.

See `docs/KNOWLEDGE-AUTHORIZATION.md`, `docs/WARDVEIL_ARTIFACT_SECURITY.md`, and `docs/ATTACHMENT_LIFECYCLE.md`.

## API foundation

```text
GET    /api/health
GET    /api/ollama/models
POST   /api/ollama/chat

GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/:id
PATCH  /api/conversations/:id
DELETE /api/conversations/:id

GET    /api/workspaces
POST   /api/workspaces
GET    /api/workspaces/:id
PATCH  /api/workspaces/:id
DELETE /api/workspaces/:id

GET    /api/files
POST   /api/files
GET    /api/files/:id
DELETE /api/files/:id
POST   /api/files/:id/extraction
GET    /api/files/:id/extraction
GET    /api/files/:id/knowledge-eligibility
POST   /api/files/:id/knowledge-authorization-assessment
```

The current JSON/local-file adapters are development persistence boundaries, not the final multi-user database design.

## Model roles

GoreeCloud AI presents stable functional roles while keeping individual model implementations replaceable:

| GoreeCloud role | Intended function | Initial candidate family |
| --- | --- | --- |
| GoreeCloud Assistant | General conversation and assistance | Qwen 3.5 |
| GoreeCloud Reasoner | Complex reasoning, architecture, and research | GPT-OSS |
| GoreeCloud Engineer | Infrastructure engineering, coding, and configuration | Qwen3-Coder |
| GoreeCloud Utility | Lightweight and recurring AI processing | Qwen3 |
| GoreeCloud Embeddings | Semantic retrieval and future RAG indexing | Qwen3-Embedding |
| GoreeCloud Vision | Optional specialized visual analysis | Gemma-family candidate |
| GoreeCloud Second Opinion | Optional independent reasoning/validation | DeepSeek-R1-family candidate |

Candidate models are not permanent dependencies.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8787` | Local backend port. |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama address visible to the backend. |
| `GOREECLOUD_AI_API_TOKEN` | unset | Optional development direct-API bearer; not final Identity/application authorization. |
| `GOREECLOUD_AI_DATA_DIR` | `./data` | Local private persistence/staging/released/extraction root. |
| `MAX_BODY_BYTES` | `1000000` | Maximum JSON request body, including authorization assessment input. |
| `MAX_FILE_BYTES` | `26214400` | Maximum attachment size. |
| `MAX_FILE_COUNT` | `1000` | Development attachment-record limit. |
| `MAX_TOTAL_FILE_BYTES` | `1073741824` | Development aggregate attachment limit. |
| `MAX_TEXT_EXTRACTION_BYTES` | `2097152` | Maximum source bytes accepted by passive extraction. |
| `REQUEST_TIMEOUT_MS` | `120000` | Ollama upstream timeout. |

Do not commit `.env`, `data/`, or reusable credentials.

## Operator-initiated model-routing diagnostic

An explicit, development-only `npm run validate:model-routing` command composes the private local policy reader, local-only discovery adapter, and approved-role preflight. It requires an explicit operator opt-in and an absolute path to a private local policy file; see [diagnostic instructions](docs/MODEL_ROUTING_DIAGNOSTIC.md). It calls only local `/api/tags`, never runs inference, does not modify the HTTP API, and always returns `inferenceAuthorized: false` for a selection. No production authorization or live integration claim is implied.

## Local development and validation

```bash
npm install
cp .env.example .env
npm run check
npm run check:server
npm run test:server
npm run build
python3 scripts/test_ai_artifact_security.py
python3 scripts/validate_wardveil_ai_integration.py
```

`npm run check:server` syntax-checks the authorization, eligibility, runtime-validator, and server modules. Native tests cover Wardveil trust/lifecycle, extraction, quotas/deletion, authorization input binding, Privacy Shield outcomes, and proof that knowledge authorization assessment remains non-executable.

### Live application/runtime validation

```bash
GOREECLOUD_AI_URL=http://127.0.0.1:8787 npm run validate:runtime
```

The base validation requires GoreeCloud AI health and Ollama model discovery through the application backend. `VALIDATE_OLLAMA_MODEL='<installed-model-id>'` can exercise one streamed model request. `VALIDATE_REQUIRE_WARDVEIL_SCANNER=true` fails if an environment expected to have an authenticated Wardveil transport reports it unconfigured.

Successful source checks or runtime validation do not establish Wardveil/Privacy Shield/Everkeep/Identity/Mesh production acceptance, recoverability, exact Glaze UI conformance, deployment readiness, or Anchor qualification.

### Approved-model runtime evidence

For a policy-bound exact-model Development check through the existing application path, use `npm run validate:approved-model-runtime` with the explicit opt-in, protected local policy path, functional role and exact preferred model documented in [Approved Local Model Runtime Validation](docs/APPROVED_MODEL_RUNTIME_VALIDATION.md). The command is literal-loopback-only, discards generated text, emits sanitized evidence, and never makes a production/Stable claim.

## Platform-system acceptance

- **Glaze UI:** the current authoritative Official Anchor consumer target is **GLAZE UI V1.6 / 1.6.0**. GoreeCloud AI remains migration/reconciliation-required until exact-revision product-specific conformance evidence exists. Existing 2.x-labeled source is historical migration input and is not current conformance evidence.
- **Wardveil Security:** source trust enforcement exists; deployed authenticated Scan transport and AI consumer production acceptance remain pending.
- **Privacy Shield:** current decision fields/outcomes are structurally consumed, but authenticated runtime enforcement/capability/evidence and AI consumer acceptance remain pending. Supplied JSON cannot create Privacy Shield authority.
- **Everkeep:** attachment/extraction/future knowledge retention, export, backup, restore, recovery, preservation, portability, and succession remain pending application-specific acceptance.
- **GoreeCloud Identity:** Identity establishes authenticated identity/claims while GoreeCloud AI owns application authorization. Current assessment consumes supplied context but authenticated production Identity/session integration and durable multi-user boundaries remain pending.
- **GoreeCloud Mesh:** cross-system capability/evidence coordination remains pending.

## Roadmap

The canonical open feature and capability inventory is [docs/PLANNED-FEATURES.md](docs/PLANNED-FEATURES.md). Implemented capability state is maintained in [docs/IMPLEMENTED-FEATURES.md](docs/IMPLEMENTED-FEATURES.md), and meaningful repository history is recorded in [docs/CHANGELOGS.md](docs/CHANGELOGS.md).

Do not infer completion, deployment, production acceptance or Anchor qualification from roadmap position or source-only validation.

## Visual identity

The canonical branding authority is `GoreeCloud/goreecloud-branding-assets`; see `docs/BRANDING.md`. Local artwork is a synchronized consumer derivative and does not establish capability or release claims.

## License

GNU Affero General Public License v3.0. See `LICENSE`.
