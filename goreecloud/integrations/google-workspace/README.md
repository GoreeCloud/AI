# GoreeCloud AI — Gmail and Google Drive (MCP + REST API)

**Status (2026-11-04):** source integration, not deployed or authenticated. Never interpret MCP catalog registration, passing unit tests, or a personal ChatGPT connector as evidence that LibreChat is connected.

## Official Google MCP services

| Product | Official remote endpoint | Current source status |
| --- | --- | --- |
| Gmail | `https://gmailmcp.googleapis.com/mcp/v1` | Registered, with per-user OAuth fields; `startup: false` pending Google Cloud setup |
| Google Drive | `https://drivemcp.googleapis.com/mcp/v1` | **Removed from the development MCP catalog**; the production checkout still includes the historical unsafe entry until a governed release |

These are separate Google Workspace Developer Preview services, not one shared MCP server. Google's public preview requires eligibility, enabled Google Cloud services, appropriately configured OAuth 2.0 credentials and per-user consent.

### Gmail MCP setup

1. In an authorized Google Cloud project, enable `gmail.googleapis.com` and `gmailmcp.googleapis.com`. Enroll in the applicable Google Workspace Developer Preview if required.
2. Create an OAuth 2.0 Web application client, selected for an AI-powered agent. Set the authorized redirect URI to **exactly** `https://ai.goreecloud.com/api/mcp/gmail/oauth/callback`. Set the appropriate OAuth audience and test users; request only the Gmail scopes needed.
3. Store the OAuth client ID and secret in the **private**, permission-restricted VPS environment, never Git, logs, URLs or chats:
   - `GOOGLE_WORKSPACE_MCP_CLIENT_ID`
   - `GOOGLE_WORKSPACE_MCP_CLIENT_SECRET`
4. The source `goreecloud/deployment/librechat.config.yml` sets `gmail` to Google OAuth with `access_type=offline`, `prompt=consent`, `gmail.readonly` alone. Google's `gmail.compose` grant also permits sending mail, so it is not appropriate for this read-only MCP catalog entry. Any future drafts capability requires separately reviewed OAuth and tool approval.
5. After the OAuth client and Google Preview have been verified and the Git-tracked config is safely deployed, authorize the Google account **inside the same Firefox container** as GoreeCloud AI (see the Webspaces OAuth handoff issue). Connection remains per LibreChat user. Confirm a safe message search and read; do not send, label, delete or draft via the read-only MCP integration.

Google might require OAuth consent verification, and testing-mode refresh tokens may expire. Client credentials and callback must match the production origin exactly.

### Drive scope policy (mandatory)

The connected Google Drive account must be `goreecloud@gmail.com`, and requests may only read/write files physically inside the **verified** Google Drive folder named `GoreeCloud` and its actual descendants. This is not the user's Drive root.

**The official Drive MCP server does not expose a verified folder-restricted authorization surface.** `startup:false` does *not* disable all manual connection pathways, and `chatMenu:false` would not block Agent Builder tools. Consequently, **do not grant OAuth or connect that remote MCP server**. A server-side, fail-closed gateway must replace its endpoint (or a reviewed, narrower Google-provided equivalent must be demonstrated) before Drive MCP activation. Direct Google Docs/Sheets/Slides MCP servers have the same potential out-of-folder access and must not be silently added as a workaround.

The `createGoreeCloudDriveApi` client in `google-api.mjs` is an API foundation for such a gateway. Each operation:
- requires a caller-supplied short-lived per-user OAuth access token, with no stored token or user secrets in source;
- checks Drive's `about.user.emailAddress` equals the canonical account and that the configured folder ID denotes a non-trashed `GoreeCloud` folder;
- verifies files by traversing only children of the authorized root; never fetches metadata for an arbitrary out-of-folder file ID. Rejects shortcuts, deleted objects, invalid IDs and untrusted listings, with bounded traversal and pagination;
- lists only children of a previously verified parent (never a global Drive search), returns metadata, and reads bounded UTF-8 plain text / exported Google Docs only;
- rejects unauthorized or oversized responses without returning private upstream error bodies.

**Security limitation:** ancestry enforcement narrows what the *application code returns*, not what a broad Google `drive.readonly` OAuth bearer token could access if compromised. A validated service boundary is required before issuing that token to a production gateway; token leaks, third-party URLs and arbitrary MCP tools cannot be considered safe just because this library exists. This module has no Express routes, model-exposed tools or standalone MCP listener by design. It is not yet a deployed Drive API.

The Drive root ID must come from a verified folder lookup using the authorized Google Drive connector; pass it only through private server configuration, never as a model-controlled argument.

### Direct REST API adapter

`google-api.mjs` exports:

- `createGmailApi({ accessToken, expectedEmail, fetchImpl })`
  - `listMessages(q, maxResults)`, `getMessage(id)`, `createDraft({ to, subject, body })`.
  - Checks the caller's Google account with Gmail `users.getProfile`. No sending, deleting or modifying messages.
- `createGoreeCloudDriveApi({ accessToken, rootId, expectedEmail, fetchImpl })`
  - `getMetadata(id)`, `listChildren(parentId, pageToken)`, `readText(id)`.
  - Requires an authenticated upstream caller and a verified root before use; never accepts untrusted open URLs or raw Drive search parameters.

These are **tested API clients**. `scoped-drive-tools.mjs` additionally exposes exactly three read-only, schema-validated MCP tool handlers (`list_children`, `get_metadata`, `read_text`) backed exclusively by the scoped Drive API. The adapter rejects unknown tools and parameters and bounds returned text; the five adapter tests run in the same `node --test` suite. These are *not* public REST endpoints or a running MCP server and do not reuse ChatGPT plugin OAuth tokens. A production gateway still needs tenant-bound authentication, secure Google OAuth credential storage, per-operation auditing, transport protections and end-to-end acceptance. Wire them only after the application's user/tenant authorization, encrypted Google OAuth token storage and refresh, audit logging and per-operation permission checks are reviewed.

Run independent tests without credentials or external network access:

```bash
node --test goreecloud/integrations/google-workspace/*.test.mjs
```

## Integration and release checklist

- [x] Confirm Google's official Gmail/Drive MCP endpoint URLs and available Google scopes.
- [x] Register Gmail in the Git-tracked MCP config with OAuth field references, default-off startup.
- [x] Remove the unrestricted raw Drive MCP entry from the development catalog, rather than trusting `startup: false`.
- [x] Implement and unit-test Gmail/Drive direct API clients with account and subtree checks.
- [ ] Verify Google Cloud project, Developer Preview eligibility, API enablement and OAuth redirect registration.
- [ ] Securely provision the OAuth client credentials, complete per-user consent and verify refresh behavior.
- [ ] Implement/review a per-user API route and Drive-constrained MCP bridge with true server-side enforcement, token storage, authorization, audit and tool approval.
- [ ] Validate actual LibreChat MCP catalog/connect flow, read-only Gmail search and draft creation, Drive subtree test including attempted out-of-folder reads.
- [ ] Reconcile GitHub/main and VPS-01 changes, validate Compose and deploy via the documented rollback path. No VPS change is made by this source branch.

References:
- https://www.librechat.ai/docs/mcp_servers/google_workspace
- https://developers.google.com/workspace/guides/configure-mcp-servers
- https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server
- https://developers.google.com/workspace/drive/api/guides/configure-mcp-server
- https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list
