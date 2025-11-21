# Frontend Responsiveness Guide

## Breakpoints & Layout
- **≥1280px**: Inbox keeps the three-panel experience (sidebar + list + thread + optional details). Comments render all three columns.
- **1024–1279px**: Inbox shows the chat list (~300px) beside the thread with tighter gutters; Comments still show list + thread side-by-side while the details preview collapses.
- **<1024px**: Inbox switches to the Chats/Conversation toggle with the search/filters pinned above the list. Comments get a Recent/Thread toggle so only one column is visible at a time. Filters open in a sheet to avoid horizontal scroll.
- **<768px**: Chat composer becomes sticky and the chat body gets extra bottom padding so the reply bar stays reachable. Comments reuse the compact toggle and the profile/details card is collapsible under the thread header.

## Key Components
- `frontend/src/pages/InboxPage.js`: owns the responsive filter bar, compact filter sheet, and the chats/conversation toggle logic.
- `frontend/src/layouts/InboxWorkspace.jsx` & `frontend/src/components/ChatSidebar.js`: ensure chat list/thread columns use `min-h-0` flex containers so only the intended panel scrolls.
- `frontend/src/components/ChatWindow.js` + `frontend/src/App.css`: provide sticky composer + overflow padding rules for smaller screens.
- `frontend/src/components/SocialComments.js` & `frontend/src/layouts/CommentsLayout.jsx`: add compact pane toggles, inline profile panel, and tablet/mobile behaviors for the comments module.
- `frontend/src/App.css`: central place for new responsive helpers (filter/search widths, comments toggle styles, compact column tweaks).

## Compact Toggles & Filters
- Inbox filters collapse into a small card + "Filters" sheet trigger when `<1024px`. Refresh remains a pill button while the rest of the actions (Unseen, Needs reply, Agent select) live inside the sheet.
- The Chats/Conversation toggle automatically switches to Conversation when an item is selected. Returning to Chats preserves the current filter state.
- Comments use a `Recent` / `Thread` toggle; selecting an item auto-focuses the thread pane on compact screens. Profile details sit behind the header toggle so tablets avoid triple-stacked columns.

## Extending
- To add new chat filters, drop another control inside `renderFilterActions` in `InboxPage.js`; it will automatically appear inline on desktop and in the sheet on compact screens.
- For comments, extend `CommentsLayout` with additional compact panes if ever needed—the toggle component is already centralized there.

Only layout/styling was changed; API calls and business logic remain untouched.