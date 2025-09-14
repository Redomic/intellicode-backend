#!/usr/bin/env python3
"""
Test script for the A2Z DSA Question Scraper.
"""
import asyncio
import json
from pathlib import Path
from rich.console import Console

from utils import setup_logging
from scraper_orchestrator import ScraperOrchestrator

console = Console()

async def test_basic_functionality():
    """Test basic scraper functionality with sample data."""
    console.print("🧪 Testing basic scraper functionality...", style="bold blue")
    
    # Create sample test data
    test_data = [
        {
            "step_no": 1,
            "step_title": "Test Step",
            "sub_steps": [
                {
                    "sub_step_no": 1,
                    "sub_step_title": "Test Sub Step",
                    "topics": [
                        {
                            "id": "test_question_1",
                            "step_no": 1,
                            "sub_step_no": 1,
                            "sl_no": 1,
                            "step_title": "Test Step",
                            "sub_step_title": "Test Sub Step",
                            "question_title": "Two Sum",
                            "post_link": None,
                            "yt_link": None,
                            "plus_link": None,
                            "editorial_link": None,
                            "gfg_link": None,
                            "cs_link": None,
                            "lc_link": "https://leetcode.com/problems/two-sum/",
                            "company_tags": None,
                            "difficulty": 0,
                            "ques_topic": '[{"value":"arrays","label":"Arrays"}]'
                        },
                        {
                            "id": "test_question_2",
                            "step_no": 1,
                            "sub_step_no": 1,
                            "sl_no": 2,
                            "step_title": "Test Step",
                            "sub_step_title": "Test Sub Step", 
                            "question_title": "Add Two Numbers",
                            "post_link": None,
                            "yt_link": None,
                            "plus_link": None,
                            "editorial_link": None,
                            "gfg_link": None,
                            "cs_link": None,
                            "lc_link": "https://leetcode.com/problems/add-two-numbers/",
                            "company_tags": None,
                            "difficulty": 1,
                            "ques_topic": '[{"value":"linked-list","label":"Linked List"}]'
                        }
                    ]
                }
            ]
        }
    ]
    
    # Save test data to temporary file
    test_file = Path("test_a2z.json")
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    console.print(f"📝 Created test file: {test_file}", style="green")
    
    try:
        # Test scraping
        async with ScraperOrchestrator() as orchestrator:
            results = await orchestrator.scrape_questions_from_a2z(
                a2z_file=test_file,
                max_questions=2
            )
            
            # Check results
            console.print(f"📊 Scraped {len(results)} questions", style="blue")
            
            for result in results:
                console.print(f"   Question {result.question_id}: {'✅' if result.success else '❌'}")
                if result.content:
                    for platform, content in result.content.items():
                        console.print(f"     {platform.value}: {content.title[:50]}...")
                
                if result.errors:
                    for platform, error in result.errors.items():
                        console.print(f"     {platform.value} error: {error[:100]}...", style="red")
            
            # Save test results
            test_output = Path("test_results.json")
            orchestrator.save_results(test_output, backup=False)
            
            # Print summary
            orchestrator.print_summary()
            
            console.print(f"✅ Test completed successfully!", style="bold green")
            console.print(f"📄 Test results saved to: {test_output}", style="green")
            
    except Exception as e:
        console.print(f"❌ Test failed: {e}", style="bold red")
        raise
    
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()
            console.print(f"🗑️  Cleaned up test file: {test_file}", style="dim")

async def test_url_identification():
    """Test URL identification and platform detection."""
    console.print("\n🔍 Testing URL identification...", style="bold blue")
    
    from config import identify_platform
    
    test_urls = [
        ("https://leetcode.com/problems/two-sum/", "leetcode"),
        ("https://practice.geeksforgeeks.org/problems/array-sum", "geeksforgeeks"),
        ("https://www.codingninjas.com/studio/problems/array", "codingninjas"),
        ("https://invalid-url.com/problem", None)
    ]
    
    for url, expected in test_urls:
        detected = identify_platform(url)
        status = "✅" if detected == expected else "❌"
        console.print(f"   {status} {url} -> {detected} (expected: {expected})")

def test_configuration():
    """Test configuration loading."""
    console.print("\n⚙️  Testing configuration...", style="bold blue")
    
    from config import CONFIG, get_platform_config
    
    console.print(f"   Concurrent limit: {CONFIG.concurrent_limit}")
    console.print(f"   Headless mode: {CONFIG.headless}")
    console.print(f"   Output directory: {CONFIG.output_dir}")
    
    # Test platform configs
    for platform in ["leetcode", "geeksforgeeks", "codingninjas"]:
        config = get_platform_config(platform)
        console.print(f"   {platform}: {len(config)} settings configured")

async def main():
    """Run all tests."""
    setup_logging("INFO")
    
    console.print("🧪 A2Z DSA Question Scraper Tests", style="bold blue", justify="center")
    console.print("=" * 50, style="blue")
    
    try:
        # Test configuration
        test_configuration()
        
        # Test URL identification
        await test_url_identification()
        
        # Test basic functionality
        await test_basic_functionality()
        
        console.print("\n🎉 All tests passed!", style="bold green")
        return 0
        
    except Exception as e:
        console.print(f"\n❌ Tests failed: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="red")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
