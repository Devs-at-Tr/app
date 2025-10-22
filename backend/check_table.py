from database import engine
from sqlalchemy import text

def check_table():
    with engine.connect() as conn:
        result = conn.execute(text("DESCRIBE facebook_pages"))
        print("\nTable Structure:")
        print("================")
        for row in result:
            print(row)

if __name__ == "__main__":
    check_table()