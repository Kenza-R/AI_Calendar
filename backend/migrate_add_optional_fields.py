"""Add is_optional and conditions columns to tasks table."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'ai_calendar.db')

print(f"📊 Migrating database: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Add is_optional column
    print("Adding is_optional column...")
    cursor.execute("ALTER TABLE tasks ADD COLUMN is_optional BOOLEAN DEFAULT 0")
    print("✅ is_optional column added")
    
    # Add conditions column
    print("Adding conditions column...")
    cursor.execute("ALTER TABLE tasks ADD COLUMN conditions TEXT")
    print("✅ conditions column added")
    
    conn.commit()
    print("\n🎉 Migration completed successfully!")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("⚠️ Columns already exist - skipping migration")
    else:
        print(f"❌ Migration failed: {e}")
        raise
finally:
    conn.close()

print("\n🔍 Verifying schema...")
os.system(f"cd {os.path.dirname(__file__)} && {os.sys.executable} verify_schema.py")
