import time
from typing import List, Optional
from app.models.schemas import QueryRequest, QueryResponse, SourceDocument
from app.rag.retrieval import get_rag_system
from app.rag.llm import get_llm_manager

class RAGPipeline:
    """Main RAG pipeline that combines retrieval and generation"""

    def __init__(self):
        self.rag_system = get_rag_system()
        self.llm_manager = get_llm_manager()

    def process_query(self, request: QueryRequest) -> QueryResponse:
        """Process a query through the RAG pipeline"""
        start_time = time.time()

        # Retrieve relevant documents
        retrieved_docs = self.rag_system.retrieve(
            request.query,
            top_k=request.top_k
        )

        # Format context from retrieved documents
        context = self._format_context(retrieved_docs)

        # Generate answer using LLM
        if self.llm_manager:
            answer = self.llm_manager.generate_answer(
                request.query,
                context
            )
        else:
            answer = "LLM is not configured. Please provide context-based answer."

        # Convert retrieved documents to SourceDocument objects
        sources = [
            SourceDocument(
                title=self._source_title(doc.get("metadata", {})),
                content=doc["content"][:500],
                relevance_score=float(doc["score"]),
                metadata=doc.get("metadata", {}),
                url=doc.get("metadata", {}).get("url")
            )
            for doc in retrieved_docs
        ]

        processing_time = time.time() - start_time

        return QueryResponse(
            query=request.query,
            answer=answer,
            sources=sources,
            processing_time=processing_time,
            model_used=self.llm_manager.llm.__class__.__name__ if self.llm_manager else None
        )

    def _source_title(self, metadata: dict) -> str:
        """Tạo tiêu đề nguồn từ metadata."""
        id_vb = metadata.get("id_vb")
        if id_vb:
            return f"Văn bản #{id_vb}"
        # Fallback cho dữ liệu cũ (ingest từ docx)
        return metadata.get("article_title") or metadata.get("doc_name") or "Unknown"

    def _format_context(self, documents: List[dict]) -> str:
        """Format retrieved documents as context string"""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = self._source_title(doc.get("metadata", {}))
            content = doc["content"]
            context_parts.append(f"[{source}]\n{content}")
        return "\n\n---\n\n".join(context_parts)


# Global RAG pipeline instance
rag_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create RAG pipeline instance"""
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
    return rag_pipeline
