"""
Main orchestrator for coordinating scraping across multiple platforms.
"""
import asyncio
import json
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import logging
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from asyncio_throttle import Throttler

from models import (
    ScrapedQuestion, QuestionLinks, ScrapingResult, ScrapingStats,
    Platform, ScrapedQuestionContent
)
from config import CONFIG, identify_platform
from scrapers import LeetCodeScraper, GeeksforGeeksScraper, CodingNinjasScraper
from utils import setup_logging, save_json, load_json

logger = logging.getLogger(__name__)
console = Console()

class ScraperOrchestrator:
    """Main orchestrator for scraping questions from multiple platforms."""
    
    def __init__(self):
        self.scrapers = {}
        self.throttlers = {}
        self.stats = ScrapingStats()
        self.results: List[ScrapingResult] = []
        
        # Initialize throttlers for each platform
        for platform_name, config in CONFIG.platform_configs.items():
            rate_limit = config.get('rate_limit', 30)
            self.throttlers[platform_name] = Throttler(rate_limit=rate_limit, period=60)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_scrapers()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup_scrapers()
    
    async def initialize_scrapers(self):
        """Initialize all platform scrapers."""
        console.print("🚀 Initializing scrapers...", style="bold blue")
        
        try:
            self.scrapers[Platform.LEETCODE] = LeetCodeScraper()
            await self.scrapers[Platform.LEETCODE].__aenter__()
            
            self.scrapers[Platform.GEEKSFORGEEKS] = GeeksforGeeksScraper()
            await self.scrapers[Platform.GEEKSFORGEEKS].__aenter__()
            
            self.scrapers[Platform.CODINGNINJAS] = CodingNinjasScraper()
            await self.scrapers[Platform.CODINGNINJAS].__aenter__()
            
            console.print("✅ All scrapers initialized successfully", style="bold green")
            
        except Exception as e:
            logger.error(f"Error initializing scrapers: {e}")
            raise
    
    async def cleanup_scrapers(self):
        """Clean up all scrapers."""
        console.print("🧹 Cleaning up scrapers...", style="bold yellow")
        
        for scraper in self.scrapers.values():
            try:
                await scraper.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up scraper: {e}")
        
        console.print("✅ Cleanup completed", style="bold green")
    
    async def scrape_questions_from_a2z(self, a2z_file: Path, max_questions: Optional[int] = None) -> List[ScrapingResult]:
        """
        Scrape questions from the A2Z JSON file.
        
        Args:
            a2z_file: Path to the A2Z JSON file
            max_questions: Maximum number of questions to scrape (for testing)
            
        Returns:
            List of scraping results
        """
        console.print(f"📚 Loading questions from {a2z_file}", style="bold blue")
        
        # Load A2Z data
        a2z_data = load_json(a2z_file)
        questions = self._extract_questions_from_a2z(a2z_data)
        
        if max_questions:
            questions = questions[:max_questions]
            console.print(f"🔢 Limited to {max_questions} questions for testing", style="yellow")
        
        console.print(f"📊 Found {len(questions)} questions to scrape", style="bold cyan")
        
        # Create progress bar
        with Progress() as progress:
            task = progress.add_task("[green]Scraping questions...", total=len(questions))
            
            # Process questions with concurrency control
            semaphore = asyncio.Semaphore(CONFIG.concurrent_limit)
            tasks = []
            
            for question in questions:
                task_coro = self._scrape_question_with_semaphore(semaphore, question, progress, task)
                tasks.append(task_coro)
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and collect results
            for result in results:
                if isinstance(result, ScrapingResult):
                    self.results.append(result)
                    self.stats.add_result(result)
                elif isinstance(result, Exception):
                    logger.error(f"Scraping task failed: {result}")
                    self.stats.failed_scrapes += 1
        
        self.stats.finalize()
        return self.results
    
    async def _scrape_question_with_semaphore(self, semaphore: asyncio.Semaphore, 
                                            question: ScrapedQuestion, 
                                            progress: Progress, 
                                            task_id: TaskID) -> ScrapingResult:
        """Scrape a single question with concurrency control."""
        async with semaphore:
            result = await self._scrape_single_question(question)
            progress.update(task_id, advance=1)
            return result
    
    async def _scrape_single_question(self, question: ScrapedQuestion) -> ScrapingResult:
        """Scrape a single question from all available platforms."""
        start_time = time.time()
        
        result = ScrapingResult(
            question_id=question.id,
            success=False
        )
        
        # Get all available URLs for this question
        urls_to_scrape = self._get_urls_to_scrape(question.links)
        
        if not urls_to_scrape:
            logger.warning(f"No URLs to scrape for question {question.id}")
            return result
        
        # Scrape from each platform
        scraping_tasks = []
        for platform, url in urls_to_scrape.items():
            if platform in self.scrapers:
                task = self._scrape_from_platform(platform, url, question.id)
                scraping_tasks.append(task)
        
        if scraping_tasks:
            platform_results = await asyncio.gather(*scraping_tasks, return_exceptions=True)
            
            # Process results
            for platform_result in platform_results:
                if isinstance(platform_result, tuple):
                    platform, content = platform_result
                    if content.scraping_success:
                        result.content[platform] = content
                        result.platforms_scraped.append(platform)
                    else:
                        result.errors[platform] = content.error_message or "Unknown error"
                elif isinstance(platform_result, Exception):
                    logger.error(f"Platform scraping failed: {platform_result}")
        
        result.success = len(result.content) > 0
        result.total_duration = time.time() - start_time
        
        return result
    
    async def _scrape_from_platform(self, platform: Platform, url: str, question_id: str) -> tuple:
        """Scrape content from a specific platform."""
        try:
            # Apply rate limiting
            throttler = self.throttlers.get(platform.value)
            if throttler:
                await throttler.acquire()
            
            scraper = self.scrapers[platform]
            content = await scraper.scrape_question(url)
            
            logger.info(f"Scraped {question_id} from {platform.value}: {'✅' if content.scraping_success else '❌'}")
            
            return platform, content
            
        except Exception as e:
            logger.error(f"Error scraping {question_id} from {platform.value}: {e}")
            return platform, ScrapedQuestionContent(
                platform=platform,
                url=url,
                scraping_success=False,
                error_message=str(e)
            )
    
    def _extract_questions_from_a2z(self, a2z_data: List[Dict]) -> List[ScrapedQuestion]:
        """Extract questions from A2Z JSON data."""
        questions = []
        
        for step in a2z_data:
            for sub_step in step.get('sub_steps', []):
                for topic in sub_step.get('topics', []):
                    try:
                        # Create links object
                        links = QuestionLinks(
                            post_link=topic.get('post_link'),
                            yt_link=topic.get('yt_link'),
                            plus_link=topic.get('plus_link'),
                            editorial_link=topic.get('editorial_link'),
                            gfg_link=topic.get('gfg_link'),
                            cs_link=topic.get('cs_link'),
                            lc_link=topic.get('lc_link')
                        )
                        
                        # Create question object
                        question = ScrapedQuestion(
                            id=topic.get('id', ''),
                            step_no=topic.get('step_no', 0),
                            sub_step_no=topic.get('sub_step_no', 0),
                            sl_no=topic.get('sl_no', 0),
                            step_title=topic.get('step_title', ''),
                            sub_step_title=topic.get('sub_step_title', ''),
                            question_title=topic.get('question_title', ''),
                            difficulty=topic.get('difficulty', 0),
                            ques_topic=topic.get('ques_topic', ''),
                            company_tags=topic.get('company_tags'),
                            links=links
                        )
                        
                        questions.append(question)
                        
                    except Exception as e:
                        logger.error(f"Error processing topic {topic.get('id', 'unknown')}: {e}")
                        continue
        
        return questions
    
    def _get_urls_to_scrape(self, links: QuestionLinks) -> Dict[Platform, str]:
        """Get URLs to scrape organized by platform."""
        urls = {}
        
        # Map links to platforms
        link_mapping = [
            (links.lc_link, Platform.LEETCODE),
            (links.gfg_link, Platform.GEEKSFORGEEKS),
            (links.cs_link, Platform.CODINGNINJAS)
        ]
        
        for url, platform in link_mapping:
            if url and url.strip():
                # Verify the URL actually belongs to the expected platform
                detected_platform = identify_platform(url)
                if detected_platform == platform.value:
                    urls[platform] = url
                else:
                    logger.warning(f"URL {url} detected as {detected_platform}, expected {platform.value}")
        
        return urls
    
    def save_results(self, output_file: Path, backup: bool = True):
        """Save scraping results to JSON file."""
        try:
            # Prepare data for export
            export_data = {
                'metadata': {
                    'scraped_at': datetime.now().isoformat(),
                    'total_questions': len(self.results),
                    'successful_scrapes': sum(1 for r in self.results if r.success),
                    'total_duration': self.stats.total_duration,
                    'platform_stats': self.stats.platform_stats
                },
                'questions': []
            }
            
            # Convert results to serializable format
            for result in self.results:
                question_data = {
                    'question_id': result.question_id,
                    'success': result.success,
                    'platforms_scraped': [p.value for p in result.platforms_scraped],
                    'content': {p.value: content.dict() for p, content in result.content.items()},
                    'errors': {p.value: error for p, error in result.errors.items()},
                    'total_duration': result.total_duration,
                    'scraped_at': result.scraped_at.isoformat()
                }
                export_data['questions'].append(question_data)
            
            # Save main file
            save_json(export_data, output_file)
            console.print(f"💾 Results saved to {output_file}", style="bold green")
            
            # Create backup if requested
            if backup:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = CONFIG.backup_dir / f"scraped_results_{timestamp}.json"
                save_json(export_data, backup_file)
                console.print(f"💾 Backup saved to {backup_file}", style="green")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise
    
    def print_summary(self):
        """Print a summary of scraping results."""
        console.print("\n" + "="*50, style="bold")
        console.print("📊 SCRAPING SUMMARY", style="bold blue", justify="center")
        console.print("="*50, style="bold")
        
        # Create summary table
        table = Table(title="Scraping Statistics")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        table.add_row("Total Questions", str(self.stats.total_questions))
        table.add_row("Successful Scrapes", str(self.stats.successful_scrapes))
        table.add_row("Failed Scrapes", str(self.stats.failed_scrapes))
        
        if self.stats.total_duration:
            table.add_row("Total Duration", f"{self.stats.total_duration:.2f}s")
            table.add_row("Avg Time per Question", f"{self.stats.total_duration/self.stats.total_questions:.2f}s")
        
        console.print(table)
        
        # Platform-specific stats
        if self.stats.platform_stats:
            console.print("\n📈 Platform Statistics:", style="bold yellow")
            
            platform_table = Table()
            platform_table.add_column("Platform", style="cyan")
            platform_table.add_column("Successful", style="green")
            platform_table.add_column("Failed", style="red")
            platform_table.add_column("Success Rate", style="blue")
            
            for platform, stats in self.stats.platform_stats.items():
                success = stats.get('success', 0)
                failed = stats.get('failed', 0)
                total = success + failed
                success_rate = f"{(success/total)*100:.1f}%" if total > 0 else "0%"
                
                platform_table.add_row(
                    platform.title(),
                    str(success),
                    str(failed),
                    success_rate
                )
            
            console.print(platform_table)
