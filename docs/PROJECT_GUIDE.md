# TickleGram Project Guide

This single reference replaces the scattered Markdown notes that used to live at the root of the repository. It captures the practical information from the former quick-start, integration, bug-fix, optimization, and prompt documents so future contributors have one place to look.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Platform Integrations](#platform-integrations)
   - [Instagram DM Support](#instagram-dm-support)
   - [Facebook Permissions & Review Assets](#facebook-permissions--review-assets)
   - [Facebook WebSocket Fix](#facebook-websocket-fix)
   - [Template Messaging & Mobile UI](#template-messaging--mobile-ui)
3. [Product & Access Control Changes](#product--access-control-changes)
4. [Engineering Notes & Fixes](#engineering-notes--fixes)
   - [General Bug Fixes](#general-bug-fixes)
   - [Chat Sidebar Improvements](#chat-sidebar-improvements)
   - [Dashboard Optimization](#dashboard-optimization)
   - [WebSocket Infinite Loop Fix](#websocket-infinite-loop-fix)
   - [Regression Test Snapshot](#regression-test-snapshot)
5. [Emergent-AI Prompt Brief](#emergent-ai-prompt-brief)

---

## Quick Start

1. **Backend**
   - `cd backend && pip install -r requirements.txt`
   - Optional: `python seed_data.py`
   - Start FastAPI: `uvicorn server:app --reload --port 8000`
2. **Frontend**
   - `cd frontend && npm install`
   - Start React dev server: `npm start` (http://localhost:3000)
3. **Default Credentials**
   - Admin: `admin@ticklegram.com / admin123`
   - Agents: `agent1@ticklegram.com / agent123`, `agent2@ticklegram.com / agent123`
4. **Mock Facebook Workflow**
   - Backend defaults to `FACEBOOK_MODE=mock`
   - Generate chats: `POST /api/mock/generate-chats?count=5&platform=facebook`
   - Manage mock pages via **Dashboard → Manage Facebook Pages**
5. **Switching to Real Facebook API**
   - Set `FACEBOOK_MODE=real` plus real App credentials in `backend/.env`
   - Connect a real Page through the in-app page manager
6. **Troubleshooting**
   - Backend issues: check Python 3.8+, `pip install`, port 8000 usage
   - Frontend issues: Node 14+, `npm install`, port 3000 usage
   - Use README for deeper setup details.

### Database Model Updates
- Run `python -m migrations.runner` to apply timestamped migrations (files named `YYYYMMDD_HHMMSS_description.py`). Add new files for every schema change instead of editing legacy scripts.
- Conversations now live in platform-specific tables (`instagram_messages`, `facebook_messages`). Instagram webhook archives were renamed to `instagram_message_logs`.
- Facebook recipients have a first-class `facebook_users` table; chats now reference either `facebook_user_id` or `instagram_user_id` based on platform. The legacy `messages` table was retired after migrating its rows into the new platform tables.

---

## Platform Integrations

### Instagram DM Support

*Highlights from `INSTAGRAM_INTEGRATION.md` and `INSTAGRAM_INTEGRATION_GUIDE.md`.*

- **Architecture**: Shared FastAPI backend + React frontend; JWT roles (Admin/Agent); MySQL/Postgres/SQLite via SQLAlchemy.
- **Backend Work**
  - `instagram_api.py` supplies mock/real clients, webhook signature checks, user profile fetches, DM sending, story/comment helpers, and insight fetchers.
  - `/api/webhooks/instagram` (GET for verification, POST for payloads) plus `/webhook` aliases.
  - Instagram accounts CRUD (`/api/instagram/accounts`), `instagram_users` and `instagram_messages` persistence, WebSocket broadcasts (`type: "ig_dm"`), and comment/insight endpoints.
- **Frontend Work**
  - Platform-aware UI (icons, filters, template selector), Instagram account manager components, story/comment handling, platform-specific message renderers.
- **Configuration**
  - Reuse Facebook App credentials: `INSTAGRAM_APP_ID/SECRET`, `INSTAGRAM_WEBHOOK_VERIFY_TOKEN`, `INSTAGRAM_API_VERSION`.
  - Instagram professional account + linked Facebook Page required; permissions `instagram_basic`, `instagram_manage_messages`.
- **Phases & Considerations**
  - Phase 1: API setup & webhook subscription.
  - Phase 2: Backend ingestion/sending & account management.
  - Phase 3: Frontend UX, story/post interactions, QA.
  - Watch for rate limits, media handling, and Meta’s 24-hour rules.

### Facebook Permissions & Review Assets

*Condensed from `FACEBOOK_PERMISSION_REQUEST.md` and `FACEBOOK_PERMISSION_TEST_PLAN.md`.*

- **Permission Justification (`pages_messaging`)**
  - Explains CRM use-case: inbound message reception, agent response tooling, assignment & collaboration, 24-hour compliance enforcement, message tag usage, and data minimization.
  - Highlights value to admins (efficiency, compliance, better CX).
- **Review Test Plan**
  - Supplies test admin/agent accounts, sample Page info, and step-by-step flows reviewers should exercise (connect Page, assign agents, send/receive messages, demonstrate 24-hour indicators/tags, audit history, multi-agent scenarios, blocked post-window sends).
  - Recording guidelines: 1080p, <5 minutes, no sensitive info.

### Facebook WebSocket Fix

*From `FACEBOOK_WEBSOCKET_FIX.md`.*

- Root cause: Facebook webhook handler saved messages but never incremented unread counts nor broadcasted WebSocket events.
- Fix adds:
  - `chat.unread_count += 1` and `chat.updated_at = now`.
  - `db.refresh(new_message)` before broadcasting.
  - Notification set = assigned agent + all admins.
  - WebSocket payload matches Instagram path so UI updates instantly.

### Template Messaging & Mobile UI

*Based on `TEMPLATE_AND_MOBILE_IMPLEMENTATION.md`.*

- **Message Templates**
  - `MessageTemplate` model + migration, CRUD APIs, schema validations, template-sending endpoint with variable substitution (`{username}`, `{platform}`, custom placeholders).
  - React template manager (admin-only), filtering, search, Meta approval badges, and in-chat selector with previews + Ctrl/Cmd+T shortcut.
- **Mobile Responsiveness**
  - Breakpoints: mobile (<768px), tablet (768–1024px), desktop (>1024px).
  - Sidebar turns into drawer on mobile, chat window stretches vertically, stats stack, template dialog uses bottom sheet on small screens, headers adopt hamburger menu, and touch targets respect 44×44px guideline.

---

## Product & Access Control Changes

*From `SIGNUP_AND_ROLE_CHANGES.md`.*

- Added public `/signup` route + page that only creates *agent* accounts with password confirmation and validation.
- `LoginPage` links to signup; `App.js` routing ensures authenticated users skip signup.
- Removed "Create User" header button and the unused `SUPERVISOR` role everywhere (backend enums, role checks, frontend visibility logic).
- Signup endpoint now unauthenticated and forces agent role.
- Testing checklist covers signup flow, agent login, admin assignment features, and verifying no supervisor references remain.

---

## Engineering Notes & Fixes

### General Bug Fixes (`BUG_FIXES.md`)
- React hooks ordering bug in `ChatWindow` fixed by moving `useIsMobile` before conditional returns.
- Added missing `/api/chats/{chat_id}/mark_read` endpoint; frontend now resets unread counts through official API.
- Document also reiterates why these safeguards exist (role enforcement on mark_read, admin-only restrictions, etc.).

### Chat Sidebar Improvements (`CHAT_SIDEBAR_FIX.md`)
- Removed pre-fetch recursion in `selectChat` that triggered maximum update depth errors.
- Dropped misleading “New” pill; rely solely on unread badge.
- Confirmed chat sorting remained correct (most recent at top).

### Dashboard Optimization (`OPTIMIZATION_CHANGES.md`)
- Initial loading overlay now appears only before stats load; subsequent requests show inline spinners/banners instead of blank screens.
- Platform changes fetch chats only, not entire dashboard payload.
- Added contextual error banner with retry instead of blocking UI.
- Component-specific loaders introduced (chat list skeleton, template modal spinner, etc.).

### WebSocket Infinite Loop Fix (`WEBSOCKET_INFINITE_LOOP_FIX.md`)
- `handleWebSocketMessage` now uses functional state updates and refs for `activePlatform`/`loadChats`, eliminating dependency churn.
- Prevents reconnection storms and ensures chat list updates remain efficient even under heavy inbound volume.

### Regression Test Snapshot (`test_result.md`)
- Checklist confirms Instagram account CRUD, webhook verification + ingestion, cross-platform message sending, and platform filtering all pass automated smoke tests (status, endpoints, comments captured for auditing).

---

## Emergent-AI Prompt Brief

Captured from `EMERGENT_AI_PROMPT.md` for future automation/assistant work.

- Repository context, stack, and objectives for mobile responsiveness.
- Detailed responsive requirements (breakpoints, per-component expectations, gestures, template modal behaviors, touch-target guidance).
- Serves as the canonical brief when spinning up AI agents or new contributors to extend mobile UX work.

---

### Retired Standalone Docs

The following Markdown files have been merged into this guide and removed to reduce clutter:

`BUG_FIXES.md`, `CHAT_SIDEBAR_FIX.md`, `EMERGENT_AI_PROMPT.md`, `FACEBOOK_PERMISSION_REQUEST.md`, `FACEBOOK_PERMISSION_TEST_PLAN.md`, `FACEBOOK_WEBSOCKET_FIX.md`, `INSTAGRAM_INTEGRATION.md`, `INSTAGRAM_INTEGRATION_GUIDE.md`, `OPTIMIZATION_CHANGES.md`, `QUICKSTART.md`, `SIGNUP_AND_ROLE_CHANGES.md`, `TEMPLATE_AND_MOBILE_IMPLEMENTATION.md`, `test_result.md`, `WEBSOCKET_INFINITE_LOOP_FIX.md`.

Refer to this consolidated document (and the main `README.md`) for all future onboarding and troubleshooting needs.
