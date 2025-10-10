import httpx
import hmac
import hashlib
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

class FacebookMode(str, Enum):
    MOCK = "mock"
    REAL = "real"

class FacebookMessengerClient:
    """Client for Facebook Messenger API with mock/real mode support"""
    
    BASE_URL = "https://graph.facebook.com/v23.0"
    
    def __init__(self, mode: FacebookMode = None):
        self.mode = mode or FacebookMode(os.getenv("FACEBOOK_MODE", "mock"))
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET", "")
        self.verify_token = os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "ticklegram_fb_verify")
        self.timeout = int(os.getenv("FACEBOOK_WEBHOOK_TIMEOUT", "30"))
        
        if self.mode == FacebookMode.REAL:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )
            logger.info("Facebook Messenger Client initialized in REAL mode")
        else:
            self.client = None
            logger.info("Facebook Messenger Client initialized in MOCK mode")
    
    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256"""
        if self.mode == FacebookMode.MOCK:
            logger.info("MOCK MODE: Skipping webhook signature verification")
            return True
        
        if not signature:
            logger.error("No signature provided in webhook request")
            return False
        
        try:
            # Remove 'sha256=' or 'sha1=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
                hash_object = hmac.new(
                    self.app_secret.encode('utf-8'),
                    payload,
                    hashlib.sha256
                )
            elif signature.startswith('sha1='):
                signature = signature[5:]
                hash_object = hmac.new(
                    self.app_secret.encode('utf-8'),
                    payload,
                    hashlib.sha1
                )
            else:
                hash_object = hmac.new(
                    self.app_secret.encode('utf-8'),
                    payload,
                    hashlib.sha256
                )
            
            expected_signature = hash_object.hexdigest()
            return hmac.compare_digest(expected_signature, signature)
        
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def verify_webhook_token(self, hub_mode: str, hub_verify_token: str) -> bool:
        """Verify webhook setup token"""
        logger.info("Verifying webhook token")
        logger.info(f"Expected verify token: {self.verify_token}, Received: {hub_verify_token}")
        return hub_mode == "subscribe" and hub_verify_token == self.verify_token
    
    async def send_text_message(
        self,
        page_access_token: str,
        recipient_id: str,
        text: str
    ) -> Dict[str, Any]:
        """Send a text message to a user"""
        
        if self.mode == FacebookMode.MOCK:
            logger.info(f"MOCK MODE: Sending text message to {recipient_id}: {text}")
            return {
                "success": True,
                "recipient_id": recipient_id,
                "message_id": f"mock_fb_msg_{datetime.now().timestamp()}",
                "mode": "mock"
            }
        
        # Real Facebook API call
        url = f"{self.BASE_URL}/me/messages"
        
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
            "access_token": page_access_token
        }
        
        try:
            response = await self.client.post(url, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    "success": True,
                    "recipient_id": response_data.get("recipient_id"),
                    "message_id": response_data.get("message_id"),
                    "mode": "real"
                }
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to send Facebook message: {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "error_code": response.status_code,
                    "mode": "real"
                }
        
        except Exception as e:
            logger.error(f"Error sending Facebook message: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "real"
            }
    
    async def send_attachment(
        self,
        page_access_token: str,
        recipient_id: str,
        attachment_type: str,
        attachment_url: str
    ) -> Dict[str, Any]:
        """Send an attachment to a user"""
        
        if self.mode == FacebookMode.MOCK:
            logger.info(f"MOCK MODE: Sending {attachment_type} attachment to {recipient_id}")
            return {
                "success": True,
                "recipient_id": recipient_id,
                "message_id": f"mock_fb_attachment_{datetime.now().timestamp()}",
                "mode": "mock"
            }
        
        # Real Facebook API call
        url = f"{self.BASE_URL}/me/messages"
        
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {
                "attachment": {
                    "type": attachment_type,
                    "payload": {
                        "url": attachment_url,
                        "is_reusable": True
                    }
                }
            },
            "access_token": page_access_token
        }
        
        try:
            response = await self.client.post(url, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    "success": True,
                    "recipient_id": response_data.get("recipient_id"),
                    "message_id": response_data.get("message_id"),
                    "mode": "real"
                }
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to send Facebook attachment: {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "error_code": response.status_code,
                    "mode": "real"
                }
        
        except Exception as e:
            logger.error(f"Error sending Facebook attachment: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "real"
            }
    
    async def process_webhook_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_data: Dict[str, Any],
        page_id: str
    ) -> Dict[str, Any]:
        """Process incoming webhook message"""
        
        message_text = message_data.get("text", "")
        message_id = message_data.get("mid", "")
        attachments = message_data.get("attachments", [])
        
        logger.info(f"Processing Facebook message from {sender_id} on page {page_id}")
        
        return {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "page_id": page_id,
            "message_id": message_id,
            "text": message_text,
            "has_attachments": len(attachments) > 0,
            "attachments": attachments,
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def get_user_profile(
        self,
        page_access_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user profile information"""
        
        if self.mode == FacebookMode.MOCK:
            logger.info(f"MOCK MODE: Getting profile for user {user_id}")
            return {
                "success": True,
                "id": user_id,
                "name": f"Mock User {user_id[:8]}",
                "profile_pic": f"https://via.placeholder.com/150?text={user_id[:8]}",
                "mode": "mock"
            }
        
        # Real Facebook API call
        url = f"{self.BASE_URL}/{user_id}"
        
        try:
            response = await self.client.get(
                url,
                params={
                    "fields": "id,name,profile_pic",
                    "access_token": page_access_token
                }
            )
            
            if response.status_code == 200:
                profile_data = response.json()
                return {
                    "success": True,
                    **profile_data,
                    "mode": "real"
                }
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to get Facebook user profile: {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "mode": "real"
                }
        
        except Exception as e:
            logger.error(f"Error getting Facebook user profile: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "real"
            }

# Global Facebook client instance
facebook_client = FacebookMessengerClient()
