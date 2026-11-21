# GoreeCloud AI — private conversation library

**Status:** Developer-preview source feature; not deployed or production certified. The API remains single-owner by default, and optional signed-owner OIDC scopes are governed by the existing pinned-JWKS adapter.

## What is implemented

- A **local SQLite FTS5 index** of explicitly saved messages, alongside literal title matching. Searches do not contact Ollama, OpenRouter, MCP, or other external services.
- Owner-authenticated search, rename, JSON/Markdown export, and JSON import of saved conversations. JSON imports use the established bounded save request (1–64 messages, 250,000 combined characters), and **always receive new IDs and timestamps** rather than trusting exported metadata.
- The React web library has private local search, rename, import, export and non-destructive in-memory branching. A branch preserves messages through the selected message and becomes persistent only if the owner explicitly saves a new conversation. Branch, new chat, and open chat reset the current cloud-consent toggle.
- Existing conversation IDs and messages remain intact. The first open of a pre-feature local database creates an FTS index and rebuilds it from existing stored messages. Database connections also maintain INSERT, DELETE and UPDATE triggers so new saves and deletions update the index. Index content is kept inside the configured database.
- Each new endpoint is classified in the optional fail-closed OIDC capability matrix. No unapproved external calls or background indexing services were introduced.

## API contract

| Method | Route | OIDC capability (when strict scopes enabled) | Behavior |
| --- | --- | --- | --- |
| `GET` | `/api/v1/search/conversations?q=TEXT&limit=20` | `read` | Search title or saved message content locally; query 2–200 characters, limit 1–50 |
| `PATCH` | `/api/v1/conversations/{uuid}` | `write` | Rename a saved conversation after bounded title validation |
| `GET` | `/api/v1/conversations/{uuid}/export?format=json` | `read` | Download `goreecloud.ai.conversation.v1` JSON |
| `GET` | `/api/v1/conversations/{uuid}/export?format=md` | `read` | Download a Markdown transcript |
| `POST` | `/api/v1/conversations/import` | `write` | Validate JSON schema and save messages as a new local snapshot |

The JSON export shape is `{"schema":"goreecloud.ai.conversation.v1","conversation":{"id":"...","title":"...","messages":[{"role":"user","content":"..."}],...}}`. On import, only the validated title and allowed user/assistant messages become the new snapshot; IDs and timestamps are discarded. Exports are explicit owner actions; no automatic upload or synchronization takes place.

## Privacy, recovery and boundaries

The **default local store remains plaintext SQLite**, unless the operator has explicitly enabled and validated optional SQLCipher with externally managed keys. Database FTS data follows that storage mode. **Exported JSON/Markdown files are plaintext even when the live database uses SQLCipher**; protect downloaded copies, browser download history, backups and device access appropriately. Avoid importing untrusted files; although the parser is bounded and schema-validated, the text is still untrusted content.

Deletes remove saved records and current FTS entries but are **not secure erasure** of SQLite pages, backups, exported files or provider copies. Do not run first-open schema changes against important real data without a tested private backup and isolated restore. No automatic retention changes, cloud transfers, identity-issuer deployment, GoreeShield runtime policy, or Wardveil production certification are implied.

The web client exposes these features. Existing Linux Qt and Android Compose clients can continue calling their prior endpoints; native UI parity for the new library actions remains an open task.

## Development validation

Use the established, canonical `GoreeCloud/CLI Commands/GoreeCloud/AI.md` reference for locked commands. This feature's tests live in `server/tests/test_conversation_library.py`, and optional scoped-route completeness remains covered in `server/tests/test_oidc_capabilities.py`. Source-level validation performed on the authorized Linux development laptop, November 21, 2026, with system Python 3.12, locked dependencies, and synthetic local records only:

- Python suite: **191 passed, 3 skipped**.
- Ruff checks: **passed**.
- React/TypeScript/Vite production build: **passed**.

No paid inference calls, production database migrations, deployment, hardware acceptance or real-provider qualification were performed.
