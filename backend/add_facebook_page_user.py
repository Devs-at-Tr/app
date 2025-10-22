"""
Migration script to add user_id column to facebook_pages table
"""
import sys
import logging
from sqlalchemy import create_engine, text
from database import get_database_url

logger = logging.getLogger(__name__)

def upgrade():
    """Add user_id column and foreign key to facebook_pages table"""
    print("Running migration: add_facebook_page_user")
    print("=" * 50)
    
    db_url = get_database_url()
    print(f"Database URL: {db_url.split('@')[1] if '@' in db_url else 'SQLite'}")
    
    engine = create_engine(db_url)
    
    try:
        # Add user_id column
        with engine.connect() as conn:
            # First check if the column already exists
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.columns 
                WHERE table_name = 'facebook_pages'
                AND column_name = 'user_id';
            """))
            if result.scalar() == 0:
                print("Adding user_id column...")
                conn.execute(text("""
                    ALTER TABLE facebook_pages
                    ADD COLUMN user_id VARCHAR(36);
                """))
                
                # Add foreign key constraint
                print("Adding foreign key constraint...")
                conn.execute(text("""
                    ALTER TABLE facebook_pages
                    ADD CONSTRAINT fk_facebook_pages_user
                    FOREIGN KEY (user_id)
                    REFERENCES users(id);
                """))
                
                # Set a default user_id (you'll need to update this with correct values)
                print("WARNING: You need to set correct user_id values for existing pages!")
                admin_user = conn.execute(text("""
                    SELECT id FROM users WHERE role = 'admin' LIMIT 1;
                """)).scalar()
                
                if admin_user:
                    print(f"Temporarily assigning all pages to admin user: {admin_user}")
                    conn.execute(text("""
                        UPDATE facebook_pages
                        SET user_id = :admin_id
                        WHERE user_id IS NULL;
                    """), {"admin_id": admin_user})
                
                # Make the column not nullable
                conn.execute(text("""
                    ALTER TABLE facebook_pages
                    MODIFY user_id VARCHAR(36) NOT NULL;
                """))
                
                print("Migration completed successfully!")
            else:
                print("Column user_id already exists. Skipping migration.")
            
            conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
        print("Rolling back changes...")
        raise

def downgrade():
    """Remove user_id column from facebook_pages table"""
    print("Running rollback: add_facebook_page_user")
    print("=" * 50)
    
    db_url = get_database_url()
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            # Remove foreign key constraint first
            print("Removing foreign key constraint...")
            conn.execute(text("""
                ALTER TABLE facebook_pages
                DROP CONSTRAINT IF EXISTS fk_facebook_pages_user;
            """))
            
            # Remove the column
            print("Removing user_id column...")
            conn.execute(text("""
                ALTER TABLE facebook_pages
                DROP COLUMN IF EXISTS user_id;
            """))
            
            conn.commit()
            print("Rollback completed successfully!")
    except Exception as e:
        print(f"Error during rollback: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()