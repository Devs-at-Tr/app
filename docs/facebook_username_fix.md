# Facebook username lookup fix

Incoming Facebook messages now follow a stricter token-resolution flow so we can fetch a user's name even when Meta returns only a page-scoped ID (PSID).

## Configuration

- Ensure `FACEBOOK_ACCESS_TOKEN_BACKUP` is set in the backend environment. This token must have permission to read the public profile (`public_profile`) so the `name` field is available.
- Optional: set `GRAPH_VERSION` if you need a different Graph API version (defaults to v18.0). The fallback Graph API request uses the same value.

## Token selection

When a webhook needs a Facebook user's profile we select a token in this order:

1. The access token of the page that triggered the webhook.
2. If unavailable, the page token linked to the user's most recent chat.
3. Finally, the `FACEBOOK_ACCESS_TOKEN_BACKUP` value.

Each attempt logs its token source. If no token is available we skip the lookup but keep processing the webhook.

## Behavior

- The selected token is passed to `facebook_client.get_user_profile`. Failures and error payloads are logged with the token source.
- If Meta still doesn't return a name, we directly call `https://graph.facebook.com/{GRAPH_VERSION}/{user_id}?fields=name` with the backup token as a last resort.
- Successful lookups populate both the chat record and the `facebook_users` table, and the rest of the webhook logic remains unchanged.
