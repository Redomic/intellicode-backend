from fastapi import FastAPI
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
