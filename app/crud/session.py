from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from arango.database import StandardDatabase
import uuid

from ..models.session import (
    CodingSessionInDB, 
    CodingSessionCreate, 
    CodingSessionUpdate,
    SessionState,
    SessionType,
    SessionEventCreate,
    SessionCodeSnapshot
)


class SessionCRUD:
    """Session management database operations."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.sessions_collection = db.collection('sessions')
        
        # Session expiration settings
        self.ABANDONED_EXPIRY_HOURS = 24  # Mark inactive sessions as abandoned after 24 hours
        
    def create_session(self, user_key: str, session_data: CodingSessionCreate) -> CodingSessionInDB:
        """Create a new coding session."""
        now = datetime.utcnow()
        
        # Generate session_id if not provided
        session_id = session_data.session_id or str(uuid.uuid4())
        
        print(f"💾 Creating session in database for user: {user_key}")
        print(f"🆔 Session ID: {session_id}")
        
        # First, end any existing active sessions for this user
        ended_count = self._end_user_active_sessions(user_key)
        if ended_count > 0:
            print(f"🔄 Ended {ended_count} existing active sessions")
        
        # Normalize session_type from either 'type' or 'session_type' field
        session_type = session_data.type or session_data.session_type
        if not session_type:
            raise ValueError("Session type is required")
        
        # Normalize field names (accept both camelCase and snake_case)
        question_id = session_data.questionId or session_data.question_id
        question_title = session_data.questionTitle or session_data.question_title
        roadmap_id = session_data.roadmapId or session_data.roadmap_id
        language = session_data.language or session_data.programming_language or "python"
        
        # Merge config fields from frontend
        config = session_data.config.copy() if session_data.config else {}
        
        # Handle both direct fields and aliased fields
        enable_tracking = session_data.enableBehaviorTracking
        if enable_tracking is not None:
            config['enable_behavior_tracking'] = enable_tracking
            
        enable_fullscreen = session_data.enableFullscreen
        if enable_fullscreen is not None:
            config['enable_fullscreen'] = enable_fullscreen
            
        time_commitment = session_data.timeCommitment
        if time_commitment:
            config['time_commitment'] = time_commitment
            
        user_agreements = session_data.userAgreements
        if user_agreements:
            config['user_agreements'] = user_agreements
        
        session_doc = {
            "user_key": user_key,
            "session_id": session_id,
            "session_type": session_type,
            "state": SessionState.ACTIVE.value,
            "question_id": question_id,
            "question_title": question_title,
            "roadmap_id": roadmap_id,
            "difficulty": session_data.difficulty,
            "programming_language": language,
            "config": config,
            "start_time": now.isoformat() + 'Z',  # Add Z to indicate UTC
            "last_activity": now.isoformat() + 'Z',
            "end_time": None,
            "behavior_session_id": session_data.behavior_session_id,
            "analytics": {
                "code_changes": 0,
                "tests_run": 0,
                "hints_used": 0,
                "attempts_count": 0,
                "is_completed": False
            },
            "code_snapshots": [],
            "session_events": [],
            "created_at": now.isoformat() + 'Z',
            "updated_at": now.isoformat() + 'Z'
        }
        
        try:
            print(f"📝 About to insert session document: {session_doc.keys()}")
            result = self.sessions_collection.insert(session_doc)
            print(f"📄 Insert result: {result}")
            
            session_doc['_key'] = result['_key']
            print(f"✅ Session inserted with key: {result['_key']}")
            
            # Immediately verify the insertion worked
            verification_cursor = self.sessions_collection.find({"session_id": session_id})
            verification_docs = list(verification_cursor)
            print(f"🔄 Verification: Found {len(verification_docs)} sessions with ID {session_id}")
            
            created_session = CodingSessionInDB(**session_doc)
            print(f"✅ Session object created successfully")
            return created_session
            
        except Exception as e:
            print(f"❌ Failed to insert session into database: {e}")
            print(f"❌ Exception type: {type(e)}")
            print(f"❌ Session document keys: {session_doc.keys()}")
            # Print the actual session_doc but mask sensitive data
            safe_doc = {k: v for k, v in session_doc.items() if k not in ['config']}
            print(f"❌ Session document (safe): {safe_doc}")
            raise
    
    def get_session(self, session_id: str) -> Optional[CodingSessionInDB]:
        """Get a session by session ID."""
        try:
            print(f"🔍 Searching for session: {session_id}")
            cursor = self.sessions_collection.find({"session_id": session_id})
            sessions = list(cursor)
            print(f"🔎 Found {len(sessions)} sessions with ID: {session_id}")
            
            if sessions:
                session_data = sessions[0]
                print(f"✅ Session found: {session_data.get('_key', 'no_key')} - State: {session_data.get('state', 'unknown')}")
                return CodingSessionInDB(**session_data)
            else:
                print(f"❌ No session found with ID: {session_id}")
                # Let's also check if there are any sessions at all for debugging
                all_sessions_cursor = self.sessions_collection.all()
                all_sessions = list(all_sessions_cursor)
                print(f"📊 Total sessions in database: {len(all_sessions)}")
                if len(all_sessions) > 0:
                    print("📋 Recent session IDs:")
                    for session in all_sessions[-5:]:  # Show last 5
                        print(f"   - {session.get('session_id', 'no_id')} ({session.get('state', 'unknown')})")
                return None
        except Exception as e:
            print(f"❌ Error getting session: {e}")
            return None
    
    def get_user_active_session(self, user_key: str) -> Optional[CodingSessionInDB]:
        """Get user's current active session. Only returns ACTIVE or PAUSED sessions, never terminal states."""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 GET_USER_ACTIVE_SESSION called for user: {user_key}")
            
            # First, let's see ALL sessions for this user to debug
            all_sessions_cursor = self.sessions_collection.find({"user_key": user_key})
            all_sessions = list(all_sessions_cursor)
            print(f"📊 Total sessions in DB for user: {len(all_sessions)}")
            for idx, s in enumerate(all_sessions):
                print(f"   Session {idx+1}: ID={s.get('session_id')}, State={s.get('state')}")
            
            # Use AQL for proper IN query (ArangoDB's find() doesn't support $in operator well)
            aql_query = """
                FOR session IN sessions
                    FILTER session.user_key == @user_key
                    AND session.state == "active"
                    SORT session.start_time DESC
                    LIMIT 1
                    RETURN session
            """
            
            print(f"📋 Using AQL query to find active/paused sessions")
            
            cursor = self.db.aql.execute(
                aql_query,
                bind_vars={"user_key": user_key}
            )
            sessions = list(cursor)
            
            print(f"📊 Found {len(sessions)} active/paused sessions using AQL")
            
            if sessions:
                session_data = sessions[0]
                print(f"✅ Returning session: ID={session_data.get('session_id')}, State={session_data.get('state')}")
                
                # Double-check the state before returning
                if session_data.get('state') != SessionState.ACTIVE.value:
                    print(f"⚠️ Session has invalid state for active query: {session_data.get('state')}")
                    print(f"{'='*60}\n")
                    return None
                
                session = CodingSessionInDB(**session_data)
                
                print(f"{'='*60}\n")
                return session
            
            print(f"ℹ️ No active sessions found for user - returning None")
            print(f"{'='*60}\n")
            return None
            
        except Exception as e:
            print(f"❌ Error getting user active session: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_user_active_session_by_question(
        self, 
        user_key: str, 
        question_id: Optional[str] = None,
        question_title: Optional[str] = None
    ) -> Optional[CodingSessionInDB]:
        """Get user's active session for a specific question. Only returns ACTIVE or PAUSED sessions."""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 GET_USER_ACTIVE_SESSION_BY_QUESTION called")
            print(f"👤 User: {user_key}")
            print(f"❓ Question ID: {question_id}")
            print(f"📝 Question Title: {question_title}")
            
            # Build AQL query based on what's provided
            if question_id and question_title:
                # Try both to be more flexible
                aql_query = """
                    FOR session IN sessions
                        FILTER session.user_key == @user_key
                        AND session.state == "active"
                        AND (session.question_id == @question_id OR session.question_title == @question_title)
                        SORT session.start_time DESC
                        LIMIT 1
                        RETURN session
                """
                bind_vars = {
                    "user_key": user_key,
                    "question_id": question_id,
                    "question_title": question_title
                }
            elif question_id:
                aql_query = """
                    FOR session IN sessions
                        FILTER session.user_key == @user_key
                        AND session.state == "active"
                        AND session.question_id == @question_id
                        SORT session.start_time DESC
                        LIMIT 1
                        RETURN session
                """
                bind_vars = {"user_key": user_key, "question_id": question_id}
            else:
                aql_query = """
                    FOR session IN sessions
                        FILTER session.user_key == @user_key
                        AND session.state == "active"
                        AND session.question_title == @question_title
                        SORT session.start_time DESC
                        LIMIT 1
                        RETURN session
                """
                bind_vars = {"user_key": user_key, "question_title": question_title}
            
            cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
            sessions = list(cursor)
            
            print(f"📊 Found {len(sessions)} active/paused sessions for this question")
            
            if sessions:
                session_data = sessions[0]
                print(f"✅ Found session: ID={session_data.get('session_id')}, State={session_data.get('state')}")
                
                # Validate state
                if session_data.get('state') != SessionState.ACTIVE.value:
                    print(f"⚠️ Session has invalid state: {session_data.get('state')}")
                    print(f"{'='*60}\n")
                    return None
                
                session = CodingSessionInDB(**session_data)
                
                print(f"{'='*60}\n")
                return session
            
            print(f"ℹ️ No active sessions found for this question")
            print(f"{'='*60}\n")
            return None
            
        except Exception as e:
            print(f"❌ Error getting user active session by question: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_session(self, session_id: str, update_data: CodingSessionUpdate) -> Optional[CodingSessionInDB]:
        """Update a session."""
        try:
            now = datetime.utcnow()
            update_doc = {"updated_at": now.isoformat() + 'Z'}
            
            if update_data.state is not None:
                update_doc["state"] = update_data.state.value
                
                # Handle state-specific logic - only ABANDONED state sets end_time
                if update_data.state == SessionState.ABANDONED:
                    update_doc["end_time"] = now.isoformat() + 'Z'
            
            if update_data.last_activity is not None:
                update_doc["last_activity"] = update_data.last_activity.isoformat() + 'Z'
            
            if update_data.analytics is not None:
                update_doc["analytics"] = update_data.analytics
                
            if update_data.config is not None:
                update_doc["config"] = update_data.config
            
            result = self.sessions_collection.update_match(
                {"session_id": session_id},
                update_doc
            )
            
            print(f"✅ Session {session_id} updated: {result}")
            
            return self.get_session(session_id)
            
        except Exception as e:
            print(f"❌ Error updating session: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def end_session(self, session_id: str, reason: str = "user_request") -> bool:
        """End a session by marking it as abandoned."""
        try:
            print(f"🛑 END_SESSION called for: {session_id}, reason: {reason}")
            session = self.get_session(session_id)
            if not session:
                print(f"❌ Session {session_id} not found")
                return False
            
            print(f"📊 Current session state: {session.state.value}")
            
            # If already abandoned, treat as success (idempotent)
            if session.state == SessionState.ABANDONED:
                print(f"ℹ️ Session {session_id} already abandoned")
                return True
            
            print(f"🔄 Marking session {session_id} as abandoned")
            
            update_data = CodingSessionUpdate(
                state=SessionState.ABANDONED,
                last_activity=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
            
            updated_session = self.update_session(session_id, update_data)
            
            if updated_session:
                print(f"✅ Session {session_id} marked as abandoned")
            else:
                print(f"❌ Failed to update session {session_id}")
            
            # Record end event
            self.add_session_event(session_id, "session_ended", {"reason": reason})
            
            return updated_session is not None
            
        except Exception as e:
            print(f"❌ Error ending session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def add_session_event(self, session_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Add an event to a session (stored within session document)."""
        try:
            now = datetime.utcnow()
            session = self.get_session(session_id)
            if not session:
                return False
            
            event = {
                "event_type": event_type,
                "data": data,
                "timestamp": now.isoformat() + 'Z'
            }
            
            # Get current session document
            cursor = self.sessions_collection.find({"session_id": session_id})
            session_docs = list(cursor)
            if not session_docs:
                return False
            
            session_doc = session_docs[0]
            session_events = session_doc.get("session_events", [])
            session_events.append(event)
            
            # Update session with new event
            self.sessions_collection.update_match(
                {"session_id": session_id},
                {
                    "session_events": session_events,
                    "last_activity": now.isoformat() + 'Z',
                    "updated_at": now.isoformat() + 'Z'
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error adding session event: {e}")
            return False
    
    def add_code_snapshot(self, session_id: str, code: str, language: str = "python", is_current: bool = False) -> bool:
        """Add a code snapshot to a session (stored within session document)."""
        try:
            now = datetime.utcnow()
            
            # Get current session document
            cursor = self.sessions_collection.find({"session_id": session_id})
            session_docs = list(cursor)
            if not session_docs:
                return False
            
            session_doc = session_docs[0]
            code_snapshots = session_doc.get("code_snapshots", [])
            
            # If this is marked as current, clear any existing current flags
            if is_current:
                for snapshot in code_snapshots:
                    snapshot["is_current"] = False
            
            snapshot = {
                "code": code,
                "language": language,
                "code_length": len(code),
                "is_current": is_current,
                "timestamp": now.isoformat() + 'Z'
            }
            
            code_snapshots.append(snapshot)
            
            # Update session analytics
            analytics = session_doc.get("analytics", {})
            analytics["code_changes"] = analytics.get("code_changes", 0) + 1
            
            # Update session with new snapshot
            self.sessions_collection.update_match(
                {"session_id": session_id},
                {
                    "code_snapshots": code_snapshots,
                    "analytics": analytics,
                    "last_activity": now.isoformat() + 'Z',
                    "updated_at": now.isoformat() + 'Z'
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error adding code snapshot: {e}")
            return False
    
    def update_current_code(self, session_id: str, code: str, language: str = "python") -> bool:
        """Update the current code state for a session."""
        return self.add_code_snapshot(session_id, code, language, is_current=True)
    
    def get_current_code(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current code state for a session."""
        try:
            cursor = self.sessions_collection.find({"session_id": session_id})
            session_docs = list(cursor)
            if not session_docs:
                return None
            
            session_doc = session_docs[0]
            code_snapshots = session_doc.get("code_snapshots", [])
            
            if not code_snapshots:
                return None
            
            # Find the current snapshot
            for snapshot in reversed(code_snapshots):
                if snapshot.get("is_current"):
                    return {
                        "code": snapshot["code"],
                        "language": snapshot["language"],
                        "timestamp": snapshot["timestamp"]
                    }
            
            # If no current code marked, get the latest snapshot
            latest_snapshot = code_snapshots[-1]
            return {
                "code": latest_snapshot["code"],
                "language": latest_snapshot["language"],
                "timestamp": latest_snapshot["timestamp"]
            }
            
        except Exception as e:
            print(f"Error getting current code: {e}")
            return None
    
    def get_session_with_code(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session with current code state for recovery."""
        try:
            session = self.get_session(session_id)
            if not session:
                return None
            
            current_code = self.get_current_code(session_id)
            
            return {
                "session": session,
                "current_code": current_code.get("code") if current_code else None,
                "language": current_code.get("language", "python") if current_code else "python",
                "last_code_update": current_code.get("timestamp") if current_code else None
            }
            
        except Exception as e:
            print(f"Error getting session with code: {e}")
            return None
    
    def get_user_sessions(self, user_key: str, limit: int = 10, include_active: bool = True) -> List[CodingSessionInDB]:
        """Get user's recent sessions."""
        try:
            query_filter = {"user_key": user_key}
            
            if not include_active:
                query_filter["state"] = SessionState.ABANDONED.value
            
            # Fix ArangoDB sort syntax
            cursor = self.sessions_collection.find(
                query_filter,
                limit=limit
            ).sort("created_at", reverse=True)
            
            sessions = []
            for session_doc in cursor:
                session = CodingSessionInDB(**session_doc)
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []
    
    def cleanup_abandoned_sessions(self) -> int:
        """Clean up abandoned sessions - mark inactive sessions as abandoned."""
        try:
            now = datetime.utcnow()
            
            # Find sessions that have been active too long with no activity
            abandoned_threshold = now - timedelta(hours=self.ABANDONED_EXPIRY_HOURS)
            cursor = self.sessions_collection.find({
                "state": SessionState.ACTIVE.value,
                "last_activity": {"$lt": abandoned_threshold.isoformat()}
            })
            
            abandoned_count = 0
            for session_doc in cursor:
                session_id = session_doc["session_id"]
                self.end_session(session_id, "auto_abandoned")
                abandoned_count += 1
            
            return abandoned_count
            
        except Exception as e:
            print(f"Error cleaning up abandoned sessions: {e}")
            return 0
    
    def _end_user_active_sessions(self, user_key: str) -> int:
        """End all active sessions for a user. Returns number of sessions ended."""
        try:
            cursor = self.sessions_collection.find({
                "user_key": user_key,
                "state": SessionState.ACTIVE.value
            })
            
            ended_count = 0
            for session_doc in cursor:
                session_id = session_doc["session_id"]
                self.end_session(session_id, "new_session_started")
                ended_count += 1
            
            return ended_count
            
        except Exception as e:
            print(f"Error ending user active sessions: {e}")
            return 0
