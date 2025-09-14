from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from arango.database import StandardDatabase
import statistics
import uuid
from collections import defaultdict

from app.models.behavior import (
    KeystrokeEventCreate, KeystrokeEventInDB, KeystrokeEvent,
    TypingSessionCreate, TypingSessionInDB, TypingSession,
    BehaviorEventCreate, BehaviorEventInDB, BehaviorEvent,
    BehaviorInsightsInDB, BehaviorInsights,
    BehaviorEventType, LiveBehaviorMetrics, BehaviorSessionSummary
)

class BehaviorCRUD:
    """Behavior tracking database operations."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.keystrokes_collection = db.collection('keystroke_events')
        self.sessions_collection = db.collection('typing_sessions')
        self.behavior_events_collection = db.collection('behavior_events')
        self.insights_collection = db.collection('behavior_insights')
        
        # Thresholds for analysis
        self.PAUSE_THRESHOLD_MS = 500.0  # Pause if > 500ms between keystrokes
        self.BURST_THRESHOLD_MS = 150.0  # Burst if < 150ms between keystrokes
        self.FLOW_STATE_SPEED_THRESHOLD = 40.0  # CPM for flow state
        self.MIN_SESSION_DURATION_SECONDS = 30  # Minimum session length to analyze
    
    def create_session(self, user_key: str, question_key: Optional[str] = None) -> str:
        """Create a new behavior tracking session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        session_data = {
            "user_key": user_key,
            "session_id": session_id,
            "question_key": question_key,
            "start_time": now.isoformat(),
            "end_time": None,
            "total_keystrokes": 0,
            "productive_keystrokes": 0,
            "typing_speed_cpm": 0.0,
            "typing_speed_wpm": 0.0,
            "total_pauses": 0,
            "average_pause_duration": 0.0,
            "longest_pause_duration": 0.0,
            "pause_threshold": self.PAUSE_THRESHOLD_MS,
            "total_bursts": 0,
            "average_burst_length": 0.0,
            "longest_burst_length": 0,
            "burst_threshold": self.BURST_THRESHOLD_MS,
            "backspace_count": 0,
            "delete_count": 0,
            "correction_ratio": 0.0,
            "created_at": now.isoformat()
        }
        
        result = self.sessions_collection.insert(session_data)
        return session_id
    
    def add_keystroke_event(self, event: KeystrokeEventCreate) -> KeystrokeEventInDB:
        """Add a keystroke event to the database."""
        now = datetime.utcnow()
        
        # Get the last keystroke for this session to calculate time difference
        last_keystroke = self.get_last_keystroke_for_session(event.session_id)
        time_since_last = None
        
        if last_keystroke:
            time_diff = (event.timestamp - last_keystroke.timestamp).total_seconds() * 1000
            time_since_last = time_diff
        
        # Determine keystroke type
        is_backspace = event.key_pressed.lower() in ['backspace', 'delete']
        is_delete = event.key_pressed.lower() == 'delete'
        is_navigation = event.key_pressed.lower() in ['arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'home', 'end', 'pageup', 'pagedown']
        
        event_data = {
            "user_key": event.user_key,
            "session_id": event.session_id,
            "question_key": event.question_key,
            "timestamp": event.timestamp.isoformat(),
            "key_pressed": event.key_pressed,
            "key_code": event.key_code,
            "is_printable": event.is_printable,
            "cursor_position": event.cursor_position,
            "text_length": event.text_length,
            "created_at": now.isoformat(),
            "time_since_last_keystroke": time_since_last,
            "is_backspace": is_backspace,
            "is_delete": is_delete,
            "is_navigation": is_navigation
        }
        
        result = self.keystrokes_collection.insert(event_data)
        
        # Update session statistics
        self.update_session_stats(event.session_id)
        
        # Return the created event
        event_data["_key"] = result["_key"]
        return KeystrokeEventInDB(**event_data)
    
    def add_keystroke_events_batch(self, events: List[KeystrokeEventCreate]) -> List[str]:
        """Add multiple keystroke events in batch for better performance."""
        if not events:
            return []
        
        now = datetime.utcnow()
        session_id = events[0].session_id
        
        # Get the last keystroke before this batch
        last_keystroke = self.get_last_keystroke_for_session(session_id)
        
        events_data = []
        prev_timestamp = last_keystroke.timestamp if last_keystroke else None
        
        for event in events:
            # Calculate time since previous keystroke
            time_since_last = None
            if prev_timestamp:
                time_diff = (event.timestamp - prev_timestamp).total_seconds() * 1000
                time_since_last = time_diff
            
            # Determine keystroke type
            is_backspace = event.key_pressed.lower() in ['backspace', 'delete']
            is_delete = event.key_pressed.lower() == 'delete'
            is_navigation = event.key_pressed.lower() in ['arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'home', 'end', 'pageup', 'pagedown']
            
            event_data = {
                "user_key": event.user_key,
                "session_id": event.session_id,
                "question_key": event.question_key,
                "timestamp": event.timestamp.isoformat(),
                "key_pressed": event.key_pressed,
                "key_code": event.key_code,
                "is_printable": event.is_printable,
                "cursor_position": event.cursor_position,
                "text_length": event.text_length,
                "created_at": now.isoformat(),
                "time_since_last_keystroke": time_since_last,
                "is_backspace": is_backspace,
                "is_delete": is_delete,
                "is_navigation": is_navigation
            }
            
            events_data.append(event_data)
            prev_timestamp = event.timestamp
        
        # Batch insert
        results = self.keystrokes_collection.insert_many(events_data)
        
        # Update session statistics
        self.update_session_stats(session_id)
        
        return [result["_key"] for result in results]
    
    def get_last_keystroke_for_session(self, session_id: str) -> Optional[KeystrokeEventInDB]:
        """Get the most recent keystroke for a session."""
        query = """
        FOR event IN keystroke_events
            FILTER event.session_id == @session_id
            SORT event.timestamp DESC
            LIMIT 1
            RETURN event
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"session_id": session_id})
        results = list(cursor)
        
        if results:
            event_data = results[0]
            event_data["key"] = event_data["_key"]
            return KeystrokeEventInDB(**event_data)
        
        return None
    
    def update_session_stats(self, session_id: str) -> None:
        """Update typing session statistics based on keystroke events."""
        # Get all keystrokes for this session
        query = """
        FOR event IN keystroke_events
            FILTER event.session_id == @session_id
            SORT event.timestamp ASC
            RETURN event
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"session_id": session_id})
        keystrokes = list(cursor)
        
        if len(keystrokes) < 2:
            return  # Need at least 2 keystrokes for meaningful analysis
        
        # Calculate metrics
        stats = self.calculate_session_metrics(keystrokes)
        
        # Update session record
        self.sessions_collection.update_match(
            {"session_id": session_id},
            stats
        )
    
    def calculate_session_metrics(self, keystrokes: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive metrics from keystroke data."""
        if len(keystrokes) < 2:
            return {}
        
        total_keystrokes = len(keystrokes)
        productive_keystrokes = sum(1 for k in keystrokes if k.get("is_printable", False) and not k.get("is_backspace", False) and not k.get("is_navigation", False))
        
        # Time analysis
        start_time = datetime.fromisoformat(keystrokes[0]["timestamp"])
        end_time = datetime.fromisoformat(keystrokes[-1]["timestamp"])
        duration_seconds = (end_time - start_time).total_seconds()
        
        if duration_seconds == 0:
            return {"total_keystrokes": total_keystrokes}
        
        # Typing speed
        typing_speed_cpm = (productive_keystrokes / duration_seconds) * 60 if duration_seconds > 0 else 0
        typing_speed_wpm = typing_speed_cpm / 5.0  # Standard conversion: 5 chars = 1 word
        
        # Pause analysis
        pauses = []
        for i in range(1, len(keystrokes)):
            time_diff = keystrokes[i].get("time_since_last_keystroke", 0)
            if time_diff and time_diff > self.PAUSE_THRESHOLD_MS:
                pauses.append(time_diff)
        
        total_pauses = len(pauses)
        average_pause_duration = statistics.mean(pauses) if pauses else 0.0
        longest_pause_duration = max(pauses) if pauses else 0.0
        
        # Burst analysis
        bursts = []
        current_burst = 0
        
        for i in range(1, len(keystrokes)):
            time_diff = keystrokes[i].get("time_since_last_keystroke", 0)
            if time_diff and time_diff < self.BURST_THRESHOLD_MS:
                current_burst += 1
            else:
                if current_burst > 1:
                    bursts.append(current_burst)
                current_burst = 1
        
        if current_burst > 1:
            bursts.append(current_burst)
        
        total_bursts = len(bursts)
        average_burst_length = statistics.mean(bursts) if bursts else 0.0
        longest_burst_length = max(bursts) if bursts else 0
        
        # Error correction analysis
        backspace_count = sum(1 for k in keystrokes if k.get("is_backspace", False))
        delete_count = sum(1 for k in keystrokes if k.get("is_delete", False))
        correction_ratio = (backspace_count + delete_count) / total_keystrokes if total_keystrokes > 0 else 0
        
        # Advanced metrics
        rhythm_consistency = self.calculate_rhythm_consistency(keystrokes)
        hesitation_points = self.identify_hesitation_points(keystrokes)
        productivity_score = self.calculate_productivity_score(
            typing_speed_cpm, correction_ratio, rhythm_consistency
        )
        
        return {
            "total_keystrokes": total_keystrokes,
            "productive_keystrokes": productive_keystrokes,
            "typing_speed_cpm": typing_speed_cpm,
            "typing_speed_wpm": typing_speed_wpm,
            "total_pauses": total_pauses,
            "average_pause_duration": average_pause_duration,
            "longest_pause_duration": longest_pause_duration,
            "total_bursts": total_bursts,
            "average_burst_length": average_burst_length,
            "longest_burst_length": longest_burst_length,
            "backspace_count": backspace_count,
            "delete_count": delete_count,
            "correction_ratio": correction_ratio,
            "rhythm_consistency": rhythm_consistency,
            "hesitation_points": hesitation_points,
            "productivity_score": productivity_score,
            "pause_frequency": total_pauses / (duration_seconds / 60) if duration_seconds > 0 else 0,
            "burst_frequency": total_bursts / (duration_seconds / 60) if duration_seconds > 0 else 0,
            "typing_flow_score": self.calculate_flow_score(typing_speed_cpm, rhythm_consistency, total_pauses),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    def calculate_rhythm_consistency(self, keystrokes: List[Dict]) -> float:
        """Calculate how consistent the typing rhythm is (0-100)."""
        if len(keystrokes) < 3:
            return 0.0
        
        intervals = []
        for i in range(1, len(keystrokes)):
            time_diff = keystrokes[i].get("time_since_last_keystroke", 0)
            if time_diff and time_diff < 1000:  # Ignore very long pauses
                intervals.append(time_diff)
        
        if len(intervals) < 2:
            return 0.0
        
        # Calculate coefficient of variation (lower = more consistent)
        mean_interval = statistics.mean(intervals)
        std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
        
        if mean_interval == 0:
            return 0.0
        
        cv = std_dev / mean_interval
        # Convert to 0-100 scale (lower CV = higher consistency)
        consistency = max(0, 100 - (cv * 50))
        return min(100, consistency)
    
    def identify_hesitation_points(self, keystrokes: List[Dict]) -> List[Dict[str, Any]]:
        """Identify moments of significant hesitation."""
        hesitations = []
        
        for i, keystroke in enumerate(keystrokes):
            time_diff = keystroke.get("time_since_last_keystroke", 0)
            
            # Significant pause (> 2 seconds)
            if time_diff and time_diff > 2000:
                hesitations.append({
                    "timestamp": keystroke["timestamp"],
                    "duration_ms": time_diff,
                    "keystroke_index": i,
                    "type": "long_pause"
                })
        
        return hesitations
    
    def calculate_productivity_score(self, typing_speed: float, correction_ratio: float, rhythm_consistency: float) -> float:
        """Calculate overall productivity score (0-100)."""
        # Normalize typing speed (assuming 60 CPM is good, 120+ is excellent)
        speed_score = min(100, (typing_speed / 60) * 50)
        
        # Correction penalty (lower correction ratio is better)
        correction_score = max(0, 100 - (correction_ratio * 200))
        
        # Rhythm contribution
        rhythm_score = rhythm_consistency
        
        # Weighted average
        productivity = (speed_score * 0.4) + (correction_score * 0.4) + (rhythm_score * 0.2)
        return min(100, max(0, productivity))
    
    def calculate_flow_score(self, typing_speed: float, rhythm_consistency: float, total_pauses: int) -> float:
        """Calculate flow state score (0-100)."""
        # Speed component (higher is better up to a point)
        speed_component = min(100, (typing_speed / 80) * 40)
        
        # Consistency component
        consistency_component = rhythm_consistency * 0.4
        
        # Pause penalty (fewer pauses in flow state)
        pause_penalty = min(20, total_pauses * 2)
        
        flow_score = speed_component + consistency_component - pause_penalty
        return min(100, max(0, flow_score))
    
    def end_session(self, session_id: str) -> Optional[TypingSessionInDB]:
        """End a typing session and finalize analytics."""
        now = datetime.utcnow()
        
        # Update end time
        result = self.sessions_collection.update_match(
            {"session_id": session_id},
            {"end_time": now.isoformat(), "updated_at": now.isoformat()}
        )
        
        if result:
            return self.get_session(session_id)
        return None
    
    def get_session(self, session_id: str) -> Optional[TypingSessionInDB]:
        """Get a typing session by ID."""
        query = """
        FOR session IN typing_sessions
            FILTER session.session_id == @session_id
            RETURN session
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"session_id": session_id})
        results = list(cursor)
        
        if results:
            session_data = results[0]
            session_data["key"] = session_data["_key"]
            return TypingSessionInDB(**session_data)
        
        return None
    
    def get_live_metrics(self, session_id: str) -> Optional[LiveBehaviorMetrics]:
        """Get real-time metrics for a session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Get recent keystrokes (last minute)
        query = """
        FOR event IN keystroke_events
            FILTER event.session_id == @session_id
            FILTER event.timestamp > DATE_SUBTRACT(DATE_NOW(), 60, "second")
            SORT event.timestamp DESC
            RETURN event
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"session_id": session_id})
        recent_keystrokes = list(cursor)
        
        if not recent_keystrokes:
            return LiveBehaviorMetrics(
                session_id=session_id,
                current_typing_speed_cpm=0.0,
                current_typing_speed_wpm=0.0,
                recent_pause_count=0,
                current_burst_length=0,
                time_since_last_keystroke=0.0,
                is_in_flow_state=False,
                productivity_indicator="low"
            )
        
        # Calculate current metrics
        recent_metrics = self.calculate_session_metrics(recent_keystrokes)
        last_keystroke = recent_keystrokes[0]  # Most recent
        
        time_since_last = 0.0
        if last_keystroke.get("timestamp"):
            last_time = datetime.fromisoformat(last_keystroke["timestamp"])
            time_since_last = (datetime.utcnow() - last_time).total_seconds() * 1000
        
        current_speed = recent_metrics.get("typing_speed_cpm", 0.0)
        is_in_flow = current_speed > self.FLOW_STATE_SPEED_THRESHOLD and recent_metrics.get("rhythm_consistency", 0) > 60
        
        # Determine productivity level
        productivity_score = recent_metrics.get("productivity_score", 0)
        if productivity_score > 70:
            productivity_indicator = "high"
        elif productivity_score > 40:
            productivity_indicator = "medium"
        else:
            productivity_indicator = "low"
        
        # Generate suggestion
        suggestion = self.generate_live_suggestion(recent_metrics, time_since_last)
        
        return LiveBehaviorMetrics(
            session_id=session_id,
            current_typing_speed_cpm=current_speed,
            current_typing_speed_wpm=current_speed / 5.0,
            recent_pause_count=recent_metrics.get("total_pauses", 0),
            current_burst_length=recent_metrics.get("longest_burst_length", 0),
            time_since_last_keystroke=time_since_last,
            is_in_flow_state=is_in_flow,
            productivity_indicator=productivity_indicator,
            suggestion=suggestion
        )
    
    def generate_live_suggestion(self, metrics: Dict[str, Any], time_since_last: float) -> Optional[str]:
        """Generate real-time suggestions based on current behavior."""
        if time_since_last > 10000:  # 10 seconds idle
            return "Take a moment to think about your approach, then continue coding!"
        
        if metrics.get("correction_ratio", 0) > 0.3:
            return "Consider slowing down to reduce typos and increase accuracy."
        
        if metrics.get("typing_speed_cpm", 0) > 100 and metrics.get("rhythm_consistency", 0) > 80:
            return "Great flow! You're coding efficiently and consistently."
        
        if metrics.get("total_pauses", 0) > 5:
            return "Frequent pauses detected. Break down the problem into smaller steps."
        
        return None
    
    def get_user_sessions(self, user_key: str, limit: int = 10) -> List[TypingSessionInDB]:
        """Get recent typing sessions for a user."""
        query = """
        FOR session IN typing_sessions
            FILTER session.user_key == @user_key
            SORT session.created_at DESC
            LIMIT @limit
            RETURN session
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"user_key": user_key, "limit": limit})
        results = list(cursor)
        
        sessions = []
        for session_data in results:
            session_data["key"] = session_data["_key"]
            sessions.append(TypingSessionInDB(**session_data))
        
        return sessions

