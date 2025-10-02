"""
Learner State CRUD Operations.

Handles initialization, updates, and calculations for the centralized
learner state used by the Intelligent Tutoring System.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from arango.database import StandardDatabase
import json

from app.models.learner_state import (
    LearnerState, 
    ReviewItem, 
    TopicStatistics,
    create_default_learner_state
)
from app.models.submission import SubmissionStatus
from app.utils.topics import normalize_topics


class LearnerStateCRUD:
    """Operations for managing learner state."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.users_collection = db.collection('users')
        self.submissions_collection = db.collection('submissions')
        self.roadmap_collection = db.collection('roadmap')
    
    def initialize_from_history(self, user_key: str) -> LearnerState:
        """
        Initialize learner state from user's submission history.
        
        Calculates:
        - Topic mastery from past submissions
        - Current streak from activity
        
        Args:
            user_key: User's document key
            
        Returns:
            Initialized LearnerState
        """
        # Start with default state
        state = create_default_learner_state()
        
        # Get all user submissions
        submissions = self._get_user_submissions(user_key)
        
        if not submissions:
            return state
        
        # Calculate mastery per topic
        state.mastery = self._calculate_topic_mastery(submissions)
        
        # Calculate current streak
        state.streak = self._calculate_streak(submissions)
        state.last_seen = date.today()
        state.updated = datetime.utcnow()
        
        return state
    
    def update_mastery_from_submission(
        self, 
        current_state: LearnerState, 
        topics: List[str], 
        is_success: bool
    ) -> Dict[str, float]:
        """
        Update topic mastery based on a new submission.
        
        Algorithm:
        - Success: mastery += 0.1 * (1 - current_mastery)
        - Failure: mastery -= 0.15 * current_mastery
        - Clamped to [0.0, 1.0]
        
        Args:
            current_state: Current learner state
            topics: Topics from the question
            is_success: Whether submission passed
            
        Returns:
            Updated mastery dict
        """
        mastery = current_state.mastery.copy()
        
        for topic in topics:
            current_level = mastery.get(topic, 0.0)
            
            if is_success:
                # Increase mastery, diminishing returns as you approach 1.0
                increase = 0.1 * (1.0 - current_level)
                mastery[topic] = min(1.0, current_level + increase)
            else:
                # Decrease mastery proportionally
                decrease = 0.15 * current_level
                mastery[topic] = max(0.0, current_level - decrease)
        
        return mastery
    
    def schedule_review(
        self,
        current_state: LearnerState,
        question_id: str,
        topics: List[str],
        is_first_success: bool = True
    ) -> List[ReviewItem]:
        """
        Schedule a question for spaced repetition review.
        
        Uses simplified SM-2 algorithm:
        - First success: Review in 1 day
        - Subsequent: Interval increases
        
        Args:
            current_state: Current learner state
            question_id: Question to schedule
            topics: All topics covered by this question
            is_first_success: Whether this is first successful solve
            
        Returns:
            Updated reviews list
        """
        reviews = current_state.reviews.copy()
        
        # Check if already scheduled
        existing = next((r for r in reviews if r.question_id == question_id), None)
        
        if existing:
            # Update existing review (increase interval)
            new_interval = int(existing.interval_days * existing.ease_factor)
            existing.interval_days = new_interval
            existing.due_date = datetime.utcnow() + timedelta(days=new_interval)
            # Update topics in case they changed
            existing.topics = topics
        else:
            # Schedule new review
            interval = 1 if is_first_success else 3
            review = ReviewItem(
                question_id=question_id,
                topics=topics,
                due_date=datetime.utcnow() + timedelta(days=interval),
                interval_days=interval,
                ease_factor=2.5
            )
            reviews.append(review)
        
        return reviews
    
    def get_due_reviews(self, learner_state: LearnerState) -> List[ReviewItem]:
        """
        Get reviews that are due today or overdue.
        
        Args:
            learner_state: Current learner state
            
        Returns:
            List of due reviews, sorted by due date
        """
        now = datetime.utcnow()
        due = [r for r in learner_state.reviews if r.due_date <= now]
        return sorted(due, key=lambda r: r.due_date)
    
    def update_streak(self, current_state: LearnerState) -> Tuple[int, date]:
        """
        Update streak based on current date.
        
        Logic:
        - Same day: Keep streak
        - Next day: Increment streak
        - Gap > 1 day: Reset to 1
        
        Args:
            current_state: Current learner state
            
        Returns:
            Tuple of (new_streak, today's_date)
        """
        today = date.today()
        last = current_state.last_seen
        
        if last == today:
            # Same day, no change
            return current_state.streak, today
        
        days_since = (today - last).days
        
        if days_since == 1:
            # Consecutive day, increment
            return current_state.streak + 1, today
        else:
            # Gap, reset to 1
            return 1, today
    
    def get_topic_statistics(self, user_key: str, topic: str) -> TopicStatistics:
        """
        Get detailed statistics for a specific topic.
        
        Args:
            user_key: User's document key
            topic: DSA topic
            
        Returns:
            TopicStatistics with metrics
        """
        # Get user's learner state
        user = self.users_collection.get(user_key)
        if not user or 'learner_state' not in user or not user['learner_state']:
            # Return empty stats
            return TopicStatistics(
                topic=topic,
                mastery_level=0.0,
                total_attempts=0,
                problems_solved=0,
                success_rate=0.0,
                last_practiced=None,
                needs_review=False
            )
        
        state_dict = user['learner_state']
        mastery_level = state_dict.get('mastery', {}).get(topic, 0.0)
        
        # Get submission stats for this topic
        query = """
        FOR r IN roadmap
            FILTER @topic IN r.topics
            LET submissions = (
                FOR s IN submissions
                    FILTER s.user_key == @user_key 
                    AND s.question_key == r._key
                    RETURN s
            )
            LET attempts = LENGTH(submissions)
            LET solved = LENGTH(submissions[* FILTER CURRENT.status == "Accepted"])
            RETURN {
                attempts: attempts,
                solved: solved,
                last_practiced: MAX(submissions[*].created_at)
            }
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={'topic': topic, 'user_key': user_key}
        )
        results = list(cursor)
        
        total_attempts = sum(r['attempts'] for r in results)
        problems_solved = sum(1 for r in results if r['solved'] > 0)
        last_practiced_str = max([r['last_practiced'] for r in results if r['last_practiced']], default=None)
        
        last_practiced = datetime.fromisoformat(last_practiced_str) if last_practiced_str else None
        success_rate = problems_solved / total_attempts if total_attempts > 0 else 0.0
        
        # Check if needs review (mastery < 0.7 or last practiced > 7 days ago)
        needs_review = mastery_level < 0.7
        if last_practiced:
            days_since = (datetime.utcnow() - last_practiced).days
            needs_review = needs_review or days_since > 7
        
        return TopicStatistics(
            topic=topic,
            mastery_level=mastery_level,
            total_attempts=total_attempts,
            problems_solved=problems_solved,
            success_rate=success_rate,
            last_practiced=last_practiced,
            needs_review=needs_review
        )
    
    # ============================================================================
    # PRIVATE HELPER METHODS
    # ============================================================================
    
    def _get_user_submissions(self, user_key: str) -> List[Dict]:
        """Get all submissions for a user."""
        query = "FOR s IN submissions FILTER s.user_key == @user_key RETURN s"
        cursor = self.db.aql.execute(query, bind_vars={'user_key': user_key})
        return list(cursor)
    
    def _calculate_topic_mastery(self, submissions: List[Dict]) -> Dict[str, float]:
        """
        Calculate mastery for each topic from submission history.
        
        Algorithm:
        1. Get topics for each question from roadmap
        2. Calculate success rate per topic
        3. Apply recency weighting
        """
        topic_stats = {}  # topic -> {'success': 0, 'total': 0, 'recent': []}
        
        for sub in submissions:
            # Get topics for this question
            topics = self._get_question_topics(sub['question_key'])
            is_success = sub['status'] == SubmissionStatus.ACCEPTED.value
            created_at = datetime.fromisoformat(sub['created_at'])
            
            for topic in topics:
                if topic not in topic_stats:
                    topic_stats[topic] = {'success': 0, 'total': 0, 'recent': []}
                
                topic_stats[topic]['total'] += 1
                if is_success:
                    topic_stats[topic]['success'] += 1
                
                topic_stats[topic]['recent'].append({
                    'is_success': is_success,
                    'date': created_at
                })
        
        # Calculate mastery levels
        mastery = {}
        for topic, stats in topic_stats.items():
            if stats['total'] == 0:
                mastery[topic] = 0.0
                continue
            
            # Base mastery from success rate
            base_mastery = stats['success'] / stats['total']
            
            # Apply recency boost (recent successes count more)
            recent_submissions = sorted(stats['recent'], key=lambda x: x['date'], reverse=True)[:5]
            recent_success_rate = sum(1 for s in recent_submissions if s['is_success']) / len(recent_submissions)
            
            # Weighted average: 60% overall, 40% recent
            mastery[topic] = min(1.0, base_mastery * 0.6 + recent_success_rate * 0.4)
        
        return mastery
    
    def _get_question_topics(self, question_key: str) -> List[str]:
        """
        Get normalized topics for a question from roadmap collection.
        
        Topics are normalized to ensure consistency across the system.
        """
        try:
            question = self.roadmap_collection.get(question_key)
            if question and 'topics' in question:
                # Normalize topics for consistency
                return normalize_topics(question['topics'])
        except:
            pass
        return []
    
    def _calculate_streak(self, submissions: List[Dict]) -> int:
        """Calculate current streak from submission dates."""
        if not submissions:
            return 0
        
        # Get unique submission dates
        dates = set()
        for sub in submissions:
            created = datetime.fromisoformat(sub['created_at'])
            dates.add(created.date())
        
        sorted_dates = sorted(dates, reverse=True)
        
        if not sorted_dates:
            return 0
        
        # Check if streak is active (today or yesterday)
        today = date.today()
        most_recent = sorted_dates[0]
        
        if most_recent < today - timedelta(days=1):
            return 0  # Streak broken
        
        # Count consecutive days
        streak = 0
        current_date = today
        
        for submission_date in sorted_dates:
            if submission_date == current_date or submission_date == current_date - timedelta(days=1):
                streak += 1
                current_date = submission_date - timedelta(days=1)
            else:
                break
        
        return streak

