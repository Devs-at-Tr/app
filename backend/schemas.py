from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import pytz
import json
from models import (
    UserRole,
    ChatStatus,
    MessageSender,
    MessageType,
    MessagePlatform,
    InstagramMessageDirection,
    InstagramInsightScope,
    InstagramCommentAction
)

def convert_to_ist(dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ist = pytz.timezone('Asia/Kolkata')
    return dt.astimezone(ist)

# Auth Schemas
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.AGENT

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Instagram Schemas
class InstagramConnect(BaseModel):
    page_id: str
    access_token: str
    username: Optional[str] = None

class InstagramAccountResponse(BaseModel):
    id: str
    page_id: str
    username: Optional[str]
    connected_at: datetime
    
    class Config:
        from_attributes = True

# Message Schemas
class MessageCreate(BaseModel):
    content: str
    message_type: Optional[MessageType] = MessageType.TEXT

class MessageResponse(BaseModel):
    id: str
    chat_id: str
    sender: MessageSender
    content: str
    message_type: MessageType
    platform: MessagePlatform
    timestamp: datetime
    is_ticklegram: bool = False
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    attachments_json: Optional[str] = Field(default=None, exclude=True)
    metadata_json: Optional[str] = Field(default=None, exclude=True)
    is_gif: Optional[bool] = Field(default=False, exclude=True)
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, _):
        self.timestamp = convert_to_ist(self.timestamp)
        if not self.attachments:
            raw = self.attachments_json
            if raw:
                try:
                    self.attachments = json.loads(raw)
                except (TypeError, ValueError):
                    self.attachments = []
            else:
                self.attachments = []

class InstagramUserSchema(BaseModel):
    igsid: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_message: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True

    def model_post_init(self, _):
        self.first_seen_at = convert_to_ist(self.first_seen_at)
        self.last_seen_at = convert_to_ist(self.last_seen_at)


class FacebookUserSchema(BaseModel):
    id: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_message: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None
    profile_pic_url: Optional[str] = None

    class Config:
        from_attributes = True

    def model_post_init(self, _):
        self.first_seen_at = convert_to_ist(self.first_seen_at)
        self.last_seen_at = convert_to_ist(self.last_seen_at)

class InstagramMessageSchema(BaseModel):
    id: str
    igsid: str
    message_id: Optional[str] = None
    direction: InstagramMessageDirection
    text: Optional[str] = None
    attachments_json: Optional[str] = None
    ts: int
    created_at: datetime
    attachments: List[Dict[str, Any]] = []
    raw_payload_json: Optional[str] = None

    class Config:
        from_attributes = True

    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)
        if self.attachments_json:
            try:
                self.attachments = json.loads(self.attachments_json)
            except (TypeError, ValueError):
                self.attachments = []
        else:
            self.attachments = []

class InstagramSendRequest(BaseModel):
    igsid: str = Field(..., description="Instagram scoped user ID")
    text: Optional[str] = Field(None, description="Message text to send")
    attachments: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Attachment payloads to forward"
    )

    @property
    def has_text(self) -> bool:
        return bool(self.text and self.text.strip())

    @model_validator(mode="after")
    def validate_payload(cls, values: "InstagramSendRequest") -> "InstagramSendRequest":
        has_attachments = bool(values.attachments)
        if not values.has_text and not has_attachments:
            raise ValueError("Either text or attachments must be provided")
        return values

class InstagramCommentSchema(BaseModel):
    id: str
    media_id: str
    author_id: Optional[str] = None
    text: Optional[str] = None
    hidden: bool = False
    action: InstagramCommentAction = InstagramCommentAction.CREATED
    mentioned_user_id: Optional[str] = None
    attachments_json: Optional[str] = None
    ts: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    attachments: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True

    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)
        if self.updated_at:
            self.updated_at = convert_to_ist(self.updated_at)
        if self.attachments_json:
            try:
                self.attachments = json.loads(self.attachments_json)
            except (TypeError, ValueError):
                self.attachments = []

class InstagramCommentCreateRequest(BaseModel):
    media_id: str = Field(..., description="Target Instagram media ID")
    message: str = Field(..., min_length=1, description="Comment text")

class InstagramCommentHideRequest(BaseModel):
    comment_id: str = Field(..., description="Comment ID to hide/unhide")
    hide: bool = Field(..., description="True to hide comment, False to unhide")

class InstagramMarketingEventRequest(BaseModel):
    event_name: str = Field(..., description="Meta standard event name e.g. Purchase")
    event_time: int = Field(..., description="Unix timestamp in seconds")
    value: Optional[float] = Field(None, description="Event monetary value")
    currency: Optional[str] = Field(None, description="Currency code e.g. INR")
    user_data: Dict[str, Any] = Field(default_factory=dict)
    custom_data: Dict[str, Any] = Field(default_factory=dict)
    event_source_url: Optional[str] = None
    action_source: Optional[str] = None
    test_event_code: Optional[str] = None
    event_id: Optional[str] = Field(None, description="Idempotency key for the event")
    pixel_id: Optional[str] = Field(None, description="Override Pixel ID, defaults to PIXEL_ID from env")

class InstagramMarketingEventSchema(BaseModel):
    id: str
    event_name: str
    value: Optional[float] = None
    currency: Optional[str] = None
    pixel_id: Optional[str] = None
    external_event_id: Optional[str] = None
    status: Optional[str] = None
    ts: int
    created_at: datetime
    payload_json: Optional[str] = None
    response_json: Optional[str] = None

    class Config:
        from_attributes = True

    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)

class InstagramInsightSchema(BaseModel):
    id: str
    scope: InstagramInsightScope
    entity_id: str
    period: Optional[str] = None
    metrics_json: str
    fetched_at: datetime
    metrics: Dict[str, Any] = {}

    class Config:
        from_attributes = True

    def model_post_init(self, _):
        self.fetched_at = convert_to_ist(self.fetched_at)
        try:
            self.metrics = json.loads(self.metrics_json)
        except (TypeError, ValueError):
            self.metrics = {}

# Chat Schemas
class ChatAssign(BaseModel):
    agent_id: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    instagram_user_id: Optional[str] = None
    facebook_user_id: Optional[str] = None
    username: str
    profile_pic_url: Optional[str]
    last_message: Optional[str]
    status: ChatStatus
    assigned_to: Optional[str]
    unread_count: int
    platform: MessagePlatform
    facebook_page_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    assigned_agent: Optional[UserResponse] = None
    instagram_user: Optional[InstagramUserSchema] = None
    facebook_user: Optional[FacebookUserSchema] = None
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)
        self.updated_at = convert_to_ist(self.updated_at)

class ChatWithMessages(ChatResponse):
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True

# Dashboard Schemas
class DashboardStats(BaseModel):
    total_chats: int
    assigned_chats: int
    unassigned_chats: int
    total_messages: int
    active_agents: int
    instagram_chats: Optional[int] = 0
    facebook_chats: Optional[int] = 0

# Facebook Schemas
class FacebookPageConnect(BaseModel):
    page_id: str
    page_name: Optional[str] = None
    access_token: str

class FacebookPageResponse(BaseModel):
    id: str
    page_id: str
    page_name: Optional[str]
    is_active: bool
    connected_at: datetime
    
    class Config:
        from_attributes = True

class FacebookPageUpdate(BaseModel):
    page_name: Optional[str] = None
    access_token: Optional[str] = None
    is_active: Optional[bool] = None

# Template Schemas
class MessageTemplateCreate(BaseModel):
    name: str
    content: str
    category: str  # greeting, utility, marketing, support, closing
    platform: MessagePlatform
    meta_template_id: Optional[str] = None
    meta_submission_id: Optional[str] = None
    meta_submission_status: Optional[str] = None
    is_meta_approved: bool = False

class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    platform: Optional[MessagePlatform] = None
    meta_template_id: Optional[str] = None
    meta_submission_id: Optional[str] = None
    meta_submission_status: Optional[str] = None
    is_meta_approved: Optional[bool] = None

class MessageTemplateResponse(BaseModel):
    id: str
    name: str
    content: str
    category: str
    platform: MessagePlatform
    meta_template_id: Optional[str]
    meta_submission_id: Optional[str]
    meta_submission_status: Optional[str]
    is_meta_approved: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)
        self.updated_at = convert_to_ist(self.updated_at)

class TemplateSendRequest(BaseModel):
    chat_id: str
    variables: Optional[dict] = {}  # For variable substitution like {name}, {order_id}
