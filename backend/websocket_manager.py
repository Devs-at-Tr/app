from fastapi import WebSocket
from typing import Dict, Set, Deque
import logging
from collections import deque

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self, max_queue_size: int = 100):
        # Store connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.pending_messages: Dict[str, Deque[dict]] = {}
        self.max_queue_size = max_queue_size

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket for a user"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"New WebSocket connection for user {user_id}")

        # Flush any pending messages for this user
        if user_id in self.pending_messages:
            queued_messages = list(self.pending_messages.pop(user_id))
            for message in queued_messages:
                try:
                    queued_payload = dict(message)
                    queued_payload.setdefault("queued", True)
                    await websocket.send_json(queued_payload)
                except Exception as exc:
                    logger.error(f"Error sending queued WebSocket message to user {user_id}: {exc}")
                    # Re-queue the message if sending fails
                    self._queue_message(user_id, message)
                    break

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send a message to all connections for a user"""
        connections = self.active_connections.get(user_id)
        if connections:
            dead_connections = set()
            delivered = False
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                    delivered = True
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead in dead_connections:
                self.active_connections[user_id].discard(dead)
            
            if dead_connections:
                logger.info(f"Removed {len(dead_connections)} dead connections for user {user_id}")
            
            if not delivered:
                self._queue_message(user_id, message)
        else:
            self._queue_message(user_id, message)

    async def broadcast_to_users(self, user_ids: Set[str], message: dict):
        """Send a message to multiple users"""
        for user_id in user_ids:
            await self.broadcast_to_user(user_id, message)

    async def broadcast_global(self, message: dict):
        """Send a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.broadcast_to_user(user_id, message)

    def _queue_message(self, user_id: str, message: dict):
        """Queue message for delivery when user reconnects."""
        if user_id not in self.pending_messages:
            self.pending_messages[user_id] = deque(maxlen=self.max_queue_size)
        queue = self.pending_messages[user_id]
        if len(queue) == queue.maxlen:
            queue.popleft()
        queue.append(message)
        logger.debug(f"Queued message for user {user_id}; queue length now {len(queue)}")

# Global connection manager instance
manager = ConnectionManager()
