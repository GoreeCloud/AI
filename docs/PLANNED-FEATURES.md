# GoreeCloud AI — Planned and Open Features

**Authority:** Repository-native open feature and capability record  
**Lifecycle:** Forge / Draft PR #1 / nonconformant

This file contains planned, in-progress, partial, blocked, deferred and otherwise incomplete GoreeCloud AI obligations. Items remain open until implementation and verification are supported by authoritative evidence or an explicit lifecycle disposition replaces them.

## Detailed owner-defined product vision and architecture

The owner-defined 22-section [AI Product Vision and Architecture](./AI-PRODUCT-VISION-AND-ARCHITECTURE.md) is the planning annex for native knowledge/RAG, GoreeCloud Search-backed research, governed agents/automation, image and speech/multimodal workflows, artifacts, collaboration, candidate dependencies and phases. The [Dependency Adoption Gates](./AI-DEPENDENCY-ADOPTION-GATES.md) and [Phase Acceptance Matrix](./AI-PHASE-ACCEPTANCE-MATRIX.md) establish proposed evaluation requirements. No proposed third-party library, external-processing service or model weight is approved or adopted merely by appearing in these documents.

Cross-platform web, desktop (Linux/Windows/macOS), and mobile (Android/iOS) clients plus first-party GoreeCloud ecosystem integrations remain planned until implemented and verified. Independent streams may proceed only behind relevant Identity, Privacy Shield, Wardveil, Policy, recovery, security and Glaze acceptance gates.

## In progress

### Search integrity and Glaze V1.7 consumer gates

Validate full-query rejection for more than 120 characters or 16 terms, dialog-owned Ctrl/Command+K behavior, representative CJK composition, browser Find coexistence and screen-reader focus/announcements. Glaze 1.7.0 is an Official Anchor/Stable inherited-runtime contract; retained development features and downstream GoreeCloud AI consumer qualification are **not** automatically accepted. Verify the exact Glaze consumer source, privacy/security and cross-device behavior independently before release.

### Finder shortcut and history-search consumer acceptance

Verify Ctrl/Command+Shift+F, native browser Ctrl/Command+F, Ctrl/Command+K saved-conversation search, focus and modal isolation, IME/composition behavior, search limits and screen-reader announcements in representative browsers. No cross-conversation message indexing, new server authorization, or production acceptance is implied.

### Transcript clipboard privacy and accessibility acceptance

Verify explicit-copy affordance, permission failures, keyboard navigation, format fidelity, private clipboard disclosures and screen-reader feedback on supported browsers and target devices. Clipboard copying is not authenticated sharing, safe transmission, restore or Everkeep backup.

### Conversation outline consumer acceptance

Validate current-conversation user-prompt navigation and turn counts in a representative browser, including keyboard focus, assistive technology announcements, long-message and responsive behavior. The Draft source is not a server search, saved index, backend authorization, knowledge retrieval or production acceptance.

### Conversation search and transcript export acceptance

The current Draft PR #15 source adds find-in-current-conversation and Markdown, TXT and JSON downloads. The remaining acceptance work includes browser and screen-reader testing, IME/keyboard handling, downloaded file integrity/privacy, independent review, and Glaze/platform conformance. The exports are not governed Everkeep backups or restore/import capabilities.

### Approved model routing integration

Connect approved model-role routing to the backend only after the required trust and runtime boundaries are ready. Existing Development source includes selector, preflight, protected local policy/discovery adapters and isolated diagnostics; the current manual chat behavior remains separate.

**Remaining acceptance:** authenticated administrator policy/profile provenance; server-owned trustworthy resource producers; representative real hardware/model measurements including GPU/VRAM where applicable; application-to-runtime streamed evidence on exact candidates; Identity-backed application authorization; Privacy Shield and GoreeCloud Policy decisions; current platform acceptance; human security review for trust-boundary integration; rollback evidence.

### Gemma/Qwen target-runtime validation

Validate approved installed model variants on representative local hardware. Record exact-model application-path streamed evidence, capacity/latency observations and material limitations without treating a single passing request as production acceptance.

## Blocked on platform authority or runtime evidence

### GoreeCloud Identity and application-resource authorization

Implement authenticated transport/session evidence and server-owned authorization for conversations, Workspaces, models, files, tools, agents and other protected operations. Client-provided claims must never manufacture authorization.

### Wardveil file-intake production acceptance

Connect an authenticated deployed Wardveil scanner transport and validate clean, malicious, stale, unavailable, mismatched and post-scan digest scenarios before safe file release.

### Privacy Shield and GoreeCloud Policy enforcement

Implement authenticated processing-zone, consent, purpose and operation decisions; durable evidence; revocation; replay protection; policy/version binding and application enforcement.

### Native RAG and citations

After trusted parsing and authorization exist, implement chunking, embeddings, indexing, retrieval, deletion, provenance, source attribution and citation generation. Existing false eligibility gates must not be bypassed.

### Everkeep, Manager, Mesh and Observability

Implement accepted backup/restore/export/recovery, management, service coordination and privacy-preserving health/telemetry evidence for each applicable platform system.

## Pending consumer work

### Official Anchor Glaze 1.7.0 consumer conformance

Adopt current Official Anchor **Glaze V1.7 / 1.7.0** from the live `GoreeCloud/glaze` lifecycle authority and complete exact-revision product accessibility, responsive, performance and conformance evidence. Shared Glaze Anchor status does not certify the GoreeCloud AI consumer.

### Application Foundation adoption

Incrementally adopt the governed GoreeCloud Application Foundation where applicable without replacing GoreeCloud AI product-specific logic or falsely inheriting consumer acceptance from a shared component.

## Planned product capabilities

- GoreeCloud Search-backed current-information lookup, source discovery and deep research.
- Research Workspaces with persistent sources, citations, findings and reports.
- Native knowledge Library, governed embeddings, semantic search and retrieval.
- Coding assistance and future GoreeCloud Code integration.
- Permission-bound tools, skills, AI agents and multi-agent workflows.
- Reusable workflows, scheduled AI tasks and conditional monitoring.
- GoreeCloud ecosystem integrations through first-party application contracts.
- Persistent artifact workspace and editable document, spreadsheet and presentation generation.
- Data analysis and visualization for approved datasets.
- Image understanding, first-party conversational image generation and governed image transformation.
- Voice conversations, screen/camera intelligence and future audio/multimedia intelligence.
- Custom assistants, optional personal daily brief and permission-bound proactive intelligence.
- Cross-device and local-first intelligence with replaceable model/runtime/index infrastructure.
- Production database/storage architecture, distributed quotas and lifecycle management.

## Governance obligations migrated from the retired roadmap

The former `FEATURE-ROADMAP.md` and Drive roadmap control contained three ongoing governance obligations. They are preserved here rather than silently discarded:

- **FR-001 — Reconciliation control:** Maintain current planned and recommended GoreeCloud AI feature state from the authoritative project record and verified repository evidence in the repository-native feature records.
- **FR-002 — Action tracking:** Move actionable obligations into GoreeCloud Tasks Management when required, preserving priority, dependency and lifecycle disposition without creating duplicates.
- **FR-003 — Evidence-backed lifecycle:** Do not mark features implemented, complete, cancelled or superseded without authoritative evidence and reconciliation of the repository-native feature records.

The former requirement to synchronize a Drive roadmap is superseded by the repository-native feature/changelog standard. GitHub now owns feature-state authority; the legacy Drive roadmap is a migration source only and may be retired after verified migration.

## Review, release and deployment

Keep Draft work from being represented as release-ready while mandatory exact-revision runtime, security, privacy, recovery, platform, rollback and human-review gates remain incomplete. A passing source build or Development diagnostic is not a production or Anchor claim.
