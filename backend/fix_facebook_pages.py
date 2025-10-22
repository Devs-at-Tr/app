"""
Direct migration script to fix facebook_pages table
"""
import logging
from sqlalchemy import create_engine, text
from database import get_database_url

def fix_facebook_pages():
    """Fix facebook_pages table structure"""
    db_url = get_database_url()
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            print("Starting table repair...")
            
            # Drop existing foreign key if it exists
            try:
                print("Dropping existing constraints and column...")
                # Drop all constraints first
                conn.execute(text("""
                    SET FOREIGN_KEY_CHECKS=0;
                """))
                
                try:
                    conn.execute(text("""
                        ALTER TABLE facebook_pages
                        DROP FOREIGN KEY fk_facebook_pages_user;
                    """))
                except:
                    pass
                
                try:
                    conn.execute(text("""
                        ALTER TABLE facebook_pages
                        DROP COLUMN user_id;
                    """))
                except:
                    pass
                
                conn.execute(text("""
                    SET FOREIGN_KEY_CHECKS=1;
                """))
            except Exception as e:
                print(f"Note: Could not drop foreign key: {e}")

            # Drop existing column if it exists
            try:
                print("Dropping existing user_id column if it exists...")
                conn.execute(text("""
                    ALTER TABLE facebook_pages
                    DROP COLUMN user_id;
                """))
            except Exception as e:
                print(f"Note: Could not drop column: {e}")
                print("Adding user_id column...")
                # Add user_id column without constraints first
                conn.execute(text("""
                    ALTER TABLE facebook_pages
                    ADD COLUMN user_id VARCHAR(36);
                """))
                
                # Get admin user ID
                admin_result = conn.execute(text("""
                    SELECT id FROM users WHERE role = 'admin' LIMIT 1;
                """))
                admin_id = admin_result.scalar()
                
                if admin_id:
                    print(f"Setting default admin user: {admin_id}")
                    # Update existing rows with admin user ID
                    conn.execute(text("""
                        UPDATE facebook_pages
                        SET user_id = :admin_id
                        WHERE user_id IS NULL;
                    """), {"admin_id": admin_id})
                    
                    # Now add NOT NULL constraint
                    conn.execute(text("""
                        ALTER TABLE facebook_pages
                        MODIFY user_id VARCHAR(36) NOT NULL;
                    """))
                    
                    # Finally add foreign key constraint
                    conn.execute(text("""
                        ALTER TABLE facebook_pages
                        ADD CONSTRAINT fk_facebook_pages_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(id);
                    """))
                    
                print("Migration completed successfully!")
            else:
                print("user_id column already exists")
            
            conn.commit()
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    fix_facebook_pages()