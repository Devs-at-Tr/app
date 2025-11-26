import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from models import (
    AssignmentCursor,
    Chat,
    ChatStatus,
    FacebookMessage,
    FacebookUser,
    InstagramMessage as InstagramChatMessage,
    InstagramUser,
    MessagePlatform,
    MessageSender,
    MessageType,
    User,
    UserRole,
)
from utils.timezone import utc_now

ChatMessageModel = Union[InstagramChatMessage, FacebookMessage]


def _message_model_for_platform(platform: MessagePlatform) -> Type[ChatMessageModel]:
    return InstagramChatMessage if platform == MessagePlatform.INSTAGRAM else FacebookMessage


def create_chat_message_record(chat: Chat, **kwargs) -> ChatMessageModel:
    """Instantiate the platform-specific chat message model."""
    model = _message_model_for_platform(chat.platform)
    payload: Dict[str, Any] = {
        "chat_id": chat.id,
        "platform": chat.platform,
        **kwargs,
    }
    if chat.platform == MessagePlatform.INSTAGRAM:
        if not chat.instagram_user_id:
            raise ValueError("Instagram chats require instagram_user_id before creating messages")
        payload.setdefault("instagram_user_id", chat.instagram_user_id)
    else:
        if not chat.facebook_user_id:
            raise ValueError("Facebook chats require facebook_user_id before creating messages")
        payload.setdefault("facebook_user_id", chat.facebook_user_id)
    return model(**payload)


def message_query_for_chat(db: Session, chat: Chat):
    """Return a SQLAlchemy query for the chat's platform-specific message table."""
    return db.query(_message_model_for_platform(chat.platform))


def _requires_sqlite_instagram_fallback(db: Session) -> bool:
    bind = getattr(db, "bind", None)
    if bind is None:
        return True
    return bind.dialect.name.lower() == "sqlite"


def _merge_message_metadata(
    existing_json: Optional[str],
    sent_by: Optional[User] = None,
    extra: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    payload: Dict[str, Any] = {}
    if existing_json:
        try:
            payload = json.loads(existing_json)
        except (TypeError, ValueError):
            payload = {}
    if sent_by:
        payload["sent_by"] = {
            "id": sent_by.id,
            "name": sent_by.name,
            "email": sent_by.email,
            "role": sent_by.role.value if isinstance(sent_by.role, UserRole) else str(sent_by.role),
        }
    if extra:
        payload.update(extra)
    try:
        return json.dumps(payload)
    except (TypeError, ValueError):
        return existing_json or None


def _is_assignable_agent(user: Optional[User]) -> bool:
    if not user:
        return False
    if user.role != UserRole.AGENT:
        return False
    return bool(getattr(user, "is_active", True))


def _get_assignable_agents(db: Session) -> List[User]:
    agents = (
        db.query(User)
        .options(joinedload(User.position))
        .filter(User.role == UserRole.AGENT)
        .filter(User.is_active.is_(True))
        .all()
    )
    return [agent for agent in agents if _is_assignable_agent(agent)]


def _get_assignment_cursor(db: Session, name: str = "default") -> AssignmentCursor:
    query = db.query(AssignmentCursor).filter(AssignmentCursor.name == name)
    bind = getattr(db, "bind", None)
    if bind and bind.dialect.name.lower() != "sqlite":
        query = query.with_for_update(of=AssignmentCursor)
    cursor = query.first()
    if not cursor:
        cursor = AssignmentCursor(name=name)
        db.add(cursor)
        db.flush()
    return cursor


def _assign_chat_round_robin(db: Session, chat: Chat) -> Optional[User]:
    agents = _get_assignable_agents(db)
    if not agents:
        chat.assigned_to = None
        chat.status = ChatStatus.UNASSIGNED
        return None

    cursor = _get_assignment_cursor(db)
    ordered_agents = sorted(
        agents,
        key=lambda agent: (getattr(agent, "created_at", utc_now()), agent.id)
    )
    next_agent = ordered_agents[0]
    if cursor.last_user_id:
        for idx, agent in enumerate(ordered_agents):
            if agent.id == cursor.last_user_id:
                next_agent = ordered_agents[(idx + 1) % len(ordered_agents)]
                break

    chat.assigned_to = next_agent.id
    chat.status = ChatStatus.ASSIGNED
    cursor.last_user_id = next_agent.id
    cursor.updated_at = utc_now()
    return next_agent


def _chat_requires_agent_reply(chat: Chat) -> bool:
    if not chat.last_incoming_at:
        return False
    if not chat.last_outgoing_at:
        return True
    return chat.last_outgoing_at < chat.last_incoming_at


def gather_dm_notify_users(db: Session, chat: Optional[Chat] = None) -> Set[str]:
    """Collect user IDs that should receive DM notifications."""
    notify_users: Set[str] = set()
    if chat and chat.assigned_to:
        notify_users.add(str(chat.assigned_to))

    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    notify_users.update(str(user.id) for user in admin_users)
    return notify_users


def normalize_message_sender(message: ChatMessageModel) -> None:
    """Ensure message sender has a valid enum value."""
    if not message:
        return
    sender_value = message.sender.value if isinstance(message.sender, MessageSender) else message.sender
    if not sender_value or not str(sender_value).strip():
        message.sender = MessageSender.INSTAGRAM_PAGE


def _serialize_user_light(user: Optional[User]) -> Optional[Dict[str, str]]:
    if not user:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }


def reassign_chats_from_inactive_agents(db: Session) -> int:
    """
    Move chats away from inactive agents to active agents in round-robin order.
    Returns number of chats reassigned.
    """
    active_agents = _get_assignable_agents(db)
    if not active_agents:
        return 0

    inactive_assigned_chats = (
        db.query(Chat)
        .join(User, Chat.assigned_to == User.id)
        .filter(User.is_active.is_(False))
        .filter(Chat.status == ChatStatus.ASSIGNED)
        .all()
    )
    if not inactive_assigned_chats:
        return 0

    reassigned = 0
    for chat in inactive_assigned_chats:
        assigned_agent = _assign_chat_round_robin(db, chat)
        if assigned_agent:
            reassigned += 1
    if reassigned:
        db.commit()
    return reassigned
