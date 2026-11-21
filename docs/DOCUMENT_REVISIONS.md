# GoreeCloud AI — opt-in local document revisions

**Status:** Developer preview. This is not deployed, tenant-isolated or certified secure erasure.

## Consent and retention

Documents are stored in the configured local SQLite database, plaintext by default
unless optional SQLCipher is configured and validated. On PUT updates,
record_revision defaults to false. Only an explicitly opted-in save of changed
content snapshots the **previous saved title and body**, never unsaved editor text.
Creation, unchanged updates, and ordinary edits create no history by default.
The 20 newest revisions per document are retained. Older rows are pruned only
on new snapshots and approved restores, and their content may persist in database
pages, exported copies or backups. Parent-document deletion cascades through
live history, but is not secure erasure.

## Protected API

- PUT /api/v1/documents/{document_id} accepts record_revision: boolean (default false).
- GET /api/v1/documents/{document_id}/revisions lists up to 20 metadata rows (read scope).
- GET /api/v1/documents/{document_id}/revisions/{revision_id} reads one body (read scope).
- POST /api/v1/documents/{document_id}/revisions/{revision_id}/restore requires
  an explicit JSON approved=true and write scope. An atomic transaction
  preserves the displaced saved content as an undo snapshot.
- All routes require the configured single-owner token or approved OIDC
  signed-owner token. There is no cloud provider contact or agent execution.

The React editor exposes a per-save opt-in checkbox, metadata list, read-only
preview, and separate confirmation to restore. Native Linux/Android history
editing parity remains pending. Historical content is untrusted reference text.

## Development-only verification

Use the locked and already documented CLI commands in the canonical
Google Drive directory GoreeCloud/CLI Commands/GoreeCloud/AI.md:

    cd server
    uv sync --locked --extra dev --extra sqlcipher --python 3.12
    uv run --locked --extra dev --extra sqlcipher pytest -q
    uv run --locked --extra dev --extra sqlcipher ruff check app tests ../tools

    cd web
    npm ci --ignore-scripts --no-audit --no-fund
    npm run build

The tests use synthetic local data; no production migration, real key custody,
paid inference, deployment, or user-device qualification is established.
