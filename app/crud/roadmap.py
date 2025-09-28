from typing import List, Optional, Dict, Any
from datetime import datetime
from arango.database import StandardDatabase

from app.models.roadmap import (
    RoadmapItemCreate, RoadmapItemInDB, RoadmapItemUpdate, 
    RoadmapStats, RoadmapSearchFilters, LeetCodeDifficulty, A2ZDifficulty
)


class RoadmapCRUD:
    """Roadmap database operations for comprehensive LeetCode questions."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.collection = db.collection('roadmap')
    
    def create_roadmap_item(self, roadmap_item: RoadmapItemCreate) -> RoadmapItemInDB:
        """Create a new roadmap item."""
        now = datetime.utcnow()
        
        roadmap_data = {
            # Course identifier
            "course": roadmap_item.course,
            
            # A2Z Striver metadata
            "question_id": roadmap_item.question_id,
            "original_title": roadmap_item.original_title,
            "a2z_step": roadmap_item.a2z_step,
            "a2z_sub_step": roadmap_item.a2z_sub_step,
            "a2z_difficulty": roadmap_item.a2z_difficulty,
            "a2z_topics": roadmap_item.a2z_topics,
            "lc_link": roadmap_item.lc_link,
            "step_number": roadmap_item.step_number,  # Include step number for proper ordering
            
            # LeetCode comprehensive data
            "leetcode_title": roadmap_item.leetcode_title,
            "leetcode_title_slug": roadmap_item.leetcode_title_slug,
            "leetcode_difficulty": roadmap_item.leetcode_difficulty,
            "leetcode_question_id": roadmap_item.leetcode_question_id,
            "is_paid_only": roadmap_item.is_paid_only,
            
            # Problem content
            "problem_statement_html": roadmap_item.problem_statement_html,
            "problem_statement_text": roadmap_item.problem_statement_text,
            
            # Examples and test cases
            "examples": roadmap_item.examples,
            "sample_test_cases": roadmap_item.sample_test_cases,
            "constraints": roadmap_item.constraints,
            
            # Code templates and solutions
            "code_templates": roadmap_item.code_templates,
            "default_code": roadmap_item.default_code,
            
            # Educational content
            "hints": roadmap_item.hints,
            "topics": roadmap_item.topics,
            "company_tags": roadmap_item.company_tags,
            "similar_questions": roadmap_item.similar_questions,
            "follow_up_questions": roadmap_item.follow_up_questions,
            "note_sections": roadmap_item.note_sections,
            
            # Scraping metadata
            "scraping_duration": roadmap_item.scraping_duration,
            "scraped_at": roadmap_item.scraped_at.isoformat() if roadmap_item.scraped_at else None,
            "scraping_success": roadmap_item.scraping_success,
            "scraping_error": roadmap_item.scraping_error,
            
            # Timestamps
            "created_at": now.isoformat(),
        }
        
        result = self.collection.insert(roadmap_data, return_new=True)
        new_roadmap_data = result['new'].copy()
        new_roadmap_data['created_at'] = now
        
        # Convert scraped_at back to datetime if it exists
        if new_roadmap_data.get('scraped_at'):
            new_roadmap_data['scraped_at'] = datetime.fromisoformat(new_roadmap_data['scraped_at'].replace('Z', '+00:00'))
        
        return RoadmapItemInDB(**new_roadmap_data)
    
    def get_roadmap_item_by_key(self, key: str) -> Optional[RoadmapItemInDB]:
        """Retrieve roadmap item by document key."""
        try:
            roadmap_data = self.collection.get(key)
            if roadmap_data:
                roadmap_data = roadmap_data.copy()
                roadmap_data['_key'] = key
                
                # Convert datetime strings
                if 'created_at' in roadmap_data and isinstance(roadmap_data['created_at'], str):
                    roadmap_data['created_at'] = datetime.fromisoformat(roadmap_data['created_at'].replace('Z', '+00:00'))
                if 'updated_at' in roadmap_data and isinstance(roadmap_data['updated_at'], str):
                    roadmap_data['updated_at'] = datetime.fromisoformat(roadmap_data['updated_at'].replace('Z', '+00:00'))
                if 'scraped_at' in roadmap_data and isinstance(roadmap_data['scraped_at'], str):
                    roadmap_data['scraped_at'] = datetime.fromisoformat(roadmap_data['scraped_at'].replace('Z', '+00:00'))
                    
                return RoadmapItemInDB(**roadmap_data)
            return None
        except Exception:
            return None
    
    def get_roadmap_item_by_question_id(self, question_id: str) -> Optional[RoadmapItemInDB]:
        """Retrieve roadmap item by question_id."""
        try:
            query = "FOR r IN roadmap FILTER r.question_id == @question_id RETURN r"
            cursor = self.db.aql.execute(query, bind_vars={'question_id': question_id})
            
            results = list(cursor)
            if results:
                roadmap_data = results[0].copy()
                
                # Convert datetime strings
                if 'created_at' in roadmap_data and isinstance(roadmap_data['created_at'], str):
                    roadmap_data['created_at'] = datetime.fromisoformat(roadmap_data['created_at'].replace('Z', '+00:00'))
                if 'updated_at' in roadmap_data and isinstance(roadmap_data['updated_at'], str):
                    roadmap_data['updated_at'] = datetime.fromisoformat(roadmap_data['updated_at'].replace('Z', '+00:00'))
                if 'scraped_at' in roadmap_data and isinstance(roadmap_data['scraped_at'], str):
                    roadmap_data['scraped_at'] = datetime.fromisoformat(roadmap_data['scraped_at'].replace('Z', '+00:00'))
                
                return RoadmapItemInDB(**roadmap_data)
            return None
        except Exception:
            return None
    
    def get_roadmap_items_by_filters(
        self, 
        filters: RoadmapSearchFilters,
        limit: int = 50,
        offset: int = 0
    ) -> List[RoadmapItemInDB]:
        """Get roadmap items by filtering criteria."""
        
        # Build AQL query
        query_parts = ["FOR r IN roadmap"]
        bind_vars = {}
        filter_conditions = []
        
        if filters.a2z_step:
            filter_conditions.append("r.a2z_step == @a2z_step")
            bind_vars['a2z_step'] = filters.a2z_step
            
        if filters.a2z_sub_step:
            filter_conditions.append("r.a2z_sub_step == @a2z_sub_step")
            bind_vars['a2z_sub_step'] = filters.a2z_sub_step
            
        if filters.a2z_difficulty is not None:
            filter_conditions.append("r.a2z_difficulty == @a2z_difficulty")
            bind_vars['a2z_difficulty'] = filters.a2z_difficulty
            
        if filters.leetcode_difficulty:
            filter_conditions.append("r.leetcode_difficulty == @leetcode_difficulty")
            bind_vars['leetcode_difficulty'] = filters.leetcode_difficulty.value
            
        if filters.is_paid_only is not None:
            filter_conditions.append("r.is_paid_only == @is_paid_only")
            bind_vars['is_paid_only'] = filters.is_paid_only
            
        if filters.scraping_success is not None:
            filter_conditions.append("r.scraping_success == @scraping_success")
            bind_vars['scraping_success'] = filters.scraping_success
            
        if filters.has_examples is not None:
            if filters.has_examples:
                filter_conditions.append("LENGTH(r.examples) > 0")
            else:
                filter_conditions.append("LENGTH(r.examples) == 0")
                
        if filters.has_hints is not None:
            if filters.has_hints:
                filter_conditions.append("LENGTH(r.hints) > 0")
            else:
                filter_conditions.append("LENGTH(r.hints) == 0")
        
        if filters.topics:
            filter_conditions.append("LENGTH(INTERSECTION(r.topics, @topics)) > 0")
            bind_vars['topics'] = filters.topics
            
        if filters.company_tags:
            filter_conditions.append("LENGTH(INTERSECTION(r.company_tags, @company_tags)) > 0")
            bind_vars['company_tags'] = filters.company_tags
        
        if filter_conditions:
            query_parts.append("FILTER " + " AND ".join(filter_conditions))
        
        query_parts.extend([
            "LIMIT @offset, @limit",
            "RETURN r"
        ])
        
        bind_vars.update({'limit': limit, 'offset': offset})
        
        query = " ".join(query_parts)
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        
        roadmap_items = []
        for roadmap_data in cursor:
            roadmap_data = roadmap_data.copy()
            
            # Convert datetime strings
            if 'created_at' in roadmap_data and isinstance(roadmap_data['created_at'], str):
                roadmap_data['created_at'] = datetime.fromisoformat(roadmap_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in roadmap_data and isinstance(roadmap_data['updated_at'], str):
                roadmap_data['updated_at'] = datetime.fromisoformat(roadmap_data['updated_at'].replace('Z', '+00:00'))
            if 'scraped_at' in roadmap_data and isinstance(roadmap_data['scraped_at'], str):
                roadmap_data['scraped_at'] = datetime.fromisoformat(roadmap_data['scraped_at'].replace('Z', '+00:00'))
            
            roadmap_items.append(RoadmapItemInDB(**roadmap_data))
        
        return roadmap_items
    
    def get_user_roadmap_progress(self, user_key: str) -> List:
        """Get user progress for all roadmaps."""
        from app.models.roadmap import RoadmapProgress
        
        # Get all unique courses
        courses_query = """
        FOR r IN roadmap
        COLLECT course = r.course
        RETURN {
            course: course,
            total_questions: LENGTH(
                FOR item IN roadmap
                FILTER item.course == course
                RETURN 1
            )
        }
        """
        
        courses_cursor = self.db.aql.execute(courses_query)
        courses_data = list(courses_cursor)
        
        roadmap_progress = []
        
        for course_info in courses_data:
            course = course_info['course']
            total_questions = course_info['total_questions']
            
            # Get completed questions for this user and course
            completed_query = """
            FOR session IN problem_solving_sessions
            FILTER session.user_key == @user_key AND session.is_correct == true
            LET roadmap_item = (
                FOR r IN roadmap
                FILTER r._key == session.question_key AND r.course == @course
                RETURN r
            )[0]
            FILTER roadmap_item != null
            COLLECT WITH COUNT INTO completed_count
            RETURN completed_count
            """
            
            completed_cursor = self.db.aql.execute(
                completed_query, 
                bind_vars={'user_key': user_key, 'course': course}
            )
            completed_result = list(completed_cursor)
            completed_questions = completed_result[0] if completed_result else 0
            
            # Calculate progress percentage
            progress_percentage = (completed_questions / total_questions * 100) if total_questions > 0 else 0
            
            # Get last activity for this course
            last_activity_query = """
            FOR session IN problem_solving_sessions
            FILTER session.user_key == @user_key AND session.is_correct == true
            LET roadmap_item = (
                FOR r IN roadmap
                FILTER r._key == session.question_key AND r.course == @course
                RETURN r
            )[0]
            FILTER roadmap_item != null
            SORT session.created_at DESC
            LIMIT 1
            RETURN session.created_at
            """
            
            last_activity_cursor = self.db.aql.execute(
                last_activity_query,
                bind_vars={'user_key': user_key, 'course': course}
            )
            last_activity_result = list(last_activity_cursor)
            last_activity = None
            if last_activity_result and last_activity_result[0]:
                if isinstance(last_activity_result[0], str):
                    last_activity = datetime.fromisoformat(last_activity_result[0].replace('Z', '+00:00'))
                else:
                    last_activity = last_activity_result[0]
            
            # Generate course display name
            course_name = self._generate_course_display_name(course)
            
            progress = RoadmapProgress(
                course=course,
                course_name=course_name,
                total_questions=total_questions,
                completed_questions=completed_questions,
                progress_percentage=round(progress_percentage, 1),
                last_activity=last_activity
            )
            
            roadmap_progress.append(progress)
        
        return roadmap_progress
    
    def _generate_course_display_name(self, course: str) -> str:
        """Generate a human-readable course name from course identifier."""
        if course == "strivers-a2z":
            return "Striver's A2Z DSA Course"
        
        # For future courses, you can add more mappings here
        # Convert snake_case or kebab-case to Title Case
        words = course.replace('-', ' ').replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)
    
    def get_roadmap_by_step(self, step: str, sub_step: Optional[str] = None) -> List[RoadmapItemInDB]:
        """Get all roadmap items for a specific step or sub-step."""
        filters = RoadmapSearchFilters(a2z_step=step, a2z_sub_step=sub_step)
        return self.get_roadmap_items_by_filters(filters, limit=1000)
    
    def update_roadmap_item(self, key: str, roadmap_update: RoadmapItemUpdate) -> Optional[RoadmapItemInDB]:
        """Update roadmap item information."""
        now = datetime.utcnow()
        update_data = {"updated_at": now.isoformat()}
        
        # Only update provided fields
        update_fields = roadmap_update.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if value is not None:
                if field == 'scraped_at' and isinstance(value, datetime):
                    update_data[field] = value.isoformat()
                else:
                    update_data[field] = value
        
        # Create update document with key
        update_document = {"_key": key}
        update_document.update(update_data)
        result = self.collection.update(update_document, return_new=True)
        if result:
            updated_roadmap_data = result['new'].copy()
            updated_roadmap_data['updated_at'] = now
            
            # Convert datetime strings
            if 'created_at' in updated_roadmap_data and isinstance(updated_roadmap_data['created_at'], str):
                updated_roadmap_data['created_at'] = datetime.fromisoformat(updated_roadmap_data['created_at'].replace('Z', '+00:00'))
            if 'scraped_at' in updated_roadmap_data and isinstance(updated_roadmap_data['scraped_at'], str):
                updated_roadmap_data['scraped_at'] = datetime.fromisoformat(updated_roadmap_data['scraped_at'].replace('Z', '+00:00'))
                
            return RoadmapItemInDB(**updated_roadmap_data)
        return None
    
    def upsert_roadmap_item(self, roadmap_item: RoadmapItemCreate) -> RoadmapItemInDB:
        """Create or update a roadmap item based on question_id."""
        existing_item = self.get_roadmap_item_by_question_id(roadmap_item.question_id)
        
        if existing_item:
            # Update existing item
            update_data = RoadmapItemUpdate(**roadmap_item.model_dump())
            updated_item = self.update_roadmap_item(existing_item.key, update_data)
            return updated_item or existing_item
        else:
            # Create new item
            return self.create_roadmap_item(roadmap_item)
    
    def delete_roadmap_item(self, key: str) -> bool:
        """Delete a roadmap item."""
        try:
            self.collection.delete(key)
            return True
        except Exception:
            return False
    
    def get_roadmap_stats(self) -> RoadmapStats:
        """Get comprehensive statistics about the roadmap collection."""
        
        # Basic counts
        total_query = "FOR r IN roadmap COLLECT WITH COUNT INTO total RETURN total"
        total_result = list(self.db.aql.execute(total_query))
        total_questions = total_result[0] if total_result else 0
        
        success_query = "FOR r IN roadmap FILTER r.scraping_success == true COLLECT WITH COUNT INTO success RETURN success"
        success_result = list(self.db.aql.execute(success_query))
        successfully_scraped = success_result[0] if success_result else 0
        
        failed_scrapes = total_questions - successfully_scraped
        success_rate = (successfully_scraped / total_questions * 100) if total_questions > 0 else 0
        
        # Difficulty distribution
        difficulty_query = """
        FOR r IN roadmap
        COLLECT difficulty = r.leetcode_difficulty WITH COUNT INTO count
        RETURN {difficulty: difficulty, count: count}
        """
        difficulty_cursor = self.db.aql.execute(difficulty_query)
        difficulty_distribution = {item['difficulty'] or 'Unknown': item['count'] for item in difficulty_cursor}
        
        # Content statistics
        content_query = """
        FOR r IN roadmap
        FILTER r.scraping_success == true
        RETURN {
            examples_count: LENGTH(r.examples),
            test_cases_count: LENGTH(r.sample_test_cases),
            hints_count: LENGTH(r.hints),
            topics_count: LENGTH(r.topics)
        }
        """
        content_cursor = self.db.aql.execute(content_query)
        content_results = list(content_cursor)
        
        total_examples = sum(item['examples_count'] for item in content_results)
        total_test_cases = sum(item['test_cases_count'] for item in content_results)
        total_hints = sum(item['hints_count'] for item in content_results)
        total_topics = sum(item['topics_count'] for item in content_results)
        
        # Steps coverage
        steps_query = "FOR r IN roadmap COLLECT step = r.a2z_step RETURN step"
        steps_cursor = self.db.aql.execute(steps_query)
        steps_covered = [step for step in steps_cursor if step]
        
        sub_steps_query = "FOR r IN roadmap COLLECT sub_step = r.a2z_sub_step RETURN sub_step"
        sub_steps_cursor = self.db.aql.execute(sub_steps_query)
        sub_steps_covered = [sub_step for sub_step in sub_steps_cursor if sub_step]
        
        # Last scraped and average duration
        last_scraped_query = """
        FOR r IN roadmap
        FILTER r.scraped_at != null
        SORT r.scraped_at DESC
        LIMIT 1
        RETURN r.scraped_at
        """
        last_scraped_cursor = self.db.aql.execute(last_scraped_query)
        last_scraped_results = list(last_scraped_cursor)
        last_scraped = None
        if last_scraped_results and last_scraped_results[0]:
            last_scraped = datetime.fromisoformat(last_scraped_results[0].replace('Z', '+00:00'))
        
        duration_query = """
        FOR r IN roadmap
        FILTER r.scraping_duration != null AND r.scraping_duration > 0
        RETURN r.scraping_duration
        """
        duration_cursor = self.db.aql.execute(duration_query)
        durations = list(duration_cursor)
        average_scraping_duration = sum(durations) / len(durations) if durations else None
        
        return RoadmapStats(
            total_questions=total_questions,
            successfully_scraped=successfully_scraped,
            failed_scrapes=failed_scrapes,
            success_rate=success_rate,
            difficulty_distribution=difficulty_distribution,
            total_examples=total_examples,
            total_test_cases=total_test_cases,
            total_hints=total_hints,
            total_topics=total_topics,
            steps_covered=steps_covered,
            sub_steps_covered=sub_steps_covered,
            last_scraped=last_scraped,
            average_scraping_duration=average_scraping_duration
        )
    
    def get_roadmap_count(self) -> int:
        """Get total number of roadmap items."""
        query = "FOR r IN roadmap COLLECT WITH COUNT INTO length RETURN length"
        cursor = self.db.aql.execute(query)
        result = list(cursor)
        return result[0] if result else 0
    
    def clear_failed_scrapes(self) -> int:
        """Remove all failed scraping attempts to retry them."""
        query = """
        FOR r IN roadmap
        FILTER r.scraping_success == false
        REMOVE r IN roadmap
        """
        cursor = self.db.aql.execute(query)
        # Return number of documents removed
        return len(list(cursor))
    
    def get_questions_without_content(self, limit: int = 100) -> List[RoadmapItemInDB]:
        """Get questions that failed scraping or have minimal content."""
        query = """
        FOR r IN roadmap
        FILTER r.scraping_success == false OR 
               r.problem_statement_text == null OR 
               LENGTH(r.examples) == 0
        LIMIT @limit
        RETURN r
        """
        
        cursor = self.db.aql.execute(query, bind_vars={'limit': limit})
        
        roadmap_items = []
        for roadmap_data in cursor:
            roadmap_data = roadmap_data.copy()
            
            # Convert datetime strings
            if 'created_at' in roadmap_data and isinstance(roadmap_data['created_at'], str):
                roadmap_data['created_at'] = datetime.fromisoformat(roadmap_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in roadmap_data and isinstance(roadmap_data['updated_at'], str):
                roadmap_data['updated_at'] = datetime.fromisoformat(roadmap_data['updated_at'].replace('Z', '+00:00'))
            if 'scraped_at' in roadmap_data and isinstance(roadmap_data['scraped_at'], str):
                roadmap_data['scraped_at'] = datetime.fromisoformat(roadmap_data['scraped_at'].replace('Z', '+00:00'))
            
            roadmap_items.append(RoadmapItemInDB(**roadmap_data))
        
        return roadmap_items
    
    def get_user_roadmap_progress(self, user_key: str) -> List:
        """Get user progress for all roadmaps."""
        from app.models.roadmap import RoadmapProgress
        
        # Get all unique courses
        courses_query = """
        FOR r IN roadmap
        COLLECT course = r.course
        RETURN {
            course: course,
            total_questions: LENGTH(
                FOR item IN roadmap
                FILTER item.course == course
                RETURN 1
            )
        }
        """
        
        courses_cursor = self.db.aql.execute(courses_query)
        courses_data = list(courses_cursor)
        
        roadmap_progress = []
        
        for course_info in courses_data:
            course = course_info['course']
            total_questions = course_info['total_questions']
            
            # Get completed questions for this user and course
            completed_query = """
            FOR session IN problem_solving_sessions
            FILTER session.user_key == @user_key AND session.is_correct == true
            LET roadmap_item = (
                FOR r IN roadmap
                FILTER r._key == session.question_key AND r.course == @course
                RETURN r
            )[0]
            FILTER roadmap_item != null
            COLLECT WITH COUNT INTO completed_count
            RETURN completed_count
            """
            
            completed_cursor = self.db.aql.execute(
                completed_query, 
                bind_vars={'user_key': user_key, 'course': course}
            )
            completed_result = list(completed_cursor)
            completed_questions = completed_result[0] if completed_result else 0
            
            # Calculate progress percentage
            progress_percentage = (completed_questions / total_questions * 100) if total_questions > 0 else 0
            
            # Get last activity for this course
            last_activity_query = """
            FOR session IN problem_solving_sessions
            FILTER session.user_key == @user_key AND session.is_correct == true
            LET roadmap_item = (
                FOR r IN roadmap
                FILTER r._key == session.question_key AND r.course == @course
                RETURN r
            )[0]
            FILTER roadmap_item != null
            SORT session.created_at DESC
            LIMIT 1
            RETURN session.created_at
            """
            
            last_activity_cursor = self.db.aql.execute(
                last_activity_query,
                bind_vars={'user_key': user_key, 'course': course}
            )
            last_activity_result = list(last_activity_cursor)
            last_activity = None
            if last_activity_result and last_activity_result[0]:
                if isinstance(last_activity_result[0], str):
                    last_activity = datetime.fromisoformat(last_activity_result[0].replace('Z', '+00:00'))
                else:
                    last_activity = last_activity_result[0]
            
            # Generate course display name
            course_name = self._generate_course_display_name(course)
            
            progress = RoadmapProgress(
                course=course,
                course_name=course_name,
                total_questions=total_questions,
                completed_questions=completed_questions,
                progress_percentage=round(progress_percentage, 1),
                last_activity=last_activity
            )
            
            roadmap_progress.append(progress)
        
        return roadmap_progress
    
    def _generate_course_display_name(self, course: str) -> str:
        """Generate a human-readable course name from course identifier."""
        if course == "strivers-a2z":
            return "Striver's A2Z DSA Course"
        
        # For future courses, you can add more mappings here
        # Convert snake_case or kebab-case to Title Case
        words = course.replace('-', ' ').replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)
