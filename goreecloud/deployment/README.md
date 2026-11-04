# GoreeCloud AI deployment overlay

This directory is the **version-controlled source of truth** for GoreeCloud's LibreChat configuration, visual theme, integrations and VPS Compose overlay. It is additive: upstream LibreChat source and vendored files remain unchanged. The public `main` Git commit is **no longer byte-identical to upstream** after adding this GoreeCloud directory, although the upstream app files were not changed. Preserve the upstream release history and merge upstream changes without deleting this directory.

## Files

- `librechat.config.yml` — current VPS-01 LibreChat settings, **GoreeCloud Iris** light/dark theme, two optional user-key model providers, nine configured MCP entries (Gmail included, pending OAuth). Gmail, Dropbox and Remote Desktop Commander have `startup: false` pending separate authorization. The unrestricted Google Drive MCP entry is **absent from the development catalog**; the live VPS configuration still needs governed reconciliation. A folder-restricted gateway must pass authorization and security tests before any Drive MCP connection. See [Google Workspace integration](../integrations/google-workspace/README.md).
- `compose.yml` — unified, Git-tracked Docker override with loopback-only API/admin ports, external Caddy proxy network, RAG database password interpolation and the read-only mount for `librechat.config.yml`.
- `Caddyfile.ai.goreecloud.com.example` — public HTTPS site snippet. Existing Caddyfile has unrelated sites; **never overwrite it wholesale**.
- `rollback.md` — deployment, validation and recovery procedures.

## Secrets and runtime state

Do not commit the production `.env`, OAuth tokens, PATs, Porkbun keys, browser profiles, admin password, database files, MongoDB data, uploads or logs. The repository's existing `.gitignore` protects most runtime paths; always review the staged diff for secret values before a push. Store production secrets in the existing private `/home/ladamian/goreecloud-ai/.env` (permissions 0600), or an approved secrets manager. `LIBRECHAT_POSTGRES_PASSWORD` must be set there. All MCP OAuth authorization remains per user; ChatGPT connectors do not automatically share credentials with LibreChat.

## Google Workspace — Gmail and Drive MCP/API

Gmail's official Developer Preview MCP endpoint is configured with env-referenced OAuth client credentials and limited Gmail scopes, but cannot connect until Google Cloud enablement, provider authorization and a reviewed deployment. The unrestricted Google Drive MCP entry has been removed from this development configuration; its historical VPS entry is not safe to connect. A folder-scoped, source-only tool adapter exists but is not yet an authenticated or deployed MCP server. An injectable, tested Gmail/Drive REST API adapter is in [`goreecloud/integrations/google-workspace`](../integrations/google-workspace/README.md); it is not yet a public API service or an authenticated MCP gateway. Keep user OAuth tokens out of GitHub and review before deploying.

## GitHub MCP — fix missing Authorization header

The hosted GitHub MCP uses the official `https://api.githubcopilot.com/mcp/readonly`
endpoint. LibreChat requires **each user** to supply a GitHub personal access token.
The YAML registers a masked per-user field named `GITHUB_PERSONAL_ACCESS_TOKEN`.
It is not a server-wide secret, and ChatGPT's connected GitHub app does not provide
the token to LibreChat.

1. In GitHub, visit **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**. Set the **Resource owner** to
   `GoreeCloud`, choose only the repositories required (start with `AI`),
   and grant **Contents: Read-only**, **Metadata: Read-only** and, if needed,
   **Issues / Pull requests: Read-only**. Use an expiry and allow for any
   account-specific token approval requirements.
2. In LibreChat at `https://ai.goreecloud.com`, open **MCP Servers**, select
   **github**, then **Configure / Connect**. Enter the token in the masked
   **GitHub personal access token** field and save. **Do not paste the PAT into
   a chat message, GitHub issue, Git repository, terminal command, or logs.**
3. Retry connecting the server. A successful connection exposes GitHub tools.
   Test a safe read, such as querying repository `GoreeCloud/AI` metadata or
   reading its README. Do not interpret a grey status dot as connected.
4. If the server reports `missing required Authorization header`, verify the
   per-user credential was saved, reconnect, and check only sanitized server logs.
   A GitHub 401/403 *after* a bearer header indicates a different problem
   (invalid/expired token, wrong owner/repository, insufficient permissions).
5. The endpoint is intentionally read-only. Enable writes only through a
   separate, reviewed permission and toolset change, not by granting a token
   broad rights or changing the path without approval.

Because the server needs a per-user credential, `startup: false` avoids
unauthenticated probes until the user actively connects. A restart is necessary
when changing this YAML; do not confuse successful server registration with
an authenticated GitHub MCP tool call. The exact cause of the screenshot failure
was confirmed in the VPS logs: `missing required Authorization header`.

References:
- https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_servers
- https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md

## Deploy (VPS-01, approved maintenance window)

First back up the live external configuration and verify the public repository commit. Run from **the repository root**. Review `git diff` and any upstream changes before `git pull --ff-only`.

```bash
cd /home/ladamian/goreecloud-ai
git status --short
git fetch origin main
git diff --stat HEAD..origin/main
git pull --ff-only origin main

docker compose -p goreecloud-ai -f docker-compose.yml -f goreecloud/deployment/compose.yml config --quiet
docker compose -p goreecloud-ai -f docker-compose.yml -f goreecloud/deployment/compose.yml up -d --no-deps api
```

If Compose says the API container is already running but hasn't reloaded YAML, **an authorized** restart is necessary:
```bash
docker compose -p goreecloud-ai -f docker-compose.yml -f goreecloud/deployment/compose.yml restart api
```
Validate HTTPS, API logs, live theme in a browser, all nine MCP server entries, authenticated MCP tool calls, light/dark/mobile layout and backup rollback. The UI must pass GoreeCloud UI's design authority in `GoreeCloud/gc-ui`; a valid YAML file alone is not visual acceptance.

## Safety / functional caveats

The older deployed external files `~/goreecloud-ai-deploy/override.yml`, `integrations.override.yml` and `librechat.yaml` are retained for rollback. **Do not load the unified overlay alongside these two previous overrides**: Compose then has two mounts for the same destination and may produce an invalid config. Changing the Compose selection is an intentional cutover. Validate against *only* the base file and the new unified overlay.

The current screenshots exposed a separate conversation-compaction error, `Nothing to compact`. Theme tokens do not fix agent/model functional errors. Validate independently instead of hiding model errors with CSS.

Google Drive access **must** remain limited to the verified `GoreeCloud/` folder and descendants. The generic Google Drive MCP endpoint alone cannot guarantee this: keep it inactive until a policy-enforcing gateway is verified. Likewise, privileged remote desktop operations require explicit authorization and approved least-privilege scope; never expose Chrome DevTools publicly.

Verification status at time of commit: syntax parsed in prior VPS check; first theme startup warned that `controlFontWeight` should be a string; corrected to `'600'`. The **post-correction live theme has not yet been verified**, and no production cutover to this Git-tracked Compose overlay has occurred merely by creating the repository commit.

## Upstream sync

Keep `GoreeCloud/AI` as a LibreChat-derived repository: update the upstream source on a reviewed branch, preserve `goreecloud/deployment/`, and use a PR with CI and visual checks before updating VPS-01. Never force-push a fresh upstream mirror over the custom deployment directory.
