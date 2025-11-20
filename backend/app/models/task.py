from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    deadline = Column(DateTime)
    completed = Column(Boolean, default=False)
    priority = Column(String)  # high, medium, low
    task_type = Column(String)  # exam_prep, interview_prep, assignment, reading
    prep_material = Column(Text)  # JSON string containing flashcards, quiz questions, etc.
    estimated_hours = Column(Integer)
    source_type = Column(String)  # syllabus, email, manual
    source_file = Column(String)  # path or reference to original document
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tasks")
    event = relationship("Event", back_populates="tasks")
