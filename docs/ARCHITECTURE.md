# Architecture and security boundaries

## Components
Web React / Native Qt Quick Linux / Native Kotlin Compose Android
  → authenticated FastAPI /api/v1
  → OpenRouter chat and image APIs (preferred)
  → optional loopback Ollama runtime (local)
  → SQLite Markdown documents
  → explicit, allowlisted MCP Streamable HTTP client

The API host, rather than client apps, stores provider secrets. Prompts are kept
in client memory until sent; saved documents persist unencrypted in the configured
SQLite file. Images are not saved by the server. The service is **single owner**
and not a general-purpose hosted multi-user system.

## Privacy & payments
An OpenRouter request transmits user-selected content to external providers.
Use OpenRouter privacy settings and independent spending limits; a local
checkbox is not a global billing budget. Requested local-only inference must
not silently route back to OpenRouter. A transient cloud error may fall back
to a separately configured local model only when the request opts in.

## MCP and agents
MCP URL is pinned by the server operator, HTTPS or loopback required, and tools
must appear in GOREECLOUD_AI_MCP_ALLOWED_TOOLS. Every tool call requires an
explicit approved flag from the authenticated owner. This does not yet provide
full per-user delegated authorization or sandboxing. Agent plans do not run;
the only built-in action in the preview is local read-document.

## MIPS integration
- GoreeCloud UI owns design language and source tokens.
- GoreeShield owns consent, minimization, retention, sharing and privacy policy.
- Wardveil owns cybersecurity assessment, scanning and runtime defense.
- GoreeCloud Mesh owns inter-product API discovery, routing and data exchange.
- GoreeCloud Identity owns real user authentication, authorization and scopes.

Current code documents these integration boundaries; it does not claim they are
deployed or enforced by remote GoreeCloud MIPS services.

## Main operational risks
- The preview bearer token is a shared secret, not delegated Identity auth.
- SQLite is not encrypted at rest, and backups/retention are not configured.
- No rate limiting, independent model spend cap, or full tool sandbox exists.
- Imported PDFs and DOCX are untrusted; parse only trusted files in preview.
- Native device tests, CI, live model and MCP compatibility still need evidence.
- Public Internet exposure is forbidden until identity, TLS, rate limits, privacy,
  security, audit, recovery, licensing and operations gates are verified.
