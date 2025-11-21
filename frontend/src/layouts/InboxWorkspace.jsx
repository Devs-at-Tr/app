import React from 'react';
import { cn } from '../lib/utils';

const InboxWorkspace = ({ filterBar, listColumn, conversationColumn, infoColumn, className }) => {
  return (
    <section className={cn('inbox-layout flex flex-col gap-2.5 min-h-0 h-full', className)}>
      {filterBar && <div className="inbox-layout__filters">{filterBar}</div>}
      <div
        className={cn(
          'inbox-layout__columns flex flex-1 min-h-0',
          infoColumn ? 'inbox-layout__columns--has-details' : 'inbox-layout__columns--no-details'
        )}
      >
        <div className="inbox-layout__list flex flex-col h-full min-h-0">
          {listColumn}
        </div>
        <div className="inbox-layout__conversation min-h-0 flex flex-col">
          {conversationColumn}
        </div>
        {infoColumn && (
          <div className="inbox-layout__details hidden 2xl:flex 2xl:flex-col">
            {infoColumn}
          </div>
        )}
      </div>
    </section>
  );
};

export default InboxWorkspace;
