"""
GeeksforGeeks-specific scraper implementation.
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

class GeeksforGeeksScraper(BaseScraper):
    """Scraper for GeeksforGeeks problems."""
    
    def __init__(self):
        super().__init__(Platform.GEEKSFORGEEKS)
    
    async def wait_for_content(self, page: Page):
        """Wait for GeeksforGeeks content to load."""
        try:
            # Wait for the main content area
            await page.wait_for_selector('.problem-statement', timeout=15000)
            
            # Additional wait for dynamic content
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.warning(f"Content selector not found, trying alternative: {e}")
            # Fallback selectors
            try:
                await page.wait_for_selector('.problemStatement', timeout=10000)
            except:
                # If all fails, just wait a bit
                await asyncio.sleep(5)
    
    async def extract_content(self, page: Page, url: str) -> ScrapedQuestionContent:
        """Extract content from GeeksforGeeks page."""
        soup = await self.get_page_source(page)
        
        content = ScrapedQuestionContent(
            platform=Platform.GEEKSFORGEEKS,
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
            logger.error(f"Error extracting GeeksforGeeks content from {url}: {e}")
            content.error_message = str(e)
            content.scraping_success = False
        
        return content
    
    async def _extract_title(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the problem title."""
        selectors = [
            '.problem-title',
            '.problemTitle',
            'h1',
            '.head'
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
        title_element = soup.find(class_='problem-title') or soup.find(class_='problemTitle') or soup.find('h1')
        if title_element:
            return self.clean_text(title_element.get_text())
        
        return "Title not found"
    
    async def _extract_problem_statement(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the problem statement."""
        selectors = [
            '.problem-statement',
            '.problemStatement',
            '.problem_statement',
            '.problem-description'
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
                      soup.find(class_='problemStatement') or
                      soup.find(class_='problem_statement'))
        if content_div:
            return self.clean_text(content_div.get_text())
        
        return "Problem statement not found"
    
    async def _extract_difficulty(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the difficulty level."""
        selectors = [
            '.difficulty-tags',
            '.difficulty',
            '.problemDifficulty',
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
        
        # Look for difficulty in text content
        difficulty_patterns = [
            r'Difficulty:\s*(\w+)',
            r'Level:\s*(\w+)',
            r'(Easy|Medium|Hard)',
        ]
        
        page_text = soup.get_text()
        for pattern in difficulty_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return self.normalize_difficulty(match.group(1))
        
        return self.normalize_difficulty("")
    
    async def _extract_examples(self, page: Page, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract examples from the problem."""
        examples = []
        
        # Look for example sections
        example_patterns = [
            r'Example\s*\d*:',
            r'Sample\s*Input\s*\d*',
            r'Test\s*Case\s*\d*'
        ]
        
        for pattern in example_patterns:
            example_elements = soup.find_all(string=re.compile(pattern, re.IGNORECASE))
            
            for example_element in example_elements:
                try:
                    # Find the parent container
                    parent = example_element.parent
                    while parent and parent.name not in ['div', 'pre', 'section', 'p']:
                        parent = parent.parent
                    
                    if parent:
                        example_text = parent.get_text()
                        
                        # Extract input and output
                        input_patterns = [
                            r'Input:\s*(.*?)(?=Output:|Explanation:|$)',
                            r'Sample\s*Input:\s*(.*?)(?=Sample\s*Output:|Output:|$)'
                        ]
                        
                        output_patterns = [
                            r'Output:\s*(.*?)(?=Explanation:|Example|$)',
                            r'Sample\s*Output:\s*(.*?)(?=Explanation:|Example|$)'
                        ]
                        
                        example_data = {}
                        
                        for input_pattern in input_patterns:
                            input_match = re.search(input_pattern, example_text, re.DOTALL | re.IGNORECASE)
                            if input_match:
                                example_data['input'] = self.clean_text(input_match.group(1))
                                break
                        
                        for output_pattern in output_patterns:
                            output_match = re.search(output_pattern, example_text, re.DOTALL | re.IGNORECASE)
                            if output_match:
                                example_data['output'] = self.clean_text(output_match.group(1))
                                break
                        
                        explanation_match = re.search(r'Explanation:\s*(.*?)(?=Example|$)', example_text, re.DOTALL | re.IGNORECASE)
                        if explanation_match:
                            example_data['explanation'] = self.clean_text(explanation_match.group(1))
                        
                        if example_data:
                            examples.append(example_data)
                            
                except Exception as e:
                    logger.warning(f"Error extracting example: {e}")
                    continue
        
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
            'Expected Time Complexity:',
            'Expected Space Complexity:'
        ]
        
        for keyword in constraint_keywords:
            constraint_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
            
            for element in constraint_elements:
                try:
                    parent = element.parent
                    while parent and parent.name not in ['div', 'section', 'ul', 'ol', 'p']:
                        parent = parent.parent
                    
                    if parent:
                        # Extract list items or text content
                        li_elements = parent.find_all('li')
                        if li_elements:
                            for li in li_elements:
                                constraint_text = self.clean_text(li.get_text())
                                if constraint_text:
                                    constraints.append(constraint_text)
                        else:
                            constraint_text = self.clean_text(parent.get_text())
                            if constraint_text:
                                # Split by common delimiters
                                lines = constraint_text.split('\n')
                                for line in lines:
                                    line = line.strip()
                                    if line and not any(kw in line for kw in constraint_keywords):
                                        constraints.append(line)
                except Exception as e:
                    logger.warning(f"Error extracting constraint: {e}")
                    continue
        
        return list(set(constraints))  # Remove duplicates
    
    async def _extract_metadata(self, page: Page, soup: BeautifulSoup, content: ScrapedQuestionContent):
        """Extract additional metadata."""
        try:
            # Extract tags if available
            tag_selectors = [
                '.tags a',
                '.topic-tags a',
                '.tag-list a'
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
