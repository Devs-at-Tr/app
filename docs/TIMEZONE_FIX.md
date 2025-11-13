# Timestamp & Timezone Migration

## Why this change?

- Messages, chats, and related audit tables were storing timestamps directly in Asia/Kolkata (`now_ist`).  
- FastAPI responses already convert values to IST before returning, and the React client converts again, which pushed every new message **+5h 30m** into the future (e.g., “Nov 13 00:48 AM” even though the reply was sent Nov 12 7:18 PM).  
- Outbound Graph echoes reinserted the same message with the shifted time, so the timeline appeared out of order.

## What changed?

1. **UTC storage everywhere**  
   - Added `utc_now()` in `backend/utils/timezone.py`.  
   - Models (`backend/models.py`) now default `created_at`/`updated_at` to `utc_now`.  
   - All runtime code (`backend/server.py`, `instagram_api.py`, `facebook_api.py`, `auth.py`) uses UTC when creating chats/messages/logs.

2. **Historical data correction**  
   - New migration `backend/migrations/20251112_180000_fix_utc_timestamps.py` subtracts 5 h 30 m from the affected columns so existing rows align with UTC.

3. **Client rendering**  
   - The API still serializes responses in IST (via `convert_to_ist`), and the frontend formats them with `formatInTimeZone`, so users continue seeing local time — but now the source values are correct.

## How to apply the migration

1. Ensure `DATABASE_URL` is set in `.env`.
2. Run the standard migration runner (from the repo root):
   ```bash
   python backend/migrations/runner.py
   ```
   This will execute `20251112_180000_fix_utc_timestamps.py` and log each table/column shifted.
3. Restart the API. All new timestamps will already be emitted in UTC and display correctly on the dashboard.

## Notes

- The migration targets the tables/columns that influence chat timelines (`chats`, `instagram_messages`, `facebook_messages`, `instagram_message_logs`, plus related metadata tables).  
- If you add new tables with timestamp defaults, reuse `utc_now()` and keep the migration list in sync if legacy data needs adjustment.  
- No user data is dropped; values are simply shifted back by 330 minutes.
