"""
Submissions API - Handle code submissions and execution.

Provides LeetCode-style code submission endpoints:
- Submit code for evaluation
- Run code with custom test cases
- Get submission history
- Get submission details
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import asyncio

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
from app.agents.orchestrator import get_orchestrator


router = APIRouter(tags=["Submissions"])


# ============================================================================
# BACKGROUND TASK: Code Analysis
# ============================================================================

async def run_code_analysis_background(
    user_key: str,
    question_id: str,
    code: str,
    problem_statement: str,
    test_results: List[Dict[str, Any]],
    language: str
):
    """
    Background task to run code analysis after code execution completes.
    Stores result in user's agent_data for later retrieval.
    """
    try:
        print(f"🔍 Starting background code analysis for user {user_key}, question {question_id}")
        
        # Get orchestrator
        orchestrator = get_orchestrator()
        
        # Prepare context for code analysis
        context = {
            "code": code,
            "problem_statement": problem_statement,
            "test_results": test_results,
            "language": language,
            "question_id": question_id
        }
        
        # Invoke code analysis workflow
        workflow_result = await orchestrator.ainvoke(
            user_key=user_key,
            trigger="code_analysis",
            context=context
        )
        
        # Extract and store code analysis
        if workflow_result and "agent_outputs" in workflow_result:
            code_analysis = workflow_result["agent_outputs"].get("code_analysis")
            if code_analysis and code_analysis.get("success"):
                # Store in user's agent_data under a specific key
                db = get_db()
                user_crud = UserCRUD(db)
                
                # Get current agent_data
                user = user_crud.get_user_by_key(user_key)
                agent_data = user.agent_data or {}
                
                # Store latest analysis with timestamp
                if "code_analyses" not in agent_data:
                    agent_data["code_analyses"] = {}
                
                agent_data["code_analyses"][question_id] = {
                    "analysis_text": code_analysis.get("analysis_text", ""),
                    "suggestion_count": code_analysis.get("suggestion_count", 0),
                    "proficiency_level": code_analysis.get("proficiency_level", "Intermediate"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "language": language
                }
                
                # Update user
                user_crud.update_user_fields(user_key, {"agent_data": agent_data})
                
                print(f"✅ Code analysis completed and stored for user {user_key}, question {question_id}")
            else:
                print(f"⚠️ Code analysis returned unsuccessful: {code_analysis.get('error', 'Unknown error')}")
        else:
            print(f"⚠️ No agent outputs in workflow result")
            
    except Exception as e:
        print(f"❌ Background code analysis failed: {e}")
        import traceback
        traceback.print_exc()


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
    question_title: Optional[str] = None
    problem_statement: Optional[str] = None


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
    analysis_pending: bool = False  # New: indicates if analysis is running in background


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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Run code with custom test cases without creating a submission.
    Used for testing code before final submission.
    
    Returns execution results immediately. If all tests pass, triggers 
    code analysis in the background. Frontend can poll /submissions/analysis/{question_id}
    to get the optimization suggestions.
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
        
        # Trigger code analysis in background if all tests passed
        analysis_pending = False
        if result.status == ExecutionStatus.ACCEPTED and request.problem_statement and request.question_id:
            # Add background task - runs AFTER response is sent
            background_tasks.add_task(
                run_code_analysis_background,
                user_key=current_user.key,
                question_id=request.question_id,
                code=request.code,
                problem_statement=request.problem_statement,
                test_results=test_results_dict,
                language=request.language
            )
            analysis_pending = True
            print(f"✅ Code analysis scheduled in background for user {current_user.key}")
        
        # Return results immediately (without waiting for analysis)
        return RunCodeResponse(
            success=result.status == ExecutionStatus.ACCEPTED,
            status=result.status.value,
            passed_count=result.passed_count,
            total_count=result.total_count,
            runtime_ms=result.runtime_ms,
            memory_kb=result.memory_kb,
            test_results=test_results_dict,
            error_message=result.error_message,
            analysis_pending=analysis_pending
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


@router.get("/analysis/{question_id}")
async def get_code_analysis(
    question_id: str,
    current_user: User = Depends(get_current_user),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """
    Get the latest code analysis for a specific question.
    
    Returns the optimization suggestions generated by the Code Analysis Agent
    after the user's code passed all tests.
    """
    try:
        # Get user's agent_data
        user = user_crud.get_user_by_key(current_user.key)
        
        if not user or not user.agent_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analysis data available"
            )
        
        # Extract code analysis for this question
        code_analyses = user.agent_data.get("code_analyses", {})
        
        if question_id not in code_analyses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analysis available for this question yet. It may still be processing."
            )
        
        analysis = code_analyses[question_id]
        
        return {
            "success": True,
            "analysis": analysis,
            "question_id": question_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch code analysis: {str(e)}"
        )
