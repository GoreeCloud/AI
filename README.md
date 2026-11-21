# GoreeCloud AI

**Open-source development preview (MIT), not a deployed or released service.**

GoreeCloud AI is a local-first, hybrid AI workspace with an original
FastAPI gateway, OpenRouter cloud routing (preferred only after explicit
consent), optional Ollama inference, documents, images, source-linked local
retrieval and human-approved tool operations. This is not a source fork of
Open WebUI, AnythingLLM or LibreChat.

## Current source coverage

| Surface | Implemented in source | Still missing |
|---|---|---|
| Shared API | Owner or opt-in scoped signed JWT, OpenRouter/Ollama, SSE/images and deliberate owner-only OpenRouter generation-cost metadata lookup | Verified Identity issuer, invoice-level cost reconciliation, dollar cap, live providers |
| Web | React/TypeScript chat stream/cancel, consent, searchable saved chats, explicit JSON/Markdown export and JSON import, rename, in-memory branching, documents, search/RAG, image-catalog browsing, images, agents, MCP | Cross-browser/visual qualification and native conversation-library UI parity |
| Linux | Native Qt Quick with bounded SSE and redirect-refusing authenticated Qt Network REST, chat cancellation, local saved-conversation list/search/save/open, images, documents, approved MCP and consent | Real desktop/accessibility, signed packages, provider acceptance and native export/import parity |
| Android | Kotlin Compose with pinned GoreeCloud UI Material 3 Expressive, incremental SSE chat/cancel, local saved-conversation list/search/save/open, images/docs/agents/MCP and debug-only emulator HTTP policy | Physical device/emulator networking, signed release, accessibility and native export/import parity |
| Documents | SQLite CRUD/FTS5 with optional SQLCipher; opt-in bounded revisions and approved rollback; upload preflight, isolated parser, export and cited retrieval | Deployed encryption, malware scanning, native revision parity and semantic search |
| Agents & MCP | Plans without automatic execution, read-only approved document action, operator-allowlisted manual Streamable HTTP MCP with bounded JSON, concurrency, timeouts and sanitized outputs | Multi-step autonomous agents, OAuth, external MCP sandbox |
| Privacy | Consent-gated cloud processing, local snapshots and approval receipts, opt-in SQLCipher/FTS and backup, explicitly gated local retention CLI plus optional timer template | Deployment/key custody, hosted scheduler, secure erasure, policy acceptance and five-MIPS qualification |
| Supply chain | Python/npm lockfile component inventories, directly declared Gradle source dependencies and partial installed PySide6 wheel inventory in CI | Resolved native transitive graph, licenses, attestation and signed release |

OpenRouter is an external model provider and may charge per request, token, image
or other unit. The daily request admission limit is **not a money limit**.
Do not use real sensitive data or expose the preview server publicly.

## Local server

Python 3.11+ with an operator-controlled non-public working directory:

    cd server
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[dev]"
    export GOREECLOUD_AI_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
    export OPENROUTER_API_KEY="YOUR_PRIVATE_SERVER_KEY"
    export GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT=20
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Ollama remains optional:

    export OLLAMA_MODEL="YOUR_INSTALLED_MODEL"
    export OLLAMA_BASE_URL="http://127.0.0.1:11434"

**Consent:** Cloud inference requires allow_cloud_processing=true in each
authenticated chat, stream, agent plan or research request. If auto routing
has no cloud consent, a configured Ollama is used; otherwise inference is
refused. Image calls require approve_paid_generation=true. No provider key
is stored in any browser/Linux/Android source.

## Browser

    cd web
    npm ci
    npm run dev

For local development set GOREECLOUD_AI_CORS_ORIGINS=http://127.0.0.1:5173
on the API. Open http://127.0.0.1:5173, enter the server URL and owner token
(managed in memory only). Browser requests to non-loopback HTTP endpoints
are refused. Chat streams are cancellable; opt-in saved chats stay in SQLite.

## Linux / Android

See linux/README.md and android/README.md. Android uses the pinned MIT-licensed
gc-ui source module; it is not a published or verified SDK release. Build
source does not establish real-device, browser, visual or accessibility
acceptance. Neither native client has its own provider/API key.

## Privacy-first API contract

Protected routes require Authorization: Bearer OWNER_TOKEN.

- POST /api/v1/chat — text response; consent is required for cloud.
- POST /api/v1/chat/stream — SSE delta/done/error events, no midstream fallback.
- POST /api/v1/images — explicitly approved paid generation/compatible reference edits (bounded image response, PNG/JPEG/WebP).
- GET /api/v1/images/models — deliberate owner-authenticated model catalog lookup using the server-only OpenRouter API key; no prompt or paid generation request.
- GET /api/v1/usage/openrouter/{generation_id} — owner/admin-capability only,
  deliberate read-only metadata lookup of one OpenRouter generation ID. Returns
  provider-reported model and USD cost; never returns full generation metadata,
  prompts, completions or provider credentials. The ID may appear in successful
  OpenRouter chat/image responses or streaming completion events. Metadata
  lookup requires a configured key with appropriate upstream permission and
  is not independent invoice reconciliation or a hard USD spending limit.
- GET /api/v1/models — configured routes.
- GET /api/v1/quotas and /api/v1/privacy/status — count and preview controls.
- GET /api/v1/privacy/consent-receipts — owner-only bounded, content-free approvals/admission metadata.
- POST /api/v1/privacy/consent-receipts/clear — explicitly approved receipt deletion; does not refund quota.
- POST /api/v1/privacy/purge-expired — explicitly approved retention deletion.
- GET /api/v1/integrations/capabilities — authenticated preview capability metadata.
- GET/POST /api/v1/documents and GET/PUT/DELETE /api/v1/documents/{uuid}.
- PUT /api/v1/documents/{uuid} accepts optional record_revision=true to snapshot
  the displaced saved content only when a change occurs.
- GET /api/v1/documents/{uuid}/revisions and GET /api/v1/documents/{uuid}/revisions/{uuid}
  expose owner-only bounded local history, 20 snapshots maximum.
- POST /api/v1/documents/{uuid}/revisions/{uuid}/restore with approved=true
  atomically restores previous content and preserves the displaced version.
  See docs/DOCUMENT_REVISIONS.md.
- GET /api/v1/search/documents?q=... — owner-only local FTS5 search.
- POST /api/v1/research/answer — retrieved local source references with
  explicit cloud consent if a cloud provider is selected.
- GET/POST /api/v1/conversations, GET/DELETE /api/v1/conversations/{uuid}
  — opt-in local snapshots.
- GET /api/v1/search/conversations?q=... — local full-text message search and
  saved title matching without provider calls.
- PATCH /api/v1/conversations/{uuid} — explicitly rename an existing snapshot.
- GET /api/v1/conversations/{uuid}/export?format=json|md — deliberately
  download a plaintext portable snapshot; exports are never cloud-synced.
- POST /api/v1/conversations/import — validate a v1 JSON export and create
  a **new** snapshot with fresh identifiers and timestamps. See
  [private conversation library](docs/CONVERSATION_LIBRARY.md).
- POST /api/v1/documents/extract — bounded PDF/DOCX/TXT/MD extraction.
- GET /api/v1/documents/{uuid}/export?format=md|docx.
- POST /api/v1/agents/plan and /api/v1/agents/run.
- GET /api/v1/mcp/tools and POST /api/v1/mcp/call. Manual MCP calls require a
  separate approval, operator tool allowlist and bounded 256 KB JSON arguments.
  Session admission allows two concurrent calls per API worker; discovery
  and tool results are bounded, and media/tool-output blobs are not returned
  raw. See docs/ARCHITECTURE.md for source-only limitations.
- GET /api/health is public, /api/docs and /api/openapi.json are developer
  references. Bind the server to loopback only in this preview.

Existing default storage is **plaintext SQLite/FTS5**. New opt-in
GOREECLOUD_AI_DB_MODE=sqlcipher stores the entire local SQLite database and
FTS5 indexes encrypted with the optional locked SQLCipher dependency and an
external 32-byte GOREECLOUD_AI_DB_KEY. The server refuses wrong keys or
plaintext/ciphertext mode mismatch; it never silently rewrites old data.
Stop the API, securely back up the original, and migrate offline into a
**new** path using `python -m app.migrate_sqlcipher`, then configure the new
key/mode/path. The old plaintext source is deliberately **preserved** for
operator-controlled retention and destruction. A second explicit offline
`python -m app.rotate_sqlcipher --source OLD --output NEW` command can rotate
SQLCipher keys into a **new** encrypted database, preserving the old file.
It requires `GOREECLOUD_AI_NEW_DB_KEY` supplied by the secret manager and a
stopped API; no in-place rewrite or automatic key replacement occurs. Backups
of encrypted storage are additionally AES-GCM encrypted and require two separate keys. This is
source-tested, NOT a deployed GoreeShield policy, secure erasure, key escrow,
or off-host recovery. See docs/RECOVERY_AND_IDENTITY.md.
Deletion removes live rows/index entries but is not verified secure erasure of pages
or backups. Before migrating existing data, back up privately and test
recovery. See docs/ARCHITECTURE.md for exact boundaries and risks. Optional
GOREECLOUD_AI_IMPORT_ISOLATION=bwrap requires a trusted Linux Bubblewrap
binary and provides namespaced, network-denied, read-only parser execution;
the default remains process-only for compatibility. A failed requested
sandbox never silently downgrades. See docs/SECURITY_IMPORTS.md for
test evidence and remaining Wardveil protections.

## Verified preview security additions

Optional scoped OIDC/JWT verification uses a pinned, operator-managed RS256
public JWKS file. No fallback to the owner token is allowed while this mode
is active. Optional GOREECLOUD_AI_OIDC_ENFORCE_CAPABILITY_SCOPES=true requires
both the baseline exact-owner scope and a route-specific AI capability scope:
read, write, inference, tools, admin or paid. Cloud inference and paid images
also require cloud capability plus their existing explicit consent/approval.
Owner-token development mode remains unchanged. An unmapped protected route
fails closed in strict mode. These are **source-tested adapter scopes**, not
delegated user access, live GoreeCloud Identity integration, or MFA verification.

Offline AES-256-GCM encrypted SQLite backups can be created and restored by
the operator-only CLI; they do **not** encrypt the running database. An owner
can explicitly approve retention cleanup of expired saved conversations.

An optional OpenRouter provider-key credit-cap preflight prevents uncapped
cloud requests when enabled and fails closed if the provider cannot confirm a
cap. It is **not** a local dollar budget or charged-usage reconciliation.
Details, command examples and key handling:
[Recovery and Identity preview](docs/RECOVERY_AND_IDENTITY.md).

## Source, tests and governance

    cd server && python -m ruff check app tests && python -m pytest -q
    cd web && npm ci && npm run build
    QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python linux/smoke.py
    cd android && gradle :app:assembleDebug

The required tracked docs/ROADMAP.md, docs/FEATURES.md and
docs/OBJECTIVES.md describe current capabilities and unsatisfied release gates.
GitHub Actions checks all four tracks; Python production and web production
dependency advisories are audited in CI. A deterministic two-ecosystem
lockfile component inventory is uploaded as a short-retention CI artifact;
actions are pinned by verified full source commit SHA. The inventories
are not release SBOM attestations or full license/scanner coverage.
See docs/SUPPLY_CHAIN.md, docs/RELEASE_GATES.md and docs/ROADMAP.md
for the remaining production blockers. Keep all changes reviewable via
pull requests with passing CI and protected main settings.

License: MIT for original source (LICENSE). Dependency and pinned
gc-ui adapter attribution: THIRD_PARTY_NOTICES.md and
android/gc-ui-compose/UPSTREAM.md. Do not vendor model weights or credentials.

GoreeCloud MIPS retains distinct responsibilities: GoreeCloud UI design,
GoreeCloud Mesh integration, GoreeCloud Identity authentication,
GoreeShield privacy and Wardveil cybersecurity. None of their production
acceptance gates is implied by this preview.
