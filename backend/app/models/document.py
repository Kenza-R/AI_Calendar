from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Document(Base):
    """Model for storing uploaded documents (syllabi, etc.)"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, txt, docx
    file_path = Column(String)  # Path to stored file
    content_text = Column(Text)  # Extracted text content
    upload_date = Column(DateTime, default=datetime.utcnow)
    document_type = Column(String, default="syllabus")  # syllabus, assignment, etc.
    
    # Metadata
    course_name = Column(String)
    semester = Column(String)
    tasks_created = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', user_id={self.user_id})>"
