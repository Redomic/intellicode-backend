#!/usr/bin/env python3
"""
Import roadmap data from JSON file into the database.
This script handles the database import separately from scraping to avoid pydantic conflicts.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import get_db
from app.crud.roadmap import RoadmapCRUD
from app.models.roadmap import RoadmapItemCreate

console = Console()


def import_roadmap_data(json_file: Path, skip_existing: bool = True, filter_paid: bool = True) -> None:
    """Import roadmap data from JSON file into database."""
    
    console.print(f"📥 Importing roadmap data from {json_file}", style="bold blue")
    
    # Load JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        console.print(f"❌ Error loading JSON file: {e}", style="bold red")
        return
    
    # Initialize database
    try:
        db = get_db()
        roadmap_crud = RoadmapCRUD(db)
        console.print("✅ Database connection established", style="green")
    except Exception as e:
        console.print(f"❌ Database connection failed: {e}", style="bold red")
        return
    
    # Get roadmap items from JSON
    roadmap_items = data.get('roadmap_items', [])
    if not roadmap_items:
        console.print("⚠️  No roadmap items found in JSON file", style="yellow")
        return
    
    console.print(f"📊 Found {len(roadmap_items)} roadmap items to process", style="blue")
    
    # Filter out paid questions if requested and renumber sequentially
    paid_questions_count = 0
    filtered_items = []
    
    for item in roadmap_items:
        if filter_paid and item.get('is_paid_only', False):
            paid_questions_count += 1
            continue
        filtered_items.append(item)
    
    if filter_paid and paid_questions_count > 0:
        console.print(f"🚫 Filtered out {paid_questions_count} paid-only questions", style="yellow")
        console.print(f"✅ Processing {len(filtered_items)} free questions", style="green")
    
    # Renumber the filtered questions sequentially from 1 to N
    console.print(f"🔢 Renumbering questions sequentially 1-{len(filtered_items)} (linear progression)", style="blue")
    for index, item in enumerate(filtered_items, start=1):
        item['original_step_number'] = item.get('step_number', 0)  # Preserve original for reference
        item['step_number'] = index  # Assign new sequential number
    
    roadmap_items = filtered_items
    
    # Import items with progress tracking
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    with Progress() as progress:
        task = progress.add_task("[green]Importing roadmap items...", total=len(roadmap_items))
        
        for item_data in roadmap_items:
            try:
                question_id = item_data.get('question_id')
                if not question_id:
                    console.print("⚠️  Skipping item without question_id", style="yellow")
                    error_count += 1
                    progress.update(task, advance=1)
                    continue
                
                # Check if item already exists
                if skip_existing:
                    existing_item = roadmap_crud.get_roadmap_item_by_question_id(question_id)
                    if existing_item and existing_item.scraping_success:
                        skipped_count += 1
                        progress.update(task, advance=1)
                        continue
                
                # Convert datetime strings to datetime objects
                scraped_at = None
                if item_data.get('scraped_at'):
                    try:
                        scraped_at = datetime.fromisoformat(item_data['scraped_at'])
                    except:
                        scraped_at = datetime.utcnow()
                
                # Create RoadmapItemCreate object
                roadmap_item = RoadmapItemCreate(
                    course=item_data.get('course', 'strivers-a2z'),  # Use course from JSON or default to strivers-a2z
                    question_id=question_id,
                    original_title=item_data.get('original_title', ''),
                    a2z_step=item_data.get('a2z_step', ''),
                    a2z_sub_step=item_data.get('a2z_sub_step', ''),
                    a2z_difficulty=item_data.get('a2z_difficulty', 0),
                    a2z_topics=item_data.get('a2z_topics', ''),
                    lc_link=item_data.get('lc_link', ''),
                    step_number=item_data.get('step_number', 0),  # Preserve original sl_no for proper ordering
                    leetcode_title=item_data.get('leetcode_title'),
                    leetcode_title_slug=item_data.get('leetcode_title_slug'),
                    leetcode_difficulty=item_data.get('leetcode_difficulty'),
                    leetcode_question_id=item_data.get('leetcode_question_id'),
                    is_paid_only=item_data.get('is_paid_only', False),
                    problem_statement_html=item_data.get('problem_statement_html'),
                    problem_statement_text=item_data.get('problem_statement_text'),
                    examples=item_data.get('examples', []),
                    sample_test_cases=item_data.get('sample_test_cases', []),
                    constraints=item_data.get('constraints', []),
                    code_templates=item_data.get('code_templates', {}),
                    default_code=item_data.get('default_code'),
                    hints=item_data.get('hints', []),
                    topics=item_data.get('topics', []),
                    company_tags=item_data.get('company_tags', []),
                    similar_questions=item_data.get('similar_questions', []),
                    follow_up_questions=item_data.get('follow_up_questions', []),
                    note_sections=item_data.get('note_sections', []),
                    scraping_duration=item_data.get('scraping_duration'),
                    scraped_at=scraped_at,
                    scraping_success=item_data.get('scraping_success', False),
                    scraping_error=item_data.get('scraping_error')
                )
                
                # Save to database
                saved_item = roadmap_crud.upsert_roadmap_item(roadmap_item)
                if saved_item:
                    imported_count += 1
                else:
                    error_count += 1
                    console.print(f"❌ Failed to save {question_id}", style="red")
                
            except Exception as e:
                error_count += 1
                console.print(f"❌ Error importing {item_data.get('question_id', 'unknown')}: {e}", style="red")
            
            progress.update(task, advance=1)
    
    # Print import summary
    console.print("\n" + "="*60, style="bold")
    console.print("📊 IMPORT SUMMARY", style="bold blue", justify="center")
    console.print("="*60, style="bold")
    
    console.print(f"✅ Imported: {imported_count}", style="green")
    console.print(f"⏭️  Skipped: {skipped_count}", style="yellow")
    console.print(f"❌ Errors: {error_count}", style="red")
    if filter_paid and paid_questions_count > 0:
        console.print(f"🚫 Paid Questions Filtered: {paid_questions_count}", style="yellow")
        console.print(f"📋 Note: Step numbers renumbered sequentially 1-{imported_count} (linear progression)", style="blue")
    
    # Get final database statistics
    try:
        stats = roadmap_crud.get_roadmap_stats()
        console.print(f"\n📈 Database Statistics:", style="bold yellow")
        console.print(f"   Total Questions: {stats.total_questions}")
        console.print(f"   Successfully Scraped: {stats.successfully_scraped}")
        console.print(f"   Success Rate: {stats.success_rate:.1f}%")
        console.print(f"   Steps Covered: {len(stats.steps_covered)}")
        console.print(f"   Sub-steps Covered: {len(stats.sub_steps_covered)}")
    except Exception as e:
        console.print(f"⚠️  Could not fetch final statistics: {e}", style="yellow")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import roadmap data from JSON into database")
    parser.add_argument("json_file", type=Path, help="JSON file containing roadmap data")
    parser.add_argument("--force", action="store_true", help="Import even if items already exist")
    parser.add_argument("--stats-only", action="store_true", help="Only show current database statistics")
    parser.add_argument("--include-paid", action="store_true", help="Include paid LeetCode questions (default: filtered out)")
    
    args = parser.parse_args()
    
    console.print("📥 Roadmap Data Importer", style="bold blue", justify="center")
    console.print("="*50, style="blue")
    
    if args.stats_only:
        try:
            db = get_db()
            roadmap_crud = RoadmapCRUD(db)
            stats = roadmap_crud.get_roadmap_stats()
            
            console.print(f"📊 Current Database Statistics:", style="bold yellow")
            console.print(f"   Total Questions: {stats.total_questions}")
            console.print(f"   Successfully Scraped: {stats.successfully_scraped}")
            console.print(f"   Failed Scrapes: {stats.failed_scrapes}")
            console.print(f"   Success Rate: {stats.success_rate:.1f}%")
            console.print(f"   Steps Covered: {len(stats.steps_covered)}")
            console.print(f"   Sub-steps Covered: {len(stats.sub_steps_covered)}")
            
            if stats.last_scraped:
                console.print(f"   Last Scraped: {stats.last_scraped.strftime('%Y-%m-%d %H:%M:%S')}")
                
        except Exception as e:
            console.print(f"❌ Error fetching statistics: {e}", style="bold red")
            return 1
    else:
        if not args.json_file.exists():
            console.print(f"❌ JSON file not found: {args.json_file}", style="bold red")
            return 1
        
        try:
            import_roadmap_data(
                args.json_file, 
                skip_existing=not args.force,
                filter_paid=not args.include_paid  # Filter paid questions unless --include-paid is specified
            )
            console.print("🎉 Import completed successfully!", style="bold green")
        except Exception as e:
            console.print(f"❌ Import failed: {e}", style="bold red")
            import traceback
            traceback.print_exc()
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
