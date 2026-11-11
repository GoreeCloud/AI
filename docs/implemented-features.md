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

**Validation distinction:** Prior GitHub CI unit checks passed; live Qwen/Gemma inference, GPU performance, running container image, external deployments, complete security gates, and fully native application packaging remain unverified. Update this document only when tested evidence exists.

15. Opt-in local knowledge document ingestion, listing, keyword excerpt search, deletion, and chat grounding; not semantic RAG.
16. Conversation title/message substring search and per-conversation versioned JSON export.
17. Smart Model route-preview API without inference or chat persistence.
18. Web UI knowledge-document create/list/delete dialog and conversation deletion controls.
19. Web UI streaming Stop button with abort behavior and partial-stream failure regression coverage.

20. Optimistic SQLite conversation write-conflict detection and explicit missing-chat rejection.
21. Bounded generated response storage, including SSE failure handling; whitespace-only search rejection.

22. Bounded version-1 JSON conversation import with regenerated IDs, complete-message-pair validation and atomic SQLite insertion; browser Import control.
