import React, { useCallback, useMemo, useState } from 'react';
import { Button } from './ui/button';
import { RefreshCw, Search, Instagram } from 'lucide-react';
import { Input } from './ui/input';

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
  selectedPlatform = 'all'
}) => {
  const [searchQuery, setSearchQuery] = useState('');

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
    return platformFiltered.filter(chat =>
      chat.username.toLowerCase().includes(query) ||
      (chat.last_message || '').toLowerCase().includes(query)
    );
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

  return (
    <div className="bg-[#1a1a2e] border border-gray-800 rounded-xl h-full flex flex-col" data-testid="chat-sidebar">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-white">Recent Chats</h2>
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
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500"
            data-testid="search-chats-input"
          />
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto chat-scroll" data-testid="chat-list">
        {filteredChats.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            No chats found
          </div>
        ) : (
          filteredChats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => handleSelect(chat.id)}
              className={`chat-item p-4 border-b border-gray-800 ${
                isSelected(chat.id) ? 'active' : ''
              }`}
              data-testid={`chat-item-${chat.id}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    {getPlatformBadge(chat.platform)}
                    <h3 className="text-white font-semibold truncate">{chat.username}</h3>
                    {chat.status === 'unassigned' && (
                      <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded-full">
                        New
                      </span>
                    )}
                    {chat.unread_count > 0 && (
                      <span className="px-2 py-0.5 bg-purple-500 text-white text-xs rounded-full">
                        {chat.unread_count}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 truncate">{chat.last_message || 'No messages'}</p>
                  {chat.assigned_agent && (
                    <p className="text-xs text-purple-400 mt-1">Assigned: {chat.assigned_agent.name}</p>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;
