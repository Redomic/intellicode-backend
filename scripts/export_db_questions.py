import json
import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db

def export_questions_from_db():
    db = get_db()
    questions_col = db.collection('questions')
    
    if not questions_col:
        print("Questions collection not found!")
        return

    # Find all questions that are likely assessment questions
    # E.g., multiple choice or true/false, or perhaps just all of them
    cursor = questions_col.all()
    questions = list(cursor)
    
    # Let's filter to those that look like assessment questions, or just export all
    # We can inspect the first few
    assessment_questions = [q for q in questions if 'question_type' in q]
    
    with open('db_questions_export.json', 'w') as f:
        json.dump(assessment_questions, f, default=str, indent=2)
    
    print(f"Exported {len(assessment_questions)} assessment questions to db_questions_export.json")

if __name__ == "__main__":
    export_questions_from_db()
