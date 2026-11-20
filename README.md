# GoreeCloud AI

**Developer preview — source foundation, not a deployed or certified product**

GoreeCloud AI is an original MIT-licensed hybrid AI workspace and API designed
for integration with GoreeCloud products. It combines an **OpenRouter-first**
model gateway, optional Ollama inference, and explicitly approved tools.
It does not copy or reskin the competing Open WebUI, AnythingLLM or LibreChat apps.

## Included source

| Component | Scope |
| --- | --- |
| FastAPI gateway | Authenticated chat API, OpenRouter Auto, configured Ollama and opt-in transient fallback |
| Image studio | OpenRouter unified Images API with optional reference image for supported editing models |
| Documents | Local SQLite Markdown editor, PDF/DOCX/text extract, MD/DOCX export |
| Agents | AI planning and explicitly approved local read-only document action |
| MCP | Streamable HTTP MCP Python SDK discovery and manually approved operator-allowlisted tool invocation |
| Web | React + TypeScript workspace |
| Linux | Native Qt Quick 6 interface |
| Android | Native Kotlin + Jetpack Compose Material 3 interface |
| Integration | REST/OpenAPI contract for future GoreeCloud Mesh consumers |

**Limits:** Single-owner proof of concept, no Identity integration, hard billing
caps, streaming, RAG, encrypted storage, multi-user permissions, tool sandbox, or
production security approval. App builds, supported browsers, real devices and
remote MCP interoperability require verification; a code commit is not a release.

## Run the API locally

Use Python 3.11 or later.

    cd server
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -e ".[dev]"
    export GOREECLOUD_AI_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
    export OPENROUTER_API_KEY="YOUR_PRIVATE_KEY"
    uvicorn app.main:app --host 127.0.0.1 --port 8000

The key stays on the server, not in browser or mobile sources. For optional local
inference, install Ollama and download a compatible model, then set OLLAMA_MODEL.
The API uses OpenRouter when a key is present; selecting Ollama is explicit.
Fallback from OpenRouter is off unless opted in, and not triggered by payment errors.

    export OLLAMA_MODEL="YOUR_INSTALLED_MODEL"
    export OLLAMA_BASE_URL="http://127.0.0.1:11434"

Run the web client from another terminal:

    cd web
    npm install
    npm run dev

Set GOREECLOUD_AI_CORS_ORIGINS=http://127.0.0.1:5173 on the API for
local dev. Open http://127.0.0.1:5173 and enter the API URL and owner token.
The browser does not persist the owner token to localStorage.

Run server checks: cd server && python -m pytest -q
Build web: cd web && npm run build

Linux and Android build instructions are in their respective READMEs.
Never expose this preview to the public Internet.

## HTTP contract

Each protected call requires Authorization: Bearer YOUR_OWNER_TOKEN.
- GET /api/health — public minimal health status
- GET /api/v1/models — configured model choices
- POST /api/v1/chat — provider routing and selected model reply
- POST /api/v1/images — paid generation/edits with consent flag
- GET/POST /api/v1/documents — list and create documents
- GET/PUT /api/v1/documents/{uuid} — retrieve and edit
- GET /api/v1/documents/{uuid}/export?format=md|docx
- POST /api/v1/documents/extract — PDF, DOCX, Markdown or text ingestion
- POST /api/v1/agents/plan and /api/v1/agents/run
- GET /api/v1/mcp/tools and POST /api/v1/mcp/call
- GET /api/openapi.json and GET /api/docs — developer reference

OpenRouter is a paid external service; model prices and capabilities can change.
Configure privacy controls and limits in your OpenRouter account. No secrets,
private user documents, model weights or third-party applications are stored here.

## Developer governance

- Original code licensed under [MIT](LICENSE); see [third-party notices](THIRD_PARTY_NOTICES.md).
- Integration and threat model: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Remaining engineering priorities: [docs/ROADMAP.md](docs/ROADMAP.md).
- GoreeCloud UI colors and tokens are copied from the existing alpha design-source
  repository with attribution; no unapproved brand specifications are introduced.
- Security claims require separate GoreeShield, Wardveil, Identity, Mesh and UI
  acceptance before any production exposure.
