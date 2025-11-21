# Inbox layout (WhatsApp-inspired)

## Structure
- Two-column desktop layout: left chat list is constrained to ~30% of the viewport (min 320–340px, max ~420px) and scrolls independently; right pane flexes to fill remaining space.
- Conversation header is a single compact row: avatar + name/handle + platform pill on the left; assignment control + details button on the right.
- Message thread uses `flex-1` + `overflow-y-auto` between header and composer; bubbles stretch up to ~76% width for readability.
- Composer sticks to the bottom of the conversation panel with tight padding; mobile keeps the back-to-list button.

## Profile overlay
- Profile/details panel now behaves like a drawer that slides over the chat window from the right, with a dimmed backdrop and click-outside-to-close.
- Width is capped around 25–30% of the viewport (max ~420px); on mobile, the profile content renders inline below the thread instead of overlaying.
- Internal spacing is denser: grid for metadata, compact header, and smaller card for the last message.

## Filters and top bar
- Filter chips are compact pills that wrap naturally; on desktop the “Unseen”, “Needs reply”, and “Assigned to” controls sit on the same row as the platform chips where space allows.
- Search + refresh row below stays narrow (`h-9` inputs/buttons). On mobile, filters remain accessible via the bottom sheet with reduced padding.
- Analytics banner/error/info blocks use slimmer padding to avoid pushing the thread down.

## Responsiveness
- ≥1024px: two-column layout maintained with no horizontal scroll; conversation column keeps `overflow-hidden` so overlays do not shrink it.
- <1024px: existing mobile split-view persists (list vs thread view with back button). Filter chips wrap and the nav sidebar collapses per AppShell behavior.
- Width constraints come from `InboxWorkspace` CSS variables (`inbox-layout__list` flex-basis) so the list stays compact on 1366×768/1440×900 screens.

## Extension/migration notes
- Header tweaks: update `src/components/ChatWindow.js` for new fields (name/handle/assignment/details live here). Keep paddings slim and reuse `assignment-pill--compact`.
- Chat list density: `src/components/ChatSidebar.js` handles list item contents; widths are controlled by `InboxWorkspace` and styles in `src/App.css`/`ChatWindow.css`.
- Profile overlay: drawer/backdrop lives in `ChatWindow.js` with global styles in `src/App.css`. If you add more sections, keep them within the existing grid to preserve height.
- Layout shell: column sizing and padding live in `src/layouts/InboxLayout.jsx`, `src/layouts/InboxWorkspace.jsx`, and `src/App.css` (inbox layout rules). Adjust there when changing overall proportions.
