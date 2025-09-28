# 🚀 Updated Roadmap Seeding Guide

## ✨ New Features Implemented

The roadmap seeding system has been enhanced with the following key improvements:

### 🔢 Sequential Step Numbering
- **NEW**: Questions now maintain their original `sl_no` from `a2z.json` as `step_number`
- **BENEFIT**: Proper sequential ordering (1, 2, 3, 4, 5...288) is preserved
- **BEHAVIOR**: Even if questions are removed, the sequence maintains gaps (e.g., 1, 3, 4, 6, 7...)

### 🚫 Paid Question Filtering
- **NEW**: Automatically filters out paid LeetCode questions during import
- **BENEFIT**: Only free questions are imported to the database
- **CONFIGURABLE**: Use `--include-paid` flag to include them if needed

### 📊 Enhanced Reporting
- **NEW**: Detailed statistics about filtered questions
- **BENEFIT**: Clear visibility into what was processed vs. filtered

## 🛠️ How to Use the Updated System

### Step 1: Environment Setup
```bash
# Navigate to scripts directory
cd backend/scripts

# Activate conda environment
conda activate intellicode

# Ensure dependencies are installed
pip install leetscrape rich beautifulsoup4
```

### Step 2: Scrape Questions (Enhanced)
The scraping process now preserves `sl_no` from `a2z.json`:

```bash
# Test with a few questions first
python standalone_roadmap_scraper.py --max-questions 10

# Full scrape (recommended for production)
python standalone_roadmap_scraper.py --output roadmap_with_step_numbers.json
```

### Step 3: Import to Database (New Features)
The import process now filters paid questions and preserves step numbering:

```bash
# Import with paid question filtering (RECOMMENDED)
python import_roadmap_data.py roadmap_with_step_numbers.json

# Import including paid questions (if needed)
python import_roadmap_data.py roadmap_with_step_numbers.json --include-paid

# Force reimport (overwrite existing)
python import_roadmap_data.py roadmap_with_step_numbers.json --force

# Check database statistics
python import_roadmap_data.py --stats-only
```

## 📋 What's Changed in the Data Structure

### Before (Old Structure)
```json
{
  "question_id": "rvrsnmbr",
  "original_title": "Reverse a Number",
  "a2z_step": "Learn the basics",
  "a2z_sub_step": "Know Basic Maths",
  "a2z_difficulty": 0,
  "lc_link": "https://leetcode.com/problems/reverse-integer/"
}
```

### After (New Structure)
```json
{
  "question_id": "rvrsnmbr",
  "original_title": "Reverse a Number",
  "a2z_step": "Learn the basics",
  "a2z_sub_step": "Know Basic Maths",
  "a2z_difficulty": 0,
  "lc_link": "https://leetcode.com/problems/reverse-integer/",
  "step_number": 42,  // <- NEW: Preserves sl_no from a2z.json
  "is_paid_only": false  // <- Enhanced: Better filtering
}
```

## 🎯 Testing the New System

### Quick Test (5 Questions)
```bash
# Scrape a small sample
python standalone_roadmap_scraper.py --max-questions 5 --output test_roadmap.json

# Import the test data
python import_roadmap_data.py test_roadmap.json --force

# Check results
python import_roadmap_data.py --stats-only
```

### Full Production Import
```bash
# Clean scrape with current data
python standalone_roadmap_scraper.py --output production_roadmap.json

# Import with paid filtering
python import_roadmap_data.py production_roadmap.json --force
```

## 📊 Expected Output

When running the import, you should see output like:

```
📥 Importing roadmap data from roadmap_data.json
✅ Database connection established
📊 Found 288 roadmap items to process
🚫 Filtered out 22 paid-only questions
✅ Processing 266 free questions (keeping original step numbers)

📊 IMPORT SUMMARY
=====================================
✅ Imported: 266
⏭️  Skipped: 0
❌ Errors: 0
🚫 Paid Questions Filtered: 22
📋 Note: Step numbers preserved from original sequence
```

## 🔍 Verification

To verify the system is working correctly:

1. **Check Step Numbers**: Questions should have sequential step numbers from original a2z.json
2. **No Paid Questions**: Verify no questions with `is_paid_only: true` in database
3. **Proper Ordering**: Questions should be orderable by `step_number` field

## 🚨 Important Notes

- **Database Schema**: The `step_number` field has been added to the roadmap model
- **Backward Compatibility**: Existing data may need migration to include step numbers
- **Default Behavior**: Paid questions are filtered by default (use `--include-paid` to override)
- **Step Gaps**: Step numbers may have gaps due to filtered questions - this is intentional

## 🎉 Benefits of the New System

1. **Proper Ordering**: Questions follow the intended A2Z roadmap sequence
2. **Clean Dataset**: No paid questions cluttering the free content
3. **Transparency**: Clear reporting of what was filtered and why
4. **Flexibility**: Option to include paid questions if needed
5. **Data Integrity**: Original step numbers preserved for accurate ordering
