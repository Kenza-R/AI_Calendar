from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.calendar_integration import CalendarIntegration
from app.utils.llm_service import extract_deadlines_from_text


class GmailService:
    """Service for interacting with Gmail API."""
    
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
    
    def scan_for_deadlines(self, days_back: int = 7) -> List[Dict]:
        """Scan Gmail for emails containing deadline information."""
        if not self.credentials:
            return []
        
        try:
            service = build('gmail', 'v1', credentials=self.credentials)
            
            # Search for emails with deadline-related keywords
            query = 'subject:(deadline OR interview OR exam OR assignment OR due) newer_than:7d'
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            messages = results.get('messages', [])
            
            deadlines = []
            for message in messages:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract email content
                subject = self._get_header(msg_data, 'Subject')
                body = self._get_email_body(msg_data)
                
                # Use LLM to extract deadlines
                extracted = extract_deadlines_from_text(
                    f"Subject: {subject}\n\n{body}",
                    context="email"
                )
                
                deadlines.extend(extracted)
            
            return deadlines
        
        except Exception as e:
            print(f"Error scanning Gmail: {str(e)}")
            return []
    
    def _get_header(self, message: Dict, header_name: str) -> str:
        """Extract header value from Gmail message."""
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == header_name:
                return header['value']
        return ''
    
    def _get_email_body(self, message: Dict) -> str:
        """Extract body text from Gmail message."""
        try:
            if 'parts' in message['payload']:
                parts = message['payload']['parts']
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            import base64
                            return base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                data = message['payload']['body'].get('data', '')
                if data:
                    import base64
                    return base64.urlsafe_b64decode(data).decode('utf-8')
        except Exception as e:
            print(f"Error extracting email body: {str(e)}")
        
        return ''
