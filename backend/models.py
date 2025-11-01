from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Integer, Boolean, BigInteger, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone
import uuid
import enum

def utc_now():
    """Get current time in UTC with timezone info"""
    return datetime.now(timezone.utc)

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AGENT = "agent"

class ChatStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"

class MessageSender(str, enum.Enum):
    AGENT = "agent"
    INSTAGRAM_USER = "instagram_user"
    FACEBOOK_USER = "facebook_user"

class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"

class MessagePlatform(str, enum.Enum):
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"

class InstagramMessageDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class InstagramInsightScope(str, enum.Enum):
    ACCOUNT = "account"
    MEDIA = "media"
    STORY = "story"
    PROFILE = "profile"

class InstagramCommentAction(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.AGENT)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    instagram_accounts = relationship("InstagramAccount", back_populates="user", cascade="all, delete-orphan")
    assigned_chats = relationship("Chat", back_populates="assigned_agent", foreign_keys="Chat.assigned_to")

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    page_id = Column(String(255), nullable=False)
    access_token = Column(String(500), nullable=False)
    username = Column(String(255), nullable=True)
    connected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="instagram_accounts")

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    instagram_user_id = Column(String(255), nullable=False, index=True)
    username = Column(String(255), nullable=False)
    profile_pic_url = Column(Text, nullable=True)
    last_message = Column(Text, nullable=True)
    status = Column(SQLEnum(ChatStatus), nullable=False, default=ChatStatus.UNASSIGNED)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    unread_count = Column(Integer, default=0)
    platform = Column(SQLEnum(MessagePlatform), nullable=False, default=MessagePlatform.INSTAGRAM, index=True)
    facebook_page_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.timestamp")
    assigned_agent = relationship("User", back_populates="assigned_chats", foreign_keys=[assigned_to])

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String(36), ForeignKey("chats.id"), nullable=False)
    sender = Column(SQLEnum(MessageSender), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), nullable=False, default=MessageType.TEXT)
    platform = Column(SQLEnum(MessagePlatform), nullable=False, default=MessagePlatform.INSTAGRAM)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
    
    chat = relationship("Chat", back_populates="messages")

class FacebookPage(Base):
    __tablename__ = "facebook_pages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    page_id = Column(String(255), unique=True, nullable=False, index=True)
    page_name = Column(String(255), nullable=True)
    access_token = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    user = relationship("User", backref="facebook_pages")

class MessageTemplate(Base):
    __tablename__ = "message_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # greeting, utility, marketing, support, closing
    platform = Column(SQLEnum(MessagePlatform), nullable=False)
    meta_template_id = Column(String(255), nullable=True)
    meta_submission_id = Column(String(255), nullable=True)
    meta_submission_status = Column(String(50), nullable=True)  # pending, approved, rejected
    is_meta_approved = Column(Boolean, default=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    creator = relationship("User", foreign_keys=[created_by])

class InstagramUser(Base):
    __tablename__ = "instagram_users"

    igsid = Column(String(255), primary_key=True)
    first_seen_at = Column(DateTime(timezone=True), default=utc_now)
    last_seen_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_message = Column(Text, nullable=True)

    messages = relationship("InstagramMessage", back_populates="user", cascade="all, delete-orphan")

class InstagramMessage(Base):
    __tablename__ = "instagram_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    igsid = Column(String(255), ForeignKey("instagram_users.igsid"), nullable=False, index=True)
    direction = Column(SQLEnum(InstagramMessageDirection), nullable=False)
    text = Column(Text, nullable=True)
    attachments_json = Column(Text, nullable=True)
    ts = Column(BigInteger, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("InstagramUser", back_populates="messages")

class InstagramComment(Base):
    __tablename__ = "instagram_comments"

    id = Column(String(255), primary_key=True)
    media_id = Column(String(255), nullable=False, index=True)
    author_id = Column(String(255), nullable=True, index=True)
    text = Column(Text, nullable=True)
    hidden = Column(Boolean, default=False)
    action = Column(SQLEnum(InstagramCommentAction), nullable=False, default=InstagramCommentAction.CREATED)
    mentioned_user_id = Column(String(255), nullable=True)
    attachments_json = Column(Text, nullable=True)
    ts = Column(BigInteger, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class InstagramMarketingEvent(Base):
    __tablename__ = "instagram_marketing_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_name = Column(String(120), nullable=False)
    value = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    pixel_id = Column(String(255), nullable=True)
    external_event_id = Column(String(255), nullable=True, unique=True)
    status = Column(String(50), nullable=True)
    payload_json = Column(Text, nullable=True)
    response_json = Column(Text, nullable=True)
    ts = Column(BigInteger, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class InstagramInsight(Base):
    __tablename__ = "instagram_insights"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope = Column(SQLEnum(InstagramInsightScope), nullable=False)
    entity_id = Column(String(255), nullable=False, index=True)
    period = Column(String(50), nullable=True)
    metrics_json = Column(Text, nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=utc_now, index=True)
