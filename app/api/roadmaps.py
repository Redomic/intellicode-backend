from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional

from app.models.user import User
from app.models.roadmap import RoadmapProgress, RoadmapProgressResponse, RoadmapItem, RoadmapSearchFilters
from app.crud.roadmap import RoadmapCRUD
from app.api.auth import get_current_user
from app.db.database import get_db

router = APIRouter(tags=["Roadmaps"])

def get_roadmap_crud():
    """Dependency to get RoadmapCRUD instance."""
    db = get_db()
    return RoadmapCRUD(db)

@router.get("/progress", response_model=RoadmapProgressResponse)
async def get_user_roadmap_progress(
    current_user: User = Depends(get_current_user),
    roadmap_crud: RoadmapCRUD = Depends(get_roadmap_crud)
):
    """Get user's progress across all roadmaps."""
    try:
        progress_data = roadmap_crud.get_user_roadmap_progress(current_user.key)
        
        return RoadmapProgressResponse(
            roadmaps=progress_data,
            total_roadmaps=len(progress_data)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve roadmap progress: {str(e)}"
        )

@router.get("/{course}/questions", response_model=List[RoadmapItem])
async def get_roadmap_questions(
    course: str,
    current_user: User = Depends(get_current_user),
    roadmap_crud: RoadmapCRUD = Depends(get_roadmap_crud),
    limit: int = Query(default=1000, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Get all questions for a specific roadmap course, ordered by step_number."""
    try:
        # Create filters to get questions for this specific course
        filters = RoadmapSearchFilters()
        
        # Get questions by course using AQL query directly for better performance
        query = """
        FOR r IN roadmap
        FILTER r.course == @course
        SORT r.step_number ASC
        LIMIT @offset, @limit
        RETURN r
        """
        
        db = get_db()
        cursor = db.aql.execute(query, bind_vars={
            'course': course,
            'offset': offset,
            'limit': limit
        })
        
        roadmap_questions = []
        for roadmap_data in cursor:
            roadmap_data = roadmap_data.copy()
            
            # Convert datetime strings if needed
            from datetime import datetime
            if 'created_at' in roadmap_data and isinstance(roadmap_data['created_at'], str):
                roadmap_data['created_at'] = datetime.fromisoformat(roadmap_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in roadmap_data and isinstance(roadmap_data['updated_at'], str):
                roadmap_data['updated_at'] = datetime.fromisoformat(roadmap_data['updated_at'].replace('Z', '+00:00'))
            if 'scraped_at' in roadmap_data and isinstance(roadmap_data['scraped_at'], str):
                roadmap_data['scraped_at'] = datetime.fromisoformat(roadmap_data['scraped_at'].replace('Z', '+00:00'))
            
            roadmap_questions.append(RoadmapItem(**roadmap_data))
        
        return roadmap_questions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve roadmap questions: {str(e)}"
        )
