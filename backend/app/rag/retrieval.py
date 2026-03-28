from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from sentence_transformers import CrossEncoder
from app.core.config import settings


class BaseVectorStore(ABC):
    """Abstract base class for vector stores"""

    @abstractmethod
    def add_documents(self, documents: List[str], metadatas: List[Dict]):
        pass

    @abstractmethod
    def similarity_search(self, query: str, k: int) -> List[Dict]:
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        pass

class ChromaVectorStore(BaseVectorStore):
    """Chroma vector store implementation"""

    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL
        )
        chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=chroma_path
        )

    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str] = None):
        """Add documents to vector store"""
        kwargs = {"texts": documents, "metadatas": metadatas}
        if ids:
            kwargs["ids"] = ids
        self.vectorstore.add_texts(**kwargs)
        self.vectorstore.persist()

    def similarity_search(self, query: str, k: int = 5, filter_where: dict = None) -> List[Dict]:
        """Search for similar documents, optionally filtered by metadata."""
        filter_info = f" | filter={filter_where}" if filter_where else ""
        print(f"  [CHROMA] similarity_search k={k}{filter_info} | query='{query[:80]}...'")
        kwargs = {"query": query, "k": k}
        if filter_where:
            kwargs["filter"] = filter_where
        results = self.vectorstore.similarity_search_with_relevance_scores(**kwargs)
        print(f"  [CHROMA] Raw results: {len(results)} — scores: {[round(s, 4) for _, s in results]}")
        return [
            {
                "content": doc.page_content,
                "score": score,
                "metadata": doc.metadata
            }
            for doc, score in results
        ]

    def delete(self, ids: List[str]) -> bool:
        """Delete documents"""
        try:
            self.vectorstore.delete(ids)
            return True
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return False


class Reranker:
    """Cross-encoder reranker to re-score retrieved candidates"""

    def __init__(self, model_name: str):
        print(f"[RERANKER] Đang tải model '{model_name}'...")
        self.model = CrossEncoder(model_name)
        print(f"[RERANKER] Sẵn sàng.")

    def rerank(self, query: str, docs: List[Dict], top_k: int) -> List[Dict]:
        if not docs:
            return docs
        pairs = [(query, doc["content"]) for doc in docs]
        scores = self.model.predict(pairs)
        for doc, score in zip(docs, scores):
            doc["original_score"] = doc["score"]
            doc["score"] = float(score)
        reranked = sorted(docs, key=lambda x: x["score"], reverse=True)
        print(f"  [RERANKER] Reranked {len(docs)} → top {top_k} | scores: {[round(d['score'], 4) for d in reranked[:top_k]]}")
        return reranked[:top_k]


class RAGSystem:
    """Retrieval Augmented Generation system"""

    def __init__(self):
        self.vector_store = self._init_vector_store()
        self.reranker = Reranker(settings.RERANKER_MODEL) if settings.RERANKER_ENABLED else None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )

    def _init_vector_store(self) -> BaseVectorStore:
        """Initialize vector store"""
        if settings.VECTOR_STORE_TYPE == "chroma":
            return ChromaVectorStore()
        else:
            raise ValueError(f"Unknown vector store type: {settings.VECTOR_STORE_TYPE}")

    def add_document(self, content: str, metadata: Dict[str, Any] = None):
        """Add document to RAG system"""
        if metadata is None:
            metadata = {}

        chunks = self.text_splitter.split_text(content)
        metadatas = [
            {**metadata, "chunk_index": i, "timestamp": time.time()}
            for i in range(len(chunks))
        ]

        self.vector_store.add_documents(chunks, metadatas)

    def retrieve(self, query: str, top_k: int = 5, filter_where: dict = None) -> List[Dict]:
        """Retrieve relevant documents, optionally filtered by metadata."""
        filter_info = f" (filter: {filter_where})" if filter_where else ""
        candidate_k = top_k * settings.RETRIEVAL_CANDIDATE_MULTIPLIER if self.reranker else top_k
        results = self.vector_store.similarity_search(query, k=candidate_k, filter_where=filter_where)
        if self.reranker:
            results = self.reranker.rerank(query, results, top_k=top_k)
        print(f"  [RETRIEVAL] Lấy top {len(results)} docs{filter_info}")
        return results

    def add_documents_batch(self, documents: List[Dict]):
        """Add multiple documents"""
        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            self.add_document(content, metadata)

    def add_documents_direct(self, rows: List[Dict]):
        """Add pre-chunked rows directly, no text splitting.

        Each row: {"id": str, "content": str, "metadata": dict}
        """
        texts = [r["content"] for r in rows]
        metadatas = [r.get("metadata", {}) for r in rows]
        ids = [r["id"] for r in rows]
        self.vector_store.add_documents(texts, metadatas, ids=ids)


# Global RAG instance
rag_system = None


def get_rag_system() -> RAGSystem:
    """Get or create RAG system instance"""
    global rag_system
    if rag_system is None:
        rag_system = RAGSystem()
    return rag_system
