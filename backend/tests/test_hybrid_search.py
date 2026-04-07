"""
Unit tests cho Hybrid Search: BM25Index, HybridRetriever (RRF fusion),
và tích hợp vào RAGSystem.
"""
import os
import pytest
from unittest.mock import MagicMock, patch


# ── Fixtures dùng chung ───────────────────────────────────────────────────────

DOCS_SMALL = [
    {
        "id": "HNGD.1.1",
        "content": "Điều kiện kết hôn theo luật hôn nhân gia đình năm 2014",
        "metadata": {"dieu_mapc": "HNGD.1.1", "chu_de": "Hôn nhân và Gia đình"},
    },
    {
        "id": "HNGD.1.2",
        "content": "Thủ tục ly hôn và chia tài sản sau khi ly hôn",
        "metadata": {"dieu_mapc": "HNGD.1.2", "chu_de": "Hôn nhân và Gia đình"},
    },
    {
        "id": "HS.1.1",
        "content": "Tội giết người theo bộ luật hình sự 2015",
        "metadata": {"dieu_mapc": "HS.1.1", "chu_de": "Hình sự"},
    },
]


# ── BM25Index tests ───────────────────────────────────────────────────────────

class TestBM25Index:
    def test_load_returns_false_when_file_not_exist(self, tmp_path):
        from app.rag.retrieval import BM25Index
        bm25 = BM25Index(str(tmp_path / "nonexistent.pkl"))
        assert bm25.load() is False

    def test_load_returns_true_after_save(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)
        bm25.save()

        bm25_loaded = BM25Index(path)
        assert bm25_loaded.load() is True

    def test_save_creates_file(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)
        bm25.save()
        assert os.path.exists(path)

    def test_search_returns_matching_doc(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)

        results = bm25.search("kết hôn", top_k=3)
        assert len(results) >= 1
        assert "kết hôn" in results[0]["content"] or "hôn nhân" in results[0]["content"]

    def test_search_returns_empty_on_no_match(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)

        results = bm25.search("xyzabc123notfound", top_k=3)
        assert results == []

    def test_search_result_has_required_keys(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)

        results = bm25.search("hôn nhân", top_k=3)
        assert len(results) > 0
        for r in results:
            assert "content" in r
            assert "metadata" in r
            assert "score" in r

    def test_search_scores_are_positive(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)

        results = bm25.search("hình sự", top_k=3)
        for r in results:
            assert r["score"] > 0

    def test_search_returns_at_most_top_k(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)

        results = bm25.search("luật", top_k=1)
        assert len(results) <= 1

    def test_load_restores_search_capability(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "index.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)
        bm25.save()

        bm25_new = BM25Index(path)
        bm25_new.load()
        results = bm25_new.search("kết hôn", top_k=3)
        assert len(results) >= 1

    def test_load_returns_false_on_corrupt_file(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "corrupt.pkl")
        with open(path, "wb") as f:
            f.write(b"this is not a valid pickle file")

        bm25 = BM25Index(path)
        assert bm25.load() is False


# ── HybridRetriever / RRF tests ───────────────────────────────────────────────

def _make_vector_results():
    return [
        {"content": "doc A về hôn nhân", "metadata": {"dieu_mapc": "A"}, "score": 0.9},
        {"content": "doc B về ly hôn", "metadata": {"dieu_mapc": "B"}, "score": 0.7},
        {"content": "doc C về hình sự", "metadata": {"dieu_mapc": "C"}, "score": 0.5},
    ]

def _make_bm25_results():
    return [
        {"content": "doc B về ly hôn", "metadata": {"dieu_mapc": "B"}, "score": 12.0},
        {"content": "doc D về dân sự", "metadata": {"dieu_mapc": "D"}, "score": 8.0},
        {"content": "doc A về hôn nhân", "metadata": {"dieu_mapc": "A"}, "score": 5.0},
    ]


class TestHybridRetriever:
    @pytest.fixture
    def mock_vector_store(self):
        vs = MagicMock()
        vs.similarity_search.return_value = _make_vector_results()
        return vs

    @pytest.fixture
    def mock_bm25(self, tmp_path):
        from app.rag.retrieval import BM25Index
        bm25 = BM25Index(str(tmp_path / "idx.pkl"))
        bm25.build(DOCS_SMALL)
        return bm25

    def test_doc_in_both_sources_scores_higher(self, mock_vector_store):
        from app.rag.retrieval import HybridRetriever, BM25Index
        bm25 = MagicMock(spec=BM25Index)
        bm25.search.return_value = _make_bm25_results()

        with patch("app.rag.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_CANDIDATE_MULTIPLIER = 3
            mock_settings.RRF_K = 60
            retriever = HybridRetriever(mock_vector_store, bm25)
            results = retriever.search("hôn nhân", top_k=4)

        scores = {r["metadata"]["dieu_mapc"]: r["score"] for r in results}
        assert scores.get("A", 0) > scores.get("D", 0)

    def test_result_count_limited_to_top_k(self, mock_vector_store):
        from app.rag.retrieval import HybridRetriever, BM25Index
        bm25 = MagicMock(spec=BM25Index)
        bm25.search.return_value = _make_bm25_results()

        with patch("app.rag.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_CANDIDATE_MULTIPLIER = 3
            mock_settings.RRF_K = 60
            retriever = HybridRetriever(mock_vector_store, bm25)
            results = retriever.search("test", top_k=2)

        assert len(results) == 2

    def test_fallback_to_vector_when_bm25_empty(self, mock_vector_store):
        from app.rag.retrieval import HybridRetriever, BM25Index
        bm25 = MagicMock(spec=BM25Index)
        bm25.search.return_value = []

        with patch("app.rag.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_CANDIDATE_MULTIPLIER = 3
            mock_settings.RRF_K = 60
            retriever = HybridRetriever(mock_vector_store, bm25)
            results = retriever.search("hôn nhân", top_k=3)

        assert len(results) > 0
        mapc_set = {r["metadata"]["dieu_mapc"] for r in results}
        assert mapc_set <= {"A", "B", "C"}

    def test_fallback_to_bm25_when_vector_empty(self):
        from app.rag.retrieval import HybridRetriever, BM25Index
        vs = MagicMock()
        vs.similarity_search.return_value = []
        bm25 = MagicMock(spec=BM25Index)
        bm25.search.return_value = _make_bm25_results()

        with patch("app.rag.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_CANDIDATE_MULTIPLIER = 3
            mock_settings.RRF_K = 60
            retriever = HybridRetriever(vs, bm25)
            results = retriever.search("ly hôn", top_k=3)

        assert len(results) > 0

    def test_result_has_rrf_score(self, mock_vector_store):
        from app.rag.retrieval import HybridRetriever, BM25Index
        bm25 = MagicMock(spec=BM25Index)
        bm25.search.return_value = _make_bm25_results()

        with patch("app.rag.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_CANDIDATE_MULTIPLIER = 3
            mock_settings.RRF_K = 60
            retriever = HybridRetriever(mock_vector_store, bm25)
            results = retriever.search("hôn nhân", top_k=4)

        for r in results:
            assert r["score"] > 0

    def test_filter_passed_to_vector_store(self, mock_vector_store):
        from app.rag.retrieval import HybridRetriever, BM25Index
        bm25 = MagicMock(spec=BM25Index)
        bm25.search.return_value = []

        with patch("app.rag.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_CANDIDATE_MULTIPLIER = 3
            mock_settings.RRF_K = 60
            retriever = HybridRetriever(mock_vector_store, bm25)
            retriever.search("query", top_k=5, filter_where={"chu_de_id": "3"})

        call_kwargs = mock_vector_store.similarity_search.call_args[1]
        assert call_kwargs.get("filter_where") == {"chu_de_id": "3"}


# ── RAGSystem hybrid integration tests ───────────────────────────────────────

class TestRAGSystemHybrid:
    @pytest.fixture
    def mock_chroma(self):
        vs = MagicMock()
        vs.similarity_search.return_value = [
            {"content": "doc vector", "metadata": {"dieu_mapc": "V1"}, "score": 0.8}
        ]
        return vs

    @pytest.fixture
    def mock_bm25_loaded(self, tmp_path):
        from app.rag.retrieval import BM25Index
        path = str(tmp_path / "idx.pkl")
        bm25 = BM25Index(path)
        bm25.build(DOCS_SMALL)
        bm25.save()
        return path

    def test_hybrid_retriever_used_when_enabled(self, mock_chroma, mock_bm25_loaded):
        from app.rag.retrieval import RAGSystem, HybridRetriever

        with patch("app.rag.retrieval.ChromaVectorStore", return_value=mock_chroma), \
             patch("app.rag.retrieval.Reranker"), \
             patch("app.rag.retrieval.settings") as ms:
            ms.RERANKER_ENABLED = False
            ms.HYBRID_SEARCH_ENABLED = True
            ms.BM25_INDEX_PATH = mock_bm25_loaded
            ms.RETRIEVAL_CANDIDATE_MULTIPLIER = 1
            ms.VECTOR_STORE_TYPE = "chroma"
            ms.RRF_K = 60
            ms.CHUNK_SIZE = 1024
            ms.CHUNK_OVERLAP = 256

            rag = RAGSystem()
            assert isinstance(rag.hybrid_retriever, HybridRetriever)

    def test_retrieve_uses_hybrid_when_available(self, mock_chroma, mock_bm25_loaded):
        from app.rag.retrieval import RAGSystem

        with patch("app.rag.retrieval.ChromaVectorStore", return_value=mock_chroma), \
             patch("app.rag.retrieval.Reranker"), \
             patch("app.rag.retrieval.settings") as ms:
            ms.RERANKER_ENABLED = False
            ms.HYBRID_SEARCH_ENABLED = True
            ms.BM25_INDEX_PATH = mock_bm25_loaded
            ms.RETRIEVAL_CANDIDATE_MULTIPLIER = 1
            ms.VECTOR_STORE_TYPE = "chroma"
            ms.RRF_K = 60
            ms.CHUNK_SIZE = 1024
            ms.CHUNK_OVERLAP = 256

            rag = RAGSystem()
            mock_hybrid = MagicMock()
            mock_hybrid.search.return_value = [
                {"content": "hybrid doc", "metadata": {"dieu_mapc": "H1"}, "score": 0.9}
            ]
            rag.hybrid_retriever = mock_hybrid

            results = rag.retrieve("câu hỏi pháp lý", top_k=3)
            mock_hybrid.search.assert_called_once()
            assert results[0]["content"] == "hybrid doc"

    def test_fallback_to_vector_when_hybrid_disabled(self, mock_chroma):
        from app.rag.retrieval import RAGSystem

        with patch("app.rag.retrieval.ChromaVectorStore", return_value=mock_chroma), \
             patch("app.rag.retrieval.Reranker"), \
             patch("app.rag.retrieval.settings") as ms:
            ms.RERANKER_ENABLED = False
            ms.HYBRID_SEARCH_ENABLED = False
            ms.RETRIEVAL_CANDIDATE_MULTIPLIER = 1
            ms.VECTOR_STORE_TYPE = "chroma"
            ms.CHUNK_SIZE = 1024
            ms.CHUNK_OVERLAP = 256

            rag = RAGSystem()
            assert rag.hybrid_retriever is None
            rag.retrieve("câu hỏi", top_k=3)
            mock_chroma.similarity_search.assert_called_once()

    def test_fallback_to_vector_when_index_missing(self, mock_chroma, tmp_path):
        from app.rag.retrieval import RAGSystem

        with patch("app.rag.retrieval.ChromaVectorStore", return_value=mock_chroma), \
             patch("app.rag.retrieval.Reranker"), \
             patch("app.rag.retrieval.settings") as ms:
            ms.RERANKER_ENABLED = False
            ms.HYBRID_SEARCH_ENABLED = True
            ms.BM25_INDEX_PATH = str(tmp_path / "nonexistent.pkl")
            ms.RETRIEVAL_CANDIDATE_MULTIPLIER = 1
            ms.VECTOR_STORE_TYPE = "chroma"
            ms.CHUNK_SIZE = 1024
            ms.CHUNK_OVERLAP = 256

            rag = RAGSystem()
            assert rag.hybrid_retriever is None
