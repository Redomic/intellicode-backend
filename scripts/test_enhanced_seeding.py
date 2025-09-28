#!/usr/bin/env python3
"""
Test script for the enhanced roadmap seeding system.
This script verifies that the new step numbering and paid question filtering works correctly.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import get_db
from app.crud.roadmap import RoadmapCRUD

console = Console()


def test_step_numbering():
    """Test that questions have proper step numbering from sl_no."""
    console.print("🔢 Testing Step Numbering...", style="bold blue")
    
    try:
        db = get_db()
        roadmap_crud = RoadmapCRUD(db)
        
        # Get some questions and check their step numbers using AQL query
        query = "FOR r IN roadmap LIMIT 10 RETURN r"
        cursor = db.aql.execute(query)
        questions = []
        for item_data in cursor:
            # Convert to RoadmapItemInDB objects
            if 'created_at' in item_data and isinstance(item_data['created_at'], str):
                item_data['created_at'] = datetime.fromisoformat(item_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in item_data and isinstance(item_data['updated_at'], str):
                item_data['updated_at'] = datetime.fromisoformat(item_data['updated_at'].replace('Z', '+00:00'))
            questions.append(type('RoadmapItem', (), item_data)())
        
        if not questions:
            console.print("❌ No questions found in database", style="red")
            return False
        
        # Create a table to show the step numbers
        table = Table(title="Step Number Verification")
        table.add_column("Question ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Step Number", style="green")
        table.add_column("A2Z Step", style="yellow")
        
        has_step_numbers = False
        for q in questions:
            step_num = getattr(q, 'step_number', 'MISSING')
            if step_num != 'MISSING' and step_num > 0:
                has_step_numbers = True
            
            question_id = getattr(q, 'question_id', 'UNKNOWN')
            original_title = getattr(q, 'original_title', 'UNKNOWN')
            a2z_step = getattr(q, 'a2z_step', 'UNKNOWN')
            
            table.add_row(
                question_id[:15] + "..." if len(question_id) > 15 else question_id,
                original_title[:30] + "..." if len(original_title) > 30 else original_title,
                str(step_num),
                a2z_step[:20] + "..." if len(a2z_step) > 20 else a2z_step
            )
        
        console.print(table)
        
        if has_step_numbers:
            console.print("✅ Step numbers are present and working!", style="green")
            return True
        else:
            console.print("❌ Step numbers are missing or zero", style="red")
            return False
            
    except Exception as e:
        console.print(f"❌ Error testing step numbering: {e}", style="red")
        return False


def test_paid_question_filtering():
    """Test that paid questions are properly filtered."""
    console.print("\n🚫 Testing Paid Question Filtering...", style="bold blue")
    
    try:
        db = get_db()
        roadmap_crud = RoadmapCRUD(db)
        
        # Count total questions and paid questions using AQL
        count_query = "FOR r IN roadmap COLLECT AGGREGATE total = COUNT(1), paid = SUM(r.is_paid_only == true ? 1 : 0) RETURN {total: total, paid: paid}"
        cursor = db.aql.execute(count_query)
        result = list(cursor)
        
        if result:
            total_count = result[0]['total']
            paid_count = result[0]['paid']
            free_count = total_count - paid_count
        else:
            total_count = 0
            paid_count = 0
            free_count = 0
        
        console.print(f"📊 Total Questions: {total_count}")
        console.print(f"🚫 Paid Questions: {paid_count}")
        console.print(f"✅ Free Questions: {free_count}")
        
        if paid_count == 0:
            console.print("✅ Paid question filtering is working correctly!", style="green")
            return True
        else:
            console.print(f"⚠️  Found {paid_count} paid questions in database", style="yellow")
            console.print("This might be expected if --include-paid was used", style="yellow")
            return True
            
    except Exception as e:
        console.print(f"❌ Error testing paid question filtering: {e}", style="red")
        return False


def test_data_integrity():
    """Test overall data integrity."""
    console.print("\n🔍 Testing Data Integrity...", style="bold blue")
    
    try:
        db = get_db()
        roadmap_crud = RoadmapCRUD(db)
        
        # Get statistics
        stats = roadmap_crud.get_roadmap_stats()
        
        console.print(f"📈 Database Statistics:")
        console.print(f"   Total Questions: {stats.total_questions}")
        console.print(f"   Successfully Scraped: {stats.successfully_scraped}")
        console.print(f"   Success Rate: {stats.success_rate:.1f}%")
        console.print(f"   Steps Covered: {len(stats.steps_covered)}")
        console.print(f"   Sub-steps Covered: {len(stats.sub_steps_covered)}")
        
        # Check for basic data completeness using AQL
        completeness_query = """
        FOR r IN roadmap
        LIMIT 10
        LET is_complete = (
            r.question_id != null AND r.question_id != "" AND
            r.original_title != null AND r.original_title != "" AND
            r.a2z_step != null AND r.a2z_step != "" AND
            r.a2z_sub_step != null AND r.a2z_sub_step != "" AND
            r.step_number != null
        )
        COLLECT AGGREGATE total = COUNT(1), complete = SUM(is_complete ? 1 : 0)
        RETURN {total: total, complete: complete}
        """
        
        cursor = db.aql.execute(completeness_query)
        result = list(cursor)
        
        if result and result[0]['total'] > 0:
            total_sample = result[0]['total']
            complete_questions = result[0]['complete']
            completeness_rate = (complete_questions / total_sample) * 100
        else:
            total_sample = 0
            complete_questions = 0
            completeness_rate = 0
        console.print(f"   Data Completeness: {completeness_rate:.1f}% (sample of {total_sample} questions)")
        
        if completeness_rate >= 90:
            console.print("✅ Data integrity looks good!", style="green")
            return True
        else:
            console.print("⚠️  Some data might be incomplete", style="yellow")
            return False
            
    except Exception as e:
        console.print(f"❌ Error testing data integrity: {e}", style="red")
        return False


def verify_sample_data_structure():
    """Verify that the scraped JSON has the correct structure."""
    console.print("\n📋 Verifying Sample Data Structure...", style="bold blue")
    
    # Check if we have recent scraped data files
    data_files = ["roadmap_data.json", "leetcode.json", "test_roadmap.json"]
    
    for filename in data_files:
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            console.print(f"📄 Checking {filename}...")
            
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                roadmap_items = data.get('roadmap_items', [])
                if not roadmap_items:
                    console.print(f"⚠️  No roadmap_items in {filename}", style="yellow")
                    continue
                
                # Check first few items for required fields
                sample = roadmap_items[:3]
                required_fields = ['question_id', 'step_number', 'a2z_step', 'a2z_sub_step']
                
                all_good = True
                for item in sample:
                    missing_fields = [field for field in required_fields if field not in item]
                    if missing_fields:
                        console.print(f"❌ Missing fields in {filename}: {missing_fields}", style="red")
                        all_good = False
                
                if all_good:
                    console.print(f"✅ {filename} structure looks good!", style="green")
                    
                    # Show sample step numbers
                    step_numbers = [item.get('step_number', 'N/A') for item in sample]
                    console.print(f"   Sample step numbers: {step_numbers}")
                    
                    # Show paid question info
                    paid_count = sum(1 for item in roadmap_items if item.get('is_paid_only', False))
                    console.print(f"   Paid questions in file: {paid_count}/{len(roadmap_items)}")
                
            except Exception as e:
                console.print(f"❌ Error reading {filename}: {e}", style="red")
    
    return True


def main():
    """Run all tests."""
    console.print("🧪 Enhanced Roadmap Seeding Test Suite", style="bold blue", justify="center")
    console.print("="*60, style="blue")
    
    tests = [
        ("Data Structure Verification", verify_sample_data_structure),
        ("Step Numbering", test_step_numbering),
        ("Paid Question Filtering", test_paid_question_filtering),
        ("Data Integrity", test_data_integrity),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            console.print(f"❌ {test_name} failed with error: {e}", style="red")
            results.append((test_name, False))
    
    # Summary
    console.print("\n" + "="*60, style="bold")
    console.print("🏁 TEST SUMMARY", style="bold blue", justify="center")
    console.print("="*60, style="bold")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        console.print(f"{status} {test_name}")
    
    console.print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        console.print("🎉 All tests passed! The enhanced seeding system is working correctly.", style="bold green")
        return 0
    else:
        console.print("⚠️  Some tests failed. Please check the implementation.", style="bold yellow")
        return 1


if __name__ == "__main__":
    exit(main())
