#!/usr/bin/env python
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database credentials from .env
MYSQL_USER = os.getenv('MYSQL_USER', 'developer')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Tickle@1800')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'pf_messenger')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')

# Construct database URL
DATABASE_URL = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# Create database engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def list_templates():
    """List all templates and their Meta approval status"""
    try:
        result = db.execute(text("""
            SELECT id, name, content, category, platform, is_meta_approved, meta_template_id, updated_at
            FROM message_templates
            ORDER BY updated_at DESC
        """))
        
        templates = result.fetchall()
        print("\nTemplate List:")
        print("-" * 80)
        for template in templates:
            print(f"ID: {template.id}")
            print(f"Name: {template.name}")
            print(f"Category: {template.category}")
            print(f"Platform: {template.platform}")
            print(f"Meta Approved: {'✓' if template.is_meta_approved else '✗'}")
            print(f"Meta Template ID: {template.meta_template_id or 'Not set'}")
            print(f"Last Updated: {template.updated_at}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error listing templates: {e}")

def update_template(template_id, meta_template_id):
    """Update a template's Meta approval status"""
    try:
        db.execute(text("""
            UPDATE message_templates 
            SET is_meta_approved = TRUE,
                meta_template_id = :meta_template_id,
                updated_at = NOW()
            WHERE id = :template_id
        """), {"template_id": template_id, "meta_template_id": meta_template_id})
        db.commit()
        print(f"✓ Template {template_id} updated successfully")
    except Exception as e:
        print(f"Error updating template: {e}")

if __name__ == "__main__":
    try:
        while True:
            print("\nTemplate Management")
            print("1. List all templates")
            print("2. Update template Meta approval")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == "1":
                list_templates()
            elif choice == "2":
                template_id = input("Enter template ID to update: ")
                meta_template_id = input("Enter Meta template ID: ")
                update_template(template_id, meta_template_id)
            elif choice == "3":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")
    finally:
        db.close()