# GoreeCloud AI native Linux preview

Qt Quick 6.12 / PySide6 6.12 source, native operating-system window and controls.
Uses the backend REST and SSE APIs; owner credentials are entered at runtime
and not persisted. Chat now supports incremental native Qt Network streaming
with explicit cancellation, with bounded pure-Python frame decoding and a
manual-redirect-denial policy for the streaming connection. All other
Linux API calls now also use a bounded native Qt Network REST bridge with
manual redirect refusal; the earlier credential-bearing QML XMLHttpRequest
path has been retired. Both Qt Network transports refuse ambient proxies
to protect the owner credential; operators requiring an approved proxy need
a separately reviewed explicit policy.

On a Linux machine with Python 3.11+ and a supported desktop environment:

    cd linux
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    python main.py

Host-side, synthetic-only Qt network and decoding tests:

    python -m unittest discover -s . -p 'test_*.py'

These tests use a temporary 127.0.0.1 HTTP fixture and make no cloud provider
requests, but they are not real desktop, provider, screen-reader or packaged
Linux device acceptance tests.

Run the FastAPI server separately and configure a token. The native UI now
requires explicit cloud-processing approval before OpenRouter inference;
without consent, Auto may use the configured Ollama model. Remote API
endpoints must use HTTPS, with HTTP limited to 127.0.0.1/localhost.
Both native Qt bridges refuse credential-bearing URLs, query/fragment
endpoints, and redirects; REST calls also enforce a bounded API route,
request/response JSON limits and single active request. They do not expose
prompts or tokens through logging or command-line arguments. The regular
non-streaming request implementation remains available for server-supported
local fallback. The Qt Quick interface
supports streamed and complete-response chat with cancel, model routing,
native context-window latest-4/8/16 message trimming, 256–2048-token
output cap selection, explicitly opt-in local complete-answer RAM caching
and OpenRouter edge response cache headers (separate cloud consent). These
are server options; no response cache data is saved in the desktop client.
Opening or starting a new conversation resets cache-consent toggles.
No live model or physical desktop token-savings acceptance was performed.
It also supports
read-only discovered image models, image generation preview, Markdown document CRUD,
agent planning and MCP tool discovery/explicit invocation. A new native History
tab supports owner-approved chat snapshots, listing, opening and local FTS
search. Qt REST queries are explicitly allowed only for the bounded conversation
search route; unknown query strings, redirects, credential-bearing endpoints
and unbounded payloads remain rejected. GET JSON arrays now support native
library lists. Opening a snapshot resets cloud consent. JSON/Markdown export,
import and native branching still require further client parity.
History now also supports explicit local rename and confirmed delete using
bounded Qt Network PATCH/DELETE calls; the bridge handles 204 no-content
success without reading an empty JSON response. Synthetic localhost tests
cover these methods and credential-preserving redirect refusal. It is a native
preview, not a packaged binary or fully feature-parity product. It does not yet
support reference-image file selection or durable image downloads.

GoreeCloud UI light/dark/accent tokens are sourced from the MIT-licensed
GoreeCloud/gc-ui snapshot in ../design/gc.tokens.json; current QML uses the
verified dark Iris token values. Native Qt component conformance is untested.
Test on Linux with actual Qt 6.12 graphics, font scaling and accessibility tools
before distribution. No server key should be hardcoded in the application.
