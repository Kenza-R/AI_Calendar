"""
Sample data seed script for AI Productivity Calendar.
Run this to populate the database with sample users, events, and tasks.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.event import Event
from app.models.task import Task
from app.utils.auth import get_password_hash
import json


def create_sample_data():
    """Create sample data for testing."""
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create sample user
        sample_user = db.query(User).filter(User.email == "demo@example.com").first()
        if not sample_user:
            sample_user = User(
                email="demo@example.com",
                hashed_password=get_password_hash("demo123"),
                full_name="Demo User"
            )
            db.add(sample_user)
            db.commit()
            db.refresh(sample_user)
            print(f"Created user: {sample_user.email}")
        
        # Create sample events
        now = datetime.utcnow()
        
        sample_events = [
            {
                "title": "CS 101 Lecture",
                "description": "Introduction to Computer Science",
                "start_time": now + timedelta(days=1, hours=10),
                "end_time": now + timedelta(days=1, hours=11, minutes=30),
                "event_type": "meeting",
                "location": "Room 101"
            },
            {
                "title": "Job Interview - TechCorp",
                "description": "Software Engineer position interview",
                "start_time": now + timedelta(days=3, hours=14),
                "end_time": now + timedelta(days=3, hours=15),
                "event_type": "interview",
                "location": "Virtual - Zoom"
            },
            {
                "title": "Midterm Exam - Data Structures",
                "description": "Covers chapters 1-5",
                "start_time": now + timedelta(days=7, hours=9),
                "end_time": now + timedelta(days=7, hours=11),
                "event_type": "exam",
                "location": "Main Hall"
            }
        ]
        
        for event_data in sample_events:
            existing = db.query(Event).filter(
                Event.user_id == sample_user.id,
                Event.title == event_data["title"]
            ).first()
            
            if not existing:
                event = Event(
                    user_id=sample_user.id,
                    **event_data,
                    source="manual"
                )
                db.add(event)
        
        db.commit()
        print(f"Created {len(sample_events)} sample events")
        
        # Create sample tasks
        sample_tasks = [
            {
                "title": "Complete Python Assignment",
                "description": "Implement sorting algorithms",
                "deadline": now + timedelta(days=5),
                "priority": "high",
                "task_type": "assignment",
                "estimated_hours": 4,
                "prep_material": json.dumps({
                    "key_concepts": ["Bubble Sort", "Quick Sort", "Merge Sort"],
                    "study_tips": ["Review algorithm complexity", "Practice implementation"]
                })
            },
            {
                "title": "Prepare for TechCorp Interview",
                "description": "Research company and practice coding questions",
                "deadline": now + timedelta(days=3),
                "priority": "high",
                "task_type": "interview_prep",
                "estimated_hours": 8,
                "prep_material": json.dumps({
                    "company_research": [
                        "TechCorp specializes in cloud solutions",
                        "Founded in 2015, 500+ employees",
                        "Recent projects in AI/ML"
                    ],
                    "questions": [
                        "Tell me about yourself",
                        "Why TechCorp?",
                        "Describe a challenging project",
                        "Explain your experience with Python",
                        "Where do you see yourself in 5 years?"
                    ],
                    "topics": [
                        "Data structures",
                        "System design",
                        "Behavioral questions"
                    ],
                    "tips": [
                        "Use STAR method for behavioral questions",
                        "Prepare questions for interviewer",
                        "Review portfolio projects"
                    ]
                })
            },
            {
                "title": "Study for Data Structures Midterm",
                "description": "Review chapters 1-5, practice problems",
                "deadline": now + timedelta(days=7),
                "priority": "high",
                "task_type": "exam_prep",
                "estimated_hours": 12,
                "prep_material": json.dumps({
                    "flashcards": [
                        {"question": "What is a linked list?", "answer": "A linear data structure where elements are stored in nodes"},
                        {"question": "What is Big O notation?", "answer": "A way to describe algorithm performance"},
                        {"question": "What is a stack?", "answer": "LIFO data structure"},
                        {"question": "What is a queue?", "answer": "FIFO data structure"},
                        {"question": "What is recursion?", "answer": "A function that calls itself"}
                    ],
                    "quiz_questions": [
                        {
                            "question": "What is the time complexity of binary search?",
                            "options": ["O(n)", "O(log n)", "O(n²)", "O(1)"],
                            "correct": "O(log n)"
                        },
                        {
                            "question": "Which data structure uses LIFO?",
                            "options": ["Queue", "Stack", "Array", "Tree"],
                            "correct": "Stack"
                        }
                    ],
                    "key_concepts": [
                        "Arrays and Lists",
                        "Stacks and Queues",
                        "Trees and Graphs",
                        "Sorting Algorithms",
                        "Time Complexity"
                    ],
                    "study_tips": [
                        "Practice implementing data structures from scratch",
                        "Solve practice problems daily",
                        "Review lecture notes and textbook",
                        "Form a study group"
                    ]
                })
            },
            {
                "title": "Read Chapter 6 - Algorithms",
                "description": "Graph algorithms and traversal",
                "deadline": now + timedelta(days=4),
                "priority": "medium",
                "task_type": "reading",
                "estimated_hours": 3
            }
        ]
        
        for task_data in sample_tasks:
            existing = db.query(Task).filter(
                Task.user_id == sample_user.id,
                Task.title == task_data["title"]
            ).first()
            
            if not existing:
                task = Task(
                    user_id=sample_user.id,
                    **task_data,
                    source_type="manual"
                )
                db.add(task)
        
        db.commit()
        print(f"Created {len(sample_tasks)} sample tasks")
        
        print("\n✅ Sample data created successfully!")
        print("\nSample credentials:")
        print("  Email: demo@example.com")
        print("  Password: demo123")
        
    except Exception as e:
        print(f"Error creating sample data: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_data()
