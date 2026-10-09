# GoreeCloud AI — Phase Acceptance Matrix

**Document class:** Planned engineering qualification criteria, not implementation or production evidence.  
**Source:** [AI Product Vision and Architecture](./AI-PRODUCT-VISION-AND-ARCHITECTURE.md) and [open feature register](./PLANNED-FEATURES.md).  
**Lifecycle:** Forge Development; Draft PR #1 is not Anchor or production-accepted.

The nine Integral Platform Systems and applicable independent security, privacy, licensing, retention and recovery review apply to every stage. An upstream engine or shared GoreeCloud service being accepted does **not** automatically accept the GoreeCloud AI consumer.

| Phase | User-observable target | Minimum implementation/qualification evidence | Hard gates |
| --- | --- | --- | --- |
| **0 — Source and platform** | First-party Glaze experience with backend-owned replaceable Ollama access | Exact source/lockfile; TypeScript, server and client tests; original product/API contract; current Glaze 1.7.0 consumer evidence; representative private host health | Identity, Privacy Shield, Wardveil, Policy, Everkeep, Manager, Mesh, Glaze and Observability mapped honestly; unresolved remain blocked |
| **1 — Conversation** | Streaming, cancellable local chat; persisted sessions; edit, branch, regenerate, export and managed Workspaces | Controlled browser keyboard/IME/mobile testing; model-routing policy checks; stale-stream/abort/error tests; concurrent store updates; restoration; permissions and retention | Authenticated session and per-resource authorization before multi-user use; backend-owned credentials and model routing |
| **2 — Knowledge and RAG** | Secure document collections with permission-filtered answers and citations | Verified scan/digest, parser isolation, exact source/version identity, chunk/embedding versioning, retrieval quality, deletion/reindex/restore and tenant-isolation tests | Authenticated Wardveil release, AI application authorization, Privacy Shield and Policy; knowledge eligibility remains disabled until accepted |
| **3 — Research and images** | Cited current web research and native image studio | GoreeCloud Search API tests, publication/retrieval provenance, quoted evidence; image-gateway queue/cancel/progress, model/workflow metadata, reproducibility, GPU load/quota and artifact recovery tests | External egress authorization, provenance and licensing for image models/workflows, separated ComfyUI or other engine trust |
| **4 — Agents and automation** | Permission-bound tools, multi-step agents and scheduled jobs | Capability Broker decisions, human approval tests, sandbox escape prevention, idempotent jobs, cancellation/rollback, log redaction and durable recovery | Models, MCP servers, tools and third-party frameworks never own the authorization decision |
| **5 — Multimodal and collaboration** | Governed audio/vision, later video, optional shared Workspaces | Voice and model-license reviews; capture consent; sensitive media retention/deletion; access revocation; multi-user isolation and assistive technology testing | Explicit privacy rights and authenticated resource/session grants |
| **6 — Qualification/retirement** | Verified replacement of required AnythingLLM/Open WebUI workflows | Owner-approved parity inventory, faithful conversation/document migration, access-control checks, independent backup restore/rollback, current exact-head/base checks, deployment and operator acceptance | No retirement until the first-party alternative is accepted; CI pass alone is insufficient |

## Architecture ownership boundaries

| Interface | Owner of the contract | Replaceable supporting candidates | Required proof before adoption |
| --- | --- | --- | --- |
| Model Provider Gateway | GoreeCloud AI | Ollama first; llama.cpp, vLLM, LocalAI, Transformers and optional approved cloud APIs | Model/source licensing; operator policy; local/egress routing proof; model-capability and hardware measurements |
| Document Intake | GoreeCloud AI with Wardveil authorization | Docling, Tika, Tesseract, PaddleOCR, Unstructured and conditionally PyMuPDF | Input threat model; sandbox; exact artifact release; parser and software/model licenses |
| RAG Index | GoreeCloud AI | PostgreSQL/pgvector first; Qdrant, Chroma, Milvus, embedding/rerank libraries | Authz-filtered retrieval, transaction/durability, model versioning, migration and restore |
| Research | GoreeCloud Search upstream; AI user/research layer | Search-owned provider infrastructure; SearXNG only as a possible transitional Search-side implementation | First-party API, citation lineage, disclosure and Privacy Shield egress authorization |
| Image Generation Gateway | GoreeCloud AI | ComfyUI first candidate; Diffusers, InvokeAI and others | Workflow/weight integrity, component licenses, isolated jobs, GPU limits, storage and provenance |
| AI Capability Broker | GoreeCloud AI + Policy and Identity | MCP, LangGraph/Haystack as optional libraries | Trusted user/resource capability evidence; approvals, effects and audit remain first-party |
| Automation | GoreeCloud AI | pg-boss first candidate; BullMQ/Redis and Temporal alternatives; n8n as potential external integration/reference | Idempotency, recovery, cancellation, quotas, license and deploy model |
| Audio services | GoreeCloud AI | faster-whisper, whisper.cpp, Piper and optional others | Microphone consent, local processing restrictions, voice and weight licenses |
| Operations | GoreeCloud AI and platform systems | Caddy, NetBird, Docker/Podman, OpenTelemetry and optional Prometheus/Grafana | Private networking, approved certificates, secure logging, migration and backup |

## Evidence worksheet for each work item

For each candidate change, record these in the authoritative code/issue/task systems rather than duplicate PR state in Drive:

1. Requirement and explicit user-visible behavior; affected platform systems and permissions.
2. Exact source commit, parent/base, applicable test suite names and workflow run identifiers.
3. Source/data provenance, dependency and model-weight licenses, external network destinations, retention obligations.
4. Negative tests for unknown, stale, malformed, unauthorized, cancelled and resource-exhausted inputs.
5. Real target-device/browser/host observations; accessibility and performance, GPU/VRAM where applicable.
6. Secure export, backup/restore, rollback and component replacement exercise.
7. Independent required review, accepted/blocked/deferred status, remaining risk and accountable next step.

**Fail closed:** a dependency recommendation, a clean file scan, a successfully generated artifact or a passing CI run does not grant inference, active file parsing, tool execution, external processing, installation, production release or Anchor qualification. All pending source implementation tasks remain in the canonical GoreeCloud AI Task Management DOCX.
