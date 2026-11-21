# Local encryption, offline migration, backup and recovery (development preview)

**Source-tested, NOT deployed or production accepted.** The default storage is
plaintext SQLite/FTS5 for compatibility. An optional locked `sqlcipher3`
dependency allows SQLCipher to encrypt the **entire local database**, including
document text, saved chats, consent receipts, counters and FTS5 indexes, when
the operator explicitly configures `GOREECLOUD_AI_DB_MODE=sqlcipher` and a
separately managed 32-byte base64 `GOREECLOUD_AI_DB_KEY`.

SQLCipher does **not** encrypt application memory, API responses, prompts sent
to cloud models, unencrypted old source files, OS swap, other backups, external
logs or processes. These controls do not prove GoreeShield policy integration,
full secure deletion, safe key custody or a real deployed recovery plan.

## Prerequisites and key management

- Work only on a trusted, private host. **Stop all API writers** and maintain
  an independently verified encrypted offline backup before migration.
- Use `cd server && uv sync --locked --extra dev --extra sqlcipher --python 3.12`
  on the authorized development host. The optional source-reviewed Python
  binding bundles SQLCipher Community Edition; check provenance, notices,
  wheel compatibility and runtime behavior on the actual deployment host.
- Supply `GOREECLOUD_AI_DB_KEY` and `GOREECLOUD_AI_BACKUP_KEY` as **different**
  independently random 32-byte base64 keys from an approved secret manager.
  Do not put values into command arguments, shell history, code, logs, GitHub,
  Google Drive, chat or test fixtures. Securely protect recovery keys off-host.
- A wrong or missing encryption key or storage-mode mismatch fails closed.
  `GOREECLOUD_AI_DB_MODE=plaintext` remains the default; SQLCipher is opt-in.

## Offline plaintext-to-SQLCipher migration (non-overwriting)

Perform on a **stopped** API with the original private 0600 database and no
SQLite WAL sidecar (safely checkpoint/stop first, never delete an active WAL).
After checking a complete offline backup and keys, run the migration into a
**new** private database pathname:

    cd server
    uv run --locked --extra sqlcipher python -m app.migrate_sqlcipher \
      --source /path/to/private-original/ai.sqlite3 \
      --output /path/to/private-encrypted/ai.sqlite3

The command refuses any existing target, uses an exclusive private scratch
file, verifies SQLCipher integrity and schema version, and publishes by a
non-overwriting filesystem link. The original plaintext DB is **kept** for
owner-controlled backup/retention and a possible rollback. Validate the
encrypted database and FTS search with synthetic or approved private test
data **before** configuring its path on the API. Then configure:

    GOREECLOUD_AI_DB_MODE=sqlcipher
    GOREECLOUD_AI_DB_PATH=/path/to/private-encrypted/ai.sqlite3

The above are config **names and illustrative path placeholders**, not commands
to paste a key or claims about a running deployment. If migration fails, the
original must remain untouched and the API should continue using its verified
original configuration. Explicitly manage the old plaintext database, WAL
files, backups and snapshots under a tested retention/erasure process; no
automatic shredding, WAL deletion or data loss is authorized.

## Offline SQLCipher key rotation (non-overwriting)

Once SQLCipher is explicitly active, rotate its 32-byte database key without
rewriting an active DB in place. **Stop every API writer**, verify a complete
offline backup and an isolated restore, and maintain the existing separate
`GOREECLOUD_AI_DB_KEY`. Supply a **distinct** `GOREECLOUD_AI_NEW_DB_KEY` as
a random 32-byte base64 value from the authorized secret manager. Never put
either key in command arguments, history, GitHub, Drive or logs.

    cd server
    uv run --locked --extra sqlcipher python -m app.rotate_sqlcipher \
      --source /path/to/private-encrypted/ai.sqlite3 \
      --output /path/to/private-rotated/ai.sqlite3

The operation requires SQLCipher mode, refuses a missing/equal/wrong key,
unsafe source/destination permissions, live WAL sidecar, a plaintext source,
and an existing output path. It uses a private scratch file, encrypted-to-
encrypted `sqlcipher_export`, a new key, integrity/schema checks, a
non-overwriting publish, and source preservation. It does not delete old
ciphertext, old database keys or historical backups. Validate encrypted FTS
search and saved data under the **new** key in an isolated test deployment,
then separately cut over `GOREECLOUD_AI_DB_PATH` and `GOREECLOUD_AI_DB_KEY`
under a reversible operating plan. Older SQLCipher snapshots still need the
**old** database key plus their backup key, until retired under verified
retention and recovery policy. Re-encrypt new backups and test off-host
restoration before revoking the original key. No production key custody or
rotation has been performed.

## CLI-only encrypted snapshot

The offline backup utility encrypts a coherent SQLite snapshot using an
independent AES-256-GCM key, random nonce and authenticated version marker.
In SQLCipher mode its temporary SQLite snapshot is **also SQLCipher-encrypted**,
so the backup directory never needs a plaintext intermediate DB. The original
plaintext mode remains supported with an ephemeral private plaintext snapshot.

    cd server
    uv run --locked --extra sqlcipher python -m app.backup backup \
      --source ./data/ai.sqlite3 \
      --output /path/to/private-backup/goreecloud-ai.gcai

## Non-overwriting isolated restore

Set the appropriate same DB mode, database key (for SQLCipher) and independent
backup key in the secure process environment before restoration. The archive
version records the source storage mode; restoring with the wrong mode is
refused rather than silently downgrading encryption.

    cd server
    uv run --locked --extra sqlcipher python -m app.backup restore \
      --source /path/to/private-backup/goreecloud-ai.gcai \
      --output /path/to/isolated-restore/ai-restored.sqlite3

Restore authenticates AES-GCM and validates SQLite/SQLCipher integrity and
GoreeCloud AI schema before atomically publishing a new private target.
It never overwrites a working database. Verify important records and local
FTS5 search in an isolated service before depending on the restored file.
The independent backup and DB keys are **both** required to recover a
SQLCipher-mode snapshot. Loss of either key loses recoverability. A backup
or restore test on synthetic data is not an off-host recovery certification.


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
a verified GoreeCloud Identity issuer, provider sessions or multi-tenant
authorization. Source-only optional per-route capability checks are available
with GOREECLOUD_AI_OIDC_ENFORCE_CAPABILITY_SCOPES=true. In this mode a signed
token must still have the existing owner subject and baseline required owner
scope, **plus** the route scope:
- goreecloud.ai.read: model/document/library metadata, retrieval search,
  local export and preview/privacy status
- goreecloud.ai.write: create/edit/delete documents and saved chats, import
- goreecloud.ai.inference: chat, stream, agent plan and local document Q&A
- goreecloud.ai.cloud: additionally required whenever inference selects
  OpenRouter or a paid image call is made
- goreecloud.ai.paid: paid image generation (also requires cloud capability,
  per-image approval and provider budget preflight)
- goreecloud.ai.tools: approved agent document reads and MCP discovery/calls
- goreecloud.ai.admin: retention deletion and consent-receipt clearing

The source checks exact space-delimited OAuth scope claims from the pinned
RS256 JWT. Unknown protected routes fail closed when strict mode is enabled.
This is **not** an end-to-end delegated Identity issuer/session contract; the
single-owner subject still governs every request. The flag is opt-in to avoid
breaking current developer-owner clients; it should be evaluated and explicitly
enforced before any production integration. Cloud permission does not replace
per-request content consent, and paid permission does not replace approval.

GOREECLOUD_AI_REQUIRE_CAPPED_OPENROUTER_KEY=true fails closed before cloud
inference unless the pinned provider GET /api/v1/key endpoint reports a positive
per-key credit limit and remaining balance. The lookup does not reserve
real model charges and cannot independently impose a hard dollar ceiling;
provider-side spending controls enforce their own caps. BYOK and concurrent
requests require separate evaluation. Configure OpenRouter key guardrails in
the provider account; do not infer any cap is configured merely from code.

A deliberate authenticated GET to
`/api/v1/usage/openrouter/{generation_id}` can read the provider-reported cost
for a validated generation ID (when the server key has that upstream permission).
Strict OIDC mode requires `goreecloud.ai.admin`. It sends only the ID to the
fixed OpenRouter metadata URL and returns no prompts or full account records.
It cannot prove actual invoice charges, enforce a USD maximum, reconcile
cancelled/failed generations or replace provider-side key caps.

**No public deployment:** Identity, GoreeShield, Wardveil, Mesh, TLS ingress,
real provider testing, billing, and end-to-end recovery remain pending.
