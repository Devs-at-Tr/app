import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from 'react';
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
import { Send, UserPlus, Instagram, FileText, CheckCircle, Search, X, ChevronLeft, Info, CornerUpLeft, Smile, Paperclip, PhoneCall } from 'lucide-react';
import axios from 'axios';
import { API, BACKEND_URL } from '../App';
import { useIsMobile, useIsTablet } from '../hooks/useMediaQuery';
import CreateInquiryModal from './CreateInquiryModal';
import './ChatWindow.css';

const HUMAN_AGENT_WINDOW_MS = 24 * 60 * 60 * 1000;
const AUTOFILL_PROPS = {
  autoComplete: 'off',
  autoCorrect: 'off',
  autoCapitalize: 'off',
  spellCheck: false,
  name: 'no-autofill',
};
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

const extractTemplatePayload = (attachments = []) => {
  if (!Array.isArray(attachments)) {
    return null;
  }
  for (const attachment of attachments) {
    if (!attachment || attachment.type !== 'template') {
      continue;
    }
    const payload = attachment.payload || {};
    const elements =
      (payload.generic && payload.generic.elements) ||
      payload.elements ||
      [];
    if (!Array.isArray(elements) || elements.length === 0) {
      continue;
    }
    const [first] = elements;
    const buttons = Array.isArray(first?.buttons) ? first.buttons : [];
    return {
      title: first?.title || '',
      buttons,
    };
  }
  return null;
};

const getMessageSnippet = (message) => {
  if (!message) {
    return '';
  }
  const content = (message.content || '').trim();
  if (content && content.toLowerCase() !== '[attachment]') {
    return content;
  }
  const templatePayload = extractTemplatePayload(message.attachments);
  if (templatePayload?.title) {
    return templatePayload.title;
  }
  if (Array.isArray(message.attachments) && message.attachments.length > 0) {
    return '[attachment]';
  }
  return '';
};

const splitFullName = (raw = '') => {
  const onlyAlnumSpaces = (raw || '').replace(/[^A-Za-z0-9\s]/g, '').trim();
  const cleaned = onlyAlnumSpaces.replace(/\s+/g, ' ');
  if (!cleaned) return { first: '', middle: '', last: '' };
  const parts = cleaned.split(' ');
  if (parts.length === 1) {
    return { first: parts[0], middle: '', last: '' };
  }
  if (parts.length === 2) {
    return { first: parts[0], middle: '', last: parts[1] };
  }
  return { first: parts[0], middle: parts.slice(1, -1).join(' '), last: parts[parts.length - 1] };
};

const FacebookIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const getSenderLabel = (message, chat) => {
  const sender = (message?.sender || '').toString().toLowerCase();
  if (sender === 'agent' || sender === 'instagram_page') {
    return 'You';
  }
  if (message?.sent_by?.name) {
    return message.sent_by.name;
  }
  return (
    chat?.instagram_user?.name ||
    chat?.facebook_user?.name ||
    chat?.username ||
    'User'
  );
};

const ChatWindow = ({
  agents,
  userRole,
  onAssignChat,
  canAssignChats = false,
  onBackToList,
  showAssignmentInfo = true,
  currentUser = null,
}) => {
  const { selectedChat: chat, sendMessage, selectChat } = useChatContext();
  const isFacebookChat = chat?.platform === 'FACEBOOK';
  const isMobile = useIsMobile(); // Must be at top level before any conditional logic
  const isTablet = useIsTablet();

  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [filteredTemplates, setFilteredTemplates] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateVariables, setTemplateVariables] = useState({});
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [replyTarget, setReplyTarget] = useState(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [showAttachmentForm, setShowAttachmentForm] = useState(false);
  const [attachmentUrl, setAttachmentUrl] = useState('');
  const [attachmentType, setAttachmentType] = useState('image');
  const attachmentsEnabled = false;
  const [showInquiryModal, setShowInquiryModal] = useState(false);
  const [createInquiryPrefill, setCreateInquiryPrefill] = useState({});
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const longPressTimerRef = useRef(null);
  const messageRefs = useRef({});
  const emojiPopoverRef = useRef(null);
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
  }, [chat?.id]);

  useEffect(() => {
    setReplyTarget(null);
    messageRefs.current = {};
  }, [chat?.id]);

  const handleMessageTouchStart = useCallback((message) => {
    if (!isMobile) {
      return;
    }
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
    }
    longPressTimerRef.current = setTimeout(() => {
      setReplyTarget({
        id: message.id,
        author: getSenderLabel(message, chat),
        snippet: getMessageSnippet(message) || '[attachment]',
      });
    }, 600);
  }, [chat, isMobile]);

  const cancelTouchTimer = useCallback(() => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
  }, []);

  const handleReplyClick = useCallback((event, message) => {
    event?.stopPropagation();
    setReplyTarget({
      id: message.id,
      author: getSenderLabel(message, chat),
      snippet: getMessageSnippet(message) || '[attachment]',
    });
  }, [chat]);

  const handleCancelReply = useCallback(() => {
    setReplyTarget(null);
  }, []);

  const handleQuotedMessageJump = useCallback((messageId) => {
    if (!messageId) return;
    const node = messageRefs.current[messageId];
    if (node) {
      node.scrollIntoView({ behavior: 'smooth', block: 'center' });
      node.classList.add('message-highlight');
      setTimeout(() => {
        node.classList.remove('message-highlight');
      }, 1200);
    }
  }, []);

  const setMessageNodeRef = useCallback((id) => (element) => {
    if (element) {
      messageRefs.current[id] = element;
    }
  }, []);

  const orderedMessages = useMemo(() => {
    if (!chat?.messages) {
      return [];
    }
    const seenIds = new Set();
    return [...chat.messages]
      .filter((msg) => {
        if (!msg?.id) return true;
        if (seenIds.has(msg.id)) return false;
        seenIds.add(msg.id);
        return true;
      })
      .sort((a, b) => {
        const tsA = (() => {
          if (a?.timestamp) {
            const v = new Date(a.timestamp).getTime();
            if (!Number.isNaN(v)) return v;
          }
          if (typeof a?.ts === 'number') return a.ts * 1000;
          return 0;
        })();
        const tsB = (() => {
          if (b?.timestamp) {
            const v = new Date(b.timestamp).getTime();
            if (!Number.isNaN(v)) return v;
          }
          if (typeof b?.ts === 'number') return b.ts * 1000;
          return 0;
        })();
        return tsA - tsB; // oldest -> newest
      });
  }, [chat?.messages]);

  useLayoutEffect(() => {
    scrollToBottom();
  }, [orderedMessages]);

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
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

  useEffect(() => () => cancelTouchTimer(), [cancelTouchTimer]);

  useEffect(() => {
    const handleOutside = (event) => {
      if (!showEmojiPicker) return;
      if (emojiPopoverRef.current && !emojiPopoverRef.current.contains(event.target)) {
        setShowEmojiPicker(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('touchstart', handleOutside);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('touchstart', handleOutside);
    };
  }, [showEmojiPicker]);

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
    if (!varName) continue;
    variables.push(varName);
  }
  return [...new Set(variables)]; // Remove duplicates
};

  const previewTemplateContent = (template) => {
    if (!template) return '';
    let content = template.content;
    const chatHandle = getChatHandle(chat);
    // Auto-populate
    const replacements = {
      username: chatHandle,
      platform: chat.platform,
      'user.name': chat?.instagram_user?.name || chat?.facebook_user?.name || chat?.username || chatHandle,
      'user.handle': chatHandle,
    };
    Object.entries(replacements).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        content = content.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
      }
    });
    // User-provided variables
    Object.keys(templateVariables).forEach(key => {
      const val = templateVariables[key];
      if (val) {
        content = content.replace(new RegExp(`\\{${key}\\}`, 'g'), val);
      }
    });
    return content;
  };

  const handleSelectTemplate = (template) => {
    setSelectedTemplate(template);
    const vars = extractVariables(template.content);
    const initialVars = {};
    vars.forEach((v) => {
      // Pre-fill common variables with best-effort values while keeping structure unchanged
      if (v === 'username') {
        initialVars[v] = getChatHandle(chat);
      } else if (v === 'name') {
        initialVars[v] = chat?.instagram_user?.name || chat?.facebook_user?.name || chat?.username || '';
      } else if (v === 'agent_name') {
        initialVars[v] = currentUser?.name || currentUser?.email || '';
      } else {
        initialVars[v] = '';
      }
    });
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
    if (!isFacebookChat) {
      return true; // 24-hour window enforced only for Facebook chats
    }
    if (!lastCustomerMessageTimestamp) {
      return true; // Allow if no inbound message recorded yet
    }
    const now = Date.now();
    return now - lastCustomerMessageTimestamp <= HUMAN_AGENT_WINDOW_MS;
  }, [isFacebookChat, lastCustomerMessageTimestamp]);

  const show24hExpiryNotice = isFacebookChat && !canSendManualMessage;

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
      const payload = {
        chat_id: chat.id,
        variables: templateVariables,
      };
      if (replyTarget?.id) {
        payload.reply_to_message_id = replyTarget.id;
        if (replyTarget.snippet) {
          payload.reply_preview = replyTarget.snippet;
        }
      }
      await axios.post(
        `${API}/templates/${selectedTemplate.id}/send`,
        payload,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setShowTemplateDialog(false);
      setSelectedTemplate(null);
      setTemplateVariables({});
      setSearchQuery('');
      if (replyTarget) {
        setReplyTarget(null);
      }
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
      await sendMessage(chat.id, message, {
        replyTo: replyTarget ? { id: replyTarget.id, preview: replyTarget.snippet } : undefined,
        attachments,
      });
      setMessage('');
      if (replyTarget) {
        setReplyTarget(null);
      }
      setShowEmojiPicker(false);
      setAttachments([]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  }, [message, chat, sendMessage, isSending, canSendManualMessage, replyTarget, attachments]);

  const handleProfileToggle = useCallback(() => {
    if (!chat) {
      return;
    }
    setIsProfileOpen((prev) => !prev);
  }, [chat]);

  const handleCloseProfile = useCallback(() => {
    setIsProfileOpen(false);
  }, []);

  const showMobileBackButton = Boolean(onBackToList) && isMobile;

  const AttachmentPreview = ({ url }) => {
    const [mode, setMode] = useState('video'); // 'video' -> 'image' -> 'link'

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

  if (!chat) {
    return (
      <div className="conversation-panel h-full w-full flex items-center justify-center" data-testid="no-chat-selected">
        <div className="text-center space-y-2">
          <MessageSquareIcon className="w-16 h-16 text-gray-600 mx-auto" />
          <p className="text-[var(--tg-text-secondary)] text-lg">Select a chat to start messaging</p>
        </div>
      </div>
    );
  }
  return (
    <div
      className={cn(
        'flex h-full min-h-0 w-full gap-3 overflow-hidden',
        isMobile ? 'flex-col' : 'items-stretch'
      )}
      data-testid="chat-window"
    >
      <div className="conversation-panel flex-1 relative w-full min-w-0 flex flex-col">
        {/* Chat Header */}
        <div className="conversation-header">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {showMobileBackButton && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="px-2 text-[var(--tg-text-primary)] hover:text-[var(--tg-accent-strong)] rounded-full bg-[var(--tg-surface-muted)]/60"
                onClick={onBackToList}
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                <span className="text-sm font-medium">Back</span>
              </Button>
            )}
            <div className="flex items-center gap-3 min-w-0 flex-1">
              {chatAvatarUrl ? (
                <img
                  src={chatAvatarUrl}
                  alt={chatDisplayName}
                  className="w-10 h-10 rounded-full object-cover border border-gray-700"
                />
              ) : (
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    chat.platform === 'FACEBOOK'
                      ? 'bg-gradient-to-br from-blue-600 to-blue-700'
                      : 'bg-gradient-to-br from-purple-600 to-pink-600'
                  }`}
                >
                  {chat.platform === 'FACEBOOK' ? (
                    <FacebookIcon className="w-4 h-4 text-white" />
                  ) : (
                    <Instagram className="w-4 h-4 text-white" />
                  )}
                </div>
              )}
              <div className="flex flex-col gap-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 min-w-0">
                  <button
                    type="button"
                    onClick={handleProfileToggle}
                    className="text-sm sm:text-base font-semibold text-white hover:text-[var(--tg-accent-strong)] transition-colors truncate max-w-[200px] sm:max-w-[260px]"
                    data-testid="chat-username"
                    title="View profile info"
                  >
                    {chatDisplayName}
                  </button>
                  <span className="assignment-pill assignment-pill--compact inline-flex items-center gap-1">
                    {chat.platform === 'FACEBOOK' ? (
                      <FacebookIcon className="w-3.5 h-3.5" />
                    ) : (
                      <Instagram className="w-3.5 h-3.5" />
                    )}
                    {chat.platform === 'FACEBOOK' ? 'Messenger' : 'Instagram'}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--tg-text-muted)] min-w-0">
                  <span className="truncate">@{chatHandle || 'unknown'}</span>
                  {lastActivityLabel && (
                    <span className="hidden sm:inline-flex items-center gap-1 text-[var(--tg-text-muted)]">
                      <span className="inline-block w-1 h-1 rounded-full bg-[var(--tg-border-soft)]" />
                      <span className="truncate">{lastActivityLabel}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap justify-end w-full md:w-auto md:flex-none">
            {canAssignChats ? (
              <Select
                value={chat.assigned_to || 'unassigned'}
                onValueChange={(value) => onAssignChat(chat.id, value === 'unassigned' ? null : value)}
              >
                <SelectTrigger
                  className="h-9 w-[170px] md:w-[190px] border-[var(--tg-border-soft)] bg-[var(--tg-surface)] text-white rounded-full px-3 text-sm"
                  data-testid="assign-agent-select"
                >
                  <UserPlus className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Assign Agent" />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1a2e] border-gray-700">
                  <SelectItem value="unassigned" className="text-white">
                    Unassigned
                  </SelectItem>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id} className="text-white">
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              showAssignmentInfo && (
              <span
                className={cn(
                  'assignment-pill assignment-pill--compact text-xs px-3 py-1.5 rounded-full truncate max-w-[220px]',
                  assignedAgentName ? '' : 'assignment-pill--unassigned'
                )}
                data-testid="assigned-agent-readonly"
              >
                {assignedAgentName ? `Assigned to ${assignedAgentName}` : 'Unassigned'}
              </span>
              )
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-9 px-2.5 rounded-full border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)]/70 flex items-center gap-1.5 text-[var(--tg-text-primary)] hover:text-[var(--tg-accent-strong)]"
              aria-label="Conversation details"
              onClick={handleProfileToggle}
            >
              <Info className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">{isProfileOpen ? 'Hide details' : 'Details'}</span>
            </Button>
          </div>
        </div>
        {/* Messages */}
        <div className="conversation-body space-y-1.5 chat-scroll" data-testid="messages-container" ref={messagesContainerRef}>
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
                const sentByName =
                  (msg.sent_by?.id && currentUser?.id === msg.sent_by.id
                    ? currentUser.name || currentUser.email
                    : msg.sent_by?.name || msg.sent_by?.email);
                let originLabel = '';
                if (showAsTicklegram) {
                  originLabel = `Sent from Ticklegram${sentByName ? ` - ${sentByName}` : ''}`;
                } else if (isInstagramPage) {
                  originLabel = 'Sent from Instagram app';
                } else if (sentByName) {
                  originLabel = `Sent by ${sentByName}`;
                }
                const attachments = Array.isArray(msg.attachments) ? msg.attachments : [];
                const templatePayload = extractTemplatePayload(attachments);
                const hasStoryMention = attachments.some(
                  (attachment) => attachment && typeof attachment === 'object' && attachment.type === 'story_mention'
                );
                const hasAttachments = attachments.length > 0 && !templatePayload;
                const placeholderText = (msg.content || '').trim().toLowerCase();
                const hideText = (hasAttachments || templatePayload) && (placeholderText === '[attachment]' || placeholderText === '');
                const displayText = hideText ? '' : msg.content;
                const phoneMatch = (() => {
                  if (!displayText) return null;
                  const match = displayText.match(/\+?\d[\d\s().-]{6,}\d/);
                  if (!match) return null;
                  const normalized = match[0].replace(/[^\d+]/g, '');
                  return normalized;
                })();
                const dayLabel = msg.timestamp ? formatMessageDay(msg.timestamp) : (msg.ts ? formatMessageDay(new Date(msg.ts * 1000).toISOString()) : '');
                const showDayLabel = dayLabel && dayLabel !== lastRenderedDay;
                if (showDayLabel) {
                  lastRenderedDay = dayLabel;
                }
                const replyMetadata = msg.metadata || {};
                const hasReplyContext = Boolean(replyMetadata.reply_to);

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
                          <div className="flex items-start gap-2">
                            <p className="text-sm whitespace-pre-line break-words flex-1">{displayText}</p>
                            {phoneMatch && (
                              <button
                                type="button"
                                onClick={() => {
                                  const normalizedMatch = phoneMatch.replace(/[^\d+]/g, '');
                                  const nameParts = splitFullName(chatDisplayName || '');
                                  setCreateInquiryPrefill({
                                    phone: normalizedMatch,
                                    notes: `Inquiry from chat ${chat?.id || ''}`,
                                    firstName: nameParts.first,
                                    middleName: nameParts.middle,
                                    lastName: nameParts.last,
                                    email:
                                      chat?.instagram_user?.email ||
                                      chat?.facebook_user?.email ||
                                      '',
                                    city: '',
                                    address: '',
                                  });
                                  setShowInquiryModal(true);
                                }}
                                className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[var(--tg-surface-muted)] text-[var(--tg-text-primary)] border border-[var(--tg-border-soft)] hover:bg-[var(--tg-chat-hover)] transition"
                                title="Create inquiry"
                              >
                                <PhoneCall className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        )}
                        {originLabel && (
                          <p className="text-[11px] text-purple-200/80 italic mt-1">
                            {originLabel}
                          </p>
                        )}
                        {hasStoryMention && (
                          <p className="message-origin italic mt-1 text-purple-200">
                            Story mention
                          </p>
                        )}
                        {attachments.length > 0 && (
                          <div className="mt-3 space-y-2">
                            {attachments.map((attachment, attachmentIndex) => {
                              const attachmentUrl = resolveAttachmentUrl(attachment);
                              if (attachment.type === 'image' && attachmentUrl) {
                                return (
                                  <img
                                    key={`${msg.id || 'msg'}-attachment-${attachmentIndex}`}
                                    src={attachmentUrl}
                                    alt={`attachment-${attachmentIndex + 1}`}
                                    className="max-h-64 w-full rounded-xl object-cover border border-white/10"
                                  />
                                );
                              }
                              if (!attachmentUrl) return null;
                              return (
                                <a
                                  key={`${msg.id || 'msg'}-attachment-${attachmentIndex}`}
                                  href={attachmentUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="block text-xs text-purple-200 underline break-all"
                                >
                                  View attachment
                                </a>
                              );
                            })}
                          </div>
                        )}
                        <p
                          className={`text-[11px] mt-2 ${
                            isAgentMessage ? 'text-purple-200' : 'text-gray-500'
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
          {show24hExpiryNotice && (
            <div className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              The 24-hour human agent window has expired. Send an approved template or wait for the user to reply.
            </div>
          )}
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {attachments.map((att, idx) => (
                <span key={`${att.payload?.url || idx}-${idx}`} className="attachment-chip">
                  {att.type}: {att.payload?.url || att.url}
                  <button
                    type="button"
                    className="attachment-chip-remove"
                    onClick={() =>
                      setAttachments((prev) => prev.filter((_, i) => i !== idx))
                    }
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          {replyTarget && (
            <div className="reply-preview">
              <div className="reply-preview-body">
                <p className="reply-preview-author">{replyTarget.author}</p>
                <p className="reply-preview-text">{replyTarget.snippet}</p>
              </div>
              <button
                type="button"
                className="reply-preview-cancel"
                onClick={handleCancelReply}
                aria-label="Cancel reply"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}
          <form onSubmit={handleSend} className="space-y-1">
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className={`composer-textarea ${isMobile ? 'min-h-[40px]' : 'min-h-[44px]'} text-sm resize-none`}
              data-testid="message-input"
              disabled={!canSendManualMessage}
              aria-disabled={!canSendManualMessage}
              placeholder={
                show24hExpiryNotice
                  ? '24-hour window expired. Use an approved template.'
                  : 'Type a reply, use / for shortcuts...'
              }
              rows={1}
              style={{ overflow: 'hidden' }}
              onInput={(e) => {
                const target = e.target;
                target.style.height = 'auto';
                target.style.height = `${Math.min(target.scrollHeight, 180)}px`;
              }}
            />
            <div className="flex flex-wrap items-center justify-between gap-1.5">
              <div className="composer-toolbar">
                <div className="relative inline-block" ref={emojiPopoverRef}>
                <Button
                  type="button"
                  onClick={() => setShowEmojiPicker((prev) => !prev)}
                  variant="ghost"
                  className={isMobile ? 'min-w-[36px] min-h-[36px]' : 'h-9 px-3'}
                  title="Insert emoji"
                >
                  <Smile className="w-4 h-4" />
                  <span className="hidden sm:inline text-sm">Emoji</span>
                </Button>
                {showEmojiPicker && (
                  <div className="emoji-popover">
                      {['😀','😃','😄','😁','😆','😅','😂','🙂','😉','😊','😍','😘','😎','🤩','🤔','🤝','👍','🙏','🔥','🎉','❤️','🚀','🌟','😴','🤖','🥳','🤝','📌','✅','❓','☕'].map((emoji) => (
                        <button
                          key={emoji}
                          type="button"
                          className="emoji-btn"
                          onClick={() => {
                            setMessage((prev) => `${prev}${emoji}`);
                            setShowEmojiPicker(false);
                          }}
                        >
                          {emoji}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {attachmentsEnabled && (
                  <Button
                    type="button"
                    onClick={() => setShowAttachmentForm((prev) => !prev)}
                    variant="ghost"
                    className={isMobile ? 'min-w-[36px] min-h-[36px]' : 'h-9 px-3'}
                    title="Add attachment (URL)"
                  >
                    <Paperclip className="w-4 h-4" />
                    <span className="hidden sm:inline text-sm">Attach</span>
                  </Button>
                )}
                <Button
                  type="button"
                  onClick={() => setShowTemplateDialog(true)}
                  variant="ghost"
                  className={isMobile ? 'min-w-[36px] min-h-[36px]' : 'h-9 px-3'}
                  title="Templates (Ctrl+T)"
                >
                  <FileText className="w-4 h-4" />
                  <span className="hidden sm:inline text-sm">Templates</span>
                </Button>
              </div>
              <Button
                type="submit"
                disabled={!message.trim() || isSending || !canSendManualMessage}
                className={`rounded-full px-4 h-9 bg-gradient-to-r from-indigo-500 to-blue-500 hover:from-indigo-600 hover:to-blue-600 ${
                  isMobile ? 'min-h-[36px]' : ''
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
          <DialogContent className="bg-[#1a1a2e] border-gray-700 text-white sm:max-w-[1024px] max-h-[80vh]">
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
                  {...AUTOFILL_PROPS}
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
                        (show24hExpiryNotice && !selectedTemplate?.is_meta_approved)
                      }
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Send Template
                    </Button>
                  </div>
                  {show24hExpiryNotice && !selectedTemplate?.is_meta_approved && (
                    <p className="text-xs text-amber-300 text-right">
                      Meta-approved templates are required outside the 24-hour window.
                    </p>
                  )}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
        <CreateInquiryModal
          isOpen={showInquiryModal}
          onClose={() => setShowInquiryModal(false)}
          onSubmit={() => setShowInquiryModal(false)}
          chat={chat}
          chatDisplayName={chatDisplayName}
          showAssignmentInfo={showAssignmentInfo}
          selectChat={selectChat}
          prefillData={createInquiryPrefill}
        />
      </div>
      {(isMobile || isTablet) && isProfileOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm">
          <div className="absolute inset-0" onClick={handleCloseProfile} role="presentation" />
          <div className="absolute inset-x-3 bottom-3 top-12 overflow-y-auto">
          <ChatProfilePanel
            chat={chat}
            orderedMessages={orderedMessages}
            onClose={handleCloseProfile}
            isMobile
            canSendManualMessage={canSendManualMessage}
            chatDisplayName={chatDisplayName}
            chatHandle={chatHandle}
            chatAvatarUrl={chatAvatarUrl}
            lastActivityLabel={lastActivityLabel}
            showAssignmentInfo={showAssignmentInfo}
          />
                </div>
                {attachmentsEnabled && showAttachmentForm && (
                  <div className="attachment-form">
                    <div className="flex flex-col gap-2">
                      <label className="text-xs text-[var(--tg-text-secondary)]">Attachment URL</label>
                <Input
                  {...AUTOFILL_PROPS}
                  value={attachmentUrl}
                  onChange={(e) => setAttachmentUrl(e.target.value)}
                  placeholder="https://example.com/image.jpg"
                  className="bg-[var(--tg-surface-muted)] border-[var(--tg-border-soft)]"
                />
                      <label className="text-xs text-[var(--tg-text-secondary)]">Type</label>
                      <select
                        value={attachmentType}
                        onChange={(e) => setAttachmentType(e.target.value)}
                        className="h-10 rounded-md bg-[var(--tg-surface-muted)] border border-[var(--tg-border-soft)] px-2 text-sm"
                      >
                        <option value="image">Image</option>
                        <option value="video">Video</option>
                        <option value="file">File</option>
                      </select>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => {
                            if (!attachmentUrl.trim()) return;
                            setAttachments((prev) => [
                              ...prev,
                              {
                                type: attachmentType,
                                payload: { url: attachmentUrl.trim() }
                              }
                            ]);
                            setAttachmentUrl('');
                            setShowAttachmentForm(false);
                          }}
                        >
                          Add
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setAttachmentUrl('');
                            setShowAttachmentForm(false);
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
      )}
      {!isMobile && !isTablet && (
        <aside
          className={cn(
            'flex-col h-full min-w-[280px] max-w-[340px] flex-shrink-0 transition-all duration-150',
            isProfileOpen ? 'hidden lg:flex opacity-100 translate-x-0' : 'hidden lg:hidden'
          )}
        >
          <ChatProfilePanel
            chat={chat}
            orderedMessages={orderedMessages}
            onClose={handleCloseProfile}
            isMobile={false}
            canSendManualMessage={canSendManualMessage}
            chatDisplayName={chatDisplayName}
            chatHandle={chatHandle}
            chatAvatarUrl={chatAvatarUrl}
            lastActivityLabel={lastActivityLabel}
            showAssignmentInfo={showAssignmentInfo}
          />
        </aside>
      )}
    </div>
  );
};

const ChatProfilePanel = ({
  chat,
  orderedMessages = [],
  onClose,
  isMobile,
  canSendManualMessage,
  chatDisplayName,
  chatHandle,
  chatAvatarUrl,
  lastActivityLabel,
  showAssignmentInfo = true,
}) => {
  const assignedAgent = chat.assigned_agent;
  const messageCount = orderedMessages.length;
  const lastMessage = messageCount > 0 ? orderedMessages[messageCount - 1] : null;

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
      label: 'Handle',
      value: `@${handle || 'unknown'}`,
    },
    ...(showAssignmentInfo
      ? [
          {
            label: 'Assigned Agent',
            value: assignedAgent?.name || 'Unassigned',
          },
          {
            label: 'Status',
            value: statusLabel,
          },
        ]
      : []),
    {
      label: 'Last Activity',
      value: lastActivityLabel || 'Not available',
    },
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
    ...(showAssignmentInfo && chat.instagram_user_id
      ? [
          {
            label: 'Instagram User ID',
            value: chat.instagram_user_id,
          },
        ]
      : []),
    ...(showAssignmentInfo && chat.facebook_page_id
      ? [
          {
            label: 'Facebook Page ID',
            value: chat.facebook_page_id,
          },
        ]
      : []),
    ...(showAssignmentInfo
      ? [
          {
            label: 'Chat ID',
            value: chat.id,
          },
          {
            label: 'Human Agent Window',
            value: canSendManualMessage ? 'Active (within 24 hours)' : 'Expired',
          },
        ]
      : []),
  ];

  return (
    <aside
      className={cn(
        'chat-panel bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] flex flex-col min-h-0',
        isMobile ? 'rounded-2xl' : 'h-full overflow-hidden'
      )}
    >
      <div className="p-2 border-b border-[var(--tg-border-soft)] flex items-start justify-between">
        <div className="flex items-center gap-2">
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
          <div className="min-w-0">
            <p className="text-[10px] uppercase text-[var(--tg-text-muted)] tracking-wide">Profile</p>
            <p className="text-base font-semibold text-[var(--tg-text-primary)] truncate">{displayName}</p>
            <p className="text-xs text-[var(--tg-text-muted)] truncate">@{handle || 'unknown'}</p>
            <div className="flex flex-wrap gap-2 mt-2">
              {showAssignmentInfo && <Badge className={statusBadgeClass}>{statusLabel}</Badge>}
              <Badge variant="outline" className="border-[var(--tg-border-soft)] text-[var(--tg-text-secondary)]">
                {platformLabel}
              </Badge>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)] transition-colors h-8 w-8 flex items-center justify-center rounded-full border border-transparent hover:border-[var(--tg-border-soft)]"
          aria-label="Close profile panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 chat-scroll">
        <div className="space-y-1.5">
          <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide">Conversation Info</p>
          <div className="grid grid-cols-2 gap-x-3 gap-y-2">
            {infoItems.map((item) => (
              <div key={item.label} className="flex flex-col gap-0.5">
                <span className="text-[10px] uppercase tracking-wide text-[var(--tg-text-muted)]">{item.label}</span>
                <span className="text-sm text-[var(--tg-text-primary)] break-all">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide">Last Message</p>
          {lastMessage ? (
            <div className="bg-[var(--tg-surface-muted)] border border-[var(--tg-border-soft)] rounded-lg p-2.5">
              <p className="text-sm text-[var(--tg-text-primary)] whitespace-pre-wrap">{lastMessage.content}</p>
              <p className="text-xs text-[var(--tg-text-muted)] mt-1.5">
                {lastMessage.timestamp ? formatMessageDate(lastMessage.timestamp) : ''}
              </p>
            </div>
          ) : (
            <p className="text-sm text-[var(--tg-text-muted)]">No messages yet</p>
          )}
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



