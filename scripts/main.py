#!/usr/bin/env python3
"""
Main script for scraping A2Z DSA questions from multiple platforms.

Usage:
    python main.py [options]

Examples:
    # Scrape all questions
    python main.py --input a2z.json --output scraped_results.json
    
    # Test with limited questions
    python main.py --input a2z.json --output test_results.json --max-questions 10
    
    # Enable debug logging
    python main.py --input a2z.json --output results.json --log-level DEBUG
"""
import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console

from config import CONFIG
from utils import setup_logging, validate_environment, print_file_info
from scraper_orchestrator import ScraperOrchestrator

console = Console()

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="A2Z DSA Question Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --input a2z.json --output scraped_results.json
    %(prog)s --input a2z.json --output test_results.json --max-questions 10 --log-level DEBUG
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("a2z.json"),
        help="Path to the A2Z JSON file (default: a2z.json)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("scraped_results.json"),
        help="Path to save scraped results (default: scraped_results.json)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--max-questions",
        type=int,
        help="Maximum number of questions to scrape (for testing)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (optional)"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup files"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browsers in headless mode (default: True)"
    )
    
    parser.add_argument(
        "--concurrent-limit",
        type=int,
        default=3,
        help="Maximum concurrent scraping tasks (default: 3)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for page loading (default: 30)"
    )
    
    return parser.parse_args()

def validate_arguments(args: argparse.Namespace) -> bool:
    """Validate command line arguments."""
    # Check input file exists
    if not args.input.exists():
        console.print(f"❌ Input file not found: {args.input}", style="bold red")
        return False
    
    # Check input file is JSON
    if args.input.suffix.lower() != '.json':
        console.print(f"⚠️  Input file should be a JSON file: {args.input}", style="yellow")
    
    # Validate output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Validate numeric arguments
    if args.max_questions is not None and args.max_questions <= 0:
        console.print("❌ max-questions must be positive", style="bold red")
        return False
    
    if args.concurrent_limit <= 0:
        console.print("❌ concurrent-limit must be positive", style="bold red")
        return False
    
    if args.timeout <= 0:
        console.print("❌ timeout must be positive", style="bold red")
        return False
    
    return True

def update_config(args: argparse.Namespace) -> None:
    """Update global configuration with command line arguments."""
    CONFIG.headless = args.headless
    CONFIG.concurrent_limit = args.concurrent_limit
    CONFIG.timeout = args.timeout * 1000  # Convert to milliseconds

async def main() -> int:
    """Main entry point."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set up logging
        setup_logging(args.log_level, args.log_file)
        
        # Validate environment
        if not validate_environment():
            return 1
        
        # Validate arguments
        if not validate_arguments(args):
            return 1
        
        # Update configuration
        update_config(args)
        
        # Print startup information
        console.print("🚀 A2Z DSA Question Scraper", style="bold blue", justify="center")
        console.print("=" * 50, style="blue")
        
        print_file_info(args.input)
        
        console.print(f"\n⚙️  Configuration:", style="bold yellow")
        console.print(f"   Max questions: {args.max_questions or 'All'}")
        console.print(f"   Concurrent limit: {args.concurrent_limit}")
        console.print(f"   Timeout: {args.timeout}s")
        console.print(f"   Headless: {args.headless}")
        console.print(f"   Log level: {args.log_level}")
        
        console.print(f"\n🎯 Starting scraper...", style="bold green")
        
        # Initialize and run scraper
        async with ScraperOrchestrator() as orchestrator:
            # Scrape questions
            results = await orchestrator.scrape_questions_from_a2z(
                a2z_file=args.input,
                max_questions=args.max_questions
            )
            
            # Save results
            orchestrator.save_results(
                output_file=args.output,
                backup=not args.no_backup
            )
            
            # Print summary
            orchestrator.print_summary()
            
            console.print(f"\n🎉 Scraping completed successfully!", style="bold green")
            console.print(f"📊 Results saved to: {args.output}", style="blue")
            
            return 0
            
    except KeyboardInterrupt:
        console.print("\n⚠️  Scraping interrupted by user", style="bold yellow")
        return 130
    
    except Exception as e:
        console.print(f"\n❌ Scraping failed: {e}", style="bold red")
        if args.log_level == "DEBUG":
            import traceback
            console.print(traceback.format_exc(), style="red")
        return 1

def run_with_conda_check():
    """Run the script with conda environment check."""
    try:
        # Check if running in correct conda environment
        import os
        conda_env = os.environ.get('CONDA_DEFAULT_ENV')
        
        if conda_env != 'intellicode':
            console.print("⚠️  Warning: Not running in 'intellicode' conda environment", style="bold yellow")
            console.print("   Activate with: conda activate intellicode", style="yellow")
        else:
            console.print(f"✅ Running in conda environment: {conda_env}", style="green")
        
        # Install playwright browsers if needed
        try:
            import subprocess
            result = subprocess.run(['playwright', 'install', 'chromium'], 
                                  capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                console.print("✅ Playwright browsers ready", style="green")
        except Exception as e:
            console.print(f"⚠️  Could not install playwright browsers: {e}", style="yellow")
            console.print("   Run manually: playwright install chromium", style="yellow")
        
        # Run main function
        return asyncio.run(main())
        
    except Exception as e:
        console.print(f"❌ Setup failed: {e}", style="bold red")
        return 1

if __name__ == "__main__":
    exit_code = run_with_conda_check()
    sys.exit(exit_code)
