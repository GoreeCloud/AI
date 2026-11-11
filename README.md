# GoreeCloud AI

**Local-first AI with Ollama, Qwen, Gemma and Smart Model.**

GoreeCloud AI is a new, independently written foundation for GoreeCloud's private AI platform. It is not a fork of LibreChat, Open WebUI or AnythingLLM. Its goal is a unified AI workspace while retaining original provenance and independently assessing integrations and licenses.

> **Status: development preview.** This repository contains an Ollama-backed chat API and web interface, deterministic Smart Model routing, persistent local conversations, tests, and deployment scaffolding. It does **not** yet implement the complete planned platform.

## Requirements

- Python 3.11+; Ollama running locally or at an administrator-configured endpoint.
- At least one installed Qwen or Gemma model, such as the model versions supported by your Ollama installation. The platform does not download any model automatically.

## Quick start

1. Install and start [Ollama](https://ollama.com).
2. Download a compatible model with Ollama, e.g. `ollama pull gemma3:4b` or `ollama pull qwen3:8b` (check local RAM and Ollama's available catalog).
3. In a virtual environment, run `python -m pip install -e ".[test]"`.
4. Run `uvicorn goreecloud_ai.app:app --host 127.0.0.1 --port 8765`.
5. Visit `http://127.0.0.1:8765`.

Run `pytest -q` for the API/router tests. The tests use a fake Ollama backend and require no model downloads.

## Docker Compose (self-contained local services)

Run `docker compose up -d --build` to start GoreeCloud AI and Ollama on a private Compose network. Then install a model inside the Ollama service, e.g. `docker compose exec ollama ollama pull gemma3:4b` or `docker compose exec ollama ollama pull qwen3:8b`. Open `http://127.0.0.1:8765`.

The default Docker Compose configuration is intended for local development only: it does not expose Ollama directly, and the UI port is loopback-bound. It uses the official moving `ollama/ollama:latest` container image; review and pin a trusted digest before reproducible or sensitive deployments. CPU-only inference can be slow, and GPU passthrough is deployment-specific. Ollama and Qwen/Gemma model files are downloaded only after the operator explicitly runs the commands.

## Smart Model

Select **Smart Model** for automatic deterministic routing over the models installed in Ollama. Coding requests prefer installed Qwen models with `coder` in the name; reasoning requests prefer Qwen; general conversation prefers Gemma. If the preferred family is unavailable, the router falls back to another installed Qwen/Gemma model. Model selection is transparent in each assistant response. Manual selection is always available. This is a **heuristic baseline**, not proven semantic classification, model benchmarking, automatic capability detection, or multi-agent inference.

## Features in this baseline

- Local Ollama model discovery (`/api/tags`), chat completions (`/api/chat`) and streaming responses.
- Qwen and Gemma Smart Model routing with manual override and safe fallback.
- Persistent SQLite conversation creation/list/detail/delete with automatic first-message titles and two-message exchanges.
- Minimal responsive streaming web client with safe text rendering, a model selector and Ollama connectivity indicator.
- Optional shared API token for `/api/*` endpoints (except health).
- Loopback-bound development server and loopback port in the included Compose example.
- Offline fake-backend API and routing tests.

## API

- `GET /api/health` — shallow service and Ollama health.
- `GET /api/models` — installed model names.
- `GET /api/chats` — list conversations.
- `POST /api/chats` — create conversation (optional `{"title":"..."}`).
- `GET /api/chats/{id}` — conversation and messages.
- `DELETE /api/chats/{id}` — delete conversation.
- `POST /api/chats/{id}/messages` — nonstreaming response to `{"content":"Hello","model":"smart"}`.
- `POST /api/chats/{id}/stream` — same payload, text/event-stream events: `chunk`, `done`, `error`. Successful completed exchanges are saved.

## Local knowledge (keyword-based preview)

The local knowledge API accepts **explicitly submitted text** documents (maximum 50,000 characters), indexes them in SQLite, and searches relevant excerpts by keywords. Use the `use_knowledge` checkbox in the composer to include matching passages in a chat request. The model is instructed to treat excerpts as untrusted evidence and cite their source labels, but no prompt can guarantee compliance. This is *not semantic vector RAG*, does not crawl the web or automatically import personal files, and has no per-user document isolation yet.

- `POST /api/knowledge/documents` with JSON `{"title":"My notes","content":"text"}`.
- `GET /api/knowledge/documents` — list stored document metadata.
- `GET /api/knowledge/search?q=term` — ranked local keyword excerpts.
- `DELETE /api/knowledge/documents/{id}` — permanently delete an indexed document.
- Chat endpoints accept optional `use_knowledge: true`; responses include document source IDs/titles.

## Conversation discovery, export and Smart Model preview

- `POST /api/chats/search` with `{"query":"text"}` searches conversation titles and messages without recording queries in URLs.
- `GET /api/chats/{id}/export` downloads a versioned, portable JSON snapshot of one conversation; protect its plaintext contents.
- `POST /api/smart/route` with `{"content":"Write Python code","model":"smart"}` shows the installed-model decision without generating a reply or saving the prompt.
- The browser interface supports conversation search and working **Export**, **Delete**, and **Knowledge** management controls. The knowledge dialog saves and deletes bounded text documents. Streaming replies have a **Stop** button that aborts the browser request; cancellation may race with upstream completion, so reopen the conversation to inspect what was actually persisted.

## Configuration

Set environment variables (see `.env.example`):

- `GOREEAI_OLLAMA_URL` default `http://127.0.0.1:11434`
- `GOREEAI_DATABASE_PATH` default `./data/ai.sqlite`
- `GOREEAI_API_TOKEN` optional; **required before exposing outside a trusted localhost network**.

The client prompts for an API token if authentication is enabled and stores it in session storage, not in source control. Do not expose this prototype directly on the public internet; see [security](docs/security.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Unified capability catalog](docs/capability-catalog.md)
- [Implemented features](docs/implemented-features.md)
- [Planned features](docs/planned-features.md)
- [Competitive objectives](docs/competitive-objectives.md)
- [Security and deployment](docs/security.md)

## License

Original GoreeCloud AI code is under the [MIT license](LICENSE). Ollama, AI model weights, and future optional integrations retain their own separate licenses, distribution rules, privacy consequences, and notices. This repository does not redistribute third-party application code or model weights.
