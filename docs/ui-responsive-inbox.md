# Responsive Inbox & Navigation Updates

## Layout breakpoints
- **≥ 1280px** – grid expands to three columns (conversation list, thread, optional profile/details). Details rail renders only on very wide screens to avoid squashing the thread.
- **768px–1279px** – inbox workspace renders as two flexible columns (list + thread) with no fixed widths that exceed the viewport, eliminating horizontal scroll.
- **< 768px** – the workspace shows either the conversation list or the active thread. Selecting a chat switches to the thread view, and a “Back to list” action is available in the thread header. All major panels enforce `w-full`/`max-w-full` so the viewport never scrolls sideways.

## Filter experience
- Primary channel filters remain pills in a single wrapping row. On mobile, an additional `Filters` pill (with sliders icon) opens a dedicated sheet.
- Desktop keeps toggles for “Unseen only” and “Needs reply” plus an “Assigned to” selector inline under the chips/search row.
- Mobile sheet aggregates the toggles and assignment selector with Apply/Clear actions so the horizontal toolbar stays uncluttered and scroll-free.

## Sidebar vs. burger icon
- At widths **≥ 1024px** the sidebar stays mounted (collapsed with hover/flyout) and the burger icon is hidden.
- At **< 1024px** the sidebar is fully hidden and only the burger icon appears in the top bar. Tapping it opens the same navigation inside a slide-in drawer.

## Manage connected pages
- A global “Manage connected pages” nav item now lives alongside the rest of the AppShell navigation (desktop sidebar + mobile drawer).
- The item expands into a dropdown listing “Manage Instagram” and “Manage Facebook”, both of which open the existing management modals directly from anywhere in the app.
