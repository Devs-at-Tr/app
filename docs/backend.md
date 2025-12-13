# Backend Documentation

[← Back to Overview](../README.md) · [Frontend Docs](./frontend.md) · [DB](./backend.database.md) · [Migrations](./backend.migrations.md)

## Stack
- FastAPI (ASGI) with Starlette middleware
- SQLAlchemy ORM; MySQL by default (supports Postgres/SQLite via `DB_TYPE`)
- Alembic-style timestamped migrations (custom runner)
- JWT auth (PyJWT), bcrypt for hashing
- Uvicorn ASGI server; WebSocket endpoint at `/ws`
- Requests/httpx for Meta (Facebook/Instagram) APIs

## Project layout
```
backend/
  server.py            # FastAPI app, routers mounted
  models.py            # SQLAlchemy models (users, chats, messages, pages, etc.)
  schemas.py           # Pydantic schemas
  routes/              # Auth, users, chat helpers, etc.
  migrations/          # Timestamped migration scripts + runner
  utils/               # helpers (timezone, mailer, etc.)
  websocket_manager.py # WS broadcast helper
  .env_example         # backend env template
```

## Running locally
```bash
cd backend
cp .env_example .env   # fill DB + Meta + SMTP + bridge vars
pip install -r requirements.txt
python run_all_migrations.py   # or: python -m migrations.runner
uvicorn server:app --reload --port 8000
```

## Environment
Key variables (see `.env_example`):
- DB: `DB_TYPE` (`mysql|postgres|sqlite`), `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE`, or `POSTGRES_URL`
- Auth/CORS: `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRATION_MINUTES`, `CORS_ORIGINS`
- Meta integrations: `FACEBOOK_*`, `INSTAGRAM_*`, `PIXEL_ID`, `GRAPH_VERSION`, `VERIFY_TOKEN`
- SMTP/password reset: `SMTP_*`, `SUPPORT_CONTACT_EMAIL`, `PASSWORD_RESET_*`, `FRONTEND_BASE_URL`
- CRM bridge/admin: `ADMIN_URL`, `FORM_TOKEN`, `UID`, `BID`, `AUTHORIZATION`, `ADMIN_COOKIE` (used by inquiry/employee bridging endpoints)

## API surface (high level)
- `/api/auth/*` – login, token handling
- `/api/users/*` – user management, permissions, agent lists
- `/api/chats/*` – chat list/detail, assign/unassign, send messages, mark read
- `/api/facebook/*` & `/api/webhooks/facebook` – FB page connect + webhook
- `/api/webhooks/instagram` – IG DM webhook handling
- `/api/inquiries/insert` – bridge to external CRM endpoints (uses admin bridge envs)
- `/ws` – WebSocket for real-time chat updates/notifications

## Permissions & roles
- Roles include admin/agent/supervisor; permissions are enforced in route dependencies (see `routes/dependencies.py` and `permissions.py`).
- Round-robin assignment respects `can_receive_new_chats` and active agents (see `routes/chat_helpers.py` and assignment helpers in `server.py`).

## Tests
- Pytest configured; install dev deps (`pip install -r requirements.txt`) and run `pytest` from `backend/`.

## Deployment notes
- Use `uvicorn`/`gunicorn` with appropriate workers; ensure `.env` is provided.
- Configure DB connectivity and run migrations before starting application pods.
- Proxy `/api` and `/ws` to the ASGI app; serve frontend separately or via proxy static host.

## Maintenance
- When changing models/schema: add a migration (see `docs/backend.migrations.md`) and update `docs/backend.database.md`.
- When adding routes: document in the API section above and ensure permissions are applied.
- Keep `.env_example` aligned with required settings.
