# 🚀 LeetCode Roadmap Scraper - Usage Guide

## 🎯 Quick Start

### Step 1: Environment Setup
```bash
# Navigate to scripts directory
cd backend/scripts

# Activate conda environment
conda activate intellicode

# Install dependencies (if not already installed)
pip install leetscrape rich beautifulsoup4
```

### Step 2: Scrape Questions
```bash
# Test with 5 questions first
python standalone_roadmap_scraper.py --max-questions 5

# Scrape all questions (will take a while!)
python standalone_roadmap_scraper.py
```

### Step 3: Import to Database
```bash
# The scraper creates roadmap_data.json
# Import it into the database:
python import_roadmap_data.py roadmap_data.json
```

## 📊 Current Status

✅ **System Working!** Successfully tested with 3 questions  
✅ **Database Integration** - Questions imported to 'roadmap' collection  
✅ **Comprehensive Data** - Examples, test cases, hints, constraints, etc.  
✅ **Error Handling** - Handles paid content, rate limits, failures  

## 🔧 Available Commands

### Scraping Commands

```bash
# Basic scraping
python standalone_roadmap_scraper.py

# With options
python standalone_roadmap_scraper.py \
  --max-questions 10 \
  --max-workers 3 \
  --delay 2.0 \
  --output my_roadmap.json

# Filter by A2Z roadmap section
python standalone_roadmap_scraper.py \
  --step "Learn the basics" \
  --sub-step "Know Basic Maths"
```

### Import Commands

```bash
# Import scraped data
python import_roadmap_data.py roadmap_data.json

# Force reimport (overwrite existing)
python import_roadmap_data.py roadmap_data.json --force

# Check database statistics
python import_roadmap_data.py --stats-only
```

### Testing Commands

```bash
# Test database system
python test_roadmap_system.py

# Quick scrape test
python standalone_roadmap_scraper.py --max-questions 3
```

## 📋 What Gets Scraped

For each LeetCode question, the system extracts:

### 📝 Problem Content
- ✅ Problem statement (HTML & text)
- ✅ Examples with input/output
- ✅ Sample test cases
- ✅ Constraints
- ✅ Follow-up questions

### 💻 Code & Solutions
- ✅ Code templates (Python, etc.)
- ✅ Function signatures
- ✅ Default starter code

### 🎓 Educational Content
- ✅ Hints
- ✅ Topic tags
- ✅ Company tags
- ✅ Similar questions
- ✅ Difficulty level

### 🗺️ A2Z Roadmap Info
- ✅ Step and sub-step categories
- ✅ Original A2Z difficulty
- ✅ Topic classifications

## 🗄️ Database Schema

Data is stored in the `roadmap` collection:

```json
{
  "_key": "17877123",
  "question_id": "rvrsnmbr",
  "original_title": "Reverse a Number",
  "a2z_step": "Learn the basics",
  "a2z_sub_step": "Know Basic Maths",
  "leetcode_title": "Reverse Integer", 
  "leetcode_difficulty": "Medium",
  "problem_statement_text": "Given a signed 32-bit integer...",
  "examples": [
    {
      "example_number": 1,
      "input": "x = 123",
      "output": "321"
    }
  ],
  "sample_test_cases": [...],
  "code_templates": {
    "python": "class Solution:\n    def reverse(self, x: int) -> int:\n        "
  },
  "hints": [...],
  "topics": ["Math"],
  "scraping_success": true,
  "created_at": "2025-09-27T...",
  // ... and much more!
}
```

## ⚙️ Configuration Options

### Scraping Performance
- `--max-workers N` - Parallel workers (default: 3)
- `--delay X.X` - Delay between requests (default: 2.0s)
- `--max-questions N` - Limit for testing

### Filtering Options
- `--step "Step Name"` - Specific A2Z step
- `--sub-step "Sub Step"` - Specific A2Z sub-step
- `--input custom.json` - Custom input file

### Output Options
- `--output filename.json` - Custom output file
- Default output: `roadmap_data.json`

## 🔍 Usage Examples

### Example 1: Test Setup
```bash
# Test with just a few questions
python standalone_roadmap_scraper.py --max-questions 3
python import_roadmap_data.py roadmap_data.json
python import_roadmap_data.py --stats-only
```

### Example 2: Scrape Specific Section
```bash
# Focus on arrays and strings
python standalone_roadmap_scraper.py \
  --step "Solve Problems on Arrays" \
  --max-questions 20
```

### Example 3: Full Production Run
```bash
# Scrape everything (will take hours!)
python standalone_roadmap_scraper.py \
  --max-workers 2 \
  --delay 3.0 \
  --output full_roadmap_$(date +%Y%m%d).json
```

## 🔧 Troubleshooting

### Issue: Pydantic Version Conflict
```bash
# If you get pydantic errors during import:
pip install "pydantic>=2.0" --upgrade
```

### Issue: Rate Limiting
```bash
# Reduce workers and increase delay:
python standalone_roadmap_scraper.py \
  --max-workers 1 \
  --delay 5.0
```

### Issue: Import Errors
```bash
# Check database connection:
python test_roadmap_system.py

# Force reimport:
python import_roadmap_data.py roadmap_data.json --force
```

### Issue: Memory Problems
```bash
# Process in smaller batches:
python standalone_roadmap_scraper.py --max-questions 50
python import_roadmap_data.py roadmap_data.json
# Repeat as needed
```

## 📈 Progress Monitoring

The system provides real-time feedback:

```
🚀 Starting comprehensive scraping of 288 LeetCode questions...
✅ Scraped: Reverse Integer (Medium) - 3 examples, 0 hints
✅ Scraped: Palindrome Number (Easy) - 3 examples, 1 hints
⚠️  Scraped: Armstrong Number (Easy) - 0 examples, 3 hints [PAID]

📊 ENHANCED LEETCODE SCRAPING SUMMARY
Total Questions Processed: 288
✅ Successful: 275
❌ Failed: 13
Success Rate: 95.5%

📈 Content Extracted:
   Examples: 825
   Test Cases: 825  
   Hints: 412
   Topic Tags: 1,203
```

## 🚀 Next Steps

Once you have a populated roadmap collection, you can:

1. **Build API endpoints** to serve questions
2. **Create practice interfaces** using the comprehensive data
3. **Implement difficulty progression** based on A2Z roadmap
4. **Add user progress tracking** against the roadmap
5. **Generate personalized study plans** from the categorized content

The roadmap collection now contains everything needed for a complete LeetCode-like coding platform! 🎉

