"""
Migration script to add MessageTemplate model to the database
Run this script to create the message_templates table
"""
import os
import sys
from sqlalchemy import create_engine, text
from database import get_database_url, Base
from models import MessageTemplate, User, Chat, Message, FacebookPage, InstagramAccount

def upgrade():
    """Create the message_templates table"""
    print("Running migration: add_template_model")
    print("=" * 50)
    
    db_url = get_database_url()
    print(f"Database URL: {db_url.split('@')[1] if '@' in db_url else 'SQLite'}")
    
    engine = create_engine(db_url)
    
    try:
        # Create the message_templates table
        print("Creating message_templates table...")
        MessageTemplate.__table__.create(engine, checkfirst=True)
        print("✓ message_templates table created successfully")
        
        # Verify table creation
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_name = 'message_templates'
            """))
            count = result.fetchone()
            if count and count[0] > 0:
                print("✓ Table verified in database")
            else:
                # For SQLite, use different query
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='message_templates'
                """))
                if result.fetchone():
                    print("✓ Table verified in database (SQLite)")
        
        print("=" * 50)
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        return False

def downgrade():
    """Drop the message_templates table"""
    print("Running rollback: add_template_model")
    print("=" * 50)
    
    db_url = get_database_url()
    engine = create_engine(db_url)
    
    try:
        print("Dropping message_templates table...")
        MessageTemplate.__table__.drop(engine, checkfirst=True)
        print("✓ message_templates table dropped successfully")
        print("=" * 50)
        print("Rollback completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error during rollback: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
