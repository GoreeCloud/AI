# GoreeCloud AI deployment overlay

This directory is the **version-controlled source of truth** for GoreeCloud's LibreChat configuration, visual theme, integrations and VPS Compose overlay. It is additive: upstream LibreChat source and vendored files remain unchanged. The public `main` Git commit is **no longer byte-identical to upstream** after adding this GoreeCloud directory, although the upstream app files were not changed. Preserve the upstream release history and merge upstream changes without deleting this directory.

## Files

- `librechat.config.yml` — current VPS-01 LibreChat settings, **GoreeCloud Iris** light/dark theme, two optional user-key model providers, nine configured MCP entries. Google Drive, Dropbox and Remote Desktop Commander have `startup: false` pending separate authorization; do not infer lack/presence of user-level runtime access solely from this flag.
- `compose.yml` — unified, Git-tracked Docker override with loopback-only API/admin ports, external Caddy proxy network, RAG database password interpolation and the read-only mount for `librechat.config.yml`.
- `Caddyfile.ai.goreecloud.com.example` — public HTTPS site snippet. Existing Caddyfile has unrelated sites; **never overwrite it wholesale**.
- `rollback.md` — deployment, validation and recovery procedures.

## Secrets and runtime state

Do not commit the production `.env`, OAuth tokens, PATs, Porkbun keys, browser profiles, admin password, database files, MongoDB data, uploads or logs. The repository's existing `.gitignore` protects most runtime paths; always review the staged diff for secret values before a push. Store production secrets in the existing private `/home/ladamian/goreecloud-ai/.env` (permissions 0600), or an approved secrets manager. `LIBRECHAT_POSTGRES_PASSWORD` must be set there. All MCP OAuth authorization remains per user; ChatGPT connectors do not automatically share credentials with LibreChat.

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
