from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.router import api_router
from app.middleware.error_handler import setup_error_middleware

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
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

@app.get("/")
async def root():
    """API information and health check."""
    return {
        "message": "IntelliCode API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy"
    }
