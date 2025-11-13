import React from 'react';
import { cn } from '../lib/utils';

const TemplatesLayout = ({ title = 'Templates', description, filters, children, className }) => (
  <section className={cn('px-4 py-6 lg:px-8 flex flex-col gap-6 min-h-0', className)}>
    <div className="flex flex-col gap-2">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--tg-text-primary)]">{title}</h1>
        {description && <p className="text-sm text-[var(--tg-text-muted)]">{description}</p>}
      </div>
      {filters && <div className="flex flex-wrap gap-3">{filters}</div>}
    </div>
    <div className="flex-1 min-h-0 rounded-3xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-4 overflow-hidden">
      {children}
    </div>
  </section>
);

export default TemplatesLayout;
