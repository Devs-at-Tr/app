from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Database URL
DATABASE_URL = os.getenv('DATABASE_URL')

# Create engine
engine = create_engine(DATABASE_URL)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

def add_profile_pic_column():
    """Add profile_pic_url column to chats table"""
    try:
        # Add the column
        session.execute('ALTER TABLE chats ADD COLUMN profile_pic_url TEXT;')
        session.commit()
        print("Successfully added profile_pic_url column to chats table")
    except Exception as e:
        session.rollback()
        print(f"Error adding column: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    add_profile_pic_column()