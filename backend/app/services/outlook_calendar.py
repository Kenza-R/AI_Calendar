import msal
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.calendar_integration import CalendarIntegration
from app.config import settings


class OutlookCalendarService:
    """Service for interacting with Microsoft Outlook Calendar API."""
    
    AUTHORITY = "https://login.microsoftonline.com/common"
    SCOPE = ["https://graph.microsoft.com/.default"]
    GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, integration: CalendarIntegration):
        self.integration = integration
    
    def _get_access_token(self) -> Optional[str]:
        """Get access token using refresh token if needed."""
        if not self.integration.refresh_token:
            return self.integration.access_token
        
        try:
            app = msal.ConfidentialClientApplication(
                settings.MICROSOFT_CLIENT_ID,
                authority=self.AUTHORITY,
                client_credential=settings.MICROSOFT_CLIENT_SECRET,
            )
            
            result = app.acquire_token_by_refresh_token(
                self.integration.refresh_token,
                scopes=self.SCOPE
            )
            
            if "access_token" in result:
                return result["access_token"]
            
            return self.integration.access_token
        
        except Exception as e:
            print(f"Error refreshing Outlook token: {str(e)}")
            return self.integration.access_token
    
    def get_events(self, days_ahead: int = 30) -> List[Dict]:
        """Fetch events from Outlook Calendar."""
        access_token = self._get_access_token()
        if not access_token:
            return []
        
        try:
            import httpx
            
            start_date = datetime.utcnow().isoformat()
            end_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat()
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Filter events by date range
            url = f"{self.GRAPH_ENDPOINT}/me/calendar/events"
            params = {
                '$filter': f"start/dateTime ge '{start_date}' and start/dateTime le '{end_date}'",
                '$orderby': 'start/dateTime',
                '$top': 100
            }
            
            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('value', [])
            
            return self._format_events(events)
        
        except Exception as e:
            print(f"Error fetching Outlook Calendar events: {str(e)}")
            return []
    
    def _format_events(self, events: List[Dict]) -> List[Dict]:
        """Format Outlook Calendar events to our standard format."""
        formatted = []
        
        for event in events:
            formatted.append({
                'external_id': event['id'],
                'title': event.get('subject', 'No Title'),
                'description': event.get('bodyPreview', ''),
                'start_time': event['start']['dateTime'],
                'end_time': event['end']['dateTime'],
                'location': event.get('location', {}).get('displayName', ''),
                'source': 'outlook'
            })
        
        return formatted
    
    def create_event(self, title: str, start_time: datetime, end_time: datetime,
                    description: str = "", location: str = "") -> Optional[str]:
        """Create an event in Outlook Calendar."""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        try:
            import httpx
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            event_data = {
                'subject': title,
                'body': {
                    'contentType': 'text',
                    'content': description
                },
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC'
                },
                'location': {
                    'displayName': location
                }
            }
            
            url = f"{self.GRAPH_ENDPOINT}/me/calendar/events"
            response = httpx.post(url, headers=headers, json=event_data)
            response.raise_for_status()
            
            created_event = response.json()
            return created_event.get('id')
        
        except Exception as e:
            print(f"Error creating Outlook Calendar event: {str(e)}")
            return None
