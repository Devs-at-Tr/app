# UI Refactor – Module Layouts

## App shell
- `src/layouts/AppShell.jsx` wraps all authenticated routes (mounted in `src/App.js`). It owns the hover-collapsible sidebar, the mobile header, and theme toggling while keeping the viewport locked to `100vh`.
- Sidebar behaviour: icon rail by default, expands smoothly on hover (desktop) or via the mobile sheet. Each item is a `NavLink` (no local state routing), and redundant in-page navigation buttons were removed.
- AppShell simply provides the chrome; each route renders its module-specific layout (Inbox, Templates, Comments, Admin) inside `{children}`.

## Layouts per module

| Layout | File | Used by | Notes |
| --- | --- | --- | --- |
| **InboxLayout** | `src/layouts/InboxLayout.jsx` | `/inbox`, `/inbox/:channel?` | Owns inbox-only chrome: stats cards (`StatsCards`), channel filter pills, search + actions. Receives the workspace (chat list + conversation) as children via `InboxWorkspace`. |
| **InboxWorkspace** | `src/layouts/InboxWorkspace.jsx` | Nested inside InboxLayout | Handles the three-column inbox grid (chat list, conversation panel, optional info panel). Only the chat list and conversation columns scroll; the stats/header stay fixed. |
| **TemplatesLayout** | `src/layouts/TemplatesLayout.jsx` | `/templates` | Presents a simple title/description block and a raised surface for the templates table. No inbox stats, tabs, or search bar leak into this module. |
| **CommentsLayout** | `src/layouts/CommentsLayout.jsx` | `/comments` | Provides the Meta-style comments experience: a scoped tab strip for channels and a 3-column flex area (posts list, comment thread, post preview). Each column uses its own scroll container so the page shell stays fixed. The middle column repeats the selected post caption at the top before rendering all comments/replies. |
| **AdminLayout** | `src/layouts/AdminLayout.jsx` | `/user-directory`, `/positions` | Generic admin surface (title + optional actions) used by configuration modules. Keeps admin screens consistent without any inbox UI. |

### Where stats & tabs live
- Stats cards (TOTAL CHATS, ASSIGNED CHATS, UNASSIGNED CHATS, ACTIVE AGENTS) render **only** inside `InboxLayout` (the inbox/direct-messages route). They no longer appear on templates, comments, user directory, or positions pages.
- Channel filter tabs/pills also live exclusively inside InboxLayout. The comments module has its own scoped channel tabs rendered by CommentsLayout; the other modules have their own filter controls.

### Scrolling behavior & column rules
- **Inbox:** The page itself is fixed height. Inside `InboxWorkspace`, the chat list (`.inbox-layout__list`) stays at ~320px while the conversation column (`.inbox-layout__conversation`) flexes to fill the remaining width (no hard max-width). Only the chat list and the conversation body (`.conversation-body`) scroll; stats cards, filters, and the composer stay fixed. Chat bubbles (`.conversation-panel`) inherit the full width so there’s no wasted right-side padding.
- **Comments:** `CommentsLayout` pins the channel bar to the top and uses `.comments-columns` with `height: calc(100vh - header)` so each column (posts list, comments thread, preview) scrolls independently. The thread column prints the selected post/comment context at the top, then renders the entire comment/reply list with inline actions (“Reply”, “Message”) and a fixed composer at the bottom—mirroring Meta’s behaviour for posts with hundreds of comments.
- **Templates/Admin:** These layouts use standard flex containers with `min-h-0` so their primary tables/cards scroll within the raised surface instead of the whole page.

### CSS helpers
- `.app-shell` / `.app-shell__content` lock the authenticated experience to the viewport and prevent accidental page scroll.
- `.dashboard-page`, `.dashboard-header`, and `.dashboard-main` split vertical space so sections such as stats cards + filters remain visible while the workspace flexes.
- `.chat-scroll` (shared by chat lists and comment columns) sets consistent thin-scrollbar behaviour across modules.

## Files created
- `src/layouts/InboxLayout.jsx`
- `src/layouts/InboxWorkspace.jsx`
- `src/layouts/TemplatesLayout.jsx`
- `src/layouts/CommentsLayout.jsx`
- `src/layouts/AdminLayout.jsx`
- `src/pages/InboxPage.js`
- `src/pages/TemplatesPage.js`
- `src/pages/CommentsPage.js`
- `docs/UI-Refactor-Modules.md`

## Files significantly modified
- `src/App.js`
- `src/layouts/AppShell.jsx`
- `src/components/SocialComments.js`
- `src/components/ChatWindow.js`
- `src/components/ChatSidebar.js`
- `src/components/UserRosterCard.jsx`
- `src/components/PositionManager.jsx`
- `src/pages/UserDirectoryPage.jsx`
- `src/pages/PositionsPage.jsx`
- `src/utils/navigationConfig.js`
- `src/App.css`

## Changelog (UI only)
- Split the monolithic dashboard into dedicated routes/layouts: inbox (with stats), templates, comments, and admin pages now render only their own UI.
- Redesigned the Comments & Reviews module using the Meta-inspired 3-column layout (posts list, thread, post preview) with scoped channel tabs.
- Sidebar now navigates between routes (NavLink based) and no longer triggers modal views; user directory and positions live on full pages via AdminLayout.
- Cleaned up imports and styles after the refactor (new layout components, removed unused tabs/actions on non-inbox pages, consistent theme tokens for every module).
- Inbox conversation column now stretches to the full remaining width while keeping only the chat list + message list scrollable; composer sits fixed along the full width.
- Comments threads show the selected post caption/media at the top of the middle column and display every comment/reply in a scrollable list with inline actions, mirroring how Meta handles “single post with many comments.”
