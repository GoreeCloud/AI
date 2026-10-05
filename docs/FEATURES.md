> **Feature-state authority:** This file is a convenience overview. The canonical repository-native records are [IMPLEMENTED-FEATURES.md](IMPLEMENTED-FEATURES.md) for implemented capability state and [PLANNED-FEATURES.md](PLANNED-FEATURES.md) for open/incomplete capability state. Meaningful history is maintained in [CHANGELOGS.md](CHANGELOGS.md).

# GoreeCloud AI Features

## Implemented source foundation

- Responsive native conversation shell with Glaze-inspired navigation, context surfaces, appearance adaptation, reduced-motion behavior, and first-party dialogs.
- Backend-owned Ollama model discovery and streaming chat boundary.
- Persistent conversations with rename, edit/resubmit, regeneration, branching, and explicit branch lineage.
- Stable GoreeCloud model roles mapped to replaceable installed runtime models.
- Development-only approved 13-role model routing selector and bounded backend preflight with local-policy file and loopback discovery adapters; not wired to inference, authenticated administration, or platform-system decisions.
- Explicit opt-in developer model-routing diagnostic that composes private local policy and loopback-only installed-model discovery, outputs sanitized selection state, and never invokes inference or grants authorization.
- Pure Development-only resource candidate assessment for operator-declared model roles, modalities, token/context budgets, memory estimates/reserves and concurrency headroom. A candidate never authorizes inference, tools or runtime acceptance.
- Separately opt-in local model-resource diagnostic that reads protected policy/profile files, discovers only literal-loopback installed model names, samples free system RAM, and outputs a sanitized non-authorizing candidate or refusal.
- Separately opt-in approved-model runtime validator that binds an exact role/model to the protected Development policy and application-backed installed-model discovery, executes one streamed request through literal-loopback GoreeCloud AI, and emits sanitized evidence without generated text or credentials. It does not authorize production inference.
- Native Workspace persistence for instructions, default model role, file references, knowledge placeholders, tools, and research preferences.
- Private attachment staging, restrictive permissions, SHA-256 binding, metadata records, quotas, storage usage, and deletion/reference reconciliation.
- Node-native Wardveil artifact trust gate with current authoritative clean-evidence checks, post-scan digest verification, fail-closed unavailable/unknown behavior, and non-destructive quarantine handoff state.
- Explicit attachment trust presentation: Verified, Unverified, Held, and Blocked.
- Passive post-Wardveil text extraction for released UTF-8 text, Markdown, and JSON with source digest revalidation and private extracted-text persistence.
- Read-only knowledge-eligibility assessment that reports Wardveil, extraction, Identity/application, Privacy Shield, indexing, retrieval, and model-context gates while keeping all knowledge-use execution eligibility false.
- Bounded `POST /api/files/:id/knowledge-authorization-assessment` consumer for supplied GoreeCloud Identity/application-authorization context plus the current Privacy Shield decision contract.
- Application-local knowledge operation identifiers with strict resource/operation/actor/time binding rather than fabricated GoreeCloud-wide Identity scopes.
- Privacy Shield `DENY`, `REQUIRE_USER_DECISION`, `ALLOW`, and `ALLOW_WITH_CONSTRAINTS` handling with request/decision, zone, destination, operation, acting-user, obligation, decision-expiration, and optional request-retention-expiration checks.
- Explicit non-authority markers: supplied authorization input is not production-trusted, is not persisted as authorization, and cannot authorize execution while authenticated runtime adapters are absent.
- Independent Python Wardveil reference contract and validation suite.
- Opt-in live application/runtime validation for service health, Ollama discovery, and an explicitly selected streamed model request through the GoreeCloud AI backend.
- Repository-local `docs/USER-MANUAL.md` as the sole authoritative user manual under the current manual-storage and root-cleanliness standards. A former Drive-side synchronized manual is historical, not current authority.
- Unified GoreeCloud branding authority reference.

## Under active development

- Recorded live application-to-Ollama validation against the intended environment.
- Authenticated GoreeCloud AI-to-Wardveil Scan transport and target-environment clean/malicious/unavailable validation.
- Migration/reconciliation to the current Official Anchor **Glaze V1.7 / 1.7.0** consumer target and exact-revision product conformance evidence. Older Glaze UI and 2.x-labeled source is historical migration input, not current conformance.
- Authenticated GoreeCloud Identity session/service integration, multi-user persistence, and application-owned Workspace/resource authorization.
- Authenticated Privacy Shield enforcement/decision/capability/evidence integration for file, extraction, conversation, model, research, and external-processing operations.
- Everkeep backup, restore, retention, export, preservation, portability, and application recovery evidence, including future derived knowledge state.
- GoreeCloud Mesh coordination/evidence integration.
- Safe content ingestion, provenance, chunking, embeddings, indexing, retrieval, RAG, and Workspace permission filtering.

## Planned

- GoreeCloud Search-backed current-information and research orchestration.
- Governed tools and agents.
- Conversational first-party image generation with replaceable local image runtimes.
- Multimodal workflows and artifacts.
- Production database/storage architecture, distributed quotas, lifecycle management, authorization evidence, and recovery.

Planned items are objectives and must not be treated as implemented or production-accepted capability.
