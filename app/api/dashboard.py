from fastapi import APIRouter, HTTPException, Depends, status
from datetime import date, timedelta
from typing import Optional

from app.models.user import User
from app.models.activity import (
    ProblemSolvingSessionCreate, ProblemSolvingSession,
    ContributionHeatmapData, DashboardStats, UserStreakInfo
)
from app.crud.activity import ActivityCRUD
from app.api.auth import get_current_user
from app.db.database import get_db

router = APIRouter(tags=["Dashboard"])

def get_activity_crud():
    """Dependency to get ActivityCRUD instance."""
    db = get_db()
    return ActivityCRUD(db)

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    activity_crud: ActivityCRUD = Depends(get_activity_crud)
):
    """Get comprehensive dashboard statistics for the current user."""
    stats = activity_crud.get_dashboard_stats(current_user.key)
    
    if not stats:
        # Return default stats for new users
        return DashboardStats(
            expertise_rank=current_user.expertise_rank,
            rank_title=activity_crud.get_rank_title(current_user.expertise_rank),
            peak_rank=current_user.peak_rank or current_user.expertise_rank,
            global_rank=None,
            country_rank=None,
            problems_solved=0,
            acceptance_rate=0.0,
            current_streak=0,
            longest_streak=0,
            total_active_days=0,
            total_points=0,
            monthly_average=0.0,
            recent_activity=[],
            skill_strengths=[],
            areas_for_improvement=["Getting Started"]
        )
    
    return stats

@router.get("/streak", response_model=UserStreakInfo)
async def get_user_streak(
    current_user: User = Depends(get_current_user),
    activity_crud: ActivityCRUD = Depends(get_activity_crud)
):
    """Get current user's streak information."""
    return activity_crud.get_user_streak_info(current_user.key)

@router.get("/contribution-heatmap", response_model=ContributionHeatmapData)
async def get_contribution_heatmap(
    days: int = 365,
    current_user: User = Depends(get_current_user),
    activity_crud: ActivityCRUD = Depends(get_activity_crud)
):
    """Get contribution heatmap data for the specified number of days."""
    if days < 1 or days > 730:  # Limit to 2 years maximum
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days parameter must be between 1 and 730"
        )
    
    return activity_crud.get_contribution_heatmap_data(current_user.key, days)

@router.post("/record-session", response_model=ProblemSolvingSession)
async def record_problem_solving_session(
    session_data: ProblemSolvingSessionCreate,
    current_user: User = Depends(get_current_user),
    activity_crud: ActivityCRUD = Depends(get_activity_crud)
):
    """Record a new problem solving session."""
    # Ensure the session belongs to the current user
    session_data.user_key = current_user.key
    
    # Validate session date (should not be in the future)
    if session_data.session_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session date cannot be in the future"
        )
    
    # Create the session
    session = activity_crud.create_problem_solving_session(session_data)
    
    # Convert to API model
    return ProblemSolvingSession(
        key=session.key,
        user_key=session.user_key,
        question_key=session.question_key,
        difficulty=session.difficulty,
        is_correct=session.is_correct,
        time_taken_seconds=session.time_taken_seconds,
        points_earned=session.points_earned,
        session_date=session.session_date,
        created_at=session.created_at,
        updated_at=session.updated_at,
        hints_used=session.hints_used,
        attempts_count=session.attempts_count,
        programming_language=session.programming_language,
        solution_quality_score=session.solution_quality_score
    )

@router.get("/sessions")
async def get_user_sessions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    activity_crud: ActivityCRUD = Depends(get_activity_crud)
):
    """Get problem solving sessions for the current user."""
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 200"
        )
    
    # Parse dates if provided
    parsed_start_date = None
    parsed_end_date = None
    
    try:
        if start_date:
            parsed_start_date = date.fromisoformat(start_date)
        if end_date:
            parsed_end_date = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    sessions = activity_crud.get_user_sessions(
        current_user.key, 
        parsed_start_date, 
        parsed_end_date, 
        limit
    )
    
    # Convert to API models
    return [
        ProblemSolvingSession(
            key=session.key,
            user_key=session.user_key,
            question_key=session.question_key,
            difficulty=session.difficulty,
            is_correct=session.is_correct,
            time_taken_seconds=session.time_taken_seconds,
            points_earned=session.points_earned,
            session_date=session.session_date,
            created_at=session.created_at,
            updated_at=session.updated_at,
            hints_used=session.hints_used,
            attempts_count=session.attempts_count,
            programming_language=session.programming_language,
            solution_quality_score=session.solution_quality_score
        )
        for session in sessions
    ]

@router.get("/profile-summary")
async def get_profile_summary(
    current_user: User = Depends(get_current_user),
    activity_crud: ActivityCRUD = Depends(get_activity_crud)
):
    """Get profile summary for the profile header component."""
    # Get basic stats
    stats = activity_crud.get_dashboard_stats(current_user.key)
    
    if not stats:
        # Return default for new users
        return {
            "user": {
                "name": current_user.name,
                "email": current_user.email,
                "created_at": current_user.created_at.isoformat()
            },
            "rating": current_user.expertise_rank,
            "rank": activity_crud.get_rank_title(current_user.expertise_rank),
            "max_rating": current_user.peak_rank or current_user.expertise_rank,
            "global_rank": None,
            "country_rank": None,
            "problems_solved": 0,
            "acceptance_rate": 0.0
        }
    
    return {
        "user": {
            "name": current_user.name,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat()
        },
        "rating": stats.expertise_rank,
        "rank": stats.rank_title,
        "max_rating": stats.peak_rank,
        "global_rank": stats.global_rank,
        "country_rank": stats.country_rank,
        "problems_solved": stats.problems_solved,
        "acceptance_rate": stats.acceptance_rate
    }

@router.get("/rankings")
async def get_user_rankings(
    current_user: User = Depends(get_current_user),
    activity_crud: ActivityCRUD = Depends(get_activity_crud)
):
    """Get current user's global and country rankings."""
    global_rank, country_rank = activity_crud.calculate_user_rankings(current_user.key)
    
    return {
        "global_rank": global_rank,
        "country_rank": country_rank,
        "total_users": None,  # Could be calculated if needed
        "ranking_last_updated": None  # Could track when rankings were last calculated
    }
