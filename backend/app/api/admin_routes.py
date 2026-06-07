from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user
from app.db.database import query_one, query_all, get_db
from app.models.schemas import GlobalLimitRequest, UserLimitRequest

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Yêu cầu quyền admin")
    return current_user


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats/overview")
def get_overview(admin=Depends(require_admin)):
    def count(sql, params=()):
        return query_one(sql, params)["cnt"]

    return {
        "users": {
            "total":    count("SELECT COUNT(*) as cnt FROM users"),
            "new_7d":   count("SELECT COUNT(*) as cnt FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"),
            "new_30d":  count("SELECT COUNT(*) as cnt FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"),
            "admins":   count("SELECT COUNT(*) as cnt FROM users WHERE is_admin = 1"),
        },
        "conversations": {
            "total":    count("SELECT COUNT(*) as cnt FROM conversations"),
            "active":   count("SELECT COUNT(*) as cnt FROM conversations WHERE is_deleted = 0"),
            "is_deleted":  count("SELECT COUNT(*) as cnt FROM conversations WHERE is_deleted = 1"),
            "today":    count("SELECT COUNT(*) as cnt FROM conversations WHERE is_deleted = 0 AND DATE(created_at) = CURDATE()"),
            "this_week": count("SELECT COUNT(*) as cnt FROM conversations WHERE is_deleted = 0 AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"),
        },
        "messages": {
            "total":         count("SELECT COUNT(*) as cnt FROM messages"),
            "active":        count("SELECT COUNT(*) as cnt FROM messages WHERE is_deleted = 0"),
            "is_deleted":       count("SELECT COUNT(*) as cnt FROM messages WHERE is_deleted = 1"),
            "user_msgs":     count("SELECT COUNT(*) as cnt FROM messages WHERE role = 'user' AND is_deleted = 0"),
            "assistant_msgs": count("SELECT COUNT(*) as cnt FROM messages WHERE role = 'assistant' AND is_deleted = 0"),
            "today":         count("SELECT COUNT(*) as cnt FROM messages WHERE is_deleted = 0 AND DATE(created_at) = CURDATE()"),
        },
        "bookmarks": {
            "total":       count("SELECT COUNT(*) as cnt FROM bookmarks"),
            "unique_dieu": count("SELECT COUNT(DISTINCT mapc) as cnt FROM bookmarks"),
        },
        "history": {
            "total":       count("SELECT COUNT(*) as cnt FROM view_history"),
            "unique_dieu": count("SELECT COUNT(DISTINCT mapc) as cnt FROM view_history"),
            "unique_users": count("SELECT COUNT(DISTINCT user_id) as cnt FROM view_history"),
        },
        "avg": {
            "msgs_per_conversation": query_one(
                "SELECT ROUND(AVG(cnt), 1) as avg FROM "
                "(SELECT COUNT(*) as cnt FROM messages WHERE is_deleted = 0 GROUP BY conversation_id) t"
            )["avg"] or 0,
            "convs_per_user": query_one(
                "SELECT ROUND(AVG(cnt), 1) as avg FROM "
                "(SELECT COUNT(*) as cnt FROM conversations WHERE is_deleted = 0 GROUP BY user_id) t"
            )["avg"] or 0,
        },
    }


@router.get("/stats/daily")
def get_daily(days: int = Query(30, ge=7, le=90), admin=Depends(require_admin)):
    def daily(sql, params):
        rows = query_all(sql, params)
        return [{"date": str(r["date"]), "count": r["count"]} for r in rows]

    return {
        "new_users": daily(
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM users "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY) "
            "GROUP BY DATE(created_at) ORDER BY date ASC",
            (days,)
        ),
        "new_conversations": daily(
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM conversations "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY) "
            "GROUP BY DATE(created_at) ORDER BY date ASC",
            (days,)
        ),
        "new_messages": daily(
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM messages "
            "WHERE role = 'user' AND is_deleted = 0 AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY) "
            "GROUP BY DATE(created_at) ORDER BY date ASC",
            (days,)
        ),
    }


@router.get("/stats/top-users")
def get_top_users(admin=Depends(require_admin)):
    return query_all(
        """
        SELECT u.id, u.username, u.full_name, u.email, u.is_admin, u.is_active,
               u.created_at,
               COUNT(DISTINCT c.id)  AS conversation_count,
               COUNT(DISTINCT m.id)  AS message_count,
               COUNT(DISTINCT b.id)  AS bookmark_count
        FROM users u
        LEFT JOIN conversations c ON c.user_id = u.id AND c.is_deleted = 0
        LEFT JOIN messages m      ON m.conversation_id = c.id AND m.role = 'user' AND m.is_deleted = 0
        LEFT JOIN bookmarks b     ON b.user_id = u.id
        GROUP BY u.id
        ORDER BY message_count DESC
        LIMIT 20
        """
    )


@router.get("/stats/top-bookmarks")
def get_top_bookmarks(admin=Depends(require_admin)):
    return query_all(
        """
        SELECT mapc, ten, chude_ten, COUNT(*) AS count
        FROM bookmarks
        GROUP BY mapc, ten, chude_ten
        ORDER BY count DESC
        LIMIT 20
        """
    )


@router.get("/stats/top-viewed")
def get_top_viewed(admin=Depends(require_admin)):
    return query_all(
        """
        SELECT mapc, ten, chude_ten, COUNT(*) AS count
        FROM view_history
        GROUP BY mapc, ten, chude_ten
        ORDER BY count DESC
        LIMIT 20
        """
    )


# ── Users ──────────────────────────────────────────────────────────────────────

@router.patch("/users/{user_id}/toggle-active")
def toggle_active(user_id: int, admin=Depends(require_admin)):
    user = query_one("SELECT id, is_active, is_admin FROM users WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["is_admin"]:
        raise HTTPException(status_code=400, detail="Không thể vô hiệu hóa tài khoản admin")
    new_val = 0 if user["is_active"] else 1
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (new_val, user_id))
            conn.commit()
    return {"id": user_id, "is_active": bool(new_val)}


@router.get("/users")
def get_all_users(admin=Depends(require_admin)):
    return query_all(
        """
        SELECT u.id, u.username, u.full_name, u.email, u.is_admin, u.is_active, u.created_at,
               u.daily_question_limit,
               COUNT(DISTINCT c.id) AS conversation_count,
               (SELECT COUNT(*) FROM messages m2
                JOIN conversations c2 ON m2.conversation_id = c2.id
                WHERE c2.user_id = u.id AND m2.role = 'user'
                  AND DATE(m2.created_at) = CURDATE() AND m2.is_deleted = 0
               ) AS today_question_count
        FROM users u
        LEFT JOIN conversations c ON c.user_id = u.id AND c.is_deleted = 0
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
    )


@router.patch("/users/{user_id}/toggle-admin")
def toggle_admin(user_id: int, admin=Depends(require_admin)):
    user = query_one("SELECT id, is_admin FROM users WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_val = 0 if user["is_admin"] else 1
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_admin = %s WHERE id = %s", (new_val, user_id))
            conn.commit()
    return {"id": user_id, "is_admin": bool(new_val)}


# ── Settings (giới hạn câu hỏi) ───────────────────────────────────────────────

@router.get("/settings")
def get_settings(admin=Depends(require_admin)):
    row = query_one("SELECT `value` FROM system_settings WHERE `key` = 'default_daily_limit'")
    return {"default_daily_limit": int(row["value"]) if row else 20}


@router.put("/settings/daily_limit")
def update_daily_limit(body: GlobalLimitRequest, admin=Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO system_settings (`key`, `value`) VALUES ('default_daily_limit', %s) "
                "ON DUPLICATE KEY UPDATE `value` = %s",
                (str(body.limit), str(body.limit))
            )
            conn.commit()
    return {"default_daily_limit": body.limit}


@router.put("/users/{user_id}/limit")
def set_user_limit(user_id: int, body: UserLimitRequest, admin=Depends(require_admin)):
    user = query_one("SELECT id FROM users WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET daily_question_limit = %s WHERE id = %s", (body.limit, user_id))
            conn.commit()
    return {"user_id": user_id, "daily_question_limit": body.limit}


@router.delete("/users/{user_id}/limit")
def reset_user_limit(user_id: int, admin=Depends(require_admin)):
    user = query_one("SELECT id FROM users WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET daily_question_limit = NULL WHERE id = %s", (user_id,))
            conn.commit()
    return {"user_id": user_id, "daily_question_limit": None}
