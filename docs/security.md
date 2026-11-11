# GoreeCloud AI — Security and Deployment

**Development preview. Not production hardened.**

## Boundary and known limitations

- Default local server binds to 127.0.0.1. Docker Compose publishes only 127.0.0.1:8765 and keeps Ollama on a private container network. Do not directly expose the app on the public internet.
- The Compose example uses `ollama/ollama:latest`. An operator must assess and pin a trusted image digest for reproducible deployments; installing unfamiliar images/models on sensitive hosts requires separate review.
- The configured Ollama origin is an administrator-controlled environment variable, not accepted from chat requests. Treat endpoint changes as a privileged operation.
- The optional `GOREEAI_API_TOKEN` protects application API endpoints but is a **single shared secret**, not GoreeCloud Identity or true multi-user authorization. It is not a complete internet-facing authentication solution.
- Browser token storage is session-scoped. The token is not placed in source code. Browser compromise, cross-site scripting, or misconfigured proxying could still expose sessions.
- The server does not implement CSRF protection, comprehensive rate limits, account-level access controls, or audit-grade logging. Use a trusted same-origin reverse proxy and additional authentication for any multi-user deployment.
- This baseline does not expose shell, code interpreters, arbitrary HTTP tools, binary file uploads, agents, or public web-fetch interfaces.
- Knowledge ingestion accepts bounded text input and stores it in plaintext SQLite. All knowledge documents are currently visible to any holder of the shared API token; multi-user isolation is not implemented.
- Knowledge grounding is explicit opt-in. Document passages are untrusted; prompt injection mitigations in the model prompt are not a proven security boundary. No agent tools are executed based on document content.
- Conversation exports contain plaintext messages; downloaded files require the same privacy and backup protections as the database. Search queries are sent as POST request bodies rather than URL query strings to reduce accidental access-log disclosure.
- SQLite messages are plaintext at rest. Apply operating-system disk encryption, filesystem access controls and encrypted backups if needed. Do not upload private database files into Git.
- Incomplete or interrupted model response streams are not saved to conversation history by the generator; existing messages are preserved. Browser cancellation is best-effort and can race with successful server completion; verify actual persistence afterward.
- Model outputs are untrusted. The UI uses `textContent` rather than interpreting model-generated HTML.
- Ollama may use user-installed third-party model weights with separate licenses and model-level safety considerations. Confirm model provenance before downloading.
- Prompts and responses are sent to the administrator-configured Ollama server. If remote, treat the remote host as a disclosure destination; use a secure trusted network or TLS transport.
- Health is public to permit low-detail health checks; it returns only status and model count.

## Production gates

Before any public or multi-user deployment: implement GoreeCloud Identity, scoped authorization, TLS, request throttling, CSRF/session hardening, trusted proxy configuration, secure logging, backup/restore tests, security tests, dependency/supply-chain review, deployment monitoring and signed release process. GoreeShield and Wardveil integration require verified implementation and enforcement, not just documentation.

## Rollback

Every implementation change should be introduced through a reviewed branch. SQLite backups should be taken before migrations; the initial schema is created if missing, without destructive migration. Restore previous application version and verified database backup for rollback. No production deployment was performed by creation of this repository.

## Concurrent requests and resource bounds

Chat writes now use a SQLite immediate transaction and compare the current message count to the history snapshot that inference used. A stale or deleted conversation refuses the late result instead of appending an out-of-context exchange (HTTP 409 for nonstreaming, SSE `error` for streaming). This is a storage consistency guard, not a per-user lock, tool sandbox, or distributed inference scheduler. Model replies have a configurable application limit of 100,000 characters by default; the streaming path discards excess generated output instead of persisting it. This does **not** cap provider-side generation, model memory use, or all request/body sizes. Empty whitespace search queries are rejected.

## User-supplied JSON conversation imports

Only explicit, versioned GoreeCloud AI JSON conversation exports are accepted. The import route reads the request stream with a strict 1.5 MB limit, validates message roles/pair structure, creates new UUIDs and timestamps, and commits atomically. It does not interpret Markdown/HTML, open archive files, follow URLs, run tools, or overwrite original conversation IDs. Imports are limited to the local single-user authentication boundary; they are not proof that imported text or model labels are trustworthy.

## Local file and knowledge search boundary

The Knowledge dialog imports only a user-selected, bounded text file. CSV/JSON content is stored as text and not interpreted as executable code. The new POST knowledge-search route keeps queries out of URLs, but legacy GET queries can still appear in access logs. Both features retain the existing single-user/plaintext storage limitations.

## Experimental semantic index and embedding disclosure

Semantic indexing and search are opt-in and require an already installed Ollama embedding model; no model downloads are performed. A selected document is divided into limited chunks and sent to the administrator-configured Ollama endpoint, which can be remote. Embeddings and excerpts are retained in plaintext SQLite; deleting a document cascades its semantic chunks. Vectors are dimension/finite-number checked and saved transactionally. This path has no worker queue, per-user permissions, real-model validation or retrieval-quality guarantees and is not approved for public deployment.

## Adapter protocol regression tests

Automated httpx MockTransport tests now check the Ollama request/response contracts, including embedding batch shape, nontruncation flags, incomplete NDJSON streams, normalized upstream HTTP errors and invalid model endpoint URLs. These are **offline contract tests**, not live Ollama runtime, real model quality, cloud data-flow, or GPU validation.

## Baseline browser-response security headers

The local preview adds a same-origin Content Security Policy for bundled JavaScript/CSS and same-origin API connections, denies framing, disables content-type sniffing, restricts referrer disclosure, and marks all `/api/` responses `Cache-Control: no-store` with legacy `Pragma: no-cache`. This includes errors and authentication failures; static scripts remain cacheable.

These headers are defense in depth, **not** per-user identity, safe remote deployment, XSS immunity, request-rate limiting, CSRF protection, a trusted reverse proxy, or Wardveil integration. A future embeddable assistant or voice/video feature needs an explicit security review before widening CSP permissions or frame access. Browser security must be verified in actual supported environments before declaring UI acceptance.
