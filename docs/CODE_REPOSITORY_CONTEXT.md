# GoreeCloud Code Repository Context

## Status

This is a source-level Development integration between GoreeCloud AI and GoreeCloud Code. It does not establish production deployment, GoreeCloud Identity acceptance, GoreeCloud Mesh transport, or permission for AI-assisted repository writes.

## Purpose

GoreeCloud AI should understand repositories through GoreeCloud Code rather than connecting directly to Forgejo or another backing forge. GoreeCloud Code remains responsible for provider access and produces a provider-neutral, bounded snapshot.

The consumer boundary in `reference/code_repository_context.py` verifies that snapshot before it may enter AI reasoning context.

## Trust model

The GoreeCloud Code envelope is an evidence broker record, not repository authority. The backing source-control provider remains the observed repository authority.

Even after structural acceptance, repository-controlled text is **untrusted repository content**. Commit messages, issue titles, pull-request titles, descriptions, branch names, and identities can contain adversarial or misleading instructions. They must be treated as data and never as system policy, tool commands, or authorization.

A valid repository context is **not an execution authorization** and is not write authorization.

## Acceptance checks

The GoreeCloud AI intake fails closed unless all applicable checks pass:

- contract version `0.1.0` and `repository_context` record type;
- exact GoreeCloud Code producer identity and non-authoritative broker role;
- exact repository owner/name and optional ref binding;
- repository ID agreement between scope and payload;
- healthy source provider with `repositories:read` capability;
- context generated no more than five minutes ago and not future-dated;
- no credential-like or secret-bearing keys anywhere in the envelope;
- no provider-specific repository fields outside the explicit safe contract;
- each branch/commit/issue/pull-request collection remains within the declared limit and the hard maximum of 20;
- evidence links use HTTP or HTTPS; and
- no unexpected top-level or nested contract fields.

Unavailable transport, malformed data, stale data, mismatched scope, or failed evidence returns no usable context.

## Transport boundary

GoreeCloud AI does not receive Forgejo credentials. The initial GoreeCloud Code endpoint uses an interim Development server-to-server bearer on the Code side. Production transport should move to GoreeCloud Identity and GoreeCloud Mesh while preserving GoreeCloud Code application authorization and appropriate Privacy Shield, Wardveil Security, policy, observability, and recovery evidence.

The Python consumer intentionally depends on a `GoreeCloudCodeContextProvider` protocol rather than a Forgejo client. This keeps transport replaceable and prevents the AI product from coupling to backing provider APIs.

## Future work

Repository file content, diffs, code search, write operations, review actions, pipeline execution, and agentic changes require separate contracts and authorization. They must not be inferred from this read-only context bridge.
