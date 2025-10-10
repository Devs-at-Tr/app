import React, { useState, useEffect } from 'react';
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
import { Button } from '../components/ui/button';
import { Settings, Instagram } from 'lucide-react';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
  }, []);

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
        user.role === 'admin' 
          ? axios.get(`${API}/users/agents`, axiosConfig)
          : Promise.resolve({ data: [] })
      ]);

      setStats(statsRes.data);
      setAgents(agentsRes.data);

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

  const handlePlatformChange = async (platform) => {
    setSelectedPlatform(platform);
    try {
      await Promise.all([
        loadData(platform),
        loadChats(platform)
      ]);
    } catch (error) {
      console.error('Error changing platform:', error);
    }
  };

  const handleSelectChat = async (chatId) => {
    try {
      await selectChat(chatId);
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
      loadData();
      if (selectedChat?.id === chatId) {
        handleSelectChat(chatId);
      }
    } catch (error) {
      console.error('Error assigning chat:', error);
    }
  };

  if (loading || chatsLoading || error || chatsError) {
    return (
      <div className="min-h-screen bg-[#0f0f1a] flex flex-col items-center justify-center">
        {(loading || chatsLoading) && (
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500 mb-4"></div>
        )}
        {(error || chatsError) && (
          <div className="text-red-500 bg-red-500/10 px-4 py-2 rounded-md">
            {error || chatsError}
            <button 
              onClick={() => loadData()} 
              className="ml-4 text-purple-400 hover:text-purple-300"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f1a]" data-testid="dashboard-page">
      <Header user={user} onLogout={onLogout} />
      
      <div className="p-3 space-y-3">
        <StatsCards stats={stats} />
        
        <Tabs defaultValue="chats" className="w-full">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
            <div className="flex flex-wrap items-center gap-2">
              <PlatformSelector
                selectedPlatform={selectedPlatform}
                onPlatformChange={handlePlatformChange}
              />
              <TabsList className="bg-[#1a1a2e] border border-gray-800 px-1 py-1 gap-1 justify-start">
                <TabsTrigger value="chats" className="px-4 py-1.5 text-sm">Direct Messages</TabsTrigger>
                <TabsTrigger value="comments" className="px-4 py-1.5 text-sm">Comments</TabsTrigger>
              </TabsList>
            </div>

            {user.role === 'admin' && (
              <div className="flex items-center space-x-1">
                <Button
                  onClick={() => setShowInstagramManager(true)}
                  variant="outline"
                  className="bg-[#1a1a2e] border-gray-800 text-pink-400 hover:text-pink-300 hover:bg-pink-500/10"
                  data-testid="manage-instagram-accounts-button"
                >
                  <Instagram className="w-4 h-4 mr-2" />
                  Manage Instagram
                </Button>
                <Button
                  onClick={() => setShowFacebookManager(true)}
                  variant="outline"
                  className="bg-[#1a1a2e] border-gray-800 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                  data-testid="manage-facebook-pages-button"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Manage Facebook
                </Button>
              </div>
            )}
          </div>

          <TabsContent value="chats">
            <div className="grid grid-cols-12 gap-6 h-[calc(100vh-360px)]">
              <div className="col-span-4 h-full min-h-0 flex flex-col">
                <ChatSidebar
                  chats={chats}
                  selectedChatId={selectedChat?.id}
                  onSelectChat={handleSelectChat}
                  onRefresh={loadData}
                  userRole={user.role}
                />
              </div>
              
              <div className="col-span-8 h-full min-h-0 flex">
                <ChatWindow
                  chat={selectedChat}
                  onSendMessage={handleSendMessage}
                  onAssignChat={handleAssignChat}
                  agents={agents}
                  userRole={user.role}
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="comments">
            <div className="h-[calc(100vh-380px)] overflow-y-auto">
              <SocialComments selectedPlatform={selectedPlatform === 'all' ? 'all' : selectedPlatform} />
            </div>
          </TabsContent>
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
    </div>
  );
};

const DashboardPage = ({ user, onLogout }) => (
  <ChatProvider userRole={user.role}>
    <DashboardContent user={user} onLogout={onLogout} />
  </ChatProvider>
);

export default DashboardPage;
