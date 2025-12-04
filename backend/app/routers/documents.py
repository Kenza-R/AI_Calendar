from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.document import Document
from app.models.event import Event
from app.utils.auth import get_current_user
from app.utils.pdf_parser import parse_pdf, parse_text_document
# Import CrewAI extraction service (replaces old LLM services)
from app.utils.crewai_extraction_service import extract_deadlines_and_tasks
import json
import re

router = APIRouter(prefix="/documents", tags=["Documents"])


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





@router.post("/extract-assessments", response_model=dict)
async def extract_assessments(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Extract grading/assessment components from a syllabus using CrewAI.
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
        
        # Use CrewAI extraction service
        result = extract_deadlines_and_tasks(file_content, file.filename)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to extract assessments")
            )
        
        # Extract assessment components from the CrewAI result
        items = result.get("items_with_workload", [])
        components = []
        total_weight = 0
        
        for item in items:
            if item.get("type") != "class_session":
                component = {
                    "name": item.get("title", ""),
                    "type": item.get("type", "assignment"),
                    "date": item.get("date", ""),
                    "weight": 0,  # CrewAI doesn't extract weights, but provides workload
                    "estimated_hours": item.get("estimated_hours", 0),
                    "description": item.get("description", "")
                }
                components.append(component)
        
        return {
            "message": f"Successfully extracted assessment components from {file.filename}",
            "components": components,
            "count": len(components),
            "total_estimated_hours": result.get("total_estimated_hours", 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting assessments: {str(e)}"
        )


@router.post("/upload-syllabus-crewai", response_model=dict)
async def upload_syllabus_crewai(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload syllabus using the advanced 4-agent CrewAI pipeline with workload estimation.
    This is the most sophisticated extraction method available.
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
        
        # Run CrewAI extraction
        extraction_result = extract_deadlines_and_tasks(file_content, file.filename)
        
        if not extraction_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=extraction_result.get("error", "Extraction failed")
            )
        
        items_with_workload = extraction_result.get("items_with_workload", [])
        
        # Debug: Print first few items to see the date format
        print(f"📊 CrewAI extracted {len(items_with_workload)} items")
        if items_with_workload:
            print(f"📋 Sample item: {items_with_workload[0]}")
        
        # Helper function to parse dates
        def parse_date_string(date_str: str) -> Optional[datetime]:
            """Parse various date formats to datetime."""
            if not date_str:
                return None
            
            # Clean the date string
            date_str = date_str.strip()
            
            # Try ISO format first
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                pass
            
            # Try common formats (expanded list)
            formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%m/%d/%y",
                "%m-%d-%Y",
                "%d/%m/%Y",
                "%b %d, %Y",
                "%B %d, %Y",
                "%b. %d, %Y",
                "%b %d",
                "%B %d",
                "%b. %d",
                "%d %b %Y",
                "%d %B %Y",
                "%Y/%m/%d",
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    # If no year provided, use current year
                    if dt.year == 1900:
                        dt = dt.replace(year=datetime.now().year)
                    return dt
                except:
                    continue
            
            # Try to extract date using regex as last resort
            import re
            # Match patterns like "Jan 15", "January 15", "1/15", etc.
            month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})', date_str, re.IGNORECASE)
            if month_match:
                try:
                    month_str = month_match.group(1)
                    day_str = month_match.group(2)
                    dt = datetime.strptime(f"{month_str} {day_str} {datetime.now().year}", "%b %d %Y")
                    return dt
                except:
                    pass
            
            return None
        
        # Parse document text for database
        if file_extension == ".pdf":
            text_content = parse_pdf(file_content)
        else:
            text_content = parse_text_document(file_content, file_extension)
        
        # Create tasks and events from extracted items
        created_tasks = []
        created_events = []
        skipped_items = []
        
        for item in items_with_workload:
            item_type = item.get("type", "deadline")
            
            # Skip class sessions (not deadlines)
            if item_type == "class_session":
                continue
            
            # Parse date
            date_str = item.get("date", "")
            deadline_date = parse_date_string(date_str)
            
            if not deadline_date:
                skipped_items.append({"item": item.get("title", "Unknown"), "date": date_str})
                print(f"⚠️ Skipped item - could not parse date: '{date_str}' for task: {item.get('title', 'Unknown')}")
                continue
            
            # Create calendar event
            event_start = deadline_date.replace(hour=23, minute=59, second=0, microsecond=0)
            event_end = event_start + timedelta(hours=1)
            
            new_event = Event(
                user_id=current_user.id,
                title=f"📅 {item.get('title', 'Untitled Task')}",
                description=item.get("description", ""),
                start_time=event_start,
                end_time=event_end,
                event_type="deadline",
                source="syllabus_crewai"
            )
            db.add(new_event)
            db.flush()
            
            # Create task with workload estimate
            estimated_hours = item.get("estimated_hours", 5)
            workload_breakdown = item.get("workload_breakdown", "")
            
            task_description = item.get("description", "")
            if workload_breakdown:
                task_description += f"\n\n⏱️ Workload: {workload_breakdown}"
            
            new_task = Task(
                user_id=current_user.id,
                event_id=new_event.id,
                title=item.get("title", "Untitled Task"),
                description=task_description,
                deadline=deadline_date,
                priority="high" if item_type in ["exam", "quiz"] else "medium",
                task_type=item_type,
                estimated_hours=estimated_hours,
                source_type="syllabus_crewai",
                source_file=file.filename
            )
            
            db.add(new_task)
            created_tasks.append({
                "title": new_task.title,
                "deadline": new_task.deadline.isoformat(),
                "type": new_task.task_type,
                "estimated_hours": estimated_hours,
                "workload_breakdown": workload_breakdown
            })
            created_events.append({
                "title": new_event.title,
                "start_time": new_event.start_time.isoformat()
            })
        
        # Save document record
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
            "message": f"Successfully processed {file.filename} with CrewAI pipeline",
            "document_id": document.id,
            "tasks_created": len(created_tasks),
            "events_created": len(created_events),
            "total_estimated_hours": extraction_result.get("total_estimated_hours", 0),
            "tasks": created_tasks,
            "events": created_events,
            "qa_summary": extraction_result.get("qa_report", {}).get("summary", ""),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )
