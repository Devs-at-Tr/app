# Facebook username lookup fix

We now use the Graph API to fetch a user's Facebook name when Messenger webhooks arrive. If the usual profile lookup returns no name, we call `https://graph.facebook.com/v17.0/{user_id}?fields=name&access_token=FACEBOOK_ACCESS_TOKEN_BACKUP` with a short timeout and populate the chat/user records when successful. Errors are logged but do not block the webhook path.

## Configuration

- Ensure `FACEBOOK_ACCESS_TOKEN_BACKUP` is set in the backend environment. This token must have permission to read the public profile (`public_profile`) so the `name` field is available.
- Optional: set `GRAPH_VERSION` if you need a different Graph API version (defaults to v18.0 elsewhere), but the fallback call here is pinned to `v17.0` to match the verified endpoint.

## Behavior

- The webhook still tries the stored page access token first via the existing `facebook_client.get_user_profile` call.
- If that returns no name, we make a direct Graph API call with the backup token. Non-200 responses and request exceptions are logged for diagnostics.
- The rest of the webhook logic is unchanged; missing names no longer block processing, but successful lookups fill the `name`/`username` fields for chats and `FacebookUser` records.
