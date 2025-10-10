import React, { createContext, useContext, useEffect, useState } from 'react';
import useWebSocket from '../hooks/useWebSocket';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children, token }) => {
  const ws = useWebSocket(token);
  const [lastMessage, setLastMessage] = useState(null);

  useEffect(() => {
    if (ws) {
      return ws.subscribe((message) => {
        setLastMessage(message);
      });
    }
  }, [ws]);

  return (
    <WebSocketContext.Provider value={{ ws, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};