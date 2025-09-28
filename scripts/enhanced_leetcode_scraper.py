#!/usr/bin/env python3
"""
Enhanced LeetCode scraper that extracts maximum information including test cases.
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
from bs4 import BeautifulSoup

console = Console()

class EnhancedLeetCodeScraper:
    """Enhanced LeetCode scraper that extracts comprehensive information."""
    
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
        """Scrape a single LeetCode question with comprehensive data extraction."""
        question_id = question_data.get('id', 'unknown')
        lc_link = question_data.get('lc_link')
        
        result = {
            'question_id': question_id,
            'original_title': question_data.get('question_title', ''),
            'a2z_step': question_data.get('step_title', ''),
            'a2z_sub_step': question_data.get('sub_step_title', ''),
            'a2z_difficulty': question_data.get('difficulty', 0),
            'a2z_topics': question_data.get('ques_topic', ''),
            'lc_link': lc_link,
            'step_number': question_data.get('step_number', 0),  # Preserve sl_no for ordering
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
            
            # Extract comprehensive data
            leetcode_data = {
                # Basic info
                'title': question.title,
                'title_slug': title_slug,
                'difficulty': question.difficulty,
                'question_id': question.QID,
                'is_paid_only': question.isPaidOnly,
                
                # Content
                'problem_statement_html': question.Body,
                'problem_statement_text': self.html_to_text(question.Body),
                
                # Test cases and examples
                'examples': self.extract_examples_comprehensive(question.Body),
                'sample_test_cases': self.extract_test_cases_from_examples(question.Body),
                'constraints': self.extract_constraints_comprehensive(question.Body),
                
                # Code and templates
                'code_templates': self.extract_all_code_templates(question),
                'default_code': question.Code if hasattr(question, 'Code') else None,
                
                # Additional metadata
                'hints': question.Hints if question.Hints else [],
                'topics': question.topics if question.topics else [],
                'company_tags': question.Companies if question.Companies else [],
                'similar_questions': question.SimilarQuestions if question.SimilarQuestions else [],
                
                # Performance
                'scraping_duration': scraping_duration,
                
                # Parsed content sections
                'follow_up_questions': self.extract_follow_up(question.Body),
                'note_sections': self.extract_notes(question.Body),
            }
            
            result['leetcode_data'] = leetcode_data
            result['success'] = True
            
            console.print(f"✅ Scraped: {question.title} ({question.difficulty}) - {len(leetcode_data['examples'])} examples, {len(leetcode_data['hints'])} hints", style="green")
            
        except Exception as e:
            result['error'] = str(e)
            console.print(f"❌ Failed {question_id}: {str(e)}", style="red")
        
        return result
    
    def html_to_text(self, html_content: str) -> str:
        """Convert HTML content to clean text."""
        if not html_content:
            return ""
        
        try:
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
    
    def extract_examples_comprehensive(self, html_content: str) -> List[Dict[str, str]]:
        """Extract examples with comprehensive parsing."""
        examples = []
        
        if not html_content:
            return examples
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Find example sections by strong tags
            example_sections = soup.find_all('strong', string=re.compile(r'Example\s*\d*', re.IGNORECASE))
            
            for i, example_tag in enumerate(example_sections, 1):
                example_data = {'example_number': i}
                
                # Get the parent container that contains the full example
                parent = example_tag.parent
                while parent and parent.name not in ['div', 'p', 'section']:
                    parent = parent.parent
                
                if parent:
                    # Get all text after the example tag until next example or end
                    example_text = self.get_text_until_next_example(parent, example_tag)
                    
                    # Extract components
                    example_data.update(self.parse_example_text(example_text))
                
                if len(example_data) > 1:  # More than just example_number
                    examples.append(example_data)
            
            # Method 2: Alternative parsing using pre tags
            if not examples:
                pre_tags = soup.find_all('pre')
                for i, pre in enumerate(pre_tags, 1):
                    pre_text = pre.get_text()
                    if 'Input:' in pre_text and 'Output:' in pre_text:
                        example_data = {'example_number': i}
                        example_data.update(self.parse_example_text(pre_text))
                        if len(example_data) > 1:
                            examples.append(example_data)
            
        except Exception as e:
            console.print(f"Warning: Could not extract examples: {e}", style="yellow")
        
        return examples
    
    def get_text_until_next_example(self, parent, start_tag) -> str:
        """Get text from start_tag until next example or end of parent."""
        text_parts = []
        current = start_tag
        
        while current and current.parent == parent:
            if current.name:
                text_parts.append(current.get_text())
            else:
                text_parts.append(str(current))
            
            current = current.next_sibling
            
            # Stop if we hit another example
            if current and hasattr(current, 'find') and current.find('strong', string=re.compile(r'Example\s*\d+', re.IGNORECASE)):
                break
        
        return ' '.join(text_parts)
    
    def parse_example_text(self, text: str) -> Dict[str, str]:
        """Parse example text to extract input, output, and explanation."""
        result = {}
        
        # Extract input
        input_patterns = [
            r'Input:\s*(.*?)(?=Output:|Explanation:|Example|\n\n|$)',
            r'<strong>Input:</strong>\s*(.*?)(?=<strong>Output:|<strong>Explanation:|$)',
        ]
        
        for pattern in input_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                result['input'] = self.clean_example_text(match.group(1))
                break
        
        # Extract output
        output_patterns = [
            r'Output:\s*(.*?)(?=Explanation:|Example|\n\n|$)',
            r'<strong>Output:</strong>\s*(.*?)(?=<strong>Explanation:|$)',
        ]
        
        for pattern in output_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                result['output'] = self.clean_example_text(match.group(1))
                break
        
        # Extract explanation
        explanation_patterns = [
            r'Explanation:\s*(.*?)(?=Example|\n\n|$)',
            r'<strong>Explanation:</strong>\s*(.*?)$',
        ]
        
        for pattern in explanation_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                result['explanation'] = self.clean_example_text(match.group(1))
                break
        
        return result
    
    def clean_example_text(self, text: str) -> str:
        """Clean extracted example text."""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common artifacts
        text = re.sub(r'^[\s\-\=\*]+', '', text)
        text = re.sub(r'[\s\-\=\*]+$', '', text)
        
        return text
    
    def extract_test_cases_from_examples(self, html_content: str) -> List[Dict[str, str]]:
        """Extract test cases in a structured format from examples."""
        test_cases = []
        examples = self.extract_examples_comprehensive(html_content)
        
        for example in examples:
            if 'input' in example and 'output' in example:
                test_case = {
                    'input': example['input'],
                    'expected_output': example['output'],
                    'explanation': example.get('explanation', ''),
                    'example_number': example.get('example_number', len(test_cases) + 1)
                }
                test_cases.append(test_case)
        
        return test_cases
    
    def extract_constraints_comprehensive(self, html_content: str) -> List[str]:
        """Extract constraints with comprehensive parsing."""
        constraints = []
        
        if not html_content:
            return constraints
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Find constraints section
            constraint_headers = soup.find_all('strong', string=re.compile(r'Constraints?:', re.IGNORECASE))
            
            for header in constraint_headers:
                # Get the next sibling elements that contain constraints
                current = header.parent
                while current:
                    if current.name == 'ul':
                        # Extract from list items
                        for li in current.find_all('li'):
                            constraint_text = self.clean_example_text(li.get_text())
                            if constraint_text and len(constraint_text) > 5:
                                constraints.append(constraint_text)
                        break
                    elif current.name == 'p' and current != header.parent:
                        # Extract from paragraph
                        constraint_text = self.clean_example_text(current.get_text())
                        if constraint_text and len(constraint_text) > 5:
                            constraints.append(constraint_text)
                        break
                    current = current.next_sibling
            
            # Method 2: Text-based extraction
            if not constraints:
                text = soup.get_text()
                constraint_patterns = [
                    r'Constraints?:\s*(.*?)(?=Example|Follow up|Note:|$)',
                    r'Constraints?:(.*?)(?=\n\n|Example|$)',
                ]
                
                for pattern in constraint_patterns:
                    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                    if match:
                        constraint_text = match.group(1)
                        # Split by common delimiters
                        for line in constraint_text.split('\n'):
                            line = line.strip()
                            if line and len(line) > 5 and not line.startswith('Example'):
                                constraints.append(line)
                        break
            
        except Exception as e:
            console.print(f"Warning: Could not extract constraints: {e}", style="yellow")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_constraints = []
        for constraint in constraints:
            if constraint not in seen:
                seen.add(constraint)
                unique_constraints.append(constraint)
        
        return unique_constraints
    
    def extract_all_code_templates(self, question) -> Dict[str, str]:
        """Extract all available code templates."""
        templates = {}
        
        if hasattr(question, 'Code') and question.Code:
            # The default code is typically Python
            templates['python'] = question.Code
        
        return templates
    
    def extract_follow_up(self, html_content: str) -> List[str]:
        """Extract follow-up questions."""
        follow_ups = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for follow-up sections
            follow_up_headers = soup.find_all('strong', string=re.compile(r'Follow\s*up', re.IGNORECASE))
            
            for header in follow_up_headers:
                parent = header.parent
                if parent:
                    follow_up_text = self.clean_example_text(parent.get_text())
                    # Remove the header text
                    follow_up_text = re.sub(r'Follow\s*up:?', '', follow_up_text, flags=re.IGNORECASE).strip()
                    if follow_up_text:
                        follow_ups.append(follow_up_text)
            
        except Exception as e:
            console.print(f"Warning: Could not extract follow-ups: {e}", style="yellow")
        
        return follow_ups
    
    def extract_notes(self, html_content: str) -> List[str]:
        """Extract note sections."""
        notes = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for note sections
            note_headers = soup.find_all('strong', string=re.compile(r'Note:', re.IGNORECASE))
            
            for header in note_headers:
                parent = header.parent
                if parent:
                    note_text = self.clean_example_text(parent.get_text())
                    # Remove the header text
                    note_text = re.sub(r'Note:?', '', note_text, flags=re.IGNORECASE).strip()
                    if note_text:
                        notes.append(note_text)
            
        except Exception as e:
            console.print(f"Warning: Could not extract notes: {e}", style="yellow")
        
        return notes
    
    def scrape_questions_parallel(self, questions: List[Dict]) -> List[Dict]:
        """Scrape multiple questions in parallel with rate limiting."""
        console.print(f"🚀 Starting comprehensive scraping of {len(questions)} LeetCode questions...", style="bold blue")
        
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
        """Save comprehensive scraping results to JSON file."""
        try:
            # Calculate comprehensive statistics
            successful_data = [r for r in self.scraped_data if r['success']]
            
            total_examples = sum(len(r['leetcode_data']['examples']) for r in successful_data if r['leetcode_data'])
            total_test_cases = sum(len(r['leetcode_data']['sample_test_cases']) for r in successful_data if r['leetcode_data'])
            total_hints = sum(len(r['leetcode_data']['hints']) for r in successful_data if r['leetcode_data'])
            total_topics = sum(len(r['leetcode_data']['topics']) for r in successful_data if r['leetcode_data'])
            
            # Prepare export data
            export_data = {
                'metadata': {
                    'scraped_at': datetime.now().isoformat(),
                    'total_questions': len(self.scraped_data),
                    'successful_scrapes': len(successful_data),
                    'failed_scrapes': len(self.errors),
                    'scraper': 'Enhanced LeetCode Scraper v2.0 using LeetScrape',
                    'content_statistics': {
                        'total_examples_extracted': total_examples,
                        'total_test_cases_extracted': total_test_cases,
                        'total_hints_extracted': total_hints,
                        'total_topics_extracted': total_topics,
                    }
                },
                'questions': self.scraped_data,
                'errors': self.errors
            }
            
            # Save to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            console.print(f"💾 Comprehensive results saved to {output_file}", style="bold green")
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            console.print(f"❌ Error saving results: {e}", style="bold red")
            raise
    
    def print_summary(self):
        """Print a comprehensive summary of scraping results."""
        total = len(self.scraped_data)
        successful = len([r for r in self.scraped_data if r['success']])
        failed = len(self.errors)
        
        console.print("\n" + "="*60, style="bold")
        console.print("📊 ENHANCED LEETCODE SCRAPING SUMMARY", style="bold blue", justify="center")
        console.print("="*60, style="bold")
        
        console.print(f"Total Questions Processed: {total}")
        console.print(f"✅ Successful: {successful}", style="green")
        console.print(f"❌ Failed: {failed}", style="red")
        
        if total > 0:
            success_rate = (successful / total) * 100
            console.print(f"Success Rate: {success_rate:.1f}%", style="blue")
        
        # Content statistics
        if self.scraped_data:
            successful_data = [r for r in self.scraped_data if r['success'] and r['leetcode_data']]
            
            if successful_data:
                total_examples = sum(len(r['leetcode_data']['examples']) for r in successful_data)
                total_test_cases = sum(len(r['leetcode_data']['sample_test_cases']) for r in successful_data)
                total_hints = sum(len(r['leetcode_data']['hints']) for r in successful_data)
                total_topics = sum(len(r['leetcode_data']['topics']) for r in successful_data)
                
                console.print(f"\n📈 Content Extracted:", style="bold yellow")
                console.print(f"   Examples: {total_examples}")
                console.print(f"   Test Cases: {total_test_cases}")
                console.print(f"   Hints: {total_hints}")
                console.print(f"   Topic Tags: {total_topics}")
                
                # Average metrics
                avg_examples = total_examples / len(successful_data) if successful_data else 0
                avg_hints = total_hints / len(successful_data) if successful_data else 0
                
                console.print(f"\n📊 Averages per Question:")
                console.print(f"   Examples: {avg_examples:.1f}")
                console.print(f"   Hints: {avg_hints:.1f}")
                
                durations = [r['leetcode_data']['scraping_duration'] for r in successful_data]
                if durations:
                    avg_duration = sum(durations) / len(durations)
                    console.print(f"   Scraping Time: {avg_duration:.2f}s")


def load_a2z_questions(a2z_file: Path) -> List[Dict]:
    """Load questions from A2Z JSON file and filter for LeetCode links with global sequential numbering."""
    try:
        with open(a2z_file, 'r', encoding='utf-8') as f:
            a2z_data = json.load(f)
        
        questions = []
        global_step_number = 1  # Start global counter at 1
        
        for step in a2z_data:
            for sub_step in step.get('sub_steps', []):
                for topic in sub_step.get('topics', []):
                    lc_link = topic.get('lc_link')
                    if lc_link and lc_link.strip():
                        # Create global sequential numbering across all sub-steps
                        topic_with_metadata = topic.copy()
                        topic_with_metadata['step_number'] = global_step_number
                        topic_with_metadata['original_sl_no'] = topic.get('sl_no', 0)  # Preserve original for reference
                        questions.append(topic_with_metadata)
                        global_step_number += 1  # Increment for next question
        
        console.print(f"📚 Found {len(questions)} questions with LeetCode links", style="blue")
        console.print(f"🔢 Assigned global step numbers 1-{global_step_number-1} (linear progression)", style="green")
        return questions
        
    except Exception as e:
        console.print(f"❌ Error loading A2Z file: {e}", style="bold red")
        raise


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced LeetCode Scraper with Comprehensive Data Extraction")
    parser.add_argument("--input", "-i", type=Path, default="a2z.json", help="A2Z JSON file")
    parser.add_argument("--output", "-o", type=Path, default="enhanced_leetcode_data.json", help="Output file")
    parser.add_argument("--max-questions", type=int, help="Limit number of questions (for testing)")
    parser.add_argument("--max-workers", type=int, default=3, help="Max parallel workers")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    
    args = parser.parse_args()
    
    console.print("🚀 Enhanced LeetCode Scraper Starting", style="bold blue", justify="center")
    console.print("="*60, style="blue")
    
    try:
        # Load questions
        questions = load_a2z_questions(args.input)
        
        if args.max_questions:
            questions = questions[:args.max_questions]
            console.print(f"🔢 Limited to {args.max_questions} questions for testing", style="yellow")
        
        # Create scraper and run
        scraper = EnhancedLeetCodeScraper(
            max_workers=args.max_workers, 
            delay_between_requests=args.delay
        )
        
        scraper.scrape_questions_parallel(questions)
        scraper.save_results(args.output)
        
        console.print("🎉 Enhanced scraping completed!", style="bold green")
        
    except Exception as e:
        console.print(f"❌ Scraping failed: {e}", style="bold red")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
