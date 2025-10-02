#!/usr/bin/env python3
"""
Fix example numbering for all roadmap questions.

This script ensures all examples are numbered sequentially starting from 1.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import get_db


def fix_example_numbers():
    """Fix example numbering for all questions."""
    db = get_db()
    roadmap = db.collection('roadmap')
    
    print("🔍 Scanning for questions with incorrect example numbers...")
    
    # Find all questions with examples
    query = """
    FOR q IN roadmap
      FILTER LENGTH(q.examples) > 0
      RETURN {
        _key: q._key,
        title: q.leetcode_title,
        examples: q.examples,
        sample_test_cases: q.sample_test_cases
      }
    """
    
    cursor = db.aql.execute(query)
    questions = list(cursor)
    
    print(f"📊 Found {len(questions)} questions with examples")
    
    fixed_count = 0
    
    for q in questions:
        needs_fix = False
        
        # Check if examples need fixing
        for idx, ex in enumerate(q['examples'], start=1):
            if ex.get('example_number') != idx:
                needs_fix = True
                break
        
        if not needs_fix:
            continue
        
        print(f"\n🔧 Fixing: {q['title']} (key: {q['_key']})")
        
        # Fix example numbers (renumber from 1)
        fixed_examples = []
        for idx, ex in enumerate(q['examples'], start=1):
            fixed_ex = ex.copy()
            fixed_ex['example_number'] = idx
            fixed_examples.append(fixed_ex)
            print(f"   Example {idx}: ✅")
        
        # Fix sample_test_cases if they exist
        fixed_tests = []
        if q.get('sample_test_cases'):
            for idx, test in enumerate(q['sample_test_cases'], start=1):
                fixed_test = test.copy()
                fixed_test['example_number'] = idx
                fixed_tests.append(fixed_test)
        
        # Update document
        try:
            roadmap.update({
                '_key': q['_key'],
                'examples': fixed_examples,
                'sample_test_cases': fixed_tests
            })
            fixed_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n" + "="*50)
    print(f"✅ Done! Fixed {fixed_count} out of {len(questions)} questions")
    print("="*50)


if __name__ == "__main__":
    try:
        fix_example_numbers()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
