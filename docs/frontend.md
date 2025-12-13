# Frontend Documentation

[← Back to Overview](../README.md) · [Backend Docs](./backend.md)

## Stack
- React (CRA + CRACO), React Router
- Tailwind + shadcn/ui (Radix UI primitives)
- Axios for API calls
- Zustand for client state
- Date handling with date-fns

## Project layout
```
frontend/
  src/
    components/      # UI + feature components (modals, chat UI, forms)
    pages/           # Routed views
    hooks/           # Custom hooks, state helpers
    lib/             # Utilities (e.g., API helpers, formatting)
    styles/          # Tailwind/theme config
  craco.config.js    # CRACO overrides for CRA
  package.json       # scripts + deps
```

## Commands
```bash
yarn install              # install deps (packageManager pinned to yarn@1.22.x)
yarn start                # dev server on http://localhost:3000 (craco start)
yarn build                # production build
```

## Environment variables
Create `frontend/.env` (or `.env.local`):
- `REACT_APP_BACKEND_URL` – Base URL for API/WebSocket (e.g., http://localhost:8000)
- Optional Meta IDs if surfaced in UI (e.g., Facebook/Instagram app IDs)

## API & data flow
- Axios instance(s) under `src/lib` hit the FastAPI backend at `/api/*`.
- Auth: JWT token stored client-side; attach `Authorization: Bearer <token>` on requests.
- Chat and assignment flows map to backend routes (`/api/chats`, `/api/users/agents`, etc.).
- WebSocket: backend exposes `/ws` for real-time events; ensure URL uses the same host as `REACT_APP_BACKEND_URL`.

## State & conventions
- Use Zustand stores for global app state (auth/session, chats, UI flags).
- Components lean on shadcn/ui + Tailwind utility classes; prefer composition over heavy component inheritance.
- Forms: React Hook Form + Zod for validation where present; fall back to inline validation in specific modals.
- Routing: React Router v7; keep route components light and move logic into hooks/stores.

## Running against backend
1. Start backend (`uvicorn server:app --reload`) and ensure CORS allows your frontend origin.
2. Set `REACT_APP_BACKEND_URL` to the backend host/port.
3. Start frontend with `yarn start`.

## Build/Deploy notes
- `yarn build` outputs to `build/`; serve via any static host or behind your backend/proxy.
- If reverse proxying, forward `/api` and `/ws` to the FastAPI server; serve static files from `frontend/build`.

## Maintenance
- When adding API calls: centralize axios config/helpers; update this doc if endpoints or auth patterns change.
- When adding shared UI: place in `src/components` with clear props; prefer hooks in `src/hooks`.
- Keep env variable list in sync with new requirements.
