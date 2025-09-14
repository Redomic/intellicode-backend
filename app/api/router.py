from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.questions import router as questions_router
from app.api.assessments import router as assessments_router
from app.api.dashboard import router as dashboard_router
from app.api.behavior import router as behavior_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(questions_router, prefix="/questions", tags=["questions"])
api_router.include_router(assessments_router, prefix="/assessments", tags=["assessments"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(behavior_router, prefix="/behavior", tags=["behavior"])
