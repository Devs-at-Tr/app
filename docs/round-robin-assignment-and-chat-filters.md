## Overview

This release introduces several Inbox workflow enhancements:

1. **User availability management**: Admins can toggle agents between Active/Inactive states. The User Directory now highlights inactive teammates in their own section.
2. **Round-robin assignment**: Newly created chats are automatically routed to the next available active agent, ensuring even load distribution.
3. **Permission-aware chat visibility**: Agents only receive their assigned chats by default, while admins or roles with `chat:view:*` permissions can still view all threads.
4. **Actionable chat filters**: The Inbox search bar now exposes toggles for “Unseen” and “Needs reply”, plus an agent filter (for privileged roles). Filters are enforced server-side.
5. **Responsive UI tweaks**: Stats cards now live inside a dedicated Analytics page accessible from the sidebar (“Analytics”). The Inbox view simply links to this page; Manage Instagram/Facebook shortcuts remain in the sidebar extras.

## Backend Changes

### Database

| Table | Column | Description |
| --- | --- | --- |
| `users` | `is_active BOOLEAN DEFAULT TRUE` | Flags whether an agent participates in round robin. |
| `chats` | `last_incoming_at`, `last_outgoing_at` (`DATETIME`) | Track the most recent customer/agent activity for filter logic. |
| `assignment_cursors` | `name`, `last_user_id`, `updated_at` | Stores the round-robin pointer (seeded with `default`). |

Migration: `backend/migrations/20251115_150000_round_robin_and_user_active.py` adds the above structures. Run via the existing migration runner.

### Models & Schemas

* `backend/models.py`
  * `User.is_active`
  * `Chat.last_incoming_at`, `Chat.last_outgoing_at`
  * New `AssignmentCursor` model
* `backend/schemas.py`
  * `UserResponse` exposes `is_active`
  * `UserActiveUpdate` request model
  * `ChatResponse` includes `last_incoming_at`, `last_outgoing_at`, and `pending_agent_reply`

### New / Updated Endpoints

| Method & Path | Notes |
| --- | --- |
| `PATCH /api/users/{user_id}/active` | Requires `position:manage`. Accepts `{ "is_active": true|false }`. Does not reassign existing chats. |
| `GET /api/users/agents?include_inactive=` | Returns assignable agents. Defaults to active-only. |
| `GET /api/chats` | New query params: `unseen=true|false`, `not_replied=true|false`, `assigned_to={id|unassigned}`. Agents without view-all permission are still limited to their chats. |

### Round-robin Assignment

* Helper functions live near `_is_assignable_agent` (`backend/server.py`):
  * `_get_assignable_agents(db)` returns role=agent, active=true, and position slug = agent.
  * `_get_assignment_cursor(db)` fetches/locks the cursor row.
  * `_assign_chat_round_robin(db, chat)` advances the cursor and assigns the next agent, or leaves the chat unassigned if none are available.
* Hook points:
  * Instagram and Facebook webhook handlers immediately call `_assign_chat_round_robin` after inserting a brand-new chat record.
  * Dashboards count active agents via `len(_get_assignable_agents(db))`.

### Filters & Metadata

* Inbound messages set `chat.last_incoming_at`; outbound actions (`/messages/send`, `/messages/send-template`, `/messages/send` (legacy), and manual replies) set `chat.last_outgoing_at`.
* `_chat_requires_agent_reply(chat)` derives `pending_agent_reply` (exposed via `ChatResponse`) and powers the `not_replied` filter.
* The `/api/chats` handler applies server-side filters before returning results and annotates ORM objects with `pending_agent_reply`.

### Permissions

* `_user_can_view_all_chats` remains the gatekeeper. Agents call `/api/chats` with `assigned_to_me=false` but still only see their assignments because the handler enforces the restriction.
* Admin/roles with `chat:view:team` or `chat:view:all` may add `assigned_to` query params to slice by user or “unassigned.”

## Frontend Changes (React)

### Chat Filters & Loaders

* Inbox maintains `chatFilters` state (`unseen`, `notReplied`, `assignedTo`).
* `ChatProvider.loadChats(platform, filters)` forwards filter params to the API; websocket-triggered reloads reuse the latest filter set.
* UI controls:
  * Toggle buttons for “Unseen” (eye icon) and “Needs reply”.
  * Agent dropdown (only for roles with `chat:view:*`) offering “All”, “Unassigned”, and individual active agents.

### Manage Integrations & Stats Placement

* `ChatSidebar` now renders compact stats cards (total, unassigned, assigned, active agents) when `statsSummary` is provided—used for mobile layouts where the main cards are hidden.
* Integration buttons moved into `ChatSidebar`, so they appear both on desktop (left column) and within the mobile drawer.
* `StatsCards` component accepts an optional `className`. The Inbox page no longer renders these cards directly; instead, the new `StatsPage` (`frontend/src/pages/StatsPage.jsx`) hosts them behind the “Analytics” sidebar link. Sidebar extras now only host integration shortcuts.

### User Directory

* `UserRosterCard` displays active members first and groups inactive users below with a dashed border.
* Each row exposes a status `Switch` (when `canToggleActive` is true) and an Activate button for dormant users.
* User Directory page adds `handleToggleActive`, calling `PATCH /users/{id}/active` followed by a roster refresh.

## Usage Notes

* **Marking users active/inactive**: Navigate to User Directory and flip the status switch. Inactive agents remain listed but no longer receive new chats via round robin. Existing assignments stay intact.
* **Round robin edge cases**:
  * If no eligible agents exist, chats remain unassigned until an admin assigns them manually or reactivates an agent.
  * Re-activating an agent automatically adds them back into the assignment rotation; no extra action needed.
* **Filters**:
  * _Unseen_ → `unseen=true` → chats with `unread_count > 0`.
  * _Needs reply_ → `not_replied=true` → last incoming timestamp is newer than last outgoing.
  * _Assigned to_ dropdown → `assigned_to={user_id|unassigned}`.
* **Analytics access**: Conversation metrics now live behind the “Analytics” sidebar entry (`/stats`). The Inbox header provides a CTA linking to that page so the chat list stays uncluttered.
## Files Touched

Backend:
- `backend/models.py`, `backend/server.py`, `backend/schemas.py`
- `backend/migrations/20251115_150000_round_robin_and_user_active.py`

Frontend:
- `frontend/src/context/ChatContext.js`
- `frontend/src/pages/InboxPage.js`
- `frontend/src/components/ChatSidebar.js`
- `frontend/src/components/StatsCards.js`
- `frontend/src/components/UserRosterCard.jsx`
- `frontend/src/pages/UserDirectoryPage.jsx`

Docs:
- `docs/backend-architecture-and-concepts.md` (reference material)
- `docs/round-robin-assignment-and-chat-filters.md` (this file)
- `frontend/src/pages/StatsPage.jsx` (new Analytics view referenced from the sidebar)

These updates keep all existing messaging flows intact while layering in richer workload management and responsive UI behaviors. Let the Inbox load once after deployment so the new cursor record is created automatically.

