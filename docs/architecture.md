# GoreeCloud AI — Architecture

**Status:** initial implementation, development preview, November 10, 2026.

The first implementation uses a Python FastAPI application, SQLite, static browser UI, and the Ollama HTTP API. The Compose template includes a separate Ollama service on the private Compose network. No external SaaS or model download is performed by the service. Model requests are directed to the configured Ollama origin only.

```text
Browser (HTML/CSS/JS, same origin)
    │
    ├── Chat and model API (FastAPI)
    │       ├── Smart Model router (installed-model heuristic)
    │       ├── Local SQLite (chats and messages)
    │       └── Ollama adapter (admin-configured URL)
    │               └── Ollama → installed Qwen/Gemma models
    └── Minimal application status
```

Smart Model is currently an interpretable, deterministic routing policy over installed Qwen/Gemma names. It is not a semantic classifier or benchmark-aware scheduler. User-requested explicit model names are accepted only if Ollama reports them as installed; the manual override can use models outside Qwen/Gemma if deliberately installed and chosen. Automatic routing is restricted to Qwen and Gemma.

**MIPS integration contracts (future)**: GoreeCloud UI for centrally verified tokens and components; Mesh for service integration and events; Identity for users and resource authorization; GoreeShield for privacy policies and retention; Wardveil for cyber defense and sandbox policy. These interfaces have not yet been implemented and must not be presented as operating security controls.

Knowledge documents use the same SQLite database but separate tables. Retrieval uses bounded, English-oriented keyword matching and snippets; it is not semantic vector retrieval. Only explicitly submitted text is ingested, and only opted-in conversations receive excerpts as untrusted context.

Data is stored locally under the configured SQLite path. Conversation exchanges are inserted transactionally once Ollama succeeds. Ollama runtime/model state, resumable streaming, multi-user isolation, workflows, RAG, and agents are future milestones. The first stream implementation translates Ollama NDJSON into SSE events and persists only completed exchanges.

The web application is a web deliverable, not a native Linux/Windows/macOS/Android/iOS app. Native clients require separately verified targets and packaging.
