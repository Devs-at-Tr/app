# Inbox Compact Layout Tuning

## Components updated
- `frontend/src/layouts/InboxLayout.jsx` / `InboxWorkspace.jsx`: reduced default padding and column gaps so the inbox chrome wastes less space on all breakpoints.
- `frontend/src/App.css`: tightened the dashboard, filter panel, chat panels, and message areas (smaller padding, lighter shadows, and denser grid gaps).
- `frontend/src/components/ChatSidebar.js`: compact list cards and header by trimming padding and fonts for previews/timestamps.
- `frontend/src/components/ChatWindow.js`: smaller header/composer spacing, optional mobile back button, denser message spacing, and a lighter profile drawer.
- `frontend/src/pages/InboxPage.js`: slimmer filter/search rows and toggle chips.

## Spacing standards
- Default horizontal padding now uses `px-3/px-4` on the layout instead of `px-6/px-8`.
- Column gaps inside the workspace were reduced to `0.75rem`, keeping chat list + thread tight on tablets/desktops.
- Filter shells and action buttons follow compact pills (`padding ≈ 0.35–0.9rem`) to avoid over-sized touch targets on desktop.
- Conversation headers/bodies use `14–18px` padding so more of the message history is visible above the composer.

## Rationale
- Previous paddings (20–24px blocks, tall filter panels) caused excessive empty space, forcing users to scroll sooner—especially on tablets and laptops.
- Aligning spacing with Tailwind’s smaller scales keeps the UI visually consistent without shrinking text sizes.
- Chat list items now surface more rows per viewport while preserving readability (platform icon, preview, assignment, timestamp still visible).
- The optional mobile back button in the thread header supports the single-panel layout without consuming vertical space elsewhere.

## Change log
- `frontend/src/layouts/InboxLayout.jsx`, `frontend/src/layouts/InboxWorkspace.jsx`: reduced wrapper padding/gaps.
- `frontend/src/App.css`: compact dashboard, filter panel, chat panel, and composer metrics.
- `frontend/src/components/ChatSidebar.js`: denser header + list item spacing; updated preview/timestamp styling.
- `frontend/src/components/ChatWindow.js`: condensed header/composer spacing, mobile back CTA, slimmer profile panel/body spacing.
- `frontend/src/pages/InboxPage.js`: tighter filter/search rows and toggle chip padding.
