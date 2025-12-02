from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, get_cors_origins
from app.database import engine, Base
from app.routers import (
    auth_router,
    events_router,
    tasks_router,
    calendar_sync_router,
    documents_router
)
import re

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered productivity calendar that helps manage tasks, deadlines, and prep sessions"
)

# Custom CORS middleware to handle Vercel preview URLs
def cors_allow_all_vercel(origin: str) -> bool:
    """Allow all Vercel domains and localhost"""
    allowed_patterns = [
        r"^https://.*\.vercel\.app$",  # All Vercel domains
        r"^http://localhost:\d+$",      # Localhost with any port
        r"^http://127\.0\.0\.1:\d+$",  # 127.0.0.1 with any port
    ]
    
    # Also check against configured origins
    configured_origins = get_cors_origins()
    if origin in configured_origins:
        return True
    
    # Check against patterns
    for pattern in allowed_patterns:
        if re.match(pattern, origin):
            return True
    
    return False

# Configure CORS with custom origin validation
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://.*\.vercel\.app$|^http://localhost:\d+$|^http://127\.0\.0\.1:\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(tasks_router)
app.include_router(calendar_sync_router)
app.include_router(documents_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to AI Productivity Calendar API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
