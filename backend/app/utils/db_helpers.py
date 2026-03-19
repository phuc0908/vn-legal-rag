from app.db.database import get_db

def save_message(conversation_id: str, role: str, content: str):
    """Save a single message to the database"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                (conversation_id, role, content)
            )
            conn.commit()

def update_conversation_title(conversation_id: str, title: str):
    """Update conversation title if it's the first message or generic"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE conversations SET title = %s WHERE id = %s",
                (title, conversation_id)
            )
            conn.commit()
