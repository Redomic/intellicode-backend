"""
Submissions API - Handle code submissions and execution.

Provides LeetCode-style code submission endpoints:
- Submit code for evaluation
- Run code with custom test cases
- Get submission history
- Get submission details
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.models.user import User
from app.models.submission import (
    SubmissionCreate, Submission, SubmissionStatus, SubmissionInDB
)
from app.crud.submission import SubmissionCRUD
from app.crud.session import SessionCRUD
from app.crud.learner_state import LearnerStateCRUD
from app.crud.user import UserCRUD
from app.api.auth import get_current_user
from app.db.database import get_db
from app.services.code_executor import execute_code, ExecutionStatus
from app.services.learner_state_service import create_learner_state_service


router = APIRouter(tags=["Submissions"])


def get_submission_crud():
    """Dependency to get SubmissionCRUD instance."""
    db = get_db()
    return SubmissionCRUD(db)


def get_session_crud():
    """Dependency to get SessionCRUD instance."""
    db = get_db()
    return SessionCRUD(db)


def get_learner_state_crud():
    """Dependency to get LearnerStateCRUD instance."""
    db = get_db()
    return LearnerStateCRUD(db)


def get_user_crud():
    """Dependency to get UserCRUD instance."""
    db = get_db()
    return UserCRUD(db)


class RunCodeRequest(BaseModel):
    """Request model for running code with custom test cases."""
    code: str
    language: str = "python"
    test_cases: List[Dict[str, Any]]
    question_id: Optional[str] = None


class SubmitCodeRequest(BaseModel):
    """Request model for submitting code for evaluation."""
    code: str
    language: str = "python"
    question_key: str
    question_title: str
    test_cases: List[Dict[str, Any]]
    session_id: Optional[str] = None
    roadmap_id: Optional[str] = None
    difficulty: Optional[str] = None
    function_name: Optional[str] = None


class RunCodeResponse(BaseModel):
    """Response model for code execution."""
    success: bool
    status: str
    passed_count: int
    total_count: int
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    test_results: List[Dict[str, Any]] = []
    error_message: Optional[str] = None


class SubmitCodeResponse(BaseModel):
    """Response model for code submission."""
    success: bool
    status: str
    submission_id: str
    passed_count: int
    total_count: int
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    runtime_percentile: Optional[float] = None
    memory_percentile: Optional[float] = None
    points_earned: int = 0
    error_message: Optional[str] = None
    failed_test_case_index: Optional[int] = None
    test_results: Optional[List[Dict[str, Any]]] = None


@router.post("/run", response_model=RunCodeResponse)
async def run_code(
    request: RunCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Run code with custom test cases without creating a submission.
    Used for testing code before final submission.
    """
    try:
        # Execute the code
        result = execute_code(
            code=request.code,
            language=request.language,
            test_cases=request.test_cases
        )
        
        # Convert test results to dict format
        test_results_dict = [
            {
                "input": tr.input,
                "expected_output": tr.expected_output,
                "actual_output": tr.actual_output,
                "passed": tr.passed,
                "runtime_ms": tr.runtime_ms,
                "error": tr.error
            }
            for tr in result.test_results
        ]
        
        return RunCodeResponse(
            success=result.status == ExecutionStatus.ACCEPTED,
            status=result.status.value,
            passed_count=result.passed_count,
            total_count=result.total_count,
            runtime_ms=result.runtime_ms,
            memory_kb=result.memory_kb,
            test_results=test_results_dict,
            error_message=result.error_message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code execution failed: {str(e)}"
        )


@router.post("/submit", response_model=SubmitCodeResponse)
async def submit_code(
    request: SubmitCodeRequest,
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud),
    session_crud: SessionCRUD = Depends(get_session_crud),
    learner_crud: LearnerStateCRUD = Depends(get_learner_state_crud),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """
    Submit code for full evaluation and create a submission record.
    Runs all test cases and stores the result.
    """
    try:
        # Execute the code with all test cases
        result = execute_code(
            code=request.code,
            language=request.language,
            test_cases=request.test_cases,
            function_name=request.function_name
        )
        
        # Map execution status to submission status
        status_map = {
            ExecutionStatus.ACCEPTED: SubmissionStatus.ACCEPTED,
            ExecutionStatus.WRONG_ANSWER: SubmissionStatus.WRONG_ANSWER,
            ExecutionStatus.RUNTIME_ERROR: SubmissionStatus.RUNTIME_ERROR,
            ExecutionStatus.TIME_LIMIT_EXCEEDED: SubmissionStatus.TIME_LIMIT_EXCEEDED,
            ExecutionStatus.MEMORY_LIMIT_EXCEEDED: SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
            ExecutionStatus.COMPILE_ERROR: SubmissionStatus.COMPILE_ERROR
        }
        
        submission_status = status_map.get(result.status, SubmissionStatus.RUNTIME_ERROR)
        
        # Points system disabled for now
        points_earned = 0
        
        # Calculate percentiles (mock for now - can be enhanced with historical data)
        runtime_percentile = None
        memory_percentile = None
        if submission_status == SubmissionStatus.ACCEPTED and result.runtime_ms:
            # Mock percentile calculation
            runtime_percentile = min(95.0, 70.0 + (100 - result.runtime_ms / 100))
            memory_percentile = 85.0  # Mock value
        
        # Create submission record
        submission_data = SubmissionCreate(
            question_key=request.question_key,
            question_title=request.question_title,
            code=request.code,
            language=request.language,
            status=submission_status,
            runtime_ms=result.runtime_ms,
            memory_kb=result.memory_kb,
            total_test_cases=result.total_count,
            passed_test_cases=result.passed_count,
            failed_test_case_index=result.failed_test_case_index,
            error_message=result.error_message,
            runtime_percentile=runtime_percentile,
            memory_percentile=memory_percentile,
            session_id=request.session_id,
            roadmap_id=request.roadmap_id,
            difficulty=request.difficulty,
            points_earned=points_earned
        )
        
        # Save submission
        submission = submission_crud.create_submission(current_user.key, submission_data)
        
        # Update session analytics if session_id provided
        if request.session_id:
            try:
                session_crud.add_session_event(
                    session_id=request.session_id,
                    event_type="CODE_SUBMITTED",
                    data={
                        "submission_id": submission.key,
                        "status": submission_status.value,
                        "passed_count": result.passed_count,
                        "total_count": result.total_count,
                        "points_earned": points_earned
                    }
                )
                
                # Update session analytics
                session_crud.increment_tests_run(request.session_id)
                
            except Exception as e:
                print(f"Warning: Failed to update session analytics: {e}")
        
        # Update learner state (ITS integration)
        try:
            learner_service = create_learner_state_service(learner_crud, user_crud)
            
            # Get topics from the question
            topics = learner_service.get_topics_from_question(request.question_key)
            
            # Update learner state based on submission
            await learner_service.update_on_submission(
                user=current_user,
                question_key=request.question_key,
                submission_status=submission_status,
                topics=topics,
                hints_used=0  # TODO: Track hints if available
            )
            
            print(f"✅ Learner state updated for user {current_user.key}")
            
        except Exception as e:
            # Don't fail the submission if learner state update fails
            print(f"⚠️ Warning: Failed to update learner state: {e}")
            import traceback
            traceback.print_exc()
        
        # Convert test results for response
        test_results_dict = None
        if result.status != ExecutionStatus.ACCEPTED:
            # Only include test results if submission failed (for debugging)
            test_results_dict = [
                {
                    "input": tr.input,
                    "expected_output": tr.expected_output,
                    "actual_output": tr.actual_output,
                    "passed": tr.passed,
                    "error": tr.error
                }
                for tr in result.test_results[:3]  # Only show first 3 failed cases
            ]
        
        return SubmitCodeResponse(
            success=submission_status == SubmissionStatus.ACCEPTED,
            status=submission_status.value,
            submission_id=submission.key,
            passed_count=result.passed_count,
            total_count=result.total_count,
            runtime_ms=result.runtime_ms,
            memory_kb=result.memory_kb,
            runtime_percentile=runtime_percentile,
            memory_percentile=memory_percentile,
            points_earned=points_earned,
            error_message=result.error_message,
            failed_test_case_index=result.failed_test_case_index,
            test_results=test_results_dict
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Submission failed: {str(e)}"
        )


@router.get("/history", response_model=List[Submission])
async def get_submission_history(
    question_key: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud)
):
    """Get user's submission history, optionally filtered by question_key."""
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )
    
    # Fetch submissions with database-level filtering for efficiency
    submissions = submission_crud.get_user_submissions(
        user_key=current_user.key,
        question_key=question_key,  # Filter at database level
        limit=limit,
        offset=offset
    )
    
    return [Submission(**sub.model_dump()) for sub in submissions]


@router.get("/{submission_id}", response_model=Submission)
async def get_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    submission_crud: SubmissionCRUD = Depends(get_submission_crud)
):
    """Get a specific submission by ID."""
    submission = submission_crud.get_submission(submission_id)
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Verify ownership
    if submission.user_key != current_user.key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this submission"
        )
    
    return Submission(**submission.model_dump())
