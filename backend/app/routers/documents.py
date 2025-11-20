from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.utils.auth import get_current_user
from app.utils.pdf_parser import parse_pdf, parse_text_document
from app.utils.llm_service import extract_deadlines_from_text
import json

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload-syllabus", response_model=dict)
async def upload_syllabus(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a syllabus document (PDF, TXT, or DOCX).
    Extracts deadlines and creates tasks automatically.
    """
    # Validate file type
    allowed_extensions = [".pdf", ".txt", ".docx"]
    file_extension = "." + file.filename.split(".")[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Parse document based on type
        if file_extension == ".pdf":
            text_content = parse_pdf(file_content)
        else:
            text_content = parse_text_document(file_content, file_extension)
        
        # Extract deadlines using LLM
        deadlines = extract_deadlines_from_text(text_content, context="syllabus")
        
        # Create tasks from extracted deadlines
        created_tasks = []
        for deadline_info in deadlines:
            # Parse date string to datetime
            try:
                deadline_date = datetime.fromisoformat(deadline_info.get("date"))
            except (ValueError, TypeError):
                # If date parsing fails, skip this item
                continue
            
            # Create task
            new_task = Task(
                user_id=current_user.id,
                title=deadline_info.get("title", "Untitled Task"),
                description=deadline_info.get("description", ""),
                deadline=deadline_date,
                priority="medium",
                task_type=deadline_info.get("type", "assignment"),
                estimated_hours=deadline_info.get("estimated_hours", 5),
                source_type="syllabus",
                source_file=file.filename
            )
            
            db.add(new_task)
            created_tasks.append({
                "title": new_task.title,
                "deadline": new_task.deadline.isoformat(),
                "type": new_task.task_type
            })
        
        db.commit()
        
        return {
            "message": f"Successfully processed {file.filename}",
            "tasks_created": len(created_tasks),
            "tasks": created_tasks,
            "extracted_text_preview": text_content[:500] + "..." if len(text_content) > 500 else text_content
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.post("/parse-text", response_model=dict)
async def parse_text_for_deadlines(
    text: str,
    context: str = "general",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Parse raw text for deadlines and create tasks.
    Useful for pasting email content or other text.
    """
    try:
        # Extract deadlines using LLM
        deadlines = extract_deadlines_from_text(text, context=context)
        
        # Create tasks from extracted deadlines
        created_tasks = []
        for deadline_info in deadlines:
            try:
                deadline_date = datetime.fromisoformat(deadline_info.get("date"))
            except (ValueError, TypeError):
                continue
            
            new_task = Task(
                user_id=current_user.id,
                title=deadline_info.get("title", "Untitled Task"),
                description=deadline_info.get("description", ""),
                deadline=deadline_date,
                priority="medium",
                task_type=deadline_info.get("type", "deadline"),
                estimated_hours=deadline_info.get("estimated_hours", 5),
                source_type=context
            )
            
            db.add(new_task)
            created_tasks.append({
                "title": new_task.title,
                "deadline": new_task.deadline.isoformat(),
                "type": new_task.task_type
            })
        
        db.commit()
        
        return {
            "message": "Successfully extracted deadlines from text",
            "tasks_created": len(created_tasks),
            "tasks": created_tasks
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing text: {str(e)}"
        )
