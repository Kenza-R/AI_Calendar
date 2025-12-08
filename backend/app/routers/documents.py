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
        
        # Extract semester metadata for relative date parsing
        def extract_semester_info(text: str) -> Optional[datetime]:
            """Try to extract semester start date from syllabus."""
            import re
            
            # Look for patterns like "Spring 2024", "Fall 2023", "January 15, 2024"
            semester_patterns = [
                r'Spring\s+(\d{4})',
                r'Fall\s+(\d{4})',
                r'Winter\s+(\d{4})',
                r'Summer\s+(\d{4})',
            ]
            
            for pattern in semester_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    year = int(match.group(1))
                    semester = match.group(0).lower()
                    if 'spring' in semester:
                        return datetime(year, 1, 15)
                    elif 'summer' in semester:
                        return datetime(year, 6, 1)
                    elif 'fall' in semester:
                        return datetime(year, 9, 1)
                    elif 'winter' in semester:
                        return datetime(year, 1, 5)
            
            return None
        
        # Run CrewAI extraction
        extraction_result = extract_deadlines_and_tasks(file_content, file.filename)
        
        if not extraction_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=extraction_result.get("error", "Extraction failed")
            )
        
        items_with_workload = extraction_result.get("items_with_workload", [])
        
        # Extract semester info for date parsing
        if file_extension == ".pdf":
            from app.utils.pdf_parser import parse_pdf
            text = parse_pdf(file_content)
        else:
            text = file_content.decode('utf-8')
        
        semester_start = extract_semester_info(text[:2000])  # Check first 2000 chars
        
        # DEBUG: See exact agent output format
        print(f"\n{'='*60}")
        print(f"📊 CrewAI EXTRACTION RESULTS")
        print(f"{'='*60}")
        print(f"Total items extracted: {len(items_with_workload)}")
        print(f"Total estimated hours: {extraction_result.get('total_estimated_hours', 0)}h")
        print(f"Extraction success: {extraction_result.get('success')}")
        
        if items_with_workload:
            print(f"\n📋 FIRST 3 ITEMS (showing date format):")
            for i, item in enumerate(items_with_workload[:3], 1):
                print(f"\n  Item {i}:")
                print(f"    Title: {item.get('title', 'NO TITLE')}")
                print(f"    Date: '{item.get('date', 'NO DATE')}'")
                print(f"    Type: {item.get('type', 'NO TYPE')}")
                print(f"    Hours: {item.get('estimated_hours', 'NO HOURS')}")
                print(f"    Breakdown: {item.get('workload_breakdown', 'NO BREAKDOWN')[:50]}...")
        else:
            print(f"⚠️  NO ITEMS RETURNED BY AGENTS!")
        print(f"{'='*60}\n")
        
        # Helper function to parse dates
        def parse_relative_date(date_str: str, semester_start: Optional[datetime] = None) -> Optional[datetime]:
            """Parse relative dates like 'Week 1', 'Week 2' to actual dates."""
            import re
            
            if not semester_start:
                # Default to current date if no semester start provided
                semester_start = datetime.now()
            
            # Match "Week N" pattern
            week_match = re.search(r'Week\s+(\d+)', date_str, re.IGNORECASE)
            if week_match:
                week_num = int(week_match.group(1))
                # Calculate date: semester_start + (week_num - 1) * 7 days
                return semester_start + timedelta(days=(week_num - 1) * 7)
            
            # Match "Session N" pattern
            session_match = re.search(r'Session\s+(\d+)', date_str, re.IGNORECASE)
            if session_match:
                session_num = int(session_match.group(1))
                # Assume sessions are weekly
                return semester_start + timedelta(days=(session_num - 1) * 7)
            
            return None
        
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
            
            # Try parsing relative dates (Week 1, Session 2, etc.)
            # Use extracted semester start or estimate based on current date
            relative_date = parse_relative_date(date_str, semester_start)
            if relative_date:
                return relative_date
            
            return None
        
        # Parse document text for database
        if file_extension == ".pdf":
            text_content = parse_pdf(file_content)
        else:
            text_content = parse_text_document(file_content, file_extension)
        
        # Filter out class sessions BEFORE processing
        deadline_items = [
            item for item in items_with_workload 
            if item.get("type") != "class_session"
        ]
        
        print(f"📊 After filtering class sessions: {len(deadline_items)} deadline items to process\n")
        
        # Create tasks and events from extracted items
        created_tasks = []
        created_events = []
        skipped_items = []
        
        for idx, item in enumerate(deadline_items, 1):
            item_type = item.get("type", "deadline")
            
            # Parse date with detailed logging
            date_str = item.get("date", "")
            print(f"\n🔍 Processing item {idx}/{len(deadline_items)}: {item.get('title', 'Unknown')}")
            print(f"   Raw date string: '{date_str}'")
            
            deadline_date = parse_date_string(date_str)
            
            if not deadline_date:
                skipped_items.append({"item": item.get("title", "Unknown"), "date": date_str})
                print(f"   ❌ SKIPPED - Could not parse date: '{date_str}'")
                continue
            
            print(f"   ✅ Parsed successfully: {deadline_date}")
            
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
            
            # Create task with ALL workload estimate fields (Phase 5 Task 5.2)
            estimated_hours = item.get("estimated_hours", 5)
            workload_breakdown = item.get("workload_breakdown", "")
            confidence = item.get("confidence", "")
            notes = item.get("notes", "")
            
            # Build comprehensive task description with workload details
            task_description = item.get("description", "")
            
            # Append workload breakdown if present
            if workload_breakdown:
                task_description += f"\n\n⏱️ Workload: {workload_breakdown}"
            
            # Append confidence level if present
            if confidence:
                confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence.lower(), "")
                task_description += f"\n{confidence_emoji} Confidence: {confidence.title()}"
            
            # Append notes if present
            if notes:
                task_description += f"\n📝 Notes: {notes}"
            
            # Debug log to track workload data preservation
            print(f"   💾 Saving task '{item.get('title')}' with estimated_hours={estimated_hours}")
            if workload_breakdown or confidence or notes:
                print(f"      Workload details: breakdown={bool(workload_breakdown)}, confidence={confidence}, notes={bool(notes)}")
            
            # Extract optional/conditional information
            is_optional = item.get("is_optional", False)
            conditions = item.get("conditions", "")
            
            new_task = Task(
                user_id=current_user.id,
                event_id=new_event.id,
                title=item.get("title", "Untitled Task"),
                description=task_description,
                deadline=deadline_date,
                priority="high" if item_type in ["exam", "quiz"] else "medium",
                task_type=item_type,
                estimated_hours=estimated_hours,
                is_optional=is_optional,
                conditions=conditions,
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
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"📊 FINAL RESULTS")
        print(f"{'='*60}")
        print(f"✅ Tasks created: {len(created_tasks)}")
        print(f"✅ Events created: {len(created_events)}")
        print(f"⚠️  Items skipped: {len(skipped_items)}")
        if skipped_items:
            print(f"\nSkipped items details:")
            for skip in skipped_items[:5]:  # Show first 5
                print(f"  - {skip['item']}: date='{skip['date']}'")
        print(f"{'='*60}\n")
        
        return {
            "message": f"Successfully processed {file.filename} with CrewAI pipeline",
            "document_id": document.id,
            "tasks_created": len(created_tasks),
            "events_created": len(created_events),
            "total_estimated_hours": extraction_result.get("total_estimated_hours", 0),
            "tasks": created_tasks,
            "events": created_events,
            "skipped_items": skipped_items,
            "qa_summary": extraction_result.get("qa_report", {}).get("summary", ""),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.post("/upload-syllabus-enhanced", response_model=dict)
async def upload_syllabus_enhanced(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Alias for upload-syllabus-crewai for backwards compatibility.
    Routes to the CrewAI pipeline.
    """
    return await upload_syllabus_crewai(file, current_user, db)


@router.post("/upload-syllabus", response_model=dict)
async def upload_syllabus(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Default syllabus upload endpoint. Routes to CrewAI pipeline.
    """
    return await upload_syllabus_crewai(file, current_user, db)
