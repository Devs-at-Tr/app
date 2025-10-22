// WebSocket singleton instance for the application
let wsInstance = null;

// Initialize WebSocket with a token
export const initializeWebSocket = (token) => {
    if (wsInstance) {
        return wsInstance;
    }

    const apiUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
    // Convert http/https to ws/wss
    const wsUrl = apiUrl.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsUrl}/ws?token=${token}`);
    
    // Track connection status
    let isConnecting = false;
    let reconnectTimer = null;
    const messageHandlers = new Set();

    const cleanup = () => {
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        messageHandlers.clear();
    };

    ws.onopen = () => {
        console.log('WebSocket connected');
        isConnecting = false;
        cleanup();
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        isConnecting = false;
        wsInstance = null; // Clear instance on disconnection
        
        // Only attempt to reconnect if we haven't scheduled a reconnection
        if (!reconnectTimer && !isConnecting) {
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                if (!wsInstance) {
                    initializeWebSocket(token);
                }
            }, 5000);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnecting = false;
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            // Notify all registered handlers
            messageHandlers.forEach(handler => handler(data));
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    };

    // Add methods to the WebSocket instance
    ws.subscribe = (handler) => {
        messageHandlers.add(handler);
        return () => messageHandlers.delete(handler);
    };

    ws.cleanup = cleanup;

    wsInstance = ws;
    return ws;
};

export const getWebSocket = () => wsInstance;

export const subscribeToMessages = (handler) => {
    const ws = wsInstance;
    if (!ws) {
        console.warn('Attempting to subscribe without an active WebSocket connection');
        return () => {};
    }
    return ws.subscribe(handler);
};

export const closeWebSocket = () => {
    if (wsInstance) {
        wsInstance.cleanup();
        wsInstance.close();
        wsInstance = null;
    }
};