# GoreeCloud AI — Implemented Features

**Scope:** Features represented in the initial source baseline; runtime availability requires Ollama and installed models. Automated fake-backend tests validate selected paths, not real model quality or production deployment.

1. FastAPI HTTP application and bundled browser UI.
2. Ollama model discovery via official `GET /api/tags`.
3. Ollama non-streaming completions and NDJSON-to-SSE streaming via official `POST /api/chat`.
4. Smart Model deterministic keyword/family routing for installed Qwen/Gemma; explainable reason.
5. Manual model selection with installed-model validation.
6. Local SQLite chat history: create, list, retrieve, delete; first-message conversation titles.
7. Persist complete user/assistant exchanges after successful upstream response, including completed streams only.
8. Bounded message length and retained conversation-context window.
9. Optional shared API token; local-only listener instructions.
10. Service status indicating Ollama availability.
11. Responsive, keyboard-accessible basic chat client using safe DOM text.
12. Unit/API tests with fake Ollama; Python compile check in CI.
13. Dockerfile/Compose templates with loopback-published port.
14. MIT license for original source; architecture, feature and security documentation.

**Not yet verified:** live Qwen/Gemma inference, GPU performance, installed Docker image, CI success, external deployments, complete security gates, and fully native application packaging. Update this document only when tested evidence exists.
