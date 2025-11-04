import httpx
import hmac
import hashlib
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class InstagramMode(str, Enum):
    MOCK = "mock"
    REAL = "real"

class InstagramClient:
    """Client for Instagram Graph API with mock/real mode support"""
    
    def __init__(self, mode: InstagramMode = None):
        self.mode = mode or InstagramMode(os.getenv("INSTAGRAM_MODE", "mock"))
        graph_version = os.getenv("GRAPH_VERSION", "v18.0")
        self.BASE_URL = f"https://graph.facebook.com/{graph_version}"
        self.skip_signature_check = os.getenv("INSTAGRAM_SKIP_SIGNATURE", "false").lower() in {"1", "true", "yes"}
        self.hmac_debug = os.getenv("INSTAGRAM_HMAC_DEBUG", "false").lower() in {"1", "true", "yes"}
        
        # Use Facebook app secret for both Facebook and Instagram since they're the same app
        self.app_secret = os.getenv("INSTAGRAM_APP_SECRET") or os.getenv("FACEBOOK_APP_SECRET", "")
        self.app_secret_alt = os.getenv("INSTAGRAM_APP_SECRET_ALT", "")
        if not self.app_secret:
            logger.warning("No app secret found in environment variables")
            
        if self.mode == InstagramMode.REAL and not self.app_secret:
            logger.error("Running in REAL mode but no app secret configured. Instagram API calls will fail.")
        
        self.verify_token = (
            os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN")
            or os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN")
            or os.getenv("VERIFY_TOKEN")
            or "ticklegram_ig_verify"
        )
        self.timeout = int(os.getenv("INSTAGRAM_WEBHOOK_TIMEOUT", "30"))
        
        # Always initialize the HTTP client regardless of mode
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        logger.info(f"Instagram Client initialized in {self.mode.upper()} mode")
    
    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
    
    def _normalize_signature(self, value: Optional[str], prefix: str) -> Optional[str]:
        if not value:
            return None
        value = value.strip()
        return value.split(prefix, 1)[1] if value.startswith(prefix) else value

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature_sha256: Optional[str],
        signature_sha1: Optional[str] = None
    ) -> bool:
        """Verify webhook signature using HMAC-SHA256 or SHA1"""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Skipping Instagram webhook signature verification")
            return True
        if self.skip_signature_check:
            logger.warning("INSTAGRAM_SKIP_SIGNATURE enabled; skipping webhook signature verification")
            return True
        
        if not signature_sha256 and not signature_sha1:
            logger.error("No signature provided in Instagram webhook request")
            return False
        
        if not self.app_secret:
            logger.error("No app secret configured. Check FACEBOOK_APP_SECRET in .env")
            return False
        
        secrets = [self.app_secret, self.app_secret_alt]
        header_sha256 = self._normalize_signature(signature_sha256, "sha256=") if signature_sha256 else None
        header_sha1 = self._normalize_signature(signature_sha1, "sha1=") if signature_sha1 else None
        header_sha256 = header_sha256.lower() if header_sha256 else None
        header_sha1 = header_sha1.lower() if header_sha1 else None

        for secret in secrets:
            if not secret:
                continue
            try:
                secret_bytes = secret.encode("utf-8")
                sha256_digest = hmac.new(secret_bytes, payload, hashlib.sha256).hexdigest()
                sha1_digest = hmac.new(secret_bytes, payload, hashlib.sha1).hexdigest()
                sha256_ok = header_sha256 and hmac.compare_digest(header_sha256, sha256_digest)
                sha1_ok = header_sha1 and hmac.compare_digest(header_sha1, sha1_digest)
                if sha256_ok or sha1_ok:
                    logger.debug("Instagram webhook signature verified using configured secret")
                    return True
                if self.hmac_debug:
                    logger.warning(
                        "Signature mismatch for provided secret suffix ****%s (computed sha256=%s sha1=%s)",
                        secret[-6:],
                        sha256_digest,
                        sha1_digest
                    )
            except Exception as exc:
                logger.error("Error verifying Instagram webhook signature: %s", exc)

        if self.hmac_debug:
            logger.error(
                "Signature verification failure. headers sha256=%s sha1=%s payload_len=%s first16=%s",
                header_sha256,
                header_sha1,
                len(payload),
                payload[:16].hex() if payload else ""
            )
        return False
    
    def verify_webhook_token(self, hub_mode: str, hub_verify_token: str) -> bool:
        """Verify webhook setup token"""
        logger.info("Verifying Instagram webhook token")
        logger.info(f"Expected verify token: {self.verify_token}, Received: {hub_verify_token}")
        return hub_mode == "subscribe" and hub_verify_token == self.verify_token
    
    async def send_text_message(
        self,
        page_access_token: str,
        recipient_id: str,
        text: str,
        page_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a text message to an Instagram user."""
        return await self.send_dm(
            page_id=page_id or "me",
            page_access_token=page_access_token,
            recipient_id=recipient_id,
            text=text,
            attachments=None
        )
    
    async def send_attachment(
        self,
        page_access_token: str,
        recipient_id: str,
        attachment_type: str,
        attachment_url: str,
        page_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an attachment (image/video) to an Instagram user."""
        attachment_payload = {
            "type": attachment_type,
            "payload": {
                "url": attachment_url,
                "is_reusable": True
            }
        }
        return await self.send_dm(
            page_id=page_id or "me",
            page_access_token=page_access_token,
            recipient_id=recipient_id,
            text=None,
            attachments=[attachment_payload]
        )

    async def send_dm(
        self,
        page_id: str,
        page_access_token: str,
        recipient_id: str,
        text: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a DM via the Instagram Messenger API."""
        if self.mode == InstagramMode.MOCK:
            logger.info(
                "MOCK MODE: Sending Instagram DM to %s via page %s. text=%s attachments=%s",
                recipient_id,
                page_id,
                text,
                attachments
            )
            return {
                "success": True,
                "recipient_id": recipient_id,
                "message_id": f"mock_ig_msg_{datetime.now().timestamp()}",
                "mode": "mock"
            }

        url = f"{self.BASE_URL}/{page_id}/messages"

        message_payload: Dict[str, Any] = {}
        if text:
            message_payload["text"] = text
        if attachments:
            attachment = attachments[0]
            attachment_type = attachment.get("type", "image")
            payload = attachment.get("payload") or {
                "url": attachment.get("url"),
                "is_reusable": attachment.get("is_reusable", True)
            }
            message_payload["attachment"] = {
                "type": attachment_type,
                "payload": payload
            }

        if not message_payload:
            return {
                "success": False,
                "error": "Message payload is empty. Provide text or attachments.",
                "mode": "real"
            }

        payload = {
            "recipient": {"id": recipient_id},
            "message": message_payload,
            "messaging_type": "RESPONSE",
            "access_token": page_access_token
        }

        try:
            response = await self.client.post(url, json=payload)
            response_data = response.json() if response.content else {}

            if response.status_code == 200:
                return {
                    "success": True,
                    "recipient_id": response_data.get("recipient_id", recipient_id),
                    "message_id": response_data.get("message_id"),
                    "mode": "real"
                }

            error_data = response_data.get("error", {})
            error_code = error_data.get("code")
            error_message = error_data.get("message", "Unknown error")
            logger.error(
                "Failed to send Instagram DM via page %s: %s (Code: %s)",
                page_id,
                error_message,
                error_code
            )
            return {
                "success": False,
                "error": error_message,
                "error_code": response.status_code,
                "mode": "real"
            }

        except Exception as e:
            logger.error("Error sending Instagram DM: %s", e)
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
        tag: str = "ACCOUNT_UPDATE"
    ) -> Dict[str, Any]:
        """
        Send a tagged/template message to an Instagram user.
        When template_id is provided we rely on the pre-approved Meta template.
        """

        if self.mode == InstagramMode.MOCK:
            logger.info(
                "MOCK MODE: Sending Instagram template message to %s (template_id=%s, tag=%s): %s",
                recipient_id,
                template_id,
                tag,
                text
            )
            return {
                "success": True,
                "recipient_id": recipient_id,
                "message_id": f"mock_ig_template_{datetime.now().timestamp()}",
                "mode": "mock"
            }

        url = f"{self.BASE_URL}/me/messages"

        message_payload: Dict[str, Any] = {}
        if template_id:
            message_payload["message_creative_id"] = template_id
        else:
            message_payload["text"] = text

        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "MESSAGE_TAG",
            "tag": tag,
            "message": message_payload,
            "access_token": page_access_token
        }

        try:
            response = await self.client.post(url, json=payload)
            response_data = response.json() if response.content else {}

            if response.status_code == 200:
                return {
                    "success": True,
                    "recipient_id": response_data.get("recipient_id"),
                    "message_id": response_data.get("message_id"),
                    "mode": "real"
                }

            error_data = response_data.get("error", {})
            error_message = error_data.get("message", "Unknown error")
            logger.error(f"Failed to send Instagram template message: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "error_code": response.status_code,
                "mode": "real"
            }

        except Exception as exc:
            logger.error(f"Error sending Instagram template message: {exc}")
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
        instagram_account_id: str
    ) -> Dict[str, Any]:
        """Process incoming Instagram webhook message"""
        
        message_text = message_data.get("text", "")
        message_id = message_data.get("mid", "")
        attachments = message_data.get("attachments", [])
        
        # Check if this is a story reply or mention
        is_story_reply = message_data.get("is_echo", False) is False and "story" in message_data.get("reply_to", {}).get("story", {})
        
        logger.info(f"Processing Instagram message from {sender_id} on account {instagram_account_id}")
        
        # Try to get sender's profile if available from the message
        sender_name = None
        try:
            if "from" in message_data:
                sender_profile = message_data.get("from", {})
                sender_name = sender_profile.get("username") or sender_profile.get("name")
        except Exception as e:
            logger.error(f"Error getting sender profile from message: {e}")
        
        return {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "instagram_account_id": instagram_account_id,
            "message_id": message_id,
            "text": message_text,
            "has_attachments": len(attachments) > 0,
            "attachments": attachments,
            "is_story_reply": is_story_reply,
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def get_user_profile(
        self,
        page_access_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get Instagram user profile information"""
        
        if self.mode == InstagramMode.MOCK:
            logger.info(f"MOCK MODE: Getting Instagram profile for user {user_id}")
            return {
                "success": True,
                "id": user_id,
                "username": f"user_{user_id[:8]}",
                "name": f"Instagram User {user_id[:8]}",  # More natural name format
                "profile_pic": f"https://via.placeholder.com/150?text={user_id[:8]}",
                "mode": "mock"
            }
        
        # Real Instagram API call for Instagram Graph API
        url = f"{self.BASE_URL}/{user_id}"
        
        try:
            # First try getting business account info
            business_response = await self.client.get(
                f"{self.BASE_URL}/{user_id}",
                params={
                    "fields": "username,profile_picture_url,name,id",  # Instagram Graph API fields
                    "access_token": page_access_token
                }
            )
            logger.debug(f"API Response for user {user_id}: {business_response.status_code} - {business_response.text}")
            
            response_data = business_response.json() if business_response.content else {}
            
            if business_response.status_code == 200:
                profile_data = response_data
                
                # Get the best available name (prefer username over ID-based fallback)
                display_name = profile_data.get("username")
                if not display_name:
                    display_name = profile_data.get("name")
                if not display_name:
                    display_name = f"Instagram User {user_id[-6:]}"  # Use last 6 chars of ID
                    
                logger.info(f"Successfully fetched profile for user {user_id}: {display_name}")
                
                return {
                    "success": True,
                    "id": profile_data.get("id", user_id),
                    "username": display_name,  # Use the best available name
                    "name": profile_data.get("name") or display_name,
                    "profile_pic": profile_data.get("profile_picture_url"),
                    "mode": "real"
                }
            else:
                error_data = business_response.json() if business_response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Failed to get Instagram user profile: {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "mode": "real"
                }
        
        except Exception as e:
            logger.error(f"Error getting Instagram user profile: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "real"
            }
    
    async def handle_story_mention(
        self,
        page_access_token: str,
        story_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle Instagram story mentions"""
        
        if self.mode == InstagramMode.MOCK:
            logger.info(f"MOCK MODE: Handling story mention")
            return {
                "success": True,
                "message": "Story mention handled (mock)",
                "mode": "mock"
            }
        
        # Process story mention in real mode
        story_id = story_data.get("id")
        mentioned_user_id = story_data.get("from", {}).get("id")
        
        logger.info(f"Processing story mention from {mentioned_user_id}")
        
        return {
            "success": True,
            "story_id": story_id,
            "user_id": mentioned_user_id,
            "mode": "real"
        }
    
    async def get_media_comments(
        self,
        page_access_token: str,
        user_id: str,
        include_media: bool = False
    ) -> List[Dict[str, Any]]:
        """Get comments from user's posts and reels with optional media info"""
        
        if self.mode == InstagramMode.MOCK:
            logger.info("Using mock data for Instagram comments")
            # Return mock data for testing
            return [
                {
                    "id": f"comment_{i}",
                    "username": f"instagram_user_{i}",
                    "text": f"This is a test comment {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "profile_pic": None,
                    "replies": [],
                    "post": {
                        "id": f"post_{i}",
                        "username": f"instagram_user_{i}",
                        "profile_pic": None,
                        "media_type": "REEL" if i % 2 == 0 else "IMAGE",
                        "media_url": f"https://picsum.photos/id/{i}/800",
                        "permalink": f"https://instagram.com/p/mock_{i}",
                        "caption": f"Test post {i} caption",
                        "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat()
                    }
                } for i in range(5)
            ]
        
        try:
            # Define fields based on whether we need media info
            fields = "id"
            if include_media:
                fields += ",media_type,media_url,permalink,caption,timestamp"
            
            # Get user's media (posts and reels)
            logger.info(f"Fetching media for Instagram account {user_id}")
            media_response = await self.client.get(
                f"{self.BASE_URL}/{user_id}/media",
                params={
                    "fields": f"{fields},comments{{id,text,username,timestamp,replies{{id,text,username,timestamp}}}}",
                    "access_token": page_access_token
                }
            )
            
            if media_response.status_code != 200:
                response_text = media_response.text if media_response.content else "No response content"
                logger.error(f"Failed to get media for account {user_id}. Status: {media_response.status_code}, Response: {response_text}")
                error_data = media_response.json() if media_response.content else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                raise Exception(f"Failed to get media: {error_message}")
            
            media_data = media_response.json()
            logger.debug(f"Retrieved {len(media_data.get('data', []))} media items")
            
            all_comments = []
            for media in media_data.get("data", []):
                try:
                    media_id = media.get("id")
                    if not media_id:
                        logger.warning("Found media item without ID, skipping")
                        continue
                        
                    comments = media.get("comments", {}).get("data", [])
                    for comment in comments:
                        try:
                            comment_data = {
                                "id": comment.get("id"),
                                "username": comment.get("username", "Unknown"),
                                "text": comment.get("text", ""),
                                "timestamp": comment.get("timestamp"),
                                "profile_pic": None,  # We could fetch this separately if needed
                                "replies": []
                            }
                            
                            # Add replies if any
                            if "replies" in comment:
                                comment_data["replies"] = [
                                    {
                                        "id": reply.get("id"),
                                        "username": reply.get("username", "Unknown"),
                                        "text": reply.get("text", ""),
                                        "timestamp": reply.get("timestamp")
                                    }
                                    for reply in comment["replies"].get("data", [])
                                ]
                            
                            # Add media info if requested
                            if include_media:
                                comment_data["post"] = {
                                    "id": media_id,
                                    "username": "",  # We'd need an additional API call to get this
                                    "profile_pic": None,
                                    "media_type": media.get("media_type", "IMAGE"),
                                    "media_url": media.get("media_url"),
                                    "permalink": media.get("permalink"),
                                    "caption": media.get("caption", ""),
                                    "timestamp": media.get("timestamp")
                                }
                            
                            all_comments.append(comment_data)
                            
                        except Exception as comment_error:
                            logger.error(f"Error processing comment in media {media_id}: {str(comment_error)}")
                            continue
                            
                except Exception as media_error:
                    logger.error(f"Error processing media item: {str(media_error)}")
                    continue
            
            logger.info(f"Successfully retrieved {len(all_comments)} comments")
            return all_comments
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting media comments for account {user_id}: {error_msg}", exc_info=True)
            raise Exception(f"Failed to get Instagram comments: {error_msg}")
    
    async def reply_to_comment(
        self,
        page_access_token: str,
        comment_id: str,
        message: str
    ) -> Dict[str, Any]:
        """Reply to an Instagram comment"""
        
        if self.mode == InstagramMode.MOCK:
            return {
                "id": f"reply_{datetime.now().timestamp()}",
                "text": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "username": "mock_account"
            }
        
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/{comment_id}/replies",
                params={
                    "message": message,
                    "access_token": page_access_token
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to reply to comment: {response.text}")
                raise Exception("Failed to reply to comment")
            
            reply_data = response.json()
            return {
                "id": reply_data["id"],
                "text": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "username": "Your Account"  # You might want to get this from the account info
            }
        
        except Exception as e:
            logger.error(f"Error replying to comment: {e}")
            raise
    
    async def handle_post_comment(
        self,
        page_access_token: str,
        comment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle Instagram post comments (if allowed to reply via DM)"""
        
        if self.mode == InstagramMode.MOCK:
            logger.info(f"MOCK MODE: Handling post comment")
            return {
                "success": True,
                "message": "Post comment handled (mock)",
                "mode": "mock"
            }
        
        # Process comment in real mode
        comment_id = comment_data.get("id")
        commenter_id = comment_data.get("from", {}).get("id")
        comment_text = comment_data.get("text", "")
        
        logger.info(f"Processing post comment from {commenter_id}: {comment_text}")
        
        return {
            "success": True,
            "comment_id": comment_id,
            "user_id": commenter_id,
            "text": comment_text,
            "mode": "real"
        }

    async def create_comment(
        self,
        page_access_token: str,
        media_id: str,
        message: str
    ) -> Dict[str, Any]:
        """Create a comment on a piece of media."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Creating Instagram comment")
            return {
                "success": True,
                "id": f"mock_comment_{datetime.now().timestamp()}",
                "media_id": media_id,
                "text": message,
                "mode": "mock"
            }

        try:
            response = await self.client.post(
                f"{self.BASE_URL}/{media_id}/comments",
                params={"access_token": page_access_token},
                data={"message": message}
            )
            response_data = response.json() if response.content else {}
            if response.status_code == 200:
                response_data["success"] = True
                return response_data
            logger.error(f"Failed to create comment on media {media_id}: {response.text}")
            return {"success": False, "error": response_data.get("error")}
        except Exception as exc:
            logger.error(f"Error creating Instagram comment: {exc}")
            return {"success": False, "error": str(exc)}

    async def set_comment_visibility(
        self,
        page_access_token: str,
        comment_id: str,
        hide: bool
    ) -> Dict[str, Any]:
        """Hide or unhide a comment."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Setting comment visibility")
            return {"success": True, "comment_id": comment_id, "hidden": hide, "mode": "mock"}

        try:
            response = await self.client.post(
                f"{self.BASE_URL}/{comment_id}",
                params={"access_token": page_access_token},
                data={"hide": str(hide).lower()}
            )
            response_data = response.json() if response.content else {}
            if response.status_code == 200:
                response_data["success"] = True
                response_data["hidden"] = hide
                return response_data
            logger.error(f"Failed to update visibility for comment {comment_id}: {response.text}")
            return {"success": False, "error": response_data.get("error")}
        except Exception as exc:
            logger.error(f"Error updating Instagram comment visibility: {exc}")
            return {"success": False, "error": str(exc)}

    async def delete_comment(
        self,
        page_access_token: str,
        comment_id: str
    ) -> Dict[str, Any]:
        """Delete an Instagram comment."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Deleting Instagram comment")
            return {"success": True, "deleted": True, "comment_id": comment_id}

        try:
            response = await self.client.delete(
                f"{self.BASE_URL}/{comment_id}",
                params={"access_token": page_access_token}
            )
            response_data = response.json() if response.content else {}
            if response.status_code == 200:
                response_data["success"] = True
                return response_data
            logger.error(f"Failed to delete comment {comment_id}: {response.text}")
            return {"success": False, "error": response_data.get("error")}
        except Exception as exc:
            logger.error(f"Error deleting Instagram comment: {exc}")
            return {"success": False, "error": str(exc)}

    async def get_mentions(
        self,
        page_access_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Fetch media where the business account was mentioned."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Getting Instagram mentions for %s", user_id)
            return {
                "success": True,
                "data": [
                    {
                        "id": f"mention_{datetime.now().timestamp()}",
                        "media_type": "IMAGE",
                        "media_url": "https://picsum.photos/seed/mention/800",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ],
                "mode": "mock"
            }

        response = await self.client.get(
            f"{self.BASE_URL}/{user_id}/mentioned_media",
            params={
                "fields": "id,caption,media_type,media_url,permalink,timestamp",
                "access_token": page_access_token
            }
        )
        response_data = response.json() if response.content else {}
        if response.status_code == 200:
            response_data["success"] = True
            return response_data

        logger.error(f"Failed to fetch mentioned media for {user_id}: {response.text}")
        return {"success": False, "error": response_data.get("error")}

    async def get_account_insights(
        self,
        page_access_token: str,
        user_id: str,
        metrics: str,
        period: str = "day"
    ) -> Dict[str, Any]:
        """Fetch account level insights."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Returning account insights")
            return {
                "success": True,
                "data": [
                    {
                        "name": metric,
                        "period": period,
                        "values": [{"value": 1234, "end_time": datetime.now(timezone.utc).isoformat()}]
                    }
                    for metric in metrics.split(",")
                ],
                "mode": "mock"
            }

        response = await self.client.get(
            f"{self.BASE_URL}/{user_id}/insights",
            params={
                "metric": metrics,
                "period": period,
                "access_token": page_access_token
            }
        )
        response_data = response.json() if response.content else {}
        if response.status_code == 200:
            response_data["success"] = True
            return response_data

        logger.error(f"Failed to fetch account insights for {user_id}: {response.text}")
        return {"success": False, "error": response_data.get("error")}

    async def get_media_insights(
        self,
        page_access_token: str,
        media_id: str,
        metrics: str
    ) -> Dict[str, Any]:
        """Fetch insights for a media item."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Returning media insights")
            return {
                "success": True,
                "data": [
                    {
                        "name": metric,
                        "values": [{"value": 456, "end_time": datetime.now(timezone.utc).isoformat()}]
                    }
                    for metric in metrics.split(",")
                ],
                "mode": "mock"
            }

        response = await self.client.get(
            f"{self.BASE_URL}/{media_id}/insights",
            params={
                "metric": metrics,
                "access_token": page_access_token
            }
        )
        response_data = response.json() if response.content else {}
        if response.status_code == 200:
            response_data["success"] = True
            return response_data

        logger.error(f"Failed to fetch media insights for {media_id}: {response.text}")
        return {"success": False, "error": response_data.get("error")}

    async def get_story_insights(
        self,
        page_access_token: str,
        story_id: str,
        metrics: str
    ) -> Dict[str, Any]:
        """Fetch insights for a story."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Returning story insights")
            return {
                "success": True,
                "data": [
                    {
                        "name": metric,
                        "values": [{"value": 78, "end_time": datetime.now(timezone.utc).isoformat()}]
                    }
                    for metric in metrics.split(",")
                ],
                "mode": "mock"
            }

        response = await self.client.get(
            f"{self.BASE_URL}/{story_id}/insights",
            params={
                "metric": metrics,
                "access_token": page_access_token
            }
        )
        response_data = response.json() if response.content else {}
        if response.status_code == 200:
            response_data["success"] = True
            return response_data

        logger.error(f"Failed to fetch story insights for {story_id}: {response.text}")
        return {"success": False, "error": response_data.get("error")}

    async def get_comment_details(
        self,
        page_access_token: str,
        comment_id: str
    ) -> Dict[str, Any]:
        """Fetch a single comment's details."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Getting comment details for %s", comment_id)
            return {
                "success": True,
                "id": comment_id,
                "text": "Mock comment",
                "media": {"id": "mock_media_id"},
                "from": {"id": "mock_user"},
                "hidden": False,
                "mode": "mock"
            }

        response = await self.client.get(
            f"{self.BASE_URL}/{comment_id}",
            params={
                "fields": "id,text,user,from,hidden,parent_id,media{id}",
                "access_token": page_access_token
            }
        )
        response_data = response.json() if response.content else {}
        if response.status_code == 200:
            response_data["success"] = True
            return response_data

        logger.error(f"Failed to fetch comment details for {comment_id}: {response.text}")
        return {"success": False, "error": response_data.get("error")}

    async def send_marketing_event(
        self,
        pixel_id: str,
        access_token: str,
        payload: Dict[str, Any],
        max_retries: int = 3,
        base_backoff: float = 1.0
    ) -> Dict[str, Any]:
        """Send events to the Meta Conversions API with retry handling."""
        if self.mode == InstagramMode.MOCK:
            logger.info("MOCK MODE: Sending marketing event for pixel %s", pixel_id)
            return {"success": True, "mode": "mock", "payload": payload}

        url = f"{self.BASE_URL}/{pixel_id}/events"
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                response = await self.client.post(
                    url,
                    params={"access_token": access_token},
                    json=payload
                )
                response_data = response.json() if response.content else {}
                if response.status_code == 200:
                    return {"success": True, "response": response_data}

                status = response.status_code
                should_retry = status == 429 or status >= 500
                logger.warning(
                    "Conversions API call failed (status=%s, attempt=%s): %s",
                    status,
                    attempt,
                    response_data
                )
                if not should_retry or attempt >= max_retries:
                    return {
                        "success": False,
                        "status": status,
                        "error": response_data.get("error", response_data)
                    }

                await asyncio.sleep(base_backoff * attempt)

            except httpx.HTTPError as http_error:
                logger.error("HTTP error when sending marketing event: %s", http_error)
                if attempt >= max_retries:
                    return {"success": False, "error": str(http_error)}
                await asyncio.sleep(base_backoff * attempt)

        return {"success": False, "error": "Exceeded retry attempts"}

# Global Instagram client instance
instagram_client = InstagramClient()
