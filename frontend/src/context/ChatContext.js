import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import axios from 'axios';
import { API } from '../App';

const ChatContext = createContext(null);

const toTimestamp = (value) => {
  if (!value) {
    return null;
  }
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? null : time;
};

const getChatActivityTime = (chat) => {
  if (!chat) {
    return 0;
  }
  const candidates = [
    chat.last_message_timestamp,
    chat.updated_at,
    chat.created_at
  ];

  for (const candidate of candidates) {
    const timestamp = toTimestamp(candidate);
    if (timestamp !== null) {
      return timestamp;
    }
  }

  return 0;
};

const sortChatsByRecency = (chatList = []) =>
  [...chatList].sort((a, b) => getChatActivityTime(b) - getChatActivityTime(a));

export const ChatProvider = ({ children, userRole }) => {
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePlatform, setActivePlatform] = useState('all');
  const activePlatformRef = useRef('all');
  const loadChatsRef = useRef(null);
  const lastFiltersRef = useRef({});

  const updateChatMessages = useCallback((chatId, newMessage, options = {}) => {
    const { chatExists = true } = options;
    const sender = (newMessage.sender || '').toString().toLowerCase();
    const isAgentMessage = sender === 'agent' || sender === 'instagram_page';
    const isActiveChat = selectedChat?.id === chatId;

    setChats(currentChats =>
      chatExists
        ? sortChatsByRecency(
            currentChats.map(chat => {
              if (chat.id !== chatId) {
                return chat;
              }

              const existingMessages = chat.messages || [];
              const alreadyExists = existingMessages.some(message => message.id === newMessage.id);
              const nextMessages = alreadyExists ? existingMessages : [...existingMessages, newMessage];

              let unreadCount = chat.unread_count || 0;
              if (isAgentMessage) {
                unreadCount = 0;
              } else {
                if (isActiveChat) {
                  unreadCount = 0;
                } else if (!alreadyExists) {
                  unreadCount += 1;
                }
              }

              return {
                ...chat,
                messages: nextMessages,
                last_message: newMessage.content,
                last_message_timestamp: newMessage.timestamp || chat.last_message_timestamp,
                unread_count: unreadCount,
                status: isAgentMessage ? 'assigned' : chat.status
              };
            })
          )
        : sortChatsByRecency(currentChats)
    );

    setSelectedChat(currentChat => {
      if (currentChat?.id !== chatId) {
        return currentChat;
      }

      const existingMessages = currentChat.messages || [];
      const alreadyExists = existingMessages.some(message => message.id === newMessage.id);
      const nextMessages = alreadyExists ? existingMessages : [...existingMessages, newMessage];

      return {
        ...currentChat,
        messages: nextMessages,
        last_message: newMessage.content,
        last_message_timestamp: newMessage.timestamp || currentChat.last_message_timestamp,
        unread_count: 0,
        status: isAgentMessage ? 'assigned' : currentChat.status
      };
    });
  }, [selectedChat]);

  const loadChats = useCallback(async (platform = 'all', filters = {}) => {
    setLoading(true);
    setError(null);
    activePlatformRef.current = platform;
    lastFiltersRef.current = filters || {};
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };
      const chatParams = {};
      if (platform !== 'all') {
        chatParams.platform = platform;
      }
      if (filters) {
        if (filters.unseen !== undefined) {
          chatParams.unseen = filters.unseen;
        }
        if (filters.not_replied !== undefined) {
          chatParams.not_replied = filters.not_replied;
        }
        if (filters.assigned_to) {
          chatParams.assigned_to = filters.assigned_to;
        }
      }
      
      const response = await axios.get(`${API}/chats`, { 
        headers, 
        params: chatParams,
        timeout: 30000
      });
      
      if (!Array.isArray(response.data)) {
        throw new Error('Invalid response format from server');
      }
      
      const chatsData = response.data || [];
      setChats(sortChatsByRecency(chatsData));
      setActivePlatform(platform);
      activePlatformRef.current = platform; // Update ref
      setSelectedChat((currentChat) => {
        if (!currentChat) {
          return null;
        }
        const refreshed = chatsData.find(chat => chat.id === currentChat.id);
        if (!refreshed) {
          return currentChat;
        }
        return {
          ...currentChat,
          ...refreshed,
          messages: currentChat.messages || [],
        };
      });
      return chatsData;
    } catch (error) {
      console.error('Error loading chats:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to load chats';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Store loadChats in ref for use in handleWebSocketMessage
  loadChatsRef.current = loadChats;

  const selectChat = useCallback(async (chatId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };
      
      const response = await axios.get(`${API}/chats/${chatId}`, { headers });
      
      // Validate and normalize the chat data
      const chatData = response.data;
      if (chatData.messages) {
        chatData.messages = chatData.messages.map(msg => ({
          ...msg,
          timestamp: msg.timestamp ? new Date(msg.timestamp).toISOString() : new Date().toISOString()
        }));
      }
      
      setSelectedChat(chatData);
      return chatData;
    } catch (error) {
      console.error('Error selecting chat:', error);
      setError(error.response?.data?.detail || error.message || 'Failed to load chat');
      throw error;
    }
  }, []);

  const sendMessage = useCallback(async (chatId, content, options = {}) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };
      const payload = { content };
      if (options.replyTo?.id) {
        payload.reply_to_message_id = options.replyTo.id;
        if (options.replyTo.preview) {
          payload.reply_preview = options.replyTo.preview;
        }
      }
      if (options.attachments?.length) {
        payload.attachments = options.attachments;
      }
      const response = await axios.post(
        `${API}/chats/${chatId}/message`,
        payload,
        { headers }
      );

      const newMessage = response.data;
      updateChatMessages(chatId, newMessage);
      
      try {
        await axios.post(`${API}/chats/${chatId}/mark_read`, {}, { headers });
      } catch (markReadError) {
        console.warn('Failed to mark messages as read after sending:', markReadError);
      }
      
      return newMessage;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }, [updateChatMessages]);

  const handleWebSocketMessage = useCallback((data) => {
    if (data.type === 'new_message') {
      // Use functional updates to avoid dependencies on chats
      setChats(currentChats => {
        const chatExists = currentChats.some(chat => chat.id === data.chat_id);
        
        if (!chatExists) {
          // If chat doesn't exist, we need to reload
          // Use setTimeout to avoid state update during render
          setTimeout(() => {
            if (loadChatsRef.current) {
              loadChatsRef.current(activePlatformRef.current, lastFiltersRef.current);
            }
          }, 0);
          return currentChats;
        }
        
        // Chat exists, update it
        const sender = (data.message.sender || '').toString().toLowerCase();
        const isAgentMessage = sender === 'agent' || sender === 'instagram_page';
        
        return sortChatsByRecency(
          currentChats.map(chat => {
            if (chat.id !== data.chat_id) {
              return chat;
            }

            const existingMessages = chat.messages || [];
            const alreadyExists = existingMessages.some(message => message.id === data.message.id);
            const nextMessages = alreadyExists ? existingMessages : [...existingMessages, data.message];

            let unreadCount = chat.unread_count || 0;
            if (isAgentMessage) {
              unreadCount = 0;
            } else {
              // Only increment if not already exists and not viewing this chat
              if (!alreadyExists) {
                unreadCount += 1;
              }
            }

            return {
              ...chat,
              messages: nextMessages,
              last_message: data.message.content,
              last_message_timestamp: data.message.timestamp || chat.last_message_timestamp,
              unread_count: unreadCount,
              status: isAgentMessage ? 'assigned' : chat.status
            };
          })
        );
      });
      
      // Update selected chat if it's the one receiving the message
      setSelectedChat(currentChat => {
        if (currentChat?.id !== data.chat_id) {
          return currentChat;
        }

        const existingMessages = currentChat.messages || [];
        const alreadyExists = existingMessages.some(message => message.id === data.message.id);
        const nextMessages = alreadyExists ? existingMessages : [...existingMessages, data.message];

        return {
          ...currentChat,
          messages: nextMessages,
          last_message: data.message.content,
          last_message_timestamp: data.message.timestamp || currentChat.last_message_timestamp,
          unread_count: 0,
            status: (data.message.sender === 'agent' || data.message.sender === 'instagram_page')
              ? 'assigned'
              : currentChat.status
        };
      });
    }
  }, []);

  const value = {
    chats,
    selectedChat,
    loading,
    error,
    activePlatform,
    loadChats,
    selectChat,
    sendMessage,
    handleWebSocketMessage,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
};
