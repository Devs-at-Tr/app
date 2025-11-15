## Meta Integrations Overview

TickleGram Inbox Suite integrates deeply with Meta's Graph API for Instagram Direct, Facebook Messenger, page comments, insights, and Conversions API events. The backend (FastAPI) hosts webhook endpoints and proxies outbound calls via two reusable clients (`backend/instagram_api.py`, `backend/facebook_api.py`) plus a template helper (`backend/meta_template_api.py`). This document consolidates every Meta call and webhook currently in use so we can extend functionality without guessing.

At a high level:

- **Outbound**: When an agent sends a DM, replies to a comment, requests insights, or submits a template, the server issues HTTPS requests to `https://graph.facebook.com/{version}/...` using page access tokens stored in the DB or fetched via the Meta template API.
- **Inbound**: Meta calls our webhooks (`/webhooks/instagram`, `/webhook`, `/webhooks/facebook`) with messaging/comments payloads. We verify tokens/signatures, map the payload into SQL tables (`chats`, `instagram_message_logs`, `facebook_messages`, `instagram_comments`, etc.), and broadcast UI updates.

The sections below describe each call, its purpose, parameters, and where it lives in the codebase.

---

## 2. Outbound API Calls

### 2.1 Instagram Direct Messaging

| Purpose | Location | HTTP details | Auth & request | Response handling | Trigger |
| --- | --- | --- | --- | --- | --- |
| **Send DM (text/attachments)** | `backend/instagram_api.py:send_dm` (wrappers `send_text_message`, `send_attachment`) invoked from `/messages/send`, `/chats/{chat_id}/message`, broadcast helpers | `POST https://graph.facebook.com/{graph_version}/{page_id}/messages` (`graph_version` from `INSTAGRAM_GRAPH_VERSION`, default `v17.0`). | Query/body includes `recipient.id`, `messaging_type` (`RESPONSE`), `message.text` or `message.attachment` with `{type,payload}`. `page_access_token` comes from `resolve_instagram_access_token` (reads `instagram_accounts` table or `.env`). | Response JSON keys `recipient_id` and `message_id` are stored on `InstagramMessage` and echoed to clients; errors log `error{code,message}`. | Fired when an agent sends a standard DM or attaches media. |
| **Send tagged / template DM** | `backend/instagram_api.py:send_template_message` called from `/messages/send-template` and escalation helpers | `POST https://graph.facebook.com/{graph_version}/me/messages` | Body includes `messaging_type: "MESSAGE_TAG"`, `tag` (default `ACCOUNT_UPDATE`), `message_creative_id` (if a template) or fallback `text`. | Logs Meta error payloads, forwards success/failure to the caller; `message_id` persisted similar to normal DMs. | Used to reply outside the 24h window via approved templates. |
| **Download IG attachment** | `backend/server.py:_download_instagram_attachment` | `GET {meta_attachment_url}` (URL extracted from webhook). | Raw download using `requests`, timeout `ATTACHMENT_DOWNLOAD_TIMEOUT`. File stored under `backend/attachments/instagram/<igsid>/<message_id>/...`. | On success returns relative file path saved to the message `attachments_json`. | Executed while processing webhook media messages. |

### 2.2 Instagram Profile, Comments & Engagement

- **Profile lookup** – `backend/instagram_api.py:get_user_profile` (`GET https://graph.facebook.com/{graph_version}/{user_id}?fields=username,profile_pic,name,id&access_token=<page_token>`). Called whenever a webhook arrives or when enriching chats. Response values hydrate `instagram_users.username/name` and chat display names. Errors log payload and default to generic “IG User ####”.
- **Media comments fetch** – `get_media_comments` (`GET /{media_id}/comments?fields=id,text,user,hidden,like_count,timestamp,...`). Called from `/instagram/comments` to populate the comment moderation UI. Results are normalized into our `InstagramComment` schema but not persisted unless user saves changes.
- **Reply/update/delete comment** – `reply_to_comment`, `create_comment`, `set_comment_visibility`, `delete_comment` (various `POST`/`PATCH` calls on `/ {comment_id}/replies`, `/comments`, `/hidden`, `/delete`). Each uses the page token and returns Meta’s comment `id`/status. Invoked by routes `/instagram/comments/reply`, `/instagram/comments/create`, `/instagram/comments/visibility`, `/instagram/comments/delete`.
- **Mentions & post mentions** – `get_mentions` (`GET /{user_id}/mentioned_media?...`) powers `/instagram/mentions`. Results are streamed to the UI but not stored.
- **Story/post comment helpers** – `handle_story_mention`, `handle_post_comment`, `get_comment_details` provide additional metadata for moderation.

### 2.3 Instagram Insights & Conversions API

- **Account/media/story insights** – `get_account_insights`, `get_media_insights`, `get_story_insights` (`GET /{id}/insights`). Query params: `metric`, `period`, `access_token`. Responses are inserted into `instagram_insights` via `persist_instagram_insight` and returned from `/instagram/insights/*`.
- **Marketing/Conversions events** – `send_marketing_event` (`POST https://graph.facebook.com/{graph_version}/{pixel_id}/events?access_token=<token>`). Payload matches Conversions API schema (`data: [{event_name,event_time,user_data,custom_data,...}]`). Retries on HTTP 429/5xx with exponential backoff. Called from `/marketing/events`. Responses (success or error JSON) are stored in `instagram_marketing_events`.

### 2.4 Facebook Messenger & Comments

| Feature | Function | Endpoint & payload | Auth | Usage |
| --- | --- | --- | --- | --- |
| **Send Messenger text** | `facebook_client.send_text_message` | `POST https://graph.facebook.com/v17.0/me/messages` with `{recipient:{id},messaging_type:"RESPONSE",message:{text}}`. | Page access token pulled from `facebook_pages.access_token`. | When replying to Facebook chats in `/messages/send`. |
| **Send Messenger attachment** | `facebook_client.send_attachment` | Same endpoint; `message.attachment={type,payload:{url,is_reusable}}`. | Page token. | Used when agent attaches files to Messenger chats. |
| **Send tagged/template message** | `facebook_client.send_template_message` | `POST /me/messages` with `messaging_type:"MESSAGE_TAG"`, optional `message_creative_id` or fallback `text`, `tag` (default `ACCOUNT_UPDATE`). | Page token. | Used to reach users outside 24h policy. |
| **Reply to Facebook comment** | `facebook_client.reply_to_comment` | `POST https://graph.facebook.com/v17.0/{comment_id}/comments` with `{message}`. | Page token. | Comments module action `/facebook/comments/reply`. |
| **Fetch feed & comments** | `get_page_feed_with_comments`, `get_page_posts`, `get_post_comments`, `get_comment_replies` (various `GET /{page_id}/feed`, `/posts`, `/comments`). Parameters include `fields` expansions (message text, attachments, reactions). | Page token. | Backs `/facebook/comments` UI for moderation. |
| **Messenger webhook parsing** | `process_webhook_message` returns normalized payload for inbound events, but outbound docs note it doesn’t call Meta itself. |
| **Messenger user profile** | `get_user_profile` (`GET /{user_id}?fields=name,profile_pic`) used when a webhook arrives without cached names. |

### 2.5 Meta Template API

- **Submit message template** – `backend/meta_template_api.py:submit_template`. Endpoint `POST https://graph.facebook.com/v24.0/{page_id}/message_templates` with the normalized template payload (`{name,category,language,en_US,components:[{type:"BODY",text,...}]}`). Access token is fetched via `_get_access_token` (`GET /{page_id}?fields=access_token&access_token={app_id}|{app_secret}`). Response `id/status/name` is saved in our templates table.
- **Check template status** – `check_template_status` hits `GET https://graph.facebook.com/v24.0/{template_id}` with the page token. Used by the templates dashboard to show approval state.

### 2.6 Other Graph calls

- **Instagram attachment download** – while not hitting Graph directly, `_download_instagram_attachment` fetches URLs provided by Meta for media attachments.
- **Insights snapshots** – See 2.3 for analytics.

---

## 3. Webhooks

### 3.1 Instagram (DMs + Comments)

- **Verification**:  
  - `GET /webhooks/instagram` and `GET /webhook` accept `hub.mode`, `hub.challenge`, `hub.verify_token`. Both call `_verify_instagram_webhook_subscription`, which compares the token to `INSTAGRAM_VERIFY_TOKEN`/`INSTAGRAM_WEBHOOK_VERIFY_TOKEN` env values and returns the numeric challenge or raises 403.

- **Endpoints**:  
  - `POST /webhooks/instagram` and `POST /webhook` both delegate to `_handle_instagram_webhook`.

- **Security**: For Instagram DM webhooks, Meta does not sign payloads; we rely on the verify token during subscription. The handler wraps errors and always returns a JSON `{status: "received"}` (or `{status:"error"}`) so Meta doesn’t retry infinitely.

- **Message payload** (`object: "instagram"`):
  ```json
  {
    "object": "instagram",
    "entry": [
      {
        "id": "<page_id>",
        "messaging": [
          {
            "sender": { "id": "<user_igsid>" },
            "recipient": { "id": "<page_id>" },
            "timestamp": 1731526800000,
            "message": {
              "mid": "<graph_message_id>",
              "text": "Hi",
              "attachments": [...]
            }
          }
        ],
        "changes": [
          {
            "field": "comments",
            "value": {
              "id": "<comment_id>",
              "media_id": "<media_id>",
              "verb": "add",
              "text": "Nice post!",
              "from": { "id": "<author_id>" }
            }
          }
        ]
      }
    ]
  }
  ```

- **Processing**:
  - For each `messaging` event we call `instagram_client.process_webhook_message` to normalize text/attachments. We fetch or create an `InstagramUser` row (updating `username/name/last_seen_at`), create/update a `Chat` (per `instagram_user_id` + page), persist `InstagramMessageLog` + `InstagramMessage`, download attachments, bump unread counts, and broadcast `new_message` / `ig_dm` payloads over websockets.
  - For each `changes` entry with `field` in `{comments,mention,mentions}` we upsert an `InstagramComment` record (`instagram_comments` table) with action `CREATED/UPDATED/DELETED`, then broadcast an `ig_comment` event.

### 3.2 Facebook (Messenger + Page events)

- **Verification**: `GET /webhooks/facebook` expects the same `hub.*` params and compares against `FACEBOOK_WEBHOOK_VERIFY_TOKEN`. The challenge is echoed back (string or int).
- **Endpoint**: `POST /webhooks/facebook`.
- **Security**: Each request must include `X-Hub-Signature-256` (preferred) or `X-Hub-Signature`. We compute `HMAC-SHA256(payload, FACEBOOK_APP_SECRET)` via `facebook_client.verify_webhook_signature`. Invalid signatures yield HTTP 401. On success we still return `{"status":"received"}` even if downstream DB operations fail to prevent repeated retries.
- **Payload** (`object: "page"`):
  ```json
  {
    "object": "page",
    "entry": [
      {
        "id": "<page_id>",
        "messaging": [
          {
            "sender": { "id": "<psid>" },
            "recipient": { "id": "<page_id>" },
            "timestamp": 1731526800000,
            "message": {
              "mid": "<m_...>",
              "text": "Need help",
              "attachments": [...]
            }
          }
        ]
      }
    ]
  }
  ```
- **Processing**:
  - Validate the page exists in `facebook_pages`. Each `messaging` item runs through `facebook_client.process_webhook_message` (normalizes text, attachments, echo flags).
  - We optionally fetch the sender’s profile (`GET /{user_id}?fields=name,profile_pic`) when no cache exists.
  - `FacebookUser` rows are created/updated with `username/name/profile_pic_url`, chats are ensured (`Chat.facebook_user_id`), and `FacebookMessage` rows are inserted. We increment chat unread counts and push websocket notifications.

### 3.3 Comment webhooks

- Instagram comment events piggyback on the same `/webhooks/instagram` route via the `changes` array (see 3.1). Verb → action mapping is handled server-side.
- Facebook comment webhooks are not yet subscribed; comment moderation relies on outbound REST calls initiated by the UI (see 2.4).

---

## 4. Data Models / Storage Mapping

- **`chats`** – Stores conversation metadata (`instagram_user_id`, `facebook_user_id`, `platform`, `last_message`, `profile_pic_url`). Links to `instagram_users` and `facebook_users`.
- **`instagram_users` / `facebook_users`** – Hold user identity fields pulled from Meta (username/name/profile picture, timestamps). Populated on inbound messages and updated on profile fetches.
- **`instagram_messages` / `facebook_messages`** – Platform-specific message tables. `instagram_messages` join to `instagram_users` and preserve attachments, timestamps, `message_id` (Graph).
- **`instagram_message_logs`** – Stores raw webhook payloads (direction, text, attachments JSON) for auditing/resync.
- **`instagram_comments`** – Tracks comment moderation events (action, media_id, author). Populated from webhook `changes`.
- **`facebook_pages` / `instagram_accounts`** – Contain page IDs and long-lived access tokens used by outbound calls.
- **`message_templates`** – Stores template metadata; when submitting to Meta the returned template ID is saved on this table.
- **`instagram_marketing_events`, `instagram_insights`** – Persist Conversions API submissions and insights snapshots.

---

## 5. Future Extension Notes

- **Permissions & tokens**: Outbound calls rely on page access tokens stored in `instagram_accounts` / `facebook_pages`. Ensure tokens carry the correct scopes (`pages_messaging`, `instagram_manage_messages`, `pages_manage_metadata`, `instagram_manage_insights`, `ads_management`, etc.) when adding new features.
- **Rate limits**: The clients currently log failures but only the Conversions API helper retries automatically. Consider adding retry/backoff for senders if Meta returns 429 or transient 5xx.
- **Webhooks**: Any new event subscriptions should reuse the verification helpers; remember to extend signature validation if Meta adds new headers.
- **Documentation links**: When adding new endpoints, append them to this file (grouped by product) and drop inline comments like `// Meta Graph API: see docs/meta-integrations.md#send-instagram-dm` near the call site.

This document now serves as the canonical reference for all Meta integrations until further changes are made.
