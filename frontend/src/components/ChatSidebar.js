import React, { useCallback, useMemo, useState } from 'react';
import { Button } from './ui/button';
import { RefreshCw, Search, Instagram, MoreHorizontal } from 'lucide-react';
import { Input } from './ui/input';
import { formatMessageTime, formatMessageDate } from '../utils/dateUtils';
import { useIsMobile } from '../hooks/useMediaQuery';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from './ui/dropdown-menu';

const getChatHandle = (chat) =>
  chat?.instagram_user?.username ||
  chat?.username ||
  chat?.instagram_user_id ||
  '';

const getChatDisplayName = (chat) =>
  chat?.instagram_user?.name ||
  chat?.instagram_user?.username ||
  chat?.username ||
  'Unknown';

const FacebookIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const ChatSidebar = ({
  chats = [],
  selectedChatId,
  onSelectChat,
  onRefresh,
  selectedPlatform = 'all',
  loading = false,
  hideHeader = false,
  searchQuery: controlledSearch,
  onSearchQueryChange,
}) => {
  const [localSearch, setLocalSearch] = useState('');
  const searchQuery = controlledSearch ?? localSearch;
  const isCompactList = useIsMobile();

  const totalUnread = useMemo(
    () => chats.reduce((count, chat) => count + (chat.unread_count || 0), 0),
    [chats]
  );

  const handleRefresh = useCallback(() => {
    onRefresh?.(selectedPlatform);
  }, [onRefresh, selectedPlatform]);

  const filteredChats = useMemo(() => {
    const platformFiltered =
      selectedPlatform === 'all'
        ? chats
        : chats.filter(chat => chat.platform === selectedPlatform.toUpperCase());

    if (!searchQuery.trim()) {
      return platformFiltered;
    }

    const query = searchQuery.toLowerCase();
    return platformFiltered.filter(chat => {
      const displayName = getChatDisplayName(chat).toLowerCase();
      const handle = getChatHandle(chat).toLowerCase();
      return (
        displayName.includes(query) ||
        handle.includes(query) ||
        (chat.last_message || '').toLowerCase().includes(query)
      );
    });
  }, [chats, selectedPlatform, searchQuery]);

  const handleSelect = (chatId) => {
    onSelectChat?.(chatId);
  };

  const isSelected = (chatId) => selectedChatId === chatId;

  const getPlatformBadge = (platform) => (
    <div className="flex items-center space-x-1">
      {platform === 'FACEBOOK' ? (
        <FacebookIcon className="w-4 h-4 text-blue-500" />
      ) : (
        <Instagram className="w-4 h-4 text-pink-500" />
      )}
    </div>
  );

  const getLastActivityLabel = (chat) => {
    const timestamp = chat?.last_message_timestamp || chat?.updated_at || chat?.created_at;
    if (!timestamp) return '';
    return formatMessageTime(timestamp) || formatMessageDate(timestamp);
  };

  const handleSearchChange = (value) => {
    if (onSearchQueryChange) {
      onSearchQueryChange(value);
    } else {
      setLocalSearch(value);
    }
  };

  return (
    <div className="chat-panel h-full flex flex-col min-h-0" data-testid="chat-sidebar">
      {!hideHeader && (
        <div className="px-3 py-2.5 border-b border-gray-800 sticky top-0 z-10 bg-[var(--tg-surface)]">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-white leading-tight">Recent Chats</h2>
              {totalUnread > 0 && (
                <span className="px-2 py-0.5 bg-purple-500 text-xs font-semibold text-white rounded-full" data-testid="chat-unread-count">
                  {totalUnread}
                </span>
              )}
            </div>
            <Button
              onClick={handleRefresh}
              size="sm"
              variant="outline"
              className="bg-purple-500/10 border-purple-500/50 hover:bg-purple-500/20 text-purple-400"
              data-testid="refresh-chats-button"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10 inbox-search-input inbox-search-input--compact"
              data-testid="search-chats-input"
            />
          </div>
        </div>
      )}
      {/* Chat List */}
      <div className="flex-1 overflow-y-auto chat-scroll min-h-0" data-testid="chat-list">
        {loading ? (
          <div className="p-4 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
            <p className="text-gray-500 text-sm mt-2">Loading chats...</p>
          </div>
        ) : filteredChats.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            No chats found
          </div>
        ) : (
          filteredChats.map((chat) => {
            const displayName = getChatDisplayName(chat);
            const lastActivityLabel = getLastActivityLabel(chat);
            return (
              <div
                key={chat.id}
                onClick={() => handleSelect(chat.id)}
                className={`chat-item px-3 py-2.5 border-b border-gray-800 ${
                  isSelected(chat.id) ? 'active' : ''
                } ${
                  chat.unread_count > 0 && !isSelected(chat.id) ? 'has-unread' : ''
                }`}
              data-testid={`chat-item-${chat.id}`}
            >
              <div className="flex items-start justify-between gap-2 w-full">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    {getPlatformBadge(chat.platform)}
                    <h3 className="text-white font-semibold truncate text-[13px] leading-tight">{displayName}</h3>
                    {chat.unread_count > 0 && (
                      <span className="px-2 py-0.5 bg-purple-500 text-white text-xs font-semibold rounded-full">
                        {chat.unread_count}
                      </span>
                    )}
                  </div>
                  <p className="text-[12px] text-gray-400 truncate leading-snug">{chat.last_message || 'No messages'}</p>
                  {!isCompactList && (
                    <p className="text-[11px] text-purple-400 mt-0.5">
                      {chat.assigned_agent ? `Assigned: ${chat.assigned_agent.name}` : 'Unassigned'}
                    </p>
                  )}
                </div>
                {isCompactList ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-gray-400 hover:text-white flex-shrink-0 h-8 w-8"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      sideOffset={6}
                      className="w-56 bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] text-[var(--tg-text-primary)]"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <DropdownMenuLabel className="text-xs uppercase tracking-wide text-[var(--tg-text-muted)]">
                        Chat details
                      </DropdownMenuLabel>
                      <DropdownMenuSeparator className="bg-[var(--tg-border-soft)]" />
                      <DropdownMenuItem className="flex flex-col items-start gap-0.5 focus:bg-transparent" onSelect={(event) => event.preventDefault()}>
                        <span className="text-sm">
                          {chat.assigned_agent?.name || 'Unassigned'}
                        </span>
                        <span className="text-xs text-[var(--tg-text-muted)]">Assigned agent</span>
                      </DropdownMenuItem>
                      {lastActivityLabel && (
                        <DropdownMenuItem className="flex flex-col items-start gap-0.5 focus:bg-transparent" onSelect={(event) => event.preventDefault()}>
                          <span className="text-sm">{lastActivityLabel}</span>
                          <span className="text-xs text-[var(--tg-text-muted)]">Last activity</span>
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <span className="text-[11px] text-gray-500 whitespace-nowrap">{lastActivityLabel}</span>
                )}
              </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;
