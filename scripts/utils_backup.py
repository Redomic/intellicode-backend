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
    """
    Set up logging configuration with Rich formatting.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
    """
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

def load_json(file_path: Path) -> Any:
    """
    Load JSON data from file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
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
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        file_path: Path to save file
        indent: JSON indentation level
    """
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
            
        except Exception as e:
        console.print(f"❌ Error saving to {file_path}: {e}", style="bold red")
            raise
            
def validate_urls(urls: List[str]) -> List[str]:
    """
    Validate and filter URLs.
    
    Args:
        urls: List of URLs to validate
        
    Returns:
        List of valid URLs
    """
    import re
    
    valid_urls = []
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    for url in urls:
        if url and isinstance(url, str) and url_pattern.match(url.strip()):
            valid_urls.append(url.strip())
    
    return valid_urls

def clean_filename(filename: str) -> str:
    """
    Clean filename to be filesystem-safe.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    import re
    
    # Remove or replace invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', '_', cleaned)
    
    # Remove leading/trailing periods and spaces
    cleaned = cleaned.strip('. ')
    
    # Limit length
    if len(cleaned) > 200:
        cleaned = cleaned[:200]
    
    return cleaned or "unnamed"

def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def estimate_completion_time(processed: int, total: int, elapsed_time: float) -> str:
    """
    Estimate completion time based on current progress.
    
    Args:
        processed: Number of items processed
        total: Total number of items
        elapsed_time: Time elapsed so far
        
    Returns:
        Estimated completion time string
    """
    if processed == 0:
        return "Unknown"
    
    avg_time_per_item = elapsed_time / processed
    remaining_items = total - processed
    estimated_remaining_time = remaining_items * avg_time_per_item
    
    return format_duration(estimated_remaining_time)

def create_backup_filename(base_name: str, extension: str = ".json") -> str:
    """
    Create a backup filename with timestamp.
    
    Args:
        base_name: Base filename
        extension: File extension
        
    Returns:
        Backup filename with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_backup_{timestamp}{extension}"

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = file_path.stat().st_size
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0

def print_file_info(file_path: Path) -> None:
    """
    Print information about a file.
    
    Args:
        file_path: Path to file
    """
    if not file_path.exists():
        console.print(f"❌ File does not exist: {file_path}", style="red")
        return
    
    size_mb = get_file_size_mb(file_path)
    modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    
    console.print(f"📄 File: {file_path.name}", style="bold blue")
    console.print(f"   Size: {size_mb:.2f} MB")
    console.print(f"   Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")

def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """
    Safely get a value from a dictionary.
    
    Args:
        data: Dictionary to get value from
        key: Key to look for
        default: Default value if key not found
        
    Returns:
        Value from dictionary or default
    """
    try:
        return data.get(key, default) if isinstance(data, dict) else default
    except Exception:
        return default

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry function on failure.
    
    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import asyncio
            
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    else:
                        logging.error(f"All {max_retries + 1} attempts failed")
            
            raise last_exception
        
        return wrapper
    return decorator

def validate_environment() -> bool:
    """
    Validate that the environment is properly set up.
    
    Returns:
        True if environment is valid, False otherwise
    """
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            console.print("❌ Python 3.8+ is required", style="bold red")
            return False

        # Check required packages (mapping package names to import names)
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
