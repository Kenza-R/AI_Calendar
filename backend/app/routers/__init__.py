from .auth import router as auth_router
from .events import router as events_router
from .tasks import router as tasks_router
from .calendar_sync import router as calendar_sync_router
from .documents import router as documents_router

__all__ = [
    "auth_router",
    "events_router", 
    "tasks_router",
    "calendar_sync_router",
    "documents_router"
]
