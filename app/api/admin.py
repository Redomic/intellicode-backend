"""
Admin API — full CRUD for users, roadmap items, and read-only research views.

Authentication: X-Admin-Key header must match settings.ADMIN_API_KEY.
All endpoints are prefixed with /admin.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import settings
from app.crud.user import UserCRUD
from app.crud.roadmap import RoadmapCRUD
from app.db.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    skill_level: Optional[str] = None
    expertise_rank: int = 600
    is_study_participant: bool = False

class UserPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    skill_level: Optional[str] = None
    expertise_rank: Optional[int] = None
    is_study_participant: Optional[bool] = None
    onboarding_completed: Optional[bool] = None
    is_active: Optional[bool] = None

class PasswordReset(BaseModel):
    new_password: str

class RoadmapPatch(BaseModel):
    original_title: Optional[str] = None
    leetcode_title: Optional[str] = None
    leetcode_difficulty: Optional[str] = None
    a2z_step: Optional[str] = None
    a2z_sub_step: Optional[str] = None
    step_number: Optional[int] = None
    topics: Optional[List[str]] = None
    problem_statement_text: Optional[str] = None
    scraping_success: Optional[bool] = None

class RoadmapCreate(BaseModel):
    course: str
    question_id: str
    original_title: str
    a2z_step: str
    a2z_sub_step: str
    a2z_difficulty: int = 0
    a2z_topics: str = ""
    lc_link: str = ""
    step_number: int
    leetcode_title: Optional[str] = None
    leetcode_difficulty: Optional[str] = None
    topics: List[str] = []
    problem_statement_text: Optional[str] = None
    scraping_success: bool = False


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    """List all users with optional name/email search."""
    db = get_db()
    if search:
        cursor = db.aql.execute(
            """
            FOR u IN users
              FILTER CONTAINS(LOWER(u.email), LOWER(@q))
                  OR CONTAINS(LOWER(u.name), LOWER(@q))
              SORT u.created_at DESC
              LIMIT @offset, @limit
              RETURN UNSET(u, "hashed_password")
            """,
            bind_vars={"q": search, "offset": offset, "limit": limit},
        )
    else:
        cursor = db.aql.execute(
            """
            FOR u IN users
              SORT u.created_at DESC
              LIMIT @offset, @limit
              RETURN UNSET(u, "hashed_password")
            """,
            bind_vars={"offset": offset, "limit": limit},
        )
    users = list(cursor)

    total_cursor = db.aql.execute("RETURN LENGTH(users)")
    total = list(total_cursor)[0]

    return {"users": users, "total": total, "offset": offset, "limit": limit}


@router.post("/users", dependencies=[Depends(require_admin)])
def create_user(body: UserCreate):
    from app.models.user import UserCreate as ModelUserCreate
    db = get_db()
    crud = UserCRUD(db)
    if crud.get_user_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(ModelUserCreate(
        name=body.name,
        email=body.email,
        password=body.password,
        is_active=True,
    ))
    extra = {}
    if body.skill_level:
        extra["skill_level"] = body.skill_level
    if body.expertise_rank != 600:
        extra["expertise_rank"] = body.expertise_rank
    if body.is_study_participant:
        extra["is_study_participant"] = True
    if extra:
        crud.update_user_fields(user.key, extra)
        user = crud.get_user_by_key(user.key)
    d = user.model_dump()
    d.pop("hashed_password", None)
    return d


@router.get("/users/{key}", dependencies=[Depends(require_admin)])
def get_user(key: str):
    db = get_db()
    user = UserCRUD(db).get_user_by_key(key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    d = user.model_dump()
    d.pop("hashed_password", None)
    return d


@router.patch("/users/{key}", dependencies=[Depends(require_admin)])
def patch_user(key: str, body: UserPatch):
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = UserCRUD(db).update_user_fields(key, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    d = updated.model_dump()
    d.pop("hashed_password", None)
    return d


@router.delete("/users/{key}", dependencies=[Depends(require_admin)])
def delete_user(key: str):
    db = get_db()
    col = db.collection("users")
    if not col.get(key):
        raise HTTPException(status_code=404, detail="User not found")
    col.delete(key)
    return {"deleted": key}


@router.post("/users/{key}/reset-password", dependencies=[Depends(require_admin)])
def reset_password(key: str, body: PasswordReset):
    from app.core.security import get_password_hash
    if not body.new_password or len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    db = get_db()
    col = db.collection("users")
    if not col.get(key):
        raise HTTPException(status_code=404, detail="User not found")
    col.update({"_key": key, "hashed_password": get_password_hash(body.new_password)})
    return {"ok": True, "user_key": key}


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

@router.get("/roadmap", dependencies=[Depends(require_admin)])
def list_roadmap(
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    course: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    db = get_db()
    filters = []
    bind: Dict[str, Any] = {"offset": offset, "limit": limit}

    if course:
        filters.append("r.course == @course")
        bind["course"] = course
    if search:
        filters.append(
            "(CONTAINS(LOWER(r.original_title), LOWER(@q)) OR CONTAINS(LOWER(r.leetcode_title), LOWER(@q)))"
        )
        bind["q"] = search

    where = ("FILTER " + " AND ".join(filters)) if filters else ""
    cursor = db.aql.execute(
        f"FOR r IN roadmap {where} SORT r.step_number ASC LIMIT @offset, @limit RETURN r",
        bind_vars=bind,
    )

    count_cursor = db.aql.execute(
        f"FOR r IN roadmap {where} COLLECT WITH COUNT INTO n RETURN n",
        bind_vars={k: v for k, v in bind.items() if k not in ("offset", "limit")},
    )
    count_list = list(count_cursor)
    total = count_list[0] if count_list else 0

    return {"items": list(cursor), "total": total, "offset": offset, "limit": limit}


@router.get("/roadmap/courses", dependencies=[Depends(require_admin)])
def list_courses():
    db = get_db()
    cursor = db.aql.execute(
        "FOR r IN roadmap COLLECT course = r.course WITH COUNT INTO n RETURN {course, count: n}"
    )
    return list(cursor)


@router.get("/roadmap/{key}", dependencies=[Depends(require_admin)])
def get_roadmap_item(key: str):
    db = get_db()
    doc = db.collection("roadmap").get(key)
    if not doc:
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    return doc


@router.post("/roadmap", dependencies=[Depends(require_admin)])
def create_roadmap_item(body: RoadmapCreate):
    from app.models.roadmap import RoadmapItemCreate
    db = get_db()
    item = RoadmapItemCreate(**body.model_dump())
    created = RoadmapCRUD(db).create_roadmap_item(item)
    return created.model_dump()


@router.patch("/roadmap/{key}", dependencies=[Depends(require_admin)])
def patch_roadmap_item(key: str, body: RoadmapPatch):
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow().isoformat()
    col = db.collection("roadmap")
    if not col.get(key):
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    col.update({"_key": key, **updates})
    return col.get(key)


@router.delete("/roadmap/{key}", dependencies=[Depends(require_admin)])
def delete_roadmap_item(key: str):
    """
    Delete a roadmap item and:
    1. Cascade-delete all references (submissions, sessions, learner_state reviews,
       mastery_history, hint_outcomes, calibration_pairs, content_policy_log, review_log)
    2. Renumber all subsequent steps in the same course (step N+1 → N, ...)
    """
    db = get_db()
    col = db.collection("roadmap")
    doc = col.get(key)
    if not doc:
        raise HTTPException(status_code=404, detail="Roadmap item not found")

    course = doc.get("course")
    deleted_step = doc.get("step_number")
    report: Dict[str, Any] = {"deleted": key, "course": course, "step_number": deleted_step}

    # ── 1. Cascade: submissions ──────────────────────────────────────────────
    r = db.aql.execute(
        "FOR s IN submissions FILTER s.question_key == @k REMOVE s IN submissions RETURN 1",
        bind_vars={"k": key},
    )
    report["submissions_deleted"] = len(list(r))

    # ── 2. Cascade: sessions ─────────────────────────────────────────────────
    r = db.aql.execute(
        "FOR s IN sessions FILTER s.question_id == @k REMOVE s IN sessions RETURN 1",
        bind_vars={"k": key},
    )
    report["sessions_deleted"] = len(list(r))

    # ── 3. Cascade: learner_state reviews on all users ───────────────────────
    # Remove any ReviewItem in learner_state.reviews where question_id == key
    r = db.aql.execute(
        """
        FOR u IN users
          FILTER u.learner_state != null
            AND LENGTH(u.learner_state.reviews) > 0
          LET filtered = (
            FOR rev IN u.learner_state.reviews
              FILTER rev.question_id != @k
              RETURN rev
          )
          FILTER LENGTH(filtered) != LENGTH(u.learner_state.reviews)
          UPDATE u WITH {
            learner_state: MERGE(u.learner_state, { reviews: filtered })
          } IN users
          RETURN 1
        """,
        bind_vars={"k": key},
    )
    report["learner_state_reviews_cleaned"] = len(list(r))

    # ── 4. Cascade: research collections ────────────────────────────────────
    for research_col in ("mastery_history", "hint_outcomes", "calibration_pairs",
                         "content_policy_log", "review_log"):
        try:
            r = db.aql.execute(
                f"FOR d IN {research_col} FILTER d.question_key == @k REMOVE d IN {research_col} RETURN 1",
                bind_vars={"k": key},
            )
            report[f"{research_col}_deleted"] = len(list(r))
        except Exception:
            report[f"{research_col}_deleted"] = 0

    # ── 5. Delete the roadmap item itself ────────────────────────────────────
    col.delete(key)

    # ── 6. Renumber subsequent steps in the same course ──────────────────────
    if course and deleted_step is not None:
        r = db.aql.execute(
            """
            FOR r IN roadmap
              FILTER r.course == @course AND r.step_number > @step
              UPDATE r WITH { step_number: r.step_number - 1 } IN roadmap
              RETURN 1
            """,
            bind_vars={"course": course, "step": deleted_step},
        )
        report["steps_renumbered"] = len(list(r))
    else:
        report["steps_renumbered"] = 0

    return report


# ---------------------------------------------------------------------------
# Submissions (read-only)
# ---------------------------------------------------------------------------

@router.get("/submissions", dependencies=[Depends(require_admin)])
def list_submissions(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    user_key: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    db = get_db()
    filters = []
    bind: Dict[str, Any] = {"offset": offset, "limit": limit}

    if user_key:
        filters.append("s.user_key == @user_key")
        bind["user_key"] = user_key
    if status_filter:
        filters.append("s.status == @status")
        bind["status"] = status_filter

    where = ("FILTER " + " AND ".join(filters)) if filters else ""
    cursor = db.aql.execute(
        f"""
        FOR s IN submissions {where}
          SORT s.created_at DESC
          LIMIT @offset, @limit
          LET u = FIRST(FOR u IN users FILTER u._key == s.user_key RETURN u)
          RETURN MERGE(s, {{ user_name: u.name, user_email: u.email }})
        """,
        bind_vars=bind,
    )
    count_cursor = db.aql.execute(
        f"FOR s IN submissions {where} COLLECT WITH COUNT INTO n RETURN n",
        bind_vars={k: v for k, v in bind.items() if k not in ("offset", "limit")},
    )
    count_list = list(count_cursor)
    total = count_list[0] if count_list else 0

    return {"submissions": list(cursor), "total": total}


@router.get("/submissions/{key}", dependencies=[Depends(require_admin)])
def get_submission_detail(key: str):
    """
    Full submission detail enriched with:
    - User profile (name, email, rank, proficiency)
    - Question metadata (title, difficulty, topics)
    - Session hint history for this session
    - Mastery delta records triggered by this submission
    - All previous attempts on the same question by this user
    """
    db = get_db()

    sub = db.collection("submissions").get(key)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    user_key = sub.get("user_key")
    question_key = sub.get("question_key")
    session_id = sub.get("session_id")
    created_at = sub.get("created_at")

    # User profile
    user_doc = db.collection("users").get(user_key) if user_key else None
    user_info = None
    if user_doc:
        user_info = {
            "key": user_doc.get("_key"),
            "name": user_doc.get("name"),
            "email": user_doc.get("email"),
            "skill_level": user_doc.get("skill_level"),
            "expertise_rank": user_doc.get("expertise_rank"),
            "is_study_participant": user_doc.get("is_study_participant", False),
            "learner_state": user_doc.get("learner_state"),
        }

    # Question metadata + sample test cases
    question_doc = db.collection("roadmap").get(question_key) if question_key else None
    question_info = None
    if question_doc:
        question_info = {
            "key": question_doc.get("_key"),
            "title": question_doc.get("leetcode_title") or question_doc.get("original_title"),
            "difficulty": question_doc.get("leetcode_difficulty"),
            "topics": question_doc.get("topics", []),
            "a2z_step": question_doc.get("a2z_step"),
            "step_number": question_doc.get("step_number"),
            "sample_test_cases": question_doc.get("sample_test_cases", []),
            "examples": question_doc.get("examples", []),
            "constraints": question_doc.get("constraints", []),
        }

    # Test results from the session's last_run (per-case input/expected/actual)
    test_results = []
    if session_id:
        sess_cur = db.aql.execute(
            "FOR s IN sessions FILTER s.session_id == @sid LIMIT 1 RETURN s.last_run",
            bind_vars={"sid": session_id},
        )
        sess_docs = list(sess_cur)
        if sess_docs and sess_docs[0]:
            test_results = sess_docs[0].get("test_results", [])

    # Hints used in the same session for this question
    hints = []
    if session_id:
        hint_cur = db.aql.execute(
            """
            FOR h IN hint_outcomes
              FILTER h.session_key == @sid AND h.question_key == @qk
              SORT h.hint_request_timestamp ASC
              RETURN h
            """,
            bind_vars={"sid": session_id, "qk": question_key or ""},
        )
        hints = list(hint_cur)

    # Mastery deltas logged at the time of this submission (within 5 seconds)
    mastery_deltas = []
    if user_key and created_at:
        delta_cur = db.aql.execute(
            """
            FOR m IN mastery_history
              FILTER m.user_key == @uk
                AND m.question_key == @qk
                AND m.timestamp >= @ts
              SORT m.timestamp ASC
              LIMIT 20
              RETURN m
            """,
            bind_vars={"uk": user_key, "qk": question_key or "", "ts": created_at},
        )
        mastery_deltas = list(delta_cur)

    # All previous attempts on this question by this user (for trajectory view)
    prior_attempts = []
    if user_key and question_key:
        attempts_cur = db.aql.execute(
            """
            FOR s IN submissions
              FILTER s.user_key == @uk AND s.question_key == @qk
              SORT s.created_at ASC
              RETURN KEEP(s, "_key", "status", "created_at", "hints_used",
                          "time_taken_seconds", "attempts_count", "passed_test_cases",
                          "total_test_cases", "error_message")
            """,
            bind_vars={"uk": user_key, "qk": question_key},
        )
        prior_attempts = list(attempts_cur)

    return {
        "submission": sub,
        "user": user_info,
        "question": question_info,
        "test_results": test_results,
        "hints_in_session": hints,
        "mastery_deltas": mastery_deltas,
        "prior_attempts": prior_attempts,
    }


# ---------------------------------------------------------------------------
# Research Metrics (read-only)
# ---------------------------------------------------------------------------

@router.get("/research/mastery_history", dependencies=[Depends(require_admin)])
def get_mastery_history(
    user_key: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
):
    db = get_db()
    bind: Dict[str, Any] = {"limit": limit}
    where = "FILTER r.user_key == @uk" if user_key else ""
    if user_key:
        bind["uk"] = user_key
    cursor = db.aql.execute(
        f"FOR r IN mastery_history {where} SORT r.timestamp DESC LIMIT @limit RETURN r",
        bind_vars=bind,
    )
    return list(cursor)


@router.get("/research/daily_snapshots", dependencies=[Depends(require_admin)])
def get_daily_snapshots(user_key: Optional[str] = Query(None)):
    db = get_db()
    bind: Dict[str, Any] = {}
    where = "FILTER r.user_key == @uk" if user_key else ""
    if user_key:
        bind["uk"] = user_key
    cursor = db.aql.execute(
        f"FOR r IN daily_snapshots {where} SORT r.date DESC RETURN r",
        bind_vars=bind,
    )
    return list(cursor)


@router.get("/research/hint_outcomes", dependencies=[Depends(require_admin)])
def get_hint_outcomes(
    user_key: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
):
    db = get_db()
    bind: Dict[str, Any] = {"limit": limit}
    where = "FILTER r.user_key == @uk" if user_key else ""
    if user_key:
        bind["uk"] = user_key
    cursor = db.aql.execute(
        f"FOR r IN hint_outcomes {where} SORT r.hint_request_timestamp DESC LIMIT @limit RETURN r",
        bind_vars=bind,
    )
    return list(cursor)


@router.get("/research/calibration_pairs", dependencies=[Depends(require_admin)])
def get_calibration_pairs(
    user_key: Optional[str] = Query(None),
    limit: int = Query(500, le=2000),
):
    db = get_db()
    bind: Dict[str, Any] = {"limit": limit}
    where = "FILTER r.user_key == @uk" if user_key else ""
    if user_key:
        bind["uk"] = user_key
    cursor = db.aql.execute(
        f"FOR r IN calibration_pairs {where} SORT r.timestamp_t DESC LIMIT @limit RETURN r",
        bind_vars=bind,
    )
    return list(cursor)


# ---------------------------------------------------------------------------
# Stats overview
# ---------------------------------------------------------------------------

@router.get("/stats", dependencies=[Depends(require_admin)])
def get_stats():
    db = get_db()
    collections = [
        "users", "roadmap", "submissions", "sessions",
        "mastery_history", "hint_outcomes", "daily_snapshots", "calibration_pairs",
    ]
    counts = {}
    for col in collections:
        try:
            cur = db.aql.execute(f"RETURN LENGTH({col})")
            counts[col] = list(cur)[0]
        except Exception:
            counts[col] = -1

    study_cur = db.aql.execute(
        "FOR u IN users FILTER u.is_study_participant == true RETURN u._key"
    )
    counts["study_participants"] = len(list(study_cur))
    return counts
