# GoreeCloud AI User Manual

## Status

GoreeCloud AI is under active native development. The current Draft Milestone 0 branch provides the first-party conversational application foundation, backend-owned Ollama access, persistent conversations, model roles, Workspaces, private attachment handling, Wardveil-gated attachment release, quota/deletion controls, bounded passive text extraction, read-only knowledge eligibility, and a bounded non-persistent knowledge-authorization assessment.

It is not Anchor-qualified or production-ready.

## Product Boundary

GoreeCloud AI owns the user-facing AI experience, conversations, Workspaces, files, future knowledge/RAG, research orchestration, tools, artifacts, and model access policy. Ollama is the primary local inference runtime. GoreeCloud Search is the intended first-party current-information and Internet-research provider.

The browser does not call Ollama directly. Model access is routed through the GoreeCloud AI backend so authentication, application authorization, Privacy Shield state, Wardveil enforcement, auditing, cancellation, and future runtime changes can remain server-owned.

The chat endpoint also rejects client-authored `system` messages. Browser chat history may contain only bounded user/assistant messages ending in a user request; Workspace system instructions are resolved and composed by the backend.

## Development Commands

Use Node.js `^20.19.0 || >=22.12.0`. Install the exact locked development toolchain and validate the current source with:

```bash
npm ci --include=dev --ignore-scripts
npm run check
npm run check:server
npm run test:server
npm run build
```

Start the client and backend with the development scripts in `package.json`. Active tokens, credentials, or environment-specific secrets belong in protected runtime configuration and must not be committed to source control.

## Conversations and Models

**Retry and Branch safeguards (Draft source):** Rapid repeated Retry or Branch here clicks are blocked by an in-memory preparation lock until the first operation completes. Create/save errors are shown without discarding the source draft. A late branch completion cannot switch away from a newer selected conversation. Real-browser, Ollama, accessibility, privacy/security and platform acceptance are still pending.


**Historical edit ownership (Draft source):** Each Edit action targets its original conversation and unchanged user message. Changing conversations closes an open edit dialog; if the source no longer matches, branching from the dialog is refused. Escape dismisses an idle dialog only when the IME is not composing text. Dialog fields expose accessible labels. This source-level protection still needs representative browser, CJK IME, screen-reader and privacy/security acceptance.


**Non-destructive historical edits and regeneration (Draft source):** Editing a previously sent user prompt or regenerating an earlier AI answer creates a separate child conversation using messages up to that point. The original conversation and all its later messages remain unchanged, and the original unsent composer draft stays scoped to its parent in browser-tab memory. The new branch automatically requests a response from the selected local model after its initial context is saved. The new conversation retains parent/message lineage. If branch creation or its initial save fails, the original conversation remains available. These Development interactions are not a remote backup, a guarantee against server/storage failures, or evidence of production acceptance. Real-browser, runtime, privacy and accessible-control testing remain pending.


**Find shortcuts:** Ctrl/Command+Shift+F opens search within the loaded conversation. Browser Ctrl/Command+F remains native, and Ctrl/Command+K searches saved conversations. Both the sidebar query and current-conversation message finder reject queries longer than 120 characters or containing more than 16 terms; excess words are never silently ignored. Dialogs and IME composition retain keyboard ownership, including Ctrl/Command+K. No backend search endpoint or cross-conversation message index is created.

**Copy transcript (local clipboard):** Choose Markdown, plain text or JSON in the export format selector, then select Copy transcript to place the selected visible-conversation format on the operating system clipboard. Copying happens only after an explicit button press; clipboard availability varies by browser and secure context. The glyph and screen-reader status report success or failure. Transcripts may contain private messages and may remain available to other applications via the OS clipboard; this is not an authenticated share or backup.

**Conversation outline (local only):** Open Context to see user/assistant turn counts and links to the latest 24 user prompts loaded for this conversation. Select a prompt to scroll and move keyboard focus to its message. Older prompts remain in the transcript and can be found with Find. No server-side search, message index, telemetry, or additional data sharing is created.

**Finder keyboard safety:** Enter and Shift+Enter navigate loaded-message matches, and Escape closes the finder without cancelling an active response. While an input method is composing, Enter/Escape are reserved for the IME. Creating a branch resets the prior conversation's finder state; no cross-conversation search is performed.

**Reuse previous prompts (Draft source):** From a user message, choose the Reuse prompt action to add the full previous user text to your unsent composer draft. It does not edit the saved transcript, replace text you have already typed, submit a request, or call a model. Existing drafts are retained and separated from reused text by a blank line. Reuse is disabled while generation/preparation/selection changes are in progress; an over-limit reuse is rejected with a visible error and does not alter the draft.

**Deletion and navigation safety (Draft source):** Successfully deleting a saved conversation also forgets its unsent browser-tab draft, without deleting other conversations' drafts. While another conversation is loading, the composer, request-producing message actions, transcript export, model/Workspace selection and attachment initiation are temporarily unavailable; a late deletion response does not force the user away from a more recently selected conversation. On reopening a conversation, a restored unsent draft is explicitly announced. This remains a source-only behavior pending representative runtime and accessibility testing.

**Session-local draft isolation (Draft source):** When you select another saved conversation, the current unsent composer text is held only in this browser tab and restored if you return. Starting a new chat restores any unsent new-chat draft in the tab. Starting another new chat while the current new-chat draft is non-empty preserves that draft instead of discarding it. Branching to a new conversation similarly keeps the parent draft scoped to the parent and opens an empty branch composer. The composer is temporarily disabled while a selected conversation is loading. Drafts are not stored on disk or backed up; closing or refreshing the browser tab loses them. Review the restored draft before sending.

**Draft message limit (Draft source):** The composer rejects a message above 250,000 UTF-16 characters before sending, consistent with the backend per-message limit. A character counter appears near the limit. This is a data-size guard, not a token estimate, context-window calculation, or a promise that any model can process the maximum message.

**Role-scoped conversation search (Draft source):** In the loaded-message finder, select All messages, Your messages, or AI responses to narrow matching without searching other conversations. Changing the role resets the active match position; navigation uses only matches within that selected role. Finder query bounds, IME key ownership, and local-only processing remain unchanged.

**Loaded transcript size (Draft source):** Context shows Unicode code-point counts for the loaded user and AI message bodies, excluding the welcome greeting and empty streaming placeholders. This summary stays in browser memory; it is **not** a model-token estimate, a context-window budget, a record of server storage, or a cross-conversation index.

**Find in current conversation:** Open the magnifying-glass control in the top bar to search messages already loaded for the selected conversation. The search matches all words without case or accent differences. Use Previous/Next (or Shift+Enter/Enter) to navigate; Escape closes the finder. IME composition is not treated as a navigation shortcut. This is not a server-side or cross-conversation message index.

**Transcript format:** Choose Markdown, plain text, or JSON beside Download. The exported file includes the visible conversation and model/Workspace metadata. JSON preserves the user/assistant message roles and bodies; Markdown/text normalize metadata labels to avoid forged headings. Files remain on the user's device, may contain private data, and do not constitute Everkeep backup, an import/restore guarantee, or new sharing permission.

The current application supports Ollama model discovery through the backend, friendly GoreeCloud model-role selection, streaming chat responses, stop generation, Markdown/GFM rendering, persistent conversations, rename/edit, retry/recovery, conversation branching with parent lineage metadata, and Workspace association.

Use **Search conversations** in the sidebar to filter saved conversations by title, model, or Workspace name. Search supports multiple words across those fields and accent-insensitive matching; it does not index message bodies. Use the refresh control beside the model picker to re-query installed local models through the GoreeCloud AI backend.

While a response is streaming, GoreeCloud AI follows the latest output until you deliberately scroll away. Scrolling up suspends automatic following; use the down-arrow control to return to the latest message. Stream output is bounded and validated by the backend before it reaches the browser, and the browser applies a second bounded parser. If a completed or manually stopped response cannot be saved, the visible response remains in the session and the interface shows a conversation-save warning instead of reporting the local model runtime as unavailable. If Ollama is reachable but reports no installed models, the runtime status says **No local models** rather than reporting an outage, and the composer explains that an approved local model must be installed before refreshing the list.

The download control exports the current visible conversation to a local Markdown file. Exported title, model, and Workspace labels are escaped as one-line Markdown metadata; message bodies are retained verbatim. This is a user-controlled browser export of the conversation transcript and basic model/Workspace metadata; it is not an Everkeep-governed backup, recovery, or full portability export.

Assistant fenced code blocks include a copy glyph, a visible language label when Markdown declares one (or a neutral Code label), and bounded horizontal scrolling for long lines. Successful and failed copy attempts update the control state and provide a polite accessibility announcement; inline code is unaffected.

Every non-welcome conversation message also includes a copy glyph in its message actions. A successful copy changes to a confirmation glyph; a clipboard failure changes to a warning glyph. Both outcomes update the accessible label and are announced politely to assistive technology.

Keyboard controls include Ctrl/Command+K to open conversation search. Escape stops an active response generation; when no generation is active and no dialog is open, Escape closes the transient navigation and context panels. Dialogs keep their own Escape-to-dismiss behavior.

Switching conversations cancels active response rendering and prevents late tokens or stale conversation loads from overwriting the newly selected conversation. If creating the new conversation fails before generation, the typed prompt remains in the composer and an error is shown for retry.

In the composer, Enter sends a message only when an input method is not composing a character; Shift+Enter inserts a newline. Alt/Ctrl/Command-modified, repeated and IME-owned Enter events do not submit. Model and Workspace selectors are disabled during generation, new-conversation preparation or another selector save. A saved conversation's chosen model or Workspace is presented as applied only after its update succeeds. Failures leave the previous selection visible and show an actionable error. Changing a Workspace's default role is a separate saved operation; if an associated conversation model update then fails, the UI reports that partial outcome. A failed individual chat request no longer marks the entire model-discovery runtime unavailable.

Deleting a saved conversation now opens a confirmation dialog before local removal. If conversation history cannot be refreshed, opened, or deleted, the sidebar keeps a visible error message rather than silently discarding the failure.

The Context panel shows the current saved conversation's message count and its created/updated times. When conversation history, Workspace state, or file listings fail to refresh, the affected surface provides a Retry control so transient local failures can be retried without reloading the entire application.

When a conversation, Workspace, or file request is rejected, the interface can include a short backend-provided reason when one is available. This detail is normalized and length-bounded before display; it is intended for actionable Development feedback rather than raw diagnostic output.

Local conversation, Workspace, file-list, and file-delete browser requests also use bounded client deadlines so a stalled local request returns control to the interface. Attachment uploads use a longer deadline because local file transfer and verification can reasonably take more time.

Text-entry and destructive confirmation dialogs block duplicate submissions while an asynchronous change is in progress. Text-entry save failures remain visible in the dialog so the user can correct or retry the change.

Actual model identifiers remain runtime infrastructure and may change independently of the user-facing role names.

## Workspaces

Workspaces currently persist development state including name, instructions, default model role, file references, knowledge-collection placeholders, tool placeholders, and research preference state. Duplicate resource identifiers in a Workspace update are rejected before persistence.

For a selected Workspace, **Rename** updates its display name and the **Default model role** selector updates the persisted role preference. When the chosen role has a recognized installed local model, GoreeCloud AI selects that model; when no matching model is installed, the UI states that no installed match exists instead of silently substituting one.

**Add instructions** or **Edit instructions** opens the private instruction editor. For each request, the browser sends the selected Workspace ID and the backend resolves the saved Workspace before prepending its instructions transiently as system context. The instructions are not inserted into the persisted conversation transcript, do not authorize tools or data access, and cannot override blocked Identity, Privacy Shield, Wardveil, Policy, knowledge, or external-processing gates.

A selected Workspace can be deleted from its trash control only when it has no file dependencies. Deletion is confirmed before execution. Saved conversations associated with the deleted Workspace are detached rather than deleted. Backend dependency checks remain authoritative if state changes between display and confirmation.

Workspace membership and access boundaries are not yet backed by production GoreeCloud Identity multi-user/session enforcement and GoreeCloud AI application authorization.

## Attachments and Wardveil Trust States

Attachments enter private staging with restrictive local permissions. Storage alone does not make an attachment trusted or eligible for model context.

Current attachment states include:

- **Verified / available** — authoritative Wardveil evidence allowed release and context use for the exact SHA-256-bound artifact;
- **Unverified** — trust could not be established, including when no authenticated scanner transport is configured;
- **Held** — the trust decision requires review;
- **Blocked** — the trust decision requires blocking/quarantine handoff state.

The development application intentionally does not connect directly to ClamAV. Until an authenticated deployed Wardveil Scan transport exists, the scanner adapter remains unconfigured and uploads fail closed in private staging.

## Attachment Quotas and Deletion

The local development attachment library enforces configurable per-file, file-count, and aggregate-byte limits. Local file-store and delete mutations are serialized within one Node.js process. Conversation and Workspace mutations now use the same process-local serialization principle, and attachment upload versus Workspace deletion is serialized at the backend lifecycle boundary to prevent a validated Workspace from disappearing before an upload is committed. This is Development single-process protection, not a distributed transaction model.

Conversation and Workspace JSON stores are also validated when loaded. The Development backend requires the expected store version, canonical stored identifiers and timestamps, bounded record shapes, and unique record IDs; invalid persisted state fails closed rather than being treated as a valid local database.

Deleting a file removes its released or staged bytes, its derived text extraction when present, and stale Workspace file references. This is application cleanup only; it is not Wardveil quarantine, secure erasure, Everkeep retention proof, or proof that no other copies exist.

The file list exposes a trash control with a confirmation step. After a successful delete, the client refreshes both file and Workspace state so removed references disappear from the current context.

Every file associated with the selected Workspace is shown in the context panel rather than only the first few entries. Larger file sets remain manageable through the scrollable context surface.

## Passive Text Extraction

The current post-release extraction boundary accepts only `text/plain`, `text/markdown`, `text/x-markdown`, and `application/json`.

Extraction requires the source attachment to be released and available, with Wardveil `releaseAllowed` and `useAsContextAllowed` state. GoreeCloud AI re-reads and SHA-256 hashes the released bytes before parsing so changed content cannot inherit prior trust evidence.

The parser uses fatal UTF-8 decoding, rejects unsupported control bytes, validates JSON, and applies a dedicated extraction-byte limit. Derived extraction records remain private and retain source/text digests for binding checks.

PDF, HTML, Office documents, archives, scripts/executables, images, audio, video, model artifacts, tool artifacts, and other parser-complex or active formats are not accepted by this initial extraction boundary.

Extraction does **not** authorize chunking, embeddings, indexing, retrieval, RAG participation, model-context use, tool execution, generated-code execution, research, or external processing.

## Knowledge Eligibility Assessment

For an existing attachment, the development API exposes:

`GET /api/files/:id/knowledge-eligibility`

This is a read-only inspection endpoint. It does not create an extraction, chunk data, compute embeddings, index content, retrieve content, insert model context, create authorization state, invoke research, or transfer data externally.

Without a separately supplied authorization assessment, the response reports Wardveil and extraction state while Identity/application authorization and Privacy Shield authorization remain pending. Indexing, retrieval, and model-context stages remain disabled.

Even when Wardveil release and safe extraction are satisfied, the current response keeps all of these false:

- `eligibleForIndexing`
- `eligibleForRetrieval`
- `eligibleForModelContext`

Do not interpret a pending state as approval.

## Knowledge Authorization Assessment

The current development API also exposes:

`POST /api/files/:id/knowledge-authorization-assessment`

This endpoint accepts bounded JSON for **assessment only**. It does not persist an authorization and does not execute a knowledge operation.

### Identity and application authorization

GoreeCloud Identity establishes authenticated identity and approved claims. GoreeCloud AI remains responsible for its own resource/Workspace authorization. The assessment therefore uses application-local operation names rather than inventing GoreeCloud-wide Identity permission scopes:

- `goreecloud-ai.knowledge.index`
- `goreecloud-ai.knowledge.retrieve`
- `goreecloud-ai.knowledge.model-context`

The supplied Identity/application context must include an authenticated actor, valid observation/expiration times, the exact attachment resource ID, and application authorization for the operation being assessed. Future-dated observations, expired/reversed time windows, resource mismatch, and missing operation permission fail closed.

### Privacy Shield decision input

The supplied Privacy Shield request/decision is checked against the current Privacy Shield authorization decision contract. The assessment checks request/decision binding, attachment resource ID, operation, requester/acting-user binding, processing zone, destination, permitted operations, decision expiration, optional request-retention expiration, and obligations. When a request-retention expiration is supplied, it must be a valid date-time or the assessment fails closed.

Outcome handling is preserved:

- `DENY` — blocked;
- `REQUIRE_USER_DECISION` — pending, not approval;
- `ALLOW` — structurally satisfied only when all checked bindings agree;
- `ALLOW_WITH_CONSTRAINTS` — structurally satisfied only when bindings agree, with obligations preserved.

The GoreeCloud AI operation names above are **not** new canonical Privacy Shield capability-registry identifiers.

### Why a satisfied assessment still cannot execute

Even when the supplied Identity/application and Privacy Shield inputs pass the structural checks, the response explicitly says:

- `sourceTrust.productionTrustedInput: false`
- `persistentAuthorizationCreated: false`
- `executionAuthorized: false`

The reason is that authenticated production Identity and Privacy Shield adapters, operation-bound capability/signature verification, durable authorization/evidence state, revocation/replay handling, and target-environment acceptance are not connected. A client-supplied JSON object cannot manufacture production authority.

A structurally satisfied assessment can report `pending_stage_implementation`, but all three knowledge execution eligibility booleans remain false. Privacy Shield `REQUIRE_USER_DECISION` reports `pending_privacy_user_decision`. Identity or Privacy denial remains blocked.

See `docs/KNOWLEDGE-AUTHORIZATION.md`.

## Live Runtime Validation

The repository includes:

```bash
npm run validate:runtime
```

By default the validator targets `http://127.0.0.1:8787`; set `GOREECLOUD_AI_URL` for an approved alternate test endpoint. If the API requires its development bearer, provide `GOREECLOUD_AI_API_TOKEN` in protected runtime configuration.

The validator checks the GoreeCloud AI health endpoint/service identity, reported Wardveil artifact-scanner configuration state, and Ollama model discovery through the GoreeCloud AI backend.

Set `VALIDATE_OLLAMA_MODEL=<installed-model-id>` to additionally send one bounded streamed chat request through the application backend. The validator requires assistant content chunks and a terminal done event but does not print the generated response content.

Set `VALIDATE_REQUIRE_WARDVEIL_SCANNER=true` only when validating an environment that is expected to have an authenticated Wardveil scanner transport. The check fails rather than treating an unconfigured scanner as acceptable evidence.

A passing runtime validation proves only the application/runtime path exercised by that run. It does not establish GoreeCloud Identity, Wardveil, Privacy Shield, Everkeep, Mesh, Glaze UI, deployment, recovery, or Anchor production acceptance.

## Glaze UI Migration State

The current authoritative Official Anchor consumer target is **Glaze V1.7 / 1.7.0** from `GoreeCloud/glaze`. Existing older Glaze UI and 2.x-labeled source is historical migration input and does not establish current conformance. GoreeCloud AI remains migration/reconciliation-required until its interface completes application-specific exact-revision 1.7.0 conformance/acceptance. Design-system promotion does not automatically promote this application.

## Privacy and External Processing

Privacy Shield remains authoritative for whether conversation, attachment, extracted, knowledge, or research data may be used for a purpose, retained, sent to a model, searched, or transferred externally. The structural assessment preserves Privacy Shield decisions but is not an authenticated Privacy Shield enforcement adapter.

GoreeCloud Search research integration and external-processing disclosure are not yet production-accepted. A Search outage must eventually remain isolated from local conversations and local knowledge workflows.

## Recovery and Portability

Everkeep remains authoritative for conversation/Workspace export, backup, restore, portability, preservation, retention, recovery evidence, continuity, and succession. Current local persistence and deletion behavior do not establish Everkeep recovery acceptance, including for future derived knowledge state.

## Current Acceptance Gaps

The Draft branch still requires, among other evidence:

- live authenticated Ollama interoperability evidence in the intended environment;
- a deployed authenticated Wardveil scanner transport, scanner/signature health, and controlled clean/malicious runtime validation;
- authenticated GoreeCloud Identity-backed multi-user/session boundaries plus GoreeCloud AI resource/Workspace authorization;
- authenticated Privacy Shield enforcement, operation-bound capability/evidence verification, and runtime data-use acceptance;
- Everkeep application lifecycle and recovery acceptance;
- GoreeCloud Mesh integration where required;
- additional safe parser decisions before broader ingestion;
- actual provenance/chunking/embeddings/indexing/retrieval/RAG/model-context execution with permission and privacy enforcement;
- migration/reconciliation to Glaze V1.7 / 1.7.0 and exact current consumer conformance evidence;
- deployment and broader production-readiness validation.

Do not represent successful source checks, a knowledge-eligibility/authorization assessment, or local runtime validation as Anchor or production-ready evidence.
