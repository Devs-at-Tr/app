# Positions & Permissions Guide

This document explains how role‑based access control works now that the messaging platform supports custom positions (roles) and fine‑grained permissions. Use it whenever you need to seed/migrate data, grant access to teammates, or extend the UI/API.

---

## 1. Core Concepts

| Term          | Description                                                                                               |
|---------------|-----------------------------------------------------------------------------------------------------------|
| **Position**  | A reusable role definition (e.g., Super Admin, Supervisor, Agent Messaging). Stored in the `positions` table with a unique `slug`, description, and `permissions_json` payload. |
| **Permission**| A capability flag (`chat:view:assigned`, `position:manage`, etc.) that toggles API endpoints and UI features. |
| **User Role** | Legacy `User.role` enum (`admin` / `agent`). Still present for backward compatibility but no longer the source of truth for permissions. |

Every user can be linked to a position through `users.position_id`. Permissions are resolved from the assigned position, with an automatic “god mode” fallback for legacy `admin` records to avoid regressions.

---

## 2. Seeded Positions (Day‑1)

| Position            | Slug            | Notes                                                                                                   |
|---------------------|-----------------|---------------------------------------------------------------------------------------------------------|
| **Super Admin**     | `super-admin`   | Assigned automatically to the first admin. Full access to everything, including position management.    |
| **Admin**           | `admin`         | Same permissions as Super Admin today (kept for future narrowing). Additional admins default here.      |
| **Supervisor**      | `supervisor`    | Can view/assign any chat, run templates, moderate comments, and view analytics (no integration access). |
| **Agent (Messaging)** | `agent-messaging` | Restricted to assigned chats, basic messaging, and template usage only.                                   |

> During bootstrap (`backend/server.py`), the system seeds these rows and makes sure existing admins are slotted into “Super Admin” / “Admin” appropriately (`ensure_admin_position_assignments` in `backend/permissions.py:245`).

---

## 3. Permission Catalogue

Each permission code uses the pattern `domain:action:scope`. Definitions live in `backend/permissions.py:28` and are exposed via `GET /api/permissions/codes`.

| Code                     | Intended Use                                                                  |
|--------------------------|-------------------------------------------------------------------------------|
| `chat:view:assigned`     | See only chats assigned to the current agent.                                |
| `chat:view:team`         | See chats assigned to teammates/queues.                                      |
| `chat:view:all`          | See every conversation across FB/IG.                                         |
| `chat:message`           | Send manual messages within the 24h window.                                  |
| `chat:assign`            | Assign/reassign chats (unassigned pool, other agents).                       |
| `template:use`           | Send Meta templates that are already approved.                               |
| `template:manage`        | Create/update/delete templates and submit them to Meta.                      |
| `comment:moderate`       | Hide/reply to Instagram/Facebook comments.                                   |
| `integration:manage`     | Connect/disconnect IG accounts or Facebook pages.                            |
| `position:manage`        | CRUD for positions and permission sets.                                      |
| `position:assign`        | Attach/detach positions from users.                                          |
| `user:invite`            | Create new accounts via admin flows.                                         |
| `stats:view`             | Access analytics/stats endpoints and widgets.                                |

Add new permissions by extending the `PermissionCode` enum and `PERMISSION_METADATA` map, then reference them inside API dependencies (`require_permissions`) and UI gates.

---

## 4. API Overview

| Endpoint                              | Method | Permission Requirement             | Purpose                                         |
|---------------------------------------|--------|------------------------------------|-------------------------------------------------|
| `/api/positions`                      | GET    | `position:manage`                  | List all positions (hides Super Admin unless you are one). |
| `/api/positions`                      | POST   | `position:manage`                  | Create a new position (Super Admin only for the Super Admin slot). |
| `/api/positions/{id}`                 | PUT    | `position:manage`                  | Update name/description/permissions (Super Admin-only for its own slot). |
| `/api/positions/{id}`                 | DELETE | `position:manage`                  | Delete custom positions (not allowed for system). |
| `/api/users/{user_id}/position`       | POST   | `position:assign`                  | Assign or clear a user’s position (Super Admin can elevate another Super Admin). |
| `/api/users/roster`                   | GET    | any of (`position:assign`, `position:manage`, `chat:assign`) | List every account with its position and assigned chat count. |
| `/api/permissions/codes`              | GET    | `position:manage`                  | Fetch human‑friendly permission metadata for the UI. |

> Existing endpoints (e.g., `/api/chats/{id}/assign`) now use `require_permissions` wrappers instead of raw role checks, so granting `chat:assign` to a position immediately unlocks the back office tools.

---

## 5. Frontend UX

* The dashboard receives `user.permissions` from `/auth/me` / `/auth/login`. Helper utilities in `frontend/src/utils/permissionUtils.js` power `<PermissionGate>`-style conditionals.
* A “Manage Positions” button now appears next to the Instagram/Facebook controls whenever the signed-in user has `position:manage`. This launches `PositionManager` (`frontend/src/components/PositionManager.jsx`), a modal that:
  - lists all positions with metadata badges,
  - lets admins create custom roles (name, slug, description),
  - toggles permissions via checkboxes fed by `/api/permissions/codes`,
  - allows updates/deletes for non-system positions.
  - hides the “Super Admin” row unless you are a Super Admin; only Super Admins can assign or edit that slot.
* Integrations, templates, and other tabs reference the same helper so they hide automatically for agents without the right scopes.
* A **User Directory** card now appears for supervisors/admins (`position:assign`, `position:manage`, or `chat:assign`). It calls `/api/users/roster` to display each account, its current position label, and live assigned-chat counts so you can balance workloads quickly (`frontend/src/components/UserRosterCard.jsx`).

---

## 6. Operational Steps

1. **Run migrations**  
   Execute the new migration (`20251112_120000_positions_and_permissions.py`) using the existing runner so the `positions` table and seed data exist before deploying the backend.

2. **Verify bootstrap**  
   Restart the API; logs should show the bootstrap seeding and admin assignment (warnings appear if it fails). Inspect `positions` and `users` tables to confirm `position_id` values.

3. **Review roles via UI**  
   Sign in as your admin account → click “Manage Positions”. Confirm Super Admin/Admin/Supervisor/Agent Messaging entries appear with the expected permission chips.

4. **Assign positions to users**  
   Until a dedicated UI exists, hit `POST /api/users/{user_id}/position` with the `position_id` from `/api/positions`. Remember agents lose access to previous features instantly once permissions change.

5. **Extend as needed**  
   - Add new permission codes inside `PermissionCode`.  
   - Update `DEFAULT_POSITION_DEFINITIONS` if you want them seeded automatically in new environments.  
   - Wrap any new FastAPI endpoints with `require_permissions(...)` to keep enforcement centralized.

---

## 7. Troubleshooting

| Symptom                                | Likely Cause / Fix                                                                                     |
|----------------------------------------|---------------------------------------------------------------------------------------------------------|
| Positions list empty in UI             | `/api/positions` failing — ensure the signed-in user has `position:manage` and the migration ran.      |
| Manage button missing for admin        | Admin user might lack `position_id` due to bootstrap failure—call `ensure_admin_position_assignments` manually or update via API. |
| Agents see chats they shouldn’t        | Check their assigned position’s permissions and confirm `/api/chats` filters include visibility scopes (`chat:view:assigned` vs `chat:view:all`). |
| Cannot delete a position               | Either marked `is_system` or still assigned to users. Reassign users first, then retry.                |

---

Keep this document updated when you add new permissions, change defaults, or ship more UI for assigning agents/teams. It’s the source of truth for onboarding and audits. 
