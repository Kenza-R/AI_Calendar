"""
Quick script to create demo user using bcrypt directly
"""
import sys
sys.path.insert(0, '/Users/kmr/Documents/GitHub/AI_Calendar/backend')

import bcrypt
from app.database import SessionLocal, engine, Base
from app.models.user import User

# Create database tables
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    # Check if demo user already exists
    demo_user = db.query(User).filter(User.email == "demo@example.com").first()
    
    if demo_user:
        print("✓ Demo user already exists")
        db.close()
        sys.exit(0)
    
    # Hash password with bcrypt directly
    password = "demo123"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create demo user
    new_user = User(
        email="demo@example.com",
        hashed_password=hashed,
        full_name="Demo User"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"✓ Demo user created successfully!")
    print(f"  Email: demo@example.com")
    print(f"  Password: demo123")
    
except Exception as e:
    print(f"✗ Error creating demo user: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
