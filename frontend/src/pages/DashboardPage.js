import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { useWebSocketContext } from '../context/WebSocketContext';
import { useChatContext, ChatProvider } from '../context/ChatContext';
import { API } from '../App';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import Header from '../components/Header';
import StatsCards from '../components/StatsCards';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';
import PlatformSelector from '../components/PlatformSelector';
import SocialComments from '../components/SocialComments';
import FacebookPageManager from '../components/FacebookPageManager';
import InstagramAccountManager from '../components/InstagramAccountManager';
import TemplateManager from '../components/TemplateManager';
import { Button } from '../components/ui/button';
import { Sheet, SheetContent } from '../components/ui/sheet';
import { Settings, Instagram, Shield } from 'lucide-react';
import { useIsMobile } from '../hooks/useMediaQuery';
import PositionManager from '../components/PositionManager';
import UserRosterModal from '../components/UserRosterModal';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';

const DashboardContent = ({ user, onLogout }) => {
  const { ws, lastMessage } = useWebSocketContext();
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

  const [stats, setStats] = useState(null);
  const [agents, setAgents] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState('all');
  const [showFacebookManager, setShowFacebookManager] = useState(false);
  const [showInstagramManager, setShowInstagramManager] = useState(false);
  const [userRoster, setUserRoster] = useState([]);
  const [userRosterLoading, setUserRosterLoading] = useState(false);
  const [rosterPositions, setRosterPositions] = useState([]);
  const [rosterPositionsLoading, setRosterPositionsLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [showPositionManager, setShowPositionManager] = useState(false);
  const [showUserRosterModal, setShowUserRosterModal] = useState(false);
  const isMobile = useIsMobile();
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
  const canAssignPositions = useMemo(() => hasPermission(user, 'position:assign'), [user]);
  const assignableAgents = useMemo(
    () =>
      agents.filter((agent) => {
        const slug = agent.position?.slug;
        if (!slug) {
          return true;
        }
        return slug === 'agent-messaging';
      }),
    [agents]
  );

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage, handleWebSocketMessage]);

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        await Promise.all([
          loadData(),
          loadChats(selectedPlatform)
        ]);
      } catch (error) {
        console.error('Error loading initial data:', error);
      }
    };
    loadInitialData();
  }, [canLoadAgentDirectory, canViewUserRoster]);

  const loadUserRoster = useCallback(async () => {
    if (!canViewUserRoster) {
      return;
    }
    setUserRosterLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      const response = await axios.get(`${API}/users/roster`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 30000
      });
      setUserRoster(response.data || []);
    } catch (error) {
      console.error('Error loading user roster:', error);
    } finally {
      setUserRosterLoading(false);
    }
  }, [canViewUserRoster]);

  const loadData = async (platform = selectedPlatform) => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      
      const headers = { Authorization: `Bearer ${token}` };
      const timeout = 30000; // 30 second timeout
      const axiosConfig = { headers, timeout };

      // Build query params for platform filtering
      const chatParams = platform !== 'all' ? { platform } : {};

      // Get stats and agents data
      const [statsRes, agentsRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats`, axiosConfig),
        canLoadAgentDirectory
          ? axios.get(`${API}/users/agents`, axiosConfig)
          : Promise.resolve({ data: [] })
      ]);

      setStats(statsRes.data);
      setAgents(agentsRes.data);

      await loadUserRoster();

      // Load chats using the context
      await loadChats(platform);
    } catch (error) {
      console.error('Error loading data:', error);
      setError(error.response?.data?.detail || error.message || 'Failed to load data');
      // If token is invalid, trigger logout
      if (error.response?.status === 401) {
        onLogout();
      }
    } finally {
      setLoading(false);
    }
  };

  const loadRosterPositions = useCallback(async () => {
    if (!canAssignPositions) {
      setRosterPositions([]);
      return;
    }
    setRosterPositionsLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      const response = await axios.get(`${API}/positions`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 30000
      });
      setRosterPositions(response.data || []);
    } catch (error) {
      console.error('Error loading positions:', error);
    } finally {
      setRosterPositionsLoading(false);
    }
  }, [canAssignPositions]);

  const handlePlatformChange = async (platform) => {
    setSelectedPlatform(platform);
    try {
      // Only reload chats when platform changes, not stats/agents
      await loadChats(platform);
    } catch (error) {
      console.error('Error changing platform:', error);
    }
  };

  const handleSelectChat = async (chatId) => {
    try {
      await selectChat(chatId);
      // Close mobile sidebar when chat is selected
      if (isMobile) {
        setMobileSidebarOpen(false);
      }
    } catch (error) {
      console.error('Error selecting chat:', error);
    }
  };

  const handleSendMessage = async (chatId, content) => {
    try {
      await sendMessage(chatId, content);
    } catch (error) {
      console.error('Error sending message:', error);
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
      // Only reload chats, not the entire page
      await loadChats(selectedPlatform);
      if (selectedChat?.id === chatId) {
        handleSelectChat(chatId);
      }
    } catch (error) {
      console.error('Error assigning chat:', error);
    }
  };

  const handleAssignPosition = async (userId, positionId) => {
    if (!canAssignPositions) {
      return;
    }
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      await axios.post(
        `${API}/users/${userId}/position`,
        { position_id: positionId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      await loadUserRoster();
    } catch (error) {
      console.error('Error assigning position:', error);
    }
  };

  useEffect(() => {
    if (showUserRosterModal && canAssignPositions) {
      loadRosterPositions();
    }
  }, [showUserRosterModal, canAssignPositions, loadRosterPositions]);

  useEffect(() => {
    if (canViewUserRoster) {
      loadUserRoster();
    } else {
      setUserRoster([]);
    }
  }, [canViewUserRoster, loadUserRoster]);

  // Only show initial loading screen, not on subsequent updates
  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-[#0f0f1a] flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500 mb-4"></div>
      </div>
    );
  }

  // Show error as a toast/banner instead of blocking the entire page
  const showError = error || chatsError;

  return (
    <div className="min-h-screen bg-[#0f0f1a]" data-testid="dashboard-page">
      <Header 
        user={user} 
        onLogout={onLogout}
        onMenuClick={() => setMobileSidebarOpen(true)}
      />
      
      {/* Error Banner */}
      {showError && (
        <div className="mx-3 mt-3 p-3 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center justify-between">
          <span className="text-red-400 text-sm">{showError}</span>
          <button 
            onClick={() => {
              setError(null);
              loadData();
            }} 
            className="text-purple-400 hover:text-purple-300 text-sm font-semibold"
          >
            Retry
          </button>
        </div>
      )}
      
      <div className="p-3 space-y-3">
        <StatsCards stats={stats} />

        <Tabs defaultValue="chats" className="w-full">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
            <div className="flex flex-wrap items-center gap-2">
              <PlatformSelector
                selectedPlatform={selectedPlatform}
                onPlatformChange={handlePlatformChange}
              />
              <TabsList className="tg-pill-group flex items-center gap-2">
                <TabsTrigger
                  value="chats"
                  className="tg-tab-trigger px-4 py-1.5 text-sm"
                >
                  Direct Messages
                </TabsTrigger>
                <TabsTrigger
                  value="comments"
                  className="tg-tab-trigger px-4 py-1.5 text-sm"
                >
                  Comments
                </TabsTrigger>
                {canManageTemplates && (
                  <TabsTrigger
                    value="templates"
                    className="tg-tab-trigger px-4 py-1.5 text-sm"
                  >
                    Templates
                  </TabsTrigger>
                )}
              </TabsList>
            </div>

            {(canManageIntegrations || canManagePositions || canViewUserRoster) && (
              <div className="flex items-center space-x-2">
                {canViewUserRoster && (
                  <Button
                    onClick={() => setShowUserRosterModal(true)}
                    variant="ghost"
                    className="manage-btn manage-btn--roles"
                  >
                    User Directory
                  </Button>
                )}
                {canManageIntegrations && (
                  <>
                    <Button
                      onClick={() => setShowInstagramManager(true)}
                      variant="ghost"
                      className="manage-btn manage-btn--ig"
                      data-testid="manage-instagram-accounts-button"
                    >
                      <Instagram className="w-4 h-4 mr-2" />
                      Manage Instagram
                    </Button>
                    <Button
                      onClick={() => setShowFacebookManager(true)}
                      variant="ghost"
                      className="manage-btn manage-btn--fb"
                      data-testid="manage-facebook-pages-button"
                    >
                      <Settings className="w-4 h-4 mr-2" />
                      Manage Facebook
                    </Button>
                  </>
                )}
                {canManagePositions && (
                  <Button
                    onClick={() => setShowPositionManager(true)}
                    variant="ghost"
                    className="manage-btn manage-btn--roles"
                  >
                    <Shield className="w-4 h-4 mr-2" />
                    Manage Positions
                  </Button>
                )}
              </div>
            )}
          </div>

          <TabsContent value="chats">
            {/* Mobile Layout */}
            {isMobile ? (
              <div className="h-[calc(100vh-280px)]">
                {/* Mobile Sidebar Drawer */}
                <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
                  <SheetContent side="left" className="bg-[#1a1a2e] border-gray-700 p-0 w-[85vw] sm:w-[400px]">
                    <div className="h-full flex flex-col">
                      <div className="p-4 border-b border-gray-700">
                        <h3 className="text-lg font-semibold text-white">Chats</h3>
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <ChatSidebar
                          chats={chats}
                          selectedChatId={selectedChat?.id}
                          onSelectChat={handleSelectChat}
                          onRefresh={loadData}
                          selectedPlatform={selectedPlatform}
                          loading={chatsLoading}
                        />
                      </div>
                    </div>
                  </SheetContent>
                </Sheet>

                {/* Mobile Chat Window - Full Screen */}
                <div className="h-full">
                  <ChatWindow
                    chat={selectedChat}
                    onSendMessage={handleSendMessage}
                    onAssignChat={handleAssignChat}
                    agents={assignableAgents}
                    userRole={user.role}
                    canAssignChats={canAssignChats}
                  />
                </div>
              </div>
            ) : (
              /* Desktop Layout */
              <div className="grid grid-cols-12 gap-6 h-[calc(100vh-360px)]">
                <div className="col-span-4 lg:col-span-3 h-full min-h-0 flex flex-col">
                  <ChatSidebar
                    chats={chats}
                    selectedChatId={selectedChat?.id}
                    onSelectChat={handleSelectChat}
                    onRefresh={loadData}
                    selectedPlatform={selectedPlatform}
                    loading={chatsLoading}
                  />
                </div>
                
                <div className="col-span-8 lg:col-span-9 h-full min-h-0 flex">
                  <ChatWindow
                    chat={selectedChat}
                    onSendMessage={handleSendMessage}
                    onAssignChat={handleAssignChat}
                    agents={assignableAgents}
                    userRole={user.role}
                    canAssignChats={canAssignChats}
                  />
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="comments">
            <div className="h-[calc(100vh-380px)] overflow-hidden">
              <SocialComments selectedPlatform={selectedPlatform === 'all' ? 'all' : selectedPlatform} />
            </div>
          </TabsContent>

          {canManageTemplates && (
            <TabsContent value="templates">
              <div className="h-[calc(100vh-380px)] overflow-y-auto">
                <TemplateManager />
              </div>
            </TabsContent>
          )}
        </Tabs>
      </div>

      {/* Instagram Account Manager Modal */}
      {showInstagramManager && (
        <InstagramAccountManager onClose={() => setShowInstagramManager(false)} />
      )}

      {/* Facebook Page Manager Modal */}
      {showFacebookManager && (
        <FacebookPageManager onClose={() => setShowFacebookManager(false)} />
      )}

      <PositionManager open={showPositionManager} onClose={() => setShowPositionManager(false)} />
      {canViewUserRoster && (
        <UserRosterModal
          open={showUserRosterModal}
          onClose={() => setShowUserRosterModal(false)}
          users={userRoster}
          loading={userRosterLoading}
          currentUserId={user.id}
          positions={rosterPositions}
          positionsLoading={rosterPositionsLoading}
          canManagePositions={canManagePositions}
          canAssignPositions={canAssignPositions}
          onManagePositions={() => {
            setShowUserRosterModal(false);
            setShowPositionManager(true);
          }}
          onAssignPosition={handleAssignPosition}
        />
      )}
    </div>
  );
};

const DashboardPage = ({ user, onLogout }) => (
  <ChatProvider userRole={user.role}>
    <DashboardContent user={user} onLogout={onLogout} />
  </ChatProvider>
);

export default DashboardPage;
