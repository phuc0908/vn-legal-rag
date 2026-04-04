"""
Unit tests cho app.rag.pipeline — RAGPipeline
  - _format_context: format documents thành context string
  - _source_title: tạo tiêu đề nguồn từ metadata
  - process_query: orchestration đầy đủ (routing, retrieval, generation)
"""
import pytest
from unittest.mock import MagicMock, patch
from app.models.schemas import QueryRequest, QueryResponse


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_DOC = {
    "content": "Nội dung điều luật mẫu về hôn nhân gia đình.",
    "score": 0.85,
    "metadata": {
        "chu_de": "Hôn nhân và Gia đình",
        "de_muc": "Luật Hôn nhân và Gia đình 2014",
        "loai_vb": "Luật",
        "so_hieu": "52/2014/QH13",
        "ten_vb": "Luật Hôn nhân và Gia đình",
        "co_quan": "Quốc hội",
        "tieu_de": "Điều 8. Điều kiện kết hôn",
    },
}

SAMPLE_DOC_MINIMAL = {
    "content": "Nội dung tối giản.",
    "score": 0.60,
    "metadata": {},
}


@pytest.fixture
def mock_rag_system():
    system = MagicMock()
    system.retrieve.return_value = []
    return system


@pytest.fixture
def mock_llm_manager():
    mgr = MagicMock()
    mgr.llm.__class__.__name__ = "GroqLLM"
    mgr.rewrite_query.side_effect = lambda q: q  # passthrough mặc định
    mgr.generate_answer.return_value = "đây là câu trả lời mẫu"
    return mgr


@pytest.fixture
def pipeline(mock_rag_system, mock_llm_manager):
    """RAGPipeline không có dependency thật — tất cả đã mock."""
    with patch("app.rag.pipeline.get_rag_system", return_value=mock_rag_system), \
         patch("app.rag.pipeline.get_llm_manager", return_value=mock_llm_manager), \
         patch("app.rag.pipeline.query_all", return_value=[]), \
         patch("app.rag.pipeline.settings") as mock_settings:
        mock_settings.TOPIC_ROUTER_ENABLED = False
        from app.rag.pipeline import RAGPipeline
        p = RAGPipeline()
    p.rag_system = mock_rag_system
    p.llm_manager = mock_llm_manager
    p.topic_router = None
    return p


def _req(query="hỏi về luật hôn nhân", chu_de_id=None, top_k=5):
    return QueryRequest(query=query, chu_de_id=chu_de_id, top_k=top_k)


# ── _format_context ───────────────────────────────────────────────────────────

class TestFormatContext:
    def test_empty_list_returns_empty_string(self, pipeline):
        """
        Ngữ cảnh: Không có document nào được retrieve.
        Kỳ vọng: _format_context([]) trả về ''.
        Lý do pass: Vòng lặp không chạy → context_parts = [] → ''.join([]) = ''.
        """
        assert pipeline._format_context([]) == ""

    def test_single_doc_has_source_header(self, pipeline):
        """
        Ngữ cảnh: 1 document được retrieve.
        Kỳ vọng: Output chứa '[Nguồn 1]' làm header.
        Lý do pass: _format_context đánh số từng nguồn bắt đầu từ 1.
        """
        result = pipeline._format_context([SAMPLE_DOC])
        assert "[Nguồn 1]" in result

    def test_single_doc_includes_chu_de(self, pipeline):
        """
        Ngữ cảnh: Document có metadata chu_de='Hôn nhân và Gia đình'.
        Kỳ vọng: Context string chứa tên chủ đề để LLM biết ngữ cảnh pháp lý.
        Lý do pass: `if chu_de: lines.append(f'Chủ đề: {chu_de}')`.
        """
        result = pipeline._format_context([SAMPLE_DOC])
        assert "Hôn nhân và Gia đình" in result

    def test_single_doc_includes_content(self, pipeline):
        """
        Ngữ cảnh: Document có content 'Nội dung điều luật mẫu...'.
        Kỳ vọng: Nội dung document phải có trong context gửi lên LLM.
        Lý do pass: content = doc['content'][:1500] được append vào context_parts.
        """
        result = pipeline._format_context([SAMPLE_DOC])
        assert "Nội dung điều luật mẫu" in result

    def test_single_doc_includes_ten_vb(self, pipeline):
        """
        Ngữ cảnh: Document có metadata ten_vb='Luật Hôn nhân và Gia đình'.
        Kỳ vọng: Tên văn bản pháp luật xuất hiện trong context.
        Lý do pass: `if ten_vb: lines.append(f'Tên: {ten_vb}')`.
        """
        result = pipeline._format_context([SAMPLE_DOC])
        assert "Luật Hôn nhân và Gia đình" in result

    def test_multiple_docs_have_numbered_headers(self, pipeline):
        """
        Ngữ cảnh: 2 documents được retrieve.
        Kỳ vọng: Context có cả '[Nguồn 1]' và '[Nguồn 2]'.
        Lý do pass: enumerate(documents, 1) đánh số tự động từ 1.
        """
        result = pipeline._format_context([SAMPLE_DOC, SAMPLE_DOC_MINIMAL])
        assert "[Nguồn 1]" in result
        assert "[Nguồn 2]" in result

    def test_multiple_docs_separated_by_divider(self, pipeline):
        """
        Ngữ cảnh: 2 documents được format.
        Kỳ vọng: Giữa các nguồn có dấu phân cách '---' để LLM phân biệt rõ.
        Lý do pass: '\n\n---\n\n'.join(context_parts) chèn divider giữa các nguồn.
        """
        result = pipeline._format_context([SAMPLE_DOC, SAMPLE_DOC_MINIMAL])
        assert "---" in result

    def test_content_truncated_to_1500_chars(self, pipeline):
        """
        Ngữ cảnh: Document có content dài 3000 ký tự.
        Kỳ vọng: Chỉ lấy tối đa 1500 ký tự để tránh context quá dài → timeout LLM.
        Lý do pass: content = doc['content'][:1500] — cắt cứng tại 1500.
        """
        long_doc = {**SAMPLE_DOC, "content": "a" * 3000}
        result = pipeline._format_context([long_doc])
        assert "a" * 1501 not in result
        assert "a" * 1500 in result

    def test_total_context_truncated_to_4000_chars(self, pipeline):
        """
        Ngữ cảnh: 10 documents, mỗi cái 1500 ký tự → tổng ~15000 ký tự.
        Kỳ vọng: Tổng context bị cắt tại 4000 ký tự để tránh vượt token limit LLM.
        Lý do pass: return context[:4000] — cắt toàn bộ context string ở cuối.
        """
        big_docs = [{**SAMPLE_DOC, "content": "x" * 1500} for _ in range(10)]
        result = pipeline._format_context(big_docs)
        assert len(result) <= 4000

    def test_minimal_metadata_still_renders(self, pipeline):
        """
        Ngữ cảnh: Document với metadata rỗng {} (dữ liệu thiếu).
        Kỳ vọng: Vẫn render được '[Nguồn 1]' và content, không crash.
        Lý do pass: Tất cả `if metadata.get(key)` đều False → bỏ qua, chỉ render header + content.
        """
        result = pipeline._format_context([SAMPLE_DOC_MINIMAL])
        assert "[Nguồn 1]" in result
        assert "Nội dung tối giản" in result


# ── _source_title ─────────────────────────────────────────────────────────────

class TestSourceTitle:
    def test_loai_vb_and_so_hieu_combined(self, pipeline):
        """
        Ngữ cảnh: Metadata có loai_vb='Luật' và so_hieu='52/2014/QH13'.
        Kỳ vọng: Title bắt đầu bằng 'Luật 52/2014/QH13'.
        Lý do pass: `if loai_vb and so_hieu: parts.append(f'{loai_vb} {so_hieu}')`.
        """
        meta = {"loai_vb": "Luật", "so_hieu": "52/2014/QH13"}
        title = pipeline._source_title(meta)
        assert "Luật 52/2014/QH13" in title

    def test_co_quan_included(self, pipeline):
        """
        Ngữ cảnh: Metadata có co_quan='Quốc hội'.
        Kỳ vọng: Cơ quan ban hành xuất hiện trong title để người dùng nhận ra nguồn.
        Lý do pass: `if co_quan: parts.append(co_quan)`.
        """
        meta = {"loai_vb": "Luật", "so_hieu": "52/2014/QH13", "co_quan": "Quốc hội"}
        title = pipeline._source_title(meta)
        assert "Quốc hội" in title

    def test_tieu_de_included(self, pipeline):
        """
        Ngữ cảnh: Metadata có tieu_de='Điều 8. Điều kiện kết hôn'.
        Kỳ vọng: Tên điều luật xuất hiện trong title.
        Lý do pass: `if tieu_de: parts.append(tieu_de)`.
        """
        meta = {"tieu_de": "Điều 8. Điều kiện kết hôn"}
        title = pipeline._source_title(meta)
        assert "Điều 8" in title

    def test_loai_vb_without_so_hieu(self, pipeline):
        """
        Ngữ cảnh: Metadata có loai_vb='Nghị định' nhưng so_hieu=''.
        Kỳ vọng: Title vẫn chứa 'Nghị định' dù thiếu số hiệu.
        Lý do pass: `elif loai_vb: parts.append(loai_vb)` xử lý trường hợp thiếu so_hieu.
        """
        meta = {"loai_vb": "Nghị định", "so_hieu": ""}
        title = pipeline._source_title(meta)
        assert "Nghị định" in title

    def test_fallback_to_article_title(self, pipeline):
        """
        Ngữ cảnh: Metadata không có loai_vb/so_hieu, chỉ có article_title (dữ liệu docx cũ).
        Kỳ vọng: Title = article_title thay vì chuỗi rỗng.
        Lý do pass: fallback `return metadata.get('article_title') or ...`.
        """
        assert pipeline._source_title({"article_title": "Điều 12"}) == "Điều 12"

    def test_fallback_to_doc_name(self, pipeline):
        """
        Ngữ cảnh: Metadata chỉ có doc_name (dữ liệu docx cũ, không có article_title).
        Kỳ vọng: Title = doc_name.
        Lý do pass: fallback chain `article_title or doc_name or f'VB #{id_vb}'`.
        """
        assert pipeline._source_title({"doc_name": "BLDS 2015"}) == "BLDS 2015"

    def test_fallback_to_id_vb(self, pipeline):
        """
        Ngữ cảnh: Metadata chỉ có id_vb='42', không có tên gì cả.
        Kỳ vọng: Title = 'VB #42' — luôn có thứ gì đó để hiển thị.
        Lý do pass: fallback cuối `f'VB #{metadata.get('id_vb', '?')}'`.
        """
        assert pipeline._source_title({"id_vb": "42"}) == "VB #42"

    def test_empty_metadata_uses_question_mark(self, pipeline):
        """
        Ngữ cảnh: Metadata hoàn toàn rỗng {}.
        Kỳ vọng: Title = 'VB #?' — không crash, không trả về chuỗi rỗng.
        Lý do pass: id_vb không có → metadata.get('id_vb', '?') = '?' → 'VB #?'.
        """
        assert pipeline._source_title({}) == "VB #?"

    def test_parts_joined_with_em_dash(self, pipeline):
        """
        Ngữ cảnh: Metadata có nhiều phần (loai_vb + co_quan).
        Kỳ vọng: Các phần được nối bằng ' — ' (em dash) cho đẹp UI.
        Lý do pass: `return ' — '.join(parts)`.
        """
        meta = {"loai_vb": "Luật", "so_hieu": "1/2020", "co_quan": "CP"}
        title = pipeline._source_title(meta)
        assert " — " in title


# ── process_query: kết quả cơ bản ────────────────────────────────────────────

class TestProcessQuery:
    def test_returns_query_response_type(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: process_query() được gọi với query hợp lệ.
        Kỳ vọng: Kết quả là instance của QueryResponse (Pydantic model).
        Lý do pass: Pipeline build và return QueryResponse(...) ở bước cuối.
        """
        mock_rag_system.retrieve.return_value = [SAMPLE_DOC]
        response = pipeline.process_query(_req())
        assert isinstance(response, QueryResponse)

    def test_response_contains_original_query(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: User hỏi 'quyền ly hôn?'.
        Kỳ vọng: response.query == 'quyền ly hôn?' — giữ nguyên query gốc (không phải query đã rewrite).
        Lý do pass: QueryResponse(query=request.query, ...) dùng query gốc, không dùng search_query.
        """
        mock_rag_system.retrieve.return_value = []
        response = pipeline.process_query(_req("quyền ly hôn?"))
        assert response.query == "quyền ly hôn?"

    def test_response_contains_answer(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: LLM manager mock trả về 'đây là câu trả lời mẫu'.
        Kỳ vọng: response.answer == 'đây là câu trả lời mẫu'.
        Lý do pass: answer = self.llm_manager.generate_answer(...) → gán vào QueryResponse.
        """
        mock_rag_system.retrieve.return_value = [SAMPLE_DOC]
        response = pipeline.process_query(_req())
        assert response.answer == "đây là câu trả lời mẫu"

    def test_sources_built_from_retrieved_docs(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: retrieve() trả về 2 documents.
        Kỳ vọng: response.sources có đúng 2 SourceDocument.
        Lý do pass: sources = [SourceDocument(...) for doc in retrieved_docs].
        """
        mock_rag_system.retrieve.return_value = [SAMPLE_DOC, SAMPLE_DOC]
        response = pipeline.process_query(_req())
        assert len(response.sources) == 2

    def test_source_relevance_score_matches_doc_score(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: SAMPLE_DOC có score=0.85.
        Kỳ vọng: sources[0].relevance_score == 0.85.
        Lý do pass: SourceDocument(relevance_score=float(doc['score']), ...).
        """
        mock_rag_system.retrieve.return_value = [SAMPLE_DOC]
        response = pipeline.process_query(_req())
        assert response.sources[0].relevance_score == pytest.approx(0.85)

    def test_processing_time_is_positive(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: Pipeline chạy với tất cả mock (rất nhanh).
        Kỳ vọng: processing_time >= 0 (Windows time resolution ~15ms, mock có thể chạy < 1 tick).
        Lý do pass: total_time = time.time() - start_time >= 0 luôn đúng.
        """
        mock_rag_system.retrieve.return_value = []
        response = pipeline.process_query(_req())
        assert response.processing_time >= 0

    def test_model_used_is_populated(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: llm_manager.llm.__class__.__name__ = 'GroqLLM'.
        Kỳ vọng: response.model_used không phải None.
        Lý do pass: model_used = self.llm_manager.llm.__class__.__name__ if self.llm_manager else None.
        """
        mock_rag_system.retrieve.return_value = []
        response = pipeline.process_query(_req())
        assert response.model_used is not None

    def test_query_rewriting_called(self, pipeline, mock_rag_system, mock_llm_manager):
        """
        Ngữ cảnh: Pipeline nhận query 'câu hỏi gốc'.
        Kỳ vọng: llm_manager.rewrite_query() được gọi với đúng query gốc.
        Lý do pass: Bước 1 của pipeline: search_query = self.llm_manager.rewrite_query(request.query).
        """
        mock_rag_system.retrieve.return_value = []
        pipeline.process_query(_req("câu hỏi gốc"))
        mock_llm_manager.rewrite_query.assert_called_once_with("câu hỏi gốc")

    def test_rewritten_query_used_for_retrieval(self, pipeline, mock_rag_system, mock_llm_manager):
        """
        Ngữ cảnh: rewrite_query() trả về 'truy vấn pháp lý chuẩn'.
        Kỳ vọng: retrieve() được gọi với query đã rewrite (không phải query gốc).
        Lý do pass: Sau bước rewrite, search_query = rewritten → retrieve(search_query, ...).
        Ghi chú: side_effect phải clear để return_value có hiệu lực.
        """
        mock_llm_manager.rewrite_query.side_effect = None
        mock_llm_manager.rewrite_query.return_value = "truy vấn pháp lý chuẩn"
        mock_rag_system.retrieve.return_value = []
        pipeline.process_query(_req())
        retrieve_args = mock_rag_system.retrieve.call_args
        assert retrieve_args[0][0] == "truy vấn pháp lý chuẩn"


# ── process_query: topic routing ─────────────────────────────────────────────

class TestProcessQueryRouting:
    def test_router_called_when_no_chu_de_id(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: User không chọn chủ đề (chu_de_id=None), pipeline có topic_router.
        Kỳ vọng: topic_router.route() được gọi để tự động phân loại query.
        Lý do pass: `if not chu_de_id and self.topic_router:` → gọi router.
        """
        mock_router = MagicMock()
        mock_router.route.return_value = "1"
        pipeline.topic_router = mock_router
        mock_rag_system.retrieve.return_value = []

        pipeline.process_query(_req(chu_de_id=None))
        mock_router.route.assert_called_once()

    def test_router_skipped_when_manual_chu_de_id_provided(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: User tự chọn chủ đề chu_de_id='1'.
        Kỳ vọng: topic_router.route() KHÔNG được gọi — user selection takes priority.
        Lý do pass: `chu_de_id = request.chu_de_id` → truthy → skip router.
        """
        mock_router = MagicMock()
        pipeline.topic_router = mock_router
        mock_rag_system.retrieve.return_value = []

        pipeline.process_query(_req(chu_de_id="1"))
        mock_router.route.assert_not_called()

    def test_routed_chu_de_id_applied_as_filter(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: Router phát hiện query thuộc chủ đề ID=3.
        Kỳ vọng: ChromaDB retrieve() được gọi với filter_where={'chu_de_id': '3'}.
        Lý do pass: `filter_where = {'chu_de_id': str(chu_de_id)} if chu_de_id else None`.
        """
        mock_router = MagicMock()
        mock_router.route.return_value = "3"
        pipeline.topic_router = mock_router
        mock_rag_system.retrieve.return_value = []

        pipeline.process_query(_req(chu_de_id=None))

        filter_used = mock_rag_system.retrieve.call_args_list[0][1].get("filter_where")
        assert filter_used == {"chu_de_id": "3"}

    def test_manual_chu_de_id_applied_as_filter(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: User chọn thủ công chu_de_id='5'.
        Kỳ vọng: retrieve() được filter theo đúng chu_de_id đó.
        Lý do pass: `chu_de_id = request.chu_de_id` → `filter_where = {'chu_de_id': '5'}`.
        """
        mock_rag_system.retrieve.return_value = []
        pipeline.process_query(_req(chu_de_id="5"))

        filter_used = mock_rag_system.retrieve.call_args_list[0][1].get("filter_where")
        assert filter_used == {"chu_de_id": "5"}

    def test_no_filter_when_router_returns_none(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: Router không khớp chủ đề nào → trả về None.
        Kỳ vọng: retrieve() được gọi KHÔNG có filter → tìm toàn bộ corpus.
        Lý do pass: `if chu_de_id` → False (None) → filter_where = None.
        """
        mock_router = MagicMock()
        mock_router.route.return_value = None
        pipeline.topic_router = mock_router
        mock_rag_system.retrieve.return_value = []

        pipeline.process_query(_req(chu_de_id=None))

        filter_used = mock_rag_system.retrieve.call_args_list[0][1].get("filter_where")
        assert filter_used is None


# ── process_query: fallback retry ────────────────────────────────────────────

class TestProcessQueryFallback:
    def test_fallback_when_manual_topic_returns_no_results(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: User chọn 'Hình sự' nhưng hỏi về Y tế → lần 1 retrieve = [].
        Kỳ vọng: Pipeline tự động retry lần 2 không có filter để tìm toàn corpus.
        Lý do pass: `if not retrieved_docs and request.chu_de_id:` → retry.
        """
        mock_rag_system.retrieve.side_effect = [[], [SAMPLE_DOC]]
        pipeline.process_query(_req(chu_de_id="1"))
        assert mock_rag_system.retrieve.call_count == 2

    def test_fallback_second_call_has_no_filter(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: Fallback retry sau khi filter không tìm được gì.
        Kỳ vọng: Lần gọi retrieve thứ 2 phải có filter_where=None (tìm toàn bộ).
        Lý do pass: Retry call: `self.rag_system.retrieve(search_query, ..., filter_where=None)`.
        """
        mock_rag_system.retrieve.side_effect = [[], [SAMPLE_DOC]]
        pipeline.process_query(_req(chu_de_id="1"))

        second_call_filter = mock_rag_system.retrieve.call_args_list[1][1].get("filter_where")
        assert second_call_filter is None

    def test_fallback_result_used_in_response(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: Fallback retry tìm được 1 document.
        Kỳ vọng: response.sources có 1 source từ fallback result.
        Lý do pass: retrieved_docs được gán lại từ retry call → dùng để build sources.
        """
        mock_rag_system.retrieve.side_effect = [[], [SAMPLE_DOC]]
        response = pipeline.process_query(_req(chu_de_id="1"))
        assert len(response.sources) == 1

    def test_no_fallback_when_no_manual_chu_de_id(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: Router tự phát hiện topic, retrieve → 0 kết quả.
        Kỳ vọng: KHÔNG retry — router đã mở rộng scope đủ rồi, retry vô nghĩa.
        Lý do pass: Fallback chỉ trigger khi `request.chu_de_id` có giá trị (user chọn thủ công).
        """
        mock_router = MagicMock()
        mock_router.route.return_value = "1"
        pipeline.topic_router = mock_router
        mock_rag_system.retrieve.return_value = []

        pipeline.process_query(_req(chu_de_id=None))
        assert mock_rag_system.retrieve.call_count == 1

    def test_no_fallback_when_manual_topic_has_results(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: User chọn topic, retrieve tìm được kết quả ngay lần đầu.
        Kỳ vọng: retrieve() chỉ được gọi 1 lần — không retry khi đã có kết quả.
        Lý do pass: `if not retrieved_docs and request.chu_de_id` → False (có kết quả).
        """
        mock_rag_system.retrieve.return_value = [SAMPLE_DOC]
        pipeline.process_query(_req(chu_de_id="3"))
        assert mock_rag_system.retrieve.call_count == 1

    def test_no_fallback_when_no_filter_at_all(self, pipeline, mock_rag_system):
        """
        Ngữ cảnh: Không có filter gì (router trả None, user không chọn), retrieve → [].
        Kỳ vọng: KHÔNG retry — đã tìm toàn bộ corpus rồi, retry sẽ cho cùng kết quả.
        Lý do pass: `request.chu_de_id` = None → fallback condition False → không retry.
        """
        mock_rag_system.retrieve.return_value = []
        pipeline.process_query(_req(chu_de_id=None))
        assert mock_rag_system.retrieve.call_count == 1
