from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from app.models.user import User
from app.crud.user_extensions import UserCourseExtensions
from app.api.auth import get_current_user
from app.db.database import get_db

router = APIRouter(tags=["Users"])

# Pydantic models for request/response
class CourseActivationRequest(BaseModel):
    course_id: str

class CourseActivationResponse(BaseModel):
    success: bool
    message: str
    active_course: Optional[str]

class UserActiveCourseResponse(BaseModel):
    active_course: Optional[str]

def get_user_course_extensions():
    db = get_db()
    return UserCourseExtensions(db)

@router.post("/courses/activate", response_model=CourseActivationResponse)
async def activate_course(
    request: CourseActivationRequest,
    current_user: User = Depends(get_current_user),
    user_course_ext: UserCourseExtensions = Depends(get_user_course_extensions)
):
    """Activate a course for the current user."""
    try:
        updated_user = user_course_ext.activate_course(current_user.key, request.course_id)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to activate course"
            )
        
        return CourseActivationResponse(
            success=True,
            message=f"Course {request.course_id} activated successfully",
            active_course=updated_user.active_course
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate course: {str(e)}"
        )

@router.post("/courses/deactivate", response_model=CourseActivationResponse)
async def deactivate_course(
    request: CourseActivationRequest,
    current_user: User = Depends(get_current_user),
    user_course_ext: UserCourseExtensions = Depends(get_user_course_extensions)
):
    """Deactivate a course for the current user."""
    try:
        updated_user = user_course_ext.deactivate_course(current_user.key, request.course_id)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate course"
            )
        
        return CourseActivationResponse(
            success=True,
            message=f"Course {request.course_id} deactivated successfully",
            active_course=updated_user.active_course
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate course: {str(e)}"
        )

@router.get("/courses/active", response_model=UserActiveCourseResponse)
async def get_active_course(
    current_user: User = Depends(get_current_user),
    user_course_ext: UserCourseExtensions = Depends(get_user_course_extensions)
):
    """Get the currently active course for the current user."""
    try:
        active_course = user_course_ext.get_user_active_course(current_user.key)
        
        return UserActiveCourseResponse(
            active_course=active_course
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active course: {str(e)}"
        )
