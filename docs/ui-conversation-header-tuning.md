# Conversation Header & Layout Tuning

## Components touched
- `frontend/src/components/ChatWindow.js`
  * Rebuilt the conversation header into a compact, multi-row layout with truncation.
  * Added a “More info” dropdown (Info icon) that exposes handle, assignment, status, and last-activity data without crowding the header.
  * Reduced avatar/back-button footprint and aligned badges/assignment controls on one line; the assignment dropdown is now the single source of truth and hides itself when the viewer lacks permission.
  * When assignment is locked, the header shows a read-only pill; when it is unlocked the dropdown handles both the assignment display and editing.
  * The “Details” button now toggles a single profile panel that contains both the prior “View details” content and the conversation metadata, and the chat window reserves space on the right so the panel sits beside (instead of covering) the thread.
  * Narrowed the agent selector width on medium screens and kept the “View details” action intact.
  * After feedback, the handle + last-activity labels now live exclusively inside the info dropdown to keep the header footprint slim.
- `frontend/src/App.css`
  * Sidebar width shrank to 80px with tighter gaps so the chat thread can expand.
  * Inbox grid now favors the conversation column (`minmax(0, 1.3–1.4fr)`), plus light adjustments for large screens.
- `frontend/src/layouts/AppShell.jsx`
  * Navigation items/padding trimmed to match the new sidebar width.
- `frontend/src/components/ChatWindow.js` (chat profile panel)
  * Shares the same compact spacing to align with the main thread.

## Highlights
- The conversation header uses fewer rows, keeping the name, platform badge, status, and assignment actions aligned horizontally.
- Less-critical metadata (full handle, last activity, chat id) moved to the info dropdown to reduce clutter.
- The Inbox grid dedicates a larger portion of the viewport to the conversation thread while the sidebar occupies less width.
- Sidebar links received smaller padding so icons and labels line up without wasting horizontal space.

## Change log
- `frontend/src/components/ChatWindow.js`
- `frontend/src/App.css`
- `frontend/src/layouts/AppShell.jsx`
