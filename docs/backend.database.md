# Backend Database

[← Back to Overview](../README.md) · [Backend](./backend.md) · [Migrations](./backend.migrations.md)

## Engines
- Primary: MySQL 8+ (set via `DB_TYPE=mysql` and `MYSQL_*` envs).
- Alternatives: Postgres (`DB_TYPE=postgres`, `POSTGRES_URL`) or SQLite (`DB_TYPE=sqlite`) for dev.

## Key models (high level)
- `User` (roles, permissions, `can_receive_new_chats`, positions)
- `Chat` (platform, assignment, status, last message timestamps)
- Platform-specific messages: `InstagramMessage`, `FacebookMessage`, plus raw log tables (`instagram_message_logs`)
- Social entities: `InstagramAccount`, `FacebookPage`, `FacebookUser`, `InstagramUser`
- Assignment cursors (`AssignmentCursor`) for round-robin fairness
- Templates, comments/reviews, and supporting tables (see `models.py`)

## Relationships & notes
- Chats link to platform users via `instagram_user_id` or `facebook_user_id`; assignment stored in `assigned_to`.
- Round-robin assignment skips inactive agents and those with `can_receive_new_chats=False`.
- Webhook payloads are persisted in log tables before normalization to chat messages.

## DB schema reference
- Detailed historical schema notes live in `docs/_legacy/db-schema.md` (original content retained).
- When models change, update migrations and refresh this summary.

## Seeding / data fixes
- Legacy data fixes (timezone, username, etc.) are captured in `_legacy` docs; check migrations before re-running fixes.

## Maintenance
- Add indexes alongside new columns when queries depend on them.
- Keep migrations idempotent; avoid long-running locks on MySQL (run during maintenance windows).
