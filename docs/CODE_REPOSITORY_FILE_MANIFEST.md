# GoreeCloud Code Repository File Manifest

## Status

This is a source-level Development integration between GoreeCloud AI and GoreeCloud Code. It extends the read-only repository-context bridge with bounded path discovery. It does not establish production deployment, repository-write authority, code-execution authority, GoreeCloud Identity acceptance, or GoreeCloud Mesh transport.

## Purpose

GoreeCloud AI needs a safe way to identify which repository file it should request without receiving an entire repository tree or directory contents as source text. GoreeCloud Code therefore exposes one root or directory-scoped provider-neutral manifest at one exact ref.

The manifest contains metadata only. File contents remain behind the separate explicit file-context contract.

## Contract

Current contract version: `0.1.0`.

The accepted envelope binds:

- repository owner and name;
- repository identifier;
- exact ref;
- exact directory path, with the empty path representing repository root;
- generation time;
- healthy provider evidence with `repositories:read`;
- at most 128 direct child entries;
- entry name, path, type, size, and object SHA;
- explicit truncation state; and
- bounded HTTP(S) evidence links.

The consumer validates that every entry is a direct child of the requested directory, rejects duplicate or malformed paths, rejects unexpected fields, and fails closed if GoreeCloud Code exposes a common credential-bearing path that should have been filtered.

## Trust and minimization boundary

Accepted path metadata remains untrusted repository data. A file name or directory name can contain misleading instructions and does not authorize any action.

The manifest does not contain file content, clone/SSH URLs, provider credentials, provider-specific child URLs, hidden-secret counts, or repository mutation authority.

Common credential-bearing paths such as live `.env` variants, private-key containers, and common service-account credential files are excluded. Templates such as `.env.example` remain eligible.

## Query-aware selection

`reference/repository_file_manifest_selection.py` can rank an accepted direct-child manifest against a user query. Selection is deterministic, limited to twenty results, and uses names/paths only. It does not fetch files or widen scope.

Directory traversal remains explicit: selecting a directory requires a separate manifest request for that exact directory path; selecting a file requires a separate file-context request for that exact file path.

## Failure behavior

Malformed, stale, mismatched, over-limit, duplicate, out-of-scope, non-direct-child, sensitive-path, or unavailable manifest data returns no accepted context. No previous manifest is silently reused.
