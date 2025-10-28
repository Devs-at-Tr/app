from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone
import pytz
from models import UserRole, ChatStatus, MessageSender, MessageType, MessagePlatform

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
    
    class Config:
        from_attributes = True
        
    def model_post_init(self, _):
        self.timestamp = convert_to_ist(self.timestamp)

# Chat Schemas
class ChatAssign(BaseModel):
    agent_id: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    instagram_user_id: str
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