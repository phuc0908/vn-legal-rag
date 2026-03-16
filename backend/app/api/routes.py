from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.models.schemas import QueryRequest, QueryResponse, HealthResponse
from app.rag.pipeline import get_rag_pipeline
from app.utils.helpers import save_query_response

router = APIRouter(prefix="/api", tags=["rag"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
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

        conversation_id = request.conversation_id or "default"
        save_query_response(conversation_id, request.query, response)

        return response

    except Exception as e:
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


@router.post("/documents/add")
async def add_document(title: str, content: str, metadata: Optional[dict] = None):
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
