import json
import sys
import os
import argparse
from datetime import datetime, timezone

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db

def seed_assessments(json_file_path):
    """Seed the assessments from a JSON file into the database."""
    print(f"Loading assessment questions from {json_file_path}...")
    
    try:
        with open(json_file_path, 'r') as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {json_file_path}")
        return
    
    db = get_db()
    questions_col = db.collection('questions')
    
    if not questions_col:
        print("Creating questions collection...")
        questions_col = db.create_collection('questions')
        
    inserted_count = 0
    updated_count = 0
    error_count = 0
    
    print(f"Found {len(questions)} questions to process.")
    
    for q in questions:
        try:
            # Prepare document for insertion
            # We remove _id and _rev as they are managed by ArangoDB
            doc = q.copy()
            doc.pop('_id', None)
            doc.pop('_rev', None)
            
            # If the JSON doesn't have timestamps, add them
            if 'created_at' not in doc:
                doc['created_at'] = datetime.now(timezone.utc).isoformat()
            
            # Check if document with this key already exists
            key = doc.get('_key')
            
            if key and questions_col.has(key):
                # Update existing document
                doc['updated_at'] = datetime.now(timezone.utc).isoformat()
                questions_col.update(doc)
                updated_count += 1
            else:
                # Insert new document
                questions_col.insert(doc)
                inserted_count += 1
                
        except Exception as e:
            print(f"Error processing question '{q.get('title', 'Unknown')}': {e}")
            error_count += 1
            
    print("\n--- Seeding Complete ---")
    print(f"Successfully inserted: {inserted_count}")
    print(f"Successfully updated: {updated_count}")
    print(f"Errors: {error_count}")
    print(f"Total questions in database: {questions_col.count()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed assessment questions into the database")
    parser.add_argument(
        "--file", 
        type=str, 
        default=os.path.join(os.path.dirname(__file__), "assessment_questions.json"),
        help="Path to the JSON file containing assessment questions"
    )
    
    args = parser.parse_args()
    seed_assessments(args.file)
