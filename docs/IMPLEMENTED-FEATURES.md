# GoreeCloud AI — Implemented Features

**Authority:** Repository-native implemented-feature record  
**Lifecycle:** Forge / Draft PR #1 / nonconformant  
**Production status:** Not production-accepted or Anchor-qualified

This file records capabilities that exist in the current repository source. An entry here does not by itself prove deployment, target-environment interoperability, production acceptance, or Anchor qualification. Those states require their own exact-revision evidence.

## Conversation search integrity and shortcut ownership (Draft PR #23 source)

- Loaded-message search refuses over-limit queries instead of silently truncating them, preventing matches that do not satisfy the complete query.
- Ctrl/Command+K history-search ownership now guards dialog focus and IME/repeated/modified key events.
- This is Draft source and unit-test evidence only, with independent accessibility, Glaze, privacy, representative browser/device, security and production acceptance outstanding.

## Local finder keyboard shortcut and history bounds (Draft Development source)

- Ctrl/Command+Shift+F opens the active-conversation finder without replacing the browser native Find command; IME/modified keys retain their existing guards.
- The saved-conversation sidebar search and helper are bounded to 120 characters and 16 query terms. The Context outline AI-response count no longer displays an extraneous glyph.
- Target-browser, CJK IME, screen-reader, security, Glaze and production acceptance remain outstanding.

## User-controlled transcript clipboard (Draft Development source)

- A toolbar button copies the selected Markdown, plain-text or JSON transcript format to the local OS clipboard only after a user click, with accessible success or failure feedback.
- The implementation reuses existing export data rather than creating server-side sharing; it does not grant authorization or qualify an Everkeep backup. Clipboard privacy, browser support and independent review remain open.

## Local conversation outline (Draft Development source)

- The Context panel shows browser-local user/assistant turn counts and the latest 24 user prompts, with keyboard-accessible navigation to their original message positions.
- Prompt previews are length-bounded and control-normalized; the capability adds no server endpoint, cross-conversation indexing, persistent storage, or execution authority.
- Source CI and target-browser accessibility acceptance must be verified at the exact candidate revision before treating this Draft source as qualified.

## Active-conversation find and portable transcript formats (Development source)

- The browser searches only messages already loaded in the active conversation. It uses bounded case/accent-insensitive word matching with next/previous wraparound, match indicators and IME-aware keyboard navigation; no additional backend search or permission is created.
- Local transcript export supports Markdown, plain-text and JSON outputs, normalized filenames and verbatim user/assistant message bodies. These downloads are not authenticated sharing, Everkeep backups or import/restore evidence.
- Focused search/export tests and exact-head GitHub CI passed on source commit `add1528d23d7670886eea8e9a27e6538807600ec`; representative browser, keyboard/IME, accessibility, privacy and platform acceptance remain pending.

## Composer and Workspace selection (Development source)

- Enter-to-send ignores active input-method composition, modifier shortcuts, repeated events, and multiline Shift+Enter; the keyboard helper has focused Node tests.
- Model and Workspace selectors wait for saved conversation updates before presenting a new selection and display failure details without silently committing local UI changes.
- Updating the Workspace default model role and updating the active conversation model are separate operations, with partial save failure disclosed.
- An individual failed chat request does not automatically mark the whole local model-discovery service offline.

These Draft-only source capabilities have passed exact-head CI; they do not establish representative browser operation, live runtime availability, or production acceptance.

## Conversation UX reliability (2026-10-08 candidate)

- Streamed-response interface changes are guarded by a conversation epoch; navigation invalidates stale token callbacks and terminal updates.
- Conversation opening rejects superseded loads so slower earlier history requests cannot overwrite later selections.
- Prompt submission waits for conversation creation before clearing the draft, prevents duplicate preparation, and surfaces a retryable composer error on creation failure.
- Saved-history search supports multiple query words across title, model, and Workspace fields, with accent-insensitive matching and no message-body indexing.
- Local Markdown export escapes untrusted title/model/Workspace labels while retaining message body text. Focused UI utility tests are included in CI.

These changes are Development candidate source capabilities, not representative-device or production-acceptance evidence.

## Application foundation

- React/TypeScript/Vite client with a responsive conversation shell, navigation and context surfaces.
- Node.js application backend bound to the local application boundary.
- Backend-owned local model discovery and streamed NDJSON chat through the replaceable local model runtime.
- All backend local-runtime HTTP requests now use a tested wrapper that preserves the existing deadline/cancellation behavior while forcing redirects to fail closed, preventing a configured local runtime from redirecting GoreeCloud AI requests to an unexpected target.
- The live `/models` route now reduces Ollama inventory data through the tested public catalog sanitizer before browser delivery: only unique trimmed model names are published, names are bounded to 512 characters, the public inventory is capped at 256 entries, arbitrary runtime metadata is omitted, and invalid catalog envelopes fail closed.
- The `/models` route now also bounds the upstream Ollama catalog body to 1 MiB before JSON parsing, with strict UTF-8 and JSON decoding, so oversized or malformed successful runtime responses fail closed before catalog sanitization.
- Browser chat types and backend chat input are limited to user/assistant message shapes ending in a user request; client-authored `system` messages are not representable in the client contract and are rejected server-side so private Workspace system context remains backend-owned.
- Streamed local-runtime output is now bounded by total-stream and per-NDJSON-line limits, decoded as strict UTF-8/JSON, reduced to public assistant-content/completion/error fields, backpressure-aware at the HTTP response boundary, and rejected fail-closed on malformed or oversized runtime output. The browser applies a second bounded parser and cancels malformed streams.
- The backend chat gateway now requires a terminal local-runtime chunk (`done: true` or a sanitized runtime error) before accepting upstream EOF, so abruptly truncated model streams are rejected instead of being treated as successfully complete.
- The unauthenticated health response reports only non-sensitive capability/configuration state and no longer exposes the configured local Ollama endpoint.
- Public JSON and streamed NDJSON responses now share centralized browser-facing security headers: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`.
- Shared browser API failures now surface bounded, whitespace-normalized public error details for conversations, Workspaces and files instead of status codes alone; displayed detail is capped to prevent oversized or control-character-heavy error text from dominating the interface.
- Local control-plane browser requests now have bounded client deadlines, with a longer allowance for attachment uploads.
- Runtime presentation distinguishes an unreachable local runtime from a reachable runtime with no installed models, with explicit refresh/install guidance.
- Browser model discovery now uses the shared bounded local-request deadline and sanitizes the returned inventory to at most 256 valid model records with bounded string fields and non-negative finite size metadata; malformed entries and unneeded arbitrary detail payloads are not consumed by the UI.
- Browser model discovery deduplicates accepted model names while preserving the 256-model cap; browser streaming independently requires terminal completion and rejects chunks after completion.
- Browser streaming also enforces a 2,000,000-character cumulative assistant-output ceiling before forwarding tokens into application state, preventing many small valid chunks from bypassing the per-buffer limit.
- Streamed browser error details are normalized, control-character stripped, whitespace-collapsed, and capped at 320 characters before they can surface to the application UI.
- Persistent conversations with rename, delete, edit/resubmit, regeneration, branching and branch lineage.
- Persisted conversation and Workspace stores validate their versioned envelopes and stored-record schemas on load; malformed timestamps, invalid resource shapes, unsupported versions, and duplicate record IDs fail closed instead of being consumed as application state.
- Stream completion and user-abort persistence is performed exactly once outside React state-updater callbacks; if persistence fails after a successful or stopped response, the visible response is retained and a save warning is shown without falsely marking the local model runtime offline.
- Conversation create/update persistence now uses closed supported-field sets, bounded title/model/message shapes, strict UUID-backed Workspace/parent references, and fail-closed malformed-input rejection.
- Conversation creation now resolves referenced Workspaces and parent conversations against live server state and validates the parent message index before persistence; Workspace reassignment also requires a live Workspace.
- Conversation Workspace association is serialized with Workspace deletion and attachment intake so a Workspace cannot disappear between relationship validation and persistence.
- Conversation and Workspace read-modify-write mutations are serialized within one Node.js process through a shared tested mutation-queue primitive, reducing lost-update races in the current local JSON stores.
- Deleting a Workspace through the backend clears saved-conversation Workspace references so the persistence layer does not retain dangling associations.
- Conversation, Workspace and file resource routes require canonical UUID paths rather than accepting arbitrary hex/hyphen identifiers.
- Client-side saved-conversation search across title, selected model and Workspace name.
- Conversation Context surfaces persisted message count plus created/updated timestamps, and history/Workspace/file load failures expose explicit local retry controls so transient control-plane failures are recoverable without reloading the application.
- Conversation deletion now uses an explicit confirmation dialog; history refresh/open/delete failures are surfaced in the sidebar instead of being silently swallowed.
- Streaming follow is user-controlled: scrolling away from the bottom suspends automatic following and exposes a compact jump-to-latest control.
- Text-entry dialogs expose their descriptions to assistive technology and support Escape-key dismissal; confirmation dialogs retain their separate alert-dialog confirmation behavior.
- Text-entry and destructive confirmation dialogs guard asynchronous submissions against duplicate activation; text-entry save failures remain visible in the dialog for retry instead of becoming unhandled UI failures.
- User-controlled local Markdown conversation export containing the visible conversation transcript plus model/Workspace metadata; this browser export is not an Everkeep-governed backup or portability acceptance path.
- Rendered fenced code blocks include a compact copy glyph with accessible success/failure feedback; inline code rendering remains unchanged.
- Fenced code blocks now render a bounded dark code surface with horizontal overflow, visible language labels when Markdown declares a language (and a neutral Code label otherwise), monospaced typography, and clipboard capability detection before copy attempts.
- Every non-welcome conversation message exposes a copy control that reports success or failure with a state glyph, updated accessible label, and polite assistive announcement instead of silently assuming clipboard access.
- Global keyboard handling keeps Ctrl/Command+K conversation search and adds context-aware Escape behavior: an active generation is stopped first, otherwise transient navigation/context panels close; open dialogs retain their own Escape semantics.
- Native Workspaces with editable names, instructions, default model roles, file references, knowledge/tool placeholders and research preferences.
- Fail-closed Workspace create/update validation for supported fields, model-role identifiers, instruction/name bounds, research preference types, and bounded resource-ID collections.
- Workspace resource-ID collections reject duplicate entries before persistence; the UI exposes every Workspace file for management and the context panel remains scrollable for larger attachment sets.
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
- Attachment Workspace context is server-owned: upload Workspace identifiers must be valid existing Workspaces before storage, and Workspace deletion is blocked while file dependencies remain so Wardveil-bound artifact context is not silently rebound.
- Workspace `fileIds` updates are accepted only when every referenced file exists and is owned by that Workspace according to the server file catalog; stale declared IDs are not treated as authoritative deletion dependencies.
- Attachment upload and Workspace deletion share a backend lifecycle queue so an upload cannot validate a Workspace and then race that Workspace's deletion before storage completes.
- Confirmed UI deletion is available for stored files and dependency-free Workspaces; file deletion retains backend extraction/reference cleanup, and Workspace deletion retains dependency and conversation-detachment safeguards.
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
- Exact-head CI for TypeScript checking, explicit syntax validation of every non-test server module, Node tests, production client build, Wardveil reference tests/contract validation and Python compilation.
- JavaScript dependencies are pinned to the exact validated versions in `package.json` and `package-lock.json`; CI and documented Development setup use lockfile-backed `npm ci --include=dev --ignore-scripts` rather than floating `latest` resolution.

## Material limitations

- The new routing components are not wired into the live backend chat route.
- Current Development API bearer handling is not final GoreeCloud Identity/application authorization.
- No authenticated production Wardveil scanner transport is connected.
- No authenticated production Identity, Privacy Shield or GoreeCloud Policy runtime adapter is accepted.
- Native RAG execution remains disabled; indexing, retrieval and model-context eligibility remain false.
- Current conversation/Workspace mutation serialization is process-local and does not replace a production transactional/distributed persistence architecture.
- Current source/CI evidence does not prove real target-host GPU capacity, sustained throughput, all model capabilities, production deployment or Anchor qualification.
