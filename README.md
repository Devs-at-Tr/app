# TickleGram Messenger CRM

Full-stack CRM for Instagram/Facebook messaging: FastAPI backend + React (CRACO/CRA) frontend with MySQL-first configuration and JWT auth/permissions.

[Frontend Docs](docs/frontend.md) · [Backend Docs](docs/backend.md)

## Overview
- Unified inbox for Instagram DMs and Facebook Messenger with agent assignment and round-robin auto-assign.
- Role-based access (admins, agents, supervisors) with JWT auth.
- FastAPI + SQLAlchemy + Alembic-style migrations; MySQL by default (Postgres/SQLite supported via env switch).
- React + Tailwind + shadcn/ui + CRACO, axios for API, React Router, Zustand state.

## Quick Start (local)

### Prerequisites
- Python 3.10+
- Node.js 18+ (Yarn 1.22 is configured via `packageManager`)
- MySQL 8+ (or set `DB_TYPE=sqlite`/`postgres` in env)

### Backend
```bash
cd backend
cp .env_example .env   # fill DB + Meta/SMTP secrets
pip install -r requirements.txt
# Run migrations (custom runner applies timestamped scripts)
python run_all_migrations.py
# or python -m migrations.runner
uvicorn server:app --reload --port 8000
```
- Key envs (see `.env_example`): `DB_TYPE`, `MYSQL_*` (or `POSTGRES_URL`), `JWT_*`, `CORS_ORIGINS`, Meta creds (`FACEBOOK_*`, `INSTAGRAM_*`, `PIXEL_ID`, `GRAPH_VERSION`), email SMTP, admin bridge vars (`ADMIN_URL`, `FORM_TOKEN`, `UID`, `BID`, `AUTHORIZATION`) used for CRM bridging endpoints.
- API served at `/api/*`; WebSocket at `/ws`.

### Frontend
```bash
cd frontend
yarn install
cp .env .env.local  # or create .env with REACT_APP_BACKEND_URL
yarn start          # runs craco start on :3000
```
- Env: `REACT_APP_BACKEND_URL` (point to backend), optional Meta IDs if used in UI.

### Running the stack
- Start backend first, ensure DB reachable and migrations applied.
- Start frontend; open http://localhost:3000.

## Documentation
- [Frontend](docs/frontend.md): stack, structure, commands, env, API patterns, state management.
- [Backend](docs/backend.md): stack, structure, commands, env, API/routers, auth/permissions, deployment notes.
- [Database & migrations](docs/backend.database.md, docs/backend.migrations.md) for schema/migration process.
- Legacy/historical docs are referenced from stubs under `docs/_legacy`.

## Maintenance
- When you add backend routes or DB columns: update `docs/backend.md` and `docs/backend.database.md` (and migrations guide if process changes).
- When you add frontend routes/state patterns: update `docs/frontend.md`.
- Keep `.env_example` in sync with required settings.

## Navigation
[Frontend Docs](docs/frontend.md) · [Backend Docs](docs/backend.md) · [Backend Database](docs/backend.database.md) · [Backend Migrations](docs/backend.migrations.md)
