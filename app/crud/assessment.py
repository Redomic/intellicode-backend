from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from arango.database import StandardDatabase
import statistics

from app.models.assessment import (
    AssessmentCreate, AssessmentInDB, AssessmentUpdate, 
    UserAnswerCreate, UserAnswer, AssessmentResult,
    AssessmentStatus, AssessmentType, RankingCalculationData
)
from app.models.question import DifficultyLevel

class AssessmentCRUD:
    """Assessment database operations."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.collection = db.collection('assessments')
        
        # Base rankings for different skill levels
        self.BASE_RANKINGS = {
            "BEGINNER": 600,
            "INTERMEDIATE": 1000,
            "PROFESSIONAL": 1600
        }
    
    def create_assessment(self, assessment: AssessmentCreate) -> AssessmentInDB:
        """Create a new assessment."""
        now = datetime.utcnow()
        
        assessment_data = {
            "user_key": assessment.user_key,
            "assessment_type": assessment.assessment_type.value,
            "total_questions": assessment.total_questions,
            "questions_answered": assessment.questions_answered,
            "status": assessment.status.value,
            "question_keys": assessment.question_keys,
            "user_answers": [],
            "total_points_possible": 0,
            "total_points_earned": 0,
            "accuracy_percentage": 0.0,
            "average_time_per_question": 0.0,
            "skill_performance": {},
            "started_at": now.isoformat(),
            "created_at": now.isoformat()
        }
        
        result = self.collection.insert(assessment_data, return_new=True)
        new_assessment_data = result['new'].copy()
        new_assessment_data['started_at'] = now
        new_assessment_data['created_at'] = now
        return AssessmentInDB(**new_assessment_data)
    
    def get_assessment_by_key(self, key: str) -> Optional[AssessmentInDB]:
        """Retrieve assessment by document key."""
        try:
            assessment_data = self.collection.get(key)
            if assessment_data:
                assessment_data = assessment_data.copy()
                assessment_data['_key'] = key
                
                # Convert datetime strings
                for date_field in ['started_at', 'completed_at', 'created_at', 'updated_at']:
                    if date_field in assessment_data and isinstance(assessment_data[date_field], str):
                        assessment_data[date_field] = datetime.fromisoformat(assessment_data[date_field].replace('Z', '+00:00'))
                
                # Convert user_answers to UserAnswer objects
                if 'user_answers' in assessment_data:
                    user_answers = []
                    for answer_data in assessment_data['user_answers']:
                        if isinstance(answer_data.get('submitted_at'), str):
                            answer_data['submitted_at'] = datetime.fromisoformat(answer_data['submitted_at'].replace('Z', '+00:00'))
                        user_answers.append(UserAnswer(**answer_data))
                    assessment_data['user_answers'] = user_answers
                    
                return AssessmentInDB(**assessment_data)
            return None
        except Exception as e:
            print(f"Error retrieving assessment: {e}")
            return None
    
    def add_user_answer(self, assessment_key: str, answer: UserAnswerCreate) -> Optional[AssessmentInDB]:
        """Add a user answer to an assessment."""
        now = datetime.utcnow()
        
        # Create UserAnswer with timestamp
        user_answer = UserAnswer(
            **answer.model_dump(),
            submitted_at=now
        )
        
        # Get current assessment
        assessment = self.get_assessment_by_key(assessment_key)
        if not assessment:
            return None
        
        # Add the new answer
        assessment.user_answers.append(user_answer)
        assessment.questions_answered += 1
        
        # Recalculate metrics
        self._recalculate_assessment_metrics(assessment)
        
        # Update in database
        # Serialize user answers properly for database storage
        serialized_answers = []
        for answer in assessment.user_answers:
            answer_dict = answer.model_dump()
            # Convert datetime to string for database storage
            if 'submitted_at' in answer_dict and hasattr(answer_dict['submitted_at'], 'isoformat'):
                answer_dict['submitted_at'] = answer_dict['submitted_at'].isoformat()
            serialized_answers.append(answer_dict)
        
        update_data = {
            "user_answers": serialized_answers,
            "questions_answered": assessment.questions_answered,
            "total_points_earned": assessment.total_points_earned,
            "accuracy_percentage": assessment.accuracy_percentage,
            "average_time_per_question": assessment.average_time_per_question,
            "skill_performance": assessment.skill_performance,
            "updated_at": now.isoformat()
        }
        
        # Check if assessment is complete
        if assessment.questions_answered >= assessment.total_questions:
            update_data["status"] = AssessmentStatus.COMPLETED.value
            update_data["completed_at"] = now.isoformat()
            assessment.status = AssessmentStatus.COMPLETED
            assessment.completed_at = now
        
        # ArangoDB update - merge _key with update data
        try:
            update_document = {"_key": assessment_key}
            update_document.update(update_data)
            result = self.collection.update(update_document, return_new=True)
        except Exception as e:
            print(f"Error updating assessment {assessment_key}: {e}")
            print(f"Update data: {update_data}")
            return None
        if result:
            updated_data = result['new'].copy()
            updated_data['updated_at'] = now
            if assessment.completed_at:
                updated_data['completed_at'] = assessment.completed_at
            
            # Convert datetime fields
            for date_field in ['started_at', 'created_at']:
                if date_field in updated_data and isinstance(updated_data[date_field], str):
                    updated_data[date_field] = datetime.fromisoformat(updated_data[date_field].replace('Z', '+00:00'))
            
            # Convert user_answers back to objects
            user_answers = []
            for answer_data in updated_data['user_answers']:
                if isinstance(answer_data.get('submitted_at'), str):
                    answer_data['submitted_at'] = datetime.fromisoformat(answer_data['submitted_at'].replace('Z', '+00:00'))
                user_answers.append(UserAnswer(**answer_data))
            updated_data['user_answers'] = user_answers
            
            return AssessmentInDB(**updated_data)
        
        return None
    
    def _recalculate_assessment_metrics(self, assessment: AssessmentInDB):
        """Recalculate assessment performance metrics."""
        if not assessment.user_answers:
            return
        
        # Basic metrics
        total_correct = sum(1 for answer in assessment.user_answers if answer.is_correct)
        assessment.accuracy_percentage = (total_correct / len(assessment.user_answers)) * 100
        assessment.total_points_earned = sum(answer.points_earned for answer in assessment.user_answers)
        
        # Calculate total points possible (estimate based on average points per question)
        if assessment.user_answers:
            # Use the points from answered questions to estimate total possible
            avg_points_per_question = 10  # Default assumption
            if any(answer.points_earned > 0 for answer in assessment.user_answers):
                # Calculate based on correct answers
                correct_answers = [answer for answer in assessment.user_answers if answer.is_correct]
                if correct_answers:
                    avg_points_per_question = statistics.mean([answer.points_earned for answer in correct_answers])
            
            assessment.total_points_possible = avg_points_per_question * assessment.total_questions
        
        # Calculate average time
        times = [answer.time_taken_seconds for answer in assessment.user_answers]
        assessment.average_time_per_question = statistics.mean(times) if times else 0.0
        
        # Initialize skill performance tracking
        # This would be enhanced with actual question skill category data
        assessment.skill_performance = {
            "overall": {
                "questions_answered": len(assessment.user_answers),
                "correct_answers": total_correct,
                "accuracy": assessment.accuracy_percentage,
                "average_time": assessment.average_time_per_question
            }
        }
    
    def calculate_expertise_ranking(
        self, 
        assessment: AssessmentInDB, 
        claimed_skill_level: str,
        questions_data: List[Dict[str, Any]] = None
    ) -> RankingCalculationData:
        """Calculate expertise ranking based on assessment performance."""
        
        base_rank = self.BASE_RANKINGS.get(claimed_skill_level, 600)
        
        # Calculate component scores
        accuracy_score = assessment.accuracy_percentage
        
        # Time efficiency score (lower time = higher score, capped at 100)
        expected_time_per_question = 300  # 5 minutes in seconds
        actual_avg_time = assessment.average_time_per_question
        if actual_avg_time > 0:
            time_efficiency = max(0, 100 - ((actual_avg_time - expected_time_per_question) / expected_time_per_question) * 50)
            time_efficiency_score = min(100, time_efficiency)
        else:
            time_efficiency_score = 50  # Default if no time data
        
        # Difficulty bonus based on question complexity
        difficulty_bonus = 0
        if questions_data:
            for question in questions_data:
                if question.get('difficulty') == 'ADVANCED':
                    difficulty_bonus += 10
                elif question.get('difficulty') == 'INTERMEDIATE':
                    difficulty_bonus += 5
        
        # Skill consistency (placeholder - would be calculated from multiple skill categories)
        skill_consistency_score = 75  # Default
        
        # Calculate total score
        total_score = (
            accuracy_score * 0.4 +  # 40% weight on accuracy
            time_efficiency_score * 0.3 +  # 30% weight on speed
            difficulty_bonus * 0.2 +  # 20% weight on difficulty
            skill_consistency_score * 0.1  # 10% weight on consistency
        )
        
        # Calculate final rank
        rank_adjustment = int((total_score - 75) * 8)  # Adjust based on performance above/below 75%
        final_rank = max(100, min(3000, base_rank + rank_adjustment))
        
        return RankingCalculationData(
            base_rank=base_rank,
            accuracy_score=accuracy_score,
            time_efficiency_score=time_efficiency_score,
            difficulty_bonus=difficulty_bonus,
            skill_consistency_score=skill_consistency_score,
            total_score=total_score,
            final_rank=final_rank
        )
    
    def complete_assessment_with_ranking(
        self, 
        assessment_key: str, 
        claimed_skill_level: str,
        previous_rank: Optional[int] = None
    ) -> Optional[AssessmentInDB]:
        """Complete assessment and calculate final ranking."""
        assessment = self.get_assessment_by_key(assessment_key)
        if not assessment:
            return None
        
        # Calculate ranking
        ranking_data = self.calculate_expertise_ranking(assessment, claimed_skill_level)
        
        # Update assessment with ranking
        update_data = {
            "calculated_expertise_rank": ranking_data.final_rank,
            "previous_rank": previous_rank,
            "rank_change": ranking_data.final_rank - (previous_rank or ranking_data.base_rank),
            "status": AssessmentStatus.COMPLETED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # ArangoDB update - merge _key with update data
        try:
            update_document = {"_key": assessment_key}
            update_document.update(update_data)
            result = self.collection.update(update_document, return_new=True)
        except Exception as e:
            print(f"Error updating assessment {assessment_key}: {e}")
            print(f"Update data: {update_data}")
            return None
        if result:
            updated_data = result['new'].copy()
            
            # Convert datetime strings
            for date_field in ['started_at', 'completed_at', 'created_at', 'updated_at']:
                if date_field in updated_data and isinstance(updated_data[date_field], str):
                    updated_data[date_field] = datetime.fromisoformat(updated_data[date_field].replace('Z', '+00:00'))
            
            # Convert user_answers back to objects
            if 'user_answers' in updated_data:
                user_answers = []
                for answer_data in updated_data['user_answers']:
                    if isinstance(answer_data.get('submitted_at'), str):
                        answer_data['submitted_at'] = datetime.fromisoformat(answer_data['submitted_at'].replace('Z', '+00:00'))
                    user_answers.append(UserAnswer(**answer_data))
                updated_data['user_answers'] = user_answers
            
            return AssessmentInDB(**updated_data)
        
        return None
    
    def get_user_assessments(self, user_key: str, limit: int = 10) -> List[AssessmentInDB]:
        """Get assessments for a user."""
        query = """
        FOR a IN assessments
        FILTER a.user_key == @user_key
        SORT a.created_at DESC
        LIMIT @limit
        RETURN a
        """
        
        cursor = self.db.aql.execute(query, bind_vars={'user_key': user_key, 'limit': limit})
        
        assessments = []
        for assessment_data in cursor:
            assessment_data = assessment_data.copy()
            
            # Convert datetime strings
            for date_field in ['started_at', 'completed_at', 'created_at', 'updated_at']:
                if date_field in assessment_data and isinstance(assessment_data[date_field], str):
                    assessment_data[date_field] = datetime.fromisoformat(assessment_data[date_field].replace('Z', '+00:00'))
            
            # Convert user_answers to objects
            if 'user_answers' in assessment_data:
                user_answers = []
                for answer_data in assessment_data['user_answers']:
                    if isinstance(answer_data.get('submitted_at'), str):
                        answer_data['submitted_at'] = datetime.fromisoformat(answer_data['submitted_at'].replace('Z', '+00:00'))
                    user_answers.append(UserAnswer(**answer_data))
                assessment_data['user_answers'] = user_answers
            
            assessments.append(AssessmentInDB(**assessment_data))
        
        return assessments
    
    def get_user_onboarding_assessments(self, user_key: str) -> List[AssessmentInDB]:
        """Get only onboarding assessments for a user to enforce one-assessment rule."""
        query = """
        FOR a IN assessments
        FILTER a.user_key == @user_key AND a.assessment_type == @assessment_type
        SORT a.created_at DESC
        RETURN a
        """
        
        cursor = self.db.aql.execute(
            query, 
            bind_vars={
                'user_key': user_key, 
                'assessment_type': AssessmentType.ONBOARDING.value
            }
        )
        
        assessments = []
        for assessment_data in cursor:
            assessment_data = assessment_data.copy()
            
            # Convert datetime strings
            for date_field in ['started_at', 'completed_at', 'created_at', 'updated_at']:
                if date_field in assessment_data and isinstance(assessment_data[date_field], str):
                    assessment_data[date_field] = datetime.fromisoformat(assessment_data[date_field].replace('Z', '+00:00'))
            
            # Convert user_answers to objects
            if 'user_answers' in assessment_data:
                user_answers = []
                for answer_data in assessment_data['user_answers']:
                    if isinstance(answer_data.get('submitted_at'), str):
                        answer_data['submitted_at'] = datetime.fromisoformat(answer_data['submitted_at'].replace('Z', '+00:00'))
                    user_answers.append(UserAnswer(**answer_data))
                assessment_data['user_answers'] = user_answers
            
            assessments.append(AssessmentInDB(**assessment_data))
        
        return assessments
    
    def get_assessment_result(self, assessment_key: str) -> Optional[AssessmentResult]:
        """Get assessment result summary."""
        assessment = self.get_assessment_by_key(assessment_key)
        if not assessment:
            return None
        
        # Analyze skill performance for feedback
        strongest_skills = []
        areas_for_improvement = []
        
        # This would be enhanced with actual skill analysis
        if assessment.accuracy_percentage >= 80:
            strongest_skills.append("Problem Solving")
        if assessment.accuracy_percentage < 60:
            areas_for_improvement.append("Fundamental Concepts")
        if assessment.average_time_per_question > 360:  # 6 minutes
            areas_for_improvement.append("Speed & Efficiency")
        
        return AssessmentResult(
            assessment_key=assessment.key,
            user_key=assessment.user_key,
            assessment_type=AssessmentType(assessment.assessment_type),
            status=AssessmentStatus(assessment.status),
            total_questions=assessment.total_questions,
            questions_answered=assessment.questions_answered,
            accuracy_percentage=assessment.accuracy_percentage,
            total_points_earned=assessment.total_points_earned,
            total_points_possible=assessment.total_points_possible,
            average_time_per_question=assessment.average_time_per_question,
            calculated_expertise_rank=assessment.calculated_expertise_rank or 600,
            previous_rank=assessment.previous_rank,
            rank_change=assessment.rank_change,
            skill_performance=assessment.skill_performance,
            strongest_skills=strongest_skills,
            areas_for_improvement=areas_for_improvement,
            started_at=assessment.started_at,
            completed_at=assessment.completed_at
        )
