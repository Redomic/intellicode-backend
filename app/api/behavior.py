from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from datetime import datetime
from typing import List, Optional

from app.models.user import User
from app.models.behavior import (
    KeystrokeEvent, TypingSession, BehaviorEvent,
    LiveBehaviorMetrics, BehaviorSessionSummary
)
from app.schemas.behavior import (
    KeystrokeEventRequest, BehaviorEventRequest,
    StartSessionRequest, EndSessionRequest, BatchKeystrokeRequest,
    StartSessionResponse, LiveMetricsResponse, SessionAnalyticsResponse,
    BehaviorInsightsResponse, PrivacyControlsRequest, PrivacyControlsResponse
)
from app.crud.behavior import BehaviorCRUD
from app.api.auth import get_current_user
from app.db.database import get_db

router = APIRouter(tags=["Behavior Tracking"])

def get_behavior_crud():
    """Dependency to get BehaviorCRUD instance."""
    db = get_db()
    return BehaviorCRUD(db)

@router.post("/session/start", response_model=StartSessionResponse)
async def start_tracking_session(
    request: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Start a new behavior tracking session."""
    try:
        session_id = behavior_crud.create_session(
            user_key=current_user.key,
            question_key=request.question_key
        )
        
        return StartSessionResponse(
            session_id=session_id,
            start_time=datetime.utcnow(),
            tracking_enabled=True,
            privacy_mode=False  # TODO: Get from user preferences
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start tracking session: {str(e)}"
        )

@router.post("/session/{session_id}/end")
async def end_tracking_session(
    session_id: str,
    request: EndSessionRequest,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """End a behavior tracking session."""
    try:
        session = behavior_crud.end_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify session belongs to current user
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return {"message": "Session ended successfully", "session_id": session_id}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )

@router.post("/keystroke")
async def add_keystroke_event(
    event: KeystrokeEventRequest,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Add a single keystroke event."""
    try:
        from app.models.behavior import KeystrokeEventCreate
        
        keystroke_event = KeystrokeEventCreate(
            user_key=current_user.key,
            session_id=event.session_id,
            question_key=event.question_key,
            timestamp=event.timestamp,
            key_pressed=event.key_pressed,
            key_code=event.key_code,
            is_printable=event.is_printable,
            cursor_position=event.cursor_position,
            text_length=event.text_length
        )
        
        created_event = behavior_crud.add_keystroke_event(keystroke_event)
        return {"message": "Keystroke event added", "event_id": created_event.key}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add keystroke event: {str(e)}"
        )

@router.post("/keystroke/batch")
async def add_keystroke_events_batch(
    request: BatchKeystrokeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Add multiple keystroke events in batch for better performance."""
    try:
        from app.models.behavior import KeystrokeEventCreate
        
        events = []
        for event_data in request.events:
            keystroke_event = KeystrokeEventCreate(
                user_key=current_user.key,
                session_id=request.session_id,
                question_key=event_data.question_key,
                timestamp=event_data.timestamp,
                key_pressed=event_data.key_pressed,
                key_code=event_data.key_code,
                is_printable=event_data.is_printable,
                cursor_position=event_data.cursor_position,
                text_length=event_data.text_length
            )
            events.append(keystroke_event)
        
        # Process in background for better response time
        background_tasks.add_task(
            behavior_crud.add_keystroke_events_batch,
            events
        )
        
        return {
            "message": f"Batch of {len(events)} keystroke events queued for processing",
            "session_id": request.session_id
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add keystroke events batch: {str(e)}"
        )

@router.get("/session/{session_id}/live", response_model=LiveMetricsResponse)
async def get_live_metrics(
    session_id: str,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Get real-time behavior metrics for a session."""
    try:
        # Verify session belongs to current user
        session = behavior_crud.get_session(session_id)
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
        
        metrics = behavior_crud.get_live_metrics(session_id)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metrics available for this session"
            )
        
        return LiveMetricsResponse(
            session_id=metrics.session_id,
            typing_speed_cpm=metrics.current_typing_speed_cpm,
            typing_speed_wpm=metrics.current_typing_speed_wpm,
            recent_pauses=metrics.recent_pause_count,
            productivity_level=metrics.productivity_indicator,
            flow_state=metrics.is_in_flow_state,
            suggestion=metrics.suggestion
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live metrics: {str(e)}"
        )

@router.get("/session/{session_id}/analytics", response_model=SessionAnalyticsResponse)
async def get_session_analytics(
    session_id: str,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Get comprehensive analytics for a completed session."""
    try:
        session = behavior_crud.get_session(session_id)
        
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
        
        # Calculate duration
        duration_minutes = 0.0
        if session.end_time:
            duration = session.end_time - session.start_time
            duration_minutes = duration.total_seconds() / 60
        
        return SessionAnalyticsResponse(
            session_id=session_id,
            duration_minutes=duration_minutes,
            total_keystrokes=session.total_keystrokes,
            productive_keystrokes=session.productive_keystrokes,
            average_typing_speed_cpm=session.typing_speed_cpm,
            average_typing_speed_wpm=session.typing_speed_wpm,
            peak_typing_speed_cpm=session.typing_speed_cpm * 1.3,  # Estimate
            total_pauses=session.total_pauses,
            average_pause_duration=session.average_pause_duration,
            longest_pause_duration=session.longest_pause_duration,
            total_bursts=session.total_bursts,
            average_burst_length=session.average_burst_length,
            longest_burst_length=session.longest_burst_length,
            correction_ratio=session.correction_ratio,
            productivity_score=session.productivity_score or 0.0,
            rhythm_consistency=session.rhythm_consistency
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session analytics: {str(e)}"
        )

@router.get("/sessions/recent")
async def get_recent_sessions(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Get recent typing sessions for the current user."""
    try:
        sessions = behavior_crud.get_user_sessions(current_user.key, limit)
        
        return {
            "sessions": [
                {
                    "session_id": session.session_id,
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "question_key": session.question_key,
                    "typing_speed_cpm": session.typing_speed_cpm,
                    "productivity_score": session.productivity_score,
                    "total_keystrokes": session.total_keystrokes
                }
                for session in sessions
            ]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent sessions: {str(e)}"
        )

@router.post("/behavior/event")
async def add_behavior_event(
    event: BehaviorEventRequest,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Add a general behavior event (for future metrics)."""
    try:
        from app.models.behavior import BehaviorEventCreate, BehaviorEventType
        
        # Validate event type
        try:
            event_type = BehaviorEventType(event.event_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event.event_type}"
            )
        
        behavior_event = BehaviorEventCreate(
            user_key=current_user.key,
            session_id=event.session_id,
            question_key=event.question_key,
            event_type=event_type,
            timestamp=event.timestamp,
            duration=event.duration,
            metadata=event.metadata
        )
        
        # For now, we'll just acknowledge the event
        # In the future, this will be stored and analyzed
        return {"message": "Behavior event received", "event_type": event.event_type}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add behavior event: {str(e)}"
        )

@router.get("/insights")
async def get_behavior_insights(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    behavior_crud: BehaviorCRUD = Depends(get_behavior_crud)
):
    """Get behavior insights for the current user."""
    try:
        # Get recent sessions for analysis
        sessions = behavior_crud.get_user_sessions(current_user.key, limit=50)
        
        if not sessions:
            return BehaviorInsightsResponse(
                user_key=current_user.key,
                analysis_period=f"last_{days}_days",
                average_typing_speed_cpm=0.0,
                typing_consistency_score=0.0,
                productivity_score=0.0,
                improvement_trend="stable",
                confidence_level=0.0,
                peak_performance_hours=[],
                common_struggle_areas=[],
                strengths=[],
                personalized_tips=["Start coding to generate insights!"],
                next_focus_areas=["Begin your first coding session"]
            )
        
        # Calculate aggregate metrics
        total_speed = sum(s.typing_speed_cpm for s in sessions)
        avg_speed = total_speed / len(sessions) if sessions else 0.0
        
        total_consistency = sum(s.rhythm_consistency or 0 for s in sessions)
        avg_consistency = total_consistency / len(sessions) if sessions else 0.0
        
        total_productivity = sum(s.productivity_score or 0 for s in sessions)
        avg_productivity = total_productivity / len(sessions) if sessions else 0.0
        
        # Determine improvement trend (simplified)
        if len(sessions) >= 3:
            recent_avg = sum(s.productivity_score or 0 for s in sessions[:3]) / 3
            older_avg = sum(s.productivity_score or 0 for s in sessions[-3:]) / 3
            
            if recent_avg > older_avg * 1.1:
                trend = "improving"
            elif recent_avg < older_avg * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Generate insights
        strengths = []
        struggle_areas = []
        tips = []
        
        if avg_speed > 50:
            strengths.append("Fast typing speed")
        elif avg_speed < 30:
            struggle_areas.append("Typing speed")
            tips.append("Practice typing exercises to improve speed")
        
        if avg_consistency > 70:
            strengths.append("Consistent typing rhythm")
        elif avg_consistency < 50:
            struggle_areas.append("Typing consistency")
            tips.append("Focus on maintaining steady typing rhythm")
        
        if avg_productivity > 70:
            strengths.append("High productivity")
        elif avg_productivity < 50:
            struggle_areas.append("Coding productivity")
            tips.append("Break down problems into smaller steps")
        
        if not tips:
            tips.append("Keep up the great work!")
        
        return BehaviorInsightsResponse(
            user_key=current_user.key,
            analysis_period=f"last_{days}_days",
            average_typing_speed_cpm=avg_speed,
            typing_consistency_score=avg_consistency,
            productivity_score=avg_productivity,
            improvement_trend=trend,
            confidence_level=min(100, len(sessions) * 10),  # More sessions = higher confidence
            peak_performance_hours=[9, 10, 11, 14, 15],  # Placeholder
            common_struggle_areas=struggle_areas,
            strengths=strengths,
            personalized_tips=tips,
            next_focus_areas=["Maintain consistency", "Challenge yourself with harder problems"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get behavior insights: {str(e)}"
        )

@router.get("/privacy", response_model=PrivacyControlsResponse)
async def get_privacy_controls(
    current_user: User = Depends(get_current_user)
):
    """Get current privacy settings for behavior tracking."""
    # For now, return default settings
    # In the future, this will be stored in user preferences
    return PrivacyControlsResponse(
        user_key=current_user.key,
        tracking_enabled=True,
        anonymization_enabled=True,
        research_participation=False,
        data_retention_days=90
    )

@router.post("/privacy", response_model=PrivacyControlsResponse)
async def update_privacy_controls(
    settings: PrivacyControlsRequest,
    current_user: User = Depends(get_current_user)
):
    """Update privacy settings for behavior tracking."""
    # For now, just return the settings as if they were saved
    # In the future, this will update user preferences in the database
    return PrivacyControlsResponse(
        user_key=current_user.key,
        tracking_enabled=settings.enable_tracking,
        anonymization_enabled=settings.anonymize_data,
        research_participation=settings.share_insights_for_research,
        data_retention_days=settings.data_retention_period_days
    )

