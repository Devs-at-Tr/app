"""
Migration script to create MySQL database schema
Run this script to initialize the MySQL database with all tables
"""
from database import Base, engine
from models import (
    User,
    InstagramAccount,
    Chat,
    InstagramMessage,
    FacebookMessage,
    FacebookUser,
    FacebookPage,
    InstagramMessageLog,
)
import sys

def create_tables():
    """Create all tables in the MySQL database"""
    try:
        print("🔄 Creating tables in MySQL database...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Successfully created all tables!")
        print("\nCreated tables:")
        print("  - users")
        print("  - instagram_accounts")
        print("  - chats")
        print("  - instagram_messages")
        print("  - facebook_messages")
        print("  - instagram_message_logs")
        print("  - facebook_users")
        print("  - facebook_pages")
        
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("MySQL Database Migration")
    print("=" * 50)
    
    success = create_tables()
    
    if success:
        print("\n✨ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your backend server: uvicorn server:app --reload --port 8000")
        print("2. The application will now use MySQL database")
        print("3. Run seed_data.py if you need initial data")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
