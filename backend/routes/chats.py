from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import (
    Chat,
    ChatStatus,
    FacebookUser,
    InstagramUser,
    MessagePlatform,
    MessageSender,
    MessageType,
    User,
    UserRole,
)
from routes.chat_helpers import (
    _message_model_for_platform,
    _assign_chat_round_robin,
    _chat_requires_agent_reply,
    _merge_message_metadata,
    _requires_sqlite_instagram_fallback,
    _serialize_user_light,
    create_chat_message_record,
    gather_dm_notify_users,
    normalize_message_sender,
)
from routes.dependencies import get_current_user, require_permissions
from schemas import ChatAssign, ChatResponse, ChatWithMessages, DashboardStats, MessageCreate, MessageResponse, UserResponse
from utils.timezone import utc_now
from websocket_manager import manager as ws_manager

router = APIRouter()


@router.get("/chats", response_model=List[ChatResponse])
def list_chats(
    status_filter: Optional[str] = None,
    assigned_to_me: bool = False,
    platform: Optional[str] = None,
    assigned_to: Optional[str] = None,
    unseen: Optional[bool] = None,
    not_replied: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Chat).options(
        joinedload(Chat.assigned_agent),
        joinedload(Chat.instagram_user),
        joinedload(Chat.facebook_user)
    )

    if status_filter:
        if status_filter == "assigned":
            query = query.filter(Chat.status == ChatStatus.ASSIGNED)
        elif status_filter == "unassigned":
            query = query.filter(Chat.status == ChatStatus.UNASSIGNED)

    if platform:
        if platform.upper() == "INSTAGRAM":
            query = query.filter(Chat.platform == MessagePlatform.INSTAGRAM)
        elif platform.upper() == "FACEBOOK":
            query = query.filter(Chat.platform == MessagePlatform.FACEBOOK)

    if assigned_to and assigned_to.lower() == "unassigned":
        query = query.filter(Chat.assigned_to.is_(None))
    elif assigned_to:
        query = query.filter(Chat.assigned_to == assigned_to)

    if unseen is True:
        query = query.filter(Chat.unread_count > 0)
    elif unseen is False:
        query = query.filter(Chat.unread_count == 0)

    if not_replied is True:
        query = query.filter(Chat.last_incoming_at.isnot(None)).filter(
            or_(Chat.last_outgoing_at.is_(None), Chat.last_outgoing_at < Chat.last_incoming_at)
        )
    elif not_replied is False:
        query = query.filter(
            or_(
                Chat.last_incoming_at.is_(None),
                Chat.last_outgoing_at.isnot(None),
                Chat.last_outgoing_at >= Chat.last_incoming_at,
            )
        )

    if assigned_to_me or current_user.role != UserRole.ADMIN:
        query = query.filter(Chat.assigned_to == current_user.id)

    chats = query.order_by(Chat.updated_at.desc()).all()

    missing_instagram_ids = {
        chat.instagram_user_id
        for chat in chats
        if chat.platform == MessagePlatform.INSTAGRAM
        and chat.instagram_user_id
        and chat.instagram_user is None
    }
    if missing_instagram_ids:
        instagram_map = {
            user.igsid: user
            for user in db.query(InstagramUser).filter(InstagramUser.igsid.in_(missing_instagram_ids)).all()
        }
        for chat in chats:
            if chat.platform == MessagePlatform.INSTAGRAM and not chat.instagram_user:
                resolved = instagram_map.get(chat.instagram_user_id)
                if resolved:
                    chat.instagram_user = resolved

    missing_facebook_ids = {
        chat.facebook_user_id
        for chat in chats
        if chat.platform == MessagePlatform.FACEBOOK
        and chat.facebook_user_id
        and chat.facebook_user is None
    }
    if missing_facebook_ids:
        facebook_map = {
            user.id: user
            for user in db.query(FacebookUser).filter(FacebookUser.id.in_(missing_facebook_ids)).all()
        }
        for chat in chats:
            if chat.platform == MessagePlatform.FACEBOOK and not chat.facebook_user:
                resolved = facebook_map.get(chat.facebook_user_id)
                if resolved:
                    chat.facebook_user = resolved

    for chat in chats:
        chat.pending_agent_reply = _chat_requires_agent_reply(chat)

    return chats


@router.get("/chats/{chat_id}", response_model=ChatWithMessages)
def get_chat(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).options(
        joinedload(Chat.assigned_agent),
        joinedload(Chat.instagram_user),
        joinedload(Chat.facebook_user)
    ).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages_query = db.query(
        _message_model_for_platform(chat.platform)
    ).filter(_message_model_for_platform(chat.platform).chat_id == chat.id)
    if chat.platform == MessagePlatform.INSTAGRAM:
        messages_query = messages_query.options(joinedload(InstagramChatMessage.instagram_user))
    messages = messages_query.order_by(_message_model_for_platform(chat.platform).timestamp).all()

    for msg in messages:
        normalize_message_sender(msg)
        if chat.platform == MessagePlatform.INSTAGRAM and isinstance(msg, InstagramChatMessage) and msg.instagram_user:
            msg.instagram_user.username = msg.instagram_user.username or msg.instagram_user.name

    message_responses = [MessageResponse.model_validate(msg) for msg in messages]
    chat.messages = message_responses
    chat.pending_agent_reply = _chat_requires_agent_reply(chat)

    return ChatWithMessages.model_validate(chat)


@router.post("/chats/{chat_id}/assign")
def assign_chat(
    chat_id: str,
    payload: ChatAssign,
    current_user: User = Depends(require_permissions("CHAT_ASSIGN")),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if payload.assign_to_user_id:
        user = db.query(User).filter(User.id == payload.assign_to_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.role != UserRole.AGENT:
            raise HTTPException(status_code=400, detail="Can only assign chats to agents")
        chat.assigned_to = payload.assign_to_user_id
        chat.status = ChatStatus.ASSIGNED
    else:
        chat.assigned_to = None
        chat.status = ChatStatus.UNASSIGNED
    db.commit()
    return ChatResponse.model_validate(chat)


@router.post("/chats/{chat_id}/mark_read")
def mark_chat_as_read(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.platform == MessagePlatform.INSTAGRAM and chat.instagram_user_id:
        chat.instagram_user = chat.instagram_user or db.query(InstagramUser).filter(
            InstagramUser.igsid == chat.instagram_user_id
        ).first()
        if chat.instagram_user:
            chat.instagram_user.last_seen_at = utc_now()
    chat.unread_count = 0
    db.commit()
    return {"success": True, "chat_id": chat_id}


@router.post("/chats/{chat_id}/message", response_model=MessageResponse)
async def send_message(
    chat_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat.platform not in {MessagePlatform.INSTAGRAM, MessagePlatform.FACEBOOK}:
        raise HTTPException(status_code=400, detail="Unsupported chat platform")

    message_content = message_data.content.strip()
    if not message_content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    reply_metadata: Dict[str, Any] = {}
    if message_data.reply_to_message_id:
        message_model = _message_model_for_platform(chat.platform)
        reply_target = (
            db.query(message_model)
            .filter(
                message_model.id == message_data.reply_to_message_id,
                message_model.chat_id == chat.id
            )
            .first()
        )
        if not reply_target:
            raise HTTPException(status_code=404, detail="Reply target not found")
        sender_value = reply_target.sender.value if isinstance(reply_target.sender, MessageSender) else str(reply_target.sender or "")
        sender_lower = sender_value.lower()
        if sender_lower in {"agent", "instagram_page"}:
            reply_sender_label = "You"
        else:
            if chat.platform == MessagePlatform.FACEBOOK and not chat.facebook_user and chat.facebook_user_id:
                chat.facebook_user = db.query(FacebookUser).filter(FacebookUser.id == chat.facebook_user_id).first()
            if chat.platform == MessagePlatform.INSTAGRAM and not chat.instagram_user and chat.instagram_user_id:
                chat.instagram_user = db.query(InstagramUser).filter(InstagramUser.igsid == chat.instagram_user_id).first()
            reply_sender_label = (
                (chat.facebook_user.name if chat.facebook_user else None)
                or (chat.instagram_user.name if chat.instagram_user else None)
                or chat.username
                or "User"
            )
        preview_text = message_data.reply_preview or reply_target.content or "[attachment]"
        preview_text = preview_text.strip()
        if not preview_text:
            preview_text = "[attachment]"
        if len(preview_text) > 200:
            preview_text = f"{preview_text[:197]}..."
        reply_metadata = {
            "reply_to": reply_target.id,
            "reply_preview": preview_text,
            "reply_sender": reply_sender_label,
            "reply_sender_type": sender_lower,
        }

    event_time = utc_now()
    new_message = create_chat_message_record(
        chat,
        sender=MessageSender.AGENT,
        content=message_content,
        message_type=MessageType.TEXT,
        timestamp=event_time,
        is_ticklegram=False,
        metadata_json=_merge_message_metadata(
            None,
            sent_by=current_user,
            extra=reply_metadata or None
        )
    )
    new_message.attachments = []
    db.add(new_message)
    chat.last_message = message_content
    chat.last_outgoing_at = event_time
    chat.updated_at = event_time
    db.commit()
    db.refresh(new_message)

    message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")
    notify_users: Set[str] = gather_dm_notify_users(db, chat=chat)

    await ws_manager.broadcast_to_users(notify_users, {
        "type": "new_message",
        "chat_id": chat.id,
        "message": message_payload
    })

    return new_message


@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        total_chats = db.query(Chat).filter(Chat.assigned_to == current_user.id).count()
        assigned_chats = total_chats
        unassigned_chats = 0
    else:
        total_chats = db.query(Chat).count()
        assigned_chats = db.query(Chat).filter(Chat.status == ChatStatus.ASSIGNED).count()
        unassigned_chats = db.query(Chat).filter(Chat.status == ChatStatus.UNASSIGNED).count()
    instagram_chats = db.query(Chat).filter(
        Chat.platform == MessagePlatform.INSTAGRAM,
        Chat.assigned_to == (current_user.id if current_user.role != UserRole.ADMIN else Chat.assigned_to)
    ).count()
    facebook_chats = db.query(Chat).filter(
        Chat.platform == MessagePlatform.FACEBOOK,
        Chat.assigned_to == (current_user.id if current_user.role != UserRole.ADMIN else Chat.assigned_to)
    ).count()

    return DashboardStats(
        total_chats=total_chats,
        assigned_chats=assigned_chats,
        unassigned_chats=unassigned_chats,
        instagram_chats=instagram_chats,
        facebook_chats=facebook_chats,
    )
