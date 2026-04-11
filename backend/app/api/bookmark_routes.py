from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.auth import get_current_user
from app.db.database import query_all, query_one, get_db

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


class BookmarkToggle(BaseModel):
    mapc: str
    chimuc: Optional[str] = None
    ten: Optional[str] = None
    vbqppl: Optional[str] = None
    chude_id: Optional[str] = None
    chude_ten: Optional[str] = None
    demuc_id: Optional[str] = None
    demuc_ten: Optional[str] = None
    chuong_id: Optional[str] = None
    chuong_ten: Optional[str] = None
    chuong_chimuc: Optional[str] = None


@router.get("/")
def list_bookmarks(current_user: dict = Depends(get_current_user)):
    """List all bookmarks for the current user, newest first"""
    rows = query_all(
        """
        SELECT mapc, chimuc, ten, vbqppl,
               chude_id, chude_ten, demuc_id, demuc_ten,
               chuong_id, chuong_ten, chuong_chimuc, created_at
        FROM bookmarks
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (current_user["id"],),
    )
    return rows


@router.post("/toggle")
def toggle_bookmark(body: BookmarkToggle, current_user: dict = Depends(get_current_user)):
    """Add bookmark if not exists, remove if exists. Returns current state."""
    existing = query_one(
        "SELECT id FROM bookmarks WHERE user_id = %s AND mapc = %s",
        (current_user["id"], body.mapc),
    )
    with get_db() as conn:
        with conn.cursor() as cur:
            if existing:
                cur.execute(
                    "DELETE FROM bookmarks WHERE user_id = %s AND mapc = %s",
                    (current_user["id"], body.mapc),
                )
                conn.commit()
                return {"bookmarked": False}
            else:
                cur.execute(
                    """
                    INSERT INTO bookmarks
                        (user_id, mapc, chimuc, ten, vbqppl,
                         chude_id, chude_ten, demuc_id, demuc_ten,
                         chuong_id, chuong_ten, chuong_chimuc)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        current_user["id"], body.mapc, body.chimuc, body.ten, body.vbqppl,
                        body.chude_id, body.chude_ten, body.demuc_id, body.demuc_ten,
                        body.chuong_id, body.chuong_ten, body.chuong_chimuc,
                    ),
                )
                conn.commit()
                return {"bookmarked": True}


@router.get("/{mapc:path}/status")
def bookmark_status(mapc: str, current_user: dict = Depends(get_current_user)):
    """Check if a điều is bookmarked by the current user"""
    existing = query_one(
        "SELECT id FROM bookmarks WHERE user_id = %s AND mapc = %s",
        (current_user["id"], mapc),
    )
    return {"bookmarked": existing is not None}


@router.delete("/{mapc:path}")
def remove_bookmark(mapc: str, current_user: dict = Depends(get_current_user)):
    """Remove a bookmark"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM bookmarks WHERE user_id = %s AND mapc = %s",
                (current_user["id"], mapc),
            )
            conn.commit()
    return {"bookmarked": False}
