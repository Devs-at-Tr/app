# Instagram DM Integration Guide

## Overview
This guide explains how to configure and use the Instagram DM integration in TickleGram Dashboard. The system now supports both Facebook Messenger and Instagram DMs through a unified interface.

## Features Implemented

### Backend
✅ **Instagram API Client** (`instagram_api.py`)
- Mock and Real mode support
- Webhook signature verification
- Send text messages and attachments
- Process incoming DMs
- Handle Instagram-specific features (story replies, post comments)
- User profile fetching

✅ **Instagram Account Management**
- `POST /api/instagram/accounts` - Connect Instagram Business Account
- `GET /api/instagram/accounts` - List all connected accounts
- `GET /api/instagram/accounts/{id}` - Get specific account
- `DELETE /api/instagram/accounts/{id}` - Disconnect account

✅ **Instagram Webhook Handlers**
- `GET /api/webhooks/instagram` - Webhook verification
- `POST /api/webhooks/instagram` - Receive Instagram DMs

### Real-Time DM Streaming
- `/webhook` (GET/POST) exposed without the `/api` prefix for Meta's webhook subscription.
- `/messages/send` (POST) sends Instagram DMs using the Page access token defined in `.env`.
- WebSocket broadcasts include `type: "ig_dm"` (legacy `instagram_dm`) with direction, igsid, text, attachments, timestamp, and delivery status.
- Offline agents receive queued DM events automatically on reconnect.
- Persistent storage uses the `instagram_users` and `instagram_messages` tables to keep history.

? **Instagram Comments & Mentions**
- CRUD helpers for comments exposed via `/api/comments/create|hide|delete`.
- Mentions feed available at `/api/instagram/mentions`.
- Webhook ingestion stores rows in `instagram_comments` and emits `type: "ig_comment"` events.

? **Instagram Insights**
- Account/media/story insights fetched through `/api/insights/{scope}`.
- Results cached in `instagram_insights` and broadcast as `type: "ig_insights"` payloads.

? **Marketing Events (Conversions API)**
- `/api/marketing/events` forwards purchase/lead/etc. to Meta Pixel with retries and idempotency.
- Events persisted in `instagram_marketing_events` and streamed as `type: "ig_marketing_event"`.

✅ **Cross-Platform Message Sending**
- Unified message sending through `POST /api/chats/{id}/message`
- Auto-detects platform (Instagram/Facebook)
- Uses appropriate API client for each platform

### Frontend
✅ **Instagram Account Manager Component**
- Connect/disconnect Instagram Business Accounts
- View connected accounts with status
- Setup instructions and guidance
- Admin-only access

✅ **Dashboard Integration**
- "Manage Instagram" button in dashboard (admin only)
- Instagram and Facebook manager side-by-side
- Platform filtering includes Instagram
- Instagram-specific UI indicators (pink/purple gradient)

## Configuration

### Environment Variables

#### Backend (.env)
```env
# Instagram Configuration
INSTAGRAM_MODE=mock                           # Use 'mock' for dev, 'real' for production
INSTAGRAM_APP_SECRET=${FACEBOOK_APP_SECRET}   # Uses same app as Facebook
INSTAGRAM_WEBHOOK_VERIFY_TOKEN=${FACEBOOK_WEBHOOK_VERIFY_TOKEN}
INSTAGRAM_WEBHOOK_TIMEOUT=30
INSTAGRAM_PAGE_ID=your-instagram-page-id
INSTAGRAM_PAGE_ACCESS_TOKEN=your-instagram-page-access-token
VERIFY_TOKEN=your-instagram-verify-token
PIXEL_ID=your-meta-pixel-id
GRAPH_VERSION=v21.0
INSTAGRAM_SKIP_SIGNATURE=false          # Set true only for debugging signature issues
```

#### Frontend (.env)
```env
REACT_APP_BACKEND_URL=/api
WDS_SOCKET_PORT=0
```

## Setup Instructions

### Prerequisites
1. **Instagram Business Account** - Your Instagram account must be:
   - Converted to a Business Account
   - Connected to a Facebook Page
   
2. **Facebook Developer App** with:
   - Instagram Basic Display API enabled
   - Instagram Graph API access
   - Webhook subscriptions configured

### Step 1: Configure Facebook App for Instagram

1. **Go to Facebook Developers Console**
   - Visit: https://developers.facebook.com
   - Select your app

2. **Add Instagram Product**
   - Dashboard → Add Product
   - Select "Instagram"
   - Complete the setup

3. **Configure Webhook Subscriptions**
   - Go to Products → Instagram → Configuration
   - Add webhook callback URL: `https://your-domain.com/api/webhooks/instagram`
   - Verify token: Use the value from `INSTAGRAM_WEBHOOK_VERIFY_TOKEN`
   - Subscribe to fields: `messages`, `messaging_postbacks`, `messaging_optins`

4. **Get Required Permissions**
   - `instagram_basic`
   - `instagram_manage_messages`
   - `pages_messaging`
   - `pages_read_engagement`

### Step 2: Get Instagram Account ID and Access Token

#### Method 1: Graph API Explorer
1. Go to: https://developers.facebook.com/tools/explorer/
2. Select your app
3. Get Page Access Token for your Facebook Page
4. Make API call: `GET /{page-id}?fields=instagram_business_account`
5. Copy the `instagram_business_account.id`

#### Method 2: Using API Call
```bash
curl -X GET "https://graph.facebook.com/v18.0/{page-id}?fields=instagram_business_account&access_token={page-access-token}"
```

### Step 3: Update Environment Variables

**For REAL Mode:**
```env
# Backend .env
INSTAGRAM_MODE=real
FACEBOOK_APP_ID=your-actual-app-id
FACEBOOK_APP_SECRET=your-actual-app-secret
FACEBOOK_WEBHOOK_VERIFY_TOKEN=your-verify-token
```

**For MOCK Mode (Development):**
```env
# Backend .env
INSTAGRAM_MODE=mock
# No real credentials needed for mock mode
```

### Step 4: Connect Instagram Account in Dashboard

1. **Login as Admin**
   - Email: `admin@ticklegram.com`
   - Password: `admin123`

2. **Open Instagram Manager**
   - Click "Manage Instagram" button in dashboard

3. **Add Instagram Account**
   - Click "Connect New Instagram Account"
   - Enter Instagram Account ID (from Step 2)
   - Enter Username (optional, will be auto-fetched in real mode)
   - Enter Page Access Token
   - Click "Connect Account"

4. **Verify Connection**
   - Account should appear in the list
   - Status shows as "Active"

### Step 5: Test the Integration

#### Mock Mode Testing
1. Generate mock Instagram chats:
   ```bash
   curl -X POST "http://localhost:8001/api/mock/generate-chats?count=5&platform=instagram" \
        -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. Simulate incoming message:
   ```bash
   curl -X POST "http://localhost:8001/api/mock/simulate-message" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"chat_id": "CHAT_ID", "message": "Test message"}'
   ```

#### Real Mode Testing
1. Send a DM to your Instagram Business Account from a test account
2. Message should appear in the dashboard
3. Reply from dashboard - message should be received on Instagram

## API Endpoints

### Instagram Accounts
```
POST   /api/instagram/accounts          # Connect Instagram account
GET    /api/instagram/accounts          # List all accounts
GET    /api/instagram/accounts/{id}     # Get specific account
DELETE /api/instagram/accounts/{id}     # Disconnect account
```

### Instagram Webhooks
```
GET    /api/webhooks/instagram          # Webhook verification
POST   /api/webhooks/instagram          # Receive Instagram messages
GET    /webhook                         # Public verification endpoint
POST   /webhook                         # Public webhook receiver (messages/comments)
```

### Cross-Platform Messaging
```
POST   /api/chats/{id}/message          # Send message (auto-detects platform)
GET    /api/chats?platform=instagram    # Filter chats by platform
POST   /messages/send                   # Direct Instagram DM send
POST   /api/messages/send               # (legacy alias)
```

### Instagram Comments & Mentions
```
POST   /api/comments/create             # Create comment on media
POST   /api/comments/hide               # Hide/Unhide comment
DELETE /api/comments/delete             # Delete comment
GET    /api/instagram/mentions          # Fetch mentioned media stream
```

### Instagram Insights
```
GET    /api/insights/account            # Account insights (metrics & period query params)
GET    /api/insights/media              # Media insights (media_id, metrics)
GET    /api/insights/story              # Story insights (story_id, metrics)
```

### Marketing Events (Conversions API)
```
POST   /api/marketing/events            # Forward marketing events to Meta Pixel
```

## cURL Samples

> Replace placeholders (`GRAPH_VERSION`, `PAGE_ACCESS_TOKEN`, `IG_MEDIA_ID`, etc.) before executing.

```bash
# Create comment
curl -X POST "https://graph.facebook.com/GRAPH_VERSION/IG_MEDIA_ID/comments" \
  -d "message=Great post! 🎯" \
  -d "access_token=PAGE_ACCESS_TOKEN"

# Hide or unhide comment
curl -X POST "https://graph.facebook.com/GRAPH_VERSION/COMMENT_ID" \
  -d "hide=true" \
  -d "access_token=PAGE_ACCESS_TOKEN"

# Delete comment
curl -X DELETE "https://graph.facebook.com/GRAPH_VERSION/COMMENT_ID?access_token=PAGE_ACCESS_TOKEN"

# Send DM
curl -X POST "https://graph.facebook.com/GRAPH_VERSION/PAGE_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": { "id": "IG_SCOPED_USER_ID" },
    "message": { "text": "Hello from our app 👋" }
  }' \
  -d "access_token=PAGE_ACCESS_TOKEN"

# Marketing event via Conversions API
curl -X POST "https://graph.facebook.com/GRAPH_VERSION/PIXEL_ID/events" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "event_name":"Purchase","event_time":1730440000,
      "user_data":{"client_ip_address":"1.2.3.4","client_user_agent":"UA"},
      "custom_data":{"currency":"INR","value":4999}
    }],
    "test_event_code":"TEST123"
  }' \
  -d "access_token=SYSTEM_OR_PAGE_TOKEN"
```

## Architecture

### How It Works

1. **Webhook Flow**
   ```
   Instagram → Webhook → instagram_api.py → Database → Frontend
   ```

2. **Message Sending Flow**
   ```
   Frontend → API → Detect Platform → Instagram Client → Instagram API
   ```

3. **Account Management**
   ```
   Admin → Dashboard → InstagramAccountManager → API → Database
   ```

### Platform Detection
The system automatically detects the platform based on the chat's `platform` field:
- `MessagePlatform.INSTAGRAM` → Uses `instagram_client`
- `MessagePlatform.FACEBOOK` → Uses `facebook_client`

## Troubleshooting

### Webhook Not Receiving Messages
1. **Check webhook verification**:
   ```bash
   curl "http://localhost:8001/api/webhooks/instagram?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=12345"
   ```
   Should return: `12345`

2. **Check Instagram webhook subscription in Facebook Developer Console**
   - Ensure all required fields are subscribed
   - Verify callback URL is correct and accessible

3. **Check backend logs**:
   ```bash
   tail -f /var/log/supervisor/backend.err.log
   ```

### Messages Not Sending
1. **Verify Instagram account is connected**:
   ```bash
   curl -X GET "http://localhost:8001/api/instagram/accounts" \
        -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. **Check access token validity**:
   - Page Access Tokens expire
   - Generate long-lived token (60 days) or use permanent token

3. **Verify permissions**:
   - Account must have `instagram_manage_messages` permission

### Database Issues
1. **Check database connection**:
   ```bash
   tail -n 50 /var/log/supervisor/backend.err.log | grep -i "database"
   ```

2. **Verify Instagram account table exists**:
   - Table: `instagram_accounts`
   - Should be created automatically by SQLAlchemy

## Security Notes

1. **Access Tokens**: Never commit access tokens to version control
2. **Webhook Signature**: Always verify webhook signatures in production
3. **HTTPS Required**: Instagram requires HTTPS for webhook URLs
4. **Token Refresh**: Implement token refresh for long-lived deployments

## Mock vs Real Mode

### Mock Mode (INSTAGRAM_MODE=mock)
- ✅ No Instagram credentials required
- ✅ Perfect for development and testing
- ✅ Simulates all API responses
- ❌ No real Instagram integration

### Real Mode (INSTAGRAM_MODE=real)
- ✅ Full Instagram integration
- ✅ Real message sending/receiving
- ✅ Production-ready
- ⚠️ Requires valid credentials and setup

## Additional Resources

- [Instagram Graph API Documentation](https://developers.facebook.com/docs/instagram-api)
- [Instagram Messaging API](https://developers.facebook.com/docs/messenger-platform/instagram)
- [Webhook Setup Guide](https://developers.facebook.com/docs/graph-api/webhooks)
- [Access Token Guide](https://developers.facebook.com/docs/facebook-login/access-tokens)

## Support

For issues or questions:
1. Check logs: `/var/log/supervisor/backend.err.log`
2. Review environment configuration
3. Verify Instagram Business Account setup
4. Check Facebook Developer Console for errors
