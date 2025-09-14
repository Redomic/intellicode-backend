from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from arango.database import StandardDatabase

from app.db.database import get_db
from app.crud.question import QuestionCRUD
from app.models.question import (
    Question, QuestionCreate, QuestionUpdate,
    DifficultyLevel, QuestionType, SkillCategory
)

router = APIRouter()

def get_question_crud(db: StandardDatabase = Depends(get_db)) -> QuestionCRUD:
    """Get QuestionCRUD instance."""
    return QuestionCRUD(db)

@router.post("/", response_model=Question, status_code=status.HTTP_201_CREATED)
async def create_question(
    question: QuestionCreate,
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Create a new question."""
    try:
        db_question = question_crud.create_question(question)
        return Question.model_validate(db_question.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create question: {str(e)}"
        )

@router.get("/{question_key}", response_model=Question)
async def get_question(
    question_key: str,
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Get a question by key."""
    question = question_crud.get_question_by_key(question_key)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    return Question.model_validate(question.model_dump())

@router.get("/", response_model=List[Question])
async def get_questions(
    difficulty: Optional[DifficultyLevel] = None,
    question_type: Optional[QuestionType] = None,
    skill_categories: Optional[str] = None,  # Comma-separated skill categories
    limit: int = 10,
    offset: int = 0,
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Get questions with optional filtering."""
    
    # Parse skill categories if provided
    parsed_skill_categories = None
    if skill_categories:
        try:
            category_names = [cat.strip().upper() for cat in skill_categories.split(',')]
            parsed_skill_categories = [SkillCategory(cat) for cat in category_names if cat in SkillCategory._value2member_map_]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid skill category provided"
            )
    
    questions = question_crud.get_questions_by_criteria(
        difficulty=difficulty,
        question_type=question_type,
        skill_categories=parsed_skill_categories,
        limit=limit,
        offset=offset
    )
    
    return [Question.model_validate(q.model_dump()) for q in questions]

@router.get("/assessment/{difficulty}", response_model=List[Question])
async def get_assessment_questions(
    difficulty: DifficultyLevel,
    count: int = 12,
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Get random questions for assessment based on difficulty level."""
    if count > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot request more than 20 questions at once"
        )
    
    questions = question_crud.get_random_assessment_questions(difficulty, count)
    
    if len(questions) < count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not enough questions available for {difficulty.value} difficulty. Found {len(questions)}, requested {count}"
        )
    
    return [Question.model_validate(q.model_dump()) for q in questions]

@router.put("/{question_key}", response_model=Question)
async def update_question(
    question_key: str,
    question_update: QuestionUpdate,
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Update a question."""
    updated_question = question_crud.update_question(question_key, question_update)
    if not updated_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    return Question.model_validate(updated_question.model_dump())

@router.delete("/{question_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_key: str,
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Delete a question."""
    success = question_crud.delete_question(question_key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

@router.get("/stats/count")
async def get_questions_count(
    question_crud: QuestionCRUD = Depends(get_question_crud)
):
    """Get total number of questions."""
    count = question_crud.get_questions_count()
    return {"total_questions": count}
