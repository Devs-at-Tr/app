import { useEffect, useCallback, useRef } from 'react';

const useWebSocket = (token) => {
  // Use refs to maintain consistent references and persist values between renders
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const handlersRef = useRef([]);
  const isConnectingRef = useRef(false);

  // Create WebSocket connection
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
      return; // Already connected or connecting
    }

    isConnectingRef.current = true;
    const wsUrl = process.env.REACT_APP_BACKEND_URL || window.location.origin.replace('http', 'ws');
    const ws = new WebSocket(`${wsUrl}/ws?token=${token}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      isConnectingRef.current = false;
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      isConnectingRef.current = false;
      // Only attempt to reconnect if we haven't already scheduled a reconnection
      if (!reconnectTimerRef.current && wsRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          connect();
        }, 5000);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      isConnectingRef.current = false;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Notify all registered handlers
        handlersRef.current.forEach(handler => handler(data));
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    };

    wsRef.current = ws;
  }, [token]);

  // Subscribe to WebSocket messages
  const subscribe = useCallback((handler) => {
    handlersRef.current = [...handlersRef.current, handler];
    return () => {
      handlersRef.current = handlersRef.current.filter(h => h !== handler);
    };
  }, []);

  // Close WebSocket connection
  const close = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    handlersRef.current = [];
    isConnectingRef.current = false;
  }, []);

  // Automatically connect when component mounts and clean up on unmount
  useEffect(() => {
    if (token) {
      connect();
    }
    return () => close();
  }, [token, connect, close]);

  return {
    subscribe,
    close,
    connect,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN
  };
};

export default useWebSocket;