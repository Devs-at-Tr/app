import React from 'react';
import { cn } from '../lib/utils';

const AdminLayout = ({ title, description, actions, children, className }) => (
  <section className={cn('px-4 py-6 lg:px-8 flex flex-col gap-4 min-h-0', className)}>
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--tg-text-primary)]">{title}</h1>
        {description && <p className="text-sm text-[var(--tg-text-muted)]">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
    <div className="flex-1 min-h-0">{children}</div>
  </section>
);

export default AdminLayout;
