from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import quote_plus

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Get database type from environment (mysql, postgres, or sqlite)
DB_TYPE = os.environ.get('DB_TYPE', 'postgres').lower()

def get_database_url():
    """Get database URL based on DB_TYPE environment variable"""
    if DB_TYPE == 'mysql':
        host = os.environ.get('MYSQL_HOST', 'localhost')
        user = os.environ.get('MYSQL_USER', 'root')
        password = os.environ.get('MYSQL_PASSWORD', '')
        database = os.environ.get('MYSQL_DATABASE', 'pf_messenger')
        port = os.environ.get('MYSQL_PORT', '3306')
        # URL-encode password to handle special characters
        encoded_password = quote_plus(password)
        return f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}"
    
    elif DB_TYPE == 'postgres':
        postgres_url = os.environ.get('POSTGRES_URL', '')
        if postgres_url:
            return postgres_url
        # Fallback to SQLite if no PostgreSQL URL
        return None
    
    else:  # sqlite
        return f"sqlite:///{ROOT_DIR / 'ticklegram.db'}"

# Initialize database connection
database_url = get_database_url()

if database_url and (database_url.startswith('mysql') or database_url.startswith('postgresql')):
    try:
        engine = create_engine(database_url, echo=True)
        # Test connection
        engine.connect()
        db_name = 'MySQL' if DB_TYPE == 'mysql' else 'PostgreSQL'
        print(f"✓ Connected to {db_name} database")
    except Exception as e:
        print(f"⚠ {DB_TYPE.upper()} connection failed: {e}")
        print("⚠ Falling back to SQLite database")
        database_url = f"sqlite:///{ROOT_DIR / 'ticklegram.db'}"
        engine = create_engine(database_url, echo=True, connect_args={"check_same_thread": False})
else:
    print("⚠ Using SQLite database")
    database_url = f"sqlite:///{ROOT_DIR / 'ticklegram.db'}"
    engine = create_engine(database_url, echo=True, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()