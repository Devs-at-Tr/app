from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Header, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Set, Dict, Any
from websocket_manager import manager as ws_manager
import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
import random
import asyncio
from datetime import datetime, timezone, timedelta

from database import engine, get_db, Base
from models import (
    User,
    InstagramAccount,
    Chat,
    Message,
    UserRole,
    ChatStatus,
    MessageSender,
    MessageType,
    FacebookPage,
    MessagePlatform,
    MessageTemplate,
    InstagramUser,
    InstagramMessage,
    InstagramMessageDirection,
    InstagramComment,
    InstagramCommentAction,
    InstagramMarketingEvent,
    InstagramInsight,
    InstagramInsightScope
)
from schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    InstagramConnect, InstagramAccountResponse,
    MessageCreate, MessageResponse,
    ChatAssign, ChatResponse, ChatWithMessages,
    DashboardStats,
    FacebookPageConnect, FacebookPageResponse, FacebookPageUpdate,
    MessageTemplateCreate,
    MessageTemplateUpdate,
    MessageTemplateResponse,
    TemplateSendRequest,
    InstagramSendRequest,
    InstagramCommentCreateRequest,
    InstagramCommentHideRequest,
    InstagramMarketingEventRequest,
    InstagramMarketingEventSchema,
    InstagramCommentSchema,
    InstagramInsightSchema
)
from auth import verify_password, get_password_hash, create_access_token, decode_access_token
from facebook_api import facebook_client, FacebookMode
from instagram_api import instagram_client, InstagramMode

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID") or os.getenv("PAGE_ID") or os.getenv("FACEBOOK_PAGE_ID")
INSTAGRAM_PAGE_ACCESS_TOKEN = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN") or os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
INSTAGRAM_VERIFY_TOKEN = os.getenv("VERIFY_TOKEN") or os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN") or os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN")
PIXEL_ID = os.getenv("PIXEL_ID")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v18.0")

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

def resolve_instagram_access_token(db: Session, page_id: Optional[str]) -> Optional[str]:
    """Resolve the best access token for an Instagram page."""
    token: Optional[str] = None
    if page_id:
        account = db.query(InstagramAccount).filter(InstagramAccount.page_id == page_id).first()
        if account and account.access_token:
            token = account.access_token
    if not token:
        token = INSTAGRAM_PAGE_ACCESS_TOKEN
    return token

def gather_dm_notify_users(db: Session, chat: Optional[Chat] = None) -> Set[str]:
    """Collect user IDs that should receive DM notifications."""
    notify_users: Set[str] = set()
    if chat and chat.assigned_to:
        notify_users.add(str(chat.assigned_to))

    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    notify_users.update(str(user.id) for user in admin_users)
    return notify_users

def gather_admin_user_ids(db: Session) -> Set[str]:
    """Return IDs for all admin users."""
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    return {str(user.id) for user in admin_users}

def upsert_instagram_comment(
    db: Session,
    comment_id: str,
    media_id: str,
    author_id: Optional[str],
    text: Optional[str],
    hidden: bool,
    action: InstagramCommentAction,
    mentioned_user_id: Optional[str],
    ts: int,
    attachments: Optional[Dict[str, Any]] = None
) -> InstagramComment:
    """Create or update an Instagram comment record."""
    comment = db.query(InstagramComment).filter(InstagramComment.id == comment_id).first()
    if comment:
        comment.media_id = media_id
        comment.author_id = author_id
        comment.text = text
        comment.hidden = hidden
        comment.action = action
        comment.mentioned_user_id = mentioned_user_id
        comment.ts = ts
        if attachments:
            comment.attachments_json = json.dumps(attachments)
    else:
        comment = InstagramComment(
            id=comment_id,
            media_id=media_id,
            author_id=author_id,
            text=text,
            hidden=hidden,
            action=action,
            mentioned_user_id=mentioned_user_id,
            ts=ts,
            attachments_json=json.dumps(attachments) if attachments else None
        )
        db.add(comment)
    return comment

def resolve_default_instagram_account(db: Session, current_user: Optional[User] = None) -> Optional[InstagramAccount]:
    """Return a default Instagram account for API operations."""
    query = db.query(InstagramAccount)
    if current_user and current_user.role != UserRole.ADMIN:
        query = query.filter(InstagramAccount.user_id == current_user.id)
    return query.first()

def persist_instagram_insight(
    db: Session,
    scope: InstagramInsightScope,
    entity_id: str,
    metrics: Dict[str, Any],
    period: Optional[str] = None
) -> InstagramInsight:
    """Store an Instagram insight snapshot."""
    insight = InstagramInsight(
        scope=scope,
        entity_id=entity_id,
        period=period,
        metrics_json=json.dumps(metrics),
        fetched_at=datetime.now(timezone.utc)
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight

def build_insight_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Graph API insight response to a simple metric dictionary."""
    metrics: Dict[str, Any] = {}
    for entry in data.get("data", []):
        name = entry.get("name")
        values = entry.get("values", [])
        latest_value = None
        if values:
            last_entry = values[-1]
            if isinstance(last_entry, dict):
                latest_value = last_entry.get("value")
            else:
                latest_value = last_entry
        metrics[name] = latest_value
    return metrics

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
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
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
def signup(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Public endpoint to create new agent accounts."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Only allow agent role for public signup
    if user_data.role not in ['agent', None]:
        role = 'agent'
    else:
        role = user_data.role or 'agent'

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New agent registered: {new_user.email}")
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
                            "profile_pic_url": None,
                            "replies": [],
                            "post": {
                                "id": f"post_{i}",
                                "username": account.username,
                                "profile_pic_url": None,
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

@api_router.post("/comments/create", response_model=InstagramCommentSchema)
async def create_instagram_comment(
    payload: InstagramCommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a comment on an Instagram media item."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram page configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not configured")

    result = await instagram_client.create_comment(
        page_access_token=page_access_token,
        media_id=payload.media_id,
        message=payload.message
    )
    if not result.get("success"):
        error = result.get("error", {"message": "Failed to create comment"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to create comment"))

    comment_id = result.get("id") or result.get("comment_id")
    timestamp_seconds = int(datetime.now(timezone.utc).timestamp())
    author_id = page_id

    comment_record = upsert_instagram_comment(
        db=db,
        comment_id=comment_id,
        media_id=payload.media_id,
        author_id=author_id,
        text=payload.message,
        hidden=False,
        action=InstagramCommentAction.CREATED,
        mentioned_user_id=None,
        ts=timestamp_seconds,
        attachments=None
    )
    db.commit()
    db.refresh(comment_record)

    await ws_manager.broadcast_global({
        "type": "ig_comment",
        "action": comment_record.action.value,
        "media_id": comment_record.media_id,
        "comment_id": comment_record.id,
        "text": comment_record.text,
        "author_id": comment_record.author_id,
        "hidden": comment_record.hidden,
        "timestamp": comment_record.ts,
        "source": "api"
    })

    return InstagramCommentSchema.model_validate(comment_record)

@api_router.post("/comments/hide", response_model=InstagramCommentSchema)
async def hide_instagram_comment(
    payload: InstagramCommentHideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hide or unhide an Instagram comment."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram page configured")
    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not configured")

    result = await instagram_client.set_comment_visibility(
        page_access_token=page_access_token,
        comment_id=payload.comment_id,
        hide=payload.hide
    )
    if not result.get("success"):
        error = result.get("error", {"message": "Failed to update comment visibility"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to update comment visibility"))

    details = await instagram_client.get_comment_details(page_access_token, payload.comment_id)
    media_id = details.get("media", {}).get("id") if details.get("success") else None
    author_id = None
    if details.get("success"):
        from_data = details.get("from") or details.get("user") or {}
        if isinstance(from_data, dict):
            author_id = from_data.get("id")

    existing = db.query(InstagramComment).filter(InstagramComment.id == payload.comment_id).first()
    if not media_id:
        media_id = existing.media_id if existing else ""

    timestamp_seconds = int(datetime.now(timezone.utc).timestamp())

    comment_record = upsert_instagram_comment(
        db=db,
        comment_id=payload.comment_id,
        media_id=media_id,
        author_id=author_id if author_id else (existing.author_id if existing else None),
        text=details.get("text") if details.get("success") else (existing.text if existing else None),
        hidden=payload.hide,
        action=InstagramCommentAction.UPDATED,
        mentioned_user_id=existing.mentioned_user_id if existing else None,
        ts=timestamp_seconds,
        attachments=None
    )
    db.commit()
    db.refresh(comment_record)

    await ws_manager.broadcast_global({
        "type": "ig_comment",
        "action": comment_record.action.value,
        "media_id": comment_record.media_id,
        "comment_id": comment_record.id,
        "text": comment_record.text,
        "author_id": comment_record.author_id,
        "hidden": comment_record.hidden,
        "timestamp": comment_record.ts,
        "source": "api"
    })

    return InstagramCommentSchema.model_validate(comment_record)

@api_router.delete("/comments/delete", response_model=Dict[str, Any])
async def delete_instagram_comment(
    comment_id: str = Query(..., description="Comment ID to delete"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an Instagram comment."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram page configured")
    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not configured")

    result = await instagram_client.delete_comment(
        page_access_token=page_access_token,
        comment_id=comment_id
    )
    if not result.get("success"):
        error = result.get("error", {"message": "Failed to delete comment"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to delete comment"))

    timestamp_seconds = int(datetime.now(timezone.utc).timestamp())
    existing = db.query(InstagramComment).filter(InstagramComment.id == comment_id).first()
    media_id = existing.media_id if existing else ""

    comment_record = upsert_instagram_comment(
        db=db,
        comment_id=comment_id,
        media_id=media_id,
        author_id=existing.author_id if existing else None,
        text=existing.text if existing else None,
        hidden=True,
        action=InstagramCommentAction.DELETED,
        mentioned_user_id=existing.mentioned_user_id if existing else None,
        ts=timestamp_seconds,
        attachments=None
    )
    db.commit()

    await ws_manager.broadcast_global({
        "type": "ig_comment",
        "action": comment_record.action.value,
        "media_id": comment_record.media_id,
        "comment_id": comment_record.id,
        "text": comment_record.text,
        "author_id": comment_record.author_id,
        "hidden": comment_record.hidden,
        "timestamp": comment_record.ts,
        "source": "api"
    })

    return {"success": True, "comment_id": comment_id}

@api_router.get("/instagram/mentions")
async def list_instagram_mentions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ig_user_id: Optional[str] = Query(None, description="Instagram business account ID to query")
):
    """Fetch media where the business account is mentioned."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = ig_user_id or (account.page_id if account else INSTAGRAM_PAGE_ID)
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram account available for mentions")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    mentions = await instagram_client.get_mentions(
        page_access_token=page_access_token,
        user_id=page_id
    )
    if not mentions.get("success"):
        error = mentions.get("error", {"message": "Failed to fetch mentions"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch mentions"))

    payload = {
        "type": "ig_comment",
        "action": "mentioned",
        "media": mentions.get("data", []),
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    }
    await ws_manager.broadcast_global(payload)

    return mentions

@api_router.get("/insights/account", response_model=InstagramInsightSchema)
async def get_account_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ig_user_id: Optional[str] = Query(None, description="Instagram business account ID"),
    metrics: str = Query("impressions,reach,profile_views", description="Comma separated list of metrics"),
    period: str = Query("day", description="Insights period e.g. day, week, month")
):
    """Fetch account-level Instagram insights."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = ig_user_id or (account.page_id if account else INSTAGRAM_PAGE_ID)
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram business account configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    response = await instagram_client.get_account_insights(
        page_access_token=page_access_token,
        user_id=page_id,
        metrics=metrics,
        period=period
    )
    if not response.get("success"):
        error = response.get("error", {"message": "Failed to fetch insights"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch insights"))

    metric_map = build_insight_metrics(response)
    insight_record = persist_instagram_insight(
        db=db,
        scope=InstagramInsightScope.ACCOUNT,
        entity_id=page_id,
        metrics=metric_map,
        period=period
    )

    await ws_manager.broadcast_global({
        "type": "ig_insights",
        "scope": "account",
        "entity_id": page_id,
        "metrics": metric_map,
        "timestamp": int(insight_record.fetched_at.timestamp())
    })

    return InstagramInsightSchema.model_validate(insight_record)

@api_router.get("/insights/media", response_model=InstagramInsightSchema)
async def get_media_insights(
    media_id: str = Query(..., description="Instagram media ID"),
    metrics: str = Query("impressions,reach,engagement,saved", description="Comma separated metrics"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch media-level Instagram insights."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram business account configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    response = await instagram_client.get_media_insights(
        page_access_token=page_access_token,
        media_id=media_id,
        metrics=metrics
    )
    if not response.get("success"):
        error = response.get("error", {"message": "Failed to fetch media insights"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch media insights"))

    metric_map = build_insight_metrics(response)
    insight_record = persist_instagram_insight(
        db=db,
        scope=InstagramInsightScope.MEDIA,
        entity_id=media_id,
        metrics=metric_map
    )

    await ws_manager.broadcast_global({
        "type": "ig_insights",
        "scope": "media",
        "entity_id": media_id,
        "metrics": metric_map,
        "timestamp": int(insight_record.fetched_at.timestamp())
    })

    return InstagramInsightSchema.model_validate(insight_record)

@api_router.get("/insights/story", response_model=InstagramInsightSchema)
async def get_story_insights(
    story_id: str = Query(..., description="Instagram story ID"),
    metrics: str = Query("impressions,reach,exits,replies", description="Comma separated metrics"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch story-level Instagram insights."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram business account configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    response = await instagram_client.get_story_insights(
        page_access_token=page_access_token,
        story_id=story_id,
        metrics=metrics
    )
    if not response.get("success"):
        error = response.get("error", {"message": "Failed to fetch story insights"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch story insights"))

    metric_map = build_insight_metrics(response)
    insight_record = persist_instagram_insight(
        db=db,
        scope=InstagramInsightScope.STORY,
        entity_id=story_id,
        metrics=metric_map
    )

    await ws_manager.broadcast_global({
        "type": "ig_insights",
        "scope": "story",
        "entity_id": story_id,
        "metrics": metric_map,
        "timestamp": int(insight_record.fetched_at.timestamp())
    })

    return InstagramInsightSchema.model_validate(insight_record)

@api_router.post("/marketing/events", response_model=InstagramMarketingEventSchema)
async def send_marketing_event(
    payload: InstagramMarketingEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Forward marketing events to the Meta Conversions API."""
    pixel_id = payload.pixel_id or PIXEL_ID
    if not pixel_id:
        raise HTTPException(status_code=400, detail="PIXEL_ID is not configured")

    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    access_token = resolve_instagram_access_token(db, page_id)
    if not access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not available")

    # Prepare Conversions API payload
    custom_data = dict(payload.custom_data or {})
    if payload.value is not None:
        custom_data.setdefault("value", payload.value)
    if payload.currency:
        custom_data.setdefault("currency", payload.currency)

    event_entry: Dict[str, Any] = {
        "event_name": payload.event_name,
        "event_time": payload.event_time,
        "user_data": payload.user_data or {},
        "custom_data": custom_data
    }
    if payload.event_source_url:
        event_entry["event_source_url"] = payload.event_source_url
    if payload.action_source:
        event_entry["action_source"] = payload.action_source
    if payload.event_id:
        event_entry["event_id"] = payload.event_id

    event_payload: Dict[str, Any] = {"data": [event_entry]}
    if payload.test_event_code:
        event_payload["test_event_code"] = payload.test_event_code

    result = await instagram_client.send_marketing_event(
        pixel_id=pixel_id,
        access_token=access_token,
        payload=event_payload
    )

    status = "success" if result.get("success") else "failed"
    response_json = result.get("response") if result.get("success") else result.get("error")

    marketing_event = InstagramMarketingEvent(
        event_name=payload.event_name,
        value=payload.value,
        currency=payload.currency,
        pixel_id=pixel_id,
        external_event_id=payload.event_id,
        status=status,
        payload_json=json.dumps(event_payload),
        response_json=json.dumps(response_json) if response_json else None,
        ts=payload.event_time
    )
    db.add(marketing_event)
    db.commit()
    db.refresh(marketing_event)

    await ws_manager.broadcast_global({
        "type": "ig_marketing_event",
        "event_name": payload.event_name,
        "value": payload.value,
        "currency": payload.currency,
        "ts": payload.event_time,
        "status": status
    })

    return InstagramMarketingEventSchema.model_validate(marketing_event)

@api_router.get("/facebook/comments")
async def list_facebook_comments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List Facebook comments in a chat-friendly format."""
    logger.info(f"Fetching Facebook comments for user {current_user.id}")
    try:
        # Get active Facebook pages that the user has access to
        pages = db.query(FacebookPage).filter(
            FacebookPage.user_id == current_user.id,
            FacebookPage.is_active == True,
            FacebookPage.access_token.isnot(None)
        ).all()
        
        if not pages:
            logger.warning(f"No active Facebook pages found for user {current_user.id}")
            return []

        # Log the number of pages being processed
        logger.info(f"Processing {len(pages)} Facebook pages for comments")
        
        # Verify page tokens are valid
        for page in pages:
            if not page.access_token or len(page.access_token) < 50:  # Basic token validation
                logger.error(f"Invalid access token for page {page.page_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid access token for page {page.page_name}. Please reconnect the page."
                )

        all_comments = []
        
        # Process each page with rate limiting
        for page in pages:
            if facebook_client.mode != FacebookMode.REAL:
                continue
                
            try:
                # Get real comments using the new batch method
                logger.info(f"Fetching comments for page {page.page_name} ({page.page_id})")
                page_comments = await facebook_client.get_page_feed_with_comments(
                    page_access_token=page.access_token,
                    page_id=page.page_id
                )
                
                if not page_comments:
                    logger.warning(f"No comments returned for page {page.page_name}")
                    continue
                    
                all_comments.extend(page_comments)
                logger.info(f"Retrieved {len(page_comments)} comments from page {page.page_name}")
                
                # Add rate limiting delay between pages
                if len(pages) > 1:  # Only delay if there are multiple pages
                    await asyncio.sleep(1)  # 1 second delay between pages
                    
            except Exception as e:
                error_msg = str(e)
                if "access token" in error_msg.lower():
                    logger.error(f"Access token error for page {page.page_id}: {error_msg}")
                    # Update page status in database
                    page.is_active = False
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Access token expired for page {page.page_name}. Please reconnect the page."
                    )
                logger.error(f"Error processing page {page.page_id}: {error_msg}")
                continue

        # Sort all comments by timestamp
        all_comments.sort(key=lambda x: x["timestamp"], reverse=True)

        logger.info(f"Returning {len(all_comments)} total comments")
        return all_comments
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions as they already have proper status codes
        raise http_exc
    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Error fetching Facebook comments: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Facebook comments: {error_msg}"
        )

@api_router.post("/facebook/comments/{comment_id}/reply")
async def reply_to_facebook_comment(
    comment_id: str,
    reply_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reply to a Facebook comment"""
    try:
        # Find all Facebook pages the user has access to
        pages = db.query(FacebookPage).all()
        if not pages:
            raise HTTPException(status_code=404, detail="No Facebook pages found")

        if facebook_client.mode == FacebookMode.MOCK:
            logger.info(f"Mock reply to Facebook comment {comment_id}: {reply_data.get('text', '')}")
            return {
                "success": True,
                "comment_id": comment_id,
                "mode": "mock"
            }

        # Try to reply using each page's access token until success
        # (Since we don't store which page the comment belongs to)
        for page in pages:
            try:
                result = await facebook_client.reply_to_comment(
                    page_access_token=page.access_token,
                    comment_id=comment_id,
                    message=reply_data.get("text", "")
                )
                if result.get("success"):
                    return result
            except Exception as e:
                logger.warning(f"Failed to reply using page {page.page_id}: {str(e)}")
                continue

        raise HTTPException(
            status_code=400,
            detail="Could not reply to comment with any available page access token"
        )
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
def _verify_instagram_webhook_subscription(hub_mode: str, hub_challenge: str, hub_verify_token: str):
    if instagram_client.verify_webhook_token(hub_mode, hub_verify_token):
        logger.info("Instagram webhook verification successful via client")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge

    if hub_mode == "subscribe" and INSTAGRAM_VERIFY_TOKEN and hub_verify_token == INSTAGRAM_VERIFY_TOKEN:
        logger.info("Instagram webhook verification successful via fallback token")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge

    logger.warning("Instagram webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")

@api_router.get("/webhooks/instagram")
async def verify_instagram_webhook(
    request: Request,
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token")
):
    """Verify Instagram webhook subscription"""
    
    return _verify_instagram_webhook_subscription(hub_mode, hub_challenge, hub_verify_token)

@app.get("/webhook")
async def instagram_dm_verify(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token")
):
    """Meta webhook verification handler for Instagram DMs."""
    return _verify_instagram_webhook_subscription(hub_mode, hub_challenge, hub_verify_token)

async def _handle_instagram_webhook(request: Request, db: Session) -> Dict[str, Any]:
    """Shared webhook handler for Instagram DM events."""
    try:
        body = await request.body()
        signature_sha256 = request.headers.get("X-Hub-Signature-256")
        signature_sha1 = request.headers.get("X-Hub-Signature")

        if instagram_client.mode != InstagramMode.MOCK and not instagram_client.verify_webhook_signature(
            body,
            signature_sha256,
            signature_sha1
        ):
            logger.warning("Invalid Instagram webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        data = await request.json()
        logger.info(f"Received Instagram webhook: {data.get('object')}")

        processed_events = 0

        if data.get("object") != "instagram":
            logger.info("Ignoring non-Instagram webhook payload")
            return {"status": "ignored"}

        for entry in data.get("entry", []):
            instagram_account_id = entry.get("id")
            if not instagram_account_id:
                continue

            page_access_token = resolve_instagram_access_token(db, instagram_account_id)
            if not page_access_token:
                logger.warning(f"No access token found for Instagram account {instagram_account_id}")
                continue

            for messaging_event in entry.get("messaging", []):
                message_data = messaging_event.get("message")
                if not message_data:
                    continue

                sender_id = messaging_event.get("sender", {}).get("id")
                recipient_id = messaging_event.get("recipient", {}).get("id")
                if not sender_id or not recipient_id:
                    continue

                is_echo = message_data.get("is_echo", False)
                direction = InstagramMessageDirection.OUTBOUND if is_echo or sender_id == instagram_account_id else InstagramMessageDirection.INBOUND
                igsid = sender_id if direction == InstagramMessageDirection.INBOUND else recipient_id

                processed_payload = await instagram_client.process_webhook_message(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    message_data=message_data,
                    instagram_account_id=instagram_account_id
                )

                attachments = processed_payload.get("attachments") or []
                if not isinstance(attachments, list):
                    attachments = [attachments]
                text_content = processed_payload.get("text") or ""

                raw_timestamp = messaging_event.get("timestamp") or int(datetime.now(timezone.utc).timestamp() * 1000)
                timestamp_seconds = int(raw_timestamp / 1000)
                event_datetime = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)

                last_message_preview = text_content or ("[attachment]" if attachments else None)

                instagram_user = db.query(InstagramUser).filter(InstagramUser.igsid == igsid).first()
                if not instagram_user:
                    instagram_user = InstagramUser(
                        igsid=igsid,
                        first_seen_at=event_datetime,
                        last_seen_at=event_datetime,
                        last_message=last_message_preview
                    )
                    db.add(instagram_user)
                else:
                    instagram_user.last_seen_at = event_datetime
                    if last_message_preview:
                        instagram_user.last_message = last_message_preview

                ig_message = InstagramMessage(
                    igsid=igsid,
                    direction=direction,
                    text=text_content,
                    attachments_json=json.dumps(attachments) if attachments else None,
                    ts=timestamp_seconds,
                    created_at=event_datetime
                )
                db.add(ig_message)

                chat: Optional[Chat] = None
                new_message: Optional[Message] = None

                if direction == InstagramMessageDirection.INBOUND:
                    chat = db.query(Chat).filter(
                        Chat.instagram_user_id == sender_id,
                        Chat.platform == MessagePlatform.INSTAGRAM,
                        Chat.facebook_page_id == instagram_account_id
                    ).first()

                    if not chat:
                        profile = await instagram_client.get_user_profile(
                            page_access_token=page_access_token,
                            user_id=sender_id
                        )
                        username = profile.get("username") or profile.get("name") or f"IG User {sender_id[:8]}"
                        profile_pic_url = profile.get("profile_pic_url") or profile.get("profile_pic")
                        if not profile_pic_url:
                            profile_pic_url = f"https://via.placeholder.com/150?text={sender_id[:8]}"

                        chat = Chat(
                            instagram_user_id=sender_id,
                            username=username,
                            profile_pic_url=profile_pic_url,
                            platform=MessagePlatform.INSTAGRAM,
                            facebook_page_id=instagram_account_id,
                            status=ChatStatus.UNASSIGNED
                        )
                        db.add(chat)
                        db.flush()

                    new_message = Message(
                        chat_id=chat.id,
                        sender=MessageSender.INSTAGRAM_USER,
                        content=text_content,
                        message_type=MessageType.TEXT,
                        platform=MessagePlatform.INSTAGRAM,
                        timestamp=event_datetime
                    )
                    db.add(new_message)

                    chat.last_message = text_content
                    chat.unread_count += 1
                    chat.updated_at = event_datetime

                db.flush()
                db.commit()

                db.refresh(ig_message)
                if new_message:
                    db.refresh(new_message)

                notify_users = set()
                if direction == InstagramMessageDirection.INBOUND:
                    notify_users = gather_dm_notify_users(db, chat)
                else:
                    existing_chat = db.query(Chat).filter(
                        Chat.instagram_user_id == igsid,
                        Chat.platform == MessagePlatform.INSTAGRAM
                    ).first()
                    notify_users = gather_dm_notify_users(db, existing_chat)

                # Broadcast legacy chat payload for inbound messages
                if new_message and notify_users:
                    message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")
                    await ws_manager.broadcast_to_users(notify_users, {
                        "type": "new_message",
                        "chat_id": str(chat.id),
                        "platform": chat.platform.value,
                        "sender_id": sender_id,
                        "message": message_payload
                    })

                # Broadcast DM payload
                dm_payload = {
                    "type": "ig_dm",
                    "legacy_type": "instagram_dm",
                    "direction": direction.value,
                    "igsid": igsid,
                    "text": text_content,
                    "attachments": attachments,
                    "timestamp": timestamp_seconds,
                    "message_id": ig_message.id,
                    "page_id": instagram_account_id,
                    "delivery_status": "received" if direction == InstagramMessageDirection.INBOUND else "delivered"
                }

                if notify_users:
                    await ws_manager.broadcast_to_users(notify_users, dm_payload)

                processed_events += 1

            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})
                if field not in {"comments", "mention", "mentions"}:
                    continue

                comment_id = value.get("id") or value.get("comment_id")
                media_id = value.get("media_id") or value.get("parent_id") or value.get("post_id")
                if not comment_id or not media_id:
                    logger.debug("Skipping comment webhook change lacking IDs: %s", value)
                    continue

                verb = value.get("verb") or value.get("action") or "add"
                action_map = {
                    "add": InstagramCommentAction.CREATED,
                    "edited": InstagramCommentAction.UPDATED,
                    "update": InstagramCommentAction.UPDATED,
                    "delete": InstagramCommentAction.DELETED,
                    "remove": InstagramCommentAction.DELETED
                }
                action = action_map.get(verb.lower(), InstagramCommentAction.CREATED)

                author_id = None
                from_data = value.get("from") or value.get("user") or {}
                if isinstance(from_data, dict):
                    author_id = from_data.get("id")

                mentioned_user_id = None
                to_data = value.get("to") or {}
                if isinstance(to_data, dict):
                    mentioned_user_id = to_data.get("id")

                text = value.get("text") or value.get("message")
                hidden = bool(value.get("hidden", False))
                raw_ts = value.get("timestamp") or value.get("created_time") or int(datetime.now(timezone.utc).timestamp() * 1000)
                if raw_ts > 10**12:
                    timestamp_seconds = int(raw_ts / 1000)
                else:
                    timestamp_seconds = int(raw_ts)
                comment_ts = timestamp_seconds

                comment_record = upsert_instagram_comment(
                    db=db,
                    comment_id=comment_id,
                    media_id=media_id,
                    author_id=author_id,
                    text=text,
                    hidden=hidden,
                    action=action,
                    mentioned_user_id=mentioned_user_id,
                    ts=comment_ts,
                    attachments=None
                )
                db.commit()
                db.refresh(comment_record)

                comment_payload = {
                    "type": "ig_comment",
                    "action": comment_record.action.value,
                    "media_id": comment_record.media_id,
                    "comment_id": comment_record.id,
                    "text": comment_record.text,
                    "author_id": comment_record.author_id,
                    "hidden": comment_record.hidden,
                    "timestamp": comment_record.ts,
                    "mentioned_user_id": comment_record.mentioned_user_id
                }

                await ws_manager.broadcast_global(comment_payload)
                processed_events += 1

        return {"status": "received", "processed_events": processed_events}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error processing Instagram webhook: {exc}", exc_info=True)
        # Return 200 to avoid Facebook retrying
        return {"status": "error", "message": str(exc)}

@api_router.post("/webhooks/instagram")
async def handle_instagram_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Instagram webhook"""
    return await _handle_instagram_webhook(request, db)

@app.post("/webhook")
async def instagram_dm_webhook(request: Request, db: Session = Depends(get_db)):
    """Unified webhook entrypoint for Meta subscriptions."""
    return await _handle_instagram_webhook(request, db)

@app.post("/messages/send")
@app.post("/send", include_in_schema=False)
async def instagram_dm_send(
    payload: InstagramSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send an Instagram DM via the Meta Graph API."""
    page_id = INSTAGRAM_PAGE_ID

    chat = db.query(Chat).filter(
        Chat.instagram_user_id == payload.igsid,
        Chat.platform == MessagePlatform.INSTAGRAM
    ).first()

    if chat and chat.facebook_page_id:
        page_id = chat.facebook_page_id

    if not page_id:
        raise HTTPException(status_code=400, detail="Instagram page ID not configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=500, detail="Instagram page access token missing")

    send_result = await instagram_client.send_dm(
        page_id=page_id,
        page_access_token=page_access_token,
        recipient_id=payload.igsid,
        text=payload.text if payload.has_text else None,
        attachments=payload.attachments
    )

    if not send_result.get("success"):
        error_message = send_result.get("error", "Failed to send message")
        logger.error(f"Failed to send Instagram DM to {payload.igsid}: {error_message}")
        raise HTTPException(status_code=502, detail=error_message)

    now_utc = datetime.now(timezone.utc)
    timestamp_seconds = int(now_utc.timestamp())
    attachments_json = json.dumps(payload.attachments) if payload.attachments else None
    message_content = payload.text or ("[attachment]" if payload.attachments else "")
    last_message_preview = message_content or None

    instagram_user = db.query(InstagramUser).filter(InstagramUser.igsid == payload.igsid).first()
    if not instagram_user:
        instagram_user = InstagramUser(
            igsid=payload.igsid,
            first_seen_at=now_utc,
            last_seen_at=now_utc,
            last_message=last_message_preview
        )
        db.add(instagram_user)
    else:
        instagram_user.last_seen_at = now_utc
        if last_message_preview:
            instagram_user.last_message = last_message_preview

    outbound_message = InstagramMessage(
        igsid=payload.igsid,
        direction=InstagramMessageDirection.OUTBOUND,
        text=payload.text,
        attachments_json=attachments_json,
        ts=timestamp_seconds,
        created_at=now_utc
    )
    db.add(outbound_message)

    if not chat:
        profile = await instagram_client.get_user_profile(
            page_access_token=page_access_token,
            user_id=payload.igsid
        )
        username = profile.get("username") or profile.get("name") or f"IG User {payload.igsid[:8]}"
        profile_pic_url = profile.get("profile_pic_url") or profile.get("profile_pic")
        if not profile_pic_url:
            profile_pic_url = f"https://via.placeholder.com/150?text={payload.igsid[:8]}"

        chat = Chat(
            instagram_user_id=payload.igsid,
            username=username,
            profile_pic_url=profile_pic_url,
            platform=MessagePlatform.INSTAGRAM,
            facebook_page_id=page_id,
            status=ChatStatus.UNASSIGNED
        )
        db.add(chat)
        db.flush()
    else:
        if not chat.facebook_page_id:
            chat.facebook_page_id = page_id

    if last_message_preview:
        chat.last_message = last_message_preview
    chat.updated_at = now_utc

    message_record = Message(
        chat_id=chat.id,
        sender=MessageSender.AGENT,
        content=message_content,
        message_type=MessageType.TEXT,
        platform=MessagePlatform.INSTAGRAM,
        timestamp=now_utc
    )
    db.add(message_record)

    db.flush()
    db.commit()

    db.refresh(outbound_message)
    db.refresh(message_record)
    db.refresh(chat)

    notify_users = gather_dm_notify_users(db, chat)

    # Broadcast chat message event
    if notify_users:
        message_payload = MessageResponse.model_validate(message_record).model_dump(mode="json")
        await ws_manager.broadcast_to_users(notify_users, {
            "type": "new_message",
            "chat_id": str(chat.id),
            "platform": chat.platform.value,
            "sender": MessageSender.AGENT.value,
            "message": message_payload
        })

        dm_payload = {
            "type": "ig_dm",
            "legacy_type": "instagram_dm",
            "direction": InstagramMessageDirection.OUTBOUND.value,
            "igsid": payload.igsid,
            "text": payload.text,
            "attachments": payload.attachments or [],
            "timestamp": timestamp_seconds,
            "message_id": outbound_message.id,
            "graph_message_id": send_result.get("message_id"),
            "page_id": page_id,
            "delivery_status": "sent",
            "sent_by": str(current_user.id)
        }
        await ws_manager.broadcast_to_users(notify_users, dm_payload)

    logger.info(f"Instagram DM sent to {payload.igsid} by user {current_user.id}")
    return {
        "success": True,
        "message_id": outbound_message.id,
        "graph_message_id": send_result.get("message_id"),
        "timestamp": timestamp_seconds,
        "igsid": payload.igsid
    }

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

@api_router.post("/chats/{chat_id}/mark_read")
def mark_chat_as_read(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a chat as read by resetting unread count"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check access - agents can only mark their assigned chats, admins can mark any
    if current_user.role == UserRole.AGENT and chat.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Reset unread count
    chat.unread_count = 0
    db.commit()
    
    logger.info(f"Chat {chat_id} marked as read by user {current_user.id}")
    return {"success": True, "chat_id": chat_id}

@api_router.post("/chats/{chat_id}/message", response_model=MessageResponse)
async def send_message(chat_id: str, message_data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check access
    if current_user.role == UserRole.AGENT and chat.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Enforce Meta's 24-hour human agent policy
    last_customer_message = (
        db.query(Message)
        .filter(
            Message.chat_id == chat_id,
            Message.sender != MessageSender.AGENT
        )
        .order_by(Message.timestamp.desc())
        .first()
    )

    if last_customer_message:
        # Ensure the timestamp is timezone-aware before comparison
        msg_timestamp = last_customer_message.timestamp
        if not msg_timestamp.tzinfo:
            msg_timestamp = msg_timestamp.replace(tzinfo=timezone.utc)
        window_deadline = msg_timestamp + timedelta(hours=24)
        if datetime.now(timezone.utc) > window_deadline:
            raise HTTPException(
                status_code=403,
                detail="Outside the 24-hour human agent window. Send an approved template instead."
            )

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
    
    # Add admin users
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
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
    if current_user.role == UserRole.ADMIN:
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
        user_id=current_user.id,
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

# Template Endpoints
@api_router.get("/templates", response_model=List[MessageTemplateResponse])
def list_templates(
    platform: Optional[MessagePlatform] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all templates with optional filtering by platform and category"""
    query = db.query(MessageTemplate)
    
    if platform:
        query = query.filter(MessageTemplate.platform == platform)
    if category:
        query = query.filter(MessageTemplate.category == category)
    
    templates = query.order_by(MessageTemplate.created_at.desc()).all()
    return templates

@api_router.post("/templates", response_model=MessageTemplateResponse)
def create_template(
    template_data: MessageTemplateCreate,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Create a new template (admin only)"""
    if template_data.is_meta_approved and not template_data.meta_template_id:
        raise HTTPException(
            status_code=400,
            detail="Meta-approved templates must include a Meta template ID"
        )

    new_template = MessageTemplate(
        name=template_data.name,
        content=template_data.content,
        category=template_data.category,
        platform=template_data.platform,
        meta_template_id=template_data.meta_template_id,
        is_meta_approved=template_data.is_meta_approved,
        created_by=current_user.id
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    logger.info(f"Template created: {new_template.id} by user {current_user.email}")
    return new_template

@api_router.put("/templates/{template_id}", response_model=MessageTemplateResponse)
def update_template(
    template_id: str,
    template_data: MessageTemplateUpdate,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Update a template (admin only)"""
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Only allow updating basic template info
    if hasattr(template_data, 'name') and template_data.name is not None:
        template.name = template_data.name
    if hasattr(template_data, 'content') and template_data.content is not None:
        template.content = template_data.content
    if hasattr(template_data, 'category') and template_data.category is not None:
        template.category = template_data.category
    if hasattr(template_data, 'platform') and template_data.platform is not None:
        template.platform = template_data.platform
        
    # Don't allow manual updates of Meta approval status
    if hasattr(template_data, 'is_meta_approved') or hasattr(template_data, 'meta_template_id'):
        raise HTTPException(
            status_code=400,
            detail="Meta approval status and template ID can only be updated through the Meta approval process"
        )

    if template.is_meta_approved and not template.meta_template_id:
        raise HTTPException(
            status_code=400,
                detail="Invalid Meta template ID format. Must start with 'meta_'"
            )
        template.meta_template_id = template_data.meta_template_id
        template.is_meta_approved = True  # Auto-approve if valid Meta template ID is provided
    
    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Template updated: {template_id} by user {current_user.email}")
    return template

@api_router.post("/templates/{template_id}/submit-to-meta")
async def submit_template_to_meta(
    template_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Submit a template for Meta's approval"""
    from meta_template_api import meta_template_api
    
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.meta_submission_status == "pending":
        raise HTTPException(status_code=400, detail="Template is already pending Meta approval")

    # Get associated Facebook page
    facebook_page = db.query(FacebookPage).filter(FacebookPage.is_active == True).first()
    if not facebook_page:
        raise HTTPException(status_code=400, detail="No active Facebook page found")

    try:
        # Log template and Facebook page info for debugging
        logger.info(f"Attempting to submit template {template_id} using Facebook page {facebook_page.page_id}")
        logger.info(f"Template details - Name: {template.name}, Category: {template.category}")
        
        # Validate category format
        valid_categories = ['CUSTOMER_SUPPORT', 'MARKETING', 'UTILITY']
        category = template.category.upper()
        if category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid template category. Must be one of: {', '.join(valid_categories)}"
            )
        
        # Prepare template data
        template_data = {
            "name": template.name,
            "category": category,
            "content": template.content,
            "platform": template.platform
        }
        
        # Submit to Meta
        result = await meta_template_api.submit_template(facebook_page.page_id, template_data)
        
        # Update template with submission info
        template.meta_submission_id = result['id']
        template.meta_submission_status = result['status']
        template.updated_at = datetime.now(timezone.utc)
        
        try:
            db.commit()
        except Exception as db_error:
            logger.error(f"Database error while updating template status: {db_error}")
            raise HTTPException(
                status_code=500,
                detail="Template was submitted but failed to update status in database"
            )
        
        return {
            "message": "Template submitted for Meta approval",
            "status": result['status'],
            "meta_submission_id": result['id']
        }
        
    except HTTPException as http_error:
        # Re-raise HTTP exceptions with their original status codes
        raise http_error
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to submit template to Meta: {error_msg}")
        # Include more details in the error message
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit template to Meta: {error_msg}"
        )

@api_router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Delete a template (admin only)"""
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    logger.info(f"Template deleted: {template_id} by user {current_user.email}")
    return {"success": True, "message": "Template deleted"}

@api_router.get("/templates/{template_id}/meta-status")
async def check_meta_template_status(
    template_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Check the Meta approval status of a template"""
    from meta_template_api import meta_template_api
    
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template.meta_submission_id:
        raise HTTPException(status_code=400, detail="Template has not been submitted to Meta")

    try:
        # Check template status with Meta
        result = await meta_template_api.check_template_status(template.meta_submission_id)
        
        # Update template status in database
        old_status = template.meta_submission_status
        template.meta_submission_status = result['status']
        
        # If status changed to approved, update template
        if result['status'] == 'approved' and old_status != 'approved':
            template.is_meta_approved = True
            template.meta_template_id = result.get('template_id')  # Meta may provide a permanent template ID
            
        template.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "message": "Template status retrieved successfully",
            "status": result['status'],
            "template_id": template.meta_template_id
        }
    except Exception as e:
        logger.error(f"Failed to check template status with Meta: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check template status. Please try again later."
        )

@api_router.post("/templates/{template_id}/send", response_model=MessageResponse)
async def send_template(
    template_id: str,
    send_request: TemplateSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a template message to a chat"""
    # Get template
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get chat
    chat = db.query(Chat).filter(Chat.id == send_request.chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check access
    if current_user.role == UserRole.AGENT and chat.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check platform match
    if template.platform != chat.platform:
        raise HTTPException(status_code=400, detail=f"Template platform ({template.platform}) doesn't match chat platform ({chat.platform})")
    
    # Enforce Meta's 24-hour policy for template sending
    last_customer_message = (
        db.query(Message)
        .filter(
            Message.chat_id == chat.id,
            Message.sender != MessageSender.AGENT
        )
        .order_by(Message.timestamp.desc())
        .first()
    )

    # Always allow template messages for now during testing
    # Comment out the 24-hour window check temporarily
    """
    if last_customer_message:
        window_deadline = last_customer_message.timestamp + timedelta(hours=24)
        if datetime.now(timezone.utc) > window_deadline and not template.is_meta_approved:
            raise HTTPException(
                status_code=403,
                detail="Outside the 24-hour human agent window. Only Meta-approved templates can be sent."
            )
    """

    # Perform variable substitution
    message_content = template.content
    if send_request.variables:
        for key, value in send_request.variables.items():
            placeholder = f"{{{key}}}"
            message_content = message_content.replace(placeholder, str(value))
    
    # Auto-populate common variables from chat context
    message_content = message_content.replace("{username}", chat.username)
    message_content = message_content.replace("{platform}", chat.platform.value)
    
    meta_template_tag = os.getenv("META_TEMPLATE_TAG", "ACCOUNT_UPDATE")
    use_meta_template = template.is_meta_approved

    if use_meta_template and not template.meta_template_id:
        raise HTTPException(
            status_code=400,
            detail="Meta-approved template is missing the Meta template ID"
        )
    
    if instagram_client.mode == InstagramMode.MOCK and facebook_client.mode == FacebookMode.MOCK:
        new_message = Message(
            chat_id=chat.id,
            sender=MessageSender.AGENT,
            content=message_content,
            message_type=MessageType.TEXT,
            platform=chat.platform
        )
        db.add(new_message)
        chat.last_message = message_content
        chat.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(new_message)
        logger.info(f"Template message sent (mock mode) in chat {chat.id}")
    else:
        # Send through appropriate platform
        if chat.platform == MessagePlatform.FACEBOOK:
            if chat.facebook_page_id:
                fb_page = db.query(FacebookPage).filter(FacebookPage.page_id == chat.facebook_page_id).first()
                if fb_page and fb_page.is_active:
                    if use_meta_template:
                        result = await facebook_client.send_template_message(
                            page_access_token=fb_page.access_token,
                            recipient_id=chat.instagram_user_id,
                            text=message_content,
                            template_id=template.meta_template_id,
                            tag=meta_template_tag
                        )
                    else:
                        result = await facebook_client.send_text_message(
                            page_access_token=fb_page.access_token,
                            recipient_id=chat.instagram_user_id,
                            text=message_content
                        )
                    if not result.get("success"):
                        raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
                else:
                    raise HTTPException(status_code=400, detail="Facebook page not found or inactive")
            else:
                raise HTTPException(status_code=400, detail="No Facebook page associated with this chat")
        
        elif chat.platform == MessagePlatform.INSTAGRAM:
            if chat.facebook_page_id:
                ig_account = db.query(InstagramAccount).filter(InstagramAccount.page_id == chat.facebook_page_id).first()
                if ig_account:
                    if use_meta_template:
                        result = await instagram_client.send_template_message(
                            page_access_token=ig_account.access_token,
                            recipient_id=chat.instagram_user_id,
                            text=message_content,
                            template_id=template.meta_template_id,
                            tag=meta_template_tag
                        )
                    else:
                        result = await instagram_client.send_text_message(
                            page_access_token=ig_account.access_token,
                            recipient_id=chat.instagram_user_id,
                            text=message_content
                        )
                    if not result.get("success"):
                        raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
                else:
                    raise HTTPException(status_code=400, detail="Instagram account not found")
            else:
                raise HTTPException(status_code=400, detail="No Instagram account associated with this chat")
        
        new_message = Message(
            chat_id=chat.id,
            sender=MessageSender.AGENT,
            content=message_content,
            message_type=MessageType.TEXT,
            platform=chat.platform
        )
        db.add(new_message)
        chat.last_message = message_content
        chat.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(new_message)
    
    # Broadcast via WebSocket
    message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")
    notify_users = set()
    if chat.assigned_to:
        notify_users.add(str(chat.assigned_to))
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    notify_users.update(str(user.id) for user in admin_users)
    
    await ws_manager.broadcast_to_users(notify_users, {
        "type": "new_message",
        "chat_id": chat.id,
        "message": message_payload
    })
    
    logger.info(f"Template {template_id} sent to chat {chat.id}")
    return new_message

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

                        # Get fresh user profile data if chat doesn't exist or username is generic
                        should_update_profile = not chat or (chat and chat.username.startswith(("FB User", "User")))
                        if should_update_profile:
                            profile = await facebook_client.get_user_profile(
                                page_access_token=fb_page.access_token,
                                user_id=sender_id
                            )
                            username = profile.get("name", f"FB User {sender_id[:8]}")
                            
                            # Create new chat
                            profile_pic_url = profile.get("profile_pic") if isinstance(profile, dict) else None
                            # Support older get_user_profile shapes (profile_pic vs profile_pic_url)
                            if not profile_pic_url:
                                profile_pic_url = profile.get("profile_pic_url") if isinstance(profile, dict) else None
                            if not profile_pic_url:
                                profile_pic_url = f"https://via.placeholder.com/150?text={sender_id[:8]}"

                            chat = Chat(
                                instagram_user_id=sender_id,
                                username=username,
                                profile_pic_url=profile_pic_url,
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
                        chat.unread_count += 1
                        chat.updated_at = datetime.now(timezone.utc)
                        
                        db.commit()
                        db.refresh(new_message)
                        logger.info(f"Processed Facebook message from {sender_id} on page {page_id}")
                        
                        # Notify relevant users about new message
                        notify_users = set()
                        
                        # Add assigned agent if any
                        if chat.assigned_to:
                            notify_users.add(str(chat.assigned_to))
                        
                        # Add admin users
                        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
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
@app.websocket("/messenger/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get('token')
    if not token:
        await websocket.close(code=1008)  # Policy violation
        logger.error("WebSocket connection rejected: No token provided")
        return

    try:
        # Verify token before accepting connection
        payload = decode_access_token(token)
        if not payload or 'user_id' not in payload:
            await websocket.close(code=1008)
            logger.error("WebSocket connection rejected: Invalid token")
            return
        
        # Extract user ID and set up connection
        user_id = str(payload['user_id'])
        await ws_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected for user {user_id}")
        
        while True:
            try:
                # Keep connection alive and handle any incoming messages
                data = await websocket.receive_json()
                
                # Handle ping messages to keep connection alive
                if data.get('type') == 'ping':
                    await websocket.send_json({'type': 'pong'})
                    continue
                
                # Handle any other incoming messages here if needed
                logger.debug(f"Received WebSocket message from user {user_id}: {data}")
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
                break
            except ValueError as json_error:
                logger.warning(f"Invalid JSON received from user {user_id}: {json_error}")
                continue
            except Exception as e:
                logger.error(f"Error handling WebSocket message from user {user_id}: {e}")
                continue
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Always clean up the connection
        try:
            ws_manager.disconnect(websocket, user_id)
            logger.info(f"WebSocket connection cleaned up for user {user_id}")
        except Exception as cleanup_error:
            logger.error(f"Error during WebSocket cleanup: {cleanup_error}")

# Include the router in the main app
app.include_router(api_router)

# Configure CORS
# cors_origins = ["*"]  # Allow all origins

# app.add_middleware(
#     CORSMiddleware,
#     allow_credentials=True,
#     allow_origins=cors_origins,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["*"]
# )

# Configure CORS
cors_origins_str = os.getenv('CORS_ORIGINS', '*')
origins = cors_origins_str.split(',') if cors_origins_str != '*' else ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

