# Database Schema (MySQL via SQLAlchemy models)

## positions
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| name | varchar(255) | NO | | |
| slug | varchar(255) | NO | | UNIQUE, INDEX |
| description | text | YES | | |
| permissions_json | text | NO | "[]" | stores JSON list |
| is_system | bool | NO | False | |
| created_at | datetime tz | NO | utc_now | |
| updated_at | datetime tz | NO | utc_now, on update |

**Relations:** 1↔N users (position_id).

## users
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| name | varchar(255) | NO | | |
| email | varchar(255) | YES | | UNIQUE, INDEX |
| contact_number | varchar(50) | YES | | UNIQUE, INDEX |
| country | varchar(100) | YES | | |
| emp_id | varchar(100) | YES | | UNIQUE, INDEX |
| password_hash | varchar(255) | NO | | |
| role | enum(admin, agent) | NO | agent | |
| position_id | varchar(36) | YES | | FK → positions.id (INDEX) |
| is_active | bool | NO | True | server_default=1 |
| can_receive_new_chats | bool | NO | True | server_default=1 |
| created_at | datetime tz | NO | utc_now | |
| updated_at | datetime tz | NO | utc_now, on update |

**Relations:** 1↔N instagram_accounts; 1↔N assigned chats (chats.assigned_to); 1↔N user_status_logs; 1↔N message_templates; 1↔N password_reset_tokens; 1↔N facebook_pages.

## password_reset_tokens
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| user_id | varchar(36) | NO | | FK → users.id (INDEX) |
| token_hash | varchar(128) | NO | | UNIQUE |
| expires_at | datetime tz | NO | | |
| used_at | datetime tz | YES | | |
| created_at | datetime tz | NO | utc_now | |
| updated_at | datetime tz | NO | utc_now, on update |

## db_schema_snapshots
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | int | NO | auto inc | PK |
| created_at | datetime tz | NO | utc_now | |
| snapshot_json | text | NO | | |
| comment | varchar(255) | YES | | |

**Relations:** 1↔N db_schema_changes.

## db_schema_changes
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | int | NO | auto inc | PK |
| snapshot_id | int | NO | | FK → db_schema_snapshots.id (INDEX) |
| change_type | varchar(50) | NO | | |
| table_name | varchar(255) | NO | | |
| column_name | varchar(255) | YES | | |
| details_json | text | YES | | |
| created_at | datetime tz | NO | utc_now | |

## instagram_accounts
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| user_id | varchar(36) | NO | | FK → users.id |
| page_id | varchar(255) | NO | | |
| access_token | varchar(500) | NO | | |
| username | varchar(255) | YES | | |
| connected_at | datetime tz | NO | utc_now | |

## chats
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| instagram_user_id | varchar(255) | YES | | FK → instagram_users.igsid (INDEX) |
| facebook_user_id | varchar(255) | YES | | FK → facebook_users.id (INDEX) |
| username | varchar(255) | NO | | |
| profile_pic_url | text | YES | | |
| last_message | text | YES | | |
| status | enum(assigned, unassigned) | NO | unassigned | |
| assigned_to | varchar(36) | YES | | FK → users.id |
| unread_count | int | YES | 0 | |
| platform | enum(INSTAGRAM, FACEBOOK) | NO | INSTAGRAM | INDEX |
| facebook_page_id | varchar(255) | YES | | |
| created_at | datetime tz | NO | utc_now | |
| updated_at | datetime tz | NO | utc_now, on update |
| last_incoming_at | datetime tz | YES | | |
| last_outgoing_at | datetime tz | YES | | |

**Relations:** 1↔N instagram_messages; 1↔N facebook_messages; N↔1 instagram_users/facebook_users; N↔1 assigned user.

## assignment_cursors
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| name | varchar(64) | NO | | PK |
| last_user_id | varchar(36) | YES | | |
| updated_at | datetime tz | NO | utc_now, on update |

## facebook_users
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(255) | NO | | PK |
| first_seen_at | datetime tz | NO | utc_now | |
| last_seen_at | datetime tz | NO | utc_now, on update |
| last_message | text | YES | | |
| username | varchar(255) | YES | | |
| name | varchar(255) | YES | | |
| profile_pic_url | text | YES | | |

**Relations:** 1↔N chats; 1↔N facebook_messages.

## instagram_users
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| igsid | varchar(255) | NO | | PK |
| first_seen_at | datetime tz | NO | utc_now | |
| last_seen_at | datetime tz | NO | utc_now, on update |
| last_message | text | YES | | |
| username | varchar(255) | YES | | |
| name | varchar(255) | YES | | |

**Relations:** 1↔N chats; 1↔N instagram_messages; 1↔N instagram_message_logs.

## instagram_messages
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| chat_id | varchar(36) | NO | | FK → chats.id |
| sender | enum(MessageSender) | NO | | |
| content | text | NO | | |
| message_type | enum(text, image) | NO | text | |
| timestamp | datetime tz | NO | utc_now | |
| attachments_json | text | YES | | |
| metadata_json | text | YES | | |
| is_gif | bool | NO | False | |
| is_ticklegram | bool | NO | False | |
| platform | enum(INSTAGRAM) | NO | | |
| instagram_user_id | varchar(255) | NO | | FK → instagram_users.igsid (INDEX) |

## facebook_messages
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| chat_id | varchar(36) | NO | | FK → chats.id |
| sender | enum(MessageSender) | NO | | |
| content | text | NO | | |
| message_type | enum(text, image) | NO | text | |
| timestamp | datetime tz | NO | utc_now | |
| attachments_json | text | YES | | |
| metadata_json | text | YES | | includes raw webhook |
| is_gif | bool | NO | False | |
| is_ticklegram | bool | NO | False | |
| platform | enum(FACEBOOK) | NO | | |
| facebook_user_id | varchar(255) | NO | | FK → facebook_users.id (INDEX) |

## facebook_webhook_events
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| object | varchar(64) | YES | | |
| page_id | varchar(255) | YES | | INDEX |
| payload | JSON | NO | | full raw webhook |
| received_at | datetime tz | NO | utc_now | |

## facebook_pages
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| user_id | varchar(36) | NO | | FK → users.id |
| page_id | varchar(255) | NO | | UNIQUE, INDEX |
| page_name | varchar(255) | YES | | |
| access_token | varchar(500) | NO | | |
| is_active | bool | NO | True | |
| connected_at | datetime tz | NO | utc_now | |
| updated_at | datetime tz | NO | utc_now, on update |

**Relations:** 1↔N facebook_page_status_logs.

## facebook_page_status_logs
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| page_id | varchar(255) | NO | | FK → facebook_pages.page_id (INDEX) |
| changed_by | varchar(255) | NO | | |
| changed_to | bool | NO | | |
| changed_at | datetime tz | NO | utc_now | |
| note | text | YES | | |

## user_status_logs
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| user_id | varchar(36) | NO | | FK → users.id (INDEX) |
| changed_by | varchar(255) | NO | | |
| changed_to | bool | NO | | |
| changed_at | datetime tz | NO | utc_now | |
| note | text | YES | | |

## message_templates
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| name | varchar(255) | NO | | |
| content | text | NO | | |
| category | varchar(50) | NO | | |
| platform | enum(INSTAGRAM, FACEBOOK) | NO | | |
| meta_template_id | varchar(255) | YES | | |
| meta_submission_id | varchar(255) | YES | | |
| meta_submission_status | varchar(50) | YES | | |
| is_meta_approved | bool | NO | False | |
| created_by | varchar(36) | NO | | FK → users.id |
| created_at | datetime tz | NO | utc_now | |
| updated_at | datetime tz | NO | utc_now, on update |

## instagram_message_logs
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| igsid | varchar(255) | NO | | FK → instagram_users.igsid (INDEX) |
| message_id | varchar(512) | YES | | UNIQUE, INDEX |
| direction | enum(inbound, outbound) | NO | | |
| text | text | YES | | |
| attachments_json | text | YES | | |
| ts | bigint | NO | | INDEX |
| created_at | datetime tz | NO | utc_now | |
| raw_payload_json | text | YES | | full raw webhook payload |
| metadata_json | text | YES | | |
| is_gif | bool | NO | False | |
| is_ticklegram | bool | NO | False | |

## instagram_comments
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(255) | NO | | PK |
| media_id | varchar(255) | NO | | INDEX |
| author_id | varchar(255) | YES | | INDEX |
| text | text | YES | | |
| hidden | bool | NO | False | |
| action | enum(created, updated, deleted) | NO | created | |
| mentioned_user_id | varchar(255) | YES | | |
| attachments_json | text | YES | | |
| ts | bigint | NO | | INDEX |
| created_at | datetime tz | NO | utc_now | |
| updated_at | datetime tz | NO | utc_now, on update |

## instagram_marketing_events
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| event_name | varchar(120) | NO | | |
| value | float | YES | | |
| currency | varchar(10) | YES | | |
| pixel_id | varchar(255) | YES | | |
| external_event_id | varchar(255) | YES | | UNIQUE |
| status | varchar(50) | YES | | |
| payload_json | text | YES | | |
| response_json | text | YES | | |
| ts | bigint | NO | | INDEX |
| created_at | datetime tz | NO | utc_now | |

## instagram_insights
| Column | Type | Null | Default | Notes |
| --- | --- | --- | --- | --- |
| id | varchar(36) | NO | uuid | PK |
| scope | enum(account, media, story, profile) | NO | | |
| entity_id | varchar(255) | NO | | INDEX |
| period | varchar(50) | YES | | |
| metrics_json | text | NO | | |
| fetched_at | datetime tz | NO | utc_now | INDEX |

---

# Relationships Summary
- positions 1↔N users.
- users 1↔N instagram_accounts; 1↔N assigned chats; 1↔N user_status_logs; 1↔N password_reset_tokens; 1↔N message_templates; 1↔N facebook_pages.
- chats N↔1 instagram_users / facebook_users; chats 1↔N instagram_messages / facebook_messages; chats N↔1 assigned user.
- instagram_users 1↔N instagram_messages / instagram_message_logs / chats.
- facebook_users 1↔N facebook_messages / chats.
- facebook_pages 1↔N facebook_page_status_logs.
- db_schema_snapshots 1↔N db_schema_changes.

---

# Constraints & Indexes (key points)
- Unique: positions.slug; users.email/contact_number/emp_id; facebook_pages.page_id; instagram_message_logs.message_id; instagram_marketing_events.external_event_id.
- Indexed FKs: users.position_id; password_reset_tokens.user_id; instagram_accounts.user_id; chats.instagram_user_id/facebook_user_id/assigned_to/platform; facebook_messages.facebook_user_id; instagram_messages.instagram_user_id; facebook_page_status_logs.page_id; user_status_logs.user_id; instagram_message_logs.igsid/message_id/ts; instagram_comments.media_id/author_id/ts; instagram_marketing_events.ts; instagram_insights.entity_id/fetched_at; facebook_webhook_events.page_id.

Raw payload storage:
- Instagram inbound logs: `instagram_message_logs.raw_payload_json` stores full `messaging_event` JSON.
- Facebook inbound messages: `facebook_messages.metadata_json` includes `raw_webhook` contents.
