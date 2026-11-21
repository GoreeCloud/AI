# Offline encrypted backup and restore (development preview)

GoreeCloud AI includes a **CLI-only, offline** SQLite backup utility.
It encrypts a coherent SQLite snapshot with AES-256-GCM, random 96-bit nonce
and authenticated version header. It stores no key in the repository, archive
or logs and refuses to overwrite outputs or existing restore databases.

These are source-level controls exercised with synthetic data. They do not
encrypt the live SQLite database, memory, WAL files, backups from unrelated
tools, cloud-provider content or disk blocks. Never claim secure erasure.

## Preconditions

- Operate on a trusted private host with filesystem permissions no broader
  than necessary. Keep output files and detached keys in separate locations.
- Supply the 32-byte random encryption key through a secret manager as a
  base64 process-only GOREECLOUD_AI_BACKUP_KEY environment value. Never paste
  keys into chat, GitHub, Drive, recorded CI logs or command-line arguments.
- Run from the locked server environment (uv sync --locked --extra dev --python 3.12).
- Backup key loss makes restoration impossible; test isolated recovery.

## Create an encrypted snapshot

    cd server
    uv run --locked python -m app.backup backup \
      --source ./data/ai.sqlite3 \
      --output /path/to/private-backup/goreecloud-ai.gcai

## Restore to a new private path

    cd server
    uv run --locked python -m app.backup restore \
      --source /path/to/private-backup/goreecloud-ai.gcai \
      --output /path/to/isolated-restore/ai-restored.sqlite3

Restore validates AEAD and SQLite PRAGMA quick_check; verify important records
in an isolated test deployment before depending on recovery. Existing target
databases are never overwritten. Practice key rotation, restore and off-host
backup policies before promoting this to critical data use.

## Retention and secure deletion limitations

- GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS=0 (default) disables expiration.
  Configure 1-3650 days for a chosen saved-conversation horizon.
- Authenticated POST /api/v1/privacy/purge-expired with approved=true removes
  expired snapshots and cascading message rows. This is explicitly approved
  owner action, not a scheduler.
- SQLite freed pages, OS storage, old encrypted backups and external cloud
  copies may retain data; row deletion is not cryptographic erasure.

## Identity and cloud budget

GOREECLOUD_AI_AUTH_MODE=oidc disables the preview-token fallback and requires
a trusted HTTPS issuer, resource audience, exact owner subject, scope and local
mode-0600 JWKS JSON. The verifier accepts only RS256 signatures and validates
token times, issuer, audience, owner and scope. It does **not** verify actual
GoreeCloud Identity issuer integration, handle sessions, OIDC discovery,
delegated per-route scopes or multi-tenant authorization.

GOREECLOUD_AI_REQUIRE_CAPPED_OPENROUTER_KEY=true fails closed before cloud
inference unless the pinned provider GET /api/v1/key endpoint reports a positive
per-key credit limit and remaining balance. The lookup does not reserve
real model charges and cannot independently impose a hard dollar ceiling;
provider-side spending controls enforce their own caps. BYOK and concurrent
requests require separate evaluation. Configure OpenRouter key guardrails in
the provider account; do not infer any cap is configured merely from code.

**No public deployment:** Identity, GoreeShield, Wardveil, Mesh, TLS ingress,
real provider testing, billing, and end-to-end recovery remain pending.
