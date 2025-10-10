from fastapi import WebSocket
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket for a user"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"New WebSocket connection for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send a message to all connections for a user"""
        if user_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead in dead_connections:
                self.active_connections[user_id].discard(dead)
            
            if dead_connections:
                logger.info(f"Removed {len(dead_connections)} dead connections for user {user_id}")

    async def broadcast_to_users(self, user_ids: Set[str], message: dict):
        """Send a message to multiple users"""
        for user_id in user_ids:
            await self.broadcast_to_user(user_id, message)

# Global connection manager instance
manager = ConnectionManager()