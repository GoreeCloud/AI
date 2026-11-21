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
| Shared API | Owner token or optional offline-JWKS scoped signed-token adapter, OpenRouter/Ollama, streaming, SSE and images | Verified GoreeCloud Identity issuer, dollar-cost reconciliation, live providers |
| Web | React/TypeScript chat stream/cancel, consent, saved local chats, documents, search/RAG, image-catalog browsing, images, agents, MCP | Cross-browser/visual qualification |
| Linux | Native Qt Quick chat, images, Markdown documents, agent plans, MCP, consent | Native stream UI, signed packages and runtime acceptance |
| Android | Kotlin Compose, pinned GoreeCloud UI Material3 Expressive adapter, chat, images, docs, agents, MCP | Device verification, native streaming and file pickers |
| Documents | SQLite CRUD, bounded Linux import subprocess and optional network-denied Bubblewrap document sandbox, export, FTS5 retrieval and source IDs | Production-qualified sandbox, encryption, semantic embeddings |
| Agents & MCP | Plans without automatic execution, read-only approved document action, operator allowlisted manual Streamable HTTP MCP | Multi-step autonomous agents, OAuth, worker sandbox |
| Privacy | Cloud opt-in, metadata-only cloud-admission receipts, owner-controlled receipt clearing, local snapshots, count quota, retention purge, encrypted offline backup | Live DB encryption and complete GoreeShield/Identity/Wardveil/Mesh enforcement |

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
- GET /api/v1/models — configured routes.
- GET /api/v1/quotas and /api/v1/privacy/status — count and preview controls.
- GET /api/v1/privacy/consent-receipts — owner-only bounded, content-free approvals/admission metadata.
- POST /api/v1/privacy/consent-receipts/clear — explicitly approved receipt deletion; does not refund quota.
- POST /api/v1/privacy/purge-expired — explicitly approved retention deletion.
- GET /api/v1/integrations/capabilities — authenticated preview capability metadata.
- GET/POST /api/v1/documents and GET/PUT/DELETE /api/v1/documents/{uuid}.
- GET /api/v1/search/documents?q=... — owner-only local FTS5 search.
- POST /api/v1/research/answer — retrieved local source references with
  explicit cloud consent if a cloud provider is selected.
- GET/POST /api/v1/conversations, GET/DELETE /api/v1/conversations/{uuid}
  — opt-in local snapshots.
- POST /api/v1/documents/extract — bounded PDF/DOCX/TXT/MD extraction.
- GET /api/v1/documents/{uuid}/export?format=md|docx.
- POST /api/v1/agents/plan and /api/v1/agents/run.
- GET /api/v1/mcp/tools and POST /api/v1/mcp/call.
- GET /api/health is public, /api/docs and /api/openapi.json are developer
  references. Bind the server to loopback only in this preview.

SQLite files, FTS5 content and saved snapshots are **unencrypted**. Deletion
removes live rows/index entries but is not verified secure erasure of pages
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
is active. The integration with a real GoreeCloud Identity issuer is unverified.

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
