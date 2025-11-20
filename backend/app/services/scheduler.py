from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.event import Event


class SchedulerService:
    """Service for auto-scheduling prep sessions based on tasks and deadlines."""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
    
    def auto_schedule_prep_sessions(self, task_id: int) -> List[Dict]:
        """
        Automatically schedule preparation sessions for a task.
        Returns a list of suggested prep session events.
        """
        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == self.user_id
        ).first()
        
        if not task or not task.deadline:
            return []
        
        # Get estimated hours (default to 5 if not set)
        estimated_hours = task.estimated_hours or 5
        
        # Calculate prep sessions
        prep_sessions = self._calculate_prep_sessions(
            deadline=task.deadline,
            total_hours=estimated_hours,
            task_title=task.title
        )
        
        # Check for conflicts with existing events
        available_sessions = self._filter_conflicting_sessions(prep_sessions)
        
        return available_sessions
    
    def _calculate_prep_sessions(self, deadline: datetime, total_hours: int, 
                                 task_title: str) -> List[Dict]:
        """Calculate optimal prep session schedule."""
        sessions = []
        now = datetime.utcnow()
        
        # Don't schedule if deadline has passed
        if deadline <= now:
            return sessions
        
        # Calculate days until deadline
        days_until = (deadline - now).days
        
        # Determine session distribution strategy
        if days_until < 2:
            # Urgent: Schedule longer sessions
            session_duration = min(total_hours, 3)  # Max 3 hours per session
            num_sessions = max(1, total_hours // session_duration)
        elif days_until < 7:
            # Schedule over multiple days, 1-2 hour sessions
            session_duration = 2
            num_sessions = max(1, total_hours // session_duration)
        else:
            # Spread out over time, 1 hour sessions
            session_duration = 1
            num_sessions = total_hours
        
        # Schedule sessions
        for i in range(num_sessions):
            # Calculate session timing
            if days_until < 2:
                # Schedule today and tomorrow
                day_offset = i % 2
                hour = 14 + (i // 2) * 2  # Start at 2 PM
            else:
                # Spread across available days
                day_offset = i * (days_until // num_sessions)
                hour = 18  # Default to 6 PM
            
            session_start = now + timedelta(days=day_offset, hours=hour)
            session_start = session_start.replace(minute=0, second=0, microsecond=0)
            session_end = session_start + timedelta(hours=session_duration)
            
            # Don't schedule past deadline
            if session_end > deadline:
                continue
            
            sessions.append({
                'title': f"Prep: {task_title} (Session {i + 1})",
                'description': f"Preparation session for {task_title}",
                'start_time': session_start,
                'end_time': session_end,
                'event_type': 'prep_session'
            })
        
        return sessions
    
    def _filter_conflicting_sessions(self, proposed_sessions: List[Dict]) -> List[Dict]:
        """Filter out sessions that conflict with existing events."""
        available_sessions = []
        
        for session in proposed_sessions:
            # Check for conflicts
            conflicts = self.db.query(Event).filter(
                Event.user_id == self.user_id,
                Event.start_time < session['end_time'],
                Event.end_time > session['start_time']
            ).count()
            
            if conflicts == 0:
                available_sessions.append(session)
            else:
                # Try to reschedule to next available slot
                rescheduled = self._find_next_available_slot(
                    session['start_time'],
                    session['end_time'] - session['start_time']
                )
                
                if rescheduled:
                    session['start_time'] = rescheduled
                    session['end_time'] = rescheduled + (session['end_time'] - session['start_time'])
                    available_sessions.append(session)
        
        return available_sessions
    
    def _find_next_available_slot(self, preferred_time: datetime, 
                                  duration: timedelta) -> Optional[datetime]:
        """Find the next available time slot after preferred_time."""
        # Check slots in 1-hour increments for the next 7 days
        for day in range(7):
            for hour in range(8, 22):  # 8 AM to 10 PM
                candidate_start = (preferred_time + timedelta(days=day)).replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
                candidate_end = candidate_start + duration
                
                # Check for conflicts
                conflicts = self.db.query(Event).filter(
                    Event.user_id == self.user_id,
                    Event.start_time < candidate_end,
                    Event.end_time > candidate_start
                ).count()
                
                if conflicts == 0:
                    return candidate_start
        
        return None
    
    def get_recommended_schedule(self, days_ahead: int = 7) -> Dict:
        """Get recommended schedule overview for upcoming days."""
        now = datetime.utcnow()
        end_date = now + timedelta(days=days_ahead)
        
        # Get upcoming tasks
        tasks = self.db.query(Task).filter(
            Task.user_id == self.user_id,
            Task.deadline >= now,
            Task.deadline <= end_date,
            Task.completed == False
        ).all()
        
        # Get existing events
        events = self.db.query(Event).filter(
            Event.user_id == self.user_id,
            Event.start_time >= now,
            Event.start_time <= end_date
        ).all()
        
        # Calculate total prep time needed
        total_prep_hours = sum(task.estimated_hours or 5 for task in tasks)
        
        # Calculate free hours
        busy_hours = sum(
            (event.end_time - event.start_time).total_seconds() / 3600 
            for event in events
        )
        
        total_hours = days_ahead * 12  # Assume 12 productive hours per day
        free_hours = total_hours - busy_hours
        
        return {
            'days_ahead': days_ahead,
            'total_tasks': len(tasks),
            'total_prep_hours_needed': total_prep_hours,
            'busy_hours': busy_hours,
            'free_hours': free_hours,
            'is_feasible': free_hours >= total_prep_hours,
            'utilization_percentage': (busy_hours / total_hours * 100) if total_hours > 0 else 0
        }
