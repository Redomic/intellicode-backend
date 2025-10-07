from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from arango.database import StandardDatabase

from ..db.database import get_db
from ..api.auth import get_current_user
from ..models.user import User
from ..models.session import (
    CodingSession,
    CodingSessionCreate,
    CodingSessionUpdate,
    SessionResponse,
    SessionRecoveryResponse,
    SessionListResponse,
    SessionEventCreate,
    SessionCodeSnapshot,
    SessionCodeUpdate,
    SessionLastRunUpdate,
    SessionState,
    SessionType
)
from ..crud.session import SessionCRUD

router = APIRouter(tags=["sessions"])


def get_session_crud() -> SessionCRUD:
    """Dependency to get SessionCRUD instance."""
    db = get_db()
    return SessionCRUD(db)


@router.post("/start", response_model=SessionResponse)
async def start_session(
    session_data: CodingSessionCreate,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Start a new coding session."""
    try:
        print(f"📊 === SESSION START ENDPOINT CALLED ===")
        print(f"👤 User: {current_user.key}")
        print(f"📋 Session data received: {session_data.dict()}")
        print(f"🏷️  Session type: {session_data.session_type}")
        
        # Get question info for targeted cleanup
        question_id = session_data.questionId or session_data.question_id
        question_title = session_data.questionTitle or session_data.question_title
        
        # Only clean up active sessions for THE SAME QUESTION
        # This allows multiple sessions for different questions while preventing duplicates
        print(f"🧹 Checking for existing active sessions for this question...")
        
        cleanup_aql = """
            FOR session IN sessions
                FILTER session.user_key == @user_key
                AND session.state == "active"
                AND (session.question_id == @question_id OR session.question_title == @question_title)
                RETURN session
        """
        
        cleanup_cursor = session_crud.db.aql.execute(
            cleanup_aql,
            bind_vars={
                "user_key": current_user.key,
                "question_id": question_id,
                "question_title": question_title
            }
        )
        sessions_to_end = list(cleanup_cursor)
        
        if sessions_to_end:
            print(f"🔄 Found {len(sessions_to_end)} active session(s) for this question")
            for old_session in sessions_to_end:
                print(f"   🛑 Ending duplicate session: {old_session['session_id']}")
                session_crud.end_session(old_session['session_id'], "new_session_started")
            print(f"✅ Cleaned up {len(sessions_to_end)} duplicate session(s)")
        else:
            print(f"✅ No existing active session for this question - starting fresh")
        
        # Create new session
        session = session_crud.create_session(current_user.key, session_data)
        print(f"✅ Session created successfully: {session.session_id}")
        
        # Verify the session was actually saved by trying to retrieve it
        verification = session_crud.get_session(session.session_id)
        if not verification:
            print(f"❌ ERROR: Session not found immediately after creation: {session.session_id}")
            raise Exception("Session creation verification failed")
        else:
            print(f"✅ Session verification successful: {verification.session_id}")
        
        return SessionResponse(
            session_id=session.session_id,
            state=session.state,
            message="Session started successfully"
        )
        
    except Exception as e:
        print(f"❌ Failed to start session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}"
        )


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: str,
    reason: Optional[str] = "user_request",
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """End a session."""
    try:
        # Get session and verify ownership
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        if session.state == SessionState.ABANDONED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session already ended with state: {session.state}"
            )
        
        success = session_crud.end_session(session_id, reason or "user_request")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to end session"
            )
        
        return SessionResponse(
            session_id=session_id,
            state=SessionState.ABANDONED,
            message="Session ended successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )


@router.get("/{session_id}", response_model=CodingSession)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Get session details."""
    try:
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Convert to API model
        return CodingSession(**session.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.get("/", response_model=SessionListResponse)
async def list_user_sessions(
    limit: int = 10,
    include_active: bool = True,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """List user's recent sessions."""
    try:
        sessions = session_crud.get_user_sessions(
            current_user.key, 
            limit=limit, 
            include_active=include_active
        )
        
        # Convert to API models
        api_sessions = [CodingSession(**session.dict()) for session in sessions]
        
        # Check for active session
        active_session = session_crud.get_user_active_session(current_user.key)
        has_active = active_session is not None
        active_session_id = active_session.session_id if active_session else None
        
        return SessionListResponse(
            sessions=api_sessions,
            total=len(api_sessions),
            has_active_session=has_active,
            active_session_id=active_session_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/active/current", response_model=Optional[CodingSession])
async def get_active_session(
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Get user's current active session."""
    try:
        session = session_crud.get_user_active_session(current_user.key)
        if not session:
            return None
        
        return CodingSession(**session.dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active session: {str(e)}"
        )


@router.get("/active/by-question", response_model=Optional[CodingSession])
async def get_active_session_by_question(
    question_id: Optional[str] = None,
    question_title: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Get user's active session for a specific question."""
    try:
        if not question_id and not question_title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either question_id or question_title must be provided"
            )
        
        session = session_crud.get_user_active_session_by_question(
            current_user.key, 
            question_id=question_id,
            question_title=question_title
        )
        
        if not session:
            return None
        
        return CodingSession(**session.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active session by question: {str(e)}"
        )


@router.post("/{session_id}/events", response_model=dict)
async def add_session_event(
    session_id: str,
    event: SessionEventCreate,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Add an event to a session."""
    try:
        # Verify session ownership
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = session_crud.add_session_event(
            session_id, 
            event.event_type, 
            event.data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add session event"
            )
        
        return {"message": "Event added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add session event: {str(e)}"
        )


@router.post("/{session_id}/code-snapshot", response_model=dict)
async def add_code_snapshot(
    session_id: str,
    snapshot: SessionCodeSnapshot,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Add a code snapshot to a session."""
    try:
        # Verify session ownership
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = session_crud.add_code_snapshot(
            session_id,
            snapshot.code,
            snapshot.language,
            getattr(snapshot, 'is_current', False)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add code snapshot"
            )
        
        return {"message": "Code snapshot added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add code snapshot: {str(e)}"
        )


@router.post("/{session_id}/current-code", response_model=dict)
async def update_current_code(
    session_id: str,
    code_update: SessionCodeUpdate,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Update the current code state for a session."""
    try:
        # Verify session ownership
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = session_crud.update_current_code(
            session_id,
            code_update.code,
            code_update.language
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update current code"
            )
        
        return {"message": "Current code updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update current code: {str(e)}"
        )


@router.post("/{session_id}/last-run", response_model=dict)
async def update_last_run(
    session_id: str,
    run_data: SessionLastRunUpdate,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Update the last run state for a session (Run button, not submission)."""
    try:
        # Verify session ownership
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = session_crud.update_last_run(
            session_id=session_id,
            code=run_data.code,
            language=run_data.language,
            status=run_data.status,
            passed_count=run_data.passed_count,
            total_count=run_data.total_count,
            runtime_ms=run_data.runtime_ms,
            error_message=run_data.error_message,
            test_results=run_data.test_results
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update last run state"
            )
        
        return {"message": "Last run state updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update last run state: {str(e)}"
        )


@router.get("/{session_id}/current-code", response_model=dict)
async def get_current_code(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Get the current code state for a session."""
    try:
        # Verify session ownership
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        current_code = session_crud.get_current_code(session_id)
        
        return {
            "code": current_code.get("code", "") if current_code else "",
            "language": current_code.get("language", "python") if current_code else "python",
            "timestamp": current_code.get("timestamp") if current_code else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current code: {str(e)}"
        )


@router.get("/{session_id}/recovery", response_model=SessionRecoveryResponse)
async def get_session_recovery_data(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Get session recovery data including current code state."""
    try:
        # Verify session ownership
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Do not allow recovery of abandoned sessions
        if session.state == SessionState.ABANDONED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot recover abandoned session"
            )
        
        session_data = session_crud.get_session_with_code(session_id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session recovery data not found"
            )
        
        return SessionRecoveryResponse(
            session=CodingSession(**session_data["session"].dict()),
            current_code=session_data["current_code"],
            language=session_data["language"],
            last_activity=session_data["session"].last_activity
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session recovery data: {str(e)}"
        )


@router.post("/debug/test-create", response_model=dict)
async def debug_test_session_creation(
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Debug endpoint to test session creation."""
    try:
        print(f"🧪 === DEBUG: Testing session creation ===")
        
        # Create a simple test session
        from datetime import datetime
        test_session_data = CodingSessionCreate(
            session_id=f"debug_test_{int(datetime.now().timestamp())}",
            session_type=SessionType.PRACTICE,
            question_id="debug_question",
            question_title="Debug Test Question",
            programming_language="python",
            config={"test": True}
        )
        
        print(f"🧪 Test session data: {test_session_data.dict()}")
        
        # Try to create it
        session = session_crud.create_session(current_user.key, test_session_data)
        
        print(f"🧪 Test session created: {session.session_id}")
        
        # Count total sessions
        all_cursor = session_crud.sessions_collection.all()
        total_count = len(list(all_cursor))
        print(f"🧪 Total sessions after test: {total_count}")
        
        return {
            "message": "Test session created successfully",
            "session_id": session.session_id,
            "total_sessions_in_db": total_count
        }
        
    except Exception as e:
        print(f"🧪 Debug test failed: {e}")
        return {
            "error": str(e),
            "message": "Test session creation failed"
        }


@router.post("/cleanup-expired", response_model=dict)
async def cleanup_expired_sessions(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """Cleanup expired sessions (admin function)."""
    try:
        # For now, allow any authenticated user to trigger cleanup
        # In production, you might want to restrict this to admin users
        
        def cleanup_task():
            expired_count = session_crud.cleanup_expired_sessions()
            print(f"Cleaned up {expired_count} expired sessions")
        
        background_tasks.add_task(cleanup_task)
        
        return {"message": "Cleanup task scheduled"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule cleanup: {str(e)}"
        )
