import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useChatContext } from '../context/ChatContext';
import { formatMessageTime } from '../utils/dateUtils';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Send, UserPlus, Instagram } from 'lucide-react';
import './ChatWindow.css';

const FacebookIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const ChatWindow = ({ agents, userRole }) => {
  const { selectedChat: chat, sendMessage } = useChatContext();
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [chat?.messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = useCallback(async (e) => {
    e.preventDefault();
    if (!chat || !message.trim() || isSending) {
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
  }, [message, chat, sendMessage, isSending]);

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
    <div className="bg-[#1a1a2e] border border-gray-800 rounded-xl h-full w-full flex flex-col min-h-0" data-testid="chat-window">
      {/* Chat Header */}
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
            chat.platform === 'FACEBOOK' 
              ? 'bg-gradient-to-br from-blue-600 to-blue-700' 
              : 'bg-gradient-to-br from-purple-600 to-pink-600'
          }`}>
            {chat.platform === 'FACEBOOK' ? (
              <FacebookIcon className="w-5 h-5 text-white" />
            ) : (
              <Instagram className="w-5 h-5 text-white" />
            )}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-white font-bold" data-testid="chat-username">@{chat.username}</h3>
              <span className={`px-2 py-0.5 text-xs rounded-full ${
                chat.platform === 'FACEBOOK'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-pink-500/20 text-pink-400'
              }`}>
                {chat.platform === 'FACEBOOK' ? 'Facebook' : 'Instagram'}
              </span>
            </div>
            <p className="text-xs text-gray-400" data-testid="chat-instagram-id">{chat.instagram_user_id}</p>
          </div>
        </div>

        {userRole === 'admin' && (
          <div className="flex items-center space-x-2">
            <Select
              value={chat.assigned_to || 'unassigned'}
              onValueChange={(value) => onAssignChat(chat.id, value === 'unassigned' ? null : value)}
            >
              <SelectTrigger className="w-[200px] bg-[#0f0f1a] border-gray-700 text-white" data-testid="assign-agent-select">
                <UserPlus className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Assign Agent" />
              </SelectTrigger>
              <SelectContent className="bg-[#1a1a2e] border-gray-700">
                <SelectItem value="unassigned" className="text-white">Unassign</SelectItem>
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
          <div className="text-center text-gray-500 mt-8">
            No messages yet
          </div>
        ) : (
          chat.messages?.map((msg) => (
            <div
              key={msg.id}
              className={`message-bubble flex ${
                msg.sender === 'agent' ? 'justify-end' : 'justify-start'
              }`}
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
                <p
                  className={`text-xs mt-1 ${
                    msg.sender === 'agent' ? 'text-purple-200' : 'text-gray-500'
                  }`}
                >
                  {formatMessageTime(msg.timestamp)}
                </p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <div className="p-4 border-t border-gray-800">
        <form onSubmit={handleSend} className="flex space-x-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500"
            data-testid="message-input"
          />
          <Button
            type="submit"
            disabled={!message.trim() || isSending}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            data-testid="send-message-button"
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
};

const MessageSquareIcon = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);

export default ChatWindow;
