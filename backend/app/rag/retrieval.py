from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import time
import pickle
import re
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

    def similarity_search(self, query: str, k: int = 5, filter_where: dict = None) -> List[Dict]:
        """Search for similar documents, optionally filtered by metadata."""
        filter_info = f" | filter={filter_where}" if filter_where else ""
        print(f"  [CHROMA] similarity_search k={k}{filter_info} | query='{query[:80]}...'")
        
        kwargs = {"query": query, "k": k}
        if filter_where:
            kwargs["filter"] = filter_where

        try:
            results = self.vectorstore.similarity_search_with_relevance_scores(**kwargs)
        except TypeError:
            # Một số phiên bản LangChain dùng 'where' thay vì 'filter'
            kwargs.pop("filter", None)
            if filter_where:
                kwargs["where"] = filter_where
            results = self.vectorstore.similarity_search_with_relevance_scores(**kwargs)
            
        print(f"  [CHROMA] Kết quả trả về: {len(results)} docs")
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


class BM25Index:
    """BM25 keyword search index, persisted to disk as pickle."""

    def __init__(self, index_path: str):
        self.index_path = index_path
        self._bm25 = None
        self._doc_contents: List[str] = []
        self._doc_metadatas: List[Dict] = []

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize Vietnamese text bằng whitespace — đủ để match số luật, tên điều."""
        return re.sub(r'[^\w\s]', ' ', text.lower()).split()

    def build(self, documents: List[Dict]) -> None:
        """Build BM25 index từ danh sách documents.

        documents: list of {"id": str, "content": str, "metadata": dict}
        """
        from rank_bm25 import BM25Okapi
        self._doc_contents = [d["content"] for d in documents]
        self._doc_metadatas = [d.get("metadata", {}) for d in documents]
        tokenized = [self._tokenize(c) for c in self._doc_contents]
        self._bm25 = BM25Okapi(tokenized)
        print(f"[BM25] Index built với {len(documents)} documents.")

    def save(self) -> None:
        """Serialize index ra file pickle."""
        data = {
            "bm25": self._bm25,
            "contents": self._doc_contents,
            "metadatas": self._doc_metadatas,
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(data, f)
        size_mb = os.path.getsize(self.index_path) / 1024 / 1024
        print(f"[BM25] Index saved → '{self.index_path}' ({size_mb:.1f} MB)")

    def load(self) -> bool:
        """Load index từ file pickle. Trả về False nếu file không tồn tại hoặc corrupt."""
        if not os.path.exists(self.index_path):
            return False
        try:
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)
            self._bm25 = data["bm25"]
            self._doc_contents = data["contents"]
            self._doc_metadatas = data["metadatas"]
            print(f"[BM25] Index loaded từ '{self.index_path}' ({len(self._doc_contents)} docs)")
            return True
        except Exception as e:
            print(f"[BM25] Lỗi load index: {e} — fallback về pure vector search")
            return False

    def search(self, query: str, top_k: int) -> List[Dict]:
        """Tìm kiếm BM25. Trả về [] nếu index chưa load hoặc không có kết quả."""
        if self._bm25 is None:
            return []
        tokens = self._tokenize(query)
        scores = self._bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            {
                "content": self._doc_contents[i],
                "metadata": self._doc_metadatas[i],
                "score": float(scores[i]),
            }
            for i in top_indices
            if scores[i] > 0
        ]


class HybridRetriever:
    """Kết hợp vector search và BM25 search bằng Reciprocal Rank Fusion."""

    def __init__(self, vector_store: "ChromaVectorStore", bm25_index: BM25Index):
        self.vector_store = vector_store
        self.bm25_index = bm25_index

    def search(self, query: str, top_k: int, filter_where: dict = None) -> List[Dict]:
        """Hybrid search: vector + BM25, kết hợp bằng RRF."""
        vector_results = self.vector_store.similarity_search(
            query, k=top_k, filter_where=filter_where
        )
        bm25_results = self.bm25_index.search(query, top_k=top_k)

        print(f"  [HYBRID] vector={len(vector_results)} docs | bm25={len(bm25_results)} docs")

        merged = self._rrf_fusion(vector_results, bm25_results, top_k)
        print(f"  [HYBRID] RRF merged → {len(merged)} docs | top scores: {[round(d['score'], 5) for d in merged[:3]]}")
        return merged

    def _rrf_fusion(self, vector_results: List[Dict], bm25_results: List[Dict], top_k: int) -> List[Dict]:
        """Reciprocal Rank Fusion: score(d) = Σ 1/(k + rank(d)) với k=RRF_K."""
        k = settings.RRF_K
        rrf_scores: Dict[str, float] = {}
        docs_by_id: Dict[str, Dict] = {}

        def doc_id(doc: Dict) -> str:
            return doc.get("metadata", {}).get("dieu_mapc") or doc["content"][:50]

        for rank, doc in enumerate(vector_results):
            did = doc_id(doc)
            rrf_scores[did] = rrf_scores.get(did, 0.0) + 1.0 / (k + rank + 1)
            docs_by_id[did] = doc

        for rank, doc in enumerate(bm25_results):
            did = doc_id(doc)
            rrf_scores[did] = rrf_scores.get(did, 0.0) + 1.0 / (k + rank + 1)
            if did not in docs_by_id:
                docs_by_id[did] = doc

        sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
        result = []
        for did in sorted_ids[:top_k]:
            doc = {**docs_by_id[did], "score": rrf_scores[did]}
            result.append(doc)
        return result


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
        self.hybrid_retriever: Optional[HybridRetriever] = self._init_hybrid_retriever()
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

    def _init_hybrid_retriever(self) -> Optional[HybridRetriever]:
        """Khởi tạo HybridRetriever nếu HYBRID_SEARCH_ENABLED và index tồn tại."""
        if not settings.HYBRID_SEARCH_ENABLED:
            print("[HYBRID] Tắt (HYBRID_SEARCH_ENABLED=False) — dùng pure vector search")
            return None
        bm25 = BM25Index(settings.BM25_INDEX_PATH)
        loaded = bm25.load()
        if not loaded:
            print(f"[HYBRID] Index không tồn tại tại '{settings.BM25_INDEX_PATH}' — fallback về pure vector search")
            print("[HYBRID] Chạy: python scripts/build_bm25_index.py để build index")
            return None
        return HybridRetriever(self.vector_store, bm25)

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

    def retrieve(self, query: str, top_k: int = 5, filter_where: dict = None, rerank_query: str = None) -> List[Dict]:
        """Retrieve relevant documents.

        Dùng HybridRetriever nếu available, fallback về pure vector search.
        query: dùng cho search (thường là rewritten query)
        rerank_query: dùng cho CrossEncoder reranking (mặc định = query)
        """
        filter_info = f" (filter: {filter_where})" if filter_where else ""
        candidate_k = top_k * settings.RETRIEVAL_CANDIDATE_MULTIPLIER if self.reranker else top_k

        if self.hybrid_retriever:
            results = self.hybrid_retriever.search(query, top_k=candidate_k, filter_where=filter_where)
        else:
            results = self.vector_store.similarity_search(query, k=candidate_k, filter_where=filter_where)

        if self.reranker:
            effective_rerank_query = rerank_query if rerank_query is not None else query
            results = self.reranker.rerank(effective_rerank_query, results, top_k=top_k)

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
