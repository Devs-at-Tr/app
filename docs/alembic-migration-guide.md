# Alembic Migration Guide

Practical notes for creating and running database migrations now that the project ships a standard Alembic setup alongside the legacy timestamped scripts.

## Key paths
- `alembic.ini` — root config pointing to `backend/migrations`.
- `backend/migrations/env.py` — wires Alembic to `database.get_database_url()` and `Base.metadata`.
- `backend/migrate_to_mysql.py` — one-time bootstrap that creates all tables from models (useful for fresh MySQL instances before applying migrations).
- Legacy runner: `backend/migrations/runner.py` still exists but the Alembic flow below is the recommended path.

## Running migrations
Run commands from the repo root so Alembic picks up `alembic.ini`:

```bash
alembic upgrade head        # apply all migrations
alembic current             # show the current revision
alembic history --verbose   # list migrations with details
```

Notes:
- The DB URL is resolved at runtime via `get_database_url()`; make sure your `.env` is loaded or exported.
- Some older migrations have `downgrade()` unimplemented; plan forward-only upgrades.
- SQLite is supported but lacks some ALTER capabilities; certain migrations (e.g., server defaults) are guarded for SQLite and may leave slight differences vs. MySQL/Postgres.

## Creating a new migration
1. Update models and/or metadata (e.g., `backend/models.py`).
2. Generate a revision using the timestamped naming convention:
   ```bash
   alembic revision --autogenerate -m "20251208_add_widget_flag"
   ```
   - Prefer the `YYYYMMDD_HHMMSS_description` slug used by recent files like `20251207_000000_lead_form_flag.py`.
3. Review the generated script:
   - Confirm adds/drops/alterations match the intended schema change.
   - For cross-dialect compatibility, avoid backend-specific types when possible.
   - Add defensive checks (e.g., inspector-based existence guards) if a migration might be re-run or if legacy DBs can be out of sync.
4. Run it locally:
   ```bash
   alembic upgrade head
   ```
5. Commit the new revision file with your code changes.

## Troubleshooting & tips
- **Autogenerate misses defaults/constraints**: Autogenerate may skip server defaults or some index changes; edit the revision manually to add `server_default` or `op.create_index` calls.
- **Mixed sources of truth**: Older “manual” migrations may have diverged from `models.py`. When in doubt, inspect the live DB (`alembic revision --autogenerate` will highlight diffs) and align in the new revision.
- **Large backfills**: For data backfills, prefer chunked `UPDATE`/`INSERT` statements and keep them idempotent so re-runs are safe.
- **Environment selection**: Set `DATABASE_URL` (or the variables consumed by `get_database_url()`) before running Alembic to target the right environment.
- **Fresh installs**: For a clean MySQL DB, you can run `python backend/migrate_to_mysql.py` to create tables, then `alembic upgrade head` to apply incremental changes.
