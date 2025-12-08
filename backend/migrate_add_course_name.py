"""
Migration script to add course_name field to tasks table.
Run this with: python migrate_add_course_name.py
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "ai_calendar.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'course_name' in columns:
            print("✅ Column 'course_name' already exists in tasks table")
        else:
            # Add course_name column
            cursor.execute("ALTER TABLE tasks ADD COLUMN course_name VARCHAR")
            conn.commit()
            print("✅ Added 'course_name' column to tasks table")
        
        # Check current schema
        cursor.execute("PRAGMA table_info(tasks)")
        print("\n📋 Current tasks table schema:")
        for col in cursor.fetchall():
            print(f"   {col[1]:20s} {col[2]:15s} nullable={col[3]==0}")
        
        # Count existing tasks
        cursor.execute("SELECT COUNT(*) FROM tasks")
        task_count = cursor.fetchone()[0]
        print(f"\n📊 Total tasks in database: {task_count}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
