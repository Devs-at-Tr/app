import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useChatContext } from '../context/ChatContext';
import { cn } from '../lib/utils';
import {
  formatMessageTime,
  formatMessageDate,
  formatMessageDay,
  formatMessageFullDateTime
} from '../utils/dateUtils';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
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
import { API, BACKEND_URL } from '../App';
import { useIsMobile } from '../hooks/useMediaQuery';
import './ChatWindow.css';

const HUMAN_AGENT_WINDOW_MS = 24 * 60 * 60 * 1000;

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

const ChatWindow = ({ agents, userRole, onAssignChat, canAssignChats = false }) => {
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
  const chatHandle = useMemo(() => getChatHandle(chat), [chat]);
  const chatDisplayName = useMemo(() => getChatDisplayName(chat), [chat]);
  const chatAvatarUrl = useMemo(() => {
    if (!chat) {
      return null;
    }
    if (chat.profile_pic_url) {
      return chat.profile_pic_url;
    }
    if (chatHandle) {
      const encoded = encodeURIComponent(chatHandle);
      return `https://ui-avatars.com/api/?name=${encoded}&background=241f3a&color=ffffff`;
    }
    return null;
  }, [chat, chatHandle]);

  const assignedAgentName = useMemo(() => {
    if (!chat) {
      return null;
    }
    return (
      chat.assigned_agent?.name ||
      chat.assigned_agent?.email ||
      chat.assigned_to_name ||
      chat.assigned_to ||
      null
    );
  }, [chat]);

  const lastActivityLabel = useMemo(() => {
    if (!chat) {
      return '';
    }
    const timestamp = chat.last_message_timestamp || chat.updated_at || chat.created_at;
    if (!timestamp) {
      return '';
    }
    return formatMessageFullDateTime(timestamp);
  }, [chat]);

  useEffect(() => {
    scrollToBottom();
  }, [chat?.messages]);

  const orderedMessages = useMemo(() => {
    if (!chat?.messages) {
      return [];
    }
    const seenIds = new Set();
    return [...chat.messages]
      .filter((msg) => {
        if (!msg?.id) {
          return true;
        }
        if (seenIds.has(msg.id)) {
          return false;
        }
        seenIds.add(msg.id);
        return true;
      })
      .sort((a, b) => {
        const tsA = (() => {
          if (a?.timestamp) {
            const value = new Date(a.timestamp).getTime();
            if (!Number.isNaN(value)) {
              return value;
            }
          }
          if (typeof a?.ts === 'number') {
            return a.ts * 1000;
          }
          return 0;
        })();
        const tsB = (() => {
          if (b?.timestamp) {
            const value = new Date(b.timestamp).getTime();
            if (!Number.isNaN(value)) {
              return value;
            }
          }
          if (typeof b?.ts === 'number') {
            return b.ts * 1000;
          }
          return 0;
        })();
        return tsA - tsB;
      });
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
    const chatHandle = getChatHandle(chat);
    // Auto-populate
    content = content.replace('{username}', chatHandle);
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
      if (sender !== 'agent' && sender !== 'instagram_page') {
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
      <div className="conversation-panel h-full w-full flex items-center justify-center" data-testid="no-chat-selected">
        <div className="text-center space-y-2">
          <MessageSquareIcon className="w-16 h-16 text-gray-600 mx-auto" />
          <p className="text-[var(--tg-text-secondary)] text-lg">Select a chat to start messaging</p>
        </div>
      </div>
    );
  const AttachmentPreview = ({ url }) => {
    const [mode, setMode] = useState('video'); // 'video' → 'image' → 'link'

    if (mode === 'video') {
      return (
        <video
          src={url}
          controls
          className="max-h-64 w-full rounded-xl border border-white/10"
          onError={() => setMode('image')} // if not a video, try image
        >
          Your browser does not support the video tag.
        </video>
      );
    }

    if (mode === 'image') {
      return (
        <img
          src={url}
          alt="attachment"
          className="max-h-64 w-full rounded-xl object-cover border border-white/10"
          onError={() => setMode('link')} // if not an image, fall back to link
        />
      );
    }

    // Final fallback: just a link
    return (
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="block text-xs text-purple-200 underline break-all"
      >
        Open attachment
      </a>
    );
  };
  return (
    <div
      className={`flex h-full min-h-0 relative w-full ${isMobile ? 'flex-col space-y-4' : ''}`}
      data-testid="chat-window"
    >
      <div className="conversation-panel flex-1 relative w-full">
        {/* Chat Header */}
        <div className="conversation-header">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {chatAvatarUrl ? (
              <img
                src={chatAvatarUrl}
                alt={chatDisplayName}
                className="w-12 h-12 rounded-full object-cover border border-gray-700"
              />
            ) : (
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center ${
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
            )}
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={handleProfileToggle}
                  className="text-lg font-semibold text-white hover:text-[var(--tg-accent-strong)] transition-colors"
                  data-testid="chat-username"
                  title="View profile info"
                >
                  {chatDisplayName}
                </button>
                <span className="assignment-pill inline-flex items-center gap-1">
                  {chat.platform === 'FACEBOOK' ? (
                    <FacebookIcon className="w-3.5 h-3.5" />
                  ) : (
                    <Instagram className="w-3.5 h-3.5" />
                  )}
                  {chat.platform === 'FACEBOOK' ? 'Messenger' : 'Instagram'}
                </span>
                {chat.status && (
                  <span className="assignment-pill">
                    {chat.status.replace('_', ' ')}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--tg-text-muted)]">
                <span data-testid="chat-instagram-id">@{chatHandle || 'unknown'}</span>
                {lastActivityLabel && <span>Last activity · {lastActivityLabel}</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap justify-end">
            <span
              className={`assignment-pill ${assignedAgentName ? '' : 'assignment-pill--unassigned'}`}
            >
              {assignedAgentName ? `Assigned to ${assignedAgentName}` : 'Unassigned'}
            </span>
            {canAssignChats && (
              <Select
                value={chat.assigned_to || 'unassigned'}
                onValueChange={(value) => onAssignChat(chat.id, value === 'unassigned' ? null : value)}
              >
                <SelectTrigger
                  className="w-full sm:w-[220px] bg-transparent border-gray-700 text-white rounded-full"
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
            )}
            <Button variant="ghost" size="sm" onClick={handleProfileToggle}>
              {isProfileOpen ? 'Hide details' : 'View details'}
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="conversation-body space-y-4 chat-scroll" data-testid="messages-container">
          {orderedMessages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">No messages yet</div>
          ) : (
            (() => {
              let lastRenderedDay = null;
              return orderedMessages.map((msg, index) => {
                const senderType = (msg.sender || '').toString().toLowerCase();
                const isInstagramPage = senderType === 'instagram_page';
                const isAgentMessage = senderType === 'agent' || isInstagramPage;
                const isTicklegramMessage = Boolean(msg.is_ticklegram);
                const showAsTicklegram = isTicklegramMessage && isAgentMessage;
              const bubbleClasses = showAsTicklegram
                ? 'bubble-agent'
                : isInstagramPage
                  ? 'bubble-agent-external'
                  : isAgentMessage
                    ? 'bubble-agent'
                    : 'bubble-user';
                const sentByName = msg.sent_by?.name || msg.sent_by?.email;
                let originLabel = '';
                if (showAsTicklegram) {
                  originLabel = `Sent from Ticklegram${sentByName ? ` · ${sentByName}` : ''}`;
                } else if (isInstagramPage) {
                  originLabel = 'Sent from Instagram app';
                } else if (sentByName) {
                  originLabel = `Sent by ${sentByName}`;
                }
                const attachments = Array.isArray(msg.attachments) ? msg.attachments : [];
                const hasAttachments = attachments.length > 0;
                const placeholderText = (msg.content || '').trim().toLowerCase();
                const hideText = hasAttachments && (placeholderText === '[attachment]' || placeholderText === '');
                const displayText = hideText ? '' : msg.content;
                const dayLabel = msg.timestamp ? formatMessageDay(msg.timestamp) : (msg.ts ? formatMessageDay(new Date(msg.ts * 1000).toISOString()) : '');
                const showDayLabel = dayLabel && dayLabel !== lastRenderedDay;
                if (showDayLabel) {
                  lastRenderedDay = dayLabel;
                }

                const resolveAttachmentUrl = (attachment) => {
                  const source =
                    attachment?.public_url ||
                    attachment?.payload?.url ||
                    attachment?.url ||
                    '';
                  if (!source) {
                    return null;
                  }
                  if (source.startsWith('http')) {
                    return source;
                  }
                  const base = BACKEND_URL || '';
                  return `${base}${source}`;
                };

                return (
                  <React.Fragment key={msg.id || `${index}-${msg.timestamp || 'message'}`}>
                    {showDayLabel && (
                      <div className="text-center text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">
                        {dayLabel}
                      </div>
                    )}
                    <div
                      className={`message-bubble flex ${isAgentMessage ? 'justify-end' : 'justify-start'}`}
                      data-testid={`message-${msg.id}`}
                    >
                      <div
                        className={`max-w-[70%] rounded-2xl px-4 py-3 ${bubbleClasses}`}
                      >
                        {displayText && (
                          <p className="text-sm whitespace-pre-line break-words">{displayText}</p>
                        )}
                        {originLabel && (
                          <p className="message-origin italic mt-1">
                            {originLabel}
                          </p>
                        )}
                        {attachments.length > 0 && (
                          <div className="mt-3 space-y-2">
                            {attachments.map((attachment, index) => {
                              const attachmentUrl = resolveAttachmentUrl(attachment);
                              if (!attachmentUrl) return null;

                              return (
                                <div key={`${msg.id || 'msg'}-attachment-${index}`}>
                                  <AttachmentPreview url={attachmentUrl} />
                                </div>
                              );
                            })}
                          </div>
                        )}
                        <p
                          className={`message-timestamp mt-2 ${
                            isAgentMessage ? 'message-timestamp--agent' : ''
                          }`}
                        >
                          {formatMessageFullDateTime(msg.timestamp || (msg.ts ? new Date(msg.ts * 1000).toISOString() : null))}
                        </p>
                      </div>
                    </div>
                  </React.Fragment>
                );
              });
            })()
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className={`composer-shell ${isMobile ? 'rounded-2xl border border-[var(--tg-border-soft)] pb-safe' : ''}`}>
          {!canSendManualMessage && (
            <div className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              The 24-hour human agent window has expired. Send an approved template or wait for the user to reply.
            </div>
          )}
          <form onSubmit={handleSend} className="space-y-3">
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className={`composer-textarea ${isMobile ? 'min-h-[80px]' : 'min-h-[100px]'}`}
              data-testid="message-input"
              disabled={!canSendManualMessage}
              aria-disabled={!canSendManualMessage}
              placeholder={
                canSendManualMessage
                  ? 'Type a reply, use / for shortcuts...'
                  : '24-hour window expired. Use an approved template.'
              }
            />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="composer-toolbar">
                <Button
                  type="button"
                  onClick={() => setShowTemplateDialog(true)}
                  variant="ghost"
                  className={isMobile ? 'min-w-[44px] min-h-[44px]' : ''}
                  title="Templates (Ctrl+T)"
                >
                  <FileText className="w-4 h-4" />
                  <span className="hidden sm:inline">Templates</span>
                </Button>
              </div>
              <Button
                type="submit"
                disabled={!message.trim() || isSending || !canSendManualMessage}
                className={`rounded-full px-6 py-2 bg-gradient-to-r from-indigo-500 to-blue-500 hover:from-indigo-600 hover:to-blue-600 ${
                  isMobile ? 'min-h-[44px]' : ''
                }`}
                data-testid="send-message-button"
              >
                <Send className="w-4 h-4 mr-2" />
                Send
              </Button>
            </div>
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
                Choose a template to send to @{chatHandle || 'unknown'}
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

      {!isMobile && isProfileOpen && (
        <div className="chat-profile-overlay">
          <ChatProfilePanel
            chat={chat}
            onClose={handleCloseProfile}
            isMobile={false}
            canSendManualMessage={canSendManualMessage}
            chatDisplayName={chatDisplayName}
            chatHandle={chatHandle}
            chatAvatarUrl={chatAvatarUrl}
          />
        </div>
      )}
      {isMobile && isProfileOpen && (
        <div className="mt-4">
          <ChatProfilePanel
            chat={chat}
            onClose={handleCloseProfile}
            isMobile
            canSendManualMessage={canSendManualMessage}
            chatDisplayName={chatDisplayName}
            chatHandle={chatHandle}
            chatAvatarUrl={chatAvatarUrl}
          />
        </div>
      )}
    </div>
  );
};

const ChatProfilePanel = ({
  chat,
  onClose,
  isMobile,
  canSendManualMessage,
  chatDisplayName,
  chatHandle,
  chatAvatarUrl,
}) => {
  const assignedAgent = chat.assigned_agent;
  const messageCount = chat.messages?.length ?? 0;
  const lastMessage =
    chat.messages && chat.messages.length > 0 ? chat.messages[chat.messages.length - 1] : null;

  const displayName = chatDisplayName || getChatDisplayName(chat);
  const handle = chatHandle || getChatHandle(chat);
  const avatarUrl =
    chatAvatarUrl ||
    chat.profile_pic_url ||
    (handle ? `https://ui-avatars.com/api/?name=${encodeURIComponent(handle)}` : null);

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
  const initials = displayName?.charAt(0)?.toUpperCase() || '?';

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
      className={cn(
        'chat-panel bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] flex flex-col min-h-0',
        isMobile ? 'rounded-2xl' : 'h-full'
      )}
    >
      <div className="p-5 border-b border-[var(--tg-border-soft)] flex items-start justify-between">
        <div className="flex items-center gap-3">
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={displayName}
              className="w-10 h-10 rounded-full object-cover border border-[var(--tg-border-soft)]"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center font-semibold text-white">
              {initials}
            </div>
          )}
          <div>
            <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide">Profile</p>
            <p className="text-lg font-semibold text-[var(--tg-text-primary)]">{displayName}</p>
            <p className="text-xs text-[var(--tg-text-muted)]">@{handle || 'unknown'}</p>
            <div className="flex flex-wrap gap-2 mt-2">
              <Badge className={statusBadgeClass}>{statusLabel}</Badge>
              <Badge variant="outline" className="border-[var(--tg-border-soft)] text-[var(--tg-text-secondary)]">
                {platformLabel}
              </Badge>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)] transition-colors"
          aria-label="Close profile panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 chat-scroll">
        <div className="space-y-2">
          <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide">Assigned Agent</p>
          {assignedAgent ? (
            <>
              <p className="text-sm font-medium text-[var(--tg-text-primary)]">{assignedAgent.name}</p>
              <p className="text-xs text-[var(--tg-text-muted)]">{assignedAgent.email}</p>
            </>
          ) : (
            <p className="text-sm text-[var(--tg-text-muted)]">Unassigned</p>
          )}
        </div>

        <div className="space-y-2">
          <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide">Last Message</p>
          {lastMessage ? (
            <div className="bg-[var(--tg-surface-muted)] border border-[var(--tg-border-soft)] rounded-lg p-3">
              <p className="text-sm text-[var(--tg-text-primary)] whitespace-pre-wrap">{lastMessage.content}</p>
              <p className="text-xs text-[var(--tg-text-muted)] mt-2">
                {lastMessage.timestamp ? formatMessageDate(lastMessage.timestamp) : ''}
              </p>
            </div>
          ) : (
            <p className="text-sm text-[var(--tg-text-muted)]">No messages yet</p>
          )}
        </div>

        <div className="space-y-4">
          {infoItems.map((item) => (
            <div key={item.label} className="flex flex-col">
              <span className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide">{item.label}</span>
              <span className="text-sm text-[var(--tg-text-primary)] break-all">{item.value}</span>
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
