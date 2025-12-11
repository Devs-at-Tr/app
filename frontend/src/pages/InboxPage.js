import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useWebSocketContext } from '../context/WebSocketContext';
import { useChatContext, ChatProvider } from '../context/ChatContext';
import { API } from '../App';
import AppShell from '../layouts/AppShell';
import InboxLayout from '../layouts/InboxLayout';
import InboxWorkspace from '../layouts/InboxWorkspace';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Sheet, SheetContent } from '../components/ui/sheet';
import { Search, SlidersHorizontal, X, Filter, RefreshCw, Users } from 'lucide-react';
import { useIsMobile } from '../hooks/useMediaQuery';
import { Switch } from '../components/ui/switch';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { buildNavigationItems } from '../utils/navigationConfig';
import { cn } from '../lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../components/ui/select';

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
  const [chatSearchQuery, setChatSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chatFilters, setChatFilters] = useState({
    unseen: false,
    notReplied: false,
    assignedTo: 'all'
  });
  const [mobileView, setMobileView] = useState('list');
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  const canManageIntegrations = useMemo(() => hasPermission(user, 'integration:manage'), [user]);
  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canAssignChats = useMemo(() => hasPermission(user, 'chat:assign'), [user]);
  const canLoadAgentDirectory = useMemo(
    () => hasPermission(user, 'chat:assign') || hasPermission(user, 'position:assign'),
    [user]
  );
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage']),
    [user]
  );
  const canInviteUsers = useMemo(() => hasPermission(user, 'user:invite'), [user]);
  const canViewStats = useMemo(() => hasPermission(user, 'stats:view'), [user]);
  const canViewAllChats = useMemo(
    () => hasAnyPermission(user, ['chat:view:team', 'chat:view:all']),
    [user]
  );
  const showAssignmentInfo = useMemo(
    () => canAssignChats || canViewAllChats,
    [canAssignChats, canViewAllChats]
  );

  const navigationItems = useMemo(
    () =>
      buildNavigationItems({
        canManageTemplates,
        canViewUserRoster,
        canManagePositions,
        canInviteUsers,
        canViewStats,
        canManageIntegrations
      }),
    [canManageTemplates, canViewUserRoster, canManagePositions, canInviteUsers, canViewStats, canManageIntegrations]
  );

  const buildChatFilterParams = useCallback(() => {
    const params = {};
    if (chatFilters.unseen) {
      params.unseen = true;
    }
    if (chatFilters.notReplied) {
      params.not_replied = true;
    }
    if (chatFilters.assignedTo && chatFilters.assignedTo !== 'all') {
      params.assigned_to = chatFilters.assignedTo;
    }
    return params;
  }, [chatFilters]);

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

  const handleFilterToggle = useCallback((key) => {
    setChatFilters((prev) => ({
      ...prev,
      [key]: !prev[key]
    }));
  }, []);

  const handleAssignedFilterChange = useCallback((value) => {
    setChatFilters((prev) => ({
      ...prev,
      assignedTo: value
    }));
  }, []);

  const handleClearFilters = useCallback(() => {
    setChatFilters({
      unseen: false,
      notReplied: false,
      assignedTo: 'all'
    });
  }, []);

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

        const filterParams = buildChatFilterParams();
        const [statsRes, agentsRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, axiosConfig),
          canLoadAgentDirectory ? axios.get(`${API}/users/agents`, axiosConfig) : Promise.resolve({ data: [] })
        ]);

        setStats(statsRes.data);
        setAgents(agentsRes.data);
        await loadChats(platform, filterParams);
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
    [buildChatFilterParams, canLoadAgentDirectory, loadChats, onLogout]
  );

  useEffect(() => {
    setSelectedPlatform(resolvedPlatform);
    loadData(resolvedPlatform);
  }, [resolvedPlatform, loadData]);

  useEffect(() => {
    if (!isMobile) {
      setMobileView('list');
      return;
    }
    if (!selectedChat) {
      setMobileView('list');
    }
  }, [isMobile, selectedChat]);

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
        setMobileView('thread');
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
      await loadChats(selectedPlatform, buildChatFilterParams());
      if (selectedChat?.id === chatId) {
        handleSelectChat(chatId);
      }
    } catch (err) {
      console.error('Error assigning chat:', err);
    }
  };

  const renderFilterChips = () => (
    <div className="flex flex-wrap items-center gap-2">
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
      {isMobile && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setFilterSheetOpen(true)}
          className="rounded-full border-[var(--tg-border-soft)] bg-[var(--tg-surface)] text-[var(--tg-text-primary)] gap-2"
        >
          <SlidersHorizontal className="w-4 h-4" />
          Filters
        </Button>
      )}
    </div>
  );

  const renderToggleChip = (key, label) => (
    <label className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] text-[12px] sm:text-[13px] font-medium text-[var(--tg-text-secondary)]">
      <span>{label}</span>
      <Switch
        checked={chatFilters[key]}
        onCheckedChange={() => handleFilterToggle(key)}
      />
    </label>
  );

  const renderAgentSelect = () =>
    canViewAllChats ? (
      <div className="flex items-center gap-2">
        <Users className="w-4 h-4 text-[var(--tg-text-muted)]" />
        <Select value={chatFilters.assignedTo} onValueChange={handleAssignedFilterChange}>
          <SelectTrigger className="min-w-[150px] sm:min-w-[180px] h-9 bg-[var(--tg-surface)] border-[var(--tg-border-soft)] text-sm rounded-full px-3">
            <SelectValue placeholder="All agents" />
          </SelectTrigger>
          <SelectContent className="bg-[var(--tg-surface)] text-[var(--tg-text-primary)]">
            <SelectItem value="all">All agents</SelectItem>
            <SelectItem value="unassigned">Unassigned</SelectItem>
            {agents.map((agent) => (
              <SelectItem key={agent.id} value={agent.id} disabled={!agent.is_active}>
                {agent.name} {agent.is_active ? '' : '(inactive)'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    ) : null;

  const renderFilters = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0 overflow-hidden">
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar py-1">
            {renderFilterChips()}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-full border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] hover:bg-[var(--tg-surface-muted)]"
            onClick={() => setFiltersExpanded((prev) => !prev)}
            aria-label="Toggle filters"
          >
            <Filter className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-full border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] hover:bg-[var(--tg-surface-muted)]"
            onClick={() => loadData(selectedPlatform)}
            aria-label="Refresh chats"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tg-text-muted)]" />
          <Input
            value={chatSearchQuery}
            onChange={(event) => setChatSearchQuery(event.target.value)}
            placeholder="Search conversations..."
            className="pl-9 inbox-search-input inbox-search-input--compact w-full h-10 text-sm"
          />
        </div>
      </div>

      {filtersExpanded && (
        <div className="flex flex-wrap items-center gap-2">
          {renderToggleChip('unseen', 'Unseen')}
          {renderToggleChip('notReplied', 'Needs reply')}
          {renderAgentSelect()}
        </div>
      )}
    </div>
  );

  const showError = error || chatsError;

  const mobileWorkspace = (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      {mobileView === 'list' ? (
        <div className="rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] flex-1">
          <ChatSidebar
            chats={chats}
            selectedChatId={selectedChat?.id}
            onSelectChat={handleSelectChat}
            selectedPlatform={selectedPlatform}
            loading={chatsLoading}
            hideHeader={false}
            searchQuery={chatSearchQuery}
            onSearchQueryChange={setChatSearchQuery}
            showAssignmentInfo={showAssignmentInfo}
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] flex-1">
          <ChatWindow
            chat={selectedChat}
            onSendMessage={handleSendMessage}
            onAssignChat={handleAssignChat}
            agents={agents}
            userRole={user.role}
            canAssignChats={canAssignChats}
            showAssignmentInfo={showAssignmentInfo}
            currentUser={user}
            onBackToList={() => setMobileView('list')}
          />
        </div>
      )}
    </div>
  );

  const workspace = isMobile ? (
    mobileWorkspace
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
            showAssignmentInfo={showAssignmentInfo}
          />
        }
        conversationColumn={
          <div className="rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] h-full flex flex-1 overflow-hidden">
          <ChatWindow
            chat={selectedChat}
            onSendMessage={handleSendMessage}
            onAssignChat={handleAssignChat}
            agents={agents}
            userRole={user.role}
            canAssignChats={canAssignChats}
            showAssignmentInfo={showAssignmentInfo}
            currentUser={user}
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
            <div className="rounded-2xl border border-red-200/40 bg-red-500/5 px-3 py-3 flex items-center justify-between">
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
            <div className="rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] px-3 py-4 flex items-center justify-center">
              <div className="h-8 w-8 rounded-full border-t-2 border-b-2 border-purple-500 animate-spin" />
            </div>
          ) : null
        }
        filterSection={renderFilters()}
      >
        {workspace}
      </InboxLayout>

      <Sheet open={filterSheetOpen} onOpenChange={setFilterSheetOpen}>
        <SheetContent
          side="bottom"
          className="w-full max-w-full sm:max-w-md mx-auto bg-[var(--tg-surface)] border-t border-[var(--tg-border-soft)] p-6 space-y-5"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide">
              <SlidersHorizontal className="w-4 h-4" />
              Filters
            </div>
            <Button variant="ghost" size="icon" onClick={() => setFilterSheetOpen(false)}>
              <X className="w-4 h-4" />
            </Button>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between px-3 py-2.5 rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)]">
              <span className="text-sm font-medium text-[var(--tg-text-primary)]">Unseen only</span>
              <Switch checked={chatFilters.unseen} onCheckedChange={() => handleFilterToggle('unseen')} />
            </div>
            <div className="flex items-center justify-between px-3 py-2.5 rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)]">
              <span className="text-sm font-medium text-[var(--tg-text-primary)]">Needs reply</span>
              <Switch checked={chatFilters.notReplied} onCheckedChange={() => handleFilterToggle('notReplied')} />
            </div>
            {canViewAllChats && (
              <div className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-[var(--tg-text-muted)]">Assigned to</span>
                <Select value={chatFilters.assignedTo} onValueChange={handleAssignedFilterChange}>
                  <SelectTrigger className="w-full bg-[var(--tg-surface)] border-[var(--tg-border-soft)] text-sm">
                    <SelectValue placeholder="Assigned to" />
                  </SelectTrigger>
                  <SelectContent className="bg-[var(--tg-surface)] text-[var(--tg-text-primary)]">
                    <SelectItem value="all">All agents</SelectItem>
                    <SelectItem value="unassigned">Unassigned</SelectItem>
                    {agents.map((agent) => (
                      <SelectItem key={agent.id} value={agent.id} disabled={!agent.is_active}>
                        {agent.name} {agent.is_active ? '' : '(inactive)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => {
                handleClearFilters();
              }}
            >
              Clear
            </Button>
            <Button className="flex-1" onClick={() => setFilterSheetOpen(false)}>
              Apply
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </AppShell>
  );
};

const InboxPage = ({ user, onLogout }) => (
  <ChatProvider userRole={user.role}>
    <InboxContent user={user} onLogout={onLogout} />
  </ChatProvider>
);

export default InboxPage;
