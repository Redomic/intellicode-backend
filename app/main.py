from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from app.core.config import settings
from app.api.router import api_router
from app.middleware.error_handler import setup_error_middleware
from app.services.session_scheduler import start_session_scheduler, stop_session_scheduler

logger = logging.getLogger(__name__)

app = FastAPI(
    title="IntelliCode API",
    description="Backend API for IntelliCode DSA Learning Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Development error handling middleware
setup_error_middleware(app)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # HSTS (Strict Transport Security) - 1 year
    # Only meaningful if served over HTTPS, but good practice to include
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Initialize background services on startup."""
    try:
        logger.info("Starting background services...")
        await start_session_scheduler()
        logger.info("Background services started successfully")
    except Exception as e:
        logger.error(f"Failed to start background services: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background services on shutdown."""
    try:
        logger.info("Stopping background services...")
        await stop_session_scheduler()
        logger.info("Background services stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop background services: {e}")


@app.get("/")
async def root():
    """API information and health check."""
    return {
        "message": "IntelliCode API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy"
    }
