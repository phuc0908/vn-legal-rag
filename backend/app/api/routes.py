from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import traceback
from app.models.schemas import QueryRequest, QueryResponse, HealthResponse, ChatTurn
from app.rag.pipeline import get_rag_pipeline
from app.core.auth import get_current_user
from app.utils.db_helpers import save_message, update_conversation_title
from app.db.database import query_one, query_all
import app.rag.pipeline as pipeline_module
import app.rag.llm as llm_module

router = APIRouter(tags=["rag"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """
    Process a legal query and retrieve relevant documents with AI-generated answer
    """
    try:
        pipeline = get_rag_pipeline()
        if pipeline is None:
            raise HTTPException(
                status_code=500,
                detail="RAG pipeline not initialized"
            )

        # Nạp lịch sử hội thoại từ DB (tối đa 3 lượt = 6 messages gần nhất)
        if request.conversation_id and request.chat_history is None:
            try:
                rows = query_all(
                    "SELECT role, content FROM messages WHERE conversation_id = %s "
                    "ORDER BY created_at DESC LIMIT 6",
                    (request.conversation_id,)
                )
                if rows:
                    history = [ChatTurn(role=r["role"], content=r["content"]) for r in reversed(rows)]
                    request = request.model_copy(update={"chat_history": history})
            except Exception as hist_err:
                print(f"Warning: không tải được lịch sử hội thoại: {hist_err}")

        response = pipeline.process_query(request)

        # Persistence for authenticated user
        if request.conversation_id:
            try:
                # Kiểm tra trước khi lưu — nếu chưa có message nào thì đây là query đầu tiên
                existing = query_one(
                    "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = %s",
                    (request.conversation_id,)
                )
                is_first_message = existing["cnt"] == 0

                save_message(request.conversation_id, "user", request.query)
                save_message(request.conversation_id, "assistant", response.answer)

                if is_first_message:
                    update_conversation_title(request.conversation_id, request.query[:60])
            except Exception as db_err:
                # Không fail toàn bộ request nếu chỉ lỗi lưu DB
                print(f"Warning: failed to save messages to DB: {db_err}")

        return response

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check API health and component status
    """
    pipeline = get_rag_pipeline()
    llm_configured = pipeline.llm_manager is not None if pipeline else False
    vector_store_ready = pipeline.rag_system is not None if pipeline else False

    return HealthResponse(
        status="ok",
        version="1.0.0",
        llm_configured=llm_configured,
        vector_store_ready=vector_store_ready
    )


@router.post("/reload")
async def reload_llm():
    """Reset LLM and pipeline to load new key from .env"""
    llm_module.llm_manager = None
    pipeline_module.rag_pipeline = None
    pipeline = get_rag_pipeline()
    return {"status": "reloaded", "llm_ok": pipeline.llm_manager is not None}


@router.post("/documents/add")
async def add_document(title: str, content: str, metadata: Optional[dict] = None, current_user: dict = Depends(get_current_user)):
    """
    Add a legal document to the knowledge base
    """
    try:
        pipeline = get_rag_pipeline()
        if pipeline is None:
            raise HTTPException(
                status_code=500,
                detail="RAG pipeline not initialized"
            )

        doc_metadata = metadata or {}
        doc_metadata["title"] = title

        pipeline.rag_system.add_document(content, doc_metadata)

        return {
            "status": "success",
            "message": f"Document '{title}' added successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding document: {str(e)}"
        )
