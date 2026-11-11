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
- SQLite messages are plaintext at rest. Apply operating-system disk encryption, filesystem access controls and encrypted backups if needed. Do not upload private database files into Git.
- Incomplete or interrupted model response streams are not saved to conversation history; existing messages are preserved.
- Model outputs are untrusted. The UI uses `textContent` rather than interpreting model-generated HTML.
- Ollama may use user-installed third-party model weights with separate licenses and model-level safety considerations. Confirm model provenance before downloading.
- Prompts and responses are sent to the administrator-configured Ollama server. If remote, treat the remote host as a disclosure destination; use a secure trusted network or TLS transport.
- Health is public to permit low-detail health checks; it returns only status and model count.

## Production gates

Before any public or multi-user deployment: implement GoreeCloud Identity, scoped authorization, TLS, request throttling, CSRF/session hardening, trusted proxy configuration, secure logging, backup/restore tests, security tests, dependency/supply-chain review, deployment monitoring and signed release process. GoreeShield and Wardveil integration require verified implementation and enforcement, not just documentation.

## Rollback

Every implementation change should be introduced through a reviewed branch. SQLite backups should be taken before migrations; the initial schema is created if missing, without destructive migration. Restore previous application version and verified database backup for rollback. No production deployment was performed by creation of this repository.
