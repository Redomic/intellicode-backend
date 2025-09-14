"""
Utility functions for the scraper.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console

console = Console()

def setup_logging(log_level: str = "INFO", log_file: Path = None) -> None:
    """Set up logging configuration with Rich formatting."""
    # Clear any existing handlers
    logging.getLogger().handlers = []
    
    # Set up Rich handler for console output
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True
    )
    rich_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        handlers=[rich_handler]
    )
    
    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logging.getLogger().addHandler(file_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('playwright').setLevel(logging.WARNING)

def validate_environment() -> bool:
    """Validate that the environment is properly set up."""
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            console.print("❌ Python 3.8+ is required", style="bold red")
            return False
        
        # Check required packages
        required_packages = {
            'playwright': 'playwright',
            'aiohttp': 'aiohttp', 
            'beautifulsoup4': 'bs4',
            'pydantic': 'pydantic',
            'tenacity': 'tenacity',
            'rich': 'rich'
        }
        
        missing_packages = []
        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
            except ImportError:
                missing_packages.append(package_name)
        
        if missing_packages:
            console.print(f"❌ Missing packages: {', '.join(missing_packages)}", style="bold red")
            console.print("Install with: pip install -r requirements.txt", style="yellow")
            return False
        
        console.print("✅ Environment validation passed", style="bold green")
        return True
        
    except Exception as e:
        console.print(f"❌ Environment validation failed: {e}", style="bold red")
        return False

def load_json(file_path: Path) -> Any:
    """Load JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"❌ File not found: {file_path}", style="bold red")
        raise
    except json.JSONDecodeError as e:
        console.print(f"❌ Invalid JSON in {file_path}: {e}", style="bold red")
        raise
    except Exception as e:
        console.print(f"❌ Error reading {file_path}: {e}", style="bold red")
        raise

def save_json(data: Any, file_path: Path, indent: int = 2) -> None:
    """Save data to JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
    except Exception as e:
        console.print(f"❌ Error saving to {file_path}: {e}", style="bold red")
        raise

def print_file_info(file_path: Path) -> None:
    """Print information about a file."""
    if not file_path.exists():
        console.print(f"❌ File does not exist: {file_path}", style="red")
        return
    
    size_mb = file_path.stat().st_size / (1024 * 1024)
    modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    
    console.print(f"📄 File: {file_path.name}", style="bold blue")
    console.print(f"   Size: {size_mb:.2f} MB")
    console.print(f"   Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
