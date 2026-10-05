# GoreeCloud AI — Implemented Features

**Authority:** Repository-native implemented-feature record  
**Lifecycle:** Forge / Draft PR #1 / nonconformant  
**Production status:** Not production-accepted or Anchor-qualified

This file records capabilities that exist in the current repository source. An entry here does not by itself prove deployment, target-environment interoperability, production acceptance, or Anchor qualification. Those states require their own exact-revision evidence.

## Application foundation

- React/TypeScript/Vite client with a responsive conversation shell, navigation and context surfaces.
- Node.js application backend bound to the local application boundary.
- Backend-owned local model discovery and streamed NDJSON chat through the replaceable local model runtime.
- Persistent conversations with rename, delete, edit/resubmit, regeneration, branching and branch lineage.
- Client-side saved-conversation search across title, selected model and Workspace name.
- User-controlled local Markdown conversation export containing the visible conversation transcript plus model/Workspace metadata; this browser export is not an Everkeep-governed backup or portability acceptance path.
- Native Workspaces with editable names, instructions, default model roles, file references, knowledge/tool placeholders and research preferences.
- Fail-closed Workspace create/update validation for supported fields, model-role identifiers, instruction/name bounds, research preference types, and bounded resource-ID collections.
- Workspace instructions are resolved by the backend from the selected Workspace ID and applied transiently as private system context to local model requests without being inserted into persisted conversation history or creating authorization.
- Manual local-model inventory refresh through the existing backend-owned Ollama discovery boundary.
- Inactive knowledge Library and external Research controls are explicitly disabled in the Development UI instead of presenting no-op controls as usable capabilities.

## Model routing and Development validation

- Stable GoreeCloud model-role abstraction over replaceable installed models.
- Side-effect-free approved selector covering the 13 planned functional roles.
- Bounded Development preflight that requires backend-supplied policy and model-discovery adapters and fails closed on invalid, stale, unavailable, timed-out or cancelled inputs.
- Restrictive protected local policy-file reader and literal-loopback-only installed-model discovery adapter.
- Explicit opt-in read-only model-routing diagnostic that never invokes inference.
- Pure operator-declared model capability/resource-fit candidate assessment covering role/model binding, modalities, tool-use declaration, context budget, estimated memory/reserve and concurrency headroom.
- Explicit opt-in local resource diagnostic that composes protected policy/profile input, loopback inventory and free **system RAM** sampling. It does not measure GPU VRAM or establish real model capability.
- Opt-in baseline live runtime validator for application health, application-backed model discovery and an explicitly selected streamed request.
- Opt-in approved-model runtime validator that binds one exact local Development request to a protected approval policy and exact application-backed installed-model discovery, executes one streamed request through the existing backend and emits sanitized evidence without generated text or credentials. This is Development evidence only; it does not authorize production inference.

## File, trust and knowledge foundations

- Private attachment staging with restrictive permissions, SHA-256 binding, metadata, quotas, aggregate storage limits, deletion and Workspace-reference reconciliation.
- Node-native Wardveil artifact trust gate with resource/digest binding, fail-closed unavailable/unknown handling and non-destructive quarantine handoff state.
- Explicit attachment trust presentation states: Verified, Unverified, Held and Blocked.
- Passive post-release text extraction for bounded UTF-8 plain text, Markdown and JSON with source-digest revalidation and private derived records.
- Read-only knowledge-eligibility assessment that reports security, extraction, Identity/application, Privacy Shield and downstream-stage gates while keeping indexing/retrieval/model-context execution disabled.
- Bounded non-persistent knowledge-authorization input assessment for supplied Identity/application context and current Privacy Shield decision structures.
- Application-local knowledge operation identifiers and strict actor/resource/operation/time/request/privacy binding.
- Explicit non-authority markers that prevent supplied authorization JSON from becoming production trust, persistent authorization or execution authority.
- Runtime-adapter readiness, evidence-envelope, replay-precondition and Development durable single-use/revocation registry foundations. These remain non-production trust scaffolding until authenticated producers and accepted adapters exist.

## Agent intelligence Development foundation

- Side-effect-free governed context selection with explicit scope, freshness, sensitivity and sharing metadata.
- Dependency-aware single-goal work planning with cycle rejection, declared action identities and shared-resource sequencing.
- Requirement-driven capability selection using declared operation fit, permission, sensitivity ceiling, health, authority and effect level; selection never creates execution authority.
- Proportional execution-mode classification for direct, standard, complex and high-consequence work.
- Bounded recovery planning for transient retry, local repair, declared fallback, degraded continuation, and safe stop outcomes; proposals preserve the original obligation and require later reverification without executing recovery.
- Seven requirement-linked Node tests covering the current isolated foundation. Exact-head validation at d0ce3d465df125766e46be7e3d460c78519b5fc5 passed 148 Node tests with 0 failures. The module is not imported by the live backend and does not establish full AIR-001 through AIR-017 conformance.

## Repository and verification foundations

- `docs/USER-MANUAL.md` as the sole authoritative repository user manual under the GitHub-only manual-storage and root-cleanliness rules.
- Repository-native specification, benefits, competitive objectives, branding references and implementation documentation.
- Platform Contract 2.0 declaration using the canonical Forge lifecycle and evaluating all nine Integral Platform Systems with incomplete integrations represented as blocked, migration-required, or nonconformant rather than passed.
- Exact-head CI for TypeScript checking, server syntax, Node tests, production client build, Wardveil reference tests/contract validation and Python compilation.

## Material limitations

- The new routing components are not wired into the live backend chat route.
- Current Development API bearer handling is not final GoreeCloud Identity/application authorization.
- No authenticated production Wardveil scanner transport is connected.
- No authenticated production Identity, Privacy Shield or GoreeCloud Policy runtime adapter is accepted.
- Native RAG execution remains disabled; indexing, retrieval and model-context eligibility remain false.
- Current source/CI evidence does not prove real target-host GPU capacity, sustained throughput, all model capabilities, production deployment or Anchor qualification.
