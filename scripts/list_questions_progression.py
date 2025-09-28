#!/usr/bin/env python3
"""
List all questions in step order to verify the learning progression makes sense.
"""
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.text import Text

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import get_db

console = Console()


def list_questions_progression():
    """List all questions ordered by step number to verify progression."""
    console.print("📚 Question Progression Analysis", style="bold blue", justify="center")
    console.print("="*80, style="blue")
    
    try:
        db = get_db()
        
        # Query all questions ordered by step_number
        query = """
        FOR r IN roadmap
        SORT r.step_number ASC
        RETURN {
            step_number: r.step_number,
            question_id: r.question_id,
            original_title: r.original_title,
            leetcode_title: r.leetcode_title,
            a2z_step: r.a2z_step,
            a2z_sub_step: r.a2z_sub_step,
            a2z_difficulty: r.a2z_difficulty,
            leetcode_difficulty: r.leetcode_difficulty,
            is_paid_only: r.is_paid_only
        }
        """
        
        cursor = db.aql.execute(query)
        questions = list(cursor)
        
        if not questions:
            console.print("❌ No questions found in database", style="red")
            return
        
        console.print(f"📊 Found {len(questions)} questions in linear progression", style="green")
        console.print()
        
        # Group by A2Z steps for better organization
        current_step = None
        current_sub_step = None
        step_count = 0
        
        # Create detailed table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Step #", style="cyan", width=6)
        table.add_column("Question Title", style="white", width=40)
        table.add_column("LC Difficulty", style="yellow", width=8)
        table.add_column("A2Z Section", style="green", width=25)
        
        # Also create a summary by sections
        section_summary = {}
        
        for question in questions:
            step_num = question.get('step_number', 0)
            title = question.get('leetcode_title') or question.get('original_title', 'Unknown')
            a2z_step = question.get('a2z_step', 'Unknown')
            a2z_sub_step = question.get('a2z_sub_step', 'Unknown')
            lc_difficulty = question.get('leetcode_difficulty', 'N/A')
            a2z_difficulty = question.get('a2z_difficulty', 0)
            
            # Track section changes
            section_key = f"{a2z_step} → {a2z_sub_step}"
            if section_key not in section_summary:
                section_summary[section_key] = {
                    'start_step': step_num,
                    'count': 0,
                    'difficulties': []
                }
            section_summary[section_key]['count'] += 1
            section_summary[section_key]['end_step'] = step_num
            section_summary[section_key]['difficulties'].append(lc_difficulty)
            
            # Add to detailed table
            if current_step != a2z_step or current_sub_step != a2z_sub_step:
                # Section header
                if current_step is not None:
                    table.add_row("", "", "", "", style="dim")
                
                current_step = a2z_step
                current_sub_step = a2z_sub_step
                step_count += 1
            
            # Truncate long titles
            display_title = title[:37] + "..." if len(title) > 40 else title
            display_section = f"{a2z_step[:22]}..." if len(a2z_step) > 25 else a2z_step
            
            table.add_row(
                str(step_num),
                display_title,
                lc_difficulty or "N/A",
                display_section
            )
        
        console.print(table)
        
        # Print section summary
        console.print("\n" + "="*80, style="bold")
        console.print("📋 SECTION SUMMARY", style="bold blue", justify="center")
        console.print("="*80, style="bold")
        
        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("Section", style="white", width=50)
        summary_table.add_column("Steps", style="cyan", width=12)
        summary_table.add_column("Count", style="green", width=8)
        summary_table.add_column("Difficulties", style="yellow", width=15)
        
        for section, data in section_summary.items():
            step_range = f"{data['start_step']}-{data['end_step']}" if data['start_step'] != data['end_step'] else str(data['start_step'])
            difficulty_counts = {}
            for diff in data['difficulties']:
                if diff and diff != 'N/A':
                    difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
            
            diff_summary = ", ".join([f"{d}:{c}" for d, c in difficulty_counts.items()]) if difficulty_counts else "N/A"
            
            summary_table.add_row(
                section[:47] + "..." if len(section) > 50 else section,
                step_range,
                str(data['count']),
                diff_summary[:12] + "..." if len(diff_summary) > 15 else diff_summary
            )
        
        console.print(summary_table)
        
        # Analysis
        console.print("\n" + "="*80, style="bold")
        console.print("🔍 PROGRESSION ANALYSIS", style="bold blue", justify="center")
        console.print("="*80, style="bold")
        
        # Check for logical progression
        progression_issues = []
        
        # Basic validation checks
        total_questions = len(questions)
        expected_range = list(range(1, total_questions + 1))
        actual_steps = [q.get('step_number', 0) for q in questions]
        
        if actual_steps != expected_range:
            progression_issues.append("❌ Step numbers are not consecutive 1-N")
        else:
            console.print("✅ Step numbers are consecutive 1-276", style="green")
        
        # Check if progression makes pedagogical sense
        basic_sections = ["Learn the basics", "Know Basic Maths", "Basic Hashing", "Sorting"]
        advanced_sections = ["Dynamic Programming", "Graph", "Tree", "Trie"]
        
        basic_steps = []
        advanced_steps = []
        
        for question in questions:
            step_num = question.get('step_number', 0)
            a2z_step = question.get('a2z_step', '')
            a2z_sub_step = question.get('a2z_sub_step', '')
            
            for basic in basic_sections:
                if basic.lower() in a2z_step.lower() or basic.lower() in a2z_sub_step.lower():
                    basic_steps.append(step_num)
                    break
            
            for advanced in advanced_sections:
                if advanced.lower() in a2z_step.lower() or advanced.lower() in a2z_sub_step.lower():
                    advanced_steps.append(step_num)
                    break
        
        if basic_steps and advanced_steps:
            avg_basic = sum(basic_steps) / len(basic_steps) if basic_steps else 0
            avg_advanced = sum(advanced_steps) / len(advanced_steps) if advanced_steps else 0
            
            if avg_basic < avg_advanced:
                console.print(f"✅ Basic concepts come before advanced (Basic avg: {avg_basic:.1f}, Advanced avg: {avg_advanced:.1f})", style="green")
            else:
                progression_issues.append("⚠️  Advanced concepts appear before basic ones")
        
        # Final assessment
        if not progression_issues:
            console.print("\n🎉 PROGRESSION LOOKS GOOD!", style="bold green")
            console.print("   Linear numbering 1-276 with logical learning flow", style="green")
        else:
            console.print("\n⚠️  PROGRESSION ISSUES FOUND:", style="bold yellow")
            for issue in progression_issues:
                console.print(f"   {issue}", style="yellow")
        
        console.print(f"\n📈 Total Questions: {total_questions}")
        console.print(f"📚 Total Sections: {len(section_summary)}")
        console.print(f"🎯 Range: Steps 1-{total_questions}")
        
    except Exception as e:
        console.print(f"❌ Error analyzing progression: {e}", style="red")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    list_questions_progression()


if __name__ == "__main__":
    main()
