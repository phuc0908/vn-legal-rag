import re
import time
from typing import List, Optional

from app.core.config import settings
from app.db.database import query_all
from app.models.schemas import QueryRequest, QueryResponse, SourceDocument
from app.rag.llm import TopicRouter, get_llm_manager
from app.rag.retrieval import get_hon_nhan_rag_system, get_rag_system


class RAGPipeline:
    """Main RAG pipeline that combines retrieval and generation."""

    def __init__(self):
        print("[PIPELINE] Khởi tạo RAGPipeline...")
        self.rag_system = get_rag_system()
        self._hon_nhan_system = get_hon_nhan_rag_system()
        self.llm_manager = get_llm_manager()
        self.topic_router: Optional[TopicRouter] = self._init_topic_router()
        print("[PIPELINE] Sẵn sàng.")

    def _get_rag_for_module(self, module: str):
        if module == "hon_nhan":
            return self._hon_nhan_system
        return self.rag_system

    def _init_topic_router(self) -> Optional[TopicRouter]:
        if not settings.TOPIC_ROUTER_ENABLED:
            print("[PIPELINE] TopicRouter bị tắt (TOPIC_ROUTER_ENABLED=False)")
            return None
        if not self.llm_manager:
            print("[PIPELINE] Bỏ qua TopicRouter - LLM chưa sẵn sàng")
            return None
        try:
            topics = query_all("SELECT id, ten FROM pdchude ORDER BY id")
            if not topics:
                print("[PIPELINE] Bảng pdchude trống - bỏ qua TopicRouter")
                return None
            return TopicRouter(self.llm_manager.llm, list(topics))
        except Exception as e:
            print(f"[PIPELINE] Không khởi tạo được TopicRouter: {e}")
            return None

    def _normalize_query(self, query: str) -> str:
        return re.sub(r"\s+", " ", (query or "").strip().lower())

    def _is_lightweight_query(self, query: str) -> bool:
        """Skip RAG for greetings, acknowledgements, and too-short non-legal input."""
        q = self._normalize_query(query)
        if not q:
            return True

        greetings = {
            "hi", "hello", "hey", "alo", "chao", "chào", "xin chào",
            "cam on", "cảm ơn", "thanks", "thank you", "ok", "oke", "ừ", "uh",
        }
        if q in greetings:
            return True

        legal_hints = [
            "luật", "điều", "khoản", "nghị định", "thông tư", "xử phạt",
            "phạt", "tội", "trách nhiệm", "hợp đồng", "ly hôn", "kết hôn",
            "đất", "thuế", "bảo hiểm", "thừa kế", "lao động", "hộ khẩu",
            "ngoại tình", "cấp dưỡng", "nuôi con", "tài sản chung", "tài sản riêng",
            "vợ chồng", "mang thai hộ", "tảo hôn",
        ]
        if any(hint in q for hint in legal_hints):
            return False

        tokens = re.findall(r"\w+", q, flags=re.UNICODE)
        return len(tokens) <= 2

    def _last_user_question(self, history) -> Optional[str]:
        for turn in reversed(history or []):
            if getattr(turn, "role", "") == "user" and getattr(turn, "content", "").strip():
                return turn.content.strip()
        return None

    def _suggestions_for_short_query(self, request: QueryRequest) -> str:
        previous = self._last_user_question(request.chat_history)
        if previous:
            topic = previous[:120].rstrip()
            return (
                "Bạn có thể hỏi tiếp theo hướng cụ thể hơn, ví dụ:\n"
                f"- Quy định pháp luật nào áp dụng cho: \"{topic}\"?\n"
                "- Điều kiện, thủ tục hoặc hồ sơ cần chuẩn bị là gì?\n"
                "- Trường hợp vi phạm thì mức phạt hoặc hậu quả pháp lý ra sao?"
            )
        return (
            "Bạn có thể hỏi một câu pháp lý cụ thể hơn, ví dụ:\n"
            "- Điều kiện kết hôn theo pháp luật Việt Nam là gì?\n"
            "- Thủ tục ly hôn đơn phương cần những giấy tờ nào?\n"
            "- Khi tranh chấp tài sản chung vợ chồng thì giải quyết thế nào?"
        )

    def _lightweight_answer(self, request: QueryRequest) -> str:
        q = self._normalize_query(request.query)
        if q in {"cam on", "cảm ơn", "thanks", "thank you"}:
            return (
                "Không có gì. Nếu bạn có câu hỏi pháp lý cụ thể, tôi có thể hỗ trợ tra cứu và giải thích.\n\n"
                + self._suggestions_for_short_query(request)
            )
        return (
            "Xin chào! Tôi có thể hỗ trợ bạn tra cứu và giải thích các vấn đề pháp luật Việt Nam.\n\n"
            + self._suggestions_for_short_query(request)
        )

    def process_query(self, request: QueryRequest) -> QueryResponse:
        start_time = time.time()
        sep = "-" * 60

        print(f"\n{sep}")
        print(f"[QUERY] {request.query}")
        print(
            f"[QUERY] conversation_id={request.conversation_id} | "
            f"top_k={request.top_k} | chu_de_id={request.chu_de_id} | module={request.module}"
        )

        if self._is_lightweight_query(request.query):
            print("[QUERY] Câu nhập ngắn/không phải câu hỏi pháp lý - bỏ qua retrieval")
            total_time = time.time() - start_time
            print(f"\n[DONE] Tổng thời gian xử lý: {total_time:.2f}s")
            print(f"{sep}\n")
            return QueryResponse(
                query=request.query,
                answer=self._lightweight_answer(request),
                sources=[],
                processing_time=total_time,
                model_used=None,
            )

        search_query = request.query

        chu_de_id = request.chu_de_id
        rag = self._get_rag_for_module(request.module)
        if request.module:
            print(f"[MODULE] Sử dụng module '{request.module}' - bỏ qua topic router")
            filter_where = None
        else:
            if not chu_de_id and self.topic_router:
                print("[ROUTER] Đang phân loại chủ đề cho query...")
                t_rt = time.time()
                chu_de_id = self.topic_router.route(search_query)
                print(f"[ROUTER] Hoàn tất sau {time.time() - t_rt:.2f}s -> chu_de_id={chu_de_id}")
            filter_where = {"chu_de_id": str(chu_de_id)} if chu_de_id else None

        print(f"\n[RETRIEVAL] Đang tìm kiếm (module={request.module or 'full'})...")
        t0 = time.time()
        retrieved_docs = rag.retrieve(
            search_query,
            top_k=request.top_k,
            filter_where=filter_where,
            rerank_query=request.query,
        )
        retrieval_time = time.time() - t0
        print(f"[RETRIEVAL] Hoàn tất sau {retrieval_time:.2f}s - tìm được {len(retrieved_docs)} đoạn văn bản")

        if not retrieved_docs and request.chu_de_id and not request.module:
            print(f"[RETRIEVAL] Không tìm thấy trong chủ đề ID={request.chu_de_id} - fallback toàn corpus...")
            t0 = time.time()
            retrieved_docs = rag.retrieve(
                search_query,
                top_k=request.top_k,
                filter_where=None,
                rerank_query=request.query,
            )
            print(f"[RETRIEVAL] Fallback hoàn tất sau {time.time() - t0:.2f}s - tìm được {len(retrieved_docs)} đoạn văn bản")

        if not retrieved_docs:
            print("[RETRIEVAL] Không có kết quả retrieval")
        else:
            for i, doc in enumerate(retrieved_docs, 1):
                score = doc.get("score", 0)
                meta = doc.get("metadata", {})
                preview = doc["content"][:120].replace("\n", " ")
                print(f"  [DOC {i}] score={score:.4f} | id_vb={meta.get('id_vb')} | {preview}...")

        context = self._format_context(retrieved_docs)
        print(f"\n[CONTEXT] Độ dài context: {len(context)} ký tự")

        if not self.llm_manager:
            answer = "LLM chưa được cấu hình."
            print("[LLM] WARN: LLM manager chưa khởi tạo")
        else:
            print(f"[LLM] Gửi prompt tới {self.llm_manager.llm.__class__.__name__}...")
            t1 = time.time()
            answer = self.llm_manager.generate_answer(
                request.query,
                context,
                history=request.chat_history,
            )
            llm_time = time.time() - t1
            print(f"[LLM] Nhận phản hồi sau {llm_time:.2f}s - độ dài câu trả lời: {len(answer)} ký tự")
            print(f"[LLM] Preview: {answer[:200].replace(chr(10), ' ')}...")

        sources = self._build_sources(retrieved_docs)

        total_time = time.time() - start_time
        print(f"\n[DONE] Tổng thời gian xử lý: {total_time:.2f}s")
        print(f"{sep}\n")

        return QueryResponse(
            query=request.query,
            answer=answer,
            sources=sources,
            processing_time=total_time,
            model_used=self.llm_manager.llm.__class__.__name__ if self.llm_manager else None,
        )

    def _source_title(self, metadata: dict) -> str:
        parts = []
        loai_vb = metadata.get("loai_vb", "").strip()
        so_hieu = metadata.get("so_hieu", "").strip()
        co_quan = metadata.get("co_quan", "").strip()
        tieu_de = metadata.get("tieu_de", "").strip()
        dieu_ten = metadata.get("dieu_ten", "").strip()

        if loai_vb and so_hieu:
            parts.append(f"{loai_vb} {so_hieu}")
        elif loai_vb:
            parts.append(loai_vb)
        if co_quan:
            parts.append(co_quan)
        if tieu_de:
            parts.append(tieu_de)
        elif dieu_ten:
            parts.append(dieu_ten)
        if parts:
            return " - ".join(parts)

        return metadata.get("article_title") or metadata.get("doc_name") or f"VB #{metadata.get('id_vb', '?')}"

    def _build_sources(self, documents: List[dict]) -> List[SourceDocument]:
        sources = []
        seen = set()
        for doc in documents:
            metadata = doc.get("metadata", {})
            title = self._source_title(metadata)
            if title == "VB #?":
                continue

            key = metadata.get("dieu_mapc") or metadata.get("id_vb") or metadata.get("url") or title
            if key in seen:
                continue
            seen.add(key)

            sources.append(SourceDocument(
                title=title,
                content=doc["content"][:500],
                relevance_score=float(doc["score"]),
                metadata=metadata,
                url=metadata.get("url"),
            ))
        return sources

    def _format_context(self, documents: List[dict]) -> str:
        context_parts = []
        for i, doc in enumerate(documents, 1):
            meta = doc.get("metadata", {})
            loai_vb = meta.get("loai_vb", "")
            so_hieu = meta.get("so_hieu", "")
            ten_vb = meta.get("ten_vb", "")
            co_quan = meta.get("co_quan", "")
            ten_chuong_cha = meta.get("ten_chuong_cha", "")
            tieu_de = meta.get("tieu_de", "")
            dieu_ten = meta.get("dieu_ten", "")

            chu_de = meta.get("chu_de", "")
            de_muc = meta.get("de_muc", "")

            lines = []
            if chu_de:
                lines.append(f"Chủ đề: {chu_de}")
            if de_muc:
                lines.append(f"Đề mục: {de_muc}")
            if loai_vb or so_hieu:
                lines.append(f"Văn bản: {loai_vb} {so_hieu}".strip())
            if ten_vb:
                lines.append(f"Tên: {ten_vb}")
            if co_quan:
                lines.append(f"Cơ quan: {co_quan}")
            if ten_chuong_cha:
                lines.append(f"Chương: {ten_chuong_cha}")
            if tieu_de:
                lines.append(f"Điều: {tieu_de}")
            elif dieu_ten:
                lines.append(f"Điều: {dieu_ten}")

            header = f"[Nguồn {i}] " + " | ".join(lines) if lines else f"[Nguồn {i}]"
            content = doc["content"][:1500]
            context_parts.append(f"{header}\n{content}")
        context = "\n\n---\n\n".join(context_parts)
        return context[:4000]


rag_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
    return rag_pipeline
