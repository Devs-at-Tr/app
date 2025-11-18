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

# Position Schemas
class PositionBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

class PositionCreate(PositionBase):
    is_system: bool = False

class PositionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class PositionResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)
        self.updated_at = convert_to_ist(self.updated_at)


# Auth Schemas
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.AGENT
    position_id: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class AdminUserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.AGENT
    position_id: Optional[str] = None


class AuthConfigResponse(BaseModel):
    allow_public_signup: bool
    forgot_password_enabled: bool = True

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    is_active: bool = True
    position: Optional[PositionResponse] = None
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserPositionUpdate(BaseModel):
    position_id: Optional[str] = None


class UserRosterEntry(UserResponse):
    assigned_chat_count: int = 0

class UserActiveUpdate(BaseModel):
    is_active: bool

# Database Visualizer Schemas

class TableColumnMeta(BaseModel):
    name: str
    data_type: str
    nullable: bool
    default: Optional[str] = None
    extra: Optional[str] = None
    key: Optional[str] = None


class TableMetadata(BaseModel):
    name: str
    rows: Optional[int] = None
    data_size_bytes: int = 0
    index_size_bytes: int = 0
    total_size_bytes: int = 0
    data_size_readable: str = "0 B"
    index_size_readable: str = "0 B"
    total_size_readable: str = "0 B"
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    columns: List[TableColumnMeta] = Field(default_factory=list)

    def model_post_init(self, _):
        if self.create_time:
            self.create_time = convert_to_ist(self.create_time)
        if self.update_time:
            self.update_time = convert_to_ist(self.update_time)


class DatabaseSummary(BaseModel):
    database_name: Optional[str] = None
    table_count: int = 0
    total_rows: int = 0
    data_size_bytes: int = 0
    index_size_bytes: int = 0
    total_size_bytes: int = 0
    total_size_readable: str = "0 B"
    metadata_supported: bool = True
    info_message: Optional[str] = None
    last_update: Optional[datetime] = None

    def model_post_init(self, _):
        if self.last_update:
            self.last_update = convert_to_ist(self.last_update)


class TableRelationship(BaseModel):
    table: str
    column: str
    references_table: str
    references_column: str
    constraint_name: Optional[str] = None


class SchemaChangeRecord(BaseModel):
    change_type: str
    table_name: str
    column_name: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SchemaChangeSnapshot(BaseModel):
    id: int
    created_at: datetime
    changes: List[SchemaChangeRecord] = Field(default_factory=list)

    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)


class SchemaChangesPayload(BaseModel):
    latest_snapshot_id: Optional[int] = None
    latest_snapshot_created_at: Optional[datetime] = None
    latest_summary: Dict[str, Any] = Field(default_factory=dict)
    recent_snapshots: List[SchemaChangeSnapshot] = Field(default_factory=list)

    def model_post_init(self, _):
        if self.latest_snapshot_created_at:
            self.latest_snapshot_created_at = convert_to_ist(self.latest_snapshot_created_at)


class StorageTableStat(BaseModel):
    name: str
    size_bytes: int
    size_readable: str
    rows: Optional[int] = None


class StorageStats(BaseModel):
    total_size_bytes: int = 0
    total_size_readable: str = "0 B"
    top_tables: List[StorageTableStat] = Field(default_factory=list)


class DatabaseOverviewResponse(BaseModel):
    summary: DatabaseSummary
    tables: List[TableMetadata] = Field(default_factory=list)
    relationships: List[TableRelationship] = Field(default_factory=list)
    schema_changes: SchemaChangesPayload
    storage: StorageStats

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
    sent_by: Optional[Dict[str, Any]] = None
    
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
        if self.metadata_json and not self.sent_by:
            try:
                metadata = json.loads(self.metadata_json)
                self.sent_by = metadata.get("sent_by")
            except (TypeError, ValueError):
                self.sent_by = None

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
    last_incoming_at: Optional[datetime] = None
    last_outgoing_at: Optional[datetime] = None
    pending_agent_reply: bool = False
    assigned_agent: Optional[UserResponse] = None
    instagram_user: Optional[InstagramUserSchema] = None
    facebook_user: Optional[FacebookUserSchema] = None
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, _):
        self.created_at = convert_to_ist(self.created_at)
        self.updated_at = convert_to_ist(self.updated_at)
        if self.last_incoming_at:
            self.last_incoming_at = convert_to_ist(self.last_incoming_at)
        if self.last_outgoing_at:
            self.last_outgoing_at = convert_to_ist(self.last_outgoing_at)

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
