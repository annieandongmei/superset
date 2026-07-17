---
name: testing-superset-golden-path
description: Bring up a local Apache Superset and test its core flows (dashboard render, chart Explore re-run, SQL Lab query) end-to-end. Use when verifying Superset runs or demoing/testing its golden-path UI.
---

# Testing Superset golden-path

## Bring up a running instance (fastest: prebuilt Docker image)
Use `docker-compose-image-tag.yml` (pulls the prebuilt `latest-dev` image + postgres + redis + worker):

```bash
docker compose -f docker-compose-image-tag.yml up -d
# wait for http://localhost:8088/health -> 200 ; log in admin/admin
```

### Known pitfall: sqlglot dependency conflict on `superset-init`
If `superset_init` exits 1 with a `uv`/`sqlglot` "No solution found" resolution error, the local
repo checkout is **ahead of** the published image. The compose file bind-mounts the local
`./superset-core`, which the image tries to reinstall editable, clashing with the image's pinned
`apache-superset` (e.g. local core wants `sqlglot>=30.8`, image wants `<29`).

Workaround (local dev only, uncommitted):
1. Remove the `- ./superset-core:/app/superset-core` line from `docker-compose-image-tag.yml`
   (it lives under the `x-superset-volumes` anchor). Overrides can't remove an anchored volume, so
   edit the file directly.
2. `printf 'DEV_MODE=false\n' > docker/.env-local` (prevents the editable reinstall).
3. `docker compose -f docker-compose-image-tag.yml down && ... up -d` again.

Note this runs the **image's** code (e.g. 6.1.0), NOT the local `master` checkout. To test local
code changes you must do a native run instead (build frontend + `superset db upgrade`/`init` +
`superset run`), which is much slower. Examples data is loaded automatically by `superset-init`
(`SUPERSET_LOAD_EXAMPLES=yes` in `docker/.env`).

## Golden-path UI tests (each has a concrete, falsifiable assertion)
1. **Dashboard render** — Home → open "World Bank's Data". Assert big-number (~7.24B), colored
   world map, and a populated country table all render (no empty/error panels).
2. **Explore re-run** — Charts → open a Table chart (e.g. "Most Populated Countries"). Note the
   row-count badge (e.g. 214 rows). Change **Row limit** to a small custom value (type `5` into the
   dropdown search — presets start at 10), click **Update chart**. Assert the badge and table both
   show exactly 5 rows. Leaving Explore prompts a "Save changes?" dialog → click **Discard**.
3. **SQL Lab** — SQL → SQL Lab. Pick database (e.g. `examples`) + schema (`public`), then click
   **Add a new tab** to get an editor (selecting a DB alone does not create one). Type a query and
   Run. Assert a results grid with the expected row count and success (not a red error).
   - Postgres folds unquoted identifiers to lowercase. The example `wb_health_population` columns
     are **uppercase** (e.g. `SP_POP_TOTL`), so reference them quoted: `SUM("SP_POP_TOTL")`.

## Devin Secrets Needed
None. Runs fully locally with the default admin/admin account and bundled example data.
