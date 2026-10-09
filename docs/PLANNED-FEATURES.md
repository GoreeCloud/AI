# GoreeCloud AI — Planned and Open Features

**Authority:** Repository-native open feature and capability record  
**Lifecycle:** Forge / Draft PR #1 / nonconformant

This file contains planned, in-progress, partial, blocked, deferred and otherwise incomplete GoreeCloud AI obligations. Items remain open until implementation and verification are supported by authoritative evidence or an explicit lifecycle disposition replaces them.

## In progress

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
