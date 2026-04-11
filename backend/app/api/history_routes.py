from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.auth import get_current_user
from app.db.database import query_all, get_db

router = APIRouter(prefix="/history", tags=["history"])


class HistoryEntry(BaseModel):
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
def get_history(current_user: dict = Depends(get_current_user)):
    """List view history for current user, newest first"""
    rows = query_all(
        """
        SELECT mapc, chimuc, ten, vbqppl,
               chude_id, chude_ten, demuc_id, demuc_ten,
               chuong_id, chuong_ten, chuong_chimuc, viewed_at
        FROM view_history
        WHERE user_id = %s
        ORDER BY viewed_at DESC
        LIMIT 100
        """,
        (current_user["id"],),
    )
    return rows


@router.post("/")
def add_history(body: HistoryEntry, current_user: dict = Depends(get_current_user)):
    """Upsert a view history entry (insert or update viewed_at)"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO view_history
                    (user_id, mapc, chimuc, ten, vbqppl,
                     chude_id, chude_ten, demuc_id, demuc_ten,
                     chuong_id, chuong_ten, chuong_chimuc)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    viewed_at = CURRENT_TIMESTAMP
                """,
                (
                    current_user["id"], body.mapc, body.chimuc, body.ten, body.vbqppl,
                    body.chude_id, body.chude_ten, body.demuc_id, body.demuc_ten,
                    body.chuong_id, body.chuong_ten, body.chuong_chimuc,
                ),
            )
            conn.commit()
    return {"ok": True}


@router.delete("/")
def clear_history(current_user: dict = Depends(get_current_user)):
    """Clear all history for current user"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM view_history WHERE user_id = %s", (current_user["id"],))
            conn.commit()
    return {"ok": True}


@router.delete("/{mapc:path}")
def remove_history(mapc: str, current_user: dict = Depends(get_current_user)):
    """Remove one entry from history"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM view_history WHERE user_id = %s AND mapc = %s",
                (current_user["id"], mapc),
            )
            conn.commit()
    return {"ok": True}
