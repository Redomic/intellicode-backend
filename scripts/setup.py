#!/usr/bin/env python3
"""
Setup script for the A2Z DSA Question Scraper.
"""
import subprocess
import sys
import os
from pathlib import Path
from rich.console import Console

console = Console()

def check_conda_environment():
    """Check if running in the correct conda environment."""
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    
    if conda_env != 'intellicode':
        console.print("⚠️  Warning: Not running in 'intellicode' conda environment", style="bold yellow")
        console.print("   Please activate with: conda activate intellicode", style="yellow")
        return False
    else:
        console.print(f"✅ Running in conda environment: {conda_env}", style="green")
        return True

def install_requirements():
    """Install Python requirements."""
    try:
        console.print("📦 Installing Python requirements...", style="blue")
        
        requirements_file = Path(__file__).parent / "requirements.txt"
        
        if not requirements_file.exists():
            console.print("❌ requirements.txt not found", style="red")
            return False
        
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("✅ Python requirements installed successfully", style="green")
            return True
        else:
            console.print(f"❌ Failed to install requirements: {result.stderr}", style="red")
            return False
            
    except Exception as e:
        console.print(f"❌ Error installing requirements: {e}", style="red")
        return False

def install_playwright_browsers():
    """Install Playwright browsers."""
    try:
        console.print("🌐 Installing Playwright browsers...", style="blue")
        
        result = subprocess.run([
            "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            console.print("✅ Playwright browsers installed successfully", style="green")
            return True
        else:
            console.print(f"❌ Failed to install Playwright browsers: {result.stderr}", style="red")
            return False
            
    except subprocess.TimeoutExpired:
        console.print("❌ Playwright installation timed out", style="red")
        return False
    except Exception as e:
        console.print(f"❌ Error installing Playwright browsers: {e}", style="red")
        return False

def create_directories():
    """Create necessary directories."""
    try:
        console.print("📁 Creating directories...", style="blue")
        
        directories = [
            "scraped_data",
            "scraped_data/backups",
            "logs"
        ]
        
        for directory in directories:
            dir_path = Path(__file__).parent / directory
            dir_path.mkdir(exist_ok=True, parents=True)
            console.print(f"   Created: {directory}", style="dim")
        
        console.print("✅ Directories created successfully", style="green")
        return True
        
    except Exception as e:
        console.print(f"❌ Error creating directories: {e}", style="red")
        return False

def check_input_file():
    """Check if A2Z input file exists."""
    a2z_file = Path(__file__).parent / "a2z.json"
    
    if a2z_file.exists():
        console.print(f"✅ Found A2Z input file: {a2z_file}", style="green")
        
        # Check file size
        size_mb = a2z_file.stat().st_size / (1024 * 1024)
        console.print(f"   File size: {size_mb:.2f} MB", style="dim")
        
        return True
    else:
        console.print(f"⚠️  A2Z input file not found: {a2z_file}", style="yellow")
        console.print("   Please ensure a2z.json is in the scripts directory", style="yellow")
        return False

def main():
    """Main setup function."""
    console.print("🚀 A2Z DSA Question Scraper Setup", style="bold blue", justify="center")
    console.print("=" * 50, style="blue")
    
    success = True
    
    # Check conda environment
    if not check_conda_environment():
        success = False
    
    # Create directories
    if not create_directories():
        success = False
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Install Playwright browsers
    if not install_playwright_browsers():
        success = False
    
    # Check input file
    if not check_input_file():
        console.print("   (This is optional for setup, but required for scraping)", style="dim")
    
    console.print("\n" + "=" * 50, style="blue")
    
    if success:
        console.print("🎉 Setup completed successfully!", style="bold green")
        console.print("\n💡 Usage examples:", style="bold yellow")
        console.print("   # Test with 5 questions")
        console.print("   python main.py --max-questions 5 --output test_results.json")
        console.print("\n   # Full scrape")
        console.print("   python main.py --input a2z.json --output scraped_results.json")
        console.print("\n   # Debug mode")
        console.print("   python main.py --max-questions 10 --log-level DEBUG")
    else:
        console.print("❌ Setup encountered some issues", style="bold red")
        console.print("   Please resolve the above errors before running the scraper", style="red")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
