from typing import List, Optional, Dict, Any
from datetime import datetime
from arango.database import StandardDatabase

from app.models.question import (
    QuestionCreate, QuestionInDB, QuestionUpdate, 
    DifficultyLevel, QuestionType, SkillCategory
)

class QuestionCRUD:
    """Question database operations."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.collection = db.collection('questions')
    
    def create_question(self, question: QuestionCreate, created_by: Optional[str] = None) -> QuestionInDB:
        """Create a new question."""
        now = datetime.utcnow()
        
        # Prepare content based on question type
        content = {}
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            content = {
                "options": [opt.model_dump() for opt in (question.options or [])],
                "correct_answer_key": question.correct_answer_key,
                "explanation": question.explanation
            }
        elif question.question_type == QuestionType.CODING:
            content = {
                "examples": [ex.model_dump() for ex in (question.examples or [])],
                "constraints": question.constraints or [],
                "function_signature": question.function_signature or {},
                "template_code": question.template_code or {},
                "test_cases": question.test_cases or []
            }
        elif question.question_type == QuestionType.TRUE_FALSE:
            content = {
                "correct_answer": question.correct_answer,
                "explanation": question.explanation
            }
        
        question_data = {
            "title": question.title,
            "description": question.description,
            "difficulty": question.difficulty.value,
            "question_type": question.question_type.value,
            "skill_categories": [cat.value for cat in question.skill_categories],
            "estimated_time_minutes": question.estimated_time_minutes,
            "points": question.points,
            "content": content,
            "created_at": now.isoformat(),
            "created_by": created_by
        }
        
        result = self.collection.insert(question_data, return_new=True)
        new_question_data = result['new'].copy()
        new_question_data['created_at'] = now
        return QuestionInDB(**new_question_data)
    
    def get_question_by_key(self, key: str) -> Optional[QuestionInDB]:
        """Retrieve question by document key."""
        try:
            question_data = self.collection.get(key)
            if question_data:
                question_data = question_data.copy()
                question_data['_key'] = key
                
                # Convert datetime strings
                if 'created_at' in question_data and isinstance(question_data['created_at'], str):
                    question_data['created_at'] = datetime.fromisoformat(question_data['created_at'].replace('Z', '+00:00'))
                if 'updated_at' in question_data and isinstance(question_data['updated_at'], str):
                    question_data['updated_at'] = datetime.fromisoformat(question_data['updated_at'].replace('Z', '+00:00'))
                    
                return QuestionInDB(**question_data)
            return None
        except Exception:
            return None
    
    def get_questions_by_criteria(
        self, 
        difficulty: Optional[DifficultyLevel] = None,
        question_type: Optional[QuestionType] = None,
        skill_categories: Optional[List[SkillCategory]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[QuestionInDB]:
        """Get questions by filtering criteria."""
        
        # Build AQL query
        query_parts = ["FOR q IN questions"]
        bind_vars = {}
        filters = []
        
        if difficulty:
            filters.append("q.difficulty == @difficulty")
            bind_vars['difficulty'] = difficulty.value
            
        if question_type:
            filters.append("q.question_type == @question_type")
            bind_vars['question_type'] = question_type.value
            
        if skill_categories:
            # Check if any of the question's skill categories match the requested ones
            category_values = [cat.value for cat in skill_categories]
            filters.append("LENGTH(INTERSECTION(q.skill_categories, @skill_categories)) > 0")
            bind_vars['skill_categories'] = category_values
        
        if filters:
            query_parts.append("FILTER " + " AND ".join(filters))
        
        query_parts.extend([
            "LIMIT @offset, @limit",
            "RETURN q"
        ])
        
        bind_vars.update({'limit': limit, 'offset': offset})
        
        query = " ".join(query_parts)
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        
        questions = []
        for question_data in cursor:
            question_data = question_data.copy()
            # Convert datetime strings
            if 'created_at' in question_data and isinstance(question_data['created_at'], str):
                question_data['created_at'] = datetime.fromisoformat(question_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in question_data and isinstance(question_data['updated_at'], str):
                question_data['updated_at'] = datetime.fromisoformat(question_data['updated_at'].replace('Z', '+00:00'))
            
            questions.append(QuestionInDB(**question_data))
        
        return questions
    
    def get_random_assessment_questions(
        self, 
        difficulty: DifficultyLevel,
        count: int = 12
    ) -> List[QuestionInDB]:
        """Get random questions for assessment based on difficulty."""
        
        # Get questions that are appropriate for assessment
        query = """
        FOR q IN questions
        FILTER q.difficulty == @difficulty
        AND q.question_type IN ["MULTIPLE_CHOICE", "TRUE_FALSE"]
        AND LENGTH(q.skill_categories) > 0
        SORT RAND()
        LIMIT @count
        RETURN q
        """
        
        bind_vars = {
            'difficulty': difficulty.value,
            'count': count
        }
        
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        
        questions = []
        for question_data in cursor:
            question_data = question_data.copy()
            # Convert datetime strings
            if 'created_at' in question_data and isinstance(question_data['created_at'], str):
                question_data['created_at'] = datetime.fromisoformat(question_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in question_data and isinstance(question_data['updated_at'], str):
                question_data['updated_at'] = datetime.fromisoformat(question_data['updated_at'].replace('Z', '+00:00'))
            
            questions.append(QuestionInDB(**question_data))
        
        return questions
    
    def get_balanced_assessment_questions(
        self, 
        claimed_skill_level: str,
        total_count: int = 12
    ) -> List[QuestionInDB]:
        """
        Get a balanced set of assessment questions across difficulty levels and skill categories.
        
        Distribution based on claimed skill level:
        - BEGINNER: 60% Beginner, 30% Intermediate, 10% Advanced
        - INTERMEDIATE: 20% Beginner, 60% Intermediate, 20% Advanced  
        - PROFESSIONAL: 10% Beginner, 30% Intermediate, 60% Advanced
        """
        
        try:
            # Define difficulty distribution based on claimed skill level
            distributions = {
                "BEGINNER": {
                    DifficultyLevel.BEGINNER: 0.6,    # 7 questions
                    DifficultyLevel.INTERMEDIATE: 0.3, # 4 questions
                    DifficultyLevel.ADVANCED: 0.1     # 1 question
                },
                "INTERMEDIATE": {
                    DifficultyLevel.BEGINNER: 0.2,    # 2 questions
                    DifficultyLevel.INTERMEDIATE: 0.6, # 7 questions
                    DifficultyLevel.ADVANCED: 0.2     # 3 questions
                },
                "PROFESSIONAL": {
                    DifficultyLevel.BEGINNER: 0.1,    # 1 question
                    DifficultyLevel.INTERMEDIATE: 0.3, # 4 questions
                    DifficultyLevel.ADVANCED: 0.6     # 7 questions
                }
            }
            
            # Get distribution for the claimed skill level
            distribution = distributions.get(claimed_skill_level, distributions["INTERMEDIATE"])
            
            # Calculate question counts for each difficulty
            question_counts = {}
            remaining_count = total_count
            
            for difficulty, ratio in distribution.items():
                count = round(total_count * ratio)
                question_counts[difficulty] = count
                remaining_count -= count
            
            # Adjust for rounding errors by adding remaining to the most appropriate level
            if remaining_count != 0:
                primary_level = max(distribution.keys(), key=lambda k: distribution[k])
                question_counts[primary_level] += remaining_count
            
            # Get questions for each difficulty level with skill category diversity
            all_questions = []
            
            for difficulty, count in question_counts.items():
                if count > 0:
                    questions = self._get_diverse_questions_by_difficulty(difficulty, count)
                    all_questions.extend(questions)
            
            # Shuffle the final list to randomize order
            import random
            random.shuffle(all_questions)
            
            return all_questions[:total_count]
            
        except Exception as e:
            print(f"Error in get_balanced_assessment_questions: {e}")
            # Fallback to simple random selection
            difficulty_map = {
                "BEGINNER": DifficultyLevel.BEGINNER,
                "INTERMEDIATE": DifficultyLevel.INTERMEDIATE,
                "PROFESSIONAL": DifficultyLevel.ADVANCED
            }
            fallback_difficulty = difficulty_map.get(claimed_skill_level, DifficultyLevel.INTERMEDIATE)
            return self.get_random_assessment_questions(fallback_difficulty, total_count)
    
    def _get_diverse_questions_by_difficulty(
        self, 
        difficulty: DifficultyLevel, 
        count: int
    ) -> List[QuestionInDB]:
        """Get questions for a specific difficulty with skill category diversity."""
        
        # Query to get questions grouped by skill categories for diversity
        query = """
        FOR q IN questions
        FILTER q.difficulty == @difficulty
        AND q.question_type IN ["MULTIPLE_CHOICE", "TRUE_FALSE"]
        AND LENGTH(q.skill_categories) > 0
        LET primary_category = q.skill_categories[0]
        COLLECT category = primary_category INTO category_questions
        RETURN {
            category: category,
            questions: category_questions[*].q
        }
        """
        
        bind_vars = {'difficulty': difficulty.value}
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        
        # Collect questions by category
        category_groups = {}
        for group in cursor:
            category = group['category']
            questions = group['questions']
            # Filter out None questions and properly extract question data
            valid_questions = []
            for q in questions:
                if q is not None:
                    # Ensure the question data has the right structure
                    if '_key' in q:
                        q['_key'] = q['_key']  # Ensure _key is preserved
                    valid_questions.append(q)
            
            if valid_questions:
                category_groups[category] = valid_questions
        
        print(f"Found {len(category_groups)} categories for {difficulty.value}: {list(category_groups.keys())}")
        
        # Select questions with round-robin approach for diversity
        selected_questions = []
        categories = list(category_groups.keys())
        category_index = 0
        
        attempts = 0
        max_attempts = count * 10  # Prevent infinite loops
        
        while len(selected_questions) < count and attempts < max_attempts:
            attempts += 1
            
            if not categories:
                break
                
            current_category = categories[category_index % len(categories)]
            
            if current_category in category_groups and category_groups[current_category]:
                # Randomly select a question from this category
                import random
                question_data = random.choice(category_groups[current_category])
                
                # Skip if question_data is None
                if not question_data:
                    continue
                
                # Remove to avoid duplicates
                category_groups[current_category].remove(question_data)
                
                # Convert to QuestionInDB
                question_data = question_data.copy()
                
                # Convert datetime strings
                if 'created_at' in question_data and isinstance(question_data['created_at'], str):
                    question_data['created_at'] = datetime.fromisoformat(question_data['created_at'].replace('Z', '+00:00'))
                if 'updated_at' in question_data and isinstance(question_data['updated_at'], str):
                    question_data['updated_at'] = datetime.fromisoformat(question_data['updated_at'].replace('Z', '+00:00'))
                
                try:
                    question = QuestionInDB(**question_data)
                    selected_questions.append(question)
                except Exception as e:
                    print(f"Error creating QuestionInDB: {e}")
                    print(f"Question data keys: {list(question_data.keys()) if question_data else 'None'}")
                    continue
                
                # If category is empty, remove it
                if not category_groups[current_category]:
                    del category_groups[current_category]
                    categories = list(category_groups.keys())
                    if category_index >= len(categories) and categories:
                        category_index = 0
            
            category_index += 1
        
        # If we still need more questions, get them randomly from remaining questions
        if len(selected_questions) < count:
            remaining_needed = count - len(selected_questions)
            additional_questions = self.get_random_assessment_questions(difficulty, remaining_needed)
            
            # Avoid duplicates
            selected_keys = {q.key for q in selected_questions}
            for q in additional_questions:
                if q.key not in selected_keys:
                    selected_questions.append(q)
                    if len(selected_questions) >= count:
                        break
        
        return selected_questions[:count]
    
    def update_question(self, key: str, question_update: QuestionUpdate) -> Optional[QuestionInDB]:
        """Update question information."""
        now = datetime.utcnow()
        update_data = {"updated_at": now.isoformat()}
        
        # Only update provided fields
        update_fields = question_update.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field == 'skill_categories' and value is not None:
                update_data[field] = [cat.value for cat in value]
            elif field in ['difficulty'] and value is not None:
                update_data[field] = value.value
            elif value is not None:
                update_data[field] = value
        
        result = self.collection.update(key, update_data, return_new=True)
        if result:
            updated_question_data = result['new'].copy()
            updated_question_data['updated_at'] = now
            
            # Convert created_at if it's a string
            if 'created_at' in updated_question_data and isinstance(updated_question_data['created_at'], str):
                updated_question_data['created_at'] = datetime.fromisoformat(updated_question_data['created_at'].replace('Z', '+00:00'))
                
            return QuestionInDB(**updated_question_data)
        return None
    
    def delete_question(self, key: str) -> bool:
        """Delete a question."""
        try:
            self.collection.delete(key)
            return True
        except Exception:
            return False
    
    def get_questions_count(self) -> int:
        """Get total number of questions."""
        query = "FOR q IN questions COLLECT WITH COUNT INTO length RETURN length"
        cursor = self.db.aql.execute(query)
        result = list(cursor)
        return result[0] if result else 0
