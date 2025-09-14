from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.exceptions import RequestValidationError
from arango.database import StandardDatabase
import json

from app.db.database import get_db
from app.crud.assessment import AssessmentCRUD
from app.crud.question import QuestionCRUD
from app.crud.user import UserCRUD
from app.models.assessment import (
    Assessment, AssessmentCreate, AssessmentResult,
    UserAnswerCreate, AssessmentType, RankingCalculationData
)
from app.models.question import DifficultyLevel

router = APIRouter()

def get_assessment_crud(db: StandardDatabase = Depends(get_db)) -> AssessmentCRUD:
    """Get AssessmentCRUD instance."""
    return AssessmentCRUD(db)

def get_question_crud(db: StandardDatabase = Depends(get_db)) -> QuestionCRUD:
    """Get QuestionCRUD instance."""
    return QuestionCRUD(db)

def get_user_crud(db: StandardDatabase = Depends(get_db)) -> UserCRUD:
    """Get UserCRUD instance."""
    return UserCRUD(db)

@router.post("/", response_model=Assessment, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    assessment: AssessmentCreate,
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud)
):
    """Create a new assessment."""
    try:
        db_assessment = assessment_crud.create_assessment(assessment)
        return Assessment.model_validate(db_assessment.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create assessment: {str(e)}"
        )

@router.post("/onboarding/{user_key}", response_model=Assessment)
async def create_onboarding_assessment(
    user_key: str,
    claimed_skill_level: str,  # BEGINNER, INTERMEDIATE, PROFESSIONAL
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud),
    question_crud: QuestionCRUD = Depends(get_question_crud),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """Create an onboarding assessment with appropriate questions. Users can only take ONE onboarding assessment."""
    
    # STRICT CHECK: Verify user exists and hasn't completed onboarding
    user = user_crud.get_user_by_key(user_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already completed onboarding. Only one assessment per user is allowed."
        )
    
    # Check if user already has an existing onboarding assessment (completed or in progress)
    existing_assessments = assessment_crud.get_user_onboarding_assessments(user_key)
    if existing_assessments:
        # If there's a completed assessment, reject
        for assessment in existing_assessments:
            if assessment.status == "COMPLETED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User has already completed an onboarding assessment. Only one assessment per user is allowed."
                )
        
        # If there's an in-progress assessment, return it instead of creating a new one
        in_progress_assessment = next((a for a in existing_assessments if a.status == "IN_PROGRESS"), None)
        if in_progress_assessment:
            # Return the existing in-progress assessment
            assessment_dict = in_progress_assessment.model_dump()
            if 'key' in assessment_dict and '_key' not in assessment_dict:
                assessment_dict['_key'] = assessment_dict['key']
            elif '_key' in assessment_dict and 'key' not in assessment_dict:
                assessment_dict['key'] = assessment_dict['_key']
            return Assessment.model_validate(assessment_dict)
    
    # Map claimed skill level to difficulty
    skill_to_difficulty = {
        "BEGINNER": DifficultyLevel.BEGINNER,
        "INTERMEDIATE": DifficultyLevel.INTERMEDIATE,
        "PROFESSIONAL": DifficultyLevel.ADVANCED
    }
    
    difficulty = skill_to_difficulty.get(claimed_skill_level)
    if not difficulty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid skill level. Must be BEGINNER, INTERMEDIATE, or PROFESSIONAL"
        )
    
    # Get 12 balanced questions for the assessment
    try:
        questions = question_crud.get_balanced_assessment_questions(claimed_skill_level, total_count=12)
        if len(questions) < 12:
            # Fallback to random questions if not enough balanced questions
            questions = question_crud.get_random_assessment_questions(difficulty, count=12)
            if len(questions) < 8:  # Minimum viable assessment
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Not enough questions available for {claimed_skill_level} level"
                )
        
        question_keys = [q.key for q in questions]
        
        # Create assessment
        assessment_create = AssessmentCreate(
            user_key=user_key,
            assessment_type=AssessmentType.ONBOARDING,
            total_questions=len(question_keys),
            question_keys=question_keys
        )
        
        db_assessment = assessment_crud.create_assessment(assessment_create)
        # Create response with proper key field for frontend
        assessment_dict = db_assessment.model_dump()
        # Ensure both key and _key are available for frontend compatibility
        if 'key' in assessment_dict and '_key' not in assessment_dict:
            assessment_dict['_key'] = assessment_dict['key']
        elif '_key' in assessment_dict and 'key' not in assessment_dict:
            assessment_dict['key'] = assessment_dict['_key']
            
        response_data = Assessment.model_validate(assessment_dict)
        return response_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create onboarding assessment: {str(e)}"
        )

@router.get("/{assessment_key}", response_model=Assessment)
async def get_assessment(
    assessment_key: str,
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud)
):
    """Get an assessment by key."""
    assessment = assessment_crud.get_assessment_by_key(assessment_key)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    # Ensure key field compatibility
    assessment_dict = assessment.model_dump()
    if 'key' in assessment_dict and '_key' not in assessment_dict:
        assessment_dict['_key'] = assessment_dict['key']
    elif '_key' in assessment_dict and 'key' not in assessment_dict:
        assessment_dict['key'] = assessment_dict['_key']
    return Assessment.model_validate(assessment_dict)

@router.post("/{assessment_key}/answers", response_model=Assessment)
async def submit_answer(
    assessment_key: str,
    request: Request,
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud),
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Submit an answer for an assessment question."""
    
    try:
        # Parse request body
        raw_body = await request.body()
        body_json = json.loads(raw_body.decode())
        answer = UserAnswerCreate.model_validate(body_json)
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")
    
    # Validate the answer against the question
    question = question_crud.get_question_by_key(answer.question_key)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Calculate if answer is correct and points earned
    is_correct = False
    points_earned = 0
    
    if question.question_type.value == "MULTIPLE_CHOICE":
        correct_key = question.content.get("correct_answer_key")
        submitted_key = answer.answer_data.get("selected_option")
        is_correct = correct_key == submitted_key
        points_earned = question.points if is_correct else 0
        
    elif question.question_type.value == "TRUE_FALSE":
        correct_answer = question.content.get("correct_answer")
        submitted_answer = answer.answer_data.get("selected_answer")
        is_correct = correct_answer == submitted_answer
        points_earned = question.points if is_correct else 0
    
    # Update the answer with calculated values
    answer.is_correct = is_correct
    answer.points_earned = points_earned
    
    # Add answer to assessment
    updated_assessment = assessment_crud.add_user_answer(assessment_key, answer)
    if not updated_assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    # Ensure key field compatibility
    assessment_dict = updated_assessment.model_dump()
    if 'key' in assessment_dict and '_key' not in assessment_dict:
        assessment_dict['_key'] = assessment_dict['key']
    elif '_key' in assessment_dict and 'key' not in assessment_dict:
        assessment_dict['key'] = assessment_dict['_key']
    
    return Assessment.model_validate(assessment_dict)

@router.post("/{assessment_key}/complete", response_model=AssessmentResult)
async def complete_assessment(
    assessment_key: str,
    claimed_skill_level: str,
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """Complete an assessment and calculate final ranking."""
    
    # Get current assessment
    assessment = assessment_crud.get_assessment_by_key(assessment_key)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    # Get user's previous rank
    user = user_crud.get_user_by_key(assessment.user_key)
    previous_rank = user.expertise_rank if user else None
    
    try:
        # Complete assessment with ranking calculation
        completed_assessment = assessment_crud.complete_assessment_with_ranking(
            assessment_key,
            claimed_skill_level,
            previous_rank
        )
        
        if not completed_assessment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete assessment"
            )
        
        # Update user's rank and complete onboarding if this is an onboarding assessment
        if completed_assessment.assessment_type == AssessmentType.ONBOARDING.value and user:
            # Use the already calculated expertise rank from the assessment
            expertise_rank = completed_assessment.calculated_expertise_rank
            
            if expertise_rank:
                # Complete onboarding and update user
                updated_user = user_crud.complete_onboarding(
                    user.key,
                    expertise_rank,
                    claimed_skill_level,
                    {
                        "assessment_key": assessment_key,
                        "completed_at": completed_assessment.completed_at.isoformat() if completed_assessment.completed_at else None,
                        "final_score": completed_assessment.accuracy_percentage,
                        "questions_answered": completed_assessment.questions_answered,
                        "total_points_earned": completed_assessment.total_points_earned,
                        "average_time_per_question": completed_assessment.average_time_per_question
                    }
                )
                
                if updated_user:
                    print(f"✅ User onboarding completed for {user.email}: rank {expertise_rank}")
                else:
                    print(f"❌ Failed to complete onboarding for user {user.key}")
            else:
                print(f"❌ No expertise rank calculated for assessment {assessment_key}")
        
        # Get assessment result
        result = assessment_crud.get_assessment_result(assessment_key)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate assessment result"
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete assessment: {str(e)}"
        )

@router.get("/user/{user_key}", response_model=List[Assessment])
async def get_user_assessments(
    user_key: str,
    limit: int = 10,
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud)
):
    """Get assessments for a specific user."""
    assessments = assessment_crud.get_user_assessments(user_key, limit)
    result = []
    for a in assessments:
        assessment_dict = a.model_dump()
        if 'key' in assessment_dict and '_key' not in assessment_dict:
            assessment_dict['_key'] = assessment_dict['key']
        elif '_key' in assessment_dict and 'key' not in assessment_dict:
            assessment_dict['key'] = assessment_dict['_key']
        result.append(Assessment.model_validate(assessment_dict))
    return result

@router.get("/{assessment_key}/result", response_model=AssessmentResult)
async def get_assessment_result(
    assessment_key: str,
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud)
):
    """Get detailed assessment result."""
    result = assessment_crud.get_assessment_result(assessment_key)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result not found"
        )
    return result

@router.get("/onboarding-status/{user_key}")
async def check_onboarding_status(
    user_key: str,
    user_crud: UserCRUD = Depends(get_user_crud),
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud)
):
    """Check if a user has completed onboarding and can access the assessment."""
    
    user = user_crud.get_user_by_key(user_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check for existing onboarding assessments
    existing_assessments = assessment_crud.get_user_onboarding_assessments(user_key)
    completed_assessment = None
    in_progress_assessment = None
    
    for assessment in existing_assessments:
        if assessment.status == "COMPLETED":
            completed_assessment = assessment
            break
        elif assessment.status == "IN_PROGRESS":
            in_progress_assessment = assessment
    
    return {
        "user_key": user_key,
        "onboarding_completed": user.onboarding_completed,
        "has_completed_assessment": completed_assessment is not None,
        "has_in_progress_assessment": in_progress_assessment is not None,
        "can_take_assessment": not user.onboarding_completed and not completed_assessment,
        "should_redirect_to_dashboard": user.onboarding_completed or completed_assessment is not None,
        "expertise_rank": user.expertise_rank,
        "assessment_data": {
            "completed_assessment_key": completed_assessment.key if completed_assessment else None,
            "in_progress_assessment_key": in_progress_assessment.key if in_progress_assessment else None
        }
    }

@router.post("/calculate-ranking", response_model=RankingCalculationData)
async def calculate_ranking_preview(
    claimed_skill_level: str,
    accuracy_percentage: float,
    average_time_seconds: float,
    assessment_crud: AssessmentCRUD = Depends(get_assessment_crud)
):
    """Preview ranking calculation without creating an assessment."""
    
    # Create a mock assessment for calculation
    from app.models.assessment import AssessmentInDB
    from datetime import datetime
    
    mock_assessment = AssessmentInDB(
        key="preview",
        user_key="preview",
        assessment_type=AssessmentType.ONBOARDING,
        total_questions=12,
        questions_answered=2,
        question_keys=[],
        accuracy_percentage=accuracy_percentage,
        average_time_per_question=average_time_seconds,
        total_points_earned=0,
        total_points_possible=0,
        skill_performance={},
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    
    ranking_data = assessment_crud.calculate_expertise_ranking(
        mock_assessment,
        claimed_skill_level
    )
    
    return ranking_data
