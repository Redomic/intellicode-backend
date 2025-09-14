"""
Script to seed the database with assessment questions.
Run this script to populate the database with initial questions.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path to import app modules
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import get_db
from app.crud.question import QuestionCRUD
from app.data.assessment_questions import ALL_ASSESSMENT_QUESTIONS

def seed_questions():
    """Seed the database with assessment questions."""
    try:
        # Get database connection
        db = get_db()
        question_crud = QuestionCRUD(db)
        
        print("Starting to seed assessment questions...")
        
        # Check if questions collection exists, create if not
        if not db.has_collection('questions'):
            db.create_collection('questions')
            print("Created 'questions' collection")
        
        # Get current question count
        existing_count = question_crud.get_questions_count()
        print(f"Found {existing_count} existing questions")
        
        # Add questions
        added_count = 0
        for question_data in ALL_ASSESSMENT_QUESTIONS:
            try:
                # Check if question already exists by title
                existing_questions = question_crud.get_questions_by_criteria(limit=1000)
                if any(q.title == question_data.title for q in existing_questions):
                    print(f"Question '{question_data.title}' already exists, skipping...")
                    continue
                
                # Create the question
                created_question = question_crud.create_question(question_data)
                print(f"Added question: {created_question.title} ({created_question.difficulty.value})")
                added_count += 1
                
            except Exception as e:
                print(f"Error adding question '{question_data.title}': {str(e)}")
        
        print(f"\nSeeding completed!")
        print(f"Added {added_count} new questions")
        print(f"Total questions in database: {question_crud.get_questions_count()}")
        
        # Print summary by difficulty
        print("\nQuestions by difficulty:")
        for difficulty in ["BEGINNER", "INTERMEDIATE", "ADVANCED"]:
            from app.models.question import DifficultyLevel
            diff_level = DifficultyLevel(difficulty)
            diff_questions = question_crud.get_questions_by_criteria(difficulty=diff_level, limit=100)
            print(f"  {difficulty}: {len(diff_questions)} questions")
        
    except Exception as e:
        print(f"Error seeding questions: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Question Database Seeder")
    print("=" * 40)
    
    success = seed_questions()
    
    if success:
        print("\n✅ Questions seeded successfully!")
    else:
        print("\n❌ Error seeding questions!")
        sys.exit(1)
