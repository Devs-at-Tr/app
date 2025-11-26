import httpx
import hmac
import hashlib
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from utils.timezone import utc_now
from enum import Enum

GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v18.0")

logger = logging.getLogger(__name__)

class FacebookMode(str, Enum):
    MOCK = "mock"
    REAL = "real"

class FacebookMessengerClient:
    """Client for Facebook Messenger API with mock/real mode support"""
    
    BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

    async def get_page_feed_with_comments(self, page_access_token: str, page_id: str) -> List[Dict[str, Any]]:
        """Get page feed with comments in a single batch request"""
        if self.mode == FacebookMode.MOCK:
            return []
        
        logger.info(f"Fetching feed with comments for page {page_id}")
        
        try:
            # First get the page feed with embedded comments
            url = f"{self.BASE_URL}/{page_id}/feed"
            params = {
                "access_token": page_access_token,
                "fields": (
                    "id,message,created_time,permalink_url,full_picture,"
                    "comments.limit(25){id,message,created_time,from{id,name,picture{url}},"
                    "attachment,comments.limit(25){id,message,created_time,from{id,name,picture{url}},attachment},"
                    "reactions.summary(total_count)},reactions.summary(total_count)"
                ),
                "limit": 25  # Reduced for faster loading
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Facebook API Response: {data}")  # Log the full response
            
            if not data.get("data"):
                logger.warning(f"No posts found for page {page_id}")
                return []

            comments = []
            for post in data.get("data", []):
                # Get comments from the post
                post_comments = post.get("comments", {}).get("data", [])
                
                # Process each comment
                for comment in post_comments:
                    try:
                        # Get user profile picture URL
                        profile_pic = comment.get("from", {}).get("picture", {}).get("data", {}).get("url")
                        
                        # Process comment replies
                        replies = []
                        for reply in comment.get("comments", {}).get("data", []):
                            reply_profile_pic = reply.get("from", {}).get("picture", {}).get("data", {}).get("url")
                            replies.append({
                                "id": reply["id"],
                                "text": reply.get("message", ""),
                                "timestamp": reply["created_time"],
                                "username": reply.get("from", {}).get("name", "Unknown"),
                                "profile_pic_url": reply_profile_pic,
                                "media_url": reply.get("attachment", {}).get("media", {}).get("image", {}).get("src")
                            })

                        # Create comment data
                        comment_data = {
                            "id": comment["id"],
                            "text": comment.get("message", ""),
                            "timestamp": comment["created_time"],
                            "username": comment.get("from", {}).get("name", "Unknown"),
                            "profile_pic_url": profile_pic,
                            "replies": replies,
                            "media_url": comment.get("attachment", {}).get("media", {}).get("image", {}).get("src"),
                            "reaction_count": comment.get("reactions", {}).get("summary", {}).get("total_count", 0),
                            "post": {
                                "id": post["id"],
                                "caption": post.get("message", ""),
                                "timestamp": post["created_time"],
                                "permalink": post["permalink_url"],
                                "media_url": post.get("full_picture"),
                                "media_type": "IMAGE" if post.get("full_picture") else "STATUS"
                            }
                        }
                        comments.append(comment_data)
                    except Exception as e:
                        logger.error(f"Error processing comment: {str(e)}")
                        continue

            logger.info(f"Successfully fetched {len(comments)} comments for page {page_id}")
            return comments

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching page feed: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Facebook API error: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching page feed: {str(e)}")
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching page feed with comments: {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")
    
    def __init__(self, mode: FacebookMode = None):
        self.mode = mode or FacebookMode(os.getenv("FACEBOOK_MODE", "mock"))
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET", "")
        self.verify_token = os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "ticklegram_fb_verify")
        self.timeout = int(os.getenv("FACEBOOK_WEBHOOK_TIMEOUT", "30"))
        
        # Always create HTTP client regardless of mode
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        logger.info(f"Facebook Messenger Client initialized in {self.mode} mode")
    
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
        text: str,
        reply_to_mid: Optional[str] = None
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
        if reply_to_mid:
            payload["message"]["reply_to"] = {"mid": reply_to_mid}
        
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

    async def get_page_posts(self, page_access_token: str, page_id: str) -> List[Dict[str, Any]]:
        """Get posts from a Facebook page"""
        if self.mode == FacebookMode.MOCK:
            return []
        
        url = f"{self.BASE_URL}/{page_id}/feed"  # Use feed instead of posts to get all types of posts
        params = {
            "access_token": page_access_token,
            "fields": "id,message,created_time,permalink_url,full_picture,attachments{media_type,url,title,description},likes.summary(true),comments.summary(true)",
            "limit": 100
        }
        
        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("data", [])
                return [{
                    "id": post["id"],
                    "caption": post.get("message", ""),
                    "timestamp": post["created_time"],
                    "permalink": post["permalink_url"],
                    "media_type": post.get("attachments", {}).get("data", [{}])[0].get("media_type", "STATUS"),
                    "media_url": post.get("full_picture") or post.get("attachments", {}).get("data", [{}])[0].get("url"),
                    "like_count": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                    "comment_count": post.get("comments", {}).get("summary", {}).get("total_count", 0)
                } for post in data]
            else:
                logger.error(f"Failed to fetch Facebook posts: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching Facebook posts: {e}")
            return []

    async def get_post_comments(self, page_access_token: str, post_id: str) -> List[Dict[str, Any]]:
        """Get comments on a Facebook post"""
        if self.mode == FacebookMode.MOCK:
            return []
        
        url = f"{self.BASE_URL}/{post_id}/comments"
        params = {
            "access_token": page_access_token,
            "fields": "id,message,created_time,from{id,name,picture},comment_count,permalink_url,attachment,reactions.summary(total_count),comments.summary(total_count)",
            "limit": 100,
            "filter": "toplevel",  # Get only top-level comments first
            "order": "reverse_chronological"  # Get newest first
        }
        
        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("data", [])
                comments = []
                for comment in data:
                    # Get user profile picture URL from the from.picture field
                    profile_pic_url = None
                    try:
                        profile_pic_url = comment.get("from", {}).get("picture", {}).get("data", {}).get("url")
                    except Exception:
                        pass

                    comment_data = {
                        "id": comment["id"],
                        "text": comment.get("message", ""),
                        "timestamp": comment["created_time"],
                        "username": comment.get("from", {}).get("name", "Unknown"),
                        "profile_pic": profile_pic_url,
                        "replies": [],
                        "permalink": comment.get("permalink_url"),
                        "reaction_count": comment.get("reactions", {}).get("summary", {}).get("total_count", 0),
                        "media_url": comment.get("attachment", {}).get("media", {}).get("image", {}).get("src"),
                        "comment_count": comment.get("comments", {}).get("summary", {}).get("total_count", 0)
                    }
                    
                    # Fetch replies if this comment has any
                    if comment_data["comment_count"] > 0:
                        replies = await self.get_comment_replies(page_access_token, comment["id"])
                        comment_data["replies"] = replies
                    
                    comments.append(comment_data)
                
                return comments
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to fetch Facebook comments: {error_message}")
                return []
        except Exception as e:
            logger.error(f"Error fetching Facebook comments: {e}")
            return []

    async def get_comment_replies(self, page_access_token: str, comment_id: str) -> List[Dict[str, Any]]:
        """Get replies to a Facebook comment"""
        if self.mode == FacebookMode.MOCK:
            return []
        
        url = f"{self.BASE_URL}/{comment_id}/comments"
        params = {
            "access_token": page_access_token,
            "fields": "id,message,created_time,from{id,name,picture}",
            "limit": 100
        }
        
        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("data", [])
                return [{
                    "id": reply["id"],
                    "text": reply.get("message", ""),
                    "timestamp": reply["created_time"],
                    "username": reply.get("from", {}).get("name", "Unknown"),
                    "profile_pic_url": reply.get("from", {}).get("picture", {}).get("data", {}).get("url")
                } for reply in data]
            else:
                logger.error(f"Failed to fetch Facebook comment replies: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching Facebook comment replies: {e}")
            return []

    async def reply_to_comment(self, page_access_token: str, comment_id: str, message: str) -> Dict[str, Any]:
        """Reply to a Facebook comment"""
        if self.mode == FacebookMode.MOCK:
            return {
                "success": True,
                "comment_id": f"mock_reply_{datetime.now().timestamp()}",
                "mode": "mock"
            }
        
        url = f"{self.BASE_URL}/{comment_id}/comments"
        payload = {
            "message": message,
            "access_token": page_access_token
        }
        
        try:
            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "comment_id": data.get("id"),
                    "mode": "real"
                }
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to reply to Facebook comment: {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "mode": "real"
                }
        except Exception as e:
            logger.error(f"Error replying to Facebook comment: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "real"
            }

    async def send_template_message(
        self,
        page_access_token: str,
        recipient_id: str,
        text: str,
        template_id: Optional[str] = None,
        tag: str = "ACCOUNT_UPDATE",
        reply_to_mid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a tagged/template message outside the standard 24-hour window"""

        if self.mode == FacebookMode.MOCK:
            logger.info(
                "MOCK MODE: Sending Facebook template message to %s (template_id=%s, tag=%s): %s",
                recipient_id,
                template_id,
                tag,
                text
            )
            return {
                "success": True,
                "recipient_id": recipient_id,
                "message_id": f"mock_fb_template_{datetime.now().timestamp()}",
                "mode": "mock"
            }

        url = f"{self.BASE_URL}/me/messages"

        message_payload: Dict[str, Any] = {}
        if template_id:
            message_payload["message_creative_id"] = template_id
        else:
            message_payload["text"] = text
        if reply_to_mid:
            message_payload["reply_to"] = {"mid": reply_to_mid}

        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "MESSAGE_TAG",
            "tag": tag,
            "message": message_payload,
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

            error_data = response.json() if response.content else {}
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            logger.error(f"Failed to send Facebook template message: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "error_code": response.status_code,
                "mode": "real"
            }

        except Exception as exc:
            logger.error(f"Error sending Facebook template message: {exc}")
            return {
                "success": False,
                "error": str(exc),
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
            "timestamp": utc_now()
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
                "profile_pic_url": f"https://via.placeholder.com/150?text={user_id[:8]}",
                "mode": "mock"
            }
        
        # Real Facebook API call
        url = f"{self.BASE_URL}/{user_id}"
        
        params = {
            "fields": "id,name,first_name,last_name,profile_pic,profile_pic_url",
            "access_token": page_access_token
        }
        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                profile_data = response.json()

                first_name = (profile_data.get("first_name") or "").strip()
                last_name = (profile_data.get("last_name") or "").strip()
                full_name = profile_data.get("name") or " ".join(part for part in [first_name, last_name] if part).strip()
                if not full_name:
                    full_name = f"Facebook User {user_id[:8]}"

                return {
                    "success": True,
                    "id": profile_data.get("id", user_id),
                    "name": full_name,
                    "first_name": first_name or None,
                    "last_name": last_name or None,
                    "profile_pic": profile_data.get("profile_pic") or profile_data.get("profile_pic_url"),
                    "raw": profile_data,
                    "mode": "real"
                }

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
