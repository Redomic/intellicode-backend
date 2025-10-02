from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.questions import router as questions_router
from app.api.assessments import router as assessments_router
from app.api.dashboard import router as dashboard_router
from app.api.behavior import router as behavior_router
from app.api.roadmaps import router as roadmaps_router
from app.api.users import router as users_router
from app.api.sessions import router as sessions_router
from app.api.submissions import router as submissions_router
from app.api.learner_state import router as learner_state_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(questions_router, prefix="/questions", tags=["questions"])
api_router.include_router(assessments_router, prefix="/assessments", tags=["assessments"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(behavior_router, prefix="/behavior", tags=["behavior"])
api_router.include_router(roadmaps_router, prefix="/roadmaps", tags=["roadmaps"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(submissions_router, prefix="/submissions", tags=["submissions"])
api_router.include_router(learner_state_router, tags=["learner-state"])
