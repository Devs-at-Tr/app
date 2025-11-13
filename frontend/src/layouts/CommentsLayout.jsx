import React from 'react';
import { cn } from '../lib/utils';

const CommentsLayout = ({
  tabs,
  activeTab,
  onTabChange,
  postsColumn,
  threadColumn,
  previewColumn,
  className,
}) => (
  <section className={cn('px-4 py-6 lg:px-8 flex flex-col gap-4 min-h-0', className)}>
    <div className="flex flex-wrap items-center gap-2 border-b border-[var(--tg-border-soft)] pb-3">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          disabled={tab.disabled}
          onClick={() => onTabChange(tab.id)}
          className={cn(
            'comments-tab',
            activeTab === tab.id && 'comments-tab--active',
            tab.disabled && 'comments-tab--disabled'
          )}
        >
          {tab.icon && <tab.icon className="w-4 h-4" />}
          <span>{tab.label}</span>
          {typeof tab.badge === 'number' && <span className="comments-tab__badge">{tab.badge}</span>}
        </button>
      ))}
    </div>
    <div className="comments-columns flex-1 min-h-0">
      <div className="comments-column">{postsColumn}</div>
      <div className="comments-column comments-column--thread">{threadColumn}</div>
      {previewColumn && (
        <div className="comments-column comments-column--preview">{previewColumn}</div>
      )}
    </div>
  </section>
);

export default CommentsLayout;
