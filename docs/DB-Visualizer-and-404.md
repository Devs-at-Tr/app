## `/dbshow` developer page

- **Purpose**: Give Super Admins and developers a live overview of the `pf_messenger` MySQL schema without exposing tooling to everyday agents.
- **Access**: Requires a valid session plus Super Admin privileges (position slug `super-admin`). Visiting `/dbshow` as any other role renders a 403-style screen.
- **Layout**: Standalone page that intentionally skips the dashboard sidebar. It provides a simple header, refresh controls, and vertically stacked sections.

### Data surfaced

1. **Database summary** – Name, table count, approximate row count, and storage totals (data/index sizes derived from `information_schema.TABLES`). Displays the last recorded schema update timestamp.
2. **Tables list** – Each table card shows rows, size, created/updated timestamps, and expands to reveal all columns (type, nullability, default, key, extras) pulled from `information_schema.COLUMNS`.
3. **Relationships** – Foreign keys extracted from `information_schema.KEY_COLUMN_USAGE`, rendered as readable edges (e.g., `facebook_messages.chat_id → chats.id`).
4. **Schema changes timeline** – Highlights the latest snapshot summary (new tables, column edits) and lists the most recent snapshots with their detailed changes.
5. **Storage breakdown** – Top five tables by combined data/index footprint with mini bar indicators and row counts.

The backend endpoint `/api/dev/db-overview` powers the page, returning all metadata in a single call.

### Schema tracking internals

- New tables: `db_schema_snapshots` & `db_schema_changes`.
  - Snapshots store serialized schema JSON (table → columns + FK definitions) plus timestamps.
  - Change rows capture `change_type` (`TABLE_ADDED`, `TABLE_REMOVED`, `COLUMN_ADDED`, `COLUMN_REMOVED`, `COLUMN_CHANGED`), table/column names, and before/after details.
- Snapshot workflow:
  1. On every `/dbshow` load, the backend fetches the current schema via `information_schema`.
  2. If no baseline exists, it saves a snapshot and stops.
  3. Otherwise it diffs the previous snapshot vs. current metadata, records any detected changes, and saves a new snapshot.
  4. Only actual differences (new/dropped/altered tables or columns) create change rows, so repeated visits without DDL tweaks don’t spam entries.

## 404 redirect behaviour

- Added a React Router catch-all route so any unknown front-end path immediately `Navigate`s back to `/`.
- API routes (`/api/*`), static assets, and Next/CRA internals (e.g., `/_next`, `/static`) remain untouched; they continue to return their natural HTTP status codes.
- Examples:
  - `https://messenger.tickleright.in/pangenotcreated` → automatically redirects to `/`.
  - `https://messenger.tickleright.in/api/doesnt-exist` still responds with an API JSON 404.

## Changelog

**Created**
- `backend/migrations/20251114_210000_db_schema_tracking.py`
- `frontend/src/pages/DatabaseVisualizerPage.jsx`
- `docs/DB-Visualizer-and-404.md`

**Significantly modified**
- `backend/models.py`, `backend/server.py`, `backend/schemas.py` – schema tracking models, metadata endpoint, helper utilities.
- `frontend/src/App.js`, `frontend/src/utils/permissionUtils.js` – new route, super-admin helper, global catch-all redirect.

This documentation should help future developers understand how to access `/dbshow`, how the automatic schema snapshots operate, and why unknown URLs now land on the main dashboard.
