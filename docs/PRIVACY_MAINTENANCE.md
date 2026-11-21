# Source-tested GoreeCloud AI local retention maintenance

**Status:** Developer-preview CLI and optional systemd **templates only**.
Nothing is scheduled or enabled by source checkout, tests, or GitHub merge.
This is a limited implementation of local retention rules, **not** production
GoreeShield policy enforcement, secure erasure or monitored backup lifecycle.

## Policy and operator authorization

- `GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS=0` retains every explicitly
  saved conversation indefinitely. Set a positive operator-chosen value
  (1–3650 days) before expecting old saved chat cleanup. Documents are **never**
  deleted by the maintenance command.
- `GOREECLOUD_AI_CONSENT_RECEIPT_RETENTION_DAYS` defaults to 30 days
  (supported 1–365); expired metadata-only approvals are eligible for deletion.
- The legacy daily cloud admission-count rows older than 14 days are eligible
  for removal. This never refunds today's request quota, and it does not
  reconcile provider charges. Retention does not cancel active generation.
- A manually invoked **preview** counts eligible rows, does not create or
  migrate a database, and uses a read-only SQLite/SQLCipher connection.
- **Actual deletion** requires both
  `GOREECLOUD_AI_MAINTENANCE_ENABLED=true` in the secured operator process
  configuration **and** a CLI invocation with `--apply`. Missing, malformed
  and disabled configuration fails closed. Never run on an unapproved database.
- Live deletion occurs in one SQLite transaction with an immediate write lock
  to avoid racing another maintenance writer. Results are counts only; no
  document, chat, prompt, credential, user ID or network request is emitted.

## Checked development-only commands (from repository `server/`)

    uv sync --locked --extra dev --extra sqlcipher --python 3.12
    uv run --locked --extra dev --extra sqlcipher pytest -q tests/test_maintenance.py
    uv run --locked --extra sqlcipher python -m app.maintenance

Do not use `--apply` without understanding the live effect and verifying
an independent encrypted backup and isolated restore. Operator-approved
example, never substitute a real path or secret in GitHub/Drive:

    # Under a deliberately authorized configured environment only:
    uv run --locked --extra sqlcipher python -m app.maintenance --apply

Run these from a trusted service account with access only to its own private
database, never from a public endpoint. The command prints only counts and
a generic failure type; it has no HTTP API and performs no provider requests.

## Optional scheduling

`deploy/systemd/goreecloud-ai-maintenance.service` and `.timer` are
**examples** for operator adaptation, not installed units. They deliberately
require site-specific verified service username, binary path, working
directory, database location, private environment source, hardening and
permissions. The template uses a daily UTC timer with randomized delay and
`Persistent=false` to avoid catching up automatically after an outage.
Never enable the unit merely because CI passes.

Before installation, review dedicated UID, SQLite mode and key custody,
SQLCipher imports, safe working directory and file permissions. Verify
manual preview, controlled `--apply` on an isolated synthetic DB, backup
restoration, systemd runtime isolation, journald privacy, timer state and
rollback. Store secrets in an authorized secret manager; an unprotected
environment file does not meet production key custody requirements.
Retain execution evidence without the database contents.

## Limitations and rollback

Deletion is irreversible on live rows. Backups, old plaintext SQLite
files, older SQLCipher snapshots, filesystem copies, WAL/freelist pages,
cloud providers and other recipients are **unaffected** and may retain data.
No vacuum/secure deletion, remotely coordinated policy, automatic revocation,
tenant segregation, continuous monitoring or production scheduler is provided.
Disable the timer before rollback; rehydrate from an independently verified
encrypted backup under a specifically authorized recovery plan.
