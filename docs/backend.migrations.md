# Backend Migrations

[← Back to Overview](../README.md) · [Backend](./backend.md) · [Database](./backend.database.md)

## Tooling
- Alembic-style timestamped scripts under `backend/migrations/` (pattern `YYYYMMDD_HHMMSS_<name>.py`).
- Custom runners:
  - `python run_all_migrations.py` (wrapper that also runs pre/post tasks)
  - `python -m migrations.runner` (direct apply)

## Workflow
1. Create a new migration file in `backend/migrations/` with the timestamped naming convention.
2. Implement `upgrade()`/`downgrade()` (or equivalent) per existing migration patterns.
3. Run locally: `python run_all_migrations.py` (ensure env is set).
4. Verify DB locks on MySQL before running in shared environments to avoid `Lock wait timeout`.

## Environment
- Uses the same `.env` as the app; DB connection determined by `DB_TYPE` and `MYSQL_*` or `POSTGRES_URL`.
- `CORS_ORIGINS`, Meta, and other app envs are not required for schema-only runs, but DB envs must be present.

## Troubleshooting
- Lock timeouts (`1205`): check for long-running transactions before applying DDL; retry during low traffic or increase `innodb_lock_wait_timeout` temporarily.
- Interpolation errors: ensure DB URLs are properly escaped (`%` must be doubled in Alembic ini contexts).
- Logging config errors: migration env catches missing formatters; keep `alembic.ini` aligned with the runner.

## Legacy references
- Historical how-tos and special-case fixes: see `docs/_legacy/alembic-migration-guide.md`, `docs/_legacy/TIMEZONE_FIX.md`, and other legacy files for context.
