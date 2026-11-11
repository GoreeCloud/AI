# GoreeCloud AI — Unified Features and Capabilities

**Classification:** Product specification and roadmap, not a claim that all features exist.
**Foundation:** Ollama for locally hosted inference; Qwen and Gemma model families; GoreeCloud Smart Model for selection and routing.
**Reference influences:** LibreChat, Open WebUI and AnythingLLM capability patterns. This is an original GoreeCloud project, not a codebase merger or upstream fork.
**Authority:** This document defines the desired product scope. [Implemented Features](implemented-features.md) records source-evidenced functionality. GitHub source, CI and runtime tests determine implementation and operational truth.

## Status legend

- **Baseline:** implemented source and passing CI tests in this repository; real Ollama/model runtime and deployment still require independent validation.
- **Planned:** specified target capability; not yet implemented or verified.
- **Conditional:** requires particular AI models, external integration, authorization, platform support or third-party license review. Conditional features are also planned unless explicitly marked baseline.

## Unified capability domains

| Domain | Intended features and functions | Status |
| --- | --- | --- |
| 1. Ollama inference | Local engine connectivity, installed Qwen/Gemma discovery, streaming chat, manual selection, versioned model management, resource-aware model loading, CPU/GPU acceleration, remote compatible endpoints | Baseline API and web chat; runtime/resource management planned |
| 2. Smart Model | Automatic task-aware routing, manual override, inspectable decisions, fallback, latency/cost/privacy/resource policies, reasoning depth, quality evaluation, model ensembles and routing profiles | Baseline deterministic Qwen/Gemma heuristic and route preview; advanced policies planned |
| 3. Conversations | Persistent multi-turn chat, editable history, streaming, search, export, deletion, branching/forking, tags, folders, message feedback, regeneration, queued prompts, temporary chats | Baseline create/list/read/delete, history, text search, JSON export and SSE; rest planned |
| 4. Workspaces and projects | Private/shared workspaces, project instructions, dedicated models/tools, templates, project folders, persistent resources, scoped sharing, project import/export | Planned |
| 5. Memory and personalization | Short/long-term memory, searchable explicit user memories, scoped memory, retention/deletion, preference profiles, context summarization and compaction | Planned; ordinary stored conversation context is baseline, not autonomous long-term memory |
| 6. Knowledge documents and RAG | Text and file ingestion, OCR, parsing, source references, chunking, embeddings, keyword/vector/hybrid search, reranking, document Q&A, comparison, reindexing, source-grounded chat | Baseline explicit text ingest, keyword excerpts, opt-in source context and document management; semantic RAG/OCR planned |
| 7. Agents | Custom assistants, skills, task planning, agent memory, tool calling, subagents, delegation, execution budgets, confirmations, run audit and cancellation | Planned |
| 8. Workflow designer | No-code flow editor, conditional steps, parallel branches, API steps, file transforms, retries, run history, validation and reusable flow templates | Planned |
| 9. Tools and MCP | Local/remote MCP, OpenAPI tools, HTTP integrations, Python/JavaScript skills, per-tool grants, OAuth adapters, safe tool discovery and lifecycle | Planned; conditional on separately reviewed providers |
| 10. Web research | Internet search, URL extraction, source ranking and citation, research synthesis, authenticated browser access, allowlisted web scraping and site-to-knowledge ingestion | Planned; external access conditional |
| 11. Programming and artifacts | Code generation, explanation, review, testing, repository analysis, sandbox execution, terminal tools, application previews, HTML/SVG/React/Mermaid artifacts | Planned; executable tools require Wardveil policy and authorization |
| 12. Images and vision | Image Q&A, screenshot analysis, OCR, text-to-image, image editing, multimodal conversations and export | Planned; model/provider dependent |
| 13. Speech, audio and video | Transcription, TTS, voice chat, speech controls, audio import, real-time voice, video transcription, frame extraction and media Q&A | Planned; model/runtime dependent |
| 14. Meeting assistant | Recording with consent, transcription, speaker diarization, summaries, action extraction, timestamp navigation, meeting history and export | Planned |
| 15. Notes and writing | Rich notes, Markdown, AI-assisted rewriting, summaries, note sharing, chat context, folders and note-to-knowledge/task workflows | Planned |
| 16. Calendar | Event management, recurring dates, attendees, reminders, multi-calendar sync, AI calendar tools and automation schedule visibility | Planned; authorized connector required |
| 17. Task management | Priorities, due dates, statuses, assignments, AI breakdown, reminders and task-service integration | Planned |
| 18. Automation | Scheduled prompts, recurring agent jobs, event/webhook triggers, work queues, logs, retries, notifications, cancellation and approvals | Planned |
| 19. Collaboration | User/group channels, shared conversations, threads, mentions, shared agents/prompts, granular permissions and resource access | Planned; Identity prerequisite |
| 20. APIs and embedded assistants | Stable REST endpoints, agent and knowledge APIs, audited auth, external widgets, domain restrictions, usage limits and embedding | Baseline limited single-user chat, knowledge and Smart Model endpoints; public widgets planned |
| 21. GoreeCloud Identity | SSO, OIDC, LDAP where appropriate, sessions, role-based access, workspace/document authorization, credential management and audit | Planned; existing shared API token is NOT user identity or RBAC |
| 22. GoreeShield privacy | Local-only processing policies, consent, minimization, retention, privacy-aware model routing, sharing controls, portable exports and user ownership | Baseline locally stored chats/knowledge and explicit RAG opt-in; policy enforcement planned |
| 23. Wardveil cybersecurity | Threat assessment, dependency review, sandboxing, injection-resistant boundaries, rate limits, service isolation, secrets, monitoring and incident response | Baseline input limits, minimal API auth and local binding; platform-enforced protection planned |
| 24. Administration and analytics | Account/model/agent administration, token use, latency/resource metrics, model A/B evaluation, trace logs, diagnostics and dashboards | Baseline basic health endpoint; expanded admin and analytics planned |
| 25. GoreeCloud UI | Central verified design tokens, accessible responsive UI, model chooser, keyboard controls, loading/empty/error/offline states and customizable layouts | Baseline responsive browser interface and usable controls; shared design-system integration planned |
| 26. Infrastructure and delivery | Python and Docker self-hosting, persistent storage, private network, automated tests, backup/restore, migrations, monitoring, releases and separately tested native clients | Baseline project packaging, Docker/Compose and CI; actual container installation/native clients/backup restore planned |

## Current first-party baseline

The source presently includes:

- Ollama HTTP model discovery, nonstreaming completions and an SSE streaming adapter.
- Qwen/Gemma keyword-based Smart Model routing, manual override, explainable reason and inference-free preview.
- SQLite conversations, bounded context, search, export, deletion and first-message auto-title.
- Opt-in local text knowledge documents, bounded keyword retrieval and source metadata.
- A browser client with model selection, streaming, stop, conversation export/delete, and knowledge document create/list/delete.
- An optional shared API token, loopback-first configuration, Python tests, GitHub Actions, Dockerfile and Compose example.

**Operational qualification:** CI uses a fake Ollama adapter and does not prove a real Qwen/Gemma model was run. No production deployment, fully native platform build, genuine per-user authorization or comprehensive security audit has been performed.

## Architectural obligations

GoreeCloud AI remains a separate application integrated through the Mandatory Integrated Platform Systems:

- **GoreeCloud UI:** central interface specification and components.
- **GoreeCloud Mesh:** integration, events and service contracts.
- **GoreeCloud Identity:** authentication and authorization.
- **GoreeShield:** privacy, user control, consent and retention.
- **Wardveil:** cybersecurity, threat prevention and incident response.

No role is interchangeable with another. Proposed connections are not implemented controls.

## Delivery and acceptance

Every planned feature must have source implementation, functional and security tests proportionate to risk, documentation with honest status, and verification of its intended platform. Model/provider integrations require provenance and licensing review. Privileged tools, public access, external exports and production deployments require additional explicit gates.

See [Planned Features](planned-features.md), [Security](security.md), [Architecture](architecture.md), [Implemented Features](implemented-features.md), and [Competitive Objectives](competitive-objectives.md).
