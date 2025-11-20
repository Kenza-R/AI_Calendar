from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.calendar_integration import CalendarIntegration


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""
    
    def __init__(self, integration: CalendarIntegration):
        self.integration = integration
        self.credentials = self._get_credentials()
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Create credentials from stored tokens."""
        if not self.integration.access_token:
            return None
        
        return Credentials(
            token=self.integration.access_token,
            refresh_token=self.integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
        )
    
    def get_events(self, days_ahead: int = 30) -> List[Dict]:
        """Fetch events from Google Calendar."""
        if not self.credentials:
            return []
        
        try:
            service = build('calendar', 'v3', credentials=self.credentials)
            
            # Get events for the next N days
            now = datetime.utcnow().isoformat() + 'Z'
            end_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end_date,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return self._format_events(events)
        
        except Exception as e:
            print(f"Error fetching Google Calendar events: {str(e)}")
            return []
    
    def _format_events(self, events: List[Dict]) -> List[Dict]:
        """Format Google Calendar events to our standard format."""
        formatted = []
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted.append({
                'external_id': event['id'],
                'title': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start_time': start,
                'end_time': end,
                'location': event.get('location', ''),
                'source': 'google'
            })
        
        return formatted
    
    def create_event(self, title: str, start_time: datetime, end_time: datetime, 
                    description: str = "", location: str = "") -> Optional[str]:
        """Create an event in Google Calendar."""
        if not self.credentials:
            return None
        
        try:
            service = build('calendar', 'v3', credentials=self.credentials)
            
            event = {
                'summary': title,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            return created_event.get('id')
        
        except Exception as e:
            print(f"Error creating Google Calendar event: {str(e)}")
            return None
