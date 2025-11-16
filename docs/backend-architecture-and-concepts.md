## Tech Stack Overview

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (synchronous style) on top of Starlette. Single app defined in `backend/server.py`.
- **Data Layer**: SQLAlchemy ORM (`backend/database.py`, `backend/models.py`) with optional MySQL/PostgreSQL backends and SQLite fallback. Migrations are home-grown scripts under `backend/migrations/`.
- **Validation / Schemas**: Pydantic models in `backend/schemas.py` (requests / responses / enums).
- **Auth / Security**: JWT access tokens via `python-jose` (`backend/auth.py`), bcrypt password hashing, role/permission helpers in `backend/permissions.py`.
- **External Integrations**:
  - Instagram Graph API client (`backend/instagram_api.py`)
  - Facebook Graph API client (`backend/facebook_api.py`)
  - Meta template submission helper (`backend/meta_template_api.py`)
  - HMAC helpers (`backend/instagram_hmac.py`) and attachments downloaders.
- **Networking / HTTP Clients**: `httpx.AsyncClient` instances for Meta calls; occasional `requests` for attachment download.
- **Real-time Delivery**: WebSockets managed via `backend/websocket_manager.py` (per-user connection registry).
- **Utility Modules**: timezone helpers (`backend/utils/timezone.py`), mock data generators, CLI scripts for database bootstrapping.

## Project Structure (Backend)

```
backend/
├── server.py                 # Main FastAPI app, 4k+ lines covering routers + business logic
├── models.py                 # SQLAlchemy ORM models for all entities
├── schemas.py                # Pydantic request/response models and enums
├── database.py               # Engine/session creation, DB_TYPE switching
├── auth.py                   # JWT + password helpers
├── permissions.py            # Permission enums and helpers
├── instagram_api.py          # Instagram Graph API wrapper
├── facebook_api.py           # Facebook Graph API wrapper
├── meta_template_api.py      # Template submission/check helper
├── websocket_manager.py      # Connection management for ws:// endpoints
├── migrations/               # Snapshot + runner scripts for schema diffs
├── utils/                    # Timezone utilities, etc.
├── attachments/              # Downloaded media referenced in messages
└── assorted CLI helpers (seed_data, add_* scripts, etc.)
```

All HTTP endpoints live in `server.py` under a single `APIRouter` (`/api`). Supporting modules are imported there and used directly.

## FastAPI Architecture & Core Concepts Used

### Application & Router Setup

- `backend/server.py` instantiates `app = FastAPI(...)` near the top and a dedicated `api_router = APIRouter(prefix="/api")`.
- All endpoints (auth, chats, templates, comments, marketing, webhooks, admin) are defined inline on this router: e.g. `@api_router.post("/auth/login")`.
- The router is registered once via `app.include_router(api_router)` near the bottom.
- Global websocket endpoint `/ws` is defined directly on `app`.
- Middleware: CORS is applied at startup by reading `CORS_ORIGINS` env var. If `*`, the middleware allows any origin via regex; otherwise the provided CSV list is used. No other custom middleware is defined (logging/auth handled in endpoints instead).
- Startup/shutdown events are not separately declared; SQLAlchemy engine is created eagerly in `database.py`.

### Dependencies

- `get_db()` from `backend/database.py` yields a synchronous `Session`. It is used throughout `server.py` via `Depends(get_db)`.
- `get_current_user`, `get_admin_user`, `get_admin_only_user`, `require_super_admin`, and permission-specific dependency factories (`require_permissions`, `require_any_permissions`) encapsulate JWT decoding, role checking, and permission code validation. These live around lines 1450–1500 of `server.py`.
- Permissions (custom enums defined in `backend/permissions.py`) decorate endpoints to enforce role-based and position-based access control.
- Other dependencies include helper functions like `resolve_default_instagram_account`, `resolve_instagram_access_token`, and `resolve_meta_entity_for_template`.

### Request / Response Models

- Pydantic schemas in `backend/schemas.py` define structures such as `UserResponse`, `TokenResponse`, `ChatResponse`, `MessageResponse`, `InstagramCommentSchema`, `InstagramInsightSchema`, etc.
- Endpoints reference these models in their `response_model` parameter to document outputs and convert ORM objects to JSON (via `.model_validate()` and `.model_dump()` before returning or broadcasting).
- Request payloads also leverage these Pydantic models (e.g., `InstagramSendRequest`, `TemplateSendRequest`, `InstagramCommentCreateRequest`), enabling validation before hitting business logic.

### Major Route Groups (All in `server.py`)

- **Auth (`/auth/*`)**: register, login, forgot/reset password, fetch auth config & current user. All async endpoints relying on JWT issuance via `create_access_token`.
- **Users / Positions / Permissions**: CRUD operations for accounts, listing permissions, assigning positions, etc.
- **Chat & Messaging**: endpoints under `/chats`, `/messages`, `/send` for fetching conversation lists, posting agent replies, marking chats as read, assigning chats to agents.
- **Comments**: `/instagram/comments`, `/facebook/comments`, plus actions to reply/create/hide/delete Instagram comments.
- **Templates**: create/list/update message templates, submit to Meta, check status, send template-based outreach.
- **Webhooks**:
  - `/webhooks/instagram` (`GET` for verification, `POST` for DM/comment payloads) and `/webhook` alias.
  - `/webhooks/facebook` for Messenger events.
- **Insights & Marketing**: `/insights/account|media|story` plus `/marketing/events` (Conversions API).
- **Admin Utilities**: endpoints to connect/disconnect Instagram accounts and Facebook pages, fetch dashboard stats, run schema snapshots, generate mock data, etc.
- **WebSocket**: `/ws` endpoint attaches to `websocket_manager` and uses JWT tokens for authentication.

### Request Flow Summary

1. Incoming HTTP request hits `/api/...`.
2. FastAPI dependency injection obtains a DB session plus any user/permission context.
3. Endpoint logic (mostly `async def`) interacts with SQLAlchemy models and, when necessary, calls out to Graph API wrappers.
4. Responses are built from Pydantic schemas; websockets use `ws_manager.broadcast_*` for realtime updates.

## Database Layer & Models

- **Engine & Sessions**: `backend/database.py` constructs a SQLAlchemy engine based on `DB_TYPE` env var. MySQL is the documented default (schema names like `pf_messenger`), but PostgreSQL or SQLite fallback is supported. `SessionLocal` is a synchronous session factory reused per request.
- **Models**: `backend/models.py` defines ~30 tables. Key ones:
  - `User`, `Position`, `UserRole`, and linking tables for permissions.
  - `Chat` (conversation metadata) with relationships to `InstagramUser`/`FacebookUser` and message tables.
  - `InstagramMessage` / `FacebookMessage` and `InstagramMessageLog` (raw payload audit log).
  - `MessageTemplate` with Meta submission fields.
  - `InstagramAccount`, `FacebookPage` storing access tokens and linked page info.
  - `InstagramComment`, `InstagramInsight`, `InstagramMarketingEvent`.
  - Schema change tracking tables (`DBSchemaSnapshot`, `DBSchemaChange`).
- **Relationships**: Chats have one-to-many relations with messages; message tables mix in shared fields via `ChatMessageMixin`. Users have many chats (assigned_to) and Instagram/Facebook accounts.
- **Migrations**: Instead of Alembic, the repo uses scripts under `backend/migrations/` to snapshot schema state and detect diffs. Files like `20251114_210000_db_schema_tracking.py` apply new tables. Runner invoked via CLI (`migrations/runner.py` imported early by `server.py`).
- **Other Storage**: Local filesystem directories `backend/attachments/instagram/...` store downloaded media for DM attachments. No Redis/NoSQL caches appear in the backend.

## Key Business Flows

### Authentication & Authorization

- `/api/auth/login`: verifies user email/password via `verify_password` (bcrypt). On success, issues JWT with `create_access_token` and returns `TokenResponse`.
- `/api/auth/register` & `/auth/signup`: create users, hashing passwords with `get_password_hash`.
- `/api/auth/me`: uses `get_current_user` to return profile info.
- Forgot/reset flows (`/auth/forgot-password`, `/auth/reset-password`) stub out email sending but update password in DB when given valid reset tokens (currently stored in-memory or derived from timestamp).
- Roles/permissions: `User.role` (Admin, Agent, etc.) plus `permissions.py` enumerations. Dependencies `require_permissions(...)` ensure endpoints only accessible to certain roles (e.g., comments management).

### Chat & Direct Messaging

- Listing chats: `/api/chats` queries `Chat` with filters (status, platform, assigned agent) and eager-loads related user records.
- Sending DM: `/api/messages/send` (`instagram_dm_send`) resolves page/account tokens, calls `instagram_client.send_dm`, writes to `InstagramMessageLog` + `InstagramMessage`, updates chat metadata, then notifies watchers via websockets (`ws_manager.broadcast_to_users`). Messenger responses follow similar logic but use `facebook_client`.
- Receiving DM: `/api/webhooks/instagram` (POST) validates HMAC, loops through entries → messages, resolves `Chat`/`InstagramUser`, stores logs/messages, downloads attachments, updates unread counts, and broadcasts events. Outbound echos from TickleGram are filtered.
- Messenger webhook path mirrors the above but for Facebook.

### Comments & Engagement

- `/api/instagram/comments` fetches comments per connected IG account using `instagram_client.get_media_comments`, normalizes results, and returns them to the UI.
- Actions like reply/create/hide/delete call the respective Graph API endpoints, update `InstagramComment` via `upsert_instagram_comment`, and broadcast comment events globally.
- `/api/facebook/comments` polls each connected page using `facebook_client.get_page_feed_with_comments` (currently in “fetch-then-display” mode; not persisted).

### Templates

- `MessageTemplate` CRUD endpoints allow teams to create message snippets and mark them Meta-approved.
- `/api/templates/{id}/meta-submit` uses `meta_template_api.submit_template` to send normalized payloads to Meta, storing the returned submission ID/status.
- `/api/templates/{id}/send` infers the target platform from the chat, optionally uses the Meta template ID (`message_creative_id`), and dispatches via `instagram_client` or `facebook_client`.

### Insights & Marketing

- `/api/insights/account|media|story` call the respective Instagram endpoints (`/{id}/insights`), persist metrics via `persist_instagram_insight`, and broadcast summary events.
- `/api/marketing/events` maps payloads to Conversions API format, calls `instagram_client.send_marketing_event`, logs success/error, and stores details in `InstagramMarketingEvent`.

### Integrations & Webhooks

- Instagram/Facebook webhook routes are the main ingestion points. Both verify hub challenges, enforce signatures, parse payloads, and ensure each new DM/comment is mirrored in the SQL tables.
- Template submission + status-check endpoints integrate with Graph API v24.0, using app tokens to fetch page access tokens when necessary.
- Misc scripts (e.g., `add_facebook_page_user.py`) provide admin utilities for linking pages/accounts offline.

### Narrative Example: Agent Replies to DM

1. Frontend calls `POST /api/messages/send` with `igsid`, text, attachments, and Bearer token.
2. Dependency chain: `get_current_user` verifies JWT → `get_db` session.
3. Endpoint resolves the appropriate Instagram account & page token via `resolve_instagram_access_token`.
4. `instagram_client.send_dm` (httpx POST to `/{page_id}/messages`) returns `message_id`.
5. Server logs the outbound message (both `InstagramMessageLog` and `InstagramMessage`), updates chat `last_message` / `updated_at`, and commits.
6. `ws_manager.broadcast_to_users` notifies assigned agents/admins with a `new_message` event plus a legacy DM payload for compatibility.

## Background Tasks & External Integrations

- **WebSocket Manager**: `backend/websocket_manager.py` queues messages for offline users and broadcasts updates for events (DMs, comments, insights).
- **Background Jobs**: No Celery/RQ; long-running operations (e.g., Meta API calls, attachment downloads) run inline within request handlers. The only “async worker” style logic is the WebSocket broadcasting plus asynchronous httpx calls.
- **External APIs**:
  - `instagram_client` & `facebook_client`: wrap HTTP requests with logging, retry logic (Conversions API) and helper methods (profile lookup, comment moderation, insights).
  - Template API: uses httpx to talk to Graph API v24.0 for template management.
  - Attachment downloads: synchronous `requests.get` to fetch media and persist under `backend/attachments/`.

## Configuration & Environments

- `.env` and `.env_example` contain configuration (DB creds, Meta secrets, JWT secret, CORS origins, feature flags, etc.).
- `database.py` loads `.env` and switches DB connections based on `DB_TYPE` plus vendor-specific env vars.
- Key environment variables:
  - `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRATION_MINUTES`
  - `DB_TYPE`, `MYSQL_*`, `POSTGRES_URL`
  - `INSTAGRAM_APP_SECRET`, `FACEBOOK_APP_SECRET`, `INSTAGRAM_PAGE_ACCESS_TOKEN`
  - `GRAPH_VERSION`, `INSTAGRAM_MODE`, `FACEBOOK_MODE`, template mode flags
  - `CORS_ORIGINS` for allowed frontend hosts
  - Feature toggles like `INSTAGRAM_SKIP_SIGNATURE`, `INSTAGRAM_HMAC_DEBUG`
- Secrets are loaded directly via `os.getenv` without a centralized settings object. Most defaults are permissive (e.g., wildcard CORS) for development; production should override them.

## Error Handling, Logging & Observability

- **Error Handling**: relies on FastAPI/Starlette defaults plus explicit `HTTPException` raises. No custom exception handlers or error middleware beyond those built-ins.
- **Logging**:
  - `logging.basicConfig` is configured at the top of `server.py` with INFO-level logs and a simple `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'` format.
  - Modules like `instagram_api.py`/`facebook_api.py` use module-level loggers for API call success/failure; webhook handler logs incoming payloads and duplicates.
  - WebSocket manager logs connection events. No structured logging or external sinks configured.
- **Observability**: No built-in tracing, metrics, Prometheus, or Sentry instrumentation. Operators rely on FastAPI/Uvicorn logs.

## Suggested Improvements (Without Changing Behaviour)

### Performance & Scalability

1. **Modularize `server.py`** (`backend/server.py`): the 4k+ line monolith makes hot paths hard to reason about. Split into routers (auth, chats, comments, webhooks, templates) and include via `app.include_router`. This keeps behaviour identical but improves maintainability and testability.
2. **Async IO Consistency**: Some endpoints call synchronous helpers (e.g., `requests.get` for attachments, SQLAlchemy sync sessions) inside `async def`. Consider either switching to async DB drivers OR running these blocking calls in thread executors to avoid starving the event loop during bursts (particularly webhooks downloading media).
3. **Database Access Patterns**: Chat queries often fetch related entities lazily (see `_hydrate_instagram_chat_messages`). Use `.options(joinedload(...))` where possible or restructure to reduce N+1 fetches when listing chats.
4. **Caching for Expensive Reads**: Comments and insights endpoints hit Meta APIs every time. Introducing a short-lived cache (Redis) could offload repeated requests when the UI polls frequently.

### Security & Reliability

1. **JWT / Session Hardening**: Currently, JWTs never include claims like `iat`, `iss`, or token versioning, and there is no refresh strategy. Document and enforce rotation/blacklisting if user roles are sensitive (`backend/auth.py`).
2. **CORS Restrictions**: Default `CORS_ORIGINS='*'` means any origin can hit the API with credentials. In production, set explicit origins to mitigate CSRF-like risks (`server.py` bottom). Document this in deployment runbooks.
3. **Rate Limiting Webhooks & Login**: Add simple throttling or signature validation metrics for `/webhooks/*` and `/auth/login` to avoid abuse. Tools like `slowapi` integrate cleanly with FastAPI.
4. **Secret Management**: Consolidate env access via Pydantic Settings or similar to avoid scattering `os.getenv` calls and to ensure required secrets (e.g., `INSTAGRAM_APP_SECRET`) are validated early. Helps catch misconfigurations before runtime.
5. **Attachment Download Safety**: `_download_instagram_attachment` (`server.py`) writes files directly under `attachments/` without virus scanning or size checks. Consider bounding file size and sanitizing paths more strictly to avoid resource exhaustion.

### Maintainability & Code Health

1. **Dedicated Service Layer**: Large sections of `server.py` perform orchestration (resolve chat, call external API, persist, broadcast). Extract them into services (e.g., `services/chats.py`, `services/webhooks.py`) to isolate business rules and ease testing.
2. **Docstrings & Type Hints**: Many helper functions lack docstrings and `->` annotations. Annotating return types for functions like `resolve_instagram_access_token` or `gather_dm_notify_users` would improve IDE assistance.
3. **Schema & Model Sync**: Document how the custom migration system should be used, and consider adopting Alembic for consistency. Manual runner scripts risk diverging from actual `models.py`.
4. **Unit / Integration Tests**: Current `tests/` directory is sparse. Add tests for critical flows (auth, DM send/receive) to prevent regressions when reorganizing.
5. **Background Task Offloading**: Webhooks synchronously handle attachments, DB writes, and websocket broadcasts. Introducing `BackgroundTasks` or a job queue would decouple critical HTTP responses from downstream failures (Meta expects 200 OK quickly).

### Operational Enhancements

1. **Health/Readiness Endpoints**: Add `/healthz` and `/readiness` routes to check DB connectivity and external API status.
2. **Observability**: Integrate structured logging or tracing (e.g., OpenTelemetry) to correlate incoming webhook IDs with outgoing Graph API calls.
3. **Configuration Profiles**: Provide example `.env` files for dev/staging/prod with recommended settings (JWT secret lengths, DB URLs, CORS). Document environment-specific overrides.

## Appendix: Important Modules & Where To Look

- **FastAPI App & Routes**: `backend/server.py`
- **Database / Session Management**: `backend/database.py`
- **ORM Models**: `backend/models.py`
- **Pydantic Schemas**: `backend/schemas.py`
- **Auth Helpers**: `backend/auth.py`, `backend/permissions.py`
- **Meta Integrations**:
  - Instagram API client: `backend/instagram_api.py`
  - Facebook API client: `backend/facebook_api.py`
  - Template API: `backend/meta_template_api.py`
- **WebSockets**: `backend/websocket_manager.py`
- **Migrations / Schema Snapshots**: `backend/migrations/`
- **Utility Scripts**: `backend/add_facebook_page_user.py`, `backend/generate_mock_data.py`, etc.

Use this document alongside the source files to understand the full lifecycle of a request—from API call, through dependency injection, database operations, third-party interactions, and realtime notifications. Together they provide a map for future improvements without altering the existing business behaviour.
