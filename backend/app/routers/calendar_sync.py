from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.calendar_integration import CalendarIntegration
from app.models.event import Event
from app.schemas.calendar import CalendarIntegrationResponse
from app.utils.auth import get_current_user
from app.services.google_calendar import GoogleCalendarService
from app.services.gmail_service import GmailService
from app.services.outlook_calendar import OutlookCalendarService
from app.services.scheduler import SchedulerService

router = APIRouter(prefix="/calendar", tags=["Calendar Integration"])


@router.get("/integrations", response_model=List[CalendarIntegrationResponse])
async def get_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all calendar integrations for the current user."""
    integrations = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == current_user.id
    ).all()
    
    return integrations


@router.post("/sync/google")
async def sync_google_calendar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync events from Google Calendar.
    Note: In production, this would require OAuth flow first.
    """
    # Get or create Google integration
    integration = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == current_user.id,
        CalendarIntegration.provider == "google"
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected. Please connect your account first."
        )
    
    # Sync events
    google_service = GoogleCalendarService(integration)
    events = google_service.get_events()
    
    # Save events to database
    synced_count = 0
    for event_data in events:
        # Check if event already exists
        existing = db.query(Event).filter(
            Event.user_id == current_user.id,
            Event.external_id == event_data.get('external_id')
        ).first()
        
        if not existing:
            new_event = Event(
                user_id=current_user.id,
                external_id=event_data.get('external_id'),
                title=event_data.get('title'),
                description=event_data.get('description'),
                start_time=datetime.fromisoformat(event_data.get('start_time').replace('Z', '+00:00')),
                end_time=datetime.fromisoformat(event_data.get('end_time').replace('Z', '+00:00')),
                location=event_data.get('location'),
                source='google'
            )
            db.add(new_event)
            synced_count += 1
    
    integration.last_sync = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Google Calendar synced successfully",
        "events_synced": synced_count
    }


@router.post("/sync/gmail")
async def scan_gmail_for_deadlines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scan Gmail for deadline information.
    Note: In production, this would require OAuth flow first.
    """
    integration = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == current_user.id,
        CalendarIntegration.provider == "google"
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gmail not connected. Please connect your Google account first."
        )
    
    gmail_service = GmailService(integration)
    deadlines = gmail_service.scan_for_deadlines()
    
    return {
        "message": "Gmail scanned successfully",
        "deadlines_found": len(deadlines),
        "deadlines": deadlines
    }


@router.post("/sync/outlook")
async def sync_outlook_calendar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync events from Outlook Calendar.
    Note: In production, this would require OAuth flow first.
    """
    integration = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == current_user.id,
        CalendarIntegration.provider == "outlook"
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlook Calendar not connected. Please connect your account first."
        )
    
    outlook_service = OutlookCalendarService(integration)
    events = outlook_service.get_events()
    
    synced_count = 0
    for event_data in events:
        existing = db.query(Event).filter(
            Event.user_id == current_user.id,
            Event.external_id == event_data.get('external_id')
        ).first()
        
        if not existing:
            new_event = Event(
                user_id=current_user.id,
                external_id=event_data.get('external_id'),
                title=event_data.get('title'),
                description=event_data.get('description'),
                start_time=datetime.fromisoformat(event_data.get('start_time')),
                end_time=datetime.fromisoformat(event_data.get('end_time')),
                location=event_data.get('location'),
                source='outlook'
            )
            db.add(new_event)
            synced_count += 1
    
    integration.last_sync = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Outlook Calendar synced successfully",
        "events_synced": synced_count
    }


@router.get("/schedule-overview")
async def get_schedule_overview(
    days_ahead: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get an overview of the schedule for the next N days."""
    scheduler = SchedulerService(db, current_user.id)
    overview = scheduler.get_recommended_schedule(days_ahead)
    
    return overview
