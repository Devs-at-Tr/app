from database import SessionLocal, engine, Base
from models import User, Chat, Message, UserRole, ChatStatus, MessageSender, MessageType, InstagramAccount, MessagePlatform
from auth import get_password_hash
import random
import uuid

def seed_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("Database already has data. Skipping seed.")
            return
        
        # Create admin user
        admin = User(
            name="Admin User",
            email="admin@ticklegram.com",
            password_hash=get_password_hash("admin123"[:72]),
            role=UserRole.ADMIN
        )
        db.add(admin)
        
        # Create agent users
        agent1 = User(
            name="Agent John",
            email="agent1@ticklegram.com",
            password_hash=get_password_hash("agent123"[:72]),
            role=UserRole.AGENT
        )
        db.add(agent1)
        
        agent2 = User(
            name="Agent Sarah",
            email="agent2@ticklegram.com",
            password_hash=get_password_hash("agent123"[:72]),
            role=UserRole.AGENT
        )
        db.add(agent2)
        
        db.commit()
        db.refresh(admin)
        db.refresh(agent1)
        db.refresh(agent2)
        
        # Create mock Instagram account for admin
        mock_ig_account = InstagramAccount(
            id=str(uuid.uuid4()),
            user_id=admin.id,
            page_id="mock_ig_123",
            access_token="mock_token",
            username="mock_instagram"
        )
        db.add(mock_ig_account)
        db.commit()
        db.refresh(mock_ig_account)
        
        print("✅ Created demo users:")
        print("   Admin: admin@ticklegram.com / admin123")
        print("   Agent 1: agent1@ticklegram.com / agent123")
        print("   Agent 2: agent2@ticklegram.com / agent123")
        print("✅ Created mock Instagram account for admin")
        
        # Create sample chats
        usernames = ["john_doe", "sarah_smith", "mike_wilson", "emma_johnson", "david_brown"]
        messages_pool = [
            "Hi! I'm interested in your product.",
            "Can you tell me more about pricing?",
            "Do you offer international shipping?",
            "I have a question about my order.",
            "Is this item still available?"
        ]
        
        for i, username in enumerate(usernames):
            ig_user_id = f"ig_{1000 + i}"
            
            # Create chat
            chat = Chat(
                instagram_user_id=ig_user_id,
                username=username,
                profile_pic_url=f"https://via.placeholder.com/150?text={ig_user_id[:8]}",
                last_message=messages_pool[i],
                status=ChatStatus.ASSIGNED if i < 3 else ChatStatus.UNASSIGNED,
                assigned_to=agent1.id if i < 2 else (agent2.id if i == 2 else None),
                unread_count=random.randint(0, 5),
                platform=MessagePlatform.INSTAGRAM,
                facebook_page_id=mock_ig_account.page_id  # Link to mock Instagram account
            )
            db.add(chat)
            db.flush()
            
            # Add messages to chat
            for j in range(random.randint(2, 4)):
                msg = Message(
                    chat_id=chat.id,
                    sender=MessageSender.INSTAGRAM_USER if j % 2 == 0 else MessageSender.AGENT,
                    content=random.choice(messages_pool),
                    message_type=MessageType.TEXT
                )
                db.add(msg)
        
        db.commit()
        print(f"✅ Created {len(usernames)} sample chats with messages")
        print("\n🚀 Database seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()