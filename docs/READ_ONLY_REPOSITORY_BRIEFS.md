# Read-only repository intelligence briefs

## Development status

This first-party, source-only adapter extends the accepted GoreeCloud Code repository-context intake with short, ranked, citation-addressable evidence previews. It is **not wired into live conversations** and does not establish production Identity, Privacy Shield, Policy, Mesh, or release acceptance.

## Interface

`reference/repository_context_brief.py` exposes `build_repository_brief(intake, query, now=None, limit=8)`. It consumes only a sealed, previously accepted `RepositoryContextIntakeResult`, rechecks the original repository/ref scope and the preserved caller-specific snapshot freshness window (up to a five-minute maximum) at use time, uses the existing bounded query-aware selector, and returns a structured `RepositoryContextBrief` with an `as_dict()` representation. Tests inject a fixed `now`; actual calls use the current UTC time.

Every returned item has a deterministic `citation_id`, item kind/key, excerpt, sanitized HTTP(S) evidence link, attribution scope, score, and explicit `untrusted_repository_data` classification. Repository and branch results disclose that their link is only a repository-level fallback, not direct item-level evidence.

## Safety properties

- No provider calls, file reads, network operations, model calls, repository mutations, or tool dispatch occur in this module.
- A rejected context, elevated write/execute flags, missing provenance, or invalid bound fails closed.
- A positive caller-selected freshness window at most five minutes is required and preserved through brief generation; an invalid or overly broad limit is rejected, not silently replaced with the default.
- The intake captures a SHA-256 fingerprint of canonical JSON snapshot bytes and retains the original requested repository/ref. Briefing clones the snapshot, checks its fingerprint, and re-runs source/scope/freshness validation against that original target; tampering or expired evidence fails closed.
- The fingerprint is a process-local mutation-detection mechanism, **not cryptographic authentication of GoreeCloud Code**, an authorization credential, or proof that input content is trustworthy. Authenticated Identity/Code transport remains a separate mandatory gate.
- Up to eight selected items, each with a 280-character preview; no response is fabricated for an unmatched query.
- Embedded controls, bidirectional-format characters, and multiline spoofing are removed from previews; text remains untrusted and is never promoted to instructions.
- Credential-bearing, malformed, and unsafe navigation links are omitted. Query strings and fragments are removed from accepted display links so token-like parameters are not included in output.
- No access is inferred from snapshot acceptance. An actual AI request must independently pass future authenticated user/resource scopes, consent/policy and provider-authority checks before these previews are exposed.

## Verification

Run `python3 scripts/test_repository_context_brief.py` and `python3 scripts/test_code_repository_context.py`. The repository validation workflow runs both suites and compiles the additional adapter/test sources.

## Remaining gates

Application integration, authenticated GoreeCloud Code transport, private-repository permissions, user-visible citations and safe navigation, accessibility/Glaze consumer acceptance, representative end-to-end tests, independent security review, current-head CI and rollback evidence remain outstanding. Keep development changes in Draft review until those gates are met.
