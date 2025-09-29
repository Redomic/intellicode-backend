from fastapi import APIRouter, HTTPException, Depends, status
from datetime import date
from typing import Optional, List

from app.models.user import User
from app.models.submission import (
    SubmissionCreate, Submission,
    UserSubmissionStats, ContributionHeatmapData
)
from app.crud.submission import SubmissionCRUD
from app.crud.user import UserCRUD
from app.api.auth import get_current_user
from app.db.database import get_db

router = APIRouter(tags=["Dashboard"])

def get_submission_crud():
    """Dependency to get SubmissionCRUD instance."""
    db = get_db()
    return SubmissionCRUD(db)

def get_user_crud():
    """Dependency to get UserCRUD instance."""
    db = get_db()
    return UserCRUD(db)

# Rank titles based on expertise_rank
RANK_TITLES = {
    (0, 700): "Newbie",
    (700, 900): "Apprentice",
    (900, 1200): "Specialist",
    (1200, 1500): "Expert",
    (1500, 1800): "Candidate Master",
    (1800, 2100): "Master",
    (2100, 2400): "International Master",
    (2400, 3000): "Grandmaster"
}

def get_rank_title(expertise_rank: int) -> str:
    """Get rank title based on expertise rank."""
    for (min_rank, max_rank), title in RANK_TITLES.items():
        if min_rank <= expertise_rank < max_rank:
            return title
    return "Grandmaster"  # For ranks above 2400


@router.get("/stats", response_model=UserSubmissionStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud)
):
    """Get comprehensive dashboard statistics for the current user."""
    return submission_crud.get_user_submission_stats(current_user.key)


@router.get("/streak")
async def get_user_streak(
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud)
):
    """Get current user's streak information."""
    stats = submission_crud.get_user_submission_stats(current_user.key)
    
    return {
        "current_streak": stats.current_streak,
        "longest_streak": stats.longest_streak,
        "total_active_days": stats.total_active_days,
        "last_submission": stats.last_submission.isoformat() if stats.last_submission else None
    }


@router.get("/contribution-heatmap", response_model=ContributionHeatmapData)
async def get_contribution_heatmap(
    days: int = 365,
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud)
):
    """Get contribution heatmap data for the specified number of days."""
    if days < 1 or days > 730:  # Limit to 2 years maximum
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days parameter must be between 1 and 730"
        )
    
    return submission_crud.get_contribution_heatmap(current_user.key, days)


@router.post("/submit", response_model=Submission)
async def create_submission(
    submission_data: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud)
):
    """Create a new code submission."""
    # Create the submission
    submission = submission_crud.create_submission(current_user.key, submission_data)
    
    # Convert to API model
    return Submission(**submission.model_dump())


@router.get("/submissions", response_model=List[Submission])
async def get_user_submissions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud)
):
    """Get submissions for the current user."""
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
    
    submissions = submission_crud.get_user_submissions(
        current_user.key,
        parsed_start_date,
        parsed_end_date,
        limit=limit,
        offset=offset
    )
    
    # Convert to API models
    return [Submission(**sub.model_dump()) for sub in submissions]


@router.get("/profile-summary")
async def get_profile_summary(
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """Get profile summary for the profile header component."""
    # Get submission stats
    stats = submission_crud.get_user_submission_stats(current_user.key)
    
    # Calculate rankings
    global_rank, country_rank = calculate_user_rankings(current_user.key, user_crud)
    
    return {
        "user": {
            "name": current_user.name,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat()
        },
        "rating": current_user.expertise_rank,
        "rank": get_rank_title(current_user.expertise_rank),
        "max_rating": current_user.peak_rank or current_user.expertise_rank,
        "global_rank": global_rank,
        "country_rank": country_rank,
        "problems_solved": stats.total_problems_solved,
        "acceptance_rate": stats.acceptance_rate
    }


@router.get("/rankings")
async def get_user_rankings(
    current_user: User = Depends(get_current_user),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """Get current user's global and country rankings."""
    global_rank, country_rank = calculate_user_rankings(current_user.key, user_crud)
    
    return {
        "global_rank": global_rank,
        "country_rank": country_rank,
        "total_users": None,  # Could be calculated if needed
        "ranking_last_updated": None  # Could track when rankings were last calculated
    }


def calculate_user_rankings(user_key: str, user_crud: UserCRUD) -> tuple:
    """Calculate global and country rankings for a user."""
    user = user_crud.get_user_by_key(user_key)
    
    if not user:
        return None, None
    
    user_rank = user.expertise_rank
    
    # Calculate global rank
    global_rank_query = """
    FOR u IN users
    FILTER u.expertise_rank > @user_rank
    COLLECT WITH COUNT INTO higher_ranked_count
    RETURN higher_ranked_count
    """
    
    db = get_db()
    cursor = db.aql.execute(global_rank_query, bind_vars={"user_rank": user_rank})
    global_rank = list(cursor)[0] + 1  # +1 because rank is 1-indexed
    
    # For country rank, simplified calculation
    country_rank = max(1, global_rank // 10)
    
    return global_rank, country_rank