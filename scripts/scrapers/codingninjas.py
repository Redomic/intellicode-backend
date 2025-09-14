"""
CodingNinjas-specific scraper implementation.
"""
import asyncio
import re
from typing import List, Dict, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
import logging

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scrapers.base import BaseScraper
from models import ScrapedQuestionContent, Platform, TestCase
from config import CONFIG

logger = logging.getLogger(__name__)

class CodingNinjasScraper(BaseScraper):
    """Scraper for CodingNinjas problems."""
    
    def __init__(self):
        super().__init__(Platform.CODINGNINJAS)
    
    async def wait_for_content(self, page: Page):
        """Wait for CodingNinjas content to load."""
        try:
            # Wait for the main content area
            await page.wait_for_selector('.problem-statement', timeout=15000)
            
            # Additional wait for dynamic content
            await asyncio.sleep(3)
            
        except Exception as e:
            logger.warning(f"Content selector not found, trying alternative: {e}")
            # Fallback selectors
            try:
                await page.wait_for_selector('.problem-description', timeout=10000)
            except:
                # If all fails, just wait a bit
                await asyncio.sleep(5)
    
    async def extract_content(self, page: Page, url: str) -> ScrapedQuestionContent:
        """Extract content from CodingNinjas page."""
        soup = await self.get_page_source(page)
        
        content = ScrapedQuestionContent(
            platform=Platform.CODINGNINJAS,
            url=url
        )
        
        try:
            # Extract title
            content.title = await self._extract_title(page, soup)
            
            # Extract problem statement
            content.problem_statement = await self._extract_problem_statement(page, soup)
            
            # Extract difficulty
            content.difficulty = await self._extract_difficulty(page, soup)
            
            # Extract examples and test cases
            content.examples = await self._extract_examples(page, soup)
            content.test_cases = await self._extract_test_cases(page, soup)
            
            # Extract constraints
            content.constraints = await self._extract_constraints(page, soup)
            
            # Extract additional metadata
            await self._extract_metadata(page, soup, content)
            
        except Exception as e:
            logger.error(f"Error extracting CodingNinjas content from {url}: {e}")
            content.error_message = str(e)
            content.scraping_success = False
        
        return content
    
    async def _extract_title(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the problem title."""
        selectors = [
            '.problem-title',
            '.problem-heading',
            'h1',
            '.title'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    title = await element.text_content()
                    if title and title.strip():
                        return self.clean_text(title)
            except:
                continue
        
        # Fallback to BeautifulSoup
        title_element = soup.find(class_='problem-title') or soup.find('h1')
        if title_element:
            return self.clean_text(title_element.get_text())
        
        return "Title not found"
    
    async def _extract_problem_statement(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the problem statement."""
        selectors = [
            '.problem-statement',
            '.problem-description',
            '.problem-content'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.text_content()
                    if content and len(content.strip()) > 50:
                        return self.clean_text(content)
            except:
                continue
        
        # Fallback to BeautifulSoup
        content_div = (soup.find(class_='problem-statement') or 
                      soup.find(class_='problem-description'))
        if content_div:
            return self.clean_text(content_div.get_text())
        
        return "Problem statement not found"
    
    async def _extract_difficulty(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the difficulty level."""
        selectors = [
            '.difficulty',
            '.problem-difficulty',
            '[data-difficulty]'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    difficulty = await element.text_content()
                    if difficulty:
                        return self.normalize_difficulty(difficulty)
            except:
                continue
        
        # Look for difficulty in URL or text content
        if '/easy/' in url.lower():
            return self.normalize_difficulty('easy')
        elif '/medium/' in url.lower():
            return self.normalize_difficulty('medium')
        elif '/hard/' in url.lower():
            return self.normalize_difficulty('hard')
        
        return self.normalize_difficulty("")
    
    async def _extract_examples(self, page: Page, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract examples from the problem."""
        examples = []
        
        # Look for sample input/output sections
        sample_io_selectors = [
            '.sample-io',
            '.sample-input-output',
            '.example'
        ]
        
        for selector in sample_io_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    example_text = await element.text_content()
                    if example_text:
                        example_data = self._parse_sample_io(example_text)
                        if example_data:
                            examples.append(example_data)
            except:
                continue
        
        # If no structured examples found, look for text patterns
        if not examples:
            examples = self._extract_examples_from_text(soup.get_text())
        
        return examples
    
    def _parse_sample_io(self, text: str) -> Dict[str, str]:
        """Parse sample input/output text."""
        example_data = {}
        
        # Common patterns for CodingNinjas
        input_patterns = [
            r'Sample\s*Input\s*\d*:\s*(.*?)(?=Sample\s*Output|Output:|$)',
            r'Input:\s*(.*?)(?=Output:|$)'
        ]
        
        output_patterns = [
            r'Sample\s*Output\s*\d*:\s*(.*?)(?=Explanation:|Sample\s*Input|$)',
            r'Output:\s*(.*?)(?=Explanation:|$)'
        ]
        
        for pattern in input_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                example_data['input'] = self.clean_text(match.group(1))
                break
        
        for pattern in output_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                example_data['output'] = self.clean_text(match.group(1))
                break
        
        explanation_match = re.search(r'Explanation:\s*(.*?)(?=Sample|$)', text, re.DOTALL | re.IGNORECASE)
        if explanation_match:
            example_data['explanation'] = self.clean_text(explanation_match.group(1))
        
        return example_data
    
    def _extract_examples_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract examples from full text using patterns."""
        examples = []
        
        # Split text into potential example sections
        example_sections = re.split(r'(Sample\s*Input\s*\d*|Example\s*\d*)', text, flags=re.IGNORECASE)
        
        for i in range(1, len(example_sections), 2):
            if i + 1 < len(example_sections):
                section_text = example_sections[i] + example_sections[i + 1]
                example_data = self._parse_sample_io(section_text)
                if example_data:
                    examples.append(example_data)
        
        return examples
    
    async def _extract_test_cases(self, page: Page, soup: BeautifulSoup) -> List[TestCase]:
        """Extract test cases from examples."""
        test_cases = []
        
        # Convert examples to test cases
        examples = await self._extract_examples(page, soup)
        for example in examples:
            if 'input' in example and 'output' in example:
                test_cases.append(TestCase(
                    input=example['input'],
                    output=example['output'],
                    explanation=example.get('explanation')
                ))
        
        return test_cases
    
    async def _extract_constraints(self, page: Page, soup: BeautifulSoup) -> List[str]:
        """Extract problem constraints."""
        constraints = []
        
        # Look for constraints section
        constraint_keywords = [
            'Constraints:',
            'Constraint:',
            'Note:',
            'Time Limit:',
            'Space Limit:'
        ]
        
        page_text = soup.get_text()
        
        for keyword in constraint_keywords:
            pattern = rf'{keyword}\s*(.*?)(?=Sample|Example|Note:|$)'
            match = re.search(pattern, page_text, re.DOTALL | re.IGNORECASE)
            
            if match:
                constraint_text = match.group(1).strip()
                if constraint_text:
                    # Split by newlines and clean
                    lines = constraint_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 10:  # Filter out very short lines
                            constraints.append(line)
        
        return list(set(constraints))  # Remove duplicates
    
    async def _extract_metadata(self, page: Page, soup: BeautifulSoup, content: ScrapedQuestionContent):
        """Extract additional metadata."""
        try:
            # Extract tags if available
            tag_selectors = [
                '.tags a',
                '.topic-tags',
                '.problem-tags'
            ]
            
            tags = []
            for selector in tag_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        tag_text = await element.text_content()
                        if tag_text and tag_text.strip():
                            tags.append(self.clean_text(tag_text))
                except:
                    continue
            
            content.tags = list(set(tags))
            
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
