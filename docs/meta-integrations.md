## Meta Integrations Overview

TickleGram Inbox Suite talks to Meta’s Graph API across Instagram Direct, Facebook Messenger, comment moderation, insights, and template approvals. All outbound calls originate from the FastAPI backend (`backend/instagram_api.py`, `backend/facebook_api.py`, `backend/meta_template_api.py`) over `httpx.AsyncClient` instances, while webhook handlers in `backend/server.py` ingest Meta callbacks, normalize them into SQL models, and fan out websocket updates. Access tokens live in `instagram_accounts` and `facebook_pages` tables (with optional environment fallbacks like `INSTAGRAM_PAGE_ACCESS_TOKEN`), so no business logic needs to embed secrets in code.

### Permissions & Tokens

- **Instagram Direct/Comments** require at minimum `instagram_basic` + `instagram_manage_messages`. The comment endpoints and comment webhook fields rely on `instagram_manage_comments` (Meta will begin enforcing this for `value.from.username` on 27 Aug 2024 per developers.facebook.com announcements). We also request `pages_manage_metadata` to link business accounts to pages.
- **Instagram Insights/Mentions** leverage `instagram_manage_insights`.
- **Facebook Messenger** uses `pages_messaging` and `pages_manage_metadata`. Reading comments also assumes `pages_read_engagement`/`pages_manage_engagement`.
- **Templates**: page access tokens must be long-lived and carry the scopes above. When we need to mint a page token inside `meta_template_api`, we call `GET /{page_id}?fields=access_token` using the app token `{FACEBOOK_APP_ID}|{FACEBOOK_APP_SECRET}`.
- **Conversions API**: uses the same page/system-user token plus a Pixel ID (`PIXEL_ID` or request payload). Feature parity with Meta’s Ad attribution may require `ads_management` or `leads_retrieval` if we later store referral/lead metadata.

---

## Outbound API Calls

Each table groups related Meta requests. Every call includes its file, request/response semantics, storage targets, and trigger(s).

### Instagram Direct Messaging

| Feature / Use case | Location | Method & endpoint | Auth & request structure | Response fields & persistence | Trigger |
| --- | --- | --- | --- | --- | --- |
| Send Instagram DM text/attachments | `backend/instagram_api.py:send_dm` (wrappers `send_text_message`, `send_attachment`) invoked from `server.py:instagram_dm_send` and `server.py:send_message` when `chat.platform == INSTAGRAM`. | `POST https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/messages` (`GRAPH_VERSION` env, default `v18.0`). | Query param `access_token=<page token>` resolved via `resolve_instagram_access_token` (reads `instagram_accounts` then `INSTAGRAM_PAGE_ACCESS_TOKEN`). JSON body: `{recipient:{id: <IGSID>}, messaging_type:"RESPONSE", message:{text, attachment:{type,payload{url,is_reusable}}}}`. Attachments inherit the same endpoint and `send_attachment` helper simply pre-builds `message.attachment`. | Uses `recipient_id`, `message_id`, and `error{code,message}`. Success inserts an `InstagramMessageLog` (message_id truncated to 255 chars if needed) plus an `InstagramMessage` row created by `create_chat_message_record`. Payload snapshot stored in `raw_payload_json`. | Any outbound DM from `/api/messages/send`, `/api/send`, `/api/chats/{chat_id}/message`, or template preview flows when the platform is Instagram. |
| Send Instagram template/tagged DM | `backend/instagram_api.py:send_template_message`; called from `server.py:send_template` (for approved templates) and fallback when an agent must send `MESSAGE_TAG`. | `POST https://graph.facebook.com/{GRAPH_VERSION}/me/messages`. | Same token resolution as above. Body: `{recipient:{id}, messaging_type:"MESSAGE_TAG", tag: <ACCOUNT_UPDATE by default>, message:{message_creative_id:<template_id>} }` or `message.text` when no template ID provided. | Reads `recipient_id`, `message_id`, logs Meta errors. Stored exactly like standard DMs with extra metadata on the originating `MessageTemplate` row (Meta template ID). | Used by `/api/templates/{template_id}/send` whenever the template is approved (`is_meta_approved`). |

### Instagram Profiles, Comments & Mentions

| Feature / Use case | Location | Method & endpoint | Auth & request structure | Response fields & persistence | Trigger |
| --- | --- | --- | --- | --- | --- |
| Lookup Instagram profile / commenter | `backend/instagram_api.py:get_user_profile`, invoked in `server.py:instagram_dm_send`, `_handle_instagram_webhook`, `/instagram/accounts` connect flow. | `GET https://graph.facebook.com/{GRAPH_VERSION}/{user_id}` with `fields=username,profile_pic,name,id`. | `access_token=<page token>` from `resolve_instagram_access_token`. | Uses `id`, `username`, `name`, `profile_pic`. Stored on `instagram_users` (`username`, `name`) and `Chat.profile_pic_url`. If Meta withholds `username` because `instagram_manage_comments` is missing after Aug 27 2024, the code defaults to “IG User ####”. | Called on every inbound DM, when sending to a new user, and when connecting an account to validate the token. |
| Fetch Instagram media & comments (+ replies) | `backend/instagram_api.py:get_media_comments`, surfaced through `server.py:list_instagram_comments`. | `GET https://graph.facebook.com/{GRAPH_VERSION}/{ig_user_id}/media` with `fields=id,media_type,...,comments{ id,text,username,timestamp,replies{...} }`. | `access_token` from `InstagramAccount.access_token`. Optional `include_media` flag appends `media_type,media_url,permalink,...`. | Consumes `data[].comments[].{id,text,username,timestamp,replies}`. Returned to the UI for moderation and optionally written to `InstagramComment` via webhook events. | `/api/instagram/comments` and dashboard refreshes. |
| Reply to an Instagram comment | `backend/instagram_api.py:reply_to_comment` used by `/api/instagram/comments/{comment_id}/reply`. | `POST https://graph.facebook.com/{GRAPH_VERSION}/{comment_id}/replies`. | Params `message`, `access_token`. | Response `id` of the reply is echoed to the caller and optionally inserted into `InstagramComment` with `InstagramCommentAction.CREATED`. | Agent clicks “Reply” in the comments UI. |
| Create outbound comment | `backend/instagram_api.py:create_comment`, route `/api/comments/create`. | `POST https://graph.facebook.com/{GRAPH_VERSION}/{media_id}/comments`. | Params: `access_token`; body form `message=<text>`. | Response `id` stored in `instagram_comments` via `upsert_instagram_comment`. | Used when an agent proactively comments from Inbox Suite. |
| Hide / unhide comment | `backend/instagram_api.py:set_comment_visibility`, `/api/comments/hide`. | `POST https://graph.facebook.com/{GRAPH_VERSION}/{comment_id}` with form `hide=true|false`. | `access_token` query param. | Response `hidden` flag is written back to `instagram_comments.hidden`. | Triggered when moderator toggles visibility. |
| Delete comment | `backend/instagram_api.py:delete_comment`, `/api/comments/delete`. | `DELETE https://graph.facebook.com/{GRAPH_VERSION}/{comment_id}` with `access_token`. | On success we mark the record as `InstagramCommentAction.DELETED`. | Removing comments from moderation UI. |
| Fetch specific comment details | `backend/instagram_api.py:get_comment_details`, used after hide/delete to enrich metadata. | `GET https://graph.facebook.com/{GRAPH_VERSION}/{comment_id}?fields=id,text,user,from,hidden,parent_id,media{id}`. | Requires `instagram_manage_comments` to populate `from{ id,username }`. | Response hydrates author IDs and `media.id` for `instagram_comments`. | Called whenever we need to ensure we know which post a comment belongs to. |
| Fetch mentioned media | `backend/instagram_api.py:get_mentions`, surfaced at `/api/instagram/mentions`. | `GET https://graph.facebook.com/{GRAPH_VERSION}/{ig_user_id}/mentioned_media?fields=id,caption,media_type,media_url,permalink,timestamp`. | Same page token. | Response `data` rebroadcast via websocket as `ig_comment` type `mentioned`; not persisted. | Agents opening the Mentions page. |

### Instagram Insights & Analytics

| Feature / Use case | Location | Method & endpoint | Auth & request structure | Response fields & persistence | Trigger |
| --- | --- | --- | --- | --- | --- |
| Account insights | `backend/instagram_api.py:get_account_insights` via `/api/insights/account`. | `GET https://graph.facebook.com/{GRAPH_VERSION}/{ig_user_id}/insights`. | Params: `metric=<comma list>`, `period=<day|week|...>`, `access_token`. | Reads `data[].{name,period,values[]}` and stores them in `instagram_insights.metrics_json` with `scope=ACCOUNT`. | Dashboard insights screen or scheduled refresh jobs. |
| Media insights | `backend/instagram_api.py:get_media_insights` via `/api/insights/media`. | `GET https://graph.facebook.com/{GRAPH_VERSION}/{media_id}/insights?metric=...`. | Same token strategy. | Persists values into `instagram_insights` with `scope=MEDIA`. | Analysts selecting a Reel/post to inspect. |
| Story insights | `backend/instagram_api.py:get_story_insights` via `/api/insights/story`. | `GET https://graph.facebook.com/{GRAPH_VERSION}/{story_id}/insights`. | Same params. | Stored in `instagram_insights` with `scope=STORY`. | Story analytics view. |

### Meta Conversions API (Marketing Events)

| Feature / Use case | Location | Method & endpoint | Auth & request structure | Response fields & persistence | Trigger |
| --- | --- | --- | --- | --- | --- |
| Send marketing / CAPI event | `backend/instagram_api.py:send_marketing_event` called by `/api/marketing/events`. | `POST https://graph.facebook.com/{GRAPH_VERSION}/{pixel_id}/events`. | Query: `access_token=<page/system token>`. JSON body: `{ data:[{event_name,event_time,user_data,custom_data,event_source_url?,action_source?,event_id?}], test_event_code? }`. Retries on 429/5xx with exponential backoff. | Reads `events_received`, `fbtrace_id`, or `error{code,message}`; entire response saved to `instagram_marketing_events.response_json`. | Any server-to-server conversion forwarded via the marketing endpoint. |

### Facebook Messenger DMs

| Feature / Use case | Location | Method & endpoint | Auth & request structure | Response fields & persistence | Trigger |
| --- | --- | --- | --- | --- | --- |
| Send Messenger text DM | `backend/facebook_api.py:send_text_message` used by `server.py:send_message` when `chat.platform == FACEBOOK`. | `POST https://graph.facebook.com/v17.0/me/messages`. | Query/body: `access_token=<FacebookPage.access_token>`, body `{recipient:{id:<PSID>}, messaging_type:"RESPONSE", message:{text}}`. | Response `recipient_id`, `message_id` logged and used to store a `FacebookMessage`. | Agents replying inside `/api/chats/{chat_id}/message`. |
| Send Messenger attachment | `backend/facebook_api.py:send_attachment` (currently unused but wired for future) | `POST https://graph.facebook.com/v17.0/me/messages` with `message.attachment.{type,payload{url,is_reusable}}`. | Same token as above. | Would mirror the text response; attachments stored via `FacebookMessage.attachments_json`. | Future support for file/media replies. |
| Send Messenger template/tag outside 24h | `backend/facebook_api.py:send_template_message` used when `/api/templates/{template_id}/send` targets a Facebook chat. | `POST https://graph.facebook.com/v17.0/me/messages` with `{messaging_type:"MESSAGE_TAG",tag,recipient,message:{message_creative_id or text}}`. | Requires page token plus appropriate approved template ID. | Response `message_id` recorded on the outbound chat log. | Template send API. |
| Fetch Messenger profile | `backend/facebook_api.py:get_user_profile`, invoked by `/webhooks/facebook` when we have no cached `FacebookUser`. | `GET https://graph.facebook.com/v17.0/{user_id}?fields=id,name,username,profile_pic,is_verified_user,follower_count,is_user_follow_business,is_business_follow_user`. | Page token from `facebook_pages.access_token`. | Stores `name`, `profile_pic`, `id`, `username` in `facebook_users` and `Chat.username`. | Called during webhook processing and when connecting a page. |

### Facebook Comments & Feed

| Feature / Use case | Location | Method & endpoint | Auth & request structure | Response fields & persistence | Trigger |
| --- | --- | --- | --- | --- | --- |
| Batch fetch feed + comments | `backend/facebook_api.py:get_page_feed_with_comments`, consumed by `/api/facebook/comments`. | `GET https://graph.facebook.com/v17.0/{page_id}/feed` with `fields=id,message,permalink_url,full_picture,comments.limit(25){id,message,created_time,from{id,name,picture{url}},attachment,comments.limit(25){...},reactions.summary(total_count)},reactions.summary(total_count)` and `limit=25`. | Access token from each active `FacebookPage`. | Response flattened into a list of comment dicts (id, text, username, profile_pic_url, replies[], reaction_count, parent post metadata) returned to the UI; not stored in DB. | `/api/facebook/comments` polls each connected page (with optional 1-second delay per page). |
| Fetch posts only *(helper)* | `backend/facebook_api.py:get_page_posts` (unused but available). | `GET https://graph.facebook.com/v17.0/{page_id}/feed?fields=id,message,created_time,permalink_url,full_picture,attachments{...},likes.summary(true),comments.summary(true)` | Page token. | Would yield `id`, `caption`, `media_type`, `like_count`, `comment_count` for analytics UI. | Future dashboards. |
| Fetch comments for a post *(helper)* | `backend/facebook_api.py:get_post_comments`. | `GET https://graph.facebook.com/v17.0/{post_id}/comments?fields=id,message,created_time,from{id,name,picture},comment_count,permalink_url,attachment,reactions.summary(total_count),comments.summary(total_count)&limit=100&filter=toplevel&order=reverse_chronological`. | Page token. | Returns structured dicts including nested replies (fetched separately); intended for granular moderation. | Not currently wired but ready for upcoming features. |
| Fetch replies to comment *(helper)* | `backend/facebook_api.py:get_comment_replies`. | `GET https://graph.facebook.com/v17.0/{comment_id}/comments?fields=id,message,created_time,from{id,name,picture}&limit=100`. | Page token. | Response would fill `replies` arrays when used. | Helper for `get_post_comments`. |
| Reply to FB comment | `backend/facebook_api.py:reply_to_comment` used in `/api/facebook/comments/{comment_id}/reply`. | `POST https://graph.facebook.com/v17.0/{comment_id}/comments`. | Body `{message,access_token}`. | Response `id` indicates the created reply; errors fed back to the UI. | Moderators replying from Inbox Suite. |

### Template Management (Messenger / Instagram)

| Feature / Use case | Location | Method & endpoint | Auth & request structure | Response fields & persistence | Trigger |
| --- | --- | --- | --- | --- | --- |
| Fetch page access token (fallback) | `backend/meta_template_api.py:_get_access_token`. | `GET https://graph.facebook.com/v24.0/{page_id}?fields=access_token`. | `access_token={FACEBOOK_APP_ID}|{FACEBOOK_APP_SECRET}` (app token). | Response `access_token` reused for subsequent template submission/status calls when no explicit token was supplied. | Internal helper used by both functions below. |
| Submit template for approval | `backend/meta_template_api.py:submit_template` invoked by `/api/templates/{template_id}/meta-submit`. | `POST https://graph.facebook.com/v24.0/{page_id}/message_templates`. | Query `access_token=<page token>`. Body: `{name,category,language:"en_US",components:[{type:"BODY",text,example{body_text}}]}` after slugifying `template.name` and normalizing placeholders. | Response `id`, `status`, `category`, `name` mapped onto `message_templates.meta_submission_id`, `.meta_submission_status`, etc. | Template submission UI. |
| Check template status | `backend/meta_template_api.py:check_template_status`, `/api/templates/{template_id}/meta-status`. | `GET https://graph.facebook.com/v24.0/{template_id}?access_token=<page token>`. | Same auth as submit. | Response `id`, `status`, `category`, `name`; we mark `is_meta_approved` and record `meta_template_id` once approved. | Manual refresh from admin console or periodic job. |

---

## Inbound Webhooks

### `/webhooks/instagram` & `/webhook` (GET verification)

- GET requests use query params `hub.mode`, `hub.challenge`, `hub.verify_token`. We validate via `instagram_client.verify_webhook_token`, falling back to the `INSTAGRAM_VERIFY_TOKEN` env var. A matching token echoes `hub.challenge`; anything else returns HTTP 403.

### `/webhooks/instagram` and `/webhook` (POST payloads)

- Both POST routes call `_handle_instagram_webhook`. Each request must include `X-Hub-Signature-256` (or legacy `X-Hub-Signature`). We compute `HMAC-SHA256(payload, INSTAGRAM_APP_SECRET)` via `instagram_client.verify_webhook_signature`; invalid signatures return HTTP 401 unless mock/skip mode is enabled for local testing.
- Payload shape for DMs matches Meta’s messaging schema:

```json
{
  "object": "instagram",
  "entry": [
    {
      "id": "<ig-business-account-id>",
      "time": 1731526800000,
      "messaging": [
        {
          "sender": { "id": "ig_user_123" },
          "recipient": { "id": "<account id>" },
          "timestamp": 1731526800000,
          "message": {
            "mid": "m_A1",
            "text": "Need help",
            "attachments": [{ "type": "image", "payload": { "url": "..." } }],
            "referral": {
              "source": "ADS",
              "type": "OPEN_THREAD",
              "ad_id": "123456",
              "ref": "summer_campaign",
              "ads_context_data": { "campaign_id": "987", "adset_id": "654" }
            }
          }
        }
      ],
      "changes": [...]
    }
  ]
}
```

- We read `sender/recipient/timestamp/message{text,attachments,is_echo,mid}` plus any referral metadata supplied on the messaging event. Those referral fields (source, type, ref, ad_id, `ads_context_data` campaign/adset IDs) are normalized so downstream services can attribute click-to-message ads without replaying the webhook.
- Referral objects (when present on `messaging[i].referral` or `message.referral`) are now normalized into `{source,type,ref,ad_id,adset_id,campaign_id,ads_context_data...}` and stored inside both `instagram_message_logs.metadata_json.referral` and the chat message’s `metadata_json`. We also forward the normalized dict via the websocket DM payload (`referral` key) so the UI/analytics layer can attribute the session immediately.
- Comment events arrive inside the same entry via `changes`:

```json
{
  "field": "comments",
  "value": {
    "id": "178...",             // comment_id
    "media_id": "179...",
    "verb": "add" | "edited" | "delete",
    "from": { "id": "ig_user_123", "username": "shopper" },
    "text": "Great!",
    "timestamp": 1731526800000
  }
}
```

- Processing steps (see `server.py:_handle_instagram_webhook`):
  1. Resolve the page token via `resolve_instagram_access_token(instagram_account_id)`. Skip Meta “test entry” payloads (id `0`).
  2. For every messaging item, call `instagram_client.process_webhook_message` to normalize the payload. We look up/provision `InstagramUser` rows (with `get_user_profile` fallback), create/refresh `Chat` entries (`platform=INSTAGRAM`), and insert an `InstagramMessageLog` and `InstagramMessage`. Attachments are downloaded locally into `backend/attachments/instagram/{igsid}/...` for persistence.
  3. Broadcast websocket events (`ig_dm` and `new_message`) to assigned agents/admins.
  4. For each `changes` entry, map `verb` to `InstagramCommentAction`, upsert an `InstagramComment`, and broadcast an `ig_comment` websocket with `action`, `media_id`, `comment_id`, `author_id`, `hidden`, and `mentioned_user_id`.
- **Permissions note**: The webhook reads `value.from.id` / `.username`. Meta’s developer update states that `instagram_manage_comments` will be required after Aug 27 2024 to populate these fields; without it, author usernames become `None`.

### `/webhooks/facebook` (GET/POST)

- GET uses the same `hub.*` params but validates via `facebook_client.verify_webhook_token`. Successful verification returns `hub.challenge`.
- POST flow:
  - Validate `X-Hub-Signature-256` (fall back to `X-Hub-Signature`) using `facebook_client.verify_webhook_signature(payload, header)`. Missing or invalid signatures return HTTP 401.
  - Payload structure:

```json
{
  "object": "page",
  "entry": [
    {
      "id": "<page_id>",
      "time": 1731526800,
      "messaging": [
        {
          "sender": { "id": "PSID_USER" },
          "recipient": { "id": "<page_id>" },
          "timestamp": 1731526800456,
          "message": {
            "mid": "m_z",
            "text": "Hey there",
            "attachments": [],
            "referral": { "...": "..." }
          }
        }
      ]
    }
  ]
}
```

  - We loop through `entry[].messaging[]`, call `facebook_client.process_webhook_message`, optionally fetch the sender profile via `facebook_client.get_user_profile`, and ensure there is a `Chat` (`platform=FACEBOOK`) + `FacebookUser`. Inbound text is stored in `FacebookMessage` (`create_chat_message_record`), unread counts increment, and websocket notifications fire.
  - Any referral object on the event is normalized (same schema as the Instagram handler) and stored inside the new message’s `metadata_json.referral`, making click-to-Messenger ad attribution data immediately available to reporting layers.
  - Delivery/read receipts, reactions, or other event types remain TODOs; only messaging + referral payloads are processed today.
  - Comment webhooks are **not** configured on the Facebook route; we rely on REST polling via `get_page_feed_with_comments`.

---

## Data Models / Storage Mapping

- **`instagram_accounts` / `facebook_pages`** – hold Meta page/account IDs and long-lived page access tokens. All outbound calls read from these tables (fallback to env).
- **`instagram_users` / `facebook_users`** – store profile metadata fetched via `/user_id?fields=...` for DM participants and commenters.
- **`chats`** – one row per conversation (Instagram DM, Messenger thread). Tracks assignment, unread counts, and links to `instagram_user_id` / `facebook_user_id`.
- **`instagram_messages` / `facebook_messages`** – canonical chat transcripts created via `create_chat_message_record`. `instagram_message_logs` mirrors the raw Graph payload (direction, attachments) for auditing/resync.
- **Referral metadata** – normalized click-to-message information (source/ref/ad_id/campaign_id/ads_context_data) is saved under `metadata_json.referral` for both `instagram_message_logs` and the corresponding chat messages (Instagram + Messenger), allowing downstream attribution without another API call.
- **`instagram_comments`** – comment moderation ledger populated either via webhook `changes` events or via explicit comment API calls (`upsert_instagram_comment`).
- **`instagram_insights`** – snapshots of account/media/story insight metrics keyed by scope + entity.
- **`instagram_marketing_events`** – outbound Conversions API payloads + Meta responses for traceability.
- **`message_templates`** – template text + Meta submission metadata (`meta_submission_id`, `meta_template_id`, `is_meta_approved`).

---

## Extensions / Permissions Notes

- **Instagram comment usernames after Aug 27 2024**: Meta’s developer update mandates `instagram_manage_comments` to read `value.from.username`. We already pass that scope during token generation; ensure future onboarding UIs explicitly request it, otherwise moderation screens will show “Unknown”.
- **Referral capture for DM attribution**: Referral metadata is normalized/stored on every inbound Instagram and Messenger DM (`metadata_json.referral` + IG websocket payloads). If you want to push this further (e.g., map to Ads Manager, pull lead forms), request `ads_management` and/or `leads_retrieval` scopes and hook that data into analytics tables.
- **Lead/ads enrichment**: If we later ingest lead-gen forms or need to fetch lead details via `/leads`, we must add `leads_retrieval` and store system-user tokens. The existing page tokens are sufficient for standard DM/comment/insight work.
- **Standard-access enhancements**: Without new permissions we can still (a) capture comment reactions/likes by extending `get_media_comments` fields, (b) enable quick replies via `message.quick_replies`, (c) enrich insights with additional metrics (stories_exits, website_clicks, ad_impressions), and (d) add comment hide/unhide batching by hitting `/media_id?fields=comments{like_count}`.

---

### Changelog

- Files created: _None_.
- Files modified: `docs/meta-integrations.md`.
- Summary: Catalogued every Meta Graph API call, webhook contract, permissions, data stores, and referral/comment-username considerations so engineers can extend integrations safely.
