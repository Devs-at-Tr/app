# Facebook WebSocket Fix

## Problem
Facebook messages were not triggering real-time updates in the dashboard via WebSocket, while Instagram messages were working correctly.

## Root Cause
The Facebook webhook handler (`handle_facebook_webhook` in `server.py`) was missing the WebSocket broadcasting code that was present in the Instagram webhook handler. When a new Facebook message arrived:

1. ✅ The message was being saved to the database
2. ✅ The chat was being created/updated
3. ❌ **No WebSocket notification was being sent to connected clients**
4. ❌ **Unread count was not being incremented**
5. ❌ **Chat timestamp was not being updated**

This meant that users had to manually refresh the page to see new Facebook messages.

---

## Solution

### Updated: `backend/server.py` - Facebook Webhook Handler

**Added the following code after saving the Facebook message (line ~1030):**

```python
# Update chat metadata
chat.unread_count += 1
chat.updated_at = datetime.now(timezone.utc)

db.commit()
db.refresh(new_message)
logger.info(f"Processed Facebook message from {sender_id} on page {page_id}")

# Notify relevant users about new message
notify_users = set()

# Add assigned agent if any
if chat.assigned_to:
    notify_users.add(str(chat.assigned_to))

# Add admin users
admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
notify_users.update(str(user.id) for user in admin_users)

message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")

# Broadcast new message notification
await ws_manager.broadcast_to_users(notify_users, {
    "type": "new_message",
    "chat_id": str(chat.id),
    "platform": chat.platform.value,
    "sender_id": sender_id,
    "message": message_payload
})
```

---

## What Changed

### 1. **Unread Count Increment**
```python
chat.unread_count += 1
```
Now Facebook messages increment the unread count badge, just like Instagram.

### 2. **Timestamp Update**
```python
chat.updated_at = datetime.now(timezone.utc)
```
Chat sorting is now correct - most recent Facebook messages appear at the top.

### 3. **Database Refresh**
```python
db.refresh(new_message)
```
Ensures the message object has all the database-generated fields (ID, timestamp, etc.) before broadcasting.

### 4. **WebSocket Notification**
```python
await ws_manager.broadcast_to_users(notify_users, {
    "type": "new_message",
    "chat_id": str(chat.id),
    "platform": chat.platform.value,
    "sender_id": sender_id,
    "message": message_payload
})
```
Broadcasts the new message to:
- The assigned agent (if any)
- All admin users

---

## How It Works Now

### Facebook Message Flow (Fixed):
1. **Webhook receives message** from Facebook
2. **Message is saved** to database
3. **Chat metadata updated** (unread count, timestamp)
4. **Database refresh** ensures all fields are populated
5. **WebSocket notification sent** to relevant users
6. **Frontend receives notification** and updates UI in real-time

### Instagram Message Flow (Already Working):
1. Webhook receives message from Instagram
2. Message is saved to database
3. Chat metadata updated (unread count, timestamp)
4. Database refresh ensures all fields are populated
5. WebSocket notification sent to relevant users
6. Frontend receives notification and updates UI in real-time

**Both platforms now have identical real-time behavior!** 🎉

---

## Testing

### How to Test Facebook WebSocket:

1. **Start the backend** (if not already running):
   ```powershell
   cd backend
   python server.py
   ```

2. **Start the frontend**:
   ```powershell
   cd frontend
   npm start
   ```

3. **Login to the dashboard**:
   - Navigate to `http://localhost:3000`
   - Login with admin or agent credentials

4. **Send a Facebook message**:
   - If in **MOCK mode**: Use the mock data generator or send directly via API
   - If in **REAL mode**: Send a message to your connected Facebook Page

5. **Verify real-time update**:
   - ✅ Chat should appear in the sidebar immediately
   - ✅ Unread badge should show on the chat
   - ✅ Message should appear in the chat window if that chat is open
   - ✅ No page refresh required!

### Comparison Test:

Open the dashboard in two browser windows (or tabs):
- Window 1: Login as Admin
- Window 2: Login as Agent (if the chat is assigned to them)

Send a Facebook message:
- ✅ Both windows should update in real-time
- ✅ Both should see the new message instantly
- ✅ Unread count should update in both windows

---

## Files Modified

- ✅ `backend/server.py` - Added WebSocket broadcasting to Facebook webhook handler

---

## Benefits

1. **✅ Real-time Facebook messages** - No more manual refresh needed
2. **✅ Consistent behavior** - Facebook and Instagram now work the same way
3. **✅ Unread count works** - Badge shows correct count for Facebook messages
4. **✅ Proper chat sorting** - Most recent chats appear at the top
5. **✅ Multi-user sync** - All connected users see updates simultaneously

---

## Technical Details

### WebSocket Manager
The `ws_manager.broadcast_to_users()` function:
- Sends notifications to specific users by their user IDs
- Handles connection failures gracefully
- Queues messages if a user is temporarily disconnected

### Message Flow
```
Facebook → Webhook → Database → WebSocket → Frontend
         (webhook)  (save)    (broadcast)  (update UI)
```

### Notification Payload
```json
{
  "type": "new_message",
  "chat_id": "uuid-of-chat",
  "platform": "FACEBOOK",
  "sender_id": "facebook-user-id",
  "message": {
    "id": "message-uuid",
    "content": "Message text",
    "sender": "facebook_user",
    "timestamp": "2025-10-10T12:00:00Z",
    ...
  }
}
```

---

## Notes

- The fix maintains parity with Instagram's working implementation
- No changes needed to the frontend - it already handles Facebook messages
- The WebSocket connection is managed by `WebSocketContext.js`
- Messages are broadcast to admin users and assigned agents only
- Unassigned chats are visible to all admins

---

## Troubleshooting

If Facebook messages still don't appear in real-time:

1. **Check WebSocket connection**:
   - Open browser DevTools → Network tab
   - Look for WS (WebSocket) connection
   - Should show "101 Switching Protocols"

2. **Check backend logs**:
   - Look for: `"Processed Facebook message from..."`
   - Followed by: WebSocket broadcast logs

3. **Check frontend console**:
   - Should show: `"Received WebSocket message:"`
   - Check the payload for the `new_message` type

4. **Verify Facebook webhook is working**:
   - Check backend logs for: `"Received Facebook webhook"`
   - Verify the message is being saved to database

---

Facebook WebSocket is now fully functional! 🚀
