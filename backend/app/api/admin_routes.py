from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from app.db.database import query_one, query_all

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Yêu cầu quyền admin")
    return current_user


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
def get_daily(admin=Depends(require_admin)):
    def daily(sql):
        rows = query_all(sql)
        return [{"date": str(r["date"]), "count": r["count"]} for r in rows]

    return {
        "new_users": daily(
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM users "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) "
            "GROUP BY DATE(created_at) ORDER BY date ASC"
        ),
        "new_conversations": daily(
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM conversations "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) "
            "GROUP BY DATE(created_at) ORDER BY date ASC"
        ),
        "new_messages": daily(
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM messages "
            "WHERE role = 'user' AND is_deleted = 0 AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) "
            "GROUP BY DATE(created_at) ORDER BY date ASC"
        ),
    }


@router.get("/stats/top-users")
def get_top_users(admin=Depends(require_admin)):
    return query_all(
        """
        SELECT u.id, u.username, u.full_name, u.email, u.is_admin,
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


@router.get("/users")
def get_all_users(admin=Depends(require_admin)):
    return query_all(
        """
        SELECT u.id, u.username, u.full_name, u.email, u.is_admin, u.created_at,
               COUNT(DISTINCT c.id) AS conversation_count
        FROM users u
        LEFT JOIN conversations c ON c.user_id = u.id AND c.is_deleted = 0
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
    )


@router.patch("/users/{user_id}/toggle-admin")
def toggle_admin(user_id: int, admin=Depends(require_admin)):
    from app.db.database import get_db
    user = query_one("SELECT id, is_admin FROM users WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_val = 0 if user["is_admin"] else 1
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_admin = %s WHERE id = %s", (new_val, user_id))
            conn.commit()
    return {"id": user_id, "is_admin": bool(new_val)}
