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
    db = get_db()
    ok = RoadmapCRUD(db).delete_roadmap_item(key)
    if not ok:
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    return {"deleted": key}


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
        f"FOR s IN submissions {where} SORT s.created_at DESC LIMIT @offset, @limit RETURN s",
        bind_vars=bind,
    )
    count_cursor = db.aql.execute(
        f"FOR s IN submissions {where} COLLECT WITH COUNT INTO n RETURN n",
        bind_vars={k: v for k, v in bind.items() if k not in ("offset", "limit")},
    )
    count_list = list(count_cursor)
    total = count_list[0] if count_list else 0

    return {"submissions": list(cursor), "total": total}


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
