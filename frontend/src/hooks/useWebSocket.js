import { useEffect, useCallback, useRef, useState } from 'react';

const useWebSocket = (token) => {
  // Use refs to maintain consistent references and persist values between renders
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const handlersRef = useRef([]);
  const isConnectingRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);

  // Create WebSocket connection
  const connect = useCallback(() => {
    if (!token) {
      console.log('No token available, skipping WebSocket connection');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
      console.log('WebSocket already connected or connecting');
      return;
    }

    isConnectingRef.current = true;
    
    try {
      // Clean up any existing connection
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // Use same backend URL as API but with WebSocket protocol
      const wsUrl = (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000').replace('http', 'ws');
      const newWs = new WebSocket(`${wsUrl}/messenger/ws?token=${token}`);
      wsRef.current = newWs;

      newWs.onopen = () => {
        console.log('WebSocket connected successfully');
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }
        isConnectingRef.current = false;
        setIsConnected(true);

        // Send periodic ping to keep connection alive
        const pingInterval = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000);
        wsRef.current.pingInterval = pingInterval;
      };

      newWs.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        isConnectingRef.current = false;
        setIsConnected(false);

        // Clear ping interval if it exists
        if (wsRef.current?.pingInterval) {
          clearInterval(wsRef.current.pingInterval);
        }

        // Define reconnection conditions
        const isNormalClosure = event.code === 1000; // Normal closure
        const isAuthFailure = event.code === 1008; // Policy violation (usually auth)
        const isCleanDisconnect = event.code === 1001; // Going away (page unload)
        
        // Only attempt to reconnect for unexpected closures and when we have a token
        const shouldReconnect = !isNormalClosure && !isAuthFailure && !isCleanDisconnect && token;
        
        // Clear any existing reconnection timer
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }
        
        if (shouldReconnect) {
          console.log('Scheduling WebSocket reconnection...');
          reconnectTimerRef.current = setTimeout(() => {
            console.log('Attempting to reconnect WebSocket...');
            reconnectTimerRef.current = null;
            connect();
          }, 5000);
        }
      };

      newWs.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnectingRef.current = false;
        setIsConnected(false);
      };

      // Set up message handler
      newWs.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handlersRef.current.forEach(handler => handler(data));
        } catch (error) {
          console.error('Error processing WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      isConnectingRef.current = false;
    }

    // ws.onmessage = (event) => {
    //   try {
    //     const data = JSON.parse(event.data);
    //     // Notify all registered handlers
    //     handlersRef.current.forEach(handler => handler(data));
    //   } catch (error) {
    //     console.error('Error processing WebSocket message:', error);
    //   }
    // };

    // wsRef.current = newWs;
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

  // Return the WebSocket interface
  return {
    subscribe,
    close,
    connect,
    isConnected,
    reconnect: () => {
      close();
      connect();
    }
  };
};

export default useWebSocket;