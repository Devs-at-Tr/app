import React from 'react';
import { cn } from '../lib/utils';

/**
 * TickleGram layout hierarchy
 * ---------------------------
 * - src/App.js bootstraps ThemeProvider/WebSocketProvider, then renders AppShell for every route.
 * - AppShell owns the persistent sidebar + top mobile bar.
 * - InboxLayout (this file) renders the inbox-only chrome: stats cards, channel filters,
 *   search/actions bar, and the viewport-height workspace that receives the chat list + conversation.
 * - InboxWorkspace (layouts/InboxWorkspace.jsx) is responsible for the scrolling columns inside the
 *   workspace (chat list + conversation + optional info panel).
 * - Templates, Comments, and Admin modules use their own layouts so they never inherit inbox chrome.
 */
const InboxLayout = ({
  className,
  statsSection,
  filterSection,
  children,
}) => (
  <section className={cn('dashboard-page px-2.5 py-3 sm:px-3 lg:px-4 h-full min-h-0 flex-1', className)}>
    <div className="dashboard-header sticky top-0 z-20">
      {statsSection}
      {filterSection}
    </div>
    <div className="dashboard-main flex-1 min-h-0 overflow-hidden">
      <div className="flex-1 min-h-0 w-full h-full">
        {children}
      </div>
    </div>
  </section>
);

export default InboxLayout;
