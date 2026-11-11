# GoreeCloud AI — Unified Feature and Capability Catalog

**Scope:** GoreeCloud AI product requirements and implementation maturity, November 11, 2026. This document describes the desired combined capabilities of a unified AI platform. It is not a claim that every item is built, tested, integrated, deployed, or supported on every operating system.

**Inference foundation:** Ollama, locally installed Qwen and Gemma models, and GoreeCloud Smart Model routing. Optional providers, specialized models, and integrations require separate installation, consent, licensing, and validation.

## Status terms

- **Source implemented / CI tested:** Function is represented in the merged repository and exercised by automated tests using a fake Ollama backend. Live Qwen/Gemma performance remains unverified.
- **Planned:** Product target; no verified implementation within this repository.
- **Conditional/experimental:** Dependent on platform, model, tools, explicit permissions, or unresolved security assessment. No deployment implied.

## 1. Model foundation and inference

**Source implemented / CI tested:** Ollama model discovery; local chat completions and SSE streaming; installed-model validation; manual model selection; Qwen/Gemma Smart Model family routing; Fast/Balanced/Quality preference profiles derived from model-name size labels; routing explanations; inference-free route preview; local service health check.

**Planned:** Evaluated model benchmarks, context-aware routing, GPU/memory-aware scheduling, model version download UI, quantization-aware policies, model prewarming, resource concurrency budgets, provider-compatible adapters, cloud-provider permissions, reasoning-depth presets, multimodal model capability discovery, cost governance and fallback diagnostics.

## 2. Conversations and chat

**Source implemented / CI tested:** Persistent SQLite conversations; create/list/read/delete; first-message titles; contextual multi-turn requests; streaming Stop control; conversation search; single-conversation JSON export/import; atomic exchanges; optimistic concurrent-write conflict guard; bounded output storage; text-only safe rendering; keyboard message submission.

**Planned:** Temporary chats, conversation branching/forking, queued prompts, richer search, conversation folders, tags, pins, archive, message edit/regenerate, multi-model response comparison, conversation sharing, transcript references, document citation UI, multi-device synchronization and resumable streams.

## 3. Workspaces, projects, and memory

**Planned:** Private and shared workspaces, project instructions and templates, workspace-specific model and tool policies, notes, explicit user memory, memory search/retention, personal settings, team sharing, scoped resource permissions, offline/project exports, isolated memory stores and portable project backups.

## 4. Document intelligence and retrieval

**Source implemented / CI tested:** Explicitly submitted local text documents, document listing/deletion, bounded keyword search/excerpts, opt-in document context in chat, source ID/title metadata. This is **not semantic RAG**.

**Planned:** Local text/Markdown/CSV/JSON file ingestion UX, PDF/Word extraction, OCR, document chunking, local embeddings, vector search, hybrid retrieval, BM25, reranking, source-grounded citations, retrieval evaluation, document sync with consent, metadata filtering, full-document context, classification/extraction and multi-document synthesis.

## 5. Agents and workflows

**Planned:** Custom assistants, agent templates, agent-scoped tools/knowledge, reusable skills, MCP tool discovery, planning, subagents, delegation, multi-agent coordination, visual flow builder, task checkpoints, human approval, agent execution budgets, cancellation, tool audit trails and sandboxed environments.

**Conditional/experimental:** Browser/computer-use agents, terminal actions, application automation and privileged tools require Wardveil review, isolation, explicit permissions and observable rollback.

## 6. Tool and integration platform

**Planned:** MCP servers, OpenAPI/REST tools, authenticated connector management, per-user credentials, secret isolation, scope-limited tool permissions, OAuth integrations, webhook actions, external database connectors, Git/Drive/email/calendar/task services, auditable tool invocation and GoreeCloud Mesh protocols.

## 7. Web research and browsing

**Planned:** Search providers, live-source reading, structured webpage extraction, source provenance and citations, research plans, multimodal search, site-to-knowledge ingestion, source freshness and robots/consent policies.

**Conditional/experimental:** Authenticated scraping and browser automation require explicit opt-in and network/credential isolation.

## 8. Software development and code tools

**Planned:** Code explanation/review, repository context, debugging, test generation, editable artifacts, syntax-highlighting, diagram rendering, Docker or sandbox interpreters, file editing, preview servers and safe terminal integration. Local model outputs remain untrusted.

## 9. Image, audio, video, and meetings

**Planned:** Image understanding, screenshot QA, OCR, image generation/editing through appropriate model/provider, speech-to-text, text-to-speech, live voice chat, transcription, meeting summaries, speaker labeling, video frame extraction and source-grounded media Q&A.

**Conditional/experimental:** Voice cloning, desktop screen capture, meeting recordings and video integrations require consent, supported operating systems, retention controls, and purpose-specific approval.

## 10. Productivity, notes, calendar, tasks and collaboration

**Planned:** AI notes, task lists, recurring reminders, shared workspaces, calendar integrations, event/attendee support, project planning, communication channels, group chat with AI assistants, notifications, agent/task activity and protected sharing.

## 11. Automation and scheduling

**Planned:** Cron/interval schedules, event/webhook triggers, durable jobs, run history, retries, idempotency, cancellation, task queue visibility, notifications, monitoring, and agent-run budgeting. Automation is never claimed active without a running scheduler and verified configuration.

## 12. APIs, embedding, and extensions

**Source implemented / CI tested:** Local chat/model/conversation/document endpoints with optional shared API token and versioned JSON export/import.

**Planned:** Versioned public API contracts, SDKs, embeddable chat widgets, developer webhooks, role-scoped API credentials, extension catalogs and production-grade request limits.

## 13. Identity and administration

**Source implemented / CI tested:** Optional shared API token for the local single-user preview. This is not per-user authentication.

**Planned:** GoreeCloud Identity SSO/MFA/passkeys, group permissions, user provisioning, resource ACLs, administrative settings, session management, access logs, API-key scopes, moderation and audit functions.

## 14. GoreeShield privacy

**Source implemented / CI tested:** Local storage by default, deliberate knowledge opt-in, local model routing, no model-weight downloads by the server, explicit import/export, plaintext-at-rest warnings.

**Planned:** Consent/retention enforcement, privacy dashboards, privacy-preserving logs, deletion/export verification, data minimization, remote-provider data sharing controls, cross-workspace isolation and personal-data governance. GoreeShield governs privacy, **not** cybersecurity.

## 15. Wardveil cybersecurity

**Source implemented / CI tested:** Local-only deployment guidance, safe DOM text rendering, bounded text inputs, conversation write integrity checks, stream failure handling and API token check.

**Planned:** Threat modeling, production IAM integration, abuse/rate limiting, CSRF/session hardening, prompt-injection resilience, network egress allowlists, secret vault integration, audit trails, malware/file validation, tool sandboxing, vulnerability scans and incident response. Wardveil governs cybersecurity and must enforce applicable GoreeShield privacy policies.

## 16. GoreeCloud Mesh

**Planned:** Verified service discovery, typed contracts, event routing, workflow coordination, synchronization and cross-product data exchange with explicit identity/privacy/security enforcement. Mere imports or naming do not establish Mesh integration.

## 17. GoreeCloud UI

**Source implemented / CI tested:** Functional dark responsive browser interface, accessible labels, conversation controls and knowledge dialog. This does not establish full GoreeCloud UI compliance.

**Planned:** Verified centralized design tokens, theme system, cross-platform components, accessibility audits, rich Markdown/code rendering, onboarding, premium visual QA, mobile/desktop layouts, high-contrast/reduced-motion states, keyboard navigation and genuine native-client experiences.

## 18. Analytics, observability and evaluation

**Planned:** Token usage, latency/throughput measurements, real-model benchmarking, response quality evaluations, routing statistics, operational dashboards, metrics/logging/tracing, error analysis and privacy-limited diagnostics.

## 19. Packaging, deployment and durability

**Source implemented / CI tested:** Python packaging, container templates, local Docker Compose wiring, CI Python test matrix and syntax checks. Actual container execution and installed-model inference require separate real-host testing.

**Planned:** Verified Linux/Windows desktop packaging, Android/iOS native or individually qualified clients, backups/restores, migrations, signed releases, vulnerability/SBOM checks, health monitoring, GPU profiles, data encryption choices, upgrade/rollback and production readiness.

## 20. Security and acceptance constraints

GoreeCloud AI is a hobby-owned, self-hosted, privacy-first product. Build third-party features through compatible licensed adapters or independently written code. Do not paste third-party source code without provenance/license review. Model weights and Ollama have independent obligations.

Always distinguish: vision → planned → implemented source → CI tested → real-runtime tested → released → deployed. The first four GoreeCloud pillars remain distinct, with Identity included in the mandatory integrated systems.

## Evidence and next milestones

See [Implemented Features](implemented-features.md), [Planned Features](planned-features.md), [Architecture](architecture.md), [Security](security.md), [Smart Model](smart-model.md) and [Conversation Portability](conversation-portability.md).

Priority engineering milestones: (1) real-model/local-host tests and recovery, (2) GoreeCloud Identity/GoreeShield/Wardveil integration gates, (3) evaluated local semantic RAG, (4) scoped workspaces and agent tool permissions, (5) native clients and production acceptance checks.
