#!/usr/bin/env python3
"""
Standalone roadmap scraper that works with pydantic v1 and saves to JSON.
This version bypasses the backend database integration to avoid pydantic conflicts.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from enhanced_leetcode_scraper import EnhancedLeetCodeScraper, load_a2z_questions

console = Console()


class StandaloneRoadmapScraper(EnhancedLeetCodeScraper):
    """Standalone version that saves comprehensive data to JSON for later database import."""
    
    def save_results(self, output_file: Path):
        """Save results in roadmap-compatible format."""
        try:
            # Convert scraped data to roadmap format
            roadmap_items = []
            
            for result in self.scraped_data:
                if not result:
                    continue
                    
                leetcode_data = result.get('leetcode_data', {})
                
                # Create roadmap item in the format expected by the database
                roadmap_item = {
                    # A2Z Striver metadata
                    "question_id": result.get('question_id', 'unknown'),
                    "original_title": result.get('original_title', ''),
                    "a2z_step": result.get('a2z_step', ''),
                    "a2z_sub_step": result.get('a2z_sub_step', ''),
                    "a2z_difficulty": result.get('a2z_difficulty', 0),
                    "a2z_topics": result.get('a2z_topics', ''),
                    "lc_link": result.get('lc_link', ''),
                    "step_number": result.get('step_number', 0),  # Preserve sl_no for proper ordering
                    
                    # LeetCode comprehensive data (if scraping was successful)
                    "leetcode_title": leetcode_data.get('title') if result['success'] else None,
                    "leetcode_title_slug": leetcode_data.get('title_slug') if result['success'] else None,
                    "leetcode_difficulty": leetcode_data.get('difficulty') if result['success'] else None,
                    "leetcode_question_id": leetcode_data.get('question_id') if result['success'] else None,
                    "is_paid_only": leetcode_data.get('is_paid_only', False) if result['success'] else False,
                    
                    # Problem content
                    "problem_statement_html": leetcode_data.get('problem_statement_html') if result['success'] else None,
                    "problem_statement_text": leetcode_data.get('problem_statement_text') if result['success'] else None,
                    
                    # Examples and test cases
                    "examples": leetcode_data.get('examples', []) if result['success'] else [],
                    "sample_test_cases": leetcode_data.get('sample_test_cases', []) if result['success'] else [],
                    "constraints": leetcode_data.get('constraints', []) if result['success'] else [],
                    
                    # Code templates and solutions
                    "code_templates": leetcode_data.get('code_templates', {}) if result['success'] else {},
                    "default_code": leetcode_data.get('default_code') if result['success'] else None,
                    
                    # Educational content
                    "hints": leetcode_data.get('hints', []) if result['success'] else [],
                    "topics": leetcode_data.get('topics', []) if result['success'] else [],
                    "company_tags": leetcode_data.get('company_tags', []) if result['success'] else [],
                    "similar_questions": leetcode_data.get('similar_questions', []) if result['success'] else [],
                    "follow_up_questions": leetcode_data.get('follow_up_questions', []) if result['success'] else [],
                    "note_sections": leetcode_data.get('note_sections', []) if result['success'] else [],
                    
                    # Scraping metadata
                    "scraping_duration": leetcode_data.get('scraping_duration') if result['success'] else None,
                    "scraped_at": result.get('scraped_at'),
                    "scraping_success": result['success'],
                    "scraping_error": result.get('error')
                }
                
                roadmap_items.append(roadmap_item)
            
            # Calculate comprehensive statistics
            successful_items = [r for r in roadmap_items if r['scraping_success']]
            
            total_examples = sum(len(r['examples']) for r in successful_items)
            total_test_cases = sum(len(r['sample_test_cases']) for r in successful_items)
            total_hints = sum(len(r['hints']) for r in successful_items)
            total_topics = sum(len(r['topics']) for r in successful_items)
            
            # Prepare export data in roadmap format
            export_data = {
                'metadata': {
                    'scraped_at': datetime.now().isoformat(),
                    'total_questions': len(roadmap_items),
                    'successful_scrapes': len(successful_items),
                    'failed_scrapes': len(self.errors),
                    'scraper': 'Standalone Roadmap Scraper v1.0 using LeetScrape',
                    'format': 'roadmap_collection_ready',
                    'content_statistics': {
                        'total_examples_extracted': total_examples,
                        'total_test_cases_extracted': total_test_cases,
                        'total_hints_extracted': total_hints,
                        'total_topics_extracted': total_topics,
                    }
                },
                'roadmap_items': roadmap_items,
                'errors': self.errors
            }
            
            # Save to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            console.print(f"💾 Roadmap data saved to {output_file}", style="bold green")
            console.print(f"📄 This file can be imported into the database using import_roadmap_data.py", style="blue")
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            console.print(f"❌ Error saving results: {e}", style="bold red")
            raise


def main():
    """Main function for standalone scraping."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Standalone Roadmap Scraper (Pydantic v1 Compatible)")
    parser.add_argument("--input", "-i", type=Path, default="a2z.json", help="A2Z JSON file")
    parser.add_argument("--output", "-o", type=Path, default="roadmap_data.json", help="Output file")
    parser.add_argument("--max-questions", type=int, help="Limit number of questions (for testing)")
    parser.add_argument("--max-workers", type=int, default=3, help="Max parallel workers")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    parser.add_argument("--step", type=str, help="Only scrape questions from specific A2Z step")
    parser.add_argument("--sub-step", type=str, help="Only scrape questions from specific A2Z sub-step")
    
    args = parser.parse_args()
    
    console.print("🛠️  Standalone Roadmap Scraper Starting", style="bold blue", justify="center")
    console.print("="*60, style="blue")
    console.print("This version saves to JSON for later database import", style="blue")
    console.print()
    
    try:
        # Load questions
        all_questions = load_a2z_questions(args.input)
        
        # Filter questions if specified
        questions_to_scrape = all_questions
        
        if args.step:
            questions_to_scrape = [q for q in questions_to_scrape if q.get('step_title') == args.step]
            console.print(f"🔍 Filtered to step '{args.step}': {len(questions_to_scrape)} questions", style="blue")
        
        if args.sub_step:
            questions_to_scrape = [q for q in questions_to_scrape if q.get('sub_step_title') == args.sub_step]
            console.print(f"🔍 Filtered to sub-step '{args.sub_step}': {len(questions_to_scrape)} questions", style="blue")
        
        if args.max_questions:
            questions_to_scrape = questions_to_scrape[:args.max_questions]
            console.print(f"🔢 Limited to {args.max_questions} questions for testing", style="yellow")
        
        if not questions_to_scrape:
            console.print("⚠️  No questions to scrape!", style="yellow")
            return 0
        
        # Create standalone scraper
        scraper = StandaloneRoadmapScraper(
            max_workers=args.max_workers, 
            delay_between_requests=args.delay
        )
        
        # Run scraper
        console.print(f"🚀 Starting to scrape {len(questions_to_scrape)} questions...", style="bold green")
        scraper.scrape_questions_parallel(questions_to_scrape)
        scraper.save_results(args.output)
        
        console.print("🎉 Standalone scraping completed!", style="bold green")
        console.print(f"📄 Next step: Import {args.output} into the database", style="blue")
        
    except Exception as e:
        console.print(f"❌ Scraping failed: {e}", style="bold red")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

