from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
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
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory="./chroma_db"
        )

    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str] = None):
        """Add documents to vector store"""
        kwargs = {"texts": documents, "metadatas": metadatas}
        if ids:
            kwargs["ids"] = ids
        self.vectorstore.add_texts(**kwargs)
        self.vectorstore.persist()

    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar documents"""
        results = self.vectorstore.similarity_search_with_relevance_scores(query, k=k)
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


class RAGSystem:
    """Retrieval Augmented Generation system"""

    def __init__(self):
        self.vector_store = self._init_vector_store()
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

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant documents"""
        results = self.vector_store.similarity_search(query, k=top_k)
        return [
            r for r in results
            if r["score"] >= settings.SIMILARITY_THRESHOLD
            and r["score"] <= 1.0
        ]

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
