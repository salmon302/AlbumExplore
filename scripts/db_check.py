import sqlite3
import os

DB_PATH = 'albumexplore.db'

if not os.path.exists(DB_PATH):
    print("DB not found")
else:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check total tags
    cursor.execute("SELECT count(*) FROM tags")
    print(f"Total tags: {cursor.fetchone()[0]}")
    
    # Check simple frequency
    cursor.execute("SELECT count(*) FROM tags WHERE frequency = 1")
    res = cursor.fetchone()[0]
    print(f"Tags with frequency=1: {res}")
    
    if res == 0:
        print("Checking calculated frequency...")
        cursor.execute("""
            SELECT count(*) FROM (
                SELECT t.id
                FROM tags t 
                JOIN album_tags at ON t.id = at.tag_id 
                GROUP BY t.id 
                HAVING COUNT(at.album_id) = 1
            )
        """)
        print(f"Calculated singletons: {cursor.fetchone()[0]}")

    conn.close()
