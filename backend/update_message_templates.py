from database import engine
from sqlalchemy import text

def update_message_templates_table():
    with engine.connect() as conn:
        # Check if columns exist before adding them
        existing_columns = conn.execute(text("DESCRIBE message_templates")).fetchall()
        existing_column_names = [col[0] for col in existing_columns]
        
        # Add meta_submission_id if it doesn't exist
        if 'meta_submission_id' not in existing_column_names:
            print("Adding meta_submission_id column...")
            conn.execute(text("ALTER TABLE message_templates ADD COLUMN meta_submission_id VARCHAR(255)"))
            
        # Add meta_submission_status if it doesn't exist
        if 'meta_submission_status' not in existing_column_names:
            print("Adding meta_submission_status column...")
            conn.execute(text("ALTER TABLE message_templates ADD COLUMN meta_submission_status VARCHAR(50)"))
            
        # Add is_meta_approved if it doesn't exist
        if 'is_meta_approved' not in existing_column_names:
            print("Adding is_meta_approved column...")
            conn.execute(text("ALTER TABLE message_templates ADD COLUMN is_meta_approved BOOLEAN DEFAULT FALSE"))
            
        conn.commit()
        print("\nUpdated table structure:")
        result = conn.execute(text("DESCRIBE message_templates"))
        for row in result:
            print(row)

if __name__ == "__main__":
    update_message_templates_table()