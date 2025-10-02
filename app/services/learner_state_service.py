"""
Learner State Service.

Handles all learner state updates triggered by user actions.
This is the bridge between submission events and the learner state database.
"""

from typing import List, Optional
from datetime import datetime
import logging

from app.models.user import User
from app.models.learner_state import LearnerState, create_default_learner_state
from app.models.submission import SubmissionStatus
from app.crud.learner_state import LearnerStateCRUD
from app.crud.user import UserCRUD

logger = logging.getLogger(__name__)


class LearnerStateService:
    """Service for managing learner state updates."""
    
    def __init__(self, learner_crud: LearnerStateCRUD, user_crud: UserCRUD):
        self.learner_crud = learner_crud
        self.user_crud = user_crud
    
    async def update_on_submission(
        self,
        user: User,
        question_key: str,
        submission_status: SubmissionStatus,
        topics: List[str],
        error_message: Optional[str] = None,
        hints_used: int = 0
    ) -> LearnerState:
        """
        Update learner state after a code submission.
        
        This is the main entry point for submission-triggered updates.
        Handles:
        - Mastery level adjustments
        - Error pattern tracking
        - Spaced repetition scheduling
        - Streak updates
        
        Args:
            user: Current user
            question_key: Question that was attempted
            submission_status: Result of submission
            topics: Topics associated with the question
            error_message: Error message if submission failed
            hints_used: Number of hints used during attempt
            
        Returns:
            Updated learner state
        """
        # Initialize state if it doesn't exist
        if user.learner_state is None:
            logger.info(f"🎓 Initializing learner state for user {user.key}")
            state = create_default_learner_state()
        else:
            state = user.learner_state
        
        is_success = submission_status == SubmissionStatus.ACCEPTED
        
        logger.info(
            f"📊 Updating learner state for user {user.key}: "
            f"Question={question_key}, Success={is_success}, Topics={topics}"
        )
        
        # Update mastery for all relevant topics
        if topics:
            state.mastery = self.learner_crud.update_mastery_from_submission(
                state, topics, is_success
            )
            logger.debug(f"✅ Updated mastery: {state.mastery}")
        
        # Schedule review if successfully solved
        if is_success and topics:
            # Check if this is first successful solve for this question
            is_first_success = self._is_first_success(user.key, question_key)
            
            state.reviews = self.learner_crud.schedule_review(
                state, question_key, topics, is_first_success
            )
            logger.debug(f"📅 Scheduled review for {question_key} (topics: {', '.join(topics)})")
        
        # Update streak
        state.streak, state.last_seen = self.learner_crud.update_streak(state)
        logger.debug(f"🔥 Current streak: {state.streak}")
        
        # Update timestamp
        state.updated = datetime.utcnow()
        
        # Save to database
        await self._save_learner_state(user.key, state)
        
        logger.info(f"💾 Learner state saved for user {user.key}")
        
        return state
    
    async def ensure_initialized(self, user: User) -> LearnerState:
        """
        Ensure user has a learner state, initializing from history if needed.
        
        Args:
            user: Current user
            
        Returns:
            User's learner state (initialized if needed)
        """
        if user.learner_state is None:
            logger.info(f"🔄 Initializing learner state from history for user {user.key}")
            state = self.learner_crud.initialize_from_history(user.key)
            await self._save_learner_state(user.key, state)
            return state
        
        return user.learner_state
    
    def get_topics_from_question(self, question_key: str) -> List[str]:
        """
        Extract topics from a question in the roadmap.
        
        Args:
            question_key: Question identifier
            
        Returns:
            List of topic strings
        """
        topics = self.learner_crud._get_question_topics(question_key)
        
        if not topics:
            logger.warning(f"⚠️ No topics found for question {question_key}")
            return []
        
        logger.debug(f"📚 Topics for {question_key}: {topics}")
        return topics
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    async def _save_learner_state(self, user_key: str, state: LearnerState):
        """Save learner state to user document."""
        try:
            # Use model_dump(mode='json') to convert datetime objects to ISO strings
            self.user_crud.update_user_fields(user_key, {
                'learner_state': state.model_dump(mode='json')
            })
        except Exception as e:
            logger.error(f"❌ Failed to save learner state for user {user_key}: {e}")
            raise
    
    def _is_first_success(self, user_key: str, question_key: str) -> bool:
        """
        Check if this is the first successful submission for a question.
        
        Args:
            user_key: User identifier
            question_key: Question identifier
            
        Returns:
            True if this is the first successful solve
        """
        query = """
        FOR s IN submissions
            FILTER s.user_key == @user_key 
            AND s.question_key == @question_key
            AND s.status == "Accepted"
            LIMIT 1
            RETURN s
        """
        
        cursor = self.learner_crud.db.aql.execute(
            query,
            bind_vars={'user_key': user_key, 'question_key': question_key}
        )
        
        results = list(cursor)
        
        # If no previous accepted submissions, this is the first
        return len(results) == 0


def create_learner_state_service(
    learner_crud: LearnerStateCRUD,
    user_crud: UserCRUD
) -> LearnerStateService:
    """
    Factory function to create a LearnerStateService.
    
    Args:
        learner_crud: LearnerStateCRUD instance
        user_crud: UserCRUD instance
        
    Returns:
        Configured LearnerStateService
    """
    return LearnerStateService(learner_crud, user_crud)

