"""
Create MySQL database if it doesn't exist
"""
import pymysql
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

def create_database():
    """Create the MySQL database if it doesn't exist"""
    host = os.environ.get('MYSQL_HOST', 'localhost')
    user = os.environ.get('MYSQL_USER', 'root')
    password = os.environ.get('MYSQL_PASSWORD', '')
    database = os.environ.get('MYSQL_DATABASE', 'pf_messenger')
    port = int(os.environ.get('MYSQL_PORT', '3306'))
    
    try:
        # Connect to MySQL server (without specifying database)
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port
        )
        
        cursor = connection.cursor()
        
        # Check if database exists
        cursor.execute(f"SHOW DATABASES LIKE '{database}'")
        result = cursor.fetchone()
        
        if result:
            print(f"✓ Database '{database}' already exists")
        else:
            # Create database
            cursor.execute(f"CREATE DATABASE {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ Created database '{database}'")
        
        cursor.close()
        connection.close()
        return True
        
    except pymysql.Error as e:
        print(f"❌ MySQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("MySQL Database Creation")
    print("=" * 50)
    
    if create_database():
        print("\n✨ Ready to run migration!")
        print("Run: python migrate_to_mysql.py")
    else:
        print("\n❌ Failed to create database")
        print("\nPlease check:")
        print("1. MySQL server is running (XAMPP)")
        print("2. MySQL credentials in .env are correct")
        print("3. User has CREATE DATABASE privilege")
