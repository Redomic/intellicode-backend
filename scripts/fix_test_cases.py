#!/usr/bin/env python3
"""
Fix test case formats in roadmap questions.

Fixes:
1. Example numbering (1, 2, 3...)
2. Expected output format (extract just the return value)
"""

import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import get_db


def extract_expected_output(output_string):
    """
    Extract the actual expected output from descriptive strings.
    
    Examples:
        "5, nums = [0,1,2,3,4,_,_,_,_,_]" -> "5"
        "2, nums = [1,2,_]" -> "2"
        "[1,2,3]" -> "[1,2,3]"
    """
    if not output_string or not isinstance(output_string, str):
        return output_string
    
    # Pattern: number followed by comma (common in in-place modification problems)
    match = re.match(r'^(\d+)\s*,', output_string)
    if match:
        return match.group(1)
    
    # Pattern: boolean followed by comma
    match = re.match(r'^(true|false)\s*,', output_string, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    
    # If it's just a clean value already, return as-is
    return output_string.strip()


def fix_question_data(q):
    """Fix a single question's data."""
    needs_fix = False
    
    # Fix example numbers
    fixed_examples = []
    for idx, ex in enumerate(q['examples'], start=1):
        fixed_ex = ex.copy()
        if fixed_ex.get('example_number') != idx:
            needs_fix = True
        fixed_ex['example_number'] = idx
        fixed_examples.append(fixed_ex)
    
    # Fix sample_test_cases
    fixed_tests = []
    if q.get('sample_test_cases'):
        for idx, test in enumerate(q['sample_test_cases'], start=1):
            fixed_test = test.copy()
            
            # Fix example number
            if fixed_test.get('example_number') != idx:
                needs_fix = True
            fixed_test['example_number'] = idx
            
            # Fix expected_output format
            old_output = fixed_test.get('expected_output', '')
            new_output = extract_expected_output(old_output)
            
            if old_output != new_output:
                needs_fix = True
                print(f"      Old output: {old_output}")
                print(f"      New output: {new_output}")
            
            fixed_test['expected_output'] = new_output
            fixed_tests.append(fixed_test)
    
    return needs_fix, fixed_examples, fixed_tests


def fix_all_questions():
    """Fix all questions in the roadmap."""
    db = get_db()
    roadmap = db.collection('roadmap')
    
    print("🔍 Scanning roadmap questions...")
    
    # Get all questions with examples
    query = """
    FOR q IN roadmap
      FILTER LENGTH(q.examples) > 0 OR LENGTH(q.sample_test_cases) > 0
      RETURN {
        _key: q._key,
        title: q.leetcode_title,
        examples: q.examples,
        sample_test_cases: q.sample_test_cases
      }
    """
    
    cursor = db.aql.execute(query)
    questions = list(cursor)
    
    print(f"📊 Found {len(questions)} questions\n")
    
    fixed_count = 0
    
    for q in questions:
        needs_fix, fixed_examples, fixed_tests = fix_question_data(q)
        
        if not needs_fix:
            continue
        
        print(f"🔧 Fixing: {q['title']} (key: {q['_key']})")
        print(f"   Examples: {len(fixed_examples)}")
        print(f"   Test cases: {len(fixed_tests)}")
        
        # Update document
        try:
            roadmap.update({
                '_key': q['_key'],
                'examples': fixed_examples,
                'sample_test_cases': fixed_tests
            })
            fixed_count += 1
            print(f"   ✅ Updated\n")
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
    
    print("="*60)
    print(f"✅ Done! Fixed {fixed_count} out of {len(questions)} questions")
    print("="*60)


if __name__ == "__main__":
    try:
        fix_all_questions()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
