# GoreeCloud AI — GoreeCloud Search research adapter

**Status: source-only, disabled and not deployed.** GoreeCloud AI will use **GoreeCloud Search as its primary research service** only after independent stability, security and release acceptance. Until then, this integration makes **no live research calls**. Source-only tests never contact external search providers.

## Verified upstream contract

Verified against [GoreeCloud/search](https://github.com/GoreeCloud/search), draft [PR #2](https://github.com/GoreeCloud/search/pull/2), specifically `goreecloud_search/server.py`, `docs/ARCHITECTURE.md`, and `docs/LOCAL_READINESS_SECURITY.md`.

- `GET /readyz`: ready only when the local SQLite index passes integrity/access checks, with `{status:"ready", scope:"local-catalog"}`.
- `GET /api/providers`: `available` provider booleans, `default:["local"]`, `external_requires_consent:true`.
- `POST /api/search`: `{query,limit,providers,share_query}`, bounded to 160 query characters and 1–20 results. The response carries `{results,count,scope,providers,warnings}`, source-attributed public HTTPS links.
- Search's current server is an **unauthenticated 127.0.0.1-only development service**, not a remotely addressable production API, crawler or safe shared-public endpoint. Its optional Brave/SearXNG providers are disabled unless an operator enables them and each external query is consented.

## Implementation

`research-client.mjs` exports `createGoreeCloudResearchClient` and `createGoreeCloudResearchTool`. It has no new NPM dependencies and starts with `enabled:false`, `releaseQualified:false` and `allowExternal:false`.

The adapter accepts **only** `http://127.0.0.1:PORT`, never arbitrary remote hosts, untrusted query URLs, or HTTP redirects. With either release flag false, no readiness or query requests are sent and the MCP tool list is empty. Once appropriately enabled, it checks readiness and provider availability before sending each query. Local research does not share terms externally; external providers require both operator-approved enablement and **explicit per-query consent**. Results are bounded, attributed, and validated against public HTTPS citation rules; returned snippets are **untrusted data**, never instructions. Model arguments cannot choose a target endpoint or token.

The MCP tool contract `goreecloud_search_research` is not a standalone server or LibreChat plugin. `authorizeRequest` must be implemented with verified, server-generated user/session context before any tool is exposed.

Run the offline tests:

```bash
node --check goreecloud/integrations/search/research-client.mjs
node --test goreecloud/integrations/search/research-client.test.mjs
```

The corresponding GitHub Actions job checks these files without credentials, an exposed search port or external provider access.

## Required activation and release gates

1. **Qualify Search.** Complete the greenfield Search PR, static/CI checks, live API and provider compatibility, privacy/legal/billing limits, first-party GC UI and accessibility acceptance, authentication, reliability, encrypted off-host recovery and rollback. A passing workflow is not a Stable release declaration.
2. **Secure the transport.** Build a separately reviewed, authenticated private Search service bridge or an intentionally isolated same-network-namespace loopback connection. **Never** expose the unauthenticated local API through public Caddy, a generic Docker bridge, a wildcard VPN allow rule or the currently broken `search-dev.goreecloud.com` reverse proxy. Search currently has no remote auth or tenant policy.
3. **Bind user identity.** Provide authenticated, tenant-scoped, server-owned `authorizeRequest`, approved token storage and auditability. No identity, URL, API key or release flag may come from model-provided arguments.
4. **Choose the primary research tool.** Once release-approved, configure LibreChat's research tool routing to prefer `goreecloud_search_research`, with citations and provider disclosure. Deprecate or subordinate competing research tools only after assessing existing user integrations. **No silent fallback** to external services if GoreeCloud Search is unavailable; explain unavailability and obtain consent for alternatives.
5. **Keep consent explicit.** External Brave/SearXNG queries require disclosure before sending, operator enablement, provider-side availability, a confirmed per-query `shareQuery:true`, account-level cost limits and approved provider terms. Model inference or default flags alone must not authorize data disclosure.
6. **Validate end-to-end.** Test authenticated and unauthorized users, live citation integrity, prompted malicious snippets, provider outages, cooldowns, per-user request limits, credential isolation, cancellation, mobile/desktop UI, recovery, controlled rollback and removal of the tool from the catalog when disabled.
7. **Governed production rollout.** Reconcile GitHub and VPS versions and deployment/build state. Require backups, approval where applicable and full verification; never enable the release flags as part of this source-only PR.

## Non-goals of this source PR

No change to live `ai.goreecloud.com`, no Search container or gateway, no service deployment, no OAuth, no DNS or NetBird changes, no user-facing tool registration, and no automatic activation. The original adapter is intentionally safe to merge as *disabled source* without asserting that research is functional.

**Owner product requirement:** Use GoreeCloud Search for GoreeCloud AI research *when stable*. Do not present an unqualified local FTS5 index as equivalent to a fully qualified web-research service.
