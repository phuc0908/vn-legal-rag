from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import traceback
from app.models.schemas import QueryRequest, QueryResponse, HealthResponse, ChatTurn, QuotaUsage
from app.rag.pipeline import get_rag_pipeline
from app.core.auth import get_current_user
from app.utils.db_helpers import save_message, update_conversation_title
from app.db.database import query_one, query_all
import app.rag.pipeline as pipeline_module
import app.rag.llm as llm_module

router = APIRouter(tags=["rag"])


def _get_effective_limit(user_id: int) -> Optional[int]:
    """Trả về giới hạn câu hỏi/ngày của user. None = vô hạn."""
    user_row = query_one("SELECT daily_question_limit FROM users WHERE id = %s", (user_id,))
    if user_row and user_row["daily_question_limit"] is not None:
        val = user_row["daily_question_limit"]
        return None if val == 0 else val
    setting = query_one("SELECT `value` FROM system_settings WHERE `key` = 'default_daily_limit'")
    if setting:
        val = int(setting["value"])
        return None if val == 0 else val
    return 20


def _count_today_questions(user_id: int) -> int:
    result = query_one(
        "SELECT COUNT(*) as cnt FROM messages m "
        "JOIN conversations c ON m.conversation_id = c.id "
        "WHERE c.user_id = %s AND m.role = 'user' "
        "AND DATE(m.created_at) = CURDATE() AND m.is_deleted = 0",
        (user_id,)
    )
    return result["cnt"] if result else 0


def _enforce_quota(current_user: dict) -> Optional[int]:
    """Kiểm tra giới hạn câu hỏi/ngày. Trả về effective_limit, raise 429 nếu hết lượt."""
    if current_user.get("is_admin"):
        return None
    effective_limit = _get_effective_limit(current_user["id"])
    if effective_limit is not None:
        used_count = _count_today_questions(current_user["id"])
        if used_count >= effective_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Bạn đã đạt giới hạn câu hỏi hôm nay",
                    "limit": effective_limit,
                    "used": used_count,
                }
            )
    return effective_limit


def _load_history(request: QueryRequest) -> QueryRequest:
    """Nạp lịch sử hội thoại từ DB (tối đa 3 lượt = 6 messages gần nhất) vào request."""
    if request.conversation_id and request.chat_history is None:
        try:
            rows = query_all(
                "SELECT role, content FROM messages WHERE conversation_id = %s AND is_deleted = 0 "
                "ORDER BY created_at DESC LIMIT 6",
                (request.conversation_id,)
            )
            if rows:
                history = [ChatTurn(role=r["role"], content=r["content"]) for r in reversed(rows)]
                request = request.model_copy(update={"chat_history": history})
        except Exception as hist_err:
            print(f"Warning: không tải được lịch sử hội thoại: {hist_err}")
    return request


def _persist_turn(request: QueryRequest, answer: str):
    """Lưu cặp message user/assistant và cập nhật tiêu đề nếu là câu đầu tiên."""
    if not request.conversation_id:
        return
    try:
        existing = query_one(
            "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = %s AND is_deleted = 0",
            (request.conversation_id,)
        )
        is_first_message = existing["cnt"] == 0
        save_message(request.conversation_id, "user", request.query)
        save_message(request.conversation_id, "assistant", answer)
        if is_first_message:
            update_conversation_title(request.conversation_id, request.query[:60])
    except Exception as db_err:
        print(f"Warning: failed to save messages to DB: {db_err}")


def _build_usage(current_user: dict, effective_limit: Optional[int]) -> Optional[QuotaUsage]:
    """Tính thông tin quota sau khi đã lưu câu hỏi (chỉ cho user thường có giới hạn)."""
    if current_user.get("is_admin") or effective_limit is None:
        return None
    used_after = _count_today_questions(current_user["id"])
    return QuotaUsage(
        used=used_after,
        limit=effective_limit,
        remaining=max(0, effective_limit - used_after),
    )


@router.get("/quota")
async def get_quota(current_user: dict = Depends(get_current_user)):
    if current_user.get("is_admin"):
        return {"is_admin": True, "used": 0, "limit": None, "remaining": None}
    limit = _get_effective_limit(current_user["id"])
    used = _count_today_questions(current_user["id"])
    remaining = None if limit is None else max(0, limit - used)
    return {"is_admin": False, "used": used, "limit": limit, "remaining": remaining}


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """
    Process a legal query and retrieve relevant documents with AI-generated answer
    """
    try:
        # Kiểm tra giới hạn câu hỏi hàng ngày (bỏ qua cho admin)
        effective_limit = None
        if not current_user.get("is_admin"):
            effective_limit = _get_effective_limit(current_user["id"])
            if effective_limit is not None:
                used_count = _count_today_questions(current_user["id"])
                if used_count >= effective_limit:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "message": "Bạn đã đạt giới hạn câu hỏi hôm nay",
                            "limit": effective_limit,
                            "used": used_count,
                        }
                    )

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
                    "SELECT role, content FROM messages WHERE conversation_id = %s AND is_deleted = 0 "
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
                    "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = %s AND is_deleted = 0",
                    (request.conversation_id,)
                )
                is_first_message = existing["cnt"] == 0

                save_message(request.conversation_id, "user", request.query)
                save_message(request.conversation_id, "assistant", response.answer)

                if is_first_message:
                    update_conversation_title(request.conversation_id, request.query[:60])
            except Exception as db_err:
                print(f"Warning: failed to save messages to DB: {db_err}")

        # Đính kèm thông tin quota vào response (chỉ cho user thường có giới hạn)
        if not current_user.get("is_admin") and effective_limit is not None:
            used_after = _count_today_questions(current_user["id"])
            usage = QuotaUsage(
                used=used_after,
                limit=effective_limit,
                remaining=max(0, effective_limit - used_after),
            )
            response = response.model_copy(update={"usage": usage})

        return response

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


def _sse(event: str, data: dict) -> str:
    """Định dạng một sự kiện Server-Sent Events."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/query/stream")
async def query_stream(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Xử lý truy vấn pháp lý và stream câu trả lời theo từng đoạn (Server-Sent Events)."""
    # Kiểm tra quota trước khi mở stream để có thể trả về 429 chuẩn
    effective_limit = _enforce_quota(current_user)

    pipeline = get_rag_pipeline()
    if pipeline is None:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    prepared_request = _load_history(request)

    def event_generator():
        try:
            for ev_type, payload in pipeline.process_query_stream(prepared_request):
                if ev_type == "sources":
                    yield _sse("sources", {"sources": payload})
                elif ev_type == "token":
                    yield _sse("token", {"text": payload})
                elif ev_type == "done":
                    _persist_turn(prepared_request, payload.get("answer", ""))
                    usage = _build_usage(current_user, effective_limit)
                    yield _sse("done", {
                        "model_used": payload.get("model_used"),
                        "usage": usage.model_dump() if usage else None,
                    })
        except Exception as e:
            traceback.print_exc()
            yield _sse("error", {"message": f"Error processing query: {str(e)}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # tắt buffering của nginx/proxy
        },
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
