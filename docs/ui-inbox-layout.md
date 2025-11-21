# Inbox Layout Overview

## Structure
- **AppShell (`frontend/src/layouts/AppShell.jsx`)** – wraps every authed page with the global sidebar + mobile header. The inbox uses the same shell.
- **InboxLayout (`frontend/src/layouts/InboxLayout.jsx`)** – applies page padding and renders the stats/filter block plus the workspace below.
- **InboxWorkspace (`frontend/src/layouts/InboxWorkspace.jsx`)** – grid that places the conversation list (`listColumn`) next to the chat window (`conversationColumn`). An optional details rail may mount on very large screens.
- **ChatSidebar (`frontend/src/components/ChatSidebar.js`)** – renders search + the list of conversations. Width is constrained via CSS (`minmax(220px, 320px)`).
- **ChatWindow (`frontend/src/components/ChatWindow.js`)** – message thread, composer, compact header, and all overlays drawer logic.
- **Profile Drawer (`ChatProfilePanel`)** – same component serves both mobile and desktop views. On desktop it’s rendered via `createPortal` into a fixed drawer on the far right.

## Responsiveness
- **≥ 1440px** – Grid uses `minmax(240px, 320px)` for the list and lets the chat window grow. When the profile drawer is open, it slides in as a fixed 360 px panel without shrinking the chat width.
- **1024–1366px** – Same two-column grid but the conversation list narrows to `minmax(220px, 300px)`. Header/pills wrap and no horizontal scroll is introduced.
- **< 1024px** – Existing mobile mode (list vs. chat panels) remains: the ChatWindow shows a back button and the profile drawer renders inline beneath the thread.

## Profile Drawer
- Triggered from the “Details” button inside `ChatWindow`.
- Desktop drawer is rendered inside the chat container and uses `.chat-profile-overlay` (absolute positioned) + `.chat-profile-overlay__panel` for the fixed 360 px column. The chat card uses the remaining grid width while the drawer floats above it, so the thread keeps the full column width.
- Mobile version reuses the same component inline below the chat window.

### Styling Hooks
- `.chat-profile-overlay` / `.chat-profile-overlay__panel` – control drawer positioning and max width.
- `.inbox-layout__columns` – defines grid widths; tweak here if the list/chat proportions need adjustment.
- `.conversation-header` – sets compact padding / gap for the header rows.
- `ChatSidebar` – list padding/search alignment; future spacing tweaks can be done there without touching layout.

Use this doc before editing inbox layout so you know which component controls each section.***
