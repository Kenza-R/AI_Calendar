from pydantic_settings import BaseSettings
from typing import Optional
import os
import json


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "AI Productivity Calendar"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./ai_calendar.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/auth/microsoft/callback"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # CORS - Allow environment variable override
    @property
    def CORS_ORIGINS(self) -> list:
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            try:
                return json.loads(cors_env)
            except:
                return cors_env.split(",")
        return ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
