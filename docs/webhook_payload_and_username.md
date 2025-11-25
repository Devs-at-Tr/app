# Facebook webhook payload storage & profile names

## What changed
- Added `facebook_webhook_events` table with a JSON `payload` column (plus `object`, `page_id`, `received_at`) to store each webhook's raw body for debugging and audit trails.
- Facebook webhook handler now persists every incoming payload before processing, so even non-message events are traceable without altering existing REST/WebSocket flows.
- Graph API profile lookup now requests `name,first_name,last_name,profile_pic` against a configurable `GRAPH_VERSION`, updating stored Facebook users with the resolved display name.

## Permissions & tokens
- Profile fetches require a Page or System User token with Meta scopes such as `pages_read_engagement`, `pages_show_list`, `pages_manage_metadata`, and `pages_user_profile` (or `public_profile` for Messenger) as outlined in Meta's lead retrieval docs.
- Configure `FACEBOOK_PAGE_ACCESS_TOKEN` on the page record (preferred) or `FACEBOOK_ACCESS_TOKEN_BACKUP`; the handler uses whichever is available to call the Graph API.

## Migration
- Create the new table by running migrations from `backend/`: `python -m migrations.runner`.
- If needed, drop the table via the optional `downgrade()` in `backend/migrations/20251121_180000_facebook_webhook_payload.py`.

## Files touched
- backend/models.py
- backend/migrations/20251121_180000_facebook_webhook_payload.py
- backend/server.py
- backend/facebook_api.py
- docs/webhook_payload_and_username.md
