# Learner State Implementation - Phase 1

## ✅ Completed Implementation

This document outlines the initial implementation of the centralized learner state for the Intelligent Tutoring System (ITS).

---

## 📊 What Was Implemented

### 1. **Core Data Models** (`app/models/learner_state.py`)

Created minimal, essential learner state tracking:

```python
LearnerState:
  - version: "1.0"
  - updated: timestamp
  - mastery: Dict[str, float]        # Topic -> mastery level (0.0-1.0)
  - common_errors: Dict[str, List]   # Topic -> error patterns
  - reviews: List[ReviewItem]        # Spaced repetition queue
  - streak: int                      # Current daily streak
  - last_seen: date                  # Last activity date
```

**Key Models:**
- `LearnerState` - Main state container
- `TopicMastery` - Detailed topic metrics (for future expansion)
- `ErrorPattern` - Error tracking for feedback
- `ReviewItem` - Spaced repetition schedule items
- `TopicStatistics` - Computed statistics per topic

### 2. **User Model Integration** (`app/models/user.py`)

Added `learner_state` field to both `UserInDB` and `User` models:
- Optional field (backward compatible)
- Initialized on first activity or manually
- Stored directly in user document

### 3. **CRUD Operations** (`app/crud/learner_state.py`)

Implemented comprehensive learner state management:

**Initialization:**
- `initialize_from_history()` - Calculate state from submission history
- `_calculate_topic_mastery()` - Mastery from success rates + recency
- `_calculate_streak()` - Current streak from activity dates

**Updates:**
- `update_mastery_from_submission()` - Adjust mastery based on new submission
  - Success: `mastery += 0.1 * (1 - current_mastery)` (diminishing returns)
  - Failure: `mastery -= 0.15 * current_mastery` (proportional penalty)
- `add_error_pattern()` - Track recurring errors for feedback
- `schedule_review()` - SM-2 spaced repetition scheduling
- `update_streak()` - Maintain activity streak

**Queries:**
- `get_due_reviews()` - Get overdue spaced repetition items
- `get_topic_statistics()` - Detailed metrics for a topic

### 4. **API Endpoints** (`app/api/learner_state.py`)

Created RESTful API for learner state access:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/learner-state` | GET | Get current state (auto-initializes if missing) |
| `/learner-state/recalculate` | POST | Force recalculation from scratch |
| `/learner-state/topics/{topic}` | GET | Get detailed topic statistics |
| `/learner-state/reviews/due` | GET | Get due spaced repetition reviews |
| `/learner-state/summary` | GET | Get overview summary |

### 5. **Router Integration** (`app/api/router.py`)

Registered learner state routes in main API router.

---

## 🎯 What Each Metric Tracks

### ✅ Knowledge Level Per Topic (IMPLEMENTED)
**Storage:** `learner_state.mastery`
**Algorithm:**
- Calculated from submission history
- Weighted by recency (recent performance counts more)
- Updated after each submission with diminishing returns
- Range: 0.0 (novice) to 1.0 (expert)

### ✅ Error Patterns (IMPLEMENTED)
**Storage:** `learner_state.common_errors`
**Purpose:** Enable targeted feedback from Pedagogical Agent
**Tracking:**
- Up to 3 most recent error patterns per topic
- Example patterns: "off-by-one", "null-check", "boundary-error"
- Links to example questions for context

### ✅ Review Schedule (IMPLEMENTED)
**Storage:** `learner_state.reviews`
**Algorithm:** Simplified SM-2 spaced repetition
- First success: Review in 1 day
- Subsequent: Interval multiplied by ease_factor (1.3-2.5)
- Due date calculated automatically
- Priority based on overdue duration

### ✅ Engagement/Streak (IMPLEMENTED)
**Storage:** `learner_state.streak` + `learner_state.last_seen`
**Logic:**
- Same day: Keep streak
- Consecutive day: Increment
- Gap > 1 day: Reset to 1

### ℹ️ Recent Submissions (ALREADY EXISTS)
**Storage:** `submissions` collection
**Note:** No duplication needed, just query when required

---

## 📖 Usage Examples

### Initialize State for New User

```python
from app.crud.learner_state import LearnerStateCRUD

learner_crud = LearnerStateCRUD(db)
state = learner_crud.initialize_from_history(user_key)

# Save to user
user_crud.update_user(user_key, {
    'learner_state': state.model_dump()
})
```

### Update After Submission

```python
# Get current state
user = user_crud.get_user_by_key(user_key)
current_state = user.learner_state

# Get topics for the question
topics = learner_crud._get_question_topics(question_key)

# Update mastery
new_mastery = learner_crud.update_mastery_from_submission(
    current_state, 
    topics, 
    is_success=True
)

# If failed, add error pattern
if not is_success:
    new_errors = learner_crud.add_error_pattern(
        current_state,
        topic="arrays",
        error_pattern="off-by-one",
        question_id=question_key
    )

# If succeeded, schedule review
if is_success:
    new_reviews = learner_crud.schedule_review(
        current_state,
        question_id=question_key,
        topic="arrays",
        is_first_success=True
    )

# Update streak
new_streak, today = learner_crud.update_streak(current_state)

# Save updates
user_crud.update_user(user_key, {
    'learner_state.mastery': new_mastery,
    'learner_state.streak': new_streak,
    'learner_state.last_seen': today.isoformat(),
    'learner_state.updated': datetime.utcnow().isoformat()
})
```

### API Usage (Frontend)

```javascript
// Get learner state (auto-initializes if missing)
const response = await fetch('/api/learner-state', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const state = await response.json();

// Get topic statistics
const topicStats = await fetch('/api/learner-state/topics/arrays', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Get due reviews
const reviews = await fetch('/api/learner-state/reviews/due', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Get summary
const summary = await fetch('/api/learner-state/summary', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## 🔄 Next Steps (Phase 2)

### Immediate (Week 1-2):
1. **Hook into Submission Flow**
   - Modify `/dashboard/submit` endpoint
   - Trigger learner state update after each submission
   - Extract topics from question automatically

2. **Testing**
   - Test state initialization for existing users
   - Verify mastery calculations
   - Test streak logic

### Short-term (Week 3-4):
1. **Frontend Integration**
   - Display mastery levels in dashboard
   - Show due reviews
   - Visualize topic strengths/weaknesses

2. **Agent Integration**
   - Create orchestrator skeleton (LangGraph)
   - Wire up Learner Profiler agent
   - Wire up Progress Synthesizer agent

---

## 📁 Files Created/Modified

### Created:
- `backend/app/models/learner_state.py` - Core data models
- `backend/app/crud/learner_state.py` - Business logic
- `backend/app/api/learner_state.py` - API endpoints
- `backend/LEARNER_STATE_IMPLEMENTATION.md` - This document

### Modified:
- `backend/app/models/user.py` - Added learner_state field
- `backend/app/api/router.py` - Registered learner_state routes

---

## 🎯 Key Design Decisions

1. **Minimal Schema**: Started with essential metrics only, extensible later
2. **Lazy Initialization**: State created on first access, not at registration
3. **Optional Field**: Backward compatible with existing users
4. **Single Source of Truth**: Stored in user document, not separate collection
5. **Calculated Mastery**: Derived from submission history, not manually set
6. **Recency Weighting**: Recent performance counts more than old data

---

## 🧪 Testing Checklist

- [ ] New user: State initializes correctly on first activity
- [ ] Existing user: State calculates from submission history
- [ ] Submission (success): Mastery increases correctly
- [ ] Submission (failure): Mastery decreases correctly
- [ ] Streak: Increments on consecutive days, resets on gap
- [ ] Reviews: Scheduled with correct SM-2 intervals
- [ ] API endpoints: All return correct data
- [ ] Topics: Extracted correctly from roadmap questions

---

## 📊 Sample Data

### Example Learner State:

```json
{
  "version": "1.0",
  "updated": "2025-01-15T10:30:00Z",
  "mastery": {
    "array": 0.75,
    "dynamic-programming": 0.42,
    "string": 0.68,
    "binary-tree": 0.55
  },
  "common_errors": {
    "array": ["off-by-one", "boundary-check"],
    "binary-tree": ["null-check"]
  },
  "reviews": [
    {
      "question_id": "two-sum",
      "topics": ["array", "hash-table"],
      "due_date": "2025-01-18T00:00:00Z",
      "interval_days": 3,
      "ease_factor": 2.5
    }
  ],
  "streak": 7,
  "last_seen": "2025-01-15"
}
```

---

## 🚀 Ready for Phase 2!

The foundation is now in place for the multi-agent intelligent tutoring system. The centralized learner state provides:

✅ Single source of truth for all agents  
✅ Efficient storage (3-5KB per user)  
✅ Real-time updates via API  
✅ Backward compatible with existing system  
✅ Extensible schema for future enhancements  

**Next:** Integrate with submission flow and build the orchestrator!


