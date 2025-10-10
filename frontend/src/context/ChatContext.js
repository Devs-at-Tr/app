import React, { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';

const ChatContext = createContext(null);

export const ChatProvider = ({ children, userRole }) => {
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePlatform, setActivePlatform] = useState('all');

  const updateChatMessages = useCallback((chatId, newMessage) => {
    setChats(currentChats =>
      currentChats.map(chat => {
        if (chat.id !== chatId) {
          return chat;
        }

        const existingMessages = chat.messages || [];
        if (existingMessages.some(message => message.id === newMessage.id)) {
          return chat;
        }

        return {
          ...chat,
          messages: [...existingMessages, newMessage],
          last_message: newMessage.content,
          last_message_timestamp: newMessage.timestamp
        };
      })
    );

    setSelectedChat(currentChat => {
      if (currentChat?.id !== chatId) {
        return currentChat;
      }

      const existingMessages = currentChat.messages || [];
      if (existingMessages.some(message => message.id === newMessage.id)) {
        return currentChat;
      }

      return {
        ...currentChat,
        messages: [...existingMessages, newMessage]
      };
    });
  }, []);

  const loadChats = useCallback(async (platform = 'all') => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };
      const chatParams = platform !== 'all' ? { platform } : {};
      
      const response = await axios.get(`${API}/chats`, { 
        headers, 
        params: chatParams,
        timeout: 30000
      });
      
      if (!Array.isArray(response.data)) {
        throw new Error('Invalid response format from server');
      }
      
      const chatsData = response.data || [];
      setChats(chatsData);
      setActivePlatform(platform);
      setSelectedChat((currentChat) => {
        if (!currentChat) {
          return null;
        }
        return chatsData.find(chat => chat.id === currentChat.id) || null;
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

  const selectChat = useCallback(async (chatId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };
      
      // First check if the chat exists in our current list
      const existingChat = chats.find(chat => chat.id === chatId);
      if (!existingChat) {
        console.warn('Chat not found in current list, refreshing chats...');
        await loadChats();
      }
      
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

      try {
        // Mark messages as read - don't fail if this fails
        await axios.post(`${API}/chats/${chatId}/mark_read`, {}, { headers });
        
        // Update unread count in chat list
        setChats(currentChats =>
          currentChats.map(chat =>
            chat.id === chatId
              ? { ...chat, unread_count: 0 }
              : chat
          )
        );
      } catch (markReadError) {
        console.warn('Failed to mark messages as read:', markReadError);
        // Continue anyway since we at least got the chat data
      }

      return response.data;
    } catch (error) {
      console.error('Error selecting chat:', error);
      setError(error.response?.data?.detail || error.message || 'Failed to load chat');
      throw error;
    }
  }, []);

  const sendMessage = useCallback(async (chatId, content) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.post(
        `${API}/chats/${chatId}/message`,
        { content },
        { headers }
      );

      const newMessage = response.data;
      updateChatMessages(chatId, newMessage);
      
      return newMessage;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }, [updateChatMessages]);

  const handleWebSocketMessage = useCallback((data) => {
    if (data.type === 'new_message') {
      updateChatMessages(data.chat_id, data.message);
    }
  }, [updateChatMessages]);

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
