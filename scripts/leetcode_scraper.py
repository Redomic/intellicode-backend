#!/usr/bin/env python3
"""
Focused LeetCode scraper using LeetScrape library.
"""
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, TaskID
from leetscrape import GetQuestion
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

console = Console()

class LeetCodeScraper:
    """LeetCode scraper using the LeetScrape library."""
    
    def __init__(self, max_workers: int = 3, delay_between_requests: float = 2.0):
        self.max_workers = max_workers
        self.delay_between_requests = delay_between_requests
        self.scraped_data = []
        self.errors = []
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def extract_title_slug_from_url(self, url: str) -> Optional[str]:
        """Extract the titleSlug from a LeetCode URL."""
        if not url:
            return None
        
        # Pattern to match LeetCode problem URLs
        patterns = [
            r'leetcode\.com/problems/([^/?]+)',
            r'leetcode\.com/problems/([^/?]+)/',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def rate_limit(self):
        """Simple rate limiting to be respectful."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.delay_between_requests:
                sleep_time = self.delay_between_requests - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()
    
    def scrape_single_question(self, question_data: Dict) -> Dict[str, Any]:
        """Scrape a single LeetCode question."""
        question_id = question_data.get('id', 'unknown')
        lc_link = question_data.get('lc_link')
        
        result = {
            'question_id': question_id,
            'original_title': question_data.get('question_title', ''),
            'a2z_step': question_data.get('step_title', ''),
            'a2z_difficulty': question_data.get('difficulty', 0),
            'lc_link': lc_link,
            'scraped_at': datetime.now().isoformat(),
            'success': False,
            'error': None,
            'leetcode_data': None
        }
        
        if not lc_link:
            result['error'] = 'No LeetCode link provided'
            return result
        
        title_slug = self.extract_title_slug_from_url(lc_link)
        if not title_slug:
            result['error'] = f'Could not extract title slug from URL: {lc_link}'
            return result
        
        try:
            # Rate limiting
            self.rate_limit()
            
            # Scrape using LeetScrape
            start_time = time.time()
            question = GetQuestion(titleSlug=title_slug).scrape()
            scraping_duration = time.time() - start_time
            
            # Extract and clean the data
            leetcode_data = {
                'title': question.title,
                'title_slug': title_slug,
                'difficulty': question.difficulty,
                'problem_statement_html': question.Body,
                'problem_statement_text': self.html_to_text(question.Body),
                'code_templates': self.extract_code_templates(question),
                'examples': self.extract_examples(question.Body),
                'constraints': self.extract_constraints(question.Body),
                'scraping_duration': scraping_duration,
                'company_tags': getattr(question, 'companyTags', []),
                'topic_tags': getattr(question, 'topicTags', []),
            }
            
            result['leetcode_data'] = leetcode_data
            result['success'] = True
            
            console.print(f"✅ Scraped: {question.title} ({question.difficulty})", style="green")
            
        except Exception as e:
            result['error'] = str(e)
            console.print(f"❌ Failed {question_id}: {str(e)}", style="red")
        
        return result
    
    def html_to_text(self, html_content: str) -> str:
        """Convert HTML content to clean text."""
        if not html_content:
            return ""
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            console.print(f"Warning: Could not convert HTML to text: {e}", style="yellow")
            return html_content
    
    def extract_code_templates(self, question) -> Dict[str, str]:
        """Extract code templates for different languages."""
        templates = {}
        
        if hasattr(question, 'Code') and question.Code:
            try:
                # LeetScrape returns a list of code templates
                for template in question.Code:
                    if hasattr(template, 'langSlug') and hasattr(template, 'code'):
                        templates[template.langSlug] = template.code
                    elif isinstance(template, dict):
                        lang = template.get('langSlug', 'unknown')
                        code = template.get('code', '')
                        templates[lang] = code
            except Exception as e:
                console.print(f"Warning: Could not extract code templates: {e}", style="yellow")
        
        return templates
    
    def extract_examples(self, html_content: str) -> List[Dict[str, str]]:
        """Extract examples from the HTML content."""
        examples = []
        
        if not html_content:
            return examples
        
        try:
            # Look for example patterns in the HTML
            example_pattern = r'<strong>Example\s*\d*:?\s*</strong>(.*?)(?=<strong>Example|\Z)'
            matches = re.findall(example_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            for i, match in enumerate(matches, 1):
                example_data = {'example_number': i}
                
                # Extract input
                input_match = re.search(r'<strong>Input:</strong>\s*(.*?)(?=<strong>Output:|<strong>Explanation:|$)', match, re.DOTALL | re.IGNORECASE)
                if input_match:
                    example_data['input'] = self.html_to_text(input_match.group(1)).strip()
                
                # Extract output
                output_match = re.search(r'<strong>Output:</strong>\s*(.*?)(?=<strong>Explanation:|$)', match, re.DOTALL | re.IGNORECASE)
                if output_match:
                    example_data['output'] = self.html_to_text(output_match.group(1)).strip()
                
                # Extract explanation
                explanation_match = re.search(r'<strong>Explanation:</strong>\s*(.*?)$', match, re.DOTALL | re.IGNORECASE)
                if explanation_match:
                    example_data['explanation'] = self.html_to_text(explanation_match.group(1)).strip()
                
                if len(example_data) > 1:  # More than just example_number
                    examples.append(example_data)
            
        except Exception as e:
            console.print(f"Warning: Could not extract examples: {e}", style="yellow")
        
        return examples
    
    def extract_constraints(self, html_content: str) -> List[str]:
        """Extract constraints from the HTML content."""
        constraints = []
        
        if not html_content:
            return constraints
        
        try:
            # Look for constraints section
            constraint_patterns = [
                r'<strong>Constraints:</strong>(.*?)(?=<strong>|$)',
                r'<p><strong>Constraints:</strong>(.*?)</p>',
                r'<ul>.*?constraints.*?</ul>'
            ]
            
            for pattern in constraint_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                
                for match in matches:
                    # Extract individual constraints from the match
                    constraint_text = self.html_to_text(match)
                    
                    # Split by common delimiters
                    for line in constraint_text.split('\n'):
                        line = line.strip()
                        if line and len(line) > 5:  # Filter out very short lines
                            constraints.append(line)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_constraints = []
            for constraint in constraints:
                if constraint not in seen:
                    seen.add(constraint)
                    unique_constraints.append(constraint)
            
            return unique_constraints
            
        except Exception as e:
            console.print(f"Warning: Could not extract constraints: {e}", style="yellow")
            return constraints
    
    def scrape_questions_parallel(self, questions: List[Dict]) -> List[Dict]:
        """Scrape multiple questions in parallel with rate limiting."""
        console.print(f"🚀 Starting to scrape {len(questions)} LeetCode questions...", style="bold blue")
        
        with Progress() as progress:
            task = progress.add_task("[green]Scraping questions...", total=len(questions))
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_question = {
                    executor.submit(self.scrape_single_question, question): question 
                    for question in questions
                }
                
                # Process completed tasks
                for future in future_to_question:
                    try:
                        result = future.result()
                        self.scraped_data.append(result)
                        
                        if not result['success']:
                            self.errors.append(result)
                            
                        progress.update(task, advance=1)
                        
                    except Exception as e:
                        error_result = {
                            'question_id': future_to_question[future].get('id', 'unknown'),
                            'error': str(e),
                            'success': False
                        }
                        self.errors.append(error_result)
                        progress.update(task, advance=1)
        
        return self.scraped_data
    
    def save_results(self, output_file: Path):
        """Save scraping results to JSON file."""
        try:
            # Prepare export data
            export_data = {
                'metadata': {
                    'scraped_at': datetime.now().isoformat(),
                    'total_questions': len(self.scraped_data),
                    'successful_scrapes': len([r for r in self.scraped_data if r['success']]),
                    'failed_scrapes': len(self.errors),
                    'scraper': 'LeetCode Scraper using LeetScrape v1.0.1'
                },
                'questions': self.scraped_data,
                'errors': self.errors
            }
            
            # Save to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            console.print(f"💾 Results saved to {output_file}", style="bold green")
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            console.print(f"❌ Error saving results: {e}", style="bold red")
            raise
    
    def print_summary(self):
        """Print a summary of scraping results."""
        total = len(self.scraped_data)
        successful = len([r for r in self.scraped_data if r['success']])
        failed = len(self.errors)
        
        console.print("\n" + "="*50, style="bold")
        console.print("📊 LEETCODE SCRAPING SUMMARY", style="bold blue", justify="center")
        console.print("="*50, style="bold")
        
        console.print(f"Total Questions Processed: {total}")
        console.print(f"✅ Successful: {successful}", style="green")
        console.print(f"❌ Failed: {failed}", style="red")
        
        if total > 0:
            success_rate = (successful / total) * 100
            console.print(f"Success Rate: {success_rate:.1f}%", style="blue")
        
        if self.scraped_data:
            durations = [r['leetcode_data']['scraping_duration'] for r in self.scraped_data 
                        if r['success'] and 'scraping_duration' in r.get('leetcode_data', {})]
            if durations:
                avg_duration = sum(durations) / len(durations)
                console.print(f"Average Scraping Time: {avg_duration:.2f}s per question")


def load_a2z_questions(a2z_file: Path) -> List[Dict]:
    """Load questions from A2Z JSON file and filter for LeetCode links."""
    try:
        with open(a2z_file, 'r', encoding='utf-8') as f:
            a2z_data = json.load(f)
        
        questions = []
        for step in a2z_data:
            for sub_step in step.get('sub_steps', []):
                for topic in sub_step.get('topics', []):
                    lc_link = topic.get('lc_link')
                    if lc_link and lc_link.strip():
                        questions.append(topic)
        
        console.print(f"📚 Found {len(questions)} questions with LeetCode links", style="blue")
        return questions
        
    except Exception as e:
        console.print(f"❌ Error loading A2Z file: {e}", style="bold red")
        raise


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LeetCode Scraper for A2Z Questions")
    parser.add_argument("--input", "-i", type=Path, default="a2z.json", help="A2Z JSON file")
    parser.add_argument("--output", "-o", type=Path, default="leetcode_scraped.json", help="Output file")
    parser.add_argument("--max-questions", type=int, help="Limit number of questions (for testing)")
    parser.add_argument("--max-workers", type=int, default=3, help="Max parallel workers")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    
    args = parser.parse_args()
    
    console.print("🚀 LeetCode Scraper Starting", style="bold blue", justify="center")
    console.print("="*50, style="blue")
    
    try:
        # Load questions
        questions = load_a2z_questions(args.input)
        
        if args.max_questions:
            questions = questions[:args.max_questions]
            console.print(f"🔢 Limited to {args.max_questions} questions for testing", style="yellow")
        
        # Create scraper and run
        scraper = LeetCodeScraper(
            max_workers=args.max_workers, 
            delay_between_requests=args.delay
        )
        
        scraper.scrape_questions_parallel(questions)
        scraper.save_results(args.output)
        
        console.print("🎉 Scraping completed!", style="bold green")
        
    except Exception as e:
        console.print(f"❌ Scraping failed: {e}", style="bold red")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
