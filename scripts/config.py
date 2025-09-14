"""
Configuration settings for the A2Z question scraper.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ScrapingConfig:
    """Configuration for scraping parameters."""
    
    # Rate limiting settings
    requests_per_minute: int = 30
    concurrent_limit: int = 3
    retry_attempts: int = 3
    retry_delay: float = 2.0
    
    # Browser settings
    headless: bool = True
    timeout: int = 30000  # 30 seconds
    
    # Output settings
    output_dir: Path = Path("./scraped_data")
    backup_dir: Path = Path("./scraped_data/backups")
    
    # Platform-specific settings
    platform_configs: Dict[str, Dict] = None
    
    def __post_init__(self):
        if self.platform_configs is None:
            self.platform_configs = {
                "leetcode": {
                    "base_url": "https://leetcode.com",
                    "selectors": {
                        "title": '[data-cy="question-title"]',
                        "description": '[data-cy="question-content"]',
                        "difficulty": '[diff="easy"], [diff="medium"], [diff="hard"]',
                        "tags": '[data-cy="question-topics"] a',
                        "examples": '.example',
                        "constraints": '.constraints'
                    },
                    "rate_limit": 20  # requests per minute
                },
                "geeksforgeeks": {
                    "base_url": "https://practice.geeksforgeeks.org",
                    "selectors": {
                        "title": '.problem-title',
                        "description": '.problem-statement',
                        "difficulty": '.difficulty-tags',
                        "examples": '.example',
                        "constraints": '.expected-time-complexity'
                    },
                    "rate_limit": 40
                },
                "codingninjas": {
                    "base_url": "https://www.codingninjas.com",
                    "selectors": {
                        "title": '.problem-title',
                        "description": '.problem-statement',
                        "difficulty": '.difficulty',
                        "examples": '.sample-io'
                    },
                    "rate_limit": 25
                }
            }
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)

# Global config instance
CONFIG = ScrapingConfig()

# Platform URL patterns for link identification
PLATFORM_PATTERNS = {
    "leetcode": ["leetcode.com"],
    "geeksforgeeks": ["geeksforgeeks.org", "practice.geeksforgeeks.org"],
    "codingninjas": ["codingninjas.com"]
}

def identify_platform(url: str) -> Optional[str]:
    """Identify the platform from a URL."""
    if not url:
        return None
    
    url_lower = url.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        if any(pattern in url_lower for pattern in patterns):
            return platform
    return None

def get_platform_config(platform: str) -> Dict:
    """Get configuration for a specific platform."""
    return CONFIG.platform_configs.get(platform, {})
