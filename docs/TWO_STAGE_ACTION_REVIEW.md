# GoreeCloud AI — Two-Stage Local Action Review

**Development-only. Nothing in this feature authenticates an approval, sends a real connector request, or performs external effects.**

## Draft, then review, then reserve

`reference/local_review_lifecycle.py` provides two separate stages. `draft_local_review` uses the trusted-scoped, loopback Ollama proposal parser, checks the exact expected resource, the restricted backend input contract, and the pinned connection/requirement revision. It creates a short-lived review state associated with the trusted Identity context. **No Policy grant, approval, or replay reservation is created during drafting.** A user can therefore inspect a write operation *before* deciding whether to consent.

`ReviewDraft.display()` exposes the actual service, operation, target resource, risk and copied argument values for an authenticated review UI. This disclosure can contain sensitive user information: never send it to the model, persist it in logs, or expose it in a public URL. The function returns a detached copy to avoid accidental UI mutation.

`reference/local_review_html.py` produces a responsive, semantic, script-free, read-only local HTML example, escapes HTML-sensitive characters, renders invisible Unicode as JSON escapes, and declares a restrictive Content Security Policy. It contains **no functional approval button**. It is a useful engineering reference, **not** a deployed or visually validated Glaze interface.

After review, the caller obtains a **new, independently verified** Identity/Policy/approval decision from a trusted backend, bound to the precise action and user/session. `reserve_reviewed_action` rechecks review lifetime, identity and action fingerprint, input schema, connection pinning and the existing authorization gate; only then does it attempt the atomic SQLite replay reservation. It returns a redacted `reserved_no_execution` result, not an execution permit. An altered payload, expired review, reused request ID, changed connection, denied Policy or missing write approval fails closed.

## Production conditions

The review fingerprint is a consistency hash, **not** a cryptographic signature or authenticated issuer attestation. The `ReviewDraft` object must remain internal to a trusted backend session, never be accepted from model/client-controlled JSON as an authorization token. Actual Glaze consent must display exact service, target, intended changes, data disclosure, irreversibility and identity, with an accessible cancel path. The future issuer must record a durable, tamper-evident approval, support expiry and revocation, and bind that approval to one exact action and the right tenant/session. Independent execution-time reauthorization, production replay/idempotency/recovery, isolated service transports, output sanitation, real installed Ollama/provider testing, visual/accessibility testing, review and release gates remain outstanding.

The current UI view is an inert demo, the database is a non-production reference, and the full capability stack remains draft/unmerged/undeployed.
