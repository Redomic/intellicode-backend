"""
Base scraper class and common utilities.
"""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from fake_useragent import UserAgent

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models import ScrapedQuestionContent, Platform, DifficultyLevel, TestCase
from config import CONFIG, get_platform_config

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all platform scrapers."""
    
    def __init__(self, platform: Platform):
        self.platform = platform
        self.config = get_platform_config(platform.value)
        self.ua = UserAgent()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize the scraper with browser setup."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=CONFIG.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        )
        
        self.context = await self.browser.new_context(
            user_agent=self.ua.random,
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # Set timeouts
        self.context.set_default_timeout(CONFIG.timeout)
        
        logger.info(f"Initialized {self.platform.value} scraper")
    
    async def cleanup(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info(f"Cleaned up {self.platform.value} scraper")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def scrape_question(self, url: str) -> ScrapedQuestionContent:
        """
        Scrape a question from the given URL.
        
        Args:
            url: The URL to scrape
            
        Returns:
            ScrapedQuestionContent with the scraped data
        """
        start_time = time.time()
        
        try:
            page = await self.context.new_page()
            
            # Navigate to the page
            await page.goto(url, wait_until='networkidle')
            
            # Wait for content to load
            await self.wait_for_content(page)
            
            # Extract content
            content = await self.extract_content(page, url)
            content.scraping_duration = time.time() - start_time
            content.scraping_success = True
            
            await page.close()
            return content
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return ScrapedQuestionContent(
                platform=self.platform,
                url=url,
                scraping_duration=time.time() - start_time,
                scraping_success=False,
                error_message=str(e)
            )
    
    @abstractmethod
    async def wait_for_content(self, page: Page):
        """Wait for the main content to load on the page."""
        pass
    
    @abstractmethod
    async def extract_content(self, page: Page, url: str) -> ScrapedQuestionContent:
        """Extract content from the page."""
        pass
    
    async def get_page_source(self, page: Page) -> BeautifulSoup:
        """Get BeautifulSoup object from page source."""
        content = await page.content()
        return BeautifulSoup(content, 'html.parser')
    
    def normalize_difficulty(self, difficulty_text: str) -> DifficultyLevel:
        """Normalize difficulty text to standard enum."""
        if not difficulty_text:
            return DifficultyLevel.UNKNOWN
        
        difficulty_lower = difficulty_text.lower().strip()
        
        if 'easy' in difficulty_lower:
            return DifficultyLevel.EASY
        elif 'medium' in difficulty_lower:
            return DifficultyLevel.MEDIUM
        elif 'hard' in difficulty_lower:
            return DifficultyLevel.HARD
        else:
            return DifficultyLevel.UNKNOWN
    
    def extract_test_cases_from_text(self, text: str) -> List[TestCase]:
        """Extract test cases from example text."""
        test_cases = []
        
        # Common patterns for test case extraction
        import re
        
        # Pattern for Input/Output format
        input_output_pattern = r'Input:\s*(.*?)\s*Output:\s*(.*?)(?=Input:|$)'
        matches = re.findall(input_output_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for input_text, output_text in matches:
            test_cases.append(TestCase(
                input=input_text.strip(),
                output=output_text.strip()
            ))
        
        return test_cases
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        import re
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
