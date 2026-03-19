from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.auth import get_current_user
from app.models.schemas import ConversationOut, MessageOut
from app.db.database import query_all, query_one, get_db
import uuid

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("/", response_model=List[ConversationOut])
async def get_user_conversations(current_user: dict = Depends(get_current_user)):
    convs = query_all("SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC", (current_user["id"],))
    
    # Process each conversation to add its messages
    results = []
    for conv in convs:
        messages = query_all("SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC", (conv["id"],))
        conv["messages"] = messages
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
            
    return {"id": conv_id, "user_id": current_user["id"], "title": title, "created_at": None, "messages": []}

@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation_detail(conversation_id: str, current_user: dict = Depends(get_current_user)):
    conv = query_one("SELECT * FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, current_user["id"]))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    messages = query_all("SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC", (conversation_id,))
    conv["messages"] = messages
    return conv
