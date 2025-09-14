"""
Scraper modules for different platforms.
"""
from scrapers.base import BaseScraper
from scrapers.leetcode import LeetCodeScraper
from scrapers.geeksforgeeks import GeeksforGeeksScraper
from scrapers.codingninjas import CodingNinjasScraper

__all__ = [
    'BaseScraper',
    'LeetCodeScraper', 
    'GeeksforGeeksScraper',
    'CodingNinjasScraper'
]
