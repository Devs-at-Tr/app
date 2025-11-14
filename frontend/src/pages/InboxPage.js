import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useWebSocketContext } from '../context/WebSocketContext';
import { useChatContext, ChatProvider } from '../context/ChatContext';
import { API } from '../App';
import AppShell from '../layouts/AppShell';
import InboxLayout from '../layouts/InboxLayout';
import InboxWorkspace from '../layouts/InboxWorkspace';
import StatsCards from '../components/StatsCards';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Sheet, SheetContent } from '../components/ui/sheet';
import { Settings, Instagram, Search } from 'lucide-react';
import { useIsMobile } from '../hooks/useMediaQuery';
import FacebookPageManager from '../components/FacebookPageManager';
import InstagramAccountManager from '../components/InstagramAccountManager';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { buildNavigationItems } from '../utils/navigationConfig';
import { cn } from '../lib/utils';

const SUPPORTED_CHANNELS = ['instagram', 'facebook'];

const InboxContent = ({ user, onLogout }) => {
  const { lastMessage } = useWebSocketContext();
  const {
    chats,
    selectedChat,
    loading: chatsLoading,
    error: chatsError,
    loadChats,
    selectChat,
    sendMessage,
    handleWebSocketMessage
  } = useChatContext();

  const { channel } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const isMobile = useIsMobile();

  const [stats, setStats] = useState(null);
  const [agents, setAgents] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState('all');
  const [showFacebookManager, setShowFacebookManager] = useState(false);
  const [showInstagramManager, setShowInstagramManager] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [chatSearchQuery, setChatSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const canManageIntegrations = useMemo(() => hasPermission(user, 'integration:manage'), [user]);
  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canAssignChats = useMemo(() => hasPermission(user, 'chat:assign'), [user]);
  const canLoadAgentDirectory = useMemo(
    () => hasPermission(user, 'chat:assign') || hasPermission(user, 'position:assign'),
    [user]
  );
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage', 'chat:assign']),
    [user]
  );
  const canInviteUsers = useMemo(() => hasPermission(user, 'user:invite'), [user]);

  const navigationItems = useMemo(
    () =>
      buildNavigationItems({
        canManageTemplates,
        canViewUserRoster,
        canManagePositions,
        canInviteUsers
      }),
    [canManageTemplates, canViewUserRoster, canManagePositions, canInviteUsers]
  );

  const resolvedPlatform = useMemo(() => {
    const normalized = (channel || 'all').toLowerCase();
    return SUPPORTED_CHANNELS.includes(normalized) ? normalized : 'all';
  }, [channel]);

  const messageFilters = useMemo(
    () => [
      { id: 'all', label: 'All messages', metric: stats?.total_chats ?? chats.length },
      { id: 'facebook', label: 'Messenger', metric: stats?.facebook_chats ?? 0 },
      { id: 'instagram', label: 'Instagram', metric: stats?.instagram_chats ?? 0 },
      { id: 'whatsapp', label: 'WhatsApp', metric: stats?.whatsapp_chats ?? 0, disabled: true, badge: 'Soon' }
    ],
    [stats, chats.length]
  );

  useEffect(() => {
    if (lastMessage) {
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage, handleWebSocketMessage]);

  const loadData = useCallback(
    async (platform) => {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }

        const headers = { Authorization: `Bearer ${token}` };
        const timeout = 30000;
        const axiosConfig = { headers, timeout };

        const [statsRes, agentsRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, axiosConfig),
          canLoadAgentDirectory ? axios.get(`${API}/users/agents`, axiosConfig) : Promise.resolve({ data: [] })
        ]);

        setStats(statsRes.data);
        setAgents(agentsRes.data);
        await loadChats(platform);
      } catch (err) {
        console.error('Error loading data:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load data');
        if (err.response?.status === 401) {
          onLogout();
        }
      } finally {
        setLoading(false);
      }
    },
    [canLoadAgentDirectory, loadChats, onLogout]
  );

  useEffect(() => {
    setSelectedPlatform(resolvedPlatform);
    loadData(resolvedPlatform);
  }, [resolvedPlatform, loadData]);

  const handlePlatformChange = useCallback(
    (platform) => {
      if (platform === 'whatsapp') {
        return;
      }
      const path = platform === 'all' ? '/inbox' : `/inbox/${platform}`;
      if (path !== location.pathname && platform !== selectedPlatform) {
        navigate(path);
      }
    },
    [navigate, location.pathname, selectedPlatform]
  );

  const handleSelectChat = async (chatId) => {
    try {
      await selectChat(chatId);
      if (isMobile) {
        setMobileSidebarOpen(false);
      }
    } catch (err) {
      console.error('Error selecting chat:', err);
    }
  };

  const handleSendMessage = async (chatId, content) => {
    try {
      await sendMessage(chatId, content);
    } catch (err) {
      console.error('Error sending message:', err);
    }
  };

  const handleAssignChat = async (chatId, agentId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/chats/${chatId}/assign`,
        { agent_id: agentId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      await loadChats(selectedPlatform);
      if (selectedChat?.id === chatId) {
        handleSelectChat(chatId);
      }
    } catch (err) {
      console.error('Error assigning chat:', err);
    }
  };

  const renderFilterChips = () => (
    <div className="flex flex-wrap gap-2">
      {messageFilters.map((filter) => {
        const isSelected = selectedPlatform === filter.id;
        return (
          <button
            key={filter.id}
            type="button"
            disabled={filter.disabled}
            onClick={() => handlePlatformChange(filter.id)}
            className={cn(
              'inbox-filter-pill',
              filter.disabled && 'inbox-filter-pill--disabled',
              isSelected && 'inbox-filter-pill--active'
            )}
          >
            <span>{filter.label}</span>
            {typeof filter.metric === 'number' && (
              <span className="inbox-filter-pill__metric">{filter.metric}</span>
            )}
            {filter.badge && <span className="inbox-filter-pill__badge">{filter.badge}</span>}
          </button>
        );
      })}
    </div>
  );

  const renderFilters = () => (
    <div className="space-y-4">
      {renderFilterChips()}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px] sm:max-w-sm lg:max-w-lg">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tg-text-muted)]" />
          <Input
            value={chatSearchQuery}
            onChange={(event) => setChatSearchQuery(event.target.value)}
            placeholder="Search conversations, people, or labels"
            className="pl-9 inbox-search-input inbox-search-input--compact w-full"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isMobile && (
            <Button
              variant="ghost"
              className="inbox-action-btn"
              onClick={() => setMobileSidebarOpen(true)}
            >
              Open chats
            </Button>
          )}
          <Button
            variant="outline"
            className="inbox-action-btn"
            onClick={() => loadData(selectedPlatform)}
          >
            Refresh
          </Button>
          {canManageIntegrations && (
            <>
              <Button
                onClick={() => setShowInstagramManager(true)}
                variant="ghost"
                className="inbox-action-btn"
              >
                <Instagram className="w-4 h-4 mr-2" />
                Manage Instagram
              </Button>
              <Button
                onClick={() => setShowFacebookManager(true)}
                variant="ghost"
                className="inbox-action-btn"
              >
                <Settings className="w-4 h-4 mr-2" />
                Manage Facebook
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );

  const showError = error || chatsError;

  const workspace = isMobile ? (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
        <SheetContent
          side="left"
          className="p-0 w-[88vw] sm:w-[420px] bg-[var(--tg-surface)] border-[var(--tg-border-soft)]"
        >
          <div className="h-full flex flex-col">
            <div className="px-4 py-3 border-b border-[var(--tg-border-soft)] flex items-center justify-between">
              <p className="text-base font-semibold">Inbox</p>
              <Button size="sm" variant="ghost" onClick={() => setMobileSidebarOpen(false)}>
                Close
              </Button>
            </div>
            <div className="flex-1 overflow-hidden">
              <ChatSidebar
                chats={chats}
                selectedChatId={selectedChat?.id}
                onSelectChat={(chatId) => {
                  handleSelectChat(chatId);
                  setMobileSidebarOpen(false);
                }}
                selectedPlatform={selectedPlatform}
                loading={chatsLoading}
                hideHeader
                searchQuery={chatSearchQuery}
                onSearchQueryChange={setChatSearchQuery}
              />
            </div>
          </div>
        </SheetContent>
      </Sheet>
      <div className="flex-1 min-h-0 rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)]">
        <ChatWindow
          chat={selectedChat}
          onSendMessage={handleSendMessage}
          onAssignChat={handleAssignChat}
          agents={agents}
          userRole={user.role}
          canAssignChats={canAssignChats}
        />
      </div>
    </div>
  ) : (
    <InboxWorkspace
      className="flex-1 min-h-0"
      listColumn={
        <ChatSidebar
          chats={chats}
          selectedChatId={selectedChat?.id}
          onSelectChat={handleSelectChat}
          selectedPlatform={selectedPlatform}
          loading={chatsLoading}
          hideHeader
          searchQuery={chatSearchQuery}
          onSearchQueryChange={setChatSearchQuery}
        />
      }
      conversationColumn={
        <div className="rounded-3xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] h-full flex flex-1">
          <ChatWindow
            chat={selectedChat}
            onSendMessage={handleSendMessage}
            onAssignChat={handleAssignChat}
            agents={agents}
            userRole={user.role}
            canAssignChats={canAssignChats}
          />
        </div>
      }
    />
  );

  return (
    <AppShell user={user} navItems={navigationItems} onLogout={onLogout}>
      <InboxLayout
        statsSection={
          showError ? (
            <div className="rounded-2xl border border-red-200/40 bg-red-500/5 px-4 py-3 flex items-center justify-between">
              <span className="text-sm text-red-200">{showError}</span>
              <button
                onClick={() => {
                  setError(null);
                  loadData(selectedPlatform);
                }}
                className="text-sm font-semibold text-[var(--tg-accent-strong)] hover:underline"
              >
                Retry
              </button>
            </div>
          ) : loading && !stats ? (
            <div className="rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] px-4 py-6 flex items-center justify-center">
              <div className="h-8 w-8 rounded-full border-t-2 border-b-2 border-purple-500 animate-spin" />
            </div>
          ) : (
            <StatsCards stats={stats} />
          )
        }
        filterSection={renderFilters()}
      >
        {workspace}
      </InboxLayout>

      {showInstagramManager && (
        <InstagramAccountManager onClose={() => setShowInstagramManager(false)} />
      )}

      {showFacebookManager && (
        <FacebookPageManager onClose={() => setShowFacebookManager(false)} />
      )}
    </AppShell>
  );
};

const InboxPage = ({ user, onLogout }) => (
  <ChatProvider userRole={user.role}>
    <InboxContent user={user} onLogout={onLogout} />
  </ChatProvider>
);

export default InboxPage;
