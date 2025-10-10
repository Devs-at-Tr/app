from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Header, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Set
from websocket_manager import manager as ws_manager
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import random
from datetime import datetime, timezone, timedelta

from database import engine, get_db, Base
from models import User, InstagramAccount, Chat, Message, UserRole, ChatStatus, MessageSender, MessageType, FacebookPage, MessagePlatform
from schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    InstagramConnect, InstagramAccountResponse,
    MessageCreate, MessageResponse,
    ChatAssign, ChatResponse, ChatWithMessages,
    DashboardStats,
    FacebookPageConnect, FacebookPageResponse, FacebookPageUpdate
)
from auth import verify_password, get_password_hash, create_access_token, decode_access_token
from facebook_api import facebook_client, FacebookMode
from instagram_api import instagram_client, InstagramMode

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create database tables
Base.metadata.create_all(bind=engine)

# Create the main app
app = FastAPI(
    title="TickleGram API",
    # Enable CORS with credentials for WebSocket
    root_path=os.getenv('API_ROOT_PATH', ''),
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dependency to get current user from token
async def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# Dependency for admin only
async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or supervisor access required"
        )
    return current_user

async def get_admin_only_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# ============= AUTH ENDPOINTS =============

@api_router.post("/auth/register", response_model=UserResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"User registered: {new_user.email}")
    return new_user

@api_router.post("/auth/signup", response_model=UserResponse)
def admin_signup(
    user_data: UserRegister,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Admin-only endpoint to create new users."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Admin {current_user.email} created user: {new_user.email} ({new_user.role})")
    return new_user

@api_router.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"user_id": user.id, "email": user.email})
    
    logger.info(f"User logged in: {user.email}")
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@api_router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ============= USER MANAGEMENT ENDPOINTS =============

@api_router.get("/users", response_model=List[UserResponse])
def list_users(current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@api_router.get("/users/agents", response_model=List[UserResponse])
def list_agents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = db.query(User).filter(User.role == UserRole.AGENT).all()
    return agents

# ============= INSTAGRAM ENDPOINTS =============

@api_router.get("/instagram/comments")
async def list_instagram_comments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all Instagram comments from posts and reels"""
    try:
        # Get all connected Instagram accounts
        accounts = db.query(InstagramAccount).filter(
            InstagramAccount.user_id == current_user.id
        ).all()
        
        if not accounts:
            logger.info(f"No Instagram accounts found for user {current_user.id}")
            return []
        
        all_comments = []
        for account in accounts:
            try:
                if instagram_client.mode == InstagramMode.MOCK:
                    # Mock data for testing including post info
                    comments = [
                        {
                            "id": f"comment_{i}",
                            "username": f"instagram_user_{i}",
                            "text": f"This is a test comment {i}",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "profile_pic": None,
                            "replies": [],
                            "post": {
                                "id": f"post_{i}",
                                "username": account.username,
                                "profile_pic": None,
                                "media_type": "REEL" if i % 2 == 0 else "IMAGE",
                                "media_url": f"https://picsum.photos/id/{i}/800",
                                "permalink": f"https://instagram.com/p/mock_{i}",
                                "caption": f"Test post {i} caption",
                                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat()
                            }
                        } for i in range(5)
                    ]
                else:
                    # Get comments and associated posts from Instagram Graph API
                    comments = await instagram_client.get_media_comments(
                        page_access_token=account.access_token,
                        user_id=account.page_id,
                        include_media=True
                    )
                    
                    if not isinstance(comments, list):
                        logger.error(f"Unexpected response format from Instagram API for account {account.id}: {comments}")
                        raise ValueError("Invalid response format from Instagram API")
                    
                all_comments.extend(comments)
                
            except Exception as account_error:
                logger.error(f"Error fetching comments for Instagram account {account.id}: {str(account_error)}")
                # Continue with other accounts instead of failing completely
                continue
        
        # Sort comments only if we have any
        if all_comments:
            try:
                return sorted(all_comments, key=lambda x: x["timestamp"], reverse=True)
            except Exception as sort_error:
                logger.error(f"Error sorting comments: {str(sort_error)}")
                # Return unsorted if sorting fails
                return all_comments
        return all_comments
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting Instagram comments for user {current_user.id}: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to fetch Instagram comments",
                "error": error_msg
            }
        )

@api_router.post("/instagram/comments/{comment_id}/reply")
async def reply_to_instagram_comment(
    comment_id: str,
    reply_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reply to an Instagram comment"""
    try:
        # Find the Instagram account that owns the post
        comment_parts = comment_id.split("_")
        if len(comment_parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid comment ID format")
        
        post_id = comment_parts[0]
        account = db.query(InstagramAccount).filter(
            InstagramAccount.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="No Instagram account found")
        
        if instagram_client.mode == InstagramMode.MOCK:
            # Mock reply for testing
            reply = {
                "id": f"reply_{datetime.now().timestamp()}",
                "text": reply_data["text"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "username": account.username
            }
        else:
            # Send reply through Instagram Graph API
            reply = await instagram_client.reply_to_comment(
                page_access_token=account.access_token,
                comment_id=comment_id,
                message=reply_data["text"]
            )
        
        return reply
    except Exception as e:
        logger.error(f"Error replying to Instagram comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/facebook/comments")
async def list_facebook_comments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List Facebook comments in a chat-friendly format."""
    try:
        pages = db.query(FacebookPage).all()
        if not pages:
            return []

        comments = []
        for page in pages:
            if facebook_client.mode == FacebookMode.MOCK:
                for index in range(5):
                    timestamp = datetime.now(timezone.utc) - timedelta(minutes=index * 7)
                    comments.append({
                        "id": f"{page.page_id}_comment_{index}",
                        "username": f"facebook_user_{index + 1}",
                        "text": f"This is a mock Facebook comment {index + 1} on {page.page_name or 'your page'}.",
                        "timestamp": timestamp.isoformat(),
                        "profile_pic": None,
                        "replies": [],
                        "post": {
                            "id": f"{page.page_id}_post_{index}",
                            "username": page.page_name or "Facebook Page",
                            "profile_pic": None,
                            "media_type": "IMAGE",
                            "media_url": f"https://picsum.photos/seed/{page.page_id}{index}/800",
                            "permalink": f"https://facebook.com/{page.page_id}/posts/mock_{index}",
                            "caption": f"Mock Facebook post {index + 1} for {page.page_name or 'your page'}.",
                            "timestamp": timestamp.isoformat()
                        }
                    })
            else:
                logger.info("Facebook comment retrieval is not implemented for REAL mode yet.")

        comments.sort(key=lambda item: item["timestamp"], reverse=True)
        return comments
    except Exception as exc:
        logger.error(f"Error fetching Facebook comments: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to fetch Facebook comments", "error": str(exc)}
        )

@api_router.post("/facebook/comments/{comment_id}/reply")
async def reply_to_facebook_comment(
    comment_id: str,
    reply_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reply to a Facebook comment (mock support)."""
    try:
        if facebook_client.mode == FacebookMode.MOCK:
            logger.info(f"Mock reply to Facebook comment {comment_id}: {reply_data.get('text', '')}")
            return {"success": True, "comment_id": comment_id, "mode": "mock"}

        logger.info("Facebook comment reply not implemented for REAL mode.")
        raise HTTPException(status_code=501, detail="Facebook comment reply not implemented in real mode")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error replying to Facebook comment: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

@api_router.post("/instagram/accounts", response_model=InstagramAccountResponse)
async def connect_instagram_account(
    data: InstagramConnect, 
    current_user: User = Depends(get_admin_only_user), 
    db: Session = Depends(get_db)
):
    """Connect an Instagram Business Account"""
    
    # Check if account already exists
    existing = db.query(InstagramAccount).filter(
        InstagramAccount.page_id == data.page_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Instagram account already connected")
    
    # In REAL mode, verify the account with Instagram API
    if instagram_client.mode == InstagramMode.REAL:
        # Verify access token by fetching account info
        profile = await instagram_client.get_user_profile(
            page_access_token=data.access_token,
            user_id=data.page_id
        )
        
        if not profile.get("success"):
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to verify Instagram account: {profile.get('error', 'Unknown error')}"
            )
        
        username = profile.get("username", data.username or f"ig_user_{data.page_id[:8]}")
    else:
        # Mock mode
        username = data.username or f"ig_user_{data.page_id[:8]}"
    
    # Create new Instagram account
    new_account = InstagramAccount(
        user_id=current_user.id,
        page_id=data.page_id,
        access_token=data.access_token,
        username=username
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    logger.info(f"Instagram account connected: {new_account.page_id} (@{username}) for user {current_user.email}")
    return new_account

@api_router.get("/instagram/accounts", response_model=List[InstagramAccountResponse])
def list_instagram_accounts(current_user: User = Depends(get_admin_only_user), db: Session = Depends(get_db)):
    """List all connected Instagram accounts for current user"""
    accounts = db.query(InstagramAccount).filter(InstagramAccount.user_id == current_user.id).all()
    return accounts

@api_router.get("/instagram/accounts/{account_id}", response_model=InstagramAccountResponse)
def get_instagram_account(
    account_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Get specific Instagram account"""
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")
    
    return account

@api_router.delete("/instagram/accounts/{account_id}")
def delete_instagram_account(
    account_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Delete/disconnect an Instagram account"""
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")
    
    db.delete(account)
    db.commit()
    
    logger.info(f"Deleted Instagram account: {account.page_id} (@{account.username})")
    return {"success": True, "message": "Instagram account disconnected"}

# Instagram Webhook Endpoints
@api_router.get("/webhooks/instagram")
async def verify_instagram_webhook(
    request: Request,
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token")
):
    """Verify Instagram webhook subscription"""
    
    if instagram_client.verify_webhook_token(hub_mode, hub_verify_token):
        logger.info("Instagram webhook verification successful")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    else:
        logger.warning("Instagram webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@api_router.post("/webhooks/instagram")
async def handle_instagram_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Instagram webhook"""
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Hub-Signature", "")
        
        # Verify signature (skip in mock mode)
        if not instagram_client.verify_webhook_signature(body, signature):
            logger.warning("Invalid Instagram webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        data = await request.json()
        logger.info(f"Received Instagram webhook: {data.get('object')}")
        
        # Process webhook entries
        if data.get("object") == "instagram":
            for entry in data.get("entry", []):
                instagram_account_id = entry.get("id")
                
                # Get Instagram account from database
                ig_account = db.query(InstagramAccount).filter(
                    InstagramAccount.page_id == instagram_account_id
                ).first()
                
                if not ig_account:
                    logger.warning(f"Received webhook for unknown Instagram account: {instagram_account_id}")
                    continue
                
                # Process messaging events
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")
                    recipient_id = messaging_event.get("recipient", {}).get("id")
                    
                    # Skip if message is from the business account itself (echo)
                    if sender_id == instagram_account_id:
                        continue
                    
                    # Handle message
                    if "message" in messaging_event:
                        message_data = messaging_event["message"]
                        
                        # Process message
                        processed = await instagram_client.process_webhook_message(
                            sender_id=sender_id,
                            recipient_id=recipient_id,
                            message_data=message_data,
                            instagram_account_id=instagram_account_id
                        )
                        
                        # Find or create chat
                        chat = db.query(Chat).filter(
                            Chat.instagram_user_id == sender_id,
                            Chat.platform == MessagePlatform.INSTAGRAM,
                            Chat.facebook_page_id == instagram_account_id
                        ).first()
                        
                        if not chat:
                            # Get user profile
                            profile = await instagram_client.get_user_profile(
                                page_access_token=ig_account.access_token,
                                user_id=sender_id
                            )
                            username = profile.get("username") or profile.get("name") or f"IG User {sender_id[:8]}"
                            
                            # Create new chat
                            chat = Chat(
                                instagram_user_id=sender_id,
                                username=username,
                                platform=MessagePlatform.INSTAGRAM,
                                facebook_page_id=instagram_account_id,
                                status=ChatStatus.UNASSIGNED
                            )
                            db.add(chat)
                            db.flush()
                        
                        # Create message
                        new_message = Message(
                            chat_id=chat.id,
                            sender=MessageSender.INSTAGRAM_USER,
                            content=processed.get("text", ""),
                            message_type=MessageType.TEXT,
                            platform=MessagePlatform.INSTAGRAM
                        )
                        db.add(new_message)
                        
                        # Update chat
                        chat.last_message = processed.get("text", "")
                        chat.unread_count += 1
                        chat.updated_at = datetime.now(timezone.utc)
                        
                        db.commit()
                        db.refresh(new_message)
                        logger.info(f"Processed Instagram message from {sender_id} on account {instagram_account_id}")
                        
                        # Notify relevant users about new message
                        notify_users = set()
                        
                        # Add assigned agent if any
                        if chat.assigned_to:
                            notify_users.add(str(chat.assigned_to))
                        
                        # Add admin users
                        admin_users = db.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.SUPERVISOR])).all()
                        notify_users.update(str(user.id) for user in admin_users)
                        
                        message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")

                        # Broadcast new message notification
                        await ws_manager.broadcast_to_users(notify_users, {
                            "type": "new_message",
                            "chat_id": str(chat.id),
                            "platform": chat.platform.value,
                            "sender_id": sender_id,
                            "message": message_payload
                        })
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Error processing Instagram webhook: {e}")
        # Return 200 to avoid Instagram retrying
        return {"status": "error", "message": str(e)}

# ============= CHAT ENDPOINTS =============

@api_router.get("/chats", response_model=List[ChatResponse])
def list_chats(
    status_filter: Optional[str] = None,
    assigned_to_me: bool = False,
    platform: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Chat).options(joinedload(Chat.assigned_agent))
    
    # Filter by status
    if status_filter:
        if status_filter == "assigned":
            query = query.filter(Chat.status == ChatStatus.ASSIGNED)
        elif status_filter == "unassigned":
            query = query.filter(Chat.status == ChatStatus.UNASSIGNED)
    
    # Filter by platform
    if platform:
        if platform.upper() == "INSTAGRAM":
            query = query.filter(Chat.platform == MessagePlatform.INSTAGRAM)
        elif platform.upper() == "FACEBOOK":
            query = query.filter(Chat.platform == MessagePlatform.FACEBOOK)
    
    # Filter by assigned to current user (for agents)
    if assigned_to_me or current_user.role == UserRole.AGENT:
        query = query.filter(Chat.assigned_to == current_user.id)
    
    chats = query.order_by(Chat.updated_at.desc()).all()
    return chats

@api_router.get("/chats/{chat_id}", response_model=ChatWithMessages)
def get_chat(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).options(
        joinedload(Chat.messages),
        joinedload(Chat.assigned_agent)
    ).filter(Chat.id == chat_id).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check access: agents can only see their assigned chats
    if current_user.role == UserRole.AGENT and chat.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Mark messages as read by resetting unread count
    chat.unread_count = 0
    db.commit()
    
    return chat

@api_router.post("/chats/{chat_id}/assign")
def assign_chat(chat_id: str, assignment: ChatAssign, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if assignment.agent_id:
        agent = db.query(User).filter(User.id == assignment.agent_id, User.role == UserRole.AGENT).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        chat.assigned_to = assignment.agent_id
        chat.status = ChatStatus.ASSIGNED
    else:
        chat.assigned_to = None
        chat.status = ChatStatus.UNASSIGNED
    
    db.commit()
    db.refresh(chat)
    
    logger.info(f"Chat {chat_id} assigned to {assignment.agent_id or 'unassigned'}")
    return {"success": True, "chat": ChatResponse.model_validate(chat)}

@api_router.post("/chats/{chat_id}/message", response_model=MessageResponse)
async def send_message(chat_id: str, message_data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check access
    if current_user.role == UserRole.AGENT and chat.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # If in mock mode, just create the message without actual platform integration
    if instagram_client.mode == InstagramMode.MOCK and facebook_client.mode == FacebookMode.MOCK:
        new_message = Message(
            chat_id=chat_id,
            sender=MessageSender.AGENT,
            content=message_data.content,
            message_type=message_data.message_type,
            platform=chat.platform
        )
        db.add(new_message)
        chat.last_message = message_data.content
        chat.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(new_message)
        logger.info(f"Mock message sent in chat {chat_id}")
        return new_message
    
    # For real mode, send through appropriate platform
    if chat.platform == MessagePlatform.FACEBOOK:
        # Get Facebook page access token
        if chat.facebook_page_id:
            fb_page = db.query(FacebookPage).filter(FacebookPage.page_id == chat.facebook_page_id).first()
            if fb_page and fb_page.is_active:
                # Send via Facebook Messenger
                result = await facebook_client.send_text_message(
                    page_access_token=fb_page.access_token,
                    recipient_id=chat.instagram_user_id,  # This is actually facebook_user_id for FB chats
                    text=message_data.content
                )
                if not result.get("success"):
                    logger.error(f"Failed to send Facebook message: {result.get('error')}")
                    raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
            else:
                raise HTTPException(status_code=400, detail="Facebook page not found or inactive")
        else:
            raise HTTPException(status_code=400, detail="No Facebook page associated with this chat")
    
    elif chat.platform == MessagePlatform.INSTAGRAM:
        # Get Instagram account access token
        if chat.facebook_page_id:  # This stores the Instagram account ID
            ig_account = db.query(InstagramAccount).filter(InstagramAccount.page_id == chat.facebook_page_id).first()
            if ig_account:
                # Send via Instagram
                result = await instagram_client.send_text_message(
                    page_access_token=ig_account.access_token,
                    recipient_id=chat.instagram_user_id,
                    text=message_data.content
                )
                if not result.get("success"):
                    logger.error(f"Failed to send Instagram message: {result.get('error')}")
                    raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
            else:
                raise HTTPException(status_code=400, detail="Instagram account not found")
        else:
            raise HTTPException(status_code=400, detail="No Instagram account associated with this chat")
    
    # Create message record in database
    new_message = Message(
        chat_id=chat_id,
        sender=MessageSender.AGENT,
        content=message_data.content,
        message_type=message_data.message_type,
        platform=chat.platform
    )
    db.add(new_message)
    
    # Update chat
    chat.last_message = message_data.content
    chat.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(new_message)
    
    message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")

    # Notify relevant users about the sent message
    notify_users = set()
    
    # Add assigned agent if any
    if chat.assigned_to:
        notify_users.add(str(chat.assigned_to))
    
    # Add admin and supervisor users
    admin_users = db.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.SUPERVISOR])).all()
    notify_users.update(str(user.id) for user in admin_users)
    
    # Broadcast message sent notification
    await ws_manager.broadcast_to_users(notify_users, {
        "type": "new_message",
        "chat_id": str(chat.id),
        "platform": chat.platform.value,
        "sender": "agent",
        "message": message_payload
    })
    
    logger.info(f"Message sent in chat {chat_id} by {current_user.email} on {chat.platform}")
    return new_message

# ============= DASHBOARD ENDPOINTS =============

@api_router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role in {UserRole.ADMIN, UserRole.SUPERVISOR}:
        total_chats = db.query(Chat).count()
        assigned_chats = db.query(Chat).filter(Chat.status == ChatStatus.ASSIGNED).count()
        unassigned_chats = db.query(Chat).filter(Chat.status == ChatStatus.UNASSIGNED).count()
        instagram_chats = db.query(Chat).filter(Chat.platform == MessagePlatform.INSTAGRAM).count()
        facebook_chats = db.query(Chat).filter(Chat.platform == MessagePlatform.FACEBOOK).count()
    else:
        # Agents only see their stats
        total_chats = db.query(Chat).filter(Chat.assigned_to == current_user.id).count()
        assigned_chats = total_chats
        unassigned_chats = 0
        instagram_chats = db.query(Chat).filter(
            Chat.assigned_to == current_user.id,
            Chat.platform == MessagePlatform.INSTAGRAM
        ).count()
        facebook_chats = db.query(Chat).filter(
            Chat.assigned_to == current_user.id,
            Chat.platform == MessagePlatform.FACEBOOK
        ).count()
    
    total_messages = db.query(Message).count()
    active_agents = db.query(User).filter(User.role == UserRole.AGENT).count()
    
    return DashboardStats(
        total_chats=total_chats,
        assigned_chats=assigned_chats,
        unassigned_chats=unassigned_chats,
        total_messages=total_messages,
        active_agents=active_agents,
        instagram_chats=instagram_chats,
        facebook_chats=facebook_chats
    )

# ============= FACEBOOK ENDPOINTS =============

@api_router.post("/facebook/pages", response_model=FacebookPageResponse)
def connect_facebook_page(
    page_data: FacebookPageConnect,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Connect a Facebook page"""
    # Check if page already exists
    existing_page = db.query(FacebookPage).filter(FacebookPage.page_id == page_data.page_id).first()
    if existing_page:
        # Update existing page
        existing_page.page_name = page_data.page_name or existing_page.page_name
        existing_page.access_token = page_data.access_token
        existing_page.is_active = True
        existing_page.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_page)
        logger.info(f"Updated Facebook page: {page_data.page_id}")
        return existing_page
    
    # Create new Facebook page
    new_page = FacebookPage(
        page_id=page_data.page_id,
        page_name=page_data.page_name or f"Facebook Page {page_data.page_id[:8]}",
        access_token=page_data.access_token
    )
    db.add(new_page)
    db.commit()
    db.refresh(new_page)
    
    logger.info(f"Connected Facebook page: {page_data.page_id}")
    return new_page

@api_router.get("/facebook/pages", response_model=List[FacebookPageResponse])
def list_facebook_pages(
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """List all connected Facebook pages"""
    pages = db.query(FacebookPage).all()
    return pages

@api_router.get("/facebook/pages/{page_id}", response_model=FacebookPageResponse)
def get_facebook_page(
    page_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Get a specific Facebook page"""
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Facebook page not found")
    return page

@api_router.patch("/facebook/pages/{page_id}", response_model=FacebookPageResponse)
def update_facebook_page(
    page_id: str,
    page_update: FacebookPageUpdate,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Update a Facebook page"""
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Facebook page not found")
    
    if page_update.page_name is not None:
        page.page_name = page_update.page_name
    if page_update.access_token is not None:
        page.access_token = page_update.access_token
    if page_update.is_active is not None:
        page.is_active = page_update.is_active
    
    page.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(page)
    
    logger.info(f"Updated Facebook page: {page_id}")
    return page

@api_router.delete("/facebook/pages/{page_id}")
def delete_facebook_page(
    page_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Delete a Facebook page"""
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Facebook page not found")
    
    db.delete(page)
    db.commit()
    
    logger.info(f"Deleted Facebook page: {page_id}")
    return {"success": True, "message": "Facebook page deleted"}

# Facebook Webhook Endpoints
@api_router.get("/webhooks/facebook")
async def verify_facebook_webhook(
    request: Request,
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token")
):
    
    if facebook_client.verify_webhook_token(hub_mode, hub_verify_token):
        logger.info("Facebook webhook verification successful")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    else:
        logger.warning("Facebook webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@api_router.post("/webhooks/facebook")
async def handle_facebook_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Facebook webhook"""
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Hub-Signature", "")
        
        # Verify signature (skip in mock mode)
        if not facebook_client.verify_webhook_signature(body, signature):
            logger.warning("Invalid Facebook webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        data = await request.json()
        logger.info(f"Received Facebook webhook: {data.get('object')}")
        
        # Process webhook entries
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                page_id = entry.get("id")
                
                # Get Facebook page from database
                fb_page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
                if not fb_page:
                    logger.warning(f"Received webhook for unknown page: {page_id}")
                    continue
                
                # Process messaging events
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")
                    recipient_id = messaging_event.get("recipient", {}).get("id")
                    
                    # Handle message
                    if "message" in messaging_event:
                        message_data = messaging_event["message"]
                        
                        # Process message
                        processed = await facebook_client.process_webhook_message(
                            sender_id=sender_id,
                            recipient_id=recipient_id,
                            message_data=message_data,
                            page_id=page_id
                        )
                        
                        # Find or create chat
                        chat = db.query(Chat).filter(
                            Chat.instagram_user_id == sender_id,
                            Chat.platform == MessagePlatform.FACEBOOK,
                            Chat.facebook_page_id == page_id
                        ).first()
                        
                        if not chat:
                            # Get user profile
                            profile = await facebook_client.get_user_profile(
                                page_access_token=fb_page.access_token,
                                user_id=sender_id
                            )
                            username = profile.get("name", f"FB User {sender_id[:8]}")
                            
                            # Create new chat
                            chat = Chat(
                                instagram_user_id=sender_id,
                                username=username,
                                platform=MessagePlatform.FACEBOOK,
                                facebook_page_id=page_id,
                                status=ChatStatus.UNASSIGNED
                            )
                            db.add(chat)
                            db.flush()
                        
                        # Create message
                        new_message = Message(
                            chat_id=chat.id,
                            sender=MessageSender.FACEBOOK_USER,
                            content=processed.get("text", ""),
                            message_type=MessageType.TEXT,
                            platform=MessagePlatform.FACEBOOK
                        )
                        db.add(new_message)
                        
                        # Update chat
                        chat.last_message = processed.get("text", "")
                        
                        db.commit()
                        logger.info(f"Processed Facebook message from {sender_id} on page {page_id}")
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Error processing Facebook webhook: {e}")
        # Return 200 to avoid Facebook retrying
        return {"status": "error", "message": str(e)}

# ============= MOCK DATA GENERATOR =============
from generate_mock_data import generate_mock_chats as generate_mock_data

@api_router.post("/mock/generate-chats")
def generate_mock_chats(
    count: int = 5,
    platform: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Generate mock chats for testing (Instagram or Facebook)"""
    chat_ids = generate_mock_data(
        db=db,
        user_id=current_user.id,
        count=count,
        platform=platform or "INSTAGRAM"
    )
    
    logger.info(f"Generated {count} mock chats")
    return {
        "success": True,
        "count": count,
        "platform": platform or "INSTAGRAM",
        "chat_ids": chat_ids
    }

@api_router.post("/mock/simulate-message")
def simulate_incoming_message(chat_id: str, message: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Simulate an incoming Instagram message"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    new_message = Message(
        chat_id=chat_id,
        sender=MessageSender.INSTAGRAM_USER,
        content=message,
        message_type=MessageType.TEXT
    )
    db.add(new_message)
    
    chat.last_message = message
    chat.unread_count += 1
    chat.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(new_message)
    
    logger.info(f"Simulated incoming message for chat {chat_id}")
    return {"success": True, "message": MessageResponse.model_validate(new_message)}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Get token from query params
    token = websocket.query_params.get('token')
    if not token:
        await websocket.close(code=1008)  # Policy violation
        return
    
    try:
        # Verify token
        payload = decode_access_token(token)
        if not payload or 'user_id' not in payload:
            await websocket.close(code=1008)
            return
        
        user_id = str(payload['user_id'])
        await ws_manager.connect(websocket, user_id)
        
        try:
            while True:
                # Keep connection alive and handle any incoming messages
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011)  # Internal error
        except:
            pass

# Include the router in the main app
app.include_router(api_router)

# Configure CORS
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
if '*' not in cors_origins:
    # Add wss:// and https:// variants for production
    ws_origins = []
    for origin in cors_origins:
        if origin.startswith('http'):
            ws_origins.append(origin.replace('http', 'ws'))
    cors_origins.extend(ws_origins)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
