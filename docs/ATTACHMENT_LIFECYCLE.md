# GoreeCloud AI Attachment Lifecycle

GoreeCloud AI owns the attachment lifecycle around the Wardveil artifact trust boundary. Storage success, security release, extraction, knowledge-eligibility observation, authorization assessment, indexing, context use, retention, and deletion are separate state transitions.

## Current development flow

```text
upload request
  -> development quota checks
  -> serialized local file mutation
  -> private 0600 staging
  -> SHA-256 / Wardveil trust gate
  -> released or retained staged
  -> metadata index
  -> optional Workspace reference
  -> explicit passive-text extraction eligibility gate
  -> digest recheck
  -> private extracted-text record
  -> read-only knowledge-eligibility assessment
  -> optional non-persistent Identity/application + Privacy Shield input assessment
  -> indexing / retrieval / model context remain disabled
```

The Wardveil rules documented in `WARDVEIL_ARTIFACT_SECURITY.md` remain authoritative for trust release. Quotas never turn unverified content into clean content, extraction never upgrades Wardveil state, eligibility/authorization assessments never create execution authority, and deletion never becomes Wardveil Quarantine.

## Storage limits

The development server enforces independent limits for attachment size, file count, aggregate stored bytes, and passive text extraction:

- `MAX_FILE_BYTES` — maximum bytes for one attachment;
- `MAX_FILE_COUNT` — maximum number of attachment records in the local library;
- `MAX_TOTAL_FILE_BYTES` — maximum aggregate attachment bytes recorded by the local library; and
- `MAX_TEXT_EXTRACTION_BYTES` — maximum source bytes permitted through the initial passive-text extraction gate.

The count and aggregate limits are checked before staging when enough request metadata is available and are enforced again while streaming. Quota rejection uses HTTP 507 and removes any partially staged file.

These are local safety limits, not final per-user, per-Workspace, tenant, billing, privacy, or retention policy. Production quota policy requires identity-aware storage accounting and shared persistence.

## Mutation serialization

The JSON-file development adapter serializes file-store and file-delete mutations within one Node.js process. This prevents two local mutations from racing the quota calculation or overwriting the file index.

This is not a distributed lock. Multiple application processes or hosts require a production persistence layer with transactional quota accounting and concurrency control before production acceptance.

## Safe text extraction foundation

`POST /api/files/:id/extraction` is the first bounded post-release content-processing boundary. It is available only when the attachment record is `available`, bytes are in `released` storage, Wardveil release is allowed, and the Wardveil decision explicitly allows context use.

The initial parser allowlist is deliberately narrow: `text/plain`, `text/markdown`, `text/x-markdown`, and `application/json`.

PDF, HTML, Office documents, archives, scripts, executables, images, audio, video, models, tools, and other active or parser-complex formats are not accepted by this boundary. They require separately reviewed parsing/sandbox/content-policy controls.

Immediately before extraction, GoreeCloud AI hashes the released bytes again and requires the SHA-256 digest to match the attachment record that was bound to accepted Wardveil evidence. The bytes must then pass fatal UTF-8 decoding and a restrictive control-character check. JSON must parse successfully before normalized text is written.

Extracted content is stored under the application data directory as a private mode-0600 JSON record containing the source resource ID/digest, media type, extracted-text digest, bounded size metadata, state, timestamp, and extracted text. `GET /api/files/:id/extraction` returns the stored extraction only while its source digest remains bound to the current attachment record.

This is extraction only. It does not establish chunking, embeddings, indexing, retrieval, RAG participation, Workspace permission filtering, model-context authorization, provenance display, external processing, or Privacy Shield authorization.

## Read-only knowledge-eligibility assessment

`GET /api/files/:id/knowledge-eligibility` inspects prerequisites without mutating file, extraction, knowledge, authorization, or model state.

The assessment evaluates Wardveil release/context use, parser/extraction binding, Identity/application-authorization state, Privacy Shield state, and whether indexing/retrieval/model-context stages are enabled.

Without supplied authorization assessment, local security/extraction prerequisites may reach `pending_authorization`, but the current source always returns `eligibleForIndexing: false`, `eligibleForRetrieval: false`, and `eligibleForModelContext: false`.

## Non-persistent knowledge authorization assessment

`POST /api/files/:id/knowledge-authorization-assessment` accepts bounded assessment input for one GoreeCloud AI application-local knowledge operation and combines it with the current attachment/extraction gates.

GoreeCloud Identity input is separated from GoreeCloud AI application authorization: authenticated actor/claim context alone does not grant resource use. The assessment requires explicit application authorization bound to the exact attachment resource and operation.

Privacy Shield input follows the current decision request/response fields. Resource/operation/request binding, acting-user/requester binding, processing zone, destination, permitted operation, obligations, and expiry are checked. `DENY` blocks and `REQUIRE_USER_DECISION` remains pending.

Even when the supplied Identity/application and Privacy inputs are structurally satisfied, the result remains explicitly untrusted for production execution because authenticated runtime adapters/capability verification are absent. It creates no persistent authorization and cannot enable indexing, retrieval, or model context.

See `KNOWLEDGE-AUTHORIZATION.md` for the detailed boundary.

## Deletion

Deleting an attachment first removes any derived text extraction and then removes both possible byte locations:

- released attachment storage; and
- private Wardveil staging.

After byte/index deletion, the API removes that file ID from persisted Workspace `fileIds` arrays. Workspace reference cleanup is metadata cleanup only; it is not malware quarantine, secure erasure, an Everkeep retention action, or proof that copies do not exist elsewhere.

Everkeep backup/recovery, legal retention, succession, export, and restore semantics remain separate future integrations. The current deletion behavior is not an Everkeep lifecycle-acceptance claim.

## Trust, privacy, and active-use boundaries

A released clean attachment may become eligible for safe context-oriented processing only where the Wardveil decision explicitly allows it. Security release does not itself authorize parsing with unsafe libraries, executing embedded content, loading a model, running code, installing a tool, or publishing data externally.

Privacy Shield remains authoritative for whether extracted content may be used for a declared purpose, retained, sent to a model, transferred externally, or included in another processing flow. Structural consumption of a supplied Privacy Shield decision is not authenticated runtime enforcement.

GoreeCloud Identity remains authoritative for production identity/claims, while GoreeCloud AI owns its own user/Workspace/resource authorization. The development API bearer is not production Identity or application authorization.

File provenance, chunking, indexing, permission filtering, RAG participation, active-content policy, authenticated Privacy Shield capability/evidence verification, external-processing disclosure, and Everkeep treatment remain separate gates.
