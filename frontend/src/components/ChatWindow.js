import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useChatContext } from '../context/ChatContext';
import { formatMessageTime, formatMessageDate } from '../utils/dateUtils';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Badge } from './ui/badge';
import { Send, UserPlus, Instagram, FileText, CheckCircle, Search, X } from 'lucide-react';
import axios from 'axios';
import { API } from '../App';
import { useIsMobile } from '../hooks/useMediaQuery';
import './ChatWindow.css';

const HUMAN_AGENT_WINDOW_MS = 24 * 60 * 60 * 1000;

const FacebookIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const ChatWindow = ({ agents, userRole, onAssignChat }) => {
  const { selectedChat: chat, sendMessage } = useChatContext();
  const isMobile = useIsMobile(); // Must be at top level before any conditional logic
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [filteredTemplates, setFilteredTemplates] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateVariables, setTemplateVariables] = useState({});
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [chat?.messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Load templates when dialog opens
  useEffect(() => {
    if (showTemplateDialog && chat) {
      loadTemplates();
    }
  }, [showTemplateDialog, chat]);

  // Filter templates based on search
  useEffect(() => {
    if (searchQuery.trim()) {
      const filtered = templates.filter(t => 
        t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.content.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredTemplates(filtered);
    } else {
      setFilteredTemplates(templates);
    }
  }, [searchQuery, templates]);

  // Keyboard shortcut for template selector (Ctrl+T or Cmd+T)
  useEffect(() => {
    const handleKeyPress = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 't') {
        e.preventDefault();
        if (chat) {
          setShowTemplateDialog(true);
        }
      }
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [chat]);

  useEffect(() => {
    if (!chat && isProfileOpen) {
      setIsProfileOpen(false);
    }
  }, [chat, isProfileOpen]);

  const loadTemplates = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/templates`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { platform: chat.platform }
      });
      setTemplates(response.data);
      setFilteredTemplates(response.data);
    } catch (error) {
      console.error('Error loading templates:', error);
    }
  };

  const extractVariables = (content) => {
    const regex = /\{([^}]+)\}/g;
    const variables = [];
    let match;
    while ((match = regex.exec(content)) !== null) {
      const varName = match[1];
      // Skip auto-populated variables
      if (varName !== 'username' && varName !== 'platform') {
        variables.push(varName);
      }
    }
    return [...new Set(variables)]; // Remove duplicates
  };

  const previewTemplateContent = (template) => {
    if (!template) return '';
    let content = template.content;
    // Auto-populate
    content = content.replace('{username}', chat.username);
    content = content.replace('{platform}', chat.platform);
    // User-provided variables
    Object.keys(templateVariables).forEach(key => {
      content = content.replace(`{${key}}`, templateVariables[key] || `{${key}}`);
    });
    return content;
  };

  const handleSelectTemplate = (template) => {
    setSelectedTemplate(template);
    const vars = extractVariables(template.content);
    const initialVars = {};
    vars.forEach(v => initialVars[v] = '');
    setTemplateVariables(initialVars);
  };

  const lastCustomerMessageTimestamp = useMemo(() => {
    if (!chat?.messages || chat.messages.length === 0) {
      return null;
    }

    for (let i = chat.messages.length - 1; i >= 0; i -= 1) {
      const message = chat.messages[i];
      if (!message) {
        continue;
      }
      const sender = (message.sender || '').toString().toLowerCase();
      if (sender !== 'agent') {
        if (!message.timestamp) {
          return null;
        }
        const time = new Date(message.timestamp).getTime();
        return Number.isNaN(time) ? null : time;
      }
    }

    return null;
  }, [chat?.messages]);

  const canSendManualMessage = useMemo(() => {
    if (!lastCustomerMessageTimestamp) {
      return true; // Allow if no inbound message recorded yet
    }
    const now = Date.now();
    return now - lastCustomerMessageTimestamp <= HUMAN_AGENT_WINDOW_MS;
  }, [lastCustomerMessageTimestamp]);

  useEffect(() => {
    if (!canSendManualMessage) {
      setMessage('');
    }
  }, [canSendManualMessage]);

  const handleSendTemplate = async () => {
    if (!selectedTemplate) return;
    if (!canSendManualMessage && !selectedTemplate.is_meta_approved) {
      alert('Only Meta-approved templates can be sent outside the 24-hour window.');
      return;
    }
    
    setIsSending(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/templates/${selectedTemplate.id}/send`,
        {
          chat_id: chat.id,
          variables: templateVariables
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setShowTemplateDialog(false);
      setSelectedTemplate(null);
      setTemplateVariables({});
      setSearchQuery('');
    } catch (error) {
      console.error('Error sending template:', error);
      const message = error.response?.data?.detail || 'Failed to send template';
      alert(message);
    } finally {
      setIsSending(false);
    }
  };

  const handleSend = useCallback(async (e) => {
    e.preventDefault();
    if (!chat || !message.trim() || isSending || !canSendManualMessage) {
      return;
    }

    setIsSending(true);
    try {
      await sendMessage(chat.id, message);
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  }, [message, chat, sendMessage, isSending, canSendManualMessage]);

  const handleProfileToggle = useCallback(() => {
    if (!chat) {
      return;
    }
    setIsProfileOpen((prev) => !prev);
  }, [chat]);

  const handleCloseProfile = useCallback(() => {
    setIsProfileOpen(false);
  }, []);

  if (!chat) {
    return (
      <div className="bg-[#1a1a2e] border border-gray-800 rounded-xl h-full w-full flex items-center justify-center" data-testid="no-chat-selected">
        <div className="text-center">
          <MessageSquareIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg">Select a chat to start messaging</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-[#1a1a2e] border border-gray-800 h-full w-full min-h-0 flex ${isMobile ? 'flex-col' : 'rounded-xl'}`}
      data-testid="chat-window"
    >
      <div className={`flex-1 flex flex-col min-h-0 ${!isMobile && isProfileOpen ? 'md:border-r md:border-gray-800' : ''}`}>
        {/* Chat Header */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                chat.platform === 'FACEBOOK'
                  ? 'bg-gradient-to-br from-blue-600 to-blue-700'
                  : 'bg-gradient-to-br from-purple-600 to-pink-600'
              }`}
            >
              {chat.platform === 'FACEBOOK' ? (
                <FacebookIcon className="w-5 h-5 text-white" />
              ) : (
                <Instagram className="w-5 h-5 text-white" />
              )}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleProfileToggle}
                  className="text-white font-bold hover:text-purple-300 transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500/50 rounded px-1 -mx-1"
                  data-testid="chat-username"
                  title="View profile info"
                >
                  @{chat.username}
                </button>
                <span
                  className={`px-2 py-0.5 text-xs rounded-full ${
                    chat.platform === 'FACEBOOK'
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-pink-500/20 text-pink-400'
                  }`}
                >
                  {chat.platform === 'FACEBOOK' ? 'Facebook' : 'Instagram'}
                </span>
              </div>
              <p className="text-xs text-gray-400" data-testid="chat-instagram-id">
                {chat.instagram_user_id}
              </p>
            </div>
          </div>

          {userRole === 'admin' && (
            <div className="flex items-center space-x-2">
              <Select
                value={chat.assigned_to || 'unassigned'}
                onValueChange={(value) => onAssignChat(chat.id, value === 'unassigned' ? null : value)}
              >
                <SelectTrigger
                  className="w-[200px] bg-[#0f0f1a] border-gray-700 text-white"
                  data-testid="assign-agent-select"
                >
                  <UserPlus className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Assign Agent" />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1a2e] border-gray-700">
                  <SelectItem value="unassigned" className="text-white">
                    Unassign
                  </SelectItem>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id} className="text-white">
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 chat-scroll" data-testid="messages-container">
          {chat.messages && chat.messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">No messages yet</div>
          ) : (
            chat.messages?.map((msg) => (
              <div
                key={msg.id}
                className={`message-bubble flex ${msg.sender === 'agent' ? 'justify-end' : 'justify-start'}`}
                data-testid={`message-${msg.id}`}
              >
                <div
                  className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                    msg.sender === 'agent'
                      ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                      : 'bg-[#0f0f1a] text-gray-200 border border-gray-700'
                  }`}
                >
                  <p className="text-sm">{msg.content}</p>
                  <p className={`text-xs mt-1 ${msg.sender === 'agent' ? 'text-purple-200' : 'text-gray-500'}`}>
                    {formatMessageTime(msg.timestamp)}
                  </p>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className={`p-3 md:p-4 border-t border-gray-800 ${isMobile ? 'pb-safe' : ''}`}>
          {!canSendManualMessage && (
            <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              The 24-hour human agent window has expired. Send an approved template or wait for the user to reply.
            </div>
          )}
          <form onSubmit={handleSend} className="flex space-x-2">
            <Button
              type="button"
              onClick={() => setShowTemplateDialog(true)}
              variant="outline"
              className={`bg-[#0f0f1a] border-gray-700 text-purple-400 hover:text-purple-300 ${
                isMobile ? 'min-w-[44px] min-h-[44px] p-3' : ''
              }`}
              title="Templates (Ctrl+T)"
            >
              <FileText className={`${isMobile ? 'w-5 h-5' : 'w-4 h-4'}`} />
            </Button>
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className={`flex-1 bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500 ${
                isMobile ? 'min-h-[44px] text-base' : ''
              }`}
              data-testid="message-input"
              disabled={!canSendManualMessage}
              aria-disabled={!canSendManualMessage}
              placeholder={
                canSendManualMessage
                  ? 'Type a message...'
                  : '24-hour window expired. Use an approved template.'
              }
            />
            <Button
              type="submit"
              disabled={!message.trim() || isSending || !canSendManualMessage}
              className={`bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 ${
                isMobile ? 'min-w-[44px] min-h-[44px] p-3' : ''
              }`}
              data-testid="send-message-button"
            >
              <Send className={`${isMobile ? 'w-5 h-5' : 'w-4 h-4'}`} />
            </Button>
          </form>
        </div>

        {/* Template Selector Dialog */}
        <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
          <DialogContent className="bg-[#1a1a2e] border-gray-700 text-white sm:max-w-[700px] max-h-[80vh]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Select Template
              </DialogTitle>
              <DialogDescription className="text-gray-400">
                Choose a template to send to @{chat?.username}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search templates..."
                  className="pl-10 bg-[#0f0f1a] border-gray-700"
                />
              </div>

              {/* Template List */}
              <div className="max-h-[300px] overflow-y-auto space-y-2 pr-2">
                {filteredTemplates.length === 0 ? (
                  <p className="text-center text-gray-400 py-8">
                    {templates.length === 0
                      ? 'No templates available for this platform'
                      : 'No templates match your search'}
                  </p>
                ) : (
                  filteredTemplates.map((template) => (
                    <div
                      key={template.id}
                      onClick={() => handleSelectTemplate(template)}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedTemplate?.id === template.id
                          ? 'border-purple-600 bg-purple-600/10'
                          : 'border-gray-700 hover:border-gray-600 bg-[#0f0f1a]'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-white">{template.name}</h4>
                          {template.is_meta_approved && (
                            <Badge className="bg-purple-600 text-white text-xs">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Utility
                            </Badge>
                          )}
                        </div>
                        <Badge variant="outline" className="border-gray-600 text-xs">
                          {template.category}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-400 line-clamp-2">{template.content}</p>
                    </div>
                  ))
                )}
              </div>

              {/* Template Preview & Variables */}
              {selectedTemplate && (
                <div className="space-y-3 border-t border-gray-700 pt-4">
                  <h4 className="font-semibold text-white">Preview & Variables</h4>

                  {/* Variable Inputs */}
                  {Object.keys(templateVariables).length > 0 && (
                    <div className="space-y-2">
                      {Object.keys(templateVariables).map((varName) => (
                        <div key={varName}>
                          <label className="text-sm text-gray-400 block mb-1">{varName}</label>
                          <Input
                            value={templateVariables[varName]}
                            onChange={(e) =>
                              setTemplateVariables({
                                ...templateVariables,
                                [varName]: e.target.value,
                              })
                            }
                            placeholder={`Enter ${varName}`}
                            className="bg-[#0f0f1a] border-gray-700"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Preview */}
                  <div className="p-3 bg-[#0f0f1a] rounded-lg border border-gray-700">
                    <p className="text-sm text-gray-300 whitespace-pre-wrap">
                      {previewTemplateContent(selectedTemplate)}
                    </p>
                  </div>

                  {/* Send Button */}
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setSelectedTemplate(null);
                        setTemplateVariables({});
                      }}
                    >
                      Clear
                    </Button>
                    <Button
                      onClick={handleSendTemplate}
                      disabled={
                        isSending ||
                        (!canSendManualMessage && !selectedTemplate?.is_meta_approved)
                      }
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Send Template
                    </Button>
                  </div>
                  {!canSendManualMessage && !selectedTemplate?.is_meta_approved && (
                    <p className="text-xs text-amber-300 text-right">
                      Meta-approved templates are required outside the 24-hour window.
                    </p>
                  )}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isProfileOpen && (
        <ChatProfilePanel
          chat={chat}
          onClose={handleCloseProfile}
          isMobile={isMobile}
          canSendManualMessage={canSendManualMessage}
        />
      )}
    </div>
  );
};

const ChatProfilePanel = ({ chat, onClose, isMobile, canSendManualMessage }) => {
  const assignedAgent = chat.assigned_agent;
  const messageCount = chat.messages?.length ?? 0;
  const lastMessage =
    chat.messages && chat.messages.length > 0 ? chat.messages[chat.messages.length - 1] : null;

  const statusLabel = chat.status
    ? chat.status
        .split(/[_\s]+/)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ')
    : 'Unknown';

  const statusBadgeClass =
    chat.status === 'assigned'
      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/40'
      : 'bg-amber-500/10 text-amber-300 border-amber-500/40';

  const platformLabel = chat.platform === 'FACEBOOK' ? 'Facebook' : 'Instagram';
  const initials = chat.username?.charAt(0)?.toUpperCase() || '?';

  const infoItems = [
    {
      label: 'Chat Created',
      value: chat.created_at ? formatMessageDate(chat.created_at) : 'Not available',
    },
    {
      label: 'Last Updated',
      value: chat.updated_at ? formatMessageDate(chat.updated_at) : 'Not available',
    },
    {
      label: 'Total Messages',
      value: messageCount,
    },
    {
      label: 'Unread Messages',
      value: chat.unread_count ?? 0,
    },
    ...(chat.instagram_user_id
      ? [
          {
            label: 'Instagram User ID',
            value: chat.instagram_user_id,
          },
        ]
      : []),
    ...(chat.facebook_page_id
      ? [
          {
            label: 'Facebook Page ID',
            value: chat.facebook_page_id,
          },
        ]
      : []),
    {
      label: 'Chat ID',
      value: chat.id,
    },
    {
      label: 'Human Agent Window',
      value: canSendManualMessage ? 'Active (within 24 hours)' : 'Expired',
    },
  ];

  return (
    <aside
      className={`bg-[#101023] border-t border-gray-800 w-full md:w-[320px] md:max-w-sm md:border-t-0 md:border-l border-gray-800 flex flex-col min-h-0 ${
        isMobile ? 'rounded-b-xl' : 'rounded-r-xl'
      }`}
    >
      <div className="p-4 border-b border-gray-800 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center font-semibold text-white">
            {initials}
          </div>
          <div>
            <p className="text-xs uppercase text-gray-500 tracking-wide">Profile</p>
            <p className="text-lg font-semibold text-white">@{chat.username}</p>
            <div className="flex flex-wrap gap-2 mt-2">
              <Badge className={statusBadgeClass}>{statusLabel}</Badge>
              <Badge variant="outline" className="border-gray-700 text-gray-300">
                {platformLabel}
              </Badge>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 transition-colors"
          aria-label="Close profile panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 chat-scroll">
        <div className="space-y-2">
          <p className="text-xs uppercase text-gray-500 tracking-wide">Assigned Agent</p>
          {assignedAgent ? (
            <>
              <p className="text-sm font-medium text-white">{assignedAgent.name}</p>
              <p className="text-xs text-gray-400">{assignedAgent.email}</p>
            </>
          ) : (
            <p className="text-sm text-gray-400">Unassigned</p>
          )}
        </div>

        <div className="space-y-2">
          <p className="text-xs uppercase text-gray-500 tracking-wide">Last Message</p>
          {lastMessage ? (
            <div className="bg-[#0a0a17] border border-gray-800 rounded-lg p-3">
              <p className="text-sm text-gray-300 whitespace-pre-wrap">{lastMessage.content}</p>
              <p className="text-xs text-gray-500 mt-2">
                {lastMessage.timestamp ? formatMessageDate(lastMessage.timestamp) : ''}
              </p>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No messages yet</p>
          )}
        </div>

        <div className="space-y-4">
          {infoItems.map((item) => (
            <div key={item.label} className="flex flex-col">
              <span className="text-xs uppercase text-gray-500 tracking-wide">{item.label}</span>
              <span className="text-sm text-gray-200 break-all">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
};

const MessageSquareIcon = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);

export default ChatWindow;
