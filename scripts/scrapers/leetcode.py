"""
LeetCode-specific scraper implementation.
"""
import asyncio
import json
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

class LeetCodeScraper(BaseScraper):
    """Scraper for LeetCode problems."""
    
    def __init__(self):
        super().__init__(Platform.LEETCODE)
    
    async def wait_for_content(self, page: Page):
        """Wait for LeetCode content to load."""
        try:
            # Wait for the main content area
            await page.wait_for_selector('[data-cy="question-content"]', timeout=15000)
            
            # Additional wait for dynamic content
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.warning(f"Content selector not found, trying alternative: {e}")
            # Fallback selectors
            try:
                await page.wait_for_selector('.content__u3I1', timeout=10000)
            except:
                # If all fails, just wait a bit for JS to render
                await asyncio.sleep(5)
    
    async def extract_content(self, page: Page, url: str) -> ScrapedQuestionContent:
        """Extract content from LeetCode page."""
        soup = await self.get_page_source(page)
        
        content = ScrapedQuestionContent(
            platform=Platform.LEETCODE,
            url=url
        )
        
        try:
            # Extract title
            content.title = await self._extract_title(page, soup)
            
            # Extract problem statement
            content.problem_statement = await self._extract_problem_statement(page, soup)
            
            # Extract difficulty
            content.difficulty = await self._extract_difficulty(page, soup)
            
            # Extract tags
            content.tags = await self._extract_tags(page, soup)
            
            # Extract examples and test cases
            content.examples = await self._extract_examples(page, soup)
            content.test_cases = await self._extract_test_cases(page, soup)
            
            # Extract constraints
            content.constraints = await self._extract_constraints(page, soup)
            
            # Extract code templates
            content.code_templates = await self._extract_code_templates(page)
            
            # Extract additional metadata
            await self._extract_metadata(page, soup, content)
            
        except Exception as e:
            logger.error(f"Error extracting LeetCode content from {url}: {e}")
            content.error_message = str(e)
            content.scraping_success = False
        
        return content
    
    async def _extract_title(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the problem title."""
        # Try multiple selectors
        selectors = [
            '[data-cy="question-title"]',
            'h1',
            '.css-v3d350',
            '.question-title'
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
        title_element = soup.find('h1') or soup.find(class_='css-v3d350')
        if title_element:
            return self.clean_text(title_element.get_text())
        
        return "Title not found"
    
    async def _extract_problem_statement(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the problem statement."""
        selectors = [
            '[data-cy="question-content"]',
            '.content__u3I1',
            '.question-content__JfgR'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.text_content()
                    if content and len(content.strip()) > 50:  # Reasonable content length
                        return self.clean_text(content)
            except:
                continue
        
        # Fallback to BeautifulSoup
        content_div = soup.find(class_='content__u3I1') or soup.find(class_='question-content__JfgR')
        if content_div:
            return self.clean_text(content_div.get_text())
        
        return "Problem statement not found"
    
    async def _extract_difficulty(self, page: Page, soup: BeautifulSoup) -> str:
        """Extract the difficulty level."""
        selectors = [
            '[diff]',
            '.difficulty',
            '[data-cy="difficulty"]'
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
        
        # Try to extract from class names or attributes
        difficulty_elements = soup.find_all(attrs={'diff': True})
        if difficulty_elements:
            diff_attr = difficulty_elements[0].get('diff')
            return self.normalize_difficulty(diff_attr)
        
        return self.normalize_difficulty("")
    
    async def _extract_tags(self, page: Page, soup: BeautifulSoup) -> List[str]:
        """Extract problem tags."""
        tags = []
        
        selectors = [
            '[data-cy="question-topics"] a',
            '.topic-tag',
            '.tag'
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    tag_text = await element.text_content()
                    if tag_text and tag_text.strip():
                        tags.append(self.clean_text(tag_text))
            except:
                continue
        
        return list(set(tags))  # Remove duplicates
    
    async def _extract_examples(self, page: Page, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract examples from the problem."""
        examples = []
        
        # Look for example sections
        example_elements = soup.find_all(string=re.compile(r'Example\s*\d*:', re.IGNORECASE))
        
        for example_element in example_elements:
            try:
                # Find the parent container
                parent = example_element.parent
                while parent and parent.name not in ['div', 'pre', 'section']:
                    parent = parent.parent
                
                if parent:
                    example_text = parent.get_text()
                    
                    # Extract input and output
                    input_match = re.search(r'Input:\s*(.*?)(?=Output:|$)', example_text, re.DOTALL | re.IGNORECASE)
                    output_match = re.search(r'Output:\s*(.*?)(?=Explanation:|Example|$)', example_text, re.DOTALL | re.IGNORECASE)
                    explanation_match = re.search(r'Explanation:\s*(.*?)(?=Example|$)', example_text, re.DOTALL | re.IGNORECASE)
                    
                    example_data = {}
                    if input_match:
                        example_data['input'] = self.clean_text(input_match.group(1))
                    if output_match:
                        example_data['output'] = self.clean_text(output_match.group(1))
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
        constraint_keywords = ['Constraints:', 'Constraint:', 'Note:']
        
        for keyword in constraint_keywords:
            constraint_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
            
            for element in constraint_elements:
                try:
                    parent = element.parent
                    while parent and parent.name not in ['div', 'section', 'ul', 'ol']:
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
    
    async def _extract_code_templates(self, page: Page) -> Dict[str, str]:
        """Extract code templates for different languages."""
        templates = {}
        
        try:
            # Try to click on different language tabs and extract code
            language_selectors = [
                '[data-cy="lang-select"]',
                '.language-picker',
                '[role="tablist"] button'
            ]
            
            for selector in language_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        break
                except:
                    continue
            
            # For now, just try to get the default visible code
            code_selectors = [
                '.monaco-editor textarea',
                '.CodeMirror-code',
                '.ace_content',
                'textarea[autocomplete="off"]'
            ]
            
            for selector in code_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        code = await element.text_content()
                        if code and code.strip():
                            templates['default'] = code.strip()
                            break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting code templates: {e}")
        
        return templates
    
    async def _extract_metadata(self, page: Page, soup: BeautifulSoup, content: ScrapedQuestionContent):
        """Extract additional metadata."""
        try:
            # Try to get likes/dislikes if visible
            like_selectors = [
                '[data-cy="like-button"]',
                '.like-button',
                '.thumbs-up'
            ]
            
            for selector in like_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        like_text = await element.text_content()
                        if like_text and like_text.isdigit():
                            content.likes = int(like_text)
                        break
                except:
                    continue
            
            # Try to extract editorial link
            editorial_selectors = [
                'a[href*="solution"]',
                'a[href*="editorial"]',
                '.solution-link'
            ]
            
            for selector in editorial_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        href = await element.get_attribute('href')
                        if href:
                            content.editorial_url = href
                            break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
