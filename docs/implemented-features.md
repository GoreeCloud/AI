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

15. Opt-in local knowledge document ingestion, listing, keyword excerpt search, deletion, and chat grounding; not semantic RAG.
16. Conversation title/message substring search and per-conversation versioned JSON export.
17. Smart Model route-preview API without inference or chat persistence.
18. Web UI knowledge-document create/list/delete dialog and conversation deletion controls.
19. Web UI streaming Stop button with abort behavior and partial-stream failure regression coverage.

**Verified CI evidence:** [GitHub Actions run #3](https://github.com/GoreeCloud/AI/actions/runs/42931187503), [knowledge run](https://github.com/GoreeCloud/AI/actions/runs/42931906115), [conversation run](https://github.com/GoreeCloud/AI/actions/runs/42932461631), and [UI-controls run](https://github.com/GoreeCloud/AI/actions/runs/42933029174) passed both Python 3.12/3.13 test jobs. This establishes only the selected automated checks.

**Not yet verified:** live Qwen/Gemma inference, GPU performance, installed Docker image, external deployments, complete security gates, backup/restore operation, and native application packaging. Update this document only with evidence.
