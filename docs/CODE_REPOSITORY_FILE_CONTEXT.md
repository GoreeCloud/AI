# GoreeCloud Code Repository File Context

## Status

This is a source-level Development integration between GoreeCloud AI and GoreeCloud Code. It extends the existing repository snapshot bridge with explicit, bounded file evidence. It does not establish production deployment, repository-write authority, code-execution authority, GoreeCloud Identity acceptance, or GoreeCloud Mesh transport.

## Purpose

Repository-aware assistance often needs exact source text, but GoreeCloud AI should not connect directly to Forgejo or receive provider credentials. GoreeCloud Code therefore remains the provider-facing evidence broker and exposes one explicitly requested previewable UTF-8 file at one explicit ref.

The consumer boundary in `reference/code_repository_file_context.py` verifies the envelope before the returned file text may enter AI reasoning context.

## Contract

Current contract version: `0.1.0`.

The accepted envelope binds:

- repository owner and name;
- repository identifier;
- exact ref;
- exact path;
- generation time;
- healthy provider evidence with `repositories:read`;
- bounded file metadata;
- UTF-8 file text capped at 65,536 characters;
- provider object SHA;
- SHA-256 digest of the complete previewable file content before AI-specific text truncation;
- truncation state; and
- bounded HTTP(S) evidence links.

When `truncated` is false, the AI consumer recomputes SHA-256 over the received UTF-8 text and requires an exact digest match. When `truncated` is true, the digest remains upstream evidence for the complete previewable file content, while the consumer verifies that the returned excerpt exactly fills the declared 65,536-character budget.

## Trust and authorization boundary

Accepted file text remains untrusted repository data. Structural acceptance does not authorize code execution, shell execution, tool use, repository mutation, review actions, secret access, or policy changes.

The consumer rejects credential-bearing envelope fields and independently blocks common credential-file paths such as live `.env` variants, private-key containers, and common service-account credential files. Template files such as `.env.example` remain eligible for source reasoning.

The path blocklist is defense in depth, not a complete secret scanner. Production use still requires the applicable Wardveil Security, Privacy Shield, Identity, Policy, and transport controls.

## Failure behavior

The intake fails closed on malformed or stale records, repository/ref/path mismatch, unhealthy providers, missing read capability, unexpected fields, invalid evidence URLs, invalid limits, digest mismatch for complete content, invalid truncation state, sensitive envelope keys, blocked file paths, or unavailable transport.

No previous repository snapshot or file context is silently reused after a failed intake.
