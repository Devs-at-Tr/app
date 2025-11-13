import React from 'react';
import { cn } from '../lib/utils';

const InboxWorkspace = ({ filterBar, listColumn, conversationColumn, infoColumn, className }) => {
  return (
    <section className={cn('inbox-layout flex flex-col gap-4 min-h-0', className)}>
      {filterBar && <div className="inbox-layout__filters">{filterBar}</div>}
      <div className="inbox-layout__columns flex-1 min-h-0">
        <div className="inbox-layout__list flex flex-col h-full">
          {listColumn}
        </div>
        <div className="inbox-layout__conversation">
          {conversationColumn}
        </div>
        {infoColumn && (
          <div className="inbox-layout__details hidden 2xl:block w-[320px] flex-shrink-0">
            {infoColumn}
          </div>
        )}
      </div>
    </section>
  );
};

export default InboxWorkspace;
