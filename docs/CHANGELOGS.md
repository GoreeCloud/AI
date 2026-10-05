# GoreeCloud AI — Changelogs

## 2026-10-05

### Added — Workspace context and conversation utilities

- Moved Workspace instruction resolution to the backend: the browser sends the selected Workspace ID, the backend resolves the saved Workspace, and its instructions are applied transiently as private system context while remaining outside the persisted conversation transcript.
- Added saved-conversation search across title, model and Workspace name.
- Added user-controlled local Markdown conversation export and a manual local-model inventory refresh control.
- Disabled the not-yet-connected knowledge Library and external Research controls so the Development interface no longer presents those no-op surfaces as available capabilities.
- Added conversation-end streaming scroll, auto-resizing prompt composition, quieter screen-reader generation status, Ctrl/Command+K conversation-search focus, and supporting focus/disabled-state polish.
- Added editable Workspace names and default model-role preferences through the existing Workspace persistence boundary; missing local role matches remain explicit and do not trigger silent substitution.
- Hardened Workspace create/update payloads with closed supported-field sets, bounded names/instructions/resource-ID lists, explicit model-role allowlisting, and fail-closed HTTP 400 responses for malformed input; added four focused validator tests.

### Changed — current Glaze consumer target

- Reverified the live `GoreeCloud/glaze` lifecycle registry and advanced GoreeCloud AI's declared consumer target from the superseded 1.6.0 target to current Official Anchor **Glaze V1.7 / 1.7.0**.
- GoreeCloud AI remains migration-required/nonconformant for Glaze. This target reconciliation does not create consumer acceptance, release authority, deployment authority, Seal qualification, or Anchor qualification.

### Validation boundary

- These changes are Development source on Draft PR #1. Exact-head CI and runtime evidence remain authoritative for validation; this entry does not treat source mutation or documentation as proof of successful build, deployment, or production acceptance.

## 2026-09-30

### Added — agent intelligence Development foundation

- Added pure helpers for governed context selection, dependency/shared-resource work planning, declared capability selection, proportional execution-mode classification, and bounded recovery planning.
- Added seven focused Node tests for the current isolated foundation. Exact-head validation for the recovery slice passed 148 Node tests with 0 failures before this documentation reconciliation.
- The foundation remains disconnected from live HTTP/chat and does not establish full AIR-001 through AIR-017 conformance, runtime execution authority, Seal qualification, or Anchor qualification.

### Changed — repository identity, Contract 2.0 lifecycle and documentation layout

- Reconciled the canonical repository identity from the historical name `GoreeCloud/goreecloud-ai` to the live repository `GoreeCloud/AI`; the repository ID and Git history are continuous.
- Migrated `goreecloud.platform.yaml` from Platform Contract 0.4 legacy lifecycle semantics to Contract 2.0 with truthful lifecycle `forge`, Development deployment state, not-started qualification, blocked/migration-required flags and next gate `weave`.
- Preserved all nine Integral Platform Systems as evidence-gated; Glaze UI is `applicable-migration-required` for Official Anchor 1.6.0, while the other unaccepted platform integrations remain `applicable-blocked`.
- Migrated human-readable repository documentation from the root into `docs/` under the current repository-root cleanliness standard, keeping `README.md`, `LICENSE`, machine/configuration entry points and build files at root.
- Updated the Platform Contract workflow to pin the current verified Contract 2.0 implementation revision and to watch the canonical `docs/` documentation paths.
- This migration changes governance declarations and repository organization only. It does not wire model routing into live chat, create authenticated runtime authority, establish real target-host model evidence, deploy the application, enter Seal, or qualify Anchor.

This repository-local changelog records meaningful source, architecture, security, privacy, governance and documentation changes. Repository history and pull-request evidence remain authoritative for exact commits and checks; entries here summarize verified lifecycle events without implying deployment or Stable acceptance.

## 2026-09-23

### Corrected — current Glaze UI consumer authority

- Reconciled GoreeCloud AI's machine-readable Platform Contract declaration and current repository documentation to Official Stable GLAZE UI V1.6 / 1.6.0 after verifying the live `GoreeCloud/glaze-ui` lifecycle registry.
- Retained GoreeCloud AI as applicable-blocked/nonconformant for Glaze UI until this application implements 1.6.0 and produces its own exact-revision consumer acceptance evidence; the shared Glaze release does not certify this consumer.


### Added — approved model-routing Development foundation

- Added a fail-closed approved-model selector for 13 functional roles, bounded backend preflight, protected local policy reader and literal-loopback model discovery.
- Added opt-in read-only model-routing and model-resource diagnostics plus a pure capability/resource-fit candidate assessment.
- Added an operator-initiated approved-model runtime validator that requires explicit Development opt-in, protected local policy, exact role/model approval and literal-loopback GoreeCloud AI; it performs one streamed request through the existing backend and emits sanitized evidence without model output or credentials.
- Added native subprocess/loopback coverage for the approved-model runtime validator. Real model inference is never run in CI.

### Changed — repository feature/changelog governance

- Migrated legacy `FEATURE-ROADMAP.md` control into repository-native `IMPLEMENTED-FEATURES.md` and `PLANNED-FEATURES.md` while preserving FR-001 through FR-003.
- Established this `CHANGELOGS.md` as the repository-local human-readable history required by current governance.
- Retained `FEATURES.md` only as a convenience overview; canonical implemented/open feature state now lives in the mandatory feature-state files.

### Validation state

- The prior exact Draft head `a3b9742f7644d478b042c8ec7f590f1e5bb90c38` passed Validate GoreeCloud AI `35861922829` and Platform Contract `35861923871` before this continuation slice.
- Any later commit recorded above requires its own exact-head CI evidence. These changes do not by themselves establish target-host production acceptance, authenticated platform integrations, deployment or Stable qualification.

## 2026-09-17

### Changed — Platform Contract 0.4 migration

- Migrated the Draft line to Platform Contract 0.4 with exactly nine Integral Platform Systems.
- Added GoreeCloud Policy and GoreeCloud Observability as applicable-but-blocked integration obligations.
- Updated the then-current Stable Glaze UI consumer target and retained Development / Draft / nonconformant lifecycle state.

## 2026-09-09

### Added — legacy roadmap control

- Added the now-retired repository `FEATURE-ROADMAP.md` and synchronized Drive roadmap control. Those records carried governance/reconciliation obligations rather than a complete product feature inventory.

## 2026-09-07

### Added — durable Development replay state

- Added Development-only durable runtime-evidence use state using hashed evidence/request identifiers, restart persistence, replay detection and revocation handling.
- Kept production trust, execution, indexing, retrieval and model-context authority explicitly false pending authenticated evidence producers and accepted adapters.

## 2026-09-06

### Added — runtime evidence readiness and binding foundations

- Added fail-closed runtime-adapter readiness assessment for future Identity, Privacy Shield and Wardveil evidence.
- Added strict runtime-evidence envelope binding and replay preconditions for authority/resource/operation/request/time semantics.
- These helpers remained structural Development evidence and did not create production trust or execution authority.

## 2026-09-05

### Hardened — Privacy Shield structural and temporal validation

- Added request-retention expiration validation and closed-schema checks for applicable Privacy Shield request/decision structures.
- Hardened non-finite clock and expired-retention handling.
- Preserved explicit non-authorizing outcomes and false downstream knowledge eligibility.

## 2026-08-31

### Added — knowledge authorization assessment

- Added bounded non-persistent Identity/application and Privacy Shield authorization-input assessment.
- Added strict actor, resource, operation and temporal binding while keeping persistent authorization and execution disabled.
- Corrected an expired-authorization test fixture whose invalid timestamp ordering prevented the intended assertion; no production check was weakened.

## 2026-08-30

### Added — live runtime validation, safe extraction and repository records

- Added the original opt-in runtime validator for application health, local model discovery and optional streamed chat through GoreeCloud AI.
- Added Wardveil-gated passive text extraction for bounded UTF-8 plain text, Markdown and JSON with source-digest revalidation.
- Added the repository specification, feature overview, benefits, competitive objectives and user manual.
- Began Glaze UI migration work that was later superseded by newer Stable consumer targets.

## 2026-08-27

### Added — attachment lifecycle and trust foundations

- Added private attachment staging, quotas, serialized mutations, Workspace reference cleanup and lifecycle safeguards.
- Added native fail-closed Wardveil attachment trust enforcement and supporting tests/documentation.

## Earlier foundation

Earlier repository history establishes the initial GoreeCloud AI application, conversation/runtime and project foundations. Exact details remain recoverable in Git history. This changelog does not rewrite historical commit facts or treat later planned requirements as if they existed at repository inception.
