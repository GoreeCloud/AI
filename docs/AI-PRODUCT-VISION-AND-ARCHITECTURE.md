# GoreeCloud AI — Planned Features, Capabilities, Architecture, and Third-Party Development Resources

**Product:** GoreeCloud AI  
**Application type:** First-party artificial intelligence platform  
**Development model:** Original GoreeCloud-owned software, not an AnythingLLM or Open WebUI fork  
**Deployment strategy:** Local-first, self-hosted, private by default  
**Primary replaceable local runtime:** [Ollama](https://ollama.com/)  
**Design system:** Glaze — GoreeCloud Design & Experience System (formerly Glaze UI)  
**First-party research provider:** GoreeCloud Search  
**Classification:** Owner-defined product vision, target architecture, candidate dependencies, and phased plan  
**Status:** Planned and phased implementation; **not** a current-feature, approval, procurement, integration, runtime, or production-acceptance claim.

This development-planning annex preserves the owner-defined detailed capability vision. The live source and provider state control implemented functionality; `docs/IMPLEMENTED-FEATURES.md` controls verified source-feature records, `docs/PLANNED-FEATURES.md` controls open feature dispositions, `docs/SPECIFICATIONS.md` controls repository-coupled contracts, and GoreeCloud Tasks Management controls active obligations. Candidate suppliers and architectures below are not selected, licensed, funded, installed, approved, connected, or accepted merely by appearing in this document.

## 1. Product overview and objectives

GoreeCloud AI will be a comprehensive, modular and self-hosted first-party AI platform unifying and extending concepts offered by AnythingLLM, Open WebUI and standalone AI utilities without repackaging or forking those applications.

**Product objectives:** unified AI interface; private local inference; optional approved external providers; GoreeCloud ownership of conversations, knowledge, permissions, artifacts and contracts; functional replacement of transitional AI interfaces only after evidence-backed parity; advanced RAG; governed agents and automation; native conversational image creation/editing; first-party ecosystem integration; future multimodal operation; data portability; desktop/tablet/mobile responsive delivery; supported offline/local-only usage; open-source/self-hosted dependencies where practical; no mandatory proprietary cloud control plane or vendor lock-in.

## 2. Conversational AI

**Planned interaction:** real-time streaming and accessible status indicators; persistent and temporary conversations; independent sessions; creation, rename, full-history search, archive, delete, folders, tags and pins; editable user messages, regenerate/continue, retry, partial results, branching, alternative answers and model comparisons; automatic titles and suggested follow-ups; compatible model changes and configurable instructions; Markdown, tables, mathematics, syntax-highlighted code; copy/export/governed sharing; files, documents, images and approved media attachments; summaries/context budgeting, user-controlled context and retention; multilingual text; explicit generation/retrieval/research/tool states; cancellation, deadlines and retries; accessible keyboard/touch navigation and responsive layouts.

**Advanced extensions:** governed contextual memory; reusable templates; conversation-to-document workflows; voice chat; permission-scoped agent participation. Some capabilities may already have Development-source foundations, but production readiness is a separate evidence gate.

## 3. Model management and inference

**Target:** a provider-independent **Model Provider Gateway** that separates inference from the application interface.

**Planned:** local model discovery/selection; streamed inference; capability and metadata detection; availability/health; logical role mapping; per-model instructions, parameters and context windows; tool and vision capability checks; timeout/cancellation; usage accounting; local-only mode; administrator-controlled availability; policy/privacy-bound model routing and optional approved fallback.

**User-facing logical roles:** GoreeCloud Assistant (general work); GoreeCloud Reasoner (analysis and mathematics); GoreeCloud Engineer (code and technical work); GoreeCloud Utility (fast extraction/classification); GoreeCloud Embeddings (RAG vectors); GoreeCloud Vision (visual input); GoreeCloud Creative (creative text/multimodal). These are product identities, **not hard-coded model names**. An existing Development 13-function routing prototype is separate from this seven-label UX taxonomy; reconcile mappings before accepting any contract change.

**Runtime candidates:** [Ollama](https://ollama.com/) (initial replaceable runtime); [llama.cpp](https://github.com/ggml-org/llama.cpp) (CPU/GPU, quantized); [vLLM](https://github.com/vllm-project/vllm) (throughput); [LocalAI](https://localai.io/) (self-hosted multimodal/API compatibility); [Transformers](https://github.com/huggingface/transformers) (specialized inference).

**Model sources:** [Hugging Face model hub](https://huggingface.co/models) and Ollama's model library. **Optional external adapters:** OpenAI, Anthropic, Google Gemini, Mistral and other approved OpenAI-compatible APIs. Credentials must remain server-side; Privacy Shield and policy must approve external processing. No external provider is required.

## 4. Workspaces, projects and knowledge organization

**Planned:** multiple Workspaces; per-Workspace instructions, models/roles, conversations, attachments, file libraries, persistent knowledge collections, retrieval settings, agent tools/permissions, research preferences, templates, import/export and retention; authorized cross-Workspace search; multi-user shared Workspaces only after verified resource permissions; activity and operational state.

**Scale requirement:** avoid arbitrary third-party file-count limitations; scale with measured storage, indexing, authorization and performance constraints.

## 5. Document processing and knowledge intelligence

**Planned intake and processing:** upload/import text, Markdown, JSON, PDF, approved Office formats and collections; extract text and metadata, scanned OCR, title/source/version lineage; reject malformed/unsupported inputs; normalization/chunking; embeddings/indexing; within-document and collection search; summaries, comparisons and QA; citations; permission-aware retrieval; reindex on change; deduplication/digest integrity; removal/index cleanup; export/recovery; managed background jobs.

**Parser candidates:** [Docling](https://github.com/docling-project/docling) (recommended structured parsing); [Apache Tika](https://tika.apache.org/); [Tesseract](https://github.com/tesseract-ocr/tesseract); [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR); [PyMuPDF](https://github.com/pymupdf/PyMuPDF) (license review required); [Unstructured](https://github.com/Unstructured-IO/unstructured).

**Mandatory sequencing:** private staging → authenticated Wardveil security release and digest binding → application authorization and Privacy Shield/Policy clearance → bounded sandboxed parser adapter → downstream indexing/use. A clean scan does not authorize active content, code execution or model loading.

## 6. Native retrieval-augmented generation (RAG)

**Planned GoreeCloud-owned retrieval:** persistent vectors; keyword/semantic/hybrid search; Workspace and resource-permission filtering; metadata filters; tunable chunking and embeddings; reranking and scores; context-window budgeting and eligible full-document mode; source-aware generation/citations; multi-document synthesis; retrieval quality tests; versioned embeddings, rebuild/migration, deletion/retention, backup and recovery validation.

**Recommended first stack:** [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) + Ollama local embeddings, subject to performance and architectural approval. **Alternatives:** [Qdrant](https://qdrant.tech/), [Chroma](https://www.trychroma.com/), [Milvus](https://milvus.io/), [sentence-transformers](https://www.sbert.net/), [FastEmbed](https://github.com/qdrant/fastembed).

Prefer a single PostgreSQL-backed operational footprint until measured retrieval/scale requirements justify specialized vectors.

## 7. Research and Internet information

**Planned:** live web discovery; technical/security/software-release documentation; news/current events; academic/scientific/government/product/community research; webpage extraction/summaries; independent source collection and comparison; citations; publication/retrieval date awareness; contradictory-evidence checks; authorized local-source synthesis; reports, saved research collections, agent research and future periodic information monitoring.

**Ownership boundary:** GoreeCloud Search owns external search-provider coordination behind an approved first-party API. GoreeCloud AI owns conversational research, synthesis, citations and UX. SearXNG, if retained, is transitional infrastructure **behind GoreeCloud Search**, not a permanent direct AI dependency.

## 8. AI agents and tool execution

**Planned:** configurable agents with explicit instructions, approved models, authorized knowledge, function calls, custom tools/skills, APIs and MCP; bounded multi-step plans and task tracking; execution history/logs; research, document, coding, file-processing and infrastructure-assistance agents; cancellation/deadlines; human approvals for sensitive effects; strict permission boundaries and fail-closed uncertainty.

**Advanced candidates:** parallel and multi-agent delegation/collaboration; dependency and shared-resource scheduling; conditional execution; bounded recovery/retry; evaluations/benchmarks; long-running jobs and reusable profiles.

**References/candidates:** [MCP](https://modelcontextprotocol.io/) and [SDKs](https://github.com/modelcontextprotocol); [LangGraph](https://github.com/langchain-ai/langgraph); [Haystack](https://github.com/deepset-ai/haystack); [Playwright](https://playwright.dev/); isolated rootless containers.

**Authority:** GoreeCloud AI Capability Broker and approved platform systems own permissions, approval decisions and execution boundaries. Agent model output and third-party orchestration frameworks do not create authority.

## 9. Workflow automation

**Planned:** scheduled and recurring prompts (daily/weekly/monthly), task queues, recurring research, document summaries, periodic source checks, automated reports, agent tasks, status/history, deadlines, retries, cancellation, usage/resource budgets, permitted notifications and administrator oversight.

**Advanced:** events and webhooks, conditional branches, multi-stage pipelines, approvals, visual editing, dependency graphs and multi-agent workflows.

**Candidates:** [pg-boss](https://github.com/timgit/pg-boss) (initial PostgreSQL-backed queue candidate); [BullMQ](https://bullmq.io/) + Redis (distributed alternative); [Temporal](https://temporal.io/) (complex durable orchestration); [n8n](https://n8n.io/) (reference/integration subject to licensing/deployment review). The permanent task/workflow model remains first-party.

## 10. Developer and coding assistance

**Planned:** code generation, explanation, debugging, refactoring, testing, configurations/scripts, documentation, repository QA and search, dependency review, PR/issue/commit summaries, logs, architecture, bounded authorized commands and sandboxed execution.

**First-party integrations:** GoreeCloud Code (repository context/operations); Terminal (authorized shell); Documents (document artifacts); Search (current references); Wardveil and Policy (safety constraints).

**Candidates:** [Monaco](https://microsoft.github.io/monaco-editor/), [CodeMirror](https://codemirror.net/), [Shiki](https://shiki.style/), [Tree-sitter](https://tree-sitter.github.io/tree-sitter/), [Playwright](https://playwright.dev/), [Vitest](https://vitest.dev/), [Pytest](https://pytest.org/).

**Security invariant:** repository data, generated code, prompts and tool responses remain untrusted. Read capability never implies write/execution authority.

## 11. Native conversational image generation and editing

**Text-to-image:** natural-language prompts and prompt assistance; candidate variants, dimensions/resolution/quality, reproducible seeds, approved checkpoints, reusable styles and presets; illustration, photorealism, concepts/mockups, backgrounds/textures; user image library and reuse.

**Editing:** image-to-image, inpainting/outpainting, backgrounds, object remove/add, upscale, restore, style transfer, reference generation, masks, selective regions and variants.

**Advanced controls:** LoRA; samplers/guidance/negative prompts; ControlNet, pose/depth/edge/sketch conditioning; versioned graphs/presets; batch generation; generation metadata; cancellable asynchronous GPU jobs and resource monitoring.

**Primary candidate:** [ComfyUI](https://github.com/comfy-org/ComfyUI). **Additional candidates:** [InvokeAI](https://github.com/invoke-ai/InvokeAI); [AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui); [Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge); [SwarmUI](https://github.com/mcmonkeyprojects/SwarmUI); [Fooocus](https://github.com/lllyasviel/Fooocus); [SD.Next](https://github.com/vladmandic/sdnext); [Easy Diffusion](https://github.com/easydiffusion/easydiffusion); [Krita AI Diffusion](https://github.com/Acly/Krita-AI-Diffusion); [Diffusers](https://github.com/huggingface/diffusers); [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp).

**Architecture:** native Image Generation Gateway → independently operated engine workers. Gateway owns model discovery/registration, backends, queues/jobs, progress/cancellation, delivery/history, artifacts, quotas, GPU health, permissions, model/workflow versions, provenance and license metadata. ComfyUI is an initial workflow engine candidate; InvokeAI informs editing experiences, and Diffusers is a possible lightweight specialized pipeline. The product UI and image studio remain first-party Glaze experiences.

## 12. Multimodal AI

**Planned:** image/screenshot/photo and visual-document understanding, text+image chat, audio transcription, spoken replies, voice interaction, image generation/editing.

**Future:** video/frame understanding, summaries, video-to-text, text-to-video, image-to-video, audio generation/classification and cross-modal knowledge search.

**Candidates:** [Transformers](https://github.com/huggingface/transformers), [Diffusers](https://github.com/huggingface/diffusers), [FFmpeg](https://ffmpeg.org/), [OpenCV](https://opencv.org/) and approved local multimodal models. Introduce modality workers independently from the core chat contract.

## 13. Voice, audio and meetings

**Planned:** speech recognition/synthesis, microphone and voice input/output controls, audio-file transcription, timestamps, transcript summaries, multilingual support and selectable speech models/voices.

**Future:** real-time voice; meeting capture; speaker diarization; searchable meeting transcripts; summaries, action items, meeting notes and voice-assisted automation.

**Candidates:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [whisper.cpp](https://github.com/ggml-org/whisper.cpp), [Piper](https://github.com/OHF-Voice/piper1-gpl), [Coqui TTS](https://github.com/coqui-ai/TTS), [Silero VAD](https://github.com/snakers4/silero-vad), [FFmpeg](https://ffmpeg.org/), [pyannote.audio](https://github.com/pyannote/pyannote-audio).

**Gate:** speech/voice/model-weight licenses, user consent, sensitive audio processing and retention must be reviewed separately.

## 14. Artifacts and productivity

**Planned:** authored/edited writing; professional documents, summaries, reports, code/configuration, Markdown, tables/charts and downloadable outputs; versioned Workspace organization, provenance, editing and exports; governed retention, backup and recovery.

**Advanced:** interactive previews, side-by-side source/results, document templates, application previews, sandboxed executable artifacts, spreadsheet analysis and presentations.

**Candidates:** [Pandoc](https://pandoc.org/), [python-docx](https://python-docx.readthedocs.io/), [PptxGenJS](https://gitbrent.github.io/PptxGenJS/), [openpyxl](https://openpyxl.readthedocs.io/), [ECharts](https://echarts.apache.org/), [Mermaid](https://mermaid.js.org/), [KaTeX](https://katex.org/).

## 15. User interface and experience

**Target:** the current approved Glaze contract, without third-party design-system takeover.

**Planned surfaces:** adaptive layout; collapsible navigation; persistent composer; chat and conversation history; Workspace navigation; optional context panel; knowledge Library; research UI; image studio; model picker; agent/tool/automation management; administration; light/dark modes; keyboard navigation, accessible touch targets and reduced-motion support; Compact/Medium/Expanded/Wide behavior; clear loading/errors/offline and privacy/security/runtime indicators.

**Existing foundation to retain unless formally changed:** React, TypeScript, Vite, Node.js; Glaze-compatible accessible primitives, Markdown renderer, Shiki or equivalent code display and ECharts or an approved chart renderer.

## 16. Collaboration and multi-user

**After accepted Identity integration:** individual accounts; RBAC, groups, authorized shared Workspaces/knowledge, shared templates/agents/tools; per-model and resource access rules; memberships and administrator management.

**Later candidates:** collaborative AI channels, group human+agent discussion, sharing/threads, team research, shared workflows and artifact libraries. Third-party identity infrastructure may be replaceable transport, never the owner of app permissions.

## 17. Security, privacy and nine Integral Platform Systems

| System | Intended responsibility |
| --- | --- |
| GoreeCloud Manager | App inventory, administration, lifecycle and approved control operations |
| Privacy Shield | Data minimization, local/external processing, consent/retention and privacy evidence |
| Wardveil Security | Artifact scanning, trust, execution protection and security evidence |
| Everkeep | Backup, export, restore, recovery and preservation |
| Glaze | First-party accessible visual/interaction design |
| GoreeCloud Mesh | Capability/service discovery, integration coordination and events |
| GoreeCloud Identity | Authentication, session/service identity and claims; AI retains resource authorization |
| GoreeCloud Policy | Policy decision/enforcement coordination and evidence |
| GoreeCloud Observability | Privacy-preserving health, metrics, logs, traces and diagnostics |

**Controls:** private-by-default/local-only modes; explicit external-processing disclosure; least privilege and backend-managed secrets; conversation/Workspace authorizations; staged scanning, digest-bound release and secure temporary data; prompt-injection and untrusted-source isolation; model-weight integrity; sandboxed active tools; human approvals; audit/evidence, quotas/rate limits; secure exports/deletion; tested backup and recovery. A clean scan never alone authorizes execution or model loading.

**Acceptance:** nine systems require their own current contracts, integrations, consumer review and runtime evidence. Writing this document does not establish any integration.

## 18. Infrastructure and deployment

**Planned:** browser-delivered self-hosted app and API; private network access/TLS; local inference; transactional conversation/Workspace data; private file/object store; workers, embeddings and retrieval, isolated image GPU workers, health/readiness, monitoring, quotas, backup/recovery and optional distributed inference.

**Candidates:** [Node.js](https://nodejs.org/), [PostgreSQL](https://www.postgresql.org/), [Docker](https://docs.docker.com/engine/) or [Podman](https://podman.io/), [Caddy](https://caddyserver.com/), [NetBird](https://netbird.io/), [OpenTelemetry](https://opentelemetry.io/), [Prometheus](https://prometheus.io/), [Grafana](https://grafana.com/oss/grafana/), [SeaweedFS](https://github.com/seaweedfs/seaweedfs), optional [Redis](https://redis.io/), GitHub Actions or approved GoreeCloud Code CI.

**Environment:** approved Linux host/VM, sized CPU/RAM/GPU and VRAM, durable model/database/artifact storage, separate protected backup storage, private DNS/certificates, approved egress and compatible GPU drivers. Sizing needs representative selected-model, concurrency, context and image-workflow benchmarks; do not infer capacity from host labels.

## 19. Third-party dependency and procurement register

| Resource | Role | Preliminary classification |
| --- | --- | --- |
| Ollama | Replaceable local inference | Initial foundation |
| React / TypeScript / Vite; Node.js | Frontend and backend | Existing Development foundation |
| PostgreSQL; pgvector | Durable data and native vectors | Recommended architecture candidates |
| Docling; FFmpeg | Structured parsing and multimedia | Recommended, subject to gates |
| Tesseract; sentence-transformers | OCR, embedding/reranking | Optional |
| Qdrant | Independent vector engine | Optional alternative |
| ComfyUI | Image generation workflows | Recommended initial image backend candidate |
| Diffusers; InvokeAI | Custom pipelines/creative editing | Optional |
| AUTOMATIC1111; Forge; SwarmUI | Diffusion engine alternatives | Optional |
| faster-whisper; Piper | Local speech input/output | Planned audio-stage candidates |
| MCP SDKs | Controlled tool protocol | Recommended candidate |
| Playwright | Authorized browser automation | Advanced-stage candidate |
| pg-boss | PostgreSQL-based background jobs | Recommended initial candidate |
| BullMQ + Redis; Temporal | Alternative queues/durable orchestration | Optional |
| Docker / Podman | Services and isolated tools | Recommended candidates |
| Caddy / NetBird | HTTPS and approved private access | Architecture dependencies, pending verification |
| OpenTelemetry | Diagnostics instrumentation | Recommended |
| Prometheus / Grafana | Operations monitoring | Optional infrastructure |
| OpenAI and other cloud APIs | Optional external model capability | Not required; privacy/security approval prerequisite |

**Before adopting any candidate**, evaluate: (1) source availability and software license; (2) whether required functionality is actually open source; (3) self-hosting/offline support; (4) subscriptions/accounts; (5) security/maintenance; (6) privacy/egress; (7) hardware/operating cost; (8) API stability; (9) export/backup/recovery; (10) upgrade/replace/migrate; (11) architecture fit; and (12) model-weight and other license obligations. A listing does not constitute license, security, procurement, supplier or production approval.

## 20. Phased implementation roadmap

| Phase | Proposed scope | Completion prerequisite |
| --- | --- | --- |
| **0 — Source and platform foundation** | Original React/TypeScript/Vite + Node foundation, API/provider contracts, persistence/model roles, Glaze, platform contracts, tests and representative runtime | Exact-revision proof; no inherited platform acceptance |
| **1 — Conversation** | Local model selection/streaming/cancel; durable conversations; edit/regen/branch/export; file/Workspace authorization; secure persistence/recovery | Target-host interoperability, security, privacy, restore evidence |
| **2 — Workspaces and knowledge** | Workspace lifecycle, approved document ingestion, parsing, embedding/indexes, native RAG, permission-filtered citations | Wardveil release, Identity/Privacy/Policy and knowledge delete/rebuild evidence |
| **3 — Research and image** | GoreeCloud Search, cited current research, Image Generation Gateway, ComfyUI candidate, text-to-image, editing, queues/artifact storage | First-party provider contracts, licensed model/workflow and GPU tests |
| **4 — Agents and automation** | Capability Broker, MCP/API tools, sandboxed code, schedules, plans/history, developer/artifact workflows | Explicit tool authority, approvals, idempotency/recovery/rollback |
| **5 — Advanced multimodal** | Speech, transcription, advanced image/video evaluation, multi-agent work, collaboration | Modality-specific safety/licensing/consent and runtime evidence |
| **6 — Qualification and transitional retirement** | Parity evaluation, migration of required AnythingLLM/Open WebUI data, permissions/digest verification, backup/restore, hardware testing, releases | Current all-system evidence, formal acceptance, verified rollback before retirement |

Phases are sequencing intent, **not** evidence of delivery, dates or automatically granted production approval.

## 21. Recommended initial build configuration

| Layer | Preferred starting architecture |
| --- | --- |
| Application | React, TypeScript, Vite, Node.js, first-party AI API, Glaze |
| Models | Ollama and approved installed conversation/embedding models, gateway-isolated alternatives |
| Storage / RAG | PostgreSQL, pgvector, owned ingestion/retrieval; Docling after trust and parser acceptance |
| Image | Image Generation Gateway; independent ComfyUI engine candidate; controlled queues and artifact store |
| Agents / jobs | AI Capability Broker; approved MCP tools; PostgreSQL-backed jobs and isolated execution |
| Platform | Identity, Privacy Shield, Wardveil Security, Policy, Everkeep, Mesh, Manager, Observability; Glaze |
| Network | Approved private transport, NetBird, DNS, Caddy HTTPS and containers when appropriate; validated local hardware |

Reduce mandatory suppliers, keep all non-first-party engines replaceable and benchmark before committing to distributed infrastructure.

## 22. Final product vision and evidence rule

GoreeCloud AI will be the central first-party GoreeCloud intelligence experience across conversations; optional local/external models; Workspaces; documents and governed RAG; live research through Search; permission-controlled agents and automation; engineering tools; native image generation/editing; future multimedia/voice; artifacts and collaboration; secure private self-hosting; observability and recovery.

The long-term objective is a comprehensive, modular, open-source-first AI platform controlled by GoreeCloud, without mandatory dependence on AnythingLLM, Open WebUI or any single runtime/provider. **Every feature remains planned, proposed, in-progress or blocked until authoritative source, integration, authorization, security, privacy, testing and runtime acceptance evidence establishes the appropriate implementation and release state.**
