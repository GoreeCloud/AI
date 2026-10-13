# Read-only repository intelligence briefs

## Development status

This first-party, source-only adapter extends the accepted GoreeCloud Code repository-context intake with short, ranked, citation-addressable evidence previews. It is **not wired into live conversations** and does not establish production Identity, Privacy Shield, Policy, Mesh, or release acceptance.

## Interface

`reference/repository_context_brief.py` exposes `build_repository_brief(intake, query, limit=8)`. It consumes only a previously accepted `RepositoryContextIntakeResult`, uses the existing bounded query-aware selector, and returns a structured `RepositoryContextBrief` with an `as_dict()` representation.

Every returned item has a deterministic `citation_id`, item kind/key, excerpt, sanitized HTTP(S) evidence link, attribution scope, score, and explicit `untrusted_repository_data` classification. Repository and branch results disclose that their link is only a repository-level fallback, not direct item-level evidence.

## Safety properties

- No provider calls, file reads, network operations, model calls, repository mutations, or tool dispatch occur in this module.
- A rejected context, elevated write/execute flags, missing provenance, or invalid bound fails closed.
- Up to eight selected items, each with a 280-character preview; no response is fabricated for an unmatched query.
- Embedded controls, bidirectional-format characters, and multiline spoofing are removed from previews; text remains untrusted and is never promoted to instructions.
- Credential-bearing, malformed, and unsafe navigation links are omitted. Query strings and fragments are removed from accepted display links so token-like parameters are not included in output.
- No access is inferred from snapshot acceptance. An actual AI request must independently pass future authenticated user/resource scopes, consent/policy and provider-authority checks before these previews are exposed.

## Verification

Run `python3 scripts/test_repository_context_brief.py` and `python3 scripts/test_code_repository_context.py`. The repository validation workflow runs both suites and compiles the additional adapter/test sources.

## Remaining gates

Application integration, authenticated GoreeCloud Code transport, private-repository permissions, user-visible citations and safe navigation, accessibility/Glaze consumer acceptance, representative end-to-end tests, independent security review, current-head CI and rollback evidence remain outstanding. Keep development changes in Draft review until those gates are met.
