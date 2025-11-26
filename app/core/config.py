from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database settings
    ARANGO_URL: str = "http://localhost:8529"
    ARANGO_USERNAME: str = "root"
    ARANGO_PASSWORD: str = "openSesame"
    ARANGO_DATABASE: str = "intellicode"
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    FRONTEND_URL: str = "http://localhost:5173"
    
    # AI Agent settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"  # Gemini 2.5 Flash
    
    # Railway/Production settings
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() in ["production", "prod"]
    
    @property
    def allowed_origins(self) -> list:
        """Get list of allowed CORS origins."""
        # In production, allow the specific frontend URL
        # In development, allow both localhost variations
        if self.is_production:
            return [self.FRONTEND_URL]
        return [
            self.FRONTEND_URL,
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ]

settings = Settings()
