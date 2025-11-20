from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CalendarIntegrationResponse(BaseModel):
    id: int
    user_id: int
    provider: str
    is_active: bool
    last_sync: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
