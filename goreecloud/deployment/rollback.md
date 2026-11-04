# Verify and roll back GoreeCloud AI configuration

The existing production files on VPS-01 are:
```
/home/ladamian/goreecloud-ai-deploy/override.yml
/home/ladamian/goreecloud-ai-deploy/integrations.override.yml
/home/ladamian/goreecloud-ai-deploy/librechat.yaml
```

Two pre-UI backup files were saved there:
```
/home/ladamian/goreecloud-ai-deploy/librechat.before-ui.yaml
/home/ladamian/goreecloud-ai-deploy/integrations.before-ui.override.yml
```

## Preflight

Run `docker compose config --quiet` before modifying a running service, examine the merged `api.volumes` to ensure **exactly one** `/app/librechat.yaml` mount, and retain the old Compose command so you can revert immediately. Keep `docker compose -p goreecloud-ai` project identity stable to preserve volumes. Do not use `down -v` or remove MongoDB volumes.

## Use Git-tracked configuration

```bash
cd /home/ladamian/goreecloud-ai
docker compose -p goreecloud-ai -f docker-compose.yml -f goreecloud/deployment/compose.yml config --quiet
docker compose -p goreecloud-ai -f docker-compose.yml -f goreecloud/deployment/compose.yml up -d --no-deps api
```

## Roll back to the previous overlays

```bash
cd /home/ladamian/goreecloud-ai
docker compose -p goreecloud-ai -f docker-compose.yml -f /home/ladamian/goreecloud-ai-deploy/override.yml -f /home/ladamian/goreecloud-ai-deploy/integrations.override.yml config --quiet
docker compose -p goreecloud-ai -f docker-compose.yml -f /home/ladamian/goreecloud-ai-deploy/override.yml -f /home/ladamian/goreecloud-ai-deploy/integrations.override.yml up -d --no-deps api
```

If rolling back the theme itself, first back up the current external YAML, restore `librechat.before-ui.yaml` to `librechat.yaml`, then restart only `api`. Restoring the pre-UI Compose file also reverts the APP_TITLE override. No other production containers need to be recreated. Check container logs and HTTP 200 afterward; carry out actual browser tests and don't infer UI quality solely from HTTP status.
