from sqlalchemy.orm import Session
from models import InstagramAccount, Chat, Message, MessagePlatform, ChatStatus, MessageSender, MessageType
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
        user_id = f"mock_user_{i}_{random.randint(1000, 9999)}"
        username = f"test_user_{i}"
        
        # Create chat with proper platform association
        chat = Chat(
            id=str(uuid.uuid4()),
            instagram_user_id=user_id,
            username=username,
            profile_pic_url=f"https://via.placeholder.com/150?text={user_id[:8]}",
            platform=chat_platform,
            status=ChatStatus.UNASSIGNED,
            facebook_page_id=mock_ig_account.page_id if chat_platform == MessagePlatform.INSTAGRAM else None,
            last_message=random.choice(messages_pool)
        )
        db.add(chat)
        db.flush()
        
        # Add some messages
        for j in range(random.randint(2, 5)):
            msg = Message(
                chat_id=chat.id,
                sender=MessageSender.INSTAGRAM_USER if chat_platform == MessagePlatform.INSTAGRAM else MessageSender.FACEBOOK_USER,
                content=random.choice(messages_pool),
                message_type=MessageType.TEXT,
                platform=chat_platform
            )
            db.add(msg)
        
        created_chats.append(chat.id)
    
    db.commit()
    return created_chats