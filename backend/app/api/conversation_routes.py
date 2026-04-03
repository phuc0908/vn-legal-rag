from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.auth import get_current_user
from app.models.schemas import ConversationOut, MessageOut
from app.db.database import query_all, query_one, get_db
from app.utils.db_helpers import update_conversation_title
import uuid
from datetime import datetime

router = APIRouter(prefix="/conversations", tags=["conversations"])

_DEFAULT_TITLE = "Cuộc trò chuyện mới"

@router.get("/", response_model=List[ConversationOut])
async def get_user_conversations(current_user: dict = Depends(get_current_user)):
    convs = query_all("SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC", (current_user["id"],))

    results = []
    for conv in convs:
        messages = query_all("SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC", (conv["id"],))
        conv["messages"] = messages

        # Nếu title vẫn là mặc định nhưng đã có messages → derive từ tin nhắn user đầu tiên
        if conv.get("title") in (None, "", _DEFAULT_TITLE) and messages:
            first_user = next((m for m in messages if m["role"] == "user"), None)
            if first_user:
                new_title = first_user["content"][:60]
                update_conversation_title(conv["id"], new_title)
                conv["title"] = new_title

        results.append(conv)

    return results

@router.post("/", response_model=ConversationOut)
async def create_conversation(title: str, current_user: dict = Depends(get_current_user)):
    conv_id = str(uuid.uuid4())
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (id, user_id, title) VALUES (%s, %s, %s)",
                (conv_id, current_user["id"], title)
            )
            conn.commit()
            
    return {
        "id": conv_id, 
        "user_id": current_user["id"], 
        "title": title, 
        "created_at": datetime.now(), 
        "messages": []
    }

@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation_detail(conversation_id: str, current_user: dict = Depends(get_current_user)):
    conv = query_one("SELECT * FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, current_user["id"]))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    messages = query_all("SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC", (conversation_id,))
    conv["messages"] = messages
    return conv

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    # Check ownership
    conv = query_one("SELECT id FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, current_user["id"]))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # Delete messages first
            cur.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
            # Delete conversation
            cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            conn.commit()
    
    return None
