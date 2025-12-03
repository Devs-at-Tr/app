from pathlib import Path
from urllib.parse import quote_plus
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# configure DB URL based on DB_TYPE env
DB_TYPE = os.environ.get('DB_TYPE', 'postgres').lower()

def get_database_url():
    if DB_TYPE == 'mysql':
        host = os.environ.get('MYSQL_HOST', 'localhost')
        user = os.environ.get('MYSQL_USER', 'root')
        password = os.environ.get('MYSQL_PASSWORD', '')
        database = os.environ.get('MYSQL_DATABASE', 'pf_messenger')
        port = os.environ.get('MYSQL_PORT', '3306')
        encoded_password = quote_plus(password)
        return f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}"
    if DB_TYPE == 'postgres':
        postgres_url = os.environ.get('POSTGRES_URL', '')
        if postgres_url:
            return postgres_url
        return None
    return f"sqlite:///{ROOT_DIR / 'ticklegram.db'}"

database_url = get_database_url()

if database_url and (database_url.startswith('mysql') or database_url.startswith('postgresql')):
    try:
        engine = create_engine(database_url,pool_pre_ping=True, pool_recycle=3600, echo=False)
        engine.connect()
        db_name = 'MySQL' if DB_TYPE == 'mysql' else 'PostgreSQL'
        print(f"[OK] Connected to {db_name} database")
    except Exception as exc:
        print(f"[WARN] {DB_TYPE.upper()} connection failed: {exc}")
        print("[WARN] Falling back to SQLite database")
        database_url = f"sqlite:///{ROOT_DIR / 'ticklegram.db'}"
        engine = create_engine(database_url, echo=True, connect_args={"check_same_thread": False})
else:
    print("[INFO] Using SQLite database")
    database_url = f"sqlite:///{ROOT_DIR / 'ticklegram.db'}"
    engine = create_engine(database_url, echo=True, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
        # Optionally commit here if you want auto-commit on success:
        # db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()