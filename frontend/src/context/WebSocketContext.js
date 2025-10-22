import React, { createContext, useContext, useEffect, useState } from 'react';
import useWebSocket from '../hooks/useWebSocket';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children, token }) => {
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useWebSocket(token);

  useEffect(() => {
    if (!token) {
      ws?.close();
      return;
    }

    const unsubscribe = ws?.subscribe((message) => {
      console.log('WebSocket message received:', message);
      setLastMessage(message);
    });

    return () => {
      unsubscribe?.();
    };
  }, [ws, token]);

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