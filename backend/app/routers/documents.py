from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from pathlib import Path
from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.document import Document
from app.models.event import Event
from app.utils.auth import get_current_user
from app.utils.pdf_parser import parse_pdf, parse_text_document
from app.utils.llm_service import extract_deadlines_from_text

# Import enhanced copy utilities
from app.utils.upload_pdf_copy import save_uploaded_file, get_latest_pdf
from app.utils.test_assessment_parser_copy import extract_assessment_components_api
from app.utils.test_deadline_extraction_copy import extract_deadlines_and_sessions_api
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
        created_events = []
        for deadline_info in deadlines:
            # Parse date string to datetime
            try:
                deadline_date = datetime.fromisoformat(deadline_info.get("date"))
            except (ValueError, TypeError):
                # If date parsing fails, skip this item
                continue
            
            # Create calendar event for the deadline
            # Set event to be at the deadline time (default to end of day)
            event_start = deadline_date.replace(hour=23, minute=59, second=0, microsecond=0)
            event_end = event_start + timedelta(hours=1)
            
            new_event = Event(
                user_id=current_user.id,
                title=f"📅 {deadline_info.get('title', 'Untitled Task')}",
                description=deadline_info.get("description", ""),
                start_time=event_start,
                end_time=event_end,
                event_type="deadline",
                source="syllabus"
            )
            db.add(new_event)
            db.flush()  # Get the event ID
            
            # Create task
            new_task = Task(
                user_id=current_user.id,
                event_id=new_event.id,
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
            created_events.append({
                "title": new_event.title,
                "start_time": new_event.start_time.isoformat()
            })
        
        # Save document record to database
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            file_type=file_extension.replace(".", ""),
            content_text=text_content,
            document_type="syllabus",
            tasks_created=len(created_tasks)
        )
        db.add(document)
        
        db.commit()
        
        return {
            "message": f"Successfully processed {file.filename}",
            "document_id": document.id,
            "tasks_created": len(created_tasks),
            "events_created": len(created_events),
            "tasks": created_tasks,
            "events": created_events,
            "extracted_text_preview": text_content[:500] + "..." if len(text_content) > 500 else text_content
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.get("/", response_model=List[dict])
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents uploaded by the current user."""
    documents = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.upload_date.desc()).all()
    
    return [{
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "upload_date": doc.upload_date.isoformat(),
        "document_type": doc.document_type,
        "tasks_created": doc.tasks_created,
        "course_name": doc.course_name,
        "semester": doc.semester
    } for doc in documents]


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document by ID."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "upload_date": document.upload_date.isoformat(),
        "document_type": document.document_type,
        "tasks_created": document.tasks_created,
        "course_name": document.course_name,
        "semester": document.semester,
        "content_text": document.content_text
    }


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


# ============================================================================
# ENHANCED ENDPOINTS (using copy files)
# ============================================================================

@router.post("/upload-syllabus-enhanced", response_model=dict)
async def upload_syllabus_enhanced(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enhanced syllabus upload with advanced deadline and assessment extraction.
    Uses improved AI parsing with assessment context and class session detection.
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
        
        # Save the uploaded file
        uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        save_result = save_uploaded_file(file_content, file.filename, uploads_dir)
        
        if save_result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=save_result["message"]
            )
        
        # Parse document based on type
        if file_extension == ".pdf":
            text_content = parse_pdf(file_content)
        else:
            text_content = parse_text_document(file_content, file_extension)
        
        # Extract ALL deadlines using improved LLM service
        deadlines = extract_deadlines_from_text(text_content, context="syllabus")
        
        # Create tasks and calendar events from extracted deadlines
        created_tasks = []
        created_events = []
        
        for deadline_info in deadlines:
            # Parse date string to datetime
            try:
                deadline_date = datetime.fromisoformat(deadline_info.get("date"))
            except (ValueError, TypeError):
                # If date parsing fails, skip this item
                continue
            
            # Create calendar event for the deadline
            event_start = deadline_date.replace(hour=23, minute=59, second=0, microsecond=0)
            event_end = event_start + timedelta(hours=1)
            
            new_event = Event(
                user_id=current_user.id,
                title=f"📅 {deadline_info.get('title', 'Untitled Task')}",
                description=deadline_info.get("description", ""),
                start_time=event_start,
                end_time=event_end,
                event_type="deadline",
                source="syllabus"
            )
            db.add(new_event)
            db.flush()  # Get the event ID
            
            # Create task linked to event
            task_type = deadline_info.get("type", "assignment")
            new_task = Task(
                user_id=current_user.id,
                event_id=new_event.id,
                title=deadline_info.get("title", "Untitled Task"),
                description=deadline_info.get("description", ""),
                deadline=deadline_date,
                priority="high" if task_type in ["exam", "quiz"] else "medium",
                task_type=task_type,
                estimated_hours=deadline_info.get("estimated_hours", 5),
                source_type="syllabus",
                source_file=file.filename
            )
            
            db.add(new_task)
            created_tasks.append({
                "title": new_task.title,
                "deadline": new_task.deadline.isoformat(),
                "type": new_task.task_type,
                "description": new_task.description
            })
            created_events.append({
                "title": new_event.title,
                "start_time": new_event.start_time.isoformat()
            })
        
        # Save document record to database
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            file_type=file_extension.replace(".", ""),
            content_text=text_content,
            document_type="syllabus",
            tasks_created=len(created_tasks)
        )
        db.add(document)
        
        db.commit()
        
        # Prepare response
        return {
            "message": f"Successfully processed {file.filename}",
            "file_saved": save_result["filename"],
            "tasks_created": len(created_tasks),
            "events_created": len(created_events),
            "tasks": created_tasks,
            "events": created_events,
            "extracted_text_preview": text_content[:500] + "..." if len(text_content) > 500 else text_content
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.post("/extract-assessments", response_model=dict)
async def extract_assessments(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Extract grading/assessment components from a syllabus.
    Returns structured information about exams, projects, assignments, etc.
    """
    allowed_extensions = [".pdf", ".txt", ".docx"]
    file_extension = "." + file.filename.split(".")[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    try:
        file_content = await file.read()
        
        # Parse document
        if file_extension == ".pdf":
            text_content = parse_pdf(file_content)
        else:
            text_content = parse_text_document(file_content, file_extension)
        
        # Extract assessment components
        result = extract_assessment_components_api(text_content)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to extract assessments")
            )
        
        return {
            "message": f"Successfully extracted assessment components from {file.filename}",
            "components": result.get("components", []),
            "count": result.get("count", 0),
            "total_weight": result.get("total_weight", 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting assessments: {str(e)}"
        )
