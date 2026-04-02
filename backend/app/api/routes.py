from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import traceback
from app.models.schemas import QueryRequest, QueryResponse, HealthResponse
from app.rag.pipeline import get_rag_pipeline
from app.core.auth import get_current_user
from app.utils.db_helpers import save_message, update_conversation_title
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

        response = pipeline.process_query(request)

        # Persistence for authenticated user
        if request.conversation_id:
            try:
                save_message(request.conversation_id, "user", request.query)
                save_message(request.conversation_id, "assistant", response.answer)
            except Exception as db_err:
                # Không fail toàn bộ request nếu chỉ lỗi lưu DB
                print(f"Warning: failed to save messages to DB: {db_err}")
            
            # 3. Optional: Update title if it's new (simple first 30 chars of query)
            # (In a real app, you'd generate a title with LLM)
            # update_conversation_title(request.conversation_id, request.query[:50])

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
