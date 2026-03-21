import time
from typing import List, Optional
from app.models.schemas import QueryRequest, QueryResponse, SourceDocument
from app.rag.retrieval import get_rag_system
from app.rag.llm import get_llm_manager

class RAGPipeline:
    """Main RAG pipeline that combines retrieval and generation"""

    def __init__(self):
        print("[PIPELINE] Khởi tạo RAGPipeline...")
        self.rag_system = get_rag_system()
        self.llm_manager = get_llm_manager()
        print("[PIPELINE] Sẵn sàng.")

    def process_query(self, request: QueryRequest) -> QueryResponse:
        """Process a query through the RAG pipeline"""
        start_time = time.time()
        sep = "─" * 60

        print(f"\n{sep}")
        print(f"[QUERY] {request.query}")
        print(f"[QUERY] conversation_id={request.conversation_id} | top_k={request.top_k} | chu_de_id={request.chu_de_id}")

        # ── 1. Query rewriting ────────────────────────────────────
        search_query = request.query
        if self.llm_manager:
            print(f"[REWRITE] Đang viết lại query...")
            t_rw = time.time()
            search_query = self.llm_manager.rewrite_query(request.query)
            print(f"[REWRITE] '{request.query}' → '{search_query}' ({time.time()-t_rw:.2f}s)")

        # ── 2. Retrieval ──────────────────────────────────────────
        print(f"\n[RETRIEVAL] Đang tìm kiếm trong ChromaDB...")
        filter_where = {"chu_de_id": str(request.chu_de_id)} if request.chu_de_id else None
        t0 = time.time()
        retrieved_docs = self.rag_system.retrieve(search_query, top_k=request.top_k, filter_where=filter_where)
        retrieval_time = time.time() - t0
        print(f"[RETRIEVAL] Hoàn tất sau {retrieval_time:.2f}s — tìm được {len(retrieved_docs)} đoạn văn bản")

        if not retrieved_docs:
            print("[RETRIEVAL] Không có kết quả nào vượt ngưỡng similarity — tiếp tục với LLM kiến thức chung")
        else:
            for i, doc in enumerate(retrieved_docs, 1):
                score = doc.get("score", 0)
                meta = doc.get("metadata", {})
                preview = doc["content"][:120].replace("\n", " ")
                print(f"  [DOC {i}] score={score:.4f} | id_vb={meta.get('id_vb')} | {preview}...")

        # ── 3. Format context ─────────────────────────────────────
        context = self._format_context(retrieved_docs)
        print(f"\n[CONTEXT] Độ dài context: {len(context)} ký tự")

        # ── 4. LLM generation ─────────────────────────────────────
        if not self.llm_manager:
            answer = "LLM chưa được cấu hình."
            print("[LLM] WARN: LLM manager chưa khởi tạo")
        else:
            print(f"[LLM] Gửi prompt tới Gemini ({self.llm_manager.llm.__class__.__name__})...")
            t1 = time.time()
            answer = self.llm_manager.generate_answer(request.query, context)
            llm_time = time.time() - t1
            print(f"[LLM] Nhận phản hồi sau {llm_time:.2f}s — độ dài câu trả lời: {len(answer)} ký tự")
            print(f"[LLM] Preview: {answer[:200].replace(chr(10), ' ')}...")

        # ── 5. Build response ─────────────────────────────────────
        sources = [
            SourceDocument(
                title=self._source_title(doc.get("metadata", {})),
                content=doc["content"][:500],
                relevance_score=float(doc["score"]),
                metadata=doc.get("metadata", {}),
                url=doc.get("metadata", {}).get("url"),
            )
            for doc in retrieved_docs
        ]

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
        if loai_vb and so_hieu:
            parts.append(f"{loai_vb} {so_hieu}")
        elif loai_vb:
            parts.append(loai_vb)
        if co_quan:
            parts.append(co_quan)
        if tieu_de:
            parts.append(tieu_de)
        if parts:
            return " — ".join(parts)
        # fallback dữ liệu cũ từ docx
        return metadata.get("article_title") or metadata.get("doc_name") or f"VB #{metadata.get('id_vb', '?')}"

    def _format_context(self, documents: List[dict]) -> str:
        context_parts = []
        for i, doc in enumerate(documents, 1):
            meta = doc.get("metadata", {})
            loai_vb = meta.get("loai_vb", "")
            so_hieu = meta.get("so_hieu", "")
            ten_vb  = meta.get("ten_vb", "")
            co_quan = meta.get("co_quan", "")
            ten_chuong_cha = meta.get("ten_chuong_cha", "")
            tieu_de = meta.get("tieu_de", "")

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

            header = f"[Nguồn {i}] " + " | ".join(lines) if lines else f"[Nguồn {i}]"
            context_parts.append(f"{header}\n{doc['content']}")
        return "\n\n---\n\n".join(context_parts)


# Global RAG pipeline instance
rag_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
    return rag_pipeline
