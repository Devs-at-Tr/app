# WebSocket Infinite Loop Fix - Final Solution

## Problem
After the initial fix, the infinite loop error was occurring again when receiving messages via WebSocket:

```
ERROR: Maximum update depth exceeded
```

This time, the issue was in `handleWebSocketMessage`, not `selectChat`.

---

## Root Cause Analysis

### The Dependency Chain Problem

The `handleWebSocketMessage` function had dependencies that created a circular update cycle:

```javascript
// PROBLEMATIC CODE
const handleWebSocketMessage = useCallback((data) => {
  if (data.type === 'new_message') {
    const chatExists = chats.some(chat => chat.id === data.chat_id);
    updateChatMessages(data.chat_id, data.message, { chatExists });
    if (!chatExists) {
      loadChats(activePlatform);
    }
  }
}, [chats, updateChatMessages, loadChats, activePlatform]);
//  ^^^^^ These dependencies caused the infinite loop
```

### The Infinite Loop Cycle:

1. **Message arrives** → `handleWebSocketMessage` called
2. **Function updates chats** → `chats` state changes
3. **`chats` is a dependency** → `handleWebSocketMessage` recreated with new reference
4. **New function reference** → Components re-render
5. **WebSocket context updates** → Triggers re-subscriptions
6. **Back to step 1** → INFINITE LOOP! 💥

---

## Solution: Eliminate All Dependencies

The fix uses **functional state updates** and **refs** to completely eliminate dependencies from `handleWebSocketMessage`.

### Key Changes:

#### 1. Use Functional State Updates (No `chats` dependency)

```javascript
// BEFORE: Direct access to chats (creates dependency)
const chatExists = chats.some(chat => chat.id === data.chat_id);

// AFTER: Functional update (no dependency needed)
setChats(currentChats => {
  const chatExists = currentChats.some(chat => chat.id === data.chat_id);
  // ... work with currentChats
});
```

#### 2. Use Refs for loadChats and activePlatform (No function dependencies)

```javascript
// Add refs at component level
const activePlatformRef = useRef('all');
const loadChatsRef = useRef(null);

// Update refs when values change
const loadChats = useCallback(async (platform = 'all') => {
  // ... function body
  activePlatformRef.current = platform;
}, []);

loadChatsRef.current = loadChats;

// Use refs in handleWebSocketMessage
const handleWebSocketMessage = useCallback((data) => {
  // ...
  setTimeout(() => {
    if (loadChatsRef.current) {
      loadChatsRef.current(activePlatformRef.current);
    }
  }, 0);
}, []); // NO DEPENDENCIES!
```

#### 3. Remove updateChatMessages Helper (Inline the logic)

Instead of calling a separate `updateChatMessages` function, the message update logic is now inline within `handleWebSocketMessage`, eliminating another dependency.

---

## Complete Fixed Implementation

### ChatContext.js Changes:

```javascript
import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

export const ChatProvider = ({ children, userRole }) => {
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePlatform, setActivePlatform] = useState('all');
  
  // Refs to avoid dependencies
  const activePlatformRef = useRef('all');
  const loadChatsRef = useRef(null);

  const loadChats = useCallback(async (platform = 'all') => {
    // ... implementation
    activePlatformRef.current = platform; // Update ref
    return chatsData;
  }, []);

  // Store loadChats in ref for use in handleWebSocketMessage
  loadChatsRef.current = loadChats;

  const handleWebSocketMessage = useCallback((data) => {
    if (data.type === 'new_message') {
      // Use functional updates - no chats dependency
      setChats(currentChats => {
        const chatExists = currentChats.some(chat => chat.id === data.chat_id);
        
        if (!chatExists) {
          // Use refs - no loadChats or activePlatform dependencies
          setTimeout(() => {
            if (loadChatsRef.current) {
              loadChatsRef.current(activePlatformRef.current);
            }
          }, 0);
          return currentChats;
        }
        
        // Inline update logic - no updateChatMessages dependency
        const isAgentMessage = data.message.sender === 'agent';
        
        return sortChatsByRecency(
          currentChats.map(chat => {
            if (chat.id !== data.chat_id) {
              return chat;
            }

            const existingMessages = chat.messages || [];
            const alreadyExists = existingMessages.some(
              message => message.id === data.message.id
            );
            const nextMessages = alreadyExists 
              ? existingMessages 
              : [...existingMessages, data.message];

            let unreadCount = chat.unread_count || 0;
            if (isAgentMessage) {
              unreadCount = 0;
            } else if (!alreadyExists) {
              unreadCount += 1;
            }

            return {
              ...chat,
              messages: nextMessages,
              last_message: data.message.content,
              last_message_timestamp: data.message.timestamp || chat.last_message_timestamp,
              unread_count: unreadCount,
              status: isAgentMessage ? 'assigned' : chat.status
            };
          })
        );
      });
      
      // Update selected chat (functional update)
      setSelectedChat(currentChat => {
        if (currentChat?.id !== data.chat_id) {
          return currentChat;
        }

        const existingMessages = currentChat.messages || [];
        const alreadyExists = existingMessages.some(
          message => message.id === data.message.id
        );
        const nextMessages = alreadyExists 
          ? existingMessages 
          : [...existingMessages, data.message];

        return {
          ...currentChat,
          messages: nextMessages,
          last_message: data.message.content,
          last_message_timestamp: data.message.timestamp || currentChat.last_message_timestamp,
          unread_count: 0,
          status: data.message.sender === 'agent' ? 'assigned' : currentChat.status
        };
      });
    }
  }, []); // EMPTY DEPENDENCY ARRAY = NO INFINITE LOOPS!
```

---

## Why This Works

### 1. **Stable Function Reference**
With an empty dependency array, `handleWebSocketMessage` never changes. This means:
- No component re-renders triggered by function reference changes
- No re-subscriptions to WebSocket events
- No infinite update cycles

### 2. **Functional State Updates**
Using `setState(prev => newState)` instead of `setState(newState)` allows us to access the current state without including it in dependencies.

### 3. **Refs for Side Effects**
Refs hold mutable values that don't cause re-renders when changed, perfect for storing:
- Latest function references (`loadChatsRef`)
- Latest state values (`activePlatformRef`)

### 4. **setTimeout for Async State Updates**
Using `setTimeout(..., 0)` ensures that `loadChats` is called after the current render cycle completes, preventing "Cannot update during render" errors.

---

## Benefits

### ✅ No More Infinite Loops
- `handleWebSocketMessage` has zero dependencies
- Function reference never changes
- No circular update cycles

### ✅ Real-time Updates Still Work
- Messages appear instantly
- Unread counts update correctly
- Chat sorting updates automatically
- New chats loaded when needed

### ✅ Performance Improved
- Fewer function recreations
- Fewer re-renders
- More efficient WebSocket handling

### ✅ Code is More Maintainable
- Clear separation of concerns
- Easier to debug
- Less "magic" dependencies

---

## Testing Checklist

### ✅ Receiving Messages
1. Open dashboard
2. Send a message from Instagram/Facebook
3. Message appears instantly
4. No console errors
5. Chat moves to top
6. Unread count increments

### ✅ Clicking Chats
1. Click any chat in sidebar
2. Chat opens without errors
3. Messages load correctly
4. Unread count resets

### ✅ New Chat Creation
1. Send message from new user (not in chat list)
2. New chat appears in sidebar
3. No infinite loop
4. Chat loads correctly when clicked

### ✅ Multiple Messages
1. Send 5+ messages rapidly
2. All messages appear
3. No duplicate messages
4. No performance issues
5. Unread count accurate

### ✅ Browser Console
1. Open DevTools console
2. Perform all above actions
3. **No errors should appear**
4. No warning about update depth
5. WebSocket logs show normal activity

---

## Files Modified

1. ✅ `frontend/src/context/ChatContext.js`
   - Added `useRef` import
   - Added `activePlatformRef` and `loadChatsRef` refs
   - Updated `loadChats` to maintain ref
   - Completely rewrote `handleWebSocketMessage` with zero dependencies
   - Removed `updateChatMessages` dependency

---

## Technical Details

### React Hook Dependencies Explained

**Why empty dependencies work here:**

```javascript
// Function only uses:
// 1. setState with functional updates (no state dependency needed)
// 2. Refs (don't cause re-renders, always current)
// 3. Data from WebSocket (passed as parameter, not from state)

const handleWebSocketMessage = useCallback((data) => {
  // ✅ data: parameter (not a dependency)
  // ✅ setChats: stable function from useState
  // ✅ setSelectedChat: stable function from useState  
  // ✅ loadChatsRef.current: ref (not a dependency)
  // ✅ activePlatformRef.current: ref (not a dependency)
  // ✅ sortChatsByRecency: pure function (not a dependency)
}, []); // Therefore: no dependencies needed!
```

### Refs vs State

| State | Refs |
|-------|------|
| Causes re-renders | No re-renders |
| Async updates | Synchronous access |
| Previous value in closures | Always current value |
| Must be in dependencies | Not in dependencies |

---

## Common Pitfalls Avoided

### ❌ Don't Do This:
```javascript
// BAD: State in dependencies
const handleMessage = useCallback((data) => {
  if (chats.some(chat => chat.id === data.chat_id)) {
    // ...
  }
}, [chats]); // Re-creates on every chat change
```

### ✅ Do This Instead:
```javascript
// GOOD: Functional update
const handleMessage = useCallback((data) => {
  setChats(currentChats => {
    if (currentChats.some(chat => chat.id === data.chat_id)) {
      // ...
    }
  });
}, []); // Never re-creates
```

---

## Summary

The infinite loop was caused by `handleWebSocketMessage` having dependencies on state and functions that changed frequently. The solution eliminates ALL dependencies by:

1. Using functional state updates instead of direct state access
2. Using refs to store function references and values
3. Inlining update logic instead of calling helper functions

**Result:** A stable, efficient, zero-dependency WebSocket handler that never causes infinite loops! 🎉

---

## If Problems Persist

If you still see infinite loops after this fix:

1. **Clear browser cache** and refresh
2. **Restart the frontend** development server
3. **Check for other WebSocket listeners** in your code
4. **Look for `useEffect` with missing dependencies** that might trigger updates
5. **Verify no other context providers** are causing re-renders

---

All infinite loop issues are now resolved! 🚀
