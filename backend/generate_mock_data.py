from sqlalchemy.orm import Session
from models import (
    InstagramAccount,
    Chat,
    InstagramMessage,
    FacebookMessage,
    FacebookUser,
    MessagePlatform,
    ChatStatus,
    MessageSender,
    MessageType,
)
from datetime import datetime, timezone
import random
import uuid

def ensure_mock_instagram_account(db: Session, user_id: str) -> InstagramAccount:
    """Ensure a mock Instagram account exists for testing"""
    mock_account = db.query(InstagramAccount).first()
    
    if not mock_account:
        mock_account = InstagramAccount(
            id=str(uuid.uuid4()),
            user_id=user_id,
            page_id="mock_ig_123",
            access_token="mock_token",
            username="mock_instagram"
        )
        db.add(mock_account)
        db.commit()
        db.refresh(mock_account)
    
    return mock_account

def generate_mock_chats(
    db: Session,
    user_id: str,
    count: int = 5,
    platform: str = "INSTAGRAM"
) -> list:
    """Generate mock chats with proper platform association"""
    
    # Ensure we have a mock Instagram account if needed
    mock_ig_account = None
    if platform.upper() == "INSTAGRAM":
        mock_ig_account = ensure_mock_instagram_account(db, user_id)
    
    dialect_name = (getattr(getattr(db, "bind", None), "dialect", None).name.lower()
                    if getattr(db, "bind", None) else "sqlite")
    requires_sqlite = dialect_name == "sqlite"

    messages_pool = [
        "Hi! I'm interested in your product.",
        "Can you tell me more about pricing?",
        "Do you offer international shipping?",
        "I have a question about my order.",
        "Is this item still available?"
    ]
    
    chat_platform = MessagePlatform.INSTAGRAM if platform.upper() == "INSTAGRAM" else MessagePlatform.FACEBOOK
    
    created_chats = []
    for i in range(count):
        user_identifier = f"mock_user_{i}_{random.randint(1000, 9999)}"
        username = f"test_user_{i}"

        facebook_user_id = None
        if chat_platform == MessagePlatform.FACEBOOK:
            facebook_user = FacebookUser(
                id=user_identifier,
                username=username,
                name=username.title(),
                profile_pic_url=f"https://via.placeholder.com/150?text={username[:8]}",
            )
            db.add(facebook_user)
            db.flush()
            facebook_user_id = facebook_user.id
        
        # Create chat with proper platform association
        instagram_fk = user_identifier if chat_platform == MessagePlatform.INSTAGRAM else (user_identifier if requires_sqlite else None)
        chat = Chat(
            id=str(uuid.uuid4()),
            instagram_user_id=instagram_fk,
            facebook_user_id=facebook_user_id,
            username=username,
            profile_pic_url=f"https://via.placeholder.com/150?text={user_identifier[:8]}",
            platform=chat_platform,
            status=ChatStatus.UNASSIGNED,
            facebook_page_id=mock_ig_account.page_id if chat_platform == MessagePlatform.INSTAGRAM else None,
            last_message=random.choice(messages_pool)
        )
        db.add(chat)
        db.flush()
        
        # Add some messages
        for j in range(random.randint(2, 5)):
            if chat_platform == MessagePlatform.INSTAGRAM:
                msg = InstagramMessage(
                    chat_id=chat.id,
                    instagram_user_id=chat.instagram_user_id,
                    sender=MessageSender.INSTAGRAM_USER if j % 2 == 0 else MessageSender.AGENT,
                    content=random.choice(messages_pool),
                    message_type=MessageType.TEXT,
                    platform=chat_platform
                )
            else:
                msg = FacebookMessage(
                    chat_id=chat.id,
                    facebook_user_id=chat.facebook_user_id,
                    sender=MessageSender.FACEBOOK_USER if j % 2 == 0 else MessageSender.AGENT,
                    content=random.choice(messages_pool),
                    message_type=MessageType.TEXT,
                    platform=chat_platform
                )
            db.add(msg)
        
        created_chats.append(chat.id)
    
    db.commit()
    return created_chats
